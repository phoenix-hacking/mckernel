"""Layer-B source/body execution for native shutdown CPU reclamation.

The Rust driver is generated from the exact journal implementation in
``smp_cpu.rs``. It has no copied journal model. It cannot invoke Linux CPU
hotplug, so source assertions bind its executable journal semantics to the
production method's guard/order/no-rollback boundary.
"""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "host-kernel/native-rust/smp_cpu.rs"
FIXTURE = ROOT / "scripts/tests/fixtures/shutdown_cpu_reclaim.rs"


def balanced_item(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError("unclosed Rust item")


class ShutdownCpuReclaimTests(unittest.TestCase):
    maxDiff = None

    def source_journal(self) -> str:
        text = SOURCE.read_text(encoding="utf-8")
        wrapper_marker = "#[derive(Clone, Copy, Debug, Eq, PartialEq)]\nstruct RetainedCpuDevice"
        wrapper_start = text.index(wrapper_marker)
        wrapper = text[wrapper_start:text.index(";", wrapper_start) + 1]
        wrapper_impl = balanced_item(text, "impl RetainedCpuDevice")
        stage = balanced_item(text, "#[derive(Clone, Copy, Debug, Eq, PartialEq)]\nenum ShutdownCpuFailureStage")
        journal = balanced_item(text, "#[derive(Clone, Copy, Debug, Eq, PartialEq)]\nstruct ShutdownCpuJournal")
        journal_impl = balanced_item(text, "impl ShutdownCpuJournal")
        fence = balanced_item(text, "fn shutdown_journal_blocks_ordinary_use(")
        return "\n\n".join((
            wrapper,
            "unsafe impl Send for RetainedCpuDevice {}",
            "unsafe impl Sync for RetainedCpuDevice {}",
            wrapper_impl,
            stage,
            journal,
            journal_impl,
            fence,
        ))

    def test_exact_production_journal_executes_semantic_cases(self) -> None:
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92")
        if not rustc:
            self.skipTest("MCKERNEL_RUSTC_1_92 is required for this exact Rust 1.92 fixture")
        version = subprocess.run([rustc, "--version"], capture_output=True, text=True, timeout=15)
        self.assertEqual(0, version.returncode, version.stdout + version.stderr)
        self.assertIn("rustc 1.92.0", version.stdout)
        template = FIXTURE.read_text(encoding="utf-8")
        self.assertEqual(1, template.count("// PRODUCTION_SHUTDOWN_CPU_CONTROL"))
        generated = template.replace("// PRODUCTION_SHUTDOWN_CPU_CONTROL", self.source_journal())
        with tempfile.TemporaryDirectory(prefix="shutdown-cpu-reclaim-") as directory:
            source = Path(directory) / "shutdown_cpu_reclaim.rs"
            binary = Path(directory) / "shutdown_cpu_reclaim"
            source.write_text(generated, encoding="utf-8")
            result = subprocess.run(
                [rustc, "--edition=2021", "--test", "-Dwarnings", str(source), "-o", str(binary)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_production_body_is_guarded_ordered_and_never_rolls_back(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        body = balanced_item(text, "fn shutdown_reset_and_reonline(")
        for token in (
            "shutdown_journal_blocks_ordinary_use(&self.shutdown_journal)",
            "self.prevalidate_shutdown_targets(owner, count, hotplug)?;",
            "before the first record",
            "CpuReadGuard::lock()",
            "native_reset_secondary_cpu_via_init(record.apic_id)",
            "bindings::device_online(record.device.0)",
            "self.shutdown_journal[index].online_status(status);",
            "if status != 0",
            "validate_shutdown_target(owner, record, true",
            "ShutdownCpuFailureStage::DeviceOnline",
            "self.retain_shutdown_failure(",
        ):
            self.assertIn(token, body)
        self.assertNotIn("execute_hotplug", body)
        self.assertNotIn("device_offline", body)
        self.assertNotIn("prepare_release", body)
        self.assertNotIn("smp_resource", body)
        self.assertNotIn("PreemptDisableGuard", body)
        self.assertNotIn("preempt_disable", body)
        self.assertNotIn("preempt_enable", body)
        self.assertNotIn("device_offline", body)
        self.assertLess(body.index("for index in 0..count {\n            let cpu = self.requests[index];"), body.index("let read = CpuReadGuard::lock();"))
        self.assertLess(body.index("native_reset_secondary_cpu_via_init(record.apic_id)"), body.index("bindings::device_online(record.device.0)"))
        self.assertIn(
            "record.reset_attempted();\n            }\n        }\n\n"
            "        // CPU read-side exclusion is gone here. The wrapper's preemption",
            body,
        )

    def test_reset_wrapper_is_the_only_pending_native_symbol(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        declaration = "fn native_reset_secondary_cpu_via_init(phys_apicid: u32);"
        self.assertEqual(1, text.count(declaration))
        self.assertNotIn("fn send_init_sequence(phys_apicid: u32);", text)
        self.assertNotIn("bindings::preempt_disable", text)
        self.assertNotIn("bindings::preempt_enable", text)

    def test_bsp_online_and_identity_controls_are_present_before_effects(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        validation = balanced_item(text, "fn validate_shutdown_target(")
        for token in (
            "cpu == 0",
            "slot.state() != CpuState::Assigned",
            "slot.owner() != Some(owner)",
            "current != record.device",
            "actual.hardware_id != record.apic_id",
            "actual.numa_node != record.numa_node",
            "actual.online != expected_online",
        ):
            self.assertIn(token, validation)

    def test_production_context_has_a_narrow_send_sync_journal_and_ordinary_fence(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("struct RetainedCpuDevice(*mut bindings::device);", text)
        self.assertIn("unsafe impl Send for RetainedCpuDevice {}", text)
        self.assertIn("unsafe impl Sync for RetainedCpuDevice {}", text)
        self.assertIn("shutdown_journal: [ShutdownCpuJournal; SMP_MAX_CPUS]", text)
        verify = balanced_item(text, "fn verify_owned(")
        self.assertIn("shutdown_journal_blocks_ordinary_use(&self.shutdown_journal)", verify)
        self.assertIn("self.poisoned = true;", verify)
        entry = balanced_item(text, "pub(super) fn shutdown_reset_and_reonline(")
        self.assertIn("#[allow(dead_code)] // Intentionally unwired until the v5 STOP/ACK drain owns it.", text)
        self.assertIn("context.shutdown_reset_and_reonline(owner, &hotplug)", entry)

    def test_prevalidation_and_raw_online_status_are_fail_closed(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        preflight = balanced_item(text, "fn prevalidate_shutdown_targets(")
        self.assertIn("ok_or(ENODEV)?", preflight)
        self.assertIn("slot.owner() != Some(owner)", preflight)
        self.assertIn("actual.online", preflight)
        body = balanced_item(text, "fn shutdown_reset_and_reonline(")
        self.assertLess(body.index("self.prevalidate_shutdown_targets(owner, count, hotplug)?;"), body.index("self.shutdown_journal[index].record("))
        self.assertIn("online_status: i32", text)
        self.assertIn("first_failure_stage: ShutdownCpuFailureStage", text)
        self.assertIn("kernel::error::to_result(status).unwrap_err()", body)
        self.assertIn("let failure = if status < 0", body)


if __name__ == "__main__":
    unittest.main()
