// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private UNWIRED candidate: exact allocation-free sequence/epoch/tail protocol.
// All topology/epoch fields and C list mirrors are protected by the SAME R.

use core::cell::UnsafeCell;
use core::ffi::c_void;
use core::marker::PhantomData;
use core::mem::{align_of, size_of, ManuallyDrop};
use core::ptr::{addr_of_mut, null_mut, write};
use crate::abi::{AbiListHead, CInt, CULong};
use super::descriptors::Locked;
use super::events::{EventBorrow, EventPin, EventRef};
use super::thread_counters::EventKey;

const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const FILE: &[u8] = concat!(file!(), "\0").as_bytes();

/// Immutable genuine-header metadata supplied by the selected C/Rust ABI join.
/// No field offset or whole mc_perf_event layout is guessed here. attr_flags is
/// C offsetof(mc_perf_event,attr) plus the existing genuine-header-qualified
/// Rust PerfEventAttr::flags offset. C's bitfield has NO named flags word on
/// which an offsetof could legitimately be requested.
#[derive(Clone, Copy, PartialEq, Eq)]
pub(super) struct EventLayout {
    pub(super) size: usize,
    pub(super) align: usize,
    pub(super) group_leader: usize,
    pub(super) sibling_list: usize,
    pub(super) group_entry: usize,
    pub(super) nr_siblings: usize,
    pub(super) pmc_status: usize,
    pub(super) counter_id: usize,
    pub(super) attr_flags: usize,
}
impl EventLayout {
    fn field<T>(&self, offset: usize) -> bool {
        offset % align_of::<T>() == 0
            && offset.checked_add(size_of::<T>()).map_or(false, |end| end <= self.size)
    }
    pub(super) fn valid_for(&self, raw: *mut c_void) -> bool {
        !raw.is_null() && self.align.is_power_of_two()
            && self.align >= align_of::<AbiListHead>()
            && raw as usize % self.align == 0
            && self.size != 0
            && self.field::<*mut c_void>(self.group_leader)
            && self.field::<AbiListHead>(self.sibling_list)
            && self.field::<AbiListHead>(self.group_entry)
            && self.field::<CInt>(self.nr_siblings)
            && self.field::<CULong>(self.pmc_status)
            && self.field::<CInt>(self.counter_id)
            && self.field::<CULong>(self.attr_flags)
    }
    unsafe fn at<T>(&self, event: *mut c_void, offset: usize) -> *mut T {
        unsafe { event.cast::<u8>().add(offset).cast() }
    }
}

struct Epoch { readers: usize, next: *mut Epoch }
impl Epoch { const fn new() -> Self { Self { readers: 0, next: null_mut() } } }

struct Member {
    next: *mut Member,
    event: ManuallyDrop<EventRef>,
    born: u64,
    dead: u64,
    // Each append prepares its own future close epoch. Closing never allocates.
    next_epoch: Epoch,
    last_old_epoch: *mut Epoch,
    mapping_retired: bool,
    mapping_claimed: bool,
}

struct Owner {
    references: usize,
    queued: bool,
    next_deferred: *mut Owner,
    next_registered: *mut Owner,
    leader: ManuallyDrop<EventRef>,
    layout: EventLayout,
    first: *mut Member,
    tail: *mut Member,
    live_members: usize,
    sequence: u64,
    // Each successful append reserves the sequence increment for its future
    // close. Thus close/exit cannot encounter a new sequence-overflow failure.
    reserved_closes: u64,
    first_epoch: Epoch,
    current_epoch: *mut Epoch,
}
struct Deferred(UnsafeCell<*mut Owner>);
unsafe impl Sync for Deferred {}
static DEFERRED: Deferred = Deferred(UnsafeCell::new(null_mut()));
static REGISTERED: Deferred = Deferred(UnsafeCell::new(null_mut()));

/// No EventOwner owns this type. External descriptor/monitor/pending/read owners
/// keep the group alive, and group nodes own only EventRef (never EventPin).
pub(super) struct GroupRef { owner: *mut Owner }

unsafe fn release_owner_locked(owner: *mut Owner, _r: &mut Locked) {
    let next = unsafe { (*owner).references }.checked_sub(1)
        .expect("perf group edge released twice");
    unsafe { (*owner).references = next };
    if next != 0 { return; }
    assert!(!unsafe { (*owner).queued });
    unsafe {
        (*owner).queued = true;
        (*owner).next_deferred = *DEFERRED.0.get();
        *DEFERRED.0.get() = owner;
    }
}

