// SPDX-License-Identifier: GPL-2.0-only
//! Actual native stack helpers and sigreturn with controlled user-copy/XSAVE.
#![allow(dead_code)]

#[path = "abi.rs"]
mod abi;
#[path = "native_signal.rs"]
mod native_signal;
use abi::*;
#[cfg(not(native_linux_irq_work_v6_12))]
use core::ptr::read_volatile;
use core::{
    ffi::c_void,
    mem::{offset_of, size_of, MaybeUninit},
    ptr::write_volatile,
};
use std::cell::{Cell, RefCell};
include!("signal-bodies.rs");

thread_local! {
    static FAULT: Cell<usize> = const { Cell::new(0) };
    static COPIES: Cell<usize> = const { Cell::new(0) };
    static TAMPER: Cell<bool> = const { Cell::new(false) };
    static SAVED: RefCell<Vec<(u64,Vec<u8>)>> = const { RefCell::new(Vec::new()) };
    static ALLOCATION: RefCell<Vec<u8>> = const { RefCell::new(Vec::new()) };
    static EVENTS: RefCell<Vec<i32>> = const { RefCell::new(Vec::new()) };
}
fn stack(base: u64, size: usize, flags: i32) -> SigStack {
    SigStack {
        ss_sp: base as *mut c_void,
        ss_size: size,
        ss_flags: flags,
        padding: 0,
    }
}
fn tuple(s: &SigStack) -> (u64, usize, i32) {
    (s.ss_sp as u64, s.ss_size, s.ss_flags)
}
fn reset() {
    FAULT.set(0);
    COPIES.set(0);
    TAMPER.set(false);
    SAVED.with(|v| v.borrow_mut().clear());
    EVENTS.with(|v| v.borrow_mut().clear());
}
unsafe extern "C" fn copy_from(dst: *mut u8, src: u64, len: usize) -> i64 {
    let count = COPIES.get() + 1;
    COPIES.set(count);
    if FAULT.get() == count {
        return -14;
    }
    core::ptr::copy_nonoverlapping(src as *const u8, dst, len);
    if TAMPER.get() && len == size_of::<RtSigreturnFrame>() {
        let f = &mut *(src as *mut RtSigreturnFrame);
        f.sigrc = 999;
        f.restart = 1;
        f.num = 999;
    }
    0
}
unsafe extern "C" fn copy_to(dst: u64, src: *const u8, len: usize) -> i64 {
    let count = COPIES.get() + 1;
    COPIES.set(count);
    if FAULT.get() == count {
        return -14;
    }
    SAVED.with(|v| {
        v.borrow_mut()
            .push((dst, core::slice::from_raw_parts(src, len).to_vec()))
    });
    0
}
unsafe extern "C" fn allocate(size: usize, _flags: u64) -> *mut c_void {
    EVENTS.with(|v| v.borrow_mut().push(4));
    ALLOCATION.with(|v| {
        let mut v = v.borrow_mut();
        v.resize(size, 0);
        v.as_mut_ptr().cast()
    })
}
unsafe extern "C" fn free(_p: *mut c_void) {
    EVENTS.with(|v| v.borrow_mut().push(6));
}
unsafe extern "C" fn xrstor(p: *mut c_void) {
    assert_eq!(p as usize % 64, 0);
    EVENTS.with(|v| v.borrow_mut().push(5));
}
unsafe extern "C" fn syscall(num: i32, ctx: *mut c_void) -> i64 {
    assert_eq!(num, 56);
    assert_eq!((*(ctx as *mut X86UserContext)).gpr.rdi, 0x1234);
    -77
}
unsafe extern "C" fn signal(sig: i32, _ctx: *mut c_void, info: *const SigInfo) {
    assert_eq!(sig, 5);
    assert_eq!((*info).si_code, 2);
    EVENTS.with(|v| v.borrow_mut().push(1));
}
unsafe extern "C" fn resched() {
    EVENTS.with(|v| v.borrow_mut().push(2));
}
unsafe extern "C" fn check(sig: i32, _ctx: *mut c_void, num: i32) {
    assert_eq!((sig, num), (0, -1));
    EVENTS.with(|v| v.borrow_mut().push(3));
}
unsafe fn returning(
    thread: &mut Thread,
    ctx: &mut X86UserContext,
    frame: &mut RtSigreturnFrame,
    xsave: i32,
) -> i64 {
    ctx.gpr.rsp = frame as *mut RtSigreturnFrame as u64;
    arch_rt_sigreturn_body_result(
        (thread as *mut Thread).cast(),
        ctx,
        offset_of!(Thread, sigmask),
        offset_of!(Thread, sigstack),
        size_of::<SigStack>(),
        size_of::<RtSigreturnFrame>(),
        xsave,
        0,
        Some(copy_from),
        Some(syscall),
        Some(signal),
        Some(resched),
        Some(check),
        Some(allocate),
        Some(free),
        Some(xrstor),
    )
}
unsafe fn frame(sp: u64, saved: SigStack) -> RtSigreturnFrame {
    let mut f = MaybeUninit::<RtSigreturnFrame>::zeroed().assume_init();
    f.sigstack = saved;
    f.sigrc = 37;
    f.regs[RTSIG_REG_RSP] = sp;
    f.regs[RTSIG_REG_RDI] = 0x1234;
    f.regs[RTSIG_REG_OLDMASK] = 0x4444;
    f.regs[RTSIG_REG_RIP] = 0x4567;
    f
}
unsafe fn prepare(s: &SigStack, sp: u64, flags: u64, xsave: i32) -> (i64, SigStack, u64, u64) {
    let mut saved = stack(0xdead, 91, 7);
    let mut frame = 11;
    let mut fp = 22;
    let rc = native_signal::native_signal_stack_prepare_result(
        s,
        &mut saved,
        sp,
        flags,
        xsave,
        size_of::<RtSigreturnFrame>(),
        0x1000,
        0x800000000000,
        &mut frame,
        &mut fp,
    );
    (rc, saved, frame, fp)
}

