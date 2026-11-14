//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Default-off credential field entry wrappers, reusing the existing refresh body.
use core::{ffi::c_void, mem::{offset_of, MaybeUninit}};
use crate::abi::{CInt, Process, Thread};

/// # Safety
/// The current CPU, thread, process, borrowed scratch and existing getcred
/// synchronous endpoint remain live. The response producer must initialize all
/// four selected fields before the existing refresh helper reads them. Caller
/// retains original field exclusion/validation; no failed response is repaired.
#[no_mangle]
pub unsafe extern "C" fn do_setresuid() {
    let mut scratch = MaybeUninit::<[CInt; 16]>::uninit();
    let thread = unsafe { (*super::get_this_cpu_local_var()).current };
    // SAFETY: Same current thread, stack allocation, indices and getcred provider;
    // no reference to the uninitialized scratch or added null/error policy.
    let _ = unsafe { super::syscall_refresh_cred_fields_body_result(
        thread.cast::<c_void>(), scratch.as_mut_ptr().cast::<CInt>(),
        offset_of!(Thread, proc), offset_of!(Process, ruid), offset_of!(Process, euid),
        offset_of!(Process, suid), offset_of!(Process, fsuid), 0, 1, 2, 3, Some(super::getcred),
    ) };
}

/// # Safety
/// Same current/endpoint and scratch ownership as the uid entry, but the producer
/// must initialize credential slots four through seven before their consumption.
#[no_mangle]
pub unsafe extern "C" fn do_setresgid() {
    let mut scratch = MaybeUninit::<[CInt; 16]>::uninit();
    let thread = unsafe { (*super::get_this_cpu_local_var()).current };
    // SAFETY: Exact existing helper, original field order and gid value indices.
    let _ = unsafe { super::syscall_refresh_cred_fields_body_result(
        thread.cast::<c_void>(), scratch.as_mut_ptr().cast::<CInt>(),
        offset_of!(Thread, proc), offset_of!(Process, rgid), offset_of!(Process, egid),
        offset_of!(Process, sgid), offset_of!(Process, fsgid), 4, 5, 6, 7, Some(super::getcred),
    ) };
}
const _: unsafe extern "C" fn() = do_setresuid;
const _: unsafe extern "C" fn() = do_setresgid;
