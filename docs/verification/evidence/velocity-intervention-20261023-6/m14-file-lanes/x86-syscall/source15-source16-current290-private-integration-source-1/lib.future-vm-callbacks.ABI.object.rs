#![feature(c_variadic)]
#![feature(core_intrinsics)]
#![no_std]

use core::panic::PanicInfo;

#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/abi.rs"]
pub mod abi;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/abort.rs"]
mod abort;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/affinity.rs"]
mod affinity;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/ap.rs"]
mod ap;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/atomic_helpers.rs"]
mod atomic_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/bitmap.rs"]
mod bitmap;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/bitops.rs"]
mod bitops;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/builtin_dma.rs"]
mod builtin_dma;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/cls.rs"]
mod cls;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/cls_helpers.rs"]
mod cls_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/debug.rs"]
mod debug;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/devobj.rs"]
mod devobj;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/fileobj.rs"]
mod fileobj;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/fork_control_guest.rs"]
mod fork_control_guest;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/fork_control_registry.rs"]
mod fork_control_registry;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/freeze.rs"]
mod freeze;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/futex.rs"]
mod futex;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/gencore.rs"]
mod gencore;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/hash.rs"]
mod hash;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/host_helpers.rs"]
mod host_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/hugefileobj.rs"]
mod hugefileobj;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/ikc_manycore.rs"]
mod ikc_manycore;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/ikc_master.rs"]
mod ikc_master;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/ikc_queue.rs"]
mod ikc_queue;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/init.rs"]
mod init;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/list_helpers.rs"]
mod list_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/listeners.rs"]
mod listeners;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/llist.rs"]
mod llist;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/lock_helpers.rs"]
mod lock_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/mem_helpers.rs"]
mod mem_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/mikc.rs"]
mod mikc;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/numparse.rs"]
mod numparse;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/object_helpers.rs"]
mod object_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/page_alloc.rs"]
mod page_alloc;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/page_helpers.rs"]
mod page_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/pager.rs"]
mod pager;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/plist.rs"]
mod plist;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/process_helpers.rs"]
mod process_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/procfs.rs"]
mod procfs;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/profile.rs"]
mod profile;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/pte_helpers.rs"]
mod pte_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/rbtree.rs"]
mod rbtree;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/refcount_helpers.rs"]
mod refcount_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/rlimit_helpers.rs"]
mod rlimit_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/sched_helpers.rs"]
mod sched_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/shmid_helpers.rs"]
mod shmid_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/shmobj.rs"]
mod shmobj;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/smp_ikc.rs"]
mod smp_ikc;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/spinlock_helpers.rs"]
mod spinlock_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/string.rs"]
mod string;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall/source15-source16-current290-private-integration-source-1/source/kernel/rust/syscall_policy.rs"]
mod syscall_policy;
#[cfg(native_linux_irq_work_v6_12)]
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/native_signal.rs"]
mod native_signal;
#[cfg(native_linux_irq_work_v6_12)]
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/native_fault.rs"]
mod native_fault;
#[cfg(native_linux_irq_work_v6_12)]
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/native_futex.rs"]
mod native_futex;
#[cfg(native_linux_irq_work_v6_12)]
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/native_xstate.rs"]
mod native_xstate;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/sysfs.rs"]
mod sysfs;
#[cfg(native_sysfs_verify)]
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/scripts/tests/fixtures/mckernel_guest_sysfs.rs"]
mod sysfs_verify;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/timer.rs"]
mod timer;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/tofu_uapi.rs"]
mod tofu_uapi;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/ubsan.rs"]
mod ubsan;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/waitq.rs"]
mod waitq;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/x86_coredump.rs"]
mod x86_coredump;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/x86_cpu_helpers.rs"]
mod x86_cpu_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/x86_cpu_log_providers.rs"]
mod x86_cpu_log_providers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/x86_local.rs"]
mod x86_local;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/x86_memory_helpers.rs"]
mod x86_memory_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/x86_memory_loggers.rs"]
mod x86_memory_loggers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/x86_memory_logger_bridges.rs"]
mod x86_memory_logger_bridges;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/x86_perfctr.rs"]
mod x86_perfctr;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/x86_setup.rs"]
mod x86_setup;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/x86_vsyscall.rs"]
mod x86_vsyscall;
#[cfg(native_linux_irq_work_v6_12)]
#[allow(dead_code)]
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/host-kernel/native-rust/abi/vdso.rs"]
mod vdso_protocol;
#[cfg(native_linux_irq_work_v6_12)]
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/native_vdso.rs"]
mod native_vdso;
#[cfg(native_linux_irq_work_v6_12)]
#[allow(dead_code)]
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/host-kernel/native-rust/zero_pages.rs"]
mod zero_pages;
#[cfg(native_linux_irq_work_v6_12)]
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/clone3.rs"]
mod clone3;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/xpmem_helpers.rs"]
mod xpmem_helpers;
#[path = "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-17-current285-five-data-owner-union-source-1/source/kernel/rust/zeroobj.rs"]
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

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Future object witness in the actual crate; reuse the real existing AP type.
#[no_mangle]
pub static M14_REAL_RUST_CPU_INFO_LAYOUT: [crate::abi::CULong; 8] = [
    core::mem::size_of::<crate::ap::IhkMcCpuInfo>() as crate::abi::CULong,
    core::mem::align_of::<crate::ap::IhkMcCpuInfo>() as crate::abi::CULong,
    core::mem::offset_of!(crate::ap::IhkMcCpuInfo, ncpus) as crate::abi::CULong,
    core::mem::offset_of!(crate::ap::IhkMcCpuInfo, hw_ids) as crate::abi::CULong,
    core::mem::offset_of!(crate::ap::IhkMcCpuInfo, nodes) as crate::abi::CULong,
    core::mem::offset_of!(crate::ap::IhkMcCpuInfo, linux_cpu_ids) as crate::abi::CULong,
    core::mem::offset_of!(crate::ap::IhkMcCpuInfo, ikc_cpus) as crate::abi::CULong,
    core::mem::size_of::<crate::abi::CInt>() as crate::abi::CULong,
];

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Compiler-only append to the real crate root, alongside selected mincore cfg.
#[no_mangle]
#[used]
pub static f03_mincore_Rust_ABI: [u64; 21] = [
    core::mem::size_of::<abi::ProcessVm>() as u64,
    core::mem::align_of::<abi::ProcessVm>() as u64,
    core::mem::offset_of!(abi::ProcessVm, address_space) as u64,
    core::mem::offset_of!(abi::ProcessVm, memory_range_lock) as u64,
    core::mem::offset_of!(abi::ProcessVm, page_table_lock) as u64,
    core::mem::offset_of!(abi::ProcessVm, region) as u64,
    core::mem::offset_of!(abi::Thread, vm) as u64,
    core::mem::offset_of!(abi::CpuLocalVar, current) as u64,
    core::mem::offset_of!(abi::AddressSpace, page_table) as u64,
    core::mem::offset_of!(abi::VmRegions, user_start) as u64,
    core::mem::offset_of!(abi::VmRegions, user_end) as u64,
    core::mem::offset_of!(abi::VmRange, start) as u64,
    core::mem::offset_of!(abi::VmRange, end) as u64,
    core::mem::offset_of!(abi::VmRange, memobj) as u64,
    core::mem::offset_of!(abi::VmRange, objoff) as u64,
    core::mem::size_of::<abi::IhkRwSpinlock>() as u64,
    core::mem::align_of::<abi::IhkRwSpinlock>() as u64,
    core::mem::size_of::<abi::IhkSpinlock>() as u64,
    core::mem::align_of::<abi::IhkSpinlock>() as u64,
    core::mem::size_of::<abi::OffT>() as u64,
    core::mem::size_of::<abi::CULong>() as u64,
];

