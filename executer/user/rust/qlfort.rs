#![no_std]

use core::ffi::{c_char, c_int, c_void};

const RTLD_NEXT: *mut c_void = !0usize as *mut c_void;

static mut MCK_QL_ARGC: *mut c_int = core::ptr::null_mut();
static mut MCK_QL_ARGV: *mut *mut *mut c_char = core::ptr::null_mut();
static mut INTEL_IARGC: Option<unsafe extern "C" fn() -> c_int> = None;
static mut INTEL_GETARG: Option<unsafe extern "C" fn(*mut c_int, *mut c_char, c_int, c_int)> = None;
static mut GFORTRAN_IARGC: Option<unsafe extern "C" fn() -> c_int> = None;
static mut GFORTRAN_GETARG: Option<unsafe extern "C" fn(*mut c_int, *mut c_char, c_int)> = None;
static mut DL_INIT_FLAG: c_int = 0;

unsafe extern "C" {
    fn dlsym(handle: *mut c_void, symbol: *const c_char) -> *mut c_void;
    fn memset(s: *mut c_void, c: c_int, n: usize) -> *mut c_void;
    fn strlen(s: *const c_char) -> usize;
    fn strncpy(dest: *mut c_char, src: *const c_char, n: usize) -> *mut c_char;
}

unsafe fn symbol(name: &'static [u8]) -> *mut c_void {
    unsafe { dlsym(RTLD_NEXT, name.as_ptr().cast()) }
}

unsafe fn init() {
    if unsafe { DL_INIT_FLAG } != 0 {
        return;
    }

    unsafe {
        MCK_QL_ARGC = symbol(b"mck_ql_argc\0").cast();
        MCK_QL_ARGV = symbol(b"mck_ql_argv\0").cast();
        INTEL_IARGC = core::mem::transmute(symbol(b"for_iargc\0"));
        INTEL_GETARG = core::mem::transmute(symbol(b"for_getarg\0"));
        GFORTRAN_IARGC = core::mem::transmute(symbol(b"_gfortran_iargc\0"));
        GFORTRAN_GETARG = core::mem::transmute(symbol(b"_gfortran_getarg_i4\0"));
        DL_INIT_FLAG = 1;
    }
}

unsafe fn ql_argv_available() -> bool {
    unsafe { !MCK_QL_ARGC.is_null() && !MCK_QL_ARGV.is_null() && !(*MCK_QL_ARGV).is_null() }
}

unsafe fn copy_ql_arg(n: c_int, arg: *mut c_char, arg_len: c_int) {
    if arg.is_null() || arg_len <= 0 {
        return;
    }

    unsafe {
        memset(arg.cast(), b' ' as c_int, arg_len as usize);
    }

    if unsafe { !ql_argv_available() || n < 0 || n > *MCK_QL_ARGC } {
        return;
    }

    let argv = unsafe { *MCK_QL_ARGV };
    let src = unsafe { *argv.add(n as usize) };
    if src.is_null() {
        return;
    }

    let mut len = unsafe { strlen(src) };
    if len > arg_len as usize {
        len = arg_len as usize;
    }
    unsafe {
        strncpy(arg, src, len);
    }
}

#[no_mangle]
pub unsafe extern "C" fn _gfortran_iargc() -> c_int {
    unsafe {
        init();
        if ql_argv_available() {
            return *MCK_QL_ARGC - 1;
        }
        if let Some(f) = GFORTRAN_IARGC {
            return f();
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn _gfortran_getarg_i4(n: *mut c_int, arg: *mut c_char, arg_len: c_int) {
    unsafe {
        init();
        if ql_argv_available() {
            copy_ql_arg(*n, arg, arg_len);
            return;
        }
        if let Some(f) = GFORTRAN_GETARG {
            f(n, arg, arg_len);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn for_iargc() -> c_int {
    unsafe {
        init();
        if ql_argv_available() {
            return *MCK_QL_ARGC - 1;
        }
        if let Some(f) = INTEL_IARGC {
            return f();
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn for_getarg(n: *mut c_int, arg: *mut c_char, dmy1: c_int, arg_len: c_int) {
    unsafe {
        init();
        if ql_argv_available() {
            copy_ql_arg(*n, arg, arg_len);
            return;
        }
        if let Some(f) = INTEL_GETARG {
            f(n, arg, dmy1, arg_len);
        }
    }
}
