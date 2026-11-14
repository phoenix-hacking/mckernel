SYSCALL_POLICY_HELPER_SCOPE long
execveat_body_result(void *ctx, int dirfd, const char *filename, char **argv,
		char **envp, int flags, int filename_first,
		syscall_execveat_fn_t execveat_fn)
{
	int error = execveat_policy_result(flags, dirfd, filename_first);

	if (error) {
		return error;
	}
	if (!execveat_fn) {
		return -EFAULT;
	}

	return execveat_fn(ctx, dirfd, filename, argv, envp, flags);
}
