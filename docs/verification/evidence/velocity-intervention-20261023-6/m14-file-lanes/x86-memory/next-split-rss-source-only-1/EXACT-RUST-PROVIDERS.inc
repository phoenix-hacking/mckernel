// Keep the real size_t callback ABI and original unsigned-long/int endpoint
// conversion. Existing Rust accounting retains enable_rusage and atomic policy.
#[no_mangle]
pub unsafe extern "C" fn x86_split_rss_add_bridge(size: SizeT, pgsize: SizeT) {
    unsafe { crate::mem_helpers::memory_stat_rss_add(size as CULong, pgsize as CInt) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_rss_sub_bridge(size: SizeT, pgsize: SizeT) {
    unsafe { crate::mem_helpers::memory_stat_rss_sub(size as CULong, pgsize as CInt) }
}
