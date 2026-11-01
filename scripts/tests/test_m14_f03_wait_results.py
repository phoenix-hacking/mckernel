"""Isolated actual-source regression for wait copyout and siginfo results.

The extracted eligible Rust helpers use the real ABI module. The wait/usercopy
callbacks only observe synthetic results; this is not native/link acceptance.
Expected status decoding and WNOHANG fields follow Linux wait(2):
https://www.man7.org/linux/man-pages/man2/waitpid.2.html
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "kernel/rust/syscall_policy.rs"


def function(source, name):
    match = re.search(r"^(?:pub )?(?:unsafe )?(?:extern \"C\" )?fn " + name + r"\(",
                      source, re.M)
    if match is None:
        raise ValueError("Missing actual helper: " + name)
    opening = source.index("{", match.start())
    cursor, depth = opening + 1, 1
    while depth:
        depth += (source[cursor] == "{") - (source[cursor] == "}")
        cursor += 1
    return source[match.start():cursor]


class WaitResultsTests(unittest.TestCase):
    def test_actual_wait_helpers(self):
        compiler = os.environ.get("RUSTC") or shutil.which("rustc")
        if compiler is None:
            self.skipTest("Rust compiler unavailable")
        source = POLICY.read_text()
        names = [
            "wait4_options_result", "wait_status_copy_needed_result",
            "wait_rusage_copy_needed_result", "zero_rusage", "wait4_body_result",
            "waitid_siginfo_needed_result", "waitid_status_code_result",
            "timeval_to_jiffy_result", "waitid_copy_siginfo_result",
            "waitid_to_wait_pid_result", "waitid_options_result", "waitid_body_result",
            "wait_process_pid_matches_result", "wait_should_scan_thread_result",
            "wait_stopped_status_result", "wait_nonptraced_stop_candidate_result",
            "wait_ptraced_stop_candidate_result", "wait_continued_candidate_result",
            "wait_thread_exited_candidate_result", "wait_reap_needed_result",
            "wait_thread_reap_action_result", "wait_process_candidate_body_result",
            "wait_thread_candidate_body_result",
        ]
        constants = ["EINVAL", "EFAULT", "ESRCH", "WNOHANG", "WUNTRACED", "WSTOPPED",
                     "WCONTINUED", "WEXITED", "WNOWAIT", "__WCLONE", "__WALL",
                     "P_ALL", "P_PID", "P_PGID", "SIGCHLD", "SIGCONT", "CLD_EXITED",
                     "CLD_KILLED", "CLD_DUMPED", "CLD_STOPPED", "CLD_CONTINUED",
                     "CLD_TRAPPED", "NSIG", "PT_TRACED", "PS_STOPPED", "PS_TRACED",
                     "PS_ZOMBIE", "PS_EXITED", "PS_DELAY_TRACED", "SIGNAL_STOP_STOPPED",
                     "SIGNAL_STOP_CONTINUED", "WAIT_THREAD_REAP_ACTION_NONE",
                     "WAIT_THREAD_REAP_ACTION_RELEASE", "WAIT_THREAD_REAP_ACTION_PTRACE_DETACH"]
        declarations = []
        for name in constants:
            match = re.search(r"^const " + name + r": CInt = .*?;", source, re.M)
            if match is None:
                raise ValueError("Missing actual constant: " + name)
            declarations.append(match.group(0))
        sentinel = re.search(r"^const WAIT_PGID_ONE: CInt = .*?;", source, re.M)
        if sentinel:
            declarations.append(sentinel.group(0))
        tag = re.search(r"^const WAIT_STATUS_PTRACED_STOP: CInt = .*?;", source, re.M)
        if tag:
            declarations.append(tag.group(0))
        aliases = []
        for name in ("WaitStatusFn", "WaitLockUnlockFn", "WaitThreadReportDetachFn",
                     "WaitThreadSideEffectFn", "WaitSignalFlagsReapFn"):
            match = re.search(r"^type " + name + r"\s*=[^;]+;", source, re.M)
            if match is None:
                raise ValueError("Missing actual callback type: " + name)
            aliases.append(match.group(0))
        harness = r'''
#[path = "@ABI@"] mod abi;
use abi::{CInt, CLong, CULong, SizeT, RUsage, SigInfo, SigInfoChild};
use core::mem::{size_of, MaybeUninit, ManuallyDrop};
use core::ffi::c_void;
use core::ptr::write;
use core::sync::atomic::{AtomicI32, AtomicUsize, Ordering};
use std::sync::Mutex;
type SyscallCopyToUserFn = unsafe extern "C" fn(CULong, *const u8, SizeT) -> CLong;
type Wait4DoWaitFn = unsafe extern "C" fn(CInt, *mut CInt, CInt, *mut RUsage) -> CInt;
@CONSTANTS@
@ALIASES@
@FUNCTIONS@
static WAIT_RESULT: AtomicI32 = AtomicI32::new(42);
static WAIT_STATUS: AtomicI32 = AtomicI32::new(7 << 8);
static FAIL_COPY: AtomicUsize = AtomicUsize::new(0);
static FAILURE_VALUE: AtomicI32 = AtomicI32::new(-14);
static WAIT_CALLS: AtomicUsize = AtomicUsize::new(0);
static COPIES: Mutex<Vec<(u64, Vec<u8>)>> = Mutex::new(Vec::new());
unsafe extern "C" fn observe_wait(_pid: CInt, status: *mut CInt,
                                  _options: CInt, usage: *mut RUsage) -> CInt {
    WAIT_CALLS.fetch_add(1, Ordering::SeqCst);
    unsafe {
        *status = WAIT_STATUS.load(Ordering::SeqCst);
        (*usage).ru_utime.tv_sec = 3;
        (*usage).ru_stime.tv_sec = 5;
    }
    WAIT_RESULT.load(Ordering::SeqCst)
}
unsafe extern "C" fn observe_copy(address: CULong, data: *const u8, size: SizeT) -> CLong {
    let bytes = unsafe { core::slice::from_raw_parts(data, size) }.to_vec();
    let mut copies = COPIES.lock().unwrap();
    copies.push((address, bytes));
    if copies.len() == FAIL_COPY.load(Ordering::SeqCst) {
        FAILURE_VALUE.load(Ordering::SeqCst) as CLong
    } else { 0 }
}
fn reset(rc: CInt, status: CInt, fail_at: usize, failure_value: CInt) {
    COPIES.lock().unwrap().clear();
    WAIT_CALLS.store(0, Ordering::SeqCst);
    WAIT_RESULT.store(rc, Ordering::SeqCst);
    WAIT_STATUS.store(status, Ordering::SeqCst);
    FAIL_COPY.store(fail_at, Ordering::SeqCst);
    FAILURE_VALUE.store(failure_value, Ordering::SeqCst);
}
fn wait4(status_addr: u64, usage_addr: u64) -> i64 {
    unsafe { wait4_body_result(-1, status_addr, WNOHANG, usage_addr, observe_wait, observe_copy) }
}
fn waitid(info_addr: u64) -> i64 {
    unsafe { waitid_body_result(P_ALL, 0, info_addr, WEXITED | WSTOPPED | WCONTINUED | WNOHANG,
                               observe_wait, observe_copy) }
}
#[test]
fn wait4_status_copy_failure_is_efault_and_stops_copyout() {
    for failure in [-14, 1, 37] {
        reset(42, 7 << 8, 1, failure);
        assert_eq!(wait4(0x1000, 0x2000), -14, "failure={failure}");
        assert_eq!(COPIES.lock().unwrap().len(), 1);
        assert_eq!(WAIT_CALLS.load(Ordering::SeqCst), 1);
    }
}
#[test]
fn wait4_rusage_copy_failure_is_efault() {
    for failure in [-14, 1] {
        reset(42, 7 << 8, 2, failure);
        assert_eq!(wait4(0x1000, 0x2000), -14);
        assert_eq!(COPIES.lock().unwrap().len(), 2);
    }
}
#[test]
fn wait4_negative_and_nohang_zero_do_not_copy_outputs() {
    for rc in [-10, -4, -512, 0] {
        reset(rc, 0x7fff, 0, 0);
        assert_eq!(wait4(0x1000, 0x2000), rc as i64);
        assert!(COPIES.lock().unwrap().is_empty(), "unexpected copy for rc={rc}");
    }
}
#[test]
fn wait4_success_keeps_raw_status_and_exact_child_result() {
    reset(42, 7 << 8, 0, 0);
    assert_eq!(wait4(0x1000, 0x2000), 42);
    let copies = COPIES.lock().unwrap().clone();
    assert_eq!(copies.len(), 2);
    assert_eq!(copies[0], (0x1000, (7i32 << 8).to_ne_bytes().to_vec()));
    assert_eq!(copies[1].0, 0x2000);
    assert_eq!(copies[1].1.len(), size_of::<RUsage>());
}
#[test]
fn waitid_decodes_exit_stop_signal_core_and_continue() {
    for (raw, code, status) in [(7 << 8, CLD_EXITED, 7), (9, CLD_KILLED, 9),
        (11 | 0x80, CLD_DUMPED, 11), ((19 << 8) | 0x7f, CLD_STOPPED, 19),
        ((4 << 16) | (5 << 8) | 0x7f, CLD_STOPPED, 0x405), (0xffff, CLD_CONTINUED, SIGCONT)] {
        reset(42, raw, 0, 0);
        assert_eq!(waitid(0x3000), 0);
        let copies = COPIES.lock().unwrap().clone();
        assert_eq!(copies.len(), 1);
        let info = unsafe { core::ptr::read_unaligned(copies[0].1.as_ptr().cast::<SigInfo>()) };
        assert_eq!(info.si_signo, SIGCHLD);
        assert_eq!(info.si_code, code, "raw={raw:#x}");
        let child = unsafe { &info.sifields.sigchld };
        assert_eq!(child.si_pid, 42);
        assert_eq!(child.si_status, status, "raw={raw:#x}");
        assert_eq!(child.si_utime, 300);
        assert_eq!(child.si_stime, 500);
    }
}
#[test]
fn waitid_copy_failure_is_efault() {
    for rc in [42, 0] {
        for failure in [-14, 1] {
            reset(rc, 7 << 8, 1, failure);
            assert_eq!(waitid(0x3000), -14, "rc={rc}, failure={failure}");
            assert_eq!(COPIES.lock().unwrap().len(), 1);
        }
    }
}
#[test]
fn waitid_nohang_clears_siginfo_without_fabricated_child() {
    reset(0, 0x7fff, 0, 0);
    assert_eq!(waitid(0x3000), 0);
    let copies = COPIES.lock().unwrap().clone();
    assert_eq!(copies.len(), 1);
    assert_eq!(copies[0].1, vec![0; size_of::<SigInfo>()]);
}
#[test]
fn waitid_negative_preserves_error_and_null_info_needs_no_copy() {
    for rc in [-10, -4, -512] {
        reset(rc, 0, 0, 0);
        assert_eq!(waitid(0x3000), rc as i64);
        assert!(COPIES.lock().unwrap().is_empty());
    }
    for rc in [42, 0] {
        reset(rc, 7 << 8, 0, 0);
        assert_eq!(waitid(0), 0);
        assert!(COPIES.lock().unwrap().is_empty());
    }
}
#[test]
fn waitid_rejects_invalid_selector_ids_without_waiting_or_copying() {
    for (selector, id) in [(P_PID, 0), (P_PID, -1), (P_PID, i32::MIN),
                           (P_PGID, -1), (P_PGID, i32::MIN)] {
        let mut output = 0x12345678;
        assert_eq!(unsafe { waitid_to_wait_pid_result(selector, id, &mut output) }, -EINVAL);
        assert_eq!(output, 0x12345678);
        reset(42, 7 << 8, 0, 0);
        let result = unsafe { waitid_body_result(selector, id, 0x3000, WEXITED,
                                                 observe_wait, observe_copy) };
        assert_eq!(result, -(EINVAL as CLong));
        assert_eq!(WAIT_CALLS.load(Ordering::SeqCst), 0);
        assert!(COPIES.lock().unwrap().is_empty());
    }
}
#[test]
fn waitid_retains_positive_pid_current_group_and_all_id_semantics() {
    for id in [1, 42, i32::MAX] {
        let mut output = 0;
        assert_eq!(unsafe { waitid_to_wait_pid_result(P_PID, id, &mut output) }, 0);
        assert_eq!(output, id);
    }
    let mut output = 99;
    assert_eq!(unsafe { waitid_to_wait_pid_result(P_PGID, 0, &mut output) }, 0);
    assert_eq!(output, 0);
    for id in [i32::MIN, -1, 0, 42, i32::MAX] {
        assert_eq!(unsafe { waitid_to_wait_pid_result(P_ALL, id, &mut output) }, 0);
        assert_eq!(output, -1);
    }
}
#[test]
fn wait4_public_int_min_never_enters_internal_selector_domain() {
    reset(42, 7 << 8, 0, 0);
    let rc = unsafe { wait4_body_result(i32::MIN, 0x1000, 0, 0x2000, observe_wait, observe_copy) };
    assert_eq!(rc, -(ESRCH as CLong));
    assert_eq!(WAIT_CALLS.load(Ordering::SeqCst), 0);
    assert!(COPIES.lock().unwrap().is_empty());
}
unsafe extern "C" fn group_wait(selector: CInt, status: *mut CInt,
                                _options: CInt, _usage: *mut RUsage) -> CInt {
    // A wrong-group child is deliberately first, as in a real child list.
    for (group, child) in [(2, 51), (1, 42)] {
        if wait_process_pid_matches_result(selector, 99, group, child) != 0 {
            unsafe { *status = 7 << 8; }
            return child;
        }
    }
    -10
}
#[test]
fn waitid_group_one_does_not_select_first_unrelated_group_child() {
    reset(42, 7 << 8, 0, 0);
    let rc = unsafe { waitid_body_result(P_PGID, 1, 0x3000, WEXITED, group_wait, observe_copy) };
    assert_eq!(rc, 0);
    let copies = COPIES.lock().unwrap().clone();
    assert_eq!(copies.len(), 1);
    let info = unsafe { core::ptr::read_unaligned(copies[0].1.as_ptr().cast::<SigInfo>()) };
    assert_eq!(unsafe { info.sifields.sigchld.si_pid }, 42);
    let mut selector = 0;
    assert_eq!(unsafe { waitid_to_wait_pid_result(P_PGID, 1, &mut selector) }, 0);
    assert_eq!(selector, i32::MIN);
    assert_eq!(wait_process_pid_matches_result(selector, 99, 1, 42), 1);
    assert_eq!(wait_process_pid_matches_result(selector, 99, 2, 51), 0);
    for options in [0, __WALL, __WCLONE, __WALL | __WCLONE] {
        assert_eq!(wait_should_scan_thread_result(selector, options), 0);
    }
    // Existing all-children and ordinary negative-group selectors retain meaning.
    assert_eq!(wait_process_pid_matches_result(-1, 99, 2, 51), 1);
    assert_eq!(wait_process_pid_matches_result(-2, 99, 2, 51), 1);
    assert_eq!(wait_process_pid_matches_result(-2, 99, 1, 42), 0);
}
#[repr(C)]
struct CandidateProcess { pid: CInt, status: CInt }
#[repr(C)]
struct CandidateThread { proc: *mut c_void, tid: CInt, status: CInt, ptrace: CInt, flags: CInt }
static CANDIDATE_CONFIG: Mutex<(bool, bool, CInt, CInt)> = Mutex::new((false, true, 19, 42));
static CANDIDATE_EVENTS: Mutex<Vec<&'static str>> = Mutex::new(Vec::new());
static CANDIDATE_FOUND: AtomicI32 = AtomicI32::new(0);
static CANDIDATE_FLAGS: AtomicI32 = AtomicI32::new(0);
unsafe extern "C" fn candidate_stopped(_thread: *mut c_void, _proc: *mut c_void,
                                       _child: *mut c_void, status: *mut CInt, _options: CInt) -> CInt {
    CANDIDATE_EVENTS.lock().unwrap().push("stopped");
    let (_, _, payload, result) = *CANDIDATE_CONFIG.lock().unwrap();
    unsafe { *status = wait_stopped_status_result(payload); }
    result
}
unsafe extern "C" fn candidate_continued(_thread: *mut c_void, _proc: *mut c_void,
                                         _child: *mut c_void, _status: *mut CInt, _options: CInt) -> CInt {
    CANDIDATE_EVENTS.lock().unwrap().push("unexpected continued");
    0
}
unsafe extern "C" fn candidate_reap(child: *mut c_void, offset: CULong,
                                    options: CInt, mask: CInt) -> CInt {
    CANDIDATE_EVENTS.lock().unwrap().push("reap");
    if wait_reap_needed_result(options) != 0 {
        unsafe { *child.cast::<u8>().add(offset as usize).cast::<CInt>() &= !mask; }
    }
    0
}
unsafe extern "C" fn candidate_unlock(lock: *mut c_void, _node: *mut c_void) {
    CANDIDATE_EVENTS.lock().unwrap().push(if lock as usize == 1 { "unlock parent" } else { "unlock child" });
}
unsafe extern "C" fn candidate_side_effect(_child: *mut c_void) {
    CANDIDATE_EVENTS.lock().unwrap().push("unexpected release/detach");
}
unsafe extern "C" fn candidate_wait(_pid: CInt, status: *mut CInt, options: CInt,
                                    _usage: *mut RUsage) -> CInt {
    let (thread_mode, traced, _, _) = *CANDIDATE_CONFIG.lock().unwrap();
    let mut proc = CandidateProcess { pid: 42, status: PS_STOPPED };
    let mut child = CandidateThread { proc: (&mut proc as *mut CandidateProcess).cast(),
        tid: 42, status: PS_STOPPED, ptrace: if traced { PT_TRACED } else { 0 }, flags: SIGNAL_STOP_STOPPED };
    let child_ptr = (&mut child as *mut CandidateThread).cast::<c_void>();
    let proc_ptr = (&mut proc as *mut CandidateProcess).cast::<c_void>();
    let mut current = 0u8;
    let mut found = 0;
    let rc = unsafe {
        if thread_mode {
            wait_thread_candidate_body_result(0, 42, status, options,
                (&mut current as *mut u8).cast(), child_ptr, 2usize as *mut c_void, 3usize as *mut c_void,
                core::mem::offset_of!(CandidateThread, proc) as CULong,
                core::mem::offset_of!(CandidateThread, tid) as CULong,
                core::mem::offset_of!(CandidateThread, status) as CULong,
                core::mem::offset_of!(CandidateThread, ptrace) as CULong,
                core::mem::offset_of!(CandidateThread, flags) as CULong,
                Some(candidate_stopped), Some(candidate_continued), Some(candidate_reap),
                Some(candidate_unlock), Some(candidate_side_effect), Some(candidate_side_effect),
                Some(candidate_side_effect), &mut found)
        } else {
            wait_process_candidate_body_result(0, 42, status, options,
                (&mut current as *mut u8).cast(), proc_ptr, child_ptr,
                1usize as *mut c_void, 3usize as *mut c_void, 2usize as *mut c_void, 4usize as *mut c_void,
                core::mem::offset_of!(CandidateProcess, pid) as CULong,
                core::mem::offset_of!(CandidateProcess, status) as CULong,
                core::mem::offset_of!(CandidateThread, tid) as CULong,
                core::mem::offset_of!(CandidateThread, ptrace) as CULong,
                core::mem::offset_of!(CandidateThread, flags) as CULong,
                Some(candidate_stopped), Some(candidate_continued), Some(candidate_reap),
                Some(candidate_unlock), &mut found)
        }
    };
    CANDIDATE_FOUND.store(found, Ordering::SeqCst);
    CANDIDATE_FLAGS.store(child.flags, Ordering::SeqCst);
    rc
}
fn candidate_setup(thread_mode: bool, traced: bool, payload: CInt, result: CInt) {
    reset(result, 0, 0, 0);
    *CANDIDATE_CONFIG.lock().unwrap() = (thread_mode, traced, payload, result);
    CANDIDATE_EVENTS.lock().unwrap().clear();
}
fn candidate_order(thread_mode: bool) -> Vec<&'static str> {
    if thread_mode { vec!["stopped", "reap", "unlock child"] }
    else { vec!["stopped", "reap", "unlock parent", "unlock child"] }
}
#[test]
fn actual_candidates_preserve_stop_origin_payload_and_public_wait4_encoding() {
    assert!(NSIG < WAIT_STATUS_PTRACED_STOP);
    for thread_mode in [false, true] {
        for traced in [false, true] {
            for payload in [19, 0x85, 0x405] {
                candidate_setup(thread_mode, traced, payload, 42);
                let rc = unsafe { waitid_body_result(P_PID, 42, 0x3000, WSTOPPED,
                                                      candidate_wait, observe_copy) };
                assert_eq!(rc, 0);
                let copies = COPIES.lock().unwrap().clone();
                let info = unsafe { core::ptr::read_unaligned(copies[0].1.as_ptr().cast::<SigInfo>()) };
                assert_eq!(info.si_code, if traced { CLD_TRAPPED } else { CLD_STOPPED },
                           "thread={thread_mode}, traced={traced}, payload={payload:#x}");
                assert_eq!(unsafe { info.sifields.sigchld.si_status }, payload);
                assert_eq!(CANDIDATE_EVENTS.lock().unwrap().clone(), candidate_order(thread_mode));
                candidate_setup(thread_mode, traced, payload, 42);
                assert_eq!(unsafe { wait4_body_result(42, 0x1000, WUNTRACED, 0,
                                                      candidate_wait, observe_copy) }, 42);
                let copies = COPIES.lock().unwrap().clone();
                assert_eq!(copies[0].1, wait_stopped_status_result(payload).to_ne_bytes());
            }
        }
    }
}
#[test]
fn ptraced_candidate_no_result_or_failure_does_not_mark_or_reap() {
    for thread_mode in [false, true] {
        for result in [0, -4] {
            candidate_setup(thread_mode, true, 0x405, result);
            let mut status = 0;
            assert_eq!(unsafe { candidate_wait(42, &mut status, WSTOPPED, core::ptr::null_mut()) }, result);
            assert_eq!(status, wait_stopped_status_result(0x405));
            assert_eq!(CANDIDATE_FOUND.load(Ordering::SeqCst), 0);
            assert_eq!(CANDIDATE_EVENTS.lock().unwrap().clone(), vec!["stopped"]);
        }
    }
}
#[test]
fn candidate_wnowait_keeps_original_reap_and_unlock_order() {
    for thread_mode in [false, true] {
        for traced in [false, true] {
            candidate_setup(thread_mode, traced, 0x405, 42);
            assert_eq!(unsafe { waitid_body_result(P_PID, 42, 0x3000, WSTOPPED | WNOWAIT,
                                                  candidate_wait, observe_copy) }, 0);
            assert_eq!(CANDIDATE_FLAGS.load(Ordering::SeqCst), SIGNAL_STOP_STOPPED);
            assert_eq!(CANDIDATE_FOUND.load(Ordering::SeqCst), 1);
            assert_eq!(CANDIDATE_EVENTS.lock().unwrap().clone(), candidate_order(thread_mode));
            let copies = COPIES.lock().unwrap().clone();
            let info = unsafe { core::ptr::read_unaligned(copies[0].1.as_ptr().cast::<SigInfo>()) };
            assert_eq!(info.si_code, if traced { CLD_TRAPPED } else { CLD_STOPPED });
            assert_eq!(unsafe { info.sifields.sigchld.si_status }, 0x405);
        }
    }
}
'''
        harness = harness.replace("@ABI@", str(ROOT / "kernel/rust/abi.rs"))
        harness = harness.replace("@CONSTANTS@", "\n".join(declarations))
        harness = harness.replace("@ALIASES@", "\n".join(aliases))
        harness = harness.replace("@FUNCTIONS@", "\n".join(function(source, name) for name in names))
        with tempfile.TemporaryDirectory(prefix="m14-f03-wait-") as directory:
            path = Path(directory)
            (path / "fixture.rs").write_text(harness)
            result = subprocess.run([compiler, "--edition=2021", "--test", str(path / "fixture.rs"),
                                     "-o", str(path / "fixture")], capture_output=True,
                                    text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(path / "fixture"), "--test-threads=1"],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
