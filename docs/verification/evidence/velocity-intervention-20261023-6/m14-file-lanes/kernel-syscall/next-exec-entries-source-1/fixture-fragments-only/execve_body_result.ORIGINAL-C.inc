SYSCALL_POLICY_HELPER_SCOPE long
execve_body_result(void *ctx, const char *filename, char **argv, char **envp,
		syscall_execveat_fn_t execveat_fn)
{
	if (!execveat_fn) {
		return -EFAULT;
	}

	return execveat_fn(ctx, AT_FDCWD, filename, argv, envp, 0);
}