// Functional OS actual production type witness; no security testing.
#[no_mangle]
#[used]
pub static SOURCE8_RUST_ABI: [usize; 12] = [
    core::mem::offset_of!(abi::CpuLocalVar, resource_set),
    core::mem::offset_of!(abi::Thread, ctx),
    core::mem::offset_of!(abi::Thread, uctx),
    core::mem::size_of::<abi::X86KernelContext>(),
    core::mem::align_of::<abi::X86KernelContext>(),
    core::mem::size_of::<abi::X86UserContext>(),
    core::mem::align_of::<abi::X86UserContext>(),
    core::mem::size_of::<*mut abi::ResourceSet>(),
    core::mem::size_of::<*mut abi::Process>(),
    core::mem::size_of::<abi::CInt>(),
    core::mem::size_of::<abi::CULong>(),
    core::mem::size_of::<*mut core::ffi::c_void>(),
];

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Compiler-only actual crate-root readonly witness; both candidate configurations.
#[no_mangle]
#[used]
pub static f03_move_pages_Rust_ABI: [u64; 30] = [
    core::mem::size_of::<abi::MovePagesSmpReq>() as u64,
    core::mem::align_of::<abi::MovePagesSmpReq>() as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, count) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, user_virt_addr) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, user_status) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, user_nodes) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, virt_addr) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, status) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, ptep) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, nodes) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, nodes_ready) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, nr_pages) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, dst_phys) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, proc) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, phase_done) as u64,
    core::mem::offset_of!(abi::MovePagesSmpReq, phase_ret) as u64,
    core::mem::size_of::<abi::Thread>() as u64,
    core::mem::offset_of!(abi::Thread, vm) as u64,
    core::mem::offset_of!(abi::Thread, cpu_set) as u64,
    core::mem::offset_of!(abi::Thread, proc) as u64,
    core::mem::offset_of!(abi::ProcessVm, page_table_lock) as u64,
    core::mem::size_of::<abi::CpuSet>() as u64,
    core::mem::align_of::<abi::CpuSet>() as u64,
    core::mem::size_of::<abi::CULong>() as u64,
    core::mem::size_of::<*mut core::ffi::c_void>() as u64,
    core::mem::size_of::<abi::CInt>() as u64,
    core::mem::size_of::<abi::CULong>() as u64,
    2usize as u64,
    core::mem::offset_of!(abi::CpuLocalVar, current) as u64,
    core::mem::size_of::<abi::ProcessVm>() as u64,
];

