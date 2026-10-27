#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod abi { include!("retained-abi-types.Rust.inc"); }
mod x86_perfctr {
    use crate::abi::{CInt, CULong};
    // Explicit HOST mocks of the existing providers: no actual PMU instructions.
    unsafe extern "C" {
        #[link_name="fixture_mask_provider"] pub fn ihk_mc_perf_counter_mask_check(mask: CULong) -> CInt;
        #[link_name="fixture_start_provider"] pub fn ihk_mc_perfctr_start(mask: CULong) -> CInt;
        #[link_name="fixture_stop_provider"] pub fn ihk_mc_perfctr_stop(mask: CULong, flags: CInt) -> CInt;
    }
}
mod policy {
    use crate::abi::{CInt, CULong};
    include!("selected-bridges.Rust.inc");
    #[no_mangle]
    pub static F03_COUNTER_CONTROL_ABI: [CULong; 6] = [
        core::mem::size_of::<CInt>() as _, core::mem::align_of::<CInt>() as _,
        core::mem::size_of::<CULong>() as _, core::mem::align_of::<CULong>() as _,
        core::mem::size_of::<unsafe extern "C" fn(CULong) -> CInt>() as _,
        core::mem::size_of::<unsafe extern "C" fn(CULong, CInt) -> CInt>() as _,
    ];
}
