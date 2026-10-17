"""Dormant inherited-VMA transaction actual-body regression; no native ABI claim."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
VM = ROOT / "host-kernel/native-rust/mcctrl_vm.rs"
FIXTURE = ROOT / "scripts/tests/fixtures/native_fork_inherited_vma_transaction_20261017.rs"
RUSTC = Path("/home/holden/mckernel-work/toolchains/rustup/toolchains/"
             "1.92.0-x86_64-unknown-linux-gnu/bin/rustc")


def braced(text, start):
    end = text.index("{", start) + 1
    level = 1
    while level:
        level += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def extracted():
    vm = VM.read_text()
    process = (ROOT / "host-kernel/native-rust/mcctrl_process.rs").read_text()
    return {
        "MM_LIFETIME": vm[vm.index("struct CurrentMm("):vm.index("pub(super) struct Mirror {")],
        "MIRROR": braced(vm, vm.index("pub(super) struct Mirror {")),
        "OWNERS": vm.split("// BEGIN FORK VMA OWNERS\n", 1)[1].split("// END FORK VMA OWNERS", 1)[0],
        "TRANSACTION": vm.split("// BEGIN INHERITED VMA TRANSACTION\n", 1)[1].split("// END INHERITED VMA TRANSACTION", 1)[0],
        "FAULT": braced(vm, vm.index("unsafe fn lookup_fault(")),
        "SAME_GENERATION": braced(process, process.index("    pub(super) fn same_generation(")),
    }


def generated_source():
    source = FIXTURE.read_text()
    for key, value in extracted().items():
        assert source.count("@" + key + "@") == 1, key
        source = source.replace("@" + key + "@", value)
    return source


class InheritedVmaTransactionTests(unittest.TestCase):
    def test_complete_production_decisions_are_compiled(self):
        source = generated_source()
        for key, value in extracted().items():
            self.assertIn(value, source, key)
        self.assertEqual(FIXTURE.read_text().count("#[test]"), 4)

    def test_runtime_gate_stays_closed(self):
        process = (ROOT / "host-kernel/native-rust/mcctrl_process.rs").read_text()
        start = process.index("    pub(super) fn create_process(")
        gate = process[start:process.index("        let process = self.process()?;", start)]
        self.assertIn("if argument != 0", gate)
        self.assertIn("return Err(kernel::error::to_result(-95).unwrap_err());", gate)

    def test_actual_transaction_prevalidation_allocation_order_and_fault_routes(self):
        attempt = Path(tempfile.mkdtemp(prefix="native-fork-inherited-vma-20261017-"))
        print("fork_inherited_vma_evidence=" + str(attempt), flush=True)
        source, binary = attempt / "generated.rs", attempt / "test"
        source.write_text(generated_source())

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

        version = captured("version", [str(RUSTC), "--version"], 15)
        self.assertTrue(version.stdout.startswith(b"rustc 1.92.0 "), version.stdout)
        captured("compile", [str(RUSTC), "--edition=2021", "--test", str(source), "-o", str(binary)], 60)
        result = captured("run", [str(binary), "--test-threads=1"], 30)
        self.assertIn(b"4 passed; 0 failed", result.stdout)


if __name__ == "__main__":
    unittest.main()
