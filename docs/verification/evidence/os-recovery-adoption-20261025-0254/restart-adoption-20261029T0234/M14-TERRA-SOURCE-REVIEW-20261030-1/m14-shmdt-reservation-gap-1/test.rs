use core::ffi::c_void;
use core::mem::offset_of;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
type CInt = i32; type CULong = u64; type SizeT = usize;
type SyscallRwlockFn = unsafe extern "C" fn(*mut c_void);
type MunmapDoFn = unsafe extern "C" fn(*mut c_void, SizeT, CInt) -> CInt;
type ShmdtLogFn = unsafe extern "C" fn(CInt, CULong, CInt);
type MsyncLookupRangeFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> *mut c_void;
const EINVAL: CInt = 22;
const SHMDT_LOG_ENTER: CInt = 1; const SHMDT_LOG_INVALID: CInt = 2; const SHMDT_LOG_EXIT: CInt = 3;
include!("actual-bodies.rs");
#[repr(C)] struct Obj { flags: u32 }
#[repr(C)] struct Range { start: u64, end: u64, object: *mut Obj }
static ACTIVE: AtomicBool = AtomicBool::new(false);
static LOCKED: AtomicBool = AtomicBool::new(false);
static OVERLAP_MUTATIONS: AtomicUsize = AtomicUsize::new(0);
static CALLS: AtomicUsize = AtomicUsize::new(0);
unsafe extern "C" fn lock(_: *mut c_void) { assert!(!LOCKED.swap(true, Ordering::SeqCst)); }
unsafe extern "C" fn unlock(_: *mut c_void) { assert!(LOCKED.swap(false, Ordering::SeqCst)); }
unsafe extern "C" fn lookup(vm: *mut c_void, start: u64, end: u64) -> *mut c_void {
 assert!(LOCKED.load(Ordering::SeqCst)); assert_eq!((start,end),(0x1000,0x1001)); vm
}
unsafe extern "C" fn remove(addr: *mut c_void, len: usize, held: i32) -> i32 {
 assert_eq!((addr as usize,len,held),(0x1000,0x1000,1)); assert!(LOCKED.load(Ordering::SeqCst));
 CALLS.fetch_add(1,Ordering::SeqCst);
 if ACTIVE.load(Ordering::SeqCst) { OVERLAP_MUTATIONS.fetch_add(1,Ordering::SeqCst); }
 0
}
fn run(flags: u32, active: bool) -> (i32, usize, usize) {
 ACTIVE.store(active,Ordering::SeqCst); LOCKED.store(false,Ordering::SeqCst);
 CALLS.store(0,Ordering::SeqCst); OVERLAP_MUTATIONS.store(0,Ordering::SeqCst);
 let mut obj=Obj{flags}; let mut r=Range{start:0x1000,end:0x2000,object:&mut obj};
 let result=unsafe{shmdt_body_result((&mut r as *mut Range).cast(),core::ptr::null_mut(),0x1000,
 offset_of!(Range,start),offset_of!(Range,end),offset_of!(Range,object),offset_of!(Obj,flags),2,
 Some(lock),Some(unlock),Some(lookup),Some(remove),None)};
 assert!(!LOCKED.load(Ordering::SeqCst)); (result,CALLS.load(Ordering::SeqCst),OVERLAP_MUTATIONS.load(Ordering::SeqCst))
}
#[test] fn reserved_both_flags_still_calls_removal() { assert_eq!(run(0x10002,true),(0,1,1)); }
#[test] fn ordinary_valid_calls_removal() { assert_eq!(run(2,false),(0,1,0)); }
#[test] fn missing_shmdt_flag_does_not_remove() { assert_eq!(run(0x10000,true),(-22,0,0)); }
