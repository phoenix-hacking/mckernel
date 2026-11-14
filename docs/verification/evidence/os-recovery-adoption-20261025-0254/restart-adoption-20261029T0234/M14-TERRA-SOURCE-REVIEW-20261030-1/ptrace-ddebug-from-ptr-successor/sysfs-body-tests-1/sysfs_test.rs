#![feature(c_variadic)]
use core::ffi::{c_void, VaList};
use std::ptr::{addr_of, null, null_mut};
mod abi {
    use core::ffi::c_void;
    pub type CInt=i32; pub type CLong=i64; pub type CULong=u64; pub type SizeT=usize; pub type SSizeT=isize;
    #[repr(C)] pub struct IhkSpinlock { pub head_tail:u32 }
    #[repr(C)] pub struct SysfsOps {
        pub show:Option<unsafe extern "C" fn(*mut Self,*mut c_void,*mut c_void,usize)->isize>,
        pub store:Option<unsafe extern "C" fn(*mut Self,*mut c_void,*mut c_void,usize)->isize>,
        pub release:Option<unsafe extern "C" fn(*mut Self,*mut c_void)>,
    }
}
mod string {
    unsafe extern "C" {
        pub fn strlen(s:*const i8)->usize; pub fn strpbrk(s:*const i8, accept:*const i8)->*mut i8;
        pub fn strncmp(a:*const i8,b:*const i8,n:usize)->i32; pub fn strchr(s:*const i8,c:i32)->*mut i8;
        pub fn strcmp(a:*const i8,b:*const i8)->i32;
    }
}
mod numparse {
    use core::ffi::VaList;
    unsafe extern "C" {
        pub fn snprintf(buf:*mut i8,n:usize,fmt:*const i8,...)->i32;
        pub fn strtol(s:*const i8,end:*mut *mut i8,base:i32)->i64;
    }
    pub unsafe fn vsnprintf_va_list_result(_buf:*mut i8,_n:usize,_fmt:*const i8,_args:&mut VaList<'_>)->i32 { 0 }
}
#[path="debug.rs"] mod debug;
mod syscall_policy {
    pub type CInt=i32;
    pub const PTRACE_CONTROL_LOG_WAKEUP_ENTER:CInt=4;
    pub use crate::debug::kprintf;
    #[path="/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/ptrace-ddebug-from-ptr-successor-terra-20261030-1/postimage/kernel/rust/syscall_ptrace_wakeup_logger.rs"]
    pub mod syscall_ptrace_wakeup_logger;
}
#[no_mangle] unsafe extern "C" fn __ihk_mc_spinlock_lock(_: *mut abi::IhkSpinlock)->u64 {0}
#[no_mangle] unsafe extern "C" fn __ihk_mc_spinlock_unlock(_: *mut abi::IhkSpinlock,_:u64) {}
#[no_mangle] unsafe extern "C" fn cpu_disable_interrupt_save()->u64 {0}
#[no_mangle] unsafe extern "C" fn cpu_restore_interrupt(_:u64) {}
#[no_mangle] unsafe extern "C" fn cpu_pause() {}
#[no_mangle] unsafe extern "C" fn cpu_interrupt_disabled()->i32 {1}
#[no_mangle] unsafe extern "C" fn ihk_mc_delay_us(_:i32) {}
#[no_mangle] unsafe extern "C" fn ihk_mc_get_processor_id()->i32 {0}
#[no_mangle] unsafe extern "C" fn ihk_mc_spinlock_init(_: *mut abi::IhkSpinlock) {}
#[no_mangle] unsafe extern "C" fn eventfd(_:i32) {}
#[no_mangle] unsafe extern "C" fn sysfs_createf(_: *mut abi::SysfsOps,_:*mut c_void,_:i32,_:*const i8,mut _args:...)->i32 {0}
#[used]
#[link_section="__verbose"]
static mut NEIGHBOR:debug::Ddebug=debug::Ddebug{file:c"neighbor.c".as_ptr(),func:c"neighbor".as_ptr(),fmt:null(),line_flags:17};
unsafe extern "C" { static __start___verbose:debug::Ddebug; static __stop___verbose:debug::Ddebug; }
unsafe fn store(cmd:&str) -> isize { let mut b=cmd.as_bytes().to_vec(); debug::test_store(&mut b) }
unsafe fn show()->String {
    let mut b=[0u8;1024]; let n=debug::test_show(&mut b); assert!(n>=0); String::from_utf8(b[..n as usize].to_vec()).unwrap()
}
fn assert_records(s:&str,wakeup:&str,neighbor:&str) {
    let mut lines=s.lines(); assert_eq!(lines.next(),Some("# filename:lineno function flags format"));
    let rows:Vec<_>=lines.collect(); assert_eq!(rows.len(),2); assert!(rows.contains(&wakeup)); assert!(rows.contains(&neighbor));
}
#[test] fn actual_store_and_show_match_selected_and_adjacent_records() { unsafe {
    let selected=syscall_policy::syscall_ptrace_wakeup_logger::test_record() as usize;
    let adjacent=addr_of!(NEIGHBOR) as usize;
    let start=addr_of!(__start___verbose) as usize; let stop=addr_of!(__stop___verbose) as usize;
    assert_eq!(stop-start,64); assert_eq!(selected.abs_diff(adjacent),32); assert_eq!(start, selected.min(adjacent));
    let a="/src/kernel/syscall.c:24429 ptrace_wakeup_log_bridge =_"; let b="neighbor.c:17 neighbor =_";
    assert_records(&show(),a,b);
    for cmd in ["file /src/kernel/syscall.c line 24430 +p\n", "func absent +p\n"] { assert_eq!(store(cmd),cmd.len() as isize); assert_records(&show(),a,b); }
    let cmd="file /src/kernel/syscall.c line 24429 +p\n"; assert_eq!(store(cmd),cmd.len() as isize);
    assert_records(&show(),"/src/kernel/syscall.c:24429 ptrace_wakeup_log_bridge =p",b);
    let cmd="func neighbor =p\n"; assert_eq!(store(cmd),cmd.len() as isize);
    assert_records(&show(),"/src/kernel/syscall.c:24429 ptrace_wakeup_log_bridge =p","neighbor.c:17 neighbor =p");
    let cmd="func ptrace_wakeup_log_bridge -p\n"; assert_eq!(store(cmd),cmd.len() as isize);
    assert_records(&show(),a,"neighbor.c:17 neighbor =p");
    let cmd="file neighbor.c line 17 =_\n"; assert_eq!(store(cmd),cmd.len() as isize); assert_records(&show(),a,b);
    let cmd="func ptrace_wakeup_log_bridge =p\n"; assert_eq!(store(cmd),cmd.len() as isize);
    assert_records(&show(),"/src/kernel/syscall.c:24429 ptrace_wakeup_log_bridge =p",b);
    let cmd="func ptrace_wakeup_log_bridge =_\n"; assert_eq!(store(cmd),cmd.len() as isize); assert_records(&show(),a,b);
    assert_eq!(debug::test_store(&mut []),-22); assert_eq!(debug::test_show(&mut [0;1024])>0,true);
} }
