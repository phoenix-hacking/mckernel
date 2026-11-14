// SPDX-License-Identifier: GPL-2.0-only
//! Exact-instruction recovery for selected native no-fault operations.

use crate::abi::{CInt, CLong, X86UserContext};
use core::arch::global_asm;

global_asm!(
    r#"
    .pushsection .text
    .p2align 4
    .global native_user_read_u32_checked
    .type native_user_read_u32_checked,@function
native_user_read_u32_checked:
    .global native_user_read_u32_fault
native_user_read_u32_fault:
    movl (%rdi), %eax
    movl %eax, (%rsi)
    xorl %eax, %eax
    .global native_user_read_u32_recover
native_user_read_u32_recover:
    ret
    .size native_user_read_u32_checked, .-native_user_read_u32_checked

    .p2align 4
    .global native_xrstor_checked
    .type native_xrstor_checked,@function
native_xrstor_checked:
    movq %rsi, %rax
    movq %rsi, %rdx
    shrq $32, %rdx
    .global native_xrstor_fault
native_xrstor_fault:
    xrstor (%rdi)
    xorl %eax, %eax
    .global native_xrstor_recover
native_xrstor_recover:
    ret
    .size native_xrstor_checked, .-native_xrstor_checked
    .popsection
"#,
    options(att_syntax)
);

extern "C" {
    fn native_user_read_u32_fault();
    fn native_user_read_u32_recover();
    fn native_xrstor_fault();
    fn native_xrstor_recover();
}

/// The caller supplies the kernel-owned, saved interrupt frame. Only the
/// source-load and restore instruction above have recoverable faults. In
/// particular the load helper's kernel output store has no recovery entry.
#[no_mangle]
pub unsafe extern "C" fn native_fault_fixup(regs: *mut X86UserContext, trap: CInt) -> CInt {
    if regs.is_null() || !matches!(trap, 13 | 14) {
        return 0;
    }
    let gpr = &mut (*regs).gpr;
    if gpr.cs & 3 != 0 {
        return 0;
    }
    let recovery = if gpr.rip == native_user_read_u32_fault as *const () as u64 {
        native_user_read_u32_recover as *const () as u64
    } else if gpr.rip == native_xrstor_fault as *const () as u64 {
        native_xrstor_recover as *const () as u64
    } else {
        return 0;
    };
    gpr.rax = (-14 as CLong) as u64;
    gpr.rip = recovery;
    1
}
