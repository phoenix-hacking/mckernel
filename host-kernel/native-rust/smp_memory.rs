// SPDX-License-Identifier: GPL-2.0
//! Linux page owners and memory ioctls for the existing SMP memory policy.
//!
//! Temporary allocations stay private until the complete batch can enter the
//! existing MemoryMap. The policy workspace lives off the kernel stack. Each
//! allocation retains its original compound-page order until return to Linux.

use super::smp_cpu::ResourceModulePin;
use super::smp_resource::{MemoryExtent, MemoryMap, MemoryWorkspace, USER_MEMORY_REQUEST_GRANULE};
use core::{
    cell::UnsafeCell,
    marker::PhantomData,
    ptr,
    ptr::NonNull,
    sync::atomic::{AtomicPtr, Ordering},
};
use kernel::{
    bindings,
    prelude::*,
    sync::{new_mutex, Mutex},
    uaccess::UserSlice,
};

#[allow(dead_code, unreachable_pub)]
#[path = "abi/x86_64.rs"]
mod abi;

const MAX_EXTENTS: usize = 4096;
const MAX_REQUESTS: usize = MAX_EXTENTS;
const MAX_NODES: usize = abi::IHK_MAX_NUM_NUMA_NODES;
const MAX_ORDER: u32 = 10;
const PAGE_BYTES: u64 = 4096;
const _: () = assert!(bindings::PAGE_SHIFT == 12);
const _: () = assert!(bindings::MAX_PAGE_ORDER >= MAX_ORDER);
const _: () = assert!(core::mem::size_of::<bindings::page>() == 64);
const _: () = assert!(bindings::NODES_WIDTH == 10 && bindings::SECTIONS_WIDTH == 0);
const _: () = assert!(bindings::NODES_MASK == 1023);

// Linux 6.12 does not expose EOVERFLOW in kernel::error::code. Keep its
// ordinary errno through the public conversion API without a new C wrapper.
fn overflow() -> Error {
    match kernel::error::to_result(-(bindings::EOVERFLOW as i32)) {
        Err(error) => error,
        Ok(()) => EINVAL,
    }
}

#[cfg(not(all(
    CONFIG_NUMA,
    CONFIG_SPARSEMEM_VMEMMAP,
    CONFIG_MEMORY_HOTPLUG,
    CONFIG_DYNAMIC_MEMORY_LAYOUT
)))]
compile_error!("native SMP memory requires the reviewed NUMA/vmemmap/hotplug layout");

/// The read guard excludes node/memory removal while validating allocation
/// targets. Non-movable allocated pages retain their lifetime after it ends.
struct MemoryHotplugGuard(PhantomData<*mut ()>);

impl MemoryHotplugGuard {
    fn lock() -> Self {
        // SAFETY: Sleepable module ioctl context; no memory hotplug lock is
        // already held. The exported Linux read semaphore is balanced by Drop.
        unsafe { bindings::get_online_mems() };
        Self(PhantomData)
    }

    fn free_bytes(&self, node: u32) -> Result<u64> {
        if node as usize >= MAX_NODES {
            return Err(EINVAL);
        }
        let word = node as usize / 64;
        let bit = 1_u64 << (node % 64);
        // SAFETY: Node-mask storage is resident and bounded. The memory
        // hotplug read semaphore excludes the writer changing memory nodes.
        let present = unsafe {
            let online = ptr::read_volatile(ptr::addr_of!(
                bindings::node_states[bindings::node_states_N_ONLINE as usize].bits[word]
            ));
            let memory = ptr::read_volatile(ptr::addr_of!(
                bindings::node_states[bindings::node_states_N_MEMORY as usize].bits[word]
            ));
            online & memory & bit != 0
        };
        if !present {
            return Err(EINVAL);
        }
        let mut info = bindings::sysinfo::default();
        // SAFETY: The node is a present memory node under exclusion. Linux
        // writes into this complete local sysinfo; only documented fields are read.
        unsafe { bindings::si_meminfo_node(&mut info, node as i32) };
        info.freeram
            .checked_mul(info.mem_unit as u64)
            .ok_or_else(overflow)
    }
}