impl GroupRef {
    /// Fallible process-context preparation, before any publication or R/P.
    pub(super) unsafe fn allocate(leader: &EventRef, flags: CULong) -> Result<Self, CInt> {
        let storage = unsafe { crate::mem_helpers::kmalloc_tracked(size_of::<Owner>() as CInt,
            flags, FILE.as_ptr().cast_mut().cast(), line!() as CInt) }.cast::<Owner>();
        if storage.is_null() { return Err(-ENOMEM); }
        let leader_copy = match leader.try_clone() {
            Ok(event) => event,
            Err(error) => {
                unsafe { crate::mem_helpers::kfree_tracked(storage.cast(), FILE.as_ptr().cast_mut().cast(), line!() as CInt) };
                return Err(error);
            }
        };
        unsafe { write(storage, Owner { references: 1, queued: false, next_deferred: null_mut(), next_registered: null_mut(),
            leader: ManuallyDrop::new(leader_copy), layout: leader.layout(),
            first: null_mut(), tail: null_mut(), live_members: 0, sequence: 1, reserved_closes: 0,
            first_epoch: Epoch::new(), current_epoch: null_mut(),
        }) };
        unsafe { (*storage).current_epoch = addr_of_mut!((*storage).first_epoch) };
        // Actual event construction initialized all fields. The caller's
        // selected owner now initializes these original empty list mirrors.
        let layout = leader.layout();
        let raw = leader.raw_event();
        unsafe {
            let head = layout.at::<AbiListHead>(raw, layout.sibling_list);
            (*head).next = head; (*head).prev = head;
            let entry = layout.at::<AbiListHead>(raw, layout.group_entry);
            (*entry).next = entry; (*entry).prev = entry;
            layout.at::<*mut c_void>(raw, layout.group_leader).write(raw);
            layout.at::<CInt>(raw, layout.nr_siblings).write(0);
            let index = layout.at::<CInt>(raw, layout.counter_id).read();
            // Initialization, not an executing-Thread hardware mask. Hardware
            // code composes masks from actual mapped indices owned by P03.
            let own_bit = if index >= 0 && index < CULong::BITS as CInt { (1 as CULong) << index } else { 0 };
            layout.at::<CULong>(raw, layout.pmc_status).write(own_bit);
        }
        {
            let _r = unsafe { Locked::take() };
            unsafe { (*storage).next_registered = *REGISTERED.0.get(); *REGISTERED.0.get() = storage };
        }
        Ok(Self { owner: storage })
    }

    pub(super) unsafe fn try_clone_locked(&self, _r: &mut Locked) -> Result<Self, CInt> {
        if unsafe { (*self.owner).queued || (*self.owner).references == 0 } { return Err(-EINVAL); }
        let next = unsafe { (*self.owner).references }.checked_add(1).ok_or(-EINVAL)?;
        unsafe { (*self.owner).references = next };
        Ok(Self { owner: self.owner })
    }
    pub(super) fn try_clone(&self) -> Result<Self, CInt> {
        let mut r = unsafe { Locked::take() };
        unsafe { self.try_clone_locked(&mut r) }
    }
    pub(super) unsafe fn release_locked(self, r: &mut Locked) {
        let this = ManuallyDrop::new(self);
        unsafe { release_owner_locked(this.owner, r) };
    }
    pub(super) fn leader_key(&self) -> EventKey { unsafe { (*self.owner).leader.key() } }
    pub(super) fn key(&self) -> EventKey { self.leader_key() }

    /// New private event is being committed with group_fd != -1. Unlike the
    /// standalone path, the original source does not add this event's own bit
    /// to its own subgroup status. No child could already name this unpublished
    /// event, so this preserves rather than discards an existing subgroup mask.
    pub(super) unsafe fn mark_nonstandalone_locked(&self, _r: &mut Locked) {
        assert!(unsafe { (*self.owner).first.is_null() && (*self.owner).live_members == 0 });
        let layout = unsafe { (*self.owner).layout };
        let raw = unsafe { (*self.owner).leader.raw_event() };
        unsafe { layout.at::<CULong>(raw, layout.pmc_status).write(0) };
    }

