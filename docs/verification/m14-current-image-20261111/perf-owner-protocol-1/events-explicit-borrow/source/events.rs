// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private UNWIRED candidate. All owner metadata uses descriptors::Locked (R).
// Measurement count, raw callback equality and numeric FDs are never references.

use core::cell::UnsafeCell;
use core::ffi::c_void;
use core::marker::PhantomData;
use core::mem::{align_of, size_of, ManuallyDrop};
use core::ptr::{addr_of, null_mut, read, write};
use core::sync::atomic::AtomicU32;

use crate::abi::{CInt, CULong, Mckfd, Process};
use crate::spinlock_helpers::{
    __ihk_mc_spinlock_lock, __ihk_mc_spinlock_unlock, IhkSpinlock,
};
use super::descriptors::Locked;
use super::groups::{EventLayout, GroupRef, PreparedMember};
use super::monitors::{DescriptorKey, MonitorSlot};
use super::thread_counters::EventKey;

const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const ORIGIN_UNISSUED: u8 = 0;
const ORIGIN_QUEUED: u8 = 1;
const ORIGIN_DRAINING: u8 = 2;
const ORIGIN_RETIRED: u8 = 3;
const FILE: &[u8] = concat!(file!(), "\0").as_bytes();

pub(super) type FreeEvent = unsafe extern "C" fn(*mut c_void);

/// Both callbacks come from the genuine selected bindings. They intentionally
/// differ: unpublished abort uses perf_event_alloc_free_bridge; publication
/// changes the eventual origin to syscall_mckfd_free_bridge.
#[derive(Clone, Copy)]
pub(super) struct EventOrigins {
    pub(super) abort: FreeEvent,
    pub(super) close: FreeEvent,
}

struct Owner {
    event: *mut c_void,
    generation: u64,
    references: usize,
    // Logical published/pending descriptor ownership is distinct from storage
    // kept by already-admitted DescriptorPins and from Process associations.
    descriptors: usize,
    descriptor_storages: usize,
    monitor_associations: usize,
    origin_state: u8,
    next_origin: *mut Owner,
    published: bool,
    queued: bool,
    next_deferred: *mut Owner,
    // Only an event-to-already-published-event edge. There is NO owning
    // EventOwner -> GroupOwner or EventOwner -> Process edge.
    upstream: *mut Owner,
    origins: EventOrigins,
    layout: EventLayout,
    state_lock: AtomicU32,
}

struct Registry { generation: u64, deferred: *mut Owner, origins: *mut Owner }
struct RegistryCell(UnsafeCell<Registry>);
unsafe impl Sync for RegistryCell {}
static REGISTRY: RegistryCell = RegistryCell(UnsafeCell::new(Registry {
    generation: 1, deferred: null_mut(), origins: null_mut(),
}));

unsafe fn registry(_r: &mut Locked) -> &mut Registry {
    unsafe { &mut *REGISTRY.0.get() }
}

/// The small, owning event edge used by group nodes and leader relationships.
/// It deliberately has no GroupRef, which makes the group/event graph acyclic.
pub(super) struct EventRef { owner: *mut Owner }

unsafe fn retain_locked(owner: *mut Owner, _r: &mut Locked) -> Result<(), CInt> {
    if owner.is_null() || unsafe { (*owner).queued || (*owner).references == 0 } {
        return Err(-EINVAL);
    }
    let next = unsafe { (*owner).references }.checked_add(1).ok_or(-EINVAL)?;
    unsafe { (*owner).references = next };
    Ok(())
}

unsafe fn release_locked(owner: *mut Owner, r: &mut Locked) {
    assert!(!owner.is_null());
    let next = unsafe { (*owner).references }.checked_sub(1)
        .expect("perf event edge released twice");
    unsafe { (*owner).references = next };
    if next != 0 { return; }
    assert!(unsafe { (*owner).descriptors == 0 && (*owner).descriptor_storages == 0
        && (*owner).monitor_associations == 0 && !(*owner).queued
        && (*owner).origin_state != ORIGIN_QUEUED && (*owner).origin_state != ORIGIN_DRAINING });
    let state = unsafe { registry(r) };
    unsafe {
        (*owner).queued = true;
        (*owner).next_deferred = state.deferred;
        state.deferred = owner;
    }
}

