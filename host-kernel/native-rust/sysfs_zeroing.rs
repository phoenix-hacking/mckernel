// SPDX-License-Identifier: GPL-2.0-only
//! Exclusive detached allocator batches in the retained OS memory ledger.

use super::{errno, Memory, Span, Tagged};
use crate::{smp_image, zero_pages as wire};
use core::{
    ptr,
    sync::atomic::{AtomicI32, AtomicU64, Ordering},
};
use kernel::{bindings, prelude::*};

struct Chunk {
    tag: Tagged,
    address: u64,
    link: u64,
    bytes: usize,
    pages: i32,
}

pub(in super::super) struct Completed {
    pub(in super::super) chunks: usize,
    pub(in super::super) pages: i32,
    pub(in super::super) pending: i32,
    pub(in super::super) workers: i32,
}

impl Memory {
    /// Free chunks may coalesce across adjacent assigned extents. Validate
    /// their entire union with the existing exact-owner address checker.
    fn zero_address(&self, physical: u64, bytes: usize) -> Result<u64> {
        let span = Span::new(physical, bytes)?;
        let mut cursor = physical;
        while cursor < span.end {
            let next = self
                .extents
                .iter()
                .filter(|extent| extent.owner() == Some(self.owner) && extent.start() <= cursor)
                .filter_map(|extent| extent.end().ok())
                .filter(|end| *end > cursor)
                .max()
                .ok_or(EINVAL)?
                .min(span.end);
            self.address(cursor, usize::try_from(next - cursor).map_err(|_| EINVAL)?)?;
            cursor = next;
        }
        self.direct_map.checked_add(physical).ok_or(EINVAL)
    }

    /// # Ownership
    /// Only the retained zeroing worker may call this. All native guest pending
    /// consumers use del_all; admission required MCZB0001. A failed operation
    /// deliberately leaves every acquired ledger tag in place. Runtime then
    /// stops zeroing and retains started storage, never retrying a lost batch.
    pub(in super::super) fn zero(&self, request: wire::Request) -> Result<Completed> {
        let physical = request
            .node_physical(
                smp_image::KERNEL_BASE,
                self.layout.kernel().start(),
                smp_image::KERNEL_WINDOW_BYTES,
            )
            .map_err(errno)?;
        let address = self.zero_address(physical, wire::NODE_BYTES)?;
        let node_span = Span::new(physical, wire::NODE_BYTES)?;
        let control_span = Span::new(physical + wire::CONTROL_OFFSET, wire::CONTROL_BYTES)?;
        let mut chunks = Vec::new();
        let mut pages: i32 = 0;
        let control;
        {
            let mut ledger = self.ledger.lock();
            if ledger.conflicts(control_span, true) {
                return Err(EBUSY);
            }
            // SAFETY: The complete aligned node is in retained OS extents.
            // Its immutable ID identifies an actual boot NUMA rank. Atomic
            // controls exclude host service aliases without borrowing peer RAM.
            let id = unsafe { ptr::read_volatile(address as *const i32) };
            let workers = unsafe { AtomicI32::from_ptr((address + 40) as *mut i32) };
            if id < 0 || id as usize >= self.numa_nodes || workers.load(Ordering::Acquire) <= 0 {
                return Err(EINVAL);
            }
            control = ledger.tag(control_span)?;
            ledger.zeroing.push(control, GFP_KERNEL)?;
            // SAFETY: Exactly this scalar is the shared pending head. The
            // exchange owns all returned links; no consumer reads them before
            // taking a whole batch. Guest producers may append new batches.
            let head = unsafe { AtomicU64::from_ptr((address + 56) as *mut u64) };
            let mut link = head.swap(0, Ordering::SeqCst);
            while link != 0 {
                let chunk_physical =
                    wire::Chunk::header_physical(link, self.direct_map).map_err(errno)?;
                let header = Span::new(chunk_physical, wire::HEADER_BYTES)?;
                if header.overlaps(node_span) || ledger.conflicts(header, true) {
                    return Err(EBUSY);
                }
                let chunk_address = self.zero_address(chunk_physical, wire::HEADER_BYTES)?;
                // SAFETY: The acquired private chain owns this header. Check
                // aliases/cycles before reading it, and snapshot every field
                // before any zeroed publication can permit allocator reuse.
                let (stored_address, size, next) = unsafe {
                    (
                        ptr::read_volatile(chunk_address as *const u64),
                        ptr::read_volatile((chunk_address + 8) as *const u64),
                        ptr::read_volatile((chunk_address + wire::LINK_OFFSET) as *const u64),
                    )
                };
                let checked = wire::Chunk::decode(link, self.direct_map, stored_address, size)
                    .map_err(errno)?;
                let span = Span::new(checked.physical, checked.bytes)?;
                if span.overlaps(node_span) || ledger.conflicts(span, true) {
                    return Err(EBUSY);
                }
                let chunk_address = self.zero_address(checked.physical, checked.bytes)?;
                let tag = ledger.tag(span)?;
                ledger.zeroing.push(tag, GFP_KERNEL)?;
                pages = pages.checked_add(checked.pages).ok_or(EINVAL)?;
                chunks.push(
                    Chunk {
                        tag,
                        address: chunk_address,
                        link,
                        bytes: checked.bytes,
                        pages: checked.pages,
                    },
                    GFP_KERNEL,
                )?;
                link = next;
            }
            let pending = unsafe { AtomicI32::from_ptr((address + 44) as *mut i32) };
            if pending.load(Ordering::Acquire) < pages {
                return Err(EINVAL);
            }
        }

        // The whole chain has now been preflighted. In particular A -> B -> A
        // cannot publish/reuse A before discovering the cycle. No Linux mutex
        // or guest spinlock is held while clearing or yielding a large range.
        for chunk in &chunks {
            let mut offset = wire::HEADER_BYTES;
            while offset < chunk.bytes {
                let stop = (offset + (1 << 20)).min(chunk.bytes);
                while offset < stop {
                    // SAFETY: Complete assigned span and exclusive private
                    // ledger tag were checked above. Preserve the 48-byte
                    // metadata header; these aligned stores create no slice.
                    unsafe {
                        ptr::write_volatile((chunk.address + offset as u64) as *mut u64, 0);
                    }
                    offset += 8;
                }
                if offset < chunk.bytes {
                    unsafe {
                        bindings::msleep(1);
                    }
                }
            }
            self.publish_zero(address, control, chunk)?;
        }

        let mut ledger = self.ledger.lock();
        let index = ledger
            .zeroing
            .iter()
            .position(|old| old.serial == control.serial)
            .ok_or(EIO)?;
        let pending =
            unsafe { AtomicI32::from_ptr((address + 44) as *mut i32) }.load(Ordering::Acquire);
        let workers = unsafe { AtomicI32::from_ptr((address + 40) as *mut i32) };
        let before = workers
            .fetch_update(Ordering::SeqCst, Ordering::SeqCst, |value| {
                if value > 0 {
                    Some(value - 1)
                } else {
                    None
                }
            })
            .map_err(|_| EINVAL)?;
        // No node access may follow release of its control claim.
        ledger.zeroing.swap_remove(index);
        Ok(Completed {
            chunks: chunks.len(),
            pages,
            pending,
            workers: before - 1,
        })
    }

