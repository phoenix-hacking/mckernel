// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Actual-source caller, compiled INSIDE syscall_policy::f03_perf_owner by the
// independent common fixture. Author has not compiled or executed this file.
// No metadata/ownership mock: all monitor, clone, close, map and terminal work
// below calls the real selected candidate. Only set_current/forward_close are
// the common fixture's declared controlled lower effects.

use core::ptr::{addr_of, read_volatile};
use crate::abi;
use super::descriptors::Locked;
use super::monitors::MonitorRead;
use super::thread_counters::EventKey;
use super::super::f03_sync_child_layout_v2::FullMcPerfEvent;

const NOWAIT: abi::CULong = 2; // same actual constructor/callback allocation flag
const CLOSE_NUMBER: abi::CInt = 3; // actual qualified x86_64 __NR_close

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct MonitorObservation {
    pub(super) remote_enable_result: abi::CInt,
    pub(super) clone_preparation_succeeded: bool,
    pub(super) remote_had_no_perf_descriptor: bool,
    pub(super) child_has_no_perf_descriptor: bool,
    pub(super) remote_monitor_installed: bool,
    pub(super) child_monitor_inherited: bool,
    pub(super) remote_temporary_process_reference_balanced: bool,
    pub(super) child_has_no_permanent_process_reference_edge: bool,
    pub(super) close_result: abi::CLong,
    pub(super) tool_descriptor_unlinked: bool,
    pub(super) remote_monitor_cleared_by_tool_close: bool,
    pub(super) remote_map_retired_by_tool_close: bool,
    pub(super) origin_held_until_descriptor_storage_retired: bool,
    pub(super) origin_retired_after_descriptor_storage_drop: bool,
    pub(super) child_monitor_survives_tool_storage_drop: bool,
    pub(super) child_map_bits_after_tool_storage_drop: u32,
    pub(super) child_group_entries: usize,
    pub(super) child_real_operation_uses_bound_mapping: bool,
    pub(super) child_monitor_survives_operation_release: bool,
    pub(super) child_thread_terminal_clears_only_its_map: bool,
    pub(super) child_process_terminal_clears_monitor: bool,
    pub(super) child_process_record_detached: bool,
    pub(super) all_three_actor_maps_retired: bool,
    pub(super) all_three_actor_records_detached: bool,
}

/// Literal external functional oracle, not a second ownership implementation.
/// The one-event fixture causes one child mapping; no physical index/generation
/// is prescribed, and these observations assert no kernel/native acceptance.
pub(super) const EXPECTED_MONITOR_OBSERVATION: MonitorObservation = MonitorObservation {
    remote_enable_result: 0,
    clone_preparation_succeeded: true,
    remote_had_no_perf_descriptor: true,
    child_has_no_perf_descriptor: true,
    remote_monitor_installed: true,
    child_monitor_inherited: true,
    remote_temporary_process_reference_balanced: true,
    child_has_no_permanent_process_reference_edge: true,
    close_result: 0,
    tool_descriptor_unlinked: true,
    remote_monitor_cleared_by_tool_close: true,
    remote_map_retired_by_tool_close: true,
    origin_held_until_descriptor_storage_retired: true,
    origin_retired_after_descriptor_storage_drop: true,
    child_monitor_survives_tool_storage_drop: true,
    child_map_bits_after_tool_storage_drop: 1,
    child_group_entries: 1,
    child_real_operation_uses_bound_mapping: true,
    child_monitor_survives_operation_release: true,
    child_thread_terminal_clears_only_its_map: true,
    child_process_terminal_clears_monitor: true,
    child_process_record_detached: true,
    all_three_actor_maps_retired: true,
    all_three_actor_records_detached: true,
};

unsafe fn bitmap(thread: *mut abi::Thread) -> abi::CULong {
    unsafe { read_volatile(addr_of!((*thread).pmc_alloc_map)) }
}
unsafe fn monitor(process: *mut abi::Process) -> *mut core::ffi::c_void {
    unsafe { read_volatile(addr_of!((*process).monitoring_event)) }
}
unsafe fn references(process: *mut abi::Process) -> abi::CInt {
    // The common fixture is serial. This is scalar observation of the genuine
    // ABI counter after the actual positive-acquire/unlock/release completed.
    unsafe { read_volatile(addr_of!((*process).refcount.counter)) }
}
unsafe fn detached(process: *mut abi::Process) -> bool {
    // existing() compares the historical pointer against actual registry rows;
    // this does not dereference the quarantined actor as a live Process.
    unsafe { super::process_targets::existing(process) }.expect("actual Process registry query").is_none()
}

