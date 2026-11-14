// SPDX-License-Identifier: GPL-2.0
//! Bounded application connections and independently pumped prepare/cleanup.

use super::{
    application_pager::Operation as PagerOperation,
    application_rpc::{Exchange, Token},
    application_syscall::Request,
    smp_application_image::{Preparation, ForkAdoption, ForkGeometry, ForkIdentity, ForkPhase,
        ForkReservation, FORK_NATIVE_MARKER},
    smp_application_syscall::Mailbox,
    smp_file_pager::{Prepared as PagerFile, Registry as Pagers},
    smp_memory::{ProcfsProcess, ProcfsRemote, SyscallResponse},
    smp_resource::OsToken,
};
use core::sync::atomic::{AtomicBool, AtomicI32, AtomicUsize, Ordering};
use core::ptr::{self, NonNull};
use kernel::{
    bindings,
    prelude::*,
    sync::{new_condvar, new_mutex, Arc, CondVar, Mutex},
};

pub(crate) const CAPACITY: usize = 64;
const PUBLICATION_TIMEOUT_SECONDS: u64 = 5;

#[path = "smp_fork_link.rs"]
mod fork_link;
pub(crate) use fork_link::PreparedLinkTicket;
#[path = "smp_fork_ingress.rs"]
mod fork_ingress;

fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}

// Structural MM and referenced TGID ownership survives close without pinning
// mm_users (which would cycle through a VMA's application connection).
struct ForkChildOwner {
    pid: NonNull<bindings::pid>,
    mm: NonNull<bindings::mm_struct>,
    number: i32,
}
// SAFETY: Only immutable identity and the Linux owned PID/MM references move.
unsafe impl Send for ForkChildOwner {}
// SAFETY: No MM mapping access follows from these shared structural identities.
unsafe impl Sync for ForkChildOwner {}
impl ForkChildOwner {
    fn current() -> Result<Self> {
        // SAFETY: Linux acquires both references from the live current task.
        let pid = NonNull::new(unsafe {
            bindings::get_task_pid(bindings::get_current(), bindings::pid_type_PIDTYPE_TGID)
        }).ok_or(ESRCH)?;
        let Some(mm) = NonNull::new(unsafe { bindings::get_task_mm(bindings::get_current()) }) else {
            unsafe { bindings::put_pid(pid.as_ptr()) };
            return Err(ESRCH);
        };
        let number = unsafe { bindings::pid_nr_ns(pid.as_ptr(), ptr::addr_of_mut!(bindings::init_pid_ns)) };
        let count = unsafe { AtomicI32::from_ptr(ptr::addr_of_mut!(
            (*mm.as_ptr()).__bindgen_anon_1.__bindgen_anon_1.mm_count.counter
        )) };
        let grabbed = if number > 0 {
            count.fetch_update(Ordering::Relaxed, Ordering::Relaxed,
                |value| (value > 0).then(|| value.checked_add(1)).flatten()).map_err(|_| errno(-75))
        } else { Err(ESRCH) };
        // SAFETY: End transient mm_users even on failure; only mm_count may
        // survive publication, matching the established mirror lifetime rule.
        unsafe { bindings::mmput(mm.as_ptr()) };
        if let Err(error) = grabbed {
            unsafe { bindings::put_pid(pid.as_ptr()) };
            return Err(error);
        }
        Ok(Self { pid, mm, number })
    }
}
impl Drop for ForkChildOwner {
    fn drop(&mut self) {
        let count = unsafe { AtomicI32::from_ptr(ptr::addr_of_mut!(
            (*self.mm.as_ptr()).__bindgen_anon_1.__bindgen_anon_1.mm_count.counter
        )) };
        let old = count.fetch_sub(1, Ordering::SeqCst);
        assert!(old > 0);
        if old == 1 { unsafe { bindings::__mmdrop(self.mm.as_ptr()) }; }
        unsafe { bindings::put_pid(self.pid.as_ptr()) };
    }
}

// BEGIN FORK BACKEND RESERVATION
struct PreparedForkSeal {
    sealed: AtomicBool,
}

struct ChildFork {
    owner: Arc<ForkChildOwner>,
    reservation: ForkReservation,
    seal: Arc<PreparedForkSeal>,
    // Deliberate retention after any sealed outcome. Only an actual revoke,
    // completed TLB barrier and final guest destruction ACK may break it.
    retained_remote: Option<Arc<Remote>>,
    link: Option<fork_link::ForkLinkRecord>,
    // A failed UNSEALED payload rollback retains the actual typed lease and
    // its publication freeze for later exact reconciliation, never a raw lease.
    held_lease: Option<PreparedForkLease>,
}

// This capability cannot be copied or manufactured from the diagnostic token.
// Immutable authority and the preallocated seal survive child-MM exclusion.
// BEGIN PREPARED FORK LEASE
pub(crate) struct PreparedForkLease {
    remote: Option<Arc<Remote>>,
    seal: Arc<PreparedForkSeal>,
    child: Token,
    token: u64,
    identity: ForkIdentity,
}

// This view cannot outlive or be copied independently of the exclusive lease
// borrow. Only the SAME preallocated atomic is lent to the synchronous bridge.
pub(crate) struct PreparedForkBorrow<'lease> {
    pub(crate) identity: ForkIdentity,
    pub(crate) sealed: &'lease AtomicBool,
}

