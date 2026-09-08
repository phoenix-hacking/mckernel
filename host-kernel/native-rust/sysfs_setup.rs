// SPDX-License-Identifier: GPL-2.0-only
//! Native ownership for the existing Rust mcctrl setup-file sequence.

use super::{
    smp_resource::OsToken,
    smp_topology::{Cpu, CpuMask},
    sysfs_objects::AttributeOps,
    sysfs_tree::Tree,
};
use kernel::{
    bindings, fmt,
    prelude::*,
    str::{CStr, CString},
    sync::Arc,
};

struct AssignedCpu {
    saved: Arc<Cpu>,
    node: usize,
}

pub(crate) struct Topology {
    cpus: Vec<AssignedCpu>,
    linux_cpus: usize,
    nodes: usize,
    distances: Vec<u32>,
}

impl Topology {
    pub(crate) fn new(
        linux_cpus: usize,
        saved: &[Arc<Cpu>],
        cpu_nodes: &[u32],
        nodes: &[u32],
        distances: Vec<u32>,
    ) -> Result<Self> {
        if linux_cpus == 0
            || linux_cpus > 512
            || saved.is_empty()
            || saved.len() > linux_cpus
            || saved.len() != cpu_nodes.len()
            || nodes.is_empty()
            || nodes.len() > 1024
            || distances.len() != nodes.len() * nodes.len()
            || distances.contains(&0)
            || nodes.windows(2).any(|pair| pair[0] >= pair[1])
        {
            return Err(EINVAL);
        }
        let mut cpus = Vec::with_capacity(saved.len(), GFP_KERNEL)?;
        for (rank, snapshot) in saved.iter().enumerate() {
            if snapshot.linux_id as usize >= linux_cpus
                || saved[..rank]
                    .iter()
                    .any(|old| old.linux_id == snapshot.linux_id || old.apic_id == snapshot.apic_id)
            {
                return Err(EINVAL);
            }
            let node = nodes.binary_search(&cpu_nodes[rank]).map_err(|_| EINVAL)?;
            cpus.push(
                AssignedCpu {
                    saved: snapshot.clone(),
                    node,
                },
                GFP_KERNEL,
            )?;
        }
        Ok(Self {
            cpus,
            linux_cpus,
            nodes: nodes.len(),
            distances,
        })
    }

    fn translate(&self, mask: &CpuMask) -> CpuMask {
        let mut result = CpuMask { words: [0; 8] };
        for (rank, cpu) in self.cpus.iter().enumerate() {
            if mask.contains(cpu.saved.linux_id as usize) {
                result.words[rank / 64] |= 1 << (rank % 64);
            }
        }
        result
    }
}

/// Validated guest allocation. PreparedBoot retains the exact memory owner
/// through every started outcome; callbacks never borrow its mutable bytes.
pub(crate) struct SharedData {
    pub(crate) owner: OsToken,
    pub(crate) physical: u64,
    pub(crate) address: u64,
    pub(crate) bytes: usize,
}

pub(crate) struct Service {
    tree: Tree,
    topology: Topology,
    data: Option<SharedData>,
}

impl Service {
    pub(crate) fn new(tree: Tree, topology: Topology) -> Self {
        Self {
            tree,
            topology,
            data: None,
        }
    }

    pub(crate) fn overlaps(&self, physical: u64, bytes: usize) -> bool {
        self.data.as_ref().is_some_and(|data| {
            physical.checked_add(bytes as u64).is_none_or(|end| {
                physical < data.physical + data.bytes as u64 && data.physical < end
            })
        })
    }

    pub(crate) fn setup(&mut self, data: SharedData) -> Result<usize> {
        if self.data.is_some() {
            return Err(EBUSY);
        }
        let count = setup_tree(&mut self.tree, &self.topology)?;
        // All required files and the final marker are published before the
        // caller releases the peer's busy word. No fallible work follows here.
        self.data = Some(data);
        Ok(count)
    }
}

/// Initial publication shares the same rollback path in production and the
/// real Linux fixture. Existing trees are never replaced by a duplicate setup.
pub(crate) fn setup_tree(tree: &mut Tree, topology: &Topology) -> Result<usize> {
    if tree.len() != 2 {
        return Err(EBUSY);
    }
    if let Err(error) = populate(tree, topology) {
        tree.clear_contents();
        return Err(error);
    }
    Ok(tree.len())
}

