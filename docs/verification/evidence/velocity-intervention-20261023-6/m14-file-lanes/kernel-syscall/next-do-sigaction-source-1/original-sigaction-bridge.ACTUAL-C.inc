int
syscall_do_sigaction_bridge(int sig, void *act, void *oact)
{
	return do_sigaction(sig, act, oact);
}