#[allow(dead_code)]
impl PreparedForkLease {
    pub(crate) fn borrow_seal(&mut self) -> PreparedForkBorrow<'_> {
        PreparedForkBorrow { identity: self.identity, sealed: &self.seal.sealed }
    }

    /// The consumer calls this exactly at its infallible VMA owner/PFN commit.
    /// No lock, allocation, callback, destructor or cancellation processing is
    /// permitted here. Repeated stores do not weaken the exclusive capability.
    pub(crate) fn seal(&mut self) {
        self.seal.sealed.store(true, Ordering::Release);
    }

    /// Call after MM unlock, local publication and publication-guard release.
    pub(crate) fn finish(mut self) {
        self.finish_inner(true);
    }

    /// Retain an unsealed lease after an uncertain payload rollback. This is
    /// recoverable exact-key storage; its prepared state and parent pin remain.
    pub(crate) fn retain_prepared(self) -> core::result::Result<(), Self> {
        let Some(remote) = self.remote.as_ref().cloned() else { return Err(self); };
        let mut slots = remote.slots.lock();
        let Ok(fork) = child_fork_in_slots(&mut slots, self.child, self.token) else { return Err(self); };
        if fork.reservation.identity != self.identity || !Arc::ptr_eq(&fork.seal, &self.seal)
            || !fork.reservation.state.prepared() || fork.held_lease.is_some()
        { return Err(self); }
        fork.retained_remote = Some(remote.clone());
        fork.held_lease = Some(self);
        drop(slots);
        Ok(())
    }

    /// The original MM callback and all local guards have returned. The exact
    /// IHK owner/capsule has become publishable before entry; this one slots
    /// lock covers phase/key/SAME seal validation, fixed first receipt write,
    /// and readiness. No fallible allocation or external callback occurs here.
    /// # Safety
    /// The genuine IHK capsule owns this initialized context under the SAME
    /// scoped adoption. No other payload borrow may exist before slots unlock.
    /// The caller passes a pointer, never an exclusive reference spanning the
    /// publication unlock and return; LINK may borrow immediately after unlock.
    pub(crate) unsafe fn finish_with_payload(&mut self, mut payload: NonNull<super::smp_memory::ForkPayload>) -> Result {
        let remote = self.remote.as_ref().ok_or(EIO)?.clone();
        let mut slots = remote.slots.lock();
        remote.transport_health()?;
        {
            let fork = child_fork_in_slots(&mut slots, self.child, self.token)?;
            if fork.reservation.identity != self.identity || !Arc::ptr_eq(&fork.seal, &self.seal)
                || !self.seal.sealed.load(Ordering::Acquire) || fork.held_lease.is_some()
                || !fork.reservation.state.prepared()
            { return Err(EACCES); }
            fork.reservation.state.finish_lease(self.identity, true, true)?;
            if fork.reservation.state.phase() != ForkPhase::AdoptedAwaitFirstReturn { return Err(EBUSY); }
        }
        let mut result = {
            // SAFETY: The actual IHK scope pins the initialized capsule. This
            // exclusive reference exists only inside the slots-held block;
            // its function-argument protector ends before publication unlock.
            let payload = unsafe { payload.as_mut() };
            fork_link::commit_adopted_fork_carrier_in_slots(
                remote.owner, &mut slots, self.child, self.identity, payload,
            )
        };
        if let Ok(fork) = child_fork_in_slots(&mut slots, self.child, self.token) {
            if result.is_err() { let _ = fork.reservation.state.quarantine(self.identity); }
            fork.retained_remote = Some(remote.clone());
        } else { result = Err(EIO); }
        if let Some(parent) = slots.iter_mut().flatten().find(|entry| entry.key().wire() == self.identity.parent) {
            if let Some(refs) = parent.fork_prepared_parent_refs.checked_sub(1) { parent.fork_prepared_parent_refs = refs; }
            else {
                parent.quarantined = true;
                result = Err(EIO);
                if let Ok(fork) = child_fork_in_slots(&mut slots, self.child, self.token) {
                    let _ = fork.reservation.state.quarantine(self.identity);
                }
            }
        } else { result = Err(EIO); }
        self.remote = None;
        drop(slots);
        result
    }

    fn finish_inner(&mut self, completed: bool) {
        let Some(remote) = self.remote.take() else { return; };
        let sealed = self.seal.sealed.load(Ordering::Acquire);
        let mut slots = remote.slots.lock();
        let transport_failed = remote.transport_health().is_err();
        let mut retained = false;
        if let Ok(fork) = child_fork_in_slots(&mut slots, self.child, self.token) {
            if fork.reservation.identity == self.identity
                && core::ptr::eq(&*fork.seal, &*self.seal)
            {
                if transport_failed { let _ = fork.reservation.state.quarantine(self.identity); }
                let result = fork.reservation.state.finish_lease(self.identity, sealed, completed);
                if result.is_err() { let _ = fork.reservation.state.quarantine(self.identity); }
                if sealed {
                    // This is outside MM/local publication exclusion. The
                    // preexisting Arc is cloned only here, never during seal.
                    fork.retained_remote = Some(remote.clone());
                    retained = true;
                }
            }
        }
        if let Some(parent) = slots.iter_mut().flatten().find(|entry| entry.key().wire() == self.identity.parent) {
            parent.fork_prepared_parent_refs = parent.fork_prepared_parent_refs.saturating_sub(1);
        }
        drop(slots);
        if sealed && !retained {
            // Corruption/failure cannot turn a sealed root into free ownership.
            // Retain the whole backend if the exact slot cannot be found.
            core::mem::forget(remote);
        }
    }
}

impl Drop for PreparedForkLease {
    fn drop(&mut self) { self.finish_inner(false); }
}
// END PREPARED FORK LEASE

// Caller holds this Remote's slots lock for discovery through publication.
// All child-owner allocation precedes this function; no guest/root is accessed.
fn reserve_fork_in_slots(
    owner: OsToken, slots: &mut [Option<Entry>], parent: Token, child: Token,
    child_owner: Arc<ForkChildOwner>, geometry: ForkGeometry, seal: Arc<PreparedForkSeal>,
) -> Result<(u64, ForkIdentity)> {
    if parent == child { return Err(EINVAL); }
    let parent_index = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key() == parent)).ok_or(ENOENT)?;
    let child_index = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key() == child)).ok_or(ENOENT)?;
    let p = slots[parent_index].as_ref().unwrap();
    let c = slots[child_index].as_ref().unwrap();
    if p.closed || p.needs_cleanup || p.quarantined || !p.scheduled
        || c.closed || c.needs_cleanup || c.quarantined || c.scheduled || c.prepare.is_some()
        || c.fork.is_some() || c.fork_ingress.is_some() || c.cleanup.pid() != child_owner.number
    { return Err(EBUSY); }
    if p.owner_slot != owner.slot() as i32 || c.owner_slot != owner.slot() as i32
        || p.owner_generation != owner.generation() || c.owner_generation != owner.generation()
    {
        return Err(EACCES);
    }
    let parent_pid = p.cleanup.pid();
    let proof = p.syscalls.unique_delivered(|request| {
        let args = request.arguments();
        request.number() == 56 && request.pid() == parent_pid
            && !matches!(args[0], 1 | 2 | 3)
            && args[1] == geometry.start && args[2] == geometry.length && args[3] == geometry.root
            && args[4] != 0 && args[5] == FORK_NATIVE_MARKER
    }).map_err(errno)?.ok_or(ENOENT)?;
    let (worker, serial, request) = proof;
    let nonce = request.arguments()[4];
    if slots.iter().flatten().filter_map(|entry| entry.fork.as_ref()).any(|fork| {
        let key = fork.reservation.identity;
        key.root == geometry.root || key.parent == parent.wire()
            && (key.delivery == serial || key.nonce == nonce)
    }) { return Err(EBUSY); }
    let identity = ForkIdentity {
        slot: owner.slot(), generation: owner.generation(), parent: parent.wire(),
        worker, delivery: serial, child: child.wire(), child_pid: child_owner.number,
        child_mm: child_owner.mm.as_ptr() as usize, root: geometry.root,
        start: geometry.start, length: geometry.length, nonce,
    };
    let mut state = ForkAdoption::reserve(identity)?;
    state.prepare_lease()?;
    let parent_refs = p.fork_prepared_parent_refs.checked_add(1).ok_or(EOVERFLOW)?;
    let token = Token::allocate().map_err(errno)?;
    let result = token.wire();
    slots[parent_index].as_mut().unwrap().fork_prepared_parent_refs = parent_refs;
    slots[child_index].as_mut().unwrap().fork = Some(ChildFork {
        owner: child_owner, seal, retained_remote: None, link: None, held_lease: None,
        reservation: ForkReservation { token, identity, cpu: request.cpu(), first: request,
            state, return_value: None, return_published: false },
    });
    Ok((result, identity))
}

fn child_fork_in_slots(slots: &mut [Option<Entry>], child: Token, token: u64) -> Result<&mut ChildFork> {
    let entry = slots.iter_mut().flatten().find(|entry| entry.key() == child).ok_or(ENOENT)?;
    let fork = entry.fork.as_mut().ok_or(ENOENT)?;
    if fork.reservation.token.wire() != token || fork.reservation.identity.child != child.wire()
        || fork.owner.number != entry.cleanup.pid()
        || fork.owner.mm.as_ptr() as usize != fork.reservation.identity.child_mm
    { return Err(EACCES); }
    Ok(fork)
}

fn abort_fork_in_slots(slots: &mut [Option<Entry>], child: Token, token: u64) -> Result {
    let fork = child_fork_in_slots(slots, child, token)?;
    if let Some(link) = &fork.link { link.cancel_if_open()?; }
    fork.reservation.state.request_abort(fork.reservation.identity)
}

fn abort_parent_forks(slots: &mut [Option<Entry>], parent: Token, worker: Option<u64>) {
    fork_ingress::abort_parent_ingress(slots, parent, worker);
    for fork in slots.iter_mut().flatten().filter_map(|entry| entry.fork.as_mut()) {
        let identity = fork.reservation.identity;
        if identity.parent == parent.wire() && worker.is_none_or(|worker|
            identity.worker == worker || fork.link.as_ref().is_some_and(|link| link.has_second_worker(worker))) {
            if fork.link.as_ref().is_some_and(|link| link.cancel_if_open().is_err()) { continue; }
            let _ = fork.reservation.state.request_abort(identity);
        }
    }
}

