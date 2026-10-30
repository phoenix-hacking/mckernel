//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! PRIVATE, UNSELECTED AND UNRUN participant adapters for candidate-3 only.
//! They do not replace sys_perf_event_open, sys_close, fork, teardown or host calls.
use core::{ffi::c_void, mem::{align_of, size_of}, ptr::{addr_of_mut, null_mut}};
use crate::abi::{CInt, CLong, IhkSpinlock, Mckfd, Process};
use super::perf_group_owner as owner;
use super::f03_sync_child_layout_v2::FullMcPerfEvent;

const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const EEXIST: CInt = 17;

/// This intentionally has no drain. It owns records permanently until a separately
/// reviewed finalization/quarantine owner is wired. Do not select for production.
struct Record { next: *mut Record, payload: Payload }
enum Payload {
    Vacant,
    MisalignedRegistration {raw:*mut c_void},
    FreshRejected {event:*mut FullMcPerfEvent, event_owner:*mut owner::EventOwner,
        group:*mut owner::GroupOwner, error:CInt},
    StandaloneRejected {descriptor:*mut Mckfd, registration:*mut owner::Registration,
        pending:owner::PendingStandalone, error:CInt},
    StandaloneAbort {outcome:Result<owner::FinalBatch,owner::TransitionFailure<owner::PendingStandalone>>},
    Close { descriptor: *mut Mckfd, outcome: owner::DetachOutcome },
    CloneInputRejected { descriptor: *mut Mckfd, registration: *mut owner::Registration, error: CInt },
    MemberRejected { descriptor: *mut Mckfd, registration: *mut owner::Registration,
        member: *mut owner::EventOwner, error: CInt },
    CloneAbort { descriptor: *mut Mckfd, registration: *mut owner::Registration,
        outcome: owner::DetachOutcome },
    CloneRejected { descriptor: *mut Mckfd, registration: *mut owner::Registration,
        error: CInt, lease: owner::DescriptorLease },
    PublishRejected { descriptor: *mut Mckfd, registration: *mut owner::Registration,
        error: CInt, lease: owner::DescriptorLease },
    BorrowRelease { outcome: owner::ReleaseOutcome },
}
static mut RETAIN_LOCK: IhkSpinlock = IhkSpinlock { head_tail: 0 };
static mut RETAIN_HEAD: *mut Record = null_mut();

/// Real selected tracked allocator/flags, outside every process/registry/group
/// lock. Matching tracked free is used only for unused private record storage.
unsafe fn new_record() -> Result<*mut Record,CInt> {
    if size_of::<Record>()>CInt::MAX as usize {return Err(-EINVAL);}
    let raw=super::perf_event_alloc_kmalloc_bridge(size_of::<Record>(),super::IHK_MC_AP_NOWAIT);
    if raw.is_null() {return Err(-ENOMEM);}
    if (raw as usize)%align_of::<Record>() != 0 {
        super::perf_event_alloc_free_bridge(raw); return Err(-EINVAL);
    }
    let p=raw.cast::<Record>(); core::ptr::write(p,Record {next:null_mut(),payload:Payload::Vacant}); Ok(p)
}
unsafe fn free_vacant(record:*mut Record) {super::perf_event_alloc_free_bridge(record.cast());}
/// No callback, allocation, host call, or finalizer runs with this lock held.
unsafe fn retain(record:*mut Record,payload:Payload) {
    (*record).payload=payload;
    let lock=core::ptr::addr_of_mut!(RETAIN_LOCK).cast::<c_void>();
    let irq=super::syscall_mckfd_lock_bridge(lock);
    (*record).next=RETAIN_HEAD; RETAIN_HEAD=record;
    super::syscall_mckfd_unlock_bridge(lock,irq);
}
fn callbacks() -> owner::ExpectedCallbacks {
    owner::ExpectedCallbacks {
        read: super::f03_perf_read_entries_v1::f03_perf_read_v1 as *const () as *mut c_void,
        ioctl: super::f03_perf_ioctl_entry_v1::f03_perf_ioctl_v1 as *const () as *mut c_void,
        mmap: super::f03_perf_mmap_entry_v1::f03_perf_mmap_v1 as *const () as *mut c_void,
        close: super::f03_perf_descriptor_entries_v1::f03_perf_close_v1 as *const () as *mut c_void,
        fcntl: super::f03_perf_descriptor_entries_v1::f03_perf_fcntl_v1 as *const () as *mut c_void,
    }
}
unsafe fn lock(proc:*mut Process)->CLong {super::syscall_mckfd_lock_bridge(addr_of_mut!((*proc).mckfd_lock).cast())}
unsafe fn unlock(proc:*mut Process,irq:CLong) {super::syscall_mckfd_unlock_bridge(addr_of_mut!((*proc).mckfd_lock).cast(),irq)}
/// Caller holds this process's descriptor lock and supplies a live list.
unsafe fn fd_exists_locked(proc:*mut Process,fd:CInt)->bool {
    let mut cur=(*proc).mckfd.cast::<Mckfd>();
    while !cur.is_null() {if (*cur).fd==fd {return true;} cur=(*cur).next;}
    false
}

