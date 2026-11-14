// SPDX-License-Identifier: GPL-2.0
//! Actual second-clone delivery transaction. This is a child of smp_application;
//! only its registered IHK resolver may supply the scoped payload borrow.
#![allow(dead_code)]
use super::*;
use core::sync::atomic::AtomicU8;
use super::super::{application_abi::{ForkIdentityV1, ForkLinkSealV1}, smp_memory::ForkPayload};
const CARRIER_MARKER: u64 = 0x313030434b46434d; // MCFKC001

/// Durable backend storage, not a phase proof. Bound by the actual first
/// receipt producer; retained even if every later callback/transport fails.
pub(super) struct ForkLinkRecord {
    identity: ForkIdentity,
    physical: u64,
    original_response: u64,
    last_sequence: u64,
    gate: Arc<AtomicU8>,
    second: Option<LinkDelivery>,
    busy: bool,
    receipt_written: bool,
    revoked_receipt_written: bool,
    return_accepted: bool,
    published: bool,
}
#[derive(Clone)]
struct LinkDelivery { worker: u64, serial: u64, cpu: i32, request: Request }
impl ForkLinkRecord {
    /// Parent abort/close must call this BEFORE altering the child lifecycle.
    /// SEALED is irreversible: even an error cannot queue a negative return or
    /// ordinary cleanup. The same retained ticket must finish or remain held.
    pub(super) fn cancel_if_open(&self) -> Result {
        match self.gate.compare_exchange(0, 1, Ordering::AcqRel, Ordering::Acquire) {
            Ok(_) | Err(1) => Ok(()),
            _ => Err(EBUSY),
        }
    }
    pub(super) fn sealed(&self) -> bool { self.gate.load(Ordering::Acquire) == 2 }
    pub(super) fn has_second_worker(&self, worker: u64) -> bool {
        self.second.as_ref().is_some_and(|delivery| delivery.worker == worker)
    }
    /// Metadata only. The ACK producer must additionally hold the actual
    /// HostRevoked state and the separately retained IHK epoch/Delivered call.
    pub(super) fn revoked_carrier(&self) -> Option<(u64, u64)> {
        self.revoked_receipt_written.then_some((self.physical, self.last_sequence))
    }
}

/// Stack ownership only of an exclusive borrow; the complete key, second
/// delivery, sequence and gate already live in ChildFork.link before callback.
/// Dropping this never destroys or cancels a sealed transaction.
pub(crate) struct PreparedLinkTicket {
    remote: Arc<Remote>, child: Token, gate: Arc<AtomicU8>, identity: ForkIdentity,
    second: LinkDelivery, physical: u64, sequence: u64,
}
fn host_key(k: ForkIdentity) -> ForkIdentityV1 {
    ForkIdentityV1 { slot: k.slot, reserved0: 0, generation: k.generation,
        parent: k.parent, worker: k.worker, delivery: k.delivery, child: k.child,
        child_pid: k.child_pid, reserved1: 0, child_mm: k.child_mm as u64,
        root: k.root, start: k.start, length: k.length, nonce: k.nonce }
}
fn payload_matches(payload: &ForkPayload, key: ForkIdentity, physical: u64, response: u64) -> bool {
    let descriptor = payload.descriptor();
    payload.owner().slot() == key.slot && payload.owner().generation() == key.generation
        && payload.physical() == physical && payload.original_response() == response
        && descriptor.nonce == key.nonce && descriptor.root == key.root
        && descriptor.start == key.start && descriptor.length == key.length
}
fn request_matches(d: &LinkDelivery, worker: u64, serial: u64, cpu: i64, request: &Request) -> bool {
    d.worker == worker && d.serial == serial && d.cpu as i64 == cpu && &d.request == request
}

