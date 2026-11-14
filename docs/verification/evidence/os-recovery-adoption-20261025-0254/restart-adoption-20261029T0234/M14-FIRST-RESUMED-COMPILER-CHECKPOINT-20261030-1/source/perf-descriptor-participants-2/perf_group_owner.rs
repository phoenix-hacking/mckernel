//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//!
//! PRIVATE UNSELECTED TYPED OWNER-CORE SUCCESSOR. This module is not registered in
//! the production crate. It requires actual descriptor/monitor/host participants
//! to provide the registration and pin contracts documented in RESULT.md.
use core::{ffi::c_void, mem::offset_of, ptr::{addr_of_mut, null_mut}, sync::atomic::{AtomicUsize, Ordering}};
use crate::abi::{AbiListHead, CInt, IhkSpinlock, Mckfd, Process, X86UserContext, CLong};
use super::f03_sync_child_layout_v2::FullMcPerfEvent;

const EINVAL: CInt = 22;
const EOVERFLOW: CInt = 75;
#[derive(Clone, Copy, PartialEq, Eq)]
enum Phase { Private, Active, Retiring }

// Sidecars are Rust-only. C event and descriptor remain at their genuine bases.
// Plain sidecar fields are group-lock protected, except during private creation.
#[repr(C)]
pub(super) struct EventOwner {
    references: AtomicUsize,
    event: *mut FullMcPerfEvent,
    group: *mut GroupOwner,
    descriptors: usize,
    phase: Phase,
    linked: bool,
}
#[repr(C)]
pub(super) struct GroupOwner {
    references: AtomicUsize,
    lock: IhkSpinlock,
    leader: *mut EventOwner, // one group-owned anchor event edge
    leader_closed: bool,
    counter_users: [u32; 64], // includes the retained leader anchor
}

// A pair is deliberately non-Copy and every consuming path returns finalization
// work to its caller. Do not let a live token go out of scope without release.
// #[must_use] is a diagnostic, not a substitute for reviewing every caller.
#[must_use]
pub(super) struct BorrowedPair { event: *mut EventOwner, group: *mut GroupOwner }
#[must_use]
pub(super) struct DescriptorLease { event: *mut EventOwner, group: *mut GroupOwner }
#[must_use]
pub(super) struct ListLease { pub event: *mut EventOwner, pub group: *mut GroupOwner }
#[must_use]
struct DetachedLease { event: *mut EventOwner, group: *mut GroupOwner }
#[derive(Clone, Copy, PartialEq, Eq)]
pub(super) enum EdgeState { Live, ZeroPending, Consumed }
#[must_use]
pub(super) struct Custody {
    pub code: CInt, pub event: *mut EventOwner, pub group: *mut GroupOwner,
    pub event_edge: EdgeState, pub group_edge: EdgeState,
    pub anchor: *mut EventOwner, pub anchor_edge: EdgeState, pub batch: FinalBatch,
}
#[must_use]
pub(super) enum ReleaseOutcome { Final(FinalBatch), Quarantined(Custody) }
#[must_use]
pub(super) struct DetachCustody {
    pub allocation: *mut Registration, pub list: Option<ListLease>, pub partial: Custody,
}
#[must_use]
pub(super) enum DetachOutcome { Final { batch: FinalBatch, allocation: *mut Registration }, Quarantined(DetachCustody) }
#[must_use]
pub(super) enum RollbackOutcome {
    Final(FinalBatch), Rejected { code: CInt, pin: BorrowedPair, member: *mut EventOwner },
    Quarantined { code: CInt, pin: Option<BorrowedPair>, member: *mut EventOwner,
        member_edge: EdgeState, partial: Option<Custody>, batch: FinalBatch },
}
#[must_use]
pub(super) struct PendingStandalone { pin: DescriptorLease }
/// Rejected preserves an unconsumed input. Quarantined means an invariant
/// failed after a mutation; the caller must retain resources and never retry.
#[must_use]
pub(super) enum TransitionFailure<T> { Rejected(CInt, T), Quarantined(Custody) }
#[must_use]
pub(super) enum AcquiredGroup { Root(BorrowedPair), Member { pin: BorrowedPair, leader_closed: bool } }
#[must_use]
pub(super) struct FinalBatch {
    pub events: [*mut EventOwner; 3],
    pub event_count: usize,
    pub group: *mut GroupOwner,
}
impl FinalBatch {
    fn empty() -> Self { Self { events: [null_mut(); 3], event_count: 0, group: null_mut() } }
    unsafe fn push_event(&mut self, owner: *mut EventOwner) -> Result<(), CInt> {
        if self.event_count == self.events.len() { return Err(-EOVERFLOW); }
        self.events[self.event_count] = owner;
        self.event_count += 1;
        Ok(())
    }
    /// On failure returns BOTH owned inputs, unmodified.
    fn merge(mut self, other: Self) -> Result<Self, (Self, Self)> {
        if self.event_count > self.events.len() || other.event_count > other.events.len()
            || self.event_count.checked_add(other.event_count).map_or(true, |n| n > self.events.len())
            || (!self.group.is_null() && !other.group.is_null()) { return Err((self, other)); }
        for i in 0..other.event_count { self.events[self.event_count] = other.events[i]; self.event_count += 1; }
        if self.group.is_null() { self.group = other.group; }
        Ok(self)
    }

}
#[derive(Clone, Copy)]
pub(super) struct ExpectedCallbacks {
    pub read: *mut c_void, pub ioctl: *mut c_void, pub mmap: *mut c_void,
    pub close: *mut c_void, pub fcntl: *mut c_void,
}
// One registered node per descriptor, keyed by descriptor address. Existing
// Rust rbtree provides logarithmic balancing. With distinct usize keys, a valid
// RB tree has at most 2 * usize::BITS levels; the lookup cap is explicit.
// Process mckfd_lock -> registry lock -> group lock is a proposed order only.
#[repr(C)]
pub(super) struct Registration {
    node: crate::rbtree::RbNode,
    descriptor: *mut Mckfd,
    event: *mut EventOwner,
    group: *mut GroupOwner,
    generation: u64,
    active: bool,
}
struct Registry {
    lock: IhkSpinlock,
    root: crate::rbtree::RbRoot,
    next_generation: u64,
}
static mut PERF_REGISTRY: Registry = Registry {
    lock: IhkSpinlock { head_tail: 0 },
    root: crate::rbtree::RbRoot { rb_node: null_mut() },
    next_generation: 1,
};
#[derive(Clone, Copy)]
pub(super) struct RegistrationKey { descriptor: *mut Mckfd, generation: u64 }
#[must_use]
pub(super) struct RemovedRegistration { lease: DetachedLease, list: Option<ListLease>, allocation: *mut Registration }

