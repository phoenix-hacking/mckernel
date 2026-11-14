// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// HOST actual-source caller INSIDE syscall_policy::f03_perf_owner. This author
// has not compiled/run it. All ownership/rollback/publication/drain is genuine
// transactions::open_from_body; only the supplied allocator/host lower effects
// are scripted. The final UNKNOWN debt is deliberately retained, never retried.

use core::ffi::{c_void, CStr};
use core::mem::{offset_of, size_of};
use core::ptr::{addr_of, read_volatile};
use crate::abi;
use crate::host_effects::{self, Effect};
use super::super::f03_sync_child_layout_v2::FullMcPerfEvent;

const ENOMEM: abi::CLong = -12;
const EINVAL: abi::CLong = -22;
const HOST_ERROR: abi::CLong = -0x1_0000_0005;
const CLOSE_ERROR: abi::CLong = -0x2_0000_0009;
const LEADER_FD: abi::CLong = 101;
const ROLLBACK_FD: abi::CLong = 202;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct AttemptObservation {
    pub(super) result: abi::CLong,
    pub(super) host_calls: usize,
    pub(super) close_requests: usize,
    pub(super) exact_72byte_close_carrier: bool,
    pub(super) all_host_calls_on_tool_route: bool,
    pub(super) abort_event_frees: usize,
    pub(super) published_event_frees: usize,
    pub(super) descriptor_backing_frees: usize,
    pub(super) map_restored: bool,
    pub(super) descriptor_list_restored: bool,
    pub(super) tracked_allocations_restored: bool,
    pub(super) unresolved_host_debt_delta: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct RollbackObservation {
    pub(super) allocation_failure: AttemptObservation,
    pub(super) invalid_group: AttemptObservation,
    pub(super) standalone_host_error: AttemptObservation,
    pub(super) member_host_error: AttemptObservation,
    pub(super) published_leader_close_result: abi::CLong,
    pub(super) published_leader_event_free_once: bool,
    pub(super) published_leader_descriptor_free_once: bool,
    pub(super) published_leader_restores_actor_baseline: bool,
    pub(super) posthost_mckfd_failure: AttemptObservation,
    pub(super) posthost_close_unknown: AttemptObservation,
    pub(super) cleanup_fullwidth_error_observed: bool,
    pub(super) unknown_live_debt_record_delta: usize,
    pub(super) unknown_second_drain_has_no_retry: bool,
    pub(super) final_local_map_empty: bool,
    pub(super) final_descriptor_list_empty: bool,
}

const fn expected_attempt(result: abi::CLong, hosts: usize, closes: usize, aborts: usize,
    restored: bool, debt: usize) -> AttemptObservation {
    AttemptObservation { result, host_calls: hosts, close_requests: closes,
        exact_72byte_close_carrier: true, all_host_calls_on_tool_route: true,
        abort_event_frees: aborts, published_event_frees: 0, descriptor_backing_frees: 0,
        map_restored: true, descriptor_list_restored: true,
        tracked_allocations_restored: restored, unresolved_host_debt_delta: debt }
}
/// Literal scalar functional oracle. No ownership decision or cleanup algorithm
/// is reimplemented here; resource observations come from actual ABI state and
/// supplied lower allocation/host-call records after real production drains.
pub(super) const EXPECTED_ROLLBACK_OBSERVATION: RollbackObservation = RollbackObservation {
    allocation_failure: expected_attempt(ENOMEM, 0, 0, 0, true, 0),
    invalid_group: expected_attempt(EINVAL, 0, 0, 1, true, 0),
    standalone_host_error: expected_attempt(HOST_ERROR, 1, 0, 1, true, 0),
    member_host_error: expected_attempt(HOST_ERROR, 1, 0, 1, true, 0),
    published_leader_close_result: 0,
    published_leader_event_free_once: true,
    published_leader_descriptor_free_once: true,
    published_leader_restores_actor_baseline: true,
    posthost_mckfd_failure: expected_attempt(ENOMEM, 2, 1, 1, true, 0),
    posthost_close_unknown: expected_attempt(ENOMEM, 2, 1, 1, false, 1),
    cleanup_fullwidth_error_observed: true,
    unknown_live_debt_record_delta: 1,
    unknown_second_drain_has_no_retry: true,
    final_local_map_empty: true,
    final_descriptor_list_empty: true,
};

unsafe fn bitmap(tool: *mut abi::Thread) -> abi::CULong {
    unsafe { read_volatile(addr_of!((*tool).pmc_alloc_map)) }
}
unsafe fn head(tool: *mut abi::Thread) -> *mut c_void {
    unsafe { read_volatile(addr_of!((*(*tool).proc).mckfd)) }
}

/// Only an allowed lower allocator failure at the ACTUAL Mckfd allocation.
/// The production transaction still owns every resource and makes every choice.
unsafe extern "C" fn fail_mckfd(size: abi::SizeT, flags: abi::CULong) -> *mut c_void {
    host_effects::fail_next_allocation();
    unsafe { super::super::syscall_alloc_bridge(size, flags) }
}

/// Compare actual recorded allocation identity/size and genuine selected origin
/// data. Private metadata frees cannot masquerade as original event/descriptor
/// frees, even if an unrelated allocation happened to have the same size.
fn free_origins() -> (usize, usize, usize) {
    let (alloc_file, alloc_line, abort_line, close_file, close_line) = unsafe {
        (CStr::from_ptr(addr_of!(super::super::f03_mckfd_alloc_origin_file_v1).cast()).to_bytes(),
         super::super::F03_PERF_ALLOC_ORIGIN_LINE_V1,
         super::super::F03_PERF_FREE_ORIGIN_LINE_V1,
         CStr::from_ptr(addr_of!(super::super::f03_mckfd_free_origin_file_v1).cast()).to_bytes(),
         super::super::f03_mckfd_free_origin_line_v1)
    };
    let mut aborts = 0; let mut published = 0; let mut descriptors = 0;
    for effect in host_effects::snapshot().iter() {
        if let Effect::Free { record, file, line } = effect {
            if record.size == size_of::<FullMcPerfEvent>()
                && record.file.as_slice() == alloc_file && record.line == alloc_line {
                if file.as_slice() == alloc_file && *line == abort_line { aborts += 1; }
                if file.as_slice() == close_file && *line == close_line { published += 1; }
            }
            if record.size == size_of::<abi::Mckfd>() && file.as_slice() == close_file && *line == close_line {
                descriptors += 1;
            }
        }
    }
    (aborts, published, descriptors)
}

fn number(request: &[u8; 72]) -> abi::CULong {
    let offset = offset_of!(abi::SyscallRequest, number);
    abi::CULong::from_ne_bytes(request[offset..offset + size_of::<abi::CULong>()].try_into().unwrap())
}

fn close_carrier(fd: abi::CULong) -> [u8; 72] {
    // External ABI oracle: explicit bytes include every padding/route byte.
    // No Rust reference to uninitialized/padding-bearing request storage.
    let mut expected = [0u8; 72];
    let nr = offset_of!(abi::SyscallRequest, number);
    let arg0 = offset_of!(abi::SyscallRequest, args);
    expected[nr..nr + 8].copy_from_slice(&3u64.to_ne_bytes());
    expected[arg0..arg0 + 8].copy_from_slice(&fd.to_ne_bytes());
    expected
}

unsafe fn summarize(
    tool: *mut abi::Thread, result: abi::CLong, old_map: abi::CULong,
    old_head: *mut c_void, old_allocations: &[host_effects::AllocationRecord], old_debt: usize,
) -> AttemptObservation {
    let mut hosts = 0; let mut closes = 0; let mut exact = true; let mut same_route = true;
    for effect in host_effects::snapshot().iter() {
        if let Effect::HostReply { request, thread, process, .. } = effect {
            hosts += 1;
            same_route &= *thread == tool as usize && *process == unsafe { (*tool).proc } as usize;
            if number(request) == 3 {
                closes += 1;
                exact &= *request == close_carrier(ROLLBACK_FD as abi::CULong);
            }
        }
    }
    let (aborts, published, descriptors) = free_origins();
    AttemptObservation {
        result, host_calls: hosts, close_requests: closes,
        exact_72byte_close_carrier: exact, all_host_calls_on_tool_route: same_route,
        abort_event_frees: aborts, published_event_frees: published, descriptor_backing_frees: descriptors,
        map_restored: unsafe { bitmap(tool) == old_map },
        descriptor_list_restored: unsafe { head(tool) == old_head },
        tracked_allocations_restored: host_effects::live_allocations().as_slice() == old_allocations,
        unresolved_host_debt_delta: unsafe { super::descriptors::unresolved_host_closes() }.checked_sub(old_debt)
            .expect("actual unresolved debt cannot disappear"),
    }
}

/// The common fixture supplies one initialized, genuinely lifecycle/map-prepared
/// Tool actor with no descriptors and an actual validated Open, live request and
/// attr storage, real callbacks, and real origin static data. No source body is
/// replaced. Its actor backing remains quarantined with final UNKNOWN debt.
pub(super) unsafe fn exercise_rollback_family(
    tool: *mut abi::Thread, configuration: super::Open,
) -> RollbackObservation {
    assert!(!tool.is_null() && !unsafe { (*tool).proc }.is_null());
    assert!(configuration.thread == tool.cast() && configuration.proc == unsafe { (*tool).proc }.cast());
    assert!(unsafe { head(tool).is_null() && bitmap(tool) == 0 });
    assert_eq!(configuration.group_fd, -1);
    assert!(!configuration.request.is_null() && !configuration.attr.is_null());
    unsafe { crate::host_effects::set_current(tool); super::drain_safe_point(); }
    let actor_allocations = host_effects::live_allocations();
    let actor_head = unsafe { head(tool) }; let actor_map = unsafe { bitmap(tool) };
    let initial_debt = unsafe { super::descriptors::unresolved_host_closes() };

    host_effects::reset_trace();host_effects::set_host_replies(&[]);host_effects::fail_next_allocation();
    let result = unsafe { super::transactions::open_from_body(configuration) };
    let allocation_failure = unsafe { summarize(tool, result, actor_map, actor_head, &actor_allocations, initial_debt) };
    assert_eq!(allocation_failure, EXPECTED_ROLLBACK_OBSERVATION.allocation_failure);

    host_effects::reset_trace();host_effects::set_host_replies(&[]);
    let mut invalid = configuration;invalid.group_fd = 999_999;
    let result = unsafe { super::transactions::open_from_body(invalid) };
    let invalid_group = unsafe { summarize(tool, result, actor_map, actor_head, &actor_allocations, initial_debt) };
    assert_eq!(invalid_group, EXPECTED_ROLLBACK_OBSERVATION.invalid_group);

    host_effects::reset_trace();host_effects::set_host_replies(&[HOST_ERROR]);
    let result = unsafe { super::transactions::open_from_body(configuration) };
    let standalone_host_error = unsafe { summarize(tool, result, actor_map, actor_head, &actor_allocations, initial_debt) };
    assert_eq!(standalone_host_error, EXPECTED_ROLLBACK_OBSERVATION.standalone_host_error);

    // A real published leader, not a hand-made list node/group owner.
    host_effects::reset_trace();host_effects::set_host_replies(&[LEADER_FD]);
    assert_eq!(unsafe { super::transactions::open_from_body(configuration) }, LEADER_FD);
    let leader_head = unsafe { head(tool) }; let leader_map = unsafe { bitmap(tool) };
    assert!(!leader_head.is_null() && leader_map.count_ones() == 1);
    let leader_allocations = host_effects::live_allocations();
    host_effects::reset_trace();host_effects::set_host_replies(&[HOST_ERROR]);
    let mut member = configuration;member.group_fd = LEADER_FD as abi::CInt;
    let result = unsafe { super::transactions::open_from_body(member) };
    let member_host_error = unsafe { summarize(tool, result, leader_map, leader_head, &leader_allocations, initial_debt) };
    assert_eq!(member_host_error, EXPECTED_ROLLBACK_OBSERVATION.member_host_error);

    host_effects::reset_trace();host_effects::set_forward_replies(&[0]);
    // Actual initialized user context and genuine setter; no made-up close
    // carrier or ownership callback replaces the real ordinary close path.
    let mut close_context: abi::X86UserContext = unsafe { core::mem::zeroed() };
    unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_set_arg0(&mut close_context, LEADER_FD as abi::CULong) };
    let gate = unsafe { super::begin_close_gate((*tool).proc) }.expect("actual leader close gate");
    assert!(gate.is_some());
    let leader_close = unsafe { super::callbacks::close_if_managed(
        tool.cast(), LEADER_FD as abi::CInt, 3, (&mut close_context as *mut abi::X86UserContext).cast(),
        host_effects::forward_close, Some(super::super::syscall_mckfd_free_bridge),
    ) }.expect("actual published leader close").expect("actual managed leader");
    drop(gate);unsafe { super::drain_safe_point(); }
    let (_, published_leader_events, published_leader_descriptors) = free_origins();
    let leader_restored = host_effects::live_allocations() == actor_allocations
        && unsafe { head(tool) == actor_head && bitmap(tool) == actor_map };
    assert_eq!(leader_close, 0);assert_eq!(published_leader_events, 1);
    assert_eq!(published_leader_descriptors, 1);assert!(leader_restored);

    let mut posthost = configuration;posthost.mckfd_alloc_fn = Some(fail_mckfd);
    host_effects::reset_trace();host_effects::set_host_replies(&[ROLLBACK_FD, 0]);
    let result = unsafe { super::transactions::open_from_body(posthost) };
    let posthost_mckfd_failure = unsafe { summarize(tool, result, actor_map, actor_head, &actor_allocations, initial_debt) };
    assert_eq!(posthost_mckfd_failure, EXPECTED_ROLLBACK_OBSERVATION.posthost_mckfd_failure);

    // One real failed host-close disposition is LAST. All local backing is
    // actually freed, but the source retains its explicit unresolved host Record.
    // Neither a second drain nor this fixture retries/claims that host fd closed.
    host_effects::reset_trace();host_effects::set_host_replies(&[ROLLBACK_FD, CLOSE_ERROR]);
    let result = unsafe { super::transactions::open_from_body(posthost) };
    let posthost_close_unknown = unsafe { summarize(tool, result, actor_map, actor_head, &actor_allocations, initial_debt) };
    assert_eq!(posthost_close_unknown, EXPECTED_ROLLBACK_OBSERVATION.posthost_close_unknown);
    let close_error_observed = host_effects::snapshot().iter().any(|effect| matches!(effect,
        Effect::HostReply { request, result, .. } if number(request) == 3 && *result == CLOSE_ERROR));
    let debt_allocations = host_effects::live_allocations().len().checked_sub(actor_allocations.len())
        .expect("UNKNOWN debt record must remain actually allocated");
    let host_count_before = host_effects::snapshot().iter().filter(|effect| matches!(effect, Effect::HostReply { .. })).count();
    unsafe { super::drain_safe_point(); }
    let host_count_after = host_effects::snapshot().iter().filter(|effect| matches!(effect, Effect::HostReply { .. })).count();

    RollbackObservation {
        allocation_failure, invalid_group, standalone_host_error, member_host_error,
        published_leader_close_result: leader_close,
        published_leader_event_free_once: published_leader_events == 1,
        published_leader_descriptor_free_once: published_leader_descriptors == 1,
        published_leader_restores_actor_baseline: leader_restored,
        posthost_mckfd_failure, posthost_close_unknown,
        cleanup_fullwidth_error_observed: close_error_observed,
        unknown_live_debt_record_delta: debt_allocations,
        unknown_second_drain_has_no_retry: host_count_before == 2 && host_count_after == host_count_before,
        final_local_map_empty: unsafe { bitmap(tool) == 0 },
        final_descriptor_list_empty: unsafe { head(tool).is_null() },
    }
}
