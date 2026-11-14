#[inline(always)]
unsafe fn pagealloc_track_entry_from_hash(node: *mut AbiListHead) -> *mut PageallocTrackEntry {
    node.cast::<u8>()
        .sub(offset_of!(PageallocTrackEntry, hash))
        .cast::<PageallocTrackEntry>()
}