#[test]
fn pinned_linux_stack_configuration_vectors() {
    let vectors = include_bytes!("vectors.bin");
    let expected = include_str!("c-reference.log").lines().collect::<Vec<_>>();
    assert_eq!(vectors.len() / 80, expected.len());
    for (i, bytes) in vectors.chunks_exact(80).enumerate() {
        reset();
        let w = bytes
            .chunks_exact(8)
            .map(|b| u64::from_le_bytes(b.try_into().unwrap()))
            .collect::<Vec<_>>();
        let mut s = stack(w[0], w[1] as usize, w[2] as i32);
        let new = stack(w[4], w[5] as usize, w[6] as i32);
        let rc = unsafe {
            native_signal::sigaltstack(
                &mut s,
                w[3],
                if w[7] != 0 {
                    &new as *const SigStack as u64
                } else {
                    0
                },
                if w[8] != 0 { 0xabc0 } else { 0 },
                Some(copy_from),
                Some(copy_to),
            )
        };
        let final_state = native_signal::snapshot(&s, w[3]);
        let old = SAVED.with(|v| {
            v.borrow()
                .last()
                .map(|(_, b)| unsafe { core::ptr::read_unaligned(b.as_ptr().cast::<SigStack>()) })
        });
        let (a, b, c) = old.as_ref().map(tuple).unwrap_or((0, 0, 0));
        let output = format!(
            "{} {} {} {} {} {} {}",
            rc, final_state.ss_sp as u64, final_state.ss_size, final_state.ss_flags, a, b, c
        );
        assert_eq!(output, expected[i], "vector {} {:?}", i, w);
    }
}

