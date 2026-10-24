long sys_execve(int n, ihk_mc_user_context_t *ctx)
{
	return execve_body_result(ctx,
			(const char *)ihk_mc_syscall_arg0(ctx),
			(char **)ihk_mc_syscall_arg1(ctx),
			(char **)ihk_mc_syscall_arg2(ctx),
			syscall_execveat_bridge);
}
