// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use super::{c_int,c_long,c_ulong,c_void,McexecThreadData,McexecUtiSwitchCtxDesc};
use super::mcexec_load_descriptor::ProgramLoadDesc;
use core::ptr::{addr_of_mut,null_mut};
#[repr(C,align(8))]
struct StatStorage { bytes:[u8;144] }
unsafe extern "C" {
 static mut debug:c_int;static mut stdout:*mut c_void;static mut stderr:*mut c_void;
 fn stat(path:*const u8,sb:*mut StatStorage)->c_int;
 fn lstat(path:*const u8,sb:*mut StatStorage)->c_int;
 fn printf(fmt:*const u8,...)->c_int;fn fprintf(f:*mut c_void,fmt:*const u8,...)->c_int;fn fflush(f:*mut c_void)->c_int;
 fn fwrite(p:*const u8,size:usize,n:usize,f:*mut c_void)->usize;
 fn mmap(p:*mut c_void,n:usize,prot:c_int,flags:c_int,fd:c_int,off:c_long)->*mut c_void;
 fn mlock(p:*const c_void,n:usize)->c_int;
 fn exit(status:c_int)->!;fn strerror(error:c_int)->*const u8;
 fn switch_ctx(fd:c_int,cmd:c_ulong,desc:*mut McexecUtiSwitchCtxDesc,lctx:*mut c_void,rctx:*mut c_void)->c_int;
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_lookup_lstat_errno_bridge(path:*const u8) -> c_int {
let mut sb:StatStorage=core::mem::zeroed();if lstat(path,addr_of_mut!(sb)) == -1 {*super::__errno_location()}else{0}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_stat_size_bridge(path:*const u8,out:*mut c_long) -> c_int {
let mut sb:StatStorage=core::mem::zeroed();
 if stat(path,addr_of_mut!(sb)) == -1 {
  if debug!=0 {printf(b"mcexec_load_desc_stat_size_bridge: Error: failed to stat %s\n\0".as_ptr(),path);fflush(stdout);}
  return *super::__errno_location();
 }
 *out=sb.bytes.as_ptr().add(48).cast::<c_long>().read();0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_stat_exists_bridge(path:*const u8) -> c_int {
let mut sb:StatStorage=core::mem::zeroed();if stat(path,addr_of_mut!(sb))<0 {-*super::__errno_location()}else{0}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_stat_errno_bridge(path:*const u8) -> c_int {
let mut sb:StatStorage=core::mem::zeroed();if stat(path,addr_of_mut!(sb)) == -1 {*super::__errno_location()}else{0}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_lstat_is_symlink_bridge(path:*const u8,out:*mut c_int) -> c_int {
let mut sb:StatStorage=core::mem::zeroed();if lstat(path,addr_of_mut!(sb)) == -1 {return -*super::__errno_location();}
 let mode=sb.bytes.as_ptr().add(24).cast::<u32>().read();*out=((mode&0o170000)==0o120000) as c_int;0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_readlink_bridge(path:*const u8,out:*mut u8,size:usize) -> isize {
super::readlink(path,out,size)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_find_libdir_bridge(out:*mut u8,size:usize) -> c_int {
super::mcexec_find_libdir_body(out,size) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dma_mmap_bridge() -> *mut c_void {
mmap(null_mut(),4096,3,0x22,-1,0)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dma_mlock_bridge(buf:*mut c_void) -> c_int {
mlock(buf,4096)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_create_ppd_bridge() -> c_int {
super::ioctl(super::MCEXEC_FD,0x30a0290e as c_ulong,core::ptr::null::<c_void>())
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dma_mmap_failed_bridge() -> ! {
if debug!=0 {printf(b"mcexec_dma_mmap_failed_bridge: error: allocating DMA area\n\0".as_ptr());fflush(stdout);}exit(1)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dma_mlock_failed_bridge() -> ! {
if debug!=0 {printf(b"mcexec_dma_mlock_failed_bridge: ERROR: locking dma_buf\n\0".as_ptr());fflush(stdout);}exit(1)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_create_ppd_failed_bridge() -> ! {
super::perror(b"creating mcctrl per-process structure\0".as_ptr());super::close(super::MCEXEC_FD);exit(1)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_prepare_image_failed_bridge() {
super::perror(b"prepare\0".as_ptr());super::close(super::MCEXEC_FD);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_start_image_failed_bridge() {
super::perror(b"exec\0".as_ptr());super::close(super::MCEXEC_FD);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_worker_threads_failed_bridge(error:c_int) {
fprintf(stderr,b"main: Error: creating worker threads: %s\n\0".as_ptr(),strerror(-error));super::close(super::MCEXEC_FD);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_flib_affinity_alloc_failed_bridge() -> ! {
fprintf(stderr,b"error: allocating memory for FLIB_AFFINITY_ON_PROCESS\n\0".as_ptr());exit(1)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_invalid_option_bridge(opt:c_int,argv:*mut *mut u8) -> ! {
match opt {
 99=>{fprintf(stderr,b"error: -c: invalid target CPU\n\0".as_ptr());},
 110=>{fprintf(stderr,b"error: -n: invalid number of processes\n\0".as_ptr());},
 116=>{fprintf(stderr,b"error: -t: invalid number of threads\n\0".as_ptr());},
 _=>{super::print_usage(argv);}
 }exit(1)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_atobytes_set_errno_bridge(value:c_int) {
*super::__errno_location()=value;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_print_usage_add_envs_bridge() -> c_int {
1 // ADD_ENVS_OPTION is always defined by current source.
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_print_usage_write_bridge(line:*const u8,len:usize) {
fwrite(line,1,len,stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_kill_thread_bridge(tid:c_ulong,sig:c_ulong,thread:*mut McexecThreadData) {
super::mcexec_kill_thread_body(tid,sig,thread.cast());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_sched_setaffinity_util_bridge(thread:*mut McexecThreadData,rp:c_ulong,tid:c_int,pattr:c_ulong,info:c_ulong,desc:c_ulong) -> c_long {
super::mcexec_util_thread_body(thread,rp,tid,pattr,info,desc)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_switch_ctx_bridge(desc:*mut McexecUtiSwitchCtxDesc,lctx:*mut c_void,rctx:*mut c_void) -> c_int {
switch_ctx(super::MCEXEC_FD,0x30a02921 as c_ulong,desc,lctx,rctx)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_debug_mlock_bridge(addr:c_ulong,len:c_ulong) -> c_long {
mlock(addr as *const c_void,len as usize) as c_long
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_debug_mlock_log_bridge(addr:c_ulong,len:c_ulong) {
printf(b"linux mlock(%p, %ld)\n\0".as_ptr(),addr as *mut c_void,len);printf(b"str(%p)=%s\0".as_ptr(),addr as *mut c_void,addr as *const u8);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_mpol_log_bridge(desc:*const ProgramLoadDesc) {
if debug!=0 {printf(b"mcexec_desc_mpol_log_bridge: mpol_mode: %d, mpol_nodemask: %ld\n\0".as_ptr(),(*desc).mpol_mode,(*desc).mpol_nodemask[0]);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_reduce_stack_newval_overflow_bridge() {
fprintf(stderr,b"mcexec_reduce_stack_newval_overflow_bridge: snprintf(%s):buffer overflow\n\0".as_ptr(),b"MCKERNEL_RLIMIT_STACK\0".as_ptr());fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_reduce_stack_setenv_failed_bridge() {
fprintf(stderr,b"mcexec_reduce_stack_setenv_failed_bridge: failed to setenv(%s)\n\0".as_ptr(),b"MCKERNEL_RLIMIT_STACK\0".as_ptr());fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_stack_parse_failed_bridge(rc:c_int) {
fprintf(stderr,b"Error: Failed to parse %s %d\n\0".as_ptr(),b"MCKERNEL_RLIMIT_STACK\0".as_ptr(),rc);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_realloc_failed_bridge(size:c_ulong) {
fprintf(stderr,b"mcexec_load_realloc_failed_bridge: realloc(%#lx) failed\n\0".as_ptr(),size as c_long);fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_sections_bridge(count:c_int) {
if debug!=0 {printf(b"mcexec_load_desc_sections_bridge: # of sections: %d\n\0".as_ptr(),count);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_print_desc_intro_bridge(desc:*const c_void) {
if debug!=0 {printf(b"print_desc: Desc (%p)\n\0".as_ptr(),desc);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_print_desc_main_bridge(cpu:c_int,pid:c_int,entry:c_ulong,rprocess:c_ulong) {
if debug!=0 {printf(b"print_desc: CPU = %d, pid = %d, entry = %lx, rp = %lx\n\0".as_ptr(),cpu,pid,entry,rprocess);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_print_desc_section_bridge(vaddr:c_ulong,len:c_ulong,pa:c_ulong,filesz:c_ulong) {
if debug!=0 {printf(b"print_desc: vaddr: %lx, mem_len: %lx, remote_pa: %lx, files: %lx\n\0".as_ptr(),vaddr,len,pa,filesz);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_upper_bridge(mck:c_int,ret:c_int,count:u32) {
if debug!=0 {printf(b"mcexec_overlay_getdents_upper_bridge: getdents from upper: mck_ret: %d, ret: %d, count: %d\n\0".as_ptr(),mck,ret,count);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_lower_bridge(linux:c_int,ret:c_int,count:u32) {
if debug!=0 {printf(b"mcexec_overlay_getdents_lower_bridge: getdents from lower: linux_ret: %d, ret: %d, count: %d\n\0".as_ptr(),linux,ret,count);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_mck_size_log_bridge(size:usize,offset:c_long,len:c_int,count:u32) {
if debug!=0 {printf(b"mcexec_overlay_getdents_mck_size_log_bridge: mck_dirents_size: %ld, offset: %ld, mck_len: %d, count: %d\n\0".as_ptr(),size,offset,len,count);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_linux_size_log_bridge(size:usize,offset:c_long,len:c_int,count:u32) {
if debug!=0 {printf(b"mcexec_overlay_getdents_linux_size_log_bridge: linux_dirents_size: %ld, offset: %ld, linux_len: %d, count: %d\n\0".as_ptr(),size,offset,len,count);fflush(stdout);}
}

#[cfg(mcexec_residual_fixture)]
#[no_mangle]
pub unsafe extern "C" fn mcexec_residual_fixture_abi(out:*mut usize) {
 let values=[core::mem::size_of::<StatStorage>(),core::mem::align_of::<StatStorage>(),24,48];core::ptr::copy_nonoverlapping(values.as_ptr(),out,4);
}