impl Remote {
    /// # Safety
    /// Registered adoption calls this under the exact IHK pending owner and
    /// payload borrow BEFORE its consumer can seal any inherited VMA change.
    /// This prepares storage only; sequence zero authorizes no LINK receipt.
    pub(crate) unsafe fn prepare_fork_link_carrier(self: &Arc<Self>, child: Token,
        identity: ForkIdentity, payload: &ForkPayload) -> Result {
        if identity.slot != self.owner.slot() || identity.generation != self.owner.generation()
            || !payload_matches(payload, identity, payload.physical(), payload.original_response()) { return Err(EACCES); }
        let gate = Arc::new(AtomicU8::new(0), GFP_KERNEL)?;
        let mut slots = self.slots.lock();
        self.transport_health()?;
        let c = slots.iter_mut().flatten().find(|entry| entry.key() == child).ok_or(ENOENT)?;
        if c.closed || c.needs_cleanup || c.quarantined { return Err(EBUSY); }
        let fork = c.fork.as_mut().ok_or(ENOENT)?;
        if fork.reservation.identity != identity || identity.child != child.wire()
            || fork.owner.number != identity.child_pid || fork.owner.mm.as_ptr() as usize != identity.child_mm
            || fork.seal.sealed.load(Ordering::Acquire)
            || fork.reservation.state.phase() != ForkPhase::Reserved || !fork.reservation.state.prepared()
        { return Err(EBUSY); }
        if let Some(old) = fork.link.as_ref() {
            return if old.identity == identity && old.physical == payload.physical()
                && old.original_response == payload.original_response() && old.last_sequence == 0
                { Ok(()) } else { Err(EACCES) };
        }
        fork.link = Some(ForkLinkRecord { identity, physical: payload.physical(),
            original_response: payload.original_response(), last_sequence: 0,
            gate, second: None, busy: false, receipt_written: false,
            revoked_receipt_written: false,
            return_accepted: false, published: false });
        Ok(())
    }
    /// Recognizes only an actual Delivered second clone. Ordinary/legacy RETs
    /// are unchanged. No guest buffer or caller-supplied child key is read.
    pub(crate) fn begin_fork_link(self: &Arc<Self>, parent: Token, worker: u64,
        serial: u64, cpu: i64, value: i64) -> Result<Option<PreparedLinkTicket>> {
        let mut slots = self.slots.lock();
        self.transport_health()?;
        let pi = slots.iter().position(|s| s.as_ref().is_some_and(|e| e.key() == parent)).ok_or(ENOENT)?;
        let p = slots[pi].as_ref().unwrap();
        let proof = p.syscalls.unique_delivered(|request| {
            request.number() == 56 && request.arguments()[0] == 1
                && request.arguments()[5] == CARRIER_MARKER
        }).map_err(errno)?;
        let Some((actual_worker, actual_serial, request)) = proof else { return Ok(None); };
        if actual_worker != worker || actual_serial != serial { return Ok(None); }
        if p.closed || p.needs_cleanup || p.quarantined || !p.scheduled { return Err(EBUSY); }
        if p.owner_slot != self.owner.slot() as i32 || p.owner_generation != self.owner.generation() { return Err(EACCES); }
        if request.pid() != p.cleanup.pid() || request.cpu() as i64 != cpu || value != 0 { return Err(EACCES); }
        let args = request.arguments();
        let ci = slots.iter().position(|s| s.as_ref().and_then(|e| e.fork.as_ref()).is_some_and(|f| {
            let k = f.reservation.identity;
            k.parent == parent.wire() && k.child_pid as i64 == args[1] as i64
        })).ok_or(ENOENT)?;
        if ci == pi { return Err(EACCES); }
        let parent_refs = p.fork_prepared_parent_refs.checked_add(1).ok_or_else(|| errno(-(kernel::bindings::EOVERFLOW as i32)))?;
        let c = slots[ci].as_mut().unwrap();
        if c.closed || c.needs_cleanup || c.quarantined || c.prepare.is_some() { return Err(EBUSY); }
        if c.owner_slot != self.owner.slot() as i32 || c.owner_generation != self.owner.generation() { return Err(EACCES); }
        let child = c.key();
        let fork = c.fork.as_mut().unwrap();
        if fork.control.is_some() { return Err(EBUSY); }
        let key = fork.reservation.identity;
        if key.slot != self.owner.slot() || key.generation != self.owner.generation()
            || key.child != child.wire() || fork.owner.number != key.child_pid
            || fork.owner.mm.as_ptr() as usize != key.child_mm || args[2] != key.length
            || args[3] != key.root || !fork.reservation.return_published
            || fork.reservation.return_value != Some(key.child_pid as i64)
            || !matches!(fork.reservation.state.phase(), ForkPhase::FirstReturnPublished | ForkPhase::GuestLinkObserved)
        { return Err(EACCES); }
        let record = fork.link.as_mut().ok_or(EBUSY)?;
        if record.identity != key || record.physical != args[4] || record.last_sequence == 0 || record.busy || record.published { return Err(EBUSY); }
        let gate_state = record.gate.load(Ordering::Acquire);
        if !matches!(gate_state, 0 | 2) { return Err(EBUSY); }
        let second = LinkDelivery { worker, serial, cpu: request.cpu(), request: request.clone() };
        if let Some(old) = record.second.as_ref() {
            if !request_matches(old, worker, serial, cpu, &request) { return Err(EACCES); }
        } else {
            if gate_state != 0 { return Err(EACCES); }
            record.last_sequence = record.last_sequence.checked_add(1).ok_or_else(|| errno(-(kernel::bindings::EOVERFLOW as i32)))?;
            record.second = Some(second.clone());
        }
        record.busy = true;
        let ticket = PreparedLinkTicket { remote: self.clone(), child,
            gate: record.gate.clone(), identity: key, second,
            physical: record.physical, sequence: record.last_sequence };
        slots[pi].as_mut().unwrap().fork_prepared_parent_refs = parent_refs;
        Ok(Some(ticket))
    }
}

/// The checked adoption finisher holds the SAME slots lock across its exact
/// lease/seal validation, finish_lease transition and this first receipt write.
/// No caller-supplied counter or prior-write assertion creates sequence1.
pub(super) fn commit_adopted_fork_carrier_in_slots(owner: OsToken,
    slots: &mut [Option<Entry>], child: Token, identity: ForkIdentity,
    payload: &mut ForkPayload) -> Result {
    if identity.slot != owner.slot() || identity.generation != owner.generation() { return Err(EACCES); }
    let p = slots.iter().flatten().find(|e| e.key().wire() == identity.parent).ok_or(EBUSY)?;
    if p.closed || p.needs_cleanup || p.quarantined || !p.scheduled
        || p.owner_slot != owner.slot() as i32 || p.owner_generation != owner.generation() { return Err(EBUSY); }
    let parent_pid = p.cleanup.pid();
    let c = slots.iter_mut().flatten().find(|e| e.key() == child).ok_or(EBUSY)?;
    if c.closed || c.needs_cleanup || c.quarantined || c.owner_slot != owner.slot() as i32
        || c.owner_generation != owner.generation() { return Err(EBUSY); }
    let fork = c.fork.as_mut().ok_or(EBUSY)?;
    let first = fork.reservation.first.clone();
    let args = first.arguments();
    if fork.reservation.identity != identity || identity.child != child.wire()
        || fork.owner.number != identity.child_pid || fork.owner.mm.as_ptr() as usize != identity.child_mm
        || !fork.seal.sealed.load(Ordering::Acquire) || fork.reservation.state.prepared()
        || fork.reservation.state.phase() != ForkPhase::AdoptedAwaitFirstReturn
        || fork.reservation.return_published || fork.reservation.return_value.is_some()
        || first.number() != 56 || first.pid() != parent_pid || first.cpu() != fork.reservation.cpu
        || matches!(args[0], 1 | 2 | 3)
        || args[1] != identity.start || args[2] != identity.length || args[3] != identity.root
        || args[5] != CARRIER_MARKER
    { return Err(EBUSY); }
    let record = fork.link.as_mut().ok_or(EBUSY)?;
    if record.identity != identity || record.physical != args[4]
        || !payload_matches(payload, identity, record.physical, record.original_response)
        || record.gate.load(Ordering::Acquire) != 0 || record.second.is_some()
    { return Err(EACCES); }
    if record.last_sequence == 1 { return Ok(()); }
    if record.last_sequence != 0 { return Err(EACCES); }
    // All storage was prepared before adoption sealed. Byte copy is the only
    // fallible effect and its failure leaves sequence0 and every owner held.
    let bytes = receipt_bytes(record, 1, 1, identity.child_pid as i64);
    payload.copy_to_guest(&bytes)?;
    record.last_sequence = 1;
    Ok(())
}

