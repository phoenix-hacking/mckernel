// SPDX-License-Identifier: GPL-2.0
//! Authentic private first-clone ingress. Parent smp_application owns lifecycle
//! and publication hooks; IHK owns the payload allocation and all outer pins.
use super::*;
use super::super::{
    application_abi::{ForkPayloadScopeV1, VERSION},
    smp_application_syscall::ForkIngressResponse,
    smp_memory::{ForkPayload, ForkPayloadSeed, fork_payload_construct,
        fork_payload_abort, fork_payload_complete},
};
use core::ffi::c_void;

const CARRIER_MARKER: u64 = 0x313030434b46434d;
type ResponseTicket = ForkIngressResponse<SyscallResponse>;
unsafe extern "C" {
    fn ihk_os_application_abort_fork_payload_v1(scope: *mut ForkPayloadScopeV1) -> i32;
    fn ihk_os_application_ready_fork_payload_v1(scope: *mut ForkPayloadScopeV1) -> i32;
}

/// Provisional publication ownership, never a host identity or adoption proof.
/// It is installed before the SAME response leaves its actual delivered Call.
/// Uncertain paths retain the typed ticket/lease and Remote in this exact slot.
pub(super) struct ForkIngressMarker {
    parent: Token,
    child: Token,
    token: Token,
    worker: u64,
    serial: u64,
    cpu: i32,
    request: Request,
    child_owner: Arc<ForkChildOwner>,
    seal: Arc<PreparedForkSeal>,
    cancelled: bool,
    retained_ticket: Option<ResponseTicket>,
    retained_lease: Option<PreparedForkLease>,
    _retained_remote: Option<Arc<Remote>>,
}
impl ForkIngressMarker {
    pub(super) fn cancel(&mut self) { self.cancelled = true; }
    fn exact(&self, parent: Token, child: Token, token: Token) -> bool {
        self.parent == parent && self.child == child && self.token == token
    }
}
impl Drop for ForkIngressMarker {
    fn drop(&mut self) {
        // Entry removal is forbidden while this marker or its parent pin is
        // live. A retained cycle is recoverable storage, not an orphaned ticket.
        assert!(self.retained_ticket.is_none() && self.retained_lease.is_none(),
            "dropping an unresolved actual fork ingress owner");
    }
}
pub(super) fn abort_parent_ingress(slots: &mut [Option<Entry>], parent: Token, worker: Option<u64>) {
    for marker in slots.iter_mut().flatten().filter_map(|entry| entry.fork_ingress.as_mut()) {
        if marker.parent == parent && worker.is_none_or(|value| value == marker.worker) { marker.cancel(); }
    }
}
pub(super) fn publication_frozen(slots: &[Option<Entry>], parent: Token, cpu: i32) -> bool {
    slots.iter().flatten().filter_map(|entry| entry.fork_ingress.as_ref())
        .any(|marker| marker.parent == parent && marker.cpu == cpu)
}

fn indexes(slots: &[Option<Entry>], parent: Token, child: Token) -> Result<(usize, usize)> {
    if parent == child { return Err(EINVAL); }
    let parent_index = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key() == parent)).ok_or(ENOENT)?;
    let child_index = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key() == child)).ok_or(ENOENT)?;
    Ok((parent_index, child_index))
}
fn current_entries(owner: OsToken, slots: &[Option<Entry>], parent_index: usize,
    child_index: usize, child_owner: &ForkChildOwner) -> Result
{
    let p = slots[parent_index].as_ref().ok_or(ENOENT)?;
    let c = slots[child_index].as_ref().ok_or(ENOENT)?;
    if p.closed || p.needs_cleanup || p.quarantined || !p.scheduled
        || c.closed || c.needs_cleanup || c.quarantined || c.scheduled || c.prepare.is_some()
        || c.fork.is_some() || c.cleanup.pid() != child_owner.number { return Err(EBUSY); }
    if p.owner_slot != owner.slot() as i32 || c.owner_slot != owner.slot() as i32
        || p.owner_generation != owner.generation() || c.owner_generation != owner.generation()
    { return Err(EACCES); }
    Ok(())
}
fn scope_metadata(owner: OsToken, scope: &ForkPayloadScopeV1) -> Result {
    if scope.version != VERSION || scope.bytes as usize != core::mem::size_of::<ForkPayloadScopeV1>()
        || scope.slot != owner.slot() || scope.reserved0 != 0 || scope.generation != owner.generation()
        || scope.epoch == 0 || scope.context.is_null() || scope.attach.is_none() { return Err(EACCES); }
    // Metadata is not authority. The actual IHK attach validates its exact live
    // stack/initializing epoch/owner before it invokes the first payload read.
    Ok(())
}
fn quarantine_provisional(remote: &Arc<Remote>, parent: Token, child: Token, token: Token,
    ticket: ResponseTicket)
{
    let mut slots = remote.slots.lock();
    let entry = slots.iter_mut().flatten().find(|entry| entry.key() == child)
        .expect("pinned ingress child disappeared");
    let marker = entry.fork_ingress.as_mut().expect("pinned ingress marker disappeared");
    assert!(marker.exact(parent, child, token) && marker.retained_ticket.is_none());
    marker.cancelled = true;
    marker.retained_ticket = Some(ticket);
    marker._retained_remote = Some(remote.clone());
    entry.quarantined = true;
}