/// A successful group lookup owns its operation pin plus a preallocated record.
/// A member-FD result is preserved distinctly; this adapter does not choose its
/// currently unresolved historical grouping semantics.
#[must_use]
pub(super) struct OpenGroup { proc:*mut Process, acquired: owner::AcquiredGroup, key: owner::RegistrationKey, record:*mut Record }
pub(super) unsafe fn acquire_open_group(proc:*mut Process,fd:CInt)->Result<OpenGroup,CInt> {
    let record=new_record()?;
    match owner::acquire_group(proc,fd,callbacks()) {
        Ok((acquired,key))=>Ok(OpenGroup {proc,acquired,key,record}),
        Err(e)=>{free_vacant(record);Err(e)}
    }
}
/// Member-FD behavior is retained as a distinguishable held disposition.
pub(super) fn group_fd_is_member(group:&OpenGroup)->bool {
    matches!(&group.acquired,owner::AcquiredGroup::Member {..})
}
/// Consume after the open's use of the borrowed pin. Any output with resources,
/// including invariant failure, is retained in a separately allocated global
/// record. The adapter never decides or executes a finalizer.
pub(super) unsafe fn release_open_group(group:OpenGroup) {
    let OpenGroup {acquired,record,..}=group;
    let pin=match acquired {owner::AcquiredGroup::Root(p)=>p,owner::AcquiredGroup::Member{pin,..}=>pin};
    let outcome=owner::release_pair(pin);
    match outcome {
        owner::ReleaseOutcome::Final(batch) if batch.event_count==0 && batch.group.is_null()=>free_vacant(record),
        other=>retain(record,Payload::BorrowRelease {outcome:other}),
    }
}

/// Caller owns initialized fresh descriptor, fresh registration and a descriptor
/// lease from standalone commit or member publication. Host outcome, fresh event
/// and counter ownership are still the caller's obligations. Register and list
/// publication occur under the same process lock. On failure every input is
/// retained in the preallocated owner record, never implicitly finalized.
unsafe fn publish_descriptor(proc:*mut Process,desc:*mut Mckfd,
    reg:*mut owner::Registration,lease:owner::DescriptorLease,record:*mut Record)->Result<CInt,CInt> {
    if proc.is_null() || desc.is_null() || reg.is_null() {
        retain(record,Payload::PublishRejected {descriptor:desc,registration:reg,error:-EINVAL,lease});
        return Err(-EINVAL);
    }
    let irq=lock(proc);
    if fd_exists_locked(proc,(*desc).fd) {unlock(proc,irq);
        retain(record,Payload::PublishRejected {descriptor:desc,registration:reg,error:-EEXIST,lease});return Err(-EEXIST);}
    let outcome=owner::register_descriptor_locked(desc,reg,lease,callbacks());
    match outcome {
        Ok(_key)=>{(*desc).next=(*proc).mckfd.cast(); (*proc).mckfd=desc.cast();
            let fd=(*desc).fd; unlock(proc,irq); free_vacant(record); Ok(fd)},
        Err((error,lease))=>{unlock(proc,irq); retain(record,Payload::PublishRejected {
            descriptor:desc,registration:reg,error,lease}); Err(error)}
    }
}

