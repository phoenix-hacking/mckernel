#![no_std]
#![allow(dead_code)]
#[path="/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_abi.rs"]mod abi;
use core::ffi::c_void;
use core::ptr::null_mut;
use abi::{CInt,CULong};
const EINVAL:CInt=22;
type MemVmapInitFn=unsafe extern "C" fn(CULong,CULong,CULong)->*mut c_void;
type MemPtPrepareMapFn=unsafe extern "C" fn(*mut c_void,*mut c_void,CULong,CInt)->CInt;
// Fixture-only declarations route exact public provider ABIs to controlled C.
// Production source calls the existing full Rust modules, never this fixture.
mod page_alloc {
 use core::ffi::c_void;use crate::abi::{CInt,CULong};
 unsafe extern "C" {
  pub fn ihk_pagealloc_init(start:CULong,size:CULong,unit:CULong)->*mut c_void;
  pub fn ihk_pagealloc_alloc(desc:*mut c_void,npages:CInt,p2align:CInt)->CULong;
  pub fn ihk_pagealloc_free(desc:*mut c_void,address:CULong,npages:CInt);
 }
}
mod x86_memory_helpers {
 use core::ffi::c_void;use crate::abi::{CInt,CULong};
 unsafe extern "C" {pub fn ihk_mc_pt_prepare_map(pt:*mut c_void,virt:*mut c_void,size:CULong,flag:CInt)->CInt;}
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
