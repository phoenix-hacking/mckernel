// SPDX-License-Identifier: GPL-2.0
//! Allocation-free ownership transfer for raw-address page-allocation adapters.
//!
//! The legacy IHK ABI returns physical addresses and later accepts an address
//! for release.  This source-only substrate retains each `PageAllocation`
//! lease in a fixed-capacity slot while such an address is outside Rust.  A
//! non-wrapping module-lifetime registry identity and a checked per-slot
//! generation make the typed handle path reject stale, foreign, and
//! double-release attempts.
//!
//! This registry deliberately has no internal lock.  Kernel integration must
//! hold one audited irqsave-equivalent outer lock across every operation and
//! `Drop`, with local IRQs disabled, preemption disabled, no sleeping, and no
//! same-CPU re-entry.  That lock must also serialize the backing allocator.

use core::cell::Cell;
use core::marker::PhantomData;
use core::sync::atomic::{AtomicU64, Ordering};

use crate::page_allocator::{BitmapPageAllocator, PageAllocation, PageAllocatorError, PageRange};

static NEXT_REGISTRY_ID: AtomicU64 = AtomicU64::new(1);

/// Frozen ownership-transfer outcomes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum RawPageOwnerError {
    /// Capacity, registry identity, or allocation input is invalid.
    Invalid,
    /// Every usable registry slot currently owns a live allocation.
    Full,
    /// The process-wide registry identity sequence cannot advance without wrap.
    RegistryIdentityExhausted,
    /// Every free slot has exhausted its non-wrapping generation space.
    GenerationExhausted,
    /// No live allocation begins at the supplied physical address.
    UnknownAddress,
    /// Address, block count, or copied handle metadata does not match ownership.
    Ownership,
    /// A handle belongs to another registry or an old slot generation.
    StaleHandle,
    /// The exact current-generation handle has already been released.
    DoubleFree,
    /// The backing allocator rejected an allocate or release transaction.
    Allocator(PageAllocatorError),
}

impl From<PageAllocatorError> for RawPageOwnerError {
    fn from(error: PageAllocatorError) -> Self {
        Self::Allocator(error)
    }
}

/// Generation-aware proof that one registry slot owns an allocation lease.
///
/// The copied address is usable only while this handle still names the live
/// generation in its originating registry.  Callers must not treat the handle
/// itself as extending the lifetime of the registry or backing allocator.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[must_use = "discarding this handle loses the generation-aware release proof"]
pub(crate) struct RawPageAllocationHandle {
    registry_id: u64,
    slot: usize,
    generation: u64,
    range: PageRange,
}

impl RawPageAllocationHandle {
    pub(crate) const fn registry_id(self) -> u64 {
        self.registry_id
    }

    pub(crate) const fn generation(self) -> u64 {
        self.generation
    }

    pub(crate) const fn address(self) -> u64 {
        self.range.address()
    }

    pub(crate) const fn blocks(self) -> usize {
        self.range.blocks()
    }

    pub(crate) const fn bytes(self) -> u64 {
        self.range.bytes()
    }
}

pub(crate) struct RawPageOwnerSlot<'allocator, 'storage> {
    generation: u64,
    allocation: Option<PageAllocation<'allocator, 'storage>>,
}

impl RawPageOwnerSlot<'_, '_> {
    /// Construct caller-owned empty slot storage.
    pub(crate) const fn empty() -> Self {
        Self {
            generation: 0,
            allocation: None,
        }
    }
}

/// Fixed-capacity store for allocation leases held across a raw-address ABI.
///
/// Identities come from one non-wrapping atomic sequence for the loaded module
/// instance. All mutation requires `&mut self`; a future kernel adapter must
/// provide the irqsave/nonpreemptible/no-sleep serialization described in this
/// module's safety contract. Slot storage must be pinned before construction
/// and outlive the registry; a future owner must drain it before module teardown.
#[must_use = "dropping the registry releases every allocation lease it retains"]
pub(crate) struct RawPageOwnerRegistry<'slots, 'allocator, 'storage> {
    registry_id: u64,
    allocator: &'allocator BitmapPageAllocator<'storage>,
    slots: &'slots mut [RawPageOwnerSlot<'allocator, 'storage>],
    // The registry cannot be directly shared as Sync. A future adapter must
    // place it behind the single audited irqsave-equivalent owner lock.
    _not_sync: PhantomData<Cell<()>>,
}

