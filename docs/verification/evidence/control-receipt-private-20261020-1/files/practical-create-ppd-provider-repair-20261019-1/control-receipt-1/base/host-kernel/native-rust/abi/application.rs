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

// BEGIN PRIVATE FORK ADOPTION ABI V1
// Dedicated kernel-only callback ABI; Invoke commands 1-14 remain unchanged.
// Geometry follows the native prepare_process header (rpgtable, start, len).
#[repr(C)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ForkGeometryV1 {
    pub(crate) root: u64,
    pub(crate) start: u64,
    pub(crate) length: u64,
}

// Scalar comparison keys, never ownership or addresses to dereference.
#[repr(C)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ForkIdentityV1 {
    pub(crate) slot: u32,
    pub(crate) reserved0: u32,
    pub(crate) generation: u64,
    pub(crate) parent: u64,
    pub(crate) worker: u64,
    pub(crate) delivery: u64,
    pub(crate) child: u64,
    pub(crate) child_pid: i32,
    pub(crate) reserved1: u32,
    pub(crate) child_mm: u64,
    pub(crate) root: u64,
    pub(crate) start: u64,
    pub(crate) length: u64,
    pub(crate) nonce: u64,
}

// BORROWED only for one synchronous callback. The provider retains the actual
// PreparedForkLease, its preallocated flag, exact OS/module and admission hold.
// The consumer must not retain the descriptor, context, flag or any reference.
// After validating every identity/geometry field and before touching the MM,
// its non-Copy scoped capability may perform ONLY the inline Release store at
// the infallible VMA commit. No callback, allocation, lock or Drop runs there.
#[repr(C)]
pub(crate) struct ForkSealV1 {
    pub(crate) version: u32,
    pub(crate) bytes: u32,
    pub(crate) identity: ForkIdentityV1,
    pub(crate) sealed: *mut core::sync::atomic::AtomicBool,
}

pub(crate) type ForkAdoptConsumerV1 = unsafe extern "C" fn(*mut c_void, *mut ForkSealV1) -> i32;
// Both contexts are live successful opens of the same provider/OS generation.
// No operations, registry, provider or Remote slots lock spans this call or its
// consumer callback. The caller pins its consumer module and borrows stack
// context and both connections until callback return. All descriptor pointers
// are private borrowed kernel storage; no public user opcode is added.
pub(crate) type ForkAdoptV1 = unsafe extern "C" fn(
    *mut c_void,
    *mut c_void,
    *const ForkGeometryV1,
    Option<ForkAdoptConsumerV1>,
    *mut c_void,
) -> i32;
// END PRIVATE FORK ADOPTION ABI V1

// BEGIN PRIVATE FORK PROGRESS ABI V1
pub(crate) const FORK_HOST_REVOKED_V1: u32 = 1;
pub(crate) const FORK_GUEST_DESTROYED_V1: u32 = 2;
// An original do_fork consumes this terminal cancellation before final ACK.
// Do not use -ERESTARTSYS: the original child must be destroyed exactly once.
pub(crate) const FORK_ABORT_RETURN_V1: i64 = -125;

// SAFETY: A private typed context retains the exact Registration, referenced
// producer proof and caller Linux module for this synchronous borrow. Stage1
// runs only AFTER provider abort/drain and performs the real Mirror alias/TLB
// revoke before success. A retry may check that same cached non-Copy receipt.
// Stage2 accepts ONLY an authenticated original in-band caller's final thread
// AND VM destruction result2 for every immutable identity field. A host revoke
// receipt alone cannot construct that proof. No user pointer/bool is authority.
// No proof/context pointer may escape, and no dependent lock spans this call.
pub(crate) type ForkVerifyV1 = unsafe extern "C" fn(*mut c_void, *const ForkIdentityV1) -> i32;
// Dedicated private progress; this is never an application Invoke opcode.
// The child connection remains live and caller module-pinned through return.
// The provider owns the exact pending transaction and all phase transitions;
// it must call verify only outside OS/table/Remote locks, then revalidate.
pub(crate) type ForkProgressV1 = unsafe extern "C" fn(
    *mut c_void,
    *const ForkIdentityV1,
    u32,
    Option<ForkVerifyV1>,
    *mut c_void,
) -> i32;
// END PRIVATE FORK PROGRESS ABI V1

