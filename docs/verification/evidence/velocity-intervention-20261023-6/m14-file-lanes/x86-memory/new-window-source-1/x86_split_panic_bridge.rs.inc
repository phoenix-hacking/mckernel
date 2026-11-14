pub unsafe extern "C" fn x86_split_panic_bridge() {
    unsafe {
        x86_memory_existing_panic(b"split_large_page:page_unmap\n\0".as_ptr().cast());
    }
}
