// SPDX-License-Identifier: GPL-2.0-only
//! Owned copies of Linux's x86 CPU/cache topology before reservation.
//!
//! Adapt the legacy IHK initialization-time collector without opening paths in
//! the calling task's filesystem namespace. Linux owns discovery; these values
//! own the snapshot. No reference into Linux's mutable topology escapes.

use core::ptr;
use kernel::{bindings, prelude::*};

const MAX_CPUS: usize = 512;
const WORDS: usize = MAX_CPUS / 64;
const MAX_CACHE_LEAVES: usize = 64;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CpuMask {
    pub(crate) words: [u64; WORDS],
}

impl CpuMask {
    /// # Safety
    /// The caller holds CPU hotplug read exclusion throughout the copy.
    pub(crate) unsafe fn online() -> Result<Self> {
        // SAFETY: The caller stabilizes both the bound and this resident mask.
        unsafe {
            Self::copy(
                &raw const bindings::__cpu_online_mask,
                bindings::nr_cpu_ids as usize,
            )
        }
    }

    pub(crate) fn contains(&self, cpu: usize) -> bool {
        cpu < MAX_CPUS && self.words[cpu / 64] & (1_u64 << (cpu % 64)) != 0
    }

    /// The caller keeps this exact Linux mask live under CPU hotplug exclusion.
    unsafe fn copy(mask: *const bindings::cpumask, limit: usize) -> Result<Self> {
        if mask.is_null() || limit == 0 || limit > MAX_CPUS {
            return Err(EINVAL);
        }
        let mut result = Self { words: [0; WORDS] };
        for index in 0..limit.div_ceil(64) {
            // SAFETY: The caller retains the mask; the checked frozen CPU bound
            // is smaller than the configured Linux cpumask witnessed at build.
            result.words[index] = unsafe { ptr::read(ptr::addr_of!((*mask).bits[index])) };
        }
        if limit % 64 != 0 {
            result.words[limit / 64] &= (1_u64 << (limit % 64)) - 1;
        }
        Ok(result)
    }

    pub(crate) fn matches_online(&self, current: &Self, online: &Self) -> bool {
        self.words
            .iter()
            .zip(&current.words)
            .zip(&online.words)
            .all(|((&saved, &current), &online)| saved & online == current & online)
    }
}

#[derive(Debug, Eq, PartialEq)]
pub(crate) struct Cache {
    pub(crate) index: u32,
    pub(crate) id: u32,
    pub(crate) kind: u32,
    pub(crate) level: u32,
    pub(crate) coherency_line_size: u32,
    pub(crate) number_of_sets: u32,
    pub(crate) ways_of_associativity: u32,
    pub(crate) physical_line_partition: u32,
    pub(crate) size: u32,
    pub(crate) attributes: u32,
    pub(crate) shared_cpus: CpuMask,
}

#[derive(Debug, Eq, PartialEq)]
pub(crate) struct Cpu {
    pub(crate) linux_id: u32,
    pub(crate) apic_id: u32,
    pub(crate) package_id: u32,
    pub(crate) core_id: u32,
    pub(crate) die_id: u32,
    pub(crate) core_siblings: CpuMask,
    pub(crate) thread_siblings: CpuMask,
    pub(crate) caches: Vec<Cache>,
}

impl Cpu {
    /// Offline peers may disappear from Linux's masks. Validate only current
    /// online membership, retaining the complete original masks for McKernel.
    pub(crate) fn matches_current(&self, current: &Self, online: &CpuMask) -> bool {
        [
            self.linux_id,
            self.apic_id,
            self.package_id,
            self.core_id,
            self.die_id,
        ] == [
            current.linux_id,
            current.apic_id,
            current.package_id,
            current.core_id,
            current.die_id,
        ] && self
            .core_siblings
            .matches_online(&current.core_siblings, online)
            && self
                .thread_siblings
                .matches_online(&current.thread_siblings, online)
            && self.caches.len() == current.caches.len()
            && self
                .caches
                .iter()
                .zip(&current.caches)
                .all(|(saved, current)| {
                    // Linux specifies cache IDs only when CACHE_ID is set. Do not
                    // infer shared membership from IDs: use the observed masks.
                    (saved.attributes & (1 << 4) == 0 || saved.id == current.id)
                        && [
                            saved.index,
                            saved.kind,
                            saved.level,
                            saved.coherency_line_size,
                            saved.number_of_sets,
                            saved.ways_of_associativity,
                            saved.physical_line_partition,
                            saved.size,
                            saved.attributes,
                        ] == [
                            current.index,
                            current.kind,
                            current.level,
                            current.coherency_line_size,
                            current.number_of_sets,
                            current.ways_of_associativity,
                            current.physical_line_partition,
                            current.size,
                            current.attributes,
                        ]
                        && saved
                            .shared_cpus
                            .matches_online(&current.shared_cpus, online)
                })
    }
}

/// Reuse the established native raised_list per-CPU address calculation.
/// This is a Linux linker token plus its runtime offset, not Rust allocation
/// pointer arithmetic between two unrelated allocations.
unsafe fn per_cpu<T>(symbol: *const T, cpu: usize) -> *const T {
    // SAFETY: The capture caller has checked nr_cpu_ids and holds CPU exclusion.
    let offset = unsafe {
        (&raw const bindings::__per_cpu_offset)
            .cast::<u64>()
            .add(cpu)
            .read()
    };
    (symbol as usize).wrapping_add(offset as usize) as *const T
}