/// Reservation must be made before creating a descriptor lease. Keeping the
/// type private avoids exporting a new C ABI or passing a fabricated pointer.
#[must_use] pub(super) struct RecordReservation {record:*mut Record}
pub(super) unsafe fn reserve_record()->Result<RecordReservation,CInt> {Ok(RecordReservation{record:new_record()?})}
/// Only for a reservation before any owned input was transferred into it.
pub(super) unsafe fn cancel_unused_reservation(reservation:RecordReservation) {free_vacant(reservation.record)}
/// A misaligned tracked allocation is never dereferenced or discarded: retain
/// its exact raw pointer for the separately reviewed allocator/custody owner.
pub(super) unsafe fn allocate_registration_reserved(reservation:RecordReservation)->Result<*mut owner::Registration,CInt> {
    finish_registration_allocation(reservation.record,owner::allocate_registration())
}
unsafe fn finish_registration_allocation(record:*mut Record,
    result:Result<*mut owner::Registration,owner::RegistrationAllocationError>)->Result<*mut owner::Registration,CInt> {
    match result {
        Ok(reg)=>{free_vacant(record);Ok(reg)},
        Err(owner::RegistrationAllocationError::NoMemory)=>{free_vacant(record);Err(-ENOMEM)},
        Err(owner::RegistrationAllocationError::Oversize)=>{free_vacant(record);Err(-EINVAL)},
        Err(owner::RegistrationAllocationError::Misaligned {raw})=>{retain(record,Payload::MisalignedRegistration {raw});Err(-EINVAL)},
    }
}
pub(super) unsafe fn publish_reserved(proc:*mut Process,desc:*mut Mckfd,reg:*mut owner::Registration,
    lease:owner::DescriptorLease,reservation:RecordReservation)->Result<CInt,CInt> {
    publish_descriptor(proc,desc,reg,lease,reservation.record)
}

/// Allocate sidecars from the same selected nonzeroing tracked provider as
/// the retained perf entry. Caller supplies the real freshly allocated event;
/// error transfers that event and any sidecars to a retained record.
unsafe fn allocate_sidecar<T>()->Result<*mut T,CInt> {
    if size_of::<T>()>CInt::MAX as usize {return Err(-EINVAL);}
    let raw=super::perf_event_alloc_kmalloc_bridge(size_of::<T>(),super::IHK_MC_AP_NOWAIT);
    if raw.is_null() {return Err(-ENOMEM);}
    if (raw as usize)%align_of::<T>()!=0 {super::perf_event_alloc_free_bridge(raw);return Err(-EINVAL);}
    Ok(raw.cast())
}
#[must_use] pub(super) struct PreparedStandalone {pending:owner::PendingStandalone,record:*mut Record}
pub(super) unsafe fn prepare_standalone(event:*mut FullMcPerfEvent,reservation:RecordReservation)
    ->Result<PreparedStandalone,CInt> {
    let record=reservation.record;
    if event.is_null() {retain(record,Payload::FreshRejected {event,event_owner:null_mut(),group:null_mut(),error:-EINVAL});return Err(-EINVAL);}
    let event_owner=match allocate_sidecar::<owner::EventOwner>() {Ok(p)=>p,Err(e)=>{
        retain(record,Payload::FreshRejected {event,event_owner:null_mut(),group:null_mut(),error:e});return Err(e);}};
    if let Err(e)=owner::init_event(event_owner,event) {retain(record,Payload::FreshRejected {
        event,event_owner,group:null_mut(),error:e});return Err(e);}
    let group=match allocate_sidecar::<owner::GroupOwner>() {Ok(p)=>p,Err(e)=>{
        retain(record,Payload::FreshRejected {event,event_owner,group:null_mut(),error:e});return Err(e);}};
    match owner::init_group(group,event_owner) {
        Ok(pending)=>Ok(PreparedStandalone {pending,record}),
        Err(e)=>{retain(record,Payload::FreshRejected {event,event_owner,group,error:e});Err(e)}
    }
}
/// Abort a prepared, unpublished standalone after a failed or unissued host
/// step. Record owns the finalizers or the rejected/quarantined pending token;
/// host FD/counter disposition is a separate unresolved obligation.
pub(super) unsafe fn abort_prepared(prepared:PreparedStandalone) {
    let PreparedStandalone {pending,record}=prepared;
    let outcome=owner::abort_standalone(pending); retain(record,Payload::StandaloneAbort {outcome});
}
/// Private prepared token and descriptor are registered under the same lock.
/// Exact host/counter outcome remains owned by the wider, not-yet-wired entry.
pub(super) unsafe fn commit_standalone_and_publish(proc:*mut Process,desc:*mut Mckfd,
    reg:*mut owner::Registration,prepared:PreparedStandalone)->Result<CInt,CInt> {
    let PreparedStandalone {pending,record}=prepared;
    if proc.is_null() || desc.is_null() || reg.is_null() {
        retain(record,Payload::StandaloneRejected {descriptor:desc,registration:reg,pending,error:-EINVAL});return Err(-EINVAL);
    }
    let irq=lock(proc);
    if fd_exists_locked(proc,(*desc).fd) {unlock(proc,irq);
        retain(record,Payload::StandaloneRejected {descriptor:desc,registration:reg,pending,error:-EEXIST});return Err(-EEXIST);}
    let lease=match owner::commit_standalone_locked(pending) {Ok(l)=>l,Err((e,pending))=>{
        unlock(proc,irq);retain(record,Payload::StandaloneRejected {descriptor:desc,registration:reg,pending,error:e});return Err(e);}};
    match owner::register_descriptor_locked(desc,reg,lease,callbacks()) {
        Ok(_)=>{(*desc).next=(*proc).mckfd.cast();(*proc).mckfd=desc.cast();let fd=(*desc).fd;
            unlock(proc,irq);free_vacant(record);Ok(fd)},
        Err((e,lease))=>{let rolled=owner::abort_unpublished_lease(lease);unlock(proc,irq);
            match rolled {Ok(removed)=>{let outcome=owner::finish_detach(removed);
                retain(record,Payload::CloneAbort {descriptor:desc,registration:reg,outcome});},
                Err((error,lease))=>retain(record,Payload::CloneRejected {descriptor:desc,registration:reg,error,lease})}
            Err(e)}
    }
}

