// Source-only proposed actual-body comparison. No execution release.
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(non_snake_case, dead_code)]
use std::ffi::{c_int, c_long, c_ulong, c_void};
use std::sync::{Mutex, atomic::{AtomicUsize, Ordering}};
const MCEXEC_UP_TRANSFER: c_ulong = 0x30a02901;
const MCEXEC_UP_CLOSE_EXEC: c_ulong = 0x30a02913;
const MCEXEC_UP_TRANSFER_TO_REMOTE: u8 = 0;
const MCEXEC_UP_TRANSFER_FROM_REMOTE: u8 = 1;
const SEEK_SET: c_int = 0;
const EINVAL: c_int = 22;
static DMA_PERROR_TAG: &[u8] = b"dma\0";
static mut MCEXEC_PAGE_SIZE: c_ulong = 4096;
static mut MCEXEC_PAGE_MASK: c_ulong = !4095;
static mut DMA: [u8;4096] = [0;4096];
static mut MCEXEC_DMA_BUF: *mut u8 = std::ptr::null_mut();
static EVENTS: Mutex<Vec<&'static str>> = Mutex::new(Vec::new());
static PAGES: AtomicUsize = AtomicUsize::new(0);
static FAIL: AtomicUsize = AtomicUsize::new(0);
#[repr(C)] struct RemoteTransfer { rphys:c_ulong, userp:*mut c_void, size:c_ulong, direction:u8 }
#[repr(C)] struct Request { args:[c_ulong;6] }
#[repr(C)] struct McexecSyscallWaitDesc { sr:Request }
fn event(s:&'static str) { EVENTS.lock().unwrap().push(s); }
fn summary() { println!("events={}",EVENTS.lock().unwrap().join(",")); }
unsafe fn malloc(size:usize)->*mut u8 { Box::into_raw(vec![0u8;size].into_boxed_slice()).cast() }
unsafe fn zero_bytes(p:*mut u8,n:usize) { std::ptr::write_bytes(p,0,n); }
unsafe fn mcexec_desc_num_sections_bridge(_:*const c_void)->c_int { 2 }
unsafe fn mcexec_desc_section_fp_bridge(_:*const c_void,_:c_int)->*mut c_void { std::ptr::null_mut() }
unsafe fn mcexec_desc_section_vaddr_bridge(_:*const c_void,i:c_int)->c_ulong { 0x1000+(i as c_ulong)*0x2000 }
unsafe fn mcexec_desc_section_len_bridge(_:*const c_void,_:c_int)->c_ulong { 8192 }
unsafe fn mcexec_desc_section_offset_bridge(_:*const c_void,_:c_int)->c_ulong { 0 }
unsafe fn mcexec_desc_section_remote_pa_bridge(_:*const c_void,i:c_int)->c_ulong { 0x8000+(i as c_ulong)*0x2000 }
unsafe fn mcexec_desc_section_filesz_bridge(_:*const c_void,_:c_int)->c_ulong { 8192 }
unsafe fn fseek(_:*mut c_void,offset:c_long,whence:c_int)->c_int {
    assert_eq!((offset,whence),(0,SEEK_SET)); event("seek");0
}
unsafe fn mcexec_transfer_seek_error_bridge() { event("seek-error"); }
unsafe fn mcexec_transfer_seeked_bridge(offset:c_ulong,flen:c_ulong) { assert_eq!((offset,flen),(0,8192)); }
unsafe fn transfer_read_exact(_:*mut c_void,p:*mut u8,n:usize)->c_int {
    assert_eq!(n,4096); std::ptr::write_bytes(p,0x5a,n);event("read");0
}
unsafe fn perror(_:*const u8) { event("perror"); }
unsafe fn ioctl(fd:c_int,request:c_ulong,arg:c_ulong)->c_int {
    assert_eq!(fd,7);
    if request==MCEXEC_UP_CLOSE_EXEC { event("close-exec");return 0; }
    assert_eq!(request,MCEXEC_UP_TRANSFER);
    let t=&*(arg as *const RemoteTransfer);
    if t.direction==MCEXEC_UP_TRANSFER_FROM_REMOTE {
        assert_eq!((t.rphys,t.size),(0x6000,64));event("descriptor-from-remote");return 0;
    }
    assert_eq!(t.direction,MCEXEC_UP_TRANSFER_TO_REMOTE);
    let page=PAGES.fetch_add(1,Ordering::SeqCst)+1;
    assert_eq!((t.rphys,t.size),(0x8000+(page as u64-1)*4096,4096));
    assert_eq!(t.userp,MCEXEC_DMA_BUF.cast());
    assert!(std::slice::from_raw_parts(t.userp.cast::<u8>(),4096).iter().all(|b|*b==0x5a));
    event("page-to-remote");
    if FAIL.load(Ordering::SeqCst)==page { -1 } else { 0 }
}
unsafe fn mcexec_execve2_alloc_desc_failed_bridge() { event("alloc-failed"); }
unsafe fn mcexec_execve2_transfer_desc_failed_bridge() { event("descriptor-failed"); }
unsafe fn mcexec_execve2_transfer_desc_ok_bridge() { event("descriptor-ok"); }
unsafe fn mcexec_execve2_transfer_image_failed_bridge() { event("image-failed"); }
unsafe fn mcexec_execve2_image_transferred_bridge() { event("image-ok"); }
unsafe fn mcexec_execve2_close_exec_failed_bridge(_:c_int) { event("close-failed"); }
unsafe fn close_cloexec_fds(fd:c_int)->c_int { assert_eq!(fd,7);event("cloexec");0 }
unsafe fn do_syscall_return(fd:c_int,cpu:c_int,ret:c_long,a:c_int,b:c_int,c:c_int,d:c_int) {
    assert_eq!((fd,cpu,ret,a,b,c,d),(7,2,0,0,0,0,0));event("success-ret");
}
unsafe fn act_execve_phase1(_:*const McexecSyscallWaitDesc,_:c_int,_:c_int,_:*mut u8) { panic!("unexpected phase1"); }
unsafe fn mcexec_execve_invalid_phase_bridge() { panic!("unexpected invalid phase"); }
unsafe fn mcexec_exit_cmd_servers_bridge() { event("cmd-cleanup"); }
unsafe fn mcexec_exit_process_bridge(code:c_int) { event("process-exit1");summary();std::process::exit(code); }

include!("transfer_image.actual-candidate-body.rs");
include!("act_execve_phase2.actual-candidate-body.rs");
include!("act_execve.actual-candidate-body.rs");

fn main() {
    let mode=std::env::args().nth(1).expect("success/page1/page2");
    FAIL.store(match mode.as_str(){"success"=>0,"page1"=>1,"page2"=>2,_=>panic!("unknown mode")},Ordering::SeqCst);
    let mut wait=McexecSyscallWaitDesc{sr:Request{args:[2,0x6000,64,0,0,0]}};
    let mut result:c_long=123;
    unsafe {
        MCEXEC_DMA_BUF=std::ptr::addr_of_mut!(DMA).cast();
        assert_eq!(act_execve(&mut wait,7,2,std::ptr::null_mut(),&mut result),0);
    }
    assert_eq!(result,123);
    summary();
}
