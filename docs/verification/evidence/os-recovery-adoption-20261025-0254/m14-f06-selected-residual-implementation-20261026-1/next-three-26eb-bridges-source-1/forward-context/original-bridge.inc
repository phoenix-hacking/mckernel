
long
arch_syscall_forward_context_bridge(int syscall_nr, void *ctx)
{
	return syscall_generic_forwarding(syscall_nr, ctx);
}
