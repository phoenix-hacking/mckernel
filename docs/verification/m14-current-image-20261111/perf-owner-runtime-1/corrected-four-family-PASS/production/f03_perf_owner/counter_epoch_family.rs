// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// TEST-ONLY actual-source caller, included as a child of f03_perf_owner.
// Production source: first-whole-compile-1/escalation-events-1/source-overlay,
// namely cbea5552 plus the explicit-borrow events15979c5d correction.
// No author compile/run. All EventKeys, generations, groups, map tokens and
// Thread records below originate in actual production constructors/transactions.
// Only host_effects and host_perf_bindings supply declared lower effects.

use core::ptr::{addr_of, addr_of_mut, null_mut, read_volatile, write_volatile};
use core::sync::atomic::{AtomicPtr, Ordering};
use crate::abi;
use super::descriptors::Locked;
use super::events::EventPin;
use super::maps::HardwareLeases;
use super::super::f03_sync_child_layout_v2::FullMcPerfEvent as Event;

const NOWAIT: abi::CULong = 2;
// Exact selected kernel/include/process.h:575 `#define PP_RESET 1`.
const HOST_PP_RESET: abi::CInt = 1;
const CHILD_FOREIGN_BIT: abi::CULong = 1;
const CHILD_RETIRED_SENTINEL: abi::CULong = (1u64 << 63) | CHILD_FOREIGN_BIT;
const OPEN_FDS: [abi::CLong; 4] = [710, 711, 712, 713];
const SCRIPTED_INIT_FAILURE: abi::CInt = -71;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct CounterEpochObservation {
    pub(super) open_results: [abi::CLong; 4],
    pub(super) initial_group_entries: usize,
    pub(super) actor_monitor_owned_bits: u32,
    pub(super) child_inherited_owned_bits: u32,
    pub(super) child_inherited_indices_differ_from_actor: bool,
    pub(super) child_new_open_avoids_both_inherited_counters: bool,
    pub(super) child_new_open_adds_exactly_one_owned_bit: bool,
    pub(super) child_close_preserves_inherited_and_foreign_bits: bool,
    pub(super) hook_fired_once: bool,
    pub(super) hook_actor_monitor_cleared: bool,
    pub(super) hook_old_actor_operation_bits_retained: bool,
    pub(super) hook_group_entries_after_append: usize,
    pub(super) hook_late_member_mapped_for_child: bool,
    pub(super) hook_late_actor_mapping_error: abi::CInt,
    pub(super) late_constructor_window_valid: bool,
    pub(super) late_constructor_atomic_writes: usize,
    pub(super) late_constructor_atomic_values: [abi::CLong; 2],
    pub(super) late_constructor_count_then_period_order: bool,
    pub(super) reset_zero_writes: usize,
    pub(super) reset_targets_and_order_match_original_two_member_epoch: bool,
    pub(super) init_calls: usize,
    pub(super) init_statuses: [abi::CInt; 2],
    pub(super) init_indices_match_actual_actor_maps: bool,
    pub(super) aggregate_start_calls: usize,
    pub(super) aggregate_start_mask_matches_actual_actor_maps: bool,
    pub(super) critical_effect_order_preserved: bool,
    pub(super) no_late_member_scheduler_reset_or_init: bool,
    pub(super) original_start_continues_after_nonzero_init: bool,
    pub(super) actor_monitor_not_resurrected: bool,
    pub(super) actor_old_bits_released_after_sequence: bool,
    pub(super) scheduler_original_count_state_written: bool,
    pub(super) child_group_entries_after_append: usize,
    pub(super) child_old_mappings_stable_across_append: bool,
    pub(super) close_results: [abi::CLong; 4],
    pub(super) tool_origin_bits_retired_after_storage_drop: bool,
    pub(super) child_operations_hold_three_actual_mapping_bits: bool,
    pub(super) child_terminal_leaves_only_foreign_bit: bool,
    pub(super) child_delayed_operation_release_bitmap: abi::CULong,
    pub(super) all_actor_records_detached: bool,
}

