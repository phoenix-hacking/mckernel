//! Fixed-arity memory initialization diagnostics formerly implemented in memory.c.
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

use core::ffi::{c_char, c_void};

use crate::abi::{CInt, CULong};

unsafe extern "C" {
    fn kprintf(format: *const c_char, ...) -> CInt;
}

/// Preserve the memory-initialization integer logger's event and promoted-int ABI.
#[no_mangle]
pub extern "C" fn x86_mem_log_int_bridge(event: CInt, value: CInt) {
    if event == 1 {
        // SAFETY: static NUL-terminated format; value has the exact promoted-int width.
        unsafe { kprintf(b"use_1gb_page: %d\n\0".as_ptr().cast(), value) };
    }
}

/// Preserve the allocator-initialization failure messages and unknown-event no-op.
#[no_mangle]
pub extern "C" fn x86_mem_log_bridge(event: CInt) {
    let function = match event {
        1 => b"ihk_mc_allocate\0".as_ptr(),
        2 => b"ihk_mc_free\0".as_ptr(),
        _ => return,
    };
    // SAFETY: both the format and selected %s argument are static NUL-terminated bytes.
    unsafe {
        kprintf(
            b"%s: error, kmalloc not yet initialized\n\0".as_ptr().cast(),
            function.cast::<c_char>(),
        )
    };
}

/// Preserve normal-area initialization's existing format and vararg types.
#[no_mangle]
pub extern "C" fn x86_init_normal_log_bridge(event: CInt, a: CULong, b: CULong, c: CULong) {
    // SAFETY: formats and %s data are static; scalars retain C widths. The original
    // passes c as void* to %lx, so retain that pointer vararg without dereferencing it.
    unsafe {
        match event {
            1 => {
                kprintf(
                    b"map_start = %lx, map_end = %lx, virt %lx\n\0".as_ptr().cast(),
                    a,
                    b,
                    c as *mut c_void,
                );
            }
            2 => {
                kprintf(
                    b"%s: error setting mapping for 0x%lx\n\0".as_ptr().cast(),
                    b"init_normal_area\0".as_ptr().cast::<c_char>(),
                    a,
                );
            }
            _ => {}
        }
    }
}

/// Preserve text mapping's int truncation and unused-argument behavior.
#[no_mangle]
pub extern "C" fn x86_init_text_log_bridge(event: CInt, a: CULong, _b: CULong, _c: CULong) {
    // SAFETY: static formats and scalar varargs. The cast reproduces the selected
    // GCC x86_64 unsigned-long-to-int truncation before the original %d call.
    unsafe {
        match event {
            1 => {
                kprintf(b"TEXT: # of large pages = %d\n\0".as_ptr().cast(), a as CInt);
            }
            2 => {
                kprintf(b"TEXT: Base address = %lx\n\0".as_ptr().cast(), a);
            }
            _ => {}
        }
    }
}

/// Preserve the page-table location diagnostic without reading the pointed-to table.
#[no_mangle]
pub extern "C" fn x86_init_page_table_log_bridge(event: CInt, pt: *mut c_void) {
    if event == 1 {
        // SAFETY: static format; the original pointer vararg is passed as a value only.
        unsafe { kprintf(b"Page table is now at 0x%lx\n\0".as_ptr().cast(), pt) };
    }
}
