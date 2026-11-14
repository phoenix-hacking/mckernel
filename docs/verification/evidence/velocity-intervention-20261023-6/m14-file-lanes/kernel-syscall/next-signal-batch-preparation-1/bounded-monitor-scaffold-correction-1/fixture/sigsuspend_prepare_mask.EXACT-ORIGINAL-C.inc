SYSCALL_POLICY_HELPER_SCOPE unsigned long
sigsuspend_prepare_mask(unsigned long raw_mask)
{
	raw_mask &= ~__sigmask(SIGKILL);
	raw_mask &= ~__sigmask(SIGSTOP);
	return raw_mask;
}
