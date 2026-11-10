// Complete existing ICR providers and idle wait. Existing selected data supplies
// register indices; no new getter, mapping, retry or hardware ordering policy.
mod icr_callbacks {
    use core::ptr::addr_of;

    use crate::abi::{CInt, CULong};

    type ReadRegister = unsafe extern "C" fn(CInt) -> u32;

    unsafe extern "C" {
        #[link_name = "lapic_read"]
        static mut selected_read: Option<ReadRegister>;
        static x86_icr_geometry: [CULong; 4];
    }

    /// Write the same combined low-word/destination value to the existing MSR.
    ///
    /// # Safety
    /// The caller must own the selected CPU/x2APIC context and controller
    /// exclusion required by the original C callback. The MSR bridge performs
    /// the existing privileged write and must remain available for this call.
    #[no_mangle]
    pub unsafe extern "C" fn x2apic_icr_write(low: u32, apicid: u32) {
        // SAFETY: The caller provides the live device/CPU context. The real C
        // macro supplies the same index. Keep the existing external MSR bridge
        // boundary instead of changing its compiler-visible memory effects.
        unsafe {
            let value = ((apicid as CULong) << 32) | low as CULong;
            super::x86_write_msr_bridge(x86_icr_geometry[0] as CInt, value);
        }
    }

    /// Preserve the high-register write followed by the low-register write.
    ///
    /// # Safety
    /// The caller must retain the existing selected mapped-APIC provider and
    /// its mapping/device exclusion across both operations. The high/low inputs
    /// and register selection have the same validity contract as the C callback.
    #[no_mangle]
    pub unsafe extern "C" fn apic_icr_write(high: u32, low: u32) {
        // SAFETY: Existing dispatch and mapping lifetime cover both writes.
        // Both calls reuse the original LAPIC bridge; no fence, read or reordering
        // is inserted between the two device operations.
        unsafe {
            super::x86_lapic_write_bridge(x86_icr_geometry[1] as CInt, high);
            super::x86_lapic_write_bridge(x86_icr_geometry[2] as CInt, low);
        }
    }

    /// Repeat the same busy-register read and pause until the busy bit clears.
    ///
    /// # Safety
    /// The selected read callback must be non-NULL, retain its actual C
    /// unsigned-int(int) ABI, and remain callable with live device state under
    /// the caller's controller exclusion. The original operation has no timeout.
    #[no_mangle]
    pub unsafe extern "C" fn apic_wait_icr_idle() {
        // SAFETY: The caller owns the same non-NULL dispatch/device contract as
        // C. Reload the function pointer each iteration without forming a Rust
        // reference to the mutable C slot. Do not add a NULL fallback or timeout.
        unsafe {
            loop {
                let read = addr_of!(selected_read).read().unwrap_unchecked();
                let value = read(x86_icr_geometry[2] as CInt);
                if value & x86_icr_geometry[3] as u32 == 0 {
                    break;
                }
                super::x86_cpu_pause_bridge();
            }
        }
    }
}
