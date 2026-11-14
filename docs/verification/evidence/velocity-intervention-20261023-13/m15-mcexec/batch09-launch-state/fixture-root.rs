// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
use core::ffi::{c_int,c_long,c_ulong,c_void};
#[repr(C)]
struct McexecMainStatePtrs {
    nr_processes: *mut c_int,
    nr_threads: *mut c_int,
    mpol_threshold: *mut c_ulong,
    heap_extension: *mut c_ulong,
    straight_map_threshold: *mut c_ulong,
    stack_premap: *mut c_long,
    stack_max: *mut c_long,
    uti_thread_rank: *mut c_int,
    mcexec_flags: *mut c_ulong,
    mpol_bind_nodes: *mut *mut u8,
    enable_uti: *mut c_int,
    enable_vdso: *mut c_int,
    profile: *mut c_int,
    mpol_no_heap: *mut c_int,
    mpol_no_stack: *mut c_int,
    mpol_no_bss: *mut c_int,
    mpol_shm_premap: *mut c_int,
    no_bind_ikc_map: *mut c_int,
    straight_map: *mut c_int,
    uti_use_last_cpu: *mut c_int,
    enable_tofu: *mut c_int,
    rlim_cur: *mut c_ulong,
    rlim_max: *mut c_ulong,
}
unsafe extern "C" {
 #[link_name="fd"]static mut MCEXEC_FD:c_int;
 #[link_name="page_size"]static mut MCEXEC_PAGE_SIZE:c_ulong;
 #[link_name="page_mask"]static mut MCEXEC_PAGE_MASK:c_ulong;
 fn __errno_location()->*mut c_int;fn sysconf(n:c_int)->c_long;
 fn free(p:*mut u8);fn getenv(n:*const u8)->*mut u8;
 fn setenv(n:*const u8,v:*const u8,replace:c_int)->c_int;
 fn readlink(p:*const u8,out:*mut u8,n:usize)->isize;
 fn getline(line:*mut *mut u8,size:*mut usize,file:*mut c_void)->isize;
 fn ioctl(fd:c_int,r:c_ulong,...)->c_int;
 fn close(fd:c_int)->c_int;
}
#[path="mcexec_launch_state.rs"]mod mcexec_launch_state;
#[no_mangle]
pub unsafe extern "C" fn mcexec_launch_fixture_abi(out:*mut usize)->usize {
 let values=[core::mem::size_of::<McexecMainStatePtrs>(),core::mem::align_of::<McexecMainStatePtrs>(),
core::mem::offset_of!(McexecMainStatePtrs,nr_processes),
core::mem::offset_of!(McexecMainStatePtrs,nr_threads),
core::mem::offset_of!(McexecMainStatePtrs,mpol_threshold),
core::mem::offset_of!(McexecMainStatePtrs,heap_extension),
core::mem::offset_of!(McexecMainStatePtrs,straight_map_threshold),
core::mem::offset_of!(McexecMainStatePtrs,stack_premap),
core::mem::offset_of!(McexecMainStatePtrs,stack_max),
core::mem::offset_of!(McexecMainStatePtrs,uti_thread_rank),
core::mem::offset_of!(McexecMainStatePtrs,mcexec_flags),
core::mem::offset_of!(McexecMainStatePtrs,mpol_bind_nodes),
core::mem::offset_of!(McexecMainStatePtrs,enable_uti),
core::mem::offset_of!(McexecMainStatePtrs,enable_vdso),
core::mem::offset_of!(McexecMainStatePtrs,profile),
core::mem::offset_of!(McexecMainStatePtrs,mpol_no_heap),
core::mem::offset_of!(McexecMainStatePtrs,mpol_no_stack),
core::mem::offset_of!(McexecMainStatePtrs,mpol_no_bss),
core::mem::offset_of!(McexecMainStatePtrs,mpol_shm_premap),
core::mem::offset_of!(McexecMainStatePtrs,no_bind_ikc_map),
core::mem::offset_of!(McexecMainStatePtrs,straight_map),
core::mem::offset_of!(McexecMainStatePtrs,uti_use_last_cpu),
core::mem::offset_of!(McexecMainStatePtrs,enable_tofu),
core::mem::offset_of!(McexecMainStatePtrs,rlim_cur),
core::mem::offset_of!(McexecMainStatePtrs,rlim_max),
 ];core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());values.len()
}
#[panic_handler]
fn panic(_: &core::panic::PanicInfo)->! {loop{}}
