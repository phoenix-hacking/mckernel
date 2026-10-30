// SPDX-License-Identifier: GPL-2.0-only
//! Retained guest mappings and exclusive continuing-service claims.

use super::super::{checked_guest_bytes, MemoryExtent, MemoryMap, MAX_EXTENTS};
use super::{errno, wire, OsToken, METADATA_CAPACITY};
use crate::application_syscall::{Request as SyscallRequest, ResponseMemory, RESPONSE_BYTES};
use core::{
    ptr,
    sync::atomic::{AtomicI32, AtomicU32, AtomicU64, Ordering},
};
use kernel::{
    prelude::*,
    sync::{new_mutex, Arc, Mutex},
};

#[path = "sysfs_zeroing.rs"]
mod zeroing;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct Span {
    physical: u64,
    end: u64,
}

impl Span {
    pub(super) fn new(physical: u64, bytes: usize) -> Result<Self> {
        if physical == 0 || bytes == 0 {
            return Err(EINVAL);
        }
        Ok(Self {
            physical,
            end: physical.checked_add(bytes as u64).ok_or(EINVAL)?,
        })
    }

    fn overlaps(self, other: Self) -> bool {
        self.physical < other.end && other.physical < self.end
    }
}

#[derive(Clone, Copy)]
struct Tagged {
    span: Span,
    serial: u64,
}

// Diagnostic snapshots contain only initialized, host-owned ledger fields.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ConflictKind { Fixed, Request, Payload, Response, ExecPayload, Snoop, Procfs, Zeroing }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct FailureConflict {
    kind: ConflictKind,
    slot: usize,
    member: Option<usize>,
    serial: Option<u64>,
    span: Span,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct SyscallFailureContext {
    cpu: i32, pid: i32, requester: i32, target: i32, number: u64,
    response: u64, response_end: Option<u64>,
    conflict: Option<FailureConflict>,
}

fn syscall_failure_context(request: &SyscallRequest, conflict: Option<FailureConflict>) -> SyscallFailureContext {
    SyscallFailureContext {
        cpu: request.cpu(), pid: request.pid(), requester: request.requester(),
        target: request.target(), number: request.number(),
        response: request.response(), response_end: request.response().checked_add(RESPONSE_BYTES as u64),
        conflict,
    }
}

fn log_conflict(os: u32, generation: u64, diag: u64, conflict: Option<FailureConflict>) {
    if let Some(old) = conflict {
        pr_err!("IHK-C os={} g={} d={} k={:?} i={} j={:?} s={:?}\n",
            os, generation, diag, old.kind, old.slot, old.member, old.serial);
        pr_err!("IHK-O os={} g={} d={} a={:x} b={:x}\n",
            os, generation, diag, old.span.physical, old.span.end);
    } else {
        pr_err!("IHK-C os={} g={} d={} k=none\n", os, generation, diag);
    }
}

fn log_syscall_failure(os: u32, generation: u64, diag: u64, error: Error, context: SyscallFailureContext) {
    pr_err!("IHK-E os={} g={} d={} at=syscall_claim e={}\n", os, generation, diag, error.to_errno());
    pr_err!("IHK-P os={} g={} d={} c={} p={} rq={} to={}\n",
        os, generation, diag, context.cpu, context.pid, context.requester, context.target);
    if let Some(end) = context.response_end {
        pr_err!("IHK-S os={} g={} d={} n={:x} a={:x} b={:x}\n",
            os, generation, diag, context.number, context.response, end);
    } else {
        pr_err!("IHK-S os={} g={} d={} n={:x} a={:x} b=none\n",
            os, generation, diag, context.number, context.response);
    }
    log_conflict(os, generation, diag, context.conflict);
}

struct Ledger {
    fixed: Vec<Span>,
    requests: Vec<Option<Tagged>>,
    responses: Vec<Option<Tagged>>,
    payloads: Vec<Option<Tagged>>,
    // Separate bounded per-response exec group; ordinary payload semantics stay strict.
    exec_payloads: Vec<Option<Vec<Tagged>>>,
    snoops: Vec<Tagged>,
    procfs: Vec<Tagged>,
    zeroing: Vec<Tagged>,
    serial: u64,
}

impl Ledger {
    fn conflicts(&self, span: Span, snoops: bool) -> bool {
        self.fixed.iter().any(|old| old.overlaps(span))
            || self
                .requests
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || self
                .payloads
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || self
                .responses
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || self.exec_payloads.iter().flatten().any(|group| group.iter().any(|old| old.span.overlaps(span)))
            || snoops && self.snoops.iter().any(|old| old.span.overlaps(span))
            || self.procfs.iter().any(|old| old.span.overlaps(span))
            || self.zeroing.iter().any(|old| old.span.overlaps(span))
    }

