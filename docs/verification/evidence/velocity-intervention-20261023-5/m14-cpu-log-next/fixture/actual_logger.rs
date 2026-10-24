#![no_std]
use core::ffi::c_void;
#[path="actual_abi.rs"] mod abi;
use abi::{CInt,CULong};
extern "C" { fn kprintf(format:*const i8, ...) -> CInt; }

/// Preserve the existing three unsigned-long CPU diagnostics through Rust kprintf.
/// Values are forwarded by value; case 15 is a pointer-format argument only and
/// is never dereferenced. Unknown events perform no call; kprintf results remain
/// ignored exactly as in the C callback.
#[no_mangle]
pub unsafe extern "C" fn x86_cpu_ulong_log_bridge(event: CInt, value: CULong) {
    match event {
        1 => unsafe {
            kprintf(b"Trampoline area: 0x%lx \n\0".as_ptr().cast(), value);
        },
        2 => unsafe {
            kprintf(b"# of cpus : %lu\n\0".as_ptr().cast(), value);
        },
        15 => unsafe {
            kprintf(
                b"arch_save_panic_regs: in user-space: %p\n\0".as_ptr().cast(),
                value as *mut c_void,
            );
        },
        _ => {},
    }
}
