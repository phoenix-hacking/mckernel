// SPDX-License-Identifier: GPL-2.0
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Source preparation only: no runtime release. Linux x86-64 syscall ABI.
#![no_std]
#![no_main]
#[cfg(not(all(target_os = "linux", target_arch = "x86_64", target_pointer_width = "64")))]
compile_error!("Linux x86-64 LP64 only");

use core::arch::{asm, global_asm};
use core::panic::PanicInfo;

// Review boundary: preserve the kernel's initial stack before aligning for the
// SysV Rust entry call. There is no libc, loader or std initialization first.
global_asm!(r#"
    .section .text
    .global _start
    .type _start,@function
_start:
    xor ebp, ebp
    mov rdi, rsp
    and rsp, -16
    call app_entry
    ud2
    .size _start, .-_start
    .global exec_reset_restorer
    .type exec_reset_restorer,@function
exec_reset_restorer:
    mov eax, 15
    syscall
    ud2
    .size exec_reset_restorer, .-exec_reset_restorer
"#);

unsafe extern "C" { fn exec_reset_restorer(); }

#[repr(C)]
struct Action { handler: usize, flags: usize, restorer: usize, mask: u64 }
#[repr(C)]
struct Stack { pointer: usize, flags: i32, padding: i32, size: usize }
#[repr(C, align(16))]
struct AltBytes([u8; 65536]);
static mut ALT: AltBytes = AltBytes([0; 65536]);
const MASK: u64 = (1 << (10 - 1)) | (1 << (12 - 1));
const AFTER: &[u8] = b"--after-exec\0";

unsafe fn syscall4(number: usize, a: usize, b: usize, c: usize, d: usize) -> isize {
    let result: isize;
    asm!("syscall", inlateout("rax") number as isize => result,
         in("rdi") a, in("rsi") b, in("rdx") c, in("r10") d,
         lateout("rcx") _, lateout("r11") _, options(nostack));
    result
}
fn exit(code: usize) -> ! {
    unsafe { syscall4(231, code, 0, 0, 0); asm!("ud2", options(noreturn)); }
}
fn output(bytes: &[u8]) {
    let mut offset = 0;
    while offset < bytes.len() {
        let count = unsafe { syscall4(1, 1, bytes.as_ptr().add(offset) as usize, bytes.len() - offset, 0) };
        if count == -4 { continue; }
        if count <= 0 || count as usize > bytes.len() - offset { exit(102); }
        offset += count as usize;
    }
}
fn fail() -> ! {
    // Failure emits no success-shaped record. Exact stderr is also required.
    let bytes = b"exec-signal-reset failed\n";
    unsafe { syscall4(1, 2, bytes.as_ptr() as usize, bytes.len(), 0); }
    exit(101)
}
#[panic_handler]
fn panic(_: &PanicInfo<'_>) -> ! { fail() }
extern "C" fn caught(_: i32) { fail(); }

unsafe fn action(signal: usize, new: *const Action, old: *mut Action) {
    if syscall4(13, signal, new as usize, old as usize, 8) != 0 { fail(); }
}
unsafe fn handler(signal: usize) -> usize {
    let mut old = Action { handler: 0, flags: 0, restorer: 0, mask: 0 };
    action(signal, core::ptr::null(), &mut old);
    old.handler
}
unsafe fn mask() -> u64 {
    let mut old = 0u64;
    if syscall4(14, 2, 0, &mut old as *mut u64 as usize, 8) != 0 { fail(); }
    old
}
unsafe fn stack() -> Stack {
    let mut old = Stack { pointer: 0, flags: 0, padding: 0, size: 0 };
    if syscall4(131, 0, &mut old as *mut Stack as usize, 0, 0) != 0 { fail(); }
    old
}
unsafe fn equals(pointer: *const u8, expected: &[u8]) -> bool {
    for (i, value) in expected.iter().enumerate() {
        if pointer.add(i).read() != *value { return false; }
    }
    true
}

#[no_mangle]
unsafe extern "C" fn app_entry(initial: *const usize) -> ! {
    // initial points to argc, argv[], NULL, envp[], NULL, auxv on x86-64.
    let argc = initial.read();
    if argc != 1 && argc != 2 { fail(); }
    let path = initial.add(1).read() as *const u8;
    if path.is_null() || path.read() != b'/' { fail(); }
    let mut end = 0;
    while end < 4096 && path.add(end).read() != 0 { end += 1; }
    if end == 4096 { fail(); }
    if initial.add(argc + 1).read() != 0 { fail(); }
    if argc == 2 {
        let phase = initial.add(2).read() as *const u8;
        if phase.is_null() || !equals(phase, AFTER) { fail(); }
        // These queries are the first signal operations in the new image.
        // No std runtime or libc has installed an alternate stack or handler.
        let caught_now = handler(10);
        let ignored_now = handler(12);
        let default_now = handler(28);
        let mask_now = mask();
        let alt_now = stack();
        if caught_now != 0 || ignored_now != 1 || default_now != 0
            || mask_now != MASK || alt_now.flags != 2
            || alt_now.pointer != 0 || alt_now.size != 0 { fail(); }
        output(b"exec-reset after caught=default ignored=ignored default=default mask=2560 alt=disabled sp=0 size=0\n");
        exit(37);
    }

    if syscall4(14, 2, &MASK as *const u64 as usize, 0, 8) != 0 { fail(); }
    let catch = Action { handler: caught as *const () as usize, flags: 0x04000000,
                         restorer: exec_reset_restorer as *const () as usize, mask: 0 };
    let ignore = Action { handler: 1, flags: 0, restorer: 0, mask: 0 };
    let default = Action { handler: 0, flags: 0, restorer: 0, mask: 0 };
    action(10, &catch, core::ptr::null_mut());
    action(12, &ignore, core::ptr::null_mut());
    action(28, &default, core::ptr::null_mut());
    let alt = Stack { pointer: core::ptr::addr_of_mut!(ALT) as usize,
                      flags: 0, padding: 0, size: 65536 };
    if syscall4(131, &alt as *const Stack as usize, 0, 0, 0) != 0 { fail(); }
    let alt_now = stack();
    if handler(10) != catch.handler || handler(12) != 1 || handler(28) != 0
        || mask() != MASK || alt_now.pointer != alt.pointer
        || alt_now.flags != 0 || alt_now.size != alt.size { fail(); }
    output(b"exec-reset before caught=installed ignored=ignored default=default mask=2560 alt=enabled size=65536\n");
    let argv = [path, AFTER.as_ptr(), core::ptr::null()];
    let env = [core::ptr::null::<u8>()];
    // Real execve syscall. Every return, including ENOSYS, is failure.
    syscall4(59, path as usize, argv.as_ptr() as usize, env.as_ptr() as usize, 0);
    fail()
}
