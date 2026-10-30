//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Root-approved defined diagnostic correction; no parity claim for old long/%x.

use super::{kprintf, CInt, CLong, CULong};

/// Preserve the public callback ABI; render the complete unsigned long bit value.
#[no_mangle]
pub(super) extern "C" fn arch_ptrace_regset_log_bridge(event: CInt, type_: CLong) {
    let format = match event {
        1 => c"ptrace_read_regset: not supported type 0x%lx\n",
        2 => c"ptrace_write_regset: not supported type 0x%lx\n",
        _ => return,
    };
    // SAFETY: immutable NUL-terminated format has one %lx slot. CULong is the
    // actual u64 unsigned long variadic type. Conversion preserves all 64 bits,
    // including negative CLong values. No pointer/object lifetime crosses here.
    unsafe { kprintf(format.as_ptr().cast(), type_ as CULong); }
}
