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
            Ok(_) => Ok(EscapedFork { handle: self.handle, request_lifetime: PhantomData }),
            Err(error) => {
                let _ = registry::retain(self.handle);
                Err(BeginFailure::Retained(RetainedFork { handle: self.handle, error }))
            }
        }
    }
}

impl EscapedFork<'_> {
    pub(crate) fn handle(&self) -> Handle { self.handle }

    /// # Safety
    /// The SAME synchronous offload has returned; this does not retain its
    /// stack request. It retains parent storage + child/VM/CPU credits only.
    /// No numeric host errno, receipt, or scalar authorizes caller teardown.
    pub(crate) unsafe fn retain_after_return(self, error: i32) -> RetainedFork {
        let _ = registry::retain(self.handle);
        RetainedFork { handle: self.handle, error }
    }
}

impl RetainedFork {
    pub(crate) fn handle(&self) -> Handle { self.handle }
    pub(crate) fn caller_cleanup_allowed(&self) -> bool { false }
}