enum RegistrySearch {
    Found(*mut Registration),
    Vacant { parent: *mut crate::rbtree::RbNode, slot: *mut *mut crate::rbtree::RbNode },
}
unsafe fn registry_search(registry: *mut Registry, desc: *mut Mckfd) -> Result<RegistrySearch, CInt> {
    let key = desc as usize;
    let mut parent: *mut crate::rbtree::RbNode = null_mut();
    let mut slot = addr_of_mut!((*registry).root.rb_node);
    for _ in 0..(2 * usize::BITS as usize) {
        let node = *slot;
        if node.is_null() { return Ok(RegistrySearch::Vacant { parent, slot }); }
        // `node` is the first repr(C) field of a live registry-owned entry.
        let item = node.cast::<Registration>();
        let other = (*item).descriptor as usize;
        if key == other { return Ok(RegistrySearch::Found(item)); }
        parent = node;
        slot = if key < other { addr_of_mut!((*node).rb_left) } else { addr_of_mut!((*node).rb_right) };
    }
    if (*slot).is_null() { Ok(RegistrySearch::Vacant { parent, slot }) } else { Err(-EOVERFLOW) }
}

/// Actual selected tracked allocator, called outside process/registry/group locks.
/// Caller owns this private registration until insertion or matched free.
#[derive(Debug)]
pub(super) enum RegistrationAllocationError { NoMemory, Oversize, Misaligned { raw:*mut c_void } }
pub(super) unsafe fn allocate_registration() -> Result<*mut Registration, RegistrationAllocationError> {
    let size=core::mem::size_of::<Registration>();
    if size > CInt::MAX as usize {return Err(RegistrationAllocationError::Oversize);}
    let raw=super::perf_event_alloc_kmalloc_bridge(size,super::IHK_MC_AP_NOWAIT);
    initialize_registration_allocation(raw)
}
/// This function does not free any rejected pointer: the caller owns it.
unsafe fn initialize_registration_allocation(raw:*mut c_void) -> Result<*mut Registration, RegistrationAllocationError> {
    if raw.is_null() {return Err(RegistrationAllocationError::NoMemory);}
    if (raw as usize)%core::mem::align_of::<Registration>()!=0 {
        return Err(RegistrationAllocationError::Misaligned {raw});
    }
    let p=raw.cast::<Registration>();
    core::ptr::write(p, Registration {
        node: crate::rbtree::RbNode { __rb_parent_color: 0, rb_right: null_mut(), rb_left: null_mut() },
        descriptor: null_mut(), event: null_mut(), group: null_mut(), generation: 0, active: false,
    });
    Ok(p)
}
/// Only for private or already unregistered storage; exact paired tracked
/// allocator/free binding must be selected and independently reviewed.
pub(super) unsafe fn free_registration_after_detach(reg: *mut Registration) -> Result<(), CInt> {
    if reg.is_null() || (*reg).active { return Err(-EINVAL); }
    super::perf_event_alloc_free_bridge(reg.cast());
    Ok(())
}

