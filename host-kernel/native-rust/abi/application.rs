// SPDX-License-Identifier: GPL-2.0
//! Versioned, kernel-only application connection to the exact SMP OS owner.

use core::ffi::c_void;

pub(crate) const VERSION: u32 = 1;
pub(crate) const CLEANUP: u32 = 1;

// SAFETY: IHK holds the OS operation guard and exact-generation/module lease.
// Success transfers a non-null, concurrency-safe connection; failure leaves
// output null. Acquisition may reserve resources but cannot publish guest work.
pub(crate) type Open = unsafe extern "C" fn(u32, u64, i32, *mut *mut c_void) -> i32;
// SAFETY: The connection and its owners remain live for every concurrent call.
// No OS operation/publication lock is held. Buffer, when a command defines one,
// is exclusive kernel storage borrowed only for this call, never a user pointer.
pub(crate) type Invoke = unsafe extern "C" fn(*mut c_void, u32, *mut u8, usize) -> i64;
// SAFETY: Called once after all invocations end. Close destroys the connection
// before IHK drops its lease. Published work must retain independent ownership.
pub(crate) type Close = unsafe extern "C" fn(*mut c_void);
