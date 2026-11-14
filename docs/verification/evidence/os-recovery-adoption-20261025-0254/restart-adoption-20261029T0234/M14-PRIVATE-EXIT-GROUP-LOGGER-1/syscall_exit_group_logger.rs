//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! PRIVATE LEAF: unselected until the exact existing C descriptor binding is supplied.

use core::ptr::{addr_of, read_volatile};
use crate::debug::Ddebug;
use super::{kprintf, CInt};

unsafe extern "C" {
    // REQUIRED dependency: the one original dkprintf descriptor, not a new row.
    static mut f03_exit_group_log_debug_v1: Ddebug;
}

/// Existing void(int) callback, with the original nonzero dynamic-debug gate.
#[no_mangle]
pub(super) extern "C" fn exit_group_log_bridge(pid: CInt) {
    // SAFETY: the required C object has the existing Ddebug32-byte/alignment8
    // layout and lifetime. Its high byte at line_flags offset24 is the original
    // flags field. Read it once without retaining a reference over kprintf.
    // The static NUL format has exactly one %d, matched by unchanged CInt/i32.
    unsafe {
        let flags = read_volatile(addr_of!(f03_exit_group_log_debug_v1.line_flags)) >> 24;
        if flags != 0 {
            kprintf(c"sys_exit_group,pid=%d\n".as_ptr().cast(), pid);
        }
    }
}