/// Caller owns process lock, an initialized unpublished matching descriptor,
/// a private allocation, and the descriptor lease produced by commit/publish/
/// dup. Insert before descriptor list publication. Success transfers that pair
/// to the registry; failure returns it to the caller for exact unwind.
pub(super) unsafe fn register_descriptor_locked(desc: *mut Mckfd, reg: *mut Registration,
    pin: DescriptorLease, expected: ExpectedCallbacks) -> Result<RegistrationKey, (CInt, DescriptorLease)> {
    if desc.is_null() || reg.is_null() || pin.event.is_null() || pin.group.is_null()
        || (*reg).active || !(*desc).opt.is_null() || !(*desc).dup_cb.is_null() || expected.read.is_null() || expected.ioctl.is_null()
        || expected.mmap.is_null() || expected.close.is_null() || expected.fcntl.is_null()
        || (*desc).read_cb != expected.read || (*desc).ioctl_cb != expected.ioctl
        || (*desc).mmap_cb != expected.mmap || (*desc).close_cb != expected.close
        || (*desc).fcntl_cb != expected.fcntl
        || (*desc).data as usize as *mut c_void != (*pin.event).event.cast::<c_void>() {
        return Err((-EINVAL, pin));
    }
    let registry = core::ptr::addr_of_mut!(PERF_REGISTRY);
    let lock = addr_of_mut!((*registry).lock).cast::<c_void>();
    let irq = super::syscall_mckfd_lock_bridge(lock);
    let result = registry_search(registry, desc);
    let (parent, slot) = match result {
        Ok(RegistrySearch::Vacant { parent, slot }) => (parent, slot),
        Ok(RegistrySearch::Found(_)) => { super::syscall_mckfd_unlock_bridge(lock, irq); return Err((-EINVAL, pin)); },
        Err(err) => { super::syscall_mckfd_unlock_bridge(lock, irq); return Err((err, pin)); },
    };
    let generation = (*registry).next_generation;
    let Some(next_generation) = generation.checked_add(1) else {
        super::syscall_mckfd_unlock_bridge(lock, irq); return Err((-EOVERFLOW, pin));
    };
    let g_lock = addr_of_mut!((*pin.group).lock).cast::<c_void>();
    let g_irq = super::syscall_mckfd_lock_bridge(g_lock);
    let valid = (*pin.event).group == pin.group && (*pin.event).phase == Phase::Active
        && (*pin.event).descriptors > 0;
    super::syscall_mckfd_unlock_bridge(g_lock, g_irq);
    if !valid { super::syscall_mckfd_unlock_bridge(lock, irq); return Err((-EINVAL, pin)); }
    (*registry).next_generation = next_generation;
    (*reg).descriptor = desc; (*reg).event = pin.event; (*reg).group = pin.group;
    (*reg).generation = generation; (*reg).active = true;
    crate::rbtree::rb_link_node(addr_of_mut!((*reg).node), parent, slot);
    crate::rbtree::rb_insert_color(addr_of_mut!((*reg).node), addr_of_mut!((*registry).root));
    (*desc).opt = reg.cast();
    super::syscall_mckfd_unlock_bridge(lock, irq);
    Ok(RegistrationKey { descriptor: desc, generation })
}

/// Absence is not evidence of a non-perf provider. Invalid includes an
/// inconsistent registered entry or bounded search failure. Process lock held.
#[must_use]
pub(super) enum RegistrationLookup { Absent, Found(RegistrationKey), Invalid(CInt) }
pub(super) unsafe fn registration_lookup_locked(desc: *mut Mckfd) -> RegistrationLookup {
    if desc.is_null() {return RegistrationLookup::Invalid(-EINVAL);}
    let registry=core::ptr::addr_of_mut!(PERF_REGISTRY);
    let lock=addr_of_mut!((*registry).lock).cast::<c_void>();
    let irq=super::syscall_mckfd_lock_bridge(lock);
    let result=match registry_search(registry,desc) {
        Ok(RegistrySearch::Vacant {..})=>RegistrationLookup::Absent,
        Ok(RegistrySearch::Found(reg)) if (*reg).active && (*reg).descriptor==desc
            && (*reg).generation!=0 && !(*reg).event.is_null() && !(*reg).group.is_null()
            && (*desc).opt==reg.cast() => RegistrationLookup::Found(RegistrationKey {descriptor:desc,generation:(*reg).generation}),
        Ok(RegistrySearch::Found(_))=>RegistrationLookup::Invalid(-EINVAL),
        Err(e)=>RegistrationLookup::Invalid(e),
    };
    super::syscall_mckfd_unlock_bridge(lock,irq); result
}

/// Caller holds process lock; registry lock serializes unregister with clone.
/// Descriptor count/list detach is performed under registry -> group before the
/// entry is erased. A failed validation makes no mutations and retains registry.
pub(super) unsafe fn unregister_descriptor_locked(desc: *mut Mckfd, key: RegistrationKey) -> Result<RemovedRegistration, CInt> {
    if desc.is_null() || key.descriptor != desc { return Err(-EINVAL); }
    let registry=core::ptr::addr_of_mut!(PERF_REGISTRY);
    let lock=addr_of_mut!((*registry).lock).cast::<c_void>();
    let irq=super::syscall_mckfd_lock_bridge(lock);
    let result=match registry_search(registry,desc) {
        Ok(RegistrySearch::Found(reg)) if (*reg).active && (*reg).generation==key.generation
            && (*desc).opt==reg.cast() => {
            let event=(*reg).event; let group=(*reg).group;
            match detach_count_under_registry(event,group) {
                Ok(list)=> {
                    crate::rbtree::rb_erase(addr_of_mut!((*reg).node),addr_of_mut!((*registry).root));
                    (*reg).active=false; (*desc).opt=null_mut();
                    Ok(RemovedRegistration { lease:DetachedLease {event,group}, list, allocation:reg })
                }, Err(e)=>Err(e)
            }
        }, _=>Err(-EINVAL),
    };
    super::syscall_mckfd_unlock_bridge(lock,irq); result
}


