pub unsafe extern "C" fn x86_split_page_map_bridge(page: *mut c_void) {
    unsafe { crate::page_helpers::page_map(page.cast::<Page>()) }
}
