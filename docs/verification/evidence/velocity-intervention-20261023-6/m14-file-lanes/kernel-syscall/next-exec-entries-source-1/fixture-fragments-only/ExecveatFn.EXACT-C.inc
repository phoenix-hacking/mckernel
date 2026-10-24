typedef int (*syscall_execveat_fn_t)(void *ctx, int dirfd,
		const char *filename, char **argv, char **envp, int flags);
