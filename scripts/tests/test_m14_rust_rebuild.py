"""Exercise the actual kernel Rust object rule with an unrelated tiny crate.

Only the extracted compiler checks, object command and target are configured.
No production kernel source, held input, SDK or native operation is selected.
The compiler observer invokes the real compiler and records object builds; it
does not replace compilation with a fabricated output.
"""

import importlib.util
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def actual_statements():
    parser_path = ROOT / "scripts/tests/test_m14_syscall_selection.py"
    spec = importlib.util.spec_from_file_location("m14_rebuild_cmake_parser", parser_path)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    parsed = parser.commands((ROOT / "kernel/CMakeLists.txt").read_text())
    start = next(index for index, (name, text) in enumerate(parsed)
                 if name == "find_program" and re.search(r"\(\s*RUSTC\s", text))
    finish = next(index for index in range(start + 1, len(parsed))
                  if parsed[index][0] == "set"
                  and re.search(r"\(\s*RUST_KERNEL_OBJ\s", parsed[index][1]))
    checks = "\n".join(text for _, text in parsed[start:finish])
    rule = parser.one([text for name, text in parsed
                       if name == "add_custom_command"
                       and 'OUTPUT "${RUST_KERNEL_OBJ}"' in text],
                      "kernel Rust object command")
    target = parser.one([text for name, text in parsed
                         if name == "add_custom_target"
                         and "mckernel_rust_obj" in text],
                        "kernel Rust object target")
    sources = next(index for index in range(finish + 1, len(parsed))
                   if parsed[index][0] == "set"
                   and re.search(r"\(\s*RUST_KERNEL_SRCS\s", parsed[index][1]))
    outputs = "\n".join(text for _, text in parsed[finish:sources])
    return checks, outputs, rule, target


class RustRebuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cmake = os.environ.get("CMAKE") or shutil.which("cmake")
        cls.rustc = os.environ.get("RUSTC") or shutil.which("rustc")
        cls.make = shutil.which("make")
        if not cls.cmake or not cls.rustc or not cls.make:
            raise unittest.SkipTest("CMake, rustc and make are required")
        cls.statements = actual_statements()

    def checked(self, command, **kwargs):
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=60, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def write_fixture(self, root, *, historical=False, unlisted=False):
        source, build = root / "source", root / "build"
        (source / "rust").mkdir(parents=True)
        (source / "rust/lib.rs").write_text(
            '#![no_std]\nmod nested;\n'
            'static DATA: &[u8] = include_bytes!("payload.bin");\n'
            '#[no_mangle]\npub extern "C" fn observed_value() -> u64 { nested::value() + DATA[0] as u64'
            ' + env!("MCKERNEL_RUST_VERSION").len() as u64 }\n')
        (source / "rust/nested.rs").write_text('pub fn value() -> u64 { 31 }\n')
        (source / "rust/payload.bin").write_bytes(b"\x21")
        (source / "cmake").mkdir()
        shutil.copyfile(ROOT / "cmake/NormalizeRustDepfile.cmake",
                        source / "cmake/NormalizeRustDepfile.cmake")
        checks, output, rule, target = self.statements
        if historical:
            # Remove only the corrected compiler prerequisite in this isolated
            # control. Every compiler flag and actual source dependency remains.
            rule, count = re.subn(
                r'(DEPENDS\s+\$\{RUST_KERNEL_SRCS\})\s+"\$\{RUSTC\}"',
                r'\1', rule, count=1)
            self.assertEqual(count, 1, "Expected the selected compiler prerequisite")
        (source / "CMakeLists.txt").write_text("\n".join([
            "cmake_minimum_required(VERSION 3.20)",
            "project(m14_rust_rebuild_fixture LANGUAGES NONE)",
            checks, output,
            'set(RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/lib.rs"'
            + (')' if unlisted else ' "${CMAKE_CURRENT_SOURCE_DIR}/rust/nested.rs")'),
            rule, target,
        ]) + "\n")
        return source, build

    def write_compiler_observer(self, path, log, label):
        path.write_text(
            '#!/bin/sh\n'
            'if [ "$1" = "--crate-name" ]; then\n'
            f'  printf "%s\\n" {shlex.quote(label)} >> {shlex.quote(str(log))}\n'
            'fi\n'
            f'exec {shlex.quote(str(self.rustc))} "$@"\n')
        path.chmod(0o755)

    def configure(self, source, build, compiler, generator="Unix Makefiles"):
        return self.checked([
            self.cmake, "-S", str(source), "-B", str(build),
            "-G", generator, f"-DRUSTC={compiler}",
        ])

    def build(self, build):
        return self.checked([self.cmake, "--build", str(build),
                             "--target", "mckernel_rust_obj", "--", "-j1"])

    def test_compiler_replacement_rebuilds_and_no_change_does_not(self):
        with tempfile.TemporaryDirectory(prefix="m14-rust-rebuild-") as temporary:
            root = Path(temporary)
            source, build = self.write_fixture(root)
            compiler, log = root / "selected-rustc", root / "compilations.txt"
            self.write_compiler_observer(compiler, log, "first")
            self.configure(source, build, compiler)
            self.build(build)
            obj = build / "rust/mckernel_rust.o"
            self.assertTrue(obj.is_file())
            self.assertEqual(obj.read_bytes()[:4], b"\x7fELF")
            first_mtime = obj.stat().st_mtime_ns
            self.build(build)
            self.assertEqual(log.read_text().splitlines(), ["first"])
            self.assertEqual(obj.stat().st_mtime_ns, first_mtime)

            self.write_compiler_observer(compiler, log, "replacement")
            self.assertGreater(compiler.stat().st_mtime_ns, first_mtime)
            self.build(build)
            self.assertEqual(log.read_text().splitlines(), ["first", "replacement"])
            replacement_mtime = obj.stat().st_mtime_ns
            self.assertGreater(replacement_mtime, first_mtime)
            self.build(build)
            self.assertEqual(obj.stat().st_mtime_ns, replacement_mtime)
            self.assertEqual(log.read_text().splitlines(), ["first", "replacement"])

            # Existing source prerequisites still rebuild the actual object.
            (source / "rust/nested.rs").write_text('pub fn value() -> u64 { 47 }\n')
            self.build(build)
            self.assertEqual(log.read_text().splitlines(),
                             ["first", "replacement", "replacement"])

    def test_original_rule_reproduces_stale_compiler_object(self):
        with tempfile.TemporaryDirectory(prefix="m14-rust-rebuild-control-") as temporary:
            root = Path(temporary)
            source, build = self.write_fixture(root, historical=True)
            compiler, log = root / "selected-rustc", root / "compilations.txt"
            self.write_compiler_observer(compiler, log, "first")
            self.configure(source, build, compiler)
            self.build(build)
            obj = build / "rust/mckernel_rust.o"
            original_mtime = obj.stat().st_mtime_ns
            self.write_compiler_observer(compiler, log, "replacement")
            self.assertGreater(compiler.stat().st_mtime_ns, original_mtime)
            self.build(build)
            self.assertEqual(log.read_text().splitlines(), ["first"])
            self.assertEqual(obj.stat().st_mtime_ns, original_mtime)

    def test_selected_compiler_must_be_an_absolute_existing_file(self):
        with tempfile.TemporaryDirectory(prefix="m14-rust-rebuild-path-") as temporary:
            root = Path(temporary)
            source, _ = self.write_fixture(root)
            for index, compiler in enumerate(("relative-rustc", root / "absent", root)):
                with self.subTest(compiler=str(compiler)):
                    result = subprocess.run([
                        self.cmake, "-S", str(source), "-B", str(root / f"build-{index}"),
                        "-G", "Unix Makefiles", f"-DRUSTC={compiler}",
                    ], capture_output=True, text=True, timeout=30)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("nondirectory absolute Rust compiler path",
                                  " ".join((result.stdout + result.stderr).split()))

    def test_unlisted_modules_and_binary_includes_rebuild_on_make_and_ninja(self):
        self.assertIsNotNone(shutil.which("ninja"), "Ninja is required for this qualified generator case")
        for generator in ("Unix Makefiles", "Ninja"):
            with self.subTest(generator=generator), tempfile.TemporaryDirectory(prefix="m14-depfile-") as tmp:
                root = Path(tmp)
                source, build = self.write_fixture(root, unlisted=True)
                compiler, log = root / "selected-rustc", root / "compilations.txt"
                self.write_compiler_observer(compiler, log, "compile")
                self.configure(source, build, compiler, generator=generator)
                self.build(build)
                obj = build / "rust/mckernel_rust.o"
                before = hashlib.sha256(obj.read_bytes()).hexdigest()
                self.build(build)
                self.assertEqual(log.read_text().splitlines(), ["compile"])
                (source / "rust/nested.rs").write_text('pub fn value() -> u64 { 99 }\n')
                self.build(build)
                after_module = hashlib.sha256(obj.read_bytes()).hexdigest()
                self.assertNotEqual(after_module, before, "unlisted module edit reused a stale object")
                (source / "rust/payload.bin").write_bytes(b"\x63")
                self.build(build)
                after_payload = hashlib.sha256(obj.read_bytes()).hexdigest()
                self.assertNotEqual(after_payload, after_module, "binary include edit reused a stale object")
                self.assertEqual(log.read_text().splitlines(), ["compile"] * 3)
                self.build(build)
                self.assertEqual(log.read_text().splitlines(), ["compile"] * 3)
                # Reproduce the same object from scratch within the same declared
                # path/toolchain profile; this is not whole-image reproducibility.
                obj.unlink()
                self.build(build)
                self.assertEqual(hashlib.sha256(obj.read_bytes()).hexdigest(), after_payload)

    def test_failed_version_probe_is_not_accepted_as_nightly(self):
        with tempfile.TemporaryDirectory(prefix="m14-version-probe-") as tmp:
            root = Path(tmp)
            source, build = self.write_fixture(root)
            compiler = root / "failed-rustc"
            compiler.write_text("#!/bin/sh\necho 'rustc fixture-nightly'\nexit 9\n")
            compiler.chmod(0o755)
            result = subprocess.run([self.cmake, "-S", str(source), "-B", str(build),
                                     f"-DRUSTC={compiler}"], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires nightly rustc", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
