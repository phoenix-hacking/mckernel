// SPDX-License-Identifier: GPL-2.0
//! Versioned IHK-to-mcctrl file service boundary; no private Rust layout crosses it.

use core::ffi::c_void;

pub(crate) const VERSION: u32 = 1;

// SAFETY: IHK retains the exact OS lease and the callback module throughout
// open. Success transfers one non-null, concurrency-safe context to IHK;
// failure leaves the output null and retains no context or OS work.
pub(crate) type Open = unsafe extern "C" fn(u32, u64, *mut *mut c_void) -> i32;
// SAFETY: The context belongs to a successful open and remains live until all
// concurrent file operations end. User addresses are borrowed synchronously;
// compat is 0 or 1, with the top-level compat argument already zero-extended.
// No provider-registration, file-publication or OS operation lock is held.
pub(crate) type Ioctl = unsafe extern "C" fn(*mut c_void, u32, u64, u32) -> i64;
// SAFETY: IHK calls close exactly once, after all ioctl borrows finish, while
// both the OS lease and callback module reference are still live. Close must
// retire all context-owned work before returning, without reentering this file.
pub(crate) type Close = unsafe extern "C" fn(*mut c_void);

pub(crate) fn handles(command: u32) -> bool {
    use crate::abi::*;
    matches!(
        command,
        MCEXEC_UP_PREPARE_IMAGE
            | MCEXEC_UP_TRANSFER
            | MCEXEC_UP_START_IMAGE
            | MCEXEC_UP_WAIT_SYSCALL
            | MCEXEC_UP_RET_SYSCALL
            | MCEXEC_UP_LOAD_SYSCALL
            | MCEXEC_UP_SEND_SIGNAL
            | MCEXEC_UP_GET_CPU
            | MCEXEC_UP_STRNCPY_FROM_USER
            | MCEXEC_UP_GET_CRED
            | MCEXEC_UP_GET_CREDV
            | MCEXEC_UP_GET_NODES
            | MCEXEC_UP_GET_CPUSET
            | MCEXEC_UP_CREATE_PPD
            | MCEXEC_UP_PREPARE_DMA
            | MCEXEC_UP_FREE_DMA
            | MCEXEC_UP_OPEN_EXEC
            | MCEXEC_UP_CLOSE_EXEC
            | MCEXEC_UP_SYS_MOUNT
            | MCEXEC_UP_SYS_UMOUNT
            | MCEXEC_UP_SYS_UNSHARE
            | MCEXEC_UP_UTI_GET_CTX
            | MCEXEC_UP_UTI_SWITCH_CTX
            | MCEXEC_UP_SIG_THREAD
            | MCEXEC_UP_SYSCALL_THREAD
            | MCEXEC_UP_TERMINATE_THREAD
            | MCEXEC_UP_GET_NUM_POOL_THREADS
            | MCEXEC_UP_UTI_ATTR
            | MCEXEC_UP_RELEASE_USER_SPACE
            | MCEXEC_UP_DEBUG_LOG
    )
}

pub(crate) fn topology_query(command: u32) -> bool {
    matches!(
        command,
        crate::abi::MCEXEC_UP_GET_CPU | crate::abi::MCEXEC_UP_GET_NODES
    )
}
