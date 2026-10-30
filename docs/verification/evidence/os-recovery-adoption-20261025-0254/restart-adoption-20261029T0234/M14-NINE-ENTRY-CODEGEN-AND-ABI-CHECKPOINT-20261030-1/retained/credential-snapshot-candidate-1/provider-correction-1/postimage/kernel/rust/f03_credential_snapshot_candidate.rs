//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Actual-crate typecheck successor. No owner adapter is supplied or admitted here.
//! f03_credential_snapshot_typecheck retains mangled entries and changes no selector.
//! Reuses original do_setresuid/do_setresgid field mapping, replacing a returned
//! borrowed response pointer with a complete by-value snapshot.
use core::{ffi::c_void, mem::MaybeUninit, ptr::{addr_of_mut, read, write}};
use crate::abi::{CInt, CLong, Process, Thread, X86UserContext};

pub const UID: CInt = 0;
pub const GID: CInt = 1;
pub const READY: CInt = 0;
pub const FAILED: CInt = 1;
pub const UNKNOWN: CInt = 2;
const EFAULT: CInt = 14;
const EIO: CInt = 5;
const EINVAL: CInt = 22;

#[repr(C)]
pub struct CredBegin {
    pub token: *mut c_void,
    pub status: CInt,
    pub reserved: CInt,
}

/// All fields are initialized even for FAILED/UNKNOWN. Values are consumed only
/// for READY/status=0. No returned pointer can outlive its response owner.
#[repr(C)]
#[derive(Clone, Copy)]
pub struct CredReply {
    pub outcome: CInt,
    pub status: CInt,
    pub ids: [CInt; 8],
}

pub struct CredOwnerOps {
    /// Must acquire the SAME process-wide serialization used by all credential
    /// setters before any refresh offload. It may sleep, but never holds the
    /// process update spinlock. A token independently pins process and response.
    /// No token/status<0 means known pre-effect failure; no owner was acquired.
    pub begin: unsafe extern "C" fn(*mut Process, CInt) -> CredBegin,
    /// The adapter retains its own response storage and mapping. It copies a
    /// completed immutable eight-id snapshot into the returned VALUE while that
    /// storage is owned. Never expose a local output/stack pointer to offload.
    /// FAILED requires known stopped/no-effect query; UNKNOWN retains all actual
    /// mappings, tasks, request and storage. A host mutation is never undone here.
    pub snapshot: unsafe extern "C" fn(*mut c_void) -> CredReply,
    /// READY/FAILED release only a known terminal owner after commit/no-write.
    /// UNKNOWN retains/quarantines it and its independent process pin. Nonzero
    /// return MUST also retain the owner. No fabricated ACK or cleanup is valid.
    pub finish: unsafe extern "C" fn(*mut c_void, CInt, CInt) -> CInt,
}

/// Refresh only the captured process; do not reload thread.proc after offload.
/// Failed replies cause no writes: rollback is deferred commit, not restoration
/// of an old snapshot over another thread's valid credentials.
///
/// # Safety
/// Current thread owns its process until the initial hold_process. Every active
/// writer must participate in the real adapter's process-wide serialization;
/// readers requiring an atomic four-field view must use update_lock. These are
/// outstanding integration requirements, not facts established by this source.
pub unsafe fn refresh(thread: *mut Thread, kind: CInt, ops: &CredOwnerOps) -> CInt {
    if thread.is_null() { return -EFAULT; }
    if kind != UID && kind != GID { return -EINVAL; }
    let proc = unsafe { read(core::ptr::addr_of!((*thread).proc)) };
    unsafe { refresh_process(proc, kind, ops) }
}

