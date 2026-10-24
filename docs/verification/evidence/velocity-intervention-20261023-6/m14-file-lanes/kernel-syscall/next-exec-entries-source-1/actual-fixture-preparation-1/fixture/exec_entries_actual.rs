//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Actual exec entry/body helpers/getters with one controlled C lifecycle effect.
#![no_std]
mod abi;
use core::ffi::c_void;
use core::mem::{size_of,align_of,offset_of};
use core::ptr::copy_nonoverlapping;
use abi::{CInt,CLong,CULong,X86UserContext,X86BasicRegs};
include!("/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-exec-entries-source-1/fixture-fragments-only/CONSTANTS.UNCHANGED-RUST.inc");
include!("/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-exec-entries-source-1/fixture-fragments-only/exec_entries_actual.RUST-FIXTURE-FRAGMENT.rs.inc");
#[no_mangle]
pub unsafe extern "C" fn f03_exec_fixture_layout(out:*mut usize)->usize {
 let values=[size_of::<X86UserContext>(),align_of::<X86UserContext>(),offset_of!(X86UserContext,gpr),offset_of!(X86UserContext,sr),size_of::<X86BasicRegs>(),align_of::<X86BasicRegs>(),offset_of!(X86BasicRegs,rdi),offset_of!(X86BasicRegs,rsi),offset_of!(X86BasicRegs,rdx),offset_of!(X86BasicRegs,r10),offset_of!(X86BasicRegs,r8),offset_of!(X86BasicRegs,r9),offset_of!(X86BasicRegs,rax),offset_of!(X86BasicRegs,orig_rax)];copy_nonoverlapping(values.as_ptr(),out,values.len());values.len()
}
