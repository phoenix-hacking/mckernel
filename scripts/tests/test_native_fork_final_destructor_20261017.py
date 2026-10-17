"""Exact additive checked-release bodies, preserving every old API/structure.

Compiler execution requires the dispatcher's separate scoped profile release.
The first three cases perform source-only checks and have no subprocesses.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUSTC = Path("/home/holden/mckernel-work/toolchains/rustup/toolchains/"
             "1.92.0-x86_64-unknown-linux-gnu/bin/rustc")
BODY_NAMES = ("process_release_thread_body_result", "process_release_vm_body_result",
              "process_release_thread_checked_body_result", "process_release_vm_checked_body_result")
LEGACY_HASHES = {
    "kernel/rust/process_helpers.rs:process_release_thread_body_result": "0cff54ad4dece33e745d5093075874850ea5b0105eb521331404752960facb8a",
    "kernel/rust/process_helpers.rs:process_release_vm_body_result": "1438e829339e637602868e5c524209d3ebdbe524a744d387eab44414df14ccd5",
    "kernel/rust/process_helpers.rs:release_thread": "7e95d7296dcfad7abdf7919191623904f153e94f32bb22e5de30ea5e5cfd4004",
    "kernel/rust/process_helpers.rs:release_process_vm": "fcc06a67be25a295dc93ee540972287d18467b602e9c1daad9e7ba13d8b5a431",
    "kernel/rust/process_helpers.rs:process_release_vm_bridge": "53c3bed00bc2a4f7ca13f8b2fe9a62d82a074ec8850efde80f685fedef2d1e65",
    "kernel/process_helpers.c:process_release_thread_body_result": "0ffd44155f8e3ea930fb8e4847179aab2e84b251bbf8f85d5a0aa868a23bf1a4",
    "kernel/process_helpers.c:process_release_vm_body_result": "9739c3ef46b6c3a9ad26d51aea483d2e0a9e5e7b5f45ff7501836a47c0d23617",
    "kernel/process.c:release_thread": "01f8c9d66f8d28a21b8b74220eb25ce95675e3890dd3e9827a7194e46fd54181",
    "kernel/process.c:release_process_vm": "51dc458d90f98f951b3c708f5b2416a2ce416ff3ffe4b1b2dba506ae53ecaafd",
    "kernel/process.c:process_release_vm_bridge": "906c47fa8ead045b8ee792d3b23f12df2ac184de676eee9d70427ae7224a588e",
}
STRUCT_HASHES = {"process": "503d228de8cd13dfdff1f26081335406d061a425ef1660fd8af80fcaac44f2aa",
                 "thread": "c29bf867b3dfaf8932c61cd34923b0e4f1baab6532b83f0551e5b4da0dded34a",
                 "process_vm": "2da612c242c98db1ef28e1462f0d36fa928b6fbd6d582b8004db47e1c28c6823"}


def braced(text, start):
    opening = text.index("{", start)
    level, end = 1, opening + 1
    while level:
        level += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def function(text, name):
    pattern = r'(?m)^(?:pub unsafe extern "C" fn |(?:int|void)\s+)' + re.escape(name) + r'\('
    matches = list(re.finditer(pattern, text))
    definitions = [match for match in matches if text.index("{", match.start()) < text.find(";", match.start())
                   or text.find(";", match.start()) == -1]
    # Rust signatures have no semicolon; C prototypes must never be extracted
    # as definitions when a later implementation has the same name.
    if len(definitions) != 1:
        raise AssertionError("expected one definition: " + name + " found=" + str(len(definitions)))
    return braced(text, definitions[0].start())


def normalize(text):
    return re.sub(r"\s+", "", text)


def c_prototype(header, name):
    match = re.search(r"(?m)^int " + name + r"\([^;]+;", header)
    if not match:
        raise AssertionError("missing exact C prototype: " + name)
    return match.group(0)


def c_guard(text, name):
    body = function(text, name)
    prefix = text[:text.index(body)]
    stack = []
    for line in prefix.splitlines():
        directive = re.match(r"\s*#\s*(ifdef|ifndef|if|else|elif|endif)\b(.*)", line)
        if not directive:
            continue
        operation, value = directive.groups()
        if operation in ("ifdef", "ifndef", "if"):
            stack.append((operation, value.strip()))
        elif operation == "else":
            old, value = stack.pop()
            stack.append(("ifndef" if old == "ifdef" else "ifdef" if old == "ifndef" else "else", value))
        elif operation == "elif":
            stack[-1] = ("if", value.strip())
        else:
            stack.pop()
    return stack


def generated_sources():
    rust = (ROOT / "kernel/rust/process_helpers.rs").read_text()
    c = (ROOT / "kernel/process_helpers.c").read_text()
    header = (ROOT / "kernel/include/process_helpers.h").read_text()
    rust_types = ("ProcessRefDecAndTestFn", "ProcessThreadProfileFn", "ProcessThreadActionFn",
                  "ProcessVmActionFn", "ProcessVmReleaseCheckedFn", "ProcessSpinLockFn", "ProcessSpinUnlockFn",
                  "ProcessDetachAddressSpaceFn", "ProcessReleaseProcessFn", "ProcessPolicyFreeFn",
                  "ProcessFreeFn", "ProcessVmFreeCallback")
    c_types = ("process_ref_dec_and_test_fn_t", "process_thread_profile_fn_t", "process_thread_action_fn_t",
               "process_vm_action_fn_t", "process_vm_release_checked_fn_t", "process_spin_lock_fn_t",
               "process_spin_unlock_fn_t", "process_detach_address_space_fn_t", "process_release_process_fn_t",
               "process_policy_free_fn_t", "process_free_fn_t", "process_vm_free_cb_fn_t")
    rust_aliases = []
    c_aliases = []
    for name in rust_types:
        rust_aliases.append(re.search(r"(?m)^type " + name + r"\s*=[^;]+;", rust).group(0))
    for name in c_types:
        c_aliases.append(re.search(r"(?m)^typedef [^;]+\(\*" + name + r"\)[^;]+;", header).group(0))
    rust_bodies = "\n\n".join("#[no_mangle]\n" + function(rust, name) for name in BODY_NAMES)
    c_bodies = "\n\n".join(function(c, name) for name in BODY_NAMES)
    rust_template = (ROOT / "scripts/tests/fixtures/native_fork_final_destructor_20261017.rs").read_text()
    c_template = (ROOT / "scripts/tests/fixtures/native_fork_final_destructor_20261017.c").read_text()
    rust_source = rust_template.replace("@CALLBACK_TYPES@", "\n".join(rust_aliases)).replace("@ACTUAL_RUST_BODIES@", rust_bodies)
    c_source = c_template.replace("@CALLBACK_TYPES@", "\n".join(c_aliases)).replace("@ACTUAL_C_BODIES@", c_bodies)
    c_source = c_source.replace("@RUST_BODY_PROTOTYPES@", "\n".join(c_prototype(header, name) for name in BODY_NAMES))
    return rust_source, c_source


class NativeForkFinalDestructorTests(unittest.TestCase):
    def test_old_body_wrapper_and_struct_bytes_unchanged(self):
        for key, expected in LEGACY_HASHES.items():
            path, name = key.split(":")
            self.assertEqual(hashlib.sha256(function((ROOT / path).read_text(), name).encode()).hexdigest(), expected, key)
        header = (ROOT / "kernel/include/process.h").read_text()
        for name, expected in STRUCT_HASHES.items():
            region = braced(header, header.index("struct " + name + " {"))
            self.assertEqual(hashlib.sha256(region.encode()).hexdigest(), expected, name)
        abi = Path("/home/holden/mckernel/kernel/rust/abi.rs")
        self.assertEqual(hashlib.sha256(abi.read_bytes()).hexdigest(),
                         "ff48bc2e7c8fe00abf19572a3fe75661dd464a7a475fec91a0ac7d870f6fdd3e")

    def test_additive_signatures_wrappers_and_symbol_selection(self):
        rust = (ROOT / "kernel/rust/process_helpers.rs").read_text()
        c = (ROOT / "kernel/process_helpers.c").read_text()
        wrappers = (ROOT / "kernel/process.c").read_text()
        header = (ROOT / "kernel/include/process_helpers.h").read_text()
        for name in BODY_NAMES[2:]:
            body = function(c, name)
            self.assertEqual(normalize(body[:body.index("{")]) + ";", normalize(c_prototype(header, name)))
            self.assertIn(("ifndef", "MCKERNEL_RUST_PROCESS_HELPERS"), c_guard(c, name))
            legacy = name.replace("_checked_body_result", "_body_result")
            old_rust_signature = function(rust, legacy).split("{", 1)[0]
            new_rust_signature = function(rust, name).split("{", 1)[0].replace(name, legacy)
            new_rust_signature = new_rust_signature.replace("ProcessVmReleaseCheckedFn", "ProcessVmActionFn")
            self.assertEqual(normalize(new_rust_signature), normalize(old_rust_signature))
        for name in ("release_thread_checked", "release_process_vm_checked", "process_release_vm_checked_bridge"):
            self.assertIn(("ifndef", "MCKERNEL_RUST_PROCESS_HELPERS"), c_guard(wrappers, name))
            self.assertIn("-> CInt", function(rust, name).split("{", 1)[0])
        for name in ("release_thread", "release_process_vm"):
            for text, pattern in ((rust, r"offset_of!\([^)]*\)"), (wrappers, r"__builtin_offsetof\([^)]*\)")):
                self.assertEqual(re.findall(pattern, function(text, name)), re.findall(pattern, function(text, name + "_checked")))
        self.assertIn("Some(process_release_vm_checked_bridge)", function(rust, "release_thread_checked"))
        self.assertIn("process_release_vm_checked_bridge", function(wrappers, "release_thread_checked"))

    def test_extracts_exact_bodies_with_no_markers_and_keeps_gate_closed(self):
        rust_source, c_source = generated_sources()
        for name in BODY_NAMES:
            self.assertIn(function((ROOT / "kernel/rust/process_helpers.rs").read_text(), name), rust_source)
            self.assertIn(function((ROOT / "kernel/process_helpers.c").read_text(), name), c_source)
        self.assertNotIn("@ACTUAL_", rust_source + c_source)
        self.assertNotIn("@CALLBACK_", rust_source + c_source)
        process = (ROOT / "host-kernel/native-rust/mcctrl_process.rs").read_text()
        start = process.index("    pub(super) fn create_process(")
        gate = process[start:process.index("        let process = self.process()?;", start)]
        self.assertIn("if argument != 0", gate)
        self.assertIn("return Err(kernel::error::to_result(-95).unwrap_err());", gate)

    def test_actual_rust_c_vectors_and_poison_controls(self):
        compiler = Path(os.environ.get("MCKERNEL_RUSTC_1_92", str(RUSTC)))
        self.assertTrue(compiler.is_file(), "pinned Rust 1.92 required")
        attempt = Path(tempfile.mkdtemp(prefix="native-fork-final-destructor-20261017-"))
        print("fork_final_destructor_evidence=" + str(attempt), flush=True)
        rust_source, c_source = generated_sources()
        rust_path, c_path = attempt / "actual_bodies.rs", attempt / "actual_bodies.c"
        obj, binary = attempt / "actual_c.o", attempt / "actual_bodies"
        rust_path.write_text(rust_source); c_path.write_text(c_source)

        def captured(label, command, timeout):
            (attempt / (label + ".command.json")).write_text(json.dumps(command) + "\n")
            try:
                result = subprocess.run(command, capture_output=True, timeout=timeout,
                                        env={**os.environ, "RUST_TEST_THREADS": "1"})
            except subprocess.TimeoutExpired as error:
                (attempt / (label + ".stdout")).write_bytes(error.stdout or b"")
                (attempt / (label + ".stderr")).write_bytes(error.stderr or b"")
                (attempt / (label + ".status.json")).write_text(json.dumps({"timeout_seconds": timeout, "returncode": None}) + "\n")
                raise
            (attempt / (label + ".stdout")).write_bytes(result.stdout)
            (attempt / (label + ".stderr")).write_bytes(result.stderr)
            (attempt / (label + ".status.json")).write_text(json.dumps({"returncode": result.returncode}) + "\n")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result

        version = captured("rustc-version", [str(compiler), "--version"], 15)
        self.assertTrue(version.stdout.startswith(b"rustc 1.92.0 "), version.stdout)
        captured("cc-version", ["/usr/bin/cc", "--version"], 15)
        captured("compile-c", ["/usr/bin/cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-c", str(c_path), "-o", str(obj)], 45)
        captured("compile-rust", [str(compiler), "--edition=2021", "--test", "-Dwarnings", str(rust_path),
                                  "-C", "link-arg=" + str(obj), "-o", str(binary)], 60)
        executed = captured("run", [str(binary), "--test-threads=1", "--nocapture"], 30)
        self.assertIn(b"2 passed; 0 failed", executed.stdout)


if __name__ == "__main__":
    unittest.main()
