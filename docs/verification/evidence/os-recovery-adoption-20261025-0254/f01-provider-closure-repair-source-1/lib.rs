#![feature(c_variadic)]
#![feature(core_intrinsics)]
#![no_std]

use core::panic::PanicInfo;


pub mod abi;
mod llist;
mod rbtree;
mod string;
mod hash;
mod spinlock_helpers;
mod mem_helpers;
mod x86_setup;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    unsafe {
        x86_setup::early_panic();
    }
    loop {
        core::hint::spin_loop();
    }
}

