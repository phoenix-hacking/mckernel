#![no_std]

use core::panic::PanicInfo;

pub mod abi;
mod bitmap;
mod bitops;
mod llist;
mod mem_helpers;
mod numparse;
mod object_helpers;
mod page_alloc;
mod page_helpers;
mod plist;
mod rbtree;
mod rlimit_helpers;
mod sched_helpers;
mod shmid_helpers;
mod string;
mod syscall_policy;
mod waitq;
mod xpmem_helpers;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}

#[no_mangle]
pub extern "C" fn mckernel_rust_probe() -> u32 {
    0x5255_5354
}
