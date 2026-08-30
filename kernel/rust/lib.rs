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
mod procfs;
mod profile;
mod pte_helpers;
mod rbtree;
mod refcount_helpers;
mod rlimit_helpers;
mod sched_helpers;
mod shmid_helpers;
mod shmobj;
mod smp_ikc;
mod spinlock_helpers;
mod string;
mod syscall_policy;
mod sysfs;
mod timer;
mod tofu_uapi;
mod ubsan;
mod waitq;
mod x86_coredump;
mod x86_cpu_helpers;
mod x86_local;
mod x86_memory_helpers;
mod x86_perfctr;
mod x86_setup;
mod x86_vsyscall;
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
