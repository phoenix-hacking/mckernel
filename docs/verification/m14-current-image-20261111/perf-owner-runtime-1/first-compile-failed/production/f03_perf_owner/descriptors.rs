// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private unwired managed-perf descriptor implementation. No C layout changes.
use core::cell::UnsafeCell;
use core::ffi::c_void;
use core::marker::PhantomData;
use core::mem::{ManuallyDrop, MaybeUninit, align_of, size_of};
use core::ptr::{addr_of, addr_of_mut, null_mut, write};
use core::sync::atomic::{AtomicBool, AtomicU8, AtomicU32, AtomicUsize, AtomicPtr, Ordering, fence};
use crate::abi::{CInt, CLong, CULong, Mckfd, Process};
use crate::spinlock_helpers::{IhkSpinlock, __ihk_mc_spinlock_lock, __ihk_mc_spinlock_unlock};
use super::events::{DescriptorEvent, EventPin};
use super::groups::PreparedMember;
use super::monitors::MonitorSlot;
use super::forward_gate::{ForwardGate,ForwardGuard};

const EINVAL:CInt=22; const EBADF:CInt=9; const ENOMEM:CInt=12;
const PREPARING:u8=0; const LIVE:u8=1; const CLOSING:u8=2; const RETIRED:u8=3;
pub(super) type FreeDescriptor = unsafe extern "C" fn(*mut c_void);
const FILE:&[u8]=concat!(file!(), "\0").as_bytes();

struct Registry { first:*mut Record, next_generation:u64, unresolved:*mut Record }
#[derive(Clone,Copy)]
pub(super) enum HostState { NoHost, PendingChildRoute, Owned, ClosedAcknowledged, Unknown(CLong), Unissued(HostUnissued) }
#[derive(Clone,Copy)]
pub(super) enum HostUnissued { NoHostFlag, WrongCurrentOwner, GateFailure(CInt), InterruptedOwnerRoute }
struct RegistryCell(UnsafeCell<Registry>);
unsafe impl Sync for RegistryCell {}
static LOCK:AtomicU32=AtomicU32::new(0);
static PENDING:AtomicPtr<Record>=AtomicPtr::new(null_mut());
static REGISTRY:RegistryCell=RegistryCell(UnsafeCell::new(Registry { first:null_mut(), next_generation:1, unresolved:null_mut() }));
const _:()={
    assert!(size_of::<IhkSpinlock>()==size_of::<AtomicU32>());
    assert!(align_of::<IhkSpinlock>()==align_of::<AtomicU32>());
};

/// The real selected four-byte ticket-spinlock storage; never held over an
/// allocator, callback, usercopy, schedule, host call, finalizer or another P.
pub(super) struct Locked { flags:CULong, not_send:PhantomData<*mut ()> }
impl Locked {
    pub(super) unsafe fn take()->Self {
        let flags=unsafe { __ihk_mc_spinlock_lock(addr_of!(LOCK).cast_mut().cast()) };
        Self { flags, not_send:PhantomData }
    }
    unsafe fn state(&mut self)->&mut Registry { unsafe { &mut *REGISTRY.0.get() } }
}
impl Drop for Locked {
    fn drop(&mut self) { unsafe { __ihk_mc_spinlock_unlock(addr_of!(LOCK).cast_mut().cast(),self.flags) }; }
}

struct Record {
    next:*mut Record,
    finalize_next:*mut Record,
    process:*mut Process, descriptor:*mut Mckfd, generation:u64,
    refs:AtomicUsize, state:AtomicU8, list_reference:AtomicBool,
    free_descriptor:Option<FreeDescriptor>,
    event:ManuallyDrop<DescriptorEvent>,
    host:HostState,host_fd:CLong,
    gate:MaybeUninit<ForwardGate>,
}

pub(super) struct Prepared { record:*mut Record }
pub(crate) struct DescriptorPin { record:*mut Record }
/// This is an extra owned descriptor pin, not permission to issue another close.
pub(super) struct CloseToken { pin:DescriptorPin }

unsafe fn retain(record:*mut Record)->Result<(),CInt> {
    let refs=unsafe { &(*record).refs };
    let mut observed=refs.load(Ordering::Relaxed);
    loop {
        if observed==0 { return Err(-EINVAL); }
        let next=observed.checked_add(1).ok_or(-EINVAL)?;
        match refs.compare_exchange_weak(observed,next,Ordering::Relaxed,Ordering::Relaxed) {
            Ok(_)=>return Ok(()), Err(actual)=>observed=actual,
        }
    }
}