    // Read-only diagnostic traversal after the ORIGINAL conflicts predicate
    // already chose EBUSY. Keep its first-match order; never use this observer
    // to admit/reject, retire a tag, acquire a claim or interpret guest bytes.
    fn diagnostic_conflict(&self, span: Span, snoops: bool) -> Option<FailureConflict> {
        for (slot, old) in self.fixed.iter().enumerate() {
            if old.overlaps(span) {
                return Some(FailureConflict { kind: ConflictKind::Fixed, slot, member: None, serial: None, span: *old });
            }
        }
        for (kind, slots) in [(ConflictKind::Request, &self.requests), (ConflictKind::Payload, &self.payloads), (ConflictKind::Response, &self.responses)] {
            for (slot, old) in slots.iter().enumerate() {
                if let Some(old) = old {
                    if old.span.overlaps(span) {
                        return Some(FailureConflict { kind, slot, member: None, serial: Some(old.serial), span: old.span });
                    }
                }
            }
        }
        for (slot, group) in self.exec_payloads.iter().enumerate() {
            if let Some(group) = group {
                for (member, old) in group.iter().enumerate() {
                    if old.span.overlaps(span) {
                        return Some(FailureConflict { kind: ConflictKind::ExecPayload, slot, member: Some(member), serial: Some(old.serial), span: old.span });
                    }
                }
            }
        }
        for (kind, tags, enabled) in [(ConflictKind::Snoop, &self.snoops, snoops), (ConflictKind::Procfs, &self.procfs, true), (ConflictKind::Zeroing, &self.zeroing, true)] {
            if enabled {
                for (slot, old) in tags.iter().enumerate() {
                    if old.span.overlaps(span) {
                        return Some(FailureConflict { kind, slot, member: None, serial: Some(old.serial), span: old.span });
                    }
                }
            }
        }
        None
    }

    fn tag(&mut self, span: Span) -> Result<Tagged> {
        self.serial = self.serial.checked_add(1).ok_or_else(|| errno(-75))?;
        Ok(Tagged {
            span,
            serial: self.serial,
        })
    }
}

#[pin_data]
pub(super) struct Memory {
    pub(super) owner: OsToken,
    pub(super) direct_map: u64,
    extents: Vec<MemoryExtent>,
    layout: crate::smp_image::BootLayout,
    numa_nodes: usize,
    failure_contexts: AtomicU64,
    #[pin]
    ledger: Mutex<Ledger>,
}

impl Memory {
    /// Retained tags include quarantined claims and must never be discarded.
    /// Fixed mappings and extents remain owned until the runtime itself retires.
    pub(super) fn shutdown_quiescent(&self) -> Result {
        let ledger = self.ledger.lock();
        if ledger.requests.iter().any(Option::is_some)
            || ledger.responses.iter().any(Option::is_some)
            || ledger.payloads.iter().any(Option::is_some)
            || ledger.exec_payloads.iter().any(Option::is_some)
            || !ledger.snoops.is_empty()
            || !ledger.procfs.is_empty()
            || !ledger.zeroing.is_empty()
        {
            return Err(EBUSY);
        }
        Ok(())
    }

    /// # Safety
    /// Started BootStorage and its original memory/module owners must retain
    /// every supplied extent and fixed region until all returned views retire.
    /// No second dispatcher may claim these queues or metadata mappings.
    pub(super) unsafe fn new(
        map: &MemoryMap<MAX_EXTENTS>,
        owner: OsToken,
        direct_map: u64,
        layout: crate::smp_image::BootLayout,
        numa_nodes: usize,
        fixed: Vec<Span>,
    ) -> Result<Arc<Self>> {
        if layout.extent().owner() != Some(owner) || numa_nodes == 0 || numa_nodes > 512 {
            return Err(EINVAL);
        }
        let mut extents = Vec::with_capacity(map.len(), GFP_KERNEL)?;
        for index in 0..map.len() {
            let extent = map.extent(index).ok_or(EIO)?;
            if extent.owner() == Some(owner) {
                extents.push(extent, GFP_KERNEL)?;
            }
        }
        if extents.is_empty() {
            return Err(EINVAL);
        }
        for (index, span) in fixed.iter().enumerate() {
            if fixed[..index].iter().any(|old| old.overlaps(*span)) {
                return Err(EINVAL);
            }
        }
        // Heap storage avoids placing the request ledger on a kernel stack.
        let mut requests = Vec::with_capacity(METADATA_CAPACITY + 2, GFP_KERNEL)?;
        for _ in 0..METADATA_CAPACITY + 2 {
            requests.push(None, GFP_KERNEL)?;
        }
        let capacity = crate::smp_application::CAPACITY * crate::smp_application_syscall::CAPACITY;
        let mut responses = Vec::with_capacity(capacity, GFP_KERNEL)?;
        let mut payloads = Vec::with_capacity(capacity, GFP_KERNEL)?;
        let mut exec_payloads = Vec::with_capacity(capacity, GFP_KERNEL)?;
        for _ in 0..capacity {
            responses.push(None, GFP_KERNEL)?;
            payloads.push(None, GFP_KERNEL)?;
            exec_payloads.push(None, GFP_KERNEL)?;
        }
        let procfs = Vec::with_capacity(4096 + METADATA_CAPACITY + 2, GFP_KERNEL)?;
        Arc::pin_init(
            pin_init!(Self {
                owner, direct_map, extents, layout, numa_nodes,
                failure_contexts: AtomicU64::new(0),
                ledger <- new_mutex!(Ledger { fixed, requests, responses, payloads, exec_payloads, snoops: Vec::new(), procfs, zeroing: Vec::new(), serial: 0 }),
            }),
            GFP_KERNEL,
        )
    }

    pub(super) fn extents(&self) -> &[MemoryExtent] {
        &self.extents
    }

    fn address(&self, physical: u64, bytes: usize) -> Result<u64> {
        checked_guest_bytes(
            self.extents.as_slice(),
            self.owner,
            self.direct_map,
            physical,
            bytes,
        )
        .map(|value| value as u64)
    }

    pub(super) fn application_range(&self, physical: u64, bytes: usize) -> Result {
        self.address(physical, bytes)?;
        if self
            .ledger
            .lock()
            .conflicts(Span::new(physical, bytes)?, true)
        {
            return Err(EBUSY);
        }
        Ok(())
    }