/// External scalar oracle. Indices and generations are deliberately NOT made
/// up: independent observations compare the actual linear leases with the
/// actual Thread bitmap and the lower PMU trace. Four finite opens/close ACKs
/// are explicit fixture inputs; neither source success nor native acceptance
/// follows from this controlled HOST family.
pub(super) const EXPECTED_COUNTER_EPOCH_OBSERVATION: CounterEpochObservation = CounterEpochObservation {
    open_results: OPEN_FDS,
    initial_group_entries: 2,
    actor_monitor_owned_bits: 2,
    child_inherited_owned_bits: 2,
    child_inherited_indices_differ_from_actor: true,
    child_new_open_avoids_both_inherited_counters: true,
    child_new_open_adds_exactly_one_owned_bit: true,
    child_close_preserves_inherited_and_foreign_bits: true,
    hook_fired_once: true,
    hook_actor_monitor_cleared: true,
    hook_old_actor_operation_bits_retained: true,
    hook_group_entries_after_append: 3,
    hook_late_member_mapped_for_child: true,
    hook_late_actor_mapping_error: -22,
    late_constructor_window_valid: true,
    late_constructor_atomic_writes: 2,
    late_constructor_atomic_values: [0, 0],
    late_constructor_count_then_period_order: true,
    reset_zero_writes: 4,
    reset_targets_and_order_match_original_two_member_epoch: true,
    init_calls: 2,
    init_statuses: [SCRIPTED_INIT_FAILURE, 0],
    init_indices_match_actual_actor_maps: true,
    aggregate_start_calls: 1,
    aggregate_start_mask_matches_actual_actor_maps: true,
    critical_effect_order_preserved: true,
    no_late_member_scheduler_reset_or_init: true,
    original_start_continues_after_nonzero_init: true,
    actor_monitor_not_resurrected: true,
    actor_old_bits_released_after_sequence: true,
    scheduler_original_count_state_written: true,
    child_group_entries_after_append: 3,
    child_old_mappings_stable_across_append: true,
    close_results: [0, 0, 0, 0],
    tool_origin_bits_retired_after_storage_drop: true,
    child_operations_hold_three_actual_mapping_bits: true,
    child_terminal_leaves_only_foreign_bit: true,
    child_delayed_operation_release_bitmap: CHILD_RETIRED_SENTINEL,
    all_actor_records_detached: true,
};

unsafe fn bitmap(thread: *mut abi::Thread) -> abi::CULong {
    unsafe { read_volatile(addr_of!((*thread).pmc_alloc_map)) }
}
unsafe fn monitoring(process: *mut abi::Process) -> *mut core::ffi::c_void {
    unsafe { read_volatile(addr_of!((*process).monitoring_event)) }
}
fn bit(index: abi::CInt) -> abi::CULong {
    assert!(index >= 0 && index < abi::CULong::BITS as abi::CInt);
    (1 as abi::CULong) << index
}

/// Genuine P lookup and managed admission. Any escaped descriptor/storage edge
/// is an actual DescriptorPin, not a raw list pointer or synthetic close token.
unsafe fn pin_fd(thread: *mut abi::Thread, fd: abi::CInt) -> super::DescriptorPin {
    let process = unsafe { (*thread).proc };
    let lock = unsafe { addr_of_mut!((*process).mckfd_lock) }.cast();
    let flags = unsafe { super::super::syscall_mckfd_lock_bridge(lock) };
    let mut descriptor = unsafe { (*process).mckfd.cast::<abi::Mckfd>() };
    while !descriptor.is_null() && unsafe { (*descriptor).fd != fd } {
        descriptor = unsafe { (*descriptor).next };
    }
    let pin = if descriptor.is_null() { Ok(None) } else {
        unsafe { super::descriptors::pin_managed_locked(process, descriptor) }
    };
    unsafe { super::super::syscall_mckfd_unlock_bridge(lock, flags) };
    pin.expect("actual managed admission").expect("real open published descriptor")
}

unsafe fn capture(thread: *mut abi::Thread, event: &EventPin) -> (usize, HardwareLeases) {
    let mut r = unsafe { Locked::take() };
    let mut snapshot = unsafe { event.selected_group().read_locked(&mut r) };
    let count = snapshot.event_count();
    let captured = unsafe { HardwareLeases::capture_locked(thread, &mut snapshot, &mut r) };
    unsafe { snapshot.finish_locked(&mut r) };
    drop(r);
    (count, captured.expect("actual executing Thread maps must be prebound"))
}

unsafe fn group_count(event: &EventPin) -> usize {
    let mut r = unsafe { Locked::take() };
    let snapshot = unsafe { event.selected_group().read_locked(&mut r) };
    let count = snapshot.event_count();
    unsafe { snapshot.finish_locked(&mut r) };
    count
}

