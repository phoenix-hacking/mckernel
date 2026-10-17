"""Bounded actual-body checks for the isolated, still disabled fork slice."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest

from scripts.tests.test_native_fork_ownership_20261017 import fixture_source as boundary_source

ROOT = Path(__file__).resolve().parents[2]
RUSTC = Path("/home/holden/mckernel-work/toolchains/rustup/toolchains/"
             "1.92.0-x86_64-unknown-linux-gnu/bin/rustc")


def items():
    vm = (ROOT / "host-kernel/native-rust/mcctrl_vm.rs").read_text()
    image = (ROOT / "host-kernel/native-rust/smp_application_image.rs").read_text()
    return {
        "@BOUNDARY_FIXTURE@": boundary_source(),
        "@FORK_TRANSITIONS@": image[image.index("// BEGIN FORK ADOPTION TRANSITIONS"):
                                    image.index("// END FORK ADOPTION TRANSITIONS")],
        "@VMA_MMAP@": vm[vm.index("unsafe extern \"C\" fn mmap("):
                          vm.index("\nstruct FaultPage")],
    }


def generated_source():
    source = (ROOT / "scripts/tests/fixtures/native_fork_adoption_transaction_20261017.rs").read_text()
    for marker, body in items().items():
        if source.count(marker) != 1:
            raise AssertionError("expected exactly one extraction marker: " + marker)
        source = source.replace(marker, body)
    return source


class NativeForkAdoptionTransactionTests(unittest.TestCase):
    def test_extracts_production_bodies_and_keeps_fork_gate_closed(self):
        source = generated_source()
        for body in items().values():
            self.assertIn(body, source)
        self.assertNotIn("@FORK_", source)
        process = (ROOT / "host-kernel/native-rust/mcctrl_process.rs").read_text()
        start = process.index("    pub(super) fn create_process(")
        gate = process[start:process.index("        let process = self.process()?;", start)]
        self.assertIn("if argument != 0", gate)
        self.assertIn("return Err(kernel::error::to_result(-95).unwrap_err());", gate)

    def test_file_is_neutral_and_vm_operations_have_owner_lifecycle(self):
        vm = (ROOT / "host-kernel/native-rust/mcctrl_vm.rs").read_text()
        mapping = vm[vm.index("struct MappingFile {"):vm.index("// SAFETY: The caller holds Linux")]
        self.assertNotIn("registration:", mapping)
        self.assertNotIn("mirror:", mapping)
        self.assertIn("Option<Arc<VmaOwner>>", mapping)
        self.assertIn("operations.open = Some(vma_open);", vm)
        self.assertIn("operations.close = Some(vma_close);", vm)

    def test_actual_owner_and_transaction_bodies(self):
        compiler = Path(os.environ.get("MCKERNEL_RUSTC_1_92", str(RUSTC)))
        self.assertTrue(compiler.is_file(), "pinned compiler required")
        attempt = Path(tempfile.mkdtemp(prefix="native-fork-adoption-20261017-"))
        print("fork_adoption_evidence=" + str(attempt), flush=True)
        source = attempt / "actual_bodies.rs"
        binary = attempt / "actual_bodies"
        source.write_text(generated_source())

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
        self.assertIn(b"12 passed; 0 failed", executed.stdout)


if __name__ == "__main__":
    unittest.main()
