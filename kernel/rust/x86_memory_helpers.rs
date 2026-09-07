use core::ffi::c_void;
use core::ptr::{copy_nonoverlapping, read_volatile, write_bytes, write_volatile};
use core::sync::atomic::{AtomicU64, Ordering};

use crate::abi::{
    CInt, CLong, CULong, CpuLocalVar, IkcScdPacket, IkcScdPacketTraditional, ProcessVm, SizeT,
    Thread,
};

const PTATTR_ACTIVE: CULong = 0x01;
const PTATTR_WRITABLE: CULong = 0x02;
const PTATTR_LARGEPAGE: CULong = 0x80;
const PTATTR_DIRTY: CULong = 0x40;
const PTATTR_UNCACHABLE: CULong = 0x10000;
const PTATTR_FOR_USER: CULong = 0x20000;
const PTATTR_WRITE_COMBINED: CULong = 0x40000;
const PTATTR_NO_EXECUTE: CULong = 0x8000000000000000;
const VR_PRIVATE: CULong = 0x2000;
const PF_PROT: CULong = 1;
const PF_WRITE: CULong = 1 << 1;
const PF_USER: CULong = 1 << 2;
const PF_PATCH: CULong = 1 << 29;
const PF_POPULATE: CULong = 1 << 30;

const EINVAL: i32 = 22;
const ENOMEM: i32 = 12;
const ENOTSUPP: i32 = 524;
const ENOENT: i32 = 2;
const EFAULT: i32 = 14;
const EBUSY: i32 = 16;
const E2BIG: i32 = 7;

const PTL4_SHIFT: i32 = 39;
const PTL1_SHIFT: i32 = 12;
const PTL2_SHIFT: i32 = 21;
const PTL3_SHIFT: i32 = 30;
const LARGE_PAGE_SHIFT: i32 = 21;

const PTL1_SIZE: CULong = 1 << PTL1_SHIFT;
const PTL2_SIZE: CULong = 1 << PTL2_SHIFT;
const PTL3_SIZE: CULong = 1 << PTL3_SHIFT;
const PTL4_SIZE: CULong = 1 << PTL4_SHIFT;
const PAGE_MASK: CULong = !(PTL1_SIZE - 1);
const LARGE_PAGE_MASK: CULong = !((1 << LARGE_PAGE_SHIFT) - 1);
const AP_TRAMPOLINE_SIZE: CULong = 0x2000;
const PT_PHYSMASK: CULong = (((1 as CULong) << 52) - 1) & PAGE_MASK;
const KERNEL_BASE: CULong = 0xffff000000000000;
const MAP_ST_START: CULong = 0xffff800000000000;
const MAP_FIXED_START: CULong = 0xffff860000000000;
const PM_STATUS_OFFSET: u32 = 61;
const PM_PSHIFT_OFFSET: u32 = 55;
const PM_PFRAME_MASK: CULong = ((1 as CULong) << PM_PSHIFT_OFFSET) - 1;
const PM_PRESENT: CULong = 4 << PM_STATUS_OFFSET;

const PFLX_PWT: CULong = 0x08;
const PFLX_PCD: CULong = 0x10;
const PFL2_PRESENT: CULong = 0x01;
const PFL2_KERN_ATTR: CULong = 0x03;
const PFL2_SIZE: CULong = 0x80;
const PFL2_PDIR_ATTR: CULong = 0x07;
const PFL3_PDIR_ATTR: CULong = 0x07;
const PFL4_PDIR_ATTR: CULong = 0x07;
const PFL_FILEOFF: CULong = 1 << 11;
const PT_ENTRIES: CULong = 512;
const PTE_NULL: CULong = 0;
const NOPHYS: CULong = !0;
const IHK_MC_AP_CRITICAL: CInt = 0x000001;
const IHK_MC_AP_NOWAIT: CInt = 0x000002;
const IHK_MC_PT_FIRST_LEVEL: CInt = 0;

const X86_VISIT_PTE_SKIP: i32 = 0;
const X86_VISIT_PTE_DIRECT: i32 = 1;
const X86_VISIT_PTE_ALLOC_AND_WALK: i32 = 2;
const X86_VISIT_PTE_WALK: i32 = 3;
const X86_VISIT_PTE_SPLIT_ERROR: i32 = 4;
const X86_VISIT_PTE_LOG_SPLIT: CInt = 1;

const X86_CLEAR_RANGE_SKIP: i32 = 0;
const X86_CLEAR_RANGE_SPLIT_ERROR: i32 = 1;
const X86_CLEAR_RANGE_CLEAR_LARGE: i32 = 2;
const X86_CLEAR_RANGE_WALK: i32 = 3;

const X86_CLEAR_OLD_FLUSH_MEMOBJ: i32 = 0x01;
const X86_CLEAR_OLD_FREE_ANON: i32 = 0x02;
const X86_CLEAR_OLD_XPMEM_KEEP: i32 = 0x04;
const X86_CLEAR_OLD_TRY_UNMAP: i32 = 0x08;
const X86_CLEAR_EFFECT_FLUSH_MEMOBJ: CInt = 1;
const X86_CLEAR_EFFECT_FREE_ANON: CInt = 2;
const X86_CLEAR_EFFECT_XPMEM_KEEP: CInt = 3;
const X86_CLEAR_EFFECT_FREE_UNMAPPED: CInt = 4;
const X86_CLEAR_EFFECT_CHILD_FREE: CInt = 5;
const X86_CLEAR_TOP_LOG_INVALID: CInt = 6;
const X86_CLEAR_TOP_LOG_ALLOC_FAILED: CInt = 7;
const X86_CLEAR_RANGE_LOG_SPLIT: CInt = 8;
const X86_CLEAR_RANGE_LOG_LARGE_PHYS: CInt = 9;

const X86_CHANGE_ATTR_ENOENT: i32 = 0;
const X86_CHANGE_ATTR_APPLY: i32 = 1;
const X86_CHANGE_ATTR_SPLIT_ERROR: i32 = 2;
const X86_CHANGE_ATTR_WALK: i32 = 3;

const X86_SET_RANGE_APPLY: i32 = 0;
const X86_SET_RANGE_ALLOC_AND_WALK: i32 = 1;
const X86_SET_RANGE_MAP_LARGE: i32 = 2;
const X86_SET_RANGE_BUSY: i32 = 3;
const X86_SET_RANGE_WALK: i32 = 4;
const X86_SET_RANGE_LOG_BUSY: CInt = 1;
const X86_SET_RANGE_LOG_ALLOC_FAILED: CInt = 2;
const X86_SET_RANGE_LOG_WALK_FAILED: CInt = 3;
const X86_SET_RANGE_LOG_MAP_LARGE: CInt = 4;
const X86_SET_RANGE_LOG_RSS_ADD: CInt = 5;
const X86_SET_RANGE_LOG_RSS_SKIP: CInt = 6;

const X86_LOOKUP_PTE_MISS: i32 = 0;
const X86_LOOKUP_PTE_WALK: i32 = 1;
const X86_LOOKUP_PTE_HIT: i32 = 2;
const X86_VTOP_MISS: i32 = 0;
const X86_VTOP_WALK: i32 = 1;
const X86_VTOP_HIT: i32 = 2;
const X86_DESTROY_PT_SKIP: i32 = 0;
const X86_DESTROY_PT_DESCEND: i32 = 1;
const X86_PT_DESTROY_PANIC_LEVEL: CInt = 1;
const X86_PT_DESTROY_PANIC_NULL: CInt = 2;
const X86_PT_SET_PTE_LOG_L2_ALIGN: CInt = 1;
const X86_PT_SET_PTE_LOG_L3_ALIGN: CInt = 2;
const X86_PT_SET_PTE_LOG_PAGE_SIZE: CInt = 3;
const X86_SPLIT_LARGE_PAGE_LOG_INVALID_PGSIZE: CInt = 1;
const X86_SPLIT_LARGE_PAGE_LOG_ALLOC_FAILED: CInt = 2;
const X86_SPLIT_LARGE_PAGE_LOG_RSS_ADD: CInt = 3;
const X86_SPLIT_LARGE_PAGE_LOG_RSS_SUB: CInt = 4;
const X86_SPLIT_LARGE_PAGE_LOG_PAGE_UNMAP: CInt = 5;
const X86_PT_SPLIT_LOG_NOT_SPLITABLE: CInt = 1;
const X86_PT_SPLIT_LOG_SPLIT_FAILED: CInt = 2;
const X86_MOVE_ONE_LOG_FILEOFF: CInt = 1;
const X86_MOVE_ONE_LOG_SET_FAILED: CInt = 2;
const X86_VPTEF_SKIP_NULL: CInt = 0x0001;
const X86_USER_COPY_READ: CInt = 0;
const X86_USER_COPY_WRITE: CInt = 1;
const X86_USER_COPY_LOG_RANGE: CInt = 1;
const X86_USER_COPY_LOG_PF: CInt = 2;
const X86_USER_COPY_LOG_VTOP: CInt = 3;
const X86_USER_COPY_LOG_EXTERNAL: CInt = 4;
const X86_USER_COPY_LOG_PATCH_START: CInt = 5;
const X86_USER_COPY_LOG_PATCH_RANGE: CInt = 6;
const X86_USER_COPY_LOG_PATCH_PF: CInt = 7;
const X86_USER_COPY_LOG_PATCH_VTOP: CInt = 8;
const X86_USER_COPY_LOG_PATCH_DONE: CInt = 9;
const X86_INIT_NORMAL_LOG_RANGE: CInt = 1;
const X86_INIT_NORMAL_LOG_SET_FAILED: CInt = 2;
const X86_INIT_TEXT_LOG_LPAGES: CInt = 1;
const X86_INIT_TEXT_LOG_BASE: CInt = 2;
const X86_INIT_LINUX_LOG_FULL: CInt = 1;
const X86_INIT_LINUX_LOG_FULL_RANGE: CInt = 2;
const X86_INIT_LINUX_LOG_FULL_SET_FAILED: CInt = 3;
const X86_INIT_LINUX_LOG_CHUNKS: CInt = 4;
const X86_INIT_LINUX_LOG_NO_CHUNK: CInt = 5;
const X86_INIT_LINUX_LOG_BAD_CHUNK: CInt = 6;
const X86_INIT_LINUX_LOG_CHUNK_RANGE: CInt = 7;
const X86_INIT_LINUX_LOG_CHUNK_SET_FAILED: CInt = 8;
const IHK_MC_GMA_MAP_START: CInt = 0;
const IHK_MC_GMA_MAP_END: CInt = 1;
const X86_INIT_LINUX_FULL_MAP_END: CULong = 0x20000000000;
const VSYSCALL_ADDR: CULong = 0xffffffffff600000;
const SAFE_KERNEL_MAP: &[u8; 16] = b"safe_kernel_map\0";
const X86_ADDR_LOG_KERNEL: CInt = 1;
const X86_ADDR_LOG_STRAIGHT: CInt = 2;
const X86_PT_PRINT_LOG_TABLE: CInt = 1;
const X86_PT_PRINT_LOG_NOT_PRESENT: CInt = 2;
const X86_PT_PRINT_LOG_ENTRY: CInt = 3;
const X86_PT_PRINT_LOG_LARGE: CInt = 4;

unsafe extern "C" {
    fn get_this_cpu_local_var() -> *mut CpuLocalVar;
    fn x86_addr_init_pt_loaded_bridge() -> CInt;
    fn x86_addr_log_bridge(event: CInt, value: CULong);
    fn x86_user_page_fault_bridge(vm: *mut c_void, addr: *mut c_void, reason: CULong) -> CInt;
    fn x86_user_verify_bridge(vm: *mut c_void, addr: *mut c_void, size: CULong) -> CInt;
    fn x86_user_vtop_bridge(pt: *mut c_void, virt: *const c_void, phys: *mut CULong) -> CInt;
    fn x86_user_is_memory_bridge(start: CULong, end: CULong) -> CInt;
    fn x86_user_map_bridge(phys: CULong, nr_pages: CInt, attr: CULong) -> *mut c_void;
    fn x86_user_unmap_bridge(addr: *mut c_void, nr_pages: CInt);
    fn x86_user_phys_to_virt_bridge(phys: CULong) -> *mut c_void;
    fn x86_user_copy_log_bridge(event: CInt, vm: *mut c_void, a: CULong, b: CULong, error: CInt);
    fn x86_user_map_kernel_start_bridge() -> CULong;
    fn x86_pt_virt_to_phys_bridge(addr: *mut c_void) -> CULong;
    fn x86_pt_phys_to_virt_bridge(phys: CULong) -> *mut c_void;
    fn x86_pt_print_log_bridge(event: CInt, level: CInt, value: CULong, index: CInt);
    fn x86_arch_mem_virt_to_phys_bridge(addr: *mut c_void) -> CULong;
    fn x86_arch_mem_phys_to_virt_bridge(phys: CULong) -> *mut c_void;
    fn x86_attr_mask_bridge() -> CULong;
    fn x86_use_1gb_page_bridge() -> CInt;
    fn x86_common_vrflag_to_ptattr_bridge(flag: CULong, fault: CULong, ptep: *mut CULong)
        -> CULong;
    fn x86_early_alloc_panic_bridge(reason: CInt);
    fn x86_early_alloc_last_page_slot_bridge() -> *mut *mut c_void;
    fn x86_early_alloc_end_bridge() -> CULong;
    fn x86_bootstrap_mem_end_bridge() -> CULong;
    fn x86_early_alloc_invalidate_bridge();
    fn x86_kmalloc_bridge(size: CInt, flag: CInt) -> *mut c_void;
    fn x86_kmalloc_initialized_bridge() -> CInt;
    fn x86_kfree_bridge(ptr: *mut c_void);
    fn x86_mem_log_bridge(event: CInt);
    fn x86_page_table_init_pt_bridge() -> *mut c_void;
    fn x86_page_table_boot_pt_bridge() -> *mut c_void;
    fn x86_load_page_table_panic_bridge();
    fn ihk_mc_chk_page_address(phys: CULong) -> CInt;
    fn x86_pt_alloc_pages_bridge(nr_pages: CInt, ap_flag: CInt) -> *mut c_void;
    fn x86_pt_free_pages_bridge(pt: *mut c_void, nr_pages: CInt);
    fn x86_pt_destroy_panic_bridge(reason: CInt);
    fn x86_pt_destroy_helper_failed_panic_bridge();
    fn x86_visit_pte_log_bridge(event: CInt, level_shift: CInt);
    fn x86_check_available_page_size_bridge(event: CInt);
    fn x86_init_page_table_alloc_bridge(nr_pages: CInt, flag: CInt) -> *mut c_void;
    fn x86_init_page_table_spin_init_bridge(lock: *mut c_void);
    fn x86_init_page_table_normal_bridge(pt: *mut c_void);
    fn x86_init_page_table_linux_bridge(pt: *mut c_void);
    fn x86_init_page_table_fixed_bridge(pt: *mut c_void);
    fn x86_init_page_table_text_bridge(pt: *mut c_void);
    fn x86_init_page_table_vsyscall_bridge(pt: *mut c_void);
    fn x86_init_page_table_low_bridge(pt: *mut c_void);
    fn x86_init_page_table_load_bridge(pt: *mut c_void);
    fn x86_init_page_table_log_bridge(event: CInt, pt: *mut c_void);
    fn x86_init_page_table_panic_bridge(reason: CInt);
    fn x86_init_page_table_init_pt_slot_bridge() -> *mut *mut c_void;
    fn x86_init_page_table_boot_pt_slot_bridge() -> *mut *mut c_void;
    fn x86_init_page_table_loaded_slot_bridge() -> *mut CInt;
    fn x86_init_page_table_lock_bridge() -> *mut c_void;
    fn x86_init_page_table_size_bridge() -> SizeT;
    fn x86_map_fixed_area_init_pt_bridge() -> *mut c_void;
    fn x86_map_fixed_area_fixed_virt_slot_bridge() -> *mut CULong;
    fn x86_map_fixed_area_log_bridge(phys: CULong, size: CULong, virt: CULong);
    fn x86_pt_set_page_bridge(pt: *mut c_void, virt: CULong, phys: CULong, attr: CULong) -> CInt;
    fn x86_move_flush_tlb_bridge();
    fn x86_init_normal_get_memory_address_bridge(type_: CInt, arg: CInt) -> CULong;
    fn x86_init_normal_set_large_bridge(
        pt: *mut c_void,
        virt: CULong,
        phys: CULong,
        attr: CULong,
    ) -> CInt;
    fn x86_init_normal_log_bridge(event: CInt, a: CULong, b: CULong, c: CULong);
    fn x86_init_normal_panic_bridge();
    fn x86_init_linux_find_command_line_bridge(name: *mut i8) -> *mut i8;
    fn x86_init_linux_get_nr_memory_chunks_bridge() -> CInt;
    fn x86_init_linux_get_memory_chunk_bridge(
        id: CInt,
        start: *mut CULong,
        end: *mut CULong,
        numa_id: *mut CInt,
    ) -> CInt;
    fn x86_init_linux_log_bridge(
        event: CInt,
        a: CULong,
        b: CULong,
        c: CULong,
        d: CULong,
        error: CInt,
    );
    fn x86_init_linux_panic_bridge();
    fn x86_init_text_log_bridge(event: CInt, a: CULong, b: CULong, c: CULong);
    fn x86_init_text_map_kernel_start_bridge() -> CULong;
    fn x86_init_text_end_bridge() -> CULong;
    fn x86_init_text_panic_bridge();
    fn x86_init_low_panic_bridge();
    fn x86_init_fixed_panic_bridge();
    fn x86_init_vsyscall_page_bridge() -> *mut c_void;
    fn x86_init_vsyscall_panic_bridge();
    fn x86_reserve_arch_pages_bridge(start: CULong, end: CULong, cb: X86ReservePagesCbFn);
    fn x86_reserve_arch_pages_panic_bridge();
    #[link_name = "attr_mask"]
    static mut X86_ATTR_MASK: CULong;
    #[link_name = "_head"]
    static mut X86_HEAD: u8;
    #[link_name = "ap_trampoline"]
    static mut X86_AP_TRAMPOLINE: CULong;
    #[link_name = "linux_page_offset_base"]
    static mut LINUX_PAGE_OFFSET_BASE: CULong;
    #[link_name = "x86_kernel_phys_base"]
    static mut X86_KERNEL_PHYS_BASE: CULong;
}

#[no_mangle]
pub extern "C" fn flush_nfo_tlb() {}

#[no_mangle]
pub extern "C" fn flush_nfo_tlb_mm(_vm: *mut ProcessVm) {}

