#[no_mangle]
pub unsafe extern "C" fn process_memobj_invalidate_page_bridge(
    memobj: *mut Memobj,
    phys: CULong,
    pgsize: SizeT,
) -> CInt {
    crate::object_helpers::memobj_invalidate_page(memobj, phys, pgsize)
}

#[no_mangle]
pub unsafe extern "C" fn process_invalidate_one_page_log_bridge(
    arg0: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pte_value: CULong,
    pgaddr: *mut c_void,
    pgshift: CInt,
    error: CInt,
) {
    let _ = kprintf(
        b"invalidate_one_page(%p,%p,%p %#lx,%p,%d):invalidate failed. %d\n\0".as_ptr().cast(),
        arg0, page_table, ptep, pte_value, pgaddr, pgshift, error,
    );
}