    /// CREATE owns four bytes until its final done store. A returned snapshot
    /// owns complete immutable pages until RELEASE is actually published.
    pub(super) fn procfs(self: &Arc<Self>, physical: u64, create: bool) -> Result<ProcfsRegion> {
        let bytes = if create { 4 } else { 4096 };
        if physical % bytes as u64 != 0 {
            return Err(EINVAL);
        }
        let address = self.address(physical, bytes)?;
        let span = Span::new(physical, bytes)?;
        let mut ledger = self.ledger.lock();
        if ledger.conflicts(span, true) {
            self.diagnostic_conflict_failure("procfs_overlap", span,
                ledger.diagnostic_conflict(span, true), None, false, None);
            return Err(EBUSY);
        }
        if ledger.procfs.len() == 4096 + METADATA_CAPACITY + 2 {
            return Err(EAGAIN);
        }
        // SAFETY: `address` names the checked four-byte, four-byte-aligned
        // CREATE field in a retained owner extent. Holding `ledger` excludes
        // every host alias; the guest shares this field only through atomic
        // accesses, and `from_ptr` creates no borrowed reference.
        if create {
            let done = unsafe { AtomicI32::from_ptr(address as *mut i32) }.load(Ordering::Acquire);
            if done != 0 {
                if let Some(diag) = super::diagnostic_ticket(&self.failure_contexts) {
                    pr_err!("IHK-W os={} g={} d={} at=procfs_create a={:x} v={} e=-16\n",
                        self.owner.slot(), self.owner.generation(), diag, physical, done);
                }
                return Err(EBUSY);
            }
        }
        let tag = ledger.tag(span)?;
        ledger.procfs.push(tag, GFP_KERNEL)?;
        Ok(ProcfsRegion {
            memory: self.clone(),
            address,
            tag,
            create,
            active: true,
        })
    }

    /// Queue-full retains every page claim. Successful publication can make
    /// the guest free/reuse the chain immediately, even before its answer.
    /// Exclude other claims until those old host read permissions are retired.
    pub(super) fn publish_procfs_release(
        &self,
        pages: &mut [ProcfsRegion],
        send: impl FnOnce() -> Result,
    ) -> Result {
        let mut ledger = self.ledger.lock();
        for page in pages.iter() {
            if !ptr::eq(self, &*page.memory)
                || !page.active
                || page.create
                || !ledger
                    .procfs
                    .iter()
                    .any(|old| old.serial == page.tag.serial)
            {
                return Err(EIO);
            }
        }
        send()?;
        for page in pages {
            let index = ledger
                .procfs
                .iter()
                .position(|old| old.serial == page.tag.serial)
                .unwrap();
            ledger.procfs.swap_remove(index);
            page.active = false;
        }
        Ok(())
    }

    pub(super) fn application_word(&self, physical: u64) -> Result<u64> {
        if physical % 8 != 0 {
            return Err(EINVAL);
        }
        let address = self.address(physical, 8)?;
        let ledger = self.ledger.lock();
        if ledger.conflicts(Span::new(physical, 8)?, true) {
            return Err(EBUSY);
        }
        // SAFETY: Original OS pages remain owned. The ledger excludes service
        // aliases, and this aligned scalar creates no shared-memory reference.
        Ok(unsafe { ptr::read_volatile(address as *const u64) })
    }

    pub(super) fn application_copy(
        &self,
        physical: u64,
        bytes: &mut [u8],
        to_guest: bool,
    ) -> Result {
        let address = self.address(physical, bytes.len())?;
        let ledger = self.ledger.lock();
        if ledger.conflicts(Span::new(physical, bytes.len())?, true) {
            return Err(EBUSY);
        }
        for (offset, byte) in bytes.iter_mut().enumerate() {
            // SAFETY: The caller independently authorizes this prepared image
            // section, whose complete retained range was checked above. Its
            // private byte buffer never aliases the guest allocation.
            unsafe {
                let target = (address as *mut u8).add(offset);
                if to_guest {
                    ptr::write_volatile(target, *byte);
                } else {
                    *byte = ptr::read_volatile(target);
                }
            }
        }
        Ok(())
    }

    pub(super) fn claim(self: &Arc<Self>, kind: wire::Kind, physical: u64) -> Result<Claim> {
        let layout = kind.layout();
        if physical % layout.alignment as u64 != 0 {
            return Err(EINVAL);
        }
        let address = self.address(physical, layout.bytes)?;
        let span = Span::new(physical, layout.bytes)?;
        let mut ledger = self.ledger.lock();
        if ledger.conflicts(span, true) {
            return Err(EBUSY);
        }
        let slot = ledger
            .requests
            .iter()
            .position(Option::is_none)
            .ok_or(ENOMEM)?;
        // SAFETY: The complete aligned exact-generation mapping is retained,
        // and this mutex excludes every overlapping host access claim.
        let busy = unsafe { AtomicI32::from_ptr((address as *mut u8).add(layout.busy).cast()) };
        if busy.load(Ordering::Acquire) != 1 {
            return Err(EBUSY);
        }
        let tag = ledger.tag(span)?;
        ledger.requests[slot] = Some(tag);
        Ok(Claim {
            memory: self.clone(),
            kind,
            address,
            tag,
            slot,
            active: true,
        })
    }

