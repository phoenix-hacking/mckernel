#[no_mangle]
pub extern "C" fn thread_hash(tid: CInt) -> CInt {
    tid % HASH_SIZE
}
