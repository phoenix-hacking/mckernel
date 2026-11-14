// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Source only. Synthetic model dependencies; includes exact private Rust body.
#![allow(dead_code)]
use std::sync::{Mutex, atomic::{AtomicBool, AtomicI32, AtomicPtr, Ordering}};
pub mod abi {
    pub type CInt = i32;
    #[repr(C, align(64))]
    pub struct McsRwlockLock;
    #[repr(C)]
    pub struct Process {
        pub update_lock: McsRwlockLock,
        pub ruid: i32, pub euid: i32, pub suid: i32, pub fsuid: i32,
        pub rgid: i32, pub egid: i32, pub sgid: i32, pub fsgid: i32,
        pub refs: i32,
    }
    pub struct Thread { pub proc: *mut Process }
}
pub mod process_helpers {
    pub unsafe fn hold_process(p: *mut super::abi::Process) { unsafe { (*p).refs += 1 }; }
    pub unsafe fn release_process(p: *mut super::abi::Process) { unsafe { (*p).refs -= 1 }; }
}
static LOCKED: AtomicBool = AtomicBool::new(false);
pub mod lock_helpers {
    #[repr(C, align(64))]
    pub struct McsRwlockNodeIrqsave { irqsave: u64 }
    pub unsafe fn __mcs_rwlock_writer_lock(_: *mut super::abi::McsRwlockLock, n: *mut McsRwlockNodeIrqsave) {
        assert!(!super::LOCKED.swap(true, super::Ordering::SeqCst));
        unsafe { (*n).irqsave = 0 };
    }
    pub unsafe fn __mcs_rwlock_writer_unlock(_: *mut super::abi::McsRwlockLock, _: *mut McsRwlockNodeIrqsave) {
        assert!(super::LOCKED.swap(false, super::Ordering::SeqCst));
    }
}
#[path = "postimage/kernel/rust/f03_credential_snapshot_candidate.rs"]
mod candidate;
use candidate::*;
use core::ffi::c_void;
static SERIAL: Mutex<()> = Mutex::new(());
static OUTCOME: AtomicI32 = AtomicI32::new(READY);
static STATUS: AtomicI32 = AtomicI32::new(0);
static FINISH_ERROR: AtomicI32 = AtomicI32::new(0);
static FINISHED: AtomicI32 = AtomicI32::new(-1);
static BEGIN_PROC: AtomicPtr<abi::Process> = AtomicPtr::new(core::ptr::null_mut());
static RETARGET_THREAD: AtomicPtr<abi::Thread> = AtomicPtr::new(core::ptr::null_mut());
static RETARGET_PROC: AtomicPtr<abi::Process> = AtomicPtr::new(core::ptr::null_mut());
unsafe extern "C" fn begin(p: *mut abi::Process, _: i32) -> CredBegin {
    assert!(!LOCKED.load(Ordering::SeqCst));
    assert!(unsafe { (*p).refs } > 0);
    BEGIN_PROC.store(p, Ordering::SeqCst);
    CredBegin { token: core::ptr::NonNull::<u8>::dangling().as_ptr().cast(), status: 0, reserved: 0 }
}
unsafe extern "C" fn snapshot(_: *mut c_void) -> CredReply {
    assert!(!LOCKED.load(Ordering::SeqCst));
    let thread = RETARGET_THREAD.load(Ordering::SeqCst);
    if !thread.is_null() { unsafe { (*thread).proc = RETARGET_PROC.load(Ordering::SeqCst) }; }
    CredReply { outcome: OUTCOME.load(Ordering::SeqCst), status: STATUS.load(Ordering::SeqCst),
        ids: [101, 102, 103, 104, 201, 202, 203, 204] }
}
unsafe extern "C" fn finish(_: *mut c_void, outcome: i32, _: i32) -> i32 {
    assert!(!LOCKED.load(Ordering::SeqCst));
    FINISHED.store(outcome, Ordering::SeqCst);
    FINISH_ERROR.load(Ordering::SeqCst)
}
fn process() -> Box<abi::Process> {
    Box::new(abi::Process { update_lock: abi::McsRwlockLock,
        ruid: 1, euid: 2, suid: 3, fsuid: 4, rgid: 5, egid: 6, sgid: 7, fsgid: 8, refs: 0 })
}
fn ids(p: &abi::Process) -> [i32; 8] { [p.ruid,p.euid,p.suid,p.fsuid,p.rgid,p.egid,p.sgid,p.fsgid] }
fn reset() {
    OUTCOME.store(READY, Ordering::SeqCst); STATUS.store(0, Ordering::SeqCst);
    FINISH_ERROR.store(0, Ordering::SeqCst); FINISHED.store(-1, Ordering::SeqCst);
    RETARGET_THREAD.store(core::ptr::null_mut(), Ordering::SeqCst);
    RETARGET_PROC.store(core::ptr::null_mut(), Ordering::SeqCst);
}
const OPS: CredOwnerOps = CredOwnerOps { begin, snapshot, finish };
#[test]
fn updates_only_original_uid_or_gid_quartet() {
    let _guard = SERIAL.lock().unwrap();
    for kind in [UID, GID] {
        reset(); let mut p = process(); let mut t = abi::Thread { proc: &mut *p };
        assert_eq!(unsafe { refresh(&mut t, kind, &OPS) }, 0);
        assert_eq!(ids(&p), if kind == UID { [101,102,103,104,5,6,7,8] } else { [1,2,3,4,201,202,203,204] });
        assert_eq!(p.refs, 0); assert_eq!(FINISHED.load(Ordering::SeqCst), READY);
    }
}
#[test]
fn captured_process_survives_thread_retarget() {
    let _guard = SERIAL.lock().unwrap(); reset();
    let mut original = process(); let mut other = process();
    let mut t = abi::Thread { proc: &mut *original };
    RETARGET_THREAD.store(&mut t, Ordering::SeqCst); RETARGET_PROC.store(&mut *other, Ordering::SeqCst);
    assert_eq!(unsafe { refresh(&mut t, UID, &OPS) }, 0);
    assert_eq!(BEGIN_PROC.load(Ordering::SeqCst), &mut *original as *mut _);
    assert_eq!(ids(&original), [101,102,103,104,5,6,7,8]);
    assert_eq!(ids(&other), [1,2,3,4,5,6,7,8]); assert_eq!(original.refs, 0);
}
#[test]
fn failures_and_unknown_do_not_restore_or_write_fields() {
    let _guard = SERIAL.lock().unwrap();
    for (outcome, status, expected, finish_outcome) in [(FAILED,-13,-13,FAILED),
        (UNKNOWN,-5,-5,UNKNOWN),(READY,-5,-5,UNKNOWN),(READY,1,-5,UNKNOWN),
        (FAILED,0,-5,UNKNOWN),(99,0,-5,UNKNOWN)] {
        reset(); OUTCOME.store(outcome, Ordering::SeqCst); STATUS.store(status, Ordering::SeqCst);
        let mut p = process(); let mut t = abi::Thread { proc: &mut *p };
        assert_eq!(unsafe { refresh(&mut t, GID, &OPS) }, expected);
        assert_eq!(ids(&p), [1,2,3,4,5,6,7,8]); assert_eq!(p.refs, 0);
        assert_eq!(FINISHED.load(Ordering::SeqCst), finish_outcome);
    }
}
#[test]
fn owner_finish_failure_is_not_reported_as_success() {
    let _guard = SERIAL.lock().unwrap(); reset(); FINISH_ERROR.store(-5, Ordering::SeqCst);
    let mut p = process(); let mut t = abi::Thread { proc: &mut *p };
    assert_eq!(unsafe { refresh(&mut t, UID, &OPS) }, -5);
    // Commit is accurate; failure to retire owner must not roll credentials back.
    assert_eq!(ids(&p), [101,102,103,104,5,6,7,8]); assert_eq!(p.refs, 0);
}
