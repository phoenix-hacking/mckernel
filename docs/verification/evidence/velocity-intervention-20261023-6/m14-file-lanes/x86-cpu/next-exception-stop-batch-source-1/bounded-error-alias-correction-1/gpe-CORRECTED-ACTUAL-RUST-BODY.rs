// Exact kernel/include/syscall.h enum values and x86 signal.h SIGSEGV.
// The supported GCC enum transport is checked by the real-header witness.
const X86_GPE_CPUTIME_K2U: CUInt = 0;
const X86_GPE_CPUTIME_U2K: CUInt = 1;
const X86_GPE_CPUTIME_K2K_IN: CUInt = 2;
const X86_GPE_CPUTIME_K2K_OUT: CUInt = 3;
const X86_GPE_SIGSEGV: CInt = 11;

/// Complete selected general-protection-fault orchestration.
///
/// The interrupt producer owns the same live context for this call. No Rust
/// reference crosses a provider call: CS is reloaded after context display,
/// and the existing classifier is called again after interrupt_exit. The
/// actual selected Rust panic provider does not return; no new recovery path,
/// pointer retention, lock, IRQ operation or signal ownership is introduced.
#[no_mangle]
pub unsafe extern "C" fn gpe_handler(regs: *mut X86UserContext) {
    unsafe {
        x86_gpe_set_cputime(if x86_gpe_from_user(regs.cast::<c_void>()) != 0 {
            X86_GPE_CPUTIME_U2K
        } else {
            X86_GPE_CPUTIME_K2K_IN
        });
        kprintf(
            b"General protection fault (err: %lx, %lx:%lx)\n\0".as_ptr().cast(),
            core::ptr::addr_of!((*regs).gpr.orig_rax).read(),
            core::ptr::addr_of!((*regs).gpr.cs).read(),
            core::ptr::addr_of!((*regs).gpr.rip).read(),
        );
        x86_gpe_show_context(regs.cast::<c_void>());
        if (core::ptr::addr_of!((*regs).gpr.cs).read() & 3) == 0 {
            x86_gpe_panic(b"gpe_handler\0".as_ptr().cast());
        }
        x86_gpe_set_signal(
            X86_GPE_SIGSEGV, regs.cast::<c_void>(), core::ptr::null_mut(),
        );
        x86_gpe_interrupt_exit(regs);
        x86_gpe_set_cputime(if x86_gpe_from_user(regs.cast::<c_void>()) != 0 {
            X86_GPE_CPUTIME_K2U
        } else {
            X86_GPE_CPUTIME_K2K_OUT
        });
        x86_gpe_panic(b"GPF\0".as_ptr().cast());
    }
}
