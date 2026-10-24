// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
// Source-only future fixture, actual ABI aliases supplied by the full frozen abi.rs.
#[path="../../sourcehandoff/abi.rs.PREIMAGE"]mod abi;
use abi::{CInt,CLong,CULong};
const EINTR: CInt = 4;
const SIGKILL: CInt = 9;
const SIGSTOP: CInt = 19;
const SIGCHLD: CInt = 17;
const SYS_EPOLL_WAIT: CULong = 232;
const SYS_PPOLL: CInt = 271;
const SYS_PSELECT6: CInt = 270;
const SYS_NANOSLEEP: CInt = 35;
include!("../candidate/syscall_policy.signal_restart.FRAGMENT.rs");
