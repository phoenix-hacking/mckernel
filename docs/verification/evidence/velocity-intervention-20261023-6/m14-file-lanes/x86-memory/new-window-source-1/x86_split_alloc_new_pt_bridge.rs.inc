pub unsafe extern "C" fn x86_split_alloc_new_pt_bridge(
    nr_pages: CInt, ap_flag: CInt,
) -> *mut c_void {
    if nr_pages != 1 {
        return core::ptr::null_mut();
    }
    unsafe { x86_pt_alloc_zeroed_result(ap_flag, Some(x86_pt_alloc_pages_bridge)) }
}