/// Refresh a captured process. The caller owns a live reference throughout;
/// this helper takes its own pin until its local commit/finish work completes.
/// No current-thread lookup or thread.proc reload occurs in this body.
///
/// # Safety
/// proc is null or an already-owned process; all CredOwnerOps contracts apply.
unsafe fn refresh_process(proc: *mut Process, kind: CInt, ops: &CredOwnerOps) -> CInt {
    if proc.is_null() { return -EFAULT; }
    if kind != UID && kind != GID { return -EINVAL; }
    unsafe { crate::process_helpers::hold_process(proc) };
    let acquired = unsafe { (ops.begin)(proc, kind) };
    let status = if acquired.token.is_null() {
        if acquired.status < 0 { acquired.status } else { -EIO }
    } else if acquired.status != 0 || acquired.reserved != 0 {
        // Malformed acquisition with a real token cannot be assumed unowned.
        let _ = unsafe { (ops.finish)(acquired.token, UNKNOWN, -EIO) };
        -EIO
    } else {
        unsafe { consume_snapshot(proc, kind, acquired.token, ops) }
    };
    unsafe { crate::process_helpers::release_process(proc) };
    status
}


/// Consume the real owner's by-value reply; shared by refresh and the checked
/// ordinary-setter path so both preserve the same deferred-commit behavior.
unsafe fn consume_snapshot(proc: *mut Process, kind: CInt,
    token: *mut c_void, ops: &CredOwnerOps) -> CInt {
    let reply = unsafe { (ops.snapshot)(token) };
    match (reply.outcome, reply.status) {
        (READY, 0) => {
            // Snapshot is already a local VALUE. No pointer to offload
            // storage or user memory is dereferenced in this commit.
            let first = if kind == UID { 0 } else { 4 };
            let selected = [reply.ids[first], reply.ids[first + 1],
                reply.ids[first + 2], reply.ids[first + 3]];
            unsafe { commit(proc, kind, selected) };
            let rc = unsafe { (ops.finish)(token, READY, 0) };
            if rc == 0 { 0 } else { -EIO }
        }
        (FAILED, error) if error < 0 => {
            // This proves only the snapshot query failed. The original setter
            // may already have changed host credentials, so cached guest fields
            // can be stale. Retain the real owner/gate until reconciliation;
            // a known query error is not proof that the setter had no effect.
            let _ = unsafe { (ops.finish)(token, UNKNOWN, error) };
            error
        }
        _ => {
            // Includes a positive/negative nonzero READY status, malformed
            // outcomes, and explicitly unknown host effects. No field read.
            let _ = unsafe { (ops.finish)(token, UNKNOWN, -EIO) };
            -EIO
        }
    }
}

/// Checked ordinary uid/gid setter body: acquire a real owner before forwarding
/// the host mutation, and carry the initially pinned process through snapshot.
/// This is not applicable to setfsuid/setfsgid, whose result is the previous ID.
///
/// # Safety
/// Same process and owner contracts as refresh. The actual owner begin must
/// acquire/attach the real gate BEFORE forward and exclude every other setter.
/// The existing forwarding ABI supplies only a scalar result, not provenance
/// separating a terminal host errno from transport uncertainty. Negative results
/// therefore retain the real owner while preserving the exact caller result.
/// Successful mutation followed by failed/unknown refresh still needs external
/// reconciliation; this checked result does not undo the host credential change.
pub unsafe fn forward_refresh_ordinary(
    thread: *mut Thread, kind: CInt, syscall_nr: CInt, ctx: *mut c_void,
    forward: unsafe extern "C" fn(CInt, *mut c_void) -> CLong,
    ops: &CredOwnerOps,
) -> CLong {
    if thread.is_null() || ctx.is_null() { return -(EFAULT as CLong); }
    if kind != UID && kind != GID { return -(EINVAL as CLong); }
    let proc = unsafe { read(core::ptr::addr_of!((*thread).proc)) };
    if proc.is_null() { return -(EFAULT as CLong); }
    unsafe { crate::process_helpers::hold_process(proc) };
    // Validation and capture precede any possible host side effect.
    let acquired = unsafe { (ops.begin)(proc, kind) };
    let result = if acquired.token.is_null() {
        if acquired.status < 0 { acquired.status as CLong } else { -(EIO as CLong) }
    } else if acquired.status != 0 || acquired.reserved != 0 {
        let _ = unsafe { (ops.finish)(acquired.token, UNKNOWN, -EIO) };
        -(EIO as CLong)
    } else {
        let host_result = unsafe { forward(syscall_nr, ctx) };
        if host_result < 0 {
            // No refresh query or process-field write on a negative result.
            // This raw scalar cannot prove the original host operation stopped
            // without effect: a transport failure can hide an applied setter.
            // Retain the exact owner and preserve the original CLong error.
            let error = CInt::try_from(host_result).unwrap_or(-EIO);
            let _ = unsafe { (ops.finish)(acquired.token, UNKNOWN, error) };
            host_result
        } else if host_result != 0 {
            // These ordinary setters can succeed only with zero. A malformed
            // positive result does not prove a known no-effect failure.
            let _ = unsafe { (ops.finish)(acquired.token, UNKNOWN, -EIO) };
            -(EIO as CLong)
        } else {
            let rc = unsafe { consume_snapshot(proc, kind, acquired.token, ops) };
            if rc != 0 {
                // A host mutation has already succeeded. Do not return normal
                // success with stale guest fields or claim a host rollback.
                #[cfg(not(test))]
                unsafe { f03_cred_refresh_failure_v1(proc, kind, rc) };
            }
            rc as CLong
        }
    };
    unsafe { crate::process_helpers::release_process(proc) };
    result
}

