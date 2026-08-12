#![cfg_attr(not(test), no_std)]
#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/abi/x86_64.rs"]
mod abi;

#[path = "../../../host-kernel/native-rust/os_registry.rs"]
mod os_registry;

#[path = "../../../host-kernel/native-rust/ihk_ioctl.rs"]
mod ihk_ioctl;

#[cfg(test)]
mod tests {
    use super::abi::{
        IHK_DEVICE_CREATE_OS, IHK_DEVICE_DESTROY_OS, IHK_OS_QUERY_STATUS, IHK_OS_STATUS,
    };
    use super::ihk_ioctl::{
        DeviceIoctl, ExternalFailure, IhkIoctlDispatcher, IoctlError,
        NATIVE_DEVICE_REGISTRATION_SUPPORTED, NATIVE_FILE_OPERATIONS_SUPPORTED,
        NATIVE_IOCTL_CALLBACK_SUPPORTED,
        USER_COPY_REACHABLE_FROM_IOCTL,
    };
    use super::os_registry::{OsHandle, OsRegistry, OsStatus, RegistryError, OS_CAPACITY};
    use std::collections::HashSet;
    use std::sync::{Arc, Barrier};
    use std::thread;

    fn error<T>(result: Result<T, IoctlError>) -> IoctlError {
        match result {
            Ok(_) => panic!("operation unexpectedly succeeded"),
            Err(error) => error,
        }
    }

    fn create(dispatcher: &IhkIoctlDispatcher<'_>, argument: u64) -> OsHandle {
        let transaction = dispatcher
            .prepare_device(IHK_DEVICE_CREATE_OS, argument)
            .unwrap();
        assert_eq!(DeviceIoctl::CreateOs { provider_arg: argument }, transaction.decoded());
        let pending = transaction.handle();
        let reply = transaction.commit_after_external_success().unwrap();
        assert_eq!(pending.minor() as i64, reply.return_value());
        assert_eq!(Some(pending), reply.created_handle());
        pending
    }

    #[test]
    fn exact_raw_commands_and_scalar_copy_policy() {
        assert_eq!(0x0011_2900, IHK_DEVICE_CREATE_OS);
        assert_eq!(0x0011_2901, IHK_DEVICE_DESTROY_OS);
        assert_eq!(0x0011_2a03, IHK_OS_QUERY_STATUS);
        assert_eq!(0x0011_2a14, IHK_OS_STATUS);
        assert!(!NATIVE_DEVICE_REGISTRATION_SUPPORTED);
        assert!(!NATIVE_FILE_OPERATIONS_SUPPORTED);
        assert!(!NATIVE_IOCTL_CALLBACK_SUPPORTED);
        assert!(!USER_COPY_REACHABLE_FROM_IOCTL);

        assert_eq!(
            DeviceIoctl::CreateOs {
                provider_arg: u64::MAX,
            },
            IhkIoctlDispatcher::decode_device(IHK_DEVICE_CREATE_OS, u64::MAX).unwrap()
        );
        assert_eq!(
            IoctlError::InvalidArgument,
            IhkIoctlDispatcher::decode_device(IHK_DEVICE_DESTROY_OS, OS_CAPACITY as u64)
                .unwrap_err()
        );
        assert_eq!(
            IoctlError::InvalidArgument,
            IhkIoctlDispatcher::decode_device(0xffff_ffff, 0).unwrap_err()
        );
        assert!(IhkIoctlDispatcher::decode_os(IHK_OS_QUERY_STATUS).is_ok());
        assert!(IhkIoctlDispatcher::decode_os(IHK_OS_STATUS).is_ok());
        assert_eq!(
            IoctlError::InvalidArgument,
            IhkIoctlDispatcher::decode_os(0).unwrap_err()
        );
    }

