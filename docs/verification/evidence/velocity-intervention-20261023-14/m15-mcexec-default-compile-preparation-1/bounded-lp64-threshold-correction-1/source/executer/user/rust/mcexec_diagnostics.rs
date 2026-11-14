// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Ports only actual project diagnostics; formatting remains libc functionality.
use super::{c_int,c_long,c_ulong,c_void};
unsafe extern "C" {
 static mut debug:c_int;static mut stdout:*mut c_void;static mut stderr:*mut c_void;
 fn printf(fmt:*const u8,...)->c_int;
 fn fprintf(stream:*mut c_void,fmt:*const u8,...)->c_int;
 fn fflush(stream:*mut c_void)->c_int;
 fn strerror(error:c_int)->*const u8;
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_load_too_large_interp_bridge() {
 fprintf(stderr,b"mcexec_load_too_large_interp_bridge: too large PT_INTERP segment\n\0".as_ptr());fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_cannot_read_interp_bridge() {
 fprintf(stderr,b"mcexec_load_cannot_read_interp_bridge: cannot read PT_INTERP segment\n\0".as_ptr());fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_search_file_path_too_long_bridge(root:*const u8,path:*const u8) {
 fprintf(stderr,b"mcexec_search_file_path_too_long_bridge: modified path too long: %s/%s\n\0".as_ptr(),root,path);fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_lookup_array_too_small_bridge() {
 fprintf(stderr,b"lookup_exec_path(): array too small?\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_lookup_stat_error_bridge(path:*const u8,error:c_int) {
 if debug!=0 {printf(b"mcexec_lookup_stat_error_bridge: lookup_exec_path(): error stat for %s: %d\n\0".as_ptr(),path,error);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_lookup_not_found_bridge(filename:*const u8) {
 fprintf(stderr,b"lookup_exec_path(): error finding file %s\n\0".as_ptr(),filename);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_lookup_success_bridge(path:*const u8) {
 if debug!=0 {printf(b"mcexec_lookup_success_bridge: lookup_exec_path(): %s\n\0".as_ptr(),path);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_not_executable_bridge(filename:*const u8,error:c_int) {
 if debug!=0 {printf(b"mcexec_load_desc_not_executable_bridge: Error: %s is not an executable?, errno: %d\n\0".as_ptr(),filename,error);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_zero_length_bridge(filename:*const u8) {
 if debug!=0 {printf(b"mcexec_load_desc_zero_length_bridge: Error: file %s is zero length\n\0".as_ptr(),filename);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_open_failed_bridge(filename:*const u8) {
 if debug!=0 {printf(b"mcexec_load_desc_open_failed_bridge: Error: Failed to open %s\n\0".as_ptr(),filename);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_header_failed_bridge(filename:*const u8) {
 if debug!=0 {printf(b"mcexec_load_desc_header_failed_bridge: Error: Failed to read header from %s\n\0".as_ptr(),filename);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_shebang_read_failed_bridge(filename:*const u8) {
 if debug!=0 {printf(b"mcexec_load_desc_shebang_read_failed_bridge: Error: reading shebang path %s\n\0".as_ptr(),filename);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_open_exec_failed_bridge(filename:*const u8,ret:c_int,fd_value:c_int) {
 fprintf(stderr,b"Error: open_exec() fails for %s: %d (fd: %d)\n\0".as_ptr(),filename,ret,fd_value);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_strdup_failed_bridge() {
 fprintf(stderr,b"WARNING: strdup(filename) failed\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_getcwd_failed_bridge() {
 fprintf(stderr,b"Error: getting current working dir pathname\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_alloc_exec_path_failed_bridge() {
 fprintf(stderr,b"Error: allocating exec_path\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_build_exec_path_failed_bridge() {
 fprintf(stderr,b"Error: building exec_path\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_parse_elf_failed_bridge() {
 fprintf(stderr,b"Error: Failed to parse ELF!\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_interp_not_found_bridge(path:*const u8) {
 fprintf(stderr,b"Error: interp not found: %s\n\0".as_ptr(),path);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_interp_open_failed_bridge(path:*const u8) {
 fprintf(stderr,b"Error: Failed to open %s\n\0".as_ptr(),path);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_desc_parse_interp_failed_bridge() {
 fprintf(stderr,b"Error: Failed to parse interp!\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_shebang_find_error_bridge(path:*const u8) {
 if debug!=0 {printf(b"mcexec_load_shebang_find_error_bridge: error: finding file: %s\n\0".as_ptr(),path);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_shebang_load_error_bridge(path:*const u8) {
 if debug!=0 {printf(b"mcexec_load_shebang_load_error_bridge: error: loading file: %s\n\0".as_ptr(),path);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_cannot_read_ehdr_bridge() {
 fprintf(stderr,b"mcexec_load_cannot_read_ehdr_bridge: Cannot read Ehdr.\n\0".as_ptr());fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_elfmag_mismatch_bridge() {
 fprintf(stderr,b"mcexec_load_elfmag_mismatch_bridge: ELFMAG mismatched.\n\0".as_ptr());fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_phdr_failed_bridge(index:c_int) {
 fprintf(stderr,b"mcexec_load_phdr_failed_bridge: Loading phdr failed (%d)\n\0".as_ptr(),index);fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_pt_interp_on_interp_bridge() {
 fprintf(stderr,b"mcexec_load_pt_interp_on_interp_bridge: PT_INTERP on interp\n\0".as_ptr());fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_section_log_bridge(index:c_int,vaddr:c_ulong,filesz:c_ulong,offset:c_ulong,len:c_ulong,prot:c_int) {
 if debug!=0 {printf(b"mcexec_load_section_log_bridge: %d: (%s) %lx, %lx, %lx, %lx, %x\n\0".as_ptr(),index,b"PT_LOAD\0".as_ptr(),vaddr,filesz,offset,len,prot);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_transfer_seek_error_bridge() {
 fprintf(stderr,b"transfer_image(): error: seeking file position\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_transfer_access_error_bridge() {
 fprintf(stderr,b"transfer_image(): error: accessing file\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_transfer_short_error_bridge() {
 fprintf(stderr,b"transfer_image(): file too short?\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_transfer_seeked_bridge(offset:c_ulong,size:c_ulong) {
 if debug!=0 {printf(b"mcexec_transfer_seeked_bridge: seeked to %lx | size %ld\n\0".as_ptr(),offset,size);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_print_flat_count_bridge(count:c_long) {
 if debug!=0 {printf(b"mcexec_print_flat_count_bridge: counter: %ld\n\0".as_ptr(),count);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_print_flat_entry_bridge(entry:*const u8) {
 if debug!=0 {printf(b"mcexec_print_flat_entry_bridge: %s\n\0".as_ptr(),entry);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_ompi_policy_log_bridge(mpol:*const u8) {
 if debug!=0 {printf(b"mcexec_desc_ompi_policy_log_bridge: OMPI_MCA_plm_ple_memory_allocation_policy: %s\n\0".as_ptr(),mpol);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_reduce_stack_failed_bridge() {
 fprintf(stderr,b"Error: Failed to reduce stack.\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_reduce_stack_setrlimit_failed_bridge() {
 fprintf(stderr,b"mcexec_reduce_stack_setrlimit_failed_bridge: failed to setrlimit(RLIMIT_STACK)\n\0".as_ptr());fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_reduce_stack_readlink_failed_bridge() {
 fprintf(stderr,b"mcexec_reduce_stack_readlink_failed_bridge: Could not readlink /proc/self/exe? %m\n\0".as_ptr());fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_reduce_stack_execv_failed_bridge() {
 fprintf(stderr,b"mcexec_reduce_stack_execv_failed_bridge: failed to execv(myself)\n\0".as_ptr());fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve2_alloc_desc_failed_bridge() {
 fprintf(stderr,b"execve(): error allocating desc\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve2_transfer_desc_failed_bridge() {
 fprintf(stderr,b"execve(): error obtaining ELF descriptor\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve2_transfer_desc_ok_bridge() {
 if debug!=0 {printf(b"mcexec_execve2_transfer_desc_ok_bridge: %s\0".as_ptr(),b"execve(): transfer ELF desc OK\n\0".as_ptr());fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve2_transfer_image_failed_bridge() {
 fprintf(stderr,b"error: transferring image\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve2_image_transferred_bridge() {
 if debug!=0 {printf(b"mcexec_execve2_image_transferred_bridge: %s\0".as_ptr(),b"execve(): image transferred\n\0".as_ptr());fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve2_close_exec_failed_bridge(ret:c_int) {
 fprintf(stderr,b"error: MCEXEC_UP_CLOSE_EXEC failed with %d\n\0".as_ptr(),ret);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_flush_bridge() {
 fflush(stdout);
 fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_flib_affinity_log_bridge(old_affinity:*const u8,new_affinity:*const u8) {
 if debug!=0 {printf(b"mcexec_flib_affinity_log_bridge: FLIB_AFFINITY_ON_PROCESS: %s -> %s\n\0".as_ptr(),old_affinity,new_affinity);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve1_load_desc_ok_bridge(filename:*const u8,sections:c_int) {
 if debug!=0 {printf(b"mcexec_execve1_load_desc_ok_bridge: execve(): load_elf_desc() for %s OK, num sections: %d\n\0".as_ptr(),filename,sections);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve1_transfer_alloc_failed_bridge(filename:*const u8) {
 fprintf(stderr,b"execve(): could not alloc transfer buffer for file %s\n\0".as_ptr(),filename);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve1_transfer_failed_bridge(filename:*const u8) {
 fprintf(stderr,b"execve(): error transfering ELF for file %s\n\0".as_ptr(),filename);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve1_transfer_ok_bridge(filename:*const u8) {
 if debug!=0 {printf(b"mcexec_execve1_transfer_ok_bridge: execve(): load_elf_desc() for %s OK\n\0".as_ptr(),filename);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve_invalid_phase_bridge() {
 fprintf(stderr,b"execve(): ERROR: invalid execve phase\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_loop_log_syscall_bridge(cpu:c_int,number:c_long) {
 if debug!=0 {printf(b"mcexec_main_loop_log_syscall_bridge: [%d] got syscall: %ld\n\0".as_ptr(),cpu,number);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_loop_timeout_bridge() {
 if debug!=0 {printf(b"mcexec_main_loop_timeout_bridge: timed out.\n\0".as_ptr());fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_add_env_list_invalid_bridge(add_string:*const u8) {
 printf(b"\"%s\" is not env value.\n\0".as_ptr(),add_string);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_stack_debug_bridge(prem:c_long,max:c_long) {
 if debug!=0 {printf(b"mcexec_main_stack_debug_bridge: stack_premap=%ld,stack_max=%ld\n\0".as_ptr(),prem,max);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_thread_plan_error_bridge() {
 fprintf(stderr,b"error: nr_processes can't exceed nr. of CPUs\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_load_desc_error_bridge(path:*const u8,ret:c_int) {
 fprintf(stderr,b"%s: could not load program: %s\n\0".as_ptr(),path,strerror(ret));
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_path_error_bridge() {
 fprintf(stderr,b"Error: Failed to build mcos device path.\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_open_error_bridge(path:*const u8) {
 fprintf(stderr,b"Error: Failed to open %s.\n\0".as_ptr(),path);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_query_error_bridge() {
 fprintf(stderr,b"Error: IHK_OS_GET_BUILDID failed\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_buildid_mismatch_bridge(buildid:*const u8,query_result:*const u8) {
 fprintf(stderr,b"Error: build-id of mcexec (%s) didn't match that of IHK (%s)\n\0".as_ptr(),buildid,query_result);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_find_libdir_readlink_failed_bridge(error:c_int) {
 fprintf(stderr,b"readlink /proc/self/exe: %d\n\0".as_ptr(),error);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_find_libdir_objdump_failed_bridge(error:c_int) {
 fprintf(stderr,b"objdump /proc/self/exe: %d\n\0".as_ptr(),error);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_find_libdir_rpath_not_found_bridge(error:c_int) {
 fprintf(stderr,b"RPATH not found: %d\n\0".as_ptr(),error);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ld_preload_find_failed_bridge() {
 fprintf(stderr,b"warning: did not set LD_PRELOAD\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ld_preload_line_too_long_bridge() {
 fprintf(stderr,b"%s: warning: LD_PRELOAD line is too long\n\0".as_ptr(),b"ld_preload_init\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ld_preload_setenv_failed_bridge() {
 printf(b"%s: warning: failed to set LD_PRELOAD environment variable\n\0".as_ptr(),b"ld_preload_init\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ld_preload_debug_bridge(envbuf:*const u8) {
 if debug!=0 {printf(b"mcexec_ld_preload_debug_bridge: %s: preload library: %s\n\0".as_ptr(),b"ld_preload_init\0".as_ptr(),envbuf);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_kill_thread_not_found_bridge(tid:c_ulong,sig:c_int) {
 printf(b"%s: ERROR: Thread not found (tid=%ld,sig=%d)\n\0".as_ptr(),b"kill_thread\0".as_ptr(),tid,sig);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_gettid_alloc_error_bridge() {
 fprintf(stderr,b"__NR_gettid(): error allocating TIDs\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_gettid_transfer_error_bridge() {
 fprintf(stderr,b"__NR_gettid(): error transfering TIDs\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_swapout_unavailable_bridge() {
 printf(b"mcexec has not been compiled with ENABLE_QLMPI\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_linux_spawn_invalid_arg_bridge() {
 fprintf(stderr,b"linux_spawn(): ERROR: invalid argument \n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_linux_spawn_invalid_exec_path_bridge() {
 fprintf(stderr,b"linux_spawn(): ERROR: invalid exec_path \n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_linux_spawn_alloc_exec_path_failed_bridge() {
 fprintf(stderr,b"linux_spawn(): ERROR: failed to allocating exec_path\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_linux_spawn_strncpy_failed_bridge() {
 fprintf(stderr,b"linux_spawn(): ERROR: failed to strncpy from user\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_linux_spawn_alloc_argv_failed_bridge(index:c_int) {
 fprintf(stderr,b"linux_spawn(): ERROR: failed to allocating argv[%d]\n\0".as_ptr(),index);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_linux_spawn_posix_spawn_failed_bridge(rc:c_int) {
 fprintf(stderr,b"linux_spawn(): ERROR: posix_spawn returned %d\n\0".as_ptr(),rc);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_missing_desc_bridge() {
 printf(b"%s: ERROR: uti_desc not found. Add --enable-uti option to mcexec.\n\0".as_ptr(),b"util_thread\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_desc_log_bridge(desc:*mut c_void) {
 if debug!=0 {printf(b"mcexec_util_thread_desc_log_bridge: %s: uti_desc=%p\n\0".as_ptr(),b"util_thread\0".as_ptr(),desc);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_worker_tid_log_bridge(tid:c_int) {
 if debug!=0 {printf(b"mcexec_util_thread_worker_tid_log_bridge: %s: worker tid: %d\n\0".as_ptr(),b"util_thread\0".as_ptr(),tid);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_intercept_warning_bridge(rc:c_int) {
 fprintf(stderr,b"%s: WARNING: syscall_intercept returned %x\n\0".as_ptr(),b"util_thread\0".as_ptr(),rc);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_get_ctx_error_bridge(error:c_int) {
 fprintf(stderr,b"%s: Error: MCEXEC_UP_UTI_GET_CTX failed (%d)\n\0".as_ptr(),b"util_thread\0".as_ptr(),error);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_param_large_bridge() {
 fprintf(stderr,b"%s: ERROR: param is too large\n\0".as_ptr(),b"util_thread\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_attr_error_bridge(error:c_int) {
 fprintf(stderr,b"%s: error: MCEXEC_UP_UTI_ATTR: %s\n\0".as_ptr(),b"util_thread\0".as_ptr(),strerror(error));
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_switch_failed_bridge(rc:c_int) {
 fprintf(stderr,b"%s: ERROR switch_ctx failed (%d)\n\0".as_ptr(),b"util_thread\0".as_ptr(),rc);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_switch_returned_bridge(rc:c_int) {
 fprintf(stderr,b"%s: ERROR: Returned from switch_ctx (%d)\n\0".as_ptr(),b"util_thread\0".as_ptr(),rc);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_sched_setaffinity_invalid_bridge(pid_arg:c_ulong) {
 fprintf(stderr,b"mcexec_sched_setaffinity_invalid_bridge: __NR_sched_setaffinity: invalid argument (%lx)\n\0".as_ptr(),pid_arg);fflush(stderr);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_addfd_path_too_long_bridge() {
 fprintf(stderr,b"%s: path too long\n\0".as_ptr(),b"overlay_addfd\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_considering_bridge(dirfd:c_int,path:*const u8) {
 if debug!=0 {printf(b"mcexec_overlay_considering_bridge: considering fd %d path %s\n\0".as_ptr(),dirfd,path);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_fd_path_truncated_bridge(dirfd:c_int) {
 fprintf(stderr,b"%s: /proc/self/fd/%d path truncated\n\0".as_ptr(),b"overlay_path\0".as_ptr(),dirfd);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_readlink_fd_failed_bridge(dirfd:c_int,error:c_int) {
 fprintf(stderr,b"%s: readlink /proc/self/fd/%d failed: %d\n\0".as_ptr(),b"overlay_path\0".as_ptr(),dirfd,error);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_truncated_bridge(path:*const u8) {
 fprintf(stderr,b"%s: %s truncated\n\0".as_ptr(),b"overlay_path\0".as_ptr(),path);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getcwd_failed_bridge(error:c_int) {
 fprintf(stderr,b"%s: could not getcwd(): %d\n\0".as_ptr(),b"overlay_path\0".as_ptr(),error);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_glued_bridge(path:*const u8) {
 if debug!=0 {printf(b"mcexec_overlay_glued_bridge: glued to %s\n\0".as_ptr(),path);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_find_libdir_failed_bridge() {
 fprintf(stderr,b"error: failed to find library directory\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_replaced_bridge(path:*const u8,mapped:*const u8) {
 if debug!=0 {printf(b"mcexec_overlay_replaced_bridge: %s: %s replaced with %s\n\0".as_ptr(),b"overlay_path\0".as_ptr(),path,mapped);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_trying_bridge(path:*const u8,error:c_int) {
 if debug!=0 {printf(b"mcexec_overlay_trying_bridge: trying %s: %d\n\0".as_ptr(),path,error);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_blacklisted_bridge(path:*const u8) {
 if debug!=0 {printf(b"mcexec_overlay_blacklisted_bridge: blacklisted %s\n\0".as_ptr(),path);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_offset_bridge(offset:c_long) {
 if debug!=0 {printf(b"mcexec_overlay_getdents_offset_bridge: offset: %ld\n\0".as_ptr(),offset);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_lower_failed_bridge(error:c_int) {
 fprintf(stderr,b"%s: linux getdents failed: %d\n\0".as_ptr(),b"overlay_getdents\0".as_ptr(),error);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_blacklisted_bridge(path:*const u8) {
 if debug!=0 {printf(b"mcexec_overlay_getdents_blacklisted_bridge: blacklisted: %s\n\0".as_ptr(),path);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_dupe_bridge(name:*const u8) {
 if debug!=0 {printf(b"mcexec_overlay_getdents_dupe_bridge: dupe: %s\n\0".as_ptr(),name);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_offset_too_large_bridge(offset:c_long,mck_size:usize,linux_size:usize) {
 fprintf(stderr,b"%s: offset (%ld) is too large (upper: %ld, lower: %ld)\n\0".as_ptr(),b"overlay_getdents\0".as_ptr(),offset,mck_size,linux_size);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_upper_small_bridge() {
 if debug!=0 {printf(b"mcexec_overlay_getdents_upper_small_bridge: upper: Result buffer is too small\n\0".as_ptr());fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_lower_small_bridge() {
 if debug!=0 {printf(b"mcexec_overlay_getdents_lower_small_bridge: lower: Result buffer is too small\n\0".as_ptr());fflush(stdout);}
}
