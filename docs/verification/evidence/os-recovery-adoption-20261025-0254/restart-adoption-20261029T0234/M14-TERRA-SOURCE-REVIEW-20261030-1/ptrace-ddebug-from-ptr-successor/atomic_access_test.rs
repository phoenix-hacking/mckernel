use std::sync::atomic::{AtomicUsize, Ordering};
static PRINTS: AtomicUsize = AtomicUsize::new(0);

mod debug {
    #[repr(C)]
    pub struct Ddebug { pub file:*const i8, pub func:*const i8, pub fmt:*const i8, pub line_flags:u32 }
    #[path = "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/ptrace-ddebug-from-ptr-successor-terra-20261030-1/postimage/kernel/rust/debug_registry_access.rs"]
    mod access;
    pub unsafe fn line(p:*mut Ddebug)->i32 { access::ddebug_line(p) }
    pub unsafe fn flags(p:*mut Ddebug)->u32 { access::ddebug_flags(p) }
    pub unsafe fn set(p:*mut Ddebug, f:u32) { access::set_ddebug_flags(p, f) }
}
mod syscall_policy {
    pub type CInt = i32;
    pub const PTRACE_CONTROL_LOG_WAKEUP_ENTER:CInt = 4;
    pub unsafe fn kprintf(fmt:*const i8, pid:i32, data:i32) {
        let bytes = std::ffi::CStr::from_ptr(fmt).to_bytes();
        assert_eq!(bytes, b"ptrace_wakeup_sig,pid=%d,data=%08x\n");
        assert_eq!((pid,data),(12,34));
        crate::PRINTS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    }
    #[path = "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/ptrace-ddebug-from-ptr-successor-terra-20261030-1/postimage/kernel/rust/syscall_ptrace_wakeup_logger.rs"]
    pub mod logger;
    pub use logger as syscall_ptrace_wakeup_logger;
    pub unsafe fn log(event:i32) { logger::ptrace_wakeup_log_bridge(event,12,34); }
}

#[test]
fn actual_accessors_and_logger() { unsafe {
    let rec = syscall_policy::logger::test_record();
    debug::set(rec,0);
    let before=PRINTS.load(Ordering::Relaxed);
    syscall_policy::log(4); syscall_policy::log(3);
    assert_eq!(PRINTS.load(Ordering::Relaxed),before);
    assert_eq!(debug::line(rec),24429);
    debug::set(rec,1);
    assert_eq!(debug::flags(rec),1);
    syscall_policy::log(4); syscall_policy::log(3);
    assert_eq!(PRINTS.load(Ordering::Relaxed),before+1);
    debug::set(rec,0); assert_eq!(debug::line(rec),24429);
    let mut other=debug::Ddebug{file:std::ptr::null(),func:std::ptr::null(),fmt:std::ptr::null(),line_flags:41};
    debug::set(&mut other,1); assert_eq!(debug::line(&other as *const _ as *mut _),41); assert_eq!(debug::flags(&other as *const _ as *mut _),1);
} }

#[test]
fn actual_atomic_loads_and_updates_concurrently() {
    let address=unsafe {syscall_policy::logger::test_record() as usize};
    let mut threads=Vec::new();
    for id in 0..6 {
        threads.push(std::thread::spawn(move || for i in 0..10000 {
            let p=address as *mut debug::Ddebug;
            unsafe {
                if id<3 {debug::set(p, (i & 1) as u32)} else {
                    assert_eq!(debug::line(p),24429);
                    assert!(debug::flags(p)<=1);
                    syscall_policy::log(4);
                }
            }
        }));
    }
    for t in threads { t.join().unwrap(); }
    unsafe {debug::set(address as *mut debug::Ddebug,0)};
}