/// Restore first, while the SAME marker and parent hold still prohibit every
/// matching RET. Only after successful restore may real IHK Abort remove the
/// independent payload claim. This avoids losing default IHK uncertainty on a
/// response-restore failure after Abort had already declared rollback ready.
unsafe fn rollback_provisional(remote: &Arc<Remote>, parent: Token, child: Token,
    token: Token, mut ticket: ResponseTicket, scope: *mut ForkPayloadScopeV1) -> Result
{
    let restored = {
        let mut slots = remote.slots.lock();
        // These are structural invariants established before the ticket left
        // the Call, not ordinary cleanup failures. Returning here would drop
        // the only typed response owner before quarantine can retain it.
        let (pi, ci) = indexes(&slots, parent, child).expect("pinned ingress entries disappeared before restore");
        let marker = slots[ci].as_ref().and_then(|entry| entry.fork_ingress.as_ref())
            .expect("pinned ingress marker disappeared before restore");
        assert!(marker.exact(parent, child, token)
            && slots[pi].as_ref().unwrap().fork_prepared_parent_refs != 0,
            "pinned ingress ownership changed before restore");
        slots[pi].as_mut().unwrap().syscalls.restore_fork_ingress_response(&mut ticket).map_err(errno)
    };
    if let Err(error) = restored {
        quarantine_provisional(remote, parent, child, token, ticket);
        return Err(error);
    }
    // No payload borrow remains here, and no Remote/MM/IHK guard spans Abort.
    let status = unsafe { ihk_os_application_abort_fork_payload_v1(scope) };
    if status != 0 {
        quarantine_provisional(remote, parent, child, token, ticket);
        return Err(errno(if (-4095..0).contains(&status) { status } else { -71 }));
    }
    let removed = {
        let mut slots = remote.slots.lock();
        // All removal/reuse gates and the parent pin were proved BEFORE Abort.
        // They cannot disappear while this exact provisional marker is live.
        let (pi, ci) = indexes(&slots, parent, child).expect("proven ingress entries disappeared after Abort");
        let exact = slots[ci].as_ref().and_then(|entry| entry.fork_ingress.as_ref())
            .is_some_and(|marker| marker.exact(parent, child, token));
        assert!(exact, "proven ingress marker changed after Abort");
        let p = slots[pi].as_mut().unwrap();
        p.fork_prepared_parent_refs = p.fork_prepared_parent_refs.checked_sub(1)
            .expect("proven ingress parent pin disappeared after Abort");
        slots[ci].as_mut().unwrap().fork_ingress.take()
    };
    drop(removed); // MM/PID/Arc destruction occurs outside slots.
    Ok(())
}

