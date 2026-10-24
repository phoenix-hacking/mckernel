#[no_mangle]
pub extern "C" fn page_mode_in_memobj_result(mode: CInt) -> CInt {
    matches!(
        mode as u8,
        PM_MAPPED | PM_PAGEIO | PM_WILL_PAGEIO | PM_DONE_PAGEIO | PM_PAGEIO_EOF | PM_PAGEIO_ERROR
    ) as CInt
}
#[no_mangle]
pub extern "C" fn page_multi_mapped_result(count: CInt) -> CInt {
    (count > 1) as CInt
}
#[no_mangle]
pub unsafe extern "C" fn page_is_in_memobj_body_result(page: *mut Page) -> CInt {
    if page.is_null() {
        return 0;
    }

    page_mode_in_memobj_result(unsafe { read_volatile(&(*page).mode) } as CInt)
}
#[no_mangle]
pub unsafe extern "C" fn page_is_multi_mapped_body_result(page: *mut Page) -> CInt {
    if page.is_null() {
        return 0;
    }

    page_multi_mapped_result(unsafe { read_volatile(&(*page).count.counter) })
}
#[no_mangle]
pub unsafe extern "C" fn page_is_in_memobj(page: *mut Page) -> CInt {
    unsafe { page_is_in_memobj_body_result(page) }
}
#[no_mangle]
pub unsafe extern "C" fn page_is_multi_mapped(page: *mut Page) -> CInt {
    unsafe { page_is_multi_mapped_body_result(page) }
}