/// Holds process lock continuously across the member link and registered
/// descriptor publication. Member-FD interpretation is intentionally held; its
/// fresh inputs are retained without attempting canonical-leader substitution.
pub(super) unsafe fn publish_member_reserved(proc:*mut Process,group:&OpenGroup,
    member:*mut owner::EventOwner,desc:*mut Mckfd,reg:*mut owner::Registration,
    reservation:RecordReservation)->Result<CInt,CInt> {
    let record=reservation.record;
    if proc.is_null() || proc!=group.proc || member.is_null() || desc.is_null() || reg.is_null() {
        retain(record,Payload::MemberRejected {descriptor:desc,registration:reg,member,error:-EINVAL}); return Err(-EINVAL);
    }
    let pin=match &group.acquired {owner::AcquiredGroup::Root(pin)=>pin,
        owner::AcquiredGroup::Member {..}=>{retain(record,Payload::MemberRejected {
            descriptor:desc,registration:reg,member,error:-EINVAL}); return Err(-EINVAL);}};
    let irq=lock(proc);
    if fd_exists_locked(proc,(*desc).fd) {unlock(proc,irq);
        retain(record,Payload::MemberRejected {descriptor:desc,registration:reg,member,error:-EEXIST});return Err(-EEXIST);}
    let lease=match owner::publish_member_locked(pin,member) {Ok(p)=>p,Err(e)=>{
        unlock(proc,irq); retain(record,Payload::MemberRejected {descriptor:desc,registration:reg,member,error:e}); return Err(e);}};
    match owner::register_descriptor_locked(desc,reg,lease,callbacks()) {
        Ok(_)=>{(*desc).next=(*proc).mckfd.cast(); (*proc).mckfd=desc.cast();
            let fd=(*desc).fd; unlock(proc,irq); free_vacant(record); Ok(fd)},
        Err((e,lease))=>{
            let rolled=owner::abort_unpublished_lease(lease); unlock(proc,irq);
            match rolled {
                Ok(removed)=>{let outcome=owner::finish_detach(removed);
                    retain(record,Payload::CloneAbort {descriptor:desc,registration:reg,outcome});},
                Err((error,lease))=>retain(record,Payload::CloneRejected {descriptor:desc,registration:reg,error,lease}),
            }
            Err(e)
        }
    }
}

