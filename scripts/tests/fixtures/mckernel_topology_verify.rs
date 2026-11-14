// SPDX-License-Identifier: GPL-2.0-only
//! Read-only Linux topology snapshots and an independent C/Rust layout witness.
use core::mem::{align_of, offset_of, size_of};
use kernel::{bindings, fmt, prelude::*, str::CString, sync::Arc};

#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/smp_topology.rs"]
mod smp_topology;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_objects.rs"]
mod sysfs_objects;
use sysfs_objects::{AttributeOps, Directory, File};

module! {
    type: TopologyVerify,
    name: "mckernel_topology_verify",
    author: "McKernel developers",
    description: "Owned native CPU and cache topology verification",
    license: "GPL",
}

#[used]
#[link_section = ".mckernel_native_topology_layout"]
static LAYOUT: [u64; 45] = [
    size_of::<bindings::cpuinfo_x86>() as u64,
    align_of::<bindings::cpuinfo_x86>() as u64,
    offset_of!(bindings::cpuinfo_x86, topo) as u64,
    size_of::<bindings::cpuinfo_topology>() as u64,
    align_of::<bindings::cpuinfo_topology>() as u64,
    offset_of!(bindings::cpuinfo_topology, pkg_id) as u64,
    offset_of!(bindings::cpuinfo_topology, core_id) as u64,
    offset_of!(bindings::cpuinfo_topology, apicid) as u64,
    offset_of!(bindings::cpuinfo_topology, initial_apicid) as u64,
    offset_of!(bindings::cpuinfo_topology, die_id) as u64,
    size_of::<bindings::cpumask>() as u64,
    align_of::<bindings::cpumask>() as u64,
    offset_of!(bindings::cpumask, bits) as u64,
    size_of::<core::ffi::c_ulong>() as u64,
    size_of::<bindings::cacheinfo>() as u64,
    align_of::<bindings::cacheinfo>() as u64,
    offset_of!(bindings::cacheinfo, id) as u64,
    offset_of!(bindings::cacheinfo, type_) as u64,
    offset_of!(bindings::cacheinfo, level) as u64,
    offset_of!(bindings::cacheinfo, coherency_line_size) as u64,
    offset_of!(bindings::cacheinfo, number_of_sets) as u64,
    offset_of!(bindings::cacheinfo, ways_of_associativity) as u64,
    offset_of!(bindings::cacheinfo, physical_line_partition) as u64,
    offset_of!(bindings::cacheinfo, size) as u64,
    offset_of!(bindings::cacheinfo, shared_cpu_map) as u64,
    offset_of!(bindings::cacheinfo, attributes) as u64,
    offset_of!(bindings::cacheinfo, disable_sysfs) as u64,
    size_of::<bindings::cpu_cacheinfo>() as u64,
    align_of::<bindings::cpu_cacheinfo>() as u64,
    offset_of!(bindings::cpu_cacheinfo, info_list) as u64,
    offset_of!(bindings::cpu_cacheinfo, per_cpu_data_slice_size) as u64,
    offset_of!(bindings::cpu_cacheinfo, num_levels) as u64,
    offset_of!(bindings::cpu_cacheinfo, num_leaves) as u64,
    offset_of!(bindings::cpu_cacheinfo, cpu_map_populated) as u64,
    offset_of!(bindings::cpu_cacheinfo, early_ci_levels) as u64,
    bindings::cache_type_CACHE_TYPE_NOCACHE as u64,
    bindings::cache_type_CACHE_TYPE_INST as u64,
    bindings::cache_type_CACHE_TYPE_DATA as u64,
    bindings::cache_type_CACHE_TYPE_SEPARATE as u64,
    // include/linux/cacheinfo.h defines CACHE_ID as BIT(4); bindgen omits it.
    bindings::cache_type_CACHE_TYPE_UNIFIED as u64,
    1 << 4,
    size_of::<u32>() as u64,
    size_of::<*const ()>() as u64,
    bindings::CONFIG_NR_CPUS as u64,
    offset_of!(bindings::cpuinfo_x86, cpu_index) as u64,
];