    /// A genuine new member can choose ANY managed descriptor's own_group,
    /// including a descriptor that is itself another group's member.
    /// Fallible allocation/retain is completed outside P/R, before host effects.
    pub(super) unsafe fn prepare_member(&self, event: &EventPin, flags: CULong) -> Result<PreparedMember, CInt> {
        if self.leader_key() == event.key() { return Err(-EINVAL); }
        let member = unsafe { crate::mem_helpers::kmalloc_tracked(size_of::<Member>() as CInt,
            flags, FILE.as_ptr().cast_mut().cast(), line!() as CInt) }.cast::<Member>();
        if member.is_null() { return Err(-ENOMEM); }
        let event_copy = match event.event_ref().try_clone() {
            Ok(pin) => pin,
            Err(error) => {
                unsafe { crate::mem_helpers::kfree_tracked(member.cast(), FILE.as_ptr().cast_mut().cast(), line!() as CInt) };
                return Err(error);
            }
        };
        let group = match self.try_clone() {
            Ok(group) => group,
            Err(error) => {
                drop(event_copy);
                unsafe { crate::mem_helpers::kfree_tracked(member.cast(), FILE.as_ptr().cast_mut().cast(), line!() as CInt) };
                return Err(error);
            }
        };
        unsafe { write(member, Member { next: null_mut(), event: ManuallyDrop::new(event_copy),
            born: 0, dead: u64::MAX, next_epoch: Epoch::new(), last_old_epoch: null_mut(),
            mapping_retired: false, mapping_claimed: false,
        }) };
        Ok(PreparedMember { group: Some(group), member })
    }

    /// Borrowing this existing external group edge avoids allocation and a new
    /// fallible snapshot retain in void scheduler/exit paths. Epoch reader-count
    /// overflow is an internal fail-stop invariant, never ENOMEM or a narrowed
    /// supported group domain. The caller keeps its real EventPin alive.
    pub(super) unsafe fn read_locked<'a>(&'a self, _r: &mut Locked) -> GroupRead<'a> {
        let owner = self.owner;
        let epoch = unsafe { (*owner).current_epoch };
        let next = unsafe { (*epoch).readers }.checked_add(1).expect("perf group reader overflow");
        unsafe { (*epoch).readers = next };
        GroupRead { group: self, epoch, sequence: unsafe { (*owner).sequence },
            tail: unsafe { (*owner).tail }, next: unsafe { (*owner).first },
            leader_pending: true, members: unsafe { (*owner).live_members }, active: true,
            logical_mask: unsafe { (*owner).layout.at::<CULong>((*owner).leader.raw_event(), (*owner).layout.pmc_status).read() },
        }
    }
    pub(super) fn read(&self) -> GroupRead<'_> {
        let mut r = unsafe { Locked::take() };
        unsafe { self.read_locked(&mut r) }
    }

    /// Actual last descriptor close. Existing GroupRead guards keep the old
    /// event and counter lease valid; later readers cannot prolong old epochs.
    /// The leading event is owned by GroupOwner rather than a member node.
    pub(super) unsafe fn retire_event_locked(&self, event: EventKey, _r: &mut Locked) {
        let owner = self.owner;
        let mut node = unsafe { (*owner).first };
        while !node.is_null() {
            if unsafe { (*node).event.key() == event && (*node).dead == u64::MAX } {
                let next = unsafe { (*owner).sequence }.checked_add(1)
                    .expect("perf close sequence was not reserved at append");
                assert!(unsafe { (*owner).reserved_closes != 0 });
                unsafe {
                    (*owner).sequence = next;
                    (*owner).reserved_closes -= 1;
                    (*node).dead = next;
                    (*node).last_old_epoch = (*owner).current_epoch;
                    let epoch = addr_of_mut!((*node).next_epoch);
                    (*(*owner).current_epoch).next = epoch;
                    (*owner).current_epoch = epoch;
                    (*owner).live_members -= 1;
                    unlink_mirror(owner, node);
                }
                return;
            }
            node = unsafe { (*node).next };
        }
    }

    /// Linear caller-owned map retirement must occur only after every epoch
    /// that COULD have seen this member is drained. Newer readers are ignored.
    /// `ack_locked` follows actual CounterLease releases, not key-only bit clear.
    pub(super) unsafe fn retired_member_locked<'a>(&'a self, _r: &mut Locked) -> Option<MemberRetirement<'a>> {
        let owner = self.owner;
        let mut member = unsafe { (*owner).first };
        while !member.is_null() {
            if unsafe { (*member).dead != u64::MAX && !(*member).mapping_retired && !(*member).mapping_claimed } {
                let mut epoch = unsafe { addr_of_mut!((*owner).first_epoch) };
                let last = unsafe { (*member).last_old_epoch };
                let mut drained = true;
                loop {
                    if epoch.is_null() { drained = false; break; }
                    if unsafe { (*epoch).readers != 0 } { drained = false; break; }
                    if epoch == last { break; }
                    epoch = unsafe { (*epoch).next };
                }
                if drained {
                    unsafe { (*member).mapping_claimed = true };
                    return Some(MemberRetirement { group: self, member, active: true, lifetime: PhantomData });
                }
            }
            member = unsafe { (*member).next };
        }
        None
    }
}
impl Drop for GroupRef {
    fn drop(&mut self) {
        let mut r = unsafe { Locked::take() };
        unsafe { release_owner_locked(self.owner, &mut r) };
    }
}

