#[no_mangle]
pub unsafe extern "C" fn syscall_atomic64_read_bridge(
    value: *mut c_void,
) -> CLong {
    // SAFETY: Same original actual provider and precise ABI inputs/effects.
    unsafe {
        crate::atomic_helpers::ihk_atomic64_read(value.cast())
    }
}
