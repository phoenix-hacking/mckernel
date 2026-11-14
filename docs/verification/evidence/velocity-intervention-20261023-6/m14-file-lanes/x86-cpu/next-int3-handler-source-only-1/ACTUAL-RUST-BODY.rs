// Exact existing syscall.h and x86 signal.h constants; real-header witness
// must confirm the supported unsigned32-bit enum transport before acceptance.
const X86_INT3_CPUTIME_K2U: CUInt = 0;
const X86_INT3_CPUTIME_U2K: CUInt = 1;
const X86_INT3_CPUTIME_K2K_IN: CUInt = 2;
const X86_INT3_CPUTIME_K2K_OUT: CUInt = 3;
const X86_INT3_SIGTRAP: CInt = 5;
const X86_INT3_TRAP_BRKPT: CInt = 1;

/// Complete breakpoint-exception orchestration using existing selected providers.
///
/// C owns the live interrupt context. The stack-local real SigInfo storage is
/// zeroed byte-for-byte (including padding) and borrowed only for set_signal.
/// No Rust reference crosses a provider, no frame/signal pointer is retained,
/// and the second classification is performed after interrupt_exit as in C.
#[no_mangle]
pub unsafe extern "C" fn int3_handler(regs: *mut X86UserContext) {
    let mut info = core::mem::MaybeUninit::<crate::abi::SigInfo>::uninit();
    unsafe {
        x86_int3_set_cputime(if x86_int3_from_user(regs.cast::<c_void>()) != 0 {
            X86_INT3_CPUTIME_U2K
        } else {
            X86_INT3_CPUTIME_K2K_IN
        });
        // #ifdef DEBUG_PRINT_CPU, including a definition with value 0, is
        // captured by the immutable data from the actual C translation unit.
        if X86_INT3_DEBUG_PRINT_ENABLED != 0 {
            kprintf(
                b"int3 exception (err: %lx, %lx:%lx)\n\0".as_ptr().cast(),
                core::ptr::addr_of!((*regs).gpr.error).read(),
                core::ptr::addr_of!((*regs).gpr.cs).read(),
                core::ptr::addr_of!((*regs).gpr.rip).read(),
            );
            x86_int3_show_context(regs.cast::<c_void>());
        }
        core::ptr::write_bytes(
            info.as_mut_ptr().cast::<u8>(), 0, core::mem::size_of::<crate::abi::SigInfo>(),
        );
        core::ptr::addr_of_mut!((*info.as_mut_ptr()).si_code).write(X86_INT3_TRAP_BRKPT);
        x86_int3_set_signal(X86_INT3_SIGTRAP, regs.cast::<c_void>(), info.as_mut_ptr());
        x86_int3_interrupt_exit(regs);
        x86_int3_set_cputime(if x86_int3_from_user(regs.cast::<c_void>()) != 0 {
            X86_INT3_CPUTIME_K2U
        } else {
            X86_INT3_CPUTIME_K2K_OUT
        });
    }
}
