// SPDX-License-Identifier: GPL-2.0
#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/ihk_mapping.rs"]
mod ihk_mapping;

#[cfg(test)]
mod tests {
    use super::ihk_mapping::{
        AlignedPhysicalRange, CachePolicy, CleanupStep, DeviceMapping,
        KernelMapDescriptor, LinuxErrno, MappingError, MmapProtection,
        MmapProtectionPolicy, MmapStage, MmapTransaction, PageGeometry,
        PhysicalRange, UserMmapRequest,
    };

    fn pages() -> PageGeometry {
        PageGeometry::new(12).unwrap()
    }

    fn protection() -> MmapProtection {
        MmapProtection {
            readable: true,
            writable: true,
            executable: false,
            shared: true,
        }
    }

    fn policy() -> MmapProtectionPolicy {
        MmapProtectionPolicy {
            require_readable: true,
            allow_write: true,
            allow_execute: false,
            require_shared: true,
        }
    }

    fn request(page_offset: u64, pages_count: u64) -> UserMmapRequest {
        let page = pages();
        let physical_start = page_offset * page.size();
        UserMmapRequest::validate(
            0x4000_0000,
            0x4000_0000 + pages_count * page.size(),
            page_offset,
            page,
            PhysicalRange::new(physical_start, pages_count * page.size()).unwrap(),
            protection(),
            policy(),
        )
        .unwrap()
    }

    #[test]
    fn valid_user_mmap_descriptor_preserves_exact_ranges() {
        let request = request(0x123, 3);
        assert_eq!(request.user_start(), 0x4000_0000);
        assert_eq!(request.user_end(), 0x4000_3000);
        assert_eq!(request.length(), 0x3000);
        assert_eq!(request.physical().start(), 0x123000);
        assert_eq!(request.physical().end(), 0x126000);
        assert_eq!(request.protection(), protection());
    }

    #[test]
    fn user_vma_alignment_length_and_order_fail_closed() {
        let page = pages();
        let window = PhysicalRange::new(0x1000, 0x10_000).unwrap();
        for (start, end, expected) in [
            (0x1001, 0x2000, MappingError::Misaligned),
            (0x1000, 0x2001, MappingError::Misaligned),
            (0x1000, 0x1000, MappingError::ZeroLength),
            (0x2000, 0x1000, MappingError::ZeroLength),
        ] {
            assert_eq!(
                UserMmapRequest::validate(
                    start,
                    end,
                    1,
                    page,
                    window,
                    protection(),
                    policy(),
                ),
                Err(expected)
            );
        }
    }

    #[test]
    fn page_offset_conversion_rejects_numeric_overflow() {
        let page = pages();
        assert_eq!(
            page.pfn_to_address((u64::MAX >> page.shift()) + 1),
            Err(MappingError::AddressOverflow)
        );
        assert_eq!(
            UserMmapRequest::validate(
                0x1000,
                0x2000,
                (u64::MAX >> page.shift()) + 1,
                page,
                PhysicalRange::new(0, u64::MAX).unwrap(),
                protection(),
                policy(),
            ),
            Err(MappingError::AddressOverflow)
        );
    }

    #[test]
    fn authorized_physical_window_is_end_exclusive() {
        let page = pages();
        let window = PhysicalRange::new(0x20_0000, 0x4000).unwrap();
        assert!(UserMmapRequest::validate(
            0x1000,
            0x5000,
            0x200,
            page,
            window,
            protection(),
            policy(),
        )
        .is_ok());
        assert_eq!(
            UserMmapRequest::validate(
                0x1000,
                0x6000,
                0x200,
                page,
                window,
                protection(),
                policy(),
            ),
            Err(MappingError::OutsidePhysicalWindow)
        );
        assert_eq!(
            UserMmapRequest::validate(
                0x1000,
                0x2000,
                0x1ff,
                page,
                window,
                protection(),
                policy(),
            ),
            Err(MappingError::OutsidePhysicalWindow)
        );
    }

