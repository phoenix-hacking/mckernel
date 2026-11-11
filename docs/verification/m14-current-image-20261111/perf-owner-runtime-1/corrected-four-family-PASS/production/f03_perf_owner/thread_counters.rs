// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private unwired perf protocol candidate. R is held by every mutating caller.
// This is bookkeeping for genuine Thread PMC bits, not a measurement refcount.

use core::ptr::{addr_of, addr_of_mut, null_mut};
use core::cell::UnsafeCell;
use super::runtime::LocalRuntime;
use crate::abi::{CInt, CULong, Thread};
const BITS: usize = CULong::BITS as usize;
const EINVAL: CInt = 22;

/// Constructed only from an actual registered, retained EventOwner identity.
/// Its address is compared, never dereferenced by this module.
#[derive(Clone, Copy, PartialEq, Eq)]
pub(super) struct EventKey { pub(super) address: usize, pub(super) generation: u64 }
impl EventKey { const EMPTY: Self = Self { address: 0, generation: 0 }; }

#[derive(Clone, Copy)]
struct Lease {
    event: EventKey,
    transaction: u64,
    pending: bool,
    open_refs: usize,
    monitor_refs: usize,
    operation_refs: usize,
}
impl Lease {
    const EMPTY: Self = Self { event: EventKey::EMPTY, transaction: 0, pending: false,
        open_refs: 0, monitor_refs: 0, operation_refs: 0 };
    fn occupied(&self) -> bool { self.event.generation != 0 }
    fn users(&self) -> bool { self.open_refs != 0 || self.monitor_refs != 0 || self.operation_refs != 0 }
}

#[derive(Clone, Copy)]
pub(super) enum LeaseUse { Open, Monitor, Operation }
/// Linear tokens: not Copy/Clone. The registry wraps them in its actual R-locked
/// RAII leases; neither counter index nor EventKey is authority to free a bit.
pub(super) struct Reservation { slot: u64, index: usize, transaction: u64, event: EventKey }
pub(super) struct CounterLease { slot: u64, index: usize, event: EventKey, use_: LeaseUse }
impl Reservation { pub(super) fn index(&self)->CInt { self.index as CInt } }
impl CounterLease { pub(super) fn index(&self) -> CInt { self.index as CInt } }

/// Preallocated at real Thread construction. Its storage can outlive Thread;
/// the terminal hook clears thread BEFORE the actual Thread allocation is freed.
pub(super) struct CounterSlot {
    generation: u64,
    thread: *mut Thread,
    leases: [Lease; BITS],
    extra:[Option<CInt>;BITS],
    runtime:[UnsafeCell<LocalRuntime>;BITS],
}

impl CounterSlot {
    /// # Safety
    /// thread is the genuine exclusive construction-time/live Thread pointer.
    /// generation is the checked nonzero registry generation, never reused.
    pub(super) unsafe fn new(thread: *mut Thread, generation: u64) -> Self {
        Self { generation, thread, leases: [Lease::EMPTY; BITS],extra:[None;BITS],runtime:[const{UnsafeCell::new(LocalRuntime::new())};BITS] }
    }

    fn validate_event(event: EventKey) -> Result<(), CInt> {
        if event.address == 0 || event.generation == 0 { Err(-EINVAL) } else { Ok(()) }
    }
    fn bit(index: usize) -> CULong { (1 as CULong) << index }

    /// Reserve using the ORIGINAL lowest-free-index policy, additionally
    /// excluding genuine private pending/owned bits for this executing Thread.
    /// No committed Thread bitmap store occurs until successful commit.
    /// # Safety
    /// R is held; the terminal hook uses the same R before invalidating thread.
    /// hardware_count is from the real selected x86 counter-count provider.
    pub(super) unsafe fn reserve(
        &mut self, event: EventKey, transaction: u64, hardware_count: CInt,
    ) -> Result<Reservation, CInt> {
        Self::validate_event(event)?;
        if self.thread.is_null() || self.generation == 0 || transaction == 0 || hardware_count <= 0 {
            return Err(-EINVAL);
        }
        let actual = unsafe { addr_of!((*self.thread).pmc_alloc_map).read() };
        for index in 0..(hardware_count as usize).min(BITS) {
            if !self.leases[index].occupied() && actual & Self::bit(index) == 0 {
                self.leases[index] = Lease { event, transaction, pending: true, ..Lease::EMPTY };
                return Ok(Reservation { slot: self.generation, index, transaction, event });
            }
        }
        // Exact no-free-counter status of ihk_mc_perfctr_alloc, not a new quota.
        Err(-EINVAL)
    }

