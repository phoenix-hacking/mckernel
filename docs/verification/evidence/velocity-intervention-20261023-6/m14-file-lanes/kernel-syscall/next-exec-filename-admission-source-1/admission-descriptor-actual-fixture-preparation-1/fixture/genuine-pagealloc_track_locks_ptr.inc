#[inline(always)]
unsafe fn pagealloc_track_locks_ptr() -> *mut IhkSpinlock {
    (&raw mut PAGEALLOC_TRACK_HASH_LOCKS).cast::<IhkSpinlock>()
}
