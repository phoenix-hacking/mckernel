#[no_mangle]
pub unsafe extern "C" fn x86_clear_free_pages_user_bridge(addr: *mut c_void, nr_pages: CInt) {
    _ihk_mc_free_pages(
        addr, nr_pages, x86_clear_free_pages_user_flag,
        core::ptr::addr_of!(x86_clear_free_pages_user_file).cast::<i8>() as *mut i8,
        x86_clear_free_pages_user_line,
    );
}
