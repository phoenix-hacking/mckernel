// SPDX-License-Identifier: GPL-2.0-only
//! Native x86 signal-stack state and checked frame placement.

use crate::abi::{CInt, CLong, CULong, SigStack, SizeT};
use core::mem::{size_of, MaybeUninit};

const SS_ONSTACK: CInt = 1;
const SS_DISABLE: CInt = 2;
const SA_ONSTACK: CULong = 0x0800_0000;
const MINSIGSTKSZ: SizeT = 2048;
type CopyFrom = unsafe extern "C" fn(*mut u8, CULong, SizeT) -> CLong;
type CopyTo = unsafe extern "C" fn(CULong, *const u8, SizeT) -> CLong;

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
