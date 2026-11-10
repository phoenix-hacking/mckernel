mod dispatch_and_msr_entries {
    use core::ptr::addr_of_mut;

    use crate::abi::CInt;

    type WriteRegister = unsafe extern "C" fn(CInt, u32);
    type ReadRegister = unsafe extern "C" fn(CInt) -> u32;
    type WriteIcr = unsafe extern "C" fn(u32, u32);
    type WaitIcr = unsafe extern "C" fn();
    type IssueIpi = unsafe extern "C" fn(u32, u32);

    // The existing nullable C-function-pointer aliases retain their exact
    // ABI. Initial NULL state and all selector publication order are unchanged.
    #[export_name = "x86_cpu_x2apic_mode"]
    static mut selected_mode: CInt = 0;

    #[no_mangle]
    pub(crate) static mut lapic_icr_write: Option<WriteIcr> = None;
    #[no_mangle]
    pub(crate) static mut lapic_wait_icr_idle: Option<WaitIcr> = None;

    // Genuine existing slot owners are imported, never redefined.
    unsafe extern "C" {
        static mut lapic_write: Option<WriteRegister>;
        static mut lapic_read: Option<ReadRegister>;
        static mut x86_issue_ipi: Option<IssueIpi>;
    }

    const _: () = {
        assert!(core::mem::size_of::<Option<WriteRegister>>() == 8);
        assert!(core::mem::align_of::<Option<WriteRegister>>() == 8);
        assert!(core::mem::size_of::<Option<ReadRegister>>() == 8);
        assert!(core::mem::align_of::<Option<ReadRegister>>() == 8);
        assert!(core::mem::size_of::<Option<WriteIcr>>() == 8);
        assert!(core::mem::align_of::<Option<WriteIcr>>() == 8);
        assert!(core::mem::size_of::<Option<WaitIcr>>() == 8);
        assert!(core::mem::align_of::<Option<WaitIcr>>() == 8);
        assert!(core::mem::size_of::<Option<IssueIpi>>() == 8);
        assert!(core::mem::align_of::<Option<IssueIpi>>() == 8);
    };

    /// Retain the existing x2APIC mode's intentionally empty wait callback.
    ///
    /// # Safety
    /// The caller retains the original x2APIC dispatch/CPU ownership contract.
    /// No timeout, polling, barrier or controller access is introduced.
    #[no_mangle]
    pub unsafe extern "C" fn x2apic_wait_icr_idle() {}

    /// Publish the original mode and five dispatch targets in the same order.
    ///
    /// # Safety
    /// Boot owns all six existing C slots and excludes concurrent consumers or
    /// updates through the entire publication. This preserves the original
    /// unsynchronized C contract; it does not add atomicity or a readiness flag.
    #[no_mangle]
    pub unsafe extern "C" fn x86_lapic_bsp_select_bridge(use_x2apic: CInt) {
        // SAFETY: Each actual selected C slot has the exact original function
        // pointer ABI. All concrete targets are the existing private Rust body
        // exports, including the empty wait. No slot lifetime is extended.
        unsafe {
            if use_x2apic != 0 {
                addr_of_mut!(selected_mode).write(1);
                addr_of_mut!(lapic_write).write(Some(super::local_apic_io::x2apic_write));
                addr_of_mut!(lapic_read).write(Some(super::local_apic_io::x2apic_read));
                addr_of_mut!(lapic_icr_write).write(Some(super::icr_callbacks::x2apic_icr_write));
                addr_of_mut!(lapic_wait_icr_idle).write(Some(x2apic_wait_icr_idle));
                addr_of_mut!(x86_issue_ipi).write(Some(super::ipi_entries::x2apic_x86_issue_ipi));
            } else {
                addr_of_mut!(selected_mode).write(0);
                addr_of_mut!(lapic_write).write(Some(super::local_apic_io::apic_write));
                addr_of_mut!(lapic_read).write(Some(super::local_apic_io::apic_read));
                addr_of_mut!(lapic_icr_write).write(Some(super::icr_callbacks::apic_icr_write));
                addr_of_mut!(lapic_wait_icr_idle)
                    .write(Some(super::icr_callbacks::apic_wait_icr_idle));
                addr_of_mut!(x86_issue_ipi).write(Some(super::ipi_entries::apic_x86_issue_ipi));
            }
        }
    }
}
