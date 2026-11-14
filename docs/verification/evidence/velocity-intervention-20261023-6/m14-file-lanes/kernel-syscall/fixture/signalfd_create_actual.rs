//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Actual selected new request/admission body plus unchanged signalfd4 helper.
#![no_std]
use core::ffi::c_void;
use core::mem::{MaybeUninit,size_of};
type CInt=i32;type CLong=i64;type CULong=u64;type SizeT=usize;
const EINVAL:CInt=22;const EFAULT:CInt=14;
const SFD_CLOEXEC:CInt=0o2000000;const SFD_NONBLOCK:CInt=0o4000;
type SyscallCopyFromUserFn=unsafe extern "C" fn(*mut u8,CULong,SizeT)->CLong;
type SyscallSignalfdCreateFn=unsafe extern "C" fn(CInt,CInt)->CLong;
type SyscallSignalfdPublishFn=unsafe extern "C" fn(*mut c_void,CInt,*const CULong,CInt)->CLong;
include!("SyscallRequest.ACTUAL-RUST-ABI.inc");
unsafe extern "C" {fn ihk_mc_get_processor_id()->CInt;fn do_syscall(request:*mut SyscallRequest,cpu:CInt)->CLong;}
include!("../candidate/signalfd_create.RUST-FRAGMENT.rs.inc");
include!("signalfd4_sigsetsize_result.UNCHANGED-RUST.inc");
include!("signalfd4_flags_result.UNCHANGED-RUST.inc");
include!("signalfd4_body_result.UNCHANGED-RUST.inc");
