//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Private uncompiled successor for the existing settid warning callback.

use super::{kprintf, CInt};

/// Preserve the existing `void (*)(int)` callback and one warning per call.
#[no_mangle]
pub(super) extern "C" fn syscall_settid_log_bridge(ret: CInt) {
    // SAFETY: the static C string is NUL-terminated and contains exactly one %d;
    // CInt is the existing i32 C int ABI, so ret has the required variadic int
    // promotion/type. No borrowed or mutable data crosses this call. kprintf is
    // the same synchronous kernel logger used by the original C callback.
    unsafe {
        kprintf(c"settid: WARNING: do_syscall returns %d\n".as_ptr().cast(), ret);
    }
}
