#[inline(always)]
unsafe fn pagealloc_addr_hash_ptr() -> *mut AbiListHead {
    (&raw mut PAGEALLOC_ADDR_HASH).cast::<AbiListHead>()
}
