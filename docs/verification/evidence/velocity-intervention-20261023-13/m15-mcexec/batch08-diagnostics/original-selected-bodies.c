void mcexec_load_too_large_interp_bridge(void)
{
	__eprintf("too large PT_INTERP segment\n");
}

void mcexec_load_cannot_read_interp_bridge(void)
{
	__eprintf("cannot read PT_INTERP segment\n");
}

void mcexec_search_file_path_too_long_bridge(const char *root,
		const char *path)
{
	__eprintf("modified path too long: %s/%s\n", root, path);
}

void mcexec_lookup_array_too_small_bridge(void)
{
	fprintf(stderr, "lookup_exec_path(): array too small?\n");
}

void mcexec_lookup_stat_error_bridge(const char *path, int error)
{
	__dprintf("lookup_exec_path(): error stat for %s: %d\n",
		  path, error);
}

void mcexec_lookup_not_found_bridge(const char *filename)
{
	fprintf(stderr,
		"lookup_exec_path(): error finding file %s\n", filename);
}

void mcexec_lookup_success_bridge(const char *path)
{
	__dprintf("lookup_exec_path(): %s\n", path);
}

void mcexec_load_desc_not_executable_bridge(const char *filename, int error)
{
	__dprintf("Error: %s is not an executable?, errno: %d\n",
		  filename, error);
}

void mcexec_load_desc_zero_length_bridge(const char *filename)
{
	__dprintf("Error: file %s is zero length\n", filename);
}

void mcexec_load_desc_open_failed_bridge(const char *filename)
{
	__dprintf("Error: Failed to open %s\n", filename);
}

void mcexec_load_desc_header_failed_bridge(const char *filename)
{
	__dprintf("Error: Failed to read header from %s\n", filename);
}

void mcexec_load_desc_shebang_read_failed_bridge(const char *filename)
{
	__dprintf("Error: reading shebang path %s\n", filename);
}

void mcexec_load_desc_open_exec_failed_bridge(const char *filename,
		int ret, int fd_value)
{
	fprintf(stderr, "Error: open_exec() fails for %s: %d (fd: %d)\n",
		filename, ret, fd_value);
}

void mcexec_load_desc_strdup_failed_bridge(void)
{
	fprintf(stderr, "WARNING: strdup(filename) failed\n");
}

void mcexec_load_desc_getcwd_failed_bridge(void)
{
	fprintf(stderr, "Error: getting current working dir pathname\n");
}

void mcexec_load_desc_alloc_exec_path_failed_bridge(void)
{
	fprintf(stderr, "Error: allocating exec_path\n");
}

void mcexec_load_desc_build_exec_path_failed_bridge(void)
{
	fprintf(stderr, "Error: building exec_path\n");
}

void mcexec_load_desc_parse_elf_failed_bridge(void)
{
	fprintf(stderr, "Error: Failed to parse ELF!\n");
}

void mcexec_load_desc_interp_not_found_bridge(const char *path)
{
	fprintf(stderr, "Error: interp not found: %s\n", path);
}

void mcexec_load_desc_interp_open_failed_bridge(const char *path)
{
	fprintf(stderr, "Error: Failed to open %s\n", path);
}

void mcexec_load_desc_parse_interp_failed_bridge(void)
{
	fprintf(stderr, "Error: Failed to parse interp!\n");
}

void mcexec_load_shebang_find_error_bridge(const char *path)
{
	__dprintf("error: finding file: %s\n", path);
}

void mcexec_load_shebang_load_error_bridge(const char *path)
{
	__dprintf("error: loading file: %s\n", path);
}

void mcexec_load_cannot_read_ehdr_bridge(void)
{
	__eprintf("Cannot read Ehdr.\n");
}

void mcexec_load_elfmag_mismatch_bridge(void)
{
	__eprintf("ELFMAG mismatched.\n");
}

void mcexec_load_phdr_failed_bridge(int index)
{
	__eprintf("Loading phdr failed (%d)\n", index);
}

void mcexec_load_pt_interp_on_interp_bridge(void)
{
	__eprintf("PT_INTERP on interp\n");
}

void mcexec_load_section_log_bridge(int index, unsigned long vaddr,
		unsigned long filesz, unsigned long offset,
		unsigned long len, int prot)
{
	__dprintf("%d: (%s) %lx, %lx, %lx, %lx, %x\n",
		  index, "PT_LOAD", vaddr, filesz, offset, len, prot);
}

