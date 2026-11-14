// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code, unused_imports)]
mod abi;
mod debug;
mod string;
mod sched_helpers {
    unsafe extern "C" {
        pub fn sched_wakeup_thread(thread: *mut crate::abi::Thread, states: crate::abi::CInt)
            -> crate::abi::CInt;
    }
}
mod process_helpers {
    unsafe extern "C" {
        pub fn release_thread(thread: *mut crate::abi::Thread);
    }
}
use abi::CInt;
const SIGKILL: CInt = 9;
const SIGCHLD: CInt = 17;
const SIGCONT: CInt = 18;
const PS_RUNNING: CInt = 1;
const PS_INTERRUPTIBLE: CInt = 2;
const PS_STOPPED: CInt = 0x20;
const PS_TRACED: CInt = 0x40;
const SIGNAL_STOP_CONTINUED: CInt = 2;
const CLD_CONTINUED: CInt = 6;
unsafe extern "C" { fn kprintf(format: *const i8, ...) -> CInt; }
include!("wakeup.FRAGMENT.rs");
#[no_mangle]
pub extern "C" fn fixture_wakeup_abi(index: usize) -> usize {
    use core::mem::{align_of, offset_of, size_of};
    use abi::{Process, SigInfo, SigInfoChild, Thread};
    let values = [
        size_of::<Thread>(), align_of::<Thread>(), size_of::<Process>(),
        align_of::<Process>(), size_of::<SigInfo>(), align_of::<SigInfo>(),
        size_of::<SigInfoChild>(), offset_of!(SigInfo, sifields),
        offset_of!(SigInfo, si_code), offset_of!(SigInfoChild, si_status),
        offset_of!(Thread, proc), offset_of!(Thread, cpu_id), offset_of!(Thread, status),
        offset_of!(Thread, signal_flags), offset_of!(Thread, sigmask),
        offset_of!(Process, status), offset_of!(Process, main_thread),
        offset_of!(Process, parent), offset_of!(Process, pid),
        size_of::<debug::Ddebug>(), align_of::<debug::Ddebug>(),
        SIGKILL as usize, SIGCHLD as usize, SIGCONT as usize, PS_RUNNING as usize,
        PS_INTERRUPTIBLE as usize, PS_STOPPED as usize, PS_TRACED as usize,
        SIGNAL_STOP_CONTINUED as usize, CLD_CONTINUED as usize,
    ];
    values[index]
}