/// The last real DescriptorEvent storage has retired. A queued OWNER edge,
/// independent of memory/reference totals, protects this origin notification.
/// Common hardware operations already hold their whole-group Operation leases;
/// any admitted descriptor callback keeps DescriptorEvent storage until done.
unsafe fn queue_origin_locked(owner: *mut Owner, r: &mut Locked) {
    assert!(unsafe { (*owner).descriptor_storages == 0 && (*owner).origin_state == ORIGIN_UNISSUED });
    unsafe { retain_locked(owner, r) }.expect("perf origin notification edge overflow");
    let state = unsafe { registry(r) };
    unsafe {
        (*owner).origin_state = ORIGIN_QUEUED;
        (*owner).next_origin = state.origins;
        state.origins = owner;
    }
}

impl EventRef {
    pub(super) fn raw_event(&self) -> *mut c_void { unsafe { (*self.owner).event } }
    pub(super) fn key(&self) -> EventKey {
        EventKey { address: self.raw_event() as usize, generation: unsafe { (*self.owner).generation } }
    }
    pub(super) fn layout(&self) -> EventLayout { unsafe { (*self.owner).layout } }
    pub(super) fn try_clone(&self) -> Result<Self, CInt> {
        let mut r = unsafe { Locked::take() };
        unsafe { self.try_clone_locked(&mut r) }
    }
    /// R is already held; the caller must not let a returned edge Drop under R.
    pub(super) unsafe fn try_clone_locked(&self, r: &mut Locked) -> Result<Self, CInt> {
        unsafe { retain_locked(self.owner, r)? };
        Ok(Self { owner: self.owner })
    }
    pub(super) unsafe fn release_locked(self, r: &mut Locked) {
        let this = ManuallyDrop::new(self);
        unsafe { release_locked(this.owner, r) };
    }
    pub(super) fn borrow(&self) -> EventBorrow<'_> {
        EventBorrow { owner: self.owner, lifetime: PhantomData }
    }
}
impl Drop for EventRef {
    fn drop(&mut self) {
        let mut r = unsafe { Locked::take() };
        unsafe { release_locked(self.owner, &mut r) };
    }
}

/// An event read that is bounded by a real EventRef or GroupRead. A group node
/// keeps its EventRef even after logical removal, until the GroupOwner dies.
pub(super) struct EventBorrow<'a> { owner: *mut Owner, lifetime: PhantomData<&'a EventRef> }
impl EventBorrow<'_> {
    pub(super) fn raw_event(&self) -> *mut c_void { unsafe { (*self.owner).event } }
    pub(super) fn key(&self) -> EventKey {
        EventKey { address: self.raw_event() as usize, generation: unsafe { (*self.owner).generation } }
    }
    /// Caller holds neither P nor R and performs only bounded non-sleeping
    /// arithmetic/local PMC/MSR operations until this S guard is dropped.
    pub(super) unsafe fn state(&self) -> StateGuard<'_> {
        unsafe { StateGuard::take(self.owner) }
    }
}

