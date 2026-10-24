#[no_mangle]
pub unsafe extern "C" fn strcmp(mut s1: *const i8, mut s2: *const i8) -> CInt {
    while read_char(s1) != 0 && read_char(s1) == read_char(s2) {
        s1 = s1.add(1);
        s2 = s2.add(1);
    }

    char_diff(read_char(s1), read_char(s2))
}