#[no_mangle] pub static SOURCE10_RUST_ABI:[usize;12]=[
    core::mem::size_of::<debug::Ddebug>(),core::mem::align_of::<debug::Ddebug>(),
    core::mem::offset_of!(debug::Ddebug,file),core::mem::offset_of!(debug::Ddebug,func),
    core::mem::offset_of!(debug::Ddebug,fmt),core::mem::offset_of!(debug::Ddebug,line_flags),
    core::mem::size_of::<abi::CInt>(),core::mem::size_of::<abi::CULong>(),
    core::mem::size_of::<*mut core::ffi::c_void>(),0,0,788,
];

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Append this witness module to the private actual full compute crate only.
mod f06_actual_union_abi45_witness {
 use core::mem::{size_of,align_of,offset_of};
 use crate::abi::{self,Thread,Process,SigInfo};
 use crate::lock_helpers::McsRwlockNodeIrqsave;
 #[used]
 #[no_mangle]
 pub static F06_DO_KILL_RUST_ABI45: [usize;45] = [size_of::<Thread>(),align_of::<Thread>(),size_of::<Process>(),align_of::<Process>(),
 size_of::<abi::ProcessHash>(),size_of::<abi::ThreadHash>(),offset_of!(abi::ProcessHash,lock),
 offset_of!(Thread,proc),offset_of!(Thread,sigmask),offset_of!(Thread,sigpending),
 offset_of!(Thread,sigpendinglock),offset_of!(Thread,sigcommon),offset_of!(Thread,sigevent),
 offset_of!(Thread,status),offset_of!(Thread,refcount),offset_of!(Thread,cpu_id),
 offset_of!(Process,threads_list),offset_of!(Process,threads_lock),offset_of!(Process,update_lock),
 offset_of!(Process,pid),offset_of!(Process,pgid),offset_of!(Process,parent),offset_of!(Process,main_thread),
 offset_of!(Process,ruid),offset_of!(Process,euid),offset_of!(Process,suid),offset_of!(Process,status),
 size_of::<abi::SigCommon>(),offset_of!(abi::SigCommon,sigpending),size_of::<abi::SigPending>(),
 offset_of!(abi::SigPending,info),offset_of!(abi::SigPending,ptracecont),size_of::<SigInfo>(),
 size_of::<abi::ResourceSet>(),offset_of!(abi::ResourceSet,process_hash),offset_of!(abi::ResourceSet,thread_hash),
 size_of::<abi::CpuLocalVar>(),offset_of!(abi::CpuLocalVar,resource_set),offset_of!(abi::CpuLocalVar,no_preempt),
 size_of::<abi::KmallocHeader>(),offset_of!(abi::KmallocHeader,link),offset_of!(abi::KmallocHeader,size),
 size_of::<abi::McsRwlockLock>(),align_of::<abi::McsRwlockLock>(),size_of::<McsRwlockNodeIrqsave>()];
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[no_mangle]
#[used]
pub static f03_sched_Rust_ABI: [usize; 9] = [
 core::mem::size_of::<abi::SchedParam>(),core::mem::align_of::<abi::SchedParam>(),
 core::mem::offset_of!(abi::SchedParam,sched_priority),core::mem::size_of::<abi::Thread>(),
 core::mem::offset_of!(abi::Thread,sched_param),core::mem::offset_of!(abi::Thread,sched_policy),
 core::mem::size_of::<abi::Process>(),core::mem::size_of::<abi::CULong>(),core::mem::size_of::<abi::CInt>(),
];

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[no_mangle] #[used]
pub static f03_signal_process_Rust_ABI:[usize;12]=[
 core::mem::size_of::<abi::Process>(),core::mem::offset_of!(abi::Process,threads_lock),
 core::mem::size_of::<abi::McsRwlockLock>(),core::mem::align_of::<abi::McsRwlockLock>(),
 core::mem::size_of::<abi::Thread>(),core::mem::offset_of!(abi::CpuLocalVar,current),
 core::mem::size_of::<abi::SigInfo>(),core::mem::align_of::<abi::SigInfo>(),
 core::mem::size_of::<abi::CULong>(),core::mem::size_of::<abi::CLong>(),
 core::mem::size_of::<*mut core::ffi::c_void>(),1,
];

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[no_mangle] #[used]
pub static F06_PTRACE_RUST_ABI6:[usize;6]=[core::mem::size_of::<debug::Ddebug>(),core::mem::align_of::<debug::Ddebug>(),core::mem::offset_of!(debug::Ddebug,file),core::mem::offset_of!(debug::Ddebug,func),core::mem::offset_of!(debug::Ddebug,fmt),core::mem::size_of::<[debug::Ddebug;2]>()];

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Count is C table data, read through the genuine descriptor; compare remaining
// ten layout words and separately witness descriptor count and C table edges.
#[no_mangle] #[used]
pub static f03_dispatch_Rust_ABI:[usize;10]=[
 core::mem::size_of::<syscall_policy::f03_dispatch_context_candidate::DispatchBinding>(),
 core::mem::align_of::<syscall_policy::f03_dispatch_context_candidate::DispatchBinding>(),
 core::mem::offset_of!(syscall_policy::f03_dispatch_context_candidate::DispatchBinding,handlers),
 core::mem::offset_of!(syscall_policy::f03_dispatch_context_candidate::DispatchBinding,count),
 core::mem::size_of::<Option<syscall_policy::f03_dispatch_context_candidate::Handler>>(),
 core::mem::size_of::<abi::CInt>(),core::mem::size_of::<abi::CLong>(),
 core::mem::size_of::<abi::X86UserContext>(),core::mem::align_of::<abi::X86UserContext>(),
 core::mem::size_of::<*mut core::ffi::c_void>(),
];

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[no_mangle] #[used]
pub static F06_VDSO_PUBLIC_RUST_ABI9:[usize;9]=[core::mem::size_of::<debug::Ddebug>(),core::mem::align_of::<debug::Ddebug>(),core::mem::offset_of!(debug::Ddebug,file),core::mem::offset_of!(debug::Ddebug,func),core::mem::offset_of!(debug::Ddebug,fmt),core::mem::size_of::<[debug::Ddebug;4]>(),core::mem::size_of::<abi::ProcessVm>(),core::mem::align_of::<abi::ProcessVm>(),core::mem::offset_of!(abi::ProcessVm,vdso_addr)];

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Append inside actual crate (e.g. lib.rs), never shadow private Page/layout.
#[no_mangle]pub static PROCESS_NEW3_CORE_RUST_ABI:[usize;12]=[core::mem::size_of::<crate::abi::ProcessVm>(),core::mem::align_of::<crate::abi::ProcessVm>(),core::mem::size_of::<crate::abi::VmRange>(),core::mem::align_of::<crate::abi::VmRange>(),core::mem::offset_of!(crate::abi::VmRange,memobj),core::mem::offset_of!(crate::abi::VmRange,start),core::mem::offset_of!(crate::abi::VmRange,end),core::mem::size_of::<crate::debug::Ddebug>(),core::mem::align_of::<crate::debug::Ddebug>(),core::mem::offset_of!(crate::debug::Ddebug,line_flags),core::mem::size_of::<crate::abi::SizeT>(),core::mem::size_of::<crate::abi::CULong>()];
#[no_mangle]pub static PROCESS_NEW3_FREE_RUST_ABI:[usize;12]=[core::mem::size_of::<crate::abi::ProcessVm>(),core::mem::align_of::<crate::abi::ProcessVm>(),core::mem::offset_of!(crate::abi::ProcessVm,proc),core::mem::size_of::<crate::abi::Process>(),core::mem::align_of::<crate::abi::Process>(),core::mem::offset_of!(crate::abi::Process,straight_va),core::mem::offset_of!(crate::abi::Process,straight_len),core::mem::offset_of!(crate::abi::Process,straight_pa),core::mem::size_of::<crate::abi::VmRange>(),core::mem::offset_of!(crate::abi::VmRange,start),core::mem::offset_of!(crate::abi::VmRange,end),core::mem::offset_of!(crate::abi::VmRange,memobj)];
#[no_mangle]pub static PROCESS_NEW3_ZEROOBJ_RUST_ABI:[usize;4]=[core::mem::size_of::<*mut crate::abi::Memobj>(),core::mem::align_of::<*mut crate::abi::Memobj>(),core::mem::size_of::<crate::abi::CInt>(),core::mem::size_of::<*mut *mut crate::abi::Memobj>()];

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact genuine ABI vector from Source9 controlled-fixture main.rs expected[].
#[no_mangle] #[used]
pub static f03_leaf_Rust_ABI:[usize;5]=[core::mem::size_of::<abi::CInt>(),core::mem::align_of::<abi::CInt>(),core::mem::size_of::<abi::CULong>(),core::mem::size_of::<abi::CLong>(),core::mem::size_of::<*mut core::ffi::c_void>()];

// Functional OS only; no security testing. Append where crate modules are visible.
#[no_mangle] pub static PROCESS_POST230_RUST_ABI45: [usize;45] = [
 core::mem::size_of::<crate::abi::CpuLocalVar>(),
 core::mem::align_of::<crate::abi::CpuLocalVar>(),
 core::mem::offset_of!(crate::abi::CpuLocalVar,idle),
 core::mem::offset_of!(crate::abi::CpuLocalVar,runq_lock),
 core::mem::offset_of!(crate::abi::CpuLocalVar,runq_irqstate),
 core::mem::offset_of!(crate::abi::CpuLocalVar,current),
 core::mem::offset_of!(crate::abi::CpuLocalVar,no_preempt),
 core::mem::offset_of!(crate::abi::CpuLocalVar,nr_ctx_switches),
 core::mem::offset_of!(crate::abi::CpuLocalVar,runq_len),
 core::mem::size_of::<crate::abi::Thread>(),
 core::mem::align_of::<crate::abi::Thread>(),
 core::mem::offset_of!(crate::abi::Thread,tid),
 core::mem::offset_of!(crate::abi::Thread,status),
 core::mem::offset_of!(crate::abi::Thread,proc),
 core::mem::offset_of!(crate::abi::Thread,vm),
 core::mem::offset_of!(crate::abi::Thread,uctx),
 core::mem::size_of::<crate::abi::Process>(),
 core::mem::align_of::<crate::abi::Process>(),
 core::mem::offset_of!(crate::abi::Process,pid),
 core::mem::size_of::<crate::abi::ProcessVm>(),
 core::mem::align_of::<crate::abi::ProcessVm>(),
 core::mem::offset_of!(crate::abi::ProcessVm,address_space),
 core::mem::size_of::<crate::abi::AddressSpace>(),
 core::mem::align_of::<crate::abi::AddressSpace>(),
 core::mem::offset_of!(crate::abi::AddressSpace,page_table),
 core::mem::size_of::<crate::abi::X86UserContext>(),
 core::mem::align_of::<crate::abi::X86UserContext>(),
 core::mem::offset_of!(crate::abi::X86UserContext,gpr),
 core::mem::size_of::<crate::abi::X86BasicRegs>(),
 core::mem::align_of::<crate::abi::X86BasicRegs>(),
 core::mem::offset_of!(crate::abi::X86BasicRegs,rip),
 core::mem::offset_of!(crate::abi::X86BasicRegs,rsp),
 core::mem::size_of::<crate::sched_helpers::SchedRunqueueOffsets>(),
 core::mem::align_of::<crate::sched_helpers::SchedRunqueueOffsets>(),
 core::mem::size_of::<crate::sched_helpers::SchedScheduleResult>(),
 core::mem::align_of::<crate::sched_helpers::SchedScheduleResult>(),
 core::mem::offset_of!(crate::sched_helpers::SchedScheduleResult,cpu_addr),
 core::mem::offset_of!(crate::sched_helpers::SchedScheduleResult,prev_thread_addr),
 core::mem::offset_of!(crate::sched_helpers::SchedScheduleResult,next_thread_addr),
 core::mem::offset_of!(crate::sched_helpers::SchedScheduleResult,prevpid),
 core::mem::size_of::<crate::sched_helpers::SchedExitDebug>(),
 core::mem::align_of::<crate::sched_helpers::SchedExitDebug>(),
 core::mem::size_of::<crate::debug::Ddebug>(),
 core::mem::align_of::<crate::debug::Ddebug>(),
 core::mem::offset_of!(crate::debug::Ddebug,line_flags),
];

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[no_mangle] #[used]
pub static f03_atomic_Rust_ABI:[usize;12]=[
 core::mem::size_of::<abi::CInt>(),core::mem::align_of::<abi::CInt>(),
 core::mem::size_of::<abi::CULong>(),core::mem::size_of::<*mut abi::CInt>(),
 0,1,2,3,4,38,14,0,
];

