#![cfg_attr(not(test), no_std)]
#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/abi/x86_64.rs"]
mod abi;

#[path = "../../../host-kernel/native-rust/os_registry.rs"]
mod os_registry;

#[cfg(test)]
mod tests {
    use super::os_registry::{
        OsRegistry, OsStatus, RegistryError, OS_CAPACITY,
    };
    use std::collections::HashSet;
    use std::sync::{Arc, Barrier};
    use std::thread;

    fn create(registry: &OsRegistry) -> super::os_registry::OsHandle {
        registry.reserve().unwrap().commit().unwrap()
    }

    fn expect_registry_error<T>(result: Result<T, RegistryError>) -> RegistryError {
        match result {
            Ok(_) => panic!("operation unexpectedly succeeded"),
            Err(error) => error,
        }
    }

    #[test]
    fn exact_capacity_first_fit_and_generation_reuse() {
        let registry = OsRegistry::new();
        let mut handles = Vec::new();
        for expected_minor in 0..OS_CAPACITY {
            let handle = create(&registry);
            assert_eq!(expected_minor, handle.minor());
            assert_eq!(1, handle.generation());
            handles.push(handle);
        }
        assert_eq!(OS_CAPACITY, registry.live_count());
        assert_eq!(RegistryError::Capacity, expect_registry_error(registry.reserve()));
        assert_eq!(-12, RegistryError::Capacity.errno());

        let old = handles[17];
        registry.begin_destroy(old).unwrap().commit().unwrap();
        let replacement = create(&registry);
        assert_eq!(17, replacement.minor());
        assert_eq!(old.generation() + 1, replacement.generation());
        assert_eq!(
            RegistryError::StaleHandle,
            registry.transition(old, OsStatus::Loading).unwrap_err()
        );
        assert_eq!(-116, RegistryError::StaleHandle.errno());
    }

    #[test]
    fn reservation_and_destroy_guards_rollback() {
        let registry = OsRegistry::new();
        let abandoned = {
            let reservation = registry.reserve().unwrap();
            let handle = reservation.handle();
            assert_eq!(RegistryError::Busy, registry.resolve_minor(0).unwrap_err());
            handle
        };
        assert_eq!(RegistryError::NotFound, registry.resolve_minor(0).unwrap_err());

        let live = create(&registry);
        assert_eq!(abandoned.generation() + 1, live.generation());
        registry.transition(live, OsStatus::Booting).unwrap();
        {
            let destroying = registry.begin_destroy(live).unwrap();
            assert_eq!(live, destroying.handle());
            assert_eq!(RegistryError::Busy, registry.resolve_minor(0).unwrap_err());
        }
        assert_eq!(OsStatus::Booting, registry.snapshot(live).unwrap().status);
    }

    #[test]
    fn references_exclude_destroy_and_release_on_drop() {
        let registry = OsRegistry::new();
        let handle = create(&registry);
        let first = registry.acquire(handle).unwrap();
        let second = registry.acquire(handle).unwrap();
        assert_eq!(handle, first.handle());
        assert_eq!(2, registry.snapshot(handle).unwrap().references);
        assert_eq!(
            RegistryError::Busy,
            expect_registry_error(registry.begin_destroy(handle))
        );
        drop(first);
        assert_eq!(1, registry.snapshot(handle).unwrap().references);
        drop(second);
        registry.begin_destroy(handle).unwrap().commit().unwrap();
        assert_eq!(RegistryError::NotFound, registry.snapshot(handle).unwrap_err());
    }

    #[test]
    fn reference_counter_overflow_fails_closed() {
        let registry = OsRegistry::new();
        let handle = create(&registry);
        let mut leases = Vec::with_capacity(u16::MAX as usize);
        for _ in 0..u16::MAX {
            leases.push(registry.acquire(handle).unwrap());
        }
        let snapshot = registry.snapshot(handle).unwrap();
        assert_eq!(handle, snapshot.handle);
        assert_eq!(u16::MAX, snapshot.references);
        assert_eq!(
            RegistryError::ReferenceOverflow,
            expect_registry_error(registry.acquire(handle))
        );
        drop(leases);
        assert_eq!(0, registry.snapshot(handle).unwrap().references);
    }

