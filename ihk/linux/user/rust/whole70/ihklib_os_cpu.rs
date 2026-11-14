//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Selected x86_64 public OS CPU API bodies; exact request/error/FD ordering.
use core::ffi::{c_int,c_ulong};
use super::IhkCpuReq;
const MAX_CPUS:c_int=1024;
const ASSIGN:c_ulong=0x112a22;
const RELEASE:c_ulong=0x112a23;
const QUERY:c_ulong=0x112a26;
const COUNT:c_ulong=0x112a38;
unsafe extern "C" {fn ioctl(fd:c_int,request:c_ulong,...)->c_int;fn close(fd:c_int)->c_int;fn __errno_location()->*mut c_int;}
unsafe fn finish(fd:c_int,value:c_int)->c_int {
    // Exact original cleanup, including negative open errors other than -1.
    if fd != -1 {unsafe {close(fd);}}
    value
}
unsafe fn change(index:c_int,cpus:*mut c_int,count:c_int,request:c_ulong)->c_int {
    let value=unsafe {super::ihklib_mcstat::readable(index)};
    if value!=0 {return value;}
    if count<0 || count>MAX_CPUS {return -22;}
    if count!=0 && cpus.is_null() {return -14;}
    if count==0 {return 0;}
    let mut storage=core::mem::MaybeUninit::<IhkCpuReq>::zeroed();
    let req=storage.as_mut_ptr();
    unsafe {core::ptr::addr_of_mut!((*req).cpus).write(cpus);core::ptr::addr_of_mut!((*req).num_cpus).write(count);}
    let fd=unsafe {super::ihklib_mcstat::ihklib_os_open(index)};
    if fd<0 {return unsafe {finish(fd,fd)};}
    let value=unsafe {ioctl(fd,request,req)};
    let value=if value!=0 {unsafe {-*__errno_location()}}else{value};
    unsafe {finish(fd,value)}
}
#[no_mangle]
pub unsafe extern "C" fn ihk_os_assign_cpu(index:c_int,cpus:*mut c_int,count:c_int)->c_int {unsafe {change(index,cpus,count,ASSIGN)}}
#[no_mangle]
pub unsafe extern "C" fn ihk_os_release_cpu(index:c_int,cpus:*mut c_int,count:c_int)->c_int {unsafe {change(index,cpus,count,RELEASE)}}
#[no_mangle]
pub unsafe extern "C" fn ihk_os_get_num_assigned_cpus(index:c_int)->c_int {
    let fd=unsafe {super::ihklib_mcstat::ihklib_os_open(index)};
    if fd<0 {return unsafe {finish(fd,fd)};}
    // Unlike query_cpu's COUNT failure, this public API returns raw negative ioctl.
    let value=unsafe {ioctl(fd,COUNT)};
    unsafe {finish(fd,value)}
}
#[no_mangle]
pub unsafe extern "C" fn ihk_os_query_cpu(index:c_int,cpus:*mut c_int,count:c_int)->c_int {
    let value=unsafe {super::ihklib_mcstat::readable(index)};
    if value!=0 {return value;}
    if count<0 || count>MAX_CPUS {return -22;}
    if count!=0 && cpus.is_null() {return -14;}
    let fd=unsafe {super::ihklib_mcstat::ihklib_os_open(index)};
    if fd<0 {return unsafe {finish(fd,fd)};}
    let actual=unsafe {ioctl(fd,COUNT)};
    if actual<0 {let value=unsafe {-*__errno_location()};return unsafe {finish(fd,value)};}
    if actual!=count {return unsafe {finish(fd,-22)};}
    if count==0 {return unsafe {finish(fd,0)};}
    let mut storage=core::mem::MaybeUninit::<IhkCpuReq>::zeroed();let req=storage.as_mut_ptr();
    unsafe {core::ptr::addr_of_mut!((*req).cpus).write(cpus);core::ptr::addr_of_mut!((*req).num_cpus).write(count);}
    let value=unsafe {ioctl(fd,QUERY,req)};
    let value=if value!=0 {unsafe {-*__errno_location()}}else{value};
    unsafe {finish(fd,value)}
}
#[cfg(ihklib_os_cpu_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_os_cpu_req_size()->usize {core::mem::size_of::<IhkCpuReq>()}
#[cfg(ihklib_os_cpu_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_os_cpu_req_count_offset()->usize {core::mem::offset_of!(IhkCpuReq,num_cpus)}
