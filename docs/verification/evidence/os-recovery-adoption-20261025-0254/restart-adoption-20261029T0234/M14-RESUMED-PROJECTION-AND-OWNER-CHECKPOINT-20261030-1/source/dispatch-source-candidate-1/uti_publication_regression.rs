//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Actual host util body with controlled preactivation callback outcomes only.
//! Does not model context execution, concurrent descriptors or host drain.
#![allow(non_camel_case_types,non_snake_case,dead_code,static_mut_refs)]
use core::ffi::{c_void,c_int,c_long,c_ulong};
use std::sync::atomic::{AtomicI32,Ordering};
const EINVAL:c_int=22; const ENOMEM:c_int=12;
const MCEXEC_UP_UTI_GET_CTX:c_ulong=1; const MCEXEC_UP_UTI_ATTR:c_ulong=2;
static UTI_CPU_SET_ENV:[u8;2]=[0,0];
static mut MCEXEC_FD:c_int=9; static mut MCEXEC_PAGE_SIZE:c_int=4096;
static mut ERRNO:c_int=7;
#[repr(C)] struct McexecThreadData { tid:c_int }
#[repr(C)] struct McexecUtiDesc {
    fd:c_int,rctx:[u8;4096],lctx:[u8;4096],mck_tid:c_int,key:c_ulong,
    pid:c_int,tid:c_int,uti_info:c_ulong,start_syscall_intercept:c_int,
}
#[repr(C)] struct McexecUtiGetCtxDesc {
    rp_rctx:c_ulong,rctx:*mut c_void,lctx:*mut c_void,uti_refill_tid:c_int,key:c_ulong,
}
#[repr(C)] struct McexecUtiAttrDesc {
    phys_attr:c_ulong,uti_cpu_set_str:*mut u8,uti_cpu_set_len:usize,
}
#[repr(C)] struct McexecUtiSwitchCtxDesc { rctx:*mut c_void,lctx:*mut c_void }
#[repr(C)] struct McexecSyscallStruct { number:c_int,args:[c_ulong;6],ret:c_ulong,uti_info:c_ulong }
static CREATE_RC:AtomicI32=AtomicI32::new(0);
static GET_CTX_RC:AtomicI32=AtomicI32::new(0);
static ATTR_RC:AtomicI32=AtomicI32::new(0);
static SWITCH_RC:AtomicI32=AtomicI32::new(0);
static SWITCH_CALLS:AtomicI32=AtomicI32::new(0);
static mut ACTIVE_DESC:*mut McexecUtiDesc=core::ptr::null_mut();
static mut THREAD:McexecThreadData=McexecThreadData { tid:73 };
unsafe fn mcexec_util_thread_create_worker_bridge(p:*mut *mut McexecThreadData)->c_int {
    unsafe { p.write(core::ptr::addr_of_mut!(THREAD)); } CREATE_RC.load(Ordering::SeqCst)
}
unsafe fn ioctl(_:c_int,n:c_ulong,_:c_ulong)->c_int {
    if n==MCEXEC_UP_UTI_GET_CTX { GET_CTX_RC.load(Ordering::SeqCst) }
    else { assert_eq!(n,MCEXEC_UP_UTI_ATTR); ATTR_RC.load(Ordering::SeqCst) }
}
unsafe fn syscall(_:c_long)->c_long { -1 }
unsafe fn __errno_location()->*mut c_int { core::ptr::addr_of_mut!(ERRNO) }
unsafe fn getpid()->c_int { 31 } unsafe fn gettid()->c_int { 32 }
unsafe fn getenv(_: *const u8)->*mut u8 { core::ptr::null_mut() }
unsafe fn strlen(_: *const u8)->usize { panic!("unexpected non-null env") }
unsafe fn mcexec_util_thread_switch_ctx_bridge(_: *mut McexecUtiSwitchCtxDesc,_:*mut c_void,_:*mut c_void)->c_int {
    unsafe {
        assert_eq!((*ACTIVE_DESC).uti_info,0x1234);
        assert_eq!((*ACTIVE_DESC).start_syscall_intercept,1);
    }
    SWITCH_CALLS.fetch_add(1,Ordering::SeqCst); SWITCH_RC.load(Ordering::SeqCst)
}
unsafe fn mcexec_util_thread_desc_log_bridge(_: *mut c_void) {}
unsafe fn mcexec_util_thread_missing_desc_bridge() {}
unsafe fn mcexec_util_thread_barrier_init_bridge() {}
unsafe fn mcexec_util_thread_barrier_wait_bridge() {}
unsafe fn mcexec_util_thread_worker_error_bridge(_:c_int) {}
unsafe fn mcexec_util_thread_worker_tid_log_bridge(_:c_int) {}
unsafe fn mcexec_util_thread_intercept_warning_bridge(_:c_int) {}
unsafe fn mcexec_util_thread_get_ctx_error_bridge(_:c_int) {}
unsafe fn mcexec_util_thread_param_large_bridge() {}
unsafe fn mcexec_util_thread_attr_error_bridge(_:c_int) {}
unsafe fn mcexec_util_thread_switch_failed_bridge(_:c_int) {}
unsafe fn mcexec_util_thread_switch_returned_bridge(_:c_int) {}
include!("mcexec_util_thread_body.PRIVATE.rs.inc");
fn desc()->McexecUtiDesc { McexecUtiDesc {
    fd:0,rctx:[0;4096],lctx:[0;4096],mck_tid:0,key:0,pid:0,tid:0,
    uti_info:0xdead,start_syscall_intercept:0,
} }
#[test]
fn borrowed_info_publishes_only_after_preactivation_success() {
    // Controlled prior descriptor state; no claim that previous borrowers drained.
    for mode in 0..6 {
        let mut d=desc();
        CREATE_RC.store(if mode==0 {1}else{0},Ordering::SeqCst);
        GET_CTX_RC.store(if mode==1 {-1}else{0},Ordering::SeqCst);
        ATTR_RC.store(if mode==3 {-1}else{0},Ordering::SeqCst);
        SWITCH_RC.store(if mode==4 {-8}else{0},Ordering::SeqCst);
        SWITCH_CALLS.store(0,Ordering::SeqCst);
        unsafe { MCEXEC_PAGE_SIZE=if mode==2 {0}else{4096}; ACTIVE_DESC=&mut d; }
        let rc=unsafe { mcexec_util_thread_body(core::ptr::null_mut(),4,5,6,0x1234,&mut d as *mut _ as c_ulong) };
        if mode<=3 {
            assert_eq!(d.uti_info,0xdead); assert_eq!(d.start_syscall_intercept,0);
            assert_eq!(SWITCH_CALLS.load(Ordering::SeqCst),0);
            assert_eq!(rc,match mode {0=>-22,1=>-7,2=>-12,_=>-7});
        } else {
            assert_eq!(d.uti_info,0x1234); assert_eq!(d.start_syscall_intercept,1);
            assert_eq!(SWITCH_CALLS.load(Ordering::SeqCst),1);
            assert_eq!(rc,if mode==4 {-8}else{-22});
            // Unknown switch completion retains state; no fabricated drain/clear.
        }
    }
}
