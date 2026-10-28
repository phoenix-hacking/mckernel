static long
perf_mmap(struct mckfd *sfd, ihk_mc_user_context_t *ctx)
{
	intptr_t addr0 = ihk_mc_syscall_arg0(ctx);
	size_t len0 = ihk_mc_syscall_arg1(ctx);
	int prot = ihk_mc_syscall_arg2(ctx);
	int flags = ihk_mc_syscall_arg3(ctx);
	int fd = ihk_mc_syscall_arg4(ctx);
	off_t off0 = ihk_mc_syscall_arg5(ctx);

	(void)sfd;

	return perf_mmap_body_result(addr0, len0, prot, flags, fd, off0,
			MAP_ANONYMOUS, PROT_WRITE,
			__builtin_offsetof(struct perf_event_mmap_page,
					   data_head),
			__builtin_offsetof(struct perf_event_mmap_page,
					   capabilities),
			1UL << 2, do_mmap);
}
