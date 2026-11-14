//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Exact existing helper plus new public entry/adapter and actual repr(C) ABI.
#![no_std]
#[path = "../sourcehandoff/abi.rs.PREIMAGE"]
mod abi;
use core::ffi::c_void;
use core::mem::{offset_of, size_of, align_of};
use core::ptr::{read_volatile, write_volatile};
use abi::{CInt, CLong, CULong, SizeT, Thread, X86UserContext};
const EFAULT: CInt = 14;
type PtraceReportSignalFn = unsafe extern "C" fn(*mut c_void, CInt);
include!("field_ptr.ACTUAL-BODY.inc");
include!("existing-helper.ACTUAL-BODY.inc");
include!("../candidate/syscall_policy.arch_ptrace_syscall_event.FRAGMENT.rs");
#[no_mangle] pub extern "C" fn fixture_context_size() -> usize { size_of::<X86UserContext>() }
#[no_mangle] pub extern "C" fn fixture_context_align() -> usize { align_of::<X86UserContext>() }
#[no_mangle] pub extern "C" fn fixture_rax_offset() -> usize { offset_of!(X86UserContext, gpr)+offset_of!(abi::X86BasicRegs, rax) }
