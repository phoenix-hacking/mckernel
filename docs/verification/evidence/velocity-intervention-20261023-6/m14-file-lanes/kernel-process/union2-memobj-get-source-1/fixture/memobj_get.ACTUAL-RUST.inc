#[no_mangle]
pub unsafe extern "C" fn process_page_fault_memobj_get_body_result(
    range: *mut VmRange,
    pgaddr: *mut c_void,
    fault_addr: CULong,
    ptep: *mut CULong,
    pgsize: SizeT,
    p2align: CInt,
    phys_out: *mut CULong,
    memobj_flag_out: *mut CULong,
    error_out: *mut CInt,
) -> CInt {
    *phys_out = NOPHYS;
    if (*range).memobj.is_null() {
        // The original no-memobj path does not overwrite flags or error.
        return 0;
    }
    let off = if ptep.is_null()
        || crate::pte_helpers::pte_is_fileoff(ptep, pgsize) == 0
    {
        ((*range).objoff as CULong)
            .wrapping_add((pgaddr as CULong).wrapping_sub((*range).start)) as OffT
    } else {
        crate::pte_helpers::pte_get_off(ptep, pgsize)
    };
    *error_out = crate::object_helpers::memobj_get_page(
        (*range).memobj.cast::<Memobj>(), off, p2align,
        phys_out, memobj_flag_out, fault_addr,
    );
    // The unchanged C caller owns zeroobj/panic/comparison handling. This
    // predicate preserves every positive/negative provider error unchanged.
    (*error_out != 0) as CInt
}
