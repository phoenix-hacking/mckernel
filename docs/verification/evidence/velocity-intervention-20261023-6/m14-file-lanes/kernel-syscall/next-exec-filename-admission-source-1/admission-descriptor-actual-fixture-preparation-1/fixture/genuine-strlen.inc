#[no_mangle]
pub unsafe extern "C" fn strlen(mut ptr: *const i8) -> SizeT {
    let head = ptr;

    while read_char(ptr) != 0 {
        ptr = ptr.add(1);
    }

    ptr.offset_from(head) as SizeT
}
