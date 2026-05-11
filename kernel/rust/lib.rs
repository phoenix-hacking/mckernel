#![no_std]

use core::panic::PanicInfo;

pub mod abi;
mod bitmap;
mod llist;
mod rbtree;

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