unsafe fn close_fd(thread: *mut abi::Thread, fd: abi::CInt) -> abi::CLong {
    unsafe { crate::host_effects::set_current(thread) };
    let mut context: abi::X86UserContext = unsafe { core::mem::zeroed() };
    context.is_gpr_valid = 1;
    unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_set_arg0(&mut context, fd as abi::CULong) };
    let gate = unsafe { super::begin_close_gate((*thread).proc) }.expect("actual Process close gate");
    assert!(gate.is_some());
    let result = unsafe { super::callbacks::close_if_managed(
        thread.cast(), fd, 3, (&mut context as *mut abi::X86UserContext).cast(),
        crate::host_effects::forward_close, Some(super::super::syscall_mckfd_free_bridge),
    ) }.expect("real close route").expect("real managed close kind");
    drop(gate);
    result
}

unsafe fn open_for(mut configuration: super::Open, thread: *mut abi::Thread,
    pid: abi::CInt, group_fd: abi::CInt) -> abi::CLong {
    configuration.thread = thread.cast();
    configuration.proc = unsafe { (*thread).proc }.cast();
    configuration.pid = pid;
    configuration.group_fd = group_fd;
    unsafe { crate::host_effects::set_current(thread) };
    let result = unsafe { super::open_from_body(configuration) };
    if result >= 0 {
        unsafe { super::host_register_event_state((*thread).proc, result as abi::CInt) };
    }
    result
}

// A one-shot test scheduling input, NOT an ownership registry or model. The
// actual source below performs the clear and append. The common lower unlock
// wrapper calls it only AFTER a registered Event S is fully unlocked, restored
// IRQs are enabled and all P/R/S/hash exclusions have gone. It is never invoked
// from a PMU callback, under S, or asynchronously after this stack state ends.
struct HookState {
    tool: *mut abi::Thread, actor: *mut abi::Thread, child: *mut abi::Thread,
    configuration: super::Open, leader_fd: abi::CInt,
    old_actor_bits: abi::CULong, old_child_indices: [abi::CInt; 2],
    actor_cleared: bool, actor_bits_retained: bool, late_fd: abi::CLong,
    group_entries: usize, child_late_bound: bool, actor_late_error: abi::CInt,
    constructor_trace_start: usize, constructor_trace_end: usize,
    late_pin: Option<super::DescriptorPin>, late_event: Option<EventPin>,
}
static HOOK_STATE: AtomicPtr<HookState> = AtomicPtr::new(null_mut());

unsafe fn clear_then_append_after_state_unlock() {
    let pointer = HOOK_STATE.load(Ordering::SeqCst);
    assert!(!pointer.is_null(), "one-shot hook outlived its actual caller");
    let state = unsafe { &mut *pointer };
    let actor_process = unsafe { (*state.actor).proc };
    unsafe { super::lifecycle::clear_current_monitor(actor_process) };
    state.actor_cleared = unsafe { monitoring(actor_process).is_null() };
    let retained_after_clear = unsafe { bitmap(state.actor) == state.old_actor_bits };

    // Read-only positions in the SAME complete effect trace. The original real
    // late constructor and scheduler use the SAME atomic_set endpoint; retain
    // both sets of effects and attribute only this exact real open call window.
    state.constructor_trace_start = crate::host_perf_bindings::perf_trace().len();
    state.late_fd = unsafe { open_for(state.configuration, state.tool,
        (*actor_process).pid, state.leader_fd) };
    state.constructor_trace_end = crate::host_perf_bindings::perf_trace().len();
    assert_eq!(state.late_fd, OPEN_FDS[3]);
    let pin = unsafe { pin_fd(state.tool, state.late_fd as abi::CInt) };
    let event = pin.event().expect("actual late group member");
    state.group_entries = unsafe { group_count(&event) };
    let key = event.key();

    // The Child still monitors this genuine group; actual append prebinds it.
    let child_capture = {
        let mut r = unsafe { Locked::take() };
        unsafe { HardwareLeases::capture_one_locked(state.child, key, &mut r) }
    }.expect("actual late append prebound the still-monitored Child");
    let index = child_capture.index(key);
    state.child_late_bound = !state.old_child_indices.contains(&index)
        && unsafe { bitmap(state.child) & bit(index) != 0 };
    drop(child_capture);

    // The Actor was genuinely cleared before append. No late map exists for
    // it; the running switch can only succeed using its retained OLD epoch.
    state.actor_late_error = {
        let mut r = unsafe { Locked::take() };
        match unsafe { HardwareLeases::capture_one_locked(state.actor, key, &mut r) } {
            Err(error) => error,
            Ok(mut unexpected) => { unsafe { unexpected.release_locked(&mut r) }; 0 }
        }
    };
    state.actor_bits_retained = retained_after_clear
        && unsafe { bitmap(state.actor) == state.old_actor_bits };
    state.late_event = Some(event);
    state.late_pin = Some(pin);
    unsafe { crate::host_effects::set_current(state.actor) };
}