#[test]
fn placement_preserves_red_zone_bounds_alignment_and_prior_state() {
    unsafe {
        for offset in 0..128 {
            let s = stack(0x20000, 65536, 0);
            let (rc, saved, frame, fp) = prepare(&s, 0x70000 + offset, 0x08000000, 832);
            assert_eq!(rc, 0);
            assert_eq!(tuple(&s), tuple(&saved));
            assert_eq!(fp, 0x30000 - 832);
            assert_eq!(frame % 16, 0);
            assert!(frame - 8 > 0x20000);
            let (rc, _, frame, fp) = prepare(&s, 0x70000 + offset, 0, 832);
            assert_eq!(rc, 0);
            assert_eq!(fp + 832, 0x70000 + offset - 128);
            assert!(frame < fp);
            let (rc, saved, frame, fp) = prepare(&s, 0x28000 + offset, 0x08000000, 832);
            assert_eq!(rc, 0);
            assert_eq!(saved.ss_flags, 1);
            assert_eq!(fp + 832, 0x28000 + offset - 128);
            assert!(frame < fp);
        }
        for (s, sp, flags, size) in [
            (stack(0x20000, 64, 0), 0x70000, 0x08000000, 832),
            (stack(u64::MAX - 100, 500, 0), 0x70000, 0x08000000, 832),
            (stack(0, 0, 2), 100, 0, 832),
            (stack(0, 0, 2), 0x800000001000, 0, 832),
            (stack(0x20000, 65536, 0), 0x20010, 0x08000000, 832),
            (stack(0x20000, 65536, 0), 0x70000, 0x08000000, -1),
        ] {
            let (rc, saved, f, fp) = prepare(&s, sp, flags, size);
            assert_eq!(rc, -14);
            assert_eq!(tuple(&saved), (0xdead, 91, 7));
            assert_eq!((f, fp), (11, 22));
        }
    }
}

#[test]
fn checked_restorer_copy_is_the_stack_state_commit_point() {
    unsafe {
        for fail in [false, true] {
            reset();
            let mut s = stack(0x20000, 65536, 0);
            FAULT.set(if fail { 1 } else { 0 });
            assert_eq!(
                native_signal::native_signal_stack_publish_result(
                    &mut s,
                    0x2f000,
                    0x4567,
                    Some(copy_to)
                ),
                if fail { -14 } else { 0 }
            );
            assert_eq!(s.ss_flags, if fail { 0 } else { 1 });
            SAVED.with(|v| {
                if !fail {
                    assert_eq!(v.borrow()[0], (0x2eff8, 0x4567u64.to_le_bytes().to_vec()))
                }
            });
        }
    }
}

#[test]
fn sigaltstack_copy_failures_and_active_replacement() {
    unsafe {
        let new = stack(0x40000, 65536, 0);
        for failure in [1, 2] {
            reset();
            let mut s = stack(0x20000, 65536, 0);
            FAULT.set(failure);
            assert_eq!(
                native_signal::sigaltstack(
                    &mut s,
                    0x70000,
                    &new as *const _ as u64,
                    0xabc0,
                    Some(copy_from),
                    Some(copy_to)
                ),
                -14
            );
            assert_eq!(s.ss_sp as u64, if failure == 1 { 0x20000 } else { 0x40000 });
        }
        reset();
        let mut s = stack(0x20000, 65536, 0);
        assert_eq!(
            native_signal::sigaltstack(
                &mut s,
                0x21000,
                &new as *const _ as u64,
                0xabc0,
                Some(copy_from),
                Some(copy_to)
            ),
            -1
        );
        assert_eq!(s.ss_sp as u64, 0x20000);
        assert!(SAVED.with(|v| v.borrow().is_empty()));
    }
}

