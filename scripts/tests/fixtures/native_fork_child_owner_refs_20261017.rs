// SPDX-License-Identifier: GPL-2.0
// Actual ForkChildOwner code; Linux reference operations/layout are adapters.
// Structural mm_count is not mapping access, guest-root or Linux runtime proof.
#![allow(dead_code, non_camel_case_types, non_upper_case_globals)]
use std::{cell::RefCell, ptr::{self, NonNull}, sync::atomic::{AtomicI32, Ordering}};
type Result<T = ()> = std::result::Result<T, i32>;
const ESRCH: i32 = -3;
fn errno(value: i32) -> i32 { value }

mod bindings {
    use super::*;
    pub struct pid;
    pub struct task_struct;
    pub struct pid_namespace;
    pub const pid_type_PIDTYPE_TGID: u32 = 1;
    pub static mut init_pid_ns: pid_namespace = pid_namespace;
    #[repr(C)] pub struct atomic_t { pub counter: i32 }
    #[repr(C)] pub struct mm_fields { pub mm_count: atomic_t }
    #[repr(C)] pub struct mm_union { pub __bindgen_anon_1: mm_fields }
    #[repr(C)] pub struct mm_struct { pub __bindgen_anon_1: mm_union }
    pub unsafe fn get_current() -> *mut task_struct { ptr::null_mut() }
    pub unsafe fn get_task_pid(_: *mut task_struct, kind: u32) -> *mut pid {
        assert_eq!(kind, pid_type_PIDTYPE_TGID);
        STATE.with(|state| {
            let mut state = state.borrow_mut(); state.pid_gets += 1;
            if !state.pid_present { return ptr::null_mut(); }
            state.pid_refs += 1; &mut *state.pid
        })
    }
    pub unsafe fn get_task_mm(_: *mut task_struct) -> *mut mm_struct {
        STATE.with(|state| {
            let mut state = state.borrow_mut(); state.mm_gets += 1;
            if !state.mm_present { return ptr::null_mut(); }
            state.mm_users += 1; &mut *state.mm
        })
    }
    pub unsafe fn pid_nr_ns(selected_pid: *mut pid, ns: *mut pid_namespace) -> i32 {
        assert_eq!(ns, ptr::addr_of_mut!(init_pid_ns));
        STATE.with(|state| { let state = state.borrow(); assert_eq!(selected_pid, ptr::from_ref(&*state.pid).cast_mut()); state.number })
    }
    pub unsafe fn put_pid(selected_pid: *mut pid) {
        STATE.with(|state| {
            let mut state = state.borrow_mut();
            assert_eq!(selected_pid, ptr::from_ref(&*state.pid).cast_mut());
            assert!(state.pid_refs > 0); state.pid_refs -= 1; state.pid_puts += 1;
        });
    }
    pub unsafe fn mmput(mm: *mut mm_struct) {
        STATE.with(|state| {
            let mut state = state.borrow_mut();
            assert_eq!(mm, ptr::from_ref(&*state.mm).cast_mut());
            assert_eq!(state.mm_users, 2, "only the transient reference is returned here");
            state.mm_users -= 1; state.mm_puts += 1;
        });
    }
    pub unsafe fn __mmdrop(mm: *mut mm_struct) {
        STATE.with(|state| {
            let mut state = state.borrow_mut();
            assert_eq!(mm, ptr::from_ref(&*state.mm).cast_mut());
            assert_eq!(state.count(), 0); state.mm_drops += 1;
        });
    }
}
struct LinuxState {
    pid_present: bool, mm_present: bool, number: i32,
    pid: Box<bindings::pid>, mm: Box<bindings::mm_struct>,
    pid_gets: usize, mm_gets: usize, pid_puts: usize, mm_puts: usize,
    pid_refs: i32, mm_users: i32, mm_drops: usize,
}
impl LinuxState {
    fn new(pid: bool, mm: bool, number: i32, count: i32) -> Self {
        Self { pid_present: pid, mm_present: mm, number,
            pid: Box::new(bindings::pid),
            mm: Box::new(bindings::mm_struct { __bindgen_anon_1: bindings::mm_union {
                __bindgen_anon_1: bindings::mm_fields { mm_count: bindings::atomic_t { counter: count } } } }),
            pid_gets: 0, mm_gets: 0, pid_puts: 0, mm_puts: 0, pid_refs: 0, mm_users: 1, mm_drops: 0 }
    }
    fn count_atomic(&self) -> &AtomicI32 {
        // Same Linux atomic_t adapter storage used by the actual owner body.
        unsafe { AtomicI32::from_ptr(ptr::addr_of!(self.mm.__bindgen_anon_1.__bindgen_anon_1.mm_count.counter).cast_mut()) }
    }
    fn count(&self) -> i32 { self.count_atomic().load(Ordering::SeqCst) }
}
thread_local! { static STATE: RefCell<LinuxState> = RefCell::new(LinuxState::new(true, true, 123, 1)); }
fn configure(pid: bool, mm: bool, number: i32, count: i32) {
    STATE.with(|state| *state.borrow_mut() = LinuxState::new(pid, mm, number, count));
}
#[derive(Debug, PartialEq)]
struct Snapshot { pid_gets: usize, mm_gets: usize, pid_puts: usize, mm_puts: usize,
    pid_refs: i32, mm_users: i32, count: i32, mm_drops: usize }