// BEGIN PRIVATE FORK CONSUMER CAPSULE ABI V1
// IHK acquires the consumer's Linux module reference BEFORE Construct. Seed is
// borrowed only for construction; successful non-null output transfers exactly
// one opaque consumer Box. Error with non-null output also transfers cleanup.
pub(crate) type ForkCapsuleConstructV1 = unsafe extern "C" fn(*mut c_void, *mut *mut c_void) -> i32;
// The actual PreparedForkLease supplies this full-key preview synchronously
// BEFORE any MM effect. It allocates storage only: actual ForkClaim/receipt
// validation remains mandatory for every later verifier/Accept. No phase0
// initializing entry permits progress. NULL/error transfer rules match v1.
pub(crate) type ForkInitialConstructV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkIdentityV1, *mut *mut c_void,
) -> i32;
// IHK invokes Destroy outside every dependent lock while its own module pin is
// live, then calls module_put from IHK text after Destroy returns. No owned
// ModuleLease or Rust owner crosses this ABI, and consumer Drop releases none.
pub(crate) type ForkCapsuleDestroyV1 = unsafe extern "C" fn(*mut c_void);
// Only IHK calls Accept AFTER durable exact-key final ACK and backend Released.
// A matching already-accepted context is idempotent; failure retains context,
// module and OS/provider ownership for an Accept-only retry. This cannot itself
// run guest cleanup/destruction. No caller boolean grants final acceptance.
pub(crate) type ForkCapsuleAcceptV1 = unsafe extern "C" fn(*mut c_void, *const ForkIdentityV1) -> i32;
// END PRIVATE FORK CONSUMER CAPSULE ABI V1

// BEGIN PRIVATE FORK LINK ABI V1
// Borrowed only through one synchronous, module-pinned callback. The SAME
// preallocated gate permits OPEN(0)->CANCELLED(1) or OPEN(0)->SEALED(2).
// SEALED is irreversible: only this exact kind2/result0 transaction may retry.
#[repr(C)]
pub(crate) struct ForkLinkSealV1 {
    pub(crate) version: u32,
    pub(crate) bytes: u32,
    pub(crate) identity: ForkIdentityV1,
    pub(crate) second_worker: u64,
    pub(crate) second_delivery: u64,
    pub(crate) second_cpu: i32,
    pub(crate) reserved: u32,
    pub(crate) carrier_physical: u64,
    pub(crate) carrier_sequence: u64,
    pub(crate) gate: *mut core::sync::atomic::AtomicU8,
}
// Full referenced child PID/MM/VMA validation precedes the ONLY inline gate
// CAS under MM write exclusion. No lock/allocation/callback/Drop under that CAS.
pub(crate) type ForkCapsuleLinkV1 = unsafe extern "C" fn(*mut c_void, *mut ForkLinkSealV1) -> i32;
// Backend derives the exact key/ticket first. IHK then claims its actual
// pending capsule/payload, invokes stored consumer verification, and calls the
// SAME trusted provider continuation while every owner/module pin stays live.
// Ticket/payload contexts are borrowed only until Finish returns; no callback
// pointer or stack context is stored. SEALED failures retain the durable ticket.
pub(crate) type ForkLinkFinishV1 = unsafe extern "C" fn(*mut c_void, *mut c_void) -> i32;
pub(crate) type ForkLinkResolveV1 = unsafe extern "C" fn(
    *mut c_void, *mut ForkLinkSealV1, Option<ForkLinkFinishV1>, *mut c_void,
) -> i32;
pub(crate) type ForkPrepareLinkV1 = unsafe extern "C" fn(
    *mut c_void, u64, u64, i64, i64, Option<ForkLinkResolveV1>, *mut c_void,
) -> i32;
// END PRIVATE FORK LINK ABI V1