pub(super) struct PreparedMember { group: Option<GroupRef>, member: *mut Member }
impl PreparedMember {
    /// All fallible host/counter/descriptor checks and new-thread revalidation
    /// precede this atomic P/R publication window. Caller must not expose an
    /// intermediate state or do a later fallible publication after R unlock.
    pub(super) unsafe fn commit_locked(mut self, event: &mut EventPin, r: &mut Locked)
        -> Result<(), (CInt, Self)>
    {
        let group = self.group.as_ref().expect("prepared perf member consumed");
        let owner = group.owner;
        let node = self.member;
        if unsafe { (*node).event.key() } != event.key()
            || unsafe { (*owner).layout } != event.layout()
            || unsafe { (*owner).live_members } >= CInt::MAX as usize {
            return Err((-EINVAL, self));
        }
        let next = match unsafe { (*owner).sequence }.checked_add(1) {
            Some(value) => value, None => return Err((-EINVAL, self)),
        };
        let reserved = match unsafe { (*owner).reserved_closes }.checked_add(1) {
            Some(value) => value, None => return Err((-EINVAL, self)),
        };
        if next.checked_add(reserved).map_or(true, |last| last >= u64::MAX) {
            return Err((-EINVAL, self));
        }
        let containing = match unsafe { group.try_clone_locked(r) } {
            Ok(group) => group, Err(error) => return Err((error, self)),
        };
        if let Err((error, containing)) = unsafe { event.bind_group_locked(containing, &(*owner).leader, r) } {
            unsafe { containing.release_locked(r) };
            return Err((error, self));
        }
        unsafe {
            (*node).born = next;
            if (*owner).tail.is_null() { (*owner).first = node; }
            else { (*(*owner).tail).next = node; }
            (*owner).tail = node;
            (*owner).sequence = next;
            (*owner).reserved_closes = reserved;
            (*owner).live_members += 1;
            append_mirror(owner, node);
        }
        self.member = null_mut();
        let prepared_group = self.group.take().unwrap();
        unsafe { prepared_group.release_locked(r) };
        Ok(())
    }
}
impl Drop for PreparedMember {
    fn drop(&mut self) {
        if self.member.is_null() { return; }
        // Only uncommitted storage reaches this destructor, outside P/R.
        unsafe {
            ManuallyDrop::drop(&mut (*self.member).event);
            crate::mem_helpers::kfree_tracked(self.member.cast(), FILE.as_ptr().cast_mut().cast(), line!() as CInt);
        }
    }
}

