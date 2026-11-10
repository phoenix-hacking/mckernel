mod local_apic_io {
    use core::ffi::c_void;
    use core::ptr::{addr_of, read_volatile, write_volatile};

    use crate::abi::{CInt, CULong};

    unsafe extern "C" {
        #[link_name = "lapic_vp"]
        static mut mapped_local_apic: *mut c_void;
        static x86_local_apic_base_msr: u32;
    }

    /// Perform the same single volatile 32-bit mapped local APIC store.
    ///
    /// # Safety
    /// The existing dispatch selection and caller must ensure the mapped device
    /// remains live, writable and excluded as required. `reg` must select an
    /// aligned accessible 32-bit register relative to the existing mapped base.
    #[no_mangle]
    pub unsafe extern "C" fn apic_write(reg: CInt, value: u32) {
        // SAFETY: The caller owns the same mapping/exclusion contract as the C
        // provider. The slot contains a live device base; no reference is formed
        // to MMIO. Signed byte offset and access width are preserved exactly.
        unsafe {
            let base = addr_of!(mapped_local_apic).read().cast::<u8>();
            let register = base.offset(reg as isize).cast::<u32>();
            write_volatile(register, value);
        }
    }

    /// Perform the same single volatile 32-bit mapped local APIC load.
    ///
    /// # Safety
    /// The caller must satisfy the live mapping, alignment and device access
    /// exclusion contract documented by `apic_write`, with a readable register.
    #[no_mangle]
    pub unsafe extern "C" fn apic_read(reg: CInt) -> u32 {
        // SAFETY: The caller supplies a live, aligned readable device register.
        // The load remains volatile; no caching, retry or additional read occurs.
        unsafe {
            let base = addr_of!(mapped_local_apic).read().cast::<u8>();
            read_volatile(base.offset(reg as isize).cast::<u32>())
        }
    }

    /// Preserve the signed register conversion and existing Rust MSR write.
    ///
    /// # Safety
    /// The caller must execute on the intended CPU with x2APIC enabled and a
    /// valid register/value for the existing dispatch selection and IRQ context.
    #[no_mangle]
    pub unsafe extern "C" fn x2apic_write(mut reg: CInt, value: u32) {
        // SAFETY: The real C macro supplies the same index base; arithmetic
        // right shift preserves GCC's signed int mapping. The existing Rust
        // wrmsr provider retains the privileged instruction and ordering contract.
        unsafe {
            reg >>= 4;
            reg |= x86_local_apic_base_msr as CInt;
            super::wrmsr(reg as u32, value as CULong);
        }
    }

    /// Preserve the signed index mapping and low-32-bit unsigned return.
    ///
    /// # Safety
    /// The caller must meet the x2APIC CPU/register/exclusion contract described
    /// by `x2apic_write`. The existing Rust MSR read may access device state.
    #[no_mangle]
    pub unsafe extern "C" fn x2apic_read(mut reg: CInt) -> u32 {
        // SAFETY: The caller selected a valid x2APIC provider/register. The same
        // single existing Rust rdmsr call occurs; C's int-to-unsigned return
        // conversion keeps the same low32 bits of the 64-bit MSR value.
        unsafe {
            reg >>= 4;
            reg |= x86_local_apic_base_msr as CInt;
            super::rdmsr(reg as u32) as u32
        }
    }
}