void mcexec_transfer_seek_error_bridge(void)
{
	fprintf(stderr, "transfer_image(): error: seeking file position\n");
}

void mcexec_transfer_access_error_bridge(void)
{
	fprintf(stderr, "transfer_image(): error: accessing file\n");
}

void mcexec_transfer_short_error_bridge(void)
{
	fprintf(stderr, "transfer_image(): file too short?\n");
}

void mcexec_transfer_seeked_bridge(unsigned long offset,
		unsigned long size)
{
	__dprintf("seeked to %lx | size %ld\n", offset, size);
}

void mcexec_print_flat_count_bridge(long count)
{
	__dprintf("counter: %ld\n", count);
}

void mcexec_print_flat_entry_bridge(const char *entry)
{
	__dprintf("%s\n", entry);
}

void mcexec_desc_ompi_policy_log_bridge(const char *mpol)
{
	__dprintf("OMPI_MCA_plm_ple_memory_allocation_policy: %s\n",
		  mpol);
}

void mcexec_main_reduce_stack_failed_bridge(void)
{
	fprintf(stderr, "Error: Failed to reduce stack.\n");
}

void mcexec_reduce_stack_setrlimit_failed_bridge(void)
{
	__eprintf("failed to setrlimit(RLIMIT_STACK)\n");
}

void mcexec_reduce_stack_readlink_failed_bridge(void)
{
	__eprintf("Could not readlink /proc/self/exe? %m\n");
}

void mcexec_reduce_stack_execv_failed_bridge(void)
{
	__eprintf("failed to execv(myself)\n");
}

void mcexec_execve2_alloc_desc_failed_bridge(void)
{
	fprintf(stderr, "execve(): error allocating desc\n");
}

void mcexec_execve2_transfer_desc_failed_bridge(void)
{
	fprintf(stderr, "execve(): error obtaining ELF descriptor\n");
}

void mcexec_execve2_transfer_desc_ok_bridge(void)
{
	__dprintf("%s", "execve(): transfer ELF desc OK\n");
}

void mcexec_execve2_transfer_image_failed_bridge(void)
{
	fprintf(stderr, "error: transferring image\n");
}

void mcexec_execve2_image_transferred_bridge(void)
{
	__dprintf("%s", "execve(): image transferred\n");
}

void mcexec_execve2_close_exec_failed_bridge(int ret)
{
	fprintf(stderr, "error: MCEXEC_UP_CLOSE_EXEC failed with %d\n", ret);
}

void mcexec_main_flush_bridge(void)
{
	fflush(stdout);
	fflush(stderr);
}

void mcexec_flib_affinity_log_bridge(const char *old_affinity,
		const char *new_affinity)
{
	__dprintf("FLIB_AFFINITY_ON_PROCESS: %s -> %s\n",
			old_affinity, new_affinity);
}

void mcexec_execve1_load_desc_ok_bridge(const char *filename, int sections)
{
	__dprintf("execve(): load_elf_desc() for %s OK, num sections: %d\n",
			filename, sections);
}

void mcexec_execve1_transfer_alloc_failed_bridge(const char *filename)
{
	fprintf(stderr,
		"execve(): could not alloc transfer buffer for file %s\n",
		filename);
}

void mcexec_execve1_transfer_failed_bridge(const char *filename)
{
	fprintf(stderr, "execve(): error transfering ELF for file %s\n",
			filename);
}

void mcexec_execve1_transfer_ok_bridge(const char *filename)
{
	__dprintf("execve(): load_elf_desc() for %s OK\n", filename);
}

void mcexec_execve_invalid_phase_bridge(void)
{
	fprintf(stderr, "execve(): ERROR: invalid execve phase\n");
}

void mcexec_main_loop_log_syscall_bridge(int cpu, long number)
{
	__dprintf("[%d] got syscall: %ld\n", cpu, number);
}

void mcexec_main_loop_timeout_bridge(void)
{
	__dprintf("timed out.\n");
}

void mcexec_add_env_list_invalid_bridge(const char *add_string)
{
	printf("\"%s\" is not env value.\n", add_string);
}

void mcexec_main_stack_debug_bridge(long prem, long max)
{
	__dprintf("stack_premap=%ld,stack_max=%ld\n", prem, max);
}

