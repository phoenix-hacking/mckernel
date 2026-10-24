#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
int
syscall_execveat_bridge(void *ctx, int dirfd, const char *filename,
		char **argv, char **envp, int flags)
{
	return do_execveat((ihk_mc_user_context_t *)ctx, dirfd, filename,
			argv, envp, flags);
}

long sys_execve(int n, ihk_mc_user_context_t *ctx);
#else
static int
syscall_execveat_bridge(void *ctx, int dirfd, const char *filename,
		char **argv, char **envp, int flags)
{
	return do_execveat((ihk_mc_user_context_t *)ctx, dirfd, filename,
			argv, envp, flags);
}

long sys_execve(int n, ihk_mc_user_context_t *ctx)
{
	return execve_body_result(ctx,
			(const char *)ihk_mc_syscall_arg0(ctx),
			(char **)ihk_mc_syscall_arg1(ctx),
			(char **)ihk_mc_syscall_arg2(ctx),
			syscall_execveat_bridge);
}
#endif
