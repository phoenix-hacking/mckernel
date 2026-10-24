int mcexec_lookup_lstat_errno_bridge(const char *path)
{
	struct stat sb;

	if (lstat(path, &sb) == -1) {
		return errno;
	}

	return 0;
}

int mcexec_load_desc_stat_size_bridge(const char *filename, long *size_out)
{
	struct stat sb;

	if (stat(filename, &sb) == -1) {
		__dprintf("Error: failed to stat %s\n", filename);
		return errno;
	}

	*size_out = sb.st_size;
	return 0;
}

int mcexec_overlay_stat_exists_bridge(const char *path)
{
	struct stat sb;

	return stat(path, &sb) < 0 ? -errno : 0;
}

int mcexec_overlay_stat_errno_bridge(const char *path)
{
	struct stat sb;

	return stat(path, &sb) == -1 ? errno : 0;
}

int mcexec_overlay_lstat_is_symlink_bridge(const char *path, int *is_symlink)
{
	struct stat sb;

	if (lstat(path, &sb) == -1)
		return -errno;

	*is_symlink = S_ISLNK(sb.st_mode);
	return 0;
}

ssize_t mcexec_overlay_readlink_bridge(const char *path, char *out,
		size_t size)
{
	return readlink(path, out, size);
}

int mcexec_overlay_find_libdir_bridge(char *out, size_t size)
{
	return find_libdir(out, size);
}

void *mcexec_dma_mmap_bridge(void)
{
	return mmap(0, PIN_SIZE, PROT_READ | PROT_WRITE,
			(MAP_ANONYMOUS | MAP_PRIVATE), -1, 0);
}

int mcexec_dma_mlock_bridge(void *buf)
{
	return mlock(buf, (size_t)PIN_SIZE);
}

int mcexec_create_ppd_bridge(void)
{
	return ioctl(fd, MCEXEC_UP_CREATE_PPD, NULL);
}

void mcexec_dma_mmap_failed_bridge(void)
{
	__dprintf("error: allocating DMA area\n");
	exit(1);
}

void mcexec_dma_mlock_failed_bridge(void)
{
	__dprintf("ERROR: locking dma_buf\n");
	exit(1);
}

void mcexec_create_ppd_failed_bridge(void)
{
	perror("creating mcctrl per-process structure");
	close(fd);
	exit(1);
}

void mcexec_main_prepare_image_failed_bridge(void)
{
	perror("prepare");
	close(fd);
}

void mcexec_main_start_image_failed_bridge(void)
{
	perror("exec");
	close(fd);
}

void mcexec_main_worker_threads_failed_bridge(int error)
{
	fprintf(stderr, "%s: Error: creating worker threads: %s\n",
			"main", strerror(-error));
	close(fd);
}

void mcexec_flib_affinity_alloc_failed_bridge(void)
{
	fprintf(stderr, "error: allocating memory for "
			"FLIB_AFFINITY_ON_PROCESS\n");
	exit(EXIT_FAILURE);
}

void mcexec_main_invalid_option_bridge(int opt, char **argv)
{
	switch (opt) {
	case 'c':
		fprintf(stderr, "error: -c: invalid target CPU\n");
		break;
	case 'n':
		fprintf(stderr, "error: -n: invalid number of processes\n");
		break;
	case 't':
		fprintf(stderr, "error: -t: invalid number of threads\n");
		break;
	default:
		print_usage(argv);
		break;
	}
	exit(EXIT_FAILURE);
}

void mcexec_atobytes_set_errno_bridge(int value)
{
	errno = value;
}

int mcexec_print_usage_add_envs_bridge(void)
{
#ifdef ADD_ENVS_OPTION
	return 1;
#else
	return 0;
#endif
}

void mcexec_print_usage_write_bridge(const char *line, size_t len)
{
	fwrite(line, 1, len, stderr);
}

void mcexec_kill_thread_bridge(unsigned long tid, unsigned long sig,
		struct thread_data_s *my_thread)
{
	mcexec_kill_thread_body(tid, sig, my_thread);
}