unsafe fn find(state:&Registry,process:*mut Process,descriptor:*mut Mckfd)->*mut Record {
    let mut row=state.first;
    while !row.is_null() {
        if unsafe { (*row).process==process && (*row).descriptor==descriptor } { return row; }
        row=unsafe { (*row).next };
    }
    null_mut()
}

/// Queue only metadata. The unique last reference/Prepared owner owns this
/// next link, so push requires no R, allocation, wait or callback even in IRQ.
unsafe fn defer(record:*mut Record) {
    let mut head=PENDING.load(Ordering::Relaxed);
    loop {
        unsafe { (*record).finalize_next=head };
        match PENDING.compare_exchange_weak(head,record,Ordering::Release,Ordering::Relaxed) {
            Ok(_)=>return, Err(actual)=>head=actual,
        }
    }
}

unsafe fn release(record:*mut Record) {
    if unsafe { (*record).refs.fetch_sub(1,Ordering::Release) }!=1 { return; }
    fence(Ordering::Acquire);
    assert!(!unsafe { (*record).list_reference.load(Ordering::Acquire) });
    assert!(unsafe { (*record).state.load(Ordering::Acquire) }==RETIRED);
    unsafe { defer(record) };
}

/// Perform actual destructor/free callbacks only at a genuine process-context
/// safe point, outside P/R/S/IRQ/runqueue exclusion. It consumes one detached
/// finite queue; newly queued work remains owned for the next drain.
pub(super) unsafe fn drain_deferred() {
    let mut row=PENDING.swap(null_mut(),Ordering::AcqRel);
    while !row.is_null() {
        let next=unsafe { (*row).finalize_next };
        let preparing=unsafe { (*row).state.load(Ordering::Acquire) }==PREPARING;
        let free=if preparing { None } else {
            assert!(unsafe { (*row).state.load(Ordering::Acquire) }==RETIRED);
            assert!(!unsafe { (*row).list_reference.load(Ordering::Acquire) });
            assert!(unsafe { (*row).refs.load(Ordering::Acquire) }==0);
            let mut lock=unsafe { Locked::take() };let state=unsafe { lock.state() };
            let mut link=addr_of_mut!(state.first);
            while !unsafe { *link }.is_null() && unsafe { *link }!=row {
                link=unsafe { addr_of_mut!((**link).next) };
            }
            assert!(unsafe { *link }==row);
            unsafe { *link=(*row).next };
            Some(unsafe { (*row).free_descriptor.expect("managed descriptor missing actual free owner") })
        };
        // Drop is metadata-only for DescriptorEvent; it may queue a real event
        // free for the separate outside-lock event drain. Prepared abort does
        // not consume the C descriptor allocation still owned by its transaction.
        unsafe {
            ManuallyDrop::drop(&mut (*row).event);
            if let Some(free)=free { free((*row).descriptor.cast()); }
            // A failed/never-issued host close is not retired by local memory
            // cleanup. Preserve this exact route/fd/outcome record, with no
            // pointer to freed descriptor/event state and NO idle offload.
            if matches!((*row).host,HostState::Owned|HostState::Unknown(_)|HostState::Unissued(_)) {
                (*row).descriptor=null_mut();
                let mut r=Locked::take();let reg=r.state();
                (*row).next=reg.unresolved;reg.unresolved=row;
            } else {
                crate::mem_helpers::kfree_tracked(row.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt);
            }
        }
        row=next;
    }
}

pub(super) fn has_deferred()->bool { !PENDING.load(Ordering::Acquire).is_null() }

