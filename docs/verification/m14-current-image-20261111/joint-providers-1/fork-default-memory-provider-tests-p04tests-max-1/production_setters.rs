// Exact unchanged production pure GPR setters; no IRQ/GS/hardware functions.
use crate::abi::{CInt, CULong, X86UserContext};
use core::ptr::write_volatile;

#[inline(always)]
unsafe fn x86_syscall_write(uctx: *mut X86UserContext, selector: CInt, value: CULong) {
    if uctx.is_null() {
        return;
    }

    unsafe {
        match selector {
            0 => write_volatile(&mut (*uctx).gpr.rdi, value),
            1 => write_volatile(&mut (*uctx).gpr.rsi, value),
            2 => write_volatile(&mut (*uctx).gpr.rdx, value),
            3 => write_volatile(&mut (*uctx).gpr.r10, value),
            4 => write_volatile(&mut (*uctx).gpr.r8, value),
            5 => write_volatile(&mut (*uctx).gpr.r9, value),
            6 => write_volatile(&mut (*uctx).gpr.rax, value),
            _ => {}
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_set_arg0(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 0, value) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_set_arg1(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 1, value) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_set_arg2(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 2, value) }
}
