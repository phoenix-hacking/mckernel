// SPDX-License-Identifier: GPL-2.0-only
// Included beside the exact production setup extent/reply bodies. The service
// callback is an effect recorder; Linux publication is checked in the real guest.
use super::smp_resource::{MemoryExtent, MemoryWorkspace, OsToken};
#[repr(align(4096))]
struct GuestStorage([u8; 65536]);
fn assigned_map(owner: OsToken) -> MemoryMap<MAX_EXTENTS> {
    let mut map = MemoryMap::new();
    let mut slots = [None; MAX_EXTENTS];
    let mut workspace = MemoryWorkspace::new(&mut slots).unwrap();
    map.insert_free(0x100000, 65536, 0, &mut workspace).unwrap();
    let extent = MemoryExtent::new(0x100000, 65536, 0, None).unwrap();
    let mut transaction = map.prepare_assign_batch(owner, &[extent], &mut workspace).unwrap();
    transaction.begin_external_effects().unwrap(); transaction.commit().unwrap();
    map
}
fn request(storage: &mut GuestStorage, buffer: u64, bytes: i64) {
    storage.0.fill(0xa5);
    storage.0[0xfc0..0xfc4].copy_from_slice(&(-115_i32).to_le_bytes());
    storage.0[0xfc8..0xfd0].copy_from_slice(&buffer.to_le_bytes());
    storage.0[0xfd0..0xfd8].copy_from_slice(&bytes.to_le_bytes());
    storage.0[0xfc0 + 1052..0xfc0 + 1056].copy_from_slice(&1_i32.to_le_bytes());
}
fn response(storage: &GuestStorage, before: &[u8; 65536], error: i32) {
    let mut expected = *before;
    expected[0xfc0..0xfc4].copy_from_slice(&error.to_le_bytes());
    expected[0xfc0 + 1052..0xfc0 + 1056].fill(0);
    assert_eq!(storage.0, expected);
}

#[test]
fn setup_checks_exact_generation_whole_extents_and_every_alias_before_writes() {
    let owner = OsToken::test_only(0, 1).unwrap();
    let stale = OsToken::test_only(0, 2).unwrap();
    let map = assigned_map(owner);
    let mut storage = Box::new(GuestStorage([0; 65536]));
    let direct = storage.0.as_mut_ptr() as u64 - 0x100000;
    let channels = [OwnedControlChannel { channel: FakeChannel {
        owner, receive_physical: 0x104000, send_physical: 0x10c000 } }];
    let mut service = super::sysfs_setup::Service::default();
    request(&mut storage, 0x102000, 4096);
    let before = storage.0;
    for physical in [0, 0x100fc1, 0x10ffc0, 0x120000, u64::MAX - 63,
        0x108008, 0x109008, 0x104008, 0x107fc0, 0x10c008, 0x10a008] {
        assert_eq!(reply_sysfs_setup(&map, owner, direct, physical, 0x108000, 0x109000,
            4096, &channels, 0x10a000, &mut service), Err(EINVAL));
        assert_eq!(storage.0, before); assert_eq!(service.calls, 0);
    }
    assert_eq!(reply_sysfs_setup(&map, stale, direct, 0x100fc0, 0x108000, 0x109000,
        4096, &channels, 0x10a000, &mut service), Err(EINVAL));
    assert_eq!(reply_sysfs_setup(&map, owner, u64::MAX - 0x100000 + 16, 0x100fc0,
        0x108000, 0x109000, 4096, &channels, 0x10a000, &mut service), Err(EINVAL));
    let wrong = [OwnedControlChannel { channel: FakeChannel {
        owner: stale, receive_physical: 0x104000, send_physical: 0x10c000 } }];
    assert_eq!(reply_sysfs_setup(&map, owner, direct, 0x100fc0, 0x108000, 0x109000,
        4096, &wrong, 0x10a000, &mut service), Err(EIO));
    assert_eq!(storage.0, before); assert_eq!(service.calls, 0);
    for buffer in [0, 1, 0x100000, 0x101000, 0x104000, 0x107000, 0x108000,
        0x109000, 0x10a000, 0x10c000, 0x110000, u64::MAX & !4095] {
        request(&mut storage, buffer, 4096); let before = storage.0;
        assert_eq!(reply_sysfs_setup(&map, owner, direct, 0x100fc0, 0x108000, 0x109000,
            4096, &channels, 0x10a000, &mut service), Err(EINVAL));
        response(&storage, &before, -22); assert_eq!(service.calls, 0);
    }
    for bytes in [-1, 0, 1, 4095, 4097, i64::MAX] {
        request(&mut storage, 0x102000, bytes); let before = storage.0;
        assert_eq!(reply_sysfs_setup(&map, owner, direct, 0x100fc0, 0x108000, 0x109000,
            4096, &channels, 0x10a000, &mut service), Err(EINVAL));
        response(&storage, &before, -22); assert_eq!(service.calls, 0);
    }
}

#[test]
fn setup_retains_data_before_acknowledgement_and_preserves_it_on_duplicate() {
    let owner = OsToken::test_only(0, 1).unwrap(); let map = assigned_map(owner);
    let mut storage = Box::new(GuestStorage([0; 65536]));
    let direct = storage.0.as_mut_ptr() as u64 - 0x100000;
    let channels = [OwnedControlChannel { channel: FakeChannel {
        owner, receive_physical: 0x104000, send_physical: 0x10c000 } }];
    let mut service = super::sysfs_setup::Service::default();
    for error in [-12, -5] {
        service.fail = Some(kernel::error::Error(error));
        request(&mut storage, 0x102000, 4096); let before = storage.0;
        assert_eq!(reply_sysfs_setup(&map, owner, direct, 0x100fc0, 0x108000, 0x109000,
            4096, &channels, 0x10a000, &mut service), Err(kernel::error::Error(error)));
        response(&storage, &before, error); assert!(service.data.is_none());
    }
    service.fail = None;
    request(&mut storage, 0x102000, 4096); let before = storage.0;
    reply_sysfs_setup(&map, owner, direct, 0x100fc0, 0x108000, 0x109000,
        4096, &channels, 0x10a000, &mut service).unwrap();
    response(&storage, &before, 0);
    let data = service.data.as_ref().unwrap();
    assert_eq!((data.owner, data.physical, data.address, data.bytes),
        (owner, 0x102000, direct + 0x102000, 4096));
    assert_eq!(service.calls, 3);
    assert!(service.overlaps(0x102000, 4096)); assert!(!service.overlaps(0x103000, 4096));
    let before = storage.0;
    assert_eq!(reply_sysfs_setup(&map, owner, direct, 0x102000, 0x108000, 0x109000,
        4096, &channels, 0x10a000, &mut service), Err(EINVAL));
    assert_eq!(storage.0, before); assert_eq!(service.calls, 3);
    request(&mut storage, 0x103000, 4096); let before = storage.0;
    assert_eq!(reply_sysfs_setup(&map, owner, direct, 0x100fc0, 0x108000, 0x109000,
        4096, &channels, 0x10a000, &mut service), Err(kernel::error::Error(-16)));
    response(&storage, &before, -16);
    assert_eq!(service.data.as_ref().unwrap().physical, 0x102000);
}
