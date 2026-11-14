static int
isrestart(int num, unsigned long rc, int sig, int restart)
{
#ifdef MCKERNEL_NATIVE_SIGNAL_STACK
	/* A pending handler observes the already-restored user continuation. */
	if (num == __NR_rt_sigreturn)
		return 0;
#endif
	if (sig == SIGKILL || sig == SIGSTOP)
		return 0;
	if (num < 0 || rc != (unsigned long)-EINTR)
		return 0;
	if (sig == SIGCHLD)
		return 1;
	switch (num) {
	    case __NR_pause:
	    case __NR_rt_sigsuspend:
	    case __NR_rt_sigtimedwait:
//	    case __NR_rt_sigwaitinfo:
	    case __NR_epoll_wait:
	    case __NR_epoll_pwait:
	    case __NR_poll:
	    case __NR_ppoll:
	    case __NR_select:
	    case __NR_pselect6:
	    case __NR_msgrcv:
	    case __NR_msgsnd:
	    case __NR_semop:
	    case __NR_semtimedop:
	    case __NR_clock_nanosleep:
	    case __NR_nanosleep:
//	    case __NR_usleep:
	    case __NR_io_getevents:
		return 0;
	}
	if (restart)
		return 1;
	return 0;
}
