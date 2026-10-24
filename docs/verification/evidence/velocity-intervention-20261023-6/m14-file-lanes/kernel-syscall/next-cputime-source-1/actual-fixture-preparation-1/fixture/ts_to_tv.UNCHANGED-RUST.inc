#[no_mangle]
pub unsafe extern "C" fn ts_to_tv(ats: *mut TimeVal, bts: *const TimeSpec) {
    unsafe {
        (*ats).tv_sec = (*bts).tv_sec;
        (*ats).tv_usec = (*bts).tv_nsec / 1000;
    }
}