long mcexec_sched_setaffinity_util_bridge(struct thread_data_s *my_thread,
		unsigned long rp_rctx, int remote_tid, unsigned long pattr,
		unsigned long uti_info, unsigned long uti_desc_arg)
{
	return util_thread(my_thread, rp_rctx, remote_tid, pattr, uti_info,
			uti_desc_arg);
}

int mcexec_util_thread_switch_ctx_bridge(struct uti_switch_ctx_desc *desc,
		void *lctx, void *rctx)
{
	return switch_ctx(fd, MCEXEC_UP_UTI_SWITCH_CTX, desc, lctx, rctx);
}

long mcexec_debug_mlock_bridge(unsigned long addr, unsigned long len)
{
	return mlock((void *)addr, len);
}

void mcexec_debug_mlock_log_bridge(unsigned long addr, unsigned long len)
{
	printf("linux mlock(%p, %ld)\n", (void *)addr, len);
	printf("str(%p)=%s", (void *)addr, (char *)addr);
}

void mcexec_desc_mpol_log_bridge(const struct program_load_desc *desc)
{
	__dprintf("mpol_mode: %d, mpol_nodemask: %ld\n",
		  desc->mpol_mode, desc->mpol_nodemask[0]);
}

void mcexec_reduce_stack_newval_overflow_bridge(void)
{
	__eprintf("snprintf(%s):buffer overflow\n", rlimit_stack_envname);
}

void mcexec_reduce_stack_setenv_failed_bridge(void)
{
	__eprintf("failed to setenv(%s)\n", rlimit_stack_envname);
}

void mcexec_main_stack_parse_failed_bridge(int parse_rc)
{
	fprintf(stderr, "Error: Failed to parse %s %d\n",
			rlimit_stack_envname, parse_rc);
}

void mcexec_load_realloc_failed_bridge(unsigned long size)
{
	__eprintf("realloc(%#lx) failed\n", (long)size);
}

void mcexec_load_desc_sections_bridge(int count)
{
	__dprintf("# of sections: %d\n", count);
}

void mcexec_print_desc_intro_bridge(const void *desc)
{
	if (debug) {
		printf("print_desc: Desc (%p)\n", desc);
		fflush(stdout);
	}
}

void mcexec_print_desc_main_bridge(int cpu, int pid, unsigned long entry,
		unsigned long rprocess)
{
	if (debug) {
		printf("print_desc: CPU = %d, pid = %d, entry = %lx, rp = %lx\n",
				cpu, pid, entry, rprocess);
		fflush(stdout);
	}
}

void mcexec_print_desc_section_bridge(unsigned long vaddr,
		unsigned long len, unsigned long remote_pa,
		unsigned long filesz)
{
	if (debug) {
		printf("print_desc: vaddr: %lx, mem_len: %lx, remote_pa: %lx, files: %lx\n",
				vaddr, len, remote_pa, filesz);
		fflush(stdout);
	}
}

void mcexec_overlay_getdents_upper_bridge(int mck_ret, int ret,
		unsigned int count)
{
	__dprintf("getdents from upper: mck_ret: %d, ret: %d, count: %d\n",
		  mck_ret, ret, count);
}

void mcexec_overlay_getdents_lower_bridge(int linux_ret, int ret,
		unsigned int count)
{
	__dprintf("getdents from lower: linux_ret: %d, ret: %d, count: %d\n",
		  linux_ret, ret, count);
}

void mcexec_overlay_getdents_mck_size_log_bridge(size_t size, long offset,
		int len, unsigned int count)
{
	__dprintf("mck_dirents_size: %ld, offset: %ld, mck_len: %d, count: %d\n",
		  size, offset, len, count);
}

void mcexec_overlay_getdents_linux_size_log_bridge(size_t size, long offset,
		int len, unsigned int count)
{
	__dprintf("linux_dirents_size: %ld, offset: %ld, linux_len: %d, count: %d\n",
		  size, offset, len, count);
}
