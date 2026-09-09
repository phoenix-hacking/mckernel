// SPDX-License-Identifier: GPL-2.0-only
//! Benign selected native signal ABI/continuation tests; FP callback is controlled.
#![allow(dead_code)]
#[path = "abi.rs"]
mod abi;
#[path = "native_signal.rs"]
mod native_signal;

use abi::*;
use core::ffi::c_void;
use core::mem::{offset_of, size_of, MaybeUninit};
use std::cell::{Cell, RefCell};

thread_local! {
    static COPIES: Cell<usize> = const { Cell::new(0) };
    static FP_EVENTS: RefCell<Vec<(u64, i32)>> = const { RefCell::new(Vec::new()) };
    static OBSERVED_CONTEXT: Cell<*const X86UserContext> = const { Cell::new(core::ptr::null()) };
}

unsafe extern "C" fn copy_from(dst: *mut u8, src: u64, bytes: usize) -> i64 {
    COPIES.set(COPIES.get() + 1);
    core::ptr::copy_nonoverlapping(src as *const u8, dst, bytes);
    0
}

unsafe extern "C" fn restore_fp(address: u64, size: i32) -> i64 {
    let context = OBSERVED_CONTEXT.get();
    assert!(!context.is_null());
    // The published return state still belongs to the signal handler here.
    assert_eq!((*context).gpr.rax, 15);
    FP_EVENTS.with(|events| events.borrow_mut().push((address, size)));
    0
}

#[test]
fn standard_libc_offsets_and_action_mask() {
    assert_eq!(offset_of!(native_signal::Frame, sigmask), 296);
    assert_eq!(offset_of!(native_signal::Frame, info), 424);
    assert_eq!(size_of::<native_signal::Frame>(), 552);
    let alarm = 1 << (14 - 1);
    let usr1 = 1 << (10 - 1);
    let usr2 = 1 << (12 - 1);
    assert_eq!(
        native_signal::native_signal_action_mask_result(alarm, usr2, 10, 0),
        alarm | usr1 | usr2
    );
    assert_eq!(
        native_signal::native_signal_action_mask_result(alarm, usr2, 10, 0x4000_0000),
        alarm | usr2
    );
}

#[test]
fn native_context_register_mask_and_fp_order_roundtrip() {
    unsafe {
        let mut vm = MaybeUninit::<ProcessVm>::zeroed().assume_init();
        vm.region.user_start = 0x1000;
        vm.region.user_end = 1 << 47;
        let mut thread = MaybeUninit::<Thread>::zeroed().assume_init();
        thread.vm = &mut vm;
        thread.sigstack.ss_flags = 2;
        let mut regs = MaybeUninit::<X86UserContext>::zeroed().assume_init();
        regs.gpr.cs = 0x33;
        regs.gpr.ss = 0x3b;
        regs.gpr.rflags = 0x202;
        regs.gpr.rsp = 0x60000;
        regs.gpr.rip = 0x50000;
        regs.gpr.rdi = 0x1234;
        regs.gpr.rsi = 0x5678;
        let mut fp = [0u8; 832];
        for result in [0, 37, -4i64, -123i64] {
            COPIES.set(0);
            FP_EVENTS.with(|events| events.borrow_mut().clear());
            let mut frame = MaybeUninit::<native_signal::Frame>::zeroed().assume_init();
            frame.sigstack.ss_flags = 2;
            regs.gpr.rsp = 0x60000;
            assert_eq!(
                native_signal::native_signal_context_prepare_result(
                    &regs, 1 << 13, result as u64, 234, 0, &mut frame, Some(copy_from)
                ),
                0
            );
            assert_eq!(frame.regs[13], result as u64);
            assert_eq!(frame.regs[18], 0x3b00_0000_0000_0033);
            assert_eq!(frame.sigmask[0], 1 << 13);
            assert!(frame.sigmask[1..].iter().all(|word| *word == 0));
            // Standard handler edits must survive, including negative RAX.
            frame.regs[12] = 0xabcdef;
            frame.sigmask[0] |= 1 << 14;
            frame.fpregs = fp.as_mut_ptr().cast::<c_void>();
            regs.gpr.rsp = (&mut frame as *mut native_signal::Frame) as u64;
            regs.gpr.rax = 15;
            OBSERVED_CONTEXT.set(&regs);
            assert_eq!(
                native_signal::sigreturn(&mut thread, &mut regs, 832, copy_from, restore_fp),
                Ok(result)
            );
            assert_eq!(COPIES.get(), 1);
            assert_eq!(regs.gpr.rdi, 0x1234);
            assert_eq!(regs.gpr.rsi, 0x5678);
            assert_eq!(regs.gpr.rdx, 0xabcdef);
            assert_eq!(regs.gpr.rsp, 0x60000);
            assert_eq!(regs.gpr.rip, 0x50000);
            assert_eq!(thread.sigmask.val[0], (1 << 13) | (1 << 14));
            assert_eq!(FP_EVENTS.with(|events| events.borrow().len()), 1);
        }
    }
}

#[test]
fn restart_is_a_normal_saved_user_syscall_context() {
    unsafe {
        let instruction = [0x0fu8, 0x05];
        let mut regs = MaybeUninit::<X86UserContext>::zeroed().assume_init();
        regs.gpr.rip = instruction.as_ptr() as u64 + 2;
        regs.gpr.rsp = 0x60000;
        regs.gpr.rdi = 7;
        regs.gpr.rsi = 0x70000;
        regs.gpr.rdx = 16;
        let mut frame = MaybeUninit::<native_signal::Frame>::zeroed().assume_init();
        assert_eq!(
            native_signal::native_signal_context_prepare_result(
                &regs, 0, (-4i64) as u64, 0, 1, &mut frame, Some(copy_from)
            ),
            0
        );
        assert_eq!(frame.regs[16], instruction.as_ptr() as u64);
        assert_eq!(frame.regs[13], 0);
        assert_eq!((frame.regs[8], frame.regs[9], frame.regs[12]), (7, 0x70000, 16));
        assert_eq!(regs.gpr.rip, instruction.as_ptr() as u64 + 2);
    }
}
