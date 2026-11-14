#![feature(linkage)]
#![feature(c_variadic)]
#![feature(core_intrinsics)]
#![no_std]

use core::panic::PanicInfo;

pub mod abi;
mod abort;
mod affinity;
mod ap;
mod atomic_helpers;
mod bitmap;
mod bitops;
mod builtin_dma;
mod cls;
mod cls_helpers;
mod debug;
mod devobj;
mod fileobj;
mod fork_control_guest;
mod fork_control_registry;
mod freeze;
mod futex;
mod gencore;
mod hash;
mod host_helpers;
mod hugefileobj;
mod ikc_manycore;
mod ikc_master;
mod ikc_queue;
mod init;
mod list_helpers;
mod listeners;
mod llist;
mod lock_helpers;
mod mem_helpers;
mod mikc;
mod numparse;
mod object_helpers;
mod page_alloc;
mod page_helpers;
mod pager;
mod plist;
mod process_helpers;
#[cfg(process_verbose_data)]
pub(crate) mod process_verbose_data;
mod procfs;
mod profile;
mod pte_helpers;
mod rbtree;
mod refcount_helpers;
mod rlimit_helpers;
mod sched_helpers;
mod shmid_helpers;
#[cfg(f06_shmget_dispatch_candidate)]
mod f06_shmget_dispatch;
mod shmobj;
mod smp_ikc;
mod spinlock_helpers;
mod string;
mod syscall_policy;
#[cfg(f03_do_mmap_candidate)]
mod f03_do_mmap;
#[cfg(f03_do_fork_candidate)]
mod f03_do_fork;
#[cfg(f03_memory_host_offload_candidate)]
mod f03_memory_host_offload;
#[cfg(f03_mprotect_host_provider_candidate)]
mod f03_mprotect_host_provider;
#[cfg(f03_do_syscall_outer_candidate)]
mod syscall_offload_entry;
#[cfg(f03_do_syscall2_bridge_candidate)]
mod f03_do_syscall2_bridge;
#[cfg(f03_policy_forward_context_bridge_candidate)]
mod f03_policy_forward_context_bridge;
#[cfg(f03_signal_forward_provider_candidate)]
mod f03_signal_forward_provider;
#[cfg(f03_wait_host_provider_candidate)]
mod f03_wait_host_provider;
#[cfg(any(f06_rt_sigreturn_xrstor_candidate, f06_debug_constants_candidate))]
mod f06_rt_sigreturn_xrstor;
#[cfg(all(f03_forward_adapters_candidate, target_arch = "x86_64"))]
mod f03_forward_adapters;
#[cfg(all(any(f03_forward_adapters_candidate, f06_ptrace_resume_callbacks_candidate), target_arch = "x86_64"))]
mod f03_ptrace_adapters;
#[cfg(all(any(f03_forward_adapters_candidate, f03_host_cleanup_candidate), target_arch = "x86_64"))]
mod f03_host_cleanup;
#[cfg(f03_exit_group_bridges_candidate)]
mod f03_exit_group;
#[cfg(all(any(f03_forward_adapters_candidate, f03_credential_refresh_candidate), target_arch = "x86_64"))]
mod f03_credential_refresh;
#[cfg(all(f03_interrupt_syscall_candidate, target_arch = "x86_64"))]
mod f03_interrupt_syscall;
#[cfg(all(f03_terminate_candidate, target_arch = "x86_64"))]
mod f03_terminate;
#[cfg(f06_signal_ptrace_diagnostics_candidate)]
mod f06_signal_ptrace_diagnostics;
#[cfg(f06_signal_trap_info_candidate)]
mod f06_signal_trap_info;
#[cfg(native_linux_irq_work_v6_12)]
mod native_signal;
#[cfg(native_linux_irq_work_v6_12)]
mod native_fault;
#[cfg(native_linux_irq_work_v6_12)]
mod native_futex;
#[cfg(native_linux_irq_work_v6_12)]
mod native_xstate;
mod sysfs;
#[cfg(native_sysfs_verify)]
#[path = "../../scripts/tests/fixtures/mckernel_guest_sysfs.rs"]
mod sysfs_verify;
mod timer;
mod tofu_uapi;
mod ubsan;
mod waitq;
mod x86_coredump;
mod x86_cpu_helpers;
mod x86_cpu_log_providers;
mod x86_local;
mod x86_memory_helpers;
mod x86_memory_loggers;
mod x86_memory_logger_bridges;
mod x86_perfctr;
mod x86_setup;
mod x86_vsyscall;
#[cfg(native_linux_irq_work_v6_12)]
#[allow(dead_code)]
#[path = "../../host-kernel/native-rust/abi/vdso.rs"]
mod vdso_protocol;
#[cfg(native_linux_irq_work_v6_12)]
mod native_vdso;
#[cfg(native_linux_irq_work_v6_12)]
#[allow(dead_code)]
#[path = "../../host-kernel/native-rust/zero_pages.rs"]
mod zero_pages;
#[cfg(native_linux_irq_work_v6_12)]
mod clone3;
mod xpmem_helpers;
mod zeroobj;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    unsafe {
        x86_setup::early_panic();
    }
    loop {
        core::hint::spin_loop();
    }
}

#[no_mangle]
pub extern "C" fn mckernel_rust_probe() -> u32 {
    0x5255_5354
}

#[cfg(enable_perf)]
pub mod f03_perf_attr_callbacks;

#[cfg(all(f03_prlimit_body_candidate,target_arch="x86_64"))]
pub mod f03_prlimit;

#[cfg(f06_native_signal_restore_fp_candidate)]
mod f06_native_signal_restore_fp;

// Exact existing F06 BODY3-9 implementations, selected together by supported CMake profile.
#[cfg(f06_ptrace_xstate_copy_to_candidate)]
mod f06_ptrace_xstate_copy_to;
#[cfg(f06_ptrace_xstate_copy_from_candidate)]
mod f06_ptrace_xstate_copy_from;
#[cfg(f06_vdso_setup_log_candidate)]
mod f06_vdso_setup_log;
#[cfg(f06_vdso_state_candidate)]
mod f06_vdso_state;
#[cfg(f06_vdso_storage_candidate)]
mod f06_vdso_storage;
#[cfg(f06_ptrace_user_bridges_candidate)]
mod f06_ptrace_user_bridges;
#[cfg(f06_ptrace_gpregs_bridges_candidate)]
mod f06_ptrace_gpregs_bridges;

// Exact subsequent F06 BODY10-12; storage and diagnostic identities retained.
#[cfg(f06_prctl_log_candidate)]
mod f06_prctl_log;
#[cfg(f06_prctl_log_storage_candidate)]
mod f06_prctl_log_storage;
#[cfg(f06_vdso_map_log_candidate)]
mod f06_vdso_map_log;

// Private perf owner candidate only; no CMake/default activation in this patch.
#[cfg(f03_perf_owner_protocol)]
pub(crate) use syscall_policy::f03_perf_owner;
#[cfg(all(f03_perf_owner_protocol,not(all(target_arch="x86_64",enable_perf,f03_sync_child_event_candidate))))]
compile_error!("managed perf ownership requires its genuine ordinary x86/perf/header provider profile");