/// A coherent logical group snapshot without any allocation. Traversal reads
/// each stable next pointer under R and NEVER follows captured-tail.next.
pub(super) struct GroupRead<'a> {
    group: &'a GroupRef,
    epoch: *mut Epoch,
    sequence: u64,
    tail: *mut Member,
    next: *mut Member,
    leader_pending: bool,
    members: usize,
    logical_mask: CULong,
    active: bool,
}
impl GroupRead<'_> {
    pub(super) fn event_count(&self) -> usize { self.members + 1 }
    /// Original creation-index selection, NOT hardware index/ref ownership.
    /// Caller translates only selected active snapshot events through its real
    /// executing-Thread CounterLease mapping, without adding omitted leader bits.
    pub(super) fn logical_mask(&self) -> CULong { self.logical_mask }
    pub(super) unsafe fn next_locked<'b>(&'b mut self, _r: &mut Locked) -> Option<EventBorrow<'b>> {
        if self.leader_pending {
            self.leader_pending = false;
            return Some(unsafe { (*self.group.owner).leader.borrow() });
        }
        while !self.next.is_null() {
            let member = self.next;
            self.next = if member == self.tail { null_mut() } else { unsafe { (*member).next } };
            if unsafe { (*member).born <= self.sequence && self.sequence < (*member).dead } {
                return Some(unsafe { (*member).event.borrow() });
            }
        }
        None
    }
    pub(super) unsafe fn finish_locked(mut self, _r: &mut Locked) {
        assert!(self.active);
        unsafe { (*self.epoch).readers = (*self.epoch).readers.checked_sub(1)
            .expect("perf group read released twice") };
        self.active = false;
    }
}
impl Drop for GroupRead<'_> {
    fn drop(&mut self) {
        if !self.active { return; }
        let _r = unsafe { Locked::take() };
        unsafe { (*self.epoch).readers = (*self.epoch).readers.checked_sub(1)
            .expect("perf group read released twice") };
        self.active = false;
    }
}

pub(super) struct MemberRetirement<'a> {
    group: &'a GroupRef, member: *mut Member, active: bool, lifetime: PhantomData<&'a EventRef>,
}
impl MemberRetirement<'_> {
    pub(super) fn key(&self) -> EventKey { unsafe { (*self.member).event.key() } }
    pub(super) fn group_key(&self) -> EventKey { self.group.leader_key() }
    pub(super) fn event(&self) -> EventBorrow<'_> { unsafe { (*self.member).event.borrow() } }
    /// Caller has just consumed the real per-Thread mapping tokens under R.
    pub(super) unsafe fn ack_locked(mut self, _r: &mut Locked) {
        let _group_kept_live = self.group;
        assert!(!unsafe { (*self.member).mapping_retired });
        assert!(unsafe { (*self.member).mapping_claimed });
        unsafe { (*self.member).mapping_retired = true; (*self.member).mapping_claimed = false };
        self.active = false;
    }
}
impl Drop for MemberRetirement<'_> {
    fn drop(&mut self) {
        if !self.active { return; }
        let _r = unsafe { Locked::take() };
        assert!(unsafe { (*self.member).mapping_claimed && !(*self.member).mapping_retired });
        unsafe { (*self.member).mapping_claimed = false };
    }
}

/// Process-context safe point, outside P/R/S, including after old IRQ/read
/// guards retire. Scans only registered groups, without allocating a snapshot.
/// Each temporary GroupRef protects the node while the genuine callback retires
/// that exact GROUP's mapping tokens. Other groups' uses of this event survive.
pub(super) unsafe fn drain_ready(retire_group_maps: unsafe fn(EventKey, EventKey)) {
    loop {
        let selected = {
            let mut r = unsafe { Locked::take() };
            let mut owner = unsafe { *REGISTERED.0.get() };
            let mut selected = None;
            while !owner.is_null() {
                if !unsafe { (*owner).queued } {
                    // This local borrowed facade never owns an extra edge.
                    let facade = ManuallyDrop::new(GroupRef { owner });
                    if let Some(token) = unsafe { facade.retired_member_locked(&mut r) } {
                        let node = token.member;
                        let group_key = token.group_key();
                        let event_key = token.key();
                        let keep = unsafe { facade.try_clone_locked(&mut r) };
                        // The claim moves into `selected`; suppress token Drop
                        // without acquiring R recursively in this locked scope.
                        let mut token = ManuallyDrop::new(token);
                        token.active = false;
                        match keep {
                            Ok(keep) => { selected = Some((keep, node, group_key, event_key)); break; }
                            Err(_) => unsafe { (*node).mapping_claimed = false },
                        }
                    };
                }
                owner = unsafe { (*owner).next_registered };
            }
            selected
        };
        let Some((keep, member, group_key, event_key)) = selected else { return; };
        unsafe { retire_group_maps(group_key, event_key) };
        let mut r = unsafe { Locked::take() };
        assert!(unsafe { (*member).mapping_claimed && !(*member).mapping_retired });
        unsafe { (*member).mapping_retired = true; (*member).mapping_claimed = false; keep.release_locked(&mut r) };
    }
}

