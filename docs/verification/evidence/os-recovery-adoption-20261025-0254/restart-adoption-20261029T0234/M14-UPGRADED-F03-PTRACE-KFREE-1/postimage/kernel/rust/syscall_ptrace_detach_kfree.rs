// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::{c_char, c_int, c_void};
use core::ptr::addr_of;

unsafe extern "C" {
    static f03_ptrace_detach_kfree_file_v1: c_char;
    static f03_ptrace_detach_kfree_line_v1: c_int;
}

/// Forward the original callback's ownership and tracking provenance unchanged.
///
/// # Safety
/// `ptr` must be null or the same live tracked allocation accepted by the
/// original callback; ownership transfers to the allocator exactly once.
#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_kfree_bridge(ptr: *mut c_void) {
    // SAFETY: The caller supplies the original tracked-free domain. These C
    // objects have static lifetime and capture the selected C file and line;
    // the tracked allocator owns the subsequent null/valid-pointer handling.
    unsafe {
        crate::mem_helpers::kfree_tracked(
            ptr,
            addr_of!(f03_ptrace_detach_kfree_file_v1).cast_mut(),
            f03_ptrace_detach_kfree_line_v1,
        );
    }
}
