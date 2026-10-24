
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