/// Independent owning references to BOTH the event's own subgroup and the
/// containing chosen-leader group. A member is a valid later group_fd itself;
/// collapsing these two groups would change that genuine source behavior.
pub(super) struct EventPin {
    event: EventRef,
    own_group: GroupRef,
    containing_group: Option<GroupRef>,
}
impl EventPin {
    /// Consumes the actual event allocation on every path, including error.
    /// Caller must not separately abort/free `raw` after calling this method.
    /// The event is fully initialized but unpublished; call outside P/R/S.
    /// Once Owner storage exists, abort is queued for the mandatory process-
    /// context drain even if GroupOwner preparation fails.
    pub(super) unsafe fn allocate(
        raw: *mut c_void, layout: EventLayout, flags: CULong, origins: EventOrigins,
    ) -> Result<Self, CInt> {
        if raw.is_null() { return Err(-EINVAL); }
        if !layout.valid_for(raw) {
            unsafe { (origins.abort)(raw) };
            return Err(-EINVAL);
        }
        let owner = unsafe { crate::mem_helpers::kmalloc_tracked(
            size_of::<Owner>() as CInt, flags, FILE.as_ptr().cast_mut().cast(), line!() as CInt,
        ) }.cast::<Owner>();
        if owner.is_null() {
            unsafe { (origins.abort)(raw) };
            return Err(-ENOMEM);
        }
        let generation = {
            let mut r = unsafe { Locked::take() };
            let state = unsafe { registry(&mut r) };
            match state.generation.checked_add(1) {
                Some(next) => { let current = state.generation; state.generation = next; Some(current) }
                None => None,
            }
        };
        let Some(generation) = generation else {
            unsafe {
                crate::mem_helpers::kfree_tracked(owner.cast(), FILE.as_ptr().cast_mut().cast(), line!() as CInt);
                (origins.abort)(raw);
            }
            return Err(-EINVAL);
        };
        unsafe { write(owner, Owner {
            event: raw, generation, references: 1, descriptors: 0, descriptor_storages: 0,
            monitor_associations: 0, origin_state: ORIGIN_UNISSUED, next_origin: null_mut(),
            published: false, queued: false, next_deferred: null_mut(), upstream: null_mut(),
            origins, layout, state_lock: AtomicU32::new(0),
        }) };
        let event = EventRef { owner };
        let own_group = match unsafe { GroupRef::allocate(&event, flags) } {
            Ok(group) => group,
            Err(error) => {
                // No publication or counter-map callback has occurred yet.
                // Drop queues the actual abort free for the process-context drain.
                drop(event);
                return Err(error);
            }
        };
        Ok(Self { event, own_group, containing_group: None })
    }

    pub(super) fn raw_event(&self) -> *mut c_void { self.event.raw_event() }
    pub(super) fn key(&self) -> EventKey { self.event.key() }
    pub(super) fn layout(&self) -> EventLayout { self.event.layout() }
    pub(super) fn own_group(&self) -> &GroupRef { &self.own_group }
    pub(super) fn selected_group(&self) -> &GroupRef {
        self.containing_group.as_ref().unwrap_or(&self.own_group)
    }
    pub(super) fn event_ref(&self) -> &EventRef { &self.event }
    pub(super) fn borrow(&self) -> EventBorrow<'_> { self.event.borrow() }
    pub(super) fn try_clone(&self) -> Result<Self, CInt> {
        let mut r = unsafe { Locked::take() };
        unsafe { self.try_clone_locked(&mut r) }
    }
    pub(super) unsafe fn try_clone_locked(&self, r: &mut Locked) -> Result<Self, CInt> {
        let event = unsafe { self.event.try_clone_locked(r)? };
        let own = match unsafe { self.own_group.try_clone_locked(r) } {
            Ok(group) => group,
            Err(error) => { unsafe { event.release_locked(r) }; return Err(error); }
        };
        let containing = match self.containing_group.as_ref() {
            None => None,
            Some(group) => match unsafe { group.try_clone_locked(r) } {
                Ok(group) => Some(group),
                Err(error) => {
                    unsafe { own.release_locked(r); event.release_locked(r) };
                    return Err(error);
                }
            },
        };
        Ok(Self { event, own_group: own, containing_group: containing })
    }
    pub(super) unsafe fn release_locked(self, r: &mut Locked) {
        let this = ManuallyDrop::new(self);
        unsafe {
            if let Some(group) = read(&this.containing_group) { group.release_locked(r); }
            read(&this.own_group).release_locked(r);
            read(&this.event).release_locked(r);
        }
    }

