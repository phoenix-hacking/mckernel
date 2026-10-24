#[no_mangle]
pub unsafe extern "C" fn kfree_tracked(ptr: *mut c_void, file: *mut i8, line: CInt) {
    unsafe {
        _kfree(ptr, file, line);
    }
}
