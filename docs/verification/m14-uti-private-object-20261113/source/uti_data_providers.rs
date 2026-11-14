//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! PRIVATE, UNSELECTED current-header DATA provider boundary.
//!
//! This file is deliberately absent from lib.rs and every build/selection cfg.
//! It defines no function, exported symbol, constructor or initialized UTI
//! instance. The prerequisite UtiInfo/UtiKattr types are the separate measured
//! private DATA candidate; they are not redefined here.
//!
//! Layout metadata is inert: neither a field offset nor a provider address
//! grants pointee ownership, a reference/pin, host completion or an ACK.

use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of};
use core::ptr::addr_of;

use crate::abi::{
    CInt, CULong, CpuLocalVar, FutexHashBucket, SizeT, UtiAttr, UtiCtx,
    UtiCtxRefill, UtiInfo, UtiKattr, X86UserContext,
};

// These metadata records have only private Rust field access. They are not a
// replacement C layout producer or a new ABI passed to any existing caller.
pub(crate) struct UtiInfoLayout {
    pub size: SizeT,
    pub align: SizeT,
    pub thread_va: SizeT,
    pub uti_futex_resp: SizeT,
    pub ikc2linux: SizeT,
    pub uti_futex_resp_pa: SizeT,
    pub ikc2linux_pa: SizeT,
    pub tid: SizeT,
    pub cpu: SizeT,
    pub status: SizeT,
    pub spin_sleep_lock: SizeT,
    pub spin_sleep: SizeT,
    pub vm: SizeT,
    pub futex_q: SizeT,
    pub status_pa: SizeT,
    pub spin_sleep_lock_pa: SizeT,
    pub spin_sleep_pa: SizeT,
    pub vm_pa: SizeT,
    pub futex_q_pa: SizeT,
    pub mc_idle_halt: SizeT,
    pub futex_queue: SizeT,
    pub os: SizeT,
    pub futex_queue_pa: SizeT,
}

pub(crate) struct UtiKattrLayout {
    pub size: SizeT,
    pub align: SizeT,
    pub parent_cpuid: SizeT,
    pub attr: SizeT,
}

pub(crate) struct UtiAttrLayout {
    pub size: SizeT,
    pub align: SizeT,
    pub numa_set: SizeT,
    pub flags: SizeT,
}

pub(crate) struct UtiCtxLayout {
    pub size: SizeT,
    pub align: SizeT,
    pub ctx: SizeT,
    pub uti_refill_tid: SizeT,
}

pub(crate) struct UtiDataLayout {
    pub info: UtiInfoLayout,
    pub kattr: UtiKattrLayout,
    pub attr: UtiAttrLayout,
    pub context: UtiCtxLayout,
}

