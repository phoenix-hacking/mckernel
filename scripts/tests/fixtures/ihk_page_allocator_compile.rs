// SPDX-License-Identifier: GPL-2.0

#[path = "../../../host-kernel/native-rust/page_allocator.rs"]
mod page_allocator;

#[cfg(test)]
mod tests {
    use super::page_allocator::{BitmapPageAllocator, PageAllocatorError};
    use std::sync::{atomic::AtomicU64, Arc, Mutex};

    fn storage() -> ([AtomicU64; 4], [AtomicU64; 4]) {
        (
            std::array::from_fn(|_| AtomicU64::new(u64::MAX)),
            std::array::from_fn(|_| AtomicU64::new(u64::MAX)),
        )
    }

    #[test]
    fn validates_constructor_ranges_and_storage() {
        let (mut allocated, mut reserved) = storage();
        assert!(BitmapPageAllocator::new(
            0x10_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .is_ok());
        assert_eq!(
            BitmapPageAllocator::new(
                0x10_0001,
                128 * 4096,
                4096,
                &mut allocated,
                &mut reserved,
            )
            .err(),
            Some(PageAllocatorError::Invalid)
        );
        assert_eq!(
            BitmapPageAllocator::new(
                0x10_0000,
                128 * 4096,
                3072,
                &mut allocated,
                &mut reserved,
            )
            .err(),
            Some(PageAllocatorError::Invalid)
        );
        let mut short_allocated = [AtomicU64::new(0)];
        let mut short_reserved = [AtomicU64::new(0)];
        assert_eq!(
            BitmapPageAllocator::new(
                0x10_0000,
                128 * 4096,
                4096,
                &mut short_allocated,
                &mut short_reserved,
            )
            .err(),
            Some(PageAllocatorError::Invalid)
        );
    }

    #[test]
    fn exact_capacity_fifo_drop_and_explicit_release_restore_space() {
        let (mut allocated, mut reserved) = storage();
        let allocator = BitmapPageAllocator::new(
            0x20_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let first = allocator.allocate(32).unwrap();
        assert_eq!(first.range().address(), 0x20_0000);
        assert_eq!(first.range().blocks(), 32);
        assert_eq!(first.range().bytes(), 32 * 4096);
        let second = allocator.allocate(96).unwrap();
        assert_eq!(allocator.allocate(1).err(), Some(PageAllocatorError::Exhausted));
        assert_eq!(allocator.snapshot().free_blocks, 0);
        first.release().unwrap();
        assert_eq!(allocator.snapshot().free_blocks, 32);
        drop(second);
        let snapshot = allocator.snapshot();
        assert_eq!(snapshot.total_blocks, 128);
        assert_eq!(snapshot.allocated_blocks, 0);
        assert_eq!(snapshot.reserved_blocks, 0);
        assert_eq!(snapshot.free_blocks, 128);
        assert_eq!(snapshot.largest_free_run, 128);
    }

    #[test]
    fn alignment_and_bitmap_word_crossing_are_exact() {
        let (mut allocated, mut reserved) = storage();
        let allocator = BitmapPageAllocator::new(
            0x30_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let prefix = allocator.allocate(63).unwrap();
        let crossing = allocator.allocate_aligned(34, 32).unwrap();
        assert_eq!(crossing.range().address() % (32 * 4096), 0);
        assert_eq!(crossing.range().address(), 0x30_0000 + 64 * 4096);
        assert_eq!(crossing.range().blocks(), 34);
        assert_eq!(allocator.allocate_aligned(1, 3).err(), Some(PageAllocatorError::Invalid));
        drop(prefix);
        drop(crossing);
        assert_eq!(allocator.snapshot().free_blocks, 128);
    }

    #[test]
    fn reservations_exclude_allocations_and_roll_back_on_drop() {
        let (mut allocated, mut reserved) = storage();
        let allocator = BitmapPageAllocator::new(
            0x40_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let reservation = allocator.reserve(0x40_0000 + 32 * 4096, 48).unwrap();
        assert_eq!(reservation.range().blocks(), 48);
        assert_eq!(
            allocator.reserve(0x40_0000 + 40 * 4096, 1).err(),
            Some(PageAllocatorError::Overlap)
        );
        let left = allocator.allocate(32).unwrap();
        let right = allocator.allocate(48).unwrap();
        assert_eq!(right.range().address(), 0x40_0000 + 80 * 4096);
        assert_eq!(allocator.allocate(1).err(), Some(PageAllocatorError::Exhausted));
        drop(left);
        drop(right);
        reservation.release().unwrap();
        assert_eq!(allocator.snapshot().largest_free_run, 128);
    }

    #[test]
    fn fragmentation_accounting_and_coalescing_are_deterministic() {
        let (mut allocated, mut reserved) = storage();
        let allocator = BitmapPageAllocator::new(
            0x50_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let a = allocator.allocate(24).unwrap();
        let b = allocator.allocate(24).unwrap();
        let c = allocator.allocate(24).unwrap();
        let d = allocator.allocate(24).unwrap();
        let e = allocator.allocate(24).unwrap();
        drop(b);
        drop(d);
        let fragmented = allocator.snapshot();
        assert_eq!(fragmented.free_blocks, 56);
        assert_eq!(fragmented.largest_free_run, 24);
        assert_eq!(allocator.allocate(25).err(), Some(PageAllocatorError::Exhausted));
        drop(c);
        let coalesced = allocator.allocate(48).unwrap();
        assert_eq!(coalesced.range().address(), 0x50_0000 + 48 * 4096);
        drop(a);
        drop(e);
        drop(coalesced);
        assert_eq!(allocator.snapshot().largest_free_run, 128);
    }

    #[test]
    fn byte_api_and_range_errors_fail_closed() {
        let (mut allocated, mut reserved) = storage();
        let allocator = BitmapPageAllocator::new(
            0x60_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        assert_eq!(
            allocator.allocate_bytes(4097, 4096).err(),
            Some(PageAllocatorError::Invalid)
        );
        assert_eq!(
            allocator.allocate_bytes(4096, 8193).err(),
            Some(PageAllocatorError::Invalid)
        );
        assert_eq!(
            allocator.reserve(0x60_0000 - 4096, 1).err(),
            Some(PageAllocatorError::Invalid)
        );
        assert_eq!(
            allocator.reserve(0x60_0000 + 127 * 4096, 2).err(),
            Some(PageAllocatorError::Invalid)
        );
        let allocation = allocator.allocate_bytes(4 * 4096, 16 * 4096).unwrap();
        assert_eq!(allocation.range().address() % (16 * 4096), 0);
        assert_eq!(allocation.range().bytes(), 4 * 4096);
    }

    #[test]
    fn concurrent_allocations_never_overlap_and_restore_every_block() {
        const THREADS: usize = 8;
        const OPERATIONS: usize = 300;
        let (allocated, reserved) = storage();
        let allocated = Box::leak(Box::new(allocated));
        let reserved = Box::leak(Box::new(reserved));
        let allocator = BitmapPageAllocator::new(
            0x70_0000,
            128 * 4096,
            4096,
            allocated,
            reserved,
        )
        .unwrap();
        let active_ranges = Arc::new(Mutex::new(Vec::<(u64, u64)>::new()));

        std::thread::scope(|scope| {
            for worker in 0..THREADS {
                let shared = &allocator;
                let active = Arc::clone(&active_ranges);
                scope.spawn(move || {
                    for operation in 0..OPERATIONS {
                        let blocks = 1 + ((worker * 17 + operation * 13) % 7);
                        loop {
                            match shared.allocate(blocks) {
                                Ok(lease) => {
                                    let range = lease.range();
                                    assert!(range.address() >= 0x70_0000);
                                    assert!(range.address() + range.bytes() <= 0x78_0000);
                                    let end = range.address() + range.bytes();
                                    {
                                        let mut ranges = active.lock().unwrap();
                                        assert!(ranges.iter().all(|(other_start, other_end)| {
                                            end <= *other_start || range.address() >= *other_end
                                        }));
                                        ranges.push((range.address(), end));
                                    }
                                    std::thread::yield_now();
                                    std::hint::black_box(range);
                                    {
                                        let mut ranges = active.lock().unwrap();
                                        let position = ranges
                                            .iter()
                                            .position(|entry| *entry == (range.address(), end))
                                            .unwrap();
                                        ranges.swap_remove(position);
                                    }
                                    drop(lease);
                                    break;
                                }
                                Err(PageAllocatorError::Exhausted) => std::thread::yield_now(),
                                Err(error) => panic!("unexpected allocation error: {error:?}"),
                            }
                        }
                    }
                });
            }
        });
        assert!(active_ranges.lock().unwrap().is_empty());
        let snapshot = allocator.snapshot();
        assert_eq!(snapshot.allocated_blocks, 0);
        assert_eq!(snapshot.reserved_blocks, 0);
        assert_eq!(snapshot.free_blocks, 128);
        assert_eq!(snapshot.largest_free_run, 128);
    }
}
