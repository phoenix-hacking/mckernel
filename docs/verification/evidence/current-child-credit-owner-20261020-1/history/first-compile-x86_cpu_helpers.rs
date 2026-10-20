pub unsafe extern "C" fn cpu_pause() {
    core::arch::asm!("pause", options(nomem, nostack, preserves_flags));
}