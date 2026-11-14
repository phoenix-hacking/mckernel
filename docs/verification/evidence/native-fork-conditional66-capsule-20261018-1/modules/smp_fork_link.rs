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
        let parent_refs = p.fork_prepared_parent_refs.checked_add(1).ok_or_else(|| errno(-75))?;
        let c = slots[ci].as_mut().unwrap();
        if c.closed || c.needs_cleanup || c.quarantined || c.prepare.is_some() { return Err(EBUSY); }
        if c.owner_slot != self.owner.slot() as i32 || c.owner_generation != self.owner.generation() { return Err(EACCES); }
        let child = c.key();
        let fork = c.fork.as_mut().unwrap();
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
            record.last_sequence = record.last_sequence.checked_add(1).ok_or_else(|| errno(-75))?;
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
