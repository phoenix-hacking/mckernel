/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
extern int debug;
#define __dprintf(format,args...) do {if(debug){printf("%s: " format,__func__,##args);fflush(stdout);}} while(0)
#define __eprintf(format,args...) do {fprintf(stderr,"%s: " format,__func__,##args);fflush(stderr);} while(0)
void mcexec_load_too_large_interp_bridge(void);
void mcexec_load_cannot_read_interp_bridge(void);
void mcexec_search_file_path_too_long_bridge(const char *root,
		const char *path);
void mcexec_lookup_array_too_small_bridge(void);
void mcexec_lookup_stat_error_bridge(const char *path, int error);
void mcexec_lookup_not_found_bridge(const char *filename);
void mcexec_lookup_success_bridge(const char *path);
void mcexec_load_desc_not_executable_bridge(const char *filename, int error);
void mcexec_load_desc_zero_length_bridge(const char *filename);
void mcexec_load_desc_open_failed_bridge(const char *filename);
void mcexec_load_desc_header_failed_bridge(const char *filename);
void mcexec_load_desc_shebang_read_failed_bridge(const char *filename);
void mcexec_load_desc_open_exec_failed_bridge(const char *filename,
		int ret, int fd_value);
void mcexec_load_desc_strdup_failed_bridge(void);
void mcexec_load_desc_getcwd_failed_bridge(void);
void mcexec_load_desc_alloc_exec_path_failed_bridge(void);
void mcexec_load_desc_build_exec_path_failed_bridge(void);
void mcexec_load_desc_parse_elf_failed_bridge(void);
void mcexec_load_desc_interp_not_found_bridge(const char *path);
void mcexec_load_desc_interp_open_failed_bridge(const char *path);
void mcexec_load_desc_parse_interp_failed_bridge(void);
void mcexec_load_shebang_find_error_bridge(const char *path);
void mcexec_load_shebang_load_error_bridge(const char *path);
void mcexec_load_cannot_read_ehdr_bridge(void);
void mcexec_load_elfmag_mismatch_bridge(void);
void mcexec_load_phdr_failed_bridge(int index);
void mcexec_load_pt_interp_on_interp_bridge(void);
void mcexec_load_section_log_bridge(int index, unsigned long vaddr,
		unsigned long filesz, unsigned long offset,
		unsigned long len, int prot);
void mcexec_transfer_seek_error_bridge(void);
void mcexec_transfer_access_error_bridge(void);
void mcexec_transfer_short_error_bridge(void);
void mcexec_transfer_seeked_bridge(unsigned long offset,
		unsigned long size);
void mcexec_print_flat_count_bridge(long count);
void mcexec_print_flat_entry_bridge(const char *entry);
void mcexec_desc_ompi_policy_log_bridge(const char *mpol);
void mcexec_main_reduce_stack_failed_bridge(void);
void mcexec_reduce_stack_setrlimit_failed_bridge(void);
void mcexec_reduce_stack_readlink_failed_bridge(void);
void mcexec_reduce_stack_execv_failed_bridge(void);
void mcexec_execve2_alloc_desc_failed_bridge(void);
void mcexec_execve2_transfer_desc_failed_bridge(void);
void mcexec_execve2_transfer_desc_ok_bridge(void);
void mcexec_execve2_transfer_image_failed_bridge(void);
void mcexec_execve2_image_transferred_bridge(void);
void mcexec_execve2_close_exec_failed_bridge(int ret);
void mcexec_main_flush_bridge(void);
void mcexec_flib_affinity_log_bridge(const char *old_affinity,
		const char *new_affinity);
