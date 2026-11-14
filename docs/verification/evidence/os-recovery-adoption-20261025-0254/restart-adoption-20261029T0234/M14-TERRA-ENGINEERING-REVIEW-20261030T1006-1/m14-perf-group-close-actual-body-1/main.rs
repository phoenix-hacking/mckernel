#![allow(dead_code,unused_variables,unused_imports,static_mut_refs)]
#[path="/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/f06-debug-constants-align32-host-1/src/kernel/rust/abi.rs"] mod abi;
use abi::{CInt,CLong,CULong,SizeT,SyscallRequest,AbiListHead};
use core::ffi::c_void;use core::mem::{offset_of,size_of};use core::ptr::{read_volatile,write_volatile};
const EINVAL:CInt=22;const ENOMEM:CInt=12;const ENOENT:CInt=2;const EFAULT:CInt=14;
type PerfOpenAllocEventFn=unsafe extern "C" fn(*mut *mut c_void,*mut c_void)->CInt;
type PerfCounterAllocFn=unsafe extern "C" fn(*mut c_void,*mut c_void)->CInt;
type PerfOpenSyscallFn=unsafe extern "C" fn(*mut SyscallRequest,CInt)->CLong;
type SyscallPolicyAllocFn=unsafe extern "C" fn(SizeT,CULong)->*mut c_void;
type SyscallMckfdLongFn=unsafe extern "C" fn(*mut c_void,*mut c_void)->CLong;
type SyscallMckfdIntFn=unsafe extern "C" fn(*mut c_void,*mut c_void)->CInt;
type SyscallMckfdLockFn=unsafe extern "C" fn(*mut c_void)->CLong;
type SyscallMckfdUnlockFn=unsafe extern "C" fn(*mut c_void,CLong);
type SyscallMckfdFreeFn=unsafe extern "C" fn(*mut c_void);
type SyscallCopyFromUserFn=unsafe extern "C" fn(*mut u8,CULong,SizeT)->CLong;
type PerfAttrFreqFn=unsafe extern "C" fn(*const c_void)->CInt;
include!("rust_actual.rs");
#[path="/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/f06-debug-constants-align32-host-1/src/kernel/rust/f03_perf_group_cleanup.rs"] mod group;
#[repr(C)] struct Event {pid:i32,counter:i32,leader:*mut c_void,siblings:AbiListHead,entry:AbiListHead,nr:i32,_pad:i32,status:u64,extra_reg:i32,extra_idx:i32}
#[repr(C)] struct Fd {next:*mut Fd,fd:i32,_pad:i32,data:i64}
#[repr(C)] struct Proc {head:*mut Fd}
static mut EVENT:*mut Event=core::ptr::null_mut();static mut FREES:i32=0;static mut FREEPTR:usize=0;static mut COUNTERS:i32=0;static mut ALLOCS:i32=0;static mut COPIES:i32=0;
unsafe extern "C" fn event_alloc(out:*mut *mut c_void,_:*mut c_void)->i32 {ALLOCS+=1;*out=EVENT.cast();0}
unsafe extern "C" fn counter(_:*mut c_void,_:*mut c_void)->i32 {COUNTERS+=1;3}
unsafe extern "C" fn copy_attr(dst:*mut u8,src:u64,n:usize)->i64 {COPIES+=1;core::ptr::copy_nonoverlapping(src as *const u8,dst,n);0}
unsafe extern "C" fn freq(_:*const c_void)->i32 {0}
unsafe extern "C" fn never_alloc(_:usize,_:u64)->*mut c_void {panic!("unexpected later allocation")}
unsafe extern "C" fn perf_event_alloc_free_bridge(ptr:*mut c_void){FREES+=1;FREEPTR=ptr as usize;}
extern "C" {fn c_perf_group(event:*mut c_void,proc:*mut c_void,group_fd:i32,counter_idx:i32,proc_head:usize,fd_next:usize,fd_fd:usize,fd_data:usize,ev_leader:usize,ev_sibling:usize,ev_entry:usize,ev_nr:usize,ev_status:usize)->i64;}
fn new_event()->Event {unsafe{core::mem::zeroed()}}
#[repr(C)] struct ThreadMaps {pmc:u64,extra:u64}
fn main(){unsafe{
 let mut leader=new_event();let head=core::ptr::addr_of_mut!(leader.siblings);(*head).next=head;(*head).prev=head;
 let mut fd=Fd{next:core::ptr::null_mut(),fd:42,_pad:0,data:(&mut leader as *mut Event) as i64};let mut proc=Proc{head:&mut fd};let mut first=new_event();let mut second=new_event();let mut thread=ThreadMaps{pmc:1u64<<3,extra:0};FREES=0;FREEPTR=0;
 let off=(offset_of!(Proc,head),offset_of!(Fd,next),offset_of!(Fd,fd),offset_of!(Fd,data),offset_of!(Event,leader),offset_of!(Event,siblings),offset_of!(Event,entry),offset_of!(Event,nr),offset_of!(Event,status));
 let first_ptr=(&mut first as *mut Event).cast();let second_ptr=(&mut second as *mut Event).cast();let proc_ptr=(&mut proc as *mut Proc).cast();
 assert_eq!(perf_event_open_group_body_result(first_ptr,proc_ptr,42,3,off.0,off.1,off.2,off.3,off.4,off.5,off.6,off.7,off.8),0);
 let first_link=core::ptr::addr_of_mut!(first.entry);assert_eq!((*head).prev,first_link);assert_eq!(leader.nr,1);
 first.counter=3;assert_eq!(perf_close_body_result(first_ptr,(&mut thread as *mut ThreadMaps).cast(),offset_of!(Event,counter),offset_of!(Event,extra_reg),offset_of!(Event,extra_idx),offset_of!(ThreadMaps,pmc),offset_of!(ThreadMaps,extra),Some(perf_event_alloc_free_bridge)),0);
 assert_eq!(FREES,1);assert_eq!(FREEPTR,first_ptr as usize);assert_eq!((*head).prev,first_link);assert_eq!(leader.nr,1);assert_eq!((*first_link).next,head);
 // The free mock marks ownership only; stack storage remains alive. This safely
 // detects the later write to a logically freed link without a real UAF.
 assert_eq!(perf_event_open_group_body_result(second_ptr,proc_ptr,42,4,off.0,off.1,off.2,off.3,off.4,off.5,off.6,off.7,off.8),0);
 assert_eq!((*first_link).next,core::ptr::addr_of_mut!(second.entry));assert_eq!((*head).prev,core::ptr::addr_of_mut!(second.entry));assert_eq!(leader.nr,2);assert_eq!(FREES,1);
 println!("PASS synthetic group-add, mocked close/free and later group-add: retained closed-event link observed");
}}
