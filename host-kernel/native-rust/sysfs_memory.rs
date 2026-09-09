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

struct Ledger {
    fixed: Vec<Span>,
    requests: Vec<Option<Tagged>>,
    responses: Vec<Option<Tagged>>,
    payloads: Vec<Option<Tagged>>,
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
            || snoops && self.snoops.iter().any(|old| old.span.overlaps(span))
            || self.procfs.iter().any(|old| old.span.overlaps(span))
            || self.zeroing.iter().any(|old| old.span.overlaps(span))
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
    #[pin]
    ledger: Mutex<Ledger>,
}

impl Memory {
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
        for _ in 0..capacity {
            responses.push(None, GFP_KERNEL)?;
            payloads.push(None, GFP_KERNEL)?;
        }
        let procfs = Vec::with_capacity(4096 + METADATA_CAPACITY + 2, GFP_KERNEL)?;
        Arc::pin_init(
            pin_init!(Self {
                owner, direct_map, extents, layout, numa_nodes,
                ledger <- new_mutex!(Ledger { fixed, requests, responses, payloads, snoops: Vec::new(), procfs, zeroing: Vec::new(), serial: 0 }),
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
            return Err(EBUSY);
        }
        if ledger.procfs.len() == 4096 + METADATA_CAPACITY + 2 {
            return Err(EAGAIN);
        }
        if create
            && unsafe { AtomicI32::from_ptr(address as *mut i32) }.load(Ordering::Acquire) != 0
        {
            return Err(EBUSY);
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

    pub(super) fn syscall(self: &Arc<Self>, request: &SyscallRequest) -> Result<SyscallResponse> {
        let physical = request.response();
        if physical % 8 != 0 {
            return Err(EINVAL);
        }
        let address = self.address(physical, RESPONSE_BYTES)?;
        let span = Span::new(physical, RESPONSE_BYTES)?;
        let mut ledger = self.ledger.lock();
        if ledger.conflicts(span, true) {
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
        })
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
        // The private owner excludes RELEASE publication throughout this read.
        // The terminal native answer made all of this guest page immutable.
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
        unsafe { wire::complete(self.kind, self.address as *mut u8, error, handle) }.map_err(errno)
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
}

impl SyscallResponse {
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

    pub(crate) fn pager_copy(&mut self, offset: usize, bytes: &mut [u8], to_guest: bool) -> Result {
        let (tag, address, direction) = self.payload.ok_or(EINVAL)?;
        if to_guest != direction
            || offset
                .checked_add(bytes.len())
                .is_none_or(|end| end as u64 > tag.span.end - tag.span.physical)
        {
            return Err(EINVAL);
        }
        // The mailbox's in-kernel reservation or complete transfer critical
        // section excludes completion/cancellation throughout this copy.
        // This unique payload tag excludes every other host service mapping;
        // no file operation or userspace access occurs while the caller locks it.
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
