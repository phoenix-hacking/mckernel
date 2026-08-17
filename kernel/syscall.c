/* syscall.c COPYRIGHT FUJITSU LIMITED 2015-2019 */
/**
 * \file syscall.c
 *  License details are found in the file LICENSE.
 * \brief
 *  system call handlers
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 * 	Copyright (C) 2011 - 2012  Taku Shimosawa
 * \author Balazs Gerofi  <bgerofi@riken.jp> \par
 * 	Copyright (C) 2012  RIKEN AICS
 * \author Masamichi Takagi  <m-takagi@ab.jp.nec.com> \par
 * 	Copyright (C) 2012 - 2013  NEC Corporation
 * \author Min Si <msi@is.s.u-tokyo.ac.jp> \par
 * 	Copyright (C) 2012  Min Si
 * \author Balazs Gerofi  <bgerofi@is.s.u-tokyo.ac.jp> \par
 * 	Copyright (C) 2013  The University of Tokyo
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 * \author Tomoki Shirasawa  <tomoki.shirasawa.kk@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 */
/*
 * HISTORY:
 */

#include <types.h>
#include <kmsg.h>
#include <ihk/cpu.h>
#include <cpulocal.h>
#include <ihk/mm.h>
#include <ihk/ikc.h>
#include <errno.h>
#include <cls.h>
#include <syscall.h>
#include <page.h>
#include <amemcpy.h>
#include <uio.h>
#include <ihk/lock.h>
#include <ctype.h>
#include <waitq.h>
#include <rlimit.h>
#include <affinity.h>
#include <time.h>
#include <ihk/perfctr.h>
#include <mman.h>
#include <kmalloc.h>
#include <memobj.h>
#include <shm.h>
#include <prio.h>
#include <arch/cpu.h>
#include <limits.h>
#include <mc_perf_event.h>
#include <march.h>
#include <process.h>
#include <process_helpers.h>
#include <bitops.h>
#include <bitmap.h>
#include <xpmem.h>
#include <rusage_private.h>
#include <ihk/monitor.h>
#include <profile.h>
#include <ihk/debug.h>
#include <sched_helpers.h>
#include "../executer/include/uti.h"

/* Headers taken from kitten LWK */
#include <lwk/stddef.h>
#include <futex.h>

#ifndef MCKERNEL_RUST_SIGNAL_HELPERS
int valid_signal(unsigned long sig)
{
	return sig <= _NSIG ? 1 : 0;
}

__sigset_t __sigmask(unsigned long sig)
{
	return ((__sigset_t)1) << (sig - 1);
}
#endif

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
size_t iov_length(const struct iovec *iov, unsigned long nr_segs)
{
	unsigned long seg;
	size_t ret = 0;

	for (seg = 0; seg < nr_segs; seg++)
		ret += iov[seg].iov_len;
	return ret;
}
#endif

#define SYSCALL_BY_IKC

//#define DEBUG_PRINT_SC

#ifdef DEBUG_PRINT_SC
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

//static ihk_atomic_t pid_cnt = IHK_ATOMIC_INIT(1024);

/* generate system call handler's prototypes */
#define	SYSCALL_HANDLED(number,name)	extern long sys_##name(int n, ihk_mc_user_context_t *ctx);
#define	SYSCALL_DELEGATED(number,name)
#include <syscall_list.h>
#undef	SYSCALL_HANDLED
#undef	SYSCALL_DELEGATED

/* generate syscall_table[] */
static long (*syscall_table[])(int, ihk_mc_user_context_t *) = {
#define	SYSCALL_HANDLED(number,name)	[number] = &sys_##name,
#define	SYSCALL_DELEGATED(number,name)
#include <syscall_list.h>
#undef	SYSCALL_HANDLED
#undef	SYSCALL_DELEGATED
};

#ifdef MCKERNEL_RUST_SYSCALL_OFFLOAD
long syscall_dispatch_context_bridge(int num, ihk_mc_user_context_t *ctx)
{
	int ns = sizeof(syscall_table) / sizeof(syscall_table[0]);

	if (num < 0 || num >= ns || !syscall_table[num])
		return -ENOSYS;

	return syscall_table[num](num, ctx);
}
#endif

/* generate syscall_name[] */
#define	MCKERNEL_UNUSED	__attribute__ ((unused))
char *syscall_name[] MCKERNEL_UNUSED = {
#define	DECLARATOR(number,name)		[number] = #name,
#define	SYSCALL_HANDLED(number,name)	DECLARATOR(number,#name)
#define	SYSCALL_DELEGATED(number,name)	DECLARATOR(number,#name)
#include <syscall_list.h>
#undef	DECLARATOR
#undef	SYSCALL_HANDLED
#undef	SYSCALL_DELEGATED
};

ihk_spinlock_t tod_data_lock = SPIN_LOCK_UNLOCKED;

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
void tsc_to_ts(unsigned long tsc, struct timespec *ts)
{
	time_t sec_delta;
	long ns_delta;

	sec_delta = tsc / tod_data.clocks_per_sec;
	ns_delta = NS_PER_SEC * (tsc % tod_data.clocks_per_sec)
	           / tod_data.clocks_per_sec;
	/* calc. of ns_delta overflows if clocks_per_sec exceeds 18.44 GHz */

	ts->tv_sec = sec_delta;
	ts->tv_nsec = ns_delta;
	if (ts->tv_nsec >= NS_PER_SEC) {
		ts->tv_nsec -= NS_PER_SEC;
		++ts->tv_sec;
	}
}

unsigned long timeval_to_jiffy(const struct timeval *ats)
{
	return ats->tv_sec * 100 + ats->tv_usec / 10000;
}

unsigned long timespec_to_jiffy(const struct timespec *ats)
{
	return ats->tv_sec * 100 + ats->tv_nsec / 10000000;
}
#endif
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
unsigned long uti_desc; /* Address of struct uti_desc object in syscall_intercept.c */
#else
static unsigned long uti_desc; /* Address of struct uti_desc object in syscall_intercept.c */
#endif

#if defined(MCKERNEL_SYSCALL_POLICY_HELPERS_TEST_EXPORT)
#define SYSCALL_POLICY_HELPER_PROTO
#else
#define SYSCALL_POLICY_HELPER_PROTO static
#endif

#define TIME_DISPATCH_NOOP 0
#define TIME_DISPATCH_LOCAL_REALTIME 1
#define TIME_DISPATCH_PROCESS_CPUTIME 2
#define TIME_DISPATCH_THREAD_CPUTIME 3
#define TIME_DISPATCH_FORWARD 4
#define SETTIMEOFDAY_LOG_ENTER 1
#define SETTIMEOFDAY_LOG_ORIGIN 2
#define SETTIMEOFDAY_LOG_EXIT 3

#define PTRACE_WAKEUP_ACTION_NONE 0
#define PTRACE_WAKEUP_ACTION_KILL 1
#define PTRACE_WAKEUP_ACTION_RESUME 2
#define PTRACE_RESUME_SIGNAL_SOURCE_USER 0
#define PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG 1
#define PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG 2
#define PTRACE_SIGINFO_STORE_SENDSIG 0x1
#define PTRACE_SIGINFO_STORE_RECVSIG 0x2
#define PTRACE_SIGINFO_ALLOC_SENDSIG 0x4
#define PTRACE_CONTROL_LOG_SETOPTIONS_UNSUPPORTED 1
#define PTRACE_CONTROL_LOG_SETOPTIONS_APPLIED 2
#define PTRACE_CONTROL_LOG_ATTACH_RETURN 3
#define PTRACE_CONTROL_LOG_WAKEUP_ENTER 4
#define PTRACE_REPORT_CLONE_LOG_ENTER 5
#define PTRACE_REPORT_CLONE_LOG_KILL_SIGCHLD 6
#define PTRACE_REPORT_CLONE_LOG_DO_KILL_FAILED 7
#define PTRACE_DISPATCH_ARCH 0
#define PTRACE_DISPATCH_TRACEME 1
#define PTRACE_DISPATCH_WAKEUP 2
#define PTRACE_DISPATCH_GETREGS 3
#define PTRACE_DISPATCH_SETREGS 4
#define PTRACE_DISPATCH_GETFPREGS 5
#define PTRACE_DISPATCH_SETFPREGS 6
#define PTRACE_DISPATCH_PEEKUSER 7
#define PTRACE_DISPATCH_POKEUSER 8
#define PTRACE_DISPATCH_PEEKTEXT 9
#define PTRACE_DISPATCH_POKETEXT 10
#define PTRACE_DISPATCH_SETOPTIONS 11
#define PTRACE_DISPATCH_ATTACH 12
#define PTRACE_DISPATCH_DETACH 13
#define PTRACE_DISPATCH_GETSIGINFO 14
#define PTRACE_DISPATCH_SETSIGINFO 15
#define PTRACE_DISPATCH_GETREGSET 16
#define PTRACE_DISPATCH_SETREGSET 17
#define PTRACE_DISPATCH_GETEVENTMSG 18
#define WAIT_STOP_SOURCE_NONE 0
#define WAIT_STOP_SOURCE_THREAD 1
#define WAIT_STOP_SOURCE_PROCESS 2
#define WAIT_STOP_SOURCE_MAIN_THREAD 3
#define WAIT_THREAD_REAP_ACTION_NONE 0
#define WAIT_THREAD_REAP_ACTION_RELEASE 1
#define WAIT_THREAD_REAP_ACTION_PTRACE_DETACH 2
#define WAIT_LOG_ENTER 1
#define WAIT_LOG_SLEEPING 2
#define WAIT_LOG_WOKEN 3
#define WAIT_LOG_FOUND 4
#define WAIT_LOG_NOTFOUND 5
#define WAIT_ZOMBIE_LOG_FOUND 1
#define WAIT_ZOMBIE_LOG_WARNING 2
#define WAIT_ZOMBIE_LOG_STATUS 3
#define GETRUSAGE_DISPATCH_SELF 1
#define GETRUSAGE_DISPATCH_CHILDREN 2
#define GETRUSAGE_DISPATCH_THREAD 3
#define GETRUSAGE_THREAD_UPDATE_READY 0
#define GETRUSAGE_THREAD_UPDATE_INTERRUPT 1
#define TERMINATE_CHILD_ACTION_NONE 0
#define TERMINATE_CHILD_ACTION_FREE_ZOMBIE 1
#define TERMINATE_CHILD_ACTION_REPARENT_CHILD 2
#define TERMINATE_CHILD_ACTION_REPARENT_PTRACED 3
#define SYNC_CHILD_EVENT_ACTION_NONE 0
#define SYNC_CHILD_EVENT_ACTION_CHILD_TOTAL 1
#define SYNC_CHILD_EVENT_ACTION_SET_COUNT 2
#define CLONE_TLS_SOURCE_INHERIT 0
#define CLONE_TLS_SOURCE_ARGUMENT 1

typedef long (*ptrace_read_user_word_fn_t)(unsigned long thread_addr,
		long addr, unsigned long *value);
typedef long (*ptrace_write_user_word_fn_t)(unsigned long thread_addr,
		long addr, unsigned long value);
typedef long (*ptrace_read_vm_word_fn_t)(unsigned long vm_addr,
		unsigned long addr, unsigned long *value);
typedef long (*ptrace_write_vm_word_fn_t)(unsigned long vm_addr,
		unsigned long addr, unsigned long value);
typedef long (*ptrace_fpregs_io_fn_t)(unsigned long thread_addr,
		unsigned long data_addr);
typedef long (*ptrace_user_copy_from_fn_t)(void *dst,
		unsigned long src_addr, size_t bytes);
typedef long (*ptrace_user_copy_to_fn_t)(unsigned long dst_addr,
		const void *src, size_t bytes);
typedef long (*ptrace_regset_io_fn_t)(unsigned long thread_addr,
		long type, void *iovp);
typedef unsigned long (*ptrace_find_thread_fn_t)(int tgid, int tid);
typedef void (*ptrace_thread_unlock_fn_t)(unsigned long thread_addr);
typedef void (*ptrace_text_log_fn_t)(int event, unsigned long addr);
typedef void (*ptrace_control_log_fn_t)(int event, int value, int result);
typedef int (*ptrace_attach_thread_fn_t)(unsigned long thread_addr,
		unsigned long proc_addr);
typedef void (*ptrace_detach_call_fn_t)(unsigned long thread_addr, int data);
typedef void (*ptrace_set_single_step_fn_t)(unsigned long thread_addr);
typedef void (*ptrace_rwlock_fn_t)(unsigned long lock_addr, void *node);
typedef int (*ptrace_saved_context_clear_fn_t)(unsigned long thread_addr,
		unsigned long offset);
typedef int (*ptrace_trace_syscall_update_fn_t)(unsigned long thread_addr,
		unsigned long ptrace_offset, int trace_syscall);
typedef unsigned long (*ptrace_pending_signal_take_fn_t)(
		unsigned long thread_addr, unsigned long sendsig_offset,
		unsigned long recvsig_offset, int source);
typedef long (*syscall_copy_int_to_user_fn_t)(unsigned long dst_addr,
		const int *src);
typedef long (*syscall_copy_from_user_fn_t)(void *dst,
		unsigned long src_addr, size_t bytes);
typedef long (*syscall_copy_to_user_fn_t)(unsigned long dst_addr,
		const void *src, size_t bytes);
typedef long (*syscall_forward_sigmask_fn_t)(unsigned long sigmask);
typedef int (*syscall_sigaction_fn_t)(int sig, void *act, void *oact);
typedef void (*syscall_sigcommon_lock_fn_t)(void *lock, void *node);
typedef long (*syscall_sigaction_forward_fn_t)(int sig, const void *act);
typedef long (*syscall_do_kill_fn_t)(int pid, int sig, const void *info);
typedef long (*syscall_do_kill_thread_fn_t)(void *thread, int pid, int tid,
		int sig, const void *info, int ptracecont);
typedef void (*ptrace_report_signal_fn_t)(void *thread, int sig);
typedef void (*ptrace_void_fn_t)(void);
typedef long (*ptrace_arch_syscall_event_fn_t)(void *thread, void *ctx,
		long setret);
typedef void (*syscall_refresh_cred_fn_t)(void);
typedef void (*syscall_gettime_fn_t)(void *ts);
typedef long (*syscall_do_syscall2_fn_t)(int syscall_nr, unsigned long arg0,
		unsigned long arg1);
typedef long (*syscall_do_syscall3_fn_t)(int syscall_nr, unsigned long arg0,
		unsigned long arg1, unsigned long arg2);
typedef long (*syscall_forward_context_fn_t)(int syscall_nr, void *ctx);
typedef void (*syscall_tsc_to_ts_fn_t)(unsigned long tsc, void *ts);
typedef unsigned long (*syscall_timespec_to_jiffy_fn_t)(const void *ts);
typedef void (*syscall_ts_add_fn_t)(void *dst, const void *src);
typedef void *(*syscall_find_process_fn_t)(int pid, void *lock_arg);
typedef void (*syscall_process_unlock_fn_t)(void *proc, void *lock_arg);
typedef long (*process_cleanup_fd_fn_t)(void *proc, int fd);
typedef void (*process_cleanup_missing_log_fn_t)(int pid);
typedef long (*syscall_do_prlimit64_fn_t)(int pid, int resource,
		unsigned long new_limit_addr, unsigned long old_limit_addr);
typedef int (*syscall_get_cpu_fn_t)(void);
typedef void (*syscall_log_int_fn_t)(int value, int error);
typedef void (*syscall_mbind_log_fn_t)(int event, unsigned long arg0,
		unsigned long arg1, int arg2);
typedef void (*syscall_set_mempolicy_log_fn_t)(int event, int value, int pid);
typedef void (*syscall_get_mempolicy_log_fn_t)(int event,
		unsigned long addr, int value);
#define MBIND_LOG_NODEMASK_BITS_TOO_BIG 2
#define MBIND_LOG_CLAMPED 3
#define MBIND_LOG_INVALID_MODE_FLAGS 4
#define MBIND_LOG_COPY_FROM_NUMA_MASK 5
#define MBIND_LOG_DEFAULT_MASK_NOT_EMPTY 6
#define MBIND_LOG_NODEMASK_NOT_SPECIFIED 7
#define MBIND_LOG_NODE_TOO_LARGE 8
#define MBIND_LOG_INVALID_RANGE 9
#define MBIND_LOG_CLEAR_POLICY_RANGE 10
#define MBIND_LOG_ALLOC_POLICY 11
#define MBIND_LOG_INSERT_POLICY 12
#define SET_MEMPOLICY_LOG_NODEMASK_BITS_TOO_BIG 1
#define SET_MEMPOLICY_LOG_CLAMPED 2
#define SET_MEMPOLICY_LOG_DEFAULT_MASK_NOT_EMPTY 3
#define SET_MEMPOLICY_LOG_NODEMASK_NOT_SPECIFIED 4
#define SET_MEMPOLICY_LOG_NODE_TOO_LARGE 5
#define SET_MEMPOLICY_LOG_INVALID_NODEMASK 6
#define SET_MEMPOLICY_LOG_SET 7
typedef void (*syscall_rwlock_fn_t)(void *lock);
typedef int (*syscall_lookup_node_fn_t)(struct process_vm *vm, void *addr);
typedef struct vm_range *(*syscall_lookup_range_fn_t)(struct process_vm *vm,
		unsigned long start, unsigned long end);
typedef struct vm_range_numa_policy *(*syscall_policy_search_fn_t)(
		struct process_vm *vm, unsigned long addr);
typedef int (*syscall_policy_clear_range_fn_t)(struct process_vm *vm,
		unsigned long start, unsigned long end);
typedef int (*syscall_policy_insert_fn_t)(struct process_vm *vm,
		struct vm_range_numa_policy *range_policy);
typedef void (*syscall_policy_rb_clear_fn_t)(
		struct vm_range_numa_policy *range_policy);
typedef void *(*syscall_policy_alloc_fn_t)(size_t size, unsigned long flags);
typedef int (*move_pages_verify_fn_t)(struct process_vm *vm,
		unsigned long addr, size_t bytes);
typedef int (*move_pages_get_nr_nodes_fn_t)(void);
typedef int (*move_pages_smp_call_fn_t)(void *cpu_set, smp_func_t handler,
		void *arg);
typedef void (*move_pages_log_fn_t)(int event, unsigned long value,
		int error);
typedef int (*arch_prctl_set_register_fn_t)(int type, unsigned long value);
typedef int (*arch_prctl_get_register_fn_t)(int type, unsigned long *addr);
typedef void (*arch_prctl_log_fn_t)(int event, int cpu, unsigned long value);
typedef void (*arch_clone_lock_fn_t)(void *lock, void *node);
typedef unsigned long (*arch_do_fork_fn_t)(int clone_flags,
		unsigned long newsp, unsigned long parent_tidptr,
		unsigned long child_tidptr, unsigned long tls,
		unsigned long pc, unsigned long sp);
typedef int (*arch_shmget_default_huge_shift_fn_t)(void);
typedef int (*arch_do_shmget_fn_t)(long key, size_t size, int shmflg);
typedef void (*arch_shmget_log_fn_t)(int event, long key, size_t size,
		int shmflg0, int error, int shmid);
typedef int (*arch_mmap_default_huge_shift_fn_t)(void);
typedef int (*arch_mmap_overmap_fn_t)(size_t len, int pgshift);
typedef long (*arch_do_mmap_fn_t)(unsigned long addr, size_t len, int prot,
		int flags, int fd, long off, int vrf0, void *private_data);
typedef void (*arch_mmap_log_fn_t)(int event, unsigned long addr0,
		size_t len0, int prot, int flags0, int fd, long off0,
		int error, unsigned long result_addr, int extra);
#define ARCH_SHMGET_LOG_ENTER 1
#define ARCH_SHMGET_LOG_EXIT 2
#define ARCH_MMAP_LOG_ENTER 1
#define ARCH_MMAP_LOG_UNSUPPORTED_PGSIZE 2
#define ARCH_MMAP_LOG_INVALID 3
#define ARCH_MMAP_LOG_NOMEM 4
#define ARCH_MMAP_LOG_UNKNOWN_FLAGS 5
#define ARCH_MMAP_LOG_EXIT 6
#define MOVE_PAGES_LOG_UNSUPPORTED_PID 1
#define MOVE_PAGES_LOG_UNSUPPORTED_MOVE_ALL 2
#define MOVE_PAGES_LOG_INIT_MALLOC 3
#define MOVE_PAGES_LOG_INIT_VERIFY 4
#define MOVE_PAGES_LOG_PARALLEL 5
#ifndef ARCH_SET_GS
#define ARCH_SET_GS 0x1001
#define ARCH_SET_FS 0x1002
#define ARCH_GET_FS 0x1003
#define ARCH_GET_GS 0x1004
#endif
typedef long (*syscall_mckfd_lock_fn_t)(void *lock);
typedef void (*syscall_mckfd_unlock_fn_t)(void *lock, long irqstate);
typedef long (*syscall_mckfd_long_fn_t)(struct mckfd *fdp,
		ihk_mc_user_context_t *ctx);
typedef int (*syscall_mckfd_int_fn_t)(struct mckfd *fdp,
		ihk_mc_user_context_t *ctx);
typedef void (*syscall_mckfd_free_fn_t)(void *fdp);
typedef long (*syscall_tofu_ioctl_fn_t)(void *thread, int fd,
		unsigned long cmd, unsigned long arg, int *handled);
typedef void (*syscall_tofu_close_fn_t)(void *thread, int fd);
typedef unsigned long (*syscall_rdtsc_fn_t)(void);
typedef unsigned long (*syscall_ns_per_tsc_fn_t)(void);
typedef int (*syscall_has_sigpending_fn_t)(void *thread);
typedef void (*syscall_cpu_pause_fn_t)(void);
typedef void (*syscall_set_timer_fn_t)(int runq_locked);
typedef long (*syscall_atomic64_read_fn_t)(void *value);
typedef void (*syscall_atomic64_inc_fn_t)(void *value);
typedef void (*syscall_wmb_fn_t)(void);
typedef void (*syscall_panic_fn_t)(void);
typedef void (*settimeofday_log_fn_t)(int event, unsigned long utv,
		unsigned long utz, long sec, long nsec, long error);
typedef unsigned long (*syscall_pending_mask_fn_t)(void *thread);
typedef long (*syscall_signalfd_create_fn_t)(int syscall_nr, int flags);
typedef long (*syscall_signalfd_publish_fn_t)(void *thread, int fd,
		const unsigned long *mask, int create);
typedef long (*syscall_sigsuspend_fn_t)(void *thread, void *set);
typedef int (*syscall_process_vm_rw_fn_t)(int pid,
		const struct iovec *local_iov, unsigned long liovcnt,
		const struct iovec *remote_iov, unsigned long riovcnt,
		unsigned long flags, int op);
typedef long (*syscall_util_thread_fn_t)(void *arg);
typedef int (*syscall_execveat_fn_t)(void *ctx, int dirfd,
		const char *filename, char **argv, char **envp, int flags);
typedef int (*syscall_swapout_pageout_fn_t)(const char *filename,
		void *workarea, size_t size, int flag);
typedef int (*syscall_swapout_pagein_fn_t)(int flag);
typedef long (*syscall_strlen_user_fn_t)(const void *path);
typedef long (*syscall_open_special_fn_t)(const char *pathname, int flags,
		void *ctx);
typedef int (*syscall_ikc_send_fn_t)(void *channel, void *packet, int opt);
typedef int (*wait4_do_wait_fn_t)(int pid, int *status, int options,
		struct rusage *usage);
typedef int (*wait_scan_fn_t)(int pid, int *status, int options,
		void *rusage, int *empty);
typedef void (*wait_entry_init_fn_t)(void *entry, void *thread);
typedef void (*wait_prepare_fn_t)(void *waitq, void *entry, int status);
typedef void (*wait_finish_fn_t)(void *waitq, void *entry);
typedef int (*wait_has_signal_fn_t)(void *thread);
typedef void (*wait_schedule_fn_t)(void);
typedef void (*wait_log_fn_t)(int event, int current_pid, int wait_pid);
typedef int (*wait_status_fn_t)(void *thread, void *child_proc,
		void *child_thread, int *status, int options);
typedef void (*wait_lock_unlock_fn_t)(void *lock, void *node);
typedef void (*wait_thread_report_detach_fn_t)(void *thread);
typedef void (*wait_thread_side_effect_fn_t)(void *thread);
typedef int (*wait_signal_flags_reap_fn_t)(void *thread,
		unsigned long signal_flags_offset, int options, int clear_mask);
typedef int (*wait_exit_status_reap_fn_t)(void *object,
		unsigned long exit_status_offset, int options);
typedef int (*wait_host_wait4_fn_t)(int pid, int options);
typedef void (*wait_list_detach_fn_t)(void *entry);
typedef void (*wait_list_add_tail_fn_t)(void *entry, void *head);
typedef void (*wait_zombie_log_fn_t)(int event, int pid, int status,
		int ret);
typedef void (*ptrace_list_detach_fn_t)(void *entry);
typedef int (*ptrace_main_reparent_fn_t)(void *process,
		unsigned long parent_offset, void *parent, void *ptraced_entry,
		void *sibling_entry, void *children_head);
typedef int (*ptrace_report_detach_fn_t)(void *thread,
		unsigned long report_proc_offset, void *report_proc,
		void *entry);
typedef int (*ptrace_report_attach_fn_t)(void *thread,
		unsigned long termsig_offset, int update_termsig, int termsig,
		unsigned long report_proc_offset, void *report_proc,
		void *entry, void *head);
typedef void *(*ptrace_cleanup_fn_t)(void *thread,
		unsigned long ptrace_offset, unsigned long saved_valid_offset,
		unsigned long debugreg_offset);
typedef void (*ptrace_free_fn_t)(void *ptr);
typedef void (*ptrace_clear_single_step_fn_t)(void *thread);
typedef void (*ptrace_thread_exit_signal_fn_t)(void *thread);
typedef long (*ptrace_do_kill_thread_fn_t)(void *current_thread,
		int pid, int tid, int sig, const void *info, int ptracecont);
typedef void (*ptrace_wakeup_thread_fn_t)(void *thread, int valid_states);
typedef void (*ptrace_finalize_process_fn_t)(void *proc);
typedef int (*ptrace_traceme_fn_t)(void);
typedef int (*ptrace_wakeup_sig_fn_t)(int pid, long request, long data);
typedef long (*ptrace_pid_data_fn_t)(int pid, long data);
typedef long (*ptrace_pid_addr_data_fn_t)(int pid, long addr, long data);
typedef int (*ptrace_setoptions_fn_t)(int pid, int flags);
typedef int (*ptrace_attach_fn_t)(int pid);
typedef int (*ptrace_detach_fn_t)(int pid, int data);
typedef long (*ptrace_siginfo_fn_t)(int pid, siginfo_t *data);
typedef long (*ptrace_arch_fn_t)(long request, int pid, long addr,
		long data);
typedef void (*syscall_threads_lock_fn_t)(void *proc, void *lock_arg);
typedef void (*syscall_threads_unlock_fn_t)(void *proc, void *lock_arg);
typedef void (*syscall_interrupt_cpu_fn_t)(int cpu_id);
typedef void (*syscall_exit_fn_t)(int code);
typedef void (*syscall_terminate_fn_t)(int status, int group);
typedef void (*syscall_exit_group_log_fn_t)(int pid);
typedef void (*syscall_schedule_fn_t)(void);
typedef void (*thread_exit_wake_fn_t)(void *waitq);
typedef void (*thread_exit_log_fn_t)(int sig, long error);
typedef void (*finalize_wakeup_log_fn_t)(void);
typedef unsigned long (*terminate_mcexec_cmpxchg_fn_t)(unsigned long *value,
		unsigned long old_value, unsigned long new_value);
typedef long (*terminate_mcexec_syscall_fn_t)(struct syscall_request *request,
		int cpu);
typedef long (*syscall_request_call_fn_t)(struct syscall_request *request,
		int cpu);
typedef unsigned long (*syscall_virt_to_phys_fn_t)(void *addr);
typedef int *(*syscall_getcred_fn_t)(int *buf);
typedef unsigned long (*sync_child_perf_read_fn_t)(int counter_id);
typedef void (*sync_child_atomic64_set_fn_t)(void *count, long value);
typedef unsigned long (*perf_event_update_fn_t)(void *event);
typedef int (*perf_read_attr_flags_fn_t)(const void *attr,
		int *exclude_user, int *exclude_kernel, int *inherit);
typedef unsigned long (*perf_read_value_fn_t)(void *event);
typedef long (*perf_read_dispatch_fn_t)(void *event, unsigned long read_format,
		unsigned long buf_addr);
typedef void (*perf_event_void_fn_t)(void *event);
typedef int (*perf_event_int_fn_t)(void *event);
typedef int (*perf_counter_extra_set_fn_t)(void *event);
typedef int (*perf_counter_init_raw_fn_t)(int counter_id,
		unsigned long hw_config, int mode);
typedef int (*perf_counter_attr_flags_fn_t)(const void *attr,
		int *exclude_kernel, int *exclude_user);
typedef int (*perf_counter_mask_check_fn_t)(unsigned long counter_mask);
typedef int (*perf_counter_start_fn_t)(unsigned long counter_mask);
typedef int (*perf_counter_stop_fn_t)(unsigned long counter_mask, int flags);
typedef int (*perf_counter_alloc_fn_t)(void *thread, void *event);
typedef long (*perf_open_syscall_fn_t)(struct syscall_request *request,
		int cpu);
typedef int (*perf_open_event_alloc_fn_t)(void **event_out, void *attr);
typedef int (*perf_attr_freq_fn_t)(const void *attr);
typedef intptr_t (*perf_do_mmap_fn_t)(uintptr_t addr, size_t len, int prot,
		int flags, int fd, off_t off, const int vrf0,
		void *private_data);
typedef unsigned long (*perf_event_map_fn_t)(unsigned long config);
typedef int (*perf_event_validate_fn_t)(unsigned long hw_config);
typedef int (*perf_extra_reg_id_fn_t)(unsigned long hw_config,
		unsigned long hw_config_ext);
typedef unsigned int (*perf_extra_reg_msr_fn_t)(int id);
typedef int (*perf_extra_reg_idx_fn_t)(int id);
typedef int (*perf_hw_event_init_fn_t)(void *event);
typedef void (*terminate_host_ref_set_fn_t)(void *refcount, int value);
struct do_futex_log_record {
	int event;
	int flags;
	int op;
	unsigned long uaddr;
	uint32_t val;
	unsigned long utime;
	unsigned long uaddr2;
	uint32_t val3;
	int fshared;
	int ret;
	long sec;
	long nsec;
};
typedef int (*do_futex_syscall_time_fn_t)(int syscall_nr, int clock_id,
		struct timespec *ts);
typedef void (*do_futex_local_time_fn_t)(struct timespec *ts);
typedef int (*do_futex_linux_time_fn_t)(int clock_id, struct timespec *ts);
typedef unsigned long (*do_futex_ns_per_tsc_fn_t)(void);
typedef int (*do_futex_dispatch_fn_t)(unsigned long uaddr, int op,
		uint32_t val, uint64_t timeout, unsigned long uaddr2,
		uint32_t val2, uint32_t val3, int fshared);
typedef void (*do_futex_log_fn_t)(const struct do_futex_log_record *record);
typedef void (*brk_flush_fn_t)(void);
typedef unsigned long (*brk_extend_fn_t)(void *vm, unsigned long old_end,
		unsigned long address, unsigned long vrflag);
typedef void (*brk_log_fn_t)(int event, int cpu, unsigned long brk_start,
		unsigned long brk_end, unsigned long value);
typedef int (*munmap_do_fn_t)(void *addr, size_t len, int holding_lock);
typedef void (*munmap_log_fn_t)(int event, int cpu, unsigned long addr,
		size_t len, int error);
typedef void (*do_munmap_void_fn_t)(void);
typedef int (*do_munmap_remove_range_fn_t)(void *vm, unsigned long start,
		unsigned long end, int *ro_freedp);
typedef void (*do_munmap_clear_host_fn_t)(unsigned long addr, size_t len,
		int holding_lock);
typedef void (*do_munmap_log_fn_t)(unsigned long addr, size_t len,
		int error);
typedef int (*do_mmap_smaller_page_fn_t)(size_t len, int *p2alignp);
typedef void (*clear_host_pte_log_fn_t)(long error);
typedef void (*munmap_all_free_ranges_fn_t)(void *vm);
typedef void (*munmap_all_log_fn_t)(unsigned long addr, size_t len,
		int error);
typedef void (*shmdt_log_fn_t)(int event, unsigned long addr, int error);
typedef void (*shmat_void_fn_t)(void);
typedef int (*shmat_lookup_obj_fn_t)(int shmid, void **objp);
typedef void (*shmat_memobj_fn_t)(void *memobj);
typedef int (*shmat_search_fn_t)(size_t len, int pgshift,
		unsigned long *addrp);
typedef int (*shmat_add_range_fn_t)(struct process_vm *vm,
		unsigned long start, unsigned long end, unsigned long phys,
		unsigned long flags, void *memobj, long objoff, int pgshift);
typedef void (*shmat_log_fn_t)(int event, int shmid, unsigned long shmaddr,
		int shmflg, long error);
struct shmctl_offsets {
	size_t obj_memobj_offset;
	size_t obj_pgshift_offset;
	size_t obj_real_segsz_offset;
	size_t obj_user_offset;
	size_t obj_ds_offset;
	size_t obj_uid_offset;
	size_t obj_cuid_offset;
	size_t obj_gid_offset;
	size_t obj_cgid_offset;
	size_t obj_mode_offset;
	size_t obj_ctime_offset;
	size_t obj_nattch_offset;
	size_t shmlock_user_locked_offset;
	size_t shmid_ds_size;
	size_t shminfo_size;
	size_t shm_info_size;
};
typedef int (*shmctl_get_max_index_fn_t)(void);
typedef int (*shmctl_shmlock_user_get_fn_t)(uid_t ruid, void **userp);
typedef int (*shmctl_memobj_refcnt_read_fn_t)(void *memobj);
typedef void (*shmctl_log_fn_t)(int event, int shmid, int cmd,
		unsigned long buf_addr, long error);
typedef void (*search_free_space_log_fn_t)(int event, size_t len,
		int pgshift, unsigned long addr, int error);

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
#if defined(MCKERNEL_SYSCALL_POLICY_HELPERS_TEST_EXPORT)
int do_mmap_page_size_body_result(int flags,
#else
static int do_mmap_page_size_body_result(int flags,
#endif
		unsigned long vrf0, int thp_disable, size_t len,
		int *pgshiftp, int *p2alignp,
		arch_mmap_default_huge_shift_fn_t default_huge_shift_fn,
		do_mmap_smaller_page_fn_t smaller_page_fn);
#endif
typedef struct vm_range *(*syscall_next_range_fn_t)(struct process_vm *vm,
		struct vm_range *range);
typedef int (*msync_memobj_has_pager_fn_t)(void *memobj);
typedef int (*msync_range_op_fn_t)(struct process_vm *vm,
		struct vm_range *range, unsigned long start, unsigned long end);
typedef void (*msync_log_fn_t)(int event, unsigned long start, size_t len,
		int flags, int error);
typedef int (*memlock_split_fn_t)(struct process_vm *vm,
		struct vm_range *range, unsigned long addr,
		struct vm_range **new_range);
typedef int (*memlock_join_fn_t)(struct process_vm *vm,
		struct vm_range *left, struct vm_range *right);
typedef int (*memlock_populate_fn_t)(struct process_vm *vm,
		unsigned long start, size_t len);
typedef void (*mprotect_flush_fn_t)(void);
typedef int (*mprotect_change_fn_t)(struct process_vm *vm,
		struct vm_range *range, unsigned long protflags);
typedef int (*mprotect_set_host_vma_fn_t)(unsigned long start,
		size_t len, int prot, int holding_lock);
typedef int (*remap_file_pages_callable_fn_t)(void *memobj);
typedef int (*remap_file_pages_remap_fn_t)(struct process_vm *vm,
		struct vm_range *range, unsigned long start, unsigned long end,
		off_t off);
typedef void (*remap_file_pages_clear_host_fn_t)(unsigned long start,
		size_t size, int holding_lock);
typedef int (*mremap_extend_fn_t)(struct process_vm *vm,
		struct vm_range *range, unsigned long newend);
typedef int (*mremap_search_fn_t)(size_t size, unsigned long pgshift,
		unsigned long *newstartp);
typedef void (*mremap_memobj_ref_fn_t)(void *memobj);
typedef int (*mremap_add_range_fn_t)(struct process_vm *vm,
		unsigned long start, unsigned long end, long pgshift,
		unsigned long flags, void *memobj, unsigned long objoff);
typedef int (*mremap_move_pte_fn_t)(void *page_table, struct process_vm *vm,
		void *oldstart, void *newstart, size_t size,
		struct vm_range *range);
struct mprotect_log_record {
	int event;
	int cpu;
	unsigned long start;
	size_t len;
	int prot;
	unsigned long addr;
	unsigned long range_start;
	unsigned long range_end;
	unsigned long range_flags;
	unsigned long protflags;
	unsigned long denied;
	int error;
};
typedef void (*mprotect_log_fn_t)(const struct mprotect_log_record *record);
struct remap_file_pages_log_record {
	int event;
	int cpu;
	unsigned long start0;
	size_t size;
	int prot;
	size_t pgoff;
	int flags;
	unsigned long start;
	unsigned long end;
	unsigned long range_start;
	unsigned long range_end;
	unsigned long range_flags;
	void *memobj;
	long off;
	int error;
};
typedef void (*remap_file_pages_log_fn_t)(
		const struct remap_file_pages_log_record *record);
struct mremap_log_record {
	int event;
	unsigned long oldaddr;
	size_t oldsize0;
	size_t newsize0;
	int flags;
	unsigned long newaddr;
	unsigned long oldstart;
	unsigned long oldend;
	unsigned long newstart;
	unsigned long newend;
	unsigned long range_start;
	unsigned long range_end;
	unsigned long range_flags;
	unsigned long lckstart;
	unsigned long lckend;
	int error;
};
typedef void (*mremap_log_fn_t)(const struct mremap_log_record *record);
struct memlock_log_record {
	int event;
	int op;
	int cpu;
	unsigned long start;
	size_t len;
	unsigned long addr;
	unsigned long range_start;
	unsigned long range_end;
	int error;
};
typedef void (*memlock_log_fn_t)(const struct memlock_log_record *record);
typedef void *(*mincore_pte_lookup_fn_t)(void *page_table, unsigned long addr);
typedef int (*mincore_pte_present_fn_t)(void *pte);
typedef int (*mincore_memobj_lookup_fn_t)(void *memobj, unsigned long offset);
typedef long (*mincore_copy_byte_fn_t)(unsigned long dst, unsigned char value);
typedef void (*mincore_log_fn_t)(int event, unsigned long start, size_t len,
		unsigned long vec, int error);
struct ptrace_syscall_ops {
	ptrace_traceme_fn_t traceme_fn;
	ptrace_wakeup_sig_fn_t wakeup_fn;
	ptrace_pid_data_fn_t getregs_fn;
	ptrace_pid_data_fn_t setregs_fn;
	ptrace_pid_data_fn_t getfpregs_fn;
	ptrace_pid_data_fn_t setfpregs_fn;
	ptrace_pid_addr_data_fn_t peekuser_fn;
	ptrace_pid_addr_data_fn_t pokeuser_fn;
	ptrace_pid_addr_data_fn_t peektext_fn;
	ptrace_pid_addr_data_fn_t poketext_fn;
	ptrace_setoptions_fn_t setoptions_fn;
	ptrace_attach_fn_t attach_fn;
	ptrace_detach_fn_t detach_fn;
	ptrace_siginfo_fn_t getsiginfo_fn;
	ptrace_siginfo_fn_t setsiginfo_fn;
	ptrace_pid_addr_data_fn_t getregset_fn;
	ptrace_pid_addr_data_fn_t setregset_fn;
	ptrace_pid_data_fn_t geteventmsg_fn;
	ptrace_arch_fn_t arch_fn;
};
struct ptrace_io_offsets {
	size_t thread_proc_offset;
	size_t thread_status_offset;
	size_t thread_vm_offset;
	size_t thread_ptrace_offset;
	size_t thread_ptrace_eventmsg_offset;
	size_t thread_ptrace_recvsig_offset;
	size_t thread_ptrace_sendsig_offset;
	size_t thread_report_proc_offset;
	size_t thread_ptrace_saved_uctx_valid_offset;
	size_t proc_pid_offset;
	size_t proc_update_lock_offset;
};
struct ptrace_report_clone_offsets {
	size_t thread_proc_offset;
	size_t thread_tid_offset;
	size_t thread_status_offset;
	size_t thread_exit_status_offset;
	size_t thread_ptrace_offset;
	size_t thread_ptrace_eventmsg_offset;
	size_t proc_pid_offset;
	size_t proc_parent_offset;
	size_t proc_status_offset;
	size_t proc_update_lock_offset;
	size_t proc_waitpid_q_offset;
};
struct ptrace_report_exec_offsets {
	size_t thread_ptrace_offset;
	size_t thread_ctx_offset;
	size_t thread_uctx_offset;
	size_t thread_ptrace_saved_uctx_offset;
	size_t thread_ptrace_saved_uctx_valid_offset;
};
struct syscall_cputime_offsets {
	size_t thread_proc_offset;
	size_t thread_status_offset;
	size_t thread_in_kernel_offset;
	size_t thread_cpu_id_offset;
	size_t thread_times_update_offset;
	size_t thread_user_tsc_offset;
	size_t thread_system_tsc_offset;
	size_t thread_siblings_list_offset;
	size_t proc_threads_list_offset;
	size_t proc_utime_offset;
	size_t proc_stime_offset;
	size_t proc_utime_children_offset;
	size_t proc_stime_children_offset;
	size_t proc_maxrss_offset;
	size_t proc_maxrss_children_offset;
};
struct syscall_itimer_offsets {
	size_t thread_itimer_enabled_offset;
	size_t thread_itimer_virtual_offset;
	size_t thread_itimer_prof_offset;
	size_t thread_itimer_virtual_value_offset;
	size_t thread_itimer_prof_value_offset;
};
struct syscall_times_offsets {
	size_t thread_proc_offset;
	size_t thread_user_tsc_offset;
	size_t thread_system_tsc_offset;
	size_t proc_utime_offset;
	size_t proc_stime_offset;
	size_t proc_utime_children_offset;
	size_t proc_stime_children_offset;
};
struct syscall_times_tms {
	unsigned long tms_utime;
	unsigned long tms_stime;
	unsigned long tms_cutime;
	unsigned long tms_cstime;
};
struct syscall_setpgid_offsets {
	size_t thread_proc_offset;
	size_t proc_pid_offset;
	size_t proc_pgid_offset;
	size_t proc_execed_offset;
};
struct syscall_mlockall_offsets {
	size_t thread_proc_offset;
	size_t proc_euid_offset;
	size_t proc_rlimit_offset;
	size_t rlimit_entry_size;
	int memlock_resource;
};
struct syscall_mckfd_offsets {
	size_t thread_proc_offset;
	size_t proc_mckfd_lock_offset;
	size_t proc_mckfd_offset;
	size_t mckfd_next_offset;
	size_t mckfd_fd_offset;
	size_t mckfd_read_cb_offset;
	size_t mckfd_ioctl_cb_offset;
	size_t mckfd_close_cb_offset;
	size_t mckfd_fcntl_cb_offset;
};
struct wait_zombie_offsets {
	size_t thread_ptrace_offset;
	size_t proc_pid_offset;
	size_t proc_ppid_parent_offset;
	size_t proc_parent_offset;
	size_t proc_status_offset;
	size_t proc_group_exit_status_offset;
	size_t proc_nowait_offset;
	size_t proc_update_lock_offset;
	size_t proc_children_lock_offset;
	size_t proc_threads_lock_offset;
	size_t proc_siblings_list_offset;
	size_t proc_children_list_offset;
	size_t proc_main_thread_offset;
	size_t proc_stime_offset;
	size_t proc_utime_offset;
	size_t proc_stime_children_offset;
	size_t proc_utime_children_offset;
	size_t proc_maxrss_offset;
	size_t proc_maxrss_children_offset;
};
struct wait_scan_offsets {
	size_t thread_proc_offset;
	size_t thread_tid_offset;
	size_t thread_status_offset;
	size_t thread_ptrace_offset;
	size_t thread_signal_flags_offset;
	size_t thread_termsig_offset;
	size_t thread_report_siblings_list_offset;
	size_t thread_siblings_list_offset;
	size_t proc_pid_offset;
	size_t proc_pgid_offset;
	size_t proc_status_offset;
	size_t proc_children_lock_offset;
	size_t proc_threads_lock_offset;
	size_t proc_children_list_offset;
	size_t proc_ptraced_children_list_offset;
	size_t proc_siblings_list_offset;
	size_t proc_ptraced_siblings_list_offset;
	size_t proc_report_threads_list_offset;
	size_t proc_threads_list_offset;
	size_t proc_main_thread_offset;
};
struct ptrace_detach_offsets {
	size_t thread_proc_offset;
	size_t thread_termsig_offset;
	size_t thread_status_offset;
	size_t thread_tid_offset;
	size_t thread_report_proc_offset;
	size_t thread_report_siblings_list_offset;
	size_t thread_ptrace_offset;
	size_t thread_ptrace_saved_uctx_valid_offset;
	size_t thread_ptrace_debugreg_offset;
	size_t proc_pid_offset;
	size_t proc_status_offset;
	size_t proc_parent_offset;
	size_t proc_ppid_parent_offset;
	size_t proc_main_thread_offset;
	size_t proc_children_lock_offset;
	size_t proc_threads_lock_offset;
	size_t proc_children_list_offset;
	size_t proc_siblings_list_offset;
	size_t proc_ptraced_siblings_list_offset;
	size_t proc_report_threads_list_offset;
};

#define DO_FUTEX_LOG_ENTER 1
#define DO_FUTEX_LOG_TIMEOUT 2
#define DO_FUTEX_LOG_ABSOLUTE_TIME 3
#define DO_FUTEX_LOG_EXIT 4
#define BRK_LOG_ENTER 1
#define BRK_LOG_SET_END 2
#define MUNMAP_LOG_ENTER 1
#define MUNMAP_LOG_EXIT 2
#define MUNMAP_LOG_ERROR 3
#define SHMDT_LOG_ENTER 1
#define SHMDT_LOG_INVALID 2
#define SHMDT_LOG_EXIT 3
#define SHMAT_LOG_ENTER 1
#define SHMAT_LOG_LOOKUP_FAILED 2
#define SHMAT_LOG_INVALID_ADDR 3
#define SHMAT_LOG_ACCESS_FAILED 4
#define SHMAT_LOG_RANGE_BUSY 5
#define SHMAT_LOG_SEARCH_FAILED 6
#define SHMAT_LOG_SET_HOST_FAILED 7
#define SHMAT_LOG_ADD_FAILED 8
#define SHMAT_LOG_EXIT 9
#define SHMCTL_LOG_ENTER 1
#define SHMCTL_LOG_LOOKUP 2
#define SHMCTL_LOG_EPERM 3
#define SHMCTL_LOG_COPY 4
#define SHMCTL_LOG_EXIT 5
#define SHMCTL_LOG_EACCES 6
#define SHMCTL_LOG_PERM_SHM 7
#define SHMCTL_LOG_PERM_PROC 8
#define SHMCTL_LOG_USER_LOOKUP 9
#define SHMCTL_LOG_TOO_LARGE 10
#define SHMCTL_LOG_EINVAL 11
#define SEARCH_FREE_SPACE_LOG_ENTER 1
#define SEARCH_FREE_SPACE_LOG_OUTSIDE 2
#define SEARCH_FREE_SPACE_LOG_EXIT 3
#define MSYNC_LOG_ENTER 1
#define MSYNC_LOG_INVALID_ARGS 2
#define MSYNC_LOG_INVALID_VMR 3
#define MSYNC_LOG_LOCKED_VMR 4
#define MSYNC_LOG_UNSYNCABLE_VMR 5
#define MSYNC_LOG_SYNC_FAILED 6
#define MSYNC_LOG_INVALIDATE_FAILED 7
#define MSYNC_LOG_EXIT 8
#define MEMLOCK_OP_LOCK 1
#define MEMLOCK_OP_UNLOCK 2
#define MEMLOCK_LOG_ENTER 1
#define MEMLOCK_LOG_NOT_CONTIG 2
#define MEMLOCK_LOG_CANNOT_CHANGE 3
#define MEMLOCK_LOG_SPLIT_FAILED 4
#define MEMLOCK_LOG_JOIN_FAILED 5
#define MEMLOCK_LOG_POPULATE_FAILED 6
#define MEMLOCK_LOG_EXIT 7
#define MPROTECT_LOG_ENTER 1
#define MPROTECT_LOG_INVALID_RANGE 2
#define MPROTECT_LOG_STRAIGHT_IGNORED 3
#define MPROTECT_LOG_NOT_CONTIG 4
#define MPROTECT_LOG_DENIED 5
#define MPROTECT_LOG_CANNOT_CHANGE 6
#define MPROTECT_LOG_SPLIT_FAILED 7
#define MPROTECT_LOG_CHANGE_FAILED 8
#define MPROTECT_LOG_JOIN_FAILED 9
#define MPROTECT_LOG_SET_HOST_FAILED 10
#define MPROTECT_LOG_EXIT 11
#define REMAP_FILE_PAGES_LOG_ENTER 1
#define REMAP_FILE_PAGES_LOG_INVALID_ARGS 2
#define REMAP_FILE_PAGES_LOG_INVALID_VMR 3
#define REMAP_FILE_PAGES_LOG_REMAP_FAILED 4
#define REMAP_FILE_PAGES_LOG_POPULATE_FAILED 5
#define REMAP_FILE_PAGES_LOG_EXIT 6
#define MREMAP_LOG_ENTER 1
#define MREMAP_LOG_STRAIGHT_REJECT 2
#define MREMAP_LOG_INVALID 3
#define MREMAP_LOG_ALLOCATE_FAILED 4
#define MREMAP_LOG_LOOKUP_FAILED 5
#define MREMAP_LOG_FIXED_MIN_ADDR 6
#define MREMAP_LOG_FIXED_OVERLAP 7
#define MREMAP_LOG_CANNOT_RELOCATE 8
#define MREMAP_LOG_SEARCH_FAILED 9
#define MREMAP_LOG_FIXED_MUNMAP_FAILED 10
#define MREMAP_LOG_ADD_FAILED 11
#define MREMAP_LOG_SPLIT_FAILED 12
#define MREMAP_LOG_MOVE_FAILED 13
#define MREMAP_LOG_RELOCATE_MUNMAP_FAILED 14
#define MREMAP_LOG_SHRINK_MUNMAP_FAILED 15
#define MREMAP_LOG_POPULATE_FAILED 16
#define MREMAP_LOG_EXIT 17
#define MINCORE_LOG_INVALID 1
#define MINCORE_LOG_LOOKUP_FAILED 2
#define MINCORE_LOG_COPY_FAILED 3
#define MINCORE_LOG_EXIT 4
long syscall_copy_from_user_bridge(void *dst_addr,
		unsigned long src_addr, size_t bytes);
long syscall_copy_to_user_bridge(unsigned long dst_addr,
		const void *src, size_t bytes);
static long syscall_do_syscall2_bridge(int syscall_nr, unsigned long arg0,
		unsigned long arg1);
static long syscall_do_syscall3_bridge(int syscall_nr, unsigned long arg0,
		unsigned long arg1, unsigned long arg2);
long syscall_policy_do_syscall3_bridge(int syscall_nr, unsigned long arg0,
		unsigned long arg1, unsigned long arg2);
static long syscall_do_syscall_request_bridge(struct syscall_request *request,
		int cpu);
static unsigned long syscall_virt_to_phys_bridge(void *addr);
static long syscall_forward_context_bridge(int syscall_nr, void *ctx);
void syscall_tsc_to_ts_bridge(unsigned long tsc, void *ts);
unsigned long syscall_timespec_to_jiffy_bridge(const void *ts);
void syscall_ts_add_bridge(void *dst, const void *src);
void *syscall_find_process_bridge(int pid, void *lock_arg);
void syscall_process_unlock_bridge(void *proc, void *lock_arg);
long syscall_do_prlimit64_bridge(int pid, int resource,
		unsigned long new_limit_addr, unsigned long old_limit_addr);
int syscall_get_processor_id_bridge(void);
int syscall_get_numa_id_bridge(void);
void syscall_mlockall_log_bridge(int flags, int error);
void syscall_munlockall_log_bridge(int value, int error);
long syscall_mckfd_lock_bridge(void *lock);
void syscall_mckfd_unlock_bridge(void *lock, long irqstate);
void *syscall_alloc_bridge(size_t size, unsigned long flags);
void syscall_mckfd_free_bridge(void *fdp);
long syscall_tofu_ioctl_bridge(void *thread, int fd,
		unsigned long cmd, unsigned long arg, int *handled);
void syscall_tofu_close_bridge(void *thread, int fd);
void syscall_gettime_bridge(void *ts);
unsigned long syscall_rdtsc_bridge(void);
unsigned long syscall_ns_per_tsc_bridge(void);
int syscall_has_sigpending_bridge(void *thread);
long syscall_do_kill_thread_bridge(void *thread, int pid, int tid,
		int sig, const void *info, int ptracecont);
void syscall_kill_log_bridge(int event, int pid, int sig, int error);
void syscall_threads_reader_lock_bridge(void *proc, void *lock_arg);
void syscall_threads_reader_unlock_bridge(void *proc, void *lock_arg);
void syscall_interrupt_cpu_bridge(int cpu_id);
void syscall_cpu_pause_bridge(void);
long syscall_sigsuspend_bridge(void *thread, void *set);
void syscall_set_timer_bridge(int runq_locked);
unsigned long sched_find_thread_bridge(int pid);
void sched_thread_unlock_bridge(unsigned long thread_addr);
long sched_yield_lock_bridge(void *lock);
void sched_yield_unlock_bridge(void *lock, long irqstate);
void sched_yield_schedule_bridge(void);

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
extern int robust_list_len_result(size_t len);
extern long set_robust_list_body_result(size_t len);
extern int tkill_tid_result(int tid);
extern int tgkill_target_result(int tgid, int tid);
extern int sigaction_validate(int sig, int has_act);
extern int rt_sigprocmask_validate(size_t sigsetsize,
		size_t expected_sigset_size, int has_set, int how);
extern unsigned long rt_sigprocmask_apply(unsigned long current_mask,
		unsigned long set_mask, int has_set, int how);
extern long rt_sigprocmask_body_result(int how, unsigned long set_addr,
		unsigned long oldset_addr, size_t sigsetsize,
		size_t expected_sigset_size, void *thread,
		size_t sigmask_offset, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_forward_sigmask_fn_t forward_fn);
extern int rt_sigpending_size_result(size_t sigsetsize,
		size_t expected_sigset_size);
extern int signalfd4_sigsetsize_result(size_t sigsetsize,
		size_t expected_sigset_size);
extern int signalfd4_flags_result(int flags);
extern long signalfd_body_result(void);
extern long syscall_temp_sigmask_body_result(unsigned long set_addr,
		void *thread, size_t sigmask_offset, int syscall_nr, void *ctx,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_forward_context_fn_t forward_fn);
extern long pselect6_sigmask_body_result(unsigned long set_ptr_addr,
		void *thread, size_t sigmask_offset, int syscall_nr, void *ctx,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_forward_context_fn_t forward_fn);
extern long rt_sigpending_body_result(unsigned long set_addr,
		size_t sigsetsize, size_t expected_sigset_size, void *thread,
		syscall_pending_mask_fn_t pending_mask_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
extern long signalfd4_body_result(int fd, unsigned long mask_addr,
		size_t sigsetsize, size_t expected_sigset_size, int flags,
		void *thread, int syscall_nr,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_signalfd_create_fn_t create_fn,
		syscall_signalfd_publish_fn_t publish_fn);
extern int syscall_refresh_cred_needed_result(long rc);
extern int syscall_getpid_result(int pid);
extern int syscall_getppid_result(int ppid);
extern int syscall_gettid_result(int tid);
extern int syscall_set_tid_address_return_result(int pid);
extern long syscall_getpid_body_result(void *thread, size_t proc_offset,
		size_t pid_offset);
extern long syscall_getppid_body_result(void *thread, size_t proc_offset,
		size_t ppid_parent_offset, size_t pid_offset);
extern long syscall_gettid_body_result(void *thread, size_t tid_offset);
extern long syscall_set_tid_address_body_result(void *thread,
		size_t clear_child_tid_offset, size_t proc_offset,
		size_t pid_offset, int *clear_child_tid);
extern long syscall_get_process_id_field_result(void *thread,
		size_t proc_offset, size_t field_offset);
extern long syscall_getresid_body_result(void *thread, size_t proc_offset,
		size_t first_offset, size_t second_offset,
		size_t third_offset, unsigned long first_user_addr,
		unsigned long second_user_addr, unsigned long third_user_addr,
		syscall_copy_int_to_user_fn_t copy_int_fn);
extern long syscall_kill_body_result(void *thread, size_t proc_offset,
		size_t pid_offset, int pid, int sig,
		syscall_do_kill_thread_fn_t do_kill_fn);
extern long syscall_tgkill_body_result(void *thread, size_t proc_offset,
		size_t pid_offset, int tgid, int tid, int sig,
		syscall_do_kill_thread_fn_t do_kill_fn);
extern long syscall_tkill_body_result(void *thread, size_t proc_offset,
		size_t pid_offset, int tid, int sig,
		syscall_do_kill_thread_fn_t do_kill_fn);
extern long syscall_forward_refresh_cred_body_result(int syscall_nr, void *ctx,
		syscall_forward_context_fn_t forward_fn,
		syscall_refresh_cred_fn_t refresh_fn);
extern unsigned long syscall_setfsid_body_result(int id, int syscall_nr,
		syscall_do_syscall2_fn_t do_syscall_fn,
		syscall_refresh_cred_fn_t refresh_fn);
extern int *getcred_body_result(int *raw_buf, unsigned long page_mask,
		int syscall_nr, syscall_virt_to_phys_fn_t virt_to_phys_fn,
		syscall_get_cpu_fn_t processor_id_fn,
		syscall_request_call_fn_t do_syscall_fn);
extern int syscall_refresh_cred_fields_body_result(void *thread, int *scratch,
		size_t thread_proc_offset, size_t field0_offset,
		size_t field1_offset, size_t field2_offset,
		size_t field3_offset, size_t value0_index,
		size_t value1_index, size_t value2_index,
		size_t value3_index, syscall_getcred_fn_t getcred_fn);
extern long syscall_times_body_result(void *thread, unsigned long buf_addr,
		int gettime_local_support,
		const struct syscall_times_offsets *offsets,
		syscall_tsc_to_ts_fn_t tsc_to_ts_fn,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_ts_add_fn_t ts_add_fn, syscall_gettime_fn_t gettime_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
extern int syscall_use_requester_tid_result(int syscall_nr, unsigned long arg0,
		int sched_setaffinity_nr);
extern int syscall_target_tid_result(int use_requester_tid, int current_tid);
extern int syscall_send_prepare_result(struct syscall_request *req,
		struct syscall_response *res);
extern int syscall_request_copy_result(struct syscall_request *dst,
		const struct syscall_request *src);
extern int syscall_request_publish_result(struct syscall_request *req);
extern long syscall_generic_forwarding_body_result(struct syscall_request *req,
		int n, unsigned long arg0, unsigned long arg1,
		unsigned long arg2, unsigned long arg3, unsigned long arg4,
		unsigned long arg5, int cpu, syscall_request_call_fn_t do_syscall_fn);
extern int syscall_packet_traditional_prepare_result(
		struct ikc_scd_packet *packet, int msg, int cpu_ref, int pid,
		unsigned long resp_pa);
extern int syscall_eventfd_packet_prepare_result(
		struct ikc_scd_packet *packet, int msg, int eventfd_type);
extern int syscall_eventfd_send_result(void *channel, int msg,
		int eventfd_type, syscall_ikc_send_fn_t send_fn);
extern int syscall_log_budget_result(int pid, int *last_pidp,
		int *log_countp, int limit);
extern int syscall_reject_after_exit_result(int process_status,
		int syscall_nr, int exit_nr, int exit_group_nr);
extern int syscall_offload_spin_without_schedule_result(int no_preempt,
		int tid);
extern int syscall_offload_prepare_result(struct syscall_request *req,
		struct syscall_response *res, int current_tid, int syscall_nr,
		unsigned long arg0, int sched_setaffinity_nr,
		unsigned long spinning_status);
extern int syscall_preempt_disable_needed_result(int rtid);
extern int syscall_proxy_dead_result(long rc);
extern int syscall_tofu_post_reply_candidate_result(int syscall_nr,
		long rc, int ioctl_nr, int openat_nr);
extern int syscall_profile_event_needed_result(int syscall_nr,
		int profile_max);
extern int syscall_offload_counted_result(int syscall_nr, int exit_group_nr);
extern int syscall_nested_dispatch_valid_result(int syscall_nr,
		int syscall_count, int has_handler);
extern int syscall_nested_rt_sigaction_index_result(int sig, int nsig);
extern int syscall_nested_response_prepare_result(struct syscall_request *req,
		struct syscall_response *res, unsigned long response_nr,
		unsigned long syscall_ret, int current_tid, int service_tid,
		unsigned long spinning_status);
extern int setpgid_normalize_pid(int current_pid, int pid);
extern int setpgid_normalize_pgid(int pid, int pgid);
extern int setpgid_execed_result(int execed);
extern long syscall_setpgid_body_result(void *thread, int pid, int pgid,
		int syscall_nr, void *ctx,
		const struct syscall_setpgid_offsets *offsets, void *lock_arg,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn);
extern long syscall_setrlimit_body_result(int resource,
		unsigned long new_limit_addr,
		syscall_do_prlimit64_fn_t do_prlimit_fn);
extern long syscall_getrlimit_body_result(int resource,
		unsigned long old_limit_addr,
		syscall_do_prlimit64_fn_t do_prlimit_fn);
extern long syscall_prlimit64_body_result(int pid, int resource,
		unsigned long new_limit_addr, unsigned long old_limit_addr,
		syscall_do_prlimit64_fn_t do_prlimit_fn);
extern long syscall_sysinfo_body_result(unsigned long sysinfo_addr,
		unsigned long totalram, unsigned long freeram,
		syscall_copy_to_user_fn_t copy_to_fn);
extern long syscall_get_cpu_id_body_result(syscall_get_cpu_fn_t get_cpu_fn);
extern long syscall_mlockall_body_result(void *thread, int flags,
		const struct syscall_mlockall_offsets *offsets,
		syscall_log_int_fn_t log_fn);
extern long syscall_munlockall_body_result(syscall_log_int_fn_t log_fn);
extern long syscall_getcpu_body_result(unsigned long cpup_addr,
		unsigned long nodep_addr, int cpu, int node,
		syscall_copy_to_user_fn_t copy_to_fn);
extern long syscall_read_body_result(void *thread, int fd, int syscall_nr,
		void *ctx, const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn);
extern long syscall_ioctl_body_result(void *thread, int fd,
		unsigned long cmd, unsigned long arg, int syscall_nr, void *ctx,
		const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn,
		syscall_tofu_ioctl_fn_t tofu_fn);
extern long syscall_fcntl_body_result(void *thread, int fd, int syscall_nr,
		void *ctx, const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn);
extern long syscall_close_body_result(void *thread, int fd, int syscall_nr,
		void *ctx, const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn,
		syscall_tofu_close_fn_t close_path_fn,
		syscall_mckfd_free_fn_t free_fn);
extern long do_mmap_mckfd_dispatch_body_result(void *thread, int flags,
		int fd, void *ctx, int *handledp,
		const struct syscall_mckfd_offsets *offsets,
		size_t mckfd_mmap_cb_offset,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn);
extern int do_mmap_page_size_body_result(int flags, unsigned long vrf0,
		int thp_disable, size_t len, int *pgshiftp, int *p2alignp,
		arch_mmap_default_huge_shift_fn_t default_huge_shift_fn,
		do_mmap_smaller_page_fn_t smaller_page_fn);
extern int memlock_prepare_range(uintptr_t start0, size_t len0,
		uintptr_t user_start, uintptr_t user_end,
		uintptr_t *startp, size_t *lenp, uintptr_t *endp);
extern int memlock_range_flag_result(unsigned long flag);
extern int memlock_body_result(void *vm, void *range_lock,
		unsigned long start0, size_t len0, unsigned long user_start,
		unsigned long user_end, int op, int cpu,
		size_t range_start_offset, size_t range_end_offset,
		size_t range_flag_offset, size_t range_memobj_offset,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn, memlock_split_fn_t split_fn,
		memlock_join_fn_t join_fn, memlock_populate_fn_t populate_fn,
		memlock_log_fn_t log_fn);
extern int range_has_disallowed_change_flags(unsigned long flag);
extern int munmap_prepare_range(uintptr_t addr, size_t len0,
		uintptr_t user_start, uintptr_t user_end, size_t *lenp);
extern int munmap_body_result(void *vm, void *range_lock, unsigned long addr,
		size_t len0, unsigned long user_start, unsigned long user_end,
		int cpu, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn, munmap_do_fn_t do_munmap_fn,
		munmap_log_fn_t log_fn);
extern int shmdt_body_result(void *vm, void *range_lock,
		unsigned long shmaddr, size_t range_start_offset,
		size_t range_end_offset, size_t range_memobj_offset,
		size_t memobj_flags_offset, unsigned long shmdt_ok_flag,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		munmap_do_fn_t do_munmap_fn, shmdt_log_fn_t log_fn);
extern int do_munmap_body_result(void *vm, void *proc, unsigned long addr,
		size_t len, int holding_memory_range_lock,
		size_t proc_straight_va_offset,
		size_t proc_straight_len_offset,
		do_munmap_void_fn_t begin_fn,
		do_munmap_remove_range_fn_t remove_range_fn,
		do_munmap_clear_host_fn_t clear_host_pte_fn,
		mprotect_set_host_vma_fn_t set_host_vma_fn,
		do_munmap_void_fn_t finish_fn, do_munmap_log_fn_t log_fn);
extern long clear_host_pte_body_result(void *vm, unsigned long addr,
		size_t len, int holding_memory_range_lock,
		size_t vm_lock_taken_offset, int cpu, int syscall_nr,
		syscall_do_syscall3_fn_t forward_fn,
		clear_host_pte_log_fn_t log_fn);
extern void munmap_all_body_result(void *vm, void *range_lock, void *region,
		size_t range_start_offset, size_t range_end_offset,
		size_t region_map_start_offset, size_t region_map_end_offset,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn, munmap_do_fn_t do_munmap_fn,
		munmap_all_free_ranges_fn_t free_ranges_fn,
		munmap_all_log_fn_t log_fn);
extern long shmat_body_result(int shmid, unsigned long shmaddr,
		int shmflg, uid_t proc_euid, gid_t proc_egid, void *vm,
		void *range_lock, size_t obj_pgshift_offset,
		size_t obj_real_segsz_offset, size_t obj_memobj_offset,
		size_t obj_uid_offset, size_t obj_cuid_offset,
		size_t obj_gid_offset, size_t obj_cgid_offset,
		size_t obj_mode_offset, shmat_void_fn_t list_lock_fn,
		shmat_void_fn_t list_unlock_fn,
		shmat_lookup_obj_fn_t lookup_obj_fn,
		shmat_memobj_fn_t memobj_unref_fn,
		syscall_rwlock_fn_t range_lock_fn,
		syscall_rwlock_fn_t range_unlock_fn,
		syscall_lookup_range_fn_t lookup_range_fn,
		shmat_search_fn_t search_free_fn,
		mprotect_set_host_vma_fn_t set_host_vma_fn,
		shmat_add_range_fn_t add_range_fn,
		shmat_log_fn_t log_fn);
extern long shmctl_body_result(int shmid, int cmd, unsigned long buf_addr,
		uid_t proc_euid, gid_t proc_egid, uid_t proc_ruid,
		unsigned long rlim_memlock_cur, long now,
		int has_cap_sys_admin, int has_cap_ipc_lock,
		const struct shmctl_offsets *offsets, const void *shminfo,
		const void *shm_info, shmat_void_fn_t list_lock_fn,
		shmat_void_fn_t list_unlock_fn,
		shmat_lookup_obj_fn_t lookup_obj_fn,
		shmat_lookup_obj_fn_t lookup_by_index_fn,
		shmat_memobj_fn_t memobj_unref_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		shmctl_get_max_index_fn_t get_max_index_fn,
		shmat_void_fn_t users_lock_fn,
		shmat_void_fn_t users_unlock_fn,
		shmctl_shmlock_user_get_fn_t shmlock_user_get_fn,
		shmat_memobj_fn_t shmlock_user_free_fn,
		shmctl_memobj_refcnt_read_fn_t memobj_refcnt_read_fn,
		shmctl_log_fn_t log_fn);
extern int search_free_space_body_result(void *vm, void *region,
		size_t len, int pgshift, unsigned long *addrp,
		size_t region_user_end_offset, size_t region_map_end_offset,
		size_t range_end_offset, syscall_lookup_range_fn_t lookup_fn,
		search_free_space_log_fn_t log_fn);
extern int set_host_vma_body_result(unsigned long addr, size_t len,
		int prot, int holding_memory_range_lock);
extern int mprotect_prepare_range(uintptr_t start, size_t len0,
		uintptr_t user_start, uintptr_t user_end,
		size_t *lenp, uintptr_t *endp);
extern void mprotect_split_needed_result(unsigned long range_start,
		unsigned long range_end, unsigned long addr, unsigned long end,
		int *split_startp, int *split_endp);
extern int mprotect_write_changed_result(unsigned long range_flags,
		unsigned long protflags);
extern int mprotect_body_result(void *vm, void *range_lock,
		unsigned long start, size_t len0, int prot,
		unsigned long user_start, unsigned long user_end,
		unsigned long straight_va, size_t straight_len, int cpu,
		size_t range_start_offset, size_t range_end_offset,
		size_t range_flag_offset, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn, memlock_split_fn_t split_fn,
		memlock_join_fn_t join_fn, mprotect_change_fn_t change_fn,
		mprotect_set_host_vma_fn_t set_host_vma_fn,
		mprotect_flush_fn_t flush_nfo_fn,
		mprotect_flush_fn_t flush_tlb_fn,
		mprotect_log_fn_t log_fn);
extern int mlockall_policy_result(int flags, int is_privileged,
		unsigned long memlock_cur);
extern int remap_file_pages_prepare(uintptr_t start0, size_t size, int prot,
		size_t pgoff, uintptr_t *startp, uintptr_t *endp, off_t *offp);
extern int remap_file_pages_body_result(void *vm, void *range_lock,
		unsigned long start0, size_t size, int prot, size_t pgoff,
		int flags, int cpu, size_t range_start_offset,
		size_t range_end_offset, size_t range_flag_offset,
		size_t range_memobj_offset, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		remap_file_pages_callable_fn_t callable_fn,
		remap_file_pages_remap_fn_t remap_fn,
		remap_file_pages_clear_host_fn_t clear_host_fn,
		memlock_populate_fn_t populate_fn,
		mprotect_flush_fn_t flush_nfo_fn,
		remap_file_pages_log_fn_t log_fn);
extern int mremap_prepare_args(uintptr_t oldaddr, size_t oldsize0,
		size_t newsize0, int flags, uintptr_t newaddr,
		uintptr_t user_start, uintptr_t user_end,
		size_t *oldsizep, size_t *newsizep, uintptr_t *oldendp,
		int *no_opp);
extern int mremap_fixed_range_result(uintptr_t newstart,
		uintptr_t user_start, uintptr_t oldstart, uintptr_t oldend,
		uintptr_t newend);
extern int mremap_maymove_result(int flags);
extern long mremap_body_result(void *vm, void *range_lock, void *pte_lock,
		void *page_table, unsigned long oldaddr, size_t oldsize0,
		size_t newsize0, int flags, unsigned long newaddr,
		unsigned long user_start, unsigned long user_end,
		unsigned long straight_va, size_t straight_len,
		size_t range_start_offset, size_t range_end_offset,
		size_t range_flag_offset, size_t range_pgshift_offset,
		size_t range_memobj_offset, size_t range_objoff_offset,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		mremap_extend_fn_t extend_fn, mprotect_flush_fn_t flush_nfo_fn,
		mremap_search_fn_t search_fn, munmap_do_fn_t munmap_fn,
		mremap_memobj_ref_fn_t memobj_ref_fn,
		mremap_memobj_ref_fn_t memobj_unref_fn,
		mremap_add_range_fn_t add_range_fn,
		syscall_rwlock_fn_t pte_lock_fn,
		syscall_rwlock_fn_t pte_unlock_fn,
		memlock_split_fn_t split_fn, mremap_move_pte_fn_t move_pte_fn,
		memlock_populate_fn_t populate_fn, mremap_log_fn_t log_fn);
extern int msync_prepare_range(uintptr_t start0, size_t len0, int flags,
		size_t *lenp, uintptr_t *endp);
extern int msync_locked_range_result(int flags, unsigned long range_flags);
extern int msync_body_result(void *vm, void *range_lock, unsigned long start0,
		size_t len0, int flags, size_t range_start_offset,
		size_t range_end_offset, size_t range_flag_offset,
		size_t range_memobj_offset, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn,
		msync_memobj_has_pager_fn_t has_pager_fn,
		msync_range_op_fn_t sync_fn, msync_range_op_fn_t invalidate_fn,
		msync_log_fn_t log_fn);
extern int mbind_prepare_range(uintptr_t addr, unsigned long len0,
		unsigned long *lenp);
extern int mempolicy_nodemask_bits_result(unsigned long maxnode,
		unsigned long *nodemask_bitsp);
extern int mempolicy_nodemask_bits_is_clamped(unsigned long maxnode);
extern int mbind_mode_flags_result(int mode, unsigned int flags,
		int *mode_flagsp, int *normalized_modep);
extern int mempolicy_mode_is_supported(int mode);
extern int set_mempolicy_normalize_mode(int mode, int *normalized_modep);
extern long mbind_body_result(unsigned long addr, unsigned long len0,
		int mode, unsigned long nodemask_addr, unsigned long maxnode,
		int flags, struct process_vm *vm, int straight_va,
		int fugaku_hacks, int nr_numa_nodes, size_t policy_size,
		unsigned long alloc_flags, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_rwlock_fn_t write_lock_fn,
		syscall_rwlock_fn_t write_unlock_fn,
		syscall_lookup_range_fn_t lookup_range_fn,
		syscall_policy_search_fn_t policy_search_fn,
		syscall_policy_clear_range_fn_t clear_range_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_policy_rb_clear_fn_t rb_clear_fn,
		syscall_policy_insert_fn_t insert_fn,
		syscall_mbind_log_fn_t log_fn);
extern long set_mempolicy_body_result(int mode, unsigned long nodemask_addr,
		unsigned long maxnode, struct process_vm *vm, int nr_numa_nodes,
		int pid, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_set_mempolicy_log_fn_t log_fn);
extern int get_mempolicy_validate(unsigned long addr, int flags,
		int process_policy, unsigned long maxnode, int nr_numa_nodes,
		unsigned long *nodemask_bitsp);
extern long get_mempolicy_body_result(unsigned long mode_addr,
		unsigned long nodemask_addr, unsigned long maxnode,
		unsigned long addr, int flags, struct process_vm *vm,
		int nr_numa_nodes, syscall_copy_to_user_fn_t copy_to_fn,
		syscall_lookup_node_fn_t lookup_node_fn,
		syscall_rwlock_fn_t read_lock_fn,
		syscall_rwlock_fn_t read_unlock_fn,
		syscall_lookup_range_fn_t lookup_range_fn,
		syscall_policy_search_fn_t policy_search_fn,
		syscall_get_mempolicy_log_fn_t log_fn);
extern int move_pages_policy_result(int pid, int flags);
extern int move_pages_smp_req_prepare_result(struct move_pages_smp_req *req,
		unsigned long count, const void **user_virt_addr,
		int *user_status, const int *user_nodes, void **virt_addr,
		int *status, pte_t **ptep, int *nodes, int *nr_pages,
		unsigned long *dst_phys, void *proc);
extern long move_pages_body_result(int pid, unsigned long count,
		unsigned long user_virt_addr_addr, unsigned long user_nodes_addr,
		unsigned long user_status_addr, int flags, struct process_vm *vm,
		void *page_table_lock, void *cpu_set, void *proc,
		unsigned long alloc_flags, size_t ptr_size, size_t int_size,
		size_t pte_size, size_t ulong_size,
		move_pages_verify_fn_t verify_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn,
		move_pages_get_nr_nodes_fn_t get_nr_nodes_fn,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		move_pages_smp_call_fn_t smp_call_fn, smp_func_t handler_fn,
		syscall_rdtsc_fn_t rdtsc_fn, move_pages_log_fn_t log_fn);
extern int brk_prepare_result(unsigned long address, unsigned long brk_start,
		unsigned long brk_end, unsigned long brk_end_allocated,
		unsigned long *resultp, int *extend_neededp);
extern unsigned long brk_default_vrflags(void);
extern unsigned long brk_body_result(void *vm, void *region,
		void *range_lock, unsigned long address, int cpu,
		size_t brk_start_offset, size_t brk_end_offset,
		size_t brk_end_allocated_offset, brk_flush_fn_t flush_fn,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		brk_extend_fn_t extend_fn, brk_log_fn_t log_fn);
extern int mincore_prepare_range(uintptr_t start, size_t len,
		uintptr_t user_start, uintptr_t user_end, uintptr_t *endp);
extern long mincore_body_result(void *vm, void *range_lock, void *pte_lock,
		void *page_table, unsigned long start, size_t len,
		unsigned long vec_addr, unsigned long user_start,
		unsigned long user_end, size_t range_start_offset,
		size_t range_end_offset, size_t range_memobj_offset,
		size_t range_objoff_offset, syscall_rwlock_fn_t range_lock_fn,
		syscall_rwlock_fn_t range_unlock_fn,
		syscall_rwlock_fn_t pte_lock_fn,
		syscall_rwlock_fn_t pte_unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		mincore_pte_lookup_fn_t pte_lookup_fn,
		mincore_pte_present_fn_t pte_present_fn,
		mincore_memobj_lookup_fn_t memobj_lookup_fn,
		mincore_copy_byte_fn_t copy_byte_fn, mincore_log_fn_t log_fn);
extern unsigned long mmap_base_vrflags(int prot, int flags,
		unsigned long vrf0, int anon_on_demand);
extern int mmap_populated_mapping_result(int flags);
extern int mmap_should_set_host_ro(int flags, int prot, int anonymous_only);
extern int mmap_update_private_maxprot(int flags, int maxprot);
extern int mmap_prot_denied_result(int prot, int maxprot, int *deniedp);
extern unsigned long mmap_maxprot_to_vrflags(int maxprot);
extern int mmap_should_force_straight(int flags, int straight_map,
		unsigned long phys, size_t len, size_t threshold);
extern int mmap_is_shared(int flags);
extern int getrusage_who_result(int who);
extern int itimer_which_result(int which);
extern int itimer_is_real(int which);
extern int itimer_should_start(long value_sec, long value_usec);
extern void itimer_snapshot_current_result(unsigned long timer_addr,
		unsigned long elapsed_addr, unsigned long out_addr);
extern long setitimer_body_result(int which, unsigned long new_addr,
		unsigned long old_addr, void *thread,
		const struct syscall_itimer_offsets *offsets, int syscall_nr,
		syscall_do_syscall3_fn_t syscall3_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_set_timer_fn_t set_timer_fn);
extern long getitimer_body_result(int which, unsigned long old_addr,
		void *thread, const struct syscall_itimer_offsets *offsets,
		int syscall_nr, syscall_do_syscall2_fn_t syscall2_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
extern int clock_gettime_dispatch(int clock_id, int local_support, int has_ts);
extern int gettimeofday_dispatch(int has_tv, int has_tz, int local_support);
extern long gettimeofday_body_result(unsigned long tv_addr,
		unsigned long tz_addr, int local_support, int syscall_nr,
		syscall_gettime_fn_t gettime_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_do_syscall2_fn_t syscall2_fn);
extern long settimeofday_body_result(unsigned long utv_addr,
		unsigned long utz_addr, int local_support,
		unsigned long clocks_per_sec, int syscall_nr, void *ctx,
		void *lock_arg, void *version_arg, struct timespec *origin,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_rdtsc_fn_t rdtsc_fn,
		syscall_forward_context_fn_t forward_fn,
		syscall_atomic64_read_fn_t atomic_read_fn,
		syscall_atomic64_inc_fn_t atomic_inc_fn, syscall_wmb_fn_t wmb_fn,
		syscall_panic_fn_t panic_fn, settimeofday_log_fn_t log_fn);
extern int nanosleep_validate_timespec(long sec, long nsec);
extern long nanosleep_body_result(unsigned long tv_addr,
		unsigned long rem_addr, int local_support, int syscall_nr,
		void *thread, void *monitor, size_t monitor_status_offset,
		int heavy_status, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_do_syscall2_fn_t syscall2_fn, syscall_rdtsc_fn_t rdtsc_fn,
		syscall_ns_per_tsc_fn_t ns_per_tsc_fn,
		syscall_has_sigpending_fn_t has_sigpending_fn,
		syscall_cpu_pause_fn_t cpu_pause_fn);
extern int rt_sigtimedwait_prepare(size_t sigsetsize,
		size_t expected_sigset_size, int has_set);
extern int rt_sigtimedwait_timeout_result(long sec, long nsec,
		int local_support);
extern void rt_sigtimedwait_prepare_masks(unsigned long raw_wait_mask,
		unsigned long current_mask, unsigned long *wait_maskp,
		unsigned long *blocked_maskp, unsigned long *interrupt_maskp);
extern void rt_sigtimedwait_deadline(long now_sec, long now_nsec,
		long timeout_sec, long timeout_nsec, long *deadline_secp,
		long *deadline_nsecp);
extern int rt_sigtimedwait_timeout_expired(long now_sec, long now_nsec,
		long deadline_sec, long deadline_nsec);
extern int sigmask_to_signal_number(unsigned long mask);
extern int signal_pending_deliverable_result(int delflag, int sig,
		unsigned long handler_addr, unsigned long pending_mask,
		unsigned long blocked_mask);
extern int signal_pending_interrupt_action_result(int sig,
		unsigned long handler_addr, unsigned long pending_mask,
		unsigned long blocked_mask, int interrupted);
extern int rt_sigqueueinfo_pid_result(int pid);
extern long rt_sigqueueinfo_body_result(int pid, int sig,
		unsigned long info_addr, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_do_kill_fn_t do_kill_fn);
extern int sigsuspend_sigsetsize_result(size_t sigsetsize,
		size_t expected_sigset_size);
extern unsigned long sigsuspend_prepare_mask(unsigned long raw_mask);
extern int sigsuspend_pending_matches(unsigned long pending_mask,
		unsigned long suspend_mask);
extern long pause_body_result(void *thread, size_t sigmask_offset,
		syscall_sigsuspend_fn_t suspend_fn);
extern long rt_sigsuspend_body_result(void *thread, unsigned long set_addr,
		size_t sigsetsize, size_t expected_sigset_size,
		void *scratch_sigset, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_sigsuspend_fn_t suspend_fn);
extern int sigaction_sigsetsize_result(size_t sigsetsize,
		size_t expected_sigset_size);
extern int do_sigaction_body_result(int sig, const struct k_sigaction *act,
		struct k_sigaction *oact, void *sigcommon,
		size_t action_offset, size_t action_stride,
		size_t lock_offset, void *lock_node,
		syscall_sigcommon_lock_fn_t lock_fn,
		syscall_sigcommon_lock_fn_t unlock_fn,
		syscall_sigaction_forward_fn_t forward_fn);
extern long rt_sigaction_body_result(int sig, unsigned long act_addr,
		unsigned long oact_addr, size_t sigsetsize,
		size_t expected_sigset_size,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_sigaction_fn_t sigaction_fn);
extern int sigaltstack_validate(int flags, size_t size);
extern int sigaltstack_is_disable(int flags);
extern long sigaltstack_body_result(void *thread, size_t sigstack_offset,
		unsigned long ss_addr, unsigned long oss_addr,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
extern int process_vm_validate_args(unsigned long flags,
		unsigned long liovcnt, unsigned long riovcnt);
extern int process_vm_op_is_write(int op);
extern int process_vm_op_is_valid(int op);
extern long process_vm_rw_body_result(int pid, const struct iovec *local_iov,
		unsigned long liovcnt, const struct iovec *remote_iov,
		unsigned long riovcnt, unsigned long flags, int op,
		syscall_process_vm_rw_fn_t rw_fn);
extern long prctl_body_result(int option, unsigned long arg2,
		unsigned long arg3, unsigned long arg4, unsigned long arg5,
		void *proc, size_t thp_disable_offset, int syscall_nr, void *ctx,
		syscall_forward_context_fn_t forward_fn);
extern int arch_prctl_type_result(unsigned long code, int *typep);
extern long arch_prctl_body_result(unsigned long code, unsigned long address,
		void *thread, size_t tlsblock_base_offset,
		syscall_get_cpu_fn_t get_cpu_fn,
		arch_prctl_set_register_fn_t set_register_fn,
		arch_prctl_get_register_fn_t get_register_fn,
		arch_prctl_log_fn_t log_fn);
extern unsigned long arch_clone_body_result(void *proc,
		size_t coredump_lock_offset, void *lock_node, int clone_flags,
		unsigned long newsp, unsigned long parent_tidptr,
		unsigned long child_tidptr, unsigned long tls, unsigned long pc,
		unsigned long sp, arch_clone_lock_fn_t lock_fn,
		arch_clone_lock_fn_t unlock_fn, arch_do_fork_fn_t fork_fn);
extern unsigned long arch_fork_body_result(unsigned long pc, unsigned long sp,
		arch_do_fork_fn_t fork_fn);
extern unsigned long arch_vfork_body_result(unsigned long pc, unsigned long sp,
		arch_do_fork_fn_t fork_fn);
extern long arch_time_body_result(long now, unsigned long tloc_addr,
		syscall_copy_to_user_fn_t copy_to_fn);
extern long arch_shmget_body_result(long key, size_t size, int shmflg0,
		arch_shmget_default_huge_shift_fn_t default_huge_shift_fn,
		arch_do_shmget_fn_t do_shmget_fn,
		arch_shmget_log_fn_t log_fn);
extern long arch_mmap_body_result(unsigned long addr0, size_t len0,
		int prot, int flags0, int fd, long off0,
		unsigned long user_start, unsigned long user_end,
		int supported_flags, int ignored_flags, int error_flags,
		arch_mmap_default_huge_shift_fn_t default_huge_shift_fn,
		arch_mmap_overmap_fn_t overmap_fn,
		arch_do_mmap_fn_t do_mmap_fn, arch_mmap_log_fn_t log_fn);
extern long migrate_pages_body_result(void);
extern long madvise_body_result(unsigned long start, size_t len, int advice);
extern long get_system_body_result(void);
extern long perf_event_open_disabled_body_result(void);
extern long linux_mlock_body_result(unsigned long addr, size_t len,
		int syscall_nr, syscall_do_syscall2_fn_t syscall2_fn);
extern long linux_spawn_body_result(int syscall_nr, void *ctx,
		syscall_forward_context_fn_t forward_fn);
extern long swapout_body_result(const char *filename, void *workarea,
		size_t size, int flag, int syscall_nr, void *linux_ctx,
		syscall_swapout_pageout_fn_t pageout_fn,
		syscall_swapout_pagein_fn_t pagein_fn,
		syscall_forward_context_fn_t forward_fn);
extern long open_common_body_result(unsigned long pathname_addr, int flags,
		int syscall_nr, void *ctx, const char *xpmem_dev_path,
		unsigned long alloc_flags, syscall_strlen_user_fn_t strlen_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn,
		syscall_open_special_fn_t special_open_fn,
		syscall_forward_context_fn_t forward_fn);
extern long util_migrate_inter_kernel_body_result(unsigned long arg_addr,
		void *scratch_attr, size_t attr_size,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_util_thread_fn_t util_thread_fn);
extern long util_indicate_clone_body_result(void *thread, int mode,
		unsigned long arg_addr, size_t attr_size,
		unsigned long alloc_flags, size_t thread_proc_offset,
		size_t proc_enable_uti_offset, size_t thread_mod_clone_offset,
		size_t thread_mod_clone_arg_offset,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn);
extern long util_register_desc_body_result(unsigned long desc,
		unsigned long *desc_store);
extern long threads_signal_body_result(void *current_thread, int signal,
		int wait_stopped, size_t thread_proc_offset,
		size_t proc_pid_offset, size_t proc_threads_list_offset,
		size_t thread_tid_offset, size_t thread_status_offset,
		size_t thread_siblings_list_offset,
		syscall_do_kill_thread_fn_t do_kill_fn,
		syscall_cpu_pause_fn_t pause_fn);
extern int ptrace_signal_data_result(long data);
extern int ptrace_detach_signal_result(long data);
extern int ptrace_user_area_result(long addr, unsigned long user_struct_size);
extern int ptrace_status_allows_io(int status);
extern int ptrace_setoptions_flags_result(int flags);
extern int ptrace_apply_options(int current, int flags);
extern int ptrace_setoptions_apply_thread_result(unsigned long thread_addr,
		unsigned long ptrace_offset, int flags);
extern int ptrace_child_traced_result(int has_child, int has_proc, int ptrace);
extern int ptrace_attach_policy_result(int tracer_pid, int target_pid,
		int target_ptrace, int same_process);
extern int ptrace_attach_mark_traced_result(unsigned long thread_addr,
		unsigned long ptrace_offset);
extern int ptrace_detach_state_result(int is_traced, int same_report_proc);
extern int ptrace_siginfo_state_result(int status, int has_siginfo);
extern int ptrace_eventmsg_state_result(int status);
extern int ptrace_eventmsg_prepare_result(int status, unsigned long eventmsg,
		unsigned long *outp);
extern int ptrace_wakeup_request_action_result(long request);
extern int ptrace_resume_single_step_result(long request);
extern int ptrace_resume_trace_syscall_result(long request);
extern int ptrace_resume_signal_needed_result(long request, long data);
extern int ptrace_resume_signal_source_result(long request, int has_sendsig,
		int has_recvsig);
extern int ptrace_detach_forward_signal_needed_result(int data);
extern int ptrace_detach_exit_signal_needed_result(int status);
extern int ptrace_detach_thread_body_result(void *thread, int data,
		void *current_thread, void *current_proc, void *pid1,
		const struct ptrace_detach_offsets *offsets,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		ptrace_list_detach_fn_t list_detach_fn,
		ptrace_main_reparent_fn_t main_reparent_fn,
		ptrace_report_detach_fn_t report_detach_fn,
		ptrace_cleanup_fn_t cleanup_fn,
		ptrace_free_fn_t free_fn,
		ptrace_clear_single_step_fn_t clear_single_step_fn,
		ptrace_report_attach_fn_t report_attach_fn,
		ptrace_thread_exit_signal_fn_t exit_signal_fn,
		ptrace_do_kill_thread_fn_t do_kill_fn,
		ptrace_wakeup_thread_fn_t wakeup_fn,
		wait_thread_side_effect_fn_t release_fn,
		ptrace_finalize_process_fn_t finalize_fn,
		void *lock_node);
extern int ptrace_setsiginfo_target_result(int status, int has_sendsig,
		int has_recvsig);
extern int ptrace_getsiginfo_prepare_result(int status,
		unsigned long pending_addr, unsigned long info_offset,
		void *outp, size_t info_size);
extern int ptrace_setsiginfo_store_result(unsigned long thread_addr,
		unsigned long sendsig_offset, unsigned long recvsig_offset,
		unsigned long info_offset, int target,
		unsigned long allocated_sendsig, const void *infop,
		size_t info_size);
extern long ptrace_read_user_words_result(unsigned long thread_addr,
		unsigned long *outp, size_t bytes,
		ptrace_read_user_word_fn_t read_fn);
extern long ptrace_write_user_words_result(unsigned long thread_addr,
		const unsigned long *inp, size_t bytes,
		ptrace_write_user_word_fn_t write_fn);
extern long ptrace_read_user_word_result(int status, unsigned long thread_addr,
		long user_area_offset, unsigned long *outp,
		ptrace_read_user_word_fn_t read_fn);
extern long ptrace_write_user_word_result(int status, unsigned long thread_addr,
		long user_area_offset, unsigned long value,
		ptrace_write_user_word_fn_t write_fn);
extern long ptrace_read_vm_word_result(int status, unsigned long vm_addr,
		unsigned long user_addr, unsigned long *outp,
		ptrace_read_vm_word_fn_t read_fn);
extern long ptrace_write_vm_word_result(int status, unsigned long vm_addr,
		unsigned long user_addr, unsigned long value,
		ptrace_write_vm_word_fn_t write_fn);
extern long ptrace_fpregs_io_result(int status, unsigned long thread_addr,
		unsigned long data_addr, ptrace_fpregs_io_fn_t io_fn);
extern long ptrace_regset_io_result(int status, unsigned long thread_addr,
		long type, unsigned long user_iovec_addr, void *iovp,
		size_t iov_size, size_t iov_len_offset, size_t iov_len_size,
		ptrace_user_copy_from_fn_t copy_from_fn,
		ptrace_regset_io_fn_t io_fn,
		ptrace_user_copy_to_fn_t copy_to_fn);
extern long ptrace_pokeuser_body_result(int pid, long addr, long data,
		unsigned long user_struct_size,
		const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_write_user_word_fn_t write_fn);
extern long ptrace_peekuser_body_result(int pid, long addr, long data,
		unsigned long user_struct_size,
		const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_read_user_word_fn_t read_fn,
		ptrace_user_copy_to_fn_t copy_to_fn);
extern long ptrace_getregs_body_result(int pid, long data, void *scratch,
		size_t regs_size, const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_read_user_word_fn_t read_fn,
		ptrace_user_copy_to_fn_t copy_to_fn);
extern long ptrace_setregs_body_result(int pid, long data, void *scratch,
		size_t regs_size, const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_write_user_word_fn_t write_fn,
		ptrace_user_copy_from_fn_t copy_from_fn);
extern long ptrace_fpregs_body_result(int pid, long data,
		const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_fpregs_io_fn_t io_fn);
extern long ptrace_regset_body_result(int pid, long type, long data,
		void *iovp, size_t iov_size, size_t iov_len_offset,
		size_t iov_len_size, const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_user_copy_from_fn_t copy_from_fn,
		ptrace_regset_io_fn_t io_fn,
		ptrace_user_copy_to_fn_t copy_to_fn);
extern long ptrace_peektext_body_result(int pid, long addr, long data,
		const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_read_vm_word_fn_t read_fn,
		ptrace_user_copy_to_fn_t copy_to_fn,
		ptrace_text_log_fn_t log_fn);
extern long ptrace_poketext_body_result(int pid, long addr, long data,
		const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_write_vm_word_fn_t write_fn,
		ptrace_text_log_fn_t log_fn);
extern long ptrace_geteventmsg_body_result(int pid, long data,
		size_t word_size, const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_user_copy_to_fn_t copy_to_fn);
extern long ptrace_getsiginfo_body_result(int pid, unsigned long data,
		void *scratch, size_t info_size, unsigned long info_offset,
		const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_user_copy_to_fn_t copy_to_fn);
extern long ptrace_setsiginfo_body_result(int pid, unsigned long data,
		void *scratch, size_t info_size, size_t pending_size,
		unsigned long alloc_flags, unsigned long info_offset,
		const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		ptrace_user_copy_from_fn_t copy_from_fn);
extern int ptrace_wakeup_sig_body_result(int pid, long request, long data,
		unsigned long current_thread, unsigned long info_offset,
		const struct ptrace_io_offsets *offsets, void *lock_node,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_control_log_fn_t log_fn,
		ptrace_saved_context_clear_fn_t clear_saved_fn,
		ptrace_set_single_step_fn_t set_single_step_fn,
		ptrace_rwlock_fn_t lock_fn,
		ptrace_trace_syscall_update_fn_t trace_syscall_update_fn,
		ptrace_rwlock_fn_t unlock_lock_fn,
		ptrace_pending_signal_take_fn_t take_pending_fn,
		ptrace_free_fn_t free_fn,
		ptrace_do_kill_thread_fn_t do_kill_fn,
		ptrace_wakeup_thread_fn_t wakeup_fn);
extern int ptrace_report_clone_body_result(void *thread, void *new_thread,
		int event, void *current_thread,
		const struct ptrace_report_clone_offsets *offsets,
		void *lock_node, void *new_lock_node,
		ptrace_rwlock_fn_t lock_fn,
		ptrace_rwlock_fn_t unlock_fn,
		ptrace_attach_thread_fn_t attach_fn,
		ptrace_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn,
		ptrace_control_log_fn_t log_fn);
extern int ptrace_syscall_event_body_result(void *thread,
		size_t thread_ptrace_offset,
		ptrace_report_signal_fn_t report_signal_fn);
extern int ptrace_report_exec_body_result(void *thread, void *syscall_ctx,
		const struct ptrace_report_exec_offsets *offsets,
		size_t kernel_context_size, size_t user_context_size,
		void *kernel_context_scratch,
		ptrace_void_fn_t preempt_enable_fn,
		ptrace_void_fn_t preempt_disable_fn,
		ptrace_report_signal_fn_t report_signal_fn,
		ptrace_arch_syscall_event_fn_t arch_syscall_event_fn);
extern int ptrace_setoptions_body_result(int pid, int flags,
		const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_control_log_fn_t log_fn);
extern int ptrace_attach_body_result(int pid, unsigned long current_thread,
		unsigned long current_proc, const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_attach_thread_fn_t attach_fn,
		ptrace_do_kill_thread_fn_t do_kill_fn,
		ptrace_control_log_fn_t log_fn);
extern int ptrace_detach_body_result(int pid, int data,
		unsigned long current_proc, const struct ptrace_io_offsets *offsets,
		ptrace_find_thread_fn_t find_fn,
		ptrace_thread_unlock_fn_t unlock_fn,
		ptrace_detach_call_fn_t detach_fn);
extern int ptrace_request_dispatch_result(long request);
extern long ptrace_syscall_body_result(long request, int pid, long addr,
		long data, const struct ptrace_syscall_ops *ops);
extern int wait4_options_result(int options);
extern int waitid_to_wait_pid_result(int idtype, int id, int *pidp);
extern int waitid_options_result(int options);
extern int wait_should_scan_process_result(int options);
extern int wait_should_scan_thread_result(int pid, int options);
extern int wait_process_pid_matches_result(int pid, int parent_pgid,
		int child_pgid, int child_pid);
extern int wait_thread_tid_matches_result(int tid, int child_tid,
		int is_main_thread);
extern int wait_process_exited_candidate_result(int options,
		int child_status);
extern int wait_thread_exited_candidate_result(int options, int child_status);
extern int wait_nonptraced_stop_candidate_result(int ptrace, int signal_flags,
		int options);
extern int wait_ptraced_stop_candidate_result(int ptrace, int status);
extern int wait_continued_candidate_result(int signal_flags, int options);
extern int wait_reap_needed_result(int options);
extern int wait_nohang_result(int options);
extern int wait_empty_result(int empty);
extern int wait_stopped_status_result(int exit_status);
extern int wait_continued_status_result(void);
extern int wait_continued_body_result(struct thread *c_thread,
		struct process *child, int *status, int options,
		unsigned long child_pid_offset,
		unsigned long child_main_thread_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_signal_flags_offset,
		wait_signal_flags_reap_fn_t reap_fn);
extern int wait_stopped_body_result(struct thread *c_thread,
		struct process *child, int *status, int options,
		unsigned long child_pid_offset,
		unsigned long child_status_offset,
		unsigned long child_group_exit_status_offset,
		unsigned long child_main_thread_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_exit_status_offset,
		wait_exit_status_reap_fn_t reap_fn);
extern int do_wait_body_result(int pid, int *status, int options,
		void *rusage, void *thread, void *wait_entry,
		unsigned long thread_proc_offset,
		unsigned long proc_pid_offset,
		unsigned long proc_waitpid_q_offset,
		int interruptible_status,
		wait_scan_fn_t wait_proc_fn,
		wait_scan_fn_t wait_thread_fn,
		wait_entry_init_fn_t init_fn,
		wait_prepare_fn_t prepare_fn,
		wait_finish_fn_t finish_fn,
		wait_has_signal_fn_t has_signal_fn,
		wait_schedule_fn_t schedule_fn,
		wait_log_fn_t log_fn);
extern int wait_process_candidate_body_result(int current_ret, int pid,
		int *status, int options, void *thread, void *child_proc,
		void *child_thread, void *parent_children_lock,
		void *parent_children_lock_node, void *child_threads_lock,
		void *child_threads_lock_node, unsigned long child_pid_offset,
		unsigned long child_status_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_ptrace_offset,
		unsigned long thread_signal_flags_offset,
		wait_status_fn_t stopped_fn,
		wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		wait_lock_unlock_fn_t unlock_fn,
		int *foundp);
extern int wait_thread_candidate_body_result(int current_ret, int tid,
		int *status, int options, void *thread, void *child_thread,
		void *threads_lock, void *threads_lock_node,
		unsigned long thread_proc_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_status_offset,
		unsigned long thread_ptrace_offset,
		unsigned long thread_signal_flags_offset,
		wait_status_fn_t stopped_fn,
		wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_thread_report_detach_fn_t report_detach_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_fn,
		int *foundp);
extern int wait_process_zombie_body_result(void *thread, void *parent_proc,
		void *child_proc, int *status, int options, void *rusage,
		void *parent_children_lock, void *parent_children_lock_node,
		void *pid1, const struct wait_zombie_offsets *offsets,
		wait_host_wait4_fn_t host_wait4_fn,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_list_detach_fn_t list_detach_fn,
		wait_list_add_tail_fn_t list_add_tail_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_process_fn,
		wait_zombie_log_fn_t log_fn, void *parent_update_lock_node,
		void *child_update_lock_node, void *pid1_children_lock_node,
		void *child_threads_lock_node);
extern int wait_process_scan_body_result(int pid, int *status, int options,
		void *rusage, int *empty, void *thread, void *proc, void *pid1,
		const struct wait_scan_offsets *scan_offsets,
		const struct wait_zombie_offsets *zombie_offsets,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_host_wait4_fn_t host_wait4_fn,
		wait_list_detach_fn_t list_detach_fn,
		wait_list_add_tail_fn_t list_add_tail_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_process_fn,
		wait_zombie_log_fn_t zombie_log_fn,
		wait_status_fn_t stopped_fn,
		wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		void *parent_children_lock_node,
		void *child_threads_lock_node,
		void *parent_update_lock_node,
		void *child_update_lock_node,
		void *pid1_children_lock_node);
extern int wait_thread_scan_body_result(int tid, int *status, int options,
		void *rusage, int *empty, void *thread, void *proc,
		const struct wait_scan_offsets *offsets,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_status_fn_t stopped_fn,
		wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		wait_thread_report_detach_fn_t report_detach_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_fn,
		void *threads_lock_node);
extern int wait_zombie_skip_host_result(int ppid_parent_pid,
		int current_pid, int nowait);
extern int wait_thread_empty_candidate_result(int is_main_thread, int termsig);
extern int waitid_status_code_result(int status);
extern int wait_stopped_source_result(int has_c_thread,
		int c_thread_exit_status, int child_status,
		int child_group_exit_status, int main_thread_exit_status);
extern int wait_stopped_exit_status_result(int source,
		int c_thread_exit_status, int child_group_exit_status,
		int main_thread_exit_status);
extern int wait_report_id_result(int source, int child_pid, int c_thread_tid);
extern int wait_reaped_exit_status_result(int options, int exit_status);
extern int wait_reaped_signal_flags_result(int options, int signal_flags,
		int clear_mask);
extern int wait_process_reparent_needed_result(int options,
		int parent_is_ppid);
extern int wait_main_thread_ptrace_detach_needed_result(int options,
		int ptrace);
extern int wait_thread_reap_action_result(int options, int ptrace);
extern int wait_status_copy_needed_result(int rc, int has_status);
extern int wait_rusage_copy_needed_result(int has_rusage);
extern long wait4_body_result(int pid, unsigned long status_addr, int options,
		unsigned long rusage_addr, wait4_do_wait_fn_t do_wait_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
extern int waitid_siginfo_needed_result(int rc, int has_infop);
extern void waitid_copy_siginfo_result(int rc, unsigned long infop_addr,
		int status, long utime_sec, long utime_usec,
		long stime_sec, long stime_usec,
		syscall_copy_to_user_fn_t copy_to_fn);
extern long waitid_body_result(int idtype, int id, unsigned long infop_addr,
		int options, wait4_do_wait_fn_t do_wait_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
extern int getrusage_dispatch_result(int who);
extern int getrusage_thread_update_action_result(int is_current_thread,
		int status, int in_kernel);
extern int getrusage_thread_times_update_prepare_result(
		unsigned long thread_addr, unsigned long times_update_offset,
		int update_action);
extern long getrusage_maxrss_kb_result(long maxrss);
extern void getrusage_timespec_add_tsc_result(long *secp, long *nsecp,
		unsigned long tsc, unsigned long clocks_per_sec);
extern void getrusage_fill_timespec_result(struct rusage *usage,
		long utime_sec, long utime_nsec, long stime_sec,
		long stime_nsec, long maxrss);
extern long getrusage_body_result(int who, unsigned long usage_addr,
		void *thread, unsigned long clocks_per_sec,
		const struct syscall_cputime_offsets *offsets,
		syscall_threads_lock_fn_t lock_fn,
		syscall_threads_unlock_fn_t unlock_fn, void *lock_arg,
		syscall_interrupt_cpu_fn_t interrupt_fn,
		syscall_cpu_pause_fn_t pause_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
extern long clock_gettime_body_result(int clock_id, unsigned long ts_addr,
		int local_support, int syscall_nr, void *thread,
		unsigned long clocks_per_sec,
		const struct syscall_cputime_offsets *offsets,
		syscall_gettime_fn_t gettime_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_do_syscall2_fn_t syscall2_fn,
		syscall_threads_lock_fn_t lock_fn,
		syscall_threads_unlock_fn_t unlock_fn, void *lock_arg,
		syscall_interrupt_cpu_fn_t interrupt_fn,
		syscall_cpu_pause_fn_t pause_fn);
extern int exit_code_status_result(int code);
extern int exit_code_signal_result(int code);
extern int exit_syscall_code_result(int status);
extern long exit_body_result(int status, syscall_exit_fn_t exit_fn);
extern long exit_group_body_result(int status, int pid,
		syscall_exit_group_log_fn_t log_fn,
		syscall_terminate_fn_t terminate_fn);
extern long sched_yield_body_result(void *cpu_local, size_t flags_offset,
		size_t runq_len_offset, size_t runq_lock_offset,
		unsigned int need_resched_flag,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_schedule_fn_t schedule_fn);
extern int thread_exit_signal_result(int ptrace, int termsig);
extern int thread_exit_signal_report_needed_result(const void *report_proc);
extern int sigchld_code_result(int exit_status);
extern long thread_exit_signal_body_result(void *thread,
		size_t thread_report_proc_offset, size_t thread_ptrace_offset,
		size_t thread_termsig_offset,
		size_t thread_exit_status_offset, size_t thread_tid_offset,
		size_t thread_user_tsc_offset, size_t thread_system_tsc_offset,
		size_t proc_pid_offset, size_t proc_waitpid_q_offset,
		syscall_tsc_to_ts_fn_t tsc_to_ts_fn,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn, thread_exit_log_fn_t log_fn);
extern long finalize_process_parent_notify_body_result(void *proc,
		size_t proc_parent_offset, size_t proc_pid_offset,
		size_t proc_group_exit_status_offset, size_t proc_termsig_offset,
		size_t proc_utime_offset, size_t proc_stime_offset,
		size_t proc_waitpid_q_offset,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn, thread_exit_log_fn_t log_fn);
extern long finalize_process_body_result(void *proc, const void *pid1,
		void *lock_node, size_t proc_parent_offset,
		size_t proc_status_offset, size_t proc_update_lock_offset,
		size_t proc_pid_offset, size_t proc_group_exit_status_offset,
		size_t proc_termsig_offset, size_t proc_utime_offset,
		size_t proc_stime_offset, size_t proc_waitpid_q_offset,
		wait_lock_unlock_fn_t lock_fn, wait_lock_unlock_fn_t unlock_fn,
		wait_thread_side_effect_fn_t release_fn,
		finalize_wakeup_log_fn_t wakeup_log_fn,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn, thread_exit_log_fn_t log_fn);
extern int exit_group_status_claimed_result(unsigned long old_exit_status);
extern int terminate_group_status_update_failed_result(
		unsigned long observed_status, unsigned long expected_status);
extern int terminate_host_exit_needed_result(int nohost);
extern long terminate_mcexec_body_result(void *proc,
		struct syscall_request *request, int rc, int sig, int cpu,
		int exit_group_nr, size_t proc_group_exit_status_offset,
		size_t proc_nohost_offset,
		terminate_mcexec_cmpxchg_fn_t cmpxchg_fn,
		terminate_mcexec_syscall_fn_t syscall_fn);
extern int sync_child_event_needed_result(int has_event, int inherit,
		int pid);
extern int sync_child_event_pid_action_result(int pid);
extern long sync_child_event_body_result(void *event, int inherit, int pid,
		size_t group_leader_offset, size_t event_pid_offset,
		size_t counter_id_offset, size_t count_offset,
		size_t child_count_total_offset, size_t sibling_list_offset,
		size_t group_entry_offset, sync_child_perf_read_fn_t read_fn,
		sync_child_atomic64_set_fn_t set_fn);
extern unsigned long perf_event_read_value_body_result(void *event,
		void *thread, int exclude_user, int exclude_kernel, int inherit,
		size_t event_pid_offset, size_t use_invariant_tsc_offset,
		size_t count_offset, size_t child_count_total_offset,
		size_t base_user_tsc_offset, size_t stopped_user_tsc_offset,
		size_t user_accum_count_offset, size_t base_system_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset,
		size_t thread_user_tsc_offset, size_t thread_system_tsc_offset,
		perf_event_update_fn_t update_fn,
		syscall_atomic64_read_fn_t atomic_read_fn);
extern unsigned long perf_event_read_value_entry_body_result(void *event,
		void *thread, size_t event_attr_offset,
		size_t event_pid_offset, size_t use_invariant_tsc_offset,
		size_t count_offset, size_t child_count_total_offset,
		size_t base_user_tsc_offset, size_t stopped_user_tsc_offset,
		size_t user_accum_count_offset, size_t base_system_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset,
		size_t thread_user_tsc_offset, size_t thread_system_tsc_offset,
		perf_read_attr_flags_fn_t attr_flags_fn,
		perf_event_update_fn_t update_fn,
		syscall_atomic64_read_fn_t atomic_read_fn);
extern long perf_event_read_one_body_result(void *event,
		unsigned long buf_addr, perf_read_value_fn_t read_value_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
extern long perf_event_read_group_body_result(void *event,
		unsigned long buf_addr, size_t group_leader_offset,
		size_t nr_siblings_offset, size_t sibling_list_offset,
		size_t group_entry_offset, perf_read_value_fn_t read_value_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
extern long perf_read_body_result(void *event, unsigned long buf_addr,
		unsigned long read_format, unsigned long group_flag,
		perf_read_dispatch_fn_t read_group_fn,
		perf_read_dispatch_fn_t read_one_fn);
extern int perf_counter_set_body_result(void *event, int exclude_kernel,
		int exclude_user, int counter_id, unsigned long hw_config,
		size_t extra_reg_reg_offset, int kernel_mode, int user_mode,
		perf_counter_extra_set_fn_t set_extra_fn,
		perf_counter_init_raw_fn_t init_raw_fn);
extern int perf_counter_set_entry_body_result(void *event,
		size_t event_attr_offset, size_t event_counter_id_offset,
		size_t event_hw_config_offset, size_t extra_reg_reg_offset,
		int kernel_mode, int user_mode,
		perf_counter_attr_flags_fn_t attr_flags_fn,
		perf_counter_extra_set_fn_t set_extra_fn,
		perf_counter_init_raw_fn_t init_raw_fn);
extern long perf_start_body_result(void *event, void *thread,
		size_t group_leader_offset, size_t sibling_list_offset,
		size_t group_entry_offset, size_t counter_id_offset,
		size_t state_offset, size_t use_invariant_tsc_offset,
		size_t base_user_tsc_offset, size_t stopped_user_tsc_offset,
		size_t user_accum_count_offset, size_t base_system_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset, size_t thread_user_tsc_offset,
		size_t thread_system_tsc_offset, size_t thread_proc_offset,
		size_t proc_perf_status_offset, int inactive_state,
		int active_state, int pp_count,
		perf_counter_mask_check_fn_t mask_check_fn,
		perf_event_int_fn_t set_period_fn,
		perf_event_int_fn_t counter_set_fn,
		perf_counter_start_fn_t counter_start_fn);
extern long perf_reset_body_result(void *event, void *thread,
		size_t group_leader_offset, size_t sibling_list_offset,
		size_t group_entry_offset, size_t counter_id_offset,
		size_t use_invariant_tsc_offset,
		size_t base_user_tsc_offset, size_t stopped_user_tsc_offset,
		size_t user_accum_count_offset, size_t base_system_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset, size_t count_offset,
		size_t thread_user_tsc_offset, size_t thread_system_tsc_offset,
		perf_counter_mask_check_fn_t mask_check_fn,
		perf_read_value_fn_t read_value_fn,
		sync_child_atomic64_set_fn_t atomic_set_fn);
extern long perf_stop_body_result(void *event, void *thread,
		size_t group_leader_offset, size_t sibling_list_offset,
		size_t group_entry_offset, size_t counter_id_offset,
		size_t state_offset, size_t use_invariant_tsc_offset,
		size_t stopped_user_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t thread_user_tsc_offset, size_t thread_system_tsc_offset,
		size_t thread_proc_offset,
		size_t proc_monitoring_event_offset,
		size_t proc_perf_status_offset, int active_state,
		int inactive_state, int pp_none, int stop_flags,
		perf_counter_mask_check_fn_t mask_check_fn,
		perf_counter_stop_fn_t counter_stop_fn,
		perf_event_update_fn_t update_fn);
extern long perf_ioctl_body_result(void *event, void *current_proc,
		void *lock_arg, unsigned long cmd, int inherit,
		unsigned long enable_cmd, unsigned long disable_cmd,
		unsigned long reset_cmd, unsigned long refresh_cmd,
		int pp_reset, size_t event_pid_offset,
		size_t proc_monitoring_event_offset,
		size_t proc_perf_status_offset, perf_event_void_fn_t start_fn,
		perf_event_void_fn_t stop_fn, perf_event_void_fn_t reset_fn,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn);
extern long perf_close_body_result(void *event, void *thread,
		size_t counter_id_offset, size_t extra_reg_reg_offset,
		size_t extra_reg_idx_offset, size_t thread_pmc_alloc_map_offset,
		size_t thread_extra_reg_alloc_map_offset,
		syscall_mckfd_free_fn_t free_fn);
extern long perf_fcntl_body_result(void *sfd, void *ctx, int cmd,
		long arg, int fcntl_nr, int set_sig_cmd, int setown_ex_cmd,
		size_t mckfd_sig_no_offset,
		syscall_forward_context_fn_t forward_fn);
extern long perf_mmap_body_result(unsigned long addr0, size_t len0,
		int prot, int flags, int fd, long off0, int map_anonymous,
		int prot_write, size_t data_head_offset,
		size_t capabilities_offset, unsigned long cap_user_rdpmc_mask,
		perf_do_mmap_fn_t do_mmap_fn);
extern int perf_event_open_validate_body_result(int cpu, unsigned long flags,
		unsigned long attr_type, unsigned long read_format, int freq,
		unsigned long sample_period, unsigned long raw_type,
		unsigned long hardware_type, unsigned long hw_cache_type,
		unsigned long unsupported_read_format_mask,
		unsigned long sample_period_sign_bit);
extern long perf_event_alloc_init_body_result(void *event, const void *attr,
		size_t event_size, size_t attr_size,
		size_t event_attr_offset, size_t group_entry_offset,
		size_t sibling_list_offset, size_t sample_freq_offset,
		size_t nr_siblings_offset, size_t count_offset,
		size_t child_count_total_offset, size_t parent_offset,
		size_t hw_sample_period_offset, size_t hw_last_period_offset,
		size_t hw_period_left_offset, size_t use_invariant_tsc_offset,
		unsigned long attr_type, unsigned long attr_config,
		int attr_freq, unsigned long attr_sample_freq,
		unsigned long attr_sample_period, unsigned long hardware_type,
		unsigned long ref_cpu_cycles_config,
		sync_child_atomic64_set_fn_t atomic_set_fn);
extern long perf_event_alloc_map_body_result(void **event_out, void *event,
		size_t hw_config_offset, size_t hw_config_ext_offset,
		size_t extra_reg_config_offset, size_t extra_reg_reg_offset,
		size_t extra_reg_idx_offset, unsigned long attr_type,
		unsigned long attr_config, unsigned long hardware_type,
		unsigned long hw_cache_type, unsigned long raw_type,
		perf_event_map_fn_t hw_event_map_fn,
		perf_event_map_fn_t hw_cache_event_map_fn,
		perf_event_map_fn_t hw_cache_extra_reg_map_fn,
		perf_event_map_fn_t raw_event_map_fn,
		perf_event_validate_fn_t validate_event_fn,
		perf_extra_reg_id_fn_t extra_reg_id_fn,
		perf_extra_reg_msr_fn_t extra_reg_msr_fn,
		perf_extra_reg_idx_fn_t extra_reg_idx_fn,
		perf_hw_event_init_fn_t hw_event_init_fn);
extern long perf_event_alloc_body_result(void **event_out, const void *attr,
		size_t event_size, size_t attr_size, unsigned long alloc_flags,
		size_t event_attr_offset, size_t group_entry_offset,
		size_t sibling_list_offset, size_t sample_freq_offset,
		size_t nr_siblings_offset, size_t count_offset,
		size_t child_count_total_offset, size_t parent_offset,
		size_t hw_sample_period_offset, size_t hw_last_period_offset,
		size_t hw_period_left_offset, size_t use_invariant_tsc_offset,
		size_t hw_config_offset, size_t hw_config_ext_offset,
		size_t extra_reg_config_offset, size_t extra_reg_reg_offset,
		size_t extra_reg_idx_offset, unsigned long attr_type,
		unsigned long attr_config, int attr_freq,
		unsigned long attr_sample_freq, unsigned long attr_sample_period,
		unsigned long hardware_type, unsigned long hw_cache_type,
		unsigned long raw_type, unsigned long ref_cpu_cycles_config,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn,
		sync_child_atomic64_set_fn_t atomic_set_fn,
		perf_event_map_fn_t hw_event_map_fn,
		perf_event_map_fn_t hw_cache_event_map_fn,
		perf_event_map_fn_t hw_cache_extra_reg_map_fn,
		perf_event_map_fn_t raw_event_map_fn,
		perf_event_validate_fn_t validate_event_fn,
		perf_extra_reg_id_fn_t extra_reg_id_fn,
		perf_extra_reg_msr_fn_t extra_reg_msr_fn,
		perf_extra_reg_idx_fn_t extra_reg_idx_fn,
		perf_hw_event_init_fn_t hw_event_init_fn);
extern long perf_event_open_group_body_result(void *event, void *proc,
		int group_fd, int counter_idx, size_t proc_mckfd_offset,
		size_t mckfd_next_offset, size_t mckfd_fd_offset,
		size_t mckfd_data_offset, size_t event_group_leader_offset,
		size_t event_sibling_list_offset,
		size_t event_group_entry_offset,
		size_t event_nr_siblings_offset,
		size_t event_pmc_status_offset);
extern long perf_event_open_counter_body_result(void *event, void *thread,
		int pid, size_t event_pid_offset,
		size_t event_counter_id_offset,
		perf_counter_alloc_fn_t counter_alloc_fn);
extern long perf_event_open_linux_fd_body_result(
		struct syscall_request *request, void *thread, int counter_idx,
		int perf_event_open_nr, int cpu,
		size_t thread_pmc_alloc_map_offset,
		perf_open_syscall_fn_t syscall_fn);
extern long perf_event_open_mckfd_publish_body_result(void *sfd,
		void *event, void *proc, int fd,
		size_t proc_mckfd_lock_offset, size_t proc_mckfd_offset,
		size_t mckfd_next_offset, size_t mckfd_fd_offset,
		size_t mckfd_sig_no_offset, size_t mckfd_data_offset,
		size_t mckfd_read_cb_offset, size_t mckfd_ioctl_cb_offset,
		size_t mckfd_mmap_cb_offset, size_t mckfd_close_cb_offset,
		size_t mckfd_fcntl_cb_offset,
		syscall_mckfd_long_fn_t read_fn,
		syscall_mckfd_int_fn_t ioctl_fn,
		syscall_mckfd_long_fn_t mmap_fn,
		syscall_mckfd_int_fn_t close_fn,
		syscall_mckfd_int_fn_t fcntl_fn,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn);
extern long perf_event_open_body_result(struct syscall_request *request,
		void *thread, void *proc, void *attr, int pid, int group_fd,
		int perf_event_open_nr, int cpu, size_t mckfd_size,
		unsigned long mckfd_alloc_flags, size_t event_pid_offset,
		size_t event_counter_id_offset, size_t proc_mckfd_offset,
		size_t mckfd_next_offset, size_t mckfd_fd_offset,
		size_t mckfd_data_offset, size_t event_group_leader_offset,
		size_t event_sibling_list_offset, size_t event_group_entry_offset,
		size_t event_nr_siblings_offset, size_t event_pmc_status_offset,
		size_t thread_pmc_alloc_map_offset,
		size_t proc_mckfd_lock_offset, size_t mckfd_sig_no_offset,
		size_t mckfd_read_cb_offset, size_t mckfd_ioctl_cb_offset,
		size_t mckfd_mmap_cb_offset, size_t mckfd_close_cb_offset,
		size_t mckfd_fcntl_cb_offset,
		perf_open_event_alloc_fn_t event_alloc_fn,
		perf_counter_alloc_fn_t counter_alloc_fn,
		perf_open_syscall_fn_t syscall_fn,
		syscall_policy_alloc_fn_t mckfd_alloc_fn,
		syscall_mckfd_long_fn_t read_fn,
		syscall_mckfd_int_fn_t ioctl_fn,
		syscall_mckfd_long_fn_t mmap_fn,
		syscall_mckfd_int_fn_t close_fn,
		syscall_mckfd_int_fn_t fcntl_fn,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn);
extern long perf_event_open_entry_body_result(
		struct syscall_request *request, void *thread, void *proc,
		void *attr, unsigned long user_attr_addr, size_t attr_size,
		size_t attr_type_offset, size_t attr_read_format_offset,
		size_t attr_sample_period_offset, int pid, int validation_cpu,
		int group_fd, unsigned long flags, int linux_cpu,
		unsigned long raw_type, unsigned long hardware_type,
		unsigned long hw_cache_type,
		unsigned long unsupported_read_format_mask,
		unsigned long sample_period_sign_bit, int perf_event_open_nr,
		size_t mckfd_size, unsigned long mckfd_alloc_flags,
		size_t event_pid_offset, size_t event_counter_id_offset,
		size_t proc_mckfd_offset, size_t mckfd_next_offset,
		size_t mckfd_fd_offset, size_t mckfd_data_offset,
		size_t event_group_leader_offset,
		size_t event_sibling_list_offset,
		size_t event_group_entry_offset,
		size_t event_nr_siblings_offset,
		size_t event_pmc_status_offset,
		size_t thread_pmc_alloc_map_offset,
		size_t proc_mckfd_lock_offset, size_t mckfd_sig_no_offset,
		size_t mckfd_read_cb_offset, size_t mckfd_ioctl_cb_offset,
		size_t mckfd_mmap_cb_offset, size_t mckfd_close_cb_offset,
		size_t mckfd_fcntl_cb_offset,
		syscall_copy_from_user_fn_t copy_from_fn,
		perf_attr_freq_fn_t attr_freq_fn,
		perf_open_event_alloc_fn_t event_alloc_fn,
		perf_counter_alloc_fn_t counter_alloc_fn,
		perf_open_syscall_fn_t syscall_fn,
		syscall_policy_alloc_fn_t mckfd_alloc_fn,
		syscall_mckfd_long_fn_t read_fn,
		syscall_mckfd_int_fn_t ioctl_fn,
		syscall_mckfd_long_fn_t mmap_fn,
		syscall_mckfd_int_fn_t close_fn,
		syscall_mckfd_int_fn_t fcntl_fn,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn);
extern unsigned long exit_group_status_result(int rc, int sig);
extern int terminate_thread_active_result(int status);
extern int terminate_process_exited_result(int status);
extern int terminate_thread_is_other_result(const void *thread,
		const void *current_thread);
extern int terminate_report_thread_ptrace_result(int ptrace);
extern int terminate_child_cleanup_needed_result(int children_empty,
		int ptraced_children_empty);
extern int terminate_release_child_needed_result(int free_child);
extern int process_lookup_missing_result(const void *process);
extern int process_cleanup_tofu_needed_result(int enable_tofu);
extern int process_cleanup_fd_path_free_needed_result(const void *path);
extern long process_cleanup_fd_body_result(int pid, int fd, void *lock_arg,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		process_cleanup_fd_fn_t cleanup_fn,
		process_cleanup_missing_log_fn_t missing_log_fn);
extern long process_cleanup_before_terminate_body_result(int pid,
		void *lock_arg, int enable_tofu, int first_fd, int max_fd,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		process_cleanup_fd_fn_t cleanup_fn);
extern int terminate_host_detached_thread_release_needed_result(
		const void *process, const void *thread);
extern int terminate_host_kill_needed_result(int nohost);
extern long terminate_host_body_result(int pid, void *detached_thread,
		void *current_thread, void *lock_arg, size_t proc_nohost_offset,
		size_t thread_proc_offset, size_t thread_refcount_offset,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		terminate_host_ref_set_fn_t ref_set_fn,
		wait_thread_side_effect_fn_t release_thread_fn,
		wait_thread_side_effect_fn_t release_process_fn,
		syscall_do_kill_thread_fn_t do_kill_fn);
extern int finalize_process_parent_is_pid1_result(const void *parent,
		const void *pid1);
extern int finalize_process_parent_signal_needed_result(int termsig);
extern int terminate_status_result(int rc, int sig);
extern int terminate_report_thread_release_needed_result(int same_process,
		int termsig);
extern int terminate_child_action_result(int ppid_is_exiting,
		int parent_is_exiting, int child_status);
extern int clone_pthread_marker_result(int clone_flags, unsigned long newsp,
		unsigned long parent_tidptr);
extern int clone_flags_result(int clone_flags, int coredump_barrier_count);
extern int clone_host_parent_flags_result(int clone_flags, int ppid_parent_pid);
extern int clone_report_thread_result(int clone_flags, int termsig);
extern int clone_parent_tid_store_needed_result(int clone_flags);
extern int clone_child_cleartid_needed_result(int clone_flags);
extern int clone_child_tid_store_needed_result(int clone_flags);
extern int clone_tls_source_result(int clone_flags);
extern int clone_use_last_cpu_result(int mod_clone, int uti_use_last_cpu);
extern int clone_remote_spawn_result(int previous_mod_clone);
extern int clone_parent_use_pid1_result(int parent_status);
extern int ptrace_exec_event_signal_result(int ptrace);
extern int ptrace_syscall_event_signal_result(int ptrace);
extern int ptrace_clone_event_result(int ptrace, int clone_flags);
extern int ptrace_clone_reparent_result(int event);
extern int execveat_policy_result(int flags, int dirfd, int filename_first);
extern long execveat_body_result(void *ctx, int dirfd, const char *filename,
		char **argv, char **envp, int flags, int filename_first,
		syscall_execveat_fn_t execveat_fn);
extern long execve_body_result(void *ctx, const char *filename, char **argv,
		char **envp, syscall_execveat_fn_t execveat_fn);
extern int futex_decode_flags_result(int flags, int *opp, int *fsharedp);
extern int futex_wait_timeout_needed_result(int op, int has_utime);
extern int futex_timeout_is_absolute_result(int op);
extern int futex_clock_id_result(int flags);
extern unsigned int futex_requeue_val2_result(int op, unsigned long arg3);
extern unsigned long futex_timeout_ns_result(int op, long timeout_sec,
		long timeout_nsec, long now_sec, long now_nsec);
extern long do_futex_body_result(int n, unsigned long arg0,
		unsigned long arg1, unsigned long arg2, unsigned long arg3,
		unsigned long arg4, unsigned long arg5, int has_uti_clv,
		int local_gettime_support,
		do_futex_syscall_time_fn_t syscall_time_fn,
		do_futex_local_time_fn_t local_time_fn,
		do_futex_linux_time_fn_t linux_time_fn,
		do_futex_ns_per_tsc_fn_t ns_per_tsc_fn,
		do_futex_dispatch_fn_t futex_fn, do_futex_log_fn_t log_fn);
#else
SYSCALL_POLICY_HELPER_PROTO int robust_list_len_result(size_t len);
SYSCALL_POLICY_HELPER_PROTO long set_robust_list_body_result(size_t len);
SYSCALL_POLICY_HELPER_PROTO int tkill_tid_result(int tid);
SYSCALL_POLICY_HELPER_PROTO int tgkill_target_result(int tgid, int tid);
SYSCALL_POLICY_HELPER_PROTO int sigaction_validate(int sig, int has_act);
SYSCALL_POLICY_HELPER_PROTO int rt_sigprocmask_validate(size_t sigsetsize,
		size_t expected_sigset_size, int has_set, int how);
SYSCALL_POLICY_HELPER_PROTO unsigned long rt_sigprocmask_apply(
		unsigned long current_mask, unsigned long set_mask, int has_set,
		int how);
SYSCALL_POLICY_HELPER_PROTO int rt_sigpending_size_result(size_t sigsetsize,
		size_t expected_sigset_size);
SYSCALL_POLICY_HELPER_PROTO int signalfd4_sigsetsize_result(
		size_t sigsetsize, size_t expected_sigset_size);
SYSCALL_POLICY_HELPER_PROTO int signalfd4_flags_result(int flags);
SYSCALL_POLICY_HELPER_PROTO long signalfd_body_result(void);
SYSCALL_POLICY_HELPER_PROTO int syscall_refresh_cred_needed_result(long rc);
SYSCALL_POLICY_HELPER_PROTO int syscall_getpid_result(int pid);
SYSCALL_POLICY_HELPER_PROTO int syscall_getppid_result(int ppid);
SYSCALL_POLICY_HELPER_PROTO int syscall_gettid_result(int tid);
SYSCALL_POLICY_HELPER_PROTO int syscall_set_tid_address_return_result(int pid);
SYSCALL_POLICY_HELPER_PROTO long syscall_getpid_body_result(void *thread,
		size_t proc_offset, size_t pid_offset);
SYSCALL_POLICY_HELPER_PROTO long syscall_getppid_body_result(void *thread,
		size_t proc_offset, size_t ppid_parent_offset,
		size_t pid_offset);
SYSCALL_POLICY_HELPER_PROTO long syscall_gettid_body_result(void *thread,
		size_t tid_offset);
SYSCALL_POLICY_HELPER_PROTO long syscall_set_tid_address_body_result(
		void *thread, size_t clear_child_tid_offset,
		size_t proc_offset, size_t pid_offset, int *clear_child_tid);
SYSCALL_POLICY_HELPER_PROTO long syscall_get_process_id_field_result(
		void *thread, size_t proc_offset, size_t field_offset);
SYSCALL_POLICY_HELPER_PROTO long syscall_getresid_body_result(void *thread,
		size_t proc_offset, size_t first_offset, size_t second_offset,
		size_t third_offset, unsigned long first_user_addr,
		unsigned long second_user_addr, unsigned long third_user_addr,
		syscall_copy_int_to_user_fn_t copy_int_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_kill_body_result(void *thread,
		size_t proc_offset, size_t pid_offset, int pid, int sig,
		syscall_do_kill_thread_fn_t do_kill_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_tgkill_body_result(void *thread,
		size_t proc_offset, size_t pid_offset, int tgid, int tid,
		int sig, syscall_do_kill_thread_fn_t do_kill_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_tkill_body_result(void *thread,
		size_t proc_offset, size_t pid_offset, int tid, int sig,
		syscall_do_kill_thread_fn_t do_kill_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_forward_refresh_cred_body_result(
		int syscall_nr, void *ctx, syscall_forward_context_fn_t forward_fn,
		syscall_refresh_cred_fn_t refresh_fn);
SYSCALL_POLICY_HELPER_PROTO unsigned long syscall_setfsid_body_result(int id,
		int syscall_nr, syscall_do_syscall2_fn_t do_syscall_fn,
		syscall_refresh_cred_fn_t refresh_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_times_body_result(void *thread,
		unsigned long buf_addr, int gettime_local_support,
		const struct syscall_times_offsets *offsets,
		syscall_tsc_to_ts_fn_t tsc_to_ts_fn,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_ts_add_fn_t ts_add_fn, syscall_gettime_fn_t gettime_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO int syscall_use_requester_tid_result(
		int syscall_nr, unsigned long arg0, int sched_setaffinity_nr);
SYSCALL_POLICY_HELPER_PROTO int syscall_target_tid_result(
		int use_requester_tid, int current_tid);
SYSCALL_POLICY_HELPER_PROTO int syscall_send_prepare_result(
		struct syscall_request *req, struct syscall_response *res);
SYSCALL_POLICY_HELPER_PROTO int syscall_request_copy_result(
		struct syscall_request *dst, const struct syscall_request *src);
SYSCALL_POLICY_HELPER_PROTO int syscall_request_publish_result(
		struct syscall_request *req);
SYSCALL_POLICY_HELPER_PROTO long syscall_generic_forwarding_body_result(
		struct syscall_request *req, int n, unsigned long arg0,
		unsigned long arg1, unsigned long arg2, unsigned long arg3,
		unsigned long arg4, unsigned long arg5, int cpu,
		syscall_request_call_fn_t do_syscall_fn);
SYSCALL_POLICY_HELPER_PROTO int syscall_packet_traditional_prepare_result(
		struct ikc_scd_packet *packet, int msg, int cpu_ref, int pid,
		unsigned long resp_pa);
SYSCALL_POLICY_HELPER_PROTO int syscall_eventfd_packet_prepare_result(
		struct ikc_scd_packet *packet, int msg, int eventfd_type);
SYSCALL_POLICY_HELPER_PROTO int syscall_eventfd_send_result(void *channel,
		int msg, int eventfd_type, syscall_ikc_send_fn_t send_fn);
SYSCALL_POLICY_HELPER_PROTO int syscall_log_budget_result(int pid,
		int *last_pidp, int *log_countp, int limit);
SYSCALL_POLICY_HELPER_PROTO int syscall_reject_after_exit_result(
		int process_status, int syscall_nr, int exit_nr,
		int exit_group_nr);
SYSCALL_POLICY_HELPER_PROTO int syscall_offload_spin_without_schedule_result(
		int no_preempt, int tid);
SYSCALL_POLICY_HELPER_PROTO int syscall_offload_prepare_result(
		struct syscall_request *req, struct syscall_response *res,
		int current_tid, int syscall_nr, unsigned long arg0,
		int sched_setaffinity_nr, unsigned long spinning_status);
SYSCALL_POLICY_HELPER_PROTO int syscall_preempt_disable_needed_result(
		int rtid);
SYSCALL_POLICY_HELPER_PROTO int syscall_proxy_dead_result(long rc);
SYSCALL_POLICY_HELPER_PROTO int syscall_tofu_post_reply_candidate_result(
		int syscall_nr, long rc, int ioctl_nr, int openat_nr);
SYSCALL_POLICY_HELPER_PROTO int syscall_profile_event_needed_result(
		int syscall_nr, int profile_max);
SYSCALL_POLICY_HELPER_PROTO int syscall_offload_counted_result(
		int syscall_nr, int exit_group_nr);
SYSCALL_POLICY_HELPER_PROTO int syscall_nested_dispatch_valid_result(
		int syscall_nr, int syscall_count, int has_handler);
SYSCALL_POLICY_HELPER_PROTO int syscall_nested_rt_sigaction_index_result(
		int sig, int nsig);
SYSCALL_POLICY_HELPER_PROTO int syscall_nested_response_prepare_result(
		struct syscall_request *req, struct syscall_response *res,
		unsigned long response_nr, unsigned long syscall_ret,
		int current_tid, int service_tid, unsigned long spinning_status);
SYSCALL_POLICY_HELPER_PROTO int setpgid_normalize_pid(int current_pid, int pid);
SYSCALL_POLICY_HELPER_PROTO int setpgid_normalize_pgid(int pid, int pgid);
SYSCALL_POLICY_HELPER_PROTO int setpgid_execed_result(int execed);
SYSCALL_POLICY_HELPER_PROTO long syscall_setpgid_body_result(void *thread,
		int pid, int pgid, int syscall_nr, void *ctx,
		const struct syscall_setpgid_offsets *offsets, void *lock_arg,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_setrlimit_body_result(int resource,
		unsigned long new_limit_addr,
		syscall_do_prlimit64_fn_t do_prlimit_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_getrlimit_body_result(int resource,
		unsigned long old_limit_addr,
		syscall_do_prlimit64_fn_t do_prlimit_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_prlimit64_body_result(int pid,
		int resource, unsigned long new_limit_addr,
		unsigned long old_limit_addr,
		syscall_do_prlimit64_fn_t do_prlimit_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_sysinfo_body_result(
		unsigned long sysinfo_addr, unsigned long totalram,
		unsigned long freeram, syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_get_cpu_id_body_result(
		syscall_get_cpu_fn_t get_cpu_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_mlockall_body_result(void *thread,
		int flags, const struct syscall_mlockall_offsets *offsets,
		syscall_log_int_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_munlockall_body_result(
		syscall_log_int_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_getcpu_body_result(
		unsigned long cpup_addr, unsigned long nodep_addr, int cpu,
		int node, syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_read_body_result(void *thread,
		int fd, int syscall_nr, void *ctx,
		const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_ioctl_body_result(void *thread,
		int fd, unsigned long cmd, unsigned long arg, int syscall_nr,
		void *ctx, const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn,
		syscall_tofu_ioctl_fn_t tofu_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_fcntl_body_result(void *thread,
		int fd, int syscall_nr, void *ctx,
		const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn);
SYSCALL_POLICY_HELPER_PROTO long syscall_close_body_result(void *thread,
		int fd, int syscall_nr, void *ctx,
		const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn,
		syscall_tofu_close_fn_t close_path_fn,
		syscall_mckfd_free_fn_t free_fn);
SYSCALL_POLICY_HELPER_PROTO int memlock_prepare_range(uintptr_t start0,
		size_t len0, uintptr_t user_start, uintptr_t user_end,
		uintptr_t *startp, size_t *lenp, uintptr_t *endp);
SYSCALL_POLICY_HELPER_PROTO int memlock_range_flag_result(unsigned long flag);
SYSCALL_POLICY_HELPER_PROTO int memlock_body_result(void *vm,
		void *range_lock, unsigned long start0, size_t len0,
		unsigned long user_start, unsigned long user_end, int op, int cpu,
		size_t range_start_offset, size_t range_end_offset,
		size_t range_flag_offset, size_t range_memobj_offset,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn, memlock_split_fn_t split_fn,
		memlock_join_fn_t join_fn, memlock_populate_fn_t populate_fn,
		memlock_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int range_has_disallowed_change_flags(
		unsigned long flag);
SYSCALL_POLICY_HELPER_PROTO int munmap_prepare_range(uintptr_t addr,
		size_t len0, uintptr_t user_start, uintptr_t user_end,
		size_t *lenp);
SYSCALL_POLICY_HELPER_PROTO int munmap_body_result(void *vm,
		void *range_lock, unsigned long addr, size_t len0,
		unsigned long user_start, unsigned long user_end, int cpu,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		munmap_do_fn_t do_munmap_fn, munmap_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int shmdt_body_result(void *vm,
		void *range_lock, unsigned long shmaddr,
		size_t range_start_offset, size_t range_end_offset,
		size_t range_memobj_offset, size_t memobj_flags_offset,
		unsigned long shmdt_ok_flag, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		munmap_do_fn_t do_munmap_fn, shmdt_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int do_munmap_body_result(void *vm, void *proc,
		unsigned long addr, size_t len, int holding_memory_range_lock,
		size_t proc_straight_va_offset,
		size_t proc_straight_len_offset,
		do_munmap_void_fn_t begin_fn,
		do_munmap_remove_range_fn_t remove_range_fn,
		do_munmap_clear_host_fn_t clear_host_pte_fn,
		mprotect_set_host_vma_fn_t set_host_vma_fn,
		do_munmap_void_fn_t finish_fn, do_munmap_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO long clear_host_pte_body_result(void *vm,
		unsigned long addr, size_t len, int holding_memory_range_lock,
		size_t vm_lock_taken_offset, int cpu, int syscall_nr,
		syscall_do_syscall3_fn_t forward_fn,
		clear_host_pte_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO void munmap_all_body_result(void *vm,
		void *range_lock, void *region, size_t range_start_offset,
		size_t range_end_offset, size_t region_map_start_offset,
		size_t region_map_end_offset, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn, munmap_do_fn_t do_munmap_fn,
		munmap_all_free_ranges_fn_t free_ranges_fn,
		munmap_all_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO long shmat_body_result(int shmid,
		unsigned long shmaddr, int shmflg, uid_t proc_euid,
		gid_t proc_egid, void *vm, void *range_lock,
		size_t obj_pgshift_offset, size_t obj_real_segsz_offset,
		size_t obj_memobj_offset, size_t obj_uid_offset,
		size_t obj_cuid_offset, size_t obj_gid_offset,
		size_t obj_cgid_offset, size_t obj_mode_offset,
		shmat_void_fn_t list_lock_fn, shmat_void_fn_t list_unlock_fn,
		shmat_lookup_obj_fn_t lookup_obj_fn,
		shmat_memobj_fn_t memobj_unref_fn,
		syscall_rwlock_fn_t range_lock_fn,
		syscall_rwlock_fn_t range_unlock_fn,
		syscall_lookup_range_fn_t lookup_range_fn,
		shmat_search_fn_t search_free_fn,
		mprotect_set_host_vma_fn_t set_host_vma_fn,
		shmat_add_range_fn_t add_range_fn, shmat_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO long shmctl_body_result(int shmid, int cmd,
		unsigned long buf_addr, uid_t proc_euid, gid_t proc_egid,
		uid_t proc_ruid, unsigned long rlim_memlock_cur, long now,
		int has_cap_sys_admin, int has_cap_ipc_lock,
		const struct shmctl_offsets *offsets, const void *shminfo,
		const void *shm_info, shmat_void_fn_t list_lock_fn,
		shmat_void_fn_t list_unlock_fn,
		shmat_lookup_obj_fn_t lookup_obj_fn,
		shmat_lookup_obj_fn_t lookup_by_index_fn,
		shmat_memobj_fn_t memobj_unref_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		shmctl_get_max_index_fn_t get_max_index_fn,
		shmat_void_fn_t users_lock_fn,
		shmat_void_fn_t users_unlock_fn,
		shmctl_shmlock_user_get_fn_t shmlock_user_get_fn,
		shmat_memobj_fn_t shmlock_user_free_fn,
		shmctl_memobj_refcnt_read_fn_t memobj_refcnt_read_fn,
		shmctl_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int search_free_space_body_result(void *vm,
		void *region, size_t len, int pgshift, unsigned long *addrp,
		size_t region_user_end_offset, size_t region_map_end_offset,
		size_t range_end_offset, syscall_lookup_range_fn_t lookup_fn,
		search_free_space_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int set_host_vma_body_result(unsigned long addr,
		size_t len, int prot, int holding_memory_range_lock);
SYSCALL_POLICY_HELPER_PROTO int mprotect_prepare_range(uintptr_t start,
		size_t len0, uintptr_t user_start, uintptr_t user_end,
		size_t *lenp, uintptr_t *endp);
SYSCALL_POLICY_HELPER_PROTO void mprotect_split_needed_result(
		unsigned long range_start, unsigned long range_end,
		unsigned long addr, unsigned long end, int *split_startp,
		int *split_endp);
SYSCALL_POLICY_HELPER_PROTO int mprotect_write_changed_result(
		unsigned long range_flags, unsigned long protflags);
SYSCALL_POLICY_HELPER_PROTO int mprotect_body_result(void *vm,
		void *range_lock, unsigned long start, size_t len0, int prot,
		unsigned long user_start, unsigned long user_end,
		unsigned long straight_va, size_t straight_len, int cpu,
		size_t range_start_offset, size_t range_end_offset,
		size_t range_flag_offset, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn, memlock_split_fn_t split_fn,
		memlock_join_fn_t join_fn, mprotect_change_fn_t change_fn,
		mprotect_set_host_vma_fn_t set_host_vma_fn,
		mprotect_flush_fn_t flush_nfo_fn,
		mprotect_flush_fn_t flush_tlb_fn,
		mprotect_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int mlockall_policy_result(int flags,
		int is_privileged, unsigned long memlock_cur);
SYSCALL_POLICY_HELPER_PROTO int remap_file_pages_prepare(uintptr_t start0,
		size_t size, int prot, size_t pgoff, uintptr_t *startp,
		uintptr_t *endp, off_t *offp);
SYSCALL_POLICY_HELPER_PROTO int remap_file_pages_body_result(void *vm,
		void *range_lock, unsigned long start0, size_t size, int prot,
		size_t pgoff, int flags, int cpu,
		size_t range_start_offset, size_t range_end_offset,
		size_t range_flag_offset, size_t range_memobj_offset,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		remap_file_pages_callable_fn_t callable_fn,
		remap_file_pages_remap_fn_t remap_fn,
		remap_file_pages_clear_host_fn_t clear_host_fn,
		memlock_populate_fn_t populate_fn,
		mprotect_flush_fn_t flush_nfo_fn,
		remap_file_pages_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int mremap_prepare_args(uintptr_t oldaddr,
		size_t oldsize0, size_t newsize0, int flags, uintptr_t newaddr,
		uintptr_t user_start, uintptr_t user_end,
		size_t *oldsizep, size_t *newsizep, uintptr_t *oldendp,
		int *no_opp);
SYSCALL_POLICY_HELPER_PROTO int mremap_fixed_range_result(
		uintptr_t newstart, uintptr_t user_start, uintptr_t oldstart,
		uintptr_t oldend, uintptr_t newend);
SYSCALL_POLICY_HELPER_PROTO int mremap_maymove_result(int flags);
SYSCALL_POLICY_HELPER_PROTO long mremap_body_result(void *vm,
		void *range_lock, void *pte_lock, void *page_table,
		unsigned long oldaddr, size_t oldsize0, size_t newsize0,
		int flags, unsigned long newaddr, unsigned long user_start,
		unsigned long user_end, unsigned long straight_va,
		size_t straight_len, size_t range_start_offset,
		size_t range_end_offset, size_t range_flag_offset,
		size_t range_pgshift_offset, size_t range_memobj_offset,
		size_t range_objoff_offset, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		mremap_extend_fn_t extend_fn, mprotect_flush_fn_t flush_nfo_fn,
		mremap_search_fn_t search_fn, munmap_do_fn_t munmap_fn,
		mremap_memobj_ref_fn_t memobj_ref_fn,
		mremap_memobj_ref_fn_t memobj_unref_fn,
		mremap_add_range_fn_t add_range_fn,
		syscall_rwlock_fn_t pte_lock_fn,
		syscall_rwlock_fn_t pte_unlock_fn,
		memlock_split_fn_t split_fn, mremap_move_pte_fn_t move_pte_fn,
		memlock_populate_fn_t populate_fn, mremap_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int msync_prepare_range(uintptr_t start0,
		size_t len0, int flags, size_t *lenp, uintptr_t *endp);
SYSCALL_POLICY_HELPER_PROTO int msync_locked_range_result(int flags,
		unsigned long range_flags);
SYSCALL_POLICY_HELPER_PROTO int msync_body_result(void *vm,
		void *range_lock, unsigned long start0, size_t len0, int flags,
		size_t range_start_offset, size_t range_end_offset,
		size_t range_flag_offset, size_t range_memobj_offset,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn,
		msync_memobj_has_pager_fn_t has_pager_fn,
		msync_range_op_fn_t sync_fn, msync_range_op_fn_t invalidate_fn,
		msync_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int mbind_prepare_range(uintptr_t addr,
		unsigned long len0, unsigned long *lenp);
SYSCALL_POLICY_HELPER_PROTO int mempolicy_nodemask_bits_result(
		unsigned long maxnode, unsigned long *nodemask_bitsp);
SYSCALL_POLICY_HELPER_PROTO int mempolicy_nodemask_bits_is_clamped(
		unsigned long maxnode);
SYSCALL_POLICY_HELPER_PROTO int mbind_mode_flags_result(int mode,
		unsigned int flags, int *mode_flagsp, int *normalized_modep);
SYSCALL_POLICY_HELPER_PROTO int mempolicy_mode_is_supported(int mode);
SYSCALL_POLICY_HELPER_PROTO int set_mempolicy_normalize_mode(int mode,
		int *normalized_modep);
SYSCALL_POLICY_HELPER_PROTO long mbind_body_result(unsigned long addr,
		unsigned long len0, int mode, unsigned long nodemask_addr,
		unsigned long maxnode, int flags, struct process_vm *vm,
		int straight_va, int fugaku_hacks, int nr_numa_nodes,
		size_t policy_size, unsigned long alloc_flags,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_rwlock_fn_t write_lock_fn,
		syscall_rwlock_fn_t write_unlock_fn,
		syscall_lookup_range_fn_t lookup_range_fn,
		syscall_policy_search_fn_t policy_search_fn,
		syscall_policy_clear_range_fn_t clear_range_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_policy_rb_clear_fn_t rb_clear_fn,
		syscall_policy_insert_fn_t insert_fn,
		syscall_mbind_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO long set_mempolicy_body_result(int mode,
		unsigned long nodemask_addr, unsigned long maxnode,
		struct process_vm *vm, int nr_numa_nodes, int pid,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_set_mempolicy_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int get_mempolicy_validate(unsigned long addr,
		int flags, int process_policy, unsigned long maxnode,
		int nr_numa_nodes, unsigned long *nodemask_bitsp);
SYSCALL_POLICY_HELPER_PROTO long get_mempolicy_body_result(
		unsigned long mode_addr, unsigned long nodemask_addr,
		unsigned long maxnode, unsigned long addr, int flags,
		struct process_vm *vm, int nr_numa_nodes,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_lookup_node_fn_t lookup_node_fn,
		syscall_rwlock_fn_t read_lock_fn,
		syscall_rwlock_fn_t read_unlock_fn,
		syscall_lookup_range_fn_t lookup_range_fn,
		syscall_policy_search_fn_t policy_search_fn,
		syscall_get_mempolicy_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int move_pages_policy_result(int pid, int flags);
SYSCALL_POLICY_HELPER_PROTO int move_pages_smp_req_prepare_result(
		struct move_pages_smp_req *req, unsigned long count,
		const void **user_virt_addr, int *user_status,
		const int *user_nodes, void **virt_addr, int *status,
		pte_t **ptep, int *nodes, int *nr_pages,
		unsigned long *dst_phys, void *proc);
SYSCALL_POLICY_HELPER_PROTO long move_pages_body_result(int pid,
		unsigned long count, unsigned long user_virt_addr_addr,
		unsigned long user_nodes_addr, unsigned long user_status_addr,
		int flags, struct process_vm *vm, void *page_table_lock,
		void *cpu_set, void *proc, unsigned long alloc_flags,
		size_t ptr_size, size_t int_size, size_t pte_size,
		size_t ulong_size, move_pages_verify_fn_t verify_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn,
		move_pages_get_nr_nodes_fn_t get_nr_nodes_fn,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		move_pages_smp_call_fn_t smp_call_fn, smp_func_t handler_fn,
		syscall_rdtsc_fn_t rdtsc_fn, move_pages_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int brk_prepare_result(unsigned long address,
		unsigned long brk_start, unsigned long brk_end,
		unsigned long brk_end_allocated, unsigned long *resultp,
		int *extend_neededp);
SYSCALL_POLICY_HELPER_PROTO unsigned long brk_default_vrflags(void);
SYSCALL_POLICY_HELPER_PROTO unsigned long brk_body_result(void *vm,
		void *region, void *range_lock, unsigned long address, int cpu,
		size_t brk_start_offset, size_t brk_end_offset,
		size_t brk_end_allocated_offset, brk_flush_fn_t flush_fn,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		brk_extend_fn_t extend_fn, brk_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int mincore_prepare_range(uintptr_t start,
		size_t len, uintptr_t user_start, uintptr_t user_end,
		uintptr_t *endp);
SYSCALL_POLICY_HELPER_PROTO long mincore_body_result(void *vm,
		void *range_lock, void *pte_lock, void *page_table,
		unsigned long start, size_t len, unsigned long vec_addr,
		unsigned long user_start, unsigned long user_end,
		size_t range_start_offset, size_t range_end_offset,
		size_t range_memobj_offset, size_t range_objoff_offset,
		syscall_rwlock_fn_t range_lock_fn,
		syscall_rwlock_fn_t range_unlock_fn,
		syscall_rwlock_fn_t pte_lock_fn,
		syscall_rwlock_fn_t pte_unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		mincore_pte_lookup_fn_t pte_lookup_fn,
		mincore_pte_present_fn_t pte_present_fn,
		mincore_memobj_lookup_fn_t memobj_lookup_fn,
		mincore_copy_byte_fn_t copy_byte_fn, mincore_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO unsigned long mmap_base_vrflags(int prot,
		int flags, unsigned long vrf0, int anon_on_demand);
SYSCALL_POLICY_HELPER_PROTO int mmap_populated_mapping_result(int flags);
SYSCALL_POLICY_HELPER_PROTO int mmap_should_set_host_ro(int flags, int prot,
		int anonymous_only);
SYSCALL_POLICY_HELPER_PROTO int mmap_update_private_maxprot(int flags,
		int maxprot);
SYSCALL_POLICY_HELPER_PROTO int mmap_prot_denied_result(int prot,
		int maxprot, int *deniedp);
SYSCALL_POLICY_HELPER_PROTO unsigned long mmap_maxprot_to_vrflags(int maxprot);
SYSCALL_POLICY_HELPER_PROTO int mmap_should_force_straight(int flags,
		int straight_map, unsigned long phys, size_t len,
		size_t threshold);
SYSCALL_POLICY_HELPER_PROTO int mmap_is_shared(int flags);
SYSCALL_POLICY_HELPER_PROTO int getrusage_who_result(int who);
SYSCALL_POLICY_HELPER_PROTO int itimer_which_result(int which);
SYSCALL_POLICY_HELPER_PROTO int itimer_is_real(int which);
SYSCALL_POLICY_HELPER_PROTO int itimer_should_start(long value_sec,
		long value_usec);
SYSCALL_POLICY_HELPER_PROTO void itimer_snapshot_current_result(
		unsigned long timer_addr, unsigned long elapsed_addr,
		unsigned long out_addr);
SYSCALL_POLICY_HELPER_PROTO long setitimer_body_result(int which,
		unsigned long new_addr, unsigned long old_addr, void *thread,
		const struct syscall_itimer_offsets *offsets, int syscall_nr,
		syscall_do_syscall3_fn_t syscall3_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_set_timer_fn_t set_timer_fn);
SYSCALL_POLICY_HELPER_PROTO long getitimer_body_result(int which,
		unsigned long old_addr, void *thread,
		const struct syscall_itimer_offsets *offsets, int syscall_nr,
		syscall_do_syscall2_fn_t syscall2_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO int clock_gettime_dispatch(int clock_id,
		int local_support, int has_ts);
SYSCALL_POLICY_HELPER_PROTO int gettimeofday_dispatch(int has_tv, int has_tz,
		int local_support);
SYSCALL_POLICY_HELPER_PROTO long settimeofday_body_result(
		unsigned long utv_addr, unsigned long utz_addr,
		int local_support, unsigned long clocks_per_sec, int syscall_nr,
		void *ctx, void *lock_arg, void *version_arg,
		struct timespec *origin, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_rdtsc_fn_t rdtsc_fn,
		syscall_forward_context_fn_t forward_fn,
		syscall_atomic64_read_fn_t atomic_read_fn,
		syscall_atomic64_inc_fn_t atomic_inc_fn, syscall_wmb_fn_t wmb_fn,
		syscall_panic_fn_t panic_fn, settimeofday_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int nanosleep_validate_timespec(long sec,
		long nsec);
SYSCALL_POLICY_HELPER_PROTO int rt_sigtimedwait_prepare(size_t sigsetsize,
		size_t expected_sigset_size, int has_set);
SYSCALL_POLICY_HELPER_PROTO int rt_sigtimedwait_timeout_result(long sec,
		long nsec, int local_support);
SYSCALL_POLICY_HELPER_PROTO void rt_sigtimedwait_prepare_masks(
		unsigned long raw_wait_mask, unsigned long current_mask,
		unsigned long *wait_maskp, unsigned long *blocked_maskp,
		unsigned long *interrupt_maskp);
SYSCALL_POLICY_HELPER_PROTO void rt_sigtimedwait_deadline(long now_sec,
		long now_nsec, long timeout_sec, long timeout_nsec,
		long *deadline_secp, long *deadline_nsecp);
SYSCALL_POLICY_HELPER_PROTO int rt_sigtimedwait_timeout_expired(long now_sec,
		long now_nsec, long deadline_sec, long deadline_nsec);
SYSCALL_POLICY_HELPER_PROTO int sigmask_to_signal_number(unsigned long mask);
SYSCALL_POLICY_HELPER_PROTO int signal_pending_deliverable_result(int delflag,
		int sig, unsigned long handler_addr, unsigned long pending_mask,
		unsigned long blocked_mask);
SYSCALL_POLICY_HELPER_PROTO int signal_pending_interrupt_action_result(int sig,
		unsigned long handler_addr, unsigned long pending_mask,
		unsigned long blocked_mask, int interrupted);
SYSCALL_POLICY_HELPER_PROTO int rt_sigqueueinfo_pid_result(int pid);
SYSCALL_POLICY_HELPER_PROTO int sigsuspend_sigsetsize_result(
		size_t sigsetsize, size_t expected_sigset_size);
SYSCALL_POLICY_HELPER_PROTO unsigned long sigsuspend_prepare_mask(
		unsigned long raw_mask);
SYSCALL_POLICY_HELPER_PROTO int sigsuspend_pending_matches(
		unsigned long pending_mask, unsigned long suspend_mask);
SYSCALL_POLICY_HELPER_PROTO long pause_body_result(void *thread,
		size_t sigmask_offset, syscall_sigsuspend_fn_t suspend_fn);
SYSCALL_POLICY_HELPER_PROTO long rt_sigsuspend_body_result(void *thread,
		unsigned long set_addr, size_t sigsetsize,
		size_t expected_sigset_size, void *scratch_sigset,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_sigsuspend_fn_t suspend_fn);
SYSCALL_POLICY_HELPER_PROTO int sigaction_sigsetsize_result(
		size_t sigsetsize, size_t expected_sigset_size);
SYSCALL_POLICY_HELPER_PROTO int sigaltstack_validate(int flags, size_t size);
SYSCALL_POLICY_HELPER_PROTO int sigaltstack_is_disable(int flags);
SYSCALL_POLICY_HELPER_PROTO long sigaltstack_body_result(void *thread,
		size_t sigstack_offset, unsigned long ss_addr,
		unsigned long oss_addr, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO int process_vm_validate_args(unsigned long flags,
		unsigned long liovcnt, unsigned long riovcnt);
SYSCALL_POLICY_HELPER_PROTO int process_vm_op_is_write(int op);
SYSCALL_POLICY_HELPER_PROTO int process_vm_op_is_valid(int op);
SYSCALL_POLICY_HELPER_PROTO long process_vm_rw_body_result(int pid,
		const struct iovec *local_iov, unsigned long liovcnt,
		const struct iovec *remote_iov, unsigned long riovcnt,
		unsigned long flags, int op, syscall_process_vm_rw_fn_t rw_fn);
SYSCALL_POLICY_HELPER_PROTO long prctl_body_result(int option,
		unsigned long arg2, unsigned long arg3, unsigned long arg4,
		unsigned long arg5, void *proc, size_t thp_disable_offset,
		int syscall_nr, void *ctx, syscall_forward_context_fn_t forward_fn);
SYSCALL_POLICY_HELPER_PROTO int arch_prctl_type_result(unsigned long code,
		int *typep);
SYSCALL_POLICY_HELPER_PROTO long arch_prctl_body_result(unsigned long code,
		unsigned long address, void *thread, size_t tlsblock_base_offset,
		syscall_get_cpu_fn_t get_cpu_fn,
		arch_prctl_set_register_fn_t set_register_fn,
		arch_prctl_get_register_fn_t get_register_fn,
		arch_prctl_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO unsigned long arch_clone_body_result(void *proc,
		size_t coredump_lock_offset, void *lock_node, int clone_flags,
		unsigned long newsp, unsigned long parent_tidptr,
		unsigned long child_tidptr, unsigned long tls, unsigned long pc,
		unsigned long sp, arch_clone_lock_fn_t lock_fn,
		arch_clone_lock_fn_t unlock_fn, arch_do_fork_fn_t fork_fn);
SYSCALL_POLICY_HELPER_PROTO unsigned long arch_fork_body_result(
		unsigned long pc, unsigned long sp, arch_do_fork_fn_t fork_fn);
SYSCALL_POLICY_HELPER_PROTO unsigned long arch_vfork_body_result(
		unsigned long pc, unsigned long sp, arch_do_fork_fn_t fork_fn);
SYSCALL_POLICY_HELPER_PROTO long arch_time_body_result(long now,
		unsigned long tloc_addr, syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO long arch_shmget_body_result(long key,
		size_t size, int shmflg0,
		arch_shmget_default_huge_shift_fn_t default_huge_shift_fn,
		arch_do_shmget_fn_t do_shmget_fn,
		arch_shmget_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO long arch_mmap_body_result(unsigned long addr0,
		size_t len0, int prot, int flags0, int fd, long off0,
		unsigned long user_start, unsigned long user_end,
		int supported_flags, int ignored_flags, int error_flags,
		arch_mmap_default_huge_shift_fn_t default_huge_shift_fn,
		arch_mmap_overmap_fn_t overmap_fn,
		arch_do_mmap_fn_t do_mmap_fn, arch_mmap_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO long migrate_pages_body_result(void);
SYSCALL_POLICY_HELPER_PROTO long madvise_body_result(unsigned long start,
		size_t len, int advice);
SYSCALL_POLICY_HELPER_PROTO long get_system_body_result(void);
SYSCALL_POLICY_HELPER_PROTO long perf_event_open_disabled_body_result(void);
SYSCALL_POLICY_HELPER_PROTO long linux_mlock_body_result(unsigned long addr,
		size_t len, int syscall_nr, syscall_do_syscall2_fn_t syscall2_fn);
SYSCALL_POLICY_HELPER_PROTO long linux_spawn_body_result(int syscall_nr,
		void *ctx, syscall_forward_context_fn_t forward_fn);
SYSCALL_POLICY_HELPER_PROTO long swapout_body_result(const char *filename,
		void *workarea, size_t size, int flag, int syscall_nr,
		void *linux_ctx, syscall_swapout_pageout_fn_t pageout_fn,
		syscall_swapout_pagein_fn_t pagein_fn,
		syscall_forward_context_fn_t forward_fn);
SYSCALL_POLICY_HELPER_PROTO long open_common_body_result(
		unsigned long pathname_addr, int flags, int syscall_nr,
		void *ctx, const char *xpmem_dev_path, unsigned long alloc_flags,
		syscall_strlen_user_fn_t strlen_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn,
		syscall_open_special_fn_t special_open_fn,
		syscall_forward_context_fn_t forward_fn);
SYSCALL_POLICY_HELPER_PROTO long util_migrate_inter_kernel_body_result(
		unsigned long arg_addr, void *scratch_attr, size_t attr_size,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_util_thread_fn_t util_thread_fn);
SYSCALL_POLICY_HELPER_PROTO long util_indicate_clone_body_result(void *thread,
		int mode, unsigned long arg_addr, size_t attr_size,
		unsigned long alloc_flags, size_t thread_proc_offset,
		size_t proc_enable_uti_offset, size_t thread_mod_clone_offset,
		size_t thread_mod_clone_arg_offset,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn);
SYSCALL_POLICY_HELPER_PROTO long util_register_desc_body_result(
		unsigned long desc, unsigned long *desc_store);
SYSCALL_POLICY_HELPER_PROTO long threads_signal_body_result(
		void *current_thread, int signal, int wait_stopped,
		size_t thread_proc_offset, size_t proc_pid_offset,
		size_t proc_threads_list_offset, size_t thread_tid_offset,
		size_t thread_status_offset, size_t thread_siblings_list_offset,
		syscall_do_kill_thread_fn_t do_kill_fn,
		syscall_cpu_pause_fn_t pause_fn);
SYSCALL_POLICY_HELPER_PROTO int ptrace_signal_data_result(long data);
SYSCALL_POLICY_HELPER_PROTO int ptrace_detach_signal_result(long data);
SYSCALL_POLICY_HELPER_PROTO int ptrace_user_area_result(long addr,
		unsigned long user_struct_size);
SYSCALL_POLICY_HELPER_PROTO int ptrace_status_allows_io(int status);
SYSCALL_POLICY_HELPER_PROTO int ptrace_setoptions_flags_result(int flags);
SYSCALL_POLICY_HELPER_PROTO int ptrace_apply_options(int current, int flags);
SYSCALL_POLICY_HELPER_PROTO int ptrace_setoptions_apply_thread_result(
		unsigned long thread_addr, unsigned long ptrace_offset,
		int flags);
SYSCALL_POLICY_HELPER_PROTO int ptrace_child_traced_result(int has_child,
		int has_proc, int ptrace);
SYSCALL_POLICY_HELPER_PROTO int ptrace_attach_policy_result(int tracer_pid,
		int target_pid, int target_ptrace, int same_process);
SYSCALL_POLICY_HELPER_PROTO int ptrace_attach_mark_traced_result(
		unsigned long thread_addr, unsigned long ptrace_offset);
SYSCALL_POLICY_HELPER_PROTO int ptrace_detach_state_result(int is_traced,
		int same_report_proc);
SYSCALL_POLICY_HELPER_PROTO int ptrace_siginfo_state_result(int status,
		int has_siginfo);
SYSCALL_POLICY_HELPER_PROTO int ptrace_eventmsg_state_result(int status);
SYSCALL_POLICY_HELPER_PROTO int ptrace_eventmsg_prepare_result(int status,
		unsigned long eventmsg, unsigned long *outp);
SYSCALL_POLICY_HELPER_PROTO int ptrace_wakeup_request_action_result(
		long request);
SYSCALL_POLICY_HELPER_PROTO int ptrace_resume_single_step_result(long request);
SYSCALL_POLICY_HELPER_PROTO int ptrace_resume_trace_syscall_result(
		long request);
SYSCALL_POLICY_HELPER_PROTO int ptrace_resume_signal_needed_result(
		long request, long data);
SYSCALL_POLICY_HELPER_PROTO int ptrace_resume_signal_source_result(
		long request, int has_sendsig, int has_recvsig);
SYSCALL_POLICY_HELPER_PROTO int ptrace_detach_forward_signal_needed_result(
		int data);
SYSCALL_POLICY_HELPER_PROTO int ptrace_detach_exit_signal_needed_result(
		int status);
SYSCALL_POLICY_HELPER_PROTO int ptrace_detach_thread_body_result(
		void *thread, int data, void *current_thread,
		void *current_proc, void *pid1,
		const struct ptrace_detach_offsets *offsets,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		ptrace_list_detach_fn_t list_detach_fn,
		ptrace_main_reparent_fn_t main_reparent_fn,
		ptrace_report_detach_fn_t report_detach_fn,
		ptrace_cleanup_fn_t cleanup_fn,
		ptrace_free_fn_t free_fn,
		ptrace_clear_single_step_fn_t clear_single_step_fn,
		ptrace_report_attach_fn_t report_attach_fn,
		ptrace_thread_exit_signal_fn_t exit_signal_fn,
		ptrace_do_kill_thread_fn_t do_kill_fn,
		ptrace_wakeup_thread_fn_t wakeup_fn,
		wait_thread_side_effect_fn_t release_fn,
		ptrace_finalize_process_fn_t finalize_fn,
		void *lock_node);
SYSCALL_POLICY_HELPER_PROTO int ptrace_report_clone_body_result(
		void *thread, void *new_thread, int event,
		void *current_thread,
		const struct ptrace_report_clone_offsets *offsets,
		void *lock_node, void *new_lock_node,
		ptrace_rwlock_fn_t lock_fn,
		ptrace_rwlock_fn_t unlock_fn,
		ptrace_attach_thread_fn_t attach_fn,
		ptrace_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn,
		ptrace_control_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int ptrace_syscall_event_body_result(
		void *thread, size_t thread_ptrace_offset,
		ptrace_report_signal_fn_t report_signal_fn);
SYSCALL_POLICY_HELPER_PROTO int ptrace_report_exec_body_result(
		void *thread, void *syscall_ctx,
		const struct ptrace_report_exec_offsets *offsets,
		size_t kernel_context_size, size_t user_context_size,
		void *kernel_context_scratch,
		ptrace_void_fn_t preempt_enable_fn,
		ptrace_void_fn_t preempt_disable_fn,
		ptrace_report_signal_fn_t report_signal_fn,
		ptrace_arch_syscall_event_fn_t arch_syscall_event_fn);
SYSCALL_POLICY_HELPER_PROTO int ptrace_setsiginfo_target_result(
		int status, int has_sendsig, int has_recvsig);
SYSCALL_POLICY_HELPER_PROTO int ptrace_getsiginfo_prepare_result(
		int status, unsigned long pending_addr,
		unsigned long info_offset, void *outp, size_t info_size);
SYSCALL_POLICY_HELPER_PROTO int ptrace_setsiginfo_store_result(
		unsigned long thread_addr, unsigned long sendsig_offset,
		unsigned long recvsig_offset, unsigned long info_offset,
		int target, unsigned long allocated_sendsig, const void *infop,
		size_t info_size);
SYSCALL_POLICY_HELPER_PROTO long ptrace_read_user_words_result(
		unsigned long thread_addr, unsigned long *outp, size_t bytes,
		ptrace_read_user_word_fn_t read_fn);
SYSCALL_POLICY_HELPER_PROTO long ptrace_write_user_words_result(
		unsigned long thread_addr, const unsigned long *inp,
		size_t bytes, ptrace_write_user_word_fn_t write_fn);
SYSCALL_POLICY_HELPER_PROTO long ptrace_read_vm_word_result(int status,
		unsigned long vm_addr, unsigned long user_addr,
		unsigned long *outp, ptrace_read_vm_word_fn_t read_fn);
SYSCALL_POLICY_HELPER_PROTO long ptrace_write_vm_word_result(int status,
		unsigned long vm_addr, unsigned long user_addr,
		unsigned long value, ptrace_write_vm_word_fn_t write_fn);
SYSCALL_POLICY_HELPER_PROTO int ptrace_request_dispatch_result(long request);
SYSCALL_POLICY_HELPER_PROTO long ptrace_syscall_body_result(long request,
		int pid, long addr, long data,
		const struct ptrace_syscall_ops *ops);
SYSCALL_POLICY_HELPER_PROTO int wait4_options_result(int options);
SYSCALL_POLICY_HELPER_PROTO int waitid_to_wait_pid_result(int idtype, int id,
		int *pidp);
SYSCALL_POLICY_HELPER_PROTO int waitid_options_result(int options);
SYSCALL_POLICY_HELPER_PROTO int wait_should_scan_process_result(int options);
SYSCALL_POLICY_HELPER_PROTO int wait_should_scan_thread_result(int pid,
		int options);
SYSCALL_POLICY_HELPER_PROTO int wait_process_pid_matches_result(int pid,
		int parent_pgid, int child_pgid, int child_pid);
SYSCALL_POLICY_HELPER_PROTO int wait_thread_tid_matches_result(int tid,
		int child_tid, int is_main_thread);
SYSCALL_POLICY_HELPER_PROTO int wait_process_exited_candidate_result(
		int options, int child_status);
SYSCALL_POLICY_HELPER_PROTO int wait_thread_exited_candidate_result(
		int options, int child_status);
SYSCALL_POLICY_HELPER_PROTO int wait_nonptraced_stop_candidate_result(
		int ptrace, int signal_flags, int options);
SYSCALL_POLICY_HELPER_PROTO int wait_ptraced_stop_candidate_result(int ptrace,
		int status);
SYSCALL_POLICY_HELPER_PROTO int wait_continued_candidate_result(
		int signal_flags, int options);
SYSCALL_POLICY_HELPER_PROTO int wait_reap_needed_result(int options);
SYSCALL_POLICY_HELPER_PROTO int wait_nohang_result(int options);
SYSCALL_POLICY_HELPER_PROTO int wait_empty_result(int empty);
SYSCALL_POLICY_HELPER_PROTO int wait_stopped_status_result(int exit_status);
SYSCALL_POLICY_HELPER_PROTO int wait_continued_status_result(void);
SYSCALL_POLICY_HELPER_PROTO int wait_continued_body_result(
		struct thread *c_thread, struct process *child, int *status,
		int options, unsigned long child_pid_offset,
		unsigned long child_main_thread_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_signal_flags_offset,
		wait_signal_flags_reap_fn_t reap_fn);
SYSCALL_POLICY_HELPER_PROTO int wait_stopped_body_result(
		struct thread *c_thread, struct process *child, int *status,
		int options, unsigned long child_pid_offset,
		unsigned long child_status_offset,
		unsigned long child_group_exit_status_offset,
		unsigned long child_main_thread_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_exit_status_offset,
		wait_exit_status_reap_fn_t reap_fn);
SYSCALL_POLICY_HELPER_PROTO int do_wait_body_result(int pid, int *status,
		int options, void *rusage, void *thread, void *wait_entry,
		unsigned long thread_proc_offset,
		unsigned long proc_pid_offset,
		unsigned long proc_waitpid_q_offset,
		int interruptible_status,
		wait_scan_fn_t wait_proc_fn,
		wait_scan_fn_t wait_thread_fn,
		wait_entry_init_fn_t init_fn,
		wait_prepare_fn_t prepare_fn,
		wait_finish_fn_t finish_fn,
		wait_has_signal_fn_t has_signal_fn,
		wait_schedule_fn_t schedule_fn,
		wait_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int wait_process_candidate_body_result(
		int current_ret, int pid, int *status, int options,
		void *thread, void *child_proc, void *child_thread,
		void *parent_children_lock, void *parent_children_lock_node,
		void *child_threads_lock, void *child_threads_lock_node,
		unsigned long child_pid_offset,
		unsigned long child_status_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_ptrace_offset,
		unsigned long thread_signal_flags_offset,
		wait_status_fn_t stopped_fn,
		wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		wait_lock_unlock_fn_t unlock_fn,
		int *foundp);
SYSCALL_POLICY_HELPER_PROTO int wait_thread_candidate_body_result(
		int current_ret, int tid, int *status, int options,
		void *thread, void *child_thread, void *threads_lock,
		void *threads_lock_node, unsigned long thread_proc_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_status_offset,
		unsigned long thread_ptrace_offset,
		unsigned long thread_signal_flags_offset,
		wait_status_fn_t stopped_fn,
		wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_thread_report_detach_fn_t report_detach_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_fn,
		int *foundp);
SYSCALL_POLICY_HELPER_PROTO int wait_process_zombie_body_result(
		void *thread, void *parent_proc, void *child_proc, int *status,
		int options, void *rusage, void *parent_children_lock,
		void *parent_children_lock_node, void *pid1,
		const struct wait_zombie_offsets *offsets,
		wait_host_wait4_fn_t host_wait4_fn,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_list_detach_fn_t list_detach_fn,
		wait_list_add_tail_fn_t list_add_tail_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_process_fn,
		wait_zombie_log_fn_t log_fn, void *parent_update_lock_node,
		void *child_update_lock_node, void *pid1_children_lock_node,
		void *child_threads_lock_node);
SYSCALL_POLICY_HELPER_PROTO int wait_process_scan_body_result(
		int pid, int *status, int options, void *rusage, int *empty,
		void *thread, void *proc, void *pid1,
		const struct wait_scan_offsets *scan_offsets,
		const struct wait_zombie_offsets *zombie_offsets,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_host_wait4_fn_t host_wait4_fn,
		wait_list_detach_fn_t list_detach_fn,
		wait_list_add_tail_fn_t list_add_tail_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_process_fn,
		wait_zombie_log_fn_t zombie_log_fn,
		wait_status_fn_t stopped_fn,
		wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		void *parent_children_lock_node,
		void *child_threads_lock_node,
		void *parent_update_lock_node,
		void *child_update_lock_node,
		void *pid1_children_lock_node);
SYSCALL_POLICY_HELPER_PROTO int wait_thread_scan_body_result(
		int tid, int *status, int options, void *rusage, int *empty,
		void *thread, void *proc,
		const struct wait_scan_offsets *offsets,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_status_fn_t stopped_fn,
		wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		wait_thread_report_detach_fn_t report_detach_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_fn,
		void *threads_lock_node);
SYSCALL_POLICY_HELPER_PROTO int wait_zombie_skip_host_result(
		int ppid_parent_pid, int current_pid, int nowait);
SYSCALL_POLICY_HELPER_PROTO int wait_thread_empty_candidate_result(
		int is_main_thread, int termsig);
SYSCALL_POLICY_HELPER_PROTO int waitid_status_code_result(int status);
SYSCALL_POLICY_HELPER_PROTO int wait_stopped_source_result(int has_c_thread,
		int c_thread_exit_status, int child_status,
		int child_group_exit_status, int main_thread_exit_status);
SYSCALL_POLICY_HELPER_PROTO int wait_stopped_exit_status_result(int source,
		int c_thread_exit_status, int child_group_exit_status,
		int main_thread_exit_status);
SYSCALL_POLICY_HELPER_PROTO int wait_report_id_result(int source,
		int child_pid, int c_thread_tid);
SYSCALL_POLICY_HELPER_PROTO int wait_reaped_exit_status_result(int options,
		int exit_status);
SYSCALL_POLICY_HELPER_PROTO int wait_reaped_signal_flags_result(int options,
		int signal_flags, int clear_mask);
SYSCALL_POLICY_HELPER_PROTO int wait_process_reparent_needed_result(
		int options, int parent_is_ppid);
SYSCALL_POLICY_HELPER_PROTO int wait_main_thread_ptrace_detach_needed_result(
		int options, int ptrace);
SYSCALL_POLICY_HELPER_PROTO int wait_thread_reap_action_result(int options,
		int ptrace);
SYSCALL_POLICY_HELPER_PROTO int wait_status_copy_needed_result(int rc,
		int has_status);
SYSCALL_POLICY_HELPER_PROTO int wait_rusage_copy_needed_result(int has_rusage);
SYSCALL_POLICY_HELPER_PROTO long wait4_body_result(int pid,
		unsigned long status_addr, int options, unsigned long rusage_addr,
		wait4_do_wait_fn_t do_wait_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO int waitid_siginfo_needed_result(int rc,
		int has_infop);
SYSCALL_POLICY_HELPER_PROTO void waitid_copy_siginfo_result(int rc,
		unsigned long infop_addr, int status, long utime_sec,
		long utime_usec, long stime_sec, long stime_usec,
		syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO long waitid_body_result(int idtype, int id,
		unsigned long infop_addr, int options,
		wait4_do_wait_fn_t do_wait_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO int getrusage_dispatch_result(int who);
SYSCALL_POLICY_HELPER_PROTO int getrusage_thread_update_action_result(
		int is_current_thread, int status, int in_kernel);
SYSCALL_POLICY_HELPER_PROTO int
getrusage_thread_times_update_prepare_result(unsigned long thread_addr,
		unsigned long times_update_offset, int update_action);
SYSCALL_POLICY_HELPER_PROTO long getrusage_maxrss_kb_result(long maxrss);
SYSCALL_POLICY_HELPER_PROTO void getrusage_timespec_add_tsc_result(
		long *secp, long *nsecp, unsigned long tsc,
		unsigned long clocks_per_sec);
SYSCALL_POLICY_HELPER_PROTO void getrusage_fill_timespec_result(
		struct rusage *usage, long utime_sec, long utime_nsec,
		long stime_sec, long stime_nsec, long maxrss);
SYSCALL_POLICY_HELPER_PROTO long getrusage_body_result(int who,
		unsigned long usage_addr, void *thread,
		unsigned long clocks_per_sec,
		const struct syscall_cputime_offsets *offsets,
		syscall_threads_lock_fn_t lock_fn,
		syscall_threads_unlock_fn_t unlock_fn, void *lock_arg,
		syscall_interrupt_cpu_fn_t interrupt_fn,
		syscall_cpu_pause_fn_t pause_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO long clock_gettime_body_result(int clock_id,
		unsigned long ts_addr, int local_support, int syscall_nr,
		void *thread, unsigned long clocks_per_sec,
		const struct syscall_cputime_offsets *offsets,
		syscall_gettime_fn_t gettime_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_do_syscall2_fn_t syscall2_fn,
		syscall_threads_lock_fn_t lock_fn,
		syscall_threads_unlock_fn_t unlock_fn, void *lock_arg,
		syscall_interrupt_cpu_fn_t interrupt_fn,
		syscall_cpu_pause_fn_t pause_fn);
SYSCALL_POLICY_HELPER_PROTO int exit_code_status_result(int code);
SYSCALL_POLICY_HELPER_PROTO int exit_code_signal_result(int code);
SYSCALL_POLICY_HELPER_PROTO int exit_syscall_code_result(int status);
SYSCALL_POLICY_HELPER_PROTO long exit_body_result(int status,
		syscall_exit_fn_t exit_fn);
SYSCALL_POLICY_HELPER_PROTO long exit_group_body_result(int status, int pid,
		syscall_exit_group_log_fn_t log_fn,
		syscall_terminate_fn_t terminate_fn);
SYSCALL_POLICY_HELPER_PROTO long sched_yield_body_result(void *cpu_local,
		size_t flags_offset, size_t runq_len_offset,
		size_t runq_lock_offset, unsigned int need_resched_flag,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_schedule_fn_t schedule_fn);
SYSCALL_POLICY_HELPER_PROTO int thread_exit_signal_result(int ptrace,
		int termsig);
SYSCALL_POLICY_HELPER_PROTO int thread_exit_signal_report_needed_result(
		const void *report_proc);
SYSCALL_POLICY_HELPER_PROTO int sigchld_code_result(int exit_status);
SYSCALL_POLICY_HELPER_PROTO long thread_exit_signal_body_result(void *thread,
		size_t thread_report_proc_offset, size_t thread_ptrace_offset,
		size_t thread_termsig_offset,
		size_t thread_exit_status_offset, size_t thread_tid_offset,
		size_t thread_user_tsc_offset, size_t thread_system_tsc_offset,
		size_t proc_pid_offset, size_t proc_waitpid_q_offset,
		syscall_tsc_to_ts_fn_t tsc_to_ts_fn,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn, thread_exit_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO long finalize_process_parent_notify_body_result(
		void *proc, size_t proc_parent_offset, size_t proc_pid_offset,
		size_t proc_group_exit_status_offset, size_t proc_termsig_offset,
		size_t proc_utime_offset, size_t proc_stime_offset,
		size_t proc_waitpid_q_offset,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn, thread_exit_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO long finalize_process_body_result(void *proc,
		const void *pid1, void *lock_node,
		size_t proc_parent_offset, size_t proc_status_offset,
		size_t proc_update_lock_offset, size_t proc_pid_offset,
		size_t proc_group_exit_status_offset, size_t proc_termsig_offset,
		size_t proc_utime_offset, size_t proc_stime_offset,
		size_t proc_waitpid_q_offset, wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_thread_side_effect_fn_t release_fn,
		finalize_wakeup_log_fn_t wakeup_log_fn,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn, thread_exit_log_fn_t log_fn);
SYSCALL_POLICY_HELPER_PROTO int exit_group_status_claimed_result(
		unsigned long old_exit_status);
SYSCALL_POLICY_HELPER_PROTO int terminate_group_status_update_failed_result(
		unsigned long observed_status, unsigned long expected_status);
SYSCALL_POLICY_HELPER_PROTO int terminate_host_exit_needed_result(
		int nohost);
SYSCALL_POLICY_HELPER_PROTO long terminate_mcexec_body_result(void *proc,
		struct syscall_request *request, int rc, int sig, int cpu,
		int exit_group_nr, size_t proc_group_exit_status_offset,
		size_t proc_nohost_offset,
		terminate_mcexec_cmpxchg_fn_t cmpxchg_fn,
		terminate_mcexec_syscall_fn_t syscall_fn);
SYSCALL_POLICY_HELPER_PROTO int sync_child_event_needed_result(
		int has_event, int inherit, int pid);
SYSCALL_POLICY_HELPER_PROTO int sync_child_event_pid_action_result(int pid);
SYSCALL_POLICY_HELPER_PROTO long sync_child_event_body_result(void *event,
		int inherit, int pid, size_t group_leader_offset,
		size_t event_pid_offset, size_t counter_id_offset,
		size_t count_offset, size_t child_count_total_offset,
		size_t sibling_list_offset, size_t group_entry_offset,
		sync_child_perf_read_fn_t read_fn,
		sync_child_atomic64_set_fn_t set_fn);
SYSCALL_POLICY_HELPER_PROTO unsigned long perf_event_read_value_body_result(
		void *event, void *thread, int exclude_user,
		int exclude_kernel, int inherit, size_t event_pid_offset,
		size_t use_invariant_tsc_offset, size_t count_offset,
		size_t child_count_total_offset, size_t base_user_tsc_offset,
		size_t stopped_user_tsc_offset, size_t user_accum_count_offset,
		size_t base_system_tsc_offset, size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset,
		size_t thread_user_tsc_offset, size_t thread_system_tsc_offset,
		perf_event_update_fn_t update_fn,
		syscall_atomic64_read_fn_t atomic_read_fn);
SYSCALL_POLICY_HELPER_PROTO unsigned long
perf_event_read_value_entry_body_result(void *event, void *thread,
		size_t event_attr_offset, size_t event_pid_offset,
		size_t use_invariant_tsc_offset, size_t count_offset,
		size_t child_count_total_offset, size_t base_user_tsc_offset,
		size_t stopped_user_tsc_offset, size_t user_accum_count_offset,
		size_t base_system_tsc_offset, size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset, size_t thread_user_tsc_offset,
		size_t thread_system_tsc_offset,
		perf_read_attr_flags_fn_t attr_flags_fn,
		perf_event_update_fn_t update_fn,
		syscall_atomic64_read_fn_t atomic_read_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_event_read_one_body_result(
		void *event, unsigned long buf_addr,
		perf_read_value_fn_t read_value_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_event_read_group_body_result(
		void *event, unsigned long buf_addr,
		size_t group_leader_offset, size_t nr_siblings_offset,
		size_t sibling_list_offset, size_t group_entry_offset,
		perf_read_value_fn_t read_value_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_read_body_result(void *event,
		unsigned long buf_addr, unsigned long read_format,
		unsigned long group_flag, perf_read_dispatch_fn_t read_group_fn,
		perf_read_dispatch_fn_t read_one_fn);
SYSCALL_POLICY_HELPER_PROTO int perf_counter_set_body_result(void *event,
		int exclude_kernel, int exclude_user, int counter_id,
		unsigned long hw_config, size_t extra_reg_reg_offset,
		int kernel_mode, int user_mode,
		perf_counter_extra_set_fn_t set_extra_fn,
		perf_counter_init_raw_fn_t init_raw_fn);
SYSCALL_POLICY_HELPER_PROTO int perf_counter_set_entry_body_result(void *event,
		size_t event_attr_offset, size_t event_counter_id_offset,
		size_t event_hw_config_offset, size_t extra_reg_reg_offset,
		int kernel_mode, int user_mode,
		perf_counter_attr_flags_fn_t attr_flags_fn,
		perf_counter_extra_set_fn_t set_extra_fn,
		perf_counter_init_raw_fn_t init_raw_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_start_body_result(void *event,
		void *thread, size_t group_leader_offset,
		size_t sibling_list_offset, size_t group_entry_offset,
		size_t counter_id_offset, size_t state_offset,
		size_t use_invariant_tsc_offset, size_t base_user_tsc_offset,
		size_t stopped_user_tsc_offset,
		size_t user_accum_count_offset,
		size_t base_system_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset,
		size_t thread_user_tsc_offset,
		size_t thread_system_tsc_offset,
		size_t thread_proc_offset, size_t proc_perf_status_offset,
		int inactive_state, int active_state, int pp_count,
		perf_counter_mask_check_fn_t mask_check_fn,
		perf_event_int_fn_t set_period_fn,
		perf_event_int_fn_t counter_set_fn,
		perf_counter_start_fn_t counter_start_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_reset_body_result(void *event,
		void *thread, size_t group_leader_offset,
		size_t sibling_list_offset, size_t group_entry_offset,
		size_t counter_id_offset, size_t use_invariant_tsc_offset,
		size_t base_user_tsc_offset,
		size_t stopped_user_tsc_offset,
		size_t user_accum_count_offset,
		size_t base_system_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset, size_t count_offset,
		size_t thread_user_tsc_offset,
		size_t thread_system_tsc_offset,
		perf_counter_mask_check_fn_t mask_check_fn,
		perf_read_value_fn_t read_value_fn,
		sync_child_atomic64_set_fn_t atomic_set_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_stop_body_result(void *event,
		void *thread, size_t group_leader_offset,
		size_t sibling_list_offset, size_t group_entry_offset,
		size_t counter_id_offset, size_t state_offset,
		size_t use_invariant_tsc_offset,
		size_t stopped_user_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t thread_user_tsc_offset,
		size_t thread_system_tsc_offset,
		size_t thread_proc_offset,
		size_t proc_monitoring_event_offset,
		size_t proc_perf_status_offset, int active_state,
		int inactive_state, int pp_none, int stop_flags,
		perf_counter_mask_check_fn_t mask_check_fn,
		perf_counter_stop_fn_t counter_stop_fn,
		perf_event_update_fn_t update_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_ioctl_body_result(void *event,
		void *current_proc, void *lock_arg, unsigned long cmd,
		int inherit, unsigned long enable_cmd,
		unsigned long disable_cmd, unsigned long reset_cmd,
		unsigned long refresh_cmd, int pp_reset,
		size_t event_pid_offset,
		size_t proc_monitoring_event_offset,
		size_t proc_perf_status_offset,
		perf_event_void_fn_t start_fn, perf_event_void_fn_t stop_fn,
		perf_event_void_fn_t reset_fn,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_close_body_result(void *event,
		void *thread, size_t counter_id_offset,
		size_t extra_reg_reg_offset, size_t extra_reg_idx_offset,
		size_t thread_pmc_alloc_map_offset,
		size_t thread_extra_reg_alloc_map_offset,
		syscall_mckfd_free_fn_t free_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_fcntl_body_result(void *sfd,
		void *ctx, int cmd, long arg, int fcntl_nr,
		int set_sig_cmd, int setown_ex_cmd,
		size_t mckfd_sig_no_offset,
		syscall_forward_context_fn_t forward_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_mmap_body_result(unsigned long addr0,
		size_t len0, int prot, int flags, int fd, long off0,
		int map_anonymous, int prot_write, size_t data_head_offset,
		size_t capabilities_offset, unsigned long cap_user_rdpmc_mask,
		perf_do_mmap_fn_t do_mmap_fn);
SYSCALL_POLICY_HELPER_PROTO int perf_event_open_validate_body_result(
		int cpu, unsigned long flags, unsigned long attr_type,
		unsigned long read_format, int freq,
		unsigned long sample_period, unsigned long raw_type,
		unsigned long hardware_type, unsigned long hw_cache_type,
		unsigned long unsupported_read_format_mask,
		unsigned long sample_period_sign_bit);
SYSCALL_POLICY_HELPER_PROTO long perf_event_alloc_init_body_result(
		void *event, const void *attr, size_t event_size,
		size_t attr_size, size_t event_attr_offset,
		size_t group_entry_offset, size_t sibling_list_offset,
		size_t sample_freq_offset, size_t nr_siblings_offset,
		size_t count_offset, size_t child_count_total_offset,
		size_t parent_offset, size_t hw_sample_period_offset,
		size_t hw_last_period_offset, size_t hw_period_left_offset,
		size_t use_invariant_tsc_offset, unsigned long attr_type,
		unsigned long attr_config, int attr_freq,
		unsigned long attr_sample_freq, unsigned long attr_sample_period,
		unsigned long hardware_type, unsigned long ref_cpu_cycles_config,
		sync_child_atomic64_set_fn_t atomic_set_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_event_alloc_map_body_result(
		void **event_out, void *event, size_t hw_config_offset,
		size_t hw_config_ext_offset, size_t extra_reg_config_offset,
		size_t extra_reg_reg_offset, size_t extra_reg_idx_offset,
		unsigned long attr_type, unsigned long attr_config,
		unsigned long hardware_type, unsigned long hw_cache_type,
		unsigned long raw_type, perf_event_map_fn_t hw_event_map_fn,
		perf_event_map_fn_t hw_cache_event_map_fn,
		perf_event_map_fn_t hw_cache_extra_reg_map_fn,
		perf_event_map_fn_t raw_event_map_fn,
		perf_event_validate_fn_t validate_event_fn,
		perf_extra_reg_id_fn_t extra_reg_id_fn,
		perf_extra_reg_msr_fn_t extra_reg_msr_fn,
		perf_extra_reg_idx_fn_t extra_reg_idx_fn,
		perf_hw_event_init_fn_t hw_event_init_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_event_alloc_body_result(
		void **event_out, const void *attr, size_t event_size,
		size_t attr_size, unsigned long alloc_flags,
		size_t event_attr_offset, size_t group_entry_offset,
		size_t sibling_list_offset, size_t sample_freq_offset,
		size_t nr_siblings_offset, size_t count_offset,
		size_t child_count_total_offset, size_t parent_offset,
		size_t hw_sample_period_offset, size_t hw_last_period_offset,
		size_t hw_period_left_offset, size_t use_invariant_tsc_offset,
		size_t hw_config_offset, size_t hw_config_ext_offset,
		size_t extra_reg_config_offset, size_t extra_reg_reg_offset,
		size_t extra_reg_idx_offset, unsigned long attr_type,
		unsigned long attr_config, int attr_freq,
		unsigned long attr_sample_freq, unsigned long attr_sample_period,
		unsigned long hardware_type, unsigned long hw_cache_type,
		unsigned long raw_type, unsigned long ref_cpu_cycles_config,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn,
		sync_child_atomic64_set_fn_t atomic_set_fn,
		perf_event_map_fn_t hw_event_map_fn,
		perf_event_map_fn_t hw_cache_event_map_fn,
		perf_event_map_fn_t hw_cache_extra_reg_map_fn,
		perf_event_map_fn_t raw_event_map_fn,
		perf_event_validate_fn_t validate_event_fn,
		perf_extra_reg_id_fn_t extra_reg_id_fn,
		perf_extra_reg_msr_fn_t extra_reg_msr_fn,
		perf_extra_reg_idx_fn_t extra_reg_idx_fn,
		perf_hw_event_init_fn_t hw_event_init_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_event_open_group_body_result(
		void *event, void *proc, int group_fd, int counter_idx,
		size_t proc_mckfd_offset, size_t mckfd_next_offset,
		size_t mckfd_fd_offset, size_t mckfd_data_offset,
		size_t event_group_leader_offset,
		size_t event_sibling_list_offset,
		size_t event_group_entry_offset,
		size_t event_nr_siblings_offset,
		size_t event_pmc_status_offset);
SYSCALL_POLICY_HELPER_PROTO long perf_event_open_counter_body_result(
		void *event, void *thread, int pid, size_t event_pid_offset,
		size_t event_counter_id_offset,
		perf_counter_alloc_fn_t counter_alloc_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_event_open_linux_fd_body_result(
		struct syscall_request *request, void *thread, int counter_idx,
		int perf_event_open_nr, int cpu,
		size_t thread_pmc_alloc_map_offset,
		perf_open_syscall_fn_t syscall_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_event_open_mckfd_publish_body_result(
		void *sfd, void *event, void *proc, int fd,
		size_t proc_mckfd_lock_offset, size_t proc_mckfd_offset,
		size_t mckfd_next_offset, size_t mckfd_fd_offset,
		size_t mckfd_sig_no_offset, size_t mckfd_data_offset,
		size_t mckfd_read_cb_offset, size_t mckfd_ioctl_cb_offset,
		size_t mckfd_mmap_cb_offset, size_t mckfd_close_cb_offset,
		size_t mckfd_fcntl_cb_offset,
		syscall_mckfd_long_fn_t read_fn,
		syscall_mckfd_int_fn_t ioctl_fn,
		syscall_mckfd_long_fn_t mmap_fn,
		syscall_mckfd_int_fn_t close_fn,
		syscall_mckfd_int_fn_t fcntl_fn,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_event_open_body_result(
		struct syscall_request *request, void *thread, void *proc,
		void *attr, int pid, int group_fd, int perf_event_open_nr,
		int cpu, size_t mckfd_size, unsigned long mckfd_alloc_flags,
		size_t event_pid_offset, size_t event_counter_id_offset,
		size_t proc_mckfd_offset, size_t mckfd_next_offset,
		size_t mckfd_fd_offset, size_t mckfd_data_offset,
		size_t event_group_leader_offset,
		size_t event_sibling_list_offset,
		size_t event_group_entry_offset,
		size_t event_nr_siblings_offset,
		size_t event_pmc_status_offset,
		size_t thread_pmc_alloc_map_offset,
		size_t proc_mckfd_lock_offset, size_t mckfd_sig_no_offset,
		size_t mckfd_read_cb_offset, size_t mckfd_ioctl_cb_offset,
		size_t mckfd_mmap_cb_offset, size_t mckfd_close_cb_offset,
		size_t mckfd_fcntl_cb_offset,
		perf_open_event_alloc_fn_t event_alloc_fn,
		perf_counter_alloc_fn_t counter_alloc_fn,
		perf_open_syscall_fn_t syscall_fn,
		syscall_policy_alloc_fn_t mckfd_alloc_fn,
		syscall_mckfd_long_fn_t read_fn,
		syscall_mckfd_int_fn_t ioctl_fn,
		syscall_mckfd_long_fn_t mmap_fn,
		syscall_mckfd_int_fn_t close_fn,
		syscall_mckfd_int_fn_t fcntl_fn,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn);
SYSCALL_POLICY_HELPER_PROTO long perf_event_open_entry_body_result(
		struct syscall_request *request, void *thread, void *proc,
		void *attr, unsigned long user_attr_addr, size_t attr_size,
		size_t attr_type_offset, size_t attr_read_format_offset,
		size_t attr_sample_period_offset, int pid, int validation_cpu,
		int group_fd, unsigned long flags, int linux_cpu,
		unsigned long raw_type, unsigned long hardware_type,
		unsigned long hw_cache_type,
		unsigned long unsupported_read_format_mask,
		unsigned long sample_period_sign_bit, int perf_event_open_nr,
		size_t mckfd_size, unsigned long mckfd_alloc_flags,
		size_t event_pid_offset, size_t event_counter_id_offset,
		size_t proc_mckfd_offset, size_t mckfd_next_offset,
		size_t mckfd_fd_offset, size_t mckfd_data_offset,
		size_t event_group_leader_offset,
		size_t event_sibling_list_offset,
		size_t event_group_entry_offset,
		size_t event_nr_siblings_offset,
		size_t event_pmc_status_offset,
		size_t thread_pmc_alloc_map_offset,
		size_t proc_mckfd_lock_offset, size_t mckfd_sig_no_offset,
		size_t mckfd_read_cb_offset, size_t mckfd_ioctl_cb_offset,
		size_t mckfd_mmap_cb_offset, size_t mckfd_close_cb_offset,
		size_t mckfd_fcntl_cb_offset,
		syscall_copy_from_user_fn_t copy_from_fn,
		perf_attr_freq_fn_t attr_freq_fn,
		perf_open_event_alloc_fn_t event_alloc_fn,
		perf_counter_alloc_fn_t counter_alloc_fn,
		perf_open_syscall_fn_t syscall_fn,
		syscall_policy_alloc_fn_t mckfd_alloc_fn,
		syscall_mckfd_long_fn_t read_fn,
		syscall_mckfd_int_fn_t ioctl_fn,
		syscall_mckfd_long_fn_t mmap_fn,
		syscall_mckfd_int_fn_t close_fn,
		syscall_mckfd_int_fn_t fcntl_fn,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn);
SYSCALL_POLICY_HELPER_PROTO unsigned long exit_group_status_result(int rc,
		int sig);
SYSCALL_POLICY_HELPER_PROTO int terminate_thread_active_result(int status);
SYSCALL_POLICY_HELPER_PROTO int terminate_process_exited_result(int status);
SYSCALL_POLICY_HELPER_PROTO int terminate_thread_is_other_result(
		const void *thread, const void *current_thread);
SYSCALL_POLICY_HELPER_PROTO int terminate_report_thread_ptrace_result(
		int ptrace);
SYSCALL_POLICY_HELPER_PROTO int terminate_child_cleanup_needed_result(
		int children_empty, int ptraced_children_empty);
SYSCALL_POLICY_HELPER_PROTO int terminate_release_child_needed_result(
		int free_child);
SYSCALL_POLICY_HELPER_PROTO int process_lookup_missing_result(
		const void *process);
SYSCALL_POLICY_HELPER_PROTO int process_cleanup_tofu_needed_result(
		int enable_tofu);
SYSCALL_POLICY_HELPER_PROTO int process_cleanup_fd_path_free_needed_result(
		const void *path);
SYSCALL_POLICY_HELPER_PROTO long process_cleanup_fd_body_result(int pid,
		int fd, void *lock_arg, syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		process_cleanup_fd_fn_t cleanup_fn,
		process_cleanup_missing_log_fn_t missing_log_fn);
SYSCALL_POLICY_HELPER_PROTO long process_cleanup_before_terminate_body_result(
		int pid, void *lock_arg, int enable_tofu, int first_fd,
		int max_fd, syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		process_cleanup_fd_fn_t cleanup_fn);
SYSCALL_POLICY_HELPER_PROTO int
terminate_host_detached_thread_release_needed_result(const void *process,
		const void *thread);
SYSCALL_POLICY_HELPER_PROTO int terminate_host_kill_needed_result(int nohost);
SYSCALL_POLICY_HELPER_PROTO long terminate_host_body_result(int pid,
		void *detached_thread, void *current_thread, void *lock_arg,
		size_t proc_nohost_offset, size_t thread_proc_offset,
		size_t thread_refcount_offset,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		terminate_host_ref_set_fn_t ref_set_fn,
		wait_thread_side_effect_fn_t release_thread_fn,
		wait_thread_side_effect_fn_t release_process_fn,
		syscall_do_kill_thread_fn_t do_kill_fn);
SYSCALL_POLICY_HELPER_PROTO int finalize_process_parent_is_pid1_result(
		const void *parent, const void *pid1);
SYSCALL_POLICY_HELPER_PROTO int finalize_process_parent_signal_needed_result(
		int termsig);
SYSCALL_POLICY_HELPER_PROTO int terminate_status_result(int rc, int sig);
SYSCALL_POLICY_HELPER_PROTO int terminate_report_thread_release_needed_result(
		int same_process, int termsig);
SYSCALL_POLICY_HELPER_PROTO int terminate_child_action_result(
		int ppid_is_exiting, int parent_is_exiting, int child_status);
SYSCALL_POLICY_HELPER_PROTO int clone_pthread_marker_result(int clone_flags,
		unsigned long newsp, unsigned long parent_tidptr);
SYSCALL_POLICY_HELPER_PROTO int clone_flags_result(int clone_flags,
		int coredump_barrier_count);
SYSCALL_POLICY_HELPER_PROTO int clone_host_parent_flags_result(
		int clone_flags, int ppid_parent_pid);
SYSCALL_POLICY_HELPER_PROTO int clone_report_thread_result(int clone_flags,
		int termsig);
SYSCALL_POLICY_HELPER_PROTO int clone_parent_tid_store_needed_result(
		int clone_flags);
SYSCALL_POLICY_HELPER_PROTO int clone_child_cleartid_needed_result(
		int clone_flags);
SYSCALL_POLICY_HELPER_PROTO int clone_child_tid_store_needed_result(
		int clone_flags);
SYSCALL_POLICY_HELPER_PROTO int clone_tls_source_result(int clone_flags);
SYSCALL_POLICY_HELPER_PROTO int clone_use_last_cpu_result(int mod_clone,
		int uti_use_last_cpu);
SYSCALL_POLICY_HELPER_PROTO int clone_remote_spawn_result(
		int previous_mod_clone);
SYSCALL_POLICY_HELPER_PROTO int clone_parent_use_pid1_result(
		int parent_status);
SYSCALL_POLICY_HELPER_PROTO int ptrace_exec_event_signal_result(int ptrace);
SYSCALL_POLICY_HELPER_PROTO int ptrace_syscall_event_signal_result(int ptrace);
SYSCALL_POLICY_HELPER_PROTO int ptrace_clone_event_result(int ptrace,
		int clone_flags);
SYSCALL_POLICY_HELPER_PROTO int ptrace_clone_reparent_result(int event);
SYSCALL_POLICY_HELPER_PROTO int execveat_policy_result(int flags, int dirfd,
		int filename_first);
SYSCALL_POLICY_HELPER_PROTO long execveat_body_result(void *ctx, int dirfd,
		const char *filename, char **argv, char **envp, int flags,
		int filename_first, syscall_execveat_fn_t execveat_fn);
SYSCALL_POLICY_HELPER_PROTO long execve_body_result(void *ctx,
		const char *filename, char **argv, char **envp,
		syscall_execveat_fn_t execveat_fn);
SYSCALL_POLICY_HELPER_PROTO int futex_decode_flags_result(int flags,
		int *opp, int *fsharedp);
SYSCALL_POLICY_HELPER_PROTO int futex_wait_timeout_needed_result(int op,
		int has_utime);
SYSCALL_POLICY_HELPER_PROTO int futex_timeout_is_absolute_result(int op);
SYSCALL_POLICY_HELPER_PROTO int futex_clock_id_result(int flags);
SYSCALL_POLICY_HELPER_PROTO unsigned int futex_requeue_val2_result(int op,
		unsigned long arg3);
SYSCALL_POLICY_HELPER_PROTO unsigned long futex_timeout_ns_result(int op,
		long timeout_sec, long timeout_nsec, long now_sec, long now_nsec);
SYSCALL_POLICY_HELPER_PROTO long do_futex_body_result(int n,
		unsigned long arg0, unsigned long arg1, unsigned long arg2,
		unsigned long arg3, unsigned long arg4, unsigned long arg5,
		int has_uti_clv, int local_gettime_support,
		do_futex_syscall_time_fn_t syscall_time_fn,
		do_futex_local_time_fn_t local_time_fn,
		do_futex_linux_time_fn_t linux_time_fn,
		do_futex_ns_per_tsc_fn_t ns_per_tsc_fn,
		do_futex_dispatch_fn_t futex_fn, do_futex_log_fn_t log_fn);
#endif

#undef SYSCALL_POLICY_HELPER_PROTO

void save_syscall_return_value(int num, unsigned long rc);
extern long alloc_debugreg(struct thread *thread);
extern int num_processors;
extern unsigned long ihk_mc_get_ns_per_tsc(void);
extern int ptrace_detach(int pid, int data);
extern void debug_log(unsigned long);
extern long arch_ptrace(long request, int pid, long addr, long data);
extern struct cpu_local_var *clv;

int prepare_process_ranges_args_envs(struct thread *thread, 
		struct program_load_desc *pn,
		struct program_load_desc *p,
		enum ihk_mc_pt_attribute attr,
		char *args, int args_len,
		char *envs, int envs_len);

#ifdef DCFA_KMOD
static void do_mod_exit(int status);
#endif

/* Size of tid table. It needs to be more than #CPUs when CPU
 * oversubscription is needed. The examples of CPU oversubscription are:
 * (1) pmi_proxy + gdb + #CPU OMP threads
 * (2) pmi_proxy + #CPU OMP threads + POSIX AIO IO + POSIX AIO notification
 */
#define OVERSUBSCRIBED_NR_TIDS 128
#define NR_TIDS (allow_oversubscribe ? \
	((num_processors * 2) > OVERSUBSCRIBED_NR_TIDS ? \
	 (num_processors * 2) : OVERSUBSCRIBED_NR_TIDS) : num_processors)

long (*linux_wait_event)(void *_resp, unsigned long nsec_timeout);
int (*linux_printk)(const char *fmt, ...);
int (*linux_clock_gettime)(clockid_t clk_id, struct timespec *tp);

#ifndef MCKERNEL_RUST_SYSCALL_OFFLOAD
static void send_syscall(struct syscall_request *req, int cpu,
			 struct syscall_response *res)
{
	struct ikc_scd_packet packet IHK_DMA_ALIGN;
	struct ihk_ikc_channel_desc *syscall_channel = get_cpu_local_var(cpu)->ikc2linux;
	int ret;
	int prep_rc;
	static int mcexec_v10_send_syscall_logs;
	static int mcexec_v10_send_syscall_pid = -1;
	struct thread *thread = get_this_cpu_local_var()->current;
	int pid = thread && thread->proc ? thread->proc->pid : -1;

	prep_rc = syscall_send_prepare_result(req, res);
	if (prep_rc) {
		kprintf("%s: ERROR: preparing syscall request failed: %d\n",
				__func__, prep_rc);
		return;
	}

	prep_rc = syscall_request_copy_result(&packet.req, req);
	if (prep_rc) {
		kprintf("%s: ERROR: copying syscall request failed: %d\n",
				__func__, prep_rc);
		return;
	}

	prep_rc = syscall_request_publish_result(&packet.req);
	if (prep_rc) {
		kprintf("%s: ERROR: publishing syscall request failed: %d\n",
				__func__, prep_rc);
		return;
	}

#ifdef SYSCALL_BY_IKC
	prep_rc = syscall_packet_traditional_prepare_result(&packet,
			SCD_MSG_SYSCALL_ONESIDE, cpu,
			get_this_cpu_local_var()->current->proc->pid, virt_to_phys(res));
	if (prep_rc) {
		kprintf("%s: ERROR: preparing syscall packet failed: %d\n",
				__func__, prep_rc);
		return;
	}
	dkprintf("send syscall, nr: %d, pid: %d\n", req->number, packet.pid);
	if (syscall_log_budget_result(pid, &mcexec_v10_send_syscall_pid,
			&mcexec_v10_send_syscall_logs, 64) > 0) {
		kprintf("mcexec_v10: send_syscall cpu=%d pid=%d tid=%d nr=%d rip=0x%lx sp=0x%lx\n",
			cpu, packet.pid, thread ? thread->tid : -1,
			req->number,
			thread && thread->uctx ? ihk_mc_syscall_pc(thread->uctx) : 0UL,
			thread && thread->uctx ? ihk_mc_syscall_sp(thread->uctx) : 0UL);
	}

	ret = ihk_ikc_send(syscall_channel, &packet, 0);
	if (ret < 0) {
		kprintf("ERROR: sending IKC msg, ret: %d\n", ret);
	}
#endif
}
#else
extern void send_syscall(struct syscall_request *req, int cpu,
		struct syscall_response *res);
extern void syscall_offload_wait_reply(struct syscall_request *req,
		struct syscall_response *res, int cpu, struct thread *thread);
#endif

long do_syscall(struct syscall_request *req, int cpu)
{
	struct syscall_response res;
	long rc;
	struct thread *thread = get_this_cpu_local_var()->current;
	struct ihk_os_cpu_monitor *monitor = get_this_cpu_local_var()->monitor;
	int mstatus = 0;
	static int mcexec_v10_offload_return_logs;
	static int mcexec_v10_offload_return_pid = -1;
	int pid = thread && thread->proc ? thread->proc->pid : -1;
	int use_requester_tid;

#ifdef PROFILE_ENABLE
	/* We cannot use thread->profile_start_ts here because the
	 * caller may be utilizing it already */
	unsigned long t_s = 0;
	if (thread->profile) {
		t_s = rdtsc();
	}
#endif // PROFILE_ENABLE

	dkprintf("SC(%d)[%3d] sending syscall\n",
		ihk_mc_get_processor_id(),
		req->number);
	
	mstatus = monitor->status;
	monitor->status = IHK_OS_MONITOR_KERNEL_OFFLOAD;
	
	barrier();

	if (syscall_offload_counted_result(req->number, __NR_exit_group)) {
		++thread->in_syscall_offload;
	}

#ifdef ENABLE_FUGAKU_HACKS
#if 0
	if (req->number == __NR_write && req->args[0] == 1) {
		return req->args[2];
	}
#endif
#endif

	/* The current thread is the requester */
	use_requester_tid = syscall_offload_prepare_result(req, &res,
			get_this_cpu_local_var()->current->tid, req->number, req->args[0],
			__NR_sched_setaffinity, IHK_SCD_REQ_THREAD_SPINNING);
	if (use_requester_tid < 0)
		return use_requester_tid;

	if (use_requester_tid) {
		/* mcexec thread serving migrate-to-Linux request must have
		   the same tid as the requesting McKernel thread because the
		   serving thread jumps to hfi driver and then jumps to
		   rus_vm_fault() without registering it into per thread data
		   by mcctrl_add_per_thread_data()). */
		dkprintf("%s: uti, ttid=%d\n", __FUNCTION__, req->ttid);
	}
	send_syscall(req, cpu, &res);

	if (syscall_preempt_disable_needed_result(req->rtid)) {
		preempt_disable();
	}

	dkprintf("%s: syscall num: %d waiting for Linux.. \n",
		__FUNCTION__, req->number);

#ifdef MCKERNEL_RUST_SYSCALL_OFFLOAD
	syscall_offload_wait_reply(req, &res, cpu, thread);
#else
#define	STATUS_IN_PROGRESS	0
#define	STATUS_COMPLETED	1
#define	STATUS_PAGE_FAULT	3
#define	STATUS_SYSCALL		4
#define __NR_syscall_response 8001
	while (smp_load_acquire_ulong(&res.status) != STATUS_COMPLETED) {
		while (smp_load_acquire_ulong(&res.status) == STATUS_IN_PROGRESS) {
			struct cpu_local_var *v;
			int do_schedule = 0;
			long runq_irqstate;
			unsigned long flags;
			waitq_entry_t scd_wq_entry;

			waitq_init_entry(&scd_wq_entry, get_this_cpu_local_var()->current);

#ifdef ENABLE_FUGAKU_HACKS
			if (req->number == __NR_epoll_wait ||
					req->number == __NR_epoll_pwait)
				goto schedule;
#endif

			if (thread->rpf_backlog) {
				void (*func)(void *) = thread->rpf_backlog;
				void *arg = thread->rpf_arg;

				thread->rpf_backlog = NULL;
				thread->rpf_arg = NULL;
				func(arg);
				kfree_tracked(arg, __FILE__, __LINE__);
			}

			check_sig_pending();
			cpu_pause();

			/* Spin if not preemptable */
			if (syscall_offload_spin_without_schedule_result(
					ihk_atomic_read(&get_this_cpu_local_var()->no_preempt),
					thread->tid)) {
				continue;
			}

			/* Spin by default, but if re-schedule is requested let
			 * the other thread run */
			runq_irqstate = cpu_disable_interrupt_save();
			ihk_mc_spinlock_lock_noirq(
				&(get_this_cpu_local_var()->runq_lock));
			v = get_this_cpu_local_var();

			if (syscall_offload_should_schedule_result(0, thread->tid,
			    v->flags & CPU_FLAG_NEED_RESCHED, v->runq_len,
			    req->number == __NR_sched_setaffinity)) {
				v->flags &= ~CPU_FLAG_NEED_RESCHED;
				do_schedule = 1;
			}

			ihk_mc_spinlock_unlock_noirq(&v->runq_lock);
			cpu_restore_interrupt(runq_irqstate);

			if (!do_schedule) {
				ihk_numa_zero_free_pages(ihk_mc_get_numa_node_by_distance(0));
				continue;
			}

#ifdef ENABLE_FUGAKU_HACKS
schedule:
#endif
			flags = cpu_disable_interrupt_save();

			/* Try to sleep until notified */
			if (smp_load_acquire_ulong(&res.req_thread_status) ==
					IHK_SCD_REQ_THREAD_DESCHEDULED ||
					(atomic_cmpxchg_ulong(&res.req_thread_status,
							       IHK_SCD_REQ_THREAD_SPINNING,
							       IHK_SCD_REQ_THREAD_DESCHEDULED) ==
					 IHK_SCD_REQ_THREAD_SPINNING)) {
				dkprintf("%s: tid %d waiting for syscall reply...\n",
						__FUNCTION__, thread->tid);
				waitq_init(&thread->scd_wq);
				waitq_prepare_to_wait(&thread->scd_wq, &scd_wq_entry,
					PS_INTERRUPTIBLE);
				cpu_restore_interrupt(flags);
				schedule();
				waitq_finish_wait(&thread->scd_wq, &scd_wq_entry);
				continue;
			}
			else {
				if (do_schedule) {
					runq_irqstate =
						ihk_mc_spinlock_lock(
							&v->runq_lock);
					v->flags |= CPU_FLAG_NEED_RESCHED;
					ihk_mc_spinlock_unlock(
						&v->runq_lock, runq_irqstate);
				}
			}

			cpu_restore_interrupt(flags);
		}

		if (smp_load_acquire_ulong(&res.status) == STATUS_SYSCALL) {
			struct syscall_request *requestp;
			struct syscall_request request;
			int num;
			ihk_mc_user_context_t ctx;
			int ns;
			unsigned long syscall_ret;
			unsigned long phys;
			struct syscall_request req2 IHK_DMA_ALIGN; /* debug */

			phys = ihk_mc_map_memory(NULL, res.fault_address,
			                        sizeof(struct syscall_request));
			requestp = ihk_mc_map_virtual(phys, 1,
			                       PTATTR_WRITABLE | PTATTR_ACTIVE);
			memcpy(&request, requestp, sizeof request);
			ihk_mc_unmap_virtual(requestp, 1);
			ihk_mc_unmap_memory(NULL, phys,
			                    sizeof(struct syscall_request));
			num = request.number;

			if (num == __NR_rt_sigaction) {
				int sig = syscall_nested_rt_sigaction_index_result(
						request.args[0], _NSIG);
				struct thread *thread = get_this_cpu_local_var()->current;

				if (sig < 0)
					syscall_ret = sig;
				else
					syscall_ret = (unsigned long)thread->
					              sigcommon->action[sig].
					              sa.sa_handler;
			}
			else {
				ns = (sizeof syscall_table  /
				      sizeof syscall_table[0]);
				if (syscall_nested_dispatch_valid_result(num,
						ns, num >= 0 && num < ns &&
						syscall_table[num])) {
					ihk_mc_syscall_set_arg0(&ctx, request.args[0]);
					ihk_mc_syscall_set_arg1(&ctx, request.args[1]);
					ihk_mc_syscall_set_arg2(&ctx, request.args[2]);
					ihk_mc_syscall_set_arg3(&ctx, request.args[3]);
					ihk_mc_syscall_set_arg4(&ctx, request.args[4]);
					ihk_mc_syscall_set_arg5(&ctx, request.args[5]);
					syscall_ret = syscall_table[num](num,
					                                 &ctx);
				}
				else
					syscall_ret = -ENOSYS;
			}

			/* send result */
			/* The current thread is the requester and only the waiting thread
			 * may serve the request */
			syscall_nested_response_prepare_result(&req2,
					&res,
					__NR_syscall_response, syscall_ret,
					get_this_cpu_local_var()->current->tid, res.stid,
					IHK_SCD_REQ_THREAD_SPINNING);
			send_syscall(&req2, cpu, &res);
		}
	}
#endif
	if (syscall_preempt_disable_needed_result(req->rtid)) {
		preempt_enable();
	}

	dkprintf("%s: syscall num: %d got host reply: %d \n",
		__FUNCTION__, req->number, res.ret);

	rc = res.ret;
	if (syscall_log_budget_result(pid, &mcexec_v10_offload_return_pid,
			&mcexec_v10_offload_return_logs, 64) > 0) {
		kprintf("mcexec_v10: offload_return cpu=%d pid=%d tid=%d nr=%d ret=0x%lx ret_signed=%ld\n",
			cpu, pid, thread ? thread->tid : -1,
			req->number, rc, rc);
	}

#ifdef ENABLE_TOFU
	if (syscall_tofu_post_reply_candidate_result(req->number, rc,
			__NR_ioctl, __NR_openat)) {
		int fd = req->number == __NR_ioctl ? req->args[0] : rc;
		char *path = req->number == __NR_ioctl ?
			thread->proc->fd_path[fd] : thread->fd_path_in_open;

		if (get_this_cpu_local_var()->current->proc->enable_tofu &&
				res.pde_data &&
				fd < MAX_FD_PDE &&
				!thread->proc->fd_pde_data[fd] &&
				!strncmp(path, "/proc/tofu/dev/", 15)) {
			unsigned long irqstate;

			irqstate = ihk_mc_spinlock_lock(&thread->proc->mckfd_lock);
			thread->proc->fd_pde_data[fd] = res.pde_data;
			ihk_mc_spinlock_unlock(&thread->proc->mckfd_lock, irqstate);

			dkprintf("%s: PID: %d, ioctl fd: %d, filename: "
					"%s, pde_data: 0x%lx\n",
					__FUNCTION__,
					thread->proc->pid,
					fd,
					path,
					res.pde_data);
		}
	}
#endif

	if (syscall_offload_counted_result(req->number, __NR_exit_group)) {
		--thread->in_syscall_offload;
	}

	/* -ERESTARTSYS indicates that the proxy process is gone
	 * and the application should be terminated */
	if (syscall_proxy_dead_result(rc)) {
		dkprintf("%s: proxy PID %d is dead, terminate()\n",
			__FUNCTION__, thread->proc->pid);
		thread->proc->nohost = 1;
	}

#ifdef PROFILE_ENABLE
	if (syscall_profile_event_needed_result(req->number,
			PROFILE_SYSCALL_MAX)) {
		profile_event_add(profile_syscall2offload(req->number),
				(rdtsc() - t_s));
	}
	else {
		dkprintf("%s: offload syscall > %d ?? : %d\n",
				__FUNCTION__, PROFILE_SYSCALL_MAX, req->number);
	}
#endif // PROFILE_ENABLE

	monitor->status = mstatus;
	monitor->counter++;
	return rc;
}

#ifndef MCKERNEL_RUST_SYSCALL_OFFLOAD
long syscall_generic_forwarding(int n, ihk_mc_user_context_t *ctx)
{
	struct syscall_request request IHK_DMA_ALIGN;

	dkprintf("syscall_generic_forwarding(%d)\n", n);
	return syscall_generic_forwarding_body_result(&request, n,
			ihk_mc_syscall_arg0(ctx), ihk_mc_syscall_arg1(ctx),
			ihk_mc_syscall_arg2(ctx), ihk_mc_syscall_arg3(ctx),
			ihk_mc_syscall_arg4(ctx), ihk_mc_syscall_arg5(ctx),
			ihk_mc_get_processor_id(), do_syscall);
}
#endif

static int wait_stopped(struct thread *thread, struct process *child, struct thread *c_thread, int *status, int options)
{
	dkprintf("wait_stopped,proc->pid=%d,child->pid=%d,options=%08x\n",
			 thread->proc->pid, child->pid, options);
	int ret = wait_stopped_body_result(c_thread, child, status, options,
			__builtin_offsetof(struct process, pid),
			__builtin_offsetof(struct process, status),
			__builtin_offsetof(struct process, group_exit_status),
			__builtin_offsetof(struct process, main_thread),
			__builtin_offsetof(struct thread, tid),
			__builtin_offsetof(struct thread, exit_status),
			process_wait_exit_status_reap_result);

	dkprintf("wait_stopped,child->pid=%d,status=%08x\n",
			 child->pid, status ? *status : -1);
	return ret;    
}

static int wait_continued(struct thread *thread, struct process *child,
			  struct thread *c_thread, int *status, int options)
{
	int ret = wait_continued_body_result(c_thread, child, status, options,
			__builtin_offsetof(struct process, pid),
			__builtin_offsetof(struct process, main_thread),
			__builtin_offsetof(struct thread, tid),
			__builtin_offsetof(struct thread, signal_flags),
			process_thread_signal_flags_reap_result);

	dkprintf("wait4,SIGNAL_STOP_CONTINUED,pid=%d,status=%08x\n",
			 child->pid, status ? *status : -1);
	return ret;
}

static void
thread_exit_waitq_wake_bridge(void *waitq)
{
	waitq_wakeup((waitq_t *)waitq);
}

static void
thread_exit_log_bridge(int sig, long error)
{
	dkprintf("terminate,klll %d,error=%ld\n", sig, error);
}

static void
finalize_process_writer_lock_bridge(void *lock, void *node)
{
	mcs_rwlock_writer_lock_noirq((struct mcs_rwlock_lock *)lock,
			(struct mcs_rwlock_node *)node);
}

static void
finalize_process_writer_unlock_bridge(void *lock, void *node)
{
	mcs_rwlock_writer_unlock_noirq((struct mcs_rwlock_lock *)lock,
			(struct mcs_rwlock_node *)node);
}

static void
finalize_process_release_bridge(void *proc)
{
	release_process((struct process *)proc);
}

static void
finalize_process_wakeup_log_bridge(void)
{
	dkprintf("terminate,wakeup\n");
}

static void
thread_exit_signal(struct thread *thread)
{
	thread_exit_signal_body_result(thread,
			__builtin_offsetof(struct thread, report_proc),
			__builtin_offsetof(struct thread, ptrace),
			__builtin_offsetof(struct thread, termsig),
			__builtin_offsetof(struct thread, exit_status),
			__builtin_offsetof(struct thread, tid),
			__builtin_offsetof(struct thread, user_tsc),
			__builtin_offsetof(struct thread, system_tsc),
			__builtin_offsetof(struct process, pid),
			__builtin_offsetof(struct process, waitpid_q),
			syscall_tsc_to_ts_bridge, syscall_timespec_to_jiffy_bridge,
			syscall_do_kill_thread_bridge, thread_exit_waitq_wake_bridge,
			thread_exit_log_bridge);
}

static void
finalize_process(struct process *proc)
{
	struct resource_set *resource_set = get_this_cpu_local_var()->resource_set;
	struct process *pid1 = resource_set->pid1;
	struct mcs_rwlock_node updatelock;

	finalize_process_body_result(proc, pid1, &updatelock,
			__builtin_offsetof(struct process, parent),
			__builtin_offsetof(struct process, status),
			__builtin_offsetof(struct process, update_lock),
			__builtin_offsetof(struct process, pid),
			__builtin_offsetof(struct process, group_exit_status),
			__builtin_offsetof(struct process, termsig),
			__builtin_offsetof(struct process, utime),
			__builtin_offsetof(struct process, stime),
			__builtin_offsetof(struct process, waitpid_q),
			finalize_process_writer_lock_bridge,
			finalize_process_writer_unlock_bridge,
			finalize_process_release_bridge,
			finalize_process_wakeup_log_bridge,
			syscall_timespec_to_jiffy_bridge,
			syscall_do_kill_thread_bridge,
			thread_exit_waitq_wake_bridge,
			thread_exit_log_bridge);
}

static void
ptrace_detach_reader_lock_bridge(void *lock, void *node)
{
	mcs_rwlock_reader_lock((struct mcs_rwlock_lock *)lock,
			(struct mcs_rwlock_node_irqsave *)node);
}

static void
ptrace_detach_reader_unlock_bridge(void *lock, void *node)
{
	mcs_rwlock_reader_unlock((struct mcs_rwlock_lock *)lock,
			(struct mcs_rwlock_node_irqsave *)node);
}

static void
ptrace_detach_list_detach_bridge(void *entry)
{
	process_list_detach_result((struct list_head *)entry);
}

static int
ptrace_detach_main_reparent_bridge(void *process,
		unsigned long parent_offset, void *parent, void *ptraced_entry,
		void *sibling_entry, void *children_head)
{
	return process_ptrace_main_detach_reparent_result(process,
			parent_offset, parent,
			(struct list_head *)ptraced_entry,
			(struct list_head *)sibling_entry,
			(struct list_head *)children_head);
}

static int
ptrace_detach_report_detach_bridge(void *thread,
		unsigned long report_proc_offset, void *report_proc,
		void *entry)
{
	return process_thread_report_detach_result(thread,
			report_proc_offset, report_proc,
			(struct list_head *)entry);
}

static void *
ptrace_detach_cleanup_bridge(void *thread, unsigned long ptrace_offset,
		unsigned long saved_valid_offset, unsigned long debugreg_offset)
{
	return process_thread_ptrace_cleanup_result(thread, ptrace_offset,
			saved_valid_offset, debugreg_offset);
}

static void
ptrace_detach_kfree_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}

static void
ptrace_detach_clear_single_step_bridge(void *thread)
{
	clear_single_step((struct thread *)thread);
}

static int
ptrace_detach_report_attach_bridge(void *thread,
		unsigned long termsig_offset, int update_termsig, int termsig,
		unsigned long report_proc_offset, void *report_proc,
		void *entry, void *head)
{
	return process_thread_report_attach_result(thread, termsig_offset,
			update_termsig, termsig, report_proc_offset,
			report_proc, (struct list_head *)entry,
			(struct list_head *)head);
}

static void
ptrace_detach_thread_exit_signal_bridge(void *thread)
{
	thread_exit_signal((struct thread *)thread);
}

static long
ptrace_detach_do_kill_bridge(void *current_thread, int pid, int tid,
		int sig, const void *info, int ptracecont)
{
	return do_kill((struct thread *)current_thread, pid, tid, sig,
			(struct siginfo *)info, ptracecont);
}

static void
ptrace_detach_wakeup_bridge(void *thread, int valid_states)
{
	sched_wakeup_thread((struct thread *)thread, valid_states);
}

static void
ptrace_detach_release_thread_bridge(void *thread)
{
	release_thread((struct thread *)thread);
}

static void
ptrace_detach_finalize_bridge(void *proc)
{
	finalize_process((struct process *)proc);
}

static const struct ptrace_detach_offsets ptrace_detach_kernel_offsets = {
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.thread_termsig_offset = __builtin_offsetof(struct thread, termsig),
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_tid_offset = __builtin_offsetof(struct thread, tid),
	.thread_report_proc_offset =
		__builtin_offsetof(struct thread, report_proc),
	.thread_report_siblings_list_offset =
		__builtin_offsetof(struct thread, report_siblings_list),
	.thread_ptrace_offset = __builtin_offsetof(struct thread, ptrace),
	.thread_ptrace_saved_uctx_valid_offset =
		__builtin_offsetof(struct thread, ptrace_saved_uctx_valid),
	.thread_ptrace_debugreg_offset =
		__builtin_offsetof(struct thread, ptrace_debugreg),
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.proc_status_offset = __builtin_offsetof(struct process, status),
	.proc_parent_offset = __builtin_offsetof(struct process, parent),
	.proc_ppid_parent_offset =
		__builtin_offsetof(struct process, ppid_parent),
	.proc_main_thread_offset =
		__builtin_offsetof(struct process, main_thread),
	.proc_children_lock_offset =
		__builtin_offsetof(struct process, children_lock),
	.proc_threads_lock_offset =
		__builtin_offsetof(struct process, threads_lock),
	.proc_children_list_offset =
		__builtin_offsetof(struct process, children_list),
	.proc_siblings_list_offset =
		__builtin_offsetof(struct process, siblings_list),
	.proc_ptraced_siblings_list_offset =
		__builtin_offsetof(struct process, ptraced_siblings_list),
	.proc_report_threads_list_offset =
		__builtin_offsetof(struct process, report_threads_list),
};

static void
ptrace_detach_thread(struct thread *thread, int data)
{
	struct resource_set *resource_set = get_this_cpu_local_var()->resource_set;
	struct process *pid1 = resource_set->pid1;
	struct thread *mythread = get_this_cpu_local_var()->current;
	struct process *proc = mythread->proc;
	struct mcs_rwlock_node_irqsave lock;

	ptrace_detach_thread_body_result(thread, data, mythread, proc, pid1,
			&ptrace_detach_kernel_offsets,
			ptrace_detach_reader_lock_bridge,
			ptrace_detach_reader_unlock_bridge,
			ptrace_detach_list_detach_bridge,
			ptrace_detach_main_reparent_bridge,
			ptrace_detach_report_detach_bridge,
			ptrace_detach_cleanup_bridge,
			ptrace_detach_kfree_bridge,
			ptrace_detach_clear_single_step_bridge,
			ptrace_detach_report_attach_bridge,
			ptrace_detach_thread_exit_signal_bridge,
			ptrace_detach_do_kill_bridge,
			ptrace_detach_wakeup_bridge,
			ptrace_detach_release_thread_bridge,
			ptrace_detach_finalize_bridge,
			&lock);
}

static int
wait_stopped_bridge(void *thread, void *child_proc, void *child_thread,
		int *status, int options)
{
	return wait_stopped((struct thread *)thread,
			(struct process *)child_proc,
			(struct thread *)child_thread, status, options);
}

static int
wait_continued_bridge(void *thread, void *child_proc, void *child_thread,
		int *status, int options)
{
	return wait_continued((struct thread *)thread,
			(struct process *)child_proc,
			(struct thread *)child_thread, status, options);
}

static void
wait_rwlock_writer_lock_bridge(void *lock, void *node)
{
	mcs_rwlock_writer_lock_noirq((struct mcs_rwlock_lock *)lock,
			(struct mcs_rwlock_node *)node);
}

static void
wait_rwlock_writer_unlock_bridge(void *lock, void *node)
{
	mcs_rwlock_writer_unlock_noirq((struct mcs_rwlock_lock *)lock,
			(struct mcs_rwlock_node *)node);
}

static void
wait_process_list_detach_bridge(void *entry)
{
	process_list_detach_result((struct list_head *)entry);
}

static void
wait_process_list_add_tail_bridge(void *entry, void *head)
{
	process_list_add_tail_result((struct list_head *)entry,
			(struct list_head *)head);
}

static int
wait_host_wait4_bridge(int pid, int options)
{
	struct syscall_request request IHK_DMA_ALIGN;

	request.number = __NR_wait4;
	request.args[0] = pid;
	request.args[1] = 0;
	request.args[2] = options;
	return do_syscall(&request, ihk_mc_get_processor_id());
}

static void
wait_process_release_bridge(void *proc)
{
	release_process((struct process *)proc);
}

static void
wait_zombie_log_bridge(int event, int pid, int status, int ret)
{
	switch (event) {
	case WAIT_ZOMBIE_LOG_FOUND:
		dkprintf("wait_zombie,found PS_ZOMBIE process: %d\n", pid);
		break;
	case WAIT_ZOMBIE_LOG_WARNING:
		kprintf("WARNING: host waitpid failed?\n");
		break;
	case WAIT_ZOMBIE_LOG_STATUS:
		dkprintf("wait_zombie,child->pid=%d,status=%08x\n",
			 pid, status);
		break;
	default:
		(void)ret;
		break;
	}
}

static const struct wait_zombie_offsets wait_zombie_kernel_offsets = {
	.thread_ptrace_offset = __builtin_offsetof(struct thread, ptrace),
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.proc_ppid_parent_offset = __builtin_offsetof(struct process,
						      ppid_parent),
	.proc_parent_offset = __builtin_offsetof(struct process, parent),
	.proc_status_offset = __builtin_offsetof(struct process, status),
	.proc_group_exit_status_offset =
		__builtin_offsetof(struct process, group_exit_status),
	.proc_nowait_offset = __builtin_offsetof(struct process, nowait),
	.proc_update_lock_offset = __builtin_offsetof(struct process,
						      update_lock),
	.proc_children_lock_offset = __builtin_offsetof(struct process,
							children_lock),
	.proc_threads_lock_offset = __builtin_offsetof(struct process,
						       threads_lock),
	.proc_siblings_list_offset = __builtin_offsetof(struct process,
							siblings_list),
	.proc_children_list_offset = __builtin_offsetof(struct process,
							children_list),
	.proc_main_thread_offset = __builtin_offsetof(struct process,
						      main_thread),
	.proc_stime_offset = __builtin_offsetof(struct process, stime),
	.proc_utime_offset = __builtin_offsetof(struct process, utime),
	.proc_stime_children_offset =
		__builtin_offsetof(struct process, stime_children),
	.proc_utime_children_offset =
		__builtin_offsetof(struct process, utime_children),
	.proc_maxrss_offset = __builtin_offsetof(struct process, maxrss),
	.proc_maxrss_children_offset =
		__builtin_offsetof(struct process, maxrss_children),
};

static const struct wait_scan_offsets wait_scan_kernel_offsets = {
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.thread_tid_offset = __builtin_offsetof(struct thread, tid),
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_ptrace_offset = __builtin_offsetof(struct thread, ptrace),
	.thread_signal_flags_offset =
		__builtin_offsetof(struct thread, signal_flags),
	.thread_termsig_offset = __builtin_offsetof(struct thread, termsig),
	.thread_report_siblings_list_offset =
		__builtin_offsetof(struct thread, report_siblings_list),
	.thread_siblings_list_offset =
		__builtin_offsetof(struct thread, siblings_list),
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.proc_pgid_offset = __builtin_offsetof(struct process, pgid),
	.proc_status_offset = __builtin_offsetof(struct process, status),
	.proc_children_lock_offset =
		__builtin_offsetof(struct process, children_lock),
	.proc_threads_lock_offset =
		__builtin_offsetof(struct process, threads_lock),
	.proc_children_list_offset =
		__builtin_offsetof(struct process, children_list),
	.proc_ptraced_children_list_offset =
		__builtin_offsetof(struct process, ptraced_children_list),
	.proc_siblings_list_offset =
		__builtin_offsetof(struct process, siblings_list),
	.proc_ptraced_siblings_list_offset =
		__builtin_offsetof(struct process, ptraced_siblings_list),
	.proc_report_threads_list_offset =
		__builtin_offsetof(struct process, report_threads_list),
	.proc_threads_list_offset =
		__builtin_offsetof(struct process, threads_list),
	.proc_main_thread_offset =
		__builtin_offsetof(struct process, main_thread),
};

static void
wait_thread_report_detach_bridge(void *thread)
{
	struct thread *child = thread;

	process_thread_report_detach_result(child,
			__builtin_offsetof(struct thread, report_proc),
			NULL, &child->report_siblings_list);
}

static void
wait_thread_ptrace_detach_bridge(void *thread)
{
	ptrace_detach_thread((struct thread *)thread, 0);
}

static void
wait_thread_release_bridge(void *thread)
{
	release_thread((struct thread *)thread);
}

static int
wait_proc(int pid, int *status, int options, void *rusage, int *empty)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process *proc = thread->proc;
	struct mcs_rwlock_node lock;
	struct mcs_rwlock_node child_lock;
	struct mcs_rwlock_node updatelock;
	struct mcs_rwlock_node child_update_lock;
	struct mcs_rwlock_node childlock;
	struct process *pid1 = get_this_cpu_local_var()->resource_set->pid1;

	return wait_process_scan_body_result(pid, status, options, rusage,
			empty, thread, proc, pid1, &wait_scan_kernel_offsets,
			&wait_zombie_kernel_offsets,
			wait_rwlock_writer_lock_bridge,
			wait_rwlock_writer_unlock_bridge,
			wait_host_wait4_bridge,
			wait_process_list_detach_bridge,
			wait_process_list_add_tail_bridge,
			wait_thread_ptrace_detach_bridge,
			wait_process_release_bridge,
			wait_zombie_log_bridge,
			wait_stopped_bridge,
			wait_continued_bridge,
			process_thread_signal_flags_reap_result,
			&lock, &child_lock, &updatelock, &child_update_lock,
			&childlock);
}

static int
wait_thread(int tid, int *status, int options, void *rusage, int *empty)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process *proc = thread->proc;
	struct mcs_rwlock_node lock;

	return wait_thread_scan_body_result(tid, status, options, rusage,
			empty, thread, proc, &wait_scan_kernel_offsets,
			wait_rwlock_writer_lock_bridge,
			wait_rwlock_writer_unlock_bridge,
			wait_stopped_bridge,
			wait_continued_bridge,
			process_thread_signal_flags_reap_result,
			wait_thread_report_detach_bridge,
			wait_thread_ptrace_detach_bridge,
			wait_thread_release_bridge,
			&lock);
}

/*
 * From glibc: INLINE_SYSCALL (wait4, 4, pid, stat_loc, options, NULL);
 */
static void do_wait_waitq_init_bridge(void *entry, void *thread)
{
	waitq_init_entry((struct waitq_entry *)entry, (struct thread *)thread);
}

static void do_wait_prepare_bridge(void *waitq, void *entry, int status)
{
	waitq_prepare_to_wait((waitq_t *)waitq, (struct waitq_entry *)entry,
			      status);
}

static void do_wait_finish_bridge(void *waitq, void *entry)
{
	waitq_finish_wait((waitq_t *)waitq, (struct waitq_entry *)entry);
}

static int do_wait_has_signal_bridge(void *thread)
{
	return hassigpending((struct thread *)thread) != NULL;
}

static void do_wait_schedule_bridge(void)
{
	schedule();
}

static void do_wait_log_bridge(int event, int current_pid, int wait_pid)
{
	switch (event) {
	case WAIT_LOG_ENTER:
		dkprintf("wait4(): current->proc->pid: %d, pid: %d\n",
			 current_pid, wait_pid);
		break;
	case WAIT_LOG_SLEEPING:
		dkprintf("wait4,sleeping\n");
		break;
	case WAIT_LOG_WOKEN:
		dkprintf("wait4(): woken up\n");
		break;
	case WAIT_LOG_FOUND:
		dkprintf("wait4,out_found\n");
		break;
	case WAIT_LOG_NOTFOUND:
		dkprintf("wait4,out_notfound\n");
		break;
	default:
		break;
	}
}

static int
do_wait(int pid, int *status, int options, void *rusage)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	struct waitq_entry waitpid_wqe;

	return do_wait_body_result(pid, status, options, rusage, thread,
			&waitpid_wqe, __builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, pid),
			__builtin_offsetof(struct process, waitpid_q),
			PS_INTERRUPTIBLE, wait_proc, wait_thread,
			do_wait_waitq_init_bridge, do_wait_prepare_bridge,
			do_wait_finish_bridge, do_wait_has_signal_bridge,
			do_wait_schedule_bridge, do_wait_log_bridge);
}

int wait4_do_wait_bridge(int pid, int *status, int options,
		struct rusage *usage)
{
	return do_wait(pid, status, options, usage);
}

static unsigned long
terminate_mcexec_cmpxchg_bridge(unsigned long *value,
		unsigned long old_value, unsigned long new_value)
{
	return atomic_cmpxchg_ulong(value, old_value, new_value);
}

static long
terminate_mcexec_do_syscall_bridge(struct syscall_request *request, int cpu)
{
	return do_syscall(request, cpu);
}

static void
terminate_host_refcount_set_bridge(void *refcount, int value)
{
	ihk_atomic_set((ihk_atomic_t *)refcount, value);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_wait4(int n, ihk_mc_user_context_t *ctx);
long sys_waitid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_wait4(int n, ihk_mc_user_context_t *ctx)
{
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	int *status = (int *)ihk_mc_syscall_arg1(ctx);
	int options = (int)ihk_mc_syscall_arg2(ctx);
	void *rusage = (void *)ihk_mc_syscall_arg3(ctx);

	return wait4_body_result(pid, (unsigned long)status, options,
			(unsigned long)rusage, wait4_do_wait_bridge,
			syscall_copy_to_user_bridge);
}

long sys_waitid(int n, ihk_mc_user_context_t *ctx)
{
	int idtype = (int)ihk_mc_syscall_arg0(ctx);
	int id = (int)ihk_mc_syscall_arg1(ctx);
	siginfo_t *infop = (siginfo_t *)ihk_mc_syscall_arg2(ctx);
	int options = (int)ihk_mc_syscall_arg3(ctx);

	return waitid_body_result(idtype, id, (unsigned long)infop, options,
			wait4_do_wait_bridge, syscall_copy_to_user_bridge);
}
#endif

void terminate_mcexec(int rc, int sig)
{
	struct thread *mythread = get_this_cpu_local_var()->current;
	struct process *proc = mythread->proc;
	struct syscall_request request IHK_DMA_ALIGN;

	terminate_mcexec_body_result(proc, &request, rc, sig,
			ihk_mc_get_processor_id(), __NR_exit_group,
			__builtin_offsetof(struct process, group_exit_status),
			__builtin_offsetof(struct process, nohost),
			terminate_mcexec_cmpxchg_bridge,
			terminate_mcexec_do_syscall_bridge);
}

static unsigned long
sync_child_perf_read_bridge(int counter_id)
{
	return ihk_mc_perfctr_read(counter_id);
}

static void
sync_child_count_set_bridge(void *count, long value)
{
	ihk_atomic64_set((ihk_atomic64_t *)count, value);
}

void sync_child_event(struct mc_perf_event *event)
{
	(void)sync_child_event_body_result(event,
			event ? event->attr.inherit : 0,
			event ? event->pid : 0,
			__builtin_offsetof(struct mc_perf_event, group_leader),
			__builtin_offsetof(struct mc_perf_event, pid),
			__builtin_offsetof(struct mc_perf_event, counter_id),
			__builtin_offsetof(struct mc_perf_event, count),
			__builtin_offsetof(struct mc_perf_event, child_count_total),
			__builtin_offsetof(struct mc_perf_event, sibling_list),
			__builtin_offsetof(struct mc_perf_event, group_entry),
			sync_child_perf_read_bridge,
			sync_child_count_set_bridge);
}

void terminate(int rc, int sig)
{
	struct resource_set *resource_set = get_this_cpu_local_var()->resource_set;
	struct thread *mythread = get_this_cpu_local_var()->current;
	struct thread *thread;
	struct process *proc = mythread->proc;
	struct process *child;
	struct process *next;
	struct process *pid1 = resource_set->pid1;
	struct process_vm *vm;
	struct mcs_rwlock_node_irqsave lock;
	struct mcs_rwlock_node updatelock;
	struct mcs_rwlock_node childlock;
	struct mcs_rwlock_node childlock1;
	int i;
	int n;
	int *ids = NULL;
	int exit_status;
	struct timespec ats;
	int found;

	// sync perf info
	if (proc->monitoring_event)
		sync_child_event(proc->monitoring_event);

	// clean up threads
	mcs_rwlock_writer_lock_noirq(&proc->update_lock, &updatelock);
	mcs_rwlock_writer_lock(&proc->threads_lock, &lock); // conflict clone
	if (terminate_process_exited_result(proc->status)) {
		dkprintf("%s: PID: %d, TID: %d PS_EXITED already\n",
				__FUNCTION__, proc->pid, mythread->tid);
		preempt_disable();
		tsc_to_ts(mythread->user_tsc, &ats);
		ts_add(&proc->utime, &ats);
		tsc_to_ts(mythread->system_tsc, &ats);
		ts_add(&proc->stime, &ats);
		mythread->user_tsc = 0;
		mythread->system_tsc = 0;
		mythread->status = PS_EXITED;
		mythread->exit_status = proc->group_exit_status;
		thread_exit_signal(mythread);
		mcs_rwlock_writer_unlock(&proc->threads_lock, &lock);
		mcs_rwlock_writer_unlock_noirq(&proc->update_lock, &updatelock);
		release_thread(mythread);
		preempt_enable();
		schedule();
		// no return
		return;
	}

	dkprintf("%s: PID: %d, TID: %d setting PS_EXITED\n",
			__FUNCTION__, proc->pid, mythread->tid);
	tsc_to_ts(mythread->user_tsc, &ats);
	ts_add(&proc->utime, &ats);
	tsc_to_ts(mythread->system_tsc, &ats);
	ts_add(&proc->stime, &ats);
	mythread->user_tsc = 0;
	mythread->system_tsc = 0;
	exit_status = terminate_status_result(rc, sig);
	proc->group_exit_status = exit_status;
	mythread->exit_status = exit_status;
	proc->status = PS_EXITED;
	mcs_rwlock_writer_unlock(&proc->threads_lock, &lock);
	mcs_rwlock_writer_unlock_noirq(&proc->update_lock, &updatelock);

#ifdef ENABLE_TOFU
	/* Tofu: cleanup, must be done before mcexec is gone */
	if (proc->enable_tofu) {
		int fd;

		for (fd = 0; fd < MAX_FD_PDE; ++fd) {
			/* Tofu? */
			if (proc->enable_tofu && proc->fd_pde_data[fd]) {
				extern void tof_utofu_release_fd(struct process *proc, int fd);

				dkprintf("%s: -> tof_utofu_release_fd() @ fd: %d (%s)\n",
						__func__, fd, proc->fd_path[fd]);
				tof_utofu_release_fd(proc, fd);
				proc->fd_pde_data[fd] = NULL;
			}

			if (proc->fd_path[fd]) {
				kfree_tracked(proc->fd_path[fd], __FILE__, __LINE__);
				proc->fd_path[fd] = NULL;
			}
		}
	}
#endif

	terminate_mcexec(rc, sig);

	mcs_rwlock_writer_lock(&proc->threads_lock, &lock);
	process_list_detach_result(&mythread->siblings_list);
	mcs_rwlock_writer_unlock(&proc->threads_lock, &lock);

	mcs_rwlock_reader_lock(&proc->threads_lock, &lock);
	n = 0;
	for (thread = ((typeof(*thread) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread), siblings_list))); &thread->siblings_list != (&proc->threads_list); thread = ((typeof(*thread) *)((char *)(thread->siblings_list.next) - offsetof(typeof(*thread), siblings_list)))) {
		if (terminate_thread_is_other_result(thread, mythread)) {
			n++;
		}
	}

	if (n) {
		ids = kmalloc_tracked(sizeof(int) * n, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		i = 0;
		if (ids) {
			for (thread = ((typeof(*thread) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread), siblings_list))); &thread->siblings_list != (&proc->threads_list); thread = ((typeof(*thread) *)((char *)(thread->siblings_list.next) - offsetof(typeof(*thread), siblings_list)))) {
				if (terminate_thread_is_other_result(thread, mythread)) {
					ids[i] = thread->tid;
					i++;
				}
			}
		}
	}
	mcs_rwlock_reader_unlock(&proc->threads_lock, &lock);

	if (ids) {
		for (i = 0; i < n; i++) {
			do_kill(mythread, proc->pid, ids[i], SIGKILL, NULL, 0);
		}
		kfree_tracked(ids, __FILE__, __LINE__);
		ids = NULL;
	}

	for (;;) {
		__mcs_rwlock_reader_lock(&proc->threads_lock, &lock);
		found = 0;
		for (thread = ((typeof(*thread) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread), siblings_list))); &thread->siblings_list != (&proc->threads_list); thread = ((typeof(*thread) *)((char *)(thread->siblings_list.next) - offsetof(typeof(*thread), siblings_list)))) {
			if (terminate_thread_active_result(thread->status)) {
				found = 1;
				break;
			}
		}
		mcs_rwlock_reader_unlock(&proc->threads_lock, &lock);
		if (!found) {
			break;
		}

		/* We might be waiting for another thread on same CPU */
		schedule();
	}

	mcs_rwlock_writer_lock(&proc->threads_lock, &lock);
	process_list_add_tail_result(&mythread->siblings_list,
				     &proc->threads_list);
	mcs_rwlock_writer_unlock(&proc->threads_lock, &lock);

	vm = proc->vm;

#ifdef ENABLE_TOFU
	if (proc->enable_tofu) {
		extern void tof_utofu_finalize();

		tof_utofu_finalize();
	}
#endif

	free_all_process_memory_range(vm);

	if (proc->saved_cmdline) {
		kfree_tracked(proc->saved_cmdline, __FILE__, __LINE__);
	}

	while (!list_empty(&proc->report_threads_list)) {
		struct thread *thr;

		thr = ((struct thread *)((char *)((&proc->report_threads_list)->next) - offsetof(struct thread, report_siblings_list)));
		if (terminate_report_thread_ptrace_result(thr->ptrace)) {
			int release_flag =
				terminate_report_thread_release_needed_result(
						thr->proc == proc, thr->termsig);

			if (release_flag) {
				process_thread_termsig_clear_result(thr,
					__builtin_offsetof(struct thread,
							   termsig),
					release_flag);
			}
			ptrace_detach_thread(thr, 0);
			if (release_flag) {
				release_thread(thr);
			}
		}
		else {
			mcs_rwlock_writer_lock(&proc->threads_lock, &lock);
			process_thread_report_detach_result(thr,
				__builtin_offsetof(struct thread, report_proc),
				NULL, &thr->report_siblings_list);
			mcs_rwlock_writer_unlock(&proc->threads_lock, &lock);
			release_thread(thr);
		}
	}

	if (terminate_child_cleanup_needed_result(
			list_empty(&proc->children_list),
			list_empty(&proc->ptraced_children_list))) {
		// clean up children
		for (i = 0; i < HASH_SIZE; i++) {
			mcs_rwlock_writer_lock(&resource_set->process_hash->lock[i],
					&lock);
			for (child = ((typeof(*child) *)((char *)((&resource_set->process_hash->list[i])->next) - offsetof(typeof(*child), hash_list))), next = ((typeof(*child) *)((char *)(child->hash_list.next) - offsetof(typeof(*child), hash_list))); &child->hash_list != (&resource_set->process_hash->list[i]); child = next, next = ((typeof(*next) *)((char *)(next->hash_list.next) - offsetof(typeof(*next), hash_list)))) {
				int free_child = 0;
				mcs_rwlock_writer_lock_noirq(&child->update_lock,
						&updatelock);

				switch (terminate_child_action_result(
						child->ppid_parent == proc,
						child->parent == proc,
						child->status)) {
				case TERMINATE_CHILD_ACTION_FREE_ZOMBIE:
					process_list_del_init_result(
						&child->hash_list);
					process_list_del_init_result(
						&child->siblings_list);
					free_child = 1;
					break;
				case TERMINATE_CHILD_ACTION_REPARENT_CHILD:
					mcs_rwlock_writer_lock_noirq(&proc->children_lock,
							&childlock);
					mcs_rwlock_writer_lock_noirq(&pid1->children_lock,
							&childlock1);
					process_child_reparent_result(child,
						__builtin_offsetof(
							struct process,
							ppid_parent),
						__builtin_offsetof(
							struct process,
							parent),
						pid1, &child->siblings_list,
						&pid1->children_list, 1);
					mcs_rwlock_writer_unlock_noirq(&pid1->children_lock,
							&childlock1);
					mcs_rwlock_writer_unlock_noirq(&proc->children_lock,
							&childlock);
					break;
				case TERMINATE_CHILD_ACTION_REPARENT_PTRACED:
					mcs_rwlock_writer_lock_noirq(&proc->children_lock,
							&childlock);
					mcs_rwlock_writer_lock_noirq(&pid1->children_lock,
							&childlock1);
					process_child_reparent_result(child,
						__builtin_offsetof(
							struct process,
							ppid_parent),
						__builtin_offsetof(
							struct process,
							parent),
						pid1,
						&child->ptraced_siblings_list,
						&pid1->ptraced_children_list, 0);
					mcs_rwlock_writer_unlock_noirq(&pid1->children_lock,
							&childlock1);
					mcs_rwlock_writer_unlock_noirq(&proc->children_lock,
							&childlock);
					break;
				}

				mcs_rwlock_writer_unlock_noirq(&child->update_lock,
						&updatelock);

				if (terminate_release_child_needed_result(free_child))
					release_process(child);
			}
			mcs_rwlock_writer_unlock(&resource_set->process_hash->lock[i],
					&lock);
		}
	}

	dkprintf("terminate,pid=%d\n", proc->pid);

#ifdef DCFA_KMOD
	do_mod_exit(rc);
#endif

	// clean up memory
	finalize_process(proc);

	preempt_disable();
	mcs_rwlock_writer_lock(&proc->threads_lock, &lock);
	mythread->status = PS_EXITED;
	mcs_rwlock_writer_unlock(&proc->threads_lock, &lock);
	release_thread(mythread);
	release_process_vm(vm);
	preempt_enable();
	schedule();
	kprintf("%s: ERROR: returned from terminate() -> schedule()\n", __FUNCTION__);
	panic("panic");
}

int __process_cleanup_fd(struct process *proc, int fd)
{
#ifdef ENABLE_TOFU
	/* Tofu? */
	if (process_cleanup_tofu_needed_result(proc->enable_tofu)) {
		extern void tof_utofu_release_fd(struct process *proc, int fd);

		dkprintf("%s: -> tof_utofu_release_fd() @ fd: %d (%s)\n",
				__func__, fd, proc->fd_path[fd]);
		tof_utofu_release_fd(proc, fd);
		proc->fd_pde_data[fd] = NULL;

		if (process_cleanup_fd_path_free_needed_result(proc->fd_path[fd])) {
			kfree_tracked(proc->fd_path[fd], __FILE__, __LINE__);
			proc->fd_path[fd] = NULL;
		}
	}
#endif
	return 0;
}

static long
process_cleanup_fd_bridge(void *proc, int fd)
{
	return __process_cleanup_fd((struct process *)proc, fd);
}

static void
process_cleanup_missing_log_bridge(int pid)
{
	dkprintf("%s: PID %d couldn't be found\n", "process_cleanup_fd", pid);
}

int process_cleanup_fd(int pid, int fd)
{
	struct mcs_rwlock_node_irqsave lock;

	return process_cleanup_fd_body_result(pid, fd, &lock,
			syscall_find_process_bridge, syscall_process_unlock_bridge,
			process_cleanup_fd_bridge,
			process_cleanup_missing_log_bridge);
}

int process_cleanup_before_terminate(int pid)
{
	struct mcs_rwlock_node_irqsave lock;

#ifdef ENABLE_TOFU
	return process_cleanup_before_terminate_body_result(pid, &lock, 1, 2,
			MAX_FD_PDE, syscall_find_process_bridge,
			syscall_process_unlock_bridge, process_cleanup_fd_bridge);
#else
	return process_cleanup_before_terminate_body_result(pid, &lock, 0, 2,
			2, syscall_find_process_bridge,
			syscall_process_unlock_bridge, process_cleanup_fd_bridge);
#endif
}


void
terminate_host(int pid, struct thread *thread)
{
	struct mcs_rwlock_node_irqsave lock;

	terminate_host_body_result(pid, thread, get_this_cpu_local_var()->current, &lock,
			__builtin_offsetof(struct process, nohost),
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct thread, refcount),
			syscall_find_process_bridge, syscall_process_unlock_bridge,
			terminate_host_refcount_set_bridge,
			wait_thread_release_bridge, wait_process_release_bridge,
			syscall_do_kill_thread_bridge);
}

static int syscall_ikc_send_bridge(void *channel, void *packet, int opt)
{
	return ihk_ikc_send((struct ihk_ikc_channel_desc *)channel, packet, opt);
}

void eventfd(int type)
{
	struct ihk_ikc_channel_desc *syscall_channel;

	syscall_channel = get_cpu_local_var(0)->ikc2linux;
	(void)syscall_eventfd_send_result(syscall_channel, SCD_MSG_EVENTFD,
			type, syscall_ikc_send_bridge);
}

void
interrupt_syscall(struct thread *thread, int sig)
{
	ihk_mc_user_context_t ctx;
	long lerror;

	dkprintf("interrupt_syscall pid=%d tid=%d sig=%d\n", thread->proc->pid,
	         thread->tid, sig);
	ihk_mc_syscall_set_arg0(&ctx, thread->proc->pid);
	ihk_mc_syscall_set_arg1(&ctx, thread->tid);
	ihk_mc_syscall_set_arg2(&ctx, sig);

	lerror = syscall_generic_forwarding(__NR_kill, &ctx);
	if (lerror) {
		kprintf("interrupt_syscall failed. %ld\n", lerror);
	}
	return;
}

void
exit_group_log_bridge(int pid)
{
	dkprintf("sys_exit_group,pid=%d\n", pid);
}

void
exit_group_terminate_bridge(int status, int group)
{
	terminate(status, group);
}

int
exit_group_current_pid_bridge(void)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	return thread->proc->pid;
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_exit_group(int n, ihk_mc_user_context_t *ctx);
#else
long sys_exit_group(int n, ihk_mc_user_context_t *ctx)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	int status = (int)ihk_mc_syscall_arg0(ctx);

	return exit_group_body_result(status, thread->proc->pid,
			exit_group_log_bridge, exit_group_terminate_bridge);
}
#endif

static void
clear_host_pte_log_bridge(long error)
{
	kprintf("clear_host_pte failed. %ld\n", error);
}

void clear_host_pte(uintptr_t addr, size_t len, int holding_memory_range_lock)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	(void)clear_host_pte_body_result(thread->vm, addr, len,
			holding_memory_range_lock,
			offsetof(struct process_vm, is_memory_range_lock_taken),
			ihk_mc_get_processor_id(), __NR_munmap,
			syscall_do_syscall3_bridge, clear_host_pte_log_bridge);
	return;
}

static int set_host_vma(uintptr_t addr, size_t len, int prot, int holding_memory_range_lock)
{
	ihk_mc_user_context_t ctx;
	long lerror;
	struct thread *thread = get_this_cpu_local_var()->current;

	ihk_mc_syscall_set_arg0(&ctx, addr);
	ihk_mc_syscall_set_arg1(&ctx, len);
	ihk_mc_syscall_set_arg2(&ctx, prot);

	/*
	 * XXX: Certain fabric drivers (e.g., the Tofu driver) use read-only
	 * mappings for the completion queue on which the kernel driver calls
	 * get_user_pages() with FOLL_FORCE and FOLL_WRITE flags requested.
	 * get_user_pages() on read-only mappings with FOLL_WRITE, however, only
	 * works if the underlying mapping is copy-on-write (i.e., private
	 * ANONYMOUS or private file mapping).  Because mcexec's address space
	 * reservation uses a shared pseudo-file mapping to cover McKernel
	 * ANONYMOUS areas, we would need to mark it private so that the condition
	 * holds. However, that would cause Linux to COW its pages and map to
	 * different physical memory thus make it inconsistent with the original
	 * McKernel mapping.
	 *
 * For the above reason, we do NOT set the host VMA read-only.
	 */
	return set_host_vma_body_result(addr, len, prot,
			holding_memory_range_lock);

	dkprintf("%s: offloading __NR_mprotect\n", __FUNCTION__);
	/* #986: Let remote page fault code skip
	   read-locking memory_range_lock. It's safe because other writers are warded off
	   until the remote PF handling code calls up_write(&current->mm->mmap_sem) and
	   vm_range is consistent when calling this function. */
	if (holding_memory_range_lock) {
		thread->vm->is_memory_range_lock_taken = ihk_mc_get_processor_id();
	}
	lerror = syscall_generic_forwarding(__NR_mprotect, &ctx);
	if (lerror) {
		kprintf("set_host_vma(%lx,%lx,%x) failed. %ld\n",
				addr, len, prot, lerror);
		goto out;
	}

	lerror = 0;
out:
	if (holding_memory_range_lock) {
		thread->vm->is_memory_range_lock_taken = -1;
	}
	return (int)lerror;
}

static void
do_munmap_begin_bridge(void)
{
	begin_free_pages_pending();
}

static int
do_munmap_remove_range_bridge(void *vm, unsigned long start,
		unsigned long end, int *ro_freedp)
{
	return remove_process_memory_range(vm, start, end, ro_freedp);
}

static void
do_munmap_clear_host_bridge(unsigned long addr, size_t len, int holding_lock)
{
	clear_host_pte(addr, len, holding_lock);
}

static int
do_munmap_set_host_bridge(unsigned long addr, size_t len, int prot,
		int holding_lock)
{
	return set_host_vma(addr, len, prot, holding_lock);
}

static void
do_munmap_finish_bridge(void)
{
	finish_free_pages_pending();
}

static void
do_munmap_log_bridge(unsigned long addr, size_t len, int error)
{
	dkprintf("%s: 0x%lx:%lu, error: %ld\n",
		"do_munmap", addr, len, error);
}

int do_munmap(void *addr, size_t len, int holding_memory_range_lock)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	return do_munmap_body_result(thread->vm, thread->proc,
			(uintptr_t)addr, len, holding_memory_range_lock,
			offsetof(struct process, straight_va),
			offsetof(struct process, straight_len),
			do_munmap_begin_bridge, do_munmap_remove_range_bridge,
			do_munmap_clear_host_bridge, do_munmap_set_host_bridge,
			do_munmap_finish_bridge, do_munmap_log_bridge);
}

static void
search_free_space_log_bridge(int event, size_t len, int pgshift,
		unsigned long addr, int error)
{
	if (event == SEARCH_FREE_SPACE_LOG_ENTER) {
		dkprintf("%s: len: %lu, pgshift: %d\n",
				"search_free_space", len, pgshift);
	}
	else if (event == SEARCH_FREE_SPACE_LOG_OUTSIDE) {
		ekprintf("%s: error: addr 0x%lx is outside the user region\n",
				"search_free_space", addr);
	}
	else if (event == SEARCH_FREE_SPACE_LOG_EXIT) {
		dkprintf("%s: len: %lu, pgshift: %d, addr: 0x%lx\n",
				"search_free_space", len, pgshift, addr);
		(void)error;
	}
}

static struct vm_range *
search_free_space_lookup_bridge(struct process_vm *vm, unsigned long start,
		unsigned long end)
{
	return lookup_process_memory_range(vm, start, end);
}

static int search_free_space(size_t len, int pgshift, uintptr_t *addrp)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	struct vm_regions *region = &thread->vm->region;
	unsigned long addr = addrp ? *addrp : 0;
	int error;

	error = search_free_space_body_result(thread->vm, region, len,
			pgshift, &addr, offsetof(struct vm_regions, user_end),
			offsetof(struct vm_regions, map_end),
			offsetof(struct vm_range, end),
			search_free_space_lookup_bridge,
			search_free_space_log_bridge);
	if (addrp)
		*addrp = addr;
	return error;
}

static int
do_mmap_smaller_page_bridge(size_t size, int *p2alignp)
{
	return arch_get_smaller_page_size(NULL, size, NULL, p2alignp);
}

intptr_t
do_mmap(const uintptr_t addr0, const size_t len0, const int prot,
	const int flags, const int fd, const off_t off0,
	const int vrf0, void *private_data)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	struct vm_regions *region = &thread->vm->region;
	uintptr_t addr = addr0;
	size_t len = len0;
	size_t populate_len = 0;
	off_t off;
	int error = 0;
	intptr_t npages = 0;
	int p2align;
	void *p = NULL;
	int vrflags = VR_NONE;
	uintptr_t phys;
	intptr_t straight_phys;
	struct memobj *memobj = NULL;
	int maxprot;
	int denied;
	int ro_vma_mapped = 0;
	struct shmid_ds ads;
	int populated_mapping = 0;
	struct process *proc = thread->proc;
#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct mckfd *fdp = NULL;
#endif
	int pgshift;
	struct vm_range *range = NULL;
	
	dkprintf("do_mmap(%lx,%lx,%x,%x,%d,%lx)\n",
			addr0, len0, prot, flags, fd, off0);

	if (!(flags & MAP_ANONYMOUS)) {
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
		static const struct syscall_mckfd_offsets mmap_mckfd_offsets = {
			.thread_proc_offset =
				__builtin_offsetof(struct thread, proc),
			.proc_mckfd_lock_offset =
				__builtin_offsetof(struct process, mckfd_lock),
			.proc_mckfd_offset =
				__builtin_offsetof(struct process, mckfd),
			.mckfd_next_offset =
				__builtin_offsetof(struct mckfd, next),
			.mckfd_fd_offset =
				__builtin_offsetof(struct mckfd, fd),
			.mckfd_read_cb_offset =
				__builtin_offsetof(struct mckfd, read_cb),
			.mckfd_ioctl_cb_offset =
				__builtin_offsetof(struct mckfd, ioctl_cb),
			.mckfd_close_cb_offset =
				__builtin_offsetof(struct mckfd, close_cb),
			.mckfd_fcntl_cb_offset =
				__builtin_offsetof(struct mckfd, fcntl_cb),
		};
		ihk_mc_user_context_t ctx;
		int handled = 0;
		long result;

		memset(&ctx, '\0', sizeof ctx);
		ihk_mc_syscall_set_arg0(&ctx, addr0);
		ihk_mc_syscall_set_arg1(&ctx, len0);
		ihk_mc_syscall_set_arg2(&ctx, prot);
		ihk_mc_syscall_set_arg3(&ctx, flags);
		ihk_mc_syscall_set_arg4(&ctx, fd);
		ihk_mc_syscall_set_arg5(&ctx, off0);

		result = do_mmap_mckfd_dispatch_body_result(thread, flags, fd,
				&ctx, &handled, &mmap_mckfd_offsets,
				__builtin_offsetof(struct mckfd, mmap_cb),
				syscall_mckfd_lock_bridge,
				syscall_mckfd_unlock_bridge);
		if (handled) {
			return result;
		}
#else
		ihk_mc_spinlock_lock_noirq(&proc->mckfd_lock);
		for(fdp = proc->mckfd; fdp; fdp = fdp->next)
			if(fdp->fd == fd)
				break;
		ihk_mc_spinlock_unlock_noirq(&proc->mckfd_lock);

		if(fdp){
			ihk_mc_user_context_t ctx;

			memset(&ctx, '\0', sizeof ctx);
			ihk_mc_syscall_set_arg0(&ctx, addr0);
			ihk_mc_syscall_set_arg1(&ctx, len0);
			ihk_mc_syscall_set_arg2(&ctx, prot);
			ihk_mc_syscall_set_arg3(&ctx, flags);
			ihk_mc_syscall_set_arg4(&ctx, fd);
			ihk_mc_syscall_set_arg5(&ctx, off0);

			if(fdp->mmap_cb){
				return fdp->mmap_cb(fdp, &ctx);
			}
			return -EBADF;
		}
#endif
	}

	flush_nfo_tlb();

	/* Initialize straight large memory mapping */
	if (proc->straight_map && !proc->straight_va) {
		unsigned long straight_pa_start = 0xFFFFFFFFFFFFFFFF;
		unsigned long straight_pa_end = 0;
		int i;
		int p2align = PAGE_P2ALIGN;
		size_t psize = PAGE_SIZE;
		unsigned long vrflags;
		enum ihk_mc_pt_attribute ptattr;
		struct vm_range *range;

		vrflags = PROT_TO_VR_FLAG(PROT_READ | PROT_WRITE);
		vrflags |= VRFLAG_PROT_TO_MAXPROT(vrflags);
		vrflags |= VR_DEMAND_PAGING;

		for (i = 0; i < ihk_mc_get_nr_memory_chunks(); ++i) {
			unsigned long start, end;

			ihk_mc_get_memory_chunk(i, &start, &end, NULL);

			if (straight_pa_start > start) {
				straight_pa_start = start;
			}

			if (straight_pa_end < end) {
				straight_pa_end = end;
			}
		}

		kprintf("%s: straight_pa_start: 0x%lx, straight_pa_end: 0x%lx\n",
				__FUNCTION__, straight_pa_start, straight_pa_end);

		error = arch_get_smaller_page_size(NULL,
				straight_pa_end - straight_pa_start,
				&psize, &p2align);

		if (error) {
			kprintf("%s: arch_get_smaller_page_size failed: %d\n",
					__FUNCTION__, error);
			goto straight_out;
		}
		//psize = PTL2_SIZE;
		//p2align = PTL2_SHIFT - PTL1_SHIFT;

		// Force 512G page
		//psize = (1UL << 39);
		//p2align = 39 - PAGE_SHIFT;

		// Force 512MB page
		psize = (1UL << 29);
		p2align = 29 - PAGE_SHIFT;

		kprintf("%s: using page shift: %d, psize: %lu\n",
				__FUNCTION__, p2align + PAGE_SHIFT, psize);

		straight_pa_start &= ~(psize - 1);
		straight_pa_end = (straight_pa_end + psize - 1) & ~(psize - 1);

		kprintf("%s: aligned straight_pa_start: 0x%lx, straight_pa_end: 0x%lx\n",
				__FUNCTION__, straight_pa_start, straight_pa_end);

		proc->straight_len = straight_pa_end - straight_pa_start;
		error = search_free_space(proc->straight_len,
				PAGE_SHIFT + p2align, (uintptr_t *)&proc->straight_va);

		if (error) {
			kprintf("%s: search_free_space() failed: %d\n",
					__FUNCTION__, error);
			proc->straight_va = 0;
			goto straight_out;
		}

		dkprintf("%s: straight_va: 0x%lx to be used\n",
				__FUNCTION__, proc->straight_va);

		if (add_process_memory_range(proc->vm, (unsigned long)proc->straight_va,
					(unsigned long)proc->straight_va + proc->straight_len,
					NOPHYS, vrflags, NULL, 0,
					PAGE_SHIFT + p2align, private_data, &range) != 0) {
			kprintf("%s: error: adding straight memory range \n",
					__FUNCTION__);
			proc->straight_va = 0;
			goto straight_out;
		}

		kprintf("%s: straight_va: 0x%lx, range->pgshift: %d, range OK\n",
				__FUNCTION__, proc->straight_va, range->pgshift);

		ptattr = arch_vrflag_to_ptattr(range->flag, PF_POPULATE, NULL);

#ifdef ENABLE_FUGAKU_HACKS
		if (1) { // Un-safe mapping of covering physical range
#endif
		error = ihk_mc_pt_set_range(proc->vm->address_space->page_table,
				proc->vm,
				(void *)range->start,
				(void *)range->end,
				straight_pa_start, ptattr,
				range->pgshift,
				range, 0);

		if (error) {
			kprintf("%s: ihk_mc_pt_set_range() failed: %d\n",
					__FUNCTION__, error);
			proc->straight_va = 0;
			goto straight_out;
		}
		//ihk_mc_pt_print_pte(proc->vm->address_space->page_table, range->start);

		region->map_end = (unsigned long)proc->straight_va + proc->straight_len;
		proc->straight_pa = straight_pa_start;
		kprintf("%s: straight mapping: 0x%lx:%lu @ 0x%lx, "
				"psize: %lu, straight_map_threshold: %lu\n",
				__FUNCTION__,
				proc->straight_va,
				proc->straight_len,
				proc->straight_pa,
				psize,
				proc->straight_map_threshold);

#ifdef ENABLE_FUGAKU_HACKS
		}
		else { // Safe mapping of only LWK memory ranges
			size_t max_pgsize = 0;
			size_t min_pgsize = 0xFFFFFFFFFFFFFFFF;

			/*
			 * Iterate LWK phsyical memory chunks and map them to their
			 * corresponding offset in the straight range using the largest
			 * suitable pages.
			 */
			for (i = 0; i < ihk_mc_get_nr_memory_chunks(); ++i) {
				unsigned long start, end, pa;
				void *va, *va_end;
				size_t pgsize;
				int pg2align;

				ihk_mc_get_memory_chunk(i, &start, &end, NULL);
				va = proc->straight_va + (start - straight_pa_start);
				va_end = va + (end - start);
				pa = start;

				while (va < va_end) {
					pgsize = (va_end - va) + 1;
retry:
					error = arch_get_smaller_page_size(NULL, pgsize,
							&pgsize, &pg2align);
					if (error) {
						ekprintf("%s: arch_get_smaller_page_size() failed"
								" during straight mapping: %d\n",
								__func__, error);
						proc->straight_va = 0;
						goto straight_out;
					}

					/* Are virtual or physical not page aligned for this size? */
					if (((unsigned long)va & (pgsize - 1)) ||
							(pa & (pgsize - 1))) {
						goto retry;
					}

					error = ihk_mc_pt_set_range(
							proc->vm->address_space->page_table,
							proc->vm,
							va,
							va + pgsize,
							pa,
							ptattr,
							pg2align + PAGE_SHIFT,
							range,
							0);

					if (error) {
						kprintf("%s: ihk_mc_pt_set_range() failed"
								" during straight mapping: %d\n",
								__func__, error);
						proc->straight_va = 0;
						goto straight_out;
					}

					if (pgsize > max_pgsize)
						max_pgsize = pgsize;

					if (pgsize < min_pgsize)
						min_pgsize = pgsize;

					va += pgsize;
					pa += pgsize;
				}
			}

			region->map_end = (unsigned long)proc->straight_va +
				proc->straight_len;
			proc->straight_pa = straight_pa_start;
			kprintf("%s: straight mapping: 0x%lx:%lu @ "
					"min_pgsize: %lu, max_pgsize: %lu\n",
					__FUNCTION__,
					proc->straight_va,
					proc->straight_len,
					min_pgsize,
					max_pgsize);
		}
#endif
	}
straight_out:

	error = do_mmap_page_size_body_result(flags, vrf0, proc->thp_disable,
			len, &pgshift, &p2align,
			ihk_mc_get_linux_default_huge_page_shift,
			do_mmap_smaller_page_bridge);
	if (error) {
		ekprintf("do_mmap:arch_get_smaller_page_size failed. %d\n",
				error);
		goto out;
	}

	ihk_rwspinlock_write_lock_noirq(&thread->vm->memory_range_lock);

	if ((flags & MAP_FIXED) && proc->straight_va &&
			((void *)addr >= proc->straight_va) &&
			((void *)addr + len) <= (proc->straight_va + proc->straight_len)) {
		kprintf("%s: can't map MAP_FIXED into straight mapping\n",
				__FUNCTION__);
		error = -EINVAL;
		goto out;
	}

	if (flags & MAP_FIXED) {
		/* clear specified address range */
		error = do_munmap((void *)addr, len, 1/* holding memory_range_lock */);
		if (error) {
			ekprintf("do_mmap:do_munmap(%lx,%lx) failed. %d\n",
					addr, len, error);
			goto out;
		}
	}
	else if (flags & MAP_ANONYMOUS) {
		/* Obtain mapping address */
		error = search_free_space(len,
					  PAGE_SHIFT + p2align, &addr);
		if (error) {
			kprintf("%s: error: search_free_space(%lx,%lx,%lx) failed. %d\n",
				__func__, len, PAGE_SHIFT + p2align, addr, error);
			goto out;
		}
	}

	/* do the map */
	vrflags = mmap_base_vrflags(prot, flags, vrf0, anon_on_demand);

	if (mmap_populated_mapping_result(flags)) {
		dkprintf("%s: 0x%lx:%lu %s%s|\n",
			__func__, addr, len,
				flags & MAP_POPULATE ? "|MAP_POPULATE" : "",
				flags & MAP_LOCKED ? "|MAP_LOCKED" : "");
		populated_mapping = 1;
	}

#if 0
	/* XXX: Intel MPI 128MB mapping.. */
	if (len == 134217728) {
		dkprintf("%s: %ld bytes mapping -> no prefault\n",
			__FUNCTION__, len);
		vrflags |= VR_DEMAND_PAGING;
		populated_mapping = 0;
	}
#endif

	if (mmap_should_set_host_ro(flags, prot, 1)) {
		error = set_host_vma(addr, len, PROT_READ | PROT_EXEC, 1/* holding memory_range_lock */);
		if (error) {
			kprintf("do_mmap:set_host_vma failed. %d\n", error);
			goto out;
		}

		ro_vma_mapped = 1;
	}

	phys = 0;
	straight_phys = 0;
	off = 0;
	maxprot = PROT_READ | PROT_WRITE | PROT_EXEC;
	if (!(flags & MAP_ANONYMOUS)) {
		off = off0;
		error = fileobj_create(fd, &memobj, &maxprot,
				       flags, addr0);
		if (memobj && memobj->path && !strncmp(memobj->path, "/dev/shm/ucx_posix", 18)) {
			kprintf("%s: mmap flags: %lx, path: %s, memobj->flags: %lx, "
					"pgshift: %d, p2align: %d -> FIXING page size\n",
					__func__, flags, memobj->path, memobj->flags, pgshift, p2align);
			pgshift = PAGE_SHIFT;
			p2align = PAGE_P2ALIGN;
			populated_mapping = 1;
		}
#ifdef ATTACHED_MIC
		/*
		 * XXX: refuse device mapping in attached-mic now:
		 *
		 * In attached-mic, ihk_mc_map_memory() cannot convert into a local
		 * physical address a remote physical address which point KNC's memory.
		 * It seems that ihk_mc_map_memory() needs to set up SMPT.
		 */
		if (error == -ESRCH) {
			error = -ENODEV;
		}
#endif
#ifdef PROFILE_ENABLE
		if (!error) {
			profile_event_add(PROFILE_mmap_regular_file, len);
		}
#endif // PROFILE_ENABLE
		if (error == -ESRCH) {
			int populate_flags = 0;

			dkprintf("do_mmap:hit non VREG\n");
			/*
			 * XXX: temporary:
			 *
			 * device mappings are uncachable
			 * until memory type setting codes are implemented.
			 */
			if (1) {
				vrflags &= ~VR_MEMTYPE_MASK;
				vrflags |= VR_MEMTYPE_UC;
			}

#ifdef ENABLE_FUGAKU_HACKS
#ifdef ENABLE_TOFU
			if (!strncmp("/var/opt/FJSVtcs/ple/daemonif/",
						thread->proc->fd_path[fd], 30)) {
				dkprintf("%s: MAP_POPULATE | MAP_LOCKED for %s\n",
					__func__, thread->proc->fd_path[fd]);
				populate_flags = (MAP_POPULATE | MAP_LOCKED);
			}
#endif
#endif

			error = devobj_create(fd, len, off, &memobj, &maxprot, 
					prot,
					populate_flags | (flags & (MAP_POPULATE | MAP_LOCKED)));

			if (!error) {
#ifdef PROFILE_ENABLE
				profile_event_add(PROFILE_mmap_device_file, len);
#endif // PROFILE_ENABLE
				if (memobj->path &&
						(!strncmp("/tmp/ompi.", memobj->path, 10) ||
						 !strncmp("/dev/shm/", memobj->path, 9))) {
					pgshift = PAGE_SHIFT;
					p2align = PAGE_P2ALIGN;
					populated_mapping = 1;
				}
			}
		}
		if (error) {
			kprintf("%s: error: file mapping failed, fd: %d, error: %d\n",
					__func__, fd, error);
			goto out;
		}

		/* hugetlbfs files are pre-created in fileobj_create, but
		 * need extra processing
		 */
		if (memobj && (memobj->flags & MF_HUGETLBFS)) {
			error = hugefileobj_create(memobj, len, off, &pgshift,
						   addr0);
			if (error) {
				memobj->ops->free(memobj);
				kprintf("%s: error creating hugetlbfs memobj, fd: %d, error: %d\n",
					__func__, fd, error);
				goto out;
			}
			p2align = pgshift - PAGE_SHIFT;
		}

		/* Obtain mapping address - delayed to use proper p2align */
		if (!(flags & MAP_FIXED))
			error = search_free_space(len, PAGE_SHIFT + p2align,
						  &addr);
		if (error) {
			ekprintf("do_mmap:search_free_space(%lx,%lx,%d) failed. %d\n",
				 len, region->map_end, p2align, error);
			goto out;
		}
		if (mmap_should_set_host_ro(flags, prot, 0)) {
			error = set_host_vma(addr, len, PROT_READ | PROT_EXEC,
					     1/* holding memory_range_lock */);
			if (error) {
				kprintf("do_mmap:set_host_vma failed. %d\n",
					error);
				goto out;
			}

			ro_vma_mapped = 1;
		}
		if (memobj->flags & MF_HUGETLBFS) {
			dkprintf("Created hugefileobj %p (%d:%x %llx-%llx, fd %d, pgshift %d)\n",
				 memobj, len, off, addr, addr+len, fd, pgshift);
		} else if (memobj->flags & MF_DEV_FILE) {
			dkprintf("%s: device fd: %d off: %lu mapping at %p - %p\n",
				 __func__, fd, off, addr, addr + len);
		}
	}
	/* Prepopulated ANONYMOUS mapping */
	else if (!(vrflags & VR_DEMAND_PAGING)
			&& !(flags & MAP_SHARED)
			&& ((vrflags & VR_PROT_MASK) != VR_PROT_NONE)) {
		npages = len >> PAGE_SHIFT;
		/* Small allocations mostly benefit from closest RAM,
		 * otherwise follow user requested policy */
		unsigned long ap_flag =
			(!(flags & MAP_STACK) && len >= thread->proc->mpol_threshold) ||
			((flags & MAP_STACK) && !(thread->proc->mpol_flags & MPOL_NO_STACK)) ?
			IHK_MC_AP_USER : 0;

		if (ap_flag) {
			vrflags |= VR_AP_USER;
		}

		p = _ihk_mc_alloc_aligned_pages_node(npages, p2align, IHK_MC_AP_NOWAIT | ap_flag, -1, IHK_MC_PG_USER, addr0, __FILE__, __LINE__);
		if (p == NULL) {
			dkprintf("%s: warning: failed to allocate %d contiguous pages "
					" (bytes: %lu, pgshift: %d), enabling demand paging\n",
					__FUNCTION__,
					npages, npages * PAGE_SIZE, p2align);

			/* Give demand paging a chance */
			vrflags |= VR_DEMAND_PAGING;
			populated_mapping = 0;

#ifdef PROFILE_ENABLE
			profile_event_add(PROFILE_mmap_anon_no_contig_phys, len);
#endif // PROFILE_ENABLE
			error = zeroobj_create(&memobj);
			if (error) {
				ekprintf("%s: zeroobj_create failed, error: %d\n",
						__FUNCTION__, error);
				goto out;
			}
		}
		else {
#ifdef PROFILE_ENABLE
			profile_event_add(PROFILE_mmap_anon_contig_phys, len);
#endif // PROFILE_ENABLE
			dkprintf("%s: 0x%x:%lu MAP_ANONYMOUS "
					"allocated %d pages, p2align: %lx\n",
					__FUNCTION__, addr, len, npages, p2align);
			phys = virt_to_phys(p);
		}
	}
	else if (mmap_is_shared(flags)) {
		dkprintf("%s: MAP_SHARED,flags=%x,len=%ld\n", __FUNCTION__, flags, len);
		memset(&ads, 0, sizeof(ads));
		ads.shm_segsz = len;
		ads.shm_perm.mode = SHM_DEST;
		ads.init_pgshift = PAGE_SHIFT + p2align;
		error = shmobj_create(&ads, &memobj);
		if (error) {
			ekprintf("do_mmap:shmobj_create failed. %d\n", error);
			goto out;
		}
	}
	else {
		dkprintf("%s: anon&demand-paging\n", __FUNCTION__);
		error = zeroobj_create(&memobj);
		if (error) {
			ekprintf("do_mmap:zeroobj_create failed. %d\n", error);
			goto out;
		}
	}

	maxprot = mmap_update_private_maxprot(flags, maxprot);
	error = mmap_prot_denied_result(prot, maxprot, &denied);
	if (error) {
		ekprintf("do_mmap:denied %x. %x %x\n", denied, prot, maxprot);
		goto out;
	}
	vrflags |= mmap_maxprot_to_vrflags(maxprot);

	/*
	 * Large anonymous non-fix allocations are in straight mapping,
	 * pretend demand paging to avoid filling in PTEs
	 */
	if (mmap_should_force_straight(flags, proc->straight_map, phys, len,
			proc->straight_map_threshold)) {
			dkprintf("%s: range 0x%lx:%lu will be straight, addding VR_DEMAND\n",
					__FUNCTION__, addr, len);
			vrflags |= VR_DEMAND_PAGING;
			straight_phys = phys;
			phys = 0;
#ifdef PROFILE_ENABLE
			profile_event_add(PROFILE_mmap_anon_straight, len);
#endif // PROFILE_ENABLE
	}
	else if ((flags & MAP_ANONYMOUS) && proc->straight_map &&
			!(flags & MAP_FIXED) && phys) {
#ifdef PROFILE_ENABLE
		if (get_this_cpu_local_var()->current->profile)
			kprintf("%s: contiguous but not straight? len: %lu\n", __func__, len);
		profile_event_add(PROFILE_mmap_anon_not_straight, len);
#endif // PROFILE_ENABLE
	}

	error = add_process_memory_range(thread->vm, addr, addr+len, phys,
			vrflags, memobj, off, pgshift, private_data, &range);
	if (error) {
		kprintf("%s: add_process_memory_range failed for 0x%lx:%lu"
				" flags: %lx, vrflags: %lx, pgshift: %d, error: %d\n",
				__FUNCTION__, addr, addr+len,
				flags, vrflags, pgshift, error);
		goto out;
	}

	/* Update straight mapping start address */
	if (straight_phys) {
		range->straight_start =
			(unsigned long)proc->straight_va +
			(straight_phys - proc->straight_pa);
#ifndef ENABLE_FUGAKU_HACKS
		dkprintf("%s: range 0x%lx:%lu is straight starting at 0x%lx\n",
			 __FUNCTION__, addr, len, range->straight_start);
#else
		dkprintf("%s: range 0x%lx:%lu is straight starting at 0x%lx"
				" (phys: 0x%lx)\n",
				__FUNCTION__, addr, len, range->straight_start,
				straight_phys);
#endif
		memset((void *)phys_to_virt(straight_phys), 0, len);
	}

	/* Determine pre-populated size */
	populate_len = memobj ? min(len, memobj->size) : len;

	if (!(flags & MAP_ANONYMOUS)) {
		if (atomic_cmpxchg4(&memobj->status, MEMOBJ_TO_BE_PREFETCHED,
				    MEMOBJ_READY) ==
		    MEMOBJ_TO_BE_PREFETCHED) {
			populated_mapping = 1;
		}

		/* Update PTEs for pre-mapped memory object */
		if ((memobj->flags & MF_PREMAP) &&
				(proc->mpol_flags & MPOL_SHM_PREMAP)) {
			if (memobj->flags & MF_ZEROFILL) {
				int i;
				enum ihk_mc_pt_attribute ptattr;
				ptattr = arch_vrflag_to_ptattr(range->flag, PF_POPULATE, NULL);

				for (i = 0; i < memobj->nr_pages; ++i) {
					error = ihk_mc_pt_set_range(proc->vm->address_space->page_table,
							proc->vm,
							(void *)range->start + (i * PAGE_SIZE),
							(void *)range->start + (i * PAGE_SIZE) +
							PAGE_SIZE,
							virt_to_phys(memobj->pages[i]),
							ptattr,
							PAGE_SHIFT,
							range,
							0);
					if (error) {
						kprintf("%s: ERROR: mapping %d page of pre-mapped file\n",
								__FUNCTION__, i);
					}
				}
				dkprintf("%s: memobj 0x%lx pre-mapped\n", __FUNCTION__, memobj);
				// 	fileobj && MF_PREMAP && MPOL_SHM_PREMAP case: memory_stat_rss_add() is called in fileobj_create()
			}
			else {
				populated_mapping = 1;
			}
		}
/*
		else if (memobj->flags & MF_REG_FILE) {
			populated_mapping = 1;
			populate_len = memobj->size;
		}
*/
	}

	error = 0;
	p = NULL;
	memobj = NULL;
	ro_vma_mapped = 0;

out:
	if (ro_vma_mapped && !range->straight_start) {
		(void)set_host_vma(addr, len, PROT_READ | PROT_WRITE | PROT_EXEC, 1/* holding memory_range_lock */);
	}
	ihk_rwspinlock_write_unlock_noirq(&thread->vm->memory_range_lock);

	ihk_rwspinlock_read_lock_noirq(&thread->vm->memory_range_lock);
	if (!error && range && range->memobj &&
	    (range->memobj->flags & MF_XPMEM)) {
		error = xpmem_update_process_page_table(thread->vm, range);
		if (error) {
			ekprintf("%s: xpmem_update_process_page_table(): "
				"vm: %p, range: %lx-%lx failed %d\n",
				__func__, thread->vm,
				range->start, range->end, error);
		}
	}
	ihk_rwspinlock_read_unlock_noirq(&thread->vm->memory_range_lock);

	if (!error && populated_mapping &&
			!((vrflags & VR_PROT_MASK) == VR_PROT_NONE) && !range->straight_start) {
		error = populate_process_memory(thread->vm,
				(void *)addr, populate_len);

		if (error) {
			ekprintf("%s: WARNING: populate_process_memory(): "
					"vm: %p, addr: %p, len: %d (flags: %s%s) failed %d\n",
					__FUNCTION__,
					thread->vm, (void *)addr, len,
					(flags & MAP_POPULATE) ? "MAP_POPULATE " : "",
					(flags & MAP_LOCKED) ? "MAP_LOCKED ": "",
					error);
			/*
			 * In this case,
			 * the mapping established by this call should be unmapped
			 * before mmap() returns with error.
			 *
			 * However, the mapping cannot be unmaped simply,
			 * because the mapping can be modified by other thread
			 * because memory_range_lock has been released.
			 *
			 * For the moment, like a linux-2.6.38-8,
			 * the physical page allocation failure is ignored.
			 */
			error = 0;
		}
	}

	if (p && npages > 0) {
		_ihk_mc_free_pages(p, npages, IHK_MC_PG_USER, __FILE__, __LINE__);
	}
	if (memobj) {
		memobj_unref(memobj);
	}

#ifndef ENABLE_FUGAKU_HACKS
	dkprintf("%s: 0x%lx:%8lu, (req: 0x%lx:%lu), prot: %x, flags: %x, "
#else
	if (get_this_cpu_local_var()->current->profile) {
		kprintf("%s: 0x%lx:%8lu, (req: 0x%lx:%lu), prot: %x, flags: %x, "
#endif
			"fd: %d, off: %lu, error: %ld, addr: 0x%lx\n",
			__FUNCTION__,
			addr, len, addr0, len0, prot, flags,
			fd, off0, error, addr);
#ifdef ENABLE_FUGAKU_HACKS
	}
#endif

	return !error ?
		(range->straight_start ? range->straight_start : addr) :
		error;
}

void munmap_write_lock_bridge(void *lock)
{
	ihk_rwspinlock_write_lock_noirq((ihk_rwspinlock_t *)lock);
}

void munmap_write_unlock_bridge(void *lock)
{
	ihk_rwspinlock_write_unlock_noirq((ihk_rwspinlock_t *)lock);
}

int munmap_do_bridge(void *addr, size_t len, int holding_lock)
{
	return do_munmap(addr, len, holding_lock);
}

void munmap_log_bridge(int event, int cpu, unsigned long addr,
		size_t len, int error)
{
	if (event == MUNMAP_LOG_ENTER) {
		dkprintf("[%d]sys_munmap(%lx,%lx)\n", cpu, addr, len);
	}
	else if (event == MUNMAP_LOG_EXIT) {
		dkprintf("[%d]sys_munmap(%lx,%lx): %d\n", cpu, addr, len,
				error);
	}
#ifdef ENABLE_FUGAKU_HACKS
	else if (event == MUNMAP_LOG_ERROR) {
		kprintf("%s: error: %d\n", __func__, error);
	}
#endif
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_munmap(int n, ihk_mc_user_context_t *ctx);
#else
long sys_munmap(int n, ihk_mc_user_context_t *ctx)
{
	const uintptr_t addr = ihk_mc_syscall_arg0(ctx);
	const size_t len0 = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct vm_regions *region = &thread->vm->region;

	return munmap_body_result(thread->vm, &thread->vm->memory_range_lock,
			addr, len0, region->user_start, region->user_end,
			ihk_mc_get_processor_id(), munmap_write_lock_bridge,
			munmap_write_unlock_bridge, munmap_do_bridge,
			munmap_log_bridge);
}
#endif

static struct vm_range *mprotect_lookup_bridge(struct process_vm *vm,
		unsigned long start, unsigned long end)
{
	return lookup_process_memory_range(vm, start, end);
}

static struct vm_range *mprotect_next_bridge(struct process_vm *vm,
		struct vm_range *range)
{
	return next_process_memory_range(vm, range);
}

static int mprotect_split_bridge(struct process_vm *vm,
		struct vm_range *range, unsigned long addr,
		struct vm_range **new_range)
{
	return split_process_memory_range(vm, range, addr, new_range);
}

static int mprotect_join_bridge(struct process_vm *vm, struct vm_range *left,
		struct vm_range *right)
{
	return join_process_memory_range(vm, left, right);
}

static int mprotect_change_bridge(struct process_vm *vm,
		struct vm_range *range, unsigned long protflags)
{
	return change_prot_process_memory_range(vm, range, protflags);
}

static int mprotect_set_host_vma_bridge(unsigned long start, size_t len,
		int prot, int holding_lock)
{
	return set_host_vma(start, len, prot, holding_lock);
}

void mprotect_flush_nfo_bridge(void)
{
	flush_nfo_tlb();
}

static void mprotect_flush_tlb_bridge(void)
{
	flush_tlb();
}

static void mprotect_log_bridge(const struct mprotect_log_record *record)
{
	if (!record)
		return;

	if (record->event == MPROTECT_LOG_ENTER) {
		dkprintf("[%d]sys_mprotect(%lx,%lx,%x)\n", record->cpu,
				record->start, record->len, record->prot);
	}
	else if (record->event == MPROTECT_LOG_INVALID_RANGE) {
		if (record->error == -EINVAL) {
			ekprintf("[%d]sys_mprotect(%lx,%lx,%x): -EINVAL\n",
					record->cpu, record->start, record->len,
					record->prot);
		}
		else if (record->error == -ENOMEM) {
			ekprintf("[%d]sys_mprotect(%lx,%lx,%x): -ENOMEM\n",
					record->cpu, record->start, record->len,
					record->prot);
		}
		else {
			ekprintf("[%d]sys_mprotect(%lx,%lx,%x): %d\n",
					record->cpu, record->start, record->len,
					record->prot, record->error);
		}
	}
	else if (record->event == MPROTECT_LOG_STRAIGHT_IGNORED) {
		kprintf("%s: ignored for straight mapping 0x%lx\n",
				"sys_mprotect", record->start);
	}
	else if (record->event == MPROTECT_LOG_NOT_CONTIG) {
		ekprintf("sys_mprotect(%lx,%lx,%x):not contiguous\n",
				record->start, record->len, record->prot);
	}
	else if (record->event == MPROTECT_LOG_DENIED) {
		ekprintf("sys_mprotect(%lx,%lx,%x):denied %lx. %lx %lx\n",
				record->start, record->len, record->prot,
				record->denied, record->protflags,
				record->range_flags);
	}
	else if (record->event == MPROTECT_LOG_CANNOT_CHANGE) {
		ekprintf("sys_mprotect(%lx,%lx,%x):cannot change\n",
				record->start, record->len, record->prot);
	}
	else if (record->event == MPROTECT_LOG_SPLIT_FAILED) {
		ekprintf("sys_mprotect(%lx,%lx,%x):split failed. %d\n",
				record->start, record->len, record->prot,
				record->error);
	}
	else if (record->event == MPROTECT_LOG_CHANGE_FAILED) {
		ekprintf("sys_mprotect(%lx,%lx,%x):change failed. %d\n",
				record->start, record->len, record->prot,
				record->error);
	}
	else if (record->event == MPROTECT_LOG_JOIN_FAILED) {
		ekprintf("sys_mprotect(%lx,%lx,%x):join failed. %d\n",
				record->start, record->len, record->prot,
				record->error);
	}
	else if (record->event == MPROTECT_LOG_SET_HOST_FAILED) {
		kprintf("sys_mprotect:set_host_vma failed. %d\n",
				record->error);
	}
	else if (record->event == MPROTECT_LOG_EXIT) {
		dkprintf("[%d]sys_mprotect(%lx,%lx,%x): %d\n", record->cpu,
				record->start, record->len, record->prot,
				record->error);
	}
}

long sys_mprotect(int n, ihk_mc_user_context_t *ctx)
{
	const uintptr_t start = ihk_mc_syscall_arg0(ctx);
	const size_t len0 = ihk_mc_syscall_arg1(ctx);
	const int prot = ihk_mc_syscall_arg2(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct vm_regions *region = &thread->vm->region;

	return mprotect_body_result(thread->vm, &thread->vm->memory_range_lock,
			start, len0, prot, region->user_start, region->user_end,
			(unsigned long)thread->proc->straight_va,
			thread->proc->straight_len, ihk_mc_get_processor_id(),
			offsetof(struct vm_range, start),
			offsetof(struct vm_range, end),
			offsetof(struct vm_range, flag),
			munmap_write_lock_bridge, munmap_write_unlock_bridge,
			mprotect_lookup_bridge, mprotect_next_bridge,
			mprotect_split_bridge, mprotect_join_bridge,
			mprotect_change_bridge, mprotect_set_host_vma_bridge,
			mprotect_flush_nfo_bridge, mprotect_flush_tlb_bridge,
			mprotect_log_bridge);
}

void brk_flush_bridge(void)
{
	flush_nfo_tlb();
}

void brk_write_lock_bridge(void *lock)
{
	ihk_rwspinlock_write_lock_noirq((ihk_rwspinlock_t *)lock);
}

void brk_write_unlock_bridge(void *lock)
{
	ihk_rwspinlock_write_unlock_noirq((ihk_rwspinlock_t *)lock);
}

unsigned long brk_extend_bridge(void *vm, unsigned long old_end,
		unsigned long address, unsigned long vrflag)
{
	return extend_process_region((struct process_vm *)vm, old_end, address,
			vrflag);
}

void brk_log_bridge(int event, int cpu, unsigned long brk_start,
		unsigned long brk_end, unsigned long value)
{
	if (event == BRK_LOG_ENTER) {
		dkprintf("SC(%d)[sys_brk] brk_start=%lx,end=%lx\n",
				cpu, brk_start, brk_end);
	}
	else if (event == BRK_LOG_SET_END) {
		dkprintf("SC(%d)[sys_brk] brk_end set to %lx\n",
				cpu, value);
	}
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_brk(int n, ihk_mc_user_context_t *ctx);
#else
long sys_brk(int n, ihk_mc_user_context_t *ctx)
{
	unsigned long address = ihk_mc_syscall_arg0(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return brk_body_result(thread->vm, &thread->vm->region,
			&thread->vm->memory_range_lock, address,
			ihk_mc_get_processor_id(),
			__builtin_offsetof(struct vm_regions, brk_start),
			__builtin_offsetof(struct vm_regions, brk_end),
			__builtin_offsetof(struct vm_regions, brk_end_allocated),
			brk_flush_bridge, brk_write_lock_bridge,
			brk_write_unlock_bridge, brk_extend_bridge,
			brk_log_bridge);
}
#endif

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_getpid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_getpid_body_result(get_this_cpu_local_var()->current,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, pid));
}

long sys_getppid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_getppid_body_result(get_this_cpu_local_var()->current,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, ppid_parent),
			__builtin_offsetof(struct process, pid));
}
#endif

static int settid(struct thread *thread, int nr_tids, int *tids)
{
	int ret;
	struct syscall_request request IHK_DMA_ALIGN;

	memset(&request, 0, sizeof(request));

	request.number = __NR_gettid;
	/*
	 * If nr_tids is non-zero, tids should point to an array of ints
	 * where the thread ids of the mcexec process are expected.
	 */
	request.args[4] = nr_tids;
	request.args[5] = virt_to_phys(tids);
	if ((ret = do_syscall(&request, ihk_mc_get_processor_id())) < 0) {
		kprintf("%s: WARNING: do_syscall returns %d\n",
			__FUNCTION__, ret);
	}
	return ret;
}

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_gettid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_gettid_body_result(get_this_cpu_local_var()->current,
			__builtin_offsetof(struct thread, tid));
}
#endif

extern void ptrace_report_signal(struct thread *thread, int sig);
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
static void
ptrace_report_signal_bridge(void *thread, int sig)
{
	ptrace_report_signal((struct thread *)thread, sig);
}

static long
ptrace_report_exec_arch_event_bridge(void *thread, void *ctx, long setret)
{
	return arch_ptrace_syscall_event((struct thread *)thread,
			(ihk_mc_user_context_t *)ctx, setret);
}
#endif

static int ptrace_report_exec(struct thread *thread,
		ihk_mc_user_context_t *syscall_ctx)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	static const struct ptrace_report_exec_offsets offsets = {
		.thread_ptrace_offset = __builtin_offsetof(struct thread,
							   ptrace),
		.thread_ctx_offset = __builtin_offsetof(struct thread, ctx),
		.thread_uctx_offset = __builtin_offsetof(struct thread, uctx),
		.thread_ptrace_saved_uctx_offset =
			__builtin_offsetof(struct thread, ptrace_saved_uctx),
		.thread_ptrace_saved_uctx_valid_offset =
			__builtin_offsetof(struct thread,
					   ptrace_saved_uctx_valid),
	};
	ihk_mc_kernel_context_t ctx;

	return ptrace_report_exec_body_result(thread, syscall_ctx,
			&offsets, sizeof(ctx), sizeof(*syscall_ctx), &ctx,
			preempt_enable, preempt_disable,
			ptrace_report_signal_bridge,
			ptrace_report_exec_arch_event_bridge);
#else
	int ptrace = thread->ptrace;
	int sig;

	sig = ptrace_exec_event_signal_result(ptrace);
	if (sig) {
		ihk_mc_kernel_context_t ctx;

		memcpy(&ctx, &thread->ctx, sizeof ctx);
		preempt_enable();
		ptrace_report_signal(thread, sig);
		preempt_disable();
		memcpy(&thread->ctx, &ctx, sizeof ctx);
	}
	if (thread->ptrace & PT_TRACE_SYSCALL) {
		ihk_mc_kernel_context_t ctx;
		ihk_mc_user_context_t *new_uctx = thread->uctx;

		memcpy(&ctx, &thread->ctx, sizeof ctx);
		memcpy(&thread->ptrace_saved_uctx, syscall_ctx,
				sizeof(thread->ptrace_saved_uctx));
		thread->ptrace_saved_uctx_valid = 1;
		thread->uctx = &thread->ptrace_saved_uctx;
		arch_ptrace_syscall_event(thread,
				&thread->ptrace_saved_uctx, 0);
		thread->uctx = new_uctx;
		memcpy(&thread->ctx, &ctx, sizeof ctx);
	}
	return 0;
#endif
}

void ptrace_syscall_event(struct thread *thread)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	ptrace_syscall_event_body_result(thread,
			__builtin_offsetof(struct thread, ptrace),
			ptrace_report_signal_bridge);
#else
	int sig = ptrace_syscall_event_signal_result(thread->ptrace);

	if (sig) {
		ptrace_report_signal(thread, sig);
	}
#endif
}

static int ptrace_check_clone_event(struct thread *thread, int clone_flags)
{
	return ptrace_clone_event_result(thread->ptrace, clone_flags);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
static int ptrace_attach_thread_bridge(unsigned long thread_addr,
		unsigned long proc_addr);

static void
process_ptrace_attach_mcs_lock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_lock((struct mcs_rwlock_lock *)lock_addr,
			(struct mcs_rwlock_node_irqsave *)node);
}

static void
process_ptrace_attach_mcs_unlock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_unlock((struct mcs_rwlock_lock *)lock_addr,
			(struct mcs_rwlock_node_irqsave *)node);
}

static int
process_ptrace_attach_alloc_debugreg_bridge(void *thread)
{
	return (int)alloc_debugreg((struct thread *)thread);
}

static void
process_ptrace_attach_clear_single_step_bridge(void *thread)
{
	clear_single_step((struct thread *)thread);
}

static void
process_ptrace_attach_hold_thread_bridge(void *thread)
{
	hold_thread((struct thread *)thread);
}

static void
process_ptrace_attach_log_bridge(int event, int pid,
		unsigned long value, int error)
{
	(void)value;
	(void)error;

	if (event == PROCESS_PTRACE_TRACEME_LOG_PARENT) {
		dkprintf("ptrace_attach() parent->pid=%d\n", pid);
	}
}

static void
ptrace_report_clone_noirq_lock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_lock_noirq((struct mcs_rwlock_lock *)lock_addr,
			(struct mcs_rwlock_node *)node);
}

static void
ptrace_report_clone_noirq_unlock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_unlock_noirq((struct mcs_rwlock_lock *)lock_addr,
			(struct mcs_rwlock_node *)node);
}

static void
ptrace_report_clone_log_bridge(int event, int value, int result)
{
	if (event == PTRACE_REPORT_CLONE_LOG_ENTER) {
		dkprintf("ptrace_report_clone,enter\n");
	}
	else if (event == PTRACE_REPORT_CLONE_LOG_KILL_SIGCHLD) {
		(void)value;
		dkprintf("ptrace_report_clone,kill SIGCHLD\n");
	}
	else if (event == PTRACE_REPORT_CLONE_LOG_DO_KILL_FAILED) {
		(void)value;
		(void)result;
		dkprintf("ptrace_report_clone,do_kill failed\n");
	}
}
#endif

static int ptrace_attach_thread(struct thread *thread, struct process *proc)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	static const struct process_ptrace_attach_offsets offsets = {
		.thread_proc_offset = __builtin_offsetof(struct thread, proc),
		.thread_report_proc_offset =
			__builtin_offsetof(struct thread, report_proc),
		.thread_report_siblings_list_offset =
			__builtin_offsetof(struct thread, report_siblings_list),
		.thread_ptrace_debugreg_offset =
			__builtin_offsetof(struct thread, ptrace_debugreg),
		.proc_pid_offset = __builtin_offsetof(struct process, pid),
		.proc_parent_offset =
			__builtin_offsetof(struct process, parent),
		.proc_main_thread_offset =
			__builtin_offsetof(struct process, main_thread),
		.proc_children_lock_offset =
			__builtin_offsetof(struct process, children_lock),
		.proc_threads_lock_offset =
			__builtin_offsetof(struct process, threads_lock),
		.proc_children_list_offset =
			__builtin_offsetof(struct process, children_list),
		.proc_siblings_list_offset =
			__builtin_offsetof(struct process, siblings_list),
		.proc_ptraced_siblings_list_offset =
			__builtin_offsetof(struct process,
					   ptraced_siblings_list),
		.proc_ptraced_children_list_offset =
			__builtin_offsetof(struct process,
					   ptraced_children_list),
		.proc_report_threads_list_offset =
			__builtin_offsetof(struct process,
					   report_threads_list),
	};
	struct mcs_rwlock_node_irqsave lock;

	return process_ptrace_attach_thread_body_result(thread, proc,
			&offsets, &lock,
			process_ptrace_attach_mcs_lock_bridge,
			process_ptrace_attach_mcs_unlock_bridge,
			process_ptrace_attach_alloc_debugreg_bridge,
			process_ptrace_attach_clear_single_step_bridge,
			process_ptrace_attach_hold_thread_bridge,
			process_ptrace_attach_log_bridge);
#else
	struct process *child;
	struct process *parent;
	struct mcs_rwlock_node_irqsave lock;
	int error = 0;

	if (thread->report_proc) {
		mcs_rwlock_writer_lock(&thread->report_proc->threads_lock,
				       &lock);
		process_list_detach_result(&thread->report_siblings_list);
		mcs_rwlock_writer_unlock(&thread->report_proc->threads_lock,
					 &lock);
	}

	mcs_rwlock_writer_lock(&proc->threads_lock, &lock);
	process_thread_report_attach_result(thread, 0, 0, 0,
		__builtin_offsetof(struct thread, report_proc),
		proc, &thread->report_siblings_list,
		&proc->report_threads_list);
	mcs_rwlock_writer_unlock(&proc->threads_lock, &lock);

	child = thread->proc;
	if (thread == child->main_thread) {
		parent = child->parent;
		dkprintf("ptrace_attach() parent->pid=%d\n", parent->pid);
		mcs_rwlock_writer_lock(&parent->children_lock, &lock);
		process_list_detach_result(&child->siblings_list);
		process_list_add_tail_result(&child->ptraced_siblings_list,
					     &parent->ptraced_children_list);
		mcs_rwlock_writer_unlock(&parent->children_lock, &lock);

		mcs_rwlock_writer_lock(&proc->children_lock, &lock);
		process_ptrace_main_attach_reparent_result(child,
			__builtin_offsetof(struct process, parent), proc,
			&child->siblings_list, &proc->children_list);
		mcs_rwlock_writer_unlock(&proc->children_lock, &lock);
	}

	if (thread->ptrace_debugreg == NULL) {
		error = alloc_debugreg(thread);
		if (error < 0) {
			goto out;
		}
	}
	hold_thread(thread);

	clear_single_step(thread);
out:
	return error;
#endif
}

static int ptrace_report_clone(struct thread *thread, struct thread *new, int event)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	static const struct ptrace_report_clone_offsets offsets = {
		.thread_proc_offset = __builtin_offsetof(struct thread, proc),
		.thread_tid_offset = __builtin_offsetof(struct thread, tid),
		.thread_status_offset =
			__builtin_offsetof(struct thread, status),
		.thread_exit_status_offset =
			__builtin_offsetof(struct thread, exit_status),
		.thread_ptrace_offset =
			__builtin_offsetof(struct thread, ptrace),
		.thread_ptrace_eventmsg_offset =
			__builtin_offsetof(struct thread, ptrace_eventmsg),
		.proc_pid_offset = __builtin_offsetof(struct process, pid),
		.proc_parent_offset =
			__builtin_offsetof(struct process, parent),
		.proc_status_offset =
			__builtin_offsetof(struct process, status),
		.proc_update_lock_offset =
			__builtin_offsetof(struct process, update_lock),
		.proc_waitpid_q_offset =
			__builtin_offsetof(struct process, waitpid_q),
	};
	struct mcs_rwlock_node lock;
	struct mcs_rwlock_node updatelock;

	return ptrace_report_clone_body_result(thread, new, event,
			get_this_cpu_local_var()->current, &offsets, &lock, &updatelock,
			ptrace_report_clone_noirq_lock_bridge,
			ptrace_report_clone_noirq_unlock_bridge,
			ptrace_attach_thread_bridge,
			ptrace_detach_do_kill_bridge,
			thread_exit_waitq_wake_bridge,
			ptrace_report_clone_log_bridge);
#else
	dkprintf("ptrace_report_clone,enter\n");
	int error = 0;
	long rc;
	struct siginfo info;
	struct mcs_rwlock_node lock;
	struct mcs_rwlock_node updatelock;
	int parent_pid;

	/* Save reason why stopped and process state for wait4() to reap */
	mcs_rwlock_writer_lock_noirq(&thread->proc->update_lock, &lock);
	thread->exit_status = (SIGTRAP | (event << 8));
	/* Transition process state */
	thread->proc->status = PS_TRACED;
	thread->status = PS_TRACED;
	thread->ptrace_eventmsg = new->tid;
	thread->ptrace &= ~PT_TRACE_SYSCALL;
	parent_pid = thread->proc->parent->pid;
	mcs_rwlock_writer_unlock_noirq(&thread->proc->update_lock, &lock);

	if (ptrace_clone_reparent_result(event)) {
		/* PTRACE_EVENT_FORK or PTRACE_EVENT_VFORK or PTRACE_EVENT_CLONE */

		mcs_rwlock_writer_lock_noirq(&new->proc->update_lock, &updatelock);
		/* set ptrace features to new process */
		new->ptrace = thread->ptrace;

		ptrace_attach_thread(new, thread->proc->parent);

		/* trace and SIGSTOP */
		new->exit_status = SIGSTOP;
		new->proc->status = PS_TRACED;
		new->status = PS_TRACED;

		mcs_rwlock_writer_unlock_noirq(&new->proc->update_lock, &updatelock);
	}

	dkprintf("ptrace_report_clone,kill SIGCHLD\n");
	memset(&info, '\0', sizeof info);
	info.si_signo = SIGCHLD;
	info.si_code = CLD_TRAPPED;
	info._sifields._sigchld.si_pid = thread->proc->pid;
	info._sifields._sigchld.si_status = thread->exit_status;
	rc = do_kill(get_this_cpu_local_var()->current, parent_pid, -1, SIGCHLD, &info, 0);
	if(rc < 0) {
		dkprintf("ptrace_report_clone,do_kill failed\n");
	}

	/* Wake parent (if sleeping in wait4()) */
	waitq_wakeup(&thread->proc->parent->waitpid_q);

	return error;
#endif
}

static void
munmap_all_free_ranges_bridge(void *vm)
{
	free_process_memory_ranges(vm);
}

static void
munmap_all_log_bridge(unsigned long addr, size_t size, int error)
{
	kprintf("munmap_all():do_munmap(%p,%lx) failed. %d\n",
			(void *)addr, size, error);
}

static void munmap_all(void)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process_vm *vm = thread->vm;

	munmap_all_body_result(vm, &vm->memory_range_lock, &vm->region,
			offsetof(struct vm_range, start),
			offsetof(struct vm_range, end),
			offsetof(struct vm_regions, map_start),
			offsetof(struct vm_regions, map_end),
			munmap_write_lock_bridge, munmap_write_unlock_bridge,
			mprotect_lookup_bridge, mprotect_next_bridge,
			munmap_do_bridge, munmap_all_free_ranges_bridge,
			munmap_all_log_bridge);
} /* munmap_all() */

static int do_execveat(ihk_mc_user_context_t *ctx, int dirfd,
		const char *filename, char **argv, char **envp, int flags)
{
	int error;
	long ret;

	char *argv_flat = NULL;
	int argv_flat_len = 0;
	char *envp_flat = NULL;
	int envp_flat_len = 0;
	
	struct syscall_request request IHK_DMA_ALIGN;
	struct program_load_desc *desc;
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process_vm *vm = thread->vm;
	struct vm_range *range;
	struct process *proc = thread->proc;
	ihk_mc_user_context_t execve_ctx;
	int i;

	memcpy(&execve_ctx, ctx, sizeof(execve_ctx));

	ihk_rwspinlock_read_lock_noirq(&vm->memory_range_lock);

	range = lookup_process_memory_range(vm, (unsigned long)filename, 
			(unsigned long)filename+1);

	if (range == NULL || !(range->flag & VR_PROT_READ)) {
		ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);
		kprintf("execve(): ERROR: filename is bad address\n");
		return -EFAULT;
	}
	
	ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);

	desc = _ihk_mc_alloc_aligned_pages_node(4, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	if (!desc) {
		kprintf("execve(): ERROR: allocating program descriptor\n");
		return -ENOMEM;
	}

	memset((void*)desc, 0, 4 * PAGE_SIZE);

	/* Request host to open executable and load ELF section descriptions */
	request.number = __NR_execve;  
	request.args[0] = 1;  /* 1st phase - get ELF desc */
	request.args[1] = dirfd;
	request.args[2] = (unsigned long)filename;
	request.args[3] = virt_to_phys(desc);
	request.args[4] = flags;
	ret = do_syscall(&request, ihk_mc_get_processor_id());

	if (ret != 0) {
		dkprintf("execve(): ERROR: host failed to load elf header, errno: %d\n", 
				ret);
		ret = -ret;
		goto end;
	}

	dkprintf("execve(): ELF desc received, num sections: %d\n",
		desc->num_sections);
	
	/* for shebang script we get extra argvs from mcexec */
	if (desc->args_len) {
		desc->args = ((char *)desc) + sizeof(struct program_load_desc) +
			     sizeof(struct program_image_section) *
			     desc->num_sections;
	}

	/* Flatten argv and envp into kernel-space buffers */
	argv_flat_len = flatten_strings_from_user(desc->args, argv,
						  &argv_flat);
	if (argv_flat_len < 0) {
		char *kfilename;
		int len = strlen_user(filename);

		kfilename = kmalloc_tracked(len + 1, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		if(kfilename)
			strcpy_from_user(kfilename, filename);
		kprintf("ERROR: no argv for executable: %s?\n", kfilename? kfilename: "");
		if(kfilename)
			kfree_tracked(kfilename, __FILE__, __LINE__);
		ret = argv_flat_len;
		goto end;
	}
	desc->args = NULL;
	desc->args_len = 0;

	envp_flat_len = flatten_strings_from_user(NULL, envp, &envp_flat);
	if (envp_flat_len < 0) {
		char *kfilename;
		int len = strlen_user(filename);

		kfilename = kmalloc_tracked(len + 1, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		if(kfilename)
			strcpy_from_user(kfilename, filename);
		kprintf("ERROR: no envp for executable: %s?\n", kfilename? kfilename: "");
		if(kfilename)
			kfree_tracked(kfilename, __FILE__, __LINE__);
		ret = envp_flat_len;
		goto end;
	}

	/* Unmap all memory areas of the process, userspace will be gone */
	munmap_all();

	/* Code assumes no process switch from here on */
	preempt_disable();
	ihk_mc_init_user_process(&thread->ctx, &thread->uctx,
			((char *)thread) +
			KERNEL_STACK_NR_PAGES * PAGE_SIZE, desc->entry, 0);

	/* map_start / map_end is used to track memory area
	 * to which the program is loaded
	 */
	vm->region.map_start = vm->region.map_end = LD_TASK_UNMAPPED_BASE;

	/* Create virtual memory ranges and update args/envs */
	if ((ret = prepare_process_ranges_args_envs(thread, desc, desc,
			PTATTR_NO_EXECUTE | PTATTR_WRITABLE | PTATTR_FOR_USER,
			argv_flat, argv_flat_len, envp_flat, envp_flat_len)) != 0) {
		kprintf("execve(): ERROR: preparing ranges, args, envs, stack, ret: %d\n",
			ret);
		preempt_enable();
		/* control can't be rolled back because vm_range is gone */
		do_kill(thread, thread->proc->pid, thread->tid, SIGKILL, NULL, 0);
		goto end;
	}
	
	/* Clear host user space PTEs */
	clear_host_pte(vm->region.user_start,
			(vm->region.user_end - vm->region.user_start), 0);

	/* Request host to transfer ELF image */
	request.number = __NR_execve;
	request.args[0] = 2;  /* 2nd phase - transfer ELF image */
	request.args[1] = virt_to_phys(desc);
	request.args[2] = sizeof(struct program_load_desc) + 
		sizeof(struct program_image_section) * desc->num_sections;

	if ((ret = do_syscall(&request, ihk_mc_get_processor_id())) != 0) {
		preempt_enable();
		/* control can't be rolled back because vm_range is gone */
		do_kill(thread, thread->proc->pid, thread->tid, SIGKILL, NULL, 0);
		goto end;
	}

	for(i = 0; i < _NSIG; i++){
		if(thread->sigcommon->action[i].sa.sa_handler != SIG_IGN &&
		   thread->sigcommon->action[i].sa.sa_handler != SIG_DFL)
			thread->sigcommon->action[i].sa.sa_handler = SIG_DFL;
	}

	/* Reset floating-point environment to default. */
	clear_fp_regs();

	/* Reset sigaltstack to default */
	thread->sigstack.ss_sp = NULL;
	thread->sigstack.ss_flags = SS_DISABLE;
	thread->sigstack.ss_size = 0;

	error = ptrace_report_exec(thread, &execve_ctx);
	if (error) {
		kprintf("execve(): ERROR: ptrace_report_exec()\n");
	}

	/* Switch to new execution context */
	dkprintf("execve(): switching to new process\n");
	proc->execed = 1;
	
	ret = 0;
end:
	if (envp_flat) {
		kfree_tracked(envp_flat, __FILE__, __LINE__);
	}
	if (argv_flat) {
		kfree_tracked(argv_flat, __FILE__, __LINE__);
	}
	_ihk_mc_free_pages(desc, 4, IHK_MC_PG_KERNEL, __FILE__, __LINE__);

	if (!ret) {
		unsigned long irqstate;

		/* Lock run queue because enter_user_mode expects to release it */
		irqstate = cpu_disable_interrupt_save();
		ihk_mc_spinlock_lock_noirq(
			&(get_this_cpu_local_var()->runq_lock));
		get_this_cpu_local_var()->runq_irqstate = irqstate;
		preempt_enable();

		ihk_mc_switch_context(NULL, &thread->ctx, thread);

		/* not reached */
		return -EFAULT;
	}

	/* no preempt_enable, errors can only happen before we disabled it */

	return ret;
}

static int
syscall_execveat_bridge(void *ctx, int dirfd, const char *filename,
		char **argv, char **envp, int flags)
{
	return do_execveat((ihk_mc_user_context_t *)ctx, dirfd, filename,
			argv, envp, flags);
}

long sys_execve(int n, ihk_mc_user_context_t *ctx)
{
	return execve_body_result(ctx,
			(const char *)ihk_mc_syscall_arg0(ctx),
			(char **)ihk_mc_syscall_arg1(ctx),
			(char **)ihk_mc_syscall_arg2(ctx),
			syscall_execveat_bridge);
}

unsigned long do_fork(int clone_flags, unsigned long newsp,
                      unsigned long parent_tidptr, unsigned long child_tidptr,
                      unsigned long tlsblock_base, unsigned long curpc,
                      unsigned long cursp)
{
	int cpuid;
	int parent_cpuid;
	struct thread *old = get_this_cpu_local_var()->current;
	struct process *oldproc = old->proc;
	struct process *newproc;
	struct thread *new;
	struct syscall_request request1 IHK_DMA_ALIGN;
	int ptrace_event = 0;
	int termsig = clone_flags & 0x000000ff;
#if 0
	const struct ihk_mc_cpu_info *cpu_info = ihk_mc_get_cpu_info();
#endif
	int err = 0;
	unsigned long clone_pthread_start_routine = 0;
	struct vm_range *range = NULL;
	int helper_thread = 0;
	int tid_table_created = 0;

	dkprintf("%s,flags=%08x,newsp=%lx,ptidptr=%lx,"
		"ctidptr=%lx,tls=%lx,curpc=%lx,cursp=%lx",
		__func__, clone_flags, newsp, parent_tidptr,
		child_tidptr, tlsblock_base, curpc, cursp);

	dkprintf("do_fork(): stack_pointr passed in: 0x%lX, stack pointer of caller: 0x%lx\n",
			 newsp, cursp);

	/* CLONE_VM and newsp == parent_tidptr impiles pthread start routine addr */
	if (clone_pthread_marker_result(clone_flags, newsp, parent_tidptr)) {
		old->clone_pthread_start_routine = parent_tidptr;
		dkprintf("%s: clone_pthread_start_routine: 0x%lx\n", __func__,
			old->clone_pthread_start_routine);
		return 0;
	}

	/* Clear pthread routine addr regardless if we succeed */
	clone_pthread_start_routine = old->clone_pthread_start_routine;
	old->clone_pthread_start_routine = 0;

	parent_cpuid = old->cpu_id;
	err = clone_flags_result(clone_flags, oldproc->coredump_barrier_count);
	if (err) {
		if (((clone_flags & CLONE_VM) && !(clone_flags & CLONE_THREAD)) ||
			(!(clone_flags & CLONE_VM) && (clone_flags & CLONE_THREAD))) {
			kprintf("clone(): ERROR: CLONE_VM and CLONE_THREAD should be set together\n");
		}
		return err;
	}

#if 0
	if (!allow_oversubscribe && rusage.num_threads >= cpu_info->ncpus) {
		kprintf("%s: ERROR: CPU oversubscription is not allowed. Specify -O option in mcreboot.sh to allow it.\n", __FUNCTION__);
		return -EINVAL;
	}
#endif

	/* N-th creation put the new on Linux CPU. It's turned off when zero is 
	   set to uti_thread_rank. */
	if (oldproc->uti_thread_rank) {
		if (oldproc->clone_count + 1 == oldproc->uti_thread_rank) {
			old->mod_clone = SPAWN_TO_REMOTE;
			kprintf("%s: mod_clone is set to %d\n", __FUNCTION__, old->mod_clone);
		} else {
			old->mod_clone = SPAWN_TO_LOCAL;
			kprintf("%s: mod_clone is set to %d\n", __FUNCTION__, old->mod_clone);
		}
	}

	if (clone_pthread_start_routine) {
		ihk_rwspinlock_read_lock_noirq(&old->vm->memory_range_lock);
		range = lookup_process_memory_range(old->vm,
				clone_pthread_start_routine,
				clone_pthread_start_routine + 1);
		ihk_rwspinlock_read_unlock_noirq(&old->vm->memory_range_lock);

		if (range && range->memobj && range->memobj->path) {
			if (!strstr(range->memobj->path, "omp.so") &&
					!strstr(range->memobj->path, "libfj90")) {
				helper_thread = 1;
			}
			dkprintf("clone(): %s thread from %s\n",
				helper_thread ? "helper" : "compute",
				range->memobj->path);
		}
	}

	if (helper_thread) {
		cpuid = ihk_mc_get_processor_id();
		//cpuid = obtain_clone_cpuid(&oldproc->cpu_set, 1);
	}
	else {
		cpuid = obtain_clone_cpuid(&oldproc->cpu_set,
				clone_use_last_cpu_result(old->mod_clone,
					oldproc->uti_use_last_cpu));
		if (cpuid == -1) {
			kprintf("do_fork,core not available\n");
			return -EAGAIN;
		}
	}

	new = clone_thread(old, curpc,
	                    newsp ? newsp : cursp, clone_flags);
	
	if (!new) {
		err =  -ENOMEM;
		goto release_cpuid;
	}

	if (clone_pthread_start_routine &&
		range && range->memobj && range->memobj->path) {

		sprintf(new->pthread_routine, "0x%lx @ %s",
			clone_pthread_start_routine,
			range->memobj->path);
	}
	else {
		sprintf(new->pthread_routine, "%s", "[unknown]");
	}

	newproc = new->proc;

	cpu_set(cpuid, &new->vm->address_space->cpu_set,
	        &new->vm->address_space->cpu_set_lock);

	if (clone_flags & CLONE_VM) {
		int *tids = NULL;
		int i;
		struct mcs_rwlock_node_irqsave lock;

		mcs_rwlock_writer_lock(&newproc->threads_lock, &lock);
		/* Obtain mcexec TIDs if not known yet */
		if (!newproc->nr_tids) {
			tids = kmalloc_tracked(sizeof(int) * NR_TIDS, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
			if (!tids) {
				mcs_rwlock_writer_unlock(&newproc->threads_lock, &lock);
				err =  -ENOMEM;
				goto destroy_thread;
			}

			newproc->tids = kmalloc_tracked(sizeof(struct mcexec_tid) *
						NR_TIDS, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
			if (!newproc->tids) {
				mcs_rwlock_writer_unlock(&newproc->threads_lock, &lock);
				kfree_tracked(tids, __FILE__, __LINE__);
				err =  -ENOMEM;
				goto destroy_thread;
			}
			tid_table_created = 1;

			if ((err = settid(new, NR_TIDS, tids)) < 0) {
				mcs_rwlock_writer_unlock(&newproc->threads_lock,
							&lock);
				kfree_tracked(tids, __FILE__, __LINE__);
				goto release_ids;
			}

			for (i = 0; (i < NR_TIDS) && tids[i]; ++i) {
				dkprintf("%s: tids[%d]: %d\n",
					 __func__, i, tids[i]);
				newproc->tids[i].tid = tids[i];
				newproc->tids[i].thread = NULL;
				++newproc->nr_tids;
			}

			kfree_tracked(tids, __FILE__, __LINE__);
		}

		/* Find an unused TID */
		new->tid = 0;
retry_tid:
		for (i = 0; i < newproc->nr_tids; ++i) {
			if (!newproc->tids[i].thread) {
				if (atomic_cmpxchg_ptr((void **)&newproc->tids[i].thread,
						       NULL, new) != NULL) {
					goto retry_tid;
				}
				new->tid = newproc->tids[i].tid;
				dkprintf("%s: tid %d assigned to %p\n", __FUNCTION__, new->tid, new);
				break;
			}
		}

		mcs_rwlock_writer_unlock(&newproc->threads_lock, &lock);

		/* TODO: spawn more mcexec threads */
		if (!new->tid) {
			kprintf("%s: no more TIDs available\n", __func__);
			for (i = 0; i < newproc->nr_tids; ++i) {
				kprintf("%s: i=%d,tid=%d,thread=%p\n",
					__func__, i, newproc->tids[i].tid,
					newproc->tids[i].thread);
			}
			err = -ENOMEM;
			goto release_ids;
		}
	}
	/* fork() a new process on the host */
	else {
		request1.number = __NR_clone;
		request1.args[0] = 0;
		request1.args[1] = new->vm->region.user_start;
		request1.args[2] = new->vm->region.user_end -
				   new->vm->region.user_start;
		request1.args[3] =
			       virt_to_phys(new->vm->address_space->page_table);
		request1.args[0] = clone_host_parent_flags_result(clone_flags,
				oldproc->ppid_parent->pid);
		newproc->pid = do_syscall(&request1, ihk_mc_get_processor_id());
		if (newproc->pid < 0) {
			kprintf("ERROR: forking host process\n");
			err = newproc->pid;
			goto destroy_thread;
		}

		/* In a single threaded process TID equals to PID */
		new->tid = newproc->pid;
		new->vm->address_space->pids[0] = new->proc->pid;

		dkprintf("fork(): new pid: %d\n", new->proc->pid);
		if(oldproc->monitoring_event &&
		   oldproc->monitoring_event->attr.inherit){
			newproc->monitoring_event = oldproc->monitoring_event;
		}
	}

	if (clone_parent_tid_store_needed_result(clone_flags)) {
		dkprintf("clone_flags & CLONE_PARENT_SETTID: 0x%lX\n",
		         parent_tidptr);

		err = setint_user((int *)parent_tidptr, new->tid);
		if (err) {
			goto release_ids;
		}
	}
	
	if (clone_child_cleartid_needed_result(clone_flags)) {
		dkprintf("clone_flags & CLONE_CHILD_CLEARTID: 0x%lX\n", 
			     child_tidptr);

		new->clear_child_tid = (int*)child_tidptr;
	}
	
	if (clone_child_tid_store_needed_result(clone_flags)) {
		unsigned long phys;
		dkprintf("clone_flags & CLONE_CHILD_SETTID: 0x%lX\n",
				child_tidptr);

		if (ihk_mc_pt_virt_to_phys(new->vm->address_space->page_table, 
					(void *)child_tidptr, &phys)) { 
			kprintf("ERROR: looking up physical addr for child process\n");
			err = -EFAULT;
			goto release_ids;
		}
	
		*((int*)phys_to_virt(phys)) = new->tid;
	}
	
	if (clone_tls_source_result(clone_flags) == CLONE_TLS_SOURCE_ARGUMENT) {
		dkprintf("clone_flags & CLONE_SETTLS: 0x%lX\n", 
			     tlsblock_base);

		new->tlsblock_base = tlsblock_base;
	}
	else { 
		new->tlsblock_base = old->tlsblock_base;
	}

	new->parent_cpuid = parent_cpuid;

	ihk_mc_syscall_set_ret(new->uctx, 0);

	new->status = PS_RUNNING;
	
	/* Only the first do_fork() call creates a thread on a Linux CPU */
	if (clone_remote_spawn_result(atomic_cmpxchg_int(&old->mod_clone,
					SPAWN_TO_REMOTE, SPAWN_TO_LOCAL))) {
		new->mod_clone = SPAWNING_TO_REMOTE;
		if (old->mod_clone_arg) {
			new->mod_clone_arg = kmalloc_tracked(sizeof(struct uti_attr), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
			if (!new->mod_clone_arg) {
				kprintf("%s: error: allocating mod_clone_arg\n",
					__func__);
				err = -ENOMEM;
				goto release_ids;
			}
			memcpy(new->mod_clone_arg, old->mod_clone_arg,
			       sizeof(struct uti_attr));
		}
	}
	chain_thread(new);
	if (!(clone_flags & CLONE_VM)) {
		newproc->status = PS_RUNNING;
		if(clone_flags & CLONE_PARENT){
			struct mcs_rwlock_node_irqsave lock;
			struct process *parent;
			struct mcs_rwlock_node parent_lock;

			mcs_rwlock_reader_lock(&oldproc->update_lock, &lock);
			parent = oldproc->ppid_parent;
			mcs_rwlock_reader_lock_noirq(&parent->update_lock, &parent_lock);
			if (clone_parent_use_pid1_result(parent->status)) {
				mcs_rwlock_reader_unlock_noirq(&parent->update_lock, &parent_lock);
				parent = get_this_cpu_local_var()->resource_set->pid1;
				mcs_rwlock_reader_lock_noirq(&parent->update_lock, &parent_lock);
			}
			newproc->parent = parent;
			newproc->ppid_parent = parent;
			newproc->nowait = 1;
			chain_process(newproc);
			mcs_rwlock_reader_unlock_noirq(&parent->update_lock, &parent_lock);
			mcs_rwlock_reader_unlock(&oldproc->update_lock, &lock);
		}
		else
			chain_process(newproc);
	}

	if (old->ptrace) {
		ptrace_event = ptrace_check_clone_event(old, clone_flags);
		if (ptrace_event) {
			ptrace_report_clone(old, new, ptrace_event);
		}
	}

	dkprintf("clone: kicking scheduler!,cpuid=%d pid=%d tid %d -> tid=%d\n",
		cpuid, newproc->pid,
		old->tid,
		new->tid);

	if (!(clone_flags & CLONE_VM)) {
		request1.number = __NR_clone;
		request1.args[0] = 1;
		request1.args[1] = new->tid;
		err = do_syscall(&request1, ihk_mc_get_processor_id());
		if (err) {
			goto free_mod_clone_arg;
		}
	}
	else if (clone_report_thread_result(clone_flags, termsig)) {
		struct mcs_rwlock_node_irqsave lock;

		mcs_rwlock_writer_lock(&oldproc->threads_lock, &lock);
		process_thread_report_attach_result(new,
			__builtin_offsetof(struct thread, termsig), 1,
			termsig,
			__builtin_offsetof(struct thread, report_proc),
			oldproc, &new->report_siblings_list,
			&oldproc->report_threads_list);
		mcs_rwlock_writer_unlock(&oldproc->threads_lock, &lock);
		hold_thread(new);
	}

	runq_add_thread(new, cpuid);

	if (ptrace_event) {
		schedule();
	}

	return new->tid;

free_mod_clone_arg:
	kfree_tracked(new->mod_clone_arg, __FILE__, __LINE__);
	new->mod_clone_arg = NULL;

	ihk_atomic_dec(&new->vm->refcount);

release_ids:
	if (clone_flags & CLONE_VM) {
		if (tid_table_created && !newproc->nr_tids) {
			kfree_tracked(newproc->tids, __FILE__, __LINE__);
			newproc->tids = NULL;
		}
	} else {
		request1.number = __NR_kill;
		request1.args[0] = newproc->pid;
		request1.args[1] = SIGKILL;
		do_syscall(&request1, ihk_mc_get_processor_id());
	}

destroy_thread:
	if (!(clone_flags & CLONE_VM)) {
		/* in case of fork, destroy struct process */
		ihk_atomic_set(&new->proc->refcount, 1);
		kfree_tracked(newproc->saved_cmdline, __FILE__, __LINE__);
		newproc->saved_cmdline = NULL;
	}
	ihk_atomic_set(&new->refcount, 1);
	release_thread(new);

release_cpuid:
	release_cpuid(cpuid);
	return err;
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_set_tid_address(int n, ihk_mc_user_context_t *ctx);
#else
long sys_set_tid_address(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_set_tid_address_body_result(get_this_cpu_local_var()->current,
			__builtin_offsetof(struct thread, clear_child_tid),
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, pid),
			(int *)ihk_mc_syscall_arg0(ctx));
}
#endif

void
syscall_tsc_to_ts_bridge(unsigned long tsc, void *ts)
{
	tsc_to_ts(tsc, ts);
}

unsigned long
syscall_timespec_to_jiffy_bridge(const void *ts)
{
	return timespec_to_jiffy((const struct timespec *)ts);
}

void
syscall_ts_add_bridge(void *dst, const void *src)
{
	ts_add(dst, (struct timespec *)src);
}

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
static const struct syscall_times_offsets syscall_times_offsets = {
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.thread_user_tsc_offset = __builtin_offsetof(struct thread, user_tsc),
	.thread_system_tsc_offset = __builtin_offsetof(struct thread, system_tsc),
	.proc_utime_offset = __builtin_offsetof(struct process, utime),
	.proc_stime_offset = __builtin_offsetof(struct process, stime),
	.proc_utime_children_offset =
		__builtin_offsetof(struct process, utime_children),
	.proc_stime_children_offset =
		__builtin_offsetof(struct process, stime_children),
};
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_times(int n, ihk_mc_user_context_t *ctx);
#else
long sys_times(int n, ihk_mc_user_context_t *ctx)
{
	struct tms *buf = (struct tms *)ihk_mc_syscall_arg0(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return syscall_times_body_result(thread, (unsigned long)buf,
			gettime_local_support, &syscall_times_offsets,
			syscall_tsc_to_ts_bridge, syscall_timespec_to_jiffy_bridge,
			syscall_ts_add_bridge, syscall_gettime_bridge,
			syscall_copy_to_user_bridge);
}
#endif

long
syscall_do_kill_thread_bridge(void *thread, int pid, int tid, int sig,
		const void *info, int ptracecont)
{
	return do_kill((struct thread *)thread, pid, tid, sig,
			(struct siginfo *)info, ptracecont);
}

void
syscall_kill_log_bridge(int event, int pid, int sig, int error)
{
	if (event == 1) {
		dkprintf("sys_kill,enter,pid=%d,sig=%d\n", pid, sig);
	} else {
		dkprintf("sys_kill,returning,pid=%d,sig=%d,error=%d\n",
				pid, sig, error);
	}
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_kill(int n, ihk_mc_user_context_t *ctx);
#else
long sys_kill(int n, ihk_mc_user_context_t *ctx)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	int sig = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	int error;

	dkprintf("sys_kill,enter,pid=%d,sig=%d\n", pid, sig);
	error = syscall_kill_body_result(thread,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, pid), pid, sig,
			syscall_do_kill_thread_bridge);
	dkprintf("sys_kill,returning,pid=%d,sig=%d,error=%d\n", pid, sig, error);
	return error;
}
#endif

#if defined(MCKERNEL_SYSCALL_POLICY_HELPERS_TEST_EXPORT)
#define SYSCALL_POLICY_HELPER_SCOPE
#else
#define SYSCALL_POLICY_HELPER_SCOPE static
#endif

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
SYSCALL_POLICY_HELPER_SCOPE int
robust_list_len_result(size_t len)
{
	return len == 24 ? 0 : -EINVAL;
}

SYSCALL_POLICY_HELPER_SCOPE long
set_robust_list_body_result(size_t len)
{
	return robust_list_len_result(len);
}

SYSCALL_POLICY_HELPER_SCOPE int
tkill_tid_result(int tid)
{
	return tid <= 0 ? -EINVAL : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
tgkill_target_result(int tgid, int tid)
{
	return (tgid <= 0 || tid <= 0) ? -EINVAL : 0;
}

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

SYSCALL_POLICY_HELPER_SCOPE int
rt_sigprocmask_validate(size_t sigsetsize, size_t expected_sigset_size,
		int has_set, int how)
{
	if (sigsetsize != expected_sigset_size) {
		return -EINVAL;
	}

	if (has_set &&
			how != SIG_BLOCK &&
			how != SIG_UNBLOCK &&
			how != SIG_SETMASK) {
		return -EINVAL;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
rt_sigprocmask_apply(unsigned long current_mask, unsigned long set_mask,
		int has_set, int how)
{
	unsigned long mask = current_mask;

	if (has_set) {
		switch (how) {
		case SIG_BLOCK:
			mask |= set_mask;
			break;
		case SIG_UNBLOCK:
			mask &= ~set_mask;
			break;
		case SIG_SETMASK:
			mask = set_mask;
			break;
		}
	}

	mask &= ~__sigmask(SIGKILL);
	mask &= ~__sigmask(SIGSTOP);
	return mask;
}

SYSCALL_POLICY_HELPER_SCOPE long
rt_sigprocmask_body_result(int how, unsigned long set_addr,
		unsigned long oldset_addr, size_t sigsetsize,
		size_t expected_sigset_size, void *thread,
		size_t sigmask_offset, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_forward_sigmask_fn_t forward_fn)
{
	unsigned long *sigmaskp;
	unsigned long wsig = 0;
	int has_set = set_addr != 0;
	int error;

	error = rt_sigprocmask_validate(sigsetsize, expected_sigset_size,
			has_set, how);
	if (error) {
		return error;
	}

	sigmaskp = (unsigned long *)((char *)thread + sigmask_offset);
	if (oldset_addr) {
		wsig = *sigmaskp;
		if (!copy_to_fn ||
		    copy_to_fn(oldset_addr, &wsig, sizeof(wsig))) {
			return -EFAULT;
		}
	}
	if (set_addr) {
		if (!copy_from_fn ||
		    copy_from_fn(&wsig, set_addr, sizeof(wsig))) {
			return -EFAULT;
		}
	}

	*sigmaskp = rt_sigprocmask_apply(*sigmaskp, wsig, has_set, how);
	if (forward_fn) {
		forward_fn(*sigmaskp);
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
rt_sigpending_size_result(size_t sigsetsize, size_t expected_sigset_size)
{
	return sigsetsize > expected_sigset_size ? -EINVAL : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
signalfd4_sigsetsize_result(size_t sigsetsize, size_t expected_sigset_size)
{
	return sigsetsize != expected_sigset_size ? -EINVAL : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
signalfd4_flags_result(int flags)
{
	return (flags & ~(SFD_NONBLOCK | SFD_CLOEXEC)) ? -EINVAL : 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
signalfd_body_result(void)
{
	return -EOPNOTSUPP;
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_temp_sigmask_body_result(unsigned long set_addr, void *thread,
		size_t sigmask_offset, int syscall_nr, void *ctx,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_forward_context_fn_t forward_fn)
{
	unsigned long *sigmaskp;
	unsigned long oldset;
	unsigned long wset = 0;
	long rc;

	if (!thread || !forward_fn)
		return -EINVAL;

	sigmaskp = (unsigned long *)((char *)thread + sigmask_offset);
	oldset = *sigmaskp;
	if (set_addr) {
		if (!copy_from_fn ||
		    copy_from_fn(&wset, set_addr, sizeof(wset)))
			return -EFAULT;
		*sigmaskp = wset;
	}

	rc = forward_fn(syscall_nr, ctx);
	*sigmaskp = oldset;
	return rc;
}

SYSCALL_POLICY_HELPER_SCOPE long
pselect6_sigmask_body_result(unsigned long set_ptr_addr, void *thread,
		size_t sigmask_offset, int syscall_nr, void *ctx,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_forward_context_fn_t forward_fn)
{
	unsigned long set_addr = 0;

	if (set_ptr_addr) {
		if (!copy_from_fn ||
		    copy_from_fn(&set_addr, set_ptr_addr, sizeof(set_addr)))
			return -EFAULT;
	}

	return syscall_temp_sigmask_body_result(set_addr, thread,
			sigmask_offset, syscall_nr, ctx, copy_from_fn,
			forward_fn);
}

SYSCALL_POLICY_HELPER_SCOPE long
rt_sigpending_body_result(unsigned long set_addr, size_t sigsetsize,
		size_t expected_sigset_size, void *thread,
		syscall_pending_mask_fn_t pending_mask_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	unsigned long pending;
	int error;

	error = rt_sigpending_size_result(sigsetsize, expected_sigset_size);
	if (error)
		return error;
	if (!set_addr || !thread || !pending_mask_fn || !copy_to_fn)
		return -EFAULT;

	pending = pending_mask_fn(thread);
	return copy_to_fn(set_addr, &pending, sizeof(pending)) ? -EFAULT : 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
signalfd4_body_result(int fd, unsigned long mask_addr, size_t sigsetsize,
		size_t expected_sigset_size, int flags, void *thread,
		int syscall_nr, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_signalfd_create_fn_t create_fn,
		syscall_signalfd_publish_fn_t publish_fn)
{
	unsigned long mask = 0;
	long newfd;
	int error;
	int create = 0;

	error = signalfd4_sigsetsize_result(sigsetsize, expected_sigset_size);
	if (error)
		return error;
	if (!mask_addr || !copy_from_fn ||
	    copy_from_fn(&mask, mask_addr, sizeof(mask)))
		return -EFAULT;
	error = signalfd4_flags_result(flags);
	if (error)
		return error;
	if (!thread || !publish_fn)
		return -EINVAL;

	if (fd == -1) {
		if (!create_fn)
			return -EINVAL;
		newfd = create_fn(syscall_nr, flags);
		if (newfd < 0)
			return newfd;
		fd = (int)newfd;
		create = 1;
	}

	return publish_fn(thread, fd, &mask, create);
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_refresh_cred_needed_result(long rc)
{
	return rc == 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_getpid_result(int pid)
{
	return pid;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_getppid_result(int ppid)
{
	return ppid;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_gettid_result(int tid)
{
	return tid;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_set_tid_address_return_result(int pid)
{
	return pid;
}

static inline void *syscall_offset_ptr(void *base, size_t offset)
{
	return (char *)base + offset;
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_getpid_body_result(void *thread, size_t proc_offset,
		size_t pid_offset)
{
	void *proc = *(void **)syscall_offset_ptr(thread, proc_offset);

	return *(int *)syscall_offset_ptr(proc, pid_offset);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_getppid_body_result(void *thread, size_t proc_offset,
		size_t ppid_parent_offset, size_t pid_offset)
{
	void *proc = *(void **)syscall_offset_ptr(thread, proc_offset);
	void *parent = *(void **)syscall_offset_ptr(proc, ppid_parent_offset);

	return *(int *)syscall_offset_ptr(parent, pid_offset);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_gettid_body_result(void *thread, size_t tid_offset)
{
	return *(int *)syscall_offset_ptr(thread, tid_offset);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_set_tid_address_body_result(void *thread,
		size_t clear_child_tid_offset, size_t proc_offset,
		size_t pid_offset, int *clear_child_tid)
{
	*(int **)syscall_offset_ptr(thread, clear_child_tid_offset) =
		clear_child_tid;

	return syscall_getpid_body_result(thread, proc_offset, pid_offset);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_get_process_id_field_result(void *thread, size_t proc_offset,
		size_t field_offset)
{
	void *proc = *(void **)syscall_offset_ptr(thread, proc_offset);

	return *(int *)syscall_offset_ptr(proc, field_offset);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_getresid_body_result(void *thread, size_t proc_offset,
		size_t first_offset, size_t second_offset,
		size_t third_offset, unsigned long first_user_addr,
		unsigned long second_user_addr, unsigned long third_user_addr,
		syscall_copy_int_to_user_fn_t copy_int_fn)
{
	void *proc = *(void **)syscall_offset_ptr(thread, proc_offset);

	if (copy_int_fn(first_user_addr,
			(int *)syscall_offset_ptr(proc, first_offset))) {
		return -EFAULT;
	}
	if (copy_int_fn(second_user_addr,
			(int *)syscall_offset_ptr(proc, second_offset))) {
		return -EFAULT;
	}
	if (copy_int_fn(third_user_addr,
			(int *)syscall_offset_ptr(proc, third_offset))) {
		return -EFAULT;
	}

	return 0;
}

static int
syscall_thread_process_pid(void *thread, size_t proc_offset, size_t pid_offset)
{
	void *proc = *(void **)syscall_offset_ptr(thread, proc_offset);

	return *(int *)syscall_offset_ptr(proc, pid_offset);
}

static void
syscall_make_kill_siginfo(struct siginfo *info, int sig, int code, int pid)
{
	memset(info, '\0', sizeof(*info));
	info->si_signo = sig;
	info->si_code = code;
	info->_sifields._kill.si_pid = pid;
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_kill_body_result(void *thread, size_t proc_offset, size_t pid_offset,
		int pid, int sig, syscall_do_kill_thread_fn_t do_kill_fn)
{
	struct siginfo info;

	if (!do_kill_fn)
		return -EINVAL;
	syscall_make_kill_siginfo(&info, sig, SI_USER,
			syscall_thread_process_pid(thread, proc_offset,
				pid_offset));
	return do_kill_fn(thread, pid, -1, sig, &info, 0);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_tgkill_body_result(void *thread, size_t proc_offset, size_t pid_offset,
		int tgid, int tid, int sig,
		syscall_do_kill_thread_fn_t do_kill_fn)
{
	struct siginfo info;
	int error;

	error = tgkill_target_result(tgid, tid);
	if (error)
		return error;
	if (!do_kill_fn)
		return -EINVAL;
	syscall_make_kill_siginfo(&info, sig, SI_TKILL,
			syscall_thread_process_pid(thread, proc_offset,
				pid_offset));
	return do_kill_fn(thread, tgid, tid, sig, &info, 0);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_tkill_body_result(void *thread, size_t proc_offset, size_t pid_offset,
		int tid, int sig, syscall_do_kill_thread_fn_t do_kill_fn)
{
	struct siginfo info;
	int error;

	error = tkill_tid_result(tid);
	if (error)
		return error;
	if (!do_kill_fn)
		return -EINVAL;
	syscall_make_kill_siginfo(&info, sig, SI_TKILL,
			syscall_thread_process_pid(thread, proc_offset,
				pid_offset));
	return do_kill_fn(thread, -1, tid, sig, &info, 0);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_forward_refresh_cred_body_result(int syscall_nr, void *ctx,
		syscall_forward_context_fn_t forward_fn,
		syscall_refresh_cred_fn_t refresh_fn)
{
	long rc;

	if (!forward_fn)
		return -EINVAL;
	rc = forward_fn(syscall_nr, ctx);
	if (syscall_refresh_cred_needed_result(rc)) {
		if (!refresh_fn)
			return -EINVAL;
		refresh_fn();
	}
	return rc;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
syscall_setfsid_body_result(int id, int syscall_nr,
		syscall_do_syscall2_fn_t do_syscall_fn,
		syscall_refresh_cred_fn_t refresh_fn)
{
	unsigned long new_id;

	if (!do_syscall_fn)
		return -EINVAL;
	new_id = do_syscall_fn(syscall_nr, id, 0);
	if (!refresh_fn)
		return -EINVAL;
	refresh_fn();
	return new_id;
}

SYSCALL_POLICY_HELPER_SCOPE int *
getcred_body_result(int *raw_buf, unsigned long page_mask, int syscall_nr,
		syscall_virt_to_phys_fn_t virt_to_phys_fn,
		syscall_get_cpu_fn_t processor_id_fn,
		syscall_request_call_fn_t do_syscall_fn)
{
	struct syscall_request request = { 0 };
	int *buf;

	if (!raw_buf || !virt_to_phys_fn || !processor_id_fn || !do_syscall_fn) {
		return NULL;
	}

	if ((((unsigned long)raw_buf) ^ ((unsigned long)(raw_buf + 8))) &
			page_mask) {
		buf = raw_buf + 8;
	} else {
		buf = raw_buf;
	}

	request.number = syscall_nr;
	request.args[0] = virt_to_phys_fn(buf);
	request.args[1] = 1;
	do_syscall_fn(&request, processor_id_fn());
	return buf;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_refresh_cred_fields_body_result(void *thread, int *scratch,
		size_t thread_proc_offset, size_t field0_offset,
		size_t field1_offset, size_t field2_offset,
		size_t field3_offset, size_t value0_index,
		size_t value1_index, size_t value2_index,
		size_t value3_index, syscall_getcred_fn_t getcred_fn)
{
	char *proc_bytes;
	int *buf;
	void *proc;

	if (!thread || !scratch) {
		return -EFAULT;
	}
	if (!getcred_fn) {
		return -EINVAL;
	}

	buf = getcred_fn(scratch);
	if (!buf) {
		return -EFAULT;
	}
	proc = *(void **)((char *)thread + thread_proc_offset);
	if (!proc) {
		return -EFAULT;
	}

	proc_bytes = proc;
	*(int *)(proc_bytes + field0_offset) = buf[value0_index];
	*(int *)(proc_bytes + field1_offset) = buf[value1_index];
	*(int *)(proc_bytes + field2_offset) = buf[value2_index];
	*(int *)(proc_bytes + field3_offset) = buf[value3_index];
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_times_body_result(void *thread, unsigned long buf_addr,
		int local_support, const struct syscall_times_offsets *offsets,
		syscall_tsc_to_ts_fn_t tsc_to_ts_fn,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_ts_add_fn_t ts_add_fn, syscall_gettime_fn_t gettime_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	struct syscall_times_tms mytms;
	struct timespec ats;
	void *proc;

	if (!offsets || !tsc_to_ts_fn || !timespec_to_jiffy_fn ||
			!ts_add_fn || !copy_to_fn) {
		return -EINVAL;
	}

	proc = *(void **)syscall_offset_ptr(thread, offsets->thread_proc_offset);
	tsc_to_ts_fn(*(unsigned long *)syscall_offset_ptr(thread,
			offsets->thread_user_tsc_offset), &ats);
	mytms.tms_utime = timespec_to_jiffy_fn(&ats);
	tsc_to_ts_fn(*(unsigned long *)syscall_offset_ptr(thread,
			offsets->thread_system_tsc_offset), &ats);
	mytms.tms_stime = timespec_to_jiffy_fn(&ats);

	ats = *(struct timespec *)syscall_offset_ptr(proc,
			offsets->proc_utime_offset);
	ts_add_fn(&ats, syscall_offset_ptr(proc,
			offsets->proc_utime_children_offset));
	mytms.tms_cutime = timespec_to_jiffy_fn(&ats);
	ats = *(struct timespec *)syscall_offset_ptr(proc,
			offsets->proc_stime_offset);
	ts_add_fn(&ats, syscall_offset_ptr(proc,
			offsets->proc_stime_children_offset));
	mytms.tms_cstime = timespec_to_jiffy_fn(&ats);

	if (copy_to_fn(buf_addr, &mytms, sizeof(mytms))) {
		return -EFAULT;
	}

	if (local_support) {
		if (!gettime_fn) {
			return -EINVAL;
		}
		gettime_fn(&ats);
	}
	else {
		ats.tv_sec = 0;
		ats.tv_nsec = 0;
	}

	return timespec_to_jiffy_fn(&ats);
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_use_requester_tid_result(int syscall_nr, unsigned long arg0,
		int sched_setaffinity_nr)
{
	return syscall_nr == sched_setaffinity_nr && arg0 == 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_target_tid_result(int use_requester_tid, int current_tid)
{
	return use_requester_tid ? current_tid : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_send_prepare_result(struct syscall_request *req,
		struct syscall_response *res)
{
	if (!req || !res)
		return -EINVAL;

	res->status = 0;
	req->valid = 0;

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_request_copy_result(struct syscall_request *dst,
		const struct syscall_request *src)
{
	if (!dst || !src)
		return -EINVAL;

	memcpy(dst, src, sizeof(*dst));

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_request_publish_result(struct syscall_request *req)
{
	if (!req)
		return -EINVAL;

	__atomic_store_n(&req->valid, 1, __ATOMIC_RELEASE);

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_generic_forwarding_body_result(struct syscall_request *req, int n,
		unsigned long arg0, unsigned long arg1, unsigned long arg2,
		unsigned long arg3, unsigned long arg4, unsigned long arg5,
		int cpu, syscall_request_call_fn_t do_syscall_fn)
{
	if (!req || !do_syscall_fn)
		return -EINVAL;

	req->number = n;
	req->args[0] = arg0;
	req->args[1] = arg1;
	req->args[2] = arg2;
	req->args[3] = arg3;
	req->args[4] = arg4;
	req->args[5] = arg5;

	return do_syscall_fn(req, cpu);
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_packet_traditional_prepare_result(struct ikc_scd_packet *packet,
		int msg, int cpu_ref, int pid, unsigned long resp_pa)
{
	if (!packet)
		return -EINVAL;

	packet->msg = msg;
	packet->ref = cpu_ref;
	packet->pid = pid;
	packet->resp_pa = resp_pa;

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_eventfd_packet_prepare_result(struct ikc_scd_packet *packet, int msg,
		int eventfd_type)
{
	if (!packet)
		return -EINVAL;

	memset(packet, 0, sizeof(*packet));
	packet->msg = msg;
	packet->eventfd_type = eventfd_type;

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_eventfd_send_result(void *channel, int msg, int eventfd_type,
		syscall_ikc_send_fn_t send_fn)
{
	struct ikc_scd_packet packet;
	int prep_rc;

	if (!send_fn)
		return -EINVAL;

	prep_rc = syscall_eventfd_packet_prepare_result(&packet, msg,
			eventfd_type);
	if (prep_rc)
		return prep_rc;

	return send_fn(channel, &packet, 0);
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_log_budget_result(int pid, int *last_pidp, int *log_countp,
		int limit)
{
	int log_count;

	if (!last_pidp || !log_countp)
		return -EINVAL;

	log_count = *log_countp;
	if (*last_pidp != pid) {
		*last_pidp = pid;
		*log_countp = 0;
		log_count = 0;
	}

	if (limit > 0 && log_count < limit) {
		*log_countp = log_count + 1;
		return 1;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_reject_after_exit_result(int process_status, int syscall_nr,
		int exit_nr, int exit_group_nr)
{
	return process_status == PS_EXITED && syscall_nr != exit_nr &&
	       syscall_nr != exit_group_nr;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_offload_spin_without_schedule_result(int no_preempt, int tid)
{
	return no_preempt || !tid;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_offload_prepare_result(struct syscall_request *req,
		struct syscall_response *res, int current_tid, int syscall_nr,
		unsigned long arg0, int sched_setaffinity_nr,
		unsigned long spinning_status)
{
	int use_requester_tid;

	if (!req || !res)
		return -EINVAL;

	use_requester_tid = syscall_use_requester_tid_result(syscall_nr, arg0,
			sched_setaffinity_nr);
	req->rtid = current_tid;
	req->ttid = syscall_target_tid_result(use_requester_tid, current_tid);
	res->req_thread_status = spinning_status;
	res->pde_data = NULL;

	return use_requester_tid;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_preempt_disable_needed_result(int rtid)
{
	return rtid == -1;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_proxy_dead_result(long rc)
{
	return rc == -ERESTARTSYS;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_tofu_post_reply_candidate_result(int syscall_nr, long rc,
		int ioctl_nr, int openat_nr)
{
	return (syscall_nr == ioctl_nr && rc == 0) ||
	       (syscall_nr == openat_nr && rc > 0);
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_profile_event_needed_result(int syscall_nr, int profile_max)
{
	return syscall_nr < profile_max;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_offload_counted_result(int syscall_nr, int exit_group_nr)
{
	return syscall_nr != exit_group_nr;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_nested_dispatch_valid_result(int syscall_nr, int syscall_count,
		int has_handler)
{
	return syscall_nr >= 0 && syscall_nr < syscall_count && has_handler;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_nested_rt_sigaction_index_result(int sig, int nsig)
{
	int index = sig - 1;

	if (index < 0 || index >= nsig)
		return -EINVAL;

	return index;
}

SYSCALL_POLICY_HELPER_SCOPE int
syscall_nested_response_prepare_result(struct syscall_request *req,
		struct syscall_response *res, unsigned long response_nr,
		unsigned long syscall_ret, int current_tid, int service_tid,
		unsigned long spinning_status)
{
	if (!req || !res)
		return -EINVAL;

	req->number = response_nr;
	req->args[1] = syscall_ret;
	req->rtid = current_tid;
	req->ttid = service_tid;
	res->req_thread_status = spinning_status;

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
setpgid_normalize_pid(int current_pid, int pid)
{
	return pid == 0 ? current_pid : pid;
}

SYSCALL_POLICY_HELPER_SCOPE int
setpgid_normalize_pgid(int pid, int pgid)
{
	return pgid == 0 ? pid : pgid;
}

SYSCALL_POLICY_HELPER_SCOPE int
setpgid_execed_result(int execed)
{
	return execed ? -EACCES : 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_setpgid_body_result(void *thread, int pid, int pgid, int syscall_nr,
		void *ctx, const struct syscall_setpgid_offsets *offsets,
		void *lock_arg, syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn)
{
	void *proc;
	int current_pid;
	long rc;

	if (!offsets || !find_fn || !unlock_fn) {
		return -EINVAL;
	}

	proc = *(void **)syscall_offset_ptr(thread, offsets->thread_proc_offset);
	current_pid = *(int *)syscall_offset_ptr(proc, offsets->proc_pid_offset);
	pid = setpgid_normalize_pid(current_pid, pid);
	pgid = setpgid_normalize_pgid(pid, pgid);

	if (current_pid != pid) {
		proc = find_fn(pid, lock_arg);
		if (proc) {
			rc = setpgid_execed_result(*(int *)syscall_offset_ptr(
					proc, offsets->proc_execed_offset));
			if (rc) {
				unlock_fn(proc, lock_arg);
				return rc;
			}
			unlock_fn(proc, lock_arg);
		}
		else {
			return -ESRCH;
		}
	}

	if (!forward_fn) {
		return -EINVAL;
	}
	rc = forward_fn(syscall_nr, ctx);
	if (rc == 0) {
		proc = find_fn(pid, lock_arg);
		if (proc) {
			*(int *)syscall_offset_ptr(proc,
					offsets->proc_pgid_offset) = pgid;
			unlock_fn(proc, lock_arg);
		}
	}
	return rc;
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_setrlimit_body_result(int resource, unsigned long new_limit_addr,
		syscall_do_prlimit64_fn_t do_prlimit_fn)
{
	if (!do_prlimit_fn) {
		return -EINVAL;
	}

	return do_prlimit_fn(0, resource, new_limit_addr, 0);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_getrlimit_body_result(int resource, unsigned long old_limit_addr,
		syscall_do_prlimit64_fn_t do_prlimit_fn)
{
	if (!do_prlimit_fn) {
		return -EINVAL;
	}

	return do_prlimit_fn(0, resource, 0, old_limit_addr);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_prlimit64_body_result(int pid, int resource,
		unsigned long new_limit_addr, unsigned long old_limit_addr,
		syscall_do_prlimit64_fn_t do_prlimit_fn)
{
	if (!do_prlimit_fn) {
		return -EINVAL;
	}

	return do_prlimit_fn(pid, resource, new_limit_addr, old_limit_addr);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_sysinfo_body_result(unsigned long sysinfo_addr,
		unsigned long totalram, unsigned long freeram,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	struct sysinfo info;

	if (!copy_to_fn) {
		return -EINVAL;
	}

	memset(&info, '\0', sizeof(info));
	info.totalram = totalram;
	info.freeram = freeram;
	info.mem_unit = 1;
	if (copy_to_fn(sysinfo_addr, &info, sizeof(info))) {
		return -EFAULT;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_get_cpu_id_body_result(syscall_get_cpu_fn_t get_cpu_fn)
{
	if (!get_cpu_fn) {
		return -EINVAL;
	}

	return get_cpu_fn();
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_mlockall_body_result(void *thread, int flags,
		const struct syscall_mlockall_offsets *offsets,
		syscall_log_int_fn_t log_fn)
{
	void *proc;
	unsigned long memlock_cur;
	int is_privileged;
	int rc;

	if (!offsets || offsets->memlock_resource < 0) {
		return -EINVAL;
	}

	proc = *(void **)syscall_offset_ptr(thread, offsets->thread_proc_offset);
	is_privileged = *(int *)syscall_offset_ptr(proc,
			offsets->proc_euid_offset) == 0;
	memlock_cur = *(unsigned long *)syscall_offset_ptr(proc,
			offsets->proc_rlimit_offset +
			(size_t)offsets->memlock_resource *
			offsets->rlimit_entry_size);
	rc = mlockall_policy_result(flags, is_privileged, memlock_cur);
	if (log_fn) {
		log_fn(flags, rc);
	}

	return rc;
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_munlockall_body_result(syscall_log_int_fn_t log_fn)
{
	if (log_fn) {
		log_fn(0, 0);
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_getcpu_body_result(unsigned long cpup_addr, unsigned long nodep_addr,
		int cpu, int node, syscall_copy_to_user_fn_t copy_to_fn)
{
	long error;

	if (!copy_to_fn) {
		return -EINVAL;
	}

	if (cpup_addr) {
		error = copy_to_fn(cpup_addr, &cpu, sizeof(cpu));
		if (error) {
			return error;
		}
	}

	if (nodep_addr) {
		error = copy_to_fn(nodep_addr, &node, sizeof(node));
		if (error) {
			return error;
		}
	}

	return 0;
}

static inline struct mckfd **
syscall_mckfd_headp(void *proc, const struct syscall_mckfd_offsets *offsets)
{
	return (struct mckfd **)((char *)proc + offsets->proc_mckfd_offset);
}

static struct mckfd *
syscall_mckfd_find_unlocked(void *proc, int fd,
		const struct syscall_mckfd_offsets *offsets)
{
	struct mckfd *fdp;

	for (fdp = *syscall_mckfd_headp(proc, offsets); fdp;
			fdp = *(struct mckfd **)((char *)fdp +
				offsets->mckfd_next_offset)) {
		if (*(int *)((char *)fdp + offsets->mckfd_fd_offset) == fd) {
			break;
		}
	}

	return fdp;
}

static struct mckfd *
syscall_mckfd_find_locked(void *thread, int fd,
		const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn)
{
	void *proc;
	void *lock;
	struct mckfd *fdp;
	long irqstate;

	if (!thread || !offsets || !lock_fn || !unlock_fn) {
		return NULL;
	}

	proc = *(void **)syscall_offset_ptr(thread, offsets->thread_proc_offset);
	lock = syscall_offset_ptr(proc, offsets->proc_mckfd_lock_offset);
	irqstate = lock_fn(lock);
	fdp = syscall_mckfd_find_unlocked(proc, fd, offsets);
	unlock_fn(lock, irqstate);

	return fdp;
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_read_body_result(void *thread, int fd, int syscall_nr, void *ctx,
		const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn)
{
	struct mckfd *fdp;
	syscall_mckfd_long_fn_t read_fn;

	if (!offsets || !lock_fn || !unlock_fn || !forward_fn) {
		return -EINVAL;
	}

	fdp = syscall_mckfd_find_locked(thread, fd, offsets, lock_fn, unlock_fn);
	if (fdp) {
		read_fn = *(syscall_mckfd_long_fn_t *)((char *)fdp +
				offsets->mckfd_read_cb_offset);
		if (read_fn) {
			return read_fn(fdp, ctx);
		}
	}

	return forward_fn(syscall_nr, ctx);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_ioctl_body_result(void *thread, int fd, unsigned long cmd,
		unsigned long arg, int syscall_nr, void *ctx,
		const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn,
		syscall_tofu_ioctl_fn_t tofu_fn)
{
	struct mckfd *fdp;
	syscall_mckfd_int_fn_t ioctl_fn;
	int handled = 0;
	long rc;

	if (!offsets || !lock_fn || !unlock_fn || !forward_fn) {
		return -EINVAL;
	}

	fdp = syscall_mckfd_find_locked(thread, fd, offsets, lock_fn, unlock_fn);
	if (tofu_fn) {
		rc = tofu_fn(thread, fd, cmd, arg, &handled);
		if (handled) {
			return rc;
		}
	}
	if (fdp) {
		ioctl_fn = *(syscall_mckfd_int_fn_t *)((char *)fdp +
				offsets->mckfd_ioctl_cb_offset);
		if (ioctl_fn) {
			return ioctl_fn(fdp, ctx);
		}
	}

	return forward_fn(syscall_nr, ctx);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_fcntl_body_result(void *thread, int fd, int syscall_nr, void *ctx,
		const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn)
{
	struct mckfd *fdp;
	syscall_mckfd_int_fn_t fcntl_fn;

	if (!offsets || !lock_fn || !unlock_fn || !forward_fn) {
		return -EINVAL;
	}

	fdp = syscall_mckfd_find_locked(thread, fd, offsets, lock_fn, unlock_fn);
	if (fdp) {
		fcntl_fn = *(syscall_mckfd_int_fn_t *)((char *)fdp +
				offsets->mckfd_fcntl_cb_offset);
		if (fcntl_fn) {
			return fcntl_fn(fdp, ctx);
		}
	}

	return forward_fn(syscall_nr, ctx);
}

SYSCALL_POLICY_HELPER_SCOPE long
syscall_close_body_result(void *thread, int fd, int syscall_nr, void *ctx,
		const struct syscall_mckfd_offsets *offsets,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_forward_context_fn_t forward_fn,
		syscall_tofu_close_fn_t close_path_fn,
		syscall_mckfd_free_fn_t free_fn)
{
	void *proc;
	void *lock;
	struct mckfd **headp;
	struct mckfd *fdp;
	struct mckfd *fdq = NULL;
	struct mckfd *next;
	syscall_mckfd_int_fn_t close_fn;
	long irqstate;

	if (!thread || !offsets || !lock_fn || !unlock_fn || !forward_fn) {
		return -EINVAL;
	}

	proc = *(void **)syscall_offset_ptr(thread, offsets->thread_proc_offset);
	lock = syscall_offset_ptr(proc, offsets->proc_mckfd_lock_offset);
	irqstate = lock_fn(lock);
	if (close_path_fn) {
		close_path_fn(thread, fd);
	}

	headp = syscall_mckfd_headp(proc, offsets);
	for (fdp = *headp; fdp; fdq = fdp,
			fdp = *(struct mckfd **)((char *)fdp +
				offsets->mckfd_next_offset)) {
		if (*(int *)((char *)fdp + offsets->mckfd_fd_offset) == fd) {
			break;
		}
	}

	if (!fdp) {
		unlock_fn(lock, irqstate);
		return forward_fn(syscall_nr, ctx);
	}

	next = *(struct mckfd **)((char *)fdp + offsets->mckfd_next_offset);
	if (fdq) {
		*(struct mckfd **)((char *)fdq + offsets->mckfd_next_offset) =
			next;
	}
	else {
		*headp = next;
	}
	*(struct mckfd **)((char *)fdp + offsets->mckfd_next_offset) = NULL;
	unlock_fn(lock, irqstate);

	close_fn = *(syscall_mckfd_int_fn_t *)((char *)fdp +
			offsets->mckfd_close_cb_offset);
	if (close_fn) {
		close_fn(fdp, ctx);
	}
	if (free_fn) {
		free_fn(fdp);
	}

	return forward_fn(syscall_nr, ctx);
}

SYSCALL_POLICY_HELPER_SCOPE long
do_mmap_mckfd_dispatch_body_result(void *thread, int flags, int fd, void *ctx,
		int *handledp, const struct syscall_mckfd_offsets *offsets,
		size_t mckfd_mmap_cb_offset,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn)
{
	struct mckfd *fdp;
	syscall_mckfd_long_fn_t mmap_fn;

	if (handledp) {
		*handledp = 0;
	}
	if (flags & MAP_ANONYMOUS) {
		return 0;
	}
	if (!handledp || !offsets || !lock_fn || !unlock_fn) {
		if (handledp) {
			*handledp = 1;
		}
		return -EINVAL;
	}

	fdp = syscall_mckfd_find_locked(thread, fd, offsets, lock_fn, unlock_fn);
	if (!fdp) {
		return 0;
	}

	*handledp = 1;
	mmap_fn = *(syscall_mckfd_long_fn_t *)((char *)fdp +
			mckfd_mmap_cb_offset);
	if (mmap_fn) {
		return mmap_fn(fdp, ctx);
	}

	return -EBADF;
}

SYSCALL_POLICY_HELPER_SCOPE int
do_mmap_page_size_body_result(int flags, unsigned long vrf0, int thp_disable,
		size_t len, int *pgshiftp, int *p2alignp,
		arch_mmap_default_huge_shift_fn_t default_huge_shift_fn,
		do_mmap_smaller_page_fn_t smaller_page_fn)
{
	if (!pgshiftp || !p2alignp) {
		return -EINVAL;
	}

	if (flags & MAP_HUGETLB) {
		int pgshift = (flags >> MAP_HUGE_SHIFT) & 0x3F;

		if (!pgshift) {
			if (!default_huge_shift_fn) {
				return -EINVAL;
			}
			pgshift = default_huge_shift_fn();
		}
		*pgshiftp = pgshift;
		*p2alignp = pgshift - PAGE_SHIFT;
		return 0;
	}

	if ((((flags & (MAP_PRIVATE | MAP_SHARED))
			&& (flags & MAP_ANONYMOUS))
			|| (vrf0 & VR_XPMEM)) && !thp_disable) {
		*pgshiftp = 0;
		*p2alignp = PAGE_P2ALIGN;

		if (len > PAGE_SIZE) {
			if (!smaller_page_fn) {
				return -EINVAL;
			}
			return smaller_page_fn(len + 1, p2alignp);
		}
		return 0;
	}

	*pgshiftp = PAGE_SHIFT;
	*p2alignp = PAGE_P2ALIGN;
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
memlock_prepare_range(uintptr_t start0, size_t len0,
		uintptr_t user_start, uintptr_t user_end,
		uintptr_t *startp, size_t *lenp, uintptr_t *endp)
{
	uintptr_t start = start0 & PAGE_MASK;
	size_t len = (start & (PAGE_SIZE - 1)) + len0;
	uintptr_t end;

	len = (len + PAGE_SIZE - 1) & PAGE_MASK;
	end = start + len;
	*startp = start;
	*lenp = len;
	*endp = end;

	if (end < start) {
		return -EINVAL;
	}

	if ((start < user_start)
			|| (user_end <= start)
			|| (len > (user_end - user_start))
			|| ((user_end - len) < start)) {
		return -ENOMEM;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
memlock_range_flag_result(unsigned long flag)
{
	return (flag & (VR_REMOTE | VR_RESERVED | VR_IO_NOCACHE)) ?
		-EINVAL : 0;
}

static unsigned long
memlock_range_ulong_field(struct vm_range *range, size_t offset)
{
	return *(unsigned long *)((char *)range + offset);
}

static void
memlock_range_set_ulong_field(struct vm_range *range, size_t offset,
		unsigned long value)
{
	*(unsigned long *)((char *)range + offset) = value;
}

static void *
memlock_range_ptr_field(struct vm_range *range, size_t offset)
{
	return *(void **)((char *)range + offset);
}

static void
memlock_log_emit(memlock_log_fn_t log_fn, int event, int op, int cpu,
		unsigned long start, size_t len, unsigned long addr,
		unsigned long range_start, unsigned long range_end, int error)
{
	struct memlock_log_record record = {
		.event = event,
		.op = op,
		.cpu = cpu,
		.start = start,
		.len = len,
		.addr = addr,
		.range_start = range_start,
		.range_end = range_end,
		.error = error,
	};

	if (log_fn)
		log_fn(&record);
}

SYSCALL_POLICY_HELPER_SCOPE int
memlock_body_result(void *vm_arg, void *range_lock, unsigned long start0,
		size_t len0, unsigned long user_start, unsigned long user_end,
		int op, int cpu, size_t range_start_offset,
		size_t range_end_offset, size_t range_flag_offset,
		size_t range_memobj_offset, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn, syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn, memlock_split_fn_t split_fn,
		memlock_join_fn_t join_fn, memlock_populate_fn_t populate_fn,
		memlock_log_fn_t log_fn)
{
	struct process_vm *vm = vm_arg;
	uintptr_t start;
	size_t len;
	uintptr_t end;
	uintptr_t addr;
	struct vm_range *range = NULL;
	struct vm_range *first = NULL;
	struct vm_range *changed = NULL;
	int error;

	memlock_log_emit(log_fn, MEMLOCK_LOG_ENTER, op, cpu, start0, len0,
			0, 0, 0, 0);

	if (op != MEMLOCK_OP_LOCK && op != MEMLOCK_OP_UNLOCK) {
		error = -EINVAL;
		goto out2;
	}

	error = memlock_prepare_range(start0, len0, user_start, user_end,
			&start, &len, &end);
	if (error)
		goto out2;
	if (start == end) {
		error = 0;
		goto out2;
	}

	if (lock_fn)
		lock_fn(range_lock);

	for (addr = start; addr < end;
			addr = memlock_range_ulong_field(range, range_end_offset)) {
		if (!first) {
			range = lookup_fn ? lookup_fn(vm, start, start + PAGE_SIZE) : NULL;
			first = range;
		}
		else {
			range = next_fn ? next_fn(vm, range) : NULL;
		}

		if (!range || addr < memlock_range_ulong_field(range, range_start_offset)) {
			error = -ENOMEM;
		memlock_log_emit(log_fn, MEMLOCK_LOG_NOT_CONTIG, op, cpu,
				start0, len0, addr,
				range ? memlock_range_ulong_field(range,
					range_start_offset) : 0,
				range ? memlock_range_ulong_field(range,
					range_end_offset) : 0,
				error);
			goto out;
		}

		error = memlock_range_flag_result(
				memlock_range_ulong_field(range, range_flag_offset));
		if (error) {
			memlock_log_emit(log_fn, MEMLOCK_LOG_CANNOT_CHANGE, op, cpu,
					start0, len0, addr,
					memlock_range_ulong_field(range,
						range_start_offset),
					memlock_range_ulong_field(range,
						range_end_offset),
					error);
			goto out;
		}
	}

	for (addr = start; addr < end;
			addr = memlock_range_ulong_field(changed, range_end_offset)) {
		if (!changed)
			range = first;
		else
			range = next_fn ? next_fn(vm, changed) : NULL;

		if (!range || addr < memlock_range_ulong_field(range, range_start_offset)) {
			error = -ENOMEM;
			memlock_log_emit(log_fn, MEMLOCK_LOG_NOT_CONTIG, op, cpu,
					start0, len0, addr,
					range ? memlock_range_ulong_field(range,
						range_start_offset) : 0,
					range ? memlock_range_ulong_field(range,
						range_end_offset) : 0,
					error);
			goto out;
		}

		if (memlock_range_ulong_field(range, range_start_offset) < addr) {
			error = split_fn ? split_fn(vm, range, addr, &range) : -EINVAL;
			if (error) {
				memlock_log_emit(log_fn, MEMLOCK_LOG_SPLIT_FAILED,
						op, cpu, start0, len0, addr,
						memlock_range_ulong_field(range,
							range_start_offset),
						memlock_range_ulong_field(range,
							range_end_offset),
						error);
				goto out;
			}
		}
		if (end < memlock_range_ulong_field(range, range_end_offset)) {
			error = split_fn ? split_fn(vm, range, end, NULL) : -EINVAL;
			if (error) {
				memlock_log_emit(log_fn, MEMLOCK_LOG_SPLIT_FAILED,
						op, cpu, start0, len0, addr,
						memlock_range_ulong_field(range,
							range_start_offset),
						memlock_range_ulong_field(range,
							range_end_offset),
						error);
				goto out;
			}
		}

		if (op == MEMLOCK_OP_LOCK) {
			memlock_range_set_ulong_field(range, range_flag_offset,
					memlock_range_ulong_field(range, range_flag_offset)
					| VR_LOCKED);
		}
		else {
			memlock_range_set_ulong_field(range, range_flag_offset,
					memlock_range_ulong_field(range, range_flag_offset)
					& ~VR_LOCKED);
		}

		if (!changed) {
			changed = range;
		}
		else {
			error = join_fn ? join_fn(vm, changed, range) : -EINVAL;
			if (error) {
				memlock_log_emit(log_fn, MEMLOCK_LOG_JOIN_FAILED,
						op, cpu, start0, len0, addr,
						memlock_range_ulong_field(changed,
							range_start_offset),
						memlock_range_ulong_field(range,
							range_end_offset),
						error);
				changed = range;
			}
		}

		(void)memlock_range_ptr_field(range, range_memobj_offset);
	}

	error = 0;
out:
	if (unlock_fn)
		unlock_fn(range_lock);
	if (!error && op == MEMLOCK_OP_LOCK) {
		error = populate_fn ? populate_fn(vm, start, len) : -EINVAL;
		if (error) {
			memlock_log_emit(log_fn, MEMLOCK_LOG_POPULATE_FAILED, op,
					cpu, start0, len0, start, start, end, error);
			error = 0;
		}
	}
out2:
	memlock_log_emit(log_fn, MEMLOCK_LOG_EXIT, op, cpu, start0, len0,
			0, 0, 0, error);
	return error;
}

SYSCALL_POLICY_HELPER_SCOPE int
range_has_disallowed_change_flags(unsigned long flag)
{
	return (flag & (VR_REMOTE | VR_RESERVED | VR_IO_NOCACHE)) ? 1 : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
munmap_prepare_range(uintptr_t addr, size_t len0,
		uintptr_t user_start, uintptr_t user_end, size_t *lenp)
{
	size_t len = (len0 + PAGE_SIZE - 1) & PAGE_MASK;

	*lenp = len;
	if ((addr & (PAGE_SIZE - 1))
			|| (addr < user_start)
			|| (user_end <= addr)
			|| (len == 0)
			|| (len > (user_end - user_start))
			|| ((user_end - len) < addr)) {
		return -EINVAL;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
munmap_body_result(void *vm, void *range_lock, unsigned long addr,
		size_t len0, unsigned long user_start, unsigned long user_end,
		int cpu, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn, munmap_do_fn_t do_munmap_fn,
		munmap_log_fn_t log_fn)
{
	size_t len;
	int error;

	(void)vm;
	if (log_fn)
		log_fn(MUNMAP_LOG_ENTER, cpu, addr, len0, 0);

	error = munmap_prepare_range(addr, len0, user_start, user_end, &len);
	if (error)
		goto out;

	if (lock_fn)
		lock_fn(range_lock);
	error = do_munmap_fn ? do_munmap_fn((void *)addr, len, 1) : -EINVAL;
	if (unlock_fn)
		unlock_fn(range_lock);

out:
	if (log_fn) {
		log_fn(MUNMAP_LOG_EXIT, cpu, addr, len0, error);
#ifdef ENABLE_FUGAKU_HACKS
		if (error)
			log_fn(MUNMAP_LOG_ERROR, cpu, addr, len0, error);
#endif
	}
	return error;
}

SYSCALL_POLICY_HELPER_SCOPE int
do_munmap_body_result(void *vm, void *proc, unsigned long addr, size_t len,
		int holding_memory_range_lock,
		size_t proc_straight_va_offset,
		size_t proc_straight_len_offset,
		do_munmap_void_fn_t begin_fn,
		do_munmap_remove_range_fn_t remove_range_fn,
		do_munmap_clear_host_fn_t clear_host_pte_fn,
		mprotect_set_host_vma_fn_t set_host_vma_fn,
		do_munmap_void_fn_t finish_fn, do_munmap_log_fn_t log_fn)
{
	unsigned long straight_va;
	size_t straight_len;
	int ro_freed = 0;
	int error;

	if (begin_fn)
		begin_fn();

	error = remove_range_fn ? remove_range_fn(vm, addr, addr + len,
			&ro_freed) : -EINVAL;

	straight_va = *(unsigned long *)syscall_offset_ptr(proc,
			proc_straight_va_offset);
	straight_len = *(size_t *)syscall_offset_ptr(proc,
			proc_straight_len_offset);
	if (!straight_va || addr < straight_va ||
			addr + len > straight_va + straight_len) {
		if (error || !ro_freed) {
			if (clear_host_pte_fn)
				clear_host_pte_fn(addr, len,
						holding_memory_range_lock);
		}
		else {
			error = set_host_vma_fn ? set_host_vma_fn(addr, len,
					PROT_READ | PROT_WRITE | PROT_EXEC,
					holding_memory_range_lock) : -EINVAL;
		}
	}

	if (finish_fn)
		finish_fn();
	if (log_fn)
		log_fn(addr, len, error);
	return error;
}

SYSCALL_POLICY_HELPER_SCOPE long
clear_host_pte_body_result(void *vm, unsigned long addr, size_t len,
		int holding_memory_range_lock, size_t vm_lock_taken_offset,
		int cpu, int syscall_nr, syscall_do_syscall3_fn_t forward_fn,
		clear_host_pte_log_fn_t log_fn)
{
	long lerror;

	if (holding_memory_range_lock) {
		*(int *)syscall_offset_ptr(vm, vm_lock_taken_offset) = cpu;
	}

	lerror = forward_fn ? forward_fn(syscall_nr, addr, len, 0) : -EINVAL;

	if (holding_memory_range_lock) {
		*(int *)syscall_offset_ptr(vm, vm_lock_taken_offset) = -1;
	}
	if (lerror && log_fn)
		log_fn(lerror);
	return lerror;
}

SYSCALL_POLICY_HELPER_SCOPE void
munmap_all_body_result(void *vm, void *range_lock, void *region,
		size_t range_start_offset, size_t range_end_offset,
		size_t region_map_start_offset, size_t region_map_end_offset,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn, munmap_do_fn_t do_munmap_fn,
		munmap_all_free_ranges_fn_t free_ranges_fn,
		munmap_all_log_fn_t log_fn)
{
	struct vm_range *range;
	struct vm_range *next;

	if (lock_fn)
		lock_fn(range_lock);

	next = lookup_fn ? lookup_fn(vm, 0, -1UL) : NULL;
	while ((range = next)) {
		unsigned long start;
		size_t size;
		int error;

		next = next_fn ? next_fn(vm, range) : NULL;
		start = *(unsigned long *)syscall_offset_ptr(range,
				range_start_offset);
		size = *(unsigned long *)syscall_offset_ptr(range,
				range_end_offset) - start;
		error = do_munmap_fn ? do_munmap_fn((void *)start, size, 1) :
				-EINVAL;
		if (error && log_fn)
			log_fn(start, size, error);
	}

	if (unlock_fn)
		unlock_fn(range_lock);

	if (free_ranges_fn)
		free_ranges_fn(vm);

	*(unsigned long *)syscall_offset_ptr(region, region_map_end_offset) =
		*(unsigned long *)syscall_offset_ptr(region,
				region_map_start_offset);
}

static void
shmdt_log_emit(shmdt_log_fn_t log_fn, int event, unsigned long addr,
		int error)
{
	if (log_fn)
		log_fn(event, addr, error);
}

SYSCALL_POLICY_HELPER_SCOPE int
shmdt_body_result(void *vm, void *range_lock, unsigned long shmaddr,
		size_t range_start_offset, size_t range_end_offset,
		size_t range_memobj_offset, size_t memobj_flags_offset,
		unsigned long shmdt_ok_flag, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		munmap_do_fn_t do_munmap_fn, shmdt_log_fn_t log_fn)
{
	struct vm_range *range = NULL;
	struct memobj *memobj = NULL;
	unsigned long start = 0;
	unsigned long end = 0;
	int invalid = 1;
	int error = -EINVAL;

	shmdt_log_emit(log_fn, SHMDT_LOG_ENTER, shmaddr, 0);
	if (lock_fn)
		lock_fn(range_lock);

	if (lookup_fn)
		range = lookup_fn(vm, shmaddr, shmaddr + 1);
	if (range) {
		start = *(unsigned long *)syscall_offset_ptr(range,
				range_start_offset);
		end = *(unsigned long *)syscall_offset_ptr(range,
				range_end_offset);
		memobj = *(struct memobj **)syscall_offset_ptr(range,
				range_memobj_offset);
		if (start == shmaddr && memobj) {
			uint32_t flags = *(uint32_t *)syscall_offset_ptr(memobj,
					memobj_flags_offset);
			if (flags & shmdt_ok_flag) {
				invalid = 0;
				error = do_munmap_fn ? do_munmap_fn((void *)start,
						end - start, 1) : -EINVAL;
			}
		}
	}

	if (unlock_fn)
		unlock_fn(range_lock);

	if (invalid)
		shmdt_log_emit(log_fn, SHMDT_LOG_INVALID, shmaddr, -EINVAL);
	else
		shmdt_log_emit(log_fn, SHMDT_LOG_EXIT, shmaddr, error);
	return error;
}

static void
shmat_log_emit(shmat_log_fn_t log_fn, int event, int shmid,
		unsigned long shmaddr, int shmflg, long error)
{
	if (log_fn)
		log_fn(event, shmid, shmaddr, shmflg, error);
}

static int
shmat_body_access_result(uid_t euid, gid_t egid, int shmflg, uid_t uid,
		uid_t cuid, gid_t gid, gid_t cgid, uint16_t mode)
{
	int req = 4;

	if (!(shmflg & SHM_RDONLY))
		req |= 2;

	if (!euid)
		req = 0;
	else if ((euid == uid) || (euid == cuid))
		req <<= 6;
	else if ((egid == gid) || (egid == cgid))
		req <<= 3;

	return (req & ~mode) ? -EACCES : 0;
}

static void *
shmat_body_memobj(void *obj, size_t obj_memobj_offset)
{
	return syscall_offset_ptr(obj, obj_memobj_offset);
}

static void
shmat_body_unref_obj(void *obj, size_t obj_memobj_offset,
		shmat_memobj_fn_t memobj_unref_fn)
{
	if (memobj_unref_fn)
		memobj_unref_fn(shmat_body_memobj(obj, obj_memobj_offset));
}

SYSCALL_POLICY_HELPER_SCOPE long
shmat_body_result(int shmid, unsigned long shmaddr, int shmflg,
		uid_t proc_euid, gid_t proc_egid, void *vm, void *range_lock,
		size_t obj_pgshift_offset, size_t obj_real_segsz_offset,
		size_t obj_memobj_offset, size_t obj_uid_offset,
		size_t obj_cuid_offset, size_t obj_gid_offset,
		size_t obj_cgid_offset, size_t obj_mode_offset,
		shmat_void_fn_t list_lock_fn, shmat_void_fn_t list_unlock_fn,
		shmat_lookup_obj_fn_t lookup_obj_fn,
		shmat_memobj_fn_t memobj_unref_fn,
		syscall_rwlock_fn_t range_lock_fn,
		syscall_rwlock_fn_t range_unlock_fn,
		syscall_lookup_range_fn_t lookup_range_fn,
		shmat_search_fn_t search_free_fn,
		mprotect_set_host_vma_fn_t set_host_vma_fn,
		shmat_add_range_fn_t add_range_fn, shmat_log_fn_t log_fn)
{
	void *obj = NULL;
	unsigned long addr;
	unsigned long pgmask;
	unsigned long vrflags;
	size_t pgsize;
	size_t len;
	int pgshift;
	int error;
	int prot;

	shmat_log_emit(log_fn, SHMAT_LOG_ENTER, shmid, shmaddr, shmflg, 0);

	if (list_lock_fn)
		list_lock_fn();

	error = lookup_obj_fn ? lookup_obj_fn(shmid, &obj) : -EINVAL;
	if (error || !obj) {
		if (!error)
			error = -EINVAL;
		if (list_unlock_fn)
			list_unlock_fn();
		shmat_log_emit(log_fn, SHMAT_LOG_LOOKUP_FAILED, shmid,
				shmaddr, shmflg, error);
		return error;
	}

	pgshift = *(int *)syscall_offset_ptr(obj, obj_pgshift_offset);
	if (pgshift < 0 || pgshift >= (int)(sizeof(size_t) * 8)) {
		if (list_unlock_fn)
			list_unlock_fn();
		shmat_body_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
		shmat_log_emit(log_fn, SHMAT_LOG_INVALID_ADDR, shmid,
				shmaddr, shmflg, -EINVAL);
		return -EINVAL;
	}

	pgsize = (size_t)1 << pgshift;
	pgmask = pgsize - 1;
	if (shmaddr && (shmaddr & pgmask) && !(shmflg & SHM_RND)) {
		if (list_unlock_fn)
			list_unlock_fn();
		shmat_body_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
		shmat_log_emit(log_fn, SHMAT_LOG_INVALID_ADDR, shmid,
				shmaddr, shmflg, -EINVAL);
		return -EINVAL;
	}
	addr = shmaddr & ~pgmask;
	len = *(size_t *)syscall_offset_ptr(obj, obj_real_segsz_offset);

	prot = PROT_READ;
	if (!(shmflg & SHM_RDONLY))
		prot |= PROT_WRITE;

	error = shmat_body_access_result(proc_euid, proc_egid, shmflg,
			*(uid_t *)syscall_offset_ptr(obj, obj_uid_offset),
			*(uid_t *)syscall_offset_ptr(obj, obj_cuid_offset),
			*(gid_t *)syscall_offset_ptr(obj, obj_gid_offset),
			*(gid_t *)syscall_offset_ptr(obj, obj_cgid_offset),
			*(uint16_t *)syscall_offset_ptr(obj, obj_mode_offset));
	if (error) {
		if (list_unlock_fn)
			list_unlock_fn();
		shmat_body_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
		shmat_log_emit(log_fn, SHMAT_LOG_ACCESS_FAILED, shmid,
				shmaddr, shmflg, error);
		return error;
	}

	if (range_lock_fn)
		range_lock_fn(range_lock);

	if (addr) {
		if (!lookup_range_fn) {
			error = -EINVAL;
			goto out_range_busy;
		}
		if (lookup_range_fn(vm, addr, addr + len)) {
			error = -ENOMEM;
out_range_busy:
			if (range_unlock_fn)
				range_unlock_fn(range_lock);
			if (list_unlock_fn)
				list_unlock_fn();
			shmat_body_unref_obj(obj, obj_memobj_offset,
					memobj_unref_fn);
			shmat_log_emit(log_fn, SHMAT_LOG_RANGE_BUSY, shmid,
					shmaddr, shmflg, error);
			return error;
		}
	}
	else {
		error = search_free_fn ? search_free_fn(len, pgshift, &addr) :
				-EINVAL;
		if (error) {
			if (range_unlock_fn)
				range_unlock_fn(range_lock);
			if (list_unlock_fn)
				list_unlock_fn();
			shmat_body_unref_obj(obj, obj_memobj_offset,
					memobj_unref_fn);
			shmat_log_emit(log_fn, SHMAT_LOG_SEARCH_FAILED, shmid,
					shmaddr, shmflg, error);
			return error;
		}
	}

	vrflags = VR_DEMAND_PAGING;
	vrflags |= PROT_TO_VR_FLAG(prot);
	vrflags |= VRFLAG_PROT_TO_MAXPROT(vrflags);

	if (!(prot & PROT_WRITE)) {
		error = set_host_vma_fn ? set_host_vma_fn(addr, len,
				PROT_READ | PROT_EXEC, 1) : -EINVAL;
		if (error) {
			if (range_unlock_fn)
				range_unlock_fn(range_lock);
			if (list_unlock_fn)
				list_unlock_fn();
			shmat_body_unref_obj(obj, obj_memobj_offset,
					memobj_unref_fn);
			shmat_log_emit(log_fn, SHMAT_LOG_SET_HOST_FAILED,
					shmid, shmaddr, shmflg, error);
			return error;
		}
	}

	error = add_range_fn ? add_range_fn(vm, addr, addr + len, -1UL,
			vrflags, shmat_body_memobj(obj, obj_memobj_offset), 0,
			pgshift) : -EINVAL;
	if (error) {
		if (!(prot & PROT_WRITE) && set_host_vma_fn) {
			(void)set_host_vma_fn(addr, len,
					PROT_READ | PROT_WRITE | PROT_EXEC, 1);
		}
		shmat_body_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
		if (range_unlock_fn)
			range_unlock_fn(range_lock);
		if (list_unlock_fn)
			list_unlock_fn();
		shmat_log_emit(log_fn, SHMAT_LOG_ADD_FAILED, shmid, shmaddr,
				shmflg, error);
		return error;
	}

	if (range_unlock_fn)
		range_unlock_fn(range_lock);
	if (list_unlock_fn)
		list_unlock_fn();
	shmat_log_emit(log_fn, SHMAT_LOG_EXIT, shmid, shmaddr, shmflg, addr);
	return addr;
}

static void
shmctl_log_emit(shmctl_log_fn_t log_fn, int event, int shmid, int cmd,
		unsigned long buf_addr, long error)
{
	if (log_fn)
		log_fn(event, shmid, cmd, buf_addr, error);
}

static void *
shmctl_body_memobj(void *obj, const struct shmctl_offsets *offsets)
{
	return syscall_offset_ptr(obj, offsets->obj_memobj_offset);
}

static void
shmctl_body_unref_obj(void *obj, const struct shmctl_offsets *offsets,
		shmat_memobj_fn_t memobj_unref_fn)
{
	if (memobj_unref_fn)
		memobj_unref_fn(shmctl_body_memobj(obj, offsets));
}

static int
shmctl_body_owner(uid_t euid, uid_t uid, uid_t cuid)
{
	return ((uid == euid) || (cuid == euid)) ? 0 : -EPERM;
}

static int
shmctl_body_owner_or_cap(int has_cap, uid_t euid, uid_t uid, uid_t cuid)
{
	return (has_cap || (uid == euid) || (cuid == euid)) ? 0 : -EPERM;
}

static int
shmctl_body_ipc_stat_access(uid_t euid, gid_t egid, uid_t uid, uid_t cuid,
		gid_t gid, gid_t cgid, uint16_t mode)
{
	int req;

	if (!euid)
		req = 0;
	else if ((euid == uid) || (euid == cuid))
		req = 0400;
	else if ((egid == gid) || (egid == cgid))
		req = 0040;
	else
		req = 0004;

	return (req & ~mode) ? -EACCES : 0;
}

static int
shmctl_body_shmlock_rlimit(int has_cap, unsigned long rlim_cur,
		unsigned long user_locked, unsigned long size)
{
	if (!rlim_cur && !has_cap)
		return -EPERM;
	if (!has_cap && rlim_cur != (unsigned long)-1 &&
			(rlim_cur < user_locked ||
			 (rlim_cur - user_locked) < size))
		return -ENOMEM;
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
shmctl_body_result(int shmid, int cmd, unsigned long buf_addr,
		uid_t proc_euid, gid_t proc_egid, uid_t proc_ruid,
		unsigned long rlim_memlock_cur, long now,
		int has_cap_sys_admin, int has_cap_ipc_lock,
		const struct shmctl_offsets *offsets, const void *shminfo,
		const void *shm_info, shmat_void_fn_t list_lock_fn,
		shmat_void_fn_t list_unlock_fn,
		shmat_lookup_obj_fn_t lookup_obj_fn,
		shmat_lookup_obj_fn_t lookup_by_index_fn,
		shmat_memobj_fn_t memobj_unref_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		shmctl_get_max_index_fn_t get_max_index_fn,
		shmat_void_fn_t users_lock_fn,
		shmat_void_fn_t users_unlock_fn,
		shmctl_shmlock_user_get_fn_t shmlock_user_get_fn,
		shmat_memobj_fn_t shmlock_user_free_fn,
		shmctl_memobj_refcnt_read_fn_t memobj_refcnt_read_fn,
		shmctl_log_fn_t log_fn)
{
	struct shmobj *obj = NULL;
	int error;

	shmctl_log_emit(log_fn, SHMCTL_LOG_ENTER, shmid, cmd, buf_addr, 0);
	if (!offsets || offsets->shmid_ds_size != sizeof(struct shmid_ds) ||
			!list_lock_fn || !list_unlock_fn ||
			!lookup_obj_fn || !copy_to_fn || !get_max_index_fn) {
		shmctl_log_emit(log_fn, SHMCTL_LOG_EINVAL, shmid, cmd,
				buf_addr, -EINVAL);
		return -EINVAL;
	}

	switch (cmd) {
	case IPC_RMID: {
		uint16_t oldmode;
		list_lock_fn();
		error = lookup_obj_fn(shmid, (void **)&obj);
		if (error || !obj) {
			if (!error)
				error = -EINVAL;
			list_unlock_fn();
			shmctl_log_emit(log_fn, SHMCTL_LOG_LOOKUP, shmid,
					cmd, buf_addr, error);
			return error;
		}
		error = shmctl_body_owner_or_cap(has_cap_sys_admin,
				proc_euid,
				*(uid_t *)syscall_offset_ptr(obj,
					offsets->obj_uid_offset),
				*(uid_t *)syscall_offset_ptr(obj,
					offsets->obj_cuid_offset));
		if (error) {
			list_unlock_fn();
			shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
			shmctl_log_emit(log_fn, SHMCTL_LOG_EPERM, shmid,
					cmd, buf_addr, error);
			return error;
		}
		oldmode = *(uint16_t *)syscall_offset_ptr(obj,
				offsets->obj_mode_offset);
		*(uint16_t *)syscall_offset_ptr(obj, offsets->obj_mode_offset) =
			oldmode | SHM_DEST;
		list_unlock_fn();
		if (!(oldmode & SHM_DEST))
			shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
		shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
		shmctl_log_emit(log_fn, SHMCTL_LOG_EXIT, shmid, cmd,
				buf_addr, 0);
		return 0;
	}
	case IPC_SET: {
		struct shmid_ds ads;
		uint16_t *modep;

		if (!copy_from_fn)
			return -EINVAL;
		list_lock_fn();
		error = lookup_obj_fn(shmid, (void **)&obj);
		if (error || !obj) {
			if (!error)
				error = -EINVAL;
			list_unlock_fn();
			shmctl_log_emit(log_fn, SHMCTL_LOG_LOOKUP, shmid,
					cmd, buf_addr, error);
			return error;
		}
		error = shmctl_body_owner(proc_euid,
				*(uid_t *)syscall_offset_ptr(obj,
					offsets->obj_uid_offset),
				*(uid_t *)syscall_offset_ptr(obj,
					offsets->obj_cuid_offset));
		if (error) {
			list_unlock_fn();
			shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
			shmctl_log_emit(log_fn, SHMCTL_LOG_EPERM, shmid,
					cmd, buf_addr, error);
			return error;
		}
		error = copy_from_fn(&ads, buf_addr, sizeof(ads));
		if (error) {
			list_unlock_fn();
			shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
			shmctl_log_emit(log_fn, SHMCTL_LOG_COPY, shmid,
					cmd, buf_addr, error);
			return error;
		}
		*(uid_t *)syscall_offset_ptr(obj, offsets->obj_uid_offset) =
			ads.shm_perm.uid;
		*(gid_t *)syscall_offset_ptr(obj, offsets->obj_gid_offset) =
			ads.shm_perm.gid;
		modep = (uint16_t *)syscall_offset_ptr(obj,
				offsets->obj_mode_offset);
		*modep &= ~0777;
		*modep |= ads.shm_perm.mode & 0777;
		*(long *)syscall_offset_ptr(obj, offsets->obj_ctime_offset) =
			now;
		list_unlock_fn();
		shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
		shmctl_log_emit(log_fn, SHMCTL_LOG_EXIT, shmid, cmd,
				buf_addr, 0);
		return 0;
	}
	case IPC_STAT:
	case SHM_STAT:
		list_lock_fn();
		if (cmd == IPC_STAT)
			error = lookup_obj_fn(shmid, (void **)&obj);
		else
			error = lookup_by_index_fn ?
				lookup_by_index_fn(shmid, (void **)&obj) :
				-EINVAL;
		if (error || !obj) {
			if (!error)
				error = -EINVAL;
			list_unlock_fn();
			shmctl_log_emit(log_fn, SHMCTL_LOG_LOOKUP, shmid,
					cmd, buf_addr, error);
			return error;
		}
		if (cmd == IPC_STAT) {
			error = shmctl_body_ipc_stat_access(proc_euid, proc_egid,
				*(uid_t *)syscall_offset_ptr(obj,
					offsets->obj_uid_offset),
				*(uid_t *)syscall_offset_ptr(obj,
					offsets->obj_cuid_offset),
				*(gid_t *)syscall_offset_ptr(obj,
					offsets->obj_gid_offset),
				*(gid_t *)syscall_offset_ptr(obj,
					offsets->obj_cgid_offset),
				*(uint16_t *)syscall_offset_ptr(obj,
					offsets->obj_mode_offset));
			if (error) {
				list_unlock_fn();
				shmctl_body_unref_obj(obj, offsets,
						memobj_unref_fn);
				shmctl_log_emit(log_fn, SHMCTL_LOG_EACCES,
						shmid, cmd, buf_addr, error);
				return error;
			}
		}
		*(uint64_t *)syscall_offset_ptr(obj, offsets->obj_nattch_offset) =
			(memobj_refcnt_read_fn ?
			 memobj_refcnt_read_fn(shmctl_body_memobj(obj,
				 offsets)) : 0) - 1;
		if (!(*(uint16_t *)syscall_offset_ptr(obj,
				offsets->obj_mode_offset) & SHM_DEST)) {
			--*(uint64_t *)syscall_offset_ptr(obj,
					offsets->obj_nattch_offset);
		}
		error = copy_to_fn(buf_addr,
				syscall_offset_ptr(obj, offsets->obj_ds_offset),
				offsets->shmid_ds_size);
		if (error) {
			list_unlock_fn();
			shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
			shmctl_log_emit(log_fn, SHMCTL_LOG_COPY, shmid,
					cmd, buf_addr, error);
			return error;
		}
		list_unlock_fn();
		shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
		shmctl_log_emit(log_fn, SHMCTL_LOG_EXIT, shmid, cmd,
				buf_addr, 0);
		return 0;
	case IPC_INFO: {
		int maxi;
		list_lock_fn();
		error = lookup_obj_fn(shmid, (void **)&obj);
		if (error || !obj) {
			if (!error)
				error = -EINVAL;
			list_unlock_fn();
			shmctl_log_emit(log_fn, SHMCTL_LOG_LOOKUP, shmid,
					cmd, buf_addr, error);
			return error;
		}
		error = copy_to_fn(buf_addr, shminfo, offsets->shminfo_size);
		if (error) {
			list_unlock_fn();
			shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
			shmctl_log_emit(log_fn, SHMCTL_LOG_COPY, shmid,
					cmd, buf_addr, error);
			return error;
		}
		maxi = get_max_index_fn();
		if (maxi < 0)
			maxi = 0;
		list_unlock_fn();
		shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
		shmctl_log_emit(log_fn, SHMCTL_LOG_EXIT, shmid, cmd,
				buf_addr, maxi);
		return maxi;
	}
	case SHM_LOCK:
		list_lock_fn();
		error = lookup_obj_fn(shmid, (void **)&obj);
		if (error || !obj) {
			if (!error)
				error = -EINVAL;
			list_unlock_fn();
			shmctl_log_emit(log_fn, SHMCTL_LOG_LOOKUP, shmid,
					cmd, buf_addr, error);
			return error;
		}
		error = shmctl_body_owner_or_cap(has_cap_ipc_lock, proc_euid,
				*(uid_t *)syscall_offset_ptr(obj,
					offsets->obj_uid_offset),
				*(uid_t *)syscall_offset_ptr(obj,
					offsets->obj_cuid_offset));
		if (error) {
			list_unlock_fn();
			shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
			shmctl_log_emit(log_fn, SHMCTL_LOG_PERM_SHM, shmid,
					cmd, buf_addr, error);
			return error;
		}
		error = shmctl_body_shmlock_rlimit(has_cap_ipc_lock,
				rlim_memlock_cur, 0, 0);
		if (error) {
			list_unlock_fn();
			shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
			shmctl_log_emit(log_fn, SHMCTL_LOG_PERM_PROC, shmid,
					cmd, buf_addr, error);
			return error;
		}
		if (!(*(uint16_t *)syscall_offset_ptr(obj,
				offsets->obj_mode_offset) & SHM_LOCKED) &&
				(*(int *)syscall_offset_ptr(obj,
					offsets->obj_pgshift_offset) == 0 ||
				 *(int *)syscall_offset_ptr(obj,
					offsets->obj_pgshift_offset) ==
					 PAGE_SHIFT)) {
			void *user = NULL;
			size_t size;
			size_t *lockedp;

			if (!users_lock_fn || !users_unlock_fn ||
					!shmlock_user_get_fn) {
				list_unlock_fn();
				shmctl_body_unref_obj(obj, offsets,
						memobj_unref_fn);
				return -EINVAL;
			}
			users_lock_fn();
			error = shmlock_user_get_fn(proc_ruid, &user);
			if (error || !user) {
				users_unlock_fn();
				shmctl_body_unref_obj(obj, offsets,
						memobj_unref_fn);
				list_unlock_fn();
				shmctl_log_emit(log_fn,
						SHMCTL_LOG_USER_LOOKUP,
						shmid, cmd, buf_addr, error);
				return -ENOMEM;
			}
			size = *(size_t *)syscall_offset_ptr(obj,
					offsets->obj_real_segsz_offset);
			lockedp = (size_t *)syscall_offset_ptr(user,
					offsets->shmlock_user_locked_offset);
			error = shmctl_body_shmlock_rlimit(has_cap_ipc_lock,
					rlim_memlock_cur, *lockedp, size);
			if (error) {
				users_unlock_fn();
				shmctl_body_unref_obj(obj, offsets,
						memobj_unref_fn);
				list_unlock_fn();
				shmctl_log_emit(log_fn,
						SHMCTL_LOG_TOO_LARGE, shmid,
						cmd, buf_addr, error);
				return error;
			}
			*(uint16_t *)syscall_offset_ptr(obj,
					offsets->obj_mode_offset) |= SHM_LOCKED;
			*(void **)syscall_offset_ptr(obj,
					offsets->obj_user_offset) = user;
			*lockedp += size;
			users_unlock_fn();
		}
		list_unlock_fn();
		shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
		shmctl_log_emit(log_fn, SHMCTL_LOG_EXIT, shmid, cmd,
				buf_addr, 0);
		return 0;
	case SHM_UNLOCK:
		list_lock_fn();
		error = lookup_obj_fn(shmid, (void **)&obj);
		if (error || !obj) {
			if (!error)
				error = -EINVAL;
			list_unlock_fn();
			shmctl_log_emit(log_fn, SHMCTL_LOG_LOOKUP, shmid,
					cmd, buf_addr, error);
			return error;
		}
		error = shmctl_body_owner_or_cap(has_cap_ipc_lock, proc_euid,
				*(uid_t *)syscall_offset_ptr(obj,
					offsets->obj_uid_offset),
				*(uid_t *)syscall_offset_ptr(obj,
					offsets->obj_cuid_offset));
		if (error) {
			list_unlock_fn();
			shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
			shmctl_log_emit(log_fn, SHMCTL_LOG_PERM_SHM, shmid,
					cmd, buf_addr, error);
			return error;
		}
		if ((*(uint16_t *)syscall_offset_ptr(obj,
				offsets->obj_mode_offset) & SHM_LOCKED) &&
				(*(int *)syscall_offset_ptr(obj,
					offsets->obj_pgshift_offset) == 0 ||
				 *(int *)syscall_offset_ptr(obj,
					offsets->obj_pgshift_offset) ==
					 PAGE_SHIFT)) {
			void *user;
			size_t size;
			size_t *lockedp;

			if (!users_lock_fn || !users_unlock_fn) {
				list_unlock_fn();
				shmctl_body_unref_obj(obj, offsets,
						memobj_unref_fn);
				return -EINVAL;
			}
			size = *(size_t *)syscall_offset_ptr(obj,
					offsets->obj_real_segsz_offset);
			users_lock_fn();
			user = *(void **)syscall_offset_ptr(obj,
					offsets->obj_user_offset);
			*(void **)syscall_offset_ptr(obj,
					offsets->obj_user_offset) = NULL;
			if (user) {
				lockedp = (size_t *)syscall_offset_ptr(user,
					offsets->shmlock_user_locked_offset);
				*lockedp -= size;
				if (!*lockedp && shmlock_user_free_fn)
					shmlock_user_free_fn(user);
			}
			users_unlock_fn();
			*(uint16_t *)syscall_offset_ptr(obj,
					offsets->obj_mode_offset) &=
				~SHM_LOCKED;
		}
		list_unlock_fn();
		shmctl_body_unref_obj(obj, offsets, memobj_unref_fn);
		shmctl_log_emit(log_fn, SHMCTL_LOG_EXIT, shmid, cmd,
				buf_addr, 0);
		return 0;
	case SHM_INFO: {
		int maxi;
		list_lock_fn();
		error = copy_to_fn(buf_addr, shm_info, offsets->shm_info_size);
		if (error) {
			list_unlock_fn();
			shmctl_log_emit(log_fn, SHMCTL_LOG_COPY, shmid,
					cmd, buf_addr, error);
			return error;
		}
		maxi = get_max_index_fn();
		if (maxi < 0)
			maxi = 0;
		list_unlock_fn();
		shmctl_log_emit(log_fn, SHMCTL_LOG_EXIT, shmid, cmd,
				buf_addr, maxi);
		return maxi;
	}
	default:
		shmctl_log_emit(log_fn, SHMCTL_LOG_EINVAL, shmid, cmd,
				buf_addr, -EINVAL);
		return -EINVAL;
	}
}

static void
search_free_space_log_emit(search_free_space_log_fn_t log_fn, int event,
		size_t len, int pgshift, unsigned long addr, int error)
{
	if (log_fn)
		log_fn(event, len, pgshift, addr, error);
}

SYSCALL_POLICY_HELPER_SCOPE int
search_free_space_body_result(void *vm, void *region, size_t len,
		int pgshift, unsigned long *addrp,
		size_t region_user_end_offset, size_t region_map_end_offset,
		size_t range_end_offset, syscall_lookup_range_fn_t lookup_fn,
		search_free_space_log_fn_t log_fn)
{
	unsigned long addr = addrp ? *addrp : 0;
	unsigned long user_end;
	unsigned long pgsize;
	unsigned long pgmask;
	struct vm_range *range;

	search_free_space_log_emit(log_fn, SEARCH_FREE_SPACE_LOG_ENTER, len,
			pgshift, addr, 0);

	if (!addrp || pgshift < 0 || pgshift >= (int)(sizeof(size_t) * 8)) {
		search_free_space_log_emit(log_fn, SEARCH_FREE_SPACE_LOG_EXIT,
				len, pgshift, addr, -EINVAL);
		return -EINVAL;
	}
	if (!lookup_fn) {
		search_free_space_log_emit(log_fn, SEARCH_FREE_SPACE_LOG_EXIT,
				len, pgshift, addr, -EINVAL);
		return -EINVAL;
	}

	user_end = *(unsigned long *)syscall_offset_ptr(region,
			region_user_end_offset);
	pgsize = (unsigned long)1 << pgshift;
	pgmask = pgsize - 1;

	if (addr != 0) {
		if ((user_end <= addr) || ((user_end - len) < addr)) {
			search_free_space_log_emit(log_fn,
					SEARCH_FREE_SPACE_LOG_OUTSIDE, len,
					pgshift, addr, -ENOMEM);
			search_free_space_log_emit(log_fn,
					SEARCH_FREE_SPACE_LOG_EXIT, len,
					pgshift, addr, -ENOMEM);
			return -ENOMEM;
		}

		range = lookup_fn(vm, addr, addr + len);
		if (range == NULL) {
			search_free_space_log_emit(log_fn,
					SEARCH_FREE_SPACE_LOG_EXIT, len,
					pgshift, addr, 0);
			return 0;
		}
	}

	addr = *(unsigned long *)syscall_offset_ptr(region,
			region_map_end_offset);
	for (;;) {
		addr = (addr + pgmask) & ~pgmask;
		if ((user_end <= addr) || ((user_end - len) < addr)) {
			search_free_space_log_emit(log_fn,
					SEARCH_FREE_SPACE_LOG_OUTSIDE, len,
					pgshift, addr, -ENOMEM);
			search_free_space_log_emit(log_fn,
					SEARCH_FREE_SPACE_LOG_EXIT, len,
					pgshift, addr, -ENOMEM);
			return -ENOMEM;
		}

		range = lookup_fn(vm, addr, addr + len);
		if (range == NULL)
			break;
		addr = *(unsigned long *)syscall_offset_ptr(range,
				range_end_offset);
	}

	*(unsigned long *)syscall_offset_ptr(region, region_map_end_offset) =
			addr + len;
	*addrp = addr;
	search_free_space_log_emit(log_fn, SEARCH_FREE_SPACE_LOG_EXIT, len,
			pgshift, addr, 0);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
set_host_vma_body_result(unsigned long addr, size_t len, int prot,
		int holding_memory_range_lock)
{
	(void)addr;
	(void)len;
	(void)prot;
	(void)holding_memory_range_lock;
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
mprotect_prepare_range(uintptr_t start, size_t len0,
		uintptr_t user_start, uintptr_t user_end,
		size_t *lenp, uintptr_t *endp)
{
	size_t len = (len0 + PAGE_SIZE - 1) & PAGE_MASK;
	uintptr_t end = start + len;

	*lenp = len;
	*endp = end;
	if (start & (PAGE_SIZE - 1)) {
		return -EINVAL;
	}

	if ((start < user_start)
			|| (user_end <= start)
			|| ((user_end - start) < len)) {
		return -ENOMEM;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE void
mprotect_split_needed_result(unsigned long range_start, unsigned long range_end,
		unsigned long addr, unsigned long end, int *split_startp,
		int *split_endp)
{
	if (split_startp)
		*split_startp = range_start < addr;
	if (split_endp)
		*split_endp = end < range_end;
}

SYSCALL_POLICY_HELPER_SCOPE int
mprotect_write_changed_result(unsigned long range_flags,
		unsigned long protflags)
{
	return ((range_flags ^ protflags) & VR_PROT_WRITE) != 0;
}

static void
mprotect_log_emit(mprotect_log_fn_t log_fn, int event, int cpu,
		unsigned long start, size_t len, int prot, unsigned long addr,
		unsigned long range_start, unsigned long range_end,
		unsigned long range_flags, unsigned long protflags,
		unsigned long denied, int error)
{
	struct mprotect_log_record record = {
		.event = event,
		.cpu = cpu,
		.start = start,
		.len = len,
		.prot = prot,
		.addr = addr,
		.range_start = range_start,
		.range_end = range_end,
		.range_flags = range_flags,
		.protflags = protflags,
		.denied = denied,
		.error = error,
	};

	if (log_fn)
		log_fn(&record);
}

SYSCALL_POLICY_HELPER_SCOPE int
mprotect_body_result(void *vm_arg, void *range_lock, unsigned long start,
		size_t len0, int prot, unsigned long user_start,
		unsigned long user_end, unsigned long straight_va,
		size_t straight_len, int cpu, size_t range_start_offset,
		size_t range_end_offset, size_t range_flag_offset,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn, memlock_split_fn_t split_fn,
		memlock_join_fn_t join_fn, mprotect_change_fn_t change_fn,
		mprotect_set_host_vma_fn_t set_host_vma_fn,
		mprotect_flush_fn_t flush_nfo_fn,
		mprotect_flush_fn_t flush_tlb_fn, mprotect_log_fn_t log_fn)
{
	struct process_vm *vm = vm_arg;
	size_t len;
	uintptr_t end;
	struct vm_range *first;
	uintptr_t addr;
	struct vm_range *range;
	struct vm_range *changed;
	const unsigned long protflags = PROT_TO_VR_FLAG(prot);
	unsigned long denied;
	int ro_changed = 0;
	int split_start;
	int split_end;
	int error;

	mprotect_log_emit(log_fn, MPROTECT_LOG_ENTER, cpu, start, len0, prot,
			0, 0, 0, 0, protflags, 0, 0);

	error = mprotect_prepare_range(start, len0, user_start, user_end,
			&len, &end);
	if (error) {
		mprotect_log_emit(log_fn, MPROTECT_LOG_INVALID_RANGE, cpu,
				start, len0, prot, 0, 0, 0, 0, protflags, 0,
				error);
		return error;
	}

	if (len == 0)
		return 0;

	if (straight_va && start >= straight_va &&
			end <= straight_va + straight_len) {
		error = 0;
		mprotect_log_emit(log_fn, MPROTECT_LOG_STRAIGHT_IGNORED, cpu,
				start, len0, prot, 0, straight_va,
				straight_va + straight_len, 0, protflags, 0,
				error);
		goto out_straight;
	}

	if (flush_nfo_fn)
		flush_nfo_fn();

	if (lock_fn)
		lock_fn(range_lock);

	first = lookup_fn ? lookup_fn(vm, start, start + PAGE_SIZE) : NULL;
	changed = NULL;
	for (addr = start; addr < end;
			addr = memlock_range_ulong_field(changed,
				range_end_offset)) {
		if (changed == NULL) {
			range = first;
		}
		else {
			range = next_fn ? next_fn(vm, changed) : NULL;
		}

		if ((range == NULL) ||
				(addr < memlock_range_ulong_field(range,
					range_start_offset))) {
			error = -ENOMEM;
			mprotect_log_emit(log_fn, MPROTECT_LOG_NOT_CONTIG, cpu,
					start, len0, prot, addr,
					range ? memlock_range_ulong_field(range,
						range_start_offset) : 0,
					range ? memlock_range_ulong_field(range,
						range_end_offset) : 0,
					range ? memlock_range_ulong_field(range,
						range_flag_offset) : 0,
					protflags, 0, error);
			goto out;
		}

		denied = protflags &
			~VRFLAG_MAXPROT_TO_PROT(
				memlock_range_ulong_field(range,
					range_flag_offset));
		if (denied) {
			error = -EACCES;
			mprotect_log_emit(log_fn, MPROTECT_LOG_DENIED, cpu,
					start, len0, prot, addr,
					memlock_range_ulong_field(range,
						range_start_offset),
					memlock_range_ulong_field(range,
						range_end_offset),
					memlock_range_ulong_field(range,
						range_flag_offset),
					protflags, denied, error);
			goto out;
		}

		if (range_has_disallowed_change_flags(
					memlock_range_ulong_field(range,
						range_flag_offset))) {
			error = -ENOMEM;
			mprotect_log_emit(log_fn, MPROTECT_LOG_CANNOT_CHANGE,
					cpu, start, len0, prot, addr,
					memlock_range_ulong_field(range,
						range_start_offset),
					memlock_range_ulong_field(range,
						range_end_offset),
					memlock_range_ulong_field(range,
						range_flag_offset),
					protflags, 0, error);
			goto out;
		}

		mprotect_split_needed_result(
				memlock_range_ulong_field(range,
					range_start_offset),
				memlock_range_ulong_field(range,
					range_end_offset),
				addr, end, &split_start, &split_end);
		if (split_start) {
			error = split_fn ? split_fn(vm, range, addr, &range) :
				-EINVAL;
			if (error) {
				mprotect_log_emit(log_fn,
						MPROTECT_LOG_SPLIT_FAILED,
						cpu, start, len0, prot, addr,
						memlock_range_ulong_field(range,
							range_start_offset),
						memlock_range_ulong_field(range,
							range_end_offset),
						memlock_range_ulong_field(range,
							range_flag_offset),
						protflags, 0, error);
				goto out;
			}
		}
		if (split_end) {
			error = split_fn ? split_fn(vm, range, end, NULL) :
				-EINVAL;
			if (error) {
				mprotect_log_emit(log_fn,
						MPROTECT_LOG_SPLIT_FAILED,
						cpu, start, len0, prot, end,
						memlock_range_ulong_field(range,
							range_start_offset),
						memlock_range_ulong_field(range,
							range_end_offset),
						memlock_range_ulong_field(range,
							range_flag_offset),
						protflags, 0, error);
				goto out;
			}
		}

		if (mprotect_write_changed_result(
					memlock_range_ulong_field(range,
						range_flag_offset),
					protflags)) {
			ro_changed = 1;
		}

		error = change_fn ? change_fn(vm, range, protflags) : -EINVAL;
		if (error) {
			mprotect_log_emit(log_fn, MPROTECT_LOG_CHANGE_FAILED,
					cpu, start, len0, prot, addr,
					memlock_range_ulong_field(range,
						range_start_offset),
					memlock_range_ulong_field(range,
						range_end_offset),
					memlock_range_ulong_field(range,
						range_flag_offset),
					protflags, 0, error);
			goto out;
		}

		if (changed == NULL) {
			changed = range;
		}
		else {
			error = join_fn ? join_fn(vm, changed, range) : -EINVAL;
			if (error) {
				mprotect_log_emit(log_fn, MPROTECT_LOG_JOIN_FAILED,
						cpu, start, len0, prot, addr,
						memlock_range_ulong_field(changed,
							range_start_offset),
						memlock_range_ulong_field(range,
							range_end_offset),
						memlock_range_ulong_field(range,
							range_flag_offset),
						protflags, 0, error);
				changed = range;
			}
		}
	}

	error = 0;
out:
	if (flush_tlb_fn)
		flush_tlb_fn();
	if (ro_changed && !error) {
		error = set_host_vma_fn ? set_host_vma_fn(start, len,
				prot & (PROT_READ | PROT_WRITE | PROT_EXEC),
				1) : -EINVAL;
		if (error)
			mprotect_log_emit(log_fn,
					MPROTECT_LOG_SET_HOST_FAILED, cpu,
					start, len0, prot, 0, 0, 0, 0,
					protflags, 0, error);
	}
	if (unlock_fn)
		unlock_fn(range_lock);

out_straight:
	mprotect_log_emit(log_fn, MPROTECT_LOG_EXIT, cpu, start, len0, prot,
			0, 0, 0, 0, protflags, 0, error);
	return error;
}

SYSCALL_POLICY_HELPER_SCOPE int
mlockall_policy_result(int flags, int is_privileged, unsigned long memlock_cur)
{
	if (!flags || (flags & ~(MCL_CURRENT | MCL_FUTURE))) {
		return -EINVAL;
	}
	if (is_privileged) {
		return 0;
	}
	if (memlock_cur != 0) {
		return -ENOMEM;
	}
	return -EPERM;
}

SYSCALL_POLICY_HELPER_SCOPE int
remap_file_pages_prepare(uintptr_t start0, size_t size, int prot,
		size_t pgoff, uintptr_t *startp, uintptr_t *endp, off_t *offp)
{
#define PGOFF_LIMIT ((off_t)1 << ((8 * sizeof(off_t) - 1) - PAGE_SHIFT))
	uintptr_t start = start0 & PAGE_MASK;
	uintptr_t end = start + size;
	off_t off = (off_t)pgoff << PAGE_SHIFT;

	*startp = start;
	*endp = end;
	*offp = off;
	if ((size <= 0) || (size & (PAGE_SIZE - 1)) || (prot != 0)
			|| (PGOFF_LIMIT <= pgoff)
			|| ((PGOFF_LIMIT - pgoff) < (size / PAGE_SIZE))
			|| !((start < end) || (end == 0))) {
		return -EINVAL;
	}

	return 0;
#undef PGOFF_LIMIT
}

static void
remap_file_pages_log_emit(remap_file_pages_log_fn_t log_fn, int event,
		int cpu, unsigned long start0, size_t size, int prot,
		size_t pgoff, int flags, unsigned long start, unsigned long end,
		unsigned long range_start, unsigned long range_end,
		unsigned long range_flags, void *memobj, off_t off, int error)
{
	struct remap_file_pages_log_record record = {
		.event = event,
		.cpu = cpu,
		.start0 = start0,
		.size = size,
		.prot = prot,
		.pgoff = pgoff,
		.flags = flags,
		.start = start,
		.end = end,
		.range_start = range_start,
		.range_end = range_end,
		.range_flags = range_flags,
		.memobj = memobj,
		.off = off,
		.error = error,
	};

	if (log_fn)
		log_fn(&record);
}

SYSCALL_POLICY_HELPER_SCOPE int
remap_file_pages_body_result(void *vm_arg, void *range_lock,
		unsigned long start0, size_t size, int prot, size_t pgoff,
		int flags, int cpu, size_t range_start_offset,
		size_t range_end_offset, size_t range_flag_offset,
		size_t range_memobj_offset, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		remap_file_pages_callable_fn_t callable_fn,
		remap_file_pages_remap_fn_t remap_fn,
		remap_file_pages_clear_host_fn_t clear_host_fn,
		memlock_populate_fn_t populate_fn,
		mprotect_flush_fn_t flush_nfo_fn,
		remap_file_pages_log_fn_t log_fn)
{
	struct process_vm *vm = vm_arg;
	uintptr_t start = 0;
	uintptr_t end = 0;
	off_t off = 0;
	struct vm_range *range = NULL;
	void *memobj = NULL;
	int error;
	int er;
	int need_populate = 0;

	remap_file_pages_log_emit(log_fn, REMAP_FILE_PAGES_LOG_ENTER, cpu,
			start0, size, prot, pgoff, flags, 0, 0, 0, 0, 0,
			NULL, 0, 0);

	if (lock_fn)
		lock_fn(range_lock);

	error = remap_file_pages_prepare(start0, size, prot, pgoff,
			&start, &end, &off);
	if (error) {
		remap_file_pages_log_emit(log_fn,
				REMAP_FILE_PAGES_LOG_INVALID_ARGS, cpu,
				start0, size, prot, pgoff, flags, start, end,
				0, 0, 0, NULL, off, error);
		goto out;
	}

	range = lookup_fn ? lookup_fn(vm, start, end) : NULL;
	if (range)
		memobj = memlock_range_ptr_field(range, range_memobj_offset);
	if (!range || start < memlock_range_ulong_field(range,
				range_start_offset)
			|| memlock_range_ulong_field(range,
				range_end_offset) < end
			|| (memlock_range_ulong_field(range,
				range_flag_offset) & VR_PRIVATE)
			|| range_has_disallowed_change_flags(
				memlock_range_ulong_field(range,
					range_flag_offset))
			|| !(callable_fn && callable_fn(memobj))) {
		remap_file_pages_log_emit(log_fn,
				REMAP_FILE_PAGES_LOG_INVALID_VMR, cpu,
				start0, size, prot, pgoff, flags, start, end,
				range ? memlock_range_ulong_field(range,
					range_start_offset) : 0,
				range ? memlock_range_ulong_field(range,
					range_end_offset) : 0,
				range ? memlock_range_ulong_field(range,
					range_flag_offset) : 0,
				memobj, off, -EINVAL);
		error = -EINVAL;
		goto out;
	}

	if (flush_nfo_fn)
		flush_nfo_fn();

	memlock_range_set_ulong_field(range, range_flag_offset,
			memlock_range_ulong_field(range, range_flag_offset) |
			VR_FILEOFF);
	error = remap_fn ? remap_fn(vm, range, start, end, off) : -EINVAL;
	if (error) {
		remap_file_pages_log_emit(log_fn,
				REMAP_FILE_PAGES_LOG_REMAP_FAILED, cpu,
				start0, size, prot, pgoff, flags, start, end,
				memlock_range_ulong_field(range,
					range_start_offset),
				memlock_range_ulong_field(range,
					range_end_offset),
				memlock_range_ulong_field(range,
					range_flag_offset),
				memobj, off, error);
		goto out;
	}
	if (clear_host_fn)
		clear_host_fn(start, size, 1);

	if (memlock_range_ulong_field(range, range_flag_offset) & VR_LOCKED)
		need_populate = 1;
	error = 0;
out:
	if (unlock_fn)
		unlock_fn(range_lock);

	if (need_populate) {
		er = populate_fn ? populate_fn(vm, start, size) : -EINVAL;
		if (er)
			remap_file_pages_log_emit(log_fn,
					REMAP_FILE_PAGES_LOG_POPULATE_FAILED,
					cpu, start0, size, prot, pgoff, flags,
					start, end,
					range ? memlock_range_ulong_field(range,
						range_start_offset) : 0,
					range ? memlock_range_ulong_field(range,
						range_end_offset) : 0,
					range ? memlock_range_ulong_field(range,
						range_flag_offset) : 0,
					memobj, off, er);
	}

	remap_file_pages_log_emit(log_fn, REMAP_FILE_PAGES_LOG_EXIT, cpu,
			start0, size, prot, pgoff, flags, start, end,
			range ? memlock_range_ulong_field(range,
				range_start_offset) : 0,
			range ? memlock_range_ulong_field(range,
				range_end_offset) : 0,
			range ? memlock_range_ulong_field(range,
				range_flag_offset) : 0,
			memobj, off, error);
	return error;
}

SYSCALL_POLICY_HELPER_SCOPE int
mremap_prepare_args(uintptr_t oldaddr, size_t oldsize0,
		size_t newsize0, int flags, uintptr_t newaddr,
		uintptr_t user_start, uintptr_t user_end,
		size_t *oldsizep, size_t *newsizep, uintptr_t *oldendp,
		int *no_opp)
{
	size_t oldsize = (oldsize0 + PAGE_SIZE - 1) & PAGE_MASK;
	size_t newsize = (newsize0 + PAGE_SIZE - 1) & PAGE_MASK;
	uintptr_t oldend = oldaddr + oldsize;

	*oldsizep = oldsize;
	*newsizep = newsize;
	*oldendp = oldend;
	*no_opp = 0;
	if ((oldaddr & ~PAGE_MASK)
			|| (newsize == 0)
			|| (flags & ~(MREMAP_MAYMOVE | MREMAP_FIXED))
			|| ((flags & MREMAP_FIXED)
				&& !(flags & MREMAP_MAYMOVE))
			|| ((flags & MREMAP_FIXED)
				&& (newaddr & ~PAGE_MASK))) {
		return -EINVAL;
	}

	if (!(flags & MREMAP_FIXED) && oldsize == newsize) {
		*no_opp = 1;
		return 0;
	}

	if (oldend < oldaddr) {
		return -EINVAL;
	}

	if (newsize > (user_end - user_start)) {
		return -ENOMEM;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
mremap_fixed_range_result(uintptr_t newstart, uintptr_t user_start,
		uintptr_t oldstart, uintptr_t oldend, uintptr_t newend)
{
	if (newstart < user_start) {
		return -EPERM;
	}
	if ((newstart < oldend) && (oldstart < newend)) {
		return -EINVAL;
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
mremap_maymove_result(int flags)
{
	return (flags & MREMAP_MAYMOVE) ? 0 : -ENOMEM;
}

static void
mremap_log_emit(mremap_log_fn_t log_fn, int event, unsigned long oldaddr,
		size_t oldsize0, size_t newsize0, int flags,
		unsigned long newaddr, unsigned long oldstart,
		unsigned long oldend, unsigned long newstart,
		unsigned long newend, unsigned long range_start,
		unsigned long range_end, unsigned long range_flags,
		unsigned long lckstart, unsigned long lckend, int error)
{
	struct mremap_log_record record = {
		.event = event,
		.oldaddr = oldaddr,
		.oldsize0 = oldsize0,
		.newsize0 = newsize0,
		.flags = flags,
		.newaddr = newaddr,
		.oldstart = oldstart,
		.oldend = oldend,
		.newstart = newstart,
		.newend = newend,
		.range_start = range_start,
		.range_end = range_end,
		.range_flags = range_flags,
		.lckstart = lckstart,
		.lckend = lckend,
		.error = error,
	};

	if (log_fn)
		log_fn(&record);
}

SYSCALL_POLICY_HELPER_SCOPE long
mremap_body_result(void *vm_arg, void *range_lock, void *pte_lock,
		void *page_table, unsigned long oldaddr, size_t oldsize0,
		size_t newsize0, int flags, unsigned long newaddr,
		unsigned long user_start, unsigned long user_end,
		unsigned long straight_va, size_t straight_len,
		size_t range_start_offset, size_t range_end_offset,
		size_t range_flag_offset, size_t range_pgshift_offset,
		size_t range_memobj_offset, size_t range_objoff_offset,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		mremap_extend_fn_t extend_fn, mprotect_flush_fn_t flush_nfo_fn,
		mremap_search_fn_t search_fn, munmap_do_fn_t munmap_fn,
		mremap_memobj_ref_fn_t memobj_ref_fn,
		mremap_memobj_ref_fn_t memobj_unref_fn,
		mremap_add_range_fn_t add_range_fn,
		syscall_rwlock_fn_t pte_lock_fn,
		syscall_rwlock_fn_t pte_unlock_fn,
		memlock_split_fn_t split_fn, mremap_move_pte_fn_t move_pte_fn,
		memlock_populate_fn_t populate_fn, mremap_log_fn_t log_fn)
{
	struct process_vm *vm = vm_arg;
	size_t oldsize;
	size_t newsize;
	unsigned long oldstart = oldaddr;
	uintptr_t oldend = 0;
	struct vm_range *range = NULL;
	int error;
	int no_op;
	int need_relocate = 0;
	unsigned long newstart = 0;
	unsigned long newend = 0;
	size_t size;
	unsigned long ret;
	unsigned long lckstart = (unsigned long)-1;
	unsigned long lckend = (unsigned long)-1;
	void *memobj;
	unsigned long objoff;

	mremap_log_emit(log_fn, MREMAP_LOG_ENTER, oldaddr, oldsize0,
			newsize0, flags, newaddr, oldstart, oldend, newstart,
			newend, 0, 0, 0, lckstart, lckend, 0);

	if (straight_va && oldaddr >= straight_va &&
			oldaddr < straight_va + straight_len) {
		error = -EINVAL;
		mremap_log_emit(log_fn, MREMAP_LOG_STRAIGHT_REJECT, oldaddr,
				oldsize0, newsize0, flags, newaddr, oldstart,
				oldend, newstart, newend, straight_va,
				straight_va + straight_len, 0, lckstart,
				lckend, error);
		return error;
	}

	if (lock_fn)
		lock_fn(range_lock);

	error = mremap_prepare_args(oldaddr, oldsize0, newsize0, flags,
			newaddr, user_start, user_end, &oldsize, &newsize,
			&oldend, &no_op);
	if (error == -EINVAL) {
		mremap_log_emit(log_fn, MREMAP_LOG_INVALID, oldaddr, oldsize0,
				newsize0, flags, newaddr, oldstart, oldend,
				newstart, newend, 0, 0, 0, lckstart, lckend,
				error);
		goto out;
	}
	if (error == -ENOMEM) {
		mremap_log_emit(log_fn, MREMAP_LOG_ALLOCATE_FAILED, oldaddr,
				oldsize0, newsize0, flags, newaddr, oldstart,
				oldend, newstart, newend, 0, 0, 0, lckstart,
				lckend, error);
		goto out;
	}
	if (no_op) {
		error = 0;
		newstart = oldaddr;
		goto out;
	}

	range = lookup_fn ? lookup_fn(vm, oldstart, oldstart + PAGE_SIZE) :
		NULL;
	if (!range || oldstart < memlock_range_ulong_field(range,
				range_start_offset)
			|| memlock_range_ulong_field(range,
				range_end_offset) < oldend
			|| (memlock_range_ulong_field(range,
				range_flag_offset) & VR_FILEOFF)
			|| range_has_disallowed_change_flags(
				memlock_range_ulong_field(range,
					range_flag_offset))) {
		error = -EFAULT;
		mremap_log_emit(log_fn, MREMAP_LOG_LOOKUP_FAILED, oldaddr,
				oldsize0, newsize0, flags, newaddr, oldstart,
				oldend, newstart, newend,
				range ? memlock_range_ulong_field(range,
					range_start_offset) : 0,
				range ? memlock_range_ulong_field(range,
					range_end_offset) : 0,
				range ? memlock_range_ulong_field(range,
					range_flag_offset) : 0,
				lckstart, lckend, error);
		goto out;
	}

	if (flags & MREMAP_FIXED) {
		need_relocate = 1;
		newstart = newaddr;
		newend = newstart + newsize;
		error = mremap_fixed_range_result(newstart, user_start,
				oldstart, oldend, newend);
		if (error == -EPERM) {
			mremap_log_emit(log_fn, MREMAP_LOG_FIXED_MIN_ADDR,
					oldaddr, oldsize0, newsize0, flags,
					newaddr, oldstart, oldend, newstart,
					newend, user_start, 0, 0, lckstart,
					lckend, error);
			goto out;
		}
		if (error == -EINVAL) {
			mremap_log_emit(log_fn, MREMAP_LOG_FIXED_OVERLAP,
					oldaddr, oldsize0, newsize0, flags,
					newaddr, oldstart, oldend, newstart,
					newend, 0, 0, 0, lckstart, lckend,
					error);
			goto out;
		}
	}
	else if (oldsize < newsize) {
		if (oldend == memlock_range_ulong_field(range,
					range_end_offset)) {
			newstart = oldstart;
			newend = newstart + newsize;
			error = extend_fn ? extend_fn(vm, range, newend) :
				-EINVAL;
			if (flush_nfo_fn)
				flush_nfo_fn();
			if (!error) {
				if (memlock_range_ulong_field(range,
						range_flag_offset) & VR_LOCKED) {
					lckstart = oldend;
					lckend = newend;
				}
				goto out;
			}
		}
		error = mremap_maymove_result(flags);
		if (error) {
			mremap_log_emit(log_fn, MREMAP_LOG_CANNOT_RELOCATE,
					oldaddr, oldsize0, newsize0, flags,
					newaddr, oldstart, oldend, newstart,
					newend, 0, 0, 0, lckstart, lckend,
					error);
			goto out;
		}
		need_relocate = 1;
		error = search_fn ? search_fn(newsize,
				memlock_range_ulong_field(range,
					range_pgshift_offset), &newstart) :
			-EINVAL;
		if (error) {
			mremap_log_emit(log_fn, MREMAP_LOG_SEARCH_FAILED,
					oldaddr, oldsize0, newsize0, flags,
					newaddr, oldstart, oldend, newstart,
					newend, 0, 0, 0, lckstart, lckend,
					error);
			goto out;
		}
		newend = newstart + newsize;
	}
	else {
		newstart = oldstart;
		newend = newstart + newsize;
	}

	if (need_relocate) {
		if (flags & MREMAP_FIXED) {
			error = munmap_fn ? munmap_fn((void *)newstart,
					newsize, 1) : -EINVAL;
			if (error) {
				mremap_log_emit(log_fn,
						MREMAP_LOG_FIXED_MUNMAP_FAILED,
						oldaddr, oldsize0, newsize0,
						flags, newaddr, oldstart, oldend,
						newstart, newend, 0, 0, 0,
						lckstart, lckend, error);
				goto out;
			}
		}
		memobj = memlock_range_ptr_field(range, range_memobj_offset);
		if (memobj && memobj_ref_fn)
			memobj_ref_fn(memobj);
		objoff = memlock_range_ulong_field(range, range_objoff_offset) +
			(oldstart - memlock_range_ulong_field(range,
				range_start_offset));
		error = add_range_fn ? add_range_fn(vm, newstart, newend, -1,
				memlock_range_ulong_field(range,
					range_flag_offset),
				memobj, objoff) : -EINVAL;
		if (error) {
			mremap_log_emit(log_fn, MREMAP_LOG_ADD_FAILED, oldaddr,
					oldsize0, newsize0, flags, newaddr,
					oldstart, oldend, newstart, newend,
					memlock_range_ulong_field(range,
						range_start_offset),
					memlock_range_ulong_field(range,
						range_end_offset),
					memlock_range_ulong_field(range,
						range_flag_offset),
					lckstart, lckend, error);
			if (memobj && memobj_unref_fn)
				memobj_unref_fn(memobj);
			goto out;
		}
		if (flush_nfo_fn)
			flush_nfo_fn();
		if (memlock_range_ulong_field(range, range_flag_offset) &
				VR_LOCKED) {
			lckstart = newstart;
			lckend = newend;
		}

		if (oldsize > 0) {
			size = (oldsize < newsize) ? oldsize : newsize;
			if (pte_lock_fn)
				pte_lock_fn(pte_lock);
			if (memlock_range_ulong_field(range,
					range_start_offset) != oldstart) {
				error = split_fn ? split_fn(vm, range,
						oldstart, &range) : -EINVAL;
				if (error) {
					if (pte_unlock_fn)
						pte_unlock_fn(pte_lock);
					mremap_log_emit(log_fn,
							MREMAP_LOG_SPLIT_FAILED,
							oldaddr, oldsize0,
							newsize0, flags,
							newaddr, oldstart,
							oldend, newstart,
							newend, 0, 0, 0,
							lckstart, lckend,
							error);
					goto out;
				}
			}
			if (memlock_range_ulong_field(range,
					range_end_offset) != oldstart + size) {
				error = split_fn ? split_fn(vm, range,
						oldstart + size, NULL) :
					-EINVAL;
				if (error) {
					if (pte_unlock_fn)
						pte_unlock_fn(pte_lock);
					mremap_log_emit(log_fn,
							MREMAP_LOG_SPLIT_FAILED,
							oldaddr, oldsize0,
							newsize0, flags,
							newaddr, oldstart,
							oldend, newstart,
							newend, 0, 0, 0,
							lckstart, lckend,
							error);
					goto out;
				}
			}
			error = move_pte_fn ? move_pte_fn(page_table, vm,
					(void *)oldstart, (void *)newstart,
					size, range) : -EINVAL;
			if (pte_unlock_fn)
				pte_unlock_fn(pte_lock);
			if (error) {
				mremap_log_emit(log_fn, MREMAP_LOG_MOVE_FAILED,
						oldaddr, oldsize0, newsize0,
						flags, newaddr, oldstart,
						oldend, newstart, newend, 0, 0,
						0, lckstart, lckend, error);
				goto out;
			}

			error = munmap_fn ? munmap_fn((void *)oldstart,
					oldsize, 1) : -EINVAL;
			if (error) {
				mremap_log_emit(log_fn,
						MREMAP_LOG_RELOCATE_MUNMAP_FAILED,
						oldaddr, oldsize0, newsize0,
						flags, newaddr, oldstart, oldend,
						newstart, newend, 0, 0, 0,
						lckstart, lckend, error);
				goto out;
			}
		}
	}
	else if (newsize < oldsize) {
		error = munmap_fn ? munmap_fn((void *)newend,
				oldend - newend, 1) : -EINVAL;
		if (error) {
			mremap_log_emit(log_fn, MREMAP_LOG_SHRINK_MUNMAP_FAILED,
					oldaddr, oldsize0, newsize0, flags,
					newaddr, oldstart, oldend, newstart,
					newend, 0, 0, 0, lckstart, lckend,
					error);
			goto out;
		}
	}
	error = 0;
out:
	if (unlock_fn)
		unlock_fn(range_lock);
	if (!error && lckstart < lckend) {
		error = populate_fn ? populate_fn(vm, lckstart,
				lckend - lckstart) : -EINVAL;
		if (error) {
			mremap_log_emit(log_fn, MREMAP_LOG_POPULATE_FAILED,
					oldaddr, oldsize0, newsize0, flags,
					newaddr, oldstart, oldend, newstart,
					newend, 0, 0, 0, lckstart, lckend,
					error);
			error = 0;
		}
	}
	ret = error ? (unsigned long)error : newstart;
	mremap_log_emit(log_fn, MREMAP_LOG_EXIT, oldaddr, oldsize0, newsize0,
			flags, newaddr, oldstart, oldend, newstart, newend,
			range ? memlock_range_ulong_field(range,
				range_start_offset) : 0,
			range ? memlock_range_ulong_field(range,
				range_end_offset) : 0,
			range ? memlock_range_ulong_field(range,
				range_flag_offset) : 0,
			lckstart, lckend, error);
	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE int
msync_prepare_range(uintptr_t start0, size_t len0, int flags,
		size_t *lenp, uintptr_t *endp)
{
	size_t len = (len0 + PAGE_SIZE - 1) & PAGE_MASK;
	uintptr_t end = start0 + len;

	*lenp = len;
	*endp = end;
	if ((start0 & ~PAGE_MASK)
			|| (flags & ~(MS_ASYNC | MS_INVALIDATE | MS_SYNC))
			|| ((flags & MS_ASYNC) && (flags & MS_SYNC))) {
		return -EINVAL;
	}
	if (end < start0) {
		return -ENOMEM;
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
msync_locked_range_result(int flags, unsigned long range_flags)
{
	return ((flags & MS_INVALIDATE) && (range_flags & VR_LOCKED)) ?
		-EBUSY : 0;
}

static unsigned long
msync_range_ulong_field(struct vm_range *range, size_t offset)
{
	return *(unsigned long *)((char *)range + offset);
}

static void *
msync_range_ptr_field(struct vm_range *range, size_t offset)
{
	return *(void **)((char *)range + offset);
}

SYSCALL_POLICY_HELPER_SCOPE int
msync_body_result(void *vm_arg, void *range_lock, unsigned long start0,
		size_t len0, int flags, size_t range_start_offset,
		size_t range_end_offset, size_t range_flag_offset,
		size_t range_memobj_offset, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		syscall_next_range_fn_t next_fn,
		msync_memobj_has_pager_fn_t has_pager_fn,
		msync_range_op_fn_t sync_fn, msync_range_op_fn_t invalidate_fn,
		msync_log_fn_t log_fn)
{
	struct process_vm *vm = vm_arg;
	size_t len;
	uintptr_t end;
	unsigned long addr;
	struct vm_range *range = NULL;
	int error;

	if (log_fn)
		log_fn(MSYNC_LOG_ENTER, start0, len0, flags, 0);
	if (lock_fn)
		lock_fn(range_lock);

	error = msync_prepare_range(start0, len0, flags, &len, &end);
	if (error) {
		if (log_fn)
			log_fn(MSYNC_LOG_INVALID_ARGS, start0, len0, flags, error);
		goto out;
	}

	for (addr = start0; addr < end;
			addr = msync_range_ulong_field(range, range_end_offset)) {
		if (!range)
			range = lookup_fn ? lookup_fn(vm, addr, addr + PAGE_SIZE) : NULL;
		else
			range = next_fn ? next_fn(vm, range) : NULL;

		if (!range || (addr < msync_range_ulong_field(range, range_start_offset))) {
			error = -ENOMEM;
			if (log_fn)
				log_fn(MSYNC_LOG_INVALID_VMR, start0, len0, flags, error);
			goto out;
		}
		error = msync_locked_range_result(flags,
				msync_range_ulong_field(range, range_flag_offset));
		if (error) {
			if (log_fn)
				log_fn(MSYNC_LOG_LOCKED_VMR, start0, len0, flags, error);
			goto out;
		}
	}

	range = NULL;
	for (addr = start0; addr < end;
			addr = msync_range_ulong_field(range, range_end_offset)) {
		unsigned long range_end;
		unsigned long range_flag;
		void *memobj;
		unsigned long s;
		unsigned long e;

		if (!range)
			range = lookup_fn ? lookup_fn(vm, addr, addr + PAGE_SIZE) : NULL;
		else
			range = next_fn ? next_fn(vm, range) : NULL;
		if (!range) {
			error = -ENOMEM;
			if (log_fn)
				log_fn(MSYNC_LOG_INVALID_VMR, start0, len0, flags, error);
			goto out;
		}

		range_end = msync_range_ulong_field(range, range_end_offset);
		range_flag = msync_range_ulong_field(range, range_flag_offset);
		memobj = msync_range_ptr_field(range, range_memobj_offset);
		if ((range_flag & VR_PRIVATE) || !memobj
				|| !(has_pager_fn && has_pager_fn(memobj))) {
			if (log_fn)
				log_fn(MSYNC_LOG_UNSYNCABLE_VMR, start0, len0, flags, 0);
			continue;
		}

		s = addr;
		e = (range_end < end) ? range_end : end;
		if (flags & (MS_ASYNC | MS_SYNC)) {
			error = sync_fn ? sync_fn(vm, range, s, e) : -EINVAL;
			if (error) {
				if (log_fn)
					log_fn(MSYNC_LOG_SYNC_FAILED, start0, len0,
							flags, error);
				goto out;
			}
		}
		if (flags & MS_INVALIDATE) {
			error = invalidate_fn ? invalidate_fn(vm, range, s, e) : -EINVAL;
			if (error) {
				if (log_fn)
					log_fn(MSYNC_LOG_INVALIDATE_FAILED, start0,
							len0, flags, error);
				goto out;
			}
		}
	}

	error = 0;
out:
	if (unlock_fn)
		unlock_fn(range_lock);
	if (log_fn)
		log_fn(MSYNC_LOG_EXIT, start0, len0, flags, error);
	return error;
}

SYSCALL_POLICY_HELPER_SCOPE int
mbind_prepare_range(uintptr_t addr, unsigned long len0, unsigned long *lenp)
{
	unsigned long len;

	if (addr & ~PAGE_MASK) {
		return -EINVAL;
	}

	len = (len0 + PAGE_SIZE - 1) & PAGE_MASK;
	*lenp = len;
	if (addr + len < addr || addr == (addr + len)) {
		return -EINVAL;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
mempolicy_nodemask_bits_result(unsigned long maxnode,
		unsigned long *nodemask_bitsp)
{
	unsigned long nodemask_bits = 0;

	if (maxnode) {
		nodemask_bits = ihk_align(maxnode, 8);
		if (maxnode > (PAGE_SIZE << 3)) {
			*nodemask_bitsp = nodemask_bits;
			return -EINVAL;
		}

		if (nodemask_bits > PROCESS_NUMA_MASK_BITS) {
			nodemask_bits = PROCESS_NUMA_MASK_BITS;
		}
	}

	*nodemask_bitsp = nodemask_bits;
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
mempolicy_nodemask_bits_is_clamped(unsigned long maxnode)
{
	return maxnode && (ihk_align(maxnode, 8) > PROCESS_NUMA_MASK_BITS);
}

SYSCALL_POLICY_HELPER_SCOPE int
mbind_mode_flags_result(int mode, unsigned int flags,
		int *mode_flagsp, int *normalized_modep)
{
	int mode_flags;

	if ((mode & MPOL_F_STATIC_NODES) && (mode & MPOL_F_RELATIVE_NODES)) {
		return -EINVAL;
	}

	if ((flags & MPOL_MF_STRICT) && (flags & MPOL_MF_MOVE)) {
		return -EINVAL;
	}

	mode_flags = mode & MPOL_MODE_FLAGS;
	*mode_flagsp = mode_flags;
	*normalized_modep = mode & ~MPOL_MODE_FLAGS;
	if (mode_flags & MPOL_F_RELATIVE_NODES) {
		return -EINVAL;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
mempolicy_mode_is_supported(int mode)
{
	return mode == MPOL_DEFAULT || mode == MPOL_BIND ||
		mode == MPOL_INTERLEAVE || mode == MPOL_PREFERRED;
}

SYSCALL_POLICY_HELPER_SCOPE int
set_mempolicy_normalize_mode(int mode, int *normalized_modep)
{
	if ((mode & MPOL_F_STATIC_NODES) &&
	    (mode & MPOL_F_RELATIVE_NODES)) {
		return -EINVAL;
	}
	*normalized_modep = mode & ~MPOL_MODE_FLAGS;
	return 0;
}

static void
set_mempolicy_log_optional(syscall_set_mempolicy_log_fn_t log_fn, int event,
		int value, int pid)
{
	if (log_fn) {
		log_fn(event, value, pid);
	}
}

static void
set_mempolicy_mask_set(unsigned long *mask, int bit)
{
	int word_bits = sizeof(unsigned long) * 8;

	mask[bit / word_bits] |= 1UL << (bit % word_bits);
}

static void
set_mempolicy_mask_clear(unsigned long *mask, int bit)
{
	int word_bits = sizeof(unsigned long) * 8;

	mask[bit / word_bits] &= ~(1UL << (bit % word_bits));
}

static int
set_mempolicy_mask_test(const unsigned long *mask, int bit)
{
	int word_bits = sizeof(unsigned long) * 8;

	return !!(mask[bit / word_bits] & (1UL << (bit % word_bits)));
}

static int
set_mempolicy_mask_empty(const unsigned long *mask, unsigned long bits)
{
	unsigned long bit;

	if (bits > PROCESS_NUMA_MASK_BITS) {
		bits = PROCESS_NUMA_MASK_BITS;
	}
	for (bit = 0; bit < bits; ++bit) {
		if (set_mempolicy_mask_test(mask, bit)) {
			return 0;
		}
	}
	return 1;
}

static void
set_mempolicy_mask_copy(unsigned long *dst, const unsigned long *src)
{
	int i;

	for (i = 0; i < (PROCESS_NUMA_MASK_BITS / (sizeof(unsigned long) * 8));
			++i) {
		dst[i] = src[i];
	}
}

static void
mbind_log_optional(syscall_mbind_log_fn_t log_fn, int event,
		unsigned long arg0, unsigned long arg1, int arg2)
{
	if (log_fn) {
		log_fn(event, arg0, arg1, arg2);
	}
}

SYSCALL_POLICY_HELPER_SCOPE long
mbind_body_result(unsigned long addr, unsigned long len0, int mode,
		unsigned long nodemask_addr, unsigned long maxnode, int flags,
		struct process_vm *vm, int straight_va, int fugaku_hacks,
		int nr_numa_nodes, size_t policy_size, unsigned long alloc_flags,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_rwlock_fn_t write_lock_fn,
		syscall_rwlock_fn_t write_unlock_fn,
		syscall_lookup_range_fn_t lookup_range_fn,
		syscall_policy_search_fn_t policy_search_fn,
		syscall_policy_clear_range_fn_t clear_range_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_policy_rb_clear_fn_t rb_clear_fn,
		syscall_policy_insert_fn_t insert_fn,
		syscall_mbind_log_fn_t log_fn)
{
	unsigned long nodemask_bits = 0;
	unsigned long len = len0;
	unsigned long numa_mask[(((PROCESS_NUMA_MASK_BITS) + BITS_PER_LONG - 1) / BITS_PER_LONG)];
	int mode_flags = 0;
	int error = 0;
	int bit;
	struct vm_range *range;
	struct vm_range_numa_policy *range_policy;
	uintptr_t end;

	if (straight_va) {
		return 0;
	}
	if (!vm) {
		return -EFAULT;
	}

	error = mbind_prepare_range(addr, len0, &len);
	if (error) {
		return error;
	}

	if (fugaku_hacks) {
		return 0;
	}

	memset(numa_mask, 0, sizeof(numa_mask));

	error = mempolicy_nodemask_bits_result(maxnode, &nodemask_bits);
	if (error) {
		mbind_log_optional(log_fn, MBIND_LOG_NODEMASK_BITS_TOO_BIG,
				addr, maxnode, error);
		return error;
	}
	if (mempolicy_nodemask_bits_is_clamped(maxnode)) {
		mbind_log_optional(log_fn, MBIND_LOG_CLAMPED, addr, maxnode,
				0);
	}

	error = mbind_mode_flags_result(mode, flags, &mode_flags, &mode);
	if (error) {
		mbind_log_optional(log_fn, MBIND_LOG_INVALID_MODE_FLAGS,
				addr, flags, error);
		return error;
	}
	if (!mempolicy_mode_is_supported(mode)) {
		return -EINVAL;
	}

	switch (mode) {
	case MPOL_DEFAULT:
		if (nodemask_addr && nodemask_bits) {
			if (!copy_from_fn) {
				return -EINVAL;
			}
			error = copy_from_fn(numa_mask, nodemask_addr,
					(nodemask_bits >> 3));
			if (error) {
				mbind_log_optional(log_fn,
						MBIND_LOG_COPY_FROM_NUMA_MASK,
						addr, nodemask_addr, 0);
				return -EFAULT;
			}

			if (!set_mempolicy_mask_empty(numa_mask, nodemask_bits)) {
				mbind_log_optional(log_fn,
						MBIND_LOG_DEFAULT_MASK_NOT_EMPTY,
						addr, nodemask_addr, 0);
				return -EINVAL;
			}
		}
		break;

	case MPOL_BIND:
	case MPOL_INTERLEAVE:
	case MPOL_PREFERRED:
		if (mode == MPOL_PREFERRED && !nodemask_addr) {
			break;
		}

		if (flags & MPOL_MF_STRICT) {
			return -EIO;
		}

		if (!copy_from_fn) {
			return -EINVAL;
		}
		error = copy_from_fn(numa_mask, nodemask_addr,
				(nodemask_bits >> 3));
		if (error) {
			return -EFAULT;
		}

		if (!nodemask_addr ||
		    set_mempolicy_mask_empty(numa_mask, nodemask_bits)) {
			mbind_log_optional(log_fn,
					MBIND_LOG_NODEMASK_NOT_SPECIFIED,
					addr, nodemask_addr, 0);
			return -EINVAL;
		}

		for (bit = 0; bit < (maxnode < PROCESS_NUMA_MASK_BITS ?
				maxnode : PROCESS_NUMA_MASK_BITS); ++bit) {
			if (!set_mempolicy_mask_test(numa_mask, bit)) {
				continue;
			}
			if (bit >= nr_numa_nodes) {
				mbind_log_optional(log_fn,
						MBIND_LOG_NODE_TOO_LARGE,
						addr, bit, 0);
				return -EINVAL;
			}
		}
		break;

	default:
		return -EINVAL;
	}

	if (!write_lock_fn || !write_unlock_fn || !lookup_range_fn ||
	    !policy_search_fn || !clear_range_fn || !alloc_fn ||
	    !rb_clear_fn || !insert_fn) {
		return -EINVAL;
	}

	write_lock_fn(&vm->memory_range_lock);

	end = addr + len;
	range = lookup_range_fn(vm, addr, end);
	if (!range) {
		mbind_log_optional(log_fn, MBIND_LOG_INVALID_RANGE, addr,
				end, 0);
		write_unlock_fn(&vm->memory_range_lock);
		return -EFAULT;
	}

	range_policy = policy_search_fn(vm, addr);
	if (!range_policy || range_policy->start != addr ||
	    range_policy->end != end) {
		error = clear_range_fn(vm, addr, end);
		if (error) {
			mbind_log_optional(log_fn, MBIND_LOG_CLEAR_POLICY_RANGE,
					addr, end, error);
			write_unlock_fn(&vm->memory_range_lock);
			return error;
		}

		range_policy = alloc_fn(policy_size, alloc_flags);
		if (!range_policy) {
			mbind_log_optional(log_fn, MBIND_LOG_ALLOC_POLICY, addr,
					end, 0);
			write_unlock_fn(&vm->memory_range_lock);
			return -ENOMEM;
		}

		rb_clear_fn(range_policy);
		range_policy->start = addr;
		range_policy->end = end;

		error = insert_fn(vm, range_policy);
		if (error) {
			mbind_log_optional(log_fn, MBIND_LOG_INSERT_POLICY,
					addr, end, error);
			write_unlock_fn(&vm->memory_range_lock);
			return error;
		}
	}

	if (mode == MPOL_DEFAULT) {
		memset(range_policy->numa_mask, 0, sizeof(numa_mask));
		for (bit = 0; bit < nr_numa_nodes &&
				bit < PROCESS_NUMA_MASK_BITS; ++bit) {
			set_mempolicy_mask_set(range_policy->numa_mask, bit);
		}
	}
	else {
		set_mempolicy_mask_copy(range_policy->numa_mask, numa_mask);
	}
	range_policy->numa_mem_policy = mode;
	if (mode == MPOL_INTERLEAVE) {
		range_policy->il_prev = PROCESS_NUMA_MASK_BITS - 1;
	}

	write_unlock_fn(&vm->memory_range_lock);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
set_mempolicy_body_result(int mode, unsigned long nodemask_addr,
		unsigned long maxnode, struct process_vm *vm, int nr_numa_nodes,
		int pid, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_set_mempolicy_log_fn_t log_fn)
{
	unsigned long nodemask_bits = 0;
	unsigned long numa_mask[(((PROCESS_NUMA_MASK_BITS) + BITS_PER_LONG - 1) / BITS_PER_LONG)];
	int error = 0;
	int bit;
	int valid_mask;

	if (!vm) {
		return -EFAULT;
	}

	memset(numa_mask, 0, sizeof(numa_mask));

	error = mempolicy_nodemask_bits_result(maxnode, &nodemask_bits);
	if (error) {
		set_mempolicy_log_optional(log_fn,
				SET_MEMPOLICY_LOG_NODEMASK_BITS_TOO_BIG, 0, pid);
		return error;
	}
	if (mempolicy_nodemask_bits_is_clamped(maxnode)) {
		set_mempolicy_log_optional(log_fn,
				SET_MEMPOLICY_LOG_CLAMPED, 0, pid);
	}

	error = set_mempolicy_normalize_mode(mode, &mode);
	if (error) {
		return error;
	}
	if (!mempolicy_mode_is_supported(mode)) {
		return -EINVAL;
	}

	switch (mode) {
	case MPOL_DEFAULT:
		if (nodemask_addr && nodemask_bits) {
			if (!copy_from_fn) {
				return -EINVAL;
			}
			error = copy_from_fn(numa_mask, nodemask_addr,
					(nodemask_bits >> 3));
			if (error) {
				return -EFAULT;
			}

			if (!set_mempolicy_mask_empty(numa_mask, nodemask_bits)) {
				set_mempolicy_log_optional(log_fn,
						SET_MEMPOLICY_LOG_DEFAULT_MASK_NOT_EMPTY,
						0, pid);
				return -EINVAL;
			}
		}

		memset(vm->numa_mask, 0, sizeof(numa_mask));
		for (bit = 0; bit < nr_numa_nodes &&
				bit < PROCESS_NUMA_MASK_BITS; ++bit) {
			set_mempolicy_mask_set(vm->numa_mask, bit);
		}

		vm->numa_mem_policy = mode;
		set_mempolicy_log_optional(log_fn, SET_MEMPOLICY_LOG_SET,
				mode, pid);
		return 0;

	case MPOL_BIND:
	case MPOL_INTERLEAVE:
	case MPOL_PREFERRED:
		if (mode == MPOL_PREFERRED && !nodemask_addr) {
			memset(vm->numa_mask, 0, sizeof(numa_mask));
			for (bit = 0; bit < nr_numa_nodes &&
					bit < PROCESS_NUMA_MASK_BITS; ++bit) {
				set_mempolicy_mask_set(vm->numa_mask, bit);
			}

			vm->numa_mem_policy = mode;
			set_mempolicy_log_optional(log_fn,
					SET_MEMPOLICY_LOG_SET, mode, pid);
			return 0;
		}

		if (!nodemask_addr) {
			set_mempolicy_log_optional(log_fn,
					SET_MEMPOLICY_LOG_NODEMASK_NOT_SPECIFIED,
					0, pid);
			return -EINVAL;
		}

		if (!copy_from_fn) {
			return -EINVAL;
		}
		error = copy_from_fn(numa_mask, nodemask_addr,
				(nodemask_bits >> 3));
		if (error) {
			return -EFAULT;
		}

		valid_mask = 0;
		for (bit = 0; bit < (maxnode < PROCESS_NUMA_MASK_BITS ?
				maxnode : PROCESS_NUMA_MASK_BITS); ++bit) {
			if (!set_mempolicy_mask_test(numa_mask, bit)) {
				continue;
			}
			if (bit >= nr_numa_nodes) {
				set_mempolicy_log_optional(log_fn,
						SET_MEMPOLICY_LOG_NODE_TOO_LARGE,
						bit, pid);
				return -EINVAL;
			}
			if (set_mempolicy_mask_test(vm->numa_mask, bit)) {
				valid_mask = 1;
			}
		}

		if (!valid_mask) {
			set_mempolicy_log_optional(log_fn,
					SET_MEMPOLICY_LOG_INVALID_NODEMASK, 0,
					pid);
			return -EINVAL;
		}

		for (bit = 0; bit < (maxnode < PROCESS_NUMA_MASK_BITS ?
				maxnode : PROCESS_NUMA_MASK_BITS); ++bit) {
			if (!set_mempolicy_mask_test(vm->numa_mask, bit)) {
				continue;
			}
			if (!set_mempolicy_mask_test(numa_mask, bit)) {
				set_mempolicy_mask_clear(vm->numa_mask, bit);
			}
		}

		vm->numa_mem_policy = mode;
		if (mode == MPOL_INTERLEAVE) {
			vm->il_prev = PROCESS_NUMA_MASK_BITS - 1;
		}
		set_mempolicy_log_optional(log_fn, SET_MEMPOLICY_LOG_SET,
				mode, pid);
		return 0;

	default:
		return -EINVAL;
	}
}

SYSCALL_POLICY_HELPER_SCOPE int
get_mempolicy_validate(unsigned long addr, int flags, int process_policy,
		unsigned long maxnode, int nr_numa_nodes,
		unsigned long *nodemask_bitsp)
{
	*nodemask_bitsp = 0;
	if ((!(flags & MPOL_F_ADDR) && addr) ||
		(flags & ~(MPOL_F_ADDR | MPOL_F_NODE | MPOL_F_MEMS_ALLOWED)) ||
		((flags & MPOL_F_NODE) && !(flags & MPOL_F_ADDR) &&
		 process_policy == MPOL_INTERLEAVE)) {
		return -EINVAL;
	}

	if ((flags & MPOL_F_ADDR) && !addr) {
		return -EFAULT;
	}

	if (maxnode) {
		if (maxnode < nr_numa_nodes) {
			return -EINVAL;
		}

		*nodemask_bitsp = ihk_align(maxnode, 8);
		if (*nodemask_bitsp > PROCESS_NUMA_MASK_BITS) {
			*nodemask_bitsp = PROCESS_NUMA_MASK_BITS;
		}
	}

	return 0;
}

#define GET_MEMPOLICY_LOG_CLAMPED 1
#define GET_MEMPOLICY_LOG_INVALID_RANGE 2

SYSCALL_POLICY_HELPER_SCOPE long
get_mempolicy_body_result(unsigned long mode_addr,
		unsigned long nodemask_addr, unsigned long maxnode,
		unsigned long addr, int flags, struct process_vm *vm,
		int nr_numa_nodes, syscall_copy_to_user_fn_t copy_to_fn,
		syscall_lookup_node_fn_t lookup_node_fn,
		syscall_rwlock_fn_t read_lock_fn,
		syscall_rwlock_fn_t read_unlock_fn,
		syscall_lookup_range_fn_t lookup_range_fn,
		syscall_policy_search_fn_t policy_search_fn,
		syscall_get_mempolicy_log_fn_t log_fn)
{
	struct vm_range_numa_policy *range_policy = NULL;
	unsigned long nodemask_bits = 0;
	int error;
	int policy;

	if (!vm) {
		return -EFAULT;
	}

	error = get_mempolicy_validate(addr, flags, vm->numa_mem_policy,
			maxnode, nr_numa_nodes, &nodemask_bits);
	if (error) {
		return error;
	}
	if (mempolicy_nodemask_bits_is_clamped(maxnode) && log_fn) {
		log_fn(GET_MEMPOLICY_LOG_CLAMPED, addr, (int)nodemask_bits);
	}

	if (!copy_to_fn) {
		return -EINVAL;
	}

	if ((flags & MPOL_F_NODE) && (flags & MPOL_F_ADDR)) {
		int nid;

		if (!lookup_node_fn) {
			return -EINVAL;
		}
		nid = lookup_node_fn(vm, (void *)addr);
		error = copy_to_fn(mode_addr, &nid, sizeof(nid));
		return error ? -EFAULT : 0;
	}

	if (flags == MPOL_F_MEMS_ALLOWED) {
		if (nodemask_addr) {
			error = copy_to_fn(nodemask_addr, vm->numa_mask,
					nodemask_bits >> 3);
			if (error) {
				return -EFAULT;
			}
		}
		return 0;
	}

	if (flags & MPOL_F_ADDR) {
		struct vm_range *range;

		if (!read_lock_fn || !read_unlock_fn || !lookup_range_fn ||
		    !policy_search_fn) {
			return -EINVAL;
		}

		read_lock_fn(&vm->memory_range_lock);
		range = lookup_range_fn(vm, addr, addr + 1);
		if (!range) {
			if (log_fn) {
				log_fn(GET_MEMPOLICY_LOG_INVALID_RANGE,
						addr, 0);
			}
			read_unlock_fn(&vm->memory_range_lock);
			return -EFAULT;
		}

		range_policy = policy_search_fn(vm, addr);
		read_unlock_fn(&vm->memory_range_lock);
	}

	policy = range_policy ? range_policy->numa_mem_policy :
		vm->numa_mem_policy;

	if (mode_addr) {
		error = copy_to_fn(mode_addr, &policy, sizeof(policy));
		if (error) {
			return -EFAULT;
		}
	}

	if (nodemask_addr && policy != MPOL_DEFAULT) {
		error = copy_to_fn(nodemask_addr,
				range_policy ? range_policy->numa_mask :
				vm->numa_mask, nodemask_bits >> 3);
		if (error) {
			return -EFAULT;
		}
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
move_pages_policy_result(int pid, int flags)
{
	if (pid) {
		return -EINVAL;
	}
	if ((flags & ~(MPOL_MF_MOVE | MPOL_MF_MOVE_ALL)) ||
			(flags & MPOL_MF_MOVE_ALL)) {
		return -EINVAL;
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
move_pages_smp_req_prepare_result(struct move_pages_smp_req *req,
		unsigned long count, const void **user_virt_addr,
		int *user_status, const int *user_nodes, void **virt_addr,
		int *status, pte_t **ptep, int *nodes, int *nr_pages,
		unsigned long *dst_phys, void *proc)
{
	if (!req) {
		return -EINVAL;
	}

	req->count = count;
	req->user_virt_addr = user_virt_addr;
	req->user_status = user_status;
	req->user_nodes = user_nodes;
	req->virt_addr = virt_addr;
	req->status = status;
	req->ptep = ptep;
	req->nodes = nodes;
	req->nodes_ready = 0;
	req->nr_pages = nr_pages;
	req->dst_phys = dst_phys;
	req->proc = proc;
	ihk_atomic_set(&req->phase_done, 0);
	req->phase_ret = 0;
	return 0;
}

static void
move_pages_free_arrays_c(syscall_mckfd_free_fn_t free_fn, void *virt_addr,
		void *nr_pages, void *nodes, void *status, void *ptep,
		void *dst_phys)
{
	if (!free_fn) {
		return;
	}

	free_fn(virt_addr);
	free_fn(nr_pages);
	free_fn(nodes);
	free_fn(status);
	free_fn(ptep);
	free_fn(dst_phys);
}

SYSCALL_POLICY_HELPER_SCOPE long
move_pages_body_result(int pid, unsigned long count,
		unsigned long user_virt_addr_addr, unsigned long user_nodes_addr,
		unsigned long user_status_addr, int flags, struct process_vm *vm,
		void *page_table_lock, void *cpu_set, void *proc,
		unsigned long alloc_flags, size_t ptr_size, size_t int_size,
		size_t pte_size, size_t ulong_size,
		move_pages_verify_fn_t verify_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn,
		move_pages_get_nr_nodes_fn_t get_nr_nodes_fn,
		syscall_rwlock_fn_t lock_fn, syscall_rwlock_fn_t unlock_fn,
		move_pages_smp_call_fn_t smp_call_fn, smp_func_t handler_fn,
		syscall_rdtsc_fn_t rdtsc_fn, move_pages_log_fn_t log_fn)
{
	const void **user_virt_addr = (const void **)user_virt_addr_addr;
	const int *user_nodes = (const int *)user_nodes_addr;
	int *user_status = (int *)user_status_addr;
	void **virt_addr = NULL;
	int *nr_pages = NULL;
	int *nodes = NULL;
	int *status = NULL;
	pte_t **ptep = NULL;
	unsigned long *dst_phys = NULL;
	struct move_pages_smp_req mpsr;
	size_t ptr_bytes = ptr_size * count;
	size_t int_bytes = int_size * count;
	size_t pte_bytes = pte_size * count;
	size_t ulong_bytes = ulong_size * count;
	unsigned long t_s = rdtsc_fn ? rdtsc_fn() : 0;
	unsigned long t_e;
	int i, ret;

	ret = move_pages_policy_result(pid, flags);
	if (ret) {
		if (log_fn) {
			if (pid) {
				log_fn(MOVE_PAGES_LOG_UNSUPPORTED_PID, 0, ret);
			}
			else if (flags & MPOL_MF_MOVE_ALL) {
				log_fn(MOVE_PAGES_LOG_UNSUPPORTED_MOVE_ALL, 0, ret);
			}
		}
		return ret;
	}

	if (!alloc_fn || !verify_fn || !copy_to_fn || !get_nr_nodes_fn ||
			!lock_fn || !unlock_fn || !smp_call_fn || !handler_fn ||
			!vm || !page_table_lock || !cpu_set || !proc) {
		return -EFAULT;
	}

	virt_addr = alloc_fn(ptr_bytes, alloc_flags);
	if (!virt_addr) {
		return -ENOMEM;
	}
	nr_pages = alloc_fn(int_bytes, alloc_flags);
	if (!nr_pages) {
		ret = -ENOMEM;
		goto dealloc_out;
	}
	nodes = alloc_fn(int_bytes, alloc_flags);
	if (!nodes) {
		ret = -ENOMEM;
		goto dealloc_out;
	}
	status = alloc_fn(int_bytes, alloc_flags);
	if (!status) {
		ret = -ENOMEM;
		goto dealloc_out;
	}
	ptep = alloc_fn(pte_bytes, alloc_flags);
	if (!ptep) {
		ret = -ENOMEM;
		goto dealloc_out;
	}
	dst_phys = alloc_fn(ulong_bytes, alloc_flags);
	if (!dst_phys) {
		ret = -ENOMEM;
		goto dealloc_out;
	}

	if (rdtsc_fn) {
		t_e = rdtsc_fn();
		if (log_fn) {
			log_fn(MOVE_PAGES_LOG_INIT_MALLOC, t_e - t_s, 0);
		}
		t_s = t_e;
	}

	if (verify_fn(vm, user_virt_addr_addr, ptr_bytes)) {
		ret = -EFAULT;
		goto dealloc_out;
	}
	if (user_nodes && verify_fn(vm, user_nodes_addr, int_bytes)) {
		ret = -EFAULT;
		goto dealloc_out;
	}
	if (verify_fn(vm, user_status_addr, int_bytes)) {
		ret = -EFAULT;
		goto dealloc_out;
	}

	if (user_nodes) {
		if (!copy_from_fn) {
			ret = -EFAULT;
			goto dealloc_out;
		}
		copy_from_fn(nodes, user_nodes_addr, int_bytes);
		for (i = 0; i < count; i++) {
			if (nodes[i] < 0 || nodes[i] >= get_nr_nodes_fn()) {
				ret = -ENODEV;
				goto dealloc_out;
			}
		}
	}

	if (rdtsc_fn) {
		t_e = rdtsc_fn();
		if (log_fn) {
			log_fn(MOVE_PAGES_LOG_INIT_VERIFY, t_e - t_s, 0);
		}
		t_s = t_e;
	}

	lock_fn(page_table_lock);
	ret = move_pages_smp_req_prepare_result(&mpsr, count, user_virt_addr,
			user_status, user_nodes, virt_addr, status, ptep, nodes,
			nr_pages, dst_phys, proc);
	if (!ret) {
		ret = smp_call_fn(cpu_set, handler_fn, &mpsr);
	}
	unlock_fn(page_table_lock);

	if (ret) {
		goto dealloc_out;
	}

	if (rdtsc_fn) {
		t_e = rdtsc_fn();
		if (log_fn) {
			log_fn(MOVE_PAGES_LOG_PARALLEL, t_e - t_s, 0);
		}
	}

	if (copy_to_fn(user_status_addr, status, int_bytes)) {
		ret = -EFAULT;
		goto dealloc_out;
	}

	ret = 0;

dealloc_out:
	move_pages_free_arrays_c(free_fn, virt_addr, nr_pages, nodes, status,
			ptep, dst_phys);
	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE int
getrusage_who_result(int who)
{
	return (who != RUSAGE_SELF &&
			who != RUSAGE_CHILDREN &&
			who != RUSAGE_THREAD) ? -EINVAL : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
itimer_which_result(int which)
{
	return (which != ITIMER_REAL &&
			which != ITIMER_VIRTUAL &&
			which != ITIMER_PROF) ? -EINVAL : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
itimer_is_real(int which)
{
	return which == ITIMER_REAL;
}

SYSCALL_POLICY_HELPER_SCOPE int
itimer_should_start(long value_sec, long value_usec)
{
	return (value_sec == 0 && value_usec == 0) ? 0 : 1;
}

static void
itimer_thread_slot(void *thread, const struct syscall_itimer_offsets *offsets,
		int which, struct itimerval **timerp, struct timespec **elapsedp)
{
	if (which == ITIMER_VIRTUAL) {
		*timerp = (struct itimerval *)((char *)thread +
				offsets->thread_itimer_virtual_offset);
		*elapsedp = (struct timespec *)((char *)thread +
				offsets->thread_itimer_virtual_value_offset);
	}
	else {
		*timerp = (struct itimerval *)((char *)thread +
				offsets->thread_itimer_prof_offset);
		*elapsedp = (struct timespec *)((char *)thread +
				offsets->thread_itimer_prof_value_offset);
	}
}

SYSCALL_POLICY_HELPER_SCOPE void
itimer_snapshot_current_result(unsigned long timer_addr,
		unsigned long elapsed_addr, unsigned long out_addr)
{
	struct itimerval *timer = (struct itimerval *)timer_addr;
	struct timespec *elapsed = (struct timespec *)elapsed_addr;
	struct itimerval *out = (struct itimerval *)out_addr;
	struct timeval tv;

	memcpy(out, timer, sizeof(*out));
	if (out->it_value.tv_sec != 0 || out->it_value.tv_usec != 0) {
		ts_to_tv(&tv, elapsed);
		tv_sub(&out->it_value, &tv);
	}
}

SYSCALL_POLICY_HELPER_SCOPE long
setitimer_body_result(int which, unsigned long new_addr,
		unsigned long old_addr, void *thread,
		const struct syscall_itimer_offsets *offsets, int syscall_nr,
		syscall_do_syscall3_fn_t syscall3_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_set_timer_fn_t set_timer_fn)
{
	struct itimerval *timer;
	struct timespec *elapsed;
	struct itimerval wkval;
	int error;
	int timer_start;

	error = itimer_which_result(which);
	if (error) {
		return error;
	}
	if (itimer_is_real(which)) {
		return syscall3_fn ? syscall3_fn(syscall_nr, which,
				new_addr, old_addr) : -EINVAL;
	}
	if (!thread || !offsets) {
		return -EINVAL;
	}

	itimer_thread_slot(thread, offsets, which, &timer, &elapsed);
	if (old_addr) {
		if (!copy_to_fn) {
			return -EFAULT;
		}
		itimer_snapshot_current_result((unsigned long)timer,
				(unsigned long)elapsed, (unsigned long)&wkval);
		if (copy_to_fn(old_addr, &wkval, sizeof(wkval))) {
			return -EFAULT;
		}
	}
	if (!new_addr) {
		return 0;
	}
	if (!copy_from_fn || !set_timer_fn) {
		return -EINVAL;
	}
	if (copy_from_fn(timer, new_addr, sizeof(*timer))) {
		return -EFAULT;
	}
	elapsed->tv_sec = 0;
	elapsed->tv_nsec = 0;
	timer_start = itimer_should_start(timer->it_value.tv_sec,
			timer->it_value.tv_usec);
	*(int *)((char *)thread + offsets->thread_itimer_enabled_offset) =
			timer_start;
	set_timer_fn(0);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
getitimer_body_result(int which, unsigned long old_addr, void *thread,
		const struct syscall_itimer_offsets *offsets, int syscall_nr,
		syscall_do_syscall2_fn_t syscall2_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	struct itimerval *timer;
	struct timespec *elapsed;
	struct itimerval wkval;
	int error;

	error = itimer_which_result(which);
	if (error) {
		return error;
	}
	if (itimer_is_real(which)) {
		return syscall2_fn ? syscall2_fn(syscall_nr, which, old_addr) :
				-EINVAL;
	}
	if (!thread || !offsets) {
		return -EINVAL;
	}
	if (!old_addr) {
		return 0;
	}
	if (!copy_to_fn) {
		return -EFAULT;
	}

	itimer_thread_slot(thread, offsets, which, &timer, &elapsed);
	itimer_snapshot_current_result((unsigned long)timer,
			(unsigned long)elapsed, (unsigned long)&wkval);
	if (copy_to_fn(old_addr, &wkval, sizeof(wkval))) {
		return -EFAULT;
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
clock_gettime_dispatch(int clock_id, int local_support, int has_ts)
{
	if (!has_ts) {
		return TIME_DISPATCH_NOOP;
	}

	if (local_support && clock_id == CLOCK_REALTIME) {
		return TIME_DISPATCH_LOCAL_REALTIME;
	}

	if (clock_id == CLOCK_PROCESS_CPUTIME_ID) {
		return TIME_DISPATCH_PROCESS_CPUTIME;
	}

	if (clock_id == CLOCK_THREAD_CPUTIME_ID) {
		return TIME_DISPATCH_THREAD_CPUTIME;
	}

	return TIME_DISPATCH_FORWARD;
}

SYSCALL_POLICY_HELPER_SCOPE int
gettimeofday_dispatch(int has_tv, int has_tz, int local_support)
{
	if (!has_tv && !has_tz) {
		return TIME_DISPATCH_NOOP;
	}

	if (!has_tz && local_support) {
		return TIME_DISPATCH_LOCAL_REALTIME;
	}

	return TIME_DISPATCH_FORWARD;
}

SYSCALL_POLICY_HELPER_SCOPE long
gettimeofday_body_result(unsigned long tv_addr, unsigned long tz_addr,
		int local_support, int syscall_nr,
		syscall_gettime_fn_t gettime_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_do_syscall2_fn_t syscall2_fn)
{
	struct timespec ats;
	struct timeval atv;
	int dispatch;

	dispatch = gettimeofday_dispatch(tv_addr != 0, tz_addr != 0,
			local_support);
	if (dispatch == TIME_DISPATCH_NOOP) {
		return 0;
	}
	if (dispatch == TIME_DISPATCH_LOCAL_REALTIME) {
		if (!gettime_fn || !copy_to_fn) {
			return -EFAULT;
		}
		gettime_fn(&ats);
		atv.tv_sec = ats.tv_sec;
		atv.tv_usec = ats.tv_nsec / 1000;
		return copy_to_fn(tv_addr, &atv, sizeof(atv));
	}
	if (!syscall2_fn) {
		return -EFAULT;
	}
	return syscall2_fn(syscall_nr, tv_addr, tz_addr);
}

static void
settimeofday_log_emit(settimeofday_log_fn_t log_fn, int event,
		unsigned long utv_addr, unsigned long utz_addr, long sec,
		long nsec, long error)
{
	if (log_fn)
		log_fn(event, utv_addr, utz_addr, sec, nsec, error);
}

static void
settimeofday_out(syscall_rwlock_fn_t unlock_fn, void *lock_arg,
		settimeofday_log_fn_t log_fn, unsigned long utv_addr,
		unsigned long utz_addr, long error)
{
	if (unlock_fn)
		unlock_fn(lock_arg);
	settimeofday_log_emit(log_fn, SETTIMEOFDAY_LOG_EXIT, utv_addr,
			utz_addr, 0, 0, error);
}

SYSCALL_POLICY_HELPER_SCOPE long
settimeofday_body_result(unsigned long utv_addr, unsigned long utz_addr,
		int local_support, unsigned long clocks_per_sec, int syscall_nr,
		void *ctx, void *lock_arg, void *version_arg,
		struct timespec *origin, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_rdtsc_fn_t rdtsc_fn,
		syscall_forward_context_fn_t forward_fn,
		syscall_atomic64_read_fn_t atomic_read_fn,
		syscall_atomic64_inc_fn_t atomic_inc_fn, syscall_wmb_fn_t wmb_fn,
		syscall_panic_fn_t panic_fn, settimeofday_log_fn_t log_fn)
{
	struct timeval tv;
	struct timespec newts = { 0, 0 };
	int update_origin = 0;
	unsigned long tsc;
	long error = 0;

	settimeofday_log_emit(log_fn, SETTIMEOFDAY_LOG_ENTER, utv_addr,
			utz_addr, 0, 0, 0);
	if (lock_fn)
		lock_fn(lock_arg);

	if (!atomic_read_fn) {
		error = -EFAULT;
		settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr,
				utz_addr, error);
		return error;
	}
	if (atomic_read_fn(version_arg) & 1) {
		if (panic_fn)
			panic_fn();
	}

	if (utv_addr && local_support) {
		if (!copy_from_fn || !rdtsc_fn) {
			error = -EFAULT;
			settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr,
					utz_addr, error);
			return error;
		}
		if (copy_from_fn(&tv, utv_addr, sizeof(tv))) {
			error = -EFAULT;
			settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr,
					utz_addr, error);
			return error;
		}
		newts.tv_sec = tv.tv_sec;
		newts.tv_nsec = tv.tv_usec * 1000;

		tsc = rdtsc_fn();
		newts.tv_sec -= tsc / clocks_per_sec;
		newts.tv_nsec -= NS_PER_SEC * (tsc % clocks_per_sec)
			/ clocks_per_sec;
		if (newts.tv_nsec < 0) {
			--newts.tv_sec;
			newts.tv_nsec += NS_PER_SEC;
		}
		update_origin = 1;
	}

	if (!forward_fn) {
		error = -EFAULT;
		settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr,
				utz_addr, error);
		return error;
	}
	error = forward_fn(syscall_nr, ctx);

	if (!error && update_origin) {
		if (!atomic_inc_fn || !wmb_fn || !origin) {
			error = -EFAULT;
			settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr,
					utz_addr, error);
			return error;
		}
		settimeofday_log_emit(log_fn, SETTIMEOFDAY_LOG_ORIGIN,
				utv_addr, utz_addr, newts.tv_sec, newts.tv_nsec,
				0);
		atomic_inc_fn(version_arg);
		wmb_fn();
		*origin = newts;
		wmb_fn();
		atomic_inc_fn(version_arg);
	}

	settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr, utz_addr,
			error);
	return error;
}

SYSCALL_POLICY_HELPER_SCOPE int
nanosleep_validate_timespec(long sec, long nsec)
{
	return (sec < 0 || nsec < 0 || nsec >= NS_PER_SEC) ? -EINVAL : 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
nanosleep_body_result(unsigned long tv_addr, unsigned long rem_addr,
		int local_support, int syscall_nr, void *thread, void *monitor,
		size_t monitor_status_offset, int heavy_status,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_do_syscall2_fn_t syscall2_fn,
		syscall_rdtsc_fn_t rdtsc_fn,
		syscall_ns_per_tsc_fn_t ns_per_tsc_fn,
		syscall_has_sigpending_fn_t has_sigpending_fn,
		syscall_cpu_pause_fn_t cpu_pause_fn)
{
	unsigned long nanosecs;
	unsigned long nanosecs_rem;
	unsigned long tscs;
	unsigned long ts;
	long tscs_rem;
	struct timespec tv;
	struct timespec rem;
	int ret = 0;

	*(int *)((char *)monitor + monitor_status_offset) = heavy_status;
	if (!local_support) {
		if (!syscall2_fn) {
			return -EFAULT;
		}
		return syscall2_fn(syscall_nr, tv_addr, rem_addr);
	}

	if (!copy_from_fn || !copy_to_fn || !rdtsc_fn || !ns_per_tsc_fn ||
	    !has_sigpending_fn || !cpu_pause_fn) {
		return -EFAULT;
	}

	ts = rdtsc_fn();
	if (copy_from_fn(&tv, tv_addr, sizeof(tv))) {
		return -EFAULT;
	}
	ret = nanosleep_validate_timespec(tv.tv_sec, tv.tv_nsec);
	if (ret) {
		return ret;
	}

	nanosecs = tv.tv_sec * NS_PER_SEC + tv.tv_nsec;
	tscs = nanosecs * 1000 / ns_per_tsc_fn();
	while (rdtsc_fn() - ts < tscs) {
		if (has_sigpending_fn(thread)) {
			ret = -EINTR;
			break;
		}
		cpu_pause_fn();
	}

	if ((ret == -EINTR) && rem_addr) {
		tscs_rem = tscs - (rdtsc_fn() - ts);
		if (tscs_rem < 0) {
			tscs_rem = 0;
		}
		nanosecs_rem = tscs_rem * ns_per_tsc_fn() / 1000;
		rem.tv_sec = nanosecs_rem / NS_PER_SEC;
		rem.tv_nsec = nanosecs_rem % NS_PER_SEC;
		if (copy_to_fn(rem_addr, &rem, sizeof(rem))) {
			ret = -EFAULT;
		}
	}

	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE int
rt_sigtimedwait_prepare(size_t sigsetsize, size_t expected_sigset_size,
		int has_set)
{
	if (sigsetsize > expected_sigset_size) {
		return -EINVAL;
	}

	if (!has_set) {
		return -EFAULT;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
rt_sigtimedwait_timeout_result(long sec, long nsec, int local_support)
{
	if (sec < 0 || nsec < 0 || nsec >= NS_PER_SEC) {
		return -EINVAL;
	}

	if (!local_support && (sec || nsec)) {
		return -EOPNOTSUPP;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE void
rt_sigtimedwait_prepare_masks(unsigned long raw_wait_mask,
		unsigned long current_mask, unsigned long *wait_maskp,
		unsigned long *blocked_maskp, unsigned long *interrupt_maskp)
{
	unsigned long wait_mask = raw_wait_mask;
	unsigned long blocked_mask;

	wait_mask &= ~__sigmask(SIGKILL);
	wait_mask &= ~__sigmask(SIGSTOP);
	blocked_mask = current_mask | wait_mask;

	*wait_maskp = wait_mask;
	*blocked_maskp = blocked_mask;
	*interrupt_maskp = ~blocked_mask;
}

SYSCALL_POLICY_HELPER_SCOPE void
rt_sigtimedwait_deadline(long now_sec, long now_nsec, long timeout_sec,
		long timeout_nsec, long *deadline_secp, long *deadline_nsecp)
{
	long sec = now_sec + timeout_sec;
	long nsec = now_nsec + timeout_nsec;

	if (nsec >= NS_PER_SEC) {
		sec++;
		nsec -= NS_PER_SEC;
	}

	*deadline_secp = sec;
	*deadline_nsecp = nsec;
}

SYSCALL_POLICY_HELPER_SCOPE int
rt_sigtimedwait_timeout_expired(long now_sec, long now_nsec,
		long deadline_sec, long deadline_nsec)
{
	return now_sec > deadline_sec ||
		(now_sec == deadline_sec && now_nsec >= deadline_nsec);
}

SYSCALL_POLICY_HELPER_SCOPE int
sigmask_to_signal_number(unsigned long mask)
{
	int sig;

	for (sig = 0; mask; sig++, mask >>= 1)
		;
	return sig;
}

static int
signal_is_default_ignored(int sig)
{
	return sig == SIGCHLD || sig == SIGURG || sig == SIGCONT;
}

SYSCALL_POLICY_HELPER_SCOPE int
signal_pending_deliverable_result(int delflag, int sig,
		unsigned long handler_addr, unsigned long pending_mask,
		unsigned long blocked_mask)
{
	if (!delflag && signal_is_default_ignored(sig) &&
			(handler_addr == 0 ||
			 handler_addr == (unsigned long)SIG_IGN)) {
		return 0;
	}

	return (pending_mask & blocked_mask) ? 0 : 1;
}

SYSCALL_POLICY_HELPER_SCOPE int
signal_pending_interrupt_action_result(int sig, unsigned long handler_addr,
		unsigned long pending_mask, unsigned long blocked_mask,
		int interrupted)
{
	if (!signal_pending_deliverable_result(0, sig, handler_addr,
			pending_mask, blocked_mask)) {
		return 0;
	}
	if (interrupted) {
		return 0;
	}
	if (!signal_is_default_ignored(sig) && handler_addr == 0) {
		return 2;
	}
	return 1;
}

SYSCALL_POLICY_HELPER_SCOPE int
rt_sigqueueinfo_pid_result(int pid)
{
	return pid <= 0 ? -ESRCH : 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
rt_sigqueueinfo_body_result(int pid, int sig, unsigned long info_addr,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_do_kill_fn_t do_kill_fn)
{
	struct siginfo info;
	int error;

	error = rt_sigqueueinfo_pid_result(pid);
	if (error) {
		return error;
	}
	if (!copy_from_fn || copy_from_fn(&info, info_addr, sizeof(info))) {
		return -EFAULT;
	}
	if (!do_kill_fn) {
		return -EFAULT;
	}
	return do_kill_fn(pid, sig, &info);
}

SYSCALL_POLICY_HELPER_SCOPE int
sigsuspend_sigsetsize_result(size_t sigsetsize, size_t expected_sigset_size)
{
	return sigsetsize > expected_sigset_size ? -EINVAL : 0;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
sigsuspend_prepare_mask(unsigned long raw_mask)
{
	raw_mask &= ~__sigmask(SIGKILL);
	raw_mask &= ~__sigmask(SIGSTOP);
	return raw_mask;
}

SYSCALL_POLICY_HELPER_SCOPE int
sigsuspend_pending_matches(unsigned long pending_mask, unsigned long suspend_mask)
{
	return !(pending_mask & suspend_mask);
}

SYSCALL_POLICY_HELPER_SCOPE long
pause_body_result(void *thread, size_t sigmask_offset,
		syscall_sigsuspend_fn_t suspend_fn)
{
	if (!thread) {
		return -EINVAL;
	}
	if (!suspend_fn) {
		return -EFAULT;
	}

	return suspend_fn(thread, syscall_offset_ptr(thread, sigmask_offset));
}

SYSCALL_POLICY_HELPER_SCOPE long
rt_sigsuspend_body_result(void *thread, unsigned long set_addr,
		size_t sigsetsize, size_t expected_sigset_size,
		void *scratch_sigset, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_sigsuspend_fn_t suspend_fn)
{
	int error = sigsuspend_sigsetsize_result(sigsetsize,
			expected_sigset_size);

	if (error) {
		return error;
	}
	if (!thread || !set_addr || !scratch_sigset || !copy_from_fn) {
		return -EFAULT;
	}
	if (copy_from_fn(scratch_sigset, set_addr, expected_sigset_size)) {
		return -EFAULT;
	}
	if (!suspend_fn) {
		return -EFAULT;
	}

	return suspend_fn(thread, scratch_sigset);
}

SYSCALL_POLICY_HELPER_SCOPE int
sigaction_sigsetsize_result(size_t sigsetsize, size_t expected_sigset_size)
{
	return sigsetsize != expected_sigset_size ? -EINVAL : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
do_sigaction_body_result(int sig, const struct k_sigaction *act,
		struct k_sigaction *oact, void *sigcommon,
		size_t action_offset, size_t action_stride,
		size_t lock_offset, void *lock_node,
		syscall_sigcommon_lock_fn_t lock_fn,
		syscall_sigcommon_lock_fn_t unlock_fn,
		syscall_sigaction_forward_fn_t forward_fn)
{
	struct k_sigaction *k;
	size_t action_index;
	size_t action_delta;
	char *sigcommon_bytes = sigcommon;
	int error;

	error = sigaction_validate(sig, act != NULL);
	if (error) {
		return error;
	}
	if (!sigcommon || !lock_node ||
			action_stride < sizeof(struct k_sigaction) ||
			!lock_fn || !unlock_fn || (act && !forward_fn)) {
		return -EFAULT;
	}

	action_index = sig - 1;
	if (action_index &&
			action_stride > (~(size_t)0 - action_offset) /
			action_index) {
		return -EINVAL;
	}
	action_delta = action_offset + action_stride * action_index;
	k = (struct k_sigaction *)(sigcommon_bytes + action_delta);

	lock_fn(sigcommon_bytes + lock_offset, lock_node);
	if (oact) {
		memcpy(oact, k, action_stride);
	}
	if (act) {
		memcpy(k, act, action_stride);
	}
	unlock_fn(sigcommon_bytes + lock_offset, lock_node);

	if (act) {
		forward_fn(sig, act);
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
rt_sigaction_body_result(int sig, unsigned long act_addr,
		unsigned long oact_addr, size_t sigsetsize,
		size_t expected_sigset_size,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_sigaction_fn_t sigaction_fn)
{
	struct k_sigaction new_sa;
	struct k_sigaction old_sa;
	int rc;

	rc = sigaction_sigsetsize_result(sigsetsize, expected_sigset_size);
	if (rc) {
		return rc;
	}
	if (act_addr) {
		if (!copy_from_fn ||
		    copy_from_fn(&new_sa.sa, act_addr, sizeof(new_sa.sa))) {
			return -EFAULT;
		}
	}

	if (!sigaction_fn) {
		return -EFAULT;
	}
	rc = sigaction_fn(sig, act_addr ? &new_sa : NULL,
			oact_addr ? &old_sa : NULL);
	if (rc == 0 && oact_addr) {
		if (!copy_to_fn ||
		    copy_to_fn(oact_addr, &old_sa.sa, sizeof(old_sa.sa))) {
			return -EFAULT;
		}
	}

	return rc;
}

SYSCALL_POLICY_HELPER_SCOPE int
sigaltstack_validate(int flags, size_t size)
{
	if (flags != 0 && flags != SS_DISABLE) {
		return -EINVAL;
	}
	if (flags != SS_DISABLE && size < MINSIGSTKSZ) {
		return -ENOMEM;
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
sigaltstack_is_disable(int flags)
{
	return flags == SS_DISABLE;
}

SYSCALL_POLICY_HELPER_SCOPE long
sigaltstack_body_result(void *thread, size_t sigstack_offset,
		unsigned long ss_addr, unsigned long oss_addr,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	stack_t *thread_sigstack =
		(stack_t *)syscall_offset_ptr(thread, sigstack_offset);
	stack_t wss;
	int error;

	if (oss_addr) {
		if (!copy_to_fn ||
				copy_to_fn(oss_addr, thread_sigstack,
					sizeof(*thread_sigstack))) {
			return -EFAULT;
		}
	}

	if (!ss_addr) {
		return 0;
	}

	if (!copy_from_fn || copy_from_fn(&wss, ss_addr, sizeof(wss))) {
		return -EFAULT;
	}

	error = sigaltstack_validate(wss.ss_flags, wss.ss_size);
	if (error) {
		return error;
	}

	if (sigaltstack_is_disable(wss.ss_flags)) {
		thread_sigstack->ss_sp = NULL;
		thread_sigstack->ss_flags = SS_DISABLE;
		thread_sigstack->ss_size = 0;
	} else {
		memcpy(thread_sigstack, &wss, sizeof(wss));
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
process_vm_validate_args(unsigned long flags, unsigned long liovcnt,
		unsigned long riovcnt)
{
	if (flags) {
		return -EINVAL;
	}

	if (liovcnt > IOV_MAX || riovcnt > IOV_MAX) {
		return -EINVAL;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
process_vm_op_is_write(int op)
{
	return op == PROCESS_VM_WRITE;
}

SYSCALL_POLICY_HELPER_SCOPE int
process_vm_op_is_valid(int op)
{
	return op == PROCESS_VM_READ || op == PROCESS_VM_WRITE;
}

SYSCALL_POLICY_HELPER_SCOPE long
process_vm_rw_body_result(int pid, const struct iovec *local_iov,
		unsigned long liovcnt, const struct iovec *remote_iov,
		unsigned long riovcnt, unsigned long flags, int op,
		syscall_process_vm_rw_fn_t rw_fn)
{
	int error = process_vm_validate_args(flags, liovcnt, riovcnt);

	if (error) {
		return error;
	}
	if (!process_vm_op_is_valid(op)) {
		return -EINVAL;
	}
	if (!rw_fn) {
		return -EFAULT;
	}

	return rw_fn(pid, local_iov, liovcnt, remote_iov, riovcnt, flags, op);
}

SYSCALL_POLICY_HELPER_SCOPE long
prctl_body_result(int option, unsigned long arg2, unsigned long arg3,
		unsigned long arg4, unsigned long arg5, void *proc,
		size_t thp_disable_offset, int syscall_nr, void *ctx,
		syscall_forward_context_fn_t forward_fn)
{
	if (option == PR_SET_THP_DISABLE) {
		if (arg3 || arg4 || arg5) {
			return -EINVAL;
		}
		if (!proc) {
			return -EFAULT;
		}
		*(int *)((char *)proc + thp_disable_offset) = arg2;
		return 0;
	}

	if (option == PR_GET_THP_DISABLE) {
		if (arg2 || arg3 || arg4 || arg5) {
			return -EINVAL;
		}
		if (!proc) {
			return -EFAULT;
		}
		return *(int *)((char *)proc + thp_disable_offset);
	}

	if (!forward_fn) {
		return -EFAULT;
	}
	return forward_fn(syscall_nr, ctx);
}

SYSCALL_POLICY_HELPER_SCOPE int
arch_prctl_type_result(unsigned long code, int *typep)
{
	int type;

	switch (code) {
	case ARCH_SET_FS:
	case ARCH_GET_FS:
		type = IHK_ASR_X86_FS;
		break;
	case ARCH_GET_GS:
		type = IHK_ASR_X86_GS;
		break;
	case ARCH_SET_GS:
		return -ENOTSUPP;
	default:
		return -EINVAL;
	}

	if (typep) {
		*typep = type;
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
arch_prctl_body_result(unsigned long code, unsigned long address, void *thread,
		size_t tlsblock_base_offset, syscall_get_cpu_fn_t get_cpu_fn,
		arch_prctl_set_register_fn_t set_register_fn,
		arch_prctl_get_register_fn_t get_register_fn,
		arch_prctl_log_fn_t log_fn)
{
	int type = 0;
	int error = arch_prctl_type_result(code, &type);

	if (error) {
		return error;
	}

	switch (code) {
	case ARCH_SET_FS:
		if (!thread) {
			return -EFAULT;
		}
		*(unsigned long *)((char *)thread + tlsblock_base_offset) =
			address;
		if (log_fn) {
			log_fn(ARCH_SET_FS, get_cpu_fn ? get_cpu_fn() : -1,
					address);
		}
		return set_register_fn ? set_register_fn(type, address) :
			-EFAULT;
	case ARCH_GET_FS:
	case ARCH_GET_GS:
		return get_register_fn ?
			get_register_fn(type, (unsigned long *)address) :
			-EFAULT;
	default:
		return 0;
	}
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
arch_clone_body_result(void *proc, size_t coredump_lock_offset,
		void *lock_node, int clone_flags, unsigned long newsp,
		unsigned long parent_tidptr, unsigned long child_tidptr,
		unsigned long tls, unsigned long pc, unsigned long sp,
		arch_clone_lock_fn_t lock_fn,
		arch_clone_lock_fn_t unlock_fn, arch_do_fork_fn_t fork_fn)
{
	void *coredump_lock;
	unsigned long ret;

	if (!proc || !lock_fn || !unlock_fn || !fork_fn) {
		return -EFAULT;
	}

	coredump_lock = (char *)proc + coredump_lock_offset;
	lock_fn(coredump_lock, lock_node);
	ret = fork_fn(clone_flags, newsp, parent_tidptr, child_tidptr, tls,
			pc, sp);
	unlock_fn(coredump_lock, lock_node);
	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
arch_fork_body_result(unsigned long pc, unsigned long sp,
		arch_do_fork_fn_t fork_fn)
{
	if (!fork_fn) {
		return -EFAULT;
	}
	return fork_fn(SIGCHLD, 0, 0, 0, 0, pc, sp);
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
arch_vfork_body_result(unsigned long pc, unsigned long sp,
		arch_do_fork_fn_t fork_fn)
{
	if (!fork_fn) {
		return -EFAULT;
	}
	return fork_fn(CLONE_VFORK | SIGCHLD, 0, 0, 0, 0, pc, sp);
}

SYSCALL_POLICY_HELPER_SCOPE long
arch_time_body_result(long now, unsigned long tloc_addr,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	if (tloc_addr) {
		if (!copy_to_fn) {
			return -EFAULT;
		}
		if (copy_to_fn(tloc_addr, &now, sizeof(now)) != 0) {
			return -EFAULT;
		}
	}
	return now;
}

SYSCALL_POLICY_HELPER_SCOPE long
arch_shmget_body_result(long key, size_t size, int shmflg0,
		arch_shmget_default_huge_shift_fn_t default_huge_shift_fn,
		arch_do_shmget_fn_t do_shmget_fn,
		arch_shmget_log_fn_t log_fn)
{
	int shmflg = shmflg0;
	int shmid = -EINVAL;
	int error;

	if (log_fn) {
		log_fn(ARCH_SHMGET_LOG_ENTER, key, size, shmflg0, 0, shmid);
	}

	if (shmflg & SHM_HUGETLB) {
		int hugeshift = shmflg & (0x3F << SHM_HUGE_SHIFT);

		if (hugeshift == 0) {
			if (!default_huge_shift_fn) {
				error = -EFAULT;
				goto out;
			}
			shmflg |= default_huge_shift_fn() << MAP_HUGE_SHIFT;
		}
		else if (hugeshift == SHM_HUGE_2MB ||
				hugeshift == SHM_HUGE_1GB) {
			/* nop */
		}
		else {
			error = -EINVAL;
			goto out;
		}
	}

	if (!do_shmget_fn) {
		error = -EFAULT;
		goto out;
	}

	shmid = do_shmget_fn(key, size, shmflg);
	error = 0;
out:
	if (log_fn) {
		log_fn(ARCH_SHMGET_LOG_EXIT, key, size, shmflg0, error, shmid);
	}
	return error ? error : shmid;
}

SYSCALL_POLICY_HELPER_SCOPE long
arch_mmap_body_result(unsigned long addr0, size_t len0, int prot, int flags0,
		int fd, long off0, unsigned long user_start,
		unsigned long user_end, int supported_flags, int ignored_flags,
		int error_flags,
		arch_mmap_default_huge_shift_fn_t default_huge_shift_fn,
		arch_mmap_overmap_fn_t overmap_fn,
		arch_do_mmap_fn_t do_mmap_fn, arch_mmap_log_fn_t log_fn)
{
	int flags = flags0;
	size_t pgsize = PAGE_SIZE;
	unsigned long addr = addr0;
	unsigned long result_addr = 0;
	size_t len;
	unsigned long valid_dummy_addr;
	int error;
	int unknown_flags;

	if (log_fn) {
		log_fn(ARCH_MMAP_LOG_ENTER, addr0, len0, prot, flags0, fd,
				off0, 0, result_addr, 0);
	}

	if (flags & MAP_HUGETLB) {
		int hugeshift;

		if (!(flags & MAP_ANONYMOUS)) {
			error = -EINVAL;
			goto out;
		}

		hugeshift = flags & (0x3F << MAP_HUGE_SHIFT);
		switch (hugeshift) {
		case 0:
			if (!default_huge_shift_fn) {
				error = -EFAULT;
				goto out;
			}
			flags |= default_huge_shift_fn() << MAP_HUGE_SHIFT;
			break;
		case MAP_HUGE_2MB:
		case MAP_HUGE_1GB:
			break;
		default:
			error = -EINVAL;
			if (log_fn) {
				log_fn(ARCH_MMAP_LOG_UNSUPPORTED_PGSIZE, addr0,
						len0, prot, flags0, fd, off0,
						error, result_addr, 0);
			}
			goto out;
		}

		pgsize = (size_t)1 << ((flags >> MAP_HUGE_SHIFT) & 0x3F);
		len0 = (len0 + pgsize - 1) & ~(pgsize - 1);
		if (!overmap_fn) {
			error = -EFAULT;
			goto out;
		}
		if (overmap_fn(len0, (flags >> MAP_HUGE_SHIFT) & 0x3F)) {
			error = -ENOMEM;
			goto out;
		}
	}

	valid_dummy_addr = (user_start + PTL3_SIZE - 1) & ~(PTL3_SIZE - 1);
	len = (len0 + pgsize - 1) & ~(pgsize - 1);
recheck:
	if ((addr & (pgsize - 1))
			|| (len == 0)
			|| !(flags & (MAP_SHARED | MAP_PRIVATE))
			|| ((flags & MAP_SHARED) && (flags & MAP_PRIVATE))
			|| (off0 & (pgsize - 1))) {
		if (!(flags & MAP_FIXED) && addr != valid_dummy_addr) {
			addr = valid_dummy_addr;
			goto recheck;
		}
		error = -EINVAL;
		if (log_fn) {
			log_fn(ARCH_MMAP_LOG_INVALID, addr0, len0, prot,
					flags0, fd, off0, error, result_addr, 0);
		}
		goto out;
	}

	if (addr < user_start || user_end <= addr ||
			len > (user_end - user_start)) {
		if (!(flags & MAP_FIXED) && addr != valid_dummy_addr) {
			addr = valid_dummy_addr;
			goto recheck;
		}
		error = -ENOMEM;
		if (log_fn) {
			log_fn(ARCH_MMAP_LOG_NOMEM, addr0, len0, prot, flags0,
					fd, off0, error, result_addr, 0);
		}
		goto out;
	}

	unknown_flags = flags & ~(supported_flags | ignored_flags);
	if ((flags & error_flags) || unknown_flags) {
		error = -EINVAL;
		if (log_fn) {
			log_fn(ARCH_MMAP_LOG_UNKNOWN_FLAGS, addr0, len0, prot,
					flags0, fd, off0, error, result_addr,
					unknown_flags);
		}
		goto out;
	}

	if (!do_mmap_fn) {
		error = -EFAULT;
		goto out;
	}

	result_addr = do_mmap_fn(addr, len, prot, flags, fd, off0, 0, NULL);
	error = 0;
out:
	if (log_fn) {
		log_fn(ARCH_MMAP_LOG_EXIT, addr0, len0, prot, flags0, fd,
				off0, error, result_addr, 0);
	}
	return error ? error : (long)result_addr;
}

SYSCALL_POLICY_HELPER_SCOPE long
migrate_pages_body_result(void)
{
	return -ENOSYS;
}

SYSCALL_POLICY_HELPER_SCOPE long
madvise_body_result(unsigned long start, size_t len, int advice)
{
	(void)start;
	(void)len;
	(void)advice;
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
get_system_body_result(void)
{
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_open_disabled_body_result(void)
{
	return -ENOSYS;
}

SYSCALL_POLICY_HELPER_SCOPE long
linux_mlock_body_result(unsigned long addr, size_t len, int syscall_nr,
		syscall_do_syscall2_fn_t syscall2_fn)
{
	if (!syscall2_fn) {
		return -EFAULT;
	}

	return syscall2_fn(syscall_nr, addr, len);
}

SYSCALL_POLICY_HELPER_SCOPE long
linux_spawn_body_result(int syscall_nr, void *ctx,
		syscall_forward_context_fn_t forward_fn)
{
	if (!forward_fn) {
		return -EFAULT;
	}

	return forward_fn(syscall_nr, ctx);
}

SYSCALL_POLICY_HELPER_SCOPE long
swapout_body_result(const char *filename, void *workarea, size_t size,
		int flag, int syscall_nr, void *linux_ctx,
		syscall_swapout_pageout_fn_t pageout_fn,
		syscall_swapout_pagein_fn_t pagein_fn,
		syscall_forward_context_fn_t forward_fn)
{
	int rc;

	if (!filename || flag == 0x01) {
		if (!forward_fn) {
			return -EFAULT;
		}
		return forward_fn(syscall_nr, linux_ctx);
	}

	if (!pageout_fn) {
		return -EFAULT;
	}
	rc = pageout_fn(filename, workarea, size, flag);
	if (rc < 0) {
		return rc;
	}

	if (flag != 0x02) {
		if (!forward_fn) {
			return -EFAULT;
		}
		(void)forward_fn(syscall_nr, linux_ctx);
	}

	if (!pagein_fn) {
		return -EFAULT;
	}

	return pagein_fn(flag);
}

static int
syscall_c_bytes_eq(const char *left, const char *right, size_t len)
{
	if (!left || !right) {
		return 0;
	}
	return strncmp(left, right, len) == 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
open_common_body_result(unsigned long pathname_addr, int flags, int syscall_nr,
		void *ctx, const char *xpmem_dev_path, unsigned long alloc_flags,
		syscall_strlen_user_fn_t strlen_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn,
		syscall_open_special_fn_t special_open_fn,
		syscall_forward_context_fn_t forward_fn)
{
	const char *_pathname = (const char *)pathname_addr;
	char *pathname;
	long len;
	size_t bytes;
	long rc;

	if (!strlen_fn) {
		return -EFAULT;
	}
	len = strlen_fn(_pathname);
	if (len < 0) {
		return len;
	}
	bytes = (size_t)len + 1;
	if (!bytes) {
		return -EINVAL;
	}

	if (!alloc_fn) {
		return -EFAULT;
	}
	pathname = alloc_fn(bytes, alloc_flags);
	if (!pathname) {
		return -ENOMEM;
	}

	if (!copy_from_fn) {
		if (free_fn) {
			free_fn(pathname);
		}
		return -EFAULT;
	}
	if (copy_from_fn(pathname, pathname_addr, bytes)) {
		rc = -EFAULT;
	}
	else if (syscall_c_bytes_eq(pathname, xpmem_dev_path, bytes)) {
		if (!special_open_fn) {
			if (free_fn) {
				free_fn(pathname);
			}
			return -EFAULT;
		}
		rc = special_open_fn(pathname, flags, ctx);
	}
	else {
		if (!forward_fn) {
			if (free_fn) {
				free_fn(pathname);
			}
			return -EFAULT;
		}
		rc = forward_fn(syscall_nr, ctx);
	}

	if (free_fn) {
		free_fn(pathname);
	}

	return rc;
}

SYSCALL_POLICY_HELPER_SCOPE long
util_migrate_inter_kernel_body_result(unsigned long arg_addr, void *scratch_attr,
		size_t attr_size, syscall_copy_from_user_fn_t copy_from_fn,
		syscall_util_thread_fn_t util_thread_fn)
{
	void *attr = NULL;

	if (!util_thread_fn) {
		return -EFAULT;
	}
	if (arg_addr) {
		if (!scratch_attr || !copy_from_fn ||
				copy_from_fn(scratch_attr, arg_addr, attr_size)) {
			return -EFAULT;
		}
		attr = scratch_attr;
	}

	return util_thread_fn(attr);
}

SYSCALL_POLICY_HELPER_SCOPE long
util_indicate_clone_body_result(void *thread, int mode, unsigned long arg_addr,
		size_t attr_size, unsigned long alloc_flags,
		size_t thread_proc_offset, size_t proc_enable_uti_offset,
		size_t thread_mod_clone_offset, size_t thread_mod_clone_arg_offset,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn)
{
	void *proc;
	void *new_attr = NULL;
	void **mod_clone_argp;
	void *old_attr;

	if (!thread) {
		return -EFAULT;
	}
	proc = *(void **)syscall_offset_ptr(thread, thread_proc_offset);
	if (!proc) {
		return -EFAULT;
	}
	if (!*(int *)syscall_offset_ptr(proc, proc_enable_uti_offset)) {
		return -EINVAL;
	}
	if (mode != SPAWN_TO_LOCAL && mode != SPAWN_TO_REMOTE) {
		return -EINVAL;
	}

	if (arg_addr) {
		if (!alloc_fn) {
			return -EFAULT;
		}
		new_attr = alloc_fn(attr_size, alloc_flags);
		if (!new_attr) {
			return -ENOMEM;
		}
		if (!copy_from_fn || copy_from_fn(new_attr, arg_addr, attr_size)) {
			if (free_fn) {
				free_fn(new_attr);
			}
			return -EFAULT;
		}
	}

	*(int *)syscall_offset_ptr(thread, thread_mod_clone_offset) = mode;
	mod_clone_argp = (void **)syscall_offset_ptr(thread,
			thread_mod_clone_arg_offset);
	old_attr = *mod_clone_argp;
	if (old_attr) {
		if (!free_fn) {
			return -EFAULT;
		}
		free_fn(old_attr);
		*mod_clone_argp = NULL;
	}
	if (new_attr) {
		*mod_clone_argp = new_attr;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
util_register_desc_body_result(unsigned long desc, unsigned long *desc_store)
{
	if (!desc_store) {
		return -EFAULT;
	}
	*desc_store = desc;
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
threads_signal_body_result(void *current_thread, int signal, int wait_stopped,
		size_t thread_proc_offset, size_t proc_pid_offset,
		size_t proc_threads_list_offset, size_t thread_tid_offset,
		size_t thread_status_offset, size_t thread_siblings_list_offset,
		syscall_do_kill_thread_fn_t do_kill_fn,
		syscall_cpu_pause_fn_t pause_fn)
{
	void *proc;
	int pid;
	struct list_head *head;
	struct list_head *pos;

	if (!current_thread || !do_kill_fn) {
		return -EFAULT;
	}
	proc = *(void **)syscall_offset_ptr(current_thread, thread_proc_offset);
	if (!proc) {
		return -EFAULT;
	}
	pid = *(int *)syscall_offset_ptr(proc, proc_pid_offset);
	head = (struct list_head *)syscall_offset_ptr(proc,
			proc_threads_list_offset);

	for (pos = head->next; pos != head; pos = pos->next) {
		void *thread = (char *)pos - thread_siblings_list_offset;

		if (thread == current_thread) {
			continue;
		}
		do_kill_fn(current_thread, pid,
				*(int *)syscall_offset_ptr(thread, thread_tid_offset),
				signal, NULL, 0);
	}

	if (!wait_stopped) {
		return 0;
	}
	if (!pause_fn) {
		return -EFAULT;
	}
	for (;;) {
		int all_stopped = 1;

		for (pos = head->next; pos != head; pos = pos->next) {
			void *thread = (char *)pos - thread_siblings_list_offset;

			if (thread == current_thread) {
				continue;
			}
			if (*(int *)syscall_offset_ptr(thread,
					thread_status_offset) != PS_STOPPED) {
				all_stopped = 0;
				break;
			}
		}
		if (all_stopped) {
			return 0;
		}
		pause_fn();
	}
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_signal_data_result(long data)
{
	return (data > 64 || data < 0) ? -EINVAL : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_detach_signal_result(long data)
{
	return (data > 64 || data < 0) ? -EIO : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_user_area_result(long addr, unsigned long user_struct_size)
{
	return (addr > user_struct_size - 8 || addr < 0) ? -EFAULT : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_status_allows_io(int status)
{
	return status & (PS_STOPPED | PS_TRACED) ? 1 : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_setoptions_flags_result(int flags)
{
	if (flags & ~(PTRACE_O_TRACESYSGOOD|
				PTRACE_O_TRACEFORK|
				PTRACE_O_TRACEVFORK|
				PTRACE_O_TRACECLONE|
				PTRACE_O_TRACEEXEC|
				PTRACE_O_TRACEVFORKDONE|
				PTRACE_O_TRACEEXIT)) {
		return -EINVAL;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_apply_options(int current, int flags)
{
	return (current & ~PTRACE_O_MASK) | flags;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_setoptions_apply_thread_result(unsigned long thread_addr,
		unsigned long ptrace_offset, int flags)
{
	int *ptracep;
	int updated;

	if (!thread_addr) {
		return 0;
	}

	ptracep = (int *)(thread_addr + ptrace_offset);
	updated = ptrace_apply_options(*ptracep, flags);
	*ptracep = updated;
	return updated;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_child_traced_result(int has_child, int has_proc, int ptrace)
{
	return (!has_child || !has_proc || !(ptrace & PT_TRACED)) ? -ESRCH : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_attach_policy_result(int tracer_pid, int target_pid,
		int target_ptrace, int same_process)
{
	if (tracer_pid == target_pid) {
		return -EPERM;
	}

	if ((target_ptrace & PT_TRACED) || same_process) {
		return -EPERM;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_attach_mark_traced_result(unsigned long thread_addr,
		unsigned long ptrace_offset)
{
	int *ptracep;
	int traced = PT_TRACED | PT_TRACE_EXEC;

	if (!thread_addr) {
		return 0;
	}

	ptracep = (int *)(thread_addr + ptrace_offset);
	*ptracep = traced;
	return traced;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_detach_state_result(int is_traced, int same_report_proc)
{
	return (!is_traced || !same_report_proc) ? -ESRCH : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_siginfo_state_result(int status, int has_siginfo)
{
	if (!ptrace_status_allows_io(status)) {
		return -ESRCH;
	}

	return has_siginfo ? 0 : -ESRCH;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_eventmsg_state_result(int status)
{
	return ptrace_status_allows_io(status) ? 0 : -ESRCH;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_eventmsg_prepare_result(int status, unsigned long eventmsg,
		unsigned long *outp)
{
	int rc = ptrace_eventmsg_state_result(status);

	if (rc) {
		return rc;
	}

	if (outp) {
		*outp = eventmsg;
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_wakeup_request_action_result(long request)
{
	if (request == PTRACE_KILL) {
		return PTRACE_WAKEUP_ACTION_KILL;
	}
	if (request == PTRACE_CONT || request == PTRACE_SINGLESTEP ||
			request == PTRACE_SYSCALL) {
		return PTRACE_WAKEUP_ACTION_RESUME;
	}
	return PTRACE_WAKEUP_ACTION_NONE;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_resume_single_step_result(long request)
{
	return request == PTRACE_SINGLESTEP;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_resume_trace_syscall_result(long request)
{
	return request == PTRACE_SYSCALL;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_resume_signal_needed_result(long request, long data)
{
	return ptrace_wakeup_request_action_result(request) ==
		PTRACE_WAKEUP_ACTION_RESUME && data != 0 && data != SIGSTOP;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_resume_signal_source_result(long request, int has_sendsig,
		int has_recvsig)
{
	if (request == PTRACE_CONT && has_sendsig) {
		return PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG;
	}
	if (request == PTRACE_CONT && has_recvsig) {
		return PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG;
	}
	return PTRACE_RESUME_SIGNAL_SOURCE_USER;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_detach_forward_signal_needed_result(int data)
{
	return data != 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_detach_exit_signal_needed_result(int status)
{
	return status == PS_EXITED || status == PS_ZOMBIE;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_detach_thread_body_result(void *thread, int data, void *current_thread,
		void *current_proc, void *pid1,
		const struct ptrace_detach_offsets *offsets,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		ptrace_list_detach_fn_t list_detach_fn,
		ptrace_main_reparent_fn_t main_reparent_fn,
		ptrace_report_detach_fn_t report_detach_fn,
		ptrace_cleanup_fn_t cleanup_fn,
		ptrace_free_fn_t free_fn,
		ptrace_clear_single_step_fn_t clear_single_step_fn,
		ptrace_report_attach_fn_t report_attach_fn,
		ptrace_thread_exit_signal_fn_t exit_signal_fn,
		ptrace_do_kill_thread_fn_t do_kill_fn,
		ptrace_wakeup_thread_fn_t wakeup_fn,
		wait_thread_side_effect_fn_t release_fn,
		ptrace_finalize_process_fn_t finalize_fn,
		void *lock_node)
{
	char *thread_base = thread;
	char *current_base = current_proc;
	char *thread_proc;
	void *report_proc = NULL;
	void *term_proc = NULL;
	void *debugreg;
	int actions = 0;

	if (!thread || !current_thread || !current_proc || !pid1 || !offsets ||
	    !lock_fn || !unlock_fn || !list_detach_fn || !main_reparent_fn ||
	    !report_detach_fn || !cleanup_fn || !free_fn ||
	    !clear_single_step_fn || !report_attach_fn || !exit_signal_fn ||
	    !do_kill_fn || !wakeup_fn || !release_fn || !finalize_fn ||
	    !lock_node) {
		return -EINVAL;
	}

	thread_proc = *(void **)(thread_base + offsets->thread_proc_offset);
	if (!thread_proc) {
		return -EINVAL;
	}

	if (thread == *(void **)(thread_proc +
				offsets->proc_main_thread_offset)) {
		void *parent = *(void **)(thread_proc +
				offsets->proc_ppid_parent_offset);

		if (!parent) {
			return -EINVAL;
		}
		actions |= 1;
		if (*(int *)(thread_proc + offsets->proc_status_offset) ==
				PS_ZOMBIE &&
		    *(void **)(thread_proc + offsets->proc_parent_offset) !=
				parent) {
			term_proc = thread_proc;
			actions |= 2;
		}

		lock_fn(current_base + offsets->proc_children_lock_offset,
				lock_node);
		list_detach_fn(thread_proc + offsets->proc_siblings_list_offset);
		unlock_fn(current_base + offsets->proc_children_lock_offset,
				lock_node);

		lock_fn(thread_proc + offsets->proc_children_lock_offset,
				lock_node);
		main_reparent_fn(thread_proc, offsets->proc_parent_offset,
				parent,
				thread_proc +
				 offsets->proc_ptraced_siblings_list_offset,
				thread_proc + offsets->proc_siblings_list_offset,
				(char *)parent +
				 offsets->proc_children_list_offset);
		unlock_fn(thread_proc + offsets->proc_children_lock_offset,
				lock_node);
	}

	if (*(int *)(thread_base + offsets->thread_termsig_offset) &&
	    *(int *)(thread_base + offsets->thread_termsig_offset) != SIGCHLD &&
	    thread_proc != pid1) {
		report_proc = thread_proc;
		actions |= 4;
	}

	lock_fn(current_base + offsets->proc_threads_lock_offset, lock_node);
	report_detach_fn(thread, offsets->thread_report_proc_offset,
			report_proc,
			thread_base +
			 offsets->thread_report_siblings_list_offset);
	unlock_fn(current_base + offsets->proc_threads_lock_offset, lock_node);

	debugreg = cleanup_fn(thread, offsets->thread_ptrace_offset,
			offsets->thread_ptrace_saved_uctx_valid_offset,
			offsets->thread_ptrace_debugreg_offset);
	free_fn(debugreg);
	clear_single_step_fn(thread);
	actions |= 8;

	if (report_proc) {
		char *report_base = report_proc;

		lock_fn(report_base + offsets->proc_threads_lock_offset,
				lock_node);
		report_attach_fn(thread, 0, 0, 0,
				offsets->thread_report_proc_offset,
				report_proc,
				thread_base +
				 offsets->thread_report_siblings_list_offset,
				report_base +
				 offsets->proc_report_threads_list_offset);
		unlock_fn(report_base + offsets->proc_threads_lock_offset,
				lock_node);
		actions |= 16;
		if (ptrace_detach_exit_signal_needed_result(
				*(int *)(thread_base +
				 offsets->thread_status_offset))) {
			exit_signal_fn(thread);
			actions |= 32;
		}
	}

	if (ptrace_detach_forward_signal_needed_result(data)) {
		struct siginfo info;

		memset(&info, '\0', sizeof(info));
		info.si_signo = data;
		info.si_code = SI_USER;
		info._sifields._kill.si_pid =
			*(int *)(current_base + offsets->proc_pid_offset);
		do_kill_fn(current_thread,
				*(int *)(thread_proc + offsets->proc_pid_offset),
				*(int *)(thread_base + offsets->thread_tid_offset),
				data, &info, 1);
		actions |= 64;
	}

	wakeup_fn(thread, PS_TRACED | PS_STOPPED);
	release_fn(thread);
	actions |= 128;
	if (term_proc) {
		finalize_fn(term_proc);
		actions |= 256;
	}

	return actions;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_setsiginfo_target_result(int status, int has_sendsig, int has_recvsig)
{
	int target = PTRACE_SIGINFO_STORE_SENDSIG;

	if (!ptrace_status_allows_io(status)) {
		return -ESRCH;
	}
	if (!has_sendsig) {
		target |= PTRACE_SIGINFO_ALLOC_SENDSIG;
	}
	if (has_recvsig) {
		target |= PTRACE_SIGINFO_STORE_RECVSIG;
	}
	return target;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_getsiginfo_prepare_result(int status, unsigned long pending_addr,
		unsigned long info_offset, void *outp, size_t info_size)
{
	int rc = ptrace_siginfo_state_result(status, pending_addr != 0);

	if (rc) {
		return rc;
	}
	if (!outp) {
		return -EFAULT;
	}

	memcpy(outp, (void *)(pending_addr + info_offset), info_size);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_setsiginfo_store_result(unsigned long thread_addr,
		unsigned long sendsig_offset, unsigned long recvsig_offset,
		unsigned long info_offset, int target,
		unsigned long allocated_sendsig, const void *infop,
		size_t info_size)
{
	unsigned long *sendsig_slot;
	unsigned long *recvsig_slot;
	unsigned long pending;

	if (target < 0) {
		return target;
	}
	if (!thread_addr) {
		return -ESRCH;
	}

	sendsig_slot = (unsigned long *)(thread_addr + sendsig_offset);
	recvsig_slot = (unsigned long *)(thread_addr + recvsig_offset);

	if (target & PTRACE_SIGINFO_ALLOC_SENDSIG) {
		if (!allocated_sendsig) {
			return -ENOMEM;
		}
		*sendsig_slot = allocated_sendsig;
	}

	if ((target & (PTRACE_SIGINFO_STORE_SENDSIG |
		       PTRACE_SIGINFO_STORE_RECVSIG)) && !infop) {
		return -EFAULT;
	}

	if (target & PTRACE_SIGINFO_STORE_SENDSIG) {
		pending = *sendsig_slot;
		if (!pending) {
			return -ENOMEM;
		}
		memcpy((void *)(pending + info_offset), infop, info_size);
	}

	if (target & PTRACE_SIGINFO_STORE_RECVSIG) {
		pending = *recvsig_slot;
		if (!pending) {
			return -ESRCH;
		}
		memcpy((void *)(pending + info_offset), infop, info_size);
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
ptrace_read_user_words_result(unsigned long thread_addr, unsigned long *outp,
		size_t bytes, ptrace_read_user_word_fn_t read_fn)
{
	size_t addr;
	unsigned long *p;

	if (!thread_addr || !outp || !read_fn) {
		return -EFAULT;
	}

	for (addr = 0, p = outp; addr < bytes; addr += sizeof(*p), p++) {
		long rc = read_fn(thread_addr, addr, p);

		if (rc) {
			return rc;
		}
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
ptrace_write_user_words_result(unsigned long thread_addr,
		const unsigned long *inp, size_t bytes,
		ptrace_write_user_word_fn_t write_fn)
{
	size_t addr;
	const unsigned long *p;

	if (!thread_addr || !inp || !write_fn) {
		return -EFAULT;
	}

	for (addr = 0, p = inp; addr < bytes; addr += sizeof(*p), p++) {
		long rc = write_fn(thread_addr, addr, *p);

		if (rc) {
			return rc;
		}
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
ptrace_read_user_word_result(int status, unsigned long thread_addr,
		long user_area_offset, unsigned long *outp,
		ptrace_read_user_word_fn_t read_fn)
{
	if (!ptrace_status_allows_io(status)) {
		return -EIO;
	}
	if (!thread_addr || !outp || !read_fn) {
		return -EFAULT;
	}

	return read_fn(thread_addr, user_area_offset, outp);
}

SYSCALL_POLICY_HELPER_SCOPE long
ptrace_write_user_word_result(int status, unsigned long thread_addr,
		long user_area_offset, unsigned long value,
		ptrace_write_user_word_fn_t write_fn)
{
	if (!ptrace_status_allows_io(status)) {
		return -EIO;
	}
	if (!thread_addr || !write_fn) {
		return -EFAULT;
	}

	return write_fn(thread_addr, user_area_offset, value);
}

SYSCALL_POLICY_HELPER_SCOPE long
ptrace_read_vm_word_result(int status, unsigned long vm_addr,
		unsigned long user_addr, unsigned long *outp,
		ptrace_read_vm_word_fn_t read_fn)
{
	if (!ptrace_status_allows_io(status)) {
		return -EIO;
	}
	if (!vm_addr || !outp || !read_fn) {
		return -EFAULT;
	}

	return read_fn(vm_addr, user_addr, outp);
}

SYSCALL_POLICY_HELPER_SCOPE long
ptrace_write_vm_word_result(int status, unsigned long vm_addr,
		unsigned long user_addr, unsigned long value,
		ptrace_write_vm_word_fn_t write_fn)
{
	if (!ptrace_status_allows_io(status)) {
		return -EIO;
	}
	if (!vm_addr || !write_fn) {
		return -EFAULT;
	}

	return write_fn(vm_addr, user_addr, value);
}

SYSCALL_POLICY_HELPER_SCOPE long
ptrace_fpregs_io_result(int status, unsigned long thread_addr,
		unsigned long data_addr, ptrace_fpregs_io_fn_t io_fn)
{
	if (!ptrace_status_allows_io(status)) {
		return -EIO;
	}
	if (!thread_addr || !io_fn) {
		return -EFAULT;
	}

	return io_fn(thread_addr, data_addr);
}

SYSCALL_POLICY_HELPER_SCOPE long
ptrace_regset_io_result(int status, unsigned long thread_addr, long type,
		unsigned long user_iovec_addr, void *iovp, size_t iov_size,
		size_t iov_len_offset, size_t iov_len_size,
		ptrace_user_copy_from_fn_t copy_from_fn,
		ptrace_regset_io_fn_t io_fn,
		ptrace_user_copy_to_fn_t copy_to_fn)
{
	long rc;

	if (!ptrace_status_allows_io(status)) {
		return -EIO;
	}
	if (!thread_addr || !iovp) {
		return -EFAULT;
	}
	if (iov_len_offset > iov_size || iov_len_size > iov_size - iov_len_offset) {
		return -EFAULT;
	}
	if (!copy_from_fn || !io_fn || !copy_to_fn) {
		return -EFAULT;
	}

	rc = copy_from_fn(iovp, user_iovec_addr, iov_size);
	if (rc) {
		return rc;
	}
	rc = io_fn(thread_addr, type, iovp);
	if (rc) {
		return rc;
	}

	return copy_to_fn(user_iovec_addr + iov_len_offset,
			(void *)((unsigned long)iovp + iov_len_offset),
			iov_len_size);
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_request_dispatch_result(long request)
{
	switch (request) {
	case PTRACE_TRACEME:
		return PTRACE_DISPATCH_TRACEME;
	case PTRACE_KILL:
	case PTRACE_CONT:
	case PTRACE_SINGLESTEP:
	case PTRACE_SYSCALL:
		return PTRACE_DISPATCH_WAKEUP;
	case PTRACE_GETREGS:
		return PTRACE_DISPATCH_GETREGS;
	case PTRACE_SETREGS:
		return PTRACE_DISPATCH_SETREGS;
	case PTRACE_GETFPREGS:
		return PTRACE_DISPATCH_GETFPREGS;
	case PTRACE_SETFPREGS:
		return PTRACE_DISPATCH_SETFPREGS;
	case PTRACE_PEEKUSER:
		return PTRACE_DISPATCH_PEEKUSER;
	case PTRACE_POKEUSER:
		return PTRACE_DISPATCH_POKEUSER;
	case PTRACE_PEEKTEXT:
	case PTRACE_PEEKDATA:
		return PTRACE_DISPATCH_PEEKTEXT;
	case PTRACE_POKETEXT:
	case PTRACE_POKEDATA:
		return PTRACE_DISPATCH_POKETEXT;
	case PTRACE_SETOPTIONS:
		return PTRACE_DISPATCH_SETOPTIONS;
	case PTRACE_ATTACH:
		return PTRACE_DISPATCH_ATTACH;
	case PTRACE_DETACH:
		return PTRACE_DISPATCH_DETACH;
	case PTRACE_GETSIGINFO:
		return PTRACE_DISPATCH_GETSIGINFO;
	case PTRACE_SETSIGINFO:
		return PTRACE_DISPATCH_SETSIGINFO;
	case PTRACE_GETREGSET:
		return PTRACE_DISPATCH_GETREGSET;
	case PTRACE_SETREGSET:
		return PTRACE_DISPATCH_SETREGSET;
	case PTRACE_GETEVENTMSG:
		return PTRACE_DISPATCH_GETEVENTMSG;
	default:
		return PTRACE_DISPATCH_ARCH;
	}
}

SYSCALL_POLICY_HELPER_SCOPE long
ptrace_syscall_body_result(long request, int pid, long addr, long data,
		const struct ptrace_syscall_ops *ops)
{
	if (!ops) {
		return -EOPNOTSUPP;
	}

	switch (ptrace_request_dispatch_result(request)) {
	case PTRACE_DISPATCH_TRACEME:
		return ops->traceme_fn ? ops->traceme_fn() : -EOPNOTSUPP;
	case PTRACE_DISPATCH_WAKEUP:
		return ops->wakeup_fn ?
			ops->wakeup_fn(pid, request, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_GETREGS:
		return ops->getregs_fn ?
			ops->getregs_fn(pid, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_SETREGS:
		return ops->setregs_fn ?
			ops->setregs_fn(pid, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_GETFPREGS:
		return ops->getfpregs_fn ?
			ops->getfpregs_fn(pid, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_SETFPREGS:
		return ops->setfpregs_fn ?
			ops->setfpregs_fn(pid, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_PEEKUSER:
		return ops->peekuser_fn ?
			ops->peekuser_fn(pid, addr, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_POKEUSER:
		return ops->pokeuser_fn ?
			ops->pokeuser_fn(pid, addr, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_PEEKTEXT:
		return ops->peektext_fn ?
			ops->peektext_fn(pid, addr, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_POKETEXT:
		return ops->poketext_fn ?
			ops->poketext_fn(pid, addr, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_SETOPTIONS:
		return ops->setoptions_fn ?
			ops->setoptions_fn(pid, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_ATTACH:
		return ops->attach_fn ? ops->attach_fn(pid) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_DETACH:
		return ops->detach_fn ?
			ops->detach_fn(pid, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_GETSIGINFO:
		return ops->getsiginfo_fn ?
			ops->getsiginfo_fn(pid, (siginfo_t *)data) :
			-EOPNOTSUPP;
	case PTRACE_DISPATCH_SETSIGINFO:
		return ops->setsiginfo_fn ?
			ops->setsiginfo_fn(pid, (siginfo_t *)data) :
			-EOPNOTSUPP;
	case PTRACE_DISPATCH_GETREGSET:
		return ops->getregset_fn ?
			ops->getregset_fn(pid, addr, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_SETREGSET:
		return ops->setregset_fn ?
			ops->setregset_fn(pid, addr, data) : -EOPNOTSUPP;
	case PTRACE_DISPATCH_GETEVENTMSG:
		return ops->geteventmsg_fn ?
			ops->geteventmsg_fn(pid, data) : -EOPNOTSUPP;
	default:
		return ops->arch_fn ?
			ops->arch_fn(request, pid, addr, data) : -EOPNOTSUPP;
	}
}

SYSCALL_POLICY_HELPER_SCOPE int
wait4_options_result(int options)
{
	return (options & ~(WNOHANG | WUNTRACED | WCONTINUED |
				__WCLONE | __WALL)) ? -EINVAL : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
waitid_to_wait_pid_result(int idtype, int id, int *pidp)
{
	if (idtype == P_PID) {
		*pidp = id;
	}
	else if (idtype == P_PGID) {
		*pidp = -id;
	}
	else if (idtype == P_ALL) {
		*pidp = -1;
	}
	else {
		return -EINVAL;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
waitid_options_result(int options)
{
	if (options & ~(WEXITED | WSTOPPED | WCONTINUED | WNOHANG |
				WNOWAIT | __WCLONE | __WALL)) {
		return -EINVAL;
	}

	if (!(options & (WEXITED | WSTOPPED | WCONTINUED))) {
		return -EINVAL;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_should_scan_process_result(int options)
{
	return (options & __WCLONE) ? 0 : 1;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_should_scan_thread_result(int pid, int options)
{
	return ((pid == -1 || pid > 0) && (options & (__WCLONE | __WALL))) ?
		1 : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_process_pid_matches_result(int pid, int parent_pgid, int child_pgid,
		int child_pid)
{
	if (pid == -1) {
		return 1;
	}
	if (pid < 0) {
		return -pid == child_pgid;
	}
	if (pid == 0) {
		return parent_pgid == child_pgid;
	}
	return pid == child_pid;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_thread_tid_matches_result(int tid, int child_tid, int is_main_thread)
{
	if (is_main_thread) {
		return 0;
	}
	return tid == -1 || tid == child_tid;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_process_exited_candidate_result(int options, int child_status)
{
	return (options & WEXITED) && child_status == PS_ZOMBIE;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_thread_exited_candidate_result(int options, int child_status)
{
	return (options & WEXITED) &&
		(child_status == PS_EXITED || child_status == PS_ZOMBIE);
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_nonptraced_stop_candidate_result(int ptrace, int signal_flags,
		int options)
{
	return !(ptrace & PT_TRACED) &&
		(signal_flags & SIGNAL_STOP_STOPPED) &&
		(options & WUNTRACED);
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_ptraced_stop_candidate_result(int ptrace, int status)
{
	return (ptrace & PT_TRACED) &&
		(status & (PS_STOPPED | PS_TRACED | PS_DELAY_TRACED));
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_continued_candidate_result(int signal_flags, int options)
{
	return (signal_flags & SIGNAL_STOP_CONTINUED) &&
		(options & WCONTINUED);
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_reap_needed_result(int options)
{
	return (options & WNOWAIT) ? 0 : 1;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_nohang_result(int options)
{
	return (options & WNOHANG) ? 1 : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_empty_result(int empty)
{
	return empty ? -ECHILD : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_stopped_status_result(int exit_status)
{
	return (exit_status << 8) | 0x7f;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_continued_status_result(void)
{
	return 0xffff;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_continued_body_result(struct thread *c_thread, struct process *child,
		int *status, int options, unsigned long child_pid_offset,
		unsigned long child_main_thread_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_signal_flags_offset,
		wait_signal_flags_reap_fn_t reap_fn)
{
	char *child_base = (char *)child;
	struct thread *target_thread;

	if (status) {
		*status = wait_continued_status_result();
	}

	if (c_thread) {
		target_thread = c_thread;
	}
	else {
		target_thread = *(struct thread **)(child_base +
				child_main_thread_offset);
	}
	reap_fn(target_thread, thread_signal_flags_offset, options,
			SIGNAL_STOP_CONTINUED);

	if (c_thread) {
		return *(int *)((char *)c_thread + thread_tid_offset);
	}
	return *(int *)(child_base + child_pid_offset);
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_stopped_body_result(struct thread *c_thread, struct process *child,
		int *status, int options, unsigned long child_pid_offset,
		unsigned long child_status_offset,
		unsigned long child_group_exit_status_offset,
		unsigned long child_main_thread_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_exit_status_offset,
		wait_exit_status_reap_fn_t reap_fn)
{
	char *child_base = (char *)child;
	char *thread_base;
	struct thread *main_thread;
	int c_thread_exit_status = 0;
	int main_thread_exit_status = 0;
	int source;
	int exit_status;
	int child_pid;
	int c_thread_tid = 0;

	if (!child) {
		return -EINVAL;
	}
	if (c_thread) {
		thread_base = (char *)c_thread;
		c_thread_exit_status =
			*(int *)(thread_base + thread_exit_status_offset);
		c_thread_tid = *(int *)(thread_base + thread_tid_offset);
	}
	main_thread = *(struct thread **)(child_base + child_main_thread_offset);
	if (main_thread) {
		main_thread_exit_status =
			*(int *)((char *)main_thread + thread_exit_status_offset);
	}

	source = wait_stopped_source_result(c_thread != NULL,
			c_thread_exit_status,
			*(int *)(child_base + child_status_offset),
			*(int *)(child_base + child_group_exit_status_offset),
			main_thread_exit_status);
	if (source == WAIT_STOP_SOURCE_NONE) {
		return 0;
	}

	exit_status = wait_stopped_exit_status_result(source,
			c_thread_exit_status,
			*(int *)(child_base + child_group_exit_status_offset),
			main_thread_exit_status);
	if (status) {
		*status = wait_stopped_status_result(exit_status);
	}
	if (!reap_fn) {
		return -EINVAL;
	}
	switch (source) {
	case WAIT_STOP_SOURCE_THREAD:
		reap_fn(c_thread, thread_exit_status_offset, options);
		break;
	case WAIT_STOP_SOURCE_PROCESS:
		reap_fn(child, child_group_exit_status_offset, options);
		break;
	case WAIT_STOP_SOURCE_MAIN_THREAD:
		reap_fn(main_thread, thread_exit_status_offset, options);
		break;
	default:
		break;
	}

	child_pid = *(int *)(child_base + child_pid_offset);
	return wait_report_id_result(source, child_pid, c_thread_tid);
}

SYSCALL_POLICY_HELPER_SCOPE int
do_wait_body_result(int pid, int *status, int options, void *rusage,
		void *thread, void *wait_entry,
		unsigned long thread_proc_offset,
		unsigned long proc_pid_offset,
		unsigned long proc_waitpid_q_offset,
		int interruptible_status,
		wait_scan_fn_t wait_proc_fn,
		wait_scan_fn_t wait_thread_fn,
		wait_entry_init_fn_t init_fn,
		wait_prepare_fn_t prepare_fn,
		wait_finish_fn_t finish_fn,
		wait_has_signal_fn_t has_signal_fn,
		wait_schedule_fn_t schedule_fn,
		wait_log_fn_t log_fn)
{
	void *proc;
	void *waitq;
	int current_pid;
	int ret;
	int empty = 1;
	int orgpid = pid;

	if (!thread || !wait_entry || !status || !wait_proc_fn ||
	    !wait_thread_fn || !init_fn || !prepare_fn || !finish_fn ||
	    !has_signal_fn || !schedule_fn || !log_fn) {
		return -EINVAL;
	}

	proc = *(void **)((char *)thread + thread_proc_offset);
	if (!proc) {
		return -EINVAL;
	}
	waitq = (char *)proc + proc_waitpid_q_offset;
	current_pid = *(int *)((char *)proc + proc_pid_offset);

	log_fn(WAIT_LOG_ENTER, current_pid, pid);

	for (;;) {
		init_fn(wait_entry, thread);
		prepare_fn(waitq, wait_entry, interruptible_status);
		pid = orgpid;

		if (wait_should_scan_process_result(options)) {
			ret = wait_proc_fn(pid, status, options, rusage, &empty);
			if (ret) {
				log_fn(WAIT_LOG_FOUND, current_pid, pid);
				finish_fn(waitq, wait_entry);
				return ret;
			}
		}
		if (wait_should_scan_thread_result(pid, options)) {
			ret = wait_thread_fn(pid, status, options, rusage,
					&empty);
			if (ret) {
				log_fn(WAIT_LOG_FOUND, current_pid, pid);
				finish_fn(waitq, wait_entry);
				return ret;
			}
		}

		ret = wait_empty_result(empty);
		if (ret) {
			log_fn(WAIT_LOG_NOTFOUND, current_pid, pid);
			finish_fn(waitq, wait_entry);
			return ret;
		}

		if (wait_nohang_result(options)) {
			*status = 0;
			log_fn(WAIT_LOG_NOTFOUND, current_pid, pid);
			finish_fn(waitq, wait_entry);
			return 0;
		}

		log_fn(WAIT_LOG_SLEEPING, current_pid, pid);

		if (has_signal_fn(thread)) {
			finish_fn(waitq, wait_entry);
			return -EINTR;
		}

		schedule_fn();
		log_fn(WAIT_LOG_WOKEN, current_pid, pid);
		finish_fn(waitq, wait_entry);
	}
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_process_candidate_body_result(int current_ret, int pid, int *status,
		int options, void *thread, void *child_proc,
		void *child_thread, void *parent_children_lock,
		void *parent_children_lock_node, void *child_threads_lock,
		void *child_threads_lock_node, unsigned long child_pid_offset,
		unsigned long child_status_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_ptrace_offset,
		unsigned long thread_signal_flags_offset,
		wait_status_fn_t stopped_fn, wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		wait_lock_unlock_fn_t unlock_fn, int *foundp)
{
	int child_pid;
	int child_status;
	int child_tid;
	int child_ptrace;
	int signal_flags;
	int ret = current_ret;

	if (!foundp) {
		return -EINVAL;
	}
	*foundp = 0;
	if (!thread || !child_proc || !child_thread || !status) {
		return current_ret;
	}
	if (!stopped_fn || !continued_fn || !reap_fn || !unlock_fn) {
		return -EINVAL;
	}

	child_pid = *(int *)((char *)child_proc + child_pid_offset);
	child_status = *(int *)((char *)child_proc + child_status_offset);
	child_tid = *(int *)((char *)child_thread + thread_tid_offset);
	child_ptrace = *(int *)((char *)child_thread + thread_ptrace_offset);
	signal_flags = *(int *)((char *)child_thread +
			thread_signal_flags_offset);

	if (wait_nonptraced_stop_candidate_result(child_ptrace, signal_flags,
			options)) {
		ret = stopped_fn(thread, child_proc, NULL, status, options);
		reap_fn(child_thread, thread_signal_flags_offset, options,
				SIGNAL_STOP_STOPPED);
		unlock_fn(parent_children_lock, parent_children_lock_node);
		unlock_fn(child_threads_lock, child_threads_lock_node);
		*foundp = 1;
		return ret;
	}

	if (wait_ptraced_stop_candidate_result(child_ptrace, child_status)) {
		ret = stopped_fn(thread, child_proc, NULL, status, options);
		if (ret == child_pid) {
			if (pid == child_tid) {
				ret = child_tid;
			}
			reap_fn(child_thread, thread_signal_flags_offset,
					options, SIGNAL_STOP_STOPPED);
			unlock_fn(parent_children_lock,
					parent_children_lock_node);
			unlock_fn(child_threads_lock, child_threads_lock_node);
			*foundp = 1;
			return ret;
		}
	}

	if (wait_continued_candidate_result(signal_flags, options)) {
		ret = continued_fn(thread, child_proc, NULL, status, options);
		reap_fn(child_thread, thread_signal_flags_offset, options,
				SIGNAL_STOP_CONTINUED);
		unlock_fn(parent_children_lock, parent_children_lock_node);
		unlock_fn(child_threads_lock, child_threads_lock_node);
		*foundp = 1;
	}

	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_thread_candidate_body_result(int current_ret, int tid, int *status,
		int options, void *thread, void *child_thread,
		void *threads_lock, void *threads_lock_node,
		unsigned long thread_proc_offset,
		unsigned long thread_tid_offset,
		unsigned long thread_status_offset,
		unsigned long thread_ptrace_offset,
		unsigned long thread_signal_flags_offset,
		wait_status_fn_t stopped_fn, wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_thread_report_detach_fn_t report_detach_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_fn,
		int *foundp)
{
	void *child_proc;
	int child_tid;
	int child_status;
	int child_ptrace;
	int signal_flags;
	int ret = current_ret;
	int action;

	(void)tid;
	if (!foundp) {
		return -EINVAL;
	}
	*foundp = 0;
	if (!thread || !child_thread || !status) {
		return current_ret;
	}
	if (!stopped_fn || !continued_fn || !reap_fn || !unlock_fn ||
	    !report_detach_fn || !ptrace_detach_fn || !release_fn) {
		return -EINVAL;
	}

	child_proc = *(void **)((char *)child_thread + thread_proc_offset);
	child_tid = *(int *)((char *)child_thread + thread_tid_offset);
	child_status = *(int *)((char *)child_thread + thread_status_offset);
	child_ptrace = *(int *)((char *)child_thread + thread_ptrace_offset);
	signal_flags = *(int *)((char *)child_thread +
			thread_signal_flags_offset);

	if (wait_thread_exited_candidate_result(options, child_status)) {
		action = wait_thread_reap_action_result(options, child_ptrace);
		if (action == WAIT_THREAD_REAP_ACTION_PTRACE_DETACH) {
			unlock_fn(threads_lock, threads_lock_node);
			ptrace_detach_fn(child_thread);
		}
		else if (action == WAIT_THREAD_REAP_ACTION_RELEASE) {
			report_detach_fn(child_thread);
			unlock_fn(threads_lock, threads_lock_node);
			release_fn(child_thread);
		}
		else {
			unlock_fn(threads_lock, threads_lock_node);
		}
		*foundp = 1;
		return child_tid;
	}

	if (wait_nonptraced_stop_candidate_result(child_ptrace, signal_flags,
			options)) {
		ret = stopped_fn(thread, child_proc, child_thread, status,
				options);
		reap_fn(child_thread, thread_signal_flags_offset, options,
				SIGNAL_STOP_STOPPED);
		unlock_fn(threads_lock, threads_lock_node);
		*foundp = 1;
		return ret;
	}

	if (wait_ptraced_stop_candidate_result(child_ptrace, child_status)) {
		ret = stopped_fn(thread, child_proc, child_thread, status,
				options);
		if (ret == child_tid) {
			reap_fn(child_thread, thread_signal_flags_offset,
					options, SIGNAL_STOP_STOPPED);
			unlock_fn(threads_lock, threads_lock_node);
			*foundp = 1;
			return ret;
		}
	}

	if (wait_continued_candidate_result(signal_flags, options)) {
		ret = continued_fn(thread, child_proc, child_thread, status,
				options);
		reap_fn(child_thread, thread_signal_flags_offset, options,
				SIGNAL_STOP_CONTINUED);
		unlock_fn(threads_lock, threads_lock_node);
		*foundp = 1;
	}

	return ret;
}

static void
wait_process_fill_rusage_fallback(void *child_proc, void *rusage,
		const struct wait_zombie_offsets *offsets)
{
	char *child = child_proc;
	struct rusage *usage = rusage;
	struct timespec *utime;
	struct timespec *stime;

	if (!usage)
		return;
	utime = (struct timespec *)(child + offsets->proc_utime_offset);
	stime = (struct timespec *)(child + offsets->proc_stime_offset);
	ts_to_tv(&usage->ru_utime, utime);
	ts_to_tv(&usage->ru_stime, stime);
	usage->ru_maxrss =
		*(long *)(child + offsets->proc_maxrss_offset) / 1024;
}

static void
wait_process_accumulate_child_rusage_fallback(void *parent_proc,
		void *child_proc, const struct wait_zombie_offsets *offsets)
{
	char *parent = parent_proc;
	char *child = child_proc;
	long *maxrss_children;

	ts_add((struct timespec *)(parent + offsets->proc_stime_children_offset),
			(struct timespec *)(child + offsets->proc_stime_offset));
	ts_add((struct timespec *)(parent + offsets->proc_utime_children_offset),
			(struct timespec *)(child + offsets->proc_utime_offset));
	ts_add((struct timespec *)(parent + offsets->proc_stime_children_offset),
			(struct timespec *)(child +
				offsets->proc_stime_children_offset));
	ts_add((struct timespec *)(parent + offsets->proc_utime_children_offset),
			(struct timespec *)(child +
				offsets->proc_utime_children_offset));
	maxrss_children = (long *)(parent +
			offsets->proc_maxrss_children_offset);
	if (*(long *)(child + offsets->proc_maxrss_offset) > *maxrss_children)
		*maxrss_children =
			*(long *)(child + offsets->proc_maxrss_offset);
	if (*(long *)(child + offsets->proc_maxrss_children_offset) >
			*maxrss_children)
		*maxrss_children =
			*(long *)(child + offsets->proc_maxrss_children_offset);
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_process_zombie_body_result(void *thread, void *parent_proc,
		void *child_proc, int *status, int options, void *rusage,
		void *parent_children_lock, void *parent_children_lock_node,
		void *pid1, const struct wait_zombie_offsets *offsets,
		wait_host_wait4_fn_t host_wait4_fn,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_list_detach_fn_t list_detach_fn,
		wait_list_add_tail_fn_t list_add_tail_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_process_fn,
		wait_zombie_log_fn_t log_fn, void *parent_update_lock_node,
		void *child_update_lock_node, void *pid1_children_lock_node,
		void *child_threads_lock_node)
{
	char *parent = parent_proc;
	char *child = child_proc;
	char *pid1_base = pid1;
	int child_pid;
	int ret;
	void *ppid_parent;
	void *parent_field;
	int ppid_parent_pid;
	int reparent_needed;
	void *child_threads_lock;
	void *main_thread;

	if (!thread || !parent || !child || !offsets || !parent_children_lock ||
	    !parent_children_lock_node || !child_threads_lock_node ||
	    !host_wait4_fn || !lock_fn || !unlock_fn || !list_detach_fn ||
	    !list_add_tail_fn || !ptrace_detach_fn || !release_process_fn ||
	    !log_fn) {
		return -EINVAL;
	}

	child_pid = *(int *)(child + offsets->proc_pid_offset);
	log_fn(WAIT_ZOMBIE_LOG_FOUND, child_pid, 0, 0);
	if (status)
		*status = *(int *)(child +
				offsets->proc_group_exit_status_offset);

	ppid_parent = *(void **)(child + offsets->proc_ppid_parent_offset);
	parent_field = *(void **)(child + offsets->proc_parent_offset);
	ppid_parent_pid = ppid_parent ?
		*(int *)((char *)ppid_parent + offsets->proc_pid_offset) : 0;
	if (wait_zombie_skip_host_result(ppid_parent_pid,
			*(int *)(parent + offsets->proc_pid_offset),
			*(int *)(child + offsets->proc_nowait_offset))) {
		ret = child_pid;
	}
	else {
		ret = host_wait4_fn(child_pid, options);
	}
	if (ret != child_pid)
		log_fn(WAIT_ZOMBIE_LOG_WARNING, child_pid, 0, ret);
	log_fn(WAIT_ZOMBIE_LOG_STATUS, child_pid, status ? *status : -1, ret);

	reparent_needed = wait_process_reparent_needed_result(options,
			parent_field == ppid_parent);
	if (reparent_needed) {
		void *parent_update_lock;
		void *child_update_lock;
		void *pid1_children_lock;
		void *child_siblings;
		void *pid1_children;

		if (!pid1 || !parent_update_lock_node ||
		    !child_update_lock_node || !pid1_children_lock_node) {
			return -EINVAL;
		}
		parent_update_lock = parent + offsets->proc_update_lock_offset;
		child_update_lock = child + offsets->proc_update_lock_offset;
		pid1_children_lock = pid1_base +
			offsets->proc_children_lock_offset;
		child_threads_lock = child + offsets->proc_threads_lock_offset;
		child_siblings = child + offsets->proc_siblings_list_offset;
		pid1_children = pid1_base + offsets->proc_children_list_offset;

		lock_fn(parent_update_lock, parent_update_lock_node);
		wait_process_accumulate_child_rusage_fallback(parent, child,
				offsets);
		wait_process_fill_rusage_fallback(child, rusage, offsets);
		unlock_fn(parent_update_lock, parent_update_lock_node);

		list_detach_fn(child_siblings);
		unlock_fn(parent_children_lock, parent_children_lock_node);

		lock_fn(child_update_lock, child_update_lock_node);
		*(void **)(child + offsets->proc_parent_offset) = pid1;
		*(void **)(child + offsets->proc_ppid_parent_offset) = pid1;
		lock_fn(pid1_children_lock, pid1_children_lock_node);
		list_add_tail_fn(child_siblings, pid1_children);
		unlock_fn(pid1_children_lock, pid1_children_lock_node);
		unlock_fn(child_update_lock, child_update_lock_node);

		lock_fn(child_threads_lock, child_threads_lock_node);
		main_thread = *(void **)(child + offsets->proc_main_thread_offset);
		if (main_thread &&
		    wait_main_thread_ptrace_detach_needed_result(options,
			*(int *)((char *)main_thread +
				offsets->thread_ptrace_offset))) {
			unlock_fn(child_threads_lock, child_threads_lock_node);
			ptrace_detach_fn(main_thread);
		}
		else {
			unlock_fn(child_threads_lock, child_threads_lock_node);
		}
		release_process_fn(child_proc);
	}
	else {
		child_threads_lock = child + offsets->proc_threads_lock_offset;

		lock_fn(child_threads_lock, child_threads_lock_node);
		main_thread = *(void **)(child + offsets->proc_main_thread_offset);
		if (main_thread &&
		    wait_main_thread_ptrace_detach_needed_result(options,
			*(int *)((char *)main_thread +
				offsets->thread_ptrace_offset))) {
			unlock_fn(child_threads_lock, child_threads_lock_node);
			unlock_fn(parent_children_lock, parent_children_lock_node);
			ptrace_detach_fn(main_thread);
		}
		else {
			unlock_fn(child_threads_lock, child_threads_lock_node);
			unlock_fn(parent_children_lock, parent_children_lock_node);
		}
	}

	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_process_scan_body_result(int pid, int *status, int options, void *rusage,
		int *empty, void *thread, void *proc_arg, void *pid1,
		const struct wait_scan_offsets *scan_offsets,
		const struct wait_zombie_offsets *zombie_offsets,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_host_wait4_fn_t host_wait4_fn,
		wait_list_detach_fn_t list_detach_fn,
		wait_list_add_tail_fn_t list_add_tail_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_process_fn,
		wait_zombie_log_fn_t zombie_log_fn,
		wait_status_fn_t stopped_fn,
		wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		void *parent_children_lock_node,
		void *child_threads_lock_node,
		void *parent_update_lock_node,
		void *child_update_lock_node,
		void *pid1_children_lock_node)
{
	struct process *proc = proc_arg;
	struct process *child;
	struct list_head *head, *pos, *next;
	void *parent_children_lock;
	int pgid;
	int ret = 0;

	if (!empty || !thread || !proc || !pid1 || !scan_offsets ||
	    !zombie_offsets || !lock_fn || !unlock_fn || !host_wait4_fn ||
	    !list_detach_fn || !list_add_tail_fn || !ptrace_detach_fn ||
	    !release_process_fn || !zombie_log_fn || !stopped_fn ||
	    !continued_fn || !reap_fn || !parent_children_lock_node ||
	    !child_threads_lock_node) {
		return -EINVAL;
	}

	pgid = *(int *)((char *)proc + scan_offsets->proc_pgid_offset);
	parent_children_lock =
		(void *)((char *)proc + scan_offsets->proc_children_lock_offset);
	lock_fn(parent_children_lock, parent_children_lock_node);

	head = (struct list_head *)((char *)proc +
			scan_offsets->proc_children_list_offset);
	for (pos = head->next; pos != head; pos = next) {
		void *child_threads_lock;
		void *c_thread;
		int found = 0;

		next = pos->next;
		child = (void *)((char *)pos -
				scan_offsets->proc_siblings_list_offset);

		if (!wait_process_pid_matches_result(pid, pgid,
				*(int *)((char *)child +
					scan_offsets->proc_pgid_offset),
				*(int *)((char *)child +
					scan_offsets->proc_pid_offset))) {
			continue;
		}

		*empty = 0;
		if (wait_process_exited_candidate_result(options,
				*(int *)((char *)child +
					scan_offsets->proc_status_offset))) {
			return wait_process_zombie_body_result(thread, proc,
					child, status, options, rusage,
					parent_children_lock,
					parent_children_lock_node, pid1,
					zombie_offsets, host_wait4_fn,
					lock_fn, unlock_fn, list_detach_fn,
					list_add_tail_fn, ptrace_detach_fn,
					release_process_fn, zombie_log_fn,
					parent_update_lock_node,
					child_update_lock_node,
					pid1_children_lock_node,
					child_threads_lock_node);
		}

		child_threads_lock = (char *)child +
			scan_offsets->proc_threads_lock_offset;
		lock_fn(child_threads_lock, child_threads_lock_node);
		c_thread = *(void **)((char *)child +
				scan_offsets->proc_main_thread_offset);
		ret = wait_process_candidate_body_result(ret, pid, status,
				options, thread, child, c_thread,
				parent_children_lock, parent_children_lock_node,
				child_threads_lock, child_threads_lock_node,
				scan_offsets->proc_pid_offset,
				scan_offsets->proc_status_offset,
				scan_offsets->thread_tid_offset,
				scan_offsets->thread_ptrace_offset,
				scan_offsets->thread_signal_flags_offset,
				stopped_fn, continued_fn, reap_fn, unlock_fn,
				&found);
		if (found) {
			return ret;
		}
		unlock_fn(child_threads_lock, child_threads_lock_node);
	}

	if (*empty) {
		head = (struct list_head *)((char *)proc +
				scan_offsets->proc_ptraced_children_list_offset);
		for (pos = head->next; pos != head; pos = pos->next) {
			child = (void *)((char *)pos -
				 scan_offsets->proc_ptraced_siblings_list_offset);
			if (wait_process_pid_matches_result(pid, pgid,
					*(int *)((char *)child +
					 scan_offsets->proc_pgid_offset),
					*(int *)((char *)child +
					 scan_offsets->proc_pid_offset))) {
				*empty = 0;
				break;
			}
		}
	}
	unlock_fn(parent_children_lock, parent_children_lock_node);
	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_thread_scan_body_result(int tid, int *status, int options, void *rusage,
		int *empty, void *thread, void *proc_arg,
		const struct wait_scan_offsets *offsets,
		wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_status_fn_t stopped_fn,
		wait_status_fn_t continued_fn,
		wait_signal_flags_reap_fn_t reap_fn,
		wait_thread_report_detach_fn_t report_detach_fn,
		wait_thread_side_effect_fn_t ptrace_detach_fn,
		wait_thread_side_effect_fn_t release_fn,
		void *threads_lock_node)
{
	struct process *proc = proc_arg;
	struct thread *child;
	struct list_head *head, *pos, *next;
	void *threads_lock;
	int ret = 0;

	(void)rusage;
	if (!empty || !thread || !proc || !offsets || !lock_fn || !unlock_fn ||
	    !stopped_fn || !continued_fn || !reap_fn || !report_detach_fn ||
	    !ptrace_detach_fn || !release_fn || !threads_lock_node) {
		return -EINVAL;
	}

	threads_lock = (char *)proc + offsets->proc_threads_lock_offset;
	lock_fn(threads_lock, threads_lock_node);
	head = (struct list_head *)((char *)proc +
			offsets->proc_report_threads_list_offset);
	for (pos = head->next; pos != head; pos = next) {
		int found = 0;
		void *child_proc;
		void *main_thread;

		next = pos->next;
		child = (void *)((char *)pos -
				offsets->thread_report_siblings_list_offset);
		child_proc = *(void **)((char *)child +
				offsets->thread_proc_offset);
		main_thread = child_proc ?
			*(void **)((char *)child_proc +
				offsets->proc_main_thread_offset) : NULL;

		if (!wait_thread_tid_matches_result(tid,
				*(int *)((char *)child +
					offsets->thread_tid_offset),
				child == main_thread)) {
			continue;
		}
		*empty = 0;
		ret = wait_thread_candidate_body_result(ret, tid, status,
				options, thread, child, threads_lock,
				threads_lock_node, offsets->thread_proc_offset,
				offsets->thread_tid_offset,
				offsets->thread_status_offset,
				offsets->thread_ptrace_offset,
				offsets->thread_signal_flags_offset,
				stopped_fn, continued_fn, reap_fn, unlock_fn,
				report_detach_fn, ptrace_detach_fn, release_fn,
				&found);
		if (found) {
			return ret;
		}
	}

	if (*empty) {
		head = (struct list_head *)((char *)proc +
				offsets->proc_threads_list_offset);
		for (pos = head->next; pos != head; pos = pos->next) {
			void *child_proc;
			void *main_thread;

			child = (void *)((char *)pos -
					offsets->thread_siblings_list_offset);
			child_proc = *(void **)((char *)child +
					offsets->thread_proc_offset);
			main_thread = child_proc ?
				*(void **)((char *)child_proc +
					offsets->proc_main_thread_offset) :
				NULL;

			if (wait_thread_empty_candidate_result(
					child == main_thread,
					*(int *)((char *)child +
						offsets->thread_termsig_offset))) {
				*empty = 0;
				break;
			}
		}
	}
	unlock_fn(threads_lock, threads_lock_node);
	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_zombie_skip_host_result(int ppid_parent_pid, int current_pid, int nowait)
{
	return ppid_parent_pid != current_pid || nowait;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_thread_empty_candidate_result(int is_main_thread, int termsig)
{
	return !is_main_thread && termsig && termsig != SIGCHLD;
}

SYSCALL_POLICY_HELPER_SCOPE int
waitid_status_code_result(int status)
{
	if ((status & 0x000000ff) == 0x0000007f) {
		return CLD_STOPPED;
	}
	else if ((status & 0x0000ffff) == 0x0000ffff) {
		return CLD_CONTINUED;
	}
	else if (status & 0x000000ff) {
		return CLD_KILLED;
	}
	return CLD_EXITED;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_stopped_source_result(int has_c_thread, int c_thread_exit_status,
		int child_status, int child_group_exit_status,
		int main_thread_exit_status)
{
	if (has_c_thread) {
		return c_thread_exit_status ? WAIT_STOP_SOURCE_THREAD :
			WAIT_STOP_SOURCE_NONE;
	}
	if (child_status & (PS_STOPPED | PS_DELAY_STOPPED)) {
		return child_group_exit_status ? WAIT_STOP_SOURCE_PROCESS :
			WAIT_STOP_SOURCE_NONE;
	}
	return main_thread_exit_status ? WAIT_STOP_SOURCE_MAIN_THREAD :
		WAIT_STOP_SOURCE_NONE;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_stopped_exit_status_result(int source, int c_thread_exit_status,
		int child_group_exit_status, int main_thread_exit_status)
{
	switch (source) {
	case WAIT_STOP_SOURCE_THREAD:
		return c_thread_exit_status;
	case WAIT_STOP_SOURCE_PROCESS:
		return child_group_exit_status;
	case WAIT_STOP_SOURCE_MAIN_THREAD:
		return main_thread_exit_status;
	default:
		return 0;
	}
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_report_id_result(int source, int child_pid, int c_thread_tid)
{
	return source == WAIT_STOP_SOURCE_THREAD ? c_thread_tid : child_pid;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_reaped_exit_status_result(int options, int exit_status)
{
	return wait_reap_needed_result(options) ? 0 : exit_status;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_reaped_signal_flags_result(int options, int signal_flags, int clear_mask)
{
	return wait_reap_needed_result(options) ?
		(signal_flags & ~clear_mask) : signal_flags;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_process_reparent_needed_result(int options, int parent_is_ppid)
{
	return wait_reap_needed_result(options) && parent_is_ppid;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_main_thread_ptrace_detach_needed_result(int options, int ptrace)
{
	return wait_reap_needed_result(options) && (ptrace & PT_TRACED);
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_thread_reap_action_result(int options, int ptrace)
{
	if (!wait_reap_needed_result(options)) {
		return WAIT_THREAD_REAP_ACTION_NONE;
	}
	return (ptrace & PT_TRACED) ?
		WAIT_THREAD_REAP_ACTION_PTRACE_DETACH :
		WAIT_THREAD_REAP_ACTION_RELEASE;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_status_copy_needed_result(int rc, int has_status)
{
	return rc >= 0 && has_status;
}

SYSCALL_POLICY_HELPER_SCOPE int
wait_rusage_copy_needed_result(int has_rusage)
{
	return has_rusage;
}

SYSCALL_POLICY_HELPER_SCOPE long
wait4_body_result(int pid, unsigned long status_addr, int options,
		unsigned long rusage_addr, wait4_do_wait_fn_t do_wait_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	int status;
	int rc;
	struct rusage usage;

	rc = wait4_options_result(options);
	if (rc) {
		return rc;
	}

	memset(&usage, '\0', sizeof(usage));
	rc = do_wait_fn(pid, &status, WEXITED | options, &usage);
	if (wait_status_copy_needed_result(rc, status_addr != 0)) {
		copy_to_fn(status_addr, &status, sizeof(status));
	}
	if (wait_rusage_copy_needed_result(rusage_addr != 0)) {
		copy_to_fn(rusage_addr, &usage, sizeof(usage));
	}
	return rc;
}

SYSCALL_POLICY_HELPER_SCOPE int
waitid_siginfo_needed_result(int rc, int has_infop)
{
	return rc > 0 && has_infop;
}

SYSCALL_POLICY_HELPER_SCOPE void
waitid_copy_siginfo_result(int rc, unsigned long infop_addr, int status,
		long utime_sec, long utime_usec, long stime_sec,
		long stime_usec, syscall_copy_to_user_fn_t copy_to_fn)
{
	siginfo_t info;
	struct timeval utime = { .tv_sec = utime_sec, .tv_usec = utime_usec };
	struct timeval stime = { .tv_sec = stime_sec, .tv_usec = stime_usec };

	if (!waitid_siginfo_needed_result(rc, infop_addr != 0) || !copy_to_fn) {
		return;
	}

	memset(&info, '\0', sizeof(info));
	info.si_signo = SIGCHLD;
	info._sifields._sigchld.si_pid = rc;
	info._sifields._sigchld.si_status = status;
	info._sifields._sigchld.si_utime = timeval_to_jiffy(&utime);
	info._sifields._sigchld.si_stime = timeval_to_jiffy(&stime);
	info.si_code = waitid_status_code_result(status);
	copy_to_fn(infop_addr, &info, sizeof(info));
}

SYSCALL_POLICY_HELPER_SCOPE long
waitid_body_result(int idtype, int id, unsigned long infop_addr, int options,
		wait4_do_wait_fn_t do_wait_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	int pid;
	int status;
	int rc;
	struct rusage usage;

	rc = waitid_to_wait_pid_result(idtype, id, &pid);
	if (rc) {
		return rc;
	}

	rc = waitid_options_result(options);
	if (rc) {
		return rc;
	}

	memset(&usage, '\0', sizeof(usage));
	rc = do_wait_fn(pid, &status, options, &usage);
	if (rc < 0) {
		return rc;
	}

	waitid_copy_siginfo_result(rc, infop_addr, status,
			usage.ru_utime.tv_sec, usage.ru_utime.tv_usec,
			usage.ru_stime.tv_sec, usage.ru_stime.tv_usec,
			copy_to_fn);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
getrusage_dispatch_result(int who)
{
	switch (who) {
	case RUSAGE_SELF:
		return GETRUSAGE_DISPATCH_SELF;
	case RUSAGE_CHILDREN:
		return GETRUSAGE_DISPATCH_CHILDREN;
	case RUSAGE_THREAD:
		return GETRUSAGE_DISPATCH_THREAD;
	default:
		return 0;
	}
}

SYSCALL_POLICY_HELPER_SCOPE int
getrusage_thread_update_action_result(int is_current_thread, int status,
		int in_kernel)
{
	return !is_current_thread && status == PS_RUNNING && !in_kernel ?
		GETRUSAGE_THREAD_UPDATE_INTERRUPT :
		GETRUSAGE_THREAD_UPDATE_READY;
}

SYSCALL_POLICY_HELPER_SCOPE int
getrusage_thread_times_update_prepare_result(unsigned long thread_addr,
		unsigned long times_update_offset, int update_action)
{
	int *times_update;

	if (!thread_addr)
		return 0;

	times_update = (int *)(thread_addr + times_update_offset);
	if (update_action == GETRUSAGE_THREAD_UPDATE_INTERRUPT) {
		*times_update = 0;
		return 1;
	}

	*times_update = 1;
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
getrusage_maxrss_kb_result(long maxrss)
{
	return maxrss / 1024;
}

SYSCALL_POLICY_HELPER_SCOPE void
getrusage_timespec_add_tsc_result(long *secp, long *nsecp,
		unsigned long tsc, unsigned long clocks_per_sec)
{
	long sec_delta;
	long ns_delta;

	if (!clocks_per_sec) {
		return;
	}

	sec_delta = tsc / clocks_per_sec;
	ns_delta = NS_PER_SEC * (tsc % clocks_per_sec) / clocks_per_sec;
	if (ns_delta >= NS_PER_SEC) {
		ns_delta -= NS_PER_SEC;
		sec_delta++;
	}

	*secp += sec_delta;
	*nsecp += ns_delta;
	while (*nsecp >= NS_PER_SEC) {
		(*secp)++;
		*nsecp -= NS_PER_SEC;
	}
}

SYSCALL_POLICY_HELPER_SCOPE void
getrusage_fill_timespec_result(struct rusage *usage, long utime_sec,
		long utime_nsec, long stime_sec, long stime_nsec,
		long maxrss)
{
	usage->ru_utime.tv_sec = utime_sec;
	usage->ru_utime.tv_usec = utime_nsec / 1000;
	usage->ru_stime.tv_sec = stime_sec;
	usage->ru_stime.tv_usec = stime_nsec / 1000;
	usage->ru_maxrss = getrusage_maxrss_kb_result(maxrss);
}

static void *cputime_field(void *base, size_t offset)
{
	return (char *)base + offset;
}

static void cputime_timespec_add_tsc(struct timespec *ts, unsigned long tsc,
		unsigned long clocks_per_sec)
{
	getrusage_timespec_add_tsc_result(&ts->tv_sec, &ts->tv_nsec, tsc,
			clocks_per_sec);
}

static void cputime_for_each_thread(void *proc,
		const struct syscall_cputime_offsets *offsets,
		void (*visit)(void *thread, void *arg), void *arg)
{
	struct list_head *head = cputime_field(proc,
			offsets->proc_threads_list_offset);
	struct list_head *pos;

	for (pos = head->next; pos != head; pos = pos->next) {
		void *thread = (char *)pos - offsets->thread_siblings_list_offset;
		visit(thread, arg);
	}
}

struct getrusage_request_arg {
	void *current;
	const struct syscall_cputime_offsets *offsets;
	syscall_interrupt_cpu_fn_t interrupt_fn;
};

static void getrusage_request_visit(void *thread, void *argp)
{
	struct getrusage_request_arg *arg = argp;
	const struct syscall_cputime_offsets *o = arg->offsets;
	int update_action = getrusage_thread_update_action_result(
			thread == arg->current,
			*(int *)cputime_field(thread, o->thread_status_offset),
			*(int *)cputime_field(thread, o->thread_in_kernel_offset));

	if (getrusage_thread_times_update_prepare_result((unsigned long)thread,
				o->thread_times_update_offset, update_action)) {
		arg->interrupt_fn(*(int *)cputime_field(thread,
					o->thread_cpu_id_offset));
	}
}

struct getrusage_collect_arg {
	struct timespec *utime;
	struct timespec *stime;
	const struct syscall_cputime_offsets *offsets;
	unsigned long clocks_per_sec;
	syscall_cpu_pause_fn_t pause_fn;
};

static void getrusage_collect_visit(void *thread, void *argp)
{
	struct getrusage_collect_arg *arg = argp;
	const struct syscall_cputime_offsets *o = arg->offsets;

	while (!*(int *)cputime_field(thread, o->thread_times_update_offset)) {
		arg->pause_fn();
	}
	cputime_timespec_add_tsc(arg->utime,
			*(unsigned long *)cputime_field(thread,
				o->thread_user_tsc_offset),
			arg->clocks_per_sec);
	cputime_timespec_add_tsc(arg->stime,
			*(unsigned long *)cputime_field(thread,
				o->thread_system_tsc_offset),
			arg->clocks_per_sec);
}

SYSCALL_POLICY_HELPER_SCOPE long
getrusage_body_result(int who, unsigned long usage_addr, void *thread,
		unsigned long clocks_per_sec,
		const struct syscall_cputime_offsets *offsets,
		syscall_threads_lock_fn_t lock_fn,
		syscall_threads_unlock_fn_t unlock_fn, void *lock_arg,
		syscall_interrupt_cpu_fn_t interrupt_fn,
		syscall_cpu_pause_fn_t pause_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	struct rusage usage;
	void *proc;
	int error;
	int dispatch;

	error = getrusage_who_result(who);
	if (error) {
		return error;
	}
	if (!thread || !offsets || !copy_to_fn) {
		return -EFAULT;
	}

	proc = *(void **)cputime_field(thread, offsets->thread_proc_offset);
	if (!proc) {
		return -EFAULT;
	}

	memset(&usage, '\0', sizeof(usage));
	dispatch = getrusage_dispatch_result(who);
	if (dispatch == GETRUSAGE_DISPATCH_SELF) {
		struct timespec utime;
		struct timespec stime;
		struct getrusage_request_arg req = {
			.current = thread,
			.offsets = offsets,
			.interrupt_fn = interrupt_fn,
		};
		struct getrusage_collect_arg collect = {
			.utime = &utime,
			.stime = &stime,
			.offsets = offsets,
			.clocks_per_sec = clocks_per_sec,
			.pause_fn = pause_fn,
		};

		if (!lock_fn || !unlock_fn || !interrupt_fn || !pause_fn) {
			return -EFAULT;
		}
		memset(&utime, '\0', sizeof(utime));
		memset(&stime, '\0', sizeof(stime));
		lock_fn(proc, lock_arg);
		cputime_for_each_thread(proc, offsets, getrusage_request_visit,
				&req);
		utime = *(struct timespec *)cputime_field(proc,
				offsets->proc_utime_offset);
		stime = *(struct timespec *)cputime_field(proc,
				offsets->proc_stime_offset);
		cputime_for_each_thread(proc, offsets, getrusage_collect_visit,
				&collect);
		unlock_fn(proc, lock_arg);
		getrusage_fill_timespec_result(&usage, utime.tv_sec,
				utime.tv_nsec, stime.tv_sec, stime.tv_nsec,
				*(long *)cputime_field(proc,
					offsets->proc_maxrss_offset));
	}
	else if (dispatch == GETRUSAGE_DISPATCH_CHILDREN) {
		struct timespec *utime = cputime_field(proc,
				offsets->proc_utime_children_offset);
		struct timespec *stime = cputime_field(proc,
				offsets->proc_stime_children_offset);

		getrusage_fill_timespec_result(&usage, utime->tv_sec,
				utime->tv_nsec, stime->tv_sec, stime->tv_nsec,
				*(long *)cputime_field(proc,
					offsets->proc_maxrss_children_offset));
	}
	else if (dispatch == GETRUSAGE_DISPATCH_THREAD) {
		struct timespec utime = { 0 };
		struct timespec stime = { 0 };

		cputime_timespec_add_tsc(&utime,
				*(unsigned long *)cputime_field(thread,
					offsets->thread_user_tsc_offset),
				clocks_per_sec);
		cputime_timespec_add_tsc(&stime,
				*(unsigned long *)cputime_field(thread,
					offsets->thread_system_tsc_offset),
				clocks_per_sec);
		getrusage_fill_timespec_result(&usage, utime.tv_sec,
				utime.tv_nsec, stime.tv_sec, stime.tv_nsec,
				*(long *)cputime_field(proc,
					offsets->proc_maxrss_offset));
	}
	else {
		return -EINVAL;
	}

	return copy_to_fn(usage_addr, &usage, sizeof(usage)) ? -EFAULT : 0;
}

struct clock_process_request_arg {
	void *current;
	const struct syscall_cputime_offsets *offsets;
	syscall_interrupt_cpu_fn_t interrupt_fn;
};

static void clock_process_request_visit(void *thread, void *argp)
{
	struct clock_process_request_arg *arg = argp;
	const struct syscall_cputime_offsets *o = arg->offsets;

	if (thread != arg->current &&
	    *(int *)cputime_field(thread, o->thread_status_offset) ==
		    PS_RUNNING &&
	    !*(int *)cputime_field(thread, o->thread_in_kernel_offset)) {
		*(int *)cputime_field(thread, o->thread_times_update_offset) = 0;
		arg->interrupt_fn(*(int *)cputime_field(thread,
					o->thread_cpu_id_offset));
	}
}

struct clock_process_collect_arg {
	struct timespec *total;
	const struct syscall_cputime_offsets *offsets;
	unsigned long clocks_per_sec;
	syscall_cpu_pause_fn_t pause_fn;
};

static void clock_process_collect_visit(void *thread, void *argp)
{
	struct clock_process_collect_arg *arg = argp;
	const struct syscall_cputime_offsets *o = arg->offsets;
	unsigned long tsc;

	while (!*(int *)cputime_field(thread, o->thread_times_update_offset)) {
		arg->pause_fn();
	}
	tsc = *(unsigned long *)cputime_field(thread,
			o->thread_user_tsc_offset) +
		*(unsigned long *)cputime_field(thread,
			o->thread_system_tsc_offset);
	cputime_timespec_add_tsc(arg->total, tsc, arg->clocks_per_sec);
}

static void clock_process_cputime_result(void *thread, void *proc,
		unsigned long clocks_per_sec,
		const struct syscall_cputime_offsets *offsets,
		syscall_threads_lock_fn_t lock_fn,
		syscall_threads_unlock_fn_t unlock_fn, void *lock_arg,
		syscall_interrupt_cpu_fn_t interrupt_fn,
		syscall_cpu_pause_fn_t pause_fn, struct timespec *out)
{
	struct clock_process_request_arg req = {
		.current = thread,
		.offsets = offsets,
		.interrupt_fn = interrupt_fn,
	};
	struct clock_process_collect_arg collect = {
		.total = out,
		.offsets = offsets,
		.clocks_per_sec = clocks_per_sec,
		.pause_fn = pause_fn,
	};
	struct timespec *stime;

	lock_fn(proc, lock_arg);
	cputime_for_each_thread(proc, offsets, clock_process_request_visit,
			&req);
	*out = *(struct timespec *)cputime_field(proc,
			offsets->proc_utime_offset);
	stime = cputime_field(proc, offsets->proc_stime_offset);
	ts_add(out, stime);
	cputime_for_each_thread(proc, offsets, clock_process_collect_visit,
			&collect);
	unlock_fn(proc, lock_arg);
}

SYSCALL_POLICY_HELPER_SCOPE long
clock_gettime_body_result(int clock_id, unsigned long ts_addr,
		int local_support, int syscall_nr, void *thread,
		unsigned long clocks_per_sec,
		const struct syscall_cputime_offsets *offsets,
		syscall_gettime_fn_t gettime_fn,
		syscall_copy_to_user_fn_t copy_to_fn,
		syscall_do_syscall2_fn_t syscall2_fn,
		syscall_threads_lock_fn_t lock_fn,
		syscall_threads_unlock_fn_t unlock_fn, void *lock_arg,
		syscall_interrupt_cpu_fn_t interrupt_fn,
		syscall_cpu_pause_fn_t pause_fn)
{
	struct timespec ts = { 0 };
	void *proc;
	int dispatch = clock_gettime_dispatch(clock_id, local_support,
			ts_addr != 0);

	if (dispatch == TIME_DISPATCH_NOOP) {
		return 0;
	}
	if (!copy_to_fn) {
		return -EFAULT;
	}
	if (dispatch == TIME_DISPATCH_LOCAL_REALTIME) {
		if (!gettime_fn) {
			return -EFAULT;
		}
		gettime_fn(&ts);
		return copy_to_fn(ts_addr, &ts, sizeof(ts));
	}
	if (dispatch == TIME_DISPATCH_PROCESS_CPUTIME ||
	    dispatch == TIME_DISPATCH_THREAD_CPUTIME) {
		if (!thread || !offsets) {
			return -EFAULT;
		}
		proc = *(void **)cputime_field(thread,
				offsets->thread_proc_offset);
		if (!proc) {
			return -EFAULT;
		}
		if (dispatch == TIME_DISPATCH_PROCESS_CPUTIME) {
			if (!lock_fn || !unlock_fn || !interrupt_fn || !pause_fn) {
				return -EFAULT;
			}
			clock_process_cputime_result(thread, proc, clocks_per_sec,
					offsets, lock_fn, unlock_fn, lock_arg,
					interrupt_fn, pause_fn, &ts);
		}
		else {
			cputime_timespec_add_tsc(&ts,
					*(unsigned long *)cputime_field(thread,
						offsets->thread_user_tsc_offset) +
					*(unsigned long *)cputime_field(thread,
						offsets->thread_system_tsc_offset),
					clocks_per_sec);
		}
		return copy_to_fn(ts_addr, &ts, sizeof(ts));
	}
	if (!syscall2_fn) {
		return -EFAULT;
	}
	return syscall2_fn(syscall_nr, clock_id, ts_addr);
}

SYSCALL_POLICY_HELPER_SCOPE int
exit_code_status_result(int code)
{
	return (code >> 8) & 255;
}

SYSCALL_POLICY_HELPER_SCOPE int
exit_code_signal_result(int code)
{
	return code & 255;
}

SYSCALL_POLICY_HELPER_SCOPE int
exit_syscall_code_result(int status)
{
	return (status & 255) << 8;
}

SYSCALL_POLICY_HELPER_SCOPE long
exit_body_result(int status, syscall_exit_fn_t exit_fn)
{
	if (exit_fn)
		exit_fn(exit_syscall_code_result(status));
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
exit_group_body_result(int status, int pid,
		syscall_exit_group_log_fn_t log_fn,
		syscall_terminate_fn_t terminate_fn)
{
	if (log_fn)
		log_fn(pid);
	if (terminate_fn)
		terminate_fn(status, 0);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
sched_yield_body_result(void *cpu_local, size_t flags_offset,
		size_t runq_len_offset, size_t runq_lock_offset,
		unsigned int need_resched_flag,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn,
		syscall_schedule_fn_t schedule_fn)
{
	char *base = cpu_local;
	unsigned int *flagsp = (unsigned int *)(base + flags_offset);
	size_t *runq_lenp = (size_t *)(base + runq_len_offset);
	void *runq_lock = base + runq_lock_offset;
	long irqstate = 0;
	int do_schedule = 0;

	if (lock_fn)
		irqstate = lock_fn(runq_lock);
	if ((*flagsp & need_resched_flag) || *runq_lenp > 1) {
		*flagsp &= ~need_resched_flag;
		do_schedule = 1;
	}
	if (unlock_fn)
		unlock_fn(runq_lock, irqstate);

	if (do_schedule && schedule_fn)
		schedule_fn();
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
thread_exit_signal_result(int ptrace, int termsig)
{
	return ptrace ? SIGCHLD : termsig;
}

SYSCALL_POLICY_HELPER_SCOPE int
thread_exit_signal_report_needed_result(const void *report_proc)
{
	return report_proc != NULL;
}

SYSCALL_POLICY_HELPER_SCOPE int
sigchld_code_result(int exit_status)
{
	if (exit_status & 0x7f) {
		return (exit_status & 0x80) ? CLD_DUMPED : CLD_KILLED;
	}
	return CLD_EXITED;
}

SYSCALL_POLICY_HELPER_SCOPE long
thread_exit_signal_body_result(void *thread,
		size_t thread_report_proc_offset, size_t thread_ptrace_offset,
		size_t thread_termsig_offset,
		size_t thread_exit_status_offset, size_t thread_tid_offset,
		size_t thread_user_tsc_offset, size_t thread_system_tsc_offset,
		size_t proc_pid_offset, size_t proc_waitpid_q_offset,
		syscall_tsc_to_ts_fn_t tsc_to_ts_fn,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn, thread_exit_log_fn_t log_fn)
{
	char *thread_base = thread;
	void *report_proc;
	char *report_base;
	struct siginfo info;
	struct timespec ats;
	int sig;
	long error;

	if (!thread) {
		return -EINVAL;
	}
	report_proc = *(void **)(thread_base + thread_report_proc_offset);
	if (!thread_exit_signal_report_needed_result(report_proc)) {
		return 0;
	}
	if (!tsc_to_ts_fn || !timespec_to_jiffy_fn || !do_kill_fn || !wake_fn) {
		return -EINVAL;
	}

	report_base = report_proc;
	sig = thread_exit_signal_result(*(int *)(thread_base +
				thread_ptrace_offset),
			*(int *)(thread_base + thread_termsig_offset));
	memset(&info, '\0', sizeof(info));
	info.si_signo = sig;
	info.si_code = sigchld_code_result(*(int *)(thread_base +
				thread_exit_status_offset));
	info._sifields._sigchld.si_pid =
		*(int *)(thread_base + thread_tid_offset);
	info._sifields._sigchld.si_status =
		*(int *)(thread_base + thread_exit_status_offset);
	tsc_to_ts_fn(*(unsigned long *)(thread_base + thread_user_tsc_offset),
			&ats);
	info._sifields._sigchld.si_utime = timespec_to_jiffy_fn(&ats);
	tsc_to_ts_fn(*(unsigned long *)(thread_base + thread_system_tsc_offset),
			&ats);
	info._sifields._sigchld.si_stime = timespec_to_jiffy_fn(&ats);
	error = do_kill_fn(NULL, *(int *)(report_base + proc_pid_offset), -1,
			sig, &info, 0);
	if (log_fn) {
		log_fn(sig, error);
	}
	wake_fn(report_base + proc_waitpid_q_offset);
	return error;
}

SYSCALL_POLICY_HELPER_SCOPE long
finalize_process_parent_notify_body_result(void *proc,
		size_t proc_parent_offset, size_t proc_pid_offset,
		size_t proc_group_exit_status_offset, size_t proc_termsig_offset,
		size_t proc_utime_offset, size_t proc_stime_offset,
		size_t proc_waitpid_q_offset,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn, thread_exit_log_fn_t log_fn)
{
	char *proc_base = proc;
	void *parent;
	char *parent_base;
	int termsig;
	long error = 0;

	if (!proc) {
		return -EINVAL;
	}
	parent = *(void **)(proc_base + proc_parent_offset);
	if (!parent) {
		return -EINVAL;
	}
	if (!wake_fn) {
		return -EINVAL;
	}

	parent_base = parent;
	termsig = *(int *)(proc_base + proc_termsig_offset);
	if (finalize_process_parent_signal_needed_result(termsig)) {
		struct siginfo info;
		int exit_status;

		if (!timespec_to_jiffy_fn || !do_kill_fn) {
			return -EINVAL;
		}
		exit_status = *(int *)(proc_base +
				proc_group_exit_status_offset);
		memset(&info, '\0', sizeof(info));
		info.si_signo = SIGCHLD;
		info.si_code = sigchld_code_result(exit_status);
		info._sifields._sigchld.si_pid =
			*(int *)(proc_base + proc_pid_offset);
		info._sifields._sigchld.si_status = exit_status;
		info._sifields._sigchld.si_utime =
			timespec_to_jiffy_fn((void *)(proc_base +
						proc_utime_offset));
		info._sifields._sigchld.si_stime =
			timespec_to_jiffy_fn((void *)(proc_base +
						proc_stime_offset));
		error = do_kill_fn(NULL, *(int *)(parent_base +
					proc_pid_offset), -1, SIGCHLD, &info, 0);
		if (log_fn) {
			log_fn(termsig, error);
		}
	}

	wake_fn(parent_base + proc_waitpid_q_offset);
	return error;
}

SYSCALL_POLICY_HELPER_SCOPE long
finalize_process_body_result(void *proc, const void *pid1, void *lock_node,
		size_t proc_parent_offset, size_t proc_status_offset,
		size_t proc_update_lock_offset, size_t proc_pid_offset,
		size_t proc_group_exit_status_offset, size_t proc_termsig_offset,
		size_t proc_utime_offset, size_t proc_stime_offset,
		size_t proc_waitpid_q_offset, wait_lock_unlock_fn_t lock_fn,
		wait_lock_unlock_fn_t unlock_fn,
		wait_thread_side_effect_fn_t release_fn,
		finalize_wakeup_log_fn_t wakeup_log_fn,
		syscall_timespec_to_jiffy_fn_t timespec_to_jiffy_fn,
		syscall_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn, thread_exit_log_fn_t log_fn)
{
	char *proc_base = proc;
	void *parent;
	void *update_lock;
	int parent_is_pid1;

	if (!proc || !lock_node || !lock_fn || !unlock_fn || !release_fn) {
		return -EINVAL;
	}

	update_lock = proc_base + proc_update_lock_offset;
	lock_fn(update_lock, lock_node);
	parent = *(void **)(proc_base + proc_parent_offset);
	*(int *)(proc_base + proc_status_offset) = PS_ZOMBIE;
	parent_is_pid1 = finalize_process_parent_is_pid1_result(parent, pid1);
	unlock_fn(update_lock, lock_node);

	if (parent_is_pid1) {
		release_fn(proc);
		return 0;
	}

	if (wakeup_log_fn) {
		wakeup_log_fn();
	}
	return finalize_process_parent_notify_body_result(proc,
			proc_parent_offset, proc_pid_offset,
			proc_group_exit_status_offset, proc_termsig_offset,
			proc_utime_offset, proc_stime_offset,
			proc_waitpid_q_offset, timespec_to_jiffy_fn, do_kill_fn,
			wake_fn, log_fn);
}

SYSCALL_POLICY_HELPER_SCOPE int
exit_group_status_claimed_result(unsigned long old_exit_status)
{
	return (old_exit_status & 0x0000000100000000UL) ? 1 : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_group_status_update_failed_result(unsigned long observed_status,
		unsigned long expected_status)
{
	return observed_status != expected_status;
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_host_exit_needed_result(int nohost)
{
	return !nohost;
}

SYSCALL_POLICY_HELPER_SCOPE long
terminate_mcexec_body_result(void *proc, struct syscall_request *request,
		int rc, int sig, int cpu, int exit_group_nr,
		size_t proc_group_exit_status_offset,
		size_t proc_nohost_offset,
		terminate_mcexec_cmpxchg_fn_t cmpxchg_fn,
		terminate_mcexec_syscall_fn_t syscall_fn)
{
	char *proc_base = proc;
	unsigned long *statusp;
	unsigned long old_exit_status;
	unsigned long observed_status;
	unsigned long exit_status;
	int *nohostp;

	if (!proc || !request || !cmpxchg_fn) {
		return -EINVAL;
	}

	statusp = (unsigned long *)(proc_base + proc_group_exit_status_offset);
	old_exit_status = *statusp;
	if (exit_group_status_claimed_result(old_exit_status)) {
		return 0;
	}

	exit_status = exit_group_status_result(rc, sig);
	observed_status = cmpxchg_fn(statusp, old_exit_status, exit_status);
	if (terminate_group_status_update_failed_result(observed_status,
				old_exit_status)) {
		return 0;
	}

	nohostp = (int *)(proc_base + proc_nohost_offset);
	if (!terminate_host_exit_needed_result(*nohostp)) {
		return 0;
	}
	if (!syscall_fn) {
		return -EINVAL;
	}

	request->number = exit_group_nr;
	request->args[0] = *statusp;
	*nohostp = 1;
	return syscall_fn(request, cpu);
}

SYSCALL_POLICY_HELPER_SCOPE int
sync_child_event_needed_result(int has_event, int inherit, int pid)
{
	return has_event && (inherit || pid != 0);
}

SYSCALL_POLICY_HELPER_SCOPE int
sync_child_event_pid_action_result(int pid)
{
	if (pid == 0)
		return SYNC_CHILD_EVENT_ACTION_CHILD_TOTAL;
	if (pid > 0)
		return SYNC_CHILD_EVENT_ACTION_SET_COUNT;
	return SYNC_CHILD_EVENT_ACTION_NONE;
}

static long
sync_child_event_apply_action_result(void *event, int action,
		size_t counter_id_offset, size_t count_offset,
		size_t child_count_total_offset,
		sync_child_perf_read_fn_t read_fn,
		sync_child_atomic64_set_fn_t set_fn)
{
	char *base = event;
	int counter_id;
	unsigned long count;

	if (action == SYNC_CHILD_EVENT_ACTION_CHILD_TOTAL) {
		unsigned long *totalp;

		counter_id = *(int *)(base + counter_id_offset);
		count = read_fn(counter_id);
		totalp = (unsigned long *)(base + child_count_total_offset);
		*totalp += count;
		return 0;
	}

	if (action == SYNC_CHILD_EVENT_ACTION_SET_COUNT) {
		if (!set_fn) {
			return -EINVAL;
		}
		counter_id = *(int *)(base + counter_id_offset);
		count = read_fn(counter_id);
		set_fn(base + count_offset, count);
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
sync_child_event_body_result(void *event, int inherit, int pid,
		size_t group_leader_offset, size_t event_pid_offset,
		size_t counter_id_offset, size_t count_offset,
		size_t child_count_total_offset, size_t sibling_list_offset,
		size_t group_entry_offset, sync_child_perf_read_fn_t read_fn,
		sync_child_atomic64_set_fn_t set_fn)
{
	void *leader;
	char *event_base;
	char *leader_base;
	struct list_head *head;
	struct list_head *node;
	int leader_pid;
	int leader_action;
	int sub_action;
	long rc;

	if (!sync_child_event_needed_result(event != NULL, inherit, pid)) {
		return 0;
	}
	if (!read_fn) {
		return -EINVAL;
	}

	event_base = event;
	leader = *(void **)(event_base + group_leader_offset);
	if (!leader) {
		return -EINVAL;
	}

	leader_base = leader;
	leader_pid = *(int *)(leader_base + event_pid_offset);
	leader_action = sync_child_event_pid_action_result(leader_pid);
	if (leader_action == SYNC_CHILD_EVENT_ACTION_NONE) {
		return 0;
	}

	rc = sync_child_event_apply_action_result(leader, leader_action,
			counter_id_offset, count_offset,
			child_count_total_offset, read_fn, set_fn);
	if (rc) {
		return rc;
	}

	sub_action = sync_child_event_pid_action_result(pid);
	if (sub_action == SYNC_CHILD_EVENT_ACTION_NONE) {
		return 0;
	}

	head = (struct list_head *)(leader_base + sibling_list_offset);
	for (node = head->next; node && node != head; node = node->next) {
		void *sub = (char *)node - group_entry_offset;

		rc = sync_child_event_apply_action_result(sub, sub_action,
				counter_id_offset, count_offset,
				child_count_total_offset, read_fn, set_fn);
		if (rc) {
			return rc;
		}
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
perf_event_read_value_body_result(void *event, void *thread,
		int exclude_user, int exclude_kernel, int inherit,
		size_t event_pid_offset, size_t use_invariant_tsc_offset,
		size_t count_offset, size_t child_count_total_offset,
		size_t base_user_tsc_offset, size_t stopped_user_tsc_offset,
		size_t user_accum_count_offset, size_t base_system_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset,
		size_t thread_user_tsc_offset, size_t thread_system_tsc_offset,
		perf_event_update_fn_t update_fn,
		syscall_atomic64_read_fn_t atomic_read_fn)
{
	char *event_base = event;
	char *thread_base = thread;
	unsigned long pmc_count = 0;
	unsigned long rtn_count;
	unsigned long cur_user_tsc;
	unsigned long cur_system_tsc;
	long stopped_user_tsc;
	long stopped_system_tsc;
	int pid;

	if (!event || !thread || !atomic_read_fn) {
		return 0;
	}

	stopped_user_tsc = *(long *)(event_base + stopped_user_tsc_offset);
	if (stopped_user_tsc) {
		cur_user_tsc = stopped_user_tsc;
	}
	else {
		cur_user_tsc = *(unsigned long *)(thread_base +
				thread_user_tsc_offset);
	}

	stopped_system_tsc = *(long *)(event_base + stopped_system_tsc_offset);
	if (stopped_system_tsc) {
		cur_system_tsc = stopped_system_tsc;
	}
	else {
		cur_system_tsc = *(unsigned long *)(thread_base +
				thread_system_tsc_offset);
	}

	pid = *(int *)(event_base + event_pid_offset);
	if (pid == 0) {
		int use_invariant_tsc =
			*(int *)(event_base + use_invariant_tsc_offset);

		if (use_invariant_tsc) {
			if (!exclude_user) {
				pmc_count += cur_user_tsc -
					*(long *)(event_base +
						base_user_tsc_offset) +
					*(long *)(event_base +
						user_accum_count_offset);
			}
			if (!exclude_kernel) {
				pmc_count += cur_system_tsc -
					*(long *)(event_base +
						base_system_tsc_offset) +
					*(long *)(event_base +
						system_accum_count_offset);
			}
		}
		else if (update_fn) {
			update_fn(event);
		}
	}

	rtn_count = atomic_read_fn(event_base + count_offset) + pmc_count;
	if (inherit) {
		rtn_count += *(unsigned long *)(event_base +
				child_count_total_offset);
	}

	return rtn_count;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
perf_event_read_value_entry_body_result(void *event, void *thread,
		size_t event_attr_offset, size_t event_pid_offset,
		size_t use_invariant_tsc_offset, size_t count_offset,
		size_t child_count_total_offset, size_t base_user_tsc_offset,
		size_t stopped_user_tsc_offset, size_t user_accum_count_offset,
		size_t base_system_tsc_offset, size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset,
		size_t thread_user_tsc_offset, size_t thread_system_tsc_offset,
		perf_read_attr_flags_fn_t attr_flags_fn,
		perf_event_update_fn_t update_fn,
		syscall_atomic64_read_fn_t atomic_read_fn)
{
	char *event_base = event;
	int exclude_user;
	int exclude_kernel;
	int inherit;
	int ret;

	if (!event || !thread || !attr_flags_fn) {
		return 0;
	}

	ret = attr_flags_fn(event_base + event_attr_offset,
			&exclude_user, &exclude_kernel, &inherit);
	if (ret) {
		return 0;
	}

	return perf_event_read_value_body_result(event, thread, exclude_user,
			exclude_kernel, inherit, event_pid_offset,
			use_invariant_tsc_offset, count_offset,
			child_count_total_offset, base_user_tsc_offset,
			stopped_user_tsc_offset, user_accum_count_offset,
			base_system_tsc_offset, stopped_system_tsc_offset,
			system_accum_count_offset, thread_user_tsc_offset,
			thread_system_tsc_offset, update_fn, atomic_read_fn);
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_read_one_body_result(void *event, unsigned long buf_addr,
		perf_read_value_fn_t read_value_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	unsigned long values[1];
	size_t size = sizeof(values[0]);

	if (!event || !read_value_fn || !copy_to_fn) {
		return -EINVAL;
	}

	values[0] = read_value_fn(event);
	if (copy_to_fn(buf_addr, values, size)) {
		return -EFAULT;
	}

	return size;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_read_group_body_result(void *event, unsigned long buf_addr,
		size_t group_leader_offset, size_t nr_siblings_offset,
		size_t sibling_list_offset, size_t group_entry_offset,
		perf_read_value_fn_t read_value_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	char *event_base = event;
	void *leader;
	char *leader_base;
	struct list_head *head;
	struct list_head *node;
	size_t value_size = sizeof(unsigned long);
	size_t ret;
	unsigned long leader_count;
	long long values[2];

	if (!event || !read_value_fn || !copy_to_fn) {
		return -EINVAL;
	}

	leader = *(void **)(event_base + group_leader_offset);
	if (!leader) {
		return -EINVAL;
	}

	leader_base = leader;
	leader_count = read_value_fn(leader);
	values[0] = 1 + *(int *)(leader_base + nr_siblings_offset);
	values[1] = leader_count;
	ret = sizeof(values);

	if (copy_to_fn(buf_addr, values, ret)) {
		return -EFAULT;
	}

	head = (struct list_head *)(leader_base + sibling_list_offset);
	for (node = head->next; node && node != head; node = node->next) {
		void *sub = (char *)node - group_entry_offset;
		unsigned long value = read_value_fn(sub);

		if (copy_to_fn(buf_addr + ret, &value, value_size)) {
			return -EFAULT;
		}

		ret += value_size;
	}

	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_read_body_result(void *event, unsigned long buf_addr,
		unsigned long read_format, unsigned long group_flag,
		perf_read_dispatch_fn_t read_group_fn,
		perf_read_dispatch_fn_t read_one_fn)
{
	if (!event) {
		return -EINVAL;
	}

	if (read_format & group_flag) {
		if (!read_group_fn) {
			return -EINVAL;
		}
		return read_group_fn(event, read_format, buf_addr);
	}

	if (!read_one_fn) {
		return -EINVAL;
	}
	return read_one_fn(event, read_format, buf_addr);
}

static unsigned long perf_event_bit_result(int index);

SYSCALL_POLICY_HELPER_SCOPE int
perf_counter_set_body_result(void *event, int exclude_kernel, int exclude_user,
		int counter_id, unsigned long hw_config,
		size_t extra_reg_reg_offset, int kernel_mode, int user_mode,
		perf_counter_extra_set_fn_t set_extra_fn,
		perf_counter_init_raw_fn_t init_raw_fn)
{
	char *event_base = event;
	int mode = 0;

	if (!event || !init_raw_fn) {
		return -EINVAL;
	}
	if (!exclude_kernel) {
		mode |= kernel_mode;
	}
	if (!exclude_user) {
		mode |= user_mode;
	}

	if (*(unsigned int *)(event_base + extra_reg_reg_offset)) {
		if (!set_extra_fn) {
			return -EINVAL;
		}
		if (set_extra_fn(event)) {
			return -1;
		}
	}

	return init_raw_fn(counter_id, hw_config, mode);
}

SYSCALL_POLICY_HELPER_SCOPE int
perf_counter_set_entry_body_result(void *event, size_t event_attr_offset,
		size_t event_counter_id_offset, size_t event_hw_config_offset,
		size_t extra_reg_reg_offset, int kernel_mode, int user_mode,
		perf_counter_attr_flags_fn_t attr_flags_fn,
		perf_counter_extra_set_fn_t set_extra_fn,
		perf_counter_init_raw_fn_t init_raw_fn)
{
	char *event_base = event;
	int exclude_kernel;
	int exclude_user;
	int ret;

	if (!event || !attr_flags_fn) {
		return -EINVAL;
	}

	ret = attr_flags_fn(event_base + event_attr_offset,
			&exclude_kernel, &exclude_user);
	if (ret) {
		return ret;
	}

	return perf_counter_set_body_result(event, exclude_kernel,
			exclude_user,
			*(int *)(event_base + event_counter_id_offset),
			*(unsigned long *)(event_base + event_hw_config_offset),
			extra_reg_reg_offset, kernel_mode, user_mode,
			set_extra_fn, init_raw_fn);
}

static long
perf_start_apply_event_body_result(void *event, void *thread,
		unsigned long *counter_mask, size_t counter_id_offset,
		size_t state_offset, size_t use_invariant_tsc_offset,
		size_t base_user_tsc_offset, size_t stopped_user_tsc_offset,
		size_t user_accum_count_offset,
		size_t base_system_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset,
		size_t thread_user_tsc_offset,
		size_t thread_system_tsc_offset,
		int inactive_state, int active_state,
		perf_counter_mask_check_fn_t mask_check_fn,
		perf_event_int_fn_t set_period_fn,
		perf_event_int_fn_t counter_set_fn)
{
	char *event_base = event;
	char *thread_base = thread;
	int counter_id = *(int *)(event_base + counter_id_offset);
	unsigned long bit = perf_event_bit_result(counter_id);

	if (!bit || !mask_check_fn(bit) ||
			*(int *)(event_base + state_offset) != inactive_state) {
		return 0;
	}

	if (*(int *)(event_base + use_invariant_tsc_offset)) {
		long long *stopped_user =
			(long long *)(event_base + stopped_user_tsc_offset);
		long long *base_user =
			(long long *)(event_base + base_user_tsc_offset);
		long long *user_accum =
			(long long *)(event_base + user_accum_count_offset);
		long long *stopped_system =
			(long long *)(event_base + stopped_system_tsc_offset);
		long long *base_system =
			(long long *)(event_base + base_system_tsc_offset);
		long long *system_accum =
			(long long *)(event_base + system_accum_count_offset);

		if (*stopped_user) {
			*user_accum += *stopped_user - *base_user;
			*stopped_user = 0;
		}
		*base_user = *(long long *)(thread_base + thread_user_tsc_offset);

		if (*stopped_system) {
			*system_accum += *stopped_system - *base_system;
			*stopped_system = 0;
		}
		*base_system =
			*(long long *)(thread_base + thread_system_tsc_offset);
	}
	else {
		if (!set_period_fn || !counter_set_fn) {
			return -EINVAL;
		}
		set_period_fn(event);
		counter_set_fn(event);
		*counter_mask |= bit;
	}

	*(int *)(event_base + state_offset) = active_state;
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_start_body_result(void *event, void *thread,
		size_t group_leader_offset, size_t sibling_list_offset,
		size_t group_entry_offset, size_t counter_id_offset,
		size_t state_offset, size_t use_invariant_tsc_offset,
		size_t base_user_tsc_offset, size_t stopped_user_tsc_offset,
		size_t user_accum_count_offset,
		size_t base_system_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset,
		size_t thread_user_tsc_offset,
		size_t thread_system_tsc_offset,
		size_t thread_proc_offset, size_t proc_perf_status_offset,
		int inactive_state, int active_state, int pp_count,
		perf_counter_mask_check_fn_t mask_check_fn,
		perf_event_int_fn_t set_period_fn,
		perf_event_int_fn_t counter_set_fn,
		perf_counter_start_fn_t counter_start_fn)
{
	char *event_base = event;
	char *thread_base = thread;
	void *leader;
	char *leader_base;
	struct list_head *head;
	struct list_head *node;
	unsigned long counter_mask = 0;
	void *proc;
	long rc;

	if (!event || !thread || !mask_check_fn) {
		return -EINVAL;
	}

	leader = *(void **)(event_base + group_leader_offset);
	if (!leader) {
		return -EINVAL;
	}
	leader_base = leader;

	rc = perf_start_apply_event_body_result(leader, thread, &counter_mask,
			counter_id_offset, state_offset,
			use_invariant_tsc_offset, base_user_tsc_offset,
			stopped_user_tsc_offset, user_accum_count_offset,
			base_system_tsc_offset, stopped_system_tsc_offset,
			system_accum_count_offset, thread_user_tsc_offset,
			thread_system_tsc_offset, inactive_state, active_state,
			mask_check_fn, set_period_fn, counter_set_fn);
	if (rc) {
		return rc;
	}

	head = (struct list_head *)(leader_base + sibling_list_offset);
	for (node = head->next; node && node != head; node = node->next) {
		void *sub = (char *)node - group_entry_offset;

		rc = perf_start_apply_event_body_result(sub, thread,
				&counter_mask, counter_id_offset, state_offset,
				use_invariant_tsc_offset, base_user_tsc_offset,
				stopped_user_tsc_offset, user_accum_count_offset,
				base_system_tsc_offset, stopped_system_tsc_offset,
				system_accum_count_offset, thread_user_tsc_offset,
				thread_system_tsc_offset, inactive_state,
				active_state, mask_check_fn, set_period_fn,
				counter_set_fn);
		if (rc) {
			return rc;
		}
	}

	if (counter_mask) {
		if (!counter_start_fn) {
			return -EINVAL;
		}
		counter_start_fn(counter_mask);
	}

	proc = *(void **)(thread_base + thread_proc_offset);
	if (!proc) {
		return -EINVAL;
	}
	*(int *)((char *)proc + proc_perf_status_offset) = pp_count;

	return 0;
}

static long
perf_reset_apply_event_body_result(void *event, void *thread,
		size_t counter_id_offset, size_t use_invariant_tsc_offset,
		size_t base_user_tsc_offset, size_t stopped_user_tsc_offset,
		size_t user_accum_count_offset,
		size_t base_system_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset, size_t count_offset,
		size_t thread_user_tsc_offset,
		size_t thread_system_tsc_offset,
		perf_counter_mask_check_fn_t mask_check_fn,
		perf_read_value_fn_t read_value_fn,
		sync_child_atomic64_set_fn_t atomic_set_fn)
{
	char *event_base = event;
	char *thread_base = thread;
	int counter_id = *(int *)(event_base + counter_id_offset);
	unsigned long bit = perf_event_bit_result(counter_id);

	if (!bit || !mask_check_fn(bit)) {
		return 0;
	}

	if (*(int *)(event_base + use_invariant_tsc_offset)) {
		long long stopped_user =
			*(long long *)(event_base + stopped_user_tsc_offset);
		long long stopped_system =
			*(long long *)(event_base + stopped_system_tsc_offset);

		*(long long *)(event_base + base_user_tsc_offset) =
			stopped_user ? stopped_user :
			*(long long *)(thread_base + thread_user_tsc_offset);
		*(long long *)(event_base + user_accum_count_offset) = 0;
		*(long long *)(event_base + base_system_tsc_offset) =
			stopped_system ? stopped_system :
			*(long long *)(thread_base + thread_system_tsc_offset);
		*(long long *)(event_base + system_accum_count_offset) = 0;
	}
	else {
		if (!read_value_fn || !atomic_set_fn) {
			return -EINVAL;
		}
		read_value_fn(event);
		atomic_set_fn(event_base + count_offset, 0);
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_reset_body_result(void *event, void *thread,
		size_t group_leader_offset, size_t sibling_list_offset,
		size_t group_entry_offset, size_t counter_id_offset,
		size_t use_invariant_tsc_offset,
		size_t base_user_tsc_offset, size_t stopped_user_tsc_offset,
		size_t user_accum_count_offset,
		size_t base_system_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t system_accum_count_offset, size_t count_offset,
		size_t thread_user_tsc_offset,
		size_t thread_system_tsc_offset,
		perf_counter_mask_check_fn_t mask_check_fn,
		perf_read_value_fn_t read_value_fn,
		sync_child_atomic64_set_fn_t atomic_set_fn)
{
	char *event_base = event;
	void *leader;
	char *leader_base;
	struct list_head *head;
	struct list_head *node;
	long rc;

	if (!event || !thread || !mask_check_fn) {
		return -EINVAL;
	}

	leader = *(void **)(event_base + group_leader_offset);
	if (!leader) {
		return -EINVAL;
	}
	leader_base = leader;

	rc = perf_reset_apply_event_body_result(leader, thread,
			counter_id_offset, use_invariant_tsc_offset,
			base_user_tsc_offset, stopped_user_tsc_offset,
			user_accum_count_offset, base_system_tsc_offset,
			stopped_system_tsc_offset, system_accum_count_offset,
			count_offset, thread_user_tsc_offset,
			thread_system_tsc_offset, mask_check_fn, read_value_fn,
			atomic_set_fn);
	if (rc) {
		return rc;
	}

	head = (struct list_head *)(leader_base + sibling_list_offset);
	for (node = head->next; node && node != head; node = node->next) {
		void *sub = (char *)node - group_entry_offset;

		rc = perf_reset_apply_event_body_result(sub, thread,
				counter_id_offset, use_invariant_tsc_offset,
				base_user_tsc_offset, stopped_user_tsc_offset,
				user_accum_count_offset, base_system_tsc_offset,
				stopped_system_tsc_offset,
				system_accum_count_offset, count_offset,
				thread_user_tsc_offset, thread_system_tsc_offset,
				mask_check_fn, read_value_fn, atomic_set_fn);
		if (rc) {
			return rc;
		}
	}

	return 0;
}

static long
perf_stop_apply_event_body_result(void *event, void *thread,
		unsigned long *counter_mask, void **stop_events,
		size_t stop_event_capacity, size_t *stop_event_idx,
		size_t counter_id_offset, size_t state_offset,
		size_t use_invariant_tsc_offset,
		size_t stopped_user_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t thread_user_tsc_offset,
		size_t thread_system_tsc_offset,
		int active_state, int inactive_state,
		perf_counter_mask_check_fn_t mask_check_fn)
{
	char *event_base = event;
	char *thread_base = thread;
	int counter_id = *(int *)(event_base + counter_id_offset);
	unsigned long bit = perf_event_bit_result(counter_id);

	if (!bit || !mask_check_fn(bit) ||
			*(int *)(event_base + state_offset) != active_state) {
		return 0;
	}

	if (*(int *)(event_base + use_invariant_tsc_offset)) {
		long long *stopped_user =
			(long long *)(event_base + stopped_user_tsc_offset);
		long long *stopped_system =
			(long long *)(event_base + stopped_system_tsc_offset);

		if (*stopped_user == 0) {
			*stopped_user =
				*(long long *)(thread_base + thread_user_tsc_offset);
		}
		if (*stopped_system == 0) {
			*stopped_system =
				*(long long *)(thread_base + thread_system_tsc_offset);
		}
	}
	else {
		if (*stop_event_idx >= stop_event_capacity) {
			return -EINVAL;
		}
		*counter_mask |= bit;
		stop_events[(*stop_event_idx)++] = event;
	}

	*(int *)(event_base + state_offset) = inactive_state;
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_stop_body_result(void *event, void *thread,
		size_t group_leader_offset, size_t sibling_list_offset,
		size_t group_entry_offset, size_t counter_id_offset,
		size_t state_offset, size_t use_invariant_tsc_offset,
		size_t stopped_user_tsc_offset,
		size_t stopped_system_tsc_offset,
		size_t thread_user_tsc_offset,
		size_t thread_system_tsc_offset,
		size_t thread_proc_offset,
		size_t proc_monitoring_event_offset,
		size_t proc_perf_status_offset, int active_state,
		int inactive_state, int pp_none, int stop_flags,
		perf_counter_mask_check_fn_t mask_check_fn,
		perf_counter_stop_fn_t counter_stop_fn,
		perf_event_update_fn_t update_fn)
{
	char *event_base = event;
	char *thread_base = thread;
	void *leader;
	char *leader_base;
	struct list_head *head;
	struct list_head *node;
	unsigned long counter_mask = 0;
	void *stop_events[sizeof(unsigned long) * 8 + 1] = { 0 };
	size_t stop_event_idx = 0;
	void *proc;
	long rc;

	if (!event || !thread || !mask_check_fn) {
		return -EINVAL;
	}

	leader = *(void **)(event_base + group_leader_offset);
	if (!leader) {
		return -EINVAL;
	}
	leader_base = leader;

	rc = perf_stop_apply_event_body_result(leader, thread, &counter_mask,
			stop_events, sizeof(stop_events) / sizeof(stop_events[0]),
			&stop_event_idx, counter_id_offset, state_offset,
			use_invariant_tsc_offset, stopped_user_tsc_offset,
			stopped_system_tsc_offset, thread_user_tsc_offset,
			thread_system_tsc_offset, active_state, inactive_state,
			mask_check_fn);
	if (rc) {
		return rc;
	}

	head = (struct list_head *)(leader_base + sibling_list_offset);
	for (node = head->next; node && node != head; node = node->next) {
		void *sub = (char *)node - group_entry_offset;

		rc = perf_stop_apply_event_body_result(sub, thread,
				&counter_mask, stop_events,
				sizeof(stop_events) / sizeof(stop_events[0]),
				&stop_event_idx, counter_id_offset,
				state_offset, use_invariant_tsc_offset,
				stopped_user_tsc_offset,
				stopped_system_tsc_offset,
				thread_user_tsc_offset, thread_system_tsc_offset,
				active_state, inactive_state, mask_check_fn);
		if (rc) {
			return rc;
		}
	}

	if (counter_mask) {
		size_t i;

		if (!counter_stop_fn || !update_fn) {
			return -EINVAL;
		}
		counter_stop_fn(counter_mask, stop_flags);
		for (i = 0; i < stop_event_idx; ++i) {
			if (stop_events[i]) {
				update_fn(stop_events[i]);
			}
		}
	}

	proc = *(void **)(thread_base + thread_proc_offset);
	if (!proc) {
		return -EINVAL;
	}
	*(void **)((char *)proc + proc_monitoring_event_offset) = NULL;
	*(int *)((char *)proc + proc_perf_status_offset) = pp_none;

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_ioctl_body_result(void *event, void *current_proc, void *lock_arg,
		unsigned long cmd, int inherit, unsigned long enable_cmd,
		unsigned long disable_cmd, unsigned long reset_cmd,
		unsigned long refresh_cmd, int pp_reset,
		size_t event_pid_offset,
		size_t proc_monitoring_event_offset,
		size_t proc_perf_status_offset,
		perf_event_void_fn_t start_fn, perf_event_void_fn_t stop_fn,
		perf_event_void_fn_t reset_fn,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn)
{
	char *event_base = event;
	int pid;

	if (!event) {
		return -EINVAL;
	}

	pid = *(int *)(event_base + event_pid_offset);

	if (cmd == enable_cmd) {
		if (pid == 0) {
			char *proc_base = current_proc;

			if (!current_proc || !start_fn) {
				return -EINVAL;
			}
			*(void **)(proc_base + proc_monitoring_event_offset) =
				event;
			start_fn(event);
		}
		else if (pid > 0) {
			void *proc;
			char *proc_base;
			void **monitoring;

			if (!find_fn || !unlock_fn) {
				return -EINVAL;
			}
			proc = find_fn(pid, lock_arg);
			if (!proc) {
				return -EINVAL;
			}
			proc_base = proc;
			monitoring = (void **)(proc_base +
					proc_monitoring_event_offset);
			if (!*monitoring) {
				*monitoring = event;
				*(int *)(proc_base + proc_perf_status_offset) =
					pp_reset;
			}
			unlock_fn(proc, lock_arg);
		}
		return 0;
	}

	if (cmd == disable_cmd) {
		if (pid == 0) {
			if (!stop_fn) {
				return -EINVAL;
			}
			stop_fn(event);
		}
		return 0;
	}

	if (cmd == reset_cmd) {
		if (!reset_fn) {
			return -EINVAL;
		}
		reset_fn(event);
		return 0;
	}

	if (cmd == refresh_cmd) {
		return inherit ? -EINVAL : 0;
	}

	return -1;
}

static unsigned long
perf_event_bit_result(int index)
{
	if (index < 0 || index >= (int)(sizeof(unsigned long) * 8)) {
		return 0;
	}
	return 1UL << index;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_close_body_result(void *event, void *thread,
		size_t counter_id_offset, size_t extra_reg_reg_offset,
		size_t extra_reg_idx_offset, size_t thread_pmc_alloc_map_offset,
		size_t thread_extra_reg_alloc_map_offset,
		syscall_mckfd_free_fn_t free_fn)
{
	char *event_base = event;
	char *thread_base = thread;
	unsigned long *pmc_map;
	unsigned long *extra_map;
	int counter_id;

	if (!event || !thread || !free_fn) {
		return -EINVAL;
	}

	counter_id = *(int *)(event_base + counter_id_offset);
	pmc_map = (unsigned long *)(thread_base + thread_pmc_alloc_map_offset);
	*pmc_map &= ~perf_event_bit_result(counter_id);

	if (*(unsigned int *)(event_base + extra_reg_reg_offset)) {
		int idx = *(int *)(event_base + extra_reg_idx_offset);

		extra_map = (unsigned long *)(thread_base +
				thread_extra_reg_alloc_map_offset);
		*extra_map &= ~perf_event_bit_result(idx);
	}

	free_fn(event);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_fcntl_body_result(void *sfd, void *ctx, int cmd, long arg,
		int fcntl_nr, int set_sig_cmd, int setown_ex_cmd,
		size_t mckfd_sig_no_offset,
		syscall_forward_context_fn_t forward_fn)
{
	char *sfd_base = sfd;

	(void)setown_ex_cmd;

	if (!sfd || !forward_fn) {
		return -EINVAL;
	}

	if (cmd == set_sig_cmd) {
		*(int *)(sfd_base + mckfd_sig_no_offset) = (int)arg;
	}

	return forward_fn(fcntl_nr, ctx);
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_mmap_body_result(unsigned long addr0, size_t len0, int prot,
		int flags, int fd, long off0, int map_anonymous,
		int prot_write, size_t data_head_offset,
		size_t capabilities_offset, unsigned long cap_user_rdpmc_mask,
		perf_do_mmap_fn_t do_mmap_fn)
{
	char *page;
	unsigned long *capabilities;
	long rc;

	if (!do_mmap_fn) {
		return -EINVAL;
	}

	rc = do_mmap_fn(addr0, len0, prot | prot_write,
			flags | map_anonymous, fd, off0, 0, NULL);
	page = (char *)rc;
	*(unsigned long *)(page + data_head_offset) = 16;
	capabilities = (unsigned long *)(page + capabilities_offset);
	*capabilities |= cap_user_rdpmc_mask;

	return rc;
}

SYSCALL_POLICY_HELPER_SCOPE int
perf_event_open_validate_body_result(int cpu, unsigned long flags,
		unsigned long attr_type, unsigned long read_format, int freq,
		unsigned long sample_period, unsigned long raw_type,
		unsigned long hardware_type, unsigned long hw_cache_type,
		unsigned long unsupported_read_format_mask,
		unsigned long sample_period_sign_bit)
{
	int unsupported = (cpu > 0 || flags > 0);

	if (attr_type != raw_type && attr_type != hardware_type &&
			attr_type != hw_cache_type) {
		unsupported = 1;
	}
	if (read_format & unsupported_read_format_mask) {
		unsupported = 1;
	}

	if (freq) {
		unsupported = 1;
	}
	else if (sample_period & sample_period_sign_bit) {
		return -EINVAL;
	}

	return unsupported ? -ENOENT : 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_alloc_init_body_result(void *event, const void *attr,
		size_t event_size, size_t attr_size,
		size_t event_attr_offset, size_t group_entry_offset,
		size_t sibling_list_offset, size_t sample_freq_offset,
		size_t nr_siblings_offset, size_t count_offset,
		size_t child_count_total_offset, size_t parent_offset,
		size_t hw_sample_period_offset, size_t hw_last_period_offset,
		size_t hw_period_left_offset, size_t use_invariant_tsc_offset,
		unsigned long attr_type, unsigned long attr_config,
		int attr_freq, unsigned long attr_sample_freq,
		unsigned long attr_sample_period, unsigned long hardware_type,
		unsigned long ref_cpu_cycles_config,
		sync_child_atomic64_set_fn_t atomic_set_fn)
{
	char *event_base = event;
	struct list_head *group_entry;
	struct list_head *sibling_list;
	unsigned long sample_period;

	if (!event || !attr || !atomic_set_fn) {
		return -EINVAL;
	}

	memset(event, 0, event_size);
	memcpy(event_base + event_attr_offset, attr, attr_size);

	group_entry = (struct list_head *)(event_base + group_entry_offset);
	group_entry->next = group_entry;
	group_entry->prev = group_entry;
	sibling_list = (struct list_head *)(event_base + sibling_list_offset);
	sibling_list->next = sibling_list;
	sibling_list->prev = sibling_list;

	*(unsigned long *)(event_base + sample_freq_offset) = attr_sample_freq;
	*(int *)(event_base + nr_siblings_offset) = 0;
	atomic_set_fn(event_base + count_offset, 0);
	*(unsigned long *)(event_base + child_count_total_offset) = 0;
	*(void **)(event_base + parent_offset) = NULL;

	sample_period = attr_sample_period;
	if (attr_freq && attr_sample_freq) {
		sample_period = 1;
	}
	*(unsigned long *)(event_base + hw_sample_period_offset) = sample_period;
	*(unsigned long *)(event_base + hw_last_period_offset) = sample_period;
	atomic_set_fn(event_base + hw_period_left_offset, sample_period);

	if (attr_type == hardware_type && attr_config == ref_cpu_cycles_config) {
		*(int *)(event_base + use_invariant_tsc_offset) = 1;
		return 1;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_alloc_map_body_result(void **event_out, void *event,
		size_t hw_config_offset, size_t hw_config_ext_offset,
		size_t extra_reg_config_offset, size_t extra_reg_reg_offset,
		size_t extra_reg_idx_offset, unsigned long attr_type,
		unsigned long attr_config, unsigned long hardware_type,
		unsigned long hw_cache_type, unsigned long raw_type,
		perf_event_map_fn_t hw_event_map_fn,
		perf_event_map_fn_t hw_cache_event_map_fn,
		perf_event_map_fn_t hw_cache_extra_reg_map_fn,
		perf_event_map_fn_t raw_event_map_fn,
		perf_event_validate_fn_t validate_event_fn,
		perf_extra_reg_id_fn_t extra_reg_id_fn,
		perf_extra_reg_msr_fn_t extra_reg_msr_fn,
		perf_extra_reg_idx_fn_t extra_reg_idx_fn,
		perf_hw_event_init_fn_t hw_event_init_fn)
{
	char *event_base = event;
	unsigned long val;
	unsigned long extra_config = 0;
	int ereg_id;
	int ret;

	if (!event_out || !event || !validate_event_fn || !extra_reg_id_fn ||
			!extra_reg_msr_fn || !extra_reg_idx_fn ||
			!hw_event_init_fn) {
		return -EINVAL;
	}

	if (attr_type == hardware_type) {
		if (!hw_event_map_fn) {
			return -EINVAL;
		}
		val = hw_event_map_fn(attr_config);
	}
	else if (attr_type == hw_cache_type) {
		if (!hw_cache_event_map_fn || !hw_cache_extra_reg_map_fn) {
			return -EINVAL;
		}
		val = hw_cache_event_map_fn(attr_config);
		extra_config = hw_cache_extra_reg_map_fn(attr_config);
	}
	else if (attr_type == raw_type) {
		if (!raw_event_map_fn) {
			return -EINVAL;
		}
		val = raw_event_map_fn(attr_config);
	}
	else {
		return -EINVAL;
	}

	if (!validate_event_fn(val)) {
		return -ENOENT;
	}

	*(unsigned long *)(event_base + hw_config_offset) = val;
	*(unsigned long *)(event_base + hw_config_ext_offset) = extra_config;

	ereg_id = extra_reg_id_fn(val, extra_config);
	if (ereg_id >= 0) {
		*(unsigned long *)(event_base + extra_reg_config_offset) =
			extra_config;
		*(unsigned int *)(event_base + extra_reg_reg_offset) =
			extra_reg_msr_fn(ereg_id);
		*(int *)(event_base + extra_reg_idx_offset) =
			extra_reg_idx_fn(ereg_id);
	}

	ret = hw_event_init_fn(event);
	if (!ret) {
		*event_out = event;
	}
	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_alloc_body_result(void **event_out, const void *attr,
		size_t event_size, size_t attr_size, unsigned long alloc_flags,
		size_t event_attr_offset, size_t group_entry_offset,
		size_t sibling_list_offset, size_t sample_freq_offset,
		size_t nr_siblings_offset, size_t count_offset,
		size_t child_count_total_offset, size_t parent_offset,
		size_t hw_sample_period_offset, size_t hw_last_period_offset,
		size_t hw_period_left_offset, size_t use_invariant_tsc_offset,
		size_t hw_config_offset, size_t hw_config_ext_offset,
		size_t extra_reg_config_offset, size_t extra_reg_reg_offset,
		size_t extra_reg_idx_offset, unsigned long attr_type,
		unsigned long attr_config, int attr_freq,
		unsigned long attr_sample_freq, unsigned long attr_sample_period,
		unsigned long hardware_type, unsigned long hw_cache_type,
		unsigned long raw_type, unsigned long ref_cpu_cycles_config,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn,
		sync_child_atomic64_set_fn_t atomic_set_fn,
		perf_event_map_fn_t hw_event_map_fn,
		perf_event_map_fn_t hw_cache_event_map_fn,
		perf_event_map_fn_t hw_cache_extra_reg_map_fn,
		perf_event_map_fn_t raw_event_map_fn,
		perf_event_validate_fn_t validate_event_fn,
		perf_extra_reg_id_fn_t extra_reg_id_fn,
		perf_extra_reg_msr_fn_t extra_reg_msr_fn,
		perf_extra_reg_idx_fn_t extra_reg_idx_fn,
		perf_hw_event_init_fn_t hw_event_init_fn)
{
	void *event;
	long ret;

	if (!event_out || !attr || !alloc_fn || !free_fn) {
		return -EINVAL;
	}

	event = alloc_fn(event_size, alloc_flags);
	if (!event) {
		return -ENOMEM;
	}

	ret = perf_event_alloc_init_body_result(event, attr, event_size,
			attr_size, event_attr_offset, group_entry_offset,
			sibling_list_offset, sample_freq_offset,
			nr_siblings_offset, count_offset,
			child_count_total_offset, parent_offset,
			hw_sample_period_offset, hw_last_period_offset,
			hw_period_left_offset, use_invariant_tsc_offset,
			attr_type, attr_config, attr_freq, attr_sample_freq,
			attr_sample_period, hardware_type,
			ref_cpu_cycles_config, atomic_set_fn);
	if (ret < 0) {
		free_fn(event);
		return ret;
	}
	if (ret > 0) {
		*event_out = event;
		return 0;
	}

	ret = perf_event_alloc_map_body_result(event_out, event,
			hw_config_offset, hw_config_ext_offset,
			extra_reg_config_offset, extra_reg_reg_offset,
			extra_reg_idx_offset, attr_type, attr_config,
			hardware_type, hw_cache_type, raw_type,
			hw_event_map_fn, hw_cache_event_map_fn,
			hw_cache_extra_reg_map_fn, raw_event_map_fn,
			validate_event_fn, extra_reg_id_fn, extra_reg_msr_fn,
			extra_reg_idx_fn, hw_event_init_fn);
	if (ret) {
		free_fn(event);
	}
	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_open_group_body_result(void *event, void *proc, int group_fd,
		int counter_idx, size_t proc_mckfd_offset,
		size_t mckfd_next_offset, size_t mckfd_fd_offset,
		size_t mckfd_data_offset, size_t event_group_leader_offset,
		size_t event_sibling_list_offset,
		size_t event_group_entry_offset,
		size_t event_nr_siblings_offset,
		size_t event_pmc_status_offset)
{
	char *event_base = event;
	void *leader;

	if (!event) {
		return -EINVAL;
	}

	if (group_fd == -1) {
		*(void **)(event_base + event_group_leader_offset) = event;
		*(unsigned long *)(event_base + event_pmc_status_offset) = 0;
		leader = event;
	}
	else {
		struct mckfd *cur;
		char *leader_base;
		struct list_head *entry;
		struct list_head *head;

		if (!proc) {
			return -EINVAL;
		}
		leader = NULL;
		for (cur = *(struct mckfd **)((char *)proc + proc_mckfd_offset);
				cur;
				cur = *(struct mckfd **)((char *)cur + mckfd_next_offset)) {
			if (*(int *)((char *)cur + mckfd_fd_offset) == group_fd) {
				leader = (void *)(uintptr_t)
					*(long *)((char *)cur + mckfd_data_offset);
				break;
			}
		}
		if (!leader) {
			return -EINVAL;
		}

		*(void **)(event_base + event_group_leader_offset) = leader;
		leader_base = leader;
		entry = (struct list_head *)(event_base + event_group_entry_offset);
		head = (struct list_head *)(leader_base + event_sibling_list_offset);
		if (!head->prev) {
			return -EINVAL;
		}
		entry->next = head;
		entry->prev = head->prev;
		head->prev->next = entry;
		head->prev = entry;
		(*(int *)(leader_base + event_nr_siblings_offset))++;
	}

	*(unsigned long *)((char *)leader + event_pmc_status_offset) |=
		perf_event_bit_result(counter_idx);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_open_counter_body_result(void *event, void *thread, int pid,
		size_t event_pid_offset, size_t event_counter_id_offset,
		perf_counter_alloc_fn_t counter_alloc_fn)
{
	char *event_base = event;
	int counter_idx;

	if (!event || !thread || !counter_alloc_fn) {
		return -EINVAL;
	}

	*(int *)(event_base + event_pid_offset) = pid;
	counter_idx = counter_alloc_fn(thread, event);
	if (counter_idx < 0) {
		return counter_idx;
	}
	*(int *)(event_base + event_counter_id_offset) = counter_idx;

	return counter_idx;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_open_linux_fd_body_result(struct syscall_request *request,
		void *thread, int counter_idx, int perf_event_open_nr,
		int cpu, size_t thread_pmc_alloc_map_offset,
		perf_open_syscall_fn_t syscall_fn)
{
	char *thread_base = thread;
	unsigned long *pmc_map;
	long fd;

	if (!request || !thread || !syscall_fn) {
		return -EINVAL;
	}

	request->number = perf_event_open_nr;
	request->args[0] = 0;
	fd = syscall_fn(request, cpu);
	if (fd < 0) {
		return fd;
	}

	pmc_map = (unsigned long *)(thread_base + thread_pmc_alloc_map_offset);
	*pmc_map |= perf_event_bit_result(counter_idx);

	return fd;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_open_mckfd_publish_body_result(void *sfd, void *event, void *proc,
		int fd, size_t proc_mckfd_lock_offset,
		size_t proc_mckfd_offset, size_t mckfd_next_offset,
		size_t mckfd_fd_offset, size_t mckfd_sig_no_offset,
		size_t mckfd_data_offset, size_t mckfd_read_cb_offset,
		size_t mckfd_ioctl_cb_offset, size_t mckfd_mmap_cb_offset,
		size_t mckfd_close_cb_offset, size_t mckfd_fcntl_cb_offset,
		syscall_mckfd_long_fn_t read_fn,
		syscall_mckfd_int_fn_t ioctl_fn,
		syscall_mckfd_long_fn_t mmap_fn,
		syscall_mckfd_int_fn_t close_fn,
		syscall_mckfd_int_fn_t fcntl_fn,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn)
{
	char *sfd_base = sfd;
	char *proc_base = proc;
	void *lock;
	long irqstate;
	struct mckfd **headp;

	if (!sfd || !event || !proc || !read_fn || !ioctl_fn || !mmap_fn ||
			!close_fn || !fcntl_fn || !lock_fn || !unlock_fn) {
		return -EINVAL;
	}

	*(int *)(sfd_base + mckfd_fd_offset) = fd;
	*(int *)(sfd_base + mckfd_sig_no_offset) = -1;
	*(long *)(sfd_base + mckfd_data_offset) = (long)event;
	*(syscall_mckfd_long_fn_t *)(sfd_base + mckfd_read_cb_offset) =
		read_fn;
	*(syscall_mckfd_int_fn_t *)(sfd_base + mckfd_ioctl_cb_offset) =
		ioctl_fn;
	*(syscall_mckfd_long_fn_t *)(sfd_base + mckfd_mmap_cb_offset) =
		mmap_fn;
	*(syscall_mckfd_int_fn_t *)(sfd_base + mckfd_close_cb_offset) =
		close_fn;
	*(syscall_mckfd_int_fn_t *)(sfd_base + mckfd_fcntl_cb_offset) =
		fcntl_fn;

	lock = proc_base + proc_mckfd_lock_offset;
	irqstate = lock_fn(lock);
	headp = (struct mckfd **)(proc_base + proc_mckfd_offset);
	*(struct mckfd **)(sfd_base + mckfd_next_offset) = *headp;
	*headp = sfd;
	unlock_fn(lock, irqstate);

	return fd;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_open_body_result(struct syscall_request *request, void *thread,
		void *proc, void *attr, int pid, int group_fd,
		int perf_event_open_nr, int cpu, size_t mckfd_size,
		unsigned long mckfd_alloc_flags, size_t event_pid_offset,
		size_t event_counter_id_offset, size_t proc_mckfd_offset,
		size_t mckfd_next_offset, size_t mckfd_fd_offset,
		size_t mckfd_data_offset, size_t event_group_leader_offset,
		size_t event_sibling_list_offset,
		size_t event_group_entry_offset,
		size_t event_nr_siblings_offset,
		size_t event_pmc_status_offset,
		size_t thread_pmc_alloc_map_offset,
		size_t proc_mckfd_lock_offset, size_t mckfd_sig_no_offset,
		size_t mckfd_read_cb_offset, size_t mckfd_ioctl_cb_offset,
		size_t mckfd_mmap_cb_offset, size_t mckfd_close_cb_offset,
		size_t mckfd_fcntl_cb_offset,
		perf_open_event_alloc_fn_t event_alloc_fn,
		perf_counter_alloc_fn_t counter_alloc_fn,
		perf_open_syscall_fn_t syscall_fn,
		syscall_policy_alloc_fn_t mckfd_alloc_fn,
		syscall_mckfd_long_fn_t read_fn,
		syscall_mckfd_int_fn_t ioctl_fn,
		syscall_mckfd_long_fn_t mmap_fn,
		syscall_mckfd_int_fn_t close_fn,
		syscall_mckfd_int_fn_t fcntl_fn,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn)
{
	void *event = NULL;
	void *sfd;
	long ret;
	int counter_idx;
	long fd;

	if (!request || !thread || !proc || !attr || !event_alloc_fn ||
			!mckfd_alloc_fn) {
		return -EINVAL;
	}

	ret = event_alloc_fn(&event, attr);
	if (ret) {
		return ret;
	}

	ret = perf_event_open_counter_body_result(event, thread, pid,
			event_pid_offset, event_counter_id_offset,
			counter_alloc_fn);
	if (ret < 0) {
		return ret;
	}
	counter_idx = ret;

	ret = perf_event_open_group_body_result(event, proc, group_fd,
			counter_idx, proc_mckfd_offset, mckfd_next_offset,
			mckfd_fd_offset, mckfd_data_offset,
			event_group_leader_offset, event_sibling_list_offset,
			event_group_entry_offset, event_nr_siblings_offset,
			event_pmc_status_offset);
	if (ret) {
		return ret;
	}

	fd = perf_event_open_linux_fd_body_result(request, thread,
			counter_idx, perf_event_open_nr, cpu,
			thread_pmc_alloc_map_offset, syscall_fn);
	if (fd < 0) {
		return fd;
	}

	sfd = mckfd_alloc_fn(mckfd_size, mckfd_alloc_flags);
	if (!sfd) {
		return -ENOMEM;
	}

	return perf_event_open_mckfd_publish_body_result(sfd, event, proc,
			fd, proc_mckfd_lock_offset, proc_mckfd_offset,
			mckfd_next_offset, mckfd_fd_offset,
			mckfd_sig_no_offset, mckfd_data_offset,
			mckfd_read_cb_offset, mckfd_ioctl_cb_offset,
			mckfd_mmap_cb_offset, mckfd_close_cb_offset,
			mckfd_fcntl_cb_offset, read_fn, ioctl_fn, mmap_fn,
			close_fn, fcntl_fn, lock_fn, unlock_fn);
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_open_entry_body_result(struct syscall_request *request,
		void *thread, void *proc, void *attr,
		unsigned long user_attr_addr, size_t attr_size,
		size_t attr_type_offset, size_t attr_read_format_offset,
		size_t attr_sample_period_offset, int pid, int validation_cpu,
		int group_fd, unsigned long flags, int linux_cpu,
		unsigned long raw_type, unsigned long hardware_type,
		unsigned long hw_cache_type,
		unsigned long unsupported_read_format_mask,
		unsigned long sample_period_sign_bit, int perf_event_open_nr,
		size_t mckfd_size, unsigned long mckfd_alloc_flags,
		size_t event_pid_offset, size_t event_counter_id_offset,
		size_t proc_mckfd_offset, size_t mckfd_next_offset,
		size_t mckfd_fd_offset, size_t mckfd_data_offset,
		size_t event_group_leader_offset,
		size_t event_sibling_list_offset,
		size_t event_group_entry_offset,
		size_t event_nr_siblings_offset,
		size_t event_pmc_status_offset,
		size_t thread_pmc_alloc_map_offset,
		size_t proc_mckfd_lock_offset, size_t mckfd_sig_no_offset,
		size_t mckfd_read_cb_offset, size_t mckfd_ioctl_cb_offset,
		size_t mckfd_mmap_cb_offset, size_t mckfd_close_cb_offset,
		size_t mckfd_fcntl_cb_offset,
		syscall_copy_from_user_fn_t copy_from_fn,
		perf_attr_freq_fn_t attr_freq_fn,
		perf_open_event_alloc_fn_t event_alloc_fn,
		perf_counter_alloc_fn_t counter_alloc_fn,
		perf_open_syscall_fn_t syscall_fn,
		syscall_policy_alloc_fn_t mckfd_alloc_fn,
		syscall_mckfd_long_fn_t read_fn,
		syscall_mckfd_int_fn_t ioctl_fn,
		syscall_mckfd_long_fn_t mmap_fn,
		syscall_mckfd_int_fn_t close_fn,
		syscall_mckfd_int_fn_t fcntl_fn,
		syscall_mckfd_lock_fn_t lock_fn,
		syscall_mckfd_unlock_fn_t unlock_fn)
{
	char *attr_base = attr;
	unsigned long attr_type;
	unsigned long read_format;
	unsigned long sample_period;
	int freq;
	int ret;

	if (!attr || !copy_from_fn || !attr_freq_fn) {
		return -EINVAL;
	}
	if (copy_from_fn(attr, user_attr_addr, attr_size)) {
		return -EFAULT;
	}

	attr_type = *(unsigned int *)(attr_base + attr_type_offset);
	read_format = *(unsigned long *)(attr_base + attr_read_format_offset);
	sample_period = *(unsigned long *)(attr_base + attr_sample_period_offset);
	freq = attr_freq_fn(attr);

	ret = perf_event_open_validate_body_result(validation_cpu, flags,
			attr_type, read_format, freq, sample_period, raw_type,
			hardware_type, hw_cache_type,
			unsupported_read_format_mask, sample_period_sign_bit);
	if (ret) {
		return ret;
	}

	return perf_event_open_body_result(request, thread, proc, attr, pid,
			group_fd, perf_event_open_nr, linux_cpu, mckfd_size,
			mckfd_alloc_flags, event_pid_offset,
			event_counter_id_offset, proc_mckfd_offset,
			mckfd_next_offset, mckfd_fd_offset, mckfd_data_offset,
			event_group_leader_offset, event_sibling_list_offset,
			event_group_entry_offset, event_nr_siblings_offset,
			event_pmc_status_offset, thread_pmc_alloc_map_offset,
			proc_mckfd_lock_offset, mckfd_sig_no_offset,
			mckfd_read_cb_offset, mckfd_ioctl_cb_offset,
			mckfd_mmap_cb_offset, mckfd_close_cb_offset,
			mckfd_fcntl_cb_offset, event_alloc_fn,
			counter_alloc_fn, syscall_fn, mckfd_alloc_fn, read_fn,
			ioctl_fn, mmap_fn, close_fn, fcntl_fn, lock_fn,
			unlock_fn);
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
exit_group_status_result(int rc, int sig)
{
	return 0x0000000100000000UL |
		(((unsigned long)rc & 0xff) << 8) |
		((unsigned long)sig & 0xff);
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_thread_active_result(int status)
{
	return status != PS_EXITED && status != PS_ZOMBIE;
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_process_exited_result(int status)
{
	return status == PS_EXITED;
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_thread_is_other_result(const void *thread, const void *current_thread)
{
	return thread != current_thread;
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_report_thread_ptrace_result(int ptrace)
{
	return ptrace != 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_child_cleanup_needed_result(int children_empty,
		int ptraced_children_empty)
{
	return !children_empty || !ptraced_children_empty;
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_release_child_needed_result(int free_child)
{
	return free_child != 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
process_lookup_missing_result(const void *process)
{
	return process == NULL;
}

SYSCALL_POLICY_HELPER_SCOPE int
process_cleanup_tofu_needed_result(int enable_tofu)
{
	return enable_tofu != 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
process_cleanup_fd_path_free_needed_result(const void *path)
{
	return path != NULL;
}

SYSCALL_POLICY_HELPER_SCOPE long
process_cleanup_fd_body_result(int pid, int fd, void *lock_arg,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		process_cleanup_fd_fn_t cleanup_fn,
		process_cleanup_missing_log_fn_t missing_log_fn)
{
	void *proc;

	if (!find_fn || !unlock_fn) {
		return -EINVAL;
	}

	proc = find_fn(pid, lock_arg);
	if (process_lookup_missing_result(proc)) {
		if (missing_log_fn) {
			missing_log_fn(pid);
		}
		return 0;
	}

	if (!cleanup_fn) {
		unlock_fn(proc, lock_arg);
		return -EINVAL;
	}

	cleanup_fn(proc, fd);
	unlock_fn(proc, lock_arg);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
process_cleanup_before_terminate_body_result(int pid, void *lock_arg,
		int enable_tofu, int first_fd, int max_fd,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		process_cleanup_fd_fn_t cleanup_fn)
{
	void *proc;

	if (!find_fn || !unlock_fn) {
		return -EINVAL;
	}

	proc = find_fn(pid, lock_arg);
	if (process_lookup_missing_result(proc)) {
		return 0;
	}

	if (process_cleanup_tofu_needed_result(enable_tofu)) {
		int fd;

		if (!cleanup_fn) {
			unlock_fn(proc, lock_arg);
			return -EINVAL;
		}

		for (fd = first_fd; fd < max_fd; ++fd) {
			cleanup_fn(proc, fd);
		}
	}

	unlock_fn(proc, lock_arg);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_host_detached_thread_release_needed_result(const void *process,
		const void *thread)
{
	return process == NULL && thread != NULL;
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_host_kill_needed_result(int nohost)
{
	return nohost != 1;
}

SYSCALL_POLICY_HELPER_SCOPE long
terminate_host_body_result(int pid, void *detached_thread,
		void *current_thread, void *lock_arg, size_t proc_nohost_offset,
		size_t thread_proc_offset, size_t thread_refcount_offset,
		syscall_find_process_fn_t find_fn,
		syscall_process_unlock_fn_t unlock_fn,
		terminate_host_ref_set_fn_t ref_set_fn,
		wait_thread_side_effect_fn_t release_thread_fn,
		wait_thread_side_effect_fn_t release_process_fn,
		syscall_do_kill_thread_fn_t do_kill_fn)
{
	void *proc;
	char *proc_base;
	char *thread_base;
	int *nohostp;

	if (!find_fn || !unlock_fn) {
		return -EINVAL;
	}

	proc = find_fn(pid, lock_arg);
	if (process_lookup_missing_result(proc)) {
		if (terminate_host_detached_thread_release_needed_result(
					proc, detached_thread)) {
			void *thread_proc;

			if (!ref_set_fn || !release_thread_fn ||
					!release_process_fn) {
				return -EINVAL;
			}
			thread_base = detached_thread;
			thread_proc = *(void **)(thread_base + thread_proc_offset);
			ref_set_fn(thread_base + thread_refcount_offset, 1);
			release_thread_fn(detached_thread);
			release_process_fn(thread_proc);
		}
		return 0;
	}

	proc_base = proc;
	nohostp = (int *)(proc_base + proc_nohost_offset);
	if (!terminate_host_kill_needed_result(*nohostp)) {
		unlock_fn(proc, lock_arg);
		return 0;
	}
	if (!do_kill_fn) {
		unlock_fn(proc, lock_arg);
		return -EINVAL;
	}

	*nohostp = 1;
	unlock_fn(proc, lock_arg);
	return do_kill_fn(current_thread, pid, -1, SIGKILL, NULL, 0);
}

SYSCALL_POLICY_HELPER_SCOPE int
finalize_process_parent_is_pid1_result(const void *parent, const void *pid1)
{
	return parent == pid1;
}

SYSCALL_POLICY_HELPER_SCOPE int
finalize_process_parent_signal_needed_result(int termsig)
{
	return termsig != 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_status_result(int rc, int sig)
{
	return ((rc & 0x00ff) << 8) | (sig & 0xff);
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_report_thread_release_needed_result(int same_process, int termsig)
{
	return same_process && termsig && termsig != SIGCHLD;
}

SYSCALL_POLICY_HELPER_SCOPE int
terminate_child_action_result(int ppid_is_exiting, int parent_is_exiting,
		int child_status)
{
	if (!ppid_is_exiting) {
		return TERMINATE_CHILD_ACTION_NONE;
	}
	if (child_status == PS_ZOMBIE) {
		return TERMINATE_CHILD_ACTION_FREE_ZOMBIE;
	}
	return parent_is_exiting ?
		TERMINATE_CHILD_ACTION_REPARENT_CHILD :
		TERMINATE_CHILD_ACTION_REPARENT_PTRACED;
}

SYSCALL_POLICY_HELPER_SCOPE int
clone_pthread_marker_result(int clone_flags, unsigned long newsp,
		unsigned long parent_tidptr)
{
	return (clone_flags & CLONE_VM) && newsp == parent_tidptr;
}

SYSCALL_POLICY_HELPER_SCOPE int
clone_flags_result(int clone_flags, int coredump_barrier_count)
{
	int termsig = clone_flags & CSIGNAL;

	if (((clone_flags & CLONE_VM) && !(clone_flags & CLONE_THREAD)) ||
			(!(clone_flags & CLONE_VM) &&
			 (clone_flags & CLONE_THREAD))) {
		return -EINVAL;
	}

	if (termsig < 0 || _NSIG < termsig) {
		return -EINVAL;
	}

	if ((clone_flags & CLONE_SIGHAND) && !(clone_flags & CLONE_VM)) {
		return -EINVAL;
	}

	if ((clone_flags & CLONE_THREAD) && !(clone_flags & CLONE_SIGHAND)) {
		return -EINVAL;
	}

	if ((clone_flags & CLONE_FS) && (clone_flags & CLONE_NEWNS)) {
		return -EINVAL;
	}

	if ((clone_flags & CLONE_NEWIPC) && (clone_flags & CLONE_SYSVSEM)) {
		return -EINVAL;
	}

	if ((clone_flags & CLONE_NEWPID) && (clone_flags & CLONE_THREAD)) {
		return -EINVAL;
	}

	if (coredump_barrier_count) {
		return -EINVAL;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
clone_host_parent_flags_result(int clone_flags, int ppid_parent_pid)
{
	if ((clone_flags & CLONE_PARENT) && ppid_parent_pid != 1) {
		return clone_flags;
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
clone_report_thread_result(int clone_flags, int termsig)
{
	return (clone_flags & CLONE_VM) && termsig && termsig != SIGCHLD;
}

SYSCALL_POLICY_HELPER_SCOPE int
clone_parent_tid_store_needed_result(int clone_flags)
{
	return !!(clone_flags & CLONE_PARENT_SETTID);
}

SYSCALL_POLICY_HELPER_SCOPE int
clone_child_cleartid_needed_result(int clone_flags)
{
	return !!(clone_flags & CLONE_CHILD_CLEARTID);
}

SYSCALL_POLICY_HELPER_SCOPE int
clone_child_tid_store_needed_result(int clone_flags)
{
	return !!(clone_flags & CLONE_CHILD_SETTID);
}

SYSCALL_POLICY_HELPER_SCOPE int
clone_tls_source_result(int clone_flags)
{
	return (clone_flags & CLONE_SETTLS) ?
		CLONE_TLS_SOURCE_ARGUMENT : CLONE_TLS_SOURCE_INHERIT;
}

SYSCALL_POLICY_HELPER_SCOPE int
clone_use_last_cpu_result(int mod_clone, int uti_use_last_cpu)
{
	return mod_clone == SPAWN_TO_REMOTE && uti_use_last_cpu;
}

SYSCALL_POLICY_HELPER_SCOPE int
clone_remote_spawn_result(int previous_mod_clone)
{
	return previous_mod_clone == SPAWN_TO_REMOTE;
}

SYSCALL_POLICY_HELPER_SCOPE int
clone_parent_use_pid1_result(int parent_status)
{
	return parent_status == PS_EXITED || parent_status == PS_ZOMBIE;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_exec_event_signal_result(int ptrace)
{
	return (ptrace & (PT_TRACE_EXEC | PTRACE_O_TRACEEXEC)) ?
		(SIGTRAP | (PTRACE_EVENT_EXEC << 8)) : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_syscall_event_signal_result(int ptrace)
{
	return (ptrace & PT_TRACE_SYSCALL) ?
		(SIGTRAP | ((ptrace & PTRACE_O_TRACESYSGOOD) ? 0x80 : 0)) :
		0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_syscall_event_body_result(void *thread, size_t thread_ptrace_offset,
		ptrace_report_signal_fn_t report_signal_fn)
{
	char *thread_base = thread;
	int sig;

	if (!thread) {
		return -EINVAL;
	}
	sig = ptrace_syscall_event_signal_result(
			*(int *)(thread_base + thread_ptrace_offset));
	if (sig) {
		if (!report_signal_fn) {
			return -EINVAL;
		}
		report_signal_fn(thread, sig);
	}
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_report_exec_body_result(void *thread, void *syscall_ctx,
		const struct ptrace_report_exec_offsets *offsets,
		size_t kernel_context_size, size_t user_context_size,
		void *kernel_context_scratch,
		ptrace_void_fn_t preempt_enable_fn,
		ptrace_void_fn_t preempt_disable_fn,
		ptrace_report_signal_fn_t report_signal_fn,
		ptrace_arch_syscall_event_fn_t arch_syscall_event_fn)
{
	char *thread_base = thread;
	char *ctx;
	int sig;

	if (!thread || !syscall_ctx || !offsets || !kernel_context_scratch ||
	    !kernel_context_size || !user_context_size) {
		return -EINVAL;
	}

	ctx = thread_base + offsets->thread_ctx_offset;
	sig = ptrace_exec_event_signal_result(
			*(int *)(thread_base + offsets->thread_ptrace_offset));
	if (sig) {
		if (!preempt_enable_fn || !preempt_disable_fn ||
		    !report_signal_fn) {
			return -EINVAL;
		}
		memcpy(kernel_context_scratch, ctx, kernel_context_size);
		preempt_enable_fn();
		report_signal_fn(thread, sig);
		preempt_disable_fn();
		memcpy(ctx, kernel_context_scratch, kernel_context_size);
	}

	if (*(int *)(thread_base + offsets->thread_ptrace_offset) &
			PT_TRACE_SYSCALL) {
		void **uctxp;
		void *new_uctx;
		void *saved_uctx;

		if (!arch_syscall_event_fn) {
			return -EINVAL;
		}
		memcpy(kernel_context_scratch, ctx, kernel_context_size);
		uctxp = (void **)(thread_base + offsets->thread_uctx_offset);
		new_uctx = *uctxp;
		saved_uctx = thread_base +
			offsets->thread_ptrace_saved_uctx_offset;
		memcpy(saved_uctx, syscall_ctx, user_context_size);
		*(int *)(thread_base +
			offsets->thread_ptrace_saved_uctx_valid_offset) = 1;
		*uctxp = saved_uctx;
		arch_syscall_event_fn(thread, saved_uctx, 0);
		*uctxp = new_uctx;
		memcpy(ctx, kernel_context_scratch, kernel_context_size);
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_clone_event_result(int ptrace, int clone_flags)
{
	int event = 0;

	if (clone_flags & CLONE_VFORK) {
		if (ptrace & PTRACE_O_TRACEVFORK) {
			event = PTRACE_EVENT_VFORK;
		}
		if (ptrace & PTRACE_O_TRACEVFORKDONE) {
			event = PTRACE_EVENT_VFORK_DONE;
		}
	}
	else if ((clone_flags & CSIGNAL) == SIGCHLD) {
		if (ptrace & PTRACE_O_TRACEFORK) {
			event = PTRACE_EVENT_FORK;
		}
	}
	else {
		if (ptrace & PTRACE_O_TRACECLONE) {
			event = PTRACE_EVENT_CLONE;
		}
	}

	return event;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_clone_reparent_result(int event)
{
	return event != PTRACE_EVENT_VFORK_DONE;
}

SYSCALL_POLICY_HELPER_SCOPE int
ptrace_report_clone_body_result(void *thread, void *new_thread, int event,
		void *current_thread,
		const struct ptrace_report_clone_offsets *offsets,
		void *lock_node, void *new_lock_node,
		ptrace_rwlock_fn_t lock_fn,
		ptrace_rwlock_fn_t unlock_fn,
		ptrace_attach_thread_fn_t attach_fn,
		ptrace_do_kill_thread_fn_t do_kill_fn,
		thread_exit_wake_fn_t wake_fn,
		ptrace_control_log_fn_t log_fn)
{
	char *thread_base = thread;
	char *new_base = new_thread;
	char *proc_base;
	char *new_proc_base;
	char *parent_base;
	void *proc;
	void *new_proc;
	void *parent;
	unsigned long update_lock;
	int exit_status;
	int parent_pid;
	int ptrace;
	int new_tid;
	long rc;
	struct siginfo info;

	if (!thread || !new_thread || !offsets || !lock_node ||
	    !new_lock_node || !lock_fn || !unlock_fn || !attach_fn ||
	    !do_kill_fn || !wake_fn) {
		return -EINVAL;
	}

	proc = *(void **)(thread_base + offsets->thread_proc_offset);
	new_proc = *(void **)(new_base + offsets->thread_proc_offset);
	if (!proc || !new_proc) {
		return -EINVAL;
	}
	proc_base = proc;
	new_proc_base = new_proc;
	parent = *(void **)(proc_base + offsets->proc_parent_offset);
	if (!parent) {
		return -EINVAL;
	}
	parent_base = parent;

	if (log_fn) {
		log_fn(PTRACE_REPORT_CLONE_LOG_ENTER, 0, 0);
	}

	update_lock = (unsigned long)proc + offsets->proc_update_lock_offset;
	lock_fn(update_lock, lock_node);
	exit_status = SIGTRAP | (event << 8);
	*(int *)(thread_base + offsets->thread_exit_status_offset) =
		exit_status;
	*(int *)(proc_base + offsets->proc_status_offset) = PS_TRACED;
	*(int *)(thread_base + offsets->thread_status_offset) = PS_TRACED;
	new_tid = *(int *)(new_base + offsets->thread_tid_offset);
	*(unsigned long *)(thread_base +
		offsets->thread_ptrace_eventmsg_offset) = new_tid;
	ptrace = *(int *)(thread_base + offsets->thread_ptrace_offset);
	ptrace &= ~PT_TRACE_SYSCALL;
	*(int *)(thread_base + offsets->thread_ptrace_offset) = ptrace;
	parent_pid = *(int *)(parent_base + offsets->proc_pid_offset);
	unlock_fn(update_lock, lock_node);

	if (ptrace_clone_reparent_result(event)) {
		unsigned long new_update_lock =
			(unsigned long)new_proc +
			offsets->proc_update_lock_offset;

		lock_fn(new_update_lock, new_lock_node);
		*(int *)(new_base + offsets->thread_ptrace_offset) = ptrace;
		attach_fn((unsigned long)new_thread, (unsigned long)parent);
		*(int *)(new_base + offsets->thread_exit_status_offset) =
			SIGSTOP;
		*(int *)(new_proc_base + offsets->proc_status_offset) =
			PS_TRACED;
		*(int *)(new_base + offsets->thread_status_offset) =
			PS_TRACED;
		unlock_fn(new_update_lock, new_lock_node);
	}

	if (log_fn) {
		log_fn(PTRACE_REPORT_CLONE_LOG_KILL_SIGCHLD, parent_pid, 0);
	}

	memset(&info, '\0', sizeof info);
	info.si_signo = SIGCHLD;
	info.si_code = CLD_TRAPPED;
	info._sifields._sigchld.si_pid =
		*(int *)(proc_base + offsets->proc_pid_offset);
	info._sifields._sigchld.si_status = exit_status;
	rc = do_kill_fn(current_thread, parent_pid, -1, SIGCHLD, &info, 0);
	if (rc < 0 && log_fn) {
		log_fn(PTRACE_REPORT_CLONE_LOG_DO_KILL_FAILED, parent_pid,
		       (int)rc);
	}

	wake_fn(parent_base + offsets->proc_waitpid_q_offset);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
execveat_policy_result(int flags, int dirfd, int filename_first)
{
	if ((flags & ~(AT_SYMLINK_NOFOLLOW | AT_EMPTY_PATH)) != 0) {
		return -EINVAL;
	}

	if (filename_first == '/' || dirfd == AT_FDCWD) {
		return 0;
	}

	if (dirfd < 0) {
		return -EBADF;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
execveat_body_result(void *ctx, int dirfd, const char *filename, char **argv,
		char **envp, int flags, int filename_first,
		syscall_execveat_fn_t execveat_fn)
{
	int error = execveat_policy_result(flags, dirfd, filename_first);

	if (error) {
		return error;
	}
	if (!execveat_fn) {
		return -EFAULT;
	}

	return execveat_fn(ctx, dirfd, filename, argv, envp, flags);
}

SYSCALL_POLICY_HELPER_SCOPE long
execve_body_result(void *ctx, const char *filename, char **argv, char **envp,
		syscall_execveat_fn_t execveat_fn)
{
	if (!execveat_fn) {
		return -EFAULT;
	}

	return execveat_fn(ctx, AT_FDCWD, filename, argv, envp, 0);
}

SYSCALL_POLICY_HELPER_SCOPE int
futex_decode_flags_result(int flags, int *opp, int *fsharedp)
{
	*fsharedp = (flags & FUTEX_PRIVATE_FLAG) ? 0 : 1;
	*opp = flags & FUTEX_CMD_MASK;
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
futex_wait_timeout_needed_result(int op, int has_utime)
{
	return has_utime && (op == FUTEX_WAIT || op == FUTEX_WAIT_BITSET);
}

SYSCALL_POLICY_HELPER_SCOPE int
futex_timeout_is_absolute_result(int op)
{
	return op == FUTEX_WAIT_BITSET;
}

SYSCALL_POLICY_HELPER_SCOPE int
futex_clock_id_result(int flags)
{
	return (flags & FUTEX_CLOCK_REALTIME) ? CLOCK_REALTIME :
		CLOCK_MONOTONIC;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned int
futex_requeue_val2_result(int op, unsigned long arg3)
{
	return (op == FUTEX_CMP_REQUEUE || op == FUTEX_WAKE_OP) ?
		(uint32_t)arg3 : 0;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
futex_timeout_ns_result(int op, long timeout_sec, long timeout_nsec,
		long now_sec, long now_nsec)
{
	unsigned long target =
		(unsigned long)(timeout_sec * NS_PER_SEC + timeout_nsec);

	if (op == FUTEX_WAIT_BITSET) {
		unsigned long now =
			(unsigned long)(now_sec * NS_PER_SEC + now_nsec);
		return target - now;
	}

	return target;
}

static void do_futex_log_result(do_futex_log_fn_t log_fn, int event,
		int flags, int op, unsigned long uaddr, uint32_t val,
		unsigned long utime, unsigned long uaddr2, uint32_t val3,
		int fshared, int ret, long sec, long nsec)
{
	struct do_futex_log_record record;

	if (!log_fn)
		return;

	record.event = event;
	record.flags = flags;
	record.op = op;
	record.uaddr = uaddr;
	record.val = val;
	record.utime = utime;
	record.uaddr2 = uaddr2;
	record.val3 = val3;
	record.fshared = fshared;
	record.ret = ret;
	record.sec = sec;
	record.nsec = nsec;
	log_fn(&record);
}

SYSCALL_POLICY_HELPER_SCOPE long
do_futex_body_result(int n, unsigned long arg0, unsigned long arg1,
		unsigned long arg2, unsigned long arg3, unsigned long arg4,
		unsigned long arg5, int has_uti_clv, int local_gettime_support,
		do_futex_syscall_time_fn_t syscall_time_fn,
		do_futex_local_time_fn_t local_time_fn,
		do_futex_linux_time_fn_t linux_time_fn,
		do_futex_ns_per_tsc_fn_t ns_per_tsc_fn,
		do_futex_dispatch_fn_t futex_fn, do_futex_log_fn_t log_fn)
{
	uint64_t timeout = 0;
	uint32_t val2;
	int fshared = 1;
	int ret;
	unsigned long uaddr = arg0;
	int op = (int)arg1;
	uint32_t val = (uint32_t)arg2;
	struct timespec *utime = (struct timespec *)arg3;
	unsigned long uaddr2 = arg4;
	uint32_t val3 = (uint32_t)arg5;
	int flags = op;

	futex_decode_flags_result(op, &op, &fshared);
	do_futex_log_result(log_fn, DO_FUTEX_LOG_ENTER, flags, op, uaddr,
			val, arg3, uaddr2, val3, fshared, 0, 0, 0);

	if (futex_wait_timeout_needed_result(op, utime != NULL)) {
		unsigned long nsec_timeout;

		do_futex_log_result(log_fn, DO_FUTEX_LOG_TIMEOUT, flags,
				op, uaddr, val, arg3, uaddr2, val3, fshared,
				0, utime->tv_sec, utime->tv_nsec);

		if (!has_uti_clv) {
			if (futex_timeout_is_absolute_result(op)) {
				struct timespec ats;

				if (!local_gettime_support ||
						!(flags & FUTEX_CLOCK_REALTIME)) {
					if (!syscall_time_fn ||
							syscall_time_fn(n,
								futex_clock_id_result(flags),
								&ats) < 0)
						return -EFAULT;
				}
				else {
					if (!local_time_fn)
						return -EFAULT;
					local_time_fn(&ats);
				}
				nsec_timeout = futex_timeout_ns_result(op,
						utime->tv_sec, utime->tv_nsec,
						ats.tv_sec, ats.tv_nsec);
			}
			else {
				nsec_timeout = futex_timeout_ns_result(op,
						utime->tv_sec, utime->tv_nsec,
						0, 0);
			}
			if (!ns_per_tsc_fn)
				return -EINVAL;
			{
				unsigned long ns_per_tsc = ns_per_tsc_fn();

				if (!ns_per_tsc)
					return -EINVAL;
				timeout = nsec_timeout * 1000 / ns_per_tsc;
			}
		}
		else {
			if (futex_timeout_is_absolute_result(op)) {
				struct timespec ats;

				if (!linux_time_fn)
					return -EFAULT;
				ret = linux_time_fn(futex_clock_id_result(flags),
						&ats);
				if (ret)
					return ret;
				do_futex_log_result(log_fn,
						DO_FUTEX_LOG_ABSOLUTE_TIME,
						flags, op, uaddr, val, arg3,
						uaddr2, val3, fshared, 0,
						ats.tv_sec, ats.tv_nsec);
				timeout = futex_timeout_ns_result(op,
						utime->tv_sec, utime->tv_nsec,
						ats.tv_sec, ats.tv_nsec);
			}
			else {
				timeout = futex_timeout_ns_result(op,
						utime->tv_sec, utime->tv_nsec,
						0, 0);
			}
		}
	}

	val2 = futex_requeue_val2_result(op, arg3);
	if (!futex_fn)
		return -EINVAL;
	ret = futex_fn(uaddr, op, val, timeout, uaddr2, val2, val3,
			fshared);

	do_futex_log_result(log_fn, DO_FUTEX_LOG_EXIT, flags, op, uaddr,
			val, arg3, uaddr2, val3, fshared, ret, 0, 0);
	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE int
brk_prepare_result(unsigned long address, unsigned long brk_start,
		unsigned long brk_end, unsigned long brk_end_allocated,
		unsigned long *resultp, int *extend_neededp)
{
	if (address < brk_start || address < brk_end) {
		*resultp = brk_end;
		*extend_neededp = 0;
		return 0;
	}

	if (address <= brk_end_allocated) {
		*resultp = address;
		*extend_neededp = 0;
		return 0;
	}

	*resultp = brk_end;
	*extend_neededp = 1;
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
brk_default_vrflags(void)
{
	unsigned long vrflag = VR_PROT_READ | VR_PROT_WRITE;

	vrflag |= VR_PRIVATE;
	vrflag |= VRFLAG_PROT_TO_MAXPROT(vrflag);
	return vrflag;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
brk_body_result(void *vm, void *region, void *range_lock,
		unsigned long address, int cpu, size_t brk_start_offset,
		size_t brk_end_offset, size_t brk_end_allocated_offset,
		brk_flush_fn_t flush_fn, syscall_rwlock_fn_t lock_fn,
		syscall_rwlock_fn_t unlock_fn, brk_extend_fn_t extend_fn,
		brk_log_fn_t log_fn)
{
	char *region_bytes = (char *)region;
	unsigned long *brk_startp =
		(unsigned long *)(region_bytes + brk_start_offset);
	unsigned long *brk_endp =
		(unsigned long *)(region_bytes + brk_end_offset);
	unsigned long *brk_end_allocatedp =
		(unsigned long *)(region_bytes + brk_end_allocated_offset);
	unsigned long r;
	unsigned long vrflag;
	unsigned long old_brk_end_allocated;
	int extend_needed;

	if (!vm || !region || !brk_startp || !brk_endp ||
			!brk_end_allocatedp)
		return 0;

	if (log_fn)
		log_fn(BRK_LOG_ENTER, cpu, *brk_startp, *brk_endp, 0);
	if (flush_fn)
		flush_fn();

	brk_prepare_result(address, *brk_startp, *brk_endp,
			*brk_end_allocatedp, &r, &extend_needed);
	if (!extend_needed) {
		*brk_endp = r;
		return r;
	}

	vrflag = brk_default_vrflags();
	old_brk_end_allocated = *brk_end_allocatedp;
	if (lock_fn)
		lock_fn(range_lock);
	if (extend_fn)
		*brk_end_allocatedp = extend_fn(vm, *brk_end_allocatedp,
				address, vrflag);
	if (unlock_fn)
		unlock_fn(range_lock);

	if (old_brk_end_allocated == *brk_end_allocatedp)
		return old_brk_end_allocated;

	*brk_endp = address;
	r = *brk_endp;
	if (log_fn)
		log_fn(BRK_LOG_SET_END, cpu, *brk_startp, *brk_endp, r);
	return r;
}

SYSCALL_POLICY_HELPER_SCOPE int
mincore_prepare_range(uintptr_t start, size_t len, uintptr_t user_start,
		uintptr_t user_end, uintptr_t *endp)
{
	*endp = start + len;
	if (start & (PAGE_SIZE - 1)) {
		return -EINVAL;
	}
	if ((start < user_start)
			|| (user_end <= start)
			|| ((user_end - start) < len)) {
		return -ENOMEM;
	}
	return 0;
}

static unsigned long
mincore_range_ulong_field(struct vm_range *range, size_t offset)
{
	return *(unsigned long *)((char *)range + offset);
}

static void *
mincore_range_ptr_field(struct vm_range *range, size_t offset)
{
	return *(void **)((char *)range + offset);
}

static off_t
mincore_range_off_field(struct vm_range *range, size_t offset)
{
	return *(off_t *)((char *)range + offset);
}

SYSCALL_POLICY_HELPER_SCOPE long
mincore_body_result(void *vm_arg, void *range_lock, void *pte_lock,
		void *page_table, unsigned long start, size_t len,
		unsigned long vec_addr, unsigned long user_start,
		unsigned long user_end, size_t range_start_offset,
		size_t range_end_offset, size_t range_memobj_offset,
		size_t range_objoff_offset, syscall_rwlock_fn_t range_lock_fn,
		syscall_rwlock_fn_t range_unlock_fn,
		syscall_rwlock_fn_t pte_lock_fn,
		syscall_rwlock_fn_t pte_unlock_fn,
		syscall_lookup_range_fn_t lookup_fn,
		mincore_pte_lookup_fn_t pte_lookup_fn,
		mincore_pte_present_fn_t pte_present_fn,
		mincore_memobj_lookup_fn_t memobj_lookup_fn,
		mincore_copy_byte_fn_t copy_byte_fn, mincore_log_fn_t log_fn)
{
	struct process_vm *vm = vm_arg;
	uintptr_t end;
	unsigned long addr;
	unsigned long up = vec_addr;
	int error;

	error = mincore_prepare_range(start, len, user_start, user_end, &end);
	if (error) {
		if (log_fn)
			log_fn(MINCORE_LOG_INVALID, start, len, vec_addr, error);
		return error;
	}

	for (addr = start; addr < end; addr += PAGE_SIZE, up++) {
		struct vm_range *range;
		void *ptep;
		void *memobj;
		unsigned char value = 0;

		if (range_lock_fn)
			range_lock_fn(range_lock);
		range = lookup_fn ? lookup_fn(vm, addr, addr + 1) : NULL;
		if (!range) {
			if (range_unlock_fn)
				range_unlock_fn(range_lock);
			if (log_fn)
				log_fn(MINCORE_LOG_LOOKUP_FAILED, start, len,
						vec_addr, -ENOMEM);
			return -ENOMEM;
		}

		if (pte_lock_fn)
			pte_lock_fn(pte_lock);
		ptep = pte_lookup_fn ? pte_lookup_fn(page_table, addr) : NULL;
		if (ptep && pte_present_fn && pte_present_fn(ptep)) {
			value = 1;
		}
		else {
			memobj = mincore_range_ptr_field(range, range_memobj_offset);
			if (memobj) {
				unsigned long objoff = mincore_range_off_field(range,
						range_objoff_offset) +
					(addr - mincore_range_ulong_field(range,
						range_start_offset));
				error = memobj_lookup_fn ?
					memobj_lookup_fn(memobj, objoff) : -ENOMEM;
				value = error ? 0 : 1;
			}
		}
		if (pte_unlock_fn)
			pte_unlock_fn(pte_lock);
		if (range_unlock_fn)
			range_unlock_fn(range_lock);

		error = copy_byte_fn ? copy_byte_fn(up, value) : -EFAULT;
		if (error) {
			if (log_fn)
				log_fn(MINCORE_LOG_COPY_FAILED, start, len,
						vec_addr, error);
			return error;
		}
	}

	if (log_fn)
		log_fn(MINCORE_LOG_EXIT, start, len, vec_addr, 0);
	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
mmap_base_vrflags(int prot, int flags, unsigned long vrf0, int anon_on_demand)
{
	unsigned long vrflags = VR_NONE;

	vrflags |= vrf0;
	vrflags |= PROT_TO_VR_FLAG(prot);
	vrflags |= (flags & MAP_PRIVATE) ? VR_PRIVATE : 0;
	vrflags |= (flags & MAP_LOCKED) ? VR_LOCKED : 0;
	vrflags |= VR_DEMAND_PAGING;
	if (flags & MAP_ANONYMOUS && !anon_on_demand) {
		if (flags & MAP_PRIVATE) {
			vrflags &= ~VR_DEMAND_PAGING;
		}
	}
	return vrflags;
}

SYSCALL_POLICY_HELPER_SCOPE int
mmap_populated_mapping_result(int flags)
{
	return (flags & (MAP_POPULATE | MAP_LOCKED)) ? 1 : 0;
}

SYSCALL_POLICY_HELPER_SCOPE int
mmap_should_set_host_ro(int flags, int prot, int anonymous_only)
{
	if (anonymous_only && !(flags & MAP_ANONYMOUS)) {
		return 0;
	}
	return !(prot & PROT_WRITE);
}

SYSCALL_POLICY_HELPER_SCOPE int
mmap_update_private_maxprot(int flags, int maxprot)
{
	if ((flags & MAP_PRIVATE) && (maxprot & PROT_READ)) {
		maxprot |= PROT_WRITE;
	}
	return maxprot;
}

SYSCALL_POLICY_HELPER_SCOPE int
mmap_prot_denied_result(int prot, int maxprot, int *deniedp)
{
	int denied = prot & ~maxprot;

	*deniedp = denied;
	if (!denied) {
		return 0;
	}
	return (denied == PROT_EXEC) ? -EPERM : -EACCES;
}

SYSCALL_POLICY_HELPER_SCOPE unsigned long
mmap_maxprot_to_vrflags(int maxprot)
{
	return VRFLAG_PROT_TO_MAXPROT(PROT_TO_VR_FLAG(maxprot));
}

SYSCALL_POLICY_HELPER_SCOPE int
mmap_should_force_straight(int flags, int straight_map, unsigned long phys,
		size_t len, size_t threshold)
{
	return (flags & MAP_ANONYMOUS) && straight_map &&
		!(flags & MAP_FIXED) && phys && (len >= threshold);
}

SYSCALL_POLICY_HELPER_SCOPE int
mmap_is_shared(int flags)
{
	return (flags & MAP_SHARED) ? 1 : 0;
}
#endif

#undef SYSCALL_POLICY_HELPER_SCOPE

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_tgkill(int n, ihk_mc_user_context_t *ctx);
#else
long sys_tgkill(int n, ihk_mc_user_context_t *ctx)
{
	int tgid = ihk_mc_syscall_arg0(ctx);
	int tid = ihk_mc_syscall_arg1(ctx);
	int sig = ihk_mc_syscall_arg2(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return syscall_tgkill_body_result(thread,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, pid), tgid, tid, sig,
			syscall_do_kill_thread_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_tkill(int n, ihk_mc_user_context_t *ctx);
#else
long sys_tkill(int n, ihk_mc_user_context_t *ctx)
{
	int tid = ihk_mc_syscall_arg0(ctx);
	int sig = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return syscall_tkill_body_result(thread,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, pid), tid, sig,
			syscall_do_kill_thread_bridge);
}
#endif

int *
getcred(int *_buf)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	return getcred_body_result(_buf, PAGE_MASK, __NR_setfsuid,
			syscall_virt_to_phys_bridge,
			syscall_get_processor_id_bridge,
			syscall_do_syscall_request_bridge);
#else
	int	*buf;
	struct syscall_request request IHK_DMA_ALIGN;
	unsigned long phys;

	if ((((unsigned long)_buf) ^ ((unsigned long)(_buf + 8))) & PAGE_MASK)
		buf = _buf + 8;
	else
		buf = _buf;
	phys = virt_to_phys(buf);
	request.number = __NR_setfsuid;
	request.args[0] = phys;
	request.args[1] = 1;
	do_syscall(&request, ihk_mc_get_processor_id());

	return buf;
#endif
}

void
do_setresuid()
{
	int	_buf[16];
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct thread *thread = get_this_cpu_local_var()->current;

	(void)syscall_refresh_cred_fields_body_result(thread, _buf,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, ruid),
			__builtin_offsetof(struct process, euid),
			__builtin_offsetof(struct process, suid),
			__builtin_offsetof(struct process, fsuid),
			0, 1, 2, 3, getcred);
#else
	int	*buf;
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process *proc = thread->proc;

	buf = getcred(_buf);

	proc->ruid = buf[0];
	proc->euid = buf[1];
	proc->suid = buf[2];
	proc->fsuid = buf[3];
#endif
}

void
do_setresgid()
{
	int	_buf[16];
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct thread *thread = get_this_cpu_local_var()->current;

	(void)syscall_refresh_cred_fields_body_result(thread, _buf,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, rgid),
			__builtin_offsetof(struct process, egid),
			__builtin_offsetof(struct process, sgid),
			__builtin_offsetof(struct process, fsgid),
			4, 5, 6, 7, getcred);
#else
	int	*buf;
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process *proc = thread->proc;

	buf = getcred(_buf);

	proc->rgid = buf[4];
	proc->egid = buf[5];
	proc->sgid = buf[6];
	proc->fsgid = buf[7];
#endif
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_setresuid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_setresuid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_forward_refresh_cred_body_result(__NR_setresuid, ctx,
			syscall_forward_context_bridge, do_setresuid);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_setreuid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_setreuid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_forward_refresh_cred_body_result(__NR_setreuid, ctx,
			syscall_forward_context_bridge, do_setresuid);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_setuid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_setuid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_forward_refresh_cred_body_result(__NR_setuid, ctx,
			syscall_forward_context_bridge, do_setresuid);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_setfsuid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_setfsuid(int n, ihk_mc_user_context_t *ctx)
{
	int fsuid = (int)ihk_mc_syscall_arg0(ctx);;

	return syscall_setfsid_body_result(fsuid, __NR_setfsuid,
			syscall_do_syscall2_bridge, do_setresuid);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_setresgid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_setresgid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_forward_refresh_cred_body_result(__NR_setresgid, ctx,
			syscall_forward_context_bridge, do_setresgid);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_setregid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_setregid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_forward_refresh_cred_body_result(__NR_setregid, ctx,
			syscall_forward_context_bridge, do_setresgid);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_setgid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_setgid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_forward_refresh_cred_body_result(__NR_setgid, ctx,
			syscall_forward_context_bridge, do_setresgid);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_setfsgid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_setfsgid(int n, ihk_mc_user_context_t *ctx)
{
	int fsgid = (int)ihk_mc_syscall_arg0(ctx);;

	return syscall_setfsid_body_result(fsgid, __NR_setfsgid,
			syscall_do_syscall2_bridge, do_setresgid);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_getuid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_getuid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_get_process_id_field_result(get_this_cpu_local_var()->current,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, ruid));
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_geteuid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_geteuid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_get_process_id_field_result(get_this_cpu_local_var()->current,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, euid));
}
#endif

long
syscall_copy_int_to_user_bridge(unsigned long dst_addr, const int *src)
{
	return copy_to_user((void *)dst_addr, src, sizeof(*src));
}

long
syscall_copy_from_user_bridge(void *dst, unsigned long src_addr, size_t bytes)
{
	return copy_from_user(dst, (const void *)src_addr, bytes);
}

long
syscall_copy_to_user_bridge(unsigned long dst_addr, const void *src,
		size_t bytes)
{
	return copy_to_user((void *)dst_addr, src, bytes);
}

void *
syscall_find_process_bridge(int pid, void *lock_arg)
{
	return find_process(pid, (struct mcs_rwlock_node_irqsave *)lock_arg);
}

void
syscall_process_unlock_bridge(void *proc, void *lock_arg)
{
	process_unlock(proc, (struct mcs_rwlock_node_irqsave *)lock_arg);
}

long
syscall_forward_rt_sigprocmask_bridge(unsigned long sigmask)
{
	ihk_mc_user_context_t ctx0;

	ihk_mc_syscall_set_arg0(&ctx0, sigmask);
	return syscall_generic_forwarding(__NR_rt_sigprocmask, &ctx0);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_getresuid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_getresuid(int n, ihk_mc_user_context_t *ctx)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	int *ruid = (int *)ihk_mc_syscall_arg0(ctx);
	int *euid = (int *)ihk_mc_syscall_arg1(ctx);
	int *suid = (int *)ihk_mc_syscall_arg2(ctx);

	return syscall_getresid_body_result(thread,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, ruid),
			__builtin_offsetof(struct process, euid),
			__builtin_offsetof(struct process, suid),
			(unsigned long)ruid, (unsigned long)euid,
			(unsigned long)suid, syscall_copy_int_to_user_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_getgid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_getgid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_get_process_id_field_result(get_this_cpu_local_var()->current,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, rgid));
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_getegid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_getegid(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_get_process_id_field_result(get_this_cpu_local_var()->current,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, egid));
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_getresgid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_getresgid(int n, ihk_mc_user_context_t *ctx)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	int *rgid = (int *)ihk_mc_syscall_arg0(ctx);
	int *egid = (int *)ihk_mc_syscall_arg1(ctx);
	int *sgid = (int *)ihk_mc_syscall_arg2(ctx);

	return syscall_getresid_body_result(thread,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, rgid),
			__builtin_offsetof(struct process, egid),
			__builtin_offsetof(struct process, sgid),
			(unsigned long)rgid, (unsigned long)egid,
			(unsigned long)sgid, syscall_copy_int_to_user_bridge);
}
#endif

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
static const struct syscall_setpgid_offsets syscall_setpgid_offsets = {
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.proc_pgid_offset = __builtin_offsetof(struct process, pgid),
	.proc_execed_offset = __builtin_offsetof(struct process, execed),
};
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_setpgid(int n, ihk_mc_user_context_t *ctx);
#else
long sys_setpgid(int n, ihk_mc_user_context_t *ctx)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	int pgid = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct mcs_rwlock_node_irqsave lock;

	return syscall_setpgid_body_result(thread, pid, pgid, __NR_setpgid,
			ctx, &syscall_setpgid_offsets, &lock,
			syscall_find_process_bridge, syscall_process_unlock_bridge,
			syscall_forward_context_bridge);
}
#endif

/* Ignore the registration by start_thread() (in pthread_create.c)
   because McKernel doesn't unlock mutex-es held by the thread which has been killed. */
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_set_robust_list(int n, ihk_mc_user_context_t *ctx);
#else
long sys_set_robust_list(int n, ihk_mc_user_context_t *ctx)
{
	size_t len = (size_t)ihk_mc_syscall_arg1(ctx);

	return set_robust_list_body_result(len);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
static void
syscall_sigcommon_writer_lock_bridge(void *lock, void *node)
{
	mcs_rwlock_writer_lock(lock, node);
}

static void
syscall_sigcommon_writer_unlock_bridge(void *lock, void *node)
{
	mcs_rwlock_writer_unlock(lock, node);
}

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
#endif

int
do_sigaction(int sig, struct k_sigaction *act, struct k_sigaction *oact)
{
	struct thread *thread = get_this_cpu_local_var()->current;
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct mcs_rwlock_node_irqsave mcs_rw_node;

	return do_sigaction_body_result(sig, act, oact, thread->sigcommon,
			__builtin_offsetof(struct sig_common, action),
			sizeof(struct k_sigaction),
			__builtin_offsetof(struct sig_common, lock),
			&mcs_rw_node, syscall_sigcommon_writer_lock_bridge,
			syscall_sigcommon_writer_unlock_bridge,
			syscall_forward_sigaction_update_bridge);
#else
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
#endif
}

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
static const struct syscall_mckfd_offsets syscall_mckfd_offsets = {
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.proc_mckfd_lock_offset = __builtin_offsetof(struct process, mckfd_lock),
	.proc_mckfd_offset = __builtin_offsetof(struct process, mckfd),
	.mckfd_next_offset = __builtin_offsetof(struct mckfd, next),
	.mckfd_fd_offset = __builtin_offsetof(struct mckfd, fd),
	.mckfd_read_cb_offset = __builtin_offsetof(struct mckfd, read_cb),
	.mckfd_ioctl_cb_offset = __builtin_offsetof(struct mckfd, ioctl_cb),
	.mckfd_close_cb_offset = __builtin_offsetof(struct mckfd, close_cb),
	.mckfd_fcntl_cb_offset = __builtin_offsetof(struct mckfd, fcntl_cb),
};
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_read(int n, ihk_mc_user_context_t *ctx);
#else
long sys_read(int n, ihk_mc_user_context_t *ctx)
{
	int fd = ihk_mc_syscall_arg0(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return syscall_read_body_result(thread, fd, __NR_read, ctx,
			&syscall_mckfd_offsets, syscall_mckfd_lock_bridge,
			syscall_mckfd_unlock_bridge,
			syscall_forward_context_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_ioctl(int n, ihk_mc_user_context_t *ctx);
#else
long sys_ioctl(int n, ihk_mc_user_context_t *ctx)
{
	int fd = ihk_mc_syscall_arg0(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return syscall_ioctl_body_result(thread, fd, ihk_mc_syscall_arg1(ctx),
			ihk_mc_syscall_arg2(ctx), __NR_ioctl, ctx,
			&syscall_mckfd_offsets, syscall_mckfd_lock_bridge,
			syscall_mckfd_unlock_bridge,
			syscall_forward_context_bridge,
			syscall_tofu_ioctl_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long
#else
static long
#endif
syscall_strlen_user_bridge(const void *path)
{
	return strlen_user(path);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long
#else
static long
#endif
syscall_xpmem_open_bridge(const char *pathname, int flags, void *ctx)
{
	return xpmem_open(pathname, flags, (ihk_mc_user_context_t *)ctx);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long
#else
static long
#endif
syscall_xpmem_openat_bridge(const char *pathname, int flags, void *ctx)
{
	return xpmem_openat(pathname, flags, (ihk_mc_user_context_t *)ctx);
}

#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && !defined(ENABLE_TOFU)
long sys_open(int n, ihk_mc_user_context_t *ctx);
#else
long sys_open(int n, ihk_mc_user_context_t *ctx)
{
#ifndef ENABLE_TOFU
	const char *_pathname = (const char *)ihk_mc_syscall_arg0(ctx);
	int flags = (int)ihk_mc_syscall_arg1(ctx);

	return open_common_body_result((unsigned long)_pathname, flags,
			__NR_open, ctx, XPMEM_DEV_PATH, IHK_MC_AP_NOWAIT,
			syscall_strlen_user_bridge, syscall_copy_from_user_bridge,
			syscall_alloc_bridge, syscall_mckfd_free_bridge,
			syscall_xpmem_open_bridge, syscall_forward_context_bridge);
#else
	const char *_pathname = (const char *)ihk_mc_syscall_arg0(ctx);
	int flags = (int)ihk_mc_syscall_arg1(ctx);
	int len;
	char *pathname;
	long rc;

	len = strlen_user(_pathname);
	if (len < 0)
		return len;
	len++;

	pathname = kmalloc_tracked(len, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (!pathname) {
		dkprintf("%s: error allocating pathname\n", __func__);
		return -ENOMEM;
	}
	if (copy_from_user(pathname, _pathname, len)) {
		dkprintf("%s: error: copy_from_user pathname\n", __func__);
		rc = -EFAULT;
		goto out;
	}

#ifdef ENABLE_TOFU
	get_this_cpu_local_var()->current->fd_path_in_open = pathname;
#endif

	dkprintf("open(): pathname=%s\n", pathname);
	if (!strncmp(pathname, XPMEM_DEV_PATH, len)) {
		rc = xpmem_open(pathname, flags, ctx);
	} else {
		rc = syscall_generic_forwarding(__NR_open, ctx);
	}

#ifdef ENABLE_TOFU
	get_this_cpu_local_var()->current->fd_path_in_open = NULL;
#endif

 out:
#ifdef ENABLE_TOFU
	if (rc > 0 && rc < MAX_FD_PDE) {
		get_this_cpu_local_var()->current->proc->fd_path[rc] = pathname;
	}
	else {
		kfree_tracked(pathname, __FILE__, __LINE__);
	}
#else
	kfree_tracked(pathname, __FILE__, __LINE__);
#endif
	return rc;
#endif
}
#endif

#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && !defined(ENABLE_TOFU)
long sys_openat(int n, ihk_mc_user_context_t *ctx);
#else
long sys_openat(int n, ihk_mc_user_context_t *ctx)
{
#ifndef ENABLE_TOFU
	const char *_pathname = (const char *)ihk_mc_syscall_arg1(ctx);
	int flags = (int)ihk_mc_syscall_arg2(ctx);

	return open_common_body_result((unsigned long)_pathname, flags,
			__NR_openat, ctx, XPMEM_DEV_PATH, IHK_MC_AP_NOWAIT,
			syscall_strlen_user_bridge, syscall_copy_from_user_bridge,
			syscall_alloc_bridge, syscall_mckfd_free_bridge,
			syscall_xpmem_openat_bridge, syscall_forward_context_bridge);
#else
	const char *_pathname = (const char *)ihk_mc_syscall_arg1(ctx);
	int flags = (int)ihk_mc_syscall_arg2(ctx);
	char *pathname;
	int len;
	long rc;

	len = strlen_user(_pathname);
	if (len < 0)
		return len;
	len++;

	pathname = kmalloc_tracked(len, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (!pathname) {
		dkprintf("%s: error allocating pathname\n", __func__);
		return -ENOMEM;
	}
	if (copy_from_user(pathname, _pathname, len)) {
		dkprintf("%s: error: copy_from_user pathname\n", __func__);
		rc = -EFAULT;
		goto out;
	}

#ifdef ENABLE_TOFU
	get_this_cpu_local_var()->current->fd_path_in_open = pathname;
#endif

	dkprintf("openat(): pathname=%s\n", pathname);
	if (!strncmp(pathname, XPMEM_DEV_PATH, len)) {
		rc = xpmem_openat(pathname, flags, ctx);
	} else {
		rc = syscall_generic_forwarding(__NR_openat, ctx);
	}

#ifdef ENABLE_TOFU
	get_this_cpu_local_var()->current->fd_path_in_open = NULL;
#endif

out:
#ifdef ENABLE_TOFU
	if (rc > 0 && rc < MAX_FD_PDE) {
		get_this_cpu_local_var()->current->proc->fd_path[rc] = pathname;
	}
	else {
		kfree_tracked(pathname, __FILE__, __LINE__);
	}
#else
	kfree_tracked(pathname, __FILE__, __LINE__);
#endif
	return rc;
#endif
}
#endif

long sys_execveat(int n, ihk_mc_user_context_t *ctx)
{
	int dirfd = (int)ihk_mc_syscall_arg0(ctx);
	const char *filename = (const char *)ihk_mc_syscall_arg1(ctx);
	int flags = (int)ihk_mc_syscall_arg4(ctx);

	return execveat_body_result(ctx, dirfd, filename,
			(char **)ihk_mc_syscall_arg2(ctx),
			(char **)ihk_mc_syscall_arg3(ctx), flags,
			filename[0], syscall_execveat_bridge);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_close(int n, ihk_mc_user_context_t *ctx);
#else
long sys_close(int n, ihk_mc_user_context_t *ctx)
{
	int fd = ihk_mc_syscall_arg0(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return syscall_close_body_result(thread, fd, __NR_close, ctx,
			&syscall_mckfd_offsets, syscall_mckfd_lock_bridge,
			syscall_mckfd_unlock_bridge,
			syscall_forward_context_bridge,
			syscall_tofu_close_bridge, syscall_mckfd_free_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_fcntl(int n, ihk_mc_user_context_t *ctx);
#else
long sys_fcntl(int n, ihk_mc_user_context_t *ctx)
{
	int fd = ihk_mc_syscall_arg0(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return syscall_fcntl_body_result(thread, fd, __NR_fcntl, ctx,
			&syscall_mckfd_offsets, syscall_mckfd_lock_bridge,
			syscall_mckfd_unlock_bridge,
			syscall_forward_context_bridge);
}
#endif

static long
syscall_forward_context_bridge(int syscall_nr, void *ctx)
{
	return syscall_generic_forwarding(syscall_nr,
			(ihk_mc_user_context_t *)ctx);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long
syscall_policy_forward_context_bridge(int syscall_nr, void *ctx)
{
	return syscall_forward_context_bridge(syscall_nr, ctx);
}
#endif

long
syscall_mckfd_lock_bridge(void *lock)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock);
}

void
syscall_mckfd_unlock_bridge(void *lock, long irqstate)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock, irqstate);
}

void *
syscall_alloc_bridge(size_t size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

void
syscall_mckfd_free_bridge(void *fdp)
{
	kfree_tracked(fdp, __FILE__, __LINE__);
}

long
syscall_tofu_ioctl_bridge(void *threadp, int fd, unsigned long cmd,
		unsigned long arg, int *handled)
{
#ifdef ENABLE_TOFU
	struct thread *thread = threadp;
	extern long tof_utofu_unlocked_ioctl(int fd,
			unsigned int cmd, unsigned long arg);
	long rc;

	if (handled) {
		*handled = 0;
	}
	if (thread && thread->proc->enable_tofu &&
			fd < MAX_FD_PDE && thread->proc->fd_pde_data[fd]) {
		rc = tof_utofu_unlocked_ioctl(fd, cmd, arg);
		if (rc != -ENOTSUPP) {
			if (handled) {
				*handled = 1;
			}
			return rc;
		}
	}
#else
	(void)threadp;
	(void)fd;
	(void)cmd;
	(void)arg;
	if (handled) {
		*handled = 0;
	}
#endif
	return 0;
}

void
syscall_tofu_close_bridge(void *threadp, int fd)
{
#ifdef ENABLE_TOFU
	struct thread *thread = threadp;

	if (thread->proc->enable_tofu && fd >= 0 && fd < MAX_FD_PDE) {
		if (thread->proc->fd_pde_data[fd]) {
			extern void tof_utofu_release_fd(struct process *proc, int fd);

			dkprintf("%s: -> tof_utofu_release_fd() @ fd: %d (%s)\n",
					__func__, fd, thread->proc->fd_path[fd]);
			tof_utofu_release_fd(thread->proc, fd);
			thread->proc->fd_pde_data[fd] = NULL;
		}

		if (thread->proc->fd_path[fd]) {
			dkprintf("%s: %d -> %s\n", __func__, fd, thread->proc->fd_path[fd]);
			kfree_tracked(thread->proc->fd_path[fd], __FILE__, __LINE__);
			thread->proc->fd_path[fd] = NULL;
		}
	}
#else
	(void)threadp;
	(void)fd;
#endif
}

unsigned long
syscall_pending_mask_bridge(void *threadp)
{
	struct thread *thread = threadp;
	struct sig_pending *pending;
	struct list_head *head;
	mcs_rwlock_lock_t *lock;
	struct mcs_rwlock_node_irqsave mcs_rw_node;
	unsigned long mask = 0;

	lock = &thread->sigcommon->lock;
	head = &thread->sigcommon->sigpending;
	mcs_rwlock_writer_lock(lock, &mcs_rw_node);
	for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))) {
		mask |= pending->sigmask.__val[0];
	}
	mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

	lock = &thread->sigpendinglock;
	head = &thread->sigpending;
	mcs_rwlock_writer_lock(lock, &mcs_rw_node);
	for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))) {
		mask |= pending->sigmask.__val[0];
	}
	mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

	return mask;
}

long
syscall_signalfd_create_bridge(int syscall_nr, int flags)
{
	struct syscall_request request IHK_DMA_ALIGN;

	memset(&request, 0, sizeof(request));
	request.number = syscall_nr;
	request.args[0] = 0;
	request.args[1] = flags;
	return do_syscall(&request, ihk_mc_get_processor_id());
}

long
syscall_signalfd_publish_bridge(void *threadp, int fd,
		const unsigned long *maskp, int create)
{
	struct thread *thread = threadp;
	struct process *proc = thread->proc;
	struct mckfd *sfd;
	long irqstate;

	if (create) {
		sfd = kmalloc_tracked(sizeof(struct mckfd), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		if (!sfd)
			return -ENOMEM;
		memset(sfd, '\0', sizeof(struct mckfd));
		sfd->fd = fd;
		irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
		sfd->next = proc->mckfd;
		proc->mckfd = sfd;
	} else {
		irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
		for (sfd = proc->mckfd; sfd; sfd = sfd->next) {
			if (sfd->fd == fd)
				break;
		}
		if (!sfd) {
			ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);
			return -EINVAL;
		}
	}

	memcpy(&sfd->data, maskp, sizeof(*maskp));
	ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);
	return sfd->fd;
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_epoll_pwait(int n, ihk_mc_user_context_t *ctx);
#else
long sys_epoll_pwait(int n, ihk_mc_user_context_t *ctx)
{
	sigset_t *set = (sigset_t *)ihk_mc_syscall_arg4(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return syscall_temp_sigmask_body_result((unsigned long)set,
			thread, __builtin_offsetof(struct thread, sigmask),
			__NR_epoll_pwait, ctx, syscall_copy_from_user_bridge,
			syscall_forward_context_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_ppoll(int n, ihk_mc_user_context_t *ctx);
#else
long sys_ppoll(int n, ihk_mc_user_context_t *ctx)
{
	sigset_t *set = (sigset_t *)ihk_mc_syscall_arg3(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return syscall_temp_sigmask_body_result((unsigned long)set,
			thread, __builtin_offsetof(struct thread, sigmask),
			__NR_ppoll, ctx, syscall_copy_from_user_bridge,
			syscall_forward_context_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_pselect6(int n, ihk_mc_user_context_t *ctx);
#else
long sys_pselect6(int n, ihk_mc_user_context_t *ctx)
{
	sigset_t **_set = (sigset_t **)ihk_mc_syscall_arg5(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return pselect6_sigmask_body_result((unsigned long)_set,
			thread, __builtin_offsetof(struct thread, sigmask),
			__NR_pselect6, ctx, syscall_copy_from_user_bridge,
			syscall_forward_context_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_rt_sigprocmask(int n, ihk_mc_user_context_t *ctx);
#else
long sys_rt_sigprocmask(int n, ihk_mc_user_context_t *ctx)
{
	int how = ihk_mc_syscall_arg0(ctx);
	const sigset_t *set = (const sigset_t *)ihk_mc_syscall_arg1(ctx);
	sigset_t *oldset = (sigset_t *)ihk_mc_syscall_arg2(ctx);
	size_t sigsetsize = (size_t)ihk_mc_syscall_arg3(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return rt_sigprocmask_body_result(how, (unsigned long)set,
			(unsigned long)oldset, sigsetsize, sizeof(sigset_t),
			thread, __builtin_offsetof(struct thread, sigmask),
			syscall_copy_from_user_bridge,
			syscall_copy_to_user_bridge,
			syscall_forward_rt_sigprocmask_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_rt_sigpending(int n, ihk_mc_user_context_t *ctx);
#else
long sys_rt_sigpending(int n, ihk_mc_user_context_t *ctx)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	sigset_t *set = (sigset_t *)ihk_mc_syscall_arg0(ctx);
	size_t sigsetsize = (size_t)ihk_mc_syscall_arg1(ctx);

	return rt_sigpending_body_result((unsigned long)set, sigsetsize,
			sizeof(sigset_t), thread, syscall_pending_mask_bridge,
			syscall_copy_to_user_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_signalfd(int n, ihk_mc_user_context_t *ctx);
#else
long sys_signalfd(int n, ihk_mc_user_context_t *ctx)
{
	return signalfd_body_result();
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_signalfd4(int n, ihk_mc_user_context_t *ctx);
#else
long sys_signalfd4(int n, ihk_mc_user_context_t *ctx)
{
	int fd = ihk_mc_syscall_arg0(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	sigset_t *maskp = (sigset_t *)ihk_mc_syscall_arg1(ctx);;
	size_t sigsetsize = (size_t)ihk_mc_syscall_arg2(ctx);
	int flags = ihk_mc_syscall_arg3(ctx);

	return signalfd4_body_result(fd, (unsigned long)maskp, sigsetsize,
			sizeof(sigset_t), flags, thread, __NR_signalfd4,
			syscall_copy_from_user_bridge,
			syscall_signalfd_create_bridge,
			syscall_signalfd_publish_bridge);
}
#endif

#ifdef ENABLE_PERF
static int
perf_counter_extra_set_bridge(void *event)
{
	return ihk_mc_perfctr_set_extra((struct mc_perf_event *)event);
}

static int
perf_counter_init_raw_bridge(int counter_id, unsigned long hw_config, int mode)
{
	return ihk_mc_perfctr_init_raw(counter_id, hw_config, mode);
}

static int
perf_counter_attr_flags_bridge(const void *attr, int *exclude_kernel,
			       int *exclude_user)
{
	const struct perf_event_attr *perf_attr = attr;

	if (!perf_attr || !exclude_kernel || !exclude_user) {
		return -EINVAL;
	}

	*exclude_kernel = perf_attr->exclude_kernel;
	*exclude_user = perf_attr->exclude_user;
	return 0;
}

int perf_counter_set(struct mc_perf_event *event)
{
	return perf_counter_set_entry_body_result(event,
			__builtin_offsetof(struct mc_perf_event, attr),
			__builtin_offsetof(struct mc_perf_event, counter_id),
			__builtin_offsetof(struct mc_perf_event, hw_config),
			__builtin_offsetof(struct mc_perf_event, extra_reg.reg),
			PERFCTR_KERNEL_MODE, PERFCTR_USER_MODE,
			perf_counter_attr_flags_bridge,
			perf_counter_extra_set_bridge,
			perf_counter_init_raw_bridge);
}

static unsigned long
perf_event_update_bridge(void *event)
{
	return ihk_mc_event_update((struct mc_perf_event *)event);
}

static long
perf_event_atomic64_read_bridge(void *value)
{
	return ihk_atomic64_read((ihk_atomic64_t *)value);
}

static int
perf_read_attr_flags_bridge(const void *attr, int *exclude_user,
			    int *exclude_kernel, int *inherit)
{
	const struct perf_event_attr *perf_attr = attr;

	if (!perf_attr || !exclude_user || !exclude_kernel || !inherit) {
		return -EINVAL;
	}

	*exclude_user = perf_attr->exclude_user;
	*exclude_kernel = perf_attr->exclude_kernel;
	*inherit = perf_attr->inherit;
	return 0;
}

unsigned long perf_event_read_value(struct mc_perf_event *event)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	return perf_event_read_value_entry_body_result(event, thread,
			__builtin_offsetof(struct mc_perf_event, attr),
			__builtin_offsetof(struct mc_perf_event, pid),
			__builtin_offsetof(struct mc_perf_event,
					   use_invariant_tsc),
			__builtin_offsetof(struct mc_perf_event, count),
			__builtin_offsetof(struct mc_perf_event,
					   child_count_total),
			__builtin_offsetof(struct mc_perf_event, base_user_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   stopped_user_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   user_accum_count),
			__builtin_offsetof(struct mc_perf_event,
					   base_system_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   stopped_system_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   system_accum_count),
			__builtin_offsetof(struct thread, user_tsc),
			__builtin_offsetof(struct thread, system_tsc),
			perf_read_attr_flags_bridge,
			perf_event_update_bridge,
			perf_event_atomic64_read_bridge);
}

static unsigned long
perf_event_read_value_bridge(void *event)
{
	return perf_event_read_value((struct mc_perf_event *)event);
}

static int
perf_event_read_group(struct mc_perf_event *event, unsigned long read_format, char  *buf)
{
	(void)read_format;

	return perf_event_read_group_body_result(event, (unsigned long)buf,
			__builtin_offsetof(struct mc_perf_event,
					   group_leader),
			__builtin_offsetof(struct mc_perf_event,
					   nr_siblings),
			__builtin_offsetof(struct mc_perf_event,
					   sibling_list),
			__builtin_offsetof(struct mc_perf_event,
					   group_entry),
			perf_event_read_value_bridge,
			syscall_copy_to_user_bridge);
}

static int
perf_event_read_one(struct mc_perf_event *event, unsigned long read_format, char *buf)
{
	(void)read_format;

	return perf_event_read_one_body_result(event, (unsigned long)buf,
			perf_event_read_value_bridge,
			syscall_copy_to_user_bridge);
}

static long
perf_event_read_group_bridge(void *event, unsigned long read_format,
		unsigned long buf_addr)
{
	return perf_event_read_group((struct mc_perf_event *)event,
			read_format, (char *)buf_addr);
}

static long
perf_event_read_one_bridge(void *event, unsigned long read_format,
		unsigned long buf_addr)
{
	return perf_event_read_one((struct mc_perf_event *)event,
			read_format, (char *)buf_addr);
}

static long
perf_read(struct mckfd *sfd, ihk_mc_user_context_t *ctx)
{
	char *buf  = (char *)ihk_mc_syscall_arg1(ctx);
	struct mc_perf_event *event = (struct mc_perf_event*)sfd->data;
	unsigned long read_format = event->attr.read_format;

	return perf_read_body_result(event, (unsigned long)buf,
			read_format, PERF_FORMAT_GROUP,
			perf_event_read_group_bridge,
			perf_event_read_one_bridge);
}

static int
perf_counter_mask_check_bridge(unsigned long counter_mask)
{
	return ihk_mc_perf_counter_mask_check(counter_mask);
}

static int
perf_event_set_period_bridge(void *event)
{
	return ihk_mc_event_set_period((struct mc_perf_event *)event);
}

static int
perf_counter_set_bridge(void *event)
{
	return perf_counter_set((struct mc_perf_event *)event);
}

static int
perf_counter_start_bridge(unsigned long counter_mask)
{
	return ihk_mc_perfctr_start(counter_mask);
}

static int
perf_counter_stop_bridge(unsigned long counter_mask, int flags)
{
	return ihk_mc_perfctr_stop(counter_mask, flags);
}

void perf_start(struct mc_perf_event *event)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	(void)perf_start_body_result(event, thread,
			__builtin_offsetof(struct mc_perf_event, group_leader),
			__builtin_offsetof(struct mc_perf_event, sibling_list),
			__builtin_offsetof(struct mc_perf_event, group_entry),
			__builtin_offsetof(struct mc_perf_event, counter_id),
			__builtin_offsetof(struct mc_perf_event, state),
			__builtin_offsetof(struct mc_perf_event,
					   use_invariant_tsc),
			__builtin_offsetof(struct mc_perf_event, base_user_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   stopped_user_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   user_accum_count),
			__builtin_offsetof(struct mc_perf_event,
					   base_system_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   stopped_system_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   system_accum_count),
			__builtin_offsetof(struct thread, user_tsc),
			__builtin_offsetof(struct thread, system_tsc),
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, perf_status),
			PERF_EVENT_STATE_INACTIVE, PERF_EVENT_STATE_ACTIVE,
			PP_COUNT, perf_counter_mask_check_bridge,
			perf_event_set_period_bridge, perf_counter_set_bridge,
			perf_counter_start_bridge);
}

void
perf_reset(struct mc_perf_event *event)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	(void)perf_reset_body_result(event, thread,
			__builtin_offsetof(struct mc_perf_event, group_leader),
			__builtin_offsetof(struct mc_perf_event, sibling_list),
			__builtin_offsetof(struct mc_perf_event, group_entry),
			__builtin_offsetof(struct mc_perf_event, counter_id),
			__builtin_offsetof(struct mc_perf_event,
					   use_invariant_tsc),
			__builtin_offsetof(struct mc_perf_event, base_user_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   stopped_user_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   user_accum_count),
			__builtin_offsetof(struct mc_perf_event,
					   base_system_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   stopped_system_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   system_accum_count),
			__builtin_offsetof(struct mc_perf_event, count),
			__builtin_offsetof(struct thread, user_tsc),
			__builtin_offsetof(struct thread, system_tsc),
			perf_counter_mask_check_bridge,
			perf_event_read_value_bridge,
			sync_child_count_set_bridge);
}

static void
perf_stop(struct mc_perf_event *event)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	(void)perf_stop_body_result(event, thread,
			__builtin_offsetof(struct mc_perf_event, group_leader),
			__builtin_offsetof(struct mc_perf_event, sibling_list),
			__builtin_offsetof(struct mc_perf_event, group_entry),
			__builtin_offsetof(struct mc_perf_event, counter_id),
			__builtin_offsetof(struct mc_perf_event, state),
			__builtin_offsetof(struct mc_perf_event,
					   use_invariant_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   stopped_user_tsc),
			__builtin_offsetof(struct mc_perf_event,
					   stopped_system_tsc),
			__builtin_offsetof(struct thread, user_tsc),
			__builtin_offsetof(struct thread, system_tsc),
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, monitoring_event),
			__builtin_offsetof(struct process, perf_status),
			PERF_EVENT_STATE_ACTIVE, PERF_EVENT_STATE_INACTIVE,
			PP_NONE, 0, perf_counter_mask_check_bridge,
			perf_counter_stop_bridge,
			perf_event_update_bridge);
}

static void
perf_start_bridge(void *event)
{
	perf_start((struct mc_perf_event *)event);
}

static void
perf_stop_bridge(void *event)
{
	perf_stop((struct mc_perf_event *)event);
}

static void
perf_reset_bridge(void *event)
{
	perf_reset((struct mc_perf_event *)event);
}

static int
perf_ioctl(struct mckfd *sfd, ihk_mc_user_context_t *ctx)
{
	unsigned int cmd = ihk_mc_syscall_arg1(ctx);
	struct mc_perf_event *event = (struct mc_perf_event*)sfd->data;
	struct mcs_rwlock_node_irqsave lock;

	return (int)perf_ioctl_body_result(event, get_this_cpu_local_var()->current->proc,
			&lock, cmd, event ? event->attr.inherit : 0,
			PERF_EVENT_IOC_ENABLE, PERF_EVENT_IOC_DISABLE,
			PERF_EVENT_IOC_RESET, PERF_EVENT_IOC_REFRESH,
			PP_RESET,
			__builtin_offsetof(struct mc_perf_event, pid),
			__builtin_offsetof(struct process, monitoring_event),
			__builtin_offsetof(struct process, perf_status),
			perf_start_bridge, perf_stop_bridge, perf_reset_bridge,
			syscall_find_process_bridge,
			syscall_process_unlock_bridge);
}

static int
perf_close(struct mckfd *sfd, ihk_mc_user_context_t *ctx)
{
	struct mc_perf_event *event = (struct mc_perf_event*)sfd->data;
	struct thread *thread = get_this_cpu_local_var()->current;

	(void)ctx;

	return (int)perf_close_body_result(event, thread,
			__builtin_offsetof(struct mc_perf_event, counter_id),
			__builtin_offsetof(struct mc_perf_event, extra_reg.reg),
			__builtin_offsetof(struct mc_perf_event, extra_reg.idx),
			__builtin_offsetof(struct thread, pmc_alloc_map),
			__builtin_offsetof(struct thread, extra_reg_alloc_map),
			syscall_mckfd_free_bridge);
}

static int
perf_fcntl(struct mckfd *sfd, ihk_mc_user_context_t *ctx)
{
	int cmd = ihk_mc_syscall_arg1(ctx);
	long arg = ihk_mc_syscall_arg2(ctx);

	return (int)perf_fcntl_body_result(sfd, ctx, cmd, arg, __NR_fcntl,
			10, 0xf, __builtin_offsetof(struct mckfd, sig_no),
			syscall_forward_context_bridge);
}

static long
perf_mmap(struct mckfd *sfd, ihk_mc_user_context_t *ctx)
{
	intptr_t addr0 = ihk_mc_syscall_arg0(ctx);
	size_t len0 = ihk_mc_syscall_arg1(ctx);
	int prot = ihk_mc_syscall_arg2(ctx);
	int flags = ihk_mc_syscall_arg3(ctx);
	int fd = ihk_mc_syscall_arg4(ctx);
	off_t off0 = ihk_mc_syscall_arg5(ctx);

	(void)sfd;

	return perf_mmap_body_result(addr0, len0, prot, flags, fd, off0,
			MAP_ANONYMOUS, PROT_WRITE,
			__builtin_offsetof(struct perf_event_mmap_page,
					   data_head),
			__builtin_offsetof(struct perf_event_mmap_page,
					   capabilities),
			1UL << 2, do_mmap);
}

static int
perf_event_open_counter_alloc_bridge(void *thread, void *event)
{
	return ihk_mc_perfctr_alloc((struct thread *)thread,
			(struct mc_perf_event *)event);
}

static long
perf_event_open_do_syscall_bridge(struct syscall_request *request, int cpu)
{
	return do_syscall(request, cpu);
}
#endif /*ENABLE_PERF*/

struct vm_range_numa_policy *vm_range_policy_search(struct process_vm *vm, uintptr_t addr)
{
	struct rb_root *root = &vm->vm_range_numa_policy_tree;
	struct rb_node *node = root->rb_node;
	struct vm_range_numa_policy *numa_policy = NULL;

	while (node) {
		numa_policy = ((struct vm_range_numa_policy *)((char *)(node) - offsetof(struct vm_range_numa_policy, policy_rb_node)));
		if (addr < numa_policy->start) {
			node = node->rb_left;
		} else if (addr >= numa_policy->end) {
			node = node->rb_right;
		} else {
			return numa_policy;
		}
	}

	return NULL;
}

static int vm_policy_insert(struct process_vm *vm,
		struct vm_range_numa_policy *newrange)
{
	struct rb_root *root = &vm->vm_range_numa_policy_tree;
	struct rb_node **new = &(root->rb_node), *parent = NULL;
	struct vm_range_numa_policy *range;

	while (*new) {
		range = ((struct vm_range_numa_policy *)((char *)(*new) - offsetof(struct vm_range_numa_policy, policy_rb_node)));
		parent = *new;
		if (newrange->end <= range->start) {
			new = &((*new)->rb_left);
		} else if (newrange->start >= range->end) {
			new = &((*new)->rb_right);
		} else {
			ekprintf("%s(%p,%lx-%lx (nodemask)%lx (policy)%d): overlap %lx-%lx (nodemask)%lx (policy)%d\n",
					__func__, vm, newrange->start,
					newrange->end, newrange->numa_mask,
					newrange->numa_mem_policy, range->start,
					range->end, range->numa_mask,
					range->numa_mem_policy);
			return -EFAULT;
		}
	}

	dkprintf("%s: %p,%p: %lx-%lx (nodemask)%lx (policy)%d\n",
			__func__, vm, newrange, newrange->start, newrange->end,
			newrange->numa_mask, newrange->numa_mem_policy);

	rb_link_node(&newrange->policy_rb_node, parent, new);
	rb_insert_color(&newrange->policy_rb_node, root);

	return 0;
}

static int vm_policy_clear_range(struct process_vm *vm,
		unsigned long start, unsigned long end)
{
	struct rb_root *root = &vm->vm_range_numa_policy_tree;
	struct vm_range_numa_policy *range, *range_policy_iter;
	struct vm_range_numa_policy *range_policy;
	struct rb_node *node;
	int error = 0;

	/*
	 * Adjust overlapping range settings and add new one
	 *  case: front part of new range overlaps existing one
	 *  case: new range is a part of existing range
	 */
	range_policy_iter = vm_range_policy_search(vm, start);
	if (range_policy_iter) {
		int adjusted = 0;
		unsigned long orig_end = range_policy_iter->end;

		if (range_policy_iter->start == start &&
				range_policy_iter->end == end) {
			rb_erase(&range_policy_iter->policy_rb_node,
				&vm->vm_range_numa_policy_tree);
			kfree_tracked(range_policy_iter, __FILE__, __LINE__);
			error = 0;
			goto out;
		}

		/* Overlapping partially? */
		if (range_policy_iter->start < start) {
			orig_end = range_policy_iter->end;
			range_policy_iter->end = start;
			adjusted = 1;
		}

		/* Do we need to keep the end? */
		if (orig_end > end) {
			if (adjusted) {
				/* Add a new entry after */
				range_policy = kmalloc_tracked(sizeof(struct vm_range_numa_policy), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
				if (!range_policy) {
					dkprintf("%s: error allocating range_policy\n",
							__func__);
					error = -ENOMEM;
					goto out;
				}

				RB_CLEAR_NODE(&range_policy->policy_rb_node);
				range_policy->start = end;
				range_policy->end = orig_end;
				range_policy->numa_mem_policy =
					range_policy_iter->numa_mem_policy;

				memcpy(range_policy->numa_mask,
					&range_policy_iter->numa_mask,
					sizeof(range_policy->numa_mask));

				error = vm_policy_insert(vm, range_policy);
				if (error) {
					kprintf("%s: ERROR: could not insert range: %d\n",
							__func__, error);
					goto out;
				}
			}
			else {
				range_policy_iter->start = end;
			}
		}
	}

	/*
	 * Adjust overlapping range settings
	 *  case: rear part of new range overlaps existing range
	 */
	range_policy_iter = vm_range_policy_search(vm, end - 1);
	if (range_policy_iter) {
		range_policy_iter->start = end;
	}

	/* Search fulliy contained range */
again_search:
	for (node = rb_first(root); node; node = rb_next(node)) {
		range = ((struct vm_range_numa_policy *)((char *)(node) - offsetof(struct vm_range_numa_policy, policy_rb_node)));

		/* existing range is fully contained */
		if (range->start >= start && range->end <= end) {
			rb_erase(&range->policy_rb_node,
				&vm->vm_range_numa_policy_tree);
			kfree_tracked(range, __FILE__, __LINE__);
			goto again_search;
		}
	}

out:
	return error;
}

#ifdef ENABLE_PERF
static void *
perf_event_alloc_kmalloc_bridge(size_t size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

static void
perf_event_alloc_free_bridge(void *event)
{
	kfree_tracked(event, __FILE__, __LINE__);
}

static int
perf_event_alloc_hw_init_bridge(void *event)
{
	return hw_perf_event_init((struct mc_perf_event *)event);
}

static int mc_perf_event_alloc(struct mc_perf_event **out,
			       struct perf_event_attr *attr)
{
	return perf_event_alloc_body_result((void **)out, attr,
			sizeof(struct mc_perf_event),
			sizeof(struct perf_event_attr),
			IHK_MC_AP_NOWAIT,
			__builtin_offsetof(struct mc_perf_event, attr),
			__builtin_offsetof(struct mc_perf_event, group_entry),
			__builtin_offsetof(struct mc_perf_event, sibling_list),
			__builtin_offsetof(struct mc_perf_event, sample_freq),
			__builtin_offsetof(struct mc_perf_event, nr_siblings),
			__builtin_offsetof(struct mc_perf_event, count),
			__builtin_offsetof(struct mc_perf_event, child_count_total),
			__builtin_offsetof(struct mc_perf_event, parent),
			__builtin_offsetof(struct mc_perf_event, hw.sample_period),
			__builtin_offsetof(struct mc_perf_event, hw.last_period),
			__builtin_offsetof(struct mc_perf_event, hw.period_left),
			__builtin_offsetof(struct mc_perf_event, use_invariant_tsc),
			__builtin_offsetof(struct mc_perf_event, hw_config),
			__builtin_offsetof(struct mc_perf_event, hw_config_ext),
			__builtin_offsetof(struct mc_perf_event, extra_reg.config),
			__builtin_offsetof(struct mc_perf_event, extra_reg.reg),
			__builtin_offsetof(struct mc_perf_event, extra_reg.idx),
			attr ? attr->type : 0, attr ? attr->config : 0,
			attr ? attr->freq : 0,
			attr ? attr->sample_freq : 0,
			attr ? attr->sample_period : 0,
			PERF_TYPE_HARDWARE, PERF_TYPE_HW_CACHE, PERF_TYPE_RAW,
			PERF_COUNT_HW_REF_CPU_CYCLES,
			perf_event_alloc_kmalloc_bridge,
			perf_event_alloc_free_bridge,
			sync_child_count_set_bridge,
			ihk_mc_hw_event_map, ihk_mc_hw_cache_event_map,
			ihk_mc_hw_cache_extra_reg_map, ihk_mc_raw_event_map,
			ihk_mc_validate_event, ihk_mc_get_extra_reg_id,
			ihk_mc_get_extra_reg_msr, ihk_mc_get_extra_reg_idx,
			perf_event_alloc_hw_init_bridge);
}

static int
perf_event_open_alloc_event_bridge(void **event_out, void *attr)
{
	return mc_perf_event_alloc((struct mc_perf_event **)event_out,
			(struct perf_event_attr *)attr);
}

static int
perf_event_open_attr_freq_bridge(const void *attr)
{
	return ((const struct perf_event_attr *)attr)->freq;
}

long sys_perf_event_open(int n, ihk_mc_user_context_t *ctx)
{
	struct syscall_request request IHK_DMA_ALIGN;
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process *proc = thread->proc;
	struct perf_event_attr *arg0 = (void *)ihk_mc_syscall_arg0(ctx);
	int pid = ihk_mc_syscall_arg1(ctx);
	int cpu = ihk_mc_syscall_arg2(ctx);
	int group_fd = ihk_mc_syscall_arg3(ctx);
	unsigned long flags = ihk_mc_syscall_arg4(ctx);
	struct perf_event_attr attr_user;

#ifndef ENABLE_PERF
	return perf_event_open_disabled_body_result();
#endif // ENABLE_PERF

	return perf_event_open_entry_body_result(&request, thread, proc,
			&attr_user, (unsigned long)arg0,
			sizeof(struct perf_event_attr),
			__builtin_offsetof(struct perf_event_attr, type),
			__builtin_offsetof(struct perf_event_attr, read_format),
			__builtin_offsetof(struct perf_event_attr, sample_period),
			pid, cpu, group_fd, flags, ihk_mc_get_processor_id(),
			PERF_TYPE_RAW, PERF_TYPE_HARDWARE, PERF_TYPE_HW_CACHE,
			PERF_FORMAT_TOTAL_TIME_ENABLED |
			PERF_FORMAT_TOTAL_TIME_RUNNING | PERF_FORMAT_ID,
			1UL << 63, __NR_perf_event_open, sizeof(struct mckfd),
			IHK_MC_AP_NOWAIT,
			__builtin_offsetof(struct mc_perf_event, pid),
			__builtin_offsetof(struct mc_perf_event, counter_id),
			__builtin_offsetof(struct process, mckfd),
			__builtin_offsetof(struct mckfd, next),
			__builtin_offsetof(struct mckfd, fd),
			__builtin_offsetof(struct mckfd, data),
			__builtin_offsetof(struct mc_perf_event, group_leader),
			__builtin_offsetof(struct mc_perf_event, sibling_list),
			__builtin_offsetof(struct mc_perf_event, group_entry),
			__builtin_offsetof(struct mc_perf_event, nr_siblings),
			__builtin_offsetof(struct mc_perf_event, pmc_status),
			__builtin_offsetof(struct thread, pmc_alloc_map),
			__builtin_offsetof(struct process, mckfd_lock),
			__builtin_offsetof(struct mckfd, sig_no),
			__builtin_offsetof(struct mckfd, read_cb),
			__builtin_offsetof(struct mckfd, ioctl_cb),
			__builtin_offsetof(struct mckfd, mmap_cb),
			__builtin_offsetof(struct mckfd, close_cb),
			__builtin_offsetof(struct mckfd, fcntl_cb),
			syscall_copy_from_user_bridge,
			perf_event_open_attr_freq_bridge,
			perf_event_open_alloc_event_bridge,
			perf_event_open_counter_alloc_bridge,
			perf_event_open_do_syscall_bridge,
			perf_event_alloc_kmalloc_bridge,
			perf_read, perf_ioctl, perf_mmap, perf_close, perf_fcntl,
			syscall_mckfd_lock_bridge,
			syscall_mckfd_unlock_bridge);
}
#endif /* ENABLE_PERF */

long sys_rt_sigtimedwait(int n, ihk_mc_user_context_t *ctx)
{
	const sigset_t *set = (const sigset_t *)ihk_mc_syscall_arg0(ctx);
	siginfo_t *info = (siginfo_t *)ihk_mc_syscall_arg1(ctx);
	void *timeout = (void *)ihk_mc_syscall_arg2(ctx);
	size_t sigsetsize = (size_t)ihk_mc_syscall_arg3(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	siginfo_t winfo;
	__sigset_t bset;
	__sigset_t blocked_set;
	__sigset_t wset;
	__sigset_t nset;
	struct timespec wtimeout;
	struct sig_pending *pending;
	struct list_head *head;
	mcs_rwlock_lock_t *lock;
	struct mcs_rwlock_node_irqsave mcs_rw_node;
	__sigset_t w;
	int sig;
        struct timespec ats;
        struct timespec ets;
	struct ihk_os_cpu_monitor *monitor = get_this_cpu_local_var()->monitor;
	int error;

	monitor->status = IHK_OS_MONITOR_KERNEL_HEAVY;

	error = rt_sigtimedwait_prepare(sigsetsize, sizeof(sigset_t),
			set != NULL);
	if (error) {
		return error;
	}

	memset(&winfo, '\0', sizeof winfo);
	if(copy_from_user(&wset, set, sizeof wset))
		return -EFAULT;
	if(timeout){
		if(copy_from_user(&wtimeout, timeout, sizeof wtimeout))
			return -EFAULT;
		error = rt_sigtimedwait_timeout_result(wtimeout.tv_sec,
				wtimeout.tv_nsec, gettime_local_support);
		if (error) {
			return error;
		}
	}

	bset = thread->sigmask.__val[0];
	rt_sigtimedwait_prepare_masks(wset, bset, &wset, &blocked_set, &nset);
	thread->sigmask.__val[0] = blocked_set;

	if(timeout){
		if (gettime_local_support) {
			calculate_time_from_tsc(&ets);
			rt_sigtimedwait_deadline(ets.tv_sec, ets.tv_nsec,
					wtimeout.tv_sec, wtimeout.tv_nsec,
					&ets.tv_sec, &ets.tv_nsec);
		}
		else {
			memset(&ats, '\0', sizeof ats);
			memset(&ets, '\0', sizeof ets);
		}
	}

	thread->sigevent = 1;
	for(;;){
		while(thread->sigevent == 0){
			thread->status = PS_INTERRUPTIBLE;
			if(timeout){
				if (gettime_local_support)
					calculate_time_from_tsc(&ats);
				if(rt_sigtimedwait_timeout_expired(ats.tv_sec,
						ats.tv_nsec, ets.tv_sec,
						ets.tv_nsec)){
					return -EAGAIN;
				}
			}

			cpu_pause();
		}
		/*
		 * Sending signal here is detected
		 * by the following list check
		 */
		thread->sigevent = 0;

		thread->status = PS_RUNNING;
		lock = &thread->sigcommon->lock;
		head = &thread->sigcommon->sigpending;
		mcs_rwlock_writer_lock(lock, &mcs_rw_node);
		for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))){
			if(pending->sigmask.__val[0] & wset)
				break;
		}

		if(&pending->list == head){
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

			lock = &thread->sigpendinglock;
			head = &thread->sigpending;
			mcs_rwlock_writer_lock(lock, &mcs_rw_node);
			for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))){
				if(pending->sigmask.__val[0] & wset)
					break;
			}
		}

		if(&pending->list != head){
			process_list_detach_result(&pending->list);
			thread->sigmask.__val[0] = bset;
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);
			break;
		}
		mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

		lock = &thread->sigcommon->lock;
		head = &thread->sigcommon->sigpending;
		mcs_rwlock_writer_lock(lock, &mcs_rw_node);
		for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))){
			if(pending->sigmask.__val[0] & nset)
				break;
		}

		if(&pending->list == head){
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

			lock = &thread->sigpendinglock;
			head = &thread->sigpending;
			mcs_rwlock_writer_lock(lock, &mcs_rw_node);
			for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))){
				if(pending->sigmask.__val[0] & nset)
					break;
			}
		}

		if(&pending->list != head){
			process_list_detach_result(&pending->list);
			thread->sigmask.__val[0] = bset;
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);
			do_signal(-EINTR, NULL, thread, pending, -1);
			return -EINTR;
		}
		mcs_rwlock_writer_unlock(lock, &mcs_rw_node);
	}

	if(info){
		if(copy_to_user(info, &pending->info, sizeof(siginfo_t))){
			kfree_tracked(pending, __FILE__, __LINE__);
			return -EFAULT;
		}
	}
	w = pending->sigmask.__val[0];
	sig = sigmask_to_signal_number(w);
	kfree_tracked(pending, __FILE__, __LINE__);

	return sig;
}

long
syscall_do_kill_current_bridge(int pid, int sig, const void *info)
{
	return do_kill(get_this_cpu_local_var()->current, pid, -1, sig,
			(struct siginfo *)info, 0);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_rt_sigqueueinfo(int n, ihk_mc_user_context_t *ctx);
#else
long sys_rt_sigqueueinfo(int n, ihk_mc_user_context_t *ctx)
{
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	int sig = (int)ihk_mc_syscall_arg1(ctx);
	void *winfo = (void *)ihk_mc_syscall_arg2(ctx);

	return rt_sigqueueinfo_body_result(pid, sig, (unsigned long)winfo,
			syscall_copy_from_user_bridge,
			syscall_do_kill_current_bridge);
}
#endif

static int
do_sigsuspend(struct thread *thread, const sigset_t *set)
{
	__sigset_t wset;
	__sigset_t bset;
	struct sig_pending *pending;
	struct list_head *head;
	mcs_rwlock_lock_t *lock;
	struct mcs_rwlock_node_irqsave mcs_rw_node;
	struct ihk_os_cpu_monitor *monitor = get_this_cpu_local_var()->monitor;

	monitor->status = IHK_OS_MONITOR_KERNEL_HEAVY;

	wset = sigsuspend_prepare_mask(set->__val[0]);
	bset = thread->sigmask.__val[0];
	thread->sigmask.__val[0] = wset;

	thread->sigevent = 1;
	for (;;) {
		while (thread->sigevent == 0) {
			int do_schedule = 0;
			struct cpu_local_var *v;
			long runq_irqstate;

			thread->status = PS_INTERRUPTIBLE;
			runq_irqstate = cpu_disable_interrupt_save();
			ihk_mc_spinlock_lock_noirq(
				&(get_this_cpu_local_var()->runq_lock));
			v = get_this_cpu_local_var();

			if (v->flags & CPU_FLAG_NEED_RESCHED) {
				v->flags &= ~CPU_FLAG_NEED_RESCHED;
				do_schedule = 1;
			}

			ihk_mc_spinlock_unlock_noirq(&v->runq_lock);
			cpu_restore_interrupt(runq_irqstate);
			
			if (do_schedule) {
				schedule();
			}
			else {
				cpu_pause();
			}
		}

		/*
		 * Sending signal here is detected
		 * by the following list check
		 */
		thread->sigevent = 0;

		thread->status = PS_RUNNING;
		lock = &thread->sigcommon->lock;
		head = &thread->sigcommon->sigpending;
		mcs_rwlock_writer_lock(lock, &mcs_rw_node);
		for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))){
			if(sigsuspend_pending_matches(
					pending->sigmask.__val[0], wset))
				break;
		}

		if(&pending->list == head){
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

			lock = &thread->sigpendinglock;
			head = &thread->sigpending;
			mcs_rwlock_writer_lock(lock, &mcs_rw_node);
			for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))){
				if(sigsuspend_pending_matches(
						pending->sigmask.__val[0], wset))
					break;
			}
	}
		if(&pending->list == head){
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);
			continue;
		}

		process_list_detach_result(&pending->list);
		mcs_rwlock_writer_unlock(lock, &mcs_rw_node);
		thread->sigmask.__val[0] = bset;
		do_signal(-EINTR, NULL, thread, pending, -1);
		break;
	}
	return -EINTR;
}

long
syscall_sigsuspend_bridge(void *thread, void *set)
{
	return do_sigsuspend(thread, set);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_pause(int n, ihk_mc_user_context_t *ctx);
#else
long sys_pause(int n, ihk_mc_user_context_t *ctx)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	return pause_body_result(thread, __builtin_offsetof(struct thread, sigmask),
			syscall_sigsuspend_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_rt_sigsuspend(int n, ihk_mc_user_context_t *ctx);
#else
long sys_rt_sigsuspend(int n, ihk_mc_user_context_t *ctx)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	const sigset_t *set = (const sigset_t *)ihk_mc_syscall_arg0(ctx);
	size_t sigsetsize = (size_t)ihk_mc_syscall_arg1(ctx);
	sigset_t wset;

	return rt_sigsuspend_body_result(thread, (unsigned long)set,
			sigsetsize, sizeof(sigset_t), &wset,
			syscall_copy_from_user_bridge,
			syscall_sigsuspend_bridge);
}
#endif

int
syscall_do_sigaction_bridge(int sig, void *act, void *oact)
{
	return do_sigaction(sig, act, oact);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_rt_sigaction(int n, ihk_mc_user_context_t *ctx);
#else
long sys_rt_sigaction(int n, ihk_mc_user_context_t *ctx)
{
	int sig = ihk_mc_syscall_arg0(ctx);
	const struct sigaction *act =
		(const struct sigaction *)ihk_mc_syscall_arg1(ctx);
	struct sigaction *oact = (struct sigaction *)ihk_mc_syscall_arg2(ctx);
	size_t sigsetsize = ihk_mc_syscall_arg3(ctx);

	return rt_sigaction_body_result(sig, (unsigned long)act,
			(unsigned long)oact, sigsetsize, sizeof(sigset_t),
			syscall_copy_from_user_bridge,
			syscall_copy_to_user_bridge,
			syscall_do_sigaction_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_sigaltstack(int n, ihk_mc_user_context_t *ctx);
#else
long sys_sigaltstack(int n, ihk_mc_user_context_t *ctx)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	const stack_t *ss = (const stack_t *)ihk_mc_syscall_arg0(ctx);
	stack_t *oss = (stack_t *)ihk_mc_syscall_arg1(ctx);

	return sigaltstack_body_result(thread,
			__builtin_offsetof(struct thread, sigstack),
			(unsigned long)ss, (unsigned long)oss,
			syscall_copy_from_user_bridge,
			syscall_copy_to_user_bridge);
}
#endif

static void
mincore_range_read_lock_bridge(void *lock)
{
	ihk_rwspinlock_read_lock_noirq((ihk_rwspinlock_t *)lock);
}

static void
mincore_range_read_unlock_bridge(void *lock)
{
	ihk_rwspinlock_read_unlock_noirq((ihk_rwspinlock_t *)lock);
}

static void
mincore_pte_lock_bridge(void *lock)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock);
}

static void
mincore_pte_unlock_bridge(void *lock)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock);
}

static struct vm_range *
mincore_lookup_range_bridge(struct process_vm *vm, unsigned long start,
		unsigned long end)
{
	return lookup_process_memory_range(vm, start, end);
}

static void *
mincore_pte_lookup_bridge(void *page_table, unsigned long addr)
{
	return ihk_mc_pt_lookup_pte(page_table, (void *)addr, 0, NULL, NULL, NULL);
}

static int
mincore_pte_present_bridge(void *pte)
{
	return pte_is_present((pte_t *)pte);
}

static int
mincore_memobj_lookup_bridge(void *memobj, unsigned long offset)
{
	return memobj_lookup_page(memobj, offset, PAGE_P2ALIGN, NULL, NULL);
}

static long
mincore_copy_byte_bridge(unsigned long dst, unsigned char value)
{
	return copy_to_user((void *)dst, &value, sizeof(value));
}

static void
mincore_log_bridge(int event, unsigned long start, size_t len,
		unsigned long vec, int error)
{
	if (event == MINCORE_LOG_INVALID) {
		dkprintf("mincore(0x%lx,0x%lx,%p): invalid %d\n",
				start, len, (void *)vec, error);
	}
	else if (event == MINCORE_LOG_LOOKUP_FAILED) {
		dkprintf("mincore(0x%lx,0x%lx,%p):lookup failed. ENOMEM\n",
				start, len, (void *)vec);
	}
	else if (event == MINCORE_LOG_COPY_FAILED) {
		dkprintf("mincore(0x%lx,0x%lx,%p):copy failed. %d\n",
				start, len, (void *)vec, error);
	}
	else if (event == MINCORE_LOG_EXIT) {
		dkprintf("mincore(0x%lx,0x%lx,%p): 0\n",
				start, len, (void *)vec);
	}
}

long sys_mincore(int n, ihk_mc_user_context_t *ctx)
{
	const uintptr_t start = ihk_mc_syscall_arg0(ctx);
	const size_t len = ihk_mc_syscall_arg1(ctx);
	const uintptr_t vec = ihk_mc_syscall_arg2(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process_vm *vm = thread->vm;

	return mincore_body_result(vm, &vm->memory_range_lock,
			&vm->page_table_lock, vm->address_space->page_table,
			start, len, vec, vm->region.user_start, vm->region.user_end,
			__builtin_offsetof(struct vm_range, start),
			__builtin_offsetof(struct vm_range, end),
			__builtin_offsetof(struct vm_range, memobj),
			__builtin_offsetof(struct vm_range, objoff),
			mincore_range_read_lock_bridge,
			mincore_range_read_unlock_bridge, mincore_pte_lock_bridge,
			mincore_pte_unlock_bridge, mincore_lookup_range_bridge,
			mincore_pte_lookup_bridge, mincore_pte_present_bridge,
			mincore_memobj_lookup_bridge, mincore_copy_byte_bridge,
			mincore_log_bridge);
} /* sys_mincore() */

static int
set_memory_range_flag(struct vm_range *range, unsigned long arg)
{
	range->flag |= arg;
	return 0;
}

static int
clear_memory_range_flag(struct vm_range *range, unsigned long arg)
{
	range->flag &= ~arg;
	return 0;
}

static int
change_attr_process_memory_range(struct process_vm *vm,
                                 uintptr_t start, uintptr_t end,
                                 int (*change_proc)(struct vm_range *,
                                                    unsigned long),
                                 unsigned long arg)
{
	uintptr_t addr;
	int error;
	struct vm_range *range;
	struct vm_range *prev;
	struct vm_range *next;
	int join_flag = 0;

	error = 0;
	range = lookup_process_memory_range(vm, start, start + PAGE_SIZE);
	if(!range){
		error = -ENOMEM;
		goto out;
	}

	prev = previous_process_memory_range(vm, range);
	if(!prev)
		prev = range;
	for (addr = start; addr < end; addr = range->start) {
		if (range->start < addr) {
			if((error = split_process_memory_range(vm, range, addr, &range))) {
				break;
			}
		}
		if (end < range->end) {
			if((error = split_process_memory_range(vm, range, end, NULL))) {
				break;
			}
		}

		if((error = change_proc(range, arg)) != 0){
			break;
		}
		range = next_process_memory_range(vm, range);
	}

	if(error == 0){
		next = next_process_memory_range(vm, range);
		if(!next)
			next = range;
	}
	else{
		next = range;
	}

	while(prev != next){
		int wkerr;

		range = next_process_memory_range(vm, prev);
		if(!range)
			break;
		wkerr = join_process_memory_range(vm, prev, range);
		if(range == next)
			join_flag = 1;
		if (wkerr) {
			if(join_flag)
				break;
			prev = range;
		}
	}

out:
	return error;
}

void
syscall_madvise_log_bridge(int cpu, unsigned long start, size_t len0,
		int advice)
{
	dkprintf("[%d]sys_madvise(%lx,%lx,%x)\n", cpu, start, len0, advice);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_madvise(int n, ihk_mc_user_context_t *ctx);
#else
long sys_madvise(int n, ihk_mc_user_context_t *ctx)
{
	const uintptr_t start = (uintptr_t)ihk_mc_syscall_arg0(ctx);
	const size_t len0 = (size_t)ihk_mc_syscall_arg1(ctx);
	const int advice = (int)ihk_mc_syscall_arg2(ctx);
	size_t len;
	uintptr_t end;
	struct thread *thread = get_this_cpu_local_var()->current;
	struct vm_regions *region = &thread->vm->region;
	struct vm_range *first;
	uintptr_t addr;
	struct vm_range *range;
	int error;
	uintptr_t s;
	uintptr_t e;

	syscall_madvise_log_bridge(ihk_mc_get_processor_id(), start, len0,
			advice);
	return madvise_body_result(start, len0, advice);

	len = (len0 + PAGE_SIZE - 1) & PAGE_MASK;
	end = start + len;

	if ((start & (PAGE_SIZE - 1))
			|| (len < len0)
			|| (end < start)) {
		error = -EINVAL;
		goto out2;
	}

	if ((start < region->user_start)
			|| (region->user_end <= start)
			|| (len > (region->user_end - region->user_start))
			|| ((region->user_end - len) < start)) {
		error = -ENOMEM;
		goto out2;
	}

	error = 0;
	switch (advice) {
	default:
	case MADV_MERGEABLE:
	case MADV_UNMERGEABLE:
		error = -EINVAL;
		break;

	case MADV_HUGEPAGE:
	case MADV_NOHUGEPAGE:
	case MADV_NORMAL:
	case MADV_RANDOM:
	case MADV_SEQUENTIAL:
	case MADV_WILLNEED:
	case MADV_DONTNEED:
	case MADV_DONTFORK:
	case MADV_DOFORK:
	case MADV_REMOVE:
	case MADV_DONTDUMP:
	case MADV_DODUMP:
	case MADV_WIPEONFORK:
	case MADV_KEEPONFORK:
		break;

	case MADV_HWPOISON:
	case MADV_SOFT_OFFLINE:
		error = -EPERM;
		break;

	}
	if (error) {
		goto out2;
	}

	if (start == end) {
		error = 0;
		goto out2;
	}

	ihk_rwspinlock_write_lock_noirq(&thread->vm->memory_range_lock);
	/* check contiguous map */
	first = NULL;
	range = NULL;	/* for avoidance of warning */
	for (addr = start; addr < end; addr = range->end) {
		if (first == NULL) {
			range = lookup_process_memory_range(thread->vm, start, start+PAGE_SIZE);
			first = range;
		}
		else {
			range = next_process_memory_range(thread->vm, range);
		}

		if ((range == NULL) || (addr < range->start)) {
			/* not contiguous */
			dkprintf("[%d]sys_madvise(%lx,%lx,%x):not contig "
					"%lx [%lx-%lx)\n",
					ihk_mc_get_processor_id(), start,
					len0, advice, addr, range?range->start:0,
					range?range->end:0);
			error = -ENOMEM;
			goto out;
		}

		if (advice == MADV_REMOVE) {
			if (range->flag & VR_LOCKED) {
				error = -EINVAL;
				goto out;
			}

			if (!range->memobj || !memobj_is_removable(range->memobj)) {
				dkprintf("sys_madvise(%lx,%lx,%x):"
						"not removable [%lx-%lx)\n",
						start, len0, advice,
						range->start, range->end);
				error = -EACCES;
				goto out;
			}
		}
		else if(advice == MADV_DONTFORK || advice == MADV_DOFORK);
		else if (advice == MADV_DONTDUMP || advice == MADV_DODUMP) {
		}
		else if (advice == MADV_NORMAL) {
			/*
			 * Normally, the settings of MADV_RANDOM and
			 * MADV_SEQUENTIAL are cleared.
			 * MADV_RANDOM and MADV_SEQUENTIAL are not supported,
			 * so do nothing.
			 */
		}
		else if (advice == MADV_WIPEONFORK
			 || advice == MADV_KEEPONFORK) {
			if (range->memobj && memobj_has_pager(range->memobj)) {
				/* device mapping, file mapping */
				error = -EINVAL;
				goto out;
			}
			if (!(range->flag & VR_PRIVATE)) {
				/* VR_SHARED */
				error = -EINVAL;
				goto out;
			}
		}
		else if (!range->memobj || !memobj_has_pager(range->memobj)) {
			dkprintf("[%d]sys_madvise(%lx,%lx,%x):has not pager"
					"[%lx-%lx) %lx\n",
					ihk_mc_get_processor_id(), start,
					len0, advice, range->start,
					range->end, range->memobj);
			error = -EBADF;
			goto out;
		}

		if ((advice == MADV_DONTNEED)
				&& (range->flag & VR_LOCKED)) {
			dkprintf("[%d]sys_madvise(%lx,%lx,%x):locked"
					"[%lx-%lx) %lx\n",
					ihk_mc_get_processor_id(), start,
					len0, advice, range->start,
					range->end, range->flag);
			error = -EINVAL;
			goto out;
		}

		/* only hugetlbfs and shm map support hugepage */
		if ((advice == MADV_HUGEPAGE || advice == MADV_NOHUGEPAGE)
		    && !(range->memobj->flags & (MF_HUGETLBFS | MF_SHM))) {
			error = -EINVAL;
			goto out;
		}

		s = start;
		if (s < range->start) {
			s = range->start;
		}
		e = end;
		if (range->end < e) {
			e = range->end;
		}

		if (advice == MADV_REMOVE) {
			error = invalidate_process_memory_range(
					thread->vm, range, s, e);
			if (error) {
				kprintf("sys_madvise(%lx,%lx,%x):[%lx-%lx):"
						"invalidate failed. %d\n",
						start, len0, advice,
						range->start, range->end,
						error);
				goto out;
			}
		}
	}

	if(advice == MADV_DONTFORK){
		error = change_attr_process_memory_range(thread->vm, start, end,
		                                         set_memory_range_flag,
		                                         VR_DONTFORK);
		if(error){
			goto out;
		}
	}
	if(advice == MADV_DOFORK){
		error = change_attr_process_memory_range(thread->vm, start, end,
		                                         clear_memory_range_flag,
		                                         VR_DONTFORK);
		if(error){
			goto out;
		}
	}
	if(advice == MADV_DONTDUMP){
		error = change_attr_process_memory_range(thread->vm, start, end,
		                                         set_memory_range_flag,
		                                         VR_DONTDUMP);
		if(error){
			goto out;
		}
	}
	if(advice == MADV_DODUMP){
		error = change_attr_process_memory_range(thread->vm, start, end,
		                                         clear_memory_range_flag,
		                                         VR_DONTDUMP);
		if(error){
			goto out;
		}
	}
	if(advice == MADV_DONTFORK ||
	   advice == MADV_DOFORK){
		error = syscall_generic_forwarding(__NR_madvise, ctx);
	}
	if (advice == MADV_WIPEONFORK) {
		error = change_attr_process_memory_range(
				thread->vm, start, end,
				set_memory_range_flag,
				VR_WIPEONFORK);
		if (error) {
			goto out;
		}
	}
	if (advice == MADV_KEEPONFORK) {
		error = change_attr_process_memory_range(
				thread->vm, start, end,
				clear_memory_range_flag,
				VR_WIPEONFORK);
		if (error) {
			goto out;
		}
	}

	error = 0;
out:
	ihk_rwspinlock_write_unlock_noirq(&thread->vm->memory_range_lock);

out2:
	dkprintf("[%d]sys_madvise(%lx,%lx,%x): %d\n",
			ihk_mc_get_processor_id(), start, len0, advice, error);
	return error;
}
#endif

struct kshmid_ds {
	int destroy;
	int padding;
	struct shmobj *obj;
	struct memobj *memobj;
	struct list_head chain;
};

unsigned long shmid_index[512];

#if defined(MCKERNEL_RUST_SHMID_HELPERS) || \
	defined(MCKERNEL_SHMID_HELPERS_TEST_EXPORT)
#define SHMID_HELPER_SCOPE
#else
#define SHMID_HELPER_SCOPE static
#endif

#ifdef MCKERNEL_RUST_SHMID_HELPERS
extern int get_shmid_max_index(void);
#else
SHMID_HELPER_SCOPE int get_shmid_max_index(void)
{
	int i;
	int index = -1;

	for (i = 511; i >= 0; i--) {
		if (shmid_index[i]) {
			index = i * 64 + 63 - __builtin_clzl(shmid_index[i]);
			break;
		}
	}
	return index;
}
#endif /* MCKERNEL_RUST_SHMID_HELPERS */

#ifdef MCKERNEL_RUST_SHMID_HELPERS
extern int get_shmid_index(void);
#else
SHMID_HELPER_SCOPE int get_shmid_index(void)
{
	int index = get_shmid_max_index();
	int i;
	unsigned long x;

	for (index = 0;; index++) {
		i = index / 64;
		x = 1UL << (index % 64);
		if (!(shmid_index[i] & x)) {
			shmid_index[i] |= x;
			break;
		}
	}
	return index;
}
#endif /* MCKERNEL_RUST_SHMID_HELPERS */

struct list_head kds_list = { &(kds_list), &(kds_list) };
struct shminfo the_shminfo = {
	.shmmax = 64L * 1024 * 1024 * 1024,
	.shmmin = 1,
	.shmmni = 4 * 1024,
	.shmall = 4L * 1024 * 1024 * 1024,
};
struct shm_info the_shm_info = { 0, };

#ifdef MCKERNEL_RUST_SHMID_HELPERS
extern int make_shmid(struct shmobj *obj);
#else
SHMID_HELPER_SCOPE int make_shmid(struct shmobj *obj)
{
	return ((int)obj->index << 16) | obj->ds.shm_perm.seq;
} /* make_shmid() */
#endif /* MCKERNEL_RUST_SHMID_HELPERS */

#ifdef MCKERNEL_RUST_SHMID_HELPERS
extern int shmid_to_index(int shmid);
#else
SHMID_HELPER_SCOPE int shmid_to_index(int shmid)
{
	return (shmid >> 16);
} /* shmid_to_index() */
#endif /* MCKERNEL_RUST_SHMID_HELPERS */

#ifdef MCKERNEL_RUST_SHMID_HELPERS
extern int shmid_to_seq(int shmid);
#else
SHMID_HELPER_SCOPE int shmid_to_seq(int shmid)
{
	return (shmid & ((1 << 16) - 1));
} /* shmid_to_seq() */
#endif /* MCKERNEL_RUST_SHMID_HELPERS */

#undef SHMID_HELPER_SCOPE

#if defined(MCKERNEL_RUST_SHM_PERM_HELPERS) || \
	defined(MCKERNEL_SHM_PERM_HELPERS_TEST_EXPORT)
#define SHM_PERM_HELPER_SCOPE
#else
#define SHM_PERM_HELPER_SCOPE static
#endif

#ifdef MCKERNEL_RUST_SHM_PERM_HELPERS
extern int shmget_existing_access_result(uid_t euid, gid_t egid, int shmflg,
		uid_t uid, uid_t cuid, gid_t gid, gid_t cgid, uint16_t mode);
#else
SHM_PERM_HELPER_SCOPE int shmget_existing_access_result(uid_t euid,
		gid_t egid, int shmflg, uid_t uid, uid_t cuid, gid_t gid,
		gid_t cgid, uint16_t mode)
{
	int req;

	if (!euid) {
		return 0;
	}

	req = (shmflg | (shmflg << 3) | (shmflg << 6)) & 0700;
	if ((uid == euid) || (cuid == euid)) {
		/* nothing to do */
	}
	else if ((gid == egid) || (cgid == egid)) {
		req >>= 3;
	}
	else {
		req >>= 6;
	}

	return (req & ~mode) ? -EACCES : 0;
}
#endif /* MCKERNEL_RUST_SHM_PERM_HELPERS */

#ifdef MCKERNEL_RUST_SHM_PERM_HELPERS
extern int shmat_access_result(uid_t euid, gid_t egid, int shmflg,
		uid_t uid, uid_t cuid, gid_t gid, gid_t cgid, uint16_t mode);
#else
SHM_PERM_HELPER_SCOPE int shmat_access_result(uid_t euid, gid_t egid,
		int shmflg, uid_t uid, uid_t cuid, gid_t gid, gid_t cgid,
		uint16_t mode)
{
	int req;

	req = 4;
	if (!(shmflg & SHM_RDONLY)) {
		req |= 2;
	}

	if (!euid) {
		req = 0;
	}
	else if ((euid == uid) || (euid == cuid)) {
		req <<= 6;
	}
	else if ((egid == gid) || (egid == cgid)) {
		req <<= 3;
	}
	else {
		req <<= 0;
	}

	return (req & ~mode) ? -EACCES : 0;
}
#endif /* MCKERNEL_RUST_SHM_PERM_HELPERS */

#ifdef MCKERNEL_RUST_SHM_PERM_HELPERS
extern int shmctl_ipc_stat_access_result(uid_t euid, gid_t egid,
		uid_t uid, uid_t cuid, gid_t gid, gid_t cgid, uint16_t mode);
#else
SHM_PERM_HELPER_SCOPE int shmctl_ipc_stat_access_result(uid_t euid,
		gid_t egid, uid_t uid, uid_t cuid, gid_t gid, gid_t cgid,
		uint16_t mode)
{
	int req;

	if (!euid) {
		req = 0;
	} else if ((euid == uid) || (euid == cuid)) {
		req = 0400;
	} else if ((egid == gid) || (egid == cgid)) {
		req = 0040;
	} else {
		req = 0004;
	}

	return (req & ~mode) ? -EACCES : 0;
}
#endif /* MCKERNEL_RUST_SHM_PERM_HELPERS */

#ifdef MCKERNEL_RUST_SHM_PERM_HELPERS
extern int shm_owner_result(uid_t euid, uid_t uid, uid_t cuid);
#else
SHM_PERM_HELPER_SCOPE int shm_owner_result(uid_t euid, uid_t uid, uid_t cuid)
{
	return ((uid == euid) || (cuid == euid)) ? 0 : -EPERM;
}
#endif /* MCKERNEL_RUST_SHM_PERM_HELPERS */

#ifdef MCKERNEL_RUST_SHM_PERM_HELPERS
extern int shm_owner_or_cap_result(int has_cap, uid_t euid, uid_t uid,
		uid_t cuid);
#else
SHM_PERM_HELPER_SCOPE int shm_owner_or_cap_result(int has_cap, uid_t euid,
		uid_t uid, uid_t cuid)
{
	return (has_cap || (uid == euid) || (cuid == euid)) ? 0 : -EPERM;
}
#endif /* MCKERNEL_RUST_SHM_PERM_HELPERS */

#ifdef MCKERNEL_RUST_SHM_PERM_HELPERS
extern int shmlock_rlimit_result(int has_cap, rlim_t rlim_cur,
		size_t user_locked, size_t size);
#else
SHM_PERM_HELPER_SCOPE int shmlock_rlimit_result(int has_cap, rlim_t rlim_cur,
		size_t user_locked, size_t size)
{
	if (!rlim_cur && !has_cap) {
		return -EPERM;
	}

	if (!has_cap
			&& (rlim_cur != (rlim_t)-1)
			&& ((rlim_cur < user_locked)
				|| ((rlim_cur - user_locked) < size))) {
		return -ENOMEM;
	}

	return 0;
}
#endif /* MCKERNEL_RUST_SHM_PERM_HELPERS */

#undef SHM_PERM_HELPER_SCOPE

int shmobj_list_lookup(int shmid, struct shmobj **objp)
{
	int index;
	int seq;
	struct shmobj *obj;

	index = shmid_to_index(shmid);
	seq = shmid_to_seq(shmid);

	for (obj = ((typeof(*obj) *)((char *)((&kds_list)->next) - offsetof(typeof(*obj), chain))); &obj->chain != (&kds_list); obj = ((typeof(*obj) *)((char *)(obj->chain.next) - offsetof(typeof(*obj), chain)))) {
		if (obj->index == index) {
			break;
		}
	}
	if (&obj->chain == &kds_list) {
		return -EINVAL;
	}
	if (obj->ds.shm_perm.seq != seq) {
		return -EIDRM;
	}

	memobj_ref(&obj->memobj);
	*objp = obj;
	return 0;
} /* shmobj_list_lookup() */

int shmobj_list_lookup_by_key(key_t key, struct shmobj **objp)
{
	struct shmobj *obj;

	for (obj = ((typeof(*obj) *)((char *)((&kds_list)->next) - offsetof(typeof(*obj), chain))); &obj->chain != (&kds_list); obj = ((typeof(*obj) *)((char *)(obj->chain.next) - offsetof(typeof(*obj), chain)))) {
		if (obj->ds.shm_perm.key == key &&
		    !(obj->ds.shm_perm.mode & SHM_DEST)) {
			break;
		}
	}
	if (&obj->chain == &kds_list) {
		return -EINVAL;
	}

	memobj_ref(&obj->memobj);
	*objp = obj;
	return 0;
} /* shmobj_list_lookup_by_key() */

int shmobj_list_lookup_by_index(int index, struct shmobj **objp)
{
	struct shmobj *obj;

	for (obj = ((typeof(*obj) *)((char *)((&kds_list)->next) - offsetof(typeof(*obj), chain))); &obj->chain != (&kds_list); obj = ((typeof(*obj) *)((char *)(obj->chain.next) - offsetof(typeof(*obj), chain)))) {
		if (obj->index == index) {
			break;
		}
	}
	if (&obj->chain == &kds_list) {
		return -EINVAL;
	}

	memobj_ref(&obj->memobj);
	*objp = obj;
	return 0;
} /* shmobj_list_lookup_by_index() */

int do_shmget(const key_t key, const size_t size, const int shmflg)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process *proc = thread->proc;
	time_t now = time();
	int shmid;
	int error;
	struct shmid_ds ads;
	struct shmobj *obj;
	int pgshift;

	dkprintf("do_shmget(%#lx,%#lx,%#x)\n", key, size, shmflg);

	if (size < the_shminfo.shmmin) {
		dkprintf("do_shmget(%#lx,%#lx,%#x): -EINVAL\n", key, size, shmflg);
		return -EINVAL;
	}

	shmobj_list_lock();
	obj = NULL;
	if (key != IPC_PRIVATE) {
		error = shmobj_list_lookup_by_key(key, &obj);
		if (error == -EINVAL) {
			obj = NULL;
		}
		else if (error) {
			shmobj_list_unlock();
			dkprintf("do_shmget(%#lx,%#lx,%#x): lookup: %d\n", key, size, shmflg, error);
			return error;
		}
		if (!obj && !(shmflg & IPC_CREAT)) {
			shmobj_list_unlock();
			dkprintf("do_shmget(%#lx,%#lx,%#x): -ENOENT\n", key, size, shmflg);
			return -ENOENT;
		}
		if (obj && (shmflg & IPC_CREAT) && (shmflg & IPC_EXCL)) {
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("do_shmget(%#lx,%#lx,%#x): -EEXIST\n", key, size, shmflg);
			return -EEXIST;
		}
	}

	if (obj) {
		error = shmget_existing_access_result(proc->euid, proc->egid,
				shmflg, obj->ds.shm_perm.uid,
				obj->ds.shm_perm.cuid, obj->ds.shm_perm.gid,
				obj->ds.shm_perm.cgid, obj->ds.shm_perm.mode);
		if (error) {
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("do_shmget(%#lx,%#lx,%#x): -EINVAL\n",
				 key, size, shmflg);
			return error;
		}
		if (obj->ds.shm_segsz < size) {
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("do_shmget(%#lx,%#lx,%#x): -EINVAL\n", key, size, shmflg);
			return -EINVAL;
		}
		shmid = make_shmid(obj);
		shmobj_list_unlock();
		memobj_unref(&obj->memobj);
		dkprintf("do_shmget(%#lx,%#lx,%#x): %d\n", key, size, shmflg, shmid);
		return shmid;
	}

	if (the_shm_info.used_ids >= the_shminfo.shmmni) {
		shmobj_list_unlock();
		dkprintf("do_shmget(%#lx,%#lx,%#x): -ENOSPC\n", key, size, shmflg);
		return -ENOSPC;
	}

	if (shmflg & SHM_HUGETLB) {
		pgshift = (shmflg >> SHM_HUGE_SHIFT) & 0x3F;
		if (!pgshift) {
			pgshift = ihk_mc_get_linux_default_huge_page_shift();
		}
	} else if (proc->thp_disable) {
		pgshift = PAGE_SHIFT;
	} else {
		/* transparent huge page */
		size_t pgsize;
		int p2align;

		if (size > PAGE_SIZE) {
			error = arch_get_smaller_page_size(NULL, size + 1,
							   &pgsize, &p2align);
			if (error) {
				ekprintf("%s: WARNING: arch_get_smaller_page_size failed. size: %ld, error: %d\n",
					 __func__, size, error);
				pgshift = PAGE_SHIFT;
			} else {
				pgshift = p2align + PAGE_SHIFT;
			}
		} else {
			pgshift = PAGE_SHIFT;
		}
	}

	memset(&ads, 0, sizeof(ads));
	ads.shm_perm.key = key;
	ads.shm_perm.uid = proc->euid;
	ads.shm_perm.cuid = proc->euid;
	ads.shm_perm.gid = proc->egid;
	ads.shm_perm.cgid = proc->egid;
	ads.shm_perm.mode = shmflg & 0777;
	ads.shm_segsz = size;
	ads.shm_ctime = now;
	ads.shm_cpid = proc->pid;
	ads.init_pgshift = pgshift;

	error = shmobj_create_indexed(&ads, &obj);
	if (error) {
		shmobj_list_unlock();
		dkprintf("do_shmget(%#lx,%#lx,%#x): shmobj_create: %d\n", key, size, shmflg, error);
		return error;
	}

	obj->index = get_shmid_index();

	list_add(&obj->chain, &kds_list);
	++the_shm_info.used_ids;

	shmid = make_shmid(obj);
	shmobj_list_unlock();

	dkprintf("do_shmget(%#lx,%#lx,%#x): %d\n", key, size, shmflg, shmid);
	return shmid;
} /* do_shmget()() */

static void
shmat_shmobj_list_lock_bridge(void)
{
	shmobj_list_lock();
}

static void
shmat_shmobj_list_unlock_bridge(void)
{
	shmobj_list_unlock();
}

static int
shmat_lookup_obj_bridge(int shmid, void **objp)
{
	struct shmobj *obj = NULL;
	int error = shmobj_list_lookup(shmid, &obj);

	if (!error && objp)
		*objp = obj;
	return error;
}

static void
shmat_memobj_unref_bridge(void *memobj)
{
	memobj_unref(memobj);
}

static struct vm_range *
shmat_lookup_range_bridge(struct process_vm *vm, unsigned long start,
		unsigned long end)
{
	return lookup_process_memory_range(vm, start, end);
}

static int
shmat_search_free_bridge(size_t len, int pgshift, unsigned long *addrp)
{
	uintptr_t addr = 0;
	int error = search_free_space(len, pgshift, &addr);

	if (addrp)
		*addrp = addr;
	return error;
}

static int
shmat_add_range_bridge(struct process_vm *vm, unsigned long start,
		unsigned long end, unsigned long phys, unsigned long flags,
		void *memobj, long objoff, int pgshift)
{
	return add_process_memory_range(vm, start, end, phys, flags, memobj,
			objoff, pgshift, NULL, NULL);
}

static void
shmat_log_bridge(int event, int shmid, unsigned long shmaddr, int shmflg,
		long error)
{
	if (event == SHMAT_LOG_ENTER) {
		dkprintf("shmat(%#x,%p,%#x)\n", shmid, (void *)shmaddr,
				shmflg);
	}
	else if (event == SHMAT_LOG_LOOKUP_FAILED) {
		dkprintf("shmat(%#x,%p,%#x): lookup: %ld\n", shmid,
				(void *)shmaddr, shmflg, error);
	}
	else if (event == SHMAT_LOG_INVALID_ADDR) {
		dkprintf("shmat(%#x,%p,%#x): -EINVAL\n", shmid,
				(void *)shmaddr, shmflg);
	}
	else if (event == SHMAT_LOG_ACCESS_FAILED) {
		dkprintf("shmat(%#x,%p,%#x): access: %ld\n", shmid,
				(void *)shmaddr, shmflg, error);
	}
	else if (event == SHMAT_LOG_RANGE_BUSY) {
		dkprintf("shmat(%#x,%p,%#x):lookup_process_memory_range "
				"succeeded. %ld\n", shmid, (void *)shmaddr,
				shmflg, error);
	}
	else if (event == SHMAT_LOG_SEARCH_FAILED) {
		dkprintf("shmat(%#x,%p,%#x):search_free_space failed. %ld\n",
				shmid, (void *)shmaddr, shmflg, error);
	}
	else if (event == SHMAT_LOG_SET_HOST_FAILED) {
		dkprintf("shmat(%#x,%p,%#x):set_host_vma failed. %ld\n",
				shmid, (void *)shmaddr, shmflg, error);
	}
	else if (event == SHMAT_LOG_ADD_FAILED) {
		dkprintf("shmat(%#x,%p,%#x):add_process_memory_range "
				"failed. %ld\n", shmid, (void *)shmaddr,
				shmflg, error);
	}
	else if (event == SHMAT_LOG_EXIT) {
		dkprintf("shmat(%#x,%p,%#x): 0x%lx. %ld\n", shmid,
				(void *)shmaddr, shmflg, error, error);
	}
}

long sys_shmat(int n, ihk_mc_user_context_t *ctx)
{
	const int shmid = ihk_mc_syscall_arg0(ctx);
	void * const shmaddr = (void *)ihk_mc_syscall_arg1(ctx);
	const int shmflg = ihk_mc_syscall_arg2(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process *proc = thread->proc;
	struct process_vm *vm = thread->vm;

	return shmat_body_result(shmid, (unsigned long)shmaddr, shmflg,
			proc->euid, proc->egid, vm, &vm->memory_range_lock,
			offsetof(struct shmobj, pgshift),
			offsetof(struct shmobj, real_segsz),
			offsetof(struct shmobj, memobj),
			offsetof(struct shmobj, ds.shm_perm.uid),
			offsetof(struct shmobj, ds.shm_perm.cuid),
			offsetof(struct shmobj, ds.shm_perm.gid),
			offsetof(struct shmobj, ds.shm_perm.cgid),
			offsetof(struct shmobj, ds.shm_perm.mode),
			shmat_shmobj_list_lock_bridge,
			shmat_shmobj_list_unlock_bridge,
			shmat_lookup_obj_bridge, shmat_memobj_unref_bridge,
			munmap_write_lock_bridge, munmap_write_unlock_bridge,
			shmat_lookup_range_bridge, shmat_search_free_bridge,
			mprotect_set_host_vma_bridge, shmat_add_range_bridge,
			shmat_log_bridge);
} /* sys_shmat() */

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
static const struct shmctl_offsets shmctl_syscall_offsets = {
	.obj_memobj_offset = offsetof(struct shmobj, memobj),
	.obj_pgshift_offset = offsetof(struct shmobj, pgshift),
	.obj_real_segsz_offset = offsetof(struct shmobj, real_segsz),
	.obj_user_offset = offsetof(struct shmobj, user),
	.obj_ds_offset = offsetof(struct shmobj, ds),
	.obj_uid_offset = offsetof(struct shmobj, ds.shm_perm.uid),
	.obj_cuid_offset = offsetof(struct shmobj, ds.shm_perm.cuid),
	.obj_gid_offset = offsetof(struct shmobj, ds.shm_perm.gid),
	.obj_cgid_offset = offsetof(struct shmobj, ds.shm_perm.cgid),
	.obj_mode_offset = offsetof(struct shmobj, ds.shm_perm.mode),
	.obj_ctime_offset = offsetof(struct shmobj, ds.shm_ctime),
	.obj_nattch_offset = offsetof(struct shmobj, ds.shm_nattch),
	.shmlock_user_locked_offset = offsetof(struct shmlock_user, locked),
	.shmid_ds_size = sizeof(struct shmid_ds),
	.shminfo_size = sizeof(struct shminfo),
	.shm_info_size = sizeof(struct shm_info),
};

static int
shmctl_lookup_by_index_bridge(int index, void **objp)
{
	struct shmobj *obj = NULL;
	int error = shmobj_list_lookup_by_index(index, &obj);

	if (!error && objp)
		*objp = obj;
	return error;
}

static void
shmctl_memobj_unref_bridge(void *memobj)
{
	memobj_unref(memobj);
}

static void
shmctl_shmlock_users_lock_bridge(void)
{
	shmlock_users_lock();
}

static void
shmctl_shmlock_users_unlock_bridge(void)
{
	shmlock_users_unlock();
}

static int
shmctl_shmlock_user_get_bridge(uid_t ruid, void **userp)
{
	struct shmlock_user *user = NULL;
	int error = shmlock_user_get(ruid, &user);

	if (!error && userp)
		*userp = user;
	return error;
}

static void
shmctl_shmlock_user_free_bridge(void *user)
{
	shmlock_user_free(user);
}

static int
shmctl_memobj_refcnt_read_bridge(void *memobj)
{
	return ihk_atomic_read(&((struct memobj *)memobj)->refcnt);
}

static void
shmctl_log_bridge(int event, int shmid, int cmd, unsigned long buf_addr,
		long error)
{
	void *buf = (void *)buf_addr;

	if (event == SHMCTL_LOG_ENTER) {
		dkprintf("shmctl(%#x,%d,%p)\n", shmid, cmd, buf);
	}
	else if (event == SHMCTL_LOG_LOOKUP) {
		dkprintf("shmctl(%#x,%d,%p): lookup: %ld\n", shmid, cmd,
			 buf, error);
	}
	else if (event == SHMCTL_LOG_EPERM) {
		dkprintf("shmctl(%#x,%d,%p): -EPERM\n", shmid, cmd, buf);
	}
	else if (event == SHMCTL_LOG_COPY) {
		dkprintf("shmctl(%#x,%d,%p): %ld\n", shmid, cmd, buf,
			 error);
	}
	else if (event == SHMCTL_LOG_EXIT) {
		dkprintf("shmctl(%#x,%d,%p): %ld\n", shmid, cmd, buf,
			 error);
	}
	else if (event == SHMCTL_LOG_EACCES) {
		dkprintf("shmctl(%#x,%d,%p): -EACCES\n", shmid, cmd, buf);
	}
	else if (event == SHMCTL_LOG_PERM_SHM) {
		dkprintf("shmctl(%#x,%d,%p): perm shm: %ld\n", shmid, cmd,
			 buf, error);
	}
	else if (event == SHMCTL_LOG_PERM_PROC) {
		dkprintf("shmctl(%#x,%d,%p): perm proc: %ld\n", shmid, cmd,
			 buf, error);
	}
	else if (event == SHMCTL_LOG_USER_LOOKUP) {
		ekprintf("shmctl(%#x,%d,%p): user lookup: %ld\n", shmid,
			 cmd, buf, error);
	}
	else if (event == SHMCTL_LOG_TOO_LARGE) {
		dkprintf("shmctl(%#x,%d,%p): too large: %ld\n", shmid,
			 cmd, buf, error);
	}
	else if (event == SHMCTL_LOG_EINVAL) {
		dkprintf("shmctl(%#x,%d,%p): EINVAL\n", shmid, cmd, buf);
	}
}
#endif /* MCKERNEL_RUST_SYSCALL_POLICY_HELPERS */

long sys_shmctl(int n, ihk_mc_user_context_t *ctx)
{
	const int shmid = ihk_mc_syscall_arg0(ctx);
	const int cmd = ihk_mc_syscall_arg1(ctx);
	struct shmid_ds * const buf = (void *)ihk_mc_syscall_arg2(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process *proc = thread->proc;
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct rlimit *rlim = &proc->rlimit[MCK_RLIMIT_MEMLOCK];

	return shmctl_body_result(shmid, cmd, (unsigned long)buf,
			proc->euid, proc->egid, proc->ruid, rlim->rlim_cur,
			time(), has_cap_sys_admin(thread),
			has_cap_ipc_lock(thread), &shmctl_syscall_offsets,
			&the_shminfo, &the_shm_info,
			shmat_shmobj_list_lock_bridge,
			shmat_shmobj_list_unlock_bridge,
			shmat_lookup_obj_bridge,
			shmctl_lookup_by_index_bridge,
			shmctl_memobj_unref_bridge,
			syscall_copy_from_user_bridge,
			syscall_copy_to_user_bridge,
			get_shmid_max_index,
			shmctl_shmlock_users_lock_bridge,
			shmctl_shmlock_users_unlock_bridge,
			shmctl_shmlock_user_get_bridge,
			shmctl_shmlock_user_free_bridge,
			shmctl_memobj_refcnt_read_bridge,
			shmctl_log_bridge);
#else
	int error;
	struct shmid_ds ads;
	time_t now = time();
	int maxi;
	struct shmobj *obj;
	struct rlimit *rlim;
	size_t size;
	struct shmlock_user *user;
	uid_t ruid = proc->ruid;
	uint16_t oldmode;

	dkprintf("shmctl(%#x,%d,%p)\n", shmid, cmd, buf);
	switch (cmd) {
	case IPC_RMID:
		shmobj_list_lock();
		error = shmobj_list_lookup(shmid, &obj);
		if (error) {
			shmobj_list_unlock();
			dkprintf("shmctl(%#x,%d,%p): lookup: %d\n", shmid, cmd, buf, error);
			return error;
		}
		error = shm_owner_or_cap_result(has_cap_sys_admin(thread),
				proc->euid, obj->ds.shm_perm.uid,
				obj->ds.shm_perm.cuid);
		if (error) {
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("shmctl(%#x,%d,%p): -EPERM\n", shmid, cmd, buf);
			return error;
		}
		oldmode = obj->ds.shm_perm.mode;
		obj->ds.shm_perm.mode |= SHM_DEST;
		shmobj_list_unlock();
		// unref twice if this is the first time rmid is called
		if (!(oldmode & SHM_DEST))
			memobj_unref(&obj->memobj);
		memobj_unref(&obj->memobj);

		dkprintf("shmctl(%#x,%d,%p): 0\n", shmid, cmd, buf);
		return 0;
	case IPC_SET:
		shmobj_list_lock();
		error = shmobj_list_lookup(shmid, &obj);
		if (error) {
			shmobj_list_unlock();
			dkprintf("shmctl(%#x,%d,%p): lookup: %d\n", shmid, cmd, buf, error);
			return error;
		}
		error = shm_owner_result(proc->euid, obj->ds.shm_perm.uid,
				obj->ds.shm_perm.cuid);
		if (error) {
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("shmctl(%#x,%d,%p): -EPERM\n", shmid, cmd, buf);
			return error;
		}
		error = copy_from_user(&ads, buf, sizeof(ads));
		if (error) {
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("shmctl(%#x,%d,%p): %d\n", shmid, cmd, buf, error);
			return error;
		}
		obj->ds.shm_perm.uid = ads.shm_perm.uid;
		obj->ds.shm_perm.gid = ads.shm_perm.gid;
		obj->ds.shm_perm.mode &= ~0777;
		obj->ds.shm_perm.mode |= ads.shm_perm.mode & 0777;
		obj->ds.shm_ctime = now;

		shmobj_list_unlock();
		memobj_unref(&obj->memobj);
		dkprintf("shmctl(%#x,%d,%p): 0\n", shmid, cmd, buf);
		return 0;
	case IPC_STAT:
	case SHM_STAT:
		shmobj_list_lock();
		if (cmd == IPC_STAT) {
			error = shmobj_list_lookup(shmid, &obj);
		} else { // SHM_STAT
			error = shmobj_list_lookup_by_index(shmid, &obj);
		}
		if (error) {
			shmobj_list_unlock();
			dkprintf("shmctl(%#x,%d,%p): lookup: %d\n", shmid, cmd, buf, error);
			return error;
		}

		if (cmd == IPC_STAT) {
			error = shmctl_ipc_stat_access_result(proc->euid,
					proc->egid, obj->ds.shm_perm.uid,
					obj->ds.shm_perm.cuid,
					obj->ds.shm_perm.gid,
					obj->ds.shm_perm.cgid,
					obj->ds.shm_perm.mode);
			if (error) {
				shmobj_list_unlock();
				memobj_unref(&obj->memobj);
				dkprintf("shmctl(%#x,%d,%p): -EACCES\n", shmid,
					 cmd, buf);
				return error;
			}
		}

		/* This could potentially be higher than required if some other
		 * thread holds a ref at this point.
		 * Minus one here is because we hold a ref...
		 */
		obj->ds.shm_nattch = ihk_atomic_read(&obj->memobj.refcnt) - 1;
		/* ... And one for sentinel unless RMID has been called */
		if (!(obj->ds.shm_perm.mode & SHM_DEST)) {
			obj->ds.shm_nattch--;
		}

		error = copy_to_user(buf, &obj->ds, sizeof(*buf));
		if (error) {
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("shmctl(%#x,%d,%p): %d\n", shmid, cmd, buf, error);
			return error;
		}
		shmobj_list_unlock();
		memobj_unref(&obj->memobj);
		dkprintf("shmctl(%#x,%d,%p): 0\n", shmid, cmd, buf);
		return 0;
	case IPC_INFO:
		shmobj_list_lock();
		error = shmobj_list_lookup(shmid, &obj);
		if (error) {
			shmobj_list_unlock();
			dkprintf("shmctl(%#x,%d,%p): lookup: %d\n", shmid, cmd, buf, error);
			return error;
		}
		error = copy_to_user(buf, &the_shminfo, sizeof(the_shminfo));
		if (error) {
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("shmctl(%#x,%d,%p): %d\n", shmid, cmd, buf, error);
			return error;
		}

		maxi = get_shmid_max_index();
		if (maxi < 0) {
			maxi = 0;
		}
		shmobj_list_unlock();
		memobj_unref(&obj->memobj);
		dkprintf("shmctl(%#x,%d,%p): %d\n", shmid, cmd, buf, maxi);
		return maxi;
	case SHM_LOCK:
		shmobj_list_lock();
		error = shmobj_list_lookup(shmid, &obj);
		if (error) {
			shmobj_list_unlock();
			dkprintf("shmctl(%#x,%d,%p): lookup: %d\n", shmid, cmd, buf, error);
			return error;
		}
		error = shm_owner_or_cap_result(has_cap_ipc_lock(thread),
				proc->euid, obj->ds.shm_perm.uid,
				obj->ds.shm_perm.cuid);
		if (error) {
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("shmctl(%#x,%d,%p): perm shm: %d\n", shmid, cmd, buf, error);
			return error;
		}
		rlim = &proc->rlimit[MCK_RLIMIT_MEMLOCK];
		error = shmlock_rlimit_result(has_cap_ipc_lock(thread),
				rlim->rlim_cur, 0, 0);
		if (error) {
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("shmctl(%#x,%d,%p): perm proc: %d\n", shmid, cmd, buf, error);
			return error;
		}
		if (!(obj->ds.shm_perm.mode & SHM_LOCKED)
				&& ((obj->pgshift == 0)
					|| (obj->pgshift == PAGE_SHIFT))) {
			shmlock_users_lock();
			error = shmlock_user_get(ruid, &user);
			if (error) {
				shmlock_users_unlock();
				memobj_unref(&obj->memobj);
				shmobj_list_unlock();
				ekprintf("shmctl(%#x,%d,%p): user lookup: %d\n", shmid, cmd, buf, error);
				return -ENOMEM;
			}
			size = obj->real_segsz;
			error = shmlock_rlimit_result(has_cap_ipc_lock(thread),
					rlim->rlim_cur, user->locked, size);
			if (error) {
				shmlock_users_unlock();
				memobj_unref(&obj->memobj);
				shmobj_list_unlock();
				dkprintf("shmctl(%#x,%d,%p): too large: %d\n", shmid, cmd, buf, error);
				return error;
			}
			obj->ds.shm_perm.mode |= SHM_LOCKED;
			obj->user = user;
			user->locked += size;
			shmlock_users_unlock();
		}
		shmobj_list_unlock();
		memobj_unref(&obj->memobj);

		dkprintf("shmctl(%#x,%d,%p): 0\n", shmid, cmd, buf);
		return 0;
	case SHM_UNLOCK:
		shmobj_list_lock();
		error = shmobj_list_lookup(shmid, &obj);
		if (error) {
			shmobj_list_unlock();
			dkprintf("shmctl(%#x,%d,%p): lookup: %d\n", shmid, cmd, buf, error);
			return error;
		}
		error = shm_owner_or_cap_result(has_cap_ipc_lock(thread),
				proc->euid, obj->ds.shm_perm.uid,
				obj->ds.shm_perm.cuid);
		if (error) {
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("shmctl(%#x,%d,%p): perm shm: %d\n", shmid, cmd, buf, error);
			return error;
		}
		if ((obj->ds.shm_perm.mode & SHM_LOCKED)
			       && ((obj->pgshift == 0)
				       || (obj->pgshift == PAGE_SHIFT))) {
			size = obj->real_segsz;
			shmlock_users_lock();
			user = obj->user;
			obj->user = NULL;
			user->locked -= size;
			if (!user->locked) {
				shmlock_user_free(user);
			}
			shmlock_users_unlock();
			obj->ds.shm_perm.mode &= ~SHM_LOCKED;
		}
		shmobj_list_unlock();
		memobj_unref(&obj->memobj);
		dkprintf("shmctl(%#x,%d,%p): 0\n", shmid, cmd, buf);
		return 0;
	case SHM_INFO:
		shmobj_list_lock();
		error = copy_to_user(buf, &the_shm_info, sizeof(the_shm_info));
		if (error) {
			shmobj_list_unlock();
			dkprintf("shmctl(%#x,%d,%p): %d\n", shmid, cmd, buf, error);
			return error;
		}

		maxi = get_shmid_max_index();
		if (maxi < 0) {
			maxi = 0;
		}
		shmobj_list_unlock();
		dkprintf("shmctl(%#x,%d,%p): %d\n", shmid, cmd, buf, maxi);
		return maxi;
	default:
		dkprintf("shmctl(%#x,%d,%p): EINVAL\n", shmid, cmd, buf);
		return -EINVAL;
	}
#endif
} /* sys_shmctl() */

static struct vm_range *
shmdt_lookup_range_bridge(struct process_vm *vm, unsigned long start,
		unsigned long end)
{
	return lookup_process_memory_range(vm, start, end);
}

static void
shmdt_log_bridge(int event, unsigned long addr, int error)
{
	if (event == SHMDT_LOG_ENTER) {
		dkprintf("shmdt(%p)\n", (void *)addr);
	}
	else if (event == SHMDT_LOG_INVALID) {
		dkprintf("shmdt(%p): -EINVAL\n", (void *)addr);
	}
	else if (event == SHMDT_LOG_EXIT) {
		dkprintf("shmdt(%p): %d\n", (void *)addr, error);
	}
}

long sys_shmdt(int n, ihk_mc_user_context_t *ctx)
{
	void * const shmaddr = (void *)ihk_mc_syscall_arg0(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process_vm *vm = thread->vm;

	return shmdt_body_result(vm, &vm->memory_range_lock,
			(unsigned long)shmaddr,
			offsetof(struct vm_range, start),
			offsetof(struct vm_range, end),
			offsetof(struct vm_range, memobj),
			offsetof(struct memobj, flags), MF_SHMDT_OK,
			munmap_write_lock_bridge, munmap_write_unlock_bridge,
			shmdt_lookup_range_bridge, munmap_do_bridge,
			shmdt_log_bridge);
} /* sys_shmdt() */

static const char *do_futex_op_name(int op)
{
	return (op == FUTEX_WAIT) ? "FUTEX_WAIT" :
		(op == FUTEX_WAIT_BITSET) ? "FUTEX_WAIT_BITSET" :
		(op == FUTEX_WAKE) ? "FUTEX_WAKE" :
		(op == FUTEX_WAKE_OP) ? "FUTEX_WAKE_OP" :
		(op == FUTEX_WAKE_BITSET) ? "FUTEX_WAKE_BITSET" :
		(op == FUTEX_CMP_REQUEUE) ? "FUTEX_CMP_REQUEUE" :
		(op == FUTEX_REQUEUE) ? "FUTEX_REQUEUE (NOT IMPL!)" :
		"unknown";
}

static int do_futex_syscall_time_bridge(int syscall_nr, int clock_id,
		struct timespec *ats)
{
	struct syscall_request request IHK_DMA_ALIGN;
	struct timespec tv[2];
	struct timespec *tv_now = tv;
	int r;

	if ((((unsigned long)tv) ^ ((unsigned long)(tv + 1))) & PAGE_MASK)
		tv_now = tv + 1;

	request.number = syscall_nr;
	request.args[0] = virt_to_phys(tv_now);
	request.args[1] = clock_id;

	r = do_syscall(&request, ihk_mc_get_processor_id());
	if (r < 0)
		return -EFAULT;

	ats->tv_sec = tv_now->tv_sec;
	ats->tv_nsec = tv_now->tv_nsec;
	return 0;
}

static void do_futex_local_time_bridge(struct timespec *ats)
{
	calculate_time_from_tsc(ats);
}

static int do_futex_linux_time_bridge(int clock_id, struct timespec *ats)
{
	if (!linux_clock_gettime)
		return -EFAULT;
	return linux_clock_gettime(clock_id, ats);
}

static unsigned long do_futex_ns_per_tsc_bridge(void)
{
	return ihk_mc_get_ns_per_tsc();
}

static int do_futex_dispatch_bridge(unsigned long uaddr, int op, uint32_t val,
		uint64_t timeout, unsigned long uaddr2, uint32_t val2,
		uint32_t val3, int fshared)
{
	return futex((uint32_t *)uaddr, op, val, timeout, (uint32_t *)uaddr2,
			val2, val3, fshared);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
int futex_atomic_access_ok_bridge(int *uaddr, unsigned long size)
{
#ifdef __UACCESS__
	return access_ok(VERIFY_WRITE, uaddr, size);
#else
	(void)uaddr;
	(void)size;
	return 1;
#endif
}

int futex_atomic_cmpxchg_inatomic_bridge(int *uaddr, int oldval, int newval)
{
	asm volatile("1:\tlock; cmpxchgl %3, %1\n"
		     "2:\t.section .fixup, \"ax\"\n"
		     "3:\tmov     %2, %0\n"
		     "\tjmp     2b\n"
		     "\t.previous\n"
		     " .section __ex_table,\"a\"\n"
		     " .balign 8\n"
		     " .quad 1b,3b\n"
		     " .previous\n"
		     : "=a" (oldval), "+m" (*uaddr)
		     : "i" (-EFAULT), "r" (newval), "0" (oldval)
		     : "memory");

	return oldval;
}

#define FUTEX_X86_ATOMIC_OP1(insn, ret, oldval, uaddr, oparg)	\
	asm volatile("1:\t" insn "\n"				\
		     "2:\t.section .fixup,\"ax\"\n"		\
		     "3:\tmov\t%3, %1\n"			\
		     "\tjmp\t2b\n"				\
		     "\t.previous\n"				\
		     " .section __ex_table,\"a\"\n"		\
		     " .balign 8\n"				\
		     " .quad 1b,3b\n"				\
		     " .previous\n"				\
		     : "=r" (oldval), "=r" (ret), "+m" (*uaddr)	\
		     : "i" (-EFAULT), "0" (oparg), "1" (0))

#define FUTEX_X86_ATOMIC_OP2(insn, ret, oldval, uaddr, oparg)	\
	asm volatile("1:\tmovl	%2, %0\n"			\
		     "\tmovl\t%0, %3\n"				\
		     "\t" insn "\n"				\
		     "2:\tlock; cmpxchgl %3, %2\n"		\
		     "\tjnz\t1b\n"				\
		     "3:\t.section .fixup,\"ax\"\n"		\
		     "4:\tmov\t%5, %1\n"			\
		     "\tjmp\t3b\n"				\
		     "\t.previous\n"				\
		     " .section __ex_table,\"a\"\n"		\
		     " .balign 8\n"				\
		     " .quad 1b,4b\n"				\
		     " .previous\n"				\
		     " .section __ex_table,\"a\"\n"		\
		     " .balign 8\n"				\
		     " .quad 2b,4b\n"				\
		     " .previous\n"				\
		     : "=&a" (oldval), "=&r" (ret),		\
		       "+m" (*uaddr), "=&r" (tem)		\
		     : "r" (oparg), "i" (-EFAULT), "1" (0))

int futex_atomic_op_inuser_bridge(int op, int *uaddr, int oparg, int *oldval)
{
	int old = 0, ret, tem;

	switch (op) {
	case FUTEX_OP_SET:
		FUTEX_X86_ATOMIC_OP1("xchgl %0, %2", ret, old,
				     uaddr, oparg);
		break;
	case FUTEX_OP_ADD:
		FUTEX_X86_ATOMIC_OP1("lock; xaddl %0, %2", ret, old,
				     uaddr, oparg);
		break;
	case FUTEX_OP_OR:
		FUTEX_X86_ATOMIC_OP2("orl %4, %3", ret, old, uaddr,
				     oparg);
		break;
	case FUTEX_OP_ANDN:
		FUTEX_X86_ATOMIC_OP2("andl %4, %3", ret, old, uaddr,
				     oparg);
		break;
	case FUTEX_OP_XOR:
		FUTEX_X86_ATOMIC_OP2("xorl %4, %3", ret, old, uaddr,
				     oparg);
		break;
	default:
		ret = -ENOSYS;
	}

	if (!ret)
		*oldval = old;

	return ret;
}
#endif

static void do_futex_log_bridge(const struct do_futex_log_record *record)
{
	if (record->event == DO_FUTEX_LOG_ENTER) {
		dkprintf("futex op=[%x, %s],uaddr=%lx, val=%x, utime=%lx, uaddr2=%lx, val3=%x, []=%x, shared: %d\n",
				record->flags, do_futex_op_name(record->op),
				record->uaddr, record->val, record->utime,
				record->uaddr2, record->val3,
				*(uint32_t *)record->uaddr, record->fshared);
	}
	else if (record->event == DO_FUTEX_LOG_TIMEOUT) {
		dkprintf("%s: utime=%ld.%09ld\n", __func__, record->sec,
				record->nsec);
	}
	else if (record->event == DO_FUTEX_LOG_ABSOLUTE_TIME) {
		dkprintf("%s: ats=%ld.%09ld\n", __func__, record->sec,
				record->nsec);
	}
	else if (record->event == DO_FUTEX_LOG_EXIT) {
		dkprintf("futex op=[%x, %s],uaddr=%lx, val=%x, utime=%lx, uaddr2=%lx, val3=%x, []=%x, shared: %d, ret: %d\n",
				record->op, do_futex_op_name(record->op),
				record->uaddr, record->val, record->utime,
				record->uaddr2, record->val3,
				*(uint32_t *)record->uaddr, record->fshared,
				record->ret);
	}
}

long do_futex(int n, unsigned long arg0, unsigned long arg1,
			  unsigned long arg2, unsigned long arg3,
			  unsigned long arg4, unsigned long arg5,
			  unsigned long _uti_clv,
			  void *uti_futex_resp,
			  void *_linux_wait_event,
			  void *_linux_printk,
			  void *_linux_clock_gettime)
{
	struct cpu_local_var *uti_clv = (struct cpu_local_var *)_uti_clv;

	/* TODO: replace these with passing via struct smp_boot_param */
	if (_linux_printk && !linux_printk) {
		linux_printk = (int (*)(const char *fmt, ...))_linux_printk;
	}
	if (_linux_wait_event && !linux_wait_event) {
		linux_wait_event = (long (*)(void *_resp, unsigned long nsec_timeout))_linux_wait_event;
	}
	if (_linux_clock_gettime && !linux_clock_gettime) {
		linux_clock_gettime = (int (*)(clockid_t clk_id, struct timespec *tp))_linux_clock_gettime;
	}

	/* Fill in clv */
	if (uti_clv) {
		uti_clv->uti_futex_resp = uti_futex_resp;
	}

	/* monitor is per-cpu object */
	if (!uti_clv) {
		struct ihk_os_cpu_monitor *monitor = get_this_cpu_local_var()->monitor;
		monitor->status = IHK_OS_MONITOR_KERNEL_HEAVY;
	}

	return do_futex_body_result(n, arg0, arg1, arg2, arg3, arg4, arg5,
			uti_clv != NULL, gettime_local_support,
			do_futex_syscall_time_bridge, do_futex_local_time_bridge,
			do_futex_linux_time_bridge, do_futex_ns_per_tsc_bridge,
			do_futex_dispatch_bridge, do_futex_log_bridge);
}

long sys_futex(int n, ihk_mc_user_context_t *ctx)
{
	return do_futex(n, ihk_mc_syscall_arg0(ctx), ihk_mc_syscall_arg1(ctx),
					ihk_mc_syscall_arg2(ctx), ihk_mc_syscall_arg3(ctx),
					ihk_mc_syscall_arg4(ctx), ihk_mc_syscall_arg5(ctx),
					0UL, NULL, NULL, NULL, NULL);
}

static void
do_exit(int code)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	struct thread *child;
	struct process *proc = thread->proc;
	struct mcs_rwlock_node_irqsave lock;
	int nproc;
	int exit_status = exit_code_status_result(code);
	int sig = exit_code_signal_result(code);
	struct timespec ats;

	dkprintf("sys_exit,pid=%d\n", proc->pid);

	/* XXX: for if all threads issued the exit(2) rather than exit_group(2),
	 *      exit(2) also should delegate.
	 */
	/* If there is a clear_child_tid address set, clear it and wake it.
	 * This unblocks any pthread_join() waiters. */
	if (thread->clear_child_tid) {
		
		dkprintf("exit clear_child!\n");

		setint_user((int*)thread->clear_child_tid, 0);
		barrier();
		futex((uint32_t *)thread->clear_child_tid,
		      FUTEX_WAKE, 1, 0, NULL, 0, 0, 1);
		thread->clear_child_tid = NULL;
	}

	mcs_rwlock_reader_lock(&proc->threads_lock, &lock);
	nproc = 0;
	for (child = ((typeof(*child) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*child), siblings_list))); &child->siblings_list != (&proc->threads_list); child = ((typeof(*child) *)((char *)(child->siblings_list.next) - offsetof(typeof(*child), siblings_list)))) {
		if (terminate_thread_active_result(child->status))
			nproc++;
	}

	if (nproc == 1) { // process has only one thread
		mcs_rwlock_reader_unlock(&proc->threads_lock, &lock);
		terminate(exit_status, sig);
		return;
	}

#ifdef DCFA_KMOD
	do_mod_exit((int)ihk_mc_syscall_arg0(ctx));
#endif

	if (terminate_process_exited_result(proc->status)) {
		mcs_rwlock_writer_unlock(&proc->threads_lock, &lock);
		terminate(exit_status, 0);
		return;
	}
	preempt_disable();
	thread->exit_status = code;
	thread->status = PS_EXITED;
	tsc_to_ts(thread->user_tsc, &ats);
	ts_add(&proc->utime, &ats);
	tsc_to_ts(thread->system_tsc, &ats);
	ts_add(&proc->stime, &ats);
	thread->user_tsc = 0;
	thread->system_tsc = 0;
	thread_exit_signal(thread);
	sync_child_event(thread->proc->monitoring_event);
	mcs_rwlock_writer_unlock(&proc->threads_lock, &lock);
	release_thread(thread);
	preempt_enable();

	schedule();

	return;
}

void
exit_do_exit_bridge(int code)
{
	do_exit(code);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_exit(int n, ihk_mc_user_context_t *ctx);
#else
long sys_exit(int n, ihk_mc_user_context_t *ctx)
{
	return exit_body_result((int)ihk_mc_syscall_arg0(ctx),
			exit_do_exit_bridge);
}
#endif

#if !defined(MCKERNEL_RUST_RLIMIT_HELPERS) || \
	defined(MCKERNEL_RLIMIT_HELPERS_TEST_EXPORT)
static int rlimits[] = {
#ifdef RLIMIT_AS
	RLIMIT_AS,	MCK_RLIMIT_AS,
#endif
#ifdef RLIMIT_CORE
	RLIMIT_CORE,	MCK_RLIMIT_CORE,
#endif
#ifdef RLIMIT_CPU
	RLIMIT_CPU,	MCK_RLIMIT_CPU,
#endif
#ifdef RLIMIT_DATA
	RLIMIT_DATA,	MCK_RLIMIT_DATA,
#endif
#ifdef RLIMIT_FSIZE
	RLIMIT_FSIZE,	MCK_RLIMIT_FSIZE,
#endif
#ifdef RLIMIT_LOCKS
	RLIMIT_LOCKS,	MCK_RLIMIT_LOCKS,
#endif
#ifdef RLIMIT_MEMLOCK
	RLIMIT_MEMLOCK,	MCK_RLIMIT_MEMLOCK,
#endif
#ifdef RLIMIT_MSGQUEUE
	RLIMIT_MSGQUEUE,MCK_RLIMIT_MSGQUEUE,
#endif
#ifdef RLIMIT_NICE
	RLIMIT_NICE,	MCK_RLIMIT_NICE,
#endif
#ifdef RLIMIT_NOFILE
	RLIMIT_NOFILE,	MCK_RLIMIT_NOFILE,
#endif
#ifdef RLIMIT_NPROC
	RLIMIT_NPROC,	MCK_RLIMIT_NPROC,
#endif
#ifdef RLIMIT_RSS
	RLIMIT_RSS,	MCK_RLIMIT_RSS,
#endif
#ifdef RLIMIT_RTPRIO
	RLIMIT_RTPRIO,	MCK_RLIMIT_RTPRIO,
#endif
#ifdef RLIMIT_RTTIME
	RLIMIT_RTTIME,	MCK_RLIMIT_RTTIME,
#endif
#ifdef RLIMIT_SIGPENDING
	RLIMIT_SIGPENDING,MCK_RLIMIT_SIGPENDING,
#endif
#ifdef RLIMIT_STACK
	RLIMIT_STACK,	MCK_RLIMIT_STACK,
#endif
};
#endif /* !MCKERNEL_RUST_RLIMIT_HELPERS || MCKERNEL_RLIMIT_HELPERS_TEST_EXPORT */

#if defined(MCKERNEL_RUST_RLIMIT_HELPERS) || \
	defined(MCKERNEL_RLIMIT_HELPERS_TEST_EXPORT)
#define RLIMIT_HELPER_SCOPE
#else
#define RLIMIT_HELPER_SCOPE static
#endif

#ifdef MCKERNEL_RUST_RLIMIT_HELPERS
extern int prlimit_validate_resource(int resource);
extern int prlimit_validate_new_limit(rlim_t rlim_cur, rlim_t rlim_max);
extern int prlimit_linux_update_needed(int resource);
extern int prlimit_to_mckernel_resource(int resource);
#else
RLIMIT_HELPER_SCOPE int prlimit_validate_resource(int resource)
{
	return (resource < 0 || resource >= RLIMIT_NLIMITS) ? -EINVAL : 0;
}

RLIMIT_HELPER_SCOPE int prlimit_validate_new_limit(rlim_t rlim_cur,
		rlim_t rlim_max)
{
	return rlim_cur > rlim_max ? -EINVAL : 0;
}

RLIMIT_HELPER_SCOPE int prlimit_linux_update_needed(int resource)
{
	switch (resource) {
	case RLIMIT_FSIZE:
	case RLIMIT_NOFILE:
	case RLIMIT_LOCKS:
	case RLIMIT_MSGQUEUE:
		return 1;
	default:
		return 0;
	}
}

RLIMIT_HELPER_SCOPE int prlimit_to_mckernel_resource(int resource)
{
	int i;

	for (i = 0; i < sizeof(rlimits) / sizeof(int); i += 2) {
		if (rlimits[i] == resource) {
			return rlimits[i + 1];
		}
	}

	return -1;
}
#endif /* MCKERNEL_RUST_RLIMIT_HELPERS */

#undef RLIMIT_HELPER_SCOPE

static int do_prlimit64(int pid, int resource, struct rlimit *_new_limit,
			struct rlimit *old_limit)
{
	struct rlimit new_limit;
	int mcresource;
	struct process *proc;
	struct resource_set *rset = get_this_cpu_local_var()->resource_set;
	int hash;
	struct process_hash *phash = rset->process_hash;
	struct mcs_rwlock_node exist_lock;
	struct mcs_rwlock_node update_lock;
	unsigned long irqstate;
	int found;
	int ret;
	ihk_mc_user_context_t ctx;

	ret = prlimit_validate_resource(resource);
	if (ret) {
		return ret;
	}

	if (_new_limit) {
		if (copy_from_user(&new_limit, _new_limit,
				   sizeof(struct rlimit))) {
			return -EFAULT;
		}

		ret = prlimit_validate_new_limit(new_limit.rlim_cur,
						 new_limit.rlim_max);
		if (ret) {
			return ret;
		}

		/* update Linux side value as well */
		if (prlimit_linux_update_needed(resource)) {
			ihk_mc_syscall_set_arg0(&ctx, pid);
			ihk_mc_syscall_set_arg1(&ctx, resource);
			ihk_mc_syscall_set_arg2(&ctx, (unsigned long)_new_limit);
			ihk_mc_syscall_set_arg3(&ctx, (unsigned long)old_limit);
			ret = syscall_generic_forwarding(__NR_prlimit64, &ctx);
			if (ret < 0)
				return ret;
		}
	}

	/* translate resource */
	mcresource = prlimit_to_mckernel_resource(resource);
	if (mcresource < 0) {
		ihk_mc_syscall_set_arg0(&ctx, pid);
		ihk_mc_syscall_set_arg1(&ctx, resource);
		ihk_mc_syscall_set_arg2(&ctx, (unsigned long)_new_limit);
		ihk_mc_syscall_set_arg3(&ctx, (unsigned long)old_limit);
		return syscall_generic_forwarding(__NR_prlimit64, &ctx);
	}

	/* find process */
	found = 0;

	if (pid == 0) {
		struct thread *thread = get_this_cpu_local_var()->current;

		pid = thread->proc->pid;
	}

	irqstate = cpu_disable_interrupt_save();
	hash = process_hash(pid);
	mcs_rwlock_reader_lock_noirq(&phash->lock[hash], &exist_lock);

	for (proc = ((typeof(*proc) *)((char *)((&phash->list[hash])->next) - offsetof(typeof(*proc), hash_list))); &proc->hash_list != (&phash->list[hash]); proc = ((typeof(*proc) *)((char *)(proc->hash_list.next) - offsetof(typeof(*proc), hash_list)))) {
		if (proc->pid == pid) {
			found = 1;
			break;
		}
	}

	if (!found) {
		mcs_rwlock_reader_unlock_noirq(&phash->lock[hash], &exist_lock);
		cpu_restore_interrupt(irqstate);
		return -ESRCH;
	}

	if (_new_limit) {
		mcs_rwlock_writer_lock_noirq(&proc->update_lock, &update_lock);
	} else {
		mcs_rwlock_reader_lock_noirq(&proc->update_lock, &update_lock);
	}

	if (old_limit) {
		if (copy_to_user(old_limit, proc->rlimit + mcresource,
				 sizeof(struct rlimit))) {
			ret = -EFAULT;
			goto out;
		}
	}

	if (_new_limit) {
		memcpy(proc->rlimit + mcresource, &new_limit,
		       sizeof(struct rlimit));
	}

	ret = 0;
 out:
	if (_new_limit) {
		mcs_rwlock_writer_unlock_noirq(&proc->update_lock,
					       &update_lock);
	} else {
		mcs_rwlock_reader_unlock_noirq(&proc->update_lock,
					       &update_lock);
	}

	mcs_rwlock_reader_unlock_noirq(&phash->lock[hash], &exist_lock);
	cpu_restore_interrupt(irqstate);

	return ret;
}

long
syscall_do_prlimit64_bridge(int pid, int resource,
		unsigned long new_limit_addr, unsigned long old_limit_addr)
{
	return do_prlimit64(pid, resource, (struct rlimit *)new_limit_addr,
			(struct rlimit *)old_limit_addr);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_setrlimit(int n, ihk_mc_user_context_t *ctx);
#else
long sys_setrlimit(int n, ihk_mc_user_context_t *ctx)
{
	int resource = ihk_mc_syscall_arg0(ctx);
	struct rlimit *new_limit = (struct rlimit *)ihk_mc_syscall_arg1(ctx);

	return syscall_setrlimit_body_result(resource, (unsigned long)new_limit,
			syscall_do_prlimit64_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_getrlimit(int n, ihk_mc_user_context_t *ctx);
#else
long sys_getrlimit(int n, ihk_mc_user_context_t *ctx)
{
	int resource = ihk_mc_syscall_arg0(ctx);
	struct rlimit *old_limit = (struct rlimit *)ihk_mc_syscall_arg1(ctx);

	return syscall_getrlimit_body_result(resource, (unsigned long)old_limit,
			syscall_do_prlimit64_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_prlimit64(int n, ihk_mc_user_context_t *ctx);
#else
long sys_prlimit64(int n, ihk_mc_user_context_t *ctx)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	int resource = ihk_mc_syscall_arg1(ctx);
	struct rlimit *new_limit = (struct rlimit *)ihk_mc_syscall_arg2(ctx);
	struct rlimit *old_limit = (struct rlimit *)ihk_mc_syscall_arg3(ctx);

	return syscall_prlimit64_body_result(pid, resource,
			(unsigned long)new_limit, (unsigned long)old_limit,
			syscall_do_prlimit64_bridge);
}
#endif

static const struct syscall_cputime_offsets syscall_cputime_offsets = {
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_in_kernel_offset = __builtin_offsetof(struct thread, in_kernel),
	.thread_cpu_id_offset = __builtin_offsetof(struct thread, cpu_id),
	.thread_times_update_offset = __builtin_offsetof(struct thread,
							  times_update),
	.thread_user_tsc_offset = __builtin_offsetof(struct thread, user_tsc),
	.thread_system_tsc_offset = __builtin_offsetof(struct thread,
							system_tsc),
	.thread_siblings_list_offset = __builtin_offsetof(struct thread,
							   siblings_list),
	.proc_threads_list_offset = __builtin_offsetof(struct process,
							threads_list),
	.proc_utime_offset = __builtin_offsetof(struct process, utime),
	.proc_stime_offset = __builtin_offsetof(struct process, stime),
	.proc_utime_children_offset = __builtin_offsetof(struct process,
							 utime_children),
	.proc_stime_children_offset = __builtin_offsetof(struct process,
							 stime_children),
	.proc_maxrss_offset = __builtin_offsetof(struct process, maxrss),
	.proc_maxrss_children_offset = __builtin_offsetof(struct process,
							  maxrss_children),
};

void
syscall_threads_reader_lock_bridge(void *proc, void *lock_arg)
{
	mcs_rwlock_reader_lock_noirq(&((struct process *)proc)->threads_lock,
			(struct mcs_rwlock_node *)lock_arg);
}

void
syscall_threads_reader_unlock_bridge(void *proc, void *lock_arg)
{
	mcs_rwlock_reader_unlock_noirq(&((struct process *)proc)->threads_lock,
			(struct mcs_rwlock_node *)lock_arg);
}

void
syscall_interrupt_cpu_bridge(int cpu_id)
{
	ihk_mc_interrupt_cpu(cpu_id, ihk_mc_get_vector(IHK_GV_IKC));
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_getrusage(int n, ihk_mc_user_context_t *ctx);
#else
long sys_getrusage(int n, ihk_mc_user_context_t *ctx)
{
	int who = ihk_mc_syscall_arg0(ctx);
	struct rusage *usage = (struct rusage *)ihk_mc_syscall_arg1(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct mcs_rwlock_node lock;

	return getrusage_body_result(who, (unsigned long)usage, thread,
			tod_data.clocks_per_sec, &syscall_cputime_offsets,
			syscall_threads_reader_lock_bridge,
			syscall_threads_reader_unlock_bridge, &lock,
			syscall_interrupt_cpu_bridge, syscall_cpu_pause_bridge,
			syscall_copy_to_user_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_sysinfo(int n, ihk_mc_user_context_t *ctx);
#else
long sys_sysinfo(int n, ihk_mc_user_context_t *ctx)
{
	struct sysinfo *sysinfo = (struct sysinfo *)ihk_mc_syscall_arg0(ctx);

	return syscall_sysinfo_body_result((unsigned long)sysinfo,
			rusage_get_total_memory(), rusage_get_free_memory(),
			syscall_copy_to_user_bridge);
}
#endif

extern int ptrace_traceme(void);
extern void set_single_step(struct thread *thread);

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
static const struct ptrace_io_offsets ptrace_wakeup_io_offsets = {
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_vm_offset = __builtin_offsetof(struct thread, vm),
	.thread_ptrace_offset = __builtin_offsetof(struct thread, ptrace),
	.thread_ptrace_eventmsg_offset =
		__builtin_offsetof(struct thread, ptrace_eventmsg),
	.thread_ptrace_recvsig_offset =
		__builtin_offsetof(struct thread, ptrace_recvsig),
	.thread_ptrace_sendsig_offset =
		__builtin_offsetof(struct thread, ptrace_sendsig),
	.thread_report_proc_offset =
		__builtin_offsetof(struct thread, report_proc),
	.thread_ptrace_saved_uctx_valid_offset =
		__builtin_offsetof(struct thread, ptrace_saved_uctx_valid),
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.proc_update_lock_offset =
		__builtin_offsetof(struct process, update_lock),
};

static unsigned long
ptrace_wakeup_find_thread_bridge(int tgid, int tid)
{
	return (unsigned long)find_thread(tgid, tid);
}

static void
ptrace_wakeup_thread_unlock_bridge(unsigned long thread_addr)
{
	thread_unlock((struct thread *)thread_addr);
}

static void
ptrace_wakeup_log_bridge(int event, int value, int result)
{
	if (event == PTRACE_CONTROL_LOG_WAKEUP_ENTER) {
		dkprintf("ptrace_wakeup_sig,pid=%d,data=%08x\n",
				value, result);
	}
}

static int
ptrace_wakeup_clear_saved_bridge(unsigned long thread_addr,
		unsigned long offset)
{
	return process_thread_ptrace_saved_context_clear_result(
			(void *)thread_addr, offset);
}

static void
ptrace_wakeup_set_single_step_bridge(unsigned long thread_addr)
{
	set_single_step((struct thread *)thread_addr);
}

static void
ptrace_wakeup_update_lock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_lock((struct mcs_rwlock_lock *)lock_addr,
			(struct mcs_rwlock_node_irqsave *)node);
}

static int
ptrace_wakeup_trace_syscall_bridge(unsigned long thread_addr,
		unsigned long ptrace_offset, int trace_syscall)
{
	return process_thread_ptrace_trace_syscall_update_result(
			(void *)thread_addr, ptrace_offset, trace_syscall);
}

static void
ptrace_wakeup_update_unlock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_unlock((struct mcs_rwlock_lock *)lock_addr,
			(struct mcs_rwlock_node_irqsave *)node);
}

static unsigned long
ptrace_wakeup_pending_take_bridge(unsigned long thread_addr,
		unsigned long sendsig_offset, unsigned long recvsig_offset,
		int source)
{
	return (unsigned long)process_thread_ptrace_pending_signal_take_result(
			(void *)thread_addr, sendsig_offset, recvsig_offset,
			source);
}
#endif

static int ptrace_wakeup_sig(int pid, long request, long data) {
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct thread *thread = get_this_cpu_local_var()->current;
	struct mcs_rwlock_node_irqsave lock;

	return ptrace_wakeup_sig_body_result(pid, request, data,
			(unsigned long)thread,
			__builtin_offsetof(struct sig_pending, info),
			&ptrace_wakeup_io_offsets, &lock,
			ptrace_wakeup_find_thread_bridge,
			ptrace_wakeup_thread_unlock_bridge,
			ptrace_wakeup_log_bridge,
			ptrace_wakeup_clear_saved_bridge,
			ptrace_wakeup_set_single_step_bridge,
			ptrace_wakeup_update_lock_bridge,
			ptrace_wakeup_trace_syscall_bridge,
			ptrace_wakeup_update_unlock_bridge,
			ptrace_wakeup_pending_take_bridge,
			ptrace_detach_kfree_bridge,
			ptrace_detach_do_kill_bridge,
			ptrace_detach_wakeup_bridge);
#else
	dkprintf("ptrace_wakeup_sig,pid=%d,data=%08x\n", pid, data);
	int error = 0;
	struct thread *child;
	struct siginfo info;
	struct mcs_rwlock_node_irqsave lock;
	struct thread *thread = get_this_cpu_local_var()->current;
	int action;
	int source;

	child = find_thread(pid, pid);
	if (!child) {
		error = -ESRCH;
		goto out;
	}

	error = ptrace_signal_data_result(data);
	if (error) {
		goto out;
	}

	action = ptrace_wakeup_request_action_result(request);
	switch (action) {
	case PTRACE_WAKEUP_ACTION_KILL:
		process_thread_ptrace_saved_context_clear_result(child,
			__builtin_offsetof(struct thread,
					   ptrace_saved_uctx_valid));
		memset(&info, '\0', sizeof info);
		info.si_signo = SIGKILL;
		error = do_kill(thread, pid, -1, SIGKILL, &info, 0);
		if (error < 0) {
			goto out;
		}
		break;
	case PTRACE_WAKEUP_ACTION_RESUME:
		process_thread_ptrace_saved_context_clear_result(child,
			__builtin_offsetof(struct thread,
					   ptrace_saved_uctx_valid));
		if (ptrace_resume_single_step_result(request)) {
			set_single_step(child);
		}
		mcs_rwlock_writer_lock(&child->proc->update_lock, &lock);
		process_thread_ptrace_trace_syscall_update_result(child,
			__builtin_offsetof(struct thread, ptrace),
			ptrace_resume_trace_syscall_result(request));
		mcs_rwlock_writer_unlock(&child->proc->update_lock, &lock);
		if (ptrace_resume_signal_needed_result(request, data)) {
			struct sig_pending *pending;

			/* TODO: Tracing process replace the original
			   signal with "data" */
			source = ptrace_resume_signal_source_result(request,
					child->ptrace_sendsig != NULL,
					child->ptrace_recvsig != NULL);
			pending = process_thread_ptrace_pending_signal_take_result(
					child,
					__builtin_offsetof(struct thread,
							   ptrace_sendsig),
					__builtin_offsetof(struct thread,
							   ptrace_recvsig),
					source);
			if (pending) {
				memcpy(&info, &pending->info, sizeof info);
				kfree_tracked(pending, __FILE__, __LINE__);
			}
			else {
				memset(&info, '\0', sizeof info);
				info.si_signo = data;
				info.si_code = SI_USER;
				info._sifields._kill.si_pid = thread->proc->pid;
			}
			error = do_kill(thread, pid, -1, data, &info, 1);
			if (error < 0) {
				goto out;
			}
		}
		break;
	default:
		break;
	}

	sched_wakeup_thread(child, PS_TRACED | PS_STOPPED);
out:
	if(child)
		thread_unlock(child);
	return error;
#endif
}

extern long ptrace_read_user(struct thread *thread, long addr, unsigned long *value);
extern long ptrace_write_user(struct thread *thread, long addr, unsigned long value);
extern long ptrace_read_fpregs(struct thread *thread, void *fpregs);
extern long ptrace_write_fpregs(struct thread *thread, void *fpregs);
extern long ptrace_read_regset(struct thread *thread, long type, struct iovec *iov);
extern long ptrace_write_regset(struct thread *thread, long type, struct iovec *iov);

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
static const struct ptrace_io_offsets ptrace_io_kernel_offsets = {
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_vm_offset = __builtin_offsetof(struct thread, vm),
	.thread_ptrace_offset = __builtin_offsetof(struct thread, ptrace),
	.thread_ptrace_eventmsg_offset =
		__builtin_offsetof(struct thread, ptrace_eventmsg),
	.thread_ptrace_recvsig_offset =
		__builtin_offsetof(struct thread, ptrace_recvsig),
	.thread_ptrace_sendsig_offset =
		__builtin_offsetof(struct thread, ptrace_sendsig),
	.thread_report_proc_offset =
		__builtin_offsetof(struct thread, report_proc),
	.thread_ptrace_saved_uctx_valid_offset =
		__builtin_offsetof(struct thread, ptrace_saved_uctx_valid),
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.proc_update_lock_offset =
		__builtin_offsetof(struct process, update_lock),
};

static unsigned long
ptrace_find_thread_bridge(int tgid, int tid)
{
	return (unsigned long)find_thread(tgid, tid);
}

static void
ptrace_thread_unlock_bridge(unsigned long thread_addr)
{
	thread_unlock((struct thread *)thread_addr);
}

static void
ptrace_text_log_bridge(int event, unsigned long addr)
{
	if (event == 1) {
		dkprintf("ptrace_peektext: bad area  addr=0x%llx\n", addr);
	}
	else if (event == 2) {
		dkprintf("ptrace_poketext: bad address 0x%llx\n", addr);
	}
}

static void
ptrace_control_log_bridge(int event, int value, int result)
{
	if (event == PTRACE_CONTROL_LOG_SETOPTIONS_UNSUPPORTED) {
		kprintf("ptrace_setoptions: not supported flag %x\n", value);
	}
	else if (event == PTRACE_CONTROL_LOG_SETOPTIONS_APPLIED) {
		int flags = value;

		dkprintf("%s: (PT_TRACED%s%s%s%s%s%s)\n",
			"ptrace_setoptions",
			flags & PTRACE_O_TRACESYSGOOD ?
				"|PTRACE_O_TRACESYSGOOD" : "",
			flags & PTRACE_O_TRACEFORK ? "|PTRACE_O_TRACEFORK" : "",
			flags & PTRACE_O_TRACEVFORK ? "|PTRACE_O_TRACEVFORK" : "",
			flags & PTRACE_O_TRACECLONE ? "|PTRACE_O_TRACECLONE" : "",
			flags & PTRACE_O_TRACEEXEC ? "|PTRACE_O_TRACEEXEC" : "",
			flags & PTRACE_O_TRACEVFORKDONE ?
				"|PTRACE_O_TRACEVFORKDONE" : "",
			flags & PTRACE_O_TRACEEXIT ? "|PTRACE_O_TRACEEXIT" : "");
	}
	else if (event == PTRACE_CONTROL_LOG_ATTACH_RETURN) {
		dkprintf("ptrace_attach,returning,error=%d\n", result);
	}
}

static int
ptrace_attach_thread_bridge(unsigned long thread_addr, unsigned long proc_addr)
{
	return ptrace_attach_thread((struct thread *)thread_addr,
			(struct process *)proc_addr);
}

static void
ptrace_detach_call_bridge(unsigned long thread_addr, int data)
{
	ptrace_detach_thread((struct thread *)thread_addr, data);
}
#endif

static long
ptrace_read_user_word_bridge(unsigned long thread_addr, long addr,
		unsigned long *value)
{
	return ptrace_read_user((struct thread *)thread_addr, addr, value);
}

static long
ptrace_write_user_word_bridge(unsigned long thread_addr, long addr,
		unsigned long value)
{
	return ptrace_write_user((struct thread *)thread_addr, addr, value);
}

static long
ptrace_read_vm_word_bridge(unsigned long vm_addr, unsigned long addr,
		unsigned long *value)
{
	return read_process_vm((struct process_vm *)vm_addr, value,
			(void *)addr, sizeof(*value));
}

static long
ptrace_write_vm_word_bridge(unsigned long vm_addr, unsigned long addr,
		unsigned long value)
{
	return patch_process_vm((struct process_vm *)vm_addr, (void *)addr,
			&value, sizeof(value));
}

static long
ptrace_read_fpregs_bridge(unsigned long thread_addr, unsigned long data_addr)
{
	return ptrace_read_fpregs((struct thread *)thread_addr, (void *)data_addr);
}

static long
ptrace_write_fpregs_bridge(unsigned long thread_addr, unsigned long data_addr)
{
	return ptrace_write_fpregs((struct thread *)thread_addr, (void *)data_addr);
}

static long
ptrace_copy_from_user_bridge(void *dst, unsigned long src_addr, size_t bytes)
{
	return copy_from_user(dst, (void *)src_addr, bytes);
}

static long
ptrace_copy_to_user_bridge(unsigned long dst_addr, const void *src, size_t bytes)
{
	return copy_to_user((void *)dst_addr, src, bytes);
}

static long
ptrace_read_regset_bridge(unsigned long thread_addr, long type, void *iovp)
{
	return ptrace_read_regset((struct thread *)thread_addr, type,
			(struct iovec *)iovp);
}

static long
ptrace_write_regset_bridge(unsigned long thread_addr, long type, void *iovp)
{
	return ptrace_write_regset((struct thread *)thread_addr, type,
			(struct iovec *)iovp);
}

static long ptrace_pokeuser(int pid, long addr, long data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	return ptrace_pokeuser_body_result(pid, addr, data,
			sizeof(struct user), &ptrace_io_kernel_offsets,
			ptrace_find_thread_bridge, ptrace_thread_unlock_bridge,
			ptrace_write_user_word_bridge);
#else
	long rc = -EIO;
	struct thread *child;

	rc = ptrace_user_area_result(addr, sizeof(struct user));
	if (rc) {
		return rc;
	}
	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	rc = ptrace_write_user_word_result(child->status, (unsigned long)child,
			addr, (unsigned long)data, ptrace_write_user_word_bridge);
	thread_unlock(child);

	return rc;
#endif
}

static long ptrace_peekuser(int pid, long addr, long data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	return ptrace_peekuser_body_result(pid, addr, data,
			sizeof(struct user), &ptrace_io_kernel_offsets,
			ptrace_find_thread_bridge, ptrace_thread_unlock_bridge,
			ptrace_read_user_word_bridge, ptrace_copy_to_user_bridge);
#else
	long rc = -EIO;
	struct thread *child;
	unsigned long *p = (unsigned long *)data;

	rc = ptrace_user_area_result(addr, sizeof(struct user));
	if (rc) {
		return rc;
	}
	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	{
		unsigned long value;

		rc = ptrace_read_user_word_result(child->status,
				(unsigned long)child, addr, &value,
				ptrace_read_user_word_bridge);
		if (rc == 0) {
			rc = copy_to_user(p, (char *)&value, sizeof(value));
		}
	}
	thread_unlock(child);

	return rc;
#endif
}

static long ptrace_getregs(int pid, long data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct user_regs_struct user_regs;

	return ptrace_getregs_body_result(pid, data, &user_regs,
			sizeof(user_regs), &ptrace_io_kernel_offsets,
			ptrace_find_thread_bridge, ptrace_thread_unlock_bridge,
			ptrace_read_user_word_bridge, ptrace_copy_to_user_bridge);
#else
	struct user_regs_struct *regs = (struct user_regs_struct *)data;
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	if(ptrace_status_allows_io(child->status)){
		struct user_regs_struct user_regs;

		memset(&user_regs, '\0', sizeof(struct user_regs_struct));
		rc = ptrace_read_user_words_result((unsigned long)child,
				(unsigned long *)&user_regs, sizeof(user_regs),
				ptrace_read_user_word_bridge);
		if (rc == 0) {
			rc = copy_to_user(regs, &user_regs, sizeof(struct user_regs_struct));
		}
	}
	thread_unlock(child);

	return rc;
#endif
}

static long ptrace_setregs(int pid, long data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct user_regs_struct user_regs;

	return ptrace_setregs_body_result(pid, data, &user_regs,
			sizeof(user_regs), &ptrace_io_kernel_offsets,
			ptrace_find_thread_bridge, ptrace_thread_unlock_bridge,
			ptrace_write_user_word_bridge,
			ptrace_copy_from_user_bridge);
#else
	struct user_regs_struct *regs = (struct user_regs_struct *)data;
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	if(ptrace_status_allows_io(child->status)){
		struct user_regs_struct user_regs;
		rc = copy_from_user(&user_regs, regs, sizeof(struct user_regs_struct));
		if (rc == 0) {
			rc = ptrace_write_user_words_result((unsigned long)child,
					(unsigned long *)&user_regs,
					sizeof(user_regs),
					ptrace_write_user_word_bridge);
		}
	}
	thread_unlock(child);

	return rc;
#endif
}

static long ptrace_getfpregs(int pid, long data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	return ptrace_fpregs_body_result(pid, data, &ptrace_io_kernel_offsets,
			ptrace_find_thread_bridge, ptrace_thread_unlock_bridge,
			ptrace_read_fpregs_bridge);
#else
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	rc = ptrace_fpregs_io_result(child->status, (unsigned long)child,
			(unsigned long)data, ptrace_read_fpregs_bridge);
	thread_unlock(child);

	return rc;
#endif
}

static long ptrace_setfpregs(int pid, long data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	return ptrace_fpregs_body_result(pid, data, &ptrace_io_kernel_offsets,
			ptrace_find_thread_bridge, ptrace_thread_unlock_bridge,
			ptrace_write_fpregs_bridge);
#else
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	rc = ptrace_fpregs_io_result(child->status, (unsigned long)child,
			(unsigned long)data, ptrace_write_fpregs_bridge);
	thread_unlock(child);

	return rc;
#endif
}

static long ptrace_getregset(int pid, long type, long data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct iovec iov;

	return ptrace_regset_body_result(pid, type, data, &iov, sizeof(iov),
			__builtin_offsetof(struct iovec, iov_len),
			sizeof(iov.iov_len), &ptrace_io_kernel_offsets,
			ptrace_find_thread_bridge, ptrace_thread_unlock_bridge,
			ptrace_copy_from_user_bridge, ptrace_read_regset_bridge,
			ptrace_copy_to_user_bridge);
#else
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	{
		struct iovec iov;

		rc = ptrace_regset_io_result(child->status, (unsigned long)child,
				type, (unsigned long)data, &iov, sizeof(iov),
				__builtin_offsetof(struct iovec, iov_len),
				sizeof(iov.iov_len), ptrace_copy_from_user_bridge,
				ptrace_read_regset_bridge, ptrace_copy_to_user_bridge);
	}
	thread_unlock(child);

	return rc;
#endif
}

static long ptrace_setregset(int pid, long type, long data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct iovec iov;

	return ptrace_regset_body_result(pid, type, data, &iov, sizeof(iov),
			__builtin_offsetof(struct iovec, iov_len),
			sizeof(iov.iov_len), &ptrace_io_kernel_offsets,
			ptrace_find_thread_bridge, ptrace_thread_unlock_bridge,
			ptrace_copy_from_user_bridge, ptrace_write_regset_bridge,
			ptrace_copy_to_user_bridge);
#else
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	{
		struct iovec iov;

		rc = ptrace_regset_io_result(child->status, (unsigned long)child,
				type, (unsigned long)data, &iov, sizeof(iov),
				__builtin_offsetof(struct iovec, iov_len),
				sizeof(iov.iov_len), ptrace_copy_from_user_bridge,
				ptrace_write_regset_bridge, ptrace_copy_to_user_bridge);
	}
	thread_unlock(child);

	return rc;
#endif
}

static long ptrace_peektext(int pid, long addr, long data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	return ptrace_peektext_body_result(pid, addr, data,
			&ptrace_io_kernel_offsets, ptrace_find_thread_bridge,
			ptrace_thread_unlock_bridge, ptrace_read_vm_word_bridge,
			ptrace_copy_to_user_bridge, ptrace_text_log_bridge);
#else
	long rc = -EIO;
	struct thread *child;
	unsigned long *p = (unsigned long *)data;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	{
		unsigned long value;

		rc = ptrace_read_vm_word_result(child->status,
				(unsigned long)child->vm, addr, &value,
				ptrace_read_vm_word_bridge);
		if (rc != 0) {
			if (ptrace_status_allows_io(child->status)) {
				dkprintf("ptrace_peektext: bad area  addr=0x%llx\n",
					 addr);
			}
		} else {
			rc = copy_to_user(p, &value, sizeof(value));
		}
	}
	thread_unlock(child);

	return rc;
#endif
}

static long ptrace_poketext(int pid, long addr, long data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	return ptrace_poketext_body_result(pid, addr, data,
			&ptrace_io_kernel_offsets, ptrace_find_thread_bridge,
			ptrace_thread_unlock_bridge, ptrace_write_vm_word_bridge,
			ptrace_text_log_bridge);
#else
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	{
		rc = ptrace_write_vm_word_result(child->status,
				(unsigned long)child->vm, addr, data,
				ptrace_write_vm_word_bridge);
		if (rc) {
			if (ptrace_status_allows_io(child->status)) {
				dkprintf("ptrace_poketext: bad address 0x%llx\n",
					 addr);
			}
		}
	}
	thread_unlock(child);

	return rc;
#endif
}

static int ptrace_setoptions(int pid, int flags)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	return ptrace_setoptions_body_result(pid, flags,
			&ptrace_io_kernel_offsets, ptrace_find_thread_bridge,
			ptrace_thread_unlock_bridge,
			ptrace_control_log_bridge);
#else
	int ret;
	struct thread *child;

	/* Only supported options are enabled.
	 * Following options are pretended to be supported for the time being:
	 * PTRACE_O_TRACESYSGOOD 
	 * PTRACE_O_TRACEFORK
	 * PTRACE_O_TRACEVFORK
	 * PTRACE_O_TRACECLONE
	 * PTRACE_O_TRACEEXEC
	 * PTRACE_O_TRACEVFORKDONE
	 */
	ret = ptrace_setoptions_flags_result(flags);
	if (ret) {
		kprintf("ptrace_setoptions: not supported flag %x\n", flags);
		goto out;
	}

	child = find_thread(0, pid);
	ret = ptrace_child_traced_result(child != NULL,
			child != NULL && child->proc != NULL,
			child ? child->ptrace : 0);
	if (ret) {
		goto unlockout;
	}
	
	ptrace_setoptions_apply_thread_result((unsigned long)child,
			__builtin_offsetof(struct thread, ptrace), flags);
	dkprintf("%s: (PT_TRACED%s%s%s%s%s%s)\n",
		__func__,
		flags & PTRACE_O_TRACESYSGOOD ? "|PTRACE_O_TRACESYSGOOD" : "",
		flags & PTRACE_O_TRACEFORK ? "|PTRACE_O_TRACEFORK" : "",
		flags & PTRACE_O_TRACEVFORK ? "|PTRACE_O_TRACEVFORK" : "",
		flags & PTRACE_O_TRACECLONE ? "|PTRACE_O_TRACECLONE" : "",
		flags & PTRACE_O_TRACEEXEC ? "|PTRACE_O_TRACEEXEC" : "",
		flags & PTRACE_O_TRACEVFORKDONE ? "|PTRACE_O_TRACEVFORKDONE" : "",
		flags & PTRACE_O_TRACEEXIT ? "|PTRACE_O_TRACEEXIT" : "");

	ret = 0;

unlockout:
	if(child)
		thread_unlock(child);
out:
	return ret;
#endif
}

static int ptrace_attach(int pid)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct thread *mythread = get_this_cpu_local_var()->current;

	return ptrace_attach_body_result(pid, (unsigned long)mythread,
			(unsigned long)mythread->proc, &ptrace_io_kernel_offsets,
			ptrace_find_thread_bridge, ptrace_thread_unlock_bridge,
			ptrace_attach_thread_bridge, ptrace_detach_do_kill_bridge,
			ptrace_control_log_bridge);
#else
	int error = 0;
	struct thread *thread;
	struct thread *mythread = get_this_cpu_local_var()->current;
	struct process *proc = mythread->proc;
	struct siginfo info;

	thread = find_thread(0, pid);
	if (!thread) {
		error = -ESRCH;
		goto out;
	}

	error = ptrace_attach_policy_result(proc->pid, pid, thread->ptrace,
			thread->proc == proc);
	if (error) {
		thread_unlock(thread);
		goto out;
	}

	ptrace_attach_mark_traced_result((unsigned long)thread,
			__builtin_offsetof(struct thread, ptrace));
	error = ptrace_attach_thread(thread, proc);

	thread_unlock(thread);

	memset(&info, '\0', sizeof info);
	info.si_signo = SIGSTOP;
	info.si_code = SI_USER;
	info._sifields._kill.si_pid = proc->pid;
	error = do_kill(mythread, -1, pid, SIGSTOP, &info, 2);

  out:
	dkprintf("ptrace_attach,returning,error=%d\n", error);
	return error;
#endif
}


int ptrace_detach(int pid, int data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct thread *mythread = get_this_cpu_local_var()->current;

	return ptrace_detach_body_result(pid, data,
			(unsigned long)mythread->proc, &ptrace_io_kernel_offsets,
			ptrace_find_thread_bridge, ptrace_thread_unlock_bridge,
			ptrace_detach_call_bridge);
#else
	int error = 0;
	struct thread *thread;
	struct thread *mythread = get_this_cpu_local_var()->current;
	struct process *proc = mythread->proc;;

	error = ptrace_detach_signal_result(data);
	if (error) {
		return error;
	}

	thread = find_thread(0, pid);
	if (!thread) {
		error = -ESRCH;
		goto out;
	}

	error = ptrace_detach_state_result(!!(thread->ptrace & PT_TRACED),
			thread->report_proc == proc);
	if (error) {
		thread_unlock(thread);
		goto out;
	}

	ptrace_detach_thread(thread, data);

	thread_unlock(thread);
out:
	return error;
#endif
}

static long ptrace_geteventmsg(int pid, long data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	return ptrace_geteventmsg_body_result(pid, data,
			sizeof(unsigned long), &ptrace_io_kernel_offsets,
			ptrace_find_thread_bridge, ptrace_thread_unlock_bridge,
			ptrace_copy_to_user_bridge);
#else
	unsigned long *msg_p = (unsigned long *)data;
	unsigned long eventmsg = 0;
	long rc = -ESRCH;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child) {
		return -ESRCH;
	}
	rc = ptrace_eventmsg_prepare_result(child->status,
			child->ptrace_eventmsg, &eventmsg);
	if (!rc) {
		if (copy_to_user(msg_p, &eventmsg, sizeof(*msg_p))) {
			rc = -EFAULT;
		}
		else {
			rc = 0;
		}
	}
	thread_unlock(child);

	return rc;
#endif
}

static long
ptrace_getsiginfo(int pid, siginfo_t *data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	siginfo_t info;

	return ptrace_getsiginfo_body_result(pid, (unsigned long)data,
			&info, sizeof(info),
			__builtin_offsetof(struct sig_pending, info),
			&ptrace_io_kernel_offsets, ptrace_find_thread_bridge,
			ptrace_thread_unlock_bridge, ptrace_copy_to_user_bridge);
#else
	struct thread *child;
	siginfo_t info;
	int rc = 0;

	child = find_thread(0, pid);
	if (!child) {
		return -ESRCH;
	}

	rc = ptrace_getsiginfo_prepare_result(child->status,
			(unsigned long)child->ptrace_recvsig,
			__builtin_offsetof(struct sig_pending, info),
			&info, sizeof(info));
	if (!rc) {
		if (copy_to_user(data, &info, sizeof(info))) {
			rc = -EFAULT;
		}
	}
	thread_unlock(child);
	return rc;
#endif
}

static long
ptrace_setsiginfo(int pid, siginfo_t *data)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	siginfo_t info;

	return ptrace_setsiginfo_body_result(pid, (unsigned long)data,
			&info, sizeof(info), sizeof(struct sig_pending),
			IHK_MC_AP_NOWAIT,
			__builtin_offsetof(struct sig_pending, info),
			&ptrace_io_kernel_offsets, ptrace_find_thread_bridge,
			ptrace_thread_unlock_bridge, syscall_alloc_bridge,
			ptrace_copy_from_user_bridge);
#else
	struct thread *child;
	struct sig_pending *allocated_sendsig = NULL;
	siginfo_t info;
	int rc = 0;
	int target;

	child = find_thread(0, pid);
	if (!child) {
		return -ESRCH;
	}

	target = ptrace_setsiginfo_target_result(child->status,
			child->ptrace_sendsig != NULL,
			child->ptrace_recvsig != NULL);
	if (target < 0) {
		rc = target;
	}
	else {
		if (target & PTRACE_SIGINFO_ALLOC_SENDSIG) {
			allocated_sendsig = kmalloc_tracked(sizeof(struct sig_pending), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
			if (allocated_sendsig == NULL) {
				rc = -ENOMEM;
			}
			else {
				rc = ptrace_setsiginfo_store_result(
						(unsigned long)child,
						__builtin_offsetof(struct thread,
								   ptrace_sendsig),
						__builtin_offsetof(struct thread,
								   ptrace_recvsig),
						__builtin_offsetof(struct sig_pending,
								   info),
						PTRACE_SIGINFO_ALLOC_SENDSIG,
						(unsigned long)allocated_sendsig,
						NULL, 0);
			}
		}

		if (!rc && (target & PTRACE_SIGINFO_STORE_SENDSIG)) {
			if (copy_from_user(&info, data, sizeof(info))) {
				rc = -EFAULT;
			}
			else {
				rc = ptrace_setsiginfo_store_result(
						(unsigned long)child,
						__builtin_offsetof(struct thread,
								   ptrace_sendsig),
						__builtin_offsetof(struct thread,
								   ptrace_recvsig),
						__builtin_offsetof(struct sig_pending,
								   info),
						PTRACE_SIGINFO_STORE_SENDSIG,
						0, &info, sizeof(info));
			}
		}
		if (!rc && (target & PTRACE_SIGINFO_STORE_RECVSIG)) {
			if (copy_from_user(&info, data, sizeof(info))) {
				rc = -EFAULT;
			}
			else {
				rc = ptrace_setsiginfo_store_result(
						(unsigned long)child,
						__builtin_offsetof(struct thread,
								   ptrace_sendsig),
						__builtin_offsetof(struct thread,
								   ptrace_recvsig),
						__builtin_offsetof(struct sig_pending,
								   info),
						PTRACE_SIGINFO_STORE_RECVSIG,
						0, &info, sizeof(info));
			}
		}
	}
	thread_unlock(child);
	return rc;
#endif
}

long sys_ptrace(int n, ihk_mc_user_context_t *ctx)
{
	const long request = (long)ihk_mc_syscall_arg0(ctx);
	const int pid = (int)ihk_mc_syscall_arg1(ctx);
	const long addr = (long)ihk_mc_syscall_arg2(ctx);
	const long data = (long)ihk_mc_syscall_arg3(ctx);
	static const struct ptrace_syscall_ops ops = {
		.traceme_fn = ptrace_traceme,
		.wakeup_fn = ptrace_wakeup_sig,
		.getregs_fn = ptrace_getregs,
		.setregs_fn = ptrace_setregs,
		.getfpregs_fn = ptrace_getfpregs,
		.setfpregs_fn = ptrace_setfpregs,
		.peekuser_fn = ptrace_peekuser,
		.pokeuser_fn = ptrace_pokeuser,
		.peektext_fn = ptrace_peektext,
		.poketext_fn = ptrace_poketext,
		.setoptions_fn = ptrace_setoptions,
		.attach_fn = ptrace_attach,
		.detach_fn = ptrace_detach,
		.getsiginfo_fn = ptrace_getsiginfo,
		.setsiginfo_fn = ptrace_setsiginfo,
		.getregset_fn = ptrace_getregset,
		.setregset_fn = ptrace_setregset,
		.geteventmsg_fn = ptrace_geteventmsg,
		.arch_fn = arch_ptrace,
	};
	long error = ptrace_syscall_body_result(request, pid, addr, data, &ops);

	dkprintf("ptrace(%d,%ld,%p,%p): returning %d\n", request, pid, addr, data, error);
	return error;
}

#define SCHED_CHECK_SAME_OWNER        0x01
#define SCHED_CHECK_ROOT              0x02

#if defined(MCKERNEL_RUST_SCHED_POLICY_HELPERS) || \
	defined(MCKERNEL_SCHED_POLICY_HELPERS_TEST_EXPORT)
#define SCHED_POLICY_HELPER_SCOPE
#else
#define SCHED_POLICY_HELPER_SCOPE static
#endif

struct sched_syscall_offsets {
	size_t thread_proc_offset;
	size_t thread_sched_param_offset;
	size_t thread_sched_policy_offset;
	size_t thread_cpu_id_offset;
	size_t thread_cpu_set_offset;
	size_t proc_pid_offset;
	size_t proc_ruid_offset;
	size_t proc_euid_offset;
	size_t proc_cpu_set_offset;
};

typedef unsigned long (*sched_find_thread_fn_t)(int pid);
typedef void (*sched_thread_unlock_fn_t)(unsigned long thread_addr);
typedef int (*sched_hold_thread_fn_t)(unsigned long thread_addr);
typedef void (*sched_release_thread_fn_t)(unsigned long thread_addr);
typedef int (*sched_apply_scheduler_fn_t)(unsigned long thread_addr,
		int policy, unsigned long param_addr);
typedef void (*sched_request_migrate_fn_t)(int cpu_id,
		unsigned long thread_addr);

#ifdef MCKERNEL_RUST_SCHED_POLICY_HELPERS
extern int sched_policy_is_valid(int policy);
extern int sched_policy_needs_root(int policy);
extern int setscheduler_validate(int policy, int priority);
extern long sched_rr_interval_nsec(int policy);
extern int sched_affinity_permission_result(uid_t caller_euid,
		uid_t target_ruid, uid_t target_euid);
extern int sched_getaffinity_len_result(size_t len, int nr_cpus);
extern size_t sched_affinity_copy_len(size_t len, size_t cpuset_size);
extern long sched_setparam_body_result(int pid, unsigned long uparam_addr,
		unsigned long current_thread, unsigned long param_addr,
		size_t param_size, const struct sched_syscall_offsets *offsets,
		int syscall_nr, sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_do_syscall2_fn_t syscall2_fn,
		sched_apply_scheduler_fn_t apply_fn);
extern long sched_getparam_body_result(int pid, unsigned long uparam_addr,
		unsigned long current_thread, size_t param_size,
		const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
extern long sched_setscheduler_body_result(int pid, int policy,
		unsigned long uparam_addr, unsigned long current_thread,
		unsigned long param_addr, size_t param_size,
		const struct sched_syscall_offsets *offsets, int syscall_nr,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_do_syscall2_fn_t syscall2_fn,
		sched_apply_scheduler_fn_t apply_fn);
extern long sched_getscheduler_body_result(int pid,
		unsigned long current_thread,
		const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn);
extern long sched_rr_get_interval_body_result(int pid,
		unsigned long utime_addr, unsigned long current_thread,
		const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
extern long sched_setaffinity_body_result(int tid, size_t len,
		unsigned long u_cpu_set_addr, unsigned long current_thread,
		unsigned long k_cpu_set_addr, unsigned long cpu_set_addr,
		size_t cpuset_size, int nr_cpus,
		const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		sched_hold_thread_fn_t hold_fn,
		sched_release_thread_fn_t release_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		sched_request_migrate_fn_t migrate_fn);
extern long sched_getaffinity_body_result(int tid, size_t len,
		unsigned long u_cpu_set_addr, unsigned long current_thread,
		size_t cpuset_size, int nr_cpus,
		const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		sched_hold_thread_fn_t hold_fn,
		sched_release_thread_fn_t release_fn,
		syscall_copy_to_user_fn_t copy_to_fn);
#else
SCHED_POLICY_HELPER_SCOPE int sched_policy_is_valid(int policy)
{
	return policy == SCHED_DEADLINE ||
		policy == SCHED_FIFO || policy == SCHED_RR ||
		policy == SCHED_NORMAL || policy == SCHED_BATCH ||
		policy == SCHED_IDLE;
}

SCHED_POLICY_HELPER_SCOPE int sched_policy_needs_root(int policy)
{
	return sched_policy_is_valid(policy) && policy != SCHED_NORMAL;
}

SCHED_POLICY_HELPER_SCOPE int setscheduler_validate(int policy, int priority)
{
	if ((policy == SCHED_FIFO || policy == SCHED_RR) &&
		((priority < 1) ||
		 (priority > MAX_USER_RT_PRIO - 1))) {
		return -EINVAL;
	}

	if ((policy == SCHED_NORMAL || policy == SCHED_BATCH || policy == SCHED_IDLE) &&
		(priority != 0)) {
		return -EINVAL;
	}

	return 0;
}

SCHED_POLICY_HELPER_SCOPE long sched_rr_interval_nsec(int policy)
{
	return policy == SCHED_RR ? 10000 : 0;
}

SCHED_POLICY_HELPER_SCOPE int sched_affinity_permission_result(uid_t caller_euid,
		uid_t target_ruid, uid_t target_euid)
{
	if (caller_euid != 0 &&
			caller_euid != target_ruid &&
			caller_euid != target_euid) {
		return -EPERM;
	}

	return 0;
}

SCHED_POLICY_HELPER_SCOPE int sched_getaffinity_len_result(size_t len,
		int nr_cpus)
{
	if (len * 8 < nr_cpus) {
		return -EINVAL;
	}
	if (len & (sizeof(unsigned long)-1)) {
		return -EINVAL;
	}

	return 0;
}

SCHED_POLICY_HELPER_SCOPE size_t sched_affinity_copy_len(size_t len,
		size_t cpuset_size)
{
	return len < cpuset_size ? len : cpuset_size;
}

static int sched_thread_pid(unsigned long thread_addr,
		const struct sched_syscall_offsets *offsets)
{
	struct thread *thread = (struct thread *)thread_addr;
	struct process *proc;

	if (!thread_addr || !offsets) {
		return -1;
	}
	proc = *(struct process **)((char *)thread + offsets->thread_proc_offset);
	if (!proc) {
		return -1;
	}
	return *(int *)((char *)proc + offsets->proc_pid_offset);
}

static int sched_thread_policy(unsigned long thread_addr,
		const struct sched_syscall_offsets *offsets)
{
	return *(int *)((char *)thread_addr + offsets->thread_sched_policy_offset);
}

static int sched_thread_cpu_id(unsigned long thread_addr,
		const struct sched_syscall_offsets *offsets)
{
	return *(int *)((char *)thread_addr + offsets->thread_cpu_id_offset);
}

static unsigned long sched_thread_proc_addr(unsigned long thread_addr,
		const struct sched_syscall_offsets *offsets)
{
	return *(unsigned long *)((char *)thread_addr + offsets->thread_proc_offset);
}

static long sched_affinity_select_thread(int tid, unsigned long current_thread,
		const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		sched_hold_thread_fn_t hold_fn, unsigned long *thread_out)
{
	unsigned long thread;
	unsigned long my_proc;
	unsigned long target_proc;
	uid_t my_euid;
	uid_t target_ruid;
	uid_t target_euid;

	if (!hold_fn) {
		return -EINVAL;
	}
	if (tid == 0) {
		hold_fn(current_thread);
		*thread_out = current_thread;
		return 0;
	}
	if (!find_fn || !unlock_fn) {
		return -EINVAL;
	}
	thread = find_fn(tid);
	if (!thread) {
		return -ESRCH;
	}
	my_proc = sched_thread_proc_addr(current_thread, offsets);
	target_proc = sched_thread_proc_addr(thread, offsets);
	if (!my_proc || !target_proc) {
		unlock_fn(thread);
		return -EINVAL;
	}
	my_euid = *(uid_t *)((char *)my_proc + offsets->proc_euid_offset);
	target_ruid = *(uid_t *)((char *)target_proc + offsets->proc_ruid_offset);
	target_euid = *(uid_t *)((char *)target_proc + offsets->proc_euid_offset);
	if (sched_affinity_permission_result(my_euid, target_ruid, target_euid)) {
		unlock_fn(thread);
		return -EPERM;
	}
	hold_fn(thread);
	unlock_fn(thread);
	*thread_out = thread;
	return 0;
}

static long sched_select_thread(int pid, unsigned long current_thread,
		const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		unsigned long *thread_out, int *pid_out, int *other_thread_out)
{
	int current_pid;

	if (pid < 0 || !current_thread || !offsets) {
		return -EINVAL;
	}
	current_pid = sched_thread_pid(current_thread, offsets);
	if (current_pid < 0) {
		return -EINVAL;
	}
	if (pid == 0) {
		pid = current_pid;
	}
	if (current_pid == pid) {
		*thread_out = current_thread;
		*pid_out = pid;
		*other_thread_out = 0;
		return 0;
	}
	if (!find_fn || !unlock_fn) {
		return -EINVAL;
	}
	*thread_out = find_fn(pid);
	if (!*thread_out) {
		return -ESRCH;
	}
	unlock_fn(*thread_out);
	*pid_out = pid;
	*other_thread_out = 1;
	return 0;
}

SCHED_POLICY_HELPER_SCOPE long sched_setparam_body_result(int pid,
		unsigned long uparam_addr, unsigned long current_thread,
		unsigned long param_addr, size_t param_size,
		const struct sched_syscall_offsets *offsets, int syscall_nr,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_do_syscall2_fn_t syscall2_fn,
		sched_apply_scheduler_fn_t apply_fn)
{
	unsigned long thread;
	int normalized_pid;
	int other_thread;
	long ret;

	if (!uparam_addr || pid < 0 || !current_thread || !param_addr || !offsets ||
			!copy_from_fn || !apply_fn) {
		return -EINVAL;
	}
	ret = sched_select_thread(pid, current_thread, offsets, find_fn, unlock_fn,
			&thread, &normalized_pid, &other_thread);
	if (ret) {
		return ret;
	}
	if (other_thread) {
		if (!syscall2_fn) {
			return -EINVAL;
		}
		ret = syscall2_fn(syscall_nr, SCHED_CHECK_SAME_OWNER,
				(unsigned long)normalized_pid);
		if (ret) {
			return ret;
		}
	}
	ret = copy_from_fn((void *)param_addr, uparam_addr, param_size);
	if (ret < 0) {
		return -EFAULT;
	}
	if (other_thread) {
		thread = find_fn(normalized_pid);
		if (!thread) {
			return -ESRCH;
		}
		ret = apply_fn(thread, sched_thread_policy(thread, offsets), param_addr);
		unlock_fn(thread);
		return ret;
	}
	return apply_fn(thread, sched_thread_policy(thread, offsets), param_addr);
}

SCHED_POLICY_HELPER_SCOPE long sched_getparam_body_result(int pid,
		unsigned long uparam_addr, unsigned long current_thread,
		size_t param_size, const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	unsigned long thread;
	int normalized_pid;
	int other_thread;
	long ret;

	if (!uparam_addr || pid < 0 || !current_thread || !offsets || !copy_to_fn) {
		return -EINVAL;
	}
	ret = sched_select_thread(pid, current_thread, offsets, find_fn, unlock_fn,
			&thread, &normalized_pid, &other_thread);
	if (ret) {
		return ret;
	}
	ret = copy_to_fn(uparam_addr,
			(const char *)thread + offsets->thread_sched_param_offset,
			param_size);
	return ret ? -EFAULT : 0;
}

SCHED_POLICY_HELPER_SCOPE long sched_setscheduler_body_result(int pid,
		int policy, unsigned long uparam_addr,
		unsigned long current_thread, unsigned long param_addr,
		size_t param_size, const struct sched_syscall_offsets *offsets,
		int syscall_nr, sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		syscall_do_syscall2_fn_t syscall2_fn,
		sched_apply_scheduler_fn_t apply_fn)
{
	unsigned long thread;
	int normalized_pid;
	int other_thread;
	long ret;

	if (!uparam_addr || pid < 0 || !current_thread || !param_addr || !offsets) {
		return -EINVAL;
	}
	if (!sched_policy_is_valid(policy)) {
		return -EINVAL;
	}
	if (sched_policy_needs_root(policy)) {
		if (!syscall2_fn) {
			return -EINVAL;
		}
		ret = syscall2_fn(syscall_nr, SCHED_CHECK_ROOT, 0);
		if (ret) {
			return ret;
		}
	}
	if (!copy_from_fn || !apply_fn) {
		return -EINVAL;
	}
	ret = copy_from_fn((void *)param_addr, uparam_addr, param_size);
	if (ret < 0) {
		return -EFAULT;
	}
	ret = sched_select_thread(pid, current_thread, offsets, find_fn, unlock_fn,
			&thread, &normalized_pid, &other_thread);
	if (ret) {
		return ret;
	}
	if (other_thread) {
		if (!syscall2_fn) {
			return -EINVAL;
		}
		ret = syscall2_fn(syscall_nr, SCHED_CHECK_SAME_OWNER,
				(unsigned long)normalized_pid);
		if (ret) {
			return ret;
		}
	}
	return apply_fn(thread, policy, param_addr);
}

SCHED_POLICY_HELPER_SCOPE long sched_getscheduler_body_result(int pid,
		unsigned long current_thread,
		const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn)
{
	unsigned long thread;
	int normalized_pid;
	int other_thread;
	long ret;

	if (pid < 0 || !current_thread || !offsets) {
		return -EINVAL;
	}
	ret = sched_select_thread(pid, current_thread, offsets, find_fn, unlock_fn,
			&thread, &normalized_pid, &other_thread);
	if (ret) {
		return ret;
	}
	return sched_thread_policy(thread, offsets);
}

SCHED_POLICY_HELPER_SCOPE long sched_rr_get_interval_body_result(int pid,
		unsigned long utime_addr, unsigned long current_thread,
		const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	unsigned long thread;
	struct timespec t;
	int normalized_pid;
	int other_thread;
	long ret;

	if (pid < 0 || !current_thread || !offsets || !copy_to_fn) {
		return -EINVAL;
	}
	ret = sched_select_thread(pid, current_thread, offsets, find_fn, unlock_fn,
			&thread, &normalized_pid, &other_thread);
	if (ret) {
		return ret;
	}
	t.tv_sec = 0;
	t.tv_nsec = sched_rr_interval_nsec(sched_thread_policy(thread, offsets));
	ret = copy_to_fn(utime_addr, &t, sizeof(t));
	return ret ? -EFAULT : 0;
}

SCHED_POLICY_HELPER_SCOPE long sched_setaffinity_body_result(int tid,
		size_t len, unsigned long u_cpu_set_addr,
		unsigned long current_thread, unsigned long k_cpu_set_addr,
		unsigned long cpu_set_addr, size_t cpuset_size, int nr_cpus,
		const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		sched_hold_thread_fn_t hold_fn,
		sched_release_thread_fn_t release_fn,
		syscall_copy_from_user_fn_t copy_from_fn,
		sched_request_migrate_fn_t migrate_fn)
{
	unsigned long thread;
	unsigned long proc;
	size_t copy_len;
	int cpu;
	int empty_set = 1;
	long ret;

	if (!u_cpu_set_addr) {
		return -EFAULT;
	}
	if (!current_thread || !k_cpu_set_addr || !cpu_set_addr || !cpuset_size ||
			!offsets || nr_cpus < 0 || !copy_from_fn || !release_fn ||
			!migrate_fn) {
		return -EINVAL;
	}
	if (cpuset_size > len) {
		memset((void *)k_cpu_set_addr, 0, cpuset_size);
	}
	copy_len = sched_affinity_copy_len(len, cpuset_size);
	if (copy_from_fn((void *)k_cpu_set_addr, u_cpu_set_addr, copy_len)) {
		return -EFAULT;
	}

	ret = sched_affinity_select_thread(tid, current_thread, offsets,
			find_fn, unlock_fn, hold_fn, &thread);
	if (ret) {
		return ret;
	}
	proc = sched_thread_proc_addr(thread, offsets);
	if (!proc) {
		release_fn(thread);
		return -EINVAL;
	}
	memset((void *)cpu_set_addr, 0, cpuset_size);
	for (cpu = 0; cpu < nr_cpus; cpu++) {
		if (CPU_ISSET(cpu, (cpu_set_t *)k_cpu_set_addr) &&
				CPU_ISSET(cpu, (cpu_set_t *)(proc +
						offsets->proc_cpu_set_offset))) {
			CPU_SET(cpu, (cpu_set_t *)cpu_set_addr);
			empty_set = 0;
		}
	}
	if (empty_set) {
		release_fn(thread);
		return -EINVAL;
	}
	memcpy((char *)thread + offsets->thread_cpu_set_offset,
			(void *)cpu_set_addr, cpuset_size);
	cpu = sched_thread_cpu_id(thread, offsets);
	if (!CPU_ISSET(cpu, (cpu_set_t *)((char *)thread +
					offsets->thread_cpu_set_offset))) {
		migrate_fn(cpu, thread);
	}
	release_fn(thread);
	return 0;
}

SCHED_POLICY_HELPER_SCOPE long sched_getaffinity_body_result(int tid,
		size_t len, unsigned long u_cpu_set_addr,
		unsigned long current_thread, size_t cpuset_size, int nr_cpus,
		const struct sched_syscall_offsets *offsets,
		sched_find_thread_fn_t find_fn,
		sched_thread_unlock_fn_t unlock_fn,
		sched_hold_thread_fn_t hold_fn,
		sched_release_thread_fn_t release_fn,
		syscall_copy_to_user_fn_t copy_to_fn)
{
	unsigned long thread;
	size_t copy_len;
	long ret;

	if (!current_thread || !cpuset_size || !offsets || nr_cpus < 0 ||
			!release_fn || !copy_to_fn) {
		return -EINVAL;
	}
	ret = sched_getaffinity_len_result(len, nr_cpus);
	if (ret) {
		return ret;
	}
	copy_len = sched_affinity_copy_len(len, cpuset_size);
	ret = sched_affinity_select_thread(tid, current_thread, offsets,
			find_fn, unlock_fn, hold_fn, &thread);
	if (ret) {
		return ret;
	}
	ret = copy_to_fn(u_cpu_set_addr,
			(const char *)thread + offsets->thread_cpu_set_offset,
			copy_len);
	release_fn(thread);
	return ret < 0 ? -EFAULT : (long)copy_len;
}
#endif /* MCKERNEL_RUST_SCHED_POLICY_HELPERS */

#undef SCHED_POLICY_HELPER_SCOPE

/* We do not have actual scheduling classes so we just make sure we store
 * policies and priorities in a POSIX/Linux complaint manner */
static int setscheduler(struct thread *thread, int policy, struct sched_param *param)
{
	int ret;

	ret = setscheduler_validate(policy, param->sched_priority);
	if (ret) {
		return ret;
	}

	memcpy(&thread->sched_param, param, sizeof(*param));
	thread->sched_policy = policy;

	return 0;
}

static const struct sched_syscall_offsets sched_syscall_offsets = {
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.thread_sched_param_offset = __builtin_offsetof(struct thread, sched_param),
	.thread_sched_policy_offset = __builtin_offsetof(struct thread, sched_policy),
	.thread_cpu_id_offset = __builtin_offsetof(struct thread, cpu_id),
	.thread_cpu_set_offset = __builtin_offsetof(struct thread, cpu_set),
	.proc_pid_offset = __builtin_offsetof(struct process, pid),
	.proc_ruid_offset = __builtin_offsetof(struct process, ruid),
	.proc_euid_offset = __builtin_offsetof(struct process, euid),
	.proc_cpu_set_offset = __builtin_offsetof(struct process, cpu_set),
};

unsigned long
sched_find_thread_bridge(int pid)
{
	return (unsigned long)find_thread(0, pid);
}

void
sched_thread_unlock_bridge(unsigned long thread_addr)
{
	thread_unlock((struct thread *)thread_addr);
}

int
sched_apply_scheduler_bridge(unsigned long thread_addr, int policy,
		unsigned long param_addr)
{
	return setscheduler((struct thread *)thread_addr, policy,
			(struct sched_param *)param_addr);
}

int
sched_hold_thread_bridge(unsigned long thread_addr)
{
	return hold_thread((struct thread *)thread_addr);
}

void
sched_release_thread_bridge(unsigned long thread_addr)
{
	release_thread((struct thread *)thread_addr);
}

void
sched_request_migrate_bridge(int cpu_id, unsigned long thread_addr)
{
	sched_request_migrate(cpu_id, (struct thread *)thread_addr);
}

void
sched_setparam_log_bridge(int pid, unsigned long uparam_addr)
{
	dkprintf("sched_setparam: pid: %d, uparam: 0x%lx\n", pid,
			uparam_addr);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_sched_setparam(int n, ihk_mc_user_context_t *ctx);
long sys_sched_getparam(int n, ihk_mc_user_context_t *ctx);
long sys_sched_setscheduler(int n, ihk_mc_user_context_t *ctx);
long sys_sched_getscheduler(int n, ihk_mc_user_context_t *ctx);
long sys_sched_setaffinity(int n, ihk_mc_user_context_t *ctx);
long sys_sched_getaffinity(int n, ihk_mc_user_context_t *ctx);
#else
long sys_sched_setparam(int n, ihk_mc_user_context_t *ctx)
{
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	struct sched_param *uparam = (struct sched_param *)ihk_mc_syscall_arg1(ctx);
	struct sched_param param;
	struct thread *thread = get_this_cpu_local_var()->current;

	dkprintf("sched_setparam: pid: %d, uparam: 0x%lx\n", pid, uparam);

	return sched_setparam_body_result(pid, (unsigned long)uparam,
			(unsigned long)thread, (unsigned long)&param, sizeof(param),
			&sched_syscall_offsets, __NR_sched_setparam,
			sched_find_thread_bridge, sched_thread_unlock_bridge,
			syscall_copy_from_user_bridge, syscall_do_syscall2_bridge,
			sched_apply_scheduler_bridge);
}

long sys_sched_getparam(int n, ihk_mc_user_context_t *ctx)
{
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	struct sched_param *param = (struct sched_param *)ihk_mc_syscall_arg1(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return sched_getparam_body_result(pid, (unsigned long)param,
			(unsigned long)thread, sizeof(*param), &sched_syscall_offsets,
			sched_find_thread_bridge, sched_thread_unlock_bridge,
			syscall_copy_to_user_bridge);
}

long sys_sched_setscheduler(int n, ihk_mc_user_context_t *ctx)
{
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	int policy = ihk_mc_syscall_arg1(ctx);
	struct sched_param *uparam = (struct sched_param *)ihk_mc_syscall_arg2(ctx);
	struct sched_param param;
	struct thread *thread = get_this_cpu_local_var()->current;

	return sched_setscheduler_body_result(pid, policy, (unsigned long)uparam,
			(unsigned long)thread, (unsigned long)&param, sizeof(param),
			&sched_syscall_offsets, __NR_sched_setparam,
			sched_find_thread_bridge, sched_thread_unlock_bridge,
			syscall_copy_from_user_bridge, syscall_do_syscall2_bridge,
			sched_apply_scheduler_bridge);
}

long sys_sched_getscheduler(int n, ihk_mc_user_context_t *ctx)
{
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return sched_getscheduler_body_result(pid, (unsigned long)thread,
			&sched_syscall_offsets, sched_find_thread_bridge,
			sched_thread_unlock_bridge);
}
#endif

#if defined(MCKERNEL_RUST_SCHED_PRIO_HELPERS) || \
	defined(MCKERNEL_SCHED_PRIO_HELPERS_TEST_EXPORT)
#define SCHED_PRIO_HELPER_SCOPE
#else
#define SCHED_PRIO_HELPER_SCOPE static
#endif

#ifdef MCKERNEL_RUST_SCHED_PRIO_HELPERS
extern int sched_get_priority_max_value(int policy);
extern long sched_get_priority_max_body_result(int policy);
#else
int NICE_TO_PRIO(int nice)
{
	return nice + DEFAULT_PRIO;
}

int PRIO_TO_NICE(int prio)
{
	return prio - DEFAULT_PRIO;
}

int USER_PRIO(int prio)
{
	return prio - MAX_RT_PRIO;
}

long nice_to_rlimit(long nice)
{
	return MAX_NICE - nice + 1;
}

long rlimit_to_nice(long prio)
{
	return MAX_NICE - prio + 1;
}

SCHED_PRIO_HELPER_SCOPE int sched_get_priority_max_value(int policy)
{
	int ret = -EINVAL;

	switch (policy) {
		case SCHED_FIFO:
		case SCHED_RR:
			ret = MAX_USER_RT_PRIO - 1;
			break;
		case SCHED_DEADLINE:
		case SCHED_NORMAL:
		case SCHED_BATCH:
		case SCHED_IDLE:
			ret = 0;
			break;
	}
	return ret;
}
#endif /* MCKERNEL_RUST_SCHED_PRIO_HELPERS */

#ifdef MCKERNEL_RUST_SCHED_PRIO_HELPERS
extern int sched_get_priority_min_value(int policy);
extern long sched_get_priority_min_body_result(int policy);
#else
SCHED_PRIO_HELPER_SCOPE int sched_get_priority_min_value(int policy)
{
	int ret = -EINVAL;

	switch (policy) {
		case SCHED_FIFO:
		case SCHED_RR:
			ret = 1;
			break;
		case SCHED_DEADLINE:
		case SCHED_NORMAL:
		case SCHED_BATCH:
		case SCHED_IDLE:
			ret = 0;
	}
	return ret;
}
#endif /* MCKERNEL_RUST_SCHED_PRIO_HELPERS */

#ifndef MCKERNEL_RUST_SCHED_PRIO_HELPERS
SCHED_PRIO_HELPER_SCOPE long sched_get_priority_max_body_result(int policy)
{
	return sched_get_priority_max_value(policy);
}

SCHED_PRIO_HELPER_SCOPE long sched_get_priority_min_body_result(int policy)
{
	return sched_get_priority_min_value(policy);
}
#endif /* MCKERNEL_RUST_SCHED_PRIO_HELPERS */

#undef SCHED_PRIO_HELPER_SCOPE

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_sched_get_priority_max(int n, ihk_mc_user_context_t *ctx);
long sys_sched_get_priority_min(int n, ihk_mc_user_context_t *ctx);
long sys_sched_rr_get_interval(int n, ihk_mc_user_context_t *ctx);
#else
long sys_sched_get_priority_max(int n, ihk_mc_user_context_t *ctx)
{
	int policy = ihk_mc_syscall_arg0(ctx);

	return sched_get_priority_max_body_result(policy);
}

long sys_sched_get_priority_min(int n, ihk_mc_user_context_t *ctx)
{
	int policy = ihk_mc_syscall_arg0(ctx);

	return sched_get_priority_min_body_result(policy);
}

long sys_sched_rr_get_interval(int n, ihk_mc_user_context_t *ctx)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	struct timespec *utime = (struct timespec *)ihk_mc_syscall_arg1(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return sched_rr_get_interval_body_result(pid, (unsigned long)utime,
			(unsigned long)thread, &sched_syscall_offsets,
			sched_find_thread_bridge, sched_thread_unlock_bridge,
			syscall_copy_to_user_bridge);
}
#endif

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_sched_setaffinity(int n, ihk_mc_user_context_t *ctx)
{
	int tid = (int)ihk_mc_syscall_arg0(ctx);
	size_t len = (size_t)ihk_mc_syscall_arg1(ctx);
	cpu_set_t *u_cpu_set = (cpu_set_t *)ihk_mc_syscall_arg2(ctx);
	cpu_set_t k_cpu_set, cpu_set;
	struct thread *thread = get_this_cpu_local_var()->current;

	return sched_setaffinity_body_result(tid, len, (unsigned long)u_cpu_set,
			(unsigned long)thread, (unsigned long)&k_cpu_set,
			(unsigned long)&cpu_set, sizeof(cpu_set), num_processors,
			&sched_syscall_offsets, sched_find_thread_bridge,
			sched_thread_unlock_bridge, sched_hold_thread_bridge,
			sched_release_thread_bridge, syscall_copy_from_user_bridge,
			sched_request_migrate_bridge);
}

// see linux-2.6.34.13/kernel/sched.c
long sys_sched_getaffinity(int n, ihk_mc_user_context_t *ctx)
{
	int tid = (int)ihk_mc_syscall_arg0(ctx);
	size_t len = (size_t)ihk_mc_syscall_arg1(ctx);
	cpu_set_t k_cpu_set, *u_cpu_set = (cpu_set_t *)ihk_mc_syscall_arg2(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	dkprintf("%s() len: %d, mask: %p\n", __FUNCTION__, len, u_cpu_set);
	return sched_getaffinity_body_result(tid, len, (unsigned long)u_cpu_set,
			(unsigned long)thread, sizeof(k_cpu_set), num_processors,
			&sched_syscall_offsets, sched_find_thread_bridge,
			sched_thread_unlock_bridge, sched_hold_thread_bridge,
			sched_release_thread_bridge, syscall_copy_to_user_bridge);
}
#endif

int
syscall_get_processor_id_bridge(void)
{
	return ihk_mc_get_processor_id();
}

int
syscall_get_numa_id_bridge(void)
{
	return ihk_mc_get_numa_id();
}

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_get_cpu_id(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_get_cpu_id_body_result(syscall_get_processor_id_bridge);
}
#endif

static const struct syscall_itimer_offsets syscall_itimer_offsets = {
	.thread_itimer_enabled_offset =
		__builtin_offsetof(struct thread, itimer_enabled),
	.thread_itimer_virtual_offset =
		__builtin_offsetof(struct thread, itimer_virtual),
	.thread_itimer_prof_offset =
		__builtin_offsetof(struct thread, itimer_prof),
	.thread_itimer_virtual_value_offset =
		__builtin_offsetof(struct thread, itimer_virtual_value),
	.thread_itimer_prof_value_offset =
		__builtin_offsetof(struct thread, itimer_prof_value),
};

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_setitimer(int n, ihk_mc_user_context_t *ctx);
long sys_getitimer(int n, ihk_mc_user_context_t *ctx);
#else
long sys_setitimer(int n, ihk_mc_user_context_t *ctx)
{
	int which = (int)ihk_mc_syscall_arg0(ctx);
	struct itimerval *new = (struct itimerval *)ihk_mc_syscall_arg1(ctx);
	struct itimerval *old = (struct itimerval *)ihk_mc_syscall_arg2(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return setitimer_body_result(which, (unsigned long)new,
			(unsigned long)old, thread, &syscall_itimer_offsets,
			__NR_setitimer, syscall_do_syscall3_bridge,
			syscall_copy_from_user_bridge, syscall_copy_to_user_bridge,
			syscall_set_timer_bridge);
}

long sys_getitimer(int n, ihk_mc_user_context_t *ctx)
{
	int which = (int)ihk_mc_syscall_arg0(ctx);
	struct itimerval *old = (struct itimerval *)ihk_mc_syscall_arg1(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return getitimer_body_result(which, (unsigned long)old, thread,
			&syscall_itimer_offsets, __NR_getitimer,
			syscall_do_syscall2_bridge, syscall_copy_to_user_bridge);
}
#endif

void
syscall_gettime_bridge(void *ts)
{
	calculate_time_from_tsc(ts);
}

static long
syscall_do_syscall2_bridge(int syscall_nr, unsigned long arg0,
		unsigned long arg1)
{
	struct syscall_request request IHK_DMA_ALIGN;

	request.number = syscall_nr;
	request.args[0] = arg0;
	request.args[1] = arg1;
	return do_syscall(&request, ihk_mc_get_processor_id());
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long
syscall_policy_do_syscall2_bridge(int syscall_nr, unsigned long arg0,
		unsigned long arg1)
{
	return syscall_do_syscall2_bridge(syscall_nr, arg0, arg1);
}
#endif

static long
syscall_do_syscall3_bridge(int syscall_nr, unsigned long arg0,
		unsigned long arg1, unsigned long arg2)
{
	struct syscall_request request IHK_DMA_ALIGN;

	request.number = syscall_nr;
	request.args[0] = arg0;
	request.args[1] = arg1;
	request.args[2] = arg2;
	return do_syscall(&request, ihk_mc_get_processor_id());
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long
syscall_policy_do_syscall3_bridge(int syscall_nr, unsigned long arg0,
		unsigned long arg1, unsigned long arg2)
{
	return syscall_do_syscall3_bridge(syscall_nr, arg0, arg1, arg2);
}
#endif

static long
syscall_do_syscall_request_bridge(struct syscall_request *request, int cpu)
{
	return do_syscall(request, cpu);
}

static unsigned long
syscall_virt_to_phys_bridge(void *addr)
{
	return virt_to_phys(addr);
}

void
syscall_set_timer_bridge(int runq_locked)
{
	set_timer(runq_locked);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_clock_gettime(int n, ihk_mc_user_context_t *ctx);
#else
long sys_clock_gettime(int n, ihk_mc_user_context_t *ctx)
{
	struct timespec *ts = (struct timespec *)ihk_mc_syscall_arg1(ctx);
	int clock_id = (int)ihk_mc_syscall_arg0(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct mcs_rwlock_node lock;

	return clock_gettime_body_result(clock_id, (unsigned long)ts,
			gettime_local_support, __NR_clock_gettime, thread,
			tod_data.clocks_per_sec, &syscall_cputime_offsets,
			syscall_gettime_bridge, syscall_copy_to_user_bridge,
			syscall_do_syscall2_bridge,
			syscall_threads_reader_lock_bridge,
			syscall_threads_reader_unlock_bridge, &lock,
			syscall_interrupt_cpu_bridge, syscall_cpu_pause_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_gettimeofday(int n, ihk_mc_user_context_t *ctx);
#else
long sys_gettimeofday(int n, ihk_mc_user_context_t *ctx)
{
	struct timeval *tv = (struct timeval *)ihk_mc_syscall_arg0(ctx);
	struct timezone *tz = (struct timezone *)ihk_mc_syscall_arg1(ctx);

	return gettimeofday_body_result((unsigned long)tv, (unsigned long)tz,
			gettime_local_support, __NR_gettimeofday,
			syscall_gettime_bridge, syscall_copy_to_user_bridge,
			syscall_do_syscall2_bridge);
}
#endif

void
syscall_settimeofday_lock_bridge(void *lock)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock);
}

void
syscall_settimeofday_unlock_bridge(void *lock)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock);
}

long
syscall_atomic64_read_bridge(void *value)
{
	return ihk_atomic64_read((ihk_atomic64_t *)value);
}

void
syscall_atomic64_inc_bridge(void *value)
{
	ihk_atomic64_inc((ihk_atomic64_t *)value);
}

void
syscall_wmb_bridge(void)
{
	wmb();
}

void
syscall_settimeofday_panic_bridge(void)
{
	panic("settimeofday");
}

void
syscall_settimeofday_log_bridge(int event, unsigned long utv,
		unsigned long utz, long sec, long nsec, long error)
{
	if (event == SETTIMEOFDAY_LOG_ENTER) {
		dkprintf("sys_settimeofday(%p,%p)\n", (void *)utv,
				(void *)utz);
	}
	else if (event == SETTIMEOFDAY_LOG_ORIGIN) {
		dkprintf("sys_settimeofday(%p,%p):origin <-- %ld.%ld\n",
				(void *)utv, (void *)utz, sec, nsec);
	}
	else if (event == SETTIMEOFDAY_LOG_EXIT) {
		dkprintf("sys_settimeofday(%p,%p): %ld\n", (void *)utv,
				(void *)utz, error);
	}
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_settimeofday(int n, ihk_mc_user_context_t *ctx);
#else
long sys_settimeofday(int n, ihk_mc_user_context_t *ctx)
{
	struct timeval * const utv = (void *)ihk_mc_syscall_arg0(ctx);
	struct timezone * const utz = (void *)ihk_mc_syscall_arg1(ctx);

	return settimeofday_body_result((unsigned long)utv,
			(unsigned long)utz, gettime_local_support,
			tod_data.clocks_per_sec, __NR_settimeofday, ctx,
			&tod_data_lock, &tod_data.version, &tod_data.origin,
			syscall_settimeofday_lock_bridge,
			syscall_settimeofday_unlock_bridge,
			syscall_copy_from_user_bridge, syscall_rdtsc_bridge,
			syscall_forward_context_bridge, syscall_atomic64_read_bridge,
			syscall_atomic64_inc_bridge, syscall_wmb_bridge,
			syscall_settimeofday_panic_bridge,
			syscall_settimeofday_log_bridge);
}
#endif

unsigned long
syscall_rdtsc_bridge(void)
{
	return rdtsc();
}

unsigned long
syscall_ns_per_tsc_bridge(void)
{
	return ihk_mc_get_ns_per_tsc();
}

int
syscall_has_sigpending_bridge(void *thread)
{
	return hassigpending(thread) != NULL;
}

void
syscall_cpu_pause_bridge(void)
{
	cpu_pause();
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_nanosleep(int n, ihk_mc_user_context_t *ctx);
#else
long sys_nanosleep(int n, ihk_mc_user_context_t *ctx)
{
	struct timespec *tv = (struct timespec *)ihk_mc_syscall_arg0(ctx);
	struct timespec *rem = (struct timespec *)ihk_mc_syscall_arg1(ctx);
	struct ihk_os_cpu_monitor *monitor = get_this_cpu_local_var()->monitor;
	struct thread *thread = get_this_cpu_local_var()->current;

	return nanosleep_body_result((unsigned long)tv, (unsigned long)rem,
			gettime_local_support, __NR_nanosleep, thread, monitor,
			__builtin_offsetof(struct ihk_os_cpu_monitor, status),
			IHK_OS_MONITOR_KERNEL_HEAVY,
			syscall_copy_from_user_bridge,
			syscall_copy_to_user_bridge,
			syscall_do_syscall2_bridge, syscall_rdtsc_bridge,
			syscall_ns_per_tsc_bridge, syscall_has_sigpending_bridge,
			syscall_cpu_pause_bridge);
}
#endif

//#define DISABLE_SCHED_YIELD
long
sched_yield_lock_bridge(void *lock)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock);
}

void
sched_yield_unlock_bridge(void *lock, long irqstate)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock, irqstate);
}

void
sched_yield_schedule_bridge(void)
{
	schedule();
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_sched_yield(int n, ihk_mc_user_context_t *ctx);
#else
long sys_sched_yield(int n, ihk_mc_user_context_t *ctx)
{
	struct cpu_local_var *v = get_this_cpu_local_var();

#ifdef DISABLE_SCHED_YIELD
	return 0;
#endif

	return sched_yield_body_result(v,
			offsetof(struct cpu_local_var, flags),
			offsetof(struct cpu_local_var, runq_len),
			offsetof(struct cpu_local_var, runq_lock),
			CPU_FLAG_NEED_RESCHED, sched_yield_lock_bridge,
			sched_yield_unlock_bridge, sched_yield_schedule_bridge);
}
#endif

void
memlock_write_lock_bridge(void *lock)
{
	ihk_rwspinlock_write_lock_noirq((ihk_rwspinlock_t *)lock);
}

void
memlock_write_unlock_bridge(void *lock)
{
	ihk_rwspinlock_write_unlock_noirq((ihk_rwspinlock_t *)lock);
}

struct vm_range *
memlock_lookup_range_bridge(struct process_vm *vm, unsigned long start,
		unsigned long end)
{
	return lookup_process_memory_range(vm, start, end);
}

struct vm_range *
memlock_next_range_bridge(struct process_vm *vm, struct vm_range *range)
{
	return next_process_memory_range(vm, range);
}

int
memlock_split_range_bridge(struct process_vm *vm, struct vm_range *range,
		unsigned long addr, struct vm_range **new_range)
{
	return split_process_memory_range(vm, range, addr, new_range);
}

int
memlock_join_range_bridge(struct process_vm *vm, struct vm_range *left,
		struct vm_range *right)
{
	return join_process_memory_range(vm, left, right);
}

int
memlock_populate_bridge(struct process_vm *vm, unsigned long start, size_t len)
{
	return populate_process_memory(vm, (void *)start, len);
}

void
memlock_log_bridge(const struct memlock_log_record *record)
{
	int event = record->event;
	int op = record->op;
	int cpu = record->cpu;
	unsigned long start = record->start;
	size_t len = record->len;
	unsigned long addr = record->addr;
	unsigned long range_start = record->range_start;
	unsigned long range_end = record->range_end;
	int error = record->error;
	const char *name = (op == MEMLOCK_OP_UNLOCK) ? "munlock" : "mlock";

	if (event == MEMLOCK_LOG_ENTER) {
		dkprintf("[%d]sys_%s(%lx,%lx)\n", cpu, name, start, len);
	}
	else if (event == MEMLOCK_LOG_NOT_CONTIG) {
		dkprintf("[%d]sys_%s(%lx,%lx):not contiguous. %lx [%lx-%lx)\n",
				cpu, name, start, len, addr, range_start, range_end);
	}
	else if (event == MEMLOCK_LOG_CANNOT_CHANGE) {
		ekprintf("[%d]sys_%s(%lx,%lx):cannot change. [%lx-%lx)\n",
				cpu, name, start, len, range_start, range_end);
	}
	else if (event == MEMLOCK_LOG_SPLIT_FAILED) {
		ekprintf("[%d]sys_%s(%lx,%lx):split failed. [%lx-%lx) %lx %d\n",
				cpu, name, start, len, range_start, range_end, addr,
				error);
	}
	else if (event == MEMLOCK_LOG_JOIN_FAILED) {
		dkprintf("[%d]sys_%s(%lx,%lx):join failed. %d\n",
				cpu, name, start, len, error);
	}
	else if (event == MEMLOCK_LOG_POPULATE_FAILED) {
		ekprintf("sys_%s(%lx,%lx):populate failed. %d\n",
				name, start, len, error);
	}
	else if (event == MEMLOCK_LOG_EXIT) {
		dkprintf("[%d]sys_%s(%lx,%lx): %d\n", cpu, name, start, len,
				error);
	}
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_mlock(int n, ihk_mc_user_context_t *ctx);
long sys_munlock(int n, ihk_mc_user_context_t *ctx);
#else
long sys_mlock(int n, ihk_mc_user_context_t *ctx)
{
	const uintptr_t start0 = ihk_mc_syscall_arg0(ctx);
	const size_t len0 = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct vm_regions *region = &thread->vm->region;

	return memlock_body_result(thread->vm, &thread->vm->memory_range_lock,
			start0, len0, region->user_start, region->user_end,
			MEMLOCK_OP_LOCK, ihk_mc_get_processor_id(),
			__builtin_offsetof(struct vm_range, start),
			__builtin_offsetof(struct vm_range, end),
			__builtin_offsetof(struct vm_range, flag),
			__builtin_offsetof(struct vm_range, memobj),
			memlock_write_lock_bridge, memlock_write_unlock_bridge,
			memlock_lookup_range_bridge, memlock_next_range_bridge,
			memlock_split_range_bridge, memlock_join_range_bridge,
			memlock_populate_bridge, memlock_log_bridge);
}

long sys_munlock(int n, ihk_mc_user_context_t *ctx)
{
	const uintptr_t start0 = ihk_mc_syscall_arg0(ctx);
	const size_t len0 = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct vm_regions *region = &thread->vm->region;

	return memlock_body_result(thread->vm, &thread->vm->memory_range_lock,
			start0, len0, region->user_start, region->user_end,
			MEMLOCK_OP_UNLOCK, ihk_mc_get_processor_id(),
			__builtin_offsetof(struct vm_range, start),
			__builtin_offsetof(struct vm_range, end),
			__builtin_offsetof(struct vm_range, flag),
			__builtin_offsetof(struct vm_range, memobj),
			memlock_write_lock_bridge, memlock_write_unlock_bridge,
			memlock_lookup_range_bridge, memlock_next_range_bridge,
			memlock_split_range_bridge, memlock_join_range_bridge,
			NULL, memlock_log_bridge);
}
#endif

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
static const struct syscall_mlockall_offsets syscall_mlockall_offsets = {
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.proc_euid_offset = __builtin_offsetof(struct process, euid),
	.proc_rlimit_offset = __builtin_offsetof(struct process, rlimit),
	.rlimit_entry_size = sizeof(((struct process *)0)->rlimit[0]),
	.memlock_resource = MCK_RLIMIT_MEMLOCK,
};
#endif

void
syscall_mlockall_log_bridge(int flags, int error)
{
	if (error == -EINVAL) {
		kprintf("mlockall(0x%x):invalid flags: EINVAL\n", flags);
		return;
	}

	if (!error) {
		kprintf("mlockall(0x%x):priv user: 0\n", flags);
		return;
	}

	if (error == -ENOMEM) {
		kprintf("mlockall(0x%x):limits exists: ENOMEM\n", flags);
		return;
	}

	kprintf("mlockall(0x%x):no lock permitted: EPERM\n", flags);
}

void
syscall_munlockall_log_bridge(int value, int error)
{
	(void)value;
	(void)error;
	kprintf("munlockall(): 0\n");
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_mlockall(int n, ihk_mc_user_context_t *ctx);
#else
long sys_mlockall(int n, ihk_mc_user_context_t *ctx)
{
	const int flags = ihk_mc_syscall_arg0(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return syscall_mlockall_body_result(thread, flags,
			&syscall_mlockall_offsets, syscall_mlockall_log_bridge);
} /* sys_mlockall() */
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_munlockall(int n, ihk_mc_user_context_t *ctx);
#else
long sys_munlockall(int n, ihk_mc_user_context_t *ctx)
{
	return syscall_munlockall_body_result(syscall_munlockall_log_bridge);
} /* sys_munlockall() */
#endif

int
remap_file_pages_callable_bridge(void *memobj)
{
	return is_callable_remap_file_pages((struct memobj *)memobj);
}

int
remap_file_pages_remap_bridge(struct process_vm *vm, struct vm_range *range,
		unsigned long start, unsigned long end, off_t off)
{
	return remap_process_memory_range(vm, range, start, end, off);
}

void
remap_file_pages_clear_host_bridge(unsigned long start, size_t size,
		int holding_lock)
{
	clear_host_pte(start, size, holding_lock);
}

void
remap_file_pages_log_bridge(const struct remap_file_pages_log_record *record)
{
	if (!record)
		return;

	if (record->event == REMAP_FILE_PAGES_LOG_ENTER) {
		dkprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x)\n",
				record->start0, record->size, record->prot,
				record->pgoff, record->flags);
	}
	else if (record->event == REMAP_FILE_PAGES_LOG_INVALID_ARGS) {
		ekprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x):"
				"invalid args\n",
				record->start0, record->size, record->prot,
				record->pgoff, record->flags);
	}
	else if (record->event == REMAP_FILE_PAGES_LOG_INVALID_VMR) {
		ekprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x):"
				"invalid VMR:[%#lx-%#lx) %#lx %p\n",
				record->start0, record->size, record->prot,
				record->pgoff, record->flags, record->range_start,
				record->range_end, record->range_flags,
				record->memobj);
	}
	else if (record->event == REMAP_FILE_PAGES_LOG_REMAP_FAILED) {
		ekprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x):"
				"remap failed %d\n",
				record->start0, record->size, record->prot,
				record->pgoff, record->flags, record->error);
	}
	else if (record->event == REMAP_FILE_PAGES_LOG_POPULATE_FAILED) {
		ekprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x):"
				"populate failed %d\n",
				record->start0, record->size, record->prot,
				record->pgoff, record->flags, record->error);
	}
	else if (record->event == REMAP_FILE_PAGES_LOG_EXIT) {
		dkprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x): %d\n",
				record->start0, record->size, record->prot,
				record->pgoff, record->flags, record->error);
	}
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_remap_file_pages(int n, ihk_mc_user_context_t *ctx);
#else
long sys_remap_file_pages(int n, ihk_mc_user_context_t *ctx)
{
	const uintptr_t start0 = ihk_mc_syscall_arg0(ctx);
	const size_t size = ihk_mc_syscall_arg1(ctx);
	const int prot = ihk_mc_syscall_arg2(ctx);
	const size_t pgoff = ihk_mc_syscall_arg3(ctx);
	const int flags = ihk_mc_syscall_arg4(ctx);
	struct thread * const thread = get_this_cpu_local_var()->current;

	return remap_file_pages_body_result(thread->vm,
			&thread->vm->memory_range_lock, start0, size, prot,
			pgoff, flags, ihk_mc_get_processor_id(),
			offsetof(struct vm_range, start),
			offsetof(struct vm_range, end),
			offsetof(struct vm_range, flag),
			offsetof(struct vm_range, memobj),
			memlock_write_lock_bridge, memlock_write_unlock_bridge,
			memlock_lookup_range_bridge,
			remap_file_pages_callable_bridge,
			remap_file_pages_remap_bridge,
			remap_file_pages_clear_host_bridge,
			memlock_populate_bridge, mprotect_flush_nfo_bridge,
			remap_file_pages_log_bridge);
}
#endif

int
mremap_extend_bridge(struct process_vm *vm, struct vm_range *range,
		unsigned long newend)
{
	return extend_up_process_memory_range(vm, range, newend);
}

int
mremap_search_bridge(size_t size, unsigned long pgshift,
		unsigned long *newstartp)
{
	uintptr_t newstart = 0;
	int error = search_free_space(size, pgshift, &newstart);

	if (newstartp)
		*newstartp = newstart;
	return error;
}

void
mremap_memobj_ref_bridge(void *memobj)
{
	memobj_ref(memobj);
}

void
mremap_memobj_unref_bridge(void *memobj)
{
	memobj_unref(memobj);
}

int
mremap_add_range_bridge(struct process_vm *vm, unsigned long start,
		unsigned long end, long pgshift, unsigned long flags,
		void *memobj, unsigned long objoff)
{
	return add_process_memory_range(vm, start, end, pgshift, flags,
			memobj, objoff, 0, NULL, NULL);
}

void
mremap_pte_lock_bridge(void *lock)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock);
}

void
mremap_pte_unlock_bridge(void *lock)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock);
}

int
mremap_move_pte_bridge(void *page_table, struct process_vm *vm,
		void *oldstart, void *newstart, size_t size,
		struct vm_range *range)
{
	return move_pte_range(page_table, vm, oldstart, newstart, size, range);
}

void
mremap_log_bridge(const struct mremap_log_record *record)
{
	if (!record)
		return;

	if (record->event == MREMAP_LOG_ENTER) {
		dkprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx)\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr);
	}
	else if (record->event == MREMAP_LOG_STRAIGHT_REJECT) {
		kprintf("sys_mremap: reject for straight range 0x%lx\n",
				record->oldaddr);
	}
	else if (record->event == MREMAP_LOG_INVALID) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):invalid. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error);
	}
	else if (record->event == MREMAP_LOG_ALLOCATE_FAILED) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"cannot allocate. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error);
	}
	else if (record->event == MREMAP_LOG_LOOKUP_FAILED) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"lookup failed. %d %p %#lx-%#lx %#lx\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error, NULL,
				record->range_start, record->range_end,
				record->range_flags);
	}
	else if (record->event == MREMAP_LOG_FIXED_MIN_ADDR) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"mmap_min_addr %#lx. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->range_start,
				record->error);
	}
	else if (record->event == MREMAP_LOG_FIXED_OVERLAP) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"fixed:overlapped. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error);
	}
	else if (record->event == MREMAP_LOG_CANNOT_RELOCATE) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"cannot relocate. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error);
	}
	else if (record->event == MREMAP_LOG_SEARCH_FAILED) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"search failed. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error);
	}
	else if (record->event == MREMAP_LOG_FIXED_MUNMAP_FAILED) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"fixed:munmap failed. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error);
	}
	else if (record->event == MREMAP_LOG_ADD_FAILED) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"add failed. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error);
	}
	else if (record->event == MREMAP_LOG_SPLIT_FAILED) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"split range failed. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error);
	}
	else if (record->event == MREMAP_LOG_MOVE_FAILED) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"move failed. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error);
	}
	else if (record->event == MREMAP_LOG_RELOCATE_MUNMAP_FAILED) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"relocate:munmap failed. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error);
	}
	else if (record->event == MREMAP_LOG_SHRINK_MUNMAP_FAILED) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"shrink:munmap failed. %d\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error);
	}
	else if (record->event == MREMAP_LOG_POPULATE_FAILED) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"populate failed. %d %#lx-%#lx\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error,
				record->lckstart, record->lckend);
	}
	else if (record->event == MREMAP_LOG_EXIT) {
		dkprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):%d %#lx\n",
				record->oldaddr, record->oldsize0,
				record->newsize0, record->flags,
				record->newaddr, record->error,
				record->error ? (unsigned long)record->error :
				record->newstart);
	}
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_mremap(int n, ihk_mc_user_context_t *ctx);
#else
long sys_mremap(int n, ihk_mc_user_context_t *ctx)
{
	const uintptr_t oldaddr = ihk_mc_syscall_arg0(ctx);
	const size_t oldsize0 = ihk_mc_syscall_arg1(ctx);
	const size_t newsize0 = ihk_mc_syscall_arg2(ctx);
	const int flags = ihk_mc_syscall_arg3(ctx);
	const uintptr_t newaddr = ihk_mc_syscall_arg4(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process_vm *vm = thread->vm;
	void *page_table = vm->address_space ? vm->address_space->page_table :
		NULL;

	return mremap_body_result(vm, &vm->memory_range_lock,
			&vm->page_table_lock, page_table, oldaddr, oldsize0,
			newsize0, flags, newaddr, vm->region.user_start,
			vm->region.user_end, (unsigned long)vm->proc->straight_va,
			vm->proc->straight_len, offsetof(struct vm_range, start),
			offsetof(struct vm_range, end),
			offsetof(struct vm_range, flag),
			offsetof(struct vm_range, pgshift),
			offsetof(struct vm_range, memobj),
			offsetof(struct vm_range, objoff),
			memlock_write_lock_bridge, memlock_write_unlock_bridge,
			memlock_lookup_range_bridge, mremap_extend_bridge,
			mprotect_flush_nfo_bridge, mremap_search_bridge,
			munmap_do_bridge, mremap_memobj_ref_bridge,
			mremap_memobj_unref_bridge, mremap_add_range_bridge,
			mremap_pte_lock_bridge, mremap_pte_unlock_bridge,
			memlock_split_range_bridge, mremap_move_pte_bridge,
			memlock_populate_bridge, mremap_log_bridge);
}
#endif

void
msync_read_lock_bridge(void *lock)
{
	ihk_rwspinlock_read_lock_noirq((ihk_rwspinlock_t *)lock);
}

void
msync_read_unlock_bridge(void *lock)
{
	ihk_rwspinlock_read_unlock_noirq((ihk_rwspinlock_t *)lock);
}

struct vm_range *
msync_lookup_range_bridge(struct process_vm *vm, unsigned long start,
		unsigned long end)
{
	return lookup_process_memory_range(vm, start, end);
}

struct vm_range *
msync_next_range_bridge(struct process_vm *vm, struct vm_range *range)
{
	return next_process_memory_range(vm, range);
}

int
msync_has_pager_bridge(void *memobj)
{
	return memobj_has_pager(memobj);
}

int
msync_sync_range_bridge(struct process_vm *vm, struct vm_range *range,
		unsigned long start, unsigned long end)
{
	return sync_process_memory_range(vm, range, start, end);
}

int
msync_invalidate_range_bridge(struct process_vm *vm, struct vm_range *range,
		unsigned long start, unsigned long end)
{
	return invalidate_process_memory_range(vm, range, start, end);
}

void
msync_log_bridge(int event, unsigned long start, size_t len, int flags,
		int error)
{
	if (event == MSYNC_LOG_ENTER) {
		dkprintf("sys_msync(%#lx,%#lx,%#x)\n", start, len, flags);
	}
	else if (event == MSYNC_LOG_INVALID_ARGS) {
		ekprintf("sys_msync(%#lx,%#lx,%#x):invalid args. %d\n",
				start, len, flags, error);
	}
	else if (event == MSYNC_LOG_INVALID_VMR) {
		ekprintf("sys_msync(%#lx,%#lx,%#x):invalid VMR %d\n",
				start, len, flags, error);
	}
	else if (event == MSYNC_LOG_LOCKED_VMR) {
		ekprintf("sys_msync(%#lx,%#lx,%#x):locked VMR %d\n",
				start, len, flags, error);
	}
	else if (event == MSYNC_LOG_UNSYNCABLE_VMR) {
		dkprintf("sys_msync(%#lx,%#lx,%#x):unsyncable VMR\n",
				start, len, flags);
	}
	else if (event == MSYNC_LOG_SYNC_FAILED) {
		ekprintf("sys_msync(%#lx,%#lx,%#x):sync failed. %d\n",
				start, len, flags, error);
	}
	else if (event == MSYNC_LOG_INVALIDATE_FAILED) {
		ekprintf("sys_msync(%#lx,%#lx,%#x):invalidate failed. %d\n",
				start, len, flags, error);
	}
	else if (event == MSYNC_LOG_EXIT) {
		dkprintf("sys_msync(%#lx,%#lx,%#x):%d\n",
				start, len, flags, error);
	}
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_msync(int n, ihk_mc_user_context_t *ctx);
#else
long sys_msync(int n, ihk_mc_user_context_t *ctx)
{
	const uintptr_t start0 = ihk_mc_syscall_arg0(ctx);
	const size_t len0 = ihk_mc_syscall_arg1(ctx);
	const int flags = ihk_mc_syscall_arg2(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process_vm *vm = thread->vm;

	return msync_body_result(vm, &vm->memory_range_lock, start0, len0,
			flags, __builtin_offsetof(struct vm_range, start),
			__builtin_offsetof(struct vm_range, end),
			__builtin_offsetof(struct vm_range, flag),
			__builtin_offsetof(struct vm_range, memobj),
			msync_read_lock_bridge, msync_read_unlock_bridge,
			msync_lookup_range_bridge, msync_next_range_bridge,
			msync_has_pager_bridge, msync_sync_range_bridge,
			msync_invalidate_range_bridge, msync_log_bridge);
} /* sys_msync() */
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_getcpu(int n, ihk_mc_user_context_t *ctx);
#else
long sys_getcpu(int n, ihk_mc_user_context_t *ctx)
{
	const uintptr_t cpup = ihk_mc_syscall_arg0(ctx);
	const uintptr_t nodep = ihk_mc_syscall_arg1(ctx);

	return syscall_getcpu_body_result(cpup, nodep,
			syscall_get_processor_id_bridge(),
			syscall_get_numa_id_bridge(), syscall_copy_to_user_bridge);
} /* sys_getcpu() */
#endif

void
syscall_mbind_write_lock_bridge(void *lock)
{
	ihk_rwspinlock_write_lock_noirq((ihk_rwspinlock_t *)lock);
}

void
syscall_mbind_write_unlock_bridge(void *lock)
{
	ihk_rwspinlock_write_unlock_noirq((ihk_rwspinlock_t *)lock);
}

struct vm_range *
syscall_mbind_lookup_range_bridge(struct process_vm *vm,
		unsigned long start, unsigned long end)
{
	return lookup_process_memory_range(vm, start, end);
}

struct vm_range_numa_policy *
syscall_mbind_policy_search_bridge(struct process_vm *vm, unsigned long addr)
{
	return vm_range_policy_search(vm, addr);
}

int
syscall_mbind_clear_range_bridge(struct process_vm *vm, unsigned long start,
		unsigned long end)
{
	return vm_policy_clear_range(vm, start, end);
}

void *
syscall_mbind_policy_alloc_bridge(size_t size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

void
syscall_mbind_policy_rb_clear_bridge(
		struct vm_range_numa_policy *range_policy)
{
	RB_CLEAR_NODE(&range_policy->policy_rb_node);
}

int
syscall_mbind_policy_insert_bridge(struct process_vm *vm,
		struct vm_range_numa_policy *range_policy)
{
	return vm_policy_insert(vm, range_policy);
}

void
syscall_mbind_log_bridge(int event, unsigned long arg0, unsigned long arg1,
		int arg2)
{
	switch (event) {
	case MBIND_LOG_NODEMASK_BITS_TOO_BIG:
		dkprintf("%s: ERROR: nodemask_bits bigger than PAGE_SIZE bits\n",
				"sys_mbind");
		break;
	case MBIND_LOG_CLAMPED:
		dkprintf("%s: WARNING: process NUMA mask bits is insufficient\n",
				"sys_mbind");
		break;
	case MBIND_LOG_INVALID_MODE_FLAGS:
		dkprintf("%s: error: invalid mode/flags combination\n",
				"sys_mbind");
		break;
	case MBIND_LOG_COPY_FROM_NUMA_MASK:
		dkprintf("%s: error: copy_from_user numa_mask\n",
				"sys_mbind");
		break;
	case MBIND_LOG_DEFAULT_MASK_NOT_EMPTY:
		dkprintf("%s: ERROR: nodemask not empty for MPOL_DEFAULT\n",
				"sys_mbind");
		break;
	case MBIND_LOG_NODEMASK_NOT_SPECIFIED:
		dkprintf("%s: ERROR: nodemask not specified\n", "sys_mbind");
		break;
	case MBIND_LOG_NODE_TOO_LARGE:
		dkprintf("%s: %lu is bigger than # of NUMA nodes\n",
				"sys_mbind", arg1);
		break;
	case MBIND_LOG_INVALID_RANGE:
		dkprintf("%s: ERROR: range is invalid\n", "sys_mbind");
		break;
	case MBIND_LOG_CLEAR_POLICY_RANGE:
		ekprintf("%s: ERROR: clear policy_range\n", "sys_mbind");
		break;
	case MBIND_LOG_ALLOC_POLICY:
		dkprintf("%s: error allocating range_policy\n", "sys_mbind");
		break;
	case MBIND_LOG_INSERT_POLICY:
		kprintf("%s: ERROR: could not insert range: %d\n",
				"sys_mbind", arg2);
		break;
	default:
		dkprintf("%s: event=%d arg0=%#lx arg1=%#lx arg2=%d\n",
				"sys_mbind", event, arg0, arg1, arg2);
		break;
	}
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
void
syscall_mbind_entry_log_bridge(unsigned long addr, unsigned long len,
		int mode, unsigned long nodemask_addr, unsigned long flags)
{
	dkprintf("%s: addr: 0x%lx, len: %lu, mode: 0x%x, "
		"nodemask: 0x%lx, flags: %lx\n",
		"sys_mbind", addr, len, mode, nodemask_addr, flags);
}

long sys_mbind(int n, ihk_mc_user_context_t *ctx);
#else
long sys_mbind(int n, ihk_mc_user_context_t *ctx)
{
	unsigned long addr = ihk_mc_syscall_arg0(ctx);
	unsigned long len = ihk_mc_syscall_arg1(ctx);
	int mode = ihk_mc_syscall_arg2(ctx);
	unsigned long *nodemask =
		(unsigned long *)ihk_mc_syscall_arg3(ctx);
	unsigned long maxnode = ihk_mc_syscall_arg4(ctx);
	unsigned flags = ihk_mc_syscall_arg5(ctx);
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;
	unsigned long nodemask_bits = 0;
	int mode_flags = 0;
	int error = 0;
	int bit;
	struct vm_range *range;
	struct vm_range_numa_policy *range_policy, *range_policy_iter = NULL;
	unsigned long numa_mask[(((PROCESS_NUMA_MASK_BITS) + BITS_PER_LONG - 1) / BITS_PER_LONG)];

	dkprintf("%s: addr: 0x%lx, len: %lu, mode: 0x%x, "
		"nodemask: 0x%lx, flags: %lx\n",
		__FUNCTION__,
		addr, len, mode, nodemask, flags);

	/* No bind support for straight mapped processes */
	if (get_this_cpu_local_var()->current->proc->straight_va) {
		return 0;
	}

	/* Validate arguments */
	error = mbind_prepare_range(addr, len, &len);
	if (error) {
		return error;
	}

#ifdef ENABLE_FUGAKU_HACKS
	return 0;
#endif

	memset(numa_mask, 0, sizeof(numa_mask));

	error = mempolicy_nodemask_bits_result(maxnode, &nodemask_bits);
	if (error) {
		dkprintf("%s: ERROR: nodemask_bits bigger than PAGE_SIZE bits\n",
			__FUNCTION__);
		goto out;
	}
	if (mempolicy_nodemask_bits_is_clamped(maxnode)) {
		dkprintf("%s: WARNING: process NUMA mask bits is insufficient\n",
			__FUNCTION__);
	}

	error = mbind_mode_flags_result(mode, flags, &mode_flags, &mode);
	if (error) {
		dkprintf("%s: error: invalid mode/flags combination\n",
				__FUNCTION__);
		goto out;
	}
	(void)mode_flags;
	if (!mempolicy_mode_is_supported(mode)) {
		error = -EINVAL;
		goto out;
	}

	switch (mode) {
		case MPOL_DEFAULT:
			if (nodemask && nodemask_bits) {
				error = copy_from_user(numa_mask, nodemask,
						(nodemask_bits >> 3));
				if (error) {
					dkprintf("%s: error: copy_from_user numa_mask\n",
							__FUNCTION__);
					error = -EFAULT;
					goto out;
				}

				if (!bitmap_empty(numa_mask, nodemask_bits)) {
					dkprintf("%s: ERROR: nodemask not empty for MPOL_DEFAULT\n",
							__FUNCTION__);
					error = -EINVAL;
					goto out;
				}
			}
			break;

		case MPOL_BIND:
		case MPOL_INTERLEAVE:
		case MPOL_PREFERRED:
			/* Special case for MPOL_PREFERRED with empty nodemask */
			if (mode == MPOL_PREFERRED && !nodemask) {
				error = 0;
				break;
			}

			if (flags & MPOL_MF_STRICT) {
				error = -EIO;
				goto out;
			}

			error = copy_from_user(numa_mask, nodemask,
					(nodemask_bits >> 3));
			if (error) {
				error = -EFAULT;
				goto out;
			}

			if (!nodemask || bitmap_empty(numa_mask, nodemask_bits)) {
				dkprintf("%s: ERROR: nodemask not specified\n",
						__FUNCTION__);
				error = -EINVAL;
				goto out;
			}

			/* Verify NUMA mask */
			for ((bit) = find_first_bit((numa_mask), (maxnode < PROCESS_NUMA_MASK_BITS ?
					maxnode : PROCESS_NUMA_MASK_BITS)); (bit) < (maxnode < PROCESS_NUMA_MASK_BITS ?
					maxnode : PROCESS_NUMA_MASK_BITS); (bit) = find_next_bit((numa_mask), (maxnode < PROCESS_NUMA_MASK_BITS ?
					maxnode : PROCESS_NUMA_MASK_BITS), (bit) + 1)) {
				if (bit >= ihk_mc_get_nr_numa_nodes()) {
					dkprintf("%s: %d is bigger than # of NUMA nodes\n",
						__FUNCTION__, bit);
					error = -EINVAL;
					goto out;
				}
			}

			break;

		default:
			error = -EINVAL;
			goto out;
	}

	/* Validate address range */
	ihk_rwspinlock_write_lock_noirq(&vm->memory_range_lock);

	range = lookup_process_memory_range(vm, addr, addr + len);
	if (!range) {
		dkprintf("%s: ERROR: range is invalid\n", __FUNCTION__);
		error = -EFAULT;
		goto unlock_out;
	}

	/* Do the actual policy setting */
	switch (mode) {
	/*
	 * Man page claims MPOL_DEFAULT should remove any range specific
	 * policies so that process wise policy will be used. LTP on the
	 * other hand seems to test if MPOL_DEFAULT is set as a range policy.
	 * MPOL_DEFAULT thus behaves the same as the rest of the policies
	 * for now.
	 */
#if 0
		case MPOL_DEFAULT:
			/* Delete or adjust any overlapping range settings */
			for (range_policy_iter = ((typeof(*range_policy_iter) *)((char *)((&vm->vm_range_numa_policy_list)->next) - offsetof(typeof(*range_policy_iter), list))), range_policy_next = ((typeof(*range_policy_iter) *)((char *)(range_policy_iter->list.next) - offsetof(typeof(*range_policy_iter), list))); &range_policy_iter->list != (&vm->vm_range_numa_policy_list); range_policy_iter = range_policy_next, range_policy_next = ((typeof(*range_policy_next) *)((char *)(range_policy_next->list.next) - offsetof(typeof(*range_policy_next), list)))) {
				int keep = 0;
				unsigned long orig_end = range_policy_iter->end;

				if (range_policy_iter->end < addr ||
					range_policy_iter->start > addr + len) {
					continue;
				}

				/* Do we need to keep the front? */
				if (range_policy_iter->start < addr) {
					range_policy_iter->end = addr;
					keep = 1;
				}

				/* Do we need to keep the end? */
				if (orig_end > addr + len) {
					/* Are we keeping front already? */
					if (keep) {
						/* Add a new entry after */
						range_policy = kmalloc_tracked(sizeof(*range_policy), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
						if (!range_policy) {
							kprintf("%s: error allocating range_policy\n",
								__FUNCTION__);
							error = -ENOMEM;
							goto unlock_out;
						}

						memcpy(range_policy, range_policy_iter,
								sizeof(*range_policy));
						range_policy->start = addr + len;
						range_policy->end = orig_end;
						list_add(&range_policy->list,
								&range_policy_iter->list);
					}
					else {
						range_policy_iter->start = addr + len;
						keep = 1;
					}
				}

				if (!keep) {
					list_del(&range_policy_iter->list);
					kfree_tracked(range_policy_iter, __FILE__, __LINE__);
				}
			}

			break;
#endif
		case MPOL_DEFAULT:
		case MPOL_BIND:
		case MPOL_INTERLEAVE:
		case MPOL_PREFERRED:
			/* Check if same range is existing */
			range_policy_iter = vm_range_policy_search(vm, addr);
			if (range_policy_iter) {
					if (range_policy_iter->start == addr &&
					range_policy_iter->end == addr + len) {
					/* same range */
					range_policy = range_policy_iter;
					goto mbind_update_only;
				}
			}

			/* Clear target range */
			error = vm_policy_clear_range(vm, addr, addr + len);
			if (error) {
				ekprintf("%s: ERROR: clear policy_range\n",
						__func__);
				goto unlock_out;
			}

			/* Add a new entry */
			range_policy = kmalloc_tracked(sizeof(struct vm_range_numa_policy), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
			if (!range_policy) {
				dkprintf("%s: error allocating range_policy\n",
						__FUNCTION__);
				error = -ENOMEM;
				goto unlock_out;
			}

			RB_CLEAR_NODE(&range_policy->policy_rb_node);
			range_policy->start = addr;
			range_policy->end = addr + len;

			error = vm_policy_insert(vm, range_policy);
			if (error) {
				kprintf("%s: ERROR: could not insert range: %d\n",__FUNCTION__, error);
				goto unlock_out;
			}

mbind_update_only:
			if (mode == MPOL_DEFAULT) {
				memset(range_policy->numa_mask, 0, sizeof(numa_mask));
				for (bit = 0; bit < ihk_mc_get_nr_numa_nodes(); ++bit) {
					set_bit(bit, range_policy->numa_mask);
				}
			}
			else {
				memcpy(range_policy->numa_mask, &numa_mask,
					sizeof(numa_mask));
			}
			range_policy->numa_mem_policy = mode;
			if (mode == MPOL_INTERLEAVE) {
				range_policy->il_prev =
						PROCESS_NUMA_MASK_BITS - 1;
			}

			break;

		default:
			error = -EINVAL;
			goto unlock_out;
	}

	error = 0;

unlock_out:
	ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
out:
	return error;
} /* sys_mbind() */
#endif /* MCKERNEL_RUST_SYSCALL_POLICY_HELPERS */

void
syscall_set_mempolicy_log_bridge(int event, int value, int pid)
{
	switch (event) {
	case SET_MEMPOLICY_LOG_NODEMASK_BITS_TOO_BIG:
		dkprintf("%s: ERROR: nodemask_bits bigger than PAGE_SIZE bits\n",
				"sys_set_mempolicy");
		break;
	case SET_MEMPOLICY_LOG_CLAMPED:
		dkprintf("%s: WARNING: process NUMA mask bits is insufficient\n",
				"sys_set_mempolicy");
		break;
	case SET_MEMPOLICY_LOG_DEFAULT_MASK_NOT_EMPTY:
		dkprintf("%s: ERROR: nodemask not empty for MPOL_DEFAULT\n",
				"sys_set_mempolicy");
		break;
	case SET_MEMPOLICY_LOG_NODEMASK_NOT_SPECIFIED:
		dkprintf("%s: ERROR: nodemask not specified\n",
				"sys_set_mempolicy");
		break;
	case SET_MEMPOLICY_LOG_NODE_TOO_LARGE:
		dkprintf("%s: %d is bigger than # of NUMA nodes\n",
				"sys_set_mempolicy", value);
		break;
	case SET_MEMPOLICY_LOG_INVALID_NODEMASK:
		dkprintf("%s: ERROR: invalid nodemask\n", "sys_set_mempolicy");
		break;
	case SET_MEMPOLICY_LOG_SET:
		dkprintf("%s: %s set for PID %d\n",
				"sys_set_mempolicy",
				value == MPOL_DEFAULT ? "MPOL_DEFAULT" :
				value == MPOL_INTERLEAVE ? "MPOL_INTERLEAVE" :
				value == MPOL_BIND ? "MPOL_BIND" :
				value == MPOL_PREFERRED ? "MPOL_PREFERRED" :
				"unknown", pid);
		break;
	default:
		dkprintf("%s: event=%d value=%d pid=%d\n",
				"sys_set_mempolicy", event, value, pid);
		break;
	}
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_set_mempolicy(int n, ihk_mc_user_context_t *ctx);
#else
long sys_set_mempolicy(int n, ihk_mc_user_context_t *ctx)
{
	int mode = ihk_mc_syscall_arg0(ctx);
	unsigned long nodemask_addr = ihk_mc_syscall_arg1(ctx);
	unsigned long maxnode = ihk_mc_syscall_arg2(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	return set_mempolicy_body_result(mode, nodemask_addr, maxnode,
			thread->vm, ihk_mc_get_nr_numa_nodes(), thread->proc->pid,
			syscall_copy_from_user_bridge,
			syscall_set_mempolicy_log_bridge);
} /* sys_set_mempolicy() */
#endif

void
syscall_get_mempolicy_read_lock_bridge(void *lock)
{
	ihk_rwspinlock_read_lock_noirq((ihk_rwspinlock_t *)lock);
}

void
syscall_get_mempolicy_read_unlock_bridge(void *lock)
{
	ihk_rwspinlock_read_unlock_noirq((ihk_rwspinlock_t *)lock);
}

struct vm_range *
syscall_get_mempolicy_lookup_range_bridge(struct process_vm *vm,
		unsigned long start, unsigned long end)
{
	return lookup_process_memory_range(vm, start, end);
}

struct vm_range_numa_policy *
syscall_get_mempolicy_policy_search_bridge(struct process_vm *vm,
		unsigned long addr)
{
	return vm_range_policy_search(vm, addr);
}

int
syscall_get_mempolicy_lookup_node_bridge(struct process_vm *vm, void *addr)
{
	extern int lookup_node(struct process_vm *vm, void *addr);

	return lookup_node(vm, addr);
}

void
syscall_get_mempolicy_log_bridge(int event, unsigned long addr, int value)
{
	switch (event) {
	case 1:
		dkprintf("%s: WARNING: process NUMA mask bits is insufficient\n",
				"sys_get_mempolicy");
		break;
	case 2:
		dkprintf("%s: ERROR: range is invalid\n", "sys_get_mempolicy");
		break;
	default:
		dkprintf("%s: event=%d addr=%#lx value=%d\n",
				"sys_get_mempolicy", event, addr, value);
		break;
	}
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_get_mempolicy(int n, ihk_mc_user_context_t *ctx);
#else
long sys_get_mempolicy(int n, ihk_mc_user_context_t *ctx)
{
	int *mode = (int *)ihk_mc_syscall_arg0(ctx);
	unsigned long *nodemask =
		(unsigned long *)ihk_mc_syscall_arg1(ctx);
	unsigned long maxnode = ihk_mc_syscall_arg2(ctx);
	unsigned long addr = ihk_mc_syscall_arg3(ctx);
	unsigned long flags = ihk_mc_syscall_arg4(ctx);
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;

	return get_mempolicy_body_result((unsigned long)mode,
			(unsigned long)nodemask, maxnode, addr, (int)flags, vm,
			ihk_mc_get_nr_numa_nodes(), syscall_copy_to_user_bridge,
			syscall_get_mempolicy_lookup_node_bridge,
			syscall_get_mempolicy_read_lock_bridge,
			syscall_get_mempolicy_read_unlock_bridge,
			syscall_get_mempolicy_lookup_range_bridge,
			syscall_get_mempolicy_policy_search_bridge,
			syscall_get_mempolicy_log_bridge);
} /* sys_get_mempolicy() */
#endif

void
syscall_migrate_pages_log_bridge(void)
{
	dkprintf("sys_migrate_pages\n");
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_migrate_pages(int n, ihk_mc_user_context_t *ctx);
#else
long sys_migrate_pages(int n, ihk_mc_user_context_t *ctx)
{
	syscall_migrate_pages_log_bridge();
	return migrate_pages_body_result();
} /* sys_migrate_pages() */
#endif

static int
move_pages_verify_bridge(struct process_vm *vm, unsigned long addr,
		size_t bytes)
{
	return verify_process_vm(vm, (const void *)addr, bytes);
}

static int
move_pages_get_nr_nodes_bridge(void)
{
	return ihk_mc_get_nr_numa_nodes();
}

static void
move_pages_page_table_lock_bridge(void *lock)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock);
}

static void
move_pages_page_table_unlock_bridge(void *lock)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock);
}

static int
move_pages_smp_call_bridge(void *cpu_set, smp_func_t handler, void *arg)
{
	return smp_call_func((cpu_set_t *)cpu_set, handler, arg);
}

static void
move_pages_log_bridge(int event, unsigned long value, int error)
{
	(void)error;

	if (event == MOVE_PAGES_LOG_UNSUPPORTED_PID) {
		kprintf("%s: ERROR: only self (pid == 0) is supported\n",
				"sys_move_pages");
	}
	else if (event == MOVE_PAGES_LOG_UNSUPPORTED_MOVE_ALL) {
		kprintf("%s: ERROR: MPOL_MF_MOVE_ALL not supported\n",
				"sys_move_pages");
	}
	else if (event == MOVE_PAGES_LOG_INIT_MALLOC) {
		kprintf("%s: init malloc: %lu \n", "sys_move_pages", value);
	}
	else if (event == MOVE_PAGES_LOG_INIT_VERIFY) {
		kprintf("%s: init verify: %lu \n", "sys_move_pages", value);
	}
	else if (event == MOVE_PAGES_LOG_PARALLEL) {
		kprintf("%s: parallel: %lu \n", "sys_move_pages", value);
	}
}

long sys_move_pages(int n, ihk_mc_user_context_t *ctx)
{
	extern int move_pages_smp_handler(int cpu_index, int nr_cpus, void *arg);
	int pid = ihk_mc_syscall_arg0(ctx);
	unsigned long count = ihk_mc_syscall_arg1(ctx);
	const void **user_virt_addr = (const void **)ihk_mc_syscall_arg2(ctx);
	const int *user_nodes = (const int *)ihk_mc_syscall_arg3(ctx);
	int *user_status = (int *)ihk_mc_syscall_arg4(ctx);
	int flags = ihk_mc_syscall_arg5(ctx);
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;

	return move_pages_body_result(pid, count,
			(unsigned long)user_virt_addr,
			(unsigned long)user_nodes, (unsigned long)user_status,
			flags, vm, &vm->page_table_lock,
			&get_this_cpu_local_var()->current->cpu_set,
			get_this_cpu_local_var()->current->proc, IHK_MC_AP_NOWAIT,
			sizeof(void *), sizeof(int), sizeof(pte_t),
			sizeof(unsigned long), move_pages_verify_bridge,
			syscall_copy_from_user_bridge, syscall_copy_to_user_bridge,
			syscall_alloc_bridge, syscall_mckfd_free_bridge,
			move_pages_get_nr_nodes_bridge,
			move_pages_page_table_lock_bridge,
			move_pages_page_table_unlock_bridge,
			move_pages_smp_call_bridge, move_pages_smp_handler,
			syscall_rdtsc_bridge, move_pages_log_bridge);
}

extern int do_process_vm_read_writev(int pid,
	const struct iovec *local_iov,
	unsigned long liovcnt,
	const struct iovec *remote_iov,
	unsigned long riovcnt,
	unsigned long flags,
	int op);

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_process_vm_writev(int n, ihk_mc_user_context_t *ctx);
long sys_process_vm_readv(int n, ihk_mc_user_context_t *ctx);
#else
long sys_process_vm_writev(int n, ihk_mc_user_context_t *ctx)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	const struct iovec *local_iov = 
		(const struct iovec *)ihk_mc_syscall_arg1(ctx);
	unsigned long liovcnt = ihk_mc_syscall_arg2(ctx);
	const struct iovec *remote_iov = 
		(const struct iovec *)ihk_mc_syscall_arg3(ctx);
	unsigned long riovcnt = ihk_mc_syscall_arg4(ctx);
	unsigned long flags = ihk_mc_syscall_arg5(ctx);

	return process_vm_rw_body_result(pid, local_iov, liovcnt,
		remote_iov, riovcnt, flags, PROCESS_VM_WRITE,
		do_process_vm_read_writev);
}

long sys_process_vm_readv(int n, ihk_mc_user_context_t *ctx)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	const struct iovec *local_iov = 
		(const struct iovec *)ihk_mc_syscall_arg1(ctx);
	unsigned long liovcnt = ihk_mc_syscall_arg2(ctx);
	const struct iovec *remote_iov = 
		(const struct iovec *)ihk_mc_syscall_arg3(ctx);
	unsigned long riovcnt = ihk_mc_syscall_arg4(ctx);
	unsigned long flags = ihk_mc_syscall_arg5(ctx);

	return process_vm_rw_body_result(pid, local_iov, liovcnt,
		remote_iov, riovcnt, flags, PROCESS_VM_READ,
		do_process_vm_read_writev);
}
#endif

#ifdef DCFA_KMOD

#ifdef CMD_DCFA
extern int ibmic_cmd_syscall(char *uargs);
extern void ibmic_cmd_exit(int status);
#endif

#ifdef CMD_DCFAMPI
extern int dcfampi_cmd_syscall(char *uargs);
#endif

static int (*mod_call_table[]) (char *) = {
#ifdef CMD_DCFA
		[1] = ibmic_cmd_syscall,
#endif
#ifdef CMD_DCFAMPI
		[2] = dcfampi_cmd_syscall,
#endif
};

static void (*mod_exit_table[]) (int) = {
#ifdef CMD_DCFA
		[1] = ibmic_cmd_exit,
#endif
#ifdef CMD_DCFAMPI
		[2] = NULL,
#endif
};

long sys_mod_call(int n, ihk_mc_user_context_t *ctx) {
	int mod_id;
	unsigned long long uargs;

	mod_id = ihk_mc_syscall_arg0(ctx);
	uargs = ihk_mc_syscall_arg1(ctx);

	dkprintf("mod_call id:%d, uargs=0x%llx, type=%s, command=%x\n", mod_id, uargs, mod_id==1?"ibmic":"dcfampi", *((uint32_t*)(((char*)uargs)+0)));

	if(mod_call_table[mod_id])
		return mod_call_table[mod_id]((char*)uargs);

	kprintf("ERROR! undefined mod_call id:%d\n", mod_id);

	return -ENOSYS;
}

static void do_mod_exit(int status){
	int i;
	for(i=1; i<=2; i++){
		if(mod_exit_table[i])
			mod_exit_table[i](status);
	}
}
#endif

extern void save_uctx(void *, void *);

/* TODO: use copy_from_user() */
int util_show_syscall_profile()
{
	int i;
	struct uti_desc *desc = (struct uti_desc *)uti_desc;

	kprintf("Syscall stats for offloaded thread:\n");
	for (i = 0; i < 512; i++) {
		if (desc->syscalls[i]) {
			kprintf("nr=%d #called=%ld\n", i, desc->syscalls[i]);
		}
	}
	
	kprintf("Syscall stats for other threads:\n");
	for (i = 0; i < 512; i++) {
		if (desc->syscalls2[i]) {
			kprintf("nr=%d #called=%ld\n", i, desc->syscalls2[i]);
		}
	}

	return 0;
}

int util_thread(struct uti_attr *arg)
{
	struct uti_ctx *rctx = NULL;
	unsigned long rp_rctx;
	struct uti_info *uti_info = NULL;
	struct syscall_request request IHK_DMA_ALIGN;
	long rc;
	struct thread *thread = get_this_cpu_local_var()->current;
	struct kuti_attr {
		long parent_cpuid;
		struct uti_attr attr;
	} kattr;

	thread->uti_state = UTI_STATE_PROLOGUE;

	rctx = kmalloc_tracked(sizeof(struct uti_ctx), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (!rctx) {
		rc = -ENOMEM;
		goto out;
	}
	rp_rctx = virt_to_phys((void *)rctx);
	save_uctx((void *)rctx->ctx, NULL);

	/* Create a information for Linux thread */
	uti_info = kmalloc_tracked(sizeof(struct uti_info), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (!uti_info) {
		rc = -ENOMEM;
		goto out;
	}
	/* clv info */
	uti_info->thread_va = (unsigned long)get_this_cpu_local_var()->current;
	uti_info->uti_futex_resp_pa = virt_to_phys((void *)get_this_cpu_local_var()->uti_futex_resp);
	uti_info->ikc2linux_pa = virt_to_phys((void *)get_this_cpu_local_var()->ikc2linux);

	/* thread info */
	uti_info->tid = thread->tid;
	uti_info->cpu = ihk_mc_get_processor_id();
	uti_info->status_pa = virt_to_phys((void *)&thread->status);
	uti_info->spin_sleep_lock_pa = virt_to_phys((void *)&thread->spin_sleep_lock);
	uti_info->spin_sleep_pa = virt_to_phys((void *)&thread->spin_sleep);
	uti_info->vm_pa = virt_to_phys((void *)thread->vm);
	uti_info->futex_q_pa = virt_to_phys((void *)&thread->futex_q);

	/* global info */
	uti_info->mc_idle_halt = idle_halt;
	uti_info->futex_queue_pa = virt_to_phys((void *)get_futex_queues());

	request.number = __NR_sched_setaffinity;
	request.args[0] = 0;
	request.args[1] = rp_rctx;
	request.args[2] = 0;
	if (arg) {
		memcpy(&kattr.attr, arg, sizeof(struct uti_attr));
		kattr.parent_cpuid = thread->parent_cpuid;
		request.args[2] = virt_to_phys(&kattr);
	}
	request.args[3] = (unsigned long)uti_info;
	request.args[4] = uti_desc;
	thread->uti_state = UTI_STATE_RUNNING_IN_LINUX;
	rc = do_syscall(&request, ihk_mc_get_processor_id());
	dkprintf("%s: returned from do_syscall,tid=%d,rc=%lx\n", __FUNCTION__, thread->tid, rc);

	thread->uti_state = UTI_STATE_EPILOGUE;

	util_show_syscall_profile();

	/* Save it before freed */
	thread->uti_refill_tid = rctx->uti_refill_tid;
	dkprintf("%s: mcexec worker tid=%d\n", __FUNCTION__, thread->uti_refill_tid);
	
	kfree_tracked(rctx, __FILE__, __LINE__);
	rctx = NULL;

	kfree_tracked(uti_info, __FILE__, __LINE__);
	uti_info = NULL;

	if (rc >= 0) {
		if (rc & 0x100000000) { /* exit_group */
			dkprintf("%s: exit_group, tid=%d,rc=%lx\n", __FUNCTION__, thread->tid, rc);
			thread->proc->nohost = 1;
			terminate((rc >> 8) & 255, rc & 255);
		} else {
			/* exit or killed-by-signal detected */
			dkprintf("%s: exit or killed by signal, pid=%d,tid=%d,rc=%lx\n", __FUNCTION__, thread->proc->pid, thread->tid, rc);
			do_exit(rc);
		}
	} else if (syscall_proxy_dead_result(rc)) {
		/* tracer is not working and /dev/mcosX has detected exit of mcexec process */
		kprintf("%s: release_handler,pid=%d,tid=%d,rc=%lx\n", __FUNCTION__, thread->proc->pid, thread->tid, rc);
		thread->proc->nohost = 1;
		do_exit(rc);
	} else {
		kprintf("%s: ERROR: do_syscall() failed (%ld)\n", __FUNCTION__, rc);
	}

 out:
	kfree_tracked(rctx, __FILE__, __LINE__);
	kfree_tracked(uti_info, __FILE__, __LINE__);

	return rc;
}

long
syscall_util_thread_bridge(void *arg)
{
	return util_thread(arg);
}

void
utilthr_migrate()
{
	struct thread *thread = get_this_cpu_local_var()->current;

	/* Don't inherit mod_clone */
	if (thread->mod_clone == SPAWNING_TO_REMOTE) {
		thread->mod_clone = SPAWN_TO_LOCAL;
		util_thread(thread->mod_clone_arg);
	}
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_util_migrate_inter_kernel(int n, ihk_mc_user_context_t *ctx);
#else
long sys_util_migrate_inter_kernel(int n, ihk_mc_user_context_t *ctx)
{
	struct uti_attr *arg = (void *)ihk_mc_syscall_arg0(ctx);
	struct uti_attr kattr;

	return util_migrate_inter_kernel_body_result((unsigned long)arg, &kattr,
			sizeof(kattr), syscall_copy_from_user_bridge,
			syscall_util_thread_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
void
syscall_util_indicate_clone_disabled_bridge(void)
{
	kprintf("%s: error: --enable-uti mcexec option not specified\n",
			"sys_util_indicate_clone");
}

long sys_util_indicate_clone(int n, ihk_mc_user_context_t *ctx);
#else
long sys_util_indicate_clone(int n, ihk_mc_user_context_t *ctx)
{
	int mod = (int)ihk_mc_syscall_arg0(ctx);
	struct uti_attr *arg = (void *)ihk_mc_syscall_arg1(ctx);
	struct thread *thread = get_this_cpu_local_var()->current;

	if (!thread->proc->enable_uti) {
		kprintf("%s: error: --enable-uti mcexec option not specified\n",
			__func__);
	}

	return util_indicate_clone_body_result(thread, mod, (unsigned long)arg,
			sizeof(struct uti_attr), IHK_MC_AP_NOWAIT,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, enable_uti),
			__builtin_offsetof(struct thread, mod_clone),
			__builtin_offsetof(struct thread, mod_clone_arg),
			syscall_copy_from_user_bridge,
			syscall_mbind_policy_alloc_bridge,
			syscall_mckfd_free_bridge);
}
#endif

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_get_system(int n, ihk_mc_user_context_t *ctx)
{
	return get_system_body_result();
}
#endif

/*
 * swapoout(const char *filename, void *workarea, size_t size)
 */
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
void
syscall_swapout_log_bridge(const void *fname, void *buf, size_t size, int flag)
{
	dkprintf("[%d]swapout(%lx,%lx,%lx,%ld)\n",
			ihk_mc_get_processor_id(), (unsigned long)fname,
			(unsigned long)buf, (unsigned long)size, (long)flag);
}

long sys_swapout(int n, ihk_mc_user_context_t *ctx);
#else
long sys_swapout(int n, ihk_mc_user_context_t *ctx)
{
	extern int do_pageout(const char*, void*, size_t, int);
	extern int do_pagein(int);
	char	*fname = (char *)ihk_mc_syscall_arg0(ctx);
	char	*buf = (char *)ihk_mc_syscall_arg1(ctx);
	size_t	size = (size_t)ihk_mc_syscall_arg2(ctx);
	int	flag = (int)ihk_mc_syscall_arg3(ctx);
	ihk_mc_user_context_t ctx0;

	dkprintf("[%d]swapout(%lx,%lx,%lx,%ld)\n",
		 ihk_mc_get_processor_id(), fname, buf, size, flag);

	return swapout_body_result(fname, buf, size, flag, __NR_swapout, &ctx0,
			do_pageout, do_pagein, syscall_forward_context_bridge);
}
#endif

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_linux_mlock(int n, ihk_mc_user_context_t *ctx)
{
	const uintptr_t addr = ihk_mc_syscall_arg0(ctx);
	const size_t len = ihk_mc_syscall_arg1(ctx);

	kprintf("linux_mlock: %p %ld\n", (void*) addr, len);
	return linux_mlock_body_result(addr, len, 802,
			syscall_do_syscall2_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
void
syscall_linux_mlock_log_bridge(unsigned long addr, unsigned long len)
{
	kprintf("linux_mlock: %p %ld\n", (void *)addr, len);
}
#endif

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_linux_spawn(int n, ihk_mc_user_context_t *ctx)
{
	return linux_spawn_body_result(__NR_linux_spawn, ctx,
			syscall_forward_context_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_suspend_threads(int n, ihk_mc_user_context_t *ctx);
#else
long sys_suspend_threads(int n, ihk_mc_user_context_t *ctx)
{
	struct thread *mythread = get_this_cpu_local_var()->current;

	return threads_signal_body_result(mythread, SIGSTOP, 1,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, pid),
			__builtin_offsetof(struct process, threads_list),
			__builtin_offsetof(struct thread, tid),
			__builtin_offsetof(struct thread, status),
			__builtin_offsetof(struct thread, siblings_list),
			syscall_do_kill_thread_bridge,
			syscall_cpu_pause_bridge);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_resume_threads(int n, ihk_mc_user_context_t *ctx);
#else
long sys_resume_threads(int n, ihk_mc_user_context_t *ctx)
{
	struct thread *mythread = get_this_cpu_local_var()->current;

	return threads_signal_body_result(mythread, SIGCONT, 0,
			__builtin_offsetof(struct thread, proc),
			__builtin_offsetof(struct process, pid),
			__builtin_offsetof(struct process, threads_list),
			__builtin_offsetof(struct thread, tid),
			__builtin_offsetof(struct thread, status),
			__builtin_offsetof(struct thread, siblings_list),
			syscall_do_kill_thread_bridge,
			syscall_cpu_pause_bridge);
}
#endif

#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long sys_util_register_desc(int n, ihk_mc_user_context_t *ctx)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	unsigned long desc = ihk_mc_syscall_arg0(ctx);

	dkprintf("%s: tid=%d,uti_desc=%lx\n", __FUNCTION__, thread->tid, desc);
	return util_register_desc_body_result(desc, &uti_desc);
}
#endif

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
void
syscall_util_register_desc_log_bridge(int tid, unsigned long desc)
{
	dkprintf("%s: tid=%d,uti_desc=%lx\n", "sys_util_register_desc",
			tid, desc);
}
#endif

void
reset_cputime()
{
	struct thread *thread;

	if(clv == NULL)
		return;

	if(!(thread = get_this_cpu_local_var()->current))
		return;

	thread->base_tsc = 0;
}

void
set_cputime(enum set_cputime_mode mode)
{
	struct thread *thread;
	unsigned long tsc;	
	struct cpu_local_var *v;
	struct ihk_os_cpu_monitor *monitor;
	unsigned long irq_flags = 0;

	if(clv == NULL)
		return;

	v = get_this_cpu_local_var();
	if(!(thread = v->current))
		return;
	if(thread == &v->idle)
		return;
	monitor = v->monitor;
	if (mode == CPUTIME_MODE_K2U) {
		monitor->status = IHK_OS_MONITOR_USER;
	}
	else if (mode == CPUTIME_MODE_U2K) {
		monitor->counter++;
		monitor->status = IHK_OS_MONITOR_KERNEL;
	}

	if(!gettime_local_support){
		thread->times_update = 1;
		return;
	}

	irq_flags = cpu_disable_interrupt_save();
	tsc = rdtsc();
	if(thread->base_tsc != 0){
		unsigned long dtsc = tsc - thread->base_tsc;
		struct timespec dts;

		tsc_to_ts(dtsc, &dts);
		if (mode == CPUTIME_MODE_U2K) {
			thread->user_tsc += dtsc;
			v->rusage->user_tsc += dtsc;
			ts_add(&thread->itimer_virtual_value, &dts);
			ts_add(&thread->itimer_prof_value, &dts);
		}
		else{
			thread->system_tsc += dtsc;
			v->rusage->system_tsc += dtsc;
			ts_add(&thread->itimer_prof_value, &dts);
		}
	}

	thread->base_tsc = tsc;

	thread->times_update = 1;
	thread->in_kernel = (int)mode;

	if(thread->itimer_enabled){
		struct timeval tv;
		int ev = 0;

		if(thread->itimer_virtual.it_value.tv_sec != 0 ||
		   thread->itimer_virtual.it_value.tv_usec){
			ts_to_tv(&tv, &thread->itimer_virtual_value);
			tv_sub(&tv, &thread->itimer_virtual.it_value);
			if(tv.tv_sec > 0 ||
			   (tv.tv_sec == 0 &&
			    tv.tv_usec > 0)){
				thread->itimer_virtual_value.tv_sec = 0;
				thread->itimer_virtual_value.tv_nsec = 0;
				thread->itimer_virtual.it_value.tv_sec =
				    thread->itimer_virtual.it_interval.tv_sec;
				thread->itimer_virtual.it_value.tv_usec =
				    thread->itimer_virtual.it_interval.tv_usec;
				do_kill(thread, thread->proc->pid, thread->tid,
				        SIGVTALRM, NULL, 0);
				ev = 1;
			}
		}

		if(thread->itimer_prof.it_value.tv_sec != 0 ||
		   thread->itimer_prof.it_value.tv_usec){
			ts_to_tv(&tv, &thread->itimer_prof_value);
			tv_sub(&tv, &thread->itimer_prof.it_value);
			if(tv.tv_sec > 0 ||
			   (tv.tv_sec == 0 &&
			    tv.tv_usec > 0)){
				thread->itimer_prof_value.tv_sec = 0;
				thread->itimer_prof_value.tv_nsec = 0;
				thread->itimer_prof.it_value.tv_sec =
				    thread->itimer_prof.it_interval.tv_sec;
				thread->itimer_prof.it_value.tv_usec =
				    thread->itimer_prof.it_interval.tv_usec;
				do_kill(thread, thread->proc->pid, thread->tid,
				        SIGPROF, NULL, 0);
				ev = 1;
			}
		}
		if(ev){
			if(thread->itimer_virtual.it_value.tv_sec == 0 &&
			   thread->itimer_virtual.it_value.tv_usec == 0 &&
			   thread->itimer_prof.it_value.tv_sec == 0 &&
			   thread->itimer_prof.it_value.tv_usec == 0){
				thread->itimer_enabled = 0;
				set_timer(0);
			}
		}
	}
	cpu_restore_interrupt(irq_flags);
}

long syscall(int num, ihk_mc_user_context_t *ctx)
{
	long l;
	struct cpu_local_var *v = get_this_cpu_local_var();
	struct thread *thread = v->current;
	static int mcexec_v10_syscall_entry_logs;
	static int mcexec_v10_syscall_entry_pid = -1;
	static int mcexec_v10_syscall_return_logs;
	static int mcexec_v10_syscall_return_pid = -1;
	int pid = thread && thread->proc ? thread->proc->pid : -1;
	int ns;

#ifdef DISABLE_SCHED_YIELD
	if (num != __NR_sched_yield)
#endif // DISABLE_SCHED_YIELD
		set_cputime(CPUTIME_MODE_U2K);

	if (syscall_log_budget_result(pid, &mcexec_v10_syscall_entry_pid,
			&mcexec_v10_syscall_entry_logs, 128) > 0) {
		kprintf("mcexec_v10: syscall entry cpu=%d pid=%d tid=%d nr=%d rip=0x%lx sp=0x%lx status=%d\n",
			ihk_mc_get_processor_id(),
			pid,
			thread ? thread->tid : -1,
			num,
			ctx ? ihk_mc_syscall_pc(ctx) : 0UL,
			ctx ? ihk_mc_syscall_sp(ctx) : 0UL,
			thread ? thread->status : -1);
	}

//kprintf("syscall=%d\n", num);
#ifdef PROFILE_ENABLE
	if (thread->profile && thread->profile_start_ts) {
		unsigned long ts = rdtsc();
		thread->profile_elapsed_ts += (ts - thread->profile_start_ts);
		thread->profile_start_ts = ts;
	}
#endif // PROFILE_ENABLE

	if (syscall_reject_after_exit_result(get_this_cpu_local_var()->current->proc->status,
			num, __NR_exit, __NR_exit_group)) {
		/* x86_64: Setting -EINVAL to rax is done in the
		 * following return.
		 */
		save_syscall_return_value(num, -EINVAL);
		check_signal(-EINVAL, NULL, -1);
		set_cputime(CPUTIME_MODE_K2U);
		return -EINVAL;
	}

	cpu_enable_interrupt();

	if (get_this_cpu_local_var()->current->ptrace) {
		arch_ptrace_syscall_event(get_this_cpu_local_var()->current,
				ctx, -ENOSYS);
		num = ihk_mc_syscall_number(ctx);
	}

#if 0
	if(num != 24)  // if not sched_yield
#endif
	dkprintf("SC(%d:%d)[%3d=%s](%lx, %lx,%lx, %lx, %lx, %lx)@%lx,sp:%lx",
             ihk_mc_get_processor_id(),
             ihk_mc_get_hardware_processor_id(),
             num, syscall_name[num],
             ihk_mc_syscall_arg0(ctx), ihk_mc_syscall_arg1(ctx),
             ihk_mc_syscall_arg2(ctx), ihk_mc_syscall_arg3(ctx),
             ihk_mc_syscall_arg4(ctx), ihk_mc_syscall_arg5(ctx),
             ihk_mc_syscall_pc(ctx), ihk_mc_syscall_sp(ctx));
#if 1
#if 0
	if(num != 24)  // if not sched_yield
#endif
    dkprintf(",*sp:%lx,*(sp+8):%lx,*(sp+16):%lx,*(sp+24):%lx",
             *((unsigned long*)ihk_mc_syscall_sp(ctx)),
             *((unsigned long*)(ihk_mc_syscall_sp(ctx)+8)),
             *((unsigned long*)(ihk_mc_syscall_sp(ctx)+16)),
             *((unsigned long*)(ihk_mc_syscall_sp(ctx)+24)));
#endif
#if 0
	if(num != 24)  // if not sched_yield
#endif
    dkprintf("\n");

	ns = sizeof(syscall_table) / sizeof(syscall_table[0]);
	if (syscall_nested_dispatch_valid_result(num, ns,
			num >= 0 && num < ns && syscall_table[num] != NULL)) {
		l = syscall_table[num](num, ctx);
		
		dkprintf("SC(%d)[%3d] ret: %lx\n", 
				ihk_mc_get_processor_id(), num, l);
	} else {
		dkprintf("USC[%3d](%lx, %lx, %lx, %lx, %lx) @ %lx | %lx\n", num,
		        ihk_mc_syscall_arg0(ctx), ihk_mc_syscall_arg1(ctx),
		        ihk_mc_syscall_arg2(ctx), ihk_mc_syscall_arg3(ctx),
		        ihk_mc_syscall_arg4(ctx), ihk_mc_syscall_pc(ctx),
		        ihk_mc_syscall_sp(ctx));
		l = syscall_generic_forwarding(num, ctx);
	}

	if (syscall_log_budget_result(pid, &mcexec_v10_syscall_return_pid,
			&mcexec_v10_syscall_return_logs, 128) > 0) {
		kprintf("mcexec_v10: syscall return cpu=%d pid=%d tid=%d nr=%d ret=0x%lx ret_signed=%ld rip=0x%lx sp=0x%lx\n",
			ihk_mc_get_processor_id(),
			pid,
			thread ? thread->tid : -1,
			num, l, l,
			ctx ? ihk_mc_syscall_pc(ctx) : 0UL,
			ctx ? ihk_mc_syscall_sp(ctx) : 0UL);
	}

	/* Store return value so that PTRACE_GETREGSET will see it */
	save_syscall_return_value(num, l);

	if (get_this_cpu_local_var()->current->ptrace) {
		/* arm64: The return value modified by the tracer is
		 * stored to x0 in the following check_signal().
		 */
		l = arch_ptrace_syscall_event(get_this_cpu_local_var()->current, ctx, l);
	}

#ifdef PROFILE_ENABLE
	{
		unsigned long ts = rdtsc();

		/*
		 * futex_wait() and schedule() will internally reset
		 * thread->profile_start_ts so that actual wait time
		 * is not accounted for.
		 */
		if (syscall_profile_event_needed_result(num,
				PROFILE_SYSCALL_MAX)) {
			profile_event_add(num, (ts - thread->profile_start_ts));
			thread->profile_start_ts = rdtsc();
		}
		else {
			if (num != __NR_profile) {
				dkprintf("%s: syscall > %d ?? : %d\n",
						__FUNCTION__, PROFILE_SYSCALL_MAX, num);
			}
		}
	}
#endif // PROFILE_ENABLE

#ifdef ENABLE_FUGAKU_HACKS
	/* Do not deschedule when returning from an event (e.g., MPI) */
	if (!(num == __NR_epoll_wait ||
				num == __NR_epoll_pwait ||
				num == __NR_ppoll) &&
			smp_load_acquire_uint(&v->flags) & CPU_FLAG_NEED_RESCHED)
#else
	if (smp_load_acquire_uint(&v->flags) & CPU_FLAG_NEED_RESCHED)
#endif
	{
		check_need_resched();
	}

	if (!list_empty(&thread->sigpending) ||
	    !list_empty(&thread->sigcommon->sigpending)) {
		check_signal(l, NULL, num);
	}

#ifdef DISABLE_SCHED_YIELD
	if (num != __NR_sched_yield)
#endif // DISABLE_SCHED_YIELD
		set_cputime(CPUTIME_MODE_K2U);

	if (thread->proc->nohost) { // mcexec termination was detected
		terminate(0, SIGKILL);
	}
//kprintf("syscall=%d returns %lx(%ld)\n", num, l, l);

	return l;
}

void
check_sig_pending()
{
	int found = 0;
	struct list_head *head;
	mcs_rwlock_lock_t *lock;
	struct mcs_rwlock_node_irqsave mcs_rw_node;
	struct sig_pending *next;
	struct sig_pending *pending;
	__sigset_t w;
	__sigset_t x;
	int sig = 0;
	struct k_sigaction *k;
	struct thread *thread;

	if (clv == NULL)
		return;

	thread = get_this_cpu_local_var()->current;
	if (thread == NULL || thread == &get_this_cpu_local_var()->idle) {
		return;
	}
	if (thread->in_syscall_offload == 0) {
		return;
	}
	if (thread->proc->group_exit_status & 0x0000000100000000L) {
		return;
	}

	w = thread->sigmask.__val[0];

	lock = &thread->sigcommon->lock;
	head = &thread->sigcommon->sigpending;
	for (;;) {
		mcs_rwlock_reader_lock(lock, &mcs_rw_node);

		for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))), next = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = next, next = ((typeof(*next) *)((char *)(next->list.next) - offsetof(typeof(*next), list)))) {
			for (x = pending->sigmask.__val[0], sig = 0; x;
				 sig++, x >>= 1) {
			}
			k = thread->sigcommon->action + sig - 1;
			found = signal_pending_interrupt_action_result(sig,
					(unsigned long)k->sa.sa_handler,
					pending->sigmask.__val[0], w,
					pending->interrupted);
			if (found) {
				pending->interrupted = 1;
				if (found == 2) {
					break;
				}
			}
		}

		mcs_rwlock_reader_unlock(lock, &mcs_rw_node);

		if (found == 2) {
			break;
		}

		if (lock == &thread->sigpendinglock) {
			break;
		}

		lock = &thread->sigpendinglock;
		head = &thread->sigpending;
	}

	if (found == 2) {
		terminate_mcexec(0, sig);
		return;
	}
	else if (found == 1) {
		interrupt_syscall(thread, 0);
		return;
	}
	return;
}

struct sig_pending *
getsigpending(struct thread *thread, int delflag)
{
	struct list_head *head;
	mcs_rwlock_lock_t *lock;
	struct mcs_rwlock_node_irqsave mcs_rw_node;
	struct sig_pending *next;
	struct sig_pending *pending;
	__sigset_t w;
	__sigset_t x;
	int sig;
	struct k_sigaction *k;

	w = thread->sigmask.__val[0];

	lock = &thread->sigcommon->lock;
	head = &thread->sigcommon->sigpending;
	for (;;) {
		if (delflag) {
			mcs_rwlock_writer_lock(lock, &mcs_rw_node);
		}
		else {
			mcs_rwlock_reader_lock(lock, &mcs_rw_node);
		}

		for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))), next = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = next, next = ((typeof(*next) *)((char *)(next->list.next) - offsetof(typeof(*next), list)))) {
			for (x = pending->sigmask.__val[0], sig = 0; x;
					sig++, x >>= 1) {
			}
			k = thread->sigcommon->action + sig - 1;
			if (signal_pending_deliverable_result(delflag, sig,
					(unsigned long)k->sa.sa_handler,
					pending->sigmask.__val[0], w)) {
				if (delflag) {
					process_list_detach_result(&pending->list);
				}

				if (delflag) {
					mcs_rwlock_writer_unlock(lock,
							&mcs_rw_node);
				}
				else {
					mcs_rwlock_reader_unlock(lock,
							&mcs_rw_node);
				}
				return pending;
			}
		}

		if (delflag) {
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);
		}
		else {
			mcs_rwlock_reader_unlock(lock, &mcs_rw_node);
		}

		if (lock == &thread->sigpendinglock) {
			return NULL;
		}

		lock = &thread->sigpendinglock;
		head = &thread->sigpending;
	}

	return NULL;
}

struct sig_pending *
hassigpending(struct thread *thread)
{
	if (list_empty(&thread->sigpending) &&
		list_empty(&thread->sigcommon->sigpending)) {
		return NULL;
	}

	return getsigpending(thread, 0);
}

static void
__check_signal(unsigned long rc, void *regs0, int num, int irq_disabled)
{
	ihk_mc_user_context_t *regs = regs0;
	struct thread *thread;
	struct sig_pending *pending;
	int irqstate;

	if (clv == NULL) {
		return;
	}
	thread = get_this_cpu_local_var()->current;

	if (thread == NULL || thread->proc->pid == 0) {
		struct thread *t;

		irqstate = cpu_disable_interrupt_save();
		ihk_mc_spinlock_lock_noirq(&(get_this_cpu_local_var()->runq_lock));
		for (t = ((typeof(*t) *)((char *)((&(get_this_cpu_local_var()->runq))->next) - offsetof(typeof(*t), sched_list))); &t->sched_list != (&(get_this_cpu_local_var()->runq)); t = ((typeof(*t) *)((char *)(t->sched_list.next) - offsetof(typeof(*t), sched_list)))) {
			if (t->proc->pid <= 0) {
				continue;
			}
			if (t->status == PS_INTERRUPTIBLE &&
			   hassigpending(t)) {
				t->status = PS_RUNNING;
				break;
			}
		}
		ihk_mc_spinlock_unlock_noirq(&(get_this_cpu_local_var()->runq_lock));
		cpu_restore_interrupt(irqstate);
		goto out;
	}

	if (regs != NULL && !interrupt_from_user(regs)) {
		goto out;
	}

	if (list_empty(&thread->sigpending) &&
		list_empty(&thread->sigcommon->sigpending)) {
		goto out;
	}

	for (;;) {
		/* When this function called from check_signal_irq_disabled,
		 * return with interrupt invalid.
		 * This is to eliminate signal loss.
		 */
		if (irq_disabled == 1) {
			irqstate = cpu_disable_interrupt_save();
		}
		pending = getsigpending(thread, 1);
		if (!pending) {
			dkprintf("check_signal,queue is empty\n");
			goto out;
		}
		if (irq_disabled == 1) {
			cpu_restore_interrupt(irqstate);
		}
		if (do_signal(rc, regs, thread, pending, num)) {
			num = -1;
		}
	}

out:
	return;
}

void
check_signal(unsigned long rc, void *regs0, int num)
{
	__check_signal(rc, regs0, num, 0);
}

void
check_signal_irq_disabled(unsigned long rc, void *regs0, int num)
{
	__check_signal(rc, regs0, num, 1);
}
