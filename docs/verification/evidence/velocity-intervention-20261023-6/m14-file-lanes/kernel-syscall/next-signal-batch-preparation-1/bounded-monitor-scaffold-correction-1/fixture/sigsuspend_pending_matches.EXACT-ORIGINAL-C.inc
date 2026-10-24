SYSCALL_POLICY_HELPER_SCOPE int
sigsuspend_pending_matches(unsigned long pending_mask, unsigned long suspend_mask)
{
	return !(pending_mask & suspend_mask);
}