unsafe fn append_mirror(owner: *mut Owner, member: *mut Member) {
    let layout = unsafe { (*owner).layout };
    let leader = unsafe { (*owner).leader.raw_event() };
    let raw = unsafe { (*member).event.raw_event() };
    unsafe {
        let head = layout.at::<AbiListHead>(leader, layout.sibling_list);
        let entry = layout.at::<AbiListHead>(raw, layout.group_entry);
        let previous = (*head).prev;
        (*entry).next = head; (*entry).prev = previous;
        (*previous).next = entry; (*head).prev = entry;
        layout.at::<*mut c_void>(raw, layout.group_leader).write(leader);
        layout.at::<CInt>(leader, layout.nr_siblings).write((*owner).live_members as CInt);
        let index = layout.at::<CInt>(raw, layout.counter_id).read();
        let bit = if index >= 0 && index < CULong::BITS as CInt { (1 as CULong) << index } else { 0 };
        let status = layout.at::<CULong>(leader, layout.pmc_status);
        status.write(status.read() | bit);
    }
}
unsafe fn unlink_mirror(owner: *mut Owner, member: *mut Member) {
    let layout = unsafe { (*owner).layout };
    let leader = unsafe { (*owner).leader.raw_event() };
    let raw = unsafe { (*member).event.raw_event() };
    unsafe {
        let entry = layout.at::<AbiListHead>(raw, layout.group_entry);
        let previous = (*entry).prev; let next = (*entry).next;
        (*previous).next = next; (*next).prev = previous;
        (*entry).next = entry; (*entry).prev = entry;
        // group_leader stays exact while old reader/event pins may use it; the
        // EventRef upstream edge keeps that actual storage alive.
        layout.at::<CInt>(leader, layout.nr_siblings).write((*owner).live_members as CInt);
        // Preserve original incremental mask bytes. Managed hardware code only
        // translates ACTIVE GroupRead members selected by its captured mask;
        // stale logical bits are never actual PMC ownership or a late bit clear.
    }
}

/// PROCESS CONTEXT only, outside P/R/S. All external GroupRefs/read guards are
/// gone before a group is queued. Finalizers release EventRefs under R but do
/// every allocator operation after dropping it; event callbacks drain separately.
pub(super) unsafe fn drain_deferred(retire_group_maps: unsafe fn(EventKey, EventKey)) {
    loop {
        let owner = {
            let _r = unsafe { Locked::take() };
            let owner = unsafe { *DEFERRED.0.get() };
            if !owner.is_null() {
                unsafe {
                    *DEFERRED.0.get() = (*owner).next_deferred;
                    let mut link = REGISTERED.0.get();
                    while !(*link).is_null() && *link != owner { link = addr_of_mut!((**link).next_registered); }
                    assert!(*link == owner);
                    *link = (*owner).next_registered;
                }
            }
            owner
        };
        if owner.is_null() { return; }
        let group_key = unsafe { (*owner).leader.key() };
        // The leading event can still be owned as another event's upstream
        // leader after THIS group dies. Its Group-specific leases must not be
        // left for the later EventOwner finalizer.
        unsafe { retire_group_maps(group_key, group_key) };
        let mut member = unsafe { (*owner).first };
        while !member.is_null() {
            let next = unsafe { (*member).next };
            if !unsafe { (*member).mapping_retired } {
                assert!(!unsafe { (*member).mapping_claimed });
                unsafe { retire_group_maps(group_key, (*member).event.key()) };
                unsafe { (*member).mapping_retired = true };
            }
            {
                let mut r = unsafe { Locked::take() };
                assert!(unsafe { (*member).next_epoch.readers == 0 });
                let event = unsafe { ManuallyDrop::take(&mut (*member).event) };
                unsafe { event.release_locked(&mut r) };
            }
            unsafe { crate::mem_helpers::kfree_tracked(member.cast(), FILE.as_ptr().cast_mut().cast(), line!() as CInt) };
            member = next;
        }
        {
            let mut r = unsafe { Locked::take() };
            assert!(unsafe { (*owner).first_epoch.readers == 0 });
            let leader = unsafe { ManuallyDrop::take(&mut (*owner).leader) };
            unsafe { leader.release_locked(&mut r) };
        }
        unsafe { crate::mem_helpers::kfree_tracked(owner.cast(), FILE.as_ptr().cast_mut().cast(), line!() as CInt) };
    }
}
