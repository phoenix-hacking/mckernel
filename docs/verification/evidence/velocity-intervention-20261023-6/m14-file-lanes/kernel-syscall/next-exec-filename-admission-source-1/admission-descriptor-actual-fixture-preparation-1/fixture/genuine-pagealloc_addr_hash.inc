#[inline(always)]
unsafe fn pagealloc_addr_hash(ptr: *mut c_void) -> CInt {
    ((ptr as CULong) >> 5 & PAGEALLOC_TRACK_HASH_MASK as CULong) as CInt
}
