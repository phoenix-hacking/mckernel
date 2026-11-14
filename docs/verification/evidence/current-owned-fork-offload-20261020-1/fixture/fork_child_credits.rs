//! Private normal-fork credits. No task/MM permit or terminal release exists.
//!
//! The unsafe constructor transfers the caller's existing private-child cleanup
//! obligation; pointer values/refcounts do not manufacture that ownership.
//! A checked extra parent Thread reference pins storage only. Dropping any
//! owner deliberately retains its obligations, without locking or freeing.
use core::marker::PhantomData;
use core::ptr::{addr_of_mut, NonNull};
use core::sync::atomic::{AtomicI32, Ordering};
use crate::abi::{Process, ProcessVm, SyscallRequest, Thread};
use super::{registry, Carrier, Handle, EACCES, EBUSY, EINVAL, NR_CLONE};

const EOVERFLOW: i32 = -75;

#[must_use = "private child/VM/CPU credits must be cancelled or retained"]
pub(crate) struct ChildCredits {
    parent: NonNull<Thread>,
    child: NonNull<Thread>,
    process: NonNull<Process>,
    vm: NonNull<ProcessVm>,
    reserved_cpu: i32,
}

/// Exactly the original caller's cleanup obligation, returned once. No new
/// child/process/VM reference or CPU reservation was acquired by this module.
#[must_use]
pub(crate) struct CallerCredits {
    pub(crate) child: NonNull<Thread>,
    pub(crate) process: NonNull<Process>,
    pub(crate) vm: NonNull<ProcessVm>,
    pub(crate) reserved_cpu: i32,
}

impl ChildCredits {
    /// # Safety
    /// Caller exclusively owns the successful non-CLONE_VM constructor's
    /// unpublished child/process/VM and exact reserved CPU cleanup credits.
    /// Transfer means it must not reset/release those credits while this owner
    /// exists. Parent is the already-live current Thread; no pin is inferred
    /// from a numeric counter or host ParentSlotPin.
    pub(crate) unsafe fn acquire(
        parent: *mut Thread, child: *mut Thread, reserved_cpu: i32,
    ) -> Result<Self, i32> {
        let parent = NonNull::new(parent).ok_or(EINVAL)?;
        let child = NonNull::new(child).ok_or(EINVAL)?;
        if parent == child || reserved_cpu < 0 { return Err(EINVAL); }
        let current = crate::cls::get_this_cpu_local_var();
        if current.is_null() || (*current).current != parent.as_ptr() { return Err(EACCES); }
        let process = NonNull::new((*child.as_ptr()).proc).ok_or(EINVAL)?;
        let vm = NonNull::new((*child.as_ptr()).vm).ok_or(EINVAL)?;
        if (*parent.as_ptr()).proc.is_null() || process.as_ptr() == (*parent.as_ptr()).proc
            || vm.as_ptr() == (*parent.as_ptr()).vm
            || (*process.as_ptr()).parent != (*parent.as_ptr()).proc
            || (*process.as_ptr()).main_thread != child.as_ptr()
            || (*process.as_ptr()).vm != vm.as_ptr()
            || (*vm.as_ptr()).proc != process.as_ptr().cast()
            || (*child.as_ptr()).cpu_id != reserved_cpu
            || !(*child.as_ptr()).sched_list.next.is_null()
            || !(*child.as_ptr()).sched_list.prev.is_null()
        { return Err(EACCES); }
        // This is the actual production IhkAtomic counter, not a shadow count.
        // SeqCst matches existing ref helpers. The live-current premise keeps
        // storage valid before the successful CAS obtains our additional pin.
        let counter = AtomicI32::from_ptr(addr_of_mut!((*parent.as_ptr()).refcount.counter));
        let mut old = counter.load(Ordering::SeqCst);
        loop {
            if old <= 0 { return Err(EBUSY); }
            if old == i32::MAX { return Err(EOVERFLOW); }
            match counter.compare_exchange_weak(old, old + 1, Ordering::SeqCst, Ordering::SeqCst) {
                Ok(_) => break,
                Err(actual) => old = actual,
            }
        }
        Ok(Self { parent, child, process, vm, reserved_cpu })
    }