/// The source process lock is held throughout the generation check and pin.
/// Returns a new descriptor edge to be registered on the child before publication;
/// on clone failure it must be detached exactly once outside all spinlocks.
/// Cross-process lock order and the actual fork path remain unproved.
pub(super) unsafe fn duplicate_registered_locked(desc: *mut Mckfd, key: RegistrationKey)
    -> Result<DescriptorLease, CInt> {
    if desc.is_null() || key.descriptor != desc { return Err(-EINVAL); }
    let registry = core::ptr::addr_of_mut!(PERF_REGISTRY);
    let lock = addr_of_mut!((*registry).lock).cast::<c_void>();
    let irq = super::syscall_mckfd_lock_bridge(lock);
    let result = match registry_search(registry, desc) {
        Ok(RegistrySearch::Found(reg)) if (*reg).active && (*reg).generation == key.generation
            && (*desc).opt == reg.cast() && !(*reg).event.is_null() && !(*reg).group.is_null() => {
            duplicate_registered_pair((*reg).event, (*reg).group)
        },
        _ => Err(-EINVAL),
    };
    super::syscall_mckfd_unlock_bridge(lock, irq);
    result
}


fn bit(index: CInt) -> u64 { if (0..64).contains(&index) { 1u64 << index } else { 0 } }
fn index(index: CInt) -> Option<usize> { if (0..64).contains(&index) { Some(index as usize) } else { None } }
fn try_pin(refs: &AtomicUsize) -> bool {
    refs.fetch_update(Ordering::AcqRel, Ordering::Acquire, |n| {
        if n == 0 { None } else { n.checked_add(1) }
    }).is_ok()
}
fn put(refs: &AtomicUsize) -> Result<bool, CInt> {
    match refs.fetch_update(Ordering::AcqRel, Ordering::Acquire, |n| n.checked_sub(1)) {
        Ok(n) => Ok(n == 1), Err(_) => Err(-EINVAL),
    }
}

/// Caller owns fresh unpublished sidecar and a genuine initialized C event.
/// One reference is the private creator edge. No descriptor exists yet.
pub(super) unsafe fn init_event(owner: *mut EventOwner, event: *mut FullMcPerfEvent) -> Result<(), CInt> {
    if owner.is_null() || event.is_null() { return Err(-EINVAL); }
    core::ptr::write(owner, EventOwner { references: AtomicUsize::new(1), event,
        group: null_mut(), descriptors: 0, phase: Phase::Private, linked: false });
    Ok(())
}

/// Fresh standalone group: transfers the private event edge and new group edge
/// into one PendingStandalone, plus a group-owned leader anchor event edge.
/// Both allocations remain unpublished; caller must commit or abort the token.
pub(super) unsafe fn init_group(group: *mut GroupOwner, leader: *mut EventOwner) -> Result<PendingStandalone, CInt> {
    if group.is_null() || leader.is_null() { return Err(-EINVAL); }
    let event = (*leader).event;
    if event.is_null() || !(*leader).group.is_null() || (*leader).phase != Phase::Private
        || (*leader).descriptors != 0 || (*leader).linked || (*leader).references.load(Ordering::Acquire) != 1 {
        return Err(-EINVAL);
    }
    let head = addr_of_mut!((*event).sibling_list);
    if (*head).next != head || (*head).prev != head { return Err(-EINVAL); }
    if !try_pin(&(*leader).references) { return Err(-EOVERFLOW); }
    let mut users = [0u32; 64];
    if let Some(i) = index((*event).counter_id) { users[i] = 1; }
    core::ptr::write(group, GroupOwner { references: AtomicUsize::new(1),
        lock: IhkSpinlock { head_tail: 0 }, leader, leader_closed: false, counter_users: users });
    (*leader).group = group;
    (*event).group_leader = event;
    (*event).pmc_status = bit((*event).counter_id);
    Ok(PendingStandalone { pin: DescriptorLease { event: leader, group } })
}

/// Under process->group lock order, turn an unpublished standalone token into
/// exactly one descriptor pair. The caller must install registration/descriptor
/// before releasing the process lock; the private registry is not wired to production.
pub(super) unsafe fn commit_standalone_locked(pending: PendingStandalone) -> Result<DescriptorLease, (CInt, PendingStandalone)> {
    let pin = &pending.pin;
    let lock = addr_of_mut!((*pin.group).lock).cast::<c_void>();
    let irq = super::syscall_mckfd_lock_bridge(lock);
    let valid = (*pin.group).leader == pin.event && (*pin.event).group == pin.group
        && (*pin.event).phase == Phase::Private && (*pin.event).descriptors == 0;
    if valid { (*pin.event).phase = Phase::Active; (*pin.event).descriptors = 1; }
    super::syscall_mckfd_unlock_bridge(lock, irq);
    if valid { Ok(pending.pin) } else { Err((-EINVAL, pending)) }
}

