pub unsafe extern "C" fn memobj_flush_page(obj: *mut Memobj, phys: CULong, pgsize: SizeT) -> CInt {
    let op = (*(*obj).ops).flush_page;
    if memobj_op_present_result(op as CULong) != 0 {
        let flush_page: MemobjPageOpFn = transmute(op);
        return flush_page(obj, phys, pgsize);
    }
    memobj_default_page_op_result()
}