struct Text(CString);
impl AttributeOps for Text {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        let value = self.0.as_bytes();
        output
            .get_mut(..value.len())
            .ok_or(EIO)?
            .copy_from_slice(value);
        Ok(value.len())
    }
}

fn text(tree: &mut Tree, path: &CStr, value: CString) -> Result {
    if value.as_bytes().len() >= 4096 {
        return Err(EINVAL);
    }
    tree.create(path.as_bytes(), 0o444, Text(value)).map(|_| ())
}

fn number(tree: &mut Tree, path: &CStr, value: u32) -> Result {
    text(tree, path, CString::try_from_fmt(fmt!("{}\n", value))?)
}

fn bitmap(tree: &mut Tree, path: &CStr, mask: &CpuMask, bits: usize, list: bool) -> Result {
    if bits == 0 || bits > 512 {
        return Err(EINVAL);
    }
    // The explicit-count Linux API works with a normal heap buffer. Unlike
    // bitmap_print_to_pagebuf it does not assume page-aligned output storage.
    let mut buffer = Vec::with_capacity(4096, GFP_KERNEL)?;
    for _ in 0..4096 {
        buffer.push(0_u8, GFP_KERNEL)?;
    }
    // SAFETY: Immutable mask storage covers the checked bit count. Linux writes
    // at most the supplied buffer length and retains no pointer on return.
    let count = unsafe {
        let print = if list {
            bindings::bitmap_print_list_to_buf
        } else {
            bindings::bitmap_print_bitmask_to_buf
        };
        print(
            buffer.as_mut_ptr().cast(),
            mask.words.as_ptr(),
            bits as i32,
            0,
            buffer.len(),
        )
    };
    kernel::error::to_result(count)?;
    let count = count as usize;
    // This API copies strlen+1. Require a complete newline/NUL-terminated
    // result; never expose its extra NUL as a sysfs attribute byte.
    if count < 2 || count > buffer.len() || buffer[count - 2..count] != *b"\n\0" {
        return Err(EIO);
    }
    let value = CStr::from_bytes_with_nul(&buffer[..count]).map_err(|_| EIO)?;
    text(tree, path, CString::try_from(value)?)
}

fn sequential(count: usize) -> CpuMask {
    let mut result = CpuMask { words: [0; 8] };
    for rank in 0..count {
        result.words[rank / 64] |= 1 << (rank % 64);
    }
    result
}

