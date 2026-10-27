// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Selected fixed-arity cpu.c providers; reuse the existing Rust debug implementation.

use crate::abi::{CInt, CULong};
use crate::debug::{kprintf, kprintf_lock, kprintf_unlock};

/// Preserve the CPU feature-value diagnostic; unknown events remain silent.
#[no_mangle]
pub extern "C" fn x86_cpu_value_log_bridge(event: CInt, value: CInt) {
    if event == 1 {
        // SAFETY: the static format is NUL terminated and its sole %d consumes
        // exactly the promoted C int value. No address is dereferenced or retained.
        unsafe {
            kprintf(b"no_execute_available: %d\n\0".as_ptr().cast(), value);
        }
    }
}

/// Print the existing stack-frame values without dereferencing the addresses.
#[no_mangle]
pub extern "C" fn x86_stack_frame_log_bridge(ip: CULong, sp: CULong, fp: CULong) {
    // SAFETY: the static NUL-terminated format has three unsigned-long conversions,
    // matching the three by-value LP64 arguments in the unchanged order.
    unsafe {
        kprintf(b"IP: %016lx, SP: %016lx, FP: %016lx\n\0".as_ptr().cast(), ip, sp, fp);
    }
}

/// Preserve the complete enter-user trace as one existing locked kprintf call.
#[no_mangle]
pub extern "C" fn x86_mcexec_v10_trace_log_bridge(
    cpu: CInt,
    pid: CInt,
    tid: CInt,
    rip: CULong,
    sp: CULong,
    cs: CULong,
    ss: CULong,
    rflags: CULong,
    status: CInt,
) {
    // SAFETY: concat supplies one static NUL-terminated format. The first three
    // and final conversions consume C int; the middle five consume unsigned long.
    // Every argument is forwarded by value; no context pointer is read or retained.
    unsafe {
        kprintf(
            concat!(
                "mcexec_v10: enter_user cpu=%d pid=%d tid=%d rip=0x%lx ",
                "sp=0x%lx cs=0x%lx ss=0x%lx rflags=0x%lx status=%d\n\0",
            )
            .as_ptr()
            .cast(),
            cpu,
            pid,
            tid,
            rip,
            sp,
            cs,
            ss,
            rflags,
            status,
        );
    }
}

/// Acquire the same Rust print lock and return the unchanged saved interrupt flags.
///
/// # Safety
/// The caller must obey the existing kprintf lock nesting rules and pair the
/// returned flags with one unlock on the same CPU before leaving the protected scope.
#[no_mangle]
pub unsafe extern "C" fn x86_kprintf_lock_bridge() -> CULong {
    // SAFETY: the caller supplies the existing kernel lock-context and pairing
    // obligations; this direct provider adds no state or additional lock acquisition.
    unsafe { kprintf_lock() }
}

/// Release the print lock and restore exactly the flags supplied by its acquisition.
///
/// # Safety
/// The caller must own the kprintf lock on this CPU and pass the flags from the
/// matching acquisition. Ownership ends here; the flags must not be reused.
#[no_mangle]
pub unsafe extern "C" fn x86_kprintf_unlock_bridge(flags: CULong) {
    // SAFETY: lock ownership and matching saved flags are the caller's existing
    // contract; the selected Rust provider performs the unchanged unlock/restoration.
    unsafe { kprintf_unlock(flags) }
}