/// Write the original unpublished first-clone cancellation receipt. Only the
/// actual payload-progress finisher calls this under SAME slots exclusion,
/// after its real backend drain and typed Mirror revoke callback. This helper
/// grants no HostRevoked or publication permission; the caller must reconcile
/// the original response and commit that phase before releasing the lock.
pub(super) fn commit_revoked_fork_carrier_in_slots(owner: OsToken,
    slots: &mut [Option<Entry>], child: Token, identity: ForkIdentity,
    payload: &mut ForkPayload) -> Result {
    if identity.slot != owner.slot() || identity.generation != owner.generation()
        || identity.child != child.wire() { return Err(EACCES); }
    let pi = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry|
        entry.key().wire() == identity.parent)).ok_or(EBUSY)?;
    let ci = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry|
        entry.key() == child)).ok_or(EBUSY)?;
    if pi == ci { return Err(EACCES); }
    let parent = slots[pi].as_ref().unwrap();
    let current = slots[ci].as_ref().unwrap();
    if parent.owner_slot != owner.slot() as i32 || parent.owner_generation != owner.generation()
        || current.owner_slot != owner.slot() as i32 || current.owner_generation != owner.generation()
    { return Err(EACCES); }
    // A closed parent may still own this unpublished response. Child service
    // admission must already be closed and its real mailbox drained; absent
    // PID or a scalar cancellation selector is never a release proof.
    if !current.needs_cleanup || current.scheduled || current.prepare.is_some()
        || current.procfs.is_some() || !current.syscalls.drained() { return Err(EBUSY); }
    let fork = current.fork.as_ref().ok_or(EBUSY)?;
    let first = fork.reservation.first.clone();
    let value = fork.reservation.return_value;
    let args = first.arguments();
    if fork.reservation.identity != identity || fork.owner.number != identity.child_pid
        || fork.owner.mm.as_ptr() as usize != identity.child_mm
        || !fork.seal.sealed.load(Ordering::Acquire) || fork.reservation.state.prepared()
        || !matches!(fork.reservation.state.phase(), ForkPhase::AbortRequested | ForkPhase::Quarantined)
        || fork.reservation.return_published || first.number() != 56
        || first.pid() != parent.cleanup.pid() || first.cpu() != fork.reservation.cpu
        || matches!(args[0], 1 | 2 | 3) || args[1] != identity.start
        || args[2] != identity.length || args[3] != identity.root || args[5] != CARRIER_MARKER
    { return Err(EBUSY); }
    let record = fork.link.as_ref().ok_or(EBUSY)?;
    if record.identity != identity || record.physical != args[4]
        || !payload_matches(payload, identity, record.physical, record.original_response)
        || record.gate.load(Ordering::Acquire) != 1 || record.second.is_some()
        || record.busy || record.receipt_written || record.return_accepted || record.published
        || record.last_sequence > 1 { return Err(EACCES); }
    // Check the SAME live response's atomic unpublished state under its actual
    // mailbox ownership before replacing an unseen kind1 sequence1. No guest
    // bytes, caller-supplied sequence or prior-written assertion authorize it.
    slots[pi].as_mut().unwrap().syscalls.check_fork_abort(
        identity.worker, identity.delivery, &first, value,
    ).map_err(errno)?;
    let record = slots[ci].as_mut().unwrap().fork.as_mut().unwrap().link.as_mut().unwrap();
    let bytes = receipt_bytes(record, 1, 3, -125);
    payload.copy_to_guest(&bytes)?;
    record.last_sequence = 1;
    record.revoked_receipt_written = true;
    Ok(())
}

impl PreparedLinkTicket {
    pub(crate) fn descriptor(&mut self) -> ForkLinkSealV1 {
        ForkLinkSealV1 { version: 1, bytes: core::mem::size_of::<ForkLinkSealV1>() as u32,
            identity: host_key(self.identity), second_worker: self.second.worker,
            second_delivery: self.second.serial, second_cpu: self.second.cpu, reserved: 0,
            carrier_physical: self.physical, carrier_sequence: self.sequence,
            gate: (&*self.gate as *const AtomicU8).cast_mut() }
    }

    /// # Safety
    /// Registered SMP Finish receives this SAME live stack ticket and a scoped
    /// unique payload borrow from the IHK resolver's exact pending capsule.
    /// No owned Rust object crosses the ABI; every outer pin survives return.
    pub(crate) unsafe fn finish_with_payload(&mut self, payload: &mut ForkPayload) -> Result {
        if self.gate.load(Ordering::Acquire) != 2 { return Err(EBUSY); }
        let mut slots = self.remote.slots.lock();
        self.remote.transport_health()?;
        let pi = slots.iter().position(|s| s.as_ref().is_some_and(|e| e.key().wire() == self.identity.parent)).ok_or(EBUSY)?;
        let p = slots[pi].as_ref().unwrap();
        if p.closed || p.needs_cleanup || p.quarantined { return Err(EBUSY); }
        let proof = p.syscalls.unique_delivered(|r| r == &self.second.request).map_err(errno)?.ok_or(EBUSY)?;
        if proof.0 != self.second.worker || proof.1 != self.second.serial { return Err(EACCES); }
        let c = slots.iter_mut().flatten().find(|e| e.key() == self.child).ok_or(EBUSY)?;
        if c.closed || c.needs_cleanup || c.quarantined { return Err(EBUSY); }
        let fork = c.fork.as_mut().ok_or(EBUSY)?;
        if fork.reservation.identity != self.identity { return Err(EACCES); }
        let record = fork.link.as_mut().ok_or(EBUSY)?;
        if !record.busy || !ptr::eq(&*record.gate, &*self.gate) || !record.sealed()
            || record.identity != self.identity || record.last_sequence != self.sequence
            || record.second.as_ref().is_none_or(|d| !request_matches(d, self.second.worker, self.second.serial, self.second.cpu as i64, &self.second.request))
            || !payload_matches(payload, self.identity, record.physical, record.original_response)
        { return Err(EACCES); }
        if !record.receipt_written {
            if fork.reservation.state.phase() != ForkPhase::FirstReturnPublished { return Err(EBUSY); }
            // Fixed LINK_READY/result0 only, from the retained backend record.
            // Storage copy grants no phase authority; the same gate seal and
            // all identity/delivery revalidation above authorized these bytes.
            let bytes = receipt_bytes(record, record.last_sequence, 2, 0);
            payload.copy_to_guest(&bytes)?;
            fork.reservation.state.observe_link(self.identity)?;
            record.receipt_written = true;
        }
        Ok(())
    }
}
impl Drop for PreparedLinkTicket {
    fn drop(&mut self) {
        let mut slots = self.remote.slots.lock();
        if let Some(c) = slots.iter_mut().flatten().find(|e| e.key() == self.child) {
            if let Some(record) = c.fork.as_mut().and_then(|f| f.link.as_mut()) {
                if record.identity == self.identity && ptr::eq(&*record.gate, &*self.gate) { record.busy = false; }
            }
        }
        if let Some(p) = slots.iter_mut().flatten().find(|e| e.key().wire() == self.identity.parent) {
            if let Some(count) = p.fork_prepared_parent_refs.checked_sub(1) { p.fork_prepared_parent_refs = count; }
            else { p.quarantined = true; }
        }
        // The durable ChildFork record owns SEALED/sequence even on failure.
        // Neither callback error nor this stack destructor cancels/revokes it.
    }
}
fn receipt_bytes(record: &ForkLinkRecord, sequence: u64, kind: u32, result: i64) -> [u8; 128] {
    let k = record.identity;
    let mut b = [0; 128];
    b[..8].copy_from_slice(b"MCFKW001");
    b[8..10].copy_from_slice(&1u16.to_le_bytes());b[10..12].copy_from_slice(&40u16.to_le_bytes());
    b[12..16].copy_from_slice(&128u32.to_le_bytes());b[16..20].copy_from_slice(&kind.to_le_bytes());
    b[24..32].copy_from_slice(&sequence.to_le_bytes());b[32..40].copy_from_slice(&result.to_le_bytes());
    b[40..44].copy_from_slice(&k.slot.to_le_bytes());b[44..48].copy_from_slice(&k.child_pid.to_le_bytes());
    for (offset, value) in [(48,k.generation),(56,k.parent),(64,k.worker),(72,k.delivery),
        (80,k.child),(88,k.child_mm as u64),(96,k.root),(104,k.start),(112,k.length),(120,k.nonce)] {
        b[offset..offset+8].copy_from_slice(&value.to_le_bytes());
    }
    b
}

