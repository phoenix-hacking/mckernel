#[no_mangle]
pub unsafe extern "C" fn strcpy(mut dest: *mut i8, mut src: *const i8) -> *mut i8 {
    let head = dest;

    loop {
        let ch = read_char(src);
        write_char(dest, ch);
        dest = dest.add(1);
        src = src.add(1);
        if ch == 0 {
            break;
        }
    }

    head
}