void mcexec_main_thread_plan_error_bridge(void)
{
	fprintf(stderr, "error: nr_processes can't exceed nr. of CPUs\n");
}

void mcexec_main_load_desc_error_bridge(const char *path, int ret)
{
	fprintf(stderr, "%s: could not load program: %s\n",
		path, strerror(ret));
}

void mcexec_opendev_path_error_bridge(void)
{
	fprintf(stderr, "Error: Failed to build mcos device path.\n");
}

void mcexec_opendev_open_error_bridge(const char *path)
{
	fprintf(stderr, "Error: Failed to open %s.\n", path);
}

void mcexec_opendev_query_error_bridge(void)
{
	fprintf(stderr, "Error: IHK_OS_GET_BUILDID failed");
}

void mcexec_opendev_buildid_mismatch_bridge(const char *buildid,
		const char *query_result)
{
	fprintf(stderr,
		"Error: build-id of mcexec (%s) didn't match that of IHK (%s)\n",
		buildid, query_result);
}

void mcexec_find_libdir_readlink_failed_bridge(int error)
{
	fprintf(stderr, "readlink /proc/self/exe: %d\n", error);
}

void mcexec_find_libdir_objdump_failed_bridge(int error)
{
	fprintf(stderr, "objdump /proc/self/exe: %d\n", error);
}

void mcexec_find_libdir_rpath_not_found_bridge(int error)
{
	fprintf(stderr, "RPATH not found: %d\n", error);
}

void mcexec_ld_preload_find_failed_bridge(void)
{
	fprintf(stderr, "warning: did not set LD_PRELOAD\n");
}

void mcexec_ld_preload_line_too_long_bridge(void)
{
	fprintf(stderr, "%s: warning: LD_PRELOAD line is too long\n",
			"ld_preload_init");
}

void mcexec_ld_preload_setenv_failed_bridge(void)
{
	printf("%s: warning: failed to set LD_PRELOAD environment variable\n",
			"ld_preload_init");
}

void mcexec_ld_preload_debug_bridge(const char *envbuf)
{
	__dprintf("%s: preload library: %s\n", "ld_preload_init", envbuf);
}

void mcexec_kill_thread_not_found_bridge(unsigned long tid, int sig)
{
	printf("%s: ERROR: Thread not found (tid=%ld,sig=%d)\n",
	       "kill_thread", tid, sig);
}

void mcexec_gettid_alloc_error_bridge(void)
{
	fprintf(stderr, "__NR_gettid(): error allocating TIDs\n");
}

void mcexec_gettid_transfer_error_bridge(void)
{
	fprintf(stderr, "__NR_gettid(): error transfering TIDs\n");
}

void mcexec_swapout_unavailable_bridge(void)
{
	printf("mcexec has not been compiled with ENABLE_QLMPI\n");
}

void mcexec_linux_spawn_invalid_arg_bridge(void)
{
	fprintf(stderr, "linux_spawn(): ERROR: invalid argument \n");
}

void mcexec_linux_spawn_invalid_exec_path_bridge(void)
{
	fprintf(stderr, "linux_spawn(): ERROR: invalid exec_path \n");
}

void mcexec_linux_spawn_alloc_exec_path_failed_bridge(void)
{
	fprintf(stderr, "linux_spawn(): ERROR: failed to allocating exec_path\n");
}

void mcexec_linux_spawn_strncpy_failed_bridge(void)
{
	fprintf(stderr, "linux_spawn(): ERROR: failed to strncpy from user\n");
}

void mcexec_linux_spawn_alloc_argv_failed_bridge(int index)
{
	fprintf(stderr, "linux_spawn(): ERROR: failed to allocating argv[%d]\n",
			index);
}

void mcexec_linux_spawn_posix_spawn_failed_bridge(int rc)
{
	fprintf(stderr, "linux_spawn(): ERROR: posix_spawn returned %d\n", rc);
}

void mcexec_util_thread_missing_desc_bridge(void)
{
	printf("%s: ERROR: uti_desc not found. Add --enable-uti option to mcexec.\n",
	       "util_thread");
}

void mcexec_util_thread_desc_log_bridge(void *desc)
{
	__dprintf("%s: uti_desc=%p\n", "util_thread", desc);
}