mod post230_genuine_abi_00 {
use core::ffi::c_void;
use crate::abi::{CpuLocalVar, Thread, IhkSpinlock, CULong, Memobj, MemobjOps, VmRange, ProcessVm, OffT, CInt, CpuSet, SizeT};
use crate::{abi, sched_helpers, debug};
type Handler = unsafe extern "C" fn(CInt,CInt,*mut c_void)->CInt;
type Visit = unsafe extern "C" fn(*mut c_void,*mut c_void,*mut CULong,*mut c_void,CInt)->CInt;
#[no_mangle]
#[used]
pub static PROCESS_POST230_RUST_ABI_00:[usize;16]=[core::mem::size_of::<CpuLocalVar>(),core::mem::align_of::<CpuLocalVar>(),core::mem::offset_of!(CpuLocalVar,monitor),core::mem::size_of::<Thread>(),core::mem::align_of::<Thread>(),core::mem::offset_of!(Thread,ctx),core::mem::size_of::<abi::X86KernelContext>(),core::mem::align_of::<abi::X86KernelContext>(),core::mem::size_of::<sched_helpers::SchedIdleOffsets>(),core::mem::align_of::<sched_helpers::SchedIdleOffsets>(),core::mem::size_of::<sched_helpers::SchedIdleValues>(),core::mem::align_of::<sched_helpers::SchedIdleValues>(),core::mem::size_of::<sched_helpers::SchedIdleCallbacks>(),core::mem::align_of::<sched_helpers::SchedIdleCallbacks>(),core::mem::offset_of!(sched_helpers::SchedIdleOffsets,cpu_current_offset),core::mem::offset_of!(sched_helpers::SchedIdleCallbacks,safe_halt)];
}

