"""Source-bound executable shutdown MODEL; not production or guest execution."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "scripts/tests/fixtures/native_shutdown_v6_normal_boot_order.rs"
NATIVE = ROOT / "host-kernel/native-rust"
PINNED_RUSTC = Path("/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc")

# Complete items, including all error/early-return arms, rather than snippets
# ending at the first brace. Changing a production item requires review of
# this sequential model; hashes do not make the model production execution.
BINDINGS = {
    "os_runtime.rs": (
        "impl Admission {", "impl ShutdownAdmission {", "impl Drop for ShutdownAdmission {",
        "fn finish_shutdown(", "fn shutdown_v6_outcome(", "fn shutdown_errno(",
        "unsafe fn os_request(",
    ),
    "ihk_smp_x86_64.rs": (
        "fn shutdown_v6_post_effect(", 'unsafe extern "C" fn ihk_smp_shutdown_v6(',
    ),
    "smp_memory.rs": (
        "fn close_irq_senders_for_shutdown(", "fn finish_shutdown(\n",
        "pub(super) fn shutdown_close_irq_senders(",
        "pub(super) fn finish_shutdown(owner:",
    ),
    "smp_cpu.rs": (
        "impl ShutdownCpuJournal {", "fn shutdown_journal_blocks_ordinary_use(",
        "fn retain_shutdown_failure(", "fn prevalidate_shutdown_targets(",
        "fn validate_shutdown_target(", "fn shutdown_reset_and_reonline(\n",
        "pub(super) fn shutdown_reset_and_reonline_outcome(",
        "pub(super) fn reconcile_shutdown(",
    ),
    "os_registry.rs": (
        "pub(crate) fn begin_shutdown(", "impl ShutdownGuard<'_> {",
        "impl Drop for ShutdownGuard<'_> {",
    ),
}
EXPECTED = {
    "os_runtime.rs": "863c038a0a438c1e6189adc3b6586f8b8deacdeccdfee47ecd252b0107d7ed4b",
    "ihk_smp_x86_64.rs": "86a0b20392f1696c4e5482026b0d4b4c6f003befddd485a9e6ac5ddb523c0af8",
    "smp_memory.rs": "c5f529b51bae2cae890a0d9fc7d15ab9f6f7ced0ce55b47adce227531ef13b47",
    "smp_cpu.rs": "959d59c08a920a6069dacd9629f6e8344f90478b19ac90e22305b110f4d38314",
    "os_registry.rs": "719ee9dfc362e10db73c8d55e06deca694d03e2bd58a3af225ee91b49d0ed4bf",
}


def item(text, marker):
    if text.count(marker) != 1:
        raise AssertionError(f"ambiguous/missing production marker: {marker!r}")
    start = text.index(marker)
    brace = text.index("{", start)
    depth = 0
    for offset in range(brace, len(text)):
        depth += text[offset] == "{"
        depth -= text[offset] == "}"
        if depth == 0:
            return text[start:offset + 1]
    raise AssertionError("unclosed production item")


def bound_items():
    return {
        name: [item((NATIVE / name).read_text(encoding="utf-8"), marker) for marker in markers]
        for name, markers in BINDINGS.items()
    }


class NativeShutdownV6NormalBootOrderTests(unittest.TestCase):
    def test_complete_production_body_bindings(self):
        for name, bodies in bound_items().items():
            with self.subTest(source=name):
                self.assertEqual(hashlib.sha256("\n".join(bodies).encode()).hexdigest(), EXPECTED[name])

    def test_executable_model_and_single_reconciliation_order_mutation(self):
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92", str(PINNED_RUSTC))
        # Missing pinned prerequisites fail explicitly, never silently skip.
        self.assertIn("rustc 1.92.0", subprocess.run(
            [rustc, "--version"], capture_output=True, text=True, check=True, timeout=15).stdout)
        fixture = FIXTURE.read_text(encoding="utf-8")
        original = """        if let Err(error) = self.physical_stop() { return Outcome::PostEffect(error); }
        match self.reconcile() {"""
        replacement = """        let reconciliation = self.reconcile();
        if let Err(error) = self.physical_stop() { return Outcome::PostEffect(error); }
        match reconciliation {"""
        self.assertEqual(fixture.count(original), 1)
        mutated = fixture.replace(original, replacement, 1)
        self.assertEqual(fixture.count("self.reconcile()"), 1)
        self.assertEqual(mutated.count("self.reconcile()"), 1)
        with tempfile.TemporaryDirectory(prefix="native-shutdown-v6-order-") as directory:
            source, binary = Path(directory) / "fixture.rs", Path(directory) / "fixture"
            for label, content in (("model", fixture), ("ordering_mutation", mutated)):
                with self.subTest(variant=label):
                    source.write_text(content, encoding="utf-8")
                    compile_result = subprocess.run(
                        [rustc, "--edition=2021", "--test", "-Dwarnings", str(source), "-o", str(binary)],
                        capture_output=True, text=True, timeout=60)
                    self.assertEqual(compile_result.returncode, 0, compile_result.stdout + compile_result.stderr)
                    run = subprocess.run([str(binary)], env={**os.environ, "RUST_TEST_THREADS": "1"},
                                         capture_output=True, text=True, timeout=15)
                    output = run.stdout + run.stderr
                    if label == "model":
                        self.assertEqual(run.returncode, 0, output)
                        self.assertIn("5 passed; 0 failed", output)
                    else:
                        self.assertNotEqual(run.returncode, 0, output)
                        self.assertIn("assertion failed: self.journal_recorded && self.irq_drained", output)
                        self.assertIn("owner_free_boot_reconciles_only_after_all_physical_effects ... FAILED", output)
                    print(f"{label}: warning-clean compile; exit={run.returncode}\n{output}", flush=True)


if __name__ == "__main__":
    unittest.main()
