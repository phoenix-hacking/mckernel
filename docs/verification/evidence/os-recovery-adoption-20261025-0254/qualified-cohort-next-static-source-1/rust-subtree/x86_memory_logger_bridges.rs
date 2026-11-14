//! Memory diagnostics with their original per-callsite C debug descriptors.
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

use core::ffi::{c_char, c_void};
use core::ptr::{addr_of, null_mut, read_volatile};

use crate::abi::{CInt, CULong};
use crate::debug::Ddebug;

// Selected x86_64 arch-memory.h fixes PAGE_SHIFT to 12 and PAGE_SIZE to 1UL << 12.
const PAGE_SHIFT: u32 = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const PAGE_MASK: CULong = !(PAGE_SIZE - 1);

unsafe extern "C" {
    fn kprintf(format: *const c_char, ...) -> CInt;

    static mut x86_addr_log_kernel_debug: Ddebug;
    static mut x86_addr_log_straight_debug: Ddebug;
    static mut x86_init_linux_log_chunk_range_debug: Ddebug;
    static mut x86_map_fixed_area_log_debug: Ddebug;
    static mut x86_user_copy_log_external_debug: Ddebug;
    static mut x86_user_copy_log_patch_start_debug: Ddebug;
    static mut x86_user_copy_log_patch_done_debug: Ddebug;
}

/// Read the same flags byte as dkprintf, without retaining a reference over kprintf.
///
/// # Safety
/// The descriptor must be one of the aligned, lifetime-long C __verbose objects.
unsafe fn debug_enabled(descriptor: *const Ddebug) -> bool {
    // SAFETY: the caller supplies live C descriptor storage; the selected C/Rust
    // layout places the 24-bit line and high 8-bit flags at byte offset 24.
    unsafe { read_volatile(addr_of!((*descriptor).line_flags)) >> 24 != 0 }
}

/// Preserve the two address diagnostics and unknown-event silence.
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

/// Preserve initialization's direct diagnostics and independently gated chunk range.
#[no_mangle]
pub extern "C" fn x86_init_linux_log_bridge(
    event: CInt,
    a: CULong,
    b: CULong,
    c: CULong,
    d: CULong,
    _error: CInt,
) {
    // SAFETY: all strings are static and NUL terminated. Scalar varargs retain the
    // original widths, including the selected GCC unsigned-long-to-int truncation.
    unsafe {
        match event {
            1 => {
                kprintf(b"Straight-map entire physical memory\n\0".as_ptr().cast());
            }
            2 => {
                kprintf(
                    b"Linux kernel virtual: 0x%lx - 0x%lx -> 0x%lx - 0x%lx\n\0"
                        .as_ptr()
                        .cast(),
                    a,
                    b,
                    c,
                    d,
                );
            }
            3 => {
                kprintf(
                    b"%s: error setting mapping for 0x%lx\n\0".as_ptr().cast(),
                    b"init_linux_kernel_mapping\0".as_ptr().cast::<c_char>(),
                    a,
                );
            }
            4 => {
                kprintf(
                    b"Straight-map physical memory areas allocated to McKernel\n\0"
                        .as_ptr()
                        .cast(),
                );
            }
            5 => {
                kprintf(
                    b"%s: ERROR: No memory chunk available.\n\0".as_ptr().cast(),
                    b"init_linux_kernel_mapping\0".as_ptr().cast::<c_char>(),
                );
            }
            6 => {
                kprintf(
                    b"%s: ERROR: Memory chunk id (%d) out of range.\n\0".as_ptr().cast(),
                    b"init_linux_kernel_mapping\0".as_ptr().cast::<c_char>(),
                    a as CInt,
                );
            }
            7 if debug_enabled(addr_of!(x86_init_linux_log_chunk_range_debug)) => {
                kprintf(
                    b"Linux kernel virtual: 0x%lx - 0x%lx -> 0x%lx - 0x%lx\n\0"
                        .as_ptr()
                        .cast(),
                    a,
                    b,
                    c,
                    d,
                );
            }
            8 => {
                kprintf(
                    b"%s: set_pt_large_page() failed for 0x%lx\n\0".as_ptr().cast(),
                    b"init_linux_kernel_mapping\0".as_ptr().cast::<c_char>(),
                    a,
                );
            }
            _ => {}
        }
    }
}