    /// Called only by the prepared-member commit after all checks/reservations.
    /// The new event has an actual pending descriptor edge but is not published.
    /// Only an ALREADY PUBLISHED chosen leader may be selected by group_fd, so
    /// publication order makes upstream links acyclic without imposing an
    /// artificial order on allocation generations of concurrent pending opens.
    pub(super) unsafe fn bind_group_locked(
        &mut self, group: GroupRef, leader: &EventRef, r: &mut Locked,
    ) -> Result<(), (CInt, GroupRef)> {
        if self.containing_group.is_some()
            || unsafe { !(*self.event.owner).upstream.is_null() }
            || unsafe { (*self.event.owner).published || (*self.event.owner).descriptors == 0 }
            || unsafe { !(*leader.owner).published }
            || self.key() == leader.key() {
            return Err((-EINVAL, group));
        }
        if let Err(error) = unsafe { retain_locked(leader.owner, r) } {
            return Err((error, group));
        }
        unsafe { (*self.event.owner).upstream = leader.owner };
        unsafe { self.own_group.mark_nonstandalone_locked(r) };
        self.containing_group = Some(group);
        Ok(())
    }
    pub(super) fn inherit_enabled(&self) -> bool {
        // Actual perf_event_attr.inherit is bit1, mask2, supplied by the
        // genuine-header layout. All attr bytes were initialized at creation.
        let flags = unsafe { self.raw_event().cast::<u8>().add(self.layout().attr_flags)
            .cast::<CULong>().read_volatile() };
        flags & 2 != 0
    }
    /// A real published monitor slot takes this independent logical ownership
    /// BEFORE releasing any displaced association. Event references alone do
    /// not authorize resurrection of an already logically retired event.
    pub(super) unsafe fn acquire_association_locked(&self, _r: &mut Locked) -> Result<(), CInt> {
        let owner = self.event.owner;
        if unsafe { !(*owner).published || ((*owner).descriptors == 0 && (*owner).monitor_associations == 0) } {
            return Err(-EINVAL);
        }
        let next = unsafe { (*owner).monitor_associations }.checked_add(1).ok_or(-EINVAL)?;
        unsafe { (*owner).monitor_associations = next };
        Ok(())
    }
    /// Consumes exactly the association represented by the caller's actual slot.
    /// It neither consumes the slot's EventPin nor releases a Process reference.
    pub(super) unsafe fn release_association_locked(&self, r: &mut Locked) {
        let owner = self.event.owner;
        let next = unsafe { (*owner).monitor_associations }.checked_sub(1)
            .expect("perf monitor association released twice");
        unsafe { (*owner).monitor_associations = next };
        unsafe { self.retire_if_unobserved_locked(r) };
    }
    unsafe fn retire_if_unobserved_locked(&self, r: &mut Locked) {
        if unsafe { (*self.event.owner).descriptors == 0 && (*self.event.owner).monitor_associations == 0 } {
            unsafe { self.selected_group().retire_event_locked(self.key(), r) };
        }
    }
    pub(super) unsafe fn state(&self) -> StateGuard<'_> {
        unsafe { StateGuard::take(self.event.owner) }
    }
}
// No custom EventPin Drop: its owned edges each queue metadata-only retirement.
// They never call the allocator, event free callback or hardware provider.

