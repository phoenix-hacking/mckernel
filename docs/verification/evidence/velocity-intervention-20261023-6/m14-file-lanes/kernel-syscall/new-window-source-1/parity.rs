// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code)]
use core::ffi::c_void;
use core::mem::MaybeUninit;
use abi::{CInt, CLong, CULong, SizeT, X86UserContext};
mod abi {
    pub type CInt = i32;
    pub type CLong = i64;
    pub type CULong = u64;
    pub type SizeT = usize;
    include!("ACTUAL-CONTEXT-ABI.rs.inc");
}
mod debug {
    #[repr(C)]
    pub struct Ddebug {
        pub file: *const i8,
        pub func: *const i8,
        pub fmt: *const i8,
        pub line_flags: u32,
    }
}
const EFAULT: CInt = 14;
const SYS_SWAPOUT: CInt = 801;
const SYS_LINUX_MLOCK: CInt = 802;
type Out = unsafe extern "C" fn(*const c_void, *mut c_void, SizeT, CInt) -> CInt;
type In = unsafe extern "C" fn(CInt) -> CInt;
type Forward = unsafe extern "C" fn(CInt, *mut c_void) -> CLong;
type Sys2 = unsafe extern "C" fn(CInt, CULong, CULong) -> CLong;
unsafe extern "C" {
    fn kprintf(format: *const i8, ...) -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
    fn syscall_swapout_log_bridge(a: *const c_void, b: *mut c_void, c: SizeT, d: CInt);
    fn syscall_linux_mlock_log_bridge(a: CULong, b: SizeT);
    fn fixture_body_record(kind: CInt, a: CULong, b: CULong, c: CULong, d: CLong) -> CLong;
}
include!("io_diagnostics.RUST-FRAGMENT.rs.inc");
include!("ACTUAL-SELECTED-RUST-WRAPPERS.rs.inc");
unsafe extern "C" fn do_pageout(_: *const c_void, _: *mut c_void, _: SizeT, _: CInt) -> CInt { -97 }
unsafe extern "C" fn do_pagein(_: CInt) -> CInt { -97 }
unsafe extern "C" fn syscall_policy_forward_context_bridge(_: CInt, _: *mut c_void) -> CLong { -97 }
unsafe extern "C" fn syscall_policy_do_syscall2_bridge(_: CInt, _: CULong, _: CULong) -> CLong { -97 }
// Controlled downstream providers observe the genuine wrapper boundary only.
unsafe fn swapout_body_result(a: *const c_void, b: *mut c_void, c: SizeT, d: CInt,
    nr: CInt, ctx: *mut c_void, out: Option<Out>, input: Option<In>, fwd: Option<Forward>) -> CLong {
    assert_eq!(nr, SYS_SWAPOUT);
    assert!(!ctx.is_null() && out.is_some() && input.is_some() && fwd.is_some());
    unsafe { fixture_body_record(1, a as CULong, b as CULong, c as CULong, d as CLong) }
}
unsafe fn linux_mlock_body_result(a: CULong, b: SizeT, nr: CInt, f: Option<Sys2>) -> CLong {
    assert_eq!(nr, SYS_LINUX_MLOCK);
    assert!(f.is_some());
    unsafe { fixture_body_record(2, a, b as CULong, 0, 0) }
}
#[no_mangle]
pub unsafe extern "C" fn fixture_rust_wrapper(kind: CInt, a: CULong, b: CULong,
    c: CULong, d: CInt, null_context: CInt) -> CLong {
    let mut ctx: X86UserContext = unsafe { core::mem::zeroed() };
    ctx.gpr.rdi = a;
    ctx.gpr.rsi = b;
    ctx.gpr.rdx = c;
    ctx.gpr.r10 = d as CULong;
    let pointer = if null_context != 0 { core::ptr::null_mut() } else { &mut ctx };
    unsafe { if kind == 1 { sys_swapout(801, pointer) } else { sys_linux_mlock(802, pointer) } }
}
