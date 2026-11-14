//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Original ptrace wakeup diagnostic callback and its single debug descriptor.
use core::mem::{align_of, offset_of, size_of};
use core::ptr::{addr_of, read_volatile};
use crate::debug::Ddebug;
use super::{kprintf, CInt, PTRACE_CONTROL_LOG_WAKEUP_ENTER};

// The C selector requires the matching integer and checks it against the actual
// translation unit's DDEBUG_DEFAULT. The build must bind both flags together.
const INITIAL_FLAGS: u32 = match env!("MCKERNEL_F03_PTRACE_WAKEUP_DDEBUG_FLAGS").as_bytes() {
    b"0" => 0,
    b"1" => 1,
    _ => panic!("ptrace wakeup debug default must match C DDEBUG_DEFAULT (0 or 1)"),
};
const _: () = {
    assert!(PTRACE_CONTROL_LOG_WAKEUP_ENTER == 4);
    assert!(size_of::<Ddebug>() == 32);
    assert!(align_of::<Ddebug>() == 8);
    assert!(offset_of!(Ddebug, line_flags) == 24);
};

// The selected x86 source profile binds the logical path and line to the C
// fallback's original dkprintf site. Only that profile may enable this module.
#[used]
#[link_section = "__verbose"]
static mut WAKEUP_DEBUG: Ddebug = Ddebug {
    file: b"/src/kernel/syscall.c\0".as_ptr().cast(),
    func: b"ptrace_wakeup_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: 24429 | (INITIAL_FLAGS << 24),
};

/// Callback with the original C event and integer argument ABI.
///
/// # Safety
/// The selected build binds the exact descriptor layout, file/line origin and
/// debug default. Descriptor updates obey the original dynamic-debug exclusion;
/// no reference or lock is retained when invoking the formatter.
#[no_mangle]
pub(super) unsafe extern "C" fn ptrace_wakeup_log_bridge(
    event: CInt, value: CInt, result: CInt,
) {
    if event == PTRACE_CONTROL_LOG_WAKEUP_ENTER {
        // SAFETY: WAKEUP_DEBUG is a live aligned image-lifetime record. Volatile
        // keeps the existing dynamic flag observation; it does not synchronize
        // concurrent updates or broaden the original C access contract.
        let flags = unsafe { read_volatile(addr_of!(WAKEUP_DEBUG.line_flags)) } >> 24;
        if flags != 0 {
            // SAFETY: original format and promoted C int operands are retained.
            unsafe { kprintf(c"ptrace_wakeup_sig,pid=%d,data=%08x\n".as_ptr(), value, result); }
        }
    }
}
