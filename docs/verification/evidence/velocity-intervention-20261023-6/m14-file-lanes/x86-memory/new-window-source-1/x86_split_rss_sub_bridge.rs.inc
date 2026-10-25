pub unsafe extern "C" fn x86_split_rss_sub_bridge(size: SizeT, pgsize: SizeT) {
    unsafe { crate::mem_helpers::memory_stat_rss_sub(size as CULong, pgsize as CInt) }
}
