// SPDX-License-Identifier: GPL-2.0
//! Exact selected guest protection bodies; controlled forwarding/range providers.

#[allow(dead_code)]
#[path = "abi.rs"]
mod abi;
use abi::*;
use core::{
    ffi::c_void,
    mem::{offset_of, MaybeUninit},
    ptr::{null_mut, write, write_volatile},
};
use std::cell::{Cell, RefCell};

thread_local! {
    static CURRENT: Cell<*mut Thread> = const { Cell::new(null_mut()) };
    static FORWARD_RESULT: Cell<i64> = const { Cell::new(0) };
    static FORWARDED: RefCell<Vec<(i32, u64, u64, u64, i32)>> = const { RefCell::new(Vec::new()) };
    static EVENTS: RefCell<Vec<&'static str>> = const { RefCell::new(Vec::new()) };
    static HOST_CALLS: RefCell<Vec<(u64, usize, i32, i32)>> = const { RefCell::new(Vec::new()) };
}

#[cfg(native_linux_irq_work_v6_12)]
unsafe fn current_thread_ptr() -> *mut Thread {
    CURRENT.with(Cell::get)
}
#[cfg(native_linux_irq_work_v6_12)]
unsafe extern "C" fn ihk_mc_get_processor_id() -> CInt {
    2
}
#[cfg(native_linux_irq_work_v6_12)]
unsafe extern "C" fn syscall_policy_do_syscall3_bridge(
    nr: CInt,
    start: CULong,
    len: CULong,
    arg2: CULong,
) -> CLong {
    let flag = (*(*current_thread_ptr()).vm).is_memory_range_lock_taken;
    FORWARDED.with(|calls| calls.borrow_mut().push((nr, start, len, arg2, flag)));
    FORWARD_RESULT.with(Cell::get)
}

include!("native-application-protection-bodies.rs");

#[test]
fn all_permission_transitions_preserve_legacy_c_and_invalidate_native_changes() {
    let rows: Vec<_> = include_str!("c-reference.log").lines().collect();
    assert_eq!(rows.len(), 64);
    for row in rows {
        let values: Vec<i32> = row.split_whitespace().map(|v| v.parse().unwrap()).collect();
        let (old, new) = (values[0], values[1]);
        let expected = if cfg!(native_linux_irq_work_v6_12) {
            (old != new) as i32
        } else {
            values[2]
        };
        assert_eq!(
            mprotect_write_changed_result(((old as u64) << 16) | 0x70a00000, (new as u64) << 16),
            expected
        );
        #[cfg(not(native_linux_irq_work_v6_12))]
        assert_eq!(set_host_vma_body_result(0x400000, 8192, new, 1), values[3]);
    }
}

#[test]
fn selected_vma_adapter_forwards_exact_clear_and_restores_vm_lock_flag() {
    for holding in [0, 1] {
        for error in [0, -14, -22, -18] {
            let mut vm: Box<ProcessVm> = Box::new(unsafe { core::mem::zeroed() });
            let mut thread: Box<Thread> = Box::new(unsafe { core::mem::zeroed() });
            vm.is_memory_range_lock_taken = 17;
            thread.vm = &mut *vm;
            CURRENT.with(|current| current.set(&mut *thread));
            FORWARD_RESULT.with(|result| result.set(error));
            FORWARDED.with(|calls| calls.borrow_mut().clear());
            let result = set_host_vma_body_result(0x400000, 8192, 0, holding);
            CURRENT.with(|current| current.set(null_mut()));
            if cfg!(native_linux_irq_work_v6_12) {
                assert_eq!(result, error as i32);
                FORWARDED.with(|calls| {
                    assert_eq!(
                        *calls.borrow(),
                        [(11, 0x400000, 8192, 0, if holding == 0 { 17 } else { 2 })]
                    )
                });
                assert_eq!(
                    vm.is_memory_range_lock_taken,
                    if holding == 0 { 17 } else { -1 }
                );
            } else {
                assert_eq!(result, 0);
                FORWARDED.with(|calls| assert!(calls.borrow().is_empty()));
                assert_eq!(vm.is_memory_range_lock_taken, 17);
            }
        }
    }
}

