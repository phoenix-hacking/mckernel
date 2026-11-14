// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::c_int;

// Same existing C provider used by the scoped Rust exit helpers. This is a
// declaration only; it does not replace or claim the terminate implementation.
unsafe extern "C" {
    fn terminate(status: c_int, group: c_int);
}

/// Forward the exit-group callback to its existing termination provider.
///
/// # Safety
/// The caller must meet the same execution-context and lifetime requirements
/// as the original C callback and the existing terminate provider.
#[no_mangle]
pub unsafe extern "C" fn exit_group_terminate_bridge(status: c_int, group: c_int) {
    // SAFETY: The original callback forwards these exact C int arguments once
    // to the existing void provider and does not assume it cannot return.
    unsafe { terminate(status, group) };
}
