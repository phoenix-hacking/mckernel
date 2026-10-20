//! Private normal-fork credits. No task/MM permit or terminal release exists.
//!
//! The unsafe constructor transfers the caller's existing private-child cleanup
//! obligation; pointer values/refcounts do not manufacture that ownership.
//! A checked extra parent Thread reference pins storage only. Dropping any
//! owner deliberately retains its obligations, without locking or freeing.
use core::marker::PhantomData;
use core::mem::size_of;
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
    private_child_cpu: i32,
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
        Self::acquire_with_private_cpu(parent, child, reserved_cpu, reserved_cpu)
    }

    /// Actual do_fork boundary: clone_thread initializes child.cpu_id to zero;
    /// only runq publication assigns the separately reserved CPU. This unsafe
    /// transfer takes the exact caller-owned reservation, never inferring it
    /// from the unpublished child's numeric cpu_id or acquiring another CPU.
    pub(crate) unsafe fn acquire_from_caller(
        parent: *mut Thread, child: *mut Thread, reserved_cpu: i32,
    ) -> Result<Self, i32> {
        Self::acquire_with_private_cpu(parent, child, reserved_cpu, 0)
    }

    unsafe fn acquire_with_private_cpu(
        parent: *mut Thread, child: *mut Thread, reserved_cpu: i32, private_child_cpu: i32,
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
            || (*child.as_ptr()).cpu_id != private_child_cpu
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
        Ok(Self { parent, child, process, vm, reserved_cpu, private_child_cpu })
    }

    unsafe fn still_private(&self) -> bool {
        let current = crate::cls::get_this_cpu_local_var();
        !current.is_null() && (*current).current == self.parent.as_ptr()
            && (*self.child.as_ptr()).proc == self.process.as_ptr()
            && (*self.child.as_ptr()).vm == self.vm.as_ptr()
            && (*self.child.as_ptr()).cpu_id == self.private_child_cpu
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

/// Owns the storage of the exact initial request, independently of the C
/// caller's stack or the parent Thread pin. No implicit Drop frees this slot.
/// It is either freed after private cancellation, or retained in the Carrier.
pub(crate) struct ForkRequestSlot { request: NonNull<SyscallRequest> }
impl ForkRequestSlot {
    unsafe fn allocate(flags: u64, start: u64, length: u64, root: u64) -> Result<Self, i32> {
        if matches!(flags, 1 | 2 | 3) || !super::geometry(root, start, length) {
            return Err(EINVAL);
        }
        let raw = crate::mem_helpers::kmalloc(size_of::<SyscallRequest>() as i32, 0)
            .cast::<SyscallRequest>();
        let request = NonNull::new(raw).ok_or(super::ENOMEM)?;
        // This is the original request, initialized in its retained allocation;
        // no existing/borrowed request is copied or later replaced for offload.
        core::ptr::write(raw, SyscallRequest { rtid: 0, ttid: 0, valid: 0,
            number: NR_CLONE, args: [flags, start, length, root, 0, 0] });
        Ok(Self { request })
    }
    unsafe fn free_private(self) { crate::mem_helpers::kfree(self.request.as_ptr().cast()); }
}

#[must_use]
pub(crate) struct PrivateFork<'request> {
    handle: Handle,
    request: NonNull<SyscallRequest>,
    original_args: [u64; 6],
    credits: Option<ChildCredits>,
    request_storage: Option<ForkRequestSlot>,
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
        Self::create_raw(NonNull::from(request), credits, None)
    }

    /// Normal-fork caller preparation: request bytes originate in owned heap
    /// storage, which follows the SAME request into the Carrier before begin.
    /// The lifetime parameter borrows no caller storage and no reference escapes.
    /// All child-credit constructor premises of `create` still apply.
    pub(crate) unsafe fn create_owned(
        credits: ChildCredits, flags: u64, start: u64, length: u64, root: u64,
    ) -> Result<Self, CreateFailure> {
        let slot = match ForkRequestSlot::allocate(flags, start, length, root) {
            Ok(slot) => slot, Err(error) => return Err(CreateFailure { error, credits }),
        };
        Self::create_raw(slot.request, credits, Some(slot))
    }

    unsafe fn create_raw(
        request: NonNull<SyscallRequest>, credits: ChildCredits,
        request_storage: Option<ForkRequestSlot>,
    ) -> Result<Self, CreateFailure> {
        let original_args = request.as_ref().args;
        let mut handle = Handle::EMPTY;
        let error = super::process_fork_guest_carrier_create_current_v1(
            request.as_ptr(), credits.parent.as_ptr(), credits.child.as_ptr(), &mut handle);
        if error != 0 {
            if let Some(slot) = request_storage { slot.free_private(); }
            return Err(CreateFailure { error, credits });
        }
        Ok(Self { handle, request, original_args, credits: Some(credits), request_storage,
            retained: false, request_lifetime: PhantomData })
    }

    unsafe fn validate(&self, carrier: &Carrier) -> bool {
        let Some(credits) = self.credits.as_ref() else { return false; };
        let request = self.request.as_ref();
        !self.retained && credits.still_private() && carrier.handle == self.handle
            && carrier.parent == credits.parent.as_ptr() as usize
            && carrier.child == credits.child.as_ptr() as usize
            && carrier.request == self.request.as_ptr() as usize
            && carrier.owned_credits.is_none() && carrier.owned_request.is_none()
            && self.request_storage.as_ref().is_none_or(|slot| slot.request == self.request)
            && request.number == NR_CLONE
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
            Ok(returned) => {
                if let Some(slot) = self.request_storage.take() { slot.free_private(); }
                Ok(returned)
            },
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
            pointer.as_mut().owned_request = self.request_storage.take();
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
                || c.owned_request.as_ref().is_some_and(|slot| slot.request != self.request)
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


/// C glue receives disposition metadata only. Actual post-transfer owners stay
/// in the existing durable Carrier registry; no pointer into a C stack is kept.
#[repr(C)]
pub(crate) struct CallerForkOutcome {
    pub(crate) disposition: u32,
    pub(crate) error: i32,
    pub(crate) handle: Handle,
}
const _: () = {
    assert!(size_of::<CallerForkOutcome>() == 24);
    assert!(core::mem::offset_of!(CallerForkOutcome, disposition) == 0);
    assert!(core::mem::offset_of!(CallerForkOutcome, error) == 4);
    assert!(core::mem::offset_of!(CallerForkOutcome, handle) == 8);
};
const CALLER_KEEPS_CREDITS: u32 = 0;
const RUST_RETAINS_CREDITS: u32 = 1;

/// # Safety
/// The exact current do_fork caller exclusively owns the successful unpublished
/// non-CLONE_VM constructor and reserved CPU cleanup credits. `out` is writable
/// metadata storage. This boundary never grants runnable-child or host task/MM
/// authority: even an observed positive receipt returns a retained error.
/// C must use disposition to bypass all destroy/refcount-reset/CPU cleanup when
/// Rust owns credits. The macro-gated C proposal remains disabled by default.
#[no_mangle]
pub(crate) unsafe extern "C" fn process_fork_owned_caller_current_v1(
    parent: *mut Thread, child: *mut Thread, reserved_cpu: i32, host_flags: u64,
    out: *mut CallerForkOutcome,
) -> i32 {
    if out.is_null() { return EINVAL; }
    core::ptr::write(out, CallerForkOutcome { disposition: CALLER_KEEPS_CREDITS,
        error: EINVAL, handle: Handle::EMPTY });
    if parent.is_null() || child.is_null() || reserved_cpu < 0 || (*child).vm.is_null() {
        return 0;
    }
    let vm = &*(*child).vm;
    if vm.address_space.is_null() { return 0; }
    let Some(length) = vm.region.user_end.checked_sub(vm.region.user_start) else { return 0; };
    let root = crate::x86_memory_helpers::virt_to_phys((*vm.address_space).page_table) as u64;
    // Every allocation happens while C still owns cleanup. The exact request
    // originates in retained storage; this is never a copy of request1.
    let slot = match ForkRequestSlot::allocate(host_flags, vm.region.user_start, length, root) {
        Ok(slot) => slot, Err(error) => { (*out).error = error; return 0; },
    };
    let mut pointer = match super::create_private_carrier_current(slot.request.as_ptr(), parent, child) {
        Ok(pointer) => pointer,
        Err(error) => { slot.free_private(); (*out).error = error; return 0; },
    };
    let handle = pointer.as_ref().handle;
    pointer.as_mut().owned_request = Some(slot);
    let credits = match ChildCredits::acquire_from_caller(parent, child, reserved_cpu) {
        Ok(credits) => credits,
        Err(error) => {
            // This private handle has never escaped this producer, and private
            // entries cannot be discovered by observers. No credit transferred.
            match registry::cancel(handle) {
                Ok(mut pointer) => {
                    let slot = pointer.as_mut().owned_request.take().unwrap();
                    crate::mem_helpers::kfree(pointer.as_ptr().cast()); slot.free_private();
                },
                Err(_) => {
                    // Request ownership is already durable. On unexpected
                    // busy/refusal, do not dereference a possibly busy Carrier.
                    // C still owns all child/VM/CPU cleanup; none transferred.
                    let _ = registry::retain(handle); (*out).handle = handle;
                },
            }
            (*out).error = error; return 0;
        },
    };
    // The private-producer exclusion above is still intact: finish ownership
    // initialization directly, just like the actual carrier constructor does.
    pointer.as_mut().owned_credits = Some(credits);
    (*out).disposition = RUST_RETAINS_CREDITS; (*out).handle = handle;
    let request = pointer.as_ref().owned_request.as_ref().unwrap().request;
    if let Err(error) = registry::begin(handle) {
        let _ = registry::retain(handle); (*out).error = error; return 0;
    }
    let escaped = EscapedFork { handle, request,
        request_lifetime: PhantomData };
    (*out).error = match escaped.offload() {
        OwnedOffloadReturn::ReceiptObserved { owner, .. } => {
            // Consume the actual next selector2 producer with its separately
            // owned request. This remains observation, never terminal handoff.
            let mut observation=super::ControlObservation::ZERO;
            let error=super::process_fork_guest_control_submit_current_v1(owner.handle(),&mut observation);
            drop(owner); if error==0 { EBUSY } else { error }
        },
        OwnedOffloadReturn::Uncertain { owner, .. } => owner.error,
    };
    0
}

#[cfg(test)]
pub(crate) mod control_adapter {
    use super::*;
    use crate::abi::{SyscallRequest,SyscallResponse};
    use std::sync::atomic::{AtomicI32,Ordering};
    pub(crate) static MODE:AtomicI32=AtomicI32::new(0);
    pub(crate) unsafe fn transport(request:*mut SyscallRequest,cpu:i32)->i64 {
        assert_eq!((*request).args[0],2);
        let mut handles=[Handle::EMPTY;registry::CAPACITY];registry::snapshot_handles(&mut handles);
        let handle=handles.into_iter().find(|h|h.epoch!=0 && registry::visit(*h,|p|
            i32::from(p.as_ref().control.request==request as usize))==1).expect("actual owned control request");
        assert_eq!(registry::visit(handle,|p|{
            let c=p.as_ref();let slot=c.control.owned_request.as_ref().expect("control storage owned before offload");
            assert_eq!(slot.request.as_ptr(),request);assert_ne!(request as usize,c.request);
            assert_eq!((*request).args,c.control.args);assert_eq!(c.control.state,super::super::PENDING);
            assert!(c.owned_credits.is_some());assert!(c.owned_request.is_some());0
        }),0);
        let mode=MODE.load(Ordering::SeqCst);
        if mode==1{return -5;}if mode==2{return 0;}
        let thread=(*crate::cls::get_this_cpu_local_var()).current;
        (*request).rtid=(*thread).tid;(*request).ttid=0;(*request).valid=0;
        let mut response:SyscallResponse=core::mem::zeroed();
        response.ret=0;response.stid=31;response.status=1;
        let physical=&mut response as *mut _ as u64;
        assert_eq!(registry::visit(handle,|mut p|{
            let c=p.as_mut();let frame=&mut c.bytes;let id=c.identity;
            frame.fill(0);frame[..8].copy_from_slice(b"MCFKR001");
            for(at,value)in[(8,2),(16,18),(24,19),(32,physical),(48,id.generation),
                (56,id.parent),(64,id.worker),(72,id.delivery),(80,id.child),(88,id.child_mm),
                (96,id.root),(104,id.start),(112,id.length),(120,id.nonce)]{
                super::super::put(frame,at,value);
            }
            frame[40..44].copy_from_slice(&id.slot.to_le_bytes());
            frame[44..48].copy_from_slice(&id.child_pid.to_le_bytes());
            if mode==4{super::super::put(frame,64,id.worker+1);}0
        }),0);
        super::super::observe_fork_control_reply(request,&mut response,cpu,thread);0
    }
}

#[cfg(test)]
pub(crate) mod next_transition_tests {
    use super::*;
    use crate::abi::{CpuLocalVar,Process,ProcessVm,SyscallRequest,SyscallResponse,Thread};
    use std::sync::atomic::{AtomicI64,AtomicUsize,Ordering};
    static TRANSPORT_RESULT:AtomicI64=AtomicI64::new(123);
    static RECEIPT:AtomicUsize=AtomicUsize::new(1);
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
            assert_eq!(crate::process_helpers::process_thread_alloc_init_body_result(
                child.cast(), core::mem::size_of::<Thread>() as u64,
                core::mem::offset_of!(Thread, refcount) as u64,
                core::mem::offset_of!(Thread, hash_list) as u64,
                core::mem::offset_of!(Thread, siblings_list) as u64, None), 0);
            assert_eq!((*child).cpu_id, 0);
            (*child).proc = process; (*child).vm = vm;
            (*process).parent = parent_proc; (*process).main_thread = child;
            (*process).vm = vm; (*process).refcount.counter = 2;
            (*vm).proc = process.cast(); (*vm).refcount.counter = 2;
            let address_space = Box::into_raw(Box::new(core::mem::zeroed::<crate::abi::AddressSpace>()));
            (*address_space).page_table = 0x4000usize as *mut core::ffi::c_void;
            (*vm).address_space = address_space;
            (*vm).region.user_start = 0x1000; (*vm).region.user_end = 0x3000;
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


    unsafe fn find_handle_for_request(request:*mut SyscallRequest)->Handle {
        let mut handles=[Handle::EMPTY;registry::CAPACITY];registry::snapshot_handles(&mut handles);
        handles.into_iter().find(|handle| handle.epoch!=0 && registry::visit(*handle,|p|
            i32::from(p.as_ref().request==request as usize))==1).expect("same request in durable registry")
    }
    pub(crate) unsafe fn transport(request: *mut SyscallRequest, cpu: i32) -> i64 {
        if (*request).args[0]==2{return super::control_adapter::transport(request,cpu);}
        assert_eq!((&(*request).args)[..4], [0, 0x1000, 0x2000, 0x4000]);
        let handle = find_handle_for_request(request);
        assert_eq!(registry::visit(handle, |pointer| {
            let c = pointer.as_ref();
            assert_eq!(c.owned_request.as_ref().unwrap().request.as_ptr(), request);
            let credits = c.owned_credits.as_ref().unwrap();
            assert_eq!(credits.reserved_cpu, 1); assert_eq!(credits.private_child_cpu, 0);
            0
        }), 0);
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
        if super::control_adapter::MODE.load(Ordering::SeqCst)==3{
            crate::mem_helpers::fail_next(core::mem::size_of::<SyscallRequest>());
        }
        actual
    }



    unsafe fn execute(objects:&Objects,mode:i32)->CallerForkOutcome {
        super::control_adapter::MODE.store(mode,Ordering::SeqCst);
        let mut out=CallerForkOutcome{disposition:0,error:0,handle:Handle::EMPTY};
        assert_eq!(process_fork_owned_caller_current_v1(objects.parent,objects.child,1,0,&mut out),0);
        assert_eq!(out.disposition,RUST_RETAINS_CREDITS);out
    }
    unsafe fn assert_owned(objects:&Objects,out:&CallerForkOutcome,state:u32,control_slot:bool){
        assert!(matches!(registry::cancel(out.handle),Err(EBUSY)));
        assert_eq!(registry::visit(out.handle,|p|{
            let c=p.as_ref();let credits=c.owned_credits.as_ref().unwrap();
            assert_eq!(credits.child.as_ptr(),objects.child);assert_eq!(credits.vm.as_ptr(),objects.vm);
            assert_eq!(credits.reserved_cpu,1);assert!(c.owned_request.is_some());
            assert_eq!(c.control.state,state);assert_eq!(c.control.owned_request.is_some(),control_slot);
            if let Some(slot)=c.control.owned_request.as_ref(){
                assert_eq!(slot.request.as_ptr()as usize,c.control.request);
                assert_eq!(slot.request.as_ref().args[0],2);
                assert_ne!(slot.request.as_ptr()as usize,c.request);
            }0
        }),0);
        assert_eq!(objects.counts(),[2,2,2,2]);assert_eq!(crate::DESTRUCTORS.load(Ordering::SeqCst),0);
    }
    #[test]
    fn next_control_success_consumed_by_caller_retains_exact_control_storage(){unsafe{
        let objects=Objects::new();let calls=crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        let out=execute(&objects,0);assert_eq!(out.error,EBUSY);
        assert_owned(&objects,&out,super::super::OBSERVED,true);
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst),calls+2);
    }}
    #[test]
    fn next_control_negative_transport_retains_original_and_control_requests(){unsafe{
        let objects=Objects::new();let out=execute(&objects,1);assert_eq!(out.error,-5);
        assert_owned(&objects,&out,super::super::RETAINED,true);
    }}
    #[test]
    fn next_control_missing_receipt_retains_after_function_stack_returns(){unsafe{
        let objects=Objects::new();let out=execute(&objects,2);assert_eq!(out.error,super::super::EIO);
        assert_owned(&objects,&out,super::super::RETAINED,true);
    }}
    #[test]
    fn next_control_allocation_failure_never_publishes_second_request(){unsafe{
        let objects=Objects::new();let calls=crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        let out=execute(&objects,3);assert_eq!(out.error,super::super::ENOMEM);
        assert_owned(&objects,&out,super::super::IDLE,false);
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst),calls+1);
    }}
    #[test]
    fn next_control_mismatched_receipt_fails_closed_with_owned_storage(){unsafe{
        let objects=Objects::new();let out=execute(&objects,4);assert_eq!(out.error,EACCES);
        assert_owned(&objects,&out,super::super::RETAINED,true);
    }}
    #[test]
    fn next_control_repeat_refusal_frees_only_new_private_slot(){unsafe{
        let objects=Objects::new();let out=execute(&objects,0);assert_eq!(out.error,EBUSY);
        let calls=crate::OFFLOAD_CALLS.load(Ordering::SeqCst);let frees=crate::mem_helpers::frees();
        let slots=crate::mem_helpers::live_request_slots();
        let mut observation=super::super::ControlObservation::ZERO;
        assert_eq!(super::super::process_fork_guest_control_submit_current_v1(out.handle,&mut observation),EBUSY);
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst),calls);
        assert_eq!(crate::mem_helpers::frees(),frees+1);assert_eq!(crate::mem_helpers::live_request_slots(),slots);
        assert_owned(&objects,&out,super::super::OBSERVED,true);
    }}
}
