// Exact existing syscall.h/registers.h/x86 signal.h constants.
// The future real-header witness must confirm each value and enum transport.
const X86_DEBUG_CPUTIME_K2U: CUInt = 0;
const X86_DEBUG_CPUTIME_U2K: CUInt = 1;
const X86_DEBUG_CPUTIME_K2K_IN: CUInt = 2;
const X86_DEBUG_CPUTIME_K2K_OUT: CUInt = 3;
const X86_DEBUG_DB6_BS: CULong = 1 << 14;
const X86_DEBUG_DB6_BREAKPOINT_MASK: CULong = 0xf;
const X86_DEBUG_RFLAGS_TF: CULong = 1 << 8;
const X86_DEBUG_SIGTRAP: CInt = 5;
const X86_DEBUG_TRAP_TRACE: CInt = 2;
const X86_DEBUG_TRAP_HWBKPT: CInt = 4;

/// Complete debug-exception orchestration. The generic reader is the existing
/// privileged debug-register boundary, not a new C getter or public helper.
/// The caller retains the original live frame and CPU-local debug-state
/// exclusion. No frame or stack-local signal-info pointer escapes.
#[inline(always)]
unsafe fn x86_debug_handler_body<R: DebugRegisterReader>(
    regs: *mut X86UserContext,
    reader: &mut R,
) {
    let mut info = core::mem::MaybeUninit::<crate::abi::SigInfo>::uninit();
    let mut si_code: CInt = 0;
    unsafe {
        x86_debug_set_cputime(if x86_debug_from_user(regs.cast::<c_void>()) != 0 {
            X86_DEBUG_CPUTIME_U2K
        } else {
            X86_DEBUG_CPUTIME_K2K_IN
        });
        if X86_DEBUG_HANDLER_DEBUG_PRINT_ENABLED != 0 {
            kprintf(
                b"debug exception (err: %lx, %lx:%lx)\n\0".as_ptr().cast(),
                core::ptr::addr_of!((*regs).gpr.error).read(),
                core::ptr::addr_of!((*regs).gpr.cs).read(),
                core::ptr::addr_of!((*regs).gpr.rip).read(),
            );
            x86_debug_show_context(regs.cast::<c_void>());
        }
        // Reuse the exact existing DR6 instruction/provider; only register6
        // is requested, once, after the optional context callback.
        let db6 = reader.read::<6>();
        if db6 & X86_DEBUG_DB6_BS != 0 {
            let flags = core::ptr::addr_of_mut!((*regs).gpr.rflags);
            flags.write(flags.read() & !X86_DEBUG_RFLAGS_TF);
            si_code = X86_DEBUG_TRAP_TRACE;
        } else if db6 & X86_DEBUG_DB6_BREAKPOINT_MASK != 0 {
            si_code = X86_DEBUG_TRAP_HWBKPT;
        }
        core::ptr::write_bytes(
            info.as_mut_ptr().cast::<u8>(), 0, core::mem::size_of::<crate::abi::SigInfo>(),
        );
        core::ptr::addr_of_mut!((*info.as_mut_ptr()).si_code).write(si_code);
        x86_debug_set_signal(X86_DEBUG_SIGTRAP, regs.cast::<c_void>(), info.as_mut_ptr());
        x86_debug_interrupt_exit(regs);
        x86_debug_set_cputime(if x86_debug_from_user(regs.cast::<c_void>()) != 0 {
            X86_DEBUG_CPUTIME_K2U
        } else {
            X86_DEBUG_CPUTIME_K2K_OUT
        });
    }
}

#[no_mangle]
pub unsafe extern "C" fn debug_handler(regs: *mut X86UserContext) {
    unsafe { x86_debug_handler_body(regs, &mut HardwareDebugRegisterReader); }
}