unsafe fn commit(proc: *mut Process, kind: CInt, ids: [CInt; 4]) {
    let mut node = MaybeUninit::<crate::lock_helpers::McsRwlockNodeIrqsave>::uninit();
    let lock: *mut crate::lock_helpers::McsRwlockLock =
        unsafe { addr_of_mut!((*proc).update_lock).cast() };
    unsafe { crate::lock_helpers::__mcs_rwlock_writer_lock(lock, node.as_mut_ptr()) };
    if kind == UID {
        unsafe {
            write(addr_of_mut!((*proc).ruid), ids[0]);
            write(addr_of_mut!((*proc).euid), ids[1]);
            write(addr_of_mut!((*proc).suid), ids[2]);
            write(addr_of_mut!((*proc).fsuid), ids[3]);
        }
    } else {
        unsafe {
            write(addr_of_mut!((*proc).rgid), ids[0]);
            write(addr_of_mut!((*proc).egid), ids[1]);
            write(addr_of_mut!((*proc).sgid), ids[2]);
            write(addr_of_mut!((*proc).fsgid), ids[3]);
        }
    }
    unsafe { crate::lock_helpers::__mcs_rwlock_writer_unlock(lock, node.as_mut_ptr()) };
}

// Adapter symbols are deliberately unresolved. Compositor must not select this
// module until a real reviewed provider and all callers have been integrated.
#[cfg(not(test))]
extern "C" {
    fn f03_cred_owner_begin_v1(proc: *mut Process, kind: CInt) -> CredBegin;
    fn f03_cred_owner_snapshot_v1(token: *mut c_void) -> CredReply;
    fn f03_cred_owner_finish_v1(token: *mut c_void, outcome: CInt, status: CInt) -> CInt;
    // Void legacy ABI cannot propagate errno. Admission must supply a reviewed
    // reconciliation/failure path or migrate every caller to the checked API.
    fn f03_cred_refresh_failure_v1(proc: *mut Process, kind: CInt, status: CInt);
}

#[cfg(not(test))]
unsafe fn current_refresh(kind: CInt) {
    let thread = unsafe { super::current_thread_ptr() };
    // Retain the same process even if an offload changes thread.proc. This pin
    // spans failure reporting; refresh also holds its own shorter local pin.
    if thread.is_null() { return; }
    let proc = unsafe { (*thread).proc };
    if proc.is_null() { return; }
    unsafe { crate::process_helpers::hold_process(proc) };
    let ops = CredOwnerOps {
        begin: f03_cred_owner_begin_v1,
        snapshot: f03_cred_owner_snapshot_v1,
        finish: f03_cred_owner_finish_v1,
    };
    let rc = unsafe { refresh_process(proc, kind, &ops) };
    if rc != 0 { unsafe { f03_cred_refresh_failure_v1(proc, kind, rc) }; }
    unsafe { crate::process_helpers::release_process(proc) };
}

#[cfg(not(test))]
#[cfg_attr(not(f03_credential_snapshot_typecheck), no_mangle)]
pub unsafe extern "C" fn do_setresuid() { unsafe { current_refresh(UID) }; }
#[cfg(not(test))]
#[cfg_attr(not(f03_credential_snapshot_typecheck), no_mangle)]
pub unsafe extern "C" fn do_setresgid() { unsafe { current_refresh(GID) }; }

