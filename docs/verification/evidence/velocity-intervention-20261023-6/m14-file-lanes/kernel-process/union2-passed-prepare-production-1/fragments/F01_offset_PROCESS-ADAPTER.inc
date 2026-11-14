#[no_mangle]
pub unsafe extern "C" fn process_page_offset_bridge(page: *mut c_void) -> OffT {
    crate::page_helpers::page_get_offset(page.cast::<crate::page_helpers::Page>())
}