void mcexec_execve1_load_desc_ok_bridge(const char *filename, int sections);
void mcexec_execve1_transfer_alloc_failed_bridge(const char *filename);
void mcexec_execve1_transfer_failed_bridge(const char *filename);
void mcexec_execve1_transfer_ok_bridge(const char *filename);
void mcexec_execve_invalid_phase_bridge(void);
void mcexec_main_loop_log_syscall_bridge(int cpu, long number);
void mcexec_main_loop_timeout_bridge(void);
void mcexec_add_env_list_invalid_bridge(const char *add_string);
void mcexec_main_stack_debug_bridge(long prem, long max);
void mcexec_main_thread_plan_error_bridge(void);
void mcexec_main_load_desc_error_bridge(const char *path, int ret);
void mcexec_opendev_path_error_bridge(void);
void mcexec_opendev_open_error_bridge(const char *path);
void mcexec_opendev_query_error_bridge(void);
void mcexec_opendev_buildid_mismatch_bridge(const char *buildid,
		const char *query_result);
void mcexec_find_libdir_readlink_failed_bridge(int error);
void mcexec_find_libdir_objdump_failed_bridge(int error);
void mcexec_find_libdir_rpath_not_found_bridge(int error);
void mcexec_ld_preload_find_failed_bridge(void);
void mcexec_ld_preload_line_too_long_bridge(void);
void mcexec_ld_preload_setenv_failed_bridge(void);
void mcexec_ld_preload_debug_bridge(const char *envbuf);
void mcexec_kill_thread_not_found_bridge(unsigned long tid, int sig);
void mcexec_gettid_alloc_error_bridge(void);
void mcexec_gettid_transfer_error_bridge(void);
void mcexec_swapout_unavailable_bridge(void);
void mcexec_linux_spawn_invalid_arg_bridge(void);
void mcexec_linux_spawn_invalid_exec_path_bridge(void);
void mcexec_linux_spawn_alloc_exec_path_failed_bridge(void);
void mcexec_linux_spawn_strncpy_failed_bridge(void);
void mcexec_linux_spawn_alloc_argv_failed_bridge(int index);
void mcexec_linux_spawn_posix_spawn_failed_bridge(int rc);
void mcexec_util_thread_missing_desc_bridge(void);
void mcexec_util_thread_desc_log_bridge(void *desc);
void mcexec_util_thread_worker_tid_log_bridge(int tid);
void mcexec_util_thread_intercept_warning_bridge(int rc);
void mcexec_util_thread_get_ctx_error_bridge(int error);
void mcexec_util_thread_param_large_bridge(void);
void mcexec_util_thread_attr_error_bridge(int error);
void mcexec_util_thread_switch_failed_bridge(int rc);
void mcexec_util_thread_switch_returned_bridge(int rc);
void mcexec_sched_setaffinity_invalid_bridge(unsigned long pid_arg);
void mcexec_overlay_addfd_path_too_long_bridge(void);
void mcexec_overlay_considering_bridge(int dirfd, const char *path);
void mcexec_overlay_fd_path_truncated_bridge(int dirfd);
void mcexec_overlay_readlink_fd_failed_bridge(int dirfd, int error);
void mcexec_overlay_truncated_bridge(const char *path);
void mcexec_overlay_getcwd_failed_bridge(int error);
void mcexec_overlay_glued_bridge(const char *path);
void mcexec_overlay_find_libdir_failed_bridge(void);
void mcexec_overlay_replaced_bridge(const char *path, const char *mapped);
void mcexec_overlay_trying_bridge(const char *path, int error);
void mcexec_overlay_blacklisted_bridge(const char *path);
void mcexec_overlay_getdents_offset_bridge(long offset);
void mcexec_overlay_getdents_lower_failed_bridge(int error);
void mcexec_overlay_getdents_blacklisted_bridge(const char *path);
void mcexec_overlay_getdents_dupe_bridge(const char *name);
void mcexec_overlay_getdents_offset_too_large_bridge(long offset,
		size_t mck_size, size_t linux_size);
void mcexec_overlay_getdents_upper_small_bridge(void);
void mcexec_overlay_getdents_lower_small_bridge(void);