// Pending cancellation can destroy the guest root on a negative first RET.
// Keep the original response claim unpublished while MM adoption is active;
// after seal, abort/quarantine stays frozen until the real host revoke barrier.
fn fork_publication_frozen(slots: &[Option<Entry>], parent: Token, cpu: i32) -> bool {
    if fork_ingress::publication_frozen(slots, parent, cpu) { return true; }
    slots.iter().flatten().filter_map(|entry| entry.fork.as_ref()).any(|fork| {
        let record = &fork.reservation;
        record.identity.parent == parent.wire() && record.cpu == cpu
            && (record.state.prepared()
                || fork.seal.sealed.load(Ordering::Acquire)
                    && matches!(record.state.phase(), ForkPhase::AbortRequested
                        | ForkPhase::Quarantined))
    })
}

fn authorize_fork_return(slots: &[Option<Entry>], parent: Token, worker: u64, serial: u64, cpu: i64, value: i64) -> Result {
    fork_link::authorize_return(slots, parent, worker, serial, cpu, value)?;
    for fork in slots.iter().flatten().filter_map(|entry| entry.fork.as_ref()) {
        let record = &fork.reservation;
        if record.identity.parent == parent.wire() && record.identity.worker == worker
            && record.identity.delivery == serial
        {
            if record.cpu as i64 != cpu { return Err(EINVAL); }
            record.authorize_return(value)?;
        }
    }
    Ok(())
}

fn record_fork_return(slots: &mut [Option<Entry>], parent: Token, worker: u64, serial: u64, value: i64) {
    fork_link::record_return(slots, parent, worker, serial, value);
    for fork in slots.iter_mut().flatten().filter_map(|entry| entry.fork.as_mut()) {
        let record = &mut fork.reservation;
        if record.identity.parent == parent.wire() && record.identity.worker == worker && record.identity.delivery == serial {
            record.return_value = Some(value);
            if value < 0 { let _ = record.state.request_abort(record.identity); }
        }
    }
}

fn observe_fork_publication(slots: &mut [Option<Entry>], parent: Token) {
    let Some(parent_index) = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key() == parent)) else { return; };
    for index in 0..slots.len() {
        let completion = slots[index].as_ref().and_then(|entry| entry.fork.as_ref()).and_then(|fork| {
            let record = &fork.reservation;
            if record.identity.parent != parent.wire() || record.return_published { return None; }
            Some(slots[parent_index].as_ref().unwrap().syscalls.returned(record.identity.worker, record.identity.delivery))
        });
        if let Some(result) = completion {
            let record = &mut slots[index].as_mut().unwrap().fork.as_mut().unwrap().reservation;
            match result {
                Ok(true) => record.observe_publication(),
                Ok(false) => {},
                Err(_) => { let _ = record.state.quarantine(record.identity); },
            }
        }
    }
}
// END FORK BACKEND RESERVATION

struct Entry {
    cleanup: Exchange,
    owner_slot: i32,
    owner_generation: u64,
    prepare: Option<Preparation>,
    schedule: Option<Exchange>,
    retirement: Option<Exchange>,
    retirement_after: u64,
    procfs: Option<Arc<ProcfsProcess>>,
    syscalls: Mailbox<SyscallResponse>,
    scheduled: bool,
    needs_cleanup: bool,
    closed: bool,
    quarantined: bool,
    fork: Option<ChildFork>,
    fork_ingress: Option<fork_ingress::ForkIngressMarker>,
    fork_prepared_parent_refs: u32,
}

impl Entry {
    fn key(&self) -> Token {
        self.cleanup.token()
    }
    fn next(&self) -> &Exchange {
        match self.prepare.as_ref() {
            Some(prepare) if prepare.result().is_none() => &prepare.exchange,
            _ => match self.schedule.as_ref() {
                Some(schedule) if schedule.result().is_none() => schedule,
                _ => self.retirement.as_ref().unwrap_or(&self.cleanup),
            },
        }
    }
    fn next_mut(&mut self) -> &mut Exchange {
        match self.prepare.as_mut() {
            Some(prepare) if prepare.result().is_none() => &mut prepare.exchange,
            _ => match self.schedule.as_mut() {
                Some(schedule) if schedule.result().is_none() => schedule,
                _ => self.retirement.as_mut().unwrap_or(&mut self.cleanup),
            },
        }
    }
    fn release_ready(&self) -> bool {
        self.fork.is_none() && self.fork_ingress.is_none() && self.fork_prepared_parent_refs == 0 && !self.quarantined
            && self.cleanup.release_ready()
            && self.syscalls.drained()
            && self.procfs.as_ref().is_none_or(|procfs| procfs.drained())
            && (!self.scheduled
                || self.cleanup.result() == Some(0)
                    && self
                        .retirement
                        .as_ref()
                        .is_some_and(|query| query.result() == Some(0))
                    && self
                        .procfs
                        .as_ref()
                        .is_some_and(|procfs| procfs.threads_retired()))
    }

    fn request_cleanup(&mut self) -> Result {
        self.needs_cleanup = true;
        if let Some(procfs) = &self.procfs {
            procfs.close();
        }
        if self.quarantined {
            return Err(errno(-71));
        }
        // Close both admissions before waiting: procfs rundown can need a
        // blocked syscall to be cancelled by the independent packet pump.
        if let Err(error) = self.syscalls.close() {
            self.quarantined = true;
            return Err(errno(error));
        }
        if let Some(ingress) = &mut self.fork_ingress {
            // Constructor/rollback owns the original response and root hold.
            // A close latches cancellation; it never dispatches guest cleanup.
            ingress.cancel();
            return Ok(());
        }
        if let Some(fork) = &mut self.fork {
            // No unpublished-child PID absence or cleanup ACK proves VM safety.
            // Keep the root identity and structural child owners until the
            // separately gated revoke/final-destruction protocol is connected.
            if let Some(link) = &fork.link { link.cancel_if_open()?; }
            fork.reservation.state.request_abort(fork.reservation.identity)?;
            return Ok(());
        }
        if !self.scheduled {
            self.schedule = None; // Nothing published can be cancelled here.
        }
        if !self.syscalls.drained() || self.procfs.as_ref().is_some_and(|procfs| !procfs.drained())
        {
            return Ok(());
        }
        if let Some(prepare) = &self.prepare {
            if prepare.result().is_none() {
                return Ok(());
            }
            if self.cleanup.reserved() {
                self.cleanup
                    .cleanup_target(
                        prepare.input.cpu,
                        if self.scheduled { 0 } else { prepare.thread },
                    )
                    .map_err(errno)?;
            }
        }
        if self.cleanup.reserved() {
            self.cleanup.begin().map_err(errno)?;
        }
        if self.scheduled && self.cleanup.result().is_some() {
            kernel::error::to_result(self.cleanup.result().unwrap())?;
            let retry = self
                .retirement
                .as_ref()
                .is_none_or(|query| query.result() == Some(-11));
            // SAFETY: ktime_get_seconds is a permanent Linux monotonic-clock
            // export, callable while this mutex is held and independent of any
            // retiring application. Its scalar result neither borrows nor
            // changes the retained exchange state.
            let now = unsafe { bindings::ktime_get_seconds() } as u64;
            if retry && now >= self.retirement_after {
                let mut query =
                    Exchange::retirement(self.owner_slot, self.cleanup.cpu(), self.cleanup.pid())
                        .map_err(errno)?;
                query.begin().map_err(errno)?;
                self.retirement = Some(query);
            }
        }
        Ok(())
    }
}

#[pin_data]
pub(crate) struct Remote {
    owner: OsToken,
    procfs: Arc<ProcfsRemote>,
    #[pin]
    slots: Mutex<Vec<Option<Entry>>>,
    #[pin]
    changed: CondVar,
    syscall_cursor: AtomicUsize,
    transport_error: AtomicI32,
    shutdown_closed: AtomicBool,
    pagers: Arc<Pagers>,
    release_token: Token,
    #[pin]
    releases: Mutex<Mailbox<SyscallResponse>>,
}

