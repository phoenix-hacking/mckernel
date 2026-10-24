unsigned long mcexec_main_page_size_bridge(void)
{
	return sysconf(_SC_PAGESIZE);
}

void mcexec_main_publish_page_altroot_bridge(unsigned long new_page_size,
		const char *new_altroot)
{
	page_size = new_page_size;
	page_mask = ~(page_size - 1);
	altroot = (char *)new_altroot;
}

const char *mcexec_altroot_bridge(void)
{
	return altroot;
}

void mcexec_load_desc_publish_exec_path_bridge(char *path)
{
	if (exec_path) {
		free(exec_path);
	}
	exec_path = path;
}

int mcexec_main_load_stack_rlimit_bridge(unsigned long *cur,
		unsigned long *max)
{
	if (getrlimit(RLIMIT_STACK, &rlim_stack)) {
		fprintf(stderr, "getrlimit failed\n");
		return 1;
	}
	*cur = rlim_stack.rlim_cur;
	*max = rlim_stack.rlim_max;
	__dprintf("rlim_stack=%ld,%ld\n", rlim_stack.rlim_cur,
			rlim_stack.rlim_max);
	return 0;
}

int mcexec_reduce_stack_setenv_bridge(const char *newval)
{
	return setenv(rlimit_stack_envname, newval, DO_NOT_OVERWRITE);
}

int mcexec_reduce_stack_setrlimit_bridge(unsigned long cur, unsigned long max)
{
	struct rlimit new_rlim;

	new_rlim.rlim_cur = cur;
	new_rlim.rlim_max = max;
	return setrlimit(RLIMIT_STACK, &new_rlim);
}

ssize_t mcexec_reduce_stack_readlink_bridge(char *path, size_t size)
{
	return readlink("/proc/self/exe", path, size);
}

ssize_t mcexec_find_libdir_readlink_bridge(char *path, size_t size)
{
	return readlink("/proc/self/exe", path, size);
}

int mcexec_reduce_stack_execv_bridge(const char *path, char **argv)
{
	return execv(path, argv);
}

int mcexec_execve1_enable_vdso_bridge(void)
{
	return enable_vdso;
}

unsigned long mcexec_execve1_rlim_cur_bridge(void)
{
	return rlim_stack.rlim_cur;
}

unsigned long mcexec_execve1_rlim_max_bridge(void)
{
	return rlim_stack.rlim_max;
}

long mcexec_execve1_stack_premap_bridge(void)
{
	return stack_premap;
}

int mcexec_main_loop_is_child_bridge(void)
{
	return ischild;
}

int mcexec_opendev_mcosid_bridge(void)
{
	return mcosid;
}

int mcexec_overlay_mcosid_bridge(void)
{
	return mcosid;
}

int mcexec_ld_preload_enable_uti_bridge(void)
{
	return enable_uti;
}

int mcexec_overlay_enable_uti_bridge(void)
{
	return enable_uti;
}

int mcexec_ld_preload_disable_sched_yield_bridge(void)
{
	return disable_sched_yield;
}

void mcexec_main_publish_args_bridge(int argc, char **argv)
{
#ifdef USE_SYSCALL_MOD_CALL
	__glob_argc = argc;
	__glob_argv = argv;
#endif
}

void mcexec_main_state_ptrs_bridge(struct mcexec_main_state_ptrs *state)
{
	memset(state, 0, sizeof(*state));
	state->nr_processes = &nr_processes;
	state->nr_threads = &nr_threads;
	state->mpol_threshold = &mpol_threshold;
	state->heap_extension = &heap_extension;
	state->straight_map_threshold = &straight_map_threshold;
	state->stack_premap = &stack_premap;
	state->stack_max = &stack_max;
	state->uti_thread_rank = &uti_thread_rank;
	state->mcexec_flags = &mcexec_flags;
	state->mpol_bind_nodes = &mpol_bind_nodes;
	state->enable_uti = &enable_uti;
	state->enable_vdso = &enable_vdso;
	state->profile = &profile;
	state->mpol_no_heap = &mpol_no_heap;
	state->mpol_no_stack = &mpol_no_stack;
	state->mpol_no_bss = &mpol_no_bss;
	state->mpol_shm_premap = &mpol_shm_premap;
	state->no_bind_ikc_map = &no_bind_ikc_map;
	state->straight_map = &straight_map;
	state->uti_use_last_cpu = &uti_use_last_cpu;
#ifdef ENABLE_TOFU
	state->enable_tofu = &enable_tofu;
#endif
	state->rlim_cur = &rlim_stack.rlim_cur;
	state->rlim_max = &rlim_stack.rlim_max;
}