/// The raw allocations and every edge state remain in Custody on error.
/// No cleanup or retry follows a quarantined result. The caller holds a live
/// pair; any concurrent actor must obey the group ownership protocol.
unsafe fn release_edges(event: *mut EventOwner, group: *mut GroupOwner, batch: FinalBatch) -> ReleaseOutcome {
    let mut c=Custody {code:-EINVAL,event,group,event_edge:EdgeState::Live,group_edge:EdgeState::Live,
        anchor:null_mut(),anchor_edge:EdgeState::Consumed,batch};
    if event.is_null() || group.is_null() {return ReleaseOutcome::Quarantined(c);}
    let lock=addr_of_mut!((*group).lock).cast::<c_void>(); let irq=super::syscall_mckfd_lock_bridge(lock);
    let en=(*event).references.load(Ordering::Acquire); let gn=(*group).references.load(Ordering::Acquire);
    let leader=(*group).leader; let event_final=en==1; let group_final=gn==1;
    let mut valid=en>0 && gn>0 && (*event).group==group;
    if event_final {valid &= (*event).descriptors==0 && !(*event).linked;}
    let mut anchor_final=false;
    if group_final {
        c.anchor=leader; c.anchor_edge=EdgeState::Live;
        valid &= !leader.is_null();
        if !leader.is_null() {
            let ln=(*leader).references.load(Ordering::Acquire);
            valid &= (*leader).group==group && (*leader).descriptors==0 && !(*leader).linked && ln>0;
            // A group anchor is a separate reference from this pair.
            if leader==event {valid &= en>=2; anchor_final=en==2;} else {anchor_final=ln==1;}
        }
    }
    let required=(event_final as usize)+(anchor_final as usize);
    valid &= c.batch.event_count<=c.batch.events.len()
        && c.batch.event_count.checked_add(required).map_or(false,|n|n<=c.batch.events.len())
        && (!group_final || c.batch.group.is_null());
    if !valid {super::syscall_mckfd_unlock_bridge(lock,irq); return ReleaseOutcome::Quarantined(c);}
    // Every group-associated increment/decrement must hold this lock; after the
    // preflight, these three updates have no fallible operation between them.
    (*event).references.fetch_sub(1,Ordering::AcqRel); c.event_edge=EdgeState::Consumed;
    if event_final {(*event).group=null_mut(); c.batch.events[c.batch.event_count]=event; c.batch.event_count+=1;}
    (*group).references.fetch_sub(1,Ordering::AcqRel); c.group_edge=EdgeState::Consumed;
    if group_final {
        (*leader).group=null_mut(); (*leader).references.fetch_sub(1,Ordering::AcqRel);
        c.anchor_edge=EdgeState::Consumed;
        if anchor_final {c.batch.events[c.batch.event_count]=leader; c.batch.event_count+=1;}
        c.batch.group=group;
    }
    super::syscall_mckfd_unlock_bridge(lock,irq); ReleaseOutcome::Final(c.batch)
}
/// The type system does not accept a descriptor or list lease here.
pub(super) unsafe fn release_pair(pin: BorrowedPair) -> ReleaseOutcome {
    release_edges(pin.event,pin.group,FinalBatch::empty())
}

/// Consume an unpublished standalone group and both creator/anchor edges.
/// Host FD and counter outcomes are not changed or declared resolved.
pub(super) unsafe fn abort_standalone(pending: PendingStandalone) -> Result<FinalBatch, TransitionFailure<PendingStandalone>> {
    let pin = &pending.pin;
    if pin.event.is_null() || pin.group.is_null() { return Err(TransitionFailure::Rejected(-EINVAL, pending)); }
    let lock = addr_of_mut!((*pin.group).lock).cast::<c_void>();
    let irq = super::syscall_mckfd_lock_bridge(lock);
    let private = (*pin.group).leader == pin.event && (*pin.event).group == pin.group
        && (*pin.event).phase == Phase::Private && (*pin.event).descriptors == 0
        && !(*pin.event).linked && (*pin.group).references.load(Ordering::Acquire) == 1
        && (*pin.event).references.load(Ordering::Acquire) == 2;
    if private { (*pin.event).phase = Phase::Retiring; }
    super::syscall_mckfd_unlock_bridge(lock, irq);
    if !private { return Err(TransitionFailure::Rejected(-EINVAL, pending)); }
    match release_edges(pending.pin.event,pending.pin.group,FinalBatch::empty()) {
        ReleaseOutcome::Final(batch)=>Ok(batch),
        ReleaseOutcome::Quarantined(c)=>Err(TransitionFailure::Quarantined(c)),
    }
}