impl Drop for DescriptorPin { fn drop(&mut self) { unsafe { release(self.record) }; } }
impl DescriptorPin {
    pub(super) fn descriptor(&self)->*mut Mckfd { unsafe { (*self.record).descriptor } }
    pub(super) unsafe fn live_locked(&self,_r:&mut Locked)->bool { unsafe{(*self.record).state.load(Ordering::Acquire)==LIVE} }
    pub(super) fn generation(&self)->u64 { unsafe { (*self.record).generation } }
    pub(super) fn process(&self)->*mut Process { unsafe { (*self.record).process } }
    pub(super) unsafe fn monitor_slot_locked(&self,r:&mut Locked)->*mut MonitorSlot {
        unsafe { (*self.record).event.monitor_slot_locked(r) }
    }
    pub(super) fn gate(&self)->&ForwardGate { unsafe { (*self.record).gate.assume_init_ref() } }
    pub(crate) unsafe fn forward(&self)->Result<ForwardGuard<'_>,CInt> { unsafe { self.gate().forward() } }
    pub(super) fn event(&self)->Result<EventPin,CInt> { unsafe { (*self.record).event.pin() } }
    pub(super) fn try_clone(&self)->Result<Self,CInt> {
        unsafe { retain(self.record)? }; Ok(Self { record:self.record })
    }
}
impl CloseToken {
    pub(super) fn descriptor(&self)->*mut Mckfd { self.pin.descriptor() }
    pub(super) fn gate(&self)->&ForwardGate { self.pin.gate() }
    pub(super) fn event(&self)->Result<EventPin,CInt> { self.pin.event() }
    pub(super) fn process(&self)->*mut Process { self.pin.process() }
    pub(super) fn host_fd(&self)->CLong { unsafe { (*self.pin.record).host_fd } }
    pub(super) fn host_state(&self)->HostState { let _r=unsafe{Locked::take()};unsafe { (*self.pin.record).host } }
    pub(super) unsafe fn mark_host_unissued(&self,reason:HostUnissued) {
        let _r=unsafe{Locked::take()};unsafe{(*self.pin.record).host=HostState::Unissued(reason);}
    }
    /// Called only after the actual unique close in this same Process fd table.
    pub(super) unsafe fn record_host_result(&self,result:CLong) {
        let _r=unsafe{Locked::take()};
        unsafe{(*self.pin.record).host=if result==0 {HostState::ClosedAcknowledged}else{HostState::Unknown(result)};}
    }
}

impl Prepared {
    /// # Safety
    /// Actual new unpublished descriptor and genuine DescriptorEvent ownership;
    /// allocator flags are the actual C binding. Call without P/R held.
    pub(super) unsafe fn allocate(
        process:*mut Process,descriptor:*mut Mckfd,event:DescriptorEvent,flags:CULong,
    )->Result<Self,CInt> {
        if process.is_null() { return Err(-EINVAL); }
        let row=unsafe { crate::mem_helpers::kmalloc_tracked(size_of::<Record>() as CInt,flags,
            FILE.as_ptr().cast_mut().cast(),line!() as CInt) }.cast::<Record>();
        if row.is_null() { return Err(-ENOMEM); }
        unsafe {
            write(row,Record { next:null_mut(),finalize_next:null_mut(),process,descriptor,generation:0,
                refs:AtomicUsize::new(1),state:AtomicU8::new(PREPARING),list_reference:AtomicBool::new(false),
                free_descriptor:None,event:ManuallyDrop::new(event),host:HostState::NoHost,host_fd:-1,gate:MaybeUninit::uninit() });
            ForwardGate::initialize_at((*row).gate.as_mut_ptr());
        }
        Ok(Self { record:row })
    }

    pub(super) unsafe fn host_opened(&mut self,fd:CLong)->Result<(),CInt> {
        if fd<0 || !matches!(unsafe{(*self.record).host},HostState::NoHost){return Err(-EINVAL);}
        unsafe{(*self.record).host_fd=fd;(*self.record).host=HostState::Owned;}Ok(())
    }
    pub(super) unsafe fn inherited_host_pending(&mut self,fd:CInt)->Result<(),CInt> {
        if fd<0 || !matches!(unsafe{(*self.record).host},HostState::NoHost){return Err(-EINVAL);}
        unsafe{(*self.record).host_fd=fd as CLong;(*self.record).host=HostState::PendingChildRoute;}Ok(())
    }
    pub(super) unsafe fn host_rollback_result(&mut self,result:CLong){
        unsafe{(*self.record).host=if result==0{HostState::ClosedAcknowledged}else{HostState::Unknown(result)};}
    }

    /// Sidecar preparation may precede the host call, but the genuine Mckfd
    /// allocation remains AFTER a successful host fd, preserving error order.
    pub(super) unsafe fn bind_unpublished_descriptor(&mut self,descriptor:*mut Mckfd)->Result<(),CInt> {
        if descriptor.is_null() || !unsafe { (*self.record).descriptor.is_null() }
            || unsafe { (*self.record).state.load(Ordering::Relaxed) }!=PREPARING { return Err(-EINVAL); }
        unsafe { (*self.record).descriptor=descriptor }; Ok(())
    }
    pub(super) fn raw_event(&self)->*mut core::ffi::c_void {
        // Used only outside R before publication. The transaction owns the
        // actual event; obtaining a temporary pin cannot escape its lifetime.
        self.event().expect("prepared descriptor event missing").raw_event()
    }
    pub(super) fn event(&self)->Result<EventPin,CInt> { unsafe { (*self.record).event.pin() } }

