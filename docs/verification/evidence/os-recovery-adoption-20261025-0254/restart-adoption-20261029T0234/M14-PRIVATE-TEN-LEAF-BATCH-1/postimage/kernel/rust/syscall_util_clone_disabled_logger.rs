//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Private source-only successor for the existing constant disabled-UTI logger.

use super::kprintf;

/// Existing no-argument void callback; one unchanged diagnostic per invocation.
#[no_mangle]
pub(super) extern "C" fn syscall_util_indicate_clone_disabled_bridge() {
    // SAFETY: both pointers refer to immutable static NUL-terminated C strings.
    // The format consumes exactly one %s; its sole variadic argument is the
    // matching const-char pointer. Neither storage can expire during kprintf.
    // The existing synchronous logger retains its CPU-prefix/output behavior.
    unsafe {
        kprintf(
            c"%s: error: --enable-uti mcexec option not specified\n".as_ptr().cast(),
            c"sys_util_indicate_clone".as_ptr().cast::<i8>(),
        );
    }
}