int mcexec_main_personality_bridge(char **argv)
{
	int persona;
	int error;
	char path[PATH_MAX];

	/* Disable READ_IMPLIES_EXEC */
	persona = personality(0xffffffff);
	if (persona & READ_IMPLIES_EXEC) {
		persona &= ~READ_IMPLIES_EXEC;
		persona = personality(persona);
	}

	/* Disable address space layout randomization */
	__dprintf("persona=%08x\n", persona);
	if ((persona & (PER_LINUX | ADDR_NO_RANDOMIZE)) == 0) {
		if (getenv("MCEXEC_ADDR_NO_RANDOMIZE")) {
			__eprintf("personality() and then execv() failed\n");
			return 1;
		}

		persona = personality(persona | PER_LINUX | ADDR_NO_RANDOMIZE);
		if (persona == -1) {
			__eprintf("personality failed, persona=%08x, strerror=%s\n",
				  persona, strerror(errno));
			return 1;
		}

		error = setenv("MCEXEC_ADDR_NO_RANDOMIZE", "1", 1);
		if (error == -1) {
			__eprintf("setenv failed\n");
			return 1;
		}

		error = readlink("/proc/self/exe", path, sizeof(path));
		if (error == -1) {
			__eprintf("readlink failed: %m\n");
			return 1;
		}
		if (error >= sizeof(path)) {
			strcpy(path, "/proc/self/exe");
		} else {
			path[error] = '\0';
		}

		error = execv(path, argv);
		if (error == -1) {
			__eprintf("execv failed, error=%d,strerror=%s\n",
				  error, strerror(errno));
			return 1;
		}
	}

	if (getenv("MCEXEC_ADDR_NO_RANDOMIZE")) {
		error = unsetenv("MCEXEC_ADDR_NO_RANDOMIZE");
		if (error == -1) {
			__eprintf("unsetenv failed");
			return 1;
		}
	}

	return 0;
}

int mcexec_main_next_option_bridge(int argc, char **argv)
{
#ifdef ADD_ENVS_OPTION
	return getopt_long(argc, argv, "+c:n:t:M:h:e:s:m:u:S:f:",
			   mcexec_options, NULL);
#else
	return getopt_long(argc, argv, "+c:n:t:M:h:s:m:u:S:f:",
			   mcexec_options, NULL);
#endif
}

char *mcexec_main_optarg_bridge(void)
{
	return optarg;
}

int mcexec_main_optind_bridge(void)
{
	return optind;
}

void mcexec_main_publish_mcosid_bridge(int new_mcosid)
{
	mcosid = new_mcosid;
}

int mcexec_main_uti_unavailable_bridge(int enable_uti_arg)
{
#ifndef ENABLE_UTI
	if (enable_uti_arg) {
		__eprintf("ERROR: uti is not available when not configured with --with-syscall_intercept=<path>\n");
		return 1;
	}
#else
	(void)enable_uti_arg;
#endif
	return 0;
}

void mcexec_main_overlay_lock_init_bridge(void)
{
	pthread_spin_init(&overlay_fd_lock, 0);
}

char *mcexec_opendev_dev_bridge(void)
{
	return dev;
}

size_t mcexec_opendev_dev_size_bridge(void)
{
	return sizeof(dev);
}

int mcexec_opendev_open_bridge(const char *path)
{
	return open(path, O_RDWR);
}

void mcexec_opendev_publish_fd_bridge(int value)
{
	fd = value;
}

int mcexec_opendev_query_buildid_bridge(int target_fd, char *query_result)
{
	return ioctl(target_fd, IHK_OS_GET_BUILDID, query_result);
}

void mcexec_opendev_close_bridge(int target_fd)
{
	close(target_fd);
}

void *mcexec_find_libdir_popen_bridge(const char *cmd)
{
	return popen(cmd, "r");
}

ssize_t mcexec_find_libdir_getline_bridge(char **line, size_t *linelen,
		void *filep)
{
	return getline(line, linelen, filep);
}

void mcexec_find_libdir_pclose_bridge(void *filep)
{
	pclose(filep);
}

void mcexec_find_libdir_free_bridge(char *line)
{
	free(line);
}

char *mcexec_ld_preload_getenv_bridge(const char *name)
{
	return getenv(name);
}

int mcexec_ld_preload_setenv_bridge(const char *value)
{
	return setenv("LD_PRELOAD", value, 1);
}

int mcexec_ld_preload_unsetenv_bridge(void)
{
	return unsetenv(ld_preload_envname);
}

int mcexec_ld_preload_enable_qlmpi_bridge(void)
{
#ifdef ENABLE_QLMPI
	return 1;
#else
	return 0;
#endif
}

int mcexec_get_thp_disable_prctl_bridge(void)
{
	return prctl(PR_GET_THP_DISABLE, 0, 0, 0, 0);
}