/// Acquire by descriptor while holding process -> registry -> group locks.
/// Only a matching live registry entry provides sidecar provenance; opt and
/// callback equality are cross-checks, never authority. The registry descriptor
/// edge keeps event and group alive while the returned temporary pair is pinned.
/// A member group_fd is reported distinctly; actual compatibility remains open.
pub(super) unsafe fn acquire_group(proc: *mut Process, fd: CInt, expected: ExpectedCallbacks)
    -> Result<(AcquiredGroup, RegistrationKey), CInt> {
    if proc.is_null() || expected.read.is_null() || expected.ioctl.is_null() || expected.mmap.is_null()
        || expected.close.is_null() || expected.fcntl.is_null() { return Err(-EINVAL); }
    let p_lock = addr_of_mut!((*proc).mckfd_lock).cast::<c_void>();
    let p_irq = super::syscall_mckfd_lock_bridge(p_lock);
    let mut cur = (*proc).mckfd.cast::<Mckfd>();
    let mut result = Err(-EINVAL);
    while !cur.is_null() {
        if (*cur).fd == fd {
            if (*cur).read_cb != expected.read || (*cur).ioctl_cb != expected.ioctl
                || (*cur).mmap_cb != expected.mmap || (*cur).close_cb != expected.close
                || (*cur).fcntl_cb != expected.fcntl { break; }
            let registry = core::ptr::addr_of_mut!(PERF_REGISTRY);
            let r_lock = addr_of_mut!((*registry).lock).cast::<c_void>();
            let r_irq = super::syscall_mckfd_lock_bridge(r_lock);
            if let Ok(RegistrySearch::Found(reg)) = registry_search(registry, cur) {
                if (*reg).active && (*reg).descriptor==cur && (*cur).opt==reg.cast()
                    && !(*reg).event.is_null() && !(*reg).group.is_null() {
                    let owner=(*reg).event; let group=(*reg).group;
                    let g_lock=addr_of_mut!((*group).lock).cast::<c_void>();
                    let g_irq=super::syscall_mckfd_lock_bridge(g_lock);
                    let en=(*owner).references.load(Ordering::Acquire); let gn=(*group).references.load(Ordering::Acquire);
                    let valid=(*owner).event.cast::<c_void>()==((*cur).data as usize as *mut c_void)
                        && (*owner).group==group && (*owner).phase==Phase::Active && (*owner).descriptors>0
                        && en>0 && en<usize::MAX && gn>0 && gn<usize::MAX;
                    if valid {
                        (*owner).references.fetch_add(1,Ordering::AcqRel); (*group).references.fetch_add(1,Ordering::AcqRel);
                        let pin=BorrowedPair {event:owner,group};
                        let disposition=if (*group).leader==owner {AcquiredGroup::Root(pin)}
                            else {AcquiredGroup::Member {pin,leader_closed:(*group).leader_closed}};
                        result=Ok((disposition,RegistrationKey {descriptor:cur,generation:(*reg).generation}));
                    }
                    super::syscall_mckfd_unlock_bridge(g_lock,g_irq);
                }
            }
            super::syscall_mckfd_unlock_bridge(r_lock, r_irq);
            break;
        }
        cur = (*cur).next;
    }
    super::syscall_mckfd_unlock_bridge(p_lock, p_irq);
    result
}

/// Under the source descriptor's process lock, add a fork/dup descriptor pair.
/// Count and state are independent of list, callback and monitoring references.
/// The caller must attach the pair to the child and call abort_unpublished_lease on
/// every failed clone path; the current real clone code does neither.
unsafe fn duplicate_registered_pair(event: *mut EventOwner, group: *mut GroupOwner) -> Result<DescriptorLease, CInt> {
    if event.is_null() || group.is_null() {return Err(-EINVAL);}
    let lock=addr_of_mut!((*group).lock).cast::<c_void>(); let irq=super::syscall_mckfd_lock_bridge(lock);
    let en=(*event).references.load(Ordering::Acquire); let gn=(*group).references.load(Ordering::Acquire);
    let next=(*event).descriptors.checked_add(1);
    let valid=(*event).group==group && (*event).phase==Phase::Active && (*event).descriptors>0
        && en>0 && en<usize::MAX && gn>0 && gn<usize::MAX && next.is_some();
    if valid {(*event).references.fetch_add(1,Ordering::AcqRel); (*group).references.fetch_add(1,Ordering::AcqRel);
        (*event).descriptors=next.unwrap();}
    super::syscall_mckfd_unlock_bridge(lock,irq);
    if valid {Ok(DescriptorLease {event,group})} else {Err(-EINVAL)}
}

