// Preserve the split callback's exact raw page identity and synchronous
// ownership handoff to the already Rust-owned page-map/unmap implementations.
#[no_mangle]
pub unsafe extern "C" fn x86_split_page_map_bridge(page: *mut c_void) {
    unsafe { crate::page_helpers::page_map(page.cast::<Page>()) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_page_unmap_bridge(page: *mut c_void) -> CInt {
    unsafe { crate::page_helpers::page_unmap(page.cast::<Page>()) }
}
