#[inline(always)]
unsafe fn write_char(ptr: *mut i8, value: i8) {
    write_volatile(ptr, value);
}
