// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Mock ABI/callbacks, real private lookup candidate and real release body.
#![allow(dead_code, non_snake_case)]
use core::ffi::c_void; use core::ptr::null_mut;
use std::mem::offset_of; use std::sync::atomic::{AtomicI32,Ordering};
use std::cell::RefCell; use std::sync::{RwLock,RwLockReadGuard};
type CInt=i32; type CULong=u64; const EINVAL:i32=22;
#[repr(C)] pub struct AbiListHead { next:*mut AbiListHead,prev:*mut AbiListHead }
#[repr(C)] struct IhkAtomic { counter:i32 }
#[repr(C)] struct Process { pid:i32 }
#[repr(C)] struct Thread { entry:AbiListHead, tid:i32, proc:*mut Process, refcount:IhkAtomic, status:i32, vm:*mut c_void }
pub struct ProcessFindThreadOffsets { thread_hash_list_offset:u64,thread_tid_offset:u64,thread_proc_offset:u64,proc_pid_offset:u64 }
type ProcessMcsRwlockFn=unsafe extern "C" fn(u64,*mut c_void);
type ProcessThreadActionFn=unsafe extern "C" fn(*mut c_void);
type ProcessVmActionFn=unsafe extern "C" fn(*mut c_void);
type ProcessVmReleaseCheckedFn=unsafe extern "C" fn(*mut c_void)->i32;
type ProcessThreadProfileFn=unsafe extern "C" fn(*mut c_void,*mut c_void);
type ProcessRefDecAndTestFn=unsafe extern "C" fn(*mut c_void,u64)->i32;
static WARN:AtomicI32=AtomicI32::new(0); static LOCKS:AtomicI32=AtomicI32::new(0);
static DESTROY:AtomicI32=AtomicI32::new(0); static FOUND:AtomicI32=AtomicI32::new(-1);
static HASH_LOCK:RwLock<()>=RwLock::new(());
static CONCURRENT:AtomicI32=AtomicI32::new(0); static PHASE:AtomicI32=AtomicI32::new(0);
thread_local! { static HASH_GUARD:RefCell<Option<RwLockReadGuard<'static,()>>>=const { RefCell::new(None) }; }
static mut HEAD:*mut AbiListHead=null_mut();
unsafe fn process_list_container(p:*mut AbiListHead,o:u64)->*mut c_void { unsafe { p.cast::<u8>().sub(o as usize).cast() } }
unsafe fn field_ptr(p:*mut c_void,o:u64)->*mut c_void { unsafe { *(p.cast::<u8>().add(o as usize).cast::<*mut c_void>()) } }
fn process_hold_thread_warn_exited_result(s:i32)->i32 { (s==99) as i32 }
unsafe fn process_hold_thread_warn_bridge(_: *mut c_void) { WARN.fetch_add(1,Ordering::SeqCst); }
unsafe fn process_ref_dec_and_test_result(p:*mut c_void,o:u64,_:Option<ProcessRefDecAndTestFn>)->i32 { (unsafe { AtomicI32::from_ptr(p.cast::<u8>().add(o as usize).cast::<i32>()).fetch_sub(1,Ordering::SeqCst) }==1) as i32 }
fn process_ref_release_should_destroy_result(v:i32)->i32 { v }
unsafe fn process_thread_profile_result(t:*mut c_void,p:*mut c_void,f:Option<ProcessThreadProfileFn>)->i32 { unsafe { f.unwrap()(t,p) }; 1 }
unsafe fn process_thread_action_result(t:*mut c_void,f:Option<ProcessThreadActionFn>)->i32 { unsafe { f.unwrap()(t) }; 1 }
unsafe fn process_vm_action_result(t:*mut c_void,f:Option<ProcessVmActionFn>)->i32 { unsafe { f.unwrap()(t) }; 1 }
unsafe extern "C" fn lock(_:u64,_:*mut c_void) { HASH_GUARD.with(|slot| *slot.borrow_mut()=Some(HASH_LOCK.read().unwrap())); LOCKS.fetch_add(1,Ordering::SeqCst); }
unsafe extern "C" fn unlock(_:u64,_:*mut c_void) { LOCKS.fetch_sub(1,Ordering::SeqCst); HASH_GUARD.with(|slot| drop(slot.borrow_mut().take())); }
unsafe fn lookup(pid:i32,tid:i32)->*mut c_void {
    let offsets=ProcessFindThreadOffsets { thread_hash_list_offset:offset_of!(Thread,entry) as u64,thread_tid_offset:offset_of!(Thread,tid) as u64,thread_proc_offset:offset_of!(Thread,proc) as u64,proc_pid_offset:offset_of!(Process,pid) as u64 };
    let mut node=0u8;
    unsafe { process_find_thread_live_body_result(HEAD,0,(&raw mut node).cast(),pid,tid,&offsets,Some(lock),Some(unlock)) }
}
unsafe extern "C" fn profile(_: *mut c_void, _: *mut c_void) {
    if CONCURRENT.load(Ordering::SeqCst)!=0 {
        PHASE.store(1,Ordering::SeqCst);
        while PHASE.load(Ordering::SeqCst)!=2 { std::thread::yield_now(); }
    } else { FOUND.store((!unsafe { lookup(0,42) }.is_null()) as i32,Ordering::SeqCst); }
}
unsafe extern "C" fn destroy(_: *mut c_void) { let _guard=HASH_LOCK.write().unwrap(); DESTROY.fetch_add(1,Ordering::SeqCst); }
unsafe extern "C" fn noop(_: *mut c_void) {}
unsafe extern "C" fn vm_checked(_: *mut c_void)->i32 { 0 }
// INSERT_ACTUAL_FUNCTIONS
fn main() {
    let mut proc=Process{pid:77}; let mut head=AbiListHead{next:null_mut(),prev:null_mut()};
    let mut t=Thread{entry:AbiListHead{next:&raw mut head,prev:&raw mut head},tid:42,proc:&mut proc,refcount:IhkAtomic{counter:1},status:99,vm:null_mut()};
    head.next=&raw mut t.entry; head.prev=&raw mut t.entry;
    unsafe { HEAD=&raw mut head; assert!(lookup(88,42).is_null()); assert!(lookup(0,0).is_null()); assert!(!lookup(42,42).is_null()); }
    assert_eq!(t.refcount.counter,2); assert_eq!(WARN.load(Ordering::SeqCst),1);
    // A successful lookup makes the subsequent ordinary release non-final.
    unsafe { assert_eq!(process_release_thread_body_result((&raw mut t).cast(),offset_of!(Thread,refcount) as u64,offset_of!(Thread,vm) as u64,offset_of!(Thread,proc) as u64,None,Some(profile),Some(noop),Some(destroy),Some(noop)),0); }
    assert_eq!(t.refcount.counter,1); assert_eq!(DESTROY.load(Ordering::SeqCst),0);
    // The following final decrement occurs before the deterministic lookup in profile.
    unsafe { assert_eq!(process_release_thread_body_result((&raw mut t).cast(),offset_of!(Thread,refcount) as u64,offset_of!(Thread,vm) as u64,offset_of!(Thread,proc) as u64,None,Some(profile),Some(noop),Some(destroy),Some(noop)),1); }
    assert_eq!(FOUND.load(Ordering::SeqCst),0); assert_eq!(t.refcount.counter,0); assert_eq!(DESTROY.load(Ordering::SeqCst),1);
    assert_eq!(WARN.load(Ordering::SeqCst),1);
    t.refcount.counter=1; t.vm=(&raw mut proc).cast(); FOUND.store(-1,Ordering::SeqCst);
    unsafe { assert_eq!(process_release_thread_checked_body_result((&raw mut t).cast(),offset_of!(Thread,refcount) as u64,offset_of!(Thread,vm) as u64,offset_of!(Thread,proc) as u64,None,Some(profile),Some(noop),Some(destroy),Some(vm_checked)),1); }
    assert_eq!(FOUND.load(Ordering::SeqCst),0); assert_eq!(WARN.load(Ordering::SeqCst),1);
    t.refcount.counter=i32::MAX; unsafe { assert!(lookup(0,42).is_null()); }
    assert_eq!(t.refcount.counter,i32::MAX);
    t.refcount.counter=-1; unsafe { assert!(lookup(0,42).is_null()); }
    assert_eq!(t.refcount.counter,-1); assert_eq!(LOCKS.load(Ordering::SeqCst),0);
    // Release executes on a separate thread; profile pauses after 1->0 while a
    // second thread performs real candidate lookup under a host rwlock reader.
    t.refcount.counter=1; CONCURRENT.store(1,Ordering::SeqCst); PHASE.store(0,Ordering::SeqCst);
    let thread_addr=(&raw mut t) as usize;
    let release=std::thread::spawn(move || unsafe {
        process_release_thread_body_result(thread_addr as *mut c_void,offset_of!(Thread,refcount) as u64,offset_of!(Thread,vm) as u64,offset_of!(Thread,proc) as u64,None,Some(profile),Some(noop),Some(destroy),Some(noop))
    });
    let lookup_worker=std::thread::spawn(|| {
        while PHASE.load(Ordering::SeqCst)!=1 { std::thread::yield_now(); }
        assert!(unsafe { lookup(0,42) }.is_null());
        PHASE.store(2,Ordering::SeqCst);
    });
    lookup_worker.join().unwrap(); assert_eq!(release.join().unwrap(),1);
    assert_eq!(t.refcount.counter,0); assert_eq!(LOCKS.load(Ordering::SeqCst),0);
    println!("PASS: live hold, ordinary/checked release, pid fallback and concurrent zero rejection");
}