/// Capture one online CPU, copying all data before returning.
///
/// # Safety
/// The caller holds cpus_read_lock (or its write side) throughout this call,
/// including allocation, and must acquire device_hotplug_lock first if it is
/// also observing devices. No CPU transition may run while that read lock is
/// held. Native callers must keep the snapshot across reservation: Linux drops
/// shared membership during offline, so a later capture cannot replace it.
pub(crate) unsafe fn capture(cpu: usize) -> Result<Cpu> {
    // SAFETY: The caller's hotplug guard stabilizes the bound and topology.
    let limit = unsafe { bindings::nr_cpu_ids } as usize;
    if limit == 0 || limit > MAX_CPUS || cpu >= limit {
        return Err(EINVAL);
    }
    // SAFETY: Static Linux masks remain live and the caller excludes updates.
    let online = unsafe { CpuMask::copy(&raw const bindings::__cpu_online_mask, limit)? };
    if !online.contains(cpu) {
        return Err(ENODEV);
    }
    // SAFETY: cpu_info and these mask-pointer symbols are exported per-CPU
    // allocations. CPU hotplug exclusion keeps both allocations and masks live.
    let (info, core, thread) = unsafe {
        (
            per_cpu(&raw const bindings::cpu_info, cpu),
            per_cpu(&raw const bindings::cpu_core_map, cpu).read(),
            per_cpu(&raw const bindings::cpu_sibling_map, cpu).read(),
        )
    };
    // SAFETY: Read only witnessed fields of the protected per-CPU allocation.
    let (apic_id, package_id, core_id, die_id, index) = unsafe {
        (
            ptr::read(ptr::addr_of!((*info).topo.apicid)),
            ptr::read(ptr::addr_of!((*info).topo.pkg_id)),
            ptr::read(ptr::addr_of!((*info).topo.core_id)),
            ptr::read(ptr::addr_of!((*info).topo.die_id)),
            ptr::read(ptr::addr_of!((*info).cpu_index)),
        )
    };
    if index as usize != cpu || apic_id == u32::MAX || package_id == u32::MAX || core_id == u32::MAX
    {
        return Err(EIO);
    }
    // SAFETY: Both returned masks are live under the supplied hotplug guard.
    let core_siblings = unsafe { CpuMask::copy(core, limit)? };
    let thread_siblings = unsafe { CpuMask::copy(thread, limit)? };
    if !core_siblings.contains(cpu) || !thread_siblings.contains(cpu) {
        return Err(EIO);
    }
    // SAFETY: The validated online CPU and held guard satisfy cacheinfo's API.
    let info = unsafe { bindings::get_cpu_cacheinfo(cpu as u32) };
    if info.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: The per-CPU descriptor and its leaf array cannot change here.
    let (leaves, count, populated) = unsafe {
        (
            ptr::read(ptr::addr_of!((*info).info_list)),
            ptr::read(ptr::addr_of!((*info).num_leaves)) as usize,
            ptr::read(ptr::addr_of!((*info).cpu_map_populated)),
        )
    };
    if leaves.is_null() || count == 0 || count > MAX_CACHE_LEAVES || !populated {
        return Err(ENODEV);
    }
    let mut caches = Vec::with_capacity(count, GFP_KERNEL)?;
    for index in 0..count {
        // SAFETY: The stable descriptor bounds this initialized cache leaf.
        let leaf = unsafe { leaves.add(index) };
        // SAFETY: Read individual fields; no borrowed Linux data is retained.
        let cache = unsafe {
            if ptr::read(ptr::addr_of!((*leaf).disable_sysfs)) {
                continue;
            }
            Cache {
                index: index as u32,
                id: ptr::read(ptr::addr_of!((*leaf).id)),
                kind: ptr::read(ptr::addr_of!((*leaf).type_)),
                level: ptr::read(ptr::addr_of!((*leaf).level)),
                coherency_line_size: ptr::read(ptr::addr_of!((*leaf).coherency_line_size)),
                number_of_sets: ptr::read(ptr::addr_of!((*leaf).number_of_sets)),
                ways_of_associativity: ptr::read(ptr::addr_of!((*leaf).ways_of_associativity)),
                physical_line_partition: ptr::read(ptr::addr_of!((*leaf).physical_line_partition)),
                size: ptr::read(ptr::addr_of!((*leaf).size)),
                attributes: ptr::read(ptr::addr_of!((*leaf).attributes)),
                shared_cpus: CpuMask::copy(ptr::addr_of!((*leaf).shared_cpu_map), limit)?,
            }
        };
        if !matches!(cache.kind, 1 | 2 | 4) || cache.level == 0 || !cache.shared_cpus.contains(cpu)
        {
            return Err(EIO);
        }
        caches.push(cache, GFP_KERNEL)?;
    }
    if caches.is_empty() {
        return Err(ENODEV);
    }
    Ok(Cpu {
        linux_id: cpu as u32,
        apic_id,
        package_id,
        core_id,
        die_id,
        core_siblings,
        thread_siblings,
        caches,
    })
}