impl Remote {
    pub(crate) fn new(owner: OsToken, procfs: Arc<ProcfsRemote>) -> Result<Arc<Self>> {
        let pagers = Pagers::new()?;
        let releases = Mailbox::new().map_err(errno)?;
        let release_token = Token::allocate().map_err(errno)?;
        let mut slots = Vec::with_capacity(CAPACITY, GFP_KERNEL)?;
        for _ in 0..CAPACITY {
            slots.push(None, GFP_KERNEL)?;
        }
        Arc::pin_init(
            pin_init!(Self { owner, procfs, slots <- new_mutex!(slots), changed <- new_condvar!(),
                syscall_cursor: AtomicUsize::new(0), transport_error: AtomicI32::new(0), shutdown_closed: AtomicBool::new(false), pagers, release_token,
                releases <- new_mutex!(releases) }),
            GFP_KERNEL,
        )
    }

    pub(crate) fn reserve(&self, pid: i32) -> Result<Token> {
        let syscalls = Mailbox::new().map_err(errno)?;
        let mut slots = self.slots.lock();
        self.transport_health()?;
        if self.shutdown_closed.load(Ordering::Acquire) { return Err(ENODEV); }
        // Late and quarantined requests continue excluding numeric PID reuse.
        if slots
            .iter()
            .flatten()
            .any(|entry| entry.cleanup.pid() == pid)
        {
            return Err(EINVAL);
        }
        let slot = slots.iter_mut().find(|slot| slot.is_none()).ok_or(EAGAIN)?;
        let cleanup = Exchange::new(self.owner.slot() as i32, 0, pid).map_err(errno)?;
        let token = cleanup.token();
        *slot = Some(Entry {
            cleanup,
            owner_slot: self.owner.slot() as i32,
            owner_generation: self.owner.generation(),
            prepare: None,
            schedule: None,
            retirement: None,
            retirement_after: 0,
            procfs: None,
            syscalls,
            scheduled: false,
            needs_cleanup: false,
            closed: false,
            quarantined: false,
            fork: None,
            fork_ingress: None,
            fork_prepared_parent_refs: 0,
        });
        Ok(token)
    }

    /// Share the reservation mutex with reserve: an Application clone taken
    /// immediately before shutdown cannot admit a new slot afterward. Busy
    /// entries remain intact so their existing owners can finish normal cleanup.
    pub(crate) fn shutdown_close_if_quiescent(&self) -> Result {
        let slots = self.slots.lock();
        self.shutdown_closed.store(true, Ordering::Release);
        if slots.iter().any(Option::is_some) || !self.releases.lock().drained() {
            return Err(EBUSY);
        }
        self.pagers.shutdown_quiescent()
    }

    /// This is a negative ownership check, never a cancellation/discard path.
    pub(crate) fn shutdown_quiescent(&self) -> Result {
        let slots = self.slots.lock();
        if !self.shutdown_closed.load(Ordering::Acquire)
            || slots.iter().any(Option::is_some) || !self.releases.lock().drained() {
            return Err(EBUSY);
        }
        self.pagers.shutdown_quiescent()
    }

    pub(crate) fn queued_cpu(&self) -> Option<i32> {
        if self.transport_health().is_err() {
            return None;
        }
        self.slots
            .lock()
            .iter()
            .flatten()
            .map(Entry::next)
            .find(|exchange| exchange.queued())
            .map(Exchange::cpu)
    }

    pub(crate) fn advance(&self) -> Result {
        let mut slots = self.slots.lock();
        self.transport_health()?;
        // This task continues even if the original RET waiter is dying. No
        // intentionally blocking user syscall is timed: only accepted results
        // whose response/wake has not reached real publication are bounded.
        // SAFETY: ktime_get_seconds is the same permanent, non-sleeping Linux
        // clock export used for retirement retries. Reading it while slots is
        // locked cannot alias application-owned memory or publish a response.
        let now = unsafe { bindings::ktime_get_seconds() } as u64;
        if let Err(error) = self.expire_publications(&mut slots, now) {
            drop(slots);
            self.changed.notify_all();
            return Err(error);
        }
        for slot in &mut *slots {
            if let Some(entry) = slot {
                if entry.needs_cleanup && !entry.quarantined {
                    if let Err(error) = entry.request_cleanup() {
                        entry.quarantined = true;
                        pr_err!(
                            "IHK-SMP: application cleanup retained pid={} errno={}\n",
                            entry.cleanup.pid(),
                            error.to_errno()
                        );
                    }
                }
                if entry.closed && entry.cleanup.retired() && entry.release_ready() {
                    *slot = None;
                }
            }
        }
        Ok(())
    }

    pub(crate) fn procfs_process(&self, pid: i32, cpu: i32) -> Result<Arc<ProcfsProcess>> {
        let slots = self.slots.lock();
        let entry = slots
            .iter()
            .flatten()
            .find(|entry| entry.cleanup.pid() == pid)
            .ok_or(ENOENT)?;
        let image = entry.prepare.as_ref().ok_or(EINVAL)?;
        if entry.quarantined || cpu < 0 {
            return Err(EINVAL);
        }
        kernel::error::to_result(image.result().ok_or(EBUSY)?)?;
        entry.procfs.as_ref().cloned().ok_or(EIO)
    }

