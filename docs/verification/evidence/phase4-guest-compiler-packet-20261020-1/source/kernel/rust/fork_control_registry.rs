//! Process-context carrier ownership registry. There is no allocator or destructor here.
//!
//! All carrier dereferences belong to the producer/consumer module. The registry
//! lock protects only slot metadata. In particular, a visitor runs after unlock.

use core::cell::UnsafeCell;
use core::ptr::NonNull;
use core::sync::atomic::{AtomicBool, Ordering};

use crate::fork_control_guest::Carrier;

pub(crate) const CAPACITY: usize = 64;
const ENOENT: i32 = -2;
const EIO: i32 = -5;
const EBUSY: i32 = -16;
const EINVAL: i32 = -22;
const ENOSPC: i32 = -28;
const EOVERFLOW: i32 = -75;

#[repr(C)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Handle {
    pub(crate) slot: u32,
    pub(crate) reserved: u32,
    pub(crate) epoch: u64,
}

impl Handle {
    pub(crate) const EMPTY: Self = Self { slot: 0, reserved: 0, epoch: 0 };

    fn valid(self) -> bool {
        self.reserved == 0 && (self.slot as usize) < CAPACITY && self.epoch != 0
    }
}

const _: () = {
    assert!(core::mem::size_of::<Handle>() == 16);
    assert!(core::mem::align_of::<Handle>() == 8);
    assert!(core::mem::offset_of!(Handle, slot) == 0);
    assert!(core::mem::offset_of!(Handle, reserved) == 4);
    assert!(core::mem::offset_of!(Handle, epoch) == 8);
};

#[derive(Clone, Copy, Eq, PartialEq)]
enum Phase { Private, Escaped, Retained }

#[derive(Clone, Copy)]
struct Slot {
    carrier: Option<NonNull<Carrier>>,
    epoch: u64,
    phase: Phase,
    busy: bool,
}

impl Slot {
    const EMPTY: Self = Self {
        carrier: None, epoch: 0, phase: Phase::Private, busy: false,
    };
}

struct State {
    slots: [Slot; CAPACITY],
    last_epoch: u64,
}

impl State {
    fn matching(&mut self, handle: Handle) -> Option<&mut Slot> {
        if handle.reserved != 0 || handle.epoch == 0 { return None; }
        let slot = self.slots.get_mut(handle.slot as usize)?;
        if slot.carrier.is_some() && slot.epoch == handle.epoch { Some(slot) } else { None }
    }
}

struct Registry {
    held: AtomicBool,
    state: UnsafeCell<State>,
}

// SAFETY: every access to state is exclusively bracketed by lock/unlock; no
// carrier reference is made here, and the lock is released before user code.
unsafe impl Sync for Registry {}

impl Registry {
    fn lock(&self) {
        while self.held.swap(true, Ordering::Acquire) {
            // Existing core-linked reviewed assembly primitive. Process context only.
            unsafe { crate::x86_cpu_helpers::cpu_pause(); }
        }
    }

    fn unlock(&self) { self.held.store(false, Ordering::Release); }
}

static REGISTRY: Registry = Registry {
    held: AtomicBool::new(false),
    state: UnsafeCell::new(State { slots: [Slot::EMPTY; CAPACITY], last_epoch: 0 }),
};

/// Transfer ownership to the registry only on success. On error the caller
/// still owns `carrier` and must perform any destruction after this call.
///
/// # Safety
/// `carrier` is a unique, initialized, live allocation, absent from this registry.
/// The caller must stop accessing it except through the explicit private
/// initialization/begin protocol or a scoped visitor. It must not be freed after
/// success unless `cancel` returns the owned pointer. Initialization using the
/// returned handle/epoch must finish before `begin` publishes eligibility.
pub(crate) unsafe fn insert_private(
    carrier: NonNull<Carrier>,
) -> Result<Handle, (i32, NonNull<Carrier>)> {
    REGISTRY.lock();
    let result = {
        let state = &mut *REGISTRY.state.get();
        match state.last_epoch.checked_add(1) {
            None => Err((EOVERFLOW, carrier)),
            Some(epoch) => match state.slots.iter().position(|slot| slot.carrier.is_none()) {
                None => Err((ENOSPC, carrier)),
                Some(index) => {
                    state.last_epoch = epoch;
                    state.slots[index] = Slot {
                        carrier: Some(carrier), epoch, phase: Phase::Private, busy: false,
                    };
                    Ok(Handle { slot: index as u32, reserved: 0, epoch })
                }
            },
        }
    };
    REGISTRY.unlock();
    result
}