impl Drop for MemoryHotplugGuard {
    fn drop(&mut self) {
        // SAFETY: This non-Send, non-Copy guard releases its acquiring task's lock.
        unsafe { bindings::put_online_mems() };
    }
}

struct PageOwner {
    page: NonNull<bindings::page>,
    order: u32,
    node: u32,
    physical: u64,
}

// SAFETY: This value owns a non-movable Linux allocation. Exclusive Rust
// ownership transfers between tasks; access/publication is under the mutex.
unsafe impl Send for PageOwner {}

impl PageOwner {
    fn allocate(order: u32, node: u32, _hotplug: &MemoryHotplugGuard) -> Result<Self> {
        if order > MAX_ORDER || node as usize >= MAX_NODES {
            return Err(EINVAL);
        }
        // Reuse the existing KmsgPages ownership approach, adding strict NUMA
        // placement. Never consume atomic reserves or request OOM escalation.
        let flags = bindings::GFP_KERNEL
            | bindings::__GFP_ZERO
            | (1 << bindings::___GFP_COMP_BIT)
            | (1 << bindings::___GFP_NORETRY_BIT)
            | (1 << bindings::___GFP_NOWARN_BIT)
            | (1 << bindings::___GFP_THISNODE_BIT);
        // SAFETY: The node was checked under memory hotplug exclusion. The
        // bounded order and Linux flags are valid; THISNODE prevents fallback.
        let raw =
            unsafe { bindings::__alloc_pages_noprof(flags, order, node as i32, ptr::null_mut()) };
        let page = NonNull::new(raw).ok_or(ENOMEM)?;
        let mut owner = Self {
            page,
            order,
            node,
            physical: 0,
        };
        // SAFETY: The selected kernel uses SPARSEMEM_VMEMMAP. vmemmap_base is
        // read-only after init; the returned page is a live member of that map.
        // Use integer address arithmetic, not subtraction between Rust objects.
        let base = unsafe { bindings::vmemmap_base } as usize;
        let offset = (raw as usize).checked_sub(base).ok_or(EIO)?;
        let stride = core::mem::size_of::<bindings::page>();
        if offset % stride != 0 {
            return Err(EIO);
        }
        owner.physical = ((offset / stride) as u64)
            .checked_mul(PAGE_BYTES)
            .ok_or_else(overflow)?;
        // SAFETY: The newly allocated head page is exclusively owned. Linux
        // fixes its node field before return; the reviewed shift is 64-0-10.
        let page_flags = unsafe { ptr::read_volatile(ptr::addr_of!((*raw).flags)) };
        if ((page_flags >> 54) & bindings::NODES_MASK as u64) != node as u64
            || owner.physical % owner.len() != 0
        {
            return Err(EIO);
        }
        owner
            .physical
            .checked_add(owner.len())
            .ok_or_else(overflow)?;
        Ok(owner)
    }

    fn len(&self) -> u64 {
        PAGE_BYTES << self.order
    }
    fn end(&self) -> u64 {
        self.physical + self.len()
    }
    fn extent(&self) -> Result<MemoryExtent> {
        MemoryExtent::new(self.physical, self.len(), self.node, None).map_err(|_| EIO)
    }
}

impl Drop for PageOwner {
    fn drop(&mut self) {
        // SAFETY: Exactly one owning value retains this original allocation
        // and order. No guest may access a free-pool range selected for return.
        unsafe { bindings::__free_pages(self.page.as_ptr(), self.order) };
    }
}

#[derive(Clone, Copy)]
struct Demand {
    bytes: u64,
    node: u32,
}

struct Request {
    sizes: usize,
    nodes: usize,
    count: usize,
    count_address: usize,
    min_order: u32,
    max_ratio: u64,
    timeout: u64,
    compat: bool,
}

impl Request {
    fn read(argument: usize, compat: bool) -> Result<Self> {
        Self::read_scope(argument, compat, true)
    }

