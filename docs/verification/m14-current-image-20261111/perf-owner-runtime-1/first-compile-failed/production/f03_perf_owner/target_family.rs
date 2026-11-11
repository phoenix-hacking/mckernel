// TEST-ONLY CALLER DRAFT. No main/adapters, final source pins or REQUEST.
// Run the entire actual target_process module; no rewritten CAS/hold algorithm.
use core::cell::Cell;
use core::ffi::c_void;
use core::ptr::addr_of_mut;
use core::sync::atomic::{AtomicI32, Ordering};
use crate::abi::{CInt, CLong, Process};
use super::target_process::{with_remote_target, FindProcess, UnlockProcess};

#[derive(Debug,PartialEq,Eq)]
pub(super) struct TargetObservation {
    pub positive_body_ref: i32,
    pub positive_result: CLong,
    pub positive_final_ref: i32,
    pub zero_error: CInt,
    pub zero_body_calls: usize,
    pub zero_final_ref: i32,
    pub overflow_error: CInt,
    pub overflow_body_calls: usize,
    pub overflow_final_ref: i32,
}

unsafe fn refcount_value(process: *mut Process) -> i32 {
    // The finite fixture owns typed backing for this single observation.
    // No reference escapes this helper or is assigned an invented lifetime.
    unsafe {
        AtomicI32::from_ptr(addr_of_mut!((*process).refcount.counter)).load(Ordering::SeqCst)
    }
}

/// The final caller supplies THREE distinct controlled typed Process objects
/// with base counts1/0/i32::MAX and actual pid fields matching positive pids.
/// The explicit lower find/unlock adapter models the genuine hash borrow and
/// captures exact pointer/node/count order. It cannot grant a positive pin.
/// The actual new with_remote_target alone performs the checked increment.
/// Its lower release_process adapter must execute the unchanged qualified F02
/// atomic-decrement helper and observe unlock first; it cannot be a fake pin
/// or claim real kernel Process destruction. Terminal monitor behavior is a
/// separate call to the actual new monitor/terminal functions, not mirrored here.
pub(super) unsafe fn exercise_actual_positive_target(
    pids: [CInt; 3],
    targets: [*mut Process; 3],
    node: *mut c_void,
    find: FindProcess,
    unlock: UnlockProcess,
) -> TargetObservation {
    assert!(!node.is_null());
    assert!(targets.iter().all(|p| !p.is_null()));
    assert!(targets[0] != targets[1] && targets[1] != targets[2] && targets[0] != targets[2]);
    unsafe {
        assert!(refcount_value(targets[0]) == 1);
        assert!(refcount_value(targets[1]) == 0);
        assert!(refcount_value(targets[2]) == i32::MAX);
    }

    let positive_body_ref = Cell::new(0);
    let positive_result = match unsafe {
        with_remote_target(pids[0], node, find, unlock, |actual| {
            assert!(actual == targets[0]);
            crate::host_effects::assert_effects_unlocked("positive target body");
            assert!(crate::host_effects::irq_enabled());
            crate::host_effects::marker("target_body");
            positive_body_ref.set(refcount_value(actual));
            // Full-width negative body result, deliberately outside CInt.
            -4_294_967_301_i64
        })
    } {
        Ok(value) => value,
        Err(_) => panic!("actual positive target was refused"),
    };
    let positive_final_ref = unsafe { refcount_value(targets[0]) };

    let zero_body_calls = Cell::new(0_usize);
    let zero_error = match unsafe {
        with_remote_target(pids[1], node, find, unlock, |_| {
            zero_body_calls.set(zero_body_calls.get() + 1);
            0
        })
    } {
        Err(error) => error,
        Ok(_) => panic!("actual target helper resurrected a zero-count Process"),
    };
    let zero_final_ref = unsafe { refcount_value(targets[1]) };

    let overflow_body_calls = Cell::new(0_usize);
    let overflow_error = match unsafe {
        with_remote_target(pids[2], node, find, unlock, |_| {
            overflow_body_calls.set(overflow_body_calls.get() + 1);
            0
        })
    } {
        Err(error) => error,
        Ok(_) => panic!("actual target helper overflowed its positive edge"),
    };
    let overflow_final_ref = unsafe { refcount_value(targets[2]) };

    TargetObservation {
        positive_body_ref: positive_body_ref.get(),
        positive_result,
        positive_final_ref,
        zero_error,
        zero_body_calls: zero_body_calls.get(),
        zero_final_ref,
        overflow_error,
        overflow_body_calls: overflow_body_calls.get(),
        overflow_final_ref,
    }
}
