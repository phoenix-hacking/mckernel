#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
extern long f03_perf_mmap_v1(struct mckfd *, ihk_mc_user_context_t *);
#define perf_mmap f03_perf_mmap_v1
struct f03_perf_mmap_binding {
	int map_anonymous;
	int prot_write;
	size_t data_head;
	size_t capabilities;
	unsigned long cap_user_rdpmc;
	perf_do_mmap_fn_t do_mmap;
};
const struct f03_perf_mmap_binding f03_perf_mmap_binding_v1 = {
	.map_anonymous = MAP_ANONYMOUS,
	.prot_write = PROT_WRITE,
	.data_head = __builtin_offsetof(struct perf_event_mmap_page, data_head),
	.capabilities = __builtin_offsetof(struct perf_event_mmap_page, capabilities),
	.cap_user_rdpmc = 1UL << 2,
	.do_mmap = do_mmap,
};
#else
#line 21087
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
#endif
#line 21106
