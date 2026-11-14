#[no_mangle]
pub unsafe extern "C" fn execve_body_result(
    ctx: *mut c_void,
    filename: *const c_void,
    argv: *mut *mut c_void,
    envp: *mut *mut c_void,
    execveat_fn: Option<ExecveatFn>,
) -> CLong {
    let Some(execveat) = execveat_fn else {
        return -(EFAULT as CLong);
    };

    execveat(ctx, AT_FDCWD, filename, argv, envp, 0) as CLong
}