    unsafe fn still_private(&self) -> bool {
        let current = crate::cls::get_this_cpu_local_var();
        !current.is_null() && (*current).current == self.parent.as_ptr()
            && (*self.child.as_ptr()).proc == self.process.as_ptr()
            && (*self.child.as_ptr()).vm == self.vm.as_ptr()
            && (*self.child.as_ptr()).cpu_id == self.reserved_cpu
            && (*self.process.as_ptr()).main_thread == self.child.as_ptr()
            && (*self.process.as_ptr()).vm == self.vm.as_ptr()
            && (*self.vm.as_ptr()).proc == self.process.as_ptr().cast()
            && (*self.child.as_ptr()).sched_list.next.is_null()
            && (*self.child.as_ptr()).sched_list.prev.is_null()
    }

    /// Only a credit owner that has never entered Carrier can call this.
    /// The actual parent reference release runs outside every registry guard.
    pub(crate) unsafe fn cancel_unpublished(self) -> Result<CallerCredits, Self> {
        if !self.still_private() { return Err(self); }
        let returned = CallerCredits { child: self.child, process: self.process,
            vm: self.vm, reserved_cpu: self.reserved_cpu };
        crate::process_helpers::release_thread(self.parent.as_ptr());
        Ok(returned)
    }
}

#[must_use]
pub(crate) struct PrivateFork<'request> {
    handle: Handle,
    request: NonNull<SyscallRequest>,
    original_args: [u64; 6],
    credits: Option<ChildCredits>,
    retained: bool,
    request_lifetime: PhantomData<&'request mut SyscallRequest>,
}

#[must_use]
pub(crate) struct EscapedFork<'request> {
    handle: Handle,
    request: NonNull<SyscallRequest>,
    request_lifetime: PhantomData<&'request mut SyscallRequest>,
}

#[must_use]
pub(crate) struct RetainedFork { handle: Handle, pub(crate) error: i32 }

pub(crate) struct CreateFailure { pub(crate) error: i32, pub(crate) credits: ChildCredits }
pub(crate) struct PrivateFailure<'request> { pub(crate) error: i32, pub(crate) owner: PrivateFork<'request> }
pub(crate) enum BeginFailure<'request> {
    Private(PrivateFailure<'request>),
    Retained(RetainedFork),
}

impl<'request> PrivateFork<'request> {
    /// Uses the actual current carrier constructor and fixed registry. No
    /// external request publication occurs here. On refusal the same credit
    /// owner returns to the caller, with request/child/VM/CPU unchanged.
    pub(crate) unsafe fn create(
        request: &'request mut SyscallRequest, credits: ChildCredits,
    ) -> Result<Self, CreateFailure> {
        let original_args = request.args;
        let mut handle = Handle::EMPTY;
        let error = super::process_fork_guest_carrier_create_current_v1(
            request, credits.parent.as_ptr(), credits.child.as_ptr(), &mut handle);
        if error != 0 { return Err(CreateFailure { error, credits }); }
        Ok(Self { handle, request: NonNull::from(request), original_args,
            credits: Some(credits), retained: false, request_lifetime: PhantomData })
    }

    unsafe fn validate(&self, carrier: &Carrier) -> bool {
        let Some(credits) = self.credits.as_ref() else { return false; };
        let request = self.request.as_ref();
        !self.retained && credits.still_private() && carrier.handle == self.handle
            && carrier.parent == credits.parent.as_ptr() as usize
            && carrier.child == credits.child.as_ptr() as usize
            && carrier.request == self.request.as_ptr() as usize
            && carrier.owned_credits.is_none() && request.number == NR_CLONE
            && request.args == carrier.initial_args
    }

