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
type SyscallCopyFromUserFn=unsafe extern "C" fn(*mut u8,CULong,SizeT)->CLong;
type PerfAttrFreqFn=unsafe extern "C" fn(*const c_void)->CInt;
include!("rust_actual.rs");
#[path="/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/f06-debug-constants-align32-host-1/src/kernel/rust/f03_perf_group_cleanup.rs"] mod group;
#[repr(C)] struct Event {pid:i32,counter:i32,leader:*mut c_void,siblings:AbiListHead,entry:AbiListHead,nr:i32,_pad:i32,status:u64}
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
fn main(){unsafe{
 for kind in 0..3 {let mut leader=new_event();leader.nr=37;leader.status=0x55;leader.siblings.next=0x1234usize as *mut AbiListHead;
 let mut fd=Fd{next:core::ptr::null_mut(),fd:42,_pad:0,data:if kind==2 {(&mut leader as *mut Event) as i64} else {0}};
 let mut proc=Proc{head:if kind==0 {core::ptr::null_mut()}else {&mut fd}};let mut event=new_event();let mut c_event=new_event();let mut req:SyscallRequest=core::mem::zeroed();let mut thread:u64=0;let input=[0u8;40];let mut attr=[0u64;5];EVENT=&mut event;FREES=0;FREEPTR=0;COUNTERS=0;ALLOCS=0;COPIES=0;
 let offs=(offset_of!(Proc,head),offset_of!(Fd,next),offset_of!(Fd,fd),offset_of!(Fd,data),offset_of!(Event,leader),offset_of!(Event,siblings),offset_of!(Event,entry),offset_of!(Event,nr),offset_of!(Event,status));
 let crc=c_perf_group((&mut c_event as *mut Event).cast(),(&mut proc as *mut Proc).cast(),42,3,offs.0,offs.1,offs.2,offs.3,offs.4,offs.5,offs.6,offs.7,offs.8);
 let rc=group::perf_entry_with_group_cleanup(&mut req,(&mut thread as *mut u64).cast(),(&mut proc as *mut Proc).cast(),attr.as_mut_ptr().cast(),input.as_ptr() as u64,40,0,32,16,17,0,42,0,7,4,0,3,7,1u64<<63,298,64,0,offset_of!(Event,pid),offset_of!(Event,counter),offs.0,offs.1,offs.2,offs.3,offs.4,offs.5,offs.6,offs.7,offs.8,0,0,0,0,0,0,0,0,Some(copy_attr),Some(freq),Some(event_alloc),Some(counter),None,Some(never_alloc),None,None,None,None,None,None,None);
 assert_eq!(crc,-22);assert_eq!(rc,crc);assert_eq!(FREES,1);assert_eq!(FREEPTR,(&mut event as *mut Event) as usize);assert_eq!(ALLOCS,1);assert_eq!(COUNTERS,1);assert_eq!(COPIES,1);
 assert_eq!(event.pid,17);assert_eq!(event.counter,3);assert_eq!(event.leader,c_event.leader);assert_eq!(leader.nr,37);assert_eq!(leader.status,0x55);assert_eq!(leader.siblings.next,0x1234usize as *mut AbiListHead);assert!(leader.siblings.prev.is_null());
 println!("case={} rust={} c={} alloc=1 counter=1 free=1 untouched_leader=1",kind,rc,crc);
 }
}}
