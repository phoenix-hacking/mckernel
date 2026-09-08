#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/ihk_mapping.rs"]
mod ihk_mapping;
#[path = "../../../host-kernel/native-rust/smp_resource.rs"]
mod smp_resource;
#[path = "../../../host-kernel/native-rust/smp_image.rs"]
mod smp_image;

#[cfg(test)]
mod image_tests {
    use super::smp_image::*;
    use super::smp_resource::*;

    fn owner(slot: u32, generation: u64) -> OsToken {
        OsToken::test_only(slot, generation).unwrap()
    }

    fn add(map: &mut MemoryMap<16>, token: OsToken, start: u64, length: u64, node: u32) {
        let mut slots = [None; 16];
        let mut workspace = MemoryWorkspace::new(&mut slots).unwrap();
        map.insert_free(start, length, node, &mut workspace)
            .unwrap();
        let extent = MemoryExtent::new(start, length, node, None).unwrap();
        let mut transaction = map
            .prepare_assign_batch(token, &[extent], &mut workspace)
            .unwrap();
        transaction.begin_external_effects().unwrap();
        transaction.commit().unwrap();
    }

    fn layout() -> BootLayout {
        let mut map = MemoryMap::new();
        add(&mut map, owner(0, 1), 0x4000_0000, 64 << 20, 1);
        BootLayout::select(&map, owner(0, 1)).unwrap()
    }

    fn put16(out: &mut [u8], at: usize, value: u16) {
        out[at..at + 2].copy_from_slice(&value.to_le_bytes());
    }
    fn put32(out: &mut [u8], at: usize, value: u32) {
        out[at..at + 4].copy_from_slice(&value.to_le_bytes());
    }
    fn put64(out: &mut [u8], at: usize, value: u64) {
        out[at..at + 8].copy_from_slice(&value.to_le_bytes());
    }

    fn elf() -> Vec<u8> {
        let mut image = vec![0; 0x2017];
        image[..7].copy_from_slice(b"\x7fELF\x02\x01\x01");
        put16(&mut image, 16, 2);
        put16(&mut image, 18, 62);
        put32(&mut image, 20, 1);
        put64(&mut image, 24, KERNEL_BASE + 0x1000);
        put64(&mut image, 32, 64);
        put16(&mut image, 52, 64);
        put16(&mut image, 54, 56);
        put16(&mut image, 56, 2);
        for (at, flags, offset, address, file, memory) in [
            (64, 5, 0x1000, 0x1000, 0x21, 0x70),
            (120, 6, 0x2000, 0x3000, 0x17, 0x71),
        ] {
            put32(&mut image, at, 1);
            put32(&mut image, at + 4, flags);
            put64(&mut image, at + 8, offset);
            put64(&mut image, at + 16, KERNEL_BASE + address);
            put64(&mut image, at + 24, KERNEL_BASE + address);
            put64(&mut image, at + 32, file);
            put64(&mut image, at + 40, memory);
            put64(&mut image, at + 48, 4096);
            for index in 0..file {
                image[(offset + index) as usize] = (index * 13 + address / 4096) as u8;
            }
        }
        image
    }

    fn with_native_note(header_bytes: u32, performance: u32) -> Vec<u8> {
        let mut image = elf();
        put16(&mut image, 56, 3);
        put32(&mut image, 176, 4);
        put64(&mut image, 184, 0x300);
        put64(&mut image, 208, 40);
        put64(&mut image, 216, 40);
        put64(&mut image, 224, 4);
        put32(&mut image, 0x300, 9);
        put32(&mut image, 0x304, 16);
        put32(&mut image, 0x308, 0x4d43_4b01);
        image[0x30c..0x315].copy_from_slice(b"MCKERNEL\0");
        put32(&mut image, 0x318, 1);
        put32(&mut image, 0x31c, 0x0006_0c00);
        put32(&mut image, 0x320, header_bytes);
        put32(&mut image, 0x324, performance);
        image
    }