    fn read_scope(argument: usize, compat: bool, reserve_hints: bool) -> Result<Self> {
        let length = if compat {
            24
        } else {
            core::mem::size_of::<abi::IhkMemoryRequest>()
        };
        let mut header = [0_u8; 32];
        UserSlice::new(argument, length)
            .reader()
            .read_slice(&mut header[..length])?;
        let pointer =
            |offset: usize| -> Result<usize> {
                if compat {
                    Ok(u32::from_ne_bytes(
                        header[offset..offset + 4].try_into().map_err(|_| EINVAL)?,
                    ) as usize)
                } else {
                    Ok(u64::from_ne_bytes(
                        header[offset..offset + 8].try_into().map_err(|_| EINVAL)?,
                    ) as usize)
                }
            };
        let width = if compat { 4 } else { 8 };
        let field = |offset: usize| -> Result<i32> {
            Ok(i32::from_ne_bytes(
                header[offset..offset + 4].try_into().map_err(|_| EINVAL)?,
            ))
        };
        let sizes = pointer(0)?;
        let nodes = pointer(width)?;
        let offset = width * 2;
        let count = field(offset)?;
        let minimum = field(offset + 4)?;
        let ratio = field(offset + 8)?;
        let timeout = field(offset + 12)?;
        if count < 0
            || count as usize > MAX_REQUESTS
            || minimum < 0
            || !(0..=98).contains(&ratio)
            || (reserve_hints && timeout < 0)
            || (count > 0 && (sizes == 0 || nodes == 0))
        {
            return Err(EINVAL);
        }
        let minimum_pages = ((minimum as u64).max(PAGE_BYTES) + PAGE_BYTES - 1) / PAGE_BYTES;
        let min_order = if reserve_hints {
            minimum_pages.next_power_of_two().trailing_zeros()
        } else {
            0
        };
        if min_order > MAX_ORDER {
            return Err(EINVAL);
        }
        Ok(Self {
            sizes,
            nodes,
            count: count as usize,
            count_address: argument.checked_add(offset).ok_or(EFAULT)?,
            min_order,
            max_ratio: ratio as u64,
            timeout: timeout as u64,
            compat,
        })
    }

    fn demands(&self) -> Result<Vec<Demand>> {
        let width = if self.compat { 4 } else { 8 };
        let mut sizes = UserSlice::new(self.sizes, self.count * width).reader();
        let mut nodes = UserSlice::new(self.nodes, self.count * 4).reader();
        let mut result = Vec::with_capacity(self.count, GFP_NOWAIT)?;
        for _ in 0..self.count {
            let bytes = if self.compat {
                match sizes.read::<u32>()? {
                    u32::MAX => u64::MAX,
                    value => value as u64,
                }
            } else {
                sizes.read::<u64>()?
            };
            let node = nodes.read::<i32>()?;
            if node < 0 || node as usize >= MAX_NODES {
                return Err(EINVAL);
            }
            result.push(
                Demand {
                    bytes,
                    node: node as u32,
                },
                GFP_NOWAIT,
            )?;
        }
        Ok(result)
    }
}

struct MemoryContext {
    map: MemoryMap<MAX_EXTENTS>,
    staging: [Option<MemoryExtent>; MAX_EXTENTS],
    pages: Vec<PageOwner>,
    pin: Option<ResourceModulePin>,
}

impl MemoryContext {
    const fn new() -> Self {
        Self {
            map: MemoryMap::new(),
            staging: [None; MAX_EXTENTS],
            pages: Vec::new(),
            pin: None,
        }
    }

