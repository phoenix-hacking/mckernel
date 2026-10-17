"""Execute complete production shutdown bodies against explicit host boundaries.

This is a sequential unprivileged regression, never runtime acceptance.
"""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile
import unittest

from scripts.tests import test_native_shutdown_v6_provider_integration_20261001 as provider_fixture
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / "host-kernel/native-rust"
FIXTURE = ROOT / "scripts/tests/fixtures/native_shutdown_v6_actual_order_20261017.rs"
RUSTC = "/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc"
RUNTIME_ITEMS = (
    "struct Admission {", "impl Admission {", "struct ShutdownAdmission {",
    "impl ShutdownAdmission {", "impl Drop for ShutdownAdmission {",
    "struct AdmissionOwner {", "impl Drop for AdmissionOwner {",
    "enum ShutdownCallbackOutcome {", "fn shutdown_v6_outcome(",
    "fn shutdown_errno(", "fn finish_shutdown(",
)


def generated():
    runtime = (NATIVE / "os_runtime.rs").read_text()
    registry = (NATIVE / "os_registry.rs").read_text().split("#[cfg(test)]\nmod tests {", 1)[0]
    abi = (NATIVE / "abi/x86_64.rs").read_text()
    constants = "\n".join(line for line in abi.splitlines() if line.startswith("pub const IHK_OS_STATUS_"))
    provider = provider_fixture.NativeShutdownV6ProviderTests().generated()
    # The original complete production callback/memory bodies are unchanged;
    # instrument only explicitly stubbed CPU boundary implementations.
    hook = "pub fn shutdown_reset_and_reonline_outcome(_: OsToken) -> std::result::Result<(), ShutdownResetFailure> {"
    assert provider.count(hook) == 1
    provider = provider.replace(hook, hook + "\n        physical_boundary();", 1)
    hook = "pub fn reconcile_shutdown(owner: OsToken) -> Result {"
    assert provider.count(hook) == 1
    provider = provider.replace(hook, hook + "\n        reconcile_boundary();", 1)
    provider = provider.replace("fn setup() {", "fn setup() {\n    ACTIVE.store(false, Ordering::Relaxed);\n    OWNER_GENERATION.store(9, Ordering::Relaxed);", 1)
    provider = provider.replace("fn owner() -> OsToken { OsToken { slot: 0, generation: 9 } }",
        "fn owner() -> OsToken { OsToken { slot: 0, generation: OWNER_GENERATION.load(Ordering::Relaxed) } }", 1)
    provider = provider.replace("fn invoke() -> i64 { unsafe { ihk_smp_shutdown_v6(0, 9) } }",
        "fn invoke() -> i64 { unsafe { ihk_smp_shutdown_v6(owner().slot, owner().generation) } }", 1)
    return FIXTURE.read_text().replace("// PROVIDER_FIXTURE", provider).replace(
        "// PRODUCTION_ABI", constants).replace("// PRODUCTION_REGISTRY", registry).replace(
        "// PRODUCTION_RUNTIME", "\n".join(balanced_item(runtime, marker) for marker in RUNTIME_ITEMS))


class ActualShutdownOrderTests(unittest.TestCase):
    def test_extraction_is_complete_and_has_no_unexpanded_slots(self):
        source = generated()
        self.assertNotIn("// PRODUCTION_", source)
        self.assertNotIn("// PROVIDER_FIXTURE", source)
        for marker in RUNTIME_ITEMS:
            self.assertIn(balanced_item((NATIVE / "os_runtime.rs").read_text(), marker), source)
        self.assertIn("pub(crate) fn begin_shutdown(", source)
        self.assertIn("impl Drop for ShutdownGuard<'_>", source)

    def test_actual_bodies_and_negative_oracles(self):
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92", RUSTC)
        version = subprocess.run([rustc, "--version"], capture_output=True, text=True, timeout=15, check=True)
        self.assertIn("rustc 1.92.0", version.stdout)
        source = generated()
        variants = [
            ("actual", source, None),
            ("omit_physical_stop", source.replace(
                    "match smp_cpu::shutdown_reset_and_reonline_outcome(owner) {",
                    "match Ok::<(), smp_cpu::ShutdownResetFailure>(()) {", 1), "actual_order_success"),
            ("post_effect_as_pre_effect", source.replace(
                "return ShutdownCallbackOutcome::PostEffectFailure(payload);",
                "return ShutdownCallbackOutcome::PreEffectFailure(payload);", 1), "actual_order_post_effect_retains_registry_and_admission"),
            ("omit_irreversible_publication", source.replace(
                "self.irreversible = true;", "self.irreversible = false;", 1), "actual_order_post_effect_retains_registry_and_admission"),
        ]
        mutation_oracles = {
            "omit_physical_stop": (-6, ("reconcile before physical reset/reonline", "panic in a function that cannot unwind")),
            "post_effect_as_pre_effect": (101, ("assertion failed: runtime::closed()",)),
            "omit_irreversible_publication": (101, ("assertion `left == right` failed", "left: Running", "right: Shutdown")),
        }
        # Preserve every materialization, compiler result and failed oracle.
        directory = Path(tempfile.mkdtemp(prefix="shutdown-actual-order-"))
        print(f"retained_fixture_root={directory}", flush=True)
        for name, content, selected in variants:
            with self.subTest(variant=name):
                if selected:
                    self.assertNotEqual(content, source)
                path, binary = directory / f"{name}.rs", directory / name
                path.write_text(content)
                compile_result = subprocess.run([rustc, "--edition=2021", "--test", "-Dwarnings", str(path), "-o", str(binary)],
                                                capture_output=True, text=True, timeout=30)
                for stream in ("stdout", "stderr"):
                    (directory / f"{name}.compile.{stream}").write_text(getattr(compile_result, stream))
                (directory / f"{name}.compile.status").write_text(str(compile_result.returncode) + "\n")
                self.assertEqual(compile_result.returncode, 0, compile_result.stdout + compile_result.stderr)
                run = subprocess.run([str(binary), "--test-threads=1"] + ([selected, "--exact"] if selected else []),
                                     capture_output=True, text=True, timeout=15)
                for stream in ("stdout", "stderr"):
                    (directory / f"{name}.run.{stream}").write_text(getattr(run, stream))
                (directory / f"{name}.run.status").write_text(str(run.returncode) + "\n")
                output = run.stdout + run.stderr
                if selected:
                    expected_status, diagnostics = mutation_oracles[name]
                    self.assertEqual(run.returncode, expected_status, output)
                    for diagnostic in diagnostics:
                        self.assertIn(diagnostic, output)
                else:
                    self.assertEqual(run.returncode, 0, output)
                    self.assertIn("13 passed; 0 failed", output)
                print(f"{name}: source_sha256={hashlib.sha256(content.encode()).hexdigest()} exit={run.returncode}\n{output}")


if __name__ == "__main__":
    unittest.main()
