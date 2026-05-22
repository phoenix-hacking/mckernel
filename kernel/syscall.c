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
#include "../executer/include/uti.h"

/* Headers taken from kitten LWK */
#include <lwk/stddef.h>
#include <futex.h>

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

static ihk_spinlock_t tod_data_lock = SPIN_LOCK_UNLOCKED;
static unsigned long uti_desc; /* Address of struct uti_desc object in syscall_intercept.c */

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

#define PTRACE_WAKEUP_ACTION_NONE 0
#define PTRACE_WAKEUP_ACTION_KILL 1
#define PTRACE_WAKEUP_ACTION_RESUME 2
#define PTRACE_RESUME_SIGNAL_SOURCE_USER 0
#define PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG 1
#define PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG 2
#define PTRACE_SIGINFO_STORE_SENDSIG 0x1
#define PTRACE_SIGINFO_STORE_RECVSIG 0x2
#define PTRACE_SIGINFO_ALLOC_SENDSIG 0x4
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
#define GETRUSAGE_DISPATCH_SELF 1
#define GETRUSAGE_DISPATCH_CHILDREN 2
#define GETRUSAGE_DISPATCH_THREAD 3
#define GETRUSAGE_THREAD_UPDATE_READY 0
#define GETRUSAGE_THREAD_UPDATE_INTERRUPT 1
#define TERMINATE_CHILD_ACTION_NONE 0
#define TERMINATE_CHILD_ACTION_FREE_ZOMBIE 1
#define TERMINATE_CHILD_ACTION_REPARENT_CHILD 2
#define TERMINATE_CHILD_ACTION_REPARENT_PTRACED 3
#define CLONE_TLS_SOURCE_INHERIT 0
#define CLONE_TLS_SOURCE_ARGUMENT 1

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
extern int robust_list_len_result(size_t len);
extern int tkill_tid_result(int tid);
extern int tgkill_target_result(int tgid, int tid);
extern int sigaction_validate(int sig, int has_act);
extern int rt_sigprocmask_validate(size_t sigsetsize,
		size_t expected_sigset_size, int has_set, int how);
extern unsigned long rt_sigprocmask_apply(unsigned long current_mask,
		unsigned long set_mask, int has_set, int how);
extern int rt_sigpending_size_result(size_t sigsetsize,
		size_t expected_sigset_size);
extern int signalfd4_sigsetsize_result(size_t sigsetsize,
		size_t expected_sigset_size);
extern int signalfd4_flags_result(int flags);
extern int syscall_refresh_cred_needed_result(long rc);
extern int syscall_getpid_result(int pid);
extern int syscall_getppid_result(int ppid);
extern int syscall_gettid_result(int tid);
extern int syscall_set_tid_address_return_result(int pid);
extern int setpgid_normalize_pid(int current_pid, int pid);
extern int setpgid_normalize_pgid(int pid, int pgid);
extern int setpgid_execed_result(int execed);
extern int memlock_prepare_range(uintptr_t start0, size_t len0,
		uintptr_t user_start, uintptr_t user_end,
		uintptr_t *startp, size_t *lenp, uintptr_t *endp);
extern int memlock_range_flag_result(unsigned long flag);
extern int range_has_disallowed_change_flags(unsigned long flag);
extern int munmap_prepare_range(uintptr_t addr, size_t len0,
		uintptr_t user_start, uintptr_t user_end, size_t *lenp);
extern int mprotect_prepare_range(uintptr_t start, size_t len0,
		uintptr_t user_start, uintptr_t user_end,
		size_t *lenp, uintptr_t *endp);
extern int mlockall_policy_result(int flags, int is_privileged,
		unsigned long memlock_cur);
extern int remap_file_pages_prepare(uintptr_t start0, size_t size, int prot,
		size_t pgoff, uintptr_t *startp, uintptr_t *endp, off_t *offp);
extern int mremap_prepare_args(uintptr_t oldaddr, size_t oldsize0,
		size_t newsize0, int flags, uintptr_t newaddr,
		uintptr_t user_start, uintptr_t user_end,
		size_t *oldsizep, size_t *newsizep, uintptr_t *oldendp,
		int *no_opp);
extern int mremap_fixed_range_result(uintptr_t newstart,
		uintptr_t user_start, uintptr_t oldstart, uintptr_t oldend,
		uintptr_t newend);
extern int mremap_maymove_result(int flags);
extern int msync_prepare_range(uintptr_t start0, size_t len0, int flags,
		size_t *lenp, uintptr_t *endp);
extern int msync_locked_range_result(int flags, unsigned long range_flags);
extern int mbind_prepare_range(uintptr_t addr, unsigned long len0,
		unsigned long *lenp);
extern int mempolicy_nodemask_bits_result(unsigned long maxnode,
		unsigned long *nodemask_bitsp);
extern int mempolicy_nodemask_bits_is_clamped(unsigned long maxnode);
extern int mbind_mode_flags_result(int mode, unsigned int flags,
		int *mode_flagsp, int *normalized_modep);
extern int mempolicy_mode_is_supported(int mode);
extern int set_mempolicy_normalize_mode(int mode, int *normalized_modep);
extern int get_mempolicy_validate(unsigned long addr, int flags,
		int process_policy, unsigned long maxnode, int nr_numa_nodes,
		unsigned long *nodemask_bitsp);
extern int move_pages_policy_result(int pid, int flags);
extern int brk_prepare_result(unsigned long address, unsigned long brk_start,
		unsigned long brk_end, unsigned long brk_end_allocated,
		unsigned long *resultp, int *extend_neededp);
extern unsigned long brk_default_vrflags(void);
extern int mincore_prepare_range(uintptr_t start, size_t len,
		uintptr_t user_start, uintptr_t user_end, uintptr_t *endp);
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
extern int clock_gettime_dispatch(int clock_id, int local_support, int has_ts);
extern int gettimeofday_dispatch(int has_tv, int has_tz, int local_support);
extern int nanosleep_validate_timespec(long sec, long nsec);
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
extern int sigsuspend_sigsetsize_result(size_t sigsetsize,
		size_t expected_sigset_size);
extern unsigned long sigsuspend_prepare_mask(unsigned long raw_mask);
extern int sigsuspend_pending_matches(unsigned long pending_mask,
		unsigned long suspend_mask);
extern int sigaction_sigsetsize_result(size_t sigsetsize,
		size_t expected_sigset_size);
extern int sigaltstack_validate(int flags, size_t size);
extern int sigaltstack_is_disable(int flags);
extern int process_vm_validate_args(unsigned long flags,
		unsigned long liovcnt, unsigned long riovcnt);
extern int process_vm_op_is_write(int op);
extern int process_vm_op_is_valid(int op);
extern int ptrace_signal_data_result(long data);
extern int ptrace_detach_signal_result(long data);
extern int ptrace_user_area_result(long addr, unsigned long user_struct_size);
extern int ptrace_status_allows_io(int status);
extern int ptrace_setoptions_flags_result(int flags);
extern int ptrace_apply_options(int current, int flags);
extern int ptrace_child_traced_result(int has_child, int has_proc, int ptrace);
extern int ptrace_attach_policy_result(int tracer_pid, int target_pid,
		int target_ptrace, int same_process);
extern int ptrace_detach_state_result(int is_traced, int same_report_proc);
extern int ptrace_siginfo_state_result(int status, int has_siginfo);
extern int ptrace_eventmsg_state_result(int status);
extern int ptrace_wakeup_request_action_result(long request);
extern int ptrace_resume_single_step_result(long request);
extern int ptrace_resume_trace_syscall_result(long request);
extern int ptrace_resume_signal_needed_result(long request, long data);
extern int ptrace_resume_signal_source_result(long request, int has_sendsig,
		int has_recvsig);
extern int ptrace_detach_forward_signal_needed_result(int data);
extern int ptrace_detach_exit_signal_needed_result(int status);
extern int ptrace_setsiginfo_target_result(int status, int has_sendsig,
		int has_recvsig);
extern int ptrace_request_dispatch_result(long request);
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
extern int waitid_siginfo_needed_result(int rc, int has_infop);
extern int getrusage_dispatch_result(int who);
extern int getrusage_thread_update_action_result(int is_current_thread,
		int status, int in_kernel);
extern long getrusage_maxrss_kb_result(long maxrss);
extern int exit_code_status_result(int code);
extern int exit_code_signal_result(int code);
extern int exit_syscall_code_result(int status);
extern int thread_exit_signal_result(int ptrace, int termsig);
extern int sigchld_code_result(int exit_status);
extern int exit_group_status_claimed_result(unsigned long old_exit_status);
extern unsigned long exit_group_status_result(int rc, int sig);
extern int terminate_thread_active_result(int status);
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
extern int futex_decode_flags_result(int flags, int *opp, int *fsharedp);
extern int futex_wait_timeout_needed_result(int op, int has_utime);
extern int futex_timeout_is_absolute_result(int op);
extern int futex_clock_id_result(int flags);
extern unsigned int futex_requeue_val2_result(int op, unsigned long arg3);
extern unsigned long futex_timeout_ns_result(int op, long timeout_sec,
		long timeout_nsec, long now_sec, long now_nsec);
#else
SYSCALL_POLICY_HELPER_PROTO int robust_list_len_result(size_t len);
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
SYSCALL_POLICY_HELPER_PROTO int syscall_refresh_cred_needed_result(long rc);
SYSCALL_POLICY_HELPER_PROTO int syscall_getpid_result(int pid);
SYSCALL_POLICY_HELPER_PROTO int syscall_getppid_result(int ppid);
SYSCALL_POLICY_HELPER_PROTO int syscall_gettid_result(int tid);
SYSCALL_POLICY_HELPER_PROTO int syscall_set_tid_address_return_result(int pid);
SYSCALL_POLICY_HELPER_PROTO int setpgid_normalize_pid(int current_pid, int pid);
SYSCALL_POLICY_HELPER_PROTO int setpgid_normalize_pgid(int pid, int pgid);
SYSCALL_POLICY_HELPER_PROTO int setpgid_execed_result(int execed);
SYSCALL_POLICY_HELPER_PROTO int memlock_prepare_range(uintptr_t start0,
		size_t len0, uintptr_t user_start, uintptr_t user_end,
		uintptr_t *startp, size_t *lenp, uintptr_t *endp);
SYSCALL_POLICY_HELPER_PROTO int memlock_range_flag_result(unsigned long flag);
SYSCALL_POLICY_HELPER_PROTO int range_has_disallowed_change_flags(
		unsigned long flag);
SYSCALL_POLICY_HELPER_PROTO int munmap_prepare_range(uintptr_t addr,
		size_t len0, uintptr_t user_start, uintptr_t user_end,
		size_t *lenp);
SYSCALL_POLICY_HELPER_PROTO int mprotect_prepare_range(uintptr_t start,
		size_t len0, uintptr_t user_start, uintptr_t user_end,
		size_t *lenp, uintptr_t *endp);
SYSCALL_POLICY_HELPER_PROTO int mlockall_policy_result(int flags,
		int is_privileged, unsigned long memlock_cur);
SYSCALL_POLICY_HELPER_PROTO int remap_file_pages_prepare(uintptr_t start0,
		size_t size, int prot, size_t pgoff, uintptr_t *startp,
		uintptr_t *endp, off_t *offp);
SYSCALL_POLICY_HELPER_PROTO int mremap_prepare_args(uintptr_t oldaddr,
		size_t oldsize0, size_t newsize0, int flags, uintptr_t newaddr,
		uintptr_t user_start, uintptr_t user_end,
		size_t *oldsizep, size_t *newsizep, uintptr_t *oldendp,
		int *no_opp);
SYSCALL_POLICY_HELPER_PROTO int mremap_fixed_range_result(
		uintptr_t newstart, uintptr_t user_start, uintptr_t oldstart,
		uintptr_t oldend, uintptr_t newend);
SYSCALL_POLICY_HELPER_PROTO int mremap_maymove_result(int flags);
SYSCALL_POLICY_HELPER_PROTO int msync_prepare_range(uintptr_t start0,
		size_t len0, int flags, size_t *lenp, uintptr_t *endp);
SYSCALL_POLICY_HELPER_PROTO int msync_locked_range_result(int flags,
		unsigned long range_flags);
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
SYSCALL_POLICY_HELPER_PROTO int get_mempolicy_validate(unsigned long addr,
		int flags, int process_policy, unsigned long maxnode,
		int nr_numa_nodes, unsigned long *nodemask_bitsp);
SYSCALL_POLICY_HELPER_PROTO int move_pages_policy_result(int pid, int flags);
SYSCALL_POLICY_HELPER_PROTO int brk_prepare_result(unsigned long address,
		unsigned long brk_start, unsigned long brk_end,
		unsigned long brk_end_allocated, unsigned long *resultp,
		int *extend_neededp);
SYSCALL_POLICY_HELPER_PROTO unsigned long brk_default_vrflags(void);
SYSCALL_POLICY_HELPER_PROTO int mincore_prepare_range(uintptr_t start,
		size_t len, uintptr_t user_start, uintptr_t user_end,
		uintptr_t *endp);
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
SYSCALL_POLICY_HELPER_PROTO int clock_gettime_dispatch(int clock_id,
		int local_support, int has_ts);
SYSCALL_POLICY_HELPER_PROTO int gettimeofday_dispatch(int has_tv, int has_tz,
		int local_support);
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
SYSCALL_POLICY_HELPER_PROTO int sigaction_sigsetsize_result(
		size_t sigsetsize, size_t expected_sigset_size);
SYSCALL_POLICY_HELPER_PROTO int sigaltstack_validate(int flags, size_t size);
SYSCALL_POLICY_HELPER_PROTO int sigaltstack_is_disable(int flags);
SYSCALL_POLICY_HELPER_PROTO int process_vm_validate_args(unsigned long flags,
		unsigned long liovcnt, unsigned long riovcnt);
SYSCALL_POLICY_HELPER_PROTO int process_vm_op_is_write(int op);
SYSCALL_POLICY_HELPER_PROTO int process_vm_op_is_valid(int op);
SYSCALL_POLICY_HELPER_PROTO int ptrace_signal_data_result(long data);
SYSCALL_POLICY_HELPER_PROTO int ptrace_detach_signal_result(long data);
SYSCALL_POLICY_HELPER_PROTO int ptrace_user_area_result(long addr,
		unsigned long user_struct_size);
SYSCALL_POLICY_HELPER_PROTO int ptrace_status_allows_io(int status);
SYSCALL_POLICY_HELPER_PROTO int ptrace_setoptions_flags_result(int flags);
SYSCALL_POLICY_HELPER_PROTO int ptrace_apply_options(int current, int flags);
SYSCALL_POLICY_HELPER_PROTO int ptrace_child_traced_result(int has_child,
		int has_proc, int ptrace);
SYSCALL_POLICY_HELPER_PROTO int ptrace_attach_policy_result(int tracer_pid,
		int target_pid, int target_ptrace, int same_process);
SYSCALL_POLICY_HELPER_PROTO int ptrace_detach_state_result(int is_traced,
		int same_report_proc);
SYSCALL_POLICY_HELPER_PROTO int ptrace_siginfo_state_result(int status,
		int has_siginfo);
SYSCALL_POLICY_HELPER_PROTO int ptrace_eventmsg_state_result(int status);
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
SYSCALL_POLICY_HELPER_PROTO int ptrace_setsiginfo_target_result(
		int status, int has_sendsig, int has_recvsig);
SYSCALL_POLICY_HELPER_PROTO int ptrace_request_dispatch_result(long request);
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
SYSCALL_POLICY_HELPER_PROTO int waitid_siginfo_needed_result(int rc,
		int has_infop);
SYSCALL_POLICY_HELPER_PROTO int getrusage_dispatch_result(int who);
SYSCALL_POLICY_HELPER_PROTO int getrusage_thread_update_action_result(
		int is_current_thread, int status, int in_kernel);
SYSCALL_POLICY_HELPER_PROTO long getrusage_maxrss_kb_result(long maxrss);
SYSCALL_POLICY_HELPER_PROTO int exit_code_status_result(int code);
SYSCALL_POLICY_HELPER_PROTO int exit_code_signal_result(int code);
SYSCALL_POLICY_HELPER_PROTO int exit_syscall_code_result(int status);
SYSCALL_POLICY_HELPER_PROTO int thread_exit_signal_result(int ptrace,
		int termsig);
SYSCALL_POLICY_HELPER_PROTO int sigchld_code_result(int exit_status);
SYSCALL_POLICY_HELPER_PROTO int exit_group_status_claimed_result(
		unsigned long old_exit_status);
SYSCALL_POLICY_HELPER_PROTO unsigned long exit_group_status_result(int rc,
		int sig);
SYSCALL_POLICY_HELPER_PROTO int terminate_thread_active_result(int status);
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

static void send_syscall(struct syscall_request *req, int cpu,
			 struct syscall_response *res)
{
	struct ikc_scd_packet packet IHK_DMA_ALIGN;
	struct ihk_ikc_channel_desc *syscall_channel = get_cpu_local_var(cpu)->ikc2linux;
	int ret;
	static int mcexec_v10_send_syscall_logs;
	static int mcexec_v10_send_syscall_pid = -1;
	struct thread *thread = cpu_local_var(current);
	int pid = thread && thread->proc ? thread->proc->pid : -1;

	res->status = 0;
	req->valid = 0;

	memcpy(&packet.req, req, sizeof(*req));

	barrier();
	smp_store_release(&packet.req.valid, 1);

#ifdef SYSCALL_BY_IKC
	packet.msg = SCD_MSG_SYSCALL_ONESIDE;
	packet.ref = cpu;
	packet.pid = cpu_local_var(current)->proc->pid;
	packet.resp_pa = virt_to_phys(res);
	dkprintf("send syscall, nr: %d, pid: %d\n", req->number, packet.pid);
	if (pid != mcexec_v10_send_syscall_pid) {
		mcexec_v10_send_syscall_pid = pid;
		mcexec_v10_send_syscall_logs = 0;
	}
	if (mcexec_v10_send_syscall_logs < 64) {
		kprintf("mcexec_v10: send_syscall cpu=%d pid=%d tid=%d nr=%d rip=0x%lx sp=0x%lx\n",
			cpu, packet.pid, thread ? thread->tid : -1,
			req->number,
			thread && thread->uctx ? ihk_mc_syscall_pc(thread->uctx) : 0UL,
			thread && thread->uctx ? ihk_mc_syscall_sp(thread->uctx) : 0UL);
		mcexec_v10_send_syscall_logs++;
	}

	ret = ihk_ikc_send(syscall_channel, &packet, 0);
	if (ret < 0) {
		kprintf("ERROR: sending IKC msg, ret: %d\n", ret);
	}
#endif
}