    /// Atomic real descriptor/group/map publication, under actual P then R.
    /// `commit_maps` is the transaction's already validated, infallible token
    /// movement, not a callback that allocates or invokes an external provider.
    /// All error paths return ownership so destructors run AFTER P/R unlock.
    pub(super) unsafe fn publish<F:FnOnce(&mut Locked)>(
        mut self,mut member:Option<PreparedMember>,r:&mut Locked,commit_maps:F,
    )->Result<(),(CInt,Self,Option<PreparedMember>)> {
        let row=self.record;
        let state=unsafe { r.state() };
        if unsafe { (*row).descriptor.is_null() }
            || !unsafe { find(state,(*row).process,(*row).descriptor) }.is_null()
            || unsafe { (*row).state.load(Ordering::Relaxed) }!=PREPARING {
            return Err((-EINVAL,self,member));
        }
        let Some(next)=state.next_generation.checked_add(1) else { return Err((-EINVAL,self,member)); };
        let generation=state.next_generation;
        if let Err(error)=unsafe { (*row).event.bind_descriptor_locked((*row).process,(*row).descriptor,generation,r) } {
            return Err((error,self,member));
        }
        if let Some(prepared)=member.take() {
            if let Err((error,prepared))=unsafe { (*row).event.commit_group_locked(prepared,r) } {
                return Err((error,self,Some(prepared)));
            }
        }
        // No fallible external step follows the committed C topology. The real
        // map plan was capacity/generation/state checked in this SAME R window.
        commit_maps(r);
        unsafe { (*row).event.published_locked(r).expect("prevalidated perf publication") };
        let state=unsafe { r.state() };
        unsafe {
            (*row).generation=generation;state.next_generation=next;
            (*row).state.store(LIVE,Ordering::Release);
            (*row).list_reference.store(true,Ordering::Release);
            (*row).next=state.first;state.first=row;
            let descriptor=(*row).descriptor;let process=(*row).process;
            (*descriptor).next=(*process).mckfd.cast();
            (*process).mckfd=descriptor.cast();
        }
        self.record=null_mut();Ok(())
    }

}
impl Drop for Prepared {
    fn drop(&mut self) {
        if self.record.is_null() { return; }
        // Even an abort under a caller's P/error branch queues only metadata.
        // The C descriptor allocation remains with the actual open transaction.
        unsafe {
            assert!((*self.record).state.load(Ordering::Acquire)==PREPARING);
            defer(self.record);
        }
    }
}

/// # Safety
/// Called BEFORE the actual P unlock with the exact found list entry. Return a
/// genuine managed pin, a genuine unregistered/nonperf result, or an error;
/// never silently turn a failed managed pin into an unowned pointer.
pub(crate) unsafe fn pin_managed_locked(
    process:*mut Process,descriptor:*mut Mckfd,
)->Result<Option<DescriptorPin>,CInt> {
    if descriptor.is_null() { return Ok(None); }
    let mut lock=unsafe { Locked::take() };let state=unsafe { lock.state() };
    let row=unsafe { find(state,process,descriptor) };
    if row.is_null() { return Ok(None); }
    if unsafe { (*row).state.load(Ordering::Acquire) }!=LIVE { return Err(-EBADF); }
    unsafe { retain(row)? }; Ok(Some(DescriptorPin { record:row }))
}

/// # Safety
/// Exact actual P lock is held; shared caller unlinks descriptor before unlock.
/// The returned unique token is held until the one real host-close disposition.
pub(super) unsafe fn mark_close_under_p(
    process:*mut Process,descriptor:*mut Mckfd,
)->Result<Option<CloseToken>,CInt> {
    let mut lock=unsafe { Locked::take() };let state=unsafe { lock.state() };
    let row=unsafe { find(state,process,descriptor) };
    if row.is_null() { return Ok(None); }
    if unsafe { (*row).state.load(Ordering::Acquire) }!=LIVE { return Err(-EBADF); }
    unsafe { retain(row)? };
    unsafe { (*row).event.close_locked(&mut lock).expect("managed close metadata");
        (*row).state.store(CLOSING,Ordering::Release); (*row).gate.assume_init_ref().mark_closing() };
    Ok(Some(CloseToken { pin:DescriptorPin { record:row } }))
}

