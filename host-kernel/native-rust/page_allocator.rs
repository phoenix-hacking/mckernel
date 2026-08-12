// SPDX-License-Identifier: GPL-2.0
//! Allocation-free bitmap allocator for IHK-managed physical ranges.
//!
//! The legacy host module exposes a six-function bitmap page allocator from
//! `ihk/linux/core/mem_alloc.c`.  This Rust substrate keeps the same contiguous
//! unit model while making range arithmetic, alignment, reservations, and
//! rollback ownership explicit.  Bitmap storage is supplied by the caller, so
//! allocator construction cannot recurse into the kernel page allocator.

use core::cmp::min;
use core::hint::spin_loop;
use core::sync::atomic::{AtomicBool, AtomicU64, Ordering};

const BITS_PER_WORD: usize = u64::BITS as usize;

/// A physical range expressed in allocator units.
///
/// This is copied metadata, not an ownership token. Its physical interval is
/// available to the caller only while the `PageAllocation` or
/// `PageReservation` lease that returned it remains alive.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PageRange {
    address: u64,
    blocks: usize,
    bytes: u64,
}

impl PageRange {
    /// First physical byte in the range.
    pub(crate) const fn address(self) -> u64 {
        self.address
    }

    /// Number of allocator units in the range.
    pub(crate) const fn blocks(self) -> usize {
        self.blocks
    }

    /// Number of bytes in the range.
    pub(crate) const fn bytes(self) -> u64 {
        self.bytes
    }
}

/// Fail-closed allocator outcomes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PageAllocatorError {
    /// Constructor input, range, count, or alignment is invalid.
    Invalid,
    /// No suitably aligned contiguous range is available.
    Exhausted,
    /// A reservation overlaps allocated or already-reserved storage.
    Overlap,
    /// A release did not exactly name storage of the requested ownership kind.
    Ownership,
}

/// Stable allocator accounting captured while holding the operation lock.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PageAllocatorSnapshot {
    /// Total managed units.
    pub(crate) total_blocks: usize,
    /// Units currently held by allocation leases.
    pub(crate) allocated_blocks: usize,
    /// Units currently held by reservation leases.
    pub(crate) reserved_blocks: usize,
    /// Units available for allocation.
    pub(crate) free_blocks: usize,
    /// Largest contiguous free run, in allocator units.
    pub(crate) largest_free_run: usize,
}

/// Releases the allocator-wide operation claim on all return paths.
struct OperationGuard<'allocator>(&'allocator AtomicBool);

impl Drop for OperationGuard<'_> {
    fn drop(&mut self) {
        self.0.store(false, Ordering::Release);
    }
}

/// Contiguous allocation whose `Drop` path rolls ownership back.
///
/// Kernel integration must obey the allocator-wide irqsave, nonpreemptible,
/// no-sleep, and non-reentrant context precondition when this lease is dropped.
#[must_use = "dropping the allocation lease immediately releases its physical range"]
pub(crate) struct PageAllocation<'allocator, 'storage> {
    allocator: &'allocator BitmapPageAllocator<'storage>,
    range: PageRange,
    owned: bool,
}

impl PageAllocation<'_, '_> {
    /// Copy range metadata that is valid only while this lease remains alive.
    pub(crate) fn range(&self) -> PageRange {
        self.range
    }

    /// Release this allocation immediately instead of waiting for `Drop`.
    pub(crate) fn release(mut self) -> Result<(), PageAllocatorError> {
        self.allocator
            .release_owned(self.range, OwnershipKind::Allocated)?;
        self.owned = false;
        Ok(())
    }
}

impl Drop for PageAllocation<'_, '_> {
    fn drop(&mut self) {
        if self.owned {
            // A lease can only contain a range marked by this allocator.  A
            // failure would indicate an internal invariant violation, but a
            // destructor must remain infallible at the kernel boundary.
            let _ = self
                .allocator
                .release_owned(self.range, OwnershipKind::Allocated);
            self.owned = false;
        }
    }
}

/// Reserved range whose `Drop` path restores availability.
///
/// Kernel integration must obey the allocator-wide irqsave, nonpreemptible,
/// no-sleep, and non-reentrant context precondition when this lease is dropped.
#[must_use = "dropping the reservation lease immediately releases its physical range"]
pub(crate) struct PageReservation<'allocator, 'storage> {
    allocator: &'allocator BitmapPageAllocator<'storage>,
    range: PageRange,
    owned: bool,
}

impl PageReservation<'_, '_> {
    /// Copy range metadata that is valid only while this lease remains alive.
    pub(crate) fn range(&self) -> PageRange {
        self.range
    }

    /// Release this reservation immediately instead of waiting for `Drop`.
    pub(crate) fn release(mut self) -> Result<(), PageAllocatorError> {
        self.allocator
            .release_owned(self.range, OwnershipKind::Reserved)?;
        self.owned = false;
        Ok(())
    }
}