    fn diagnostic_conflict_failure(&self, at: &'static str, span: Span,
        conflict: Option<FailureConflict>, own: Option<Tagged>, node_overlap: bool,
        route: Option<(i32, i32)>) {
        if let Some(diag) = super::diagnostic_ticket(&self.failure_contexts) {
            pr_err!("IHK-E os={} g={} d={} at={} e=-16 node={}\n",
                self.owner.slot(), self.owner.generation(), diag, at, node_overlap as u8);
            pr_err!("IHK-S os={} g={} d={} a={:x} b={:x}\n",
                self.owner.slot(), self.owner.generation(), diag, span.physical, span.end);
            if let Some((pid, cpu)) = route {
                pr_err!("IHK-P os={} g={} d={} p={} c={}\n",
                    self.owner.slot(), self.owner.generation(), diag, pid, cpu);
            }
            if let Some(own) = own {
                pr_err!("IHK-T os={} g={} d={} s={} a={:x} b={:x}\n",
                    self.owner.slot(), self.owner.generation(), diag, own.serial, own.span.physical, own.span.end);
            }
            log_conflict(self.owner.slot(), self.owner.generation(), diag, conflict);
        }
    }

    fn diagnostic_completion_failure(&self, kind: wire::Kind, tag: Tagged, operation_error: i32, busy: i32) {
        if let Some(diag) = super::diagnostic_ticket(&self.failure_contexts) {
            pr_err!("IHK-M os={} g={} d={} k={:?} busy={} op_e={} e=-16\n",
                self.owner.slot(), self.owner.generation(), diag, kind, busy, operation_error);
            pr_err!("IHK-T os={} g={} d={} s={} a={:x} b={:x}\n",
                self.owner.slot(), self.owner.generation(), diag, tag.serial, tag.span.physical, tag.span.end);
        }
    }

    pub(super) fn syscall(self: &Arc<Self>, request: &SyscallRequest) -> Result<SyscallResponse> {
        let mut conflict = None;
        let result = (|| {
            let physical = request.response();
            if physical % 8 != 0 {
                return Err(EINVAL);
            }
            let address = self.address(physical, RESPONSE_BYTES)?;
            let span = Span::new(physical, RESPONSE_BYTES)?;
            let mut ledger = self.ledger.lock();
            if ledger.conflicts(span, true) {
                conflict = ledger.diagnostic_conflict(span, true);
                return Err(EBUSY);
            }
            let slot = ledger
                .responses
                .iter()
                .position(Option::is_none)
                .ok_or(EAGAIN)?;
            // SAFETY: The checked exact-generation RAM is aligned and disjoint
            // from every active service access. The guest owns only atomic state.
            let status = unsafe { AtomicU64::from_ptr((address as *mut u8).add(8).cast()) };
            // SAFETY: The same retained, response-sized mapping covers the
            // eight-byte-aligned state word at offset 16. The held ledger claim
            // excludes host aliases, while the guest accesses this shared word
            // atomically; this creates no Rust reference to guest memory.
            let state = unsafe { AtomicU64::from_ptr((address as *mut u8).add(16).cast()) };
            if status.load(Ordering::Acquire) != 0 || !matches!(state.load(Ordering::Acquire), 0 | 2) {
                return Err(errno(-71));
            }
            let tag = ledger.tag(span)?;
            ledger.responses[slot] = Some(tag);
            Ok(SyscallResponse {
                memory: self.clone(),
                address,
                tag,
                slot,
                payload: None,
                exec_group: None,
            })
        
        })();
        // The original ledger guard has ended. The copied snapshot has no
        // borrowed tag/pointer, and this diagnostic runs BEFORE returning the
        // same error to the unchanged mailbox/Remote quarantine path.
        if let Err(error) = &result {
            if *error != EAGAIN {
                if let Some(diag) = super::diagnostic_ticket(&self.failure_contexts) {
                    log_syscall_failure(self.owner.slot(), self.owner.generation(), diag,
                        *error, syscall_failure_context(request, conflict));
                }
            }
        }
        result
    }

    /// Reserve queue aliases while the caller allocates and stores both owned
    /// endpoints. This lock never spans a remote callback or response wait.
    pub(super) fn connect(
        &self,
        physical: u64,
        bytes: usize,
        make: impl FnOnce() -> Result<super::AcceptSuccess>,
    ) -> Result<super::AcceptSuccess> {
        self.address(physical, bytes)?;
        let span = Span::new(physical, bytes)?;
        let mut ledger = self.ledger.lock();
        if ledger.conflicts(span, true) {
            return Err(EBUSY);
        }
        // Reserve both vector slots before any endpoint is installed. The
        // duplicate is a private placeholder while the ledger stays locked.
        ledger.fixed.push(span, GFP_KERNEL)?;
        if let Err(error) = ledger.fixed.push(span, GFP_KERNEL) {
            ledger.fixed.pop();
            return Err(error.into());
        }
        match make() {
            Ok(result) => {
                // The backend's fresh BootPages allocation is nonzero, bounded
                // and disjoint from all other allocations before installation.
                let host = Span::new(result.receive_queue, bytes)?;
                *ledger.fixed.last_mut().ok_or(EIO)? = host;
                Ok(result)
            }
            Err(error) => {
                ledger.fixed.pop();
                ledger.fixed.pop();
                Err(error)
            }
        }
    }

    fn descriptor(&self, physical: u64) -> Result<(i32, u64)> {
        let address = self.address(physical, 16)?;
        let span = Span::new(physical, 16)?;
        let ledger = self.ledger.lock();
        if ledger.conflicts(span, false) {
            return Err(EBUSY);
        }
        let mut bytes = [0u8; 16];
        for (index, byte) in bytes.iter_mut().enumerate() {
            // SAFETY: The transient descriptor is fully checked and disjoint
            // from writers. Copy all input before releasing the ledger lock.
            *byte = unsafe { ptr::read_volatile((address as *const u8).add(index)) };
        }
        Ok((
            i32::from_le_bytes(bytes[..4].try_into().unwrap()),
            u64::from_le_bytes(bytes[8..].try_into().unwrap()),
        ))
    }

