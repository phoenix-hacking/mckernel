#[no_mangle]
pub unsafe extern "C" fn process_pte_make_fileoff_bridge(
    off: OffT,
    pgsize: SizeT,
    ptep: *mut c_void,
) {
    crate::pte_helpers::pte_make_fileoff(off, 0, pgsize, ptep.cast::<CULong>());
}

#[no_mangle]
pub unsafe extern "C" fn process_pte_xchg_bridge(
    ptep: *mut c_void,
    valp: *mut c_void,
) {
    crate::pte_helpers::pte_xchg(ptep.cast::<CULong>(), valp.cast::<CULong>());
}
