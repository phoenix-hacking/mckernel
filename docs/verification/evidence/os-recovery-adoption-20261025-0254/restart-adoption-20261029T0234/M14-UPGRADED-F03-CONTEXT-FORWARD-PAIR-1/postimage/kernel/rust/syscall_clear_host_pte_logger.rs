//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Private same-name successor for the clear_host_pte diagnostic callback.

use super::{kprintf, CLong};

/// Existing `void (*)(long)` callback; body-level nonzero gating stays upstream.
#[no_mangle]
pub(super) extern "C" fn clear_host_pte_log_bridge(error: CLong) {
    // SAFETY: the immutable NUL-terminated format contains one %ld. CLong is
    // the existing signed i64 C long ABI on the selected 64-bit compute target;
    // error is passed unchanged as that exact variadic type. No pointer payload,
    // allocation, retained reference or mutable logger state crosses this call.
    unsafe {
        kprintf(c"clear_host_pte failed. %ld\n".as_ptr().cast(), error);
    }
}
