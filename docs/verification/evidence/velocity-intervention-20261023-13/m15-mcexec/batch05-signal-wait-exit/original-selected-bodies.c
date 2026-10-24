int mcexec_sendsig_si_pid_bridge(const siginfo_t *siginfo)
{
	return siginfo->si_pid;
}

int mcexec_sendsig_si_signo_bridge(const siginfo_t *siginfo)
{
	return siginfo->si_signo;
}

void mcexec_sendsig_default_action_bridge(int sig)
{
	signal(sig, SIG_DFL);
	kill(getpid(), sig);
	for(;;)
		sleep(1);
}

ssize_t mcexec_act_signalfd4_write_bridge(int fd, const void *info,
		size_t len)
{
	return write(fd, info, len);
}

void mcexec_act_signalfd4_write_error_bridge(void)
{
	fprintf(stderr, "error: writing sigpipe\n");
}

void mcexec_act_sigaction_install_bridge(int sig, int ignored)
{
	struct sigaction act;

	memset(&act, '\0', sizeof act);
	if (ignored) {
		act.sa_handler = SIG_IGN;
	}
	else {
		act.sa_sigaction = sendsig;
		act.sa_flags = SA_SIGINFO;
	}
	sigaction(sig, &act, NULL);
}

void mcexec_act_sigprocmask_apply_bridge(unsigned long mask)
{
	sigset_t set;

	sigemptyset(&set);
	memcpy(&set, &mask, sizeof(unsigned long));
	sigdelset(&set, LOCALSIG);
	sigprocmask(SIG_SETMASK, &set, NULL);
}

void mcexec_init_sigaction_set_master_tid_bridge(int tid)
{
	master_tid = tid;
}

void mcexec_init_sigaction_install_bridge(int sig)
{
	struct sigaction act;

	sigaction(sig, NULL, &act);
	act.sa_sigaction = sendsig;
	act.sa_flags &= ~(SA_RESTART);
	act.sa_flags |= SA_SIGINFO;
	sigaction(sig, &act, NULL);
}

int mcexec_waitid_pid_bridge(int pid, int opt, int *errno_out)
{
	siginfo_t info;
	int ret;

	memset(&info, '\0', sizeof info);
	while ((ret = waitid(P_PID, pid, &info, opt)) == -1 &&
			errno == EINTR)
		;
	if (errno_out)
		*errno_out = errno;
	if (ret == 0)
		ret = info.si_pid;
	return ret;
}

void mcexec_wait4_error_bridge(unsigned long requested_pid, int ret,
		int errno_value)
{
	fprintf(stderr, "ERROR: waiting for %lu rc=%d errno=%d\n",
			requested_pid, ret, errno_value);
}

void mcexec_exit_debug_bridge(unsigned long status, int cpu)
{
	__dprintf("__NR_exit/__NR_exit_group: %ld (cpu_id: %d)\n",
			status, cpu);
}

int mcexec_exit_isatty_bridge(int target_fd)
{
	return isatty(target_fd);
}

void mcexec_exit_report_signal_bridge(int sig)
{
	fprintf(stderr, "Terminate by signal %d\n", sig);
}

void mcexec_exit_report_status_bridge(int term)
{
	__dprintf("Exit status: %d\n", term);
}

void mcexec_exit_replay_signal_bridge(int sig)
{
	signal(sig, SIG_DFL);
	kill(getpid(), sig);
	pause();
}

void mcexec_exit_process_bridge(int term)
{
	exit(term);
}
