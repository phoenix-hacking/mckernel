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
    const TRACE_FILE_BYTES: [u8; 319] = [
        47, 104, 111, 109, 101, 47, 104, 111, 108, 100, 101, 110, 47, 109, 99, 107, 101, 114, 110, 101,
        108, 45, 119, 111, 114, 107, 47, 104, 111, 115, 116, 45, 112, 114, 101, 112, 97, 114, 97, 116,
        105, 111, 110, 47, 118, 101, 108, 111, 99, 105, 116, 121, 45, 105, 110, 116, 101, 114, 118, 101,
        110, 116, 105, 111, 110, 45, 50, 48, 50, 54, 49, 48, 50, 51, 45, 49, 53, 47, 109, 49,
        52, 45, 114, 101, 116, 97, 105, 110, 101, 100, 45, 118, 97, 108, 105, 100, 97, 116, 111, 114,
        45, 99, 111, 110, 116, 105, 110, 117, 97, 116, 105, 111, 110, 45, 49, 47, 119, 104, 111, 108,
        101, 45, 109, 101, 109, 111, 114, 121, 45, 99, 108, 111, 115, 117, 114, 101, 45, 115, 111, 117,
        114, 99, 101, 45, 51, 47, 112, 114, 111, 100, 117, 99, 116, 105, 111, 110, 45, 99, 111, 110,
        115, 117, 109, 101, 114, 45, 112, 114, 101, 112, 97, 114, 97, 116, 105, 111, 110, 45, 49, 47,
        98, 111, 117, 110, 100, 101, 100, 45, 116, 121, 112, 101, 45, 105, 109, 112, 111, 114, 116, 45,
        99, 111, 114, 114, 101, 99, 116, 105, 111, 110, 45, 49, 47, 101, 120, 112, 101, 114, 116, 45,
        111, 117, 116, 101, 114, 45, 98, 114, 97, 99, 101, 45, 99, 111, 114, 114, 101, 99, 116, 105,
        111, 110, 45, 49, 47, 114, 101, 97, 108, 45, 115, 112, 108, 105, 116, 45, 112, 114, 111, 118,
        105, 100, 101, 114, 45, 115, 111, 117, 114, 99, 101, 45, 115, 117, 99, 99, 101, 115, 115, 111,
        114, 45, 49, 47, 115, 111, 117, 114, 99, 101, 47, 97, 114, 99, 104, 47, 120, 56, 54, 95,
        54, 52, 47, 107, 101, 114, 110, 101, 108, 47, 109, 101, 109, 111, 114, 121, 46, 99, 0,
    ];
    static TRACE_FILE: [u8; 319] = TRACE_FILE_BYTES;
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
