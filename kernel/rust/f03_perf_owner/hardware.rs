// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// PRIVATE UNWIRED managed-perf hardware/accounting implementation; no activation.
// Source/API origin: HARDWARE-UNIT-INTERFACE.json 5f15dee41804a8823159719cb4964658b407111e43efed849ab5d53d86b9a555.
// Actual math: ancestor perf_{start,reset,stop}_apply_event_result,
// perf_event_read_value_entry_body_result and sync_child_event_apply_action.
// Actual C-header data: f03_perf_event_layout_v1/f03_perf_counter_providers_v1,
// f03_perf_read_layout_v1/f03_perf_read_providers_v1; no guessed offsets/providers.
// Stable additions confirmed by P03: capture_one_locked and transferred-R entries.
// A stop operation needs a third same-epoch snapshot for its update-after-stop
// pass. All snapshots and all real Operation tokens are captured under ONE R.

use core::ffi::c_void;
use core::mem::{offset_of, size_of};
use core::ptr::{addr_of, addr_of_mut, null_mut, read_volatile, write_volatile};
use crate::abi::{CInt, CLong, CULong, Thread};
use super::descriptors::Locked;
use super::events::{EventBorrow, EventPin};
use super::groups::GroupRead;
use super::maps::HardwareLeases;
use super::runtime::RuntimeWindow;
use super::super::f03_sync_child_layout_v2::FullMcPerfEvent as Event;
use super::super::f03_perf_counter_control_v1::{
    f03_perf_counter_providers_v1 as COUNTERS, f03_perf_event_layout_v1 as CONTROL,
};
use super::super::f03_perf_read_entries_v1::{
    f03_perf_read_layout_v1 as READ_LAYOUT, f03_perf_read_providers_v1 as READERS,
};
use super::super::{
    perf_event_bit_result, perf_event_read_value_entry_body_result,
    perf_reset_apply_event_result, perf_start_apply_event_result,
    perf_stop_apply_event_result, sync_child_event_apply_action,
    sync_child_event_needed_result, sync_child_event_pid_action_result,
    f03_sync_child_perf_read_v2, f03_sync_child_count_set_v2,
    syscall_copy_to_user_bridge, PERF_STOP_EVENT_CAPACITY, SYNC_CHILD_EVENT_ACTION_NONE,
};

const EINVAL: CLong = 22;
const EFAULT: CLong = 14;

struct Operation<'a> {
    walk: GroupRead<'a>,
    after_stop: Option<GroupRead<'a>>,
    leases: HardwareLeases,
}

/// Transfers the caller's SAME R through snapshot and complete Operation-token
/// capture. No allocator, extra-register reservation, hardware or S acquisition.
/// The existing EventPin owns the GroupRef; there is no self-referential guard.
unsafe fn capture<'a>(
    event: &'a EventPin, thread: *mut Thread, mut r: Locked, after_stop: bool,
) -> Result<Operation<'a>, CLong> {
    if thread.is_null() { return Err(-EINVAL); }
    let group = event.selected_group();
    let mut mapping = unsafe { group.read_locked(&mut r) };
    let walk = unsafe { group.read_locked(&mut r) };
    let follow = if after_stop { Some(unsafe { group.read_locked(&mut r) }) } else { None };
    let leases = unsafe { HardwareLeases::capture_locked(thread, &mut mapping, &mut r) };
    unsafe { mapping.finish_locked(&mut r) };
    match leases {
        Ok(leases) => {
            drop(r);
            Ok(Operation { walk, after_stop: follow, leases })
        }
        Err(error) => {
            unsafe { walk.finish_locked(&mut r) };
            if let Some(follow) = follow { unsafe { follow.finish_locked(&mut r) }; }
            drop(r);
            Err(error as CLong)
        }
    }
}

/// Read ONE stable topology step under R, then release R before any S/provider.
fn next<'a>(walk: &'a mut GroupRead<'_>) -> Option<EventBorrow<'a>> {
    let mut r = unsafe { Locked::take() };
    unsafe { walk.next_locked(&mut r) }
}

