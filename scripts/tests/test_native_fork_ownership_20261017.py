"""Execute unchanged native fault/worker bodies at the missing fork boundary.

This is a negative reproducer, not a replacement fork implementation or guest
acceptance. Linux structures and transport are explicit fixture boundaries.
"""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "scripts/tests/fixtures/native_fork_ownership_20261017.rs"
RUSTC = Path("/home/holden/mckernel-work/toolchains/rustup/toolchains/"
             "1.92.0-x86_64-unknown-linux-gnu/bin/rustc")


def extracted_bodies():
    vm = (ROOT / "host-kernel/native-rust/mcctrl_vm.rs").read_text()
    backend = (ROOT / "host-kernel/native-rust/smp_application.rs").read_text()
    return {
        "@VMA_OWNERS@": vm[vm.index("// BEGIN FORK VMA OWNERS"):
                             vm.index("// END FORK VMA OWNERS")],
        "@LOOKUP_FAULT@": vm[vm.index("unsafe fn lookup_fault("):
                              vm.index("\n// SAFETY: The locked live VMA retains")],
        "@WORKER@": backend[backend.index("    pub(crate) fn worker("):
                               backend.index("\n    pub(crate) fn wait_syscall(")],
    }


def fixture_source():
    source = FIXTURE.read_text()
    for marker, body in extracted_bodies().items():
        if source.count(marker) != 1:
            raise AssertionError("fixture extraction marker must occur once: " + marker)
        source = source.replace(marker, body)
    return source


class NativeForkOwnershipTests(unittest.TestCase):
    def test_fixture_contains_verbatim_actual_bodies(self):
        source = fixture_source()
        for body in extracted_bodies().values():
            self.assertEqual(source.count(body), 1)
        self.assertNotIn("@LOOKUP_FAULT@", source)
        self.assertNotIn("@WORKER@", source)
        self.assertNotIn("@VMA_OWNERS@", source)

    def test_worker_close_dependency_has_explicit_no_child_adapter(self):
        source = fixture_source()
        self.assertIn('assert_eq!(slots.len(), 1, "no-child baseline only");', source)
        self.assertIn('assert_eq!(entry.key(), parent, "no child entry in this adapter");', source)
        self.assertIn("backend.worker(4, &mut bytes, false)", source)
        self.assertIn("assert_eq!(parent.baseline_cancel_calls, 1);", source)
        self.assertIn("assert_eq!(parent.baseline_cancel_worker, Some(77));", source)

    def test_actual_fault_and_worker_reproducers(self):
        compiler = Path(os.environ.get("MCKERNEL_RUSTC_1_92", str(RUSTC)))
        self.assertTrue(compiler.is_file(), "pinned Rust 1.92 compiler required")
        # Retain generated source, executable and every stream even if the
        # compiler/test fails. TMPDIR is assigned by the reviewed dispatcher.
        attempt = Path(tempfile.mkdtemp(prefix="native-fork-ownership-20261017-"))
        print("fork_ownership_evidence=" + str(attempt), flush=True)
        source = attempt / "actual_bodies.rs"
        binary = attempt / "actual_bodies"
        source.write_text(fixture_source())

        def captured(label, command, timeout):
            (attempt / (label + ".command.json")).write_text(json.dumps(command) + "\n")
            try:
                result = subprocess.run(command, capture_output=True, timeout=timeout,
                                        env={**os.environ, "RUST_TEST_THREADS": "1"})
            except subprocess.TimeoutExpired as error:
                (attempt / (label + ".stdout")).write_bytes(error.stdout or b"")
                (attempt / (label + ".stderr")).write_bytes(error.stderr or b"")
                (attempt / (label + ".status.json")).write_text(
                    json.dumps({"timeout_seconds": timeout, "returncode": None}) + "\n")
                raise
            (attempt / (label + ".stdout")).write_bytes(result.stdout)
            (attempt / (label + ".stderr")).write_bytes(result.stderr)
            (attempt / (label + ".status.json")).write_text(
                json.dumps({"returncode": result.returncode}) + "\n")
            return result

        version = captured("compiler-version", [str(compiler), "--version"], 15)
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertTrue(version.stdout.startswith(b"rustc 1.92.0 "), version.stdout)
        compiled = captured("compile", [str(compiler), "--edition=2021", "--test",
                                       "-Dwarnings", str(source), "-o", str(binary)], 60)
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
        executed = captured("run", [str(binary), "--test-threads=1"], 30)
        self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)
        self.assertIn(b"4 passed; 0 failed", executed.stdout)


if __name__ == "__main__":
    unittest.main()