mod post230_genuine_abi_01 {
use core::ffi::c_void;
use crate::abi::{CpuLocalVar, Thread, IhkSpinlock, CULong, Memobj, MemobjOps, VmRange, ProcessVm, OffT, CInt, CpuSet, SizeT};
use crate::{abi, sched_helpers, debug};
type Handler = unsafe extern "C" fn(CInt,CInt,*mut c_void)->CInt;
type Visit = unsafe extern "C" fn(*mut c_void,*mut c_void,*mut CULong,*mut c_void,CInt)->CInt;
#[no_mangle]
#[used]
pub static PROCESS_POST230_RUST_ABI_01:[usize;12]=[core::mem::size_of::<IhkSpinlock>(),core::mem::align_of::<IhkSpinlock>(),core::mem::offset_of!(IhkSpinlock,head_tail),core::mem::size_of::<CULong>(),core::mem::size_of::<u32>(),core::mem::size_of::<*mut IhkSpinlock>(),crate::x86_cpu_helpers::POST230_TIMER_CONSTANTS[0],crate::x86_cpu_helpers::POST230_TIMER_CONSTANTS[1],crate::x86_cpu_helpers::POST230_TIMER_CONSTANTS[2],crate::x86_cpu_helpers::POST230_TIMER_CONSTANTS[3],crate::x86_cpu_helpers::POST230_TIMER_CONSTANTS[4],crate::x86_cpu_helpers::POST230_TIMER_CONSTANTS[5]];
}

mod post230_genuine_abi_02 {
use core::ffi::c_void;
use crate::abi::{CpuLocalVar, Thread, IhkSpinlock, CULong, Memobj, MemobjOps, VmRange, ProcessVm, OffT, CInt, CpuSet, SizeT};
use crate::{abi, sched_helpers, debug};
type Handler = unsafe extern "C" fn(CInt,CInt,*mut c_void)->CInt;
type Visit = unsafe extern "C" fn(*mut c_void,*mut c_void,*mut CULong,*mut c_void,CInt)->CInt;
#[no_mangle]
#[used]
pub static PROCESS_POST230_RUST_ABI_02:[usize;12]=[
 core::mem::size_of::<Memobj>(),core::mem::align_of::<Memobj>(),core::mem::offset_of!(Memobj,ops),
 core::mem::size_of::<MemobjOps>(),core::mem::align_of::<MemobjOps>(),core::mem::offset_of!(MemobjOps,lookup_page),core::mem::offset_of!(MemobjOps,update_page),
 core::mem::size_of::<crate::page_helpers::Page>(),core::mem::align_of::<crate::page_helpers::Page>(),core::mem::size_of::<VmRange>(),core::mem::size_of::<ProcessVm>(),core::mem::size_of::<OffT>()];
}

mod post230_genuine_abi_03 {
use core::ffi::c_void;
use crate::abi::{CpuLocalVar, Thread, IhkSpinlock, CULong, Memobj, MemobjOps, VmRange, ProcessVm, OffT, CInt, CpuSet, SizeT};
use crate::{abi, sched_helpers, debug};
type Handler = unsafe extern "C" fn(CInt,CInt,*mut c_void)->CInt;
type Visit = unsafe extern "C" fn(*mut c_void,*mut c_void,*mut CULong,*mut c_void,CInt)->CInt;
#[no_mangle]
#[used]
pub static PROCESS_POST230_RUST_ABI_03:[usize;12]=[core::mem::size_of::<ProcessVm>(),core::mem::align_of::<ProcessVm>(),core::mem::size_of::<VmRange>(),core::mem::align_of::<VmRange>(),core::mem::offset_of!(VmRange,start),core::mem::offset_of!(VmRange,end),core::mem::size_of::<CULong>(),core::mem::size_of::<CInt>(),core::mem::size_of::<*mut c_void>(),core::mem::size_of::<CULong>(),core::mem::align_of::<CULong>(),core::mem::size_of::<unsafe extern "C" fn(CInt,CULong,*mut i8,CInt)->*mut c_void>()];
}

