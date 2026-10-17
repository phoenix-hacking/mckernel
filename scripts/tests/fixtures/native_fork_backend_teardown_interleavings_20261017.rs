// SPDX-License-Identifier: GPL-2.0
// Appended to the accepted actual-body generator; only these tests execute.
// Packet construction and owned Linux identities remain explicit adapters.
fn interleaving_request(pid: i32, tid: i32, root: u64, nonce: u64, response: u64) -> Request {
    let original = request(root, nonce, response, tid, FORK_NATIVE_MARKER);
    let mut bytes = [0u8; 128];
    bytes[8..12].copy_from_slice(&4i32.to_le_bytes());
    bytes[32..36].copy_from_slice(&pid.to_le_bytes());
    bytes[48..120].copy_from_slice(&original.wait_output()[8..]);
    bytes[56..64].copy_from_slice(&1u64.to_le_bytes());
    bytes[120..128].copy_from_slice(&response.to_le_bytes());
    Request::decode(&bytes, 1).unwrap()
}

#[test]
fn teardown_interleaving_two_parent_cancellation_is_independent() {
    let (mut slots, parent, child, _, _, _, released) = setup();
    let first_owner = child_owner(123);
    reserve_fork_in_slots(OsToken(0,2), &mut slots, parent, child, first_owner.clone(), geometry()).unwrap();
    let mut other_parent = entry(300, true);
    let other_child = entry(323, false);
    let worker = other_parent.syscalls.open_worker(400).unwrap();
    let (other_words, other_released) = admit(&mut other_parent.syscalls,
        interleaving_request(300, 400, 0x19000, 17, 0x1a000));
    let (serial, _) = other_parent.syscalls.reserve(worker).unwrap().unwrap();
    other_parent.syscalls.copied(worker, serial, true).unwrap();
    let other_parent_key = other_parent.key(); let other_child_key = other_child.key();
    slots.push(Some(other_parent)); slots.push(Some(other_child));
    let other_owner = Arc::new(ForkChildOwner { number: 323, mm: NonNull::new(0x2000usize as *mut ()).unwrap() });
    let other_token = reserve_fork_in_slots(OsToken(0,2), &mut slots, other_parent_key, other_child_key,
        other_owner.clone(), ForkGeometry { start: 0, length: 0x8000, root: 0x19000 }).unwrap();

    slots[0].as_mut().unwrap().syscalls.close().unwrap();
    abort_parent_forks(&mut slots, parent, None);
    assert_eq!(slots[1].as_ref().unwrap().fork.as_ref().unwrap().reservation.state.phase(), ForkPhase::AbortRequested);
    assert_eq!(slots[3].as_ref().unwrap().fork.as_ref().unwrap().reservation.state.phase(), ForkPhase::Reserved);
    assert!(slots[2].as_ref().unwrap().syscalls.unique_delivered(|_| true).unwrap().is_some());
    assert_eq!(released.load(Ordering::SeqCst), 0);
    assert_eq!(other_released.load(Ordering::SeqCst), 0);
    slots[0].as_mut().unwrap().syscalls.publish(0, |_| Ok(())).unwrap();
    observe_fork_publication(&mut slots, parent);
    assert_eq!(released.load(Ordering::SeqCst), 1);
    assert_eq!(other_released.load(Ordering::SeqCst), 0);
    commit_fork_in_slots(&mut slots, other_child_key, other_token).unwrap();
    authorize_fork_return(&slots, other_parent_key, worker, serial, 0, 323).unwrap();
    slots[2].as_mut().unwrap().syscalls.return_value(worker, serial, 0, 323, |_| Ok(())).unwrap();
    record_fork_return(&mut slots, other_parent_key, worker, serial, 323);
    slots[2].as_mut().unwrap().syscalls.publish(0, |_| Ok(())).unwrap();
    observe_fork_publication(&mut slots, other_parent_key);
    assert_eq!(other_released.load(Ordering::SeqCst), 1);
    assert_eq!(unsafe { (*other_words.0.get())[3] }, 323);
    assert_eq!(slots[3].as_ref().unwrap().fork.as_ref().unwrap().reservation.state.phase(), ForkPhase::FirstReturnPublished);
    assert_eq!(Arc::strong_count(&first_owner), 2);
    assert_eq!(Arc::strong_count(&other_owner), 2);
}

