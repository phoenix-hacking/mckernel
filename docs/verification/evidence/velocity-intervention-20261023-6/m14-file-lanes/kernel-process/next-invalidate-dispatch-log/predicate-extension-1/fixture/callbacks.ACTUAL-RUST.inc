#[no_mangle]
pub unsafe extern "C" fn process_pte_is_null_bridge(ptep: *mut c_void) -> CInt {
    crate::pte_helpers::pte_is_null(ptep.cast::<CULong>())
}

#[no_mangle]
pub unsafe extern "C" fn process_pte_is_fileoff_bridge(
    ptep: *mut c_void,
    pgsize: SizeT,
) -> CInt {
    crate::pte_helpers::pte_is_fileoff(ptep.cast::<CULong>(), pgsize)
}