// Use the genuine current types. No historical numeric offset table, mirrored
// representation, legacy f03_util_thread_layout_v1 or new ABI assertion exists.
// The same expressions already produced the matching actual ABI35 DATA words.
pub(crate) const CURRENT_HEADER_LAYOUT: UtiDataLayout = UtiDataLayout {
    info: UtiInfoLayout {
        size: size_of::<UtiInfo>(),
        align: align_of::<UtiInfo>(),
        thread_va: offset_of!(UtiInfo, thread_va),
        uti_futex_resp: offset_of!(UtiInfo, uti_futex_resp),
        ikc2linux: offset_of!(UtiInfo, ikc2linux),
        uti_futex_resp_pa: offset_of!(UtiInfo, uti_futex_resp_pa),
        ikc2linux_pa: offset_of!(UtiInfo, ikc2linux_pa),
        tid: offset_of!(UtiInfo, tid),
        cpu: offset_of!(UtiInfo, cpu),
        status: offset_of!(UtiInfo, status),
        spin_sleep_lock: offset_of!(UtiInfo, spin_sleep_lock),
        spin_sleep: offset_of!(UtiInfo, spin_sleep),
        vm: offset_of!(UtiInfo, vm),
        futex_q: offset_of!(UtiInfo, futex_q),
        status_pa: offset_of!(UtiInfo, status_pa),
        spin_sleep_lock_pa: offset_of!(UtiInfo, spin_sleep_lock_pa),
        spin_sleep_pa: offset_of!(UtiInfo, spin_sleep_pa),
        vm_pa: offset_of!(UtiInfo, vm_pa),
        futex_q_pa: offset_of!(UtiInfo, futex_q_pa),
        mc_idle_halt: offset_of!(UtiInfo, mc_idle_halt),
        futex_queue: offset_of!(UtiInfo, futex_queue),
        os: offset_of!(UtiInfo, os),
        futex_queue_pa: offset_of!(UtiInfo, futex_queue_pa),
    },
    kattr: UtiKattrLayout {
        size: size_of::<UtiKattr>(),
        align: align_of::<UtiKattr>(),
        parent_cpuid: offset_of!(UtiKattr, parent_cpuid),
        attr: offset_of!(UtiKattr, attr),
    },
    attr: UtiAttrLayout {
        size: size_of::<UtiAttr>(),
        align: align_of::<UtiAttr>(),
        numa_set: offset_of!(UtiAttr, numa_set),
        flags: offset_of!(UtiAttr, flags),
    },
    context: UtiCtxLayout {
        size: size_of::<UtiCtx>(),
        align: align_of::<UtiCtx>(),
        ctx: offset_of!(UtiCtx, ctx),
        uti_refill_tid: offset_of!(UtiCtx, refill)
            + offset_of!(UtiCtxRefill, uti_refill_tid),
    },
};

pub(crate) type CurrentCpuLocal = unsafe extern "C" fn() -> *mut CpuLocalVar;
pub(crate) type AllocateTracked = unsafe extern "C" fn(CInt, CULong, *mut i8, CInt) -> *mut c_void;
pub(crate) type FreeTracked = unsafe extern "C" fn(*mut c_void, *mut i8, CInt);
pub(crate) type SaveUserContext = unsafe extern "C" fn(*mut c_void, *mut X86UserContext);
pub(crate) type VirtualToPhysical = unsafe extern "C" fn(*mut c_void) -> CULong;
pub(crate) type FutexQueues = unsafe extern "C" fn() -> *mut FutexHashBucket;
pub(crate) type ProcessorId = unsafe extern "C" fn() -> CInt;

pub(crate) struct UtiDataProviders {
    pub current_cpu_local: CurrentCpuLocal,
    pub allocate_tracked: AllocateTracked,
    pub free_tracked: FreeTracked,
    pub save_user_context: SaveUserContext,
    pub virtual_to_physical: VirtualToPhysical,
    pub futex_queues: FutexQueues,
    pub processor_id: ProcessorId,
    // Address only; the original caller's exclusion/initialization governs any
    // later plain C-int read. No Atomic/Sync/Send or scalar snapshot is added.
    pub idle_halt_storage: *const CInt,
}

unsafe extern "C" {
    // Existing unique current global, owned by the selected Rust
    // process_global_storage candidate. This declaration creates no storage.
    static mut idle_halt: CInt;
}

// Typed function-pointer assignments bind the actual existing Rust providers,
// without invoking them or introducing a C facade or replacement callback.
// The record deliberately omits uti_desc storage, dispatch/ACK/completion,
// profile reads, termination and legacy debug/origin/constant producers.
pub(crate) const EXISTING_DATA_PROVIDERS: UtiDataProviders = UtiDataProviders {
    current_cpu_local: crate::cls::get_this_cpu_local_var,
    allocate_tracked: crate::mem_helpers::kmalloc_tracked,
    free_tracked: crate::mem_helpers::kfree_tracked,
    save_user_context: crate::syscall_policy::save_uctx,
    virtual_to_physical: crate::x86_memory_helpers::virt_to_phys,
    futex_queues: crate::futex::get_futex_queues,
    processor_id: crate::x86_local::ihk_mc_get_processor_id,
    idle_halt_storage: addr_of!(idle_halt),
};
