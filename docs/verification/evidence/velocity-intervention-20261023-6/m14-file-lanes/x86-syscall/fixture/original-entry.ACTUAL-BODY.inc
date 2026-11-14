long arch_ptrace_syscall_event(struct thread *thread,
				ihk_mc_user_context_t *ctx, long setret)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	return arch_ptrace_syscall_event_body_result(thread, ctx, setret,
			__builtin_offsetof(ihk_mc_user_context_t, gpr.rax),
			arch_ptrace_syscall_event_bridge);
#else
	ihk_mc_syscall_set_ret(ctx, setret);
	ptrace_syscall_event(thread);
	return ihk_mc_syscall_ret(ctx);
#endif
}
