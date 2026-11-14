#[inline(always)]
unsafe fn pagealloc_entry_addr_list_lock(entry: *mut PageallocTrackEntry) -> CULong {
    (&raw mut (*entry).addr_list_lock) as CULong
}
