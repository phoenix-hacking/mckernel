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
pub(crate) const TID_TRANSFER: u32 = 14;

// Explicit preparation-only extension over the existing v6 Invoke callback.
// It never grants VMA adoption, a positive clone result, runnable credit or ACK.
#[repr(C)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ForkGeometryV3 { pub root:u64, pub start:u64, pub length:u64 }
#[repr(C)]
pub(crate) struct ForkPreparedV3 {
    pub geometry: ForkGeometryV3, pub child_pid:i32, pub reserved:u32,
    pub child_mm:u64, pub response:u64, pub nonce:u64,
}
// v4 adds an actual owned lease transfer and an infallible one-shot seal.
// Frozen v3 preparation remains separate evidence. This ABI grants no final ACK,
// runnable credit, root destruction or a fabricated positive clone response.
pub(crate) const FORK_ADOPT_CURRENT_V4:u32=16;
pub(crate) type ForkSealCommitV4=unsafe extern "C" fn(*mut c_void);
pub(crate) type ForkLeaseReleaseV4=unsafe extern "C" fn(*mut c_void);
#[repr(C)]
pub(crate) struct ForkSealV4 {
    pub prepared:ForkPreparedV3,pub seal:Option<ForkSealCommitV4>,pub context:*mut c_void,
}
pub(crate) type ForkAdoptConsumerV4=unsafe extern "C" fn(*mut c_void,*const ForkSealV4)->i32;
#[repr(C)]
pub(crate) struct ForkAdoptCallV4 {
    pub version:u32,pub bytes:u32,pub child:*mut c_void,pub geometry:ForkGeometryV3,
    pub consumer:Option<ForkAdoptConsumerV4>,pub context:*mut c_void,
    // Real preallocated IHK lease object. Provider takes it by nulling BOTH
    // fields, before any seal/VMA effect. It is never a numeric lease token.
    pub lease:*mut c_void,pub release_lease:Option<ForkLeaseReleaseV4>,
}

// TID_TRANSFER: worker/delivery/physical/direction in 32 kernel-only bytes,
// followed by the complete copied launcher TID array. The backend checks the
// exact Delivered nr-186 request, count and destination before any guest write.
// This does not complete the syscall; the original launcher RET still owns its
// result. Handles are taken only from the referenced current Linux worker.

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

// Explicit current control ABI. The v6 callback table and v4 adoption ABI are
// unchanged. An owned capsule transfers before revoke; no scalar creates one.
pub(crate) const FORK_CONTROL_CURRENT_V1:u32=18;
#[repr(C)]
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct ForkControlIdentityV1 {
    pub slot:u32,pub child_pid:i32,pub generation:u64,pub parent:u64,
    pub worker:u64,pub delivery:u64,pub child:u64,pub child_mm:u64,
    pub root:u64,pub start:u64,pub length:u64,pub nonce:u64,
}
#[repr(C)]
#[derive(Clone,Copy)]
pub(crate) struct ForkRevokeClaimV1 {pub identity:ForkControlIdentityV1,pub carrier:u64}
pub(crate) type ForkRevokeV1=unsafe extern "C" fn(*mut c_void,*const ForkRevokeClaimV1)->i32;
pub(crate) type ForkAcceptV1=unsafe extern "C" fn(*mut c_void)->i32;
#[repr(C)]
pub(crate) struct ForkControlCallV1 {
    pub version:u32,pub bytes:u32,pub child:*mut c_void,pub worker:u64,pub delivery:u64,
    pub owner:*mut c_void,pub revoke:Option<ForkRevokeV1>,pub accept:Option<ForkAcceptV1>,
    pub release:Option<ForkLeaseReleaseV4>,
}
