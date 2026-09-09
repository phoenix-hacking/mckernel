// SPDX-License-Identifier: GPL-2.0
//! Versioned, kernel-only application connection to the exact SMP OS owner.

use core::ffi::c_void;

pub(crate) const VERSION: u32 = 1;
pub(crate) const CLEANUP: u32 = 1;
pub(crate) const PREPARE: u32 = 2;
pub(crate) const LOOKUP: u32 = 3;
pub(crate) const TRANSFER: u32 = 4;
pub(crate) const WORKER_OPEN: u32 = 5;
pub(crate) const WORKER_CLOSE: u32 = 6;
pub(crate) const WAIT_SYSCALL: u32 = 7;
pub(crate) const COPIED_SYSCALL: u32 = 8;
pub(crate) const RETURN_SYSCALL: u32 = 9;
pub(crate) const START: u32 = 10;
pub(crate) const PAGER_SYSCALL: u32 = 11;
pub(crate) const CLEAR_SYSCALL: u32 = 12;
pub(crate) const CLEAR_DONE: u32 = 13;

// CLEAR: 40 kernel-only bytes: worker, delivery, accepted output, start, end.
// BEGIN returns the checked range from the retained nr-11 request and reserves
// in-kernel ownership. DONE replaces start with the actual Mirror::clear result
// and clears end; acceptance transfers completion to the continuing pump.
// The caller must retain its worker/MM/connection through the actual clear and
// submit DONE on both success and error. No user pointer or range is an input.

// PAGER: 32 kernel-only bytes, worker/delivery, accepted output, actual result.
// It consumes the exact reserved WAIT packet before any userspace copy. Its
// payload addresses come only from that retained packet, never from this ABI.

// Kernel-only buffers: WORKER_OPEN/CLOSE 16 bytes (tid/handle, output handle);
// WAIT 96 bytes (worker, delivery, original 80-byte copyout); COPIED 24 bytes
// (worker, delivery, successful-copy flag); RETURN 72 bytes (worker, delivery,
// cpu, value, copy destination/length, accepted output flag, up to 16 data bytes).
// Handles originate in the backend and remain attached to referenced Linux
// worker/MM owners. None of these handles are accepted from the user UAPI.

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