/// Owned lease plus one synchronous IHK payload borrow. Neither the scope nor
/// payload/ABI pointers may escape this registered callback. Successful finish
/// first makes the real IHK pending owner visible, then atomically commits the
/// canonical first receipt under the SAME backend slots exclusion before RET.
#[must_use]
pub(crate) struct PreparedForkCarrier<'scope> {
    lease: Option<PreparedForkLease>,
    payload: Option<NonNull<ForkPayload>>,
    scope: &'scope ForkPayloadScopeV1,
    recovery: Option<ForkIngressMarker>,
}
impl PreparedForkCarrier<'_> {
    pub(crate) fn borrow_seal(&mut self) -> PreparedForkBorrow<'_> {
        self.lease.as_mut().expect("consumed fork carrier").borrow_seal()
    }
    pub(crate) fn finish(mut self) -> Result {
        // The real MM callback and every local guard have returned. The actual
        // IHK scope rechecks its observed seal/epoch/capsule, outside slots.
        let status = unsafe { ihk_os_application_ready_fork_payload_v1(ptr::from_ref(self.scope).cast_mut()) };
        if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
        let payload = self.payload.take().ok_or(EIO)?;
        // SAFETY: IHK still owns this exact capsule. Checked finish creates
        // its exclusive reference ONLY under slots and ends that reference
        // before unlocking. No reference argument spans return from that call:
        // an immediate LINK may then borrow the same payload. Neither this
        // function nor Drop dereferences the pointer; successful finish disarms
        // the lease, so Drop cannot run cleanup.
        unsafe { self.lease.as_mut().ok_or(EIO)?.finish_with_payload(payload) }
    }
}
impl Drop for PreparedForkCarrier<'_> {
    fn drop(&mut self) {
        self.payload.take(); // Clear ALL borrowed payload pointers BEFORE Abort.
        let Some(lease) = self.lease.take() else { return; };
        if lease.seal.sealed.load(Ordering::Acquire) {
            drop(lease); // Never Abort a sealed/uncertain root; actual Drop retains.
            return;
        }
        let status = unsafe { ihk_os_application_abort_fork_payload_v1(ptr::from_ref(self.scope).cast_mut()) };
        if status == 0 {
            drop(lease); // Claim is gone BEFORE actual prepared publication unfreezes.
            return;
        }
        match lease.retain_prepared() {
            Ok(()) => {}
            Err(lease) => {
                // Unexpected structural damage still retains typed ownership.
                // Ordinary gates guarantee at least its pinned parent exists.
                let remote = lease.remote.as_ref().expect("unsealed retained lease lost Remote").clone();
                let mut marker = self.recovery.take().expect("retained ingress lost recovery metadata");
                marker.cancelled = true;
                marker.retained_lease = Some(lease);
                marker._retained_remote = Some(remote.clone());
                let mut slots = remote.slots.lock();
                let entry = slots.iter_mut().flatten().find(|entry|
                    (entry.key() == marker.child || entry.key() == marker.parent) && entry.fork_ingress.is_none())
                    .expect("all pinned ingress recovery slots disappeared");
                entry.quarantined = true;
                entry.fork_ingress = Some(marker);
            }
        }
    }
}

