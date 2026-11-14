#[inline(always)]
unsafe fn pagealloc_track_entry_alloc_count(entry: *mut PageallocTrackEntry) -> &'static AtomicI32 {
    AtomicI32::from_ptr(&raw mut (*entry).alloc_count.counter)
}