    /// The policy may split an allocation between OS-owned and free ranges.
    /// Verify exact coverage without inventing a second ownership map.
    fn verify(&self) -> Result {
        self.map.validate().map_err(|_| EIO)?;
        let mut map_index = 0;
        let mut previous_end = 0;
        let mut bytes = 0_u64;
        for page in &self.pages {
            if page.physical < previous_end {
                return Err(EIO);
            }
            let mut cursor = page.physical;
            while cursor < page.end() {
                let range = self.map.extent(map_index).ok_or(EIO)?;
                let end = range.end().map_err(|_| EIO)?;
                if end <= cursor {
                    map_index += 1;
                    continue;
                }
                if range.start() > cursor || range.numa_node() != page.node {
                    return Err(EIO);
                }
                cursor = end.min(page.end());
            }
            previous_end = page.end();
            bytes = bytes.checked_add(page.len()).ok_or_else(overflow)?;
        }
        let mut mapped = 0_u64;
        for index in 0..self.map.len() {
            mapped = mapped
                .checked_add(self.map.extent(index).ok_or(EIO)?.length())
                .ok_or_else(overflow)?;
        }
        if bytes != mapped {
            return Err(EIO);
        }
        Ok(())
    }

    fn reserve(&mut self, request: &Request) -> Result<isize> {
        let mut demands = request.demands()?;
        demands.sort_unstable_by_key(|item| item.node);
        let mut written = 0;
        for index in 0..demands.len() {
            let demand = demands[index];
            if demand.bytes != u64::MAX && demand.bytes % USER_MEMORY_REQUEST_GRANULE != 0 {
                return Err(EINVAL);
            }
            if written > 0 && demands[written - 1].node == demand.node {
                if demands[written - 1].bytes == u64::MAX || demand.bytes == u64::MAX {
                    return Err(EINVAL);
                }
                demands[written - 1].bytes = demands[written - 1]
                    .bytes
                    .checked_add(demand.bytes)
                    .ok_or_else(overflow)?;
            } else {
                demands[written] = demand;
                written += 1;
            }
        }
        demands.truncate(written);
        let hotplug = MemoryHotplugGuard::lock();
        // Validate every node and budget before the first physical allocation.
        let mut budgets = Vec::with_capacity(demands.len(), GFP_NOWAIT)?;
        for demand in &demands {
            let free = hotplug.free_bytes(demand.node)?;
            let ratio = if demand.bytes == u64::MAX {
                if demand.node == 0 {
                    request.max_ratio.min(95)
                } else {
                    request.max_ratio
                }
            } else if demand.node == 0 {
                95
            } else {
                100
            };
            let limit =
                (free / 100 * ratio) / USER_MEMORY_REQUEST_GRANULE * USER_MEMORY_REQUEST_GRANULE;
            let wanted = if demand.bytes == u64::MAX {
                limit
            } else {
                demand.bytes
            };
            if wanted > limit {
                return Err(ENOMEM);
            }
            budgets.push(wanted, GFP_NOWAIT)?;
        }
        let mut pending = Vec::new();
        for (demand, &wanted) in demands.iter().zip(&budgets) {
            let mut acquired = 0_u64;
            let mut order = MAX_ORDER;
            // SAFETY: This ordinary Linux clock export returns a scalar time.
            let started = unsafe { bindings::ktime_get_seconds() } as u64;
            while acquired < wanted {
                if current!().signal_pending() {
                    return Err(ERESTARTSYS);
                }
                while PAGE_BYTES << order > wanted - acquired {
                    order -= 1;
                }
                match PageOwner::allocate(order, demand.node, &hotplug) {
                    Ok(page) => {
                        acquired += page.len();
                        pending.push(page, GFP_NOWAIT)?;
                    }
                    Err(error) if error == ENOMEM => {
                        // SAFETY: Scalar read from Linux's monotonic seconds clock.
                        let elapsed = (unsafe { bindings::ktime_get_seconds() } as u64)
                            .saturating_sub(started);
                        if order > request.min_order && elapsed <= request.timeout {
                            order -= 1;
                        } else if demand.bytes == u64::MAX {
                            break;
                        } else {
                            return Err(error);
                        }
                    }
                    Err(error) => return Err(error),
                }
            }
        }
        drop(hotplug);
        if pending.is_empty() {
            return Ok(0);
        }
        pending.sort_unstable_by_key(|page| page.physical);
        let mut ranges = Vec::with_capacity(pending.len(), GFP_NOWAIT)?;
        for page in &pending {
            ranges.push(page.extent()?, GFP_NOWAIT)?;
        }
        self.pages.reserve(pending.len(), GFP_NOWAIT)?;
        if self.pin.is_none() {
            self.pin = Some(ResourceModulePin::acquire()?);
        }
        let mut workspace = MemoryWorkspace::new(&mut self.staging).map_err(|_| EIO)?;
        let mut transaction = self
            .map
            .prepare_insert_free_batch(&ranges, &mut workspace)
            .map_err(|_| ENOMEM)?;
        transaction.begin_external_effects().map_err(|_| EIO)?;
        let original_len = self.pages.len();
        for page in pending {
            // Capacity was reserved before effects. Retain compensation even
            // for an unexpected allocation failure in the existing Vec API.
            if self.pages.push(page, GFP_NOWAIT).is_err() {
                self.pages.truncate(original_len);
                transaction.compensated_rollback().map_err(|_| EIO)?;
                return Err(ENOMEM);
            }
        }
        self.pages.sort_unstable_by_key(|page| page.physical);
        transaction.commit().map_err(|_| EIO)?;
        self.verify()?;
        Ok(0)
    }

