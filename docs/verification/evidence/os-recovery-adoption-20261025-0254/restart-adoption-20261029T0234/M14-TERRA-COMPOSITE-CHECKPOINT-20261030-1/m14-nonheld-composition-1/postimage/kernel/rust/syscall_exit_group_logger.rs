//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Private candidate: both the callback and its original descriptor are Rust-owned.

use core::mem::{align_of, offset_of, size_of};
use core::ptr::{addr_of, read_volatile};
use crate::debug::Ddebug;
use super::{kprintf, CInt};

const _: () = {
    assert!(size_of::<Ddebug>() == 32);
    assert!(align_of::<Ddebug>() == 8);
    assert!(offset_of!(Ddebug, line_flags) == 24);
};

// Exactly one original af46 registry row, using the existing private F06 Rust
// static pattern. Keep original image-lifetime storage and flag-update/exclusion
// contract: no new reference aliases, locks or atomicity guarantees are added.
#[used]
#[link_section = "__verbose"]
static mut EXIT_GROUP_DEBUG: Ddebug = Ddebug {
    file: b"/src/kernel/syscall.c\0".as_ptr().cast(),
    func: b"exit_group_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: 5678 | (0 << 24),
};

/// Existing void(int) callback, with the original nonzero dynamic-debug gate.
#[no_mangle]
pub(super) extern "C" fn exit_group_log_bridge(pid: CInt) {
    // SAFETY: the private static has image lifetime and the existing Ddebug ABI.
    // Read the same mutable high-byte flags once without retaining a reference
    // over kprintf, under the unchanged debug-update/exclusion contract. Volatile
    // retains the load; it supplies no new synchronization guarantee.
    // The static NUL format has exactly one %d matched by unchanged CInt/i32.
    unsafe {
        let flags = read_volatile(addr_of!(EXIT_GROUP_DEBUG.line_flags)) >> 24;
        if flags != 0 {
            kprintf(c"sys_exit_group,pid=%d\n".as_ptr().cast(), pid);
        }
    }
}