/// Parent RET validation hook, before any response is committed.
pub(super) fn authorize_return(slots: &[Option<Entry>], parent: Token,
    worker: u64, serial: u64, cpu: i64, value: i64) -> Result {
    for record in slots.iter().flatten().filter_map(|e| e.fork.as_ref().and_then(|f| f.link.as_ref())) {
        if record.identity.parent == parent.wire() && record.second.as_ref().is_some_and(|d| d.worker == worker && d.serial == serial) {
            let d = record.second.as_ref().unwrap();
            if value != 0 || d.cpu as i64 != cpu || !record.sealed() || !record.receipt_written { return Err(EBUSY); }
        }
    }
    Ok(())
}
pub(super) fn record_return(slots: &mut [Option<Entry>], parent: Token, worker: u64, serial: u64, value: i64) {
    for record in slots.iter_mut().flatten().filter_map(|e| e.fork.as_mut().and_then(|f| f.link.as_mut())) {
        if record.identity.parent == parent.wire() && record.second.as_ref().is_some_and(|d| d.worker == worker && d.serial == serial)
            && value == 0 && record.sealed() && record.receipt_written { record.return_accepted = true; }
    }
}
/// Includes automatic worker-close returns, which bypass explicit RET hooks.
pub(super) fn publication_frozen(slots: &mut [Option<Entry>], parent: Token, cpu: i32) -> bool {
    let Some(pi) = slots.iter().position(|s| s.as_ref().is_some_and(|e| e.key() == parent)) else { return false; };
    let parent_pid = slots[pi].as_ref().unwrap().cleanup.pid();
    for ci in 0..slots.len() {
        let Some(record) = slots[ci].as_ref().and_then(|e| e.fork.as_ref()).and_then(|f| f.link.as_ref()) else { continue; };
        if record.identity.parent != parent.wire() { continue; }
        let key = record.identity;
        let physical = record.physical;
        let second = record.second.clone();
        let published = record.published;
        let ready = record.sealed() && record.receipt_written && record.return_accepted;
        // Discovery includes queued and cancelling calls BEFORE begin_link can
        // capture a ticket. A close may queue -512 on a different guest CPU.
        let unexpected = slots[pi].as_ref().unwrap().syscalls.has_fork_link_response(cpu, |r| {
            let a = r.arguments();
            r.pid() == parent_pid && a[1] == key.child_pid as u64 && a[2] == key.length
                && a[3] == key.root && a[4] == physical && a[5] == CARRIER_MARKER
                && (published || second.as_ref().is_none_or(|d| r != &d.request))
        });
        if unexpected { return true; }
        let Some(d) = second else { continue; };
        if d.cpu != cpu || published { continue; }
        if !ready { return true; }
        if slots[pi].as_mut().unwrap().syscalls.check_fork_abort(d.worker, d.serial, &d.request, Some(0)).is_err() { return true; }
    }
    false
}
pub(super) fn observe_publication(slots: &mut [Option<Entry>], parent: Token) {
    let Some(pi) = slots.iter().position(|s| s.as_ref().is_some_and(|e| e.key() == parent)) else { return; };
    for ci in 0..slots.len() {
        let second = slots[ci].as_ref().and_then(|e| e.fork.as_ref()).and_then(|f| f.link.as_ref()).filter(|r| r.identity.parent == parent.wire() && r.receipt_written && r.return_accepted && !r.published).and_then(|r| r.second.clone());
        let Some(d) = second else { continue; };
        if slots[pi].as_ref().unwrap().syscalls.returned(d.worker, d.serial) != Ok(true) { continue; }
        let c = slots[ci].as_mut().unwrap();let fork = c.fork.as_mut().unwrap();let record = fork.link.as_mut().unwrap();
        if record.sealed() && fork.reservation.state.second_return_published(record.identity, 0).is_ok() {
            record.published = true;
            // Actual guest child syscalls can be admitted only after the real
            // second response publication, under this same slots mutex.
            c.scheduled = true;
        }
    }
}

// A real fresh delivered response, retained independently of the already
// published first RET. No Drop/release API: discard cannot authorize completion.
pub(super) struct ForkControlOwner {
    descriptor: super::super::application_abi::ForkControlV1,
    request: Request,
    _response: super::super::smp_application_syscall::ForkIngressResponse<SyscallResponse>,
    _parent: ForkParentPin,
    quarantined: bool,
    receipt: ControlReceiptRecord,
}
pub(crate) struct PreparedControlTicket {
    remote: Arc<Remote>, parent: Token, child: Token,
    descriptor: super::super::application_abi::ForkControlV1,
    request: Request, parked: bool,
}