    fn release(&mut self, request: &Request, partial: bool) -> Result<isize> {
        let demands = request.demands()?;
        let mut ranges = Vec::<MemoryExtent>::new();
        for demand in demands {
            if partial {
                // Reconstruct remaining free chunks after earlier requests
                // in this batch. Keep the legacy smallest-chunk-first order.
                let mut candidates: Vec<(u64, u64, usize, usize)> = Vec::new();
                let mut available = 0_u64;
                for (page_index, page) in self.pages.iter().enumerate() {
                    if page.node != demand.node
                        || ranges.iter().any(|range| range.start() == page.physical)
                    {
                        continue;
                    }
                    for index in 0..self.map.len() {
                        let range = self.map.extent(index).ok_or(EIO)?;
                        if range.owner().is_none()
                            && range.start() <= page.physical
                            && range.end().map_err(|_| EIO)? >= page.end()
                        {
                            available = available.checked_add(page.len()).ok_or_else(overflow)?;
                            if let Some(last) = candidates.last_mut() {
                                if last.1 + last.0 == page.physical && last.3 == page_index {
                                    last.0 += page.len();
                                    last.3 += 1;
                                    break;
                                }
                            }
                            candidates.push(
                                (page.len(), page.physical, page_index, page_index + 1),
                                GFP_NOWAIT,
                            )?;
                            break;
                        }
                    }
                }
                if available < demand.bytes {
                    return Err(EINVAL);
                }
                candidates.sort_unstable_by_key(|entry| (entry.0, entry.1));
                let mut left = demand.bytes;
                for (length, _, first, end) in candidates {
                    if left == 0 {
                        break;
                    }
                    if length <= left {
                        for page in &self.pages[first..end] {
                            ranges.push(page.extent()?, GFP_NOWAIT)?;
                        }
                        left -= length;
                        continue;
                    }
                    for page in &self.pages[first..end] {
                        // The legacy trim stops before splitting a compound
                        // allocation, and preserves 4-MiB alignment for small
                        // remainders. Never return more than was requested.
                        if page.len() > left
                            || (page.order > 0
                                && left < USER_MEMORY_REQUEST_GRANULE
                                && page.physical % USER_MEMORY_REQUEST_GRANULE == 0)
                        {
                            break;
                        }
                        ranges.push(page.extent()?, GFP_NOWAIT)?;
                        left -= page.len();
                        if left == 0 {
                            break;
                        }
                    }
                    break;
                }
            } else {
                let mut selected = None;
                for index in 0..self.map.len() {
                    let range = self.map.extent(index).ok_or(EIO)?;
                    if range.owner().is_none()
                        && range.length() == demand.bytes
                        && range.numa_node() == demand.node
                        && !ranges.iter().any(|prior| prior.start() == range.start())
                    {
                        selected = Some(range);
                        break;
                    }
                }
                ranges.push(selected.ok_or(EINVAL)?, GFP_NOWAIT)?;
            }
        }
        if ranges.is_empty() {
            return Ok(0);
        }
        ranges.sort_unstable_by_key(|range| range.start());
        let mut indices = Vec::new();
        let mut bytes = 0_u64;
        let mut wanted = 0_u64;
        for range in &ranges {
            wanted = wanted.checked_add(range.length()).ok_or_else(overflow)?;
        }
        for (index, page) in self.pages.iter().enumerate() {
            for range in &ranges {
                let end = range.end().map_err(|_| EIO)?;
                if page.physical < end && page.end() > range.start() {
                    if page.physical < range.start() || page.end() > end {
                        return Err(EINVAL);
                    }
                    indices.push(index, GFP_NOWAIT)?;
                    bytes = bytes.checked_add(page.len()).ok_or_else(overflow)?;
                    break;
                }
            }
        }
        if bytes != wanted {
            return Err(EIO);
        }
        let mut workspace = MemoryWorkspace::new(&mut self.staging).map_err(|_| EIO)?;
        let mut transaction = self
            .map
            .prepare_remove_free_batch(&ranges, &mut workspace)
            .map_err(|_| EINVAL)?;
        transaction.begin_external_effects().map_err(|_| EIO)?;
        for &index in indices.iter().rev() {
            drop(self.pages.remove(index));
        }
        transaction.commit().map_err(|_| EIO)?;
        self.verify()?;
        Ok(0)
    }

