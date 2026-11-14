"""Focused source proof for the native STOP owner ABI boundary.

This is deliberately a negative fixture: it must establish that the current
v5 callback cannot safely carry an irreversible STOP transaction.  It does
not build a module, invoke a provider, or claim shutdown acceptance.
"""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "host-kernel/native-rust/os_runtime.rs"
SMP = ROOT / "host-kernel/native-rust/ihk_smp_x86_64.rs"
CPU = ROOT / "host-kernel/native-rust/smp_cpu.rs"
DESIGN = ROOT / "docs/verification/stability-native-shutdown-stop-ack-design-review-20260928-1.json"
RUSTC_DEFAULT = Path(
    "/home/holden/mckernel-work/toolchains/rustup/toolchains/"
    "1.92.0-x86_64-unknown-linux-gnu/bin/rustc"
)


def rustc_192() -> str:
    configured = os.environ.get("MCKERNEL_RUSTC_1_92")
    compiler = Path(configured) if configured else RUSTC_DEFAULT
    if not compiler.is_file():
        raise unittest.SkipTest("pinned Rust 1.92 compiler is unavailable")
    version = subprocess.run(
        [str(compiler), "--version"], capture_output=True, text=True, timeout=15
    )
    if version.returncode != 0 or "rustc 1.92.0" not in version.stdout:
        raise unittest.SkipTest("configured compiler is not Rust 1.92.0")
    return str(compiler)


def assert_v5_contract(test: unittest.TestCase, text: str) -> None:
    """Check the exact source properties which make the ABI fail closed."""
    test.assertIn(
        "type OsBackendShutdownV5 = unsafe extern \"C\" fn(u32, u64) -> i32;",
        text,
    )
    outcome_start = text.index("fn shutdown_v5_outcome")
    # v6 adds a tagged post-effect result between the legacy mapper and the
    # transaction body; the v5 proof must remain scoped to its own mapper.
    outcome_end = text.index("fn shutdown_v6_outcome", outcome_start)
    outcome = text[outcome_start:outcome_end]
    test.assertIn("if result == 0", outcome)
    test.assertIn("ShutdownCallbackOutcome::Complete", outcome)
    test.assertIn("ShutdownCallbackOutcome::PreEffectFailure(result)", outcome)
    test.assertNotIn("ShutdownCallbackOutcome::PostEffectFailure(result)", outcome)

    start = text.index("fn finish_shutdown(")
    end = text.index("/// The raw pointer is valid", start)
    body = text[start:end]
    pre = body.index("ShutdownCallbackOutcome::PreEffectFailure(result)")
    post = body.index("ShutdownCallbackOutcome::PostEffectFailure(result)")
    pre_arm = body[pre:post]
    test.assertNotIn("admission.commit();", pre_arm)
    test.assertIn("shutdown_errno(result)", pre_arm)
    test.assertIn("admission.commit();", body[post:])
    test.assertIn("guard.mark_irreversible()", body[post:])

    drop_start = text.index("impl Drop for ShutdownAdmission")
    drop_end = text.index("}\n\n/// Finish one shutdown transaction", drop_start) + 1
    drop = text[drop_start:drop_end]
    test.assertIn("if !self.armed || !self.reopen_on_drop", drop)
    test.assertIn("reopen_unpoisoned()", drop)


def assert_v6_post_effect_contract(test: unittest.TestCase, text: str) -> None:
    """Keep the v5 fixture useful after the additive v6 provider migration."""
    start = text.index("fn shutdown_v6_outcome")
    end = text.index("fn shutdown_errno", start)
    outcome = text[start:end]
    test.assertIn("ShutdownCallbackOutcome::PostEffectFailure(payload)", outcome)
    test.assertIn("IHK_SMP_SHUTDOWN_V6_POST_EFFECT", outcome)


TRANSACTION_MODEL = r'''
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Outcome { Complete, Pre(i32), Post(i32) }

struct Admission { closed: bool, reopened: u32 }

struct Guard { committed: bool, irreversible: bool, fail_commit: bool }
impl Guard {
    fn commit(&mut self) -> Result<(), i32> {
        if self.fail_commit { Err(-5) } else { self.committed = true; Ok(()) }
    }
    fn mark_irreversible(&mut self) -> Result<(), i32> {
        self.irreversible = true; Ok(())
    }
}

struct Claim<'a> { admission: &'a mut Admission, reopen_on_drop: bool, armed: bool }
impl<'a> Claim<'a> {
    fn commit(mut self) { self.armed = false; }
}
impl Drop for Claim<'_> {
    fn drop(&mut self) {
        if !self.armed || !self.reopen_on_drop { return; }
        self.admission.closed = false;
        self.admission.reopened += 1;
    }
}

fn finish(mut guard: Guard, claim: Claim<'_>, outcome: Outcome) -> i32 {
    match outcome {
        Outcome::Complete => match guard.commit() {
            Ok(()) => { claim.commit(); 0 }
            Err(error) => { claim.commit(); error }
        },
        Outcome::Pre(result) => result,
        Outcome::Post(result) => {
            claim.commit();
            if let Err(error) = guard.mark_irreversible() { return error; }
            result
        }
    }
}

#[test]
fn transaction_semantics_are_effect_aware() {
    let mut admission = Admission { closed: true, reopened: 0 };
    let result = finish(
        Guard { committed: false, irreversible: false, fail_commit: false },
        Claim { admission: &mut admission, reopen_on_drop: true, armed: true },
        Outcome::Complete,
    );
    assert_eq!(result, 0);
    assert!(admission.closed);
    assert_eq!(admission.reopened, 0);

    let mut admission = Admission { closed: true, reopened: 0 };
    let result = finish(
        Guard { committed: false, irreversible: false, fail_commit: false },
        Claim { admission: &mut admission, reopen_on_drop: true, armed: true },
        Outcome::Pre(-110),
    );
    assert_eq!(result, -110);
    assert!(!admission.closed);
    assert_eq!(admission.reopened, 1);

    let mut admission = Admission { closed: true, reopened: 0 };
    let result = finish(
        Guard { committed: false, irreversible: false, fail_commit: false },
        Claim { admission: &mut admission, reopen_on_drop: true, armed: true },
        Outcome::Post(-110),
    );
    assert_eq!(result, -110);
    assert!(admission.closed);
    assert_eq!(admission.reopened, 0);
}
'''


