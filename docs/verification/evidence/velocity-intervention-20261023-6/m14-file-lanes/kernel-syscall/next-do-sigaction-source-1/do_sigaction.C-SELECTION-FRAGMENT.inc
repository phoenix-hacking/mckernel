#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long
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

int do_sigaction(int sig, struct k_sigaction *act, struct k_sigaction *oact);
#else
int
do_sigaction(int sig, struct k_sigaction *act, struct k_sigaction *oact)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	struct k_sigaction *k;
	struct mcs_rwlock_node_irqsave mcs_rw_node;
	ihk_mc_user_context_t ctx0;
	int error;

	error = sigaction_validate(sig, act != NULL);
	if (error) {
		return error;
	}

	mcs_rwlock_writer_lock(&thread->sigcommon->lock, &mcs_rw_node);
	k = thread->sigcommon->action + sig - 1;
	if(oact)
		memcpy(oact, k, sizeof(struct k_sigaction));
	if(act)
		memcpy(k, act, sizeof(struct k_sigaction));
	mcs_rwlock_writer_unlock(&thread->sigcommon->lock, &mcs_rw_node);

	if(act){
		ihk_mc_syscall_set_arg0(&ctx0, sig);
		ihk_mc_syscall_set_arg1(&ctx0, (unsigned long)act->sa.sa_handler);
		ihk_mc_syscall_set_arg2(&ctx0, act->sa.sa_flags);
		syscall_generic_forwarding(__NR_rt_sigaction, &ctx0);
	}
	return 0;
}
#endif