// Call only with SAME Remote slots guard. This validates metadata, not a revoke
// receipt. Exact current ChildFork and first-publication state supply authority.
fn control_snapshot(remote: &Remote, slots: &[Option<Entry>], parent: Token,
    worker: u64, serial: u64, cpu: i64,
) -> Result<Option<(Token, super::super::application_abi::ForkControlV1, Request)>> {
    remote.transport_health()?;
    let p = slots.iter().flatten().find(|e| e.key() == parent).ok_or(ENOENT)?;
    // A parked call no longer appears in unique_delivered because the SAME
    // Response has moved. Reject its exact retry before legacy RETURN hooks.
    for f in slots.iter().flatten().filter_map(|e| e.fork.as_ref()) {
        let Some(control) = &f.control else { continue; };
        let d = control.descriptor;
        if d.identity.parent != parent.wire() || d.worker != worker || d.delivery != serial { continue; }
        if d.cpu as i64 != cpu || d.identity != host_key(f.reservation.identity)
            || f.ack.as_ref().is_none_or(|ack| ack.epoch != d.epoch)
            || control.request.number() != 56 || control.request.arguments()[0] != 2
            || control.request.arguments()[5] != CARRIER_MARKER
            || control.request.pid() != p.cleanup.pid() || control.request.cpu() != d.cpu
            || control.request.response() != d.response || control._response.request() != &control.request
        { return Err(EACCES); }
        return Err(EBUSY);
    }
    let proof = p.syscalls.unique_delivered(|r| r.number() == 56 && r.arguments()[0] == 2).map_err(errno)?;
    let Some((actual_worker, actual_serial, request)) = proof else { return Ok(None); };
    if actual_worker != worker || actual_serial != serial { return Ok(None); }
    if p.closed || p.needs_cleanup || p.quarantined || !p.scheduled { return Err(EBUSY); }
    if p.owner_slot != remote.owner.slot() as i32 || p.owner_generation != remote.owner.generation()
        || request.pid() != p.cleanup.pid() || request.cpu() as i64 != cpu
        || cpu < 0 || request.response() == 0 || request.arguments()[5] != CARRIER_MARKER
    { return Err(EACCES); }
    let args = request.arguments();
    let c = slots.iter().flatten().find(|e| e.fork.as_ref().is_some_and(|f|
        f.reservation.identity.parent == parent.wire()
            && f.reservation.identity.child_pid as i64 == args[1] as i64)).ok_or(ENOENT)?;
    if c.key() == parent || c.closed || c.needs_cleanup || c.quarantined
        || c.scheduled || c.prepare.is_some() || c.procfs.is_some() || !c.syscalls.drained()
    { return Err(EBUSY); }
    if c.owner_slot != remote.owner.slot() as i32 || c.owner_generation != remote.owner.generation() { return Err(EACCES); }
    let f = c.fork.as_ref().unwrap(); let k = f.reservation.identity;
    let link = f.link.as_ref().ok_or(EBUSY)?;
    let ack = f.ack.as_ref().ok_or(EBUSY)?;
    if k.slot != remote.owner.slot() || k.generation != remote.owner.generation()
        || k.child != c.key().wire() || f.owner.number != k.child_pid
        || f.owner.mm.as_ptr() as usize != k.child_mm || args[2] != k.length || args[3] != k.root
        || !f.seal.sealed.load(Ordering::Acquire) || f.reservation.state.prepared()
        || !f.reservation.return_published || f.reservation.return_value != Some(k.child_pid as i64)
        || f.reservation.state.phase() != ForkPhase::FirstReturnPublished
        || f.control.is_some() || f.retained_parent.is_none()
        || ack.epoch == 0 || ack.delivery.is_some() || ack.busy || ack.verified || ack.accepted
        || link.identity != k || link.physical != args[4] || link.last_sequence != 1
        || link.gate.load(Ordering::Acquire) != 0 || link.second.is_some() || link.busy
        || link.published || link.receipt_written || link.revoked_receipt_written
        || request.response() == link.original_response
    { return Err(EBUSY); }
    let pin = f.retained_parent.as_ref().ok_or(EBUSY)?;
    if pin.parent != parent || pin.identity != k || pin.reservation != f.reservation.token.wire()
        || !core::ptr::eq(&*pin.remote, remote) { return Err(EACCES); }
    let descriptor = super::super::application_abi::ForkControlV1 {
        version: 1, bytes: core::mem::size_of::<super::super::application_abi::ForkControlV1>() as u32,
        identity: host_key(k), epoch: ack.epoch, worker, delivery: serial, cpu: request.cpu(),
        reserved: 0, physical: link.physical, response: request.response(),
    };
    Ok(Some((c.key(), descriptor, request)))
}
impl Remote {
    pub(crate) fn begin_fork_control(self: &Arc<Self>, parent: Token, worker: u64,
        serial: u64, cpu: i64, _value: i64) -> Result<Option<PreparedControlTicket>> {
        let slots = self.slots.lock();
        let Some((child, descriptor, request)) = control_snapshot(self, &slots, parent, worker, serial, cpu)?
            else { return Ok(None); };
        Ok(Some(PreparedControlTicket { remote: self.clone(), parent, child, descriptor, request, parked: false }))
    }
}
impl PreparedControlTicket {
    pub(crate) fn descriptor(&self) -> super::super::application_abi::ForkControlV1 { self.descriptor }
    /// # Safety
    /// IHK lends only its initialized exact-epoch capsule under an exclusive
    /// PENDING control claim. Shared metadata borrow ends before claim restore.
    pub(crate) unsafe fn park(&mut self, payload: &ForkPayload) -> Result {
        if self.parked { return Err(EBUSY); }
        let mut slots = self.remote.slots.lock();
        let d = self.descriptor;
        let Some((child, current, request)) = control_snapshot(&self.remote, &slots, self.parent,
            d.worker, d.delivery, d.cpu as i64)? else { return Err(EACCES); };
        if child != self.child || current != d || request != self.request { return Err(EACCES); }
        let pi = slots.iter().position(|e| e.as_ref().is_some_and(|e| e.key() == self.parent)).ok_or(ENOENT)?;
        let ci = slots.iter().position(|e| e.as_ref().is_some_and(|e| e.key() == self.child)).ok_or(ENOENT)?;
        let f = slots[ci].as_ref().unwrap().fork.as_ref().unwrap();
        let key = f.reservation.identity; let reservation = f.reservation.token.wire();
        let original = f.link.as_ref().unwrap().original_response;
        if !payload_matches(payload, key, d.physical, original) { return Err(EACCES); }
        let count = slots[pi].as_ref().unwrap().fork_prepared_parent_refs.checked_add(1).ok_or_else(|| errno(-(kernel::bindings::EOVERFLOW as i32)))?;
        // No fallible effect follows this actual mailbox ownership transfer.
        // All validation and count arithmetic precede moving the SAME Response.
        let response = slots[pi].as_mut().unwrap().syscalls.take_fork_ingress_response(
            d.worker, d.delivery, &self.request).map_err(errno)?;
        let owner = ForkControlOwner { descriptor: d, request: self.request.clone(), _response: response,
            _parent: ForkParentPin { parent: self.parent, identity: key, reservation, remote: self.remote.clone() },
            quarantined: false, receipt: ControlReceiptRecord::new() };
        slots[pi].as_mut().unwrap().fork_prepared_parent_refs = count;
        slots[ci].as_mut().unwrap().fork.as_mut().unwrap().control = Some(owner);
        self.parked = true;
        Ok(())
    }
    // Restore failure after the move must retain both actual owners, never
    // return the response to ordinary RET or decrement the pin on uncertainty.
    pub(crate) fn quarantine_if_parked(&self) {
        if !self.parked { return; }
        let mut slots = self.remote.slots.lock();
        if let Some(c) = slots.iter_mut().flatten().find(|e| e.key() == self.child) {
            if let Some(control) = c.fork.as_mut().and_then(|f| f.control.as_mut()) {
                if control.descriptor == self.descriptor && control.request == self.request {
                    control.quarantined = true; c.quarantined = true;
                }
            }
        }
    }
}
pub(super) fn control_publication_frozen(slots: &[Option<Entry>], parent: Token, cpu: i32) -> bool {
    let Some(p) = slots.iter().flatten().find(|e| e.key() == parent) else { return false; };
    slots.iter().flatten().filter_map(|e| e.fork.as_ref()).any(|f| {
        let k = f.reservation.identity;
        if k.parent != parent.wire() { return false; }
        if f.control.as_ref().is_some_and(|c| c.descriptor.cpu == cpu) { return true; }
        let Some(link) = &f.link else { return false; };
        p.syscalls.has_private_fork_response(cpu, 2, |r| {
            let a = r.arguments(); r.pid() == p.cleanup.pid() && a[1] == k.child_pid as u64
                && a[2] == k.length && a[3] == k.root && a[4] == link.physical && a[5] == CARRIER_MARKER
        })
    })
}
pub(super) fn authorize_control_return(slots: &[Option<Entry>], parent: Token, worker: u64, serial: u64) -> Result {
    if slots.iter().flatten().filter_map(|e| e.fork.as_ref()).any(|f| f.control.as_ref().is_some_and(|c|
        c.descriptor.identity.parent == parent.wire() && c.descriptor.worker == worker && c.descriptor.delivery == serial))
    { return Err(EBUSY); }
    Ok(())
}

