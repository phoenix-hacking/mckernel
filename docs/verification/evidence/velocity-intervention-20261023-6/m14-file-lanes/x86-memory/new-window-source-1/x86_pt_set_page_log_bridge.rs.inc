pub unsafe extern "C" fn x86_pt_set_page_log_bridge(virt: CULong) {
    unsafe {
        let _ = kprintf(b"EBUSY: page table for 0x%lX is already set\n\0".as_ptr().cast(), virt);
    }
}
