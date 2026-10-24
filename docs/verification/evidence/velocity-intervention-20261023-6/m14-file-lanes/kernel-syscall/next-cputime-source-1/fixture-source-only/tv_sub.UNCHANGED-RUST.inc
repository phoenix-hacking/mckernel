#[no_mangle]
pub unsafe extern "C" fn tv_sub(ats: *mut TimeVal, bts: *const TimeVal) {
    unsafe {
        (*ats).tv_sec = (*ats).tv_sec.wrapping_sub((*bts).tv_sec);
        (*ats).tv_usec = (*ats).tv_usec.wrapping_sub((*bts).tv_usec);
        while (*ats).tv_usec < 0 {
            (*ats).tv_sec = (*ats).tv_sec.wrapping_sub(1);
            (*ats).tv_usec = (*ats).tv_usec.wrapping_add(US_PER_SEC);
        }
    }
}
