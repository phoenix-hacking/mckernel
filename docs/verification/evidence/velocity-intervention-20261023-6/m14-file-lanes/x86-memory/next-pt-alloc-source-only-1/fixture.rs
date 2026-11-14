#![no_std]
#![allow(dead_code,unused_imports)]
#[path="/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/passed-six-provider-current-union-production-preparation-1/source/kernel/rust/abi.rs"] mod abi;
use abi::{CInt,CULong};
use core::ffi::c_void;
unsafe extern "C" {
    fn _ihk_mc_alloc_aligned_pages_node(npages: CInt, p2align: CInt, flag: CULong, node: CInt, is_user: CInt, virt_addr: CULong, file: *mut i8, line: CInt) -> *mut c_void;
    static x86_pt_alloc_pages_file: [i8; 1];
    static x86_pt_alloc_pages_line: CInt;
    static x86_pt_alloc_pages_p2align: CInt;
    static x86_pt_alloc_pages_is_user: CInt;
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
