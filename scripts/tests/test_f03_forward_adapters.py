"""Focused candidate checks; these are not ABI/link/native acceptance.

The behavioral fixture uses RUSTC when supplied, otherwise rustc from PATH,
and skips when no compiler is available. It is an isolated local unit test;
it does not build, install or execute the production kernel.
The fixture uses the real ABI source, candidate module and forwarding builder;
its observation providers are test doubles, never production/link evidence.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "kernel/rust/f03_forward_adapters.rs"
POLICY = ROOT / "kernel/rust/syscall_policy.rs"


def rust_function(text, name):
    """Extract a known brace-balanced Rust body, without modifying its source."""
    begin = text.index("pub unsafe extern \"C\" fn " + name + "(")
    opening = text.index("{", begin)
    depth = 1
    cursor = opening + 1
    while depth:
        depth += (text[cursor] == "{") - (text[cursor] == "}")
        cursor += 1
    return text[begin:cursor]


class ForwardAdaptersTests(unittest.TestCase):
    def test_actual_wait_consumers_only_read_pid_and_options(self):
        source = (ROOT / "executer/user/mcexec.c").read_text()
        c_wait = source.split("case __NR_wait4: {", 1)[1].split("case __NR_execve:", 1)[0]
        rust_wait = rust_function(
            (ROOT / "executer/user/rust/mcexec_helpers.rs").read_text(), "act_wait4")
        for body in (c_wait, rust_wait):
            self.assertIn("args[0]", body)
            self.assertIn("args[2]", body)
            for index in (1, 3, 4, 5):
                self.assertNotIn("args[" + str(index) + "]", body)

    def test_behavioral_fixture(self):
        compiler = os.environ.get("RUSTC") or shutil.which("rustc")
        if compiler is None:
            self.skipTest("Rust compiler unavailable")
        builder = rust_function(POLICY.read_text(), "syscall_generic_forwarding_body_result")
        harness = r'''
#[path = "@ABI@"] mod abi;
mod syscall_policy {
    use crate::abi::{CInt, CLong, CULong, SyscallRequest};
    use core::ptr::{addr_of_mut, write};
    const EINVAL: CInt = 22;
    type SyscallRequestCallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;
    @BUILDER@
}
mod x86_local {
    use core::sync::atomic::{AtomicUsize, Ordering};
    pub static CALLS: AtomicUsize = AtomicUsize::new(0);
    pub unsafe fn ihk_mc_get_processor_id() -> i32 {
        CALLS.fetch_add(1, Ordering::SeqCst);
        -17
    }
}
#[path = "@MODULE@"] mod adapters;
use abi::{CInt, CLong, CULong, SyscallRequest};
use core::sync::atomic::{AtomicI64, AtomicUsize, Ordering};
use std::sync::Mutex;
const _: unsafe extern "C" fn(CInt, CULong, CULong) -> CLong = adapters::syscall_do_syscall2_bridge;
const _: unsafe extern "C" fn(CInt, CULong, CULong, CULong) -> CLong = adapters::syscall_do_syscall3_bridge;
const _: unsafe extern "C" fn(CInt, CULong, CULong) -> CLong = adapters::syscall_policy_do_syscall2_bridge;
const _: unsafe extern "C" fn(CInt, CULong, CULong, CULong) -> CLong = adapters::syscall_policy_do_syscall3_bridge;
const _: unsafe extern "C" fn(CInt, CInt) -> CInt = adapters::wait_host_wait4_bridge;
static EXPECTED: Mutex<(u64, [u64; 6])> = Mutex::new((0, [0; 6]));
static RESULT: AtomicI64 = AtomicI64::new(0);
static TRANSACTIONS: AtomicUsize = AtomicUsize::new(0);
#[no_mangle]
unsafe extern "C" fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong {
    assert_eq!(cpu, -17);
    assert!(!request.is_null());
    assert_eq!(request as usize % core::mem::align_of::<SyscallRequest>(), 0);
    TRANSACTIONS.fetch_add(1, Ordering::SeqCst);
    let expected = *EXPECTED.lock().unwrap();
    // The caller is blocked in join while another thread reads its live request.
    // This is only a fixture check of synchronous stack storage lifetime.
    let address = request as usize;
    std::thread::spawn(move || {
        std::thread::yield_now();
        let request = unsafe { &*(address as *const SyscallRequest) };
        assert_eq!((request.rtid, request.ttid, request.valid), (0, 0, 0));
        assert_eq!(request.number, expected.0);
        assert_eq!(request.args, expected.1);
    }).join().unwrap();
    // The real provider mutates metadata; every later transaction must start zero.
    unsafe { (*request).rtid = -1; (*request).ttid = 99; (*request).valid = 1; }
    RESULT.load(Ordering::SeqCst)
}
fn expect(number: CInt, args: [CULong; 6], result: CLong) {
    *EXPECTED.lock().unwrap() = (number as CULong, args);
    RESULT.store(result, Ordering::SeqCst);
}
#[test]
fn signed_values_full_results_zero_slots_and_one_transaction() {
    let high = 0x8000_0000_ffff_ffff;
    let tail = 0xffff_ffff_8000_0000;
    for number in [i32::MIN, -1, 0, i32::MAX] {
        for result in [i64::MIN, -4095, -1, 0, 0x1_8000_0001, i64::MAX] {
            expect(number, [high, tail, 0, 0, 0, 0], result);
            let before = TRANSACTIONS.load(Ordering::SeqCst);
            let cpus = x86_local::CALLS.load(Ordering::SeqCst);
            assert_eq!(unsafe { adapters::syscall_do_syscall2_bridge(number, high, tail) }, result);
            assert_eq!(unsafe { adapters::syscall_policy_do_syscall2_bridge(number, high, tail) }, result);
            expect(number, [high, tail, 0x1234_5678_9abc_def0, 0, 0, 0], result);
            assert_eq!(unsafe { adapters::syscall_do_syscall3_bridge(number, high, tail, 0x1234_5678_9abc_def0) }, result);
            assert_eq!(unsafe { adapters::syscall_policy_do_syscall3_bridge(number, high, tail, 0x1234_5678_9abc_def0) }, result);
            assert_eq!(TRANSACTIONS.load(Ordering::SeqCst), before + 4);
            assert_eq!(x86_local::CALLS.load(Ordering::SeqCst), cpus + 4);
        }
    }
    for pid in [i32::MIN, -1, 0, i32::MAX] {
        for options in [i32::MIN, -1, 0, i32::MAX] {
            for result in [i64::MIN, -4095, -1, 0, 0x1_8000_0001, i64::MAX] {
                expect(61, [pid as CULong, 0, options as CULong, 0, 0, 0], result);
                let before = TRANSACTIONS.load(Ordering::SeqCst);
                let cpus = x86_local::CALLS.load(Ordering::SeqCst);
                assert_eq!(unsafe { adapters::wait_host_wait4_bridge(pid, options) }, result as CInt);
                assert_eq!(TRANSACTIONS.load(Ordering::SeqCst), before + 1);
                assert_eq!(x86_local::CALLS.load(Ordering::SeqCst), cpus + 1);
            }
        }
    }
}
'''
        harness = harness.replace("@ABI@", str(ROOT / "kernel/rust/abi.rs"))
        harness = harness.replace("@MODULE@", str(MODULE)).replace("@BUILDER@", builder)
        with tempfile.TemporaryDirectory(prefix="f03-forward-adapters-") as directory:
            source = Path(directory) / "fixture.rs"
            binary = Path(directory) / "fixture"
            source.write_text(harness)
            compile_result = subprocess.run(
                [compiler, "--edition=2021", "--test", str(source), "-o", str(binary)],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(compile_result.returncode, 0, compile_result.stdout + compile_result.stderr)
            result = subprocess.run([str(binary), "--test-threads=1"], capture_output=True,
                                    text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
