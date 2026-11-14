#![no_std]
use abi::{CInt,CULong,X86UserContext,X86BasicRegs};
#[path="actual_abi.rs"] mod abi;
type X86ContextLogFn=unsafe extern "C" fn(CInt,CULong,CULong,CULong,CULong);
type X86KprintfLockFn=unsafe extern "C" fn()->CULong;
type X86KprintfUnlockFn=unsafe extern "C" fn(CULong);
const EINVAL:CInt=22;
extern "C" {
 fn kprintf(format:*const i8,...) -> CInt;
 fn __kprintf(format:*const i8,...) -> CInt;
}
/// Preserve complete context diagnostics using the existing Rust print providers.
/// The caller owns any outer print lock. Events 1..6 use __kprintf without
/// acquiring that lock again; 20..22 retain the original kprintf calls. All
/// arguments are integer values, no context pointer or callback is retained.
#[no_mangle]
pub unsafe extern "C" fn x86_context_line_log_bridge(
    event: CInt, a: CULong, b: CULong, c: CULong, d: CULong,
) {
    match event {
        1 => unsafe {
            __kprintf(b"CS:RIP = %4lx:%16lx\n\0".as_ptr().cast(), a, b);
        },
        2 => unsafe {
            __kprintf(b"             RAX              RBX              RCX              RDX\n\0".as_ptr().cast());
            __kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        3 => unsafe {
            __kprintf(b"             RSI              RDI              RSP              RBP\n\0".as_ptr().cast());
            __kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        4 => unsafe {
            __kprintf(b"              R8               R9              R10              R11\n\0".as_ptr().cast());
            __kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        5 => unsafe {
            __kprintf(b"             R12              R13              R14              R15\n\0".as_ptr().cast());
            __kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        6 => unsafe {
            __kprintf(b"              CS               SS           RFLAGS            ERROR\n\0".as_ptr().cast());
            __kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        20 => unsafe {
            kprintf(b"CS:RIP = %04lx:%16lx\n\0".as_ptr().cast(), a, b);
        },
        21 => unsafe {
            kprintf(b"%16lx %16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c, d);
        },
        22 => unsafe {
            kprintf(b"%16lx %16lx %16lx\n\0".as_ptr().cast(), a, b, c);
        },
        _ => {},
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_print_user_context_body_result(
    uctx: *const X86UserContext,
    log_fn: Option<X86ContextLogFn>,
) -> CInt {
    if uctx.is_null() {
        return -EINVAL;
    }
    let Some(log) = log_fn else {
        return -EINVAL;
    };

    unsafe {
        let regs = &(*uctx).gpr;
        log(20, regs.cs, regs.rip, 0, 0);
        log(21, regs.rax, regs.rbx, regs.rcx, regs.rdx);
        log(22, regs.rsi, regs.rdi, regs.rsp, 0);
    }
    0
}
#[no_mangle]
pub unsafe extern "C" fn x86_arch_show_interrupt_context_body_result(
    uctx: *const X86UserContext,
    lock_fn: Option<X86KprintfLockFn>,
    unlock_fn: Option<X86KprintfUnlockFn>,
    log_fn: Option<X86ContextLogFn>,
) -> CInt {
    if uctx.is_null() {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock), Some(log)) = (lock_fn, unlock_fn, log_fn) else {
        return -EINVAL;
    };

    unsafe {
        let flags = lock();
        let regs = &(*uctx).gpr;
        log(1, regs.cs, regs.rip, 0, 0);
        log(2, regs.rax, regs.rbx, regs.rcx, regs.rdx);
        log(3, regs.rsi, regs.rdi, regs.rsp, regs.rbp);
        log(4, regs.r8, regs.r9, regs.r10, regs.r11);
        log(5, regs.r12, regs.r13, regs.r14, regs.r15);
        log(6, regs.cs, regs.ss, regs.rflags, regs.orig_rax);
        unlock(flags);
    }
    0
}
// Fixture-only construction from real ABI types, not a model of their layout.
#[no_mangle]
pub unsafe extern "C" fn fixture_run_context(
    which:CInt, values:*const CULong, log:Option<X86ContextLogFn>,
    lock:Option<X86KprintfLockFn>, unlock:Option<X86KprintfUnlockFn>,
)->CInt {
 let mut ctx:X86UserContext=unsafe{core::mem::zeroed()};
 macro_rules! v {($n:expr)=>{unsafe{*values.add($n)}}}
 ctx.gpr=X86BasicRegs{
 r15:v!(0),r14:v!(1),r13:v!(2),r12:v!(3),rbp:v!(4),rbx:v!(5),
 r11:v!(6),r10:v!(7),r9:v!(8),r8:v!(9),rax:v!(10),rcx:v!(11),
 rdx:v!(12),rsi:v!(13),rdi:v!(14),orig_rax:v!(15),rip:v!(16),
 cs:v!(17),rflags:v!(18),rsp:v!(19),ss:v!(20)};
 if which==0 {unsafe{x86_print_user_context_body_result(&ctx,log)}}
 else {unsafe{x86_arch_show_interrupt_context_body_result(&ctx,lock,unlock,log)}}
}
