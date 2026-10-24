#[no_mangle]
pub extern "C" fn signalfd4_flags_result(flags: CInt) -> CInt {
    if (flags & !(SFD_NONBLOCK | SFD_CLOEXEC)) != 0 {
        -EINVAL
    } else {
        0
    }
}
