#[inline(always)]
unsafe fn read_char(ptr: *const i8) -> i8 {
    read_volatile(ptr)
}
