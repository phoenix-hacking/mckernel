// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// PRIVATE UNSELECTED coherent source candidate; compiler/type closure pending.
// No selector/default/source-eligibility activation.
// This module is a child of syscall_policy and uses its genuine selected ABI
// providers. lib.rs reexports only the same typed callsite facade.
#[path="f03_perf_owner/descriptors.rs"] mod descriptors;
#[path="f03_perf_owner/events.rs"] mod events;
#[path="f03_perf_owner/groups.rs"] mod groups;
#[path="f03_perf_owner/monitors.rs"] mod monitors;
#[path="f03_perf_owner/thread_counters.rs"] mod thread_counters;
#[path="f03_perf_owner/maps.rs"] mod maps;
#[path="f03_perf_owner/runtime.rs"] mod runtime;
#[path="f03_perf_owner/process_targets.rs"] mod process_targets;
#[path="f03_perf_owner/target_process.rs"] mod target_process;
#[path="f03_perf_owner/forward_gate.rs"] mod forward_gate;
#[path="f03_perf_owner/transactions.rs"] mod transactions;
#[path="f03_perf_owner/callbacks.rs"] mod callbacks;
#[path="f03_perf_owner/hardware.rs"] mod hardware;
#[path="f03_perf_owner/fork_copy.rs"] mod fork_copy;
#[path="f03_perf_owner/copy_borrows.rs"] mod copy_borrows;
#[path="f03_perf_owner/lifecycle.rs"] mod lifecycle;
#[path="f03_perf_owner/entry.rs"] mod entry;

pub(crate) use descriptors::{DescriptorPin,pin_managed_locked};
pub(crate) use maps::{prepare_thread,retire_thread_before_destroy};
pub(crate) use transactions::{Open,open_from_body};
pub(crate) use lifecycle::{prepare_created_thread,prepare_cloned_thread,inherit_monitor_after_host_clone};
pub(crate) use fork_copy::{copy_descriptors,finish_child_host_route};
pub(crate) use lifecycle::{sync_monitor,switch_monitor};
pub(crate) use callbacks::{read as descriptor_read,ioctl as descriptor_ioctl,close_if_managed};
#[path="f03_perf_owner/terminal.rs"] mod terminal;
pub(crate) use terminal::terminal_current_process;
use core::ffi::c_void;
use crate::abi::{CInt,Mckfd,Process};

pub(crate) unsafe fn vm_mark_close_locked(descriptor:*mut Mckfd)->Result<bool,CInt> {
    if unsafe{descriptors::mark_vm_close_under_p(descriptor)}{return Ok(true);}
    let _=unsafe{copy_borrows::retire_before_free(descriptor)}?;Ok(false)
}
pub(crate) unsafe fn retire_process_descriptor(descriptor:*mut Mckfd,free:unsafe extern "C" fn(*mut c_void))->Result<bool,CInt>{
    if unsafe{descriptors::retire_any_unlinked(descriptor,free)}?{return Ok(true);}
    let _=unsafe{copy_borrows::retire_before_free(descriptor)}?;Ok(false)
}
pub(crate) unsafe fn retire_process_before_free(process:*mut Process){unsafe{fork_copy::abort_pending(process);process_targets::retire_before_free(process);}}

/// Actual known process-context safe point ONLY: no P/R/S/hash/runqueue/IRQ
/// exclusion and no raw pointer borrowed across destruction. Does not invoke
/// do_syscall, close a numeric host fd, alter accounting or infer task exit.
pub(crate) unsafe fn drain_safe_point(){
    {let mut r=unsafe{descriptors::Locked::take()};unsafe{maps::reconcile_monitors_locked(|key,group,r|process_targets::current_group_locked(key,group,r),&mut r);}}
    unsafe{
        fork_copy::drain_deferred();
        descriptors::drain_deferred();
        events::drain_origins(maps::retire_origin);
        events::drain_deferred(maps::retire_event,maps::retire_group);
        maps::drain_deferred();
        copy_borrows::drain_deferred();
        process_targets::drain_deferred();
    }
}

/// Owns the actual per-Process table-mutation gate before ordinary close's P
/// lookup/unlink, including opaque nodes. Constructor hooks prebound every real
/// user Process before it could publish a managed fd; never wait under P/R.
pub(crate) struct ProcessCloseGate{_owner:process_targets::OpeningOwner}
pub(crate) unsafe fn begin_close_gate(process:*mut Process)->Result<Option<ProcessCloseGate>,CInt>{
    match unsafe{process_targets::existing(process)}?{None=>Ok(None),Some(handle)=>Ok(Some(ProcessCloseGate{_owner:unsafe{handle.into_opening()}?}))}
}
pub(crate) struct CopyCloseGuard{guard:Option<copy_borrows::CloseBorrow>}
pub(crate) unsafe fn mark_copy_close_under_p(process:*mut Process,node:*mut Mckfd)->Result<CopyCloseGuard,CInt>{
    Ok(CopyCloseGuard{guard:unsafe{copy_borrows::mark_close_under_p(process,node)}?})
}
impl CopyCloseGuard{pub(crate) unsafe fn wait_unlinked(self)->Result<(),CInt>{if let Some(guard)=self.guard{unsafe{guard.wait_unlinked()}}else{Ok(())}}}

// HOST-only four actual-function callers; production facade above is unchanged.
include!("../owner_test_accessors.rs");
#[path="f03_perf_owner/monitor_family.rs"] mod monitor_family;
#[path="f03_perf_owner/target_family.rs"] mod target_family;
#[path="f03_perf_owner/counter_epoch_family.rs"] mod counter_epoch_family;
#[path="f03_perf_owner/rollback_family.rs"] mod rollback_family;
#[path="f03_perf_owner/vm_drain_family.rs"] mod vm_drain_family;
#[path="../owner_case_driver.rs"] pub(crate) mod host_case_driver;
