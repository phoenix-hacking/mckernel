//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Original void refresh callbacks, using the genuine synchronous guest helpers.
use crate::abi::{CInt, Process, Thread};
use core::{ffi::c_void, mem::offset_of};

/// # Safety
/// The current CPU/thread/process and the existing physical mapping and
/// synchronous offload remain live through return, as required by the original
/// C callback. The matched error-aware getcred producer must be selected.
/// This entry creates no setter serialization, reconciliation or rollback owner.
#[no_mangle]
pub unsafe extern "C" fn do_setresuid() {
    let mut scratch: [CInt; 16] = [0; 16];
    let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
    if cpu.is_null() {
        return;
    }
    let thread = unsafe { (*cpu).current };
    // The genuine helper rejects a null thread or failed snapshot before any
    // field read/write. The private scratch stays live through synchronous use.
    let _ = unsafe {
        crate::syscall_policy::syscall_refresh_cred_fields_body_result(
            thread.cast::<c_void>(),
            scratch.as_mut_ptr(),
            offset_of!(Thread, proc),
            offset_of!(Process, ruid),
            offset_of!(Process, euid),
            offset_of!(Process, suid),
            offset_of!(Process, fsuid),
            0,
            1,
            2,
            3,
            Some(crate::syscall_policy::getcred),
        )
    };
}

/// # Safety
/// Same original current-thread/process and synchronous scratch ownership as
/// do_setresuid, consuming exactly the producer's four gid slots. A failed
/// snapshot produces no guest field writes; the original void ABI drops status.
#[no_mangle]
pub unsafe extern "C" fn do_setresgid() {
    let mut scratch: [CInt; 16] = [0; 16];
    let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
    if cpu.is_null() {
        return;
    }
    let thread = unsafe { (*cpu).current };
    let _ = unsafe {
        crate::syscall_policy::syscall_refresh_cred_fields_body_result(
            thread.cast::<c_void>(),
            scratch.as_mut_ptr(),
            offset_of!(Thread, proc),
            offset_of!(Process, rgid),
            offset_of!(Process, egid),
            offset_of!(Process, sgid),
            offset_of!(Process, fsgid),
            4,
            5,
            6,
            7,
            Some(crate::syscall_policy::getcred),
        )
    };
}

const _: unsafe extern "C" fn() = do_setresuid;
const _: unsafe extern "C" fn() = do_setresgid;
const _: () = {
    assert!(core::mem::size_of::<[CInt; 8]>() == 32);
    assert!(core::mem::size_of::<[CInt; 16]>() == 64);
};
