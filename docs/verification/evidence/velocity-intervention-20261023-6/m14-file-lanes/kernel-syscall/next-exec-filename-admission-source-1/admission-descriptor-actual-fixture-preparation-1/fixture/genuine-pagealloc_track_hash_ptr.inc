#[inline(always)]
unsafe fn pagealloc_track_hash_ptr() -> *mut AbiListHead {
    (&raw mut PAGEALLOC_TRACK_HASH).cast::<AbiListHead>()
}
