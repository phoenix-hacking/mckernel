#![no_std]

#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

mod x86_cpu_helpers {
type CUInt = u32;

mod initialization_entries {
    use core::ffi::c_void;

    #[no_mangle]
    pub(crate) static mut lapic_vp: *mut c_void = core::ptr::null_mut();
}

// Literal values transcribed from the exact selected C macro definitions.
// No build-dependent MAP_KERNEL_START or configuration policy is inferred here.
// Real-header object equality remains mandatory before these private providers
// can be integrated; alternate header values are not qualified by this source.
mod selected_fixed_cpu_selectors {
    use super::CUInt;

    #[no_mangle]
    pub static x86_local_apic_base_msr: CUInt = 0x800;
}
}
