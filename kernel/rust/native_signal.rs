// SPDX-License-Identifier: GPL-2.0-only
//! Native x86 signal-stack state and checked frame placement.

use crate::abi::{CInt, CLong, CULong, SigInfo, SigStack, SizeT, Thread, X86UserContext};
use core::ffi::c_void;
use core::mem::{offset_of, size_of, MaybeUninit};

const SS_ONSTACK: CInt = 1;
const SS_DISABLE: CInt = 2;
const SA_ONSTACK: CULong = 0x0800_0000;
const MINSIGSTKSZ: SizeT = 2048;
const UNBLOCKABLE: CULong = (1 << (9 - 1)) | (1 << (19 - 1));
const SA_NODEFER: CULong = 0x4000_0000;
// Pinned Linux arch/x86/include/asm/sighandling.h FIX_EFLAGS.
const USER_CHANGEABLE_RFLAGS: CULong = 0x50dd5;
pub(crate) type CopyFrom = unsafe extern "C" fn(*mut u8, CULong, SizeT) -> CLong;
type CopyTo = unsafe extern "C" fn(CULong, *const u8, SizeT) -> CLong;
pub(crate) type RestoreFp = unsafe extern "C" fn(CULong, CInt) -> CLong;

/// x86_64 libc ucontext prefix, mcontext, complete libc sigset reservation,
/// then the separately addressed siginfo. There is no private restart state.
#[repr(C)]
pub struct Frame {
    pub(crate) flags: CULong,
    pub(crate) link: *mut c_void,
    pub(crate) sigstack: SigStack,
    pub(crate) regs: [CULong; 23],
    pub(crate) fpregs: *mut c_void,
    pub(crate) reserve: [CULong; 8],
    pub(crate) sigmask: [CULong; 16],
    pub(crate) info: SigInfo,
}

const _: () = {
    assert!(offset_of!(Frame, sigstack) == 16);
    assert!(offset_of!(Frame, regs) == 40);
    assert!(offset_of!(Frame, fpregs) == 224);
    assert!(offset_of!(Frame, sigmask) == 296);
    assert!(offset_of!(Frame, info) == 424);
    assert!(size_of::<Frame>() == 552);
};

/// The frame is private kernel storage. Restart preparation verifies the
/// original SYSCALL instruction, then resumes through ordinary userspace
/// execution rather than dispatching a syscall recursively from sigreturn.
#[no_mangle]
pub unsafe extern "C" fn native_signal_context_prepare_result(
    regs: *const X86UserContext,
    saved_mask: CULong,
    result: CULong,
    number: CInt,
    restart: CInt,
    frame: *mut Frame,
    copy_from: Option<CopyFrom>,
) -> CLong {
    if regs.is_null() || frame.is_null() {
        return -14;
    }
    let gpr = &(*regs).gpr;
    let mut rip = gpr.rip;
    let mut rax = result;
    if restart != 0 {
        if number < 0 {
            return -22;
        }
        let Some(instruction) = rip.checked_sub(2) else {
            return -14;
        };
        let Some(copy) = copy_from else { return -14 };
        let mut opcode = [0u8; 2];
        if copy(opcode.as_mut_ptr(), instruction, opcode.len()) != 0 {
            return -14;
        }
        if opcode != [0x0f, 0x05] {
            return -22;
        }
        rip = instruction;
        rax = number as CULong;
    }
    let frame = &mut *frame;
    frame.regs = [
        gpr.r8,
        gpr.r9,
        gpr.r10,
        gpr.r11,
        gpr.r12,
        gpr.r13,
        gpr.r14,
        gpr.r15,
        gpr.rdi,
        gpr.rsi,
        gpr.rbp,
        gpr.rbx,
        gpr.rdx,
        rax,
        gpr.rcx,
        gpr.rsp,
        rip,
        gpr.rflags,
        (gpr.cs & 0xffff) | ((gpr.ss & 0xffff) << 48),
        gpr.orig_rax,
        0,
        saved_mask & !UNBLOCKABLE,
        0,
    ];
    frame.sigmask = [0; 16];
    frame.sigmask[0] = saved_mask & !UNBLOCKABLE;
    0
}