impl Remote {
    /// # Safety
    /// ONLY the genuine registered IHK scoped-adoption callback calls this.
    /// Its existing ForkProviderOwner pins actual admission/OS/module/storage
    /// before entry, owns any constructed capsule, and retains sealed/uncertain
    /// outcomes. The exact scope/seed/out pointers remain synchronous borrows.
    pub(crate) unsafe fn prepare_fork_carrier<'scope>(self: &Arc<Self>, parent: Token,
        child: Token, geometry: ForkGeometry, scope: &'scope ForkPayloadScopeV1)
        -> Result<PreparedForkCarrier<'scope>>
    {
        scope_metadata(self.owner, scope)?;
        // Descriptor fields are immutable: IHK validates/reads this SAME
        // stack descriptor during attach/Abort/Ready. No exclusive reference
        // may protect it against those raw shared reads across the callback.
        let scope_pointer = ptr::from_ref(scope).cast_mut();
        let initial = (|| -> Result<(Token, ResponseTicket)> {
            if geometry.root == 0 || geometry.root % 4096 != 0 || geometry.start % 4096 != 0
                || geometry.length == 0 || geometry.length % 4096 != 0
                || geometry.start.checked_add(geometry.length).is_none() { return Err(EINVAL); }
            let child_owner = Arc::new(ForkChildOwner::current()?, GFP_KERNEL)?;
            let seal = Arc::new(PreparedForkSeal { sealed: AtomicBool::new(false) }, GFP_KERNEL)?;
            let token = Token::allocate().map_err(errno)?;
            let mut slots = self.slots.lock();
            self.transport_health()?;
            let (pi, ci) = indexes(&slots, parent, child)?;
            current_entries(self.owner, &slots, pi, ci, &child_owner)?;
            if slots[ci].as_ref().unwrap().fork_ingress.is_some() { return Err(EBUSY); }
            let p = slots[pi].as_ref().unwrap();
            let parent_pid = p.cleanup.pid();
            let (worker, serial, request) = p.syscalls.unique_delivered(|request| {
                let a = request.arguments();
                request.number() == 56 && request.pid() == parent_pid && !matches!(a[0], 1 | 2 | 3)
                    && a[1] == geometry.start && a[2] == geometry.length && a[3] == geometry.root
                    && a[4] != 0 && a[4] % 8 == 0 && a[4].checked_add(128).is_some() && a[5] == CARRIER_MARKER
            }).map_err(errno)?.ok_or(ENOENT)?;
            if slots.iter().flatten().any(|entry|
                entry.fork.as_ref().is_some_and(|fork| fork.reservation.identity.root == geometry.root)
                    || entry.fork_ingress.as_ref().is_some_and(|marker| marker.request.arguments()[3] == geometry.root
                        || marker.parent == parent && marker.serial == serial)) { return Err(EBUSY); }
            let refs = slots[pi].as_ref().unwrap().fork_prepared_parent_refs.checked_add(1).ok_or_else(|| errno(-(kernel::bindings::EOVERFLOW as i32)))?;
            slots[ci].as_mut().unwrap().fork_ingress = Some(ForkIngressMarker {
                parent, child, token, worker, serial, cpu: request.cpu(), request: request.clone(),
                child_owner, seal, cancelled: false, retained_ticket: None, retained_lease: None,
                _retained_remote: None,
            });
            slots[pi].as_mut().unwrap().fork_prepared_parent_refs = refs;
            match slots[pi].as_mut().unwrap().syscalls.take_fork_ingress_response(worker, serial, &request).map_err(errno) {
                Ok(ticket) => Ok((token, ticket)),
                Err(error) => {
                    slots[pi].as_mut().unwrap().fork_prepared_parent_refs -= 1;
                    let removed = slots[ci].as_mut().unwrap().fork_ingress.take();
                    drop(slots); drop(removed);
                    Err(error)
                }
            }
        })();
        let (token, mut ticket) = match initial {
            Ok(value) => value,
            Err(error) => {
                // No MM/Q read/borrow exists and no marker remains. Actual IHK
                // validates its own scope before declaring pre-effect rollback.
                let _ = unsafe { ihk_os_application_abort_fork_payload_v1(scope_pointer) };
                return Err(error);
            }
        };
        let request = ticket.request().clone();
        let mut output: *mut c_void = ptr::null_mut();
        let attached = (|| -> Result {
            let response = ticket.response().map_err(errno)?;
            // SAFETY: This is the SAME actual delivered response, now owned by
            // this non-Copy ticket outside slots, under genuine IHK admission.
            let mut seed = unsafe { ForkPayloadSeed::new(response.memory_mut(), &request, self.owner) };
            let attach = scope.attach.ok_or(EACCES)?;
            let status = unsafe { attach(scope.context, Some(fork_payload_construct),
                ptr::from_mut(&mut seed).cast(), Some(fork_payload_abort), Some(fork_payload_complete), &mut output) };
            if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
            if output.is_null() { return Err(EIO); }
            Ok(())
        })();
        if let Err(error) = attached {
            let _ = core::mem::replace(&mut output, ptr::null_mut());
            // No payload borrow survives across actual IHK Abort.
            let _ = unsafe { rollback_provisional(self, parent, child, token, ticket, scope_pointer) };
            return Err(error);
        }
        // The actual attach success was checked for a nonnull initialized
        // borrowed context above. Keep the sole pointer in an Option so every
        // failed bind clears it before an IHK Abort can free the capsule.
        let mut payload = Some(NonNull::new(core::mem::replace(&mut output, ptr::null_mut()).cast::<ForkPayload>())
            .expect("checked attach returned a null payload"));
        let mut restore_failed = false;
        let bound = (|| -> Result<(PreparedForkLease, ForkIngressMarker)> {
            // SAFETY: Actual IHK owns this initialized payload capsule and
            // returns only this scoped borrow; nothing else may access bytes.
            let payload_ref = unsafe { payload.as_ref().unwrap().as_ref() };
            let descriptor = payload_ref.descriptor();
            let args = request.arguments();
            if payload_ref.owner() != self.owner || payload_ref.physical() != args[4]
                || payload_ref.original_response() != request.response()
                || descriptor.nonce == 0 || descriptor.root != geometry.root
                || descriptor.start != geometry.start || descriptor.length != geometry.length { return Err(EACCES); }
            let mut slots = self.slots.lock();
            self.transport_health()?;
            let (pi, ci) = indexes(&slots, parent, child)?;
            let marker = slots[ci].as_ref().and_then(|entry| entry.fork_ingress.as_ref()).ok_or(EIO)?;
            if !marker.exact(parent, child, token) || marker.cancelled || marker.request != request { return Err(EBUSY); }
            current_entries(self.owner, &slots, pi, ci, &marker.child_owner)?;
            let identity = ForkIdentity { slot: self.owner.slot(), generation: self.owner.generation(),
                parent: parent.wire(), worker: marker.worker, delivery: marker.serial, child: child.wire(),
                child_pid: marker.child_owner.number, child_mm: marker.child_owner.mm.as_ptr() as usize,
                root: geometry.root, start: geometry.start, length: geometry.length, nonce: descriptor.nonce };
            if slots.iter().flatten().filter_map(|entry| entry.fork.as_ref()).any(|fork| {
                let old = fork.reservation.identity;
                old.root == identity.root || old.parent == identity.parent
                    && (old.delivery == identity.delivery || old.nonce == identity.nonce)
            }) { return Err(EBUSY); }
            let mut state = ForkAdoption::reserve(identity)?;
            state.prepare_lease()?;
            if let Err(error) = slots[pi].as_mut().unwrap().syscalls.restore_fork_ingress_response(&mut ticket) {
                // Restore may have moved the response back before a later
                // cancellation error. Never retry it or declare rollback.
                restore_failed = true;
                return Err(errno(error));
            }
            let marker = slots[ci].as_mut().unwrap().fork_ingress.take().expect("validated ingress marker disappeared");
            let seal = marker.seal.clone();
            slots[ci].as_mut().unwrap().fork = Some(ChildFork {
                owner: marker.child_owner.clone(), seal: seal.clone(), retained_remote: None, retained_parent: None,
                held_lease: None, link: None, control: None,
                ack: Some(ForkAckRecord::new(scope.epoch)),
                reservation: ForkReservation { token, identity, cpu: request.cpu(), first: request.clone(),
                    state, return_value: None, return_published: false },
            });
            // The SAME parent pin transfers to the exact prepared lease, with
            // no publication/removal gap and no payload/phase authority copied.
            drop(slots);
            Ok((PreparedForkLease { remote: Some(self.clone()), seal, child, token: token.wire(), identity }, marker))
        })();
        let (lease, recovery) = match bound {
            Ok(value) => value,
            Err(error) => {
                payload.take(); // End the sole capsule borrow before cleanup.
                if restore_failed {
                    quarantine_provisional(self, parent, child, token, ticket);
                } else {
                    let _ = unsafe { rollback_provisional(self, parent, child, token, ticket, scope_pointer) };
                }
                return Err(error);
            }
        };
        let carrier = PreparedForkCarrier { lease: Some(lease), payload: payload.take(), scope, recovery: Some(recovery) };
        let key = carrier.lease.as_ref().unwrap().identity;
        // SAFETY: Still pre-MM, SAME real IHK capsule/lease; this prepares only
        // durable sequence0/link storage and cannot emit a successful receipt.
        unsafe { self.prepare_fork_link_carrier(child, key, carrier.payload.as_ref().unwrap().as_ref()) }?;
        Ok(carrier)
    }
}