void mcexec_util_thread_worker_tid_log_bridge(int tid)
{
	__dprintf("%s: worker tid: %d\n", "util_thread", tid);
}

void mcexec_util_thread_intercept_warning_bridge(int rc)
{
	fprintf(stderr, "%s: WARNING: syscall_intercept returned %x\n",
		"util_thread", rc);
}

void mcexec_util_thread_get_ctx_error_bridge(int error)
{
	fprintf(stderr, "%s: Error: MCEXEC_UP_UTI_GET_CTX failed (%d)\n",
		"util_thread", error);
}

void mcexec_util_thread_param_large_bridge(void)
{
	fprintf(stderr, "%s: ERROR: param is too large\n", "util_thread");
}

void mcexec_util_thread_attr_error_bridge(int error)
{
	fprintf(stderr, "%s: error: MCEXEC_UP_UTI_ATTR: %s\n",
		"util_thread", strerror(error));
}

void mcexec_util_thread_switch_failed_bridge(int rc)
{
	fprintf(stderr, "%s: ERROR switch_ctx failed (%d)\n",
		"util_thread", rc);
}

void mcexec_util_thread_switch_returned_bridge(int rc)
{
	fprintf(stderr, "%s: ERROR: Returned from switch_ctx (%d)\n",
		"util_thread", rc);
}

void mcexec_sched_setaffinity_invalid_bridge(unsigned long pid_arg)
{
	__eprintf("__NR_sched_setaffinity: invalid argument (%lx)\n",
			pid_arg);
}

void mcexec_overlay_addfd_path_too_long_bridge(void)
{
	fprintf(stderr, "%s: path too long\n", "overlay_addfd");
}

void mcexec_overlay_considering_bridge(int dirfd, const char *path)
{
	__dprintf("considering fd %d path %s\n", dirfd, path);
}

void mcexec_overlay_fd_path_truncated_bridge(int dirfd)
{
	fprintf(stderr, "%s: /proc/self/fd/%d path truncated\n",
		"overlay_path", dirfd);
}

void mcexec_overlay_readlink_fd_failed_bridge(int dirfd, int error)
{
	fprintf(stderr, "%s: readlink /proc/self/fd/%d failed: %d\n",
		"overlay_path", dirfd, error);
}

void mcexec_overlay_truncated_bridge(const char *path)
{
	fprintf(stderr, "%s: %s truncated\n", "overlay_path", path);
}

void mcexec_overlay_getcwd_failed_bridge(int error)
{
	fprintf(stderr, "%s: could not getcwd(): %d\n",
		"overlay_path", error);
}

void mcexec_overlay_glued_bridge(const char *path)
{
	__dprintf("glued to %s\n", path);
}

void mcexec_overlay_find_libdir_failed_bridge(void)
{
	fprintf(stderr, "error: failed to find library directory\n");
}

void mcexec_overlay_replaced_bridge(const char *path, const char *mapped)
{
	__dprintf("%s: %s replaced with %s\n", "overlay_path", path, mapped);
}

void mcexec_overlay_trying_bridge(const char *path, int error)
{
	__dprintf("trying %s: %d\n", path, error);
}

void mcexec_overlay_blacklisted_bridge(const char *path)
{
	__dprintf("blacklisted %s\n", path);
}

void mcexec_overlay_getdents_offset_bridge(long offset)
{
	__dprintf("offset: %ld\n", offset);
}

void mcexec_overlay_getdents_lower_failed_bridge(int error)
{
	fprintf(stderr, "%s: linux getdents failed: %d\n",
		"overlay_getdents", error);
}

void mcexec_overlay_getdents_blacklisted_bridge(const char *path)
{
	__dprintf("blacklisted: %s\n", path);
}

void mcexec_overlay_getdents_dupe_bridge(const char *name)
{
	__dprintf("dupe: %s\n", name);
}

void mcexec_overlay_getdents_offset_too_large_bridge(long offset,
		size_t mck_size, size_t linux_size)
{
	fprintf(stderr, "%s: offset (%ld) is too large (upper: %ld, lower: %ld)\n",
		"overlay_getdents", offset, mck_size, linux_size);
}

void mcexec_overlay_getdents_upper_small_bridge(void)
{
	__dprintf("upper: Result buffer is too small\n");
}

void mcexec_overlay_getdents_lower_small_bridge(void)
{
	__dprintf("lower: Result buffer is too small\n");
}
