// SPDX-License-Identifier: GPL-2.0
//! Native per-process executable and application ownership across OS files.

use super::{application_image as image, mcctrl_exec::Executable, mcctrl_vm::Mirror};
use core::{
    ffi::c_void,
    pin::Pin,
    ptr::{self, NonNull},
    sync::atomic::{AtomicBool, AtomicI32, AtomicPtr, AtomicU64, Ordering},
};
use kernel::{
    bindings,
    prelude::*,
    sync::{new_mutex, Arc, Mutex},
    uaccess::UserSlice,
};

// SAFETY: IHK is the real namespaced module dependency. These operations use
// only kernel-owned output/connection storage and retain exact OS/backend owners.
extern "C" {
    fn ihk_os_application_open_v1(
        slot: u32,
        generation: u64,
        version: u32,
        pid: i32,
        output: *mut *mut c_void,
    ) -> i32;
    fn ihk_os_application_invoke_v1(
        context: *mut c_void,
        command: u32,
        buffer: *mut u8,
        bytes: usize,
    ) -> i64;
    fn ihk_os_application_close_v1(context: *mut c_void);
    #[allow(dead_code)]
    fn ihk_os_application_adopt_fork_v1(parent: *mut c_void, child: *mut c_void,
        geometry: *const super::application_abi::ForkGeometryV1,
        consumer: Option<super::application_abi::ForkAdoptConsumerV1>, context: *mut c_void) -> i32;
    fn ihk_os_application_fork_progress_v1(child: *mut c_void,
        identity: *const super::application_abi::ForkIdentityV1, stage: u32,
        verify: Option<super::application_abi::ForkVerifyV1>, context: *mut c_void) -> i32;
    #[allow(dead_code)]
    fn ihk_os_application_attach_fork_capsule_v1(child: *mut c_void,
        identity: *const super::application_abi::ForkIdentityV1, module: *mut c_void,
        construct: Option<super::application_abi::ForkCapsuleConstructV1>, seed: *mut c_void,
        destroy: Option<super::application_abi::ForkCapsuleDestroyV1>,
        verify: Option<super::application_abi::ForkVerifyV1>,
        accept: Option<super::application_abi::ForkCapsuleAcceptV1>) -> i32;
    fn ihk_os_application_cancel_fork_capsule_v1(child: *mut c_void,
        identity: *const super::application_abi::ForkIdentityV1) -> i32;
    fn ihk_os_application_attach_fork_capsule_v2(child: *mut c_void,
        identity: *const super::application_abi::ForkIdentityV1, module: *mut c_void,
        construct: Option<super::application_abi::ForkCapsuleConstructV1>, seed: *mut c_void,
        destroy: Option<super::application_abi::ForkCapsuleDestroyV1>,
        verify: Option<super::application_abi::ForkVerifyV1>,
        accept: Option<super::application_abi::ForkCapsuleAcceptV1>,
        link: Option<super::application_abi::ForkCapsuleLinkV1>) -> i32;
    fn ihk_os_application_prepare_fork_link_v1(parent: *mut c_void,
        worker: u64, serial: u64, cpu: i64, value: i64) -> i32;
    fn ihk_os_application_prepare_fork_control_v1(parent: *mut core::ffi::c_void, worker: u64, serial: u64, cpu: i64, value: i64) -> i32;
    fn ihk_os_application_prepare_fork_ack_v1(parent: *mut c_void,
        worker: u64, serial: u64, cpu: i64, value: i64) -> i32;
    fn ihk_os_application_adopt_fork_v2(parent: *mut c_void, child: *mut c_void,
        geometry: *const super::application_abi::ForkGeometryV1, module: *mut c_void,
        initial: Option<super::application_abi::ForkInitialConstructV1>, seed: *mut c_void,
        destroy: Option<super::application_abi::ForkCapsuleDestroyV1>,
        verify: Option<super::application_abi::ForkVerifyV1>,
        accept: Option<super::application_abi::ForkCapsuleAcceptV1>,
        link: Option<super::application_abi::ForkCapsuleLinkV1>,
        consumer: Option<super::application_abi::ForkAdoptConsumerV1>, context: *mut c_void) -> i32;
}

// BEGIN PREPARED FORK CONSUMER CONTRACT
/// Decoded legacy CREATE_PPD geometry; it contains no authority by itself.
#[derive(Clone, Copy)]
pub(super) struct ForkDescriptor {
    pub(super) start: u64,
    pub(super) length: u64,
    pub(super) root: u64,
}

#[allow(dead_code)]
impl ForkDescriptor {
    fn read(argument: usize, compat: bool) -> Result<Self> {
        if argument == 0 { return Err(EINVAL); }
        let mut bytes = [0u8; 24];
        let width = if compat { 4 } else { 8 };
        UserSlice::new(argument, width * 3).reader().read_slice(&mut bytes[..width * 3])?;
        let mut words = [0u64; 3];
        for (index, word) in words.iter_mut().enumerate() {
            let start = index * width;
            *word = if compat {
                u32::from_le_bytes(bytes[start..start + 4].try_into().unwrap()) as u64
            } else {
                u64::from_le_bytes(bytes[start..start + 8].try_into().unwrap())
            };
        }
        let descriptor = Self { root: words[0], start: words[1], length: words[2] };
        descriptor.end()?;
        Ok(descriptor)
    }

    fn end(self) -> Result<u64> {
        if self.start % 4096 != 0 || self.length == 0 || self.length % 4096 != 0
            || self.root == 0 || self.root % 4096 != 0 { return Err(EINVAL); }
        self.start.checked_add(self.length).ok_or(EINVAL)
    }
}

/// An owned, exclusive backend capability. There is deliberately no mcctrl
/// implementation or production constructor while fork activation is gated.
///
/// # Safety
/// The producer must pin exact original parent delivery/nonce/OS generation,
/// child Registration/PID/MM and root/range ownership. While the lease lives,
/// cancellation may become pending but cannot invalidate its Reserved phase.
/// seal must only perform an infallible nonblocking transition: no Result,
/// panic, lock, allocation, external call, cancellation processing or final
/// owner destructor. It retains all owners until inherit_vmas has unlocked.
/// finish and Drop run outside MM/publication locks. They must retain every
/// adopted/cancelled root and transaction until actual host revocation and the
/// exact final guest destructor/ACK; ordinary abort is not physical release.
#[allow(dead_code)]
pub(super) unsafe trait PreparedForkLease {
    fn seal(&mut self);
    fn finish(self) where Self: Sized;
}

/// Bridge authority is backend-owned, never reconstructed from user geometry.
///
/// # Safety
/// reserve must authenticate and pin all PreparedForkLease identities against
/// one unique retained delivered parent clone. It runs without MM/publication
/// locks. Returning Err may not publish a child or release an uncertain root.
#[allow(dead_code)]
pub(super) unsafe trait ForkBackend {
    type Lease: PreparedForkLease;
    fn reserve(&self, parent: &Arc<Registration>, child: &Arc<Registration>,
        descriptor: ForkDescriptor) -> Result<Self::Lease>;
}
// END PREPARED FORK CONSUMER CONTRACT

// BEGIN PRIVATE FORK COMPLETION CONTEXT
/// Exclusively owned by IHK's typed capsule. The surrounding capsule acquired
/// its mcctrl ModuleLease BEFORE construction and destroys this Box while that
/// external pin remains live; IHK releases the module only after return.
struct PendingForkProof {
    registration: Arc<Registration>,
    receipt: Option<super::mcctrl_vm::ForkRevocation>,
    identity: super::application_abi::ForkIdentityV1,
    accepted: bool,
    link_receipt: Option<super::mcctrl_vm::ForkLinkReceipt>,
}
struct ForkProofSeed<'a> {
    registration: &'a Arc<Registration>,
    identity: super::application_abi::ForkIdentityV1,
}

