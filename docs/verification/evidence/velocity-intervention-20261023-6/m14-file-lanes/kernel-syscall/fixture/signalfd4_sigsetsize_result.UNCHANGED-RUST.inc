#[no_mangle]
pub extern "C" fn signalfd4_sigsetsize_result(
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
) -> CInt {
    if sigsetsize != expected_sigset_size {
        -EINVAL
    } else {
        0
    }
}
