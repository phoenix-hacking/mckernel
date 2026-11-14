//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Private same-name callback and three Rust-owned original debug descriptors.
use core::mem::{align_of, offset_of, size_of};
use core::ptr::{addr_of, read_volatile};
use crate::debug::Ddebug;
use super::{kprintf, CInt, PTRACE_REPORT_CLONE_LOG_ENTER,
    PTRACE_REPORT_CLONE_LOG_KILL_SIGCHLD, PTRACE_REPORT_CLONE_LOG_DO_KILL_FAILED};

const _: () = {
    assert!(size_of::<Ddebug>() == 32);
    assert!(align_of::<Ddebug>() == 8);
    assert!(offset_of!(Ddebug, line_flags) == 24);
};

// Private image-lifetime records reuse the existing Rust __verbose pattern.
// Preserve original debug update/exclusion; volatile is not synchronization.
#[used]
#[link_section = "__verbose"]
static mut CLONE_ENTER_DEBUG: Ddebug = Ddebug {
    file: b"/src/kernel/syscall.c\0".as_ptr().cast(),
    func: b"ptrace_report_clone_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(), line_flags: 7279 | (0 << 24),
};
#[used]
#[link_section = "__verbose"]
static mut CLONE_KILL_DEBUG: Ddebug = Ddebug {
    file: b"/src/kernel/syscall.c\0".as_ptr().cast(),
    func: b"ptrace_report_clone_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(), line_flags: 7283 | (0 << 24),
};
#[used]
#[link_section = "__verbose"]
static mut CLONE_FAILED_DEBUG: Ddebug = Ddebug {
    file: b"/src/kernel/syscall.c\0".as_ptr().cast(),
    func: b"ptrace_report_clone_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(), line_flags: 7288 | (0 << 24),
};

/// # Safety
/// The pointer is one of these live aligned records; original flag-update
/// exclusion remains. No reference is retained across the eventual kprintf.
unsafe fn enabled(descriptor: *const Ddebug) -> bool {
    unsafe { read_volatile(addr_of!((*descriptor).line_flags)) >> 24 != 0 }
}

/// Existing void(int,int,int) callback; value/result were never format arguments.
#[no_mangle]
pub(super) extern "C" fn ptrace_report_clone_log_bridge(
    event: CInt, _value: CInt, _result: CInt,
) {
    // SAFETY: only the matching image-lifetime descriptor is read; each format
    // is static NUL-terminated with zero varargs. kprintf retains its existing
    // CPU prefix; no extra CPU query/argument or body action is added.
    unsafe {
        match event {
            PTRACE_REPORT_CLONE_LOG_ENTER => {
                if enabled(addr_of!(CLONE_ENTER_DEBUG)) {
                    kprintf(c"ptrace_report_clone,enter\n".as_ptr().cast());
                }
            }
            PTRACE_REPORT_CLONE_LOG_KILL_SIGCHLD => {
                if enabled(addr_of!(CLONE_KILL_DEBUG)) {
                    kprintf(c"ptrace_report_clone,kill SIGCHLD\n".as_ptr().cast());
                }
            }
            PTRACE_REPORT_CLONE_LOG_DO_KILL_FAILED => {
                if enabled(addr_of!(CLONE_FAILED_DEBUG)) {
                    kprintf(c"ptrace_report_clone,do_kill failed\n".as_ptr().cast());
                }
            }
            _ => {}
        }
    }
}
