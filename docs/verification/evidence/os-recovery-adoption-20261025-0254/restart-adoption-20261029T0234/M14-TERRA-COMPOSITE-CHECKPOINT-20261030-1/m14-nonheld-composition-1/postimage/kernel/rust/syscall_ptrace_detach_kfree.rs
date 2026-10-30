// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::{c_int, c_void};

// These constants are valid only under the independently bound PROFILE_119
// source path and logical-line profile described in the private handoff.
const SOURCE_FILE: &[u8] = b"/src/kernel/syscall.c\0";
#[cfg(f03_ptrace_kfree_dispatch_origin)]
const SOURCE_LINE: c_int = 4657;
#[cfg(not(f03_ptrace_kfree_dispatch_origin))]
const SOURCE_LINE: c_int = 4664;

/// Preserve the original tracked-free callback and its selected C origin.
///
/// # Safety
/// `ptr` must be null or an owned live tracked allocation admissible to the
/// original callback, and ownership must be transferred exactly once.
#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_kfree_bridge(ptr: *mut c_void) {
    // SAFETY: The caller supplies the original pointer domain, and the source
    // profile binds these Rust-owned C-string bytes and line to the original
    // translation unit. The allocator handles null and tracking as before.
    unsafe {
        crate::mem_helpers::kfree_tracked(
            ptr, SOURCE_FILE.as_ptr().cast_mut().cast(), SOURCE_LINE,
        );
    }
}
