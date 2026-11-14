//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! PRIVATE, UNSELECTED current-header DATA provider boundary.
//!
//! This PRIVATE paired candidate uses only the existing private crate-root
//! overlay. One unsafe C-ABI helper writes the original twelve kernel-owned
//! UtiInfo fields; it is not a util_thread body, constructor or default selector.
//! The measured UtiInfo/UtiKattr types remain the separate DATA candidate.
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

use core::ptr::addr_of_mut;
use crate::abi::Thread;

/// Initialize only the original twelve kernel-owned UtiInfo fields.
///
/// # Safety
/// `info` must be the caller's successful, aligned UtiInfo allocation, writable
/// for these individual fields. It need not contain an initialized UtiInfo.
/// `thread` is the original C caller's captured live Thread pointer; the caller
/// retains its current CPU/CLS/thread/global exclusion and all pointee lifetimes.
/// Current-CPU lookups and provider reads/calls have exactly their original order.
/// Host-owned pointer fields and padding remain untouched. This function creates
/// no whole-object reference/value, performs no allocation or publication, and
/// supplies no host-completion/ACK/refill/free permission or new error path.
#[no_mangle]
pub unsafe extern "C" fn f03_uti_info_data_initialize_v1(
    info: *mut UtiInfo,
    thread: *mut Thread,
) {
    // 1. Fresh current-CPU current POINTER VALUE, kept as kernel VA bits.
    let clv_thread = unsafe { (EXISTING_DATA_PROVIDERS.current_cpu_local)() };
    let current_thread = unsafe { addr_of!((*clv_thread).current).read() };
    unsafe { addr_of_mut!((*info).thread_va).write(current_thread as CULong) };

    // 2. Fresh current-CPU response POINTER VALUE, not its pointer slot.
    let clv_response = unsafe { (EXISTING_DATA_PROVIDERS.current_cpu_local)() };
    let response = unsafe { addr_of!((*clv_response).uti_futex_resp).read() };
    let response_pa = unsafe { (EXISTING_DATA_PROVIDERS.virtual_to_physical)(response) };
    unsafe { addr_of_mut!((*info).uti_futex_resp_pa).write(response_pa) };

    // 3. Fresh current-CPU channel POINTER VALUE, not its pointer slot.
    let clv_channel = unsafe { (EXISTING_DATA_PROVIDERS.current_cpu_local)() };
    let channel = unsafe { addr_of!((*clv_channel).ikc2linux).read() };
    let channel_pa = unsafe { (EXISTING_DATA_PROVIDERS.virtual_to_physical)(channel) };
    unsafe { addr_of_mut!((*info).ikc2linux_pa).write(channel_pa) };

    // 4. C-int TID from the initially captured Thread.
    let tid = unsafe { addr_of!((*thread).tid).read() };
    unsafe { addr_of_mut!((*info).tid).write(tid) };

    // 5. Existing actual processor-ID provider, exactly once.
    let cpu = unsafe { (EXISTING_DATA_PROVIDERS.processor_id)() };
    unsafe { addr_of_mut!((*info).cpu).write(cpu) };

    // 6..8. Physical ADDRESSES of captured Thread fields.
    let status_pa = unsafe {
        (EXISTING_DATA_PROVIDERS.virtual_to_physical)(addr_of_mut!((*thread).status) as *mut c_void)
    };
    unsafe { addr_of_mut!((*info).status_pa).write(status_pa) };
    let spin_sleep_lock_pa = unsafe {
        (EXISTING_DATA_PROVIDERS.virtual_to_physical)(addr_of_mut!((*thread).spin_sleep_lock) as *mut c_void)
    };
    unsafe { addr_of_mut!((*info).spin_sleep_lock_pa).write(spin_sleep_lock_pa) };
    let spin_sleep_pa = unsafe {
        (EXISTING_DATA_PROVIDERS.virtual_to_physical)(addr_of_mut!((*thread).spin_sleep) as *mut c_void)
    };
    unsafe { addr_of_mut!((*info).spin_sleep_pa).write(spin_sleep_pa) };

    // 9. Captured Thread.vm POINTER VALUE, not the Thread.vm slot address.
    let vm = unsafe { addr_of!((*thread).vm).read() };
    let vm_pa = unsafe { (EXISTING_DATA_PROVIDERS.virtual_to_physical)(vm as *mut c_void) };
    unsafe { addr_of_mut!((*info).vm_pa).write(vm_pa) };

    // 10. Physical ADDRESS of the captured Thread's embedded futex_q.
    let futex_q_pa = unsafe {
        (EXISTING_DATA_PROVIDERS.virtual_to_physical)(addr_of_mut!((*thread).futex_q) as *mut c_void)
    };
    unsafe { addr_of_mut!((*info).futex_q_pa).write(futex_q_pa) };

    // 11. Existing ordinary C-int DATA read; no Atomic/volatile/Sync change.
    let mc_idle_halt = unsafe { EXISTING_DATA_PROVIDERS.idle_halt_storage.read() };
    unsafe { addr_of_mut!((*info).mc_idle_halt).write(mc_idle_halt) };

    // 12. Physical value of the POINTER RETURNED by the existing queue getter.
    let queues = unsafe { (EXISTING_DATA_PROVIDERS.futex_queues)() };
    let futex_queue_pa = unsafe {
        (EXISTING_DATA_PROVIDERS.virtual_to_physical)(queues as *mut c_void)
    };
    unsafe { addr_of_mut!((*info).futex_queue_pa).write(futex_queue_pa) };
}
