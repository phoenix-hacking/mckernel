@BOUNDARY_FIXTURE@

// Additional production items, copied verbatim by the driver. No transaction
// operation below is a handwritten replacement for its production decision.
@FORK_TRANSITIONS@
mod initial_mapping {
    use super::*;
    @VMA_MMAP@

    fn bootstrap(mm: &mut bindings::mm_struct) -> (Arc<Registration>, MappingFile) {
        let registration = Arc::new(Registration { calls: Cell::new(0), physical: 0x9000 });
        let owner = Arc::new(VmaOwner {
            registration: registration.clone(),
            mirror: Arc::new(Mirror { mm: MmIdentity(NonNull::from(mm)), start: 0, end: 0x8000 }),
        });
        let private = MappingFile { bootstrap: Box::pin(Mutex(RefCell::new(Some(owner)))) };
        (registration, private)
    }

    #[test]
    fn initial_validation_failure_keeps_bootstrap_until_file_release() {
        let mut mm = bindings::mm_struct { identity: 10 };
        let (registration, mut private) = bootstrap(&mut mm);
        let mut file = bindings::file { private_data: (&mut private as *mut MappingFile).cast() };
        let mut vma = vma(&mut mm, &mut file);
        vma.vm_pgoff = 1;
        assert_eq!(unsafe { mmap(&mut file, &mut vma) }, EINVAL);
        assert!(vma.vm_private_data.is_null());
        assert!(private.bootstrap.lock().is_some());
        assert_eq!(Arc::strong_count(&registration), 2);
        drop(private);
        assert_eq!(Arc::strong_count(&registration), 1);
    }

    #[test]
    fn one_shot_bootstrap_open_split_fork_close_balance_owned_references() {
        let mut parent_mm = bindings::mm_struct { identity: 10 };
        let mut child_mm = bindings::mm_struct { identity: 11 };
        let (registration, mut private) = bootstrap(&mut parent_mm);
        let mut file = bindings::file { private_data: (&mut private as *mut MappingFile).cast() };
        let mut parent = vma(&mut parent_mm, &mut file);
        assert_eq!(unsafe { mmap(&mut file, &mut parent) }, 0);
        assert!(private.bootstrap.lock().is_none());
        assert!(!parent.vm_private_data.is_null());
        let mut rejected = vma(&mut parent_mm, &mut file);
        assert_eq!(unsafe { mmap(&mut file, &mut rejected) }, EINVAL);
        assert!(rejected.vm_private_data.is_null());

        let mut split = parent;
        unsafe { vma_open(&mut split) };
        let mut child = parent;
        child.vm_mm = &mut child_mm;
        unsafe { vma_open(&mut child) };
        unsafe { vma_close(&mut parent) };
        assert_eq!(Arc::strong_count(&registration), 2);
        unsafe { vma_close(&mut split) };
        assert_eq!(Arc::strong_count(&registration), 2);
        // Neutral file bootstrap cannot extend the original registration.
        drop(private);
        unsafe { vma_close(&mut child) };
        assert_eq!(Arc::strong_count(&registration), 1);
        assert!(parent.vm_private_data.is_null());
        assert!(split.vm_private_data.is_null());
        assert!(child.vm_private_data.is_null());
    }

    #[test]
    fn successful_mmap_then_linux_close_releases_its_owner() {
        let mut mm = bindings::mm_struct { identity: 10 };
        let (registration, mut private) = bootstrap(&mut mm);
        let mut file = bindings::file { private_data: (&mut private as *mut MappingFile).cast() };
        let mut vma = vma(&mut mm, &mut file);
        assert_eq!(unsafe { mmap(&mut file, &mut vma) }, 0);
        unsafe { vma_close(&mut vma) };
        assert_eq!(Arc::strong_count(&registration), 1);
        assert!(private.bootstrap.lock().is_none());
    }
}

fn identity() -> ForkIdentity {
    ForkIdentity {
        slot: 0, generation: 2, parent: 3, worker: 4, delivery: 5, child: 6,
        child_pid: 123, child_mm: 0x1000, root: 0x9000, start: 0, length: 0x8000, nonce: 7,
    }
}

#[test]
fn identity_failures_never_adopt_or_open_access() {
    let key = identity();
    let mut variants = [key; 13];
    variants[0].slot += 1;
    variants[1].generation += 1;
    variants[2].parent += 1;
    variants[3].worker += 1;
    variants[4].delivery += 1;
    variants[5].child += 1;
    variants[6].child_pid += 1;
    variants[7].child_mm += 1;
    variants[8].root += 4096;
    variants[9].start += 4096;
    variants[10].length += 4096;
    variants[11].nonce += 1;
    variants[12].root = 0;
    for wrong in variants {
        let mut transaction = ForkAdoption::reserve(key).unwrap();
        assert_eq!(transaction.adopted(wrong), Err(EACCES));
        assert_eq!(transaction.phase(), ForkPhase::Reserved);
        assert_eq!(transaction.begin_access(key), Err(EBUSY));
    }
    for mut invalid in [key; 8].into_iter().enumerate() {
        match invalid.0 {
            0 => invalid.1.child = key.parent,
            1 => invalid.1.root = 0,
            2 => invalid.1.root += 1,
            3 => invalid.1.length = 0,
            4 => invalid.1.length += 1,
            5 => invalid.1.nonce = 0,
            6 => invalid.1.child_mm = 0,
            _ => invalid.1.start = u64::MAX & !4095,
        }
        assert!(matches!(ForkAdoption::reserve(invalid.1), Err(EINVAL)));
    }
}

