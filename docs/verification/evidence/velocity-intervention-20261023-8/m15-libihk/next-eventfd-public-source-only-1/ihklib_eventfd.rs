//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Exact original public event registration ABI. Existing device_open is reused,
//! not redefined: actual HOST production Rust provider already exports it.
use core::ffi::{c_int,c_uint,c_ulong};
#[repr(C)]
struct EventfdDesc {fd:c_int,kind:c_int}
const _:()={assert!(core::mem::size_of::<EventfdDesc>()==8);assert!(core::mem::offset_of!(EventfdDesc,kind)==4);};
unsafe extern "C" {
    fn ihklib_os_open(index:c_int)->c_int;
    fn eventfd(initval:c_uint,flags:c_int)->c_int;
    fn ioctl(fd:c_int,request:c_ulong,...)->c_int;
    fn close(fd:c_int)->c_int;
    fn __errno_location()->*mut c_int;
}
#[no_mangle]
pub unsafe extern "C" fn ihk_os_get_eventfd(index:c_int,kind:c_int)->c_int {
    let mut storage=core::mem::MaybeUninit::<EventfdDesc>::zeroed();
    let desc=storage.as_mut_ptr();
    let fd=unsafe {ihklib_os_open(index)};
    let result=if fd<0 {fd} else if kind!=0&&kind!=2&&kind!=101 {-22} else {
        unsafe {
            core::ptr::addr_of_mut!((*desc).fd).write(eventfd(0,0));
            core::ptr::addr_of_mut!((*desc).kind).write(kind);
        }
        let rc=unsafe {ioctl(fd,0x112a15 as c_ulong,desc)};
        if rc!=0 {unsafe {-*__errno_location()}} else {unsafe {(*desc).fd}}
    };
    // Capture errno before close. Preserve original fd!=-1 cleanup, even if
    // os_open returns another negative errno; no invented valid descriptor.
    if fd != -1 {unsafe {close(fd);}}
    // Original C leaves the created eventfd open on registration failure.
    // Preserve that parity here; a separate ownership repair is not selected.
    result
}
#[cfg(ihklib_eventfd_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_eventfd_desc_size()->usize {core::mem::size_of::<EventfdDesc>()}
#[cfg(ihklib_eventfd_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_eventfd_type_offset()->usize {core::mem::offset_of!(EventfdDesc,kind)}
