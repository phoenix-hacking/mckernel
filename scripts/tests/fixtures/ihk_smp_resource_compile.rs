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
