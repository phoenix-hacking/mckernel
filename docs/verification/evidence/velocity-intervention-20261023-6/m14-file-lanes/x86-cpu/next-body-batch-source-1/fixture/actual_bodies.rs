#![no_std]
use core::ffi::c_void;
use core::ptr::{addr_of,read_volatile};
#[path="actual_abi.rs"] mod abi;
use abi::{CInt,CULong,X86UserContext};
extern "C" {
 #[link_name="fixture_stack_snprintf"]
 fn snprintf(buf:*mut i8,size:usize,format:*const i8,...)->CInt;
 #[link_name="fixture_stack_print"]
 fn __kprintf(format:*const i8,...)->CInt;
 fn fixture_nmi_capture_flags()->CULong;
     // Existing providers; the Rust-local alias adds no exported C helper.
    fn interrupt_from_user(regs: *mut c_void) -> CInt;
    #[link_name = "cpu_enable_interrupt"]
    fn x86_interrupt_exit_enable_interrupt();
    fn check_sig_pending();
    fn check_need_resched();
    fn check_signal(rc: CULong, regs: *mut c_void, num: CInt);
}



/// Build the existing single addr2line stack diagnostic with existing Rust
/// snprintf and unlocked-print providers. The caller supplies the same live
/// two-word C stack frames; no frame/context or local-buffer pointer is retained.
/// Frame reads stay separated by snprintf as in C so a provider may affect the
/// next-link word before that word is read.
#[no_mangle]
pub unsafe extern "C" fn __print_stack(mut rbp: *mut CULong, first: CULong) {
    // Exact existing C STACK_BUF_LEN: 1024-sizeof("[  0]: ").
    const BUF_LEN: usize = 1024 - b"[  0]: \0".len();
    let mut buf = [0i8; BUF_LEN];
    let out = buf.as_mut_ptr();
    let mut len = unsafe {
        snprintf(
            out, BUF_LEN,
            b"addr2line -e smp-x86/kernel/mckernel.img -fpia\0".as_ptr().cast(),
        )
    } as usize;
    if first != 0 {
        len = len.wrapping_add(unsafe {
            snprintf(
                out.wrapping_add(len), BUF_LEN.wrapping_sub(len),
                b" %#16lx\0".as_ptr().cast(), first,
            )
        } as usize);
    }
    while (rbp as CULong) > 0xffff880000000000
        && BUF_LEN.wrapping_sub(len) > b" 0x0123456789abcdef\0".len()
    {
        let ip = unsafe { rbp.add(1).read() };
        len = len.wrapping_add(unsafe {
            snprintf(
                out.wrapping_add(len), BUF_LEN.wrapping_sub(len),
                b" %#16lx\0".as_ptr().cast(), ip,
            )
        } as usize);
        rbp = unsafe { rbp.read() } as *mut CULong;
    }
    unsafe { __kprintf(b"%s\n\0".as_ptr().cast(), out); }
}


/// Preserve the complete existing NMI frame rewrite. The caller owns a live,
/// aligned writable span of at least 27 C unsigned-long words. This forward
/// overlapping copy and the final five fields exactly match the C producer;
/// the supplied function is stored as a return address and is never invoked.
#[no_mangle]
pub unsafe extern "C" fn mod_nmi_ctx(
    nmi_ctx: *mut c_void,
    func: Option<unsafe extern "C" fn()>,
) {
    let flags: CULong;
    // Same pushfq/pop read used by existing cpu_interrupt_disabled. Default
    // memory/flags clobbers retain the original C "memory","cc" barrier.
    unsafe { core::arch::asm!("pushfq", "pop {flags}", flags = lateout(reg) flags); }
    let words = nmi_ctx.cast::<CULong>();
    let mut i = 0usize;
    while i < 22 {
        let value = unsafe { words.add(i + 5).read() };
        unsafe { words.add(i).write(value); }
        i += 1;
    }
    let return_address = func.map_or(0, |entry| entry as CULong);
    unsafe {
        words.add(22).write(return_address);
        words.add(23).write(0x20);
        // Actual registers.h RFLAGS_IF=(1<<9); same mask is already used by
        // existing Rust cpu_interrupt_disabled. No IRQ state is changed here.
        words.add(24).write(flags & !(1 << 9));
        words.add(25).write(words.add(27) as CULong);
        words.add(26).write(0x28);
    }
}

