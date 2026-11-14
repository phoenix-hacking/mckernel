pub unsafe extern "C" fn x86_split_phys_to_page_bridge(phys: CULong) -> *mut c_void {
    unsafe { phys_to_page(phys).cast::<c_void>() }
}
