// Complete existing IPI entry wrappers. The already selected Rust transaction
// cores retain barrier, IRQ flags, idle wait, ICR argument order and restoration.
mod ipi_entries {
    use crate::abi::CInt;

    unsafe extern "C" {
        fn x2apic_icr_write(low: u32, apicid: u32);
        fn apic_icr_write(high: u32, low: u32);
        fn apic_wait_icr_idle();
        static x86_ipi_icr_id_shift: CInt;
    }

    /// Execute the same complete x2APIC IPI transaction using existing providers.
    ///
    /// # Safety
    /// The caller must run on the selected CPU in valid x2APIC/device context,
    /// with the same interrupt-controller exclusion and live ICR provider state
    /// required by the original wrapper. This invokes privileged IRQ/MSR effects.
    #[no_mangle]
    pub unsafe extern "C" fn x2apic_x86_issue_ipi(apicid: u32, low: u32) {
        // SAFETY: The caller supplies the existing device/exclusion contract.
        // These are the same Rust primitives reached through the old C thunks;
        // the existing transaction core preserves all callback order/flag data.
        unsafe {
            let _ = super::x86_x2apic_issue_ipi_body_result(
                apicid,
                low,
                Some(super::ihk_mc_mb),
                Some(super::cpu_disable_interrupt_save),
                Some(x2apic_icr_write),
                Some(super::cpu_restore_interrupt),
            );
        }
    }

    /// Execute the same complete mapped-APIC IPI transaction.
    ///
    /// # Safety
    /// The caller must provide the selected CPU/device/exclusion context and
    /// live mapped-APIC callbacks. The unchanged idle loop may wait for hardware;
    /// the same IRQ flags must remain owned through the final restore operation.
    #[no_mangle]
    pub unsafe extern "C" fn apic_x86_issue_ipi(apicid: u32, low: u32) {
        // SAFETY: Existing device/mapping lifetime and IRQ exclusion cover the
        // callback sequence. The real C macro supplies the unchanged bit shift;
        // no new mask, bound, fallback, error suppression or return is added.
        unsafe {
            let _ = super::x86_apic_issue_ipi_body_result(
                apicid,
                low,
                x86_ipi_icr_id_shift,
                Some(super::cpu_disable_interrupt_save),
                Some(apic_wait_icr_idle),
                Some(apic_icr_write),
                Some(super::cpu_restore_interrupt),
            );
        }
    }
}
