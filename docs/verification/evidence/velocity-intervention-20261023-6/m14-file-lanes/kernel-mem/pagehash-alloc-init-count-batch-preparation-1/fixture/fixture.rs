#![no_std]
#![allow(dead_code)]
#[path="/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_abi.rs"]mod abi;
#[path="/home/holden/mckernel/kernel/rust/spinlock_helpers.rs"]mod spinlock_helpers;
#[path="/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/pagehash-alloc-init-count-batch-preparation-1/candidate/kernel/rust/page_helpers.rs"]mod page_helpers;
use core::ffi::c_void;
use abi::{CInt,CULong,SizeT};
unsafe extern "C" {fn kmalloc_tracked(size:CInt,flag:CULong,file:*mut i8,line:CInt)->*mut c_void;}
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