/// VM mark-under-P does not wait on G, drop list ownership or free any node.
/// # Safety
/// The genuine final VM close list traversal holds P and descriptor is its live
/// current entry. A later real drain must unlink and retire it outside P/R.
pub(super) unsafe fn mark_vm_close_under_p(descriptor:*mut Mckfd)->bool {
    let mut r=unsafe { Locked::take() };
    let mut row=unsafe { r.state().first };
    while !row.is_null() && unsafe { (*row).descriptor!=descriptor } { row=unsafe { (*row).next }; }
    if row.is_null() { return false; }
    let state=unsafe { (*row).state.load(Ordering::Acquire) };
    assert!(state==LIVE || state==CLOSING,"VM encountered retired managed descriptor");
    if state==LIVE { unsafe {
        (*row).event.close_locked(&mut r).expect("managed VM close metadata");
        (*row).state.store(CLOSING,Ordering::Release);
        (*row).gate.assume_init_ref().mark_closing();
    } }
    true
}

/// # Safety
/// Actual list unlink/drain has occurred, P/R released, and this is the single
/// callsite's real descriptor free callback. No guessed alternate free owner.
pub(super) unsafe fn retire_unlinked(
    process:*mut Process,descriptor:*mut Mckfd,free:FreeDescriptor,
)->Result<bool,CInt> {
    let row;
    {
        let mut lock=unsafe { Locked::take() };let state=unsafe { lock.state() };
        row=unsafe { find(state,process,descriptor) };
        if row.is_null() { return Ok(false); }
        if unsafe { (*row).state.load(Ordering::Acquire) }!=CLOSING { return Err(-EINVAL); }
        if !unsafe { (*row).list_reference.swap(false,Ordering::AcqRel) } { return Err(-EINVAL); }
        unsafe { (*row).free_descriptor=Some(free); (*row).state.store(RETIRED,Ordering::Release) };
    }
    unsafe { release(row) };
    Ok(true)
}

/// Genuine free bridge has only the actual unlinked descriptor argument. The
/// pointer is compared against registered identities while R is held; no data
/// or callback bytes of an unregistered nonperf node are interpreted as a kind.
pub(super) unsafe fn retire_any_unlinked(descriptor:*mut Mckfd,free:FreeDescriptor)->Result<bool,CInt> {
    let process={
        let mut r=unsafe { Locked::take() };let mut row=unsafe { r.state().first };
        while !row.is_null() && unsafe { (*row).descriptor!=descriptor } { row=unsafe { (*row).next }; }
        if row.is_null() { return Ok(false); }
        if unsafe{(*row).state.load(Ordering::Acquire)}==LIVE {
            // Actual unlinked constructor/VM drain. PendingChildRoute never
            // owned a child host fd; Owned without owner-context ACK remains
            // explicit debt retained by the later metadata-only finalizer.
            unsafe{(*row).event.close_locked(&mut r).expect("managed drain close metadata");(*row).gate.assume_init_ref().mark_closing();(*row).state.store(CLOSING,Ordering::Release);}
        }
        unsafe { (*row).process }
    };
    unsafe { retire_unlinked(process,descriptor,free) }
}

/// Registered lookup for callbacks is protected by their already-held real
/// DescriptorPin. A new caller MUST first resolve under P with pin_managed_locked.
pub(super) unsafe fn pin_callback(descriptor:*mut Mckfd)->Result<DescriptorPin,CInt> {
    let mut r=unsafe { Locked::take() };let mut row=unsafe { r.state().first };
    while !row.is_null() && unsafe { (*row).descriptor!=descriptor } { row=unsafe { (*row).next }; }
    if row.is_null() || !matches!(unsafe { (*row).state.load(Ordering::Acquire) },LIVE|CLOSING) { return Err(-EBADF); }
    unsafe { retain(row)? };Ok(DescriptorPin {record:row})
}

/// The actual successful Linux clone supplies a genuine independent child fd
/// table. This occurs only after positive host PID, before child scheduling.
/// No synthetic close is sent from the parent's still-current Thread.
pub(crate) unsafe fn activate_child_routes(process:*mut Process) {
    let mut r=unsafe{Locked::take()};let mut row=unsafe{r.state().first};
    while !row.is_null(){if unsafe{(*row).process==process} && matches!(unsafe{(*row).host},HostState::PendingChildRoute){unsafe{(*row).host=HostState::Owned;}}row=unsafe{(*row).next};}
}
/// Observable technical ownership debt, not release authority or a retry API.
pub(crate) unsafe fn unresolved_host_closes()->usize {
    let mut r=unsafe{Locked::take()};let mut row=unsafe{r.state().unresolved};let mut n=0usize;
    while !row.is_null(){n=n.checked_add(1).expect("perf host debt count overflow");row=unsafe{(*row).next};}n
}