    #[test]
    fn native_boot_requires_explicit_layout_metadata_but_legacy_still_loads() {
        let legacy = elf();
        assert_eq!(
            ImagePlan::parse(&legacy, layout())
                .unwrap()
                .native_boot_abi(),
            None
        );
        for (header_bytes, flag) in [(6656, 0), (7616, 1)] {
            let image = with_native_note(header_bytes, flag);
            let plan = ImagePlan::parse(&image, layout()).unwrap();
            assert_eq!(
                plan.native_boot_abi(),
                Some(NativeBootAbi {
                    header_bytes: header_bytes as usize,
                    performance: flag == 1,
                    completed_queue_reads: false,
                    generic_vdso: false,
                })
            );
            assert_eq!(plan.load_segments(), 2);
        }
    }

    #[test]
    fn native_revisions_advertise_independent_queue_and_vdso_contracts() {
        for revision in [2, 3] {
            for (header_bytes, flag) in [(6656, 0), (7616, 1)] {
                let mut image = with_native_note(header_bytes, flag);
                put32(&mut image, 0x318, revision);
                let plan = ImagePlan::parse(&image, layout()).unwrap();
                assert_eq!(
                    plan.native_boot_abi(),
                    Some(NativeBootAbi {
                        header_bytes: header_bytes as usize,
                        performance: flag == 1,
                        completed_queue_reads: true,
                        generic_vdso: revision == 3,
                    })
                );
                assert_eq!(plan.load_segments(), 2);
            }
        }
    }

    #[test]
    fn wrong_native_abi_version_layout_flags_and_duplicates_are_rejected() {
        for (at, value) in [
            (0x318, 0),
            (0x318, 4),
            (0x31c, 0x0005_0000),
            (0x320, 6656),
            (0x320, 7615),
            (0x324, 0),
            (0x324, 3),
        ] {
            let mut image = with_native_note(7616, 1);
            put32(&mut image, at, value);
            assert!(
                ImagePlan::parse(&image, layout()).is_err(),
                "at={at:x} value={value}"
            );
        }
        let mut image = with_native_note(7616, 1);
        image.copy_within(0x300..0x328, 0x328);
        put64(&mut image, 208, 80);
        assert!(ImagePlan::parse(&image, layout()).is_err());
        let mut image = with_native_note(7616, 1);
        image.copy_within(176..232, 232);
        put16(&mut image, 56, 4);
        assert!(ImagePlan::parse(&image, layout()).is_err());
    }

    #[test]
    fn note_extents_and_internal_lengths_are_checked_before_acceptance() {
        for length in 1..40 {
            let mut image = with_native_note(7616, 1);
            put64(&mut image, 208, length);
            assert!(
                ImagePlan::parse(&image, layout()).is_err(),
                "length={length}"
            );
        }
        for length in [4097, u64::MAX] {
            let mut image = with_native_note(7616, 1);
            put64(&mut image, 208, length);
            assert!(ImagePlan::parse(&image, layout()).is_err());
        }
        for at in [0x300, 0x304] {
            let mut image = with_native_note(7616, 1);
            put32(&mut image, at, u32::MAX);
            assert!(ImagePlan::parse(&image, layout()).is_err());
        }
        let mut image = with_native_note(7616, 1);
        put64(&mut image, 184, u64::MAX - 16);
        assert!(ImagePlan::parse(&image, layout()).is_err());
    }

    #[test]
    fn unrelated_notes_do_not_advertise_native_boot_compatibility() {
        let mut image = with_native_note(7616, 1);
        image[0x30c] = b'X';
        assert_eq!(
            ImagePlan::parse(&image, layout())
                .unwrap()
                .native_boot_abi(),
            None
        );
        let mut image = with_native_note(7616, 1);
        put32(&mut image, 0x308, 0x4d43_4b02);
        assert_eq!(
            ImagePlan::parse(&image, layout())
                .unwrap()
                .native_boot_abi(),
            None
        );
    }

