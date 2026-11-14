//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Original ptrace wakeup diagnostic callback and its single debug descriptor.
use core::mem::{align_of, offset_of, size_of};
use core::ptr::{addr_of, addr_of_mut};
use core::sync::atomic::{AtomicU32, Ordering};
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
    assert!(align_of::<Ddebug>() >= align_of::<AtomicU32>());
    assert!(offset_of!(Ddebug, line_flags) % align_of::<AtomicU32>() == 0);
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

// The registry must route this exact descriptor to atomic accesses; ordinary
// reads/writes of its packed word are forbidden while concurrent. Static
// initialization precedes execution; the aligned object has image lifetime.
#[inline(always)]
unsafe fn word() -> &'static AtomicU32 {
    AtomicU32::from_ptr(addr_of_mut!(WAKEUP_DEBUG.line_flags))
}

#[inline(always)]
pub(crate) unsafe fn special_load(record: *const Ddebug) -> Option<u32> {
    if record == addr_of!(WAKEUP_DEBUG).cast::<Ddebug>() {
        Some(word().load(Ordering::Relaxed))
    } else {
        None
    }
}

#[inline(always)]
pub(crate) unsafe fn special_set_flags(record: *mut Ddebug, flags: u32) -> bool {
    if record.cast_const() != addr_of!(WAKEUP_DEBUG).cast::<Ddebug>() {
        return false;
    }
    let atom = word();
    let mut previous = atom.load(Ordering::Relaxed);
    loop {
        let next = (previous & 0x00ff_ffff) | (flags << 24);
        match atom.compare_exchange_weak(previous, next, Ordering::Relaxed, Ordering::Relaxed) {
            Ok(_) => return true,
            Err(observed) => previous = observed,
        }
    }
}

/// Callback with the original C event and integer argument ABI.
///
/// # Safety
/// The selected build must route every registry access to this record through
/// Rust debug's special accessors, and preserve original formatting arguments.
#[no_mangle]
pub(super) unsafe extern "C" fn ptrace_wakeup_log_bridge(
    event: CInt, value: CInt, result: CInt,
) {
    if event == PTRACE_CONTROL_LOG_WAKEUP_ENTER {
        let flags = word().load(Ordering::Relaxed) >> 24;
        if flags != 0 {
            kprintf(c"ptrace_wakeup_sig,pid=%d,data=%08x\n".as_ptr(), value, result);
        }
    }
}

#[cfg(test)]
pub(crate) unsafe fn test_record() -> *mut Ddebug {
    addr_of!(WAKEUP_DEBUG).cast_mut().cast::<Ddebug>()
}
