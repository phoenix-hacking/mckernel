#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/ihk_mapping.rs"]
mod ihk_mapping;
#[path = "../../../host-kernel/native-rust/smp_resource.rs"]
mod smp_resource;
#[path = "../../../host-kernel/native-rust/smp_image.rs"]
mod smp_image;
#[path = "../../../host-kernel/native-rust/smp_startup.rs"]
mod smp_startup;

use smp_image::{BootLayout, KERNEL_BASE};
use smp_resource::{MemoryExtent, MemoryMap, MemoryWorkspace, OsToken};
use smp_startup::{PageTablePlan, StartupError, TABLE_BYTES};

fn layout(physical: u64) -> BootLayout {
    let owner = OsToken::test_only(0, 1).unwrap();
    let mut map = MemoryMap::<4>::new();
    let mut slots = [None; 4];
    let mut workspace = MemoryWorkspace::new(&mut slots).unwrap();
    map.insert_free(physical, 64 << 20, 0, &mut workspace)
        .unwrap();
    let extent = MemoryExtent::new(physical, 64 << 20, 0, None).unwrap();
    let mut transaction = map
        .prepare_assign_batch(owner, &[extent], &mut workspace)
        .unwrap();
    transaction.begin_external_effects().unwrap();
    transaction.commit().unwrap();
    BootLayout::select(&map, owner).unwrap()
}

// Independent x86 page-table walker. It uses the encoded entries and address
// bits, not the planner's page indices or mapping-generation implementation.
fn translate(tables: &[u64], root: u64, virtual_address: u64) -> Option<u64> {
    let canonical = virtual_address >> 47;
    if canonical != 0 && canonical != 0x1ffff {
        return None;
    }
    let mut physical = root;
    for shift in [39, 30, 21] {
        let offset = physical.checked_sub(root)? / 8;
        let index = (virtual_address >> shift) & 511;
        let entry = *tables.get((offset + index) as usize)?;
        if entry & 1 == 0 {
            return None;
        }
        if shift == 21 {
            if entry & 128 == 0 {
                return None;
            }
            return Some((entry & 0x000f_ffff_ffe0_0000) | (virtual_address & 0x1f_ffff));
        }
        if entry & 128 != 0 {
            return None;
        }
        physical = entry & 0x000f_ffff_ffff_f000;
    }
    None
}

#[test]
fn all_identity_and_straight_leaves_have_exact_physical_translation() {
    let plan = PageTablePlan::new(0x20_0000, layout(0x100_0000)).unwrap();
    let mut tables = vec![0xdead_beef; TABLE_BYTES / 8];
    plan.fill(&mut tables).unwrap();
    for leaf in 0..131_072_u64 {
        for offset in [0, 4095, 0x1f_ffff] {
            let address = (leaf << 21) | offset;
            assert_eq!(translate(&tables, plan.root(), address), Some(address));
            assert_eq!(
                translate(&tables, plan.root(), 0xffff_8000_0000_0000 + address),
                Some(address)
            );
        }
    }
}

#[test]
fn kernel_window_matches_owned_placement_including_above_four_gib() {
    for physical in [0x100_0000, 0x1_0000_0000, (256_u64 << 30) - (64 << 20)] {
        let layout = layout(physical);
        let plan = PageTablePlan::new(0x20_0000, layout).unwrap();
        let mut tables = vec![0; TABLE_BYTES / 8];
        plan.fill(&mut tables).unwrap();
        for offset in (0..(8_u64 << 20)).step_by(4096) {
            assert_eq!(
                translate(&tables, plan.root(), KERNEL_BASE + offset),
                Some(layout.kernel().start() + offset)
            );
        }
        assert_eq!(translate(&tables, plan.root(), KERNEL_BASE - 1), None);
        assert_eq!(
            translate(&tables, plan.root(), KERNEL_BASE + (8 << 20)),
            None
        );
    }
}

#[test]
fn unmapped_holes_and_noncanonical_addresses_remain_unmapped() {
    let plan = PageTablePlan::new(0x20_0000, layout(0x100_0000)).unwrap();
    let mut tables = vec![0; TABLE_BYTES / 8];
    plan.fill(&mut tables).unwrap();
    for address in [
        256_u64 << 30,
        512_u64 << 30,
        0xffff_8040_0000_0000,
        0xffff_8080_0000_0000,
        0x0000_8000_0000_0000,
        u64::MAX,
    ] {
        assert_eq!(
            translate(&tables, plan.root(), address),
            None,
            "{address:#x}"
        );
    }
}

#[test]
fn root_alignment_width_and_allocation_overlap_are_rejected() {
    let owned = layout(0x100_0000);
    for root in [
        0,
        1,
        4095,
        4097,
        1_u64 << 32,
        (1_u64 << 32) - 4096,
        u64::MAX - 4095,
        0x100_0000,
        0x100_0000 - 4096,
        0x100_0000 + (63 << 20),
    ] {
        assert!(
            matches!(
                PageTablePlan::new(root, owned),
                Err(StartupError::TableAddress)
            ),
            "{root:#x}"
        );
    }
    assert!(PageTablePlan::new((1_u64 << 32) - TABLE_BYTES as u64, owned).is_ok());
    assert!(PageTablePlan::new(0x100_0000 - TABLE_BYTES as u64, owned).is_ok());
}

#[test]
fn bad_storage_length_is_atomic_and_indices_are_bounded() {
    let plan = PageTablePlan::new(0x20_0000, layout(0x100_0000)).unwrap();
    for length in [0, 1, TABLE_BYTES / 8 - 1, TABLE_BYTES / 8 + 1] {
        let mut storage = vec![0xfeed_face; length];
        assert_eq!(plan.fill(&mut storage), Err(StartupError::StorageSize));
        assert!(storage.iter().all(|&value| value == 0xfeed_face));
    }
    assert_eq!(plan.entry(260, 0), Err(StartupError::Index));
    assert_eq!(plan.entry(0, 512), Err(StartupError::Index));
}

#[test]
fn flags_and_all_table_pointers_stay_inside_the_owned_root_extent() {
    let plan = PageTablePlan::new(0x20_0000, layout(0x100_0000)).unwrap();
    for page in 0..260 {
        for index in 0..512 {
            let entry = plan.entry(page, index).unwrap();
            if entry == 0 {
                continue;
            }
            assert_eq!(entry & 0xfff, if entry & 128 != 0 { 0xe3 } else { 0x63 });
            if entry & 128 == 0 {
                let address = entry & !0xfff;
                assert!((plan.root()..plan.root() + TABLE_BYTES as u64).contains(&address));
            }
        }
    }
}
