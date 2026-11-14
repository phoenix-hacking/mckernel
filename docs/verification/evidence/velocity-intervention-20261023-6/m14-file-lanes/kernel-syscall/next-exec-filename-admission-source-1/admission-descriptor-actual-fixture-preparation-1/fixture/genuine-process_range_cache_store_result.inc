#[no_mangle]
pub unsafe extern "C" fn process_range_cache_store_result(
    cache: *mut *mut c_void,
    count: CInt,
    indexp: *mut CInt,
    match_range: *mut c_void,
) -> CInt {
    if cache.is_null() || count <= 0 || indexp.is_null() || match_range.is_null() {
        return -EINVAL;
    }

    let new_index = unsafe { (*indexp - 1 + count) % count };
    unsafe {
        *indexp = new_index;
        *cache.add(new_index as usize) = match_range;
    }
    new_index
}
