//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Compile-only actual native Rust types; not a production artifact.
#![cfg(sigreturn_abi_witness_only)]
use core::mem::{align_of, offset_of, size_of};
use crate::abi::{CULong, SigStack, SigSet, Thread, ProcessVm, VmRegions, X86UserContext, X86BasicRegs};
use crate::native_signal::Frame;
const SIGSET_EXAMPLE: SigSet = SigSet { val: [0] };
const fn inferred_size<T>(_: &T) -> usize { size_of::<T>() }
#[used]
#[no_mangle]
#[link_section = ".sigreturn_extra_rust"]
pub static sigreturn_extra_rust_geometry: [u64; 46] = [
    (offset_of!(Frame, flags)) as u64, // 0: frame.flags
    (offset_of!(Frame, link)) as u64, // 1: frame.link
    (offset_of!(Frame, sigstack)) as u64, // 2: frame.sigstack
    (offset_of!(Frame, regs)) as u64, // 3: frame.regs
    (offset_of!(Frame, fpregs)) as u64, // 4: frame.fpregs
    (offset_of!(Frame, reserve)) as u64, // 5: frame.reserve
    (offset_of!(Frame, sigmask)) as u64, // 6: frame.sigmask
    (offset_of!(Frame, info)) as u64, // 7: frame.info
    (offset_of!(SigStack, ss_sp)) as u64, // 8: stack.ss_sp
    (offset_of!(SigStack, ss_flags)) as u64, // 9: stack.ss_flags
    (offset_of!(SigStack, ss_size)) as u64, // 10: stack.ss_size
    (size_of::<SigStack>()) as u64, // 11: stack.size
    (align_of::<SigStack>()) as u64, // 12: stack.align
    (offset_of!(Thread, vm)) as u64, // 13: thread.vm
    (offset_of!(ProcessVm, region)) as u64, // 14: process_vm.region
    (offset_of!(VmRegions, user_start)) as u64, // 15: vm_regions.user_start
    (offset_of!(VmRegions, user_end)) as u64, // 16: vm_regions.user_end
    (offset_of!(X86UserContext, gpr)) as u64, // 17: context.gpr
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, r8)) as u64, // 18: context.gpr.r8
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, r9)) as u64, // 19: context.gpr.r9
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, r10)) as u64, // 20: context.gpr.r10
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, r11)) as u64, // 21: context.gpr.r11
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, r12)) as u64, // 22: context.gpr.r12
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, r13)) as u64, // 23: context.gpr.r13
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, r14)) as u64, // 24: context.gpr.r14
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, r15)) as u64, // 25: context.gpr.r15
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, rdi)) as u64, // 26: context.gpr.rdi
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, rsi)) as u64, // 27: context.gpr.rsi
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, rbp)) as u64, // 28: context.gpr.rbp
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, rbx)) as u64, // 29: context.gpr.rbx
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, rdx)) as u64, // 30: context.gpr.rdx
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, rax)) as u64, // 31: context.gpr.rax
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, rcx)) as u64, // 32: context.gpr.rcx
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, rsp)) as u64, // 33: context.gpr.rsp
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, rip)) as u64, // 34: context.gpr.rip
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, rflags)) as u64, // 35: context.gpr.rflags
    (offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, orig_rax)) as u64, // 36: context.gpr.orig_rax
    (offset_of!(Frame, regs) + 15 * size_of::<CULong>()) as u64, // 37: frame.regs.rsp
    (offset_of!(Frame, regs) + 16 * size_of::<CULong>()) as u64, // 38: frame.regs.rip
    (offset_of!(Frame, regs) + 17 * size_of::<CULong>()) as u64, // 39: frame.regs.rflags
    (offset_of!(Thread, sigmask)) as u64, // 40: thread.sigmask
    (size_of::<SigSet>()) as u64, // 41: sigset.size
    (align_of::<SigSet>()) as u64, // 42: sigset.align
    (offset_of!(SigSet, val)) as u64, // 43: sigset.first.offset
    (offset_of!(Thread, sigmask) + offset_of!(SigSet, val)) as u64, // 44: thread.sigmask.first.offset
    (inferred_size(&SIGSET_EXAMPLE.val[0])) as u64, // 45: sigset.first.width
];