    /// Restores args4/5 before detaching the still-private registry allocation.
    /// Only this non-Copy ticket can name its private handle. Failed detach is
    /// conservatively retained and never returns caller cleanup authority.
    pub(crate) unsafe fn cancel(mut self) -> Result<CallerCredits, PrivateFailure<'request>> {
        let rc = registry::visit(self.handle, |pointer| {
            if !self.validate(pointer.as_ref()) { return EACCES; }
            let request = self.request.as_mut();
            request.args[4] = self.original_args[4];
            request.args[5] = self.original_args[5];
            0
        });
        if rc != 0 { return Err(PrivateFailure { error: rc, owner: self }); }
        let pointer = match registry::cancel(self.handle) {
            Ok(pointer) => pointer,
            Err(error) => {
                self.retained = true;
                let _ = registry::retain(self.handle);
                return Err(PrivateFailure { error, owner: self });
            }
        };
        // Cancel returned this allocation only after releasing registry lock.
        crate::mem_helpers::kfree(pointer.as_ptr().cast());
        let credits = self.credits.take().unwrap();
        // The validation above proves this current-parent release cannot be a
        // last-reference destructor; no child/process/VM/CPU credit is changed.
        match credits.cancel_unpublished() {
            Ok(returned) => Ok(returned),
            Err(credits) => {
                self.credits = Some(credits);
                self.retained = true;
                Err(PrivateFailure { error: EBUSY, owner: self })
            }
        }
    }

    /// Moves all credits into the actual immovable Carrier before registry
    /// begin makes it discoverable. After this move no cancellation API can
    /// recover credits: existing Escaped/Retained guards reject registry.cancel.
    pub(crate) unsafe fn begin(mut self) -> Result<EscapedFork<'request>, BeginFailure<'request>> {
        let rc = registry::visit(self.handle, |mut pointer| {
            if !self.validate(pointer.as_ref()) { return EACCES; }
            pointer.as_mut().owned_credits = self.credits.take();
            0
        });
        if rc != 0 {
            if self.credits.is_some() {
                return Err(BeginFailure::Private(PrivateFailure { error: rc, owner: self }));
            }
            let _ = registry::retain(self.handle);
            return Err(BeginFailure::Retained(RetainedFork { handle: self.handle, error: rc }));
        }
        match registry::begin(self.handle) {
            Ok(_) => Ok(EscapedFork { handle: self.handle, request: self.request,
                request_lifetime: PhantomData }),
            Err(error) => {
                let _ = registry::retain(self.handle);
                Err(BeginFailure::Retained(RetainedFork { handle: self.handle, error }))
            }
        }
    }
}

/// Every post-begin outcome retains the original child, VM and reserved CPU
/// credits in the Carrier. A positive receipt is host observation only; neither
/// branch grants the C caller destroy_thread/refcount-reset/release_cpuid rights.
#[must_use = "the retained child/VM/CPU owner must survive this offload outcome"]
pub(crate) enum OwnedOffloadReturn {
    ReceiptObserved { child_pid: i32, owner: RetainedFork },
    Uncertain { actual: Option<i64>, owner: RetainedFork },
}