long do_syscall(struct syscall_request *req, int cpu)
{
	struct syscall_response res;
	long rc;
	struct thread *thread = cpu_local_var(current);
	struct ihk_os_cpu_monitor *monitor = cpu_local_var(monitor);
	int mstatus = 0;
	static int mcexec_v10_offload_return_logs;
	static int mcexec_v10_offload_return_pid = -1;
	int pid = thread && thread->proc ? thread->proc->pid : -1;

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

	if(req->number != __NR_exit_group){
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
	req->rtid = cpu_local_var(current)->tid;

	if (req->number == __NR_sched_setaffinity && req->args[0] == 0) {
		/* mcexec thread serving migrate-to-Linux request must have
		   the same tid as the requesting McKernel thread because the
		   serving thread jumps to hfi driver and then jumps to
		   rus_vm_fault() without registering it into per thread data
		   by mcctrl_add_per_thread_data()). */
		req->ttid = cpu_local_var(current)->tid/*0*/;
		dkprintf("%s: uti, ttid=%d\n", __FUNCTION__, req->ttid);
	} else {
		/* Any thread from the pool may serve the request */
		req->ttid = 0;
	}
	res.req_thread_status = IHK_SCD_REQ_THREAD_SPINNING;
#ifdef ENABLE_TOFU
	res.pde_data = NULL;
#endif
	send_syscall(req, cpu, &res);

	if (req->rtid == -1) {
		preempt_disable();
	}

	dkprintf("%s: syscall num: %d waiting for Linux.. \n",
		__FUNCTION__, req->number);

#define	STATUS_IN_PROGRESS	0
#define	STATUS_COMPLETED	1
#define	STATUS_PAGE_FAULT	3
#define	STATUS_SYSCALL		4
#define __NR_syscall_response 8001
	while (smp_load_acquire(&res.status) != STATUS_COMPLETED) {
		while (smp_load_acquire(&res.status) == STATUS_IN_PROGRESS) {
			struct cpu_local_var *v;
			int do_schedule = 0;
			long runq_irqstate;
			unsigned long flags;
			DECLARE_WAITQ_ENTRY(scd_wq_entry, cpu_local_var(current));

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
				kfree(arg);
			}

			check_sig_pending();
			cpu_pause();

			/* Spin if not preemptable */
			if (ihk_atomic_read(&cpu_local_var(no_preempt))
				|| !thread->tid) {
				continue;
			}

			/* Spin by default, but if re-schedule is requested let
			 * the other thread run */
			runq_irqstate = cpu_disable_interrupt_save();
			ihk_mc_spinlock_lock_noirq(
				&(get_this_cpu_local_var()->runq_lock));
			v = get_this_cpu_local_var();

			if (v->flags & CPU_FLAG_NEED_RESCHED ||
			    v->runq_len > 1 ||
			    req->number == __NR_sched_setaffinity) {
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
			if (smp_load_acquire(&res.req_thread_status) ==
					IHK_SCD_REQ_THREAD_DESCHEDULED ||
					(cmpxchg(&res.req_thread_status,
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

		if (smp_load_acquire(&res.status) == STATUS_SYSCALL) {
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
				int sig = request.args[0];
				struct thread *thread = cpu_local_var(current);

				sig--;
				if (sig < 0 || sig >= _NSIG)
					syscall_ret = -EINVAL;
				else
					syscall_ret = (unsigned long)thread->
					              sigcommon->action[sig].
					              sa.sa_handler;
			}
			else {
				ns = (sizeof syscall_table  /
				      sizeof syscall_table[0]);
				if (num >= 0 && num < ns &&
				    syscall_table[num]) {
					ihk_mc_syscall_arg0(&ctx) =
					                       request.args[0];
					ihk_mc_syscall_arg1(&ctx) =
					                       request.args[1];
					ihk_mc_syscall_arg2(&ctx) =
					                       request.args[2];
					ihk_mc_syscall_arg3(&ctx) =
					                       request.args[3];
					ihk_mc_syscall_arg4(&ctx) =
					                       request.args[4];
					ihk_mc_syscall_arg5(&ctx) =
					                       request.args[5];
					syscall_ret = syscall_table[num](num,
					                                 &ctx);
				}
				else
					syscall_ret = -ENOSYS;
			}

			/* send result */
			req2.number = __NR_syscall_response;
			req2.args[1] = syscall_ret;
			/* The current thread is the requester and only the waiting thread
			 * may serve the request */
			req2.rtid = cpu_local_var(current)->tid;
			req2.ttid = res.stid;

			res.req_thread_status = IHK_SCD_REQ_THREAD_SPINNING;
			send_syscall(&req2, cpu, &res);
		}
	}
	if (req->rtid == -1) {
		preempt_enable();
	}

	dkprintf("%s: syscall num: %d got host reply: %d \n",
		__FUNCTION__, req->number, res.ret);

	rc = res.ret;
	if (pid != mcexec_v10_offload_return_pid) {
		mcexec_v10_offload_return_pid = pid;
		mcexec_v10_offload_return_logs = 0;
	}
	if (mcexec_v10_offload_return_logs < 64) {
		kprintf("mcexec_v10: offload_return cpu=%d pid=%d tid=%d nr=%d ret=0x%lx ret_signed=%ld\n",
			cpu, pid, thread ? thread->tid : -1,
			req->number, rc, rc);
		mcexec_v10_offload_return_logs++;
	}

#ifdef ENABLE_TOFU
	if ((req->number == __NR_ioctl && rc == 0) ||
			(req->number == __NR_openat && rc > 0)) {
		int fd = req->number == __NR_ioctl ? req->args[0] : rc;
		char *path = req->number == __NR_ioctl ?
			thread->proc->fd_path[fd] : thread->fd_path_in_open;

		if (cpu_local_var(current)->proc->enable_tofu &&
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

	if(req->number != __NR_exit_group){
		--thread->in_syscall_offload;
	}

	/* -ERESTARTSYS indicates that the proxy process is gone
	 * and the application should be terminated */
	if (rc == -ERESTARTSYS) {
		dkprintf("%s: proxy PID %d is dead, terminate()\n",
			__FUNCTION__, thread->proc->pid);
		thread->proc->nohost = 1;
	}

#ifdef PROFILE_ENABLE
	if (req->number < PROFILE_SYSCALL_MAX) {
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

long syscall_generic_forwarding(int n, ihk_mc_user_context_t *ctx)
{
	SYSCALL_HEADER;
	dkprintf("syscall_generic_forwarding(%d)\n", n);
	SYSCALL_ARGS_6(D,D,D,D,D,D);
	SYSCALL_FOOTER;
}

static int wait_zombie(struct thread *thread, struct process *child, int *status, int options) {
    int ret;
    struct syscall_request request IHK_DMA_ALIGN;
    
    dkprintf("wait_zombie,found PS_ZOMBIE process: %d\n", child->pid);
    
	if (status) {
		*status = child->group_exit_status;
	}
    
	if (wait_zombie_skip_host_result(child->ppid_parent->pid,
			thread->proc->pid, child->nowait))
		return child->pid;
	request.number = __NR_wait4;
	request.args[0] = child->pid;
	request.args[1] = 0;
	request.args[2] = options;
	/* Ask host to clean up exited child */
	ret = do_syscall(&request, ihk_mc_get_processor_id());

	if (ret != child->pid)
		kprintf("WARNING: host waitpid failed?\n");
	dkprintf("wait_zombie,child->pid=%d,status=%08x\n",
		 child->pid, status ? *status : -1);

    return ret;
}

static int wait_stopped(struct thread *thread, struct process *child, struct thread *c_thread, int *status, int options)
{
	dkprintf("wait_stopped,proc->pid=%d,child->pid=%d,options=%08x\n",
			 thread->proc->pid, child->pid, options);
	int ret;
	int source = wait_stopped_source_result(c_thread != NULL,
			c_thread ? c_thread->exit_status : 0, child->status,
			child->group_exit_status,
			child->main_thread->exit_status);
	int exit_status;

	/* Skip this process because exit_status has been reaped. */
	if (source == WAIT_STOP_SOURCE_NONE) {
		ret = 0;
		goto out;
	}

	exit_status = wait_stopped_exit_status_result(source,
			c_thread ? c_thread->exit_status : 0,
			child->group_exit_status,
			child->main_thread->exit_status);
	/* TODO: define 0x7f in kernel/include/process.h */
	if (status) {
		*status = wait_stopped_status_result(exit_status);
	}

	/* Reap exit_status. signal_flags is reaped on receiving */
	/* signal in do_kill(). */
	switch (source) {
	case WAIT_STOP_SOURCE_THREAD:
		process_wait_exit_status_reap_result(c_thread,
			__builtin_offsetof(struct thread, exit_status),
			options);
		break;
	case WAIT_STOP_SOURCE_PROCESS:
		process_wait_exit_status_reap_result(child,
			__builtin_offsetof(struct process, group_exit_status),
			options);
		break;
	case WAIT_STOP_SOURCE_MAIN_THREAD:
		process_wait_exit_status_reap_result(child->main_thread,
			__builtin_offsetof(struct thread, exit_status),
			options);
		break;
	}

	dkprintf("wait_stopped,child->pid=%d,status=%08x\n",
			 child->pid, status ? *status : -1);
	ret = wait_report_id_result(source, child->pid,
			c_thread ? c_thread->tid : 0);
 out:
	return ret;    
}

static int wait_continued(struct thread *thread, struct process *child,
			  struct thread *c_thread, int *status, int options)
{
	int ret;

	if (status) {
		*status = wait_continued_status_result();
	}

	/* Reap signal_flags */
	if (c_thread)
		process_thread_signal_flags_reap_result(c_thread,
				__builtin_offsetof(struct thread, signal_flags),
				options, SIGNAL_STOP_CONTINUED);
	else
		process_thread_signal_flags_reap_result(child->main_thread,
				__builtin_offsetof(struct thread, signal_flags),
				options, SIGNAL_STOP_CONTINUED);

	dkprintf("wait4,SIGNAL_STOP_CONTINUED,pid=%d,status=%08x\n",
			 child->pid, status ? *status : -1);
	ret = c_thread ? c_thread->tid : child->pid;
	return ret;
}

static void
thread_exit_signal(struct thread *thread)
{
	int sig;
	struct siginfo info;
	int error;
	struct timespec ats;

	if (thread->report_proc == NULL) {
		return;
	}

	sig = thread_exit_signal_result(thread->ptrace, thread->termsig);
	memset(&info, '\0', sizeof(info));
	info.si_signo = sig;
	info.si_code = sigchld_code_result(thread->exit_status);
	info._sifields._sigchld.si_pid = thread->tid;
	info._sifields._sigchld.si_status = thread->exit_status;
	tsc_to_ts(thread->user_tsc, &ats);
	info._sifields._sigchld.si_utime = timespec_to_jiffy(&ats);
	tsc_to_ts(thread->system_tsc, &ats);
	info._sifields._sigchld.si_stime = timespec_to_jiffy(&ats);
	error = do_kill(NULL, thread->report_proc->pid, -1, sig, &info, 0);
	dkprintf("terminate,klll %d,error=%d\n", sig, error);
	/* Wake parent (if sleeping in wait4()) */
	waitq_wakeup(&thread->report_proc->waitpid_q);
}

static void
finalize_process(struct process *proc)
{
	struct resource_set *resource_set = cpu_local_var(resource_set);
	struct process *pid1 = resource_set->pid1;
	int exit_status = proc->group_exit_status;
	struct mcs_rwlock_node updatelock;

	mcs_rwlock_writer_lock_noirq(&proc->update_lock, &updatelock);
	// Send signal to parent
	if (proc->parent == pid1) {
		proc->status = PS_ZOMBIE;
		mcs_rwlock_writer_unlock_noirq(&proc->update_lock, &updatelock);
		release_process(proc);
	}
	else {
		proc->status = PS_ZOMBIE;
		mcs_rwlock_writer_unlock_noirq(&proc->update_lock, &updatelock);

		dkprintf("terminate,wakeup\n");

		/* Signal parent if still attached */
		if (proc->termsig != 0) {
			struct siginfo info;
			int error;

			memset(&info, '\0', sizeof info);
			info.si_signo = SIGCHLD;
			info.si_code = sigchld_code_result(exit_status);
			info._sifields._sigchld.si_pid = proc->pid;
			info._sifields._sigchld.si_status = exit_status;
			info._sifields._sigchld.si_utime =
			                        timespec_to_jiffy(&proc->utime);
			info._sifields._sigchld.si_stime =
			                        timespec_to_jiffy(&proc->stime);
			error = do_kill(NULL, proc->parent->pid, -1, SIGCHLD, &info, 0);
			dkprintf("terminate,klll %d,error=%d\n",
					proc->termsig, error);
		}
		/* Wake parent (if sleeping in wait4()) */
		waitq_wakeup(&proc->parent->waitpid_q);
	}
}

static void
ptrace_detach_thread(struct thread *thread, int data)
{
	struct resource_set *resource_set = cpu_local_var(resource_set);
	struct process *pid1 = resource_set->pid1;
	struct thread *mythread = cpu_local_var(current);
	struct process *proc = mythread->proc;
	struct process *report_proc = NULL;
	struct mcs_rwlock_node_irqsave lock;
	struct process *term_proc = NULL;

	if (thread == thread->proc->main_thread) {
		struct process *tracee_proc = thread->proc;
		struct process *parent = tracee_proc->ppid_parent;

		if (thread->proc->status == PS_ZOMBIE &&
		    thread->proc->parent != parent) {
			term_proc = thread->proc;
		}
		mcs_rwlock_reader_lock(&proc->children_lock, &lock);

		process_list_detach_result(&tracee_proc->siblings_list);
		mcs_rwlock_reader_unlock(&proc->children_lock, &lock);

		mcs_rwlock_reader_lock(&tracee_proc->children_lock, &lock);
		process_ptrace_main_detach_reparent_result(tracee_proc,
			__builtin_offsetof(struct process, parent), parent,
			&tracee_proc->ptraced_siblings_list,
			&tracee_proc->siblings_list, &parent->children_list);

		mcs_rwlock_reader_unlock(&tracee_proc->children_lock, &lock);
	}
	if (thread->termsig &&
	    thread->termsig != SIGCHLD &&
	    thread->proc != pid1) {
		report_proc = thread->proc;
	}
	mcs_rwlock_reader_lock(&proc->threads_lock, &lock);
	process_thread_report_detach_result(thread,
		__builtin_offsetof(struct thread, report_proc), report_proc,
		&thread->report_siblings_list);
	mcs_rwlock_reader_unlock(&proc->threads_lock, &lock);
	kfree(process_thread_ptrace_cleanup_result(thread,
		__builtin_offsetof(struct thread, ptrace),
		__builtin_offsetof(struct thread, ptrace_saved_uctx_valid),
		__builtin_offsetof(struct thread, ptrace_debugreg)));

	clear_single_step(thread);
	if (report_proc) {
		mcs_rwlock_reader_lock(&report_proc->threads_lock, &lock);
		process_thread_report_attach_result(thread, 0, 0, 0,
			__builtin_offsetof(struct thread, report_proc),
			report_proc, &thread->report_siblings_list,
			&report_proc->report_threads_list);
		mcs_rwlock_reader_unlock(&report_proc->threads_lock, &lock);
		if (ptrace_detach_exit_signal_needed_result(thread->status)) {
			/*
			 * Traced thread reports to the original parent with
			 * the termination signal in addition to the report
			 * to the tracer.
			 */
			thread_exit_signal(thread);
		}
	}

	if (ptrace_detach_forward_signal_needed_result(data)) {
		struct siginfo info;

		memset(&info, '\0', sizeof(info));
		info.si_signo = data;
		info.si_code = SI_USER;
		info._sifields._kill.si_pid = proc->pid;
		do_kill(mythread, thread->proc->pid, thread->tid,
			data, &info, 1);
	}
	sched_wakeup_thread(thread, PS_TRACED | PS_STOPPED);
	release_thread(thread);
	if (term_proc) {
		finalize_process(term_proc);
	}
}

static void
set_process_rusage(struct process *proc, struct rusage *usage)
{
	ts_to_tv(&usage->ru_utime, &proc->utime);
	ts_to_tv(&usage->ru_stime, &proc->stime);
	usage->ru_maxrss = proc->maxrss / 1024;
}

static int
wait_proc(int pid, int *status, int options, void *rusage, int *empty)
{
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct process *child, *next;
	int pgid = proc->pgid;
	int ret = 0;
	struct mcs_rwlock_node lock;
	struct mcs_rwlock_node child_lock;
	struct thread *c_thread = NULL;

	mcs_rwlock_writer_lock_noirq(&proc->children_lock, &lock);
	list_for_each_entry_safe(child, next, &proc->children_list,
				 siblings_list) {
		/*
		 * Find thread with pid == tid, this will be either the main
		 * thread or the one we are looking for specifically when
		 * __WCLONE is passed
		 */
		if (!wait_process_pid_matches_result(pid, pgid, child->pgid,
				child->pid))
			continue;

		*empty = 0;

		if (wait_process_exited_candidate_result(options,
				child->status)) {
			ret = wait_zombie(thread, child, status, options);
			if (wait_process_reparent_needed_result(options,
			    child->parent == child->ppid_parent)) {
				struct mcs_rwlock_node updatelock;
				struct mcs_rwlock_node childlock;
				struct process *pid1;

				pid1 = cpu_local_var(resource_set)->pid1;

				mcs_rwlock_writer_lock_noirq(&proc->update_lock,
							     &updatelock);
				ts_add(&proc->stime_children, &child->stime);
				ts_add(&proc->utime_children, &child->utime);
				ts_add(&proc->stime_children,
							&child->stime_children);
				ts_add(&proc->utime_children,
							&child->utime_children);
				if (child->maxrss > proc->maxrss_children)
					proc->maxrss_children = child->maxrss;
				if (child->maxrss_children >
							  proc->maxrss_children)
					proc->maxrss_children =
							 child->maxrss_children;
				set_process_rusage(child, rusage);
				mcs_rwlock_writer_unlock_noirq(
					       &proc->update_lock, &updatelock);
				process_list_detach_result(&child->siblings_list);
				mcs_rwlock_writer_unlock_noirq(
						   &proc->children_lock, &lock);

				mcs_rwlock_writer_lock_noirq(
					      &child->update_lock, &updatelock);
				child->parent = pid1;
				child->ppid_parent = pid1;
				mcs_rwlock_writer_lock_noirq(
					      &pid1->children_lock, &childlock);
				process_list_add_tail_result(&child->siblings_list,
							     &pid1->children_list);
				mcs_rwlock_writer_unlock_noirq(
					      &pid1->children_lock, &childlock);
				mcs_rwlock_writer_unlock_noirq(
					      &child->update_lock, &updatelock);
				mcs_rwlock_writer_lock_noirq(
					     &child->threads_lock, &child_lock);
				c_thread = child->main_thread;
				if (c_thread &&
				    wait_main_thread_ptrace_detach_needed_result(
					    options, c_thread->ptrace)) {
					mcs_rwlock_writer_unlock_noirq(
					     &child->threads_lock, &child_lock);
					ptrace_detach_thread(c_thread, 0);
				}
				else {
					mcs_rwlock_writer_unlock_noirq(
					     &child->threads_lock, &child_lock);
				}
				release_process(child);
			}
			else{
				mcs_rwlock_writer_lock_noirq(
					     &child->threads_lock, &child_lock);
				c_thread = child->main_thread;
				if (c_thread &&
				    wait_main_thread_ptrace_detach_needed_result(
					    options, c_thread->ptrace)) {
					mcs_rwlock_writer_unlock_noirq(
					     &child->threads_lock, &child_lock);
					mcs_rwlock_writer_unlock_noirq(
						   &proc->children_lock, &lock);
					ptrace_detach_thread(c_thread, 0);
				}
				else {
					mcs_rwlock_writer_unlock_noirq(
					     &child->threads_lock, &child_lock);
					mcs_rwlock_writer_unlock_noirq(
						   &proc->children_lock, &lock);
				}
			}

			goto out_found;
		}

		mcs_rwlock_writer_lock_noirq(&child->threads_lock, &child_lock);
		c_thread = child->main_thread;

		if (wait_nonptraced_stop_candidate_result(c_thread->ptrace,
				c_thread->signal_flags, options)) {
			/*
			 * Not ptraced and in stopped state and WUNTRACED is
			 * specified
			 */
			ret = wait_stopped(thread, child, NULL, status,
					   options);
			process_thread_signal_flags_reap_result(c_thread,
					__builtin_offsetof(struct thread,
							   signal_flags),
					options, SIGNAL_STOP_STOPPED);
			mcs_rwlock_writer_unlock_noirq(&proc->children_lock,
						       &lock);
			mcs_rwlock_writer_unlock_noirq(&child->threads_lock,
						       &child_lock);
			goto out_found;
		}

		if (wait_ptraced_stop_candidate_result(c_thread->ptrace,
				child->status)) {
			ret = wait_stopped(thread, child, NULL, status,
					   options);
			if (ret == child->pid) {
				/* Are we looking for a specific thread? */
				if (pid == c_thread->tid) {
					ret = c_thread->tid;
				}
				process_thread_signal_flags_reap_result(c_thread,
						__builtin_offsetof(struct thread,
								   signal_flags),
						options, SIGNAL_STOP_STOPPED);
				mcs_rwlock_writer_unlock_noirq(
						   &proc->children_lock, &lock);
				mcs_rwlock_writer_unlock_noirq(
					     &child->threads_lock, &child_lock);
				goto out_found;
			}
		}

		if (wait_continued_candidate_result(c_thread->signal_flags,
				options)) {
			ret = wait_continued(thread, child, NULL, status,
					     options);
			process_thread_signal_flags_reap_result(c_thread,
					__builtin_offsetof(struct thread,
							   signal_flags),
					options, SIGNAL_STOP_CONTINUED);
			mcs_rwlock_writer_unlock_noirq(&proc->children_lock,
						       &lock);
			mcs_rwlock_writer_unlock_noirq(&child->threads_lock,
						       &child_lock);
			goto out_found;
		}
		mcs_rwlock_writer_unlock_noirq(&child->threads_lock,
					       &child_lock);
	}

	if (*empty) {
		list_for_each_entry(child, &proc->ptraced_children_list,
				    ptraced_siblings_list) {
			if (wait_process_pid_matches_result(pid, pgid,
					child->pgid, child->pid)) {
				*empty = 0;
				break;
			}
		}
	}
	mcs_rwlock_writer_unlock_noirq(&proc->children_lock, &lock);
out_found:

	return ret;
}

static int
wait_thread(int tid, int *status, int options, void *rusage, int *empty)
{
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct thread *child, *next;
	int ret = 0;
	struct mcs_rwlock_node lock;

	mcs_rwlock_writer_lock_noirq(&thread->proc->threads_lock, &lock);
	list_for_each_entry_safe(child, next, &proc->report_threads_list,
				 report_siblings_list) {
		if (!wait_thread_tid_matches_result(tid, child->tid,
				child == child->proc->main_thread))
			continue;
		*empty = 0;
		if (wait_thread_exited_candidate_result(options,
				child->status)) {
			int action;

			ret = child->tid;
			action = wait_thread_reap_action_result(options,
					child->ptrace);
			if (action == WAIT_THREAD_REAP_ACTION_PTRACE_DETACH) {
				mcs_rwlock_writer_unlock_noirq(
					    &thread->proc->threads_lock, &lock);
				ptrace_detach_thread(child, 0);
			}
			else if (action == WAIT_THREAD_REAP_ACTION_RELEASE) {
				process_thread_report_detach_result(child,
					__builtin_offsetof(struct thread,
							   report_proc),
					NULL, &child->report_siblings_list);
				mcs_rwlock_writer_unlock_noirq(
				    &thread->proc->threads_lock, &lock);
				release_thread(child);
			}
			else {
				mcs_rwlock_writer_unlock_noirq(
					    &thread->proc->threads_lock, &lock);
			}
			goto out_found;
		}

		if (wait_nonptraced_stop_candidate_result(child->ptrace,
				child->signal_flags, options)) {
			/*
			 * Not ptraced and in stopped state and WUNTRACED is
			 * specified
			 */
			ret = wait_stopped(thread, child->proc, child, status,
					   options);
			process_thread_signal_flags_reap_result(child,
					__builtin_offsetof(struct thread,
							   signal_flags),
					options, SIGNAL_STOP_STOPPED);
			mcs_rwlock_writer_unlock_noirq(
					    &thread->proc->threads_lock, &lock);
			goto out_found;
		}

		if (wait_ptraced_stop_candidate_result(child->ptrace,
				child->status)) {
			ret = wait_stopped(thread, child->proc, child, status,
					   options);
			if (ret == child->tid) {
				/* Are we looking for a specific thread? */
				process_thread_signal_flags_reap_result(child,
						__builtin_offsetof(struct thread,
								   signal_flags),
						options, SIGNAL_STOP_STOPPED);
				mcs_rwlock_writer_unlock_noirq(
					    &thread->proc->threads_lock, &lock);
				goto out_found;
			}
		}

		if (wait_continued_candidate_result(child->signal_flags,
				options)) {
			ret = wait_continued(thread, child->proc, child, status,
					     options);
			process_thread_signal_flags_reap_result(child,
					__builtin_offsetof(struct thread,
							   signal_flags),
					options, SIGNAL_STOP_CONTINUED);
			mcs_rwlock_writer_unlock_noirq(
					    &thread->proc->threads_lock, &lock);
			goto out_found;
		}
	}

	if (*empty) {
		list_for_each_entry(child, &proc->threads_list,
				    siblings_list) {
			if (wait_thread_empty_candidate_result(
					child == child->proc->main_thread,
					child->termsig)) {
				*empty = 0;
				break;
			}
		}
	}
	mcs_rwlock_writer_unlock_noirq(&thread->proc->threads_lock, &lock);
out_found:
	return ret;
}

/*
 * From glibc: INLINE_SYSCALL (wait4, 4, pid, stat_loc, options, NULL);
 */
static int
do_wait(int pid, int *status, int options, void *rusage)
{
	struct thread *thread = cpu_local_var(current);
	int ret;
	struct waitq_entry waitpid_wqe;
	int empty = 1;
	int orgpid = pid;

	dkprintf("wait4(): current->proc->pid: %d, pid: %d\n",
		 thread->proc->pid, pid);

 rescan:
	waitq_init_entry(&waitpid_wqe, thread);
	waitq_prepare_to_wait(&thread->proc->waitpid_q, &waitpid_wqe,
			      PS_INTERRUPTIBLE);
	pid = orgpid;

	if (wait_should_scan_process_result(options)) {
		if ((ret = wait_proc(pid, status, options, rusage, &empty))) {
			goto out_found;
		}
	}
	if (wait_should_scan_thread_result(pid, options)) {
		if ((ret = wait_thread(pid, status, options, rusage, &empty))) {
			goto out_found;
		}
	}

	ret = wait_empty_result(empty);
	if (ret) {
		goto out_notfound;
	}

	/* Don't sleep if WNOHANG requested */
	if (wait_nohang_result(options)) {
		*status = 0;
		ret = 0;
		goto out_notfound;
	}

	/* Sleep */
	dkprintf("wait4,sleeping\n");

	if(hassigpending(thread)){
		waitq_finish_wait(&thread->proc->waitpid_q, &waitpid_wqe);
		return -EINTR;
	}

	schedule();
	dkprintf("wait4(): woken up\n");

	waitq_finish_wait(&thread->proc->waitpid_q, &waitpid_wqe);

	goto rescan;

 exit:
	waitq_finish_wait(&thread->proc->waitpid_q, &waitpid_wqe);
	return ret;
 out_found:
	dkprintf("wait4,out_found\n");
	goto exit;
 out_notfound:
	dkprintf("wait4,out_notfound\n");
	goto exit;
}

SYSCALL_DECLARE(wait4)
{
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	int *status = (int *)ihk_mc_syscall_arg1(ctx);
	int options = (int)ihk_mc_syscall_arg2(ctx);
	void *rusage = (void *)ihk_mc_syscall_arg3(ctx);
	int st;
	int rc;
	struct rusage usage;

	rc = wait4_options_result(options);
	if (rc) {
		dkprintf("wait4: unexpected options(%x).\n", options);
		return rc;
	}
	memset(&usage, '\0', sizeof usage);
	rc = do_wait(pid, &st, WEXITED | options, &usage);
	if (wait_status_copy_needed_result(rc, status != NULL))
		copy_to_user(status, &st, sizeof(int));
	if (wait_rusage_copy_needed_result(rusage != NULL))
		copy_to_user(rusage, &usage, sizeof usage);
	return rc;
}

SYSCALL_DECLARE(waitid)
{
	int idtype = (int)ihk_mc_syscall_arg0(ctx);
	int id = (int)ihk_mc_syscall_arg1(ctx);
	siginfo_t *infop = (siginfo_t *)ihk_mc_syscall_arg2(ctx);
	int options = (int)ihk_mc_syscall_arg3(ctx);
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
		dkprintf("wait4: unexpected options(%x).\n", options);
		dkprintf("waitid: unexpected options(%x).\n", options);
		return rc;
	}
	memset(&usage, '\0', sizeof usage);
	rc = do_wait(pid, &status, options, &usage);
	if(rc < 0)
		return rc;
	if(waitid_siginfo_needed_result(rc, infop != NULL)){
		siginfo_t info;
		memset(&info, '\0', sizeof(siginfo_t));
		info.si_signo = SIGCHLD;
		info._sifields._sigchld.si_pid = rc;
		info._sifields._sigchld.si_status = status;
		info._sifields._sigchld.si_utime =
		                             timeval_to_jiffy(&usage.ru_utime);
		info._sifields._sigchld.si_stime =
		                             timeval_to_jiffy(&usage.ru_stime);
		info.si_code = waitid_status_code_result(status);
		copy_to_user(infop, &info, sizeof info);
	}
	return 0;
}

void terminate_mcexec(int rc, int sig)
{
	unsigned long old_exit_status;
	unsigned long exit_status;
	struct thread *mythread = cpu_local_var(current);
	struct process *proc = mythread->proc;
	struct syscall_request request IHK_DMA_ALIGN;

	old_exit_status = proc->group_exit_status;
	if (exit_group_status_claimed_result(old_exit_status))
		return;
	exit_status = exit_group_status_result(rc, sig);
	if (cmpxchg(&proc->group_exit_status,
				old_exit_status, exit_status) != old_exit_status)
		return;
	if (!proc->nohost) {
		request.number = __NR_exit_group;
		request.args[0] = proc->group_exit_status;
		proc->nohost = 1;
		do_syscall(&request, ihk_mc_get_processor_id());
	}
}

void sync_child_event(struct mc_perf_event *event)
{
	struct mc_perf_event *leader;
	struct mc_perf_event *sub;

	if (!event)
		return;
	if (!(event->attr.inherit) && (event->pid == 0))
		return;

	leader = event->group_leader;
	if (leader->pid == 0) {
		leader->child_count_total +=
			ihk_mc_perfctr_read(leader->counter_id);
	}
	else if (leader->pid > 0) {
		uint64_t count = ihk_mc_perfctr_read(leader->counter_id);

		ihk_atomic64_set(&leader->count, count);
	}
	else
		return; // Error

	list_for_each_entry(sub, &leader->sibling_list, group_entry) {
		if (event->pid == 0) {
			sub->child_count_total +=
				ihk_mc_perfctr_read(sub->counter_id);
		}
		else if (event->pid > 0) {
			uint64_t count = ihk_mc_perfctr_read(sub->counter_id);

			ihk_atomic64_set(&sub->count, count);
		}
	}
}

void terminate(int rc, int sig)
{
	struct resource_set *resource_set = cpu_local_var(resource_set);
	struct thread *mythread = cpu_local_var(current);
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
	if (proc->status == PS_EXITED) {
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
				kfree(proc->fd_path[fd]);
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
	list_for_each_entry(thread, &proc->threads_list, siblings_list) {
		if (thread != mythread) {
			n++;
		}
	}

	if (n) {
		ids = kmalloc(sizeof(int) * n, IHK_MC_AP_NOWAIT);
		i = 0;
		if (ids) {
			list_for_each_entry(thread, &proc->threads_list, siblings_list) {
				if (thread != mythread) {
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
		kfree(ids);
		ids = NULL;
	}

	for (;;) {
		__mcs_rwlock_reader_lock(&proc->threads_lock, &lock);
		found = 0;
		list_for_each_entry(thread, &proc->threads_list,
				    siblings_list) {
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
		kfree(proc->saved_cmdline);
	}

	while (!list_empty(&proc->report_threads_list)) {
		struct thread *thr;

		thr = list_first_entry(&proc->report_threads_list,
				       struct thread, report_siblings_list);
		if (thr->ptrace) {
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

	if (!list_empty(&proc->children_list) ||
	    !list_empty(&proc->ptraced_children_list)) {
		// clean up children
		for (i = 0; i < HASH_SIZE; i++) {
			mcs_rwlock_writer_lock(&resource_set->process_hash->lock[i],
					&lock);
			list_for_each_entry_safe(child, next,
					&resource_set->process_hash->list[i],
					hash_list) {
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

				if (free_child)
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
	if (proc->enable_tofu) {
		extern void tof_utofu_release_fd(struct process *proc, int fd);

		dkprintf("%s: -> tof_utofu_release_fd() @ fd: %d (%s)\n",
				__func__, fd, proc->fd_path[fd]);
		tof_utofu_release_fd(proc, fd);
		proc->fd_pde_data[fd] = NULL;

		if (proc->fd_path[fd]) {
			kfree(proc->fd_path[fd]);
			proc->fd_path[fd] = NULL;
		}
	}
#endif
	return 0;
}

int process_cleanup_fd(int pid, int fd)
{
	struct process *proc;
	struct mcs_rwlock_node_irqsave lock;

	proc = find_process(pid, &lock);
	if (!proc) {
		/* This is normal behavior */
		dkprintf("%s: PID %d couldn't be found\n", __func__, pid);
		return 0;
	}

	__process_cleanup_fd(proc, fd);

	process_unlock(proc, &lock);
	return 0;
}

int process_cleanup_before_terminate(int pid)
{
	struct process *proc;
	struct mcs_rwlock_node_irqsave lock;
#ifdef ENABLE_TOFU
	int fd;
#endif

	proc = find_process(pid, &lock);
	if (!proc) {
		/* This is normal behavior */
		return 0;
	}

#ifdef ENABLE_TOFU
	/* Clean up PDE file descriptors */
	for (fd = 2; fd < MAX_FD_PDE; ++fd) {
		__process_cleanup_fd(proc, fd);
	}
#endif

	process_unlock(proc, &lock);
	return 0;
}


void
terminate_host(int pid, struct thread *thread)
{
	struct process *proc;
	struct mcs_rwlock_node_irqsave lock;

	proc = find_process(pid, &lock);
	if (!proc) {
		if (thread) {
			proc = thread->proc;
			ihk_atomic_set(&thread->refcount, 1);
			release_thread(thread);
			release_process(proc);
		}
		return;
	}

	if (proc->nohost != 1) {
		proc->nohost = 1;
		process_unlock(proc, &lock);
		do_kill(cpu_local_var(current), pid, -1, SIGKILL, NULL, 0);
	}
	else {
		process_unlock(proc, &lock);
	}
}

void eventfd(int type)
{
	struct ihk_ikc_channel_desc *syscall_channel;
	struct ikc_scd_packet pckt;

	syscall_channel = get_cpu_local_var(0)->ikc2linux;
	memset(&pckt, '\0', sizeof pckt);
	pckt.msg = SCD_MSG_EVENTFD;
	pckt.eventfd_type = type;
	ihk_ikc_send(syscall_channel, &pckt, 0);
}

void
interrupt_syscall(struct thread *thread, int sig)
{
	ihk_mc_user_context_t ctx;
	long lerror;

	dkprintf("interrupt_syscall pid=%d tid=%d sig=%d\n", thread->proc->pid,
	         thread->tid, sig);
	ihk_mc_syscall_arg0(&ctx) = thread->proc->pid;
	ihk_mc_syscall_arg1(&ctx) = thread->tid;
	ihk_mc_syscall_arg2(&ctx) = sig;

	lerror = syscall_generic_forwarding(__NR_kill, &ctx);
	if (lerror) {
		kprintf("interrupt_syscall failed. %ld\n", lerror);
	}
	return;
}

SYSCALL_DECLARE(exit_group)
{
	dkprintf("sys_exit_group,pid=%d\n", cpu_local_var(current)->proc->pid);
	terminate((int)ihk_mc_syscall_arg0(ctx), 0);

	return 0;
}

void clear_host_pte(uintptr_t addr, size_t len, int holding_memory_range_lock)
{
	ihk_mc_user_context_t ctx;
	long lerror;
	struct thread *thread = cpu_local_var(current);

	ihk_mc_syscall_arg0(&ctx) = addr;
	ihk_mc_syscall_arg1(&ctx) = len;
	/* NOTE: 3rd parameter denotes new rpgtable of host process (if not zero) */
	ihk_mc_syscall_arg2(&ctx) = 0;

	/* #986: Let remote page fault code skip
	   read-locking memory_range_lock. It's safe because other writers are warded off
	   until the remote PF handling code calls up_write(&current->mm->mmap_sem) and
	   vm_range is consistent when calling this function. */
	if (holding_memory_range_lock) {
		thread->vm->is_memory_range_lock_taken = ihk_mc_get_processor_id();
	}
	lerror = syscall_generic_forwarding(__NR_munmap, &ctx);
	if (holding_memory_range_lock) {
		thread->vm->is_memory_range_lock_taken = -1;
	}
	if (lerror) {
		kprintf("clear_host_pte failed. %ld\n", lerror);
	}
	return;
}

static int set_host_vma(uintptr_t addr, size_t len, int prot, int holding_memory_range_lock)
{
	ihk_mc_user_context_t ctx;
	long lerror;
	struct thread *thread = cpu_local_var(current);

	ihk_mc_syscall_arg0(&ctx) = addr;
	ihk_mc_syscall_arg1(&ctx) = len;
	ihk_mc_syscall_arg2(&ctx) = prot;

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
	return 0;

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

int do_munmap(void *addr, size_t len, int holding_memory_range_lock)
{
	int error;
	int ro_freed;
	struct thread *thread = cpu_local_var(current);

	begin_free_pages_pending();
	error = remove_process_memory_range(cpu_local_var(current)->vm,
			(intptr_t)addr, (intptr_t)addr+len, &ro_freed);

	/* No host involvement for straight mapping ranges */
	if (thread->proc->straight_va &&
			addr >= thread->proc->straight_va &&
			(addr + len) <=
			(thread->proc->straight_va + thread->proc->straight_len)) {
		goto out;
	}

	if (error || !ro_freed) {
		clear_host_pte((uintptr_t)addr, len, holding_memory_range_lock);
	}
	else {
		error = set_host_vma((uintptr_t)addr, len, PROT_READ | PROT_WRITE | PROT_EXEC, holding_memory_range_lock);
		if (error) {
			kprintf("sys_munmap:set_host_vma failed. %d\n", error);
			/* through */
		}
	}

out:
	finish_free_pages_pending();

	dkprintf("%s: 0x%lx:%lu, error: %ld\n",
		__FUNCTION__, addr, len, error);
	return error;
}

static int search_free_space(size_t len, int pgshift, uintptr_t *addrp)
{
	struct thread *thread = cpu_local_var(current);
	struct vm_regions *region = &thread->vm->region;
	intptr_t addr;
	int error = 0;
	struct vm_range *range;
	size_t pgsize = (size_t)1 << pgshift;

	dkprintf("%s: len: %lu, pgshift: %d\n",
		__FUNCTION__, len, pgshift);

	/* try given addr first */
	addr = *addrp;
	if (addr != 0) {
		if ((region->user_end <= addr)
				|| ((region->user_end - len) < addr)) {
			error = -ENOMEM;
			goto out;
		}

		range = lookup_process_memory_range(thread->vm, addr, addr+len);
		if (range == NULL)
			goto out;
	}

	addr = region->map_end;
	for (;;) {
		addr = (addr + pgsize - 1) & ~(pgsize - 1);
		if ((region->user_end <= addr)
				|| ((region->user_end - len) < addr)) {
			ekprintf("%s: error: addr 0x%lx is outside the user region\n",
				__FUNCTION__, addr);

			error = -ENOMEM;
			goto out;
		}

		range = lookup_process_memory_range(thread->vm, addr, addr+len);
		if (range == NULL) {
			break;
		}
		addr = range->end;
	}

	region->map_end = addr + len;
	*addrp = addr;

out:
	dkprintf("%s: len: %lu, pgshift: %d, addr: 0x%lx\n",
		__FUNCTION__, len, pgshift, addr);
	return error;
}

intptr_t
do_mmap(const uintptr_t addr0, const size_t len0, const int prot,
	const int flags, const int fd, const off_t off0,
	const int vrf0, void *private_data)
{
	struct thread *thread = cpu_local_var(current);
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
	struct mckfd *fdp = NULL;
	int pgshift;
	struct vm_range *range = NULL;
	
	dkprintf("do_mmap(%lx,%lx,%x,%x,%d,%lx)\n",
			addr0, len0, prot, flags, fd, off0);

	if (!(flags & MAP_ANONYMOUS)) {
		ihk_mc_spinlock_lock_noirq(&proc->mckfd_lock);
		for(fdp = proc->mckfd; fdp; fdp = fdp->next)
			if(fdp->fd == fd)
				break;
		ihk_mc_spinlock_unlock_noirq(&proc->mckfd_lock);

		if(fdp){
			ihk_mc_user_context_t ctx;

			memset(&ctx, '\0', sizeof ctx);
			ihk_mc_syscall_arg0(&ctx) = addr0;
			ihk_mc_syscall_arg1(&ctx) = len0;
			ihk_mc_syscall_arg2(&ctx) = prot;
			ihk_mc_syscall_arg3(&ctx) = flags;
			ihk_mc_syscall_arg4(&ctx) = fd;
			ihk_mc_syscall_arg5(&ctx) = off0;

			if(fdp->mmap_cb){
				return fdp->mmap_cb(fdp, &ctx);
			}
			return -EBADF;
		}
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

	if (flags & MAP_HUGETLB) {
		pgshift = (flags >> MAP_HUGE_SHIFT) & 0x3F;
		if (!pgshift) {
			pgshift = ihk_mc_get_linux_default_huge_page_shift();
		}
		p2align = pgshift - PAGE_SHIFT;
	}
	else if ((((flags & (MAP_PRIVATE | MAP_SHARED))
			&& (flags & MAP_ANONYMOUS))
			|| (vrf0 & VR_XPMEM))
		    && !proc->thp_disable) {
		pgshift = 0;		/* transparent huge page */
		p2align = PAGE_P2ALIGN;

		if (len > PAGE_SIZE) {
			error = arch_get_smaller_page_size(NULL, len+1, NULL, &p2align);
			if (error) {
				ekprintf("do_mmap:arch_get_smaller_page_size failed. %d\n", error);
				goto out;
			}
		}
	}
	else {
		pgshift = PAGE_SHIFT;	/* basic page size */
		p2align = PAGE_P2ALIGN;
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

		p = ihk_mc_alloc_aligned_pages_user(npages, p2align,
				IHK_MC_AP_NOWAIT | ap_flag, addr0);
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
		if (cpu_local_var(current)->profile)
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
		if (cmpxchg(&memobj->status, MEMOBJ_TO_BE_PREFETCHED,
					MEMOBJ_READY) == MEMOBJ_TO_BE_PREFETCHED) {
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
		ihk_mc_free_pages_user(p, npages);
	}
	if (memobj) {
		memobj_unref(memobj);
	}

#ifndef ENABLE_FUGAKU_HACKS
	dkprintf("%s: 0x%lx:%8lu, (req: 0x%lx:%lu), prot: %x, flags: %x, "
#else
	if (cpu_local_var(current)->profile) {
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

SYSCALL_DECLARE(munmap)
{
	const uintptr_t addr = ihk_mc_syscall_arg0(ctx);
	const size_t len0 = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = cpu_local_var(current);
	struct vm_regions *region = &thread->vm->region;
	size_t len;
	int error;

	dkprintf("[%d]sys_munmap(%lx,%lx)\n",
			ihk_mc_get_processor_id(), addr, len0);

	error = munmap_prepare_range(addr, len0, region->user_start,
			region->user_end, &len);
	if (error) {
		goto out;
	}

	ihk_rwspinlock_write_lock_noirq(&thread->vm->memory_range_lock);
	error = do_munmap((void *)addr, len, 1/* holding memory_range_lock */);
	ihk_rwspinlock_write_unlock_noirq(&thread->vm->memory_range_lock);

out:
	dkprintf("[%d]sys_munmap(%lx,%lx): %d\n",
			ihk_mc_get_processor_id(), addr, len0, error);
#ifdef ENABLE_FUGAKU_HACKS
	if (error) {
		kprintf("%s: error: %d\n", __func__, error);
	}
#endif
	return error;
}

SYSCALL_DECLARE(mprotect)
{
	const uintptr_t start = ihk_mc_syscall_arg0(ctx);
	const size_t len0 = ihk_mc_syscall_arg1(ctx);
	const int prot = ihk_mc_syscall_arg2(ctx);
	struct thread *thread = cpu_local_var(current);
	struct vm_regions *region = &thread->vm->region;
	size_t len;
	uintptr_t end;
	struct vm_range *first;
	uintptr_t addr;
	struct vm_range *range;
	int error;
	struct vm_range *changed;
	const unsigned long protflags = PROT_TO_VR_FLAG(prot);
	unsigned long denied;
	int ro_changed = 0;

	dkprintf("[%d]sys_mprotect(%lx,%lx,%x)\n",
			ihk_mc_get_processor_id(), start, len0, prot);

	error = mprotect_prepare_range(start, len0, region->user_start,
			region->user_end, &len, &end);
	if (error == -EINVAL) {
		ekprintf("[%d]sys_mprotect(%lx,%lx,%x): -EINVAL\n",
				ihk_mc_get_processor_id(), start, len0, prot);
		return -EINVAL;
	}
	if (error == -ENOMEM) {
		ekprintf("[%d]sys_mprotect(%lx,%lx,%x): -ENOMEM\n",
				ihk_mc_get_processor_id(), start, len0, prot);
		return -ENOMEM;
	}

	if (len == 0) {
		/* nothing to do */
		return 0;
	}

	if (thread->proc->straight_va &&
			((void *)start >= thread->proc->straight_va) &&
			(void *)end <= (thread->proc->straight_va +
				thread->proc->straight_len)) {
		kprintf("%s: ignored for straight mapping 0x%lx\n",
				__FUNCTION__, start);
		error = 0;
		goto out_straight;
	}

	flush_nfo_tlb();

	ihk_rwspinlock_write_lock_noirq(&thread->vm->memory_range_lock);

	first = lookup_process_memory_range(thread->vm, start, start+PAGE_SIZE);

	/* do the mprotect */
	changed = NULL;
	for (addr = start; addr < end; addr = changed->end) {
		if (changed == NULL) {
			range = first;
		}
		else {
			range = next_process_memory_range(thread->vm, changed);
		}

		if ((range == NULL) || (addr < range->start)) {
			/* not contiguous */
			ekprintf("sys_mprotect(%lx,%lx,%x):not contiguous\n",
					start, len0, prot);
			error = -ENOMEM;
			goto out;
		}

		denied = protflags & ~VRFLAG_MAXPROT_TO_PROT(range->flag);
		if (denied) {
			ekprintf("sys_mprotect(%lx,%lx,%x):denied %lx. %lx %lx\n",
					start, len0, prot, denied, protflags, range->flag);
			error = -EACCES;
			goto out;
		}

		if (range_has_disallowed_change_flags(range->flag)) {
			ekprintf("sys_mprotect(%lx,%lx,%x):cannot change\n",
					start, len0, prot);
			error = -ENOMEM;
			goto out;
		}

		if (range->start < addr) {
			error = split_process_memory_range(thread->vm, range, addr, &range);
			if (error) {
				ekprintf("sys_mprotect(%lx,%lx,%x):split failed. %d\n",
						start, len0, prot, error);
				goto out;
			}
		}
		if (end < range->end) {
			error = split_process_memory_range(thread->vm, range, end, NULL);
			if (error) {
				ekprintf("sys_mprotect(%lx,%lx,%x):split failed. %d\n",
						start, len0, prot, error);
				goto out;
			}
		}

		if ((range->flag ^ protflags) & VR_PROT_WRITE) {
			ro_changed = 1;
		}

		error = change_prot_process_memory_range(thread->vm, range, protflags);
		if (error) {
			ekprintf("sys_mprotect(%lx,%lx,%x):change failed. %d\n",
					start, len0, prot, error);
			goto out;
		}

		if (changed == NULL) {
			changed = range;
		}
		else {
			error = join_process_memory_range(thread->vm, changed, range);
			if (error) {
				ekprintf("sys_mprotect(%lx,%lx,%x):join failed. %d\n",
						start, len0, prot, error);
				changed = range;
				/* through */
			}
		}
	}

	error = 0;
out:
	// XXX: TLB flush
	flush_tlb();
	if (ro_changed && !error) {
		error = set_host_vma(start, len, prot & (PROT_READ | PROT_WRITE | PROT_EXEC), 1/* holding memory_range_lock */);
		if (error) {
			kprintf("sys_mprotect:set_host_vma failed. %d\n", error);
			/* through */
		}
	}
	ihk_rwspinlock_write_unlock_noirq(&thread->vm->memory_range_lock);

out_straight:
	dkprintf("[%d]sys_mprotect(%lx,%lx,%x): %d\n",
			ihk_mc_get_processor_id(), start, len0, prot, error);
	return error;
}

SYSCALL_DECLARE(brk)
{
	unsigned long address = ihk_mc_syscall_arg0(ctx);
	struct vm_regions *region = &cpu_local_var(current)->vm->region;
	unsigned long r;
	unsigned long vrflag;
	unsigned long old_brk_end_allocated = 0;
	int extend_needed;

	dkprintf("SC(%d)[sys_brk] brk_start=%lx,end=%lx\n",
			ihk_mc_get_processor_id(), region->brk_start, region->brk_end);

	flush_nfo_tlb();

	brk_prepare_result(address, region->brk_start, region->brk_end,
			region->brk_end_allocated, &r, &extend_needed);
	if (!extend_needed) {
		region->brk_end = r;
		goto out;
	}

	/* Try to extend memory region */
	vrflag = brk_default_vrflags();
	old_brk_end_allocated = region->brk_end_allocated;
	ihk_rwspinlock_write_lock_noirq(&cpu_local_var(current)->vm->memory_range_lock);
	region->brk_end_allocated =
		extend_process_region(cpu_local_var(current)->vm,
				region->brk_end_allocated, address, vrflag);
	ihk_rwspinlock_write_unlock_noirq(&cpu_local_var(current)->vm->memory_range_lock);

	if (old_brk_end_allocated == region->brk_end_allocated) {
		r = old_brk_end_allocated;
		goto out;
	}

	region->brk_end = address;
	r = region->brk_end;
	dkprintf("SC(%d)[sys_brk] brk_end set to %lx\n",
			ihk_mc_get_processor_id(), region->brk_end);

out:
	return r;
}

SYSCALL_DECLARE(getpid)
{
	return syscall_getpid_result(cpu_local_var(current)->proc->pid);
}

SYSCALL_DECLARE(getppid)
{
	struct thread *thread = cpu_local_var(current);

	return syscall_getppid_result(thread->proc->ppid_parent->pid);
}

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

SYSCALL_DECLARE(gettid)
{
	return syscall_gettid_result(cpu_local_var(current)->tid);
}

extern void ptrace_report_signal(struct thread *thread, int sig);
static int ptrace_report_exec(struct thread *thread,
		ihk_mc_user_context_t *syscall_ctx)
{
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
}

void ptrace_syscall_event(struct thread *thread)
{
	int sig = ptrace_syscall_event_signal_result(thread->ptrace);

	if (sig) {
		ptrace_report_signal(thread, sig);
	}
}

static int ptrace_check_clone_event(struct thread *thread, int clone_flags)
{
	return ptrace_clone_event_result(thread->ptrace, clone_flags);
}

static int ptrace_attach_thread(struct thread *thread, struct process *proc)
{
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
}

static int ptrace_report_clone(struct thread *thread, struct thread *new, int event)
{
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
	rc = do_kill(cpu_local_var(current), parent_pid, -1, SIGCHLD, &info, 0);
	if(rc < 0) {
		dkprintf("ptrace_report_clone,do_kill failed\n");
	}

	/* Wake parent (if sleeping in wait4()) */
	waitq_wakeup(&thread->proc->parent->waitpid_q);

	return error;
}

static void munmap_all(void)
{
	struct thread *thread = cpu_local_var(current);
	struct process_vm *vm = thread->vm;
	struct vm_range *range;
	struct vm_range *next;
	void *addr;
	size_t size;
	int error;

	ihk_rwspinlock_write_lock_noirq(&vm->memory_range_lock);
	next = lookup_process_memory_range(vm, 0, -1);
	while ((range = next)) {
		next = next_process_memory_range(vm, range);

		addr = (void *)range->start;
		size = range->end - range->start;
		error = do_munmap(addr, size, 1/* holding memory_range_lock */);
		if (error) {
			kprintf("munmap_all():do_munmap(%p,%lx) failed. %d\n",
					addr, size, error);
			/* through */
		}
	}
	ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);

	/* free vm_ranges which do_munmap() failed to remove. */
	free_process_memory_ranges(thread->vm);

	/* reset vm_region's map area */
	thread->vm->region.map_end = thread->vm->region.map_start;

	return;
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
	struct thread *thread = cpu_local_var(current);
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

	desc = ihk_mc_alloc_pages(4, IHK_MC_AP_NOWAIT);
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

		kfilename = kmalloc(len + 1, IHK_MC_AP_NOWAIT);
		if(kfilename)
			strcpy_from_user(kfilename, filename);
		kprintf("ERROR: no argv for executable: %s?\n", kfilename? kfilename: "");
		if(kfilename)
			kfree(kfilename);
		ret = argv_flat_len;
		goto end;
	}
	desc->args = NULL;
	desc->args_len = 0;

	envp_flat_len = flatten_strings_from_user(NULL, envp, &envp_flat);
	if (envp_flat_len < 0) {
		char *kfilename;
		int len = strlen_user(filename);

		kfilename = kmalloc(len + 1, IHK_MC_AP_NOWAIT);
		if(kfilename)
			strcpy_from_user(kfilename, filename);
		kprintf("ERROR: no envp for executable: %s?\n", kfilename? kfilename: "");
		if(kfilename)
			kfree(kfilename);
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
		kfree(envp_flat);
	}
	if (argv_flat) {
		kfree(argv_flat);
	}
	ihk_mc_free_pages(desc, 4);

	if (!ret) {
		unsigned long irqstate;

		/* Lock run queue because enter_user_mode expects to release it */
		irqstate = cpu_disable_interrupt_save();
		ihk_mc_spinlock_lock_noirq(
			&(get_this_cpu_local_var()->runq_lock));
		cpu_local_var(runq_irqstate) = irqstate;
		preempt_enable();

		ihk_mc_switch_context(NULL, &thread->ctx, thread);

		/* not reached */
		return -EFAULT;
	}

	/* no preempt_enable, errors can only happen before we disabled it */

	return ret;
}

SYSCALL_DECLARE(execve)
{
	return do_execveat(ctx, AT_FDCWD,
			(const char *)ihk_mc_syscall_arg0(ctx),
			(char **)ihk_mc_syscall_arg1(ctx),
			(char **)ihk_mc_syscall_arg2(ctx), 0);
}

unsigned long do_fork(int clone_flags, unsigned long newsp,
                      unsigned long parent_tidptr, unsigned long child_tidptr,
                      unsigned long tlsblock_base, unsigned long curpc,
                      unsigned long cursp)
{
	int cpuid;
	int parent_cpuid;
	struct thread *old = cpu_local_var(current);
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
			tids = kmalloc(sizeof(int) * NR_TIDS, IHK_MC_AP_NOWAIT);
			if (!tids) {
				mcs_rwlock_writer_unlock(&newproc->threads_lock, &lock);
				err =  -ENOMEM;
				goto destroy_thread;
			}

			newproc->tids = kmalloc(sizeof(struct mcexec_tid) *
						NR_TIDS, IHK_MC_AP_NOWAIT);
			if (!newproc->tids) {
				mcs_rwlock_writer_unlock(&newproc->threads_lock, &lock);
				kfree(tids);
				err =  -ENOMEM;
				goto destroy_thread;
			}
			tid_table_created = 1;

			if ((err = settid(new, NR_TIDS, tids)) < 0) {
				mcs_rwlock_writer_unlock(&newproc->threads_lock,
							&lock);
				kfree(tids);
				goto release_ids;
			}

			for (i = 0; (i < NR_TIDS) && tids[i]; ++i) {
				dkprintf("%s: tids[%d]: %d\n",
					 __func__, i, tids[i]);
				newproc->tids[i].tid = tids[i];
				newproc->tids[i].thread = NULL;
				++newproc->nr_tids;
			}

			kfree(tids);
		}

		/* Find an unused TID */
		new->tid = 0;
retry_tid:
		for (i = 0; i < newproc->nr_tids; ++i) {
			if (!newproc->tids[i].thread) {
				if (cmpxchg(&newproc->tids[i].thread,
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

	ihk_mc_syscall_ret(new->uctx) = 0;

	new->status = PS_RUNNING;
	
	/* Only the first do_fork() call creates a thread on a Linux CPU */
	if (clone_remote_spawn_result(cmpxchg(&old->mod_clone,
					SPAWN_TO_REMOTE, SPAWN_TO_LOCAL))) {
		new->mod_clone = SPAWNING_TO_REMOTE;
		if (old->mod_clone_arg) {
			new->mod_clone_arg = kmalloc(sizeof(struct uti_attr),
			                             IHK_MC_AP_NOWAIT);
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
				parent = cpu_local_var(resource_set)->pid1;
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
	kfree(new->mod_clone_arg);
	new->mod_clone_arg = NULL;

	ihk_atomic_dec(&new->vm->refcount);

release_ids:
	if (clone_flags & CLONE_VM) {
		if (tid_table_created && !newproc->nr_tids) {
			kfree(newproc->tids);
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
		kfree(newproc->saved_cmdline);
		newproc->saved_cmdline = NULL;
	}
	ihk_atomic_set(&new->refcount, 1);
	release_thread(new);

release_cpuid:
	release_cpuid(cpuid);
	return err;
}

SYSCALL_DECLARE(set_tid_address)
{
	cpu_local_var(current)->clear_child_tid = 
	                        (int*)ihk_mc_syscall_arg0(ctx);

	return syscall_set_tid_address_return_result(
		cpu_local_var(current)->proc->pid);
}

SYSCALL_DECLARE(times)
{
	struct tms {
		unsigned long tms_utime;
		unsigned long tms_stime;
		unsigned long tms_cutime;
		unsigned long tms_cstime;
	};
	struct tms mytms;
	struct tms *buf = (struct tms *)ihk_mc_syscall_arg0(ctx);
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct timespec ats;

	tsc_to_ts(thread->user_tsc, &ats);
	mytms.tms_utime = timespec_to_jiffy(&ats);
	tsc_to_ts(thread->system_tsc, &ats);
	mytms.tms_stime = timespec_to_jiffy(&ats);
	ats.tv_sec = proc->utime.tv_sec;
	ats.tv_nsec = proc->utime.tv_nsec;
	ts_add(&ats, &proc->utime_children);
	mytms.tms_cutime = timespec_to_jiffy(&ats);
	ats.tv_sec = proc->stime.tv_sec;
	ats.tv_nsec = proc->stime.tv_nsec;
	ts_add(&ats, &proc->stime_children);
	mytms.tms_cstime = timespec_to_jiffy(&ats);
	if(copy_to_user(buf, &mytms, sizeof mytms))
		return -EFAULT;
	if(gettime_local_support){
		calculate_time_from_tsc(&ats);
	}
	else{
		ats.tv_sec = 0;
		ats.tv_nsec = 0;
	}

	return timespec_to_jiffy(&ats);
}

SYSCALL_DECLARE(kill)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	int sig = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = cpu_local_var(current);
	struct siginfo info;
	int error;

	memset(&info, '\0', sizeof info);
	info.si_signo = sig;
	info.si_code = SI_USER;
	info._sifields._kill.si_pid = thread->proc->pid;

	dkprintf("sys_kill,enter,pid=%d,sig=%d\n", pid, sig);
	error = do_kill(thread, pid, -1, sig, &info, 0);
	dkprintf("sys_kill,returning,pid=%d,sig=%d,error=%d\n", pid, sig, error);
	return error;
}

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
		nodemask_bits = ALIGN(maxnode, 8);
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
	return maxnode && (ALIGN(maxnode, 8) > PROCESS_NUMA_MASK_BITS);
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

		*nodemask_bitsp = ALIGN(maxnode, 8);
		if (*nodemask_bitsp > PROCESS_NUMA_MASK_BITS) {
			*nodemask_bitsp = PROCESS_NUMA_MASK_BITS;
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

SYSCALL_POLICY_HELPER_SCOPE int
nanosleep_validate_timespec(long sec, long nsec)
{
	return (sec < 0 || nsec < 0 || nsec >= NS_PER_SEC) ? -EINVAL : 0;
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

SYSCALL_POLICY_HELPER_SCOPE int
sigaction_sigsetsize_result(size_t sigsetsize, size_t expected_sigset_size)
{
	return sigsetsize != expected_sigset_size ? -EINVAL : 0;
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

SYSCALL_POLICY_HELPER_SCOPE int
waitid_siginfo_needed_result(int rc, int has_infop)
{
	return rc > 0 && has_infop;
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

SYSCALL_POLICY_HELPER_SCOPE long
getrusage_maxrss_kb_result(long maxrss)
{
	return maxrss / 1024;
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

SYSCALL_POLICY_HELPER_SCOPE int
thread_exit_signal_result(int ptrace, int termsig)
{
	return ptrace ? SIGCHLD : termsig;
}

SYSCALL_POLICY_HELPER_SCOPE int
sigchld_code_result(int exit_status)
{
	if (exit_status & 0x7f) {
		return (exit_status & 0x80) ? CLD_DUMPED : CLD_KILLED;
	}
	return CLD_EXITED;
}

SYSCALL_POLICY_HELPER_SCOPE int
exit_group_status_claimed_result(unsigned long old_exit_status)
{
	return (old_exit_status & 0x0000000100000000UL) ? 1 : 0;
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

SYSCALL_DECLARE(tgkill)
{
	int tgid = ihk_mc_syscall_arg0(ctx);
	int tid = ihk_mc_syscall_arg1(ctx);
	int sig = ihk_mc_syscall_arg2(ctx);
	struct thread *thread = cpu_local_var(current);
	struct siginfo info;
	int error;

	error = tgkill_target_result(tgid, tid);
	if (error) {
		return error;
	}

	memset(&info, '\0', sizeof info);
	info.si_signo = sig;
	info.si_code = SI_TKILL;
	info._sifields._kill.si_pid = thread->proc->pid;

	return do_kill(thread, tgid, tid, sig, &info, 0);
}

SYSCALL_DECLARE(tkill)
{
	int tid = ihk_mc_syscall_arg0(ctx);
	int sig = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = cpu_local_var(current);
	struct siginfo info;
	int error;

	memset(&info, '\0', sizeof info);
	info.si_signo = sig;
	info.si_code = SI_TKILL;
	info._sifields._kill.si_pid = thread->proc->pid;

	error = tkill_tid_result(tid);
	if (error) {
		return error;
	}

	return do_kill(thread, -1, tid, sig, &info, 0);
}

int *
getcred(int *_buf)
{
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
}

void
do_setresuid()
{
	int	_buf[16];
	int	*buf;
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;

	buf = getcred(_buf);

	proc->ruid = buf[0];
	proc->euid = buf[1];
	proc->suid = buf[2];
	proc->fsuid = buf[3];
}

void
do_setresgid()
{
	int	_buf[16];
	int	*buf;
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;

	buf = getcred(_buf);

	proc->rgid = buf[4];
	proc->egid = buf[5];
	proc->sgid = buf[6];
	proc->fsgid = buf[7];
}

SYSCALL_DECLARE(setresuid)
{
	int rc;

	rc = syscall_generic_forwarding(__NR_setresuid, ctx);
	if (syscall_refresh_cred_needed_result(rc)) {
		do_setresuid();
	}
	return rc;
}

SYSCALL_DECLARE(setreuid)
{
	int rc;

	rc = syscall_generic_forwarding(__NR_setreuid, ctx);
	if (syscall_refresh_cred_needed_result(rc)) {
		do_setresuid();
	}
	return rc;
}

SYSCALL_DECLARE(setuid)
{
	long rc;

	rc = syscall_generic_forwarding(__NR_setuid, ctx);
	if (syscall_refresh_cred_needed_result(rc)) {
		do_setresuid();
	}
	return rc;
}

SYSCALL_DECLARE(setfsuid)
{
	int fsuid = (int)ihk_mc_syscall_arg0(ctx);;
	unsigned long newfsuid;
	struct syscall_request request IHK_DMA_ALIGN;

	request.number = __NR_setfsuid;
	request.args[0] = fsuid;
	request.args[1] = 0;
	newfsuid = do_syscall(&request, ihk_mc_get_processor_id());
	do_setresuid();
	return newfsuid;
}

SYSCALL_DECLARE(setresgid)
{
	int rc;

	rc = syscall_generic_forwarding(__NR_setresgid, ctx);
	if (syscall_refresh_cred_needed_result(rc)) {
		do_setresgid();
	}
	return rc;
}

SYSCALL_DECLARE(setregid)
{
	int rc;

	rc = syscall_generic_forwarding(__NR_setregid, ctx);
	if (syscall_refresh_cred_needed_result(rc)) {
		do_setresgid();
	}
	return rc;
}

SYSCALL_DECLARE(setgid)
{
	long rc;

	rc = syscall_generic_forwarding(__NR_setgid, ctx);
	if (syscall_refresh_cred_needed_result(rc)) {
		do_setresgid();
	}
	return rc;
}

SYSCALL_DECLARE(setfsgid)
{
	int fsgid = (int)ihk_mc_syscall_arg0(ctx);;
	unsigned long newfsgid;
	struct syscall_request request IHK_DMA_ALIGN;

	request.number = __NR_setfsgid;
	request.args[0] = fsgid;
	newfsgid = do_syscall(&request, ihk_mc_get_processor_id());
	do_setresgid();
	return newfsgid;
}

SYSCALL_DECLARE(getuid)
{
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;

	return proc->ruid;
}

SYSCALL_DECLARE(geteuid)
{
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;

	return proc->euid;
}

SYSCALL_DECLARE(getresuid)
{
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	int *ruid = (int *)ihk_mc_syscall_arg0(ctx);
	int *euid = (int *)ihk_mc_syscall_arg1(ctx);
	int *suid = (int *)ihk_mc_syscall_arg2(ctx);

	if(copy_to_user(ruid, &proc->ruid, sizeof(int)))
		return -EFAULT;
	if(copy_to_user(euid, &proc->euid, sizeof(int)))
		return -EFAULT;
	if(copy_to_user(suid, &proc->suid, sizeof(int)))
		return -EFAULT;

	return 0;
}

SYSCALL_DECLARE(getgid)
{
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;

	return proc->rgid;
}

SYSCALL_DECLARE(getegid)
{
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;

	return proc->egid;
}

SYSCALL_DECLARE(getresgid)
{
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	int *rgid = (int *)ihk_mc_syscall_arg0(ctx);
	int *egid = (int *)ihk_mc_syscall_arg1(ctx);
	int *sgid = (int *)ihk_mc_syscall_arg2(ctx);

	if(copy_to_user(rgid, &proc->rgid, sizeof(int)))
		return -EFAULT;
	if(copy_to_user(egid, &proc->egid, sizeof(int)))
		return -EFAULT;
	if(copy_to_user(sgid, &proc->sgid, sizeof(int)))
		return -EFAULT;

	return 0;
}

SYSCALL_DECLARE(setpgid)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	int pgid = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct mcs_rwlock_node_irqsave lock;
	long rc;

	pid = setpgid_normalize_pid(proc->pid, pid);
	pgid = setpgid_normalize_pgid(pid, pgid);

	if(proc->pid != pid){
		proc = find_process(pid, &lock);
		if(proc){
			rc = setpgid_execed_result(proc->execed);
			if(rc){
				process_unlock(proc, &lock);
				return rc;
			}
			process_unlock(proc, &lock);
		}
		else
			return -ESRCH;
	}

	rc = syscall_generic_forwarding(__NR_setpgid, ctx);
	if(rc == 0){
		proc = find_process(pid, &lock);
		if(proc){
			proc->pgid = pgid;
			process_unlock(proc, &lock);
		}
	}
	return rc;
}

/* Ignore the registration by start_thread() (in pthread_create.c)
   because McKernel doesn't unlock mutex-es held by the thread which has been killed. */
SYSCALL_DECLARE(set_robust_list)
{
	size_t len = (size_t)ihk_mc_syscall_arg1(ctx);

	return robust_list_len_result(len);
}

int
do_sigaction(int sig, struct k_sigaction *act, struct k_sigaction *oact)
{
	struct thread *thread = cpu_local_var(current);
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
		ihk_mc_syscall_arg0(&ctx0) = sig;
		ihk_mc_syscall_arg1(&ctx0) = (unsigned long)act->sa.sa_handler;
		ihk_mc_syscall_arg2(&ctx0) = act->sa.sa_flags;
		syscall_generic_forwarding(__NR_rt_sigaction, &ctx0);
	}
	return 0;
}

SYSCALL_DECLARE(read)
{
	int fd = ihk_mc_syscall_arg0(ctx);
	long rc;
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct mckfd *fdp;
	long irqstate;

	irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
	for(fdp = proc->mckfd; fdp; fdp = fdp->next)
		if(fdp->fd == fd)
			break;
	ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);

	if(fdp && fdp->read_cb){
//kprintf("read: found system fd %d\n", fd);
		rc = fdp->read_cb(fdp, ctx);
	}
	else{
		rc = syscall_generic_forwarding(__NR_read, ctx);
	}
	return rc;
}

SYSCALL_DECLARE(ioctl)
{
	int fd = ihk_mc_syscall_arg0(ctx);
	long rc;
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct mckfd *fdp;
	long irqstate;

	irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
	for(fdp = proc->mckfd; fdp; fdp = fdp->next)
		if(fdp->fd == fd)
			break;
	ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);

#ifdef ENABLE_TOFU
	/* Tofu? */
	if (proc->enable_tofu &&
			fd < MAX_FD_PDE && thread->proc->fd_pde_data[fd]) {
		extern long tof_utofu_unlocked_ioctl(int fd,
				unsigned int cmd, unsigned long arg);

		rc = tof_utofu_unlocked_ioctl(fd,
			ihk_mc_syscall_arg1(ctx),
			ihk_mc_syscall_arg2(ctx));

		/* Do we need to offload? */
		if (rc != -ENOTSUPP)
			return rc;
	}
#endif

	if(fdp && fdp->ioctl_cb){
		//kprintf("ioctl: found system fd %d\n", fd);
		rc = fdp->ioctl_cb(fdp, ctx);
	}
	else{
		rc = syscall_generic_forwarding(__NR_ioctl, ctx);
	}

	return rc;
}

SYSCALL_DECLARE(open)
{
	const char *_pathname = (const char *)ihk_mc_syscall_arg0(ctx);
	int flags = (int)ihk_mc_syscall_arg1(ctx);
	int len;
	char *pathname;
	long rc;

	len = strlen_user(_pathname);
	if (len < 0)
		return len;
	len++;

	pathname = kmalloc(len, IHK_MC_AP_NOWAIT);
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
	cpu_local_var(current)->fd_path_in_open = pathname;
#endif

	dkprintf("open(): pathname=%s\n", pathname);
	if (!strncmp(pathname, XPMEM_DEV_PATH, len)) {
		rc = xpmem_open(pathname, flags, ctx);
	} else {
		rc = syscall_generic_forwarding(__NR_open, ctx);
	}

#ifdef ENABLE_TOFU
	cpu_local_var(current)->fd_path_in_open = NULL;
#endif

 out:
#ifdef ENABLE_TOFU
	if (rc > 0 && rc < MAX_FD_PDE) {
		cpu_local_var(current)->proc->fd_path[rc] = pathname;
	}
	else {
		kfree(pathname);
	}
#else
	kfree(pathname);
#endif
	return rc;
}

SYSCALL_DECLARE(openat)
{
	const char *_pathname = (const char *)ihk_mc_syscall_arg1(ctx);
	int flags = (int)ihk_mc_syscall_arg2(ctx);
	char *pathname;
	int len;
	long rc;

	len = strlen_user(_pathname);
	if (len < 0)
		return len;
	len++;

	pathname = kmalloc(len, IHK_MC_AP_NOWAIT);
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
	cpu_local_var(current)->fd_path_in_open = pathname;
#endif

	dkprintf("openat(): pathname=%s\n", pathname);
	if (!strncmp(pathname, XPMEM_DEV_PATH, len)) {
		rc = xpmem_openat(pathname, flags, ctx);
	} else {
		rc = syscall_generic_forwarding(__NR_openat, ctx);
	}

#ifdef ENABLE_TOFU
	cpu_local_var(current)->fd_path_in_open = NULL;
#endif

out:
#ifdef ENABLE_TOFU
	if (rc > 0 && rc < MAX_FD_PDE) {
		cpu_local_var(current)->proc->fd_path[rc] = pathname;
	}
	else {
		kfree(pathname);
	}
#else
	kfree(pathname);
#endif
	return rc;
}

SYSCALL_DECLARE(execveat)
{
	int dirfd = (int)ihk_mc_syscall_arg0(ctx);
	const char *filename = (const char *)ihk_mc_syscall_arg1(ctx);
	int flags = (int)ihk_mc_syscall_arg4(ctx);
	long ret;

	ret = execveat_policy_result(flags, dirfd, filename[0]);
	if (ret) {
		goto out;
	}

	ret = do_execveat(ctx, dirfd, filename,
			(char **)ihk_mc_syscall_arg2(ctx),
			(char **)ihk_mc_syscall_arg3(ctx), flags);

out:
	return ret;
}

SYSCALL_DECLARE(close)
{
	int fd = ihk_mc_syscall_arg0(ctx);
	long rc;
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct mckfd *fdp;
	struct mckfd *fdq;
	long irqstate;

	irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);

#ifdef ENABLE_TOFU
	/* Clear path and PDE data */
	if (thread->proc->enable_tofu &&
			fd >= 0 && fd < MAX_FD_PDE) {
		/* Tofu? */
		if (thread->proc->fd_pde_data[fd]) {
			extern void tof_utofu_release_fd(struct process *proc, int fd);

			dkprintf("%s: -> tof_utofu_release_fd() @ fd: %d (%s)\n",
					__func__, fd, thread->proc->fd_path[fd]);
			tof_utofu_release_fd(thread->proc, fd);
			thread->proc->fd_pde_data[fd] = NULL;
		}

		if (thread->proc->fd_path[fd]) {
			dkprintf("%s: %d -> %s\n", __func__, fd, thread->proc->fd_path[fd]);
			kfree(thread->proc->fd_path[fd]);
			thread->proc->fd_path[fd] = NULL;
		}
	}
#endif

	for(fdp = proc->mckfd, fdq = NULL; fdp; fdq = fdp, fdp = fdp->next)
		if(fdp->fd == fd)
			break;

	if(fdp){
//kprintf("close: found system fd %d pid=%d\n", fd, proc->pid);
		if(fdq)
			fdq->next = fdp->next;
		else
			proc->mckfd = fdp->next;
		ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);
		if(fdp->close_cb)
			fdp->close_cb(fdp, ctx);
		kfree(fdp);
		rc = syscall_generic_forwarding(__NR_close, ctx);
	}
	else{
		ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);
		rc = syscall_generic_forwarding(__NR_close, ctx);
	}
	return rc;
}

SYSCALL_DECLARE(fcntl)
{
	int fd = ihk_mc_syscall_arg0(ctx);
	// int cmd = ihk_mc_syscall_arg1(ctx);
	long rc;
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct mckfd *fdp;
	long irqstate;

	irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
	for(fdp = proc->mckfd; fdp; fdp = fdp->next)
		if(fdp->fd == fd)
			break;
	ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);

	if(fdp && fdp->fcntl_cb){
		rc = fdp->fcntl_cb(fdp, ctx);
	}
	else{
		rc = syscall_generic_forwarding(__NR_fcntl, ctx);
	}
	return rc;
}

SYSCALL_DECLARE(epoll_pwait)
{
	long rc;
	sigset_t *set = (sigset_t *)ihk_mc_syscall_arg4(ctx);
	__sigset_t oldset;
	__sigset_t wset;
	struct thread *thread = cpu_local_var(current);

	oldset = thread->sigmask.__val[0];
	if (set) {
		if (copy_from_user(&wset, set->__val, sizeof(wset))) {
			return -EFAULT;
		}
		thread->sigmask.__val[0] = wset;
	}
	rc = syscall_generic_forwarding(__NR_epoll_pwait, ctx);
	thread->sigmask.__val[0] = oldset;

	return rc;
}

SYSCALL_DECLARE(ppoll)
{
	long rc;
	sigset_t *set = (sigset_t *)ihk_mc_syscall_arg3(ctx);
	__sigset_t oldset;
	__sigset_t wset;
	struct thread *thread = cpu_local_var(current);

	oldset = thread->sigmask.__val[0];
	if (set) {
		if (copy_from_user(&wset, set->__val, sizeof(wset))) {
			return -EFAULT;
		}
		thread->sigmask.__val[0] = wset;
	}
	rc = syscall_generic_forwarding(__NR_ppoll, ctx);
	thread->sigmask.__val[0] = oldset;

	return rc;
}

SYSCALL_DECLARE(pselect6)
{
	long rc;
	sigset_t **_set = (sigset_t **)ihk_mc_syscall_arg5(ctx);
	sigset_t *set = NULL;
	__sigset_t oldset;
	__sigset_t wset;
	struct thread *thread = cpu_local_var(current);

	if (_set) {
		if (copy_from_user(&set, _set, sizeof(void *))) {
			return -EFAULT;
		}
	}
	oldset = thread->sigmask.__val[0];
	if (set) {
		if (copy_from_user(&wset, set->__val, sizeof(wset))) {
			return -EFAULT;
		}
		thread->sigmask.__val[0] = wset;
	}
	rc = syscall_generic_forwarding(__NR_pselect6, ctx);
	thread->sigmask.__val[0] = oldset;

	return rc;
}

SYSCALL_DECLARE(rt_sigprocmask)
{
	int how = ihk_mc_syscall_arg0(ctx);
	const sigset_t *set = (const sigset_t *)ihk_mc_syscall_arg1(ctx);
	sigset_t *oldset = (sigset_t *)ihk_mc_syscall_arg2(ctx);
	size_t sigsetsize = (size_t)ihk_mc_syscall_arg3(ctx);
	struct thread *thread = cpu_local_var(current);
	__sigset_t wsig = 0;
	ihk_mc_user_context_t ctx0;
	int error;

	error = rt_sigprocmask_validate(sigsetsize, sizeof(sigset_t),
			set != NULL, how);
	if (error) {
		return error;
	}

	if(oldset){
		wsig = thread->sigmask.__val[0];
		if(copy_to_user(oldset->__val, &wsig, sizeof wsig))
			goto fault;
	}
	if(set){
		if(copy_from_user(&wsig, set->__val, sizeof wsig))
			goto fault;
	}
	thread->sigmask.__val[0] = rt_sigprocmask_apply(
			thread->sigmask.__val[0], wsig, set != NULL, how);
	wsig = thread->sigmask.__val[0];

	ihk_mc_syscall_arg0(&ctx0) = wsig;
	syscall_generic_forwarding(__NR_rt_sigprocmask, &ctx0);
	return 0;
fault:
	return -EFAULT;
}

SYSCALL_DECLARE(rt_sigpending)
{
	struct sig_pending *pending;
	struct list_head *head;
	mcs_rwlock_lock_t *lock;
	struct mcs_rwlock_node_irqsave mcs_rw_node;
	__sigset_t w = 0;
	struct thread *thread = cpu_local_var(current);
	sigset_t *set = (sigset_t *)ihk_mc_syscall_arg0(ctx);
	size_t sigsetsize = (size_t)ihk_mc_syscall_arg1(ctx);
	int error;

	error = rt_sigpending_size_result(sigsetsize, sizeof(sigset_t));
	if (error) {
		return error;
	}

	lock = &thread->sigcommon->lock;
	head = &thread->sigcommon->sigpending;
	mcs_rwlock_writer_lock(lock, &mcs_rw_node);
	list_for_each_entry(pending, head, list){
		w |= pending->sigmask.__val[0];
	}
	mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

	lock = &thread->sigpendinglock;
	head = &thread->sigpending;
	mcs_rwlock_writer_lock(lock, &mcs_rw_node);
	list_for_each_entry(pending, head, list){
		w |= pending->sigmask.__val[0];
	}
	mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

	if(copy_to_user(set->__val, &w, sizeof w))
		return -EFAULT;

	return 0;
}

SYSCALL_DECLARE(signalfd)
{
	return -EOPNOTSUPP;
}

SYSCALL_DECLARE(signalfd4)
{
	int fd = ihk_mc_syscall_arg0(ctx);
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct mckfd *sfd;
	long    irqstate;
	sigset_t *maskp = (sigset_t *)ihk_mc_syscall_arg1(ctx);;
	__sigset_t mask;
	size_t sigsetsize = (size_t)ihk_mc_syscall_arg2(ctx);
	int flags = ihk_mc_syscall_arg3(ctx);
	int error;

	error = signalfd4_sigsetsize_result(sigsetsize, sizeof(sigset_t));
	if (error) {
		return error;
	}
	if(copy_from_user(&mask, maskp, sizeof mask))
		return -EFAULT;
	error = signalfd4_flags_result(flags);
	if (error) {
		return error;
	}

	if(fd == -1){
		struct syscall_request request IHK_DMA_ALIGN;

		request.number = __NR_signalfd4;
		request.args[0] = 0;
		request.args[1] = flags;
		fd = do_syscall(&request, ihk_mc_get_processor_id());
		if(fd < 0){
			return fd;
		}
		sfd = kmalloc(sizeof(struct mckfd), IHK_MC_AP_NOWAIT);
		if(!sfd)
			return -ENOMEM;
		memset(sfd, '\0', sizeof(struct mckfd));
		sfd->fd = fd;
		irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
		sfd->next = proc->mckfd;
		proc->mckfd = sfd;
	}
	else{
		irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
		for(sfd = proc->mckfd; sfd; sfd = sfd->next)
			if(sfd->fd == fd)
				break;
		if(!sfd){
			ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);
			return -EINVAL;
		}
	}
	memcpy(&sfd->data, &mask, sizeof mask);
	ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);
	return sfd->fd;
}

#ifdef ENABLE_PERF
int perf_counter_set(struct mc_perf_event *event)
{
	int ret = 0;
	struct perf_event_attr *attr = &event->attr;
	int mode = 0x00;

	if(!attr->exclude_kernel) {
		mode |= PERFCTR_KERNEL_MODE;
	}
	if(!attr->exclude_user) {
		mode |= PERFCTR_USER_MODE;
	}

	if (event->extra_reg.reg) {
		if (ihk_mc_perfctr_set_extra(event)) {
			ret = -1;
			goto out;
		}
	}
	ret = ihk_mc_perfctr_init_raw(event->counter_id,
		event->hw_config, mode);

out:
	return ret;
}

unsigned long perf_event_read_value(struct mc_perf_event *event)
{
	unsigned long rtn_count = 0;
	unsigned long pmc_count = 0;
	struct thread *thread = cpu_local_var(current);
	unsigned long cur_user_tsc, cur_system_tsc;

	if (event->stopped_user_tsc) {
		cur_user_tsc = event->stopped_user_tsc;
	}
	else {
		cur_user_tsc = thread->user_tsc;
	}

	if (event->stopped_system_tsc) {
		cur_system_tsc = event->stopped_system_tsc;
	}
	else {
		cur_system_tsc = thread->system_tsc;
	}

	/* -- For use_invariant_tsc --
	 * Add sum of counts in the previous start-stop periods to
	 * the current count in the start-read period
	 */
	if(event->pid == 0) {
		if (event->use_invariant_tsc) {
			if (!event->attr.exclude_user) {
				pmc_count += cur_user_tsc -
					event->base_user_tsc +
					event->user_accum_count;
			}
			if (!event->attr.exclude_kernel) {
				/* Add sum of counts in the previous
				 * start-stop periods to the current count
				 * in the start-read period
				 */
				pmc_count += cur_system_tsc -
					event->base_system_tsc +
					event->system_accum_count;
			}
		}
		else {
			ihk_mc_event_update(event);
		}
	}

	rtn_count += ihk_atomic64_read(&event->count) + pmc_count;

	if(event->attr.inherit)
		rtn_count += event->child_count_total;

	return rtn_count;
}

static int
perf_event_read_group(struct mc_perf_event *event, unsigned long read_format, char  *buf)
{
	struct mc_perf_event *leader = event->group_leader, *sub;
	int n = 0, size = 0, ret;
	unsigned long count;
	long long  values[5];

	count = perf_event_read_value(leader);

	values[n++] = 1 + leader->nr_siblings;
	values[n++] = count;

	size = n * sizeof(long long);

	if (copy_to_user(buf, values, size))
		return -EFAULT;

	ret = size;
	
	list_for_each_entry(sub, &leader->sibling_list, group_entry) {
		n = 0;
		values[n++] = perf_event_read_value(sub);

		size = n * sizeof(long long);

		if (copy_to_user(buf + ret, values, size)) {
			return -EFAULT;
		}

		ret += size;
	}
	return ret;
}

static int
perf_event_read_one(struct mc_perf_event *event, unsigned long read_format, char *buf)
{
	unsigned long values[4];
	int n = 0;
	int size = 0;

	values[n++] = perf_event_read_value(event);

	size = n * sizeof(unsigned long);

	if (copy_to_user(buf, values, size))
		return -EFAULT;

	return size;
}

static long
perf_read(struct mckfd *sfd, ihk_mc_user_context_t *ctx)
{
	char *buf  = (char *)ihk_mc_syscall_arg1(ctx);
	struct mc_perf_event *event = (struct mc_perf_event*)sfd->data;
	unsigned long read_format = event->attr.read_format;
	long ret;

	if (read_format & PERF_FORMAT_GROUP) {
		ret = perf_event_read_group(event, read_format, buf);
	} else {
		ret = perf_event_read_one(event, read_format, buf);
	}
	return ret;
}

void perf_start(struct mc_perf_event *event)
{
	int counter_id;
	unsigned long counter_mask = 0;
	struct mc_perf_event *leader = event->group_leader, *sub;
	struct thread *thread = cpu_local_var(current);

	/* -- For use_invariant_tsc --
	 * Record sum of counts the previous start-stop periods
	 * into accum_count,
	 * because only the count at the last start is recorded
	 */
	counter_id = leader->counter_id;
	if (ihk_mc_perf_counter_mask_check(1UL << counter_id) &&
			leader->state == PERF_EVENT_STATE_INACTIVE) {
		if (leader->use_invariant_tsc) {
			if (leader->stopped_user_tsc) {
				leader->user_accum_count +=
					leader->stopped_user_tsc -
					leader->base_user_tsc;
				leader->stopped_user_tsc = 0;
			}
			leader->base_user_tsc = thread->user_tsc;

			if (leader->stopped_system_tsc) {
				leader->system_accum_count +=
					leader->stopped_system_tsc -
					leader->base_system_tsc;
				leader->stopped_system_tsc = 0;
			}
			leader->base_system_tsc = thread->system_tsc;
		}
		else {
			ihk_mc_event_set_period(leader);
			perf_counter_set(leader);
			counter_mask |= 1UL << counter_id;
		}

		leader->state = PERF_EVENT_STATE_ACTIVE;
	}

	list_for_each_entry(sub, &leader->sibling_list, group_entry) {
		counter_id = sub->counter_id;
		if (ihk_mc_perf_counter_mask_check(1UL << counter_id) &&
				sub->state == PERF_EVENT_STATE_INACTIVE) {
			if (sub->use_invariant_tsc) {
				if (sub->stopped_user_tsc) {
					sub->user_accum_count +=
						sub->stopped_user_tsc -
						sub->base_user_tsc;
					sub->stopped_user_tsc = 0;
				}
				sub->base_user_tsc = thread->user_tsc;

				if (sub->stopped_system_tsc) {
					sub->system_accum_count +=
						sub->stopped_system_tsc -
						sub->base_system_tsc;
					sub->stopped_system_tsc = 0;
				}
				sub->base_system_tsc = thread->system_tsc;
			}
			else {
				ihk_mc_event_set_period(sub);
				perf_counter_set(sub);
				counter_mask |= 1UL << counter_id;
			}

			sub->state = PERF_EVENT_STATE_ACTIVE;
		}
	}

	if (counter_mask) {
		ihk_mc_perfctr_start(counter_mask);
	}
	thread->proc->perf_status = PP_COUNT;
}

void 
perf_reset(struct mc_perf_event *event)
{
	int counter_id;
	struct mc_perf_event *leader = event->group_leader, *sub;
	struct thread *thread = cpu_local_var(current);

	counter_id = leader->counter_id;
	if (ihk_mc_perf_counter_mask_check(1UL << counter_id)) {
		/* Let perf_event_read_value return zero when stopped */
		if (leader->use_invariant_tsc) {
			if (leader->stopped_user_tsc) {
				leader->base_user_tsc =
					leader->stopped_user_tsc;
			}
			else {
				leader->base_user_tsc = thread->user_tsc;
			}
			leader->user_accum_count = 0;

			if (leader->stopped_system_tsc) {
				leader->base_system_tsc =
					leader->stopped_system_tsc;
			}
			else {
				leader->base_system_tsc = thread->system_tsc;
			}
			leader->system_accum_count = 0;
		}
		else {
			perf_event_read_value(leader);
			ihk_atomic64_set(&leader->count, 0);
		}
	}

	list_for_each_entry(sub, &leader->sibling_list, group_entry) {
		counter_id = sub->counter_id;
		if (ihk_mc_perf_counter_mask_check(1UL << counter_id)) {
			/* Let perf_event_read_value return zero when stopped */
			if (sub->use_invariant_tsc) {
				if (sub->stopped_user_tsc) {
					sub->base_user_tsc =
						sub->stopped_user_tsc;
				}
				else {
					sub->base_user_tsc = thread->user_tsc;
				}
				sub->user_accum_count = 0;

				if (sub->stopped_system_tsc) {
					sub->base_system_tsc =
						sub->stopped_system_tsc;
				}
				else {
					sub->base_system_tsc =
						thread->system_tsc;
				}
				sub->system_accum_count = 0;
			}
			else {
				perf_event_read_value(sub);
				ihk_atomic64_set(&sub->count, 0);
			}
		}
	}
}

static void
perf_stop(struct mc_perf_event *event)
{
	int counter_id;
	unsigned long counter_mask = 0;
	struct mc_perf_event *leader = event->group_leader, *sub;
	struct thread *thread = cpu_local_var(current);

	struct mc_perf_event *stop_event[PMC_ALLOC_MAP_BITS + 1];
	int stop_event_idx = 0;

	stop_event[0] = NULL;
	counter_id = leader->counter_id;
	if (ihk_mc_perf_counter_mask_check(1UL << counter_id) &&
			leader->state == PERF_EVENT_STATE_ACTIVE) {
		if (leader->use_invariant_tsc) {
			if (leader->stopped_user_tsc == 0) {
				leader->stopped_user_tsc = thread->user_tsc;
			}
			if (leader->stopped_system_tsc == 0) {
				leader->stopped_system_tsc = thread->system_tsc;
			}
		}
		else {
			counter_mask |= 1UL << counter_id;
			stop_event[stop_event_idx++] = leader;
			stop_event[stop_event_idx] = NULL;
		}

		leader->state = PERF_EVENT_STATE_INACTIVE;
	}

	list_for_each_entry(sub, &leader->sibling_list, group_entry) {
		counter_id = sub->counter_id;
		if (ihk_mc_perf_counter_mask_check(1UL << counter_id) &&
				sub->state == PERF_EVENT_STATE_ACTIVE) {
			if (sub->use_invariant_tsc) {
				if (sub->stopped_user_tsc == 0) {
					sub->stopped_user_tsc =
						thread->user_tsc;
				}
				if (sub->stopped_system_tsc == 0) {
					sub->stopped_system_tsc =
						thread->system_tsc;
				}
			}
			else {
				counter_mask |= 1UL << counter_id;
				stop_event[stop_event_idx++] = sub;
				stop_event[stop_event_idx] = NULL;
			}
			sub->state = PERF_EVENT_STATE_INACTIVE;
		}
	}

	if (counter_mask) {
		ihk_mc_perfctr_stop(counter_mask, 0);
		stop_event_idx = 0;
		while (stop_event[stop_event_idx]) {
			ihk_mc_event_update(stop_event[stop_event_idx++]);
		}
	}
	cpu_local_var(current)->proc->monitoring_event = NULL;
	cpu_local_var(current)->proc->perf_status = PP_NONE;
}

static int
perf_ioctl(struct mckfd *sfd, ihk_mc_user_context_t *ctx)
{
	unsigned int cmd = ihk_mc_syscall_arg1(ctx);
	struct mc_perf_event *event = (struct mc_perf_event*)sfd->data;
	struct mcs_rwlock_node_irqsave lock;
	struct process *proc;

	switch (cmd) {
        case PERF_EVENT_IOC_ENABLE:
		if(event->pid == 0){
			cpu_local_var(current)->proc->monitoring_event = event;
			perf_start(event);
		}
		else if(event->pid > 0){
			proc = find_process(event->pid, &lock);
			if(!proc)
				return -EINVAL;
			if(proc->monitoring_event == NULL){
				proc->monitoring_event = event;
				proc->perf_status = PP_RESET;
			}
			process_unlock(proc, &lock);
		}
                break;
        case PERF_EVENT_IOC_DISABLE:
		if(event->pid == 0){
			perf_stop(event);
		}
		// TODO: stop other process
		/*
		else if(event->pid > 0){
			proc = find_process(event->pid, &lock);
			if(!proc)
				return -EINVAL;
			proc->monitoring_event = NULL;
			proc->perf_status = PP_NONE;
			process_unlock(proc, &lock);
		}
		*/
		break;
        case PERF_EVENT_IOC_RESET:
		// TODO: reset other process
		perf_reset(event);
		break;
        case PERF_EVENT_IOC_REFRESH:
		// TODO: refresh other process
		
		// not supported on inherited events
		if(event->attr.inherit)
			return -EINVAL;

		/* REFRESH doesn't need to include ENABLE */
		/* perf_start(event); */

		break;
	default :
		return -1;
	}

	return 0;
}

static int
perf_close(struct mckfd *sfd, ihk_mc_user_context_t *ctx)
{
	struct mc_perf_event *event = (struct mc_perf_event*)sfd->data;
	struct thread *thread = cpu_local_var(current);

	thread->pmc_alloc_map &= ~(1UL << event->counter_id);
	if (event->extra_reg.reg) {
		thread->extra_reg_alloc_map &= ~(1UL << event->extra_reg.idx);
	}
		
	kfree(event);

	return 0;
}

static int
perf_fcntl(struct mckfd *sfd, ihk_mc_user_context_t *ctx)
{
	int cmd = ihk_mc_syscall_arg1(ctx);
	long arg = ihk_mc_syscall_arg2(ctx);
	int rc = 0;

	switch(cmd) {
	case 10: // F_SETSIG
		sfd->sig_no = arg;
		break;
	case 0xf: // F_SETOWN_EX
		break;
	default : 
		break;
	}

	rc = syscall_generic_forwarding(__NR_fcntl, ctx);

	return rc;
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
	struct perf_event_mmap_page *page = NULL;
	long rc;

	flags |= MAP_ANONYMOUS;
	prot |= PROT_WRITE;
	rc = do_mmap(addr0, len0, prot, flags, fd, off0, 0, NULL);

	// setup perf_event_mmap_page
	page = (struct perf_event_mmap_page *)rc;
	page->data_head = 16;
	page->cap_user_rdpmc = 1;

	return rc;
}
#endif /*ENABLE_PERF*/

struct vm_range_numa_policy *vm_range_policy_search(struct process_vm *vm, uintptr_t addr)
{
	struct rb_root *root = &vm->vm_range_numa_policy_tree;
	struct rb_node *node = root->rb_node;
	struct vm_range_numa_policy *numa_policy = NULL;

	while (node) {
		numa_policy = rb_entry(node, struct vm_range_numa_policy, policy_rb_node);
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
		range = rb_entry(*new, struct vm_range_numa_policy,
				policy_rb_node);
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
			kfree(range_policy_iter);
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
				range_policy = kmalloc(
					sizeof(struct vm_range_numa_policy),
					IHK_MC_AP_NOWAIT);
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
		range = rb_entry(node, struct vm_range_numa_policy,
				policy_rb_node);

		/* existing range is fully contained */
		if (range->start >= start && range->end <= end) {
			rb_erase(&range->policy_rb_node,
				&vm->vm_range_numa_policy_tree);
			kfree(range);
			goto again_search;
		}
	}

out:
	return error;
}

#ifdef ENABLE_PERF
static int mc_perf_event_alloc(struct mc_perf_event **out,
			       struct perf_event_attr *attr)
{
	int ret = 0;
	unsigned long val = 0, extra_config = 0;
	struct mc_perf_event *event = NULL;
	int ereg_id;
	struct hw_perf_event *hwc;

	if (!attr) {
		ret = -EINVAL;
		goto out;
	}

	event = kmalloc(sizeof(struct mc_perf_event), IHK_MC_AP_NOWAIT);
	if (!event) {
		ret = -ENOMEM;
		goto out;
	}
	memset(event, 0, sizeof(struct mc_perf_event));

	INIT_LIST_HEAD(&event->group_entry);
	INIT_LIST_HEAD(&event->sibling_list);
	event->attr = *attr;

	event->sample_freq = attr->sample_freq;
	event->nr_siblings = 0;
	ihk_atomic64_set(&event->count, 0);
	event->child_count_total = 0;
	event->parent = NULL;

	hwc = &event->hw;
	hwc->sample_period = attr->sample_period;
	if (attr->freq && attr->sample_freq) {
		/*
		 * Mark struct perf_event_attr::sample_freq is set by user.
		 * Note that it's okay to use
		 * struct hw_perf_event::sample_period for this purpose
		 * because it's not union and not used when
		 * struct perf_event_attr::freq is one.
		 */
		hwc->sample_period = 1;
	}
	hwc->last_period = hwc->sample_period;
	ihk_atomic64_set(&hwc->period_left, hwc->sample_period);

	if (attr->type == PERF_TYPE_HARDWARE &&
		attr->config == PERF_COUNT_HW_REF_CPU_CYCLES) {
		event->use_invariant_tsc = 1;

		/*
		 * REF_CPU_CYCLES is counted by thread's tsc.
		 * Always support.
		 */
		*out = event;
		ret = 0;
		goto out;
	}

	switch (attr->type) {
	case PERF_TYPE_HARDWARE :
		val = ihk_mc_hw_event_map(attr->config);
		break;
	case PERF_TYPE_HW_CACHE :
		val = ihk_mc_hw_cache_event_map(attr->config);
		extra_config = ihk_mc_hw_cache_extra_reg_map(attr->config);
		break;
	case PERF_TYPE_RAW :
		val = ihk_mc_raw_event_map(attr->config);
		break;

	default:
		// Unexpected type
		ret = -EINVAL;
		goto out;
	}

	if (!ihk_mc_validate_event(val)) {
		ret = -ENOENT;
		goto out;
	}
	
	event->hw_config = val;
	event->hw_config_ext = extra_config;

	ereg_id = ihk_mc_get_extra_reg_id(event->hw_config, event->hw_config_ext);
	if (ereg_id >= 0) {
		event->extra_reg.config = event->hw_config_ext;
		event->extra_reg.reg = ihk_mc_get_extra_reg_msr(ereg_id);
		event->extra_reg.idx = ihk_mc_get_extra_reg_idx(ereg_id);
	}

	ret = hw_perf_event_init(event);

	*out = event;

out:
	if (ret) {
		kfree(event);
	}
	return ret;
}

SYSCALL_DECLARE(perf_event_open)
{
	int ret;
	struct syscall_request request IHK_DMA_ALIGN;
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct mckfd *sfd, *cfd;
	int fd;
	int counter_idx;
	long irqstate;
	struct perf_event_attr *arg0 = (void *)ihk_mc_syscall_arg0(ctx);
	int pid = ihk_mc_syscall_arg1(ctx);
	int cpu = ihk_mc_syscall_arg2(ctx);
	int group_fd = ihk_mc_syscall_arg3(ctx);
	unsigned long flags = ihk_mc_syscall_arg4(ctx);
	struct mc_perf_event *event;
	struct perf_event_attr attr_user,*attr;

	int not_supported_flag = 0;

#ifndef ENABLE_PERF
	return -ENOSYS;
#endif // ENABLE_PERF

	if (copy_from_user(&attr_user, arg0, sizeof(struct perf_event_attr))){
		return -EFAULT;
	}
	attr = &attr_user;

	// check Not supported 
	if (cpu > 0) {
		not_supported_flag = 1;	
	}
	if (flags > 0) {
		not_supported_flag = 1;	
	}

	if ((attr->type != PERF_TYPE_RAW) && 
	    (attr->type != PERF_TYPE_HARDWARE) &&
	    (attr->type != PERF_TYPE_HW_CACHE)) {
		not_supported_flag = 1;
	}
	if (attr->read_format & 
	    (PERF_FORMAT_TOTAL_TIME_ENABLED |
	     PERF_FORMAT_TOTAL_TIME_RUNNING |
	     PERF_FORMAT_ID)) {
		not_supported_flag = 1;
	}

	if (attr->freq) {
		not_supported_flag = 1;
	} else {
		if (attr->sample_period & (1ULL << 63)) {
			return -EINVAL;
		}
	}

	if (not_supported_flag) {
		return -ENOENT;
	}

	ret = mc_perf_event_alloc(&event, (struct perf_event_attr *)attr);
	if (ret) {
		return ret;
	}

	event->pid = pid;

	counter_idx = ihk_mc_perfctr_alloc(thread, event);
	if (counter_idx < 0) {
		return counter_idx;
	}
	event->counter_id = counter_idx;

	if (group_fd == -1) {
		event->group_leader = event; 
		event->pmc_status = 0x0UL;
	}
	else {
		for (cfd = proc->mckfd; cfd; cfd = cfd->next) {
			if (cfd->fd == group_fd) {
				event->group_leader = (struct mc_perf_event*)cfd->data;
				list_add_tail(&event->group_entry, &event->group_leader->sibling_list);
				event->group_leader->nr_siblings++;
				break;
			}
		}
	}

	event->group_leader->pmc_status |= (1UL << counter_idx);

	request.number = __NR_perf_event_open;
	request.args[0] = 0;
	fd = do_syscall(&request, ihk_mc_get_processor_id());
	if(fd < 0){
		return fd;
	} 

	thread->pmc_alloc_map |= 1UL << counter_idx;

	sfd = kmalloc(sizeof(struct mckfd), IHK_MC_AP_NOWAIT);
	if(!sfd)
		return -ENOMEM;
	sfd->fd = fd;
	sfd->sig_no = -1;
	sfd->read_cb = perf_read;
	sfd->ioctl_cb = perf_ioctl;
	sfd->close_cb = perf_close;
	sfd->mmap_cb = perf_mmap;
	sfd->fcntl_cb = perf_fcntl;
	sfd->data = (long)event;
	irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);

	if(proc->mckfd == NULL) {
		proc->mckfd = sfd;
		sfd->next = NULL;
	} else {
		sfd->next = proc->mckfd;
		proc->mckfd = sfd;
	}

	ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);
	return sfd->fd;
}
#endif /* ENABLE_PERF */

SYSCALL_DECLARE(rt_sigtimedwait)
{
	const sigset_t *set = (const sigset_t *)ihk_mc_syscall_arg0(ctx);
	siginfo_t *info = (siginfo_t *)ihk_mc_syscall_arg1(ctx);
	void *timeout = (void *)ihk_mc_syscall_arg2(ctx);
	size_t sigsetsize = (size_t)ihk_mc_syscall_arg3(ctx);
	struct thread *thread = cpu_local_var(current);
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
	struct ihk_os_cpu_monitor *monitor = cpu_local_var(monitor);
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
		list_for_each_entry(pending, head, list){
			if(pending->sigmask.__val[0] & wset)
				break;
		}

		if(&pending->list == head){
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

			lock = &thread->sigpendinglock;
			head = &thread->sigpending;
			mcs_rwlock_writer_lock(lock, &mcs_rw_node);
			list_for_each_entry(pending, head, list){
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
		list_for_each_entry(pending, head, list){
			if(pending->sigmask.__val[0] & nset)
				break;
		}

		if(&pending->list == head){
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

			lock = &thread->sigpendinglock;
			head = &thread->sigpending;
			mcs_rwlock_writer_lock(lock, &mcs_rw_node);
			list_for_each_entry(pending, head, list){
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
			kfree(pending);
			return -EFAULT;
		}
	}
	w = pending->sigmask.__val[0];
	sig = sigmask_to_signal_number(w);
	kfree(pending);

	return sig;
}

SYSCALL_DECLARE(rt_sigqueueinfo)
{
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	int sig = (int)ihk_mc_syscall_arg1(ctx);
	void *winfo = (void *)ihk_mc_syscall_arg2(ctx);
	struct siginfo info;
	int error;

	error = rt_sigqueueinfo_pid_result(pid);
	if (error) {
		return error;
	}

	if(copy_from_user(&info, winfo, sizeof info))
		return -EFAULT;

	return do_kill(cpu_local_var(current), pid, -1, sig, &info, 0);
}

static int
do_sigsuspend(struct thread *thread, const sigset_t *set)
{
	__sigset_t wset;
	__sigset_t bset;
	struct sig_pending *pending;
	struct list_head *head;
	mcs_rwlock_lock_t *lock;
	struct mcs_rwlock_node_irqsave mcs_rw_node;
	struct ihk_os_cpu_monitor *monitor = cpu_local_var(monitor);

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
		list_for_each_entry(pending, head, list){
			if(sigsuspend_pending_matches(
					pending->sigmask.__val[0], wset))
				break;
		}

		if(&pending->list == head){
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

			lock = &thread->sigpendinglock;
			head = &thread->sigpending;
			mcs_rwlock_writer_lock(lock, &mcs_rw_node);
			list_for_each_entry(pending, head, list){
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

SYSCALL_DECLARE(pause)
{
	struct thread *thread = cpu_local_var(current);

	return do_sigsuspend(thread, &thread->sigmask);
}

SYSCALL_DECLARE(rt_sigsuspend)
{
	struct thread *thread = cpu_local_var(current);
	const sigset_t *set = (const sigset_t *)ihk_mc_syscall_arg0(ctx);
	size_t sigsetsize = (size_t)ihk_mc_syscall_arg1(ctx);
	sigset_t wset;
	int error;

	error = sigsuspend_sigsetsize_result(sigsetsize, sizeof(sigset_t));
	if (error) {
		return error;
	}
	if(copy_from_user(&wset, set, sizeof wset))
		return -EFAULT;

	return do_sigsuspend(thread, &wset);
}

SYSCALL_DECLARE(rt_sigaction)
{
	int sig = ihk_mc_syscall_arg0(ctx);
	const struct sigaction *act =
		(const struct sigaction *)ihk_mc_syscall_arg1(ctx);
	struct sigaction *oact = (struct sigaction *)ihk_mc_syscall_arg2(ctx);
	size_t sigsetsize = ihk_mc_syscall_arg3(ctx);
	struct k_sigaction new_sa, old_sa;
	int rc;

	rc = sigaction_sigsetsize_result(sigsetsize, sizeof(sigset_t));
	if (rc) {
		return rc;
	}

	if (act) {
		if (copy_from_user(&new_sa.sa, act, sizeof(new_sa.sa))) {
			goto fault;
		}
	}

	rc = do_sigaction(sig, act ? &new_sa : NULL, oact ? &old_sa : NULL);
	if (rc == 0 && oact) {
		if (copy_to_user(oact, &old_sa.sa, sizeof(old_sa.sa))) {
			goto fault;
		}
	}

	return rc;
fault:
	return -EFAULT;
}

SYSCALL_DECLARE(sigaltstack)
{
	struct thread *thread = cpu_local_var(current);
	const stack_t *ss = (const stack_t *)ihk_mc_syscall_arg0(ctx);
	stack_t *oss = (stack_t *)ihk_mc_syscall_arg1(ctx);
	stack_t	wss;
	int error;

	if(oss)
		if(copy_to_user(oss, &thread->sigstack, sizeof wss))
			return -EFAULT;
	if(ss){
		if(copy_from_user(&wss, ss, sizeof wss))
			return -EFAULT;
		error = sigaltstack_validate(wss.ss_flags, wss.ss_size);
		if (error) {
			return error;
		}
		if(sigaltstack_is_disable(wss.ss_flags)){
			thread->sigstack.ss_sp = NULL;
			thread->sigstack.ss_flags = SS_DISABLE;
			thread->sigstack.ss_size = 0;
		}
		else{
			memcpy(&thread->sigstack, &wss, sizeof wss);
		}
	}

	return 0;
}

SYSCALL_DECLARE(mincore)
{
	const uintptr_t start = ihk_mc_syscall_arg0(ctx);
	const size_t len = ihk_mc_syscall_arg1(ctx);
	uint8_t * const vec = (void *)ihk_mc_syscall_arg2(ctx);
	uintptr_t end;
	struct thread *thread = cpu_local_var(current);
	struct process_vm *vm = thread->vm;
	void *up;
	uintptr_t addr;
	struct vm_range *range;
	uint8_t value;
	int error;
	pte_t *ptep;

	error = mincore_prepare_range(start, len, vm->region.user_start,
			vm->region.user_end, &end);
	if (error == -EINVAL) {
		dkprintf("mincore(0x%lx,0x%lx,%p): EINVAL\n", start, len, vec);
		return error;
	}
	if (error == -ENOMEM) {
		dkprintf("mincore(0x%lx,0x%lx,%p): EINVAL\n", start, len, vec);
		return error;
	}

	range = NULL;
	up = vec;
	for (addr = start; addr < end; addr += PAGE_SIZE) {
		ihk_rwspinlock_read_lock_noirq(&vm->memory_range_lock);
		range = lookup_process_memory_range(vm, addr, addr+1);
		if (!range) {
			ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);
			dkprintf("mincore(0x%lx,0x%lx,%p):lookup failed. ENOMEM\n",
					start, len, vec);
			return -ENOMEM;
		}

		ihk_mc_spinlock_lock_noirq(&vm->page_table_lock);
		ptep = ihk_mc_pt_lookup_pte(vm->address_space->page_table,
				(void *)addr, 0, NULL, NULL, NULL);
		if (ptep && pte_is_present(ptep)) {
			value = 1;
		}
		else if (range->memobj) {
			error = memobj_lookup_page(range->memobj,
					range->objoff + (addr - range->start),
					PAGE_P2ALIGN, NULL, NULL);
			value = (!error)? 1: 0;
		}
		else {
			value = 0;
		}
		ihk_mc_spinlock_unlock_noirq(&vm->page_table_lock);
		ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);

		error = copy_to_user(up, &value, sizeof(value));
		if (error) {
			dkprintf("mincore(0x%lx,0x%lx,%p):copy failed. %d\n",
					start, len, vec, error);
			return error;
		}
		++up;
	}

	dkprintf("mincore(0x%lx,0x%lx,%p): 0\n", start, len, vec);
	return 0;
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

SYSCALL_DECLARE(madvise)
{
	const uintptr_t start = (uintptr_t)ihk_mc_syscall_arg0(ctx);
	const size_t len0 = (size_t)ihk_mc_syscall_arg1(ctx);
	const int advice = (int)ihk_mc_syscall_arg2(ctx);
	size_t len;
	uintptr_t end;
	struct thread *thread = cpu_local_var(current);
	struct vm_regions *region = &thread->vm->region;
	struct vm_range *first;
	uintptr_t addr;
	struct vm_range *range;
	int error;
	uintptr_t s;
	uintptr_t e;

	dkprintf("[%d]sys_madvise(%lx,%lx,%x)\n",
			ihk_mc_get_processor_id(), start, len0, advice);
	return 0;

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

LIST_HEAD(kds_list);
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

	list_for_each_entry(obj, &kds_list, chain) {
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

	list_for_each_entry(obj, &kds_list, chain) {
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

	list_for_each_entry(obj, &kds_list, chain) {
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
	struct thread *thread = cpu_local_var(current);
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

SYSCALL_DECLARE(shmat)
{
	const int shmid = ihk_mc_syscall_arg0(ctx);
	void * const shmaddr = (void *)ihk_mc_syscall_arg1(ctx);
	const int shmflg = ihk_mc_syscall_arg2(ctx);
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct process_vm *vm = thread->vm;
	size_t len;
	int error;
	uintptr_t addr;
	int prot;
	int vrflags;
	struct shmobj *obj;
	size_t pgsize;

	dkprintf("shmat(%#x,%p,%#x)\n", shmid, shmaddr, shmflg);

	shmobj_list_lock();
	error = shmobj_list_lookup(shmid, &obj);
	if (error) {
		shmobj_list_unlock();
		dkprintf("shmat(%#x,%p,%#x): lookup: %d\n", shmid, shmaddr, shmflg, error);
		return error;
	}

	pgsize = (size_t)1 << obj->pgshift;
	if (shmaddr && ((uintptr_t)shmaddr & (pgsize - 1)) && !(shmflg & SHM_RND)) {
		shmobj_list_unlock();
		memobj_unref(&obj->memobj);
		dkprintf("shmat(%#x,%p,%#x): -EINVAL\n", shmid, shmaddr, shmflg);
		return -EINVAL;
	}
	addr = (uintptr_t)shmaddr & ~(pgsize - 1);
	len = obj->real_segsz;

	prot = PROT_READ;
	if (!(shmflg & SHM_RDONLY)) {
		prot |= PROT_WRITE;
	}

	error = shmat_access_result(proc->euid, proc->egid, shmflg,
			obj->ds.shm_perm.uid, obj->ds.shm_perm.cuid,
			obj->ds.shm_perm.gid, obj->ds.shm_perm.cgid,
			obj->ds.shm_perm.mode);
	if (error) {
		shmobj_list_unlock();
		memobj_unref(&obj->memobj);
		dkprintf("shmat(%#x,%p,%#x): -EINVAL\n", shmid, shmaddr, shmflg);
		return error;
	}

	ihk_rwspinlock_write_lock_noirq(&vm->memory_range_lock);

	if (addr) {
		if (lookup_process_memory_range(vm, addr, addr+len)) {
			ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("shmat(%#x,%p,%#x):lookup_process_memory_range succeeded. -ENOMEM\n", shmid, shmaddr, shmflg);
			return -ENOMEM;
		}
	}
	else {
		error = search_free_space(len, obj->pgshift, &addr);
		if (error) {
			ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("shmat(%#x,%p,%#x):search_free_space failed. %d\n", shmid, shmaddr, shmflg, error);
			return error;
		}
	}

	vrflags = VR_NONE;
	vrflags |= VR_DEMAND_PAGING;
	vrflags |= PROT_TO_VR_FLAG(prot);
	vrflags |= VRFLAG_PROT_TO_MAXPROT(vrflags);

	if (!(prot & PROT_WRITE)) {
		error = set_host_vma(addr, len, PROT_READ | PROT_EXEC, 1/* holding memory_range_lock */);
		if (error) {
			ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
			shmobj_list_unlock();
			memobj_unref(&obj->memobj);
			dkprintf("shmat(%#x,%p,%#x):set_host_vma failed. %d\n", shmid, shmaddr, shmflg, error);
			return error;
		}
	}

	error = add_process_memory_range(vm, addr, addr+len, -1,
			vrflags, &obj->memobj, 0, obj->pgshift, NULL, NULL);
	if (error) {
		if (!(prot & PROT_WRITE)) {
			(void)set_host_vma(addr, len, PROT_READ | PROT_WRITE | PROT_EXEC, 1/* holding memory_range_lock */);
		}
		memobj_unref(&obj->memobj);
		ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
		shmobj_list_unlock();
		dkprintf("shmat(%#x,%p,%#x):add_process_memory_range failed. %d\n", shmid, shmaddr, shmflg, error);
		return error;
	}

	ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
	shmobj_list_unlock();

	dkprintf("shmat(%#x,%p,%#x): 0x%lx. %d\n", shmid, shmaddr, shmflg, addr);
	return addr;
} /* sys_shmat() */

SYSCALL_DECLARE(shmctl)
{
	const int shmid = ihk_mc_syscall_arg0(ctx);
	const int cmd = ihk_mc_syscall_arg1(ctx);
	struct shmid_ds * const buf = (void *)ihk_mc_syscall_arg2(ctx);
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
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
} /* sys_shmctl() */

SYSCALL_DECLARE(shmdt)
{
	void * const shmaddr = (void *)ihk_mc_syscall_arg0(ctx);
	struct thread *thread = cpu_local_var(current);
	struct process_vm *vm = thread->vm;
	struct vm_range *range;
	int error;

	dkprintf("shmdt(%p)\n", shmaddr);
	ihk_rwspinlock_write_lock_noirq(&vm->memory_range_lock);
	range = lookup_process_memory_range(vm, (uintptr_t)shmaddr, (uintptr_t)shmaddr+1);
	if (!range || (range->start != (uintptr_t)shmaddr) || !range->memobj
			|| !(range->memobj->flags & MF_SHMDT_OK)) {
		ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
		dkprintf("shmdt(%p): -EINVAL\n", shmaddr);
		return -EINVAL;
	}

	error = do_munmap((void *)range->start, (range->end - range->start), 1/* holding memory_range_lock */);
	if (error) {
		ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
		dkprintf("shmdt(%p): %d\n", shmaddr, error);
		return error;
	}

	ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
	dkprintf("shmdt(%p): 0\n", shmaddr);
	return 0;
} /* sys_shmdt() */

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
	uint64_t timeout = 0; // No timeout
	uint32_t val2 = 0;
	// Only one clock is used, ignore FUTEX_CLOCK_REALTIME
	//int futex_clock_realtime = 0; 
	int fshared = 1;
	int ret = 0;

	uint32_t *uaddr = (uint32_t *)arg0;
	int op = (int)arg1;
	uint32_t val = (uint32_t)arg2;
	struct timespec *utime = (struct timespec*)arg3;
	uint32_t *uaddr2 = (uint32_t *)arg4;
	uint32_t val3 = (uint32_t)arg5;
	int flags = op;


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
		struct ihk_os_cpu_monitor *monitor = cpu_local_var(monitor);
		monitor->status = IHK_OS_MONITOR_KERNEL_HEAVY;
	} 

	futex_decode_flags_result(op, &op, &fshared);
	
	dkprintf("futex op=[%x, %s],uaddr=%lx, val=%x, utime=%lx, uaddr2=%lx, val3=%x, []=%x, shared: %d\n",
			flags,
			(op == FUTEX_WAIT) ? "FUTEX_WAIT" :
			(op == FUTEX_WAIT_BITSET) ? "FUTEX_WAIT_BITSET" :
			(op == FUTEX_WAKE) ? "FUTEX_WAKE" :
			(op == FUTEX_WAKE_OP) ? "FUTEX_WAKE_OP" :
			(op == FUTEX_WAKE_BITSET) ? "FUTEX_WAKE_BITSET" :
			(op == FUTEX_CMP_REQUEUE) ? "FUTEX_CMP_REQUEUE" :
			(op == FUTEX_REQUEUE) ? "FUTEX_REQUEUE (NOT IMPL!)" : "unknown",
			(unsigned long)uaddr, val, utime, uaddr2, val3, *uaddr, fshared);

	if (futex_wait_timeout_needed_result(op, utime != NULL)) {
		dkprintf("%s: utime=%ld.%09ld\n",
				__func__, utime->tv_sec, utime->tv_nsec);
	}
	if (futex_wait_timeout_needed_result(op, utime != NULL)) {
		unsigned long nsec_timeout;
		if (!uti_clv) {
			/* Use cycles for non-UTI case */

		/* As per the Linux implementation FUTEX_WAIT specifies the duration of
		 * the timeout, while FUTEX_WAIT_BITSET specifies the absolute timestamp */
		if (futex_timeout_is_absolute_result(op)) {
			struct timespec ats;

			if (!gettime_local_support ||
			    !(flags & FUTEX_CLOCK_REALTIME)) {
				struct syscall_request request IHK_DMA_ALIGN; 
				struct timespec tv[2];
				struct timespec *tv_now = tv;

				if ((((unsigned long)tv) ^
				    ((unsigned long)(tv + 1))) & PAGE_MASK)
					tv_now = tv + 1;

				request.number = n;
				request.args[0] = virt_to_phys(tv_now);
				request.args[1] = futex_clock_id_result(flags);

				int r = do_syscall(&request,
						   ihk_mc_get_processor_id());

				if (r < 0) {
					return -EFAULT;
				}

				ats.tv_sec = tv_now->tv_sec;
				ats.tv_nsec = tv_now->tv_nsec;
			}
			/* Compute timeout based on TSC/nanosec ratio */
			else {
				calculate_time_from_tsc(&ats);
			}

			nsec_timeout = futex_timeout_ns_result(op,
					utime->tv_sec, utime->tv_nsec,
					ats.tv_sec, ats.tv_nsec);
		}
		else {
			nsec_timeout = futex_timeout_ns_result(op,
					utime->tv_sec, utime->tv_nsec, 0, 0);
		}
		timeout = nsec_timeout * 1000 / ihk_mc_get_ns_per_tsc();

		}
		else{
			if (futex_timeout_is_absolute_result(op)) { /* User passed absolute time */
				struct timespec ats;
				ret = (*linux_clock_gettime)(futex_clock_id_result(flags), &ats);
				if (ret) {
					return ret;
				}
				dkprintf("%s: ats=%ld.%09ld\n",
						__func__, ats.tv_sec, ats.tv_nsec);
				/* Use nsec for UTI case */
				timeout = futex_timeout_ns_result(op,
						utime->tv_sec, utime->tv_nsec,
						ats.tv_sec, ats.tv_nsec);
			} else { /* User passed relative time */
				/* Use nsec for UTI case */
				timeout = futex_timeout_ns_result(op,
						utime->tv_sec, utime->tv_nsec, 0, 0);
			}
		}
	}

	/* Requeue parameter in 'utime' if op == FUTEX_CMP_REQUEUE.
	 * number of waiters to wake in 'utime' if op == FUTEX_WAKE_OP. */
	val2 = futex_requeue_val2_result(op, arg3);

	ret = futex(uaddr, op, val, timeout, uaddr2, val2, val3, fshared);

	dkprintf("futex op=[%x, %s],uaddr=%lx, val=%x, utime=%lx, uaddr2=%lx, val3=%x, []=%x, shared: %d, ret: %d\n",
			op,
			(op == FUTEX_WAIT) ? "FUTEX_WAIT" :
			(op == FUTEX_WAIT_BITSET) ? "FUTEX_WAIT_BITSET" :
			(op == FUTEX_WAKE) ? "FUTEX_WAKE" :
			(op == FUTEX_WAKE_OP) ? "FUTEX_WAKE_OP" :
			(op == FUTEX_WAKE_BITSET) ? "FUTEX_WAKE_BITSET" :
			(op == FUTEX_CMP_REQUEUE) ? "FUTEX_CMP_REQUEUE" :
			(op == FUTEX_REQUEUE) ? "FUTEX_REQUEUE (NOT IMPL!)" : "unknown",
			(unsigned long)uaddr, val, utime, uaddr2, val3, *uaddr, fshared, ret);

	return ret;
}

SYSCALL_DECLARE(futex)
{
	return do_futex(n, ihk_mc_syscall_arg0(ctx), ihk_mc_syscall_arg1(ctx),
					ihk_mc_syscall_arg2(ctx), ihk_mc_syscall_arg3(ctx),
					ihk_mc_syscall_arg4(ctx), ihk_mc_syscall_arg5(ctx),
					0UL, NULL, NULL, NULL, NULL);
}

static void
do_exit(int code)
{
	struct thread *thread = cpu_local_var(current);
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
	list_for_each_entry(child, &proc->threads_list, siblings_list) {
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

	if(proc->status == PS_EXITED){
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

SYSCALL_DECLARE(exit)
{
	int code = exit_syscall_code_result((int)ihk_mc_syscall_arg0(ctx));

	do_exit(code);
	return 0;
}

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
	struct resource_set *rset = cpu_local_var(resource_set);
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
			ihk_mc_syscall_arg0(&ctx) = pid;
			ihk_mc_syscall_arg1(&ctx) = resource;
			ihk_mc_syscall_arg2(&ctx) =
				(unsigned long)_new_limit;
			ihk_mc_syscall_arg3(&ctx) =
				(unsigned long)old_limit;
			ret = syscall_generic_forwarding(__NR_prlimit64, &ctx);
			if (ret < 0)
				return ret;
		}
	}

	/* translate resource */
	mcresource = prlimit_to_mckernel_resource(resource);
	if (mcresource < 0) {
		ihk_mc_syscall_arg0(&ctx) = pid;
		ihk_mc_syscall_arg1(&ctx) = resource;
		ihk_mc_syscall_arg2(&ctx) =
			(unsigned long)_new_limit;
		ihk_mc_syscall_arg3(&ctx) =
			(unsigned long)old_limit;
		return syscall_generic_forwarding(__NR_prlimit64, &ctx);
	}

	/* find process */
	found = 0;

	if (pid == 0) {
		struct thread *thread = cpu_local_var(current);

		pid = thread->proc->pid;
	}

	irqstate = cpu_disable_interrupt_save();
	hash = process_hash(pid);
	mcs_rwlock_reader_lock_noirq(&phash->lock[hash], &exist_lock);

	list_for_each_entry(proc, &phash->list[hash], hash_list) {
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

SYSCALL_DECLARE(setrlimit)
{
	int resource = ihk_mc_syscall_arg0(ctx);
	struct rlimit *new_limit = (struct rlimit *)ihk_mc_syscall_arg1(ctx);

	return do_prlimit64(0, resource, new_limit, NULL);
}

SYSCALL_DECLARE(getrlimit)
{
	int resource = ihk_mc_syscall_arg0(ctx);
	struct rlimit *old_limit = (struct rlimit *)ihk_mc_syscall_arg1(ctx);

	return do_prlimit64(0, resource, NULL, old_limit);
}

SYSCALL_DECLARE(prlimit64)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	int resource = ihk_mc_syscall_arg1(ctx);
	struct rlimit *new_limit = (struct rlimit *)ihk_mc_syscall_arg2(ctx);
	struct rlimit *old_limit = (struct rlimit *)ihk_mc_syscall_arg3(ctx);

	return do_prlimit64(pid, resource, new_limit, old_limit);
}

SYSCALL_DECLARE(getrusage)
{
	int who = ihk_mc_syscall_arg0(ctx);
	struct rusage *usage = (struct rusage *)ihk_mc_syscall_arg1(ctx);
	struct rusage kusage;
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	struct timespec utime;
	struct timespec stime;
	struct mcs_rwlock_node lock;
	struct timespec ats;
	int error;
	int dispatch;

	error = getrusage_who_result(who);
	if (error) {
		return error;
	}
	dispatch = getrusage_dispatch_result(who);

	memset(&kusage, '\0', sizeof kusage);

	if(dispatch == GETRUSAGE_DISPATCH_SELF){
		struct thread *child;

		memset(&utime, '\0', sizeof utime);
		memset(&stime, '\0', sizeof stime);
		mcs_rwlock_reader_lock_noirq(&proc->threads_lock, &lock);
		list_for_each_entry(child, &proc->threads_list, siblings_list){
			int update_action =
				getrusage_thread_update_action_result(
					child == thread, child->status,
					child->in_kernel);

			if(update_action == GETRUSAGE_THREAD_UPDATE_INTERRUPT){
				child->times_update = 0;
				ihk_mc_interrupt_cpu(child->cpu_id,
						ihk_mc_get_vector(IHK_GV_IKC));
			}
			else
				child->times_update = 1;
		}
		utime.tv_sec = proc->utime.tv_sec;
		utime.tv_nsec = proc->utime.tv_nsec;
		stime.tv_sec = proc->stime.tv_sec;
		stime.tv_nsec = proc->stime.tv_nsec;
		list_for_each_entry(child, &proc->threads_list, siblings_list){
			while(!child->times_update)
				cpu_pause();
			tsc_to_ts(child->user_tsc, &ats);
			ts_add(&utime, &ats);
			tsc_to_ts(child->system_tsc, &ats);
			ts_add(&stime, &ats);
		}
		mcs_rwlock_reader_unlock_noirq(&proc->threads_lock, &lock);
		ts_to_tv(&kusage.ru_utime, &utime);
		ts_to_tv(&kusage.ru_stime, &stime);

		kusage.ru_maxrss = getrusage_maxrss_kb_result(proc->maxrss);
	}
	else if(dispatch == GETRUSAGE_DISPATCH_CHILDREN){
		ts_to_tv(&kusage.ru_utime, &proc->utime_children);
		ts_to_tv(&kusage.ru_stime, &proc->stime_children);

		kusage.ru_maxrss =
			getrusage_maxrss_kb_result(proc->maxrss_children);
	}
	else if(dispatch == GETRUSAGE_DISPATCH_THREAD){
		tsc_to_ts(thread->user_tsc, &ats);
		ts_to_tv(&kusage.ru_utime, &ats);
		tsc_to_ts(thread->system_tsc, &ats);
		ts_to_tv(&kusage.ru_stime, &ats);

		kusage.ru_maxrss = getrusage_maxrss_kb_result(proc->maxrss);
	}

	if(copy_to_user(usage, &kusage, sizeof kusage))
		return -EFAULT;

	return 0;
}

SYSCALL_DECLARE(sysinfo)
{
	struct sysinfo *sysinfo = (struct sysinfo *)ihk_mc_syscall_arg0(ctx);
	struct sysinfo __sysinfo;
	int ret = 0;

	memset(&__sysinfo, '\0', sizeof(struct sysinfo));

	__sysinfo.totalram = rusage_get_total_memory();
	__sysinfo.freeram = rusage_get_free_memory();
	__sysinfo.mem_unit = 1; // always one unit for McKernel

	if (copy_to_user(sysinfo, &__sysinfo, sizeof(struct sysinfo))) {
		ret = -EFAULT;
		goto out;
	}

out:
	return ret;
}

extern int ptrace_traceme(void);
extern void set_single_step(struct thread *thread);

static int ptrace_wakeup_sig(int pid, long request, long data) {
	dkprintf("ptrace_wakeup_sig,pid=%d,data=%08x\n", pid, data);
	int error = 0;
	struct thread *child;
	struct siginfo info;
	struct mcs_rwlock_node_irqsave lock;
	struct thread *thread = cpu_local_var(current);
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
				kfree(pending);
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
}

extern long ptrace_read_user(struct thread *thread, long addr, unsigned long *value);
extern long ptrace_write_user(struct thread *thread, long addr, unsigned long value);

static long ptrace_pokeuser(int pid, long addr, long data)
{
	long rc = -EIO;
	struct thread *child;

	rc = ptrace_user_area_result(addr, sizeof(struct user));
	if (rc) {
		return rc;
	}
	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	if(ptrace_status_allows_io(child->status)){
		rc = ptrace_write_user(child, addr, (unsigned long)data);
	}
	thread_unlock(child);

	return rc;
}

static long ptrace_peekuser(int pid, long addr, long data)
{
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
	if(ptrace_status_allows_io(child->status)){
		unsigned long value;
		rc = ptrace_read_user(child, addr, &value);
		if (rc == 0) {
			rc = copy_to_user(p, (char *)&value, sizeof(value));
		}
	}
	thread_unlock(child);

	return rc;
}

static long ptrace_getregs(int pid, long data)
{
	struct user_regs_struct *regs = (struct user_regs_struct *)data;
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	if(ptrace_status_allows_io(child->status)){
		struct user_regs_struct user_regs;
		long addr;
		unsigned long *p;
		memset(&user_regs, '\0', sizeof(struct user_regs_struct));
		for (addr = 0, p = (unsigned long *)&user_regs;
				addr < sizeof(struct user_regs_struct);
				addr += sizeof(*p), p++) {
			rc = ptrace_read_user(child, addr, p);
			if (rc) break;
		}
		if (rc == 0) {
			rc = copy_to_user(regs, &user_regs, sizeof(struct user_regs_struct));
		}
	}
	thread_unlock(child);

	return rc;
}

static long ptrace_setregs(int pid, long data)
{
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
			long addr;
			unsigned long *p;
			for (addr = 0, p = (unsigned long *)&user_regs;
					addr < sizeof(struct user_regs_struct);
					addr += sizeof(*p), p++) {
				rc = ptrace_write_user(child, addr, *p);
				if (rc) {
					break;
				}
			}
		}
	}
	thread_unlock(child);

	return rc;
}

extern long ptrace_read_fpregs(struct thread *thread, void *fpregs);
extern long ptrace_write_fpregs(struct thread *thread, void *fpregs);

static long ptrace_getfpregs(int pid, long data)
{
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	if(ptrace_status_allows_io(child->status)){
		rc = ptrace_read_fpregs(child, (void *)data);
	}
	thread_unlock(child);

	return rc;
}

static long ptrace_setfpregs(int pid, long data)
{
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	if(ptrace_status_allows_io(child->status)){
		rc = ptrace_write_fpregs(child, (void *)data);
	}
	thread_unlock(child);

	return rc;
}

extern long ptrace_read_regset(struct thread *thread, long type, struct iovec *iov);
extern long ptrace_write_regset(struct thread *thread, long type, struct iovec *iov);

static long ptrace_getregset(int pid, long type, long data)
{
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	if(ptrace_status_allows_io(child->status)){
		struct iovec iov;

		rc = copy_from_user(&iov, (struct iovec *)data, sizeof(iov));
		if (rc == 0) {
			rc = ptrace_read_regset(child, type, &iov);
		}
		if (rc == 0) {
			rc = copy_to_user(&((struct iovec *)data)->iov_len,
					&iov.iov_len, sizeof(iov.iov_len));
		}
	}
	thread_unlock(child);

	return rc;
}

static long ptrace_setregset(int pid, long type, long data)
{
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	if(ptrace_status_allows_io(child->status)){
		struct iovec iov;

		rc = copy_from_user(&iov, (struct iovec *)data, sizeof(iov));
		if (rc == 0) {
			rc = ptrace_write_regset(child, type, &iov);
		}
		if (rc == 0) {
			rc = copy_to_user(&((struct iovec *)data)->iov_len,
					&iov.iov_len, sizeof(iov.iov_len));
		}
	}
	thread_unlock(child);

	return rc;
}

static long ptrace_peektext(int pid, long addr, long data)
{
	long rc = -EIO;
	struct thread *child;
	unsigned long *p = (unsigned long *)data;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	if(ptrace_status_allows_io(child->status)){
		unsigned long value;
		rc = read_process_vm(child->vm, &value, (void *)addr, sizeof(value));
		if (rc != 0) { 
			dkprintf("ptrace_peektext: bad area  addr=0x%llx\n", addr);
		} else {
			rc = copy_to_user(p, &value, sizeof(value));
		}
	}
	thread_unlock(child);

	return rc;
}

static long ptrace_poketext(int pid, long addr, long data)
{
	long rc = -EIO;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child)
		return -ESRCH;
	if(ptrace_status_allows_io(child->status)){
		rc = patch_process_vm(child->vm, (void *)addr, &data, sizeof(data));
		if (rc) {
			dkprintf("ptrace_poketext: bad address 0x%llx\n", addr);
		}
	}
	thread_unlock(child);

	return rc;
}

static int ptrace_setoptions(int pid, int flags)
{
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
	
	child->ptrace = ptrace_apply_options(child->ptrace, flags);
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
}

static int ptrace_attach(int pid)
{
	int error = 0;
	struct thread *thread;
	struct thread *mythread = cpu_local_var(current);
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

	thread->ptrace = PT_TRACED | PT_TRACE_EXEC;
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
}


int ptrace_detach(int pid, int data)
{
	int error = 0;
	struct thread *thread;
	struct thread *mythread = cpu_local_var(current);
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
}

static long ptrace_geteventmsg(int pid, long data)
{
	unsigned long *msg_p = (unsigned long *)data;
	long rc = -ESRCH;
	struct thread *child;

	child = find_thread(0, pid);
	if (!child) {
		return -ESRCH;
	}
	rc = ptrace_eventmsg_state_result(child->status);
	if (!rc) {
		if (copy_to_user(msg_p, &child->ptrace_eventmsg,
				 sizeof(*msg_p))) {
			rc = -EFAULT;
		}
		else {
			rc = 0;
		}
	}
	thread_unlock(child);

	return rc;
}

static long
ptrace_getsiginfo(int pid, siginfo_t *data)
{
	struct thread *child;
	int rc = 0;

	child = find_thread(0, pid);
	if (!child) {
		return -ESRCH;
	}

	rc = ptrace_siginfo_state_result(child->status,
			child->ptrace_recvsig != NULL);
	if (!rc && child->ptrace_recvsig) {
		if (copy_to_user(data, &child->ptrace_recvsig->info, sizeof(siginfo_t))) {
			rc = -EFAULT;
		}
	}
	thread_unlock(child);
	return rc;
}

static long
ptrace_setsiginfo(int pid, siginfo_t *data)
{
	struct thread *child;
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
			child->ptrace_sendsig = kmalloc(sizeof(struct sig_pending), IHK_MC_AP_NOWAIT);
			if (child->ptrace_sendsig == NULL) {
				rc = -ENOMEM;
			}
		}

		if (!rc && (target & PTRACE_SIGINFO_STORE_SENDSIG) &&
		    copy_from_user(&child->ptrace_sendsig->info, data, sizeof(siginfo_t))) {
			rc = -EFAULT;
		}
		if (!rc && (target & PTRACE_SIGINFO_STORE_RECVSIG)) {
			    if(copy_from_user(&child->ptrace_recvsig->info, data, sizeof(siginfo_t))) {
				rc = -EFAULT;
			}
		}
	}
	thread_unlock(child);
	return rc;
}

SYSCALL_DECLARE(ptrace)
{
	const long request = (long)ihk_mc_syscall_arg0(ctx);
	const int pid = (int)ihk_mc_syscall_arg1(ctx);
	const long addr = (long)ihk_mc_syscall_arg2(ctx);
	const long data = (long)ihk_mc_syscall_arg3(ctx);
	long error = -EOPNOTSUPP;
	int dispatch = ptrace_request_dispatch_result(request);

	switch (dispatch) {
	case PTRACE_DISPATCH_TRACEME:
		dkprintf("ptrace: PTRACE_TRACEME\n");
		error = ptrace_traceme();
		break;
	case PTRACE_DISPATCH_WAKEUP:
		if (request == PTRACE_KILL) {
			dkprintf("ptrace: PTRACE_KILL\n");
		}
		else if (request == PTRACE_CONT) {
			dkprintf("ptrace: PTRACE_CONT: data=%d\n", data);
		}
		else if (request == PTRACE_SINGLESTEP) {
			dkprintf("ptrace: PTRACE_SINGLESTEP: data=%d\n", data);
		}
		else {
			dkprintf("ptrace: PTRACE_SYSCALL: data=%d\n", data);
		}
		error = ptrace_wakeup_sig(pid, request, data);
		break;
	case PTRACE_DISPATCH_GETREGS:
		error = ptrace_getregs(pid, data);
		dkprintf("PTRACE_GETREGS: data=%p return=%p\n", data, error);
		break;
	case PTRACE_DISPATCH_PEEKUSER:
		error = ptrace_peekuser(pid, addr, data);
		dkprintf("PTRACE_PEEKUSER: addr=%p return=%p\n", addr, error);
		break;
	case PTRACE_DISPATCH_POKEUSER:
		error = ptrace_pokeuser(pid, addr, data);
		dkprintf("PTRACE_POKEUSER: addr=%p data=%p return=%p\n", addr, data, error);
		break;
	case PTRACE_DISPATCH_SETOPTIONS:
		error = ptrace_setoptions(pid, data);
		dkprintf("PTRACE_SETOPTIONS: flags=%d return=%p\n", data, error);
		break;
	case PTRACE_DISPATCH_PEEKTEXT:
		error = ptrace_peektext(pid, addr, data);
		if (request == PTRACE_PEEKTEXT) {
			dkprintf("PTRACE_PEEKTEXT: addr=%p return=%p\n", addr, error);
		}
		else {
			dkprintf("PTRACE_PEEKDATA: addr=%p return=%p\n", addr, error);
		}
		break;
	case PTRACE_DISPATCH_POKETEXT:
		error = ptrace_poketext(pid, addr, data);
		if (request == PTRACE_POKETEXT) {
			dkprintf("PTRACE_POKETEXT: addr=%p data=%p\n", addr, data);
		}
		else {
			dkprintf("PTRACE_POKEDATA: addr=%p data=%p\n", addr, data);
		}
		break;
	case PTRACE_DISPATCH_GETFPREGS:
		dkprintf("ptrace: PTRACE_GETFPREGS: data=%p\n", data);
		error = ptrace_getfpregs(pid, data);
		break;
	case PTRACE_DISPATCH_SETFPREGS:
		dkprintf("ptrace: PTRACE_SETFPREGS: data=%p\n", data);
		error = ptrace_setfpregs(pid, data);
		break;
	case PTRACE_DISPATCH_SETREGS:
		error = ptrace_setregs(pid, data);
		dkprintf("PTRACE_SETREGS: data=%p return=%p\n", data, error);
		break;
	case PTRACE_DISPATCH_ATTACH:
		dkprintf("ptrace: PTRACE_ATTACH: pid=%d\n", pid);
		error = ptrace_attach(pid);
		break;
	case PTRACE_DISPATCH_DETACH:
		dkprintf("ptrace: PTRACE_DETACH: data=%d\n", data);
		error = ptrace_detach(pid, data);
		break;
	case PTRACE_DISPATCH_GETSIGINFO:
		dkprintf("ptrace: PTRACE_GETSIGINFO: data=%p\n", data);
		error = ptrace_getsiginfo(pid, (siginfo_t *)data);
		break;
	case PTRACE_DISPATCH_SETSIGINFO:
		dkprintf("ptrace: PTRACE_SETSIGINFO: data=%p\n", data);
		error = ptrace_setsiginfo(pid, (siginfo_t *)data);
		break;
	case PTRACE_DISPATCH_GETREGSET:
		dkprintf("ptrace: PTRACE_GETREGSET: addr=0x%x, data=%p\n", addr, data);
		error = ptrace_getregset(pid, addr, data);
		break;
	case PTRACE_DISPATCH_SETREGSET:
		dkprintf("ptrace: PTRACE_SETREGSET: addr=0x%x, data=%p\n", addr, data);
		error = ptrace_setregset(pid, addr, data);
		break;
	case PTRACE_DISPATCH_GETEVENTMSG:
		dkprintf("ptrace: PTRACE_GETEVENTMSG: data=%p\n", data);
		error = ptrace_geteventmsg(pid, data);
		break;
	default:
		error = arch_ptrace(request, pid, addr, data);
		break;
	}

	dkprintf("ptrace(%d,%ld,%p,%p): returning %d\n", request, pid, addr, data, error);
	return error;
}

#if defined(MCKERNEL_RUST_SCHED_POLICY_HELPERS) || \
	defined(MCKERNEL_SCHED_POLICY_HELPERS_TEST_EXPORT)
#define SCHED_POLICY_HELPER_SCOPE
#else
#define SCHED_POLICY_HELPER_SCOPE static
#endif

#ifdef MCKERNEL_RUST_SCHED_POLICY_HELPERS
extern int sched_policy_is_valid(int policy);
extern int sched_policy_needs_root(int policy);
extern int setscheduler_validate(int policy, int priority);
extern long sched_rr_interval_nsec(int policy);
extern int sched_affinity_permission_result(uid_t caller_euid,
		uid_t target_ruid, uid_t target_euid);
extern int sched_getaffinity_len_result(size_t len, int nr_cpus);
extern size_t sched_affinity_copy_len(size_t len, size_t cpuset_size);
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

#define SCHED_CHECK_SAME_OWNER        0x01
#define SCHED_CHECK_ROOT              0x02

SYSCALL_DECLARE(sched_setparam)
{
	int retval = 0;
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	struct sched_param *uparam = (struct sched_param *)ihk_mc_syscall_arg1(ctx);
	struct sched_param param;
	struct thread *thread = cpu_local_var(current);
	struct syscall_request request1 IHK_DMA_ALIGN;
	int other_thread = 0;

	dkprintf("sched_setparam: pid: %d, uparam: 0x%lx\n", pid, uparam);

	if (!uparam || pid < 0) {
		return -EINVAL;
	}

	if (pid == 0)
		pid = thread->proc->pid;

	if (thread->proc->pid != pid) {
		other_thread = 1;
		thread = find_thread(0, pid);
		if (!thread) {
			return -ESRCH;
		}
		thread_unlock(thread);
		
		/* Ask Linux about ownership.. */
		request1.number = __NR_sched_setparam;
		request1.args[0] = SCHED_CHECK_SAME_OWNER;
		request1.args[1] = pid;

		retval = do_syscall(&request1, ihk_mc_get_processor_id());
		if (retval != 0) {
			return retval;
		}
	}

	retval = copy_from_user(&param, uparam, sizeof(param));
	if (retval < 0) {
		return -EFAULT;
	}

	if (other_thread) {
		thread = find_thread(0, pid);
		if (!thread) {
			return -ESRCH;
		}
	}
	retval = setscheduler(thread, thread->sched_policy, &param);
	if (other_thread) {
		thread_unlock(thread);
	}
	return retval;
}

SYSCALL_DECLARE(sched_getparam)
{
	int retval = 0;
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	struct sched_param *param = (struct sched_param *)ihk_mc_syscall_arg1(ctx);
	struct thread *thread = cpu_local_var(current);

	if (!param || pid < 0) {
		return -EINVAL;
	}

	if (pid == 0)
		pid = thread->proc->pid;

	if (thread->proc->pid != pid) {
		thread = find_thread(0, pid);
		if (!thread) {
			return -ESRCH;
		}
		thread_unlock(thread);
	}
	
	retval = copy_to_user(param, &thread->sched_param, sizeof(*param)) ? -EFAULT : 0;
	
	return retval;
}

SYSCALL_DECLARE(sched_setscheduler)
{
	int retval;
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	int policy = ihk_mc_syscall_arg1(ctx);
	struct sched_param *uparam = (struct sched_param *)ihk_mc_syscall_arg2(ctx);
	struct sched_param param;
	struct thread *thread = cpu_local_var(current);
	
	struct syscall_request request1 IHK_DMA_ALIGN;
	
	if (!uparam || pid < 0) {
		return -EINVAL;
	}
	
	if (!sched_policy_is_valid(policy)) {
		return -EINVAL;
	}

	if (sched_policy_needs_root(policy)) {
		
		/* Ask Linux about permissions */
		request1.number = __NR_sched_setparam;
		request1.args[0] = SCHED_CHECK_ROOT;

		retval = do_syscall(&request1, ihk_mc_get_processor_id());
		if (retval != 0) {
			return retval;
		}
	}
	
	retval = copy_from_user(&param, uparam, sizeof(param));
	if (retval < 0) {
		return -EFAULT;
	}

	if (pid == 0)
		pid = thread->proc->pid;

	if (thread->proc->pid != pid) {
		thread = find_thread(0, pid);
		if (!thread) {
			return -ESRCH;
		}
		thread_unlock(thread);
		
		/* Ask Linux about ownership.. */
		request1.number = __NR_sched_setparam;
		request1.args[0] = SCHED_CHECK_SAME_OWNER;
		request1.args[1] = pid;

		retval = do_syscall(&request1, ihk_mc_get_processor_id());
		if (retval != 0) {
			return retval;
		}
	}

	return setscheduler(thread, policy, &param);
}

SYSCALL_DECLARE(sched_getscheduler)
{
	int pid = (int)ihk_mc_syscall_arg0(ctx);
	struct thread *thread = cpu_local_var(current);

	if (pid < 0) {
		return -EINVAL;
	}

	if (pid == 0)
		pid = thread->proc->pid;

	if (thread->proc->pid != pid) {
		thread = find_thread(0, pid);
		if (!thread) {
			return -ESRCH;
		}
		thread_unlock(thread);
	}

	return thread->sched_policy;
}

#if defined(MCKERNEL_RUST_SCHED_PRIO_HELPERS) || \
	defined(MCKERNEL_SCHED_PRIO_HELPERS_TEST_EXPORT)
#define SCHED_PRIO_HELPER_SCOPE
#else
#define SCHED_PRIO_HELPER_SCOPE static
#endif

#ifdef MCKERNEL_RUST_SCHED_PRIO_HELPERS
extern int sched_get_priority_max_value(int policy);
#else
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

#undef SCHED_PRIO_HELPER_SCOPE

SYSCALL_DECLARE(sched_get_priority_max)
{
	int policy = ihk_mc_syscall_arg0(ctx);

	return sched_get_priority_max_value(policy);
}

SYSCALL_DECLARE(sched_get_priority_min)
{
	int policy = ihk_mc_syscall_arg0(ctx);

	return sched_get_priority_min_value(policy);
}

SYSCALL_DECLARE(sched_rr_get_interval)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	struct timespec *utime = (struct timespec *)ihk_mc_syscall_arg1(ctx);
	struct timespec t;
	struct thread *thread = cpu_local_var(current);
	int retval = 0;

	if (pid < 0) 
		return -EINVAL;

	if (pid == 0)
		pid = thread->proc->pid;

	if (thread->proc->pid != pid) {
		thread = find_thread(0, pid);
		if (!thread) {
			return -ESRCH;
		}
		thread_unlock(thread);
	}
	
	t.tv_sec = 0;
	t.tv_nsec = sched_rr_interval_nsec(thread->sched_policy);
	
	retval = copy_to_user(utime, &t, sizeof(t)) ? -EFAULT : 0;
	
	return retval;
}

#define MIN2(x,y) (x) < (y) ? (x) : (y)
SYSCALL_DECLARE(sched_setaffinity)
{
	int tid = (int)ihk_mc_syscall_arg0(ctx);
	size_t len = (size_t)ihk_mc_syscall_arg1(ctx);
	cpu_set_t *u_cpu_set = (cpu_set_t *)ihk_mc_syscall_arg2(ctx);
	cpu_set_t k_cpu_set, cpu_set;
	struct thread *thread;
	int cpu_id;
	int empty_set = 1; 

	if (!u_cpu_set) {
		return -EFAULT;
	}

	if (sizeof(k_cpu_set) > len) {
		memset(&k_cpu_set, 0, sizeof(k_cpu_set));
	}

	len = sched_affinity_copy_len(len, sizeof(k_cpu_set));

	if (copy_from_user(&k_cpu_set, u_cpu_set, len)) {
		dkprintf("%s: error: copy_from_user failed for %p:%d\n",
				__FUNCTION__, u_cpu_set, len);
		return -EFAULT;
	}
	
	/* Find thread */
	if (tid == 0) {
		tid = cpu_local_var(current)->tid;
		thread = cpu_local_var(current);
		cpu_id = ihk_mc_get_processor_id();
		hold_thread(thread);
	}
	else {
		struct thread *mythread = cpu_local_var(current);

		thread = find_thread(0, tid);

		if (!thread)
			return -ESRCH;

		if (sched_affinity_permission_result(mythread->proc->euid,
				thread->proc->ruid, thread->proc->euid)) {
			thread_unlock(thread);
			return -EPERM;
		}

		hold_thread(thread);
		thread_unlock(thread);
		cpu_id = thread->cpu_id;
	}

	/* Only allow cores that are also in process' cpu_set */
	CPU_ZERO(&cpu_set);
	for (cpu_id = 0; cpu_id < num_processors; cpu_id++) {
		if (CPU_ISSET(cpu_id, &k_cpu_set) &&
			CPU_ISSET(cpu_id, &thread->proc->cpu_set)) {
			CPU_SET(cpu_id, &cpu_set);
			dkprintf("sched_setaffinity(): tid %d: setting target core %d\n",
					cpu_local_var(current)->tid, cpu_id);
			empty_set = 0;
		}
	}

	/* Empty target set? */
	if (empty_set) {
		release_thread(thread);
		return -EINVAL;
	}

	/* Update new affinity mask */
	memcpy(&thread->cpu_set, &cpu_set, sizeof(cpu_set));

	/* Current core not part of new mask? */
	cpu_id = thread->cpu_id;
	if (!CPU_ISSET(cpu_id, &thread->cpu_set)) {
		dkprintf("sched_setaffinity(): tid %d sched_request_migrate: %d\n",
				cpu_local_var(current)->tid, cpu_id);
		sched_request_migrate(cpu_id, thread);
	} 
	release_thread(thread);
	return 0;
}

// see linux-2.6.34.13/kernel/sched.c
SYSCALL_DECLARE(sched_getaffinity)
{
	int tid = (int)ihk_mc_syscall_arg0(ctx);
	size_t len = (size_t)ihk_mc_syscall_arg1(ctx);
	cpu_set_t k_cpu_set, *u_cpu_set = (cpu_set_t *)ihk_mc_syscall_arg2(ctx);
	struct thread *thread;
	int ret;

	dkprintf("%s() len: %d, mask: %p\n", __FUNCTION__, len, u_cpu_set);
	ret = sched_getaffinity_len_result(len, num_processors);
	if (ret) {
		dkprintf("%s: Too small buffer.\n", __func__);
		return ret;
	}

	len = sched_affinity_copy_len(len, sizeof(k_cpu_set));

	if(tid == 0){
		thread = cpu_local_var(current);
		hold_thread(thread);
	}
	else{
		struct thread *mythread = cpu_local_var(current);

		thread = find_thread(0, tid);
		if(!thread)
			return -ESRCH;
		if(sched_affinity_permission_result(mythread->proc->euid,
		   thread->proc->ruid, thread->proc->euid)){
			thread_unlock(thread);
			return -EPERM;
		}
		hold_thread(thread);
		thread_unlock(thread);
	}

	ret = copy_to_user(u_cpu_set, &thread->cpu_set, len);
	release_thread(thread);
	if (ret < 0) {
		ret = -EFAULT;
	}
	else {
		ret = len;
	}

	dkprintf("%s() len: %d, ret: %d\n", __FUNCTION__, len, ret);

	return ret;
}

SYSCALL_DECLARE(get_cpu_id)
{
	return ihk_mc_get_processor_id();
}

SYSCALL_DECLARE(setitimer)
{
	int which = (int)ihk_mc_syscall_arg0(ctx);
	struct itimerval *new = (struct itimerval *)ihk_mc_syscall_arg1(ctx);
	struct itimerval *old = (struct itimerval *)ihk_mc_syscall_arg2(ctx);
	struct syscall_request request IHK_DMA_ALIGN;
	struct thread *thread = cpu_local_var(current);
	int timer_start = 1;
	struct itimerval wkval;
	struct timeval tv;
	int error;

	error = itimer_which_result(which);
	if (error) {
		return error;
	}

	if(itimer_is_real(which)){
		request.number = __NR_setitimer;
		request.args[0] = ihk_mc_syscall_arg0(ctx);
		request.args[1] = ihk_mc_syscall_arg1(ctx);
		request.args[2] = ihk_mc_syscall_arg2(ctx);

		return do_syscall(&request, ihk_mc_get_processor_id());
	}
	else if(which == ITIMER_VIRTUAL){
		if(old){
			memcpy(&wkval, &thread->itimer_virtual, sizeof wkval);
			if(wkval.it_value.tv_sec != 0 ||
			   wkval.it_value.tv_usec != 0){
				ts_to_tv(&tv, &thread->itimer_virtual_value);
				tv_sub(&wkval.it_value, &tv);
			}
			if(copy_to_user(old, &wkval, sizeof wkval))
				return -EFAULT;
		}
		if(!new){
			return 0;
		}
		if (copy_from_user(&thread->itimer_virtual, new, sizeof(struct itimerval))) {
			return -EFAULT;
		}
		thread->itimer_virtual_value.tv_sec = 0;
		thread->itimer_virtual_value.tv_nsec = 0;
		timer_start = itimer_should_start(
				thread->itimer_virtual.it_value.tv_sec,
				thread->itimer_virtual.it_value.tv_usec);
	}
	else if(which == ITIMER_PROF){
		if(old){
			memcpy(&wkval, &thread->itimer_prof, sizeof wkval);
			if(wkval.it_value.tv_sec != 0 ||
			   wkval.it_value.tv_usec != 0){
				ts_to_tv(&tv, &thread->itimer_prof_value);
				tv_sub(&wkval.it_value, &tv);
			}
			if(copy_to_user(old, &wkval, sizeof wkval))
				return -EFAULT;
		}
		if(!new){
			return 0;
		}
		if (copy_from_user(&thread->itimer_prof, new, sizeof(struct itimerval))) {
			return -EFAULT;
		}
		thread->itimer_prof_value.tv_sec = 0;
		thread->itimer_prof_value.tv_nsec = 0;
		timer_start = itimer_should_start(
				thread->itimer_prof.it_value.tv_sec,
				thread->itimer_prof.it_value.tv_usec);
	}
	thread->itimer_enabled = timer_start;
	set_timer(0);
	return 0;
}

SYSCALL_DECLARE(getitimer)
{
	int which = (int)ihk_mc_syscall_arg0(ctx);
	struct itimerval *old = (struct itimerval *)ihk_mc_syscall_arg1(ctx);
	struct syscall_request request IHK_DMA_ALIGN;
	struct thread *thread = cpu_local_var(current);
	struct itimerval wkval;
	struct timeval tv;
	int error;

	error = itimer_which_result(which);
	if (error) {
		return error;
	}

	if(itimer_is_real(which)){
		request.number = __NR_getitimer;
		request.args[0] = ihk_mc_syscall_arg0(ctx);
		request.args[1] = ihk_mc_syscall_arg1(ctx);

		return do_syscall(&request, ihk_mc_get_processor_id());
	}
	else if(which == ITIMER_VIRTUAL){
		if(old){
			memcpy(&wkval, &thread->itimer_virtual, sizeof wkval);
			if(wkval.it_value.tv_sec != 0 ||
			   wkval.it_value.tv_usec != 0){
				ts_to_tv(&tv, &thread->itimer_virtual_value);
				tv_sub(&wkval.it_value, &tv);
			}
			if(copy_to_user(old, &wkval, sizeof wkval))
				return -EFAULT;
		}
	}
	else if(which == ITIMER_PROF){
		if(old){
			memcpy(&wkval, &thread->itimer_prof, sizeof wkval);
			if(wkval.it_value.tv_sec != 0 ||
			   wkval.it_value.tv_usec != 0){
				ts_to_tv(&tv, &thread->itimer_prof_value);
				tv_sub(&wkval.it_value, &tv);
			}
			if(copy_to_user(old, &wkval, sizeof wkval))
				return -EFAULT;
		}
	}
	return 0;
}

SYSCALL_DECLARE(clock_gettime)
{
	/* TODO: handle clock_id */
	struct timespec *ts = (struct timespec *)ihk_mc_syscall_arg1(ctx);
	int clock_id = (int)ihk_mc_syscall_arg0(ctx);
	struct syscall_request request IHK_DMA_ALIGN;
	int error;
	struct timespec ats;
	int dispatch;

	dispatch = clock_gettime_dispatch(clock_id, gettime_local_support,
			ts != NULL);
	if (dispatch == TIME_DISPATCH_NOOP) {
		return 0;
	}

	/* Do it locally if supported */
	if (dispatch == TIME_DISPATCH_LOCAL_REALTIME) {
		calculate_time_from_tsc(&ats);

		error = copy_to_user(ts, &ats, sizeof(ats));

		dkprintf("clock_gettime(): %d\n", error);
		return error;
	}
	else if(dispatch == TIME_DISPATCH_PROCESS_CPUTIME){
		struct thread *thread = cpu_local_var(current);
		struct process *proc = thread->proc;
		struct thread *child;
		struct mcs_rwlock_node lock;

		mcs_rwlock_reader_lock_noirq(&proc->threads_lock, &lock);
		list_for_each_entry(child, &proc->threads_list, siblings_list){
			if(child != thread &&
			   child->status == PS_RUNNING &&
			   !child->in_kernel){
				child->times_update = 0;
				ihk_mc_interrupt_cpu(child->cpu_id,
						ihk_mc_get_vector(IHK_GV_IKC));
			}
		}
		ats.tv_sec = proc->utime.tv_sec;
		ats.tv_nsec = proc->utime.tv_nsec;
		ts_add(&ats, &proc->stime);
		list_for_each_entry(child, &proc->threads_list, siblings_list){
			struct timespec wts;
			while(!child->times_update)
				cpu_pause();
			tsc_to_ts(child->user_tsc + child->system_tsc, &wts);
			ts_add(&ats, &wts);
		}
		mcs_rwlock_reader_unlock_noirq(&proc->threads_lock, &lock);
		return copy_to_user(ts, &ats, sizeof ats);
	}
	else if(dispatch == TIME_DISPATCH_THREAD_CPUTIME){
		struct thread *thread = cpu_local_var(current);

		tsc_to_ts(thread->user_tsc + thread->system_tsc, &ats);
		return copy_to_user(ts, &ats, sizeof ats);
	}

	/* Otherwise offload */
	request.number = __NR_clock_gettime;
	request.args[0] = ihk_mc_syscall_arg0(ctx);
	request.args[1] = ihk_mc_syscall_arg1(ctx);

	return do_syscall(&request, ihk_mc_get_processor_id());
}

SYSCALL_DECLARE(gettimeofday)
{
	struct timeval *tv = (struct timeval *)ihk_mc_syscall_arg0(ctx);
	struct syscall_request request IHK_DMA_ALIGN;
	struct timezone *tz = (struct timezone *)ihk_mc_syscall_arg1(ctx);
	struct timeval atv;
	int error;
	struct timespec ats;
	int dispatch;

	dispatch = gettimeofday_dispatch(tv != NULL, tz != NULL,
			gettime_local_support);
	if (dispatch == TIME_DISPATCH_NOOP) {
		return 0;
	}

	/* Do it locally if supported */
	if (dispatch == TIME_DISPATCH_LOCAL_REALTIME) {
		calculate_time_from_tsc(&ats);

		atv.tv_sec = ats.tv_sec;
		atv.tv_usec = ats.tv_nsec / 1000;

		error = copy_to_user(tv, &atv, sizeof(atv));

		dkprintf("gettimeofday(): %d\n", error);
		return error;
	}

	/* Otherwise offload */
	request.number = __NR_gettimeofday;
	request.args[0] = (unsigned long)tv;
	request.args[1] = (unsigned long)tz;

	return do_syscall(&request, ihk_mc_get_processor_id());
}

SYSCALL_DECLARE(settimeofday)
{
	long error;
	struct timeval * const utv = (void *)ihk_mc_syscall_arg0(ctx);
	struct timezone * const utz = (void *)ihk_mc_syscall_arg1(ctx);
	struct timeval tv;
	struct timespec newts;
	unsigned long tsc;

	dkprintf("sys_settimeofday(%p,%p)\n", utv, utz);
	ihk_mc_spinlock_lock_noirq(&tod_data_lock);
	if (ihk_atomic64_read(&tod_data.version) & 1) {
		panic("settimeofday");
	}

	if (utv && gettime_local_support) {
		if (copy_from_user(&tv, utv, sizeof(tv))) {
			error = -EFAULT;
			goto out;
		}
		newts.tv_sec = tv.tv_sec;
		newts.tv_nsec = (long)tv.tv_usec * 1000;

		tsc = rdtsc();
		newts.tv_sec -= tsc / tod_data.clocks_per_sec;
		newts.tv_nsec -= NS_PER_SEC * (tsc % tod_data.clocks_per_sec)
			/ tod_data.clocks_per_sec;
		if (newts.tv_nsec < 0) {
			--newts.tv_sec;
			newts.tv_nsec += NS_PER_SEC;
		}
	}

	error = syscall_generic_forwarding(n, ctx);

	if (!error && utv && gettime_local_support) {
		dkprintf("sys_settimeofday(%p,%p):origin <-- %ld.%ld\n",
				utv, utz, newts.tv_sec, newts.tv_nsec);
		ihk_atomic64_inc(&tod_data.version);
		wmb();
		tod_data.origin = newts;
		wmb();
		ihk_atomic64_inc(&tod_data.version);
	}

out:
	ihk_mc_spinlock_unlock_noirq(&tod_data_lock);
	dkprintf("sys_settimeofday(%p,%p): %ld\n", utv, utz, error);
	return error;
}

SYSCALL_DECLARE(nanosleep)
{
	struct timespec *tv = (struct timespec *)ihk_mc_syscall_arg0(ctx);
	struct timespec *rem = (struct timespec *)ihk_mc_syscall_arg1(ctx);
	struct syscall_request request IHK_DMA_ALIGN;
	struct ihk_os_cpu_monitor *monitor = cpu_local_var(monitor);

	monitor->status = IHK_OS_MONITOR_KERNEL_HEAVY;

	/* Do it locally if supported */
	if (gettime_local_support) {
		unsigned long nanosecs;
		unsigned long nanosecs_rem;
		unsigned long tscs;
		long tscs_rem;
		struct timespec _tv;
		struct timespec _rem;
		int ret = 0;

		unsigned long ts = rdtsc();

		if (copy_from_user(&_tv, tv, sizeof(*tv))) {
			return -EFAULT;
		}

		ret = nanosleep_validate_timespec(_tv.tv_sec, _tv.tv_nsec);
		if (ret) {
			return ret;
		}

		nanosecs = _tv.tv_sec * NS_PER_SEC + _tv.tv_nsec;
		tscs = nanosecs * 1000 / ihk_mc_get_ns_per_tsc();

		/* Spin wait */
		while (rdtsc() - ts < tscs) {
			if (hassigpending(cpu_local_var(current))) {
				ret = -EINTR;
				break;
			}
			cpu_pause();
		}

		if ((ret == -EINTR) && rem) {
			tscs_rem = tscs - (rdtsc() - ts);
			if (tscs_rem < 0) {
				tscs_rem = 0;
			}
			nanosecs_rem = tscs_rem * ihk_mc_get_ns_per_tsc() / 1000;

			_rem.tv_sec = nanosecs_rem / NS_PER_SEC;
			_rem.tv_nsec = nanosecs_rem % NS_PER_SEC;

			if (copy_to_user(rem, &_rem, sizeof(*rem))) {
				ret = -EFAULT;
			}
		}

		return ret;
	}

	/* Otherwise offload */
	request.number = __NR_nanosleep;
	request.args[0] = (unsigned long)tv;
	request.args[1] = (unsigned long)rem;

	return do_syscall(&request, ihk_mc_get_processor_id());
}

//#define DISABLE_SCHED_YIELD
SYSCALL_DECLARE(sched_yield)
{
	int do_schedule = 0;
	long runq_irqstate;
	struct cpu_local_var *v = get_this_cpu_local_var();

#ifdef DISABLE_SCHED_YIELD
	return 0;
#endif

	runq_irqstate = ihk_mc_spinlock_lock(&v->runq_lock);

	if (v->flags & CPU_FLAG_NEED_RESCHED || v->runq_len > 1) {
		v->flags &= ~CPU_FLAG_NEED_RESCHED;
		do_schedule = 1;
	}

	ihk_mc_spinlock_unlock(&v->runq_lock, runq_irqstate);

	if (do_schedule) {
		schedule();
	}

	return 0;
}

SYSCALL_DECLARE(mlock)
{
	const uintptr_t start0 = ihk_mc_syscall_arg0(ctx);
	const size_t len0 = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = cpu_local_var(current);
	struct vm_regions *region = &thread->vm->region;
	uintptr_t start;
	size_t len;
	uintptr_t end;
	struct vm_range *first;
	uintptr_t addr;
	struct vm_range *range;
	int error;
	struct vm_range *changed;

	dkprintf("[%d]sys_mlock(%lx,%lx)\n",
			ihk_mc_get_processor_id(), start0, len0);

	error = memlock_prepare_range(start0, len0, region->user_start,
			region->user_end, &start, &len, &end);
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
	for (addr = start; addr < end; addr = range->end) {
		if (first == NULL) {
			range = lookup_process_memory_range(thread->vm, start, start+PAGE_SIZE);
			first = range;
		}
		else {
			range = next_process_memory_range(thread->vm, range);
		}

		if (!range || (addr < range->start)) {
			/* not contiguous */
			dkprintf("[%d]sys_mlock(%lx,%lx):not contiguous."
				       " %lx [%lx-%lx)\n",
					ihk_mc_get_processor_id(), start0,
					len0, addr, range->start, range->end);
			error = -ENOMEM;
			goto out;
		}

		error = memlock_range_flag_result(range->flag);
		if (error) {
			ekprintf("[%d]sys_mlock(%lx,%lx):cannot change."
				       " [%lx-%lx) %lx\n",
					ihk_mc_get_processor_id(), start0,
					len0, range->start, range->end,
					range->flag);
			goto out;
		}
	}

	/* do the mlock */
	changed = NULL;
	for (addr = start; addr < end; addr = changed->end) {
		if (!changed) {
			range = first;
		}
		else {
			range = next_process_memory_range(thread->vm, changed);
		}

		if (!range || (addr < range->start)) {
			/* not contiguous */
			dkprintf("[%d]sys_mlock(%lx,%lx):not contiguous."
				       " %lx [%lx-%lx)\n",
					ihk_mc_get_processor_id(), start0,
					len0, addr, range?range->start:0,
					range?range->end:0);
			error = -ENOMEM;
			goto out;
		}

		if (range->start < addr) {
			error = split_process_memory_range(thread->vm, range, addr, &range);
			if (error) {
				ekprintf("[%d]sys_mlock(%lx,%lx):split failed. "
						" [%lx-%lx) %lx %d\n",
						ihk_mc_get_processor_id(),
						start0, len0, range->start,
						range->end, addr, error);
				goto out;
			}
		}
		if (end < range->end) {
			error = split_process_memory_range(thread->vm, range, end, NULL);
			if (error) {
				ekprintf("[%d]sys_mlock(%lx,%lx):split failed. "
						" [%lx-%lx) %lx %d\n",
						ihk_mc_get_processor_id(),
						start0, len0, range->start,
						range->end, addr, error);
				goto out;
			}
		}

		range->flag |= VR_LOCKED;

		if (!changed) {
			changed = range;
		}
		else {
			error = join_process_memory_range(thread->vm, changed, range);
			if (error) {
				dkprintf("[%d]sys_mlock(%lx,%lx):join failed. %d",
						ihk_mc_get_processor_id(),
						start0, len0, error);
				dkprintf("LHS: %p [%lx-%lx) %lx %p\n",
						changed, changed->start,
						changed->end, changed->flag,
						changed->memobj);
				dkprintf("RHS: %p [%lx-%lx) %lx %p\n",
						range, range->start,
						range->end, range->flag,
						range->memobj);
				changed = range;
				/* through */
			}
		}
	}

	error = 0;
out:
	ihk_rwspinlock_write_unlock_noirq(&thread->vm->memory_range_lock);

	if (!error) {
		error = populate_process_memory(thread->vm, (void *)start, len);
		if (error) {
			ekprintf("sys_mlock(%lx,%lx):populate failed. %d\n",
					start0, len0, error);
			/*
			 * In this case,
			 * the region locked by this call should be unlocked
			 * before mlock() returns with error.
			 *
			 * However, the region cannot be unlocked simply,
			 * because the region can be modified by other thread
			 * because memory_range_lock has been released.
			 *
			 * For the time being, like a linux-2.6.38-8,
			 * the physical page allocation failure is ignored.
			 */
			error = 0;
		}
	}

out2:
	dkprintf("[%d]sys_mlock(%lx,%lx): %d\n",
			ihk_mc_get_processor_id(), start0, len0, error);
	return error;
}

SYSCALL_DECLARE(munlock)
{
	const uintptr_t start0 = ihk_mc_syscall_arg0(ctx);
	const size_t len0 = ihk_mc_syscall_arg1(ctx);
	struct thread *thread = cpu_local_var(current);
	struct vm_regions *region = &thread->vm->region;
	uintptr_t start;
	size_t len;
	uintptr_t end;
	struct vm_range *first;
	uintptr_t addr;
	struct vm_range *range;
	int error;
	struct vm_range *changed;

	dkprintf("[%d]sys_munlock(%lx,%lx)\n",
			ihk_mc_get_processor_id(), start0, len0);

	error = memlock_prepare_range(start0, len0, region->user_start,
			region->user_end, &start, &len, &end);
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
	for (addr = start; addr < end; addr = range->end) {
		if (first == NULL) {
			range = lookup_process_memory_range(thread->vm, start, start+PAGE_SIZE);
			first = range;
		}
		else {
			range = next_process_memory_range(thread->vm, range);
		}

		if (!range || (addr < range->start)) {
			/* not contiguous */
			dkprintf("[%d]sys_munlock(%lx,%lx):not contiguous."
				       " %lx [%lx-%lx)\n",
					ihk_mc_get_processor_id(), start0,
					len0, addr, range->start, range->end);
			error = -ENOMEM;
			goto out;
		}

		error = memlock_range_flag_result(range->flag);
		if (error) {
			ekprintf("[%d]sys_munlock(%lx,%lx):cannot change."
				       " [%lx-%lx) %lx\n",
					ihk_mc_get_processor_id(), start0,
					len0, range->start, range->end,
					range->flag);
			goto out;
		}
	}

	/* do the munlock */
	changed = NULL;
	for (addr = start; addr < end; addr = changed->end) {
		if (!changed) {
			range = first;
		}
		else {
			range = next_process_memory_range(thread->vm, changed);
		}

		if (!range || (addr < range->start)) {
			/* not contiguous */
			dkprintf("[%d]sys_munlock(%lx,%lx):not contiguous."
				       " %lx [%lx-%lx)\n",
					ihk_mc_get_processor_id(), start0,
					len0, addr, range?range->start:0,
					range?range->end:0);
			error = -ENOMEM;
			goto out;
		}

		if (range->start < addr) {
			error = split_process_memory_range(thread->vm, range, addr, &range);
			if (error) {
				ekprintf("[%d]sys_munlock(%lx,%lx):split failed. "
						" [%lx-%lx) %lx %d\n",
						ihk_mc_get_processor_id(),
						start0, len0, range->start,
						range->end, addr, error);
				goto out;
			}
		}
		if (end < range->end) {
			error = split_process_memory_range(thread->vm, range, end, NULL);
			if (error) {
				ekprintf("[%d]sys_munlock(%lx,%lx):split failed. "
						" [%lx-%lx) %lx %d\n",
						ihk_mc_get_processor_id(),
						start0, len0, range->start,
						range->end, addr, error);
				goto out;
			}
		}

		range->flag &= ~VR_LOCKED;

		if (!changed) {
			changed = range;
		}
		else {
			error = join_process_memory_range(thread->vm, changed, range);
			if (error) {
				dkprintf("[%d]sys_munlock(%lx,%lx):join failed. %d",
						ihk_mc_get_processor_id(),
						start0, len0, error);
				dkprintf("LHS: %p [%lx-%lx) %lx %p\n",
						changed, changed->start,
						changed->end, changed->flag,
						changed->memobj);
				dkprintf("RHS: %p [%lx-%lx) %lx %p\n",
						range, range->start,
						range->end, range->flag,
						range->memobj);
				changed = range;
				/* through */
			}
		}
	}

	error = 0;
out:
	ihk_rwspinlock_write_unlock_noirq(&thread->vm->memory_range_lock);
out2:
	dkprintf("[%d]sys_munlock(%lx,%lx): %d\n",
			ihk_mc_get_processor_id(), start0, len0, error);
	return error;
}

SYSCALL_DECLARE(mlockall)
{
	const int flags = ihk_mc_syscall_arg0(ctx);
	struct thread *thread = cpu_local_var(current);
	struct process *proc = thread->proc;
	int error;

	error = mlockall_policy_result(flags, proc->euid == 0,
			proc->rlimit[MCK_RLIMIT_MEMLOCK].rlim_cur);
	if (error == -EINVAL) {
		kprintf("mlockall(0x%x):invalid flags: EINVAL\n", flags);
		return error;
	}

	if (!error) {
		kprintf("mlockall(0x%x):priv user: 0\n", flags);
		return error;
	}

	if (error == -ENOMEM) {
		kprintf("mlockall(0x%x):limits exists: ENOMEM\n", flags);
		return error;
	}

	kprintf("mlockall(0x%x):no lock permitted: EPERM\n", flags);
	return error;
} /* sys_mlockall() */

SYSCALL_DECLARE(munlockall)
{
	kprintf("munlockall(): 0\n");
	return 0;
} /* sys_munlockall() */

SYSCALL_DECLARE(remap_file_pages)
{
	const uintptr_t start0 = ihk_mc_syscall_arg0(ctx);
	const size_t size = ihk_mc_syscall_arg1(ctx);
	const int prot = ihk_mc_syscall_arg2(ctx);
	const size_t pgoff = ihk_mc_syscall_arg3(ctx);
	const int flags = ihk_mc_syscall_arg4(ctx);
	int error;
	uintptr_t start;
	uintptr_t end;
	off_t off;
	struct thread * const thread = cpu_local_var(current);
	struct vm_range *range;
	int er;
	int need_populate = 0;

	dkprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x)\n",
			start0, size, prot, pgoff, flags);
	ihk_rwspinlock_write_lock_noirq(&thread->vm->memory_range_lock);
	error = remap_file_pages_prepare(start0, size, prot, pgoff,
			&start, &end, &off);
	if (error) {
		ekprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x):"
				"invalid args\n",
				start0, size, prot, pgoff, flags);
		goto out;
	}

	range = lookup_process_memory_range(thread->vm, start, end);
	if (!range || (start < range->start) || (range->end < end)
			|| (range->flag & VR_PRIVATE)
			|| range_has_disallowed_change_flags(range->flag)
			|| !is_callable_remap_file_pages(range->memobj)) {
		ekprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x):"
				"invalid VMR:[%#lx-%#lx) %#lx %p\n",
				start0, size, prot, pgoff, flags,
				range?range->start:0, range?range->end:0,
				range?range->flag:0, range?range->memobj:NULL);
		error = -EINVAL;
		goto out;
	}

	flush_nfo_tlb();

	range->flag |= VR_FILEOFF;
	error = remap_process_memory_range(thread->vm, range, start, end, off);
	if (error) {
		ekprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x):"
				"remap failed %d\n",
				start0, size, prot, pgoff, flags, error);
		goto out;
	}
	clear_host_pte(start, size, 1 /* memory range lock */);	/* XXX: workaround */

	if (range->flag & VR_LOCKED) {
		need_populate = 1;
	}
	error = 0;
out:
	ihk_rwspinlock_write_unlock_noirq(&thread->vm->memory_range_lock);

	if (need_populate
			&& (er = populate_process_memory(
					thread->vm, (void *)start, size))) {
		ekprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x):"
				"populate failed %d\n",
				start0, size, prot, pgoff, flags, er);
		/* ignore populate error */
	}

	dkprintf("sys_remap_file_pages(%#lx,%#lx,%#x,%#lx,%#x): %d\n",
			start0, size, prot, pgoff, flags, error);
	return error;
}

SYSCALL_DECLARE(mremap)
{
	const uintptr_t oldaddr = ihk_mc_syscall_arg0(ctx);
	const size_t oldsize0 = ihk_mc_syscall_arg1(ctx);
	const size_t newsize0 = ihk_mc_syscall_arg2(ctx);
	const int flags = ihk_mc_syscall_arg3(ctx);
	const uintptr_t newaddr = ihk_mc_syscall_arg4(ctx);
	size_t oldsize;
	size_t newsize;
	const uintptr_t oldstart = oldaddr;
	uintptr_t oldend;
	struct thread *thread = cpu_local_var(current);
	struct process_vm *vm = thread->vm;
	int error;
	struct vm_range *range;
	int need_relocate;
	uintptr_t newstart;
	uintptr_t newend;
	size_t size;
	uintptr_t ret;
	uintptr_t lckstart = -1;
	uintptr_t lckend = -1;
	int no_op;

	dkprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx)\n",
			oldaddr, oldsize0, newsize0, flags, newaddr);

	if (vm->proc->straight_va &&
			(void *)oldaddr >= vm->proc->straight_va &&
			(void *)oldaddr < vm->proc->straight_va + vm->proc->straight_len) {
		kprintf("%s: reject for straight range 0x%lx\n",
				__FUNCTION__, oldaddr);
		return -EINVAL;
	}

	ihk_rwspinlock_write_lock_noirq(&vm->memory_range_lock);

	error = mremap_prepare_args(oldaddr, oldsize0, newsize0, flags,
			newaddr, vm->region.user_start, vm->region.user_end,
			&oldsize, &newsize, &oldend, &no_op);
	if (error == -EINVAL) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):invalid. %d\n",
				oldaddr, oldsize0, newsize0, flags, newaddr,
				error);
		goto out;
	}
	if (error == -ENOMEM) {
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"cannot allocate. %d\n",
				oldaddr, oldsize0, newsize0,
				flags, newaddr, error);
		goto out;
	}
	if (no_op) {
		/* Nothing to do */
		error = 0;
		newstart = oldaddr;
		goto out;
	}

	/* check original mapping */
	range = lookup_process_memory_range(vm, oldstart, oldstart+PAGE_SIZE);
	if (!range || (oldstart < range->start) || (range->end < oldend)
			|| (range->flag & (VR_FILEOFF))
			|| range_has_disallowed_change_flags(range->flag)) {
		error = -EFAULT;
		ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
				"lookup failed. %d %p %#lx-%#lx %#lx\n",
				oldaddr, oldsize0, newsize0, flags, newaddr,
				error, range, range?range->start:0,
				range?range->end:0, range?range->flag:0);
		goto out;
	}

	/* determine new mapping range */
	need_relocate = 0;
	if (flags & MREMAP_FIXED) {
		need_relocate = 1;
		newstart = newaddr;
		newend = newstart + newsize;
		error = mremap_fixed_range_result(newstart,
				vm->region.user_start, oldstart, oldend, newend);
		if (error == -EPERM) {
			ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
					"mmap_min_addr %#lx. %d\n",
					oldaddr, oldsize0, newsize0, flags,
					newaddr, vm->region.user_start,
					error);
			goto out;
		}
		if (error == -EINVAL) {
			ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
					"fixed:overlapped. %d\n",
					oldaddr, oldsize0, newsize0, flags,
					newaddr, error);
			goto out;
		}
	}
	else if (!(flags & MREMAP_FIXED) && (oldsize < newsize)) {
		if (oldend == range->end) {
			newstart = oldstart;
			newend = newstart + newsize;
			error = extend_up_process_memory_range(vm, range,
					newend);
			flush_nfo_tlb();
			if (!error) {
				if (range->flag & VR_LOCKED) {
					lckstart = oldend;
					lckend = newend;
				}
				goto out;
			}
		}
		error = mremap_maymove_result(flags);
		if (error) {
			ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
					"cannot relocate. %d\n",
					oldaddr, oldsize0, newsize0, flags,
					newaddr, error);
			goto out;
		}
		need_relocate = 1;
		error = search_free_space(newsize, range->pgshift, &newstart);
		if (error) {
			ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
					"search failed. %d\n",
					oldaddr, oldsize0, newsize0, flags,
					newaddr, error);
			goto out;
		}
		newend = newstart + newsize;
	}
	else {
		newstart = oldstart;
		newend = newstart + newsize;
	}

	/* do the remap */
	if (need_relocate) {
		if (flags & MREMAP_FIXED) {
			error = do_munmap((void *)newstart, newsize, 1/* holding memory_range_lock */);
			if (error) {
				ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
						"fixed:munmap failed. %d\n",
						oldaddr, oldsize0, newsize0,
						flags, newaddr, error);
				goto out;
			}
		}
		if (range->memobj) {
			memobj_ref(range->memobj);
		}
		error = add_process_memory_range(thread->vm, newstart, newend, -1,
				range->flag, range->memobj,
				range->objoff + (oldstart - range->start),
				0, NULL, NULL);
		if (error) {
			ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
					"add failed. %d\n",
					oldaddr, oldsize0, newsize0, flags,
					newaddr, error);
			if (range->memobj) {
				memobj_unref(range->memobj);
			}
			goto out;
		}
		flush_nfo_tlb();
		if (range->flag & VR_LOCKED) {
			lckstart = newstart;
			lckend = newend;
		}

		if (oldsize > 0) {
			size = (oldsize < newsize)? oldsize: newsize;
			ihk_mc_spinlock_lock_noirq(&vm->page_table_lock);
			if (range->start != oldstart) {
				error = split_process_memory_range(vm,
						range, oldstart, &range);
				if (error) {
					ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
						"split range failed. %d\n",
						oldaddr, oldsize0, newsize0,
						flags, newaddr, error);
					goto out;
				}
			}
			if (range->end != oldstart + size) {
				error = split_process_memory_range(vm,
						range, oldstart + size, NULL);
				if (error) {
					ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
						"split range failed. %d\n",
						oldaddr, oldsize0, newsize0,
						flags, newaddr, error);
					goto out;
				}
			}

			error = move_pte_range(vm->address_space->page_table, vm,
								   (void *)oldstart, (void *)newstart,
								   size, range);
			ihk_mc_spinlock_unlock_noirq(&vm->page_table_lock);
			if (error) {
				ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
						"move failed. %d\n",
						oldaddr, oldsize0, newsize0,
						flags, newaddr, error);
				goto out;
			}

			error = do_munmap((void *)oldstart, oldsize, 1/* holding memory_range_lock */);
			if (error) {
				ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
						"relocate:munmap failed. %d\n",
						oldaddr, oldsize0, newsize0,
						flags, newaddr, error);
				goto out;
			}
		}
	}
	else if (newsize < oldsize) {
		error = do_munmap((void *)newend, (oldend - newend), 1/* holding memory_range_lock */);
		if (error) {
			ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
					"shrink:munmap failed. %d\n",
					oldaddr, oldsize0, newsize0, flags,
					newaddr, error);
			goto out;
		}
	}
	else {
		/* nothing to do */
	}

	error = 0;
