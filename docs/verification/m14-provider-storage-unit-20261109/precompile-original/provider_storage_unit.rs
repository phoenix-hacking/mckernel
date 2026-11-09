#![no_std]
// Actual six storage definitions and bounded address-logger closure only.
// Source/codegeneration/partial-link preparation is NOT runtime initialization.
// No allocator, boot, GS/MSR, mapping setup or logging provider is supplied here.
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;
mod cls {
use crate::abi::CpuLocalVar;
use core::ptr::null_mut;
#[no_mangle]
pub static mut clv: *mut CpuLocalVar = null_mut();
}
mod x86_local {
use crate::abi::X86CpuLocalVariables;
#[no_mangle]
pub static mut locals: *mut X86CpuLocalVariables = core::ptr::null_mut();
}
mod ap {
use crate::abi::CInt;
#[no_mangle]
pub static mut num_processors: CInt = 1;
}
mod x86_setup {
use crate::abi::CULong;
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut linux_page_offset_base: CULong = 0;
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut x86_kernel_phys_base: CULong = 0;
}
mod debug {
#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}
const _: () = {
    use core::mem::{align_of, offset_of, size_of};
    assert!(size_of::<Ddebug>() == 32);
    assert!(align_of::<Ddebug>() == 8);
    assert!(offset_of!(Ddebug, line_flags) == 24);
};
}
mod x86_memory_helpers {
mod owned_memory_data {
use crate::abi::CULong;
    const TRACE_FILE_BYTES: [u8;
    static TRACE_FILE: [u8;
    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    pub(super) static mut x86_addr_log_straight_debug: crate::debug::Ddebug =
        crate::debug::Ddebug {
            file: TRACE_FILE.as_ptr().cast(),
            func: b"x86_addr_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 3276,
        };
    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    pub(super) static mut x86_addr_log_kernel_debug: crate::debug::Ddebug =
        crate::debug::Ddebug {
            file: TRACE_FILE.as_ptr().cast(),
            func: b"x86_addr_log_bridge\0".as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: 3272,
        };
    #[no_mangle]
    pub(super) static x86_map_kernel_start_geometry: CULong = 0xfffffffffe800000;
}
}
mod x86_memory_logger_bridges {
use core::ffi::c_char;
use core::ptr::{addr_of, read_volatile};
use crate::abi::{CInt, CULong};
use crate::debug::Ddebug;
unsafe extern "C" {
    fn kprintf(format: *const c_char, ...) -> CInt;
    static mut x86_addr_log_kernel_debug: Ddebug;
    static mut x86_addr_log_straight_debug: Ddebug;
}
unsafe fn debug_enabled(descriptor: *const Ddebug) -> bool {
    // SAFETY: the caller supplies live C descriptor storage; the selected C/Rust
    // layout places the 24-bit line and high 8-bit flags at byte offset 24.
    unsafe { read_volatile(addr_of!((*descriptor).line_flags)) >> 24 != 0 }
}
#[no_mangle]
pub extern "C" fn x86_addr_log_bridge(event: CInt, value: CULong) {
    // SAFETY: descriptor storage is provided by the selected C translation unit;
    // formats and %s data are static, and value retains its unsigned-long width.
    unsafe {
        match event {
            1 if debug_enabled(addr_of!(x86_addr_log_kernel_debug)) => {
                kprintf(
                    b"%s: MAP_KERNEL_START <= 0x%lx <= linux_page_offset_base\n\0"
                        .as_ptr()
                        .cast(),
                    b"virt_to_phys\0".as_ptr().cast::<c_char>(),
                    value,
                );
            }
            2 if debug_enabled(addr_of!(x86_addr_log_straight_debug)) => {
                kprintf(
                    b"%s: MAP_ST_START <= 0x%lx <= MAP_FIXED_START\n\0".as_ptr().cast(),
                    b"virt_to_phys\0".as_ptr().cast::<c_char>(),
                    value,
                );
            }
            _ => {}
        }
    }
}
}
