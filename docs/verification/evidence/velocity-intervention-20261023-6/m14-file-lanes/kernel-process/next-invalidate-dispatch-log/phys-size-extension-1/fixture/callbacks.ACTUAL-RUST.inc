#[no_mangle]
pub unsafe extern "C" fn process_pte_get_phys_bridge(ptep: *mut c_void) -> CULong {
    crate::pte_helpers::pte_get_phys(ptep.cast::<CULong>())
}

#[no_mangle]
pub unsafe extern "C" fn process_pgsize_to_tbllv_bridge(pgsize: SizeT) -> CInt {
    crate::pte_helpers::pgsize_to_tbllv(pgsize)
}

#[no_mangle]
pub unsafe extern "C" fn process_tbllv_to_contpgsize_bridge(level: CInt) -> SizeT {
    crate::pte_helpers::tbllv_to_contpgsize(level)
}