out:
	ihk_rwspinlock_write_unlock_noirq(&vm->memory_range_lock);
	if (!error && (lckstart < lckend)) {
		error = populate_process_memory(thread->vm, (void *)lckstart, (lckend - lckstart));
		if (error) {
			ekprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):"
					"populate failed. %d %#lx-%#lx\n",
					oldaddr, oldsize0, newsize0, flags,
					newaddr, error, lckstart, lckend);
			error = 0;	/* ignore error */
		}
	}
	ret = (error)? error: newstart;
	dkprintf("sys_mremap(%#lx,%#lx,%#lx,%#x,%#lx):%d %#lx\n",
			oldaddr, oldsize0, newsize0, flags, newaddr, error,
			ret);
	return ret;
}

SYSCALL_DECLARE(msync)
{
	const uintptr_t start0 = ihk_mc_syscall_arg0(ctx);
	const size_t len0 = ihk_mc_syscall_arg1(ctx);
	const int flags = ihk_mc_syscall_arg2(ctx);
	size_t len;
	const uintptr_t start = start0;
	uintptr_t end;
	struct thread *thread = cpu_local_var(current);
	struct process_vm *vm = thread->vm;
	int error;
	uintptr_t addr;
	struct vm_range *range;
	uintptr_t s;
	uintptr_t e;

	dkprintf("sys_msync(%#lx,%#lx,%#x)\n", start0, len0, flags);
	ihk_rwspinlock_read_lock_noirq(&vm->memory_range_lock);

	error = msync_prepare_range(start0, len0, flags, &len, &end);
	if (error) {
		ekprintf("sys_msync(%#lx,%#lx,%#x):invalid args. %d\n",
				start0, len0, flags, error);
		goto out;
	}

	/* check ranges */
	range = NULL;
	for (addr = start; addr < end; addr = range->end) {
		if (!range) {
			range = lookup_process_memory_range(vm, addr,
					addr+PAGE_SIZE);
		}
		else {
			range = next_process_memory_range(vm, range);
		}

		if (!range || (addr < range->start)) {
			error = -ENOMEM;
			ekprintf("sys_msync(%#lx,%#lx,%#x):"
					"invalid VMR %d %#lx-%#lx %#lx\n",
					start0, len0, flags, error,
					range?range->start:0,
					range?range->end:0,
					range?range->flag:0);
			goto out;
		}
		error = msync_locked_range_result(flags, range->flag);
		if (error) {
			ekprintf("sys_msync(%#lx,%#lx,%#x):"
					"locked VMR %d %#lx-%#lx %#lx\n",
					start0, len0, flags, error,
					range->start, range->end, range->flag);
			goto out;
		}
	}

	/* do the sync */
	range = NULL;
	for (addr = start; addr < end; addr = range->end) {
		if (!range) {
			range = lookup_process_memory_range(vm, addr,
					addr+PAGE_SIZE);
		}
		else {
			range = next_process_memory_range(vm, range);
		}

		if ((range->flag & VR_PRIVATE) || !range->memobj
				|| !memobj_has_pager(range->memobj)) {
			dkprintf("sys_msync(%#lx,%#lx,%#x):unsyncable VMR %#lx-%#lx %#lx\n",
					start0, len0, flags,
					range->start, range->end, range->flag);
			/* nothing to do */
			continue;
		}

		s = addr;
		e = (range->end < end)? range->end: end;

		if (flags & (MS_ASYNC | MS_SYNC)) {
			error = sync_process_memory_range(vm, range, s, e);
			if (error) {
				ekprintf("sys_msync(%#lx,%#lx,%#x):sync failed. %d\n",
						start0, len0, flags, error);
				goto out;
			}
		}

		if (flags & MS_INVALIDATE) {
			error = invalidate_process_memory_range(
					vm, range, s, e);
			if (error) {
				ekprintf("sys_msync(%#lx,%#lx,%#x):"
						"invalidate failed. %d\n",
						start0, len0, flags, error);
				goto out;
			}
		}
	}

	error = 0;
out:
	ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);
	dkprintf("sys_msync(%#lx,%#lx,%#x):%d\n", start0, len0, flags, error);
	return error;
} /* sys_msync() */