// Source-only postpositive receipt contract. Existing guest MCFKW001 consumers
// do not accept this frame. A future authenticated delivery/consumer is required.
struct HostAliasesRevokedControl {
    descriptor: super::super::application_abi::ForkControlV1,
}
struct ControlReceiptRecord {
    frozen: bool,
    proof: Option<HostAliasesRevokedControl>,
    journal: Option<[u8; 128]>,
    written: bool,
    uncertain: bool,
    write_error: Option<i32>,
    queued: bool,
    published: bool,
}
impl ControlReceiptRecord {
    fn new() -> Self { Self { frozen: false, proof: None, journal: None,
        written: false, uncertain: false, write_error: None, queued: false, published: false } }
}
pub(crate) struct PreparedControlReceiptTicket {
    remote: Arc<Remote>, parent: Token, child: Token,
    descriptor: super::super::application_abi::ForkControlV1,
    request: Request,
}
pub(crate) enum ControlReceiptOutcome { Written, Uncertain }

fn control_receipt_bytes(d: super::super::application_abi::ForkControlV1) -> [u8; 128] {
    let k = d.identity;
    let mut bytes = [0u8; 128];
    bytes[..8].copy_from_slice(b"MCFKR001");
    for (offset, value) in [(8,d.epoch),(16,d.worker),(24,d.delivery),(32,d.response),
        (48,k.generation),(56,k.parent),(64,k.worker),(72,k.delivery),(80,k.child),
        (88,k.child_mm),(96,k.root),(104,k.start),(112,k.length),(120,k.nonce)] {
        bytes[offset..offset+8].copy_from_slice(&value.to_le_bytes());
    }
    bytes[40..44].copy_from_slice(&k.slot.to_le_bytes());
    bytes[44..48].copy_from_slice(&k.child_pid.to_le_bytes());
    bytes
}

