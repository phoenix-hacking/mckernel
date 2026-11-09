unsafe extern "C" {
    // The exact existing CPU C dynamic-debug selector remains declarative data.
    static mut x86_interrupt_log_debug: crate::debug::Ddebug;
}

/// Preserve complete interrupt diagnostics and dynamic-debug argument evaluation.
/// Event1 always reports the supplied CPU; event2 obtains the current CPU only
/// after the original selector is enabled. The vector remains ignored, logger
/// results remain ignored, and no CPU/context pointer or lock is retained.
#[no_mangle]
pub unsafe extern "C" fn x86_interrupt_log_bridge(
    event: CInt, cpu: CInt, _vector: CInt,
) {
    match event {
        1 => unsafe {
            kprintf(
                b"%s: invalid CPU id: %d\n\0".as_ptr().cast(),
                b"ihk_mc_interrupt_cpu\0".as_ptr().cast::<i8>(), cpu,
            );
        },
        2 => unsafe {
            let flags = read_volatile(
                core::ptr::addr_of!(x86_interrupt_log_debug.line_flags),
            ) >> 24;
            if flags != 0 {
                let current = crate::x86_local::ihk_mc_get_processor_id();
                kprintf(
                    b"[%d] ihk_mc_interrupt_cpu: %d\n\0".as_ptr().cast(),
                    current, cpu,
                );
            }
        },
        _ => {},
    }
}
