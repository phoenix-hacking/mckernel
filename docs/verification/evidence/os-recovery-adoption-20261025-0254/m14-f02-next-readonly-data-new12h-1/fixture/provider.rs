#![no_std]
use core::mem::offset_of;
#[path="/home/holden/mckernel/kernel/rust/abi.rs"] mod abi;
use abi::{Thread, Process, CpuLocalVar, SigCommon};
#[repr(C)]
pub struct SchedRunqueueOffsets {
    pub thread_cpu_id_offset: usize,
    pub thread_tid_offset: usize,
    pub thread_status_offset: usize,
    pub thread_spin_sleep_lock_offset: usize,
    pub thread_spin_sleep_offset: usize,
    pub thread_sched_list_offset: usize,
    pub thread_sigpending_offset: usize,
    pub thread_sigcommon_offset: usize,
    pub sigcommon_sigpending_offset: usize,
    pub thread_proc_offset: usize,
    pub thread_mod_clone_offset: usize,
    pub proc_pid_offset: usize,
    pub proc_status_offset: usize,
    pub proc_update_lock_offset: usize,
    pub proc_clone_count_offset: usize,
    pub cpu_runq_lock_offset: usize,
    pub cpu_runq_irqstate_offset: usize,
    pub cpu_current_offset: usize,
    pub cpu_prevpid_offset: usize,
    pub cpu_runq_offset: usize,
    pub cpu_runq_len_offset: usize,
    pub cpu_runq_reserved_offset: usize,
    pub cpu_flags_offset: usize,
    pub cpu_status_offset: usize,
    pub cpu_in_interrupt_offset: usize,
    pub cpu_nr_ctx_switches_offset: usize,
}
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Paired with MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE in process.c. Reuse the
// existing typed constructor; no scheduler body or callback/lifetime change.
#[cfg(process_global_storage_candidate)]
#[no_mangle]
pub static process_sched_runqueue_offsets: SchedRunqueueOffsets = sched_runqueue_offsets();

const _: () = {
    assert!(core::mem::size_of::<SchedRunqueueOffsets>() == 208);
    assert!(core::mem::align_of::<SchedRunqueueOffsets>() == 8);
};

const fn sched_runqueue_offsets() -> SchedRunqueueOffsets {
    SchedRunqueueOffsets {
        thread_cpu_id_offset: offset_of!(Thread, cpu_id),
        thread_tid_offset: offset_of!(Thread, tid),
        thread_status_offset: offset_of!(Thread, status),
        thread_spin_sleep_lock_offset: offset_of!(Thread, spin_sleep_lock),
        thread_spin_sleep_offset: offset_of!(Thread, spin_sleep),
        thread_sched_list_offset: offset_of!(Thread, sched_list),
        thread_sigpending_offset: offset_of!(Thread, sigpending),
        thread_sigcommon_offset: offset_of!(Thread, sigcommon),
        sigcommon_sigpending_offset: offset_of!(SigCommon, sigpending),
        thread_proc_offset: offset_of!(Thread, proc),
        thread_mod_clone_offset: offset_of!(Thread, mod_clone),
        proc_pid_offset: offset_of!(Process, pid),
        proc_status_offset: offset_of!(Process, status),
        proc_update_lock_offset: offset_of!(Process, update_lock),
        proc_clone_count_offset: offset_of!(Process, clone_count),
        cpu_runq_lock_offset: offset_of!(CpuLocalVar, runq_lock),
        cpu_runq_irqstate_offset: offset_of!(CpuLocalVar, runq_irqstate),
        cpu_current_offset: offset_of!(CpuLocalVar, current),
        cpu_prevpid_offset: offset_of!(CpuLocalVar, prevpid),
        cpu_runq_offset: offset_of!(CpuLocalVar, runq),
        cpu_runq_len_offset: offset_of!(CpuLocalVar, runq_len),
        cpu_runq_reserved_offset: offset_of!(CpuLocalVar, runq_reserved),
        cpu_flags_offset: offset_of!(CpuLocalVar, flags),
        cpu_status_offset: offset_of!(CpuLocalVar, status),
        cpu_in_interrupt_offset: offset_of!(CpuLocalVar, in_interrupt),
        cpu_nr_ctx_switches_offset: offset_of!(CpuLocalVar, nr_ctx_switches),
    }
}
