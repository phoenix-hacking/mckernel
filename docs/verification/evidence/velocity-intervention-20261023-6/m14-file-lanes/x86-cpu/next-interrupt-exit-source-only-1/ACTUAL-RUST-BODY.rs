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