    fn publish_zero(&self, node_address: u64, control: Tagged, chunk: &Chunk) -> Result {
        let mut ledger = self.ledger.lock();
        if !ledger
            .zeroing
            .iter()
            .any(|old| old.serial == control.serial)
        {
            return Err(EIO);
        }
        let index = ledger
            .zeroing
            .iter()
            .position(|old| old.serial == chunk.tag.serial)
            .ok_or(EIO)?;
        let pending = unsafe { AtomicI32::from_ptr((node_address + 44) as *mut i32) };
        if pending.load(Ordering::Acquire) < chunk.pages {
            return Err(EINVAL);
        }
        // SAFETY: The node control and entire private chunk remain claimed.
        // Linux and all guest zero producers append with the same CAS ordering.
        // No old-head link is dereferenced while publishing this owned chunk.
        let head = unsafe { AtomicU64::from_ptr((node_address + 48) as *mut u64) };
        let mut first = head.load(Ordering::Acquire);
        loop {
            if first != 0 {
                let physical =
                    wire::Chunk::header_physical(first, self.direct_map).map_err(errno)?;
                self.zero_address(physical, wire::HEADER_BYTES)?;
                if ledger.conflicts(Span::new(physical, wire::HEADER_BYTES)?, true) {
                    return Err(EBUSY);
                }
            }
            unsafe {
                ptr::write_volatile((chunk.address + wire::LINK_OFFSET) as *mut u64, first);
            }
            match head.compare_exchange(first, chunk.link, Ordering::SeqCst, Ordering::SeqCst) {
                Ok(_) => break,
                Err(actual) => first = actual,
            }
        }
        // Publication permits immediate guest reuse. Everything used below is
        // private host metadata or the separately retained node control words.
        ledger.zeroing.swap_remove(index);
        pending
            .fetch_update(Ordering::SeqCst, Ordering::SeqCst, |value| {
                if value >= chunk.pages {
                    Some(value - chunk.pages)
                } else {
                    None
                }
            })
            .map_err(|_| EINVAL)?;
        Ok(())
    }
}