    #[test]
    fn create_failure_rolls_back_and_preserves_provider_errno() {
        let registry = OsRegistry::new();
        let dispatcher = IhkIoctlDispatcher::new(&registry);
        let first = dispatcher
            .prepare_device(IHK_DEVICE_CREATE_OS, 0xfeed_beef)
            .unwrap();
        let abandoned = first.handle();
        assert_eq!(
            -5,
            first.abort_external_failure(ExternalFailure::CreateOrSetup(-5))
        );
        assert_eq!(RegistryError::NotFound, registry.resolve_minor(0).unwrap_err());

        let replacement = create(&dispatcher, 7);
        assert_eq!(abandoned.minor(), replacement.minor());
        assert_eq!(abandoned.generation() + 1, replacement.generation());
    }

    #[test]
    fn create_status_aliases_and_destroy_return_exact_scalars() {
        let registry = OsRegistry::new();
        let dispatcher = IhkIoctlDispatcher::new(&registry);
        let handle = create(&dispatcher, 0);
        assert_eq!(0, dispatcher.dispatch_os(handle, IHK_OS_QUERY_STATUS, u64::MAX).unwrap());
        registry.transition(handle, OsStatus::Booting).unwrap();
        assert_eq!(2, dispatcher.dispatch_os(handle, IHK_OS_STATUS, 123).unwrap());

        let transaction = dispatcher
            .prepare_device(IHK_DEVICE_DESTROY_OS, handle.minor() as u64)
            .unwrap();
        assert_eq!(DeviceIoctl::DestroyOs { minor: 0 }, transaction.decoded());
        assert_eq!(handle, transaction.handle());
        let reply = transaction.commit_after_external_success().unwrap();
        assert_eq!(0, reply.return_value());
        assert_eq!(None, reply.created_handle());
        assert_eq!(0, registry.live_count());
    }

    #[test]
    fn destroy_lookup_and_unknown_requests_use_legacy_einval() {
        let registry = OsRegistry::new();
        let dispatcher = IhkIoctlDispatcher::new(&registry);
        assert_eq!(
            -22,
            error(dispatcher.prepare_device(IHK_DEVICE_DESTROY_OS, 0)).errno()
        );
        assert_eq!(
            -22,
            error(dispatcher.prepare_device(IHK_DEVICE_DESTROY_OS, OS_CAPACITY as u64)).errno()
        );
        assert_eq!(-22, error(dispatcher.prepare_device(0, 0)).errno());
    }

    #[test]
    fn destroy_failures_roll_back_with_exact_stage_errno_mapping() {
        let registry = OsRegistry::new();
        let dispatcher = IhkIoctlDispatcher::new(&registry);
        let handle = create(&dispatcher, 0);
        let transaction = dispatcher
            .prepare_device(IHK_DEVICE_DESTROY_OS, handle.minor() as u64)
            .unwrap();
        assert_eq!(
            -5,
            transaction.abort_external_failure(ExternalFailure::DestroyShutdown(-5))
        );
        assert_eq!(handle, registry.resolve_minor(handle.minor()).unwrap());
        assert_eq!(OsStatus::NotBooted, registry.snapshot(handle).unwrap().status);

        let transaction = dispatcher
            .prepare_device(IHK_DEVICE_DESTROY_OS, handle.minor() as u64)
            .unwrap();
        assert_eq!(
            -22,
            transaction.abort_external_failure(ExternalFailure::DestroyProvider(-5))
        );
        assert_eq!(handle, registry.resolve_minor(handle.minor()).unwrap());
    }

    #[test]
    fn exact_sixty_four_capacity_returns_enomem() {
        let registry = OsRegistry::new();
        let dispatcher = IhkIoctlDispatcher::new(&registry);
        for minor in 0..OS_CAPACITY {
            let handle = create(&dispatcher, minor as u64);
            assert_eq!(minor, handle.minor());
        }
        assert_eq!(OS_CAPACITY, registry.live_count());
        assert_eq!(
            -12,
            error(dispatcher.prepare_device(IHK_DEVICE_CREATE_OS, 0)).errno()
        );
    }