// SAME slots exclusion throughout scalar validation. No IHK/MM callback runs
// here. This is a resume of one durable owner, never a new Delivered discovery.
fn control_receipt_snapshot(remote: &Remote, slots: &[Option<Entry>], parent: Token,
    worker: u64, serial: u64, cpu: i64,
) -> Result<Option<(Token, super::super::application_abi::ForkControlV1, Request)>> {
    remote.transport_health()?;
    let p = slots.iter().flatten().find(|e| e.key() == parent).ok_or(ENOENT)?;
    let found = slots.iter().flatten().find(|e| e.fork.as_ref().and_then(|f|f.control.as_ref())
        .is_some_and(|c| c.descriptor.identity.parent == parent.wire()
            && c.descriptor.worker == worker && c.descriptor.delivery == serial));
    let Some(c) = found else { return Ok(None); };
    let f = c.fork.as_ref().unwrap(); let control = f.control.as_ref().unwrap();
    let d = control.descriptor; let k = f.reservation.identity;
    if p.closed || p.needs_cleanup || p.quarantined || !p.scheduled
        || c.closed || c.quarantined || c.scheduled || c.prepare.is_some() || c.procfs.is_some()
        || !c.syscalls.drained() || control.quarantined || control.receipt.uncertain
    { return Err(EBUSY); }
    if p.owner_slot != remote.owner.slot() as i32 || p.owner_generation != remote.owner.generation()
        || c.owner_slot != remote.owner.slot() as i32 || c.owner_generation != remote.owner.generation()
        || k.slot != remote.owner.slot() || k.generation != remote.owner.generation()
        || k.parent != parent.wire() || k.child != c.key().wire() || d.identity != host_key(k)
        || d.cpu as i64 != cpu || d.epoch == 0 || f.ack.as_ref().is_none_or(|ack|ack.epoch != d.epoch)
        || f.owner.number != k.child_pid || f.owner.mm.as_ptr() as usize != k.child_mm
        || !f.seal.sealed.load(Ordering::Acquire) || f.reservation.state.prepared()
        || !f.reservation.return_published || f.reservation.return_value != Some(k.child_pid as i64)
        || f.reservation.state.phase() != ForkPhase::FirstReturnPublished
    { return Err(EACCES); }
    let r = &control.request; let args = r.arguments();
    if r.number() != 56 || r.pid() != p.cleanup.pid() || r.cpu() != d.cpu || r.response() != d.response
        || args[0] != 2 || args[1] != k.child_pid as u64 || args[2] != k.length
        || args[3] != k.root || args[4] != d.physical || args[5] != CARRIER_MARKER
        || control._response.request() != r || control._parent.parent != parent
        || control._parent.identity != k || control._parent.reservation != f.reservation.token.wire()
        || !core::ptr::eq(&*control._parent.remote, remote)
    { return Err(EACCES); }
    let link = f.link.as_ref().ok_or(EBUSY)?;
    if link.identity != k || link.physical != d.physical || link.last_sequence != 1
        || link.busy || link.second.is_some() || link.published || link.receipt_written
        || link.revoked_receipt_written
        || link.gate.load(Ordering::Acquire) != u8::from(control.receipt.frozen)
        || c.needs_cleanup != control.receipt.frozen
    { return Err(EBUSY); }
    Ok(Some((c.key(), d, r.clone())))
}
impl Remote {
    pub(crate) fn begin_fork_control_receipt(self: &Arc<Self>, parent: Token, worker: u64,
        serial: u64, cpu: i64, _value: i64) -> Result<Option<PreparedControlReceiptTicket>> {
        let slots = self.slots.lock();
        let Some((child, descriptor, request)) = control_receipt_snapshot(self, &slots, parent, worker, serial, cpu)?
            else { return Ok(None); };
        Ok(Some(PreparedControlReceiptTicket { remote: self.clone(), parent, child, descriptor, request }))
    }
}
impl PreparedControlReceiptTicket {
    pub(crate) fn descriptor(&self) -> super::super::application_abi::ForkControlV1 { self.descriptor }
    fn indexes(&self, slots: &[Option<Entry>]) -> Result<(usize, usize)> {
        let d = self.descriptor;
        let Some((child, actual, request)) = control_receipt_snapshot(&self.remote, slots,
            self.parent, d.worker, d.delivery, d.cpu as i64)? else { return Err(EACCES); };
        if child != self.child || actual != d || request != self.request { return Err(EACCES); }
        let pi = slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==self.parent)).ok_or(ENOENT)?;
        let ci = slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==self.child)).ok_or(ENOENT)?;
        Ok((pi, ci))
    }
    fn freeze(&self) -> Result<bool> {
        let mut slots = self.remote.slots.lock();
        let (_, ci) = self.indexes(&slots)?;
        let child = slots[ci].as_mut().unwrap();
        let fork = child.fork.as_mut().unwrap(); let control = fork.control.as_mut().unwrap();
        if control.receipt.written {
            if !control.receipt.frozen
                || control.receipt.proof.as_ref().is_none_or(|proof|proof.descriptor != self.descriptor)
                || control.receipt.journal != Some(control_receipt_bytes(self.descriptor))
            { return Err(EIO); }
            return Ok(true);
        }
        if !control.receipt.frozen {
            // Actual gate closure precedes the real MM callback. No sealed
            // LINK can race it; every begin/link/removal path also sees control.
            fork.link.as_ref().unwrap().cancel_if_open()?;
            control.receipt.frozen = true; child.needs_cleanup = true;
            child.syscalls.close().map_err(errno)?;
        }
        Ok(false)
    }
    /// # Safety
    /// ONLY the exact live IHK BUSY control claim calls this trusted registered
    /// continuation with its module-pinned capsule.verify and payload contexts.
    /// No Slots/table/MM guard crosses verify; mutable payload exists only in
    /// write_verified after actual MM proof and exact slots-held revalidation.
    pub(crate) unsafe fn resume(&self, verify: super::super::application_abi::ForkVerifyV1,
        context: *mut core::ffi::c_void, payload: NonNull<ForkPayload>) -> Result<ControlReceiptOutcome> {
        if self.freeze()? { return Ok(ControlReceiptOutcome::Written); }
        let status = unsafe { verify(context, &self.descriptor.identity) };
        if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
        // This non-Copy authority has no public constructor and is created
        // ONLY after the actual registered Mirror revoke verifier succeeds.
        let proof = HostAliasesRevokedControl { descriptor: self.descriptor };
        unsafe { self.write_verified(proof, payload) }
    }
    unsafe fn write_verified(&self, proof: HostAliasesRevokedControl,
        mut payload: NonNull<ForkPayload>) -> Result<ControlReceiptOutcome> {
        let mut slots = self.remote.slots.lock(); let (_, ci) = self.indexes(&slots)?;
        let f = slots[ci].as_mut().unwrap().fork.as_mut().unwrap();
        let k = f.reservation.identity; let original = f.link.as_ref().unwrap().original_response;
        let control = f.control.as_mut().unwrap();
        if proof.descriptor != self.descriptor || !control.receipt.frozen
            || control.receipt.written || control.receipt.uncertain || control.receipt.journal.is_some()
        { return Err(EBUSY); }
        // Validate SAME fresh response is still unpublished, without writing a
        // result or converting launcher0/-95 into a permission.
        control._response.response().map_err(errno)?.check_fork_unpublished(&self.request).map_err(errno)?;
        let payload = unsafe { payload.as_mut() };
        if !payload_matches(payload, k, self.descriptor.physical, original) { return Err(EACCES); }
        let bytes = control_receipt_bytes(self.descriptor);
        control.receipt.proof = Some(proof); control.receipt.journal = Some(bytes);
        match payload.copy_to_guest(&bytes) {
            Ok(()) => { control.receipt.written = true; Ok(ControlReceiptOutcome::Written) },
            Err(error) => {
                // Any error is conservatively uncertain, even a pre-copy
                // failure. Keep the exact immutable journal and actual owners;
                // no unverified replay/overwrite or first-RET rollback exists.
                control.receipt.uncertain = true; control.receipt.write_error = Some(error.to_errno());
                control.quarantined = true;
                Ok(ControlReceiptOutcome::Uncertain)
            },
        }
    }
    pub(crate) fn quarantine(&self) {
        let mut slots = self.remote.slots.lock();
        if let Some(c) = slots.iter_mut().flatten().find(|e|e.key()==self.child) {
            if let Some(control) = c.fork.as_mut().and_then(|f|f.control.as_mut()) {
                if control.descriptor == self.descriptor && control.request == self.request {
                    control.quarantined = true; c.quarantined = true;
                }
            }
        }
    }
}