    pub(crate) fn publish(
        &self,
        cpu: i32,
        send: impl FnOnce(&[u8; 128]) -> Result,
    ) -> Result<bool> {
        let mut slots = self.slots.lock();
        self.transport_health()?;
        let Some(entry) = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.next().queued() && entry.next().cpu() == cpu)
        else {
            return Ok(false);
        };
        let is_schedule = entry
            .schedule
            .as_ref()
            .is_some_and(|schedule| schedule.queued());
        let exchange = entry.next_mut();
        let packet = exchange.outgoing().ok_or(EIO)?;
        // Publication and the irreversible scheduled transition share this lock.
        send(&packet)?;
        exchange.published().map_err(errno)?;
        if is_schedule {
            entry.scheduled = true;
            pr_info!(
                "IHK-SMP: application SCHEDULE os={} generation={} pid={} cpu={}\n",
                self.owner.slot(),
                self.owner.generation(),
                entry.cleanup.pid(),
                cpu
            );
            self.changed.notify_all();
        }
        Ok(true)
    }

    pub(crate) fn reply(
        &self,
        packet: &[u8; 128],
        mut memory: impl FnMut(u64, usize) -> Result,
    ) -> Result {
        let mut slots = self.slots.lock();
        self.transport_health()?;
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        for slot in &mut *slots {
            let Some(entry) = slot.as_mut() else {
                continue;
            };
            if message == super::application_rpc::TID_DELETE {
                match entry.cleanup.accept_unscheduled_delete(packet) {
                    Ok(()) => {
                        pr_info!("IHK-SMP: application unscheduled delete os={} generation={} pid={} cpu={} tid=0 cleanup_token={}\n",
                            self.owner.slot(), self.owner.generation(), entry.cleanup.pid(),
                            entry.cleanup.cpu(), entry.key().wire());
                        if entry.closed && entry.cleanup.retired() && entry.release_ready() {
                            *slot = None;
                        }
                        return Ok(());
                    }
                    Err(-2 | -16) => continue,
                    Err(error) => return Err(errno(error)),
                }
            }
            if let Some(prepare) = entry
                .prepare
                .as_mut()
                .filter(|prepare| prepare.result().is_none())
            {
                match prepare.exchange.accept(packet) {
                    Ok(()) => {
                        let outcome = prepare.finish(&mut memory);
                        entry.quarantined =
                            prepare.exchange.result() == Some(0) && outcome.is_err();
                        pr_info!("IHK-SMP: application prepare ACK os={} generation={} pid={} token={} errno={} abandoned={} quarantined={}\n",
                            self.owner.slot(), self.owner.generation(), prepare.input.pid,
                            prepare.exchange.token().wire(), prepare.result().unwrap(),
                            prepare.exchange.abandoned() as u8, entry.quarantined as u8);
                        if entry.needs_cleanup && !entry.quarantined {
                            entry.request_cleanup()?;
                        }
                        return Ok(());
                    }
                    Err(-2 | -16) => continue,
                    Err(error) => return Err(errno(error)),
                }
            }
            if let Some(query) = &mut entry.retirement {
                match query.accept(packet) {
                    Ok(()) => {
                        let result = query.result().unwrap();
                        pr_info!("IHK-SMP: application retirement os={} generation={} pid={} token={} errno={}\n",
                            self.owner.slot(), self.owner.generation(), query.pid(), query.token().wire(), result);
                        if result == -11 {
                            // SAFETY: This reads only Linux's permanent
                            // monotonic clock while the entry remains covered
                            // by slots; the value is copied into a local retry
                            // deadline and has no application-memory lifetime.
                            entry.retirement_after =
                                unsafe { bindings::ktime_get_seconds() } as u64 + 1;
                        } else if result != 0 {
                            entry.quarantined = true;
                        }
                        if entry.closed && entry.cleanup.retired() && entry.release_ready() {
                            *slot = None;
                        }
                        return Ok(());
                    }
                    Err(-2 | -16) => continue,
                    Err(error) => return Err(errno(error)),
                }
            }
            match entry.cleanup.accept(packet) {
                Ok(()) => {
                    pr_info!("IHK-SMP: application cleanup ACK os={} generation={} pid={} token={} errno={} abandoned={}\n",
                        self.owner.slot(), self.owner.generation(), entry.cleanup.pid(), entry.key().wire(),
                        entry.cleanup.result().unwrap(), entry.cleanup.abandoned() as u8);
                    if entry.closed && entry.cleanup.retired() && entry.release_ready() {
                        *slot = None;
                    }
                    return Ok(());
                }
                Err(-2 | -16) => continue,
                Err(error) => return Err(errno(error)),
            }
        }
        Err(ENOENT)
    }

    fn close_inner(&self, token: Token) {
        let mut slots = self.slots.lock();
        abort_parent_forks(&mut slots, token, None);
        if let Some(slot) = slots
            .iter_mut()
            .find(|slot| slot.as_ref().is_some_and(|entry| entry.key() == token))
        {
            let entry = slot.as_mut().unwrap();
            if entry.quarantined {
                entry.closed = true;
                if let Some(procfs) = &entry.procfs {
                    procfs.close();
                }
                // An untrustworthy success cannot prove prepared-task retirement.
                // Retain its bounded slot until actual OS shutdown is implemented.
                return;
            }
            if entry.fork.is_none() && entry.fork_ingress.is_none() && entry.fork_prepared_parent_refs == 0 && entry.syscalls.drained()
                && entry.procfs.as_ref().is_none_or(|procfs| procfs.drained())
                && (entry.prepare.is_none() && entry.cleanup.reserved() || entry.release_ready())
            {
                *slot = None;
            } else {
                entry.closed = true;
                entry.cleanup.abandon();
                if let Some(prepare) = &mut entry.prepare {
                    prepare.exchange.abandon();
                }
                let _ = entry.request_cleanup();
            }
        }
    }

    pub(crate) fn close(&self, token: Token) {
        self.close_inner(token);
        self.changed.notify_all();
    }

    pub(crate) fn syscall_request(
        &self,
        request: Request,
        claim: impl FnOnce(&Request) -> Result<SyscallResponse>,
    ) -> Result {
        if PagerOperation::is_release(&request) {
            let slots = self.slots.lock();
            self.transport_health()?;
            // A shared file object can outlive the original PID. This exact-OS
            // response queue owns no launcher/MM and is pumped independently.
            let result = self
                .releases
                .lock()
                .admit_serviced(
                    request,
                    |request| claim(request).map_err(|error| error.to_errno()),
                    |request| {
                        let PagerOperation::Release { handle, references } =
                            PagerOperation::decode(request).unwrap()
                        else {
                            unreachable!()
                        };
                        self.pagers
                            .release(handle, references)
                            .unwrap_or_else(|error| error.to_errno() as i64)
                    },
                )
                .map(|_| ())
                .map_err(errno);
            drop(slots);
            self.changed.notify_all();
            return result;
        }
        let result = (|| {
            let mut slots = self.slots.lock();
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.cleanup.pid() == request.pid())
                .ok_or(ENOENT)?;
            if !entry.scheduled || entry.quarantined {
                return Err(EINVAL);
            }
            let result = entry
                .syscalls
                .admit(request, |request| claim(request).map_err(|e| e.to_errno()));
            if let Err(error) = result {
                if error != -11 {
                    entry.quarantined = true;
                }
                return Err(errno(error));
            }
            Ok(())
        })();
        self.changed.notify_all();
        result
    }

    pub(crate) fn syscall_cpu(&self) -> Option<(Token, i32)> {
        if self.transport_health().is_err() {
            return None;
        }
        let start = self.syscall_cursor.fetch_add(1, Ordering::Relaxed);
        if start % 2 == 0 {
            if let Some(cpu) = self.releases.lock().queued_cpu() {
                return Some((self.release_token, cpu));
            }
        }
        let slots = self.slots.lock();
        let application =
            super::smp_application_syscall::cyclic(start, slots.len()).find_map(|index| {
                let entry = slots[index].as_ref()?;
                entry.syscalls.queued_cpu().map(|cpu| (entry.key(), cpu))
            });
        drop(slots);
        application.or_else(|| {
            self.releases
                .lock()
                .queued_cpu()
                .map(|cpu| (self.release_token, cpu))
        })
    }

    pub(crate) fn publish_syscall(
        &self,
        token: Token,
        cpu: i32,
        send: impl FnOnce(&[u8; 128]) -> Result,
        notify: impl FnOnce() -> Result,
    ) -> Result<bool> {
        let mut slots = self.slots.lock();
        self.transport_health()?;
        if token == self.release_token {
            let result = self
                .releases
                .lock()
                .publish(cpu, |packet| send(packet).map_err(|error| error.to_errno()))
                .map_err(errno);
            return self.finish_publication(&mut slots, result, notify);
        }
        if fork_publication_frozen(&slots, token, cpu)
            || fork_link::publication_frozen(&mut slots, token, cpu)
        { return Ok(false); }
        let Some(entry) = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
        else {
            return Ok(false);
        };
        let result = entry
            .syscalls
            .publish(cpu, |packet| send(packet).map_err(|e| e.to_errno()))
            .map_err(errno);
        if matches!(&result, Ok(true)) {
            observe_fork_publication(&mut slots, token);
            fork_link::observe_publication(&mut slots, token);
        }
        // `send` above means only queue publication. Notification runs after
        // the response has released its memory, but under the same application
        // mutex as RET completion. Its error must never retry that publication.
        let published = self.finish_publication(&mut slots, result, notify)?;
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        if entry.needs_cleanup && entry.syscalls.drained() && !entry.quarantined {
            if let Err(error) = entry.request_cleanup() {
                entry.quarantined = true;
                pr_err!(
                    "IHK-SMP: syscall drain retained application pid={} cleanup_errno={}\n",
                    entry.cleanup.pid(),
                    error.to_errno()
                );
                // Publication and notification already happened. A following
                // cleanup failure cannot cause another syscall publication.
            }
        }
        Ok(published)
    }

    fn transport_health(&self) -> Result {
        let error = self.transport_error.load(Ordering::Acquire);
        if error == 0 {
            Ok(())
        } else {
            Err(errno(error))
        }
    }

    fn expire_publications(&self, slots: &mut [Option<Entry>], now: u64) -> Result {
        let expired = slots.iter_mut().flatten().any(|entry| {
            entry
                .syscalls
                .publication_expired(now, PUBLICATION_TIMEOUT_SECONDS)
        }) || self
            .releases
            .lock()
            .publication_expired(now, PUBLICATION_TIMEOUT_SECONDS);
        if expired {
            pr_err!("IHK-SMP: application transport failure os={} generation={} phase=publication_timeout errno=-110\n",
                self.owner.slot(), self.owner.generation());
            self.quarantine_transport(slots, errno(-110));
            return Err(errno(-110));
        }
        Ok(())
    }

    /// Caller holds slots; all publication, failure and admission decisions
    /// share that mutex. No guest bytes or cancellation responses are written.
    fn quarantine_transport(&self, slots: &mut [Option<Entry>], error: Error) {
        if self
            .transport_error
            .compare_exchange(0, error.to_errno(), Ordering::AcqRel, Ordering::Acquire)
            .is_err()
        {
            return;
        }
        for entry in slots.iter_mut().flatten() {
            entry.quarantined = true;
            entry.needs_cleanup = true;
            entry.syscalls.quarantine();
            if let Some(procfs) = &entry.procfs {
                procfs.close();
            }
        }
        self.releases.lock().quarantine();
    }

    /// A hard target/channel error before entering publication follows the
    /// same terminal transition. Wake after releasing all publication locks.
    pub(crate) fn fail_transport(&self, error: Error) {
        let mut slots = self.slots.lock();
        self.quarantine_transport(&mut slots, error);
        drop(slots);
        self.changed.notify_all();
    }

    /// Record a continuing-service failure at the same admission boundary as
    /// transport quarantine. The referenced error belongs to our retained
    /// Runtime. Callers hold none of the application/publication locks.
    pub(crate) fn fail_service(&self, service_error: &AtomicI32, error: Error) -> bool {
        let mut slots = self.slots.lock();
        let first = service_error.compare_exchange(
            0,
            error.to_errno(),
            Ordering::AcqRel,
            Ordering::Acquire,
        );
        let recorded = first.err().unwrap_or(error.to_errno());
        self.quarantine_transport(&mut slots, errno(recorded));
        drop(slots);
        self.changed.notify_all();
        first.is_ok()
    }

    fn finish_publication(
        &self,
        slots: &mut [Option<Entry>],
        published: Result<bool>,
        notify: impl FnOnce() -> Result,
    ) -> Result<bool> {
        match published {
            Ok(true) => match notify() {
                Ok(()) => Ok(true),
                Err(error) => {
                    pr_err!("IHK-SMP: application transport failure os={} generation={} phase=postpublication_notify errno={}\n",
                        self.owner.slot(), self.owner.generation(), error.to_errno());
                    self.quarantine_transport(slots, error);
                    Err(error)
                }
            },
            Ok(false) => Ok(false),
            Err(error) if error == EBUSY || error == EAGAIN => Ok(false),
            Err(error) => {
                pr_err!("IHK-SMP: application transport failure os={} generation={} phase=prepublication errno={}\n",
                    self.owner.slot(), self.owner.generation(), error.to_errno());
                self.quarantine_transport(slots, error);
                Err(error)
            }
        }
    }

    pub(crate) fn notify_syscalls(&self) {
        self.changed.notify_all();
    }

    pub(crate) fn worker(&self, token: Token, bytes: &mut [u8], open: bool) -> Result {
        if bytes.len() != 16 {
            return Err(EINVAL);
        }
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        if open {
            if entry.closed || entry.needs_cleanup || entry.quarantined || entry.fork_ingress.is_some() {
                return Err(EBUSY);
            }
            if let Some(prepare) = entry.prepare.as_ref() {
                kernel::error::to_result(prepare.result().ok_or(EBUSY)?)?;
            } else if !entry.scheduled || !entry.fork.as_ref().is_some_and(|fork|
                fork.reservation.state.phase() == ForkPhase::Linked)
            { return Err(EINVAL); }
            let tid = i64::from_le_bytes(bytes[..8].try_into().unwrap());
            let tid = i32::try_from(tid).map_err(|_| EINVAL)?;
            let worker = entry.syscalls.open_worker(tid).map_err(errno)?;
            bytes[8..16].copy_from_slice(&worker.to_le_bytes());
            Ok(())
        } else {
            let worker = u64::from_le_bytes(bytes[..8].try_into().unwrap());
            let result = entry.syscalls.close_worker(worker);
            entry.quarantined |= entry.syscalls.quarantined();
            if result.is_ok() || result == Err(-16) {
                abort_parent_forks(&mut slots, token, Some(worker));
            }
            result.map_err(errno)
        }
    }

    pub(crate) fn wait_syscall(&self, token: Token, bytes: &mut [u8]) -> Result {
        if bytes.len() != 96 {
            return Err(EINVAL);
        }
        let worker = u64::from_le_bytes(bytes[..8].try_into().unwrap());
        let mut slots = self.slots.lock();
        loop {
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.closed || entry.needs_cleanup || entry.quarantined || entry.fork_ingress.is_some() {
                return Err(errno(-32));
            }
            if kernel::current!().signal_pending() {
                return Err(EINTR);
            }
            if let Some((serial, output)) = entry.syscalls.reserve(worker).map_err(errno)? {
                bytes[8..16].copy_from_slice(&serial.to_le_bytes());
                bytes[16..96].copy_from_slice(&output);
                return Ok(());
            }
            // Linux queues the waiter before releasing this exact mutex. No
            // transport, OS operation or user-copy lock is held by the caller.
            if self.changed.wait_interruptible(&mut slots) {
                return Err(EINTR);
            }
        }
    }

    pub(crate) fn copied_syscall(&self, token: Token, bytes: &[u8]) -> Result {
        if bytes.len() != 24 {
            return Err(EINVAL);
        }
        let word = |offset| u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        let success = word(16);
        if success > 1 {
            return Err(EINVAL);
        }
        let result = {
            let mut slots = self.slots.lock();
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            entry
                .syscalls
                .copied(word(0), word(8), success != 0)
                .map_err(errno)
        };
        self.changed.notify_all();
        result
    }

    pub(crate) fn transfer_tids(&self, token: Token, bytes: &mut [u8]) -> Result {
        if bytes.len() <= 32 || bytes.len() - 32 > super::application_image::MAX_FLAT_BYTES {
            return Err(EINVAL);
        }
        let word = |offset| u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        let (worker, serial, physical, direction) = (word(0), word(8), word(16), word(24));
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        entry
            .syscalls
            .transfer_tids(
                worker,
                serial,
                physical,
                &mut bytes[32..],
                direction,
                |request, memory, data| {
                    memory
                        .copy_tids(request, data)
                        .map_err(|error| error.to_errno())
                },
            )
            .map_err(errno)?;
        pr_info!("application_tids=transferred os={} generation={} pid={} worker={} delivery={} physical={:x} bytes={}\n",
            self.owner.slot(), self.owner.generation(), entry.cleanup.pid(), worker, serial, physical, bytes.len() - 32);
        Ok(())
    }

    pub(crate) fn clear_syscall(&self, token: Token, bytes: &mut [u8], finish: bool) -> Result {
        if bytes.len() != 40 {
            return Err(EINVAL);
        }
        let worker = u64::from_le_bytes(bytes[..8].try_into().unwrap());
        let serial = u64::from_le_bytes(bytes[8..16].try_into().unwrap());
        let value = i64::from_le_bytes(bytes[24..32].try_into().unwrap());
        bytes[16..].fill(0);
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        if !finish {
            let (start, end) = entry
                .syscalls
                .begin_invalidation(worker, serial)
                .map_err(errno)?;
            bytes[16..24].copy_from_slice(&1u64.to_le_bytes());
            bytes[24..32].copy_from_slice(&start.to_le_bytes());
            bytes[32..40].copy_from_slice(&end.to_le_bytes());
            return Ok(());
        }
        let outcome = entry.syscalls.finish_invalidation(worker, serial, value);
        entry.quarantined |= entry.syscalls.quarantined();
        let completed = outcome.map_err(errno)?;
        bytes[16..24].copy_from_slice(&1u64.to_le_bytes());
        bytes[24..32].copy_from_slice(&completed.to_le_bytes());
        pr_info!("host_mapping=invalidated os={} generation={} pid={} worker={} delivery={} value={} completed={}\n",
            self.owner.slot(), self.owner.generation(), entry.cleanup.pid(), worker, serial, value, completed);
        loop {
            let entry = slots
                .iter()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.syscalls.returned(worker, serial).map_err(errno)? {
                return Ok(());
            }
            if self.changed.wait_interruptible(&mut slots) {
                return Err(EINTR);
            }
        }
    }

    pub(crate) fn pager_syscall(&self, token: Token, bytes: &mut [u8]) -> Result {
        if bytes.len() != 32 {
            return Err(EINVAL);
        }
        let worker = u64::from_le_bytes(bytes[..8].try_into().unwrap());
        let serial = u64::from_le_bytes(bytes[8..16].try_into().unwrap());
        bytes[16..].fill(0);
        let request = {
            let mut slots = self.slots.lock();
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            entry.syscalls.begin_kernel(worker, serial).map_err(errno)?
        };
        bytes[16..24].copy_from_slice(&1u64.to_le_bytes());
        enum Work {
            Create(PagerFile),
            Value(i64),
        }
        let outcome = (|| -> Result<Work> {
            let operation = PagerOperation::decode(&request).map_err(errno)?;
            self.with_pager_memory(token, worker, serial, |request, memory| {
                memory.prepare_pager(request)
            })?;
            match operation {
                PagerOperation::Create { fd, .. } => PagerFile::open(fd).map(Work::Create),
                PagerOperation::Io {
                    write,
                    handle,
                    offset,
                    bytes,
                    ..
                } => self
                    .pagers
                    .io(write, handle, offset, bytes, |offset, data, to_guest| {
                        self.with_pager_memory(token, worker, serial, |_, memory| {
                            memory.pager_copy(offset, data, to_guest)
                        })
                    })
                    .map(Work::Value),
                PagerOperation::Release { .. } => Err(EINVAL), // Owned by continuing ingress.
            }
        })();
        let mut value = -512i64;
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        let finished = entry.syscalls.finish_kernel(worker, serial, |_, memory| {
            let result = match outcome {
                Ok(Work::Create(prepared)) => self
                    .pagers
                    .create(prepared, |data| memory.pager_copy(0, data, true)),
                Ok(Work::Value(value)) => Ok(value),
                Err(error) => Err(error),
            };
            value = result.unwrap_or_else(|error| error.to_errno() as i64);
            Ok(value)
        });
        entry.quarantined |= entry.syscalls.quarantined();
        finished.map_err(errno)?;
        bytes[24..32].copy_from_slice(&value.to_le_bytes());
        pr_info!("file_pager=completed os={} generation={} pid={} worker={} delivery={} operation={} value={}\n",
            self.owner.slot(), self.owner.generation(), request.pid(), worker, serial, request.arguments()[0], value);
        loop {
            let entry = slots
                .iter()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.syscalls.returned(worker, serial).map_err(errno)? {
                return Ok(());
            }
            if self.changed.wait_interruptible(&mut slots) {
                return Err(EINTR);
            }
        }
    }

    fn with_pager_memory<T>(
        &self,
        token: Token,
        worker: u64,
        serial: u64,
        operation: impl FnOnce(&Request, &mut SyscallResponse) -> Result<T>,
    ) -> Result<T> {
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        entry
            .syscalls
            .with_kernel_memory(worker, serial, |request, memory| {
                operation(request, memory).map_err(|error| error.to_errno())
            })
            .map_err(errno)
    }

    pub(crate) fn return_syscall(
        &self,
        token: Token,
        bytes: &mut [u8],
        copy: impl FnOnce(&Request, u64, &mut [u8]) -> Result,
    ) -> Result {
        if bytes.len() != 72 {
            return Err(EINVAL);
        }
        let word = |offset| u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        let (worker, serial, cpu, value, destination, length) = (
            word(0),
            word(8),
            word(16) as i64,
            word(24) as i64,
            word(32),
            word(40),
        );
        if length > 16 {
            return Err(EINVAL);
        }
        bytes[48..56].fill(0); // Output: whether the continuing owner accepted the return.
        let mut slots = self.slots.lock();
        authorize_fork_return(&slots, token, worker, serial, cpu, value)?;
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        let result = entry
            .syscalls
            .return_value(worker, serial, cpu, value, |request| {
                if length == 0 {
                    return Ok(());
                }
                copy(request, destination, &mut bytes[56..56 + length as usize])
                    .map_err(|e| e.to_errno())
            });
        entry.quarantined |= entry.syscalls.quarantined();
        result.map_err(errno)?;
        record_fork_return(&mut slots, token, worker, serial, value);
        bytes[48..56].copy_from_slice(&1u64.to_le_bytes());
        loop {
            let entry = slots
                .iter()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.quarantined {
                return Err(errno(-71));
            }
            if entry.syscalls.returned(worker, serial).map_err(errno)? {
                return Ok(());
            }
            // The return is committed: complete its real publication before
            // exposing success to the launcher. A signal cannot cancel or
            // replay that result. The continuing owner still handles errors,
            // quarantine and wake publication; ordinary WAIT is interruptible.
            self.changed.wait(&mut slots);
        }
    }

    pub(crate) fn prepare(
        &self,
        token: Token,
        bytes: &mut [u8],
        cpus: usize,
        direct_map: u64,
    ) -> Result {
        // All allocations and input validation finish outside the state lock.
        let mut prepare = Preparation::new(self.owner.slot() as i32, bytes, cpus, direct_map)?;
        let (uid, gid) = prepare.procfs_credentials()?;
        let procfs = ProcfsProcess::new(
            self.procfs.clone(),
            token,
            prepare.input.pid,
            prepare.input.cpu,
            uid,
            gid,
        )?;
        {
            let mut slots = self.slots.lock();
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.closed
                || entry.needs_cleanup
                || entry.quarantined
                || entry.prepare.is_some()
                || entry.fork_ingress.is_some()
                || !entry.cleanup.reserved()
            {
                return Err(EBUSY);
            }
            if prepare.input.pid != entry.cleanup.pid() {
                return Err(EINVAL);
            }
            prepare.exchange.begin().map_err(errno)?;
            entry.procfs = Some(procfs);
            entry.prepare = Some(prepare);
        }
        for _ in 0..3000 {
            {
                let slots = self.slots.lock();
                let entry = slots
                    .iter()
                    .flatten()
                    .find(|entry| entry.key() == token)
                    .ok_or(ENOENT)?;
                let prepare = entry.prepare.as_ref().ok_or(EIO)?;
                if entry.quarantined {
                    return Err(errno(-71));
                }
                if prepare.result().is_some() {
                    return prepare.copy_result(bytes);
                }
            }
            // SAFETY: Called only from the launcher's sleepable ioctl context.
            unsafe { bindings::msleep(10) };
        }
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        if entry.quarantined {
            return Err(errno(-71));
        }
        let prepare = entry.prepare.as_mut().ok_or(EIO)?;
        // Resolve the completion/timeout race while holding the same reply lock.
        if prepare.result().is_some() {
            return prepare.copy_result(bytes);
        }
        prepare.exchange.abandon();
        entry.request_cleanup()?;
        Err(errno(-110))
    }

    pub(crate) fn start(&self, token: Token, bytes: &[u8]) -> Result {
        let mut slots = self.slots.lock();
        {
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.closed || entry.needs_cleanup || entry.quarantined || entry.fork_ingress.is_some() || entry.schedule.is_some()
            {
                return Err(EBUSY);
            }
            let image = entry.prepare.as_ref().ok_or(EINVAL)?;
            image.authorize_start(bytes)?;
            let mut schedule = Exchange::schedule(
                self.owner.slot() as i32,
                image.input.cpu,
                image.input.pid,
                image.thread,
            )
            .map_err(errno)?;
            schedule.begin().map_err(errno)?;
            entry.schedule = Some(schedule);
        }
        loop {
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.scheduled {
                return Ok(());
            }
            if entry.needs_cleanup || entry.closed || entry.quarantined {
                return Err(EBUSY);
            }
            if self.changed.wait_interruptible(&mut slots) {
                let entry = slots
                    .iter_mut()
                    .flatten()
                    .find(|entry| entry.key() == token)
                    .ok_or(ENOENT)?;
                if entry.scheduled {
                    return Ok(());
                }
                // The same mutex excludes publication while cancelling queued work.
                entry.schedule = None;
                entry.request_cleanup()?;
                return Err(EINTR);
            }
        }
    }

    pub(crate) fn with_prepared<T>(
        &self,
        token: Token,
        use_image: impl FnOnce(&Preparation) -> Result<T>,
    ) -> Result<T> {
        let slots = self.slots.lock();
        let entry = slots
            .iter()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        if entry.needs_cleanup || entry.closed || entry.quarantined || entry.fork_ingress.is_some() {
            return Err(EBUSY);
        }
        let prepare = entry.prepare.as_ref().ok_or(EINVAL)?;
        kernel::error::to_result(prepare.result().ok_or(EBUSY)?)?;
        use_image(prepare)
    }

    pub(crate) fn cleanup(&self, token: Token) -> Result {
        {
            let mut slots = self.slots.lock();
            abort_parent_forks(&mut slots, token, None);
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            let result = entry.request_cleanup();
            drop(slots);
            self.changed.notify_all();
            result?;
        }
        // The independent packet worker continues past a departing waiter.
        for _ in 0..500 {
            {
                let mut slots = self.slots.lock();
                let slot = slots
                    .iter_mut()
                    .find(|slot| slot.as_ref().is_some_and(|entry| entry.key() == token))
                    .ok_or(ENOENT)?;
                let entry = slot.as_ref().unwrap();
                if entry.quarantined {
                    return Err(errno(-71));
                }
                if entry.release_ready() {
                    let error = entry.cleanup.result().unwrap();
                    *slot = None;
                    return kernel::error::to_result(error).map(|_| ());
                }
            }
            // SAFETY: Called only from sleepable application-owner release.
            unsafe { bindings::msleep(10) };
        }
        self.close(token);
        Err(errno(-110))
    }
}