/// Same existing read-value body, with the caller's actual executing/scheduler-
/// owned Thread rather than a nested CPU-local lookup that could name another
/// Thread. Caller already holds S and its matching RuntimeWindow; no new lock.
unsafe fn value_window(raw: *mut c_void, thread: *mut Thread) -> CULong {
    unsafe { perf_event_read_value_entry_body_result(
        raw, thread.cast(), READ_LAYOUT.attr, READ_LAYOUT.pid,
        READ_LAYOUT.use_invariant_tsc, READ_LAYOUT.count, READ_LAYOUT.child_count_total,
        READ_LAYOUT.base_user_tsc, READ_LAYOUT.stopped_user_tsc, READ_LAYOUT.user_accum_count,
        READ_LAYOUT.base_system_tsc, READ_LAYOUT.stopped_system_tsc, READ_LAYOUT.system_accum_count,
        offset_of!(Thread, user_tsc), offset_of!(Thread, system_tsc),
        READERS.attr_flags, READERS.update, READERS.atomic_read,
    ) }
}

/// The actual perf_counter_set_entry/body order, factored only to pass a genuine
/// pre-reserved local extra index and to observe whether its MSR was programmed.
/// Its signed result remains ignored by start, as the original apply body did.
/// No original extra_set callback is used: that callback allocates Thread map
/// state, whereas the actual managed_set_extra_reserved primitive does not.
unsafe fn configure_window(raw: *mut Event, extra: Option<CInt>) -> (CInt, bool) {
    let Some(attr_flags) = (unsafe { COUNTERS.attr_flags }) else { return (-EINVAL as CInt, false); };
    let mut exclude_kernel = 0;
    let mut exclude_user = 0;
    let rc = unsafe { attr_flags(addr_of!((*raw).attr).cast(), &mut exclude_kernel, &mut exclude_user) };
    if rc != 0 { return (rc, false); }
    let Some(init_raw) = (unsafe { COUNTERS.init_raw }) else { return (-EINVAL as CInt, false); };
    let mut mode = 0;
    if exclude_kernel == 0 { mode |= unsafe { CONTROL.kernel_mode }; }
    if exclude_user == 0 { mode |= unsafe { CONTROL.user_mode }; }
    let mut programmed = false;
    if unsafe { read_volatile(addr_of!((*raw).extra_reg.reg)) } != 0 {
        let Some(index) = extra else { return (-1, false); };
        let rc = unsafe { crate::x86_perfctr::managed_set_extra_reserved(raw.cast(), index) };
        if rc != 0 { return (-1, false); }
        programmed = true;
    }
    let rc = unsafe { init_raw(read_volatile(addr_of!((*raw).counter_id)),
        read_volatile(addr_of!((*raw).hw_config)), mode) };
    (rc, programmed)
}