    fn reservation(&self, token: &Reservation) -> Result<usize, CInt> {
        if token.slot != self.generation || token.index >= BITS { return Err(-EINVAL); }
        let row = &self.leases[token.index];
        if !row.pending || row.event != token.event || row.transaction != token.transaction {
            return Err(-EINVAL);
        }
        Ok(token.index)
    }

    /// # Safety
    /// R held. Consume only THIS transaction's pending reservation.
    pub(super) unsafe fn rollback(&mut self, token: Reservation) -> Result<(), (CInt, Reservation)> {
        let index = match self.reservation(&token) {
            Ok(index) => index,
            Err(error) => return Err((error, token)),
        };
        self.leases[index] = Lease::EMPTY;
        // reserve never set Thread.pmc_alloc_map, so rollback cannot clear a
        // committed bit belonging to another concurrent operation.
        Ok(())
    }

    /// # Safety
    /// R held and the actual Thread remains live under the terminal-hook
    /// contract. Publication/transaction caller owns this unique reservation.
    pub(super) unsafe fn commit(
        &mut self, token: Reservation, use_: LeaseUse,
    ) -> Result<CounterLease, (CInt, Reservation)> {
        let index = match self.reservation(&token) {
            Ok(index) => index,
            Err(error) => return Err((error, token)),
        };
        if self.thread.is_null() { return Err((-EINVAL, token)); }
        let bit = Self::bit(index);
        let current = unsafe { addr_of!((*self.thread).pmc_alloc_map).read() };
        if current & bit != 0 { return Err((-EINVAL, token)); }
        self.leases[index].pending = false;
        let row = &mut self.leases[index];
        match use_ {
            LeaseUse::Open => row.open_refs = 1,
            LeaseUse::Monitor => row.monitor_refs = 1,
            LeaseUse::Operation => row.operation_refs = 1,
        }
        unsafe { addr_of_mut!((*self.thread).pmc_alloc_map).write(current | bit) };
        Ok(CounterLease { slot: self.generation, index, event: token.event, use_ })
    }

    /// Retain an ALREADY BOUND actual per-executing-Thread mapping. Inherited
    /// scheduler paths use this prebinding; they never guess the origin index.
    /// # Safety
    /// R held; caller supplies a real retained EventOwner key.
    pub(super) unsafe fn retain(
        &mut self, event: EventKey, use_: LeaseUse,
    ) -> Result<CounterLease, CInt> {
        Self::validate_event(event)?;
        if self.thread.is_null() { return Err(-EINVAL); }
        for index in 0..BITS {
            let row = &mut self.leases[index];
            if row.event == event && !row.pending && row.users() {
                let count = match use_ {
                    LeaseUse::Open => &mut row.open_refs,
                    LeaseUse::Monitor => &mut row.monitor_refs,
                    LeaseUse::Operation => &mut row.operation_refs,
                };
                *count = count.checked_add(1).ok_or(-EINVAL)?;
                return Ok(CounterLease { slot: self.generation, index, event, use_ });
            }
        }
        Err(-EINVAL)
    }

