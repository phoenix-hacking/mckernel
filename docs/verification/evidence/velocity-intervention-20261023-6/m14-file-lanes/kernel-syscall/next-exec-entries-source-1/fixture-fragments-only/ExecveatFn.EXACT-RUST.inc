type ExecveatFn = unsafe extern "C" fn(
    *mut c_void,
    CInt,
    *const c_void,
    *mut *mut c_void,
    *mut *mut c_void,
    CInt,
) -> CInt;