impl Drop for PageReservation<'_, '_> {
    fn drop(&mut self) {
        if self.owned {
            // See the matching allocation destructor invariant above.
            let _ = self
                .allocator
                .release_owned(self.range, OwnershipKind::Reserved);
            self.owned = false;
        }
    }
}

#[derive(Clone, Copy)]
enum OwnershipKind {
    Allocated,
    Reserved,
}

/// Bitmap-backed allocator over one fixed physical interval.
///
/// Every operation is serialized by `operation_lock`. Before this source is
/// attached to the kernel, every call (including lease `Drop`) must be wrapped
/// by an audited Linux irqsave-equivalent adapter that disables local IRQs and
/// preemption, cannot sleep, and prevents same-CPU re-entry for the entire
/// operation. This process-portable `AtomicBool` only serializes CPUs; it does
/// not establish those kernel context properties itself.
pub(crate) struct BitmapPageAllocator<'storage> {
    start: u64,
    end: u64,
    unit_bytes: u64,
    block_count: usize,
    allocated: &'storage [AtomicU64],
    reserved: &'storage [AtomicU64],
    operation_lock: AtomicBool,
}

impl<'storage> BitmapPageAllocator<'storage> {
    /// Construct an empty allocator using caller-owned zeroable bitmap storage.
    pub(crate) fn new(
        start: u64,
        size_bytes: u64,
        unit_bytes: u64,
        allocated_storage: &'storage mut [AtomicU64],
        reserved_storage: &'storage mut [AtomicU64],
    ) -> Result<Self, PageAllocatorError> {
        if unit_bytes == 0
            || !unit_bytes.is_power_of_two()
            || start == 0
            || start % unit_bytes != 0
            || size_bytes == 0
            || size_bytes % unit_bytes != 0
        {
            return Err(PageAllocatorError::Invalid);
        }
        let end = start
            .checked_add(size_bytes)
            .ok_or(PageAllocatorError::Invalid)?;
        let block_count_u64 = size_bytes / unit_bytes;
        let block_count = usize::try_from(block_count_u64)
            .map_err(|_| PageAllocatorError::Invalid)?;
        let required_words = block_count
            .checked_add(BITS_PER_WORD - 1)
            .ok_or(PageAllocatorError::Invalid)?
            / BITS_PER_WORD;
        if required_words == 0
            || allocated_storage.len() < required_words
            || reserved_storage.len() < required_words
        {
            return Err(PageAllocatorError::Invalid);
        }

        let allocated = &allocated_storage[..required_words];
        let reserved = &reserved_storage[..required_words];
        for word in allocated.iter().chain(reserved.iter()) {
            word.store(0, Ordering::Relaxed);
        }

        Ok(Self {
            start,
            end,
            unit_bytes,
            block_count,
            allocated,
            reserved,
            operation_lock: AtomicBool::new(false),
        })
    }

    /// Allocate an exact number of contiguous units with unit alignment.
    pub(crate) fn allocate(
        &self,
        blocks: usize,
    ) -> Result<PageAllocation<'_, 'storage>, PageAllocatorError> {
        self.allocate_aligned(blocks, 1)
    }

    /// Allocate an exact contiguous range aligned to `alignment_blocks` units.
    pub(crate) fn allocate_aligned(
        &self,
        blocks: usize,
        alignment_blocks: usize,
    ) -> Result<PageAllocation<'_, 'storage>, PageAllocatorError> {
        if blocks == 0
            || blocks > self.block_count
            || alignment_blocks == 0
            || !alignment_blocks.is_power_of_two()
        {
            return Err(PageAllocatorError::Invalid);
        }
        let _guard = self.lock();
        let base_block = self.start / self.unit_bytes;
        let alignment_blocks =
            u64::try_from(alignment_blocks).map_err(|_| PageAllocatorError::Invalid)?;

        // The legacy descriptor never advances `last`, so its effective search
        // policy is first-fit from block zero on every allocation attempt.
        for candidate in 0..self.block_count {
            let Some(limit) = candidate.checked_add(blocks) else {
                break;
            };
            let candidate_u64 =
                u64::try_from(candidate).map_err(|_| PageAllocatorError::Invalid)?;
            let physical_block = base_block
                .checked_add(candidate_u64)
                .ok_or(PageAllocatorError::Invalid)?;
            if limit > self.block_count
                || physical_block % alignment_blocks != 0
                || !self.range_is_clear(candidate, blocks)
            {
                continue;
            }
            // Materialize all fallible metadata before committing bitmap
            // ownership, so an arithmetic failure cannot leak a marked range.
            let range = self.range_from_blocks(candidate, blocks)?;
            self.set_range(self.allocated, candidate, blocks, true);
            return Ok(PageAllocation {
                allocator: self,
                range,
                owned: true,
            });
        }
        Err(PageAllocatorError::Exhausted)
    }