mod post230_genuine_abi_04 {
use core::ffi::c_void;
use crate::abi::{CpuLocalVar, Thread, IhkSpinlock, CULong, Memobj, MemobjOps, VmRange, ProcessVm, OffT, CInt, CpuSet, SizeT};
use crate::{abi, sched_helpers, debug};
type Handler = unsafe extern "C" fn(CInt,CInt,*mut c_void)->CInt;
type Visit = unsafe extern "C" fn(*mut c_void,*mut c_void,*mut CULong,*mut c_void,CInt)->CInt;
#[no_mangle]
#[used]
pub static PROCESS_POST230_RUST_ABI_04:[usize;12]=[core::mem::size_of::<CpuSet>(),core::mem::align_of::<CpuSet>(),core::mem::size_of::<SizeT>(),core::mem::size_of::<CULong>(),core::mem::size_of::<CInt>(),core::mem::size_of::<Handler>(),core::mem::size_of::<Option<Handler>>(),core::mem::size_of::<ProcessVm>(),core::mem::size_of::<VmRange>(),core::mem::offset_of!(VmRange,start),core::mem::offset_of!(VmRange,end),core::mem::size_of::<*mut c_void>()];
}

mod post230_genuine_abi_05 {
use core::ffi::c_void;
use crate::abi::{CpuLocalVar, Thread, IhkSpinlock, CULong, Memobj, MemobjOps, VmRange, ProcessVm, OffT, CInt, CpuSet, SizeT};
use crate::{abi, sched_helpers, debug};
type Handler = unsafe extern "C" fn(CInt,CInt,*mut c_void)->CInt;
type Visit = unsafe extern "C" fn(*mut c_void,*mut c_void,*mut CULong,*mut c_void,CInt)->CInt;
#[no_mangle]
#[used]
pub static PROCESS_POST230_RUST_ABI_05:[usize;12]=[core::mem::size_of::<CULong>(),core::mem::align_of::<CULong>(),core::mem::size_of::<*mut c_void>(),core::mem::size_of::<CULong>(),core::mem::size_of::<CInt>(),core::mem::size_of::<CInt>(),core::mem::size_of::<Visit>(),core::mem::size_of::<Option<Visit>>(),core::mem::size_of::<ProcessVm>(),core::mem::align_of::<ProcessVm>(),core::mem::size_of::<abi::IhkMcPtAttribute>(),core::mem::align_of::<abi::IhkMcPtAttribute>()];
}

mod post230_genuine_abi_06 {
use core::ffi::c_void;
use crate::abi::{CpuLocalVar, Thread, IhkSpinlock, CULong, Memobj, MemobjOps, VmRange, ProcessVm, OffT, CInt, CpuSet, SizeT};
use crate::{abi, sched_helpers, debug};
type Handler = unsafe extern "C" fn(CInt,CInt,*mut c_void)->CInt;
type Visit = unsafe extern "C" fn(*mut c_void,*mut c_void,*mut CULong,*mut c_void,CInt)->CInt;
#[no_mangle]
#[used]
pub static PROCESS_POST230_RUST_ABI_06:[usize;8]=[core::mem::size_of::<ProcessVm>(),core::mem::align_of::<ProcessVm>(),core::mem::size_of::<VmRange>(),core::mem::align_of::<VmRange>(),core::mem::size_of::<*const i8>(),core::mem::size_of::<unsafe extern "C" fn(*const i8)>(),core::mem::size_of::<i8>(),core::mem::size_of::<CInt>()];
}

mod post230_genuine_abi_07 {
use core::ffi::c_void;
use crate::abi::{CpuLocalVar, Thread, IhkSpinlock, CULong, Memobj, MemobjOps, VmRange, ProcessVm, OffT, CInt, CpuSet, SizeT};
use crate::{abi, sched_helpers, debug};
type Handler = unsafe extern "C" fn(CInt,CInt,*mut c_void)->CInt;
type Visit = unsafe extern "C" fn(*mut c_void,*mut c_void,*mut CULong,*mut c_void,CInt)->CInt;
#[no_mangle]
#[used]
pub static PROCESS_POST230_RUST_ABI_07:[usize;12]=[core::mem::size_of::<debug::Ddebug>(),core::mem::align_of::<debug::Ddebug>(),core::mem::offset_of!(debug::Ddebug,fmt),core::mem::offset_of!(debug::Ddebug,line_flags),core::mem::size_of::<VmRange>(),core::mem::align_of::<VmRange>(),core::mem::offset_of!(VmRange,start),core::mem::offset_of!(VmRange,end),core::mem::offset_of!(VmRange,straight_start),core::mem::size_of::<ProcessVm>(),core::mem::align_of::<ProcessVm>(),core::mem::size_of::<CInt>()];
}

