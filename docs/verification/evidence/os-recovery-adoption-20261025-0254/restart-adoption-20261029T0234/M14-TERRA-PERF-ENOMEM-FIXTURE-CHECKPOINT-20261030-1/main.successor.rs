//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! UNRUN: actual private composed perf entry; sequential mocked provider inputs.
#![allow(dead_code, unused_variables, unused_imports, static_mut_refs)]
#[path = "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/f06-debug-constants-align32-host-1/src/kernel/rust/abi.rs"] mod abi;
use abi::{CInt, CLong, CULong, SizeT, SyscallRequest, AbiListHead, Mckfd};
use core::{ffi::c_void, mem::{offset_of, size_of}, ptr::{read_volatile, write_volatile}};
const EINVAL:CInt=22; const ENOMEM:CInt=12; const ENOENT:CInt=2; const EFAULT:CInt=14;
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
#[path = "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-xpmem-perf-composite-source-1/f03_perf_group_cleanup.rs"] mod group;
#[repr(C)] struct Event {pid:i32,counter:i32,leader:*mut c_void,siblings:AbiListHead,entry:AbiListHead,nr:i32,_pad:i32,status:u64}
#[repr(C)] struct Fd {next:*mut Fd,fd:i32,_pad:i32,data:i64}
#[repr(C)] struct Proc {head:*mut Fd}
static mut EVENT:*mut Event=core::ptr::null_mut();
static mut FREE_COUNT:i32=0; static mut FREE_PTR:usize=0;
static mut EVENT_ALLOCS:i32=0; static mut COUNTER_CALLS:i32=0; static mut COPIES:i32=0;
static mut HOST_CALLS:i32=0; static mut HOST_BAD:i32=0; static mut MCKFD_ALLOCS:i32=0;
static mut PUBLISH_CALLS:i32=0;
unsafe extern "C" fn event_alloc(out:*mut *mut c_void,_:*mut c_void)->i32 { EVENT_ALLOCS+=1; *out=EVENT.cast(); 0 }
unsafe extern "C" fn counter(_:*mut c_void,_:*mut c_void)->i32 { COUNTER_CALLS+=1; 3 }
unsafe extern "C" fn copy_attr(dst:*mut u8,src:u64,n:usize)->i64 { COPIES+=1; core::ptr::copy_nonoverlapping(src as *const u8,dst,n); 0 }
unsafe extern "C" fn freq(_:*const c_void)->i32 { 0 }
unsafe extern "C" fn descriptor_failure(size:usize,_:u64)->*mut c_void { MCKFD_ALLOCS+=1; if size!=size_of::<Mckfd>() { HOST_BAD+=1; } core::ptr::null_mut() }
unsafe extern "C" fn perf_event_alloc_free_bridge(ptr:*mut c_void) { FREE_COUNT+=1; FREE_PTR=ptr as usize; }
unsafe extern "C" fn host(req:*mut SyscallRequest,cpu:i32)->i64 {
    HOST_CALLS+=1;
    if cpu!=7 || (*req).number!=298 || (*req).args!=[0;6] { HOST_BAD+=1; }
    41
}
fn new_event()->Event { unsafe { core::mem::zeroed() } }
fn main() { unsafe {
    for group_fd in [-1,42] {
        let mut leader=new_event(); let head=core::ptr::addr_of_mut!(leader.siblings);
        (*head).next=head; (*head).prev=head;
        let mut fd=Fd{next:core::ptr::null_mut(),fd:42,_pad:0,data:(&mut leader as *mut Event) as i64};
        let mut proc=Proc{head:if group_fd==-1 {core::ptr::null_mut()}else{&mut fd}};
        let initial_head=proc.head;
        let mut event=new_event(); let mut req:SyscallRequest=core::mem::zeroed();
        // Independently distinct poisoned arguments must all be cleared by the real helper.
        req.args=[0x11,0x22,0x33,0x44,0x55,0x66];
        assert_eq!(req.args,[0x11,0x22,0x33,0x44,0x55,0x66]);
        let mut thread:u64=2; let input=[0u8;40]; let mut attr=[0u64;5];
        EVENT=&mut event; FREE_COUNT=0; FREE_PTR=0; EVENT_ALLOCS=0; COUNTER_CALLS=0;
        COPIES=0; HOST_CALLS=0; HOST_BAD=0; MCKFD_ALLOCS=0; PUBLISH_CALLS=0;
        let o=(offset_of!(Proc,head),offset_of!(Fd,next),offset_of!(Fd,fd),offset_of!(Fd,data),offset_of!(Event,leader),offset_of!(Event,siblings),offset_of!(Event,entry),offset_of!(Event,nr),offset_of!(Event,status));
        let rc=group::perf_entry_with_group_cleanup(&mut req,(&mut thread as *mut u64).cast(),(&mut proc as *mut Proc).cast(),attr.as_mut_ptr().cast(),input.as_ptr() as u64,40,0,32,16,17,0,group_fd,0,7,4,0,3,7,1u64<<63,298,size_of::<Mckfd>(),0,offset_of!(Event,pid),offset_of!(Event,counter),o.0,o.1,o.2,o.3,o.4,o.5,o.6,o.7,o.8,0,0,0,0,0,0,0,0,Some(copy_attr),Some(freq),Some(event_alloc),Some(counter),Some(host),Some(descriptor_failure),None,None,None,None,None,None,None);
        assert_eq!(rc,-12); assert_eq!(EVENT_ALLOCS,1); assert_eq!(COUNTER_CALLS,1); assert_eq!(COPIES,1);
        assert_eq!(HOST_CALLS,1); assert_eq!(HOST_BAD,0); assert_eq!(req.args,[0;6]);
        assert_eq!(MCKFD_ALLOCS,1); assert_eq!(PUBLISH_CALLS,0);
        assert_eq!(thread,10); assert_eq!(proc.head,initial_head);
        if group_fd==-1 {
            assert_eq!(FREE_COUNT,1); assert_eq!(FREE_PTR,(&mut event as *mut Event) as usize);
            assert_eq!(event.leader,(&mut event as *mut Event).cast());
        } else {
            assert_eq!(FREE_COUNT,0); assert_eq!(FREE_PTR,0); assert_eq!(leader.nr,1); assert_eq!(leader.status,8);
            let expected_leader=(&mut leader as *mut Event).cast::<c_void>();
            let member=core::ptr::addr_of_mut!(event.entry);
            assert_eq!(event.leader,expected_leader);
            assert_eq!((*head).next,member); assert_eq!((*head).prev,member);
            assert_eq!((*member).next,head); assert_eq!((*member).prev,head);
        }
        println!("{} rc={} event_free={} host_calls={} map={}",if group_fd==-1 {"standalone"} else {"grouped"},rc,FREE_COUNT,HOST_CALLS,thread);
    }
} }
