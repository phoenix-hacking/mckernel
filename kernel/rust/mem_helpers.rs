use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of};
use core::ptr::{null_mut, write_bytes, write_volatile};
use core::sync::atomic::{AtomicI32, AtomicI64, AtomicPtr, AtomicU64, Ordering};

use crate::abi::{
    AbiListHead, AddressSpace, CInt, CLong, CULong, CpuLocalVar, IhkAtomic, IhkAtomic64,
    IhkCpuInfo, IhkSpinlock, KmallocCacheHeader, KmallocHeader, McsLockNode, Memobj, OffT, Process,
    ProcessVm, RusagePercpu, SizeT, TlbFlushEntry, VmRange, CPU_SET_WORDS, IHK_MAX_NUM_CPUS,
    IHK_MAX_NUM_NUMA_NODES, IHK_MAX_NUM_PGSIZES, PROCESS_HASH_SIZE,
};
use crate::llist::{LListHead, LListNode};
use crate::rbtree::{rb_first_safe, rb_next_safe, RbNode, RbRoot};
use crate::string::{strcmp, strcpy, strlen, strstr};

unsafe extern "C" {
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
    fn mem_num_processors_bridge() -> CInt;
    fn mem_dump_level_bridge() -> CInt;
    fn mem_get_dump_page_set_bridge() -> *mut IhkDumpPageSet;
    fn mem_get_dump_page_bridge() -> *mut IhkDumpPage;
    fn mem_process_hash_lists_bridge() -> *mut AbiListHead;
    fn mem_dump_complete_log_bridge();
    fn mem_dump_free_pages_bridge(node: CInt) -> CULong;
    fn mem_dump_first_free_chunk_bridge(node: CInt) -> *mut c_void;
    fn mem_dump_next_free_chunk_bridge(chunk: *mut c_void) -> *mut c_void;
    fn mem_dump_chunk_addr_bridge(chunk: *mut c_void) -> CULong;
    fn mem_dump_chunk_size_bridge(chunk: *mut c_void) -> CULong;
    fn mem_dump_warn_bridge(
        kind: CInt,
        map_count: CULong,
        map_index: CULong,
        map_start: CULong,
        map_end: CULong,
        page_index: CULong,
    );
    fn visit_pte_range_safe(
        pt: *mut c_void,
        start: *mut c_void,
        end: *mut c_void,
        pgshift: CInt,
        p2align: CInt,
        visitor: Option<MemPteVisitorFn>,
        arg: *mut c_void,
    ) -> CInt;
    fn ihk_mc_get_mem_user_page(
        arg0: *mut c_void,
        pt: *mut c_void,
        ptep: *mut CULong,
        pgaddr: *mut c_void,
        pgshift: CInt,
    ) -> CInt;
    fn get_this_cpu_local_var() -> *mut CpuLocalVar;
    #[allow(clashing_extern_declarations)]
    fn phys_to_page(phys: CULong) -> *mut MemPage;
    fn kprintf(format: *const i8, ...) -> CInt;
    fn kmalloc_cache_alloc_bridge(size: SizeT, flag: CULong) -> *mut c_void;
    fn kmalloc_cache_log(event: CInt, ptr: *mut c_void);
    fn eventfd(type_: CInt);
    fn mem_pagealloc_track_base_alloc_bridge(
        npages: CInt,
        p2align: CInt,
        flag: CULong,
        node: CInt,
        is_user: CInt,
        virt_addr: CULong,
    ) -> *mut c_void;
    fn mem_pagealloc_track_base_free_bridge(ptr: *mut c_void, npages: CInt, is_user: CInt);
    fn mem_pagealloc_track_meta_alloc_bridge(size: CInt, flag: CULong) -> *mut c_void;
    fn mem_pagealloc_track_meta_free_bridge(ptr: *mut c_void);
    fn mem_pagealloc_track_lock_bridge(lock_addr: CULong) -> CULong;
    fn mem_pagealloc_track_unlock_bridge(lock_addr: CULong, irqflags: CULong);
    fn mem_pagealloc_track_noirq_lock_bridge(lock_addr: CULong);
    fn mem_pagealloc_track_noirq_unlock_bridge(lock_addr: CULong);
    fn mem_pagealloc_track_spin_init_bridge(lock_addr: CULong);
    fn mem_pagealloc_track_log_bridge(
        event: CInt,
        ptr: *mut c_void,
        file: *mut i8,
        line: CInt,
        npages: CInt,
    );
    fn mem_pagealloc_invalid_free_bridge(ptr: *mut c_void, file: *mut i8, line: CInt);
    fn mem_pagealloc_invalid_size_bridge(
        ptr: *mut c_void,
        npages: CInt,
        alloc_npages: CInt,
        file: *mut i8,
        line: CInt,
    );
    fn mem_pagealloc_leak_log_bridge(
        event: CInt,
        ptr: *mut c_void,
        file: *mut i8,
        line: CInt,
        size: CInt,
        count: CInt,
        runcount: CInt,
    );
    fn mem_init_allocator_bridge() -> *mut IhkMcPaOps;
    fn mem_init_page_fault_handler_bridge() -> CULong;
    fn mem_init_query_free_handler_bridge() -> CULong;
    fn mem_init_anon_on_demand_bridge() -> *mut CInt;
    fn mem_init_xpmem_remote_bridge() -> *mut CInt;
    fn mem_init_hugetlbfs_on_demand_bridge() -> *mut CInt;
    fn mem_monitor_init_bridge();
    fn mem_rusage_init_bridge();
    fn mem_numa_init_bridge();
    fn mem_set_page_fault_handler_bridge(handler: CULong);
    fn mem_get_vector_bridge(type_: CInt) -> CInt;
    fn mem_register_interrupt_handler_bridge(vector: CInt, handler: CULong) -> CInt;
    fn mem_page_init_bridge();
    fn mem_virtual_allocator_init_bridge();
    fn mem_find_command_line_bridge(name: *mut i8) -> *mut i8;
    fn mem_numa_distances_init_bridge();
    fn mem_init_log_bridge(event: CInt);
    fn mem_kmalloc_track_base_alloc_bridge(size: CInt, flag: CULong) -> *mut c_void;
    fn mem_kmalloc_track_base_free_bridge(ptr: *mut c_void);
    fn mem_kmalloc_track_lock_bridge(lock_addr: CULong) -> CULong;
    fn mem_kmalloc_track_unlock_bridge(lock_addr: CULong, irqflags: CULong);
    fn mem_kmalloc_track_spin_init_bridge(lock_addr: CULong);
    fn mem_kmalloc_track_log_bridge(
        event: CInt,
        ptr: *mut c_void,
        file: *mut i8,
        line: CInt,
        size: CInt,
    );
    fn mem_kmalloc_invalid_free_bridge(ptr: *mut c_void, file: *mut i8, line: CInt);
    fn mem_kmalloc_leak_log_bridge(
        event: CInt,
        ptr: *mut c_void,
        file: *mut i8,
        line: CInt,
        size: CInt,
        count: CInt,
        runcount: CInt,
    );
    fn mem_pending_free_pages_bridge() -> *mut AbiListHead;
    fn mem_begin_free_pages_pending_panic_bridge();
    fn mem_pending_free_bridge(phys: CULong, npages: CInt, is_user: CInt);
    fn mem_finish_free_pages_pending_panic_bridge();
    fn mem_vmap_allocator_bridge() -> *mut c_void;
    fn mem_vmap_alloc_bridge(desc: *mut c_void, npages: CInt, p2align: CInt) -> CULong;
    fn mem_vmap_free_bridge(desc: *mut c_void, address: CULong, npages: CInt);
    fn mem_pt_set_page_bridge(pt: *mut c_void, virt: *mut c_void, phys: CULong, attr: CInt)
        -> CInt;
    fn mem_pt_clear_page_bridge(pt: *mut c_void, virt: *mut c_void) -> CInt;
    fn mem_flush_tlb_single_bridge(addr: CULong);
    fn mem_barrier_bridge();

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
type MemPtSetPageFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CInt) -> CInt;
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
    attr: CInt,
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
pub unsafe extern "C" fn ihk_mc_map_virtual(phys: CULong, npages: CInt, attr: CInt) -> *mut c_void {
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