SYSCALL_DECLARE(getcpu)
{
	const uintptr_t cpup = ihk_mc_syscall_arg0(ctx);
	const uintptr_t nodep = ihk_mc_syscall_arg1(ctx);
	const int cpu = ihk_mc_get_processor_id();
	const int node = ihk_mc_get_numa_id();
	int error;

	if (cpup) {
		error = copy_to_user((void *)cpup, &cpu, sizeof(cpu));
		if (error) {
			goto out;
		}
	}

	if (nodep) {
		error = copy_to_user((void *)nodep, &node, sizeof(node));
		if (error) {
			goto out;
		}
	}

	error = 0;
out:
	return error;
} /* sys_getcpu() */

SYSCALL_DECLARE(mbind)
{
	unsigned long addr = ihk_mc_syscall_arg0(ctx);
	unsigned long len = ihk_mc_syscall_arg1(ctx);
	int mode = ihk_mc_syscall_arg2(ctx);
	unsigned long *nodemask =
		(unsigned long *)ihk_mc_syscall_arg3(ctx);
	unsigned long maxnode = ihk_mc_syscall_arg4(ctx);
	unsigned flags = ihk_mc_syscall_arg5(ctx);
	struct process_vm *vm = cpu_local_var(current)->vm;
	unsigned long nodemask_bits = 0;
	int mode_flags = 0;
	int error = 0;
	int bit;
	struct vm_range *range;
	struct vm_range_numa_policy *range_policy, *range_policy_iter = NULL;
	DECLARE_BITMAP(numa_mask, PROCESS_NUMA_MASK_BITS);

	dkprintf("%s: addr: 0x%lx, len: %lu, mode: 0x%x, "
		"nodemask: 0x%lx, flags: %lx\n",
		__FUNCTION__,
		addr, len, mode, nodemask, flags);

	/* No bind support for straight mapped processes */
	if (cpu_local_var(current)->proc->straight_va) {
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
			for_each_set_bit(bit, numa_mask,
					maxnode < PROCESS_NUMA_MASK_BITS ?
					maxnode : PROCESS_NUMA_MASK_BITS) {
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
			list_for_each_entry_safe(range_policy_iter, range_policy_next,
					&vm->vm_range_numa_policy_list, list) {
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
						range_policy = kmalloc(sizeof(*range_policy),
								IHK_MC_AP_NOWAIT);
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
					kfree(range_policy_iter);
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
			range_policy = kmalloc(sizeof(struct vm_range_numa_policy),
					IHK_MC_AP_NOWAIT);
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

SYSCALL_DECLARE(set_mempolicy)
{
	int mode = ihk_mc_syscall_arg0(ctx);
	unsigned long *nodemask =
		(unsigned long *)ihk_mc_syscall_arg1(ctx);
	unsigned long maxnode = ihk_mc_syscall_arg2(ctx);
	unsigned long nodemask_bits = 0;
	struct process_vm *vm = cpu_local_var(current)->vm;
	int error = 0;
	int bit, valid_mask;
	DECLARE_BITMAP(numa_mask, PROCESS_NUMA_MASK_BITS);

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

	error = set_mempolicy_normalize_mode(mode, &mode);
	if (error) {
		goto out;
	}
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

			memset(vm->numa_mask, 0, sizeof(numa_mask));
			for (bit = 0; bit < ihk_mc_get_nr_numa_nodes(); ++bit) {
				set_bit(bit, vm->numa_mask);
			}

#if 0
			/* In man, "MPOL_DEFAULT mode deletes a process memory policy 
			   other than the default and interprets that the memory policy" 
			   falls back to the system default policy ", but not to delete 
			   the NUMA memory policy.
			   There was no processing of Linux's same name command. */

			/* Delete all range settings */
			ihk_mc_spinlock_lock_noirq(&vm->memory_range_lock);
			list_for_each_entry_safe(range_policy_iter, range_policy_next,
					&vm->vm_range_numa_policy_list, list) {
				list_del(&range_policy_iter->list);
				kfree(range_policy_iter);
			}
			ihk_mc_spinlock_unlock_noirq(&vm->memory_range_lock);
#endif

			vm->numa_mem_policy = mode;
			error = 0;
			break;

		case MPOL_BIND:
		case MPOL_INTERLEAVE:
		case MPOL_PREFERRED:
			/* Special case for MPOL_PREFERRED with empty nodemask */
			if (mode == MPOL_PREFERRED && !nodemask) {
				memset(vm->numa_mask, 0, sizeof(numa_mask));
				for (bit = 0; bit < ihk_mc_get_nr_numa_nodes(); ++bit) {
					set_bit(bit, vm->numa_mask);
				}

				vm->numa_mem_policy = mode;
				error = 0;
				break;
			}

			if (!nodemask) {
				dkprintf("%s: ERROR: nodemask not specified\n",
						__FUNCTION__);
				error = -EINVAL;
				goto out;
			}

			error = copy_from_user(numa_mask, nodemask,
					(nodemask_bits >> 3));
			if (error) {
				error = -EFAULT;
				goto out;
			}

			/* Verify NUMA mask */
			valid_mask = 0;
			for_each_set_bit(bit, numa_mask,
					maxnode < PROCESS_NUMA_MASK_BITS ?
					maxnode : PROCESS_NUMA_MASK_BITS) {
				if (bit >= ihk_mc_get_nr_numa_nodes()) {
					dkprintf("%s: %d is bigger than # of NUMA nodes\n",
						__FUNCTION__, bit);
					error = -EINVAL;
					goto out;
				}

				/* Is there at least one node which is allowed
				 * in current mask? */
				if (test_bit(bit, vm->numa_mask)) {
					valid_mask = 1;
				}
			}

			if (!valid_mask) {
				dkprintf("%s: ERROR: invalid nodemask\n", __FUNCTION__);
				error = -EINVAL;
				goto out;
			}

			/* Update current mask by clearing non-requested nodes */
			for_each_set_bit(bit, vm->numa_mask,
					maxnode < PROCESS_NUMA_MASK_BITS ?
					maxnode : PROCESS_NUMA_MASK_BITS) {
				if (!test_bit(bit, numa_mask)) {
					clear_bit(bit, vm->numa_mask);
				}
			}

			vm->numa_mem_policy = mode;
			if (mode == MPOL_INTERLEAVE) {
				vm->il_prev = PROCESS_NUMA_MASK_BITS - 1;
			}
			error = 0;
			break;

		default:
			error = -EINVAL;
	}

	dkprintf("%s: %s set for PID %d\n",
			__FUNCTION__,
			mode == MPOL_DEFAULT ? "MPOL_DEFAULT" :
			mode == MPOL_INTERLEAVE ? "MPOL_INTERLEAVE" :
			mode == MPOL_BIND ? "MPOL_BIND" :
			mode == MPOL_PREFERRED ? "MPOL_PREFERRED" :
			"unknown",
			cpu_local_var(current)->proc->pid);

out:
	return error;
} /* sys_set_mempolicy() */

SYSCALL_DECLARE(get_mempolicy)
{
	int *mode = (int *)ihk_mc_syscall_arg0(ctx);
	unsigned long *nodemask =
		(unsigned long *)ihk_mc_syscall_arg1(ctx);
	unsigned long nodemask_bits = 0;
	unsigned long maxnode = ihk_mc_syscall_arg2(ctx);
	unsigned long addr = ihk_mc_syscall_arg3(ctx);
	unsigned long flags = ihk_mc_syscall_arg4(ctx);
	struct process_vm *vm = cpu_local_var(current)->vm;
	struct vm_range_numa_policy *range_policy = NULL;
	int error = 0;
	int policy;

	error = get_mempolicy_validate(addr, flags, vm->numa_mem_policy,
			maxnode, ihk_mc_get_nr_numa_nodes(), &nodemask_bits);
	if (error) {
		return error;
	}
	if (mempolicy_nodemask_bits_is_clamped(maxnode)) {
		dkprintf("%s: WARNING: process NUMA mask bits is insufficient\n",
			__FUNCTION__);
	}

	/* case of MPOL_F_NODE and MPOL_F_ADDR are specified */
	if (flags & MPOL_F_NODE && flags & MPOL_F_ADDR) {
		/* return the node ID which addr is allocated by mode */
		int nid;

		nid = lookup_node(vm, (void *)addr);
		error = copy_to_user(mode, &nid, sizeof(int));
		if (error) {
			error = -EFAULT;
			goto out;
		}
		goto out;
	}

	/* Special case of MPOL_F_MEMS_ALLOWED */
	if (flags == MPOL_F_MEMS_ALLOWED) {
		if (nodemask) {
			error = copy_to_user(nodemask,
					cpu_local_var(current)->vm->numa_mask,
					(nodemask_bits >> 3));
			if (error) {
				error = -EFAULT;
			}
		}

		goto out;
	}

	/* Address range specific? */
	if (flags & MPOL_F_ADDR) {
		struct vm_range *range;

		ihk_rwspinlock_read_lock_noirq(&vm->memory_range_lock);
		range = lookup_process_memory_range(vm, addr, addr + 1);
		if (!range) {
			dkprintf("%s: ERROR: range is invalid\n", __FUNCTION__);
			error = -EFAULT;
			ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);
			goto out;
		}

		range_policy = vm_range_policy_search(vm, addr);

		ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);
	}

	/* Return policy */
	policy = range_policy ? range_policy->numa_mem_policy :
		vm->numa_mem_policy;

	if (mode) {
		error = copy_to_user(mode, &policy, sizeof(int));
		if (error) {
			error = -EFAULT;
			goto out;
		}
	}

	if (nodemask && (policy != MPOL_DEFAULT)) {
		error = copy_to_user(nodemask,
				range_policy ? range_policy->numa_mask :
				cpu_local_var(current)->vm->numa_mask,
				(nodemask_bits >> 3));
		if (error) {
			error = -EFAULT;
			goto out;
		}
	}

out:
	return error;
} /* sys_get_mempolicy() */

SYSCALL_DECLARE(migrate_pages)
{
	dkprintf("sys_migrate_pages\n");
	return -ENOSYS;
} /* sys_migrate_pages() */

SYSCALL_DECLARE(move_pages)
{
	extern int move_pages_smp_handler(int cpu_index, int nr_cpus, void *arg);
	int pid = ihk_mc_syscall_arg0(ctx);
	unsigned long count = ihk_mc_syscall_arg1(ctx);
	const void **user_virt_addr = (const void **)ihk_mc_syscall_arg2(ctx);
	const int *user_nodes = (const int *)ihk_mc_syscall_arg3(ctx);
	int *user_status = (int *)ihk_mc_syscall_arg4(ctx);
	int flags = ihk_mc_syscall_arg5(ctx);

	void **virt_addr = NULL;
	int *nodes = NULL, *status = NULL;
	int *nr_pages = NULL;
	unsigned long *dst_phys = NULL;
	pte_t **ptep = NULL;
	struct move_pages_smp_req mpsr;

	struct process_vm *vm = cpu_local_var(current)->vm;
	int i, ret = 0;

	unsigned long t_s, t_e;

	t_s = rdtsc();

	ret = move_pages_policy_result(pid, flags);
	if (ret) {
		if (pid) {
			kprintf("%s: ERROR: only self (pid == 0)"
					" is supported\n", __FUNCTION__);
		}
		else if (flags & MPOL_MF_MOVE_ALL) {
			kprintf("%s: ERROR: MPOL_MF_MOVE_ALL"
				" not supported\n", __func__);
		}
		goto out;
	}

	/* Allocate kernel arrays */
	virt_addr = kmalloc(sizeof(void *) * count, IHK_MC_AP_NOWAIT);
	if (!virt_addr) {
		ret = -ENOMEM;
		goto dealloc_out;
	}

	nr_pages = kmalloc(sizeof(int) * count, IHK_MC_AP_NOWAIT);
	if (!nr_pages) {
		ret = -ENOMEM;
		goto dealloc_out;
	}

	nodes = kmalloc(sizeof(int) * count, IHK_MC_AP_NOWAIT);
	if (!nodes) {
		ret = -ENOMEM;
		goto dealloc_out;
	}

	status = kmalloc(sizeof(int) * count, IHK_MC_AP_NOWAIT);
	if (!status) {
		ret = -ENOMEM;
		goto dealloc_out;
	}

	ptep = kmalloc(sizeof(pte_t) * count, IHK_MC_AP_NOWAIT);
	if (!ptep) {
		ret = -ENOMEM;
		goto dealloc_out;
	}

	dst_phys = kmalloc(sizeof(unsigned long) * count, IHK_MC_AP_NOWAIT);
	if (!dst_phys) {
		ret = -ENOMEM;
		goto dealloc_out;
	}
t_e = rdtsc(); kprintf("%s: init malloc: %lu \n", __FUNCTION__, t_e - t_s); t_s = t_e;

	/* Get virt addresses and NUMA node numbers from user */
	if (verify_process_vm(cpu_local_var(current)->vm,
				user_virt_addr, sizeof(void *) * count)) {
		ret = -EFAULT;
		goto dealloc_out;
	}

	if (user_nodes && verify_process_vm(cpu_local_var(current)->vm,
				user_nodes, sizeof(int) * count)) {
		ret = -EFAULT;
		goto dealloc_out;
	}

	if (verify_process_vm(cpu_local_var(current)->vm,
				user_status, sizeof(int) * count)) {
		ret = -EFAULT;
		goto dealloc_out;
	}

	/* Check node ID */
	if (user_nodes) {
		copy_from_user(nodes, user_nodes, sizeof(int) * count);
		for (i = 0; i < count; i++) {
			if (nodes[i] < 0 || nodes[i] >= ihk_mc_get_nr_numa_nodes()) {
				ret = -ENODEV;
				goto dealloc_out;
			}
		}
	}

t_e = rdtsc(); kprintf("%s: init verify: %lu \n", __FUNCTION__, t_e - t_s); t_s = t_e;

#if 0
	memcpy(virt_addr, user_virt_addr, sizeof(void *) * count);
	memcpy(status, user_status, sizeof(int) * count);
	memcpy(nodes, user_nodes, sizeof(int) * count);

	if (copy_from_user(virt_addr, user_virt_addr,
				sizeof(void *) * count)) {
		ret = -EFAULT;
		goto dealloc_out;
	}

	if (copy_from_user(nodes, user_nodes, sizeof(int) * count)) {
		ret = -EFAULT;
		goto dealloc_out;
	}

	/* Won't use it but better to verify the user buffer before
	 * doing anything.. */
	if (copy_from_user(status, user_status, sizeof(int) * count)) {
		ret = -EFAULT;
		goto dealloc_out;
	}

t_e = rdtsc(); kprintf("%s: init copy: %lu \n", __FUNCTION__, t_e - t_s); t_s = t_e;

	/* Verify target NUMA nodes are valid */
	for (i = 0; i < count; i++) {
		if (nodes[i] < 0 ||
				nodes[i] >= ihk_mc_get_nr_numa_nodes() ||
				!test_bit(nodes[i], vm->numa_mask)) {
			ret = -EINVAL;
			goto dealloc_out;
		}
	}

t_e = rdtsc(); kprintf("%s: init NUMAver: %lu \n", __FUNCTION__, t_e - t_s); t_s = t_e;

	memset(ptep, 0, sizeof(pte_t) * count);
	memset(status, 0, sizeof(int) * count);
	memset(nr_pages, 0, sizeof(int) * count);
	memset(dst_phys, 0, sizeof(unsigned long) * count);

t_e = rdtsc(); kprintf("%s: init memset: %lu \n", __FUNCTION__, t_e - t_s); t_s = t_e;
#endif

	ihk_mc_spinlock_lock_noirq(&vm->page_table_lock);

	/* Do the arg init, NUMA verification, copy,
	 * update PTEs, free original memory */
	mpsr.count = count;
	mpsr.user_virt_addr = user_virt_addr;
	mpsr.user_status = user_status;
	mpsr.user_nodes = user_nodes;
	mpsr.virt_addr = virt_addr;
	mpsr.status = status;
	mpsr.nodes = nodes;
	mpsr.nodes_ready = 0;
	mpsr.ptep = ptep;
	mpsr.dst_phys = dst_phys;
	mpsr.nr_pages = nr_pages;
	mpsr.proc = cpu_local_var(current)->proc;
	ihk_atomic_set(&mpsr.phase_done, 0);
	mpsr.phase_ret = 0;
	ret = smp_call_func(&cpu_local_var(current)->cpu_set,
		move_pages_smp_handler, &mpsr);

	ihk_mc_spinlock_unlock_noirq(&vm->page_table_lock);

	if (ret != 0) {
		goto dealloc_out;
	}

t_e = rdtsc(); kprintf("%s: parallel: %lu \n", __FUNCTION__, t_e - t_s); t_s = t_e;

	/* This shouldn't fail (verified above) */
	if (copy_to_user(user_status, status, sizeof(int) * count)) {
		ret = -EFAULT;
		goto dealloc_out;
	}

	ret = 0;

dealloc_out:
	kfree(virt_addr);
	kfree(nr_pages);
	kfree(nodes);
	kfree(status);
	kfree(ptep);
	kfree(dst_phys);

out:
	return ret;
}

extern int do_process_vm_read_writev(int pid,
	const struct iovec *local_iov,
	unsigned long liovcnt,
	const struct iovec *remote_iov,
	unsigned long riovcnt,
	unsigned long flags,
	int op);

SYSCALL_DECLARE(process_vm_writev)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	const struct iovec *local_iov = 
		(const struct iovec *)ihk_mc_syscall_arg1(ctx);
	unsigned long liovcnt = ihk_mc_syscall_arg2(ctx);
	const struct iovec *remote_iov = 
		(const struct iovec *)ihk_mc_syscall_arg3(ctx);
	unsigned long riovcnt = ihk_mc_syscall_arg4(ctx);
	unsigned long flags = ihk_mc_syscall_arg5(ctx);
	int ret;

	ret = process_vm_validate_args(flags, liovcnt, riovcnt);
	if (ret) {
		return ret;
	}
	return do_process_vm_read_writev(pid, local_iov, liovcnt,
		remote_iov, riovcnt, flags, PROCESS_VM_WRITE);
}