impl EscapedFork<'_> {
    pub(crate) fn handle(&self) -> Handle { self.handle }

    /// # Safety
    /// Original constructor/current-parent exclusivity continues to hold. No
    /// raw-handle API or other producer may submit/mutate this transaction.
    /// Consumes this owner and submits the SAME borrowed request exactly once;
    /// no stack copy or registry guard survives into the actual synchronous FFI.
    /// Any post-begin refusal, missing receipt, or transport result retains all
    /// credits. The stack request borrow ends only when this method returns.
    pub(crate) unsafe fn offload(self) -> OwnedOffloadReturn {
        let mut cpu = -1;
        let prepared = registry::visit(self.handle, |pointer| {
            let c = pointer.as_ref();
            let Some(credits) = c.owned_credits.as_ref() else { return EACCES; };
            let local = crate::cls::get_this_cpu_local_var();
            if c.handle != self.handle || c.request != self.request.as_ptr() as usize
                || local.is_null() || (*local).current != credits.parent.as_ptr()
                || c.parent != credits.parent.as_ptr() as usize
                || c.child != credits.child.as_ptr() as usize
                || c.cpu < 0 || (*credits.parent.as_ptr()).cpu_id != c.cpu
                || !credits.still_private() || c.phase != super::SUBMITTED
                || c.error != 0 || self.request.as_ref().number != NR_CLONE
                || self.request.as_ref().args != c.initial_args
            { return EACCES; }
            cpu = c.cpu;
            0
        });
        if prepared != 0 {
            return OwnedOffloadReturn::Uncertain { actual: None,
                owner: self.retain(prepared) };
        }
        let actual = super::do_syscall(self.request.as_ptr(), cpu);
        // The existing actual return hook must already have accepted the exact
        // response. A positive scalar alone never authenticates a first receipt.
        let mut child_pid = 0;
        let observed = registry::visit(self.handle, |pointer| {
            let c = pointer.as_ref();
            if c.handle != self.handle || c.request != self.request.as_ptr() as usize
                || c.owned_credits.is_none() || c.phase != super::FIRST_POSITIVE
                || c.error != 0 || actual <= 0 || i64::from(c.identity.child_pid) != actual
                || !super::carrier_geometry(c, &c.identity)
            { return if c.error != 0 { c.error } else if actual <= 0 {
                    super::transport_error(actual)
                } else { super::EPROTO }; }
            child_pid = c.identity.child_pid;
            0
        });
        let owner = self.retain(observed);
        if observed == 0 { OwnedOffloadReturn::ReceiptObserved { child_pid, owner } }
        else { OwnedOffloadReturn::Uncertain { actual: Some(actual), owner } }
    }

    // Private: external callers cannot assert that the offload already returned.
    unsafe fn retain(self, error: i32) -> RetainedFork {
        let _ = registry::retain(self.handle);
        RetainedFork { handle: self.handle, error }
    }
}

impl RetainedFork {
    pub(crate) fn handle(&self) -> Handle { self.handle }
    pub(crate) fn caller_cleanup_allowed(&self) -> bool { false }
}

#[cfg(test)]
pub(crate) mod offload_tests {
    use super::*;
    use crate::abi::{CpuLocalVar, Process, ProcessVm, SyscallRequest, SyscallResponse, Thread};
    use std::sync::atomic::{AtomicI64, AtomicUsize, Ordering};
    static EXPECTED_REQUEST: AtomicUsize = AtomicUsize::new(0);
    static EXPECTED_ARGS: std::sync::Mutex<[u64; 6]> = std::sync::Mutex::new([0; 6]);
    static TRANSPORT_RESULT: AtomicI64 = AtomicI64::new(-5);
    static RECEIPT: AtomicUsize = AtomicUsize::new(0);
    struct Objects {
        parent: *mut Thread, child: *mut Thread, process: *mut Process,
        vm: *mut ProcessVm,
    }
    impl Objects {
        unsafe fn new() -> Self {
            // Each C-ABI object is a distinct real full production layout.
            // Escaped/error owners retain these allocations; the fixture never
            // frees a static arena or invents a guest reset/terminal release.
            let parent = Box::into_raw(Box::new(core::mem::zeroed::<Thread>()));
            let child = Box::into_raw(Box::new(core::mem::zeroed::<Thread>()));
            let parent_proc = Box::into_raw(Box::new(core::mem::zeroed::<Process>()));
            let parent_vm = Box::into_raw(Box::new(core::mem::zeroed::<ProcessVm>()));
            let process = Box::into_raw(Box::new(core::mem::zeroed::<Process>()));
            let vm = Box::into_raw(Box::new(core::mem::zeroed::<ProcessVm>()));
            let local = Box::into_raw(Box::new(core::mem::zeroed::<CpuLocalVar>()));
            (*parent).proc = parent_proc; (*parent).vm = parent_vm;
            (*parent).refcount.counter = 1; (*parent).tid = 19; (*parent).cpu_id = 0;
            (*parent_proc).vm = parent_vm; (*parent_proc).main_thread = parent;
            (*parent_vm).proc = parent_proc.cast();
            (*child).proc = process; (*child).vm = vm; (*child).cpu_id = 1;
            (*child).refcount.counter = 2;
            (*process).parent = parent_proc; (*process).main_thread = child;
            (*process).vm = vm; (*process).refcount.counter = 2;
            (*vm).proc = process.cast(); (*vm).refcount.counter = 2;
            (*local).current = parent; crate::cls::set(local);
            Self { parent, child, process, vm }
        }
        unsafe fn counts(&self) -> [i32; 4] {
            [(*self.parent).refcount.counter, (*self.child).refcount.counter,
             (*self.process).refcount.counter, (*self.vm).refcount.counter]
        }
        unsafe fn acquire(&self) -> ChildCredits {
            ChildCredits::acquire(self.parent, self.child, 1).ok().expect("authentic current private child")
        }
    }
    fn request() -> SyscallRequest {
        let mut request: SyscallRequest = unsafe { core::mem::zeroed() };
        request.number = 56;
        request.args = [0, 0x1000, 0x2000, 0x4000, 0xa000, 0xb000];
        request
    }