fn emit(output: &mut [u8], offset: &mut usize, args: core::fmt::Arguments<'_>) -> Result {
    let value = CString::try_from_fmt(args)?;
    let bytes = value.as_bytes();
    let end = offset.checked_add(bytes.len()).ok_or(EIO)?;
    output
        .get_mut(*offset..end)
        .ok_or(EIO)?
        .copy_from_slice(bytes);
    *offset = end;
    Ok(())
}

fn mask(output: &mut [u8], offset: &mut usize, value: &smp_topology::CpuMask) -> Result {
    for word in value.words {
        emit(output, offset, fmt!(" {:016x}", word))?;
    }
    emit(output, offset, fmt!("\n"))
}

struct ShowCpu(Arc<smp_topology::Cpu>);
impl AttributeOps for ShowCpu {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        let cpu = &self.0;
        let mut offset = 0;
        emit(
            output,
            &mut offset,
            fmt!(
                "cpu {} {} {} {} {}\n",
                cpu.linux_id,
                cpu.apic_id,
                cpu.package_id,
                cpu.core_id,
                cpu.die_id
            ),
        )?;
        emit(output, &mut offset, fmt!("core"))?;
        mask(output, &mut offset, &cpu.core_siblings)?;
        emit(output, &mut offset, fmt!("thread"))?;
        mask(output, &mut offset, &cpu.thread_siblings)?;
        for cache in &cpu.caches {
            emit(
                output,
                &mut offset,
                fmt!(
                    "cache {} {} {} {} {} {} {} {} {} {}",
                    cache.index,
                    cache.id,
                    cache.kind,
                    cache.level,
                    cache.coherency_line_size,
                    cache.number_of_sets,
                    cache.ways_of_associativity,
                    cache.physical_line_partition,
                    cache.size,
                    cache.attributes
                ),
            )?;
            mask(output, &mut offset, &cache.shared_cpus)?;
        }
        Ok(offset)
    }
}

// The disposable fixture owns the same Linux read exclusion required by the
// production capture API; its guard is never sent or copied to another task.
struct ReadGuard(core::marker::PhantomData<*mut ()>);
impl ReadGuard {
    fn new() -> Self {
        // SAFETY: Module initialization is sleepable and holds no hotplug lock.
        unsafe { bindings::cpus_read_lock() };
        Self(core::marker::PhantomData)
    }
}
impl Drop for ReadGuard {
    fn drop(&mut self) {
        // SAFETY: This task acquired the balanced guard above.
        unsafe { bindings::cpus_read_unlock() };
    }
}

struct TopologyVerify {
    _files: Vec<File<ShowCpu>>,
    _root: Directory,
}

impl kernel::Module for TopologyVerify {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        let read = ReadGuard::new();
        // SAFETY: The held read guard stabilizes the initialized CPU bound.
        let limit = unsafe { bindings::nr_cpu_ids } as usize;
        if limit == 0 || limit > 512 {
            return Err(EINVAL);
        }
        let mut saved = Vec::with_capacity(limit, GFP_KERNEL)?;
        for cpu in 0..limit {
            // SAFETY: The checked bound and retained read guard protect this
            // static mask. An online CPU with missing topology must fail init.
            let online = unsafe { bindings::__cpu_online_mask.bits[cpu / 64] };
            if online & (1_u64 << (cpu % 64)) == 0 {
                continue;
            }
            // SAFETY: The fixture retains its read guard throughout capture.
            saved.push(unsafe { smp_topology::capture(cpu) }?, GFP_KERNEL)?;
        }
        // All subsequent formatting and reads access only Rust-owned values.
        drop(read);
        if saved.is_empty() {
            return Err(ENODEV);
        }
        let count = saved.len();
        let root = Directory::new(None, kernel::c_str!("mckernel_topology_verify"))?;
        let mut files = Vec::with_capacity(count, GFP_KERNEL)?;
        for cpu in saved {
            let name = CString::try_from_fmt(fmt!("cpu{}", cpu.linux_id))?;
            let cpu = Arc::new(cpu, GFP_KERNEL)?;
            files.push(File::new(&root, &name, 0o444, ShowCpu(cpu))?, GFP_KERNEL)?;
        }
        pr_info!(
            "MCKERNEL_TOPOLOGY_VERIFY READY cpus={} owned_snapshots=1\n",
            count
        );
        Ok(Self {
            _files: files,
            _root: root,
        })
    }
}
