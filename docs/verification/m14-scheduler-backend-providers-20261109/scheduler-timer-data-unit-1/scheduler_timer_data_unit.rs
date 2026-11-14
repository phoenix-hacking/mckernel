#![no_std]

#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

mod sched_helpers {
#[repr(C)]
pub struct TimerRuntimeOffsets {
    pub thread_status_offset: usize,
    pub thread_sched_list_offset: usize,
    pub thread_spin_sleep_lock_offset: usize,
    pub thread_spin_sleep_offset: usize,
    pub thread_itimer_enabled_offset: usize,
    pub cpu_runq_lock_offset: usize,
    pub cpu_runq_offset: usize,
    pub cpu_runq_len_offset: usize,
    pub cpu_current_offset: usize,
    pub cpu_timer_enabled_offset: usize,
    pub cpu_backlog_list_offset: usize,
    pub timer_timeout_offset: usize,
    pub timer_waitq_offset: usize,
    pub timer_list_offset: usize,
    pub timer_thread_offset: usize,
}
}

mod process_helpers {
#[cfg(process_global_storage_candidate)]
mod process_global_storage {
    use core::mem::{align_of, size_of};
    use crate::abi::CInt;

    // Preserve the existing plain C int ABI and boot defaults. Initialization
    // owns writes before normal scheduler/application consumers observe these
    // flags; existing extern accesses retain their current synchronization.
    // Keep plain mutable storage: changing this to an AtomicI32, bool, or a
    // lazy initializer would change the original C/Rust access contract.
    const _: [(); 4] = [(); size_of::<CInt>()];
    const _: [(); 4] = [(); align_of::<CInt>()];

    #[no_mangle]
    pub static mut time_sharing: CInt = 1;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// The same immutable timer descriptor, using the existing genuine Rust ABI types.
// This changes storage ownership only; no timer, lock, interrupt or list logic.
#[cfg(process_global_storage_candidate)]
mod remaining_process_timer_layout_storage {
    use core::mem::{align_of, offset_of, size_of};

    use crate::abi::{CpuLocalVar, Thread, Timer};
    use crate::sched_helpers::TimerRuntimeOffsets;

    const _: () = {
        assert!(size_of::<TimerRuntimeOffsets>() == 120);
        assert!(align_of::<TimerRuntimeOffsets>() == 8);
    };

    #[no_mangle]
    pub static process_timer_runtime_offsets: TimerRuntimeOffsets = TimerRuntimeOffsets {
        thread_status_offset: offset_of!(Thread, status),
        thread_sched_list_offset: offset_of!(Thread, sched_list),
        thread_spin_sleep_lock_offset: offset_of!(Thread, spin_sleep_lock),
        thread_spin_sleep_offset: offset_of!(Thread, spin_sleep),
        thread_itimer_enabled_offset: offset_of!(Thread, itimer_enabled),
        cpu_runq_lock_offset: offset_of!(CpuLocalVar, runq_lock),
        cpu_runq_offset: offset_of!(CpuLocalVar, runq),
        cpu_runq_len_offset: offset_of!(CpuLocalVar, runq_len),
        cpu_current_offset: offset_of!(CpuLocalVar, current),
        cpu_timer_enabled_offset: offset_of!(CpuLocalVar, timer_enabled),
        cpu_backlog_list_offset: offset_of!(CpuLocalVar, backlog_list),
        timer_timeout_offset: offset_of!(Timer, timeout),
        timer_waitq_offset: offset_of!(Timer, processes),
        timer_list_offset: offset_of!(Timer, list),
        timer_thread_offset: offset_of!(Timer, thread),
    };
}
}
