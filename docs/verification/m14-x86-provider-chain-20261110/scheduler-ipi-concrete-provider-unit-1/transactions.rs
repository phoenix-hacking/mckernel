#[no_mangle]
pub unsafe extern "C" fn x86_x2apic_issue_ipi_body_result(
    apicid: CUInt,
    low: CUInt,
    mb_fn: Option<X86VoidFn>,
    disable_save_fn: Option<X86DisableSaveFn>,
    icr_write_fn: Option<X86IcrWriteFn>,
    restore_fn: Option<X86RestoreFn>,
) -> CInt {
    let (Some(mb), Some(disable_save), Some(icr_write), Some(restore)) =
        (mb_fn, disable_save_fn, icr_write_fn, restore_fn)
    else {
        return -EINVAL;
    };

    mb();
    let flags = disable_save();
    icr_write(low, apicid);
    restore(flags);
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_apic_issue_ipi_body_result(
    apicid: CUInt,
    low: CUInt,
    lapic_icr_id_shift: CInt,
    disable_save_fn: Option<X86DisableSaveFn>,
    wait_idle_fn: Option<X86VoidFn>,
    icr_write_fn: Option<X86IcrWriteFn>,
    restore_fn: Option<X86RestoreFn>,
) -> CInt {
    if lapic_icr_id_shift < 0 || lapic_icr_id_shift >= 32 {
        return -EINVAL;
    }
    let (Some(disable_save), Some(wait_idle), Some(icr_write), Some(restore)) =
        (disable_save_fn, wait_idle_fn, icr_write_fn, restore_fn)
    else {
        return -EINVAL;
    };

    let flags = disable_save();
    wait_idle();
    icr_write(apicid << (lapic_icr_id_shift as u32), low);
    restore(flags);
    0
}
