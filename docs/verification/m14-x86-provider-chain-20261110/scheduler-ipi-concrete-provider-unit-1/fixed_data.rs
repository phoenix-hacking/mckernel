mod selected_fixed_cpu_selectors {
    use crate::abi::CInt;

    // Selected march.h LAPIC_ICR_ID_SHIFT definition.
    #[no_mangle]
    pub static x86_ipi_icr_id_shift: CInt = 24;
}

mod selected_remaining_cpu_arrays {
    use crate::abi::CULong;

    // IA32_X2APIC_ICR, LAPIC_ICR2, LAPIC_ICR0, APIC_ICR_BUSY.
    #[no_mangle]
    pub static x86_icr_geometry: [CULong; 4] = [0x830, 0x310, 0x300, 0x1000];
}