#[cfg(native_linux_irq_work_v6_12)]
#[test]
fn real_sigreturn_repeated_and_nested_altstack_frames() {
    unsafe {
        reset();
        let mut thread = MaybeUninit::<Thread>::zeroed().assume_init();
        let mut ctx = MaybeUninit::<X86UserContext>::zeroed().assume_init();
        thread.sigstack = stack(0x20000, 65536, 0);
        for _ in 0..128 {
            let (rc, saved, outer, _) = prepare(&thread.sigstack, 0x70000, 0x08000000, 832);
            assert_eq!(rc, 0);
            assert_eq!(
                native_signal::native_signal_stack_publish_result(
                    &mut thread.sigstack,
                    outer,
                    0x4567,
                    Some(copy_to)
                ),
                0
            );
            let (rc, nested_saved, inner, _) =
                prepare(&thread.sigstack, outer - 64, 0x08000000, 832);
            assert_eq!(rc, 0);
            assert!(inner < outer - 128);
            let mut nested = frame(outer - 64, nested_saved);
            assert_eq!(returning(&mut thread, &mut ctx, &mut nested, 0), 37);
            assert_eq!(thread.sigstack.ss_flags, 1);
            let mut outer_frame = frame(0x70000, saved);
            assert_eq!(returning(&mut thread, &mut ctx, &mut outer_frame, 0), 37);
            assert_eq!(thread.sigstack.ss_flags, 0);
            assert_eq!(
                (ctx.gpr.rsp, ctx.gpr.rip, thread.sigmask.val[0]),
                (0x70000, 0x4567, 0x4444)
            );
        }
    }
}

#[test]
fn actual_sigreturn_copy_restart_trace_and_xsave_paths() {
    unsafe {
        let mut thread = MaybeUninit::<Thread>::zeroed().assume_init();
        let mut ctx = MaybeUninit::<X86UserContext>::zeroed().assume_init();
        for fault in [0, 1, 2] {
            reset();
            FAULT.set(fault);
            thread.sigstack = stack(0x20000, 65536, 1);
            thread.sigmask.val[0] = 0xaaaa;
            let fp = [0u8; 128];
            let mut f = frame(0x70000, stack(0x20000, 65536, 0));
            f.fpregs = fp.as_ptr() as *mut c_void;
            assert_eq!(
                returning(&mut thread, &mut ctx, &mut f, 128),
                if fault == 0 { 37 } else { -14 }
            );
            if fault == 1 {
                assert_eq!(thread.sigmask.val[0], 0xaaaa);
                assert_eq!(thread.sigstack.ss_flags, 1);
            }
            let events = EVENTS.with(|v| v.borrow().clone());
            if fault == 0 {
                assert_eq!(events, [4, 5, 6]);
            }
            if fault == 2 {
                assert_eq!(
                    events,
                    if cfg!(native_linux_irq_work_v6_12) {
                        vec![4, 6]
                    } else {
                        vec![4]
                    }
                );
            }
        }
        reset();
        let mut f = frame(0x70000, stack(0x20000, 65536, 0));
        f.restart = 1;
        f.num = 56;
        assert_eq!(returning(&mut thread, &mut ctx, &mut f, 0), -77);
        reset();
        let mut f = frame(0x70000, stack(0x20000, 65536, 0));
        f.regs[RTSIG_REG_RFLAGS] = 0x100;
        assert_eq!(returning(&mut thread, &mut ctx, &mut f, 0), 37);
        assert_eq!(EVENTS.with(|v| v.borrow().clone()), [1, 2, 3]);
        #[cfg(native_linux_irq_work_v6_12)]
        {
            reset();
            TAMPER.set(true);
            let mut f = frame(0x70000, stack(0x20000, 65536, 0));
            assert_eq!(returning(&mut thread, &mut ctx, &mut f, 0), 37);
            assert_eq!(f.sigrc, 999);
        }
        #[cfg(not(native_linux_irq_work_v6_12))]
        {
            reset();
            let mut f = frame(0x70000, stack(0x20000, 1234, 6));
            assert_eq!(returning(&mut thread, &mut ctx, &mut f, 0), 37);
            assert_eq!(tuple(&thread.sigstack), (0x20000, 1234, 6));
        }
    }
}