SYSCALL_DECLARE(process_vm_readv)
{
	int pid = ihk_mc_syscall_arg0(ctx);
	const struct iovec *local_iov = 
		(const struct iovec *)ihk_mc_syscall_arg1(ctx);
	unsigned long liovcnt = ihk_mc_syscall_arg2(ctx);
	const struct iovec *remote_iov = 
		(const struct iovec *)ihk_mc_syscall_arg3(ctx);
	unsigned long riovcnt = ihk_mc_syscall_arg4(ctx);
	unsigned long flags = ihk_mc_syscall_arg5(ctx);
	int ret;

	ret = process_vm_validate_args(flags, liovcnt, riovcnt);
	if (ret) {
		return ret;
	}
	return do_process_vm_read_writev(pid, local_iov, liovcnt,
		remote_iov, riovcnt, flags, PROCESS_VM_READ);
}

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

SYSCALL_DECLARE(mod_call) {
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
	struct thread *thread = cpu_local_var(current);
	struct kuti_attr {
		long parent_cpuid;
		struct uti_attr attr;
	} kattr;

	thread->uti_state = UTI_STATE_PROLOGUE;

	rctx = kmalloc(sizeof(struct uti_ctx), IHK_MC_AP_NOWAIT);
	if (!rctx) {
		rc = -ENOMEM;
		goto out;
	}
	rp_rctx = virt_to_phys((void *)rctx);
	save_uctx((void *)rctx->ctx, NULL);

	/* Create a information for Linux thread */
	uti_info = kmalloc(sizeof(struct uti_info), IHK_MC_AP_NOWAIT);
	if (!uti_info) {
		rc = -ENOMEM;
		goto out;
	}
	/* clv info */
	uti_info->thread_va = (unsigned long)cpu_local_var(current);
	uti_info->uti_futex_resp_pa = virt_to_phys((void *)cpu_local_var(uti_futex_resp));
	uti_info->ikc2linux_pa = virt_to_phys((void *)cpu_local_var(ikc2linux));

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
	
	kfree(rctx);
	rctx = NULL;

	kfree(uti_info);
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
	} else if (rc == -ERESTARTSYS) { 
		/* tracer is not working and /dev/mcosX has detected exit of mcexec process */
		kprintf("%s: release_handler,pid=%d,tid=%d,rc=%lx\n", __FUNCTION__, thread->proc->pid, thread->tid, rc);
		thread->proc->nohost = 1;
		do_exit(rc);
	} else {
		kprintf("%s: ERROR: do_syscall() failed (%ld)\n", __FUNCTION__, rc);
	}

 out:
	kfree(rctx);
	kfree(uti_info);

	return rc;
}