impl<'slots, 'allocator, 'storage> RawPageOwnerRegistry<'slots, 'allocator, 'storage> {
    /// Construct a registry over caller-owned, preallocated slot storage.
    pub(crate) fn new(
        allocator: &'allocator BitmapPageAllocator<'storage>,
        slots: &'slots mut [RawPageOwnerSlot<'allocator, 'storage>],
    ) -> Result<Self, RawPageOwnerError> {
        if slots.is_empty() || slots.iter().any(|slot| slot.allocation.is_some()) {
            return Err(RawPageOwnerError::Invalid);
        }
        let registry_id = next_registry_id()?;
        Ok(Self {
            registry_id,
            allocator,
            slots,
            _not_sync: PhantomData,
        })
    }

    pub(crate) fn capacity(&self) -> usize {
        self.slots.len()
    }

    pub(crate) fn active_count(&self) -> usize {
        self.slots
            .iter()
            .filter(|slot| slot.allocation.is_some())
            .count()
    }

    /// Allocate units and retain the returned lease in a generation slot.
    pub(crate) fn allocate(
        &mut self,
        blocks: usize,
    ) -> Result<RawPageAllocationHandle, RawPageOwnerError> {
        let (slot, generation) = self.next_slot()?;
        let allocator: &'allocator BitmapPageAllocator<'storage> = self.allocator;
        let allocation = allocator.allocate(blocks)?;
        Ok(self.commit(slot, generation, allocation))
    }

    /// Allocate aligned bytes and retain the returned lease in a generation slot.
    pub(crate) fn allocate_bytes(
        &mut self,
        bytes: u64,
        alignment_bytes: u64,
    ) -> Result<RawPageAllocationHandle, RawPageOwnerError> {
        let (slot, generation) = self.next_slot()?;
        let allocator: &'allocator BitmapPageAllocator<'storage> = self.allocator;
        let allocation = allocator.allocate_bytes(bytes, alignment_bytes)?;
        Ok(self.commit(slot, generation, allocation))
    }

    /// Release the exact live generation represented by `handle`.
    ///
    /// The slot is cleared only after `PageAllocation::try_release` succeeds;
    /// an allocator error therefore leaves the same lease available for retry.
    pub(crate) fn release(
        &mut self,
        handle: RawPageAllocationHandle,
    ) -> Result<(), RawPageOwnerError> {
        if handle.registry_id != self.registry_id || handle.generation == 0 {
            return Err(RawPageOwnerError::StaleHandle);
        }
        let slot = self
            .slots
            .get_mut(handle.slot)
            .ok_or(RawPageOwnerError::StaleHandle)?;
        if slot.generation != handle.generation {
            return Err(RawPageOwnerError::StaleHandle);
        }
        let allocation = slot
            .allocation
            .as_mut()
            .ok_or(RawPageOwnerError::DoubleFree)?;
        let range = allocation.range();
        if range.address() != handle.address()
            || range.blocks() != handle.blocks()
            || range.bytes() != handle.bytes()
        {
            return Err(RawPageOwnerError::Ownership);
        }
        allocation.try_release()?;
        let released = slot.allocation.take();
        drop(released);
        Ok(())
    }

    /// Release the allocation currently owned at an exact address and size.
    ///
    /// Unlike `release`, this legacy-facing operation has no generation proof.
    /// After an identical address and size are freed and reused, a stale raw
    /// request is indistinguishable from the current allocation.  The caller
    /// must therefore prove that this is the current ownership transfer; the
    /// future legacy adapter and all consumers remain unimplemented.
    pub(crate) fn release_address(
        &mut self,
        address: u64,
        blocks: usize,
    ) -> Result<(), RawPageOwnerError> {
        if address == 0 || blocks == 0 {
            return Err(RawPageOwnerError::Invalid);
        }
        let mut found = None;
        for (index, slot) in self.slots.iter().enumerate() {
            let Some(allocation) = slot.allocation.as_ref() else {
                continue;
            };
            let range = allocation.range();
            if range.address() != address {
                continue;
            }
            if range.blocks() != blocks || found.is_some() {
                return Err(RawPageOwnerError::Ownership);
            }
            found = Some(RawPageAllocationHandle {
                registry_id: self.registry_id,
                slot: index,
                generation: slot.generation,
                range,
            });
        }
        self.release(found.ok_or(RawPageOwnerError::UnknownAddress)?)
    }