/// Capture/release actual Operation tokens from the Process-owned child monitor
/// after the Tool origin/descriptor has gone. No start/reset/read hardware,
/// fake index, direct refcount modification, or mirrored registry is involved.
unsafe fn observe_child_operation(
    child: *mut abi::Thread, expected: EventKey,
) -> (usize, bool) {
    let process = unsafe { (*child).proc };
    let mut r = unsafe { Locked::take() };
    let current = unsafe { super::process_targets::pin_under_lock(process, &mut r) };
    let pin = match current {
        Ok(MonitorRead::Managed(pin)) => pin,
        Ok(MonitorRead::None) => { drop(r); panic!("child inherited association disappeared"); }
        Ok(MonitorRead::Unmanaged(_)) => { drop(r); panic!("child monitor is not actual managed kind"); }
        Err(error) => { drop(r); panic!("child monitor pin failed: {}", error); }
    };
    let same = pin.key() == expected && pin.selected_group().key() == expected;
    let mut snapshot = unsafe { pin.selected_group().read_locked(&mut r) };
    let entries = snapshot.event_count();
    let captured = unsafe { super::maps::HardwareLeases::capture_locked(child, &mut snapshot, &mut r) };
    unsafe { snapshot.finish_locked(&mut r); pin.release_locked(&mut r); }
    drop(r);
    let leases = captured.expect("actual inherited child map must have been prebound");
    // Inspect only our owned Operation token after R drops. On an oracle
    // failure, its genuine Drop can therefore retire without recursive R.
    let bound = if same && entries == 1 {
        let index = leases.index(expected);
        index >= 0 && index < abi::CULong::BITS as abi::CInt
            && unsafe { bitmap(child) } == (1 as abi::CULong) << index
    } else { false };
    drop(leases);
    (entries, bound)
}

