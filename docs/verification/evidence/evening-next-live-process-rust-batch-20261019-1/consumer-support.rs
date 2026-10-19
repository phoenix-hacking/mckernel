type ProcessRefDecAndTestFn = unsafe extern "C" fn(*mut c_void, CULong) -> CInt;
type ProcessCurrentResourceSetFn = unsafe extern "C" fn() -> *mut c_void;
type ProcessResourceProcessActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessProcessActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessResourceSetActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessThreadActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessSpinLockFn = unsafe extern "C" fn(CULong) -> CULong;
type ProcessSpinUnlockFn = unsafe extern "C" fn(CULong, CULong);
type ProcessFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessMckfdFreeFn = unsafe extern "C" fn(*mut c_void);

unsafe extern "C" {
fn process_release_process_body_result(
    proc: *mut c_void,
    refcount_offset: CULong,
    tids_offset: CULong,
    main_thread_offset: CULong,
    mckfd_offset: CULong,
    mckfd_lock_offset: CULong,
    mckfd_next_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    current_resource_set_fn: Option<ProcessCurrentResourceSetFn>,
    hash_detach_fn: Option<ProcessResourceProcessActionFn>,
    sibling_detach_fn: Option<ProcessProcessActionFn>,
    profile_fn: Option<ProcessProcessActionFn>,
    free_thread_pages_fn: Option<ProcessThreadActionFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    mckfd_free_fn: Option<ProcessMckfdFreeFn>,
    free_fn: Option<ProcessFreeFn>,
    final_cleanup_fn: Option<ProcessResourceSetActionFn>,
) -> CInt;
    fn process_current_resource_set_bridge() -> *mut c_void;
    fn process_release_profile_bridge(proc: *mut c_void);
    fn process_release_final_cleanup_bridge(resource_set: *mut c_void);
    fn process_free_thread_pages_bridge(thread: *mut c_void);
    fn process_mckfd_free_bridge(fdp: *mut c_void);
    fn process_optional_free_bridge(ptr: *mut c_void);
fn process_spin_lock_bridge(lock_addr: CULong) -> CULong;
fn process_spin_unlock_bridge(lock_addr: CULong, irqstate: CULong);
}
