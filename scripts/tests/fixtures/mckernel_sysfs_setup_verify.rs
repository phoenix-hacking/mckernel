// SPDX-License-Identifier: GPL-2.0-only
//! Actual setup tree, rollback, topology comparison and Linux file formatting.
use kernel::{bindings, prelude::*, sync::Arc};
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/smp_resource.rs"]
mod smp_resource;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/smp_topology.rs"]
mod smp_topology;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_objects.rs"]
mod sysfs_objects;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_tree.rs"]
mod sysfs_tree;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_setup.rs"]
mod sysfs_setup;

module! {
    type: SetupVerify,
    name: "mckernel_sysfs_setup_verify",
    author: "McKernel developers",
    description: "Native setup publication and rollback verification",
    license: "GPL",
}

struct ReadGuard;
impl ReadGuard {
    fn new() -> Self {
        // SAFETY: Disposable module initialization is sleepable and unguarded.
        unsafe { bindings::cpus_read_lock() };
        Self
    }
    fn capture(&self, cpu: usize) -> Result<smp_topology::Cpu> {
        // SAFETY: This task retains the complete CPU read exclusion.
        unsafe { smp_topology::capture(cpu) }
    }
}
impl Drop for ReadGuard {
    fn drop(&mut self) {
        // SAFETY: Balanced release by the acquiring task.
        unsafe { bindings::cpus_read_unlock() };
    }
}

struct SetupVerify {
    _good: sysfs_tree::Tree,
    _failed: sysfs_tree::Tree,
    _good_parent: sysfs_objects::Directory,
    _failed_parent: sysfs_objects::Directory,
    _root: sysfs_objects::Directory,
}

impl kernel::Module for SetupVerify {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        let guard = ReadGuard::new();
        // This fixture is intentionally pinned to its four-vCPU/two-node guest.
        if unsafe { bindings::nr_cpu_ids } != 4 { return Err(EINVAL); }
        let saved = guard.capture(0)?;
        // SAFETY: The fixture still holds CPU read exclusion.
        let online = unsafe { smp_topology::CpuMask::online()? };
        if !saved.matches_current(&guard.capture(0)?, &online) { return Err(EIO); }
        for field in 0..18 {
            let mut current = guard.capture(0)?;
            match field {
                0 => current.linux_id ^= 1,
                1 => current.apic_id ^= 1,
                2 => current.package_id ^= 1,
                3 => current.core_id ^= 1,
                4 => current.die_id ^= 1,
                5 => current.core_siblings.words[0] ^= 4,
                6 => current.thread_siblings.words[0] ^= 4,
                7 => current.caches[0].index ^= 1,
                8 => current.caches[0].kind ^= 1,
                9 => current.caches[0].level ^= 1,
                10 => current.caches[0].coherency_line_size ^= 1,
                11 => current.caches[0].number_of_sets ^= 1,
                12 => current.caches[0].ways_of_associativity ^= 1,
                13 => current.caches[0].physical_line_partition ^= 1,
                14 => current.caches[0].size ^= 1,
                15 => current.caches[0].attributes ^= 1,
                16 => current.caches[0].shared_cpus.words[0] ^= 4,
                17 => { current.caches.pop(); },
                _ => return Err(EIO),
            }
            if saved.matches_current(&current, &online) { return Err(EIO); }
        }
        let mut current = guard.capture(0)?;
        if current.caches[0].attributes & (1 << 4) == 0 { return Err(EIO); }
        current.caches[0].id ^= 1;
        if saved.matches_current(&current, &online) { return Err(EIO); }
        let mut current = guard.capture(0)?;
        let mut reduced = online.clone();
        reduced.words[0] &= !2;
        current.core_siblings.words[0] &= !2;
        current.thread_siblings.words[0] &= !2;
        for cache in &mut current.caches { cache.shared_cpus.words[0] &= !2; }
        if !saved.matches_current(&current, &reduced) { return Err(EIO); }
        if saved.matches_current(&current, &online) { return Err(EIO); }

        let mut snapshots = Vec::new();
        for cpu in [3, 1] { snapshots.push(Arc::new(guard.capture(cpu)?, GFP_KERNEL)?, GFP_KERNEL)?; }
        let mut distances = Vec::new();
        for from in 0..2 {
            for to in 0..2 {
                // SAFETY: Both nodes belong to the fixed retained guest CPUs.
                let distance = unsafe { bindings::__node_distance(from, to) };
                if distance <= 0 { return Err(EIO); }
                distances.push(distance as u32, GFP_KERNEL)?;
            }
        }
        let topology = sysfs_setup::Topology::new(4, &snapshots, &[1, 0], &[0, 1], distances)?;
        let mut invalid = guard.capture(1)?;
        // Force a failure after test/global/topology/cache nodes were created.
        invalid.caches[0].kind = 0;
        let invalid = [Arc::new(invalid, GFP_KERNEL)?];
        let mut local_distance = Vec::new(); local_distance.push(10, GFP_KERNEL)?;
        let invalid = sysfs_setup::Topology::new(4, &invalid, &[0], &[0], local_distance)?;
        drop(guard);
        let root = sysfs_objects::Directory::new(None, kernel::c_str!("mckernel_sysfs_setup_verify"))?;
        let good_parent = sysfs_objects::Directory::new(Some(&root), kernel::c_str!("good"))?;
        let failed_parent = sysfs_objects::Directory::new(Some(&root), kernel::c_str!("failed"))?;
        let mut good = sysfs_tree::Tree::new(sysfs_objects::Directory::new(Some(&good_parent), kernel::c_str!("sys"))?)?;
        let mut failed = sysfs_tree::Tree::new(sysfs_objects::Directory::new(Some(&failed_parent), kernel::c_str!("sys"))?)?;
        let count = sysfs_setup::setup_tree(&mut good, &topology)?;
        if count <= 2 || sysfs_setup::setup_tree(&mut good, &topology) != Err(EBUSY)
            || good.len() != count || good.lookup(b"/sys/setup_complete").is_err()
            || sysfs_setup::setup_tree(&mut failed, &invalid) != Err(EIO)
            || failed.len() != 2 || failed.lookup(b"/sys/test").is_ok()
            || failed.lookup(b"/sys/setup_complete").is_ok() { return Err(EIO); }
        pr_info!("MCKERNEL_SYSFS_SETUP_VERIFY READY nodes={} comparison_checks=22 rollback=1 duplicate_preserved=1 ranks=3,1\n", count);
        Ok(Self { _good: good, _failed: failed, _good_parent: good_parent,
            _failed_parent: failed_parent, _root: root })
    }
}