void
utilthr_migrate()
{
	struct thread *thread = cpu_local_var(current);

	/* Don't inherit mod_clone */
	if (thread->mod_clone == SPAWNING_TO_REMOTE) {
		thread->mod_clone = SPAWN_TO_LOCAL;
		util_thread(thread->mod_clone_arg);
	}
}

SYSCALL_DECLARE(util_migrate_inter_kernel)
{
	struct uti_attr *arg = (void *)ihk_mc_syscall_arg0(ctx);
	struct uti_attr kattr;

	if (arg) {
		if (copy_from_user(&kattr, arg, sizeof(struct uti_attr))) {
			return -EFAULT;
		}
	}

	return util_thread(arg? &kattr: NULL);
}

SYSCALL_DECLARE(util_indicate_clone)
{
	int mod = (int)ihk_mc_syscall_arg0(ctx);
	struct uti_attr *arg = (void *)ihk_mc_syscall_arg1(ctx);
	struct thread *thread = cpu_local_var(current);
	struct uti_attr *kattr = NULL;

	if (!thread->proc->enable_uti) {
		kprintf("%s: error: --enable-uti mcexec option not specified\n",
			__func__);
		return -EINVAL;
	}

	if (mod != SPAWN_TO_LOCAL &&
	    mod != SPAWN_TO_REMOTE)
		return -EINVAL;
	if (arg) {
		if (!(kattr = kmalloc(sizeof(struct uti_attr), IHK_MC_AP_NOWAIT))) {
			kprintf("%s: error: allocating kattr\n", __func__);
			return -ENOMEM;
		}

		if (copy_from_user(kattr, arg, sizeof(struct uti_attr))) {
			kfree(kattr);
			return -EFAULT;
		}
	}
	thread->mod_clone = mod;
	if (thread->mod_clone_arg) {
		kfree(thread->mod_clone_arg);
		thread->mod_clone_arg = NULL;
	}
	if (kattr) {
		thread->mod_clone_arg = kattr;
	}
	return 0;
}

