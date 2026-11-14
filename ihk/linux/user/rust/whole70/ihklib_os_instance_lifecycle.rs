//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Public OS instance lifecycle bodies, reusing the actual Rust device-open owner.
use core::ffi::{c_int,c_uint,c_ulong};
const CREATE:c_ulong=0x112900;
const DESTROY:c_ulong=0x112901;
unsafe extern "C" {fn ioctl(fd:c_int,request:c_ulong,...)->c_int;fn close(fd:c_int)->c_int;fn usleep(usec:c_uint)->c_int;fn __errno_location()->*mut c_int;}
unsafe fn finish(fd:c_int,value:c_int)->c_int {
    // Keep baseline close condition; captured result is unaffected by close errno.
    if fd != -1 {unsafe {close(fd);}}
    value
}
#[no_mangle]
pub unsafe extern "C" fn ihk_create_os(index:c_int)->c_int {
    let fd=unsafe {super::ihklib_device_open(index)};
    if fd<0 {return unsafe {finish(fd,fd)};}
    let value=unsafe {ioctl(fd,CREATE,0 as c_int)};
    let value=if value<0 {unsafe {-*__errno_location()}}else{value};
    unsafe {finish(fd,value)}
}
#[no_mangle]
pub unsafe extern "C" fn ihk_destroy_os(dev_index:c_int,os_index:c_int)->c_int {
    let fd=unsafe {super::ihklib_device_open(dev_index)};
    if fd<0 {return unsafe {finish(fd,fd)};}
    let mut value=0;
    for _ in 0..100 {
        value=unsafe {ioctl(fd,DESTROY,os_index)};
        if value==0 {break;}
        value=unsafe {-*__errno_location()};
        if value != -16 {break;}
        // Exact existing bounded retry policy: also sleep after the 100th EBUSY.
        // Neither sleep failure nor errno after sleep replaces the captured result.
        unsafe {usleep(10000);}
    }
    unsafe {finish(fd,value)}
}
