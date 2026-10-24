#[no_mangle]
pub unsafe extern "C" fn ts_add(ats: *mut TimeSpec, bts: *const TimeSpec) {
    unsafe {
        (*ats).tv_sec = (*ats).tv_sec.wrapping_add((*bts).tv_sec);
        (*ats).tv_nsec = (*ats).tv_nsec.wrapping_add((*bts).tv_nsec);
        while (*ats).tv_nsec >= NS_PER_SEC {
            (*ats).tv_sec = (*ats).tv_sec.wrapping_add(1);
            (*ats).tv_nsec = (*ats).tv_nsec.wrapping_sub(NS_PER_SEC);
        }
    }
}