    #[test]
    fn selection_uses_only_exact_generation_before_numa_preference() {
        let mut map = MemoryMap::new();
        add(&mut map, owner(1, 1), 0x1000_0000, 64 << 20, 0);
        add(&mut map, owner(0, 1), 0x2000_0000, 32 << 20, 1);
        add(&mut map, owner(0, 1), 0x3000_0000, 64 << 20, 2);
        add(&mut map, owner(0, 1), 0x4000_0000, 48 << 20, 1);
        let selected = BootLayout::select(&map, owner(0, 1)).unwrap();
        assert_eq!(selected.extent().start(), 0x4000_0000);
        assert_eq!(selected.extent().numa_node(), 1);
        assert_eq!(
            BootLayout::select(&map, owner(0, 2)),
            Err(ImageError::NoBootstrapMemory)
        );
    }

    #[test]
    fn layout_preserves_legacy_placement_and_owned_startup_reservations() {
        let value = layout();
        assert_eq!(value.kernel().start(), 0x4020_0000);
        assert_eq!(value.kernel().end(), 0x40a0_0000);
        assert_eq!(value.startup(), 0x43c0_0000);
        assert_eq!(value.stack(), 0x43ff_f000);
        for misalignment in 0..512_u64 {
            let start = 0x8000_0000 + misalignment * 4096;
            let mut map = MemoryMap::new();
            add(&mut map, owner(0, 1), start, 16 << 20, 0);
            let value = BootLayout::select(&map, owner(0, 1)).unwrap();
            assert_eq!(value.kernel().start(), (start + 0x3f_ffff) & !0x1f_ffff);
            assert!(value.kernel().end() <= value.startup());
            assert!(value.startup() >= start && value.stack() < start + (16 << 20));
        }
    }

    #[test]
    fn small_extents_and_outside_identity_space_never_yield_layouts() {
        for (start, length) in [
            (0, 4096),
            (0x4000_0000, 12 << 20),
            (IDENTITY_WINDOW_END - (8 << 20), 64 << 20),
        ] {
            let mut map = MemoryMap::new();
            add(&mut map, owner(0, 1), start, length, 0);
            assert_eq!(
                BootLayout::select(&map, owner(0, 1)),
                Err(ImageError::OutsideBootstrap)
            );
        }
    }

    #[test]
    fn valid_segments_preserve_bytes_bss_holes_and_entry() {
        let image = elf();
        let plan = ImagePlan::parse(&image, layout()).unwrap();
        assert_eq!(plan.entry(), KERNEL_BASE + 0x1000);
        assert_eq!(plan.load_segments(), 2);
        let mut destination = vec![0_u8; KERNEL_WINDOW_BYTES as usize];
        for segment in plan.segments() {
            let start = (segment.destination - plan.layout().kernel().start()) as usize;
            destination[start..start + segment.file.len()].copy_from_slice(segment.file);
        }
        assert_eq!(&destination[0x1000..0x1021], &image[0x1000..0x1021]);
        assert_eq!(&destination[0x3000..0x3017], &image[0x2000..0x2017]);
        assert!(destination[..0x1000].iter().all(|b| *b == 0));
        assert!(destination[0x1021..0x3000].iter().all(|b| *b == 0));
        assert!(destination[0x3017..].iter().all(|b| *b == 0));
    }

    #[test]
    fn every_truncated_file_is_rejected_before_a_plan_is_available() {
        let image = elf();
        for length in 0..image.len() {
            assert!(
                ImagePlan::parse(&image[..length], layout()).is_err(),
                "length={length}"
            );
        }
    }

    #[test]
    fn wrong_class_endianness_type_architecture_and_header_shape_are_rejected() {
        for (offset, value) in [
            (0, 0),
            (4, 1),
            (5, 2),
            (6, 0),
            (16, 3),
            (18, 3),
            (20, 2),
            (48, 1),
            (52, 63),
            (54, 57),
            (56, 0),
        ] {
            let mut image = elf();
            image[offset] = value;
            assert!(
                ImagePlan::parse(&image, layout()).is_err(),
                "offset={offset}"
            );
        }
        for phoff in [0, 63, 4096, u64::MAX, u64::MAX - 55] {
            let mut image = elf();
            put64(&mut image, 32, phoff);
            assert!(ImagePlan::parse(&image, layout()).is_err());
        }
        for count in [65, 72, 0xffff] {
            let mut image = elf();
            put16(&mut image, 56, count);
            assert!(ImagePlan::parse(&image, layout()).is_err());
        }
    }