SYSCALL_DECLARE(get_system)
{
	return 0;
}

/*
 * swapoout(const char *filename, void *workarea, size_t size)
 */
SYSCALL_DECLARE(swapout)
{
	extern int do_pageout(const char*, void*, size_t, int);
	extern int do_pagein(int);
	char	*fname = (char *)ihk_mc_syscall_arg0(ctx);
	char	*buf = (char *)ihk_mc_syscall_arg1(ctx);
	size_t	size = (size_t)ihk_mc_syscall_arg2(ctx);
	int	flag = (int)ihk_mc_syscall_arg3(ctx);
	ihk_mc_user_context_t ctx0;
	int	cc;

	dkprintf("[%d]swapout(%lx,%lx,%lx,%ld)\n",
		 ihk_mc_get_processor_id(), fname, buf, size, flag);

	if (fname == NULL || flag == 0x01) { /* for development purupse */
		kprintf("swapout: skipping real swap\n");
		cc = syscall_generic_forwarding(__NR_swapout, &ctx0);
		kprintf("swapout: return from Linux\n");
		return cc;
	}
	/* pageout */
	cc = do_pageout(fname, buf, size, flag);
	if (cc < 0) return cc;
	if (flag == 0x02) {
		kprintf("swapout: skipping calling swapout in Linux\n");
	} else {
		kprintf("swapout: before calling swapout in Linux\n");
		cc = syscall_generic_forwarding(__NR_swapout, &ctx0);
		kprintf("swapout: after calling swapout in Linux cc(%d)\n", cc);
	}
	/* Though swapout in Linux side returns error, needs to call
	 * pagein to recover the image */
	cc = do_pagein(flag);
	kprintf("swapout: after calling do_pagein cc(%d)\n", cc);
	return cc;
}

