#[no_mangle]
pub unsafe extern "C" fn x86_pt_alloc_zeroed_result(
    ap_flag: CInt,
    alloc_fn: Option<X86PtAllocPagesFn>,
) -> *mut c_void {
    let Some(alloc) = alloc_fn else {
        return core::ptr::null_mut();
    };

    let pt = unsafe { alloc(1, ap_flag) };
    if !pt.is_null() {
        unsafe {
            write_bytes(pt as *mut CULong, 0, PT_ENTRIES as usize);
        }
    }

    pt
}