#[no_mangle]
pub extern "C" fn native_signal_action_mask_result(
    previous: CULong,
    action_mask: CULong,
    signal: CInt,
    flags: CULong,
) -> CULong {
    let self_mask = if (1..=64).contains(&signal) && flags & SA_NODEFER == 0 {
        1u64 << (signal - 1)
    } else {
        0
    };
    (previous | action_mask | self_mask) & !UNBLOCKABLE
}

/// Consume the newly selected native frame. The architecture FP provider
/// completes before normal context state is published. Validation and the
/// process-local bad-frame disposition are part of the native integration.
pub(crate) unsafe fn sigreturn(
    thread: *mut Thread,
    regs: *mut X86UserContext,
    xsave_size: CInt,
    copy_from: CopyFrom,
    restore_fp: RestoreFp,
) -> Result<CLong, CLong> {
    if thread.is_null() || regs.is_null() || (*thread).vm.is_null() {
        return Err(-14);
    }
    let mut storage = MaybeUninit::<Frame>::uninit();
    if copy_from(
        storage.as_mut_ptr().cast(),
        (*regs).gpr.rsp,
        size_of::<Frame>(),
    ) != 0
    {
        return Err(-14);
    }
    let frame = &*storage.as_ptr();
    let region = &(*(*thread).vm).region;
    let rip = frame.regs[16];
    let rsp = frame.regs[15];
    // Native x86 currently uses the canonical lower 47-bit user half. A stack
    // pointer may be the one-past-end stack top, but must remain canonical.
    if region.user_start >= region.user_end
        || rip < region.user_start
        || rip >= region.user_end
        || rip >= (1 << 47)
        || rsp < region.user_start
        || rsp > region.user_end
        || rsp >= (1 << 47)
    {
        return Err(-14);
    }
    let result = restore_fp(frame.fpregs as CULong, xsave_size);
    if result != 0 {
        return Err(result);
    }
    let gpr = &mut (*regs).gpr;
    gpr.r8 = frame.regs[0];
    gpr.r9 = frame.regs[1];
    gpr.r10 = frame.regs[2];
    gpr.r11 = frame.regs[3];
    gpr.r12 = frame.regs[4];
    gpr.r13 = frame.regs[5];
    gpr.r14 = frame.regs[6];
    gpr.r15 = frame.regs[7];
    gpr.rdi = frame.regs[8];
    gpr.rsi = frame.regs[9];
    gpr.rbp = frame.regs[10];
    gpr.rbx = frame.regs[11];
    gpr.rdx = frame.regs[12];
    gpr.rax = frame.regs[13];
    gpr.rcx = frame.regs[14];
    gpr.rsp = frame.regs[15];
    gpr.rip = frame.regs[16];
    gpr.rflags = (gpr.rflags & !USER_CHANGEABLE_RFLAGS)
        | (frame.regs[17] & USER_CHANGEABLE_RFLAGS);
    gpr.orig_rax = CULong::MAX;
    (*thread).sigmask.val[0] = frame.sigmask[0] & !UNBLOCKABLE;
    restore(&mut (*thread).sigstack, &frame.sigstack, gpr.rsp);
    Ok(gpr.rax as CLong)
}

// Pinned Linux __on_sig_stack(): a downward stack excludes its base and
// includes its top. Compute membership from SP, never a saved active bit.
pub(crate) fn on_stack(stack: &SigStack, sp: CULong) -> bool {
    stack.ss_flags & SS_DISABLE == 0
        && sp > stack.ss_sp as CULong
        && sp - stack.ss_sp as CULong <= stack.ss_size as CULong
}

pub(crate) fn snapshot(stack: &SigStack, sp: CULong) -> SigStack {
    SigStack {
        ss_sp: stack.ss_sp,
        ss_flags: if stack.ss_size == 0 || stack.ss_flags & SS_DISABLE != 0 {
            SS_DISABLE
        } else if on_stack(stack, sp) {
            SS_ONSTACK
        } else {
            0
        },
        padding: 0,
        ss_size: stack.ss_size,
    }
}

fn install(stack: &mut SigStack, new: &SigStack, sp: CULong) -> CLong {
    if on_stack(stack, sp) {
        return -1; // EPERM, including an attempt to disable the active stack.
    }
    if !matches!(new.ss_flags, 0 | SS_ONSTACK | SS_DISABLE) {
        return -22; // SS_AUTODISARM has no McKernel owner yet.
    }
    if new.ss_flags == SS_DISABLE {
        *stack = SigStack {
            ss_sp: core::ptr::null_mut(),
            ss_flags: SS_DISABLE,
            padding: 0,
            ss_size: 0,
        };
    } else {
        if new.ss_size < MINSIGSTKSZ {
            return -12;
        }
        *stack = snapshot(new, sp);
    }
    0
}