/// Mark the allocation escaped before returning its pointer. There is no
/// transition from Escaped/Retained back to Private, and no implicit free.
pub(crate) fn begin(handle: Handle) -> Result<NonNull<Carrier>, i32> {
    if !handle.valid() { return Err(EINVAL); }
    REGISTRY.lock();
    let result = unsafe {
        match (&mut *REGISTRY.state.get()).matching(handle) {
            None => Err(ENOENT),
            Some(slot) if slot.busy || slot.phase != Phase::Private => Err(EBUSY),
            Some(slot) => {
                slot.phase = Phase::Escaped;
                Ok(slot.carrier.unwrap())
            }
        }
    };
    REGISTRY.unlock();
    result
}

/// Remove a still-private, nonbusy allocation and return ownership for freeing
/// outside the lock. An escaped allocation is retained and returns EBUSY.
pub(crate) fn cancel(handle: Handle) -> Result<NonNull<Carrier>, i32> {
    if !handle.valid() { return Err(EINVAL); }
    REGISTRY.lock();
    let result = unsafe {
        match (&mut *REGISTRY.state.get()).matching(handle) {
            None => Err(ENOENT),
            Some(slot) if slot.busy => Err(EBUSY),
            Some(slot) if slot.phase != Phase::Private => {
                slot.phase = Phase::Retained;
                Err(EBUSY)
            }
            Some(slot) => Ok(slot.carrier.take().unwrap()),
        }
    };
    REGISTRY.unlock();
    result
}

/// Quarantine the allocation without freeing it or assuming host retirement.
pub(crate) fn retain(handle: Handle) -> Result<(), i32> {
    if !handle.valid() { return Err(EINVAL); }
    REGISTRY.lock();
    let result = unsafe {
        match (&mut *REGISTRY.state.get()).matching(handle) {
            None => Err(ENOENT),
            Some(slot) if slot.busy => Err(EBUSY),
            Some(slot) => { slot.phase = Phase::Retained; Ok(()) }
        }
    };
    REGISTRY.unlock();
    result
}

/// # Safety
/// The unique current producer has acquired the SAME final ACK Response and
/// positively checked its constructor graph destruction. No observer/transport
/// retains a Carrier borrow. This only detaches metadata; destruction runs
/// outside this lock. Stale snapshots can no longer discover the allocation.
pub(crate) unsafe fn detach_terminal(handle:Handle,expected:NonNull<Carrier>)->Result<NonNull<Carrier>,i32>{
    if !handle.valid(){return Err(EINVAL);}
    REGISTRY.lock();
    let result=match (&mut *REGISTRY.state.get()).matching(handle){
        Some(slot) if !slot.busy&&slot.phase!=Phase::Private&&slot.carrier==Some(expected)=>Ok(slot.carrier.take().unwrap()),
        Some(_)=>Err(EBUSY),None=>Err(ENOENT),
    };
    REGISTRY.unlock();result
}

/// Execute one exclusive, scoped carrier callback outside the registry lock.
/// Reentrant visits/cancel/retain/begin on this handle see EBUSY. A callback that
/// does not return leaves the allocation busy and retained by the registry.
///
/// # Safety
/// The callback must not free the carrier, retain references into it, or permit
/// concurrent direct dereferences through an escaped pointer. All such accesses
/// must share this visit protocol (or an externally proven stronger exclusion).
pub(crate) unsafe fn visit(handle: Handle, callback: impl FnOnce(NonNull<Carrier>) -> i32) -> i32 {
    if !handle.valid() { return EINVAL; }
    REGISTRY.lock();
    let claimed = {
        match (&mut *REGISTRY.state.get()).matching(handle) {
            None => Err(ENOENT),
            Some(slot) if slot.busy => Err(EBUSY),
            Some(slot) => { slot.busy = true; Ok(slot.carrier.unwrap()) }
        }
    };
    REGISTRY.unlock();
    let carrier = match claimed { Ok(carrier) => carrier, Err(rc) => return rc };
    let callback_rc = callback(carrier);
    REGISTRY.lock();
    let result = {
        match (&mut *REGISTRY.state.get()).matching(handle) {
            Some(slot) if slot.carrier == Some(carrier) && slot.busy => {
                slot.busy = false;
                callback_rc
            }
            _ => EIO,
        }
    };
    REGISTRY.unlock();
    result
}

/// Copy only eligible handle metadata for the actual return hook. A snapshot
/// grants no carrier access: each candidate still needs an epoch-checked visit.
/// Private entries are excluded until producer initialization and begin finish.
pub(crate) fn snapshot_handles(out: &mut [Handle; CAPACITY]) -> usize {
    REGISTRY.lock();
    let mut count = 0;
    unsafe {
        for (index, slot) in (&*REGISTRY.state.get()).slots.iter().enumerate() {
            if slot.carrier.is_some() && slot.phase != Phase::Private {
                out[count] = Handle { slot: index as u32, reserved: 0, epoch: slot.epoch };
                count += 1;
            }
        }
    }
    REGISTRY.unlock();
    count
}
