#[no_mangle]
pub unsafe extern "C" fn x86_clear_page_unmap_bridge(page: *mut c_void) -> CInt {
    page_unmap(page.cast::<Page>())
}
