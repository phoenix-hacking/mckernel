// SPDX-License-Identifier: GPL-2.0
//! Linux page owners and memory ioctls for the existing SMP memory policy.
//!
//! Temporary allocations stay private until the complete batch can enter the
//! existing MemoryMap. The policy workspace lives off the kernel stack. Each
//! allocation retains its original compound-page order until return to Linux.

use super::smp_cpu::{BootCpu, BootIrqRoute, BootTopology, ResourceModulePin};
use super::smp_image::{BootLayout, ImageError, ImagePlan, NativeBootAbi, IDENTITY_WINDOW_END};
use super::smp_resource::{MemoryExtent, MemoryMap, MemoryWorkspace, USER_MEMORY_REQUEST_GRANULE};
use super::smp_startup::{PageTablePlan, TABLE_BYTES, TABLE_PAGES};
use core::{
    cell::UnsafeCell,
    marker::PhantomData,
    mem::{offset_of, size_of, ManuallyDrop},
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
    fn allocate(order: u32, node: u32, hotplug: &MemoryHotplugGuard) -> Result<Self> {
        Self::allocate_scope(order, Some(node), false, hotplug)
    }

    fn allocate_startup(hotplug: &MemoryHotplugGuard) -> Result<Self> {
        // The real-mode entry loads a 32-bit CR3. A high-NUMA image may still
        // use low Linux tables; do not force THISNODE on this separate owner.
        const _: () = assert!(TABLE_BYTES <= 4096 << 9);
        Self::allocate_scope(9, None, true, hotplug)
    }

    fn allocate_scope(
        order: u32,
        node: Option<u32>,
        dma32: bool,
        _hotplug: &MemoryHotplugGuard,
    ) -> Result<Self> {
        if order > MAX_ORDER || node.is_some_and(|node| node as usize >= MAX_NODES) {
            return Err(EINVAL);
        }
        // Reuse the existing KmsgPages ownership approach, adding strict NUMA
        // placement. Never consume atomic reserves or request OOM escalation.
        let mut flags = bindings::GFP_KERNEL
            | bindings::__GFP_ZERO
            | (1 << bindings::___GFP_COMP_BIT)
            | (1 << bindings::___GFP_NORETRY_BIT)
            | (1 << bindings::___GFP_NOWARN_BIT);
        if node.is_some() {
            flags |= 1 << bindings::___GFP_THISNODE_BIT;
        }
        if dma32 {
            flags |= 1 << bindings::___GFP_DMA32_BIT;
        }
        // SAFETY: Memory hotplug is excluded. A requested concrete node was
        // checked; the low-level allocator never receives NUMA_NO_NODE. The
        // ordinary exported allocator resolves the current Linux policy when
        // no fixed node is requested. Bounded orders and flags are valid;
        // THISNODE is set only for strict-node resource reservations.
        let raw = unsafe {
            match node {
                Some(node) => {
                    bindings::__alloc_pages_noprof(flags, order, node as i32, ptr::null_mut())
                }
                None => bindings::alloc_pages_noprof(flags, order),
            }
        };
        let page = NonNull::new(raw).ok_or(ENOMEM)?;
        let mut owner = Self {
            page,
            order,
            node: 0,
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
        owner.node = ((page_flags >> 54) & bindings::NODES_MASK as u64) as u32;
        if node.is_some_and(|node| owner.node != node)
            || owner.node as usize >= MAX_NODES
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

/// Linux owns the entire original compound allocation until this unbooted
/// image is invalidated. No CPU or caller receives a pointer or capability.
struct StartupTables {
    _pages: PageOwner,
    plan: PageTablePlan,
    checksum: u64,
}

impl StartupTables {
    fn new(layout: BootLayout, direct_map: u64) -> Result<Self> {
        let hotplug = MemoryHotplugGuard::lock();
        let pages = match PageOwner::allocate_startup(&hotplug) {
            Ok(pages) => pages,
            Err(error) => {
                pr_info!("IHK-SMP: startup table allocation failed order=9; CPUs not started\n");
                return Err(error);
            }
        };
        let plan = PageTablePlan::new(pages.physical, layout).map_err(|_| EIO)?;
        let address = direct_map
            .checked_add(pages.physical)
            .ok_or_else(overflow)?;
        address
            .checked_add(TABLE_BYTES as u64)
            .ok_or_else(overflow)?;
        // SAFETY: This newly owned, zeroed, non-movable compound allocation
        // is private. The useful table extent fits inside that single Linux
        // allocation and is aligned for u64. No alias or CPU sees the pages.
        // fill writes only checked entries and retains no borrowed reference.
        let entries =
            unsafe { core::slice::from_raw_parts_mut(address as *mut u64, TABLE_BYTES / 8) };
        plan.fill(entries).map_err(|_| EIO)?;
        let mut checksum = 0xcbf2_9ce4_8422_2325_u64;
        for offset in 0..TABLE_BYTES {
            // SAFETY: The original allocation remains exclusively owned.
            // Read actual initialized memory, wholly within its useful extent;
            // the temporary mutable fill borrow has ended before this access.
            let byte = unsafe { ptr::read_volatile((address as *const u8).add(offset)) };
            checksum = (checksum ^ byte as u64).wrapping_mul(0x100_0000_01b3);
        }
        Ok(Self {
            _pages: pages,
            plan,
            checksum,
        })
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
    images: [Option<LoadedImage>; 64],
    arguments: [Option<(super::smp_resource::OsToken, [u8; 256])>; 64],
}

// Loading does not publish a boot capability. The following AP-start adapter
// must revalidate this generation and its layout under the same resource locks.
#[allow(dead_code)]
struct LoadedImage {
    owner: super::smp_resource::OsToken,
    layout: BootLayout,
    entry: u64,
    checksum: u64,
    tables: ManuallyDrop<StartupTables>,
    native_boot_abi: Option<NativeBootAbi>,
    boot: Option<BootStorage>,
}

impl LoadedImage {
    fn started(&self) -> bool {
        self.boot.as_ref().is_some_and(|boot| boot.started)
    }
}

impl Drop for LoadedImage {
    fn drop(&mut self) {
        if !self.started() {
            // SAFETY: No CPU-start effect occurred. This is the only destructor
            // for the original startup allocation; the field has no auto-drop.
            unsafe { ManuallyDrop::drop(&mut self.tables) };
        }
        // A started image deliberately retains both tables and BootStorage.
        // The resource-map guards separately forbid freeing assigned memory.
    }
}

/// One original Linux allocation, used only through bounded preparation writes
/// and raw status reads after publication. No Rust slice escapes a method.
struct BootPages {
    pages: PageOwner,
    address: u64,
    bytes: usize,
}

impl BootPages {
    fn allocate(bytes: usize, direct_map: u64) -> Result<Self> {
        if bytes == 0 || bytes > (4096 << MAX_ORDER) {
            return Err(ENOMEM);
        }
        let pages_needed = bytes.div_ceil(4096).next_power_of_two();
        let hotplug = MemoryHotplugGuard::lock();
        let pages = PageOwner::allocate_scope(pages_needed.trailing_zeros(), None, true, &hotplug)?;
        if pages.end() > IDENTITY_WINDOW_END {
            return Err(EINVAL);
        }
        let address = direct_map
            .checked_add(pages.physical)
            .ok_or_else(overflow)?;
        address.checked_add(pages.len()).ok_or_else(overflow)?;
        Ok(Self {
            pages,
            address,
            bytes,
        })
    }

    fn put(&mut self, offset: usize, bytes: &[u8]) -> Result {
        let end = offset.checked_add(bytes.len()).ok_or_else(overflow)?;
        if end > self.bytes {
            return Err(EINVAL);
        }
        // SAFETY: This unstarted exclusive owner retains one complete Linux
        // allocation. The checked source/destination belong to distinct storage.
        unsafe {
            ptr::copy_nonoverlapping(
                bytes.as_ptr(),
                (self.address as *mut u8).add(offset),
                bytes.len(),
            )
        };
        Ok(())
    }
    fn put64(&mut self, offset: usize, value: u64) -> Result {
        self.put(offset, &value.to_le_bytes())
    }
    fn put32(&mut self, offset: usize, value: u32) -> Result {
        self.put(offset, &value.to_le_bytes())
    }
    fn physical(&self) -> u64 {
        self.pages.physical
    }

    fn read64(&self, offset: usize) -> Result<u64> {
        if offset % 8 != 0 || offset.checked_add(8).is_none_or(|end| end > self.bytes) {
            return Err(EINVAL);
        }
        // SAFETY: The owner retains this aligned ABI field for the full guest
        // lifetime. It is shared with the independently executing co-kernel;
        // only a single volatile scalar is read, without a Rust reference to
        // its concurrently updated boot-parameter header.
        Ok(unsafe { ptr::read_volatile((self.address + offset as u64) as *const u64) })
    }

    /// Only on a new private allocation, before handing its address to a peer.
    fn initialize_queue(
        &mut self,
        channel_id: u32,
        port: u16,
    ) -> Result<*mut super::abi::IhkIkcQueueHead> {
        // SAFETY: The original compound allocation is still exclusive. This
        // temporary slice and queue view end before any raw endpoint attaches.
        let storage =
            unsafe { core::slice::from_raw_parts_mut(self.address as *mut u8, self.bytes) };
        let queue = super::ikc_queue::SharedQueue::initialize(
            storage,
            1,
            port,
            super::smp_ikc::CONTROL_PACKET_BYTES as u16,
        )
        .map_err(|error| {
            kernel::error::to_result(error.legacy_status())
                .err()
                .unwrap_or(EIO)
        })?;
        drop(queue);
        self.put32(
            offset_of!(super::abi::IhkIkcQueueHead, channel_id),
            channel_id,
        )?;
        // All native boot IRQ routes currently target pinned Linux CPU 0.
        self.put32(offset_of!(super::abi::IhkIkcQueueHead, read_cpu), 0)?;
        Ok(self.address as *mut super::abi::IhkIkcQueueHead)
    }
}

/// Endpoint views retire before the private allocation on any prepublication
/// error. Once published, PreparedBoot retains both through every boot outcome.
struct OwnedControlChannel {
    channel: super::smp_ikc::ControlChannel,
    pages: BootPages,
}

fn checked_guest_queue(
    map: &MemoryMap<MAX_EXTENTS>,
    owner: super::smp_resource::OsToken,
    direct_map: u64,
    physical: u64,
    bytes: usize,
) -> Result<*mut super::abi::IhkIkcQueueHead> {
    let end = physical.checked_add(bytes as u64).ok_or(EINVAL)?;
    if physical == 0 || physical % 4096 != 0 || bytes == 0 || end > IDENTITY_WINDOW_END {
        return Err(EINVAL);
    }
    for index in 0..map.len() {
        let extent = map.extent(index).ok_or(EIO)?;
        if extent.owner() == Some(owner)
            && extent.start() <= physical
            && end <= extent.end().map_err(|_| EIO)?
        {
            return Ok(
                direct_map.checked_add(physical).ok_or(EINVAL)? as *mut super::abi::IhkIkcQueueHead
            );
        }
    }
    Err(EINVAL)
}

fn accept_control_channel(
    map: &MemoryMap<MAX_EXTENTS>,
    owner: super::smp_resource::OsToken,
    cpus: &[BootCpu],
    channels: &mut Vec<OwnedControlChannel>,
    direct_map: u64,
    master_receive: u64,
    master_send: u64,
    master_bytes: usize,
    offer: super::ikc_master::ConnectOffer,
) -> Result<super::ikc_master::AcceptSuccess> {
    use super::smp_ikc::{ControlChannel, CONTROL_QUEUE_BYTES};
    if offer.receive_queue != 0
        || offer.remote_channel_cookie == 0
        || offer.reference == 0
        || !matches!((offer.port, offer.interrupt_cpu), (501, -1) | (503, 0))
    {
        return Err(EINVAL);
    }
    let peer = checked_guest_queue(
        map,
        owner,
        direct_map,
        offer.send_queue,
        CONTROL_QUEUE_BYTES,
    )?;
    let end = offer.send_queue + CONTROL_QUEUE_BYTES as u64;
    for (physical, bytes) in [(master_receive, master_bytes), (master_send, master_bytes)] {
        if offer.send_queue < physical + bytes as u64 && physical < end {
            return Err(EINVAL);
        }
    }
    // SAFETY: The entire peer queue mapping was proven inside this OS's owned
    // memory. These fields are fixed before CONNECT publication; use raw reads
    // without creating references to concurrently owned queue/header storage.
    let (guest_cpu, channel_id, port) = unsafe {
        (
            ptr::read_volatile(ptr::addr_of!((*peer).read_cpu)),
            ptr::read_volatile(ptr::addr_of!((*peer).channel_id)),
            ptr::read_volatile(ptr::addr_of!((*peer).type_)),
        )
    };
    if guest_cpu as usize >= cpus.len()
        || channel_id != offer.reference
        || port as i32 != offer.port
    {
        return Err(EINVAL);
    }
    for old in channels.iter() {
        let old = &old.channel;
        if old.owner != owner {
            return Err(EIO);
        }
        if old.port == offer.port && (offer.port == 503 || old.guest_cpu == guest_cpu) {
            return Err(EBUSY);
        }
        for physical in [old.send_physical, old.receive_physical] {
            if offer.send_queue < physical + CONTROL_QUEUE_BYTES as u64 && physical < end {
                return Err(EBUSY);
            }
        }
    }
    if channels.len() >= cpus.len() + 1 {
        return Err(EBUSY);
    }
    // Cookies are local indices scoped by the exact OS generation. A received
    // cookie is matched against these records and is never cast to a pointer.
    let cookie = channels.len() as u64 + 1;
    let mut pages = BootPages::allocate(CONTROL_QUEUE_BYTES, direct_map)?;
    let receive = pages.initialize_queue(cookie as u32, offer.port as u16)?;
    let physical = pages.physical();
    // SAFETY: The checked peer's writer-CPU field is owned by this endpoint;
    // geometry/reader identity remain unchanged. Publication occurs in reply.
    unsafe { ptr::write_volatile(ptr::addr_of_mut!((*peer).write_cpu), 0) };
    // SAFETY: The private receive allocation and checked disjoint peer queue
    // have no aliases, use the version-2 protocol, and belong to this owner.
    let channel = unsafe {
        ControlChannel::new(
            owner,
            cookie,
            offer.port,
            guest_cpu,
            physical,
            offer.send_queue,
            receive,
            peer,
        )?
    };
    // Store every owner before a reply can expose physical memory to McKernel.
    channels.push(OwnedControlChannel { channel, pages }, GFP_KERNEL)?;
    pr_info!("IHK-SMP: control accepted os={} generation={} port={} guest_cpu={} linux_cpu={} cookie={} receive={:x} send={:x} bytes={} reference={} remote_cookie={:x}\n",
        owner.slot(), owner.generation(), offer.port, guest_cpu, cpus[guest_cpu as usize].linux_id,
        cookie, physical, offer.send_queue, CONTROL_QUEUE_BYTES, offer.reference, offer.remote_channel_cookie);
    Ok(super::ikc_master::AcceptSuccess {
        receive_queue: physical,
        accepted_channel_cookie: cookie,
    })
}

struct PreparedBoot {
    params: BootPages,
    _dump: BootPages,
    trampoline: super::smp_trampoline::LowRegion,
    irq: BootIrqRoute,
    cpus: Vec<BootCpu>,
    master: Option<Box<super::smp_ikc::BootMaster>>,
    channels: Vec<OwnedControlChannel>,
}

/// Turning started on is irreversible without an implemented stop/drain proof.
/// Even accidental metadata retirement cannot drop live boot/callback storage.
struct BootStorage {
    prepared: ManuallyDrop<PreparedBoot>,
    started: bool,
}

impl Drop for BootStorage {
    fn drop(&mut self) {
        if !self.started {
            // SAFETY: Preparation had no CPU effect. This is the unique final
            // cleanup path for all original page/resource/IRQ-route owners.
            unsafe { ManuallyDrop::drop(&mut self.prepared) };
        }
    }
}

extern "C" {
    // Exact existing Linux APIs, with patch 0006 exporting the unchanged start
    // implementation and permanent data symbol. Opaque addresses never borrow
    // a Linux task's private page-table lifetime.
    static init_top_pgt: u8;
    static mut raised_list: core::ffi::c_void;
    fn per_cpu_ptr_to_phys(address: *mut core::ffi::c_void) -> u64;
    fn wakeup_secondary_cpu_via_init(apic_id: u32, physical: u64, cpu: u32) -> i32;
}

fn linux_boot_root() -> Result<u64> {
    // The preserved guest owns four-level mappings. Reject an active LA57
    // Linux root before exposing it to the guest's existing page-table walker.
    #[cfg(CONFIG_X86_5LEVEL)]
    if unsafe { bindings::pgdir_shift } != 39 {
        return Err(EINVAL);
    }
    let offset = (&raw const init_top_pgt as u64)
        .checked_sub(0xffff_ffff_8000_0000)
        .ok_or(EIO)?;
    if offset >= 1 << 30 {
        return Err(EIO);
    }
    // SAFETY: phys_base is Linux's boot-initialized __pa_symbol base. The
    // permanent assembly symbol uses the kernel-image mapping, not PAGE_OFFSET.
    let physical = offset
        .checked_add(unsafe { bindings::phys_base })
        .ok_or(EIO)?;
    if physical % 4096 != 0 || physical >= IDENTITY_WINDOW_END {
        return Err(EIO);
    }
    Ok(physical)
}

fn image_error(error: ImageError) -> Error {
    match error {
        ImageError::NoBootstrapMemory | ImageError::OutsideBootstrap => ENOMEM,
        ImageError::InvalidOwnership => EIO,
        ImageError::Overflow => overflow(),
        _ => EINVAL,
    }
}

impl MemoryContext {
    fn require_unstarted(&self, owner: super::smp_resource::OsToken) -> Result {
        if let Some(image) = self
            .images
            .get(owner.slot() as usize)
            .ok_or(EINVAL)?
            .as_ref()
        {
            if image.owner != owner {
                return Err(EIO);
            }
            if image.started() {
                return Err(EBUSY);
            }
        }
        Ok(())
    }
    const fn new() -> Self {
        Self {
            map: MemoryMap::new(),
            staging: [None; MAX_EXTENTS],
            pages: Vec::new(),
            pin: None,
            images: [const { None }; 64],
            arguments: [const { None }; 64],
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
        self.require_unstarted(owner)?;
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
        self.images[owner.slot() as usize] = None;
        Ok(0)
    }

    fn release_os(
        &mut self,
        owner: super::smp_resource::OsToken,
        request: &Request,
    ) -> Result<isize> {
        self.require_unstarted(owner)?;
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
        self.images[owner.slot() as usize] = None;
        Ok(0)
    }

    fn invalidate_image(&mut self, owner: super::smp_resource::OsToken) -> Result {
        self.require_unstarted(owner)?;
        let slot = self.images.get_mut(owner.slot() as usize).ok_or(EINVAL)?;
        if slot.as_ref().is_some_and(|image| image.owner != owner) {
            return Err(EIO);
        }
        *slot = None;
        Ok(())
    }

    /// Split access at original Linux allocation boundaries: logical adjacency
    /// in MemoryMap does not create one Rust allocation spanning two PageOwners.
    fn write_image_range(
        &mut self,
        direct_map: u64,
        start: u64,
        length: usize,
        source: Option<&[u8]>,
    ) -> Result {
        let end = start.checked_add(length as u64).ok_or_else(overflow)?;
        if source.is_some_and(|data| data.len() != length) {
            return Err(EIO);
        }
        let mut cursor = start;
        for page in &mut self.pages {
            if page.end() <= cursor {
                continue;
            }
            if cursor == end {
                break;
            }
            if page.physical > cursor {
                return Err(EIO);
            }
            let count = (end.min(page.end()) - cursor) as usize;
            let address = direct_map.checked_add(cursor).ok_or_else(overflow)?;
            address.checked_add(count as u64).ok_or_else(overflow)?;
            // SAFETY: verify() proves the retained PageOwners exactly cover
            // the canonical map. The caller holds CPU and memory locks for an
            // unbooted OS and preflighted this range as exclusively assigned.
            // This chunk lies in one original non-movable allocation's direct
            // map. The immutable vmalloc input is a separate Linux allocation.
            unsafe {
                if let Some(data) = source {
                    core::ptr::copy_nonoverlapping(
                        data.as_ptr().add((cursor - start) as usize),
                        address as *mut u8,
                        count,
                    );
                } else {
                    core::ptr::write_bytes(address as *mut u8, 0, count);
                }
            }
            cursor += count as u64;
        }
        if cursor != end {
            return Err(EIO);
        }
        Ok(())
    }

    fn load_image(&mut self, owner: super::smp_resource::OsToken, image: &[u8]) -> Result {
        self.verify()?;
        self.invalidate_image(owner)?;
        let layout = BootLayout::select(&self.map, owner).map_err(image_error)?;
        let plan = ImagePlan::parse(image, layout).map_err(image_error)?;
        // SAFETY: The selected DYNAMIC_MEMORY_LAYOUT x86_64 kernel initializes
        // this direct-map base before module loading; it is stable thereafter.
        let direct_map = unsafe { bindings::page_offset_base };
        direct_map
            .checked_add(layout.extent().end().map_err(|_| EIO)?)
            .ok_or_else(overflow)?;
        // Allocate and fill tables before the first image write. On failure,
        // the original page owner drops and no loaded image can be published.
        let tables = StartupTables::new(layout, direct_map)?;
        // No image write occurs before ALL ELF and startup-space checks.
        // Zeroing the entire bounded image window also clears holes and BSS.
        self.write_image_range(
            direct_map,
            layout.kernel().start(),
            layout.kernel().length() as usize,
            None,
        )?;
        for segment in plan.segments() {
            self.write_image_range(
                direct_map,
                segment.destination,
                segment.file.len(),
                Some(segment.file),
            )?;
        }
        let mut checksum = 0xcbf2_9ce4_8422_2325_u64;
        let start = layout.kernel().start();
        let end = layout.kernel().end();
        for page in &self.pages {
            let first = start.max(page.physical);
            let last = end.min(page.end());
            for physical in first..last {
                // SAFETY: Same exclusive retained allocation and direct-map
                // proof as the write path. Each actual byte is read back after
                // loading; no reference spans separate compound allocations.
                let byte = unsafe { ptr::read_volatile((direct_map + physical) as *const u8) };
                checksum = (checksum ^ byte as u64).wrapping_mul(0x100_0000_01b3);
            }
        }
        pr_info!("IHK-SMP: startup tables os={} generation={} root={:x} image={:x} pages={} checksum={:016x}; CPUs not started\n",
                 owner.slot(), owner.generation(), tables.plan.root(),
                 layout.kernel().start(), TABLE_PAGES, tables.checksum);
        self.images[owner.slot() as usize] = Some(LoadedImage {
            owner,
            layout,
            entry: plan.entry(),
            checksum,
            tables: ManuallyDrop::new(tables),
            native_boot_abi: plan.native_boot_abi(),
            boot: None,
        });
        pr_info!("IHK-SMP: image loaded os={} generation={} segments={} window={} checksum={:016x}; CPUs not started\n",
                 owner.slot(), owner.generation(), plan.load_segments(),
                 layout.kernel().length(), checksum);
        Ok(())
    }

    fn prepare_boot(
        &mut self,
        owner: super::smp_resource::OsToken,
        topology: &BootTopology<'_>,
        kmsg: u64,
        kmsg_bytes: u64,
        trampoline_physical: u64,
    ) -> Result {
        self.verify()?;
        self.require_unstarted(owner)?;
        let loaded = self.images[owner.slot() as usize].as_mut().ok_or(EINVAL)?;
        let boot_abi = loaded.native_boot_abi.ok_or(EINVAL)?;
        // Older native images remain loadable, but cannot safely reuse reply
        // slots. Reject them before taking the trampoline or preparing startup.
        if !boot_abi.completed_queue_reads {
            return Err(EINVAL);
        }
        let (layout, entry, root) = (loaded.layout, loaded.entry, loaded.tables.plan.root());
        loaded.boot.take();
        if kmsg == 0
            || kmsg % 4096 != 0
            || kmsg_bytes != 4 << 20
            || kmsg
                .checked_add(kmsg_bytes)
                .is_none_or(|end| end > IDENTITY_WINDOW_END)
        {
            return Err(EINVAL);
        }
        // Default module configuration has no startup page. A real boot needs
        // an explicit independently carved, exclusively owned low-memory page.
        let mut trampoline = super::smp_trampoline::LowRegion::acquire(trampoline_physical)?;
        let linux_root = linux_boot_root()?;
        let mut cpus = Vec::with_capacity(topology.cpus().len(), GFP_KERNEL)?;
        let mut nodes = Vec::with_capacity(MAX_NODES, GFP_KERNEL)?;
        for &cpu in topology.cpus() {
            if cpu.numa_node as usize >= MAX_NODES {
                return Err(EINVAL);
            }
            cpus.push(cpu, GFP_KERNEL)?;
            if !nodes.contains(&cpu.numa_node) {
                nodes.push(cpu.numa_node, GFP_KERNEL)?;
            }
        }
        let mut chunks = Vec::with_capacity(self.map.len(), GFP_KERNEL)?;
        let mut first = u64::MAX;
        let mut last = 0;
        let mut dump_bytes = 0_usize;
        for index in 0..self.map.len() {
            let range = self.map.extent(index).ok_or(EIO)?;
            if range.owner() != Some(owner) {
                continue;
            }
            let end = range.end().map_err(|_| EIO)?;
            if end > IDENTITY_WINDOW_END {
                return Err(EINVAL);
            }
            first = first.min(range.start());
            last = last.max(end);
            if !nodes.contains(&range.numa_node()) {
                nodes.push(range.numa_node(), GFP_KERNEL)?;
            }
            chunks.push(range, GFP_KERNEL)?;
            let words =
                usize::try_from(range.length().div_ceil(4096 * 64)).map_err(|_| overflow())?;
            dump_bytes = dump_bytes
                .checked_add(
                    size_of::<abi::IhkDumpPagePrefix>()
                        + words.checked_mul(8).ok_or_else(overflow)?,
                )
                .ok_or_else(overflow)?;
        }
        if chunks.is_empty() || nodes.is_empty() || nodes.len() > MAX_NODES {
            return Err(EINVAL);
        }
        nodes.sort_unstable();
        // Preserve the pinned boot ABI's NUMA-major chunk ordering.
        chunks.sort_unstable_by_key(|range| (range.numa_node(), range.start()));
        let cpu_offset = boot_abi.header_bytes;
        let node_offset = cpu_offset
            .checked_add(cpus.len() * size_of::<abi::IhkSmpBootParamCpu>())
            .ok_or_else(overflow)?;
        let chunk_offset = node_offset
            .checked_add(nodes.len() * size_of::<abi::IhkSmpBootParamNumaNode>())
            .ok_or_else(overflow)?;
        let distance_offset = chunk_offset
            .checked_add(chunks.len() * size_of::<abi::IhkSmpBootParamMemoryChunk>())
            .ok_or_else(overflow)?;
        let param_bytes = distance_offset
            .checked_add(nodes.len() * nodes.len() * 4)
            .ok_or_else(overflow)?
            .checked_add(4095)
            .ok_or_else(overflow)?
            & !4095;
        let dump_bytes = dump_bytes.checked_add(4095).ok_or_else(overflow)? & !4095;
        // SAFETY: Linux initializes this direct-map base before module loading.
        let direct_map = unsafe { bindings::page_offset_base };
        let mut params = BootPages::allocate(param_bytes, direct_map)?;
        let mut dump = BootPages::allocate(dump_bytes, direct_map)?;
        let irq = BootIrqRoute::new(owner, topology)?;
        macro_rules! put64 {
            ($field:ident, $value:expr) => {
                params.put64(offset_of!(abi::IhkSmpBootParam, $field), $value)?
            };
        }
        macro_rules! put32 {
            ($field:ident, $value:expr) => {
                params.put32(offset_of!(abi::IhkSmpBootParam, $field), $value as u32)?
            };
        }
        put64!(start, first);
        put64!(end, last);
        put32!(parameter_size, param_bytes);
        put64!(
            bootstrap_memory_end,
            layout.extent().end().map_err(|_| EIO)?
        );
        put64!(message_buffer, kmsg);
        put64!(message_buffer_size, kmsg_bytes);
        put64!(linux_kernel_page_table_physical, linux_root);
        put64!(page_offset_base, direct_map);
        put64!(identity_table, root);
        if let Some((argument_owner, bytes)) = &self.arguments[owner.slot() as usize] {
            if *argument_owner != owner {
                return Err(EIO);
            }
            params.put(offset_of!(abi::IhkSmpBootParam, kernel_args), bytes)?;
        }
        // Same documented scaled nanoseconds-per-TSC fallback as the pinned
        // IHK calc_ns_per_tsc, using Linux's calibrated exported frequency.
        let khz = unsafe { bindings::tsc_khz };
        if khz == 0 {
            return Err(EIO);
        }
        put64!(nanoseconds_per_tsc, 1_000_000_000 / khz as u64);
        let mut now = bindings::timespec64::default();
        // SAFETY: Linux fills a complete local timespec, without retaining it.
        unsafe { bindings::ktime_get_real_ts64(&mut now) };
        if now.tv_sec < 0 || now.tv_nsec < 0 || now.tv_nsec >= 1_000_000_000 {
            return Err(EIO);
        }
        put64!(boot_seconds, now.tv_sec as u64);
        put64!(boot_nanoseconds, now.tv_nsec as u64);
        let low: u32;
        let high: u32;
        // SAFETY: RDTSC reads this x86 counter and has no memory side effect.
        unsafe {
            core::arch::asm!("rdtsc", out("eax") low, out("edx") high, options(nomem, nostack))
        };
        put64!(boot_tsc, (high as u64) << 32 | low as u64);
        put64!(ikc_irq_work_function, irq.callback() as u64);
        put32!(ikc_irq, 0xf6);
        put32!(nr_linux_cpus, topology.linux_cpus());
        put32!(nr_cpus, cpus.len());
        put32!(nr_numa_nodes, nodes.len());
        put32!(nr_memory_chunks, chunks.len());
        put32!(os_number, owner.slot());
        // The supported x86 default huge-page geometry is 2 MiB. No huge-page
        // allocation capability or performance-event mapping is advertised here.
        put32!(linux_default_huge_page_shift, 21);
        let dump_set = offset_of!(abi::IhkSmpBootParam, dump_page_set);
        params.put32(
            dump_set + offset_of!(abi::IhkDumpPageSet, count),
            chunks.len() as u32,
        )?;
        params.put64(
            dump_set + offset_of!(abi::IhkDumpPageSet, page_size),
            dump_bytes as u64,
        )?;
        params.put64(
            dump_set + offset_of!(abi::IhkDumpPageSet, physical_page),
            dump.physical(),
        )?;
        for cpu in 0..topology.linux_cpus() {
            let snapshot = match topology.host_cpu(cpu) {
                Ok(snapshot) => snapshot,
                Err(error) if error == ENODEV => continue,
                Err(error) => return Err(error),
            };
            params.put32(
                offset_of!(abi::IhkSmpBootParam, ikc_irq_apic_ids) + cpu * 4,
                snapshot.hardware_id,
            )?;
            // SAFETY: The retained topology guard bounds the per-CPU offset
            // and keeps the resident Linux queue allocation stable. Integer
            // token arithmetic matches Linux per_cpu_ptr; no Rust object spans
            // the linker symbol and its per-CPU offset.
            let address = unsafe {
                let offset = (&raw const bindings::__per_cpu_offset)
                    .cast::<u64>()
                    .add(cpu)
                    .read();
                (&raw mut raised_list as usize).wrapping_add(offset as usize)
                    as *mut core::ffi::c_void
            };
            // SAFETY: This is the exact resident per-CPU llist_head token.
            let physical = unsafe { per_cpu_ptr_to_phys(address) };
            if physical == 0 || physical >= IDENTITY_WINDOW_END {
                return Err(EIO);
            }
            params.put64(
                offset_of!(abi::IhkSmpBootParam, ikc_cpu_raised_list) + cpu * 8,
                physical,
            )?;
        }
        for (rank, cpu) in cpus.iter().enumerate() {
            let offset = cpu_offset + rank * size_of::<abi::IhkSmpBootParamCpu>();
            let node = nodes.binary_search(&cpu.numa_node).map_err(|_| EIO)?;
            for (field, value) in [
                (0, node as u32),
                (4, cpu.hardware_id),
                (8, cpu.linux_id),
                (12, 0),
            ] {
                params.put32(offset + field, value)?;
            }
        }
        for (rank, &node) in nodes.iter().enumerate() {
            params.put32(node_offset + rank * 8, 1)?;
            params.put32(node_offset + rank * 8 + 4, node)?;
            for (other_rank, &other) in nodes.iter().enumerate() {
                // SAFETY: Both bounded nodes come from retained CPU/page owners
                // under topology exclusion; Linux owns the distance table.
                let distance = unsafe { bindings::__node_distance(node as i32, other as i32) };
                if distance <= 0 {
                    return Err(EIO);
                }
                params.put32(
                    distance_offset + (rank * nodes.len() + other_rank) * 4,
                    distance as u32,
                )?;
            }
        }
        let mut dump_offset = 0;
        for (rank, range) in chunks.iter().enumerate() {
            let offset = chunk_offset + rank * size_of::<abi::IhkSmpBootParamMemoryChunk>();
            let node = nodes.binary_search(&range.numa_node()).map_err(|_| EIO)?;
            params.put64(offset, range.start())?;
            params.put64(offset + 8, range.end().map_err(|_| EIO)?)?;
            params.put32(offset + 16, node as u32)?;
            let pages = range.length() / 4096;
            let words = pages.div_ceil(64);
            dump.put64(dump_offset, range.start())?;
            dump.put64(dump_offset + 8, words)?;
            for word in 0..words {
                let bits = (pages - word * 64).min(64);
                dump.put64(
                    dump_offset + 16 + word as usize * 8,
                    if bits == 64 {
                        u64::MAX
                    } else {
                        (1_u64 << bits) - 1
                    },
                )?;
            }
            dump_offset += 16 + words as usize * 8;
        }
        self.write_image_range(direct_map, layout.startup(), 4096, None)?;
        let code = super::smp_boot_code::startup();
        self.write_image_range(direct_map, layout.startup(), code.len(), Some(code))?;
        for (offset, value) in [
            (16, root),
            (24, layout.stack()),
            (32, layout.kernel().start()),
            (40, trampoline.physical()),
            (48, entry),
        ] {
            self.write_image_range(
                direct_map,
                layout.startup() + offset,
                8,
                Some(&value.to_le_bytes()),
            )?;
        }
        for (offset, &byte) in super::smp_boot_code::trampoline().iter().enumerate() {
            trampoline.write_byte(offset, byte)?;
        }
        for (offset, value) in [
            (8, root),
            (16, layout.startup()),
            (24, layout.stack()),
            (32, params.physical()),
        ] {
            for (byte_offset, byte) in value.to_le_bytes().iter().copied().enumerate() {
                trampoline.write_byte(offset + byte_offset, byte)?;
            }
        }
        let header = [root, layout.startup(), layout.stack(), params.physical()];
        for (offset, &template) in super::smp_boot_code::trampoline().iter().enumerate() {
            let expected = if (8..40).contains(&offset) {
                header[(offset - 8) / 8].to_le_bytes()[(offset - 8) % 8]
            } else {
                template
            };
            if trampoline.read_byte(offset)? != expected {
                return Err(EIO);
            }
        }
        pr_info!("IHK-SMP: boot prepared os={} generation={} params={:x} bytes={} trampoline={:x} startup={:x} cpus={} numa={} chunks={} kmsg={:x}; CPUs not started\n",
            owner.slot(), owner.generation(), params.physical(), param_bytes, trampoline.physical(), layout.startup(), cpus.len(), nodes.len(), chunks.len(), kmsg);
        self.images[owner.slot() as usize].as_mut().ok_or(EIO)?.boot = Some(BootStorage {
            prepared: ManuallyDrop::new(PreparedBoot {
                params,
                _dump: dump,
                trampoline,
                irq,
                cpus,
                master: None,
                channels: Vec::new(),
            }),
            started: false,
        });
        Ok(())
    }

    fn start_boot(
        &mut self,
        owner: super::smp_resource::OsToken,
        topology: &BootTopology<'_>,
    ) -> Result {
        self.verify()?;
        self.require_unstarted(owner)?;
        let memory_map = &self.map;
        let image = self.images[owner.slot() as usize].as_mut().ok_or(EINVAL)?;
        let boot = image.boot.as_mut().ok_or(EINVAL)?;
        if boot.prepared.cpus.as_slice() != topology.cpus() {
            return Err(EIO);
        }
        let cpu = *topology.cpus().first().ok_or(EINVAL)?;
        let trampoline = boot.prepared.trampoline.physical();
        // Retain every owner BEFORE the first INIT/SIPI effect. No future
        // error, module teardown or metadata drop may release reachable RAM.
        boot.started = true;
        core::sync::atomic::fence(Ordering::SeqCst);
        // SAFETY: The exact assigned offline CPU and original Linux device
        // remain pinned under both hotplug guards. Its owned startup page,
        // image, tables, parameters, kmsg and callback code are fully prepared
        // and retained for all outcomes. This calls Linux's unchanged routine.
        let sent =
            unsafe { wakeup_secondary_cpu_via_init(cpu.hardware_id, trampoline, cpu.linux_id) };
        pr_info!("IHK-SMP: CPU start os={} generation={} linux_cpu={} apic={} result={}; resources retained\n", owner.slot(), owner.generation(), cpu.linux_id, cpu.hardware_id, sent);
        if sent != 0 {
            return Err(EIO);
        }
        let mut last = u64::MAX;
        for _ in 0..3000 {
            let status = boot
                .prepared
                .params
                .read64(offset_of!(abi::IhkSmpBootParam, status))?;
            if status != last {
                pr_info!("IHK-SMP: guest boot progress os={} generation={} status={} irq_events={}; IKC readiness pending\n", owner.slot(), owner.generation(), status, boot.prepared.irq.events());
                last = status;
            }
            // The existing guest reaches 2 before post_init/host IKC. Keep
            // this intermediate state distinct from full boot success.
            if status >= 2 {
                break;
            }
            // SAFETY: Sleepable ioctl context; topology/resource mutexes are
            // sleepable and keep this guest's exact owners stable while waiting.
            unsafe { bindings::msleep(10) };
        }
        pr_info!("IHK-SMP: boot incomplete os={} generation={} status={} receive={:x} send={:x}; host IKC integration pending, all resources retained\n",
            owner.slot(), owner.generation(), last,
            boot.prepared.params.read64(offset_of!(abi::IhkSmpBootParam, master_ikc_queue_receive))?,
            boot.prepared.params.read64(offset_of!(abi::IhkSmpBootParam, master_ikc_queue_send))?);
        if last == 2 {
            use super::ikc_master::{ExecutionContext, MasterRouter, RouteAction};
            core::sync::atomic::fence(Ordering::Acquire);
            let prepared = &mut *boot.prepared;
            let receive = prepared
                .params
                .read64(offset_of!(abi::IhkSmpBootParam, master_ikc_queue_receive))?;
            let send = prepared
                .params
                .read64(offset_of!(abi::IhkSmpBootParam, master_ikc_queue_send))?;
            let queue_bytes = (4 * prepared.cpus.len() * 56).div_ceil(4096) * 4096;
            let direct_map = unsafe { bindings::page_offset_base };
            let receive_pointer =
                checked_guest_queue(memory_map, owner, direct_map, receive, queue_bytes)?;
            let send_pointer =
                checked_guest_queue(memory_map, owner, direct_map, send, queue_bytes)?;
            if receive < send + queue_bytes as u64 && send < receive + queue_bytes as u64 {
                return Err(EINVAL);
            }
            // SAFETY: Complete disjoint queues belong to this permanently
            // retained generation; preparation required native boot revision 2.
            let master = unsafe {
                super::smp_ikc::BootMaster::new(owner, receive_pointer, send_pointer, queue_bytes)?
            };
            prepared.master = Some(Box::new(master, GFP_KERNEL)?);
            let master = prepared.master.as_ref().ok_or(EIO)?;
            // SAFETY: The stable Box is already inside the retained started
            // owner before the IRQ route can observe it.
            unsafe { prepared.irq.publish_master(master)? };
            master.send_initial_ack(cpu.linux_id)?;
            pr_info!("IHK-SMP: master INIT_ACK os={} generation={} target_cpu={} receive={:x} send={:x}; revision-2 replies enabled\n", owner.slot(), owner.generation(), cpu.linux_id, receive, send);
            let router = MasterRouter::new(super::smp_ikc::listeners());
            'service: for _ in 0..3000 {
                if master.error() != 0 {
                    return Err(EIO);
                }
                let notified = master.take_notification();
                // The shared ring itself retains pending packets. Always poll
                // after a bounded drain, even if one IRQ covered many packets.
                for _ in 0..16 {
                    let Some(packet) = master.next_packet()? else {
                        break;
                    };
                    let decision = router.route(&packet, ExecutionContext::Process);
                    match decision.action {
                        RouteAction::Accept(plan) => {
                            let offer = plan.offer();
                            pr_info!("IHK-SMP: guest CONNECT os={} generation={} irq_events={} packets={} port={} packet_size={} receive={:x} send={:x} cookie={:x} magic={} cpu={}; process listener notified={}\n", owner.slot(), owner.generation(), prepared.irq.events(), master.packets(), offer.port, offer.packet_size, offer.receive_queue, offer.send_queue, offer.remote_channel_cookie, offer.magic, offer.interrupt_cpu, notified);
                            let result = accept_control_channel(
                                memory_map,
                                owner,
                                &prepared.cpus,
                                &mut prepared.channels,
                                direct_map,
                                receive,
                                send,
                                queue_bytes,
                                offer,
                            )
                            .map_err(|error| error.to_errno());
                            let reply = plan
                                .connect_reply(result)
                                .map_err(super::smp_ikc::master_error)?;
                            master.send_packet(cpu.linux_id, &reply.packet())?;
                            pr_info!("IHK-SMP: CONNECT_REPLY os={} generation={} port={} reference={} errno={} receive={:x} cookie={}\n", owner.slot(), owner.generation(), offer.port, reply.reference, reply.parameters[0], reply.parameters[1], reply.parameters[3]);
                        }
                        RouteAction::SendConnectError(reply) => {
                            master.send_packet(cpu.linux_id, &reply.packet())?;
                        }
                        RouteAction::DeliverPacket { channel_cookie } => {
                            if !prepared.channels.iter().any(|entry| {
                                entry.channel.owner == owner
                                    && entry.channel.cookie == channel_cookie
                            }) {
                                return Err(EINVAL);
                            }
                        }
                        _ => {
                            pr_info!("IHK-SMP: unserviced master message os={} generation={} message={:x} reference={}; resources retained\n", owner.slot(), owner.generation(), packet.message, packet.reference);
                            break 'service;
                        }
                    }
                }
                for entry in prepared.channels.iter_mut() {
                    if let Some(packet) = entry.channel.next_packet()? {
                        // Queue publication synchronizes the guest's preceding
                        // write_cpu update. Validate the source before dispatch.
                        if entry.pages.read64(56)? as u32 != entry.channel.guest_cpu {
                            return Err(EIO);
                        }
                        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
                        let reference = i32::from_le_bytes(packet[24..28].try_into().unwrap());
                        let argument = u64::from_le_bytes(packet[40..48].try_into().unwrap());
                        pr_info!("IHK-SMP: regular request os={} generation={} port={} cookie={} packets={} message={:x} reference={} argument={:x} irq_events={}; host service pending, resources retained\n", owner.slot(), owner.generation(), entry.channel.port, entry.channel.cookie, entry.channel.received, message, reference, argument, prepared.irq.events());
                        break 'service;
                    }
                }
                // SAFETY: Sleepable BOOT retains all CPU, memory, channel and
                // module owners. IRQ callbacks take none of these mutexes.
                unsafe { bindings::msleep(10) };
            }
        }
        // No success is returned merely for AP entry or architecture readiness.
        // Listener replies alone are insufficient: host services and runtime dispatch remain open.
        Err(kernel::error::to_result(-110).err().unwrap_or(EIO))
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
    context.require_unstarted(owner)?;
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
    context.images[owner.slot() as usize] = None;
    context.arguments[owner.slot() as usize] = None;
    Ok(())
}

/// Preserve the existing 1024-byte host read and 255-byte SMP argument payload.
pub(super) fn set_kernel_arguments(
    owner: super::smp_resource::OsToken,
    argument: usize,
) -> Result<isize> {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: IHK's exact OS/module lease retains this mutex for the callback.
    let mut context = unsafe { &*published }.lock();
    context.verify()?;
    context.require_unstarted(owner)?;
    let supplied = super::smp_loader::read_user_string::<1024>(argument, false)?;
    let mut bytes = [0_u8; 256];
    bytes[..255].copy_from_slice(&supplied[..255]);
    if let Some(image) = context.images[owner.slot() as usize].as_mut() {
        image.boot.take();
    }
    context.arguments[owner.slot() as usize] = Some((owner, bytes));
    Ok(0)
}

/// Invalidate any prior successful load before opening a replacement file.
pub(super) fn invalidate_os_image(owner: super::smp_resource::OsToken) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: IHK pins this module and holds its OS operation mutex. This
    // standalone memory lock is released before the later CPU -> memory pair.
    let mut context = unsafe { &*published }.lock();
    context.invalidate_image(owner)
}

/// Called under the CPU lock after checking an assigned, offline CPU exists.
pub(super) fn load_os_image(owner: super::smp_resource::OsToken, image: &[u8]) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: IHK's operation/module owners and the caller's CPU lock retain
    // this published controller. Loading never starts a CPU or exposes a map.
    let mut context = unsafe { &*published }.lock();
    context.load_image(owner, image)
}

/// Called under CPU -> memory lock order before changing an OS CPU assignment.
pub(super) fn retire_os_boot(owner: super::smp_resource::OsToken) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: The synchronous IHK backend call retains its module and lease.
    let mut context = unsafe { &*published }.lock();
    context.require_unstarted(owner)?;
    if let Some(image) = context.images[owner.slot() as usize].as_mut() {
        image.boot.take();
    }
    Ok(())
}

pub(super) fn prepare_os_boot(
    owner: super::smp_resource::OsToken,
    topology: &BootTopology<'_>,
    kmsg: u64,
    kmsg_bytes: u64,
    trampoline: u64,
) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: IHK's exact-generation lease, operation lock and module pin plus
    // the caller's CPU topology guards remain live throughout preparation.
    let mut context = unsafe { &*published }.lock();
    context.prepare_boot(owner, topology, kmsg, kmsg_bytes, trampoline)
}

pub(super) fn start_os_boot(
    owner: super::smp_resource::OsToken,
    topology: &BootTopology<'_>,
) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: Same IHK and topology owners as prepare, after Booting publication.
    // The native storage makes the lifetime irreversible before INIT/SIPI.
    let mut context = unsafe { &*published }.lock();
    context.start_boot(owner, topology)
}

const _: () = {
    assert!(size_of::<abi::IhkSmpBootParam>() == 7616);
    assert!(offset_of!(abi::IhkSmpBootParam, hardware_event_map) == 6656);
    assert!(size_of::<abi::IhkSmpBootParamCpu>() == 16);
    assert!(size_of::<abi::IhkSmpBootParamNumaNode>() == 8);
    assert!(size_of::<abi::IhkSmpBootParamMemoryChunk>() == 24);
    assert!(size_of::<abi::IhkDumpPagePrefix>() == 16);
};