    /// Allocate enough units to cover exactly an aligned byte count.
    pub(crate) fn allocate_bytes(
        &self,
        bytes: u64,
        alignment_bytes: u64,
    ) -> Result<PageAllocation<'_, 'storage>, PageAllocatorError> {
        if bytes == 0
            || bytes % self.unit_bytes != 0
            || alignment_bytes == 0
            || alignment_bytes % self.unit_bytes != 0
        {
            return Err(PageAllocatorError::Invalid);
        }
        let blocks = usize::try_from(bytes / self.unit_bytes)
            .map_err(|_| PageAllocatorError::Invalid)?;
        let alignment_blocks = usize::try_from(alignment_bytes / self.unit_bytes)
            .map_err(|_| PageAllocatorError::Invalid)?;
        self.allocate_aligned(blocks, alignment_blocks)
    }

    /// Reserve an exact physical interval so normal allocation cannot use it.
    pub(crate) fn reserve(
        &self,
        address: u64,
        blocks: usize,
    ) -> Result<PageReservation<'_, 'storage>, PageAllocatorError> {
        let start_block = self.validate_range(address, blocks)?;
        let _guard = self.lock();
        if !self.range_is_clear(start_block, blocks) {
            return Err(PageAllocatorError::Overlap);
        }
        // Complete checked metadata construction before the reservation bit
        // commit, preserving rollback-free failure semantics.
        let range = self.range_from_blocks(start_block, blocks)?;
        self.set_range(self.reserved, start_block, blocks, true);
        Ok(PageReservation {
            allocator: self,
            range,
            owned: true,
        })
    }

    /// Return deterministic usage and largest-free-run accounting.
    pub(crate) fn snapshot(&self) -> PageAllocatorSnapshot {
        let _guard = self.lock();
        let mut allocated_blocks = 0_usize;
        let mut reserved_blocks = 0_usize;
        let mut largest_free_run = 0_usize;
        let mut current_free_run = 0_usize;
        for block in 0..self.block_count {
            let allocated = self.bit_is_set(self.allocated, block);
            let reserved = self.bit_is_set(self.reserved, block);
            allocated_blocks += usize::from(allocated);
            reserved_blocks += usize::from(reserved);
            if allocated || reserved {
                largest_free_run = largest_free_run.max(current_free_run);
                current_free_run = 0;
            } else {
                current_free_run += 1;
            }
        }
        largest_free_run = largest_free_run.max(current_free_run);
        PageAllocatorSnapshot {
            total_blocks: self.block_count,
            allocated_blocks,
            reserved_blocks,
            free_blocks: self.block_count - allocated_blocks - reserved_blocks,
            largest_free_run,
        }
    }

