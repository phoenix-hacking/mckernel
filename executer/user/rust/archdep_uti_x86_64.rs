#![no_std]

use core::arch::asm;
use core::ffi::c_long;

#[no_mangle]
pub unsafe extern "C" fn uti_syscall6(
    syscall_number: c_long,
    arg0: c_long,
    arg1: c_long,
    arg2: c_long,
    arg3: c_long,
    arg4: c_long,
    arg5: c_long,
) -> c_long {
    let ret: c_long;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") syscall_number => ret,
            in("rdi") arg0,
            in("rsi") arg1,
            in("rdx") arg2,
            in("r10") arg3,
            in("r8") arg4,
            in("r9") arg5,
            lateout("rcx") _,
            lateout("r11") _,
            options(nostack),
        );
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn uti_syscall3(
    syscall_number: c_long,
    arg0: c_long,
    arg1: c_long,
    arg2: c_long,
) -> c_long {
    let ret: c_long;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") syscall_number => ret,
            in("rdi") arg0,
            in("rsi") arg1,
            in("rdx") arg2,
            lateout("rcx") _,
            lateout("r11") _,
            options(nostack),
        );
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn uti_syscall1(syscall_number: c_long, arg0: c_long) -> c_long {
    let ret: c_long;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") syscall_number => ret,
            in("rdi") arg0,
            lateout("rcx") _,
            lateout("r11") _,
            options(nostack),
        );
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn uti_syscall0(syscall_number: c_long) -> c_long {
    let ret: c_long;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") syscall_number => ret,
            lateout("rcx") _,
            lateout("r11") _,
            options(nostack),
        );
    }
    ret
}
