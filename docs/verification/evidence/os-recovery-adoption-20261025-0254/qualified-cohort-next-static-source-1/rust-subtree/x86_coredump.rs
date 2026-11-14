use core::ffi::c_void;

use crate::abi::{CInt, CULong, ElfPrstatus64, Thread, X86UserContext};

const MSR_FS_BASE: u32 = 0xc000_0100;
const MSR_GS_BASE: u32 = 0xc000_0101;

#[inline(always)]
unsafe fn rdmsr(index: u32) -> CULong {
    let low: u32;
    let high: u32;

    core::arch::asm!(
        "rdmsr",
        in("ecx") index,
        out("eax") low,
        out("edx") high,
        options(nostack, preserves_flags)
    );

    ((high as CULong) << 32) | low as CULong
}

#[inline(always)]
unsafe fn read_r12() -> CULong {
    let value: CULong;

    core::arch::asm!("mov {}, r12", out(reg) value, options(nomem, nostack, preserves_flags));
    value
}

#[inline(always)]
unsafe fn read_r13() -> CULong {
    let value: CULong;

    core::arch::asm!("mov {}, r13", out(reg) value, options(nomem, nostack, preserves_flags));
    value
}

#[inline(always)]
unsafe fn read_r14() -> CULong {
    let value: CULong;

    core::arch::asm!("mov {}, r14", out(reg) value, options(nomem, nostack, preserves_flags));
    value
}

#[inline(always)]
unsafe fn read_r15() -> CULong {
    let value: CULong;

    core::arch::asm!("mov {}, r15", out(reg) value, options(nomem, nostack, preserves_flags));
    value
}

#[no_mangle]
pub unsafe extern "C" fn x86_coredump_fill_prstatus_body_result(
    prstatus: *mut ElfPrstatus64,
    thread: *mut Thread,
    regs0: *mut c_void,
    sig: CInt,
    r12: CULong,
    r13: CULong,
    r14: CULong,
    r15: CULong,
    fs_base: CULong,
    gs_base: CULong,
) {
    let uctx = regs0.cast::<X86UserContext>();
    let regs = core::ptr::addr_of!((*uctx).gpr);

    (*prstatus).pr_pid = (*thread).tid;
    if !(*(*thread).proc).parent.is_null() {
        (*prstatus).pr_ppid = (*(*(*thread).proc).parent).pid;
    }

    (*prstatus).pr_info.si_signo = sig;
    (*prstatus).pr_cursig = sig as i16;

    (*prstatus).pr_reg[0] = r15;
    (*prstatus).pr_reg[1] = r14;
    (*prstatus).pr_reg[2] = r13;
    (*prstatus).pr_reg[3] = r12;
    (*prstatus).pr_reg[4] = (*regs).rbp;
    (*prstatus).pr_reg[5] = (*regs).rbx;
    (*prstatus).pr_reg[6] = (*regs).r11;
    (*prstatus).pr_reg[7] = (*regs).r10;
    (*prstatus).pr_reg[8] = (*regs).r9;
    (*prstatus).pr_reg[9] = (*regs).r8;
    (*prstatus).pr_reg[10] = (*regs).rax;
    (*prstatus).pr_reg[11] = (*regs).rcx;
    (*prstatus).pr_reg[12] = (*regs).rdx;
    (*prstatus).pr_reg[13] = (*regs).rsi;
    (*prstatus).pr_reg[14] = (*regs).rdi;
    (*prstatus).pr_reg[15] = (*regs).rax;
    (*prstatus).pr_reg[16] = (*regs).rip;
    (*prstatus).pr_reg[17] = (*regs).cs;
    (*prstatus).pr_reg[18] = (*regs).rflags;
    (*prstatus).pr_reg[19] = (*regs).rsp;
    (*prstatus).pr_reg[20] = (*regs).ss;
    (*prstatus).pr_reg[21] = fs_base;
    (*prstatus).pr_reg[22] = gs_base;
    (*prstatus).pr_fpvalid = 0;
}

#[no_mangle]
pub unsafe extern "C" fn arch_fill_prstatus(
    prstatus: *mut ElfPrstatus64,
    thread: *mut Thread,
    regs0: *mut c_void,
    sig: CInt,
) {
    x86_coredump_fill_prstatus_body_result(
        prstatus,
        thread,
        regs0,
        sig,
        read_r12(),
        read_r13(),
        read_r14(),
        read_r15(),
        rdmsr(MSR_FS_BASE),
        rdmsr(MSR_GS_BASE),
    );
}

#[no_mangle]
pub unsafe extern "C" fn arch_fill_thread_core_info(
    _head: *mut c_void,
    _thread: *mut Thread,
    _regs: *mut c_void,
) {
}

#[no_mangle]
pub extern "C" fn arch_get_thread_core_info_size() -> CInt {
    0
}
