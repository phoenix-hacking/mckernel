#!/usr/bin/env python3
"""Source-bound checks for the physical STOP v6 provider transaction."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "host-kernel/native-rust/ihk_smp_x86_64.rs"


def callback_body(source: str) -> str:
    start = source.index("unsafe extern \"C\" fn ihk_smp_shutdown_v6")
    end = source.index("\n}\n\n// These callbacks deliberately own lifecycle only.", start) + 2
    return source[start:end]


class NativeShutdownV6ProviderTests(unittest.TestCase):
    def generated(self):
        memory = (ROOT / "host-kernel/native-rust/smp_memory.rs").read_text()
        source = SOURCE.read_text()
        template = (ROOT / "scripts/tests/fixtures/shutdown_v6_provider.rs").read_text()
        methods = balanced_item(memory, "fn close_irq_senders_for_shutdown(") + "\n" + \
            "pub(super) " + balanced_item(memory, "fn finish_shutdown(")
        return template.replace("// PRODUCTION_IRQ_FAILURE", balanced_item(memory, "pub(super) enum ShutdownIrqFailure")) \
            .replace("// PRODUCTION_EFFECT_TAG", next(line for line in source.splitlines() if line.startswith("const IHK_SMP_SHUTDOWN_V6_POST_EFFECT:"))) \
            .replace("// PRODUCTION_BOOT_STORAGE", balanced_item(memory, "struct BootStorage {") + "\n" + balanced_item(memory, "impl Drop for BootStorage")) \
            .replace("// PRODUCTION_MEMORY_METHODS", methods) \
            .replace("// PRODUCTION_CALLBACK", balanced_item(source, "fn shutdown_v6_post_effect(") + "\n" + callback_body(source))

    def execute(self, generated, selected=None):
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92", "/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc")
        with tempfile.TemporaryDirectory(prefix="shutdown-v6-provider-") as directory:
            source, binary = Path(directory) / "fixture.rs", Path(directory) / "fixture"
            source.write_text(generated)
            result = subprocess.run([rustc, "--edition=2021", "--test", "-Dwarnings", str(source), "-o", str(binary)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return subprocess.run([str(binary), "--test-threads=1"] + ([selected, "--exact"] if selected else []), capture_output=True, text=True, timeout=30)

    def test_production_callback_and_memory_methods_execute_fault_boundaries(self):
        result = self.execute(self.generated())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("9 passed; 0 failed", result.stdout)
        print(result.stdout, end="")

    def test_compiled_oracles_reject_early_success_and_wrong_generation(self):
        source = self.generated()
        for old, new, selected in (
            ("Ok(()) => match smp_cpu::reconcile_shutdown(owner)", "Ok(()) => match Ok::<(), kernel::Error>(())", "success_requires_both_logical_commits_and_boot_retirement"),
            ("if image.owner != owner { return Err(EIO); }", "if false { return Err(EIO); }", "wrong_generation_cannot_close_or_reconcile_foreign_owner"),
            ("boot.started = false;", "boot.started = true;", "success_requires_both_logical_commits_and_boot_retirement"),
            ("Err(error) => Err(ShutdownIrqFailure::PreEffect(error))", "Err(error) => Err(ShutdownIrqFailure::PostEffect(error))", "pre_begin_failure_is_rollback_safe_and_retryable"),
        ):
            with self.subTest(selected=selected, mutation=old):
                self.assertEqual(source.count(old), 1)
                result = self.execute(source.replace(old, new, 1), selected)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("assertion", result.stdout + result.stderr)
                print("compiled mutation rejected:", old)

    def test_production_callback_closes_senders_before_reset(self) -> None:
        source = SOURCE.read_text()
        body = callback_body(source)
        close = body.index("shutdown_close_irq_senders")
        reset = body.index("shutdown_reset_and_reonline_outcome")
        self.assertLess(close, reset)
        self.assertIn("Err(smp_memory::ShutdownIrqFailure::PreEffect(error))", body)
        self.assertIn("return error.to_errno() as i64;", body)
        self.assertIn("Err(smp_memory::ShutdownIrqFailure::PostEffect(error))", body)
        self.assertIn("return shutdown_v6_post_effect(error);", body)
        self.assertIn("Err(smp_cpu::ShutdownResetFailure::PreEffect(error)) => shutdown_v6_post_effect(error)", body)
        self.assertIn("Err(smp_cpu::ShutdownResetFailure::PostEffect(error)) => shutdown_v6_post_effect(error)", body)

    def test_mutations_cannot_make_post_effect_failure_rollback_safe(self) -> None:
        source = SOURCE.read_text()
        body = callback_body(source)
        self.assertNotIn(
            "Err(smp_memory::ShutdownIrqFailure::PostEffect(error)) => return error.to_errno() as i64,",
            body,
        )
        self.assertNotIn(
            "Err(smp_cpu::ShutdownResetFailure::PostEffect(error)) => error.to_errno() as i64",
            body,
        )
        self.assertNotIn(
            "shutdown_reset_and_reonline_outcome(owner) {\n        match smp_memory::shutdown_close_irq_senders(owner)",
            body,
        )


if __name__ == "__main__":
    unittest.main()
