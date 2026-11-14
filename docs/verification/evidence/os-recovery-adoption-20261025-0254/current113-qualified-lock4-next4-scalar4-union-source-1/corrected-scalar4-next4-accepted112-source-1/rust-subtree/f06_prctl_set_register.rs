// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact existing private provider; selected CPU helper retains the MSR effect.
use crate::abi::{CInt, CULong};

/// # Safety
/// Same architecture/current-thread contract as ihk_mc_arch_set_special_register.
/// Genuine provider may execute WRMSR; a HOST fixture must control only that effect.
#[no_mangle]
pub unsafe extern "C" fn arch_prctl_set_register_bridge(type_: CInt, value: CULong) -> CInt {
    // SAFETY: exact provider, register number, full-width value and error result.
    unsafe { crate::x86_cpu_helpers::ihk_mc_arch_set_special_register(type_, value) }
}