unsafe fn start_event(
    event: &EventBorrow<'_>, leases: &HardwareLeases, thread: *mut Thread, mask: &mut CULong,
) -> CLong {
    let key = event.key();
    let raw = event.raw_event().cast::<Event>();
    let physical = leases.index(key);
    let Some(mask_check) = (unsafe { COUNTERS.mask_check }) else { return -EINVAL; };
    // Inspect the genuine per-executing-Thread template under S, then release S
    // BEFORE reserve_extra takes R. It is never inferred from a measurement or
    // from reg!=0 alone that an extra-register map bit is already owned.
    let extra_template = {
        let state = unsafe { event.state() };
        let window = unsafe { RuntimeWindow::enter(raw.cast(), leases.runtime(key), physical, None) };
        let needs = unsafe { read_volatile(addr_of!((*raw).state)) == CONTROL.inactive_state
            && read_volatile(addr_of!((*raw).use_invariant_tsc)) == 0
            && read_volatile(addr_of!((*raw).extra_reg.reg)) != 0 };
        let preferred = unsafe { read_volatile(addr_of!((*raw).extra_reg.idx)) };
        drop(window); drop(state);
        if needs { Some(preferred) } else { None }
    };
    let reservation = extra_template.and_then(|preferred| unsafe { leases.reserve_extra(key, preferred).ok() });
    let extra = reservation.map(|(index, _)| index);
    let mut programmed = false;
    let rc = {
        let state = unsafe { event.state() };
        let window = unsafe { RuntimeWindow::enter(raw.cast(), leases.runtime(key), physical, extra) };
        let bit = perf_event_bit_result(physical);
        let rc = if unsafe { read_volatile(addr_of!((*raw).use_invariant_tsc)) } != 0 {
            // Exact existing invariant-TSC accumulation/base/stopped arithmetic.
            unsafe { perf_start_apply_event_result(
                raw.cast(), thread.cast(), mask, CONTROL.counter_id, CONTROL.state,
                CONTROL.use_invariant_tsc, CONTROL.base_user_tsc, CONTROL.stopped_user_tsc,
                CONTROL.user_accum_count, CONTROL.base_system_tsc, CONTROL.stopped_system_tsc,
                CONTROL.system_accum_count, offset_of!(Thread, user_tsc), offset_of!(Thread, system_tsc),
                CONTROL.inactive_state, CONTROL.active_state, mask_check, None, None,
            ) }
        } else if unsafe { bit == 0 || mask_check(bit) == 0
            || read_volatile(addr_of!((*raw).state)) != CONTROL.inactive_state } {
            0
        } else if let Some(set_period) = unsafe { COUNTERS.set_period } {
            unsafe { set_period(raw.cast()) };
            let (ignored_original_rc, did_program) = unsafe { configure_window(raw, extra) };
            let _ = ignored_original_rc; // original start deliberately ignored counter_set's signed status
            programmed = did_program;
            *mask |= bit;
            unsafe { write_volatile(addr_of_mut!((*raw).state), CONTROL.active_state) };
            0
        } else { -EINVAL };
        drop(window); drop(state);
        rc
    };
    if let Some((index, true)) = reservation {
        if !programmed {
            // Only the exact newly reserved, UNPROGRAMMED bit can be rolled
            // back. An old map/foreign bit or programmed MSR is never guessed.
            unsafe { leases.abort_new_extra(key, index) };
        }
    }
    rc
}

pub(super) unsafe fn start(event: &EventPin, thread: *mut Thread) -> CLong {
    unsafe { start_locked(event, thread, Locked::take()) }
}
pub(super) unsafe fn start_locked(event: &EventPin, thread: *mut Thread, r: Locked) -> CLong {
    let mut operation = match unsafe { capture(event, thread, r, false) } { Ok(op) => op, Err(error) => return error };
    unsafe { start_walk(event, thread, &mut operation.walk, &operation.leases) }
}

/// Run the original complete start step on an ALREADY CAPTURED member epoch
/// and its actual per-executing-Thread Operation leases. No new epoch capture.
unsafe fn start_walk(
    event: &EventPin, thread: *mut Thread, walk: &mut GroupRead<'_>, leases: &HardwareLeases,
) -> CLong {
    let mut mask = 0;
    while let Some(member) = next(walk) {
        let rc = unsafe { start_event(&member, leases, thread, &mut mask) };
        if rc != 0 { return rc; }
    }
    if mask != 0 {
        let Some(start) = (unsafe { COUNTERS.counter_start }) else { return -EINVAL; };
        let state = unsafe { event.state() };
        unsafe { start(mask) };
        drop(state);
    }
    let process = unsafe { read_volatile(addr_of!((*thread).proc)) };
    if process.is_null() { return -EINVAL; }
    let _r = unsafe { Locked::take() };
    unsafe { write_volatile(addr_of_mut!((*process).perf_status), CONTROL.pp_count) };
    0
}