    fn snoop(self: &Arc<Self>, physical: u64, bytes: usize) -> Result<Region> {
        let address = self.address(physical, bytes)?;
        let span = Span::new(physical, bytes)?;
        let mut ledger = self.ledger.lock();
        // Read-only snoops may share data with each other. They may never
        // alias a queue, response page or a pending metadata request.
        if ledger.conflicts(span, false) {
            return Err(EBUSY);
        }
        let tag = ledger.tag(span)?;
        ledger.snoops.push(tag, GFP_KERNEL)?;
        Ok(Region {
            memory: self.clone(),
            address,
            bytes,
            tag,
        })
    }
}

/// Unfinished destruction leaves its exact ledger tag quarantined. Started OS
/// storage retains the physical RAM; Drop never dereferences the peer address.
pub(super) struct ProcfsRegion {
    memory: Arc<Memory>,
    address: u64,
    tag: Tagged,
    create: bool,
    active: bool,
}

impl ProcfsRegion {
    pub(super) fn read(&self, offset: usize, output: &mut [u8]) -> Result {
        if !self.active
            || self.create
            || offset
                .checked_add(output.len())
                .is_none_or(|end| end > 4096)
        {
            return Err(EINVAL);
        }
        // SAFETY: This live non-CREATE region retains a checked 4096-byte
        // mapping, and its private ledger claim excludes RELEASE and all host
        // aliases. The terminal native answer makes the guest page immutable;
        // the bounded byte offset is valid and creates no shared reference.
        for (index, byte) in output.iter_mut().enumerate() {
            *byte = unsafe { ptr::read_volatile((self.address as *const u8).add(offset + index)) };
        }
        Ok(())
    }

    pub(super) fn created(mut self) -> Result {
        let mut ledger = self.memory.ledger.lock();
        if !self.active || !self.create {
            return Err(EINVAL);
        }
        let index = ledger
            .procfs
            .iter()
            .position(|old| old.serial == self.tag.serial)
            .ok_or(EIO)?;
        ledger.procfs.swap_remove(index);
        self.active = false;
        // SAFETY: The exact aligned CREATE claim is still excluded. Namespace
        // publication succeeded before this final store; no peer access follows.
        unsafe { AtomicI32::from_ptr(self.address as *mut i32) }.store(1, Ordering::Release);
        Ok(())
    }
}

/// A unique ingress claim. Completion retires it before the final busy store
/// while keeping the ledger locked, so immediate peer reuse cannot see a stale
/// claim. No method can acquire another claim while this one is completing.
pub(super) struct Claim {
    memory: Arc<Memory>,
    kind: wire::Kind,
    address: u64,
    tag: Tagged,
    slot: usize,
    active: bool,
}

impl Claim {
    pub(super) fn snapshot(&self) -> Result<wire::Request> {
        // SAFETY: This unique claim retains and excludes the whole descriptor;
        // the protocol peer leaves its inputs immutable until busy becomes zero.
        unsafe { wire::read(self.kind, self.address as *mut u8) }.map_err(errno)
    }

    pub(super) fn descriptor(&self, physical: u64) -> Result<(i32, u64)> {
        self.memory.descriptor(physical)
    }

    pub(super) fn snoop(&self, physical: u64, bytes: usize) -> Result<Region> {
        self.memory.snoop(physical, bytes)
    }

    fn finish(&mut self, error: i32, handle: Option<u64>) -> Result {
        let mut ledger = self.memory.ledger.lock();
        let entry = ledger.requests.get_mut(self.slot).ok_or(EIO)?;
        if !self.active
            || entry
                .as_ref()
                .is_none_or(|tag| tag.serial != self.tag.serial)
        {
            return Err(EIO);
        }
        *entry = None;
        self.active = false;
        // SAFETY: The unique original claim is still excluded by the ledger
        // lock. Completion writes error/handle before its final release store;
        // no guest memory is accessed by us after that store.
        unsafe { wire::complete_observed(self.kind, self.address as *mut u8, error, handle, |busy| {
            // This is the original failed busy load, under the still-held
            // exclusive ledger mutex, before any final store or peer reuse.
            self.memory.diagnostic_completion_failure(busy.kind, self.tag, error, busy.value);
        }) }.map_err(errno)
    }

    pub(super) fn complete(mut self, result: Result<Option<u64>>) -> Result {
        match result {
            Ok(handle) => self.finish(0, handle),
            Err(error) => self.finish(error.to_errno(), None),
        }
    }
}

impl Drop for Claim {
    fn drop(&mut self) {
        if self.active {
            if let Err(error) = self.finish(EIO.to_errno(), None) {
                pr_err!(
                    "IHK-SMP: sysfs abandoned request completion failed errno={}\n",
                    error.to_errno()
                );
            }
        }
    }
}