    #[test]
    fn explicit_state_graph_accepts_only_reviewed_edges() {
        let registry = OsRegistry::new();
        let handle = create(&registry);
        assert_eq!(OsStatus::NotBooted, registry.snapshot(handle).unwrap().status);
        assert_eq!(
            RegistryError::InvalidTransition,
            registry.transition(handle, OsStatus::Running).unwrap_err()
        );
        assert_eq!(-22, RegistryError::InvalidTransition.errno());

        for next in [
            OsStatus::Booting,
            OsStatus::Booted,
            OsStatus::Ready,
            OsStatus::Running,
            OsStatus::Freezing,
            OsStatus::Frozen,
            OsStatus::Running,
            OsStatus::Shutdown,
            OsStatus::NotBooted,
            OsStatus::Loading,
            OsStatus::NotBooted,
        ] {
            registry.transition(handle, next).unwrap();
            assert_eq!(next, registry.snapshot(handle).unwrap().status);
            registry.transition(handle, next).unwrap();
        }

        registry.transition(handle, OsStatus::Booting).unwrap();
        registry.transition(handle, OsStatus::Hungup).unwrap();
        registry.transition(handle, OsStatus::Failed).unwrap();
        registry.transition(handle, OsStatus::Shutdown).unwrap();
        registry.transition(handle, OsStatus::NotBooted).unwrap();
    }

    #[test]
    fn concurrent_reservations_are_exclusive_and_complete() {
        let registry = Arc::new(OsRegistry::new());
        let barrier = Arc::new(Barrier::new(OS_CAPACITY + 1));
        let mut threads = Vec::new();
        for _ in 0..OS_CAPACITY {
            let registry = Arc::clone(&registry);
            let barrier = Arc::clone(&barrier);
            threads.push(thread::spawn(move || {
                let handle = create(&registry);
                barrier.wait();
                handle
            }));
        }
        barrier.wait();
        assert_eq!(RegistryError::Capacity, expect_registry_error(registry.reserve()));
        let handles: Vec<_> = threads.into_iter().map(|thread| thread.join().unwrap()).collect();
        let minors: HashSet<_> = handles.iter().map(|handle| handle.minor()).collect();
        assert_eq!(OS_CAPACITY, minors.len());
        assert_eq!(OS_CAPACITY, registry.live_count());
    }

    #[test]
    fn concurrent_churn_never_revives_an_old_handle() {
        let registry = Arc::new(OsRegistry::new());
        let mut threads = Vec::new();
        for _ in 0..8 {
            let registry = Arc::clone(&registry);
            threads.push(thread::spawn(move || {
                for _ in 0..2_000 {
                    let handle = create(&registry);
                    registry.transition(handle, OsStatus::Loading).unwrap();
                    registry.transition(handle, OsStatus::NotBooted).unwrap();
                    registry.begin_destroy(handle).unwrap().commit().unwrap();
                    assert!(matches!(
                        registry.snapshot(handle),
                        Err(RegistryError::NotFound) | Err(RegistryError::StaleHandle)
                    ));
                }
            }));
        }
        for thread in threads {
            thread.join().unwrap();
        }
        assert_eq!(0, registry.live_count());
    }

    #[test]
    fn errno_mapping_is_stable_and_minor_bounds_fail_closed() {
        let registry = OsRegistry::new();
        assert_eq!(RegistryError::InvalidMinor, registry.resolve_minor(OS_CAPACITY).unwrap_err());
        let mappings = [
            (RegistryError::NotFound, -2),
            (RegistryError::Capacity, -12),
            (RegistryError::Busy, -16),
            (RegistryError::InvalidMinor, -22),
            (RegistryError::InvalidTransition, -22),
            (RegistryError::GenerationExhausted, -75),
            (RegistryError::ReferenceOverflow, -75),
            (RegistryError::StaleHandle, -116),
            (RegistryError::Corrupt, -117),
        ];
        for (error, expected) in mappings {
            assert_eq!(expected, error.errno());
        }
    }
}
