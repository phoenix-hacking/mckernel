SYSCALL_POLICY_HELPER_SCOPE int
sigaction_validate(int sig, int has_act)
{
	if (!valid_signal(sig) || sig < 1) {
		return -EINVAL;
	}
	if (has_act && (sig == SIGKILL || sig == SIGSTOP)) {
		return -EINVAL;
	}
	return 0;
}