/// Exact real current-owner terminal take. The caller already holds the real
/// Process terminal transaction gate, outside hash/IRQ/runqueue exclusion.
/// This function owns the genuine P window and returns its unique close pin
/// only AFTER unlink and matching unlock. It never issues a host operation.
pub(super) unsafe fn take_terminal_owned(process:*mut Process)->Result<Option<CloseToken>,CInt>{
    if process.is_null(){return Err(-EINVAL);}
    let p=unsafe{addr_of_mut!((*process).mckfd_lock)}.cast::<c_void>();
    let flags=unsafe{super::super::syscall_mckfd_lock_bridge(p)};
    struct P{lock:*mut c_void,flags:CLong}
    impl Drop for P{fn drop(&mut self){unsafe{super::super::syscall_mckfd_unlock_bridge(self.lock,self.flags)};}}
    let _p=P{lock:p,flags};
    let mut link=unsafe{addr_of_mut!((*process).mckfd)}.cast::<*mut Mckfd>();
    while !unsafe{*link}.is_null(){let descriptor=unsafe{*link};
        let owned={let mut r=unsafe{Locked::take()};let row=unsafe{find(r.state(),process,descriptor)};
            !row.is_null()&&unsafe{(*row).state.load(Ordering::Acquire)==LIVE}&&matches!(unsafe{(*row).host},HostState::Owned)};
        if owned{
            let token=unsafe{mark_close_under_p(process,descriptor)}?.expect("registered terminal identity");
            unsafe{*link=(*descriptor).next;(*descriptor).next=null_mut();}
            return Ok(Some(token));
        }
        link=unsafe{addr_of_mut!((*descriptor).next)};
    }Ok(None)
}

/// No ACK is manufactured for a skipped/invalid terminal route. Preserve an
/// explicit not-issued reason only for actual owned host descriptors; pending
/// child metadata never implied that a child host fd table had existed.
pub(super) unsafe fn mark_owned_host_unresolved(process:*mut Process,reason:HostUnissued){
    let mut r=unsafe{Locked::take()};let mut row=unsafe{r.state().first};
    while !row.is_null(){if unsafe{(*row).process==process}&&matches!(unsafe{(*row).host},HostState::Owned){unsafe{(*row).host=HostState::Unissued(reason);}}row=unsafe{(*row).next};}
}

/// Genuine parent P and shared R are held. This acquires the pending child's
/// logical descriptor/storage ownership BEFORE copying can race parent close.
/// None is genuinely unregistered/nonperf, never a guessed callback kind.
pub(super) unsafe fn copy_snapshot_locked(process:*mut Process,node:*mut Mckfd,r:&mut Locked)->Result<Option<DescriptorEvent>,CInt>{
    let row=unsafe{find(r.state(),process,node)};if row.is_null(){return Ok(None);}
    if unsafe{(*row).state.load(Ordering::Acquire)}!=LIVE{return Err(-EBADF);}
    unsafe{(*row).event.copy_locked(r)}.map(Some)
}

/// Genuine local event/association retirement callback. Its caller owns the
/// actual P removal window or has already unlinked this exact registered node.
/// Numeric host close is a distinct current-owner operation, never this callback.
pub(super) unsafe fn close_callback_mark(node:*mut Mckfd)->Result<(),CInt>{
    let mut r=unsafe{Locked::take()};let mut row=unsafe{r.state().first};
    while !row.is_null()&&unsafe{(*row).descriptor!=node}{row=unsafe{(*row).next};}
    if row.is_null(){return Err(-EINVAL);}
    let state=unsafe{(*row).state.load(Ordering::Acquire)};
    if state==CLOSING{return Ok(());}if state!=LIVE{return Err(-EBADF);}
    unsafe{(*row).event.close_locked(&mut r)?;(*row).gate.assume_init_ref().mark_closing();(*row).state.store(CLOSING,Ordering::Release);}Ok(())
}

// HOST-only observation of this actual registry lock, never guessed storage.
pub(super) fn host_registry_lock_address()->*mut crate::abi::IhkSpinlock {
 core::ptr::addr_of!(LOCK).cast_mut().cast()
}