// These internal entrypoints deliberately have no application-invoke opcode or
// mcctrl caller yet. CREATE_PPD remains closed until the VMA transaction and
// pre-destruction revoke/final-ACK proofs are separately implemented.
#[allow(dead_code)]
impl Remote {
    pub(crate) fn prepare_fork(self: &Arc<Self>, parent: Token, child: Token, geometry: ForkGeometry) -> Result<PreparedForkLease> {
        let child_owner = Arc::new(ForkChildOwner::current()?, GFP_KERNEL)?;
        let seal = Arc::new(PreparedForkSeal { sealed: AtomicBool::new(false) }, GFP_KERNEL)?;
        let mut slots = self.slots.lock();
        self.transport_health()?;
        let (token, identity) = reserve_fork_in_slots(self.owner, &mut slots, parent, child, child_owner, geometry, seal.clone())?;
        Ok(PreparedForkLease { remote: Some(self.clone()), seal, child, token, identity })
    }

    pub(crate) fn abort_fork(&self, child: Token, token: u64) -> Result {
        let mut slots = self.slots.lock();
        abort_fork_in_slots(&mut slots, child, token)
    }
}

// BEGIN PRIVATE FORK BACKEND PROGRESS
// This completion boundary covers ONLY the original unpublished first RET.
// Running/second-link teardown requires its separately authenticated protocol.
fn fork_progress_in_slots(
    owner: OsToken, slots: &mut [Option<Entry>], child: Token,
    identity: ForkIdentity, stage: u32,
) -> Result<(Option<usize>, usize)> {
    use super::application_abi::{FORK_HOST_REVOKED_V1, FORK_GUEST_DESTROYED_V1};
    if identity.slot != owner.slot() || identity.generation != owner.generation()
        || identity.child != child.wire()
    { return Err(EACCES); }
    let child_index = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key() == child)).ok_or(ENOENT)?;
    let entry = slots[child_index].as_mut().unwrap();
    let fork = entry.fork.as_mut().ok_or(ENOENT)?;
    if fork.reservation.identity != identity || fork.owner.number != entry.cleanup.pid()
        || fork.owner.mm.as_ptr() as usize != identity.child_mm
        || !fork.seal.sealed.load(Ordering::Acquire)
    { return Err(EACCES); }
    if stage == FORK_HOST_REVOKED_V1 {
        // A sealed LINK grants irreversible same-kind2 handoff permission.
        // Host abort cannot alter that phase or close admissions afterwards.
        if let Some(link) = &fork.link { link.cancel_if_open()?; }
        // Close ACTUAL existing service admission before drain. Every current
        // prepare/start/worker/wait/with_prepared path observes this gate under
        // the same slots mutex. No child image was prepared or scheduled at
        // this original-first-RET boundary; foreign active state fails closed.
        entry.needs_cleanup = true;
        if fork.reservation.state.phase() != ForkPhase::Quarantined {
            fork.reservation.state.request_abort(identity)?;
        }
        entry.syscalls.close().map_err(errno)?;
    } else if stage != FORK_GUEST_DESTROYED_V1 { return Err(EINVAL); }
    if !entry.needs_cleanup || entry.scheduled || entry.prepare.is_some()
        || entry.procfs.is_some() || !entry.syscalls.drained()
    { return Err(EBUSY); }
    fork.reservation.state.revoke_drained(identity)?;
    let first = fork.reservation.first.clone();
    let value = fork.reservation.return_value;
    let published = fork.reservation.return_published;
    if stage == FORK_GUEST_DESTROYED_V1 {
        fork.reservation.state.permit_guest_destroy(identity)?;
        if !published || value != Some(super::application_abi::FORK_ABORT_RETURN_V1) { return Err(EBUSY); }
        // Publication retained the authenticated full child key and terminal
        // value. The parent's normally retired mailbox is no longer needed.
        return Ok((None, child_index));
    } else if published { return Err(EBUSY); }
    let parent_index = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key().wire() == identity.parent)).ok_or(ENOENT)?;
    if stage == FORK_HOST_REVOKED_V1 {
        // Establish exact response ownership/unpublished state BEFORE any MM
        // callback. AbortRequested/Quarantined freezes all its publication.
        slots[parent_index].as_mut().unwrap().syscalls.check_fork_abort(
            identity.worker, identity.delivery, &first, value,
        ).map_err(errno)?;
    }
    Ok((Some(parent_index), child_index))
}

