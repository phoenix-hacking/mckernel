// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
use core::ffi::c_void;use core::ptr::null_mut;
use abi::{CInt,CULong,SizeT,ProcessVm,VmRange,IhkSpinlock};
const PF_PATCH:CULong=1<<29;const EFAULT:CInt=14;
#[repr(C)] pub struct Ddebug { file:*const i8,func:*const i8,fmt:*const i8,line_flags:u32 }
extern "C" {
 static mut process_page_fault_prepare_bounds_debug:Ddebug;
 fn ihk_mc_pt_lookup_pte(pt:*mut c_void,virt:*mut c_void,shift:CInt,base:*mut *mut c_void,size:*mut SizeT,align:*mut CInt)->*mut CULong;
 fn kprintf(format:*const i8,...)->CInt;
}
mod spinlock_helpers { use crate::abi::IhkSpinlock;extern "C" { pub fn __ihk_mc_spinlock_lock_noirq(lock:*mut IhkSpinlock); } }
use spinlock_helpers::__ihk_mc_spinlock_lock_noirq;
mod pte_helpers { include!("pte_provider.ACTUAL-RUST.inc"); }
mod smaller { include!("smaller_provider.ACTUAL-RUST.inc"); }
mod x86_memory_helpers {
 use core::ffi::c_void;use crate::abi::{CULong,CInt,SizeT};
 extern "C" { pub fn flush_tlb_single(addr:CULong);pub fn arch_get_smaller_page_size(args:*mut c_void,size:SizeT,newsize:*mut SizeT,align:*mut CInt)->CInt; }
}
include!("page_fault_prepare.ACTUAL-RUST.inc");
#[no_mangle] pub unsafe extern "C" fn fixture_layout(out:*mut usize) {
 use core::mem::{size_of,align_of,offset_of};
 let x=[size_of::<ProcessVm>(),align_of::<ProcessVm>(),offset_of!(ProcessVm,address_space),offset_of!(ProcessVm,page_table_lock),
 size_of::<abi::AddressSpace>(),offset_of!(abi::AddressSpace,page_table),size_of::<VmRange>(),offset_of!(VmRange,start),offset_of!(VmRange,end),offset_of!(VmRange,flag),offset_of!(VmRange,pgshift),size_of::<IhkSpinlock>(),size_of::<Ddebug>()];
 core::ptr::copy_nonoverlapping(x.as_ptr(),out,x.len());
}
