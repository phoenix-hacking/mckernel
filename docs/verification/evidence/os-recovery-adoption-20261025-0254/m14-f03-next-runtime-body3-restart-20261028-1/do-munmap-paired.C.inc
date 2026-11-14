#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
struct f03_do_munmap_binding {
	do_munmap_void_fn_t begin;
	do_munmap_remove_range_fn_t remove_range;
	do_munmap_clear_host_fn_t clear_host;
	mprotect_set_host_vma_fn_t set_host;
	do_munmap_void_fn_t finish;
	do_munmap_log_fn_t log;
};
const struct f03_do_munmap_binding f03_do_munmap_binding_v1 = {
	.begin = do_munmap_begin_bridge,
	.remove_range = do_munmap_remove_range_bridge,
	.clear_host = do_munmap_clear_host_bridge,
	.set_host = do_munmap_set_host_bridge,
	.finish = do_munmap_finish_bridge,
	.log = do_munmap_log_bridge,
};
extern int do_munmap(void *, size_t, int);
#else
#line 5837
int do_munmap(void *addr, size_t len, int holding_memory_range_lock)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	return do_munmap_body_result(thread->vm, thread->proc,
			(uintptr_t)addr, len, holding_memory_range_lock,
			offsetof(struct process, straight_va),
			offsetof(struct process, straight_len),
			do_munmap_begin_bridge, do_munmap_remove_range_bridge,
			do_munmap_clear_host_bridge, do_munmap_set_host_bridge,
			do_munmap_finish_bridge, do_munmap_log_bridge);
}
#endif
#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)
#line 5838
#else
#line 5847
#endif