struct DescriptorState {
    pin: ManuallyDrop<EventPin>,
    closed: bool,
    bound: bool,
    monitor: MonitorSlot,
}
/// Inline and preallocated inside the actual descriptor record. `bind` must be
/// called after moving it to that stable location, before exposing the record.
pub(super) struct DescriptorEvent { state: UnsafeCell<DescriptorState> }
impl DescriptorEvent {
    pub(super) fn from_pin(pin: EventPin) -> Result<Self, CInt> {
        {
            let _r = unsafe { Locked::take() };
            let owner = pin.event.owner;
            // A genuine fork copy has held source descriptor storage throughout
            // admission, so its origin notification cannot already be queued.
            if unsafe { (*owner).origin_state != ORIGIN_UNISSUED } { return Err(-EINVAL); }
            let next = unsafe { (*owner).descriptors }.checked_add(1).ok_or(-EINVAL)?;
            let storage = unsafe { (*owner).descriptor_storages }.checked_add(1).ok_or(-EINVAL)?;
            unsafe { (*owner).descriptors = next; (*owner).descriptor_storages = storage };
        }
        Ok(Self { state: UnsafeCell::new(DescriptorState {
            pin: ManuallyDrop::new(pin), closed: false, bound: false, monitor: MonitorSlot::new(),
        }) })
    }
    pub(super) fn pin(&self) -> Result<EventPin, CInt> {
        let mut r = unsafe { Locked::take() };
        // A DescriptorPin obtained before close may still finish its own
        // operation. The descriptor registry/gate controls new use admission.
        unsafe { (&*self.state.get()).pin.try_clone_locked(&mut r) }
    }
    /// Allocation-free fork snapshot edge, acquired under actual parent P+R
    /// BEFORE a parent close can retire logical membership. Caller preallocates
    /// its snapshot storage outside P/R, performs the real Mckfd80 copy, and
    /// binds this new unbound DescriptorEvent only after moving it to the real
    /// child descriptor record. A mere EventPin is not a pending descriptor.
    pub(super) unsafe fn copy_locked(&self, r: &mut Locked) -> Result<Self, CInt> {
        let source = unsafe { &*self.state.get() };
        let owner = source.pin.event.owner;
        if source.closed || !source.bound || unsafe { !(*owner).published
            || (*owner).origin_state != ORIGIN_UNISSUED || (*owner).descriptors == 0 } {
            return Err(-EINVAL);
        }
        let descriptors = unsafe { (*owner).descriptors }.checked_add(1).ok_or(-EINVAL)?;
        let storages = unsafe { (*owner).descriptor_storages }.checked_add(1).ok_or(-EINVAL)?;
        // All later steps are infallible scalar construction. Failed pin clone
        // balances its own retained edges using the already-held R.
        let pin = unsafe { source.pin.try_clone_locked(r)? };
        unsafe { (*owner).descriptors = descriptors; (*owner).descriptor_storages = storages };
        Ok(Self { state: UnsafeCell::new(DescriptorState {
            pin: ManuallyDrop::new(pin), closed: false, bound: false, monitor: MonitorSlot::new(),
        }) })
    }
    pub(super) unsafe fn bind_descriptor_locked(
        &self, process: *mut Process, descriptor: *mut Mckfd, generation: u64, r: &mut Locked,
    ) -> Result<(), CInt> {
        let state = unsafe { &mut *self.state.get() };
        if state.bound || state.closed { return Err(-EINVAL); }
        unsafe { state.monitor.bind_locked(DescriptorKey {
            process: process as usize, descriptor: descriptor as usize, generation,
        }, r)? };
        state.bound = true;
        Ok(())
    }
    pub(super) unsafe fn published_locked(&self, _r: &mut Locked) -> Result<(), CInt> {
        let state = unsafe { &mut *self.state.get() };
        if !state.bound || state.closed { return Err(-EINVAL); }
        unsafe { (*state.pin.event.owner).published = true };
        Ok(())
    }
    /// Final atomic-publication hook, after allocation of this stable descriptor
    /// record and every host/counter preparation. No operation/monitor EventPin
    /// has escaped yet. A failed commit returns the still-owned prepared node;
    /// callers must drop it only AFTER releasing P/R.
    pub(super) unsafe fn commit_group_locked(
        &self, prepared: PreparedMember, r: &mut Locked,
    ) -> Result<(), (CInt, PreparedMember)> {
        let state = unsafe { &mut *self.state.get() };
        if !state.bound || state.closed || unsafe { (*state.pin.event.owner).published } {
            return Err((-EINVAL, prepared));
        }
        unsafe { prepared.commit_locked(&mut state.pin, r) }
    }
    pub(super) unsafe fn close_locked(&self, r: &mut Locked) -> Result<(), CInt> {
        let state = unsafe { &mut *self.state.get() };
        if state.closed { return Ok(()); }
        unsafe { state.monitor.retire_locked(r) };
        state.closed = true;
        let owner = state.pin.event.owner;
        let next = unsafe { (*owner).descriptors }.checked_sub(1)
            .expect("perf descriptor event edge released twice");
        unsafe { (*owner).descriptors = next };
        unsafe { state.pin.retire_if_unobserved_locked(r) };
        Ok(())
    }
    pub(super) unsafe fn monitor_slot_locked(&self, _r: &mut Locked) -> *mut MonitorSlot {
        unsafe { core::ptr::addr_of_mut!((*self.state.get()).monitor) }
    }
}
impl Drop for DescriptorEvent {
    fn drop(&mut self) {
        let mut r = unsafe { Locked::take() };
        unsafe {
            self.close_locked(&mut r).expect("invalid perf descriptor event retirement");
            let owner = (&(*self.state.get()).pin).event.owner;
            let storage = (*owner).descriptor_storages.checked_sub(1)
                .expect("perf descriptor storage released twice");
            (*owner).descriptor_storages = storage;
            if storage == 0 { queue_origin_locked(owner, &mut r); }
            ManuallyDrop::take(&mut (*self.state.get()).pin).release_locked(&mut r);
        }
    }
}