/// Source descriptor belongs to parent list. Dest descriptor and registration
/// are fresh private tracked allocations acquired before entry. Parent and child
/// process locks are held sequentially, never across allocator/callback calls.
/// Parent lock binds source snapshot and generation; acquired descriptor lease
/// preserves event/group after unlock. Child publication is one locked transition.
pub(super) unsafe fn clone_registered(parent:*mut Process,child:*mut Process,src:*mut Mckfd,
    dst:*mut Mckfd,reg:*mut owner::Registration,reservation:RecordReservation)->Result<(),CInt> {
    let record=reservation.record;
    if parent.is_null() || child.is_null() || src.is_null() || dst.is_null() || reg.is_null() || src==dst {
        // Caller still owns dst/reg; no lease was acquired. Return them through
        // an explicit untouched-input record instead of freeing under uncertainty.
        retain(record,Payload::CloneInputRejected {descriptor:dst,registration:reg,error:-EINVAL}); return Err(-EINVAL);
    }
    let irq=lock(parent); let mut cur=(*parent).mckfd.cast::<Mckfd>();
    while !cur.is_null() && cur!=src {cur=(*cur).next;}
    if cur.is_null() || !(*src).dup_cb.is_null() {
        unlock(parent,irq); retain(record,Payload::CloneInputRejected {descriptor:dst,registration:reg,error:-EINVAL}); return Err(-EINVAL);
    }
    let key=match owner::registration_lookup_locked(src) {owner::RegistrationLookup::Found(k)=>k,
        owner::RegistrationLookup::Absent=>{unlock(parent,irq);retain(record,Payload::CloneInputRejected {descriptor:dst,registration:reg,error:-EINVAL});return Err(-EINVAL);},
        owner::RegistrationLookup::Invalid(e)=>{unlock(parent,irq);retain(record,Payload::CloneInputRejected {descriptor:dst,registration:reg,error:e});return Err(e);}};
    let lease=match owner::duplicate_registered_locked(src,key) {Ok(p)=>p,Err(e)=>{unlock(parent,irq);
        retain(record,Payload::CloneInputRejected {descriptor:dst,registration:reg,error:e});return Err(e);}};
    core::ptr::copy_nonoverlapping(src,dst,1); (*dst).opt=null_mut(); (*dst).next=null_mut();
    unlock(parent,irq);
    let child_irq=lock(child);
    if fd_exists_locked(child,(*dst).fd) {
        let rolled=owner::abort_unpublished_lease(lease); unlock(child,child_irq);
        match rolled {
            Ok(removed)=>{let outcome=owner::finish_detach(removed);retain(record,Payload::CloneAbort {descriptor:dst,registration:reg,outcome});},
            Err((error,lease))=>retain(record,Payload::CloneRejected {descriptor:dst,registration:reg,error,lease}),
        }
        return Err(-EEXIST);
    }
    match owner::register_descriptor_locked(dst,reg,lease,callbacks()) {
        Ok(_)=>{(*dst).next=(*child).mckfd.cast(); (*child).mckfd=dst.cast();
            unlock(child,child_irq); free_vacant(record); Ok(())},
        Err((e,lease))=>{unlock(child,child_irq);
            match owner::abort_unpublished_lease(lease) {
                Ok(removed)=>{let outcome=owner::finish_detach(removed);
                    retain(record,Payload::CloneAbort {descriptor:dst,registration:reg,outcome});},
                Err((error,lease))=>retain(record,Payload::CloneRejected {descriptor:dst,registration:reg,error,lease}),
            }
            Err(e)
        }
    }
}

/// The unregistered variants are NOT permission for a legacy callback/free.
/// A separate type/provenance owner must positively classify the descriptor.
#[derive(Debug,PartialEq,Eq)]
pub(super) enum CloseDisposition { NoDescriptor, MissingPerfRegistration, NeedsNonperfProof, Detached }
/// A fingerprint is solely a reason to stop, not proof of provider identity.
unsafe fn perf_fingerprint(desc:*mut Mckfd)->bool {
    let c=callbacks(); (*desc).read_cb==c.read || (*desc).ioctl_cb==c.ioctl || (*desc).mmap_cb==c.mmap
        || (*desc).close_cb==c.close || (*desc).fcntl_cb==c.fcntl
}
/// No legacy handling, callback, host forward, free, or syscall result here.
pub(super) unsafe fn detach_for_close(proc:*mut Process,fd:CInt,reservation:RecordReservation)->Result<CloseDisposition,CInt> {
    let record=reservation.record;
    if proc.is_null() {free_vacant(record);return Err(-EINVAL);}
    let irq=lock(proc); let mut prev:*mut Mckfd=null_mut(); let mut cur=(*proc).mckfd.cast::<Mckfd>();
    while !cur.is_null() && (*cur).fd!=fd {prev=cur;cur=(*cur).next;}
    if cur.is_null() {unlock(proc,irq);free_vacant(record);return Ok(CloseDisposition::NoDescriptor);}
    let key=match owner::registration_lookup_locked(cur) {
        owner::RegistrationLookup::Found(k)=>k,
        owner::RegistrationLookup::Absent=>{let disposition=if perf_fingerprint(cur) {CloseDisposition::MissingPerfRegistration}
            else {CloseDisposition::NeedsNonperfProof};unlock(proc,irq);free_vacant(record);return Ok(disposition);},
        owner::RegistrationLookup::Invalid(e)=>{unlock(proc,irq);free_vacant(record);return Err(e);},
    };
    let removed=match owner::unregister_descriptor_locked(cur,key) {Ok(r)=>r,Err(e)=>{unlock(proc,irq);free_vacant(record);return Err(e);}};
    if prev.is_null() {(*proc).mckfd=(*cur).next.cast();} else {(*prev).next=(*cur).next;}
    (*cur).next=null_mut(); unlock(proc,irq);
    let outcome=owner::finish_detach(removed);
    retain(record,Payload::Close {descriptor:cur,outcome}); Ok(CloseDisposition::Detached)
}
