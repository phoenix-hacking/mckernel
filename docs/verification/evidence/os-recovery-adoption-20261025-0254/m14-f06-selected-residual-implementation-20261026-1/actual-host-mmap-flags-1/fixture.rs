//! Functional McKernel OS/apps only; no security testing.
#![no_std]
mod abi { pub type CInt = i32; }
use abi::CInt;
const MAP_SHARED: CInt = 0x01;
const MAP_PRIVATE: CInt = 0x02;
const MAP_FIXED: CInt = 0x10;
const MAP_ANONYMOUS: CInt = 0x20;
const MAP_LOCKED: CInt = 0x2000;
const MAP_POPULATE: CInt = 0x8000;
const MAP_HUGETLB: CInt = 0x00040000;
const MAP_HUGE_MASK: CInt = 0xfc000000u32 as CInt;
#[cfg(f06_mmap_flag_providers)]
#[path = "f06_mmap_flags.rs"]
mod providers;
#[panic_handler]
fn panic(_info: &core::panic::PanicInfo<'_>) -> ! { loop { core::hint::spin_loop(); } }