mod post230_genuine_abi_08 {
use core::ffi::c_void;
use crate::abi::{CpuLocalVar, Thread, IhkSpinlock, CULong, Memobj, MemobjOps, VmRange, ProcessVm, OffT, CInt, CpuSet, SizeT};
use crate::{abi, sched_helpers, debug};
type Handler = unsafe extern "C" fn(CInt,CInt,*mut c_void)->CInt;
type Visit = unsafe extern "C" fn(*mut c_void,*mut c_void,*mut CULong,*mut c_void,CInt)->CInt;
#[no_mangle]
#[used]
pub static PROCESS_POST230_RUST_ABI_08:[usize;12]=[core::mem::size_of::<debug::Ddebug>(),core::mem::align_of::<debug::Ddebug>(),core::mem::offset_of!(debug::Ddebug,fmt),core::mem::offset_of!(debug::Ddebug,line_flags),core::mem::size_of::<abi::VmRange>(),core::mem::align_of::<abi::VmRange>(),core::mem::offset_of!(abi::VmRange,start),core::mem::offset_of!(abi::VmRange,end),core::mem::size_of::<abi::CLong>(),core::mem::size_of::<abi::SizeT>(),core::mem::size_of::<abi::ProcessVm>(),core::mem::size_of::<CInt>()];
}

mod post285_genuine_abi_00 {
use core::ffi::c_void;
use crate::abi::{CInt, CULong, CLong, SizeT, ProcessVm, VmRange};
use crate::{abi, debug, sched_helpers};
type Clear = unsafe extern "C" fn(*mut c_void, CULong);
#[no_mangle]
#[used]
pub static PROCESS_POST285_RUST_ABI_00:[usize;12]=[core::mem::size_of::<debug::Ddebug>(),core::mem::align_of::<debug::Ddebug>(),core::mem::offset_of!(debug::Ddebug,fmt),core::mem::offset_of!(debug::Ddebug,line_flags),core::mem::size_of::<abi::VmRange>(),core::mem::align_of::<abi::VmRange>(),core::mem::offset_of!(abi::VmRange,start),core::mem::offset_of!(abi::VmRange,end),core::mem::size_of::<abi::Thread>(),core::mem::align_of::<abi::Thread>(),core::mem::offset_of!(abi::Thread,status),core::mem::offset_of!(abi::Thread,cpu_id)];
}

mod post285_genuine_abi_01 {
use core::ffi::c_void;
use crate::abi::{CInt, CULong, CLong, SizeT, ProcessVm, VmRange};
use crate::{abi, debug, sched_helpers};
type Clear = unsafe extern "C" fn(*mut c_void, CULong);
#[no_mangle]
#[used]
pub static PROCESS_POST285_RUST_ABI_01:[usize;8]=[core::mem::size_of::<CULong>(),core::mem::size_of::<SizeT>(),core::mem::size_of::<*mut c_void>(),core::mem::align_of::<*mut c_void>(),core::mem::size_of::<Clear>(),core::mem::size_of::<Option<Clear>>(),core::mem::align_of::<Option<Clear>>(),core::mem::size_of::<CInt>()];
}

mod post285_genuine_abi_02 {
use core::ffi::c_void;
use crate::abi::{CInt, CULong, CLong, SizeT, ProcessVm, VmRange};
use crate::{abi, debug, sched_helpers};
type Clear = unsafe extern "C" fn(*mut c_void, CULong);
#[no_mangle]
#[used]
pub static PROCESS_POST285_RUST_ABI_02:[usize;12]=[core::mem::size_of::<sched_helpers::SchedExitDebug>(),core::mem::align_of::<sched_helpers::SchedExitDebug>(),core::mem::offset_of!(sched_helpers::SchedExitDebug,num_threads),core::mem::offset_of!(sched_helpers::SchedExitDebug,total_memory_usage),core::mem::offset_of!(sched_helpers::SchedExitDebug,memory_stat_rss),core::mem::offset_of!(sched_helpers::SchedExitDebug,memory_stat_mapped_file),core::mem::offset_of!(sched_helpers::SchedExitDebug,page_sizes),core::mem::size_of::<CULong>(),core::mem::size_of::<CLong>(),core::mem::size_of::<core::sync::atomic::AtomicU64>(),core::mem::align_of::<core::sync::atomic::AtomicI64>(),core::mem::size_of::<CInt>()];
}

