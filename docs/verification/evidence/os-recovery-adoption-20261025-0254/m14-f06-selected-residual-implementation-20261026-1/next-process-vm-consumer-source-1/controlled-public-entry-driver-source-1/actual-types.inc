type ProcessVmRwFn =
    unsafe extern "C" fn(CInt, *const c_void, CULong, *const c_void, CULong, CULong, CInt) -> CInt;
type ArchProcessVmRwLockFn = unsafe extern "C" fn(*mut c_void);
type ArchProcessVmRwLookupRangeFn =
    unsafe extern "C" fn(*mut c_void, CULong, CULong) -> *mut c_void;
type ArchProcessVmRwFindProcessFn = unsafe extern "C" fn(CInt, *mut c_void) -> *mut c_void;
type ArchProcessVmRwProcessUnlockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ArchProcessVmRwProcessLockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ArchProcessVmRwVmVoidFn = unsafe extern "C" fn(*mut c_void);
type ArchProcessVmRwVtopFn =
    unsafe extern "C" fn(*mut c_void, CULong, *mut CULong, *mut CULong) -> CInt;
type ArchProcessVmRwFaultFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> CInt;
type ArchProcessVmRwPhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ArchProcessVmRwMemcpyFn = unsafe extern "C" fn(*mut c_void, *const c_void, SizeT);
type ArchProcessVmRwLogFn = unsafe extern "C" fn(*const ArchProcessVmRwLogRecord);
