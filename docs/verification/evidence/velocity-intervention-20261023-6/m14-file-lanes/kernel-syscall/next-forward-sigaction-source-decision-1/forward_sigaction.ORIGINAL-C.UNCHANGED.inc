static long
syscall_forward_sigaction_update_bridge(int sig, const void *actp)
{
	const struct k_sigaction *act = actp;
	ihk_mc_user_context_t ctx0;

	ihk_mc_syscall_set_arg0(&ctx0, sig);
	ihk_mc_syscall_set_arg1(&ctx0,
			(unsigned long)act->sa.sa_handler);
	ihk_mc_syscall_set_arg2(&ctx0, act->sa.sa_flags);
	return syscall_generic_forwarding(__NR_rt_sigaction, &ctx0);
}
