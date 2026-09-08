// SPDX-License-Identifier: GPL-2.0-only
//! Retained guest mappings and exclusive claims for continuing sysfs requests.

use super::super::{checked_guest_bytes, MemoryExtent, MemoryMap, MAX_EXTENTS};
use super::{errno, wire, OsToken, METADATA_CAPACITY};
use core::{
    ptr,
    sync::atomic::{AtomicI32, AtomicU32, AtomicU64, Ordering},
};
use kernel::{
    prelude::*,
    sync::{new_mutex, Arc, Mutex},
};

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
    snoops: Vec<Tagged>,
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
            || snoops && self.snoops.iter().any(|old| old.span.overlaps(span))
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
        fixed: Vec<Span>,
    ) -> Result<Arc<Self>> {
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
        Arc::pin_init(
            pin_init!(Self {
                owner, direct_map, extents,
                ledger <- new_mutex!(Ledger { fixed, requests, snoops: Vec::new(), serial: 0 }),
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
                Ok(unsafe { AtomicU32::from_ptr(self.address as *mut u32) }
                    .load(Ordering::Relaxed) as u64)
            }
            8 if self.address % 8 == 0 => {
                // SAFETY: As above, for a complete aligned 64-bit RAM value.
                Ok(unsafe { AtomicU64::from_ptr(self.address as *mut u64) }
                    .load(Ordering::Relaxed))
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