/// Publish a private member with one descriptor edge and one list edge.
/// Caller holds process lock and an independent live group pin. Source-level
/// registration and actual descriptor publication must occur before unlock.
/// Bounded counter bookkeeping replaces the previous unbounded IRQ-off scan.
pub(super) unsafe fn publish_member_locked(group_pin: &BorrowedPair, member: *mut EventOwner) -> Result<DescriptorLease, CInt> {
    let group = group_pin.group;
    if group.is_null() || member.is_null() || (*member).event.is_null()
        || (*member).phase != Phase::Private || (*member).references.load(Ordering::Acquire) != 1 {
        return Err(-EINVAL);
    }
    let lock = addr_of_mut!((*group).lock).cast::<c_void>();
    let irq = super::syscall_mckfd_lock_bridge(lock);
    let leader_owner = (*group).leader;
    let en=(*member).references.load(Ordering::Acquire); let gn=(*group).references.load(Ordering::Acquire);
    let mut valid = !leader_owner.is_null() && !(*group).leader_closed && (*member).group.is_null()
        && !(*member).linked && (*member).descriptors == 0 && (*member).phase == Phase::Private
        && en==1 && gn>0 && gn<=usize::MAX-2;
    if valid {
        let leader = (*leader_owner).event; let event = (*member).event;
        valid = !leader.is_null();
        if valid {
            let head = addr_of_mut!((*leader).sibling_list); let entry = addr_of_mut!((*event).group_entry);
            let prev = (*head).prev; let next = (*head).next; let count = (*leader).nr_siblings;
            let counter = index((*event).counter_id);
            // Neighbor pointer provenance is an all-participant lock/list invariant.
            valid = !prev.is_null() && !next.is_null() && (*prev).next == head && (*next).prev == head
                && (*entry).next == entry && (*entry).prev == entry && count >= 0 && count < CInt::MAX
                && counter.map_or(true, |i| (*group).counter_users[i] < u32::MAX);
            if valid {
                (*member).references.fetch_add(1,Ordering::AcqRel);
                (*group).references.fetch_add(2,Ordering::AcqRel);
                (*event).group_leader = leader; (*entry).next = head; (*entry).prev = prev;
                (*prev).next = entry; (*head).prev = entry; (*leader).nr_siblings = count + 1;
                if let Some(i) = counter { (*group).counter_users[i] += 1; }
                (*leader).pmc_status |= bit((*event).counter_id);
                (*member).group = group; (*member).linked = true;
                (*member).descriptors = 1; (*member).phase = Phase::Active;
            }
        }
    }
    super::syscall_mckfd_unlock_bridge(lock, irq);
    if valid { Ok(DescriptorLease { event: member, group }) }
    else { Err(-EINVAL) }
}

/// Registry lock is held. All checks precede the count/list mutation.
unsafe fn detach_count_under_registry(event: *mut EventOwner, group: *mut GroupOwner) -> Result<Option<ListLease>,CInt> {
    if event.is_null() || group.is_null() { return Err(-EINVAL); }
    let lock=addr_of_mut!((*group).lock).cast::<c_void>(); let irq=super::syscall_mckfd_lock_bridge(lock);
    if (*event).group!=group || (*event).phase!=Phase::Active || (*event).descriptors==0 {
        super::syscall_mckfd_unlock_bridge(lock,irq); return Err(-EINVAL);
    }
    let last=(*event).descriptors==1; let leader=(*group).leader==event;
    let mut list=None;
    if last && !leader {
        let lo=(*group).leader;
        if lo.is_null() || (*lo).event.is_null() || (*event).event.is_null() || !(*event).linked {
            super::syscall_mckfd_unlock_bridge(lock,irq); return Err(-EINVAL);
        }
        let le=(*lo).event; let ev=(*event).event; let entry=addr_of_mut!((*ev).group_entry);
        let prev=(*entry).prev; let next=(*entry).next; let counter=index((*ev).counter_id);
        if prev.is_null() || next.is_null() || prev==entry || next==entry || (*le).nr_siblings<=0
            || (*prev).next!=entry || (*next).prev!=entry || counter.map_or(false,|i|(*group).counter_users[i]==0) {
            super::syscall_mckfd_unlock_bridge(lock,irq); return Err(-EINVAL);
        }
        (*prev).next=next; (*next).prev=prev; (*entry).next=entry; (*entry).prev=entry;
        (*le).nr_siblings-=1;
        if let Some(i)=counter { (*group).counter_users[i]-=1;
            if (*group).counter_users[i]==0 {(*le).pmc_status &= !bit((*ev).counter_id);} }
        (*event).linked=false; list=Some(ListLease {event,group});
    }
    (*event).descriptors-=1;
    if last { (*event).phase=Phase::Retiring; if leader {(*group).leader_closed=true;} }
    super::syscall_mckfd_unlock_bridge(lock,irq); Ok(list)
}

/// An unregistered clone or prepublication descriptor lease can be unwound.
/// Registry lock serializes its count transition with registered clones/closes.
pub(super) unsafe fn abort_unpublished_lease(lease: DescriptorLease)
    -> Result<RemovedRegistration,(CInt,DescriptorLease)> {
    let registry=core::ptr::addr_of_mut!(PERF_REGISTRY); let lock=addr_of_mut!((*registry).lock).cast::<c_void>();
    let irq=super::syscall_mckfd_lock_bridge(lock);
    let result=detach_count_under_registry(lease.event,lease.group);
    super::syscall_mckfd_unlock_bridge(lock,irq);
    match result { Ok(list)=>Ok(RemovedRegistration {lease:DetachedLease {event:lease.event,group:lease.group},list,allocation:null_mut()}), Err(e)=>Err((e,lease)) }
}