// Bind actual crate function types rather than synthetic bridge declarations.
const _: unsafe extern "C" fn(*mut Process) = crate::process_helpers::hold_process;
const _: unsafe extern "C" fn(*mut Process) = crate::process_helpers::release_process;
const _: unsafe extern "C" fn(
    *mut crate::lock_helpers::McsRwlockLock,
    *mut crate::lock_helpers::McsRwlockNodeIrqsave,
) = crate::lock_helpers::__mcs_rwlock_writer_lock;
const _: unsafe extern "C" fn(
    *mut crate::lock_helpers::McsRwlockLock,
    *mut crate::lock_helpers::McsRwlockNodeIrqsave,
) = crate::lock_helpers::__mcs_rwlock_writer_unlock;
#[cfg(not(test))]
const _: unsafe extern "C" fn() = do_setresuid;
#[cfg(not(test))]
const _: unsafe extern "C" fn() = do_setresgid;

const _: () = {
    assert!(core::mem::size_of::<CInt>() == 4);
    assert!(core::mem::size_of::<*mut Process>() == 8);
    // Process stores the ABI mirror; the genuine Rust lock helper accepts its
    // own matching definition. Keep this cast tied to both actual layouts.
    assert!(core::mem::size_of::<crate::abi::McsRwlockLock>() ==
        core::mem::size_of::<crate::lock_helpers::McsRwlockLock>());
    assert!(core::mem::align_of::<crate::abi::McsRwlockLock>() ==
        core::mem::align_of::<crate::lock_helpers::McsRwlockLock>());
    assert!(core::mem::size_of::<crate::abi::McsRwlockLock>() == 64);
    assert!(core::mem::align_of::<crate::abi::McsRwlockLock>() == 64);
    assert!(core::mem::align_of::<crate::lock_helpers::McsRwlockNodeIrqsave>() == 64);
    assert!(core::mem::size_of::<CredReply>() == 40);
    assert!(core::mem::align_of::<CredReply>() == 4);
    assert!(core::mem::offset_of!(CredReply, ids) == 8);
    assert!(core::mem::size_of::<CredBegin>() == 16);
    assert!(core::mem::align_of::<CredBegin>() == 8);
    assert!(core::mem::offset_of!(CredBegin, token) == 0);
    assert!(core::mem::offset_of!(CredBegin, reserved) == 12);
    assert!(core::mem::offset_of!(CredBegin, status) == 8);
};

// Private checked caller candidates. Mangled Rust symbols only: neither replaces
// the original sys_setresuid/sys_setresgid entry or any production selector.
#[cfg(not(test))]
unsafe fn checked_current_setter(kind: CInt, number: CInt,
    ctx: *mut X86UserContext) -> CLong {
    let ops = CredOwnerOps {
        begin: f03_cred_owner_begin_v1,
        snapshot: f03_cred_owner_snapshot_v1,
        finish: f03_cred_owner_finish_v1,
    };
    unsafe { forward_refresh_ordinary(super::current_thread_ptr(), kind, number,
        ctx.cast(), super::syscall_policy_forward_context_bridge, &ops) }
}

#[cfg(not(test))]
pub unsafe extern "C" fn f03_sys_setresuid_checked_v1(
    _n: CInt, ctx: *mut X86UserContext) -> CLong {
    unsafe { checked_current_setter(UID, super::SYS_SETRESUID, ctx) }
}

#[cfg(not(test))]
pub unsafe extern "C" fn f03_sys_setresgid_checked_v1(
    _n: CInt, ctx: *mut X86UserContext) -> CLong {
    unsafe { checked_current_setter(GID, super::SYS_SETRESGID, ctx) }
}

#[cfg(not(test))]
const _: unsafe extern "C" fn(CInt, *mut c_void) -> CLong =
    super::syscall_policy_forward_context_bridge;
#[cfg(not(test))]
const _: unsafe extern "C" fn(CInt, *mut X86UserContext) -> CLong =
    f03_sys_setresuid_checked_v1;
#[cfg(not(test))]
const _: unsafe extern "C" fn(CInt, *mut X86UserContext) -> CLong =
    f03_sys_setresgid_checked_v1;
