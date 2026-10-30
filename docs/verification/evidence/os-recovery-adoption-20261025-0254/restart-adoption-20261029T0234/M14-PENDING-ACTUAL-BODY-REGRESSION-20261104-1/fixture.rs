// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Mocked providers/layouts; imports actual candidate and actual Rust spinlock.
#![allow(dead_code, unused_variables)]
use std::ffi::c_void;
use std::sync::atomic::{AtomicI32, AtomicPtr, Ordering};
mod abi {
    use std::ffi::c_void;
    pub type CInt=i32; pub type CLong=i64; pub type CULong=u64;
    #[repr(C)] pub struct SigInfo { pub bytes:[u8;16] }
    #[repr(C)] pub struct SigPending { pub info:SigInfo, pub ptracecont:i32 }
    #[repr(C)] pub struct SigCommon { pub lock:u64 }
    #[repr(C)] pub struct Thread { pub ptrace_recvsig:*mut c_void, pub ptrace_sendsig:*mut c_void, pub sigcommon:*mut c_void }
}
#[path = "../../../../../../kernel/rust/spinlock_helpers.rs"] mod spinlock_helpers;
mod lock_helpers { pub struct McsRwlockNodeIrqsave; pub unsafe fn __mcs_rwlock_writer_unlock(_: *mut core::ffi::c_void, _: *mut McsRwlockNodeIrqsave) {} }
mod mem_helpers {
    pub unsafe fn kfree_tracked(p:*mut core::ffi::c_void, _: *mut i8, _:i32) {
        if !p.is_null() { unsafe { drop(Box::from_raw(p.cast::<crate::abi::SigPending>())); } crate::FREED.fetch_add(1, std::sync::atomic::Ordering::SeqCst); }
    }
}
mod process_helpers { pub unsafe fn process_release_fp_regs_result(_: *mut core::ffi::c_void, _:Option<unsafe extern "C" fn(*mut core::ffi::c_void)>)->i32 { 0 } }
#[no_mangle] extern "C" fn preempt_disable() {} #[no_mangle] extern "C" fn preempt_enable() {}
#[no_mangle] extern "C" fn cpu_pause() { std::hint::spin_loop(); }
#[no_mangle] extern "C" fn cpu_disable_interrupt_save()->u64 { 0 }
#[no_mangle] extern "C" fn cpu_restore_interrupt(_:u64) {}
use abi::*;
static CHILD:AtomicPtr<Thread>=AtomicPtr::new(core::ptr::null_mut());
static FREED:AtomicI32=AtomicI32::new(0);
static COPY_MODE:AtomicI32=AtomicI32::new(0);
static COPIES:AtomicI32=AtomicI32::new(0);
static UNLOCKS:AtomicI32=AtomicI32::new(0);
const EFAULT:i32=14; const ENOMEM:i32=12; const ESRCH:i32=3; const IHK_MC_AP_NOWAIT:u64=0;
const PTRACE_SIGINFO_STORE_SENDSIG:i32=1; const PTRACE_SIGINFO_STORE_RECVSIG:i32=2; const PTRACE_SIGINFO_ALLOC_SENDSIG:i32=4;
const PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG:i32=1; const PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG:i32=2;
static F03_PTRACE_IO_OFFSETS:u8=0;
unsafe fn f03_ptrace_io_find(_:i32,_:i32)->u64 { CHILD.load(Ordering::SeqCst) as u64 }
unsafe fn f03_ptrace_io_unlock(_:u64) { UNLOCKS.fetch_add(1,Ordering::SeqCst); }
unsafe fn ptrace_io_status(_:u64,_:*const u8)->i32 { 1 }
fn ptrace_setsiginfo_target_result(status:i32,send:i32,recv:i32)->i32 {
    if status==0 { return -ESRCH; } 1 | if send==0 {4} else {0} | if recv!=0 {2} else {0}
}
fn ptrace_siginfo_state_result(status:i32,present:i32)->i32 { if status!=0 && present!=0 {0} else {-ESRCH} }
fn ptrace_resume_signal_source_result(request:i64,send:i32,recv:i32)->i32 { if request==7 && send!=0 {1} else if request==7 && recv!=0 {2} else {0} }
unsafe fn syscall_alloc_bridge(_:usize,_:u64)->*mut c_void { Box::into_raw(Box::new(SigPending{info:SigInfo{bytes:[0;16]},ptracecont:0})).cast() }
unsafe fn syscall_copy_from_user_bridge(dst:*mut u8,src:u64,len:usize)->i32 {
    let n=COPIES.fetch_add(1,Ordering::SeqCst);
    match COPY_MODE.load(Ordering::SeqCst) {
        1 => return -1,
        2 if n==0 => {
            let winner=Box::into_raw(Box::new(SigPending{info:SigInfo{bytes:[8;16]},ptracecont:0}));
            assert!(unsafe { f03_pending_slot_protocol::try_publish_sendsig(CHILD.load(Ordering::SeqCst),winner) }.is_ok());
        },
        3 if n==1 => return -1,
        _ => ()
    }
    unsafe { std::ptr::copy_nonoverlapping(src as *const u8,dst,len) }; 0
}
unsafe fn syscall_copy_to_user_bridge(dst:u64,src:*const u8,len:usize)->i32 { unsafe { std::ptr::copy_nonoverlapping(src,dst as *mut u8,len) }; 0 }
#[path = "../M14-REMAINING23-C-1/staged-pending-successor-1/postimage/kernel/rust/pending_slot_protocol.rs"] mod f03_pending_slot_protocol;
#[path = "../M14-REMAINING23-C-1/staged-pending-successor-1/postimage/kernel/rust/syscall_ptrace_setsiginfo_staged.rs"] mod producer;
fn main() {
    let mut thread=Thread{ptrace_recvsig:core::ptr::null_mut(),ptrace_sendsig:core::ptr::null_mut(),sigcommon:core::ptr::null_mut()};
    CHILD.store(&mut thread,Ordering::SeqCst);
    let mut input=SigInfo{bytes:[42;16]};
    unsafe {
        COPY_MODE.store(1,Ordering::SeqCst);
        assert_eq!(producer::f03_ptrace_setsiginfo_staged_v2(1,&mut input),-14);
        assert!(thread.ptrace_sendsig.is_null()); assert_eq!(FREED.load(Ordering::SeqCst),1);
        COPY_MODE.store(2,Ordering::SeqCst); COPIES.store(0,Ordering::SeqCst);
        assert_eq!(producer::f03_ptrace_setsiginfo_staged_v2(1,&mut input),0);
        assert_eq!(COPIES.load(Ordering::SeqCst),2); assert_eq!(FREED.load(Ordering::SeqCst),2);
        let mut snapshot=[0u8;16];
        assert!(f03_pending_slot_protocol::snapshot_info(&mut thread, &raw mut thread.ptrace_sendsig, snapshot.as_mut_ptr()));
        assert_eq!(snapshot,[42;16]);
        let taken=f03_pending_slot_protocol::take_for_request(&mut thread,7);
        assert!(!taken.is_null()); assert!(thread.ptrace_sendsig.is_null());
        mem_helpers::kfree_tracked(taken,core::ptr::null_mut(),0);
        assert_eq!(UNLOCKS.load(Ordering::SeqCst),2);
        assert_eq!(FREED.load(Ordering::SeqCst),3);
        // The second usercopy fails after the successful send publication;
        // send remains initialized and receive retains its prior payload.
        let receive=Box::into_raw(Box::new(SigPending{info:SigInfo{bytes:[11;16]},ptracecont:0}));
        thread.ptrace_recvsig=receive.cast();
        COPY_MODE.store(3,Ordering::SeqCst); COPIES.store(0,Ordering::SeqCst);
        assert_eq!(producer::f03_ptrace_setsiginfo_staged_v2(1,&mut input),-14);
        assert_eq!(COPIES.load(Ordering::SeqCst),2);
        let mut recv_bytes=[0;16]; let mut send_bytes=[0;16];
        assert!(f03_pending_slot_protocol::snapshot_info(&mut thread,&raw mut thread.ptrace_recvsig,recv_bytes.as_mut_ptr()));
        assert!(f03_pending_slot_protocol::snapshot_info(&mut thread,&raw mut thread.ptrace_sendsig,send_bytes.as_mut_ptr()));
        assert_eq!(recv_bytes,[11;16]); assert_eq!(send_bytes,[42;16]);
        let (recv,send)=f03_pending_slot_protocol::drain_for_thread_destruction(&mut thread);
        mem_helpers::kfree_tracked(recv,core::ptr::null_mut(),0);
        mem_helpers::kfree_tracked(send,core::ptr::null_mut(),0);
    }
    // Keep thread and pending allocation live until both workers have joined.
    let mut concurrent=Box::new(Thread{ptrace_recvsig:core::ptr::null_mut(),ptrace_sendsig:core::ptr::null_mut(),sigcommon:core::ptr::null_mut()});
    let address=(&mut *concurrent as *mut Thread) as usize;
    let pending=Box::into_raw(Box::new(SigPending{info:SigInfo{bytes:[0;16]},ptracecont:0}));
    unsafe { assert!(f03_pending_slot_protocol::try_publish_sendsig(address as *mut Thread,pending).is_ok()); }
    let writer=std::thread::spawn(move || unsafe {
        let t=address as *mut Thread;
        for i in 0..10000 {
            let bytes=[(i & 255) as u8;16];
            assert!(f03_pending_slot_protocol::update_current_info(t,&raw mut (*t).ptrace_sendsig,bytes.as_ptr()));
        }
    });
    let reader=std::thread::spawn(move || unsafe {
        let t=address as *mut Thread;
        for _ in 0..10000 {
            let mut bytes=[0;16];
            assert!(f03_pending_slot_protocol::snapshot_info(t,&raw mut (*t).ptrace_sendsig,bytes.as_mut_ptr()));
            assert!(bytes.iter().all(|x| *x==bytes[0]));
        }
    });
    writer.join().unwrap(); reader.join().unwrap();
    unsafe {
        let (recv,send)=f03_pending_slot_protocol::drain_for_thread_destruction(&mut *concurrent);
        assert!(recv.is_null()); assert_eq!(send,pending.cast());
        mem_helpers::kfree_tracked(send,core::ptr::null_mut(),0);
    }
    println!("PASS: failed copy, publication conflict, ownership transfer and concurrent snapshot/update");
}