    #[test]
    fn cache_policy_values_match_frozen_ihk_flags_only() {
        assert_eq!(CachePolicy::from_legacy_flag(0), Ok(CachePolicy::Cached));
        assert_eq!(
            CachePolicy::from_legacy_flag(1),
            Ok(CachePolicy::Uncached)
        );
        assert_eq!(CachePolicy::Cached.legacy_flag(), 0);
        assert_eq!(CachePolicy::Uncached.legacy_flag(), 1);
        for invalid in [-2, -1, 2, i32::MAX] {
            assert_eq!(
                CachePolicy::from_legacy_flag(invalid),
                Err(MappingError::InvalidCachePolicy)
            );
        }
    }

    #[test]
    fn kernel_mapping_descriptor_covers_pages_and_preserves_offset() {
        let descriptor = KernelMapDescriptor::new(
            PhysicalRange::new(0x12_345, 0x2345).unwrap(),
            Some(0x82_345),
            CachePolicy::Uncached,
            pages(),
        )
        .unwrap();
        assert_eq!(descriptor.requested().start(), 0x12_345);
        assert_eq!(descriptor.mapped().start(), 0x12_000);
        assert_eq!(descriptor.mapped().end(), 0x15_000);
        assert_eq!(descriptor.byte_offset(), 0x345);
        assert_eq!(descriptor.desired_virtual_base(), Some(0x82_000));
        assert_eq!(descriptor.cache_policy(), CachePolicy::Uncached);
        assert_eq!(
            KernelMapDescriptor::new(
                PhysicalRange::new(0x12_345, 0x100).unwrap(),
                Some(0x82_000),
                CachePolicy::Cached,
                pages(),
            ),
            Err(MappingError::Misaligned)
        );
        assert_eq!(
            KernelMapDescriptor::new(
                PhysicalRange::new(0x12_000, 0x100).unwrap(),
                Some(0),
                CachePolicy::Cached,
                pages(),
            ),
            Err(MappingError::ZeroMappedAddress)
        );
        assert_eq!(
            KernelMapDescriptor::new(
                PhysicalRange::new(0x12_345, 0x100).unwrap(),
                Some(0x345),
                CachePolicy::Cached,
                pages(),
            ),
            Err(MappingError::ZeroMappedAddress)
        );
    }

    #[test]
    fn kernel_mapping_descriptor_checks_the_full_page_padded_virtual_extent() {
        let requested = PhysicalRange::new(0x1ff0, 1).unwrap();
        assert!(KernelMapDescriptor::new(
            requested,
            Some(0xffff_ffff_ffff_eff0),
            CachePolicy::Cached,
            pages(),
        )
        .is_ok());
        assert_eq!(
            KernelMapDescriptor::new(
                requested,
                Some(0xffff_ffff_ffff_fff0),
                CachePolicy::Cached,
                pages(),
            ),
            Err(MappingError::AddressOverflow)
        );
    }

    #[test]
    fn protection_policy_is_explicit_and_fail_closed() {
        let base = protection();
        assert_eq!(policy().validate(base), Ok(()));
        for invalid in [
            MmapProtection {
                readable: false,
                ..base
            },
            MmapProtection {
                executable: true,
                ..base
            },
            MmapProtection {
                shared: false,
                ..base
            },
        ] {
            assert_eq!(
                policy().validate(invalid),
                Err(MappingError::InvalidProtection)
            );
        }
        let read_only = MmapProtectionPolicy {
            allow_write: false,
            ..policy()
        };
        assert_eq!(
            read_only.validate(base),
            Err(MappingError::InvalidProtection)
        );
    }