/// Preconditions are supplied by the independent actual-source common fixture:
/// - Tool+remote are distinct initialized ABI Threads/Processes, with genuine
///   lifecycle metadata and a real hash-visible positive remote Process.
/// - One actual standalone Tool open has event.pid=remote.pid and inherit bit2.
/// - storage_pin is the ONLY escaped Tool DescriptorPin; no hidden pin is kept.
/// - Child is initialized, private, has no metadata/FD, and is not yet visible.
/// - Contexts are fully initialized; enable arg1=0x2400; close arg0=Tool fd.
/// - Actor backing is quarantined after terminal hooks for scalar observation;
///   the common fixture, not this family, owns its eventual host allocation.
pub(super) unsafe fn exercise_monitor_family(
    tool: *mut abi::Thread,
    remote: *mut abi::Thread,
    child: *mut abi::Thread,
    storage_pin: super::DescriptorPin,
    enable_ctx: *mut abi::X86UserContext,
    close_ctx: *mut abi::X86UserContext,
) -> MonitorObservation {
    assert!(!tool.is_null() && !remote.is_null() && !child.is_null());
    assert!(!enable_ctx.is_null() && !close_ctx.is_null());
    let (tool_process, remote_process, child_process) = unsafe { ((*tool).proc, (*remote).proc, (*child).proc) };
    assert!(!tool_process.is_null() && !remote_process.is_null() && !child_process.is_null());
    assert!(tool_process != remote_process && tool_process != child_process && remote_process != child_process);
    let descriptor = storage_pin.descriptor();
    assert!(!descriptor.is_null() && storage_pin.process() == tool_process);
    let fd = unsafe { (*descriptor).fd };
    assert_eq!(unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg0(close_ctx) } as abi::CInt, fd);
    let (key, event_address) = {
        let event = storage_pin.event().expect("actual Tool event pin");
        assert!(event.inherit_enabled());
        assert_eq!(unsafe { (*event.raw_event().cast::<FullMcPerfEvent>()).pid }, unsafe { (*remote_process).pid });
        assert!(event.selected_group().key() == event.key());
        (event.key(), event.raw_event())
    }; // No extra EventPin is held across the lifetime observations below.
    let origin_before = unsafe { bitmap(tool) };
    assert_eq!(origin_before.count_ones(), 1);
    assert_eq!(unsafe { bitmap(remote) }, 0);
    assert_eq!(unsafe { bitmap(child) }, 0);
    let remote_no_fd = unsafe { (*remote_process).mckfd.is_null() };
    assert!(remote_no_fd && unsafe { (*child_process).mckfd.is_null() });
    let remote_refs_before = unsafe { references(remote_process) };
    let child_refs_before = unsafe { references(child_process) };
    assert!(remote_refs_before > 0 && child_refs_before > 0);

    unsafe { crate::host_effects::set_current(tool) };
    let enable_result = unsafe { super::callbacks::ioctl(descriptor, enable_ctx) };
    assert_eq!(enable_result, 0);
    let remote_monitor_installed = unsafe { monitor(remote_process) == event_address && bitmap(remote).count_ones() == 1 };
    let remote_reference_balanced = unsafe { references(remote_process) == remote_refs_before };

    // Match the genuine private Thread constructor: map storage preparation
    // precedes the actual clone/inherit hook; no artificial descriptor is copied.
    unsafe { super::prepare_thread(child, NOWAIT) }.expect("actual child Thread storage preparation");
    unsafe { super::lifecycle::prepare_cloned_thread(remote, child, NOWAIT) }
        .expect("actual child monitor inheritance/prebinding");
    let child_no_fd = unsafe { (*child_process).mckfd.is_null() };
    let child_monitor_inherited = unsafe { monitor(child_process) == event_address && bitmap(child).count_ones() == 1 };
    let child_no_process_cycle = unsafe { references(child_process) == child_refs_before };

    unsafe { crate::host_effects::set_current(tool) };
    let gate = unsafe { super::begin_close_gate(tool_process) }.expect("actual Tool close gate");
    assert!(gate.is_some());
    let close_result = unsafe { super::callbacks::close_if_managed(
        tool.cast(), fd, CLOSE_NUMBER, close_ctx.cast(), crate::host_effects::forward_close,
        Some(super::super::syscall_mckfd_free_bridge),
    ) }.expect("actual managed Tool close").expect("actual managed descriptor kind");
    drop(gate);
    let descriptor_unlinked = unsafe { (*tool_process).mckfd.is_null() };
    unsafe { super::drain_safe_point() };
    let held_origin = unsafe { bitmap(tool) == origin_before };
    let remote_cleared = unsafe { monitor(remote_process).is_null() };
    let remote_map_cleared = unsafe { bitmap(remote) == 0 };

    // This is the actual last DescriptorEvent STORAGE edge, not an Event count
    // or a fabricated last-reference notification. The child owns no Tool FD.
    drop(storage_pin);
    unsafe { super::drain_safe_point() };
    let origin_retired = unsafe { bitmap(tool) == 0 };
    let child_survives = unsafe { monitor(child_process) == event_address };
    let child_map_bits = unsafe { bitmap(child).count_ones() };

    unsafe { crate::host_effects::set_current(child) };
    let (child_entries, child_mapping_used) = unsafe { observe_child_operation(child, key) };
    let child_survives_operation = unsafe { monitor(child_process) == event_address && bitmap(child).count_ones() == 1 };

    // Actual pre-destruction hooks, with no hidden event/descriptor/operation
    // guard left to make a missing terminal edge look safe. Actor backing stays
    // quarantined; no real kernel object or process is destroyed by this test.
    unsafe { super::retire_thread_before_destroy(child) };
    let child_thread_cleared = unsafe { bitmap(child) == 0 && bitmap(tool) == 0 && bitmap(remote) == 0 };
    unsafe { super::retire_process_before_free(child_process); super::drain_safe_point(); }
    let child_process_cleared = unsafe { monitor(child_process).is_null() };
    let child_detached = unsafe { detached(child_process) };

    unsafe { crate::host_effects::set_current(remote); super::retire_thread_before_destroy(remote);
        super::retire_process_before_free(remote_process); super::drain_safe_point(); }
    unsafe { crate::host_effects::set_current(tool); super::retire_thread_before_destroy(tool);
        super::retire_process_before_free(tool_process); super::drain_safe_point(); }
    let all_maps = unsafe { bitmap(tool) == 0 && bitmap(remote) == 0 && bitmap(child) == 0 };
    let all_records = unsafe { detached(tool_process) && detached(remote_process) && detached(child_process) };

    MonitorObservation {
        remote_enable_result: enable_result,
        clone_preparation_succeeded: true,
        remote_had_no_perf_descriptor: remote_no_fd,
        child_has_no_perf_descriptor: child_no_fd,
        remote_monitor_installed,
        child_monitor_inherited,
        remote_temporary_process_reference_balanced: remote_reference_balanced,
        child_has_no_permanent_process_reference_edge: child_no_process_cycle,
        close_result,
        tool_descriptor_unlinked: descriptor_unlinked,
        remote_monitor_cleared_by_tool_close: remote_cleared,
        remote_map_retired_by_tool_close: remote_map_cleared,
        origin_held_until_descriptor_storage_retired: held_origin,
        origin_retired_after_descriptor_storage_drop: origin_retired,
        child_monitor_survives_tool_storage_drop: child_survives,
        child_map_bits_after_tool_storage_drop: child_map_bits,
        child_group_entries: child_entries,
        child_real_operation_uses_bound_mapping: child_mapping_used,
        child_monitor_survives_operation_release: child_survives_operation,
        child_thread_terminal_clears_only_its_map: child_thread_cleared,
        child_process_terminal_clears_monitor: child_process_cleared,
        child_process_record_detached: child_detached,
        all_three_actor_maps_retired: all_maps,
        all_three_actor_records_detached: all_records,
    }
}
