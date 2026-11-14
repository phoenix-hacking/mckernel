static int
syscall_execveat_bridge(void *ctx, int dirfd, const char *filename,
		char **argv, char **envp, int flags)
{
	return do_execveat((ihk_mc_user_context_t *)ctx, dirfd, filename,
			argv, envp, flags);
}
