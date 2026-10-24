    // Existing providers and actual selected C data, no new runtime C getter.
    #[link_name = "x86_set_warm_reset"]
    fn x86_wakeup_set_warm_reset(ip: CULong, first_page: *mut i8);
    #[link_name = "x86_issue_ipi"]
    static mut X86_WAKEUP_ISSUE_IPI: unsafe extern "C" fn(CUInt, CUInt);
    #[link_name = "x86_wakeup_lapic_write_slot"]
    static X86_WAKEUP_LAPIC_WRITE_SLOT: *const unsafe extern "C" fn(CInt, CUInt);
    #[link_name = "x86_wakeup_lapic_read_slot"]
    static X86_WAKEUP_LAPIC_READ_SLOT: *const unsafe extern "C" fn(CInt) -> CUInt;
    #[link_name = "x86_wakeup_wait_slot"]
    static X86_WAKEUP_WAIT_SLOT: *const unsafe extern "C" fn();
    #[link_name = "x86_wakeup_first_page_slot"]
    static X86_WAKEUP_FIRST_PAGE_SLOT: *const *mut i8;
    #[link_name = "x86_wakeup_boot_status_slot"]
    static X86_WAKEUP_BOOT_STATUS_SLOT: *const CInt;
    #[link_name = "x86_wakeup_constants"]
    static X86_WAKEUP_CONSTANTS: [CUInt; 5];
