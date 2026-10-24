#[no_mangle]
pub extern "C" fn process_range_cache_hit_result(
    cache_start: CULong,
    cache_end: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    (cache_start <= start && cache_end >= end) as CInt
}
