#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_execveat(int n, ihk_mc_user_context_t *ctx);
#else
long sys_execveat(int n, ihk_mc_user_context_t *ctx)
{
	int dirfd = (int)ihk_mc_syscall_arg0(ctx);
	const char *filename = (const char *)ihk_mc_syscall_arg1(ctx);
	int flags = (int)ihk_mc_syscall_arg4(ctx);

	return execveat_body_result(ctx, dirfd, filename,
			(char **)ihk_mc_syscall_arg2(ctx),
			(char **)ihk_mc_syscall_arg3(ctx), flags,
			filename[0], syscall_execveat_bridge);
}
#endif