pub(crate) fn restore(stack: &mut SigStack, saved: &SigStack, sp: CULong) {
    // Linux restore_altstack ignores configuration errors. In particular, a
    // nested return must retain the stack still executing the outer handler.
    let _ = install(stack, saved, sp);
}

pub(crate) unsafe fn sigaltstack(
    stack: &mut SigStack,
    sp: CULong,
    ss: CULong,
    oss: CULong,
    copy_from: Option<CopyFrom>,
    copy_to: Option<CopyTo>,
) -> CLong {
    let mut new = MaybeUninit::<SigStack>::uninit();
    if ss != 0 {
        let Some(copy) = copy_from else { return -14 };
        if copy(new.as_mut_ptr().cast(), ss, size_of::<SigStack>()) != 0 {
            return -14;
        }
    }
    let old = snapshot(stack, sp);
    if ss != 0 {
        let result = install(stack, &*new.as_ptr(), sp);
        if result != 0 {
            return result;
        }
    }
    if oss != 0 {
        let Some(copy) = copy_to else { return -14 };
        if copy(oss, (&old as *const SigStack).cast(), size_of::<SigStack>()) != 0 {
            return -14;
        }
    }
    0
}

/// Called with kernel-owned stack/output pointers while the signal lock is
/// held. No live thread state or user memory changes before all checks pass.
#[no_mangle]
pub unsafe extern "C" fn native_signal_stack_prepare_result(
    stack: *const SigStack,
    saved: *mut SigStack,
    sp: CULong,
    flags: CULong,
    xsave_size: CInt,
    frame_size: SizeT,
    user_start: CULong,
    user_end: CULong,
    frame_out: *mut CULong,
    fpregs_out: *mut CULong,
) -> CLong {
    if stack.is_null()
        || saved.is_null()
        || frame_out.is_null()
        || fpregs_out.is_null()
        || xsave_size < 0
        || frame_size == 0
        || user_start >= user_end
    {
        return -14;
    }
    let stack = &*stack;
    let saved_stack = snapshot(stack, sp);
    let nested = on_stack(stack, sp);
    let entering = flags & SA_ONSTACK != 0 && saved_stack.ss_flags == 0;
    let top = if entering {
        (stack.ss_sp as CULong).checked_add(stack.ss_size as CULong)
    } else {
        // Both ordinary and nested handlers must preserve the interrupted
        // function's complete x86-64 red zone.
        sp.checked_sub(128)
    };
    let Some(top) = top else { return -14 };
    let Some(fpregs) = top.checked_sub(xsave_size as CULong) else {
        return -14;
    };
    let Some(frame) = fpregs.checked_sub(frame_size as CULong).map(|p| p & !15) else {
        return -14;
    };
    let Some(entry) = frame.checked_sub(8) else {
        return -14;
    };
    if entry < user_start || entry >= user_end || top > user_end {
        return -14;
    }
    if entering || nested {
        let Some(end) = (stack.ss_sp as CULong).checked_add(stack.ss_size as CULong) else {
            return -14;
        };
        if !on_stack(stack, entry) || top > end {
            return -14;
        }
    }
    saved.write(saved_stack);
    frame_out.write(frame);
    fpregs_out.write(fpregs);
    0
}

/// Finish the already-copied frame with checked user access, then commit the
/// active-stack state. A restorer-copy fault leaves that state unchanged.
#[no_mangle]
pub unsafe extern "C" fn native_signal_stack_publish_result(
    stack: *mut SigStack,
    frame: CULong,
    restorer: CULong,
    copy_to: Option<CopyTo>,
) -> CLong {
    if stack.is_null() || frame < 16 || frame & 15 != 0 {
        return -14;
    }
    let Some(copy) = copy_to else { return -14 };
    if copy(
        frame - 8,
        (&restorer as *const CULong).cast(),
        size_of::<CULong>(),
    ) != 0
    {
        return -14;
    }
    let stack = &mut *stack;
    *stack = snapshot(stack, frame - 8);
    0
}