    fn lock(&self) -> OperationGuard<'_> {
        loop {
            if self
                .operation_lock
                .compare_exchange_weak(false, true, Ordering::Acquire, Ordering::Relaxed)
                .is_ok()
            {
                return OperationGuard(&self.operation_lock);
            }
            while self.operation_lock.load(Ordering::Relaxed) {
                spin_loop();
            }
        }
    }

    fn validate_range(
        &self,
        address: u64,
        blocks: usize,
    ) -> Result<usize, PageAllocatorError> {
        if blocks == 0 || address < self.start || address % self.unit_bytes != 0 {
            return Err(PageAllocatorError::Invalid);
        }
        let bytes = (blocks as u64)
            .checked_mul(self.unit_bytes)
            .ok_or(PageAllocatorError::Invalid)?;
        let range_end = address
            .checked_add(bytes)
            .ok_or(PageAllocatorError::Invalid)?;
        if range_end > self.end {
            return Err(PageAllocatorError::Invalid);
        }
        usize::try_from((address - self.start) / self.unit_bytes)
            .map_err(|_| PageAllocatorError::Invalid)
    }

    fn range_from_blocks(
        &self,
        start_block: usize,
        blocks: usize,
    ) -> Result<PageRange, PageAllocatorError> {
        let offset = (start_block as u64)
            .checked_mul(self.unit_bytes)
            .ok_or(PageAllocatorError::Invalid)?;
        let bytes = (blocks as u64)
            .checked_mul(self.unit_bytes)
            .ok_or(PageAllocatorError::Invalid)?;
        let address = self
            .start
            .checked_add(offset)
            .ok_or(PageAllocatorError::Invalid)?;
        address
            .checked_add(bytes)
            .filter(|end| *end <= self.end)
            .ok_or(PageAllocatorError::Invalid)?;
        Ok(PageRange {
            address,
            blocks,
            bytes,
        })
    }

    fn release_owned(
        &self,
        range: PageRange,
        kind: OwnershipKind,
    ) -> Result<(), PageAllocatorError> {
        let start_block = self.validate_range(range.address, range.blocks)?;
        if range.bytes
            != (range.blocks as u64)
                .checked_mul(self.unit_bytes)
                .ok_or(PageAllocatorError::Invalid)?
        {
            return Err(PageAllocatorError::Invalid);
        }
        let _guard = self.lock();
        let (owned, other) = match kind {
            OwnershipKind::Allocated => (self.allocated, self.reserved),
            OwnershipKind::Reserved => (self.reserved, self.allocated),
        };
        if !self.range_is_set(owned, start_block, range.blocks)
            || self.range_has_any(other, start_block, range.blocks)
        {
            return Err(PageAllocatorError::Ownership);
        }
        self.set_range(owned, start_block, range.blocks, false);
        Ok(())
    }

    fn range_is_clear(&self, start: usize, blocks: usize) -> bool {
        !self.range_has_any(self.allocated, start, blocks)
            && !self.range_has_any(self.reserved, start, blocks)
    }

    fn range_is_set(&self, bitmap: &[AtomicU64], start: usize, blocks: usize) -> bool {
        let mut current = start;
        let mut remaining = blocks;
        while remaining != 0 {
            let word_index = current / BITS_PER_WORD;
            let bit_index = current % BITS_PER_WORD;
            let take = min(remaining, BITS_PER_WORD - bit_index);
            let mask = Self::word_mask(bit_index, take);
            let Some(word) = bitmap.get(word_index) else {
                return false;
            };
            if word.load(Ordering::Relaxed) & mask != mask {
                return false;
            }
            current += take;
            remaining -= take;
        }
        true
    }

    fn range_has_any(&self, bitmap: &[AtomicU64], start: usize, blocks: usize) -> bool {
        let mut current = start;
        let mut remaining = blocks;
        while remaining != 0 {
            let word_index = current / BITS_PER_WORD;
            let bit_index = current % BITS_PER_WORD;
            let take = min(remaining, BITS_PER_WORD - bit_index);
            let mask = Self::word_mask(bit_index, take);
            let Some(word) = bitmap.get(word_index) else {
                return true;
            };
            if word.load(Ordering::Relaxed) & mask != 0 {
                return true;
            }
            current += take;
            remaining -= take;
        }
        false
    }

    fn set_range(
        &self,
        bitmap: &[AtomicU64],
        start: usize,
        blocks: usize,
        value: bool,
    ) {
        let mut current = start;
        let mut remaining = blocks;
        while remaining != 0 {
            let word_index = current / BITS_PER_WORD;
            let bit_index = current % BITS_PER_WORD;
            let take = min(remaining, BITS_PER_WORD - bit_index);
            let mask = Self::word_mask(bit_index, take);
            // Constructor and range validation prove this index exists.
            if let Some(word) = bitmap.get(word_index) {
                let old = word.load(Ordering::Relaxed);
                word.store(if value { old | mask } else { old & !mask }, Ordering::Relaxed);
            }
            current += take;
            remaining -= take;
        }
    }

    fn bit_is_set(&self, bitmap: &[AtomicU64], block: usize) -> bool {
        bitmap
            .get(block / BITS_PER_WORD)
            .map(|word| word.load(Ordering::Relaxed) & (1_u64 << (block % BITS_PER_WORD)) != 0)
            .unwrap_or(true)
    }

    fn word_mask(bit: usize, count: usize) -> u64 {
        if count == BITS_PER_WORD {
            u64::MAX
        } else {
            ((1_u64 << count) - 1) << bit
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn wrong_kind_and_overlapping_release_are_rejected_without_clearing() {
        let mut allocated = [const { AtomicU64::new(0) }; 1];
        let mut reserved = [const { AtomicU64::new(0) }; 1];
        let allocator =
            BitmapPageAllocator::new(0x1000, 0x1000, 0x1000, &mut allocated, &mut reserved)
                .unwrap();
        let allocation = allocator.allocate(1).unwrap();
        let range = allocation.range();

        assert_eq!(
            allocator.release_owned(range, OwnershipKind::Reserved),
            Err(PageAllocatorError::Ownership)
        );
        assert!(allocator.bit_is_set(allocator.allocated, 0));

        allocator.reserved[0].store(1, Ordering::Relaxed);
        assert_eq!(
            allocator.release_owned(range, OwnershipKind::Allocated),
            Err(PageAllocatorError::Ownership)
        );
        assert!(allocator.bit_is_set(allocator.allocated, 0));
        assert!(allocator.bit_is_set(allocator.reserved, 0));

        allocator.reserved[0].store(0, Ordering::Relaxed);
        drop(allocation);
        let snapshot = allocator.snapshot();
        assert_eq!(snapshot.allocated_blocks, 0);
        assert_eq!(snapshot.free_blocks, 1);
    }
}
