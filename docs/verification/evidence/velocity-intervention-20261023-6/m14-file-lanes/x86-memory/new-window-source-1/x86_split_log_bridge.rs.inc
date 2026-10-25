pub unsafe extern "C" fn x86_split_log_bridge(
    event: CInt, value: CULong, size: SizeT, pgsize: SizeT, page: *mut c_void,
) {
    unsafe {
        match event {
            X86_SPLIT_LARGE_PAGE_LOG_INVALID_PGSIZE => {
                let _ = kprintf(b"split_large_page:invalid pgsize %#lx\n\0".as_ptr().cast(), pgsize);
            }
            X86_SPLIT_LARGE_PAGE_LOG_ALLOC_FAILED => {
                let _ = kprintf(b"split_large_page:__alloc_new_pt failed\n\0".as_ptr().cast());
            }
            X86_SPLIT_LARGE_PAGE_LOG_RSS_ADD => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_split_rss_add_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(
                        b"%lx+,%s: calling memory_stat_rss_add(),size=%ld,pgsize=%ld\n\0".as_ptr().cast(),
                        value, b"split_large_page\0".as_ptr().cast::<i8>(), size, pgsize,
                    );
                }
            }
            X86_SPLIT_LARGE_PAGE_LOG_RSS_SUB => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_split_rss_sub_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(
                        b"%lx-,%s: calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n\0".as_ptr().cast(),
                        value, b"split_large_page\0".as_ptr().cast::<i8>(), size, pgsize,
                    );
                }
            }
            X86_SPLIT_LARGE_PAGE_LOG_PAGE_UNMAP => {
                let _ = kprintf(b"split_large_page:page_unmap:%p\n\0".as_ptr().cast(), page);
            }
            _ => {}
        }
    }
}
