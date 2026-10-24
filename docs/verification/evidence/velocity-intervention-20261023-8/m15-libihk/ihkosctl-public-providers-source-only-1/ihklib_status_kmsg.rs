//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Private actual public API bodies; preserve open-before-validation and error contract.
use core::ffi::{c_char,c_int,c_ulong};
unsafe extern "C" {fn ioctl(fd:c_int,request:c_ulong,...)->c_int;fn close(fd:c_int)->c_int;fn __errno_location()->*mut c_int;}
unsafe fn finish(fd:c_int,result:c_int)->c_int {if fd != -1 {unsafe {close(fd);}}result}
#[no_mangle]
pub unsafe extern "C" fn ihk_os_get_status(index:c_int)->c_int {
 let fd=unsafe {super::ihklib_mcstat::ihklib_os_open(index)};
 if fd<0 {return unsafe {finish(fd,fd)};}
 let value=unsafe {ioctl(fd,0x112a14 as c_ulong)};
 // Negative STATUS results pass through directly; original C does not map errno here.
 let result=if value<0 {value}else{match value {0|1=>0,2|3|4=>1,5=>2,8=>3,9=>4,10=>5,6=>6,7=>7,_=>-22}};
 unsafe {finish(fd,result)}
}
#[no_mangle]
pub unsafe extern "C" fn ihk_os_kmsg(index:c_int,buffer:*mut c_char,size:isize)->c_int {
 let fd=unsafe {super::ihklib_mcstat::ihklib_os_open(index)};
 if fd<0 {return unsafe {finish(fd,fd)};}
 if size!=((4<<20)-4096) {return unsafe {finish(fd,-22)};}
 if buffer.is_null(){return unsafe {finish(fd,-14)};}
 let value=unsafe {ioctl(fd,0x112a20 as c_ulong,buffer as c_ulong)};
 let result=if value<0 {unsafe {-*__errno_location()}}else{value};
 unsafe {finish(fd,result)}
}