class NativeShutdownV5AbiBlockerTests(unittest.TestCase):
    def test_v5_nonzero_is_unconditionally_pre_effect(self):
        text = RUNTIME.read_text(encoding="utf-8")
        assert_v5_contract(self, text)

    def test_actual_effect_aware_transaction_model_runs_on_rust_192(self):
        compiler = rustc_192()
        with tempfile.TemporaryDirectory(prefix="native-shutdown-v5-abi-") as directory:
            source = Path(directory) / "transaction.rs"
            binary = Path(directory) / "transaction"
            source.write_text(TRANSACTION_MODEL, encoding="utf-8")
            compiled = subprocess.run(
                [compiler, "--edition=2021", "--test", "-Dwarnings", str(source), "-o", str(binary)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(0, compiled.returncode, compiled.stdout + compiled.stderr)
            executed = subprocess.run(
                [str(binary)], capture_output=True, text=True, timeout=30,
                env={**os.environ, "RUST_TEST_THREADS": "1"},
            )
            self.assertEqual(0, executed.returncode, executed.stdout + executed.stderr)
            self.assertIn("1 passed", executed.stdout)

    def test_decisive_in_memory_mutations_are_rejected(self):
        original = RUNTIME.read_text(encoding="utf-8")
        mutations = {
            "pre-effect commit": (
                "ShutdownCallbackOutcome::PreEffectFailure(result) => shutdown_errno(result),",
                "ShutdownCallbackOutcome::PreEffectFailure(result) => { admission.commit(); shutdown_errno(result) },",
            ),
            "drop never reopens": (
                "unsafe { &*self.admission }.reopen_unpoisoned();",
                "/* admission reopening removed */",
            ),
            "v6 post-effect tag cannot be erased": (
                "return ShutdownCallbackOutcome::PostEffectFailure(payload);",
                "return ShutdownCallbackOutcome::PreEffectFailure(payload as i32);",
            ),
        }
        for name, (needle, replacement) in mutations.items():
            with self.subTest(mutation=name):
                self.assertIn(needle, original)
                mutated = original.replace(needle, replacement, 1)
                with self.assertRaises(AssertionError):
                    if name.startswith("v6 "):
                        assert_v6_post_effect_contract(self, mutated)
                    else:
                        assert_v5_contract(self, mutated)

    def test_pre_effect_error_reopens_gate_but_post_effect_would_commit(self):
        text = RUNTIME.read_text(encoding="utf-8")
        start = text.index("fn finish_shutdown(")
        end = text.index("/// The raw pointer is valid", start)
        body = text[start:end]
        pre = body.index("ShutdownCallbackOutcome::PreEffectFailure(result)")
        post = body.index("ShutdownCallbackOutcome::PostEffectFailure(result)")
        self.assertLess(pre, post)
        self.assertIn("shutdown_errno(result)", body[pre:post])
        self.assertIn("admission.commit();", body[post:])
        self.assertIn("guard.mark_irreversible()", body[post:])

    def test_native_provider_is_v6_and_cpu_stop_is_wired(self):
        smp = SMP.read_text(encoding="utf-8")
        cpu = CPU.read_text(encoding="utf-8")
        self.assertIn('ihk_os_create_unbooted_v6', smp)
        self.assertIn('Some(ihk_smp_shutdown_v6)', smp)
        self.assertIn('pub(super) fn shutdown_reset_and_reonline_outcome', cpu)
        self.assertIn('pub(super) fn reconcile_shutdown', cpu)

    def test_review_preserves_wire_and_ack_prerequisite(self):
        text = DESIGN.read_text(encoding="utf-8")
        self.assertIn('"status": "BLOCK_ABI_FREEZE"', text)
        self.assertIn('"current_stop_opcode": false', text)
        self.assertIn('"current_boot_session_identity": false', text)
        self.assertIn('"wire reservation authority"', text)
        self.assertIn('"implementation"', text)
        self.assertIn('"failure_rule": "timeout or any stale/malformed/missing ACK retains CPU assignments, RAM, mappings, queues, module pins and request ledger"', text)


if __name__ == "__main__":
    unittest.main()