/// The common fixture owns genuine, initialized positive backing objects;
/// Tool/Actor are already prepared by the real lifecycle, Child is private and
/// fresh. All start with bitmap0/no perf FD. The actual provider count is4.
/// Configuration supplies real typed callbacks, initialized attr/request and
/// validated offsets; type=RAW, config=1, inherit bit1, no invariant/extra event.
/// Host allocations remain quarantined after terminal hooks for scalar reads.
/// No raw Thread is used by production after its real retirement hook below.
pub(super) unsafe fn exercise_counter_epoch_family(
    tool: *mut abi::Thread, actor: *mut abi::Thread, child: *mut abi::Thread,
    configuration: super::Open,
) -> CounterEpochObservation {
    use crate::host_perf_bindings::{self as effects, PerfEffect};
    assert!(!tool.is_null() && !actor.is_null() && !child.is_null());
    assert!(tool != actor && tool != child && actor != child);
    let (tool_process, actor_process, child_process) = unsafe { ((*tool).proc, (*actor).proc, (*child).proc) };
    assert!(!tool_process.is_null() && !actor_process.is_null() && !child_process.is_null());
    assert!(tool_process != actor_process && tool_process != child_process && actor_process != child_process);
    assert!(unsafe { (*actor_process).pid > 0 });
    assert_eq!(unsafe { (bitmap(tool), bitmap(actor), bitmap(child)) }, (0, 0, 0));
    assert!(unsafe { (*tool_process).mckfd.is_null() && (*actor_process).mckfd.is_null() && (*child_process).mckfd.is_null() });
    assert!(!configuration.attr.is_null());
    let attribute = configuration.attr.cast::<crate::f03_perf_attr_callbacks::PerfEventAttr>();
    // Exact existing common inputs, not derived output-as-oracle: the genuine
    // allocation body must initialize count=0 then period_left=sample_period=0.
    assert_eq!(unsafe { (*attribute).frequency() }, 0);
    assert_eq!(unsafe { (*attribute).sampling.sample_period }, 0);
    unsafe { (*attribute).flags |= 2 };
    crate::host_effects::set_host_replies(&OPEN_FDS);
    crate::host_effects::set_forward_replies(&[0, 0, 0, 0]);

    let leader_fd = unsafe { open_for(configuration, tool, (*actor_process).pid, -1) };
    let member_fd = unsafe { open_for(configuration, tool, (*actor_process).pid, leader_fd as abi::CInt) };
    assert_eq!([leader_fd, member_fd], [OPEN_FDS[0], OPEN_FDS[1]]);
    let leader_pin = unsafe { pin_fd(tool, leader_fd as abi::CInt) };
    let member_pin = unsafe { pin_fd(tool, member_fd as abi::CInt) };
    let leader = leader_pin.event().expect("actual group leader");
    let member = member_pin.event().expect("actual direct member");
    assert!(leader.inherit_enabled() && member.inherit_enabled());
    assert!(leader.key() != member.key());
    for event in [&leader, &member] {
        let raw = event.raw_event().cast::<Event>();
        assert_eq!(unsafe { (*raw).use_invariant_tsc }, 0);
        assert_eq!(unsafe { (*raw).extra_reg.reg }, 0);
    }

    let mut enable_context: abi::X86UserContext = unsafe { core::mem::zeroed() };
    enable_context.is_gpr_valid = 1;
    unsafe {
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg0(&mut enable_context, leader_fd as abi::CULong);
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg1(&mut enable_context, 0x2400);
        crate::host_effects::set_current(tool);
    }
    assert_eq!(unsafe { super::callbacks::ioctl(leader_pin.descriptor(), &mut enable_context) }, 0);
    let (initial_group_entries, actor_leases) = unsafe { capture(actor, &leader) };
    let actor_indices = [actor_leases.index(leader.key()), actor_leases.index(member.key())];
    let actor_mask = bit(actor_indices[0]) | bit(actor_indices[1]);
    let actor_owned_bits = unsafe { bitmap(actor).count_ones() };
    assert_eq!(unsafe { bitmap(actor) }, actor_mask);
    drop(actor_leases);

    // This foreign bit is declared lower-owner initialization, performed BEFORE
    // the actual Child CounterSlot exists. Nothing in this driver fabricates a
    // CounterSlot/generation/Reservation/CounterLease or copies a parent's map.
    unsafe { write_volatile(addr_of_mut!((*child).pmc_alloc_map), CHILD_FOREIGN_BIT) };
    unsafe { super::prepare_thread(child, NOWAIT) }.expect("real Child map-storage preparation");
    unsafe { super::lifecycle::prepare_cloned_thread(actor, child, NOWAIT) }.expect("real inherited monitor/maps preparation");
    let (_, child_leases) = unsafe { capture(child, &leader) };
    let child_indices = [child_leases.index(leader.key()), child_leases.index(member.key())];
    let child_mask = bit(child_indices[0]) | bit(child_indices[1]);
    let child_owned_bits = unsafe { (bitmap(child) & !CHILD_FOREIGN_BIT).count_ones() };
    let inherited_different = child_indices[0] != actor_indices[0] && child_indices[1] != actor_indices[1];
    assert_eq!(unsafe { bitmap(child) }, CHILD_FOREIGN_BIT | child_mask);
    drop(child_leases);

    // The originally missing inheritance edge is exercised by an ACTUAL new
    // Child open. Its Origin cannot reuse either inherited active PMC or the
    // declared foreign bit. Closing it must not clear the inherited mappings.
    let child_fd = unsafe { open_for(configuration, child, 0, -1) };
    assert_eq!(child_fd, OPEN_FDS[2]);
    let child_pin = unsafe { pin_fd(child, child_fd as abi::CInt) };
    let child_event = child_pin.event().expect("actual Child standalone open");
    let (_, child_new_leases) = unsafe { capture(child, &child_event) };
    let child_new_index = child_new_leases.index(child_event.key());
    let new_avoids_inherited = !child_indices.contains(&child_new_index)
        && bit(child_new_index) & CHILD_FOREIGN_BIT == 0;
    let new_adds_one = unsafe { bitmap(child) == (CHILD_FOREIGN_BIT | child_mask | bit(child_new_index)) };
    drop(child_new_leases);
    let child_close = unsafe { close_fd(child, child_fd as abi::CInt) };
    drop(child_pin); drop(child_event);
    unsafe { super::drain_safe_point() };
    let child_close_preserved = unsafe { bitmap(child) == (CHILD_FOREIGN_BIT | child_mask) };

    let mut hook = HookState {
        tool, actor, child, configuration, leader_fd: leader_fd as abi::CInt,
        old_actor_bits: actor_mask, old_child_indices: child_indices,
        actor_cleared: false, actor_bits_retained: false, late_fd: -1,
        group_entries: 0, child_late_bound: false, actor_late_error: 0,
        constructor_trace_start: 0, constructor_trace_end: 0,
        late_pin: None, late_event: None,
    };
    assert!(HOOK_STATE.swap(&mut hook, Ordering::SeqCst).is_null());
    effects::reset_perf_trace();
    effects::set_init_results(&[SCRIPTED_INIT_FAILURE, 0]);
    effects::set_start_results(&[0]);
    // Remote enable set the real PP_RESET input; do not manufacture a state or
    // invoke a different helper. Original order is reset, reset, start.
    let control_layout = unsafe { &super::super::f03_perf_counter_control_v1::f03_perf_event_layout_v1 };
    assert_eq!(unsafe { (*actor_process).perf_status }, HOST_PP_RESET);
    unsafe { crate::host_effects::set_current(actor) };
    effects::arm_after_state_unlock(clear_then_append_after_state_unlock);
    unsafe { super::lifecycle::switch_monitor(actor, HOST_PP_RESET, control_layout.pp_count) };
    assert_eq!(HOOK_STATE.swap(null_mut(), Ordering::SeqCst), &mut hook as *mut HookState);
    assert!(!effects::hook_pending());
    // Bound this trace to the completed original switch call. All later real
    // close/retirement effects remain legitimate; they are not scheduler events.
    let trace = effects::perf_trace();
    let constructor_window_valid = hook.constructor_trace_start < hook.constructor_trace_end
        && hook.constructor_trace_end <= trace.len()
        && trace[..hook.constructor_trace_start].iter().any(|effect| matches!(effect, PerfEffect::HookFired));
    assert!(constructor_window_valid, "actual late open boundaries must be inside the switch trace");
    let late_pin = hook.late_pin.take().expect("hook performed actual late open");
    let late_event = hook.late_event.take().expect("actual late event pin");
    let leader_count = unsafe { addr_of!((*leader.raw_event().cast::<Event>()).count) } as usize;
    let member_count = unsafe { addr_of!((*member.raw_event().cast::<Event>()).count) } as usize;
    let late_count = unsafe { addr_of!((*late_event.raw_event().cast::<Event>()).count) } as usize;
    let late_period_left = unsafe { addr_of!((*late_event.raw_event().cast::<Event>()).hw.period_left) } as usize;
    let late_creation_index = unsafe { (*late_event.raw_event().cast::<Event>()).counter_id };
    assert!(!actor_indices.contains(&late_creation_index));
    let mut zero_targets = Vec::new();
    let mut all_reset_values_zero = true;
    let mut inits = Vec::new();
    let mut starts = Vec::new();
    let mut critical = Vec::new();
    let mut hook_calls = 0usize;
    let mut late_was_reset_or_initialized = false;
    let mut constructor_writes = Vec::new();
    for (position, effect) in trace.iter().enumerate() {
        let in_constructor = hook.constructor_trace_start <= position
            && position < hook.constructor_trace_end;
        match effect {
            PerfEffect::AtomicSet { address, value } if *address == leader_count || *address == member_count => {
                all_reset_values_zero &= *value == 0;
                zero_targets.push(*address);
                critical.push(if *address == leader_count { 0u8 } else { 2u8 });
            }
            PerfEffect::AtomicSet { address, value } if *address == late_count || *address == late_period_left => {
                if in_constructor {
                    let field = if *address == late_count { 0u8 } else { 1u8 };
                    constructor_writes.push((field, *value));
                    // Retain genuine constructor stores in the critical order;
                    // they are neither suppressed nor mislabeled as reset.
                    critical.push(if field == 0 { 6 } else { 7 });
                } else {
                    // Outside the actual constructor call, this late event is
                    // absent from the Actor's captured scheduler epoch/maps.
                    late_was_reset_or_initialized = true;
                    critical.push(8);
                }
            },
            PerfEffect::HookFired => { hook_calls += 1; critical.push(1); }
            PerfEffect::InitRaw { counter, result, .. } => {
                inits.push((*counter, *result));
                if *counter == late_creation_index { late_was_reset_or_initialized = true; }
                critical.push(if *counter == actor_indices[0] { 3 } else if *counter == actor_indices[1] { 4 } else { 9 });
            }
            PerfEffect::CounterStart { mask, result } => { starts.push((*mask, *result)); critical.push(5); }
            _ => {},
        }
    }
    let constructor_values = if constructor_writes.len() == 2 {
        [constructor_writes[0].1, constructor_writes[1].1]
    } else { [abi::CLong::MIN, abi::CLong::MIN] };
    let init_statuses = if inits.len() == 2 { [inits[0].1, inits[1].1] } else { [0, 0] };
    let original_continues = inits == vec![(actor_indices[0], SCRIPTED_INIT_FAILURE), (actor_indices[1], 0)]
        && starts == vec![(actor_mask, 0)];
    let actor_not_resurrected = unsafe { monitoring(actor_process).is_null() };
    let actor_bits_released = unsafe { bitmap(actor) == 0 };
    let original_count_state = unsafe { (*actor_process).perf_status == control_layout.pp_count };

    // Keep actual Operation tokens across genuine owner/Thread retirement. The
    // three events themselves remain pinned until those tokens are released.
    let (child_group_after, child_operations) = unsafe { capture(child, &leader) };
    let old_child_stable = child_operations.index(leader.key()) == child_indices[0]
        && child_operations.index(member.key()) == child_indices[1];
    let child_late_index = child_operations.index(late_event.key());
    let child_complete_mask = child_mask | bit(child_late_index);
    let late_close = unsafe { close_fd(tool, hook.late_fd as abi::CInt) };
    let member_close = unsafe { close_fd(tool, member_fd as abi::CInt) };
    let leader_close = unsafe { close_fd(tool, leader_fd as abi::CInt) };
    drop(late_pin); drop(member_pin); drop(leader_pin);
    unsafe { super::drain_safe_point() };
    let tool_origins_retired = unsafe { bitmap(tool) == 0 };
    let child_ops_hold = child_complete_mask.count_ones() == 3
        && unsafe { bitmap(child) == (CHILD_FOREIGN_BIT | child_complete_mask) };
    unsafe { super::retire_thread_before_destroy(child) };
    let terminal_only_foreign = unsafe { bitmap(child) == CHILD_FOREIGN_BIT };
    // Only HOST quarantined backing is altered after real retirement. A late
    // raw-pointer bitmap write from Operation Drop would corrupt this sentinel.
    unsafe { write_volatile(addr_of_mut!((*child).pmc_alloc_map), CHILD_RETIRED_SENTINEL) };
    drop(child_operations);
    let delayed_release_bitmap = unsafe { bitmap(child) };
    drop(late_event); drop(member); drop(leader);
    unsafe { super::retire_process_before_free(child_process); super::drain_safe_point() };
    unsafe { crate::host_effects::set_current(actor); super::retire_thread_before_destroy(actor);
        super::retire_process_before_free(actor_process); super::drain_safe_point() };
    unsafe { crate::host_effects::set_current(tool); super::retire_thread_before_destroy(tool);
        super::retire_process_before_free(tool_process); super::drain_safe_point() };
    let all_detached = unsafe {
        super::process_targets::existing(tool_process).expect("Tool registry query").is_none()
            && super::process_targets::existing(actor_process).expect("Actor registry query").is_none()
            && super::process_targets::existing(child_process).expect("Child registry query").is_none()
    };

    CounterEpochObservation {
        open_results: [leader_fd, member_fd, child_fd, hook.late_fd],
        initial_group_entries,
        actor_monitor_owned_bits: actor_owned_bits,
        child_inherited_owned_bits: child_owned_bits,
        child_inherited_indices_differ_from_actor: inherited_different,
        child_new_open_avoids_both_inherited_counters: new_avoids_inherited,
        child_new_open_adds_exactly_one_owned_bit: new_adds_one,
        child_close_preserves_inherited_and_foreign_bits: child_close_preserved,
        hook_fired_once: hook_calls == 1,
        hook_actor_monitor_cleared: hook.actor_cleared,
        hook_old_actor_operation_bits_retained: hook.actor_bits_retained,
        hook_group_entries_after_append: hook.group_entries,
        hook_late_member_mapped_for_child: hook.child_late_bound,
        hook_late_actor_mapping_error: hook.actor_late_error,
        late_constructor_window_valid: constructor_window_valid,
        late_constructor_atomic_writes: constructor_writes.len(),
        late_constructor_atomic_values: constructor_values,
        late_constructor_count_then_period_order: constructor_writes == vec![(0, 0), (1, 0)],
        reset_zero_writes: zero_targets.len(),
        reset_targets_and_order_match_original_two_member_epoch: all_reset_values_zero
            && zero_targets == vec![leader_count, member_count, leader_count, member_count],
        init_calls: inits.len(),
        init_statuses,
        init_indices_match_actual_actor_maps: inits.iter().map(|v|v.0).collect::<Vec<_>>() == actor_indices,
        aggregate_start_calls: starts.len(),
        aggregate_start_mask_matches_actual_actor_maps: starts == vec![(actor_mask, 0)],
        critical_effect_order_preserved: critical == vec![0, 1, 6, 7, 2, 0, 2, 3, 4, 5],
        no_late_member_scheduler_reset_or_init: !late_was_reset_or_initialized,
        original_start_continues_after_nonzero_init: original_continues,
        actor_monitor_not_resurrected: actor_not_resurrected,
        actor_old_bits_released_after_sequence: actor_bits_released,
        scheduler_original_count_state_written: original_count_state,
        child_group_entries_after_append: child_group_after,
        child_old_mappings_stable_across_append: old_child_stable,
        close_results: [child_close, late_close, member_close, leader_close],
        tool_origin_bits_retired_after_storage_drop: tool_origins_retired,
        child_operations_hold_three_actual_mapping_bits: child_ops_hold,
        child_terminal_leaves_only_foreign_bit: terminal_only_foreign,
        child_delayed_operation_release_bitmap: delayed_release_bitmap,
        all_actor_records_detached: all_detached,
    }
}
