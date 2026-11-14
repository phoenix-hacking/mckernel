// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// No executable queue. The model below tests decision/ownership handoff only;
// exact production allocator source remains in allocator.EXISTING-RUST-REFERENCE.inc.
#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
use core::ffi::c_void;use core::ptr::null_mut;
use abi::{CInt,CULong,SizeT,ProcessVm,VmRange};
const PAGE_SIZE:CULong=4096;const IHK_MC_AP_NOWAIT:CULong=2;
const VR_AP_USER:CULong=4;const ENOMEM:CInt=12;
extern "C" {
 static process_page_fault_anon_alloc_file:*const i8;
 static process_page_fault_anon_alloc_line:CInt;
 fn kprintf(format:*const i8,...)->CInt;
}
mod mem_helpers {
 use core::ffi::c_void;use crate::abi::{CInt,CULong};
 extern "C" { fn fixture_alloc_effect(n:CInt,a:CInt,f:CULong,node:CInt,user:CInt,addr:CULong,file:*mut i8,line:CInt)->*mut c_void; }
 pub unsafe fn _ihk_mc_alloc_aligned_pages_node(n:CInt,a:CInt,f:CULong,node:CInt,user:CInt,addr:CULong,file:*mut i8,line:CInt)->*mut c_void {
  fixture_alloc_effect(n,a,f,node,user,addr,file,line)
 }
}
mod x86_memory_helpers {
 use core::ffi::c_void;use crate::abi::{CInt,SizeT};
 extern "C" { pub fn arch_get_smaller_page_size(args:*mut c_void,size:SizeT,out:*mut SizeT,align:*mut CInt)->CInt; }
}
include!("anon_allocate.ACTUAL-RUST.inc");