#[test]
fn native_adapter_rejects_absent_thread_or_vm_without_forwarding() {
    CURRENT.with(|current| current.set(null_mut()));
    FORWARDED.with(|calls| calls.borrow_mut().clear());
    let expected = if cfg!(native_linux_irq_work_v6_12) {
        -22
    } else {
        0
    };
    assert_eq!(set_host_vma_body_result(4096, 4096, 1, 1), expected);
    let mut thread: Box<Thread> = Box::new(unsafe { core::mem::zeroed() });
    CURRENT.with(|current| current.set(&mut *thread));
    assert_eq!(set_host_vma_body_result(4096, 4096, 1, 1), expected);
    CURRENT.with(|current| current.set(null_mut()));
    FORWARDED.with(|calls| assert!(calls.borrow().is_empty()));
}

#[repr(C)]
struct Range {
    start: u64,
    end: u64,
    flags: u64,
}
unsafe extern "C" fn lookup(vm: *mut c_void, _: u64, _: u64) -> *mut c_void {
    vm
}
unsafe extern "C" fn next(_: *mut c_void, _: *mut c_void) -> *mut c_void {
    null_mut()
}
unsafe extern "C" fn lock(_: *mut c_void) {
    EVENTS.with(|e| e.borrow_mut().push("lock"));
}
unsafe extern "C" fn unlock(_: *mut c_void) {
    EVENTS.with(|e| e.borrow_mut().push("unlock"));
}
unsafe extern "C" fn flush() {
    EVENTS.with(|e| e.borrow_mut().push("flush"));
}
unsafe extern "C" fn change(_: *mut c_void, range: *mut c_void, flags: u64) -> i32 {
    let range = &mut *range.cast::<Range>();
    range.flags = (range.flags & !VR_PROT_MASK) | flags;
    EVENTS.with(|e| e.borrow_mut().push("change"));
    0
}
unsafe extern "C" fn host(start: u64, len: usize, prot: i32, held: i32) -> i32 {
    EVENTS.with(|e| e.borrow_mut().push("host"));
    HOST_CALLS.with(|calls| calls.borrow_mut().push((start, len, prot, held)));
    FORWARD_RESULT.with(Cell::get) as i32
}

#[test]
fn full_body_invalidates_read_revocation_and_partial_changes_before_unlock() {
    for (old, new) in [(3, 1), (1, 0), (1, 5), (1, 1)] {
        for partial in [false, true] {
            for host_error in [0, -14] {
                let mut range = Range {
                    start: 0x400000,
                    end: 0x401000,
                    flags: VR_MAXPROT_MASK | ((old as u64) << 16),
                };
                let len = if partial { 8192 } else { 4096 };
                FORWARD_RESULT.with(|result| result.set(host_error));
                EVENTS.with(|events| events.borrow_mut().clear());
                HOST_CALLS.with(|calls| calls.borrow_mut().clear());
                let result = unsafe {
                    mprotect_body_result(
                        (&mut range as *mut Range).cast(),
                        null_mut(),
                        0x400000,
                        len,
                        new,
                        0,
                        0x800000,
                        0,
                        0,
                        2,
                        offset_of!(Range, start),
                        offset_of!(Range, end),
                        offset_of!(Range, flags),
                        Some(lock),
                        Some(unlock),
                        Some(lookup),
                        Some(next),
                        None,
                        None,
                        Some(change),
                        Some(host),
                        None,
                        Some(flush),
                        None,
                    )
                };
                let called = if cfg!(native_linux_irq_work_v6_12) {
                    old != new
                } else {
                    ((old ^ new) & 2) != 0 && !partial
                };
                let expected = if partial {
                    -12
                } else if called {
                    host_error as i32
                } else {
                    0
                };
                assert_eq!(result, expected);
                assert_eq!(range.flags & VR_PROT_MASK, (new as u64) << 16);
                HOST_CALLS.with(|calls| {
                    assert_eq!(
                        *calls.borrow(),
                        if called {
                            vec![(0x400000, len, new, 1)]
                        } else {
                            vec![]
                        }
                    )
                });
                EVENTS.with(|events| {
                    assert_eq!(
                        *events.borrow(),
                        if called {
                            vec!["lock", "change", "flush", "host", "unlock"]
                        } else {
                            vec!["lock", "change", "flush", "unlock"]
                        }
                    )
                });
            }
        }
    }
}
