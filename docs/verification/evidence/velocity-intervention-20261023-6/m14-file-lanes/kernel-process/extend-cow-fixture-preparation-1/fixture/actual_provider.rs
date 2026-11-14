// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
use core::ffi::c_void;use core::ptr::null_mut;
use abi::{CInt,CULong,SizeT,ProcessVm,Process,VmRange,Memobj};
const VR_DEMAND_PAGING:CULong=0x1000;const VR_PRIVATE:CULong=0x2000;
const VR_PROT_WRITE:CULong=0x20000;const PF_PATCH:CULong=1<<29;
mod debug { include!("debug_type.ACTUAL-RUST.rs"); }
mod page_helpers { include!("page_predicates.ACTUAL-RUST.rs"); }
extern "C" {
 fn kprintf(format:*const i8,...)->CInt;
 fn lookup_process_memory_range(vm:*mut ProcessVm,start:CULong,end:CULong)->*mut VmRange;
 fn add_process_memory_range(vm:*mut ProcessVm,start:CULong,end:CULong,phys:CULong,
  flag:CULong,obj:*mut c_void,off:abi::OffT,shift:CInt,data:*mut c_void,rp:*mut *mut VmRange)->CInt;
}
mod mem_helpers {
 use super::*;
 extern "C" {
  pub fn _ihk_mc_alloc_aligned_pages_node(n:CInt,a:CInt,f:CULong,node:CInt,user:CInt,
   addr:CULong,file:*mut i8,line:CInt)->*mut c_void;
  pub fn _ihk_mc_free_pages(p:*mut c_void,n:CInt,user:CInt,file:*mut i8,line:CInt);
 }
}
mod x86_memory_helpers {
 use super::*;extern "C" { pub fn virt_to_phys(p:*mut c_void)->CULong; }
}
include!("extend_region.ACTUAL-RUST.inc");
include!("cow_classify.ACTUAL-RUST.inc");
#[no_mangle]pub unsafe extern "C" fn fixture_layout(out:*mut usize) {
 use core::mem::{size_of,align_of,offset_of};
 let p=page_helpers::fixture_layout();
 let x=[size_of::<ProcessVm>(),align_of::<ProcessVm>(),offset_of!(ProcessVm,proc),
 size_of::<Process>(),align_of::<Process>(),offset_of!(Process,mpol_flags),offset_of!(Process,heap_extension),
 size_of::<CULong>(),size_of::<CULong>(),size_of::<debug::Ddebug>(),align_of::<debug::Ddebug>(),
 size_of::<VmRange>(),offset_of!(VmRange,flag),offset_of!(VmRange,memobj),
 size_of::<Memobj>(),offset_of!(Memobj,flags),
 p[0],p[1],p[2],p[3],p[4]];
 core::ptr::copy_nonoverlapping(x.as_ptr(),out,x.len());
}
