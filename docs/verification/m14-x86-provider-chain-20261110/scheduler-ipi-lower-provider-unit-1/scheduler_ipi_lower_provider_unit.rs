#![no_std]

#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

mod x86_cpu_helpers {
use crate::abi::CULong;

type CUInt = u32;

unsafe extern "C" {
    fn cpu_pause();
}

#[no_mangle]
pub unsafe extern "C" fn wrmsr(index: CUInt, value: CULong) {
    let low = value as u32;
    let high = (value >> 32) as u32;

    core::arch::asm!(
        "wrmsr",
        in("ecx") index,
        in("eax") low,
        in("edx") high,
        options(nostack, preserves_flags),
    );
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_mb() {
    core::arch::asm!("mfence", options(nostack, preserves_flags));
}

mod remaining_cpu_callbacks {
    use crate::abi::{CInt, CULong};

    /// Write the same MSR through the existing Rust provider.
    ///
    /// # Safety
    /// The original legal MSR/value and privileged CPU ownership must hold.
    #[no_mangle]
    pub unsafe extern "C" fn x86_write_msr_bridge(register: CInt, value: CULong) {
    unsafe { super::wrmsr(register as u32, value); }
    }

    /// Call the same existing pause instruction provider.
    ///
    /// # Safety
    /// Retain the original polling/CPU context; no timeout or progress is added.
    #[no_mangle]
    pub unsafe extern "C" fn x86_cpu_pause_bridge() {
    unsafe { super::cpu_pause(); }
    }
}

mod dispatch_and_msr_entries {
    use crate::abi::CInt;

    type ReadRegister = unsafe extern "C" fn(CInt) -> u32;

    #[no_mangle]
    pub(crate) static mut lapic_read: Option<ReadRegister> = None;

    const _: () = {
        assert!(core::mem::size_of::<Option<ReadRegister>>() == 8);
        assert!(core::mem::align_of::<Option<ReadRegister>>() == 8);
    };
}
}
