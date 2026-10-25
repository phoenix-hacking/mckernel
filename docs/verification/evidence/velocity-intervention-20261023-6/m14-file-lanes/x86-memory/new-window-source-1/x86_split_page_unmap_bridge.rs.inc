pub unsafe extern "C" fn x86_split_page_unmap_bridge(page: *mut c_void) -> CInt {
    unsafe { crate::page_helpers::page_unmap(page.cast::<Page>()) }
}
