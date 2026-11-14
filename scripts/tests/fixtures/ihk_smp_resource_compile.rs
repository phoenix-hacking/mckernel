#![cfg_attr(not(test), no_std)]
#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/smp_resource.rs"]
mod smp_resource;

#[cfg(test)]
mod integration_tests {
    use super::smp_resource::{
        CpuChange, CpuState, CpuTable, IkcPair, MemoryExtent, MemoryMap,
        MemoryWorkspace, OsToken, ResourceError,
    };

    #[test]
    fn cpu_ownership_and_ikc_round_trip() {
        let owner = OsToken::test_only(7, 11).unwrap();
        let mut cpus = CpuTable::<6>::new();
        for cpu in 0..6 {
            cpus.add_online_cpu(cpu, 0x40 + cpu as u32, 0).unwrap();
        }
        let mut workspace = [CpuChange::empty(); 6];

        cpus
            .prepare_reserve(&[1, 2], &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
        cpus
            .prepare_assign(owner, &[1, 2], &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
        cpus.set_ikc_map(
            owner,
            &[
                IkcPair {
                    source: 1,
                    destination: 4,
                },
                IkcPair {
                    source: 2,
                    destination: 4,
                },
            ],
        )
        .unwrap();

        let mut assigned = [usize::MAX; 2];
        assert_eq!(cpus.assigned_cpus(owner, &mut assigned).unwrap(), 2);
        assert_eq!(assigned, [1, 2]);
        cpus
            .prepare_release(owner, &[1, 2], &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
        assert_eq!(cpus.ikc_destination(1).unwrap(), None);
        cpus
            .prepare_return_to_host(&[1, 2], &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
        assert_eq!(cpus.slot(1).unwrap().state(), CpuState::Online);
        cpus.validate().unwrap();
    }

    #[test]
    fn dropped_transaction_and_memory_capacity_failure_are_atomic() {
        let owner = OsToken::test_only(2, 1).unwrap();
        let mut cpus = CpuTable::<3>::new();
        for cpu in 0..3 {
            cpus.add_online_cpu(cpu, cpu as u32, 0).unwrap();
        }
        let mut workspace = [CpuChange::empty(); 3];
        {
            let _rollback = cpus.prepare_reserve(&[0, 1], &mut workspace).unwrap();
        }
        assert_eq!(cpus.slot(0).unwrap().state(), CpuState::Online);

        let mut memory = MemoryMap::<2>::new();
        let mut short_staging = [None; 1];
        let mut short = MemoryWorkspace::new(&mut short_staging).unwrap();
        assert_eq!(
            memory.insert_free(0x1000, 0x5000, 0, &mut short),
            Err(ResourceError::OutputTooSmall { needed: 2 })
        );
        assert!(memory.is_empty());
        let mut staging = [None; 2];
        let mut memory_workspace = MemoryWorkspace::new(&mut staging).unwrap();
        memory
            .insert_free(0x1000, 0x5000, 0, &mut memory_workspace)
            .unwrap();
        assert_eq!(
            memory.assign(owner, 0x2000, 0x1000, &mut memory_workspace),
            Err(ResourceError::Capacity)
        );
        assert_eq!(memory.len(), 1);
        assert_eq!(memory.extent(0).unwrap().owner(), None);
    }

    #[test]
    fn memory_owner_generation_is_part_of_release_authority() {
        let current = OsToken::test_only(4, 3).unwrap();
        let stale = OsToken::test_only(4, 2).unwrap();
        let mut memory = MemoryMap::<8>::new();
        let mut staging = [None; 8];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        memory
            .insert_free(0x1000, 0x8000, 1, &mut workspace)
            .unwrap();
        memory
            .assign(current, 0x3000, 0x2000, &mut workspace)
            .unwrap();
        assert_eq!(
            memory.release(stale, 0x3000, 0x1000, &mut workspace),
            Err(ResourceError::Ownership)
        );
        assert_eq!(memory.bytes_owned_by(current).unwrap(), 0x2000);

        let sentinel = MemoryExtent::new(0x20_0000, 0x1000, 2, None).unwrap();
        let mut output = [sentinel];
        assert_eq!(memory.owned_extents(current, &mut output).unwrap(), 1);
        assert_eq!(output[0].start(), 0x3000);
        memory.release_all(current, &mut workspace).unwrap();
        assert_eq!(memory.bytes_owned_by(current).unwrap(), 0);
    }

    #[test]
    fn external_effect_drop_is_fail_closed_and_compensation_restores() {
        let mut cpus = CpuTable::<4>::new();
        for cpu in 0..4 {
            cpus.add_online_cpu(cpu, cpu as u32, 0).unwrap();
        }
        let mut workspace = [CpuChange::empty(); 4];
        {
            let mut transaction = cpus.prepare_reserve(&[1], &mut workspace).unwrap();
            transaction.begin_external_effects().unwrap();
            transaction.compensated_rollback().unwrap();
        }
        assert_eq!(cpus.slot(1).unwrap().state(), CpuState::Online);
        {
            let mut transaction = cpus.prepare_reserve(&[2], &mut workspace).unwrap();
            transaction.begin_external_effects().unwrap();
        }
        assert_eq!(cpus.slot(2).unwrap().state(), CpuState::Quarantined);
    }

    #[test]
    fn memory_candidate_is_invisible_until_commit_and_remove_can_rollback() {
        let mut memory = MemoryMap::<4>::new();
        let mut staging = [None; 4];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        {
            let transaction = memory
                .prepare_insert_free(0x1000, 0x4000, 0, &mut workspace)
                .unwrap();
            assert_eq!(transaction.live_len(), 0);
            assert_eq!(transaction.candidate_len(), 1);
        }
        assert!(memory.is_empty());
        {
            let mut transaction = memory
                .prepare_insert_free(0x1000, 0x4000, 0, &mut workspace)
                .unwrap();
            transaction.begin_external_effects().unwrap();
            transaction.commit().unwrap();
        }
        memory
            .prepare_remove_free(0x2000, 0x1000, &mut workspace)
            .unwrap()
            .rollback()
            .unwrap();
        assert_eq!(memory.len(), 1);
        memory
            .remove_free(0x2000, 0x1000, &mut workspace)
            .unwrap();
        assert_eq!(memory.len(), 2);
    }
}

#[cfg(test)]
mod hotplug_tests {
    use super::smp_resource::{
        CpuChange, CpuEffectCause, CpuState, CpuTable, HostCpuHotplug,
        HostCpuSnapshot, OsToken, ResourceError,
    };

    #[derive(Clone, Copy)]
    enum Fault {
        Before,
        After,
        NoEffectSuccess,
        ChangedIdentity,
        PanicAfter,
    }

    struct Host {
        cpus: [HostCpuSnapshot; 4],
        actions: Vec<(usize, bool)>,
        faults: Vec<(usize, Fault)>,
        observations: usize,
        read_fault: Option<usize>,
        identity_change: Option<(usize, usize)>,
    }

    impl Host {
        fn new(online: bool) -> Self {
            Self {
                cpus: core::array::from_fn(|cpu| HostCpuSnapshot {
                    hardware_id: 0x40 + cpu as u32,
                    numa_node: (cpu % 2) as u32,
                    online: cpu == 0 || online,
                }),
                actions: Vec::new(),
                faults: Vec::new(),
                observations: 0,
                read_fault: None,
                identity_change: None,
            }
        }
    }

    impl HostCpuHotplug for Host {
        type Error = i32;

        fn observe(&mut self, cpu: usize) -> Result<HostCpuSnapshot, i32> {
            self.observations += 1;
            if self.read_fault == Some(self.observations) {
                return Err(-19);
            }
            if let Some((at, changed)) = self.identity_change {
                if at == self.observations {
                    self.cpus[changed].hardware_id += 0x100;
                }
            }
            Ok(self.cpus[cpu])
        }

        fn set_online(&mut self, cpu: usize, online: bool) -> Result<(), i32> {
            assert_ne!(cpu, 0, "the control CPU must never be targeted");
            self.actions.push((cpu, online));
            let fault = self.faults.iter()
                .find(|(call, _)| *call == self.actions.len())
                .map(|(_, fault)| *fault);
            match fault {
                Some(Fault::Before) => return Err(-16),
                Some(Fault::NoEffectSuccess) => return Ok(()),
                Some(Fault::ChangedIdentity) => {
                    self.cpus[cpu].hardware_id += 0x100;
                    return Err(-19);
                }
                _ => {}
            }
            if self.cpus[cpu].online == online {
                return Err(-114);
            }
            self.cpus[cpu].online = online;
            match fault {
                Some(Fault::After) => Err(-5),
                Some(Fault::PanicAfter) => panic!("injected interruption"),
                _ => Ok(()),
            }
        }
    }

    fn table(online: bool) -> CpuTable<4> {
        let mut cpus = CpuTable::new();
        for cpu in 0..4 {
            cpus.add_online_cpu(cpu, 0x40 + cpu as u32, (cpu % 2) as u32).unwrap();
        }
        if !online {
            cpus.prepare_reserve(&[1, 2, 3], &mut [CpuChange::empty(); 3])
                .unwrap().commit_policy_only().unwrap();
        }
        cpus
    }

    fn unchanged(cpus: &CpuTable<4>, host: &Host, online: bool) {
        assert!(host.cpus[0].online);
        assert_eq!(cpus.slot(0).unwrap().state(), CpuState::Online);
        for cpu in 1..4 {
            assert_eq!(host.cpus[cpu].online, online);
            assert_eq!(cpus.slot(cpu).unwrap().state(),
                       if online { CpuState::Online } else { CpuState::Available });
        }
        cpus.validate().unwrap();
    }

    fn quarantined(cpus: &CpuTable<4>) {
        assert_eq!(cpus.slot(0).unwrap().state(), CpuState::Online);
        for cpu in 1..4 {
            assert_eq!(cpus.slot(cpu).unwrap().state(), CpuState::Quarantined);
        }
        cpus.validate().unwrap();
    }

    #[test]
    fn sparse_cpu_hotplug_round_trip_uses_existing_journal() {
        let mut cpus = table(true);
        let mut host = Host::new(true);
        let mut workspace = [CpuChange::empty(); 3];
        cpus.prepare_reserve(&[3, 1], &mut workspace).unwrap()
            .execute_hotplug(&mut host).unwrap();
        assert_eq!(host.actions, [(3, false), (1, false)]);
        assert_eq!(cpus.count_state(CpuState::Available), 2);
        assert!(host.cpus[2].online);
        cpus.prepare_return_to_host(&[1, 3], &mut workspace).unwrap()
            .execute_hotplug(&mut host).unwrap();
        assert_eq!(host.actions, [(3, false), (1, false), (1, true), (3, true)]);
        unchanged(&cpus, &host, true);
    }

    #[test]
    fn every_forward_failure_is_reversed_in_both_directions() {
        for online in [false, true] {
            for failed_cpu in 1..4 {
                for fault in [Fault::Before, Fault::After, Fault::NoEffectSuccess] {
                    let mut cpus = table(online);
                    let mut host = Host::new(online);
                    host.faults.push((failed_cpu, fault));
                    let mut workspace = [CpuChange::empty(); 3];
                    let transaction = if online {
                        cpus.prepare_reserve(&[1, 2, 3], &mut workspace)
                    } else {
                        cpus.prepare_return_to_host(&[1, 2, 3], &mut workspace)
                    }.unwrap();
                    let error = transaction.execute_hotplug(&mut host).unwrap_err();
                    assert!(!error.quarantined);
                    assert_eq!(error.rollback_cause, None);
                    let changed = if matches!(fault, Fault::After) {
                        failed_cpu
                    } else { failed_cpu - 1 };
                    let mut expected: Vec<_> = (1..=failed_cpu).map(|cpu| (cpu, !online)).collect();
                    expected.extend((1..=changed).rev().map(|cpu| (cpu, online)));
                    assert_eq!(host.actions, expected);
                    unchanged(&cpus, &host, online);
                }
            }
        }
    }

    #[test]
    fn complete_preflight_rejects_state_identity_numa_and_read_errors() {
        for online in [false, true] {
            for cpu in 1..4 {
                for failure in 0..4 {
                    let mut cpus = table(online);
                    let mut host = Host::new(online);
                    match failure {
                        0 => host.cpus[cpu].online = !online,
                        1 => host.cpus[cpu].hardware_id += 0x100,
                        2 => host.cpus[cpu].numa_node += 1,
                        _ => host.read_fault = Some(cpu),
                    }
                    let mut workspace = [CpuChange::empty(); 3];
                    let transaction = if online {
                        cpus.prepare_reserve(&[1, 2, 3], &mut workspace)
                    } else {
                        cpus.prepare_return_to_host(&[1, 2, 3], &mut workspace)
                    }.unwrap();
                    let error = transaction.execute_hotplug(&mut host).unwrap_err();
                    assert!(!error.quarantined);
                    assert!(host.actions.is_empty());
                    // Rejection preserves policy; it does not claim the host
                    // observation was reconciled or mutate the discrepant CPU.
                    unchanged(&cpus, &Host::new(online), online);
                }
            }
        }
    }

    #[test]
    fn inverse_failure_continues_cleanup_and_uses_observed_physical_state() {
        for online in [false, true] {
            for inverse in [Fault::Before, Fault::After, Fault::NoEffectSuccess] {
                let mut cpus = table(online);
                let mut host = Host::new(online);
                host.faults = vec![(3, Fault::Before), (4, inverse)];
                let mut workspace = [CpuChange::empty(); 3];
                let transaction = if online {
                    cpus.prepare_reserve(&[1, 2, 3], &mut workspace)
                } else {
                    cpus.prepare_return_to_host(&[1, 2, 3], &mut workspace)
                }.unwrap();
                let error = transaction.execute_hotplug(&mut host).unwrap_err();
                assert_eq!(error.cause, CpuEffectCause::Host { cpu: 3, error: -16 });
                assert_eq!(host.actions, [(1, !online), (2, !online), (3, !online),
                                          (2, online), (1, online)]);
                assert_eq!(host.cpus[1].online, online);
                if matches!(inverse, Fault::After) {
                    assert!(!error.quarantined);
                    unchanged(&cpus, &host, online);
                } else {
                    assert!(error.quarantined);
                    assert_eq!(error.rollback_cause, Some(CpuEffectCause::StateMismatch { cpu: 2 }));
                    quarantined(&cpus);
                }
            }
        }
    }

    #[test]
    fn changed_identity_is_never_targeted_during_compensation() {
        let mut cpus = table(true);
        let mut host = Host::new(true);
        host.faults.push((2, Fault::ChangedIdentity));
        let error = cpus.prepare_reserve(&[1, 2, 3], &mut [CpuChange::empty(); 3])
            .unwrap().execute_hotplug(&mut host).unwrap_err();
        assert!(error.quarantined);
        assert_eq!(host.actions, [(1, false), (2, false), (1, true)]);
        quarantined(&cpus);
    }

    #[test]
    fn final_batch_observation_detects_late_identity_change() {
        let mut cpus = table(true);
        let mut host = Host::new(true);
        host.identity_change = Some((7, 3));
        let error = cpus.prepare_reserve(&[1, 2, 3], &mut [CpuChange::empty(); 3])
            .unwrap().execute_hotplug(&mut host).unwrap_err();
        assert!(error.quarantined);
        assert_eq!(error.cause, CpuEffectCause::StateMismatch { cpu: 3 });
        assert_eq!(host.actions, [(1, false), (2, false), (3, false), (2, true), (1, true)]);
        quarantined(&cpus);
    }

    #[test]
    fn unknown_rollback_cpu_does_not_prevent_other_compensation() {
        let mut cpus = table(true);
        let mut host = Host::new(true);
        host.faults.push((3, Fault::Before));
        host.read_fault = Some(7);
        let error = cpus.prepare_reserve(&[1, 2, 3], &mut [CpuChange::empty(); 3])
            .unwrap().execute_hotplug(&mut host).unwrap_err();
        assert!(error.quarantined);
        assert_eq!(error.rollback_cause, Some(CpuEffectCause::Host { cpu: 2, error: -19 }));
        assert_eq!(host.actions, [(1, false), (2, false), (3, false), (1, true)]);
        quarantined(&cpus);
    }

    #[test]
    fn started_and_os_assignment_transactions_cannot_enter_hotplug() {
        let mut cpus = table(false);
        let mut host = Host::new(false);
        let owner = OsToken::test_only(2, 1).unwrap();
        let error = cpus.prepare_assign(owner, &[1, 2, 3], &mut [CpuChange::empty(); 3])
            .unwrap().execute_hotplug(&mut host).unwrap_err();
        assert_eq!(error.cause, CpuEffectCause::Policy(ResourceError::InvalidState));
        assert!(!error.quarantined);
        unchanged(&cpus, &host, false);
        let mut workspace = [CpuChange::empty(); 3];
        let mut transaction = cpus.prepare_return_to_host(&[1, 2, 3], &mut workspace).unwrap();
        transaction.begin_external_effects().unwrap();
        let error = transaction.execute_hotplug(&mut host).unwrap_err();
        assert_eq!(error.cause, CpuEffectCause::Policy(ResourceError::ExternalEffectsPending));
        assert!(error.quarantined);
        assert!(host.actions.is_empty());
        quarantined(&cpus);
    }

    #[test]
    fn interruption_retains_existing_transaction_quarantine() {
        let mut cpus = table(true);
        let mut host = Host::new(true);
        host.faults.push((2, Fault::PanicAfter));
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            cpus.prepare_reserve(&[1, 2, 3], &mut [CpuChange::empty(); 3])
                .unwrap().execute_hotplug(&mut host)
        }));
        assert!(result.is_err());
        assert_eq!(host.actions, [(1, false), (2, false)]);
        quarantined(&cpus);
    }
}
