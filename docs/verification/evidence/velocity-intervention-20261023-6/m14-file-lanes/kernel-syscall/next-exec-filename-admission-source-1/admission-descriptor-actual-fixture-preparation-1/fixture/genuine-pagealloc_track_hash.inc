#[inline(always)]
unsafe fn pagealloc_track_hash(file: *mut i8, line: CInt) -> CInt {
    let len = if file.is_null() {
        0
    } else {
        strlen(file.cast_const()) as CInt
    };
    len.wrapping_add(line) & PAGEALLOC_TRACK_HASH_MASK
}