// UNWIRED real ledger implementation. Constructor is private to original
// SyscallResponse; scalar keys alone cannot create a group or mapping owner.
struct ExecMapping { tag: Tagged, address: u64 }
pub(crate) struct ExecClaimGroup {
    memory: Arc<Memory>, slot: usize, key: crate::exec_transfer_checked::ExecKey,
    descriptor: crate::exec_transfer_checked::Step,
    mappings: Vec<ExecMapping>, reserved: bool,
}
// SAFETY: SyscallResponse exclusively constructs/holds this group after its
// exact descriptor payload claim. Original Response owns both. Every section
// claim is atomically published in the same Memory ledger, and only original
// ResponseMemory::release removes it after real final status publication.
// Unfinished drop preserves tags; continuing Runtime/BootStorage retain RAM.
unsafe impl crate::exec_transfer_checked::ResponseOwnedExecClaims for ExecClaimGroup {
    fn key(&self)->crate::exec_transfer_checked::ExecKey {self.key}
    fn descriptor(&self)->crate::exec_transfer_checked::Step {self.descriptor}
    fn reserve_sections(&mut self, sections:&[crate::exec_transfer_checked::Section])->core::result::Result<(),i32> {
        self.reserve_all(sections).map_err(|e|e.to_errno())
    }
}
impl ExecClaimGroup {
    fn reserve_all(&mut self, sections:&[crate::exec_transfer_checked::Section])->Result {
        if self.reserved || sections.len()>crate::application_image::MAX_SECTIONS {return Err(EINVAL);}
        // Allocate every fallible vector before publishing ANY new claim.
        let mut mappings=Vec::with_capacity(sections.len(),GFP_KERNEL)?;
        let mut tags=Vec::with_capacity(sections.len(),GFP_KERNEL)?;
        let mut ledger=self.memory.ledger.lock();
        if ledger.responses[self.slot].as_ref().map(|t|t.serial)!=Some(self.key.response_serial)
            || ledger.exec_payloads[self.slot].is_some() {return Err(EBUSY);}
        let descriptor=ledger.payloads[self.slot].ok_or(EIO)?;
        if descriptor.span.physical!=self.descriptor.physical
            || descriptor.span.end-descriptor.span.physical!=self.descriptor.bytes as u64 {return Err(EACCES);}
        for section in sections {
            if section.pages==0 {continue;}
            let bytes=section.pages.checked_mul(4096).and_then(|n|usize::try_from(n).ok()).ok_or(EINVAL)?;
            let span=Span::new(section.physical,bytes)?;
            let address=self.memory.address(section.physical,bytes)?;
            if section.physical%4096!=0 || ledger.conflicts(span,true)
                || tags.iter().any(|old:&Tagged|old.span.overlaps(span)) {return Err(EBUSY);}
            let tag=ledger.tag(span)?;
            tags.push(tag,GFP_KERNEL)?;
            mappings.push(ExecMapping{tag,address},GFP_KERNEL)?;
        }
        // Infallible single ownership publication after all validation and
        // allocations. A failure above may consume serials, never a claim.
        ledger.exec_payloads[self.slot]=Some(tags);
        self.mappings=mappings;self.reserved=true;Ok(())
    }
}

/// Only completed response publication removes this exact ledger tag. Dropping
/// an unfinished capability leaves its span excluded; the continuing Runtime
/// and original started BootStorage retain all RAM/module owners in quarantine.
pub(crate) struct SyscallResponse {
    memory: Arc<Memory>,
    address: u64,
    tag: Tagged,
    slot: usize,
    // Same slot in a distinct ledger: this capability outlives all page I/O
    // and stays excluded until the response's actual final publication.
    payload: Option<(Tagged, u64, bool)>,
    exec_group: Option<ExecClaimGroup>,
}

impl SyscallResponse {

    pub(crate) fn prepare_exec_delivery(&mut self,request:&SyscallRequest,application:u64,worker:u64,delivery:u64)->core::result::Result<crate::exec_delivery::ExecDelivery,i32>{
        use crate::exec_transfer_checked::{ExecKey,Phase2};
        let key=ExecKey{os_slot:self.memory.owner.slot(),os_generation:self.memory.owner.generation(),application,worker,delivery,response_serial:self.tag.serial,response_physical:self.tag.span.physical};
        if request.number()!=59||request.response()!=key.response_physical||application==0||worker==0||delivery==0{return Err(-22);}
        if request.arguments()[0]==1{return Ok(crate::exec_delivery::ExecDelivery::phase1(key));}
        let mut plan=Phase2::begin(request,key)?;let step=plan.expected(request,key)?.ok_or(-22)?;
        let mut snapshot=Vec::with_capacity(step.bytes,GFP_KERNEL).map_err(|_|-12)?;
        for _ in 0..step.bytes{snapshot.push(0,GFP_KERNEL).map_err(|_|-12)?;}
        self.prepare_exec_descriptor(request,key).map_err(|e|e.to_errno())?;
        self.pager_copy(0,&mut snapshot,false).map_err(|e|e.to_errno())?;
        plan.stage_descriptor(request,key,&snapshot)?;
        plan.reserve_sections(self.exec_claim_group().map_err(|e|e.to_errno())?)?;
        Ok(crate::exec_delivery::ExecDelivery::phase2(key,plan,snapshot))
    }
    pub(crate) fn copy_exec_delivery(&mut self,request:&SyscallRequest,key:crate::exec_transfer_checked::ExecKey,step:crate::exec_transfer_checked::Step,bytes:&mut[u8])->core::result::Result<(),i32>{
        if key.os_slot!=self.memory.owner.slot()||key.os_generation!=self.memory.owner.generation()||key.response_serial!=self.tag.serial||key.response_physical!=self.tag.span.physical{return Err(-13);}
        if request.arguments()[0]==1{
            crate::exec_transfer_checked::phase1_upload(request,step,bytes)?;
            self.prepare_payload(step.physical,step.bytes,true).map_err(|e|e.to_errno())?;
            self.pager_copy(0,bytes,true).map_err(|e|e.to_errno())
        }else{self.copy_exec_page(key,step,bytes).map_err(|e|e.to_errno())}
    }


