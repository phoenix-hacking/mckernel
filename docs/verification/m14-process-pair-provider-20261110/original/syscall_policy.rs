use core::ffi::c_void;
use crate::abi::CInt;
#[no_mangle]
pub unsafe extern "C" fn syscall_find_process_bridge(
    pid: CInt,
    lock_arg: *mut c_void,
) -> *mut c_void {
    // SAFETY: The actual process helper receives the same pid and caller-owned lock
    // node. Its returned pointer and lock ownership are forwarded without new claims.
    unsafe { crate::process_helpers::find_process(pid, lock_arg.cast()).cast() }
}
#[no_mangle]
pub unsafe extern "C" fn syscall_process_unlock_bridge(
    proc: *mut c_void,
    lock_arg: *mut c_void,
) {
    // SAFETY: The existing provider owns the release and IRQ restoration. Raw casts
    // preserve the original ABI and do not create references or acquire another lock.
    unsafe { crate::process_helpers::process_unlock(proc.cast(), lock_arg.cast()) };
}