    fn query(
        &self,
        request: &Request,
        owner: Option<super::smp_resource::OsToken>,
    ) -> Result<isize> {
        let mut count = 0;
        for index in 0..self.map.len() {
            let range = self.map.extent(index).ok_or(EIO)?;
            if range.owner() == owner {
                if request.compat && request.count != 0 && range.length() > u32::MAX as u64 {
                    return Err(overflow());
                }
                count += 1;
            }
        }
        if request.count != 0 {
            if request.count < count {
                return Err(EINVAL);
            }
            let mut sizes =
                UserSlice::new(request.sizes, count * if request.compat { 4 } else { 8 }).writer();
            let mut nodes = UserSlice::new(request.nodes, count * 4).writer();
            for index in 0..self.map.len() {
                let range = self.map.extent(index).ok_or(EIO)?;
                if range.owner() == owner {
                    if request.compat {
                        sizes.write(&(range.length() as u32))?;
                    } else {
                        sizes.write(&range.length())?;
                    }
                    nodes.write(&(range.numa_node() as i32))?;
                }
            }
        }
        UserSlice::new(request.count_address, 4)
            .writer()
            .write(&(count as i32))?;
        Ok(0)
    }

    fn assign_os(
        &mut self,
        owner: super::smp_resource::OsToken,
        request: &Request,
    ) -> Result<isize> {
        // Copy all caller arrays before selecting or transferring any resource.
        let demands = request.demands()?;
        let mut available = Vec::with_capacity(self.map.len(), GFP_NOWAIT)?;
        for index in 0..self.map.len() {
            let range = self.map.extent(index).ok_or(EIO)?;
            if range.owner().is_none() {
                available.push(range, GFP_NOWAIT)?;
            }
        }
        let mut selected = Vec::new();
        for demand in demands {
            let all = demand.bytes == u64::MAX;
            if !all && (demand.bytes == 0 || demand.bytes % PAGE_BYTES != 0) {
                return Err(EINVAL);
            }
            let mut remaining = demand.bytes;
            let before = selected.len();
            while remaining != 0 {
                // Preserve the legacy exact-match-then-largest selection on
                // the requested node. Physical order breaks equal-size ties.
                let mut choice: Option<usize> = None;
                for (index, range) in available.iter().enumerate() {
                    if range.numa_node() != demand.node {
                        continue;
                    }
                    if range.length() == remaining {
                        choice = Some(index);
                        break;
                    }
                    if choice.is_none_or(|prior| available[prior].length() < range.length()) {
                        choice = Some(index);
                    }
                }
                let Some(index) = choice else {
                    if all && selected.len() != before {
                        break;
                    }
                    return Err(ENOMEM);
                };
                let range = available[index];
                let bytes = range.length().min(remaining);
                if selected.len() >= MAX_EXTENTS {
                    return Err(ENOMEM);
                }
                selected.push(
                    MemoryExtent::new(range.start(), bytes, demand.node, None)
                        .map_err(|_| EINVAL)?,
                    GFP_NOWAIT,
                )?;
                if bytes == range.length() {
                    available.remove(index);
                } else {
                    available[index] = MemoryExtent::new(
                        range.start() + bytes,
                        range.length() - bytes,
                        demand.node,
                        None,
                    )
                    .map_err(|_| EIO)?;
                }
                // Rust keeps metadata outside managed pages. A page-aligned
                // logical split may share a Linux compound allocation; its
                // original PageOwner stays pinned until all subranges are free.
                if !all {
                    remaining -= bytes;
                }
            }
        }
        selected.sort_unstable_by_key(|range| range.start());
        let mut workspace = MemoryWorkspace::new(&mut self.staging).map_err(|_| EIO)?;
        let mut transaction = self
            .map
            .prepare_assign_batch(owner, &selected, &mut workspace)
            .map_err(|_| EINVAL)?;
        transaction.begin_external_effects().map_err(|_| EIO)?;
        transaction
            .commit()
            .unwrap_or_else(|_| panic!("OS memory assignment invariant violated"));
        Ok(0)
    }

