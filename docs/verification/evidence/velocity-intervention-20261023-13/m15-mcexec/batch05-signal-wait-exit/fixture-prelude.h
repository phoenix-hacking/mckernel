/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <setjmp.h>
#include <assert.h>
extern int debug;
extern pid_t master_tid;
void sendsig(int,siginfo_t *,void *);
#define LOCALSIG SIGURG
#define __dprintf(format,args...) do {if(debug){printf("%s: " format,__func__,##args);fflush(stdout);}} while(0)
int mcexec_sendsig_si_pid_bridge(const siginfo_t *siginfo);
int mcexec_sendsig_si_signo_bridge(const siginfo_t *siginfo);
void mcexec_sendsig_default_action_bridge(int sig);
ssize_t mcexec_act_signalfd4_write_bridge(int fd, const void *info,
		size_t len);
void mcexec_act_signalfd4_write_error_bridge(void);
void mcexec_act_sigaction_install_bridge(int sig, int ignored);
void mcexec_act_sigprocmask_apply_bridge(unsigned long mask);
void mcexec_init_sigaction_set_master_tid_bridge(int tid);
void mcexec_init_sigaction_install_bridge(int sig);
int mcexec_waitid_pid_bridge(int pid, int opt, int *errno_out);
void mcexec_wait4_error_bridge(unsigned long requested_pid, int ret,
		int errno_value);
void mcexec_exit_debug_bridge(unsigned long status, int cpu);
int mcexec_exit_isatty_bridge(int target_fd);
void mcexec_exit_report_signal_bridge(int sig);
void mcexec_exit_report_status_bridge(int term);
void mcexec_exit_replay_signal_bridge(int sig);
void mcexec_exit_process_bridge(int term);