// BEGIN PRIVATE FORK PAYLOAD CAPSULE ABI V1
// Construct starts with a NULL output. Non-NULL transfers exactly one opaque
// context even on error; NULL on error guarantees no remaining claim/context.
// IHK reserves capsule storage BEFORE construction under its real independent
// admission/OS/provider hold. No owned Rust/module/OS lease crosses this ABI.
pub(crate) type ForkPayloadConstructV1 = unsafe extern "C" fn(*mut c_void, *mut *mut c_void) -> i32;
// 0 consumes the context/claim exactly once. Negative retains it unchanged;
// positive is a protocol error and retains it. IHK calls outside all guards,
// with provider ownership live until callback return. Abort is preseal only,
// BEFORE publication unfreeze; Complete additionally needs authenticated final
// destruction AND actual final RET publication, never stage2 proof alone.
pub(crate) type ForkPayloadDropV1 = unsafe extern "C" fn(*mut c_void) -> i32;
pub(crate) type ForkPayloadAttachV1 = unsafe extern "C" fn(
    *mut c_void, Option<ForkPayloadConstructV1>, *mut c_void,
    Option<ForkPayloadDropV1>, Option<ForkPayloadDropV1>, *mut *mut c_void,
) -> i32;
// BORROWED stack scope only. Seed/outparams/scope never escape synchronous
// attach. The returned context is borrowed under the live exact capsule epoch;
// all SMP ticket/ChildFork pointers must clear BEFORE Abort/Complete frees it.
#[repr(C)]
pub(crate) struct ForkPayloadScopeV1 {
    pub(crate) version: u32,
    pub(crate) bytes: u32,
    pub(crate) slot: u32,
    pub(crate) reserved0: u32,
    pub(crate) generation: u64,
    pub(crate) epoch: u64,
    pub(crate) context: *mut c_void,
    pub(crate) attach: Option<ForkPayloadAttachV1>,
}
pub(crate) type ForkAdoptScopedV1 = unsafe extern "C" fn(
    *mut c_void, *mut c_void, *const ForkGeometryV1, *mut ForkPayloadScopeV1,
    Option<ForkAdoptConsumerV1>, *mut c_void,
) -> i32;
// END PRIVATE FORK PAYLOAD CAPSULE ABI V1

// BEGIN PRIVATE FORK FINALIZATION ABI V1
// The IHK claim, never the caller, selects its exact owned payload context.
// The provider materializes a short exclusive borrow only under its slots
// lock. Stage1 writes kind3/-125 before permitting the original negative RET.
pub(crate) type ForkProgressPayloadV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkIdentityV1, u32, Option<ForkVerifyV1>, *mut c_void,
    *mut c_void,
) -> i32;

// Borrowed metadata from the actual owned selector3 delivery. Header bytes
// alone are not a guest destruction proof; its trusted provider ticket must
// validate the retained carrier and original in-band checked result2 producer.
#[repr(C)]
pub(crate) struct ForkGuestAckV1 {
    pub(crate) version: u32,
    pub(crate) bytes: u32,
    pub(crate) identity: ForkIdentityV1,
    pub(crate) epoch: u64,
    pub(crate) worker: u64,
    pub(crate) delivery: u64,
    pub(crate) cpu: i32,
    pub(crate) reserved: u32,
    pub(crate) physical: u64,
    pub(crate) sequence: u64,
}
pub(crate) type ForkAckVerifyV1 = unsafe extern "C" fn(*mut c_void, *mut c_void) -> i32;
pub(crate) type ForkAckFinishV1 = unsafe extern "C" fn(*mut c_void) -> i32;
pub(crate) type ForkAckResolveV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkGuestAckV1, Option<ForkAckVerifyV1>,
    Option<ForkAckFinishV1>, *mut c_void,
) -> i32;
pub(crate) type ForkPrepareAckV1 = unsafe extern "C" fn(
    *mut c_void, u64, u64, i64, i64, Option<ForkAckResolveV1>, *mut c_void,
) -> i32;
// These immutable registered callbacks validate the actual durable publication
// record and later retire that exact backend owner. IHK invokes neither under
// its table lock. Receipt contexts are synchronous borrows, never owned leases.
pub(crate) type ForkPublicationVerifyV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkIdentityV1, u64, *mut c_void,
) -> i32;
pub(crate) type ForkReleaseAckV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkIdentityV1, u64,
) -> i32;
// END PRIVATE FORK FINALIZATION ABI V1

// Distinct synchronous, park-only control ABI. No receipt/MM/terminal authority.
#[repr(C)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) struct ForkControlV1 {
    pub(crate) version: u32,
    pub(crate) bytes: u32,
    pub(crate) identity: ForkIdentityV1,
    pub(crate) epoch: u64,
    pub(crate) worker: u64,
    pub(crate) delivery: u64,
    pub(crate) cpu: i32,
    pub(crate) reserved: u32,
    pub(crate) physical: u64,
    pub(crate) response: u64,
}
// Payload is a shared metadata borrow owned by the exact IHK pending claim.
// No pointer, claim or ticket may escape either synchronous callback.
pub(crate) type ForkControlParkV1 = unsafe extern "C" fn(*mut c_void, *const c_void) -> i32;
pub(crate) type ForkControlResolveV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkControlV1, Option<ForkControlParkV1>, *mut c_void,
) -> i32;
pub(crate) type ForkPrepareControlV1 = unsafe extern "C" fn(
    *mut c_void, u64, u64, i64, i64, Option<ForkControlResolveV1>, *mut c_void,
) -> i32;
