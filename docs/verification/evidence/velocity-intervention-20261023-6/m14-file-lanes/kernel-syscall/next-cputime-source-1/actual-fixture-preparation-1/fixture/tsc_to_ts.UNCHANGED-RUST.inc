#[no_mangle]
pub unsafe extern "C" fn tsc_to_ts(tsc: CULong, ts: *mut TimeSpec) {
    let clocks_per_sec = tod_data.clocks_per_sec;
    let sec_delta = core::intrinsics::unchecked_div(tsc, clocks_per_sec);
    let tsc_rem = core::intrinsics::unchecked_rem(tsc, clocks_per_sec);
    let ns_delta = core::intrinsics::unchecked_div(
        (NS_PER_SEC as CULong).wrapping_mul(tsc_rem),
        clocks_per_sec,
    );

    (*ts).tv_sec = sec_delta as CLong;
    (*ts).tv_nsec = ns_delta as CLong;
    if (*ts).tv_nsec >= NS_PER_SEC {
        (*ts).tv_nsec -= NS_PER_SEC;
        (*ts).tv_sec += 1;
    }
}
