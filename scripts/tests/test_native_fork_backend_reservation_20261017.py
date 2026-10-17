"""Actual retained-mailbox and backend fork reservation decisions.

Only test_actual_bodies invokes the compiler; dispatcher approval is required.
The other tests are source-only and use the standard library exclusively.
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
NATIVE = ROOT / "host-kernel/native-rust"
RUSTC = Path("/home/holden/mckernel-work/toolchains/rustup/toolchains/"
             "1.92.0-x86_64-unknown-linux-gnu/bin/rustc")
TEMPLATE = ROOT / "scripts/tests/fixtures/native_fork_backend_reservation_20261017.rs"


def region(text, label):
    begin, end = "// BEGIN " + label, "// END " + label
    assert text.count(begin) == text.count(end) == 1, label
    return text.split(begin, 1)[1].split(end, 1)[0]


def braced(text, start):
    opening = text.index("{", start)
    level, end = 1, opening + 1
    while level:
        level += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def generated_source():
    backend = (NATIVE / "smp_application.rs").read_text()
    image = (NATIVE / "smp_application_image.rs").read_text()
    replacements = {
        "RPC": (NATIVE / "application_rpc.rs").read_text(),
        "SYSCALL": (NATIVE / "application_syscall.rs").read_text(),
        "MAILBOX": (NATIVE / "smp_application_syscall.rs").read_text(),
        "TRANSITIONS": region(image, "FORK ADOPTION TRANSITIONS"),
        "RESERVATION_METADATA": region(image, "FORK RESERVATION METADATA"),
        "BACKEND_HELPERS": region(backend, "FORK BACKEND RESERVATION"),
        "ENTRY_KEY": braced(backend, backend.index("    fn key(&self) -> Token {")),
    }
    source = TEMPLATE.read_text()
    for key, value in replacements.items():
        assert source.count("@" + key + "@") == 1, key
        source = source.replace("@" + key + "@", value)
    assert not re.search(r"@[A-Z_]+@", source)
    return source


class NativeForkBackendReservationTests(unittest.TestCase):
    def test_exact_production_bodies_are_extracted(self):
        source = generated_source()
        for name in ("application_rpc.rs", "application_syscall.rs", "smp_application_syscall.rs"):
            self.assertIn((NATIVE / name).read_text(), source)
        self.assertIn(region((NATIVE / "smp_application.rs").read_text(), "FORK BACKEND RESERVATION"), source)
        self.assertEqual(source.count("#[test]"), 5)

    def test_original_mailbox_and_wire_abi_are_preserved(self):
        mailbox = (NATIVE / "smp_application_syscall.rs").read_text()
        start = mailbox.index("    /// Immutable discovery under Remote.slots.")
        end = mailbox.index("    pub(crate) fn queued_cpu", start)
        original = mailbox[:start] + mailbox[end:]
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),
                         "4118de1401f33b2df17393660e6acbce2f337dca8a9cdfcf10965b1d3dc84c55")
        abi = (NATIVE / "abi/application.rs").read_bytes()
        self.assertEqual(hashlib.sha256(abi).hexdigest(),
                         "d2b3770a111777d4f28a7a81814a03414d318a90d3ec7082d5c89149b1704a0f")

    def test_no_success_gate_or_external_reservation_caller(self):
        process = (NATIVE / "mcctrl_process.rs").read_text()
        start = process.index("    pub(super) fn create_process(")
        gate = process[start:process.index("        let process = self.process()?;", start)]
        self.assertIn("if argument != 0", gate)
        self.assertIn("return Err(kernel::error::to_result(-95).unwrap_err());", gate)
        for name in ("ihk_smp_x86_64.rs", "mcctrl_process.rs", "mcctrl_vm.rs"):
            self.assertNotIn(".reserve_fork(", (NATIVE / name).read_text())

    def test_actual_bodies(self):
        compiler = Path(os.environ.get("MCKERNEL_RUSTC_1_92", str(RUSTC)))
        self.assertTrue(compiler.is_file(), "pinned Rust 1.92 required")
        attempt = Path(tempfile.mkdtemp(prefix="native-fork-backend-reservation-20261017-"))
        print("fork_backend_reservation_evidence=" + str(attempt), flush=True)
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
                (attempt / (label + ".status.json")).write_text(json.dumps({"timeout_seconds": timeout, "returncode": None}) + "\n")
                raise
            (attempt / (label + ".stdout")).write_bytes(result.stdout)
            (attempt / (label + ".stderr")).write_bytes(result.stderr)
            (attempt / (label + ".status.json")).write_text(json.dumps({"returncode": result.returncode}) + "\n")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result

        version = captured("rustc-version", [str(compiler), "--version"], 15)
        self.assertTrue(version.stdout.startswith(b"rustc 1.92.0 "), version.stdout)
        captured("compile", [str(compiler), "--edition=2021", "--test", "-Dwarnings", str(source), "-o", str(binary)], 60)
        result = captured("run", [str(binary), "--test-threads=1", "--nocapture"], 30)
        self.assertIn(b"5 passed; 0 failed", result.stdout)


if __name__ == "__main__":
    unittest.main()
