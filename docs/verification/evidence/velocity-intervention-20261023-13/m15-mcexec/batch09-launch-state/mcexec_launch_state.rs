// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Project launch-state/lifecycle callbacks now Rust; retain original global storage.
use super::{c_int,c_long,c_ulong,c_void,McexecMainStatePtrs};
use core::ptr::{addr_of_mut,null_mut};
#[repr(C)]
struct Rlimit { cur:c_ulong,max:c_ulong }
unsafe extern "C" {
 static mut nr_processes:c_int;
 static mut nr_threads:c_int;
 static mut mpol_threshold:c_ulong;
 static mut heap_extension:c_ulong;
 static mut straight_map_threshold:c_ulong;
 static mut stack_premap:c_long;
 static mut stack_max:c_long;
 static mut uti_thread_rank:c_int;
 static mut mcexec_flags:c_ulong;
 static mut mpol_bind_nodes:*mut u8;
 static mut enable_uti:c_int;
 static mut enable_vdso:c_int;
 static mut profile:c_int;
 static mut mpol_no_heap:c_int;
 static mut mpol_no_stack:c_int;
 static mut mpol_no_bss:c_int;
 static mut mpol_shm_premap:c_int;
 static mut no_bind_ikc_map:c_int;
 static mut straight_map:c_int;
 static mut uti_use_last_cpu:c_int;
 #[cfg(mcexec_enable_tofu)]
 static mut enable_tofu:c_int;
 static mut mcosid:c_int;static mut ischild:c_int;static mut exec_path:*mut u8;static mut altroot:*mut u8;
 static mut rlim_stack:Rlimit;static mut disable_sched_yield:c_int;static mut dev:[u8;64];
 static mut overlay_fd_lock:c_int;static mut mcexec_options:c_void;
 static mut optarg:*mut u8;static mut optind:c_int;
 static mut debug:c_int;static mut stdout:*mut c_void;static mut stderr:*mut c_void;
 #[cfg(mcexec_syscall_mod_call)]static mut __glob_argc:c_int;
 #[cfg(mcexec_syscall_mod_call)]static mut __glob_argv:*mut *mut u8;
 fn fprintf(f:*mut c_void,fmt:*const u8,...)->c_int;fn printf(fmt:*const u8,...)->c_int;fn fflush(f:*mut c_void)->c_int;
 fn getrlimit(resource:c_int,limit:*mut Rlimit)->c_int;fn setrlimit(resource:c_int,limit:*const Rlimit)->c_int;
 fn execv(path:*const u8,argv:*mut *mut u8)->c_int;
 fn unsetenv(name:*const u8)->c_int;
 fn personality(persona:c_ulong)->c_int;
 fn strerror(error:c_int)->*const u8;
 fn getopt_long(argc:c_int,argv:*mut *mut u8,opts:*const u8,longopts:*const c_void,index:*mut c_int)->c_int;
 fn pthread_spin_init(lock:*mut c_int,shared:c_int)->c_int;
 fn open(path:*const u8,flags:c_int,...)->c_int;
 fn popen(command:*const u8,mode:*const u8)->*mut c_void;fn pclose(file:*mut c_void)->c_int;
 fn prctl(option:c_int,...)->c_int;
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_main_page_size_bridge() -> c_ulong {
 super::sysconf(30) as c_ulong
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_publish_page_altroot_bridge(size:c_ulong,root:*const u8) {
 super::MCEXEC_PAGE_SIZE=size;super::MCEXEC_PAGE_MASK=!(size.wrapping_sub(1));altroot=root.cast_mut();
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_altroot_bridge() -> *const u8 {
 altroot
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_publish_exec_path_bridge(path:*mut u8) {
 if !exec_path.is_null(){super::free(exec_path);}exec_path=path;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_load_stack_rlimit_bridge(cur:*mut c_ulong,max:*mut c_ulong) -> c_int {
 if getrlimit(3,addr_of_mut!(rlim_stack))!=0 {fprintf(stderr,b"getrlimit failed\n\0".as_ptr());return 1;}
 *cur=rlim_stack.cur;*max=rlim_stack.max;
 if debug!=0 {printf(b"mcexec_main_load_stack_rlimit_bridge: rlim_stack=%ld,%ld\n\0".as_ptr(),rlim_stack.cur,rlim_stack.max);fflush(stdout);}0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_reduce_stack_setenv_bridge(value:*const u8) -> c_int {
 super::setenv(b"MCKERNEL_RLIMIT_STACK\0".as_ptr(),value,0)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_reduce_stack_setrlimit_bridge(cur:c_ulong,max:c_ulong) -> c_int {
 let limit=Rlimit{cur,max};setrlimit(3,&limit)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_reduce_stack_readlink_bridge(out:*mut u8,size:usize) -> isize {
 super::readlink(b"/proc/self/exe\0".as_ptr(),out,size)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_find_libdir_readlink_bridge(out:*mut u8,size:usize) -> isize {
 super::readlink(b"/proc/self/exe\0".as_ptr(),out,size)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_reduce_stack_execv_bridge(path:*const u8,argv:*mut *mut u8) -> c_int {
 execv(path,argv)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve1_enable_vdso_bridge() -> c_int {
 enable_vdso
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve1_rlim_cur_bridge() -> c_ulong {
 rlim_stack.cur
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve1_rlim_max_bridge() -> c_ulong {
 rlim_stack.max
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve1_stack_premap_bridge() -> c_long {
 stack_premap
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_loop_is_child_bridge() -> c_int {
 ischild
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_mcosid_bridge() -> c_int {
 mcosid
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_mcosid_bridge() -> c_int {
 mcosid
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ld_preload_enable_uti_bridge() -> c_int {
 enable_uti
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_enable_uti_bridge() -> c_int {
 enable_uti
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ld_preload_disable_sched_yield_bridge() -> c_int {
 disable_sched_yield
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_publish_args_bridge(argc:c_int,argv:*mut *mut u8) {
 #[cfg(mcexec_syscall_mod_call)] {__glob_argc=argc;__glob_argv=argv;}
 #[cfg(not(mcexec_syscall_mod_call))] {let _=(argc,argv);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_state_ptrs_bridge(state:*mut McexecMainStatePtrs) {
 *state=core::mem::zeroed();
 (*state).nr_processes=addr_of_mut!(nr_processes);
 (*state).nr_threads=addr_of_mut!(nr_threads);
 (*state).mpol_threshold=addr_of_mut!(mpol_threshold);
 (*state).heap_extension=addr_of_mut!(heap_extension);
 (*state).straight_map_threshold=addr_of_mut!(straight_map_threshold);
 (*state).stack_premap=addr_of_mut!(stack_premap);
 (*state).stack_max=addr_of_mut!(stack_max);
 (*state).uti_thread_rank=addr_of_mut!(uti_thread_rank);
 (*state).mcexec_flags=addr_of_mut!(mcexec_flags);
 (*state).mpol_bind_nodes=addr_of_mut!(mpol_bind_nodes);
 (*state).enable_uti=addr_of_mut!(enable_uti);
 (*state).enable_vdso=addr_of_mut!(enable_vdso);
 (*state).profile=addr_of_mut!(profile);
 (*state).mpol_no_heap=addr_of_mut!(mpol_no_heap);
 (*state).mpol_no_stack=addr_of_mut!(mpol_no_stack);
 (*state).mpol_no_bss=addr_of_mut!(mpol_no_bss);
 (*state).mpol_shm_premap=addr_of_mut!(mpol_shm_premap);
 (*state).no_bind_ikc_map=addr_of_mut!(no_bind_ikc_map);
 (*state).straight_map=addr_of_mut!(straight_map);
 (*state).uti_use_last_cpu=addr_of_mut!(uti_use_last_cpu);
 #[cfg(mcexec_enable_tofu)] {(*state).enable_tofu=addr_of_mut!(enable_tofu);}
 (*state).rlim_cur=addr_of_mut!(rlim_stack.cur);
 (*state).rlim_max=addr_of_mut!(rlim_stack.max);

}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_personality_bridge(argv:*mut *mut u8) -> c_int {
 let mut persona=personality(0xffffffff);
 if persona&0x400000!=0 {persona &= !0x400000;persona=personality(persona as c_ulong);}
 if debug!=0 {printf(b"mcexec_main_personality_bridge: persona=%08x\n\0".as_ptr(),persona);fflush(stdout);}
 let env=b"MCEXEC_ADDR_NO_RANDOMIZE\0".as_ptr();
 if persona&0x40000==0 {
  if !super::getenv(env).is_null() {fprintf(stderr,b"mcexec_main_personality_bridge: personality() and then execv() failed\n\0".as_ptr());fflush(stderr);return 1;}
  persona=personality((persona|0x40000) as c_ulong);
  if persona == -1 {fprintf(stderr,b"mcexec_main_personality_bridge: personality failed, persona=%08x, strerror=%s\n\0".as_ptr(),persona,strerror(*super::__errno_location()));fflush(stderr);return 1;}
  if super::setenv(env,b"1\0".as_ptr(),1)==-1 {fprintf(stderr,b"mcexec_main_personality_bridge: setenv failed\n\0".as_ptr());fflush(stderr);return 1;}
  let mut path=[0u8;4096];
  let error=super::readlink(b"/proc/self/exe\0".as_ptr(),path.as_mut_ptr(),path.len()) as c_int;
  if error == -1 {fprintf(stderr,b"mcexec_main_personality_bridge: readlink failed: %m\n\0".as_ptr());fflush(stderr);return 1;}
  if error as usize>=path.len() {core::ptr::copy_nonoverlapping(b"/proc/self/exe\0".as_ptr(),path.as_mut_ptr(),b"/proc/self/exe\0".len());}else{path[error as usize]=0;}
  let error=execv(path.as_ptr(),argv);
  if error == -1 {fprintf(stderr,b"mcexec_main_personality_bridge: execv failed, error=%d,strerror=%s\n\0".as_ptr(),error,strerror(*super::__errno_location()));fflush(stderr);return 1;}
 }
 if !super::getenv(env).is_null() && unsetenv(env)==-1 {fprintf(stderr,b"mcexec_main_personality_bridge: unsetenv failed\0".as_ptr());fflush(stderr);return 1;}
 0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_next_option_bridge(argc:c_int,argv:*mut *mut u8) -> c_int {
 getopt_long(argc,argv,b"+c:n:t:M:h:e:s:m:u:S:f:\0".as_ptr(),addr_of_mut!(mcexec_options),null_mut())
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_optarg_bridge() -> *mut u8 {
 optarg
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_optind_bridge() -> c_int {
 optind
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_publish_mcosid_bridge(id:c_int) {
 mcosid=id;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_uti_unavailable_bridge(enabled:c_int) -> c_int {
 #[cfg(not(mcexec_enable_uti))] {if enabled!=0 {fprintf(stderr,b"mcexec_main_uti_unavailable_bridge: ERROR: uti is not available when not configured with --with-syscall_intercept=<path>\n\0".as_ptr());fflush(stderr);return 1;}}
 #[cfg(mcexec_enable_uti)] {let _=enabled;}0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_overlay_lock_init_bridge() {
 pthread_spin_init(addr_of_mut!(overlay_fd_lock),0);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_dev_bridge() -> *mut u8 {
 addr_of_mut!(dev).cast()
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_dev_size_bridge() -> usize {
64
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_open_bridge(path:*const u8) -> c_int {
 open(path,2)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_publish_fd_bridge(value:c_int) {
super::MCEXEC_FD=value;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_query_buildid_bridge(target:c_int,result:*mut u8) -> c_int {
super::ioctl(target,0x112a37 as c_ulong,result)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_close_bridge(target:c_int) {
super::close(target);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_find_libdir_popen_bridge(cmd:*const u8) -> *mut c_void {
popen(cmd,b"r\0".as_ptr())
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_find_libdir_getline_bridge(line:*mut *mut u8,size:*mut usize,file:*mut c_void) -> isize {
super::getline(line,size,file)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_find_libdir_pclose_bridge(file:*mut c_void) {
pclose(file);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_find_libdir_free_bridge(line:*mut u8) {
super::free(line);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ld_preload_getenv_bridge(name:*const u8) -> *mut u8 {
super::getenv(name)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ld_preload_setenv_bridge(value:*const u8) -> c_int {
super::setenv(b"LD_PRELOAD\0".as_ptr(),value,1)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ld_preload_unsetenv_bridge() -> c_int {
unsetenv(b"MCKERNEL_LD_PRELOAD\0".as_ptr())
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ld_preload_enable_qlmpi_bridge() -> c_int {
cfg!(mcexec_enable_qlmpi) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_get_thp_disable_prctl_bridge() -> c_int {
prctl(42,0 as c_int,0 as c_int,0 as c_int,0 as c_int)
}
