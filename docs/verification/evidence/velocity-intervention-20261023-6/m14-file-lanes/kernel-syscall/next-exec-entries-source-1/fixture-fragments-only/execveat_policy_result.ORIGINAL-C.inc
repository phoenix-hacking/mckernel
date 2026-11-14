SYSCALL_POLICY_HELPER_SCOPE int
execveat_policy_result(int flags, int dirfd, int filename_first)
{
	if ((flags & ~(AT_SYMLINK_NOFOLLOW | AT_EMPTY_PATH)) != 0) {
		return -EINVAL;
	}

	if (filename_first == '/' || dirfd == AT_FDCWD) {
		return 0;
	}

	if (dirfd < 0) {
		return -EBADF;
	}

	return 0;
}
