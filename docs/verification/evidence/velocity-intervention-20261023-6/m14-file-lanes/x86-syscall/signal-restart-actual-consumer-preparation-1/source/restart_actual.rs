// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Genuine default-std HOST core/runtime, complete exact policy fragment.
#![allow(dead_code,unused_imports)]
#[path="abi.ACTUAL.rs"]mod abi;
use abi::{CInt,CLong,CULong};
const EINTR:CInt=4;
const SIGKILL:CInt=9;
const SIGSTOP:CInt=19;
const SIGCHLD:CInt=17;
const SYS_EPOLL_WAIT:CULong=232;
const SYS_PPOLL:CInt=271;
const SYS_PSELECT6:CInt=270;
const SYS_NANOSLEEP:CInt=35;
include!("candidate-policy.ACTUAL.inc");
#[no_mangle]pub extern "C" fn fixture_restart_actual_Rust_ABI(i:usize)->CULong {
 let a=[core::mem::size_of::<CInt>() as CULong,core::mem::size_of::<CLong>() as CULong,core::mem::size_of::<CULong>() as CULong,
 EINTR as CULong,SIGKILL as CULong,SIGSTOP as CULong,SIGCHLD as CULong,15,
 34,130,128,SYS_EPOLL_WAIT,281,7,SYS_PPOLL as CULong,23,SYS_PSELECT6 as CULong,70,69,65,220,230,SYS_NANOSLEEP as CULong,208];a[i]
}