    /// Called only under the original authenticated mailbox delivery guard.
    /// Key OS/response fields come from these actual retained owners; numeric
    /// application/worker/delivery fields must already match that mailbox.
    pub(crate) fn prepare_exec_descriptor(&mut self,request:&SyscallRequest,
        key:crate::exec_transfer_checked::ExecKey)->Result {
        use crate::exec_transfer_checked::{Phase2,Step};
        if key.os_slot!=self.memory.owner.slot() || key.os_generation!=self.memory.owner.generation()
            || key.response_serial!=self.tag.serial || key.response_physical!=self.tag.span.physical
            || request.response()!=self.tag.span.physical || self.exec_group.is_some() {return Err(EACCES);}
        let plan=Phase2::begin(request,key).map_err(errno)?;
        let descriptor=plan.expected(request,key).map_err(errno)?.ok_or(EINVAL)?;
        if descriptor.direction!=1 {return Err(EINVAL);}
        self.prepare_payload(descriptor.physical,descriptor.bytes,false)?;
        self.exec_group=Some(ExecClaimGroup{memory:self.memory.clone(),slot:self.slot,key,
            descriptor:Step{..descriptor},mappings:Vec::new(),reserved:false});Ok(())
    }
    pub(crate) fn exec_claim_group(&mut self)->Result<&mut ExecClaimGroup> {
        self.exec_group.as_mut().ok_or(EINVAL)
    }
    /// Exact cursor check is an additional mandatory caller prerequisite.
    /// This primitive confers no page-order or successful-RET authority.
    pub(crate) fn copy_exec_page(&mut self,key:crate::exec_transfer_checked::ExecKey,
        step:crate::exec_transfer_checked::Step,bytes:&mut[u8])->Result {
        let group=self.exec_group.as_ref().ok_or(EINVAL)?;
        if group.key!=key || !group.reserved || step.direction!=0 || step.bytes!=4096
            || bytes.len()!=4096 || step.physical%4096!=0 {return Err(EACCES);}
        let last=step.physical.checked_add(4096).ok_or(EINVAL)?;
        let mapping=group.mappings.iter().find(|m|step.physical>=m.tag.span.physical&&last<=m.tag.span.end).ok_or(EACCES)?;
        let offset=usize::try_from(step.physical-mapping.tag.span.physical).map_err(|_|EINVAL)?;
        for(i,byte)in bytes.iter().enumerate(){
            // SAFETY: exact original-response group retains the whole checked,
            // disjoint extent; mailbox guard excludes cancellation/publication.
            unsafe {ptr::write_volatile((mapping.address as *mut u8).add(offset+i),*byte)};
        }Ok(())
    }

    pub(crate) fn validate_fork_root(&self,request:&SyscallRequest,root:u64)->Result {
        if request.number()!=56||request.arguments()[3]!=root||root==0||root%4096!=0{return Err(EACCES);}
        // Range/mapping validation is subordinate to the actual retained
        // original delivery/child-credit/root owner. It grants no authority.
        self.memory.address(root,4096)?;Ok(())
    }
    fn read_current_fork_carrier(&mut self,request:&SyscallRequest)->Result<[u8;128]> {
        let args=request.arguments();
        if request.number()!=56||args[5]!=0x313030434b46434d{return Err(EACCES);}
        if self.payload.is_none(){self.prepare_payload(args[4],128,true)?;}
        let(tag,address,writable)=self.payload.ok_or(EIO)?;
        if !writable||tag.span.physical!=args[4]
            ||tag.span.end.checked_sub(tag.span.physical)!=Some(128){return Err(EACCES);}
        // The same exclusive response-owned span permits both initial reads
        // and the eventual first receipt write; ordinary pager rights remain
        // unchanged. No peer byte is written before the original RET is bound.
        let mut bytes=[0;128];
        for(i,b)in bytes.iter_mut().enumerate(){*b=unsafe {ptr::read_volatile((address as *const u8).add(i))};}
        Ok(bytes)
    }
    pub(crate) fn current_fork_carrier(&mut self,request:&SyscallRequest)->Result<u64> {
        let bytes=self.read_current_fork_carrier(request)?;
        request.current_fork_carrier(&bytes).map_err(errno)
    }
    pub(crate) fn write_first_fork_receipt(&mut self,request:&SyscallRequest,
        receipt:&crate::application_syscall::ForkFirstReceipt)->Result {
        let nonce=self.current_fork_carrier(request)?;
        if nonce!=receipt.nonce{return Err(EACCES);}
        let mut bytes=request.first_fork_receipt(receipt).map_err(errno)?;
        self.pager_copy(0,&mut bytes,true)
    }

    pub(crate) fn current_fork_control_frame(&mut self,request:&SyscallRequest)->Result<[u8;128]> {
        let a=request.arguments();
        if request.number()!=56||!matches!(a[0],2|3)||a[5]!=0x313030434b46434d{return Err(EACCES);}
        self.read_current_fork_carrier(request)
    }
    pub(crate) fn write_fork_control_frame(&mut self,bytes:&mut[u8;128])->Result {
        self.pager_copy(0,bytes,true)
    }

    pub(crate) fn prepare_pager(&mut self, request: &SyscallRequest) -> Result {
        let operation = crate::application_pager::Operation::decode(request).map_err(errno)?;
        let Some((physical, bytes, to_guest)) = operation.payload() else {
            return Ok(());
        };
        self.prepare_payload(physical, bytes, to_guest)
    }

    fn prepare_payload(&mut self, physical: u64, bytes: usize, to_guest: bool) -> Result {
        if self.payload.is_some() {
            return Err(EBUSY);
        }
        let address = self.memory.address(physical, bytes)?;
        let span = Span::new(physical, bytes)?;
        let mut ledger = self.memory.ledger.lock();
        if ledger.payloads[self.slot].is_some() || ledger.conflicts(span, true) {
            return Err(EBUSY);
        }
        let tag = ledger.tag(span)?;
        ledger.payloads[self.slot] = Some(tag);
        self.payload = Some((tag, address, to_guest));
        Ok(())
    }

