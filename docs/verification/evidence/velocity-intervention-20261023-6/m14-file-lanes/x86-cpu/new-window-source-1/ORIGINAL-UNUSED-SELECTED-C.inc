static const struct x86_thread_context_offsets x86_thread_context_offsets = {
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_uctx_offset = __builtin_offsetof(struct thread, uctx),
	.thread_tlsblock_base_offset =
		__builtin_offsetof(struct thread, tlsblock_base),
};

static void *x86_cpu_local_bridge(int cpu)
{
	return get_x86_cpu_local_variable(cpu);
}

static void x86_arch_delay_bridge(int us)
{
	arch_delay(us);
}

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	return x86_lookup_user_context_body_result(thread, get_this_cpu_local_var()->current,
			PS_INTERRUPTIBLE | PS_UNINTERRUPTIBLE |
			PS_STOPPED | PS_TRACED, &x86_thread_context_offsets);
#else
