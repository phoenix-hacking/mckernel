"""Check credential refresh prerequisites before observable host mutations.

Compile only the three genuine affected Rust helpers. Observation callbacks
model effects; this establishes helper behavior, not runtime provider closure.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from scripts.tests.test_m14_f06_tail_codegen import definition

ROOT = Path(__file__).resolve().parents[2]
RUST_OBSERVER = r'''
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Synthetic callback observers only; no runtime credential/transport provider.
use std::sync::{Mutex, atomic::{AtomicI32, AtomicI64, AtomicU64, Ordering}};
static SERIAL: Mutex<()> = Mutex::new(());
static HOST_CALLS: AtomicI32 = AtomicI32::new(0);
static HOST_MUTATIONS: AtomicI32 = AtomicI32::new(0);
static REFRESHES: AtomicI32 = AtomicI32::new(0);
static HOST_RESULT: AtomicI64 = AtomicI64::new(0);
static HOST_ARG: AtomicU64 = AtomicU64::new(0);
unsafe extern "C" fn forward(_: CInt, _: *mut c_void) -> CLong {
    HOST_CALLS.fetch_add(1, Ordering::SeqCst);
    let result = HOST_RESULT.load(Ordering::SeqCst);
    if result == 0 { HOST_MUTATIONS.fetch_add(1, Ordering::SeqCst); }
    result
}
unsafe extern "C" fn setfsid(_: CInt, id: CULong, _: CULong) -> CLong {
    HOST_CALLS.fetch_add(1, Ordering::SeqCst);
    HOST_MUTATIONS.fetch_add(1, Ordering::SeqCst);
    HOST_ARG.store(id, Ordering::SeqCst);
    HOST_RESULT.load(Ordering::SeqCst)
}
unsafe extern "C" fn refresh() { REFRESHES.fetch_add(1, Ordering::SeqCst); }
fn reset(result: CLong) {
    HOST_CALLS.store(0, Ordering::SeqCst);
    HOST_MUTATIONS.store(0, Ordering::SeqCst);
    REFRESHES.store(0, Ordering::SeqCst);
    HOST_ARG.store(0, Ordering::SeqCst);
    HOST_RESULT.store(result, Ordering::SeqCst);
}
#[test]
fn missing_ordinary_refresh_performs_zero_host_mutations() {
    let _guard = SERIAL.lock().unwrap_or_else(|error| error.into_inner()); reset(0);
    assert_eq!(unsafe { syscall_forward_refresh_cred_body_result(117,
        core::ptr::null_mut(), Some(forward), None) }, -22);
    assert_eq!(HOST_CALLS.load(Ordering::SeqCst), 0);
    assert_eq!(HOST_MUTATIONS.load(Ordering::SeqCst), 0);
    assert_eq!(REFRESHES.load(Ordering::SeqCst), 0);
}
#[test]
fn missing_setfsid_refresh_performs_zero_host_mutations() {
    let _guard = SERIAL.lock().unwrap_or_else(|error| error.into_inner()); reset(1000);
    assert_eq!(unsafe { syscall_setfsid_body_result(2000, 122, Some(setfsid), None) },
        (-22_i64) as CULong);
    assert_eq!(HOST_CALLS.load(Ordering::SeqCst), 0);
    assert_eq!(HOST_MUTATIONS.load(Ordering::SeqCst), 0);
    assert_eq!(REFRESHES.load(Ordering::SeqCst), 0);
}
#[test]
fn valid_ordinary_callbacks_preserve_exact_host_result_and_refresh_rule() {
    let _guard = SERIAL.lock().unwrap_or_else(|error| error.into_inner());
    for result in [0, -1, -13, -4095, 7] {
        reset(result);
        assert_eq!(unsafe { syscall_forward_refresh_cred_body_result(117,
            core::ptr::null_mut(), Some(forward), Some(refresh)) }, result);
        assert_eq!(HOST_CALLS.load(Ordering::SeqCst), 1);
        assert_eq!(REFRESHES.load(Ordering::SeqCst), if result == 0 { 1 } else { 0 });
    }
}
#[test]
fn valid_setfsid_callbacks_preserve_previous_id_bits_and_refresh() {
    let _guard = SERIAL.lock().unwrap_or_else(|error| error.into_inner());
    for result in [0, 1000, i32::MAX as i64, -1] {
        reset(result);
        assert_eq!(unsafe { syscall_setfsid_body_result(-1, 122, Some(setfsid), Some(refresh)) },
            result as CULong);
        assert_eq!(HOST_ARG.load(Ordering::SeqCst), (-1_i32) as CULong);
        assert_eq!(HOST_CALLS.load(Ordering::SeqCst), 1);
        assert_eq!(REFRESHES.load(Ordering::SeqCst), 1);
    }
}
#[test]
fn missing_host_callback_remains_an_error_without_refresh() {
    let _guard = SERIAL.lock().unwrap_or_else(|error| error.into_inner()); reset(0);
    assert_eq!(unsafe { syscall_forward_refresh_cred_body_result(117,
        core::ptr::null_mut(), None, Some(refresh)) }, -22);
    assert_eq!(unsafe { syscall_setfsid_body_result(2000, 122, None, Some(refresh)) },
        (-22_i64) as CULong);
    assert_eq!(HOST_CALLS.load(Ordering::SeqCst), 0);
    assert_eq!(REFRESHES.load(Ordering::SeqCst), 0);
}
'''


def build_fixture(directory, source=None):
    policy = source if source is not None else (ROOT / "kernel/rust/syscall_policy.rs").read_text()
    abi = (ROOT / "kernel/rust/abi.rs").read_text()
    pieces = ["use core::ffi::c_void;"]
    for name in ("CInt", "CLong", "CULong"):
        pieces.append(re.search(r"(?m)^pub type " + name + r" = [^;]+;", abi).group())
    for name in ("SyscallRefreshCredFn", "SyscallDoSyscall2Fn", "SyscallForwardContextFn"):
        pieces.append(re.search(r"(?m)^type " + name + r" = [^;]+;", policy).group())
    pieces.append(re.search(r"(?m)^const EINVAL: CInt = [^;]+;", policy).group())
    for name in ("syscall_refresh_cred_needed_result", "syscall_forward_refresh_cred_body_result",
                 "syscall_setfsid_body_result"):
        pieces.append(definition(policy, name))
    pieces.append(RUST_OBSERVER)
    fixture = directory / "credential_preflight.rs"
    fixture.write_text("\n\n".join(pieces) + "\n")
    return fixture


class CredentialPreflightTests(unittest.TestCase):
    def test_missing_refresh_has_no_host_effect_and_valid_returns_are_preserved(self):
        compiler = os.environ.get("RUSTC") or shutil.which("rustc")
        if not compiler:
            self.skipTest("Rust compiler required")
        with tempfile.TemporaryDirectory(prefix="m14-credential-preflight-") as tmp:
            directory = Path(tmp)
            fixture = build_fixture(directory)
            binary = directory / "credential_preflight"
            compiled = subprocess.run([compiler, "--edition=2021", "--test", "-C", "opt-level=2",
                                       str(fixture), "-o", str(binary)],
                                      capture_output=True, text=True, timeout=45)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(binary), "--test-threads=1"],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("5 passed; 0 failed", result.stdout)


if __name__ == "__main__":
    unittest.main()
