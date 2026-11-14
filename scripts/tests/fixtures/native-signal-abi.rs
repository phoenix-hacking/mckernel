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
    static COPY_FAILURE: Cell<bool> = const { Cell::new(false) };
    static FP_EVENTS: RefCell<Vec<(u64, i32)>> = const { RefCell::new(Vec::new()) };
    static OBSERVED_CONTEXT: Cell<*const X86UserContext> = const { Cell::new(core::ptr::null()) };
}

unsafe extern "C" fn copy_from(dst: *mut u8, src: u64, bytes: usize) -> i64 {
    COPIES.set(COPIES.get() + 1);
    if COPY_FAILURE.get() {
        return -14;
    }
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

unsafe extern "C" fn restore_fp_failure(_address: u64, _size: i32) -> i64 {
    -14
}

unsafe extern "C" fn publish_restorer(_address: u64, _source: *const u8, _bytes: usize) -> i64 {
    0
}

#[test]
fn selected_native_consumer_c81_altstack_roundtrip() {
    unsafe {
        let mut vm = MaybeUninit::<ProcessVm>::zeroed().assume_init();
        vm.region.user_start = 0x1000;
        vm.region.user_end = 1 << 47;
        let mut thread = MaybeUninit::<Thread>::zeroed().assume_init();
        thread.vm = &mut vm;
        thread.sigstack.ss_sp = 0x20000 as *mut c_void;
        thread.sigstack.ss_size = 65536;
        thread.sigstack.ss_flags = 0;
        let mut regs = MaybeUninit::<X86UserContext>::zeroed().assume_init();
        regs.gpr.rflags = 0x202;
        regs.gpr.rax = 15;
        let regs_ptr = core::ptr::addr_of_mut!(regs);
        let mut fp = [0u8; 832];

        for _ in 0..2 {
            let mut saved = MaybeUninit::<SigStack>::zeroed().assume_init();
            let mut frame_address = 0;
            let mut fp_address = 0;
            assert_eq!(
                native_signal::native_signal_stack_prepare_result(
                    &thread.sigstack,
                    &mut saved,
                    0x70000,
                    0x08000000,
                    832,
                    size_of::<native_signal::Frame>(),
                    0x1000,
                    1 << 47,
                    &mut frame_address,
                    &mut fp_address,
                ),
                0
            );
            assert!(frame_address - 8 > 0x20000);
            assert!(frame_address - 8 <= 0x20000 + 65536);
            assert_eq!(
                native_signal::native_signal_stack_publish_result(
                    &mut thread.sigstack,
                    frame_address,
                    0x4567,
                    Some(publish_restorer),
                ),
                0
            );
            assert_eq!(thread.sigstack.ss_flags, 1);

            let mut frame = MaybeUninit::<native_signal::Frame>::zeroed().assume_init();
            frame.sigstack = saved;
            frame.regs[15] = 0x70000;
            frame.regs[16] = 0x50000;
            frame.regs[17] = 0x202;
            frame.regs[13] = 37;
            frame.fpregs = fp.as_mut_ptr().cast();
            regs.gpr.rsp = (&mut frame as *mut native_signal::Frame) as u64;
            regs.gpr.rax = 15;
            OBSERVED_CONTEXT.set(regs_ptr);
            assert_eq!(
                native_signal::sigreturn(&mut thread, regs_ptr, 832, copy_from, restore_fp),
                Ok(37)
            );
            assert_eq!((regs.gpr.rsp, regs.gpr.rip), (0x70000, 0x50000));
            assert_eq!(
                (
                    thread.sigstack.ss_sp as u64,
                    thread.sigstack.ss_size,
                    thread.sigstack.ss_flags,
                ),
                (0x20000, 65536, 0)
            );
        }

        // A nested handler consumes a second selected frame while the outer
        // handler is active; its normal return must retain SS_ONSTACK until
        // the outer frame is consumed.
        let mut outer_saved = MaybeUninit::<SigStack>::zeroed().assume_init();
        let mut outer_address = 0;
        let mut outer_fp = 0;
        assert_eq!(
            native_signal::native_signal_stack_prepare_result(
                &thread.sigstack,
                &mut outer_saved,
                0x70000,
                0x08000000,
                832,
                size_of::<native_signal::Frame>(),
                0x1000,
                1 << 47,
                &mut outer_address,
                &mut outer_fp,
            ),
            0
        );
        assert_eq!(
            native_signal::native_signal_stack_publish_result(
                &mut thread.sigstack,
                outer_address,
                0x4567,
                Some(publish_restorer),
            ),
            0
        );
        assert_eq!(thread.sigstack.ss_flags, 1);

        let mut nested_saved = MaybeUninit::<SigStack>::zeroed().assume_init();
        let mut nested_address = 0;
        let mut nested_fp = 0;
        assert_eq!(
            native_signal::native_signal_stack_prepare_result(
                &thread.sigstack,
                &mut nested_saved,
                outer_address - 64,
                0x08000000,
                832,
                size_of::<native_signal::Frame>(),
                0x1000,
                1 << 47,
                &mut nested_address,
                &mut nested_fp,
            ),
            0
        );
        assert!(nested_address - 8 > 0x20000);
        assert!(nested_address - 8 <= 0x20000 + 65536);
        assert_eq!(nested_saved.ss_flags, 1);
        assert_eq!(
            native_signal::native_signal_stack_publish_result(
                &mut thread.sigstack,
                nested_address,
                0x4567,
                Some(publish_restorer),
            ),
            0
        );
        let mut nested = MaybeUninit::<native_signal::Frame>::zeroed().assume_init();
        nested.sigstack = nested_saved;
        nested.regs[15] = outer_address - 64;
        nested.regs[16] = 0x50000;
        nested.regs[17] = 0x202;
        nested.regs[13] = 37;
        nested.fpregs = fp.as_mut_ptr().cast();
        regs.gpr.rsp = (&mut nested as *mut native_signal::Frame) as u64;
        regs.gpr.rax = 15;
        OBSERVED_CONTEXT.set(regs_ptr);
        assert_eq!(
            native_signal::sigreturn(&mut thread, regs_ptr, 832, copy_from, restore_fp),
            Ok(37)
        );
        assert_eq!((regs.gpr.rsp, regs.gpr.rip), (outer_address - 64, 0x50000));
        assert_eq!(thread.sigstack.ss_flags, 1);

        let mut outer = MaybeUninit::<native_signal::Frame>::zeroed().assume_init();
        outer.sigstack = outer_saved;
        outer.regs[15] = 0x70000;
        outer.regs[16] = 0x50000;
        outer.regs[17] = 0x202;
        outer.regs[13] = 37;
        outer.fpregs = fp.as_mut_ptr().cast();
        regs.gpr.rsp = (&mut outer as *mut native_signal::Frame) as u64;
        regs.gpr.rax = 15;
        OBSERVED_CONTEXT.set(regs_ptr);
        assert_eq!(
            native_signal::sigreturn(&mut thread, regs_ptr, 832, copy_from, restore_fp),
            Ok(37)
        );
        assert_eq!((regs.gpr.rsp, regs.gpr.rip), (0x70000, 0x50000));
        assert_eq!(
            (
                thread.sigstack.ss_sp as u64,
                thread.sigstack.ss_size,
                thread.sigstack.ss_flags,
            ),
            (0x20000, 65536, 0)
        );

        // Both pre-publication consumers fail before committing any context,
        // mask, or complete altstack state.
        for fp_failure in [false, true] {
            thread.sigmask.val[0] = 0xaaaa;
            thread.sigstack.ss_sp = 0x22000 as *mut c_void;
            thread.sigstack.ss_size = 32768;
            thread.sigstack.ss_flags = 1;
            let before_stack = (
                thread.sigstack.ss_sp as u64,
                thread.sigstack.ss_size,
                thread.sigstack.ss_flags,
            );
            let before_mask = thread.sigmask.val[0];
            let mut failed = MaybeUninit::<native_signal::Frame>::zeroed().assume_init();
            failed.sigstack.ss_sp = 0x24000 as *mut c_void;
            failed.sigstack.ss_size = 16384;
            failed.sigstack.ss_flags = 0;
            failed.regs[15] = 0x71000;
            failed.regs[16] = 0x51000;
            failed.regs[17] = 0x202;
            failed.regs[13] = 19;
            failed.fpregs = fp.as_mut_ptr().cast();
            regs.gpr.rsp = (&mut failed as *mut native_signal::Frame) as u64;
            regs.gpr.rip = 0x4f000;
            regs.gpr.rax = 15;
            let before_regs = (regs.gpr.rsp, regs.gpr.rip, regs.gpr.rax);
            COPY_FAILURE.set(!fp_failure);
            let result = native_signal::sigreturn(
                &mut thread,
                regs_ptr,
                832,
                copy_from,
                if fp_failure { restore_fp_failure } else { restore_fp },
            );
            COPY_FAILURE.set(false);
            assert_eq!(result, Err(-14));
            assert_eq!((regs.gpr.rsp, regs.gpr.rip, regs.gpr.rax), before_regs);
            assert_eq!(thread.sigmask.val[0], before_mask);
            assert_eq!(
                (
                    thread.sigstack.ss_sp as u64,
                    thread.sigstack.ss_size,
                    thread.sigstack.ss_flags,
                ),
                before_stack
            );
        }
    }
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
fn selected_handler_and_restorer_user_interval() {
    let start = 0x200000;
    let end = 1 << 47;
    let handler = 0x401000;
    let restorer = 0x2aaa_aaa4_b1c0;
    assert_eq!(
        native_signal::native_signal_entry_targets_result(handler, restorer, start, end),
        0
    );
    assert_eq!(
        native_signal::native_signal_entry_targets_result(start, end - 1, start, end),
        0
    );
    for target in [0, start - 1, end, u64::MAX] {
        assert_eq!(
            native_signal::native_signal_entry_targets_result(target, restorer, start, end),
            -14
        );
        assert_eq!(
            native_signal::native_signal_entry_targets_result(handler, target, start, end),
            -14
        );
    }
    assert_eq!(
        native_signal::native_signal_entry_targets_result(handler, restorer, end, start),
        -14
    );
    assert_eq!(
        native_signal::native_signal_entry_targets_result(handler, end, start, u64::MAX),
        -14
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
        let regs_ptr = core::ptr::addr_of_mut!(regs);
        let mut fp = [0u8; 832];
        for result in [0, 37, -4i64, -123i64] {
            COPIES.set(0);
            FP_EVENTS.with(|events| events.borrow_mut().clear());
            let mut frame = MaybeUninit::<native_signal::Frame>::zeroed().assume_init();
            frame.sigstack.ss_flags = 2;
            regs.gpr.rsp = 0x60000;
            assert_eq!(
                native_signal::native_signal_context_prepare_result(
                    &regs,
                    1 << 13,
                    result as u64,
                    234,
                    0,
                    &mut frame,
                    Some(copy_from)
                ),
                0
            );
            assert_eq!(frame.regs[13], result as u64);
            assert_eq!(frame.regs[18], 0x003b_0000_0000_0033);
            assert_eq!(frame.sigmask[0], 1 << 13);
            assert!(frame.sigmask[1..].iter().all(|word| *word == 0));
            // Standard handler edits must survive, including negative RAX.
            frame.regs[12] = 0xabcdef;
            frame.sigmask[0] |= 1 << 14;
            frame.fpregs = fp.as_mut_ptr().cast::<c_void>();
            regs.gpr.rsp = (&mut frame as *mut native_signal::Frame) as u64;
            regs.gpr.rax = 15;
            OBSERVED_CONTEXT.set(regs_ptr);
            assert_eq!(
                native_signal::sigreturn(&mut thread, regs_ptr, 832, copy_from, restore_fp),
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
                &regs,
                0,
                (-4i64) as u64,
                0,
                1,
                &mut frame,
                Some(copy_from)
            ),
            0
        );
        assert_eq!(frame.regs[16], instruction.as_ptr() as u64);
        assert_eq!(frame.regs[13], 0);
        assert_eq!(
            (frame.regs[8], frame.regs[9], frame.regs[12]),
            (7, 0x70000, 16)
        );
        assert_eq!(regs.gpr.rip, instruction.as_ptr() as u64 + 2);
    }
}
