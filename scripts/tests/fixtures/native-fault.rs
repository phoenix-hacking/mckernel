// SPDX-License-Identifier: GPL-2.0-only
//! Controlled dispatcher verification, not actual kernel trap delivery.
#![allow(dead_code)]
#[path = "abi.rs"]
mod abi;
#[path = "native_fault.rs"]
mod native_fault;

use abi::X86UserContext;
use core::mem::MaybeUninit;

extern "C" {
    fn native_user_read_u32_checked(from: *const u32, to: *mut u32) -> i64;
    fn native_user_read_u32_fault();
    fn native_user_read_u32_recover();
    fn native_xrstor_fault();
    fn native_xrstor_recover();
}

#[test]
fn ordinary_authorized_u32_load() {
    for input in [0, 1, 0x12345678, u32::MAX] {
        let mut output = !input;
        assert_eq!(
            unsafe { native_user_read_u32_checked(&input, &mut output) },
            0
        );
        assert_eq!(input, output);
    }
}

#[test]
fn exact_kernel_fault_dispatch_preserves_other_state() {
    for (fault, recovery) in [
        (
            native_user_read_u32_fault as *const () as u64,
            native_user_read_u32_recover as *const () as u64,
        ),
        (
            native_xrstor_fault as *const () as u64,
            native_xrstor_recover as *const () as u64,
        ),
    ] {
        for trap in [13, 14] {
            let mut regs = unsafe { MaybeUninit::<X86UserContext>::zeroed().assume_init() };
            regs.gpr.cs = 0x20;
            regs.gpr.rip = fault;
            regs.gpr.rsp = 0xfeed0000;
            regs.gpr.rdi = 0x1234;
            regs.gpr.rflags = 0x202;
            assert_eq!(
                unsafe { native_fault::native_fault_fixup(&mut regs, trap) },
                1
            );
            assert_eq!(regs.gpr.rip, recovery);
            assert_eq!(regs.gpr.rax as i64, -14);
            assert_eq!(
                (regs.gpr.cs, regs.gpr.rsp, regs.gpr.rdi, regs.gpr.rflags),
                (0x20, 0xfeed0000, 0x1234, 0x202)
            );
        }
    }
}

#[test]
fn unrelated_traps_pcs_and_user_contexts_are_unchanged() {
    let fault = native_user_read_u32_fault as *const () as u64;
    for (cs, pc, trap) in [
        (0x33, fault, 14),
        (0x20, fault + 1, 14),
        (0x20, 0, 13),
        (0x20, fault, 6),
        (0x20, fault, 0),
    ] {
        let mut regs = unsafe { MaybeUninit::<X86UserContext>::zeroed().assume_init() };
        regs.gpr.cs = cs;
        regs.gpr.rip = pc;
        regs.gpr.rax = 99;
        assert_eq!(
            unsafe { native_fault::native_fault_fixup(&mut regs, trap) },
            0
        );
        assert_eq!((regs.gpr.cs, regs.gpr.rip, regs.gpr.rax), (cs, pc, 99));
    }
    assert_eq!(
        unsafe { native_fault::native_fault_fixup(core::ptr::null_mut(), 14) },
        0
    );
}