    fn next_slot(&self) -> Result<(usize, u64), RawPageOwnerError> {
        let mut saw_free_slot = false;
        for (index, slot) in self.slots.iter().enumerate() {
            if slot.allocation.is_some() {
                continue;
            }
            saw_free_slot = true;
            if let Some(generation) = slot.generation.checked_add(1) {
                if generation != 0 {
                    return Ok((index, generation));
                }
            }
        }
        if saw_free_slot {
            Err(RawPageOwnerError::GenerationExhausted)
        } else {
            Err(RawPageOwnerError::Full)
        }
    }

    fn commit(
        &mut self,
        slot: usize,
        generation: u64,
        allocation: PageAllocation<'allocator, 'storage>,
    ) -> RawPageAllocationHandle {
        let range = allocation.range();
        let destination = &mut self.slots[slot];
        destination.generation = generation;
        destination.allocation = Some(allocation);
        RawPageAllocationHandle {
            registry_id: self.registry_id,
            slot,
            generation,
            range,
        }
    }
}

impl Drop for RawPageOwnerRegistry<'_, '_, '_> {
    fn drop(&mut self) {
        for slot in self.slots.iter_mut() {
            drop(slot.allocation.take());
        }
    }
}

fn next_registry_id() -> Result<u64, RawPageOwnerError> {
    let mut current = NEXT_REGISTRY_ID.load(Ordering::Relaxed);
    loop {
        let next = current
            .checked_add(1)
            .ok_or(RawPageOwnerError::RegistryIdentityExhausted)?;
        if current == 0 {
            return Err(RawPageOwnerError::RegistryIdentityExhausted);
        }
        match NEXT_REGISTRY_ID.compare_exchange_weak(
            current,
            next,
            Ordering::Relaxed,
            Ordering::Relaxed,
        ) {
            Ok(_) => return Ok(current),
            Err(observed) => current = observed,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use core::sync::atomic::AtomicU64;

    #[test]
    fn generation_exhaustion_never_wraps_or_allocates() {
        let mut allocated = [AtomicU64::new(0)];
        let mut reserved = [AtomicU64::new(0)];
        let allocator = BitmapPageAllocator::new(
            0x1000,
            64 * 0x1000,
            0x1000,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots = [RawPageOwnerSlot::empty()];
        let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
        registry.slots[0].generation = u64::MAX;

        assert_eq!(
            registry.allocate(1),
            Err(RawPageOwnerError::GenerationExhausted)
        );
        assert_eq!(registry.active_count(), 0);
        assert_eq!(allocator.snapshot().allocated_blocks, 0);
    }

    #[test]
    fn forged_handle_metadata_cannot_clear_a_live_lease() {
        let mut allocated = [AtomicU64::new(0)];
        let mut reserved = [AtomicU64::new(0)];
        let allocator = BitmapPageAllocator::new(
            0x20_0000,
            64 * 0x1000,
            0x1000,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots = [RawPageOwnerSlot::empty(), RawPageOwnerSlot::empty()];
        let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
        let handle = registry.allocate(2).unwrap();
        let other = registry.allocate(3).unwrap();
        let forged = RawPageAllocationHandle {
            range: other.range,
            ..handle
        };

        assert_eq!(registry.release(forged), Err(RawPageOwnerError::Ownership));
        assert_eq!(registry.active_count(), 2);
        assert_eq!(allocator.snapshot().allocated_blocks, 5);
        registry.release(handle).unwrap();
        registry.release(other).unwrap();
    }
}
