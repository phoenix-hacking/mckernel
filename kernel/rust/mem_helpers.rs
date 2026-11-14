use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of};
use core::marker::{PhantomData, PhantomPinned};
use core::pin::Pin;
use core::ptr::{null_mut, write_bytes, write_volatile};
use core::sync::atomic::{AtomicI32, AtomicI64, AtomicPtr, AtomicU64, Ordering};

use crate::abi::{
    AbiListHead, AddressSpace, CInt, CLong, CULong, CpuLocalVar, IhkAtomic, IhkAtomic64,
    IhkCpuInfo, IhkMcPtAttribute, IhkSpinlock, KmallocCacheHeader, KmallocHeader, McsLockNode, Memobj, OffT, Process,
    ProcessVm, RusagePercpu, SizeT, TlbFlushEntry, VmRange, CPU_SET_WORDS, IHK_MAX_NUM_CPUS,
    IHK_MAX_NUM_NUMA_NODES, IHK_MAX_NUM_PGSIZES, PROCESS_HASH_SIZE,
};
use crate::llist::{LListHead, LListNode};
use crate::rbtree::{rb_first_safe, rb_next_safe, RbNode, RbRoot};
use crate::string::{strcmp, strcpy, strlen, strstr};

unsafe extern "C" {
    // Existing public providers; opaque VM/PT pointers preserve the C pointer ABI.
    fn ihk_mc_pt_lookup_pte(
        pt: *mut c_void, virt: *mut c_void, pgshift: CInt,
        basep: *mut *mut c_void, sizep: *mut usize, p2alignp: *mut CInt,
    ) -> *mut CULong;
    fn page_fault_process_vm(vm: *mut c_void, virt: *mut c_void, reason: CULong) -> CInt;
    // Same public Rust/reviewed-assembly providers used by the original C adapters.
    fn rdtsc() -> CULong;
    fn flush_tlb_single(addr: CULong);
    fn flush_tlb();
    fn cpu_pause();
    // C owns the complete vector array; this names its first element only.
    // No array extent is invented: the immutable header geometry supplies it.
    #[link_name = "tlb_flush_vector"]
    static mut MEM_TLB_FLUSH_VECTOR_FIRST: TlbFlushEntry;
    static mem_remote_tlb_geometry: [CInt; 3];

    #[link_name = "rusage"]
    static mut RUSAGE: RusageGlobal;

    fn early_alloc_pages(nr_pages: CInt) -> *mut c_void;
    fn early_alloc_invalidate();
    fn ihk_mc_get_nr_memory_chunks() -> CInt;
    fn ihk_mc_get_memory_chunk(
        id: CInt,
        start: *mut CULong,
        end: *mut CULong,
        numa_id: *mut CInt,
    ) -> CInt;
    fn ihk_mc_get_nr_numa_nodes() -> CInt;
    fn ihk_get_kargs() -> *mut i8;
    fn ihk_mc_get_processor_id() -> CInt;
    fn ihk_mc_get_vector(type_: CInt) -> CInt;
    fn ihk_mc_interrupt_cpu(cpu: CInt, vector: CInt) -> CInt;
    fn visit_pte_range_safe(
        pt: *mut c_void,
        start: *mut c_void,
        end: *mut c_void,
        pgshift: CInt,
        p2align: CInt,
        visitor: Option<MemPteVisitorFn>,
        arg: *mut c_void,
    ) -> CInt;
    fn get_this_cpu_local_var() -> *mut CpuLocalVar;
    fn kprintf(format: *const i8, ...) -> CInt;
    fn eventfd(type_: CInt);

    static mut sysctl_overcommit_memory: CInt;
    #[link_name = "memdebug"]
    static mut MEMDEBUG: *mut i8;
    #[link_name = "pagealloc_track_hash"]
    static mut PAGEALLOC_TRACK_HASH: [AbiListHead; PAGEALLOC_TRACK_HASH_SIZE];
    #[link_name = "pagealloc_track_hash_locks"]
    static mut PAGEALLOC_TRACK_HASH_LOCKS: [IhkSpinlock; PAGEALLOC_TRACK_HASH_SIZE];
    #[link_name = "pagealloc_addr_hash"]
    static mut PAGEALLOC_ADDR_HASH: [AbiListHead; PAGEALLOC_TRACK_HASH_SIZE];
    #[link_name = "pagealloc_addr_hash_locks"]
    static mut PAGEALLOC_ADDR_HASH_LOCKS: [IhkSpinlock; PAGEALLOC_TRACK_HASH_SIZE];
    #[link_name = "pagealloc_track_initialized"]
    static mut PAGEALLOC_TRACK_INITIALIZED: CInt;
    #[link_name = "pagealloc_runcount"]
    static mut PAGEALLOC_RUNCOUNT: CInt;
    #[link_name = "kmalloc_track_hash"]
    static mut KMALLOC_TRACK_HASH: [AbiListHead; KMALLOC_TRACK_HASH_SIZE];
    #[link_name = "kmalloc_track_hash_locks"]
    static mut KMALLOC_TRACK_HASH_LOCKS: [IhkSpinlock; KMALLOC_TRACK_HASH_SIZE];
    #[link_name = "kmalloc_addr_hash"]
    static mut KMALLOC_ADDR_HASH: [AbiListHead; KMALLOC_TRACK_HASH_SIZE];
    #[link_name = "kmalloc_addr_hash_locks"]
    static mut KMALLOC_ADDR_HASH_LOCKS: [IhkSpinlock; KMALLOC_TRACK_HASH_SIZE];
    #[link_name = "kmalloc_runcount"]
    static mut KMALLOC_RUNCOUNT: CInt;
}

const KMALLOC_FRONT_MAGIC: u32 = 0x5c5c5c5c;
const KMALLOC_END_MAGIC: u32 = 0x6d6d6d6d;
const KMALLOC_MIN_SIZE: CInt = 1 << 5;
const KMALLOC_MIN_MASK: CInt = KMALLOC_MIN_SIZE - 1;
const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const ENOENT: CInt = 2;
const PAGE_SHIFT: CULong = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const PAGE_MASK: CULong = !(PAGE_SIZE - 1);
const OVERCOMMIT_ALWAYS: CInt = 1;
const RUSAGE_OOM_MARGIN: CULong = 8 * 1024 * 1024;
const IHK_OS_EVENTFD_TYPE_OOM: CInt = 0;
const PAGE_P2ALIGN: CInt = 0;
const IHK_MC_PG_KERNEL: CInt = 0;
const IHK_MC_PG_USER: CInt = 1;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const IHK_MC_AP_USER: CULong = 0x001000;
const IHK_MM_WRAPPER_FILE: &[u8] = b"lib/include/ihk/mm.h\0";
const KMALLOC_WRAPPER_FILE: &[u8] = b"kernel/include/kmalloc.h\0";
const KMALLOC_OOM_FMT: &[u8] = b"kmalloc: out of memory %s:%d no_preempt=%d\n\0";
const MPOL_DEFAULT: CInt = 0;
const MPOL_PREFERRED: CInt = 1;
const MPOL_BIND: CInt = 2;
const MPOL_INTERLEAVE: CInt = 3;
const VR_RESERVED: CULong = 0x2;
const VR_IO_NOCACHE: CULong = 0x100;
const VR_REMOTE: CULong = 0x200;
const MF_REG_FILE: CULong = 0x1000;
const MF_DEV_FILE: CULong = 0x2000;
const MF_PREMAP: CULong = 0x8000;
const MF_XPMEM: CULong = 0x10000;
const MF_ZEROOBJ: CULong = 0x20000;
const MF_SHM: CULong = 0x40000;
const MF_HUGETLBFS: CULong = 0x100000;
const PM_NONE: u8 = 0x00;
const PM_PENDING_FREE: u8 = 0x01;
const LIST_POISON1: usize = 0x0010_0129;
const LIST_POISON2: usize = 0x0020_0229;
const MEM_ALLOC_LOG_EXPLICIT_OK: CInt = 1;
const MEM_ALLOC_LOG_EXPLICIT_MISS: CInt = 2;
const MEM_ALLOC_LOG_POLICY_OK: CInt = 3;
const MEM_ALLOC_LOG_POLICY_MISS: CInt = 4;
const MEM_ALLOC_LOG_DISTANCE_OK: CInt = 5;
const MEM_ALLOC_LOG_DISTANCE_FIRST_MISS: CInt = 6;
const MEM_ALLOC_LOG_OOM: CInt = 7;
const MEM_VIRT_ADDR_NONE: CULong = CULong::MAX;
const MEM_INIT_LOG_ANON_ON_DEMAND: CInt = 1;
const MEM_INIT_LOG_XPMEM_PAGE_IN_REMOTE: CInt = 2;
const MEM_INIT_LOG_HUGETLBFS_ON_DEMAND: CInt = 3;
const MEM_NUMA_INIT_LOG_CHUNK: CInt = 1;
const MEM_NUMA_INIT_LOG_NODE: CInt = 2;
const IHK_GV_QUERY_FREE_MEM: CInt = 2;
const IHK_DUMP_PAGE_SET_INCOMPLETE: u32 = 0;
const IHK_DUMP_PAGE_SET_COMPLETED: u32 = 1;
const DUMP_LEVEL_USER_UNUSED_EXCLUDE: CInt = 24;
const PTATTR_ACTIVE: CULong = 0x01;
const PTATTR_USER: CULong = 0x04;
const PT_PHYSMASK: CULong = ((1u64 << 52) - 1) & !(PAGE_SIZE - 1);
const PF_USER: CULong = 1 << 2;
const PF_POPULATE: CULong = 1 << 30;
const MEM_DUMP_WARN_FREE: CInt = 0;
const MEM_DUMP_WARN_USER: CInt = 1;
const IHK_OS_PGSIZE_4KB: CInt = 0;
const IHK_OS_PGSIZE_2MB: CInt = 2;
const IHK_OS_PGSIZE_1GB: CInt = 4;
const RUSAGE_CHECK_OOM_NAME: &[u8] = b"rusage_check_oom\0";
const RUSAGE_CHECK_OOM_FMT: &[u8] = b"%s: memory used:%ld available:%ld\n\0";
const RUSAGE_MEMORY_STAT_ADD_NAME: &[u8] = b"rusage_memory_stat_add\0";
const RUSAGE_MEMORY_STAT_ADD_WITH_PAGE_NAME: &[u8] = b"rusage_memory_stat_add_with_page\0";
const RUSAGE_MEMORY_STAT_ADD_WARNING_FMT: &[u8] = b"%s: WARNING !page,phys=%lx\n\0";

#[derive(Clone, Copy, PartialEq, Eq)]
enum PendingFreeBatchState {
    Vacant,
    Retained,
    Drained,
}

/// Inclusive/exclusive physical authority supplied by the future inventory
/// producer.  This is deliberately private until that producer can bind the
/// range to the allocator and Mirror ownership records.
#[derive(Clone, Copy)]
struct PendingPhysicalBounds {
    start: CULong,
    end: CULong,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct PendingFreeCallbackArgs {
    phys: CULong,
    npages: CInt,
}

/// An exclusive, caller-retained inventory of the exact descriptors which may
/// be transferred.  Both arrays are preallocated by the caller: validation,
/// reanchoring, and drain never allocate, log, or free.
///
/// # Safety
/// The caller must keep every descriptor pointer live, distinct, physically
/// authoritative within `bounds`, and exclusively mutation-owned until the
/// explicit drain completes.  It must also keep both supplied arrays live and
/// exclusively available, keep the source ring stable, and prevent callback
/// re-entry.  These obligations are intentionally not inferred from raw list
/// links; a later production producer must establish them from allocator
/// ownership, quarantine, backing-reference, VA, and TLB-acknowledgement
/// state before this private helper is wired to a caller.
struct PendingInventoryLease {
    descriptors: *mut *mut MemPage,
    descriptor_len: usize,
    callback_args: *mut PendingFreeCallbackArgs,
    callback_len: usize,
    bounds: PendingPhysicalBounds,
    _pin: PhantomPinned,
    _not_send_or_sync: PhantomData<*mut ()>,
}

impl PendingInventoryLease {
    /// Creates only the private lease representation.  It does not validate
    /// any descriptor or mutate either input; `validate` is the sole admission
    /// point and reports a malformed inventory before transfer.
    unsafe fn new(
        descriptors: &mut [*mut MemPage],
        callback_args: &mut [PendingFreeCallbackArgs],
        bounds: PendingPhysicalBounds,
    ) -> Self {
        Self {
            descriptors: descriptors.as_mut_ptr(),
            descriptor_len: descriptors.len(),
            callback_args: callback_args.as_mut_ptr(),
            callback_len: callback_args.len(),
            bounds,
            _pin: PhantomPinned,
            _not_send_or_sync: PhantomData,
        }
    }

    unsafe fn descriptor(&self, index: usize) -> *mut MemPage {
        *self.descriptors.add(index)
    }

    unsafe fn descriptor_node(&self, index: usize) -> *mut AbiListHead {
        &raw mut (*self.descriptor(index)).list
    }

    unsafe fn descriptor_index(&self, node: *mut AbiListHead) -> Option<usize> {
        for index in 0..self.descriptor_len {
            if self.descriptor_node(index) == node {
                return Some(index);
            }
        }
        None
    }
}

/// A consumed admission token.  It exists only after the exact independently
/// supplied inventory, rather than a discovery walk over suspect links, has
/// validated the source ring.
struct ValidatedPendingInventory {
    lease: PendingInventoryLease,
    source: *mut AbiListHead,
    count: usize,
}

/// Pinned transaction destination for pending-page ownership transfer.
/// It is deliberately !Unpin, !Send and !Sync and never frees implicitly.
struct PendingFreeBatch {
    head: AbiListHead,
    state: PendingFreeBatchState,
    source: *mut AbiListHead,
    lease: Option<PendingInventoryLease>,
    _pin: PhantomPinned,
    _owner: PhantomData<*mut ()>,
}

impl PendingFreeBatch {
    const fn new() -> Self {
        Self {
            head: AbiListHead { next: null_mut(), prev: null_mut() },
            state: PendingFreeBatchState::Vacant,
            source: null_mut(),
            lease: None,
            _pin: PhantomPinned,
            _owner: PhantomData,
        }
    }
}

// There is intentionally no `Drop` implementation for the lease, admission
// token, or batch.  Ownership leaves this helper only through explicit drain.

unsafe fn validate_pending_inventory_metadata(
    lease: &PendingInventoryLease,
) -> Result<(), CInt> {
    if lease.bounds.start >= lease.bounds.end
        || lease.bounds.start & (PAGE_SIZE - 1) != 0
        || lease.bounds.end & (PAGE_SIZE - 1) != 0
        // The public finish return/count contract is CInt.  Reject before any
        // descriptor-pointer traversal so a hostile oversized lease cannot
        // turn bounded validation into an unrepresentable drain result.
        || lease.descriptor_len > CInt::MAX as usize
        || lease.callback_len < lease.descriptor_len
    {
        return Err(-EINVAL);
    }

    for index in 0..lease.descriptor_len {
        let page = lease.descriptor(index);
        if page.is_null() {
            return Err(-EINVAL);
        }
        for previous in 0..index {
            if lease.descriptor(previous) == page {
                return Err(-EINVAL);
            }
        }
        if (*page).mode != PM_PENDING_FREE
            || (*page).offset <= 0
            || (*page).offset > CInt::MAX as OffT
            || (*page).phys & (PAGE_SIZE - 1) != 0
        {
            return Err(-EINVAL);
        }
        let bytes = match ((*page).offset as CULong).checked_mul(PAGE_SIZE) {
            Some(bytes) => bytes,
            None => return Err(-EINVAL),
        };
        let end = match (*page).phys.checked_add(bytes) {
            Some(end) => end,
            None => return Err(-EINVAL),
        };
        if (*page).phys < lease.bounds.start || end > lease.bounds.end {
            return Err(-EINVAL);
        }
        for previous in 0..index {
            let other = lease.descriptor(previous);
            let other_bytes = match ((*other).offset as CULong).checked_mul(PAGE_SIZE) {
                Some(bytes) => bytes,
                None => return Err(-EINVAL),
            };
            let other_end = match (*other).phys.checked_add(other_bytes) {
                Some(end) => end,
                None => return Err(-EINVAL),
            };
            if (*page).phys < other_end && (*other).phys < end {
                return Err(-EINVAL);
            }
        }
    }
    Ok(())
}

/// Checks a ring exclusively through the independently supplied inventory.
/// Every dereferenced non-sentinel node has first been matched to one of the
/// inventory entries; links can therefore reject membership, cycles, and
/// reciprocity faults without discovering liveness from suspect raw pointers.
unsafe fn validate_pending_inventory_ring(
    head: *mut AbiListHead,
    lease: &PendingInventoryLease,
) -> Result<usize, CInt> {
    if head.is_null() || (*head).next.is_null() || (*head).prev.is_null() {
        return Err(-EINVAL);
    }
    let count = lease.descriptor_len;
    if count == 0 {
        return if (*head).next == head && (*head).prev == head {
            Ok(0)
        } else {
            Err(-EINVAL)
        };
    }
    if (*head).next == head || (*head).prev == head {
        return Err(-EINVAL);
    }

    let mut node = (*head).next;
    let mut previous = head;
    for _ in 0..count {
        if lease.descriptor_index(node).is_none()
            || (*node).prev != previous
            || (*node).next.is_null()
        {
            return Err(-EINVAL);
        }
        previous = node;
        node = (*node).next;
    }
    if node != head || (*head).prev != previous || (*previous).next != head {
        return Err(-EINVAL);
    }

    // Exact cardinality alone rejects a foreign node, but does not distinguish
    // duplicate membership from a missing supplied descriptor.  Prove every
    // independently retained descriptor occurs exactly once in the bounded
    // ring before permitting a mutation.
    for index in 0..count {
        let expected = lease.descriptor_node(index);
        let mut occurrences = 0usize;
        let mut candidate = (*head).next;
        for _ in 0..count {
            if candidate == expected {
                occurrences += 1;
            }
            candidate = (*candidate).next;
        }
        if occurrences != 1 {
            return Err(-EINVAL);
        }
    }
    Ok(count)
}

unsafe fn validate_pending_inventory(
    source: *mut AbiListHead,
    lease: PendingInventoryLease,
) -> Result<ValidatedPendingInventory, CInt> {
    // This admission phase intentionally writes nothing: any error leaves the
    // source, supplied descriptors, destination candidates, and callback
    // storage untouched.  The consumed lease has no Drop action.
    validate_pending_inventory_metadata(&lease)?;
    let count = validate_pending_inventory_ring(source, &lease)?;
    Ok(ValidatedPendingInventory { lease, source, count })
}

impl ValidatedPendingInventory {
    /// Checks a destination before consuming the token.  An invalid destination
    /// returns the unchanged token so its owner can choose another pinned batch;
    /// the successful branch delegates to the infallible reanchor below.
    unsafe fn try_reanchor_into(
        self,
        mut destination: Pin<&mut PendingFreeBatch>,
    ) -> Result<(), Self> {
        let dest = destination.as_mut().get_unchecked_mut();
        if self.source == &raw mut dest.head
            || dest.state != PendingFreeBatchState::Vacant
            || dest.lease.is_some()
            || !dest.head.next.is_null()
            || !dest.head.prev.is_null()
        {
            return Err(self);
        }
        self.reanchor_into(destination);
        Ok(())
    }

    /// Reanchors a fully validated token without an error path.
    ///
    /// # Safety
    /// `destination` must be the exclusive, pinned, still-vacant batch whose
    /// head is distinct from `source`; no actor may have changed either after
    /// validation.  These are transaction-owner obligations, so a valid token
    /// cannot be partially detached by a later fallible destination check.
    unsafe fn reanchor_into(self, mut destination: Pin<&mut PendingFreeBatch>) {
        let dest = destination.as_mut().get_unchecked_mut();
        let dest_head = &raw mut dest.head;
        debug_assert!(dest.state == PendingFreeBatchState::Vacant);
        debug_assert!(dest.head.next.is_null() && dest.head.prev.is_null());
        debug_assert!(dest.lease.is_none());
        debug_assert!(self.source != dest_head);

        if self.count == 0 {
            init_list_head(dest_head);
        } else {
            let first = (*self.source).next;
            let last = (*self.source).prev;
            init_list_head(dest_head);
            (*dest_head).next = first;
            (*dest_head).prev = last;
            (*first).prev = dest_head;
            (*last).next = dest_head;
        }
        (*self.source).next = null_mut();
        (*self.source).prev = null_mut();
        dest.source = self.source;
        dest.lease = Some(self.lease);
        dest.state = PendingFreeBatchState::Retained;
    }
}

unsafe fn drain_validated_pending_inventory(
    mut batch: Pin<&mut PendingFreeBatch>,
    free_fn: Option<MemPendingFreeFn>,
) -> CInt {
    let Some(free_fn) = free_fn else { return -EINVAL; };
    let b = batch.as_mut().get_unchecked_mut();
    if b.state != PendingFreeBatchState::Retained || b.source.is_null() {
        return -EINVAL;
    }
    let Some(lease) = b.lease.as_mut() else { return -EINVAL; };

    // All fallible checks, including the callback capacity and the complete
    // retained topology/metadata, happen before page state or any link moves.
    let count = match validate_pending_inventory_metadata(lease)
        .and_then(|_| validate_pending_inventory_ring(&raw mut b.head, lease))
    {
        Ok(count) => count,
        Err(_) => return -EINVAL,
    };
    let mut node = b.head.next;
    for index in 0..count {
        let page = page_from_list(node);
        *lease.callback_args.add(index) = PendingFreeCallbackArgs {
            phys: (*page).phys,
            npages: (*page).offset as CInt,
        };
        node = (*node).next;
    }

    // Make all descriptor/list mutations before the first callback.  Callback
    // delivery below reads only the pre-captured argument array, never a
    // descriptor which an earlier allocator callback may have released.
    node = b.head.next;
    for _ in 0..count {
        let next = (*node).next;
        let page = page_from_list(node);
        (*page).mode = PM_NONE;
        list_del_poison(node);
        node = next;
    }
    b.head.next = null_mut();
    b.head.prev = null_mut();
    b.source = null_mut();
    b.state = PendingFreeBatchState::Drained;
    for index in 0..count {
        let args = *lease.callback_args.add(index);
        free_fn(args.phys, args.npages, IHK_MC_PG_USER);
    }
    count as CInt
}

unsafe fn validate_pending_head(head: *mut AbiListHead) -> Result<bool, CInt> {
    if head.is_null() || (*head).next.is_null() || (*head).prev.is_null() {
        return Err(-EINVAL);
    }
    if (*head).next == head || (*head).prev == head {
        if (*head).next != head || (*head).prev != head {
            return Err(-EINVAL);
        }
        return Ok(false);
    }
    if (*(*head).next).prev != head || (*(*head).prev).next != head {
        return Err(-EINVAL);
    }

    // Validate the complete ring before changing either list.  Floyd's
    // traversal detects a foreign cycle without imposing a node-count cap.
    let mut slow = (*head).next;
    let mut fast = (*head).next;
    loop {
        if slow == head {
            break;
        }
        if slow.is_null()
            || (*slow).next.is_null()
            || (*slow).prev.is_null()
            || (*(*slow).next).prev != slow
            || (*(*slow).prev).next != slow
        {
            return Err(-EINVAL);
        }
        let page = page_from_list(slow);
        if page.is_null() || (*page).mode != PM_PENDING_FREE {
            return Err(-EINVAL);
        }
        slow = (*slow).next;

        if fast == head {
            continue;
        }
        if fast.is_null() || (*fast).next.is_null() {
            return Err(-EINVAL);
        }
        fast = (*fast).next;
        if fast == head {
            continue;
        }
        if (*fast).next.is_null() {
            return Err(-EINVAL);
        }
        fast = (*fast).next;
        if fast == slow && slow != head {
            return Err(-EINVAL);
        }
    }
    Ok(true)
}

unsafe fn detach_pending_free_batch(
    source: *mut AbiListHead,
    mut destination: Pin<&mut PendingFreeBatch>,
) -> CInt {
    // Safety obligations: the caller owns an exclusive, CPU-local source
    // ring and keeps every live descriptor stable; no producer may edit the
    // transfer or retained descriptors, and no callback may re-enter while
    // this transaction is detached. `destination` must remain at this pinned
    // address until drain (or explicit recovery). Once the source head has
    // been reset, a later independently owned capture of that source is
    // permitted while this older pinned batch remains retained.
    let dest = destination.as_mut().get_unchecked_mut();
    let dest_head = &raw mut dest.head;
    if source.is_null()
        || source == dest_head
        || dest.state != PendingFreeBatchState::Vacant
        || dest.lease.is_some()
        || !(dest.head.next.is_null() && dest.head.prev.is_null())
    {
        return -EINVAL;
    }
    let nonempty = match validate_pending_head(source) {
        Ok(nonempty) => nonempty,
        Err(_) => return -EINVAL,
    };
    if nonempty {
        let first = (*source).next;
        let last = (*source).prev;
        init_list_head(dest_head);
        (*dest_head).next = first;
        (*dest_head).prev = last;
        (*first).prev = dest_head;
        (*last).next = dest_head;
        (*source).next = null_mut();
        (*source).prev = null_mut();
    } else {
        init_list_head(dest_head);
        (*source).next = null_mut();
        (*source).prev = null_mut();
    }
    dest.source = source;
    dest.state = PendingFreeBatchState::Retained;
    0
}

unsafe fn drain_pending_free_batch(
    source: *mut AbiListHead,
    mut batch: Pin<&mut PendingFreeBatch>,
    free_fn: Option<MemPendingFreeFn>,
) -> CInt {
    // Safety obligations: `source` must be the exact source captured by
    // detach, the pinned transaction must outlive this call, and `free_fn`
    // must not mutate either list or re-enter detach/drain. The caller owns
    // the exclusive CPU/descriptor lease for the whole operation.
    let Some(free_fn) = free_fn else { return -EINVAL; };
    let b = batch.as_mut().get_unchecked_mut();
    if b.state != PendingFreeBatchState::Retained
        || b.source != source
        || b.lease.is_some()
        || validate_pending_head(&raw mut b.head).is_err()
    {
        return -EINVAL;
    }
    let mut node = b.head.next;
    let mut count = 0;
    while node != &raw mut b.head {
        let next = (*node).next;
        let page = page_from_list(node);
        (*page).mode = PM_NONE;
        list_del_poison(node);
        free_fn((*page).phys, (*page).offset as CInt, IHK_MC_PG_USER);
        count += 1;
        node = next;
    }
    b.head.next = null_mut();
    b.head.prev = null_mut();
    b.source = null_mut();
    b.state = PendingFreeBatchState::Drained;
    count
}

#[no_mangle]
pub extern "C" fn round_up(x: CULong, y: CULong) -> CULong {
    (x.wrapping_sub(1) | y.wrapping_sub(1)).wrapping_add(1)
}

#[no_mangle]
pub extern "C" fn round_down(x: CULong, y: CULong) -> CULong {
    x & !y.wrapping_sub(1)
}

type MemPaAllocPageFn = unsafe extern "C" fn(CInt, CInt, CULong, CInt, CInt, CULong) -> *mut c_void;
type MemPaFreePageFn = unsafe extern "C" fn(*mut c_void, CInt, CInt);
type MemEarlyAllocPagesFn = unsafe extern "C" fn(CInt) -> *mut c_void;
type MemPendingWarnFn = unsafe extern "C" fn(CULong);
type MemPendingFreeFn = unsafe extern "C" fn(CULong, CInt, CInt);
type MemBeginFreePagesPendingFn = unsafe extern "C" fn(*mut AbiListHead) -> CInt;
type MemFinishFreePagesPendingFn =
    unsafe extern "C" fn(*mut AbiListHead, Option<MemPendingFreeFn>) -> CInt;
type MemReserveLogFn = unsafe extern "C" fn(CULong, CULong, CULong);
type MemReserveRangeFn = unsafe extern "C" fn(*mut c_void, CULong, CULong);
type MemReservePagesBodyFn = unsafe extern "C" fn(
    *mut c_void,
    CULong,
    CULong,
    CULong,
    CULong,
    Option<MemReserveLogFn>,
    Option<MemReserveRangeFn>,
) -> CInt;
type MemGetNrMemoryChunksFn = unsafe extern "C" fn() -> CInt;
type MemGetMemoryChunkFn = unsafe extern "C" fn(CInt, *mut CULong, *mut CULong, *mut CInt) -> CInt;
type MemVirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type MemPendingPagesFn = unsafe extern "C" fn() -> *mut AbiListHead;
type MemGetNumaNodeFn = unsafe extern "C" fn(CInt) -> *mut c_void;
type MemNumaFreeFn = unsafe extern "C" fn(*mut c_void, CULong, CInt);
type MemRusageSubFn = unsafe extern "C" fn(CInt, CInt, CInt);
type MemTryAllocNodeFn = unsafe extern "C" fn(CInt, CInt, CInt, CInt, *mut CInt) -> CULong;
type MemDistanceIdFn = unsafe extern "C" fn(CInt, CInt) -> CInt;
type MemMaskTestFn = unsafe extern "C" fn(CInt, *mut CULong) -> CInt;
type MemInterleaveNextFn = unsafe extern "C" fn(CInt, *mut CULong) -> CInt;
type MemRusageAddFn = unsafe extern "C" fn(CInt, CInt, CInt);
type MemPhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type MemAllocLogFn = unsafe extern "C" fn(CInt, CInt, CInt, CInt);
type MemCurrentVmFn = unsafe extern "C" fn() -> *mut c_void;
type MemRangePolicySearchFn = unsafe extern "C" fn(*mut c_void, CULong) -> *mut c_void;
type MemLookupMemoryRangeFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> *mut c_void;
type MemRangeIsShmFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type MemPolicyFieldsFn =
    unsafe extern "C" fn(*mut c_void, *mut CInt, *mut *mut CULong, *mut *mut CInt);
type MemMckernelAllocPolicyFn = unsafe extern "C" fn(
    CInt,
    CInt,
    CULong,
    CInt,
    CInt,
    CInt,
    CInt,
    CInt,
    CInt,
    *mut CULong,
    *mut CInt,
) -> *mut c_void;
type MemPhysToPageFn = unsafe extern "C" fn(CULong) -> *mut MemPage;
type MemFreeInAllocatorFn = unsafe extern "C" fn(*mut c_void, CInt, CInt);
type MemMckernelFreePagesBodyFn = unsafe extern "C" fn(
    *mut c_void,
    CInt,
    CInt,
    *mut AbiListHead,
    Option<MemVirtToPhysFn>,
    Option<MemPhysToPageFn>,
    Option<MemFreeInAllocatorFn>,
    Option<MemPendingWarnFn>,
) -> CInt;
type MemQueryFreeNodePagesFn = unsafe extern "C" fn(CInt) -> CInt;
type MemQueryFreeLogFn = unsafe extern "C" fn(CInt);
type MemQueryPageHashCountFn = unsafe extern "C" fn() -> CInt;
type MemQuerySboxWriteFn = unsafe extern "C" fn(CInt, u32);
type MemGetNrNumaNodesFn = unsafe extern "C" fn() -> CInt;
type MemVoidFn = unsafe extern "C" fn();
type MemSetPageAllocatorFn = unsafe extern "C" fn(*mut IhkMcPaOps);
type MemSetPageFaultHandlerFn = unsafe extern "C" fn(CULong);
type MemGetVectorFn = unsafe extern "C" fn(CInt) -> CInt;
type MemRegisterInterruptHandlerFn = unsafe extern "C" fn(CInt, CULong) -> CInt;
type MemFindCommandLineFn = unsafe extern "C" fn(*mut i8) -> *mut i8;
type MemInitLogFn = unsafe extern "C" fn(CInt);
type MemNumaDistanceAllocFn = unsafe extern "C" fn(CInt, CULong) -> *mut MemNodeDistance;
type MemNumaDistanceFn = unsafe extern "C" fn(CInt, CInt) -> CInt;
type MemNumaDistanceAllocFailLogFn = unsafe extern "C" fn(CInt);
type MemNumaDistanceLogFn = unsafe extern "C" fn(CInt, *mut MemNodeDistance, CInt);
type MemGetNumaNodeInfoFn = unsafe extern "C" fn(CInt, *mut CInt, *mut CInt) -> CInt;
type MemNumaNodeInitFn = unsafe extern "C" fn(*mut MemNumaNode, CInt);
type MemNumaAddFreePagesFn = unsafe extern "C" fn(*mut MemNumaNode, CULong, CULong);
type MemPageAllocatorInitFn = unsafe extern "C" fn(CULong, CULong) -> *mut c_void;
type MemNumaListAllocatorFn = unsafe extern "C" fn(*mut c_void, *mut MemNumaNode);
type MemPageallocCountFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type MemRusageTotalAddFn = unsafe extern "C" fn(CULong);
type MemNumaInitLogFn =
    unsafe extern "C" fn(CInt, CInt, CInt, CInt, CULong, CULong, CULong, CInt, CInt);
type MemNumaPanicFn = unsafe extern "C" fn(CInt);
type MemGetCpuInfoFn = unsafe extern "C" fn() -> *mut IhkCpuInfo;
type MemGetNsPerTscFn = unsafe extern "C" fn() -> CULong;
type MemSetRusageFn = unsafe extern "C" fn(CULong, CULong) -> CInt;
type MemRusageInitLogFn = unsafe extern "C" fn(CULong);
type MemRusageCheckOomFn = unsafe extern "C" fn(CInt, CInt, CInt) -> CInt;
type MemNumaAllocNodeFn = unsafe extern "C" fn(*mut MemNumaNode, CInt, CInt) -> CULong;
type MemCurrentNumaIdFn = unsafe extern "C" fn() -> CInt;
type MemDumpGetPageSetFn = unsafe extern "C" fn() -> *mut IhkDumpPageSet;
type MemDumpGetPageFn = unsafe extern "C" fn() -> *mut IhkDumpPage;
type MemDumpQueryFn = unsafe extern "C" fn(*mut c_void);
type MemDumpLogFn = unsafe extern "C" fn();
type MemDumpChunkCountFn = unsafe extern "C" fn(CInt) -> CULong;
type MemDumpChunkIterFn = unsafe extern "C" fn(CInt) -> *mut c_void;
type MemDumpNextChunkFn = unsafe extern "C" fn(*mut c_void) -> *mut c_void;
type MemDumpChunkFieldFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type MemDumpWarnFn = unsafe extern "C" fn(CInt, CULong, CULong, CULong, CULong, CULong);
type MemChkPageAddressFn = unsafe extern "C" fn(CULong) -> CInt;
type MemLookupPteFn = unsafe extern "C" fn(
    *mut c_void,
    *mut c_void,
    CInt,
    *mut *mut c_void,
    *mut usize,
    *mut CInt,
) -> *mut CULong;
type MemPageFaultProcessVmFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong) -> CInt;
type MemFaultLogFn = unsafe extern "C" fn(*mut c_void);
type MemPhysToNidFn = unsafe extern "C" fn(CULong) -> CInt;
type MemPteVisitorFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, *mut CULong, *mut c_void, CInt) -> CInt;
type MemVisitPteRangeFn = unsafe extern "C" fn(
    *mut c_void,
    *mut c_void,
    *mut c_void,
    CInt,
    CInt,
    Option<MemPteVisitorFn>,
    *mut c_void,
) -> CInt;
type MemKmallocIrqSaveFn = unsafe extern "C" fn() -> CULong;
type MemKmallocIrqRestoreFn = unsafe extern "C" fn(CULong);
type MemKmallocAllocPagesFn = unsafe extern "C" fn(CInt, CULong, CInt) -> *mut c_void;
type MemKmallocGetCpuLocalVarFn = unsafe extern "C" fn(CInt) -> *mut c_void;
type MemKmallocSpinLockFn = unsafe extern "C" fn(CULong) -> CULong;
type MemKmallocSpinUnlockFn = unsafe extern "C" fn(CULong, CULong);
type MemKmallocCorruptionFn = unsafe extern "C" fn(*mut c_void);
type MemKmallocCacheAllocFn = unsafe extern "C" fn(SizeT, CULong) -> *mut c_void;
type MemKmallocCacheLogFn = unsafe extern "C" fn(CInt, *mut c_void);
type MemKmallocCachePreallocFn = unsafe extern "C" fn(*mut KmallocCacheHeader, SizeT, CInt);
type MemKmallocBaseAllocFn = unsafe extern "C" fn(CInt, CULong) -> *mut c_void;
type MemKmallocBaseFreeFn = unsafe extern "C" fn(*mut c_void);
type MemKmallocSpinInitFn = unsafe extern "C" fn(CULong);
type MemKmallocTrackLogFn = unsafe extern "C" fn(CInt, *mut c_void, *mut i8, CInt, CInt);
type MemKmallocInvalidFreeFn = unsafe extern "C" fn(*mut c_void, *mut i8, CInt);
type MemGetThisCpuLocalVarFn = unsafe extern "C" fn() -> *mut CpuLocalVar;
type MemRegisterAllocFn = unsafe extern "C" fn(CInt, CULong) -> *mut c_void;
type MemRegisterFreeFn = unsafe extern "C" fn(*mut c_void);
type MemVmapInitFn = unsafe extern "C" fn(CULong, CULong, CULong) -> *mut c_void;
type MemPtPrepareMapFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CInt) -> CInt;
type MemVmapAllocFn = unsafe extern "C" fn(*mut c_void, CInt, CInt) -> CULong;
type MemVmapFreeFn = unsafe extern "C" fn(*mut c_void, CULong, CInt);
type MemPtSetPageFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, IhkMcPtAttribute) -> CInt;
type MemPtClearPageFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type MemFlushTlbSingleFn = unsafe extern "C" fn(CULong);
type MemFlushTlbAllFn = unsafe extern "C" fn();
type MemRdtscFn = unsafe extern "C" fn() -> CULong;
type MemCurrentCpuFn = unsafe extern "C" fn() -> CInt;
type MemInterruptCpuFn = unsafe extern "C" fn(CInt, CInt);
type MemNoirqLockFn = unsafe extern "C" fn(CULong);
type MemAtomicSetFn = unsafe extern "C" fn(CULong, CInt);
type MemAtomicIncFn = unsafe extern "C" fn(CULong);
type MemAtomicDecFn = unsafe extern "C" fn(CULong);
type MemAtomicReadFn = unsafe extern "C" fn(CULong) -> CInt;
type MemPauseFn = unsafe extern "C" fn();
type MemPageallocBaseAllocFn =
    unsafe extern "C" fn(CInt, CInt, CULong, CInt, CInt, CULong) -> *mut c_void;
type MemPageallocBaseFreeFn = unsafe extern "C" fn(*mut c_void, CInt, CInt);
type MemPageallocMetaAllocFn = unsafe extern "C" fn(CInt, CULong) -> *mut c_void;
type MemPageallocMetaFreeFn = unsafe extern "C" fn(*mut c_void);
type MemPageallocSpinInitFn = unsafe extern "C" fn(CULong);
type MemPageallocTrackLogFn = unsafe extern "C" fn(CInt, *mut c_void, *mut i8, CInt, CInt);
type MemPageallocInvalidFreeFn = unsafe extern "C" fn(*mut c_void, *mut i8, CInt);
type MemPageallocInvalidSizeFn = unsafe extern "C" fn(*mut c_void, CInt, CInt, *mut i8, CInt);
type MemPageallocNoirqLockFn = unsafe extern "C" fn(CULong);
type MemPageallocNoirqUnlockFn = unsafe extern "C" fn(CULong);
type MemTrackLeakLogFn = unsafe extern "C" fn(CInt, *mut c_void, *mut i8, CInt, CInt, CInt, CInt);

const KMALLOC_TRACK_HASH_MASK: CInt = 255;
const KMALLOC_TRACK_HASH_SIZE: usize = (KMALLOC_TRACK_HASH_MASK as usize) + 1;
const KMALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED: CInt = 1;
const KMALLOC_TRACK_LOG_FILE_ALLOC_FAILED: CInt = 2;
const KMALLOC_TRACK_LOG_ENTRY_ADDED: CInt = 3;
const KMALLOC_TRACK_LOG_ADDR_ALLOC_FAILED: CInt = 4;
const KMALLOC_TRACK_LOG_ADDR_ADDED: CInt = 5;
const KMALLOC_TRACK_LOG_ADDR_REMOVED: CInt = 6;
const KMALLOC_TRACK_LOG_ENTRY_REMOVED: CInt = 7;
const KMALLOC_CACHE_LOG_NO_CACHE: CInt = 1;
const KMALLOC_CACHE_LOG_ALLOC_FAILED: CInt = 2;
const KMALLOC_CACHE_LOG_PREALLOC: CInt = 3;
const PAGEALLOC_TRACK_HASH_MASK: CInt = 255;
const PAGEALLOC_TRACK_HASH_SIZE: usize = (PAGEALLOC_TRACK_HASH_MASK as usize) + 1;
const PAGEALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED: CInt = 1;
const PAGEALLOC_TRACK_LOG_FILE_ALLOC_FAILED: CInt = 2;
const PAGEALLOC_TRACK_LOG_ENTRY_ADDED: CInt = 3;
const PAGEALLOC_TRACK_LOG_ADDR_ALLOC_FAILED: CInt = 4;
const PAGEALLOC_TRACK_LOG_ADDR_ADDED: CInt = 5;
const PAGEALLOC_TRACK_LOG_ADDR_REMOVED: CInt = 6;
const PAGEALLOC_TRACK_LOG_ENTRY_REMOVED: CInt = 7;
const PAGEALLOC_TRACK_LOG_COVERING_FOUND: CInt = 8;
const PAGEALLOC_TRACK_LOG_ADDR_NEXT_ADDED: CInt = 9;
const PAGEALLOC_TRACK_LOG_ADDR_MODIFIED: CInt = 10;
const MEM_TRACK_LEAK_DETAIL: CInt = 1;
const X86_USER_END: CULong = 0x0000_8000_0000_0000;
const MEM_TRACK_LEAK_SUMMARY: CInt = 2;

#[repr(C)]
pub struct IhkMcPaOps {
    alloc_page: Option<MemPaAllocPageFn>,
    free_page: Option<MemPaFreePageFn>,
    alloc: *mut c_void,
    free: *mut c_void,
}

static mut MEM_PA_OPS: *mut IhkMcPaOps = null_mut();

#[repr(C)]
pub struct RusageGlobal {
    memory_stat_rss: [CLong; IHK_MAX_NUM_PGSIZES],
    memory_stat_mapped_file: [CLong; IHK_MAX_NUM_PGSIZES],
    rss_current: CLong,
    memory_max_usage: CULong,
    max_num_threads: CULong,
    num_threads: CULong,
    memory_kmem_usage: CULong,
    memory_kmem_max_usage: CULong,
    memory_numa_stat: [CULong; IHK_MAX_NUM_NUMA_NODES],
    cpu: [RusagePercpu; IHK_MAX_NUM_CPUS],
    total_memory: CULong,
    total_memory_usage: CULong,
    total_memory_max_usage: CULong,
    num_numa_nodes: CULong,
    num_processors: CULong,
    ns_per_tsc: CULong,
}

#[no_mangle]
pub extern "C" fn rusage_pgsize_to_pgtype(pgsize: SizeT) -> CInt {
    match pgsize {
        0x1000 => IHK_OS_PGSIZE_4KB,
        0x20_0000 => IHK_OS_PGSIZE_2MB,
        0x4000_0000 => IHK_OS_PGSIZE_1GB,
        _ => IHK_OS_PGSIZE_4KB,
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_total_memory_add(size: CULong) {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        (*rusage_ptr).total_memory = (*rusage_ptr).total_memory.wrapping_add(size);
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = size;
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_get_total_memory() -> CULong {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        (*rusage_ptr).total_memory
    }

    #[cfg(not(enable_rusage))]
    {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_get_free_memory() -> CULong {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        (*rusage_ptr)
            .total_memory
            .wrapping_sub((*rusage_ptr).total_memory_usage)
    }

    #[cfg(not(enable_rusage))]
    {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_get_usage_memory() -> CULong {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        (*rusage_ptr).total_memory_usage
    }

    #[cfg(not(enable_rusage))]
    {
        0
    }
}

#[inline(always)]
unsafe fn rusage_atomic_add_long(slot: *mut CLong, value: CLong) {
    (*slot.cast::<AtomicI64>()).fetch_add(value, Ordering::SeqCst);
}

#[inline(always)]
unsafe fn rusage_atomic_add_long_fetch(slot: *mut CLong, value: CLong) -> CLong {
    (*slot.cast::<AtomicI64>())
        .fetch_add(value, Ordering::SeqCst)
        .wrapping_add(value)
}

#[inline(always)]
unsafe fn rusage_atomic_sub_long_fetch(slot: *mut CLong, value: CLong) -> CLong {
    (*slot.cast::<AtomicI64>())
        .fetch_sub(value, Ordering::SeqCst)
        .wrapping_sub(value)
}

#[inline(always)]
unsafe fn rusage_atomic_add_ulong(slot: *mut CULong, value: CULong) -> CULong {
    (*slot.cast::<AtomicU64>())
        .fetch_add(value, Ordering::SeqCst)
        .wrapping_add(value)
}

#[inline(always)]
unsafe fn rusage_atomic_sub_ulong(slot: *mut CULong, value: CULong) -> CULong {
    (*slot.cast::<AtomicU64>())
        .fetch_sub(value, Ordering::SeqCst)
        .wrapping_sub(value)
}

#[inline(always)]
unsafe fn rusage_update_max(slot: *mut CULong, newval: CULong) {
    let max = &*slot.cast::<AtomicU64>();
    let mut oldval = max.load(Ordering::SeqCst);
    while newval > oldval {
        match max.compare_exchange(oldval, newval, Ordering::SeqCst, Ordering::SeqCst) {
            Ok(_) => break,
            Err(actual) => oldval = actual,
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_rss_add(size: CULong) {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let newval =
            rusage_atomic_add_long_fetch(&raw mut (*rusage_ptr).rss_current, size as CLong);
        rusage_update_max(&raw mut (*rusage_ptr).memory_max_usage, newval as CULong);

        let cpu_local = get_this_cpu_local_var();
        let mut vm = (*cpu_local).on_fork_vm;
        if vm.is_null() {
            vm = (*(*cpu_local).current).vm;
        }

        (*vm).currss = (*vm).currss.wrapping_add(size as CLong);
        let proc = (*vm).proc.cast::<Process>();
        if !proc.is_null() && (*vm).currss > (*proc).maxrss {
            (*proc).maxrss = (*vm).currss;
        }
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = size;
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_rss_sub(size: CULong) {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let _ = rusage_atomic_sub_long_fetch(&raw mut (*rusage_ptr).rss_current, size as CLong);

        let cpu_local = get_this_cpu_local_var();
        let vm = (*(*cpu_local).current).vm;
        (*vm).currss = (*vm).currss.wrapping_sub(size as CLong);
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = size;
    }
}

#[no_mangle]
pub unsafe extern "C" fn memory_stat_rss_add(size: CULong, pgsize: CInt) {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let slot = (*rusage_ptr)
            .memory_stat_rss
            .as_mut_ptr()
            .add(rusage_pgsize_to_pgtype(pgsize as SizeT) as usize);
        rusage_atomic_add_long(slot, size as CLong);
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (size, pgsize);
    }
}

#[no_mangle]
pub unsafe extern "C" fn memory_stat_rss_sub(size: CULong, pgsize: CInt) {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let slot = (*rusage_ptr)
            .memory_stat_rss
            .as_mut_ptr()
            .add(rusage_pgsize_to_pgtype(pgsize as SizeT) as usize);
        rusage_atomic_add_long(slot, (size as CLong).wrapping_neg());
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (size, pgsize);
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_memory_stat_mapped_file_add(size: CULong, pgsize: CInt) {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let slot = (*rusage_ptr)
            .memory_stat_mapped_file
            .as_mut_ptr()
            .add(rusage_pgsize_to_pgtype(pgsize as SizeT) as usize);
        rusage_atomic_add_long(slot, size as CLong);
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (size, pgsize);
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_memory_stat_mapped_file_sub(size: CULong, pgsize: CInt) {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let slot = (*rusage_ptr)
            .memory_stat_mapped_file
            .as_mut_ptr()
            .add(rusage_pgsize_to_pgtype(pgsize as SizeT) as usize);
        rusage_atomic_add_long(slot, (size as CLong).wrapping_neg());
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (size, pgsize);
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_memory_stat_sub(memobj: *mut Memobj, size: CULong, pgsize: CInt) {
    #[cfg(enable_rusage)]
    {
        if ((*memobj).flags & (MF_SHM as u32)) != 0 {
            memory_stat_rss_sub(size, pgsize);
        } else {
            rusage_memory_stat_mapped_file_sub(size, pgsize);
        }
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (memobj, size, pgsize);
    }
}

#[cfg(enable_rusage)]
unsafe fn rusage_memory_stat_add_body(
    range: *mut VmRange,
    phys: CULong,
    size: CULong,
    pgsize: CInt,
    mut page: *mut MemPage,
    lookup_page: bool,
    cow_flags: CULong,
    warning_name: *const i8,
) -> CInt {
    let memobj = (*range).memobj.cast::<Memobj>();

    if ((*range).flag & (VR_REMOTE | VR_IO_NOCACHE | VR_RESERVED)) != 0 {
        return 0;
    }

    if memobj.is_null() {
        memory_stat_rss_add(size, pgsize);
        return 1;
    }

    let flags = (*memobj).flags as CULong;
    if (flags & MF_DEV_FILE) != 0 || (flags & MF_PREMAP) != 0 || (flags & MF_XPMEM) != 0 {
        return 0;
    }

    if (flags & MF_ZEROOBJ) != 0 {
        memory_stat_rss_add(size, pgsize);
        return 1;
    }

    if lookup_page {
        page = phys_to_page(phys);
    }

    if (flags & cow_flags) != 0 && page.is_null() {
        memory_stat_rss_add(size, pgsize);
        return 1;
    }

    if page.is_null() {
        kprintf(
            RUSAGE_MEMORY_STAT_ADD_WARNING_FMT.as_ptr().cast(),
            warning_name,
            phys,
        );
        return 0;
    }

    let mapped = &*(&raw mut (*page).mapped.counter64).cast::<AtomicI64>();
    if mapped
        .compare_exchange(0, 1, Ordering::SeqCst, Ordering::SeqCst)
        .is_ok()
    {
        if (flags & MF_SHM) != 0 {
            memory_stat_rss_add(size, pgsize);
        } else {
            rusage_memory_stat_mapped_file_add(size, pgsize);
        }
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_memory_stat_add(
    range: *mut VmRange,
    phys: CULong,
    size: CULong,
    pgsize: CInt,
) -> CInt {
    #[cfg(enable_rusage)]
    {
        rusage_memory_stat_add_body(
            range,
            phys,
            size,
            pgsize,
            core::ptr::null_mut(),
            true,
            MF_DEV_FILE | MF_REG_FILE | MF_HUGETLBFS,
            RUSAGE_MEMORY_STAT_ADD_NAME.as_ptr().cast(),
        )
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (range, phys, size, pgsize);
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_memory_stat_add_with_page(
    range: *mut VmRange,
    phys: CULong,
    size: CULong,
    pgsize: CInt,
    page: *mut MemPage,
) -> CInt {
    #[cfg(enable_rusage)]
    {
        rusage_memory_stat_add_body(
            range,
            phys,
            size,
            pgsize,
            page,
            false,
            MF_DEV_FILE | MF_REG_FILE,
            RUSAGE_MEMORY_STAT_ADD_WITH_PAGE_NAME.as_ptr().cast(),
        )
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (range, phys, size, pgsize, page);
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_numa_add(numa_id: CInt, size: CULong) {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let slot = (*rusage_ptr)
            .memory_numa_stat
            .as_mut_ptr()
            .add(numa_id as usize);
        let _ = rusage_atomic_add_ulong(slot, size);
        rusage_rss_add(size);
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (numa_id, size);
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_numa_sub(numa_id: CInt, size: CULong) {
    #[cfg(enable_rusage)]
    {
        rusage_rss_sub(size);
        let rusage_ptr = &raw mut RUSAGE;
        let slot = (*rusage_ptr)
            .memory_numa_stat
            .as_mut_ptr()
            .add(numa_id as usize);
        let _ = rusage_atomic_sub_ulong(slot, size);
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (numa_id, size);
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_page_add(numa_id: CInt, pages: CULong, is_user: CInt) {
    #[cfg(enable_rusage)]
    {
        let size = pages.wrapping_mul(PAGE_SIZE);

        if is_user != 0 {
            rusage_numa_add(numa_id, size);
        } else {
            rusage_kmem_add(size);
        }

        let rusage_ptr = &raw mut RUSAGE;
        let newval = rusage_atomic_add_ulong(&raw mut (*rusage_ptr).total_memory_usage, size);
        rusage_update_max(&raw mut (*rusage_ptr).total_memory_max_usage, newval);
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (numa_id, pages, is_user);
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_page_sub(numa_id: CInt, pages: CULong, is_user: CInt) {
    #[cfg(enable_rusage)]
    {
        let size = pages.wrapping_mul(PAGE_SIZE);
        let rusage_ptr = &raw mut RUSAGE;
        let _ = rusage_atomic_sub_ulong(&raw mut (*rusage_ptr).total_memory_usage, size);

        if is_user != 0 {
            rusage_numa_sub(numa_id, size);
        } else {
            rusage_kmem_sub(size);
        }
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (numa_id, pages, is_user);
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_kmem_add(size: CULong) {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let newval = rusage_atomic_add_ulong(&raw mut (*rusage_ptr).memory_kmem_usage, size);
        rusage_update_max(&raw mut (*rusage_ptr).memory_kmem_max_usage, newval);
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = size;
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_kmem_sub(size: CULong) {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let _ = rusage_atomic_sub_ulong(&raw mut (*rusage_ptr).memory_kmem_usage, size);
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = size;
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_num_threads_inc() {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let newval = rusage_atomic_add_ulong(&raw mut (*rusage_ptr).num_threads, 1);
        rusage_update_max(&raw mut (*rusage_ptr).max_num_threads, newval);
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_num_threads_dec() {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let _ = rusage_atomic_sub_ulong(&raw mut (*rusage_ptr).num_threads, 1);
    }
}

#[no_mangle]
pub unsafe extern "C" fn rusage_check_oom(_numa_id: CInt, pages: CULong, is_user: CInt) -> CInt {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let size = pages.wrapping_mul(PAGE_SIZE);
        let usage = (*rusage_ptr).total_memory_usage;
        let total = (*rusage_ptr).total_memory;
        if usage.wrapping_add(size) > total.wrapping_sub(RUSAGE_OOM_MARGIN) {
            kprintf(
                RUSAGE_CHECK_OOM_FMT.as_ptr().cast(),
                RUSAGE_CHECK_OOM_NAME.as_ptr().cast::<i8>(),
                usage,
                total,
            );
            eventfd(IHK_OS_EVENTFD_TYPE_OOM);
            if is_user != 0 {
                return -ENOMEM;
            }
        }
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (_numa_id, pages, is_user);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn rusage_check_overmap(len: SizeT, pgshift: CInt) -> CInt {
    #[cfg(enable_rusage)]
    {
        if sysctl_overcommit_memory == OVERCOMMIT_ALWAYS {
            return 0;
        }

        let shift = pgshift as u32;
        let page_size = 1usize << shift;
        let npages = ((len.wrapping_add(page_size.wrapping_sub(1))) >> shift) as CInt;
        let rusage_ptr = &raw mut RUSAGE;
        let remain_pages = ((*rusage_ptr)
            .total_memory
            .wrapping_sub((*rusage_ptr).total_memory_usage)
            >> shift) as CInt;

        if npages > remain_pages {
            return 1;
        }
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (len, pgshift);
    }

    0
}

#[repr(C)]
pub struct MemPage {
    list: AbiListHead,
    hash: AbiListHead,
    mode: u8,
    phys: CULong,
    count: IhkAtomic,
    mapped: IhkAtomic64,
    offset: OffT,
    pgshift: CInt,
}

#[repr(C)]
pub struct KmallocTrackAddrEntry {
    addr: *mut c_void,
    runcount: CInt,
    list: AbiListHead,
    entry: *mut KmallocTrackEntry,
    hash: AbiListHead,
}

#[repr(C)]
pub struct KmallocTrackEntry {
    file: *mut i8,
    line: CInt,
    size: CInt,
    alloc_count: IhkAtomic,
    hash: AbiListHead,
    addr_list: AbiListHead,
    addr_list_lock: IhkSpinlock,
}

#[repr(C)]
pub struct PageallocTrackAddrEntry {
    addr: *mut c_void,
    runcount: CInt,
    list: AbiListHead,
    entry: *mut PageallocTrackEntry,
    hash: AbiListHead,
    npages: CInt,
}

#[repr(C)]
pub struct PageallocTrackEntry {
    file: *mut i8,
    line: CInt,
    alloc_count: IhkAtomic,
    hash: AbiListHead,
    addr_list: AbiListHead,
    addr_list_lock: IhkSpinlock,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct MemNodeDistance {
    id: CInt,
    distance: CInt,
}

#[repr(C, align(64))]
pub struct MemNumaNode {
    id: CInt,
    linux_numa_id: CInt,
    node_type: CInt,
    _pad0: CInt,
    allocators: AbiListHead,
    nodes_by_distance: *mut MemNodeDistance,
    zeroing_workers: IhkAtomic,
    nr_to_zero_pages: IhkAtomic,
    zeroed_list: LListHead,
    to_zero_list: LListHead,
    free_chunks: RbRoot,
    lock: McsLockNode,
    nr_pages: CULong,
    nr_free_pages: CULong,
    min_addr: CULong,
    max_addr: CULong,
}

#[repr(C)]
pub struct MemFreeChunk {
    addr: CULong,
    size: CULong,
    node: RbNode,
    list: LListNode,
}

#[repr(C)]
pub struct IhkDumpPage {
    start: CULong,
    map_count: CULong,
    map: [CULong; 0],
}

#[repr(C)]
pub struct IhkDumpPageSet {
    completion_flag: u32,
    count: u32,
    page_size: CULong,
    phy_page: CULong,
}

#[repr(C)]
pub struct DumpPaseInfo {
    dump_page_set: *mut IhkDumpPageSet,
    dump_pages: *mut IhkDumpPage,
}

const _: () = {
    assert!(size_of::<IhkMcPaOps>() == 32);
    assert!(align_of::<IhkMcPaOps>() == 8);
    assert!(offset_of!(IhkMcPaOps, alloc_page) == 0);
    assert!(offset_of!(IhkMcPaOps, free_page) == 8);
    assert!(size_of::<MemPage>() == 80);
    assert!(align_of::<MemPage>() == 8);
    assert!(offset_of!(MemPage, list) == 0);
    assert!(offset_of!(MemPage, hash) == 16);
    assert!(offset_of!(MemPage, mode) == 32);
    assert!(offset_of!(MemPage, phys) == 40);
    assert!(offset_of!(MemPage, count) == 48);
    assert!(offset_of!(MemPage, mapped) == 56);
    assert!(offset_of!(MemPage, offset) == 64);
    assert!(offset_of!(MemPage, pgshift) == 72);
    assert!(size_of::<KmallocTrackAddrEntry>() == 56);
    assert!(align_of::<KmallocTrackAddrEntry>() == 8);
    assert!(offset_of!(KmallocTrackAddrEntry, runcount) == 8);
    assert!(offset_of!(KmallocTrackAddrEntry, list) == 16);
    assert!(offset_of!(KmallocTrackAddrEntry, entry) == 32);
    assert!(offset_of!(KmallocTrackAddrEntry, hash) == 40);
    assert!(size_of::<KmallocTrackEntry>() == 64);
    assert!(align_of::<KmallocTrackEntry>() == 8);
    assert!(offset_of!(KmallocTrackEntry, line) == 8);
    assert!(offset_of!(KmallocTrackEntry, size) == 12);
    assert!(offset_of!(KmallocTrackEntry, alloc_count) == 16);
    assert!(offset_of!(KmallocTrackEntry, hash) == 24);
    assert!(offset_of!(KmallocTrackEntry, addr_list) == 40);
    assert!(offset_of!(KmallocTrackEntry, addr_list_lock) == 56);
    assert!(size_of::<PageallocTrackAddrEntry>() == 64);
    assert!(align_of::<PageallocTrackAddrEntry>() == 8);
    assert!(offset_of!(PageallocTrackAddrEntry, runcount) == 8);
    assert!(offset_of!(PageallocTrackAddrEntry, list) == 16);
    assert!(offset_of!(PageallocTrackAddrEntry, entry) == 32);
    assert!(offset_of!(PageallocTrackAddrEntry, hash) == 40);
    assert!(offset_of!(PageallocTrackAddrEntry, npages) == 56);
    assert!(size_of::<PageallocTrackEntry>() == 56);
    assert!(align_of::<PageallocTrackEntry>() == 8);
    assert!(offset_of!(PageallocTrackEntry, line) == 8);
    assert!(offset_of!(PageallocTrackEntry, alloc_count) == 12);
    assert!(offset_of!(PageallocTrackEntry, hash) == 16);
    assert!(offset_of!(PageallocTrackEntry, addr_list) == 32);
    assert!(offset_of!(PageallocTrackEntry, addr_list_lock) == 48);
    assert!(size_of::<MemNodeDistance>() == 8);
    assert!(align_of::<MemNodeDistance>() == 4);
    assert!(offset_of!(MemNodeDistance, id) == 0);
    assert!(offset_of!(MemNodeDistance, distance) == 4);
    assert!(size_of::<MemNumaNode>() == 256);
    assert!(align_of::<MemNumaNode>() == 64);
    assert!(offset_of!(MemNumaNode, id) == 0);
    assert!(offset_of!(MemNumaNode, linux_numa_id) == 4);
    assert!(offset_of!(MemNumaNode, node_type) == 8);
    assert!(offset_of!(MemNumaNode, allocators) == 16);
    assert!(offset_of!(MemNumaNode, nodes_by_distance) == 32);
    assert!(offset_of!(MemNumaNode, free_chunks) == 64);
    assert!(offset_of!(MemNumaNode, lock) == 128);
    assert!(offset_of!(MemNumaNode, nr_pages) == 192);
    assert!(offset_of!(MemNumaNode, nr_free_pages) == 200);
    assert!(size_of::<MemFreeChunk>() == 48);
    assert!(align_of::<MemFreeChunk>() == 8);
    assert!(offset_of!(MemFreeChunk, addr) == 0);
    assert!(offset_of!(MemFreeChunk, size) == 8);
    assert!(offset_of!(MemFreeChunk, node) == 16);
    assert!(offset_of!(MemFreeChunk, list) == 40);
    assert!(size_of::<IhkDumpPage>() == 16);
    assert!(align_of::<IhkDumpPage>() == 8);
    assert!(offset_of!(IhkDumpPage, map_count) == 8);
    assert!(offset_of!(IhkDumpPage, map) == 16);
    assert!(size_of::<IhkDumpPageSet>() == 24);
    assert!(align_of::<IhkDumpPageSet>() == 8);
    assert!(offset_of!(IhkDumpPageSet, completion_flag) == 0);
    assert!(offset_of!(IhkDumpPageSet, count) == 4);
    assert!(offset_of!(IhkDumpPageSet, page_size) == 8);
    assert!(offset_of!(IhkDumpPageSet, phy_page) == 16);
    assert!(size_of::<DumpPaseInfo>() == 16);
    assert!(align_of::<DumpPaseInfo>() == 8);
    assert!(offset_of!(DumpPaseInfo, dump_pages) == 8);
};

#[inline(always)]
unsafe fn kmalloc_list(chunk: *mut KmallocHeader) -> *mut AbiListHead {
    (&raw mut (*chunk).link.list).cast::<AbiListHead>()
}

#[inline(always)]
unsafe fn list_to_kmalloc_header(node: *mut AbiListHead) -> *mut KmallocHeader {
    node.cast::<u8>()
        .sub(offset_of!(KmallocHeader, link))
        .cast::<KmallocHeader>()
}

#[inline(always)]
unsafe fn list_add(new: *mut AbiListHead, prev: *mut AbiListHead, next: *mut AbiListHead) {
    (*next).prev = new;
    (*new).next = next;
    (*new).prev = prev;
    (*prev).next = new;
}

#[inline(always)]
unsafe fn list_add_tail(new: *mut AbiListHead, head: *mut AbiListHead) {
    list_add(new, (*head).prev, head);
}

#[inline(always)]
unsafe fn list_add_after(new: *mut AbiListHead, head: *mut AbiListHead) {
    list_add(new, head, (*head).next);
}

#[inline(always)]
unsafe fn list_del(entry: *mut AbiListHead) {
    let next = (*entry).next;
    let prev = (*entry).prev;
    (*next).prev = prev;
    (*prev).next = next;
}

#[inline(always)]
unsafe fn init_list_head(head: *mut AbiListHead) {
    (*head).next = head;
    (*head).prev = head;
}

#[inline(always)]
unsafe fn list_del_poison(entry: *mut AbiListHead) {
    list_del(entry);
    (*entry).next = LIST_POISON1 as *mut AbiListHead;
    (*entry).prev = LIST_POISON2 as *mut AbiListHead;
}

#[inline(always)]
unsafe fn page_from_list(node: *mut AbiListHead) -> *mut MemPage {
    node.cast::<MemPage>()
}

#[inline(always)]
unsafe fn kmalloc_track_hash(size: CInt, file: *mut i8, line: CInt) -> CInt {
    let len = if file.is_null() {
        0
    } else {
        strlen(file.cast_const()) as CInt
    };
    len.wrapping_add(line).wrapping_add(size) & KMALLOC_TRACK_HASH_MASK
}

#[inline(always)]
unsafe fn kmalloc_addr_hash(ptr: *mut c_void) -> CInt {
    ((ptr as CULong) >> 5 & KMALLOC_TRACK_HASH_MASK as CULong) as CInt
}

#[inline(always)]
unsafe fn kmalloc_track_entry_alloc_count(entry: *mut KmallocTrackEntry) -> &'static AtomicI32 {
    AtomicI32::from_ptr(&raw mut (*entry).alloc_count.counter)
}

#[inline(always)]
unsafe fn kmalloc_track_entry_from_hash(node: *mut AbiListHead) -> *mut KmallocTrackEntry {
    node.cast::<u8>()
        .sub(offset_of!(KmallocTrackEntry, hash))
        .cast::<KmallocTrackEntry>()
}

#[inline(always)]
unsafe fn kmalloc_track_addr_from_hash(node: *mut AbiListHead) -> *mut KmallocTrackAddrEntry {
    node.cast::<u8>()
        .sub(offset_of!(KmallocTrackAddrEntry, hash))
        .cast::<KmallocTrackAddrEntry>()
}

#[inline(always)]
unsafe fn kmalloc_track_addr_from_list(node: *mut AbiListHead) -> *mut KmallocTrackAddrEntry {
    node.cast::<u8>()
        .sub(offset_of!(KmallocTrackAddrEntry, list))
        .cast::<KmallocTrackAddrEntry>()
}

#[inline(always)]
unsafe fn kmalloc_track_log(
    log_fn: Option<MemKmallocTrackLogFn>,
    event: CInt,
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
    size: CInt,
) {
    if let Some(log) = log_fn {
        log(event, ptr, file, line, size);
    }
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_track_find_entry_result(
    size: CInt,
    file: *mut i8,
    line: CInt,
    track_hash: *mut AbiListHead,
) -> *mut KmallocTrackEntry {
    if file.is_null() || track_hash.is_null() {
        return null_mut();
    }

    let hash = kmalloc_track_hash(size, file, line);
    let head = track_hash.add(hash as usize);
    let mut node = (*head).next;

    while node != head {
        let entry = kmalloc_track_entry_from_hash(node);
        if (*entry).size == size && (*entry).line == line && strcmp((*entry).file, file) == 0 {
            return entry;
        }
        node = (*node).next;
    }

    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_track_alloc_result(
    size: CInt,
    flag: CULong,
    file: *mut i8,
    line: CInt,
    memdebug: *mut i8,
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    runcount: CInt,
    base_alloc_fn: Option<MemKmallocBaseAllocFn>,
    base_free_fn: Option<MemKmallocBaseFreeFn>,
    lock_fn: Option<MemKmallocSpinLockFn>,
    unlock_fn: Option<MemKmallocSpinUnlockFn>,
    spin_init_fn: Option<MemKmallocSpinInitFn>,
    log_fn: Option<MemKmallocTrackLogFn>,
) -> *mut c_void {
    let Some(base_alloc) = base_alloc_fn else {
        return null_mut();
    };

    let result = base_alloc(size, flag);
    if memdebug.is_null() || result.is_null() {
        return result;
    }
    if file.is_null()
        || track_hash.is_null()
        || track_locks.is_null()
        || addr_hash.is_null()
        || addr_locks.is_null()
    {
        return result;
    }
    let (Some(base_free), Some(lock), Some(unlock), Some(spin_init)) =
        (base_free_fn, lock_fn, unlock_fn, spin_init_fn)
    else {
        return result;
    };

    let hash = kmalloc_track_hash(size, file, line);
    let track_lock = track_locks.add(hash as usize);
    let irq_flags = lock(track_lock as CULong);
    let mut entry = kmalloc_track_find_entry_result(size, file, line, track_hash);

    if entry.is_null() {
        entry = base_alloc(size_of::<KmallocTrackEntry>() as CInt, IHK_MC_AP_NOWAIT)
            .cast::<KmallocTrackEntry>();
        if entry.is_null() {
            unlock(track_lock as CULong, irq_flags);
            kmalloc_track_log(
                log_fn,
                KMALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED,
                result,
                file,
                line,
                size,
            );
            return result;
        }

        (*entry).line = line;
        (*entry).size = size;
        kmalloc_track_entry_alloc_count(entry).store(1, Ordering::Relaxed);
        spin_init((&raw mut (*entry).addr_list_lock) as CULong);
        init_list_head(&raw mut (*entry).addr_list);

        let file_len = strlen(file.cast_const()) as CInt;
        (*entry).file = base_alloc(file_len.wrapping_add(1), IHK_MC_AP_NOWAIT).cast::<i8>();
        if (*entry).file.is_null() {
            kmalloc_track_log(
                log_fn,
                KMALLOC_TRACK_LOG_FILE_ALLOC_FAILED,
                result,
                file,
                line,
                size,
            );
            base_free(entry.cast::<c_void>());
            unlock(track_lock as CULong, irq_flags);
            return result;
        }

        strcpy((*entry).file, file.cast_const());
        init_list_head(&raw mut (*entry).hash);
        list_add_after(&raw mut (*entry).hash, track_hash.add(hash as usize));
        kmalloc_track_log(
            log_fn,
            KMALLOC_TRACK_LOG_ENTRY_ADDED,
            result,
            file,
            line,
            size,
        );
    } else {
        kmalloc_track_entry_alloc_count(entry).fetch_add(1, Ordering::Relaxed);
    }
    unlock(track_lock as CULong, irq_flags);

    let addr_entry = base_alloc(size_of::<KmallocTrackAddrEntry>() as CInt, IHK_MC_AP_NOWAIT)
        .cast::<KmallocTrackAddrEntry>();
    if addr_entry.is_null() {
        kmalloc_track_log(
            log_fn,
            KMALLOC_TRACK_LOG_ADDR_ALLOC_FAILED,
            result,
            file,
            line,
            size,
        );
        return result;
    }

    (*addr_entry).addr = result;
    (*addr_entry).runcount = runcount;
    (*addr_entry).entry = entry;
    init_list_head(&raw mut (*addr_entry).list);
    init_list_head(&raw mut (*addr_entry).hash);

    let irq_flags = lock((&raw mut (*entry).addr_list_lock) as CULong);
    list_add_after(&raw mut (*addr_entry).list, &raw mut (*entry).addr_list);
    unlock((&raw mut (*entry).addr_list_lock) as CULong, irq_flags);

    let addr_hash_index = kmalloc_addr_hash(result);
    let addr_lock = addr_locks.add(addr_hash_index as usize);
    let irq_flags = lock(addr_lock as CULong);
    list_add_after(
        &raw mut (*addr_entry).hash,
        addr_hash.add(addr_hash_index as usize),
    );
    unlock(addr_lock as CULong, irq_flags);
    kmalloc_track_log(
        log_fn,
        KMALLOC_TRACK_LOG_ADDR_ADDED,
        result,
        file,
        line,
        size,
    );

    result
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_track_free_result(
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
    memdebug: *mut i8,
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    base_free_fn: Option<MemKmallocBaseFreeFn>,
    lock_fn: Option<MemKmallocSpinLockFn>,
    unlock_fn: Option<MemKmallocSpinUnlockFn>,
    invalid_free_fn: Option<MemKmallocInvalidFreeFn>,
    log_fn: Option<MemKmallocTrackLogFn>,
) -> CInt {
    if ptr.is_null() {
        return 0;
    }
    let Some(base_free) = base_free_fn else {
        return -EINVAL;
    };
    if memdebug.is_null() {
        base_free(ptr);
        return 0;
    }
    if addr_hash.is_null() || addr_locks.is_null() || track_hash.is_null() || track_locks.is_null()
    {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock)) = (lock_fn, unlock_fn) else {
        return -EINVAL;
    };

    let addr_hash_index = kmalloc_addr_hash(ptr);
    let addr_lock = addr_locks.add(addr_hash_index as usize);
    let irq_flags = lock(addr_lock as CULong);
    let head = addr_hash.add(addr_hash_index as usize);
    let mut node = (*head).next;
    let mut addr_entry: *mut KmallocTrackAddrEntry = null_mut();

    while node != head {
        let candidate = kmalloc_track_addr_from_hash(node);
        if (*candidate).addr == ptr {
            addr_entry = candidate;
            break;
        }
        node = (*node).next;
    }

    if !addr_entry.is_null() {
        list_del(&raw mut (*addr_entry).hash);
    }
    unlock(addr_lock as CULong, irq_flags);

    if addr_entry.is_null() {
        if let Some(invalid_free) = invalid_free_fn {
            invalid_free(ptr, file, line);
        }
        return -EINVAL;
    }

    let entry = (*addr_entry).entry;
    let irq_flags = lock((&raw mut (*entry).addr_list_lock) as CULong);
    list_del(&raw mut (*addr_entry).list);
    unlock((&raw mut (*entry).addr_list_lock) as CULong, irq_flags);
    kmalloc_track_log(
        log_fn,
        KMALLOC_TRACK_LOG_ADDR_REMOVED,
        ptr,
        (*entry).file,
        (*entry).line,
        (*entry).size,
    );
    base_free(addr_entry.cast::<c_void>());

    let hash = kmalloc_track_hash((*entry).size, (*entry).file, (*entry).line);
    let track_lock = track_locks.add(hash as usize);
    let irq_flags = lock(track_lock as CULong);
    let old_count = kmalloc_track_entry_alloc_count(entry).fetch_sub(1, Ordering::Relaxed);
    if old_count != 1 {
        unlock(track_lock as CULong, irq_flags);
        base_free(ptr);
        return 0;
    }

    list_del(&raw mut (*entry).hash);
    unlock(track_lock as CULong, irq_flags);
    kmalloc_track_log(
        log_fn,
        KMALLOC_TRACK_LOG_ENTRY_REMOVED,
        ptr,
        (*entry).file,
        (*entry).line,
        (*entry).size,
    );
    base_free((*entry).file.cast::<c_void>());
    base_free(entry.cast::<c_void>());
    base_free(ptr);
    0
}

#[inline(always)]
unsafe fn pagealloc_track_hash(file: *mut i8, line: CInt) -> CInt {
    let len = if file.is_null() {
        0
    } else {
        strlen(file.cast_const()) as CInt
    };
    len.wrapping_add(line) & PAGEALLOC_TRACK_HASH_MASK
}

#[inline(always)]
unsafe fn pagealloc_addr_hash(ptr: *mut c_void) -> CInt {
    ((ptr as CULong) >> 5 & PAGEALLOC_TRACK_HASH_MASK as CULong) as CInt
}

#[inline(always)]
unsafe fn pagealloc_track_entry_alloc_count(entry: *mut PageallocTrackEntry) -> &'static AtomicI32 {
    AtomicI32::from_ptr(&raw mut (*entry).alloc_count.counter)
}

#[inline(always)]
unsafe fn pagealloc_track_entry_from_hash(node: *mut AbiListHead) -> *mut PageallocTrackEntry {
    node.cast::<u8>()
        .sub(offset_of!(PageallocTrackEntry, hash))
        .cast::<PageallocTrackEntry>()
}

#[inline(always)]
unsafe fn pagealloc_track_addr_from_hash(node: *mut AbiListHead) -> *mut PageallocTrackAddrEntry {
    node.cast::<u8>()
        .sub(offset_of!(PageallocTrackAddrEntry, hash))
        .cast::<PageallocTrackAddrEntry>()
}

#[inline(always)]
unsafe fn pagealloc_track_addr_from_list(node: *mut AbiListHead) -> *mut PageallocTrackAddrEntry {
    node.cast::<u8>()
        .sub(offset_of!(PageallocTrackAddrEntry, list))
        .cast::<PageallocTrackAddrEntry>()
}

#[inline(always)]
unsafe fn pagealloc_track_log(
    log_fn: Option<MemPageallocTrackLogFn>,
    event: CInt,
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
    npages: CInt,
) {
    if let Some(log) = log_fn {
        log(event, ptr, file, line, npages);
    }
}

#[inline(always)]
unsafe fn pagealloc_entry_addr_list_lock(entry: *mut PageallocTrackEntry) -> CULong {
    (&raw mut (*entry).addr_list_lock) as CULong
}

#[inline(always)]
unsafe fn pagealloc_rehash_addr_entry(
    addr_entry: *mut PageallocTrackAddrEntry,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    lock: MemKmallocSpinLockFn,
    unlock: MemKmallocSpinUnlockFn,
) {
    let addr_hash_index = pagealloc_addr_hash((*addr_entry).addr);
    let addr_lock = addr_locks.add(addr_hash_index as usize);
    let irq_flags = lock(addr_lock as CULong);
    list_add_after(
        &raw mut (*addr_entry).hash,
        addr_hash.add(addr_hash_index as usize),
    );
    unlock(addr_lock as CULong, irq_flags);
}

#[no_mangle]
pub unsafe extern "C" fn pagealloc_track_find_entry_result(
    file: *mut i8,
    line: CInt,
    track_hash: *mut AbiListHead,
) -> *mut PageallocTrackEntry {
    if file.is_null() || track_hash.is_null() {
        return null_mut();
    }

    let hash = pagealloc_track_hash(file, line);
    let head = track_hash.add(hash as usize);
    let mut node = (*head).next;

    while node != head {
        let entry = pagealloc_track_entry_from_hash(node);
        if (*entry).line == line && strcmp((*entry).file, file) == 0 {
            return entry;
        }
        node = (*node).next;
    }

    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn pagealloc_track_alloc_result(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    node: CInt,
    is_user: CInt,
    virt_addr: CULong,
    file: *mut i8,
    line: CInt,
    memdebug: *mut i8,
    track_initialized: CInt,
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    runcount: CInt,
    base_alloc_fn: Option<MemPageallocBaseAllocFn>,
    meta_alloc_fn: Option<MemPageallocMetaAllocFn>,
    meta_free_fn: Option<MemPageallocMetaFreeFn>,
    lock_fn: Option<MemKmallocSpinLockFn>,
    unlock_fn: Option<MemKmallocSpinUnlockFn>,
    spin_init_fn: Option<MemPageallocSpinInitFn>,
    log_fn: Option<MemPageallocTrackLogFn>,
) -> *mut c_void {
    let Some(base_alloc) = base_alloc_fn else {
        return null_mut();
    };

    let result = base_alloc(npages, p2align, flag, node, is_user, virt_addr);
    if memdebug.is_null() || track_initialized == 0 || result.is_null() {
        return result;
    }
    if file.is_null()
        || track_hash.is_null()
        || track_locks.is_null()
        || addr_hash.is_null()
        || addr_locks.is_null()
    {
        return result;
    }
    let (Some(meta_alloc), Some(meta_free), Some(lock), Some(unlock), Some(spin_init)) = (
        meta_alloc_fn,
        meta_free_fn,
        lock_fn,
        unlock_fn,
        spin_init_fn,
    ) else {
        return result;
    };

    let hash = pagealloc_track_hash(file, line);
    let track_lock = track_locks.add(hash as usize);
    let irq_flags = lock(track_lock as CULong);
    let mut entry = pagealloc_track_find_entry_result(file, line, track_hash);

    if entry.is_null() {
        entry = meta_alloc(size_of::<PageallocTrackEntry>() as CInt, IHK_MC_AP_NOWAIT)
            .cast::<PageallocTrackEntry>();
        if entry.is_null() {
            unlock(track_lock as CULong, irq_flags);
            pagealloc_track_log(
                log_fn,
                PAGEALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED,
                result,
                file,
                line,
                npages,
            );
            return result;
        }

        (*entry).line = line;
        pagealloc_track_entry_alloc_count(entry).store(1, Ordering::Relaxed);
        spin_init(pagealloc_entry_addr_list_lock(entry));
        init_list_head(&raw mut (*entry).addr_list);

        let file_len = strlen(file.cast_const()) as CInt;
        (*entry).file = meta_alloc(file_len.wrapping_add(1), IHK_MC_AP_NOWAIT).cast::<i8>();
        if (*entry).file.is_null() {
            pagealloc_track_log(
                log_fn,
                PAGEALLOC_TRACK_LOG_FILE_ALLOC_FAILED,
                result,
                file,
                line,
                npages,
            );
            meta_free(entry.cast::<c_void>());
            unlock(track_lock as CULong, irq_flags);
            return result;
        }

        strcpy((*entry).file, file.cast_const());
        init_list_head(&raw mut (*entry).hash);
        list_add_after(&raw mut (*entry).hash, track_hash.add(hash as usize));
        pagealloc_track_log(
            log_fn,
            PAGEALLOC_TRACK_LOG_ENTRY_ADDED,
            result,
            file,
            line,
            npages,
        );
    } else {
        pagealloc_track_entry_alloc_count(entry).fetch_add(1, Ordering::Relaxed);
    }
    unlock(track_lock as CULong, irq_flags);

    let addr_entry = meta_alloc(
        size_of::<PageallocTrackAddrEntry>() as CInt,
        IHK_MC_AP_NOWAIT,
    )
    .cast::<PageallocTrackAddrEntry>();
    if addr_entry.is_null() {
        pagealloc_track_log(
            log_fn,
            PAGEALLOC_TRACK_LOG_ADDR_ALLOC_FAILED,
            result,
            file,
            line,
            npages,
        );
        return result;
    }

    (*addr_entry).addr = result;
    (*addr_entry).runcount = runcount;
    (*addr_entry).entry = entry;
    (*addr_entry).npages = npages;
    init_list_head(&raw mut (*addr_entry).list);
    init_list_head(&raw mut (*addr_entry).hash);

    let irq_flags = lock(pagealloc_entry_addr_list_lock(entry));
    list_add_after(&raw mut (*addr_entry).list, &raw mut (*entry).addr_list);
    unlock(pagealloc_entry_addr_list_lock(entry), irq_flags);

    pagealloc_rehash_addr_entry(addr_entry, addr_hash, addr_locks, lock, unlock);
    pagealloc_track_log(
        log_fn,
        PAGEALLOC_TRACK_LOG_ADDR_ADDED,
        result,
        file,
        line,
        npages,
    );

    result
}

#[no_mangle]
pub unsafe extern "C" fn pagealloc_track_free_result(
    ptr: *mut c_void,
    npages: CInt,
    is_user: CInt,
    file: *mut i8,
    line: CInt,
    memdebug: *mut i8,
    track_initialized: CInt,
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    base_free_fn: Option<MemPageallocBaseFreeFn>,
    meta_alloc_fn: Option<MemPageallocMetaAllocFn>,
    meta_free_fn: Option<MemPageallocMetaFreeFn>,
    lock_fn: Option<MemKmallocSpinLockFn>,
    unlock_fn: Option<MemKmallocSpinUnlockFn>,
    noirq_lock_fn: Option<MemPageallocNoirqLockFn>,
    noirq_unlock_fn: Option<MemPageallocNoirqUnlockFn>,
    invalid_free_fn: Option<MemPageallocInvalidFreeFn>,
    invalid_size_fn: Option<MemPageallocInvalidSizeFn>,
    log_fn: Option<MemPageallocTrackLogFn>,
) -> CInt {
    let Some(base_free) = base_free_fn else {
        return -EINVAL;
    };
    if memdebug.is_null() || track_initialized == 0 {
        base_free(ptr, npages, is_user);
        return 0;
    }
    if addr_hash.is_null() || addr_locks.is_null() || track_hash.is_null() || track_locks.is_null()
    {
        return -EINVAL;
    }
    let (Some(meta_alloc), Some(meta_free), Some(lock), Some(unlock)) =
        (meta_alloc_fn, meta_free_fn, lock_fn, unlock_fn)
    else {
        return -EINVAL;
    };

    let free_bytes = (npages as usize) << PAGE_SHIFT;
    let free_start = ptr as usize;
    let free_end = free_start.wrapping_add(free_bytes);
    let mut rehash_addr_entry = false;
    let mut addr_entry: *mut PageallocTrackAddrEntry = null_mut();

    let hash = pagealloc_addr_hash(ptr);
    let addr_lock = addr_locks.add(hash as usize);
    let irq_flags = lock(addr_lock as CULong);
    let head = addr_hash.add(hash as usize);
    let mut cursor = (*head).next;

    while cursor != head {
        let candidate = pagealloc_track_addr_from_hash(cursor);
        if (*candidate).addr == ptr {
            addr_entry = candidate;
            break;
        }
        cursor = (*cursor).next;
    }

    if !addr_entry.is_null() {
        if npages > (*addr_entry).npages {
            unlock(addr_lock as CULong, irq_flags);
            if let Some(invalid_size) = invalid_size_fn {
                invalid_size(ptr, npages, (*addr_entry).npages, file, line);
            }
            return -EINVAL;
        }

        if (*addr_entry).npages > npages {
            (*addr_entry).addr = ((ptr as usize).wrapping_add(free_bytes)) as *mut c_void;
            (*addr_entry).npages -= npages;
            if (*addr_entry).npages != 0 {
                rehash_addr_entry = true;
            }
        }
        list_del(&raw mut (*addr_entry).hash);
    }
    unlock(addr_lock as CULong, irq_flags);

    if addr_entry.is_null() {
        let mut scan_hash = 0;
        while scan_hash <= PAGEALLOC_TRACK_HASH_MASK {
            let scan_lock = addr_locks.add(scan_hash as usize);
            let irq_flags = lock(scan_lock as CULong);
            let head = addr_hash.add(scan_hash as usize);
            let mut node = (*head).next;
            while node != head {
                let candidate = pagealloc_track_addr_from_hash(node);
                let candidate_start = (*candidate).addr as usize;
                let candidate_end =
                    candidate_start.wrapping_add(((*candidate).npages as usize) << PAGE_SHIFT);
                if candidate_start < free_start && candidate_end >= free_end {
                    addr_entry = candidate;
                    break;
                }
                node = (*node).next;
            }
            if !addr_entry.is_null() {
                list_del(&raw mut (*addr_entry).hash);
            }
            unlock(scan_lock as CULong, irq_flags);
            if !addr_entry.is_null() {
                break;
            }
            scan_hash += 1;
        }

        if addr_entry.is_null() {
            if let Some(invalid_free) = invalid_free_fn {
                invalid_free(ptr, file, line);
            }
            return -EINVAL;
        }

        pagealloc_track_log(
            log_fn,
            PAGEALLOC_TRACK_LOG_COVERING_FOUND,
            (*addr_entry).addr,
            file,
            line,
            (*addr_entry).npages,
        );

        let entry = (*addr_entry).entry;
        let old_start = (*addr_entry).addr as usize;
        let old_end = old_start.wrapping_add(((*addr_entry).npages as usize) << PAGE_SHIFT);
        if free_end < old_end {
            let addr_entry_next = meta_alloc(
                size_of::<PageallocTrackAddrEntry>() as CInt,
                IHK_MC_AP_NOWAIT,
            )
            .cast::<PageallocTrackAddrEntry>();
            if addr_entry_next.is_null() {
                pagealloc_track_log(
                    log_fn,
                    PAGEALLOC_TRACK_LOG_ADDR_ALLOC_FAILED,
                    ptr,
                    file,
                    line,
                    npages,
                );
                base_free(ptr, npages, is_user);
                return -EINVAL;
            }

            (*addr_entry_next).addr = free_end as *mut c_void;
            (*addr_entry_next).npages = ((old_end - free_end) >> PAGE_SHIFT) as CInt;
            (*addr_entry_next).runcount = (*addr_entry).runcount;
            (*addr_entry_next).entry = entry;
            init_list_head(&raw mut (*addr_entry_next).list);
            init_list_head(&raw mut (*addr_entry_next).hash);
            pagealloc_rehash_addr_entry(addr_entry_next, addr_hash, addr_locks, lock, unlock);
            pagealloc_track_entry_alloc_count(entry).fetch_add(1, Ordering::Relaxed);

            if let (Some(noirq_lock), Some(noirq_unlock)) = (noirq_lock_fn, noirq_unlock_fn) {
                let lock_addr = pagealloc_entry_addr_list_lock(entry);
                noirq_lock(lock_addr);
                list_add_after(
                    &raw mut (*addr_entry_next).list,
                    &raw mut (*entry).addr_list,
                );
                noirq_unlock(lock_addr);
            } else {
                let lock_addr = pagealloc_entry_addr_list_lock(entry);
                let irq_flags = lock(lock_addr);
                list_add_after(
                    &raw mut (*addr_entry_next).list,
                    &raw mut (*entry).addr_list,
                );
                unlock(lock_addr, irq_flags);
            }

            pagealloc_track_log(
                log_fn,
                PAGEALLOC_TRACK_LOG_ADDR_NEXT_ADDED,
                (*addr_entry_next).addr,
                file,
                line,
                (*addr_entry_next).npages,
            );
        }

        (*addr_entry).npages = ((free_start - old_start) >> PAGE_SHIFT) as CInt;
        rehash_addr_entry = true;
        pagealloc_track_log(
            log_fn,
            PAGEALLOC_TRACK_LOG_ADDR_MODIFIED,
            (*addr_entry).addr,
            file,
            line,
            (*addr_entry).npages,
        );
    }

    let entry = (*addr_entry).entry;
    if rehash_addr_entry {
        pagealloc_rehash_addr_entry(addr_entry, addr_hash, addr_locks, lock, unlock);
        base_free(ptr, npages, is_user);
        return 0;
    }

    let lock_addr = pagealloc_entry_addr_list_lock(entry);
    let irq_flags = lock(lock_addr);
    list_del(&raw mut (*addr_entry).list);
    unlock(lock_addr, irq_flags);
    pagealloc_track_log(
        log_fn,
        PAGEALLOC_TRACK_LOG_ADDR_REMOVED,
        (*addr_entry).addr,
        (*entry).file,
        (*entry).line,
        npages,
    );
    meta_free(addr_entry.cast::<c_void>());

    let hash = pagealloc_track_hash((*entry).file, (*entry).line);
    let track_lock = track_locks.add(hash as usize);
    let irq_flags = lock(track_lock as CULong);
    let old_count = pagealloc_track_entry_alloc_count(entry).fetch_sub(1, Ordering::Relaxed);
    if old_count != 1 {
        unlock(track_lock as CULong, irq_flags);
        base_free(ptr, npages, is_user);
        return 0;
    }

    list_del(&raw mut (*entry).hash);
    unlock(track_lock as CULong, irq_flags);
    pagealloc_track_log(
        log_fn,
        PAGEALLOC_TRACK_LOG_ENTRY_REMOVED,
        ptr,
        (*entry).file,
        (*entry).line,
        npages,
    );
    meta_free((*entry).file.cast::<c_void>());
    meta_free(entry.cast::<c_void>());
    base_free(ptr, npages, is_user);
    0
}

#[no_mangle]
pub unsafe extern "C" fn mem_track_hashes_init_result(
    initialized: *mut CInt,
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    hash_size: CInt,
    spin_init_fn: Option<MemPageallocSpinInitFn>,
) -> CInt {
    if initialized.is_null()
        || track_hash.is_null()
        || track_locks.is_null()
        || addr_hash.is_null()
        || addr_locks.is_null()
        || hash_size <= 0
    {
        return -EINVAL;
    }
    if *initialized != 0 {
        return 0;
    }
    let Some(spin_init) = spin_init_fn else {
        return -EINVAL;
    };

    *initialized = 1;
    let mut i = 0;
    while i < hash_size {
        spin_init(track_locks.add(i as usize) as CULong);
        init_list_head(track_hash.add(i as usize));
        spin_init(addr_locks.add(i as usize) as CULong);
        init_list_head(addr_hash.add(i as usize));
        i += 1;
    }

    1
}

#[inline(always)]
unsafe fn mem_track_leak_log(
    log_fn: Option<MemTrackLeakLogFn>,
    event: CInt,
    addr: *mut c_void,
    file: *mut i8,
    line: CInt,
    size: CInt,
    count: CInt,
    runcount: CInt,
) {
    if let Some(log) = log_fn {
        log(event, addr, file, line, size, count, runcount);
    }
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_memcheck_result(
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    runcount: *mut CInt,
    hash_size: CInt,
    lock_fn: Option<MemKmallocSpinLockFn>,
    unlock_fn: Option<MemKmallocSpinUnlockFn>,
    noirq_lock_fn: Option<MemPageallocNoirqLockFn>,
    noirq_unlock_fn: Option<MemPageallocNoirqUnlockFn>,
    log_fn: Option<MemTrackLeakLogFn>,
) -> CInt {
    if track_hash.is_null() || track_locks.is_null() || runcount.is_null() || hash_size <= 0 {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock), Some(noirq_lock), Some(noirq_unlock)) =
        (lock_fn, unlock_fn, noirq_lock_fn, noirq_unlock_fn)
    else {
        return -EINVAL;
    };

    let current_runcount = *runcount;
    let mut leak_entries = 0;
    let mut i = 0;
    while i < hash_size {
        let lock_addr = track_locks.add(i as usize) as CULong;
        let irq_flags = lock(lock_addr);
        let head = track_hash.add(i as usize);
        let mut node = (*head).next;

        while node != head {
            let entry = kmalloc_track_entry_from_hash(node);
            let addr_lock_addr = (&raw mut (*entry).addr_list_lock) as CULong;
            let mut count = 0;
            noirq_lock(addr_lock_addr);
            let mut addr_node = (*entry).addr_list.next;
            while addr_node != &raw mut (*entry).addr_list {
                let addr_entry = kmalloc_track_addr_from_list(addr_node);
                mem_track_leak_log(
                    log_fn,
                    MEM_TRACK_LEAK_DETAIL,
                    (*addr_entry).addr,
                    (*entry).file,
                    (*entry).line,
                    (*entry).size,
                    0,
                    (*addr_entry).runcount,
                );
                if (*addr_entry).runcount == current_runcount {
                    count += 1;
                }
                addr_node = (*addr_node).next;
            }
            noirq_unlock(addr_lock_addr);

            if count != 0 {
                leak_entries += 1;
                mem_track_leak_log(
                    log_fn,
                    MEM_TRACK_LEAK_SUMMARY,
                    null_mut(),
                    (*entry).file,
                    (*entry).line,
                    (*entry).size,
                    count,
                    current_runcount,
                );
            }

            node = (*node).next;
        }

        unlock(lock_addr, irq_flags);
        i += 1;
    }

    *runcount = current_runcount.wrapping_add(1);
    leak_entries
}

#[no_mangle]
pub unsafe extern "C" fn pagealloc_memcheck_result(
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    runcount: *mut CInt,
    hash_size: CInt,
    lock_fn: Option<MemKmallocSpinLockFn>,
    unlock_fn: Option<MemKmallocSpinUnlockFn>,
    noirq_lock_fn: Option<MemPageallocNoirqLockFn>,
    noirq_unlock_fn: Option<MemPageallocNoirqUnlockFn>,
    log_fn: Option<MemTrackLeakLogFn>,
) -> CInt {
    if track_hash.is_null() || track_locks.is_null() || runcount.is_null() || hash_size <= 0 {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock), Some(noirq_lock), Some(noirq_unlock)) =
        (lock_fn, unlock_fn, noirq_lock_fn, noirq_unlock_fn)
    else {
        return -EINVAL;
    };

    let current_runcount = *runcount;
    let mut leak_entries = 0;
    let mut i = 0;
    while i < hash_size {
        let lock_addr = track_locks.add(i as usize) as CULong;
        let irq_flags = lock(lock_addr);
        let head = track_hash.add(i as usize);
        let mut node = (*head).next;

        while node != head {
            let entry = pagealloc_track_entry_from_hash(node);
            let addr_lock_addr = pagealloc_entry_addr_list_lock(entry);
            let mut count = 0;
            noirq_lock(addr_lock_addr);
            let mut addr_node = (*entry).addr_list.next;
            while addr_node != &raw mut (*entry).addr_list {
                let addr_entry = pagealloc_track_addr_from_list(addr_node);
                mem_track_leak_log(
                    log_fn,
                    MEM_TRACK_LEAK_DETAIL,
                    (*addr_entry).addr,
                    (*entry).file,
                    (*entry).line,
                    0,
                    0,
                    (*addr_entry).runcount,
                );
                if (*addr_entry).runcount == current_runcount {
                    count += 1;
                }
                addr_node = (*addr_node).next;
            }
            noirq_unlock(addr_lock_addr);

            if count != 0 {
                leak_entries += 1;
                mem_track_leak_log(
                    log_fn,
                    MEM_TRACK_LEAK_SUMMARY,
                    null_mut(),
                    (*entry).file,
                    (*entry).line,
                    0,
                    count,
                    current_runcount,
                );
            }

            node = (*node).next;
        }

        unlock(lock_addr, irq_flags);
        i += 1;
    }

    *runcount = current_runcount.wrapping_add(1);
    leak_entries
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_consolidate_free_list_result(
    remote_free_list: *mut AbiListHead,
    free_list: *mut AbiListHead,
    remote_free_list_lock: *mut IhkSpinlock,
    lock_fn: Option<MemKmallocSpinLockFn>,
    unlock_fn: Option<MemKmallocSpinUnlockFn>,
) -> CInt {
    if remote_free_list.is_null() || free_list.is_null() || remote_free_list_lock.is_null() {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock)) = (lock_fn, unlock_fn) else {
        return -EINVAL;
    };

    let lock_addr = remote_free_list_lock as CULong;
    let irq_flags = lock(lock_addr);
    let mut moved = 0;

    while (*remote_free_list).next != remote_free_list {
        let node = (*remote_free_list).next;
        let chunk = list_to_kmalloc_header(node);
        list_del(node);
        ___kmalloc_insert_chunk_result(free_list, chunk);
        moved += 1;
    }

    ___kmalloc_consolidate_list_result(free_list);
    unlock(lock_addr, irq_flags);
    moved
}

#[no_mangle]
pub unsafe extern "C" fn mem_set_page_allocator_result(
    pa_ops_slot: *mut *mut IhkMcPaOps,
    ops: *mut IhkMcPaOps,
    pagealloc_track_init_fn: Option<MemVoidFn>,
    early_alloc_invalidate_fn: Option<MemVoidFn>,
) -> CInt {
    if pa_ops_slot.is_null() {
        return -EINVAL;
    }
    let (Some(pagealloc_track_init), Some(early_alloc_invalidate)) =
        (pagealloc_track_init_fn, early_alloc_invalidate_fn)
    else {
        return -EINVAL;
    };

    pagealloc_track_init();
    early_alloc_invalidate();
    *pa_ops_slot = ops;
    0
}

#[no_mangle]
pub unsafe extern "C" fn mem_register_kmalloc_result(
    allocator: *mut IhkMcPaOps,
    memdebug_present: CInt,
    debug_alloc_fn: Option<MemRegisterAllocFn>,
    debug_free_fn: Option<MemRegisterFreeFn>,
    base_alloc_fn: Option<MemRegisterAllocFn>,
    base_free_fn: Option<MemRegisterFreeFn>,
) -> CInt {
    if allocator.is_null() {
        return -EINVAL;
    }

    let (alloc_fn, free_fn) = if memdebug_present != 0 {
        let (Some(alloc_fn), Some(free_fn)) = (debug_alloc_fn, debug_free_fn) else {
            return -EINVAL;
        };
        (
            alloc_fn as usize as *mut c_void,
            free_fn as usize as *mut c_void,
        )
    } else {
        let (Some(alloc_fn), Some(free_fn)) = (base_alloc_fn, base_free_fn) else {
            return -EINVAL;
        };
        (
            alloc_fn as usize as *mut c_void,
            free_fn as usize as *mut c_void,
        )
    };

    (*allocator).alloc = alloc_fn;
    (*allocator).free = free_fn;
    0
}

#[no_mangle]
pub unsafe extern "C" fn mem_virtual_allocator_init_body_result(
    vmap_allocator_slot: *mut *mut c_void,
    start: CULong,
    size: CULong,
    unit: CULong,
    first_level: CInt,
    pagealloc_init_fn: Option<MemVmapInitFn>,
    pt_prepare_map_fn: Option<MemPtPrepareMapFn>,
) -> CInt {
    if vmap_allocator_slot.is_null() {
        return -EINVAL;
    }
    let (Some(pagealloc_init), Some(pt_prepare_map)) = (pagealloc_init_fn, pt_prepare_map_fn)
    else {
        return -EINVAL;
    };

    let allocator = pagealloc_init(start, size, unit);
    *vmap_allocator_slot = allocator;
    pt_prepare_map(null_mut(), start as *mut c_void, size, first_level)
}

#[no_mangle]
pub unsafe extern "C" fn mem_map_virtual_body_result(
    vmap_allocator: *mut c_void,
    phys: CULong,
    npages: CInt,
    attr: IhkMcPtAttribute,
    pagealloc_alloc_fn: Option<MemVmapAllocFn>,
    pt_set_page_fn: Option<MemPtSetPageFn>,
    pt_clear_page_fn: Option<MemPtClearPageFn>,
    pagealloc_free_fn: Option<MemVmapFreeFn>,
    flush_tlb_single_fn: Option<MemFlushTlbSingleFn>,
    barrier_fn: Option<MemVoidFn>,
) -> *mut c_void {
    if vmap_allocator.is_null() || npages < 0 {
        return null_mut();
    }
    let (
        Some(pagealloc_alloc),
        Some(pt_set_page),
        Some(pt_clear_page),
        Some(pagealloc_free),
        Some(flush_tlb_single),
        Some(barrier),
    ) = (
        pagealloc_alloc_fn,
        pt_set_page_fn,
        pt_clear_page_fn,
        pagealloc_free_fn,
        flush_tlb_single_fn,
        barrier_fn,
    )
    else {
        return null_mut();
    };

    let offset = phys & (PAGE_SIZE - 1);
    let aligned_phys = phys & PAGE_MASK;
    let va = pagealloc_alloc(vmap_allocator, npages, PAGE_P2ALIGN);
    if va == 0 {
        return null_mut();
    }

    let mut i: CInt = 0;
    while i < npages {
        let page_offset = (i as CULong) << PAGE_SHIFT;
        let page_va = va.wrapping_add(page_offset);
        let page_phys = aligned_phys.wrapping_add(page_offset);
        if pt_set_page(null_mut(), page_va as *mut c_void, page_phys, attr) != 0 {
            let mut j: CInt = 0;
            while j < i {
                let clear_va = va.wrapping_add((j as CULong) << PAGE_SHIFT);
                pt_clear_page(null_mut(), clear_va as *mut c_void);
                j += 1;
            }
            pagealloc_free(vmap_allocator, va, npages);
            return null_mut();
        }
        flush_tlb_single(page_va);
        i += 1;
    }

    barrier();
    va.wrapping_add(offset) as *mut c_void
}

#[no_mangle]
pub unsafe extern "C" fn mem_unmap_virtual_body_result(
    vmap_allocator: *mut c_void,
    va: *mut c_void,
    npages: CInt,
    pt_clear_page_fn: Option<MemPtClearPageFn>,
    flush_tlb_single_fn: Option<MemFlushTlbSingleFn>,
    pagealloc_free_fn: Option<MemVmapFreeFn>,
) -> CInt {
    if vmap_allocator.is_null() || va.is_null() || npages < 0 {
        return -EINVAL;
    }
    let (Some(pt_clear_page), Some(flush_tlb_single), Some(pagealloc_free)) =
        (pt_clear_page_fn, flush_tlb_single_fn, pagealloc_free_fn)
    else {
        return -EINVAL;
    };

    let base = (va as CULong) & PAGE_MASK;
    let mut i: CInt = 0;
    while i < npages {
        let page_va = base.wrapping_add((i as CULong) << PAGE_SHIFT);
        pt_clear_page(null_mut(), page_va as *mut c_void);
        flush_tlb_single(page_va);
        i += 1;
    }
    pagealloc_free(vmap_allocator, base, npages);
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_map_virtual(
    phys: CULong,
    npages: CInt,
    attr: IhkMcPtAttribute,
) -> *mut c_void {
    mem_map_virtual_body_result(
        mem_vmap_allocator_bridge(),
        phys,
        npages,
        attr,
        Some(mem_vmap_alloc_bridge),
        Some(mem_pt_set_page_bridge),
        Some(mem_pt_clear_page_bridge),
        Some(mem_vmap_free_bridge),
        Some(mem_flush_tlb_single_bridge),
        Some(mem_barrier_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_unmap_virtual(va: *mut c_void, npages: CInt) {
    let _ = mem_unmap_virtual_body_result(
        mem_vmap_allocator_bridge(),
        va,
        npages,
        Some(mem_pt_clear_page_bridge),
        Some(mem_flush_tlb_single_bridge),
        Some(mem_vmap_free_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn mem_rusage_init_body_result(
    rusage: *mut RusageGlobal,
    rusage_size: CULong,
    get_cpu_info_fn: Option<MemGetCpuInfoFn>,
    nr_numa_nodes_fn: Option<MemGetNrNumaNodesFn>,
    ns_per_tsc_fn: Option<MemGetNsPerTscFn>,
    virt_to_phys_fn: Option<MemVirtToPhysFn>,
    set_rusage_fn: Option<MemSetRusageFn>,
    panic_fn: Option<MemVoidFn>,
    log_fn: Option<MemRusageInitLogFn>,
) -> CInt {
    if rusage.is_null() {
        return -EINVAL;
    }
    let (Some(get_cpu_info), Some(nr_numa_nodes), Some(ns_per_tsc), Some(virt_to_phys)) = (
        get_cpu_info_fn,
        nr_numa_nodes_fn,
        ns_per_tsc_fn,
        virt_to_phys_fn,
    ) else {
        return -EINVAL;
    };
    let Some(set_rusage) = set_rusage_fn else {
        return -EINVAL;
    };

    let cpu_info = get_cpu_info();
    if cpu_info.is_null() {
        if let Some(panic) = panic_fn {
            panic();
        }
        return -EINVAL;
    }

    write_bytes(rusage, 0, 1);
    (*rusage).num_processors = (*cpu_info).n_cpus as CULong;
    (*rusage).num_numa_nodes = nr_numa_nodes() as CULong;
    (*rusage).ns_per_tsc = ns_per_tsc();

    let phys = virt_to_phys(rusage.cast::<c_void>());
    let rc = set_rusage(phys, rusage_size);
    if let Some(log) = log_fn {
        log((*rusage).total_memory);
    }
    rc
}

#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_init_body_result(
    memdebug_slot: *mut *mut i8,
    track_initialized: *mut CInt,
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    hash_size: CInt,
    get_this_cpu_local_var_fn: Option<MemGetThisCpuLocalVarFn>,
    register_kmalloc_fn: Option<MemVoidFn>,
    find_command_line_fn: Option<MemFindCommandLineFn>,
    spin_init_fn: Option<MemKmallocSpinInitFn>,
) -> CInt {
    if memdebug_slot.is_null() || track_initialized.is_null() {
        return -EINVAL;
    }
    let (Some(get_this_cpu_local_var), Some(register_kmalloc), Some(find_command_line)) = (
        get_this_cpu_local_var_fn,
        register_kmalloc_fn,
        find_command_line_fn,
    ) else {
        return -EINVAL;
    };
    let Some(spin_init) = spin_init_fn else {
        return -EINVAL;
    };

    let cpu_local = get_this_cpu_local_var();
    if cpu_local.is_null() {
        return -EINVAL;
    }

    register_kmalloc();
    init_list_head(&raw mut (*cpu_local).free_list);
    init_list_head(&raw mut (*cpu_local).remote_free_list);
    spin_init((&raw mut (*cpu_local).remote_free_list_lock) as CULong);
    (*cpu_local).kmalloc_initialized = 1;

    if *track_initialized == 0 {
        *memdebug_slot = find_command_line(b"memdebug\0".as_ptr().cast::<i8>().cast_mut());
        mem_track_hashes_init_result(
            track_initialized,
            track_hash,
            track_locks,
            addr_hash,
            addr_locks,
            hash_size,
            Some(spin_init),
        )
    } else {
        0
    }
}

#[inline(always)]
unsafe fn mem_init_check_command(
    flag: *mut CInt,
    name: *const u8,
    find_command_line: MemFindCommandLineFn,
    log_fn: Option<MemInitLogFn>,
    event: CInt,
) {
    if flag.is_null() {
        return;
    }
    if !find_command_line(name.cast::<i8>().cast_mut()).is_null() {
        *flag = 1;
        if let Some(log) = log_fn {
            log(event);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mem_init_sequence_result(
    allocator_ops: *mut IhkMcPaOps,
    page_fault_handler_addr: CULong,
    query_free_mem_handler_addr: CULong,
    anon_on_demand_flag: *mut CInt,
    xpmem_remote_flag: *mut CInt,
    hugetlbfs_on_demand_flag: *mut CInt,
    monitor_init_fn: Option<MemVoidFn>,
    rusage_init_fn: Option<MemVoidFn>,
    numa_init_fn: Option<MemVoidFn>,
    set_page_allocator_fn: Option<MemSetPageAllocatorFn>,
    set_page_fault_handler_fn: Option<MemSetPageFaultHandlerFn>,
    get_vector_fn: Option<MemGetVectorFn>,
    register_interrupt_handler_fn: Option<MemRegisterInterruptHandlerFn>,
    page_init_fn: Option<MemVoidFn>,
    virtual_allocator_init_fn: Option<MemVoidFn>,
    find_command_line_fn: Option<MemFindCommandLineFn>,
    numa_distances_init_fn: Option<MemVoidFn>,
    log_fn: Option<MemInitLogFn>,
) -> CInt {
    let (
        Some(monitor_init),
        Some(rusage_init),
        Some(numa_init),
        Some(set_page_allocator),
        Some(set_page_fault_handler),
        Some(get_vector),
        Some(register_interrupt_handler),
        Some(page_init),
        Some(virtual_allocator_init),
        Some(find_command_line),
        Some(numa_distances_init),
    ) = (
        monitor_init_fn,
        rusage_init_fn,
        numa_init_fn,
        set_page_allocator_fn,
        set_page_fault_handler_fn,
        get_vector_fn,
        register_interrupt_handler_fn,
        page_init_fn,
        virtual_allocator_init_fn,
        find_command_line_fn,
        numa_distances_init_fn,
    )
    else {
        return -EINVAL;
    };

    monitor_init();
    crate::x86_setup::early_phase(b'o');
    rusage_init();
    crate::x86_setup::early_phase(b'p');
    numa_init();
    crate::x86_setup::early_phase(b'q');
    set_page_allocator(allocator_ops);
    crate::x86_setup::early_phase(b'r');
    set_page_fault_handler(page_fault_handler_addr);
    crate::x86_setup::early_phase(b's');
    let vector = get_vector(IHK_GV_QUERY_FREE_MEM);
    let register_rc = register_interrupt_handler(vector, query_free_mem_handler_addr);
    crate::x86_setup::early_phase(b't');
    page_init();
    crate::x86_setup::early_phase(b'u');
    virtual_allocator_init();
    crate::x86_setup::early_phase(b'v');

    mem_init_check_command(
        anon_on_demand_flag,
        b"anon_on_demand\0".as_ptr(),
        find_command_line,
        log_fn,
        MEM_INIT_LOG_ANON_ON_DEMAND,
    );
    mem_init_check_command(
        xpmem_remote_flag,
        b"xpmem_page_in_remote_on_attach\0".as_ptr(),
        find_command_line,
        log_fn,
        MEM_INIT_LOG_XPMEM_PAGE_IN_REMOTE,
    );
    mem_init_check_command(
        hugetlbfs_on_demand_flag,
        b"hugetlbfs_on_demand\0".as_ptr(),
        find_command_line,
        log_fn,
        MEM_INIT_LOG_HUGETLBFS_ON_DEMAND,
    );
    crate::x86_setup::early_phase(b'w');

    numa_distances_init();
    crate::x86_setup::early_phase(b'x');
    register_rc
}

#[no_mangle]
pub unsafe extern "C" fn mem_init() {
    let _ = mem_init_sequence_result(
        mem_init_allocator_bridge(),
        mem_init_page_fault_handler_bridge(),
        mem_init_query_free_handler_bridge(),
        mem_init_anon_on_demand_bridge(),
        mem_init_xpmem_remote_bridge(),
        mem_init_hugetlbfs_on_demand_bridge(),
        Some(mem_monitor_init_bridge),
        Some(mem_rusage_init_bridge),
        Some(mem_numa_init_bridge),
        Some(ihk_mc_set_page_allocator),
        Some(mem_set_page_fault_handler_bridge),
        Some(mem_get_vector_bridge),
        Some(mem_register_interrupt_handler_bridge),
        Some(mem_page_init_bridge),
        Some(mem_virtual_allocator_init_bridge),
        Some(mem_find_command_line_bridge),
        Some(mem_numa_distances_init_bridge),
        Some(mem_init_log_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn mem_numa_init_body_result(
    memory_nodes: *mut MemNumaNode,
    nr_nodes: CInt,
    nr_chunks: CInt,
    rbtree_allocator: CInt,
    last_early_heap_phys: CULong,
    get_numa_node_fn: Option<MemGetNumaNodeInfoFn>,
    get_memory_chunk_fn: Option<MemGetMemoryChunkFn>,
    node_init_fn: Option<MemNumaNodeInitFn>,
    add_free_pages_fn: Option<MemNumaAddFreePagesFn>,
    page_allocator_init_fn: Option<MemPageAllocatorInitFn>,
    list_allocator_fn: Option<MemNumaListAllocatorFn>,
    pagealloc_count_fn: Option<MemPageallocCountFn>,
    rusage_total_add_fn: Option<MemRusageTotalAddFn>,
    log_fn: Option<MemNumaInitLogFn>,
    panic_fn: Option<MemNumaPanicFn>,
) -> CInt {
    if memory_nodes.is_null() || !(0..=512).contains(&nr_nodes) || nr_chunks < 0 {
        return -EINVAL;
    }

    let (Some(get_numa_node), Some(get_memory_chunk), Some(node_init), Some(rusage_total_add)) = (
        get_numa_node_fn,
        get_memory_chunk_fn,
        node_init_fn,
        rusage_total_add_fn,
    ) else {
        return -EINVAL;
    };

    let mut i = 0;
    while i < nr_nodes {
        let mut linux_numa_id: CInt = 0;
        let mut node_type: CInt = 0;
        if get_numa_node(i, &mut linux_numa_id, &mut node_type) != 0 {
            if let Some(panic) = panic_fn {
                panic(i);
            }
            return -EINVAL;
        }

        let node = memory_nodes.add(i as usize);
        (*node).id = i;
        (*node).linux_numa_id = linux_numa_id;
        (*node).node_type = node_type;
        init_list_head(&raw mut (*node).allocators);
        (*node).nodes_by_distance = null_mut();
        node_init(node, rbtree_allocator);
        i += 1;
    }

    let mut node_free_pages = [0 as CInt; 512];
    let mut chunk_index = 0;
    while chunk_index < nr_chunks {
        let mut start: CULong = 0;
        let mut end: CULong = 0;
        let mut numa_id: CInt = 0;

        get_memory_chunk(chunk_index, &mut start, &mut end, &mut numa_id);
        if numa_id < 0 || numa_id >= nr_nodes {
            chunk_index += 1;
            continue;
        }

        if last_early_heap_phys >= start && last_early_heap_phys < end {
            start = last_early_heap_phys;
        }
        if end < start {
            chunk_index += 1;
            continue;
        }

        let node = memory_nodes.add(numa_id as usize);
        let mut available_bytes = end.wrapping_sub(start);
        let mut available_pages = (available_bytes >> PAGE_SHIFT) as CInt;

        if rbtree_allocator != 0 {
            let Some(add_free_pages) = add_free_pages_fn else {
                return -EINVAL;
            };
            add_free_pages(node, start, available_bytes);
        } else {
            let (Some(page_allocator_init), Some(list_allocator), Some(pagealloc_count)) = (
                page_allocator_init_fn,
                list_allocator_fn,
                pagealloc_count_fn,
            ) else {
                return -EINVAL;
            };
            let allocator = page_allocator_init(start, end);
            if !allocator.is_null() {
                list_allocator(allocator, node);
                available_pages = pagealloc_count(allocator) as CInt;
                available_bytes = (available_pages as CULong).wrapping_mul(PAGE_SIZE);
            } else {
                available_pages = 0;
                available_bytes = 0;
            }
        }

        if let Some(log) = log_fn {
            log(
                MEM_NUMA_INIT_LOG_CHUNK,
                numa_id,
                (*node).linux_numa_id,
                (*node).node_type,
                start,
                end,
                available_bytes,
                available_pages,
                rbtree_allocator,
            );
        }
        let pages_slot = node_free_pages.as_mut_ptr().add(numa_id as usize);
        *pages_slot = (*pages_slot).wrapping_add(available_pages);
        rusage_total_add(available_bytes);
        chunk_index += 1;
    }

    i = 0;
    while i < nr_nodes {
        let node = memory_nodes.add(i as usize);
        let mut available_bytes: CULong = 0;
        let mut available_pages: CInt = *node_free_pages.as_ptr().add(i as usize);

        if rbtree_allocator != 0 {
            available_bytes = (available_pages as CULong).wrapping_mul(PAGE_SIZE);
        } else {
            available_pages = 0;
        }

        if let Some(log) = log_fn {
            log(
                MEM_NUMA_INIT_LOG_NODE,
                i,
                (*node).linux_numa_id,
                (*node).node_type,
                0,
                0,
                available_bytes,
                available_pages,
                rbtree_allocator,
            );
        }
        i += 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mem_numa_distances_init_result(
    memory_nodes: *mut MemNumaNode,
    nr_nodes: CInt,
    alloc_pages_fn: Option<MemNumaDistanceAllocFn>,
    get_distance_fn: Option<MemNumaDistanceFn>,
    alloc_fail_log_fn: Option<MemNumaDistanceAllocFailLogFn>,
    distances_log_fn: Option<MemNumaDistanceLogFn>,
) -> CInt {
    if memory_nodes.is_null() || nr_nodes < 0 {
        return -EINVAL;
    }

    let (Some(alloc_pages), Some(get_distance), Some(alloc_fail_log), Some(distances_log)) = (
        alloc_pages_fn,
        get_distance_fn,
        alloc_fail_log_fn,
        distances_log_fn,
    ) else {
        return -EINVAL;
    };

    let node_count = nr_nodes as usize;
    if node_count == 0 {
        return 0;
    }

    let bytes = size_of::<MemNodeDistance>() * node_count;
    let npages = ((bytes + PAGE_SIZE as usize - 1) >> PAGE_SHIFT) as CInt;

    for i in 0..node_count {
        let node = memory_nodes.add(i);
        let distances = alloc_pages(npages, IHK_MC_AP_NOWAIT);
        (*node).nodes_by_distance = distances;

        if distances.is_null() {
            alloc_fail_log(i as CInt);
            continue;
        }

        for j in 0..node_count {
            let entry = distances.add(j);
            (*entry).id = j as CInt;
            (*entry).distance = get_distance(i as CInt, j as CInt);
        }

        let mut swapped = true;
        while swapped {
            swapped = false;
            for j in 1..node_count {
                let prev = distances.add(j - 1);
                let cur = distances.add(j);
                let prev_distance = (*prev).distance;
                let cur_distance = (*cur).distance;
                if prev_distance > cur_distance
                    || (prev_distance == cur_distance && (*prev).id > (*cur).id)
                {
                    let tmp = *prev;
                    *prev = *cur;
                    *cur = tmp;
                    swapped = true;
                }
            }
        }

        distances_log(i as CInt, distances, nr_nodes);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mem_numa_distances_init_public_result(
    memory_nodes: *mut MemNumaNode,
    nr_nodes_fn: Option<MemGetNrNumaNodesFn>,
    alloc_pages_fn: Option<MemNumaDistanceAllocFn>,
    get_distance_fn: Option<MemNumaDistanceFn>,
    alloc_fail_log_fn: Option<MemNumaDistanceAllocFailLogFn>,
    distances_log_fn: Option<MemNumaDistanceLogFn>,
) -> CInt {
    let Some(nr_nodes) = nr_nodes_fn else {
        return -EINVAL;
    };

    mem_numa_distances_init_result(
        memory_nodes,
        nr_nodes(),
        alloc_pages_fn,
        get_distance_fn,
        alloc_fail_log_fn,
        distances_log_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn mem_try_alloc_node_result(
    memory_nodes: *mut MemNumaNode,
    nr_nodes: CInt,
    numa_id: CInt,
    npages: CInt,
    p2align: CInt,
    is_user: CInt,
    oomp: *mut CInt,
    rusage_check_oom_fn: Option<MemRusageCheckOomFn>,
    numa_alloc_fn: Option<MemNumaAllocNodeFn>,
) -> CULong {
    if !oomp.is_null() {
        *oomp = 0;
    }

    if memory_nodes.is_null() || numa_id < 0 || numa_id >= nr_nodes {
        return 0;
    }

    let (Some(rusage_check_oom), Some(numa_alloc)) = (rusage_check_oom_fn, numa_alloc_fn) else {
        return 0;
    };

    if rusage_check_oom(numa_id, npages, is_user) == -ENOMEM {
        if !oomp.is_null() {
            *oomp = 1;
        }
        return 0;
    }

    numa_alloc(memory_nodes.add(numa_id as usize), npages, p2align)
}

#[no_mangle]
pub unsafe extern "C" fn mem_try_alloc_node_public_result(
    memory_nodes: *mut MemNumaNode,
    numa_id: CInt,
    npages: CInt,
    p2align: CInt,
    is_user: CInt,
    oomp: *mut CInt,
    nr_nodes_fn: Option<MemGetNrNumaNodesFn>,
    rusage_check_oom_fn: Option<MemRusageCheckOomFn>,
    numa_alloc_fn: Option<MemNumaAllocNodeFn>,
) -> CULong {
    let Some(nr_nodes) = nr_nodes_fn else {
        if !oomp.is_null() {
            *oomp = 0;
        }
        return 0;
    };

    mem_try_alloc_node_result(
        memory_nodes,
        nr_nodes(),
        numa_id,
        npages,
        p2align,
        is_user,
        oomp,
        rusage_check_oom_fn,
        numa_alloc_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn mem_distance_id_result(
    memory_nodes: *mut MemNumaNode,
    nr_nodes: CInt,
    base_node: CInt,
    index: CInt,
) -> CInt {
    if memory_nodes.is_null()
        || base_node < 0
        || base_node >= nr_nodes
        || index < 0
        || index >= nr_nodes
    {
        return -1;
    }

    let distances = (*memory_nodes.add(base_node as usize)).nodes_by_distance;
    if distances.is_null() {
        return -1;
    }

    (*distances.add(index as usize)).id
}

#[no_mangle]
pub unsafe extern "C" fn mem_distance_id_public_result(
    memory_nodes: *mut MemNumaNode,
    base_node: CInt,
    index: CInt,
    nr_nodes_fn: Option<MemGetNrNumaNodesFn>,
) -> CInt {
    let Some(nr_nodes) = nr_nodes_fn else {
        return -1;
    };

    mem_distance_id_result(memory_nodes, nr_nodes(), base_node, index)
}

#[no_mangle]
pub unsafe extern "C" fn mem_get_numa_node_by_distance_result(
    memory_nodes: *mut MemNumaNode,
    nr_nodes: CInt,
    cpu_local_initialized: CInt,
    index: CInt,
    current_numa_id_fn: Option<MemCurrentNumaIdFn>,
) -> *mut MemNumaNode {
    if cpu_local_initialized == 0 || memory_nodes.is_null() || index < 0 || index >= nr_nodes {
        return null_mut();
    }

    let Some(current_numa_id) = current_numa_id_fn else {
        return null_mut();
    };

    let numa_id = current_numa_id();
    if numa_id < 0 || numa_id >= nr_nodes {
        return null_mut();
    }

    let distances = (*memory_nodes.add(numa_id as usize)).nodes_by_distance;
    if distances.is_null() {
        return null_mut();
    }

    let target_id = (*distances.add(index as usize)).id;
    if target_id < 0 || target_id >= nr_nodes {
        return null_mut();
    }

    memory_nodes.add(target_id as usize)
}

#[no_mangle]
pub unsafe extern "C" fn mem_get_numa_node_by_distance_public_result(
    memory_nodes: *mut MemNumaNode,
    cpu_local_initialized: CInt,
    index: CInt,
    nr_nodes_fn: Option<MemGetNrNumaNodesFn>,
    current_numa_id_fn: Option<MemCurrentNumaIdFn>,
) -> *mut MemNumaNode {
    let Some(nr_nodes) = nr_nodes_fn else {
        return null_mut();
    };

    mem_get_numa_node_by_distance_result(
        memory_nodes,
        nr_nodes(),
        cpu_local_initialized,
        index,
        current_numa_id_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn mem_get_numa_node_public_result(
    memory_nodes: *mut MemNumaNode,
    nr_nodes: CInt,
    numa_id: CInt,
) -> *mut MemNumaNode {
    if memory_nodes.is_null() || numa_id < 0 || numa_id >= nr_nodes {
        return null_mut();
    }

    memory_nodes.add(numa_id as usize)
}

#[no_mangle]
pub unsafe extern "C" fn mem_pa_alloc_aligned_pages_node_result(
    ops: *mut IhkMcPaOps,
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    node: CInt,
    is_user: CInt,
    virt_addr: CULong,
    early_alloc_pages: Option<MemEarlyAllocPagesFn>,
) -> *mut c_void {
    if !ops.is_null() {
        if let Some(alloc_page) = (*ops).alloc_page {
            return alloc_page(npages, p2align, flag, node, is_user, virt_addr);
        }
        return null_mut();
    }

    match early_alloc_pages {
        Some(early_alloc_pages) => early_alloc_pages(npages),
        None => null_mut(),
    }
}

#[no_mangle]
pub unsafe extern "C" fn ___ihk_mc_alloc_aligned_pages_node(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    node: CInt,
    is_user: CInt,
    virt_addr: CULong,
) -> *mut c_void {
    mem_pa_alloc_aligned_pages_node_result(
        MEM_PA_OPS,
        npages,
        p2align,
        flag,
        node,
        is_user,
        virt_addr,
        Some(early_alloc_pages),
    )
}

#[no_mangle]
pub unsafe extern "C" fn mem_pa_alloc_pages_result(
    ops: *mut IhkMcPaOps,
    npages: CInt,
    flag: CULong,
    is_user: CInt,
    early_alloc_pages: Option<MemEarlyAllocPagesFn>,
) -> *mut c_void {
    mem_pa_alloc_aligned_pages_node_result(
        ops,
        npages,
        PAGE_P2ALIGN,
        flag,
        -1,
        is_user,
        CULong::MAX,
        early_alloc_pages,
    )
}

#[no_mangle]
pub unsafe extern "C" fn ___ihk_mc_alloc_pages(
    npages: CInt,
    flag: CULong,
    is_user: CInt,
) -> *mut c_void {
    mem_pa_alloc_pages_result(MEM_PA_OPS, npages, flag, is_user, Some(early_alloc_pages))
}

#[inline(always)]
unsafe fn pagealloc_track_hash_ptr() -> *mut AbiListHead {
    (&raw mut PAGEALLOC_TRACK_HASH).cast::<AbiListHead>()
}

#[inline(always)]
unsafe fn pagealloc_track_locks_ptr() -> *mut IhkSpinlock {
    (&raw mut PAGEALLOC_TRACK_HASH_LOCKS).cast::<IhkSpinlock>()
}

#[inline(always)]
unsafe fn pagealloc_addr_hash_ptr() -> *mut AbiListHead {
    (&raw mut PAGEALLOC_ADDR_HASH).cast::<AbiListHead>()
}

#[inline(always)]
unsafe fn pagealloc_addr_locks_ptr() -> *mut IhkSpinlock {
    (&raw mut PAGEALLOC_ADDR_HASH_LOCKS).cast::<IhkSpinlock>()
}

#[no_mangle]
pub unsafe extern "C" fn pagealloc_track_init() {
    let _ = mem_track_hashes_init_result(
        &raw mut PAGEALLOC_TRACK_INITIALIZED,
        pagealloc_track_hash_ptr(),
        pagealloc_track_locks_ptr(),
        pagealloc_addr_hash_ptr(),
        pagealloc_addr_locks_ptr(),
        PAGEALLOC_TRACK_HASH_SIZE as CInt,
        Some(mem_pagealloc_track_spin_init_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn __pagealloc_track_find_entry(
    file: *mut i8,
    line: CInt,
) -> *mut PageallocTrackEntry {
    pagealloc_track_find_entry_result(file, line, pagealloc_track_hash_ptr())
}

#[no_mangle]
pub unsafe extern "C" fn _ihk_mc_alloc_aligned_pages_node(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    node: CInt,
    is_user: CInt,
    virt_addr: CULong,
    file: *mut i8,
    line: CInt,
) -> *mut c_void {
    pagealloc_track_alloc_result(
        npages,
        p2align,
        flag,
        node,
        is_user,
        virt_addr,
        file,
        line,
        MEMDEBUG,
        PAGEALLOC_TRACK_INITIALIZED,
        pagealloc_track_hash_ptr(),
        pagealloc_track_locks_ptr(),
        pagealloc_addr_hash_ptr(),
        pagealloc_addr_locks_ptr(),
        PAGEALLOC_RUNCOUNT,
        Some(mem_pagealloc_track_base_alloc_bridge),
        Some(mem_pagealloc_track_meta_alloc_bridge),
        Some(mem_pagealloc_track_meta_free_bridge),
        Some(mem_pagealloc_track_lock_bridge),
        Some(mem_pagealloc_track_unlock_bridge),
        Some(mem_pagealloc_track_spin_init_bridge),
        Some(mem_pagealloc_track_log_bridge),
    )
}

fn ihk_mm_wrapper_file() -> *mut i8 {
    IHK_MM_WRAPPER_FILE.as_ptr() as *mut i8
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_alloc_aligned_pages_node(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    node: CInt,
) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        p2align,
        flag,
        node,
        IHK_MC_PG_KERNEL,
        CULong::MAX,
        ihk_mm_wrapper_file(),
        line!() as CInt,
    )
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_alloc_aligned_pages_node_user(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    node: CInt,
    virt_addr: CULong,
) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        p2align,
        flag,
        node,
        IHK_MC_PG_USER,
        virt_addr,
        ihk_mm_wrapper_file(),
        line!() as CInt,
    )
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_alloc_aligned_pages(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        p2align,
        flag,
        -1,
        IHK_MC_PG_KERNEL,
        CULong::MAX,
        ihk_mm_wrapper_file(),
        line!() as CInt,
    )
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_alloc_aligned_pages_user(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    virt_addr: CULong,
) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        p2align,
        flag,
        -1,
        IHK_MC_PG_USER,
        virt_addr,
        ihk_mm_wrapper_file(),
        line!() as CInt,
    )
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_alloc_pages(npages: CInt, flag: CULong) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        PAGE_P2ALIGN,
        flag,
        -1,
        IHK_MC_PG_KERNEL,
        CULong::MAX,
        ihk_mm_wrapper_file(),
        line!() as CInt,
    )
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_alloc_pages_user(
    npages: CInt,
    flag: CULong,
    virt_addr: CULong,
) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        PAGE_P2ALIGN,
        flag,
        -1,
        IHK_MC_PG_USER,
        virt_addr,
        ihk_mm_wrapper_file(),
        line!() as CInt,
    )
}

#[no_mangle]
pub unsafe extern "C" fn mem_pa_free_pages_result(
    ops: *mut IhkMcPaOps,
    ptr: *mut c_void,
    npages: CInt,
    is_user: CInt,
) {
    if ops.is_null() {
        return;
    }
    if let Some(free_page) = (*ops).free_page {
        free_page(ptr, npages, is_user);
    }
}

#[no_mangle]
pub unsafe extern "C" fn mem_reserve_pages_body_result(
    pa_allocator: *mut c_void,
    allocator_start: CULong,
    allocator_end: CULong,
    mut start: CULong,
    mut end: CULong,
    log_fn: Option<MemReserveLogFn>,
    reserve_fn: Option<MemReserveRangeFn>,
) -> CInt {
    let (Some(log), Some(reserve)) = (log_fn, reserve_fn) else {
        return -EINVAL;
    };
    if pa_allocator.is_null() {
        return -EINVAL;
    }

    if start < allocator_start {
        start = allocator_start;
    }
    if end > allocator_end {
        end = allocator_end;
    }
    if start >= end {
        return 0;
    }

    unsafe {
        log(start, end, (end - start) >> PAGE_SHIFT);
        reserve(pa_allocator, start, end);
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn mem_reserve_pages_public_body_result(
    pa_allocator: *mut c_void,
    allocator_start: CULong,
    allocator_end: CULong,
    start: CULong,
    end: CULong,
    log_fn: Option<MemReserveLogFn>,
    reserve_fn: Option<MemReserveRangeFn>,
    reserve_body_fn: Option<MemReservePagesBodyFn>,
    panic_fn: Option<MemVoidFn>,
) -> CInt {
    let ret = if let Some(reserve_body) = reserve_body_fn {
        reserve_body(
            pa_allocator,
            allocator_start,
            allocator_end,
            start,
            end,
            log_fn,
            reserve_fn,
        )
    } else {
        -EINVAL
    };
    if ret < 0 {
        if let Some(panic) = panic_fn {
            panic();
        }
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn ___ihk_mc_free_pages(ptr: *mut c_void, npages: CInt, is_user: CInt) {
    mem_pa_free_pages_result(MEM_PA_OPS, ptr, npages, is_user);
}

#[no_mangle]
pub unsafe extern "C" fn _ihk_mc_free_pages(
    ptr: *mut c_void,
    npages: CInt,
    is_user: CInt,
    file: *mut i8,
    line: CInt,
) {
    let _ = pagealloc_track_free_result(
        ptr,
        npages,
        is_user,
        file,
        line,
        MEMDEBUG,
        PAGEALLOC_TRACK_INITIALIZED,
        pagealloc_track_hash_ptr(),
        pagealloc_track_locks_ptr(),
        pagealloc_addr_hash_ptr(),
        pagealloc_addr_locks_ptr(),
        Some(mem_pagealloc_track_base_free_bridge),
        Some(mem_pagealloc_track_meta_alloc_bridge),
        Some(mem_pagealloc_track_meta_free_bridge),
        Some(mem_pagealloc_track_lock_bridge),
        Some(mem_pagealloc_track_unlock_bridge),
        Some(mem_pagealloc_track_noirq_lock_bridge),
        Some(mem_pagealloc_track_noirq_unlock_bridge),
        Some(mem_pagealloc_invalid_free_bridge),
        Some(mem_pagealloc_invalid_size_bridge),
        Some(mem_pagealloc_track_log_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn pagealloc_memcheck() {
    let _ = pagealloc_memcheck_result(
        pagealloc_track_hash_ptr(),
        pagealloc_track_locks_ptr(),
        &raw mut PAGEALLOC_RUNCOUNT,
        PAGEALLOC_TRACK_HASH_SIZE as CInt,
        Some(mem_pagealloc_track_lock_bridge),
        Some(mem_pagealloc_track_unlock_bridge),
        Some(mem_pagealloc_track_noirq_lock_bridge),
        Some(mem_pagealloc_track_noirq_unlock_bridge),
        Some(mem_pagealloc_leak_log_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_free_pages(ptr: *mut c_void, npages: CInt) {
    _ihk_mc_free_pages(
        ptr,
        npages,
        IHK_MC_PG_KERNEL,
        ihk_mm_wrapper_file(),
        line!() as CInt,
    );
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_free_pages_user(ptr: *mut c_void, npages: CInt) {
    _ihk_mc_free_pages(
        ptr,
        npages,
        IHK_MC_PG_USER,
        ihk_mm_wrapper_file(),
        line!() as CInt,
    );
}

fn kmalloc_wrapper_file() -> *mut i8 {
    KMALLOC_WRAPPER_FILE.as_ptr() as *mut i8
}

#[inline(always)]
unsafe fn kmalloc_track_hash_ptr() -> *mut AbiListHead {
    (&raw mut KMALLOC_TRACK_HASH).cast::<AbiListHead>()
}

#[inline(always)]
unsafe fn kmalloc_track_locks_ptr() -> *mut IhkSpinlock {
    (&raw mut KMALLOC_TRACK_HASH_LOCKS).cast::<IhkSpinlock>()
}

#[inline(always)]
unsafe fn kmalloc_addr_hash_ptr() -> *mut AbiListHead {
    (&raw mut KMALLOC_ADDR_HASH).cast::<AbiListHead>()
}

#[inline(always)]
unsafe fn kmalloc_addr_locks_ptr() -> *mut IhkSpinlock {
    (&raw mut KMALLOC_ADDR_HASH_LOCKS).cast::<IhkSpinlock>()
}

#[no_mangle]
pub unsafe extern "C" fn __kmalloc_track_find_entry(
    size: CInt,
    file: *mut i8,
    line: CInt,
) -> *mut KmallocTrackEntry {
    kmalloc_track_find_entry_result(size, file, line, kmalloc_track_hash_ptr())
}

#[no_mangle]
pub unsafe extern "C" fn _kmalloc(
    size: CInt,
    flag: CULong,
    file: *mut i8,
    line: CInt,
) -> *mut c_void {
    kmalloc_track_alloc_result(
        size,
        flag,
        file,
        line,
        MEMDEBUG,
        kmalloc_track_hash_ptr(),
        kmalloc_track_locks_ptr(),
        kmalloc_addr_hash_ptr(),
        kmalloc_addr_locks_ptr(),
        KMALLOC_RUNCOUNT,
        Some(mem_kmalloc_track_base_alloc_bridge),
        Some(mem_kmalloc_track_base_free_bridge),
        Some(mem_kmalloc_track_lock_bridge),
        Some(mem_kmalloc_track_unlock_bridge),
        Some(mem_kmalloc_track_spin_init_bridge),
        Some(mem_kmalloc_track_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn _kfree(ptr: *mut c_void, file: *mut i8, line: CInt) {
    let _ = kmalloc_track_free_result(
        ptr,
        file,
        line,
        MEMDEBUG,
        kmalloc_track_hash_ptr(),
        kmalloc_track_locks_ptr(),
        kmalloc_addr_hash_ptr(),
        kmalloc_addr_locks_ptr(),
        Some(mem_kmalloc_track_base_free_bridge),
        Some(mem_kmalloc_track_lock_bridge),
        Some(mem_kmalloc_track_unlock_bridge),
        Some(mem_kmalloc_invalid_free_bridge),
        Some(mem_kmalloc_track_log_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_memcheck() {
    let _ = kmalloc_memcheck_result(
        kmalloc_track_hash_ptr(),
        kmalloc_track_locks_ptr(),
        &raw mut KMALLOC_RUNCOUNT,
        KMALLOC_TRACK_HASH_SIZE as CInt,
        Some(mem_kmalloc_track_lock_bridge),
        Some(mem_kmalloc_track_unlock_bridge),
        Some(mem_pagealloc_track_noirq_lock_bridge),
        Some(mem_pagealloc_track_noirq_unlock_bridge),
        Some(mem_kmalloc_leak_log_bridge),
    );
}

unsafe fn kmalloc_no_preempt_counter() -> CInt {
    let cpu = unsafe { get_this_cpu_local_var() };
    if cpu.is_null() {
        -1
    } else {
        unsafe { (*cpu).no_preempt.counter }
    }
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_tracked(
    size: CInt,
    flag: CULong,
    file: *mut i8,
    line: CInt,
) -> *mut c_void {
    let ptr = unsafe { _kmalloc(size, flag, file, line) };
    if ptr.is_null() {
        unsafe {
            kprintf(
                KMALLOC_OOM_FMT.as_ptr().cast::<i8>(),
                file,
                line,
                kmalloc_no_preempt_counter(),
            );
        }
    }
    ptr
}

#[no_mangle]
pub unsafe extern "C" fn kfree_tracked(ptr: *mut c_void, file: *mut i8, line: CInt) {
    unsafe {
        _kfree(ptr, file, line);
    }
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc(size: CInt, flag: CULong) -> *mut c_void {
    unsafe { kmalloc_tracked(size, flag, kmalloc_wrapper_file(), line!() as CInt) }
}

#[no_mangle]
pub unsafe extern "C" fn kfree(ptr: *mut c_void) {
    unsafe {
        kfree_tracked(ptr, kmalloc_wrapper_file(), line!() as CInt);
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_set_page_allocator(ops: *mut IhkMcPaOps) {
    pagealloc_track_init();
    early_alloc_invalidate();
    MEM_PA_OPS = ops;
}

#[no_mangle]
pub unsafe extern "C" fn mem_begin_free_pages_pending_result(pendings: *mut AbiListHead) -> CInt {
    if pendings.is_null() || !(*pendings).next.is_null() {
        return -EINVAL;
    }
    init_list_head(pendings);
    0
}

#[no_mangle]
pub unsafe extern "C" fn mem_begin_free_pages_pending_body_result(
    pendings: *mut AbiListHead,
    begin_fn: Option<MemBeginFreePagesPendingFn>,
    panic_fn: Option<MemVoidFn>,
) -> CInt {
    let ret = if let Some(begin) = begin_fn {
        begin(pendings)
    } else {
        -EINVAL
    };
    if ret != 0 {
        if let Some(panic) = panic_fn {
            panic();
        }
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn mem_begin_free_pages_pending_public_body_result(
    pending_pages_fn: Option<MemPendingPagesFn>,
    begin_fn: Option<MemBeginFreePagesPendingFn>,
    panic_fn: Option<MemVoidFn>,
) -> CInt {
    let Some(pending_pages) = pending_pages_fn else {
        if let Some(panic) = panic_fn {
            panic();
        }
        return -EINVAL;
    };

    let pendings = pending_pages();
    if pendings.is_null() {
        if let Some(panic) = panic_fn {
            panic();
        }
        return -EINVAL;
    }

    let ret = if let Some(begin) = begin_fn {
        begin(pendings)
    } else {
        -EINVAL
    };
    if ret != 0 {
        if let Some(panic) = panic_fn {
            panic();
        }
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn begin_free_pages_pending() {
    let _ = mem_begin_free_pages_pending_public_body_result(
        Some(mem_pending_free_pages_bridge),
        Some(mem_begin_free_pages_pending_result),
        Some(mem_begin_free_pages_pending_panic_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn mem_free_pages_pending_enqueue_result(
    page: *mut MemPage,
    pendings: *mut AbiListHead,
    npages: CInt,
    warn_fn: Option<MemPendingWarnFn>,
) -> CInt {
    if page.is_null() || pendings.is_null() {
        return 0;
    }

    if (*page).mode != PM_NONE {
        if let Some(warn) = warn_fn {
            warn((*page).phys);
        }
    }

    if (*pendings).next.is_null() {
        return 0;
    }

    (*page).mode = PM_PENDING_FREE;
    (*page).offset = npages as OffT;
    list_add_tail(&raw mut (*page).list, pendings);
    1
}

#[no_mangle]
pub unsafe extern "C" fn mem_finish_free_pages_pending_result(
    pendings: *mut AbiListHead,
    free_fn: Option<MemPendingFreeFn>,
) -> CInt {
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };
    if pendings.is_null() || (*pendings).next.is_null() {
        return 0;
    }

    // Preflight the whole live ring before unlinking or releasing a prefix.
    // This retains the existing caller obligation to own stable, live list
    // nodes exclusively. It does not acquire allocator extent authority or
    // exclude migration, interrupt producers, or callback reentry. Those need
    // an explicit owner/descriptor lease supplied by the production callers.
    if validate_pending_head(pendings).is_err() {
        return -EINVAL;
    }
    let mut checked_count: CInt = 0;
    let mut checked_entry = (*pendings).next;
    while checked_entry != pendings {
        let page = page_from_list(checked_entry);
        if (*page).offset <= 0 || (*page).offset > CInt::MAX as OffT
            || (*page).phys & (PAGE_SIZE - 1) != 0
        {
            return -EINVAL;
        }
        let Some(bytes) = ((*page).offset as CULong).checked_mul(PAGE_SIZE) else {
            return -EINVAL;
        };
        let Some(end) = (*page).phys.checked_add(bytes) else {
            return -EINVAL;
        };
        // Earlier extents have already passed the checked arithmetic above.
        // Reject aliases before either occurrence can reach the allocator.
        // This checks geometry only: addresses are not allocator ownership or
        // descriptor-generation evidence, and the caller still excludes edits.
        let mut previous = (*pendings).next;
        while previous != checked_entry {
            let other = page_from_list(previous);
            let other_end = (*other).phys + (*other).offset as CULong * PAGE_SIZE;
            if (*page).phys < other_end && (*other).phys < end {
                return -EINVAL;
            }
            previous = (*previous).next;
        }
        let Some(next_count) = checked_count.checked_add(1) else {
            return -EINVAL;
        };
        checked_count = next_count;
        checked_entry = (*checked_entry).next;
    }

    let mut count: CInt = 0;
    let mut entry = (*pendings).next;
    while entry != pendings {
        let next = (*entry).next;
        let page = page_from_list(entry);

        if (*page).mode != PM_PENDING_FREE {
            return -EINVAL;
        }

        (*page).mode = PM_NONE;
        list_del_poison(entry);
        free_fn((*page).phys, (*page).offset as CInt, IHK_MC_PG_USER);
        count += 1;
        entry = next;
    }

    write_volatile(&raw mut (*pendings).next, null_mut());
    write_volatile(&raw mut (*pendings).prev, null_mut());
    count
}

#[no_mangle]
pub unsafe extern "C" fn mem_finish_free_pages_pending_body_result(
    pendings: *mut AbiListHead,
    finish_fn: Option<MemFinishFreePagesPendingFn>,
    free_fn: Option<MemPendingFreeFn>,
    panic_fn: Option<MemVoidFn>,
) -> CInt {
    let ret = if let Some(finish) = finish_fn {
        finish(pendings, free_fn)
    } else {
        -EINVAL
    };
    if ret < 0 {
        if let Some(panic) = panic_fn {
            panic();
        }
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn mem_finish_free_pages_pending_public_body_result(
    pending_pages_fn: Option<MemPendingPagesFn>,
    finish_fn: Option<MemFinishFreePagesPendingFn>,
    free_fn: Option<MemPendingFreeFn>,
    panic_fn: Option<MemVoidFn>,
) -> CInt {
    let Some(pending_pages) = pending_pages_fn else {
        if let Some(panic) = panic_fn {
            panic();
        }
        return -EINVAL;
    };

    let pendings = pending_pages();
    if pendings.is_null() {
        if let Some(panic) = panic_fn {
            panic();
        }
        return -EINVAL;
    }

    let ret = if let Some(finish) = finish_fn {
        finish(pendings, free_fn)
    } else {
        -EINVAL
    };
    if ret < 0 {
        if let Some(panic) = panic_fn {
            panic();
        }
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn finish_free_pages_pending() {
    let _ = mem_finish_free_pages_pending_public_body_result(
        Some(mem_pending_free_pages_bridge),
        Some(mem_finish_free_pages_pending_result),
        Some(mem_pending_free_bridge),
        Some(mem_finish_free_pages_pending_panic_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn mem_free_pages_in_allocator_rbtree_result(
    va: *mut c_void,
    npages: CInt,
    is_user: CInt,
    get_nr_memory_chunks: Option<MemGetNrMemoryChunksFn>,
    get_memory_chunk: Option<MemGetMemoryChunkFn>,
    virt_to_phys_fn: Option<MemVirtToPhysFn>,
    get_numa_node: Option<MemGetNumaNodeFn>,
    numa_free: Option<MemNumaFreeFn>,
    rusage_sub: Option<MemRusageSubFn>,
) -> CInt {
    if npages <= 0 {
        return 0;
    }

    let Some(get_nr_memory_chunks) = get_nr_memory_chunks else {
        return 0;
    };
    let Some(get_memory_chunk) = get_memory_chunk else {
        return 0;
    };
    let Some(virt_to_phys_fn) = virt_to_phys_fn else {
        return 0;
    };
    let Some(get_numa_node) = get_numa_node else {
        return 0;
    };
    let Some(numa_free) = numa_free else {
        return 0;
    };
    let Some(rusage_sub) = rusage_sub else {
        return 0;
    };

    let pa_start = virt_to_phys_fn(va);
    let pa_end = pa_start.wrapping_add((npages as CULong) << PAGE_SHIFT);
    let nr_chunks = get_nr_memory_chunks();
    let mut i = 0;

    while i < nr_chunks {
        let mut start: CULong = 0;
        let mut end: CULong = 0;
        let mut numa_id: CInt = -1;

        get_memory_chunk(i, &mut start, &mut end, &mut numa_id);
        if !(start > pa_start || end < pa_end) {
            let node = get_numa_node(numa_id);
            if !node.is_null() {
                numa_free(node, pa_start, npages);
                rusage_sub(numa_id, npages, is_user);
                return 1;
            }
        }

        i += 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mem_mask_test_result(
    numa_id: CInt,
    numa_mask: *mut CULong,
    nr_bits: CInt,
) -> CInt {
    if numa_mask.is_null() || numa_id < 0 || nr_bits <= 0 || numa_id >= nr_bits {
        return 0;
    }

    let word_bits = (core::mem::size_of::<CULong>() * 8) as CInt;
    let word = unsafe { *numa_mask.add((numa_id / word_bits) as usize) };
    (((word >> (numa_id % word_bits)) & 1) != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn mem_interleave_nodes_result(
    off: CInt,
    numa_mask: *mut CULong,
    nr_bits: CInt,
) -> CInt {
    if numa_mask.is_null() || nr_bits <= 0 {
        return nr_bits;
    }

    let word_bits = (core::mem::size_of::<CULong>() * 8) as CInt;
    let bit_is_set = |bit: CInt| -> bool {
        let word = unsafe { *numa_mask.add((bit / word_bits) as usize) };
        ((word >> (bit % word_bits)) & 1) != 0
    };
    let start = if off < 0 {
        0
    } else if off >= nr_bits {
        nr_bits
    } else {
        off + 1
    };

    for bit in start..nr_bits {
        if bit_is_set(bit) {
            return bit;
        }
    }
    for bit in 0..nr_bits {
        if bit_is_set(bit) {
            return bit;
        }
    }

    nr_bits
}

#[no_mangle]
pub extern "C" fn mem_range_is_shm_result(
    has_range: CInt,
    has_memobj: CInt,
    memobj_flags: CULong,
) -> CInt {
    if has_range == 0 || has_memobj == 0 {
        return 0;
    }

    (memobj_flags == MF_SHM) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn mem_policy_fields_result(
    has_policy: CInt,
    policy: CInt,
    mask: *mut CULong,
    il_prev_in: *mut CInt,
    numa_mem_policy: *mut CInt,
    numa_mask: *mut *mut CULong,
    il_prev: *mut *mut CInt,
) -> CInt {
    if has_policy == 0 {
        return 0;
    }

    if !numa_mem_policy.is_null() {
        unsafe {
            *numa_mem_policy = policy;
        }
    }
    if !numa_mask.is_null() {
        unsafe {
            *numa_mask = mask;
        }
    }
    if !il_prev.is_null() {
        unsafe {
            *il_prev = il_prev_in;
        }
    }
    1
}

#[no_mangle]
pub extern "C" fn mem_current_vm_result(
    cpu_local_initialized: CInt,
    current: *mut c_void,
    vm: *mut c_void,
) -> *mut c_void {
    if cpu_local_initialized == 0 || current.is_null() {
        return null_mut();
    }

    vm
}

#[no_mangle]
pub unsafe extern "C" fn mem_default_alloc_policy_result(
    flag: CULong,
    policy_flag: *mut CULong,
    policy_pref_node: *mut CInt,
    numa_mem_policy: *mut CInt,
) -> CInt {
    if !numa_mem_policy.is_null() {
        unsafe {
            *numa_mem_policy = MPOL_DEFAULT;
        }
    }
    if !policy_pref_node.is_null() {
        unsafe {
            *policy_pref_node = -1;
        }
    }
    if !policy_flag.is_null() {
        unsafe {
            *policy_flag = flag & !IHK_MC_AP_USER;
        }
    }
    1
}

#[no_mangle]
pub extern "C" fn mem_alloc_policy_should_try_policy_result(
    pref_node: CInt,
    flag: CULong,
    numa_mem_policy: CInt,
    chk_shm: CInt,
) -> CInt {
    if pref_node == -1
        && (flag & IHK_MC_AP_USER) == 0
        && numa_mem_policy == MPOL_DEFAULT
        && chk_shm == 0
    {
        0
    } else {
        1
    }
}

#[no_mangle]
pub extern "C" fn mem_alloc_node_id_valid_result(node: CInt, nr_nodes: CInt) -> CInt {
    (node >= 0 && node < nr_nodes) as CInt
}

#[no_mangle]
pub extern "C" fn mem_alloc_policy_inputs_valid_result(
    npages: CInt,
    nr_nodes: CInt,
    has_try_alloc: CInt,
    has_rusage_add: CInt,
    has_phys_to_virt: CInt,
) -> CInt {
    (npages > 0
        && nr_nodes > 0
        && has_try_alloc != 0
        && has_rusage_add != 0
        && has_phys_to_virt != 0) as CInt
}

#[no_mangle]
pub extern "C" fn mem_alloc_order_node_result(
    current_node: CInt,
    offset: CInt,
    nr_nodes: CInt,
) -> CInt {
    if nr_nodes <= 0 {
        return -1;
    }

    (current_node + offset) % nr_nodes
}

#[inline(always)]
unsafe fn mem_try_alloc_node(
    try_alloc: MemTryAllocNodeFn,
    numa_id: CInt,
    npages: CInt,
    p2align: CInt,
    is_user: CInt,
) -> (CULong, bool) {
    let mut oom: CInt = 0;
    let pa = try_alloc(numa_id, npages, p2align, is_user, &mut oom);
    (pa, oom != 0)
}

#[inline(always)]
unsafe fn mem_finish_alloc(
    pa: CULong,
    current_node: CInt,
    numa_id: CInt,
    npages: CInt,
    is_user: CInt,
    event: CInt,
    rusage_add: MemRusageAddFn,
    phys_to_virt: MemPhysToVirtFn,
    log_fn: Option<MemAllocLogFn>,
) -> *mut c_void {
    rusage_add(numa_id, npages, is_user);
    if let Some(log_fn) = log_fn {
        log_fn(event, current_node, numa_id, npages);
    }
    phys_to_virt(pa)
}

#[no_mangle]
pub unsafe extern "C" fn mem_mckernel_alloc_policy_result(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    pref_node: CInt,
    is_user: CInt,
    current_node: CInt,
    nr_nodes: CInt,
    numa_mem_policy: CInt,
    chk_shm: CInt,
    numa_mask: *mut CULong,
    il_prevp: *mut CInt,
    try_alloc_fn: Option<MemTryAllocNodeFn>,
    distance_id_fn: Option<MemDistanceIdFn>,
    mask_test_fn: Option<MemMaskTestFn>,
    interleave_next_fn: Option<MemInterleaveNextFn>,
    rusage_add_fn: Option<MemRusageAddFn>,
    phys_to_virt_fn: Option<MemPhysToVirtFn>,
    log_fn: Option<MemAllocLogFn>,
) -> *mut c_void {
    if mem_alloc_policy_inputs_valid_result(
        npages,
        nr_nodes,
        try_alloc_fn.is_some() as CInt,
        rusage_add_fn.is_some() as CInt,
        phys_to_virt_fn.is_some() as CInt,
    ) == 0
    {
        return null_mut();
    }
    let (Some(try_alloc), Some(rusage_add), Some(phys_to_virt)) =
        (try_alloc_fn, rusage_add_fn, phys_to_virt_fn)
    else {
        return null_mut();
    };

    if mem_alloc_policy_should_try_policy_result(pref_node, flag, numa_mem_policy, chk_shm) != 0 {
        if mem_alloc_node_id_valid_result(pref_node, nr_nodes) != 0 {
            let (pa, _) = mem_try_alloc_node(try_alloc, pref_node, npages, p2align, is_user);
            if pa != 0 {
                return mem_finish_alloc(
                    pa,
                    current_node,
                    pref_node,
                    npages,
                    is_user,
                    MEM_ALLOC_LOG_EXPLICIT_OK,
                    rusage_add,
                    phys_to_virt,
                    log_fn,
                );
            }
            if let Some(log_fn) = log_fn {
                log_fn(MEM_ALLOC_LOG_EXPLICIT_MISS, current_node, pref_node, npages);
            }
        }

        let mut policy_pa: CULong = 0;
        let mut policy_numa: CInt = -1;

        match numa_mem_policy {
            MPOL_BIND | MPOL_PREFERRED => {
                if let (Some(distance_id), Some(mask_test)) = (distance_id_fn, mask_test_fn) {
                    if !numa_mask.is_null() {
                        let mut i = 0;
                        while i < nr_nodes {
                            let numa_id = distance_id(current_node, i);
                            if mem_alloc_node_id_valid_result(numa_id, nr_nodes) != 0
                                && mask_test(numa_id, numa_mask) != 0
                            {
                                let (pa, _) = mem_try_alloc_node(
                                    try_alloc, numa_id, npages, p2align, is_user,
                                );
                                if pa != 0 {
                                    policy_pa = pa;
                                    policy_numa = numa_id;
                                    break;
                                }
                            }
                            i += 1;
                        }
                    }
                }
            }
            MPOL_INTERLEAVE => {
                if let Some(interleave_next) = interleave_next_fn {
                    if !numa_mask.is_null() && !il_prevp.is_null() {
                        let il_start = *il_prevp;
                        let mut looping = false;
                        let mut attempts = 0;
                        while attempts <= nr_nodes {
                            let numa_id = interleave_next(*il_prevp, numa_mask);
                            let mut oom = false;
                            *il_prevp = numa_id;

                            if il_start == *il_prevp && looping {
                                policy_pa = 0;
                                break;
                            }
                            looping = true;

                            if numa_id >= 0 && numa_id < nr_nodes {
                                let result = mem_try_alloc_node(
                                    try_alloc, numa_id, npages, p2align, is_user,
                                );
                                policy_pa = result.0;
                                oom = result.1;
                                if policy_pa != 0 {
                                    policy_numa = numa_id;
                                    break;
                                }
                            }

                            if !oom {
                                break;
                            }
                            attempts += 1;
                        }
                    }
                }
            }
            _ => {}
        }

        if policy_pa != 0 {
            return mem_finish_alloc(
                policy_pa,
                current_node,
                policy_numa,
                npages,
                is_user,
                MEM_ALLOC_LOG_POLICY_OK,
                rusage_add,
                phys_to_virt,
                log_fn,
            );
        }
        if let Some(log_fn) = log_fn {
            log_fn(MEM_ALLOC_LOG_POLICY_MISS, current_node, -1, npages);
        }
    }

    if let Some(distance_id) = distance_id_fn {
        let mut i = 0;
        while i < nr_nodes {
            let numa_id = distance_id(current_node, i);
            if mem_alloc_node_id_valid_result(numa_id, nr_nodes) != 0 {
                let (pa, _) = mem_try_alloc_node(try_alloc, numa_id, npages, p2align, is_user);
                if pa != 0 {
                    return mem_finish_alloc(
                        pa,
                        current_node,
                        numa_id,
                        npages,
                        is_user,
                        MEM_ALLOC_LOG_DISTANCE_OK,
                        rusage_add,
                        phys_to_virt,
                        log_fn,
                    );
                }
                if i == 0 {
                    if let Some(log_fn) = log_fn {
                        log_fn(
                            MEM_ALLOC_LOG_DISTANCE_FIRST_MISS,
                            current_node,
                            numa_id,
                            npages,
                        );
                    }
                }
            }
            i += 1;
        }
    }

    let mut i = 0;
    while i < nr_nodes {
        let numa_id = mem_alloc_order_node_result(current_node, i, nr_nodes);
        let (pa, _) = mem_try_alloc_node(try_alloc, numa_id, npages, p2align, is_user);
        if pa != 0 {
            return mem_finish_alloc(
                pa,
                current_node,
                numa_id,
                npages,
                is_user,
                0,
                rusage_add,
                phys_to_virt,
                None,
            );
        }
        i += 1;
    }

    if let Some(log_fn) = log_fn {
        log_fn(MEM_ALLOC_LOG_OOM, current_node, -1, npages);
    }
    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn mem_mckernel_allocate_aligned_pages_node_body_result(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    pref_node: CInt,
    is_user: CInt,
    virt_addr: CULong,
    cpu_local_initialized: CInt,
    nr_nodes: CInt,
    current_vm_fn: Option<MemCurrentVmFn>,
    range_policy_search_fn: Option<MemRangePolicySearchFn>,
    lookup_memory_range_fn: Option<MemLookupMemoryRangeFn>,
    range_is_shm_fn: Option<MemRangeIsShmFn>,
    range_policy_fields_fn: Option<MemPolicyFieldsFn>,
    vm_policy_fields_fn: Option<MemPolicyFieldsFn>,
    current_numa_id_fn: Option<MemCurrentNumaIdFn>,
    alloc_policy_fn: Option<MemMckernelAllocPolicyFn>,
) -> *mut c_void {
    if npages <= 0 {
        return null_mut();
    }

    let (Some(current_numa_id), Some(alloc_policy)) = (current_numa_id_fn, alloc_policy_fn) else {
        return null_mut();
    };

    let mut numa_mem_policy: CInt = -1;
    let mut chk_shm: CInt = 0;
    let mut numa_mask: *mut CULong = null_mut();
    let mut il_prev: *mut CInt = null_mut();
    let mut policy_pref_node = pref_node;
    let mut policy_flag = flag;

    let vm = if cpu_local_initialized != 0 {
        if let Some(current_vm) = current_vm_fn {
            current_vm()
        } else {
            null_mut()
        }
    } else {
        null_mut()
    };

    if vm.is_null() {
        unsafe {
            mem_default_alloc_policy_result(
                flag,
                &mut policy_flag,
                &mut policy_pref_node,
                &mut numa_mem_policy,
            );
        }
    } else if virt_addr != MEM_VIRT_ADDR_NONE {
        let range_policy = if let Some(search) = range_policy_search_fn {
            search(vm, virt_addr)
        } else {
            null_mut()
        };

        if !range_policy.is_null() {
            if let Some(lookup) = lookup_memory_range_fn {
                let range = lookup(vm, virt_addr, virt_addr.wrapping_add(1));
                if !range.is_null() {
                    if let Some(is_shm) = range_is_shm_fn {
                        chk_shm = is_shm(range);
                    }
                }
            }
            if let Some(fields) = range_policy_fields_fn {
                fields(
                    range_policy,
                    &mut numa_mem_policy,
                    &mut numa_mask,
                    &mut il_prev,
                );
            }
        } else if let Some(fields) = vm_policy_fields_fn {
            fields(vm, &mut numa_mem_policy, &mut numa_mask, &mut il_prev);
        }
    }

    let current_node = current_numa_id();
    alloc_policy(
        npages,
        p2align,
        policy_flag,
        policy_pref_node,
        is_user,
        current_node,
        nr_nodes,
        numa_mem_policy,
        chk_shm,
        numa_mask,
        il_prev,
    )
}

#[no_mangle]
pub unsafe extern "C" fn mem_mckernel_allocate_aligned_pages_node_public_body_result(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    pref_node: CInt,
    is_user: CInt,
    virt_addr: CULong,
    cpu_local_initialized: CInt,
    nr_nodes_fn: Option<MemGetNrNumaNodesFn>,
    current_vm_fn: Option<MemCurrentVmFn>,
    range_policy_search_fn: Option<MemRangePolicySearchFn>,
    lookup_memory_range_fn: Option<MemLookupMemoryRangeFn>,
    range_is_shm_fn: Option<MemRangeIsShmFn>,
    range_policy_fields_fn: Option<MemPolicyFieldsFn>,
    vm_policy_fields_fn: Option<MemPolicyFieldsFn>,
    current_numa_id_fn: Option<MemCurrentNumaIdFn>,
    alloc_policy_fn: Option<MemMckernelAllocPolicyFn>,
) -> *mut c_void {
    let Some(nr_nodes) = nr_nodes_fn else {
        return null_mut();
    };

    mem_mckernel_allocate_aligned_pages_node_body_result(
        npages,
        p2align,
        flag,
        pref_node,
        is_user,
        virt_addr,
        cpu_local_initialized,
        nr_nodes(),
        current_vm_fn,
        range_policy_search_fn,
        lookup_memory_range_fn,
        range_is_shm_fn,
        range_policy_fields_fn,
        vm_policy_fields_fn,
        current_numa_id_fn,
        alloc_policy_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn mem_mckernel_free_pages_body_result(
    va: *mut c_void,
    npages: CInt,
    is_user: CInt,
    pendings: *mut AbiListHead,
    virt_to_phys_fn: Option<MemVirtToPhysFn>,
    phys_to_page_fn: Option<MemPhysToPageFn>,
    free_in_allocator_fn: Option<MemFreeInAllocatorFn>,
    warn_fn: Option<MemPendingWarnFn>,
) -> CInt {
    let (Some(virt_to_phys), Some(phys_to_page), Some(free_in_allocator)) =
        (virt_to_phys_fn, phys_to_page_fn, free_in_allocator_fn)
    else {
        return -EINVAL;
    };

    let page = phys_to_page(virt_to_phys(va));
    if mem_free_pages_pending_enqueue_result(page, pendings, npages, warn_fn) != 0 {
        return 1;
    }

    free_in_allocator(va, npages, is_user);
    0
}

#[no_mangle]
pub unsafe extern "C" fn mem_mckernel_free_pages_public_body_result(
    va: *mut c_void,
    npages: CInt,
    is_user: CInt,
    pending_pages_fn: Option<MemPendingPagesFn>,
    virt_to_phys_fn: Option<MemVirtToPhysFn>,
    phys_to_page_fn: Option<MemPhysToPageFn>,
    free_in_allocator_fn: Option<MemFreeInAllocatorFn>,
    warn_fn: Option<MemPendingWarnFn>,
    free_body_fn: Option<MemMckernelFreePagesBodyFn>,
) -> CInt {
    let (Some(pending_pages), Some(free_body)) = (pending_pages_fn, free_body_fn) else {
        return -EINVAL;
    };

    let pendings = pending_pages();
    if pendings.is_null() {
        return -EINVAL;
    }

    free_body(
        va,
        npages,
        is_user,
        pendings,
        virt_to_phys_fn,
        phys_to_page_fn,
        free_in_allocator_fn,
        warn_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn mem_query_free_mem_interrupt_body_result(
    nr_nodes: CInt,
    memdebug_name: *mut i8,
    fugaku_panic: CInt,
    attached_mic: CInt,
    sbox_scratch0: CInt,
    sbox_scratch1: CInt,
    node_pages_fn: Option<MemQueryFreeNodePagesFn>,
    total_log_fn: Option<MemQueryFreeLogFn>,
    panic_fn: Option<MemVoidFn>,
    find_command_line_fn: Option<MemFindCommandLineFn>,
    kmalloc_memcheck_fn: Option<MemVoidFn>,
    pagealloc_memcheck_fn: Option<MemVoidFn>,
    page_hash_count_fn: Option<MemQueryPageHashCountFn>,
    page_hash_log_fn: Option<MemQueryFreeLogFn>,
    sbox_write_fn: Option<MemQuerySboxWriteFn>,
) -> CInt {
    if nr_nodes < 0 {
        return -EINVAL;
    }
    let Some(node_pages) = node_pages_fn else {
        return -EINVAL;
    };

    let mut pages: CInt = 0;
    let mut i: CInt = 0;
    while i < nr_nodes {
        pages = pages.wrapping_add(node_pages(i));
        i += 1;
    }

    if let Some(total_log) = total_log_fn {
        total_log(pages);
    }

    if fugaku_panic != 0 {
        if let Some(panic_fn) = panic_fn {
            panic_fn();
        }
    }

    if !memdebug_name.is_null() {
        if let Some(find_command_line) = find_command_line_fn {
            if !find_command_line(memdebug_name).is_null() {
                if let Some(kmalloc_memcheck) = kmalloc_memcheck_fn {
                    kmalloc_memcheck();
                }
                if let Some(pagealloc_memcheck) = pagealloc_memcheck_fn {
                    pagealloc_memcheck();
                }
            }
        }
    }

    if let (Some(page_hash_count), Some(page_hash_log)) = (page_hash_count_fn, page_hash_log_fn) {
        page_hash_log(page_hash_count());
    }

    if attached_mic != 0 {
        if let Some(sbox_write) = sbox_write_fn {
            sbox_write(sbox_scratch0, pages as u32);
            sbox_write(sbox_scratch1, 1);
        }
    }

    pages
}

#[no_mangle]
pub unsafe extern "C" fn mem_query_free_mem_interrupt_public_body_result(
    priv_arg: *mut c_void,
    nr_nodes_fn: Option<MemGetNrNumaNodesFn>,
    memdebug_name: *mut i8,
    fugaku_panic: CInt,
    attached_mic: CInt,
    sbox_scratch0: CInt,
    sbox_scratch1: CInt,
    node_pages_fn: Option<MemQueryFreeNodePagesFn>,
    total_log_fn: Option<MemQueryFreeLogFn>,
    panic_fn: Option<MemVoidFn>,
    find_command_line_fn: Option<MemFindCommandLineFn>,
    kmalloc_memcheck_fn: Option<MemVoidFn>,
    pagealloc_memcheck_fn: Option<MemVoidFn>,
    page_hash_count_fn: Option<MemQueryPageHashCountFn>,
    page_hash_log_fn: Option<MemQueryFreeLogFn>,
    sbox_write_fn: Option<MemQuerySboxWriteFn>,
) -> CInt {
    let _ = priv_arg;
    let Some(nr_nodes) = nr_nodes_fn else {
        return -EINVAL;
    };

    mem_query_free_mem_interrupt_body_result(
        nr_nodes(),
        memdebug_name,
        fugaku_panic,
        attached_mic,
        sbox_scratch0,
        sbox_scratch1,
        node_pages_fn,
        total_log_fn,
        panic_fn,
        find_command_line_fn,
        kmalloc_memcheck_fn,
        pagealloc_memcheck_fn,
        page_hash_count_fn,
        page_hash_log_fn,
        sbox_write_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn is_mckernel_memory(start: CULong, end: CULong) -> CInt {
    let mut i = 0;
    let nr_chunks = ihk_mc_get_nr_memory_chunks();

    while i < nr_chunks {
        let mut chunk_start: CULong = 0;
        let mut chunk_end: CULong = 0;
        let mut numa_id: CInt = 0;

        ihk_mc_get_memory_chunk(i, &mut chunk_start, &mut chunk_end, &mut numa_id);
        if chunk_start <= start && start < chunk_end && chunk_start <= end && end <= chunk_end {
            return 1;
        }
        i += 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn phys_to_nid(p: CULong) -> CInt {
    let mut i = 0;
    let nr_chunks = ihk_mc_get_nr_memory_chunks();

    while i < nr_chunks {
        let mut start: CULong = 0;
        let mut end: CULong = 0;
        let mut numa_id: CInt = -1;

        ihk_mc_get_memory_chunk(i, &mut start, &mut end, &mut numa_id);
        if p >= start && p < end {
            return numa_id;
        }
        i += 1;
    }

    -1
}

#[inline(always)]
unsafe fn mem_vm_page_table(
    vm: *mut c_void,
    address_space_offset: CULong,
    page_table_offset: CULong,
) -> *mut c_void {
    if vm.is_null() {
        return null_mut();
    }

    let address_space = *(vm
        .cast::<u8>()
        .add(address_space_offset as usize)
        .cast::<*mut c_void>());
    if address_space.is_null() {
        return null_mut();
    }

    *(address_space
        .cast::<u8>()
        .add(page_table_offset as usize)
        .cast::<*mut c_void>())
}

#[no_mangle]
pub unsafe extern "C" fn mem_pt_lookup_fault_pte_body_result(
    vm: *mut c_void,
    virt: *mut c_void,
    pgshift: CInt,
    basep: *mut *mut c_void,
    sizep: *mut usize,
    p2alignp: *mut CInt,
    address_space_offset: CULong,
    page_table_offset: CULong,
    lookup_pte_fn: Option<MemLookupPteFn>,
    page_fault_fn: Option<MemPageFaultProcessVmFn>,
    log_fn: Option<MemFaultLogFn>,
) -> *mut CULong {
    let (Some(lookup_pte), Some(page_fault)) = (lookup_pte_fn, page_fault_fn) else {
        return null_mut();
    };

    let page_table = mem_vm_page_table(vm, address_space_offset, page_table_offset);
    if page_table.is_null() {
        return null_mut();
    }

    let mut ptep = lookup_pte(page_table, virt, pgshift, basep, sizep, p2alignp);
    if ptep.is_null() || (*ptep & PTATTR_ACTIVE) == 0 {
        page_fault(vm, virt, PF_POPULATE | PF_USER);
        ptep = lookup_pte(page_table, virt, pgshift, basep, sizep, p2alignp);
        if !ptep.is_null() && (*ptep & PTATTR_ACTIVE) != 0 {
            if let Some(log) = log_fn {
                log(virt);
            }
        }
    }

    ptep
}

#[no_mangle]
pub unsafe extern "C" fn mem_lookup_node_body_result(
    vm: *mut c_void,
    addr: *mut c_void,
    address_space_offset: CULong,
    page_table_offset: CULong,
    lookup_pte_fn: Option<MemLookupPteFn>,
    page_fault_fn: Option<MemPageFaultProcessVmFn>,
    phys_to_nid_fn: Option<MemPhysToNidFn>,
) -> CInt {
    let (Some(lookup_pte), Some(page_fault), Some(phys_to_nid_cb)) =
        (lookup_pte_fn, page_fault_fn, phys_to_nid_fn)
    else {
        return -EINVAL;
    };

    let err = page_fault(vm, addr, PF_POPULATE | PF_USER);
    if err != 0 {
        return err;
    }

    let page_table = mem_vm_page_table(vm, address_space_offset, page_table_offset);
    if page_table.is_null() {
        return -ENOENT;
    }

    let ptep = lookup_pte(page_table, addr, 0, null_mut(), null_mut(), null_mut());
    if ptep.is_null() || (*ptep & PTATTR_ACTIVE) == 0 {
        return -ENOENT;
    }

    phys_to_nid_cb(*ptep & PT_PHYSMASK)
}

/// Exact TLB target-selection provider: preserve the current public CPU ABI.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_current_cpu_bridge() -> CInt {
    unsafe { ihk_mc_get_processor_id() }
}

/// Exact public vector translation, including every signed type/result bit.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_get_vector_bridge(type_: CInt) -> CInt {
    unsafe { ihk_mc_get_vector(type_) }
}

/// Preserve one interrupt call and the original void/ignored-result contract.
/// No completion/ACK is inferred from the public provider's return value.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_interrupt_cpu_bridge(cpu: CInt, vector: CInt) {
    let _ = unsafe { ihk_mc_interrupt_cpu(cpu, vector) };
}

/// Preserve the existing TLB pending-counter provider and its atomic ordering.
///
/// # Safety
/// atomic_addr is the same live, aligned ihk_atomic_t owned by the synchronous
/// TLB protocol. No null policy, reference retention, or completion is invented.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_atomic_set_bridge(atomic_addr: CULong, value: CInt) {
    unsafe { crate::atomic_helpers::ihk_atomic_set(atomic_addr as *mut crate::atomic_helpers::IhkAtomic, value) }
}

#[no_mangle]
pub unsafe extern "C" fn mem_tlb_atomic_inc_bridge(atomic_addr: CULong) {
    unsafe { crate::atomic_helpers::ihk_atomic_inc(atomic_addr as *mut crate::atomic_helpers::IhkAtomic) }
}

/// Called only at the existing handler's actual completion point.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_atomic_dec_bridge(atomic_addr: CULong) {
    unsafe { crate::atomic_helpers::ihk_atomic_dec(atomic_addr as *mut crate::atomic_helpers::IhkAtomic) }
}

#[no_mangle]
pub unsafe extern "C" fn mem_tlb_atomic_read_bridge(atomic_addr: CULong) -> CInt {
    unsafe { crate::atomic_helpers::ihk_atomic_read(atomic_addr as *const crate::atomic_helpers::IhkAtomic) }
}

/// Exact no-IRQ ticket-lock callback; the original live lock remains caller-owned.
///
/// # Safety
/// lock_addr is the original aligned, initialized ihk_spinlock_t, retained for the
/// entire synchronous TLB protocol. The same provider owns preemption and ticket
/// ordering; this adapter neither changes IRQ state nor retains the pointer.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_noirq_lock_bridge(lock_addr: CULong) {
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_lock_noirq(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        )
    }
}

/// Exact no-IRQ release callback; release precedes the provider's preempt-enable.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_noirq_unlock_bridge(lock_addr: CULong) {
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_unlock_noirq(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        )
    }
}

/// Exact existing timestamp instruction provider; no serialization is added.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_rdtsc_bridge() -> CULong {
    unsafe { rdtsc() }
}

/// The same privileged invalidation provider consumes all address bits once.
/// Caller owns the original CPU/IRQ/address-space execution context.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_flush_single_bridge(addr: CULong) {
    unsafe { flush_tlb_single(addr) }
}

/// Preserve the existing CR3 flush provider and its instruction/memory ordering.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_flush_all_bridge() {
    unsafe { flush_tlb() }
}

/// Exact existing PAUSE provider; no yield, sleep, or completion is invented.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_pause_bridge() {
    unsafe { cpu_pause() }
}

/// Preserve the complete default VM fault/PTE/NUMA lookup entry.
///
/// # Safety
/// The caller retains the original VM/address-space/page-table lifetime and the
/// original mapping synchronization. This entry adds no reference or lock. The
/// same helper faults first, propagates the exact error, then resolves an active
/// PTE and its physical NUMA node; the default helper's null behavior is unchanged.
#[no_mangle]
pub unsafe extern "C" fn lookup_node(vm: *mut ProcessVm, addr: *mut c_void) -> CInt {
    unsafe {
        mem_lookup_node_body_result(
            vm.cast(), addr,
            offset_of!(ProcessVm, address_space) as CULong,
            offset_of!(AddressSpace, page_table) as CULong,
            Some(ihk_mc_pt_lookup_pte), Some(page_fault_process_vm), Some(phys_to_nid),
        )
    }
}

/// Exact former C diagnostic callback; preserve format bytes and varargs types.
unsafe extern "C" fn mem_lookup_fault_log_bridge(virt: *mut c_void) {
    unsafe {
        kprintf(
            b"%s: successfully faulted 0x%lx\n\0".as_ptr().cast(),
            b"ihk_mc_pt_lookup_fault_pte\0".as_ptr().cast::<i8>(),
            virt as CULong,
        );
    }
}

/// Complete default public fault/PTE lookup; reuse the unchanged production body.
///
/// # Safety
/// Caller retains the VM/address-space/PT and output-pointer lifetimes and the
/// same mapping synchronization as before. No new lock/reference or ownership
/// transfer is introduced. The existing body retries once after fault, ignores
/// the same fault return, and logs only an active post-fault PTE.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_lookup_fault_pte(
    vm: *mut ProcessVm, virt: *mut c_void, pgshift: CInt,
    basep: *mut *mut c_void, sizep: *mut usize, p2alignp: *mut CInt,
) -> *mut CULong {
    unsafe {
        mem_pt_lookup_fault_pte_body_result(
            vm.cast(), virt, pgshift, basep, sizep, p2alignp,
            offset_of!(ProcessVm, address_space) as CULong,
            offset_of!(AddressSpace, page_table) as CULong,
            Some(ihk_mc_pt_lookup_pte), Some(page_fault_process_vm),
            Some(mem_lookup_fault_log_bridge),
        )
    }
}

/// Exact existing physical-page hash IRQ-save ticket-lock provider.
/// Caller retains the initialized aligned lock; saved flags are returned unchanged.
#[no_mangle]
pub unsafe extern "C" fn page_hash_lock_bridge(lock_addr: CULong) -> CULong {
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_lock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        )
    }
}

/// Same release/preempt-enable/IRQ-restore provider and exact captured flags.
#[no_mangle]
pub unsafe extern "C" fn page_hash_unlock_bridge(lock_addr: CULong, flags: CULong) {
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_unlock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock, flags,
        )
    }
}

/// Exact existing lock initialization; no allocator or bucket ownership changes.
#[no_mangle]
pub unsafe extern "C" fn page_hash_lock_init_bridge(lock_addr: CULong) {
    unsafe {
        crate::spinlock_helpers::ihk_mc_spinlock_init(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        )
    }
}

/// Preserve the original single-address stack-local handoff to the array entry.
///
/// # Safety
/// The caller retains vm under the original TLB contract. The initialized local
/// lives through the synchronous array call, just as the C unsigned-long local
/// did. The existing array/body completion and lock protocol must finish every
/// use before this local expires. This entry does not dereference vm or retain
/// an additional pointer; neither callback nor shared-vector ownership changes.
#[no_mangle]
pub unsafe extern "C" fn remote_flush_tlb_cpumask(
    vm: *mut ProcessVm, addr: CULong, cpu_id: CInt,
) {
    let mut local_addr = addr;
    unsafe {
        remote_flush_tlb_array_cpumask(
            vm, core::ptr::addr_of_mut!(local_addr), 1, cpu_id,
        )
    }
}

/// Keep the original synchronous TLB request and callback ownership boundary.
///
/// # Safety
/// The caller retains vm and the address array until the existing body returns.
/// Existing callbacks preserve current-CPU, vector, IRQ and lock semantics. C
/// owns the shared vector and immutable geometry; no pointer is retained by this
/// entry beyond the original body, and its integer return remains ignored.
#[no_mangle]
pub unsafe extern "C" fn remote_flush_tlb_array_cpumask(
    vm: *mut ProcessVm, addr: *mut CULong, nr_addr: CInt, cpu_id: CInt,
) {
    let geometry = unsafe { core::ptr::read(core::ptr::addr_of!(mem_remote_tlb_geometry)) };
    let _ = unsafe {
        mem_remote_flush_tlb_array_body_result(
            vm, addr, nr_addr, cpu_id,
            core::ptr::addr_of_mut!(MEM_TLB_FLUSH_VECTOR_FIRST),
            geometry[0], geometry[1], geometry[2],
            Some(mem_tlb_rdtsc_bridge), Some(mem_tlb_current_cpu_bridge),
            Some(mem_tlb_get_vector_bridge), Some(mem_tlb_interrupt_cpu_bridge),
            Some(mem_tlb_noirq_lock_bridge), Some(mem_tlb_noirq_unlock_bridge),
            Some(mem_tlb_atomic_set_bridge), Some(mem_tlb_atomic_inc_bridge),
            Some(mem_tlb_atomic_read_bridge), Some(mem_tlb_flush_single_bridge),
            Some(mem_tlb_flush_all_bridge), Some(mem_tlb_pause_bridge),
        )
    };
}

#[no_mangle]
pub unsafe extern "C" fn mem_remote_flush_tlb_array_body_result(
    vm: *mut ProcessVm,
    addr: *mut CULong,
    nr_addr: CInt,
    _cpu_id: CInt,
    tlb_flush_vector: *mut TlbFlushEntry,
    vector_size: CInt,
    vector_start: CInt,
    cpu_set_bits: CInt,
    rdtsc_fn: Option<MemRdtscFn>,
    current_cpu_fn: Option<MemCurrentCpuFn>,
    get_vector_fn: Option<MemGetVectorFn>,
    interrupt_cpu_fn: Option<MemInterruptCpuFn>,
    lock_fn: Option<MemNoirqLockFn>,
    unlock_fn: Option<MemNoirqLockFn>,
    atomic_set_fn: Option<MemAtomicSetFn>,
    atomic_inc_fn: Option<MemAtomicIncFn>,
    atomic_read_fn: Option<MemAtomicReadFn>,
    flush_single_fn: Option<MemFlushTlbSingleFn>,
    flush_all_fn: Option<MemFlushTlbAllFn>,
    pause_fn: Option<MemPauseFn>,
) -> CInt {
    let (
        Some(rdtsc),
        Some(current_cpu),
        Some(get_vector),
        Some(interrupt_cpu),
        Some(lock),
        Some(unlock),
        Some(atomic_set),
        Some(atomic_inc),
        Some(atomic_read),
        Some(flush_single),
        Some(flush_all),
        Some(pause),
    ) = (
        rdtsc_fn,
        current_cpu_fn,
        get_vector_fn,
        interrupt_cpu_fn,
        lock_fn,
        unlock_fn,
        atomic_set_fn,
        atomic_inc_fn,
        atomic_read_fn,
        flush_single_fn,
        flush_all_fn,
        pause_fn,
    )
    else {
        return -EINVAL;
    };

    if vm.is_null()
        || addr.is_null()
        || nr_addr <= 0
        || tlb_flush_vector.is_null()
        || vector_size <= 0
        || cpu_set_bits <= 0
    {
        return -EINVAL;
    }

    let aspace: *mut AddressSpace = (*vm).address_space;
    if aspace.is_null() {
        return -EINVAL;
    }

    let first_addr = *addr;
    let flush_ind = if first_addr != 0 {
        ((first_addr >> PAGE_SHIFT) % (vector_size as CULong)) as CInt
    } else {
        (rdtsc() % (vector_size as CULong)) as CInt
    };
    let flush_entry = tlb_flush_vector.add(flush_ind as usize);

    let bits_per_word = core::mem::size_of::<CULong>() * 8;
    let max_bits = cpu_set_bits as usize;
    let mut cpu_word_count = (max_bits + bits_per_word - 1) / bits_per_word;
    if cpu_word_count > CPU_SET_WORDS {
        cpu_word_count = CPU_SET_WORDS;
    }
    let mut cpu_bits = core::mem::MaybeUninit::<[CULong; CPU_SET_WORDS]>::uninit();
    let cpu_bits_ptr = cpu_bits.as_mut_ptr().cast::<CULong>();
    lock((&raw mut (*aspace).cpu_set_lock).cast::<c_void>() as CULong);
    let mut i = 0usize;
    while i < cpu_word_count {
        let word = core::ptr::read_volatile(&raw const (*aspace).cpu_set.bits[i]);
        core::ptr::write_volatile(cpu_bits_ptr.add(i), word);
        i += 1;
    }
    unlock((&raw mut (*aspace).cpu_set_lock).cast::<c_void>() as CULong);

    lock((&raw mut (*flush_entry).lock).cast::<c_void>() as CULong);
    (*flush_entry).vm = vm;
    (*flush_entry).addr = addr;
    (*flush_entry).nr_addr = nr_addr;
    atomic_set(
        (&raw mut (*flush_entry).pending).cast::<c_void>() as CULong,
        0,
    );

    let mut word_index = 0usize;
    while word_index < cpu_word_count {
        let mut word = core::ptr::read_volatile(cpu_bits_ptr.add(word_index));
        while word != 0 {
            let bit = word.trailing_zeros() as usize;
            let cpu = word_index * bits_per_word + bit;
            if cpu >= max_bits {
                break;
            }
            if current_cpu() != cpu as CInt {
                atomic_inc((&raw mut (*flush_entry).pending).cast::<c_void>() as CULong);
                let vector = get_vector(flush_ind + vector_start);
                interrupt_cpu(cpu as CInt, vector);
            }
            word &= word - 1;
        }
        word_index += 1;
    }

    if first_addr != 0 {
        let mut index = 0isize;
        while index < nr_addr as isize {
            flush_single(*addr.offset(index) & PAGE_MASK);
            index += 1;
        }
    } else {
        flush_all();
    }

    while atomic_read((&raw mut (*flush_entry).pending).cast::<c_void>() as CULong) != 0 {
        pause();
    }
    unlock((&raw mut (*flush_entry).lock).cast::<c_void>() as CULong);

    flush_ind
}

#[no_mangle]
pub unsafe extern "C" fn mem_tlb_flush_handler_body_result(
    vector: CInt,
    tlb_flush_vector: *mut TlbFlushEntry,
    vector_size: CInt,
    vector_start: CInt,
    irq_save_fn: Option<MemKmallocIrqSaveFn>,
    irq_restore_fn: Option<MemKmallocIrqRestoreFn>,
    flush_single_fn: Option<MemFlushTlbSingleFn>,
    flush_all_fn: Option<MemFlushTlbAllFn>,
    atomic_dec_fn: Option<MemAtomicDecFn>,
) -> CInt {
    let (Some(irq_save), Some(irq_restore), Some(flush_single), Some(flush_all), Some(atomic_dec)) = (
        irq_save_fn,
        irq_restore_fn,
        flush_single_fn,
        flush_all_fn,
        atomic_dec_fn,
    ) else {
        return -EINVAL;
    };

    if tlb_flush_vector.is_null() || vector_size <= 0 {
        return -EINVAL;
    }

    let index = vector - vector_start;
    if index < 0 || index >= vector_size {
        return -EINVAL;
    }

    let flags = irq_save();
    let flush_entry = tlb_flush_vector.add(index as usize);
    let addr = (*flush_entry).addr;
    if !addr.is_null() && *addr != 0 {
        let mut i = 0isize;
        while i < (*flush_entry).nr_addr as isize {
            flush_single(*addr.offset(i) & PAGE_MASK);
            i += 1;
        }
    } else {
        flush_all();
    }
    atomic_dec((&raw mut (*flush_entry).pending).cast::<c_void>() as CULong);
    irq_restore(flags);

    0
}

#[inline(always)]
unsafe fn dump_page_map(page: *mut IhkDumpPage) -> *mut CULong {
    (page.cast::<u8>())
        .add(size_of::<IhkDumpPage>())
        .cast::<CULong>()
}

#[inline(always)]
unsafe fn dump_page_next(page: *mut IhkDumpPage) -> *mut IhkDumpPage {
    (page.cast::<u8>())
        .add(size_of::<IhkDumpPage>() + (*page).map_count as usize * size_of::<CULong>())
        .cast::<IhkDumpPage>()
}

#[no_mangle]
pub unsafe extern "C" fn mem_chk_page_address_result(
    mem_addr: CULong,
    nr_chunks_fn: Option<MemGetNrMemoryChunksFn>,
    chunk_fn: Option<MemGetMemoryChunkFn>,
) -> CInt {
    let (Some(nr_chunks), Some(get_chunk)) = (nr_chunks_fn, chunk_fn) else {
        return -1;
    };

    let mut i = 0;
    let chunks = nr_chunks();
    while i < chunks {
        let mut start = 0;
        let mut end = 0;
        let mut numa_id = 0;
        get_chunk(i, &mut start, &mut end, &mut numa_id);
        if mem_addr >= start && end >= mem_addr {
            return 0;
        }
        i += 1;
    }

    -1
}

#[no_mangle]
pub unsafe extern "C" fn mem_clear_dump_page_completion_result(
    get_page_set_fn: Option<MemDumpGetPageSetFn>,
) -> CInt {
    let Some(get_page_set) = get_page_set_fn else {
        return -EINVAL;
    };
    let page_set = get_page_set();
    if page_set.is_null() {
        return -EINVAL;
    }

    write_volatile(
        &raw mut (*page_set).completion_flag,
        IHK_DUMP_PAGE_SET_INCOMPLETE,
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn mem_dump_mark_range_result(
    dump_pase_info: *mut DumpPaseInfo,
    mut chunk_addr: CULong,
    mut chunk_size: CULong,
    warn_kind: CInt,
    warn_fn: Option<MemDumpWarnFn>,
) -> CInt {
    if dump_pase_info.is_null() || chunk_size == 0 {
        return 0;
    }

    let dump_page_set = (*dump_pase_info).dump_page_set;
    let mut dump_page = (*dump_pase_info).dump_pages;
    if dump_page_set.is_null() || dump_page.is_null() {
        return 0;
    }

    let mut cleared = 0;
    let mut i = 0;
    while i < (*dump_page_set).count {
        if i != 0 {
            dump_page = dump_page_next(dump_page);
        }

        let phy_start = (*dump_page).start;
        let map_count = (*dump_page).map_count;
        let map_size = map_count << (PAGE_SHIFT + 6);

        if chunk_addr >= phy_start && phy_start.wrapping_add(map_size) >= chunk_addr {
            let map_start = (chunk_addr - phy_start) >> PAGE_SHIFT;
            let map_end = if phy_start.wrapping_add(map_size) < chunk_addr.wrapping_add(chunk_size)
            {
                let set_size = map_size - (chunk_addr - phy_start);
                chunk_addr = chunk_addr.wrapping_add(set_size);
                chunk_size = chunk_size.wrapping_sub(set_size);
                map_start + (set_size >> PAGE_SHIFT)
            } else {
                map_start + (chunk_size >> PAGE_SHIFT)
            };

            let map = dump_page_map(dump_page);
            let mut k = map_start;
            while k < map_end {
                let map_index = k >> 6;
                if map_index >= map_count {
                    if let Some(warn) = warn_fn {
                        warn(warn_kind, map_count, map_index, map_start, map_end, k);
                    }
                    break;
                }
                let word = map.add(map_index as usize);
                *word &= !(1u64 << (k & 0x3f));
                cleared += 1;
                k += 1;
            }
        }

        i += 1;
    }

    cleared
}

#[no_mangle]
pub unsafe extern "C" fn mem_get_mem_user_page_result(
    dump_pase_info: *mut DumpPaseInfo,
    ptep: *mut CULong,
    pgshift: CInt,
    chk_page_address_fn: Option<MemChkPageAddressFn>,
    warn_fn: Option<MemDumpWarnFn>,
) -> CInt {
    if ptep.is_null() || pgshift < 0 {
        return 0;
    }

    let pte = *ptep;
    if (pte & PTATTR_ACTIVE) == 0 || (pte & PTATTR_USER) == 0 {
        return 0;
    }

    let phys = pte & PT_PHYSMASK;
    if let Some(chk_page_address) = chk_page_address_fn {
        if chk_page_address(phys) == -1 {
            return 0;
        }
    }

    mem_dump_mark_range_result(
        dump_pase_info,
        phys,
        1u64 << (pgshift as u32),
        MEM_DUMP_WARN_USER,
        warn_fn,
    );
    0
}

#[inline(always)]
unsafe fn mem_free_chunk_from_rb_node(node: *mut RbNode) -> *mut MemFreeChunk {
    node.cast::<u8>()
        .sub(offset_of!(MemFreeChunk, node))
        .cast::<MemFreeChunk>()
}

#[no_mangle]
pub unsafe extern "C" fn mem_dump_free_pages_public_result(
    memory_nodes: *mut MemNumaNode,
    node: CInt,
    nr_nodes_fn: Option<MemGetNrNumaNodesFn>,
) -> CULong {
    let Some(nr_nodes) = nr_nodes_fn else {
        return 0;
    };
    if memory_nodes.is_null() || node < 0 || node >= nr_nodes() {
        return 0;
    }

    (*memory_nodes.add(node as usize)).nr_free_pages
}

#[no_mangle]
pub unsafe extern "C" fn mem_dump_first_free_chunk_public_result(
    memory_nodes: *mut MemNumaNode,
    node: CInt,
    nr_nodes_fn: Option<MemGetNrNumaNodesFn>,
) -> *mut c_void {
    let Some(nr_nodes) = nr_nodes_fn else {
        return null_mut();
    };
    if memory_nodes.is_null() || node < 0 || node >= nr_nodes() {
        return null_mut();
    }

    let root = &raw const (*memory_nodes.add(node as usize)).free_chunks;
    let rbnode = rb_first_safe(root);
    if rbnode.is_null() {
        null_mut()
    } else {
        mem_free_chunk_from_rb_node(rbnode).cast::<c_void>()
    }
}

#[no_mangle]
pub unsafe extern "C" fn mem_dump_next_free_chunk_result(chunk: *mut c_void) -> *mut c_void {
    if chunk.is_null() {
        return null_mut();
    }

    let chunk = chunk.cast::<MemFreeChunk>();
    let rbnode = rb_next_safe(&raw const (*chunk).node);
    if rbnode.is_null() {
        null_mut()
    } else {
        mem_free_chunk_from_rb_node(rbnode).cast::<c_void>()
    }
}

#[no_mangle]
pub unsafe extern "C" fn mem_dump_chunk_addr_result(chunk: *mut c_void) -> CULong {
    if chunk.is_null() {
        0
    } else {
        (*chunk.cast::<MemFreeChunk>()).addr
    }
}

#[no_mangle]
pub unsafe extern "C" fn mem_dump_chunk_size_result(chunk: *mut c_void) -> CULong {
    if chunk.is_null() {
        0
    } else {
        (*chunk.cast::<MemFreeChunk>()).size
    }
}

#[no_mangle]
pub unsafe extern "C" fn mem_query_mem_free_page_result(
    dump_pase_info: *mut DumpPaseInfo,
    nr_nodes: CInt,
    free_pages_fn: Option<MemDumpChunkCountFn>,
    first_chunk_fn: Option<MemDumpChunkIterFn>,
    next_chunk_fn: Option<MemDumpNextChunkFn>,
    chunk_addr_fn: Option<MemDumpChunkFieldFn>,
    chunk_size_fn: Option<MemDumpChunkFieldFn>,
    warn_fn: Option<MemDumpWarnFn>,
) -> CInt {
    let (Some(free_pages), Some(first_chunk), Some(next_chunk), Some(chunk_addr), Some(chunk_size)) = (
        free_pages_fn,
        first_chunk_fn,
        next_chunk_fn,
        chunk_addr_fn,
        chunk_size_fn,
    ) else {
        return -EINVAL;
    };

    let mut cleared = 0;
    let mut i = 0;
    while i < nr_nodes {
        let max_chunks = free_pages(i);
        let mut count = 0;
        let mut chunk = first_chunk(i);

        while !chunk.is_null() {
            if count >= max_chunks {
                break;
            }
            cleared += mem_dump_mark_range_result(
                dump_pase_info,
                chunk_addr(chunk),
                chunk_size(chunk),
                MEM_DUMP_WARN_FREE,
                warn_fn,
            );
            count += 1;
            chunk = next_chunk(chunk);
        }

        i += 1;
    }

    cleared
}

#[no_mangle]
pub unsafe extern "C" fn mem_query_mem_free_page_public_result(
    dump_pase_info: *mut DumpPaseInfo,
    nr_nodes_fn: Option<MemGetNrNumaNodesFn>,
    free_pages_fn: Option<MemDumpChunkCountFn>,
    first_chunk_fn: Option<MemDumpChunkIterFn>,
    next_chunk_fn: Option<MemDumpNextChunkFn>,
    chunk_addr_fn: Option<MemDumpChunkFieldFn>,
    chunk_size_fn: Option<MemDumpChunkFieldFn>,
    warn_fn: Option<MemDumpWarnFn>,
) -> CInt {
    let Some(nr_nodes) = nr_nodes_fn else {
        return -EINVAL;
    };

    mem_query_mem_free_page_result(
        dump_pase_info,
        nr_nodes(),
        free_pages_fn,
        first_chunk_fn,
        next_chunk_fn,
        chunk_addr_fn,
        chunk_size_fn,
        warn_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn mem_query_mem_user_page_result(
    process_hash_lists: *mut AbiListHead,
    hash_size: CInt,
    process_hash_list_offset: CULong,
    process_vm_offset: CULong,
    vm_address_space_offset: CULong,
    address_space_page_table_offset: CULong,
    user_end: CULong,
    visit_pte_range_fn: Option<MemVisitPteRangeFn>,
    pte_visitor_fn: Option<MemPteVisitorFn>,
    dump_pase_info: *mut c_void,
) -> CInt {
    if process_hash_lists.is_null() || hash_size <= 0 {
        return 0;
    }
    let (Some(visit_pte_range), Some(pte_visitor)) = (visit_pte_range_fn, pte_visitor_fn) else {
        return -EINVAL;
    };

    let mut dispatched = 0;
    let mut i = 0;
    while i < hash_size {
        let head = process_hash_lists.add(i as usize);
        let mut node = (*head).next;

        while !node.is_null() && node != head {
            let next = (*node).next;
            let process = (node.cast::<u8>())
                .sub(process_hash_list_offset as usize)
                .cast::<u8>();
            let vm = *(process
                .add(process_vm_offset as usize)
                .cast::<*mut c_void>());

            if !vm.is_null() {
                let address_space = *(vm
                    .cast::<u8>()
                    .add(vm_address_space_offset as usize)
                    .cast::<*mut c_void>());
                if !address_space.is_null() {
                    let page_table = *(address_space
                        .cast::<u8>()
                        .add(address_space_page_table_offset as usize)
                        .cast::<*mut c_void>());
                    if !page_table.is_null() {
                        visit_pte_range(
                            page_table,
                            null_mut(),
                            user_end as *mut c_void,
                            0,
                            0,
                            Some(pte_visitor),
                            dump_pase_info,
                        );
                        dispatched += 1;
                    }
                }
            }

            node = next;
        }

        i += 1;
    }

    dispatched
}

#[no_mangle]
pub unsafe extern "C" fn mem_query_mem_areas_result(
    current_cpu: CInt,
    nr_cpus: CInt,
    dump_level: CInt,
    get_page_set_fn: Option<MemDumpGetPageSetFn>,
    get_page_fn: Option<MemDumpGetPageFn>,
    query_user_fn: Option<MemDumpQueryFn>,
    query_free_fn: Option<MemDumpQueryFn>,
    log_fn: Option<MemDumpLogFn>,
) -> CInt {
    if nr_cpus <= 0 || current_cpu != nr_cpus - 1 {
        return 0;
    }

    let (Some(get_page_set), Some(get_page), Some(query_user), Some(query_free)) =
        (get_page_set_fn, get_page_fn, query_user_fn, query_free_fn)
    else {
        return -EINVAL;
    };

    let dump_page_set = get_page_set();
    if dump_page_set.is_null() {
        return -EINVAL;
    }

    if dump_level == DUMP_LEVEL_USER_UNUSED_EXCLUDE && (*dump_page_set).count != 0 {
        let mut dump_pase_info = DumpPaseInfo {
            dump_page_set,
            dump_pages: get_page(),
        };
        query_user((&raw mut dump_pase_info).cast::<c_void>());
        query_free((&raw mut dump_pase_info).cast::<c_void>());
    }

    write_volatile(
        &raw mut (*dump_page_set).completion_flag,
        IHK_DUMP_PAGE_SET_COMPLETED,
    );
    if let Some(log) = log_fn {
        log();
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_query_mem_areas() {
    unsafe {
        mem_query_mem_areas_result(
            ihk_mc_get_processor_id(),
            mem_num_processors_bridge(),
            mem_dump_level_bridge(),
            Some(mem_get_dump_page_set_bridge),
            Some(mem_get_dump_page_bridge),
            Some(ihk_mc_query_mem_user_page),
            Some(ihk_mc_query_mem_free_page),
            Some(mem_dump_complete_log_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_query_mem_user_page(dump_pase_info: *mut c_void) {
    unsafe {
        mem_query_mem_user_page_result(
            mem_process_hash_lists_bridge(),
            PROCESS_HASH_SIZE as CInt,
            offset_of!(Process, hash_list) as CULong,
            offset_of!(Process, vm) as CULong,
            offset_of!(ProcessVm, address_space) as CULong,
            offset_of!(AddressSpace, page_table) as CULong,
            X86_USER_END,
            Some(visit_pte_range_safe),
            Some(ihk_mc_get_mem_user_page),
            dump_pase_info,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_query_mem_free_page(dump_pase_info: *mut c_void) {
    unsafe {
        mem_query_mem_free_page_public_result(
            dump_pase_info.cast::<DumpPaseInfo>(),
            Some(ihk_mc_get_nr_numa_nodes),
            Some(mem_dump_free_pages_bridge),
            Some(mem_dump_first_free_chunk_bridge),
            Some(mem_dump_next_free_chunk_bridge),
            Some(mem_dump_chunk_addr_bridge),
            Some(mem_dump_chunk_size_bridge),
            Some(mem_dump_warn_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn find_command_line(name: *mut i8) -> *mut i8 {
    let cmdline = ihk_get_kargs();

    if cmdline.is_null() {
        return null_mut();
    }

    strstr(cmdline, name)
}

#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_init_chunk_result(h: *mut KmallocHeader, size: CInt) {
    (*h).size = size;
    (*h).front_magic = KMALLOC_FRONT_MAGIC;
    (*h).end_magic = KMALLOC_END_MAGIC;
    (*h).cpu_id = ihk_mc_get_processor_id();
}

#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_insert_chunk_result(
    free_list: *mut AbiListHead,
    chunk: *mut KmallocHeader,
) {
    let mut next_chunk: *mut KmallocHeader = null_mut();
    let mut node = (*free_list).next;

    while node != free_list {
        let chunk_iter = list_to_kmalloc_header(node);
        if (chunk as usize) < (chunk_iter as usize) {
            next_chunk = chunk_iter;
            break;
        }
        node = (*node).next;
    }

    if !next_chunk.is_null() {
        list_add_tail(kmalloc_list(chunk), kmalloc_list(next_chunk));
    } else {
        list_add_tail(kmalloc_list(chunk), free_list);
    }
}

#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_consolidate_list_result(list: *mut AbiListHead) {
    loop {
        let mut chunk_iter: *mut KmallocHeader = null_mut();
        let mut chunk: *mut KmallocHeader = null_mut();
        let mut next_chunk: *mut KmallocHeader = null_mut();
        let mut node = (*list).next;

        while node != list {
            let candidate = list_to_kmalloc_header(node);

            if !chunk_iter.is_null()
                && (chunk_iter as usize)
                    + core::mem::size_of::<KmallocHeader>()
                    + (*chunk_iter).size as usize
                    == candidate as usize
            {
                chunk = chunk_iter;
                next_chunk = candidate;
                break;
            }

            chunk_iter = candidate;
            node = (*node).next;
        }

        if chunk.is_null() {
            return;
        }

        (*chunk).size += (*next_chunk).size + core::mem::size_of::<KmallocHeader>() as CInt;
        list_del(kmalloc_list(next_chunk));
    }
}

#[inline(always)]
fn kmalloc_aligned_size(size: CInt) -> CInt {
    if (size & KMALLOC_MIN_MASK) != 0 {
        size.wrapping_add(KMALLOC_MIN_SIZE - 1) & !KMALLOC_MIN_MASK
    } else {
        size
    }
}

#[inline(always)]
unsafe fn kmalloc_find_fit(free_list: *mut AbiListHead, size: CInt) -> *mut KmallocHeader {
    let mut node = (*free_list).next;

    while node != free_list {
        let chunk_iter = list_to_kmalloc_header(node);
        if (*chunk_iter).size >= size {
            return chunk_iter;
        }
        node = (*node).next;
    }

    null_mut()
}

#[inline(always)]
unsafe fn kmalloc_split_if_needed(chunk: *mut KmallocHeader, size: CInt) {
    let header_size = size_of::<KmallocHeader>() as CInt;

    if (*chunk).size > size.wrapping_add(header_size) {
        let leftover = (chunk.cast::<u8>())
            .add(size_of::<KmallocHeader>())
            .add(size as usize)
            .cast::<KmallocHeader>();
        ___kmalloc_init_chunk_result(
            leftover,
            (*chunk).size.wrapping_sub(size).wrapping_sub(header_size),
        );
        list_add_after(kmalloc_list(leftover), kmalloc_list(chunk));
        (*chunk).size = size;
    }
}

#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_body_result(
    size: CInt,
    flag: CULong,
    free_list: *mut AbiListHead,
    irq_save_fn: Option<MemKmallocIrqSaveFn>,
    irq_restore_fn: Option<MemKmallocIrqRestoreFn>,
    alloc_pages_fn: Option<MemKmallocAllocPagesFn>,
) -> *mut c_void {
    if free_list.is_null() {
        return null_mut();
    }
    let Some(irq_save) = irq_save_fn else {
        return null_mut();
    };
    let Some(irq_restore) = irq_restore_fn else {
        return null_mut();
    };
    let Some(alloc_pages) = alloc_pages_fn else {
        return null_mut();
    };

    let irq_flags = irq_save();
    let size = kmalloc_aligned_size(size);
    let mut chunk = kmalloc_find_fit(free_list, size);

    if chunk.is_null() {
        let npages = ((size as CULong)
            .wrapping_add(size_of::<KmallocHeader>() as CULong)
            .wrapping_add(PAGE_SIZE - 1))
            >> PAGE_SHIFT;
        chunk = alloc_pages(npages as CInt, flag, IHK_MC_PG_KERNEL).cast::<KmallocHeader>();

        if chunk.is_null() {
            irq_restore(irq_flags);
            return null_mut();
        }

        ___kmalloc_init_chunk_result(
            chunk,
            (npages
                .wrapping_mul(PAGE_SIZE)
                .wrapping_sub(size_of::<KmallocHeader>() as CULong)) as CInt,
        );
        ___kmalloc_insert_chunk_result(free_list, chunk);
    }

    kmalloc_split_if_needed(chunk, size);
    list_del_poison(kmalloc_list(chunk));
    irq_restore(irq_flags);

    (chunk.cast::<u8>())
        .add(size_of::<KmallocHeader>())
        .cast::<c_void>()
}

#[no_mangle]
pub unsafe extern "C" fn ___kfree_body_result(
    ptr: *mut c_void,
    free_list: *mut AbiListHead,
    remote_free_list_lock_offset: CULong,
    remote_free_list_offset: CULong,
    irq_save_fn: Option<MemKmallocIrqSaveFn>,
    irq_restore_fn: Option<MemKmallocIrqRestoreFn>,
    get_cpu_local_var_fn: Option<MemKmallocGetCpuLocalVarFn>,
    remote_lock_fn: Option<MemKmallocSpinLockFn>,
    remote_unlock_fn: Option<MemKmallocSpinUnlockFn>,
    corruption_fn: Option<MemKmallocCorruptionFn>,
) -> CInt {
    if ptr.is_null() {
        return 0;
    }
    if free_list.is_null() {
        return -EINVAL;
    }
    let Some(irq_save) = irq_save_fn else {
        return -EINVAL;
    };
    let Some(irq_restore) = irq_restore_fn else {
        return -EINVAL;
    };

    let chunk = (ptr.cast::<u8>())
        .sub(size_of::<KmallocHeader>())
        .cast::<KmallocHeader>();
    let irq_flags = irq_save();

    if (*chunk).front_magic != KMALLOC_FRONT_MAGIC || (*chunk).end_magic != KMALLOC_END_MAGIC {
        if let Some(corruption) = corruption_fn {
            corruption(ptr);
        }
        return -EINVAL;
    }

    if (*chunk).cpu_id == ihk_mc_get_processor_id() {
        ___kmalloc_insert_chunk_result(free_list, chunk);
        ___kmalloc_consolidate_list_result(free_list);
    } else {
        let Some(get_cpu_local_var) = get_cpu_local_var_fn else {
            irq_restore(irq_flags);
            return -EINVAL;
        };
        let Some(remote_lock) = remote_lock_fn else {
            irq_restore(irq_flags);
            return -EINVAL;
        };
        let Some(remote_unlock) = remote_unlock_fn else {
            irq_restore(irq_flags);
            return -EINVAL;
        };

        let remote_cpu = get_cpu_local_var((*chunk).cpu_id);
        if remote_cpu.is_null() {
            irq_restore(irq_flags);
            return -EINVAL;
        }

        let lock_addr = (remote_cpu as CULong).wrapping_add(remote_free_list_lock_offset);
        let remote_list = (remote_cpu.cast::<u8>())
            .add(remote_free_list_offset as usize)
            .cast::<AbiListHead>();
        let remote_irq_flags = remote_lock(lock_addr);
        list_add_after(kmalloc_list(chunk), remote_list);
        remote_unlock(lock_addr, remote_irq_flags);
    }

    irq_restore(irq_flags);
    0
}

#[inline(always)]
unsafe fn kmalloc_cache_next_atomic(
    cache: *mut KmallocCacheHeader,
) -> *mut AtomicPtr<KmallocCacheHeader> {
    (&raw mut (*cache).next).cast::<AtomicPtr<KmallocCacheHeader>>()
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_cache_free_result(
    elem: *mut c_void,
    log_fn: Option<MemKmallocCacheLogFn>,
) -> CInt {
    if elem.is_null() {
        return 0;
    }

    let new = elem.cast::<KmallocCacheHeader>();
    let header = elem
        .cast::<u8>()
        .sub(size_of::<KmallocHeader>())
        .cast::<KmallocHeader>();
    let cache = (*header).link.cache;

    if cache.is_null() {
        if let Some(log) = log_fn {
            log(KMALLOC_CACHE_LOG_NO_CACHE, elem);
        }
        return 0;
    }

    let next = kmalloc_cache_next_atomic(cache);
    loop {
        let current = (*next).load(Ordering::SeqCst);
        (*new).next = current;

        if (*next)
            .compare_exchange(current, new, Ordering::SeqCst, Ordering::SeqCst)
            .is_ok()
        {
            return 1;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_cache_prealloc_result(
    cache: *mut KmallocCacheHeader,
    size: SizeT,
    nr_elem: CInt,
    alloc_fn: Option<MemKmallocCacheAllocFn>,
    log_fn: Option<MemKmallocCacheLogFn>,
) -> CInt {
    if cache.is_null() {
        return -EINVAL;
    }

    if !(*kmalloc_cache_next_atomic(cache))
        .load(Ordering::SeqCst)
        .is_null()
    {
        return 0;
    }

    let Some(alloc) = alloc_fn else {
        return -EINVAL;
    };

    let mut added = 0;
    let mut i = 0;
    while i < nr_elem {
        let elem = alloc(size, IHK_MC_AP_NOWAIT).cast::<KmallocCacheHeader>();

        if elem.is_null() {
            if let Some(log) = log_fn {
                log(KMALLOC_CACHE_LOG_ALLOC_FAILED, null_mut());
            }
            i += 1;
            continue;
        }

        let header = (elem.cast::<u8>())
            .sub(size_of::<KmallocHeader>())
            .cast::<KmallocHeader>();
        (*header).link.cache = cache;
        added += kmalloc_cache_free_result(elem.cast::<c_void>(), log_fn);
        i += 1;
    }

    added
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_cache_alloc_result(
    cache: *mut KmallocCacheHeader,
    size: SizeT,
    prealloc_fn: Option<MemKmallocCachePreallocFn>,
    log_fn: Option<MemKmallocCacheLogFn>,
) -> *mut c_void {
    if cache.is_null() {
        return null_mut();
    }

    let next = kmalloc_cache_next_atomic(cache);
    loop {
        let first = (*next).load(Ordering::SeqCst);
        if first.is_null() {
            if let Some(log) = log_fn {
                log(KMALLOC_CACHE_LOG_PREALLOC, cache.cast::<c_void>());
            }
            let Some(prealloc) = prealloc_fn else {
                return null_mut();
            };
            prealloc(cache, size, 384);
            continue;
        }

        let after_first = (*first).next;
        if (*next)
            .compare_exchange(first, after_first, Ordering::SeqCst, Ordering::SeqCst)
            .is_ok()
        {
            return first.cast::<c_void>();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_cache_free(elem: *mut c_void) {
    kmalloc_cache_free_result(elem, Some(kmalloc_cache_log));
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_cache_prealloc(
    cache: *mut KmallocCacheHeader,
    size: SizeT,
    nr_elem: CInt,
) {
    kmalloc_cache_prealloc_result(
        cache,
        size,
        nr_elem,
        Some(kmalloc_cache_alloc_bridge),
        Some(kmalloc_cache_log),
    );
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_cache_alloc(
    cache: *mut KmallocCacheHeader,
    size: SizeT,
) -> *mut c_void {
    kmalloc_cache_alloc_result(
        cache,
        size,
        Some(kmalloc_cache_prealloc),
        Some(kmalloc_cache_log),
    )
}

#[cfg(test)]
mod pending_free_batch_tests {
    use super::*;

    static mut FREED: CInt = 0;

    unsafe extern "C" fn record_free(_: CULong, npages: CInt, _: CInt) {
        unsafe { FREED += npages; }
    }

    unsafe fn page(phys: CULong, npages: CInt) -> MemPage {
        MemPage {
            list: AbiListHead { next: null_mut(), prev: null_mut() },
            hash: AbiListHead { next: null_mut(), prev: null_mut() },
            mode: PM_PENDING_FREE,
            phys,
            count: IhkAtomic { counter: 0 },
            mapped: IhkAtomic64 { counter64: 0 },
            offset: npages as OffT,
            pgshift: PAGE_SHIFT as CInt,
        }
    }

    #[test]
    fn actual_helpers_transfer_drain_reuse_and_reject_atomically() {
        unsafe {
            let mut source = AbiListHead { next: null_mut(), prev: null_mut() };
            init_list_head(&raw mut source);
            let mut first = page(10, 2);
            let mut second = page(20, 3);
            list_add_tail(&raw mut first.list, &raw mut source);
            list_add_tail(&raw mut second.list, &raw mut source);
            let mut batch = PendingFreeBatch::new();
            let mut pinned = Pin::new_unchecked(&mut batch);
            assert_eq!(detach_pending_free_batch(&raw mut source, pinned.as_mut()), 0);
            assert!(source.next.is_null() && source.prev.is_null());
            let view = pinned.as_ref().get_ref();
            assert_eq!(view.head.next, &raw mut first.list);
            assert_eq!(view.head.prev, &raw mut second.list);
            let mut wrong_source = AbiListHead { next: null_mut(), prev: null_mut() };
            init_list_head(&raw mut wrong_source);
            assert_eq!(drain_pending_free_batch(
                &raw mut wrong_source,
                pinned.as_mut(),
                Some(record_free),
            ), -EINVAL);
            assert_eq!(detach_pending_free_batch(&raw mut source, pinned.as_mut()), -EINVAL);
            FREED = 0;
            assert_eq!(drain_pending_free_batch(&raw mut source, pinned, Some(record_free)), 2);
            assert_eq!(FREED, 5);
            init_list_head(&raw mut source);
            let mut empty = PendingFreeBatch::new();
            let empty_pin = Pin::new_unchecked(&mut empty);
            assert_eq!(detach_pending_free_batch(&raw mut source, empty_pin), 0);
            assert!(source.next.is_null() && source.prev.is_null());
            init_list_head(&raw mut source);

            let mut mixed = PendingFreeBatch::new();
            mixed.head.next = &raw mut mixed.head;
            let before = source;
            assert_eq!(detach_pending_free_batch(
                &raw mut source,
                Pin::new_unchecked(&mut mixed),
            ), -EINVAL);
            assert_eq!(source.next, before.next);
            assert_eq!(source.prev, before.prev);

            let mut bad = page(30, 4);
            let mut invalid = page(40, 5);
            list_add_tail(&raw mut bad.list, &raw mut source);
            list_add_tail(&raw mut invalid.list, &raw mut source);
            invalid.mode = PM_NONE;
            let before = source;
            let mut rejected = PendingFreeBatch::new();
            assert_eq!(detach_pending_free_batch(
                &raw mut source,
                Pin::new_unchecked(&mut rejected),
            ), -EINVAL);
            assert_eq!(source.next, before.next);
            assert_eq!(source.prev, before.prev);
            assert_eq!(bad.list.prev, &raw mut source);
        }
    }
}

// C data-only diagnostic origin at the former callback callsite. This does
// not acquire, allocate, dereference a Page or create another C provider.
unsafe extern "C" {
    static page_hash_alloc_file: [i8; 1];
    static page_hash_alloc_line: CInt;
}

/// Exact page-hash allocation adapter to the existing tracked allocator.
/// The C callback's unsigned-long -> int size conversion and signed-int ->
/// unsigned-long allocation-flag conversion are intentional and unchanged.
#[no_mangle]
pub unsafe extern "C" fn page_hash_alloc_bridge(
    size: CULong,
    flag: CInt,
) -> *mut crate::page_helpers::Page {
    unsafe {
        kmalloc_tracked(
            size as CInt,
            flag as CULong,
            core::ptr::addr_of!(page_hash_alloc_file).cast::<i8>() as *mut i8,
            page_hash_alloc_line,
        ).cast::<crate::page_helpers::Page>()
    }
}

// Existing C arrays and immutable ABI geometry. Each [u8;1] names only its
// first byte; the C count/strides define bounds, never a Rust-invented extent.
unsafe extern "C" {
    #[link_name = "page_hash"]
    static PAGE_INIT_HASH_FIRST: [u8; 1];
    #[link_name = "page_hash_locks"]
    static PAGE_INIT_LOCK_FIRST: [u8; 1];
    static page_init_hash_bucket_count: CInt;
    static page_init_hash_head_stride: SizeT;
    // Already exported for the existing page_unmap public Rust consumer.
    static page_unmap_lock_stride: SizeT;
    // Existing selected provider, declared using the existing helper's usize
    // address ABI (unsigned long on this supported x86_64 profile).
    #[link_name = "page_hash_lock_init_bridge"]
    fn page_init_lock_callback(lock_addr: usize);
}

/// Initialize the existing page hash through the unchanged Rust orchestrator.
/// Same synchronous boot-owned arrays/callbacks/order; C void wrapper ignored
/// the helper's result, so this entry intentionally discards it as well.
#[no_mangle]
pub unsafe extern "C" fn page_init() {
    unsafe {
        let _ = crate::page_helpers::page_hash_tables_init_body_result(
            core::ptr::addr_of!(PAGE_INIT_HASH_FIRST) as usize,
            core::ptr::addr_of!(PAGE_INIT_LOCK_FIRST) as usize,
            page_init_hash_bucket_count,
            page_init_hash_head_stride,
            page_unmap_lock_stride,
            Some(page_init_lock_callback),
            Some(crate::page_helpers::page_hash_bucket_init_result),
        );
    }
}

// Same already-selected Rust provider symbols, declared with the existing
// page_helpers usize address ABI (unsigned long on supported x86_64).
unsafe extern "C" {
    #[link_name = "page_hash_lock_bridge"]
    fn page_count_lock_callback(lock_addr: usize) -> CULong;
    #[link_name = "page_hash_unlock_bridge"]
    fn page_count_unlock_callback(lock_addr: usize, flags: CULong);
}

/// Count through the unchanged Rust orchestrator and exact existing geometry.
#[no_mangle]
pub unsafe extern "C" fn page_hash_count_pages() -> CInt {
    unsafe {
        crate::page_helpers::page_hash_count_pages_body_result(
            core::ptr::addr_of!(PAGE_INIT_HASH_FIRST) as usize,
            core::ptr::addr_of!(PAGE_INIT_LOCK_FIRST) as usize,
            page_init_hash_bucket_count,
            page_init_hash_head_stride,
            page_unmap_lock_stride,
            Some(page_count_lock_callback),
            Some(page_count_unlock_callback),
            Some(crate::page_helpers::page_hash_count_all_result),
        )
    }
}

unsafe extern "C" {
    // Existing statically owned 512-node array. The provider's runtime node
    // count remains the original validity bound; no new extent/null policy.
    static mem_query_free_nodes: *mut MemNumaNode;
}

/// Complete supported IHK_RBTREE_ALLOCATOR accounting callback.
/// Reuse the existing typed guard/read helper; narrowing to int matches the
/// original unsigned-long counter assignment to the callback's int result.
#[no_mangle]
pub unsafe extern "C" fn mem_query_free_node_pages_bridge(node: CInt) -> CInt {
    unsafe {
        mem_dump_free_pages_public_result(
            mem_query_free_nodes,
            node,
            Some(ihk_mc_get_nr_numa_nodes),
        ) as CInt
    }
}

/// Exact ordinary (not dkprintf) total-accounting event and int argument.
#[no_mangle]
pub unsafe extern "C" fn mem_query_free_total_log_bridge(pages: CInt) {
    unsafe { kprintf(b"McKernel free pages in total: %d\n\0".as_ptr().cast::<i8>(), pages); }
}

/// Exact page-hash accounting event, preserving signed count and newline.
#[no_mangle]
pub unsafe extern "C" fn mem_query_free_page_hash_log_bridge(pages: CInt) {
    unsafe { kprintf(b"Page hash: %d pages active\n\0".as_ptr().cast::<i8>(), pages); }
}

/// Same already-Rust tracked-allocator checker. The interrupt consumer still
/// decides whether memdebug enables it; no new lock, scan or lifetime action.
#[no_mangle]
pub unsafe extern "C" fn mem_query_free_kmalloc_memcheck_bridge() {
    unsafe { kmalloc_memcheck() }
}

/// Declarative C addresses retain the existing private allocator/provider owners.
#[repr(C)]
struct MemRegisterKmallocMetadata {
    allocator: *mut IhkMcPaOps,
    debug_alloc: Option<MemRegisterAllocFn>,
    debug_free: Option<MemRegisterFreeFn>,
    base_alloc: Option<MemRegisterAllocFn>,
    base_free: Option<MemRegisterFreeFn>,
}
unsafe extern "C" {
    static mem_register_kmalloc_metadata: MemRegisterKmallocMetadata;
}

/// Same selected C entry: sample memdebug, then assign alloc and free in order.
#[no_mangle]
pub unsafe extern "C" fn register_kmalloc() {
    unsafe {
        let metadata = &mem_register_kmalloc_metadata;
        let _ = mem_register_kmalloc_result(
            metadata.allocator, (!MEMDEBUG.is_null()) as CInt,
            metadata.debug_alloc, metadata.debug_free,
            metadata.base_alloc, metadata.base_free,
        );
    }
}

/// Immutable original C-source diagnostic identity, never Rust file!/line!.
#[repr(C)]
struct MemTrackedRedirectionSource {
    file: *const i8,
    line: CInt,
}
unsafe extern "C" {
    static mem_tracked_alloc_redirection_source: MemTrackedRedirectionSource;
    static mem_tracked_free_redirection_source: MemTrackedRedirectionSource;
}

#[no_mangle]
pub unsafe extern "C" fn __kmalloc(size: CInt, flag: CULong) -> *mut c_void {
    unsafe {
        let source = &mem_tracked_alloc_redirection_source;
        kmalloc_tracked(size, flag, source.file.cast_mut(), source.line)
    }
}

#[no_mangle]
pub unsafe extern "C" fn __kfree(ptr: *mut c_void) {
    unsafe {
        let source = &mem_tracked_free_redirection_source;
        kfree_tracked(ptr, source.file.cast_mut(), source.line)
    }
}

unsafe extern "C" {
    static mem_cache_alloc_redirection_source: MemTrackedRedirectionSource;
}
/// Exact existing C size_t-to-int conversion at tracked allocation boundary.
#[no_mangle]
pub unsafe extern "C" fn kmalloc_cache_alloc_bridge(size: SizeT, flag: CULong) -> *mut c_void {
    unsafe {
        let source = &mem_cache_alloc_redirection_source;
        kmalloc_tracked(size as CInt, flag, source.file.cast_mut(), source.line)
    }
}

#[repr(C)]
struct MemLowlevelKmallocMetadata {
    remote_lock_offset: CULong,
    remote_list_offset: CULong,
    irq_save: Option<MemKmallocIrqSaveFn>,
    irq_restore: Option<MemKmallocIrqRestoreFn>,
    alloc_pages: Option<MemKmallocAllocPagesFn>,
    get_cpu_local: Option<MemKmallocGetCpuLocalVarFn>,
    remote_lock: Option<MemKmallocSpinLockFn>,
    remote_unlock: Option<MemKmallocSpinUnlockFn>,
    corruption: Option<MemKmallocCorruptionFn>,
}
unsafe extern "C" {
    static mem_lowlevel_kmalloc_metadata: MemLowlevelKmallocMetadata;
}

/// Original selected C computes its CPU-local free-list before the body call.
#[no_mangle]
pub unsafe extern "C" fn ___kmalloc(size: CInt, flag: CULong) -> *mut c_void {
    unsafe {
        let free_list = core::ptr::addr_of_mut!((*get_this_cpu_local_var()).free_list);
        let m = &mem_lowlevel_kmalloc_metadata;
        ___kmalloc_body_result(size, flag, free_list,
            m.irq_save, m.irq_restore, m.alloc_pages)
    }
}

/// Even NULL preserves the selected C CPU-local lookup before the Rust no-op.
#[no_mangle]
pub unsafe extern "C" fn ___kfree(ptr: *mut c_void) {
    unsafe {
        let free_list = core::ptr::addr_of_mut!((*get_this_cpu_local_var()).free_list);
        let m = &mem_lowlevel_kmalloc_metadata;
        let _ = ___kfree_body_result(ptr, free_list,
            m.remote_lock_offset, m.remote_list_offset,
            m.irq_save, m.irq_restore, m.get_cpu_local,
            m.remote_lock, m.remote_unlock, m.corruption);
    }
}

/// Same existing reviewed assembly endpoint; no added IRQ or fence policy.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_irq_save_bridge() -> CULong {
    unsafe { crate::x86_cpu_helpers::cpu_disable_interrupt_save() }
}
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_irq_restore_bridge(flags: CULong) {
    unsafe { crate::x86_cpu_helpers::cpu_restore_interrupt(flags) }
}
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_alloc_pages_bridge(
    npages: CInt, flag: CULong, is_user: CInt,
) -> *mut c_void {
    unsafe { ___ihk_mc_alloc_pages(npages, flag, is_user) }
}
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_get_cpu_local_var_bridge(cpu: CInt) -> *mut c_void {
    unsafe { crate::cls::get_cpu_local_var(cpu).cast::<c_void>() }
}

/// Exact arch-lock.h selected ihk_mc_spinlock_lock macro target.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_remote_lock_bridge(lock_addr: CULong) -> CULong {
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_lock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock)
    }
}
/// Same ticket release/preempt-enable followed by original full IRQ restore.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_remote_unlock_bridge(lock_addr: CULong, flags: CULong) {
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_unlock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock, flags)
    }
}

unsafe extern "C" {
    // The genuine ihk/debug.h ABI is void panic(const char *), not a Rust ! ABI.
    #[link_name = "panic"]
    fn mem_kmalloc_panic(message: *const i8);
}

/// Preserve the low-level free corruption diagnostic and panic endpoint order.
///
/// # Safety
/// The caller retains the original allocator IRQ/ownership context. `ptr` is
/// formatted as an address and is never dereferenced by this wrapper. The
/// existing logging and panic providers must obey their genuine C ABIs.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_corruption_bridge(ptr: *mut c_void) {
    // SAFETY: Both strings have static lifetime and terminating NUL bytes. The
    // varargs retain the original const-char-pointer and void-pointer types.
    // No IRQ restoration, list operation or pointer dereference is inserted.
    unsafe {
        kprintf(
            b"%s: memory corruption at address 0x%p\n\0".as_ptr().cast::<i8>(),
            b"___kfree\0".as_ptr().cast::<i8>(),
            ptr,
        );
        mem_kmalloc_panic(b"panic\0".as_ptr().cast::<i8>());
    }
}

unsafe extern "C" {
    // Existing C-owned tracking state, already externally linked in mem.c.
    #[link_name = "kmalloc_track_initialized"]
    static mut MEM_KMALLOC_TRACK_INITIALIZED: CInt;
}

/// Initialize the current CPU allocator and first-use tracking tables.
///
/// # Safety
/// The caller must retain the original boot/per-CPU initialization exclusion.
/// Existing C-owned arrays and state must remain valid and exclusively writable
/// for initialization. The CPU-local provider and allocator callbacks retain
/// their original lifetime, IRQ and ownership contracts.
#[no_mangle]
pub unsafe extern "C" fn kmalloc_init() {
    // SAFETY: Raw addresses name the same C-owned slots and existing typed arrays
    // as the selected C wrapper. They create no references or ownership transfer.
    // The unchanged helper registers callbacks before first-use memdebug lookup,
    // initializes CPU lists on every call, and gates global table initialization.
    unsafe {
        let _ = mem_kmalloc_init_body_result(
            &raw mut MEMDEBUG,
            &raw mut MEM_KMALLOC_TRACK_INITIALIZED,
            (&raw mut KMALLOC_TRACK_HASH).cast::<AbiListHead>(),
            (&raw mut KMALLOC_TRACK_HASH_LOCKS).cast::<IhkSpinlock>(),
            (&raw mut KMALLOC_ADDR_HASH).cast::<AbiListHead>(),
            (&raw mut KMALLOC_ADDR_HASH_LOCKS).cast::<IhkSpinlock>(),
            KMALLOC_TRACK_HASH_SIZE as CInt,
            Some(get_this_cpu_local_var),
            Some(register_kmalloc),
            Some(find_command_line),
            Some(mem_kmalloc_track_spin_init_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn mem_vmap_init_bridge(start: CULong, size: CULong, unit: CULong) -> *mut c_void {
    unsafe { crate::page_alloc::ihk_pagealloc_init(start, size, unit) }
}

#[no_mangle]
pub unsafe extern "C" fn mem_vmap_alloc_bridge(desc: *mut c_void, npages: CInt, p2align: CInt) -> CULong {
    unsafe { crate::page_alloc::ihk_pagealloc_alloc(desc, npages, p2align) }
}

#[no_mangle]
pub unsafe extern "C" fn mem_vmap_free_bridge(desc: *mut c_void, address: CULong, npages: CInt) {
    unsafe { crate::page_alloc::ihk_pagealloc_free(desc, address, npages) }
}

#[no_mangle]
pub unsafe extern "C" fn mem_pt_prepare_map_bridge(
    pt: *mut c_void,
    virt: *mut c_void,
    size: CULong,
    flag: CInt,
) -> CInt {
    unsafe { crate::x86_memory_helpers::ihk_mc_pt_prepare_map(pt, virt, size, flag) }
}

#[repr(C)]
struct MemQueryFreeInterruptMetadata {
    fugaku_panic: CInt,
    attached_mic: CInt,
    sbox_scratch0: CInt,
    sbox_scratch1: CInt,
    nr_nodes: Option<MemGetNrNumaNodesFn>,
    node_pages: Option<MemQueryFreeNodePagesFn>,
    total_log: Option<MemQueryFreeLogFn>,
    panic_fn: Option<MemVoidFn>,
    find_command_line: Option<MemFindCommandLineFn>,
    kmalloc_memcheck_fn: Option<MemVoidFn>,
    pagealloc_memcheck_fn: Option<MemVoidFn>,
    page_hash_count: Option<MemQueryPageHashCountFn>,
    page_hash_log: Option<MemQueryFreeLogFn>,
    sbox_write: Option<MemQuerySboxWriteFn>,
}

unsafe extern "C" {
    static mem_query_free_interrupt_metadata: MemQueryFreeInterruptMetadata;
}

/// Run the original synchronous free-memory interrupt orchestration.
///
/// # Safety
/// The caller must retain the original interrupt lifetime and accounting
/// exclusion. Immutable C metadata must name the same valid callbacks/profile.
/// This entry transfers no page, allocator or private-argument ownership.
#[no_mangle]
pub unsafe extern "C" fn query_free_mem_interrupt_handler(priv_arg: *mut c_void) {
    // SAFETY: Metadata is immutable C-owned static data. The unchanged helper
    // retains node enumeration, logging/checker order and conditional effects.
    // The command-name literal has static lifetime; its original lookup API
    // accepts a mutable char pointer but does not receive ownership here.
    unsafe {
        let metadata = &mem_query_free_interrupt_metadata;
        let _ = mem_query_free_mem_interrupt_public_body_result(
            priv_arg,
            metadata.nr_nodes,
            b"memdebug\0".as_ptr().cast::<i8>().cast_mut(),
            metadata.fugaku_panic,
            metadata.attached_mic,
            metadata.sbox_scratch0,
            metadata.sbox_scratch1,
            metadata.node_pages,
            metadata.total_log,
            metadata.panic_fn,
            metadata.find_command_line,
            metadata.kmalloc_memcheck_fn,
            metadata.pagealloc_memcheck_fn,
            metadata.page_hash_count,
            metadata.page_hash_log,
            metadata.sbox_write,
        );
    }
}

/// Check the original inclusive physical chunk interval without taking ownership.
///
/// # Safety
/// Existing chunk callbacks must retain their normal synchronous output-buffer
/// and memory-topology contracts. This wrapper adds no pointer dereference.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_chk_page_address(mem_addr: CULong) -> CInt {
    // SAFETY: These are the exact existing providers used by the selected C
    // entry. The unchanged helper owns local output slots and preserves -1/0.
    unsafe {
        mem_chk_page_address_result(
            mem_addr,
            Some(ihk_mc_get_nr_memory_chunks),
            Some(ihk_mc_get_memory_chunk),
        )
    }
}

/// Mark a user mapping in the caller-owned dump bitmap using the existing helper.
///
/// # Safety
/// `arg0` must retain the original dump descriptor/buffer lifetime and exclusion.
/// When active/user processing applies, `ptep` and the dump records must satisfy
/// the existing PTE and bitmap layout contracts. No Page reference is acquired.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_get_mem_user_page(
    arg0: *mut c_void,
    _pt: *mut c_void,
    ptep: *mut CULong,
    _pgaddr: *mut c_void,
    pgshift: CInt,
) -> CInt {
    // SAFETY: The opaque descriptor and PTE pointer are cast exactly as in the
    // selected C entry. The existing helper retains its early guards, physical
    // mask, bitmap writes, warning callback and integer return convention.
    unsafe {
        mem_get_mem_user_page_result(
            arg0.cast::<DumpPaseInfo>(),
            ptep,
            pgshift,
            Some(ihk_mc_chk_page_address),
            Some(mem_dump_warn_bridge),
        )
    }
}

unsafe extern "C" {
    static mem_interleave_nodes_mask_bits: CInt;
}

/// Select the next allowed NUMA node with the original wraparound helper.
///
/// # Safety
/// A non-null `numa_mask` must remain readable for the original process mask
/// extent under the caller's existing memory-policy exclusion. This entry
/// borrows the mask synchronously and never changes its words or ownership.
#[no_mangle]
pub unsafe extern "C" fn interleave_nodes(off: CInt, numa_mask: *mut CULong) -> CInt {
    // SAFETY: The immutable C constant is generated from the actual process
    // mask definition. The unchanged helper retains negative-offset handling,
    // wraparound, empty-mask sentinel and its original null-pointer behavior.
    unsafe { mem_interleave_nodes_result(off, numa_mask, mem_interleave_nodes_mask_bits) }
}

#[repr(C)]
struct MemWholeAllocationMetadata {
    nr_nodes: Option<MemGetNrNumaNodesFn>,
    current_vm: Option<MemCurrentVmFn>,
    range_policy_search: Option<MemRangePolicySearchFn>,
    lookup_memory_range: Option<MemLookupMemoryRangeFn>,
    range_is_shm: Option<MemRangeIsShmFn>,
    range_policy_fields: Option<MemPolicyFieldsFn>,
    vm_policy_fields: Option<MemPolicyFieldsFn>,
    current_numa: Option<MemCurrentNumaIdFn>,
    alloc_policy: Option<MemMckernelAllocPolicyFn>,
}

#[repr(C)]
struct MemWholeFreeMetadata {
    pending_pages: Option<MemPendingPagesFn>,
    virt_to_phys: Option<MemVirtToPhysFn>,
    phys_to_page: Option<MemPhysToPageFn>,
    free_in_allocator: Option<MemFreeInAllocatorFn>,
    warn: Option<MemPendingWarnFn>,
    free_body: Option<MemMckernelFreePagesBodyFn>,
}

unsafe extern "C" {
    static mem_whole_allocation_metadata: MemWholeAllocationMetadata;
    static mem_whole_free_metadata: MemWholeFreeMetadata;
    #[link_name = "cpu_local_var_initialized"]
    static mut MEM_CPU_LOCAL_INITIALIZED: CInt;
}

/// Allocate using the original VM policy and NUMA accounting orchestration.
///
/// # Safety
/// The caller must retain the original CPU/VM policy and allocator exclusion.
/// Borrowed VM/range/mask state remains owned by its existing providers, and
/// the returned allocation transfers exactly the original allocator ownership.
#[no_mangle]
pub unsafe extern "C" fn mckernel_allocate_aligned_pages_node(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    pref_node: CInt,
    is_user: CInt,
    virt_addr: CULong,
) -> *mut c_void {
    // SAFETY: Immutable metadata names the exact original selected C callbacks.
    // The initialization flag is sampled once as before, without new locking.
    // The unchanged helper retains argument guards, policy selection and errors.
    unsafe {
        let metadata = &mem_whole_allocation_metadata;
        mem_mckernel_allocate_aligned_pages_node_public_body_result(
            npages,
            p2align,
            flag,
            pref_node,
            is_user,
            virt_addr,
            MEM_CPU_LOCAL_INITIALIZED,
            metadata.nr_nodes,
            metadata.current_vm,
            metadata.range_policy_search,
            metadata.lookup_memory_range,
            metadata.range_is_shm,
            metadata.range_policy_fields,
            metadata.vm_policy_fields,
            metadata.current_numa,
            metadata.alloc_policy,
        )
    }
}

/// Free or defer exactly the caller-owned page batch through the original helper.
///
/// # Safety
/// `va`, `npages` and `is_user` must satisfy the existing allocator/Page ownership
/// contract. The caller retains pending-ring and physical-page lifetime guards.
/// This wrapper creates no Page references and introduces no completion ACK.
#[no_mangle]
pub unsafe extern "C" fn mckernel_free_pages(va: *mut c_void, npages: CInt, is_user: CInt) {
    // SAFETY: These static callback addresses retain their original synchronous
    // lifetimes. The unchanged helper owns pending/free choice and Page updates;
    // its status is discarded exactly as by the original void C entry.
    unsafe {
        let metadata = &mem_whole_free_metadata;
        let _ = mem_mckernel_free_pages_public_body_result(
            va,
            npages,
            is_user,
            metadata.pending_pages,
            metadata.virt_to_phys,
            metadata.phys_to_page,
            metadata.free_in_allocator,
            metadata.warn,
            metadata.free_body,
        );
    }
}

/// Borrow the original current VM without acquiring a reference.
///
/// # Safety
/// The caller retains the existing CPU-local/current-thread lifetime guards.
/// Initialized CPU state must provide the same valid CPU-local record as C.
#[no_mangle]
pub unsafe extern "C" fn mem_current_vm_bridge() -> *mut c_void {
    // SAFETY: Preserve the original initialization guards and two flag reads.
    // CPU/thread/VM pointers are only read and returned as synchronous borrows.
    unsafe {
        let mut thread = null_mut::<crate::abi::Thread>();
        let mut vm = null_mut();
        if MEM_CPU_LOCAL_INITIALIZED != 0 {
            thread = (*get_this_cpu_local_var()).current;
            if !thread.is_null() {
                vm = (*thread).vm.cast::<c_void>();
            }
        }
        mem_current_vm_result(MEM_CPU_LOCAL_INITIALIZED, thread.cast::<c_void>(), vm)
    }
}

/// Apply the existing exact shared-memory flag predicate to a borrowed range.
///
/// # Safety
/// A non-null range and its non-null memobj must remain valid under the caller's
/// existing VM-range/memobj lifetime and memory-policy exclusion.
#[no_mangle]
pub unsafe extern "C" fn mem_range_is_shm_bridge(range: *mut c_void) -> CInt {
    // SAFETY: Match the original range and memobj guards before each field load.
    // The unsigned memobj flags are widened without changing their bits.
    unsafe {
        let range = range.cast::<VmRange>();
        if range.is_null() {
            return mem_range_is_shm_result(0, 0, 0);
        }
        let memobj = (*range).memobj.cast::<Memobj>();
        if memobj.is_null() {
            return mem_range_is_shm_result(1, 0, 0);
        }
        mem_range_is_shm_result(1, 1, (*memobj).flags as CULong)
    }
}

/// Expose the existing range-policy fields as synchronous borrowed addresses.
///
/// # Safety
/// A non-null policy must be a live real VmRangeNumaPolicy. Non-null output
/// slots must be writable exactly as for the existing C helper call. The caller
/// retains all policy/list lifetime and synchronization guards.
#[no_mangle]
pub unsafe extern "C" fn mem_range_policy_fields_bridge(
    policy: *mut c_void,
    numa_mem_policy: *mut CInt,
    numa_mask: *mut *mut CULong,
    il_prev: *mut *mut CInt,
) {
    // SAFETY: No references or policy ownership are created. Read scalar input
    // before the unchanged helper writes any possibly aliased output slots.
    unsafe {
        let policy = policy.cast::<crate::abi::VmRangeNumaPolicy>();
        let (value, mask, previous) = if policy.is_null() {
            (-1, null_mut(), null_mut())
        } else {
            (
                (*policy).numa_mem_policy,
                core::ptr::addr_of_mut!((*policy).numa_mask).cast::<CULong>(),
                core::ptr::addr_of_mut!((*policy).il_prev),
            )
        };
        let _ = mem_policy_fields_result(
            (!policy.is_null()) as CInt,
            value,
            mask,
            previous,
            numa_mem_policy,
            numa_mask,
            il_prev,
        );
    }
}

/// Expose the process policy fields without taking VM or mask ownership.
///
/// # Safety
/// A non-null VM must remain live under the original policy exclusion.
/// Non-null output slots must satisfy the existing writable/aliasing contract.
#[no_mangle]
pub unsafe extern "C" fn mem_vm_policy_fields_bridge(
    vm: *mut c_void,
    numa_mem_policy: *mut CInt,
    numa_mask: *mut *mut CULong,
    il_prev: *mut *mut CInt,
) {
    // SAFETY: Match the original null guard and scalar/address evaluation before
    // helper writes. The returned addresses borrow the same existing fields.
    unsafe {
        let vm = vm.cast::<ProcessVm>();
        let (value, mask, previous) = if vm.is_null() {
            (-1, null_mut(), null_mut())
        } else {
            (
                (*vm).numa_mem_policy,
                core::ptr::addr_of_mut!((*vm).numa_mask).cast::<CULong>(),
                core::ptr::addr_of_mut!((*vm).il_prev),
            )
        };
        let _ = mem_policy_fields_result(
            (!vm.is_null()) as CInt,
            value,
            mask,
            previous,
            numa_mem_policy,
            numa_mask,
            il_prev,
        );
    }
}

unsafe extern "C" {
    fn ihk_mc_get_numa_id() -> CInt;
}

/// Borrow the original distance-table node identifier.
///
/// # Safety
/// The existing node array and distance tables must remain initialized/live
/// under the caller's original topology lifetime exclusion.
#[no_mangle]
pub unsafe extern "C" fn mem_distance_id_bridge(base_node: CInt, index: CInt) -> CInt {
    // SAFETY: The existing immutable C array pointer names the same memory_nodes;
    // the unchanged helper retains all bounds and missing-table guards.
    unsafe {
        mem_distance_id_public_result(
            mem_query_free_nodes,
            base_node,
            index,
            Some(ihk_mc_get_nr_numa_nodes),
        )
    }
}

/// Read one allowed-node bit through the existing process-mask helper.
///
/// # Safety
/// A non-null mask must remain readable for the original process mask extent
/// under existing memory-policy synchronization. The mask remains borrowed.
#[no_mangle]
pub unsafe extern "C" fn mem_mask_test_bridge(numa_id: CInt, mask: *mut CULong) -> CInt {
    // SAFETY: Exact C-generated geometry and the original guarded helper.
    unsafe { mem_mask_test_result(numa_id, mask, mem_interleave_nodes_mask_bits) }
}

/// Preserve the original current-CPU NUMA provider call.
///
/// # Safety
/// The caller must retain the original CPU-local execution context.
#[no_mangle]
pub unsafe extern "C" fn mem_current_numa_id_bridge() -> CInt {
    // SAFETY: This is exactly the preexisting C ABI provider, without caching
    // the CPU id, changing affinity or adding preemption/IRQ operations.
    unsafe { ihk_mc_get_numa_id() }
}

/// Borrow the node selected by the original current-node distance ordering.
///
/// # Safety
/// CPU initialization state and node/distance tables retain their existing
/// lifetime and topology synchronization. No reference is acquired.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_get_numa_node_by_distance(index: CInt) -> *mut MemNumaNode {
    // SAFETY: Same array, one state snapshot and the exact original helpers.
    unsafe {
        mem_get_numa_node_by_distance_public_result(
            mem_query_free_nodes,
            MEM_CPU_LOCAL_INITIALIZED,
            index,
            Some(ihk_mc_get_nr_numa_nodes),
            Some(mem_current_numa_id_bridge),
        )
    }
}

/// Return the existing node record as a synchronous opaque borrow.
///
/// # Safety
/// The topology provider and C-owned array must retain their original lifetime.
#[no_mangle]
pub unsafe extern "C" fn mem_get_numa_node_bridge(numa_id: CInt) -> *mut c_void {
    // SAFETY: The helper retains its signed bounds checks; no new guard/refcount.
    unsafe {
        mem_get_numa_node_public_result(
            mem_query_free_nodes,
            ihk_mc_get_nr_numa_nodes(),
            numa_id,
        )
        .cast::<c_void>()
    }
}

#[repr(C)]
struct MemRemainingAllocPolicyMetadata {
    try_alloc: Option<MemTryAllocNodeFn>,
    rusage_add: Option<MemRusageAddFn>,
    phys_to_virt: Option<MemPhysToVirtFn>,
    log: Option<MemAllocLogFn>,
}

unsafe extern "C" {
    static mem_remaining_alloc_policy_metadata: MemRemainingAllocPolicyMetadata;
}

/// Execute the original complete NUMA policy and accounting orchestration.
///
/// # Safety
/// The caller must retain the original allocation, policy-mask and interleave
/// cursor ownership/exclusion. Returned memory has exactly the existing
/// allocator ownership; this wrapper acquires no Page or VM references.
#[no_mangle]
pub unsafe extern "C" fn mem_mckernel_alloc_policy_bridge(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    pref_node: CInt,
    is_user: CInt,
    current_node: CInt,
    nr_nodes: CInt,
    numa_mem_policy: CInt,
    chk_shm: CInt,
    numa_mask: *mut CULong,
    il_prevp: *mut CInt,
) -> *mut c_void {
    // SAFETY: The four immutable addresses are the exact remaining C providers.
    // Three already-ported callbacks name their same Rust algorithms directly.
    // The unchanged policy helper owns retry/order/accounting/error behavior.
    unsafe {
        let metadata = &mem_remaining_alloc_policy_metadata;
        mem_mckernel_alloc_policy_result(
            npages,
            p2align,
            flag,
            pref_node,
            is_user,
            current_node,
            nr_nodes,
            numa_mem_policy,
            chk_shm,
            numa_mask,
            il_prevp,
            metadata.try_alloc,
            Some(mem_distance_id_bridge),
            Some(mem_mask_test_bridge),
            Some(interleave_nodes),
            metadata.rusage_add,
            metadata.phys_to_virt,
            metadata.log,
        )
    }
}

/// Convert the original physical address using the existing selected mapping.
///
/// # Safety
/// The caller retains the original address-space/bootstrap mapping context.
#[no_mangle]
pub unsafe extern "C" fn mem_phys_to_virt_bridge(pa: CULong) -> *mut c_void {
    // SAFETY: Same existing mapping provider and unchanged unsigned address.
    unsafe { crate::x86_memory_helpers::phys_to_virt(pa) }
}

/// Convert the original raw virtual address without acquiring memory ownership.
///
/// # Safety
/// The original address classification and mapping context must remain valid.
#[no_mangle]
pub unsafe extern "C" fn mem_virt_to_phys_bridge(va: *mut c_void) -> CULong {
    // SAFETY: Same selected provider; its own mapping/diagnostic guards remain.
    unsafe { crate::x86_memory_helpers::virt_to_phys(va) }
}

/// Preserve the C int-to-unsigned-long page conversion at the OOM provider.
///
/// # Safety
/// The original rusage accounting state and execution exclusion must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_rusage_check_oom_bridge(
    numa_id: CInt,
    npages: CInt,
    is_user: CInt,
) -> CInt {
    // SAFETY: This matches the genuine rusage_private.h ulong pages prototype.
    unsafe { rusage_check_oom(numa_id, npages as CULong, is_user) }
}

/// Add exactly the original page amount to existing rusage accounting.
///
/// # Safety
/// The caller retains the existing allocation/accounting ownership contract.
#[no_mangle]
pub unsafe extern "C" fn mem_rusage_page_add_bridge(
    numa_id: CInt,
    npages: CInt,
    is_user: CInt,
) {
    // SAFETY: Same integer conversion and actual atomic/accounting provider.
    unsafe { rusage_page_add(numa_id, npages as CULong, is_user) }
}

/// Subtract the original page amount after the existing release operation.
///
/// # Safety
/// The caller must own the released batch and existing accounting exclusion.
#[no_mangle]
pub unsafe extern "C" fn mem_rusage_page_sub_bridge(
    numa_id: CInt,
    npages: CInt,
    is_user: CInt,
) {
    // SAFETY: Preserve even the original signed-to-ulong conversion, without
    // inserting a clamp, added accounting update or new error convention.
    unsafe { rusage_page_sub(numa_id, npages as CULong, is_user) }
}

/// Allocate from the same actual NUMA-node provider.
///
/// # Safety
/// `node` must be the original live C-layout NUMA record under its existing
/// allocator synchronization. Returned physical pages retain original ownership.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_alloc_node_bridge(
    node: *mut MemNumaNode,
    npages: CInt,
    p2align: CInt,
) -> CULong {
    // SAFETY: Both real Rust node representations bind the same C256/align64
    // record. The provider retains all cache, locking and allocation semantics.
    unsafe {
        crate::page_alloc::ihk_numa_alloc_pages(
            node.cast::<crate::page_alloc::IhkMcNumaNode>(),
            npages,
            p2align,
        )
    }
}

/// Release exactly the original batch through the actual NUMA provider.
///
/// # Safety
/// The node, physical address and page count retain the original allocator
/// ownership and caller exclusion. No Page reference is acquired by this entry.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_free_bridge(node: *mut c_void, addr: CULong, npages: CInt) {
    // SAFETY: The same opaque C pointer now names the actual typed Rust provider;
    // no layout is copied or dereferenced by this forwarding wrapper.
    unsafe {
        crate::page_alloc::ihk_numa_free_pages(
            node.cast::<crate::page_alloc::IhkMcNumaNode>(),
            addr,
            npages,
        );
    }
}

/// Find the original physical chunk, release the batch and subtract accounting.
///
/// # Safety
/// The caller must retain its original page-batch ownership and topology/node
/// lifetime guards. The existing helper decides whether any chunk owns the span.
#[no_mangle]
pub unsafe extern "C" fn __mckernel_free_pages_in_allocator(
    va: *mut c_void,
    npages: CInt,
    is_user: CInt,
) {
    // SAFETY: Exact original selected helper and callback providers. Its status
    // is discarded as by the void C entry; release and accounting order remain.
    unsafe {
        let _ = mem_free_pages_in_allocator_rbtree_result(
            va,
            npages,
            is_user,
            Some(ihk_mc_get_nr_memory_chunks),
            Some(ihk_mc_get_memory_chunk),
            Some(mem_virt_to_phys_bridge),
            Some(mem_get_numa_node_bridge),
            Some(mem_numa_free_bridge),
            Some(mem_rusage_page_sub_bridge),
        );
    }
}

/// Preserve the synchronous physical allocator-free callback.
///
/// # Safety
/// The original batch ownership and physical allocator contract must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_free_in_allocator_bridge(
    va: *mut c_void,
    npages: CInt,
    is_user: CInt,
) {
    // SAFETY: Direct same entry, with no extra release or completion action.
    unsafe { __mckernel_free_pages_in_allocator(va, npages, is_user) }
}

/// Convert and free the same detached pending batch without inventing an ACK.
///
/// # Safety
/// The caller must have detached/owned the original pending Page batch and
/// retained its physical mapping lifetime until this synchronous free returns.
#[no_mangle]
pub unsafe extern "C" fn mem_pending_free_bridge(phys: CULong, npages: CInt, is_user: CInt) {
    // SAFETY: Preserve conversion-before-free exactly; no Page field writes,
    // refcount changes, IRQ changes or second accounting update are inserted.
    unsafe {
        let va = crate::x86_memory_helpers::phys_to_virt(phys);
        __mckernel_free_pages_in_allocator(va, npages, is_user);
    }
}

unsafe extern "C" {
    fn ihk_mc_get_numa_node(node: CInt, linux_numa_id: *mut CInt, node_type: *mut CInt) -> CInt;
}

/// Try the original RBTREE node allocator and preserve its OOM output convention.
///
/// # Safety
/// The topology and node allocator must retain their original lifetimes and
/// locks. A non-null `oomp` must be a writable caller-owned C int slot.
#[no_mangle]
pub unsafe extern "C" fn mem_try_alloc_node_bridge(
    numa_id: CInt,
    npages: CInt,
    p2align: CInt,
    is_user: CInt,
    oomp: *mut CInt,
) -> CULong {
    // SAFETY: Same node array and unchanged helper/provider bounds, accounting
    // and OOM semantics. No new allocation claim or output policy is inserted.
    unsafe {
        mem_try_alloc_node_public_result(
            mem_query_free_nodes,
            numa_id,
            npages,
            p2align,
            is_user,
            oomp,
            Some(ihk_mc_get_nr_numa_nodes),
            Some(mem_rusage_check_oom_bridge),
            Some(mem_numa_alloc_node_bridge),
        )
    }
}

/// Initialize the original RBTREE-only node fields under boot exclusion.
///
/// # Safety
/// If `rbtree_allocator` is nonzero, `node` must be a valid exclusively owned
/// real NUMA node during initialization. Zero preserves the original no-access
/// path, including when the pointer is null. This is not runtime node reset.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_node_init_bridge(node: *mut MemNumaNode, rbtree_allocator: CInt) {
    if rbtree_allocator == 0 {
        return;
    }
    // SAFETY: The caller's initialization exclusion covers all fields. Real
    // ABI atomic/MCS/list representations have the same C layout; use the
    // existing selected atomic, list and MCS initialization providers in order.
    unsafe {
        crate::atomic_helpers::ihk_atomic_set(
            core::ptr::addr_of_mut!((*node).zeroing_workers)
                .cast::<crate::atomic_helpers::IhkAtomic>(),
            0,
        );
        crate::atomic_helpers::ihk_atomic_set(
            core::ptr::addr_of_mut!((*node).nr_to_zero_pages)
                .cast::<crate::atomic_helpers::IhkAtomic>(),
            0,
        );
        (*node).free_chunks.rb_node = null_mut();
        crate::llist::init_llist_head(core::ptr::addr_of_mut!((*node).zeroed_list));
        crate::llist::init_llist_head(core::ptr::addr_of_mut!((*node).to_zero_list));
        crate::lock_helpers::mcs_lock_init(
            core::ptr::addr_of_mut!((*node).lock).cast::<crate::lock_helpers::McsLockNode>(),
        );
        (*node).min_addr = CULong::MAX;
        (*node).max_addr = 0;
        (*node).nr_pages = 0;
        (*node).nr_free_pages = 0;
    }
}

/// Add the original physical span through the existing actual NUMA provider.
///
/// # Safety
/// The node and range retain the original boot/allocator ownership and guards.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_add_free_pages_bridge(
    node: *mut MemNumaNode,
    start: CULong,
    len: CULong,
) {
    // SAFETY: Same real C-layout node and exact span; existing provider owns
    // page geometry, zeroing, list/RBTREE synchronization and errors.
    unsafe {
        crate::page_alloc::ihk_numa_add_free_pages(
            node.cast::<crate::page_alloc::IhkMcNumaNode>(),
            start,
            len,
        );
    }
}

/// Preserve the original null allocator guard before reading the page count.
///
/// # Safety
/// A non-null descriptor must be the original live actual allocator object.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_pagealloc_count_bridge(allocator: *mut c_void) -> CULong {
    if allocator.is_null() {
        return 0;
    }
    // SAFETY: Exactly the existing actual Rust descriptor/count provider.
    unsafe { crate::page_alloc::ihk_pagealloc_count(allocator) }
}

/// Forward the original topology-query outputs and status without new policy.
///
/// # Safety
/// Output pointers must satisfy the genuine topology provider's C ABI contract.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_get_node_info_bridge(
    node: CInt,
    linux_numa_id: *mut CInt,
    node_type: *mut CInt,
) -> CInt {
    // SAFETY: Same existing ihk/mm.h provider and unmodified caller pointers.
    unsafe { ihk_mc_get_numa_node(node, linux_numa_id, node_type) }
}

#[repr(C)]
struct MemRusageEntryMetadata {
    state_bytes: CULong,
    cpu_info: Option<MemGetCpuInfoFn>,
    nr_nodes: Option<MemGetNrNumaNodesFn>,
    ns_per_tsc: Option<MemGetNsPerTscFn>,
    virt_to_phys: Option<MemVirtToPhysFn>,
    set_rusage: Option<MemSetRusageFn>,
    panic_fn: Option<MemVoidFn>,
    log: Option<MemRusageInitLogFn>,
}

#[repr(C)]
struct MemDistanceEntryMetadata {
    nr_nodes: Option<MemGetNrNumaNodesFn>,
    alloc: Option<MemNumaDistanceAllocFn>,
    distance: Option<MemNumaDistanceFn>,
    alloc_fail: Option<MemNumaDistanceAllocFailLogFn>,
    log: Option<MemNumaDistanceLogFn>,
}

unsafe extern "C" {
    static mem_rusage_entry_metadata: MemRusageEntryMetadata;
    static mem_distance_entry_metadata: MemDistanceEntryMetadata;
    #[link_name = "monitor_init"]
    fn mem_existing_monitor_init();
}

/// Initialize and publish the original C-owned rusage state through its helper.
///
/// # Safety
/// The original boot/init exclusion must cover RUSAGE and all provider calls.
/// The publication endpoint retains its existing ownership and physical mapping.
#[no_mangle]
pub unsafe extern "C" fn rusage_init() {
    // SAFETY: Exact C-generated object size and original callback addresses.
    // Raw global address avoids references; the unchanged helper preserves
    // CPU-info/panic, clear/populate, physical publication and logging order.
    unsafe {
        let metadata = &mem_rusage_entry_metadata;
        let _ = mem_rusage_init_body_result(
            &raw mut RUSAGE,
            metadata.state_bytes,
            metadata.cpu_info,
            metadata.nr_nodes,
            metadata.ns_per_tsc,
            metadata.virt_to_phys,
            metadata.set_rusage,
            metadata.panic_fn,
            metadata.log,
        );
    }
}

/// Allocate and order the original per-node distance tables.
///
/// # Safety
/// Node topology and distance table storage must retain the original boot
/// initialization exclusion, allocation ownership and diagnostic lifetimes.
#[no_mangle]
pub unsafe extern "C" fn numa_distances_init() {
    // SAFETY: Same static node-array borrow and unchanged selected sorting/
    // allocation helper. The void entry discards status as the original C did.
    unsafe {
        let metadata = &mem_distance_entry_metadata;
        let _ = mem_numa_distances_init_public_result(
            mem_query_free_nodes,
            metadata.nr_nodes,
            metadata.alloc,
            metadata.distance,
            metadata.alloc_fail,
            metadata.log,
        );
    }
}

/// Borrow the same C-owned allocator object for the existing boot entry.
///
/// # Safety
/// The caller must retain the existing static allocator initialization order.
#[no_mangle]
pub unsafe extern "C" fn mem_init_allocator_bridge() -> *mut IhkMcPaOps {
    // SAFETY: Metadata already names the exact private allocator address; this
    // returns a borrow only and does not register, initialize or clone it.
    unsafe { mem_register_kmalloc_metadata.allocator }
}

/// Forward the existing monitor initialization without changing its owner.
///
/// # Safety
/// The original monitor initialization prerequisites must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_monitor_init_bridge() {
    // SAFETY: Same preexisting C ABI provider; its body remains explicit debt.
    unsafe { mem_existing_monitor_init() }
}

/// Invoke the same rusage initialization entry synchronously.
///
/// # Safety
/// The original rusage boot exclusion and publication prerequisites must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_rusage_init_bridge() {
    // SAFETY: Exactly the existing initialization operation, once.
    unsafe { rusage_init() }
}

/// Invoke the existing actual Rust page-table hash initialization entry.
///
/// # Safety
/// The original page-hash initialization exclusion and storage must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_page_init_bridge() {
    // SAFETY: Same already-passed page_init body and initialization lifetime.
    unsafe { page_init() }
}

/// Delegate to the still-C-selected virtual allocator initialization entry.
///
/// # Safety
/// The original virtual allocator initialization order and ownership must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_virtual_allocator_init_bridge() {
    // SAFETY: Same synchronous boot entry now delegates to the coherent private
    // whole Rust initializer. No duplicate init, new lifetime or status policy.
    unsafe { virtual_allocator_init() }
}

/// Return the same borrowed command-line match from the existing Rust parser.
///
/// # Safety
/// The caller's name pointer must satisfy the original find_command_line ABI.
#[no_mangle]
pub unsafe extern "C" fn mem_find_command_line_bridge(name: *mut i8) -> *mut i8 {
    // SAFETY: Same pointer, provider and returned borrow; no string ownership.
    unsafe { find_command_line(name) }
}

/// Invoke the same distance-table initialization entry once.
///
/// # Safety
/// The original topology/table initialization exclusion must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_distances_init_bridge() {
    // SAFETY: No extra allocation, logging, lock or ownership operation.
    unsafe { numa_distances_init() }
}

unsafe extern "C" {
    fn kprintf_lock() -> CULong;
    fn kprintf_unlock(irqflags: CULong);
    fn __kprintf(format: *const i8, ...) -> CInt;
}

/// Print the original current-CPU free list under the existing output lock.
///
/// # Safety
/// The current CPU record and traversed chunks must retain the original valid
/// free-list lifetime/stability assumptions. The output lock serializes logging;
/// this wrapper does not claim it supplies a new allocator ownership lock.
/// The original `list` parameter remains intentionally unused.
#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_print_free_list(_list: *mut AbiListHead) {
    // SAFETY: Exact existing logging ABIs and static NUL-terminated formats.
    // Traverse the real list without references or field writes. Preserve the
    // C initial CPU lookup and one lookup on every loop-condition evaluation;
    // do not cache a CPU pointer or add preemption/IRQ operations around it.
    unsafe {
        let irqflags = kprintf_lock();
        let name = b"___kmalloc_print_free_list\0".as_ptr().cast::<i8>();
        __kprintf(b"%s: [ \n\0".as_ptr().cast::<i8>(), name);
        let mut node = (*get_this_cpu_local_var()).free_list.next;
        loop {
            let head = core::ptr::addr_of_mut!((*get_this_cpu_local_var()).free_list);
            if node == head {
                break;
            }
            let chunk = list_to_kmalloc_header(node);
            let address = chunk as CULong;
            __kprintf(
                b"%s: 0x%lx:%d (VA PFN: %lu, off: %lu)\n\0".as_ptr().cast::<i8>(),
                name,
                address,
                (*chunk).size,
                address >> PAGE_SHIFT,
                address % PAGE_SIZE,
            );
            node = (*node).next;
        }
        __kprintf(b"%s: ] \n\0".as_ptr().cast::<i8>(), name);
        kprintf_unlock(irqflags);
    }
}

#[repr(C)]
struct MemStaticBootAddressMetadata {
    page_fault_handler_address: CULong,
    query_free_handler_address: CULong,
    anon_on_demand_slot: *mut CInt,
    xpmem_remote_slot: *mut CInt,
    hugetlbfs_on_demand_slot: *mut CInt,
}

unsafe extern "C" {
    static mem_static_boot_address_metadata: MemStaticBootAddressMetadata;
}

/// Return the original C handler address without changing its code or ownership.
///
/// # Safety
/// The caller must retain the original boot-registration and function ABI checks.
#[no_mangle]
pub unsafe extern "C" fn mem_init_page_fault_handler_bridge() -> CULong {
    // SAFETY: This immutable integer is the exact C-generated function-address
    // conversion. The still-C handler is not invoked or retyped by this getter.
    unsafe { mem_static_boot_address_metadata.page_fault_handler_address }
}

/// Borrow the existing private interrupt registration object address.
///
/// # Safety
/// The caller retains its original registration-object lifetime and exclusion.
#[no_mangle]
pub unsafe extern "C" fn mem_init_query_free_handler_bridge() -> CULong {
    // SAFETY: The immutable C address names the same original static object.
    unsafe { mem_static_boot_address_metadata.query_free_handler_address }
}

/// Borrow the original anonymous-demand policy slot without reading its value.
///
/// # Safety
/// The caller must retain the original boot policy-slot lifetime and exclusion.
#[no_mangle]
pub unsafe extern "C" fn mem_init_anon_on_demand_bridge() -> *mut CInt {
    // SAFETY: Return the C-owned slot address only, without creating a reference.
    unsafe { mem_static_boot_address_metadata.anon_on_demand_slot }
}

/// Borrow the original remote XPMEM policy slot without new lifetime ownership.
///
/// # Safety
/// The original policy-slot lifetime and initialization exclusion must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_init_xpmem_remote_bridge() -> *mut CInt {
    // SAFETY: Same static C-owned address, no value access or new synchronization.
    unsafe { mem_static_boot_address_metadata.xpmem_remote_slot }
}

/// Return the original profile-selected huge-page policy slot or null.
///
/// # Safety
/// A non-null result retains the original profile's static policy-slot contract.
#[no_mangle]
pub unsafe extern "C" fn mem_init_hugetlbfs_on_demand_bridge() -> *mut CInt {
    // SAFETY: The genuine C configuration selects this pointer; Rust does not
    // invent an optional field, dereference it or substitute a configuration.
    unsafe { mem_static_boot_address_metadata.hugetlbfs_on_demand_slot }
}

/// Allocate tracking storage through the unchanged low-level allocator entry.
///
/// # Safety
/// The caller retains its original tracking/allocator IRQ and ownership context.
/// Returned storage has exactly the existing low-level allocation ownership.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_track_base_alloc_bridge(
    size: CInt,
    flag: CULong,
) -> *mut c_void {
    // SAFETY: Same signed size, flag bits and actual low-level allocator entry.
    unsafe { ___kmalloc(size, flag) }
}

/// Free the original tracking-storage pointer through the same low-level entry.
///
/// # Safety
/// The caller must own the pointer under the original low-level free contract.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_track_base_free_bridge(ptr: *mut c_void) {
    // SAFETY: No extra guard, release or IRQ action; even null follows the same
    // low-level entry and its original CPU-local lookup/no-op behavior.
    unsafe { ___kfree(ptr) }
}

/// Acquire the original tracking lock with its existing IRQ-save semantics.
///
/// # Safety
/// `lock_addr` must name the original live aligned spinlock; caller lock ordering
/// and eventual release obligations remain unchanged.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_track_lock_bridge(lock_addr: CULong) -> CULong {
    // SAFETY: Exact arch-lock.h selected macro target and real spinlock layout.
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_lock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        )
    }
}

/// Release the original tracking lock and restore its full saved IRQ flags.
///
/// # Safety
/// The caller must own the matching lock and supply its original saved flags.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_track_unlock_bridge(lock_addr: CULong, irqflags: CULong) {
    // SAFETY: Same selected release/preemption/IRQ restore provider and arguments.
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_unlock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
            irqflags,
        );
    }
}

/// Initialize the original tracking spinlock under initialization exclusion.
///
/// # Safety
/// The lock must be exclusively owned for initialization and have real alignment.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_track_spin_init_bridge(lock_addr: CULong) {
    // SAFETY: Exact existing selected Rust ticket-lock initialization operation.
    unsafe {
        crate::spinlock_helpers::ihk_mc_spinlock_init(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        );
    }
}

/// Preserve the underlying page batch allocation without tracking recursion.
///
/// # Safety
/// The caller retains the original page allocator, NUMA-policy and tracking
/// ownership/exclusion. Returned pages follow exactly the original provider.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_track_base_alloc_bridge(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    node: CInt,
    is_user: CInt,
    virt_addr: CULong,
) -> *mut c_void {
    // SAFETY: Exact original low-level page entry and unmodified batch tuple.
    unsafe { ___ihk_mc_alloc_aligned_pages_node(npages, p2align, flag, node, is_user, virt_addr) }
}

/// Release the original tracked page batch through its untracked base entry.
///
/// # Safety
/// The caller owns the same batch and retains the original release contract.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_track_base_free_bridge(
    ptr: *mut c_void,
    npages: CInt,
    is_user: CInt,
) {
    // SAFETY: Same provider and values, no new reference or completion ACK.
    unsafe { ___ihk_mc_free_pages(ptr, npages, is_user) }
}

/// Allocate the same bookkeeping bytes through the existing low-level heap.
///
/// # Safety
/// The original tracking/heap lock and IRQ contract must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_track_meta_alloc_bridge(
    size: CInt,
    flag: CULong,
) -> *mut c_void {
    // SAFETY: Original signed size and complete flag bits forwarded once.
    unsafe { ___kmalloc(size, flag) }
}

/// Free exactly the original bookkeeping allocation.
///
/// # Safety
/// The pointer must satisfy the original low-level free ownership contract.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_track_meta_free_bridge(ptr: *mut c_void) {
    // SAFETY: Same low-level free, including its original null behavior.
    unsafe { ___kfree(ptr) }
}

/// Acquire the original tracking spinlock with IRQ save.
///
/// # Safety
/// The address must name the original live aligned lock with valid lock ordering.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_track_lock_bridge(lock_addr: CULong) -> CULong {
    // SAFETY: Same selected architecture macro target and actual Rust lock type.
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_lock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        )
    }
}

/// Release the matching tracking lock and restore the original full IRQ flags.
///
/// # Safety
/// The caller must hold this lock and supply its matching saved flags.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_track_unlock_bridge(lock_addr: CULong, irqflags: CULong) {
    // SAFETY: Same release/preemption/IRQ-restore sequence as the C provider.
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_unlock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
            irqflags,
        );
    }
}

/// Acquire the original no-IRQ tracking lock without adding IRQ operations.
///
/// # Safety
/// The original caller IRQ/preemption and lock ownership prerequisites must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_track_noirq_lock_bridge(lock_addr: CULong) {
    // SAFETY: Exact no-IRQ selected helper; its existing preemption semantics
    // remain, with no substitution by the IRQ-saving helper.
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_lock_noirq(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        );
    }
}

/// Release the matching no-IRQ tracking lock without restoring flags.
///
/// # Safety
/// The caller must own the same no-IRQ lock under its original IRQ context.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_track_noirq_unlock_bridge(lock_addr: CULong) {
    // SAFETY: Same ticket-release/preempt-enable endpoint, no new IRQ action.
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_unlock_noirq(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        );
    }
}

/// Initialize the original tracking lock under exclusive initialization.
///
/// # Safety
/// The lock must be valid, aligned and exclusively owned for initialization.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_track_spin_init_bridge(lock_addr: CULong) {
    // SAFETY: Same actual ticket-lock initialization provider and address.
    unsafe {
        crate::spinlock_helpers::ihk_mc_spinlock_init(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        );
    }
}

unsafe extern "C" {
    fn ihk_mc_get_dump_page_set() -> *mut IhkDumpPageSet;
    fn ihk_mc_get_dump_page() -> *mut IhkDumpPage;
}

/// Reset the existing dump completion field using the original guarded helper.
///
/// # Safety
/// The original dump-set publication lifetime and reset exclusion must hold.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_clear_dump_page_completion() {
    // SAFETY: Same genuine provider and existing volatile-field update helper.
    // The void entry discards its status exactly as the selected C wrapper.
    unsafe {
        let _ = mem_clear_dump_page_completion_result(Some(ihk_mc_get_dump_page_set));
    }
}

/// Borrow the original published dump record, without taking buffer ownership.
///
/// # Safety
/// The caller must retain the provider's dump-record lifetime/exclusion.
#[no_mangle]
pub unsafe extern "C" fn mem_get_dump_page_bridge() -> *mut IhkDumpPage {
    // SAFETY: Exact original ihk/mm.h provider, no dereference or new null policy.
    unsafe { ihk_mc_get_dump_page() }
}

/// Borrow the original published dump-set descriptor.
///
/// # Safety
/// The caller retains the same dump-set lifetime and publication contract.
#[no_mangle]
pub unsafe extern "C" fn mem_get_dump_page_set_bridge() -> *mut IhkDumpPageSet {
    // SAFETY: Same provider and returned raw borrow, no added reference.
    unsafe { ihk_mc_get_dump_page_set() }
}

/// Read the original free-page total through the actual node-array helper.
///
/// # Safety
/// The topology and node accounting must retain their original snapshot guards.
#[no_mangle]
pub unsafe extern "C" fn mem_dump_free_pages_bridge(node: CInt) -> CULong {
    // SAFETY: Same array and topology callback, with unchanged bounds behavior.
    unsafe {
        mem_dump_free_pages_public_result(
            mem_query_free_nodes,
            node,
            Some(ihk_mc_get_nr_numa_nodes),
        )
    }
}

/// Borrow the first free chunk under the original dump traversal contract.
///
/// # Safety
/// The caller retains the original RBTREE/topology traversal exclusion/lifetime.
#[no_mangle]
pub unsafe extern "C" fn mem_dump_first_free_chunk_bridge(node: CInt) -> *mut c_void {
    // SAFETY: Same actual helper, including signed bounds and null root guards.
    unsafe {
        mem_dump_first_free_chunk_public_result(
            mem_query_free_nodes,
            node,
            Some(ihk_mc_get_nr_numa_nodes),
        )
    }
}

/// Borrow the next chunk without retaining or unlinking the current one.
///
/// # Safety
/// A non-null chunk must retain the original free-tree traversal lifetime.
#[no_mangle]
pub unsafe extern "C" fn mem_dump_next_free_chunk_bridge(chunk: *mut c_void) -> *mut c_void {
    // SAFETY: Existing guarded iterator helper only; no new lock or ownership.
    unsafe { mem_dump_next_free_chunk_result(chunk) }
}

/// Read the same free-chunk physical address.
///
/// # Safety
/// A non-null chunk must be the original live actual free-chunk record.
#[no_mangle]
pub unsafe extern "C" fn mem_dump_chunk_addr_bridge(chunk: *mut c_void) -> CULong {
    // SAFETY: Same actual typed-field helper and null behavior.
    unsafe { mem_dump_chunk_addr_result(chunk) }
}

/// Read the same free-chunk size without changing its accounting.
///
/// # Safety
/// A non-null chunk must retain its original lifetime and snapshot exclusion.
#[no_mangle]
pub unsafe extern "C" fn mem_dump_chunk_size_bridge(chunk: *mut c_void) -> CULong {
    // SAFETY: Same actual typed-field helper, no allocation or Page reference.
    unsafe { mem_dump_chunk_size_result(chunk) }
}

#[repr(C)]
struct MemDumpCompleteDebugMetadata {
    record: *mut u8,
    flags_byte: usize,
}

unsafe extern "C" {
    fn ihk_mc_get_dump_level() -> u32;
    static mem_dump_complete_debug_metadata: MemDumpCompleteDebugMetadata;
}

/// Preserve the original dump bitmap-boundary diagnostic and argument widths.
///
/// # Safety
/// The caller retains the original logging/provider context. No bitmap or Page
/// pointer is dereferenced or retained by this value-only diagnostic callback.
#[no_mangle]
pub unsafe extern "C" fn mem_dump_warn_bridge(
    kind: CInt,
    map_count: CULong,
    map_index: CULong,
    map_start: CULong,
    map_end: CULong,
    page_index: CULong,
) {
    // SAFETY: Static NUL-terminated strings and exact original vararg types.
    // The genuine C callback narrows map_count to int; other words stay ulong,
    // including the original %ld representation of the unsigned map index.
    unsafe {
        if kind == 0 {
            kprintf(
                b"%s:free page is out of range(max:%d): %ld (map_start:0x%lx, map_end:0x%lx) k(0x%lx)\n\0".as_ptr().cast::<i8>(),
                b"ihk_mc_query_mem_free_page\0".as_ptr().cast::<i8>(),
                map_count as CInt,
                map_index,
                map_start,
                map_end,
                page_index,
            );
        } else {
            kprintf(
                b"%s:user page is out of range(max:%d): %ld (map_start:0x%lx, map_end:0x%lx) j(0x%lx)\n\0".as_ptr().cast::<i8>(),
                b"ihk_mc_get_mem_user_page\0".as_ptr().cast::<i8>(),
                map_count as CInt,
                map_index,
                map_start,
                map_end,
                page_index,
            );
        }
    }
}

/// Return the original unsigned provider level through its C int callback ABI.
///
/// # Safety
/// The existing dump-level provider and publication context must remain valid.
#[no_mangle]
pub unsafe extern "C" fn mem_dump_level_bridge() -> CInt {
    // SAFETY: Genuine ihk/mm.h declares unsigned int; this retains the original
    // supported compiler's same-width int conversion, without range clamping.
    unsafe { ihk_mc_get_dump_level() as CInt }
}

/// Emit the original optional dump-completion event after its mutable flag gate.
///
/// # Safety
/// The caller retains the original dynamic-debug record access discipline and
/// logging context. This callback publishes no new completion or ownership ACK.
#[no_mangle]
pub unsafe extern "C" fn mem_dump_complete_log_bridge() {
    // SAFETY: Same mutable C __verbose record with actual-GCC9-bound flags byte.
    // Plain one-byte read preserves the original access policy; no cached copy,
    // atomic strengthening or unconditional log replaces the gate.
    unsafe {
        let metadata = &mem_dump_complete_debug_metadata;
        if core::ptr::read(metadata.record.add(metadata.flags_byte)) != 0 {
            kprintf(
                b"%s: IHK_DUMP_PAGE_SET_COMPLETED\n\0".as_ptr().cast::<i8>(),
                b"ihk_mc_query_mem_areas\0".as_ptr().cast::<i8>(),
            );
        }
    }
}

/// Preserve the three original ordinary boot-configuration messages.
///
/// # Safety
/// The caller retains the existing logging initialization/provider context.
#[no_mangle]
pub unsafe extern "C" fn mem_init_log_bridge(event: CInt) {
    // SAFETY: Exact original static messages. Unknown events have no effects.
    unsafe {
        match event {
            MEM_INIT_LOG_ANON_ON_DEMAND => {
                kprintf(b"Demand paging on ANONYMOUS mappings enabled.\n\0".as_ptr().cast());
            }
            MEM_INIT_LOG_XPMEM_PAGE_IN_REMOTE => {
                kprintf(b"Demand paging on XPMEM remote mappings enabled.\n\0".as_ptr().cast());
            }
            MEM_INIT_LOG_HUGETLBFS_ON_DEMAND => {
                kprintf(b"Demand paging on hugetlbfs mappings enabled.\n\0".as_ptr().cast());
            }
            _ => {}
        }
    }
}

/// Preserve the original distance-allocation failure message and ignored node.
///
/// # Safety
/// The caller retains its original initialization and logging context.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_distances_alloc_fail_log_bridge(_node: CInt) {
    // SAFETY: Same exact static varargs, no node lookup/allocation/retry added.
    unsafe {
        kprintf(
            b"%s: error: allocating nodes_by_distance\n\0".as_ptr().cast::<i8>(),
            b"numa_distances_init\0".as_ptr().cast::<i8>(),
        );
    }
}

/// Diagnose the original invalid heap release without freeing or unlocking.
///
/// # Safety
/// The caller retains the original tracking/IRQ context. `file` must satisfy
/// the existing logging string lifetime contract. No pointer is dereferenced.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_invalid_free_bridge(
    _ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
) {
    // SAFETY: Exact original varargs and genuine void panic ABI. The pointer
    // argument remains ignored; no invented release, IRQ restore or trap follows.
    unsafe {
        kprintf(
            b"%s: ERROR: kfree()ing invalid pointer at %s:%d\n\0".as_ptr().cast::<i8>(),
            b"_kfree\0".as_ptr().cast::<i8>(),
            file,
            line,
        );
        mem_kmalloc_panic(b"panic\0".as_ptr().cast::<i8>());
    }
}

/// Diagnose the original invalid page-batch release using the caller provenance.
///
/// # Safety
/// The original release/tracking context and logging string lifetime must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_invalid_free_bridge(
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
) {
    // SAFETY: Preserve the genuine raw-pointer vararg passed to the old %lx
    // format, exact borrowed file/line and log-before-void-panic sequence.
    unsafe {
        kprintf(
            b"%s: ERROR: invalid deallocation for addr: 0x%lx @ %s:%d\n\0".as_ptr().cast(),
            b"_ihk_mc_free_pages\0".as_ptr().cast::<i8>(),
            ptr,
            file,
            line,
        );
        mem_kmalloc_panic(b"panic: invalid deallocation\0".as_ptr().cast::<i8>());
    }
}

/// Diagnose the original mismatched page count without altering the batch.
///
/// # Safety
/// The original tracking context and caller provenance string must remain valid.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_invalid_size_bridge(
    _ptr: *mut c_void,
    npages: CInt,
    alloc_npages: CInt,
    file: *mut i8,
    line: CInt,
) {
    // SAFETY: Exact original signed counts and string/int varargs, then the
    // same genuine void panic endpoint. No clamp, cleanup or ACK is introduced.
    unsafe {
        kprintf(
            b"%s: ERROR: trying to deallocate %d pages for a %d pages allocation at %s:%d\n\0"
                .as_ptr()
                .cast::<i8>(),
            b"_ihk_mc_free_pages\0".as_ptr().cast::<i8>(),
            npages,
            alloc_npages,
            file,
            line,
        );
        mem_kmalloc_panic(b"invalid deallocation\0".as_ptr().cast::<i8>());
    }
}

#[repr(C)]
struct MemTrackingDebugRecords1 {
    records: [*mut u8; 1],
    flags_byte: usize,
}

#[repr(C)]
struct MemTrackingDebugRecords4 {
    records: [*mut u8; 4],
    flags_byte: usize,
}

#[repr(C)]
struct MemTrackingDebugRecords7 {
    records: [*mut u8; 7],
    flags_byte: usize,
}

unsafe extern "C" {
    static mem_kmalloc_track_log_bridge_debug_metadata: MemTrackingDebugRecords4;
    static mem_pagealloc_track_log_bridge_debug_metadata: MemTrackingDebugRecords7;
    static mem_kmalloc_leak_log_bridge_debug_metadata: MemTrackingDebugRecords1;
    static mem_pagealloc_leak_log_bridge_debug_metadata: MemTrackingDebugRecords1;
}

/// Read the original ordinary flag byte from a live C-owned __verbose record.
///
/// # Safety
/// `record` must name the real valid ddebug object and `flags_byte` its
/// actual-GCC9-bound byte within that object. Original debug-control access
/// discipline applies; this is neither an atomic upgrade nor a copied flag.
unsafe fn mem_tracking_debug_enabled(record: *mut u8, flags_byte: usize) -> bool {
    // SAFETY: The immutable descriptor binds actual object extent and byte27;
    // the pointed record remains mutable C-owned storage throughout the call.
    unsafe { core::ptr::read(record.add(flags_byte)) != 0 }
}

/// Preserve the complete original tracking diagnostic switch and flag gates.
///
/// # Safety
/// The caller retains the original tracking/IRQ context and borrowed file-string
/// lifetime when its event is enabled. Debug-record access discipline is the
/// original one; this callback changes no allocation, list or reference state.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_track_log_bridge(
    event: CInt,
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
    size: CInt,
) {
    // SAFETY: Exact C-derived static formats and original scalar/pointer varargs.
    // Only dynamic cases read their own live mutable __verbose flag byte, and
    // no disabled/unknown event dereferences the incoming file or data pointer.
    unsafe {
        match event {
            KMALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED => {
                kprintf(
                    b"%s: ERROR: allocating tracking entry\n\0".as_ptr().cast::<i8>(),
                    b"_kmalloc\0".as_ptr().cast::<i8>(),
                );
            }
            KMALLOC_TRACK_LOG_FILE_ALLOC_FAILED => {
                kprintf(
                    b"%s: ERROR: allocating file string\n\0".as_ptr().cast::<i8>(),
                    b"_kmalloc\0".as_ptr().cast::<i8>(),
                );
            }
            KMALLOC_TRACK_LOG_ENTRY_ADDED => {
                let metadata = &mem_kmalloc_track_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[0], metadata.flags_byte) {
                    kprintf(
                        b"%s entry %s:%d size: %d added\n\0".as_ptr().cast::<i8>(),
                        b"_kmalloc\0".as_ptr().cast::<i8>(),
                        file,
                        line,
                        size,
                    );
                }
            }
            KMALLOC_TRACK_LOG_ADDR_ALLOC_FAILED => {
                kprintf(
                    b"%s: ERROR: allocating addr entry\n\0".as_ptr().cast::<i8>(),
                    b"_kmalloc\0".as_ptr().cast::<i8>(),
                );
            }
            KMALLOC_TRACK_LOG_ADDR_ADDED => {
                let metadata = &mem_kmalloc_track_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[1], metadata.flags_byte) {
                    kprintf(
                        b"%s addr_entry %p added\n\0".as_ptr().cast::<i8>(),
                        b"_kmalloc\0".as_ptr().cast::<i8>(),
                        ptr,
                    );
                }
            }
            KMALLOC_TRACK_LOG_ADDR_REMOVED => {
                let metadata = &mem_kmalloc_track_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[2], metadata.flags_byte) {
                    kprintf(
                        b"%s addr_entry %p removed\n\0".as_ptr().cast::<i8>(),
                        b"_kfree\0".as_ptr().cast::<i8>(),
                        ptr,
                    );
                }
            }
            KMALLOC_TRACK_LOG_ENTRY_REMOVED => {
                let metadata = &mem_kmalloc_track_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[3], metadata.flags_byte) {
                    kprintf(
                        b"%s entry %s:%d size: %d removed\n\0".as_ptr().cast::<i8>(),
                        b"_kfree\0".as_ptr().cast::<i8>(),
                        file,
                        line,
                        size,
                    );
                }
            }
            _ => {}
        }
    }
}
/// Preserve the complete original tracking diagnostic switch and flag gates.
///
/// # Safety
/// The caller retains the original tracking/IRQ context and borrowed file-string
/// lifetime when its event is enabled. Debug-record access discipline is the
/// original one; this callback changes no allocation, list or reference state.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_track_log_bridge(
    event: CInt,
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
    npages: CInt,
) {
    // SAFETY: Exact C-derived static formats and original scalar/pointer varargs.
    // Only dynamic cases read their own live mutable __verbose flag byte, and
    // no disabled/unknown event dereferences the incoming file or data pointer.
    unsafe {
        match event {
            PAGEALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED => {
                kprintf(
                    b"%s: ERROR: allocating tracking entry\n\0".as_ptr().cast::<i8>(),
                    b"_ihk_mc_alloc_aligned_pages_node\0".as_ptr().cast::<i8>(),
                );
            }
            PAGEALLOC_TRACK_LOG_FILE_ALLOC_FAILED => {
                kprintf(
                    b"%s: ERROR: allocating file string\n\0".as_ptr().cast::<i8>(),
                    b"_ihk_mc_alloc_aligned_pages_node\0".as_ptr().cast::<i8>(),
                );
            }
            PAGEALLOC_TRACK_LOG_ENTRY_ADDED => {
                let metadata = &mem_pagealloc_track_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[0], metadata.flags_byte) {
                    kprintf(
                        b"%s entry %s:%d npages: %d added\n\0".as_ptr().cast::<i8>(),
                        b"_ihk_mc_alloc_aligned_pages_node\0".as_ptr().cast::<i8>(),
                        file,
                        line,
                        npages,
                    );
                }
            }
            PAGEALLOC_TRACK_LOG_ADDR_ALLOC_FAILED => {
                kprintf(
                    b"%s: ERROR: allocating addr entry\n\0".as_ptr().cast::<i8>(),
                    b"_ihk_mc_alloc_aligned_pages_node\0".as_ptr().cast::<i8>(),
                );
            }
            PAGEALLOC_TRACK_LOG_ADDR_ADDED => {
                let metadata = &mem_pagealloc_track_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[1], metadata.flags_byte) {
                    kprintf(
                        b"%s addr_entry %p added\n\0".as_ptr().cast::<i8>(),
                        b"_ihk_mc_alloc_aligned_pages_node\0".as_ptr().cast::<i8>(),
                        ptr,
                    );
                }
            }
            PAGEALLOC_TRACK_LOG_ADDR_REMOVED => {
                let metadata = &mem_pagealloc_track_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[2], metadata.flags_byte) {
                    kprintf(
                        b"%s addr_entry %p removed\n\0".as_ptr().cast::<i8>(),
                        b"_ihk_mc_free_pages\0".as_ptr().cast::<i8>(),
                        ptr,
                    );
                }
            }
            PAGEALLOC_TRACK_LOG_ENTRY_REMOVED => {
                let metadata = &mem_pagealloc_track_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[3], metadata.flags_byte) {
                    kprintf(
                        b"%s entry %s:%d removed\n\0".as_ptr().cast::<i8>(),
                        b"_ihk_mc_free_pages\0".as_ptr().cast::<i8>(),
                        file,
                        line,
                    );
                }
            }
            PAGEALLOC_TRACK_LOG_COVERING_FOUND => {
                let metadata = &mem_pagealloc_track_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[4], metadata.flags_byte) {
                    kprintf(
                        b"%s: found covering addr_entry: 0x%lx:%d\n\0".as_ptr().cast::<i8>(),
                        b"_ihk_mc_free_pages\0".as_ptr().cast::<i8>(),
                        ptr,
                        npages,
                    );
                }
            }
            PAGEALLOC_TRACK_LOG_ADDR_NEXT_ADDED => {
                let metadata = &mem_pagealloc_track_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[5], metadata.flags_byte) {
                    kprintf(
                        b"%s: addr_entry_next: 0x%lx:%d\n\0".as_ptr().cast::<i8>(),
                        b"_ihk_mc_free_pages\0".as_ptr().cast::<i8>(),
                        ptr,
                        npages,
                    );
                }
            }
            PAGEALLOC_TRACK_LOG_ADDR_MODIFIED => {
                let metadata = &mem_pagealloc_track_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[6], metadata.flags_byte) {
                    kprintf(
                        b"%s: modified addr_entry: 0x%lx:%d\n\0".as_ptr().cast::<i8>(),
                        b"_ihk_mc_free_pages\0".as_ptr().cast::<i8>(),
                        ptr,
                        npages,
                    );
                }
            }
            _ => {}
        }
    }
}
/// Preserve the complete original tracking diagnostic switch and flag gates.
///
/// # Safety
/// The caller retains the original tracking/IRQ context and borrowed file-string
/// lifetime when its event is enabled. Debug-record access discipline is the
/// original one; this callback changes no allocation, list or reference state.
#[no_mangle]
pub unsafe extern "C" fn mem_kmalloc_leak_log_bridge(
    event: CInt,
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
    size: CInt,
    count: CInt,
    runcount: CInt,
) {
    // SAFETY: Exact C-derived static formats and original scalar/pointer varargs.
    // Only dynamic cases read their own live mutable __verbose flag byte, and
    // no disabled/unknown event dereferences the incoming file or data pointer.
    unsafe {
        match event {
            MEM_TRACK_LEAK_DETAIL => {
                let metadata = &mem_kmalloc_leak_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[0], metadata.flags_byte) {
                    kprintf(
                        b"%s memory leak: %p @ %s:%d size: %d runcount: %d\n\0".as_ptr().cast::<i8>(),
                        b"kmalloc_memcheck\0".as_ptr().cast::<i8>(),
                        ptr,
                        file,
                        line,
                        size,
                        runcount,
                    );
                }
            }
            MEM_TRACK_LEAK_SUMMARY => {
                kprintf(
                    b"%s memory leak: %s:%d size: %d cnt: %d, runcount: %d\n\0".as_ptr().cast::<i8>(),
                    b"kmalloc_memcheck\0".as_ptr().cast::<i8>(),
                    file,
                    line,
                    size,
                    count,
                    runcount,
                );
            }
            _ => {}
        }
    }
}
/// Preserve the complete original tracking diagnostic switch and flag gates.
///
/// # Safety
/// The caller retains the original tracking/IRQ context and borrowed file-string
/// lifetime when its event is enabled. Debug-record access discipline is the
/// original one; this callback changes no allocation, list or reference state.
#[no_mangle]
pub unsafe extern "C" fn mem_pagealloc_leak_log_bridge(
    event: CInt,
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
    _size: CInt,
    count: CInt,
    runcount: CInt,
) {
    // SAFETY: Exact C-derived static formats and original scalar/pointer varargs.
    // Only dynamic cases read their own live mutable __verbose flag byte, and
    // no disabled/unknown event dereferences the incoming file or data pointer.
    unsafe {
        match event {
            MEM_TRACK_LEAK_DETAIL => {
                let metadata = &mem_pagealloc_leak_log_bridge_debug_metadata;
                if mem_tracking_debug_enabled(metadata.records[0], metadata.flags_byte) {
                    kprintf(
                        b"%s memory leak: %p @ %s:%d runcount: %d\n\0".as_ptr().cast::<i8>(),
                        b"pagealloc_memcheck\0".as_ptr().cast::<i8>(),
                        ptr,
                        file,
                        line,
                        runcount,
                    );
                }
            }
            MEM_TRACK_LEAK_SUMMARY => {
                kprintf(
                    b"%s memory leak: %s:%d cnt: %d, runcount: %d\n\0".as_ptr().cast::<i8>(),
                    b"pagealloc_memcheck\0".as_ptr().cast::<i8>(),
                    file,
                    line,
                    count,
                    runcount,
                );
            }
            _ => {}
        }
    }
}

unsafe extern "C" {
    #[link_name = "lookup_process_memory_range"]
    fn mem_lookup_process_memory_range_provider(
        vm: *mut ProcessVm,
        start: CULong,
        end: CULong,
    ) -> *mut VmRange;

    #[link_name = "ihk_mc_register_interrupt_handler"]
    fn mem_register_interrupt_handler_provider(vector: CInt, handler: *mut c_void) -> CInt;
}

/// Delegate a borrowed VM range lookup without changing range ownership.
///
/// # Safety
/// The caller must retain the same VM lifetime and range-lock discipline required
/// by lookup_process_memory_range. The returned raw range keeps its original
/// borrowed lifetime; this adapter acquires no lock or reference.
#[no_mangle]
pub unsafe extern "C" fn mem_lookup_memory_range_bridge(
    vm: *mut c_void,
    start: CULong,
    end: CULong,
) -> *mut c_void {
    // SAFETY: The original provider receives the same VM and unmodified bounds.
    // No local dereference, null policy, normalization or ownership transfer occurs.
    unsafe { mem_lookup_process_memory_range_provider(vm.cast(), start, end).cast() }
}

/// Register the caller-owned interrupt descriptor through the existing provider.
///
/// # Safety
/// handler must represent the original ihk_mc_interrupt_handler pointer, including
/// its original list state, callback lifetime and registration synchronization.
/// These obligations remain with the caller/provider; no descriptor is copied.
#[no_mangle]
pub unsafe extern "C" fn mem_register_interrupt_handler_bridge(
    vector: CInt,
    handler: CULong,
) -> CInt {
    // SAFETY: Supported x86_64 unsigned-long to pointer conversion preserves the
    // same descriptor bits. The genuine provider retains its exact result/order.
    unsafe { mem_register_interrupt_handler_provider(vector, handler as *mut c_void) }
}

unsafe extern "C" {
    static mem_rusage_init_debug_metadata: MemTrackingDebugRecords1;
}

/// Preserve the NUMA initialization failure diagnostic and genuine void panic.
///
/// # Safety
/// The caller retains its original initialization and logging context. This
/// callback does not release partially initialized nodes or alter IRQ state.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_panic_bridge(node: CInt) {
    // SAFETY: Static strings, exact signed node, log before the existing panic.
    // panic retains its genuine void ABI; no trap or unreachable is invented.
    unsafe {
        kprintf(
            b"%s: error: obtaining NUMA info for node %d\n\0".as_ptr().cast::<i8>(),
            b"numa_init\0".as_ptr().cast::<i8>(),
            node,
        );
        mem_kmalloc_panic(b"\0".as_ptr().cast::<i8>());
    }
}

/// Preserve the original missing CPU-info panic during resource initialization.
///
/// # Safety
/// The original initialization and genuine panic provider context must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_rusage_init_panic_bridge() {
    // SAFETY: Exact original static diagnostic and void panic ABI; no cleanup,
    // synthetic initialization success or new completion publication follows.
    unsafe {
        mem_kmalloc_panic(
            b"rusage_init: PANIC: ihk_mc_get_cpu_info returned NULL\0".as_ptr().cast(),
        );
    }
}

/// Retain the mutable dynamic-debug gate and original total-memory word format.
///
/// # Safety
/// The caller retains the original debug-record access discipline and logging
/// context. The word is diagnostic only and no resource accounting is changed.
#[no_mangle]
pub unsafe extern "C" fn mem_rusage_init_log_bridge(total_memory: CULong) {
    // SAFETY: The descriptor names the actual mutable C record and actual-GCC9
    // flags-byte witness. Plain read and any-nonzero predicate match original C.
    unsafe {
        let metadata = &mem_rusage_init_debug_metadata;
        if mem_tracking_debug_enabled(metadata.records[0], metadata.flags_byte) {
            kprintf(
                b"%s: rusage.total_memory=%ld\n\0".as_ptr().cast::<i8>(),
                b"rusage_init\0".as_ptr().cast::<i8>(),
                total_memory,
            );
        }
    }
}

#[repr(C)]
struct MemNumaDistanceAllocationOrigin {
    file: *const i8,
    line: CInt,
}

unsafe extern "C" {
    static mem_numa_log_rbtree_enabled: CInt;
    static mem_numa_distance_allocation_origin: MemNumaDistanceAllocationOrigin;
}

/// Retain the existing resource-accounting provider and its configuration gate.
///
/// # Safety
/// Caller must retain the original boot/accounting serialization. This wrapper
/// does not make the ordinary resource total update atomic or acquire a lock.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_rusage_total_add_bridge(bytes: CULong) {
    // SAFETY: Reuse the existing Rust provider with the exact unsigned word.
    // Its enable_rusage gate and wrapping arithmetic remain authoritative.
    unsafe { rusage_total_memory_add(bytes) }
}

/// Preserve the complete NUMA initialization diagnostic switch.
///
/// # Safety
/// Original boot logging context must hold. All values remain diagnostic only;
/// no node, range, page or allocation pointer is dereferenced or retained here.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_init_log_bridge(
    event: CInt,
    node: CInt,
    linux_numa_id: CInt,
    node_type: CInt,
    start: CULong,
    end: CULong,
    bytes: CULong,
    pages: CInt,
    rbtree_allocator: CInt,
) {
    // SAFETY: Exact static format bytes and original signed/unsigned varargs.
    // The immutable C configuration datum retains the original preprocessor arm.
    unsafe {
        match event {
            MEM_NUMA_INIT_LOG_CHUNK => {
                kprintf(
                    b"Physical memory: 0x%lx - 0x%lx, %lu bytes, %d pages available @ NUMA: %d\n\0"
                        .as_ptr().cast::<i8>(),
                    start, end, bytes, pages, node,
                );
            }
            MEM_NUMA_INIT_LOG_NODE => {
                if mem_numa_log_rbtree_enabled != 0 && rbtree_allocator != 0 {
                    kprintf(
                        b"NUMA: %d, Linux NUMA: %d, type: %d, available bytes: %lu, pages: %d\n\0"
                            .as_ptr().cast::<i8>(),
                        node, linux_numa_id, node_type, bytes, pages,
                    );
                } else {
                    kprintf(
                        b"NUMA: %d, Linux NUMA: %d, type: %d\n\0".as_ptr().cast::<i8>(),
                        node, linux_numa_id, node_type,
                    );
                }
            }
            _ => {}
        }
    }
}

/// Allocate the original distance array with the tracked caller provenance.
///
/// # Safety
/// The original boot allocator, page-tracking and node-selection context must
/// hold. The caller owns the returned batch exactly as before, including NULL.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_distances_alloc_bridge(
    npages: CInt,
    flag: CULong,
) -> *mut c_void {
    // SAFETY: Immutable C metadata captures the original language's file/line
    // origin at the replaced callsite. No Rust file!/line! or new C shim is used.
    // The same tracked allocator receives all eight arguments once, in order.
    unsafe {
        let origin = &mem_numa_distance_allocation_origin;
        _ihk_mc_alloc_aligned_pages_node(
            npages,
            PAGE_P2ALIGN,
            flag,
            -1,
            IHK_MC_PG_KERNEL,
            CULong::MAX,
            origin.file as *mut i8,
            origin.line,
        )
    }
}

type MemPageFaultHandler = unsafe extern "C" fn(*mut c_void, u64, *mut c_void);

unsafe extern "C" {
    #[link_name = "ihk_mc_set_page_fault_handler"]
    fn mem_set_page_fault_handler_provider(handler: Option<MemPageFaultHandler>);
}

/// Install the same fault-handler address through the existing public provider.
///
/// # Safety
/// The word must satisfy the original supported x86_64 unsigned-long to function
/// pointer conversion contract. A nonzero address must name a live callback with
/// the genuine void(void *, uint64_t, void *) ABI for its entire installed life.
/// The caller retains original initialization and publication synchronization.
#[no_mangle]
pub unsafe extern "C" fn mem_set_page_fault_handler_bridge(handler: CULong) {
    // SAFETY: Supported ABI has equal-sized word and function pointer; nullable
    // function pointers use the zero representation. transmute preserves every
    // incoming bit without dereferencing/invoking the callback, inventing a null
    // rejection, retaining a new reference or adding publication/ACK behavior.
    unsafe {
        let callback = core::mem::transmute::<CULong, Option<MemPageFaultHandler>>(handler);
        mem_set_page_fault_handler_provider(callback);
    }
}

unsafe extern "C" {
    #[link_name = "ihk_mc_get_vector"]
    fn mem_get_vector_provider(vector_type: u32) -> CInt;
    #[link_name = "vm_range_policy_search"]
    fn mem_range_policy_search_provider(
        vm: *mut ProcessVm,
        address: CULong,
    ) -> *mut crate::abi::VmRangeNumaPolicy;
}

/// Forward the original int-to-enum conversion to the public vector provider.
///
/// # Safety
/// The caller must retain the original provider initialization context. The
/// selected C consumer must prove the exact four-byte unsigned enum ABI; an
/// incompatible compiler option is rejected by its genuine-header witness.
#[no_mangle]
pub unsafe extern "C" fn mem_get_vector_bridge(vector_type: CInt) -> CInt {
    // SAFETY: The original explicit C enum cast preserves all int bits in its
    // unsigned underlying type. No validation, default vector or clamp is added.
    unsafe { mem_get_vector_provider(vector_type as u32) }
}

/// Return the original borrowed VM range-policy search result.
///
/// # Safety
/// The VM, policy tree and returned raw policy must retain the caller/provider's
/// original lifetime and lock discipline. No Rust reference extends that life.
#[no_mangle]
pub unsafe extern "C" fn mem_range_policy_search_bridge(
    vm: *mut c_void,
    virt_addr: CULong,
) -> *mut c_void {
    // SAFETY: Genuine syscall.h declares precisely this VM/address/result ABI.
    // The adapter does not dereference, normalize, lock, refcount or copy policy.
    unsafe { mem_range_policy_search_provider(vm.cast(), virt_addr).cast() }
}

unsafe extern "C" {
    #[link_name = "snprintf"]
    fn mem_distance_snprintf(buffer: *mut i8, size: SizeT, format: *const i8, ...) -> CInt;
}

/// Format the original complete NUMA-distance line through the existing formatter.
///
/// # Safety
/// Positive nr_nodes requires that many readable live MemNodeDistance entries.
/// Original C defined-behavior bounds must hold: each snprintf return advances
/// the cursor within the same 1024-byte buffer, and each remaining-size argument
/// must describe writable storage there. Callers must retain the boot logging
/// context. No new truncation, clamp, negative-size or overflow policy is added.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_distances_log_bridge(
    node: CInt,
    distances: *mut MemNodeDistance,
    nr_nodes: CInt,
) {
    let mut buffer = core::mem::MaybeUninit::<[u8; 1024]>::uninit();
    let base = buffer.as_mut_ptr().cast::<i8>();

    // SAFETY: Genuine snprintf initializes its written prefix and NUL terminator;
    // only that initialized string is passed to kprintf. Unwritten stack bytes
    // are not read or silently zeroed. Cursor arithmetic mirrors original C,
    // subject to its same within-buffer precondition rather than a new policy.
    unsafe {
        let prefix = mem_distance_snprintf(
            base,
            1024,
            b"NUMA %d distances: \0".as_ptr().cast(),
            node,
        );
        let mut cursor = base.offset(prefix as isize);
        let mut index: CInt = 0;
        while index < nr_nodes {
            let remaining = 1024_isize.wrapping_sub(cursor.offset_from(base)) as SizeT;
            let distance = distances.add(index as usize);
            let written = mem_distance_snprintf(
                cursor,
                remaining,
                b"%d (%d), \0".as_ptr().cast(),
                (*distance).id,
                (*distance).distance,
            );
            cursor = cursor.offset(written as isize);
            index += 1;
        }
        kprintf(b"%s\n\0".as_ptr().cast::<i8>(), base);
    }
}

#[repr(C)]
struct MemAllocationLogMetadata {
    records: [*mut u8; 7],
    flags_byte: usize,
    profile_add: Option<unsafe extern "C" fn(u32, u64)>,
    profile_event: u32,
    fugaku: CInt,
}

unsafe extern "C" {
    static mem_allocation_log_metadata: MemAllocationLogMetadata;
}

/// Preserve the complete allocation diagnostic and profile-event switch.
///
/// # Safety
/// The caller retains the original allocation/thread profile context and mutable
/// debug-record access discipline. This callback does not change allocation,
/// IRQ, CPU selection, page ownership or the selected profile provider lifetime.
#[no_mangle]
pub unsafe extern "C" fn mem_mckernel_alloc_log_bridge(
    event: CInt,
    current_node: CInt,
    numa_id: CInt,
    npages: CInt,
) {
    // SAFETY: Immutable C metadata captures original feature arms/event ABI and
    // genuine selected provider. Each debug callsite retains its own live record.
    unsafe {
        let metadata = &mem_allocation_log_metadata;
        match event {
            MEM_ALLOC_LOG_EXPLICIT_OK => {
                if mem_tracking_debug_enabled(metadata.records[0], metadata.flags_byte) {
                    kprintf(
                        b"%s: explicit (node: %d) CPU @ node %d allocated %d pages from node %d\n\0".as_ptr().cast::<i8>(),
                        b"mckernel_allocate_aligned_pages_node\0".as_ptr().cast::<i8>(),
                        numa_id,
                        current_node,
                        npages,
                        current_node,
                    );
                }
            }
            MEM_ALLOC_LOG_EXPLICIT_MISS => {
                if let Some(add) = metadata.profile_add {
                    // Original npages * PAGE_SIZE is unsigned-word arithmetic;
                    // profile accounting precedes the optional debug log.
                    add(metadata.profile_event, (npages as CULong).wrapping_mul(PAGE_SIZE) as u64);
                }
                if mem_tracking_debug_enabled(metadata.records[1], metadata.flags_byte) {
                    kprintf(
                        b"%s: couldn't fulfill explicit NUMA request for %d pages\n\0".as_ptr().cast::<i8>(),
                        b"mckernel_allocate_aligned_pages_node\0".as_ptr().cast::<i8>(),
                        npages,
                    );
                }
            }
            MEM_ALLOC_LOG_POLICY_OK => {
                if mem_tracking_debug_enabled(metadata.records[2], metadata.flags_byte) {
                    kprintf(
                        b"%s: policy: CPU @ node %d allocated %d pages from node %d\n\0".as_ptr().cast::<i8>(),
                        b"mckernel_allocate_aligned_pages_node\0".as_ptr().cast::<i8>(),
                        current_node,
                        npages,
                        current_node,
                    );
                }
            }
            MEM_ALLOC_LOG_POLICY_MISS => {
                if let Some(add) = metadata.profile_add {
                    // Original npages * PAGE_SIZE is unsigned-word arithmetic;
                    // profile accounting precedes the optional debug log.
                    add(metadata.profile_event, (npages as CULong).wrapping_mul(PAGE_SIZE) as u64);
                }
                if mem_tracking_debug_enabled(metadata.records[3], metadata.flags_byte) {
                    kprintf(
                        b"%s: couldn't fulfill user policy for %d pages\n\0".as_ptr().cast::<i8>(),
                        b"mckernel_allocate_aligned_pages_node\0".as_ptr().cast::<i8>(),
                        npages,
                    );
                }
            }
            MEM_ALLOC_LOG_DISTANCE_OK => {
                if mem_tracking_debug_enabled(metadata.records[4], metadata.flags_byte) {
                    kprintf(
                        b"%s: distance: CPU @ node %d allocated %d pages from node %d\n\0".as_ptr().cast::<i8>(),
                        b"mckernel_allocate_aligned_pages_node\0".as_ptr().cast::<i8>(),
                        current_node,
                        npages,
                        numa_id,
                    );
                }
            }
            MEM_ALLOC_LOG_DISTANCE_FIRST_MISS => {
                if metadata.fugaku == 0 || mem_tracking_debug_enabled(metadata.records[5], metadata.flags_byte) {
                    kprintf(
                        b"%s: distance: CPU @ node %d failed to allocate %d pages from node %d\n\0".as_ptr().cast::<i8>(),
                        b"mckernel_allocate_aligned_pages_node\0".as_ptr().cast::<i8>(),
                        current_node,
                        npages,
                        numa_id,
                    );
                }
            }
            MEM_ALLOC_LOG_OOM => {
                if mem_tracking_debug_enabled(metadata.records[6], metadata.flags_byte) {
                    kprintf(
                        b"OOM\n\0".as_ptr().cast::<i8>(),
                        b"mckernel_allocate_aligned_pages_node\0".as_ptr().cast::<i8>(),
                    );
                }
            }
            _ => {}
        }
    }
}

#[repr(C)]
struct MemNumaInitializationMetadata {
    nodes: *mut MemNumaNode,
    rbtree_allocator: CInt,
    get_node_info: MemGetNumaNodeInfoFn,
    get_chunk: MemGetMemoryChunkFn,
    init_node: MemNumaNodeInitFn,
    add_free: MemNumaAddFreePagesFn,
    init_allocator: MemPageAllocatorInitFn,
    list_allocator: MemNumaListAllocatorFn,
    count_pages: MemPageallocCountFn,
    add_total: MemRusageTotalAddFn,
    log: MemNumaInitLogFn,
    panic_fn: MemNumaPanicFn,
}

unsafe extern "C" {
    static mem_numa_initialization_metadata: MemNumaInitializationMetadata;
}

/// Run the complete selected NUMA initialization through the existing Rust body.
///
/// # Safety
/// The original single-owner boot context must hold: stable boot topology,
/// exclusive node-array initialization and live allocator/architecture providers.
/// The last-early-heap slot retains its existing volatile access discipline.
#[no_mangle]
pub unsafe extern "C" fn numa_init() {
    // SAFETY: The two topology getters only read distinct stable boot fields.
    // Neither writes, allocates, logs nor changes the early-heap slot, so they
    // commute with the sole effectful argument chain below. Preserve exactly one
    // volatile heap read, its address-conversion/log effect, then the Rust body.
    unsafe {
        let metadata = &mem_numa_initialization_metadata;
        let nr_nodes = ihk_mc_get_nr_numa_nodes();
        let nr_chunks = ihk_mc_get_nr_memory_chunks();
        let heap = crate::x86_memory_helpers::get_last_early_heap();
        let heap_phys = crate::x86_memory_helpers::virt_to_phys(heap);
        let _ = mem_numa_init_body_result(
            metadata.nodes,
            nr_nodes,
            nr_chunks,
            metadata.rbtree_allocator,
            heap_phys,
            Some(metadata.get_node_info),
            Some(metadata.get_chunk),
            Some(metadata.init_node),
            Some(metadata.add_free),
            Some(metadata.init_allocator),
            Some(metadata.list_allocator),
            Some(metadata.count_pages),
            Some(metadata.add_total),
            Some(metadata.log),
            Some(metadata.panic_fn),
        );
    }
}

/// Preserve the original boot callback entry without another initialization.
///
/// # Safety
/// The same exclusive initialization obligations as numa_init must hold.
#[no_mangle]
pub unsafe extern "C" fn mem_numa_init_bridge() {
    // SAFETY: Same synchronous single call and discarded void result.
    unsafe { numa_init() }
}

#[repr(C)]
struct MemNumaSysfsRegistrationMetadata {
    ops: *mut crate::abi::SysfsOps,
    nodes: *mut MemNumaNode,
}

unsafe extern "C" {
    static mem_numa_sysfs_registration_metadata: MemNumaSysfsRegistrationMetadata;
}

/// Register the original per-node sysfs file through the existing Rust provider.
///
/// # Safety
/// The original setup context must hold. The C-owned ops table and node array
/// remain live for every subsequent registered callback, and the boot node count
/// stays within the actual array extent. The stack path is borrowed only for
/// the synchronous create call; the genuine provider formats its own owned copy.
#[no_mangle]
pub unsafe extern "C" fn numa_sysfs_setup() {
    let mut path = core::mem::MaybeUninit::<[i8; crate::abi::PATH_MAX]>::uninit();
    let path_pointer = path.as_mut_ptr().cast::<i8>();
    let mut index: CInt = 0;

    // SAFETY: Each iteration mirrors original formatting/create/error order.
    // Only initialized formatted bytes are read. No raw stack path is retained
    // by the genuine create provider; persistent ops/instance are C-owned globals.
    unsafe {
        let metadata = &mem_numa_sysfs_registration_metadata;
        while index < ihk_mc_get_nr_numa_nodes() {
            mem_distance_snprintf(
                path_pointer,
                crate::abi::PATH_MAX,
                b"/sys/devices/system/node/node%d/meminfo\0".as_ptr().cast(),
                index,
            );
            let error = crate::sysfs::sysfs_createf(
                metadata.ops,
                metadata.nodes.add(index as usize).cast(),
                0o444,
                path_pointer,
            );
            if error != 0 {
                kprintf(
                    b"%s: ERROR: creating %s\n\0".as_ptr().cast::<i8>(),
                    b"numa_sysfs_setup\0".as_ptr().cast::<i8>(),
                    path_pointer,
                );
            }
            index += 1;
        }
    }
}

unsafe extern "C" {
    static mem_fatal_user_bytes_geometry: [CULong; 2];
}

/// Emit the complete original bounded fatal-user-byte diagnostic.
///
/// # Safety
/// Caller must retain the original current-thread/user-copy/fault logging context.
/// For an address admitted by the original range check, name must remain a valid
/// logging string. User mapping access/fault policy remains with copy_from_user;
/// this wrapper never directly dereferences the supplied user address.
#[no_mangle]
pub unsafe extern "C" fn mcexec_v10_dump_user_bytes(name: *const i8, addr: CULong) {
    // SAFETY: Real C compile/header geometry retains the exact original address
    // gate. Rejected values return before usercopy or logging/name access.
    unsafe {
        if addr < mem_fatal_user_bytes_geometry[0] || addr >= mem_fatal_user_bytes_geometry[1] {
            return;
        }
        let mut storage = core::mem::MaybeUninit::<[u8; 16]>::uninit();
        let error = crate::x86_memory_helpers::copy_from_user(
            storage.as_mut_ptr().cast(),
            addr as *const c_void,
            16,
        );
        if error != 0 {
            kprintf(
                b"mcexec_v10: fatal_user_bytes %s=0x%lx copy_failed=%d\n\0"
                    .as_ptr().cast::<i8>(),
                name,
                addr,
                error,
            );
            return;
        }

        // SAFETY: Genuine usercopy returns0 only after all sixteen output bytes
        // are initialized. The failed/partial path above never reads that storage.
        let bytes = storage.assume_init();
        let mut ascii = core::mem::MaybeUninit::<[u8; 17]>::uninit();
        let ascii_pointer = ascii.as_mut_ptr().cast::<u8>();
        let mut index = 0;
        while index < 16 {
            let byte = bytes[index];
            core::ptr::write(
                ascii_pointer.add(index),
                if (0x20..=0x7e).contains(&byte) { byte } else { b'.' },
            );
            index += 1;
        }
        core::ptr::write(ascii_pointer.add(16), 0);

        // SAFETY: All ASCII bytes/NUL are initialized and live synchronously.
        // Original unsigned chars undergo int promotion for every %02x; the
        // same positive CInt arguments preserve values0..255 and exact format.
        kprintf(
            b"mcexec_v10: fatal_user_bytes %s=0x%lx b=%02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x ascii=\"%s\"\n\0"
                .as_ptr().cast::<i8>(),
            name,
            addr,
            bytes[0] as CInt,
            bytes[1] as CInt,
            bytes[2] as CInt,
            bytes[3] as CInt,
            bytes[4] as CInt,
            bytes[5] as CInt,
            bytes[6] as CInt,
            bytes[7] as CInt,
            bytes[8] as CInt,
            bytes[9] as CInt,
            bytes[10] as CInt,
            bytes[11] as CInt,
            bytes[12] as CInt,
            bytes[13] as CInt,
            bytes[14] as CInt,
            bytes[15] as CInt,
            ascii_pointer.cast::<i8>(),
        );
    }
}

/// Consolidate the current CPU lists using the observed original getter order.
///
/// # Safety
/// Each CPU lookup must meet the original current-context/lifetime contract for
/// its returned CpuLocalVar. Distinct returns are preserved: no same-CPU or
/// preemption-disabled assumption is added before the existing remote-list lock.
#[no_mangle]
pub unsafe extern "C" fn kmalloc_consolidate_free_list() {
    // SAFETY: Actual selected GCC9 assembly evaluates lock CPU first, free-list
    // CPU second and remote-list CPU third, then passes those three field
    // addresses to the existing helper. Keep three independent calls; the CPU
    // getter contains real architectural reads and must not be cached or merged.
    unsafe {
        let lock_cpu = get_this_cpu_local_var();
        let free_cpu = get_this_cpu_local_var();
        let remote_cpu = get_this_cpu_local_var();
        let _ = kmalloc_consolidate_free_list_result(
            core::ptr::addr_of_mut!((*remote_cpu).remote_free_list),
            core::ptr::addr_of_mut!((*free_cpu).free_list),
            core::ptr::addr_of_mut!((*lock_cpu).remote_free_list_lock),
            Some(mem_kmalloc_remote_lock_bridge),
            Some(mem_kmalloc_remote_unlock_bridge),
        );
    }
}

#[repr(C)]
struct MemNumaSysfsShowGeometry {
    rbtree: CInt,
    kb_shift: u32,
}

unsafe extern "C" {
    static mem_numa_sysfs_show_geometry: MemNumaSysfsShowGeometry;
}

/// Preserve the complete original per-node meminfo formatting callback.
///
/// # Safety
/// In the RBTREE arm, instance must name the original live NUMA node and buf
/// writable storage for size bytes. Retain the caller's original counter-read
/// synchronization/lifetime discipline. Each snprintf cursor and cumulative int
/// length must stay in the original C defined-behavior domain; no clamp, extra
/// lock, atomic/volatile upgrade or stronger snapshot guarantee is introduced.
#[no_mangle]
pub unsafe extern "C" fn numa_sysfs_show_meminfo(
    _ops: *mut crate::abi::SysfsOps,
    instance: *mut c_void,
    buf: *mut c_void,
    size: SizeT,
) -> crate::abi::SSizeT {
    // SAFETY: Immutable metadata binds the genuine Cconfiguration and shift.
    // The original non-RBTREE arm returns0 without reading node/buffer pointers.
    unsafe {
        let geometry = &mem_numa_sysfs_show_geometry;
        if geometry.rbtree == 0 {
            return 0;
        }
        let node = instance.cast::<MemNumaNode>();
        let buffer = buf.cast::<i8>();
        let mut length: CInt = 0;

        // Each call performs its own original plain counter reads; do not cache
        // a new node snapshot across calls. Original C passes unsigned long
        // counter arithmetic to %d, so retain that raw vararg representation.
        let written = mem_distance_snprintf(
            buffer.offset(length as isize),
            size.wrapping_sub(length as SizeT),
            b"Node %d MemTotal:%15d kB\n\0".as_ptr().cast(),
            (*node).id,
            (*node).nr_pages.wrapping_shl(geometry.kb_shift),
        );
        length = length.wrapping_add(written);
        let written = mem_distance_snprintf(
            buffer.offset(length as isize),
            size.wrapping_sub(length as SizeT),
            b"Node %d MemFree:%16d kB\n\0".as_ptr().cast(),
            (*node).id,
            (*node).nr_free_pages.wrapping_shl(geometry.kb_shift),
        );
        length = length.wrapping_add(written);
        let written = mem_distance_snprintf(
            buffer.offset(length as isize),
            size.wrapping_sub(length as SizeT),
            b"Node %d MemUsed:%16d kB\n\0".as_ptr().cast(),
            (*node).id,
            (*node).nr_pages
                .wrapping_sub((*node).nr_free_pages)
                .wrapping_shl(geometry.kb_shift),
        );
        length = length.wrapping_add(written);
        length as crate::abi::SSizeT
    }
}

#[repr(C)]
struct MemCoredumpWakeupMetadata {
    descheduled: CInt,
    to_be_woken: CInt,
    record: *mut u8,
    flags_byte: usize,
}

unsafe extern "C" {
    static mem_coredump_wakeup_metadata: MemCoredumpWakeupMetadata;
}

/// Preserve the complete original status-CAS and wait-queue wakeup entry.
///
/// # Safety
/// thread must be live and its naturally aligned status/queue storage must retain
/// the original coredump protocol ownership and synchronization for the entire
/// call. No thread reference is acquired here. This port does not strengthen the
/// separate wait-entry initialization, scheduler or coredump-barrier protocol.
#[no_mangle]
pub unsafe extern "C" fn coredump_wakeup(thread: *mut crate::abi::Thread) {
    // SAFETY: Same aligned int word as original __sync_bool_compare_and_swap.
    // SeqCst success AND failure retain the full-barrier CAS access policy;
    // no load/store approximation, retry loop or synthetic success is introduced.
    unsafe {
        let metadata = &mem_coredump_wakeup_metadata;
        let status = &*core::ptr::addr_of_mut!((*thread).coredump_status).cast::<AtomicI32>();
        if status
            .compare_exchange(
                metadata.descheduled,
                metadata.to_be_woken,
                Ordering::SeqCst,
                Ordering::SeqCst,
            )
            .is_ok()
        {
            // Same flag gate precedes the plain tid read; disabled logging does
            // not read tid. Wake the original embedded queue after optional log.
            if mem_tracking_debug_enabled(metadata.record, metadata.flags_byte) {
                kprintf(
                    b"%s: waking up tid %d\n\0".as_ptr().cast::<i8>(),
                    b"coredump_wakeup\0".as_ptr().cast::<i8>(),
                    (*thread).tid,
                );
            }
            crate::waitq::waitq_wakeup(
                core::ptr::addr_of_mut!((*thread).coredump_wq).cast::<crate::waitq::Waitq>(),
            );
        }
    }
}

#[repr(C)]
struct MemCoredumpWaitMetadata {
    running: CInt,
    descheduled: CInt,
    interruptible: CInt,
    records: [*mut u8; 2],
    flags_byte: usize,
}

// The queue publishes this address while schedule suspends the current frame.
// Pin prohibits moving the stack storage until the original finish_wait unlinks
// it. MaybeUninit permits genuine waitq_init_entry to initialize its private type.
struct MemPinnedCoredumpWaitEntry {
    entry: core::mem::MaybeUninit<crate::waitq::WaitqEntry>,
    _pin: PhantomPinned,
}

unsafe extern "C" {
    static mem_coredump_wait_metadata: MemCoredumpWaitMetadata;
    #[link_name = "cpu_disable_interrupt_save"]
    fn mem_coredump_disable_interrupt_save() -> CULong;
    #[link_name = "cpu_restore_interrupt"]
    fn mem_coredump_restore_interrupt(flags: CULong);
    #[link_name = "schedule"]
    fn mem_coredump_schedule();
}

/// Preserve the complete original pinned wait-entry and scheduling transaction.
///
/// # Safety
/// The original live thread/status/embedded-queue and current-thread contexts
/// must hold. schedule must suspend and resume this same live stack frame; the
/// kernel must retain that stack until finish_wait unlinks the local entry.
/// The separate caller's coredump/barrier protocol remains responsible for wake
/// ordering; no new thread reference, initialized-queue ACK or race repair exists.
#[no_mangle]
pub unsafe extern "C" fn coredump_wait(thread: *mut crate::abi::Thread) {
    let mut storage = core::pin::pin!(MemPinnedCoredumpWaitEntry {
        entry: core::mem::MaybeUninit::uninit(),
        _pin: PhantomPinned,
    });

    // SAFETY: Project the field of the pinned stack wrapper without moving it.
    // No typed WaitqEntry read occurs before the genuine initializer writes it.
    unsafe {
        let entry = core::ptr::addr_of_mut!(Pin::as_mut(&mut storage).get_unchecked_mut().entry)
            .cast::<crate::waitq::WaitqEntry>();
        let current = (*get_this_cpu_local_var()).current.cast::<c_void>();
        crate::waitq::waitq_init_entry(entry, current);

        let metadata = &mem_coredump_wait_metadata;
        let status = core::ptr::addr_of_mut!((*thread).coredump_status);
        // Same original single full-barrier CAS, even if it fails. The temporary
        // atomic view ends here, before the original later plain status store.
        let descheduled = (&*status.cast::<AtomicI32>())
            .compare_exchange(
                metadata.running,
                metadata.descheduled,
                Ordering::SeqCst,
                Ordering::SeqCst,
            )
            .is_ok();
        if descheduled {
            let flags = mem_coredump_disable_interrupt_save();
            if mem_tracking_debug_enabled(metadata.records[0], metadata.flags_byte) {
                kprintf(
                    b"%s: sleeping,tid=%d\n\0".as_ptr().cast::<i8>(),
                    b"coredump_wait\0".as_ptr().cast::<i8>(),
                    (*thread).tid,
                );
            }
            let queue = core::ptr::addr_of_mut!((*thread).coredump_wq)
                .cast::<crate::waitq::Waitq>();
            crate::waitq::waitq_init(queue);
            crate::waitq::waitq_prepare_to_wait(queue, entry, metadata.interruptible);
            mem_coredump_restore_interrupt(flags);
            mem_coredump_schedule();

            // SAFETY: Stack storage remains pinned and live across schedule.
            // Finish unlinks the exact same entry before its frame is released.
            crate::waitq::waitq_finish_wait(queue, entry);
            core::ptr::write(status, metadata.running);
            if mem_tracking_debug_enabled(metadata.records[1], metadata.flags_byte) {
                kprintf(
                    b"%s: woken up,tid=%d\n\0".as_ptr().cast::<i8>(),
                    b"coredump_wait\0".as_ptr().cast::<i8>(),
                    (*thread).tid,
                );
            }
        }
    }
}

// C retains the existing private allocator slot; immutable address/geometry
// metadata below is the exact held source ABI, not a new runtime C provider.
unsafe extern "C" {
    static mem_vmap_allocator_slot: *mut *mut c_void;
    static mem_vmap_init_start: CULong;
    static mem_vmap_init_size: CULong;
    static mem_vmap_init_unit: CULong;
    static mem_vmap_init_first_level: CInt;
}

/// Return the same borrowed allocator pointer with its original plain access.
///
/// # Safety
/// The caller must retain the original slot publication and allocator lifetime
/// discipline. No reference or new ownership is acquired, including for NULL.
#[no_mangle]
pub unsafe extern "C" fn mem_vmap_allocator_bridge() -> *mut c_void {
    unsafe { core::ptr::read(mem_vmap_allocator_slot) }
}

/// Initialize and publish the allocator before preparing first-level mappings.
///
/// # Safety
/// Original exclusive boot slot ownership, mapped geometry and page-table
/// initialization context must hold. Existing provider callbacks are synchronous
/// and retain their original lifetime; ignored helper status remains ignored.
#[no_mangle]
pub unsafe extern "C" fn virtual_allocator_init() {
    unsafe {
        let _ = mem_virtual_allocator_init_body_result(
            mem_vmap_allocator_slot,
            mem_vmap_init_start,
            mem_vmap_init_size,
            mem_vmap_init_unit,
            mem_vmap_init_first_level,
            Some(mem_vmap_init_bridge),
            Some(mem_pt_prepare_map_bridge),
        );
    }
}

#[repr(C)]
struct MemPageFaultEntryMetadata {
    log_count: *mut CInt,
    log_pid: *mut CInt,
    page_size: CULong,
    kernel_start: CULong,
    pf_user: u64,
    invalid: CInt,
    canceled: CInt,
    range_error: CInt,
    busy: CInt,
    sigsegv: CInt,
    sigbus: CInt,
    sigstop: CInt,
    map_error: CInt,
    access_error: CInt,
    bus_address_error: CInt,
    time_u2k: u32,
    time_k2kin: u32,
    time_k2u: u32,
    time_k2kout: u32,
    tofu: CInt,
    fugaku_debug: CInt,
    tofu_attr: CULong,
    records: [*mut u8; 4],
    flags_byte: usize,
    unhandled: unsafe extern "C" fn(*mut crate::abi::Thread, *mut c_void, u64, *mut c_void),
    linux_resolve: Option<unsafe extern "C" fn(
        *mut c_void, *const c_void, *mut CULong, *mut CULong,
    ) -> CInt>,
    linux_pgt: Option<unsafe extern "C" fn() -> *mut c_void>,
    clear_kernel_range: Option<unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt>,
    do_kill: Option<unsafe extern "C" fn(
        *mut crate::abi::Thread, CInt, CInt, CInt, *mut crate::abi::SigInfo, CInt,
    ) -> CULong>,
    profile_add: Option<unsafe extern "C" fn(u32, u64)>,
    profile_event: u32,
}

unsafe extern "C" {
    static mem_page_fault_entry_metadata: MemPageFaultEntryMetadata;
    #[link_name = "interrupt_from_user"]
    fn mem_pf_interrupt_from_user(regs: *mut c_void) -> CInt;
    #[link_name = "set_cputime"]
    fn mem_pf_set_cputime(mode: u32);
    #[link_name = "ihk_mc_get_processor_id"]
    fn mem_pf_processor_id() -> CInt;
    #[link_name = "preempt_disable"]
    fn mem_pf_preempt_disable();
    #[link_name = "preempt_enable"]
    fn mem_pf_preempt_enable();
    #[link_name = "cpu_disable_interrupt"]
    fn mem_pf_disable_interrupt();
    #[link_name = "cpu_enable_interrupt"]
    fn mem_pf_enable_interrupt();
    #[link_name = "terminate"]
    fn mem_pf_terminate(status: CInt, signal: CInt);
    #[link_name = "set_signal"]
    fn mem_pf_set_signal(signal: CInt, regs: *mut c_void, info: *mut crate::abi::SigInfo);
    #[link_name = "check_need_resched"]
    fn mem_pf_check_need_resched();
    #[link_name = "check_signal"]
    fn mem_pf_check_signal(rc: CULong, regs: *mut c_void, number: CInt);
}

/// Execute the complete original page-fault entry through existing providers.
///
/// # Safety
/// Retain the original fault CPU/frame/current-thread/VM/signal lifetime context.
/// Raw thread/frame pointers must remain valid whenever the original providers
/// return here; providers that terminate or transfer control must obey their
/// actual existing ABI. No new reference keeps a thread/VM/frame alive. Original
/// diagnostic-state read discipline, nested-fault panic semantics and privileged
/// IRQ/preemption context remain required; this port adds no recovery or ACK.
#[no_mangle]
pub unsafe extern "C" fn page_fault_handler(
    fault_addr: *mut c_void,
    reason: u64,
    regs: *mut c_void,
) {
    // SAFETY: Typed raw fields preserve the original conditional accesses and
    // synchronous callback lifetimes. Avoid Rust borrows across scheduling,
    // signal/termination or VM providers; all user reads use existing usercopy.
    unsafe {
        let metadata = &mem_page_fault_entry_metadata;
        let thread = (*get_this_cpu_local_var()).current;
        let pid = if !thread.is_null() && !(*thread).proc.is_null() {
            (*(*thread).proc).pid
        } else {
            -1
        };
        let mut start_tsc: u64 = 0;
        if metadata.profile_add.is_some() && !thread.is_null() && (*thread).profile != 0 {
            start_tsc = rdtsc() as u64;
        }
        mem_pf_set_cputime(if mem_pf_interrupt_from_user(regs) != 0 {
            metadata.time_u2k
        } else {
            metadata.time_k2kin
        });
        if mem_tracking_debug_enabled(metadata.records[0], metadata.flags_byte) {
            kprintf(
                b"%s: addr: %p, reason: %lx, regs: %p\n\0".as_ptr().cast::<i8>(),
                b"page_fault_handler\0".as_ptr().cast::<i8>(),
                fault_addr,
                reason,
                regs,
            );
        }
        if pid != core::ptr::read(metadata.log_pid) {
            core::ptr::write(metadata.log_pid, pid);
            core::ptr::write(metadata.log_count, 0);
        }
        if reason & metadata.pf_user != 0 && core::ptr::read(metadata.log_count) < 128 {
            let context = regs.cast::<crate::abi::X86UserContext>();
            kprintf(
                b"mcexec_v10: page_fault cpu=%d pid=%d tid=%d addr=0x%lx reason=0x%lx rip=0x%lx sp=0x%lx error=0x%lx\n\0".as_ptr().cast::<i8>(),
                mem_pf_processor_id(),
                pid,
                if thread.is_null() { -1 } else { (*thread).tid },
                fault_addr as CULong,
                reason,
                if context.is_null() { 0 } else { (*context).gpr.rip },
                if context.is_null() { 0 } else { (*context).gpr.rsp },
                if context.is_null() { 0 } else { (*context).gpr.orig_rax },
            );
            let count = core::ptr::read(metadata.log_count);
            core::ptr::write(metadata.log_count, count.wrapping_add(1));
        }

        mem_pf_preempt_disable();
        // Preserve separate CPU lookups at each original sequenced statement.
        let nesting_cpu = get_this_cpu_local_var();
        let nesting = core::ptr::addr_of_mut!((*nesting_cpu).in_page_fault);
        core::ptr::write(nesting, core::ptr::read(nesting).wrapping_add(1));
        if (*get_this_cpu_local_var()).in_page_fault > 1 {
            kprintf(
                b"%s: PF in PF??\n\0".as_ptr().cast::<i8>(),
                b"page_fault_handler\0".as_ptr().cast::<i8>(),
            );
            mem_pf_disable_interrupt();
            if reason & metadata.pf_user == 0 {
                (*get_this_cpu_local_var()).kernel_mode_pf_regs = regs;
                mem_kmalloc_panic(b"panic: kernel mode PF in PF\0".as_ptr().cast());
            }
            loop {
                mem_kmalloc_panic(b"PANIC\0".as_ptr().cast());
            }
        }
        mem_pf_enable_interrupt();

        let address = fault_addr as CULong;
        let mut linux_mapping_ready = false;
        if metadata.tofu != 0
            && reason & metadata.pf_user == 0
            && address > 0xffff_0000_0000_0000
            && address < 0xffff_8000_0000_0000
        {
            // SAFETY: Cmetadata binds Some(actual provider) iff ENABLE_TOFU.
            // No invented missing-provider error/ACK replaces the original ABI.
            let resolve = metadata.linux_resolve.unwrap_unchecked();
            let mut phys = core::mem::MaybeUninit::<CULong>::uninit();
            let mut size = core::mem::MaybeUninit::<CULong>::uninit();
            let resolve_error = resolve(
                (metadata.linux_pgt.unwrap_unchecked())(), fault_addr, phys.as_mut_ptr(), size.as_mut_ptr(),
            );
            if resolve_error < 0 {
                kprintf(
                    b"%s: failed to resolve 0x%lx from Linux PT..\n\0".as_ptr().cast::<i8>(),
                    b"page_fault_handler\0".as_ptr().cast::<i8>(),
                    address,
                );
            } else {
                // Original successful provider initializes phys; size remains
                // ignored just as in C. Failure never reads either output.
                let phys = phys.assume_init();
                loop {
                    let mapping_error = crate::x86_memory_helpers::ihk_mc_pt_set_page(
                        core::ptr::null_mut(), fault_addr, phys, metadata.tofu_attr,
                    );
                    if mapping_error < 0 {
                        if mapping_error == metadata.busy {
                            kprintf(
                                b"%s: WARNING: updating 0x%lx -> 0x%lx to reflect Linux kernel mapping..\n\0".as_ptr().cast::<i8>(),
                                b"page_fault_handler\0".as_ptr().cast::<i8>(),
                                address,
                                phys,
                            );
                            let _ = (metadata.clear_kernel_range.unwrap_unchecked())(
                                fault_addr,
                                fault_addr.cast::<u8>()
                                    .wrapping_add(metadata.page_size as usize).cast(),
                            );
                            continue;
                        }
                        kprintf(
                            b"%s: failed to set up 0x%lx -> 0x%lx Linux kernel mapping..\n\0".as_ptr().cast::<i8>(),
                            b"page_fault_handler\0".as_ptr().cast::<i8>(),
                            address,
                            phys,
                        );
                        break;
                    }
                    if mem_tracking_debug_enabled(metadata.records[1], metadata.flags_byte) {
                        kprintf(
                            b"%s: Linux kernel mapping 0x%lx -> 0x%lx set\n\0".as_ptr().cast::<i8>(),
                            b"page_fault_handler\0".as_ptr().cast::<i8>(),
                            address,
                            phys,
                        );
                    }
                    linux_mapping_ready = true;
                    break;
                }
            }
        }

        let mut error = 0;
        if !linux_mapping_ready {
            error = if address < metadata.page_size || thread.is_null() {
                metadata.invalid
            } else {
                page_fault_process_vm((*thread).vm.cast(), fault_addr, reason as CULong)
            };
        }
        if error != 0 {
            if error == metadata.canceled {
                if mem_tracking_debug_enabled(metadata.records[2], metadata.flags_byte) {
                    kprintf(
                        b"process is exiting, terminate.\n\0".as_ptr().cast::<i8>(),
                    );
                }
                mem_pf_preempt_enable();
                // Genuine Cterminate ABI is void. Preserve original continuation
                // if a controlled provider returns, rather than inventing !/trap.
                mem_pf_terminate(0, metadata.sigsegv);
            }
            kprintf(
                b"%s fault VM failed for TID: %d, addr: 0x%lx, reason: %d, error: %d\n\0".as_ptr().cast::<i8>(),
                b"page_fault_handler\0".as_ptr().cast::<i8>(),
                if thread.is_null() { -1 } else { (*thread).tid },
                fault_addr,
                reason,
                error,
            );
            if reason & metadata.pf_user != 0 {
                let context = regs.cast::<crate::abi::X86UserContext>();
                kprintf(
                    b"mcexec_v10: fatal_page_fault cpu=%d pid=%d tid=%d addr=0x%lx reason=0x%lx fault_error=%d rip=0x%lx sp=0x%lx rax=0x%lx rdi=0x%lx rsi=0x%lx rdx=0x%lx r10=0x%lx\n\0".as_ptr().cast::<i8>(),
                    mem_pf_processor_id(),
                    pid,
                    if thread.is_null() { -1 } else { (*thread).tid },
                    fault_addr as CULong,
                    reason,
                    error,
                    if context.is_null() { 0 } else { (*context).gpr.rip },
                    if context.is_null() { 0 } else { (*context).gpr.rsp },
                    if context.is_null() { 0 } else { (*context).gpr.rax },
                    if context.is_null() { 0 } else { (*context).gpr.rdi },
                    if context.is_null() { 0 } else { (*context).gpr.rsi },
                    if context.is_null() { 0 } else { (*context).gpr.rdx },
                    if context.is_null() { 0 } else { (*context).gpr.r10 },
                );
                if !context.is_null() {
                    kprintf(
                        b"mcexec_v10: fatal_regs2 cpu=%d pid=%d tid=%d rbx=0x%lx rcx=0x%lx r8=0x%lx r9=0x%lx r11=0x%lx r12=0x%lx r13=0x%lx r14=0x%lx r15=0x%lx\n\0".as_ptr().cast::<i8>(),
                        mem_pf_processor_id(),
                        pid,
                        if thread.is_null() { -1 } else { (*thread).tid },
                        (*context).gpr.rbx,
                        (*context).gpr.rcx,
                        (*context).gpr.r8,
                        (*context).gpr.r9,
                        (*context).gpr.r11,
                        (*context).gpr.r12,
                        (*context).gpr.r13,
                        (*context).gpr.r14,
                        (*context).gpr.r15,
                    );
                    mcexec_v10_dump_user_bytes(b"rsi\0".as_ptr().cast(), (*context).gpr.rsi);
                    mcexec_v10_dump_user_bytes(b"rdx\0".as_ptr().cast(), (*context).gpr.rdx);
                    mcexec_v10_dump_user_bytes(b"r10\0".as_ptr().cast(), (*context).gpr.r10);
                    mcexec_v10_dump_user_bytes(b"r11\0".as_ptr().cast(), (*context).gpr.r11);
                }
                if !context.is_null()
                    && (*context).gpr.rsp >= metadata.page_size
                    && (*context).gpr.rsp < metadata.kernel_start
                {
                    let mut words = core::mem::MaybeUninit::<[CULong; 8]>::uninit();
                    let stack_error = crate::x86_memory_helpers::copy_from_user(
                        words.as_mut_ptr().cast(),
                        (*context).gpr.rsp as *const c_void,
                        core::mem::size_of::<[CULong; 8]>(),
                    );
                    if stack_error == 0 {
                        // Complete usercopy success initializes all eight words.
                        let words = words.assume_init();
                        kprintf(
                            b"mcexec_v10: fatal_stack sp=0x%lx q0=0x%lx q1=0x%lx q2=0x%lx q3=0x%lx q4=0x%lx q5=0x%lx q6=0x%lx q7=0x%lx\n\0".as_ptr().cast::<i8>(),
                            (*context).gpr.rsp,
                            words[0],
                            words[1],
                            words[2],
                            words[3],
                            words[4],
                            words[5],
                            words[6],
                            words[7],
                        );
                        let labels: [&[u8]; 8] = [
                            b"q0\0", b"q1\0", b"q2\0", b"q3\0",
                            b"q4\0", b"q5\0", b"q6\0", b"q7\0",
                        ];
                        let mut index = 0;
                        while index < 8 {
                            mcexec_v10_dump_user_bytes(labels[index].as_ptr().cast(), words[index]);
                            index += 1;
                        }
                    } else {
                        kprintf(
                            b"mcexec_v10: fatal_stack sp=0x%lx copy_failed=%d\n\0".as_ptr().cast::<i8>(),
                            (*context).gpr.rsp,
                            stack_error,
                        );
                    }
                }
            }
            (metadata.unhandled)(thread, fault_addr, reason, regs);
            let cpu = get_this_cpu_local_var();
            let nesting = core::ptr::addr_of_mut!((*cpu).in_page_fault);
            core::ptr::write(nesting, core::ptr::read(nesting).wrapping_sub(1));
            mem_pf_preempt_enable();

            if metadata.fugaku_debug != 0 {
                kprintf(
                    b"%s: sending SIGSTOP to TID: %d\n\0".as_ptr().cast::<i8>(),
                    b"page_fault_handler\0".as_ptr().cast::<i8>(),
                    (*thread).tid,
                );
                let _ = (metadata.do_kill.unwrap_unchecked())(
                    thread, (*(*thread).proc).pid, (*thread).tid,
                    metadata.sigstop, core::ptr::null_mut(), 0,
                );
            } else {
                // SAFETY: Genuine SigInfo is integer/raw-pointer Cdata; all-zero
                // initialization matches original memset, including unused union.
                let mut info = core::mem::MaybeUninit::<crate::abi::SigInfo>::zeroed()
                    .assume_init();
                if error == metadata.range_error {
                    info.si_signo = metadata.sigbus;
                    info.si_code = metadata.bus_address_error;
                    info.sifields.sigfault = core::mem::ManuallyDrop::new(
                        crate::abi::SigInfoFault { si_addr: fault_addr },
                    );
                    mem_pf_set_signal(metadata.sigbus, regs, &mut info);
                } else {
                    info.si_signo = metadata.sigsegv;
                    info.si_code = metadata.map_error;
                    let mut range = core::ptr::null_mut();
                    if !thread.is_null() {
                        range = mem_lookup_process_memory_range_provider(
                            (*thread).vm, address, address.wrapping_add(1),
                        );
                    }
                    if !range.is_null() {
                        info.si_code = metadata.access_error;
                    }
                    info.sifields.sigfault = core::mem::ManuallyDrop::new(
                        crate::abi::SigInfoFault { si_addr: fault_addr },
                    );
                    mem_pf_set_signal(metadata.sigsegv, regs, &mut info);
                }
            }
        } else {
            // Includes original out_ok after a successful TOFU mapping.
            let cpu = get_this_cpu_local_var();
            let nesting = core::ptr::addr_of_mut!((*cpu).in_page_fault);
            core::ptr::write(nesting, core::ptr::read(nesting).wrapping_sub(1));
            mem_pf_preempt_enable();
        }
        if mem_tracking_debug_enabled(metadata.records[3], metadata.flags_byte) {
            kprintf(
                b"%s: addr: %p, reason: %lx, regs: %p -> error: %d\n\0".as_ptr().cast::<i8>(),
                b"page_fault_handler\0".as_ptr().cast::<i8>(),
                fault_addr,
                reason,
                regs,
                error,
            );
        }
        if mem_pf_interrupt_from_user(regs) != 0 {
            mem_pf_enable_interrupt();
            mem_pf_check_need_resched();
            mem_pf_check_signal(0, regs, -1);
        }
        // Original calls interrupt_from_user again here, do not cache its result.
        mem_pf_set_cputime(if mem_pf_interrupt_from_user(regs) != 0 {
            metadata.time_k2u
        } else {
            metadata.time_k2kout
        });
        if let Some(add) = metadata.profile_add {
            if !thread.is_null() && (*thread).profile != 0 {
                add(metadata.profile_event, (rdtsc() as u64).wrapping_sub(start_tsc));
            }
        }
    }
}

#[repr(C)]
struct MemUnhandledFaultMetadata {
    pf_prot: u64,
    pf_write: u64,
    pf_user: u64,
    pf_reserved: u64,
    pf_instruction: u64,
    mf_regular_file: u32,
    fugaku: CInt,
    debug_stack: CInt,
    instruction_address: Option<unsafe extern "C" fn(*const c_void) -> CULong>,
    stack_address: Option<unsafe extern "C" fn(*const c_void) -> CULong>,
}

unsafe extern "C" {
    static mem_unhandled_fault_metadata: MemUnhandledFaultMetadata;
    #[link_name = "kprintf_lock"]
    fn mem_unhandled_kprintf_lock() -> CULong;
    #[link_name = "kprintf_unlock"]
    fn mem_unhandled_kprintf_unlock(flags: CULong);
    #[link_name = "__kprintf"]
    fn mem_unhandled_locked_printf(format: *const i8, ...) -> CInt;
    #[link_name = "ihk_mc_debug_show_interrupt_context"]
    fn mem_unhandled_show_context(regs: *const c_void);
}

/// Emit the complete original locked unhandled-fault diagnostic and panic path.
///
/// # Safety
/// The original non-null live thread/VM/range/memobj and frame access discipline
/// must hold for borrowed raw fields. This port does not acquire VM references
/// or repair the original NULL-thread error route. Lock/IRQ and context/panic
/// providers retain original ABI; optional raw stack reads require original
/// readable stack storage. No reference survives a callback or panic boundary.
#[no_mangle]
pub unsafe extern "C" fn unhandled_page_fault(
    thread: *mut crate::abi::Thread,
    fault_addr: *mut c_void,
    reason: u64,
    regs: *mut c_void,
) {
    // SAFETY: Retain the exact logger lock span and borrowed pointer operations.
    // Unlocked kprintf is used only at original sites after lock release.
    unsafe {
        let metadata = &mem_unhandled_fault_metadata;
        let address = fault_addr as CULong;
        let vm = (*thread).vm;
        let flags = mem_unhandled_kprintf_lock();
        mem_unhandled_locked_printf(
            b"Page fault for 0x%lx\n\0".as_ptr().cast::<i8>(),
            address,
        );
        mem_unhandled_locked_printf(
            b"%s for %s access in %s mode (reserved bit %s set), it %s an instruction fetch\n\0".as_ptr().cast::<i8>(),
            if reason & metadata.pf_prot != 0 { b"protection fault\0".as_ptr().cast::<i8>() } else { b"no page found\0".as_ptr().cast::<i8>() },
            if reason & metadata.pf_write != 0 { b"write\0".as_ptr().cast::<i8>() } else { b"read\0".as_ptr().cast::<i8>() },
            if reason & metadata.pf_user != 0 { b"user\0".as_ptr().cast::<i8>() } else { b"kernel\0".as_ptr().cast::<i8>() },
            if reason & metadata.pf_reserved != 0 { b"was\0".as_ptr().cast::<i8>() } else { b"wasn't\0".as_ptr().cast::<i8>() },
            if reason & metadata.pf_instruction != 0 { b"was\0".as_ptr().cast::<i8>() } else { b"wasn't\0".as_ptr().cast::<i8>() },
        );
        let range = mem_lookup_process_memory_range_provider(vm, address, address.wrapping_add(1));
        if !range.is_null() {
            mem_unhandled_locked_printf(
                b"address is in range, flag: 0x%lx (%s)\n\0".as_ptr().cast::<i8>(),
                (*range).flag,
                if !(*range).memobj.is_null() { (*(*range).memobj.cast::<Memobj>()).path } else { b"\0".as_ptr() as *mut i8 },
            );
            let _ = crate::x86_memory_helpers::ihk_mc_pt_print_pte(
                (*(*vm).address_space).page_table,
                address as *mut c_void,
            );
        } else {
            mem_unhandled_locked_printf(
                b"address is out of range!\n\0".as_ptr().cast::<i8>(),
            );
        }

        if metadata.fugaku != 0 {
            // SAFETY: Cmetadata binds this actual provider only in the original
            // enabled feature arm. There is no inactive-feature direct import.
            let pc = (metadata.instruction_address.unwrap_unchecked())(regs);
            let range = mem_lookup_process_memory_range_provider(vm, pc, pc.wrapping_add(1));
            if !range.is_null() {
                let offset = if !(*range).memobj.is_null()
                    && (*(*range).memobj.cast::<Memobj>()).flags & metadata.mf_regular_file != 0
                {
                    pc.wrapping_sub((*range).start).wrapping_add((*range).objoff as CULong)
                } else {
                    pc.wrapping_sub((*range).start)
                };
                let path = if !(*range).memobj.is_null()
                    && !(*(*range).memobj.cast::<Memobj>()).path.is_null()
                {
                    (*(*range).memobj.cast::<Memobj>()).path
                } else {
                    b"(unknown)\0".as_ptr() as *mut i8
                };
                mem_unhandled_locked_printf(
                    b"PC: 0x%lx (%lx in %s)\n\0".as_ptr().cast::<i8>(),
                    pc,
                    offset,
                    path,
                );
            }
        }
        mem_unhandled_kprintf_unlock(flags);
        mem_unhandled_show_context(regs);

        if reason & metadata.pf_user == 0 {
            (*get_this_cpu_local_var()).kernel_mode_pf_regs = regs;
            if metadata.fugaku == 0 {
                // Original genuine void panic ABI; do not invent !/unreachable
                // or a return when a controlled panic provider returns.
                mem_kmalloc_panic(b"panic: kernel mode PF\0".as_ptr().cast());
            } else {
                kprintf(
                    b"panic: kernel mode PF\0".as_ptr().cast::<i8>(),
                );
                loop {
                    cpu_pause();
                }
            }
        }

        if metadata.debug_stack != 0 {
            // SAFETY: Same original optional direct four-word stack read. No
            // usercopy/null/range policy is silently substituted by this port.
            let stack = (metadata.stack_address.unwrap_unchecked())(regs) as *const u64;
            kprintf(
                b"*rsp:%lx,*rsp+8:%lx,*rsp+16:%lx,*rsp+24:%lx,\n\0".as_ptr().cast::<i8>(),
                *stack.add(0),
                *stack.add(1),
                *stack.add(2),
                *stack.add(3),
            );
        }
    }
}

/// Reuse the exact held VM mapping effect callback implementation.
///
/// # Safety
/// The caller must retain the original page-table/address and mapping ownership
/// context, including CPU affinity for the privileged flush endpoint. No new
/// reference, lock, retry, null policy or hardware fence is introduced here.
#[no_mangle]
pub unsafe extern "C" fn mem_pt_set_page_bridge(
    pt: *mut c_void,
    virt: *mut c_void,
    phys: CULong,
    attr: IhkMcPtAttribute,
) -> CInt {
    unsafe { crate::x86_memory_helpers::ihk_mc_pt_set_page(pt, virt, phys, attr) }
}

/// Reuse the exact held VM mapping effect callback implementation.
///
/// # Safety
/// The caller must retain the original page-table/address and mapping ownership
/// context, including CPU affinity for the privileged flush endpoint. No new
/// reference, lock, retry, null policy or hardware fence is introduced here.
#[no_mangle]
pub unsafe extern "C" fn mem_pt_clear_page_bridge(pt: *mut c_void, virt: *mut c_void) -> CInt {
    unsafe { crate::x86_memory_helpers::ihk_mc_pt_clear_page(pt, virt) }
}

/// Reuse the exact held VM mapping effect callback implementation.
///
/// # Safety
/// The caller must retain the original page-table/address and mapping ownership
/// context, including CPU affinity for the privileged flush endpoint. No new
/// reference, lock, retry, null policy or hardware fence is introduced here.
#[no_mangle]
pub unsafe extern "C" fn mem_flush_tlb_single_bridge(addr: CULong) {
    unsafe { mem_tlb_flush_single_bridge(addr) }
}

/// Reuse the exact held VM mapping effect callback implementation.
///
/// # Safety
/// The caller must retain the original page-table/address and mapping ownership
/// context, including CPU affinity for the privileged flush endpoint. No new
/// reference, lock, retry, null policy or hardware fence is introduced here.
#[no_mangle]
pub unsafe extern "C" fn mem_barrier_bridge() {
    unsafe { crate::x86_cpu_helpers::arch_barrier() }
}


// Existing C geometry is already provided for page_unmap. The same page
// shift/mask/stride and same borrowed arrays are used for this lookup.
unsafe extern "C" {
    static page_unmap_hash_shift: CInt;
    static page_unmap_hash_mask: CULong;
}

/// Look up the original physical-address value through the existing hash.
///
/// # Safety
/// The caller must keep hash storage, bucket locks and returned Page storage live
/// under its original mapping ownership. This function acquires no Page reference.
/// No reference is acquired: the existing synchronous lookup locks its bucket,
/// finds the matching Page, unlocks with the captured flags, and returns the
/// same borrowed pointer (or null). The caller keeps its original lifetime duty.
#[no_mangle]
pub unsafe extern "C" fn phys_to_page(phys: CULong) -> *mut MemPage {
    unsafe {
        crate::page_helpers::phys_to_page_lookup_body_result(
            phys,
            core::ptr::addr_of!(PAGE_INIT_HASH_FIRST) as usize,
            core::ptr::addr_of!(PAGE_INIT_LOCK_FIRST) as usize,
            page_unmap_hash_shift,
            page_unmap_hash_mask,
            page_init_hash_head_stride,
            page_unmap_lock_stride,
            Some(page_count_lock_callback),
            Some(page_count_unlock_callback),
            Some(crate::page_helpers::phys_to_page_lookup_orchestrate_result),
        ).cast::<MemPage>()
    }
}

// Exact IHK_MC_AP_CRITICAL value from existing lib/include/ihk/mm.h.
const PAGE_INSERT_ALLOC_CRITICAL: CInt = 0x000001;

unsafe extern "C" {
    // Existing tracked-allocation callback symbol; usize is the helper's
    // unsigned-long address/size ABI on the supported 64-bit profile.
    #[link_name = "page_hash_alloc_bridge"]
    fn page_insert_alloc_callback(size: usize, flag: CInt) -> *mut crate::page_helpers::Page;
}

/// Same NULL-only insertion failure event; phys was ignored by original C.
///
/// # Safety
/// The synchronous caller must retain the original kernel formatter context.
#[no_mangle]
pub unsafe extern "C" fn phys_to_page_insert_hash_log_bridge(_phys: CULong) {
    unsafe {
        kprintf(
            b"%s: error allocating page\n\0".as_ptr().cast::<i8>(),
            b"phys_to_page_insert_hash\0".as_ptr().cast::<i8>(),
        );
    }
}

/// Preserve the existing bucket ownership and zero initial Page count.
///
/// # Safety
/// The original hash, lock and tracked-allocation providers must remain initialized
/// and live. Caller ownership must retain existing/new Page storage after unlock;
/// this routine neither acquires its reference nor changes the allocator context.
/// Existing pages are returned without allocation/reference changes; a new
/// Page remains count==0 and the caller must retain its original increment.
#[no_mangle]
pub unsafe extern "C" fn phys_to_page_insert_hash(phys: CULong) -> *mut crate::page_helpers::Page {
    unsafe {
        crate::page_helpers::phys_to_page_insert_hash_body_result(
            phys,
            core::ptr::addr_of!(PAGE_INIT_HASH_FIRST) as usize,
            core::ptr::addr_of!(PAGE_INIT_LOCK_FIRST) as usize,
            page_unmap_hash_shift,
            page_unmap_hash_mask,
            page_init_hash_head_stride,
            page_unmap_lock_stride,
            size_of::<crate::page_helpers::Page>(),
            PAGE_INSERT_ALLOC_CRITICAL,
            Some(page_count_lock_callback),
            Some(page_count_unlock_callback),
            Some(page_insert_alloc_callback),
            Some(crate::page_helpers::phys_to_page_insert_hash_orchestrate_result),
            Some(phys_to_page_insert_hash_log_bridge),
        )
    }
}

#[repr(C)]
struct MemTlbHandlerProfileMetadata {
    event: u32,
    add: Option<unsafe extern "C" fn(u32, u64)>,
}

unsafe extern "C" {
    static mem_tlb_handler_profile_metadata: MemTlbHandlerProfileMetadata;
}

/// Run the existing complete TLB handler and preserve its profile accounting.
///
/// # Safety
/// The original interrupt CPU/vector context and initialized shared TLB entry
/// must remain valid for this synchronous handler. Its address array and pending
/// counter retain their original request-owner lifetime until completion. The
/// optional profile metadata names the original provider under PROFILE_ENABLE;
/// each fresh current-thread lookup retains the original live-thread invariant.
/// This entry adds no acknowledgement, scheduling, lock or null policy.
#[no_mangle]
pub unsafe extern "C" fn tlb_flush_handler(vector: CInt) {
    // SAFETY: The immutable metadata has the real C profile gate and provider.
    let profile = unsafe { &mem_tlb_handler_profile_metadata };
    let mut start = 0;
    if profile.add.is_some() {
        // SAFETY: Original interrupt context guarantees the same live CPU-local
        // and current-thread pointers that the C profile branch dereferences.
        let current = unsafe { (*get_this_cpu_local_var()).current };
        if unsafe { (*current).profile } != 0 {
            start = unsafe { rdtsc() };
        }
    }
    // SAFETY: The existing immutable geometry and complete shared entry are
    // unchanged. Actual Rust IRQ/flush/completion providers preserve the old
    // save -> flush(es) -> completion decrement -> IRQ restore sequence.
    unsafe {
        let geometry = core::ptr::read(core::ptr::addr_of!(mem_remote_tlb_geometry));
        let _ = mem_tlb_flush_handler_body_result(
            vector,
            core::ptr::addr_of_mut!(MEM_TLB_FLUSH_VECTOR_FIRST),
            geometry[0],
            geometry[1],
            Some(crate::x86_cpu_helpers::cpu_disable_interrupt_save),
            Some(crate::x86_cpu_helpers::cpu_restore_interrupt),
            Some(mem_tlb_flush_single_bridge),
            Some(mem_tlb_flush_all_bridge),
            Some(mem_tlb_atomic_dec_bridge),
        );
    }
    if let Some(add) = profile.add {
        // SAFETY: Preserve the second current-thread lookup after the complete
        // handler and IRQ restoration; do not reuse the pre-handler pointer.
        let current = unsafe { (*get_this_cpu_local_var()).current };
        if unsafe { (*current).profile } != 0 {
            let end = unsafe { rdtsc() };
            let elapsed = end.wrapping_sub(start);
            unsafe { add(profile.event, elapsed as u64) };
            // SAFETY: Original C performs a third CPU/current lookup after the
            // profile callback. Read/write only that thread's plain elapsed slot
            // under the same interrupt/profile ownership, with unsigned wrap.
            let current = unsafe { (*get_this_cpu_local_var()).current };
            unsafe {
                let slot = core::ptr::addr_of_mut!((*current).profile_elapsed_ts);
                slot.write(slot.read().wrapping_add(elapsed));
            }
        }
    }
}

/// Return the original plain processor-count observation.
///
/// # Safety
/// The existing boot/runtime publication discipline for num_processors must hold;
/// this read neither establishes a snapshot nor changes CPU ownership.
#[no_mangle]
pub unsafe extern "C" fn mem_num_processors_bridge() -> CInt {
    // SAFETY: Reuse the genuine defining ap module's existing CInt slot with the
    // same plain access as original C, without a new atomic/volatile policy.
    unsafe { core::ptr::addr_of!(crate::ap::num_processors).read() }
}

/// Return the current resource set's original borrowed process-hash list base.
///
/// # Safety
/// The caller must retain the original CPU/current resource-set lifetime and
/// synchronization. CPU-local storage and resource_set must be non-null/live as
/// in the C owner. A non-null process_hash remains borrowed after this return;
/// no reference, lock, snapshot or resource-set lifetime extension is acquired.
#[no_mangle]
pub unsafe extern "C" fn mem_process_hash_lists_bridge() -> *mut AbiListHead {
    // SAFETY: Preserve the single current-CPU lookup and ordered raw field reads.
    unsafe {
        let resource_set = (*get_this_cpu_local_var()).resource_set;
        let process_hash = (*resource_set).process_hash;
        if process_hash.is_null() {
            core::ptr::null_mut()
        } else {
            core::ptr::addr_of_mut!((*process_hash).list).cast::<AbiListHead>()
        }
    }
}

/// Return the original current-CPU pending-free list's borrowed address.
///
/// # Safety
/// The caller retains the original CPU affinity, pending-list lock/IRQ ownership
/// and CPU-local storage lifetime. This function takes no list/reference lock and
/// adds no null policy or ownership transfer.
#[no_mangle]
pub unsafe extern "C" fn mem_pending_free_pages_bridge() -> *mut AbiListHead {
    // SAFETY: The live current CPU-local storage owns this initialized list head;
    // form its raw address without creating a Rust reference to shared list data.
    unsafe { core::ptr::addr_of_mut!((*get_this_cpu_local_var()).pending_free_pages) }
}

/// Preserve the complete original kmalloc cache diagnostic event switch.
///
/// # Safety
/// The caller retains the original synchronous kernel formatter/allocator context.
/// ptr is diagnostic bytes only: this callback never dereferences or owns it.
/// Its raw pointer vararg is retained for the original %lx formatter contract.
#[no_mangle]
pub unsafe extern "C" fn kmalloc_cache_log(event: CInt, ptr: *mut c_void) {
    // SAFETY: The original NUL-terminated formats and C-promoted arguments are
    // supplied unchanged to the existing formatter; unknown events have no effect.
    unsafe {
        match event {
            KMALLOC_CACHE_LOG_NO_CACHE => {
                kprintf(
                    b"%s: WARNING: no cache for 0x%lx\n\0".as_ptr().cast::<i8>(),
                    b"kmalloc_cache_free\0".as_ptr().cast::<i8>(),
                    ptr,
                );
            }
            KMALLOC_CACHE_LOG_ALLOC_FAILED => {
                kprintf(
                    b"%s: ERROR: allocating cache element\n\0".as_ptr().cast::<i8>(),
                    b"kmalloc_cache_prealloc\0".as_ptr().cast::<i8>(),
                );
            }
            KMALLOC_CACHE_LOG_PREALLOC => {
                kprintf(
                    b"%s: calling pre-alloc for 0x%lx...\n\0".as_ptr().cast::<i8>(),
                    b"kmalloc_cache_alloc\0".as_ptr().cast::<i8>(),
                    ptr,
                );
            }
            _ => {}
        }
    }
}

/// Emit the exact pending-free warning, including its lack of a final newline.
///
/// # Safety
/// The caller retains the original kernel formatter and pending-free context.
/// No Page field, reference, list or IRQ state is accessed by this diagnostic.
#[no_mangle]
pub unsafe extern "C" fn mem_pending_free_warn_bridge(phys: CULong) {
    // SAFETY: The original %lx receives the same unsigned-long physical value.
    unsafe {
        kprintf(
            b"%s: WARNING: page phys 0x%lx is not PM_NONE\0".as_ptr().cast::<i8>(),
            b"mckernel_free_pages\0".as_ptr().cast::<i8>(),
            phys,
        );
    }
}

/// Preserve the original begin-pending failure's genuine void panic callback.
///
/// # Safety
/// The existing pending-list ownership and caller IRQ context must remain valid.
/// This wrapper does not restore IRQs, unlock, publish completion or return an ACK.
#[no_mangle]
pub unsafe extern "C" fn mem_begin_free_pages_pending_panic_bridge() {
    // SAFETY: Call the actual void panic(const char *) ABI with its original
    // immutable string. Do not invent a Rust never-returning type or recovery.
    unsafe { mem_kmalloc_panic(b"begin_free_pages_pending\0".as_ptr().cast::<i8>()) };
}

/// Preserve the original finish-pending failure and its exact panic message.
///
/// # Safety
/// The caller retains the original pending-list/Page/IRQ ownership on failure;
/// this wrapper adds no rollback, reference release or completion guarantee.
#[no_mangle]
pub unsafe extern "C" fn mem_finish_free_pages_pending_panic_bridge() {
    // SAFETY: The unchanged NUL-terminated bytes target the genuine void provider.
    unsafe { mem_kmalloc_panic(b"free_pending_pages:not PM_PENDING_FREE\0".as_ptr().cast()) };
}

/// Preserve the free-memory query's original panic callback.
///
/// # Safety
/// The original query/formatter context and its failure ownership must hold.
/// Genuine panic behavior remains provider-owned; no lock/IRQ policy is changed.
#[no_mangle]
pub unsafe extern "C" fn mem_query_free_panic_bridge() {
    // SAFETY: Exact original message and void C ABI, without invented termination.
    unsafe { mem_kmalloc_panic(b"PANIC\0".as_ptr().cast::<i8>()) };
}

#[repr(C)]
struct MemSboxAccessMetadata {
    attached: CInt,
    base_slot: *mut *mut c_void,
}

unsafe extern "C" {
    static mem_sbox_access_metadata: MemSboxAccessMetadata;
}

/// Perform the original single 32-bit volatile SBOX store.
///
/// # Safety
/// This endpoint may only be called in the original ATTACHED_MIC profile after
/// its C-owned sbox_base mapping is established. The signed byte offset must
/// select an aligned, accessible 32-bit MMIO register under the original device
/// ownership. No ordinary Rust allocation/reference is manufactured for MMIO.
/// Volatile preserves the original access, not an atomic or completion protocol.
#[no_mangle]
pub unsafe extern "C" fn sbox_write(offset: CInt, value: u32) {
    // SAFETY: The active profile supplies a live, aligned pointer slot. Keep its
    // original plain read; the register operation itself is the volatile store.
    let base = unsafe { mem_sbox_access_metadata.base_slot.read() };
    let register = base.cast::<u8>().wrapping_offset(offset as isize).cast::<u32>();
    // SAFETY: Caller guarantees a valid aligned MMIO register for one u32 store.
    // Signed C int byte arithmetic is retained without bounds/NULL policy changes.
    unsafe { core::ptr::write_volatile(register, value) };
}

/// Perform the original single 32-bit volatile SBOX read.
///
/// # Safety
/// The original ATTACHED_MIC mapping, register alignment/accessibility and device
/// read-side-effect ownership must hold exactly as for sbox_write. This returns
/// the actual volatile register value, with no new barrier, retry or ACK.
#[no_mangle]
pub unsafe extern "C" fn sbox_read(offset: CInt) -> u32 {
    // SAFETY: Same genuine C-owned mapping slot and caller-owned MMIO lifetime.
    let base = unsafe { mem_sbox_access_metadata.base_slot.read() };
    let register = base.cast::<u8>().wrapping_offset(offset as isize).cast::<u32>();
    // SAFETY: Caller guarantees one valid aligned 32-bit MMIO load. No reference
    // aliases ordinary Rust storage and no speculative extra read is introduced.
    unsafe { core::ptr::read_volatile(register) }
}

/// Preserve the original compile-profile-gated mailbox diagnostic write.
///
/// # Safety
/// When ATTACHED_MIC is enabled, retain the original live SBOX mapping/device
/// ownership and offset/value contract. Otherwise the callback is a no-op with
/// no slot read or MMIO access, matching the original empty C feature branch.
#[no_mangle]
pub unsafe extern "C" fn mem_query_free_sbox_write_bridge(offset: CInt, value: u32) {
    // SAFETY: Immutable C metadata encodes the actual original feature, avoiding
    // an undefined sbox_base import in the ordinary non-MIC source profile.
    if unsafe { mem_sbox_access_metadata.attached } != 0 {
        unsafe { sbox_write(offset, value) };
    }
}

// The existing arrival word also gates clone_flags_result (any nonzero rejects).
// INT_MIN is a transient staging state under the existing exclusive core lock;
// a negative errno is a terminal pre-enrollment failure, never a fake arrival.
const MEM_CORE_STAGING: CInt = CInt::MIN;

#[repr(C)]
struct MemCoredumpMetadata {
    core_limit_index: CULong,
    busy: CInt,
    nomem: CInt,
    nowait: CULong,
    syscall_number: CULong,
    alloc_file: *mut i8,
    alloc_line: CInt,
    free_file: *mut i8,
    free_line: CInt,
    records: [*mut u8; 2],
    flags_byte: usize,
}

enum MemCoreAdmission {
    StageLeader,
    Follower(CInt),
    Aborted(CInt),
}

unsafe extern "C" {
    static mem_coredump_metadata: MemCoredumpMetadata;
    #[link_name = "do_kill"]
    fn mem_core_signal(
        thread: *mut crate::abi::Thread, pid: CInt, tid: CInt, signal: CInt,
        info: *mut crate::abi::SigInfo, ptrace_continue: CInt,
    ) -> CULong;
    #[link_name = "do_syscall"]
    fn mem_core_syscall(request: *mut crate::abi::SyscallRequest, cpu: CInt) -> CLong;
}

/// # Safety
/// The caller owns the genuine exclusive IRQsave coredump lock. This word is
/// initialized once to zero for the live Process; no completed/aborted generation
/// is reused before that terminal process is destroyed. Other clone consumers
/// retain their original any-nonzero rejection. No caller may enter while another
/// owner holds the lock in MEM_CORE_STAGING.
unsafe fn mem_core_admit_locked(word: *mut CInt) -> MemCoreAdmission {
    // SAFETY: Genuine aligned Process CInt, accessed through existing atomic ABI.
    let count = unsafe { AtomicI32::from_ptr(word) };
    let observed = count.load(Ordering::SeqCst);
    if observed == 0 {
        count.store(MEM_CORE_STAGING, Ordering::SeqCst);
        MemCoreAdmission::StageLeader
    } else if observed < 0 {
        // A published failure remains a failure; never reset or turn it into ACK.
        MemCoreAdmission::Aborted(observed)
    } else {
        MemCoreAdmission::Follower(count.fetch_add(1, Ordering::SeqCst))
    }
}

/// # Safety
/// Caller owns the same exclusive lock and exactly one uncommitted stage. A
/// positive publication is the leader's first REAL arrival; a negative result
/// publishes only its genuine pre-enrollment error. Barrier2 remains untouched.
unsafe fn mem_core_publish_stage(word: *mut CInt, result: CInt) {
    unsafe { AtomicI32::from_ptr(word) }.store(result, Ordering::SeqCst);
}

/// # Safety
/// link is a live actual Thread.siblings_list, retained by the original threads
/// list ownership. No Rust reference or new thread reference count is acquired.
unsafe fn mem_core_thread_from_link(link: *mut AbiListHead) -> *mut crate::abi::Thread {
    link.cast::<u8>()
        .wrapping_sub(offset_of!(crate::abi::Thread, siblings_list))
        .cast::<crate::abi::Thread>()
}

/// Execute the whole original core protocol with fail-closed ENOMEM admission.
///
/// # Safety
/// Retain the original live thread/Process/frame and fatal-signal context. The
/// genuine supported-profile coredump reader lock is an exclusive IRQsave spin
/// lock; staging and every admission must use it. Process counters start at zero
/// and describe one terminal process-lifetime generation, never a reusable epoch.
/// Existing thread-list, wake/schedule, gencore/coretable, syscall/DMA and caller
/// termination contracts remain required. This fixes the exact rank0 tid-table
/// failure before enrollment; it does not invent signal, barrier or dump ACKs.
#[no_mangle]
pub unsafe extern "C" fn coredump(
    thread: *mut crate::abi::Thread, _regs: *mut c_void, signal: CInt,
) -> CInt {
    // SAFETY: Original synchronous owner provides live raw fields and initialized
    // intrusive lists. Avoid references across signal/schedule/offload providers.
    unsafe {
        let metadata = &mem_coredump_metadata;
        let process = (*thread).proc;
        let first = core::ptr::addr_of_mut!((*process).coredump_barrier_count);
        let second = core::ptr::addr_of_mut!((*process).coredump_barrier_count2);
        let head = core::ptr::addr_of_mut!((*process).threads_list);
        let core_lock = core::ptr::addr_of_mut!((*process).coredump_lock)
            .cast::<crate::lock_helpers::McsRwlockLock>();
        let threads_lock = core::ptr::addr_of_mut!((*process).threads_lock)
            .cast::<crate::lock_helpers::McsRwlockLock>();
        let mut core_node = core::mem::MaybeUninit::<
            crate::lock_helpers::McsRwlockNodeIrqsave,
        >::uninit();
        let mut list_node = core::mem::MaybeUninit::<
            crate::lock_helpers::McsRwlockNodeIrqsave,
        >::uninit();
        let mut ids: *mut CInt = core::ptr::null_mut();
        let mut result: CInt;
        if mem_tracking_debug_enabled(metadata.records[0], metadata.flags_byte) {
            kprintf(
                b"%s: pid=%d,tid=%d,coredump_barrier_count=%d\n\0".as_ptr().cast(),
                b"coredump\0".as_ptr().cast::<i8>(),
                (*process).pid, (*thread).tid, AtomicI32::from_ptr(first).load(Ordering::SeqCst),
            );
        }
        'dump: {
            if (*process).rlimit[metadata.core_limit_index as usize].rlim_cur == 0 {
                result = metadata.busy;
                break 'dump;
            }
            crate::lock_helpers::__mcs_rwlock_reader_lock(core_lock, core_node.as_mut_ptr());
            let rank;
            match mem_core_admit_locked(first) {
                MemCoreAdmission::Aborted(error) => {
                    // Exactly this acquisition is released; no barrier enrolled.
                    crate::lock_helpers::__mcs_rwlock_reader_unlock(
                        core_lock, core_node.as_mut_ptr(),
                    );
                    result = error;
                    break 'dump;
                }
                MemCoreAdmission::Follower(arrival_rank) => rank = arrival_rank,
                MemCoreAdmission::StageLeader => {
                    rank = 0;
                    let mut peers: CInt = 0;
                    crate::lock_helpers::__mcs_rwlock_reader_lock(
                        threads_lock, list_node.as_mut_ptr(),
                    );
                    let mut link = (*head).next;
                    while link != head {
                        if mem_core_thread_from_link(link) != thread {
                            peers = peers.wrapping_add(1);
                        }
                        link = (*link).next;
                    }
                    if peers != 0 {
                        let bytes = size_of::<CInt>().wrapping_mul(peers as usize) as CInt;
                        ids = kmalloc_tracked(
                            bytes, metadata.nowait, metadata.alloc_file, metadata.alloc_line,
                        ).cast::<CInt>();
                        if ids.is_null() {
                            // This is BEFORE any real arrival publication. The
                            // same lock excludes every possible core follower.
                            crate::lock_helpers::__mcs_rwlock_reader_unlock(
                                threads_lock, list_node.as_mut_ptr(),
                            );
                            mem_core_publish_stage(first, metadata.nomem);
                            crate::lock_helpers::__mcs_rwlock_reader_unlock(
                                core_lock, core_node.as_mut_ptr(),
                            );
                            kprintf(
                                b"%s: ERROR: allocating tid table\n\0".as_ptr().cast(),
                                b"coredump\0".as_ptr().cast::<i8>(),
                            );
                            result = metadata.nomem;
                            break 'dump;
                        }
                        let mut index = 0;
                        link = (*head).next;
                        while link != head {
                            let peer = mem_core_thread_from_link(link);
                            if peer != thread {
                                ids.add(index).write((*peer).tid);
                                index += 1;
                            }
                            link = (*link).next;
                        }
                    }
                    crate::lock_helpers::__mcs_rwlock_reader_unlock(
                        threads_lock, list_node.as_mut_ptr(),
                    );
                    // Allocation/staging succeeded: publish the genuine leader
                    // arrival BEFORE signaling, never a fabricated peer count.
                    mem_core_publish_stage(first, 1);
                    let mut index = 0;
                    while index < peers as usize {
                        let tid = ids.add(index).read();
                        if mem_tracking_debug_enabled(metadata.records[1], metadata.flags_byte) {
                            kprintf(
                                b"%s: calling do_kill, target tid=%d\n\0".as_ptr().cast(),
                                b"coredump\0".as_ptr().cast::<i8>(), tid,
                            );
                        }
                        let _ = mem_core_signal(
                            thread, (*process).pid, tid, signal, core::ptr::null_mut(), 0,
                        );
                        index += 1;
                    }
                }
            }
            crate::lock_helpers::__mcs_rwlock_reader_unlock(core_lock, core_node.as_mut_ptr());
            let participants;
            loop {
                let mut live: CInt = 0;
                crate::lock_helpers::__mcs_rwlock_reader_lock(
                    threads_lock, list_node.as_mut_ptr(),
                );
                let mut link = (*head).next;
                while link != head {
                    live = live.wrapping_add(1);
                    link = (*link).next;
                }
                crate::lock_helpers::__mcs_rwlock_reader_unlock(
                    threads_lock, list_node.as_mut_ptr(),
                );
                if live == AtomicI32::from_ptr(first).load(Ordering::SeqCst) {
                    link = (*head).next;
                    while link != head {
                        coredump_wakeup(mem_core_thread_from_link(link));
                        link = (*link).next;
                    }
                    participants = live;
                    break;
                }
                coredump_wait(thread);
            }
            if rank != 0 {
                // Original follower return convention retained; this is not a
                // new claim that rank0's gencore/offload succeeded.
                result = 0;
            } else {
                let mut table: *mut crate::abi::Coretable = core::ptr::null_mut();
                let mut chunks = core::mem::MaybeUninit::<CInt>::uninit();
                result = crate::gencore::gencore(
                    process, &raw mut table, chunks.as_mut_ptr(),
                    (*process).saved_cmdline, signal,
                );
                if result != 0 {
                    kprintf(
                        b"%s: ERROR: gencore returned %d\n\0".as_ptr().cast(),
                        b"coredump\0".as_ptr().cast::<i8>(), result,
                    );
                } else {
                    // The actual SMP IHK_DMA_ALIGN macro is empty; native
                    // SyscallRequest alignment is retained, not invented64B.
                    let mut request = core::mem::MaybeUninit::<
                        crate::abi::SyscallRequest,
                    >::uninit();
                    let request = request.as_mut_ptr();
                    core::ptr::addr_of_mut!((*request).number).write(metadata.syscall_number);
                    let args = core::ptr::addr_of_mut!((*request).args).cast::<CULong>();
                    args.add(0).write(chunks.assume_init() as CULong);
                    args.add(1).write(mem_virt_to_phys_bridge(table.cast()));
                    args.add(2).write(mem_virt_to_phys_bridge((*(*thread).proc).saved_cmdline.cast()));
                    args.add(3).write((*(*thread).proc).saved_cmdline_len as CULong);
                    result = mem_core_syscall(request, (*thread).cpu_id) as CInt;
                    if result == 0 {
                        kprintf(
                            b"%s: INFO: coredump done\n\0".as_ptr().cast(),
                            b"coredump\0".as_ptr().cast::<i8>(),
                        );
                    } else {
                        kprintf(
                            b"%s: ERROR: do_syscall failed (%d)\n\0".as_ptr().cast(),
                            b"coredump\0".as_ptr().cast::<i8>(), result,
                        );
                    }
                    crate::gencore::freecore(&raw mut table);
                }
            }
            AtomicI32::from_ptr(second).fetch_add(1, Ordering::SeqCst);
            loop {
                if participants == AtomicI32::from_ptr(second).load(Ordering::SeqCst) {
                    let mut link = (*head).next;
                    while link != head {
                        coredump_wakeup(mem_core_thread_from_link(link));
                        link = (*link).next;
                    }
                    break;
                }
                coredump_wait(thread);
            }
        }
        // Exactly once on every returning path, including NULL abort/follower ids.
        kfree_tracked(ids.cast(), metadata.free_file, metadata.free_line);
        result
    }
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

/// Delegate the actual whole-free callback to its existing physical-page lookup.
///
/// # Safety
/// Keep the original hash/bucket-lock/Page lifetime contract of phys_to_page.
/// The returned pointer remains borrowed; this adapter acquires no Page reference
/// and adds no null check, physical conversion, retry or accounting operation.
#[no_mangle]
pub unsafe extern "C" fn mem_phys_to_page_bridge(phys: CULong) -> *mut MemPage {
    // SAFETY: The synchronous caller supplies the same physical value and retains
    // all lookup/storage ownership required by the already-qualified Rust entry.
    unsafe { phys_to_page(phys) }
}

// Defining storage only. Consumers retain the original plain CInt load/store
// discipline and page-fault diagnostic lifetime. These are deliberately not
// AtomicI32: this port does not introduce synchronization or a new thread owner.
mod owned_page_fault_diagnostic_state {
    use super::CInt;

    #[export_name = "mem_page_fault_log_count"]
    static mut COUNT: CInt = 0;

    #[export_name = "mem_page_fault_log_pid"]
    static mut PID: CInt = -1;

    const _: () = {
        assert!(core::mem::size_of::<CInt>() == 4);
        assert!(core::mem::align_of::<CInt>() == 4);
    };
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Permanent defining storage. No getter, constructor, lock, reference transfer,
// initialization reordering or atomic upgrade is introduced. Existing consumers
// continue their original raw field/list/atomic access under the same owners.
mod owned_mem_runtime_data {
    use super::{AbiListHead, CInt, CULong, IhkMcPaOps, IhkSpinlock, MemNumaNode};
    use super::{mckernel_allocate_aligned_pages_node, mckernel_free_pages};
    use super::numa_sysfs_show_meminfo;
    use crate::abi::{SysfsOps, TlbFlushEntry};

    // GCC9's retained COMMON objects have 32-byte symbol alignment. The wrapper
    // preserves that actual placement; field0 has offset0 and identical array
    // stride/extent. It does not add a per-element alignment or padding change.
    #[repr(C, align(32))]
    struct CommonArray<T>(T);

    #[export_name = "pa_start"]
    static mut PA_START: CULong = 0;
    #[export_name = "pa_end"]
    static mut PA_END: CULong = 0;

    #[export_name = "memory_nodes"]
    static mut MEMORY_NODES: [MemNumaNode; 512] = [const {
        // SAFETY: This genuine repr(C) node contains only C integer/atomic words,
        // raw pointers and intrusive list/lock storage, all valid when zeroed.
        // Boot code, not this initializer, later establishes live list topology.
        unsafe { core::mem::zeroed() }
    }; 512];

    #[export_name = "tlb_flush_vector"]
    static mut TLB_FLUSH_VECTOR: [TlbFlushEntry; 64] = [const {
        // SAFETY: Genuine repr(C,align64) entry has raw pointers and integer lock/
        // atomic words. All-zero exactly preserves the original static storage;
        // actual setup/publication and pending accounting remain in their owners.
        unsafe { core::mem::zeroed() }
    }; 64];

    #[export_name = "anon_on_demand"]
    static mut ANON_ON_DEMAND: CInt = 0;
    #[export_name = "xpmem_page_in_remote_on_attach"]
    static mut XPMEM_PAGE_IN_REMOTE_ON_ATTACH: CInt = 0;
    #[export_name = "sysctl_overcommit_memory"]
    static mut SYSCTL_OVERCOMMIT_MEMORY: CInt = 1;
    #[export_name = "memdebug"]
    static mut MEMDEBUG: *mut i8 = core::ptr::null_mut();

    #[export_name = "vmap_allocator"]
    static mut VMAP_ALLOCATOR: *mut crate::page_alloc::IhkPageAllocatorDesc =
        core::ptr::null_mut();

    #[export_name = "allocator"]
    static mut ALLOCATOR: IhkMcPaOps = IhkMcPaOps {
        alloc_page: Some(mckernel_allocate_aligned_pages_node),
        free_page: Some(mckernel_free_pages),
        alloc: core::ptr::null_mut(),
        free: core::ptr::null_mut(),
    };

    #[export_name = "numa_sysfs_meminfo"]
    static mut NUMA_SYSFS_MEMINFO: SysfsOps = SysfsOps {
        show: Some(numa_sysfs_show_meminfo),
        store: None,
        release: None,
    };

    #[export_name = "pagealloc_track_hash"]
    static mut PAGEALLOC_TRACK_HASH: CommonArray<[AbiListHead; 256]> = CommonArray([const {
        AbiListHead { next: core::ptr::null_mut(), prev: core::ptr::null_mut() }
    }; 256]);

    #[export_name = "pagealloc_track_hash_locks"]
    static mut PAGEALLOC_TRACK_HASH_LOCKS: CommonArray<[IhkSpinlock; 256]> = CommonArray([const {
        IhkSpinlock { head_tail: 0 }
    }; 256]);

    #[export_name = "pagealloc_addr_hash"]
    static mut PAGEALLOC_ADDR_HASH: CommonArray<[AbiListHead; 256]> = CommonArray([const {
        AbiListHead { next: core::ptr::null_mut(), prev: core::ptr::null_mut() }
    }; 256]);

    #[export_name = "pagealloc_addr_hash_locks"]
    static mut PAGEALLOC_ADDR_HASH_LOCKS: CommonArray<[IhkSpinlock; 256]> = CommonArray([const {
        IhkSpinlock { head_tail: 0 }
    }; 256]);

    #[export_name = "pagealloc_track_initialized"]
    static mut PAGEALLOC_TRACK_INITIALIZED: CInt = 0;

    #[export_name = "pagealloc_runcount"]
    static mut PAGEALLOC_RUNCOUNT: CInt = 0;

    #[export_name = "kmalloc_track_hash"]
    static mut KMALLOC_TRACK_HASH: CommonArray<[AbiListHead; 256]> = CommonArray([const {
        AbiListHead { next: core::ptr::null_mut(), prev: core::ptr::null_mut() }
    }; 256]);

    #[export_name = "kmalloc_track_hash_locks"]
    static mut KMALLOC_TRACK_HASH_LOCKS: CommonArray<[IhkSpinlock; 256]> = CommonArray([const {
        IhkSpinlock { head_tail: 0 }
    }; 256]);

    #[export_name = "kmalloc_addr_hash"]
    static mut KMALLOC_ADDR_HASH: CommonArray<[AbiListHead; 256]> = CommonArray([const {
        AbiListHead { next: core::ptr::null_mut(), prev: core::ptr::null_mut() }
    }; 256]);

    #[export_name = "kmalloc_addr_hash_locks"]
    static mut KMALLOC_ADDR_HASH_LOCKS: CommonArray<[IhkSpinlock; 256]> = CommonArray([const {
        IhkSpinlock { head_tail: 0 }
    }; 256]);

    #[export_name = "kmalloc_track_initialized"]
    static mut KMALLOC_TRACK_INITIALIZED: CInt = 0;

    #[export_name = "kmalloc_runcount"]
    static mut KMALLOC_RUNCOUNT: CInt = 0;

    #[export_name = "page_hash"]
    static mut PAGE_HASH: CommonArray<[AbiListHead; 1024]> = CommonArray([const {
        AbiListHead { next: core::ptr::null_mut(), prev: core::ptr::null_mut() }
    }; 1024]);

    #[export_name = "page_hash_locks"]
    static mut PAGE_HASH_LOCKS: CommonArray<[IhkSpinlock; 1024]> = CommonArray([const {
        IhkSpinlock { head_tail: 0 }
    }; 1024]);

    const _: () = {
        use core::mem::{align_of, offset_of, size_of};
        assert!(size_of::<CInt>() == 4 && align_of::<CInt>() == 4);
        assert!(size_of::<CULong>() == 8 && align_of::<CULong>() == 8);
        assert!(size_of::<MemNumaNode>() == 256 && align_of::<MemNumaNode>() == 64);
        assert!(size_of::<[MemNumaNode; 512]>() == 0x20000);
        assert!(size_of::<TlbFlushEntry>() == 64 && align_of::<TlbFlushEntry>() == 64);
        assert!(size_of::<[TlbFlushEntry; 64]>() == 4096);
        assert!(size_of::<IhkMcPaOps>() == 32 && align_of::<IhkMcPaOps>() == 8);
        assert!(size_of::<SysfsOps>() == 24 && align_of::<SysfsOps>() == 8);
        assert!(size_of::<CommonArray<[AbiListHead; 256]>>() == 4096);
        assert!(size_of::<CommonArray<[IhkSpinlock; 256]>>() == 1024);
        assert!(size_of::<CommonArray<[AbiListHead; 1024]>>() == 16384);
        assert!(size_of::<CommonArray<[IhkSpinlock; 1024]>>() == 4096);
        assert!(align_of::<CommonArray<[AbiListHead; 256]>>() == 32);
        assert!(offset_of!(CommonArray<[AbiListHead; 256]>, 0) == 0);
    };
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact supported-profile configuration values from the retained real C headers
// and production argv. The real-C witness rejects any different config rather
// than silently reusing this static data in another architecture/feature profile.
mod owned_mem_geometry {
    use super::{CInt, CULong, MemNumaSysfsShowGeometry, MemUnhandledFaultMetadata};

    #[export_name = "mem_interleave_nodes_mask_bits"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static MEM_INTERLEAVE_NODES_MASK_BITS: CInt = 256;

    #[export_name = "mem_vmap_init_start"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static MEM_VMAP_INIT_START: CULong = 0xffff_8500_0000_0000;

    #[export_name = "mem_vmap_init_size"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static MEM_VMAP_INIT_SIZE: CULong = 0x0000_0001_0000_0000;

    #[export_name = "mem_vmap_init_unit"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static MEM_VMAP_INIT_UNIT: CULong = super::PAGE_SIZE;

    #[export_name = "mem_vmap_init_first_level"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static MEM_VMAP_INIT_FIRST_LEVEL: CInt = 0;

    #[export_name = "page_init_hash_bucket_count"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static PAGE_INIT_HASH_BUCKET_COUNT: CInt = 1024;

    #[export_name = "page_init_hash_head_stride"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static PAGE_INIT_HASH_HEAD_STRIDE: CULong = core::mem::size_of::<super::AbiListHead>() as CULong;

    #[export_name = "page_unmap_hash_mask"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static PAGE_UNMAP_HASH_MASK: CULong = 1023;

    #[export_name = "page_unmap_hash_shift"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static PAGE_UNMAP_HASH_SHIFT: CInt = super::PAGE_SHIFT as CInt;

    #[export_name = "page_unmap_lock_stride"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static PAGE_UNMAP_LOCK_STRIDE: CULong = core::mem::size_of::<super::IhkSpinlock>() as CULong;

    #[export_name = "mem_fatal_user_bytes_geometry"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static FATAL_USER_BYTES_GEOMETRY: [CULong; 2] = [super::PAGE_SIZE, 0xffff_ffff_fe80_0000];

    #[export_name = "mem_remote_tlb_geometry"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static REMOTE_TLB_GEOMETRY: [CInt; 3] = [64, 68, 1024];

    #[export_name = "mem_numa_log_rbtree_enabled"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static NUMA_LOG_RBTREE_ENABLED: CInt = 1;

    #[export_name = "mem_numa_sysfs_show_geometry"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static NUMA_SYSFS_SHOW_GEOMETRY: MemNumaSysfsShowGeometry = MemNumaSysfsShowGeometry {
        rbtree: 1,
        kb_shift: (super::PAGE_SHIFT - 10) as u32,
    };

    #[export_name = "mem_unhandled_fault_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static UNHANDLED_FAULT_METADATA: MemUnhandledFaultMetadata = MemUnhandledFaultMetadata {
        pf_prot: 1 << 0,
        pf_write: 1 << 1,
        pf_user: 1 << 2,
        pf_reserved: 1 << 3,
        pf_instruction: 1 << 4,
        mf_regular_file: super::MF_REG_FILE as u32,
        fugaku: 0,
        debug_stack: 0,
        instruction_address: None,
        stack_address: None,
    };

    const _: () = {
        use core::mem::{align_of, offset_of, size_of};
        assert!(size_of::<MemNumaSysfsShowGeometry>() == 8);
        assert!(align_of::<MemNumaSysfsShowGeometry>() == 4);
        assert!(offset_of!(MemNumaSysfsShowGeometry, kb_shift) == 4);
        assert!(size_of::<MemUnhandledFaultMetadata>() == 72);
        assert!(align_of::<MemUnhandledFaultMetadata>() == 8);
        assert!(offset_of!(MemUnhandledFaultMetadata, instruction_address) == 56);
        assert!(offset_of!(MemUnhandledFaultMetadata, stack_address) == 64);
    };
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Actual Cdescriptor provenance is frozen from the successful current80 producer's
// retained preprocessed source. It is an origin snapshot, not a claim that later
// source edits retain the same current line or that Rust file!/line! means C.
// This matches the accepted F05 typed Ddebug data-ownership mechanism.
mod owned_mem_debug_records {
    use crate::debug::Ddebug;

    static TRACE_FILE: [u8; 209] = [
        47, 104, 111, 109, 101, 47, 104, 111, 108, 100, 101, 110, 47, 109, 99, 107, 101, 114,
        110, 101, 108, 45, 119, 111, 114, 107, 47, 104, 111, 115, 116, 45, 112, 114, 101, 112,
        97, 114, 97, 116, 105, 111, 110, 47, 118, 101, 108, 111, 99, 105, 116, 121, 45, 105,
        110, 116, 101, 114, 118, 101, 110, 116, 105, 111, 110, 45, 50, 48, 50, 54, 49, 48,
        50, 51, 45, 54, 47, 109, 49, 52, 45, 102, 105, 108, 101, 45, 108, 97, 110, 101,
        115, 47, 107, 101, 114, 110, 101, 108, 45, 109, 101, 109, 47, 110, 101, 120, 116, 49,
        51, 45, 113, 117, 97, 108, 105, 102, 105, 101, 100, 45, 99, 111, 114, 101, 45, 99,
        117, 114, 114, 101, 110, 116, 45, 112, 114, 111, 100, 117, 99, 116, 105, 111, 110, 45,
        112, 114, 111, 112, 111, 115, 97, 108, 45, 49, 47, 99, 97, 110, 111, 110, 105, 99,
        97, 108, 56, 48, 45, 70, 48, 53, 45, 99, 108, 111, 115, 117, 114, 101, 45, 114,
        101, 102, 114, 101, 115, 104, 45, 49, 47, 115, 111, 117, 114, 99, 101, 47, 107, 101,
        114, 110, 101, 108, 47, 109, 101, 109, 46, 99, 0,
    ];

    #[export_name = "mem_dump_complete_debug_record"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_DUMP_COMPLETE_DEBUG_RECORD: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_dump_complete_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 7727 | (0 << 24),
    };

    #[export_name = "mem_kmalloc_leak_log_bridge_debug_record_0"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_KMALLOC_LEAK_LOG_BRIDGE_DEBUG_RECORD_0: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_kmalloc_leak_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 6879 | (0 << 24),
    };

    #[export_name = "mem_kmalloc_track_log_bridge_debug_record_0"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_KMALLOC_TRACK_LOG_BRIDGE_DEBUG_RECORD_0: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_kmalloc_track_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 6847 | (0 << 24),
    };

    #[export_name = "mem_kmalloc_track_log_bridge_debug_record_1"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_KMALLOC_TRACK_LOG_BRIDGE_DEBUG_RECORD_1: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_kmalloc_track_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 6852 | (0 << 24),
    };

    #[export_name = "mem_kmalloc_track_log_bridge_debug_record_2"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_KMALLOC_TRACK_LOG_BRIDGE_DEBUG_RECORD_2: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_kmalloc_track_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 6857 | (0 << 24),
    };

    #[export_name = "mem_kmalloc_track_log_bridge_debug_record_3"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_KMALLOC_TRACK_LOG_BRIDGE_DEBUG_RECORD_3: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_kmalloc_track_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 6862 | (0 << 24),
    };

    #[export_name = "mem_rusage_init_debug_record"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_RUSAGE_INIT_DEBUG_RECORD: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_rusage_init_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 6583 | (0 << 24),
    };

    #[export_name = "page_unmap_debug_enter"]
    #[used]
    #[link_section = "__verbose"]
    static mut PAGE_UNMAP_DEBUG_ENTER: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"page_unmap_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 6315 | (0 << 24),
    };

    #[export_name = "page_unmap_debug_still_mapped"]
    #[used]
    #[link_section = "__verbose"]
    static mut PAGE_UNMAP_DEBUG_STILL_MAPPED: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"page_unmap_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 6320 | (0 << 24),
    };

    #[export_name = "page_unmap_debug_unmapped"]
    #[used]
    #[link_section = "__verbose"]
    static mut PAGE_UNMAP_DEBUG_UNMAPPED: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"page_unmap_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 6325 | (0 << 24),
    };

    #[export_name = "mem_page_fault_debug_0"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_PAGE_FAULT_DEBUG_0: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"page_fault_handler\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 4831 | (0 << 24),
    };

    #[export_name = "mem_page_fault_debug_2"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_PAGE_FAULT_DEBUG_2: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"page_fault_handler\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 4841 | (0 << 24),
    };

    #[export_name = "mem_page_fault_debug_3"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_PAGE_FAULT_DEBUG_3: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"page_fault_handler\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 4845 | (0 << 24),
    };

    #[export_name = "mem_coredump_debug_0"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_COREDUMP_DEBUG_0: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"coredump\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 4310 | (0 << 24),
    };

    #[export_name = "mem_coredump_debug_1"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_COREDUMP_DEBUG_1: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"coredump\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 4314 | (0 << 24),
    };

    #[export_name = "mem_coredump_wakeup_debug_record"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_COREDUMP_WAKEUP_DEBUG_RECORD: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"coredump_wakeup\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 4269 | (0 << 24),
    };

    #[export_name = "mem_coredump_wait_sleep_record"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_COREDUMP_WAIT_SLEEP_RECORD: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"coredump_wait\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 4220 | (0 << 24),
    };

    #[export_name = "mem_coredump_wait_resume_record"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_COREDUMP_WAIT_RESUME_RECORD: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"coredump_wait\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 4224 | (0 << 24),
    };

    #[export_name = "mem_allocation_log_record_0"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_ALLOCATION_LOG_RECORD_0: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_mckernel_alloc_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 3583 | (0 << 24),
    };

    #[export_name = "mem_allocation_log_record_1"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_ALLOCATION_LOG_RECORD_1: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_mckernel_alloc_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 3588 | (0 << 24),
    };

    #[export_name = "mem_allocation_log_record_2"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_ALLOCATION_LOG_RECORD_2: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_mckernel_alloc_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 3593 | (0 << 24),
    };

    #[export_name = "mem_allocation_log_record_3"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_ALLOCATION_LOG_RECORD_3: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_mckernel_alloc_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 3598 | (0 << 24),
    };

    #[export_name = "mem_allocation_log_record_4"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_ALLOCATION_LOG_RECORD_4: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_mckernel_alloc_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 3603 | (0 << 24),
    };

    #[export_name = "mem_allocation_log_record_6"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_ALLOCATION_LOG_RECORD_6: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_mckernel_alloc_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 3615 | (0 << 24),
    };

    #[export_name = "mem_reserve_pages_debug_record"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_RESERVE_PAGES_DEBUG_RECORD: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_reserve_pages_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 3425 | (0 << 24),
    };

    #[export_name = "mem_pagealloc_leak_log_bridge_debug_record_0"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_PAGEALLOC_LEAK_LOG_BRIDGE_DEBUG_RECORD_0: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_pagealloc_leak_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 2644 | (0 << 24),
    };

    #[export_name = "mem_pagealloc_track_log_bridge_debug_record_0"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_PAGEALLOC_TRACK_LOG_BRIDGE_DEBUG_RECORD_0: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_pagealloc_track_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 2594 | (0 << 24),
    };

    #[export_name = "mem_pagealloc_track_log_bridge_debug_record_1"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_PAGEALLOC_TRACK_LOG_BRIDGE_DEBUG_RECORD_1: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_pagealloc_track_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 2599 | (0 << 24),
    };

    #[export_name = "mem_pagealloc_track_log_bridge_debug_record_2"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_PAGEALLOC_TRACK_LOG_BRIDGE_DEBUG_RECORD_2: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_pagealloc_track_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 2604 | (0 << 24),
    };

    #[export_name = "mem_pagealloc_track_log_bridge_debug_record_3"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_PAGEALLOC_TRACK_LOG_BRIDGE_DEBUG_RECORD_3: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_pagealloc_track_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 2609 | (0 << 24),
    };

    #[export_name = "mem_pagealloc_track_log_bridge_debug_record_4"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_PAGEALLOC_TRACK_LOG_BRIDGE_DEBUG_RECORD_4: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_pagealloc_track_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 2614 | (0 << 24),
    };

    #[export_name = "mem_pagealloc_track_log_bridge_debug_record_5"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_PAGEALLOC_TRACK_LOG_BRIDGE_DEBUG_RECORD_5: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_pagealloc_track_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 2619 | (0 << 24),
    };

    #[export_name = "mem_pagealloc_track_log_bridge_debug_record_6"]
    #[used]
    #[link_section = "__verbose"]
    static mut MEM_PAGEALLOC_TRACK_LOG_BRIDGE_DEBUG_RECORD_6: Ddebug = Ddebug {
        file: TRACE_FILE.as_ptr().cast(),
        func: b"mem_pagealloc_track_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 2624 | (0 << 24),
    };

    const _: () = {
        use core::mem::{align_of, offset_of, size_of};
        assert!(size_of::<Ddebug>() == 32 && align_of::<Ddebug>() == 8);
        assert!(offset_of!(Ddebug, file) == 0);
        assert!(offset_of!(Ddebug, func) == 8);
        assert!(offset_of!(Ddebug, fmt) == 16);
        assert!(offset_of!(Ddebug, line_flags) == 24);
    };
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Immutable address/config containers only. Pointee flags remain mutable under
// original debug-control rules; publishing these addresses grants no reference,
// synchronization, new lifetime or permission to mutate through a safe API.
mod owned_mem_debug_addresses {
    use super::{
        MemCoredumpWaitMetadata,
        MemCoredumpWakeupMetadata,
        MemDumpCompleteDebugMetadata,
        MemTrackingDebugRecords1,
        MemTrackingDebugRecords4,
        MemTrackingDebugRecords7,
    };
    use crate::debug::Ddebug;

    #[repr(C)]
    struct OwnedThreeRecordAddresses {
        records: [*mut u8; 3],
        flags_byte: usize,
    }

    // SAFETY: This exact repr(C) container has only scalar configuration and
    // permanent raw record addresses. It is immutable and exposes no safe
    // dereference; record accesses retain their original external discipline.
    unsafe impl Sync for MemCoredumpWaitMetadata {}

    // SAFETY: This exact repr(C) container has only scalar configuration and
    // permanent raw record addresses. It is immutable and exposes no safe
    // dereference; record accesses retain their original external discipline.
    unsafe impl Sync for MemCoredumpWakeupMetadata {}

    // SAFETY: This exact repr(C) container has only scalar configuration and
    // permanent raw record addresses. It is immutable and exposes no safe
    // dereference; record accesses retain their original external discipline.
    unsafe impl Sync for MemDumpCompleteDebugMetadata {}

    // SAFETY: This exact repr(C) container has only scalar configuration and
    // permanent raw record addresses. It is immutable and exposes no safe
    // dereference; record accesses retain their original external discipline.
    unsafe impl Sync for MemTrackingDebugRecords1 {}

    // SAFETY: This exact repr(C) container has only scalar configuration and
    // permanent raw record addresses. It is immutable and exposes no safe
    // dereference; record accesses retain their original external discipline.
    unsafe impl Sync for MemTrackingDebugRecords4 {}

    // SAFETY: This exact repr(C) container has only scalar configuration and
    // permanent raw record addresses. It is immutable and exposes no safe
    // dereference; record accesses retain their original external discipline.
    unsafe impl Sync for MemTrackingDebugRecords7 {}

    // SAFETY: This exact repr(C) container has only scalar configuration and
    // permanent raw record addresses. It is immutable and exposes no safe
    // dereference; record accesses retain their original external discipline.
    unsafe impl Sync for OwnedThreeRecordAddresses {}

    unsafe extern "C" {
        #[link_name = "mem_coredump_wait_resume_record"]
        static mut RECORD_0: Ddebug;
        #[link_name = "mem_coredump_wait_sleep_record"]
        static mut RECORD_1: Ddebug;
        #[link_name = "mem_coredump_wakeup_debug_record"]
        static mut RECORD_2: Ddebug;
        #[link_name = "mem_dump_complete_debug_record"]
        static mut RECORD_3: Ddebug;
        #[link_name = "mem_kmalloc_leak_log_bridge_debug_record_0"]
        static mut RECORD_4: Ddebug;
        #[link_name = "mem_kmalloc_track_log_bridge_debug_record_0"]
        static mut RECORD_5: Ddebug;
        #[link_name = "mem_kmalloc_track_log_bridge_debug_record_1"]
        static mut RECORD_6: Ddebug;
        #[link_name = "mem_kmalloc_track_log_bridge_debug_record_2"]
        static mut RECORD_7: Ddebug;
        #[link_name = "mem_kmalloc_track_log_bridge_debug_record_3"]
        static mut RECORD_8: Ddebug;
        #[link_name = "mem_pagealloc_leak_log_bridge_debug_record_0"]
        static mut RECORD_9: Ddebug;
        #[link_name = "mem_pagealloc_track_log_bridge_debug_record_0"]
        static mut RECORD_10: Ddebug;
        #[link_name = "mem_pagealloc_track_log_bridge_debug_record_1"]
        static mut RECORD_11: Ddebug;
        #[link_name = "mem_pagealloc_track_log_bridge_debug_record_2"]
        static mut RECORD_12: Ddebug;
        #[link_name = "mem_pagealloc_track_log_bridge_debug_record_3"]
        static mut RECORD_13: Ddebug;
        #[link_name = "mem_pagealloc_track_log_bridge_debug_record_4"]
        static mut RECORD_14: Ddebug;
        #[link_name = "mem_pagealloc_track_log_bridge_debug_record_5"]
        static mut RECORD_15: Ddebug;
        #[link_name = "mem_pagealloc_track_log_bridge_debug_record_6"]
        static mut RECORD_16: Ddebug;
        #[link_name = "mem_reserve_pages_debug_record"]
        static mut RECORD_17: Ddebug;
        #[link_name = "mem_rusage_init_debug_record"]
        static mut RECORD_18: Ddebug;
        #[link_name = "page_unmap_debug_enter"]
        static mut RECORD_19: Ddebug;
        #[link_name = "page_unmap_debug_still_mapped"]
        static mut RECORD_20: Ddebug;
        #[link_name = "page_unmap_debug_unmapped"]
        static mut RECORD_21: Ddebug;
    }

    #[export_name = "mem_dump_complete_debug_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_DUMP_COMPLETE_DEBUG_METADATA: MemDumpCompleteDebugMetadata = MemDumpCompleteDebugMetadata {
        // SAFETY: Permanent typed Rust Ddebug definitions are linked by the
        // exact Cmetadata symbol names; this forms addresses without access.
        record: unsafe { core::ptr::addr_of_mut!(RECORD_3).cast::<u8>() },
        flags_byte: 27,
    };

    #[export_name = "mem_kmalloc_leak_log_bridge_debug_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_KMALLOC_LEAK_LOG_BRIDGE_DEBUG_METADATA: MemTrackingDebugRecords1 = MemTrackingDebugRecords1 {
        // SAFETY: Permanent typed Rust Ddebug definitions are linked by the
        // exact Cmetadata symbol names; this forms addresses without access.
        records: [
            unsafe { core::ptr::addr_of_mut!(RECORD_4).cast::<u8>() },
        ],
        flags_byte: 27,
    };

    #[export_name = "mem_kmalloc_track_log_bridge_debug_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_KMALLOC_TRACK_LOG_BRIDGE_DEBUG_METADATA: MemTrackingDebugRecords4 = MemTrackingDebugRecords4 {
        // SAFETY: Permanent typed Rust Ddebug definitions are linked by the
        // exact Cmetadata symbol names; this forms addresses without access.
        records: [
            unsafe { core::ptr::addr_of_mut!(RECORD_5).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_6).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_7).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_8).cast::<u8>() },
        ],
        flags_byte: 27,
    };

    #[export_name = "mem_pagealloc_leak_log_bridge_debug_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_PAGEALLOC_LEAK_LOG_BRIDGE_DEBUG_METADATA: MemTrackingDebugRecords1 = MemTrackingDebugRecords1 {
        // SAFETY: Permanent typed Rust Ddebug definitions are linked by the
        // exact Cmetadata symbol names; this forms addresses without access.
        records: [
            unsafe { core::ptr::addr_of_mut!(RECORD_9).cast::<u8>() },
        ],
        flags_byte: 27,
    };

    #[export_name = "mem_pagealloc_track_log_bridge_debug_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_PAGEALLOC_TRACK_LOG_BRIDGE_DEBUG_METADATA: MemTrackingDebugRecords7 = MemTrackingDebugRecords7 {
        // SAFETY: Permanent typed Rust Ddebug definitions are linked by the
        // exact Cmetadata symbol names; this forms addresses without access.
        records: [
            unsafe { core::ptr::addr_of_mut!(RECORD_10).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_11).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_12).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_13).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_14).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_15).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_16).cast::<u8>() },
        ],
        flags_byte: 27,
    };

    #[export_name = "mem_rusage_init_debug_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_RUSAGE_INIT_DEBUG_METADATA: MemTrackingDebugRecords1 = MemTrackingDebugRecords1 {
        // SAFETY: Permanent typed Rust Ddebug definitions are linked by the
        // exact Cmetadata symbol names; this forms addresses without access.
        records: [
            unsafe { core::ptr::addr_of_mut!(RECORD_18).cast::<u8>() },
        ],
        flags_byte: 27,
    };

    #[export_name = "mem_reserve_pages_debug_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_RESERVE_PAGES_DEBUG_METADATA: MemDumpCompleteDebugMetadata = MemDumpCompleteDebugMetadata {
        // SAFETY: Permanent typed Rust Ddebug definitions are linked by the
        // exact Cmetadata symbol names; this forms addresses without access.
        record: unsafe { core::ptr::addr_of_mut!(RECORD_17).cast::<u8>() },
        flags_byte: 27,
    };

    #[export_name = "page_unmap_debug_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static PAGE_UNMAP_DEBUG_METADATA: OwnedThreeRecordAddresses = OwnedThreeRecordAddresses {
        // SAFETY: Permanent typed Rust Ddebug definitions are linked by the
        // exact Cmetadata symbol names; this forms addresses without access.
        records: [
            unsafe { core::ptr::addr_of_mut!(RECORD_19).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_20).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_21).cast::<u8>() },
        ],
        flags_byte: 27,
    };

    #[export_name = "mem_coredump_wakeup_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_COREDUMP_WAKEUP_METADATA: MemCoredumpWakeupMetadata = MemCoredumpWakeupMetadata {
        descheduled: 1,
        to_be_woken: 2,
        // SAFETY: Permanent typed Rust Ddebug definitions are linked by the
        // exact Cmetadata symbol names; this forms addresses without access.
        record: unsafe { core::ptr::addr_of_mut!(RECORD_2).cast::<u8>() },
        flags_byte: 27,
    };

    #[export_name = "mem_coredump_wait_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_COREDUMP_WAIT_METADATA: MemCoredumpWaitMetadata = MemCoredumpWaitMetadata {
        running: 0,
        descheduled: 1,
        interruptible: 2,
        // SAFETY: Permanent typed Rust Ddebug definitions are linked by the
        // exact Cmetadata symbol names; this forms addresses without access.
        records: [
            unsafe { core::ptr::addr_of_mut!(RECORD_1).cast::<u8>() },
            unsafe { core::ptr::addr_of_mut!(RECORD_0).cast::<u8>() },
        ],
        flags_byte: 27,
    };

    const _: () = {
        use core::mem::{align_of, offset_of, size_of};
        assert!(size_of::<MemDumpCompleteDebugMetadata>() == 16);
        assert!(size_of::<MemTrackingDebugRecords1>() == 16);
        assert!(size_of::<MemTrackingDebugRecords4>() == 40);
        assert!(size_of::<MemTrackingDebugRecords7>() == 64);
        assert!(size_of::<OwnedThreeRecordAddresses>() == 32);
        assert!(offset_of!(OwnedThreeRecordAddresses, flags_byte) == 24);
        assert!(size_of::<MemCoredumpWakeupMetadata>() == 24);
        assert!(offset_of!(MemCoredumpWakeupMetadata, record) == 8);
        assert!(size_of::<MemCoredumpWaitMetadata>() == 40);
        assert!(offset_of!(MemCoredumpWaitMetadata, records) == 16);
        assert!(align_of::<MemCoredumpWaitMetadata>() == 8);
    };
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Typed permanent owners and immutable addresses; no C getter or constructor.
mod owned_mem_static_addresses {
    use super::{AbiListHead, CInt, MemNumaNode, MemNumaSysfsRegistrationMetadata};
    use super::{MemSboxAccessMetadata, c_void, page_fault_handler};
    use super::query_free_mem_interrupt_handler;
    use crate::abi::SysfsOps;

    #[repr(transparent)]
    struct ImmutableAddress<T>(*mut T);
    // SAFETY: Only a permanent raw address is published, with no safe reference
    // or dereference API. Every pointee access retains its original owner/locks.
    unsafe impl<T> Sync for ImmutableAddress<T> {}

    // SAFETY: These exact readonly containers consist of scalar config and raw
    // permanent addresses. They expose no safe pointee access or mutation.
    unsafe impl Sync for MemNumaSysfsRegistrationMetadata {}
    unsafe impl Sync for MemSboxAccessMetadata {}

    #[repr(C)]
    struct InterruptHandler {
        list: AbiListHead,
        func: Option<unsafe extern "C" fn(*mut c_void)>,
        private: *mut c_void,
    }
    #[repr(C, align(32))]
    struct InterruptStorage(InterruptHandler);

    #[export_name = "query_free_mem_handler"]
    static mut QUERY_FREE_MEM_HANDLER: InterruptStorage = InterruptStorage(InterruptHandler {
        list: AbiListHead { next: core::ptr::null_mut(), prev: core::ptr::null_mut() },
        func: Some(query_free_mem_interrupt_handler),
        private: core::ptr::null_mut(),
    });

    // Pointer storage represents exactly the C address-to-ulong relocations. No
    // pointer-to-integer const evaluation or invented numeric runtime address is
    // used. Existing integer-view getters read the same LP64 address bytes.
    #[repr(C)]
    struct BootAddresses {
        page_fault_handler: *const c_void,
        query_free_handler: *const c_void,
        anon_slot: *mut CInt,
        xpmem_slot: *mut CInt,
        hugetlbfs_slot: *mut CInt,
    }
    // SAFETY: Only immutable code/static raw addresses, no safe dereference API.
    unsafe impl Sync for BootAddresses {}

    unsafe extern "C" {
        #[link_name = "anon_on_demand"]
        static mut ANON_ON_DEMAND: CInt;
        #[link_name = "xpmem_page_in_remote_on_attach"]
        static mut XPMEM_PAGE_IN_REMOTE_ON_ATTACH: CInt;
        #[link_name = "memory_nodes"]
        static mut MEMORY_NODES: [MemNumaNode; 512];
        #[link_name = "numa_sysfs_meminfo"]
        static mut NUMA_SYSFS_MEMINFO: SysfsOps;
        #[link_name = "vmap_allocator"]
        static mut VMAP_ALLOCATOR: *mut crate::page_alloc::IhkPageAllocatorDesc;
    }

    #[export_name = "mem_static_boot_address_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static STATIC_BOOT_ADDRESS_METADATA: BootAddresses = BootAddresses {
        page_fault_handler: page_fault_handler as *const () as *const c_void,
        // SAFETY: Permanent owned handler storage, field0 has the exact Cpayload.
        query_free_handler: unsafe { core::ptr::addr_of!(QUERY_FREE_MEM_HANDLER).cast() },
        // SAFETY: Permanent typed Rust words, no borrow/access when forming address.
        anon_slot: unsafe { core::ptr::addr_of_mut!(ANON_ON_DEMAND) },
        xpmem_slot: unsafe { core::ptr::addr_of_mut!(XPMEM_PAGE_IN_REMOTE_ON_ATTACH) },
        hugetlbfs_slot: core::ptr::null_mut(),
    };

    #[export_name = "mem_query_free_nodes"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static QUERY_FREE_NODES: ImmutableAddress<MemNumaNode> = ImmutableAddress(
        // SAFETY: Permanent owned node array, exact first-element address only.
        unsafe { core::ptr::addr_of_mut!(MEMORY_NODES).cast() },
    );

    #[export_name = "mem_vmap_allocator_slot"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static VMAP_ALLOCATOR_SLOT: ImmutableAddress<*mut crate::page_alloc::IhkPageAllocatorDesc> =
        ImmutableAddress(
            // SAFETY: Permanent mutable pointer word, no pointee read or new owner.
            unsafe { core::ptr::addr_of_mut!(VMAP_ALLOCATOR) },
        );

    #[export_name = "mem_numa_sysfs_registration_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static NUMA_SYSFS_REGISTRATION_METADATA: MemNumaSysfsRegistrationMetadata =
        MemNumaSysfsRegistrationMetadata {
            // SAFETY: Both registered table and nodes remain permanently owned.
            ops: unsafe { core::ptr::addr_of_mut!(NUMA_SYSFS_MEMINFO) },
            nodes: unsafe { core::ptr::addr_of_mut!(MEMORY_NODES).cast() },
        };

    #[export_name = "mem_sbox_access_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static SBOX_ACCESS_METADATA: MemSboxAccessMetadata = MemSboxAccessMetadata {
        attached: 0,
        base_slot: core::ptr::null_mut(),
    };

    const _: () = {
        use core::mem::{align_of, offset_of, size_of};
        assert!(size_of::<InterruptHandler>() == 32 && align_of::<InterruptHandler>() == 8);
        assert!(offset_of!(InterruptHandler, list) == 0);
        assert!(offset_of!(InterruptHandler, func) == 16);
        assert!(offset_of!(InterruptHandler, private) == 24);
        assert!(size_of::<InterruptStorage>() == 32 && align_of::<InterruptStorage>() == 32);
        assert!(offset_of!(InterruptStorage, 0) == 0);
        assert!(size_of::<BootAddresses>() == 40 && align_of::<BootAddresses>() == 8);
        assert!(offset_of!(BootAddresses, query_free_handler) == 8);
        assert!(offset_of!(BootAddresses, anon_slot) == 16);
        assert!(offset_of!(BootAddresses, xpmem_slot) == 24);
        assert!(offset_of!(BootAddresses, hugetlbfs_slot) == 32);
        assert!(size_of::<ImmutableAddress<MemNumaNode>>() == 8);
        assert!(size_of::<MemNumaSysfsRegistrationMetadata>() == 16);
        assert!(size_of::<MemSboxAccessMetadata>() == 16);
    };
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact diagnostic/allocation provenance from successful current80 Cproducer.
// Like accepted F05 data ownership, preserve the captured origin as data: no
// Rust file!/line!, invented numeric addresses, #line or artificial Cpadding.
mod owned_mem_origin_and_core_metadata {
    use super::{CInt, MemCoredumpMetadata, MemNumaDistanceAllocationOrigin};
    use super::MemTrackedRedirectionSource;
    use crate::debug::Ddebug;

    // SAFETY: Immutable scalar configuration plus permanent raw string/record
    // addresses only; no safe dereference or pointee mutability guarantee.
    unsafe impl Sync for MemTrackedRedirectionSource {}

    // SAFETY: Immutable scalar configuration plus permanent raw string/record
    // addresses only; no safe dereference or pointee mutability guarantee.
    unsafe impl Sync for MemNumaDistanceAllocationOrigin {}

    // SAFETY: Immutable scalar configuration plus permanent raw string/record
    // addresses only; no safe dereference or pointee mutability guarantee.
    unsafe impl Sync for MemCoredumpMetadata {}

    static TRACE_FILE: [u8; 209] = [
        47, 104, 111, 109, 101, 47, 104, 111, 108, 100, 101, 110, 47, 109, 99, 107, 101, 114,
        110, 101, 108, 45, 119, 111, 114, 107, 47, 104, 111, 115, 116, 45, 112, 114, 101, 112,
        97, 114, 97, 116, 105, 111, 110, 47, 118, 101, 108, 111, 99, 105, 116, 121, 45, 105,
        110, 116, 101, 114, 118, 101, 110, 116, 105, 111, 110, 45, 50, 48, 50, 54, 49, 48,
        50, 51, 45, 54, 47, 109, 49, 52, 45, 102, 105, 108, 101, 45, 108, 97, 110, 101,
        115, 47, 107, 101, 114, 110, 101, 108, 45, 109, 101, 109, 47, 110, 101, 120, 116, 49,
        51, 45, 113, 117, 97, 108, 105, 102, 105, 101, 100, 45, 99, 111, 114, 101, 45, 99,
        117, 114, 114, 101, 110, 116, 45, 112, 114, 111, 100, 117, 99, 116, 105, 111, 110, 45,
        112, 114, 111, 112, 111, 115, 97, 108, 45, 49, 47, 99, 97, 110, 111, 110, 105, 99,
        97, 108, 56, 48, 45, 70, 48, 53, 45, 99, 108, 111, 115, 117, 114, 101, 45, 114,
        101, 102, 114, 101, 115, 104, 45, 49, 47, 115, 111, 117, 114, 99, 101, 47, 107, 101,
        114, 110, 101, 108, 47, 109, 101, 109, 46, 99, 0,
    ];

    #[export_name = "page_hash_alloc_file"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static PAGE_HASH_ALLOC_FILE: [u8; 209] = TRACE_FILE;

    #[export_name = "page_hash_alloc_line"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static PAGE_HASH_ALLOC_LINE: CInt = 5819;

    #[export_name = "mem_tracked_alloc_redirection_source"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static MEM_TRACKED_ALLOC_REDIRECTION_SOURCE: MemTrackedRedirectionSource = MemTrackedRedirectionSource {
        file: TRACE_FILE.as_ptr().cast(),
        line: 7215,
    };

    #[export_name = "mem_tracked_free_redirection_source"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static MEM_TRACKED_FREE_REDIRECTION_SOURCE: MemTrackedRedirectionSource = MemTrackedRedirectionSource {
        file: TRACE_FILE.as_ptr().cast(),
        line: 7226,
    };

    #[export_name = "mem_cache_alloc_redirection_source"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static MEM_CACHE_ALLOC_REDIRECTION_SOURCE: MemTrackedRedirectionSource = MemTrackedRedirectionSource {
        file: TRACE_FILE.as_ptr().cast(),
        line: 7357,
    };

    #[export_name = "mem_numa_distance_allocation_origin"]
    #[link_section = ".rodata.mem_owned_metadata"]
    static MEM_NUMA_DISTANCE_ALLOCATION_ORIGIN: MemNumaDistanceAllocationOrigin = MemNumaDistanceAllocationOrigin {
        file: TRACE_FILE.as_ptr().cast(),
        line: 5497,
    };

    unsafe extern "C" {
        #[link_name = "mem_coredump_debug_0"]
        static mut CORE_DEBUG_0: Ddebug;
        #[link_name = "mem_coredump_debug_1"]
        static mut CORE_DEBUG_1: Ddebug;
    }

    #[export_name = "mem_coredump_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static COREDUMP_METADATA: MemCoredumpMetadata = MemCoredumpMetadata {
        core_limit_index: 1,
        busy: -16,
        nomem: -12,
        nowait: 2,
        syscall_number: 999,
        alloc_file: TRACE_FILE.as_ptr().cast_mut().cast(),
        alloc_line: 4329,
        free_file: TRACE_FILE.as_ptr().cast_mut().cast(),
        free_line: 4329,
        // SAFETY: Permanent typed Ddebug owners; form raw addresses only.
        records: [
            unsafe { core::ptr::addr_of_mut!(CORE_DEBUG_0).cast() },
            unsafe { core::ptr::addr_of_mut!(CORE_DEBUG_1).cast() },
        ],
        flags_byte: 27,
    };

    const _: () = {
        use core::mem::{align_of, offset_of, size_of};
        assert!(size_of::<MemTrackedRedirectionSource>() == 16);
        assert!(align_of::<MemTrackedRedirectionSource>() == 8);
        assert!(offset_of!(MemTrackedRedirectionSource, line) == 8);
        assert!(size_of::<MemNumaDistanceAllocationOrigin>() == 16);
        assert!(offset_of!(MemNumaDistanceAllocationOrigin, line) == 8);
        assert!(size_of::<MemCoredumpMetadata>() == 88);
        assert!(align_of::<MemCoredumpMetadata>() == 8);
        assert!(offset_of!(MemCoredumpMetadata, alloc_file) == 32);
        assert!(offset_of!(MemCoredumpMetadata, alloc_line) == 40);
        assert!(offset_of!(MemCoredumpMetadata, free_file) == 48);
        assert!(offset_of!(MemCoredumpMetadata, free_line) == 56);
        assert!(offset_of!(MemCoredumpMetadata, records) == 64);
        assert!(offset_of!(MemCoredumpMetadata, flags_byte) == 80);
    };
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Defining immutable callback/configuration data only; no function, getter,
// constructor, control-flow effect, ownership transfer or callback replacement.
mod owned_mem_callback_configuration {
    use super::*;
    use crate::debug::Ddebug;

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemLowlevelKmallocMetadata {}

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemRusageEntryMetadata {}

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemRegisterKmallocMetadata {}

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemDistanceEntryMetadata {}

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemNumaInitializationMetadata {}

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemPageFaultEntryMetadata {}

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemTlbHandlerProfileMetadata {}

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemQueryFreeInterruptMetadata {}

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemWholeFreeMetadata {}

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemWholeAllocationMetadata {}

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemRemainingAllocPolicyMetadata {}

    // SAFETY: This exact immutable repr(C) container holds scalar configuration,
    // code pointers and permanent raw storage addresses. No safe dereference or
    // pointee Sync/ownership promise is exposed; existing callback duties remain.
    unsafe impl Sync for MemAllocationLogMetadata {}

    unsafe extern "C" {
        // Exact original public C declaration views. These bind the existing
        // unique Rust producers; differing private Rust pointer types are not a
        // new ABI, casted call, runtime wrapper or duplicated implementation.
        #[link_name = "ihk_mc_get_cpu_info"]
        fn ORIGINAL_CPU_INFO() -> *mut IhkCpuInfo;
        #[link_name = "mem_numa_list_allocator_bridge"]
        fn ORIGINAL_LIST_ALLOCATOR(allocator: *mut c_void, node: *mut MemNumaNode);
        // Same allocator symbol viewed through its genuine original C prototype.
        // The allocated node-distance storage and ownership remain unchanged.
        #[link_name = "mem_numa_distances_alloc_bridge"]
        fn ORIGINAL_NUMA_DISTANCES_ALLOC(npages: CInt, flag: CULong) -> *mut MemNodeDistance;

        #[link_name = "allocator"]
        static mut ALLOCATOR: IhkMcPaOps;
        #[link_name = "memory_nodes"]
        static mut MEMORY_NODES: [MemNumaNode; 512];
        #[link_name = "mem_page_fault_log_count"]
        static mut PAGE_FAULT_LOG_COUNT: CInt;
        #[link_name = "mem_page_fault_log_pid"]
        static mut PAGE_FAULT_LOG_PID: CInt;

        // Exact original public C ABI declarations bind existing unique providers,
        // never new shims. profile's unsigned C enum carries only the same valid
        // positive event4000/4001/4007 values to the existing Rust CInt producer.
        #[link_name = "virt_to_phys"]
        fn ORIGINAL_VIRT_TO_PHYS(address: *mut c_void) -> CULong;
        #[link_name = "ihk_mc_get_numa_distance"]
        fn ORIGINAL_NUMA_DISTANCE(first: CInt, second: CInt) -> CInt;
        #[link_name = "profile_event_add"]
        fn ORIGINAL_PROFILE_EVENT_ADD(event: u32, clocks: u64);
        #[link_name = "mem_page_fault_debug_0"]
        static mut RECORD_0: Ddebug;
        #[link_name = "mem_page_fault_debug_2"]
        static mut RECORD_1: Ddebug;
        #[link_name = "mem_page_fault_debug_3"]
        static mut RECORD_2: Ddebug;
        #[link_name = "mem_allocation_log_record_0"]
        static mut RECORD_3: Ddebug;
        #[link_name = "mem_allocation_log_record_1"]
        static mut RECORD_4: Ddebug;
        #[link_name = "mem_allocation_log_record_2"]
        static mut RECORD_5: Ddebug;
        #[link_name = "mem_allocation_log_record_3"]
        static mut RECORD_6: Ddebug;
        #[link_name = "mem_allocation_log_record_4"]
        static mut RECORD_7: Ddebug;
        #[link_name = "mem_allocation_log_record_6"]
        static mut RECORD_8: Ddebug;
    }

    #[export_name = "mem_lowlevel_kmalloc_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_LOWLEVEL_KMALLOC_METADATA: MemLowlevelKmallocMetadata = MemLowlevelKmallocMetadata {
        remote_lock_offset: offset_of!(CpuLocalVar, remote_free_list_lock) as CULong,
        remote_list_offset: offset_of!(CpuLocalVar, remote_free_list) as CULong,
        irq_save: Some(mem_kmalloc_irq_save_bridge),
        irq_restore: Some(mem_kmalloc_irq_restore_bridge),
        alloc_pages: Some(mem_kmalloc_alloc_pages_bridge),
        get_cpu_local: Some(mem_kmalloc_get_cpu_local_var_bridge),
        remote_lock: Some(mem_kmalloc_remote_lock_bridge),
        remote_unlock: Some(mem_kmalloc_remote_unlock_bridge),
        corruption: Some(mem_kmalloc_corruption_bridge),
    };

    #[export_name = "mem_rusage_entry_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_RUSAGE_ENTRY_METADATA: MemRusageEntryMetadata = MemRusageEntryMetadata {
        state_bytes: size_of::<RusageGlobal>() as CULong,
        cpu_info: Some(ORIGINAL_CPU_INFO),
        nr_nodes: Some(ihk_mc_get_nr_numa_nodes),
        ns_per_tsc: Some(crate::x86_setup::ihk_mc_get_ns_per_tsc),
        virt_to_phys: Some(ORIGINAL_VIRT_TO_PHYS),
        set_rusage: Some(crate::x86_setup::ihk_set_rusage),
        panic_fn: Some(mem_rusage_init_panic_bridge),
        log: Some(mem_rusage_init_log_bridge),
    };

    #[export_name = "mem_register_kmalloc_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_REGISTER_KMALLOC_METADATA: MemRegisterKmallocMetadata = MemRegisterKmallocMetadata {
        // SAFETY: Permanent typed allocator table; form its address without access.
        allocator: unsafe { core::ptr::addr_of_mut!(ALLOCATOR) },
        debug_alloc: Some(__kmalloc),
        debug_free: Some(__kfree),
        base_alloc: Some(___kmalloc),
        base_free: Some(___kfree),
    };

    #[export_name = "mem_distance_entry_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_DISTANCE_ENTRY_METADATA: MemDistanceEntryMetadata = MemDistanceEntryMetadata {
        nr_nodes: Some(ihk_mc_get_nr_numa_nodes),
        alloc: Some(ORIGINAL_NUMA_DISTANCES_ALLOC),
        distance: Some(ORIGINAL_NUMA_DISTANCE),
        alloc_fail: Some(mem_numa_distances_alloc_fail_log_bridge),
        log: Some(mem_numa_distances_log_bridge),
    };

    #[export_name = "mem_numa_initialization_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_NUMA_INITIALIZATION_METADATA: MemNumaInitializationMetadata = MemNumaInitializationMetadata {
        // SAFETY: Same permanent typed node array; no borrow or initialization here.
        nodes: unsafe { core::ptr::addr_of_mut!(MEMORY_NODES).cast() },
        rbtree_allocator: 1,
        get_node_info: mem_numa_get_node_info_bridge,
        get_chunk: ihk_mc_get_memory_chunk,
        init_node: mem_numa_node_init_bridge,
        add_free: mem_numa_add_free_pages_bridge,
        init_allocator: crate::page_alloc::mem_numa_page_allocator_init_bridge,
        list_allocator: ORIGINAL_LIST_ALLOCATOR,
        count_pages: mem_numa_pagealloc_count_bridge,
        add_total: mem_numa_rusage_total_add_bridge,
        log: mem_numa_init_log_bridge,
        panic_fn: mem_numa_panic_bridge,
    };

    #[export_name = "mem_page_fault_entry_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_PAGE_FAULT_ENTRY_METADATA: MemPageFaultEntryMetadata = MemPageFaultEntryMetadata {
        // SAFETY: Same permanent CInt diagnostic words, no load/store or atomic change.
        log_count: unsafe { core::ptr::addr_of_mut!(PAGE_FAULT_LOG_COUNT) },
        log_pid: unsafe { core::ptr::addr_of_mut!(PAGE_FAULT_LOG_PID) },
        page_size: PAGE_SIZE,
        kernel_start: 0xffff_ffff_fe80_0000,
        pf_user: 4,
        invalid: -22,
        canceled: -125,
        range_error: -34,
        busy: -16,
        sigsegv: 11,
        sigbus: 7,
        sigstop: 19,
        map_error: 1,
        access_error: 2,
        bus_address_error: 2,
        time_u2k: 1,
        time_k2kin: 2,
        time_k2u: 0,
        time_k2kout: 3,
        tofu: 0,
        fugaku_debug: 0,
        tofu_attr: 3,
        // SAFETY: Permanent real descriptors; absent TOFU record stays exactly NULL.
        records: [
            unsafe { core::ptr::addr_of_mut!(RECORD_0).cast() },
            core::ptr::null_mut(),
            unsafe { core::ptr::addr_of_mut!(RECORD_1).cast() },
            unsafe { core::ptr::addr_of_mut!(RECORD_2).cast() },
        ],
        flags_byte: 27,
        unhandled: unhandled_page_fault,
        linux_resolve: None,
        linux_pgt: None,
        clear_kernel_range: None,
        do_kill: None,
        profile_add: Some(ORIGINAL_PROFILE_EVENT_ADD),
        profile_event: 4001,
    };

    #[export_name = "mem_tlb_handler_profile_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_TLB_HANDLER_PROFILE_METADATA: MemTlbHandlerProfileMetadata = MemTlbHandlerProfileMetadata {
        event: 4000,
        add: Some(ORIGINAL_PROFILE_EVENT_ADD),
    };

    #[export_name = "mem_query_free_interrupt_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_QUERY_FREE_INTERRUPT_METADATA: MemQueryFreeInterruptMetadata = MemQueryFreeInterruptMetadata {
        fugaku_panic: 0,
        attached_mic: 0,
        sbox_scratch0: 0,
        sbox_scratch1: 0,
        nr_nodes: Some(ihk_mc_get_nr_numa_nodes),
        node_pages: Some(mem_query_free_node_pages_bridge),
        total_log: Some(mem_query_free_total_log_bridge),
        panic_fn: Some(mem_query_free_panic_bridge),
        find_command_line: Some(find_command_line),
        kmalloc_memcheck_fn: Some(mem_query_free_kmalloc_memcheck_bridge),
        pagealloc_memcheck_fn: Some(pagealloc_memcheck),
        page_hash_count: Some(page_hash_count_pages),
        page_hash_log: Some(mem_query_free_page_hash_log_bridge),
        sbox_write: Some(mem_query_free_sbox_write_bridge),
    };

    #[export_name = "mem_whole_free_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_WHOLE_FREE_METADATA: MemWholeFreeMetadata = MemWholeFreeMetadata {
        pending_pages: Some(mem_pending_free_pages_bridge),
        virt_to_phys: Some(mem_virt_to_phys_bridge),
        phys_to_page: Some(mem_phys_to_page_bridge),
        free_in_allocator: Some(mem_free_in_allocator_bridge),
        warn: Some(mem_pending_free_warn_bridge),
        free_body: Some(mem_mckernel_free_pages_body_result),
    };

    #[export_name = "mem_whole_allocation_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_WHOLE_ALLOCATION_METADATA: MemWholeAllocationMetadata = MemWholeAllocationMetadata {
        nr_nodes: Some(ihk_mc_get_nr_numa_nodes),
        current_vm: Some(mem_current_vm_bridge),
        range_policy_search: Some(mem_range_policy_search_bridge),
        lookup_memory_range: Some(mem_lookup_memory_range_bridge),
        range_is_shm: Some(mem_range_is_shm_bridge),
        range_policy_fields: Some(mem_range_policy_fields_bridge),
        vm_policy_fields: Some(mem_vm_policy_fields_bridge),
        current_numa: Some(mem_current_numa_id_bridge),
        alloc_policy: Some(mem_mckernel_alloc_policy_bridge),
    };

    #[export_name = "mem_remaining_alloc_policy_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_REMAINING_ALLOC_POLICY_METADATA: MemRemainingAllocPolicyMetadata = MemRemainingAllocPolicyMetadata {
        try_alloc: Some(mem_try_alloc_node_bridge),
        rusage_add: Some(mem_rusage_page_add_bridge),
        phys_to_virt: Some(mem_phys_to_virt_bridge),
        log: Some(mem_mckernel_alloc_log_bridge),
    };

    #[export_name = "mem_allocation_log_metadata"]
    #[link_section = ".rodata.mem_owned_metadata"]
    #[used]
    static MEM_ALLOCATION_LOG_METADATA: MemAllocationLogMetadata = MemAllocationLogMetadata {
        // SAFETY: Same permanent records/ordering; absent FUGAKU record stays NULL.
        records: [
            unsafe { core::ptr::addr_of_mut!(RECORD_3).cast() },
            unsafe { core::ptr::addr_of_mut!(RECORD_4).cast() },
            unsafe { core::ptr::addr_of_mut!(RECORD_5).cast() },
            unsafe { core::ptr::addr_of_mut!(RECORD_6).cast() },
            unsafe { core::ptr::addr_of_mut!(RECORD_7).cast() },
            core::ptr::null_mut(),
            unsafe { core::ptr::addr_of_mut!(RECORD_8).cast() },
        ],
        flags_byte: 27,
        profile_add: Some(ORIGINAL_PROFILE_EVENT_ADD),
        profile_event: 4007,
        fugaku: 0,
    };

    const _: () = {
        assert!(size_of::<MemLowlevelKmallocMetadata>() == 72);
        assert!(size_of::<MemRusageEntryMetadata>() == 64);
        assert!(size_of::<MemRegisterKmallocMetadata>() == 40);
        assert!(size_of::<MemDistanceEntryMetadata>() == 40);
        assert!(size_of::<MemNumaInitializationMetadata>() == 96);
        assert!(size_of::<MemPageFaultEntryMetadata>() == 208);
        assert!(offset_of!(MemPageFaultEntryMetadata, records) == 112);
        assert!(offset_of!(MemPageFaultEntryMetadata, unhandled) == 152);
        assert!(offset_of!(MemPageFaultEntryMetadata, profile_add) == 192);
        assert!(size_of::<MemTlbHandlerProfileMetadata>() == 16);
        assert!(size_of::<MemQueryFreeInterruptMetadata>() == 96);
        assert!(size_of::<MemWholeFreeMetadata>() == 48);
        assert!(size_of::<MemWholeAllocationMetadata>() == 72);
        assert!(size_of::<MemRemainingAllocPolicyMetadata>() == 32);
        assert!(size_of::<MemAllocationLogMetadata>() == 80);
    };
}
