#[inline(always)]
unsafe fn pagealloc_addr_locks_ptr() -> *mut IhkSpinlock {
    (&raw mut PAGEALLOC_ADDR_HASH_LOCKS).cast::<IhkSpinlock>()
}