// SAFETY: IHK supplies exclusive initialized output and borrows this seed only
// during the synchronous attach. Its external module lease already pins every
// constructor/error/destructor instruction. No MM/provider lock is held.
unsafe extern "C" fn fork_proof_construct(seed: *mut c_void, output: *mut *mut c_void) -> i32 {
    if seed.is_null() || output.is_null() { return EINVAL.to_errno(); }
    unsafe { output.write(ptr::null_mut()) };
    let seed = unsafe { &*seed.cast::<ForkProofSeed<'_>>() };
    let result = (|| -> Result<_> {
        if seed.registration.fork.lock().as_ref().map(ForkClaim::identity) != Some(seed.identity)
            || seed.registration.fork_accepted.load(Ordering::Acquire) { return Err(EACCES); }
        Box::new(PendingForkProof { registration: seed.registration.clone(), receipt: None,
            identity: seed.identity, accepted: false, link_receipt: None }, GFP_KERNEL).map_err(Into::into)
    })();
    match result {
        Ok(context) => { unsafe { output.write(Box::into_raw(context).cast()) }; 0 }
        Err(error) => error.to_errno(),
    }
}

// SAFETY: IHK alone supplies the authenticated PreparedForkLease preview,
// outside all locks and BEFORE the MM consumer can seal. Its independent
// module lease already pins allocation/error cleanup and all later callbacks.
// This creates storage, not adoption, LINK, revocation or final-ACK proof.
unsafe extern "C" fn fork_proof_initial_construct(
    seed: *mut c_void, preview: *const super::application_abi::ForkIdentityV1,
    output: *mut *mut c_void,
) -> i32 {
    if seed.is_null() || preview.is_null() || output.is_null() { return EINVAL.to_errno(); }
    unsafe { output.write(ptr::null_mut()) };
    let attempt = unsafe { &*seed.cast::<ForkAttempt<'_>>() };
    let identity = unsafe { *preview };
    let result = (|| -> Result<_> {
        attempt.child.validate_inherited_child(attempt.parent)?;
        let current_mm = Mirror::current_mm_identity()?;
        let child = attempt.child;
        if identity.reserved0 != 0 || identity.reserved1 != 0
            || identity.slot != child.slot || identity.generation == 0 || identity.generation != child.generation
            || !child.same_generation(attempt.parent) || identity.child_pid != child.pid
            || identity.child_mm != current_mm || identity.parent == 0 || identity.child == 0
            || identity.parent == identity.child || identity.worker == 0 || identity.delivery == 0
            || identity.nonce == 0 || identity.root != attempt.descriptor.root
            || identity.start != attempt.descriptor.start || identity.length != attempt.descriptor.length
            || child.fork_accepted.load(Ordering::Acquire) || child.fork.lock().is_some()
            || child.mapping.lock().is_some() || attempt.process.registration.lock().is_some()
        { return Err(EACCES); }
        // Every fallible allocation completes before the independent MM
        // callback. A phase0 IHK entry cannot invoke any progress callback.
        Box::new(PendingForkProof { registration: child.clone(), receipt: None,
            identity, accepted: false, link_receipt: None }, GFP_KERNEL).map_err(Into::into)
    })();
    match result {
        Ok(context) => { unsafe { output.write(Box::into_raw(context).cast()) }; 0 }
        Err(error) => error.to_errno(),
    }
}

// SAFETY: Only IHK returns the exact sole Box after its scoped invocations end.
// Its capsule holds mcctrl's module lease throughout this destructor and all
// field Drops, then performs module_put from IHK text after this returns.
unsafe extern "C" fn fork_proof_destroy(context: *mut c_void) {
    if !context.is_null() { unsafe { drop(Box::from_raw(context.cast::<PendingForkProof>())) }; }
}

// SAFETY: Only IHK's capsule dispatches this with its authenticated pending key
// AFTER actual original-response freeze/backend drain, outside all locks. IHK
// exclusively claims that entry; callback/context pointers never escape.
unsafe extern "C" fn fork_verify_host(
    context: *mut c_void, identity: *const super::application_abi::ForkIdentityV1,
) -> i32 {
    if context.is_null() || identity.is_null() { return EINVAL.to_errno(); }
    let context = unsafe { &mut *context.cast::<PendingForkProof>() };
    let identity = unsafe { *identity };
    let result = (|| -> Result {
        if identity != context.identity || context.accepted { return Err(EACCES); }
        if context.registration.fork.lock().as_ref().map(ForkClaim::identity) != Some(identity) {
            return Err(EACCES);
        }
        if let Some(receipt) = context.receipt.as_ref() {
            return if receipt.matches(identity) { Ok(()) } else { Err(EACCES) };
        }
        // Actual MM revocation is inside this callback, never precomputed while
        // a positive RET might still be publishable. Errors retain the capsule.
        let receipt = context.registration.revoke_fork()?;
        if !receipt.matches(identity) { return Err(EACCES); }
        context.receipt = Some(receipt);
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

// SAFETY: IHK invokes ONLY after authentic final in-band destructor ACK and its
// exact durable receipt cache are committed, outside all locks under the pin.
// There is deliberately no public caller-asserted success/boolean constructor.
unsafe extern "C" fn fork_proof_accept(
    context: *mut c_void, identity: *const super::application_abi::ForkIdentityV1,
) -> i32 {
    if context.is_null() || identity.is_null() { return EINVAL.to_errno(); }
    let context = unsafe { &mut *context.cast::<PendingForkProof>() };
    let identity = unsafe { *identity };
    let result = (|| -> Result {
        if identity != context.identity { return Err(EACCES); }
        if context.accepted { return Ok(()); }
        if !context.receipt.as_ref().is_some_and(|receipt| receipt.matches(identity)) {
            return Err(EBUSY);
        }
        if context.registration.fork.lock().as_ref().map(ForkClaim::identity) != Some(identity) {
            return Err(EACCES);
        }
        // No fallible work follows. Keep the full key for exact retry/cache
        // reconciliation, and prevent ordinary CLEANUP from destroying twice.
        context.registration.armed.store(false, Ordering::Release);
        context.registration.fork_accepted.store(true, Ordering::Release);
        context.accepted = true;
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

#[allow(dead_code)]
impl Context {
    /// This dormant path is entered only from the live fd/registered callback
    /// whose IHK service lease pins our constructor and return frame. No UAPI
    /// opcode selects it while final transport/ACK integration is incomplete.
    pub(super) fn attach_fork_completion(&self) -> Result {
        let registration = self.registered()?;
        let identity = registration.fork.lock().as_ref().ok_or(EBUSY)?.identity();
        let mut seed = ForkProofSeed { registration: &registration, identity };
        // SAFETY: Borrowed seed/exact connection/current module are real kernel
        // owners. IHK takes its independent external pin before calling us and
        // owns the resulting Box; no raw lease/proof is returned to the caller.
        let status = unsafe { ihk_os_application_attach_fork_capsule_v2(
            registration.context.as_ptr(), &identity, super::THIS_MODULE.as_ptr().cast(),
            Some(fork_proof_construct), ptr::from_mut(&mut seed).cast(),
            Some(fork_proof_destroy), Some(fork_verify_host), Some(fork_proof_accept), Some(fork_verify_link),
        ) };
        kernel::error::to_result(status)
    }

    pub(super) fn revoke_fork_host(&self) -> Result {
        let registration = self.registered()?;
        let identity = registration.fork.lock().as_ref().ok_or(EBUSY)?.identity();
        // SAFETY: IHK selects ONLY its attached typed host verifier/context.
        // Its independently owned capsule pins this callback/module; no local
        // proof, MM lock or publication lock spans the synchronous dispatch.
        let status = unsafe { ihk_os_application_fork_progress_v1(
            registration.context.as_ptr(), &identity,
            super::application_abi::FORK_HOST_REVOKED_V1, None, ptr::null_mut(),
        ) };
        kernel::error::to_result(status)
    }

    pub(super) fn cancel_fork_completion(&self) -> Result {
        let registration = self.registered()?;
        let identity = registration.fork.lock().as_ref().ok_or(EBUSY)?.identity();
        // SAFETY: Live caller lease pins the return frame. IHK rejects any
        // attempted/uncertain context and destroys only an unattempted capsule
        // outside all locks while its independent module pin remains owned.
        let status = unsafe { ihk_os_application_cancel_fork_capsule_v1(
            registration.context.as_ptr(), &identity,
        ) };
        kernel::error::to_result(status)
    }
}
// END PRIVATE FORK COMPLETION CONTEXT

// BEGIN PRIVATE FORK LINK CONSUMER
#[derive(Clone, Copy, Eq, PartialEq)]
pub(super) struct ForkLinkBinding {
    pub(super) identity: super::application_abi::ForkIdentityV1,
    second_worker: u64, second_delivery: u64, second_cpu: i32,
    carrier_physical: u64, carrier_sequence: u64, gate: usize,
}

pub(super) struct BorrowedLinkSeal<'ticket> {
    gate: &'ticket core::sync::atomic::AtomicU8,
    binding: ForkLinkBinding,
}
impl<'ticket> BorrowedLinkSeal<'ticket> {
    // SAFETY: Only the IHK resolver lends this descriptor while its exclusively
    // claimed pending capsule/module and the exact backend ticket remain live.
    // Descriptor storage never escapes; only the retained gate identity does.
    unsafe fn from_provider(
        descriptor: &'ticket mut super::application_abi::ForkLinkSealV1,
        expected: super::application_abi::ForkIdentityV1,
    ) -> Result<Self> {
        if descriptor.version != 1 || descriptor.bytes as usize != core::mem::size_of::<super::application_abi::ForkLinkSealV1>()
            || descriptor.identity != expected || descriptor.reserved != 0
            || descriptor.second_worker == 0 || descriptor.second_delivery == 0
            || descriptor.second_cpu < 0 || descriptor.carrier_physical == 0
            || descriptor.carrier_physical % 8 != 0
            || descriptor.carrier_physical.checked_add(128).is_none()
            || descriptor.carrier_sequence == 0 || descriptor.gate.is_null()
        { return Err(EACCES); }
        let gate = unsafe { &*descriptor.gate };
        let binding = ForkLinkBinding { identity: expected,
            second_worker: descriptor.second_worker, second_delivery: descriptor.second_delivery,
            second_cpu: descriptor.second_cpu, carrier_physical: descriptor.carrier_physical,
            carrier_sequence: descriptor.carrier_sequence, gate: descriptor.gate as usize };
        Ok(Self { gate, binding })
    }
    pub(super) fn binding(&self) -> ForkLinkBinding { self.binding }
    pub(super) fn sealed(&self) -> bool { self.gate.load(Ordering::Acquire) == 2 }
    // The only operation permitted after VMA validation under MM exclusion.
    // No MM mutation precedes it: a concurrent cancellation can safely win.
    #[inline(always)]
    pub(super) fn try_seal(&mut self) -> Result {
        self.gate.compare_exchange(0, 2, Ordering::AcqRel, Ordering::Acquire)
            .map(|_| ()).map_err(|_| EBUSY)
    }
}

/// Transient mm_users only. Never stored in a durable receipt/capsule: that
/// would form a VMA -> Registration -> capsule -> mm_users cycle.
pub(super) struct ReferencedChildMm { mm: NonNull<bindings::mm_struct> }
impl ReferencedChildMm {
    pub(super) fn as_ptr(&self) -> *mut bindings::mm_struct { self.mm.as_ptr() }
}
impl Drop for ReferencedChildMm {
    fn drop(&mut self) {
        // SAFETY: Balance exactly get_task_mm, after MM write unlock and outside
        // all local/provider locks. The outer capsule pins our callback text.
        unsafe { bindings::mmput(self.mm.as_ptr()) };
    }
}

impl Registration {
    fn fork_link_mm(&self, identity: super::application_abi::ForkIdentityV1) -> Result<ReferencedChildMm> {
        if self.slot != identity.slot || self.generation != identity.generation
            || self.pid != identity.child_pid || self._pid.number()? != identity.child_pid
            || !self.armed.load(Ordering::Acquire) || self.fork_accepted.load(Ordering::Acquire)
        { return Err(EACCES); }
        // SAFETY: The retained PID object excludes numeric reuse. A task
        // reference pins the child while get_task_mm acquires its real users.
        let task = unsafe { bindings::get_pid_task(self._pid.0.as_ptr(), bindings::pid_type_PIDTYPE_TGID) };
        if task.is_null() { return Err(ESRCH); }
        let mm = unsafe { bindings::get_task_mm(task) };
        unsafe { bindings::put_task_struct(task) };
        let mm = ReferencedChildMm { mm: NonNull::new(mm).ok_or(ESRCH)? };
        if mm.as_ptr() as u64 != identity.child_mm { return Err(EACCES); }
        Ok(mm)
    }
}

// SAFETY: IHK dispatches only its stored capsule callback, outside slots, while
// the exact prepared backend link ticket and its atomic gate remain pinned.
unsafe extern "C" fn fork_verify_link(
    context: *mut c_void, descriptor: *mut super::application_abi::ForkLinkSealV1,
) -> i32 {
    if context.is_null() || descriptor.is_null() { return EINVAL.to_errno(); }
    let context = unsafe { &mut *context.cast::<PendingForkProof>() };
    let result = (|| -> Result {
        if context.accepted || context.receipt.is_some() { return Err(EBUSY); }
        let mut seal = unsafe { BorrowedLinkSeal::from_provider(&mut *descriptor, context.identity) }?;
        if let Some(receipt) = context.link_receipt.as_ref() {
            return if receipt.matches(seal.binding()) && seal.sealed() { Ok(()) } else { Err(EACCES) };
        }
        let registration = context.registration.clone();
        let mm = registration.fork_link_mm(context.identity)?;
        let mirror = registration.mapping.lock().clone().ok_or(EBUSY)?;
        let result = {
            let claim = registration.fork.lock();
            let claim = claim.as_ref().ok_or(EBUSY)?;
            if claim.identity() != context.identity { return Err(EACCES); }
            mirror.validate_fork_link(claim, &registration, &mm, &mut seal)
        };
        // mmput can trigger VMA/Registration destructors: no MM or claim lock
        // remains. Persistent ownership uses mm_count, never this users ref.
        drop(mm);
        context.link_receipt = Some(result?);
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}
// END PRIVATE FORK LINK CONSUMER

// BEGIN PRIVATE SCOPED FORK CONSUMER
/// Created only after validating a provider-owned scoped callback. Scalar keys
/// alone cannot construct this claim outside this module.
#[allow(dead_code)]
pub(super) struct ForkClaim { identity: super::application_abi::ForkIdentityV1 }
#[allow(dead_code)]
impl ForkClaim {
    pub(super) fn identity(&self) -> super::application_abi::ForkIdentityV1 { self.identity }
}

struct BorrowedSeal<'callback> {
    flag: &'callback AtomicBool,
    identity: super::application_abi::ForkIdentityV1,
}
impl<'callback> BorrowedSeal<'callback> {
    /// # Safety
    /// Only the registered synchronous provider callback may lend descriptor
    /// storage and flag. Its actual exclusive lease/module/OS owners outlive
    /// this whole borrow; neither pointer may escape or be retained here.
    unsafe fn from_provider(
        descriptor: &'callback mut super::application_abi::ForkSealV1,
        parent: &Registration, child: &Registration, geometry: ForkDescriptor,
        child_mm: u64,
    ) -> Result<Self> {
        let key = descriptor.identity;
        if descriptor.version != 1
            || descriptor.bytes as usize != core::mem::size_of::<super::application_abi::ForkSealV1>()
            || descriptor.sealed.is_null()
            || descriptor.sealed as usize % core::mem::align_of::<AtomicBool>() != 0
            || key.reserved0 != 0 || key.reserved1 != 0
            || key.slot != child.slot || key.generation == 0 || key.generation != child.generation
            || !child.same_generation(parent) || key.child_pid != child.pid || key.child_mm != child_mm
            || key.parent == 0 || key.child == 0 || key.parent == key.child
            || key.worker == 0 || key.delivery == 0 || key.nonce == 0
            || key.root != geometry.root || key.start != geometry.start || key.length != geometry.length
        { return Err(EACCES); }
        // SAFETY: The checked registered provider lends this exact aligned
        // preallocated AtomicBool while retaining the actual lease.
        let flag = unsafe { &*descriptor.sealed };
        if flag.load(Ordering::Acquire) { return Err(EBUSY); }
        Ok(Self { flag, identity: key })
    }
    fn seal(&mut self) { self.flag.store(true, Ordering::Release); }
}

struct ForkAttempt<'a> {
    process: &'a Arc<Process>, parent: &'a Arc<Registration>, child: &'a Arc<Registration>,
    parent_mirror: &'a Arc<Mirror>, descriptor: ForkDescriptor,
    called: bool, published: bool,
}

// SAFETY: Only the synchronous provider callback receives this borrowed stack
// attempt; both Registration connections/module owners survive the whole call.
unsafe extern "C" fn fork_adopt_consumer(
    context: *mut c_void, descriptor: *mut super::application_abi::ForkSealV1,
) -> i32 {
    if context.is_null() || descriptor.is_null() { return EINVAL.to_errno(); }
    let attempt = unsafe { &mut *context.cast::<ForkAttempt<'_>>() };
    if attempt.called { return EBUSY.to_errno(); }
    attempt.called = true;
    let result = (|| -> Result {
        attempt.child.validate_inherited_child(attempt.parent)?;
        let child_mm = Mirror::current_mm_identity()?;
        let mut seal = unsafe { BorrowedSeal::from_provider(&mut *descriptor,
            attempt.parent, attempt.child, attempt.descriptor, child_mm) }?;
        let mut publication = attempt.process.registration.lock();
        if publication.is_some() { return Err(EINVAL); }
        let mut mapping = attempt.child.mapping.lock();
        let mut claim = attempt.child.fork.lock();
        if mapping.is_some() || claim.is_some() { return Err(EINVAL); }
        // No provider calls/locks, fallible work or owner Drop in this seal.
        let mirror = unsafe { Mirror::inherit_vmas(attempt.parent_mirror, attempt.parent,
            attempt.child.clone(), attempt.descriptor.start, attempt.descriptor.end()?, |_| seal.seal()) }?;
        // MM and per-VMA write exclusion have ended. Preallocated publication
        // slots make all remaining local work infallible.
        *mapping = Some(mirror);
        *claim = Some(ForkClaim { identity: seal.identity });
        attempt.child.armed.store(true, Ordering::Release);
        *publication = Some(attempt.child.clone());
        drop(claim);
        drop(mapping);
        drop(publication);
        attempt.published = true;
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}
// END PRIVATE SCOPED FORK CONSUMER

pub(super) struct Registration {
    context: NonNull<c_void>,
    slot: u32,
    generation: u64,
    pid: i32,
    armed: AtomicBool,
    reap_error: AtomicI32,
    trace_budget: AtomicI32,
    operation: Pin<Box<Mutex<()>>>,
    mapping: Pin<Box<Mutex<Option<Arc<Mirror>>>>>,
    fork: Pin<Box<Mutex<Option<ForkClaim>>>>,
    fork_accepted: AtomicBool,
    workers: Pin<Box<Mutex<Vec<Arc<HostWorker>>>>>,
    // Mirror files can outlive all mcos file bindings and their Process owner.
    // Retain the referenced PID independently for that complete lifetime.
    _pid: ProcessId,
}

// SAFETY: The IHK connection contract permits concurrent borrows and ownership
// transfer. Our process mutex publishes it; only its final destructor invokes it.
unsafe impl Send for Registration {}
// SAFETY: The IHK connection supports concurrent invocations. The operation
// mutex serializes image preparation; the mapping publication lock is short.
unsafe impl Sync for Registration {}

impl Registration {
    pub(super) fn same_generation(&self, other: &Self) -> bool {
        self.slot == other.slot && self.generation != 0 && self.generation == other.generation
    }

    /// Bind only the child registration's referenced PID to this calling TGID.
    /// Backend parent delivery/nonce/reservation/root provenance and the
    /// infallible seal/revoke/final-ACK obligations remain separate authority.
    pub(super) fn validate_inherited_child(&self, parent: &Self) -> Result {
        if !self.same_generation(parent) {
            return Err(EACCES);
        }
        let current = ProcessId::current()?;
        if !self._pid.same(&current) || self._pid.same(&parent._pid)
            || current.number()? != self.pid
        {
            return Err(EACCES);
        }
        Ok(())
    }

    /// Only this registration's authenticated scoped callback can install the
    /// claim consumed by the actual mirror revoke. Full identity stays pinned.
    #[allow(dead_code)]
    pub(super) fn revoke_fork(self: &Arc<Self>) -> Result<super::mcctrl_vm::ForkRevocation> {
        let mirror = self.mapping.lock().clone().ok_or(EBUSY)?;
        let claim = self.fork.lock();
        let claim = claim.as_ref().ok_or(EBUSY)?;
        let key = claim.identity();
        if key.slot != self.slot || key.generation != self.generation || key.child_pid != self.pid {
            return Err(EACCES);
        }
        mirror.revoke_fork_aliases(claim)
    }

    fn acquire(slot: u32, generation: u64, identity: ProcessId) -> Result<Arc<Self>> {
        let pid = identity.number()?;
        let operation = Box::pin_init(new_mutex!(()), GFP_KERNEL)?;
        let mapping = Box::pin_init(new_mutex!(None), GFP_KERNEL)?;
        let fork = Box::pin_init(new_mutex!(None), GFP_KERNEL)?;
        let workers = Box::pin_init(new_mutex!(Vec::with_capacity(64, GFP_KERNEL)?), GFP_KERNEL)?;
        let mut context = ptr::null_mut();
        // SAFETY: mcctrl pins IHK, and this output remains exclusively borrowed
        // until the checked open transfers its independently leased connection.
        kernel::error::to_result(unsafe {
            ihk_os_application_open_v1(
                slot,
                generation,
                super::application_abi::VERSION,
                pid,
                &mut context,
            )
        })?;
        Ok(Arc::new(
            Self {
                context: NonNull::new(context).ok_or(EIO)?,
                slot,
                generation,
                pid,
                armed: AtomicBool::new(false),
                reap_error: AtomicI32::new(0),
                trace_budget: AtomicI32::new(64),
                operation,
                mapping,
                fork,
                fork_accepted: AtomicBool::new(false),
                workers,
                _pid: identity,
            },
            GFP_KERNEL,
        )?)
    }

    pub(super) fn invoke(&self, command: u32, bytes: &mut [u8]) -> Result {
        // SAFETY: This Arc retains the kernel connection through the exclusive
        // byte borrow. The backend copies any published work into its own pages.
        let status = unsafe {
            ihk_os_application_invoke_v1(
                self.context.as_ptr(),
                command,
                bytes.as_mut_ptr(),
                bytes.len(),
            )
        };
        if status > 0 || status < -4095 {
            return Err(EIO);
        }
        kernel::error::to_result(status as i32).map(|_| ())
    }

    fn trace(&self) -> bool {
        self.trace_budget
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |count| {
                (count > 0).then(|| count - 1)
            })
            .is_ok()
    }

    fn worker(&self, create: bool) -> Result<Arc<HostWorker>> {
        let identity = ProcessId::thread()?;
        let mirror = self.mapping.lock().clone().ok_or(EINVAL)?;
        mirror.current()?;
        let workers = self.workers.lock();
        if let Some(worker) = workers
            .iter()
            .find(|worker| worker.identity.same(&identity))
        {
            worker.mirror.current()?;
            return Ok(worker.clone());
        }
        if !create {
            return Err(EINVAL);
        }
        drop(workers);
        self.reap_workers()?;
        let mut workers = self.workers.lock();
        if workers.len() == 64 {
            return Err(EAGAIN);
        }
        let mut bytes = [0; 16];
        bytes[..8].copy_from_slice(&(identity.number()? as i64).to_le_bytes());
        self.invoke(super::application_abi::WORKER_OPEN, &mut bytes)?;
        let handle = u64::from_le_bytes(bytes[8..].try_into().unwrap());
        if handle == 0 {
            return Err(EIO);
        }
        let worker = match Arc::new(
            HostWorker {
                identity,
                mirror,
                handle,
                delivery: AtomicU64::new(0),
                delivery_cpu: AtomicI32::new(-1),
                delivery_trace: AtomicBool::new(false),
            },
            GFP_KERNEL,
        ) {
            Ok(worker) => worker,
            Err(error) => {
                bytes[..8].copy_from_slice(&handle.to_le_bytes());
                let _ = self.invoke(super::application_abi::WORKER_CLOSE, &mut bytes);
                return Err(error.into());
            }
        };
        if let Err(error) = workers.push(worker.clone(), GFP_KERNEL) {
            bytes[..8].copy_from_slice(&handle.to_le_bytes());
            let _ = self.invoke(super::application_abi::WORKER_CLOSE, &mut bytes);
            return Err(error.into());
        }
        Ok(worker)
    }

    /// Both acquisition and the independent reaper use this original PID/MM
    /// retirement path. The backend owns cancellation past a departing task.
    fn reap_workers(&self) -> Result {
        let mut workers = self.workers.lock();
        let mut index = 0;
        while index < workers.len() {
            if !workers[index].identity.thread_alive() {
                let mut bytes = [0; 16];
                bytes[..8].copy_from_slice(&workers[index].handle.to_le_bytes());
                match self.invoke(super::application_abi::WORKER_CLOSE, &mut bytes) {
                    Ok(()) => {
                        let removed = workers.swap_remove(index);
                        drop(workers);
                        pr_info!("application_worker=retired os={} generation={} pid={} tid={} handle={} delivered={}\n",
                            self.slot, self.generation, self.pid, removed.identity.number()?, removed.handle,
                            removed.delivery.load(Ordering::Acquire));
                        // Referenced PID/MM destruction is outside publication.
                        drop(removed);
                        workers = self.workers.lock();
                        index = 0;
                        continue;
                    }
                    Err(error) if error == EBUSY => {}
                    Err(error) => return Err(error),
                }
            }
            index += 1;
        }
        Ok(())
    }

    fn wait_syscall(&self, argument: usize, compat: bool) -> Result<isize> {
        if compat {
            return Err(errno(-95));
        }
        let worker = self.worker(true)?;
        if worker.delivery.load(Ordering::Acquire) != 0 {
            return Err(EBUSY);
        }
        loop {
            let mut bytes = [0; 96];
            bytes[..8].copy_from_slice(&worker.handle.to_le_bytes());
            self.invoke(super::application_abi::WAIT_SYSCALL, &mut bytes)?;
            let serial = u64::from_le_bytes(bytes[8..16].try_into().unwrap());
            if serial == 0 {
                return Err(EIO);
            }
            if image::word(&bytes, 40).map_err(errno)? == 9 {
                // mmap numbers in this protocol are kernel file/device-pager
                // requests. Consume the retained packet in this worker's context
                // before the ordinary userspace WAIT descriptor is touched.
                let mut pager = [0; 32];
                pager[..16].copy_from_slice(&bytes[..16]);
                let result = self.invoke(super::application_abi::PAGER_SYSCALL, &mut pager);
                if result.is_err() && image::word(&pager, 16).map_err(errno)? == 0 {
                    let mut rollback = [0; 24];
                    rollback[..16].copy_from_slice(&bytes[..16]);
                    let _ = self.invoke(super::application_abi::COPIED_SYSCALL, &mut rollback);
                }
                result?;
                continue;
            }
            if image::word(&bytes, 40).map_err(errno)? == 11 {
                let mut clear = [0; 40];
                clear[..16].copy_from_slice(&bytes[..16]);
                if let Err(error) = self.invoke(super::application_abi::CLEAR_SYSCALL, &mut clear) {
                    if u64::from_le_bytes(clear[16..24].try_into().unwrap()) == 0 {
                        let mut rollback = [0; 24];
                        rollback[..16].copy_from_slice(&bytes[..16]);
                        let _ = self.invoke(super::application_abi::COPIED_SYSCALL, &mut rollback);
                    }
                    return Err(error);
                }
                let start = u64::from_le_bytes(clear[24..32].try_into().unwrap());
                let end = u64::from_le_bytes(clear[32..40].try_into().unwrap());
                // The kernel reservation defers cancellation. This worker
                // retains the exact Mirror/Registration while Linux clears its
                // current MM outside every application/transport lock. Always
                // finish the reservation, including an actual MM error.
                let value = worker
                    .mirror
                    .clear(start, end)
                    .map_or_else(|error| error.to_errno() as i64, |()| 0);
                clear[16..].fill(0);
                clear[24..32].copy_from_slice(&value.to_le_bytes());
                self.invoke(super::application_abi::CLEAR_DONE, &mut clear)?;
                continue;
            }
            let copied = UserSlice::new(argument, 80)
                .writer()
                .write_slice(&bytes[16..96]);
            let mut result = [0; 24];
            result[..16].copy_from_slice(&bytes[..16]);
            result[16..24].copy_from_slice(&(copied.is_ok() as u64).to_le_bytes());
            let commit = self.invoke(super::application_abi::COPIED_SYSCALL, &mut result);
            // The original private request stays queued if any user byte faults.
            copied?;
            commit?;
            let number = image::word(&bytes, 40).map_err(errno)?;
            // The launcher uses its Linux worker slot in RET.cpu. Retain the
            // packet's guest CPU before publishing this private delivered serial.
            worker.delivery_cpu.store(
                image::word(&bytes, 16).map_err(errno)? as i32,
                Ordering::Relaxed,
            );
            // Ordinary samples remain grouped with their route and return;
            // committed non-returning exit_group delivery is always visible
            // even after the ordinary trace budget is exhausted.
            let traced = number == 231 || self.trace();
            worker.delivery_trace.store(traced, Ordering::Relaxed);
            worker.delivery.store(serial, Ordering::Release);
            if traced {
                pr_info!("application_syscall=delivered os={} generation={} pid={} worker={} delivery={} cpu={} number={}\n",
                self.slot, self.generation, self.pid, worker.handle, serial,
                image::word(&bytes, 16).map_err(errno)?, number);
            }
            return Ok(0);
        }
    }

    fn return_syscall(&self, argument: usize, compat: bool) -> Result<isize> {
        if compat {
            return Err(errno(-95));
        }
        let mut descriptor = [0; 40];
        UserSlice::new(argument, descriptor.len())
            .reader()
            .read_slice(&mut descriptor)?;
        let worker = self.worker(false)?;
        let serial = worker.delivery.load(Ordering::Acquire);
        if serial == 0 {
            return Err(EINVAL);
        }
        let traced = worker.delivery_trace.load(Ordering::Relaxed);
        let length = image::word(&descriptor, 32).map_err(errno)?;
        if length > 16 {
            return Err(EINVAL);
        }
        let mut bytes = [0; 72];
        bytes[..8].copy_from_slice(&worker.handle.to_le_bytes());
        bytes[8..16].copy_from_slice(&serial.to_le_bytes());
        let cpu = worker.delivery_cpu.load(Ordering::Relaxed) as i64;
        bytes[16..24].copy_from_slice(&cpu.to_le_bytes());
        bytes[24..32].copy_from_slice(&descriptor[8..16]);
        bytes[32..48].copy_from_slice(&descriptor[24..40]);
        if length != 0 {
            let source = image::word(&descriptor, 16).map_err(errno)? as usize;
            source.checked_add(length as usize).ok_or(errno(-75))?;
            UserSlice::new(source, length as usize)
                .reader()
                .read_slice(&mut bytes[56..56 + length as usize])?;
        }
        let launcher_cpu = image::word(&descriptor, 0).map_err(errno)? as i64;
        if launcher_cpu != cpu && traced {
            pr_info!("application_syscall=return_route os={} generation={} pid={} worker={} delivery={} launcher_cpu={} guest_cpu={}\n",
                self.slot, self.generation, self.pid, worker.handle, serial, launcher_cpu, cpu);
        }
        // This private operation inspects the actual owned delivery. Ordinary
        // returns are unchanged; only the new carrier's second clone can seal
        // LINK. A failure leaves the delivery owned for exact retry.
        let value = image::word(&bytes, 24).map_err(errno)? as i64;
        // Park a genuine fresh selector2 delivery before any legacy return
        // hook. The incoming launcher -95 is not authority. Parked MUST stop
        // ordinary RETURN; it cannot manufacture RET0 or a revoke receipt.
        match unsafe { ihk_os_application_prepare_fork_control_v1(
            self.context.as_ptr(), worker.handle, serial, cpu, value,
        ) } {
            0 => {}, 1 => return Err(EBUSY),
            e if (-4095..0).contains(&e) => return Err(errno(e)),
            _ => return Err(errno(-71)),
        }
        // SAFETY: This live fd/worker pins our return frame and connection. IHK
        // authenticates the backend delivery and dispatches only its own capsule.
        kernel::error::to_result(unsafe { ihk_os_application_prepare_fork_link_v1(
            self.context.as_ptr(), worker.handle, serial, cpu, value,
        ) })?;
        // The provider derives a final-ACK ticket only from this exact owned
        // Delivered selector3. A decoded guest frame alone cannot release any
        // capsule, registration, root or module owner. Ordinary returns pass.
        // SAFETY: The same live fd/worker/connection pins this call and return;
        // IHK lends only its own retained payload while all callbacks are scoped.
        kernel::error::to_result(unsafe { ihk_os_application_prepare_fork_ack_v1(
            self.context.as_ptr(), worker.handle, serial, cpu, value,
        ) })?;
        let result = self.invoke(super::application_abi::RETURN_SYSCALL, &mut bytes);
        if image::word(&bytes, 48).map_err(errno)? == 1 {
            // This includes interrupted waits after acceptance. The independent
            // pump retains the original result; WAIT cannot rebind this worker
            // until its status and any required wake have actually published.
            worker.delivery.store(0, Ordering::Release);
        }
        result?;
        if traced {
            pr_info!("application_syscall=returned os={} generation={} pid={} worker={} delivery={} cpu={} value={}\n",
                self.slot, self.generation, self.pid, worker.handle, serial,
                image::word(&bytes, 16).map_err(errno)?, image::word(&bytes, 24).map_err(errno)? as i64);
        }
        Ok(0)
    }

    fn prepare_image(self: &Arc<Self>, argument: usize, compat: bool) -> Result<isize> {
        if compat {
            return Err(kernel::error::to_result(-95).unwrap_err());
        }
        // This is an operation serializer, not a publication/OS lock. The
        // continuing service and VM faults do not need it to make progress.
        let _operation = self.operation.lock();
        if self.mapping.lock().is_some() {
            return Err(EBUSY);
        }
        let mut header = zero_bytes(image::HEADER)?;
        UserSlice::new(argument, header.len())
            .reader()
            .read_slice(&mut header)?;
        let descriptor = image::descriptor_bytes(&header).map_err(errno)?;
        let args = image::word(&header, image::ARGS_LEN).map_err(errno)? as usize;
        let envs = image::word(&header, image::ENVS_LEN).map_err(errno)? as usize;
        if !(16..=image::MAX_FLAT_BYTES).contains(&args)
            || !(16..=image::MAX_FLAT_BYTES).contains(&envs)
        {
            return Err(errno(-7));
        }
        let total = descriptor
            .checked_add(args)
            .and_then(|n| n.checked_add(envs))
            .ok_or(errno(-75))?;
        let mut bytes = zero_bytes(total)?;
        bytes[..image::HEADER].copy_from_slice(&header);
        UserSlice::new(
            argument.checked_add(image::HEADER).ok_or(errno(-75))?,
            descriptor - image::HEADER,
        )
        .reader()
        .read_slice(&mut bytes[image::HEADER..descriptor])?;
        let argv = image::word(&header, image::ARGS).map_err(errno)? as usize;
        let envp = image::word(&header, image::ENVS).map_err(errno)? as usize;
        UserSlice::new(argv, args)
            .reader()
            .read_slice(&mut bytes[descriptor..descriptor + args])?;
        UserSlice::new(envp, envs)
            .reader()
            .read_slice(&mut bytes[descriptor + args..])?;
        bytes[image::PID..image::PID + 4].copy_from_slice(&self.pid.to_le_bytes());
        for (index, value) in super::mcctrl_exec::credential_values().iter().enumerate() {
            let offset = image::CREDENTIALS + index * 4;
            bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
        }
        image::put_word(&mut bytes, image::USER_START, 0).map_err(errno)?;
        image::put_word(&mut bytes, image::USER_END, image::USER_LIMIT).map_err(errno)?;
        // SAFETY: Exact scalar identities belong to our retained connection.
        let cpus = unsafe {
            super::ihk_os_topology_query_v1(
                self.slot,
                self.generation,
                super::abi::MCEXEC_UP_GET_CPU,
            )
        };
        if cpus <= 0 {
            return Err(if cpus < 0 { errno(cpus as i32) } else { EINVAL });
        }
        image::Input::parse(&bytes, cpus as usize).map_err(errno)?;
        let mirror = Mirror::reserve(self.clone())?;
        *self.mapping.lock() = Some(mirror.clone());
        image::put_word(&mut bytes, image::USER_END, mirror.end).map_err(errno)?;
        let result = image::Input::parse(&bytes, cpus as usize)
            .map_err(errno)
            .and_then(|_| self.invoke(super::application_abi::PREPARE, &mut bytes));
        if let Err(error) = result {
            if mirror.unmap().is_ok() {
                *self.mapping.lock() = None;
            }
            return Err(error);
        }
        UserSlice::new(argument, descriptor)
            .writer()
            .write_slice(&bytes[..descriptor])?;
        pr_info!(
            "application_image=prepared os={} generation={} pid={} sections={} cpu={}\n",
            self.slot,
            self.generation,
            self.pid,
            (descriptor - image::HEADER) / image::SECTION,
            image::integer(&bytes, image::CPU).map_err(errno)?
        );
        Ok(0)
    }

    fn start_image(&self, argument: usize, compat: bool) -> Result<isize> {
        if compat {
            return Err(errno(-95));
        }
        let _operation = self.operation.lock();
        let mirror = self.mapping.lock().clone().ok_or(EINVAL)?;
        mirror.current()?;
        let mut header = zero_bytes(image::HEADER)?;
        UserSlice::new(argument, header.len())
            .reader()
            .read_slice(&mut header)?;
        self.invoke(super::application_abi::START, &mut header)?;
        Ok(0)
    }

    fn transfer_image(&self, argument: usize, compat: bool) -> Result<isize> {
        let mirror = self.mapping.lock().clone().ok_or(EINVAL)?;
        mirror.current()?;
        let mut descriptor = [0; 32];
        let length = if compat { 16 } else { 32 };
        UserSlice::new(argument, length)
            .reader()
            .read_slice(&mut descriptor[..length])?;
        let (physical, user, size, direction) = if compat {
            (
                u32::from_le_bytes(descriptor[0..4].try_into().unwrap()) as u64,
                u32::from_le_bytes(descriptor[4..8].try_into().unwrap()) as usize,
                u32::from_le_bytes(descriptor[8..12].try_into().unwrap()) as usize,
                descriptor[12],
            )
        } else {
            (
                image::word(&descriptor, 0).map_err(errno)?,
                image::word(&descriptor, 8).map_err(errno)? as usize,
                image::word(&descriptor, 16).map_err(errno)? as usize,
                descriptor[24],
            )
        };
        if size == 0 || size > image::MAX_FLAT_BYTES || direction > 1 {
            return Err(EINVAL);
        }
        user.checked_add(size).ok_or(errno(-75))?;
        physical.checked_add(size as u64).ok_or(errno(-75))?;
        let identity = ProcessId::thread()?;
        let worker = self
            .workers
            .lock()
            .iter()
            .find(|worker| worker.identity.same(&identity))
            .cloned();
        let delivery = worker
            .as_ref()
            .map_or(0, |worker| worker.delivery.load(Ordering::Acquire));
        let running = delivery != 0;
        let prefix = if running { 32 } else { 16 };
        let mut bytes = zero_bytes(prefix + size)?;
        if running {
            let worker = worker.as_ref().ok_or(EINVAL)?;
            worker.mirror.current()?;
            image::put_word(&mut bytes, 0, worker.handle).map_err(errno)?;
            image::put_word(&mut bytes, 8, delivery).map_err(errno)?;
        }
        image::put_word(&mut bytes, prefix - 16, physical).map_err(errno)?;
        image::put_word(&mut bytes, prefix - 8, direction as u64).map_err(errno)?;
        if direction == 0 {
            UserSlice::new(user, size)
                .reader()
                .read_slice(&mut bytes[prefix..])?;
        }
        let command = if running {
            super::application_abi::TID_TRANSFER
        } else {
            super::application_abi::TRANSFER
        };
        self.invoke(command, &mut bytes)?;
        if direction == 1 {
            UserSlice::new(user, size)
                .writer()
                .write_slice(&bytes[prefix..])?;
        }
        Ok(0)
    }

    fn clear_user_space(&self, argument: usize, compat: bool) -> Result<isize> {
        let mut bytes = [0; 16];
        let length = if compat { 8 } else { 16 };
        UserSlice::new(argument, length)
            .reader()
            .read_slice(&mut bytes[..length])?;
        let (start, end) = if compat {
            (
                u32::from_le_bytes(bytes[..4].try_into().unwrap()) as u64,
                u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as u64,
            )
        } else {
            (
                image::word(&bytes, 0).map_err(errno)?,
                image::word(&bytes, 8).map_err(errno)?,
            )
        };
        let mirror = self.mapping.lock().clone().ok_or(EINVAL)?;
        mirror.clear(start, end)?;
        Ok(0)
    }
}

fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}

fn zero_bytes(length: usize) -> Result<Vec<u8>> {
    let mut bytes = Vec::with_capacity(length, GFP_KERNEL)?;
    for _ in 0..length {
        bytes.push(0, GFP_KERNEL)?;
    }
    Ok(bytes)
}

impl Drop for Registration {
    fn drop(&mut self) {
        if self.fork.lock().is_some() && !self.fork_accepted.load(Ordering::Acquire) {
            // A retained authenticated adoption is never ordinary CLEANUP.
            // Until authenticated capsule acceptance, retain the successful
            // opaque connection (and its admission/OS/provider owners).
            // Accepted claims keep their key but are unarmed: Close only.
            pr_err!("application_fork=retained os={} generation={} pid={}\n", self.slot, self.generation, self.pid);
            return;
        }
        if self.armed.load(Ordering::Acquire) {
            // SAFETY: The process's PID and this connection remain owned until
            // cleanup finishes. The continuing service owns any request whose
            // acknowledgement arrives after the bounded waiter has departed.
            let status = unsafe {
                ihk_os_application_invoke_v1(
                    self.context.as_ptr(),
                    super::application_abi::CLEANUP,
                    ptr::null_mut(),
                    0,
                )
            };
            pr_info!(
                "application_process=release os={} generation={} pid={} cleanup_errno={}\n",
                self.slot,
                self.generation,
                self.pid,
                status
            );
        }
        // SAFETY: Return exactly the successful connection after invocation.
        // A failed/racing publication remains unarmed and cancels only its own
        // reserved descriptor; it cannot clean up the winning registration.
        unsafe { ihk_os_application_close_v1(self.context.as_ptr()) };
    }
}

/// Linux's referenced thread-group PID, stable across namespace-number reuse
/// and leader replacement. The kernel owns the object's atomic reference count.
struct ProcessId(NonNull<bindings::pid>);

impl ProcessId {
    fn current() -> Result<Self> {
        Self::from_current(bindings::pid_type_PIDTYPE_TGID)
    }

    fn thread() -> Result<Self> {
        Self::from_current(bindings::pid_type_PIDTYPE_PID)
    }

    fn from_current(kind: bindings::pid_type) -> Result<Self> {
        // SAFETY: get_current is valid for this calling task; get_task_pid takes
        // its own reference under Linux's RCU protection before returning.
        let pid = unsafe { bindings::get_task_pid(bindings::get_current(), kind) };
        Ok(Self(NonNull::new(pid).ok_or(ESRCH)?))
    }

    fn thread_alive(&self) -> bool {
        self.alive(bindings::pid_type_PIDTYPE_PID)
    }

    fn group_alive(&self) -> bool {
        self.alive(bindings::pid_type_PIDTYPE_TGID)
    }

    fn alive(&self, kind: bindings::pid_type) -> bool {
        // SAFETY: The referenced PID excludes object reuse. Linux checks its
        // task link under RCU and returns an owned task reference on success.
        let task = unsafe { bindings::get_pid_task(self.0.as_ptr(), kind) };
        if task.is_null() {
            return false;
        }
        // SAFETY: Balance exactly get_pid_task's task reference.
        unsafe { bindings::put_task_struct(task) };
        true
    }
    fn same(&self, other: &Self) -> bool {
        self.0 == other.0
    }

    fn number(&self) -> Result<i32> {
        // SAFETY: The referenced PID and permanent initial namespace outlive
        // this call. The guest identity uses the host-global number, while the
        // process registry continues to distinguish referenced PID objects.
        let pid = unsafe {
            bindings::pid_nr_ns(self.0.as_ptr(), ptr::addr_of_mut!(bindings::init_pid_ns))
        };
        if pid <= 0 {
            return Err(ESRCH);
        }
        Ok(pid)
    }
}

// SAFETY: Linux permits owned PID references to move between tasks; the opaque
// object is accessed only by its exported reference operations and identity.
unsafe impl Send for ProcessId {}
// SAFETY: Shared ProcessId access performs only Linux's exported reference and
// identity operations; the owned PID reference remains valid until its one Drop.
unsafe impl Sync for ProcessId {}

impl Drop for ProcessId {
    fn drop(&mut self) {
        // SAFETY: Exactly one successful get_task_pid reference is released.
        unsafe { bindings::put_pid(self.0.as_ptr()) };
    }
}

struct HostWorker {
    identity: ProcessId,
    mirror: Arc<Mirror>,
    handle: u64,
    delivery: AtomicU64,
    delivery_cpu: AtomicI32,
    delivery_trace: AtomicBool,
}

#[pin_data]
struct Process {
    slot: u32,
    generation: u64,
    #[pin]
    executable: Mutex<Option<Executable>>,
    #[pin]
    registration: Mutex<Option<Arc<Registration>>>,
    // Field destruction closes the executable and application before this PID.
    pid: ProcessId,
}

impl Process {
    fn matches(&self, slot: u32, generation: u64, pid: &ProcessId) -> bool {
        self.slot == slot && self.generation == generation && self.pid.same(pid)
    }

    fn detach_owners(&self) {
        let registration = self.registration.lock().take();
        let executable = self.executable.lock().take();
        // Reaper snapshots retain only Process identity. Real VMAs and active
        // invocations still own independent Registration references.
        drop(executable);
        drop(registration);
    }

    fn replace(&self, executable: Option<Executable>) -> bool {
        let old = core::mem::replace(&mut *self.executable.lock(), executable);
        let found = old.is_some();
        // The process lock protects publication only; VFS release runs after it.
        drop(old);
        found
    }
}

struct Entry {
    process: Arc<Process>,
    files: usize,
}

type Table = Mutex<Vec<Entry>>;
static PUBLISHED: AtomicPtr<Table> = AtomicPtr::new(ptr::null_mut());

pub(super) struct Registry {
    reaper: Reaper,
    table: Arc<Table>,
}

impl Registry {
    pub(super) fn new() -> Result<Self> {
        let table = Arc::pin_init(new_mutex!(Vec::new()), GFP_KERNEL)?;
        let reaper = Reaper::new(table.clone())?;
        PUBLISHED
            .compare_exchange(
                ptr::null_mut(),
                ptr::from_ref(&*table).cast_mut(),
                Ordering::AcqRel,
                Ordering::Acquire,
            )
            .map_err(|_| EBUSY)?;
        reaper.activate();
        Ok(Self { reaper, table })
    }
}

impl Drop for Registry {
    fn drop(&mut self) {
        // Every published process is held by at least one IHK-owned file
        // binding, whose mcctrl module reference excludes registry destruction.
        self.reaper.stop();
        assert!(self.table.lock().is_empty());
        assert!(
            PUBLISHED.swap(ptr::null_mut(), Ordering::AcqRel)
                == ptr::from_ref(&*self.table).cast_mut()
        );
    }
}

struct ReaperContext {
    table: Arc<Table>,
    entered: Arc<AtomicBool>,
}

struct Reaper {
    task: *mut bindings::task_struct,
    context: *mut ReaperContext,
    entered: Arc<AtomicBool>,
}

// SAFETY: Only Registry activates this owned task and its unique destructor
// stops/joins it. Callback ownership is tracked independently of task entry.
unsafe impl Send for Reaper {}
// SAFETY: Shared Reaper access cannot transfer its task/context ownership; only
// its unique destructor stops and joins the task before either pointer is freed.
unsafe impl Sync for Reaper {}

impl Reaper {
    fn new(table: Arc<Table>) -> Result<Self> {
        let entered = Arc::new(AtomicBool::new(false), GFP_KERNEL)?;
        let context = Box::into_raw(Box::new(
            ReaperContext {
                table,
                entered: entered.clone(),
            },
            GFP_KERNEL,
        )?);
        // SAFETY: The context transfers only if the stopped task actually enters.
        let task = unsafe {
            bindings::kthread_create_on_node(
                Some(reap),
                context.cast(),
                -1,
                kernel::c_str!("mck-worker-reap").as_char_ptr(),
            )
        };
        if task.is_null() || (-4095..0).contains(&(task as isize)) {
            // SAFETY: Failed creation has not transferred the unique Box context
            // to a task; this is its sole from_raw reconstruction and drop.
            unsafe { drop(Box::from_raw(context)) };
            return Err(if task.is_null() {
                ENOMEM
            } else {
                errno(task as isize as i32)
            });
        }
        // No fallible allocation after task creation can lose this task owner.
        Ok(Self {
            task,
            context,
            entered,
        })
    }

    fn activate(&self) {
        // SAFETY: Registry calls once after successful table publication.
        unsafe { bindings::wake_up_process(self.task) };
    }

    fn stop(&mut self) {
        if self.task.is_null() {
            return;
        }
        // SAFETY: The task and its callback code stay resident through this join.
        unsafe { bindings::kthread_stop(self.task) };
        self.task = ptr::null_mut();
        if !self.entered.load(Ordering::Acquire) {
            // A never-entered stopped task did not consume the unique Box.
            // SAFETY: The completed join and false entered flag prove reap never
            // reconstructed this unique context, so this is its sole reclamation.
            unsafe { drop(Box::from_raw(self.context)) };
        }
    }
}

impl Drop for Reaper {
    fn drop(&mut self) {
        self.stop();
    }
}

// SAFETY: Only the successfully created task can take this context. Registry
// joins the task before freeing its table or allowing module-code retirement.
unsafe extern "C" fn reap(context: *mut c_void) -> i32 {
    let context = unsafe { Box::from_raw(context.cast::<ReaperContext>()) };
    context.entered.store(true, Ordering::Release);
    let mut cursor = 0usize;
    while !unsafe { bindings::kthread_should_stop() } {
        let mut batch: [Option<Arc<Process>>; 16] = core::array::from_fn(|_| None);
        {
            let entries = context.table.lock();
            let count = entries.len().min(batch.len());
            for destination in &mut batch[..count] {
                let index = cursor % entries.len();
                *destination = Some(entries[index].process.clone());
                cursor = cursor.wrapping_add(1);
            }
        }
        for process in batch.into_iter().flatten() {
            {
                // WORKER_CLOSE never waits for guest publication. Borrow under
                // this short mutex, so observational clones cannot defer cleanup
                // past the final binding's detach_owners call.
                let registration = process.registration.lock();
                if let Some(registration) = &*registration {
                    if let Err(error) = registration.reap_workers() {
                        if registration
                            .reap_error
                            .compare_exchange(
                                0,
                                error.to_errno(),
                                Ordering::AcqRel,
                                Ordering::Acquire,
                            )
                            .is_ok()
                        {
                            pr_err!("application_worker=reap_retained os={} generation={} pid={} errno={}\n",
                            registration.slot, registration.generation, registration.pid, error.to_errno());
                        }
                    }
                }
            }
            if !process.pid.group_alive() {
                // File bindings may outlive a dead TGID through inheritance.
                // VMAs and in-flight calls still retain their independent Arc;
                // final cleanup cannot free pages under a surviving mirror.
                process.detach_owners();
            }
        }
        // Bounded snapshots prevent one large inherited-file registry from
        // monopolizing a CPU. This scan does not depend on another ioctl.
        // SAFETY: reap is a kernel-thread callback in sleepable process context;
        // no registry mutex or borrowed process state is held across this delay.
        unsafe { bindings::msleep(10) };
    }
    0
}

fn table() -> &'static Table {
    let table = PUBLISHED.load(Ordering::Acquire);
    assert!(!table.is_null());
    // SAFETY: Only IHK-pinned mcctrl file callbacks and binding destructors call
    // this private helper; the owning Registry outlives all of those callers.
    unsafe { &*table }
}

struct Binding(Arc<Process>);

impl Binding {
    fn acquire(slot: u32, generation: u64, pid: ProcessId) -> Result<Self> {
        let mut entries = table().lock();
        for entry in &mut *entries {
            if entry.process.matches(slot, generation, &pid) {
                entry.files = entry
                    .files
                    .checked_add(1)
                    .ok_or_else(|| kernel::error::to_result(-75).unwrap_err())?;
                return Ok(Self(entry.process.clone()));
            }
        }
        let process = Arc::pin_init(
            try_pin_init!(Process {
                slot, generation, executable <- new_mutex!(None),
                registration <- new_mutex!(None), pid,
            }),
            GFP_KERNEL,
        )?;
        entries.push(
            Entry {
                process: process.clone(),
                files: 1,
            },
            GFP_KERNEL,
        )?;
        Ok(Self(process))
    }
}

impl Drop for Binding {
    fn drop(&mut self) {
        let removed = {
            let mut entries = table().lock();
            let index = entries
                .iter()
                .position(|entry| Arc::ptr_eq(&entry.process, &self.0))
                .expect("native process binding lost its registry entry");
            assert!(entries[index].files != 0);
            entries[index].files -= 1;
            if entries[index].files == 0 {
                Some(entries.swap_remove(index))
            } else {
                None
            }
        };
        if removed.is_some() {
            // A reaper snapshot can retain Process beyond close. Explicitly
            // detach its owners here, after releasing the global table lock.
            self.0.detach_owners();
        }
        drop(removed);
    }
}

pub(super) struct Context {
    pub(super) slot: u32,
    pub(super) generation: u64,
    bindings: Pin<Box<Mutex<Vec<Binding>>>>,
}

impl Context {
    pub(super) fn new(slot: u32, generation: u64) -> Result<Self> {
        Ok(Self {
            slot,
            generation,
            bindings: Box::pin_init(new_mutex!(Vec::new()), GFP_KERNEL)?,
        })
    }

    fn process(&self) -> Result<Arc<Process>> {
        let pid = ProcessId::current()?;
        let mut bindings = self.bindings.lock();
        for binding in &*bindings {
            if binding.0.pid.same(&pid) {
                return Ok(binding.0.clone());
            }
        }
        // Lock order: file bindings -> global process table; neither path takes
        // those locks while holding the per-process executable mutex.
        let binding = Binding::acquire(self.slot, self.generation, pid)?;
        let process = binding.0.clone();
        bindings.push(binding, GFP_KERNEL)?;
        Ok(process)
    }

    pub(super) fn open_executable(&self, argument: usize) -> Result<isize> {
        // All pathname reads, VFS hooks, exclusion and canonical-path checks
        // finish before acquiring any publication lock. Failure preserves the
        // process's previous executable and balances the temporary file owner.
        let executable = Executable::open(argument)?;
        self.process()?.replace(Some(executable));
        Ok(0)
    }

    pub(super) fn close_executable(&self) -> Result<isize> {
        let pid = ProcessId::current()?;
        let process = {
            let entries = table().lock();
            entries
                .iter()
                .find(|entry| entry.process.matches(self.slot, self.generation, &pid))
                .map(|entry| entry.process.clone())
        };
        // Preserve mcctrl_control_close_exec_body_result's unusual positive
        // EINVAL when no executable exists, including a repeated close.
        Ok(if process.is_some_and(|process| process.replace(None)) {
            0
        } else {
            22
        })
    }

    /// Dormant actual consumer; CREATE_PPD does not select it. A real bridge
    /// and revoke/final-destructor/ACK integration are required before runtime.
    #[allow(dead_code)]
    pub(super) unsafe fn adopt_fork_candidate<B: ForkBackend>(
        &self, argument: usize, compat: bool, parent: Arc<Registration>, backend: &B,
    ) -> Result<isize> {
        let descriptor = ForkDescriptor::read(argument, compat)?;
        let end = descriptor.end()?;
        if parent.slot != self.slot || parent.generation == 0
            || parent.generation != self.generation { return Err(EACCES); }
        let process = self.process()?;
        let current = ProcessId::current()?;
        if !process.pid.same(&current) { return Err(EACCES); }
        // Reserve local eligibility before opening an additional descriptor.
        // The short check is repeated with the final publication guard below.
        if process.registration.lock().is_some() { return Err(EINVAL); }
        let parent_mirror = parent.mapping.lock().clone().ok_or(EINVAL)?;
        if descriptor.start != parent_mirror.start || end != parent_mirror.end {
            return Err(EINVAL);
        }
        let child = Registration::acquire(self.slot, self.generation, current)?;
        child.validate_inherited_child(&parent)?;
        // No MM or local publication lock spans backend discovery/reservation.
        let mut lease = backend.reserve(&parent, &child, descriptor)?;
        let mut publication = process.registration.lock();
        if publication.is_some() {
            drop(publication);
            drop(lease); // Cancel only after releasing local publication lock.
            return Err(EINVAL);
        }
        let mut mapping = child.mapping.lock();
        if mapping.is_some() {
            drop(mapping);
            drop(publication);
            drop(lease);
            return Err(EINVAL);
        }
        // SAFETY: The typed backend lease pins the exact authenticated parent
        // delivery and child identity/root. Both local publication slots are
        // reserved. The closure only seals that lease; it cannot drop it or
        // perform a fallible/external operation under the real MM/VMA locks.
        let inherited = unsafe { Mirror::inherit_vmas(&parent_mirror, &parent,
            child.clone(), descriptor.start, end, |_| lease.seal()) };
        match inherited {
            Ok(mirror) => {
                // Real MM/VMA write exclusion is already released. These
                // retained guards make publication infallible and race-free.
                *mapping = Some(mirror);
                child.armed.store(true, Ordering::Release);
                *publication = Some(child.clone());
                drop(mapping);
                drop(publication);
                // Pending cancellation/destructors may proceed only now, and
                // still cannot free a root without real revoke/final ACK.
                lease.finish();
                Ok(0)
            }
            Err(error) => {
                drop(mapping);
                drop(publication);
                drop(lease); // Pre-mutation abort retains exact backend owner.
                Err(error)
            }
        }
    }

    /// Actual private bridge consumer, deliberately unselected by CREATE_PPD.
    #[allow(dead_code)]
    pub(super) fn adopt_fork_private(&self, argument: usize, compat: bool) -> Result<isize> {
        let descriptor = ForkDescriptor::read(argument, compat)?;
        let process = self.process()?;
        let current = ProcessId::current()?;
        if !process.pid.same(&current) { return Err(EACCES); }
        if process.registration.lock().is_some() { return Err(EINVAL); }
        let (parent_mirror, parent) = Mirror::inherited_registration(descriptor.start, descriptor.end()?)?;
        if parent.slot != self.slot || parent.generation != self.generation || self.generation == 0 {
            return Err(EACCES);
        }
        let child = Registration::acquire(self.slot, self.generation, current)?;
        child.validate_inherited_child(&parent)?;
        let geometry = super::application_abi::ForkGeometryV1 {
            root: descriptor.root, start: descriptor.start, length: descriptor.length,
        };
        let mut attempt = ForkAttempt { process: &process, parent: &parent, child: &child,
            parent_mirror: &parent_mirror, descriptor, called: false, published: false };
        // SAFETY: Both referenced Registrations pin their successful module
        // connections. IHK/provider validate exact same-generation ownership;
        // the callback borrows this exclusive stack only until return. No
        // MM/publication lock spans dispatch, finish or cancellation.
        let attempt_context = ptr::from_mut(&mut attempt).cast();
        // IHK reserves phase0 storage and its independent mcctrl module lease
        // before the actual preview constructor, and all allocation completes
        // before this attempt's separate MM callback can seal inherited VMAs.
        let status = unsafe { ihk_os_application_adopt_fork_v2(parent.context.as_ptr(),
            child.context.as_ptr(), &geometry, super::THIS_MODULE.as_ptr().cast(),
            Some(fork_proof_initial_construct), attempt_context,
            Some(fork_proof_destroy), Some(fork_verify_host), Some(fork_proof_accept),
            Some(fork_verify_link), Some(fork_adopt_consumer), attempt_context) };
        kernel::error::to_result(status)?;
        if !attempt.called || !attempt.published { return Err(errno(-71)); }
        Ok(0)
    }

    pub(super) fn create_process(&self, argument: usize, compat: bool) -> Result<isize> {
        if argument != 0 {
            // Legacy non-null CREATE_PPD also clears Linux mirror VMAs after
            // fork. Preserve real user-copy failures, but do not claim that VM
            // operation until its adapter exists. No registration is published.
            let mut descriptor = [0u8; 24];
            let bytes = if compat { 12 } else { 24 };
            UserSlice::new(argument, bytes)
                .reader()
                .read_slice(&mut descriptor[..bytes])?;
            return Err(kernel::error::to_result(-95).unwrap_err());
        }
        let process = self.process()?;
        if process.registration.lock().is_some() {
            return Err(EINVAL);
        }
        let pid = process.pid.number()?;
        let registration =
            Registration::acquire(self.slot, self.generation, ProcessId::current()?)?;
        {
            let mut published = process.registration.lock();
            if published.is_some() {
                return Err(EINVAL);
            }
            registration.armed.store(true, Ordering::Release);
            *published = Some(registration);
        }
        pr_info!(
            "application_process=registered os={} generation={} pid={}\n",
            self.slot,
            self.generation,
            pid
        );
        Ok(0)
    }

    fn registered(&self) -> Result<Arc<Registration>> {
        let process = self.process()?;
        let registration = process.registration.lock().clone().ok_or(EINVAL)?;
        Ok(registration)
    }

    pub(super) fn prepare_image(&self, argument: usize, compat: bool) -> Result<isize> {
        self.registered()?.prepare_image(argument, compat)
    }

    pub(super) fn start_image(&self, argument: usize, compat: bool) -> Result<isize> {
        self.registered()?.start_image(argument, compat)
    }

    pub(super) fn transfer_image(&self, argument: usize, compat: bool) -> Result<isize> {
        self.registered()?.transfer_image(argument, compat)
    }

    pub(super) fn clear_user_space(&self, argument: usize, compat: bool) -> Result<isize> {
        self.registered()?.clear_user_space(argument, compat)
    }

    pub(super) fn wait_syscall(&self, argument: usize, compat: bool) -> Result<isize> {
        self.registered()?.wait_syscall(argument, compat)
    }

    pub(super) fn return_syscall(&self, argument: usize, compat: bool) -> Result<isize> {
        self.registered()?.return_syscall(argument, compat)
    }
}
