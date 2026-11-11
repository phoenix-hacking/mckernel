// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// HOST actual-source VM descriptor-drain caller, included INSIDE the real owner
// module by the independent common fixture. Author has not compiled/executed it.
// SDK explicitly released this file without creating a draft. No other family,
// production unit, common binding, or ownership algorithm is modified here.

use core::ffi::{c_void, CStr};
use core::mem::offset_of;
use core::ptr::{addr_of, addr_of_mut, read_volatile};
use core::sync::atomic::Ordering;
use crate::abi;
use crate::host_effects::{self, Effect, LockClass};

const PINNED_FD: abi::CLong = 301;
const UNPINNED_FD: abi::CLong = 302;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct VmFreePhase {
    pub(super) published_event_frees: usize,
    pub(super) descriptor_backing_frees: usize,
    pub(super) abort_event_frees: usize,
    pub(super) pinned_event_or_descriptor_freed: bool,
    pub(super) origin_bitmap_matches_expected: bool,
    pub(super) unresolved_host_route_delta: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct VmDrainObservation {
    pub(super) actual_two_host_opens: usize,
    pub(super) actual_admitted_pin_retained: bool,
    pub(super) close_all_result: abi::CInt,
    pub(super) drain_free_result: abi::CInt,
    pub(super) actual_head_detached_under_p: bool,
    pub(super) origin_bitmap_unchanged_under_p: bool,
    pub(super) under_p_process_lock_entries: usize,
    pub(super) under_p_allocations: usize,
    pub(super) under_p_frees: usize,
    pub(super) under_p_host_calls: usize,
    pub(super) under_p_state_lock_entries: usize,
    pub(super) under_p_hash_actions: usize,
    pub(super) irq_restored_after_p: bool,
    pub(super) before_last_pin_drop: VmFreePhase,
    pub(super) after_last_pin_drop: VmFreePhase,
    pub(super) no_host_close_or_fabricated_ack_in_vm_drains: bool,
    pub(super) final_unresolved_record_allocation_delta: usize,
    pub(super) repeated_drain_has_no_retry: bool,
    pub(super) actual_schedule_calls: usize,
    pub(super) positive_actor_vm_links_preserved: bool,
    pub(super) blocked_wait_or_native_behavior_proven: bool,
}

/// External literal scalar oracle. Two completed opens create two real host
/// routes. VM mark/drain cannot issue those numeric closes under P or from idle;
/// both routes remain explicit debt after their LOCAL backing is safely freed.
pub(super) const EXPECTED_VM_DRAIN_OBSERVATION: VmDrainObservation = VmDrainObservation {
    actual_two_host_opens: 2,
    actual_admitted_pin_retained: true,
    close_all_result: 2,
    drain_free_result: 2,
    actual_head_detached_under_p: true,
    origin_bitmap_unchanged_under_p: true,
    under_p_process_lock_entries: 1,
    under_p_allocations: 0,
    under_p_frees: 0,
    under_p_host_calls: 0,
    under_p_state_lock_entries: 0,
    under_p_hash_actions: 0,
    irq_restored_after_p: true,
    before_last_pin_drop: VmFreePhase {
        published_event_frees: 1, descriptor_backing_frees: 1, abort_event_frees: 0,
        pinned_event_or_descriptor_freed: false, origin_bitmap_matches_expected: true,
        unresolved_host_route_delta: 1,
    },
    after_last_pin_drop: VmFreePhase {
        published_event_frees: 2, descriptor_backing_frees: 2, abort_event_frees: 0,
        pinned_event_or_descriptor_freed: true, origin_bitmap_matches_expected: true,
        unresolved_host_route_delta: 2,
    },
    no_host_close_or_fabricated_ack_in_vm_drains: true,
    final_unresolved_record_allocation_delta: 2,
    repeated_drain_has_no_retry: true,
    actual_schedule_calls: 0,
    positive_actor_vm_links_preserved: true,
    blocked_wait_or_native_behavior_proven: false,
};

unsafe fn bitmap(actor: *mut abi::Thread) -> abi::CULong {
    unsafe { read_volatile(addr_of!((*actor).pmc_alloc_map)) }
}

/// Only lower allocator observations, keyed to the actual two published
/// descriptor/event addresses captured while their genuine list/pin owns them.
fn frees(
    pinned_descriptor: usize, unpinned_descriptor: usize,
    pinned_event: usize, unpinned_event: usize,
) -> (usize, usize, usize, bool) {
    let (alloc_file, abort_line, close_file, close_line) = unsafe {
        (CStr::from_ptr(addr_of!(super::super::f03_mckfd_alloc_origin_file_v1).cast()).to_bytes(),
         super::super::F03_PERF_FREE_ORIGIN_LINE_V1,
         CStr::from_ptr(addr_of!(super::super::f03_mckfd_free_origin_file_v1).cast()).to_bytes(),
         super::super::f03_mckfd_free_origin_line_v1)
    };
    let mut events = 0; let mut descriptors = 0; let mut aborts = 0; let mut pinned = false;
    for effect in host_effects::snapshot().iter() {
        if let Effect::Free { record, file, line } = effect {
            let is_event = record.address == pinned_event || record.address == unpinned_event;
            let is_descriptor = record.address == pinned_descriptor || record.address == unpinned_descriptor;
            if file.as_slice() == close_file && *line == close_line {
                if is_event { events += 1; }
                if is_descriptor { descriptors += 1; }
            }
            if is_event && file.as_slice() == alloc_file && *line == abort_line { aborts += 1; }
            pinned |= record.address == pinned_event || record.address == pinned_descriptor;
        }
    }
    (events, descriptors, aborts, pinned)
}

unsafe fn phase(
    actor: *mut abi::Thread, expected_bitmap: abi::CULong, debt_before: usize,
    pinned_descriptor: usize, unpinned_descriptor: usize,
    pinned_event: usize, unpinned_event: usize,
) -> VmFreePhase {
    let (events, descriptors, aborts, pinned) = frees(pinned_descriptor, unpinned_descriptor,
        pinned_event, unpinned_event);
    VmFreePhase {
        published_event_frees: events, descriptor_backing_frees: descriptors, abort_event_frees: aborts,
        pinned_event_or_descriptor_freed: pinned,
        origin_bitmap_matches_expected: unsafe { bitmap(actor) == expected_bitmap },
        unresolved_host_route_delta: unsafe { super::descriptors::unresolved_host_closes() }
            .checked_sub(debt_before).expect("actual host debt cannot silently disappear"),
    }
}

/// Common supplies positive, initialized ABI Process/Thread/ProcessVm backing,
/// real lifecycle/map metadata, no FDs, and one actual validated Copy Open with
/// live request/attr and genuine production callbacks. It keeps actor backing
/// quarantined after this case: unresolved creator-host routes are not ACKed or
/// released by this scalar observation. No real kernel/VM/native object exists.
pub(super) unsafe fn exercise_vm_drain_family(
    actor: *mut abi::Thread, configuration: super::Open,
) -> VmDrainObservation {
    assert!(!actor.is_null());
    let process = unsafe { (*actor).proc };
    assert!(!process.is_null() && configuration.thread == actor.cast() && configuration.proc == process.cast());
    let vm = unsafe { (*process).vm };
    assert!(!vm.is_null() && unsafe { (*actor).vm == vm && (*vm).proc == process });
    assert!(unsafe { (*process).refcount.counter > 0 && (*vm).refcount.counter > 0 });
    assert!(unsafe { (*process).mckfd.is_null() && bitmap(actor) == 0 });
    assert_eq!(configuration.group_fd, -1);
    unsafe { host_effects::set_current(actor); super::drain_safe_point(); }
    let baseline_allocations = host_effects::live_allocations().len();
    let initial_debt = unsafe { super::descriptors::unresolved_host_closes() };
    host_effects::reset_trace();host_effects::set_host_replies(&[PINNED_FD, UNPINNED_FD]);
    assert_eq!(unsafe { super::transactions::open_from_body(configuration) }, PINNED_FD);
    unsafe { super::host_register_event_state(process, PINNED_FD as abi::CInt) };
    let first_origin = unsafe { bitmap(actor) };
    assert_eq!(first_origin.count_ones(), 1);
    assert_eq!(unsafe { super::transactions::open_from_body(configuration) }, UNPINNED_FD);
    unsafe { super::host_register_event_state(process, UNPINNED_FD as abi::CInt) };
    let both_origins = unsafe { bitmap(actor) };
    assert_eq!(both_origins.count_ones(), 2);
    let opens = host_effects::snapshot().iter().filter(|effect| matches!(effect,
        Effect::HostReply { thread, process: route, result, .. }
        if *thread == actor as usize && *route == process as usize && (*result == PINNED_FD || *result == UNPINNED_FD))).count();
    assert_eq!(opens, 2);

    host_effects::reset_trace(); // observation only; never resets live ownership
    let irq_before = host_effects::irq_enabled();
    let schedule_before = crate::platform_bindings::SCHEDULE_CALLS.load(Ordering::SeqCst);
    let lock = unsafe { addr_of_mut!((*process).mckfd_lock) }.cast::<c_void>();
    let flags = unsafe { super::super::syscall_mckfd_lock_bridge(lock) };
    let mut first = core::ptr::null_mut::<abi::Mckfd>();
    let mut second = core::ptr::null_mut::<abi::Mckfd>();
    let mut row = unsafe { (*process).mckfd.cast::<abi::Mckfd>() };
    while !row.is_null() {
        if unsafe { (*row).fd } == PINNED_FD as abi::CInt { first = row; }
        if unsafe { (*row).fd } == UNPINNED_FD as abi::CInt { second = row; }
        row = unsafe { (*row).next };
    }
    if first.is_null() || second.is_null() {
        unsafe { super::super::syscall_mckfd_unlock_bridge(lock, flags) };
        panic!("actual two published descriptor nodes missing");
    }
    let pin_result = unsafe { super::pin_managed_locked(process, first) };
    let storage_pin = match pin_result {
        Ok(Some(pin)) => pin,
        _ => {
            unsafe { super::super::syscall_mckfd_unlock_bridge(lock, flags) };
            panic!("actual pre-unlock managed storage pin missing");
        }
    };
    // Addresses are scalar observation identities, never dereferenced after
    // their actual free. No fabricated pin is installed on the second node.
    let first_event = unsafe { (*first).data as usize };
    let second_event = unsafe { (*second).data as usize };
    let marked = unsafe { crate::process_helpers::process_mckfd_close_all_result(
        (*process).mckfd, offset_of!(abi::Mckfd, next) as abi::CULong,
        offset_of!(abi::Mckfd, close_cb) as abi::CULong,
    ) };
    if marked != 2 {
        unsafe { super::super::syscall_mckfd_unlock_bridge(lock, flags) };
        drop(storage_pin);
        panic!("actual VM close_all did not mark both managed descriptors");
    }
    // This is the COMPLETE production drain_free body. It invokes the COMPLETE
    // real process_mckfd_free_result for each node WHILE this genuine P is held.
    // None of the three source bodies is mirrored by this test caller.
    let drained = unsafe { crate::process_helpers::process_mckfd_drain_free_result(
        addr_of_mut!((*process).mckfd), offset_of!(abi::Mckfd, next) as abi::CULong,
        Some(super::super::syscall_mckfd_free_bridge),
    ) };
    let head_detached = unsafe { (*process).mckfd.is_null() };
    let map_unchanged = unsafe { bitmap(actor) == both_origins };
    unsafe { super::super::syscall_mckfd_unlock_bridge(lock, flags) };
    let irq_restored = host_effects::irq_enabled() == irq_before;
    // The trace is copied only AFTER P unlock: even test observation does not
    // allocate a Vec while the production process lock is held.
    let under_p = host_effects::snapshot();
    let allocations = under_p.iter().filter(|effect| matches!(effect, Effect::Alloc { .. } | Effect::AllocFailed { .. })).count();
    let frees_under_p = under_p.iter().filter(|effect| matches!(effect, Effect::Free { .. } | Effect::FreeNull { .. })).count();
    let hosts = under_p.iter().filter(|effect| matches!(effect, Effect::HostReply { .. } | Effect::ForwardClose { .. })).count();
    let p_entries = under_p.iter().filter(|effect| matches!(effect, Effect::Lock { lock } if lock.class == LockClass::Process)).count();
    let s_entries = under_p.iter().filter(|effect| matches!(effect, Effect::Lock { lock } if lock.class == LockClass::State)).count();
    let hash = under_p.iter().filter(|effect| matches!(effect, Effect::HashFind { .. } | Effect::HashUnlock { .. })).count();
    assert_eq!(drained, 2);

    unsafe { super::drain_safe_point(); }
    let before_pin = unsafe { phase(actor, first_origin, initial_debt,
        first as usize, second as usize, first_event, second_event) };
    assert_eq!(before_pin, EXPECTED_VM_DRAIN_OBSERVATION.before_last_pin_drop);
    drop(storage_pin);
    unsafe { super::drain_safe_point(); }
    let after_pin = unsafe { phase(actor, 0, initial_debt,
        first as usize, second as usize, first_event, second_event) };
    assert_eq!(after_pin, EXPECTED_VM_DRAIN_OBSERVATION.after_last_pin_drop);
    let retained = host_effects::live_allocations().len().checked_sub(baseline_allocations)
        .expect("actual unresolved route records remain allocated");
    let prior_trace = host_effects::snapshot();
    let prior_host_count = prior_trace.iter().filter(|effect| matches!(effect, Effect::HostReply { .. } | Effect::ForwardClose { .. })).count();
    unsafe { super::drain_safe_point(); }
    let later_host_count = host_effects::snapshot().iter().filter(|effect| matches!(effect, Effect::HostReply { .. } | Effect::ForwardClose { .. })).count();
    let schedule_after = crate::platform_bindings::SCHEDULE_CALLS.load(Ordering::SeqCst);

    VmDrainObservation {
        actual_two_host_opens: opens, actual_admitted_pin_retained: true,
        close_all_result: marked, drain_free_result: drained,
        actual_head_detached_under_p: head_detached, origin_bitmap_unchanged_under_p: map_unchanged,
        under_p_process_lock_entries: p_entries, under_p_allocations: allocations,
        under_p_frees: frees_under_p, under_p_host_calls: hosts,
        under_p_state_lock_entries: s_entries, under_p_hash_actions: hash,
        irq_restored_after_p: irq_restored, before_last_pin_drop: before_pin, after_last_pin_drop: after_pin,
        no_host_close_or_fabricated_ack_in_vm_drains: prior_host_count == 0 && later_host_count == 0,
        final_unresolved_record_allocation_delta: retained,
        repeated_drain_has_no_retry: prior_host_count == later_host_count
            && unsafe { super::descriptors::unresolved_host_closes() } == initial_debt + 2,
        actual_schedule_calls: if schedule_before == 0 { schedule_after } else { usize::MAX },
        positive_actor_vm_links_preserved: unsafe { (*actor).vm == vm && (*process).vm == vm
            && (*vm).proc == process && (*process).refcount.counter > 0 && (*vm).refcount.counter > 0 },
        blocked_wait_or_native_behavior_proven: false,
    }
}
