
/// Preserve the complete selected stack-frame diagnostic. All three values are
/// passed by value to the existing Rust variadic logger; none is dereferenced.
/// The outer caller's lock span is unchanged and the logger result is ignored.
#[no_mangle]
pub unsafe extern "C" fn x86_stack_frame_log_bridge(
    ip: CULong, sp: CULong, fp: CULong,
) {
    unsafe {
        kprintf(b"IP: %016lx, SP: %016lx, FP: %016lx\n\0".as_ptr().cast(), ip, sp, fp);
    }
}

/// Forward the same caller-owned frame and first IP to the already accepted
/// Rust stack formatter. The frame is neither read here nor retained. The
/// formatter's existing live-frame precondition and native-walk gap remain.
#[no_mangle]
pub unsafe extern "C" fn x86_print_stack_bridge(rbp: *mut c_void, first: CULong) {
    unsafe { __print_stack(rbp.cast::<CULong>(), first); }
}