fn snapshot() -> Snapshot {
    STATE.with(|state| { let state = state.borrow(); Snapshot {
        pid_gets: state.pid_gets, mm_gets: state.mm_gets, pid_puts: state.pid_puts, mm_puts: state.mm_puts,
        pid_refs: state.pid_refs, mm_users: state.mm_users, count: state.count(), mm_drops: state.mm_drops } })
}
fn linux_last_user_teardown() {
    STATE.with(|state| {
        let mut state = state.borrow_mut(); assert_eq!(state.mm_users, 1);
        state.mm_users = 0;
        assert_eq!(state.count_atomic().fetch_sub(1, Ordering::SeqCst), 2);
        assert_eq!(state.mm_drops, 0, "the structural owner still prevents final free");
    });
}

@ACTUAL_OWNER@

mod missing_put_mutant {
    use super::*;
    @MISSING_PUT_MUTANT@
    pub(super) fn execute() -> Result { ForkChildOwner::current().map(drop) }
}
mod corrupt_drop_mutant {
    use super::*;
    @CORRUPT_DROP_MUTANT@
    pub(super) fn execute() -> Result { ForkChildOwner::current().map(drop) }
}
fn missing_mm_oracle(result: Result, observed: &Snapshot) -> bool {
    result == Err(ESRCH) && observed.pid_refs == 0 && observed.pid_puts == 1
        && observed.mm_gets == 1 && observed.mm_puts == 0
}
fn ordinary_drop_oracle(result: Result, observed: &Snapshot) -> bool {
    result.is_ok() && observed.pid_refs == 0 && observed.pid_puts == 1 && observed.count == 1
        && observed.mm_users == 1 && observed.mm_puts == 1 && observed.mm_drops == 0
}

#[test]
fn owner_missing_pid_or_mm_balances_only_acquired_references() {
    configure(false, true, 123, 1);
    assert!(matches!(ForkChildOwner::current(), Err(ESRCH)));
    assert_eq!(snapshot(), Snapshot { pid_gets: 1, mm_gets: 0, pid_puts: 0, mm_puts: 0,
        pid_refs: 0, mm_users: 1, count: 1, mm_drops: 0 });
    configure(true, false, 123, 1);
    let result = ForkChildOwner::current().map(drop);
    assert!(missing_mm_oracle(result, &snapshot()));
}
#[test]
fn owner_invalid_pid_number_releases_transient_mm_and_pid() {
    for number in [0, -1] {
        configure(true, true, number, 1);
        assert!(matches!(ForkChildOwner::current(), Err(ESRCH)));
        assert_eq!(snapshot(), Snapshot { pid_gets: 1, mm_gets: 1, pid_puts: 1, mm_puts: 1,
            pid_refs: 0, mm_users: 1, count: 1, mm_drops: 0 });
    }
}
#[test]
fn owner_overflow_and_nonpositive_counts_leave_count_unchanged() {
    for count in [i32::MAX, 0, -1] {
        configure(true, true, 123, count);
        assert!(matches!(ForkChildOwner::current(), Err(-75)));
        assert_eq!(snapshot(), Snapshot { pid_gets: 1, mm_gets: 1, pid_puts: 1, mm_puts: 1,
            pid_refs: 0, mm_users: 1, count, mm_drops: 0 });
    }
}
#[test]
fn owner_ordinary_drop_returns_structural_count_without_final_free() {
    configure(true, true, 123, 1);
    let owner = ForkChildOwner::current().unwrap();
    assert_eq!(owner.number, 123);
    assert_eq!(snapshot(), Snapshot { pid_gets: 1, mm_gets: 1, pid_puts: 0, mm_puts: 1,
        pid_refs: 1, mm_users: 1, count: 2, mm_drops: 0 });
    drop(owner);
    assert!(ordinary_drop_oracle(Ok(()), &snapshot()));
}
#[test]
fn owner_survives_linux_last_user_then_performs_exact_final_drop() {
    configure(true, true, 123, 1);
    let owner = ForkChildOwner::current().unwrap();
    linux_last_user_teardown();
    assert_eq!(snapshot().count, 1);
    assert_eq!(snapshot().pid_refs, 1);
    drop(owner);
    assert_eq!(snapshot(), Snapshot { pid_gets: 1, mm_gets: 1, pid_puts: 1, mm_puts: 1,
        pid_refs: 0, mm_users: 0, count: 0, mm_drops: 1 });
}
#[test]
fn owner_reference_oracles_reject_missing_put_and_corrupt_drop_mutants() {
    configure(true, false, 123, 1);
    let result = missing_put_mutant::execute();
    assert!(!missing_mm_oracle(result, &snapshot()), "missing put_pid must fail the same reference oracle");
    assert_eq!(snapshot().pid_refs, 1);
    configure(true, true, 123, 1);
    let result = corrupt_drop_mutant::execute();
    assert!(!ordinary_drop_oracle(result, &snapshot()), "wrong structural decrement must fail the same reference oracle");
    assert_eq!(snapshot().count, 3);
}