fn populate(tree: &mut Tree, topology: &Topology) -> Result {
    tree.mkdir(b"/sys/test/x.dir")?;
    number(tree, kernel::c_str!("/sys/test/a.dir/a_value"), 35)?;
    let target = tree.lookup(b"/sys/test/a.dir")?;
    tree.symlink(target, b"/sys/test/L.dir")?;
    tree.unlink(b"/sys/test/x.dir", 0)?;
    let online = sequential(topology.cpus.len());
    for name in ["online", "possible", "present"] {
        bitmap(
            tree,
            &CString::try_from_fmt(fmt!("/sys/devices/system/cpu/{}", name))?,
            &online,
            topology.linux_cpus,
            true,
        )?;
    }
    bitmap(
        tree,
        kernel::c_str!("/sys/devices/system/cpu/offline"),
        &sequential(0),
        topology.linux_cpus,
        true,
    )?;
    for (rank, cpu) in topology.cpus.iter().enumerate() {
        let saved = &cpu.saved;
        let prefix = CString::try_from_fmt(fmt!("/sys/devices/system/cpu/cpu{}", rank))?;
        for (name, value) in [
            ("physical_package_id", saved.package_id),
            ("core_id", saved.core_id),
        ] {
            number(
                tree,
                &CString::try_from_fmt(fmt!("{}/topology/{}", &*prefix, name))?,
                value,
            )?;
        }
        for (name, mask) in [
            ("core_siblings", &saved.core_siblings),
            ("thread_siblings", &saved.thread_siblings),
        ] {
            let mask = topology.translate(mask);
            bitmap(
                tree,
                &CString::try_from_fmt(fmt!("{}/topology/{}", &*prefix, name))?,
                &mask,
                topology.linux_cpus,
                false,
            )?;
            bitmap(
                tree,
                &CString::try_from_fmt(fmt!("{}/topology/{}_list", &*prefix, name))?,
                &mask,
                topology.linux_cpus,
                true,
            )?;
        }
        for cache in &saved.caches {
            let prefix = CString::try_from_fmt(fmt!("{}/cache/index{}", &*prefix, cache.index))?;
            for (name, value) in [
                ("level", cache.level),
                ("coherency_line_size", cache.coherency_line_size),
                ("number_of_sets", cache.number_of_sets),
                ("physical_line_partition", cache.physical_line_partition),
                ("ways_of_associativity", cache.ways_of_associativity),
            ] {
                number(
                    tree,
                    &CString::try_from_fmt(fmt!("{}/{}", &*prefix, name))?,
                    value,
                )?;
            }
            let kind = match cache.kind {
                1 => "Instruction",
                2 => "Data",
                4 => "Unified",
                _ => return Err(EIO),
            };
            text(
                tree,
                &CString::try_from_fmt(fmt!("{}/type", &*prefix))?,
                CString::try_from_fmt(fmt!("{}\n", kind))?,
            )?;
            text(
                tree,
                &CString::try_from_fmt(fmt!("{}/size", &*prefix))?,
                CString::try_from_fmt(fmt!("{}K\n", cache.size / 1024))?,
            )?;
            let mask = topology.translate(&cache.shared_cpus);
            bitmap(
                tree,
                &CString::try_from_fmt(fmt!("{}/shared_cpu_map", &*prefix))?,
                &mask,
                topology.linux_cpus,
                false,
            )?;
            bitmap(
                tree,
                &CString::try_from_fmt(fmt!("{}/shared_cpu_list", &*prefix))?,
                &mask,
                topology.linux_cpus,
                true,
            )?;
        }
    }
    for name in ["online", "possible"] {
        let value = if topology.nodes == 1 {
            CString::try_from_fmt(fmt!("0\n"))?
        } else {
            CString::try_from_fmt(fmt!("0-{}\n", topology.nodes - 1))?
        };
        text(
            tree,
            &CString::try_from_fmt(fmt!("/sys/devices/system/node/{}", name))?,
            value,
        )?;
    }
    for node in 0..topology.nodes {
        let prefix = CString::try_from_fmt(fmt!("/sys/devices/system/node/node{}", node))?;
        let mut distance = CString::try_from(kernel::c_str!(""))?;
        for target in 0..topology.nodes {
            distance = CString::try_from_fmt(fmt!(
                "{}{}{}",
                &*distance,
                if target == 0 { "" } else { " " },
                topology.distances[node * topology.nodes + target]
            ))?;
        }
        text(
            tree,
            &CString::try_from_fmt(fmt!("{}/distance", &*prefix))?,
            CString::try_from_fmt(fmt!("{}\n", &*distance))?,
        )?;
        let mut mask = sequential(0);
        for (rank, cpu) in topology.cpus.iter().enumerate() {
            if cpu.node == node {
                mask.words[rank / 64] |= 1 << (rank % 64);
            }
        }
        bitmap(
            tree,
            &CString::try_from_fmt(fmt!("{}/cpumap", &*prefix))?,
            &mask,
            topology.linux_cpus,
            false,
        )?;
        bitmap(
            tree,
            &CString::try_from_fmt(fmt!("{}/cpulist", &*prefix))?,
            &mask,
            topology.linux_cpus,
            true,
        )?;
        let target = tree.lookup(prefix.as_bytes())?;
        tree.symlink(
            target,
            CString::try_from_fmt(fmt!("/sys/bus/node/devices/node{}", node))?.as_bytes(),
        )?;
        for (rank, cpu) in topology.cpus.iter().enumerate() {
            if cpu.node != node {
                continue;
            }
            let cpu_path = CString::try_from_fmt(fmt!("/sys/devices/system/cpu/cpu{}", rank))?;
            tree.symlink(
                target,
                CString::try_from_fmt(fmt!("{}/node{}", &*cpu_path, node))?.as_bytes(),
            )?;
            let target = tree.lookup(cpu_path.as_bytes())?;
            tree.symlink(
                target,
                CString::try_from_fmt(fmt!("{}/cpu{}", &*prefix, rank))?.as_bytes(),
            )?;
        }
    }
    tree.mkdir(b"/sys/setup_complete")?;
    Ok(())
}