unsafe fn reset_event(event: &EventBorrow<'_>, leases: &HardwareLeases, thread: *mut Thread) -> CLong {
    let key = event.key(); let raw = event.raw_event().cast::<Event>();
    let Some(mask_check) = (unsafe { COUNTERS.mask_check }) else { return -EINVAL; };
    let state = unsafe { event.state() };
    let window = unsafe { RuntimeWindow::enter(raw.cast(), leases.runtime(key), leases.index(key), None) };
    let bit = perf_event_bit_result(unsafe { read_volatile(addr_of!((*raw).counter_id)) });
    let rc = if unsafe { read_volatile(addr_of!((*raw).use_invariant_tsc)) } != 0 {
        unsafe { perf_reset_apply_event_result(
            raw.cast(), thread.cast(), CONTROL.counter_id, CONTROL.use_invariant_tsc,
            CONTROL.base_user_tsc, CONTROL.stopped_user_tsc, CONTROL.user_accum_count,
            CONTROL.base_system_tsc, CONTROL.stopped_system_tsc, CONTROL.system_accum_count,
            CONTROL.count, offset_of!(Thread, user_tsc), offset_of!(Thread, system_tsc),
            mask_check, None, None,
        ) }
    } else if bit == 0 || unsafe { mask_check(bit) } == 0 { 0 }
    else if unsafe { COUNTERS.read_value }.is_none() { -EINVAL }
    else if let Some(set_count) = unsafe { COUNTERS.atomic_set } {
        // Same read-before-zero order, but the full existing reader receives
        // this actual Thread explicitly instead of a nested CPU-local lookup.
        unsafe { value_window(raw.cast(), thread); set_count(addr_of_mut!((*raw).count).cast(), 0) };
        0
    } else { -EINVAL };
    drop(window); drop(state); rc
}

pub(super) unsafe fn reset(event: &EventPin, thread: *mut Thread) -> CLong {
    unsafe { reset_locked(event, thread, Locked::take()) }
}
pub(super) unsafe fn reset_locked(event: &EventPin, thread: *mut Thread, r: Locked) -> CLong {
    let mut operation = match unsafe { capture(event, thread, r, false) } { Ok(op) => op, Err(error) => return error };
    unsafe { reset_walk(thread, &mut operation.walk, &operation.leases) }
}

/// Preserve the original reset step, including its early return within THIS
/// step. A later original void scheduler step still runs even after an error.
unsafe fn reset_walk(
    thread: *mut Thread, walk: &mut GroupRead<'_>, leases: &HardwareLeases,
) -> CLong {
    while let Some(member) = next(walk) {
        let rc = unsafe { reset_event(&member, leases, thread) };
        if rc != 0 { return rc; }
    }
    0
}

/// ONE actual member epoch/tail and ONE complete actual mapping lease set for
/// the scheduler's entire original reset/reset/start transaction. All cursors
/// are captured under the same R, so they share sequence, tail and epoch even
/// if another CPU clears the Process monitor and appends after R unlock.
struct SwitchSequence<'a> {
    initial_reset: Option<GroupRead<'a>>,
    reset: GroupRead<'a>,
    start: GroupRead<'a>,
    leases: HardwareLeases,
}
unsafe fn capture_switch_sequence<'a>(
    event: &'a EventPin, thread: *mut Thread, mut r: Locked, initial_reset: bool,
) -> Result<SwitchSequence<'a>, CLong> {
    if thread.is_null() { return Err(-EINVAL); }
    let group = event.selected_group();
    let mut mapping = unsafe { group.read_locked(&mut r) };
    let first = if initial_reset { Some(unsafe { group.read_locked(&mut r) }) } else { None };
    let reset = unsafe { group.read_locked(&mut r) };
    let start = unsafe { group.read_locked(&mut r) };
    let leases = unsafe { HardwareLeases::capture_locked(thread, &mut mapping, &mut r) };
    unsafe { mapping.finish_locked(&mut r) };
    match leases {
        Ok(leases) => {
            drop(r);
            Ok(SwitchSequence { initial_reset: first, reset, start, leases })
        }
        Err(error) => {
            if let Some(first) = first { unsafe { first.finish_locked(&mut r) }; }
            unsafe { reset.finish_locked(&mut r); start.finish_locked(&mut r); }
            drop(r);
            Err(error as CLong)
        }
    }
}