// Zero is transport success only. The private receipt proof, not this scalar,
// permits queueing; no legacy HOST_REVOKED/ACK/task-publication flag changes.
const CONTROL_RECEIPT_TRANSPORT_SUCCESS: i64 = 0;

pub(super) fn queue_control_receipt_in_slots(remote: &Remote, slots: &mut [Option<Entry>],
    parent: Token, worker: u64, serial: u64, cpu: i64, destination: u64, length: u64,
) -> Result<Option<()>> {
    // Ordinary returns retain their original gate/error order. Only an exact
    // durable control owner enters the strict transport/receipt checks.
    if !slots.iter().flatten().filter_map(|e|e.fork.as_ref()).filter_map(|f|f.control.as_ref())
        .any(|c|c.descriptor.identity.parent==parent.wire()&&c.descriptor.worker==worker&&c.descriptor.delivery==serial)
    { return Ok(None); }
    let Some((child, descriptor, request)) = control_receipt_snapshot(remote, slots,
        parent, worker, serial, cpu)? else { return Ok(None); };
    if destination != 0 || length != 0 { return Err(EINVAL); }
    let pi = slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==parent)).ok_or(ENOENT)?;
    let ci = slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==child)).ok_or(ENOENT)?;
    if pi == ci { return Err(EIO); }
    let (p,c) = if pi < ci { let(a,b)=slots.split_at_mut(ci);(a[pi].as_mut().unwrap(),b[0].as_mut().unwrap()) }
        else { let(a,b)=slots.split_at_mut(pi);(b[0].as_mut().unwrap(),a[ci].as_mut().unwrap()) };
    let control=c.fork.as_mut().unwrap().control.as_mut().unwrap();
    if !control.receipt.frozen || !control.receipt.written || control.receipt.uncertain
        || control.receipt.proof.as_ref().is_none_or(|proof|proof.descriptor != descriptor)
        || control.receipt.journal != Some(control_receipt_bytes(descriptor))
        || control.request != request
    { return Err(EBUSY); }
    if control.receipt.queued { return Ok(Some(())); }
    match p.syscalls.queue_control_response(&mut control._response,
        CONTROL_RECEIPT_TRANSPORT_SUCCESS) {
        Ok(()) => { control.receipt.queued=true; Ok(Some(())) },
        Err((error, uncertain)) => {
            if uncertain {
                // The SAME response or completion remains owned. No retry can
                // overwrite a response whose wake-state outcome is uncertain.
                control.quarantined=true;control.receipt.uncertain=true;
                control.receipt.write_error=Some(error);c.quarantined=true;
            }
            Err(errno(error))
        },
    }
}

pub(super) fn control_receipt_published(slots: &[Option<Entry>], parent: Token,
    worker:u64, serial:u64, cpu:i64,
) -> Result<bool> {
    let control=slots.iter().flatten().filter_map(|e|e.fork.as_ref())
        .filter_map(|f|f.control.as_ref()).find(|c|c.descriptor.identity.parent==parent.wire()
            &&c.descriptor.worker==worker&&c.descriptor.delivery==serial).ok_or(ENOENT)?;
    if control.descriptor.cpu as i64 != cpu || control.descriptor.epoch==0
        || !control.receipt.written || !control.receipt.queued
    { return Err(EACCES); }
    Ok(control.receipt.published)
}

// Select ONLY the exact authenticated control Completion. A CPU-wide generic
// next_completion could publish an unrelated return while its owner is frozen.
pub(super) fn publish_control_receipt_in_slots(remote:&Remote,slots:&mut [Option<Entry>],
    parent:Token,cpu:i32,send:impl FnOnce(&[u8;128])->Result,
) -> Result<bool> {
    let selected=slots.iter().flatten().filter_map(|e|e.fork.as_ref())
        .filter_map(|f|f.control.as_ref()).find(|c|c.descriptor.identity.parent==parent.wire()
            &&c.descriptor.cpu==cpu&&c.receipt.queued&&!c.receipt.published)
        .map(|c|c.descriptor);
    let Some(d)=selected else {return Ok(false);};
    let Some((child,actual,request))=control_receipt_snapshot(remote,slots,parent,d.worker,d.delivery,cpu as i64)?
        else{return Err(EACCES);};
    if actual!=d{return Err(EACCES);}
    let pi=slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==parent)).ok_or(ENOENT)?;
    let ci=slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==child)).ok_or(ENOENT)?;
    if pi==ci{return Err(EIO);}
    let(p,c)=if pi<ci{let(a,b)=slots.split_at_mut(ci);(a[pi].as_mut().unwrap(),b[0].as_mut().unwrap())}
        else{let(a,b)=slots.split_at_mut(pi);(b[0].as_mut().unwrap(),a[ci].as_mut().unwrap())};
    let control=c.fork.as_mut().unwrap().control.as_mut().unwrap();
    if control.quarantined||control.receipt.uncertain||!control.receipt.written
        ||control.receipt.proof.as_ref().is_none_or(|proof|proof.descriptor!=d)
        ||control.receipt.journal!=Some(control_receipt_bytes(d))
    {return Err(EBUSY);}
    p.syscalls.publish_control_observed(d.worker,d.delivery,&request,cpu,
        |packet|send(packet).map_err(|e|e.to_errno()),|actual,worker,serial|{
            // Infallible marker immediately after the real status Release and
            // response-memory release, BEFORE fallible delivery/worker work.
            if actual==&control.request&&worker==Some(d.worker)&&serial==d.delivery
                &&control.descriptor==d {control.receipt.published=true;}
        }).map_err(errno)
}

pub(super) fn has_control_completion(slots:&[Option<Entry>],parent:Token,cpu:i32)->bool{
 slots.iter().flatten().filter_map(|e|e.fork.as_ref()).filter_map(|f|f.control.as_ref())
  .any(|c|c.descriptor.identity.parent==parent.wire()&&c.descriptor.cpu==cpu
   &&c.receipt.queued&&!c.receipt.published)
}