    /// # Safety
    /// R held. Release a linear actual lease, never an event counter value.
    pub(super) unsafe fn release(&mut self, token: CounterLease) -> Result<(), (CInt, CounterLease)> {
        if token.slot != self.generation || token.index >= BITS { return Err((-EINVAL, token)); }
        let row = &mut self.leases[token.index];
        if row.event != token.event || row.pending { return Err((-EINVAL, token)); }
        let count = match token.use_ {
            LeaseUse::Open => &mut row.open_refs,
            LeaseUse::Monitor => &mut row.monitor_refs,
            LeaseUse::Operation => &mut row.operation_refs,
        };
        let Some(next) = count.checked_sub(1) else { return Err((-EINVAL, token)); };
        *count = next;
        if !row.users() {
            // Only this exact slot/event mapping installed this bit. A retired
            // slot has no raw Thread pointer, so delayed release is data-only.
            if !self.thread.is_null() {
                let current = unsafe { addr_of!((*self.thread).pmc_alloc_map).read() };
                unsafe { addr_of_mut!((*self.thread).pmc_alloc_map).write(current & !Self::bit(token.index)) };
            }
            if let Some(extra)=self.extra[token.index].take(){
                if !self.thread.is_null(){let map=unsafe{addr_of!((*self.thread).extra_reg_alloc_map).read()};unsafe{addr_of_mut!((*self.thread).extra_reg_alloc_map).write(map&!Self::bit(extra as usize));}}
            }
            // No operation owns this row now, so resetting its private state
            // cannot race a RuntimeWindow guarded by an actual Operation lease.
            unsafe{self.runtime[token.index].get().write(LocalRuntime::new());}
            self.leases[token.index] = Lease::EMPTY;
        }
        Ok(())
    }

    /// Actual final Thread path, BEFORE freeing its real memory. This retires
    /// only our known owned bits; existing/unmanaged bitmap bits are untouched.
    /// # Safety
    /// R held; caller owns the actual final live Thread and no raw Thread use by
    /// this slot can race the same mandatory terminal hook.
    pub(super) unsafe fn retire_before_destroy(&mut self, expected: *mut Thread) -> Result<(), CInt> {
        if expected.is_null() || self.thread != expected { return Err(-EINVAL); }
        let mut owned = 0;
        for index in 0..BITS {
            if self.leases[index].occupied() && !self.leases[index].pending {
                owned |= Self::bit(index);
            }
        }
        let mut extra_owned=0;
        for extra in self.extra.iter().flatten(){extra_owned|=Self::bit(*extra as usize);}
        let extra_actual=unsafe{addr_of!((*expected).extra_reg_alloc_map).read()};
        unsafe{addr_of_mut!((*expected).extra_reg_alloc_map).write(extra_actual&!extra_owned);}
        let actual = unsafe { addr_of!((*expected).pmc_alloc_map).read() };
        unsafe { addr_of_mut!((*expected).pmc_alloc_map).write(actual & !owned) };
        self.thread = null_mut();
        Ok(())
    }

    /// R held and actual Operation token names this row. Called only by a real
    /// start attempt with a nonzero genuine extra-register template. It reserves
    /// only one actually available slot, not every event's configured reg field.
    pub(super) unsafe fn reserve_extra(&mut self,token:&CounterLease,preferred:CInt)->Result<(CInt,bool),CInt>{
        if token.slot!=self.generation||token.index>=BITS||self.thread.is_null()
            || self.leases[token.index].event!=token.event{return Err(-EINVAL);}
        if let Some(index)=self.extra[token.index]{return Ok((index,false));}
        if preferred!=0&&preferred!=1{return Err(-EINVAL);}
        let actual=unsafe{addr_of!((*self.thread).extra_reg_alloc_map).read()};
        let index=if actual&Self::bit(preferred as usize)==0{preferred}else{1-preferred};
        if actual&Self::bit(index as usize)!=0{return Err(-1);}
        unsafe{addr_of_mut!((*self.thread).extra_reg_alloc_map).write(actual|Self::bit(index as usize));}
        self.extra[token.index]=Some(index);Ok((index,true))
    }
    pub(super) unsafe fn abort_new_extra(&mut self,token:&CounterLease,index:CInt){
        assert!(token.slot==self.generation&&self.leases[token.index].event==token.event&&self.extra[token.index]==Some(index));
        self.extra[token.index]=None;
        if !self.thread.is_null(){let map=unsafe{addr_of!((*self.thread).extra_reg_alloc_map).read()};unsafe{addr_of_mut!((*self.thread).extra_reg_alloc_map).write(map&!Self::bit(index as usize));}}
    }
    pub(super) unsafe fn runtime(&self,token:&CounterLease)->*mut LocalRuntime{
        assert!(token.slot==self.generation&&token.index<BITS&&self.leases[token.index].event==token.event);
        self.runtime[token.index].get()
    }

    pub(super) fn retired_and_unused(&self) -> bool {
        self.thread.is_null() && self.leases.iter().all(|row| !row.occupied())
    }
}
