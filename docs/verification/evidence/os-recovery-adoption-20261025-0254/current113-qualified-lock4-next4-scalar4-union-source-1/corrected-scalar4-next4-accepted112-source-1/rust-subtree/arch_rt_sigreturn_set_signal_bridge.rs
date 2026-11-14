// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::c_void;
use crate::abi::{CInt, SigInfo};

unsafe extern "C" {
    #[link_name = "set_signal"]
    fn f06_signal_adapter_set_signal(signal: CInt, context: *mut c_void, info: *mut SigInfo);
}

/// # Safety
/// Original current signal/context/info contract; the C const pointer was also
/// cast to mutable SigInfo before set_signal. No Rust reference/retained borrow
/// is created, and the actual selected signal producer keeps its full behavior.
#[no_mangle]
pub unsafe extern "C" fn arch_rt_sigreturn_set_signal_bridge(
    signal: CInt, context: *mut c_void, info: *const SigInfo,
) {
    // SAFETY: exact prior C cast and synchronous public producer.
    unsafe { f06_signal_adapter_set_signal(signal, context, info.cast_mut()) };
}
