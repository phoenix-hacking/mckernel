#![no_std]
use core::ffi::c_void;
mod abi {
    pub type CInt = i32;
    pub type CLong = i64;
    #[repr(C)] pub struct SigInfo { _opaque: [u8; 0] }
    #[repr(C)] pub struct Thread { _opaque: [u8; 0] }
}
mod policy {
    use core::ffi::c_void;
    use crate::abi::{CInt, CLong, SigInfo, Thread};
    extern "C" {
        #[link_name = "do_kill"]
        fn f06_ptrace_report_signal_do_kill(thread: *mut Thread, pid: CInt,
            tid: CInt, sig: CInt, info: *mut SigInfo, ptracecont: CInt) -> u64;
    }
    include!("adapter.rs");
    #[path = "bridge.rs"]
    mod bridge;
}