/// Consume detached descriptor and optional list edge outside spinlocks. The
/// returned allocation is the actual registry node (null for unpublished lease).
pub(super) unsafe fn finish_detach(removed: RemovedRegistration) -> DetachOutcome {
    let RemovedRegistration {lease,list,allocation}=removed;
    let first=release_edges(lease.event,lease.group,FinalBatch::empty());
    let batch=match first {
        ReleaseOutcome::Final(b)=>b,
        ReleaseOutcome::Quarantined(partial)=>return DetachOutcome::Quarantined(DetachCustody {allocation,list,partial}),
    };
    match list {
        None=>DetachOutcome::Final {batch,allocation},
        Some(edge)=>match release_edges(edge.event,edge.group,batch) {
            ReleaseOutcome::Final(batch)=>DetachOutcome::Final {batch,allocation},
            ReleaseOutcome::Quarantined(partial)=>DetachOutcome::Quarantined(DetachCustody {allocation,list:None,partial}),
        }
    }
}

/// Consume an operation pair and a private unpublished member; retain both on
/// preflight failure, or an exact partial edge/finalizer record after mutation.
pub(super) unsafe fn rollback_grouped(pin: BorrowedPair, member: *mut EventOwner) -> RollbackOutcome {
    if member.is_null() || !(*member).group.is_null() || (*member).linked
        || (*member).phase!=Phase::Private || (*member).descriptors!=0
        || (*member).references.load(Ordering::Acquire)!=1 {
        return RollbackOutcome::Rejected {code:-EINVAL,pin,member};
    }
    match put(&(*member).references) {
        Err(e)=>return RollbackOutcome::Quarantined {code:e,pin:Some(pin),member,
            member_edge:EdgeState::Live,partial:None,batch:FinalBatch::empty()},
        Ok(false)=>return RollbackOutcome::Quarantined {code:-EINVAL,pin:Some(pin),member,
            member_edge:EdgeState::Consumed,partial:None,batch:FinalBatch::empty()},
        Ok(true)=>{}
    }
    let mut batch=FinalBatch::empty(); batch.events[0]=member; batch.event_count=1;
    match release_edges(pin.event,pin.group,batch) {
        ReleaseOutcome::Final(b)=>RollbackOutcome::Final(b),
        ReleaseOutcome::Quarantined(c)=>RollbackOutcome::Quarantined {code:c.code,pin:None,member,
            member_edge:EdgeState::Consumed,partial:Some(c),batch:FinalBatch::empty()},
    }
}

/// FinalBatch transfers owner/group allocations; exact selected tracked-free and
/// host/counter/monitor release remain explicit caller obligations.
pub(super) unsafe fn final_event_base(owner: *mut EventOwner) -> *mut FullMcPerfEvent { (*owner).event }

// C witness must be compiled and compared in the exact selected ABI profile.
#[no_mangle]
pub(super) static f03_perf_group_owner_rust_layout_v2: [usize; 33] = [
    core::mem::size_of::<Mckfd>(), core::mem::align_of::<Mckfd>(),
    offset_of!(Mckfd, fd), offset_of!(Mckfd, data), offset_of!(Mckfd, opt),
    offset_of!(Mckfd, read_cb), offset_of!(Mckfd, ioctl_cb), offset_of!(Mckfd, mmap_cb),
    offset_of!(Mckfd, close_cb), offset_of!(Mckfd, fcntl_cb),
    core::mem::size_of::<FullMcPerfEvent>(), core::mem::align_of::<FullMcPerfEvent>(),
    offset_of!(FullMcPerfEvent, group_leader), offset_of!(FullMcPerfEvent, sibling_list),
    offset_of!(FullMcPerfEvent, group_entry), offset_of!(FullMcPerfEvent, nr_siblings),
    offset_of!(FullMcPerfEvent, counter_id), offset_of!(FullMcPerfEvent, pmc_status),
    core::mem::size_of::<IhkSpinlock>(), core::mem::align_of::<IhkSpinlock>(),
    core::mem::size_of::<AbiListHead>(), core::mem::align_of::<AbiListHead>(),
    offset_of!(AbiListHead, next), offset_of!(AbiListHead, prev),
    core::mem::size_of::<Process>(), core::mem::align_of::<Process>(),
    offset_of!(Process, mckfd_lock), offset_of!(Process, mckfd),
    offset_of!(Mckfd, next), offset_of!(Mckfd, dup_cb),
    offset_of!(IhkSpinlock, head_tail), core::mem::size_of::<u32>(), core::mem::align_of::<u32>(),
];
// Actual selected Rust symbols are checked against their intended typed ABI;
// C declarations are checked separately by the paired C witness.
const _: unsafe extern "C" fn(*mut Mckfd, *mut X86UserContext) -> CLong = super::f03_perf_read_entries_v1::f03_perf_read_v1;
const _: unsafe extern "C" fn(*mut Mckfd, *mut X86UserContext) -> CInt = super::f03_perf_ioctl_entry_v1::f03_perf_ioctl_v1;
const _: unsafe extern "C" fn(*mut Mckfd, *mut X86UserContext) -> CLong = super::f03_perf_mmap_entry_v1::f03_perf_mmap_v1;
const _: unsafe extern "C" fn(*mut Mckfd, *mut X86UserContext) -> CInt = super::f03_perf_descriptor_entries_v1::f03_perf_close_v1;
const _: unsafe extern "C" fn(*mut Mckfd, *mut X86UserContext) -> CInt = super::f03_perf_descriptor_entries_v1::f03_perf_fcntl_v1;