/// Scheduler-only complete original void-call sequence. Err denotes failure to
/// capture its PREBOUND maps before any hardware step; lifecycle treats that as
/// the existing protocol invariant failure rather than silently truncating.
/// Ok contains the first real helper status for precise diagnostics. Original
/// void semantics are retained: execute EACH scheduled step even if a prior
/// helper returned nonzero, then deliberately ignore that backend status.
/// No allocation/wait, R across S/providers, new cursor or late map lookup.
pub(super) unsafe fn switch_sequence_locked(
    event: &EventPin, thread: *mut Thread, r: Locked, initial_reset: bool,
) -> Result<CLong, CLong> {
    let mut sequence = unsafe { capture_switch_sequence(event, thread, r, initial_reset) }?;
    let mut first_error = 0;
    if let Some(first) = sequence.initial_reset.as_mut() {
        let result = unsafe { reset_walk(thread, first, &sequence.leases) };
        if result != 0 { first_error = result; }
    }
    let result = unsafe { reset_walk(thread, &mut sequence.reset, &sequence.leases) };
    if first_error == 0 && result != 0 { first_error = result; }
    let result = unsafe { start_walk(event, thread, &mut sequence.start, &sequence.leases) };
    if first_error == 0 && result != 0 { first_error = result; }
    Ok(first_error)
}

pub(super) unsafe fn stop(event: &EventPin, thread: *mut Thread) -> CLong {
    unsafe { stop_locked(event, thread, Locked::take()) }
}
pub(super) unsafe fn stop_locked(event: &EventPin, thread: *mut Thread, r: Locked) -> CLong {
    let mut operation = match unsafe { capture(event, thread, r, true) } { Ok(op) => op, Err(error) => return error };
    let Some(mask_check) = (unsafe { COUNTERS.mask_check }) else { return -EINVAL; };
    let mut mask = 0;
    let mut stopped = [null_mut::<c_void>(); PERF_STOP_EVENT_CAPACITY];
    let mut used = 0;
    while let Some(member) = next(&mut operation.walk) {
        let key = member.key(); let raw = member.raw_event();
        let state = unsafe { member.state() };
        let window = unsafe { RuntimeWindow::enter(raw, operation.leases.runtime(key), operation.leases.index(key), None) };
        let rc = unsafe { perf_stop_apply_event_result(
            raw.cast(), thread.cast(), &mut mask, &mut stopped, &mut used,
            CONTROL.counter_id, CONTROL.state, CONTROL.use_invariant_tsc,
            CONTROL.stopped_user_tsc, CONTROL.stopped_system_tsc,
            offset_of!(Thread, user_tsc), offset_of!(Thread, system_tsc),
            CONTROL.active_state, CONTROL.inactive_state, mask_check,
        ) };
        drop(window); drop(state);
        if rc != 0 { return rc; }
    }
    if mask != 0 {
        let Some(stop) = (unsafe { COUNTERS.counter_stop }) else { return -EINVAL; };
        let Some(update) = (unsafe { COUNTERS.event_update }) else { return -EINVAL; };
        {
            let state = unsafe { event.state() };
            unsafe { stop(mask, 0) };
            drop(state);
        }
        // Exactly stop-the-whole-mask THEN update each stopped event, with each
        // update reentering its OWN S and actual local RuntimeWindow. The third
        // snapshot has the same initial epoch/sequence/tail as the first pass.
        let follow = operation.after_stop.as_mut().expect("perf stop follow-up snapshot");
        while let Some(member) = next(follow) {
            let raw = member.raw_event();
            if !stopped.iter().take(used).any(|value| *value == raw) { continue; }
            let key = member.key();
            let state = unsafe { member.state() };
            let window = unsafe { RuntimeWindow::enter(raw, operation.leases.runtime(key), operation.leases.index(key), None) };
            unsafe { update(raw) };
            drop(window); drop(state);
        }
    }
    // The common owner clears the exact current association under R and writes
    // original PP_NONE only on successful completion. No raw monitor clear here.
    0
}