/// Preserve the gated mapping diagnostic, including wrapping and pointer varargs.
#[no_mangle]
pub extern "C" fn x86_map_fixed_area_log_bridge(phys: CULong, size: CULong, virt: CULong) {
    // SAFETY: descriptor storage and the format are live static data. The pointer
    // is passed only as a value, matching the original void* vararg to %lx.
    unsafe {
        if debug_enabled(addr_of!(x86_map_fixed_area_log_debug)) {
            let pages = ((phys & (PAGE_SIZE - 1))
                .wrapping_add(size)
                .wrapping_add(PAGE_SIZE - 1)
                >> PAGE_SHIFT) as CInt;
            kprintf(
                b"map_fixed: phys: 0x%lx => 0x%lx (%d pages)\n\0".as_ptr().cast(),
                phys & PAGE_MASK,
                virt as *mut c_void,
                pages,
            );
        }
    }
}

/// Preserve user-copy's event order, debug gates and original C vararg conversions.
#[no_mangle]
pub extern "C" fn x86_user_copy_log_bridge(
    event: CInt,
    vm: *mut c_void,
    a: CULong,
    b: CULong,
    error: CInt,
) {
    // SAFETY: formats are static; pointer varargs are never dereferenced. Each
    // integer is passed at its original promoted C width, including negative
    // error's unsigned-long conversion in PATCH_START and both PATCH_DONE zeros.
    unsafe {
        match event {
            1 => {
                kprintf(
                    b"x86_user_copy(%p): error: out of user range addr=%lx size=%lx\n\0"
                        .as_ptr()
                        .cast(),
                    vm,
                    a,
                    b,
                );
            }
            2 => {
                kprintf(
                    b"x86_user_copy(%p): error: PF for %p failed: %d\n\0".as_ptr().cast(),
                    vm,
                    a as *mut c_void,
                    error,
                );
            }
            3 => {
                kprintf(
                    b"x86_user_copy(%p): error: resolving physical address of %p: %d\n\0"
                        .as_ptr()
                        .cast(),
                    vm,
                    a as *mut c_void,
                    error,
                );
            }
            4 if debug_enabled(addr_of!(x86_user_copy_log_external_debug)) => {
                kprintf(
                    b"x86_user_copy(%p): pa is outside of LWK memory, pa: %p, cpsize: %lu\n\0"
                        .as_ptr()
                        .cast(),
                    vm,
                    a as *mut c_void,
                    b,
                );
            }
            5 if debug_enabled(addr_of!(x86_user_copy_log_patch_start_debug)) => {
                kprintf(
                    b"patch_process_vm(%p,%p,%p,%lx)\n\0".as_ptr().cast(),
                    vm,
                    a as *mut c_void,
                    b as *mut c_void,
                    error as CULong,
                );
            }
            6 => {
                kprintf(
                    b"patch_process_vm(%p,%p,%p,%lx):not in user\n\0".as_ptr().cast(),
                    vm,
                    a as *mut c_void,
                    null_mut::<c_void>(),
                    b,
                );
            }
            7 => {
                kprintf(
                    b"patch_process_vm(%p):pf(%lx):%d\n\0".as_ptr().cast(),
                    vm,
                    a,
                    error,
                );
            }
            8 => {
                kprintf(
                    b"patch_process_vm(%p):v2p(%p):%d\n\0".as_ptr().cast(),
                    vm,
                    a as *mut c_void,
                    error,
                );
            }
            9 if debug_enabled(addr_of!(x86_user_copy_log_patch_done_debug)) => {
                kprintf(
                    b"patch_process_vm(%p,%p,%p,%lx):%d\n\0".as_ptr().cast(),
                    vm,
                    a as *mut c_void,
                    b as *mut c_void,
                    0 as CULong,
                    0 as CInt,
                );
            }
            _ => {}
        }
    }
}