    #[test]
    fn adapter_errno_range_and_local_mapping_are_checked() {
        assert_eq!(LinuxErrno::from_adapter(-1).unwrap().get(), -1);
        assert_eq!(LinuxErrno::from_adapter(-4095).unwrap().get(), -4095);
        for invalid in [-4096, 0, 1] {
            assert_eq!(
                LinuxErrno::from_adapter(invalid),
                Err(MappingError::InvalidAdapterErrno)
            );
        }
        let request = request(0x20, 2);
        let mapping = DeviceMapping::new(request, 0x90_000, pages()).unwrap();
        assert_eq!(mapping.local().length(), request.length());
        assert_eq!(mapping.local_pfn(), 0x90);
        assert_eq!(
            DeviceMapping::new(request, 0xffff_ffff_ffff_f000, pages()),
            Err(MappingError::AddressOverflow)
        );
    }

    #[test]
    fn pre_mapping_failure_has_no_cleanup_and_preserves_errno() {
        let mut transaction = MmapTransaction::new(request(0x20, 1));
        let errno = LinuxErrno::from_adapter(-5).unwrap();
        let mut plan = transaction.rollback(errno).unwrap();
        assert_eq!(plan.errno(), Some(errno));
        assert_eq!(plan.next_step(), None);
        assert_eq!(plan.next_step(), None);
        assert_eq!(transaction.stage(), MmapStage::Terminal);
    }

    #[test]
    fn remap_failure_releases_device_mapping_once() {
        let request = request(0x20, 2);
        let mapping = DeviceMapping::new(request, 0xa0_000, pages()).unwrap();
        let mut transaction = MmapTransaction::new(request);
        transaction.record_device_mapping(mapping).unwrap();
        let mut plan = transaction.rollback(LinuxErrno::ENOMEM).unwrap();
        assert_eq!(plan.errno(), Some(LinuxErrno::ENOMEM));
        assert_eq!(
            plan.next_step(),
            Some(CleanupStep::UnmapDevice {
                local: mapping.local()
            })
        );
        assert_eq!(plan.next_step(), None);
        assert_eq!(plan.next_step(), None);
        assert_eq!(
            transaction.record_user_remap(),
            Err(MappingError::InvalidTransition)
        );
    }

    #[test]
    fn metadata_failure_orders_user_then_device_rollback() {
        let request = request(0x20, 2);
        let mapping = DeviceMapping::new(request, 0xb0_000, pages()).unwrap();
        let mut transaction = MmapTransaction::new(request);
        transaction.record_device_mapping(mapping).unwrap();
        transaction.record_user_remap().unwrap();
        let errno = LinuxErrno::from_adapter(-12).unwrap();
        let mut plan = transaction.rollback(errno).unwrap();
        assert_eq!(plan.errno(), Some(errno));
        assert_eq!(
            plan.next_step(),
            Some(CleanupStep::UnmapUser {
                user_start: request.user_start(),
                length: request.length(),
            })
        );
        assert_eq!(
            plan.next_step(),
            Some(CleanupStep::UnmapDevice {
                local: mapping.local()
            })
        );
        assert_eq!(plan.next_step(), None);
    }

    #[test]
    fn live_mapping_close_is_terminal_without_failure_errno() {
        let request = request(0x20, 1);
        let mapping = DeviceMapping::new(request, 0xc0_000, pages()).unwrap();
        let mut transaction = MmapTransaction::new(request);
        transaction.record_device_mapping(mapping).unwrap();
        transaction.record_user_remap().unwrap();
        transaction.record_metadata_installed().unwrap();
        assert_eq!(transaction.stage(), MmapStage::Live);
        let mut plan = transaction.vma_close().unwrap();
        assert_eq!(plan.errno(), None);
        assert_eq!(
            plan.next_step(),
            Some(CleanupStep::UnmapDevice {
                local: mapping.local()
            })
        );
        assert_eq!(plan.next_step(), None);
        assert_eq!(plan.next_step(), None);
        assert_eq!(
            transaction.vma_close(),
            Err(MappingError::InvalidTransition)
        );
    }