    #[test]
    fn malformed_later_segment_never_produces_a_partial_plan() {
        for (offset, value) in [
            (8, u64::MAX),
            (16, KERNEL_BASE - 1),
            (16, KERNEL_BASE + KERNEL_WINDOW_BYTES),
            (32, 0x72),
            (40, u64::MAX),
            (40, 0),
            (48, 3),
        ] {
            let mut image = elf();
            put64(&mut image, 120 + offset, value);
            assert!(
                ImagePlan::parse(&image, layout()).is_err(),
                "offset={offset}"
            );
        }
        for kind in [2, 3, 7, u32::MAX] {
            let mut image = elf();
            put32(&mut image, 120, kind);
            assert_eq!(
                ImagePlan::parse(&image, layout()).err(),
                Some(ImageError::BadElf)
            );
        }
        let mut image = elf();
        put32(&mut image, 124, 8);
        assert_eq!(
            ImagePlan::parse(&image, layout()).err(),
            Some(ImageError::BadElf)
        );
    }

    #[test]
    fn entry_must_be_file_backed_and_executable() {
        for entry in [
            0,
            KERNEL_BASE,
            KERNEL_BASE + 0x1021,
            KERNEL_BASE + 0x3000,
            KERNEL_BASE + KERNEL_WINDOW_BYTES,
            u64::MAX,
        ] {
            let mut image = elf();
            put64(&mut image, 24, entry);
            assert_eq!(
                ImagePlan::parse(&image, layout()).err(),
                Some(ImageError::BadEntry)
            );
        }
        let mut image = elf();
        put32(&mut image, 68, 6);
        assert_eq!(
            ImagePlan::parse(&image, layout()).err(),
            Some(ImageError::BadEntry)
        );
    }

    #[test]
    fn overlap_including_bss_is_rejected_but_adjacent_segments_are_allowed() {
        for address in [0x1000, 0x1020, 0x1030, 0x106f] {
            let mut image = elf();
            put64(&mut image, 136, KERNEL_BASE + address);
            put64(&mut image, 168, 1);
            assert_eq!(
                ImagePlan::parse(&image, layout()).err(),
                Some(ImageError::SegmentOverlap)
            );
        }
        let mut image = elf();
        put64(&mut image, 136, KERNEL_BASE + 0x1070);
        put64(&mut image, 168, 1);
        assert!(ImagePlan::parse(&image, layout()).is_ok());
    }

    #[test]
    fn immutable_segments_can_be_reordered_and_zero_file_data_is_valid() {
        let mut image = elf();
        let first: Vec<_> = image[64..120].to_vec();
        image.copy_within(120..176, 64);
        image[120..176].copy_from_slice(&first);
        put64(&mut image, 96, 0);
        let plan = ImagePlan::parse(&image, layout()).unwrap();
        assert_eq!(plan.segments().next().unwrap().file.len(), 0);
        assert_eq!(plan.load_segments(), 2);
    }

    #[test]
    fn malformed_header_corpus_never_panics_or_leaves_the_owned_window() {
        let original = elf();
        let mut seed = 0x81a6_23db_u64;
        for _ in 0..4096 {
            let mut image = original.clone();
            for _ in 0..4 {
                seed ^= seed << 13;
                seed ^= seed >> 7;
                seed ^= seed << 17;
                let offset = seed as usize % 176;
                image[offset] ^= (seed >> 40) as u8;
            }
            if let Ok(plan) = ImagePlan::parse(&image, layout()) {
                for segment in plan.segments() {
                    assert!(segment.destination >= plan.layout().kernel().start());
                    assert!(
                        segment.destination + segment.memory_bytes <= plan.layout().kernel().end()
                    );
                    assert!(segment.file.len() as u64 <= segment.memory_bytes);
                }
            }
        }
    }
}