    pub(crate) fn copy_tids(&mut self, request: &SyscallRequest, bytes: &mut [u8]) -> Result {
        let (physical, length) = request.tid_buffer().map_err(errno)?;
        if length != bytes.len() as u64 {
            return Err(EINVAL);
        }
        self.prepare_payload(physical, bytes.len(), true)?;
        self.pager_copy(0, bytes, true)
    }

    /// Private candidate: invoked only with the original Delivered request
    /// under the application mailbox lock; this is not a public physical map.
    #[cfg(m14_getcred_private_candidate)]
    pub(crate) fn copy_credentials(&mut self, request: &SyscallRequest, physical: u64,
        bytes: &mut [u8]) -> Result {
        if request.number() != 122 || request.arguments()[1] != 1
            || request.arguments()[0] != physical || physical == 0
            || physical % 4 != 0 || physical % 4096 > 4096 - 32 || bytes.len() != 32
            || physical.checked_add(32).is_none() { return Err(EINVAL); }
        // One-page range remains within one original page-aligned PageOwner;
        // the retained Memory owner and ledger also cover its entire extent.
        self.prepare_payload(physical, 32, true)?;
        self.pager_copy(0, bytes, true)
    }

    pub(crate) fn pager_copy(&mut self, offset: usize, bytes: &mut [u8], to_guest: bool) -> Result {
        let (tag, address, direction) = self.payload.ok_or(EINVAL)?;
        if to_guest != direction
            || offset
                .checked_add(bytes.len())
                .is_none_or(|end| end as u64 > tag.span.end - tag.span.physical)
        {
            return Err(EINVAL);
        }
        // SAFETY: The bounded offset lies in the retained payload span. The
        // mailbox reservation or complete-transfer critical section excludes
        // completion and cancellation, and its unique tag excludes every host
        // mapping; byte accesses need no stronger alignment or Rust reference.
        for (index, byte) in bytes.iter_mut().enumerate() {
            unsafe {
                let pointer = (address as *mut u8).add(offset + index);
                if to_guest {
                    ptr::write_volatile(pointer, *byte);
                } else {
                    *byte = ptr::read_volatile(pointer);
                }
            }
        }
        Ok(())
    }
}

// SAFETY: Memory::syscall is the only constructor. It validates the complete
// retained mapping and excludes aliases under the shared ledger. Unfinished
// destruction does not remove the tag or acknowledge the guest.
unsafe impl ResponseMemory for SyscallResponse {
    fn physical(&self) -> u64 {
        self.tag.span.physical
    }
    fn address(&mut self) -> *mut u8 {
        self.address as *mut u8
    }
    unsafe fn release(self) {
        let mut ledger = self.memory.ledger.lock();
        let slot = &mut ledger.responses[self.slot];
        assert!(slot
            .as_ref()
            .is_some_and(|tag| tag.serial == self.tag.serial));
        *slot = None;
        if let Some((tag, _, _)) = self.payload {
            assert!(ledger.payloads[self.slot]
                .as_ref()
                .is_some_and(|old| old.serial == tag.serial));
            ledger.payloads[self.slot] = None;
        }
        if let Some(group)=self.exec_group {
            let retained=ledger.exec_payloads[self.slot].as_ref();
            if group.reserved {
                let retained=retained.expect("exec claims lost before RET");
                assert!(retained.len()==group.mappings.len());
                for(old,mapping)in retained.iter().zip(group.mappings.iter()) {assert!(old.serial==mapping.tag.serial);}
                ledger.exec_payloads[self.slot]=None;
            } else {assert!(retained.is_none());}
        }
        // The guest can already reuse the response; only host bookkeeping is
        // accessed above. No destructor dereferences its address.
    }
}

/// Its final drop occurs only after Linux drains every attribute callback.
pub(super) struct Region {
    memory: Arc<Memory>,
    address: u64,
    bytes: usize,
    tag: Tagged,
}

impl Region {
    /// One coherent native-width scalar load, without ordering other fields.
    pub(super) fn number(&self) -> Result<u64> {
        match self.bytes {
            4 if self.address % 4 == 0 => {
                // SAFETY: The checked, retained RAM covers this aligned word.
                // The guest publishes native-width scalar values; an atomic
                // load cannot combine bytes from different such stores.
                Ok(
                    unsafe { AtomicU32::from_ptr(self.address as *mut u32) }.load(Ordering::Relaxed)
                        as u64,
                )
            }
            8 if self.address % 8 == 0 => {
                // SAFETY: As above, for a complete aligned 64-bit RAM value.
                Ok(
                    unsafe { AtomicU64::from_ptr(self.address as *mut u64) }
                        .load(Ordering::Relaxed),
                )
            }
            _ => Err(EINVAL),
        }
    }

    pub(super) fn copy(&self, output: &mut [u8]) -> Result {
        if output.len() > self.bytes {
            return Err(EINVAL);
        }
        for (index, byte) in output.iter_mut().enumerate() {
            // SAFETY: The exact retained region excludes every host writer;
            // all reads are bounded and create no references to peer memory.
            *byte = unsafe { ptr::read_volatile((self.address as *const u8).add(index)) };
        }
        Ok(())
    }
}

impl Drop for Region {
    fn drop(&mut self) {
        let mut ledger = self.memory.ledger.lock();
        if let Some(index) = ledger
            .snoops
            .iter()
            .position(|tag| tag.serial == self.tag.serial)
        {
            ledger.snoops.remove(index);
        }
    }
}
