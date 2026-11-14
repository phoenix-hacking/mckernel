use crate::abi::{CInt,CULong,X86UserContext};
use core::ptr::{read_volatile,write_volatile};

pub unsafe extern "C" fn ihk_mc_syscall_arg0(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 0) }
}

pub unsafe extern "C" fn ihk_mc_syscall_arg1(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 1) }
}

pub unsafe extern "C" fn ihk_mc_syscall_arg2(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 2) }
}

pub unsafe extern "C" fn ihk_mc_syscall_arg3(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 3) }
}

pub unsafe extern "C" fn ihk_mc_syscall_arg4(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 4) }
}

pub unsafe extern "C" fn ihk_mc_syscall_arg5(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 5) }
}

pub unsafe extern "C" fn ihk_mc_syscall_set_arg0(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 0, value) }
}

pub unsafe extern "C" fn ihk_mc_syscall_set_arg1(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 1, value) }
}

pub unsafe extern "C" fn ihk_mc_syscall_set_arg2(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 2, value) }
}

pub unsafe extern "C" fn ihk_mc_syscall_set_arg3(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 3, value) }
}

pub unsafe extern "C" fn ihk_mc_syscall_set_arg4(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 4, value) }
}

pub unsafe extern "C" fn ihk_mc_syscall_set_arg5(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 5, value) }
}

unsafe fn x86_syscall_read(uctx: *const X86UserContext, selector: CInt) -> CULong {
    if uctx.is_null() {
        return 0;
    }

    unsafe {
        match selector {
            0 => read_volatile(&(*uctx).gpr.rdi),
            1 => read_volatile(&(*uctx).gpr.rsi),
            2 => read_volatile(&(*uctx).gpr.rdx),
            3 => read_volatile(&(*uctx).gpr.r10),
            4 => read_volatile(&(*uctx).gpr.r8),
            5 => read_volatile(&(*uctx).gpr.r9),
            6 => read_volatile(&(*uctx).gpr.rax),
            7 => read_volatile(&(*uctx).gpr.orig_rax),
            8 => read_volatile(&(*uctx).gpr.rip),
            9 => read_volatile(&(*uctx).gpr.rsp),
            _ => 0,
        }
    }
}

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