pub(super) unsafe fn sync(event: &EventPin, thread: *mut Thread) -> CLong {
    unsafe { sync_locked(event, thread, Locked::take()) }
}
pub(super) unsafe fn sync_locked(event: &EventPin, thread: *mut Thread, r: Locked) -> CLong {
    let input_pid = unsafe { read_volatile(addr_of!((*event.raw_event().cast::<Event>()).pid)) };
    if sync_child_event_needed_result(1, event.inherit_enabled() as CInt, input_pid) == 0 {
        drop(r); return 0;
    }
    let mut operation = match unsafe { capture(event, thread, r, false) } { Ok(op) => op, Err(error) => return error };
    let mut leader = true;
    while let Some(member) = next(&mut operation.walk) {
        let raw = member.raw_event().cast::<Event>();
        let action = sync_child_event_pid_action_result(if leader {
            unsafe { read_volatile(addr_of!((*raw).pid)) }
        } else { input_pid });
        // Original leader action NONE terminates the whole sync; original
        // sibling action is selected by the INPUT event pid, not each sibling.
        if action == SYNC_CHILD_EVENT_ACTION_NONE { return 0; }
        leader = false;
        let key = member.key();
        let state = unsafe { member.state() };
        let window = unsafe { RuntimeWindow::enter(raw.cast(), operation.leases.runtime(key), operation.leases.index(key), None) };
        let rc = unsafe { sync_child_event_apply_action(raw.cast(), action,
            CONTROL.counter_id, CONTROL.count, READ_LAYOUT.child_count_total,
            f03_sync_child_perf_read_v2, Some(f03_sync_child_count_set_v2)) };
        drop(window); drop(state);
        if rc != 0 { return rc; }
    }
    0
}

pub(super) unsafe fn read(
    event: &EventPin, thread: *mut Thread, buf: CULong, count: CULong, read_format: CULong,
) -> CLong {
    unsafe { read_locked(event, thread, buf, count, read_format, Locked::take()) }
}

pub(super) unsafe fn read_locked(
    event: &EventPin, thread: *mut Thread, buf: CULong, _count: CULong,
    read_format: CULong, mut r: Locked,
) -> CLong {
    if thread.is_null() { return -EINVAL; }
    if read_format & unsafe { READ_LAYOUT.group_flag } == 0 {
        // An admitted descriptor callback may begin after logical close; its
        // storage/Origin is still real. Capture this EXACT event, even if a new
        // selected-group snapshot has already omitted its retired member node.
        let leases = match unsafe { HardwareLeases::capture_one_locked(thread, event.key(), &mut r) } {
            Ok(leases) => leases, Err(error) => return error as CLong,
        };
        drop(r);
        let value = {
            let state = unsafe { event.state() };
            let window = unsafe { RuntimeWindow::enter(event.raw_event(), leases.runtime(event.key()), leases.index(event.key()), None) };
            let value = unsafe { value_window(event.raw_event(), thread) };
            drop(window); drop(state); value
        };
        let values = [value];
        // Original count argument is ignored; actual usercopy determines fault.
        if unsafe { syscall_copy_to_user_bridge(buf, values.as_ptr().cast(), size_of::<CULong>()) } != 0 { return -EFAULT; }
        return size_of::<CULong>() as CInt as CLong;
    }
    let mut operation = match unsafe { capture(event, thread, r, false) } { Ok(op) => op, Err(error) => return error };
    let entries = operation.walk.event_count();
    let Some(leader) = next(&mut operation.walk) else { return -EINVAL; };
    let leader_value = {
        let state = unsafe { leader.state() };
        let window = unsafe { RuntimeWindow::enter(leader.raw_event(), operation.leases.runtime(leader.key()), operation.leases.index(leader.key()), None) };
        let value = unsafe { value_window(leader.raw_event(), thread) };
        drop(window); drop(state); value
    };
    let header = [entries as CULong, leader_value];
    let mut bytes = 2 * size_of::<CULong>();
    if unsafe { syscall_copy_to_user_bridge(buf, header.as_ptr().cast(), bytes) } != 0 { return -EFAULT; }
    while let Some(member) = next(&mut operation.walk) {
        let value = {
            let state = unsafe { member.state() };
            let window = unsafe { RuntimeWindow::enter(member.raw_event(), operation.leases.runtime(member.key()), operation.leases.index(member.key()), None) };
            let value = unsafe { value_window(member.raw_event(), thread) };
            drop(window); drop(state); value
        };
        let values = [value];
        if unsafe { syscall_copy_to_user_bridge(buf.wrapping_add(bytes as CULong), values.as_ptr().cast(), size_of::<CULong>()) } != 0 { return -EFAULT; }
        bytes = bytes.wrapping_add(size_of::<CULong>());
    }
    // Same actual callback ABI truncation as f03_perf_read_{group,one}_v1.
    bytes as CInt as CLong
}
