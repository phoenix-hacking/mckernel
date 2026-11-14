pub unsafe extern "C" fn x86_split_rss_add_bridge(size: SizeT, pgsize: SizeT) {
    unsafe { crate::mem_helpers::memory_stat_rss_add(size as CULong, pgsize as CInt) }
}
