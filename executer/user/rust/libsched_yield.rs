#![no_std]

use core::ffi::{c_char, c_int, c_long, c_ulong, c_void};
use core::mem;
use core::panic::PanicInfo;
use core::ptr;

const RTLD_NEXT: *mut c_void = (-1isize) as *mut c_void;
const SYS_CLONE: c_long = 56;
const CLONE_VM: c_long = 0x0000_0100;

type PthreadT = c_ulong;

#[repr(C)]
pub struct PthreadAttr {
    _private: [u8; 0],
}

type PthreadCreateFn = unsafe extern "C" fn(
    thread: *mut PthreadT,
    attr: *const PthreadAttr,
    start_routine: *mut c_void,
    arg: *mut c_void,
) -> c_int;

static mut ORIG_PTHREAD_CREATE: *mut c_void = ptr::null_mut();

unsafe extern "C" {
    fn dlsym(handle: *mut c_void, symbol: *const c_char) -> *mut c_void;
    fn syscall(number: c_long, ...) -> c_long;
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {}
}

#[no_mangle]
pub extern "C" fn sched_yield() -> c_int {
    0
}

#[no_mangle]
pub unsafe extern "C" fn pthread_create(
    thread: *mut PthreadT,
    attr: *const PthreadAttr,
    start_routine: *mut c_void,
    arg: *mut c_void,
) -> c_int {
    if unsafe { ORIG_PTHREAD_CREATE }.is_null() {
        unsafe {
            ORIG_PTHREAD_CREATE = dlsym(RTLD_NEXT, b"pthread_create\0".as_ptr() as *const c_char);
        }
    }

    unsafe {
        syscall(
            SYS_CLONE,
            CLONE_VM,
            start_routine,
            start_routine,
            0 as c_long,
            0 as c_long,
            0 as c_long,
        );
    }

    let orig: PthreadCreateFn = unsafe { mem::transmute(ORIG_PTHREAD_CREATE) };
    unsafe { orig(thread, attr, start_routine, arg) }
}
