//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Proposed exact existing selected Rust companion providers; no product/body changes.
#![no_std]
#[path="../fixture/abi.rs"] mod abi;
use abi::{CInt,CULong,X86UserContext};
use core::ptr::{read_volatile,write_volatile};
include!("x86_syscall_read.ACTUAL-UNCHANGED.rs.inc");
include!("x86_syscall_write.ACTUAL-UNCHANGED.rs.inc");
include!("ihk_mc_syscall_arg0.ACTUAL-UNCHANGED.rs.inc");
include!("ihk_mc_syscall_arg1.ACTUAL-UNCHANGED.rs.inc");
include!("ihk_mc_syscall_arg2.ACTUAL-UNCHANGED.rs.inc");
include!("ihk_mc_syscall_set_arg0.ACTUAL-UNCHANGED.rs.inc");
include!("ihk_mc_syscall_set_arg1.ACTUAL-UNCHANGED.rs.inc");
include!("ihk_mc_syscall_set_arg2.ACTUAL-UNCHANGED.rs.inc");
include!("__sigmask.ACTUAL-UNCHANGED.rs.inc");

// Source-only ABI/type witnesses for the exact imported production functions.
const _: unsafe extern "C" fn(*const X86UserContext)->CULong=ihk_mc_syscall_arg0;
const _: unsafe extern "C" fn(*const X86UserContext)->CULong=ihk_mc_syscall_arg1;
const _: unsafe extern "C" fn(*const X86UserContext)->CULong=ihk_mc_syscall_arg2;
const _: unsafe extern "C" fn(*mut X86UserContext,CULong)=ihk_mc_syscall_set_arg0;
const _: unsafe extern "C" fn(*mut X86UserContext,CULong)=ihk_mc_syscall_set_arg1;
const _: unsafe extern "C" fn(*mut X86UserContext,CULong)=ihk_mc_syscall_set_arg2;
const _: extern "C" fn(CULong)->CULong=__sigmask;
const _: ()={
 assert!(core::mem::size_of::<X86UserContext>()==224);
 assert!(core::mem::align_of::<X86UserContext>()==8);
 assert!(core::mem::offset_of!(X86UserContext,gpr)==56);
 assert!(core::mem::offset_of!(X86UserContext,gpr)+core::mem::offset_of!(abi::X86BasicRegs,rdi)==168);
 assert!(core::mem::offset_of!(X86UserContext,gpr)+core::mem::offset_of!(abi::X86BasicRegs,rsi)==160);
 assert!(core::mem::offset_of!(X86UserContext,gpr)+core::mem::offset_of!(abi::X86BasicRegs,rdx)==152);
};