    fn release_os(
        &mut self,
        owner: super::smp_resource::OsToken,
        request: &Request,
    ) -> Result<isize> {
        let demands = request.demands()?;
        let mut selected: Vec<MemoryExtent> = Vec::with_capacity(demands.len(), GFP_NOWAIT)?;
        for demand in demands {
            let mut choice = None;
            for index in 0..self.map.len() {
                let range = self.map.extent(index).ok_or(EIO)?;
                if range.owner() == Some(owner)
                    && range.length() == demand.bytes
                    && range.numa_node() == demand.node
                    && !selected.iter().any(|prior| prior.start() == range.start())
                {
                    choice = Some(
                        MemoryExtent::new(range.start(), range.length(), range.numa_node(), None)
                            .map_err(|_| EIO)?,
                    );
                    break;
                }
            }
            selected.push(choice.ok_or(EINVAL)?, GFP_NOWAIT)?;
        }
        selected.sort_unstable_by_key(|range| range.start());
        let mut workspace = MemoryWorkspace::new(&mut self.staging).map_err(|_| EIO)?;
        let mut transaction = self
            .map
            .prepare_release_batch(owner, &selected, &mut workspace)
            .map_err(|_| EINVAL)?;
        transaction.begin_external_effects().map_err(|_| EIO)?;
        transaction
            .commit()
            .unwrap_or_else(|_| panic!("OS memory release invariant violated"));
        Ok(0)
    }
}

struct ContextStorage(UnsafeCell<MemoryContext>);
// SAFETY: Module init lends this static once to the pinned mutex. No other
// path accesses the UnsafeCell directly after that exclusive handoff.
unsafe impl Sync for ContextStorage {}
static CONTEXT: ContextStorage = ContextStorage(UnsafeCell::new(MemoryContext::new()));
type ContextMutex = Mutex<&'static mut MemoryContext>;
static PUBLISHED: AtomicPtr<ContextMutex> = AtomicPtr::new(ptr::null_mut());

pub(super) struct MemoryController {
    mutex: Pin<Box<ContextMutex>>,
}

impl MemoryController {
    pub(super) fn new() -> Result<Self> {
        // SAFETY: Exclusive module init before control-device publication.
        // Only this small reference reaches the stack, not the map/workspace.
        let context = unsafe { &mut *CONTEXT.0.get() };
        let mutex = Box::pin_init(new_mutex!(context), GFP_KERNEL)?;
        PUBLISHED.store(
            (&*mutex as *const ContextMutex).cast_mut(),
            Ordering::Release,
        );
        Ok(Self { mutex })
    }
}

