#[no_mangle]
pub extern "C" fn process_lookup_range_relation_result(
    start: CULong,
    end: CULong,
    range_start: CULong,
    range_end: CULong,
) -> CInt {
    if end <= range_start {
        -1
    } else if start >= range_end {
        1
    } else if start < range_start {
        -2
    } else {
        0
    }
}