    pub(crate) unsafe fn transport(request: *mut SyscallRequest, cpu: i32) -> i64 {
        assert_eq!(request as usize, EXPECTED_REQUEST.load(Ordering::SeqCst));
        assert_eq!((*request).args, *EXPECTED_ARGS.lock().unwrap());
        assert_eq!(cpu, 0);
        let actual = TRANSPORT_RESULT.load(Ordering::SeqCst);
        if RECEIPT.load(Ordering::SeqCst) == 0 { return actual; }
        let thread = (*crate::cls::get_this_cpu_local_var()).current;
        (*request).rtid = (*thread).tid; (*request).ttid = 0; (*request).valid = 0;
        let mut handles = [Handle::EMPTY; registry::CAPACITY];
        registry::snapshot_handles(&mut handles);
        let handle = handles.into_iter().find(|h| {
            if h.epoch == 0 { return false; }
            registry::visit(*h, |p| i32::from(p.as_ref().request == request as usize)) == 1
        }).expect("actual escaped request is discoverable");
        assert_eq!(registry::visit(handle, |mut pointer| {
            let c = pointer.as_mut(); let frame = &mut c.bytes;
            frame.fill(0); frame[..8].copy_from_slice(b"MCFKW001");
            frame[8..12].copy_from_slice(&[1, 0, 40, 0]);
            frame[12..16].copy_from_slice(&128u32.to_le_bytes());
            frame[16..20].copy_from_slice(&1u32.to_le_bytes());
            super::super::put(frame, 24, 1); super::super::put(frame, 32, actual as u64);
            frame[40..44].copy_from_slice(&3u32.to_le_bytes());
            frame[44..48].copy_from_slice(&(actual as i32).to_le_bytes());
            for (at, value) in [(48, 7), (56, c.parent as u64), (64, 8), (72, 9),
                (80, c.child as u64), (88, 0x9000), (96, c.root), (104, c.start),
                (112, c.length), (120, c.nonce)] { super::super::put(frame, at, value); }
            0
        }), 0);
        let mut response: SyscallResponse = core::mem::zeroed();
        response.ret = actual; response.stid = 17; response.status = 1;
        // The unchanged production observer, its Acquire helper and first-receipt
        // parser consume this adapter response; no direct phase/identity injection.
        super::super::observe_fork_control_reply(request, &mut response, cpu, thread);
        actual
    }

