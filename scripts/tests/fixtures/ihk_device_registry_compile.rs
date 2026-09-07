// SPDX-License-Identifier: GPL-2.0
#![cfg_attr(not(test), no_std)]
#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/device_registry.rs"]
mod device_registry;

#[cfg(test)]
mod fixture_tests {
    use super::device_registry::{
        ActiveDevicePhase, DeviceRegistry, DeviceRegistryError, SharePolicy,
        IHK_DEVICE_REGISTRY,
    };
    use std::collections::HashSet;
    use std::sync::{Arc, Barrier, Mutex};
    use std::thread;

    static PRODUCTION_REGISTRY_TEST_LOCK: Mutex<()> = Mutex::new(());

    fn registry() -> DeviceRegistry {
        DeviceRegistry::new().unwrap()
    }

    fn publish(
        registry: &DeviceRegistry,
        share_policy: SharePolicy,
    ) -> super::device_registry::DeviceHandle {
        registry.reserve(share_policy).unwrap().publish().unwrap()
    }

    fn expect_error<T>(result: Result<T, DeviceRegistryError>) -> DeviceRegistryError {
        match result {
            Ok(_) => panic!("operation unexpectedly succeeded"),
            Err(error) => error,
        }
    }

    #[test]
    fn success_path_publishes_counts_and_unregisters() {
        let registry = registry();
        let handle = publish(&registry, SharePolicy::Shared);
        let open = registry.acquire_open(handle).unwrap();
        let os = registry.acquire_os(handle).unwrap();
        let snapshot = registry.snapshot(handle).unwrap();
        assert_eq!(ActiveDevicePhase::Live, snapshot.phase);
        assert_eq!(1, snapshot.provider_references);
        assert_eq!(1, snapshot.os_references);
        drop(open);
        let unregister = registry.begin_unregister(handle).unwrap();
        assert_eq!(
            DeviceRegistryError::Busy,
            expect_error(registry.acquire_os(handle))
        );
        drop(os);
        unregister.commit().unwrap();
        assert_eq!(0, registry.active_count().unwrap());
    }

    #[test]
    fn failed_external_publication_aborts_without_reusing_handle() {
        let registry = registry();
        let failed = {
            let reservation = registry.reserve(SharePolicy::Exclusive).unwrap();
            let handle = reservation.handle();
            reservation.abort().unwrap();
            handle
        };
        assert_eq!(0, registry.active_count().unwrap());
        let replacement = publish(&registry, SharePolicy::Exclusive);
        assert_eq!(failed.minor(), replacement.minor());
        assert!(replacement.generation() > failed.generation());
        assert_eq!(
            DeviceRegistryError::StaleHandle,
            registry.snapshot(failed).unwrap_err()
        );
    }

    #[test]
    fn registry_state_rollback_restores_live_before_external_commit() {
        let registry = registry();
        let handle = publish(&registry, SharePolicy::Exclusive);
        let unregister = registry.begin_unregister(handle).unwrap();
        assert_eq!(ActiveDevicePhase::Unpublishing, registry.snapshot(handle).unwrap().phase);
        assert_eq!(handle, unregister.rollback().unwrap());
        assert_eq!(ActiveDevicePhase::Live, registry.snapshot(handle).unwrap().phase);
        let _open = registry.acquire_open(handle).unwrap();
    }

    #[test]
    fn deterministic_open_first_interleaving_blocks_unregister() {
        let registry = Arc::new(registry());
        let handle = publish(&registry, SharePolicy::Shared);
        let acquired = Arc::new(Barrier::new(2));
        let release = Arc::new(Barrier::new(2));
        let worker = {
            let registry = Arc::clone(&registry);
            let acquired = Arc::clone(&acquired);
            let release = Arc::clone(&release);
            thread::spawn(move || {
                let lease = registry.acquire_open(handle).unwrap();
                acquired.wait();
                release.wait();
                drop(lease);
            })
        };

        acquired.wait();
        assert_eq!(
            DeviceRegistryError::Busy,
            expect_error(registry.begin_unregister(handle))
        );
        release.wait();
        worker.join().unwrap();
        registry.begin_unregister(handle).unwrap().commit().unwrap();
    }

    #[test]
    fn deterministic_unregister_first_interleaving_blocks_references() {
        let registry = Arc::new(registry());
        let handle = publish(&registry, SharePolicy::Shared);
        let unregister = registry.begin_unregister(handle).unwrap();
        let worker = {
            let registry = Arc::clone(&registry);
            thread::spawn(move || {
                assert_eq!(
                    DeviceRegistryError::Busy,
                    expect_error(registry.acquire_open(handle))
                );
                assert_eq!(
                    DeviceRegistryError::Busy,
                    expect_error(registry.acquire_os(handle))
                );
            })
        };
        worker.join().unwrap();
        unregister.rollback().unwrap();
        let _open = registry.acquire_open(handle).unwrap();
    }

    #[test]
    fn simultaneous_publishers_get_unique_generation_tagged_slots() {
        const WORKERS: usize = 12;
        let registry = Arc::new(registry());
        let start = Arc::new(Barrier::new(WORKERS));
        let mut workers = std::vec::Vec::new();
        for _ in 0..WORKERS {
            let registry = Arc::clone(&registry);
            let start = Arc::clone(&start);
            workers.push(thread::spawn(move || {
                start.wait();
                publish(&registry, SharePolicy::Shared)
            }));
        }
        let handles: std::vec::Vec<_> = workers
            .into_iter()
            .map(|worker| worker.join().unwrap())
            .collect();
        let minors: HashSet<_> = handles.iter().map(|handle| handle.minor()).collect();
        let identities: HashSet<_> = handles
            .iter()
            .map(|handle| handle.registry_id())
            .collect();
        assert_eq!(WORKERS, minors.len());
        assert_eq!(1, identities.len());
        assert_eq!(WORKERS, registry.live_count().unwrap());
    }

    #[test]
    fn production_token_adapter_round_trips_and_detaches() {
        let _serial = PRODUCTION_REGISTRY_TEST_LOCK.lock().unwrap();
        let token = IHK_DEVICE_REGISTRY.attach_provider_token().unwrap();
        assert!(token > 0);
        let decoded = IHK_DEVICE_REGISTRY.decode_provider_token(token).unwrap();
        assert_eq!(0, decoded.minor());
        assert_eq!(decoded, IHK_DEVICE_REGISTRY.detach_provider_token(token).unwrap());
        assert_eq!(0, IHK_DEVICE_REGISTRY.active_count().unwrap());
    }

    #[test]
    fn malformed_and_replayed_production_tokens_fail_closed() {
        let _serial = PRODUCTION_REGISTRY_TEST_LOCK.lock().unwrap();
        let token = IHK_DEVICE_REGISTRY.attach_provider_token().unwrap();
        assert_eq!(
            DeviceRegistryError::InvalidToken,
            IHK_DEVICE_REGISTRY
                .decode_provider_token(token ^ (1_i64 << 34))
                .unwrap_err()
        );
        IHK_DEVICE_REGISTRY.detach_provider_token(token).unwrap();
        assert_eq!(
            DeviceRegistryError::NotFound,
            IHK_DEVICE_REGISTRY.detach_provider_token(token).unwrap_err()
        );
    }
}
