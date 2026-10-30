//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Rebased existing private adapters. Instruction and destructive native proof OPEN.
use core::ffi::c_void;
use super::{kprintf, CInt, CLong, EFAULT};

unsafe extern "C" {
    #[link_name = "terminate"]
    fn f06_signal_adapter_terminate(status: CInt, signal: CInt);
}

/// # Safety
/// Exact original raw XRSTOR contract: aligned valid standard state, boot mask,
/// intended CPU and exclusion; all code/callees obey the no-FP/SIMD profile.
/// Fault behavior stays raw; never substitute native_xrstor_checked or HOST-run.
#[no_mangle]
pub unsafe extern "C" fn arch_rt_sigreturn_xrstor_bridge(state: *mut c_void) {
    // SAFETY: complete existing Rust instruction body and actual boot-mask getter.
    unsafe {
        let mask = crate::x86_cpu_helpers::get_xsave_mask();
        crate::x86_cpu_helpers::x86_restore_xstate(state.cast_const(), mask);
    }
}

/// # Safety
/// Original native disposition: logger is available and genuine terminate owns
/// the current process lifetime. The original void call may return in a fixture.
#[cfg(native_linux_irq_work_v6_12)]
#[no_mangle]
pub unsafe extern "C" fn arch_native_signal_bad_frame_bridge(error: CLong) -> CLong {
    // SAFETY: exact diagnostic, then original void terminate and constant result.
    unsafe {
        kprintf(b"native signal return rejected: %ld\n\0".as_ptr().cast(), error);
        f06_signal_adapter_terminate(0, 11); // SIGSEGV, actual header witness.
    }
    -(EFAULT as CLong)
}