#[test]
fn duplicate_commit_wrong_pid_and_reordered_link_reject_before_state_change() {
    let key = identity();
    let mut transaction = ForkAdoption::reserve(key).unwrap();
    assert_eq!(transaction.observe_link(key), Err(EBUSY));
    transaction.adopted(key).unwrap();
    assert_eq!(transaction.adopted(key), Err(EBUSY));
    assert_eq!(transaction.authorize_first_return(key, 456), Err(EINVAL));
    assert_eq!(transaction.first_return_published(key, 456), Err(EINVAL));
    assert_eq!(transaction.phase(), ForkPhase::AdoptedAwaitFirstReturn);
    transaction.first_return_published(key, 123).unwrap();
    assert_eq!(transaction.second_return_published(key, 0), Err(EBUSY));
    transaction.observe_link(key).unwrap();
    assert_eq!(transaction.observe_link(key), Err(EBUSY));
    transaction.second_return_published(key, 0).unwrap();
    assert_eq!(transaction.phase(), ForkPhase::Linked);
    assert_eq!(transaction.acknowledge_destroyed(key), Err(EBUSY));
}

#[test]
fn negative_first_or_second_return_closes_admission() {
    let key = identity();
    for first in [true, false] {
        let mut transaction = ForkAdoption::reserve(key).unwrap();
        transaction.adopted(key).unwrap();
        if first {
            transaction.first_return_published(key, -512).unwrap();
        } else {
            transaction.first_return_published(key, 123).unwrap();
            transaction.observe_link(key).unwrap();
            transaction.second_return_published(key, -5).unwrap();
        }
        assert_eq!(transaction.phase(), ForkPhase::AbortRequested);
        assert_eq!(transaction.begin_access(key), Err(EBUSY));
        assert_eq!(transaction.permit_guest_destroy(key), Err(EBUSY));
    }
}

#[test]
fn abort_trace_requires_admission_close_drain_revoke_final_destroy_then_ack() {
    let key = identity();
    let mut transaction = ForkAdoption::reserve(key).unwrap();
    transaction.adopted(key).unwrap();
    transaction.begin_access(key).unwrap();
    let mut events = Vec::new();
    assert_eq!(unsafe { transaction.host_revoked(key, 0) }, Err(EBUSY));
    assert_eq!(unsafe { transaction.guest_destroyed(key) }, Err(EBUSY));
    transaction.request_abort(key).unwrap(); events.push("admission_closed");
    assert_eq!(transaction.begin_access(key), Err(EBUSY));
    assert_eq!(unsafe { transaction.host_revoked(key, 0) }, Err(EBUSY));
    transaction.end_access(key).unwrap(); events.push("operations_drained");
    assert_eq!(unsafe { transaction.host_revoked(key, -5) }, Err(-5));
    assert_eq!(transaction.permit_guest_destroy(key), Err(EBUSY));
    assert_eq!(transaction.acknowledge_destroyed(key), Err(EBUSY));
    // The fixture supplies this unsafe boundary's proof; it does not claim to
    // execute Linux PTE/TLB revocation or an actual final guest destructor.
    unsafe { transaction.host_revoked(key, 0) }.unwrap(); events.push("host_revoked");
    transaction.permit_guest_destroy(key).unwrap();
    assert_eq!(transaction.acknowledge_destroyed(key), Err(EBUSY));
    unsafe { transaction.guest_destroyed(key) }.unwrap(); events.push("guest_final_destroyed");
    transaction.acknowledge_destroyed(key).unwrap(); events.push("ack");
    assert_eq!(events, ["admission_closed", "operations_drained", "host_revoked", "guest_final_destroyed", "ack"]);
    assert_eq!(transaction.phase(), ForkPhase::Released);
    transaction.acknowledge_destroyed(key).unwrap();
    let mut reused = key; reused.nonce += 1;
    assert_eq!(transaction.acknowledge_destroyed(reused), Err(EACCES));
}

#[test]
fn quarantined_or_unproven_destruction_never_releases() {
    let key = identity();
    let mut transaction = ForkAdoption::reserve(key).unwrap();
    transaction.request_abort(key).unwrap();
    assert_eq!(transaction.acknowledge_destroyed(key), Err(EBUSY));
    transaction.quarantine(key).unwrap();
    assert_eq!(unsafe { transaction.host_revoked(key, 0) }, Err(EBUSY));
    assert_eq!(transaction.permit_guest_destroy(key), Err(EBUSY));
    assert_eq!(transaction.acknowledge_destroyed(key), Err(EBUSY));
}