impl Drop for MemoryController {
    fn drop(&mut self) {
        PUBLISHED.store(ptr::null_mut(), Ordering::Release);
        // Open files and reservation pins exclude teardown while pages remain.
        // Keeping the mutex field here also keeps its static context borrow live.
        let mut context = self.mutex.lock();
        // Rust statics have no automatic destructor. Release the descriptor
        // vector's capacity even when all physical allocations were returned.
        drop(core::mem::take(&mut context.pages));
    }
}

pub(super) fn handles(command: u32) -> bool {
    matches!(
        command,
        abi::IHK_DEVICE_RESERVE_MEM
            | abi::IHK_DEVICE_RELEASE_MEM
            | abi::IHK_DEVICE_QUERY_MEM
            | abi::IHK_DEVICE_RELEASE_MEM_PARTIALLY
    )
}

pub(super) fn ioctl(command: u32, argument: usize, compat: bool) -> Result<isize> {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: The open miscdevice file pins the module and published mutex.
    let mut context = unsafe { &*published }.lock();
    context.verify()?;
    let request = Request::read(argument, compat)?;
    let result = match command {
        abi::IHK_DEVICE_RESERVE_MEM => context.reserve(&request),
        abi::IHK_DEVICE_RELEASE_MEM => context.release(&request, false),
        abi::IHK_DEVICE_RELEASE_MEM_PARTIALLY => context.release(&request, true),
        abi::IHK_DEVICE_QUERY_MEM => context.query(&request, None),
        _ => Err(EINVAL),
    };
    if context.map.is_empty() && context.pages.is_empty() && !context.map.is_poisoned() {
        context.pin.take();
    }
    result
}

pub(super) fn handles_os(command: u32) -> bool {
    matches!(
        command,
        abi::IHK_OS_ASSIGN_MEM | abi::IHK_OS_RELEASE_MEM | abi::IHK_OS_QUERY_MEM
    )
}

/// IHK's live OS object pins the module and serializes this initial-state call.
pub(super) fn os_ioctl(
    owner: super::smp_resource::OsToken,
    command: u32,
    argument: usize,
    compat: bool,
) -> Result<isize> {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: The OS object's provider module reference keeps this published
    // mutex and context live for the callback. No guard or owner escapes.
    let mut context = unsafe { &*published }.lock();
    context.verify()?;
    // Legacy OS requests validate count/pointers, nonnegative minimum and the
    // ratio. Allocation-order and timeout limits apply only to reservation.
    let request = Request::read_scope(argument, compat, false)?;
    match command {
        abi::IHK_OS_ASSIGN_MEM => context.assign_os(owner, &request),
        abi::IHK_OS_RELEASE_MEM => context.release_os(owner, &request),
        abi::IHK_OS_QUERY_MEM => context.query(&request, Some(owner)),
        _ => Err(EINVAL),
    }
}

/// Called with the CPU policy lock and exclusive OS destruction held. Invoke
/// the preflighted CPU commit only after memory preflight, retaining both locks
/// until both maps have changed. No Linux allocation or module owner is freed.
pub(super) fn release_os_resources(
    owner: super::smp_resource::OsToken,
    commit_cpu: impl FnOnce(),
) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: The IHK destruction callback retains the provider module until
    // this borrowed controller, its lock and the CPU commit callback finish.
    let mut guard = unsafe { &*published }.lock();
    let context = &mut **guard;
    context.verify()?;
    let mut workspace = MemoryWorkspace::new(&mut context.staging).map_err(|_| EIO)?;
    let mut transaction = context
        .map
        .prepare_release_all(owner, &mut workspace)
        .map_err(|_| EIO)?;
    transaction.begin_external_effects().map_err(|_| EIO)?;
    commit_cpu();
    transaction
        .commit()
        .unwrap_or_else(|_| panic!("OS memory cleanup invariant violated"));
    Ok(())
}