#[allow(dead_code)]
impl Remote {
    pub(crate) fn begin_fork_progress(&self, child: Token, identity: ForkIdentity, stage: u32) -> Result {
        let mut slots = self.slots.lock();
        fork_progress_in_slots(self.owner, &mut slots, child, identity, stage)?;
        Ok(())
    }

    /// # Safety
    /// A module-pinned, typed verifier just established the requested actual
    /// alias/TLB or authenticated final in-band destructor proof for this key.
    /// No verifier/callback/borrowed pointer escapes into Remote state.
    pub(crate) unsafe fn finish_fork_progress(&self, child: Token, identity: ForkIdentity, stage: u32) -> Result {
        use super::application_abi::{FORK_HOST_REVOKED_V1, FORK_ABORT_RETURN_V1};
        let mut slots = self.slots.lock();
        let (parent_index, child_index) = fork_progress_in_slots(self.owner, &mut slots, child, identity, stage)?;
        if stage == FORK_HOST_REVOKED_V1 {
            let parent_index = parent_index.ok_or(EIO)?;
            let record = &slots[child_index].as_ref().unwrap().fork.as_ref().unwrap().reservation;
            let first = record.first.clone();
            let value = record.return_value;
            slots[parent_index].as_mut().unwrap().syscalls.reconcile_fork_abort(
                identity.worker, identity.delivery, &first, value,
            ).map_err(errno)?;
            let record = &mut slots[child_index].as_mut().unwrap().fork.as_mut().unwrap().reservation;
            // One publication lock atomically commits the terminal negative
            // metadata and its permission. No stale positive can pass between.
            record.return_value = Some(FORK_ABORT_RETURN_V1);
            if record.state.phase() == ForkPhase::Quarantined {
                unsafe { record.state.reconciled_quarantined_host_revoke(identity) }?;
            } else {
                unsafe { record.state.host_revoked(identity, 0) }?;
            }
            drop(slots);
            return Ok(());
        }
        let record = &mut slots[child_index].as_mut().unwrap().fork.as_mut().unwrap().reservation;
        unsafe { record.state.guest_destroyed(identity) }?;
        record.state.acknowledge_destroyed(identity)?;
        // Exact final proof retires this never-scheduled reservation itself;
        // ordinary CLEANUP must not send another destructor for the same child.
        let retired = slots[child_index].take();
        drop(slots);
        // Structural PID/MM and retained Remote cycles drop outside all locks.
        drop(retired);
        Ok(())
    }
}
// END PRIVATE FORK BACKEND PROGRESS
