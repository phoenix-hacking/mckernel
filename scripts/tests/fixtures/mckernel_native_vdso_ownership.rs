// Included beside the complete production descriptor ownership/write adapter.
use super::smp_resource::{MemoryExtent, MemoryWorkspace, OsToken};

#[repr(align(4096))]
struct GuestStorage([u8; 65536]);

fn assigned_map(owner: OsToken) -> MemoryMap<MAX_EXTENTS> {
    let mut map = MemoryMap::new();
    let mut slots = [None; MAX_EXTENTS];
    let mut workspace = MemoryWorkspace::new(&mut slots).unwrap();
    map.insert_free(0x100000, 65536, 0, &mut workspace).unwrap();
    let extent = MemoryExtent::new(0x100000, 65536, 0, None).unwrap();
    let mut transaction = map
        .prepare_assign_batch(owner, &[extent], &mut workspace)
        .unwrap();
    transaction.begin_external_effects().unwrap();
    transaction.commit().unwrap();
    map
}

#[test]
fn exact_owner_whole_extent_all_queue_aliases_and_linux_page_exclusion() {
    use super::vdso_protocol::{Descriptor, BYTES};
    let owner = OsToken::test_only(0, 1).unwrap();
    let stale = OsToken::test_only(0, 2).unwrap();
    let map = assigned_map(owner);
    let mut storage = Box::new(GuestStorage([0xa5; 65536]));
    let linear = storage.0.as_mut_ptr() as u64 - 0x100000;
    let argument = 0x100fc0;
    let channels = [OwnedControlChannel {
        channel: FakeChannel {
            owner,
            receive_physical: 0x104000,
            send_physical: 0x10c000,
        },
    }];
    let request = Descriptor::request().encode();
    storage.0[0xfc0..0xfc0 + BYTES].copy_from_slice(&request);
    let before = storage.0;
    for physical in [
        0,
        argument + 1,
        0x10ffc0,
        0x120000,
        u64::MAX - 63,
        0x108008,
        0x109008,
        0x104008,
        0x107fc0,
        0x10c008,
    ] {
        assert_eq!(
            reply_vdso(&map, owner, linear, physical, 0x108000, 0x109000, 4096, &channels),
            Err(EINVAL)
        );
        assert_eq!(storage.0, before);
    }
    assert_eq!(
        reply_vdso(&map, stale, linear, argument, 0x108000, 0x109000, 4096, &channels),
        Err(EINVAL)
    );
    assert_eq!(
        reply_vdso(
            &map,
            owner,
            u64::MAX - 0x100000 + 16,
            argument,
            0x108000,
            0x109000,
            4096,
            &channels
        ),
        Err(EINVAL)
    );
    let wrong_channels = [OwnedControlChannel {
        channel: FakeChannel {
            owner: stale,
            receive_physical: 0x104000,
            send_physical: 0x10c000,
        },
    }];
    assert_eq!(
        reply_vdso(
            &map,
            owner,
            linear,
            argument,
            0x108000,
            0x109000,
            4096,
            &wrong_channels
        ),
        Err(EIO)
    );
    assert_eq!(storage.0, before);
    let mut overlap = assigned_map(owner);
    let mut slots = [None; MAX_EXTENTS];
    let mut workspace = MemoryWorkspace::new(&mut slots).unwrap();
    // Even a currently free reserved-pool extent cannot own Linux vDSO pages.
    overlap
        .insert_free(0x2000, 16384, 0, &mut workspace)
        .unwrap();
    assert_eq!(
        reply_vdso(&overlap, owner, linear, argument, 0x108000, 0x109000, 4096, &channels),
        Err(EIO)
    );
    assert_eq!(storage.0, before);
    assert!(reply_vdso(&map, owner, linear, argument, 0x108000, 0x109000, 4096, &channels).is_ok());
    assert_eq!(
        unsafe { super::vdso_protocol::read_response(storage.0.as_ptr().add(0xfc0)) }.unwrap(),
        super::smp_vdso::collect().unwrap()
    );
    assert_eq!(&storage.0[..0xfc0], &before[..0xfc0]);
    assert_eq!(&storage.0[0xfc0 + BYTES..], &before[0xfc0 + BYTES..]);
}