    #[test]
    fn rejected_live_rollback_preserves_the_required_close_cleanup() {
        let request = request(0x20, 1);
        let mapping = DeviceMapping::new(request, 0xc0_000, pages()).unwrap();
        let mut transaction = MmapTransaction::new(request);
        transaction.record_device_mapping(mapping).unwrap();
        transaction.record_user_remap().unwrap();
        transaction.record_metadata_installed().unwrap();

        assert_eq!(
            transaction.rollback(LinuxErrno::ENOMEM),
            Err(MappingError::InvalidTransition)
        );
        assert_eq!(transaction.stage(), MmapStage::Live);
        let mut plan = transaction.vma_close().unwrap();
        assert_eq!(plan.errno(), None);
        assert_eq!(
            plan.next_step(),
            Some(CleanupStep::UnmapDevice {
                local: mapping.local()
            })
        );
        assert_eq!(plan.next_step(), None);
    }

    #[test]
    fn transaction_rejects_mapping_for_another_request() {
        let first = request(0x20, 1);
        let second = request(0x30, 1);
        let foreign = DeviceMapping::new(second, 0xd0_000, pages()).unwrap();
        let mut transaction = MmapTransaction::new(first);
        assert_eq!(
            transaction.record_device_mapping(foreign),
            Err(MappingError::TranslationMismatch)
        );
        assert_eq!(transaction.stage(), MmapStage::Validated);
    }

    #[test]
    fn property_covering_range_is_aligned_minimal_and_contains_input() {
        let page = pages();
        let mut state = 0x8a5c_d789_635d_2dff_u64;
        for _ in 0..20_000 {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            let start = state & 0x0000_ffff_ffff_ffff;
            state ^= state.rotate_left(17);
            let length = (state & 0xffff) + 1;
            let range = PhysicalRange::new(start, length).unwrap();
            let covered = range.covering_pages(page).unwrap();
            assert!(page.is_aligned(covered.start()));
            assert!(page.is_aligned(covered.end()));
            assert!(covered.range().contains(range));
            assert!(start - covered.start() < page.size());
            assert!(covered.end() - range.end() < page.size());
        }
    }

    #[test]
    fn property_page_requests_round_trip_without_overlap_or_truncation() {
        let page = pages();
        let window = PhysicalRange::new(0x1000_0000, 0x1000_0000).unwrap();
        let mut state = 0x1234_5678_9abc_def0_u64;
        for _ in 0..10_000 {
            state = state.wrapping_mul(2_862_933_555_777_941_757).wrapping_add(3_037_000_493);
            let relative_page = state % 0x8000;
            let count = ((state >> 32) % 64) + 1;
            let physical = window.start() + relative_page * page.size();
            let request = UserMmapRequest::validate(
                0x4000_0000,
                0x4000_0000 + count * page.size(),
                physical >> page.shift(),
                page,
                window,
                protection(),
                policy(),
            )
            .unwrap();
            assert_eq!(request.physical().start(), physical);
            assert_eq!(request.physical().length(), count * page.size());
            assert!(window.contains(request.physical().range()));
        }
    }

    #[test]
    fn error_classes_map_to_stable_negative_errno_values() {
        assert_eq!(MappingError::AddressOverflow.errno(), LinuxErrno::EOVERFLOW);
        assert_eq!(MappingError::InvalidTransition.errno(), LinuxErrno::EALREADY);
        for error in [
            MappingError::InvalidPageShift,
            MappingError::ZeroLength,
            MappingError::Misaligned,
            MappingError::OutsidePhysicalWindow,
            MappingError::InvalidCachePolicy,
            MappingError::InvalidProtection,
            MappingError::InvalidAdapterErrno,
            MappingError::ZeroMappedAddress,
            MappingError::TranslationMismatch,
        ] {
            assert_eq!(error.errno(), LinuxErrno::EINVAL);
        }
        assert_eq!(LinuxErrno::ENOSYS.get(), -38);
    }

    #[test]
    fn aligned_range_constructor_rejects_partial_pages() {
        let page = pages();
        assert_eq!(
            AlignedPhysicalRange::from_start_length(0x1001, 0x1000, page),
            Err(MappingError::Misaligned)
        );
        assert_eq!(
            AlignedPhysicalRange::from_start_length(0x1000, 0x1001, page),
            Err(MappingError::Misaligned)
        );
    }
}