#[no_mangle]
pub unsafe extern "C" fn x86_vdso_packet_prepare_result(
    packet: *mut IkcScdPacket,
    msg: CInt,
    arg: CULong,
) -> CInt {
    if packet.is_null() {
        return -EINVAL;
    }

    let traditional = core::ptr::addr_of_mut!((*packet).body).cast::<IkcScdPacketTraditional>();
    write_volatile(core::ptr::addr_of_mut!((*packet).msg), msg);
    write_volatile(core::ptr::addr_of_mut!((*traditional).arg), arg);

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_early_alloc_pages_body_result(
    last_page_slot: *mut *mut c_void,
    end_addr: CULong,
    bootstrap_end: CULong,
    nr_pages: CInt,
    virt_to_phys_fn: Option<X86MemVirtToPhysFn>,
    phys_to_virt_fn: Option<X86MemPhysToVirtFn>,
    panic_fn: Option<X86MemPanicFn>,
) -> *mut c_void {
    if last_page_slot.is_null() {
        return core::ptr::null_mut();
    }
    let (Some(virt_to_phys), Some(phys_to_virt), Some(panic_cb)) =
        (virt_to_phys_fn, phys_to_virt_fn, panic_fn)
    else {
        return core::ptr::null_mut();
    };

    let mut last_page = read_volatile(last_page_slot);
    if last_page.is_null() {
        let aligned = x86_early_alloc_align_end_result(end_addr);
        last_page = phys_to_virt(virt_to_phys(aligned as *mut c_void));
    } else if last_page as usize == usize::MAX {
        panic_cb(1);
        return core::ptr::null_mut();
    } else if x86_early_alloc_exhausted_result(virt_to_phys(last_page), bootstrap_end) != 0 {
        panic_cb(2);
        return core::ptr::null_mut();
    }

    let ret = last_page;
    write_volatile(
        last_page_slot,
        x86_early_alloc_next_result(last_page as CULong, nr_pages) as *mut c_void,
    );
    ret
}

#[no_mangle]
pub unsafe extern "C" fn x86_early_alloc_invalidate_body_result(
    last_page_slot: *mut *mut c_void,
) -> CInt {
    if last_page_slot.is_null() {
        return -EINVAL;
    }
    write_volatile(last_page_slot, usize::MAX as *mut c_void);
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_get_last_early_heap_body_result(
    last_page_slot: *mut *mut c_void,
) -> *mut c_void {
    if last_page_slot.is_null() {
        return core::ptr::null_mut();
    }
    read_volatile(last_page_slot)
}

#[no_mangle]
pub unsafe extern "C" fn early_alloc_pages(nr_pages: CInt) -> *mut c_void {
    let last_page_slot = unsafe { x86_early_alloc_last_page_slot_bridge() };
    let end_addr = unsafe { x86_early_alloc_end_bridge() };
    let bootstrap_end = unsafe { x86_bootstrap_mem_end_bridge() };

    unsafe {
        x86_early_alloc_pages_body_result(
            last_page_slot,
            end_addr,
            bootstrap_end,
            nr_pages,
            Some(x86_arch_mem_virt_to_phys_bridge),
            Some(x86_arch_mem_phys_to_virt_bridge),
            Some(x86_early_alloc_panic_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn early_alloc_invalidate() {
    let last_page_slot = unsafe { x86_early_alloc_last_page_slot_bridge() };
    unsafe {
        x86_early_alloc_invalidate_bridge();
        let _ = x86_early_alloc_invalidate_body_result(last_page_slot);
    }
}

#[no_mangle]
pub unsafe extern "C" fn get_last_early_heap() -> *mut c_void {
    let last_page_slot = unsafe { x86_early_alloc_last_page_slot_bridge() };
    unsafe { x86_get_last_early_heap_body_result(last_page_slot) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_check_available_page_size_body_result(
    use_1gb_page_slot: *mut CInt,
    cpuid_edx_fn: Option<X86MemCpuidEdxFn>,
    log_fn: Option<X86MemLogIntFn>,
) -> CInt {
    if use_1gb_page_slot.is_null() {
        return -EINVAL;
    }
    let Some(cpuid_edx) = cpuid_edx_fn else {
        return -EINVAL;
    };

    let mut edx = 0;
    cpuid_edx(0x80000001, &mut edx);
    let available = ((edx & (1 << 26)) != 0) as CInt;
    write_volatile(use_1gb_page_slot, available);
    if let Some(log) = log_fn {
        log(1, available);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_enable_ptattr_no_execute_body_result(
    attr_mask_slot: *mut CULong,
    no_execute_attr: CULong,
) -> CInt {
    if attr_mask_slot.is_null() {
        return -EINVAL;
    }
    let attr = read_volatile(attr_mask_slot) | no_execute_attr;
    write_volatile(attr_mask_slot, attr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn enable_ptattr_no_execute() {
    unsafe {
        let _ = x86_enable_ptattr_no_execute_body_result(
            core::ptr::addr_of_mut!(X86_ATTR_MASK),
            PTATTR_NO_EXECUTE,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_ihk_mc_allocate_body_result(
    kmalloc_initialized: CInt,
    size: CInt,
    nowait_flag: CInt,
    kmalloc_fn: Option<X86MemKmallocFn>,
    log_fn: Option<X86MemLogFn>,
) -> *mut c_void {
    if kmalloc_initialized == 0 {
        if let Some(log) = log_fn {
            log(1);
        }
        return core::ptr::null_mut();
    }
    let Some(kmalloc_cb) = kmalloc_fn else {
        return core::ptr::null_mut();
    };
    kmalloc_cb(size, nowait_flag)
}

#[no_mangle]
pub unsafe extern "C" fn x86_ihk_mc_free_body_result(
    kmalloc_initialized: CInt,
    ptr: *mut c_void,
    kfree_fn: Option<X86MemKfreeFn>,
    log_fn: Option<X86MemLogFn>,
) -> CInt {
    if kmalloc_initialized == 0 {
        if let Some(log) = log_fn {
            log(2);
        }
        return 0;
    }
    let Some(kfree_cb) = kfree_fn else {
        return -EINVAL;
    };
    kfree_cb(ptr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_allocate(size: CInt, flag: CInt) -> *mut c_void {
    let _ = flag;
    let kmalloc_initialized = unsafe { x86_kmalloc_initialized_bridge() };

    unsafe {
        x86_ihk_mc_allocate_body_result(
            kmalloc_initialized,
            size,
            IHK_MC_AP_NOWAIT,
            Some(x86_kmalloc_bridge),
            Some(x86_mem_log_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_free(ptr: *mut c_void) {
    let kmalloc_initialized = unsafe { x86_kmalloc_initialized_bridge() };

    unsafe {
        let _ = x86_ihk_mc_free_body_result(
            kmalloc_initialized,
            ptr,
            Some(x86_kfree_bridge),
            Some(x86_mem_log_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_setup_l2_body_result(
    pt: *mut c_void,
    page_head: CULong,
    start: CULong,
    end: CULong,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
) -> CULong {
    let Some(virt_to_phys) = virt_to_phys_fn else {
        return 0;
    };
    if pt.is_null() {
        return 0;
    }

    let entries = pt.cast::<CULong>();
    for i in 0..(PT_ENTRIES as usize) {
        let phys = page_head.wrapping_add((i as CULong) << PTL2_SHIFT);
        let entry = if phys.wrapping_add(PTL2_SIZE) <= start || phys >= end {
            0
        } else {
            phys | PFL2_KERN_ATTR | PFL2_SIZE
        };
        unsafe {
            *entries.add(i) = entry;
        }
    }

    unsafe { virt_to_phys(pt) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_setup_l3_body_result(
    pt: *mut c_void,
    page_head: CULong,
    start: CULong,
    end: CULong,
    critical_flag: CInt,
    alloc_pages_fn: Option<X86PtAllocPagesFn>,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
) -> CULong {
    let (Some(alloc_pages), Some(virt_to_phys)) = (alloc_pages_fn, virt_to_phys_fn) else {
        return 0;
    };
    if pt.is_null() {
        return 0;
    }

    let entries = pt.cast::<CULong>();
    for i in 0..(PT_ENTRIES as usize) {
        let phys = page_head.wrapping_add((i as CULong) << PTL3_SHIFT);
        if phys.wrapping_add(PTL3_SIZE) <= start || phys >= end {
            unsafe {
                *entries.add(i) = 0;
            }
            continue;
        }

        let child_pt = unsafe { alloc_pages(1, critical_flag) };
        if child_pt.is_null() {
            return 0;
        }
        let child_phys =
            unsafe { x86_setup_l2_body_result(child_pt, phys, start, end, Some(virt_to_phys)) };
        unsafe {
            *entries.add(i) = child_phys | PFL3_PDIR_ATTR;
        }
    }

    unsafe { virt_to_phys(pt) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_page_table_body_result(
    init_pt_slot: *mut *mut c_void,
    boot_pt_slot: *mut *mut c_void,
    init_pt_loaded_slot: *mut CInt,
    init_pt_lock: *mut c_void,
    page_table_size: SizeT,
    critical_flag: CInt,
    check_available_page_size_fn: Option<X86MemLogFn>,
    alloc_pages_fn: Option<X86MemAllocPagesFn>,
    spin_init_fn: Option<X86MemSpinInitFn>,
    init_normal_area_fn: Option<X86MemPtInitFn>,
    init_linux_kernel_mapping_fn: Option<X86MemPtInitFn>,
    init_fixed_area_fn: Option<X86MemPtInitFn>,
    init_text_area_fn: Option<X86MemPtInitFn>,
    init_vsyscall_area_fn: Option<X86MemPtInitFn>,
    init_low_area_fn: Option<X86MemPtInitFn>,
    load_page_table_fn: Option<X86MemPtLoadFn>,
    log_fn: Option<X86MemPtLogFn>,
    panic_fn: Option<X86MemPanicFn>,
) -> CInt {
    if init_pt_slot.is_null()
        || boot_pt_slot.is_null()
        || init_pt_loaded_slot.is_null()
        || init_pt_lock.is_null()
        || page_table_size == 0
    {
        return -EINVAL;
    }
    let (
        Some(check_available_page_size),
        Some(alloc_pages),
        Some(spin_init),
        Some(init_normal_area),
        Some(init_linux_kernel_mapping),
        Some(init_fixed_area),
        Some(init_text_area),
        Some(init_vsyscall_area),
        Some(init_low_area),
        Some(load_page_table),
        Some(panic_cb),
    ) = (
        check_available_page_size_fn,
        alloc_pages_fn,
        spin_init_fn,
        init_normal_area_fn,
        init_linux_kernel_mapping_fn,
        init_fixed_area_fn,
        init_text_area_fn,
        init_vsyscall_area_fn,
        init_low_area_fn,
        load_page_table_fn,
        panic_fn,
    )
    else {
        return -EINVAL;
    };

    crate::x86_setup::early_phase(b'a');
    check_available_page_size(3);
    crate::x86_setup::early_phase(b'b');

    let init_pt = alloc_pages(1, critical_flag);
    if init_pt.is_null() {
        crate::x86_setup::early_panic();
        panic_cb(3);
        return -ENOMEM;
    }
    write_volatile(init_pt_slot, init_pt);
    spin_init(init_pt_lock);
    write_bytes(init_pt.cast::<u8>(), 0, page_table_size);
    crate::x86_setup::early_phase(b'c');

    init_normal_area(init_pt);
    crate::x86_setup::early_phase(b'd');
    init_linux_kernel_mapping(init_pt);
    crate::x86_setup::early_phase(b'e');
    init_fixed_area(init_pt);
    init_text_area(init_pt);
    init_vsyscall_area(init_pt);
    crate::x86_setup::early_phase(b'f');

    let boot_pt = alloc_pages(1, critical_flag);
    if boot_pt.is_null() {
        crate::x86_setup::early_panic();
        panic_cb(4);
        return -ENOMEM;
    }
    write_volatile(boot_pt_slot, boot_pt);
    copy_nonoverlapping(init_pt.cast::<u8>(), boot_pt.cast::<u8>(), page_table_size);
    init_low_area(boot_pt);

    let mut same = true;
    let mut offset = 0usize;
    while offset < page_table_size {
        if read_volatile(init_pt.cast::<u8>().add(offset))
            != read_volatile(boot_pt.cast::<u8>().add(offset))
        {
            same = false;
            break;
        }
        offset += 1;
    }
    if same {
        crate::x86_setup::early_panic();
        panic_cb(5);
        return -EINVAL;
    }
    crate::x86_setup::early_phase(b'g');

    crate::x86_setup::early_phase(b'h');
    load_page_table(init_pt);
    crate::x86_setup::early_phase(b'i');
    write_volatile(init_pt_loaded_slot, 1);
    if let Some(log) = log_fn {
        log(1, init_pt);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn init_page_table() {
    let ret = unsafe {
        x86_init_page_table_body_result(
            x86_init_page_table_init_pt_slot_bridge(),
            x86_init_page_table_boot_pt_slot_bridge(),
            x86_init_page_table_loaded_slot_bridge(),
            x86_init_page_table_lock_bridge(),
            x86_init_page_table_size_bridge(),
            IHK_MC_AP_CRITICAL,
            Some(x86_check_available_page_size_bridge),
            Some(x86_init_page_table_alloc_bridge),
            Some(x86_init_page_table_spin_init_bridge),
            Some(x86_init_page_table_normal_bridge),
            Some(x86_init_page_table_linux_bridge),
            Some(x86_init_page_table_fixed_bridge),
            Some(x86_init_page_table_text_bridge),
            Some(x86_init_page_table_vsyscall_bridge),
            Some(x86_init_page_table_low_bridge),
            Some(x86_init_page_table_load_bridge),
            Some(x86_init_page_table_log_bridge),
            Some(x86_init_page_table_panic_bridge),
        )
    };
    if ret != 0 {
        crate::x86_setup::early_panic();
        unsafe { x86_init_page_table_panic_bridge(0) };
    }
}

type X86WalkPteCallback =
    unsafe extern "C" fn(*mut c_void, *mut CULong, CULong, CULong, CULong) -> i32;
type X86VisitPteFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, *mut CULong, *mut c_void, CInt) -> CInt;
type X86VisitPteWalkFn =
    unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong, *mut c_void) -> CInt;
type X86VisitPteLogFn = unsafe extern "C" fn(CInt, CInt);
type X86WalkPhysCheckFn = unsafe extern "C" fn(CULong) -> i32;
type X86PtAllocPagesFn = unsafe extern "C" fn(CInt, CInt) -> *mut c_void;
type X86PtDestroyFn = unsafe extern "C" fn(CInt, *mut c_void);
type X86PtPhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type X86PtFreePagesFn = unsafe extern "C" fn(*mut c_void, CInt);
type X86PtDestroyPanicFn = unsafe extern "C" fn(CInt);
type X86PtVirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type X86PtPrintLogFn = unsafe extern "C" fn(CInt, CInt, CULong, CInt);
type X86PtSetPageFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong) -> CInt;
type X86PtSetPageLogFn = unsafe extern "C" fn(CULong);
type X86PtSetPteLogFn =
    unsafe extern "C" fn(CInt, *mut c_void, *mut CULong, CULong, CULong, CULong, CInt, CULong);
type X86PtSetPtePanicFn = unsafe extern "C" fn();

#[repr(C)]
struct X86VisitPteArgs {
    pt: *mut c_void,
    flags: CInt,
    pgshift: CInt,
    funcp: Option<X86VisitPteFn>,
    arg: *mut c_void,
}

type X86SplitPhysToPageFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type X86SplitPageMapFn = unsafe extern "C" fn(*mut c_void);
type X86SplitRssFn = unsafe extern "C" fn(SizeT, SizeT);
type X86SplitPageUnmapFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type X86SplitLogFn = unsafe extern "C" fn(CInt, CULong, SizeT, SizeT, *mut c_void);
type X86SplitPanicFn = unsafe extern "C" fn();
type X86PtSplitLookupFn = unsafe extern "C" fn(
    *mut c_void,
    CULong,
    CInt,
    *mut CULong,
    *mut SizeT,
    *mut CInt,
) -> *mut CULong;
type X86PtSplitableFn = unsafe extern "C" fn(*mut c_void, u32) -> CInt;
type X86PtSplitLargeFn = unsafe extern "C" fn(*mut CULong, SizeT) -> CInt;
type X86PtSplitFlushFn = unsafe extern "C" fn(*mut c_void, CULong, CInt);
type X86PtSplitLogFn = unsafe extern "C" fn(CInt, CInt);
type X86MoveSetRangeFn = unsafe extern "C" fn(
    *mut c_void,
    *mut c_void,
    CULong,
    CULong,
    CULong,
    CULong,
    CInt,
    *mut c_void,
    CInt,
) -> CInt;
type X86MoveLogFn = unsafe extern "C" fn(
    CInt,
    *mut c_void,
    *mut c_void,
    *mut CULong,
    CULong,
    CULong,
    CULong,
    CInt,
    CInt,
);
type X86MoveVisitRangeFn = unsafe extern "C" fn(
    *mut c_void,
    CULong,
    CULong,
    CInt,
    CInt,
    X86VisitPteFn,
    *mut c_void,
) -> CInt;
type X86MoveFlushFn = unsafe extern "C" fn();
type X86ReadCr3Fn = unsafe extern "C" fn() -> CULong;
type X86LoadCr3Fn = unsafe extern "C" fn(CULong);
type X86InvlpgFn = unsafe extern "C" fn(CULong);
type X86GetMemoryAddressFn = unsafe extern "C" fn(CInt, CInt) -> CULong;
type X86InitNormalLogFn = unsafe extern "C" fn(CInt, CULong, CULong, CULong);
type X86InitTextLogFn = unsafe extern "C" fn(CInt, CULong, CULong, CULong);
type X86FindCommandLineFn = unsafe extern "C" fn(*mut i8) -> *mut i8;
type X86GetNrMemoryChunksFn = unsafe extern "C" fn() -> CInt;
type X86GetMemoryChunkFn = unsafe extern "C" fn(CInt, *mut CULong, *mut CULong, *mut CInt) -> CInt;
type X86InitLinuxLogFn = unsafe extern "C" fn(CInt, CULong, CULong, CULong, CULong, CInt);
type X86AddrLogFn = unsafe extern "C" fn(CInt, CULong);
type X86MemVirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type X86MemPhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type X86MemPanicFn = unsafe extern "C" fn(CInt);
type X86MemCpuidEdxFn = unsafe extern "C" fn(CULong, *mut CULong);
type X86MemLogIntFn = unsafe extern "C" fn(CInt, CInt);
type X86MemLogFn = unsafe extern "C" fn(CInt);
type X86MemKmallocFn = unsafe extern "C" fn(CInt, CInt) -> *mut c_void;
type X86MemKfreeFn = unsafe extern "C" fn(*mut c_void);
type X86MemAllocPagesFn = unsafe extern "C" fn(CInt, CInt) -> *mut c_void;
type X86MemSpinInitFn = unsafe extern "C" fn(*mut c_void);
type X86MemPtInitFn = unsafe extern "C" fn(*mut c_void);
type X86MemPtLoadFn = unsafe extern "C" fn(*mut c_void);
type X86MemPtLogFn = unsafe extern "C" fn(CInt, *mut c_void);
type X86ReservePagesCbFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, CInt);
type X86ReserveArchFn = unsafe extern "C" fn(CULong, CULong, X86ReservePagesCbFn);
type X86ClearRemoteFlushFn = unsafe extern "C" fn(*mut c_void, *mut CULong, CInt, CInt);
type X86ClearFlushMemobjFn = unsafe extern "C" fn(*mut c_void, CULong, CULong);
type X86ClearPhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type X86ClearFreePagesFn = unsafe extern "C" fn(*mut c_void, CInt);
type X86ClearPageUnmapFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type X86ClearRssSubFn = unsafe extern "C" fn(CULong, CULong);
type X86ClearMemobjRssSubFn = unsafe extern "C" fn(*mut c_void, CULong, CULong);
type X86ClearEffectLogFn = unsafe extern "C" fn(CInt, CULong, CULong, CULong);
type X86ClearRangeTopLogFn = unsafe extern "C" fn(CInt, *mut c_void, CULong, CULong, CInt);
type X86ClearOldActionFn = unsafe extern "C" fn(
    *mut c_void,
    CULong,
    CULong,
    *mut CULong,
    *mut *mut c_void,
    *mut CInt,
) -> CInt;
type X86ClearChildWalkFn =
    unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong, *mut c_void) -> CInt;
type X86ClearRangeLogFn = unsafe extern "C" fn(
    CInt,
    *mut c_void,
    *mut CULong,
    CULong,
    CULong,
    CULong,
    CInt,
    CInt,
    CULong,
);
type X86SetRangeClearFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CULong, CInt, *mut c_void) -> CInt;
type X86SetRangeRssAddFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong) -> CInt;
type X86SetRangeLogFn = unsafe extern "C" fn(
    CInt,
    CInt,
    CULong,
    CULong,
    CULong,
    CInt,
    CULong,
    CULong,
    CULong,
    CULong,
    CInt,
);
type X86SetRangeChildWalkFn =
    unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong, *mut c_void) -> CInt;
type X86RangeTopWalkFn =
    unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong, *mut c_void) -> CInt;
type X86UserPageFaultFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong) -> CInt;
type X86UserVtopFn = unsafe extern "C" fn(*mut c_void, *const c_void, *mut CULong) -> CInt;
type X86UserIsMemoryFn = unsafe extern "C" fn(CULong, CULong) -> CInt;
type X86UserMapFn = unsafe extern "C" fn(CULong, CInt, CULong) -> *mut c_void;
type X86UserUnmapFn = unsafe extern "C" fn(*mut c_void, CInt);
type X86UserPhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type X86UserLogFn = unsafe extern "C" fn(CInt, *mut c_void, CULong, CULong, CInt);
type X86ReadProcessVmFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, *const c_void, SizeT) -> CInt;
type X86WriteProcessVmFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, *const c_void, SizeT) -> CInt;
type X86CopyFromUserFn = unsafe extern "C" fn(*mut c_void, *const c_void, SizeT) -> CInt;
type X86CopyToUserFn = unsafe extern "C" fn(*mut c_void, *const c_void, SizeT) -> CInt;

#[no_mangle]
pub unsafe extern "C" fn x86_pt_print_pte_body_result(
    pt: *mut c_void,
    init_pt: *mut c_void,
    virt: CULong,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
    log_fn: Option<X86PtPrintLogFn>,
) -> CInt {
    let (Some(virt_to_phys), Some(phys_to_virt), Some(log)) =
        (virt_to_phys_fn, phys_to_virt_fn, log_fn)
    else {
        return -EINVAL;
    };

    let mut table = if pt.is_null() { init_pt } else { pt } as *mut CULong;
    if table.is_null() {
        return -EFAULT;
    }

    let l4idx = ((virt >> PTL4_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l3idx = ((virt >> PTL3_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l2idx = ((virt >> PTL2_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l1idx = ((virt >> PTL1_SHIFT) & (PT_ENTRIES - 1)) as usize;

    unsafe {
        log(
            X86_PT_PRINT_LOG_TABLE,
            4,
            virt_to_phys(table.cast::<c_void>()),
            l4idx as CInt,
        );
    }
    let mut entry = unsafe { read_volatile(table.add(l4idx)) };
    if (entry & PFL2_PRESENT) == 0 {
        unsafe { log(X86_PT_PRINT_LOG_NOT_PRESENT, 4, virt, l4idx as CInt) };
        return -EFAULT;
    }
    unsafe { log(X86_PT_PRINT_LOG_ENTRY, 4, entry, l4idx as CInt) };

    table = unsafe { phys_to_virt(entry & PAGE_MASK) as *mut CULong };
    if table.is_null() {
        return -EFAULT;
    }
    unsafe {
        log(
            X86_PT_PRINT_LOG_TABLE,
            3,
            virt_to_phys(table.cast::<c_void>()),
            l3idx as CInt,
        );
    }
    entry = unsafe { read_volatile(table.add(l3idx)) };
    if (entry & PFL2_PRESENT) == 0 {
        unsafe { log(X86_PT_PRINT_LOG_NOT_PRESENT, 3, virt, l3idx as CInt) };
        return -EFAULT;
    }
    unsafe { log(X86_PT_PRINT_LOG_ENTRY, 3, entry, l3idx as CInt) };
    if (entry & PFL2_SIZE) != 0 {
        unsafe { log(X86_PT_PRINT_LOG_LARGE, 3, entry, l3idx as CInt) };
        return 0;
    }

    table = unsafe { phys_to_virt(entry & PAGE_MASK) as *mut CULong };
    if table.is_null() {
        return -EFAULT;
    }
    unsafe {
        log(
            X86_PT_PRINT_LOG_TABLE,
            2,
            virt_to_phys(table.cast::<c_void>()),
            l2idx as CInt,
        );
    }
    entry = unsafe { read_volatile(table.add(l2idx)) };
    if (entry & PFL2_PRESENT) == 0 {
        unsafe { log(X86_PT_PRINT_LOG_NOT_PRESENT, 2, virt, l2idx as CInt) };
        return -EFAULT;
    }
    unsafe { log(X86_PT_PRINT_LOG_ENTRY, 2, entry, l2idx as CInt) };
    if (entry & PFL2_SIZE) != 0 {
        unsafe { log(X86_PT_PRINT_LOG_LARGE, 2, entry, l2idx as CInt) };
        return 0;
    }

    table = unsafe { phys_to_virt(entry & PAGE_MASK) as *mut CULong };
    if table.is_null() {
        return -EFAULT;
    }
    unsafe {
        log(
            X86_PT_PRINT_LOG_TABLE,
            1,
            virt_to_phys(table.cast::<c_void>()),
            l1idx as CInt,
        );
    }
    entry = unsafe { read_volatile(table.add(l1idx)) };
    if (entry & PFL2_PRESENT) == 0 {
        unsafe {
            log(X86_PT_PRINT_LOG_NOT_PRESENT, 1, virt, l1idx as CInt);
            log(X86_PT_PRINT_LOG_ENTRY, 1, entry, l1idx as CInt);
        }
        return -EFAULT;
    }
    unsafe { log(X86_PT_PRINT_LOG_ENTRY, 1, entry, l1idx as CInt) };
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_print_pte(pt: *mut c_void, virt: *mut c_void) -> CInt {
    unsafe {
        x86_pt_print_pte_body_result(
            pt,
            x86_page_table_init_pt_bridge(),
            virt as CULong,
            Some(x86_pt_virt_to_phys_bridge),
            Some(x86_pt_phys_to_virt_bridge),
            Some(x86_pt_print_log_bridge),
        )
    }
}

#[no_mangle]
pub extern "C" fn x86_attr_to_l3attr_result(attr: CULong, attr_mask: CULong) -> CULong {
    let result = attr & (attr_mask | PTATTR_LARGEPAGE);

    if (attr & PTATTR_UNCACHABLE) != 0 && (attr & PTATTR_LARGEPAGE) != 0 {
        result | PFLX_PCD | PFLX_PWT
    } else {
        result
    }
}

#[no_mangle]
pub extern "C" fn x86_attr_to_l2attr_result(attr: CULong, attr_mask: CULong) -> CULong {
    let result = attr & (attr_mask | PTATTR_LARGEPAGE);

    if (attr & PTATTR_UNCACHABLE) != 0 && (attr & PTATTR_LARGEPAGE) != 0 {
        result | PFLX_PCD | PFLX_PWT
    } else {
        result
    }
}

#[no_mangle]
pub extern "C" fn x86_attr_to_l1attr_result(attr: CULong, attr_mask: CULong) -> CULong {
    if (attr & PTATTR_UNCACHABLE) != 0 {
        (attr & attr_mask) | PFLX_PCD | PFLX_PWT
    } else if (attr & PTATTR_WRITE_COMBINED) != 0 {
        (attr & attr_mask) | PFLX_PWT
    } else {
        attr & attr_mask
    }
}

#[no_mangle]
pub extern "C" fn x86_set_pte_value_result(
    phys: CULong,
    attr: CULong,
    attr_mask: CULong,
) -> CULong {
    if (attr & PTATTR_LARGEPAGE) != 0 {
        phys | x86_attr_to_l2attr_result(attr, attr_mask) | PFL2_SIZE
    } else {
        phys | x86_attr_to_l1attr_result(attr, attr_mask)
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_pte(ppte: *mut CULong, phys: CULong, attr: CULong) {
    unsafe {
        *ppte = x86_set_pte_value_result(phys, attr, x86_attr_mask_bridge());
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_pt_large_page(
    pt: *mut c_void,
    virt: *mut c_void,
    phys: CULong,
    attr: CULong,
) -> CInt {
    unsafe {
        x86_pt_set_page_bridge(
            pt,
            virt as CULong,
            phys,
            attr | PTATTR_LARGEPAGE | PTATTR_ACTIVE,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_set_large_page(
    pt: *mut c_void,
    virt: *mut c_void,
    phys: CULong,
    attr: CULong,
) -> CInt {
    unsafe {
        x86_pt_set_page_bridge(
            pt,
            virt as CULong,
            phys,
            attr | PTATTR_LARGEPAGE | PTATTR_ACTIVE,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_set_page(
    pt: *mut c_void,
    virt: *mut c_void,
    phys: CULong,
    attr: CULong,
) -> CInt {
    unsafe { x86_pt_set_page_bridge(pt, virt as CULong, phys, attr | PTATTR_ACTIVE) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_set_pte_value_result(
    pgsize: CULong,
    phys: CULong,
    attr: CULong,
    attr_mask: CULong,
    use_1gb_page: i32,
    entryp: *mut CULong,
) -> i32 {
    let entry = if pgsize == PTL1_SIZE {
        phys | x86_attr_to_l1attr_result(attr, attr_mask)
    } else if pgsize == PTL2_SIZE {
        if (phys & (PTL2_SIZE - 1)) != 0 {
            return -1;
        }
        phys | x86_attr_to_l2attr_result(attr | PTATTR_LARGEPAGE, attr_mask)
    } else if pgsize == PTL3_SIZE && use_1gb_page != 0 {
        if (phys & (PTL3_SIZE - 1)) != 0 {
            return -1;
        }
        phys | x86_attr_to_l3attr_result(attr | PTATTR_LARGEPAGE, attr_mask)
    } else {
        return -EINVAL;
    };

    if !entryp.is_null() {
        unsafe {
            *entryp = entry;
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_smaller_page_size_result(
    cursize: CULong,
    use_1gb_page: i32,
    newsizep: *mut CULong,
    p2alignp: *mut i32,
) -> i32 {
    let (newsize, p2align, error) = if cursize > PTL3_SIZE && use_1gb_page != 0 {
        (PTL3_SIZE, PTL3_SHIFT - PTL1_SHIFT, 0)
    } else if cursize > PTL2_SIZE {
        (PTL2_SIZE, PTL2_SHIFT - PTL1_SHIFT, 0)
    } else if cursize > PTL1_SIZE {
        (PTL1_SIZE, 0, 0)
    } else {
        (0, -1, -ENOMEM)
    };

    if !newsizep.is_null() {
        unsafe {
            *newsizep = newsize;
        }
    }
    if !p2alignp.is_null() {
        unsafe {
            *p2alignp = p2align;
        }
    }

    error
}

#[no_mangle]
pub extern "C" fn x86_early_alloc_align_end_result(end_addr: CULong) -> CULong {
    (end_addr + PTL1_SIZE - 1) & !(PTL1_SIZE - 1)
}

#[no_mangle]
pub extern "C" fn x86_early_alloc_exhausted_result(
    current_phys: CULong,
    bootstrap_end: CULong,
) -> i32 {
    (current_phys >= bootstrap_end) as i32
}

#[no_mangle]
pub extern "C" fn x86_early_alloc_next_result(current: CULong, nr_pages: i32) -> CULong {
    current + ((nr_pages as CULong) * PTL1_SIZE)
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_indices_result(
    virt: CULong,
    l4idxp: *mut i32,
    l3idxp: *mut i32,
    l2idxp: *mut i32,
    l1idxp: *mut i32,
) {
    if !l4idxp.is_null() {
        unsafe {
            *l4idxp = ((virt >> 39) & (PT_ENTRIES - 1)) as i32;
        }
    }
    if !l3idxp.is_null() {
        unsafe {
            *l3idxp = ((virt >> PTL3_SHIFT) & (PT_ENTRIES - 1)) as i32;
        }
    }
    if !l2idxp.is_null() {
        unsafe {
            *l2idxp = ((virt >> PTL2_SHIFT) & (PT_ENTRIES - 1)) as i32;
        }
    }
    if !l1idxp.is_null() {
        unsafe {
            *l1idxp = ((virt >> PTL1_SHIFT) & (PT_ENTRIES - 1)) as i32;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_walk_bounds_result(
    start: CULong,
    end: CULong,
    base: CULong,
    span: CULong,
    shift: i32,
    sixp: *mut i32,
    eixp: *mut i32,
) {
    let size = 1u64 << shift;
    let six = if start <= base {
        0
    } else {
        ((start - base) >> shift) as i32
    };
    let eix = if end == 0 || (span != 0 && base.wrapping_add(span) <= end) {
        PT_ENTRIES as i32
    } else {
        (((end - base) + (size - 1)) >> shift) as i32
    };

    if !sixp.is_null() {
        unsafe {
            *sixp = six;
        }
    }
    if !eixp.is_null() {
        unsafe {
            *eixp = eix;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_walk_step_result(
    current_ret: i32,
    error: i32,
    next_retp: *mut i32,
) -> i32 {
    let mut next_ret = current_ret;
    let mut stop = 0;

    if error == 0 {
        next_ret = 0;
    } else if error != -ENOENT {
        next_ret = error;
        stop = 1;
    }

    if !next_retp.is_null() {
        unsafe {
            *next_retp = next_ret;
        }
    }
    stop
}

#[no_mangle]
pub unsafe extern "C" fn x86_walk_pte_range_result(
    pt_addr: CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    span: CULong,
    shift: i32,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
    phys_check_fn: Option<X86WalkPhysCheckFn>,
    phys_mask: CULong,
) -> i32 {
    if pt_addr == 0 {
        return -ENOENT;
    }
    let Some(func) = funcp else {
        return -ENOENT;
    };

    let mut six = 0;
    let mut eix = 0;
    unsafe {
        x86_walk_bounds_result(start, end, base, span, shift, &mut six, &mut eix);
    }

    let pt = pt_addr as *mut CULong;
    let mut ret = -ENOENT;
    let mut i = six;
    while i < eix {
        let ptep = unsafe { pt.add(i as usize) };

        if let Some(check) = phys_check_fn {
            let entry = unsafe { read_volatile(ptep) };
            if unsafe { check(entry & phys_mask) } == -1 {
                i += 1;
                continue;
            }
        }

        let off = (i as CULong) << (shift as u32);
        let error = unsafe { func(args, ptep, base.wrapping_add(off), start, end) };
        if unsafe { x86_walk_step_result(ret, error, &mut ret) } != 0 {
            break;
        }
        i += 1;
    }

    ret
}

#[no_mangle]
pub unsafe extern "C" fn x86_virt_to_phys_level_result(
    entry: CULong,
    virt: CULong,
    level_shift: i32,
    size_flag: CULong,
    physp: *mut CULong,
    sizep: *mut CULong,
) -> i32 {
    let level_size = (1 as CULong) << (level_shift as u32);

    if (entry & PFL2_PRESENT) == 0 {
        return X86_VTOP_MISS;
    }

    if (size_flag != 0 && (entry & size_flag) != 0) || level_shift == PTL1_SHIFT {
        if !physp.is_null() {
            unsafe {
                *physp = (entry & PT_PHYSMASK) | (virt & (level_size - 1));
            }
        }
        if !sizep.is_null() {
            unsafe {
                *sizep = level_size;
            }
        }
        return X86_VTOP_HIT;
    }

    X86_VTOP_WALK
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_virt_to_phys_size_result(
    pt: *mut c_void,
    init_pt: *mut c_void,
    virt: CULong,
    phys: *mut CULong,
    size: *mut CULong,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
) -> CInt {
    let Some(phys_to_virt) = phys_to_virt_fn else {
        return -EFAULT;
    };
    let mut entries = if pt.is_null() {
        init_pt as *mut CULong
    } else {
        pt as *mut CULong
    };
    if entries.is_null() {
        return -EFAULT;
    }

    let l4idx = ((virt >> PTL4_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l3idx = ((virt >> PTL3_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l2idx = ((virt >> PTL2_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l1idx = ((virt >> PTL1_SHIFT) & (PT_ENTRIES - 1)) as usize;

    let l4e = unsafe { read_volatile(entries.add(l4idx)) };
    let mut action = unsafe {
        x86_virt_to_phys_level_result(
            l4e,
            virt,
            PTL4_SHIFT,
            0,
            core::ptr::null_mut(),
            core::ptr::null_mut(),
        )
    };
    if action == X86_VTOP_MISS {
        return -EFAULT;
    }

    entries = unsafe { phys_to_virt(l4e & PT_PHYSMASK) as *mut CULong };
    if entries.is_null() {
        return -EFAULT;
    }

    let l3e = unsafe { read_volatile(entries.add(l3idx)) };
    action = unsafe { x86_virt_to_phys_level_result(l3e, virt, PTL3_SHIFT, PFL2_SIZE, phys, size) };
    if action == X86_VTOP_MISS {
        return -EFAULT;
    }
    if action == X86_VTOP_HIT {
        return 0;
    }

    entries = unsafe { phys_to_virt(l3e & PT_PHYSMASK) as *mut CULong };
    if entries.is_null() {
        return -EFAULT;
    }

    let l2e = unsafe { read_volatile(entries.add(l2idx)) };
    action = unsafe { x86_virt_to_phys_level_result(l2e, virt, PTL2_SHIFT, PFL2_SIZE, phys, size) };
    if action == X86_VTOP_MISS {
        return -EFAULT;
    }
    if action == X86_VTOP_HIT {
        return 0;
    }

    entries = unsafe { phys_to_virt(l2e & PT_PHYSMASK) as *mut CULong };
    if entries.is_null() {
        return -EFAULT;
    }

    let l1e = unsafe { read_volatile(entries.add(l1idx)) };
    action = unsafe { x86_virt_to_phys_level_result(l1e, virt, PTL1_SHIFT, 0, phys, size) };
    if action == X86_VTOP_MISS {
        return -EFAULT;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_virt_to_pagemap_result(
    pt: *mut c_void,
    init_pt: *mut c_void,
    virt: CULong,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
) -> CULong {
    let mut phys = 0;

    if unsafe {
        x86_pt_virt_to_phys_size_result(
            pt,
            init_pt,
            virt,
            &mut phys,
            core::ptr::null_mut(),
            phys_to_virt_fn,
        )
    } != 0
    {
        return (PTL1_SHIFT as CULong) << PM_PSHIFT_OFFSET;
    }

    ((phys >> PTL1_SHIFT) & PM_PFRAME_MASK)
        | ((PTL1_SHIFT as CULong) << PM_PSHIFT_OFFSET)
        | PM_PRESENT
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_large_page_prepare_result(
    entry: CULong,
    pgsize: CULong,
    child_entryp: *mut CULong,
    rss_pgsizep: *mut CULong,
    step_p: *mut CULong,
) -> i32 {
    if pgsize != PTL3_SIZE && pgsize != PTL2_SIZE {
        return -EINVAL;
    }

    if !child_entryp.is_null() {
        unsafe {
            *child_entryp = if pgsize == PTL2_SIZE {
                entry & !PFL2_SIZE
            } else {
                entry
            };
        }
    }
    if !rss_pgsizep.is_null() {
        unsafe {
            *rss_pgsizep = pgsize / PT_ENTRIES;
        }
    }
    if !step_p.is_null() {
        unsafe {
            *step_p = pgsize / PT_ENTRIES;
        }
    }

    0
}

#[no_mangle]
pub extern "C" fn x86_split_large_page_next_entry_result(entry: CULong, pgsize: CULong) -> CULong {
    entry + pgsize / PT_ENTRIES
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_large_page_source_result(
    entry: CULong,
    pgsize: CULong,
    phys_basep: *mut CULong,
    child_entryp: *mut CULong,
    rss_pgsizep: *mut CULong,
) -> i32 {
    let mut child_entry = 0;
    let mut rss_pgsize = 0;
    let error = unsafe {
        x86_split_large_page_prepare_result(
            entry,
            pgsize,
            &mut child_entry,
            &mut rss_pgsize,
            core::ptr::null_mut(),
        )
    };
    if error != 0 {
        return -EINVAL;
    }

    if !phys_basep.is_null() {
        unsafe {
            *phys_basep = if (entry & x86_fileoff_flag(pgsize)) != 0 {
                NOPHYS
            } else {
                entry & PT_PHYSMASK
            };
        }
    }
    if !child_entryp.is_null() {
        unsafe {
            *child_entryp = child_entry;
        }
    }
    if !rss_pgsizep.is_null() {
        unsafe {
            *rss_pgsizep = rss_pgsize;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_large_page_child_map_result(
    phys_base: CULong,
    pgsize: CULong,
    index: i32,
    physp: *mut CULong,
) -> i32 {
    if phys_base == NOPHYS || pgsize == PTL2_SIZE {
        return 0;
    }

    if !physp.is_null() {
        unsafe {
            *physp = phys_base + ((index as CULong) * pgsize / PT_ENTRIES);
        }
    }

    1
}

#[no_mangle]
pub extern "C" fn x86_split_large_page_publish_result(child_pt_phys: CULong) -> CULong {
    (child_pt_phys & PT_PHYSMASK) | PFL2_PDIR_ATTR
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_large_page_source_unmap_result(
    phys_base: CULong,
    pgsize: CULong,
    physp: *mut CULong,
) -> i32 {
    if phys_base == NOPHYS || pgsize == PTL2_SIZE {
        return 0;
    }

    if !physp.is_null() {
        unsafe {
            *physp = phys_base;
        }
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_large_page_body_result(
    ptep: *mut CULong,
    pgsize: SizeT,
    alloc_ap_flag: CInt,
    alloc_fn: Option<X86PtAllocPagesFn>,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
    phys_to_page_fn: Option<X86SplitPhysToPageFn>,
    page_map_fn: Option<X86SplitPageMapFn>,
    rss_add_fn: Option<X86SplitRssFn>,
    rss_sub_fn: Option<X86SplitRssFn>,
    page_unmap_fn: Option<X86SplitPageUnmapFn>,
    log_fn: Option<X86SplitLogFn>,
    panic_fn: Option<X86SplitPanicFn>,
) -> CInt {
    if ptep.is_null() {
        return -EINVAL;
    }

    let pgsize_ul = pgsize as CULong;
    let source_entry = unsafe { read_volatile(ptep) };
    let source_fileoff = (source_entry & x86_fileoff_flag(pgsize_ul)) != 0;
    let mut phys_base = 0;
    let mut child_entry = 0;
    let mut rss_pgsize = 0;

    if unsafe {
        x86_split_large_page_source_result(
            source_entry,
            pgsize_ul,
            &mut phys_base,
            &mut child_entry,
            &mut rss_pgsize,
        )
    } != 0
    {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    X86_SPLIT_LARGE_PAGE_LOG_INVALID_PGSIZE,
                    0,
                    pgsize,
                    pgsize,
                    core::ptr::null_mut(),
                );
            }
        }
        return -EINVAL;
    }

    let (Some(alloc), Some(virt_to_phys), Some(rss_add), Some(rss_sub)) =
        (alloc_fn, virt_to_phys_fn, rss_add_fn, rss_sub_fn)
    else {
        return -EINVAL;
    };

    let pt = unsafe { alloc(1, alloc_ap_flag) };
    if pt.is_null() {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    X86_SPLIT_LARGE_PAGE_LOG_ALLOC_FAILED,
                    0,
                    pgsize,
                    pgsize,
                    core::ptr::null_mut(),
                );
            }
        }
        return -ENOMEM;
    }

    let entries = pt as *mut CULong;
    let mut i = 0;
    while i < PT_ENTRIES as usize {
        let mut phys = 0;

        if unsafe {
            x86_split_large_page_child_map_result(phys_base, pgsize_ul, i as CInt, &mut phys)
        } != 0
        {
            let Some(phys_to_page) = phys_to_page_fn else {
                return -EINVAL;
            };
            let page = unsafe { phys_to_page(phys) };
            if !page.is_null() {
                let Some(page_map) = page_map_fn else {
                    return -EINVAL;
                };
                unsafe {
                    page_map(page);
                }
            }
        }

        unsafe {
            x86_pte_store_result(entries.add(i), child_entry);
        }
        let log_value = if source_fileoff {
            child_entry & PAGE_MASK
        } else {
            child_entry & PT_PHYSMASK
        };
        if let Some(log) = log_fn {
            unsafe {
                log(
                    X86_SPLIT_LARGE_PAGE_LOG_RSS_ADD,
                    log_value,
                    rss_pgsize as SizeT,
                    rss_pgsize as SizeT,
                    core::ptr::null_mut(),
                );
            }
        }
        unsafe {
            rss_add(rss_pgsize as SizeT, rss_pgsize as SizeT);
        }

        child_entry = x86_split_large_page_next_entry_result(child_entry, pgsize_ul);
        i += 1;
    }

    unsafe {
        x86_pte_store_result(ptep, x86_split_large_page_publish_result(virt_to_phys(pt)));
    }

    if let Some(log) = log_fn {
        unsafe {
            log(
                X86_SPLIT_LARGE_PAGE_LOG_RSS_SUB,
                phys_base,
                pgsize,
                pgsize,
                core::ptr::null_mut(),
            );
        }
    }
    unsafe {
        rss_sub(pgsize, pgsize);
    }

    let mut phys = 0;
    if unsafe { x86_split_large_page_source_unmap_result(phys_base, pgsize_ul, &mut phys) } != 0 {
        let Some(phys_to_page) = phys_to_page_fn else {
            return -EINVAL;
        };
        let page = unsafe { phys_to_page(phys) };
        if !page.is_null() {
            let Some(page_unmap) = page_unmap_fn else {
                return -EINVAL;
            };
            if unsafe { page_unmap(page) } != 0 {
                if let Some(log) = log_fn {
                    unsafe {
                        log(
                            X86_SPLIT_LARGE_PAGE_LOG_PAGE_UNMAP,
                            phys,
                            pgsize,
                            pgsize,
                            page,
                        );
                    }
                }
                if let Some(panic) = panic_fn {
                    unsafe {
                        panic();
                    }
                }
            }
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_split_body_result(
    pt: *mut c_void,
    vm: *mut c_void,
    addr: CULong,
    memobj_flags: u32,
    cpu_id: CInt,
    lookup_fn: Option<X86PtSplitLookupFn>,
    phys_to_page_fn: Option<X86SplitPhysToPageFn>,
    splitable_fn: Option<X86PtSplitableFn>,
    split_large_fn: Option<X86PtSplitLargeFn>,
    flush_fn: Option<X86PtSplitFlushFn>,
    log_fn: Option<X86PtSplitLogFn>,
) -> CInt {
    let (Some(lookup), Some(splitable), Some(split_large), Some(flush)) =
        (lookup_fn, splitable_fn, split_large_fn, flush_fn)
    else {
        return -EINVAL;
    };

    loop {
        let mut pgaddr = 0;
        let mut pgsize = 0;
        let ptep = unsafe { lookup(pt, addr, 0, &mut pgaddr, &mut pgsize, core::ptr::null_mut()) };

        if ptep.is_null() || unsafe { read_volatile(ptep) } == PTE_NULL || pgaddr == addr {
            return 0;
        }

        let entry = unsafe { read_volatile(ptep) };
        let mut page = core::ptr::null_mut();
        if (entry & x86_fileoff_flag(pgsize as CULong)) == 0 {
            let Some(phys_to_page) = phys_to_page_fn else {
                return -EINVAL;
            };
            page = unsafe { phys_to_page(entry & PT_PHYSMASK) };
        }

        if unsafe { splitable(page, memobj_flags) } == 0 {
            if let Some(log) = log_fn {
                unsafe {
                    log(X86_PT_SPLIT_LOG_NOT_SPLITABLE, 0);
                }
            }
            return -EINVAL;
        }

        let error = unsafe { split_large(ptep, pgsize) };
        if error != 0 {
            if let Some(log) = log_fn {
                unsafe {
                    log(X86_PT_SPLIT_LOG_SPLIT_FAILED, error);
                }
            }
            return error;
        }

        unsafe {
            flush(vm, pgaddr, cpu_id);
        }
    }
}

#[no_mangle]
pub extern "C" fn x86_clear_pt_page_aligned_addr_result(virt: CULong, largepage: i32) -> CULong {
    if largepage != 0 {
        virt & LARGE_PAGE_MASK
    } else {
        virt & PAGE_MASK
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_clear_pt_page_target_result(
    l2_entry: CULong,
    largepage: i32,
    clear_l2p: *mut i32,
) -> i32 {
    if (l2_entry & PFL2_PRESENT) == 0 {
        return -EINVAL;
    }

    if !clear_l2p.is_null() {
        unsafe {
            *clear_l2p = (largepage != 0) as i32;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_clear_page_result(
    pt: *mut c_void,
    init_pt: *mut c_void,
    virt: CULong,
    largepage: i32,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
) -> i32 {
    let Some(phys_to_virt) = phys_to_virt_fn else {
        return -EINVAL;
    };
    let mut entries = if pt.is_null() {
        init_pt as *mut CULong
    } else {
        pt as *mut CULong
    };
    if entries.is_null() {
        return -EINVAL;
    }

    let virt = x86_clear_pt_page_aligned_addr_result(virt, largepage);
    let l4idx = ((virt >> PTL4_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l3idx = ((virt >> PTL3_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l2idx = ((virt >> PTL2_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l1idx = ((virt >> PTL1_SHIFT) & (PT_ENTRIES - 1)) as usize;

    let l4e = unsafe { read_volatile(entries.add(l4idx)) };
    if (l4e & PFL2_PRESENT) == 0 {
        return -EINVAL;
    }
    entries = unsafe { phys_to_virt(l4e & PAGE_MASK) as *mut CULong };
    if entries.is_null() {
        return -EINVAL;
    }

    let l3e = unsafe { read_volatile(entries.add(l3idx)) };
    if (l3e & PFL2_PRESENT) == 0 {
        return -EINVAL;
    }
    entries = unsafe { phys_to_virt(l3e & PAGE_MASK) as *mut CULong };
    if entries.is_null() {
        return -EINVAL;
    }

    let l2p = unsafe { entries.add(l2idx) };
    let l2e = unsafe { read_volatile(l2p) };
    let mut clear_l2 = 0;
    let error = unsafe { x86_clear_pt_page_target_result(l2e, largepage, &mut clear_l2) };
    if error != 0 {
        return error;
    }

    if clear_l2 != 0 {
        unsafe {
            write_volatile(l2p, PTE_NULL);
        }
        return 0;
    }

    entries = unsafe { phys_to_virt(l2e & PAGE_MASK) as *mut CULong };
    if entries.is_null() {
        return -EINVAL;
    }

    unsafe {
        write_volatile(entries.add(l1idx), PTE_NULL);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_clear_page(pt: *mut c_void, virt: *mut c_void) -> CInt {
    unsafe {
        x86_pt_clear_page_result(
            pt,
            x86_page_table_init_pt_bridge(),
            virt as CULong,
            0,
            Some(x86_pt_phys_to_virt_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_clear_large_page(pt: *mut c_void, virt: *mut c_void) -> CInt {
    unsafe {
        x86_pt_clear_page_result(
            pt,
            x86_page_table_init_pt_bridge(),
            virt as CULong,
            1,
            Some(x86_pt_phys_to_virt_bridge),
        )
    }
}

#[no_mangle]
pub extern "C" fn x86_visit_pte_action_result(
    entry: CULong,
    skip_null: i32,
    start: CULong,
    end: CULong,
    base: CULong,
    level_size: CULong,
    target_shift: i32,
    pgshift: i32,
    size_flag: CULong,
    direct_requires_size: i32,
    direct_enabled: i32,
    can_allocate: i32,
) -> i32 {
    let is_null = entry == PTE_NULL;
    let is_large = size_flag != 0 && (entry & size_flag) != 0;
    let full_cover = start <= base && (base.wrapping_add(level_size) <= end || end == 0);
    let pgshift_match = pgshift == 0 || pgshift == target_shift;

    if is_null {
        if skip_null != 0 {
            return X86_VISIT_PTE_SKIP;
        }
        if direct_enabled != 0 && direct_requires_size == 0 && full_cover && pgshift_match {
            return X86_VISIT_PTE_DIRECT;
        }
        return if can_allocate != 0 {
            X86_VISIT_PTE_ALLOC_AND_WALK
        } else {
            X86_VISIT_PTE_SKIP
        };
    }

    if direct_enabled != 0 && (direct_requires_size == 0 || is_large) && full_cover && pgshift_match
    {
        return X86_VISIT_PTE_DIRECT;
    }

    if is_large {
        X86_VISIT_PTE_SPLIT_ERROR
    } else {
        X86_VISIT_PTE_WALK
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_pte_leaf_result(
    visitor_arg: *mut c_void,
    root_pt: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    skip_null: CInt,
    level_shift: CInt,
    visitor_fn: Option<X86VisitPteFn>,
) -> CInt {
    if ptep.is_null() {
        return -EINVAL;
    }

    if unsafe { read_volatile(ptep) } == PTE_NULL && skip_null != 0 {
        return 0;
    }

    let Some(visitor) = visitor_fn else {
        return -EINVAL;
    };

    unsafe { visitor(visitor_arg, root_pt, ptep, base as *mut c_void, level_shift) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_pte_level_result(
    visitor_arg: *mut c_void,
    root_pt: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    skip_null: CInt,
    retry_skip_null: CInt,
    pgshift: CInt,
    level_size: CULong,
    target_shift: CInt,
    size_flag: CULong,
    direct_requires_size: CInt,
    direct_enabled: CInt,
    can_allocate: CInt,
    pdir_attr: CULong,
    alloc_fn: Option<X86PtAllocPagesFn>,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
    child_walk_fn: Option<X86VisitPteWalkFn>,
    child_args: *mut c_void,
    visitor_fn: Option<X86VisitPteFn>,
    log_fn: Option<X86VisitPteLogFn>,
) -> CInt {
    if ptep.is_null() {
        return -EINVAL;
    }

    let Some(visitor) = visitor_fn else {
        return -EINVAL;
    };
    let Some(child_walk) = child_walk_fn else {
        return -EINVAL;
    };
    let Some(phys_to_virt) = phys_to_virt_fn else {
        return -EINVAL;
    };

    let current = unsafe { read_volatile(ptep) };
    let mut action = x86_visit_pte_action_result(
        current,
        skip_null,
        start,
        end,
        base,
        level_size,
        target_shift,
        pgshift,
        size_flag,
        direct_requires_size,
        direct_enabled,
        can_allocate,
    );
    if action == X86_VISIT_PTE_SKIP {
        return 0;
    }

    if action == X86_VISIT_PTE_DIRECT {
        let error = unsafe {
            visitor(
                visitor_arg,
                root_pt,
                ptep,
                base as *mut c_void,
                target_shift,
            )
        };
        if error != -E2BIG {
            return error;
        }
        action = x86_visit_pte_action_result(
            unsafe { read_volatile(ptep) },
            retry_skip_null,
            start,
            end,
            base,
            level_size,
            target_shift,
            pgshift,
            size_flag,
            direct_requires_size,
            0,
            can_allocate,
        );
    }

    if action == X86_VISIT_PTE_SPLIT_ERROR {
        if let Some(log) = log_fn {
            unsafe { log(X86_VISIT_PTE_LOG_SPLIT, target_shift) };
        }
        return -ENOMEM;
    }

    let child_pt = if action == X86_VISIT_PTE_ALLOC_AND_WALK {
        let (Some(alloc), Some(virt_to_phys)) = (alloc_fn, virt_to_phys_fn) else {
            return -EINVAL;
        };
        let newpt = unsafe { alloc(1, IHK_MC_AP_NOWAIT) };
        if newpt.is_null() {
            return -ENOMEM;
        }
        unsafe { x86_pte_store_result(ptep, virt_to_phys(newpt) | pdir_attr) };
        newpt
    } else {
        unsafe { phys_to_virt(read_volatile(ptep) & PT_PHYSMASK) }
    };

    unsafe { child_walk(child_pt, base, start, end, child_args) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_pte_root_result(
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    skip_null: CInt,
    can_allocate: CInt,
    pdir_attr: CULong,
    alloc_fn: Option<X86PtAllocPagesFn>,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
    child_walk_fn: Option<X86VisitPteWalkFn>,
    child_args: *mut c_void,
) -> CInt {
    if ptep.is_null() {
        return -EINVAL;
    }

    let current = unsafe { read_volatile(ptep) };
    if current == PTE_NULL && skip_null != 0 {
        return 0;
    }

    let Some(child_walk) = child_walk_fn else {
        return -EINVAL;
    };
    let child_pt = if current == PTE_NULL {
        if can_allocate == 0 {
            return 0;
        }
        let (Some(alloc), Some(virt_to_phys)) = (alloc_fn, virt_to_phys_fn) else {
            return -EINVAL;
        };
        let newpt = unsafe { alloc(1, IHK_MC_AP_NOWAIT) };
        if newpt.is_null() {
            return -ENOMEM;
        }
        unsafe { x86_pte_store_result(ptep, virt_to_phys(newpt) | pdir_attr) };
        newpt
    } else {
        let Some(phys_to_virt) = phys_to_virt_fn else {
            return -EINVAL;
        };
        unsafe { phys_to_virt(current & PT_PHYSMASK) }
    };

    unsafe { child_walk(child_pt, base, start, end, child_args) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_pte_range_dispatch_result(
    pt: *mut c_void,
    start: CULong,
    end: CULong,
    args: *mut c_void,
    walk_fn: Option<X86VisitPteWalkFn>,
) -> CInt {
    let Some(walk) = walk_fn else {
        return -EINVAL;
    };

    unsafe { walk(pt, 0, start, end, args) }
}

#[no_mangle]
pub extern "C" fn x86_clear_range_validate_result(
    start: CULong,
    end: CULong,
    user_start: CULong,
    user_end: CULong,
) -> i32 {
    if start < user_start || user_end < end || end <= start {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn x86_clear_range_free_physical_result(
    free_physical: i32,
    is_dev_file: i32,
    is_premap: i32,
    is_straight_main: i32,
) -> i32 {
    (free_physical != 0 && is_dev_file == 0 && is_premap == 0 && is_straight_main == 0) as i32
}

#[no_mangle]
pub extern "C" fn x86_clear_range_entry_action_result(
    entry: CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    level_size: CULong,
    size_flag: CULong,
) -> i32 {
    if entry == PTE_NULL {
        return X86_CLEAR_RANGE_SKIP;
    }

    if (entry & size_flag) != 0 {
        if base < start || end < base.wrapping_add(level_size) {
            return X86_CLEAR_RANGE_SPLIT_ERROR;
        }
        return X86_CLEAR_RANGE_CLEAR_LARGE;
    }

    X86_CLEAR_RANGE_WALK
}

#[no_mangle]
pub unsafe extern "C" fn x86_clear_range_old_entry_result(
    entry: CULong,
    pgsize: CULong,
    physp: *mut CULong,
    fileoffp: *mut i32,
    dirtyp: *mut i32,
) {
    if !physp.is_null() {
        unsafe {
            *physp = entry & PT_PHYSMASK;
        }
    }
    if !fileoffp.is_null() {
        unsafe {
            *fileoffp = ((entry & x86_fileoff_flag(pgsize)) != 0) as i32;
        }
    }
    if !dirtyp.is_null() {
        unsafe {
            *dirtyp = ((entry & 0x40) != 0) as i32;
        }
    }
}

#[no_mangle]
pub extern "C" fn x86_clear_range_old_action_result(
    is_fileoff: i32,
    free_physical: i32,
    has_page: i32,
    page_in_memobj: i32,
    entry_dirty: i32,
    has_memobj: i32,
    memobj_no_flush: i32,
    memobj_xpmem: i32,
) -> i32 {
    if is_fileoff != 0 {
        return 0;
    }

    let mut action = 0;

    if has_page != 0
        && page_in_memobj != 0
        && entry_dirty != 0
        && has_memobj != 0
        && memobj_no_flush == 0
    {
        action |= X86_CLEAR_OLD_FLUSH_MEMOBJ;
    }

    if free_physical != 0 {
        if has_page == 0 {
            if has_memobj == 0 || memobj_xpmem == 0 {
                action |= X86_CLEAR_OLD_FREE_ANON;
            } else {
                action |= X86_CLEAR_OLD_XPMEM_KEEP;
            }
        } else {
            action |= X86_CLEAR_OLD_TRY_UNMAP;
        }
    }

    action
}

#[no_mangle]
pub unsafe extern "C" fn x86_remote_flush_tlb_add_addr_result(
    vm: *mut c_void,
    addr_array: *mut CULong,
    nr_addrp: *mut CInt,
    max_nr_addr: CInt,
    addr: CULong,
    cpu_id: CInt,
    flush_fn: Option<X86ClearRemoteFlushFn>,
) -> CInt {
    if addr_array.is_null() || nr_addrp.is_null() || max_nr_addr <= 0 {
        return -EINVAL;
    }

    let nr_addr = *nr_addrp;
    if nr_addr < 0 {
        return -EINVAL;
    }

    if nr_addr < max_nr_addr {
        *addr_array.add(nr_addr as usize) = addr;
        *nr_addrp = nr_addr + 1;
        return 0;
    }

    let Some(flush) = flush_fn else {
        return -EINVAL;
    };

    flush(vm, addr_array, nr_addr, cpu_id);
    *addr_array = addr;
    *nr_addrp = 1;
    1
}

#[no_mangle]
pub unsafe extern "C" fn x86_clear_range_old_effects_result(
    old_action: CInt,
    is_fileoff: CInt,
    free_physical: CInt,
    memobj: *mut c_void,
    page: *mut c_void,
    phys: CULong,
    base: CULong,
    pgsize: CULong,
    flush_fn: Option<X86ClearFlushMemobjFn>,
    phys_to_virt_fn: Option<X86ClearPhysToVirtFn>,
    free_pages_fn: Option<X86ClearFreePagesFn>,
    page_unmap_fn: Option<X86ClearPageUnmapFn>,
    rss_sub_fn: Option<X86ClearRssSubFn>,
    memobj_rss_sub_fn: Option<X86ClearMemobjRssSubFn>,
    log_fn: Option<X86ClearEffectLogFn>,
) -> CInt {
    if pgsize == 0 {
        return -EINVAL;
    }

    if (old_action & X86_CLEAR_OLD_FLUSH_MEMOBJ) != 0 {
        let Some(flush) = flush_fn else {
            return -EINVAL;
        };
        flush(memobj, phys, pgsize);
        if let Some(log) = log_fn {
            log(X86_CLEAR_EFFECT_FLUSH_MEMOBJ, base, phys, pgsize);
        }
    }

    if is_fileoff != 0 || free_physical == 0 {
        return 0;
    }

    let nr_pages = (pgsize >> PTL1_SHIFT) as CInt;

    if (old_action & X86_CLEAR_OLD_FREE_ANON) != 0 {
        let (Some(phys_to_virt), Some(free_pages), Some(rss_sub)) =
            (phys_to_virt_fn, free_pages_fn, rss_sub_fn)
        else {
            return -EINVAL;
        };
        free_pages(phys_to_virt(phys), nr_pages);
        rss_sub(pgsize, pgsize);
        if let Some(log) = log_fn {
            log(X86_CLEAR_EFFECT_FREE_ANON, base, phys, pgsize);
        }
    } else if (old_action & X86_CLEAR_OLD_XPMEM_KEEP) != 0 {
        if let Some(log) = log_fn {
            log(X86_CLEAR_EFFECT_XPMEM_KEEP, base, phys, pgsize);
        }
    } else if (old_action & X86_CLEAR_OLD_TRY_UNMAP) != 0 {
        let (Some(page_unmap), Some(phys_to_virt), Some(free_pages), Some(memobj_rss_sub)) = (
            page_unmap_fn,
            phys_to_virt_fn,
            free_pages_fn,
            memobj_rss_sub_fn,
        ) else {
            return -EINVAL;
        };

        if !page.is_null() && page_unmap(page) != 0 {
            free_pages(phys_to_virt(phys), nr_pages);
            memobj_rss_sub(memobj, pgsize, pgsize);
            if let Some(log) = log_fn {
                log(X86_CLEAR_EFFECT_FREE_UNMAPPED, base, phys, pgsize);
            }
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_clear_range_child_table_result(
    ptep: *mut CULong,
    pt: *mut c_void,
    start: CULong,
    base: CULong,
    end: CULong,
    level_size: CULong,
    enabled: CInt,
    vm: *mut c_void,
    addr_array: *mut CULong,
    nr_addrp: *mut CInt,
    max_nr_addr: CInt,
    cpu_id: CInt,
    flush_fn: Option<X86ClearRemoteFlushFn>,
    free_pages_fn: Option<X86PtFreePagesFn>,
    log_fn: Option<X86ClearEffectLogFn>,
) -> CInt {
    if enabled == 0 || !(start <= base && base.wrapping_add(level_size) <= end) {
        return 0;
    }
    if ptep.is_null() || pt.is_null() || level_size == 0 {
        return -EINVAL;
    }

    let Some(free_pages) = free_pages_fn else {
        return -EINVAL;
    };

    x86_pte_store_result(ptep, PTE_NULL);
    let rc = x86_remote_flush_tlb_add_addr_result(
        vm,
        addr_array,
        nr_addrp,
        max_nr_addr,
        base,
        cpu_id,
        flush_fn,
    );
    if rc < 0 {
        return rc;
    }

    free_pages(pt, 1);
    if let Some(log) = log_fn {
        log(X86_CLEAR_EFFECT_CHILD_FREE, base, 0, level_size);
    }
    1
}

unsafe fn x86_clear_range_clear_entry_effects(
    args: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    pgsize: CULong,
    vm: *mut c_void,
    addr_array: *mut CULong,
    nr_addrp: *mut CInt,
    max_nr_addr: CInt,
    cpu_id: CInt,
    free_physical: CInt,
    memobj: *mut c_void,
    old_action_fn: Option<X86ClearOldActionFn>,
    flush_fn: Option<X86ClearRemoteFlushFn>,
    flush_memobj_fn: Option<X86ClearFlushMemobjFn>,
    phys_to_virt_fn: Option<X86ClearPhysToVirtFn>,
    free_pages_fn: Option<X86ClearFreePagesFn>,
    page_unmap_fn: Option<X86ClearPageUnmapFn>,
    rss_sub_fn: Option<X86ClearRssSubFn>,
    memobj_rss_sub_fn: Option<X86ClearMemobjRssSubFn>,
    effect_log_fn: Option<X86ClearEffectLogFn>,
) -> CInt {
    if ptep.is_null() || pgsize == 0 {
        return -EINVAL;
    }
    let Some(old_action) = old_action_fn else {
        return -EINVAL;
    };

    let old = unsafe { x86_pte_clear_result(ptep) };
    let _ = unsafe {
        x86_remote_flush_tlb_add_addr_result(
            vm,
            addr_array,
            nr_addrp,
            max_nr_addr,
            base,
            cpu_id,
            flush_fn,
        )
    };

    let mut phys: CULong = 0;
    let mut page: *mut c_void = core::ptr::null_mut();
    let mut is_fileoff: CInt = 0;
    let old_action =
        unsafe { old_action(args, old, pgsize, &mut phys, &mut page, &mut is_fileoff) };
    if old_action < 0 {
        return old_action;
    }

    unsafe {
        x86_clear_range_old_effects_result(
            old_action,
            is_fileoff,
            free_physical,
            memobj,
            page,
            phys,
            base,
            pgsize,
            flush_memobj_fn,
            phys_to_virt_fn,
            free_pages_fn,
            page_unmap_fn,
            rss_sub_fn,
            memobj_rss_sub_fn,
            effect_log_fn,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_clear_range_leaf_body_result(
    args: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    _start: CULong,
    _end: CULong,
    vm: *mut c_void,
    addr_array: *mut CULong,
    nr_addrp: *mut CInt,
    max_nr_addr: CInt,
    cpu_id: CInt,
    free_physical: CInt,
    memobj: *mut c_void,
    old_action_fn: Option<X86ClearOldActionFn>,
    flush_fn: Option<X86ClearRemoteFlushFn>,
    flush_memobj_fn: Option<X86ClearFlushMemobjFn>,
    phys_to_virt_fn: Option<X86ClearPhysToVirtFn>,
    free_pages_fn: Option<X86ClearFreePagesFn>,
    page_unmap_fn: Option<X86ClearPageUnmapFn>,
    rss_sub_fn: Option<X86ClearRssSubFn>,
    memobj_rss_sub_fn: Option<X86ClearMemobjRssSubFn>,
    effect_log_fn: Option<X86ClearEffectLogFn>,
) -> CInt {
    if ptep.is_null() {
        return -EINVAL;
    }
    if unsafe { *ptep } == PTE_NULL {
        return -ENOENT;
    }

    unsafe {
        x86_clear_range_clear_entry_effects(
            args,
            ptep,
            base,
            PTL1_SIZE,
            vm,
            addr_array,
            nr_addrp,
            max_nr_addr,
            cpu_id,
            free_physical,
            memobj,
            old_action_fn,
            flush_fn,
            flush_memobj_fn,
            phys_to_virt_fn,
            free_pages_fn,
            page_unmap_fn,
            rss_sub_fn,
            memobj_rss_sub_fn,
            effect_log_fn,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_clear_range_level_body_result(
    args: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    level_shift: CInt,
    level_size: CULong,
    size_flag: CULong,
    child_teardown_enabled: CInt,
    vm: *mut c_void,
    addr_array: *mut CULong,
    nr_addrp: *mut CInt,
    max_nr_addr: CInt,
    cpu_id: CInt,
    free_physical: CInt,
    memobj: *mut c_void,
    old_action_fn: Option<X86ClearOldActionFn>,
    phys_to_virt_fn: Option<X86ClearPhysToVirtFn>,
    child_walk_fn: Option<X86ClearChildWalkFn>,
    flush_fn: Option<X86ClearRemoteFlushFn>,
    pt_free_pages_fn: Option<X86PtFreePagesFn>,
    flush_memobj_fn: Option<X86ClearFlushMemobjFn>,
    free_pages_fn: Option<X86ClearFreePagesFn>,
    page_unmap_fn: Option<X86ClearPageUnmapFn>,
    rss_sub_fn: Option<X86ClearRssSubFn>,
    memobj_rss_sub_fn: Option<X86ClearMemobjRssSubFn>,
    range_log_fn: Option<X86ClearRangeLogFn>,
    effect_log_fn: Option<X86ClearEffectLogFn>,
) -> CInt {
    if ptep.is_null() {
        return -EINVAL;
    }

    let action = x86_clear_range_entry_action_result(
        unsafe { *ptep },
        base,
        start,
        end,
        level_size,
        size_flag,
    );
    if action == X86_CLEAR_RANGE_SKIP {
        return -ENOENT;
    }
    if action == X86_CLEAR_RANGE_SPLIT_ERROR {
        if let Some(log) = range_log_fn {
            unsafe {
                log(
                    X86_CLEAR_RANGE_LOG_SPLIT,
                    args,
                    ptep,
                    base,
                    start,
                    end,
                    -EINVAL,
                    level_shift,
                    0,
                );
            }
        }
        return -EINVAL;
    }
    if action == X86_CLEAR_RANGE_CLEAR_LARGE {
        let old = unsafe { *ptep };
        let ret = unsafe {
            x86_clear_range_clear_entry_effects(
                args,
                ptep,
                base,
                level_size,
                vm,
                addr_array,
                nr_addrp,
                max_nr_addr,
                cpu_id,
                free_physical,
                memobj,
                old_action_fn,
                flush_fn,
                flush_memobj_fn,
                phys_to_virt_fn,
                free_pages_fn,
                page_unmap_fn,
                rss_sub_fn,
                memobj_rss_sub_fn,
                effect_log_fn,
            )
        };
        if level_shift == PTL3_SHIFT {
            if let Some(log) = range_log_fn {
                let mut phys: CULong = 0;
                unsafe {
                    x86_clear_range_old_entry_result(
                        old,
                        level_size,
                        &mut phys,
                        core::ptr::null_mut(),
                        core::ptr::null_mut(),
                    );
                    log(
                        X86_CLEAR_RANGE_LOG_LARGE_PHYS,
                        args,
                        ptep,
                        base,
                        start,
                        end,
                        ret,
                        level_shift,
                        phys,
                    );
                }
            }
        }
        return ret;
    }

    let (Some(phys_to_virt), Some(child_walk)) = (phys_to_virt_fn, child_walk_fn) else {
        return -EINVAL;
    };
    let child_pt = unsafe { phys_to_virt(*ptep & PT_PHYSMASK) };
    if child_pt.is_null() {
        return -EINVAL;
    }

    let error = unsafe { child_walk(child_pt, base, start, end, args) };
    if error != 0 && error != -ENOENT {
        return error;
    }

    let ret = unsafe {
        x86_clear_range_child_table_result(
            ptep,
            child_pt,
            start,
            base,
            end,
            level_size,
            child_teardown_enabled,
            vm,
            addr_array,
            nr_addrp,
            max_nr_addr,
            cpu_id,
            flush_fn,
            pt_free_pages_fn,
            effect_log_fn,
        )
    };
    if ret < 0 {
        return ret;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_clear_range_root_body_result(
    args: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    phys_to_virt_fn: Option<X86ClearPhysToVirtFn>,
    child_walk_fn: Option<X86ClearChildWalkFn>,
) -> CInt {
    if ptep.is_null() {
        return -EINVAL;
    }
    if unsafe { *ptep } == PTE_NULL {
        return -ENOENT;
    }

    let (Some(phys_to_virt), Some(child_walk)) = (phys_to_virt_fn, child_walk_fn) else {
        return -EINVAL;
    };
    let child_pt = unsafe { phys_to_virt(*ptep & PT_PHYSMASK) };
    if child_pt.is_null() {
        return -EINVAL;
    }

    unsafe { child_walk(child_pt, base, start, end, args) }
}

#[no_mangle]
pub extern "C" fn x86_change_attr_leaf_action_result(entry: CULong, fileoff_flag: CULong) -> i32 {
    if entry == PTE_NULL || (fileoff_flag != 0 && (entry & fileoff_flag) != 0) {
        return X86_CHANGE_ATTR_ENOENT;
    }

    X86_CHANGE_ATTR_APPLY
}

#[no_mangle]
pub extern "C" fn x86_change_attr_entry_action_result(
    entry: CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    level_size: CULong,
    size_flag: CULong,
    fileoff_flag: CULong,
) -> i32 {
    if entry == PTE_NULL || (fileoff_flag != 0 && (entry & fileoff_flag) != 0) {
        return X86_CHANGE_ATTR_ENOENT;
    }

    if size_flag != 0 && (entry & size_flag) != 0 {
        if base < start || end < base.wrapping_add(level_size) {
            return X86_CHANGE_ATTR_SPLIT_ERROR;
        }
        return X86_CHANGE_ATTR_APPLY;
    }

    X86_CHANGE_ATTR_WALK
}

unsafe fn x86_pt_change_attr_l1(
    ptep: *mut CULong,
    _base: CULong,
    _start: CULong,
    _end: CULong,
    clrpte: CULong,
    setpte: CULong,
    _phys_to_virt: X86PtPhysToVirtFn,
) -> i32 {
    let entry = unsafe { read_volatile(ptep) };
    let action = x86_change_attr_leaf_action_result(entry, PFL_FILEOFF);

    if action == X86_CHANGE_ATTR_ENOENT {
        return -ENOENT;
    }

    unsafe {
        x86_pte_apply_attr_result(ptep, clrpte, setpte);
    }
    0
}

unsafe fn x86_pt_change_attr_l2(
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    clrpte: CULong,
    setpte: CULong,
    phys_to_virt: X86PtPhysToVirtFn,
) -> i32 {
    let entry = unsafe { read_volatile(ptep) };
    let action = x86_change_attr_entry_action_result(
        entry,
        base,
        start,
        end,
        PTL2_SIZE,
        PFL2_SIZE,
        PFL_FILEOFF,
    );

    if action == X86_CHANGE_ATTR_ENOENT {
        return -ENOENT;
    }
    if action == X86_CHANGE_ATTR_SPLIT_ERROR {
        return -EINVAL;
    }
    if action == X86_CHANGE_ATTR_APPLY {
        unsafe {
            x86_pte_apply_attr_result(ptep, clrpte, setpte);
        }
        return 0;
    }

    let pt = unsafe { phys_to_virt(entry & PT_PHYSMASK) as *mut CULong };
    if pt.is_null() {
        return -EINVAL;
    }
    unsafe {
        x86_pt_change_attr_walk(
            pt,
            base,
            start,
            end,
            PTL2_SIZE,
            PTL1_SHIFT,
            clrpte,
            setpte,
            phys_to_virt,
            x86_pt_change_attr_l1,
        )
    }
}

unsafe fn x86_pt_change_attr_l3(
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    clrpte: CULong,
    setpte: CULong,
    phys_to_virt: X86PtPhysToVirtFn,
) -> i32 {
    let entry = unsafe { read_volatile(ptep) };
    let action = x86_change_attr_entry_action_result(
        entry,
        base,
        start,
        end,
        PTL3_SIZE,
        PFL2_SIZE,
        PFL_FILEOFF,
    );

    if action == X86_CHANGE_ATTR_ENOENT {
        return -ENOENT;
    }
    if action == X86_CHANGE_ATTR_SPLIT_ERROR {
        return -EINVAL;
    }
    if action == X86_CHANGE_ATTR_APPLY {
        unsafe {
            x86_pte_apply_attr_result(ptep, clrpte, setpte);
        }
        return 0;
    }

    let pt = unsafe { phys_to_virt(entry & PT_PHYSMASK) as *mut CULong };
    if pt.is_null() {
        return -EINVAL;
    }
    unsafe {
        x86_pt_change_attr_walk(
            pt,
            base,
            start,
            end,
            PTL3_SIZE,
            PTL2_SHIFT,
            clrpte,
            setpte,
            phys_to_virt,
            x86_pt_change_attr_l2,
        )
    }
}

unsafe fn x86_pt_change_attr_l4(
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    clrpte: CULong,
    setpte: CULong,
    phys_to_virt: X86PtPhysToVirtFn,
) -> i32 {
    let entry = unsafe { read_volatile(ptep) };
    let action = x86_change_attr_entry_action_result(entry, base, start, end, 0, 0, 0);

    if action == X86_CHANGE_ATTR_ENOENT {
        return -ENOENT;
    }

    let pt = unsafe { phys_to_virt(entry & PT_PHYSMASK) as *mut CULong };
    if pt.is_null() {
        return -EINVAL;
    }
    unsafe {
        x86_pt_change_attr_walk(
            pt,
            base,
            start,
            end,
            PTL4_SIZE,
            PTL3_SHIFT,
            clrpte,
            setpte,
            phys_to_virt,
            x86_pt_change_attr_l3,
        )
    }
}

type X86PtChangeAttrLevelFn =
    unsafe fn(*mut CULong, CULong, CULong, CULong, CULong, CULong, X86PtPhysToVirtFn) -> i32;

unsafe fn x86_pt_change_attr_walk(
    pt: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    span: CULong,
    shift: i32,
    clrpte: CULong,
    setpte: CULong,
    phys_to_virt: X86PtPhysToVirtFn,
    visit: X86PtChangeAttrLevelFn,
) -> i32 {
    if pt.is_null() {
        return -ENOENT;
    }

    let mut six = 0;
    let mut eix = 0;
    unsafe {
        x86_walk_bounds_result(start, end, base, span, shift, &mut six, &mut eix);
    }

    let mut ret = -ENOENT;
    let mut i = six;
    while i < eix {
        let ptep = unsafe { pt.add(i as usize) };
        let off = (i as CULong) << (shift as u32);
        let error = unsafe {
            visit(
                ptep,
                base.wrapping_add(off),
                start,
                end,
                clrpte,
                setpte,
                phys_to_virt,
            )
        };
        if unsafe { x86_walk_step_result(ret, error, &mut ret) } != 0 {
            break;
        }
        i += 1;
    }

    ret
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_change_attr_range_result(
    pt: *mut c_void,
    start: CULong,
    end: CULong,
    clrpte: CULong,
    setpte: CULong,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
) -> i32 {
    let Some(phys_to_virt) = phys_to_virt_fn else {
        return -EINVAL;
    };

    unsafe {
        x86_pt_change_attr_walk(
            pt as *mut CULong,
            0,
            start,
            end,
            0,
            PTL4_SHIFT,
            clrpte,
            setpte,
            phys_to_virt,
            x86_pt_change_attr_l4,
        )
    }
}

#[no_mangle]
pub extern "C" fn x86_set_range_leaf_action_result(entry: CULong) -> i32 {
    if entry == PTE_NULL {
        X86_SET_RANGE_APPLY
    } else {
        X86_SET_RANGE_BUSY
    }
}

#[no_mangle]
pub extern "C" fn x86_set_range_entry_action_result(
    entry: CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    diff: CULong,
    pgshift: i32,
    target_shift: i32,
    level_size: CULong,
    size_flag: CULong,
    direct_enabled: i32,
) -> i32 {
    let full_cover = start <= base && base.wrapping_add(level_size) <= end;
    let diff_aligned = (diff & level_size.wrapping_sub(1)) == 0;
    let pgshift_match = pgshift == 0 || pgshift == target_shift;

    if entry == PTE_NULL {
        if direct_enabled != 0 && full_cover && diff_aligned && pgshift_match {
            return X86_SET_RANGE_MAP_LARGE;
        }
        return X86_SET_RANGE_ALLOC_AND_WALK;
    }

    if size_flag != 0 && (entry & size_flag) != 0 {
        return X86_SET_RANGE_BUSY;
    }

    X86_SET_RANGE_WALK
}

#[no_mangle]
pub unsafe extern "C" fn x86_set_range_map_entry_result(
    phys_base: CULong,
    base: CULong,
    start: CULong,
    attr: CULong,
    level_shift: i32,
    attr_mask: CULong,
    physp: *mut CULong,
    entryp: *mut CULong,
) -> i32 {
    let phys = phys_base.wrapping_add(base.wrapping_sub(start));
    let entry = if level_shift == PTL1_SHIFT {
        phys | x86_attr_to_l1attr_result(attr, attr_mask)
    } else if level_shift == PTL2_SHIFT {
        phys | x86_attr_to_l2attr_result(attr | PTATTR_LARGEPAGE, attr_mask)
    } else if level_shift == PTL3_SHIFT {
        phys | x86_attr_to_l3attr_result(attr | PTATTR_LARGEPAGE, attr_mask)
    } else {
        return -EINVAL;
    };

    if !physp.is_null() {
        unsafe {
            *physp = phys;
        }
    }
    if !entryp.is_null() {
        unsafe {
            *entryp = entry;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_clear_range_top_result(
    pt: *mut c_void,
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    user_start: CULong,
    user_end: CULong,
    requested_free: CInt,
    is_dev_file: CInt,
    is_premap: CInt,
    is_straight_main: CInt,
    memobj: *mut c_void,
    addr_slot: *mut *mut CULong,
    nr_addrp: *mut CInt,
    max_nr_addrp: *mut CInt,
    free_physicalp: *mut CInt,
    memobj_slot: *mut *mut c_void,
    vm_slot: *mut *mut c_void,
    tlb_array_pages: CInt,
    page_size: CULong,
    args: *mut c_void,
    alloc_fn: Option<X86PtAllocPagesFn>,
    free_fn: Option<X86PtFreePagesFn>,
    walk_fn: Option<X86RangeTopWalkFn>,
    flush_fn: Option<X86ClearRemoteFlushFn>,
    cpu_id: CInt,
    log_fn: Option<X86ClearRangeTopLogFn>,
) -> CInt {
    let (Some(alloc), Some(free_pages), Some(walk), Some(flush)) =
        (alloc_fn, free_fn, walk_fn, flush_fn)
    else {
        return -EINVAL;
    };
    if addr_slot.is_null()
        || nr_addrp.is_null()
        || max_nr_addrp.is_null()
        || free_physicalp.is_null()
        || memobj_slot.is_null()
        || vm_slot.is_null()
        || args.is_null()
        || tlb_array_pages <= 0
        || page_size < core::mem::size_of::<CULong>() as CULong
    {
        return -EINVAL;
    }

    if x86_clear_range_validate_result(start, end, user_start, user_end) != 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(X86_CLEAR_TOP_LOG_INVALID, pt, start, end, requested_free);
            }
        }
        return -EINVAL;
    }

    let addr = unsafe { alloc(tlb_array_pages, IHK_MC_AP_CRITICAL) }.cast::<CULong>();
    if addr.is_null() {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    X86_CLEAR_TOP_LOG_ALLOC_FAILED,
                    pt,
                    start,
                    end,
                    requested_free,
                );
            }
        }
        return -ENOMEM;
    }

    let max_nr_addr = ((tlb_array_pages as CULong) * page_size
        / core::mem::size_of::<CULong>() as CULong) as CInt;
    let free_physical = x86_clear_range_free_physical_result(
        requested_free,
        is_dev_file,
        is_premap,
        is_straight_main,
    );

    unsafe {
        *addr_slot = addr;
        *nr_addrp = 0;
        *max_nr_addrp = max_nr_addr;
        *free_physicalp = free_physical;
        *memobj_slot = memobj;
        *vm_slot = vm;
    }

    let error = unsafe { walk(pt, 0, start, end, args) };
    let nr_addr = unsafe { *nr_addrp };
    if nr_addr > 0 {
        unsafe {
            flush(vm, addr, nr_addr, cpu_id);
        }
    }
    unsafe {
        free_pages(addr.cast::<c_void>(), tlb_array_pages);
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn x86_set_range_conflict_result(
    pt: *mut c_void,
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    base: CULong,
    current: CULong,
    level_shift: CInt,
    free_physical: CInt,
    clear_fn: Option<X86SetRangeClearFn>,
    log_fn: Option<X86SetRangeLogFn>,
) -> i32 {
    let Some(clear) = clear_fn else {
        return -EINVAL;
    };

    if let Some(log) = log_fn {
        unsafe {
            log(
                X86_SET_RANGE_LOG_BUSY,
                level_shift,
                base,
                start,
                end,
                -EBUSY,
                current,
                start,
                base,
                end,
                free_physical,
            );
        }
    }
    unsafe {
        clear(pt, vm, start, base, free_physical, core::ptr::null_mut());
    }

    -EBUSY
}

#[no_mangle]
pub unsafe extern "C" fn x86_set_range_alloc_failed_result(
    pt: *mut c_void,
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    base: CULong,
    current: CULong,
    level_shift: CInt,
    free_physical: CInt,
    clear_fn: Option<X86SetRangeClearFn>,
    log_fn: Option<X86SetRangeLogFn>,
) -> i32 {
    let Some(clear) = clear_fn else {
        return -EINVAL;
    };

    if let Some(log) = log_fn {
        unsafe {
            log(
                X86_SET_RANGE_LOG_ALLOC_FAILED,
                level_shift,
                base,
                start,
                end,
                -ENOMEM,
                current,
                start,
                base,
                end,
                free_physical,
            );
        }
    }
    unsafe {
        clear(pt, vm, start, base, free_physical, core::ptr::null_mut());
    }

    -ENOMEM
}

#[no_mangle]
pub unsafe extern "C" fn x86_set_range_walk_failed_result(
    error: CInt,
    base: CULong,
    start: CULong,
    end: CULong,
    current: CULong,
    level_shift: CInt,
    log_fn: Option<X86SetRangeLogFn>,
) -> i32 {
    if error != 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    X86_SET_RANGE_LOG_WALK_FAILED,
                    level_shift,
                    base,
                    start,
                    end,
                    error,
                    current,
                    start,
                    base,
                    end,
                    error,
                );
            }
        }
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn x86_set_range_map_effect_result(
    phys_base: CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    attr: CULong,
    level_shift: CInt,
    attr_mask: CULong,
    pgsize: CULong,
    ptep: *mut CULong,
    range: *mut c_void,
    log_large: CInt,
    rss_add_fn: Option<X86SetRangeRssAddFn>,
    log_fn: Option<X86SetRangeLogFn>,
) -> i32 {
    let Some(rss_add) = rss_add_fn else {
        return -EINVAL;
    };
    if ptep.is_null() || pgsize == 0 {
        return -EINVAL;
    }

    let mut phys = 0;
    let mut entry = 0;
    let ret = unsafe {
        x86_set_range_map_entry_result(
            phys_base,
            base,
            start,
            attr,
            level_shift,
            attr_mask,
            &mut phys,
            &mut entry,
        )
    };
    if ret != 0 {
        return ret;
    }

    let ret = unsafe { x86_pte_store_result(ptep, entry) };
    if ret != 0 {
        return ret;
    }

    if log_large != 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    X86_SET_RANGE_LOG_MAP_LARGE,
                    level_shift,
                    base,
                    start,
                    end,
                    0,
                    *ptep,
                    phys,
                    pgsize,
                    pgsize,
                    0,
                );
            }
        }
    }

    let rss_called = unsafe { rss_add(range, phys, pgsize, pgsize) };
    if let Some(log) = log_fn {
        unsafe {
            log(
                if rss_called != 0 {
                    X86_SET_RANGE_LOG_RSS_ADD
                } else {
                    X86_SET_RANGE_LOG_RSS_SKIP
                },
                level_shift,
                base,
                start,
                end,
                0,
                *ptep,
                phys,
                pgsize,
                pgsize,
                rss_called,
            );
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_set_range_leaf_body_result(
    _args: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    pt: *mut c_void,
    vm: *mut c_void,
    phys_base: CULong,
    attr: CULong,
    attr_mask: CULong,
    range: *mut c_void,
    clear_fn: Option<X86SetRangeClearFn>,
    rss_add_fn: Option<X86SetRangeRssAddFn>,
    log_fn: Option<X86SetRangeLogFn>,
) -> i32 {
    if ptep.is_null() {
        return -EINVAL;
    }

    let current = unsafe { *ptep };
    let action = x86_set_range_leaf_action_result(current);
    if action == X86_SET_RANGE_BUSY {
        return unsafe {
            x86_set_range_conflict_result(
                pt, vm, start, end, base, current, PTL1_SHIFT, 0, clear_fn, log_fn,
            )
        };
    }

    unsafe {
        x86_set_range_map_effect_result(
            phys_base, base, start, end, attr, PTL1_SHIFT, attr_mask, PTL1_SIZE, ptep, range, 0,
            rss_add_fn, log_fn,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_set_range_level_body_result(
    args: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    pt_root: *mut c_void,
    vm: *mut c_void,
    phys_base: CULong,
    attr: CULong,
    attr_mask: CULong,
    diff: CULong,
    pgshift: CInt,
    target_shift: CInt,
    level_size: CULong,
    size_flag: CULong,
    direct_enabled: CInt,
    pdir_attr: CULong,
    range: *mut c_void,
    alloc_fn: Option<X86PtAllocPagesFn>,
    free_fn: Option<X86PtFreePagesFn>,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
    child_walk_fn: Option<X86SetRangeChildWalkFn>,
    clear_fn: Option<X86SetRangeClearFn>,
    rss_add_fn: Option<X86SetRangeRssAddFn>,
    log_fn: Option<X86SetRangeLogFn>,
) -> i32 {
    let (Some(alloc), Some(free_pages), Some(virt_to_phys), Some(phys_to_virt), Some(child_walk)) = (
        alloc_fn,
        free_fn,
        virt_to_phys_fn,
        phys_to_virt_fn,
        child_walk_fn,
    ) else {
        return -EINVAL;
    };
    if ptep.is_null() {
        return -EINVAL;
    }

    let mut newpt: *mut c_void = core::ptr::null_mut();
    let child_pt: *mut c_void;
    let mut error: i32;
    let mut child_walk_failed = false;

    loop {
        let current = unsafe { *ptep };
        let action = x86_set_range_entry_action_result(
            current,
            base,
            start,
            end,
            diff,
            pgshift,
            target_shift,
            level_size,
            size_flag,
            direct_enabled,
        );

        if action == X86_SET_RANGE_ALLOC_AND_WALK {
            if newpt.is_null() {
                newpt = unsafe { x86_pt_alloc_zeroed_result(IHK_MC_AP_NOWAIT, Some(alloc)) };
                if newpt.is_null() {
                    error = unsafe {
                        x86_set_range_alloc_failed_result(
                            pt_root,
                            vm,
                            start,
                            end,
                            base,
                            current,
                            target_shift,
                            0,
                            clear_fn,
                            log_fn,
                        )
                    };
                    break;
                }
            }

            let entry = unsafe { virt_to_phys(newpt) } | pdir_attr;
            let old = unsafe { x86_pte_publish_table_result(ptep, entry) };
            if old != PTE_NULL {
                continue;
            }

            child_pt = newpt;
            newpt = core::ptr::null_mut();
            error = unsafe { child_walk(child_pt, base, start, end, args) };
            child_walk_failed = error != 0;
            break;
        } else if action == X86_SET_RANGE_MAP_LARGE {
            error = unsafe {
                x86_set_range_map_effect_result(
                    phys_base,
                    base,
                    start,
                    end,
                    attr,
                    target_shift,
                    attr_mask,
                    level_size,
                    ptep,
                    range,
                    1,
                    rss_add_fn,
                    log_fn,
                )
            };
            break;
        } else if action == X86_SET_RANGE_BUSY {
            error = unsafe {
                x86_set_range_conflict_result(
                    pt_root,
                    vm,
                    start,
                    end,
                    base,
                    current,
                    target_shift,
                    0,
                    clear_fn,
                    log_fn,
                )
            };
            break;
        } else {
            child_pt = unsafe { phys_to_virt(current & PT_PHYSMASK) };
            if child_pt.is_null() {
                error = -EINVAL;
                break;
            }
            error = unsafe { child_walk(child_pt, base, start, end, args) };
            child_walk_failed = error != 0;
            break;
        }
    }

    if child_walk_failed {
        error = unsafe {
            x86_set_range_walk_failed_result(error, base, start, end, *ptep, target_shift, log_fn)
        };
    }
    if !newpt.is_null() {
        unsafe {
            free_pages(newpt, 1);
        }
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn x86_set_range_top_result(
    pt: *mut c_void,
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    phys: CULong,
    attr: CInt,
    pgshift: CInt,
    range: *mut c_void,
    args: *mut c_void,
    args_ptp: *mut *mut c_void,
    args_physp: *mut CULong,
    args_attrp: *mut CInt,
    args_diffp: *mut CULong,
    args_vmp: *mut *mut c_void,
    args_pgshiftp: *mut CInt,
    args_rangep: *mut *mut c_void,
    walk_fn: Option<X86RangeTopWalkFn>,
    log_fn: Option<X86SetRangeLogFn>,
) -> CInt {
    let Some(walk) = walk_fn else {
        return -EINVAL;
    };
    if args.is_null()
        || args_ptp.is_null()
        || args_physp.is_null()
        || args_attrp.is_null()
        || args_diffp.is_null()
        || args_vmp.is_null()
        || args_pgshiftp.is_null()
        || args_rangep.is_null()
    {
        return -EINVAL;
    }

    unsafe {
        *args_ptp = pt;
        *args_physp = phys;
        *args_attrp = attr;
        *args_diffp = start ^ phys;
        *args_vmp = vm;
        *args_pgshiftp = pgshift;
        *args_rangep = range;
    }

    let error = unsafe { walk(pt, 0, start, end, args) };
    if error != 0 {
        unsafe { x86_set_range_walk_failed_result(error, 0, start, end, 0, 0, log_fn) }
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_pte_store_result(ptep: *mut CULong, entry: CULong) -> i32 {
    if ptep.is_null() {
        return -EINVAL;
    }

    unsafe {
        write_volatile(ptep, entry);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_pte_publish_table_result(ptep: *mut CULong, entry: CULong) -> CULong {
    if ptep.is_null() {
        return NOPHYS;
    }

    let atomic = unsafe { &*(ptep.cast::<AtomicU64>()) };
    match atomic.compare_exchange(PTE_NULL, entry, Ordering::SeqCst, Ordering::SeqCst) {
        Ok(old) | Err(old) => old,
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_pte_clear_result(ptep: *mut CULong) -> CULong {
    if ptep.is_null() {
        return NOPHYS;
    }

    let atomic = unsafe { &*(ptep.cast::<AtomicU64>()) };
    atomic.swap(PTE_NULL, Ordering::SeqCst)
}

#[no_mangle]
pub unsafe extern "C" fn x86_pte_apply_attr_result(
    ptep: *mut CULong,
    clrpte: CULong,
    setpte: CULong,
) -> CULong {
    if ptep.is_null() {
        return NOPHYS;
    }

    let entry = unsafe { *ptep };
    let updated = (entry & !clrpte) | setpte;
    unsafe {
        write_volatile(ptep, updated);
    }
    updated
}

#[no_mangle]
pub extern "C" fn x86_pt_kernel_lock_needed_result(virt: CULong) -> CInt {
    (virt >= KERNEL_BASE) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_alloc_zeroed_result(
    ap_flag: CInt,
    alloc_fn: Option<X86PtAllocPagesFn>,
) -> *mut c_void {
    let Some(alloc) = alloc_fn else {
        return core::ptr::null_mut();
    };

    let pt = unsafe { alloc(1, ap_flag) };
    if !pt.is_null() {
        unsafe {
            write_bytes(pt as *mut CULong, 0, PT_ENTRIES as usize);
        }
    }

    pt
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_get_pte_result(
    pt: *mut c_void,
    init_pt: *mut c_void,
    virt: CULong,
    attr: CULong,
    attr_mask: CULong,
    ap_flag: CInt,
    alloc_fn: Option<X86PtAllocPagesFn>,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
) -> *mut CULong {
    let Some(virt_to_phys) = virt_to_phys_fn else {
        return core::ptr::null_mut();
    };
    let Some(phys_to_virt) = phys_to_virt_fn else {
        return core::ptr::null_mut();
    };

    let mut entries = if pt.is_null() {
        init_pt as *mut CULong
    } else {
        pt as *mut CULong
    };
    if entries.is_null() {
        return core::ptr::null_mut();
    }

    let l4idx = ((virt >> PTL4_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l3idx = ((virt >> PTL3_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l2idx = ((virt >> PTL2_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l1idx = ((virt >> PTL1_SHIFT) & (PT_ENTRIES - 1)) as usize;

    let mut entryp = unsafe { entries.add(l4idx) };
    let mut entry = unsafe { read_volatile(entryp) };
    if (entry & PFL2_PRESENT) != 0 {
        entries = unsafe { phys_to_virt(entry & PAGE_MASK) as *mut CULong };
        if entries.is_null() {
            return core::ptr::null_mut();
        }
    } else {
        let newpt = unsafe { x86_pt_alloc_zeroed_result(ap_flag, alloc_fn) };
        if newpt.is_null() {
            return core::ptr::null_mut();
        }
        entry = unsafe { virt_to_phys(newpt) } | ((attr & attr_mask) | PFL2_PRESENT);
        unsafe {
            write_volatile(entryp, entry);
        }
        entries = newpt as *mut CULong;
    }

    entryp = unsafe { entries.add(l3idx) };
    entry = unsafe { read_volatile(entryp) };
    if (entry & PFL2_PRESENT) != 0 {
        entries = unsafe { phys_to_virt(entry & PAGE_MASK) as *mut CULong };
        if entries.is_null() {
            return core::ptr::null_mut();
        }
    } else {
        let newpt = unsafe { x86_pt_alloc_zeroed_result(ap_flag, alloc_fn) };
        if newpt.is_null() {
            return core::ptr::null_mut();
        }
        entry = unsafe { virt_to_phys(newpt) } | x86_attr_to_l3attr_result(attr, attr_mask);
        unsafe {
            write_volatile(entryp, entry);
        }
        entries = newpt as *mut CULong;
    }

    if (attr & PTATTR_LARGEPAGE) != 0 {
        return unsafe { entries.add(l2idx) };
    }

    entryp = unsafe { entries.add(l2idx) };
    entry = unsafe { read_volatile(entryp) };
    if (entry & PFL2_SIZE) != 0 {
        return core::ptr::null_mut();
    }
    if (entry & PFL2_PRESENT) != 0 {
        entries = unsafe { phys_to_virt(entry & PAGE_MASK) as *mut CULong };
        if entries.is_null() {
            return core::ptr::null_mut();
        }
    } else {
        let newpt = unsafe { x86_pt_alloc_zeroed_result(ap_flag, alloc_fn) };
        if newpt.is_null() {
            return core::ptr::null_mut();
        }
        entry = unsafe { virt_to_phys(newpt) }
            | x86_attr_to_l2attr_result(attr, attr_mask)
            | PFL2_PRESENT;
        unsafe {
            write_volatile(entryp, entry);
        }
        entries = newpt as *mut CULong;
    }

    unsafe { entries.add(l1idx) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_set_page_body_result(
    pt: *mut c_void,
    init_pt: *mut c_void,
    virt: CULong,
    mut phys: CULong,
    attr: CULong,
    attr_mask: CULong,
    alloc_fn: Option<X86PtAllocPagesFn>,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
    log_fn: Option<X86PtSetPageLogFn>,
) -> CInt {
    let Some(virt_to_phys) = virt_to_phys_fn else {
        return -ENOMEM;
    };
    let Some(phys_to_virt) = phys_to_virt_fn else {
        return -ENOMEM;
    };

    let mut entries = if pt.is_null() {
        init_pt as *mut CULong
    } else {
        pt as *mut CULong
    };
    if entries.is_null() {
        return -ENOMEM;
    }

    let ap_flag = if (attr & PTATTR_FOR_USER) != 0 {
        IHK_MC_AP_NOWAIT
    } else {
        IHK_MC_AP_CRITICAL
    };
    phys &= if (attr & PTATTR_LARGEPAGE) != 0 {
        LARGE_PAGE_MASK
    } else {
        PAGE_MASK
    };

    let l4idx = ((virt >> PTL4_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l3idx = ((virt >> PTL3_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l2idx = ((virt >> PTL2_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l1idx = ((virt >> PTL1_SHIFT) & (PT_ENTRIES - 1)) as usize;

    let mut entryp = unsafe { entries.add(l4idx) };
    let mut entry = unsafe { read_volatile(entryp) };
    if (entry & PFL2_PRESENT) != 0 {
        entries = unsafe { phys_to_virt(entry & PAGE_MASK) as *mut CULong };
        if entries.is_null() {
            return -ENOMEM;
        }
    } else {
        let newpt = unsafe { x86_pt_alloc_zeroed_result(ap_flag, alloc_fn) };
        if newpt.is_null() {
            return -ENOMEM;
        }
        unsafe {
            write_volatile(entryp, virt_to_phys(newpt) | PFL4_PDIR_ATTR);
        }
        entries = newpt as *mut CULong;
    }

    entryp = unsafe { entries.add(l3idx) };
    entry = unsafe { read_volatile(entryp) };
    if (entry & PFL2_PRESENT) != 0 {
        entries = unsafe { phys_to_virt(entry & PAGE_MASK) as *mut CULong };
        if entries.is_null() {
            return -ENOMEM;
        }
    } else {
        let newpt = unsafe { x86_pt_alloc_zeroed_result(ap_flag, alloc_fn) };
        if newpt.is_null() {
            return -ENOMEM;
        }
        unsafe {
            write_volatile(entryp, virt_to_phys(newpt) | PFL3_PDIR_ATTR);
        }
        entries = newpt as *mut CULong;
    }

    if (attr & PTATTR_LARGEPAGE) != 0 {
        entryp = unsafe { entries.add(l2idx) };
        entry = unsafe { read_volatile(entryp) };
        if (entry & PFL2_PRESENT) != 0 {
            if (entry & PAGE_MASK) != phys {
                return -ENOMEM;
            }
            return 0;
        }

        unsafe {
            write_volatile(
                entryp,
                phys | x86_attr_to_l2attr_result(attr, attr_mask) | PFL2_SIZE,
            );
        }
        return 0;
    }

    entryp = unsafe { entries.add(l2idx) };
    entry = unsafe { read_volatile(entryp) };
    if (entry & PFL2_PRESENT) != 0 {
        entries = unsafe { phys_to_virt(entry & PAGE_MASK) as *mut CULong };
        if entries.is_null() {
            return -ENOMEM;
        }
    } else {
        let newpt = unsafe { x86_pt_alloc_zeroed_result(ap_flag, alloc_fn) };
        if newpt.is_null() {
            return -ENOMEM;
        }
        unsafe {
            write_volatile(entryp, virt_to_phys(newpt) | PFL2_PDIR_ATTR);
        }
        entries = newpt as *mut CULong;
    }

    entryp = unsafe { entries.add(l1idx) };
    entry = unsafe { read_volatile(entryp) };
    if (entry & PFL2_PRESENT) != 0 {
        if (entry & PT_PHYSMASK) != phys {
            if let Some(log) = log_fn {
                unsafe {
                    log(virt);
                }
            }
            return -EBUSY;
        }
        return 0;
    }

    unsafe {
        write_volatile(entryp, phys | x86_attr_to_l1attr_result(attr, attr_mask));
    }
    0
}

#[no_mangle]
pub extern "C" fn x86_lookup_default_pgshift_result(pgshift: i32, use_1gb_page: i32) -> i32 {
    if pgshift != 0 {
        pgshift
    } else if use_1gb_page != 0 {
        PTL3_SHIFT
    } else {
        PTL2_SHIFT
    }
}

#[no_mangle]
pub extern "C" fn x86_lookup_l4_empty_pgshift_result(pgshift: i32) -> i32 {
    if pgshift > PTL3_SHIFT {
        PTL3_SHIFT
    } else {
        pgshift
    }
}

#[no_mangle]
pub extern "C" fn x86_lookup_level_action_result(
    entry: CULong,
    pgshift: i32,
    level_shift: i32,
    size_flag: CULong,
) -> i32 {
    if entry == PTE_NULL || (size_flag != 0 && (entry & size_flag) != 0) {
        if pgshift >= level_shift {
            X86_LOOKUP_PTE_HIT
        } else {
            X86_LOOKUP_PTE_MISS
        }
    } else {
        X86_LOOKUP_PTE_WALK
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_lookup_shape_result(
    virt: CULong,
    pgshift: i32,
    basep: *mut CULong,
    sizep: *mut CULong,
    p2alignp: *mut i32,
) {
    let size = (1 as CULong) << (pgshift as u32);
    let base = virt & !(size - 1);

    if !basep.is_null() {
        unsafe {
            *basep = base;
        }
    }
    if !sizep.is_null() {
        unsafe {
            *sizep = size;
        }
    }
    if !p2alignp.is_null() {
        unsafe {
            *p2alignp = pgshift - PTL1_SHIFT;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_lookup_pte_result(
    pt: *mut c_void,
    virt: CULong,
    pgshift: i32,
    use_1gb_page: i32,
    basep: *mut CULong,
    sizep: *mut CULong,
    p2alignp: *mut i32,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
) -> *mut CULong {
    let mut entries = pt as *mut CULong;
    let mut ptep = core::ptr::null_mut();
    let mut pgshift = x86_lookup_default_pgshift_result(pgshift, use_1gb_page);
    let l4idx = ((virt >> PTL4_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l3idx = ((virt >> PTL3_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l2idx = ((virt >> PTL2_SHIFT) & (PT_ENTRIES - 1)) as usize;
    let l1idx = ((virt >> PTL1_SHIFT) & (PT_ENTRIES - 1)) as usize;

    if entries.is_null() {
        unsafe {
            x86_lookup_shape_result(virt, pgshift, basep, sizep, p2alignp);
        }
        return ptep;
    }

    let l4e = unsafe { read_volatile(entries.add(l4idx)) };
    if l4e == PTE_NULL {
        pgshift = x86_lookup_l4_empty_pgshift_result(pgshift);
        unsafe {
            x86_lookup_shape_result(virt, pgshift, basep, sizep, p2alignp);
        }
        return ptep;
    }

    let Some(phys_to_virt) = phys_to_virt_fn else {
        unsafe {
            x86_lookup_shape_result(virt, pgshift, basep, sizep, p2alignp);
        }
        return ptep;
    };

    entries = unsafe { phys_to_virt(l4e & PT_PHYSMASK) as *mut CULong };
    if entries.is_null() {
        unsafe {
            x86_lookup_shape_result(virt, pgshift, basep, sizep, p2alignp);
        }
        return ptep;
    }

    let l3e = unsafe { read_volatile(entries.add(l3idx)) };
    let mut action = x86_lookup_level_action_result(l3e, pgshift, PTL3_SHIFT, PFL2_SIZE);
    if action == X86_LOOKUP_PTE_HIT {
        ptep = unsafe { entries.add(l3idx) };
        pgshift = PTL3_SHIFT;
    } else if action == X86_LOOKUP_PTE_WALK {
        entries = unsafe { phys_to_virt(l3e & PT_PHYSMASK) as *mut CULong };
        if !entries.is_null() {
            let l2e = unsafe { read_volatile(entries.add(l2idx)) };
            action = x86_lookup_level_action_result(l2e, pgshift, PTL2_SHIFT, PFL2_SIZE);
            if action == X86_LOOKUP_PTE_HIT {
                ptep = unsafe { entries.add(l2idx) };
                pgshift = PTL2_SHIFT;
            } else if action == X86_LOOKUP_PTE_WALK {
                entries = unsafe { phys_to_virt(l2e & PT_PHYSMASK) as *mut CULong };
                if !entries.is_null() {
                    ptep = unsafe { entries.add(l1idx) };
                    pgshift = PTL1_SHIFT;
                }
            }
        }
    }

    unsafe {
        x86_lookup_shape_result(virt, pgshift, basep, sizep, p2alignp);
    }
    ptep
}

#[no_mangle]
pub extern "C" fn x86_arch_vrflag_to_ptattr_result(
    flag: CULong,
    fault: CULong,
    common_attr: CULong,
) -> CULong {
    if (fault & PF_PROT) != 0
        || ((fault & (PF_POPULATE | PF_PATCH)) != 0 && (flag & VR_PRIVATE) != 0)
    {
        common_attr | PTATTR_DIRTY
    } else {
        common_attr
    }
}

#[no_mangle]
pub unsafe extern "C" fn arch_get_smaller_page_size(
    _args: *mut c_void,
    cursize: SizeT,
    newsizep: *mut SizeT,
    p2alignp: *mut CInt,
) -> CInt {
    unsafe {
        x86_smaller_page_size_result(
            cursize as CULong,
            x86_use_1gb_page_bridge(),
            newsizep.cast::<CULong>(),
            p2alignp,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn arch_vrflag_to_ptattr(
    flag: CULong,
    fault: CULong,
    ptep: *mut CULong,
) -> CULong {
    let attr = unsafe { x86_common_vrflag_to_ptattr_bridge(flag, fault, ptep) };
    x86_arch_vrflag_to_ptattr_result(flag, fault, attr)
}

fn x86_fileoff_flag(_pgsize: CULong) -> CULong {
    PFL_FILEOFF
}

#[no_mangle]
pub unsafe extern "C" fn x86_move_pte_preflight_result(
    entry: CULong,
    pgsize: CULong,
    src: CULong,
    dest: CULong,
    pgaddr: CULong,
    mapped_destp: *mut CULong,
) -> i32 {
    if (entry & x86_fileoff_flag(pgsize)) != 0 {
        return -ENOTSUPP;
    }

    if !mapped_destp.is_null() {
        unsafe {
            *mapped_destp = dest.wrapping_add(pgaddr.wrapping_sub(src));
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_move_one_page_body_result(
    arg: *mut c_void,
    pt: *mut c_void,
    ptep: *mut CULong,
    pgaddr: CULong,
    pgshift: CInt,
    src: CULong,
    dest: CULong,
    vm: *mut c_void,
    range: *mut c_void,
    set_range_fn: Option<X86MoveSetRangeFn>,
    log_fn: Option<X86MoveLogFn>,
) -> CInt {
    let Some(set_range) = set_range_fn else {
        return -EINVAL;
    };
    if ptep.is_null() || pgshift < 0 {
        return -EINVAL;
    }

    let pgsize = 1usize << (pgshift as usize);
    let pgsize_ul = pgsize as CULong;
    let entry = unsafe { read_volatile(ptep) };
    let mut mapped_dest = 0;
    let error = unsafe {
        x86_move_pte_preflight_result(entry, pgsize_ul, src, dest, pgaddr, &mut mapped_dest)
    };
    if error != 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    X86_MOVE_ONE_LOG_FILEOFF,
                    arg,
                    pt,
                    ptep,
                    entry,
                    entry,
                    pgaddr,
                    pgshift,
                    error,
                );
            }
        }
        return error;
    }

    let old_entry = unsafe { x86_pte_clear_result(ptep) };
    let mut phys = 0;
    let mut attr = 0;
    unsafe {
        x86_move_pte_entry_parts_result(old_entry, &mut phys, &mut attr);
    }

    let error = unsafe {
        set_range(
            pt,
            vm,
            mapped_dest,
            mapped_dest.wrapping_add(pgsize_ul),
            phys,
            attr,
            pgshift,
            range,
            0,
        )
    };
    if error != 0 {
        if let Some(log) = log_fn {
            let current = unsafe { read_volatile(ptep) };
            unsafe {
                log(
                    X86_MOVE_ONE_LOG_SET_FAILED,
                    arg,
                    pt,
                    ptep,
                    old_entry,
                    current,
                    pgaddr,
                    pgshift,
                    error,
                );
            }
        }
        return error;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_move_pte_range_body_result(
    pt: *mut c_void,
    src: CULong,
    dest: CULong,
    size: SizeT,
    vm: *mut c_void,
    range: *mut c_void,
    args: *mut c_void,
    args_srcp: *mut CULong,
    args_destp: *mut CULong,
    args_vmp: *mut *mut c_void,
    args_rangep: *mut *mut c_void,
    visitor_fn: Option<X86VisitPteFn>,
    visit_fn: Option<X86MoveVisitRangeFn>,
    flush_fn: Option<X86MoveFlushFn>,
) -> CInt {
    let (Some(visitor), Some(visit), Some(flush)) = (visitor_fn, visit_fn, flush_fn) else {
        return -EINVAL;
    };

    if args.is_null()
        || args_srcp.is_null()
        || args_destp.is_null()
        || args_vmp.is_null()
        || args_rangep.is_null()
    {
        return -EINVAL;
    }

    unsafe {
        *args_srcp = src;
        *args_destp = dest;
        *args_vmp = vm;
        *args_rangep = range;
    }

    let error = unsafe {
        visit(
            pt,
            src,
            src.wrapping_add(size as CULong),
            0,
            X86_VPTEF_SKIP_NULL,
            visitor,
            args,
        )
    };
    unsafe {
        flush();
    }

    if error != 0 {
        return error;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_load_cr3_result(pt_addr: CULong) {
    unsafe {
        core::arch::asm!(
            "mov cr3, {addr}",
            addr = in(reg) pt_addr,
            options(nostack, preserves_flags)
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_read_cr3_result() -> CULong {
    let cr3: CULong;
    unsafe {
        core::arch::asm!(
            "mov {addr}, cr3",
            addr = out(reg) cr3,
            options(nostack, preserves_flags)
        );
    }
    cr3
}

#[no_mangle]
pub unsafe extern "C" fn x86_flush_tlb_body_result(
    read_cr3_fn: Option<X86ReadCr3Fn>,
    load_cr3_fn: Option<X86LoadCr3Fn>,
) {
    if let (Some(read_cr3), Some(load_cr3)) = (read_cr3_fn, load_cr3_fn) {
        let cr3 = unsafe { read_cr3() };
        unsafe {
            load_cr3(cr3);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_flush_tlb_result() {
    unsafe {
        x86_flush_tlb_body_result(Some(x86_read_cr3_result), Some(x86_load_cr3_result));
    }
}

#[no_mangle]
pub unsafe extern "C" fn flush_tlb() {
    unsafe {
        x86_flush_tlb_result();
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_flush_tlb_single_body_result(
    addr: CULong,
    invlpg_fn: Option<X86InvlpgFn>,
) {
    if let Some(invlpg) = invlpg_fn {
        unsafe {
            invlpg(addr);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_flush_tlb_single_result(addr: CULong) {
    unsafe {
        core::arch::asm!(
            "invlpg [{addr}]",
            addr = in(reg) addr,
            options(nostack, preserves_flags)
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn flush_tlb_single(addr: CULong) {
    unsafe {
        x86_flush_tlb_single_result(addr);
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_load_page_table_body_result(
    pt: *mut c_void,
    init_pt: *mut c_void,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
    load_cr3_fn: Option<X86LoadCr3Fn>,
) -> CInt {
    let (Some(virt_to_phys), Some(load_cr3)) = (virt_to_phys_fn, load_cr3_fn) else {
        return -EINVAL;
    };
    let target = if pt.is_null() { init_pt } else { pt };
    if target.is_null() {
        return -EINVAL;
    }

    let pt_addr = unsafe { virt_to_phys(target) };
    unsafe {
        load_cr3(pt_addr);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn load_page_table(pt: *mut c_void) {
    let ret = unsafe {
        x86_load_page_table_body_result(
            pt,
            x86_page_table_init_pt_bridge(),
            Some(x86_pt_virt_to_phys_bridge),
            Some(x86_load_cr3_result),
        )
    };
    if ret != 0 {
        unsafe {
            x86_load_page_table_panic_bridge();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_load_page_table(pt: *mut c_void) {
    unsafe {
        load_page_table(pt);
    }
}

#[no_mangle]
pub unsafe extern "C" fn get_init_page_table() -> *mut c_void {
    unsafe { x86_page_table_init_pt_bridge() }
}

#[no_mangle]
pub unsafe extern "C" fn get_boot_page_table() -> *mut c_void {
    unsafe { x86_page_table_boot_pt_bridge() }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_virt_to_pagemap(pt: *mut c_void, virt: CULong) -> CULong {
    unsafe {
        x86_pt_virt_to_pagemap_result(
            pt,
            x86_page_table_init_pt_bridge(),
            virt,
            Some(x86_arch_mem_phys_to_virt_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_virt_to_phys_size(
    pt: *mut c_void,
    virt: *const c_void,
    phys: *mut CULong,
    size: *mut CULong,
) -> CInt {
    unsafe {
        x86_pt_virt_to_phys_size_result(
            pt,
            x86_page_table_init_pt_bridge(),
            virt as CULong,
            phys,
            size,
            Some(x86_arch_mem_phys_to_virt_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_virt_to_phys(
    pt: *mut c_void,
    virt: *const c_void,
    phys: *mut CULong,
) -> CInt {
    unsafe { ihk_mc_pt_virt_to_phys_size(pt, virt, phys, core::ptr::null_mut()) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_map_fixed_area_body_result(
    init_pt: *mut c_void,
    fixed_virtp: *mut CULong,
    phys: CULong,
    size: CULong,
    uncachable: CInt,
    set_page_fn: Option<X86PtSetPageFn>,
    flush_fn: Option<X86MoveFlushFn>,
) -> *mut c_void {
    let (Some(set_page), Some(flush)) = (set_page_fn, flush_fn) else {
        return core::ptr::null_mut();
    };
    if init_pt.is_null() || fixed_virtp.is_null() {
        return core::ptr::null_mut();
    }

    let poffset = phys & (PTL1_SIZE - 1);
    let mut paligned = phys & PAGE_MASK;
    let npages = (poffset.wrapping_add(size).wrapping_add(PTL1_SIZE - 1)) >> PTL1_SHIFT;
    let mut fixed = unsafe { *fixed_virtp };
    let base = fixed;
    let mut attr = PTATTR_WRITABLE | PTATTR_ACTIVE;

    if uncachable != 0 {
        attr |= PTATTR_UNCACHABLE;
    }

    let mut i = 0;
    while i < npages {
        if unsafe { set_page(init_pt, fixed, paligned, attr) } != 0 {
            return core::ptr::null_mut();
        }
        fixed = fixed.wrapping_add(PTL1_SIZE);
        paligned = paligned.wrapping_add(PTL1_SIZE);
        i += 1;
    }

    unsafe {
        *fixed_virtp = fixed;
        flush();
    }

    base.wrapping_add(poffset) as *mut c_void
}

#[no_mangle]
pub unsafe extern "C" fn map_fixed_area(
    phys: CULong,
    size: CULong,
    uncachable: CULong,
) -> *mut c_void {
    let init_pt = unsafe { x86_map_fixed_area_init_pt_bridge() };
    let fixed_virtp = unsafe { x86_map_fixed_area_fixed_virt_slot_bridge() };
    if !fixed_virtp.is_null() {
        unsafe {
            x86_map_fixed_area_log_bridge(phys, size, *fixed_virtp);
        }
    }
    unsafe {
        x86_map_fixed_area_body_result(
            init_pt,
            fixed_virtp,
            phys,
            size,
            (uncachable != 0) as CInt,
            Some(x86_pt_set_page_bridge),
            Some(x86_move_flush_tlb_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_normal_area_body_result(
    pt: *mut c_void,
    map_st_start: CULong,
    large_page_size: CULong,
    writable_attr: CULong,
    map_start_key: CInt,
    map_end_key: CInt,
    get_addr_fn: Option<X86GetMemoryAddressFn>,
    set_large_fn: Option<X86PtSetPageFn>,
    log_fn: Option<X86InitNormalLogFn>,
) -> CInt {
    let (Some(get_addr), Some(set_large), Some(log)) = (get_addr_fn, set_large_fn, log_fn) else {
        return -EINVAL;
    };
    if pt.is_null() || large_page_size == 0 {
        return -EINVAL;
    }

    let map_start = unsafe { get_addr(map_start_key, 0) };
    let map_end = unsafe { get_addr(map_end_key, 0) };
    let mut virt = map_st_start.wrapping_add(map_start);

    unsafe {
        log(X86_INIT_NORMAL_LOG_RANGE, map_start, map_end, virt);
    }

    let mut phys = map_start;
    while phys < map_end {
        let error = unsafe { set_large(pt, virt, phys, writable_attr) };
        if error != 0 {
            unsafe {
                log(X86_INIT_NORMAL_LOG_SET_FAILED, virt, phys, error as CULong);
            }
        }
        phys = phys.wrapping_add(large_page_size);
        virt = virt.wrapping_add(large_page_size);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_normal_area_public(pt: *mut c_void) {
    let ret = unsafe {
        x86_init_normal_area_body_result(
            pt,
            MAP_ST_START,
            PTL2_SIZE,
            PTATTR_WRITABLE,
            IHK_MC_GMA_MAP_START,
            IHK_MC_GMA_MAP_END,
            Some(x86_init_normal_get_memory_address_bridge),
            Some(x86_init_normal_set_large_bridge),
            Some(x86_init_normal_log_bridge),
        )
    };
    if ret != 0 {
        unsafe {
            x86_init_normal_panic_bridge();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_text_area_body_result(
    pt: *mut c_void,
    map_kernel_start: CULong,
    end_addr: CULong,
    large_page_size: CULong,
    large_page_shift: CInt,
    large_page_mask: CULong,
    kernel_phys_base: CULong,
    writable_attr: CULong,
    set_large_fn: Option<X86PtSetPageFn>,
    log_fn: Option<X86InitTextLogFn>,
) -> CInt {
    let (Some(set_large), Some(log)) = (set_large_fn, log_fn) else {
        return -EINVAL;
    };
    if pt.is_null()
        || large_page_size == 0
        || large_page_shift < 0
        || large_page_shift >= (CULong::BITS as CInt)
    {
        return -EINVAL;
    }

    let end_aligned =
        end_addr.wrapping_add(large_page_size.wrapping_mul(2).wrapping_sub(1)) & large_page_mask;
    let nlpages = end_aligned.wrapping_sub(map_kernel_start) >> large_page_shift;

    unsafe {
        log(X86_INIT_TEXT_LOG_LPAGES, nlpages, 0, 0);
        log(X86_INIT_TEXT_LOG_BASE, kernel_phys_base, 0, 0);
    }

    let mut phys = kernel_phys_base;
    let mut virt = map_kernel_start;
    let mut i = 0;
    while i < nlpages {
        unsafe {
            set_large(pt, virt, phys, writable_attr);
        }
        virt = virt.wrapping_add(large_page_size);
        phys = phys.wrapping_add(large_page_size);
        i += 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn init_text_area(pt: *mut c_void) {
    let ret = unsafe {
        x86_init_text_area_body_result(
            pt,
            x86_init_text_map_kernel_start_bridge(),
            x86_init_text_end_bridge(),
            PTL2_SIZE,
            LARGE_PAGE_SHIFT,
            LARGE_PAGE_MASK,
            X86_KERNEL_PHYS_BASE,
            PTATTR_WRITABLE,
            Some(x86_init_normal_set_large_bridge),
            Some(x86_init_text_log_bridge),
        )
    };
    if ret != 0 {
        unsafe {
            x86_init_text_panic_bridge();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_fixed_area_body_result(
    fixed_virtp: *mut CULong,
    map_fixed_start: CULong,
) -> CInt {
    if fixed_virtp.is_null() {
        return -EINVAL;
    }

    unsafe {
        *fixed_virtp = map_fixed_start;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_fixed_area_public(pt: *mut c_void) {
    let _ = pt;
    let ret = unsafe {
        x86_init_fixed_area_body_result(
            x86_map_fixed_area_fixed_virt_slot_bridge(),
            MAP_FIXED_START,
        )
    };
    if ret != 0 {
        unsafe {
            x86_init_fixed_panic_bridge();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_low_area_body_result(
    pt: *mut c_void,
    no_execute_attr: CULong,
    writable_attr: CULong,
    set_large_fn: Option<X86PtSetPageFn>,
) -> CInt {
    let Some(set_large) = set_large_fn else {
        return -EINVAL;
    };
    if pt.is_null() {
        return -EINVAL;
    }

    unsafe {
        set_large(pt, 0, 0, no_execute_attr | writable_attr);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn init_low_area(pt: *mut c_void) {
    let ret = unsafe {
        x86_init_low_area_body_result(
            pt,
            PTATTR_NO_EXECUTE,
            PTATTR_WRITABLE,
            Some(x86_init_normal_set_large_bridge),
        )
    };
    if ret != 0 {
        unsafe {
            x86_init_low_panic_bridge();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_vsyscall_area_body_result(
    pt: *mut c_void,
    vsyscall_addr: CULong,
    vsyscall_page: *mut c_void,
    attr: CULong,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
    set_page_fn: Option<X86PtSetPageFn>,
) -> CInt {
    let (Some(virt_to_phys), Some(set_page)) = (virt_to_phys_fn, set_page_fn) else {
        return -EINVAL;
    };
    if pt.is_null() || vsyscall_page.is_null() {
        return -EINVAL;
    }

    let phys = unsafe { virt_to_phys(vsyscall_page) };
    unsafe { set_page(pt, vsyscall_addr, phys, attr) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_vsyscall_area_public(pt: *mut c_void) {
    let ret = unsafe {
        x86_init_vsyscall_area_body_result(
            pt,
            VSYSCALL_ADDR,
            x86_init_vsyscall_page_bridge(),
            PTATTR_ACTIVE | PTATTR_FOR_USER,
            Some(x86_pt_virt_to_phys_bridge),
            Some(x86_pt_set_page_bridge),
        )
    };
    if ret != 0 {
        unsafe {
            x86_init_vsyscall_panic_bridge();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_linux_kernel_mapping_body_result(
    pt: *mut c_void,
    linux_page_offset_base: CULong,
    large_page_size: CULong,
    writable_attr: CULong,
    full_map_end: CULong,
    safe_kernel_map_name: *mut i8,
    find_command_line_fn: Option<X86FindCommandLineFn>,
    get_nr_chunks_fn: Option<X86GetNrMemoryChunksFn>,
    get_chunk_fn: Option<X86GetMemoryChunkFn>,
    set_large_fn: Option<X86PtSetPageFn>,
    log_fn: Option<X86InitLinuxLogFn>,
) -> CInt {
    let (Some(find_command_line), Some(get_nr_chunks), Some(get_chunk), Some(set_large), Some(log)) = (
        find_command_line_fn,
        get_nr_chunks_fn,
        get_chunk_fn,
        set_large_fn,
        log_fn,
    ) else {
        return -EINVAL;
    };
    if pt.is_null() || large_page_size == 0 || safe_kernel_map_name.is_null() {
        return -EINVAL;
    }

    if unsafe { find_command_line(safe_kernel_map_name) }.is_null() {
        unsafe {
            log(X86_INIT_LINUX_LOG_FULL, 0, 0, 0, 0, 0);
        }
        let map_start = 0;
        let map_end = full_map_end;
        let mut virt = linux_page_offset_base;
        unsafe {
            log(
                X86_INIT_LINUX_LOG_FULL_RANGE,
                virt,
                virt.wrapping_add(map_end),
                0,
                map_end,
                0,
            );
        }

        let mut phys = map_start;
        while phys < map_end {
            let error = unsafe { set_large(pt, virt, phys, writable_attr) };
            if error != 0 {
                unsafe {
                    log(X86_INIT_LINUX_LOG_FULL_SET_FAILED, virt, phys, 0, 0, error);
                }
            }
            phys = phys.wrapping_add(large_page_size);
            virt = virt.wrapping_add(large_page_size);
        }
        return 0;
    }

    unsafe {
        log(X86_INIT_LINUX_LOG_CHUNKS, 0, 0, 0, 0, 0);
    }
    let nr_memory_chunks = unsafe { get_nr_chunks() };
    if nr_memory_chunks == 0 {
        unsafe {
            log(X86_INIT_LINUX_LOG_NO_CHUNK, 0, 0, 0, 0, 0);
        }
        return 0;
    }

    let mut chunk_id = 0;
    while chunk_id < nr_memory_chunks {
        let mut map_start = 0;
        let mut map_end = 0;
        let mut numa_id = 0;
        if unsafe { get_chunk(chunk_id, &mut map_start, &mut map_end, &mut numa_id) } != 0 {
            unsafe {
                log(X86_INIT_LINUX_LOG_BAD_CHUNK, chunk_id as CULong, 0, 0, 0, 0);
            }
            chunk_id += 1;
            continue;
        }

        unsafe {
            log(
                X86_INIT_LINUX_LOG_CHUNK_RANGE,
                linux_page_offset_base.wrapping_add(map_start),
                linux_page_offset_base.wrapping_add(map_end),
                map_start,
                map_end,
                0,
            );
        }

        let mut phys = map_start;
        let mut virt = linux_page_offset_base.wrapping_add(map_start);
        while phys < map_end {
            let error = unsafe { set_large(pt, virt, phys, writable_attr) };
            if error != 0 {
                unsafe {
                    log(X86_INIT_LINUX_LOG_CHUNK_SET_FAILED, virt, phys, 0, 0, error);
                }
            }
            phys = phys.wrapping_add(large_page_size);
            virt = virt.wrapping_add(large_page_size);
        }

        chunk_id += 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_linux_kernel_mapping_public(pt: *mut c_void) {
    let ret = unsafe {
        x86_init_linux_kernel_mapping_body_result(
            pt,
            LINUX_PAGE_OFFSET_BASE,
            PTL2_SIZE,
            PTATTR_WRITABLE,
            X86_INIT_LINUX_FULL_MAP_END,
            SAFE_KERNEL_MAP.as_ptr() as *mut i8,
            Some(x86_init_linux_find_command_line_bridge),
            Some(x86_init_linux_get_nr_memory_chunks_bridge),
            Some(x86_init_linux_get_memory_chunk_bridge),
            Some(x86_init_normal_set_large_bridge),
            Some(x86_init_linux_log_bridge),
        )
    };
    if ret != 0 {
        unsafe {
            x86_init_linux_panic_bridge();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_virt_to_phys_body_result(
    va: CULong,
    map_kernel_start: CULong,
    kernel_phys_base: CULong,
    linux_page_offset_base: CULong,
    map_fixed_start: CULong,
    map_st_start: CULong,
    log_fn: Option<X86AddrLogFn>,
) -> CULong {
    if va >= map_kernel_start {
        if let Some(log) = log_fn {
            unsafe {
                log(X86_ADDR_LOG_KERNEL, va);
            }
        }
        return va
            .wrapping_sub(map_kernel_start)
            .wrapping_add(kernel_phys_base);
    }
    if va >= linux_page_offset_base {
        return va.wrapping_sub(linux_page_offset_base);
    }
    if va >= map_fixed_start {
        return va.wrapping_sub(map_fixed_start);
    }

    if let Some(log) = log_fn {
        unsafe {
            log(X86_ADDR_LOG_STRAIGHT, va);
        }
    }
    va.wrapping_sub(map_st_start)
}

#[no_mangle]
pub unsafe extern "C" fn x86_phys_to_virt_body_result(
    phys: CULong,
    init_pt_loaded: CInt,
    map_st_start: CULong,
    linux_page_offset_base: CULong,
) -> *mut c_void {
    if init_pt_loaded == 0 {
        return phys.wrapping_add(map_st_start) as *mut c_void;
    }

    phys.wrapping_add(linux_page_offset_base) as *mut c_void
}

#[no_mangle]
pub unsafe extern "C" fn virt_to_phys(v: *mut c_void) -> CULong {
    x86_virt_to_phys_body_result(
        v as CULong,
        x86_user_map_kernel_start_bridge(),
        X86_KERNEL_PHYS_BASE,
        LINUX_PAGE_OFFSET_BASE,
        MAP_FIXED_START,
        MAP_ST_START,
        Some(x86_addr_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn phys_to_virt(p: CULong) -> *mut c_void {
    x86_phys_to_virt_body_result(
        p,
        x86_addr_init_pt_loaded_bridge(),
        MAP_ST_START,
        LINUX_PAGE_OFFSET_BASE,
    )
}

#[no_mangle]
pub unsafe extern "C" fn x86_reserve_arch_pages_body_result(
    pa_allocator: *mut c_void,
    start: CULong,
    end: CULong,
    head: *mut c_void,
    last_early_heap: *mut c_void,
    ap_trampoline: CULong,
    ap_trampoline_size: CULong,
    page_size: CULong,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
    cb_fn: Option<X86ReservePagesCbFn>,
    reserve_arch_fn: Option<X86ReserveArchFn>,
) -> CInt {
    let (Some(virt_to_phys), Some(cb), Some(reserve_arch)) =
        (virt_to_phys_fn, cb_fn, reserve_arch_fn)
    else {
        return -EINVAL;
    };
    if pa_allocator.is_null() || head.is_null() || last_early_heap.is_null() {
        return -EINVAL;
    }

    unsafe {
        cb(
            pa_allocator,
            virt_to_phys(head),
            virt_to_phys(last_early_heap),
            0,
        );
        cb(
            pa_allocator,
            ap_trampoline,
            ap_trampoline.wrapping_add(ap_trampoline_size),
            0,
        );
        cb(pa_allocator, 0, page_size, 0);
        reserve_arch(start, end, cb);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_reserve_arch_pages(
    pa_allocator: *mut c_void,
    start: CULong,
    end: CULong,
    cb: Option<X86ReservePagesCbFn>,
) {
    let ret = x86_reserve_arch_pages_body_result(
        pa_allocator,
        start,
        end,
        core::ptr::addr_of_mut!(X86_HEAD).cast::<c_void>(),
        get_last_early_heap(),
        X86_AP_TRAMPOLINE,
        AP_TRAMPOLINE_SIZE,
        PTL1_SIZE,
        Some(x86_pt_virt_to_phys_bridge),
        cb,
        Some(x86_reserve_arch_pages_bridge),
    );
    if ret != 0 {
        x86_reserve_arch_pages_panic_bridge();
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_move_pte_entry_parts_result(
    entry: CULong,
    physp: *mut CULong,
    attrp: *mut CULong,
) {
    if !physp.is_null() {
        unsafe {
            *physp = entry & PT_PHYSMASK;
        }
    }
    if !attrp.is_null() {
        unsafe {
            *attrp = entry & !PT_PHYSMASK;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_destroy_pt_entry_action_result(
    level: i32,
    entry: CULong,
    lower_physp: *mut CULong,
) -> i32 {
    if !lower_physp.is_null() {
        unsafe {
            *lower_physp = 0;
        }
    }

    if level <= 1 || (entry & PFL2_PRESENT) == 0 || (entry & PFL2_SIZE) != 0 {
        return X86_DESTROY_PT_SKIP;
    }

    if !lower_physp.is_null() {
        unsafe {
            *lower_physp = entry & PT_PHYSMASK;
        }
    }
    X86_DESTROY_PT_DESCEND
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_create_result(
    init_pt: *mut c_void,
    ap_flag: CInt,
    alloc_fn: Option<X86PtAllocPagesFn>,
) -> *mut c_void {
    let Some(alloc) = alloc_fn else {
        return core::ptr::null_mut();
    };
    let pt = unsafe { alloc(1, ap_flag) };
    if pt.is_null() {
        return core::ptr::null_mut();
    }

    let init_entries = init_pt as *const CULong;
    let pt_entries = pt as *mut CULong;
    unsafe {
        write_bytes(pt_entries, 0, PT_ENTRIES as usize);
        copy_nonoverlapping(
            init_entries.add((PT_ENTRIES as usize) / 2),
            pt_entries.add((PT_ENTRIES as usize) / 2),
            (PT_ENTRIES as usize) / 2,
        );
    }

    pt
}

unsafe fn x86_pt_destroy_table_inner(
    level: CInt,
    pt: *mut c_void,
    phys_to_virt: X86PtPhysToVirtFn,
    free_pages: X86PtFreePagesFn,
    panic_fn: Option<X86PtDestroyPanicFn>,
) -> CInt {
    if !(1..=4).contains(&level) {
        if let Some(panic) = panic_fn {
            unsafe {
                panic(X86_PT_DESTROY_PANIC_LEVEL);
            }
        }
        return -EINVAL;
    }
    if pt.is_null() {
        if let Some(panic) = panic_fn {
            unsafe {
                panic(X86_PT_DESTROY_PANIC_NULL);
            }
        }
        return -EINVAL;
    }

    let entries = pt as *mut CULong;
    if level > 1 {
        let mut ix = 0;
        while ix < PT_ENTRIES {
            let entry = unsafe { read_volatile(entries.add(ix as usize)) };
            let mut lower_phys = 0;

            if unsafe { x86_destroy_pt_entry_action_result(level, entry, &mut lower_phys) }
                == X86_DESTROY_PT_DESCEND
            {
                let lower = unsafe { phys_to_virt(lower_phys) };
                let ret = unsafe {
                    x86_pt_destroy_table_inner(level - 1, lower, phys_to_virt, free_pages, panic_fn)
                };
                if ret != 0 {
                    return ret;
                }
            }

            ix += 1;
        }
    }

    unsafe {
        free_pages(pt, 1);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_destroy_table_result(
    level: CInt,
    pt: *mut c_void,
    phys_to_virt_fn: Option<X86PtPhysToVirtFn>,
    free_pages_fn: Option<X86PtFreePagesFn>,
    panic_fn: Option<X86PtDestroyPanicFn>,
) -> CInt {
    let Some(free_pages) = free_pages_fn else {
        return -EINVAL;
    };
    let phys_to_virt = if level > 1 {
        match phys_to_virt_fn {
            Some(phys_to_virt) => phys_to_virt,
            None => return -EINVAL,
        }
    } else {
        unsafe extern "C" fn unused_phys_to_virt(_phys: CULong) -> *mut c_void {
            core::ptr::null_mut()
        }
        unused_phys_to_virt
    };

    unsafe { x86_pt_destroy_table_inner(level, pt, phys_to_virt, free_pages, panic_fn) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_destroy_root_result(
    pt: *mut c_void,
    destroy_fn: Option<X86PtDestroyFn>,
) {
    let entries = pt as *mut CULong;
    unsafe {
        write_bytes(
            entries.add((PT_ENTRIES as usize) / 2),
            0,
            (PT_ENTRIES as usize) / 2,
        );
    }

    if let Some(destroy) = destroy_fn {
        unsafe {
            destroy(4, pt);
        }
    }
}

unsafe extern "C" fn x86_pt_destroy_public_bridge(level: CInt, pt: *mut c_void) {
    let ret = unsafe {
        x86_pt_destroy_table_result(
            level,
            pt,
            Some(x86_pt_phys_to_virt_bridge),
            Some(x86_pt_free_pages_bridge),
            Some(x86_pt_destroy_panic_bridge),
        )
    };
    if ret != 0 {
        unsafe {
            x86_pt_destroy_helper_failed_panic_bridge();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_create(ap_flag: CInt) -> *mut c_void {
    unsafe {
        x86_pt_create_result(
            x86_page_table_init_pt_bridge(),
            ap_flag,
            Some(x86_pt_alloc_pages_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_destroy(pt: *mut c_void) {
    unsafe {
        x86_pt_destroy_root_result(pt, Some(x86_pt_destroy_public_bridge));
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_prepare_map(
    pt: *mut c_void,
    virt: *mut c_void,
    size: CULong,
    flag: CInt,
) -> CInt {
    unsafe {
        x86_pt_prepare_map_result(
            pt,
            x86_page_table_init_pt_bridge(),
            virt as CULong,
            size,
            flag,
            PTATTR_WRITABLE,
            Some(x86_pt_alloc_pages_bridge),
            Some(x86_pt_virt_to_phys_bridge),
            Some(x86_pt_set_page_bridge),
        )
    }
}

unsafe fn x86_walk_pte_level_result(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    span: CULong,
    shift: CInt,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
) -> CInt {
    unsafe {
        x86_walk_pte_range_result(
            pt as CULong,
            base,
            start,
            end,
            span,
            shift,
            funcp,
            args,
            None,
            PT_PHYSMASK,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn walk_pte_l1(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
) -> CInt {
    unsafe { x86_walk_pte_level_result(pt, base, start, end, PTL2_SIZE, PTL1_SHIFT, funcp, args) }
}

#[no_mangle]
pub unsafe extern "C" fn walk_pte_l2(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
) -> CInt {
    unsafe { x86_walk_pte_level_result(pt, base, start, end, PTL3_SIZE, PTL2_SHIFT, funcp, args) }
}

#[no_mangle]
pub unsafe extern "C" fn walk_pte_l3(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
) -> CInt {
    unsafe { x86_walk_pte_level_result(pt, base, start, end, PTL4_SIZE, PTL3_SHIFT, funcp, args) }
}

#[no_mangle]
pub unsafe extern "C" fn walk_pte_l4(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
) -> CInt {
    unsafe { x86_walk_pte_level_result(pt, base, start, end, 0, PTL4_SHIFT, funcp, args) }
}

unsafe extern "C" fn x86_walk_page_address_check(phys: CULong) -> CInt {
    unsafe { ihk_mc_chk_page_address(phys) }
}

unsafe fn x86_walk_pte_safe_level_result(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    span: CULong,
    shift: CInt,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
) -> CInt {
    if pt.is_null() {
        return 0;
    }

    unsafe {
        x86_walk_pte_range_result(
            pt as CULong,
            base,
            start,
            end,
            span,
            shift,
            funcp,
            args,
            Some(x86_walk_page_address_check),
            PT_PHYSMASK,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn walk_pte_l1_safe(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
) -> CInt {
    unsafe {
        x86_walk_pte_safe_level_result(pt, base, start, end, PTL2_SIZE, PTL1_SHIFT, funcp, args)
    }
}

#[no_mangle]
pub unsafe extern "C" fn walk_pte_l2_safe(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
) -> CInt {
    unsafe {
        x86_walk_pte_safe_level_result(pt, base, start, end, PTL3_SIZE, PTL2_SHIFT, funcp, args)
    }
}

#[no_mangle]
pub unsafe extern "C" fn walk_pte_l3_safe(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
) -> CInt {
    unsafe {
        x86_walk_pte_safe_level_result(pt, base, start, end, PTL4_SIZE, PTL3_SHIFT, funcp, args)
    }
}

#[no_mangle]
pub unsafe extern "C" fn walk_pte_l4_safe(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
) -> CInt {
    unsafe { x86_walk_pte_safe_level_result(pt, base, start, end, 0, PTL4_SHIFT, funcp, args) }
}

#[no_mangle]
pub unsafe extern "C" fn visit_pte_l1(
    arg0: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    _start: CULong,
    _end: CULong,
) -> CInt {
    if arg0.is_null() {
        return -EINVAL;
    }

    let args = unsafe { &mut *(arg0 as *mut X86VisitPteArgs) };
    unsafe {
        x86_visit_pte_leaf_result(
            args.arg,
            args.pt,
            ptep,
            base,
            args.flags & X86_VPTEF_SKIP_NULL,
            PTL1_SHIFT,
            args.funcp,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_walk_l1_bridge(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    args: *mut c_void,
) -> CInt {
    unsafe { walk_pte_l1(pt, base, start, end, Some(visit_pte_l1), args) }
}

#[no_mangle]
pub unsafe extern "C" fn visit_pte_l2(
    arg0: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    if arg0.is_null() {
        return -EINVAL;
    }

    let args = unsafe { &mut *(arg0 as *mut X86VisitPteArgs) };
    unsafe {
        x86_visit_pte_level_result(
            args.arg,
            args.pt,
            ptep,
            base,
            start,
            end,
            args.flags & X86_VPTEF_SKIP_NULL,
            0,
            args.pgshift,
            PTL2_SIZE,
            PTL2_SHIFT,
            PFL2_SIZE,
            0,
            1,
            1,
            PFL2_PDIR_ATTR,
            Some(x86_pt_alloc_pages_bridge),
            Some(x86_pt_virt_to_phys_bridge),
            Some(x86_pt_phys_to_virt_bridge),
            Some(x86_visit_walk_l1_bridge),
            arg0,
            args.funcp,
            Some(x86_visit_pte_log_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_walk_l2_bridge(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    args: *mut c_void,
) -> CInt {
    unsafe { walk_pte_l2(pt, base, start, end, Some(visit_pte_l2), args) }
}

#[no_mangle]
pub unsafe extern "C" fn visit_pte_l3(
    arg0: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    if arg0.is_null() {
        return -EINVAL;
    }

    let args = unsafe { &mut *(arg0 as *mut X86VisitPteArgs) };
    unsafe {
        x86_visit_pte_level_result(
            args.arg,
            args.pt,
            ptep,
            base,
            start,
            end,
            args.flags & X86_VPTEF_SKIP_NULL,
            0,
            args.pgshift,
            PTL3_SIZE,
            PTL3_SHIFT,
            PFL2_SIZE,
            0,
            x86_use_1gb_page_bridge(),
            1,
            PFL3_PDIR_ATTR,
            Some(x86_pt_alloc_pages_bridge),
            Some(x86_pt_virt_to_phys_bridge),
            Some(x86_pt_phys_to_virt_bridge),
            Some(x86_visit_walk_l2_bridge),
            arg0,
            args.funcp,
            Some(x86_visit_pte_log_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_walk_l3_bridge(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    args: *mut c_void,
) -> CInt {
    unsafe { walk_pte_l3(pt, base, start, end, Some(visit_pte_l3), args) }
}

#[no_mangle]
pub unsafe extern "C" fn visit_pte_l4(
    arg0: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    if arg0.is_null() {
        return -EINVAL;
    }

    let args = unsafe { &mut *(arg0 as *mut X86VisitPteArgs) };
    unsafe {
        x86_visit_pte_root_result(
            ptep,
            base,
            start,
            end,
            args.flags & X86_VPTEF_SKIP_NULL,
            1,
            PFL4_PDIR_ATTR,
            Some(x86_pt_alloc_pages_bridge),
            Some(x86_pt_virt_to_phys_bridge),
            Some(x86_pt_phys_to_virt_bridge),
            Some(x86_visit_walk_l3_bridge),
            arg0,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_walk_l4_bridge(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    args: *mut c_void,
) -> CInt {
    unsafe { walk_pte_l4(pt, base, start, end, Some(visit_pte_l4), args) }
}

#[no_mangle]
pub unsafe extern "C" fn visit_pte_range(
    pt: *mut c_void,
    start0: *mut c_void,
    end0: *mut c_void,
    pgshift: CInt,
    flags: CInt,
    funcp: Option<X86VisitPteFn>,
    arg: *mut c_void,
) -> CInt {
    let mut args = X86VisitPteArgs {
        pt,
        flags,
        pgshift,
        funcp,
        arg,
    };

    unsafe {
        x86_visit_pte_range_dispatch_result(
            pt,
            start0 as CULong,
            end0 as CULong,
            &mut args as *mut X86VisitPteArgs as *mut c_void,
            Some(x86_visit_walk_l4_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn visit_pte_l1_safe(
    arg0: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    _start: CULong,
    _end: CULong,
) -> CInt {
    if arg0.is_null() {
        return -EINVAL;
    }

    let args = unsafe { &mut *(arg0 as *mut X86VisitPteArgs) };
    unsafe { x86_visit_pte_leaf_result(args.arg, args.pt, ptep, base, 1, PTL1_SHIFT, args.funcp) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_walk_l1_safe_bridge(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    args: *mut c_void,
) -> CInt {
    unsafe { walk_pte_l1_safe(pt, base, start, end, Some(visit_pte_l1_safe), args) }
}

#[no_mangle]
pub unsafe extern "C" fn visit_pte_l2_safe(
    arg0: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    if arg0.is_null() {
        return -EINVAL;
    }

    let args = unsafe { &mut *(arg0 as *mut X86VisitPteArgs) };
    unsafe {
        x86_visit_pte_level_result(
            args.arg,
            args.pt,
            ptep,
            base,
            start,
            end,
            1,
            1,
            args.pgshift,
            PTL2_SIZE,
            PTL2_SHIFT,
            PFL2_SIZE,
            1,
            1,
            0,
            PFL2_PDIR_ATTR,
            Some(x86_pt_alloc_pages_bridge),
            Some(x86_pt_virt_to_phys_bridge),
            Some(x86_pt_phys_to_virt_bridge),
            Some(x86_visit_walk_l1_safe_bridge),
            arg0,
            args.funcp,
            Some(x86_visit_pte_log_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_walk_l2_safe_bridge(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    args: *mut c_void,
) -> CInt {
    unsafe { walk_pte_l2_safe(pt, base, start, end, Some(visit_pte_l2_safe), args) }
}

#[no_mangle]
pub unsafe extern "C" fn visit_pte_l3_safe(
    arg0: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    if arg0.is_null() {
        return -EINVAL;
    }

    let args = unsafe { &mut *(arg0 as *mut X86VisitPteArgs) };
    unsafe {
        x86_visit_pte_level_result(
            args.arg,
            args.pt,
            ptep,
            base,
            start,
            end,
            1,
            1,
            args.pgshift,
            PTL3_SIZE,
            PTL3_SHIFT,
            PFL2_SIZE,
            1,
            x86_use_1gb_page_bridge(),
            0,
            PFL3_PDIR_ATTR,
            Some(x86_pt_alloc_pages_bridge),
            Some(x86_pt_virt_to_phys_bridge),
            Some(x86_pt_phys_to_virt_bridge),
            Some(x86_visit_walk_l2_safe_bridge),
            arg0,
            args.funcp,
            Some(x86_visit_pte_log_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_walk_l3_safe_bridge(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    args: *mut c_void,
) -> CInt {
    unsafe { walk_pte_l3_safe(pt, base, start, end, Some(visit_pte_l3_safe), args) }
}

#[no_mangle]
pub unsafe extern "C" fn visit_pte_l4_safe(
    arg0: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    if arg0.is_null() {
        return -EINVAL;
    }

    unsafe {
        x86_visit_pte_root_result(
            ptep,
            base,
            start,
            end,
            1,
            0,
            PFL4_PDIR_ATTR,
            Some(x86_pt_alloc_pages_bridge),
            Some(x86_pt_virt_to_phys_bridge),
            Some(x86_pt_phys_to_virt_bridge),
            Some(x86_visit_walk_l3_safe_bridge),
            arg0,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_visit_walk_l4_safe_bridge(
    pt: *mut c_void,
    base: CULong,
    start: CULong,
    end: CULong,
    args: *mut c_void,
) -> CInt {
    unsafe { walk_pte_l4_safe(pt, base, start, end, Some(visit_pte_l4_safe), args) }
}

#[no_mangle]
pub unsafe extern "C" fn visit_pte_range_safe(
    pt: *mut c_void,
    start0: *mut c_void,
    end0: *mut c_void,
    pgshift: CInt,
    flags: CInt,
    funcp: Option<X86VisitPteFn>,
    arg: *mut c_void,
) -> CInt {
    let mut args = X86VisitPteArgs {
        pt,
        flags,
        pgshift,
        funcp,
        arg,
    };

    unsafe {
        x86_visit_pte_range_dispatch_result(
            pt,
            start0 as CULong,
            end0 as CULong,
            &mut args as *mut X86VisitPteArgs as *mut c_void,
            Some(x86_visit_walk_l4_safe_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_prepare_map_result(
    pt: *mut c_void,
    init_pt: *mut c_void,
    virt: CULong,
    size: CULong,
    flag: CInt,
    writable_attr: CULong,
    alloc_fn: Option<X86PtAllocPagesFn>,
    virt_to_phys_fn: Option<X86PtVirtToPhysFn>,
    set_page_fn: Option<X86PtSetPageFn>,
) -> CInt {
    let entries = if pt.is_null() {
        init_pt as *mut CULong
    } else {
        pt as *mut CULong
    };
    let mut v = virt;
    let l4idx = ((v >> PTL4_SHIFT) & (PT_ENTRIES - 1)) as usize;

    if flag == IHK_MC_PT_FIRST_LEVEL {
        let Some(alloc) = alloc_fn else {
            return -ENOMEM;
        };
        let Some(virt_to_phys) = virt_to_phys_fn else {
            return -ENOMEM;
        };
        let l4e = ((v.wrapping_add(size) >> PTL4_SHIFT) & (PT_ENTRIES - 1)) as usize;
        let mut ret = 0;

        for idx in l4idx..=l4e {
            let entryp = unsafe { entries.add(idx) };
            if unsafe { read_volatile(entryp) } & PFL2_PRESENT != 0 {
                return 0;
            }

            let newpt = unsafe { alloc(1, IHK_MC_AP_CRITICAL) };
            if newpt.is_null() {
                ret = -ENOMEM;
            } else {
                let entry = unsafe { virt_to_phys(newpt) } | PFL4_PDIR_ATTR;
                unsafe {
                    write_volatile(entryp, entry);
                }
            }
        }
        ret
    } else {
        let Some(set_page) = set_page_fn else {
            return -ENOMEM;
        };
        let end = v.wrapping_add(size);
        let mut ret = 0;

        while v < end {
            ret = unsafe { set_page(entries as *mut c_void, v, 0, writable_attr) };
            if ret != 0 {
                break;
            }
            v = v.wrapping_add(PTL1_SIZE);
        }
        ret
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_set_pte_body_result(
    pt: *mut c_void,
    ptep: *mut CULong,
    pgsize: CULong,
    phys: CULong,
    attr: CULong,
    attr_mask: CULong,
    use_1gb_page: CInt,
    log_fn: Option<X86PtSetPteLogFn>,
    panic_fn: Option<X86PtSetPtePanicFn>,
) -> CInt {
    let mut entry = 0;
    let current = if ptep.is_null() {
        0
    } else {
        unsafe { read_volatile(ptep) }
    };
    let error = unsafe {
        x86_pt_set_pte_value_result(pgsize, phys, attr, attr_mask, use_1gb_page, &mut entry)
    };

    if error != 0 {
        if error == -1 && pgsize == PTL2_SIZE {
            if let Some(log) = log_fn {
                unsafe {
                    log(
                        X86_PT_SET_PTE_LOG_L2_ALIGN,
                        pt,
                        ptep,
                        pgsize,
                        phys,
                        attr,
                        error,
                        current,
                    );
                }
            }
            return error;
        }
        if error == -1 && pgsize == PTL3_SIZE {
            if let Some(log) = log_fn {
                unsafe {
                    log(
                        X86_PT_SET_PTE_LOG_L3_ALIGN,
                        pt,
                        ptep,
                        pgsize,
                        phys,
                        attr,
                        error,
                        current,
                    );
                }
            }
            return error;
        }
        if let Some(log) = log_fn {
            unsafe {
                log(
                    X86_PT_SET_PTE_LOG_PAGE_SIZE,
                    pt,
                    ptep,
                    pgsize,
                    phys,
                    attr,
                    error,
                    current,
                );
            }
        }
        if let Some(panic) = panic_fn {
            unsafe {
                panic();
            }
        }
        return error;
    }

    unsafe {
        x86_pte_store_result(ptep, entry);
    }
    0
}

#[inline]
unsafe fn x86_user_copy_bytes(dst: *mut u8, src: *const u8, size: usize) {
    let mut i = 0usize;

    while i < size {
        let byte = unsafe { read_volatile(src.add(i)) };
        unsafe {
            write_volatile(dst.add(i), byte);
        }
        i += 1;
    }
}

#[inline]
fn x86_user_range_valid(uaddr: CULong, size: SizeT, user_start: CULong, user_end: CULong) -> bool {
    let size = size as CULong;

    !(uaddr < user_start || user_end <= uaddr || user_end.wrapping_sub(uaddr) < size)
}

#[no_mangle]
pub unsafe extern "C" fn x86_verify_process_vm_result(
    vm: *mut c_void,
    uaddr: CULong,
    size: SizeT,
    user_start: CULong,
    user_end: CULong,
    reason: CULong,
    page_fault_fn: Option<X86UserPageFaultFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    if !x86_user_range_valid(uaddr, size, user_start, user_end) {
        if let Some(log) = log_fn {
            unsafe {
                log(X86_USER_COPY_LOG_RANGE, vm, uaddr, size as CULong, -EFAULT);
            }
        }
        return -EFAULT;
    }

    let Some(page_fault) = page_fault_fn else {
        return -EFAULT;
    };

    let uend = uaddr.wrapping_add(size as CULong);
    let mut addr = uaddr & PAGE_MASK;

    while addr < uend {
        if addr == 0 {
            return -EINVAL;
        }

        let error = unsafe { page_fault(vm, addr as *mut c_void, reason) };
        if error != 0 {
            if let Some(log) = log_fn {
                unsafe {
                    log(X86_USER_COPY_LOG_PF, vm, addr, reason, error);
                }
            }
            return error;
        }

        addr = addr.wrapping_add(PTL1_SIZE);
    }

    0
}

#[inline(always)]
unsafe fn x86_process_vm_copy_impl(
    vm: *mut c_void,
    pt: *mut c_void,
    user_addr: CULong,
    kernel_addr: CULong,
    size: SizeT,
    user_start: CULong,
    user_end: CULong,
    reason: CULong,
    direction: CInt,
    page_fault_fn: Option<X86UserPageFaultFn>,
    vtop_fn: Option<X86UserVtopFn>,
    is_memory_fn: Option<X86UserIsMemoryFn>,
    map_fn: Option<X86UserMapFn>,
    unmap_fn: Option<X86UserUnmapFn>,
    phys_to_virt_fn: Option<X86UserPhysToVirtFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    if (reason & PF_PATCH) != 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    X86_USER_COPY_LOG_PATCH_START,
                    vm,
                    user_addr,
                    kernel_addr,
                    size as CInt,
                );
            }
        }
    }

    let verify_error = unsafe {
        x86_verify_process_vm_result(
            vm,
            user_addr,
            size,
            user_start,
            user_end,
            reason,
            page_fault_fn,
            log_fn,
        )
    };
    if verify_error != 0 {
        if (reason & PF_PATCH) != 0 {
            if let Some(log) = log_fn {
                let event = if verify_error == -EFAULT {
                    X86_USER_COPY_LOG_PATCH_RANGE
                } else {
                    X86_USER_COPY_LOG_PATCH_PF
                };
                unsafe {
                    log(event, vm, user_addr, size as CULong, verify_error);
                }
            }
        }
        return verify_error;
    }

    let (Some(vtop), Some(is_memory), Some(map), Some(unmap), Some(phys_to_virt)) =
        (vtop_fn, is_memory_fn, map_fn, unmap_fn, phys_to_virt_fn)
    else {
        return -EFAULT;
    };

    let mut user_cursor = user_addr;
    let mut kernel_cursor = kernel_addr;
    let mut remain = size as CULong;

    while remain > 0 {
        let mut cpsize = PTL1_SIZE - (user_cursor & (PTL1_SIZE - 1));
        if cpsize > remain {
            cpsize = remain;
        }

        let mut pa = 0;
        let error = unsafe { vtop(pt, user_cursor as *const c_void, &mut pa) };
        if error != 0 {
            if let Some(log) = log_fn {
                let event = if (reason & PF_PATCH) != 0 {
                    X86_USER_COPY_LOG_PATCH_VTOP
                } else {
                    X86_USER_COPY_LOG_VTOP
                };
                unsafe {
                    log(event, vm, user_cursor, pa, error);
                }
            }
            return error;
        }

        let is_lwk = unsafe { is_memory(pa, pa.wrapping_add(cpsize)) };
        let va = if is_lwk == 0 {
            if let Some(log) = log_fn {
                unsafe {
                    log(X86_USER_COPY_LOG_EXTERNAL, vm, pa, cpsize, 0);
                }
            }
            unsafe { map(pa, 1, PTATTR_ACTIVE) }
        } else {
            unsafe { phys_to_virt(pa) }
        };

        if va.is_null() {
            return -EFAULT;
        }

        if direction == X86_USER_COPY_READ {
            unsafe {
                x86_user_copy_bytes(kernel_cursor as *mut u8, va as *const u8, cpsize as usize);
            }
        } else {
            unsafe {
                x86_user_copy_bytes(va as *mut u8, kernel_cursor as *const u8, cpsize as usize);
            }
        }

        if is_lwk == 0 {
            unsafe {
                unmap(va, 1);
            }
        }

        user_cursor = user_cursor.wrapping_add(cpsize);
        kernel_cursor = kernel_cursor.wrapping_add(cpsize);
        remain -= cpsize;
    }

    if (reason & PF_PATCH) != 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(X86_USER_COPY_LOG_PATCH_DONE, vm, user_addr, kernel_addr, 0);
            }
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_process_vm_copy_result(
    vm: *mut c_void,
    pt: *mut c_void,
    user_addr: CULong,
    kernel_addr: CULong,
    size: SizeT,
    user_start: CULong,
    user_end: CULong,
    reason: CULong,
    direction: CInt,
    page_fault_fn: Option<X86UserPageFaultFn>,
    vtop_fn: Option<X86UserVtopFn>,
    is_memory_fn: Option<X86UserIsMemoryFn>,
    map_fn: Option<X86UserMapFn>,
    unmap_fn: Option<X86UserUnmapFn>,
    phys_to_virt_fn: Option<X86UserPhysToVirtFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    unsafe {
        x86_process_vm_copy_impl(
            vm,
            pt,
            user_addr,
            kernel_addr,
            size,
            user_start,
            user_end,
            reason,
            direction,
            page_fault_fn,
            vtop_fn,
            is_memory_fn,
            map_fn,
            unmap_fn,
            phys_to_virt_fn,
            log_fn,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_copy_from_user_result(
    vm: *mut c_void,
    dst: *mut c_void,
    src: *const c_void,
    size: SizeT,
    read_fn: Option<X86ReadProcessVmFn>,
) -> CInt {
    match read_fn {
        Some(read) => unsafe { read(vm, dst, src, size) },
        None => -EFAULT,
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_copy_to_user_result(
    vm: *mut c_void,
    dst: *mut c_void,
    src: *const c_void,
    size: SizeT,
    write_fn: Option<X86WriteProcessVmFn>,
) -> CInt {
    match write_fn {
        Some(write) => unsafe { write(vm, dst, src, size) },
        None => -EFAULT,
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_getlong_user_result(
    dest: *mut i64,
    src: *const i64,
    copy_fn: Option<X86CopyFromUserFn>,
) -> CLong {
    match copy_fn {
        Some(copy) => unsafe {
            copy(dest.cast(), src.cast(), core::mem::size_of::<i64>()) as CLong
        },
        None => -EFAULT as CLong,
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_getint_user_result(
    dest: *mut CInt,
    src: *const CInt,
    copy_fn: Option<X86CopyFromUserFn>,
) -> CInt {
    match copy_fn {
        Some(copy) => unsafe { copy(dest.cast(), src.cast(), core::mem::size_of::<CInt>()) },
        None => -EFAULT,
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_setlong_user_result(
    dst: *mut i64,
    data: i64,
    copy_fn: Option<X86CopyToUserFn>,
) -> CInt {
    match copy_fn {
        Some(copy) => unsafe {
            copy(
                dst.cast(),
                (&data as *const i64).cast(),
                core::mem::size_of::<i64>(),
            )
        },
        None => -EFAULT,
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_setint_user_result(
    dst: *mut CInt,
    data: CInt,
    copy_fn: Option<X86CopyToUserFn>,
) -> CInt {
    match copy_fn {
        Some(copy) => unsafe {
            copy(
                dst.cast(),
                (&data as *const CInt).cast(),
                core::mem::size_of::<CInt>(),
            )
        },
        None => -EFAULT,
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_strlen_user_result(
    vm: *mut c_void,
    src: *const i8,
    map_kernel_start: CULong,
    verify_fn: Option<X86UserPageFaultFn>,
) -> CInt {
    let mut maxlen = PTL1_SIZE - ((src as CULong) & (PTL1_SIZE - 1));
    let pgstart = (src as CULong) & PAGE_MASK;
    let head = src as CULong;
    let mut cur = src;
    let Some(verify) = verify_fn else {
        return -EFAULT;
    };

    if pgstart == 0 || pgstart >= map_kernel_start {
        return -EFAULT;
    }

    loop {
        let error = unsafe { verify(vm, cur.cast_mut().cast(), 1) };
        if error != 0 {
            return error;
        }

        while unsafe { read_volatile(cur) } != 0 && maxlen > 0 {
            cur = unsafe { cur.add(1) };
            maxlen -= 1;
        }
        if unsafe { read_volatile(cur) } == 0 {
            return (cur as CULong).wrapping_sub(head) as CInt;
        }
        maxlen = PTL1_SIZE;
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_strcpy_from_user_result(
    vm: *mut c_void,
    dst: *mut i8,
    src: *const i8,
    map_kernel_start: CULong,
    verify_fn: Option<X86UserPageFaultFn>,
) -> CInt {
    let mut maxlen = PTL1_SIZE - ((src as CULong) & (PTL1_SIZE - 1));
    let pgstart = (src as CULong) & PAGE_MASK;
    let Some(verify) = verify_fn else {
        return -EFAULT;
    };

    if pgstart == 0 || pgstart >= map_kernel_start {
        return -EFAULT;
    }

    let mut from = src;
    let mut to = dst;
    loop {
        let error = unsafe { verify(vm, from.cast_mut().cast(), 1) };
        if error != 0 {
            return error;
        }

        while unsafe { read_volatile(from) } != 0 && maxlen > 0 {
            let byte = unsafe { read_volatile(from) };
            unsafe {
                write_volatile(to, byte);
            }
            from = unsafe { from.add(1) };
            to = unsafe { to.add(1) };
            maxlen -= 1;
        }
        if unsafe { read_volatile(from) } == 0 {
            unsafe {
                write_volatile(to, 0);
            }
            break;
        }
        maxlen = PTL1_SIZE;
    }

    0
}

#[inline]
unsafe fn x86_current_vm(thread: *mut c_void) -> *mut ProcessVm {
    unsafe { (*(thread as *mut Thread)).vm }
}

#[inline]
unsafe fn x86_process_vm_page_table(vm: *mut ProcessVm) -> *mut c_void {
    unsafe { (*(*vm).address_space).page_table }
}

#[no_mangle]
pub unsafe extern "C" fn x86_copy_from_user_public_result(
    thread: *mut c_void,
    dst: *mut c_void,
    src: *const c_void,
    size: SizeT,
    read_fn: Option<X86ReadProcessVmFn>,
) -> CInt {
    let vm = unsafe { x86_current_vm(thread) };
    unsafe { x86_copy_from_user_result(vm.cast(), dst, src, size, read_fn) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_copy_to_user_public_result(
    thread: *mut c_void,
    dst: *mut c_void,
    src: *const c_void,
    size: SizeT,
    write_fn: Option<X86WriteProcessVmFn>,
) -> CInt {
    let vm = unsafe { x86_current_vm(thread) };
    unsafe { x86_copy_to_user_result(vm.cast(), dst, src, size, write_fn) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_copy_from_user_direct_public_result(
    thread: *mut c_void,
    dst: *mut c_void,
    src: *const c_void,
    size: SizeT,
    page_fault_fn: Option<X86UserPageFaultFn>,
    vtop_fn: Option<X86UserVtopFn>,
    is_memory_fn: Option<X86UserIsMemoryFn>,
    map_fn: Option<X86UserMapFn>,
    unmap_fn: Option<X86UserUnmapFn>,
    phys_to_virt_fn: Option<X86UserPhysToVirtFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    let vm = unsafe { x86_current_vm(thread) };
    let page_table = unsafe { x86_process_vm_page_table(vm) };
    let user_start = unsafe { (*vm).region.user_start };
    let user_end = unsafe { (*vm).region.user_end };

    unsafe {
        x86_process_vm_copy_impl(
            vm.cast(),
            page_table,
            src as CULong,
            dst as CULong,
            size,
            user_start,
            user_end,
            PF_USER,
            X86_USER_COPY_READ,
            page_fault_fn,
            vtop_fn,
            is_memory_fn,
            map_fn,
            unmap_fn,
            phys_to_virt_fn,
            log_fn,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_copy_to_user_direct_public_result(
    thread: *mut c_void,
    dst: *mut c_void,
    src: *const c_void,
    size: SizeT,
    page_fault_fn: Option<X86UserPageFaultFn>,
    vtop_fn: Option<X86UserVtopFn>,
    is_memory_fn: Option<X86UserIsMemoryFn>,
    map_fn: Option<X86UserMapFn>,
    unmap_fn: Option<X86UserUnmapFn>,
    phys_to_virt_fn: Option<X86UserPhysToVirtFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    let vm = unsafe { x86_current_vm(thread) };
    let page_table = unsafe { x86_process_vm_page_table(vm) };
    let user_start = unsafe { (*vm).region.user_start };
    let user_end = unsafe { (*vm).region.user_end };

    unsafe {
        x86_process_vm_copy_impl(
            vm.cast(),
            page_table,
            dst as CULong,
            src as CULong,
            size,
            user_start,
            user_end,
            PF_POPULATE | PF_WRITE | PF_USER,
            X86_USER_COPY_WRITE,
            page_fault_fn,
            vtop_fn,
            is_memory_fn,
            map_fn,
            unmap_fn,
            phys_to_virt_fn,
            log_fn,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_strlen_user_public_result(
    thread: *mut c_void,
    src: *const i8,
    map_kernel_start: CULong,
    verify_fn: Option<X86UserPageFaultFn>,
) -> CInt {
    let vm = unsafe { x86_current_vm(thread) };
    unsafe { x86_strlen_user_result(vm.cast(), src, map_kernel_start, verify_fn) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_strcpy_from_user_public_result(
    thread: *mut c_void,
    dst: *mut i8,
    src: *const i8,
    map_kernel_start: CULong,
    verify_fn: Option<X86UserPageFaultFn>,
) -> CInt {
    let vm = unsafe { x86_current_vm(thread) };
    unsafe { x86_strcpy_from_user_result(vm.cast(), dst, src, map_kernel_start, verify_fn) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_getlong_user_public_result(
    dest: *mut i64,
    src: *const i64,
    copy_fn: Option<X86CopyFromUserFn>,
) -> CLong {
    unsafe { x86_getlong_user_result(dest, src, copy_fn) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_getint_user_public_result(
    dest: *mut CInt,
    src: *const CInt,
    copy_fn: Option<X86CopyFromUserFn>,
) -> CInt {
    unsafe { x86_getint_user_result(dest, src, copy_fn) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_setlong_user_public_result(
    dst: *mut i64,
    data: i64,
    copy_fn: Option<X86CopyToUserFn>,
) -> CInt {
    unsafe { x86_setlong_user_result(dst, data, copy_fn) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_setint_user_public_result(
    dst: *mut CInt,
    data: CInt,
    copy_fn: Option<X86CopyToUserFn>,
) -> CInt {
    unsafe { x86_setint_user_result(dst, data, copy_fn) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_verify_process_vm_public_result(
    vm: *mut ProcessVm,
    usrc: *const c_void,
    size: SizeT,
    page_fault_fn: Option<X86UserPageFaultFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    let user_start = unsafe { (*vm).region.user_start };
    let user_end = unsafe { (*vm).region.user_end };

    unsafe {
        x86_verify_process_vm_result(
            vm.cast(),
            usrc as CULong,
            size,
            user_start,
            user_end,
            PF_USER,
            page_fault_fn,
            log_fn,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_read_process_vm_public_result(
    vm: *mut ProcessVm,
    kdst: *mut c_void,
    usrc: *const c_void,
    size: SizeT,
    page_fault_fn: Option<X86UserPageFaultFn>,
    vtop_fn: Option<X86UserVtopFn>,
    is_memory_fn: Option<X86UserIsMemoryFn>,
    map_fn: Option<X86UserMapFn>,
    unmap_fn: Option<X86UserUnmapFn>,
    phys_to_virt_fn: Option<X86UserPhysToVirtFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    let page_table = unsafe { x86_process_vm_page_table(vm) };
    let user_start = unsafe { (*vm).region.user_start };
    let user_end = unsafe { (*vm).region.user_end };

    unsafe {
        x86_process_vm_copy_impl(
            vm.cast(),
            page_table,
            usrc as CULong,
            kdst as CULong,
            size,
            user_start,
            user_end,
            PF_USER,
            X86_USER_COPY_READ,
            page_fault_fn,
            vtop_fn,
            is_memory_fn,
            map_fn,
            unmap_fn,
            phys_to_virt_fn,
            log_fn,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_write_process_vm_public_result(
    vm: *mut ProcessVm,
    udst: *mut c_void,
    ksrc: *const c_void,
    size: SizeT,
    page_fault_fn: Option<X86UserPageFaultFn>,
    vtop_fn: Option<X86UserVtopFn>,
    is_memory_fn: Option<X86UserIsMemoryFn>,
    map_fn: Option<X86UserMapFn>,
    unmap_fn: Option<X86UserUnmapFn>,
    phys_to_virt_fn: Option<X86UserPhysToVirtFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    let page_table = unsafe { x86_process_vm_page_table(vm) };
    let user_start = unsafe { (*vm).region.user_start };
    let user_end = unsafe { (*vm).region.user_end };

    unsafe {
        x86_process_vm_copy_impl(
            vm.cast(),
            page_table,
            udst as CULong,
            ksrc as CULong,
            size,
            user_start,
            user_end,
            PF_POPULATE | PF_WRITE | PF_USER,
            X86_USER_COPY_WRITE,
            page_fault_fn,
            vtop_fn,
            is_memory_fn,
            map_fn,
            unmap_fn,
            phys_to_virt_fn,
            log_fn,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_patch_process_vm_public_result(
    vm: *mut ProcessVm,
    udst: *mut c_void,
    ksrc: *const c_void,
    size: SizeT,
    page_fault_fn: Option<X86UserPageFaultFn>,
    vtop_fn: Option<X86UserVtopFn>,
    is_memory_fn: Option<X86UserIsMemoryFn>,
    map_fn: Option<X86UserMapFn>,
    unmap_fn: Option<X86UserUnmapFn>,
    phys_to_virt_fn: Option<X86UserPhysToVirtFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    let page_table = unsafe { x86_process_vm_page_table(vm) };
    let user_start = unsafe { (*vm).region.user_start };
    let user_end = unsafe { (*vm).region.user_end };

    unsafe {
        x86_process_vm_copy_impl(
            vm.cast(),
            page_table,
            udst as CULong,
            ksrc as CULong,
            size,
            user_start,
            user_end,
            PF_PATCH | PF_WRITE | PF_USER,
            X86_USER_COPY_WRITE,
            page_fault_fn,
            vtop_fn,
            is_memory_fn,
            map_fn,
            unmap_fn,
            phys_to_virt_fn,
            log_fn,
        )
    }
}

#[inline]
unsafe fn x86_current_thread_for_user_copy() -> *mut c_void {
    let cpu = get_this_cpu_local_var();
    if cpu.is_null() {
        core::ptr::null_mut()
    } else {
        (*cpu).current.cast()
    }
}

#[no_mangle]
pub unsafe extern "C" fn copy_from_user(dst: *mut c_void, src: *const c_void, size: SizeT) -> CInt {
    x86_copy_from_user_direct_public_result(
        x86_current_thread_for_user_copy(),
        dst,
        src,
        size,
        Some(x86_user_page_fault_bridge),
        Some(x86_user_vtop_bridge),
        Some(x86_user_is_memory_bridge),
        Some(x86_user_map_bridge),
        Some(x86_user_unmap_bridge),
        Some(x86_user_phys_to_virt_bridge),
        Some(x86_user_copy_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn copy_to_user(dst: *mut c_void, src: *const c_void, size: SizeT) -> CInt {
    x86_copy_to_user_direct_public_result(
        x86_current_thread_for_user_copy(),
        dst,
        src,
        size,
        Some(x86_user_page_fault_bridge),
        Some(x86_user_vtop_bridge),
        Some(x86_user_is_memory_bridge),
        Some(x86_user_map_bridge),
        Some(x86_user_unmap_bridge),
        Some(x86_user_phys_to_virt_bridge),
        Some(x86_user_copy_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn strlen_user(src: *const i8) -> CInt {
    x86_strlen_user_public_result(
        x86_current_thread_for_user_copy(),
        src,
        x86_user_map_kernel_start_bridge(),
        Some(x86_user_verify_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn strcpy_from_user(dst: *mut i8, src: *const i8) -> CInt {
    x86_strcpy_from_user_public_result(
        x86_current_thread_for_user_copy(),
        dst,
        src,
        x86_user_map_kernel_start_bridge(),
        Some(x86_user_verify_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn getlong_user(dest: *mut CLong, src: *const CLong) -> CLong {
    x86_getlong_user_public_result(dest, src, Some(copy_from_user))
}

#[no_mangle]
pub unsafe extern "C" fn getint_user(dest: *mut CInt, src: *const CInt) -> CInt {
    x86_getint_user_public_result(dest, src, Some(copy_from_user))
}

#[no_mangle]
pub unsafe extern "C" fn setlong_user(dst: *mut CLong, data: CLong) -> CInt {
    x86_setlong_user_public_result(dst, data, Some(copy_to_user))
}

#[no_mangle]
pub unsafe extern "C" fn setint_user(dst: *mut CInt, data: CInt) -> CInt {
    x86_setint_user_public_result(dst, data, Some(copy_to_user))
}

#[no_mangle]
pub unsafe extern "C" fn verify_process_vm(
    vm: *mut ProcessVm,
    usrc: *const c_void,
    size: SizeT,
) -> CInt {
    x86_verify_process_vm_public_result(
        vm,
        usrc,
        size,
        Some(x86_user_page_fault_bridge),
        Some(x86_user_copy_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn read_process_vm(
    vm: *mut ProcessVm,
    kdst: *mut c_void,
    usrc: *const c_void,
    size: SizeT,
) -> CInt {
    x86_read_process_vm_public_result(
        vm,
        kdst,
        usrc,
        size,
        Some(x86_user_page_fault_bridge),
        Some(x86_user_vtop_bridge),
        Some(x86_user_is_memory_bridge),
        Some(x86_user_map_bridge),
        Some(x86_user_unmap_bridge),
        Some(x86_user_phys_to_virt_bridge),
        Some(x86_user_copy_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn write_process_vm(
    vm: *mut ProcessVm,
    udst: *mut c_void,
    ksrc: *const c_void,
    size: SizeT,
) -> CInt {
    x86_write_process_vm_public_result(
        vm,
        udst,
        ksrc,
        size,
        Some(x86_user_page_fault_bridge),
        Some(x86_user_vtop_bridge),
        Some(x86_user_is_memory_bridge),
        Some(x86_user_map_bridge),
        Some(x86_user_unmap_bridge),
        Some(x86_user_phys_to_virt_bridge),
        Some(x86_user_copy_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn patch_process_vm(
    vm: *mut ProcessVm,
    udst: *mut c_void,
    ksrc: *const c_void,
    size: SizeT,
) -> CInt {
    x86_patch_process_vm_public_result(
        vm,
        udst,
        ksrc,
        size,
        Some(x86_user_page_fault_bridge),
        Some(x86_user_vtop_bridge),
        Some(x86_user_is_memory_bridge),
        Some(x86_user_map_bridge),
        Some(x86_user_unmap_bridge),
        Some(x86_user_phys_to_virt_bridge),
        Some(x86_user_copy_log_bridge),
    )
}
