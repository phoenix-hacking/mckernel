#![no_std]
#![allow(dead_code,unused_imports)]
#[path="rust/abi.rs"] mod abi;
#[path="rust/spinlock_helpers.rs"] mod spinlock_helpers;
#[path="rust/page_helpers.rs"] mod page_helpers;
use abi::{CInt,CULong};
use page_helpers::Page;
use core::ffi::c_void;
use core::ptr::write_bytes;
const KERNEL_BASE: CULong = 0xffff000000000000;
const PT_ENTRIES: CULong = 512;
type X86PtAllocPagesFn = unsafe extern "C" fn(CInt, CInt) -> *mut c_void;
type X86PtVirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type X86PtPhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type X86PtSetPageLogFn = unsafe extern "C" fn(CULong);
unsafe extern "C" {
    fn x86_init_page_table_lock_bridge() -> *mut c_void;
    fn x86_page_table_init_pt_bridge() -> *mut c_void;
    fn x86_attr_mask_bridge() -> CULong;
    fn x86_pt_virt_to_phys_bridge(addr: *mut c_void) -> CULong;
    fn x86_pt_phys_to_virt_bridge(phys: CULong) -> *mut c_void;
    fn _ihk_mc_alloc_aligned_pages_node(npages: CInt, p2align: CInt, flag: CULong, node: CInt, is_user: CInt, virt_addr: CULong, file: *mut i8, line: CInt) -> *mut c_void;
    static x86_pt_alloc_pages_file: [i8; 1];
    static x86_pt_alloc_pages_line: CInt;
    static x86_pt_alloc_pages_p2align: CInt;
    static x86_pt_alloc_pages_is_user: CInt;
    fn x86_pt_set_page_log_bridge(virt:CULong);
    fn x86_pt_set_page_body_result(pt:*mut c_void,init_pt:*mut c_void,
      virt:CULong,phys:CULong,attr:CULong,mask:CULong,
      alloc:Option<X86PtAllocPagesFn>,vp:Option<X86PtVirtToPhysFn>,
      pv:Option<X86PtPhysToVirtFn>,log:Option<X86PtSetPageLogFn>)->CInt;
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
pub unsafe extern "C" fn x86_pt_alloc_pages_bridge(nr_pages: CInt, ap_flag: CInt) -> *mut c_void {
    unsafe {
        _ihk_mc_alloc_aligned_pages_node(
            nr_pages, x86_pt_alloc_pages_p2align, ap_flag as CULong,
            -1, x86_pt_alloc_pages_is_user, CULong::MAX,
            core::ptr::addr_of!(x86_pt_alloc_pages_file).cast::<i8>() as *mut i8,
            x86_pt_alloc_pages_line,
        )
    }
}
#[no_mangle]
pub unsafe extern "C" fn x86_pt_set_page_bridge(
    pt: *mut c_void, virt: CULong, phys: CULong, attr: CULong,
) -> CInt {
    unsafe {
        let in_kernel = x86_pt_kernel_lock_needed_result(virt) != 0;
        let mut lock: *mut crate::spinlock_helpers::IhkSpinlock = core::ptr::null_mut();
        let mut flags: CULong = 0;
        if in_kernel {
            lock = x86_init_page_table_lock_bridge().cast();
            flags = crate::spinlock_helpers::__ihk_mc_spinlock_lock(lock);
        }
        // Read init_pt after acquisition, exactly as the original C body did.
        let ret = x86_pt_set_page_body_result(
            pt, x86_page_table_init_pt_bridge(), virt, phys, attr,
            x86_attr_mask_bridge(), Some(x86_pt_alloc_pages_bridge),
            Some(x86_pt_virt_to_phys_bridge), Some(x86_pt_phys_to_virt_bridge),
            Some(x86_pt_set_page_log_bridge),
        );
        if in_kernel {
            crate::spinlock_helpers::__ihk_mc_spinlock_unlock(lock, flags);
        }
        ret
    }
}
#[no_mangle]
pub unsafe extern "C" fn x86_split_alloc_new_pt_bridge(
    nr_pages: CInt, ap_flag: CInt,
) -> *mut c_void {
    if nr_pages != 1 {
        return core::ptr::null_mut();
    }
    unsafe { x86_pt_alloc_zeroed_result(ap_flag, Some(x86_pt_alloc_pages_bridge)) }
}
#[no_mangle]
pub unsafe extern "C" fn x86_split_page_map_bridge(page: *mut c_void) {
    unsafe { crate::page_helpers::page_map(page.cast::<Page>()) }
}
#[no_mangle]
pub unsafe extern "C" fn x86_split_page_unmap_bridge(page: *mut c_void) -> CInt {
    unsafe { crate::page_helpers::page_unmap(page.cast::<Page>()) }
}
