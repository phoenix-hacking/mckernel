#![no_std]
// Exact finite current native delay source partition; nonexecuted codegen only.
// No calibration, hardware counter, timing, boot or native-runtime qualification.
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

mod x86_cpu_helpers {
use crate::abi::{CInt, CULong};

extern "C" {
    fn arch_delay(us: CInt);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_delay_us(us: CInt) {
    unsafe {
        arch_delay(us);
    }
}

#[no_mangle]
pub unsafe extern "C" fn rdtsc() -> CULong {
    let high: u32;
    let low: u32;

    core::arch::asm!(
        "rdtsc",
        lateout("edx") high,
        lateout("eax") low,
        options(nomem, nostack, preserves_flags),
    );

    ((high as CULong) << 32) | (low as CULong)
}
}

mod x86_setup {
use crate::abi::{CInt, CULong};

extern "C" {
    fn cpu_pause();
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn arch_delay(us: CInt) {
    let tsc = crate::x86_cpu_helpers::rdtsc().wrapping_add(333u64.wrapping_mul(us as CULong));
    while crate::x86_cpu_helpers::rdtsc() < tsc {
        cpu_pause();
    }
}
}
