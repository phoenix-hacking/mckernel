#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Extract and exercise the actual patched Rust core-termination body with host stubs.
No kernel build, guest, or native workload is performed.
"""
from pathlib import Path
import hashlib, subprocess, tempfile
here = Path(__file__).resolve().parent
base = here.parent / 'M14-ARCH5-CUTOVER-1/postimage/kernel/rust/syscall_policy.rs'
private = here.parent / 'M14-ARCH5-SIGNAL-ATOMIC-PRIVATE-2'
with tempfile.TemporaryDirectory(prefix='m14-signal-body-') as td:
    t = Path(td)
    patched = t / 'policy.rs'
    subprocess.run(['patch','--silent','--output',str(patched),str(base),str(private/'SIGNAL-ATOMIC.PRIVATE.patch')],check=True)
    text = patched.read_text()
    start = text.index('#[no_mangle]\npub unsafe extern "C" fn arch_do_signal_core_terminate_result(')
    end = text.index('\n// Functional McKernel OS/apps', start)
    (t/'body.rs').write_text(text[start:end]+'\n')
    (t/'f06_signal_log_budget.rs').write_bytes((private/'f06_signal_log_budget.rs').read_bytes())
    (t/'mock.c').write_text(r'''
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
int diagnostic_count, other_count;
char last_diagnostic[512];
int kprintf(const char *format, ...) {
    va_list args; va_start(args, format);
    if (strstr(format, "mcexec_v10: signal_default") != NULL) {
        ++diagnostic_count;
        vsnprintf(last_diagnostic, sizeof last_diagnostic, format, args);
    } else { ++other_count; }
    va_end(args); return 0;
}
''')
    (t/'fixture.rs').write_text(r'''
#![allow(non_camel_case_types, dead_code, private_interfaces)]
use std::ffi::c_void;
use std::mem::size_of;
type CInt = i32; type CULong = u64;
const IHK_MC_AP_NOWAIT: CULong = 2;
const EBUSY: CInt = 16;
#[repr(C)] #[derive(Clone, Copy, Debug, PartialEq)]
struct Gpr { rip: u64, rsp: u64 }
#[repr(C)] #[derive(Clone, Copy, Debug, PartialEq)]
struct X86UserContext { gpr: Gpr, extra: u64 }
#[repr(C)] struct Thread { tid: CInt, coredump_regs: *mut c_void }
static mut ALLOC_FAIL: bool = false;
static mut DUMP_RESULT: CInt = 0;
static mut DUMP_CALLS: usize = 0;
static mut TERMINATE_STATUS: CInt = -1;
mod mem_helpers {
    use super::*;
    pub unsafe fn kmalloc_tracked(size: CInt, flags: CULong, _: *mut i8, _: CInt) -> *mut c_void {
        assert_eq!(size as usize, size_of::<X86UserContext>()); assert_eq!(flags, IHK_MC_AP_NOWAIT);
        if ALLOC_FAIL { std::ptr::null_mut() } else {
            Box::into_raw(Box::new(X86UserContext { gpr: Gpr { rip: 0, rsp: 0 }, extra: 0 })).cast()
        }
    }
}
mod string {
    use super::*;
    pub unsafe fn memcpy(dst: *mut c_void, src: *const c_void, size: usize) {
        std::ptr::copy_nonoverlapping(src.cast::<u8>(), dst.cast::<u8>(), size);
    }
}
mod f06_signal_log_budget { include!("f06_signal_log_budget.rs"); }
extern "C" { fn kprintf(fmt: *const i8, ...) -> CInt; static mut diagnostic_count: CInt;
    static mut other_count: CInt; static mut last_diagnostic: [u8; 512]; }
unsafe fn f06_signal_core_dump(_: *mut Thread, _: *mut c_void, _: CInt) -> CInt { DUMP_CALLS += 1; DUMP_RESULT }
unsafe fn f06_signal_core_terminate(status: CInt, signal: CInt) { assert_eq!(status, 0); TERMINATE_STATUS = signal; }
include!("body.rs");
unsafe fn run(t: &mut Thread, r: &mut X86UserContext, s: &std::sync::atomic::AtomicU64) {
    arch_do_signal_core_terminate_result(t, r, 11, 22, 0xabc, s);
}
#[test] fn actual_body_diagnostic_limit_reset_and_core_paths() { unsafe {
    use std::sync::atomic::{AtomicU64, Ordering};
    let state = AtomicU64::new(u64::from(u32::MAX) << 32);
    let mut regs = X86UserContext { gpr: Gpr { rip: 0x1234, rsp: 0x5678 }, extra: 99 };
    let mut thread = Thread { tid: 33, coredump_regs: std::ptr::null_mut() };
    diagnostic_count = 0; other_count = 0; DUMP_CALLS = 0; ALLOC_FAIL = false; DUMP_RESULT = 0;
    f06_signal_log_budget::f06_log_observe_pid(&state, 22);
    for _ in 0..65 {
        run(&mut thread, &mut regs, &state);
        assert!(!thread.coredump_regs.is_null());
        assert_eq!(*thread.coredump_regs.cast::<X86UserContext>(), regs);
        drop(Box::from_raw(thread.coredump_regs.cast::<X86UserContext>()));
    }
    assert_eq!({ diagnostic_count }, 64); assert_eq!({ DUMP_CALLS }, 65); assert_eq!({ TERMINATE_STATUS }, 11 | 0x80);
    let line = std::ffi::CStr::from_ptr(std::ptr::addr_of!(last_diagnostic).cast::<i8>()).to_str().unwrap();
    assert_eq!(line, "mcexec_v10: signal_default pid=22 tid=33 sig=11 rip=0x1234 sp=0x5678 si_addr=0xabc\n");
    assert_eq!(state.load(Ordering::Relaxed), (22u64 << 32) | 64);
    f06_signal_log_budget::f06_log_observe_pid(&state, 23);
    ALLOC_FAIL = true; run(&mut thread, &mut regs, &state);
    assert!(thread.coredump_regs.is_null()); assert_eq!({ diagnostic_count }, 65);
    assert_eq!({ other_count }, 1); assert_eq!({ DUMP_CALLS }, 65); assert_eq!({ TERMINATE_STATUS }, 11);
    ALLOC_FAIL = false; DUMP_RESULT = -EBUSY; run(&mut thread, &mut regs, &state);
    assert_eq!({ other_count }, 2); assert_eq!({ TERMINATE_STATUS }, 11);
    drop(Box::from_raw(thread.coredump_regs.cast::<X86UserContext>()));
    DUMP_RESULT = -5; run(&mut thread, &mut regs, &state);
    assert_eq!({ other_count }, 3); assert_eq!({ TERMINATE_STATUS }, 11);
    drop(Box::from_raw(thread.coredump_regs.cast::<X86UserContext>()));
} }
''')
    subprocess.run(['cc','-c',str(t/'mock.c'),'-o',str(t/'mock.o')],check=True)
    subprocess.run([str(Path.home()/'.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc'),'--edition=2021','--test',str(t/'fixture.rs'),'-C',f'link-arg={t / "mock.o"}','-o',str(t/'fixture')],check=True)
    subprocess.run([str(t/'fixture'),'--test-threads=1'],check=True)
    for p in (base, private/'SIGNAL-ATOMIC.PRIVATE.patch', private/'f06_signal_log_budget.rs', here/'check.py'):
        print(hashlib.sha256(p.read_bytes()).hexdigest(), p, flush=True)