/// S protects event arithmetic/local hardware only. It is independent of R;
/// callers release S before log/usercopy/offload and never acquire P/R under S.
pub(super) struct StateGuard<'a> {
    owner: *mut Owner, flags: CULong, lifetime: PhantomData<&'a EventRef>,
}
impl StateGuard<'_> {
    unsafe fn take(owner: *mut Owner) -> Self {
        const _: () = {
            assert!(size_of::<AtomicU32>() == size_of::<IhkSpinlock>());
            assert!(align_of::<AtomicU32>() == align_of::<IhkSpinlock>());
        };
        let flags = unsafe { __ihk_mc_spinlock_lock(addr_of!((*owner).state_lock).cast_mut().cast()) };
        Self { owner, flags, lifetime: PhantomData }
    }
    pub(super) fn raw_event(&self) -> *mut c_void { unsafe { (*self.owner).event } }
}
impl Drop for StateGuard<'_> {
    fn drop(&mut self) {
        unsafe { __ihk_mc_spinlock_unlock(addr_of!((*self.owner).state_lock).cast_mut().cast(), self.flags) };
    }
}

/// PROCESS CONTEXT only, outside P/R/S, after the actual descriptor deferred
/// storage drain. This distinct callback consumes ONLY real Origin CounterLease
/// tokens. A surviving Process-owned monitor retains its own bindings and event
/// memory; neither its count nor EventOwner.references delays this notification.
pub(super) unsafe fn drain_origins(retire_origin: unsafe fn(EventKey)) {
    loop {
        let owner = {
            let mut r = unsafe { Locked::take() };
            let state = unsafe { registry(&mut r) };
            let owner = state.origins;
            if !owner.is_null() {
                unsafe {
                    state.origins = (*owner).next_origin;
                    assert!((*owner).origin_state == ORIGIN_QUEUED && (*owner).descriptor_storages == 0);
                    (*owner).origin_state = ORIGIN_DRAINING;
                }
            }
            owner
        };
        if owner.is_null() { return; }
        let key = EventKey { address: unsafe { (*owner).event } as usize,
            generation: unsafe { (*owner).generation } };
        unsafe { retire_origin(key) };
        let mut r = unsafe { Locked::take() };
        assert!(unsafe { (*owner).origin_state == ORIGIN_DRAINING });
        unsafe { (*owner).origin_state = ORIGIN_RETIRED; release_locked(owner, &mut r) };
    }
}

/// Genuine PROCESS-CONTEXT safe point, outside P/R/S, after actual mapping
/// operations have stopped. The supplied real retirement function consumes
/// actual counter-lease tokens; a key alone is not permission to clear a bit.
/// Neither EventPin Drop nor descriptor/VM/IRQ metadata paths call this drain.
pub(super) unsafe fn drain_deferred(
    retire_maps: unsafe fn(EventKey), retire_group_maps: unsafe fn(EventKey, EventKey),
) {
    // Group finalization can queue EventRefs and upstream events. Drain until
    // this finite current queue is empty; each owner is consumed only once.
    loop {
        unsafe {
            super::groups::drain_ready(retire_group_maps);
            super::groups::drain_deferred(retire_group_maps);
        }
        let owner = {
            let mut r = unsafe { Locked::take() };
            let state = unsafe { registry(&mut r) };
            let owner = state.deferred;
            if !owner.is_null() { state.deferred = unsafe { (*owner).next_deferred }; }
            owner
        };
        if owner.is_null() { break; }
        let key = EventKey { address: unsafe { (*owner).event } as usize,
            generation: unsafe { (*owner).generation } };
        unsafe { retire_maps(key) };
        let (event, free, upstream) = unsafe {
            ((*owner).event, if (*owner).published { (*owner).origins.close } else { (*owner).origins.abort },
                (*owner).upstream)
        };
        unsafe {
            free(event);
            crate::mem_helpers::kfree_tracked(owner.cast(), FILE.as_ptr().cast_mut().cast(), line!() as CInt);
        }
        if !upstream.is_null() {
            let mut r = unsafe { Locked::take() };
            unsafe { release_locked(upstream, &mut r) };
        }
    }
}