#[test]
fn teardown_interleaving_wrong_worker_close_preserves_reserved_delivery() {
    let (mut slots, parent, child, worker, _, words, released) = setup();
    let owner = child_owner(123);
    reserve_fork_in_slots(OsToken(0,2), &mut slots, parent, child, owner.clone(), geometry()).unwrap();
    let wrong = slots[0].as_mut().unwrap().syscalls.open_worker(201).unwrap();
    slots[0].as_mut().unwrap().syscalls.close_worker(wrong).unwrap();
    abort_parent_forks(&mut slots, parent, Some(wrong));
    assert_eq!(slots[1].as_ref().unwrap().fork.as_ref().unwrap().reservation.state.phase(), ForkPhase::Reserved);
    assert!(slots[0].as_ref().unwrap().syscalls.unique_delivered(|_| true).unwrap().is_some());
    assert_eq!(released.load(Ordering::SeqCst), 0);
    assert_eq!(slots[0].as_mut().unwrap().syscalls.close_worker(worker), Err(-16));
    abort_parent_forks(&mut slots, parent, Some(worker));
    assert_eq!(released.load(Ordering::SeqCst), 0);
    assert_eq!(Arc::strong_count(&owner), 2);
    let record = &slots[1].as_ref().unwrap().fork.as_ref().unwrap().reservation;
    assert_eq!(record.identity.root, 0x9000);
    assert_eq!(record.state.phase(), ForkPhase::AbortRequested);
    assert_eq!(record.state.permit_guest_destroy(record.identity), Err(EBUSY));
    slots[0].as_mut().unwrap().syscalls.publish(0, |_| Ok(())).unwrap();
    observe_fork_publication(&mut slots, parent);
    assert_eq!(released.load(Ordering::SeqCst), 1);
    assert_eq!(unsafe { (*words.0.get())[3] } as i64, -512);
    assert_eq!(Arc::strong_count(&owner), 2);
}

#[test]
fn teardown_interleaving_close_after_ret_preparation_publishes_once_and_retains_root() {
    let (mut slots, parent, child, worker, serial, words, released) = setup();
    let owner = child_owner(123);
    let token = reserve_fork_in_slots(OsToken(0,2), &mut slots, parent, child, owner.clone(), geometry()).unwrap();
    commit_fork_in_slots(&mut slots, child, token).unwrap();
    authorize_fork_return(&slots, parent, worker, serial, 0, 123).unwrap();
    slots[0].as_mut().unwrap().syscalls.return_value(worker, serial, 0, 123, |_| Ok(())).unwrap();
    record_fork_return(&mut slots, parent, worker, serial, 123);
    slots[0].as_mut().unwrap().syscalls.close().unwrap();
    abort_parent_forks(&mut slots, parent, None);
    assert_eq!(released.load(Ordering::SeqCst), 0);
    assert_eq!(slots[1].as_ref().unwrap().fork.as_ref().unwrap().reservation.state.phase(), ForkPhase::AbortRequested);
    let mut wakes = 0;
    assert!(slots[0].as_mut().unwrap().syscalls.publish(0, |_| { wakes += 1; Ok(()) }).unwrap());
    observe_fork_publication(&mut slots, parent);
    assert_eq!(released.load(Ordering::SeqCst), 1);
    assert_eq!(unsafe { (*words.0.get())[3] }, 123);
    assert_eq!(unsafe { (*words.0.get())[1] }, 1);
    assert!(!slots[0].as_mut().unwrap().syscalls.publish(0, |_| { wakes += 1; Ok(()) }).unwrap());
    observe_fork_publication(&mut slots, parent);
    assert_eq!(wakes, 1);
    assert_eq!(released.load(Ordering::SeqCst), 1);
    let record = &slots[1].as_ref().unwrap().fork.as_ref().unwrap().reservation;
    // Already prepared positive RET is irrevocable; its publication after abort
    // conservatively quarantines the transaction rather than inventing linkage.
    assert_eq!(record.state.phase(), ForkPhase::Quarantined);
    assert!(record.return_published);
    assert_eq!(record.identity.root, 0x9000);
    assert_eq!(record.state.permit_guest_destroy(record.identity), Err(EBUSY));
    assert_eq!(Arc::strong_count(&owner), 2);
}
