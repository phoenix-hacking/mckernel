#![no_std]

use core::panic::PanicInfo;

pub mod abi;
mod bitmap;
mod bitops;
mod llist;
mod mem_helpers;
mod numparse;
mod page_alloc;
mod page_helpers;
mod plist;
mod rbtree;
mod sched_helpers;
mod shmid_helpers;
mod string;
mod waitq;

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
