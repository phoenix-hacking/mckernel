use crate::abi::CULong;
use core::ptr::read_volatile;
pub unsafe extern "C" fn cpu_pause() {
    core::arch::asm!("pause", options(nomem, nostack, preserves_flags));
}
pub unsafe extern "C" fn arch_barrier() {
    core::arch::asm!("", options(nostack, preserves_flags));
}
pub unsafe extern "C" fn smp_load_acquire_ulong(p: *const CULong) -> CULong {
    let value = unsafe { read_volatile(p) };
    unsafe { arch_barrier() };
    value
}
use crate::abi::{CInt,X86UserContext};
use core::ptr::write_volatile;

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

pub unsafe extern "C" fn ihk_mc_syscall_set_ret(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 6, value) }
}

pub unsafe fn cpu_interrupt_disabled()->i32{crate::phase5_tests::irq_disabled()}
