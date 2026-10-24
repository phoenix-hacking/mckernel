// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Genuine default-std HOST runtime; no fake panic or kernel hardware provider.
#![allow(dead_code,unused_imports,private_interfaces)]
#[path="abi.ACTUAL.rs"]mod abi;
#[path="native_xstate.ACTUAL.rs"]mod native_xstate;
use core::ffi::c_void;
use core::mem::{size_of,align_of};
use abi::{CInt,CLong,CULong,SizeT};
const ENOMEM:CInt=12;
const EFAULT:CInt=14;
const IHK_MC_AP_NOWAIT:CULong=0x000002;
unsafe extern "C" {
 fn get_xsave_size()->CInt;
 fn get_xsave_mask()->CULong;
 fn kmalloc_tracked(size:CInt,flags:CULong,file:*mut i8,line:CInt)->*mut c_void;
 fn kfree_tracked(p:*mut c_void,file:*mut i8,line:CInt);
 fn copy_from_user(dst:*mut c_void,src:*const c_void,size:SizeT)->CInt;
}
mod x86_cpu_helpers {use super::*;
 pub unsafe extern "C" fn get_xsave_size()->CInt {super::get_xsave_size()}
 pub unsafe extern "C" fn get_xsave_mask()->CULong {super::get_xsave_mask()}}
mod mem_helpers {use super::*;
 pub unsafe extern "C" fn kmalloc_tracked(n:CInt,f:CULong,p:*mut i8,l:CInt)->*mut c_void {super::kmalloc_tracked(n,f,p,l)}
 pub unsafe extern "C" fn kfree_tracked(p:*mut c_void,f:*mut i8,l:CInt) {super::kfree_tracked(p,f,l)}}
mod x86_memory_helpers {use super::*;
 pub unsafe extern "C" fn copy_from_user(d:*mut c_void,s:*const c_void,n:SizeT)->CInt {super::copy_from_user(d,s,n)}}
include!("candidate-entry.ACTUAL.inc");
#[no_mangle]pub extern "C" fn fixture_fp_actual_Rust_ABI(i:usize)->usize {
 let a=[size_of::<CInt>(),size_of::<CLong>(),size_of::<CULong>(),size_of::<SizeT>(),size_of::<*mut c_void>(),IHK_MC_AP_NOWAIT as usize,65536+63];a[i]
}
