// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact live fatal-signal and ptrace-regset adapters; genuine print/exit providers.
use crate::abi::{CInt, CLong};

/// Keep the original two event formats and their unsigned-int varargs width.
/// The original long was consumed by %x; explicit low32 extraction expresses
/// that x86_64 diagnostic behavior without a mismatched varargs argument type.
#[no_mangle]
pub extern "C" fn arch_ptrace_regset_log_bridge(event: CInt, type_: CLong) {
    let format: &[u8] = match event {
        1 => b"ptrace_read_regset: not supported type 0x%x\n\0",
        2 => b"ptrace_write_regset: not supported type 0x%x\n\0",
        _ => return,
    };
    // SAFETY: immutable terminated format consumes exactly one unsigned int.
    unsafe { crate::debug::kprintf(format.as_ptr().cast(), type_ as u32) };
}

#[cfg(native_linux_irq_work_v6_12)]
unsafe extern "C" {
    #[link_name = "terminate"]
    fn signal_terminate(status: CInt, signal: CInt);
}

/// Reject a failed native signal return using the existing termination endpoint.
///
/// # Safety
/// The caller retains the original current-thread/IRQ termination preconditions.
/// terminate remains void: preserve -EFAULT if the real endpoint returns.
#[cfg(native_linux_irq_work_v6_12)]
#[no_mangle]
pub unsafe extern "C" fn arch_native_signal_bad_frame_bridge(error: CLong) -> CLong {
    unsafe {
        crate::debug::kprintf(b"native signal return rejected: %ld\n\0".as_ptr().cast(), error);
        signal_terminate(0, 11); // SIGSEGV
    }
    -14 // EFAULT
}