    unsafe fn setup<'a>(objects: &Objects, request: &'a mut SyscallRequest, actual: i64,
        receipt: bool) -> EscapedFork<'a> {
        EXPECTED_REQUEST.store(request as *mut _ as usize, Ordering::SeqCst);
        TRANSPORT_RESULT.store(actual, Ordering::SeqCst);
        RECEIPT.store(usize::from(receipt), Ordering::SeqCst);
        let owner = PrivateFork::create(request, objects.acquire()).ok().expect("private owner");
        *EXPECTED_ARGS.lock().unwrap() = owner.request.as_ref().args;
        owner.begin().ok().expect("actual begin")
    }
    unsafe fn assert_retained(objects: &Objects, owner: RetainedFork, frees: usize) {
        assert!(!owner.caller_cleanup_allowed());
        assert!(matches!(registry::cancel(owner.handle()), Err(EBUSY)));
        assert_eq!(registry::visit(owner.handle(), |pointer| {
            let credits = pointer.as_ref().owned_credits.as_ref().expect("durable credits");
            assert_eq!(credits.parent.as_ptr(), objects.parent);
            assert_eq!(credits.child.as_ptr(), objects.child);
            assert_eq!(credits.process.as_ptr(), objects.process);
            assert_eq!(credits.vm.as_ptr(), objects.vm); assert_eq!(credits.reserved_cpu, 1);
            0
        }), 0);
        drop(owner);
        assert_eq!(objects.counts(), [2, 2, 2, 2]);
        assert_eq!(crate::mem_helpers::frees(), frees);
        assert_eq!(crate::DESTRUCTORS.load(Ordering::SeqCst), 0);
    }
    #[test]
    fn owned_offload_negative_retains_same_request_and_all_credits() { unsafe {
        let objects = Objects::new(); let mut request = request();
        let escaped = setup(&objects, &mut request, -5, false);
        let calls = crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        let frees = crate::mem_helpers::frees();
        match escaped.offload() {
            OwnedOffloadReturn::Uncertain { actual, owner } => {
                assert_eq!(actual, Some(-5)); assert_eq!(owner.error, -5);
                assert_retained(&objects, owner, frees);
            }, _ => panic!("negative result cannot be successful observation"),
        }
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst), calls + 1);
    } }
    #[test]
    fn owned_offload_actual_observer_positive_still_retains() { unsafe {
        let objects = Objects::new(); let mut request = request();
        let escaped = setup(&objects, &mut request, 123, true);
        let calls = crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        let frees = crate::mem_helpers::frees();
        match escaped.offload() {
            OwnedOffloadReturn::ReceiptObserved { child_pid, owner } => {
                assert_eq!(child_pid, 123); assert_eq!(owner.error, 0);
                assert_retained(&objects, owner, frees);
            }, _ => panic!("actual observer receipt should be reported"),
        }
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst), calls + 1);
    } }
    #[test]
    fn owned_offload_positive_without_receipt_is_uncertain() { unsafe {
        let objects = Objects::new(); let mut request = request();
        let escaped = setup(&objects, &mut request, 123, false);
        let calls = crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        let frees = crate::mem_helpers::frees();
        match escaped.offload() {
            OwnedOffloadReturn::Uncertain { actual, owner } => {
                assert_eq!(actual, Some(123)); assert_eq!(owner.error, super::super::EPROTO);
                assert_retained(&objects, owner, frees);
            }, _ => panic!("scalar result cannot invent a receipt"),
        }
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst), calls + 1);
    } }
    #[test]
    fn owned_offload_postbegin_refusal_retains_but_prebegin_cancel_returns() { unsafe {
        let objects = Objects::new(); let mut request1 = request();
        let owner = PrivateFork::create(&mut request1, objects.acquire()).ok().unwrap();
        let returned = owner.cancel().ok().expect("actual private cancellation");
        assert_eq!(returned.child.as_ptr(), objects.child);
        assert_eq!(returned.process.as_ptr(), objects.process);
        assert_eq!(returned.vm.as_ptr(), objects.vm); assert_eq!(returned.reserved_cpu, 1);
        assert_eq!(objects.counts(), [1, 2, 2, 2]);
        let mut request2 = request();
        let mut escaped = setup(&objects, &mut request2, 123, false);
        escaped.request.as_mut().args[4] ^= 8;
        let calls = crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        let frees = crate::mem_helpers::frees();
        match escaped.offload() {
            OwnedOffloadReturn::Uncertain { actual, owner } => {
                assert_eq!(actual, None); assert_eq!(owner.error, EACCES);
                assert_retained(&objects, owner, frees);
            }, _ => panic!("changed request refused before actual transport"),
        }
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst), calls);
    } }
}
