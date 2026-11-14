// Preserve the exact existing physical-page lookup endpoint and pointer bits.
// Its lower C geometry/lookup wrapper remains debt; no new page/null policy.
#[no_mangle]
pub unsafe extern "C" fn x86_split_phys_to_page_bridge(phys: CULong) -> *mut c_void {
    unsafe { phys_to_page(phys).cast::<c_void>() }
}
