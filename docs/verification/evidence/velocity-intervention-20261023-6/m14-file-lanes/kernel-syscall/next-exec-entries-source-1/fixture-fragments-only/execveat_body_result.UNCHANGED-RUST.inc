#[no_mangle]
pub unsafe extern "C" fn execveat_body_result(
    ctx: *mut c_void,
    dirfd: CInt,
    filename: *const c_void,
    argv: *mut *mut c_void,
    envp: *mut *mut c_void,
    flags: CInt,
    filename_first: CInt,
    execveat_fn: Option<ExecveatFn>,
) -> CLong {
    let error = execveat_policy_result(flags, dirfd, filename_first);
    if error != 0 {
        return error as CLong;
    }
    let Some(execveat) = execveat_fn else {
        return -(EFAULT as CLong);
    };

    execveat(ctx, dirfd, filename, argv, envp, flags) as CLong
}
