// SPDX-License-Identifier: GPL-2.0

#[path = "../../../host-kernel/native-rust/page_allocator.rs"]
mod page_allocator;
#[path = "../../../host-kernel/native-rust/page_owner_registry.rs"]
mod page_owner_registry;

#[cfg(test)]
mod tests {
    use super::page_allocator::{BitmapPageAllocator, PageAllocatorError};
    use super::page_owner_registry::{
        RawPageOwnerError, RawPageOwnerRegistry, RawPageOwnerSlot,
    };
    use std::sync::{atomic::AtomicU64, Mutex};

    fn bitmap_storage() -> ([AtomicU64; 2], [AtomicU64; 2]) {
        (
            std::array::from_fn(|_| AtomicU64::new(0)),
            std::array::from_fn(|_| AtomicU64::new(0)),
        )
    }

    #[test]
    fn construction_requires_caller_capacity_and_issues_distinct_identities() {
        let (mut allocated, mut reserved) = bitmap_storage();
        let allocator = BitmapPageAllocator::new(
            0x10_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut empty: [RawPageOwnerSlot<'_, '_>; 0] = [];
        assert_eq!(
            RawPageOwnerRegistry::new(&allocator, &mut empty).err(),
            Some(RawPageOwnerError::Invalid)
        );
        let explicit = allocator.allocate(1).unwrap();
        explicit.release().unwrap();
        let reservation = allocator.reserve(0x10_0000 + 8 * 4096, 2).unwrap();
        assert_eq!(reservation.range().blocks(), 2);
        assert_eq!(
            allocator.reserve(0x10_0000 + 9 * 4096, 1).err(),
            Some(PageAllocatorError::Overlap)
        );
        reservation.release().unwrap();

        let mut slots = std::array::from_fn::<_, 1, _>(|_| RawPageOwnerSlot::empty());
        let first_id = {
            let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
            assert_eq!(registry.capacity(), 1);
            let handle = registry.allocate(1).unwrap();
            let id = handle.registry_id();
            registry.release(handle).unwrap();
            id
        };
        let second_id = {
            let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
            let handle = registry.allocate(1).unwrap();
            let id = handle.registry_id();
            registry.release(handle).unwrap();
            id
        };
        assert_ne!(first_id, second_id);
    }

    #[test]
    fn allocation_lease_remains_owned_until_typed_release() {
        let (mut allocated, mut reserved) = bitmap_storage();
        let allocator = BitmapPageAllocator::new(
            0x20_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots = std::array::from_fn::<_, 2, _>(|_| RawPageOwnerSlot::empty());
        let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
        let handle = registry.allocate(4).unwrap();
        assert_eq!(handle.address(), 0x20_0000);
        assert_eq!(handle.blocks(), 4);
        assert_eq!(handle.bytes(), 4 * 4096);
        assert_ne!(handle.generation(), 0);
        assert_eq!(registry.active_count(), 1);
        assert_eq!(allocator.snapshot().allocated_blocks, 4);
        registry.release(handle).unwrap();
        assert_eq!(registry.active_count(), 0);
        assert_eq!(allocator.snapshot().free_blocks, 128);
    }

    #[test]
    fn exact_capacity_full_failure_preserves_allocator_state() {
        let (mut allocated, mut reserved) = bitmap_storage();
        let allocator = BitmapPageAllocator::new(
            0x30_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots = std::array::from_fn::<_, 2, _>(|_| RawPageOwnerSlot::empty());
        let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
        let first = registry.allocate(3).unwrap();
        let second = registry.allocate(5).unwrap();
        let before = allocator.snapshot();
        assert_eq!(registry.allocate(1), Err(RawPageOwnerError::Full));
        assert_eq!(registry.active_count(), 2);
        assert_eq!(allocator.snapshot(), before);
        registry.release(first).unwrap();
        registry.release(second).unwrap();
    }

    #[test]
    fn double_free_and_stale_generation_are_distinct() {
        let (mut allocated, mut reserved) = bitmap_storage();
        let allocator = BitmapPageAllocator::new(
            0x40_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots = std::array::from_fn::<_, 1, _>(|_| RawPageOwnerSlot::empty());
        let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
        let old = registry.allocate(1).unwrap();
        registry.release(old).unwrap();
        assert_eq!(registry.release(old), Err(RawPageOwnerError::DoubleFree));
        let current = registry.allocate(1).unwrap();
        assert_eq!(current.address(), old.address());
        assert!(current.generation() > old.generation());
        assert_eq!(registry.release(old), Err(RawPageOwnerError::StaleHandle));
        assert_eq!(registry.active_count(), 1);
        registry.release(current).unwrap();
    }

    #[test]
    fn foreign_registry_handle_cannot_release_current_owner() {
        let (mut allocated, mut reserved) = bitmap_storage();
        let allocator = BitmapPageAllocator::new(
            0x50_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots_a = std::array::from_fn::<_, 1, _>(|_| RawPageOwnerSlot::empty());
        let mut slots_b = std::array::from_fn::<_, 1, _>(|_| RawPageOwnerSlot::empty());
        let mut first = RawPageOwnerRegistry::new(&allocator, &mut slots_a).unwrap();
        let mut second = RawPageOwnerRegistry::new(&allocator, &mut slots_b).unwrap();
        let first_handle = first.allocate(1).unwrap();
        let second_handle = second.allocate(1).unwrap();
        assert_eq!(
            second.release(first_handle),
            Err(RawPageOwnerError::StaleHandle)
        );
        assert_eq!(allocator.snapshot().allocated_blocks, 2);
        first.release(first_handle).unwrap();
        second.release(second_handle).unwrap();
    }

    #[test]
    fn raw_address_release_is_exact_and_fails_closed() {
        let (mut allocated, mut reserved) = bitmap_storage();
        let allocator = BitmapPageAllocator::new(
            0x60_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots = std::array::from_fn::<_, 2, _>(|_| RawPageOwnerSlot::empty());
        let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
        let handle = registry.allocate(4).unwrap();
        assert_eq!(
            registry.release_address(0, 4),
            Err(RawPageOwnerError::Invalid)
        );
        assert_eq!(
            registry.release_address(handle.address(), 0),
            Err(RawPageOwnerError::Invalid)
        );
        assert_eq!(
            registry.release_address(handle.address() + 4096, 3),
            Err(RawPageOwnerError::UnknownAddress)
        );
        assert_eq!(
            registry.release_address(handle.address(), 3),
            Err(RawPageOwnerError::Ownership)
        );
        assert_eq!(registry.active_count(), 1);
        registry
            .release_address(handle.address(), handle.blocks())
            .unwrap();
        assert_eq!(
            registry.release_address(handle.address(), handle.blocks()),
            Err(RawPageOwnerError::UnknownAddress)
        );
    }

    #[test]
    fn backing_allocator_failure_does_not_consume_free_slot() {
        let mut allocated = [AtomicU64::new(0)];
        let mut reserved = [AtomicU64::new(0)];
        let allocator = BitmapPageAllocator::new(
            0x70_0000,
            2 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots = std::array::from_fn::<_, 2, _>(|_| RawPageOwnerSlot::empty());
        let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
        let handle = registry.allocate(2).unwrap();
        assert_eq!(
            registry.allocate(1),
            Err(RawPageOwnerError::Allocator(PageAllocatorError::Exhausted))
        );
        assert_eq!(registry.active_count(), 1);
        assert_eq!(allocator.snapshot().allocated_blocks, 2);
        registry.release(handle).unwrap();
    }

    #[test]
    fn failed_release_retains_lease_for_retry() {
        let (mut allocated, mut reserved) = bitmap_storage();
        let allocator = BitmapPageAllocator::new(
            0x80_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots = std::array::from_fn::<_, 1, _>(|_| RawPageOwnerSlot::empty());
        let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
        let handle = registry.allocate(2).unwrap();
        allocator
            .inject_reserved_overlap_for_test(handle.address(), handle.blocks(), true)
            .unwrap();
        assert_eq!(
            registry.release(handle),
            Err(RawPageOwnerError::Allocator(PageAllocatorError::Ownership))
        );
        assert_eq!(registry.active_count(), 1);
        assert_eq!(allocator.snapshot().allocated_blocks, 2);
        allocator
            .inject_reserved_overlap_for_test(handle.address(), handle.blocks(), false)
            .unwrap();
        registry.release(handle).unwrap();
        assert_eq!(allocator.snapshot().allocated_blocks, 0);
    }

    #[test]
    fn aligned_byte_metadata_round_trips_exactly() {
        let (mut allocated, mut reserved) = bitmap_storage();
        let allocator = BitmapPageAllocator::new(
            0x90_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots = std::array::from_fn::<_, 1, _>(|_| RawPageOwnerSlot::empty());
        let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
        let handle = registry.allocate_bytes(3 * 4096, 16 * 4096).unwrap();
        assert_eq!(handle.address() % (16 * 4096), 0);
        assert_eq!(handle.blocks(), 3);
        assert_eq!(handle.bytes(), 3 * 4096);
        registry.release(handle).unwrap();
    }

    #[test]
    fn registry_drop_drains_every_retained_lease_once() {
        let (mut allocated, mut reserved) = bitmap_storage();
        let allocator = BitmapPageAllocator::new(
            0xa0_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots = std::array::from_fn::<_, 4, _>(|_| RawPageOwnerSlot::empty());
        {
            let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
            for blocks in 1..=4 {
                let _retained_handle = registry.allocate(blocks).unwrap();
            }
            assert_eq!(allocator.snapshot().allocated_blocks, 10);
        }
        let snapshot = allocator.snapshot();
        assert_eq!(snapshot.allocated_blocks, 0);
        assert_eq!(snapshot.free_blocks, 128);
    }

    #[test]
    fn locked_concurrency_preserves_unique_addresses_and_accounting() {
        const THREADS: usize = 8;
        const OPERATIONS: usize = 200;
        let allocated = Box::leak(Box::new(std::array::from_fn::<_, 2, _>(|_| {
            AtomicU64::new(0)
        })));
        let reserved = Box::leak(Box::new(std::array::from_fn::<_, 2, _>(|_| {
            AtomicU64::new(0)
        })));
        let allocator = Box::leak(Box::new(
            BitmapPageAllocator::new(
                0xb0_0000,
                128 * 4096,
                4096,
                allocated,
                reserved,
            )
            .unwrap(),
        ));
        let slots = Box::leak(Box::new(std::array::from_fn::<_, 32, _>(|_| {
            RawPageOwnerSlot::empty()
        })));
        let registry = Mutex::new(RawPageOwnerRegistry::new(allocator, slots).unwrap());
        let active = Mutex::new(Vec::<u64>::new());

        std::thread::scope(|scope| {
            for worker in 0..THREADS {
                let registry = &registry;
                let active = &active;
                scope.spawn(move || {
                    for operation in 0..OPERATIONS {
                        let blocks = 1 + ((worker * 11 + operation * 7) % 4);
                        loop {
                            let attempt = registry.lock().unwrap().allocate(blocks);
                            match attempt {
                                Ok(handle) => {
                                    {
                                        let mut addresses = active.lock().unwrap();
                                        assert!(!addresses.contains(&handle.address()));
                                        addresses.push(handle.address());
                                    }
                                    std::thread::yield_now();
                                    {
                                        let mut addresses = active.lock().unwrap();
                                        let position = addresses
                                            .iter()
                                            .position(|address| *address == handle.address())
                                            .unwrap();
                                        addresses.swap_remove(position);
                                    }
                                    registry.lock().unwrap().release(handle).unwrap();
                                    break;
                                }
                                Err(RawPageOwnerError::Full)
                                | Err(RawPageOwnerError::Allocator(
                                    PageAllocatorError::Exhausted,
                                )) => std::thread::yield_now(),
                                Err(error) => panic!("unexpected registry error: {error:?}"),
                            }
                        }
                    }
                });
            }
        });
        assert!(active.lock().unwrap().is_empty());
        assert_eq!(registry.lock().unwrap().active_count(), 0);
        assert_eq!(allocator.snapshot().allocated_blocks, 0);
        assert_eq!(allocator.snapshot().free_blocks, 128);
    }

    #[test]
    fn address_only_aba_limit_is_explicit_while_typed_handle_stays_stale() {
        let (mut allocated, mut reserved) = bitmap_storage();
        let allocator = BitmapPageAllocator::new(
            0xc0_0000,
            128 * 4096,
            4096,
            &mut allocated,
            &mut reserved,
        )
        .unwrap();
        let mut slots = std::array::from_fn::<_, 1, _>(|_| RawPageOwnerSlot::empty());
        let mut registry = RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap();
        let stale = registry.allocate(1).unwrap();
        registry.release(stale).unwrap();
        let current = registry.allocate(1).unwrap();
        assert_eq!(current.address(), stale.address());
        assert_eq!(current.blocks(), stale.blocks());

        // A generation-free legacy request cannot distinguish these owners.
        registry
            .release_address(stale.address(), stale.blocks())
            .unwrap();
        assert_eq!(registry.release(stale), Err(RawPageOwnerError::StaleHandle));
        assert_eq!(registry.active_count(), 0);
    }
}