SYSCALL_DECLARE(linux_mlock)
{
	ihk_mc_user_context_t ctx0;
	const uintptr_t addr = ihk_mc_syscall_arg0(ctx);
	const size_t len = ihk_mc_syscall_arg1(ctx);
	int		cc;

	kprintf("linux_mlock: %p %ld\n", (void*) addr, len);
	ihk_mc_syscall_arg0(&ctx0) = addr;
	ihk_mc_syscall_arg1(&ctx0) = len;
	cc = syscall_generic_forwarding(802, &ctx0);
	return cc;
}

SYSCALL_DECLARE(linux_spawn)
{
	int rc;

	rc = syscall_generic_forwarding(__NR_linux_spawn, ctx);
	return rc;
}

SYSCALL_DECLARE(suspend_threads)
{
	struct thread *mythread = cpu_local_var(current);
	struct thread *thread;
	struct process *proc = mythread->proc;

	list_for_each_entry(thread, &proc->threads_list, siblings_list) {
		if (thread == mythread)
			continue;
		do_kill(mythread, proc->pid, thread->tid, SIGSTOP, NULL, 0);
	}
	list_for_each_entry(thread, &proc->threads_list, siblings_list) {
		if (thread == mythread)
			continue;
		while (thread->status != PS_STOPPED)
			cpu_pause();
	}
	return 0;
}

SYSCALL_DECLARE(resume_threads)
{
	struct thread *mythread = cpu_local_var(current);
	struct thread *thread;
	struct process *proc = mythread->proc;

	list_for_each_entry(thread, &proc->threads_list, siblings_list) {
		if (thread == mythread)
			continue;
		do_kill(mythread, proc->pid, thread->tid, SIGCONT, NULL, 0);
	}
	return 0;
}

SYSCALL_DECLARE(util_register_desc)
{
	struct thread *thread = cpu_local_var(current);
	uti_desc = ihk_mc_syscall_arg0(ctx);
	dkprintf("%s: tid=%d,uti_desc=%lx\n", __FUNCTION__, thread->tid, uti_desc);
	return 0;
}

void
reset_cputime()
{
	struct thread *thread;

	if(clv == NULL)
		return;

	if(!(thread = cpu_local_var(current)))
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

#ifdef DISABLE_SCHED_YIELD
	if (num != __NR_sched_yield)
#endif // DISABLE_SCHED_YIELD
		set_cputime(CPUTIME_MODE_U2K);

	if (pid != mcexec_v10_syscall_entry_pid) {
		mcexec_v10_syscall_entry_pid = pid;
		mcexec_v10_syscall_entry_logs = 0;
	}
	if (mcexec_v10_syscall_entry_logs < 128) {
		kprintf("mcexec_v10: syscall entry cpu=%d pid=%d tid=%d nr=%d rip=0x%lx sp=0x%lx status=%d\n",
			ihk_mc_get_processor_id(),
			pid,
			thread ? thread->tid : -1,
			num,
			ctx ? ihk_mc_syscall_pc(ctx) : 0UL,
			ctx ? ihk_mc_syscall_sp(ctx) : 0UL,
			thread ? thread->status : -1);
		mcexec_v10_syscall_entry_logs++;
	}

//kprintf("syscall=%d\n", num);
#ifdef PROFILE_ENABLE
	if (thread->profile && thread->profile_start_ts) {
		unsigned long ts = rdtsc();
		thread->profile_elapsed_ts += (ts - thread->profile_start_ts);
		thread->profile_start_ts = ts;
	}
#endif // PROFILE_ENABLE

	if(cpu_local_var(current)->proc->status == PS_EXITED &&
	   (num != __NR_exit && num != __NR_exit_group)){
		/* x86_64: Setting -EINVAL to rax is done in the
		 * following return.
		 */
		save_syscall_return_value(num, -EINVAL);
		check_signal(-EINVAL, NULL, -1);
		set_cputime(CPUTIME_MODE_K2U);
		return -EINVAL;
	}

	cpu_enable_interrupt();

	if (cpu_local_var(current)->ptrace) {
		arch_ptrace_syscall_event(cpu_local_var(current),
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

	if ((0 <= num) && (num < (sizeof(syscall_table) / sizeof(syscall_table[0])))
			&& (syscall_table[num] != NULL)) {
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

	if (pid != mcexec_v10_syscall_return_pid) {
		mcexec_v10_syscall_return_pid = pid;
		mcexec_v10_syscall_return_logs = 0;
	}
	if (mcexec_v10_syscall_return_logs < 128) {
		kprintf("mcexec_v10: syscall return cpu=%d pid=%d tid=%d nr=%d ret=0x%lx ret_signed=%ld rip=0x%lx sp=0x%lx\n",
			ihk_mc_get_processor_id(),
			pid,
			thread ? thread->tid : -1,
			num, l, l,
			ctx ? ihk_mc_syscall_pc(ctx) : 0UL,
			ctx ? ihk_mc_syscall_sp(ctx) : 0UL);
		mcexec_v10_syscall_return_logs++;
	}

	/* Store return value so that PTRACE_GETREGSET will see it */
	save_syscall_return_value(num, l);

	if (cpu_local_var(current)->ptrace) {
		/* arm64: The return value modified by the tracer is
		 * stored to x0 in the following check_signal().
		 */
		l = arch_ptrace_syscall_event(cpu_local_var(current), ctx, l);
	}

#ifdef PROFILE_ENABLE
	{
		unsigned long ts = rdtsc();

		/*
		 * futex_wait() and schedule() will internally reset
		 * thread->profile_start_ts so that actual wait time
		 * is not accounted for.
		 */
		if (num < PROFILE_SYSCALL_MAX) {
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
			smp_load_acquire(&v->flags) & CPU_FLAG_NEED_RESCHED)
#else
	if (smp_load_acquire(&v->flags) & CPU_FLAG_NEED_RESCHED)
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

	thread = cpu_local_var(current);
	if (thread == NULL || thread == &cpu_local_var(idle)) {
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

		list_for_each_entry_safe(pending, next, head, list) {
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

		list_for_each_entry_safe(pending, next, head, list) {
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
	thread = cpu_local_var(current);

	if (thread == NULL || thread->proc->pid == 0) {
		struct thread *t;

		irqstate = cpu_disable_interrupt_save();
		ihk_mc_spinlock_lock_noirq(&(cpu_local_var(runq_lock)));
		list_for_each_entry(t, &(cpu_local_var(runq)), sched_list) {
			if (t->proc->pid <= 0) {
				continue;
			}
			if (t->status == PS_INTERRUPTIBLE &&
			   hassigpending(t)) {
				t->status = PS_RUNNING;
				break;
			}
		}
		ihk_mc_spinlock_unlock_noirq(&(cpu_local_var(runq_lock)));
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