/// Complete interrupt-return orchestration for the caller-owned context.
///
/// The classifier and callbacks retain their original contract. In particular,
/// interrupt enable precedes pending-signal and reschedule handling. No context
/// pointer or callback state is retained, and no new null/error policy is added.
#[no_mangle]
pub unsafe extern "C" fn interrupt_exit(regs: *mut X86UserContext) {
    unsafe {
        if interrupt_from_user(regs.cast::<c_void>()) != 0 {
            x86_interrupt_exit_enable_interrupt();
            check_sig_pending();
            check_need_resched();
            check_signal(0, regs.cast::<c_void>(), -1);
        }
    }
}

/// Preserve the complete existing NMI frame rewrite. The caller owns a live,
/// aligned writable span of at least 27 C unsigned-long words. This forward
/// overlapping copy and the final five fields exactly match the C producer;
/// the supplied function is stored as a return address and is never invoked.
#[no_mangle]
pub unsafe extern "C" fn rust_mod_nmi_pure(
    nmi_ctx: *mut c_void,
    func: Option<unsafe extern "C" fn()>,
) {
    let flags: CULong;
    // Same pushfq/pop read used by existing cpu_interrupt_disabled. Default
    // memory/flags clobbers retain the original C "memory","cc" barrier.
    flags = unsafe { fixture_nmi_capture_flags() };
    let words = nmi_ctx.cast::<CULong>();
    let mut i = 0usize;
    while i < 22 {
        let value = unsafe { words.add(i + 5).read() };
        unsafe { words.add(i).write(value); }
        i += 1;
    }
    let return_address = func.map_or(0, |entry| entry as CULong);
    unsafe {
        words.add(22).write(return_address);
        words.add(23).write(0x20);
        // Actual registers.h RFLAGS_IF=(1<<9); same mask is already used by
        // existing Rust cpu_interrupt_disabled. No IRQ state is changed here.
        words.add(24).write(flags & !(1 << 9));
        words.add(25).write(words.add(27) as CULong);
        words.add(26).write(0x28);
    }
}

// This fixture-only data export uses real ABI types, never a 27-word model.
#[no_mangle]
pub static M14_RUST_NMI_HEADER_ABI:[usize;12]=[
 core::mem::size_of::<CULong>(),core::mem::align_of::<CULong>(),
 core::mem::size_of::<*mut c_void>(),core::mem::size_of::<Option<unsafe extern "C" fn()>>(),
 core::mem::size_of::<abi::X86BasicRegs>(),core::mem::offset_of!(abi::X86BasicRegs,rip),
 core::mem::offset_of!(abi::X86BasicRegs,cs),core::mem::offset_of!(abi::X86BasicRegs,rflags),
 core::mem::offset_of!(abi::X86BasicRegs,rsp),core::mem::offset_of!(abi::X86BasicRegs,ss),
 core::mem::size_of::<abi::X86UserContext>(),core::mem::offset_of!(abi::X86UserContext,gpr)];

#[no_mangle]
pub unsafe extern "C" fn actual_interrupt_classifier(regs0: *mut c_void) -> CInt {
    let regs = regs0.cast::<X86UserContext>();
    if (read_volatile(addr_of!((*regs).gpr.rsp)) & 0x8000_0000_0000_0000) == 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub static M14_RUST_BATCH_WORD_ABI:[usize;7]=[
 core::mem::size_of::<CInt>(),core::mem::size_of::<CULong>(),
 2*core::mem::size_of::<CULong>(),core::mem::align_of::<CULong>(),
 0,core::mem::size_of::<CULong>(),core::mem::size_of::<X86UserContext>()];