mod post285_genuine_abi_03 {
use core::ffi::c_void;
use crate::abi::{CInt, CULong, CLong, SizeT, ProcessVm, VmRange};
use crate::{abi, debug, sched_helpers};
type Clear = unsafe extern "C" fn(*mut c_void, CULong);
#[no_mangle]
#[used]
pub static PROCESS_POST285_RUST_ABI_03:[usize;12]=[core::mem::size_of::<ProcessVm>(),core::mem::align_of::<ProcessVm>(),core::mem::size_of::<VmRange>(),core::mem::align_of::<VmRange>(),core::mem::size_of::<CULong>(),core::mem::size_of::<u64>(),core::mem::size_of::<usize>(),core::mem::size_of::<*mut ProcessVm>(),core::mem::size_of::<CInt>(),core::mem::offset_of!(VmRange,start),core::mem::offset_of!(VmRange,end),core::mem::offset_of!(ProcessVm,address_space)];
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(all(f03_syscall_entry_candidate, f03_dispatch_context_candidate, enable_profile))]
mod f03_syscall_entry_abi52 {
 use core::mem::{size_of, align_of, offset_of};
 use crate::{abi, debug};
 use crate::syscall_policy::f03_syscall_entry_candidate;
pub const ENTRY_ABI: [usize; 52] = [
size_of::<abi::Thread>(),
align_of::<abi::Thread>(),
offset_of!(abi::Thread, tid),
offset_of!(abi::Thread, status),
offset_of!(abi::Thread, proc),
offset_of!(abi::Thread, profile),
offset_of!(abi::Thread, profile_start_ts),
offset_of!(abi::Thread, profile_elapsed_ts),
offset_of!(abi::Thread, ptrace),
offset_of!(abi::Thread, sigpending),
offset_of!(abi::Thread, sigcommon),
size_of::<abi::Process>(),
align_of::<abi::Process>(),
offset_of!(abi::Process, pid),
offset_of!(abi::Process, status),
offset_of!(abi::Process, nohost),
size_of::<abi::CpuLocalVar>(),
align_of::<abi::CpuLocalVar>(),
offset_of!(abi::CpuLocalVar, current),
offset_of!(abi::CpuLocalVar, flags),
size_of::<abi::SigCommon>(),
align_of::<abi::SigCommon>(),
offset_of!(abi::SigCommon, sigpending),
size_of::<f03_syscall_entry_candidate::EntryConfig>(),
align_of::<f03_syscall_entry_candidate::EntryConfig>(),
offset_of!(f03_syscall_entry_candidate::EntryConfig, names),
offset_of!(f03_syscall_entry_candidate::EntryConfig, name_count),
offset_of!(f03_syscall_entry_candidate::EntryConfig, fork_drain),
offset_of!(f03_syscall_entry_candidate::EntryConfig, profile_max),
offset_of!(f03_syscall_entry_candidate::EntryConfig, profile_nr),
offset_of!(f03_syscall_entry_candidate::EntryConfig, exit_nr),
offset_of!(f03_syscall_entry_candidate::EntryConfig, exit_group_nr),
offset_of!(f03_syscall_entry_candidate::EntryConfig, sched_yield_nr),
offset_of!(f03_syscall_entry_candidate::EntryConfig, epoll_wait_nr),
offset_of!(f03_syscall_entry_candidate::EntryConfig, epoll_pwait_nr),
offset_of!(f03_syscall_entry_candidate::EntryConfig, ppoll_nr),
offset_of!(f03_syscall_entry_candidate::EntryConfig, mode_u2k),
offset_of!(f03_syscall_entry_candidate::EntryConfig, mode_k2u),
offset_of!(f03_syscall_entry_candidate::EntryConfig, sigkill),
offset_of!(f03_syscall_entry_candidate::EntryConfig, disable_yield),
offset_of!(f03_syscall_entry_candidate::EntryConfig, fugaku),
offset_of!(f03_syscall_entry_candidate::EntryConfig, resched_mask),
size_of::<core::sync::atomic::AtomicU64>(),
align_of::<core::sync::atomic::AtomicU64>(),
u32::MAX as usize,
0usize,
128usize,
2usize,
size_of::<abi::X86UserContext>(),
align_of::<abi::X86UserContext>(),
size_of::<debug::Ddebug>(),
align_of::<debug::Ddebug>()
];

 #[used]
 #[no_mangle]
 pub static f03_syscall_entry_Rust_ABI52: [usize; 52] = ENTRY_ABI;
}

#[cfg(all(f03_syscall_entry_candidate,f03_dispatch_context_candidate,enable_profile))]
const _: unsafe extern "C" fn(crate::abi::CInt,*mut crate::abi::X86UserContext)->crate::abi::CLong = crate::syscall_policy::f03_syscall_entry_candidate::syscall_entry;

#[cfg(process_global_storage_candidate)]
#[used]
#[no_mangle]pub static PROCESS_STORAGE3_RUST_ABI18:[usize;18]=[
 core::mem::size_of::<crate::abi::IhkSpinlock>(),core::mem::align_of::<crate::abi::IhkSpinlock>(),core::mem::offset_of!(crate::abi::IhkSpinlock,head_tail),
 core::mem::size_of::<crate::abi::McsRwlockLock>(),core::mem::align_of::<crate::abi::McsRwlockLock>(),core::mem::offset_of!(crate::abi::McsRwlockLock,slock),
 core::mem::size_of::<crate::abi::AbiListHead>(),core::mem::align_of::<crate::abi::AbiListHead>(),core::mem::offset_of!(crate::abi::AbiListHead,next),core::mem::offset_of!(crate::abi::AbiListHead,prev),
 core::mem::size_of::<crate::spinlock_helpers::IhkSpinlock>(),core::mem::align_of::<crate::spinlock_helpers::IhkSpinlock>(),
 core::mem::size_of::<crate::lock_helpers::McsRwlockLock>(),core::mem::align_of::<crate::lock_helpers::McsRwlockLock>(),
 core::mem::size_of::<crate::abi::ResourceSet>(),core::mem::align_of::<crate::abi::ResourceSet>(),core::mem::offset_of!(crate::abi::ResourceSet,list),core::mem::offset_of!(crate::abi::ResourceSet,cpu_set)];

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Compiler-only witnesses appended to the central genuine lib root.
#[cfg(all(f03_syscall_table_candidate, f03_dispatch_context_candidate))]
mod f03_table_compiler_abi {
 use core::mem::{size_of,align_of,offset_of};
 use crate::abi::{CInt,CLong,X86UserContext};
 use crate::syscall_policy::f03_dispatch_context_candidate::{DispatchBinding,Handler};
 use crate::syscall_policy::f03_syscall_table_candidate::SLOT_COUNT;
 #[no_mangle]
 pub static f03_table_Rust_ABI11:[usize;11]=[
  size_of::<DispatchBinding>(),align_of::<DispatchBinding>(),
  offset_of!(DispatchBinding,handlers),offset_of!(DispatchBinding,count),
  size_of::<Option<Handler>>(),SLOT_COUNT,size_of::<CInt>(),size_of::<CLong>(),
  size_of::<X86UserContext>(),align_of::<X86UserContext>(),size_of::<*mut core::ffi::c_void>()
 ];
 #[no_mangle]
 pub static f03_table_Rust_guards4:[usize;4]=[
  cfg!(enable_profile) as usize,cfg!(enable_perf) as usize,
  cfg!(f03_syscall_table_clone3) as usize,cfg!(f03_syscall_table_dcfa) as usize
 ];
}
