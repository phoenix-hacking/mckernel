unsigned long ihk_mc_syscall_ret(const ihk_mc_user_context_t *uc)
{
	return uc ? uc->gpr.rax : 0;
}
void ihk_mc_syscall_set_ret(ihk_mc_user_context_t *uc, unsigned long value)
{
	if (uc)
		uc->gpr.rax = value;
}