    #[test]
    fn leases_exclude_destroy_until_the_open_identity_is_released() {
        let registry = OsRegistry::new();
        let dispatcher = IhkIoctlDispatcher::new(&registry);
        let handle = create(&dispatcher, 0);
        let lease = registry.acquire(handle).unwrap();
        assert_eq!(
            -16,
            error(dispatcher.prepare_device(IHK_DEVICE_DESTROY_OS, 0)).errno()
        );
        drop(lease);
        dispatcher
            .prepare_device(IHK_DEVICE_DESTROY_OS, 0)
            .unwrap()
            .commit_after_external_success()
            .unwrap();
    }

    #[test]
    fn stale_open_identity_never_observes_a_recycled_minor() {
        let registry = OsRegistry::new();
        let dispatcher = IhkIoctlDispatcher::new(&registry);
        let old = create(&dispatcher, 0);
        dispatcher
            .prepare_device(IHK_DEVICE_DESTROY_OS, 0)
            .unwrap()
            .commit_after_external_success()
            .unwrap();
        let replacement = create(&dispatcher, 0);
        assert_eq!(old.minor(), replacement.minor());
        assert_ne!(old.generation(), replacement.generation());
        assert_eq!(
            -116,
            error(dispatcher.dispatch_os(old, IHK_OS_QUERY_STATUS, 0)).errno()
        );
        assert_eq!(0, dispatcher.dispatch_os(replacement, IHK_OS_STATUS, 0).unwrap());
    }

    #[test]
    fn concurrent_create_transactions_publish_unique_minors() {
        let registry = Arc::new(OsRegistry::new());
        let barrier = Arc::new(Barrier::new(OS_CAPACITY + 1));
        let mut workers = Vec::new();
        for argument in 0..OS_CAPACITY {
            let registry = Arc::clone(&registry);
            let barrier = Arc::clone(&barrier);
            workers.push(thread::spawn(move || {
                let dispatcher = IhkIoctlDispatcher::new(&registry);
                let transaction = dispatcher
                    .prepare_device(IHK_DEVICE_CREATE_OS, argument as u64)
                    .unwrap();
                barrier.wait();
                transaction
                    .commit_after_external_success()
                    .unwrap()
                    .created_handle()
                    .unwrap()
            }));
        }
        barrier.wait();
        let handles: Vec<_> = workers
            .into_iter()
            .map(|worker| worker.join().unwrap())
            .collect();
        let minors: HashSet<_> = handles.iter().map(|handle| handle.minor()).collect();
        assert_eq!(OS_CAPACITY, minors.len());
        assert_eq!(OS_CAPACITY, registry.live_count());
    }

    #[test]
    fn deterministic_operation_property_preserves_registry_invariants() {
        let registry = OsRegistry::new();
        let dispatcher = IhkIoctlDispatcher::new(&registry);
        let mut handles: [Option<OsHandle>; OS_CAPACITY] = [None; OS_CAPACITY];
        let mut state = 0x6a09_e667_f3bc_c909_u64;

        for _ in 0..10_000 {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            let minor = ((state >> 32) as usize) % OS_CAPACITY;
            if let Some(handle) = handles[minor] {
                dispatcher
                    .prepare_device(IHK_DEVICE_DESTROY_OS, minor as u64)
                    .unwrap()
                    .commit_after_external_success()
                    .unwrap();
                assert!(matches!(
                    registry.snapshot(handle),
                    Err(RegistryError::NotFound) | Err(RegistryError::StaleHandle)
                ));
                handles[minor] = None;
            } else if registry.live_count() < OS_CAPACITY {
                let handle = create(&dispatcher, state);
                assert!(handles[handle.minor()].is_none());
                handles[handle.minor()] = Some(handle);
            }

            let expected = handles.iter().filter(|slot| slot.is_some()).count();
            assert_eq!(expected, registry.live_count());
            for handle in handles.iter().flatten() {
                assert_eq!(*handle, registry.resolve_minor(handle.minor()).unwrap());
            }
        }
    }
}
