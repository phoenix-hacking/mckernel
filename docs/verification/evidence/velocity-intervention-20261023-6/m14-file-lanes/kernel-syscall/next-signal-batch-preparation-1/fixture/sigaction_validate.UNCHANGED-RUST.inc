#[no_mangle]
pub extern "C" fn sigaction_validate(sig: CInt, has_act: CInt) -> CInt {
    if sig < 1 || sig > NSIG {
        return -EINVAL;
    }

    if has_act != 0 && (sig == SIGKILL || sig == SIGSTOP) {
        return -EINVAL;
    }

    0
}
