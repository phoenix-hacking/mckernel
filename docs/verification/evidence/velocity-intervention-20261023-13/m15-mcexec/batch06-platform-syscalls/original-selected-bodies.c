long mcexec_path_readlinkat_bridge(int dirfd, const char *path,
		char *buf, size_t size)
{
	long ret;

	ret = readlinkat(dirfd, path, buf, size);
	SET_ERR(ret);
	__dprintf("readlinkat: dirfd=%d, path=%s, buf=%s, ret=%ld\n",
		dirfd, path, buf, ret);
	return ret;
}

long mcexec_path_readlink_bridge(const char *path, char *buf, size_t size)
{
	long ret;

	ret = readlink(path, buf, size);
	SET_ERR(ret);
	__dprintf("readlink: path=%s, buf=%s, ret=%ld\n", path, buf, ret);
	return ret;
}

long mcexec_path_fstatat_bridge(int dirfd, const char *path,
		void *statbuf, int flags)
{
	long ret;

	ret = fstatat(dirfd, path, statbuf, flags);
	SET_ERR(ret);
	__dprintf("fstatat: dirfd=%d, pathname=%s, buf=%p, flags=%x, ret=%ld\n",
		  dirfd, path, statbuf, flags, ret);
	return ret;
}

long mcexec_path_stat_bridge(const char *path, void *statbuf)
{
	long ret;

	ret = stat(path, statbuf);
	SET_ERR(ret);
	__dprintf("stat: path=%s, ret=%ld\n", path, ret);
	return ret;
}

long mcexec_path_faccessat_bridge(int dirfd, const char *path,
		int mode, int flags)
{
	long ret;

	ret = faccessat(dirfd, path, mode, flags);
	SET_ERR(ret);
	__dprintf("faccessat: dirfd=%d, pathname=%s, mode=%d, ret=%ld\n",
		  dirfd, path, mode, ret);
	return ret;
}

long mcexec_path_access_bridge(const char *path, int mode)
{
	long ret;

	ret = access(path, mode);
	SET_ERR(ret);
	__dprintf("access: path=%s, ret=%ld\n", path, ret);
	return ret;
}

long mcexec_path_getxattr_bridge(const char *path, const char *name,
		void *value, size_t size)
{
	long ret;

	ret = getxattr(path, name, value, size);
	SET_ERR(ret);
	__dprintf("getxattr: path=%s, name=%s, ret=%ld\n", path, name, ret);
	return ret;
}

long mcexec_path_lgetxattr_bridge(const char *path, const char *name,
		void *value, size_t size)
{
	long ret;

	ret = lgetxattr(path, name, value, size);
	SET_ERR(ret);
	__dprintf("lgetxattr: path=%s, name=%s, ret=%ld\n", path, name, ret);
	return ret;
}

void mcexec_path_openat_log_bridge(int dirfd, const char *path, int tid)
{
	__dprintf("openat: %d, %s,tid=%d\n", dirfd, path, tid);
}

void mcexec_path_open_log_bridge(const char *path)
{
	__dprintf("open: %s\n", path);
}

long mcexec_path_openat_bridge(int dirfd, const char *path,
		unsigned long flags, unsigned long mode)
{
	long ret;

	ret = openat(dirfd, path, flags, mode);
	SET_ERR(ret);
	return ret;
}

long mcexec_path_open_bridge(const char *path, unsigned long flags,
		unsigned long mode)
{
	long ret;

	ret = open(path, flags, mode);
	SET_ERR(ret);
	return ret;
}

void mcexec_cred_get_bridge(int mcos_fd, unsigned long arg)
{
	ioctl(mcos_fd, MCEXEC_UP_GET_CRED, arg);
}

long mcexec_cred_setfsuid_bridge(unsigned long uid)
{
	return setfsuid(uid);
}

long mcexec_cred_setfsgid_bridge(unsigned long gid)
{
	return setfsgid(gid);
}

long mcexec_cred_setresuid_bridge(unsigned long ruid,
		unsigned long euid, unsigned long suid)
{
	long ret;

	ret = setresuid(ruid, euid, suid);
	SET_ERR(ret);
	return ret;
}

long mcexec_cred_setresgid_bridge(unsigned long rgid,
		unsigned long egid, unsigned long sgid)
{
	long ret;

	ret = setresgid(rgid, egid, sgid);
	SET_ERR(ret);
	return ret;
}

long mcexec_cred_setreuid_bridge(unsigned long ruid, unsigned long euid)
{
	long ret;

	ret = setreuid(ruid, euid);
	SET_ERR(ret);
	return ret;
}

long mcexec_cred_setregid_bridge(unsigned long rgid, unsigned long egid)
{
	long ret;

	ret = setregid(rgid, egid);
	SET_ERR(ret);
	return ret;
}

long mcexec_cred_setuid_bridge(unsigned long uid)
{
	long ret;

	ret = setuid(uid);
	SET_ERR(ret);
	return ret;
}

long mcexec_cred_setgid_bridge(unsigned long gid)
{
	long ret;

	ret = setgid(gid);
	SET_ERR(ret);
	return ret;
}

long mcexec_do_generic_syscall_raw_bridge(struct syscall_wait_desc *w)
{
	return syscall(w->sr.number, w->sr.args[0], w->sr.args[1], w->sr.args[2],
		       w->sr.args[3], w->sr.args[4], w->sr.args[5]);
}

void mcexec_do_generic_syscall_start_bridge(unsigned long number)
{
	__dprintf("do_generic_syscall(%ld)\n", number);
}

void mcexec_do_generic_syscall_done_bridge(unsigned long number, long ret)
{
	__dprintf("do_generic_syscall(%ld):%ld (%#lx)\n", number, ret, ret);
}

long mcexec_do_generic_syscall_bridge(struct syscall_wait_desc *w)
{
	return mcexec_do_generic_syscall_body(w);
}

long mcexec_perf_event_open_bridge(void)
{
	return open("/dev/null", O_RDONLY);
}

long mcexec_clock_gettime_bridge(int clock_id, struct timespec *tv)
{
	long ret;

	ret = clock_gettime(clock_id, tv);
	SET_ERR(ret);
	return ret;
}

void mcexec_clock_gettime_log_bridge(long sec, long nsec)
{
	__dprintf("clock_gettime=%016ld,%09ld\n", sec, nsec);
}
