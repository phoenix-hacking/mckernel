/* mcexec.c COPYRIGHT FUJITSU LIMITED 2015-2018 */
/**
 * \file executer/user/mcexec.c
 *  License details are found in the file LICENSE.
 * \brief
 *  ....
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2011 - 2012  Taku Shimosawa
 * \author Balazs Gerofi  <bgerofi@riken.jp> \par
 *      Copyright (C) 2012  RIKEN AICS
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 *      Copyright (C) 2012 - 2013 Hitachi, Ltd.
 * \author Tomoki Shirasawa  <tomoki.shirasawa.kk@hitachi-solutions.com> \par
 *      Copyright (C) 2012 - 2013 Hitachi, Ltd.
 * \author Balazs Gerofi  <bgerofi@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2013  The University of Tokyo
 */
/*
 * HISTORY:
 *  2013/11/07 hamada added <sys/resource.h> which is required by getrlimit(2)
 *  2013/10/21 nakamura exclude interpreter's segment from data region
 *  2013/10/11 nakamura mcexec: add a upper limit of the stack size
 *  2013/10/11 nakamura mcexec: add a path prefix for interpreter search
 *  2013/10/11 nakamura mcexec: add a interpreter invocation
 *  2013/10/08 nakamura add a AT_ENTRY entry to the auxiliary vector
 *  2013/09/02 shirasawa add terminate thread
 *  2013/08/19 shirasawa mcexec forward signal to MIC process
 *  2013/08/07 nakamura add page fault forwarding
 *  2013/07/26 shirasawa mcexec print signum or exit status
 *  2013/07/17 nakamura create more mcexec thread so that all cpu to be serviced
 *  2013/04/17 nakamura add generic system call forwarding
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <elf.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <ctype.h>
#include <sys/mman.h>
#include <asm/unistd.h>
#include <sched.h>
#include <dirent.h>

#include <termios.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/resource.h>
#include <sys/utsname.h>
#include <sys/fsuid.h>
#include <time.h>
#include <sys/time.h>
#include <signal.h>
#include <sys/wait.h>
#include <dirent.h>
#include <sys/syscall.h>
#include <sys/ptrace.h>
#include <pthread.h>
#include <semaphore.h>
#include <signal.h>
#include <sys/signalfd.h>
#include <sys/mount.h>
#include <include/generated/uapi/linux/version.h>
#ifndef __aarch64__
#include <sys/user.h>
#endif /* !__aarch64__ */
#include <sys/prctl.h>
#include "../../config.h"
#include "../include/uprotocol.h"
#include <ihk/ihk_host_user.h>
#include "../include/uti.h"
#include <getopt.h>
#include "archdep.h"
#include "arch_args.h"
#include <numa.h>
#include <numaif.h>
#include <spawn.h>
#include <sys/personality.h>
#include <sys/socket.h>
#include <sys/un.h>
#include "../include/pmi.h"
#include "../include/qlmpi.h"
#include <sys/xattr.h>
#include "../include/defs.h"
#include "../../lib/include/list.h"
#include "../../lib/include/bitops-set_bit.h"
#include "../../lib/include/bitops-clear_bit.h"
#include "../../lib/include/bitops-test_bit.h"

//#define DEBUG
#define ADD_ENVS_OPTION

#ifdef DEBUG
static int debug = 1;
#else
static int debug;
#endif

#define __dprintf(format, args...) do {                  \
	if (debug) {                                     \
		printf("%s: " format, __func__, ##args); \
		fflush(stdout);                          \
	}                                                \
} while (0)
#define __eprintf(format, args...) do {                   \
	fprintf(stderr, "%s: " format, __func__, ##args); \
	fflush(stderr);                                   \
} while (0)

#define CHKANDJUMPF(cond, err, format, ...)             \
	do {                                            \
		if (cond) {                             \
			__eprintf(format, __VA_ARGS__); \
			ret = err;                      \
			goto fn_fail;                   \
		}                                       \
	} while(0)

#define CHKANDJUMP(cond, err, msg)      \
	do {                            \
		if (cond) {             \
			__eprintf(msg); \
			ret = err;      \
			goto fn_fail;   \
		}                       \
	} while(0)


#undef DEBUG_UTI

#ifdef USE_SYSCALL_MOD_CALL
extern int mc_cmd_server_init();
extern void mc_cmd_server_exit();
extern void mc_cmd_handle(int fd, int cpu, unsigned long args[6]);

#ifdef CMD_DCFA
extern void ibmic_cmd_server_exit();
extern int ibmic_cmd_server_init();
#endif

#ifdef CMD_DCFAMPI
extern void dcfampi_cmd_server_exit();
extern int dcfampi_cmd_server_init();
#endif

int __glob_argc = -1;
char **__glob_argv = 0;
#endif

typedef unsigned char   cc_t;
typedef unsigned int    speed_t;
typedef unsigned int    tcflag_t;

struct sigfd {
	struct sigfd *next;
	int sigpipe[2];
};

struct sigfd *sigfdtop;

#ifdef NCCS
#undef NCCS
#endif

#define NCCS 19
struct kernel_termios {
	tcflag_t c_iflag;               /* input mode flags */
        tcflag_t c_oflag;               /* output mode flags */
	tcflag_t c_cflag;               /* control mode flags */
	tcflag_t c_lflag;               /* local mode flags */
	cc_t c_line;                    /* line discipline */
	cc_t c_cc[NCCS];                /* control characters */
};

struct thread_data_s;
int main_loop(struct thread_data_s *);

#ifndef MCEXEC_RUST_HELPERS
int get_syscall_args(int pid, syscall_args *args)
{
	return ptrace(PTRACE_GETREGS, pid, NULL, args);
}

int set_syscall_args(int pid, syscall_args *args)
{
	return ptrace(PTRACE_SETREGS, pid, NULL, args);
}

unsigned long get_syscall_number(syscall_args *args)
{
	return args->orig_rax;
}

unsigned long get_syscall_return(syscall_args *args)
{
	return args->rax;
}

unsigned long get_syscall_arg1(syscall_args *args)
{
	return args->rdi;
}

unsigned long get_syscall_arg2(syscall_args *args)
{
	return args->rsi;
}

unsigned long get_syscall_arg3(syscall_args *args)
{
	return args->rdx;
}

unsigned long get_syscall_arg4(syscall_args *args)
{
	return args->r10;
}

unsigned long get_syscall_arg5(syscall_args *args)
{
	return args->r8;
}

unsigned long get_syscall_arg6(syscall_args *args)
{
	return args->r9;
}

unsigned long get_syscall_rip(syscall_args *args)
{
	return args->rip;
}

void set_syscall_number(syscall_args *args, unsigned long value)
{
	args->orig_rax = value;
}

void set_syscall_return(syscall_args *args, unsigned long value)
{
	args->rax = value;
}

void set_syscall_arg1(syscall_args *args, unsigned long value)
{
	args->rdi = value;
}

void set_syscall_arg2(syscall_args *args, unsigned long value)
{
	args->rsi = value;
}

void set_syscall_arg3(syscall_args *args, unsigned long value)
{
	args->rdx = value;
}

void set_syscall_arg4(syscall_args *args, unsigned long value)
{
	args->r10 = value;
}

void set_syscall_arg5(syscall_args *args, unsigned long value)
{
	args->r8 = value;
}

void set_syscall_arg6(syscall_args *args, unsigned long value)
{
	args->r9 = value;
}

int syscall_enter(syscall_args *args)
{
	return get_syscall_return(args) == (unsigned long)-ENOSYS;
}

void set_bit(int nr, volatile unsigned long *addr)
{
	volatile unsigned int *p = (volatile unsigned int *)addr + (nr >> 5);
	unsigned int mask = 1U << (nr & 31);

	__sync_fetch_and_or((unsigned int *)p, mask);
}

void clear_bit(int nr, volatile unsigned long *addr)
{
	volatile unsigned int *p = (volatile unsigned int *)addr + (nr >> 5);
	unsigned int mask = 1U << (nr & 31);

	__sync_fetch_and_and((unsigned int *)p, ~mask);
}

int test_bit(int nr, const void *addr)
{
	const unsigned int *p = (const unsigned int *)addr;

	return ((1U << (nr & 31)) & p[nr >> 5]) != 0;
}
#endif

static int mcosid;
int fd;
static char *exec_path = NULL;
static char *altroot;
static const char rlimit_stack_envname[] = "MCKERNEL_RLIMIT_STACK";
static const char ld_preload_envname[] = "MCKERNEL_LD_PRELOAD";
static int ischild;
static int enable_vdso = 1;
static int mpol_no_heap = 0;
static int mpol_no_stack = 0;
static int mpol_no_bss = 0;
static int mpol_shm_premap = 0;
static int no_bind_ikc_map = 0;
static int straight_map = 0;
static unsigned long straight_map_threshold = (1024*1024);
static unsigned long mpol_threshold = 0;
static unsigned long heap_extension = -1;
static int profile = 0;
static int disable_sched_yield = 0;
static long stack_premap = (2ULL << 20);
static long stack_max = -1;
static struct rlimit rlim_stack;
static char *mpol_bind_nodes = NULL;
static int uti_thread_rank = 0;
static int uti_use_last_cpu = 0;
static int enable_uti = 0;
#ifdef ENABLE_TOFU
static int enable_tofu = 0;
#endif
static unsigned long mcexec_flags = 0;

/* Partitioned execution (e.g., for MPI) */
static int nr_processes = 0;
static int nr_threads = -1;

#ifdef MCEXEC_RUST_HELPERS
extern unsigned long mcexec_atobytes_result(const char *string);
extern void mcexec_parse_stack_arg_result(const char *string,
		long *stack_premap, long *stack_max);
extern int mcexec_apply_option_result(int opt, const char *optarg,
		int *target_core, int *nr_processes, int *nr_threads,
		unsigned long *mpol_threshold, unsigned long *heap_extension,
		unsigned long *straight_map_threshold, long *stack_premap,
		long *stack_max, int *uti_thread_rank,
		unsigned long *mcexec_flags);
extern unsigned long mcexec_default_heap_extension_result(
		unsigned long heap_extension, unsigned long page_size);
extern int mcexec_default_thread_count_result(int nr_threads,
		int omp_present, int omp_threads, int nr_processes, int ncpu);
extern int mcexec_plan_process_threads_result(int *nr_processes,
		int nr_threads, int ncpu, int *planned_threads);
extern unsigned long mcexec_mpol_flags_result(int no_heap, int no_stack,
		int no_bss, int shm_premap);
extern int mcexec_ompi_mpol_policy_result(const char *mpol,
		int mpol_default, int mpol_interleave, int mpol_bind,
		int mpol_preferred, int *mode, int *nodemask_action);
extern void mcexec_apply_stack_max_result(long stack_max,
		rlim_t *rlim_cur, rlim_t *rlim_max);
extern int mcexec_parse_int_base0_full_result(const char *string,
		int require_positive, int *result);
extern int mcexec_atoi_result(const char *string);
extern unsigned long mcexec_strtoul_hex_result(const char *string);
extern int mcexec_parse_optional_mcosid_result(const char *string,
		int *result);
extern int mcexec_post_options_plan_result(int optind, int argc,
		const char *candidate, unsigned long heap_extension,
		unsigned long page_size, int current_mcosid,
		unsigned long *planned_heap_extension, int *planned_mcosid,
		int *planned_optind);
extern int mcexec_usage_line_result(char *buf, size_t size, const char *prog,
		int add_envs_option);
extern int mcexec_env_list_count_result(const void *head);
extern void *mcexec_search_env_list_result(void *head, const char *name);
extern int mcexec_add_env_list_result(void *headp, char *add_string);
extern void mcexec_add_env_list_body(void *headp, char *add_string);
extern void mcexec_destroy_env_list_result(void *head);
extern char **mcexec_create_local_environ_result(void *inc_list);
extern void mcexec_destroy_local_environ_result(char **local_env);
extern char *mcexec_shift_flib_affinity_result(const char *affinity,
		int shift);
extern int mcexec_parse_rlimit_stack_env_result(const char *env,
		rlim_t *cur, rlim_t *max);
extern void mcexec_apply_saved_stack_limit_result(rlim_t saved_cur,
		rlim_t saved_max, rlim_t *rlim_cur, rlim_t *rlim_max);
extern unsigned short mcexec_dirent32_reclen_result(const void *dirp);
extern char *mcexec_dirent32_name_result(void *dirp);
extern void *mcexec_dirent32_off_result(void *dirp);
extern unsigned short mcexec_dirent64_reclen_result(const void *dirp);
extern char *mcexec_dirent64_name_result(void *dirp);
extern void *mcexec_dirent64_off_result(void *dirp);
extern int mcexec_is_proc_task_leaf_path_result(const char *path);
extern int mcexec_path_is_absolute_result(const char *path);
extern int mcexec_path_is_single_component_exec_result(const char *path);
extern int mcexec_path_len_less_than_result(const char *path, size_t limit);
extern int mcexec_copy_path_result(const char *path, char *out, size_t size);
extern int mcexec_join_path_result(const char *prefix, const char *path,
		char *out, size_t size);
extern int lookup_exec_path(char *filename, char *path, int max_len,
		int execvp);
extern int load_elf_desc_shebang(char *shebang_argv0,
		struct program_load_desc **desc_p, char ***shebang_argv_p,
		int execvp);
char *search_file(char *orgpath, int mode);
extern int mcexec_objdump_rpath_cmd_result(const char *path, char *out,
		size_t size);
extern ssize_t mcexec_find_libdir_body(char *libdir, size_t len);
extern int mcexec_getpath_execveat_prepare_result(int dirfd,
		const char *filename, int flags, int at_fdcwd,
		int at_empty_path, int at_symlink_nofollow,
		char *pathbuf, size_t size, int *check_symlink);
extern int mcexec_build_ld_preload_result(const char *libdir,
		const char *existing, int enable_uti,
		int disable_sched_yield, int enable_qlmpi,
		char *out, size_t size);
extern void mcexec_ld_preload_init_body(void);
extern int mcexec_overlay_addfd_prepare_result(const char *path,
		int mcosid, char *linux_path, size_t linux_size,
		char *mck_path, size_t mck_size, size_t *pathlen);
extern int mcexec_mcos_device_path_result(char *out, size_t size,
		int mcosid);
extern int mcexec_proc_self_fd_path_result(char *out, size_t size,
		int dirfd);
extern int mcexec_join_path_inplace_result(char *path, size_t size,
		const char *leaf);
extern int mcexec_path_is_dev_xpmem_result(const char *path);
extern int mcexec_path_has_libuti_result(const char *path);
extern int mcexec_overlay_uti_path_result(const char *libdir,
		const char *path, char *out, size_t size);
extern int mcexec_overlay_proc_self_path_result(const char *path,
		int mcosid, int pid, char *out, size_t size);
extern int mcexec_overlay_proc_path_result(const char *path, int mcosid,
		char *out, size_t size);
extern int mcexec_overlay_sys_path_result(const char *path, int mcosid,
		char *out, size_t size, size_t *mapped_offset);
extern int mcexec_normalize_overlay_path_result(char *path, size_t *len);
extern const char *overlay_path(int dirfd, const char *in, char *buf,
		int *resolvelinks);
extern int mcexec_parse_proc_task_ids_result(const char *path,
		int current_pid, int *pid, int *tid);
extern int mcexec_proc_task_check_path_result(char *out, size_t size,
		int mcosid, int pid, int tid);
extern int mcexec_flatten_strings_result(char *pre_strings, char **strings,
		char **flat);
extern int mcexec_shebang_argv_extend_result(char ***shebang_argv_p,
		char *shebang);
extern int mcexec_execve1_transfer_buffer_result(const void *desc,
		size_t desc_size, const void *args, size_t args_len,
		char **buffer_out, size_t *size_out);
extern int mcexec_syscall_should_log_result(long number,
		unsigned long arg0, long nr_write);
extern long mcexec_errno_return_result(long ret, int errno_value);
extern long mcexec_path_copy_return_result(long copy_ret,
		unsigned long limit);
extern long mcexec_close_plan_result(unsigned long remote_fd, int mcos_fd);
extern int mcexec_setfsuid_needs_cred_result(unsigned long mode);
extern long mcexec_sched_setaffinity_action_result(unsigned long pid_arg);
extern void mcexec_exit_status_plan_result(long number,
		unsigned long status, long nr_exit_group, int is_child,
		int is_tty, int *sig, int *term, int *report_sig,
		int *report_status);
extern int mcexec_collect_active_tids_result(const void *head, int *tids,
		size_t count);
extern int mcexec_fork_sync_complete_result(void *top, int pid,
		void **fs_out, void **node_out);
extern int mcexec_fork_sync_remove_node_result(void *top, void *target);
extern int mcexec_dirent_rewrite_offsets_result(void *dirents, size_t start,
		size_t end, size_t base, int is64);
extern int mcexec_copy_dirents_result(void *dst, const void *dirents,
		size_t dirents_size, size_t offset, unsigned int *count,
		int is64);
extern int mcexec_dirent_buffer_contains_name_result(const void *dirents,
		size_t dirents_size, const void *entry, int is64);
int flatten_strings(char *pre_strings, char **strings, char **flat);
int copy_dirents(void *_dirp, void *dirents, size_t dirents_size,
		off_t offset, unsigned int *count, int sysnum);
int overlay_getdents(int sysnum, int fd, void *_dirp, unsigned int count);
void print_usage(char **argv);
void print_desc(struct program_load_desc *desc);
void print_flat(char *flat);
unsigned long atobytes(char *string);
pid_t gettid(void);
int tgkill(int tgid, int tid, int sig);
void do_syscall_return(int fd, int cpu, long ret, int n,
		unsigned long src, unsigned long dest, unsigned long sz);
void do_syscall_load(int fd, int cpu, unsigned long dest, unsigned long src,
		unsigned long sz);
long do_strncpy_from_user(int fd, void *dest, void *src, unsigned long n);
int close_cloexec_fds(int mcos_fd);
void init_sigaction(void);
void sendsig(int sig, siginfo_t *siginfo, void *context);
int init_worker_threads(int fd);
void overlay_addfd(int fd, const char *path);
void overlay_delfd(int fd);
int overlay_blacklist(const char *path);
long act_signalfd4(struct syscall_wait_desc *w);
void act_sigaction(struct syscall_wait_desc *w);
void act_sigprocmask(struct syscall_wait_desc *w);
void act_signalfd4_syscall(struct syscall_wait_desc *w, int fd, int cpu);
void act_rt_sigaction(struct syscall_wait_desc *w, int fd, int cpu);
void act_rt_sigprocmask(struct syscall_wait_desc *w, int fd, int cpu);
void act_setfsuid(struct syscall_wait_desc *w, int fd, int cpu);
void act_setresuid(struct syscall_wait_desc *w, int fd, int cpu);
void act_setreuid(struct syscall_wait_desc *w, int fd, int cpu);
void act_setuid(struct syscall_wait_desc *w, int fd, int cpu);
void act_setresgid(struct syscall_wait_desc *w, int fd, int cpu);
void act_setregid(struct syscall_wait_desc *w, int fd, int cpu);
void act_setgid(struct syscall_wait_desc *w, int fd, int cpu);
void act_setfsgid(struct syscall_wait_desc *w, int fd, int cpu);
void act_close(struct syscall_wait_desc *w, int fd, int cpu);
void act_generic_syscall(struct syscall_wait_desc *w, int fd, int cpu);
void act_sched_setaffinity(struct syscall_wait_desc *w, int fd, int cpu,
		struct thread_data_s *my_thread);
void act_getdents(struct syscall_wait_desc *w, int fd, int cpu);
void act_perf_event_open(struct syscall_wait_desc *w, int fd, int cpu);
void act_futex_clock(struct syscall_wait_desc *w, int fd, int cpu);
void act_kill(struct syscall_wait_desc *w, int fd, int cpu,
		struct thread_data_s *my_thread);
void act_wait4(struct syscall_wait_desc *w, int fd, int cpu);
void act_gettid(struct syscall_wait_desc *w, int fd, int cpu);
void act_debug_mlock(struct syscall_wait_desc *w, int fd, int cpu);
void act_swapout_unavailable(struct syscall_wait_desc *w, int fd, int cpu);
void act_linux_spawn(struct syscall_wait_desc *w, int fd, int cpu);
void act_clone_complete(struct syscall_wait_desc *w, int fd, int cpu);
int act_clone_start(struct syscall_wait_desc *w, int fd, int cpu,
		long *main_loop_ret);
void act_exit(struct syscall_wait_desc *w, int cpu, int is_child);
void act_execve_phase1(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf);
long act_execve_phase2(struct syscall_wait_desc *w, int fd, int cpu);
int act_execve(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf, long *main_loop_ret);
void act_reserved_memory_syscall(struct syscall_wait_desc *w, int fd, int cpu);
void act_readlinkat(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf, char *tmpbuf);
void act_openat(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf, char *tmpbuf);
void act_open(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf, char *tmpbuf);
void act_readlink(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf, char *tmpbuf);
void act_newfstatat(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf, char *tmpbuf);
void act_stat(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf, char *tmpbuf);
void act_faccessat(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf, char *tmpbuf);
void act_access(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf, char *tmpbuf);
void act_getxattr(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf, char *tmpbuf);
void act_lgetxattr(struct syscall_wait_desc *w, int fd, int cpu,
		char *pathbuf, char *tmpbuf);
int act_main_loop_syscall(struct syscall_wait_desc *w, int fd, int cpu,
		struct thread_data_s *my_thread, char *pathbuf, char *tmpbuf,
		long *main_loop_ret, int is_child);
int act_main_loop_iteration(struct syscall_wait_desc *w, int fd,
		struct thread_data_s *my_thread, char *pathbuf, char *tmpbuf,
		long *main_loop_ret, int is_child);
int act_main_loop_body(struct thread_data_s *my_thread, int fd, int is_child);
void *mcexec_main_loop_thread_func_body(void *arg);
int mcexec_create_worker_thread_body(struct thread_data_s **tp_out,
		void *init_ready);
void mcexec_join_all_threads_body(void);
void mcexec_kill_thread_body(unsigned long tid, unsigned long sig,
		struct thread_data_s *my_thread);
long mcexec_do_generic_syscall_body(struct syscall_wait_desc *w);
long mcexec_util_thread_body(struct thread_data_s *my_thread,
		unsigned long rp_rctx, int remote_tid, unsigned long pattr,
		unsigned long uti_info, unsigned long uti_desc_arg);
int mcexec_get_thp_disable_body(void);
void mcexec_numa_local_body(unsigned long *localset,
		unsigned long *nodemask, int nonlocal);
void mcexec_numa_all_body(unsigned long *nodemask);
void *mcexec_numa_node_set_body(int n, void *numa_nodes,
		size_t cpu_set_size);
int mcexec_opendev_body(void);
int mcexec_reduce_stack_body(unsigned long orig_cur, unsigned long orig_max,
		char **argv);
int mcexec_getpath_execveat_body(int dirfd, const char *filename, int flags,
		char *pathbuf, size_t size);
void mcexec_overlay_list_add_body(struct list_head *new, struct list_head *head);
void mcexec_overlay_list_del_body(struct list_head *entry);
int mcexec_mapped_proc_task_parent_exists_body(const char *mapped);
int mcexec_dirent_is64_body(int sysnum, int getdents64);
void mcexec_setup_dma_ppd_body(void);
int mcexec_finish_main_image_body(struct program_load_desc *desc);
void mcexec_apply_flib_affinity_body(void);
int mcexec_apply_main_stack_body(struct program_load_desc *desc,
		const char *env, long stack_max, long stack_premap,
		rlim_t *rlim_cur, rlim_t *rlim_max);
int mcexec_setup_cpu_topology_body(void);
int mcexec_apply_partitioned_cpu_body(struct program_load_desc *desc,
		int nr_processes, int *target_core, int no_bind_ikc_map);
void mcexec_apply_desc_runtime_body(struct program_load_desc *desc,
		int profile, int nr_processes, int mpol_no_heap,
		int mpol_no_stack, int mpol_no_bss, int mpol_shm_premap,
		unsigned long mpol_threshold, unsigned long heap_extension,
		const char *mpol_bind_nodes, int mpol_default,
		int mpol_interleave, int mpol_bind, int mpol_preferred,
		int pld_mpol_max, int enable_uti, int uti_thread_rank,
		int uti_use_last_cpu, int straight_map,
		unsigned long straight_map_threshold, int enable_tofu,
		unsigned long mcexec_flags);
void mcexec_prepare_main_desc_body(struct program_load_desc *desc,
		char **argv_tail, char **shebang_argv, int envs_len,
		char *envs, int target_core, int enable_vdso_arg);
void mcexec_collect_main_envs_body(void *extra_env_headp, int *envs_len,
		char **envs);
void mcexec_collect_default_envs_body(int *envs_len, char **envs);
void mcexec_init_page_altroot_body(void);
int mcexec_init_stack_limit_body(char **argv);
int mcexec_post_option_setup_body(int new_mcosid, int enable_uti_arg);
int mcexec_load_main_desc_body(char *path,
		struct program_load_desc **desc_p, char ***shebang_argv_p);
#endif

#ifdef MCEXEC_RUST_HELPERS
#define SET_ERR(ret) ret = mcexec_errno_return_result(ret, errno)
#define MCEXEC_PATH_COPY_RET(ret) mcexec_path_copy_return_result(ret, PATH_MAX)
#define MCEXEC_SETFSUID_NEEDS_CRED(mode) \
	mcexec_setfsuid_needs_cred_result(mode)
#define MCEXEC_CLOSE_PLAN(remote_fd, mcos_fd) \
	mcexec_close_plan_result(remote_fd, mcos_fd)
#define MCEXEC_SCHED_SETAFFINITY_ACTION(pid_arg) \
	mcexec_sched_setaffinity_action_result(pid_arg)
#else
#define SET_ERR(ret) if (ret == -1) ret = -errno
#define MCEXEC_PATH_COPY_RET(ret) ((ret) >= PATH_MAX ? -ENAMETOOLONG : (ret))
#define MCEXEC_SETFSUID_NEEDS_CRED(mode) ((mode) == 1)
#define MCEXEC_CLOSE_PLAN(remote_fd, mcos_fd) \
	((remote_fd) == (unsigned long)(mcos_fd) ? -EBADF : 0)
#define MCEXEC_SCHED_SETAFFINITY_ACTION(pid_arg) \
	((pid_arg) == 0 ? 1 : -EINVAL)
#endif

struct fork_sync {
	int status;
	volatile int success;
	sem_t sem;
};

struct fork_sync_container {
	pid_t pid;
	struct fork_sync_container *next;
	struct fork_sync *fs;
};

struct fork_sync_container *fork_sync_top;
pthread_mutex_t fork_sync_mutex = PTHREAD_MUTEX_INITIALIZER;

unsigned long page_size;
unsigned long page_mask;

#ifndef MCEXEC_RUST_HELPERS
pid_t gettid(void)
{
	return syscall(SYS_gettid);
}

int tgkill(int tgid, int tid, int sig)
{
	return syscall(SYS_tgkill, tgid, tid, sig);
}
#endif

#ifdef MCEXEC_RUST_HELPERS
struct program_load_desc *load_elf(FILE *fp, char **interp_pathp);

struct program_load_desc *mcexec_load_alloc_desc_bridge(int nsections)
{
	struct program_load_desc *desc;
	size_t size = sizeof(struct program_load_desc) +
		sizeof(struct program_image_section) * nsections;

	desc = malloc(size);
	if (!desc) {
		return NULL;
	}
	memset(desc, '\0', size);
	desc->magic = PLD_MAGIC;
	desc->num_sections = nsections;
	desc->stack_prot = PROT_READ | PROT_WRITE | PROT_EXEC;
	return desc;
}

void mcexec_load_publish_main_section_bridge(
		struct program_load_desc *desc, int index,
		unsigned long vaddr, unsigned long filesz,
		unsigned long offset, unsigned long len, int prot, void *fp)
{
	desc->sections[index].vaddr = vaddr;
	desc->sections[index].filesz = filesz;
	desc->sections[index].offset = offset;
	desc->sections[index].len = len;
	desc->sections[index].interp = 0;
	desc->sections[index].fp = fp;
	desc->sections[index].prot = prot;
}

int *mcexec_load_cred_bridge(struct program_load_desc *desc)
{
	return desc->cred;
}

long mcexec_load_clk_tck_bridge(void)
{
	return sysconf(_SC_CLK_TCK);
}

void mcexec_load_finalize_desc_bridge(struct program_load_desc *desc,
		int pid, int pgid, int reloc, unsigned long entry,
		unsigned long at_phdr, unsigned long at_phent,
		unsigned long at_phnum, unsigned long at_entry,
		unsigned long at_clktck, int stack_prot)
{
	desc->pid = pid;
	desc->pgid = pgid;
	desc->reloc = reloc;
	desc->entry = entry;
	desc->at_phdr = at_phdr;
	desc->at_phent = at_phent;
	desc->at_phnum = at_phnum;
	desc->at_entry = at_entry;
	desc->at_clktck = at_clktck;
	desc->stack_prot = stack_prot;
}

void mcexec_load_too_large_interp_bridge(void)
{
	__eprintf("too large PT_INTERP segment\n");
}

void mcexec_load_cannot_read_interp_bridge(void)
{
	__eprintf("cannot read PT_INTERP segment\n");
}
#else
struct program_load_desc *load_elf(FILE *fp, char **interp_pathp)
{
	Elf64_Ehdr hdr;
	Elf64_Phdr phdr;
	int i, j, nhdrs = 0;
	struct program_load_desc *desc;
	unsigned long load_addr = 0;
	int load_addr_set = 0;
	unsigned long at_phdr = 0;
	int at_phdr_set = 0;
	static char interp_path[PATH_MAX];
	ssize_t ss;

	*interp_pathp = NULL;

	if (fread(&hdr, sizeof(hdr), 1, fp) < 1) {
		__eprintf("Cannot read Ehdr.\n");
		return NULL;
	}
	if (memcmp(hdr.e_ident, ELFMAG, SELFMAG)) {
		__eprintf("ELFMAG mismatched.\n");
		return NULL;
	}
	fseek(fp, hdr.e_phoff, SEEK_SET);
	for (i = 0; i < hdr.e_phnum; i++) {
		if (fread(&phdr, sizeof(phdr), 1, fp) < 1) {
			__eprintf("Loading phdr failed (%d)\n", i);
			return NULL;
		}
		if (phdr.p_type == PT_LOAD) {
			nhdrs++;
		}
	}
	
	desc = malloc(sizeof(struct program_load_desc)
	              + sizeof(struct program_image_section) * nhdrs);
	memset(desc, '\0', sizeof(struct program_load_desc)
	                   + sizeof(struct program_image_section) * nhdrs);
	desc->magic = PLD_MAGIC;
	fseek(fp, hdr.e_phoff, SEEK_SET);
	j = 0;
	desc->num_sections = nhdrs;
	desc->stack_prot = PROT_READ | PROT_WRITE | PROT_EXEC;	/* default */
	for (i = 0; i < hdr.e_phnum; i++) {
		if (fread(&phdr, sizeof(phdr), 1, fp) < 1) {
			__eprintf("Loading phdr failed (%d)\n", i);
			return NULL;
		}
		if (phdr.p_type == PT_INTERP) {
			if (phdr.p_filesz > sizeof(interp_path)) {
				__eprintf("too large PT_INTERP segment\n");
				return NULL;
			}
			ss = pread(fileno(fp), interp_path, phdr.p_filesz,
					phdr.p_offset);
			if (ss <= 0) {
				__eprintf("cannot read PT_INTERP segment\n");
				return NULL;
			}
			interp_path[ss] = '\0';
			*interp_pathp = interp_path;
		}
		if (phdr.p_type == PT_PHDR) {
			at_phdr = phdr.p_vaddr;
			at_phdr_set = 1;
		}
		if (phdr.p_type == PT_LOAD) {
			desc->sections[j].vaddr = phdr.p_vaddr;
			desc->sections[j].filesz = phdr.p_filesz;
			desc->sections[j].offset = phdr.p_offset;
			desc->sections[j].len = phdr.p_memsz;
			desc->sections[j].interp = 0;
			desc->sections[j].fp = fp;

			desc->sections[j].prot = PROT_NONE;
			desc->sections[j].prot |= (phdr.p_flags & PF_R)? PROT_READ: 0;
			desc->sections[j].prot |= (phdr.p_flags & PF_W)? PROT_WRITE: 0;
			desc->sections[j].prot |= (phdr.p_flags & PF_X)? PROT_EXEC: 0;

			__dprintf("%d: (%s) %lx, %lx, %lx, %lx, %x\n",
				  j, (phdr.p_type == PT_LOAD ? "PT_LOAD" : "PT_TLS"), 
				  desc->sections[j].vaddr,
			          desc->sections[j].filesz,
			          desc->sections[j].offset,
			          desc->sections[j].len,
				  desc->sections[j].prot);
			j++;

			if (!load_addr_set) {
				load_addr_set = 1;
				load_addr = phdr.p_vaddr - phdr.p_offset;
			}
		}
		if (phdr.p_type == PT_GNU_STACK) {
			desc->stack_prot = PROT_NONE;
			desc->stack_prot |= (phdr.p_flags & PF_R)? PROT_READ: 0;
			desc->stack_prot |= (phdr.p_flags & PF_W)? PROT_WRITE: 0;
			desc->stack_prot |= (phdr.p_flags & PF_X)? PROT_EXEC: 0;
		}
	}
	desc->pid = getpid();
	desc->pgid = getpgid(0);
	if(*interp_pathp)
		desc->reloc = hdr.e_type == ET_DYN;
	desc->entry = hdr.e_entry;
	ioctl(fd, MCEXEC_UP_GET_CREDV, desc->cred);
	desc->at_phdr = at_phdr_set ? at_phdr : load_addr + hdr.e_phoff;
	desc->at_phent = sizeof(phdr);
	desc->at_phnum = hdr.e_phnum;
	desc->at_entry = hdr.e_entry;
	desc->at_clktck = sysconf(_SC_CLK_TCK);

	return desc;
}
#endif

#ifdef MCEXEC_RUST_HELPERS
unsigned long mcexec_main_page_size_bridge(void)
{
	return sysconf(_SC_PAGESIZE);
}

void mcexec_main_publish_page_altroot_bridge(unsigned long new_page_size,
		const char *new_altroot)
{
	page_size = new_page_size;
	page_mask = ~(page_size - 1);
	altroot = (char *)new_altroot;
}

const char *mcexec_altroot_bridge(void)
{
	return altroot;
}

void mcexec_search_file_path_too_long_bridge(const char *root,
		const char *path)
{
	__eprintf("modified path too long: %s/%s\n", root, path);
}
#else
char *search_file(char *orgpath, int mode)
{
	int error;
	static char modpath[PATH_MAX];
	int n;

	error = access(orgpath, mode);
	if (!error) {
		return orgpath;
	}

#ifdef MCEXEC_RUST_HELPERS
	n = mcexec_join_path_result(altroot, orgpath, modpath,
			sizeof(modpath));
#else
	n = snprintf(modpath, sizeof(modpath), "%s/%s", altroot, orgpath);
#endif
	if (n < 0 || n >= sizeof(modpath)) {
		__eprintf("modified path too long: %s/%s\n", altroot, orgpath);
		return NULL;
	}

	error = access(modpath, mode);
	if (!error) {
		return modpath;
	}

	return NULL;
}
#endif

#ifdef MCEXEC_RUST_HELPERS
struct program_load_desc *load_interp(struct program_load_desc *desc0,
		FILE *fp);
#else
struct program_load_desc *load_interp(struct program_load_desc *desc0, FILE *fp)
{
	Elf64_Ehdr hdr;
	Elf64_Phdr phdr;
	int i, j, nhdrs = 0;
	struct program_load_desc *desc = desc0;
	size_t newsize;
	unsigned long align;

	if (fread(&hdr, sizeof(hdr), 1, fp) < 1) {
		__eprintf("Cannot read Ehdr.\n");
		return NULL;
	}
	if (memcmp(hdr.e_ident, ELFMAG, SELFMAG)) {
		__eprintf("ELFMAG mismatched.\n");
		return NULL;
	}
	fseek(fp, hdr.e_phoff, SEEK_SET);
	for (i = 0; i < hdr.e_phnum; i++) {
		if (fread(&phdr, sizeof(phdr), 1, fp) < 1) {
			__eprintf("Loading phdr failed (%d)\n", i);
			return NULL;
		}
		if (phdr.p_type == PT_LOAD) {
			nhdrs++;
		}
	}

	nhdrs += desc->num_sections;
	newsize = sizeof(struct program_load_desc)
		+ (nhdrs * sizeof(struct program_image_section));
	desc = realloc(desc, newsize);
	if (!desc) {
		__eprintf("realloc(%#lx) failed\n", (long)newsize);
		return NULL;
	}

	fseek(fp, hdr.e_phoff, SEEK_SET);
	align = 1;
	j = desc->num_sections;
	for (i = 0; i < hdr.e_phnum; i++) {
		if (fread(&phdr, sizeof(phdr), 1, fp) < 1) {
			__eprintf("Loading phdr failed (%d)\n", i);
			free(desc);
			return NULL;
		}
		if (phdr.p_type == PT_INTERP) {
			__eprintf("PT_INTERP on interp\n");
			free(desc);
			return NULL;
		}
		if (phdr.p_type == PT_LOAD) {
			desc->sections[j].vaddr = phdr.p_vaddr;
			desc->sections[j].filesz = phdr.p_filesz;
			desc->sections[j].offset = phdr.p_offset;
			desc->sections[j].len = phdr.p_memsz;
			desc->sections[j].interp = 1;
			desc->sections[j].fp = fp;

			desc->sections[j].prot = PROT_NONE;
			desc->sections[j].prot |= (phdr.p_flags & PF_R)? PROT_READ: 0;
			desc->sections[j].prot |= (phdr.p_flags & PF_W)? PROT_WRITE: 0;
			desc->sections[j].prot |= (phdr.p_flags & PF_X)? PROT_EXEC: 0;

			if (phdr.p_align > align) {
				align = phdr.p_align;
			}

			__dprintf("%d: (%s) %lx, %lx, %lx, %lx, %x\n",
				  j, (phdr.p_type == PT_LOAD ? "PT_LOAD" : "PT_TLS"),
				  desc->sections[j].vaddr,
			          desc->sections[j].filesz,
			          desc->sections[j].offset,
			          desc->sections[j].len,
				  desc->sections[j].prot);
			j++;
		}
	}
	desc->num_sections = j;

	desc->entry = hdr.e_entry;
	desc->interp_align = align;

	return desc;
}
#endif

unsigned char *dma_buf;

#ifdef MCEXEC_RUST_HELPERS
int mcexec_lookup_lstat_errno_bridge(const char *path)
{
	struct stat sb;

	if (lstat(path, &sb) == -1) {
		return errno;
	}

	return 0;
}

void mcexec_lookup_array_too_small_bridge(void)
{
	fprintf(stderr, "lookup_exec_path(): array too small?\n");
}

void mcexec_lookup_stat_error_bridge(const char *path, int error)
{
	__dprintf("lookup_exec_path(): error stat for %s: %d\n",
		  path, error);
}

void mcexec_lookup_not_found_bridge(const char *filename)
{
	fprintf(stderr,
		"lookup_exec_path(): error finding file %s\n", filename);
}

void mcexec_lookup_success_bridge(const char *path)
{
	__dprintf("lookup_exec_path(): %s\n", path);
}
#else
int lookup_exec_path(char *filename, char *path, int max_len, int execvp) 
{
	int found;
	int error;
	int filename_absolute;
	int filename_single_component;
	int filename_len_lt_255;
	struct stat sb;
	char *link_path = NULL;

	found = 0;
#ifdef MCEXEC_RUST_HELPERS
	filename_absolute = mcexec_path_is_absolute_result(filename);
	filename_single_component =
		mcexec_path_is_single_component_exec_result(filename);
	filename_len_lt_255 = mcexec_path_len_less_than_result(filename, 255);
#else
	filename_absolute = !strncmp(filename, "/", 1);
	filename_single_component =
		strncmp(filename, ".", 1) && !strchr(filename, '/');
	filename_len_lt_255 = strlen(filename) < 255;
#endif

	/* Is file not absolute path? */
	if (!filename_absolute) {
		
		/* Is filename a single component without path? */
		while (filename_single_component) {

			char *token, *string, *tofree;
			char *PATH = getenv("COKERNEL_PATH");

			if (!execvp) {
#ifdef MCEXEC_RUST_HELPERS
				error = mcexec_copy_path_result(filename, path,
						max_len);
				if (error < 0) {
					free(link_path);
					return error == -ENAMETOOLONG ?
						ENAMETOOLONG : EINVAL;
				}
#else
				if (strlen(filename) + 1 > max_len) {
					free(link_path);
					return ENAMETOOLONG;
				}
				strcpy(path, filename);
#endif
				error = access(path, X_OK);
				if (error) {
					free(link_path);
					return errno;
				}
				found = 1;
				break;
			}

			if (!(PATH = getenv("COKERNEL_PATH"))) {
				PATH = getenv("PATH");
			}

			if (!filename_len_lt_255) {
				free(link_path);
				return ENAMETOOLONG;
			}

			__dprintf("PATH: %s\n", PATH);

			/* strsep() modifies string! */
			tofree = string = strdup(PATH);
			if (string == NULL) {
				printf("lookup_exec_path(): copying PATH, not enough memory?\n");
				free(link_path);
				return ENOMEM;
			}

			while ((token = strsep(&string, ":")) != NULL) {

#ifdef MCEXEC_RUST_HELPERS
				error = mcexec_join_path_result(token, filename,
						path, max_len);
#else
				error = snprintf(path, max_len,
						"%s/%s", token, filename);
#endif
				if (error < 0 || error >= max_len) {
					fprintf(stderr, "lookup_exec_path(): array too small?\n");
					continue;
				}

				error = access(path, X_OK);
				if (error == 0) {
					found = 1;
					break;
				}
			}

			free(tofree);
			if (!found) {
				free(link_path);
				return ENOENT;
			}
			break;
		}

		/* Not in path, file to be open from the working directory */
		if (!found) {
#ifdef MCEXEC_RUST_HELPERS
			error = mcexec_copy_path_result(filename, path, max_len);
#else
			error = snprintf(path, max_len, "%s", filename);
#endif

			if (error < 0 || error >= max_len) {
				fprintf(stderr, "lookup_exec_path(): array too small?\n");
				free(link_path);
				return ENOMEM;
			}

			found = 1;
		}
	}
	/* Absolute path */
	else if (filename_absolute) {
		char *root = getenv("COKERNEL_EXEC_ROOT");

		if (root) {
#ifdef MCEXEC_RUST_HELPERS
			error = mcexec_join_path_result(root, filename, path,
					max_len);
#else
			error = snprintf(path, max_len, "%s/%s", root, filename);
#endif
		}
		else {
#ifdef MCEXEC_RUST_HELPERS
			error = mcexec_copy_path_result(filename, path, max_len);
#else
			error = snprintf(path, max_len, "%s", filename);
#endif
		}

		if (error < 0 || error >= max_len) {
			fprintf(stderr, "lookup_exec_path(): array too small?\n");
			free(link_path);
			return ENOMEM;
		}

		found = 1;
	}

	if (link_path) {
		free(link_path);
		link_path = NULL;
	}

	/* Check whether the resolved path is a symlink */
	if (lstat(path, &sb) == -1) {
		error = errno;
		__dprintf("lookup_exec_path(): error stat for %s: %d\n",
			  path, error);
		return error;
	}

	if (!found) {
		fprintf(stderr, 
				"lookup_exec_path(): error finding file %s\n", filename);
		return ENOENT;
	}

	__dprintf("lookup_exec_path(): %s\n", path);

	return 0;
}
#endif

#ifdef MCEXEC_RUST_HELPERS
int load_elf_desc(char *filename, struct program_load_desc **desc_p,
		char **shebang_p);

int mcexec_load_desc_stat_size_bridge(const char *filename, long *size_out)
{
	struct stat sb;

	if (stat(filename, &sb) == -1) {
		__dprintf("Error: failed to stat %s\n", filename);
		return errno;
	}

	*size_out = sb.st_size;
	return 0;
}

void mcexec_load_desc_not_executable_bridge(const char *filename, int error)
{
	__dprintf("Error: %s is not an executable?, errno: %d\n",
		  filename, error);
}

void mcexec_load_desc_zero_length_bridge(const char *filename)
{
	__dprintf("Error: file %s is zero length\n", filename);
}

void mcexec_load_desc_open_failed_bridge(const char *filename)
{
	__dprintf("Error: Failed to open %s\n", filename);
}

void mcexec_load_desc_header_failed_bridge(const char *filename)
{
	__dprintf("Error: Failed to read header from %s\n", filename);
}

void mcexec_load_desc_shebang_read_failed_bridge(const char *filename)
{
	__dprintf("Error: reading shebang path %s\n", filename);
}

void mcexec_load_desc_open_exec_failed_bridge(const char *filename,
		int ret, int fd_value)
{
	fprintf(stderr, "Error: open_exec() fails for %s: %d (fd: %d)\n",
		filename, ret, fd_value);
}

void mcexec_load_desc_publish_exec_path_bridge(char *path)
{
	if (exec_path) {
		free(exec_path);
	}
	exec_path = path;
}

void mcexec_load_desc_strdup_failed_bridge(void)
{
	fprintf(stderr, "WARNING: strdup(filename) failed\n");
}

void mcexec_load_desc_getcwd_failed_bridge(void)
{
	fprintf(stderr, "Error: getting current working dir pathname\n");
}

void mcexec_load_desc_alloc_exec_path_failed_bridge(void)
{
	fprintf(stderr, "Error: allocating exec_path\n");
}

void mcexec_load_desc_build_exec_path_failed_bridge(void)
{
	fprintf(stderr, "Error: building exec_path\n");
}

void mcexec_load_desc_parse_elf_failed_bridge(void)
{
	fprintf(stderr, "Error: Failed to parse ELF!\n");
}

void mcexec_load_desc_interp_not_found_bridge(const char *path)
{
	fprintf(stderr, "Error: interp not found: %s\n", path);
}

void mcexec_load_desc_interp_open_failed_bridge(const char *path)
{
	fprintf(stderr, "Error: Failed to open %s\n", path);
}

void mcexec_load_desc_parse_interp_failed_bridge(void)
{
	fprintf(stderr, "Error: Failed to parse interp!\n");
}

void mcexec_load_desc_sections_bridge(int count)
{
	__dprintf("# of sections: %d\n", count);
}
#else
int load_elf_desc(char *filename, struct program_load_desc **desc_p,
		char **shebang_p)
{
	FILE *fp;
	FILE *interp = NULL;
	char *interp_path;
	char *shebang = NULL;
	size_t shebang_len = 0;
	struct program_load_desc *desc;
	int ret = 0;
	struct stat sb;
	char header[1024];

	if ((ret = access(filename, X_OK)) != 0) {
		__dprintf("Error: %s is not an executable?, errno: %d\n",
			filename, errno);
		return errno;
	}
	
	if ((ret = stat(filename, &sb)) == -1) {
		__dprintf("Error: failed to stat %s\n", filename);
		return errno;
	}
	
	if (sb.st_size == 0) {
		__dprintf("Error: file %s is zero length\n", filename);
		return ENOEXEC;
	}

	fp = fopen(filename, "rb");
	if (!fp) {
		__dprintf("Error: Failed to open %s\n", filename);
		return errno;
	}

	if (fread(&header, 1, 2, fp) != 2) {
		__dprintf("Error: Failed to read header from %s\n", filename);
		fclose(fp);
		return errno;
	}

	if (!strncmp(header, "#!", 2)) {
		if (getline(&shebang, &shebang_len, fp) == -1) {
			__dprintf("Error: reading shebang path %s\n",
				filename);
		}

		fclose(fp);

		/* Delete new line character and any trailing/leading spaces */
		shebang_len = strlen(shebang) - 1;
		shebang[shebang_len] = '\0';
		while (shebang_len > 0 &&
				strpbrk(shebang + shebang_len - 1, " \t")) {
			shebang_len--;
			shebang[shebang_len] = '\0';
		}
		while (shebang_len > 0 && strpbrk(shebang, " \t") == shebang) {
			shebang_len--;
			shebang++;
		}
		*shebang_p = shebang;
		return 0;
	}

	rewind(fp);
	
	if ((ret = ioctl(fd, MCEXEC_UP_OPEN_EXEC, filename)) != 0) {
		fprintf(stderr, "Error: open_exec() fails for %s: %d (fd: %d)\n", 
			filename, ret, fd);
		fclose(fp);
		return ret;
	}

	/* Drop old name if exists */
	if (exec_path) {
		free(exec_path);
		exec_path = NULL;
	}

	if (!strncmp("/", filename, 1)) {
		exec_path = strdup(filename);
		
		if (!exec_path) {
			fprintf(stderr, "WARNING: strdup(filename) failed\n");
			fclose(fp);
			return ENOMEM;
		}
	}
	else {
		char *cwd = getcwd(NULL, 0);
		if (!cwd) {
			fprintf(stderr, "Error: getting current working dir pathname\n");
			fclose(fp);
			return ENOMEM;
		}

		exec_path = malloc(strlen(cwd) + strlen(filename) + 2);
		if (!exec_path) {
			fprintf(stderr, "Error: allocating exec_path\n");
			free(cwd);
			fclose(fp);
			return ENOMEM;
		}

#ifdef MCEXEC_RUST_HELPERS
		if (mcexec_join_path_result(cwd, filename, exec_path,
					strlen(cwd) + strlen(filename) + 2) < 0) {
			fprintf(stderr, "Error: building exec_path\n");
			free(exec_path);
			exec_path = NULL;
			free(cwd);
			fclose(fp);
			return ENOMEM;
		}
#else
		sprintf(exec_path, "%s/%s", cwd, filename);
#endif
		free(cwd);
	}
	
	desc = load_elf(fp, &interp_path);
	if (!desc) {
		fprintf(stderr, "Error: Failed to parse ELF!\n");
		fclose(fp);
		return 1;
	}

	if (interp_path) {
		char *path;

		path = search_file(interp_path, X_OK);
		if (!path) {
			fprintf(stderr, "Error: interp not found: %s\n", interp_path);
			fclose(fp);
			return 1;
		}

		interp = fopen(path, "rb");
		if (!interp) {
			fprintf(stderr, "Error: Failed to open %s\n", path);
			fclose(fp);
			return 1;
		}

		desc = load_interp(desc, interp);
		if (!desc) {
			fprintf(stderr, "Error: Failed to parse interp!\n");
			fclose(fp);
			fclose(interp);
			return 1;
		}
	}

	__dprintf("# of sections: %d\n", desc->num_sections);
	
	*desc_p = desc;
	return 0;
}
#endif

/* recursively resolve shebangs
 *
 * Note: shebang_argv_p must point to reallocable memory or be NULL
 */
#ifdef MCEXEC_RUST_HELPERS
int load_elf_desc_shebang(char *shebang_argv0,
			  struct program_load_desc **desc_p,
			  char ***shebang_argv_p,
			  int execvp);

void mcexec_load_shebang_find_error_bridge(const char *path)
{
	__dprintf("error: finding file: %s\n", path);
}

void mcexec_load_shebang_load_error_bridge(const char *path)
{
	__dprintf("error: loading file: %s\n", path);
}
#else
int load_elf_desc_shebang(char *shebang_argv0,
			  struct program_load_desc **desc_p,
			  char ***shebang_argv_p,
			  int execvp)
{
	char path[PATH_MAX];
	char *shebang = NULL;
	int ret;

	if ((ret = lookup_exec_path(shebang_argv0, path, sizeof(path), execvp))
			!= 0) {
		__dprintf("error: finding file: %s\n", shebang_argv0);
		return ret;
	}

	if ((ret = load_elf_desc(path, desc_p, &shebang)) != 0) {
		__dprintf("error: loading file: %s\n", shebang_argv0);
		return ret;
	}

	if (shebang) {
#ifdef MCEXEC_RUST_HELPERS
		if (!shebang_argv_p)
			return load_elf_desc_shebang(shebang, desc_p,
						     NULL, execvp);

		if (mcexec_shebang_argv_extend_result(shebang_argv_p,
				shebang) < 0) {
			return ENOMEM;
		}
#else
		char *shebang_params;
		size_t shebang_param_count = 1;
		size_t shebang_argv_count = 0;
		char **shebang_argv;

		if (!shebang_argv_p)
			return load_elf_desc_shebang(shebang, desc_p,
						     NULL, execvp);

		shebang_argv = *shebang_argv_p;

		/* if there is a space, add whatever follows as extra arg */
		shebang_params = strchr(shebang, ' ');
		if (shebang_params) {
			shebang_params[0] = '\0';
			shebang_params++;
			shebang_param_count++;
		}

		if (shebang_argv == NULL) {
			shebang_argv_count = shebang_param_count + 1;
			shebang_argv = malloc(shebang_argv_count *
					      sizeof(void *));
			shebang_argv[shebang_param_count] = 0;
		} else {
			while (shebang_argv[shebang_argv_count++])
				;

			shebang_argv_count += shebang_param_count + 1;
			shebang_argv = realloc(shebang_argv,
					    shebang_argv_count * sizeof(void *));
			memmove(shebang_argv + shebang_param_count,
				shebang_argv,
				(shebang_argv_count - shebang_param_count)
					* sizeof(void *));
		}
		shebang_argv[0] = shebang;
		if (shebang_params)
			shebang_argv[1] = shebang_params;

		*shebang_argv_p = shebang_argv;
#endif

		return load_elf_desc_shebang(shebang, desc_p, shebang_argv_p,
					     execvp);
	}

	return 0;
}
#endif

#ifdef MCEXEC_RUST_HELPERS
size_t mcexec_program_load_desc_size_bridge(void)
{
	return sizeof(struct program_load_desc);
}

size_t mcexec_program_image_section_size_bridge(void)
{
	return sizeof(struct program_image_section);
}

void mcexec_load_cannot_read_ehdr_bridge(void)
{
	__eprintf("Cannot read Ehdr.\n");
}

void mcexec_load_elfmag_mismatch_bridge(void)
{
	__eprintf("ELFMAG mismatched.\n");
}

void mcexec_load_phdr_failed_bridge(int index)
{
	__eprintf("Loading phdr failed (%d)\n", index);
}

void mcexec_load_realloc_failed_bridge(unsigned long size)
{
	__eprintf("realloc(%#lx) failed\n", (long)size);
}

void mcexec_load_pt_interp_on_interp_bridge(void)
{
	__eprintf("PT_INTERP on interp\n");
}

void mcexec_desc_set_num_sections_bridge(struct program_load_desc *desc,
		int count)
{
	desc->num_sections = count;
}

void mcexec_desc_set_entry_bridge(struct program_load_desc *desc,
		unsigned long entry)
{
	desc->entry = entry;
}

void mcexec_desc_set_interp_align_bridge(struct program_load_desc *desc,
		unsigned long align)
{
	desc->interp_align = align;
}

void mcexec_desc_publish_interp_section_bridge(
		struct program_load_desc *desc, int index,
		unsigned long vaddr, unsigned long filesz,
		unsigned long offset, unsigned long len, int prot, void *fp)
{
	desc->sections[index].vaddr = vaddr;
	desc->sections[index].filesz = filesz;
	desc->sections[index].offset = offset;
	desc->sections[index].len = len;
	desc->sections[index].interp = 1;
	desc->sections[index].fp = fp;
	desc->sections[index].prot = prot;
}

void mcexec_load_section_log_bridge(int index, unsigned long vaddr,
		unsigned long filesz, unsigned long offset,
		unsigned long len, int prot)
{
	__dprintf("%d: (%s) %lx, %lx, %lx, %lx, %x\n",
		  index, "PT_LOAD", vaddr, filesz, offset, len, prot);
}

int transfer_image(int fd, struct program_load_desc *desc);
#else
int transfer_image(int fd, struct program_load_desc *desc)
{
	struct remote_transfer pt;
	unsigned long s, e, flen, rpa;
	int i, l, lr;
	FILE *fp;

	for (i = 0; i < desc->num_sections; i++) {
		fp = desc->sections[i].fp;
		s = (desc->sections[i].vaddr) & page_mask;
		e = (desc->sections[i].vaddr + desc->sections[i].len
		     + page_size - 1) & page_mask;
		rpa = desc->sections[i].remote_pa;

		if (fseek(fp, desc->sections[i].offset, SEEK_SET) != 0) {
			fprintf(stderr, "transfer_image(): error: seeking file position\n");
			return -1;
		}
		flen = desc->sections[i].filesz;

		__dprintf("seeked to %lx | size %ld\n",
		          desc->sections[i].offset, flen);

		while (s < e) {
			memset(&pt, '\0', sizeof pt);
			pt.rphys = rpa;
			pt.userp = dma_buf;
			pt.size = page_size;
			pt.direction = MCEXEC_UP_TRANSFER_TO_REMOTE;
			lr = 0;
			
			memset(dma_buf, 0, page_size);
			if (s < desc->sections[i].vaddr) {
				l = desc->sections[i].vaddr 
					& (page_size - 1);
				lr = page_size - l;
				if (lr > flen) {
					lr = flen;
				}
				if (fread(dma_buf + l, 1, lr, fp) != lr) {
					if (ferror(fp) > 0) {
						fprintf(stderr, "transfer_image(): error: accessing file\n");
						return -EINVAL;
					}
					else if (feof(fp) > 0) {
						fprintf(stderr, "transfer_image(): file too short?\n");
						return -EINVAL;
					}
					else {
						/* TODO: handle smaller reads.. */
						return -EINVAL;
					}
				}
				flen -= lr;
			} 
			else if (flen > 0) {
				if (flen > page_size) {
					lr = page_size;
				} else {
					lr = flen;
				}
				if (fread(dma_buf, 1, lr, fp) != lr) {
					if (ferror(fp) > 0) {
						fprintf(stderr, "transfer_image(): error: accessing file\n");
						return -EINVAL;
					}
					else if (feof(fp) > 0) {
						fprintf(stderr, "transfer_image(): file too short?\n");
						return -EINVAL;
					}
					else {
						/* TODO: handle smaller reads.. */
						return -EINVAL;
					}
				}
				flen -= lr;
			} 
			s += page_size;
			rpa += page_size;
			
			/* No more left to upload.. */
			if (lr == 0 && flen == 0) break;

			if (ioctl(fd, MCEXEC_UP_TRANSFER,
						(unsigned long)&pt)) {
				perror("dma");
				break;
			}
		}
	}

	return 0;
}
#endif

#ifdef MCEXEC_RUST_HELPERS
int mcexec_desc_num_sections_bridge(const struct program_load_desc *desc)
{
	return desc->num_sections;
}

int mcexec_desc_cpu_bridge(const struct program_load_desc *desc)
{
	return desc->cpu;
}

int mcexec_desc_pid_bridge(const struct program_load_desc *desc)
{
	return desc->pid;
}

unsigned long mcexec_desc_entry_bridge(const struct program_load_desc *desc)
{
	return desc->entry;
}

unsigned long mcexec_desc_rprocess_bridge(const struct program_load_desc *desc)
{
	return desc->rprocess;
}

unsigned long mcexec_desc_section_vaddr_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].vaddr;
}

unsigned long mcexec_desc_section_len_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].len;
}

unsigned long mcexec_desc_section_remote_pa_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].remote_pa;
}

unsigned long mcexec_desc_section_filesz_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].filesz;
}

unsigned long mcexec_desc_section_offset_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].offset;
}

void *mcexec_desc_section_fp_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].fp;
}

void mcexec_transfer_seek_error_bridge(void)
{
	fprintf(stderr, "transfer_image(): error: seeking file position\n");
}

void mcexec_transfer_access_error_bridge(void)
{
	fprintf(stderr, "transfer_image(): error: accessing file\n");
}

void mcexec_transfer_short_error_bridge(void)
{
	fprintf(stderr, "transfer_image(): file too short?\n");
}

void mcexec_transfer_seeked_bridge(unsigned long offset,
		unsigned long size)
{
	__dprintf("seeked to %lx | size %ld\n", offset, size);
}

void mcexec_print_desc_intro_bridge(const void *desc)
{
	if (debug) {
		printf("print_desc: Desc (%p)\n", desc);
		fflush(stdout);
	}
}

void mcexec_print_desc_main_bridge(int cpu, int pid, unsigned long entry,
		unsigned long rprocess)
{
	if (debug) {
		printf("print_desc: CPU = %d, pid = %d, entry = %lx, rp = %lx\n",
				cpu, pid, entry, rprocess);
		fflush(stdout);
	}
}

void mcexec_print_desc_section_bridge(unsigned long vaddr,
		unsigned long len, unsigned long remote_pa,
		unsigned long filesz)
{
	if (debug) {
		printf("print_desc: vaddr: %lx, mem_len: %lx, remote_pa: %lx, files: %lx\n",
				vaddr, len, remote_pa, filesz);
		fflush(stdout);
	}
}
#else
void print_desc(struct program_load_desc *desc)
{
	int i;

	__dprintf("Desc (%p)\n", desc);
	__dprintf("CPU = %d, pid = %d, entry = %lx, rp = %lx\n",
		  desc->cpu, desc->pid, desc->entry, desc->rprocess);
	for (i = 0; i < desc->num_sections; i++) {
		__dprintf("vaddr: %lx, mem_len: %lx, remote_pa: %lx, files: %lx\n", 
		          desc->sections[i].vaddr, desc->sections[i].len, 
				  desc->sections[i].remote_pa, desc->sections[i].filesz);
	}
}
#endif

#define PIN_SHIFT  12
#define PIN_SIZE  (1 << PIN_SHIFT)
#define PIN_MASK  ~(unsigned long)(PIN_SIZE - 1)

#if 0
unsigned long dma_buf_pa;
#endif


#ifdef MCEXEC_RUST_HELPERS
void *mcexec_dma_mmap_bridge(void)
{
	return mmap(0, PIN_SIZE, PROT_READ | PROT_WRITE,
			(MAP_ANONYMOUS | MAP_PRIVATE), -1, 0);
}

int mcexec_dma_mlock_bridge(void *buf)
{
	return mlock(buf, (size_t)PIN_SIZE);
}

void mcexec_dma_mmap_failed_bridge(void)
{
	__dprintf("error: allocating DMA area\n");
	exit(1);
}

void mcexec_dma_mlock_failed_bridge(void)
{
	__dprintf("ERROR: locking dma_buf\n");
	exit(1);
}

int mcexec_create_ppd_bridge(void)
{
	return ioctl(fd, MCEXEC_UP_CREATE_PPD, NULL);
}

void mcexec_create_ppd_failed_bridge(void)
{
	perror("creating mcctrl per-process structure");
	close(fd);
	exit(1);
}

void mcexec_print_flat_count_bridge(long count)
{
	__dprintf("counter: %ld\n", count);
}

void mcexec_print_flat_entry_bridge(const char *entry)
{
	__dprintf("%s\n", entry);
}
#else
void print_flat(char *flat) 
{
	long i, count;
	long *_flat = (long *)flat;

	count = _flat[0];
	__dprintf("counter: %ld\n", count);

	for (i = 0; i < count; i++) {
		__dprintf("%s\n", (flat + _flat[i + 1]));
	}
}
#endif

/* 
 * Flatten out a (char **) string array into the following format:
 * [nr_strings][char *offset of string_0]...[char *offset of string_n-1][char *offset of end of string][string0]...[stringn_1]
 * if nr_strings == -1, we assume the last item is NULL 
 *
 * sizes all are longs.
 *
 * NOTE: copy this string somewhere, add the address of the string to each offset
 * and we get back a valid argv or envp array.
 *
 * pre_strings is already flattened, so we just need to manage counts and copy
 * the string part appropriately.
 *
 * returns the total length of the flat string and updates flat to
 * point to the beginning.
 */
#ifndef MCEXEC_RUST_HELPERS
int flatten_strings(char *pre_strings, char **strings, char **flat)
{
	int full_len, len, i;
	int nr_strings;
	int pre_strings_count = 0;
	int pre_strings_len = 0;
	long *_flat;
	long *pre_strings_flat;
	char *p;

	for (nr_strings = 0; strings[nr_strings]; ++nr_strings)
		;

	/* Count full length */
	full_len = sizeof(long) + sizeof(char *); // Counter and terminating NULL
	if (pre_strings) {
		pre_strings_flat = (long *)pre_strings;
		pre_strings_count = pre_strings_flat[0];

		pre_strings_len = pre_strings_flat[pre_strings_count + 1];
		pre_strings_len -= sizeof(long) * (pre_strings_count + 2);

		full_len += pre_strings_count * sizeof(long) + pre_strings_len;
	}

	for (i = 0; strings[i]; ++i) {
		// Pointer + actual value
		full_len += sizeof(char *) + strlen(strings[i]) + 1;
	}

	full_len = (full_len + sizeof(long) - 1) & ~(sizeof(long) - 1);

	_flat = malloc(full_len);
	if (!_flat) {
		return 0;
	}

	memset(_flat, 0, full_len);

	/* Number of strings */
	_flat[0] = nr_strings + pre_strings_count;
	
	// Actual offset
	p = (char *)(_flat + nr_strings + pre_strings_count + 2);

	if (pre_strings) {
		for (i = 0; i < pre_strings_count; i++) {
			_flat[i + 1] = pre_strings_flat[i + 1] +
					nr_strings * sizeof(long);
		}
		memcpy(p, pre_strings + pre_strings_flat[1],
		       pre_strings_len);
		p += pre_strings_len;
	}

	for (i = 0; i < nr_strings; ++i) {
		int len = strlen(strings[i]) + 1;

		_flat[i + pre_strings_count + 1] = p - (char *)_flat;

		memcpy(p, strings[i], len);
		p += len;
	}
	_flat[nr_strings + pre_strings_count + 1] = p - (char *)_flat;

	*flat = (char *)_flat;
	len = p - (char *)_flat;
	if (len < full_len)
		memset(p, 0, full_len - len);

	return len;
}
#endif /* !MCEXEC_RUST_HELPERS */

//#define NUM_HANDLER_THREADS	248

struct thread_data_s {
	struct thread_data_s *next;
	pthread_t thread_id;
	int cpu;
	int ret;
	pid_t	tid;
	int terminate;
	int remote_tid;
	int remote_cpu;
	int joined, detached;
	pthread_mutex_t *lock;
	pthread_barrier_t *init_ready;
} *thread_data;

int ncpu;
int nnodes;
void *numa_nodes;
size_t cpu_set_size;
int n_threads;

#ifndef MCEXEC_RUST_HELPERS
static inline cpu_set_t *numa_node_set(int n)
{
	return (cpu_set_t *)(numa_nodes + n * cpu_set_size);
}
#else
#define numa_node_set(n) \
	((cpu_set_t *)mcexec_numa_node_set_body((n), numa_nodes, cpu_set_size))
#endif

#ifdef MCEXEC_RUST_HELPERS
int mcexec_numa_node_cpu_isset_bridge(int node, int cpu)
{
	return CPU_ISSET_S(cpu, cpu_set_size, numa_node_set(node));
}

void mcexec_numa_local_cpu_log_bridge(int cpu)
{
	__dprintf("%d belongs to local set\n", cpu);
}

void mcexec_numa_node_cpu_log_bridge(int cpu, int node)
{
	__dprintf("%d belongs to node %d\n", cpu, node);
}

int mcexec_main_get_cpu_bridge(void)
{
	return ioctl(fd, MCEXEC_UP_GET_CPU, 0);
}

int mcexec_main_get_nodes_bridge(void)
{
	return ioctl(fd, MCEXEC_UP_GET_NODES, 0);
}

void mcexec_main_no_cpu_bridge(void)
{
	fprintf(stderr, "No CPU found.\n");
}

void mcexec_main_no_numa_node_bridge(void)
{
	fprintf(stderr, "No numa node found.\n");
}

size_t mcexec_main_cpu_alloc_size_bridge(int cpu_count)
{
	return CPU_ALLOC_SIZE(cpu_count);
}

void mcexec_main_alloc_nodes_error_bridge(void)
{
	fprintf(stderr, "Error allocating nodes cpu sets\n");
}

void mcexec_main_publish_topology_bridge(int cpu_count, int node_count,
		size_t node_set_size, void *nodes)
{
	ncpu = cpu_count;
	nnodes = node_count;
	cpu_set_size = node_set_size;
	numa_nodes = nodes;
}

void mcexec_main_numa_node_zero_bridge(void *nodes, size_t node_set_size,
		int node_id)
{
	CPU_ZERO_S(node_set_size,
			(cpu_set_t *)((char *)nodes + node_id * node_set_size));
}

int mcexec_main_node_cpu_exists_bridge(int node_id, int cpu)
{
	struct stat sb;
	char buf[PATH_MAX];

	snprintf(buf, PATH_MAX,
			"/sys/class/mcos/mcos0/sys/devices/system/node/node%d/cpu%d",
			node_id, cpu);
	return stat(buf, &sb) == 0;
}

void mcexec_main_numa_node_set_cpu_bridge(void *nodes, size_t node_set_size,
		int node_id, int cpu)
{
	CPU_SET_S(cpu, node_set_size,
			(cpu_set_t *)((char *)nodes + node_id * node_set_size));
}

void mcexec_process_thread_plan_flib_log_bridge(int planned_nr_processes)
{
	__dprintf("%s: using FLIB_NUM_PROCESS_ON_NODE: %d\n",
			"main", planned_nr_processes);
}

static cpu_set_t mcexec_partition_cpu_set_storage;

int mcexec_partition_get_cpuset_bridge(struct program_load_desc *desc,
		int nr_processes, int *target_core, int *process_rank,
		int *mcexec_linux_numa, int *ikc_mapped)
{
	struct get_cpu_set_arg cpu_set_arg;

	CPU_ZERO(&mcexec_partition_cpu_set_storage);

	cpu_set_arg.req_cpu_list = NULL;
	cpu_set_arg.req_cpu_list_len = 0;
	cpu_set_arg.cpu_set = (void *)&desc->cpu_set;
	cpu_set_arg.cpu_set_size = sizeof(desc->cpu_set);
	cpu_set_arg.nr_processes = nr_processes;
	cpu_set_arg.ppid = getppid();
	cpu_set_arg.target_core = target_core;
	cpu_set_arg.process_rank = process_rank;
	cpu_set_arg.mcexec_linux_numa = mcexec_linux_numa;
	cpu_set_arg.mcexec_cpu_set = &mcexec_partition_cpu_set_storage;
	cpu_set_arg.mcexec_cpu_set_size =
		sizeof(mcexec_partition_cpu_set_storage);
	cpu_set_arg.ikc_mapped = ikc_mapped;

	/* Fugaku specific: Fujitsu CPU binding */
	if (getenv("FLIB_AFFINITY_ON_PROCESS")) {
		cpu_set_arg.req_cpu_list =
			getenv("FLIB_AFFINITY_ON_PROCESS");
		cpu_set_arg.req_cpu_list_len =
			strlen(cpu_set_arg.req_cpu_list) + 1;
		__dprintf("%s: requesting CPUs: %s\n",
			"main", cpu_set_arg.req_cpu_list);
	}

	return ioctl(fd, MCEXEC_UP_GET_CPUSET, (void *)&cpu_set_arg);
}

void mcexec_partition_get_cpuset_failed_bridge(void)
{
	perror("getting CPU set for partitioned execution");
	close(fd);
}

void mcexec_partition_publish_cpu_rank_bridge(struct program_load_desc *desc,
		int target_core, int process_rank)
{
	desc->cpu = target_core;
	desc->process_rank = process_rank;
}

void mcexec_partition_publish_rank_bridge(struct program_load_desc *desc,
		int process_rank)
{
	desc->process_rank = process_rank;
}

void mcexec_partition_rank_log_bridge(int process_rank, int target_core)
{
	__dprintf("%s: rank: %d, target CPU: %d\n",
		"main", process_rank, target_core);
}

int mcexec_partition_sched_setaffinity_bridge(void)
{
	return sched_setaffinity(0, sizeof(mcexec_partition_cpu_set_storage),
			&mcexec_partition_cpu_set_storage);
}

void mcexec_partition_sched_setaffinity_warning_bridge(void)
{
	__dprintf("WARNING: couldn't bind to mcexec_cpu_set\n");
}

void mcexec_partition_debug_ikc_binding_bridge(void)
{
#ifdef DEBUG
	int i;

	for (i = 0; i < numa_num_possible_cpus(); ++i) {
		if (CPU_ISSET(i, &mcexec_partition_cpu_set_storage)) {
			__dprintf("PID %d bound to CPU %d\n",
				getpid(), i);
		}
	}
#endif
}

int mcexec_partition_numa_run_bridge(int mcexec_linux_numa)
{
	return numa_run_on_node(mcexec_linux_numa);
}

void mcexec_partition_numa_run_warning_bridge(int mcexec_linux_numa)
{
	__dprintf("WARNING: couldn't bind to NUMA %d\n",
			mcexec_linux_numa);
}

void mcexec_partition_debug_numa_binding_bridge(void)
{
#ifdef DEBUG
	int i;
	cpu_set_t cpuset;
	char affinity[BUFSIZ];

	CPU_ZERO(&cpuset);
	if ((sched_getaffinity(0, sizeof(cpu_set_t), &cpuset)) != 0) {
		perror("Error sched_getaffinity");
		exit(1);
	}

	affinity[0] = '\0';
	for (i = 0; i < 512; i++) {
		if (CPU_ISSET(i, &cpuset) == 1) {
			sprintf(affinity, "%s %d", affinity, i);
		}
	}
	__dprintf("PID: %d affinity: %s\n",
			getpid(), affinity);
#endif
}

#define numa_local(localset, nodemask) \
	mcexec_numa_local_body((unsigned long *)(localset), (nodemask), 0)
#define numa_nonlocal(localset, nodemask) \
	mcexec_numa_local_body((unsigned long *)(localset), (nodemask), 1)
#define numa_all(nodemask) mcexec_numa_all_body(nodemask)

void mcexec_desc_publish_mpol_base_bridge(struct program_load_desc *desc,
		int profile_arg, int nr_processes_arg, unsigned long flags,
		unsigned long threshold, unsigned long heap_ext,
		int pld_mpol_max)
{
	desc->profile = profile_arg;
	desc->nr_processes = nr_processes_arg;
	desc->mpol_flags = flags;
	desc->mpol_threshold = threshold;
	desc->heap_extension = heap_ext;
	desc->mpol_bind_mask = 0;
	desc->mpol_mode = pld_mpol_max;
}

void mcexec_desc_apply_bind_nodes_bridge(struct program_load_desc *desc,
		const char *nodes)
{
	struct bitmask *bind_mask;

	bind_mask = numa_parse_nodestring_all(nodes);
	if (bind_mask) {
		int node;

		for (node = 0; node <= numa_max_possible_node(); ++node) {
			if (numa_bitmask_isbitset(bind_mask, node)) {
				desc->mpol_bind_mask |= (1UL << node);
			}
		}
	}
}

void mcexec_desc_ompi_policy_log_bridge(const char *mpol)
{
	__dprintf("OMPI_MCA_plm_ple_memory_allocation_policy: %s\n",
		  mpol);
}

void mcexec_desc_apply_ompi_policy_bridge(struct program_load_desc *desc,
		int mode, int nodemask_action)
{
	desc->mpol_mode = mode;
	if (nodemask_action == 1) {
		numa_local(desc->cpu_set, desc->mpol_nodemask);
	}
	else if (nodemask_action == 2) {
		numa_nonlocal(desc->cpu_set, desc->mpol_nodemask);
	}
	else if (nodemask_action == 3) {
		numa_all(desc->mpol_nodemask);
	}
}

void mcexec_desc_mpol_log_bridge(const struct program_load_desc *desc)
{
	__dprintf("mpol_mode: %d, mpol_nodemask: %ld\n",
		  desc->mpol_mode, desc->mpol_nodemask[0]);
}

void mcexec_desc_publish_runtime_flags_bridge(struct program_load_desc *desc,
		int enable_uti_arg, int uti_thread_rank_arg,
		int uti_use_last_cpu_arg, int thp_disable_arg,
		int straight_map_arg, unsigned long straight_map_threshold_arg,
		int enable_tofu_arg, unsigned long mcexec_flags_arg)
{
	desc->enable_uti = enable_uti_arg;
	desc->uti_thread_rank = uti_thread_rank_arg;
	desc->uti_use_last_cpu = uti_use_last_cpu_arg;
	desc->thp_disable = thp_disable_arg;
	desc->straight_map = straight_map_arg;
	desc->straight_map_threshold = straight_map_threshold_arg;
#ifdef ENABLE_TOFU
	desc->enable_tofu = enable_tofu_arg;
#else
	(void)enable_tofu_arg;
#endif
	if (mcexec_flags_arg) {
		desc->mcexec_flags = mcexec_flags_arg;
	}
}
#else
static inline void _numa_local(__cpu_set_unit *localset,
			       unsigned long *nodemask, int nonlocal)
{
	int i;

	memset(nodemask, 0, PLD_PROCESS_NUMA_MASK_BITS / 8);

	for (i = 0; i < nnodes; i++) {
		cpu_set_t *nodeset = numa_node_set(i);
		int j;

		if (nonlocal) {
			set_bit(i, nodemask);
		}

		for (j = 0; j < ncpu; j++) {
			if (test_bit(j, localset)) {
				__dprintf("%d belongs to local set\n", j);
			}

			if (CPU_ISSET_S(j, cpu_set_size, nodeset)) {
				__dprintf("%d belongs to node %d\n", j, i);
			}

			if (test_bit(j, localset) &&
			    CPU_ISSET_S(j, cpu_set_size, nodeset)) {
				if (nonlocal) {
					clear_bit(i, nodemask);
				} else {
					set_bit(i, nodemask);
				}
			}
		}
	}
}

static inline void numa_local(__cpu_set_unit *localset, unsigned long *nodemask)
{
	_numa_local(localset, nodemask, 0);
}

static inline void numa_nonlocal(__cpu_set_unit *localset,
				 unsigned long *nodemask)
{
	_numa_local(localset, nodemask, 1);
}

static inline void numa_all(unsigned long *nodemask)
{
	int i;

	memset(nodemask, 0, PLD_PROCESS_NUMA_MASK_BITS / 8);

	for (i = 0; i < nnodes; i++) {
		set_bit(i, nodemask);
	}
}
#endif

pid_t master_tid;

pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
pthread_barrier_t init_ready;
pthread_barrier_t uti_init_ready;

#ifdef MCEXEC_RUST_HELPERS
#define main_loop_thread_func mcexec_main_loop_thread_func_body
#else
static void *main_loop_thread_func(void *arg)
{
	struct thread_data_s *td = (struct thread_data_s *)arg;

	td->tid = gettid();
	td->remote_tid = -1;
	if (td->init_ready)
		pthread_barrier_wait(td->init_ready);
	td->ret = main_loop(td);

	return NULL;
}
#endif

#define LOCALSIG SIGURG

#ifndef MCEXEC_RUST_HELPERS
void
sendsig(int sig, siginfo_t *siginfo, void *context)
{
	pid_t	pid;
	pid_t	tid;
	int	remote_tid;
	int	cpu;
	struct signal_desc sigdesc;
	struct thread_data_s *tp;
	int not_uti;

	not_uti = ioctl(fd, MCEXEC_UP_SIG_THREAD, 1);
	pid = getpid();
	tid = gettid();
	if (siginfo->si_pid == pid &&
	    siginfo->si_signo == LOCALSIG)
		goto out;

	if (siginfo->si_signo == SIGCHLD)
		goto out;

	for (tp = thread_data; tp; tp = tp->next) {
		if (siginfo->si_pid == pid &&
		    tp->tid == tid) {
			if (tp->terminate)
				goto out;
			break;
		}
		if (siginfo->si_pid != pid &&
		    tp->remote_tid == tid) {
			if (tp->terminate)
				goto out;
			break;
		}
	}
	if (tp) {
		remote_tid = tp->remote_tid;
		cpu = tp->remote_cpu;
	}
	else {
		cpu = 0;
		remote_tid = -1;
	}

	if (not_uti) { /* target isn't uti thread, ask McKernel to call the handler */
		memset(&sigdesc, '\0', sizeof sigdesc);
		sigdesc.cpu = cpu;
		sigdesc.pid = (int)pid;
		sigdesc.tid = remote_tid;
		sigdesc.sig = sig;
		memcpy(&sigdesc.info, siginfo, 128);
		if (ioctl(fd, MCEXEC_UP_SEND_SIGNAL, &sigdesc) != 0) {
			close(fd);
			exit(1);
		}
	}
	else { /* target is uti thread, mcexec calls the handler */
		struct syscall_struct param;
		int rc;

		param.number = SYS_rt_sigaction;
		param.args[0] = sig;
		rc = ioctl(fd, MCEXEC_UP_SYSCALL_THREAD, &param);
		if (rc == -1);
		else if (param.ret == (unsigned long)SIG_IGN);
		else if (param.ret == (unsigned long)SIG_DFL) {
			if (sig != SIGCHLD && sig != SIGURG && sig != SIGCONT) {
				signal(sig, SIG_DFL);
				kill(getpid(), sig);
				for(;;)
					sleep(1);
			}
		}
		else {
			ioctl(fd, MCEXEC_UP_SIG_THREAD, 0);
			((void (*)(int, siginfo_t *, void *))param.ret)(sig,
			                                      siginfo, context);
			ioctl(fd, MCEXEC_UP_SIG_THREAD, 1);
		}
	}
out:
	if (!not_uti)
		ioctl(fd, MCEXEC_UP_SIG_THREAD, 0);
}
#else
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
#endif

#ifndef MCEXEC_RUST_HELPERS
long
act_signalfd4(struct syscall_wait_desc *w)
{
	struct sigfd *sfd;
	struct sigfd *sb;
	int mode = w->sr.args[0];
	int flags;
	int tmp;
	int rc = 0;
	struct signalfd_siginfo *info;

	switch(mode){
	    case 0: /* new signalfd */
		sfd = malloc(sizeof(struct sigfd));
		memset(sfd, '\0', sizeof(struct sigfd));
		tmp = w->sr.args[1];
		flags = 0;
		if(tmp & SFD_NONBLOCK)
			flags |= O_NONBLOCK;
		if(tmp & SFD_CLOEXEC)
			flags |= O_CLOEXEC;
		if (pipe2(sfd->sigpipe, flags) < 0) {
			perror("pipe2 failed:");
			return -1;
		}
		sfd->next = sigfdtop;
		sigfdtop = sfd;
		rc = sfd->sigpipe[0];
		break;
	    case 1: /* close signalfd */
		tmp = w->sr.args[1];
		for(sfd = sigfdtop, sb = NULL; sfd; sb = sfd, sfd = sfd->next)
			if(sfd->sigpipe[0] == tmp)
				break;
		if(!sfd)
			rc = -EBADF;
		else{
			if(sb)
				sb->next = sfd->next;
			else
				sigfdtop = sfd->next;
			close(sfd->sigpipe[0]);
			close(sfd->sigpipe[1]);
			free(sfd);
		}
		break;
	    case 2: /* push signal */
		tmp = w->sr.args[1];
		for(sfd = sigfdtop; sfd; sfd = sfd->next)
			if(sfd->sigpipe[0] == tmp)
				break;
		if(!sfd)
			rc = -EBADF;
		else{
			info = (struct signalfd_siginfo *)w->sr.args[2];
			if (write(sfd->sigpipe[1], info, sizeof(struct signalfd_siginfo))
					!= sizeof(struct signalfd_siginfo)) {
				fprintf(stderr, "error: writing sigpipe\n");
				rc = -EBADF;
			}
		}
		break;
	}
	return rc;
}
#else
ssize_t mcexec_act_signalfd4_write_bridge(int fd, const void *info,
		size_t len)
{
	return write(fd, info, len);
}

void mcexec_act_signalfd4_write_error_bridge(void)
{
	fprintf(stderr, "error: writing sigpipe\n");
}
#endif

#ifdef MCEXEC_RUST_HELPERS
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

long mcexec_path_readlinkat_bridge(int dirfd, const char *path,
		char *buf, size_t size)
{
	long ret;

	ret = readlinkat(dirfd, path, buf, size);
	SET_ERR(ret);
	__dprintf("readlinkat: dirfd=%d, path=%s, buf=%s, ret=%ld\n",
		dirfd, path, buf, ret);
	return ret;
}

long mcexec_path_readlink_bridge(const char *path, char *buf, size_t size)
{
	long ret;

	ret = readlink(path, buf, size);
	SET_ERR(ret);
	__dprintf("readlink: path=%s, buf=%s, ret=%ld\n", path, buf, ret);
	return ret;
}

long mcexec_path_fstatat_bridge(int dirfd, const char *path,
		void *statbuf, int flags)
{
	long ret;

	ret = fstatat(dirfd, path, statbuf, flags);
	SET_ERR(ret);
	__dprintf("fstatat: dirfd=%d, pathname=%s, buf=%p, flags=%x, ret=%ld\n",
		  dirfd, path, statbuf, flags, ret);
	return ret;
}

long mcexec_path_stat_bridge(const char *path, void *statbuf)
{
	long ret;

	ret = stat(path, statbuf);
	SET_ERR(ret);
	__dprintf("stat: path=%s, ret=%ld\n", path, ret);
	return ret;
}

long mcexec_path_faccessat_bridge(int dirfd, const char *path,
		int mode, int flags)
{
	long ret;

	ret = faccessat(dirfd, path, mode, flags);
	SET_ERR(ret);
	__dprintf("faccessat: dirfd=%d, pathname=%s, mode=%d, ret=%ld\n",
		  dirfd, path, mode, ret);
	return ret;
}

long mcexec_path_access_bridge(const char *path, int mode)
{
	long ret;

	ret = access(path, mode);
	SET_ERR(ret);
	__dprintf("access: path=%s, ret=%ld\n", path, ret);
	return ret;
}

long mcexec_path_getxattr_bridge(const char *path, const char *name,
		void *value, size_t size)
{
	long ret;

	ret = getxattr(path, name, value, size);
	SET_ERR(ret);
	__dprintf("getxattr: path=%s, name=%s, ret=%ld\n", path, name, ret);
	return ret;
}

long mcexec_path_lgetxattr_bridge(const char *path, const char *name,
		void *value, size_t size)
{
	long ret;

	ret = lgetxattr(path, name, value, size);
	SET_ERR(ret);
	__dprintf("lgetxattr: path=%s, name=%s, ret=%ld\n", path, name, ret);
	return ret;
}

void mcexec_path_openat_log_bridge(int dirfd, const char *path, int tid)
{
	__dprintf("openat: %d, %s,tid=%d\n", dirfd, path, tid);
}

void mcexec_path_open_log_bridge(const char *path)
{
	__dprintf("open: %s\n", path);
}

long mcexec_path_openat_bridge(int dirfd, const char *path,
		unsigned long flags, unsigned long mode)
{
	long ret;

	ret = openat(dirfd, path, flags, mode);
	SET_ERR(ret);
	return ret;
}

long mcexec_path_open_bridge(const char *path, unsigned long flags,
		unsigned long mode)
{
	long ret;

	ret = open(path, flags, mode);
	SET_ERR(ret);
	return ret;
}

void mcexec_cred_get_bridge(int mcos_fd, unsigned long arg)
{
	ioctl(mcos_fd, MCEXEC_UP_GET_CRED, arg);
}

long mcexec_cred_setfsuid_bridge(unsigned long uid)
{
	return setfsuid(uid);
}

long mcexec_cred_setresuid_bridge(unsigned long ruid,
		unsigned long euid, unsigned long suid)
{
	long ret;

	ret = setresuid(ruid, euid, suid);
	SET_ERR(ret);
	return ret;
}

long mcexec_cred_setreuid_bridge(unsigned long ruid, unsigned long euid)
{
	long ret;

	ret = setreuid(ruid, euid);
	SET_ERR(ret);
	return ret;
}

long mcexec_cred_setuid_bridge(unsigned long uid)
{
	long ret;

	ret = setuid(uid);
	SET_ERR(ret);
	return ret;
}

long mcexec_cred_setresgid_bridge(unsigned long rgid,
		unsigned long egid, unsigned long sgid)
{
	long ret;

	ret = setresgid(rgid, egid, sgid);
	SET_ERR(ret);
	return ret;
}

long mcexec_cred_setregid_bridge(unsigned long rgid, unsigned long egid)
{
	long ret;

	ret = setregid(rgid, egid);
	SET_ERR(ret);
	return ret;
}

long mcexec_cred_setgid_bridge(unsigned long gid)
{
	long ret;

	ret = setgid(gid);
	SET_ERR(ret);
	return ret;
}

long mcexec_cred_setfsgid_bridge(unsigned long gid)
{
	return setfsgid(gid);
}
#else
void
act_sigaction(struct syscall_wait_desc *w)
{
	struct sigaction act;
	int sig;

	sig = w->sr.args[0];
	if (sig == SIGCHLD || sig == LOCALSIG)
		return;
	memset(&act, '\0', sizeof act);
	if (w->sr.args[1] == (unsigned long)SIG_IGN)
		act.sa_handler = SIG_IGN;
	else{
		act.sa_sigaction = sendsig;
		act.sa_flags = SA_SIGINFO;
	}
	sigaction(sig, &act, NULL);
}

void
act_sigprocmask(struct syscall_wait_desc *w)
{
	sigset_t set;

	sigemptyset(&set);
	memcpy(&set, &w->sr.args[0], sizeof(unsigned long));
	sigdelset(&set, LOCALSIG);
	sigprocmask(SIG_SETMASK, &set, NULL);
}
#endif

#define DO_NOT_OVERWRITE 0
#define MCEXEC_STACK_SIZE (10 * 1024 * 1024)	/* 10 MiB */

#ifdef MCEXEC_RUST_HELPERS
int mcexec_main_load_stack_rlimit_bridge(unsigned long *cur,
		unsigned long *max)
{
	if (getrlimit(RLIMIT_STACK, &rlim_stack)) {
		fprintf(stderr, "getrlimit failed\n");
		return 1;
	}
	*cur = rlim_stack.rlim_cur;
	*max = rlim_stack.rlim_max;
	__dprintf("rlim_stack=%ld,%ld\n", rlim_stack.rlim_cur,
			rlim_stack.rlim_max);
	return 0;
}

void mcexec_main_reduce_stack_failed_bridge(void)
{
	fprintf(stderr, "Error: Failed to reduce stack.\n");
}

void mcexec_reduce_stack_newval_overflow_bridge(void)
{
	__eprintf("snprintf(%s):buffer overflow\n", rlimit_stack_envname);
}

int mcexec_reduce_stack_setenv_bridge(const char *newval)
{
	return setenv(rlimit_stack_envname, newval, DO_NOT_OVERWRITE);
}

void mcexec_reduce_stack_setenv_failed_bridge(void)
{
	__eprintf("failed to setenv(%s)\n", rlimit_stack_envname);
}

int mcexec_reduce_stack_setrlimit_bridge(unsigned long cur, unsigned long max)
{
	struct rlimit new_rlim;

	new_rlim.rlim_cur = cur;
	new_rlim.rlim_max = max;
	return setrlimit(RLIMIT_STACK, &new_rlim);
}

void mcexec_reduce_stack_setrlimit_failed_bridge(void)
{
	__eprintf("failed to setrlimit(RLIMIT_STACK)\n");
}

ssize_t mcexec_reduce_stack_readlink_bridge(char *path, size_t size)
{
	return readlink("/proc/self/exe", path, size);
}

void mcexec_reduce_stack_readlink_failed_bridge(void)
{
	__eprintf("Could not readlink /proc/self/exe? %m\n");
}

int mcexec_reduce_stack_execv_bridge(const char *path, char **argv)
{
	return execv(path, argv);
}

void mcexec_reduce_stack_execv_failed_bridge(void)
{
	__eprintf("failed to execv(myself)\n");
}

#define reduce_stack(orig_rlim, argv) \
	mcexec_reduce_stack_body((orig_rlim)->rlim_cur, (orig_rlim)->rlim_max, \
			(argv))
#else
static int reduce_stack(struct rlimit *orig_rlim, char *argv[])
{
	int n;
	char newval[40];
	char path[PATH_MAX];
	int error;
	struct rlimit new_rlim;

	/* save original value to environment variable */
	n = snprintf(newval, sizeof(newval), "%ld,%ld",
			(unsigned long)orig_rlim->rlim_cur,
			(unsigned long)orig_rlim->rlim_max);
	if (n >= sizeof(newval)) {
		__eprintf("snprintf(%s):buffer overflow\n",
				rlimit_stack_envname);
		return 1;
	}

	error = setenv(rlimit_stack_envname, newval, DO_NOT_OVERWRITE);
	if (error) {
		__eprintf("failed to setenv(%s)\n", rlimit_stack_envname);
		return 1;
	}

	/* exec() myself with small stack */
	new_rlim.rlim_cur = MCEXEC_STACK_SIZE;
	new_rlim.rlim_max = orig_rlim->rlim_max;

	error = setrlimit(RLIMIT_STACK, &new_rlim);
	if (error) {
		__eprintf("failed to setrlimit(RLIMIT_STACK)\n");
		return 1;
	}

	error = readlink("/proc/self/exe", path, sizeof(path));
	if (error < 0) {
		__eprintf("Could not readlink /proc/self/exe? %m\n");
		return 1;
	} else if (error >= sizeof(path)) {
#ifdef MCEXEC_RUST_HELPERS
		if (mcexec_copy_path_result("/proc/self/exe", path,
					sizeof(path)) < 0) {
			return 1;
		}
#else
		strcpy(path, "/proc/self/exe");
#endif
	} else {
		path[error] = '\0';
	}

	execv(path, argv);

	__eprintf("failed to execv(myself)\n");
	return 1;
}
#endif

#ifdef MCEXEC_RUST_HELPERS
int mcexec_print_usage_add_envs_bridge(void)
{
#ifdef ADD_ENVS_OPTION
	return 1;
#else
	return 0;
#endif
}

void mcexec_print_usage_write_bridge(const char *line, size_t len)
{
	fwrite(line, 1, len, stderr);
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

void mcexec_exit_cmd_servers_bridge(void)
{
#ifdef USE_SYSCALL_MOD_CALL
#ifdef CMD_DCFA
	ibmic_cmd_server_exit();
#endif

#ifdef CMD_DCFAMPI
	dcfampi_cmd_server_exit();
#endif
	mc_cmd_server_exit();
	__dprintf("mccmd server exited\n");
#endif
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

void mcexec_execve2_alloc_desc_failed_bridge(void)
{
	fprintf(stderr, "execve(): error allocating desc\n");
}

void mcexec_execve2_transfer_desc_failed_bridge(void)
{
	fprintf(stderr, "execve(): error obtaining ELF descriptor\n");
}

void mcexec_execve2_transfer_desc_ok_bridge(void)
{
	__dprintf("%s", "execve(): transfer ELF desc OK\n");
}

void mcexec_execve2_transfer_image_failed_bridge(void)
{
	fprintf(stderr, "error: transferring image\n");
}

void mcexec_execve2_image_transferred_bridge(void)
{
	__dprintf("%s", "execve(): image transferred\n");
}

void mcexec_execve2_close_exec_failed_bridge(int ret)
{
	fprintf(stderr, "error: MCEXEC_UP_CLOSE_EXEC failed with %d\n", ret);
}

void mcexec_main_prepare_image_failed_bridge(void)
{
	perror("prepare");
	close(fd);
}

void mcexec_main_flush_bridge(void)
{
	fflush(stdout);
	fflush(stderr);
}

int mcexec_main_cmd_servers_init_bridge(void)
{
#ifdef USE_SYSCALL_MOD_CALL
	if(mc_cmd_server_init()){
		fprintf(stderr, "Error: cmd server init failed\n");
		return 1;
	}

#ifdef CMD_DCFA
	if(ibmic_cmd_server_init()){
		fprintf(stderr, "Error: Failed to initialize ibmic_cmd_server.\n");
		return -1;
	}
#endif

#ifdef CMD_DCFAMPI
	if(dcfampi_cmd_server_init()){
		fprintf(stderr, "Error: Failed to initialize dcfampi_cmd_server.\n");
		return -1;
	}
#endif
	__dprintf("mccmd server initialized\n");
#endif

	return 0;
}

void mcexec_main_worker_threads_failed_bridge(int error)
{
	fprintf(stderr, "%s: Error: creating worker threads: %s\n",
			"main", strerror(-error));
	close(fd);
}

void mcexec_main_start_image_failed_bridge(void)
{
	perror("exec");
	close(fd);
}

void mcexec_flib_affinity_alloc_failed_bridge(void)
{
	fprintf(stderr, "error: allocating memory for "
			"FLIB_AFFINITY_ON_PROCESS\n");
	exit(EXIT_FAILURE);
}

void mcexec_flib_affinity_log_bridge(const char *old_affinity,
		const char *new_affinity)
{
	__dprintf("FLIB_AFFINITY_ON_PROCESS: %s -> %s\n",
			old_affinity, new_affinity);
}

void mcexec_main_stack_parse_failed_bridge(int parse_rc)
{
	fprintf(stderr, "Error: Failed to parse %s %d\n",
			rlimit_stack_envname, parse_rc);
}

int mcexec_execve1_enable_vdso_bridge(void)
{
	return enable_vdso;
}

unsigned long mcexec_execve1_rlim_cur_bridge(void)
{
	return rlim_stack.rlim_cur;
}

unsigned long mcexec_execve1_rlim_max_bridge(void)
{
	return rlim_stack.rlim_max;
}

long mcexec_execve1_stack_premap_bridge(void)
{
	return stack_premap;
}

void mcexec_desc_set_execve1_runtime_bridge(struct program_load_desc *desc,
		int vdso, unsigned long rlim_cur, unsigned long rlim_max,
		long prem)
{
	desc->enable_vdso = vdso;
	desc->rlimit[RLIMIT_STACK].rlim_cur = rlim_cur;
	desc->rlimit[RLIMIT_STACK].rlim_max = rlim_max;
	desc->stack_premap = prem;
}

void mcexec_desc_set_args_len_bridge(struct program_load_desc *desc,
		unsigned long args_len)
{
	desc->args_len = args_len;
}

void mcexec_execve1_load_desc_ok_bridge(const char *filename, int sections)
{
	__dprintf("execve(): load_elf_desc() for %s OK, num sections: %d\n",
			filename, sections);
}

void mcexec_execve1_transfer_alloc_failed_bridge(const char *filename)
{
	fprintf(stderr,
		"execve(): could not alloc transfer buffer for file %s\n",
		filename);
}

void mcexec_execve1_transfer_failed_bridge(const char *filename)
{
	fprintf(stderr, "execve(): error transfering ELF for file %s\n",
			filename);
}

void mcexec_execve1_transfer_ok_bridge(const char *filename)
{
	__dprintf("execve(): load_elf_desc() for %s OK\n", filename);
}

void mcexec_execve_invalid_phase_bridge(void)
{
	fprintf(stderr, "execve(): ERROR: invalid execve phase\n");
}

void mcexec_main_loop_log_syscall_bridge(int cpu, long number)
{
	__dprintf("[%d] got syscall: %ld\n", cpu, number);
}

void mcexec_main_loop_timeout_bridge(void)
{
	__dprintf("timed out.\n");
}

int mcexec_main_loop_thread_barrier_wait_bridge(void *barrier)
{
	return pthread_barrier_wait((pthread_barrier_t *)barrier);
}

int mcexec_main_loop_is_child_bridge(void)
{
	return ischild;
}
#else
void print_usage(char **argv)
{
#ifdef ADD_ENVS_OPTION
	fprintf(stderr, "usage: %s [-c target_core] [-n nr_partitions] [<-e ENV_NAME=value>...] [--mpol-threshold=N] [--enable-straight-map] [--extend-heap-by=N] [-s (--stack-premap=)[premap_size][,max]] [--mpol-no-heap] [--mpol-no-bss] [--mpol-no-stack] [--mpol-shm-premap] [--disable-sched-yield] [--enable-uti] [--uti-thread-rank=N] [--uti-use-last-cpu] [<mcos-id>] (program) [args...]\n", argv[0]);
#else /* ADD_ENVS_OPTION */
	fprintf(stderr, "usage: %s [-c target_core] [-n nr_partitions] [--mpol-threshold=N] [--enable-straight-map] [--extend-heap-by=N] [-s (--stack-premap=)[premap_size][,max]] [--mpol-no-heap] [--mpol-no-bss] [--mpol-no-stack] [--mpol-shm-premap] [--disable-sched-yield]  [--enable-uti] [--uti-thread-rank=N] [--uti-use-last-cpu] [<mcos-id>] (program) [args...]\n", argv[0]);
#endif /* ADD_ENVS_OPTION */
}
#endif

#ifdef MCEXEC_RUST_HELPERS
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
#else
void init_sigaction(void)
{
	int i;

	master_tid = gettid();
	for (i = 1; i <= 64; i++) {
		if (i != SIGKILL && i != SIGSTOP && i != SIGCHLD &&
				i != SIGTSTP && i != SIGTTIN && i != SIGTTOU) {
			struct sigaction act;

			sigaction(i, NULL, &act);
			act.sa_sigaction = sendsig;
			act.sa_flags &= ~(SA_RESTART);
			act.sa_flags |= SA_SIGINFO;
			sigaction(i, &act, NULL);
		}
	}
}
#endif

static int max_cpuid;

#ifdef MCEXEC_RUST_HELPERS
void *mcexec_create_worker_thread_alloc_bridge(void)
{
	return malloc(sizeof(struct thread_data_s));
}

void mcexec_create_worker_thread_alloc_error_bridge(void)
{
	fprintf(stderr, "%s: error: allocating thread structure\n",
		"create_worker_thread");
}

int mcexec_create_worker_thread_next_cpu_bridge(void)
{
	return max_cpuid++;
}

void *mcexec_create_worker_thread_lock_bridge(void)
{
	return &lock;
}

void mcexec_create_worker_thread_publish_bridge(struct thread_data_s *tp,
		struct thread_data_s **tp_out)
{
	tp->next = thread_data;
	thread_data = tp;

	if (tp_out) {
		*tp_out = tp;
	}
}

int mcexec_create_worker_thread_pthread_create_bridge(struct thread_data_s *tp)
{
	return pthread_create(&tp->thread_id, NULL,
			      &main_loop_thread_func, tp);
}

#define create_worker_thread(tp_out, init_ready) \
	mcexec_create_worker_thread_body((tp_out), (init_ready))
#else
static int create_worker_thread(struct thread_data_s **tp_out, pthread_barrier_t *init_ready)
{
	struct thread_data_s *tp;

	tp = malloc(sizeof(struct thread_data_s));
	if (!tp) {
		fprintf(stderr, "%s: error: allocating thread structure\n",
			__FUNCTION__);
		return ENOMEM;
	}
	memset(tp, '\0', sizeof(struct thread_data_s));
	tp->cpu = max_cpuid++;
	tp->lock = &lock;
	tp->init_ready = init_ready;
	tp->terminate = 0;
	tp->next = thread_data;
	thread_data = tp;

	if (tp_out) {
		*tp_out = tp;
	}

	return pthread_create(&tp->thread_id, NULL, 
	                      &main_loop_thread_func, tp);
}
#endif

#ifndef MCEXEC_RUST_HELPERS
int init_worker_threads(int fd)
{
	int i;

	pthread_mutex_init(&lock, NULL);
	pthread_barrier_init(&init_ready, NULL, n_threads + 2);

	max_cpuid = 0;
	for (i = 0; i <= n_threads; ++i) {
		int ret = create_worker_thread(NULL, &init_ready);

		if (ret) {
			printf("ERROR: creating worker threads (%d), check ulimit?\n",
			       ret);
			return -ret;
		}
	}

	pthread_barrier_wait(&init_ready);
	return 0;
}
#else
void mcexec_init_worker_threads_lock_init_bridge(void)
{
	pthread_mutex_init(&lock, NULL);
}

void mcexec_init_worker_threads_barrier_init_bridge(int count)
{
	pthread_barrier_init(&init_ready, NULL, count);
}

void mcexec_init_worker_threads_reset_cpuid_bridge(void)
{
	max_cpuid = 0;
}

int mcexec_init_worker_threads_create_bridge(void)
{
	return create_worker_thread(NULL, &init_ready);
}

void mcexec_init_worker_threads_wait_bridge(void)
{
	pthread_barrier_wait(&init_ready);
}

void mcexec_init_worker_threads_error_bridge(int ret)
{
	printf("ERROR: creating worker threads (%d), check ulimit?\n", ret);
}
#endif

#define MCK_RLIMIT_AS	0
#define MCK_RLIMIT_CORE	1
#define MCK_RLIMIT_CPU	2
#define MCK_RLIMIT_DATA	3
#define MCK_RLIMIT_FSIZE	4
#define MCK_RLIMIT_LOCKS	5
#define MCK_RLIMIT_MEMLOCK	6
#define MCK_RLIMIT_MSGQUEUE	7
#define MCK_RLIMIT_NICE	8
#define MCK_RLIMIT_NOFILE	9
#define MCK_RLIMIT_NPROC	10
#define MCK_RLIMIT_RSS	11
#define MCK_RLIMIT_RTPRIO	12
#define MCK_RLIMIT_RTTIME	13
#define MCK_RLIMIT_SIGPENDING	14
#define MCK_RLIMIT_STACK	15

#ifdef MCEXEC_RUST_HELPERS
void mcexec_main_stack_publish_bridge(struct program_load_desc *desc,
		rlim_t cur, rlim_t max, long prem)
{
	desc->rlimit[MCK_RLIMIT_STACK].rlim_cur = cur;
	desc->rlimit[MCK_RLIMIT_STACK].rlim_max = max;
	desc->stack_premap = prem;
	__dprintf("desc->rlimit[MCK_RLIMIT_STACK]=%ld,%ld\n",
			desc->rlimit[MCK_RLIMIT_STACK].rlim_cur,
			desc->rlimit[MCK_RLIMIT_STACK].rlim_max);
}
#endif

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

#ifdef MCEXEC_RUST_HELPERS
void mcexec_desc_snapshot_rlimits_bridge(struct program_load_desc *desc)
{
	int i;

	for (i = 0; i < sizeof(rlimits) / sizeof(int); i += 2) {
		getrlimit(rlimits[i], &desc->rlimit[rlimits[i + 1]]);
	}
}

void mcexec_desc_publish_env_bridge(struct program_load_desc *desc,
		int envs_len, char *envs)
{
	desc->envs_len = envs_len;
	desc->envs = envs;
}

void mcexec_desc_publish_args_cpu_bridge(struct program_load_desc *desc,
		unsigned long args_len, char *args, int cpu, int vdso)
{
	desc->args_len = args_len;
	desc->args = args;
	desc->cpu = cpu;
	desc->enable_vdso = vdso;
}
#endif

char dev[64];

#ifdef ADD_ENVS_OPTION
struct env_list_entry {
	char* str;
	char* name;
	char* value;
	struct env_list_entry *next;
};

#ifdef MCEXEC_RUST_HELPERS
#define get_env_list_entry_count(head) mcexec_env_list_count_result(head)
#define search_env_list(head, name) \
	((struct env_list_entry *)mcexec_search_env_list_result((head), (name)))
#define add_env_list(head, add_string) \
	mcexec_add_env_list_body((head), (add_string))
#define destroy_env_list(head) mcexec_destroy_env_list_result(head)
#define create_local_environ(inc_list) \
	mcexec_create_local_environ_result(inc_list)
#define destroy_local_environ(local_env) \
	mcexec_destroy_local_environ_result(local_env)

void mcexec_add_env_list_invalid_bridge(const char *add_string)
{
	printf("\"%s\" is not env value.\n", add_string);
}
#else
static int get_env_list_entry_count(struct env_list_entry *head)
{
	int list_count = 0;
	struct env_list_entry *current = head;

	while (current) {
		list_count++;
		current = current->next;
	}
	return list_count;
}

static struct env_list_entry *search_env_list(struct env_list_entry *head, char *name)
{
	struct env_list_entry *current = head;

	while (current) {
		if (!(strcmp(name, current->name))) {
			return current;
		}
		current = current->next;
	}
	return NULL;
}

static void add_env_list(struct env_list_entry **head, char *add_string)
{
	struct env_list_entry *current = NULL;
	char *value = NULL;
	char *name = NULL;
	struct env_list_entry *exist = NULL;

	name = (char *)malloc(strlen(add_string) + 1);
	strcpy(name, add_string);

	/* include '=' ? */
	if (!(value = strchr(name, '='))) {
		printf("\"%s\" is not env value.\n", add_string);
		free(name);
		return;
	}
	*value = '\0';
	value++;

	/* name overlap serch */
	if (*head) {
		exist = search_env_list(*head, name);
		if (exist) {
			free(name);
			return;
		}
	}

	/* ADD env_list */
	current = (struct env_list_entry *)malloc(sizeof(struct env_list_entry));
	current->str = add_string;
	current->name = name;
	current->value = value;
	if (*head) {
		current->next = *head;
	} else {
		current->next = NULL;
	}
	*head = current;
	return;
}

static void destroy_env_list(struct env_list_entry *head)
{
	struct env_list_entry *current = head;
	struct env_list_entry *next = NULL;

	while (current) {
		next = current->next;
		free(current->name);
		free(current);
		current = next;
	}
}

static char **create_local_environ(struct env_list_entry *inc_list)
{
	int list_count = 0;
	int i = 0;
	struct env_list_entry *current = inc_list;
	char **local_env = NULL;

	list_count = get_env_list_entry_count(inc_list);
	local_env = (char **)malloc(sizeof(char **) * (list_count + 1));
	local_env[list_count] = NULL;

	while (current) {
		local_env[i] = (char *)malloc(strlen(current->str) + 1);
		strcpy(local_env[i], current->str);
		current = current->next;
		i++;
	}
	return local_env;
}

static void destroy_local_environ(char **local_env)
{
	int i = 0;

	if (!local_env) {
		return;
	}

	for (i = 0; local_env[i]; i++) {
		free(local_env[i]);
		local_env[i] = NULL;
	}
	free(local_env);
}
#endif
#endif /* ADD_ENVS_OPTION */

#ifdef MCEXEC_RUST_HELPERS
void mcexec_atobytes_set_errno_bridge(int value)
{
	errno = value;
}
#else
unsigned long atobytes(char *string)
{
	unsigned long mult = 1;
	unsigned long ret;
	char orig_postfix = 0;
	char *postfix;
	errno = ERANGE;

	if (!strlen(string)) {
		return 0;
	}

	postfix = &string[strlen(string) - 1];

	if (*postfix == 'k' || *postfix == 'K') {
		mult = 1024;
		orig_postfix = *postfix;
		*postfix = 0;
	}
	else if (*postfix == 'm' || *postfix == 'M') {
		mult = 1024 * 1024;
		orig_postfix = *postfix;
		*postfix = 0;
	}
	else if (*postfix == 'g' || *postfix == 'G') {
		mult = 1024 * 1024 * 1024;
		orig_postfix = *postfix;
		*postfix = 0;
	}

	ret = atol(string) * mult;
	if (orig_postfix)
		*postfix = orig_postfix;

	errno = 0;
	return ret;
}
#endif

static struct option mcexec_options[] = {
#ifndef __aarch64__
	{
		.name =		"disable-vdso",
		.has_arg =	no_argument,
		.flag =		&enable_vdso,
		.val =		0,
	},
	{
		.name =		"enable-vdso",
		.has_arg =	no_argument,
		.flag =		&enable_vdso,
		.val =		1,
	},
#endif /*__aarch64__*/
	{
		.name =		"profile",
		.has_arg =	no_argument,
		.flag =		&profile,
		.val =		1,
	},
	{
		.name =		"mpol-no-heap",
		.has_arg =	no_argument,
		.flag =		&mpol_no_heap,
		.val =		1,
	},
	{
		.name =		"mpol-no-stack",
		.has_arg =	no_argument,
		.flag =		&mpol_no_stack,
		.val =		1,
	},
	{
		.name =		"mpol-no-bss",
		.has_arg =	no_argument,
		.flag =		&mpol_no_bss,
		.val =		1,
	},
	{
		.name =		"mpol-shm-premap",
		.has_arg =	no_argument,
		.flag =		&mpol_shm_premap,
		.val =		1,
	},
	{
		.name =		"no-bind-ikc-map",
		.has_arg =	no_argument,
		.flag =		&no_bind_ikc_map,
		.val =		1,
	},
	{
		.name =		"mpol-threshold",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'M',
	},
	{
		.name =		"enable-straight-map",
		.has_arg =	no_argument,
		.flag =		&straight_map,
		.val =		1,
	},
	{
		.name =		"straight-map-threshold",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'S',
	},
	{
		.name =		"disable-sched-yield",
		.has_arg =	no_argument,
		.flag =		&disable_sched_yield,
		.val =		1,
	},
	{
		.name =		"extend-heap-by",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'h',
	},
	{
		.name =		"stack-premap",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		's',
	},
	{
		.name =		"uti-thread-rank",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'u',
	},
	{
		.name =		"uti-use-last-cpu",
		.has_arg =	no_argument,
		.flag =		&uti_use_last_cpu,
		.val =		1,
	},
	{
		.name =		"enable-uti",
		.has_arg =	no_argument,
		.flag =		&enable_uti,
		.val =		1,
	},
#ifdef ENABLE_TOFU
	{
		.name =		"enable-tofu",
		.has_arg =	no_argument,
		.flag =		&enable_tofu,
		.val =		1,
	},
#endif
	{
		.name =		"debug-mcexec",
		.has_arg =	no_argument,
		.flag =		&debug,
		.val =		1,
	},
	{
		.name =		"flags",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'f',
	},
	/* end */
	{ NULL, 0, NULL, 0, },
};

#ifdef MCEXEC_RUST_HELPERS
struct mcexec_main_state_ptrs {
	int *nr_processes;
	int *nr_threads;
	unsigned long *mpol_threshold;
	unsigned long *heap_extension;
	unsigned long *straight_map_threshold;
	long *stack_premap;
	long *stack_max;
	int *uti_thread_rank;
	unsigned long *mcexec_flags;
	char **mpol_bind_nodes;
	int *enable_uti;
	int *enable_vdso;
	int *profile;
	int *mpol_no_heap;
	int *mpol_no_stack;
	int *mpol_no_bss;
	int *mpol_shm_premap;
	int *no_bind_ikc_map;
	int *straight_map;
	int *uti_use_last_cpu;
	int *enable_tofu;
	rlim_t *rlim_cur;
	rlim_t *rlim_max;
};

extern int mcexec_main_body(int argc, char **argv);

void mcexec_main_publish_args_bridge(int argc, char **argv)
{
#ifdef USE_SYSCALL_MOD_CALL
	__glob_argc = argc;
	__glob_argv = argv;
#endif
}

void mcexec_main_state_ptrs_bridge(struct mcexec_main_state_ptrs *state)
{
	memset(state, 0, sizeof(*state));
	state->nr_processes = &nr_processes;
	state->nr_threads = &nr_threads;
	state->mpol_threshold = &mpol_threshold;
	state->heap_extension = &heap_extension;
	state->straight_map_threshold = &straight_map_threshold;
	state->stack_premap = &stack_premap;
	state->stack_max = &stack_max;
	state->uti_thread_rank = &uti_thread_rank;
	state->mcexec_flags = &mcexec_flags;
	state->mpol_bind_nodes = &mpol_bind_nodes;
	state->enable_uti = &enable_uti;
	state->enable_vdso = &enable_vdso;
	state->profile = &profile;
	state->mpol_no_heap = &mpol_no_heap;
	state->mpol_no_stack = &mpol_no_stack;
	state->mpol_no_bss = &mpol_no_bss;
	state->mpol_shm_premap = &mpol_shm_premap;
	state->no_bind_ikc_map = &no_bind_ikc_map;
	state->straight_map = &straight_map;
	state->uti_use_last_cpu = &uti_use_last_cpu;
#ifdef ENABLE_TOFU
	state->enable_tofu = &enable_tofu;
#endif
	state->rlim_cur = &rlim_stack.rlim_cur;
	state->rlim_max = &rlim_stack.rlim_max;
}

int mcexec_main_personality_bridge(char **argv)
{
	int persona;
	int error;
	char path[PATH_MAX];

	/* Disable READ_IMPLIES_EXEC */
	persona = personality(0xffffffff);
	if (persona & READ_IMPLIES_EXEC) {
		persona &= ~READ_IMPLIES_EXEC;
		persona = personality(persona);
	}

	/* Disable address space layout randomization */
	__dprintf("persona=%08x\n", persona);
	if ((persona & (PER_LINUX | ADDR_NO_RANDOMIZE)) == 0) {
		if (getenv("MCEXEC_ADDR_NO_RANDOMIZE")) {
			__eprintf("personality() and then execv() failed\n");
			return 1;
		}

		persona = personality(persona | PER_LINUX | ADDR_NO_RANDOMIZE);
		if (persona == -1) {
			__eprintf("personality failed, persona=%08x, strerror=%s\n",
				  persona, strerror(errno));
			return 1;
		}

		error = setenv("MCEXEC_ADDR_NO_RANDOMIZE", "1", 1);
		if (error == -1) {
			__eprintf("setenv failed\n");
			return 1;
		}

		error = readlink("/proc/self/exe", path, sizeof(path));
		if (error == -1) {
			__eprintf("readlink failed: %m\n");
			return 1;
		}
		if (error >= sizeof(path)) {
			strcpy(path, "/proc/self/exe");
		} else {
			path[error] = '\0';
		}

		error = execv(path, argv);
		if (error == -1) {
			__eprintf("execv failed, error=%d,strerror=%s\n",
				  error, strerror(errno));
			return 1;
		}
	}

	if (getenv("MCEXEC_ADDR_NO_RANDOMIZE")) {
		error = unsetenv("MCEXEC_ADDR_NO_RANDOMIZE");
		if (error == -1) {
			__eprintf("unsetenv failed");
			return 1;
		}
	}

	return 0;
}

int mcexec_main_next_option_bridge(int argc, char **argv)
{
#ifdef ADD_ENVS_OPTION
	return getopt_long(argc, argv, "+c:n:t:M:h:e:s:m:u:S:f:",
			   mcexec_options, NULL);
#else
	return getopt_long(argc, argv, "+c:n:t:M:h:s:m:u:S:f:",
			   mcexec_options, NULL);
#endif
}

char *mcexec_main_optarg_bridge(void)
{
	return optarg;
}

int mcexec_main_optind_bridge(void)
{
	return optind;
}

void mcexec_main_invalid_option_bridge(int opt, char **argv)
{
	switch (opt) {
	case 'c':
		fprintf(stderr, "error: -c: invalid target CPU\n");
		break;
	case 'n':
		fprintf(stderr, "error: -n: invalid number of processes\n");
		break;
	case 't':
		fprintf(stderr, "error: -t: invalid number of threads\n");
		break;
	default:
		print_usage(argv);
		break;
	}
	exit(EXIT_FAILURE);
}

void mcexec_main_stack_debug_bridge(long prem, long max)
{
	__dprintf("stack_premap=%ld,stack_max=%ld\n", prem, max);
}

void mcexec_main_thread_plan_error_bridge(void)
{
	fprintf(stderr, "error: nr_processes can't exceed nr. of CPUs\n");
}

int mcexec_main_bind_mount_bridge(void)
{
#ifdef MCEXEC_BIND_MOUNT
	int error;

	error = isunshare();
	if (error == 0) {
		struct sys_unshare_desc unshare_desc;
		struct sys_mount_desc mount_desc;
		struct sys_umount_desc umount_desc;

		/* Unshare mount namespace */
		memset(&unshare_desc, '\0', sizeof unshare_desc);
		memset(&mount_desc, '\0', sizeof mount_desc);
		unshare_desc.unshare_flags = CLONE_NEWNS;
		if (ioctl(fd, MCEXEC_UP_SYS_UNSHARE,
			(unsigned long)&unshare_desc) != 0) {
			fprintf(stderr, "Error: Failed to unshare. (%s)\n",
				strerror(errno));
			return 1;
		}

		/* Privatize mount namespace */
		mount_desc.dev_name = NULL;
		mount_desc.dir_name = "/";
		mount_desc.type = NULL;
		mount_desc.flags = MS_PRIVATE | MS_REC;
		mount_desc.data = NULL;
		if (ioctl(fd, MCEXEC_UP_SYS_MOUNT,
			(unsigned long)&mount_desc) != 0) {
			fprintf(stderr, "Error: Failed to privatize mounts. (%s)\n",
				strerror(errno));
			return 1;
		}

		// bind_mount_recursive(<root>, <prefix>);
		(void)umount_desc;
	} else if (error == -1) {
		return 1;
	}
#endif
	return 0;
}
#endif

#ifdef MCEXEC_BIND_MOUNT
/* bind-mount files under <root>/<prefix> over <prefix> recursively */
void bind_mount_recursive(const char *root, char *prefix)
{
	DIR *dir;
	struct dirent *entry;
	char path[PATH_MAX];

	snprintf(path, sizeof(path), "%s/%s", root, prefix);
	path[sizeof(path) - 1] = 0;

	if (!(dir = opendir(path))) {
		return;
	}

	while ((entry = readdir(dir))) {
		char fullpath[PATH_MAX];
		char shortpath[PATH_MAX];
		struct stat st;

		/* Use lstat instead of checking dt_type of readdir
		   result because the latter reports DT_UNKNOWN for
		   files on some file systems */
		snprintf(fullpath, sizeof(fullpath),
			       "%s/%s/%s", root, prefix, entry->d_name);
		fullpath[sizeof(fullpath) - 1] = 0;

		if (lstat(fullpath, &st)) {
			fprintf(stderr, "%s: error: lstat %s: %s\n",
				__func__, fullpath, strerror(errno));
			continue;
		}

		/* Traverse target or mount point */
		snprintf(shortpath, sizeof(shortpath),
			       "%s/%s", prefix, entry->d_name);
		shortpath[sizeof(shortpath) - 1] = 0;

		if (S_ISDIR(st.st_mode)) {
			__dprintf("dir found: %s\n", fullpath);

			if (strcmp(entry->d_name, ".") == 0 ||
					strcmp(entry->d_name, "..") == 0)
				continue;

			bind_mount_recursive(root, shortpath);
		}
		else if (S_ISREG(st.st_mode) || S_ISLNK(st.st_mode)) {
			int ret;
			struct sys_mount_desc mount_desc;

			__dprintf("reg/symlink found: %s\n", fullpath);

			if (lstat(shortpath, &st)) {
				fprintf(stderr, "%s: warning: lstat of mount point (%s) failed: %s\n",
					__func__, shortpath, strerror(errno));
				continue;
			}

			memset(&mount_desc, '\0', sizeof(mount_desc));
			mount_desc.dev_name = fullpath;
			mount_desc.dir_name = shortpath;
			mount_desc.type = NULL;
			mount_desc.flags = MS_BIND | MS_PRIVATE;
			mount_desc.data = NULL;

			if ((ret = ioctl(fd, MCEXEC_UP_SYS_MOUNT,
						(unsigned long)&mount_desc)) != 0) {
				fprintf(stderr, "%s: warning: failed to bind mount %s over %s: %d\n",
					__func__, fullpath, shortpath, ret);
			}
		}
	}

	closedir(dir);
}
#endif // MCEXEC_BIND_MOUNT

#ifdef MCEXEC_RUST_HELPERS
#define join_all_threads() mcexec_join_all_threads_body()
#else
static void
join_all_threads()
{
	struct thread_data_s *tp;
	int live_thread;

	do {
		live_thread = 0;
		for (tp = thread_data; tp; tp = tp->next) {
			if (tp->joined || tp->detached)
				continue;
			live_thread = 1;
			pthread_join(tp->thread_id, NULL);
			tp->joined = 1;
			}
	} while (live_thread);
}
#endif

#ifdef MCEXEC_RUST_HELPERS
void *mcexec_join_all_threads_head_bridge(void)
{
	return thread_data;
}

void mcexec_join_all_threads_join_bridge(struct thread_data_s *tp)
{
	pthread_join(tp->thread_id, NULL);
}
#endif

#ifdef MCEXEC_RUST_HELPERS
#define opendev() mcexec_opendev_body()

extern pthread_spinlock_t overlay_fd_lock;

void mcexec_main_publish_mcosid_bridge(int new_mcosid)
{
	mcosid = new_mcosid;
}

int mcexec_main_uti_unavailable_bridge(int enable_uti_arg)
{
#ifndef ENABLE_UTI
	if (enable_uti_arg) {
		__eprintf("ERROR: uti is not available when not configured with --with-syscall_intercept=<path>\n");
		return 1;
	}
#else
	(void)enable_uti_arg;
#endif
	return 0;
}

void mcexec_main_overlay_lock_init_bridge(void)
{
	pthread_spin_init(&overlay_fd_lock, 0);
}

void mcexec_main_load_desc_error_bridge(const char *path, int ret)
{
	fprintf(stderr, "%s: could not load program: %s\n",
		path, strerror(ret));
}

void mcexec_desc_clear_flags_bridge(struct program_load_desc *desc)
{
	desc->mcexec_flags = 0;
}
#else
static int
opendev()
{
	int f;
	char buildid[] = BUILDID;
    char query_result[sizeof(BUILDID)];

	sprintf(dev, "/dev/mcos%d", mcosid);

	/* Open OS chardev for ioctl() */
	f = open(dev, O_RDWR);
	if (f < 0) {
		fprintf(stderr, "Error: Failed to open %s.\n", dev);
		return -1;
	}
	fd = f;

	if (ioctl(fd, IHK_OS_GET_BUILDID, query_result)) {
		fprintf(stderr, "Error: IHK_OS_GET_BUILDID failed");
		close(fd);
		return -1;
	}

	if (strncmp(buildid, query_result, sizeof(buildid))) {
		fprintf(stderr, "Error: build-id of mcexec (%s) didn't match that of IHK (%s)\n", buildid, query_result);
		close(fd);
		return -1;
	}

	return fd;
}
#endif

#ifdef MCEXEC_RUST_HELPERS
int mcexec_opendev_mcosid_bridge(void)
{
	return mcosid;
}

char *mcexec_opendev_dev_bridge(void)
{
	return dev;
}

size_t mcexec_opendev_dev_size_bridge(void)
{
	return sizeof(dev);
}

void mcexec_opendev_path_error_bridge(void)
{
	fprintf(stderr, "Error: Failed to build mcos device path.\n");
}

int mcexec_opendev_open_bridge(const char *path)
{
	return open(path, O_RDWR);
}

void mcexec_opendev_open_error_bridge(const char *path)
{
	fprintf(stderr, "Error: Failed to open %s.\n", path);
}

void mcexec_opendev_publish_fd_bridge(int value)
{
	fd = value;
}

size_t mcexec_opendev_buildid_size_bridge(void)
{
	return sizeof(BUILDID);
}

const char *mcexec_opendev_buildid_bridge(void)
{
	static char buildid[] = BUILDID;

	return buildid;
}

char *mcexec_opendev_query_result_bridge(void)
{
	static char query_result[sizeof(BUILDID)];

	memset(query_result, '\0', sizeof(query_result));
	return query_result;
}

int mcexec_opendev_query_buildid_bridge(int target_fd, char *query_result)
{
	return ioctl(target_fd, IHK_OS_GET_BUILDID, query_result);
}

void mcexec_opendev_query_error_bridge(void)
{
	fprintf(stderr, "Error: IHK_OS_GET_BUILDID failed");
}

void mcexec_opendev_close_bridge(int target_fd)
{
	close(target_fd);
}

void mcexec_opendev_buildid_mismatch_bridge(const char *buildid,
		const char *query_result)
{
	fprintf(stderr,
		"Error: build-id of mcexec (%s) didn't match that of IHK (%s)\n",
		buildid, query_result);
}
#endif

#define LD_PRELOAD_PREPARE(name) do {	\
	int n = 0;	\
	\
	if (1 + strnlen(libdir, PATH_MAX) + 1 +	\
		strnlen(name, PATH_MAX) + 1 > PATH_MAX) {	\
		fprintf(stderr,	\
			"%s: warning: LD_PRELOAD path is too long\n",	\
			__func__);	\
		return;	\
	}	\
	if (nelem > 0)	\
		n += snprintf(elembuf, PATH_MAX, ":");	\
	n += snprintf(elembuf + n, PATH_MAX - n - 1, libdir); \
	n += snprintf(elembuf + n, PATH_MAX - n - 1, "/"); \
	n += snprintf(elembuf + n, PATH_MAX - n - 1, name); \
} while (0)

#define LD_PRELOAD_APPEND do {	\
		if (strlen(elembuf) + 1 > remainder) { \
			fprintf(stderr, "%s: warning: LD_PRELOAD line is too long\n", __FUNCTION__); \
			return; \
		} \
		strncat(envbuf, elembuf, remainder - 1); \
		remainder = PATH_MAX - (strlen(envbuf) + 1); \
		nelem++; \
	} while (0)

#ifdef MCEXEC_RUST_HELPERS
#define find_libdir(libdir, len) mcexec_find_libdir_body((libdir), (len))
#else
static ssize_t find_libdir(char *libdir, size_t len)
{
	FILE *filep = NULL;
	ssize_t rc;
	size_t linelen = 0;
	char *line = NULL;
	char *slash;
	char path[PATH_MAX];
	char cmd[PATH_MAX];

	rc = readlink("/proc/self/exe", path, sizeof(path));
	if (rc < 0) {
		rc = -errno;
		fprintf(stderr, "readlink /proc/self/exe: %ld\n", -rc);
		goto out;
	} else if (rc >= sizeof(path)) {
		strcpy(path, "/proc/self/exe");
	} else {
		path[rc] = '\0';
	}

	rc = snprintf(cmd, sizeof(cmd),
		      "objdump -x %s | awk '/RPATH/ { print $2 }'",
		      path);
	if (rc >= sizeof(cmd)) {
		rc = -ERANGE;
		goto out;
	}

	filep = popen(cmd, "r");
	if (!filep) {
		rc = -errno;
		fprintf(stderr, "objdump /proc/self/exe: %ld\n", -rc);
		goto out;
	}

	rc = getline(&line, &linelen, filep);
	if (rc <= 0) {
		rc = -errno;
		fprintf(stderr, "RPATH not found: %ld\n", -rc);
		goto out;
	}
	line[rc - 1] = 0;

	slash = strchr(line, '/');
	if (!slash) {
		rc = -EINVAL;
		goto out;
	}

	rc = snprintf(libdir, len, "%s", line);

	if (rc > len) {
		rc = -ERANGE;
		goto out;
	}

out:
	if (filep) {
		pclose(filep);
	}
	free(line);
	return rc;
}
#endif

#ifdef MCEXEC_RUST_HELPERS
ssize_t mcexec_find_libdir_readlink_bridge(char *path, size_t size)
{
	return readlink("/proc/self/exe", path, size);
}

void *mcexec_find_libdir_popen_bridge(const char *cmd)
{
	return popen(cmd, "r");
}

ssize_t mcexec_find_libdir_getline_bridge(char **line, size_t *linelen,
		void *filep)
{
	return getline(line, linelen, filep);
}

void mcexec_find_libdir_pclose_bridge(void *filep)
{
	pclose(filep);
}

void mcexec_find_libdir_free_bridge(char *line)
{
	free(line);
}

void mcexec_find_libdir_readlink_failed_bridge(int error)
{
	fprintf(stderr, "readlink /proc/self/exe: %d\n", error);
}

void mcexec_find_libdir_objdump_failed_bridge(int error)
{
	fprintf(stderr, "objdump /proc/self/exe: %d\n", error);
}

void mcexec_find_libdir_rpath_not_found_bridge(int error)
{
	fprintf(stderr, "RPATH not found: %d\n", error);
}
#endif

#ifdef MCEXEC_RUST_HELPERS
#define ld_preload_init() mcexec_ld_preload_init_body()

char *mcexec_ld_preload_getenv_bridge(const char *name)
{
	return getenv(name);
}

int mcexec_ld_preload_setenv_bridge(const char *value)
{
	return setenv("LD_PRELOAD", value, 1);
}

int mcexec_ld_preload_unsetenv_bridge(void)
{
	return unsetenv(ld_preload_envname);
}

int mcexec_ld_preload_enable_uti_bridge(void)
{
	return enable_uti;
}

int mcexec_ld_preload_disable_sched_yield_bridge(void)
{
	return disable_sched_yield;
}

int mcexec_ld_preload_enable_qlmpi_bridge(void)
{
#ifdef ENABLE_QLMPI
	return 1;
#else
	return 0;
#endif
}

void mcexec_ld_preload_find_failed_bridge(void)
{
	fprintf(stderr, "warning: did not set LD_PRELOAD\n");
}

void mcexec_ld_preload_line_too_long_bridge(void)
{
	fprintf(stderr, "%s: warning: LD_PRELOAD line is too long\n",
			"ld_preload_init");
}

void mcexec_ld_preload_setenv_failed_bridge(void)
{
	printf("%s: warning: failed to set LD_PRELOAD environment variable\n",
			"ld_preload_init");
}

void mcexec_ld_preload_debug_bridge(const char *envbuf)
{
	__dprintf("%s: preload library: %s\n", "ld_preload_init", envbuf);
}
#else
static void ld_preload_init()
{
	char envbuf[PATH_MAX];
	char *ld_preload_str;
	size_t remainder = PATH_MAX;
	int nelem = 0;
	char elembuf[PATH_MAX];
	char libdir[PATH_MAX];

	if (find_libdir(libdir, sizeof(libdir)) < 0) {
		fprintf(stderr, "warning: did not set LD_PRELOAD\n");
		return;
	}

	memset(envbuf, 0, PATH_MAX);

	if (enable_uti) {
		LD_PRELOAD_PREPARE("libmck_syscall_intercept.so");
		LD_PRELOAD_APPEND;
	}

	if (disable_sched_yield) {
		LD_PRELOAD_PREPARE("libsched_yield.so.1.0.0");
		LD_PRELOAD_APPEND;
	}

#ifdef ENABLE_QLMPI
	LD_PRELOAD_PREPARE("libqlfort.so");
	LD_PRELOAD_APPEND;
#endif

	/* Set LD_PRELOAD to McKernel specific value */
	ld_preload_str = getenv(ld_preload_envname);
	if (ld_preload_str) {
		sprintf(elembuf, "%s%s", nelem > 0 ? ":" : "", ld_preload_str);
		LD_PRELOAD_APPEND;
	}

	if (strlen(envbuf)) {
		if (setenv("LD_PRELOAD", envbuf, 1) < 0) {
			printf("%s: warning: failed to set LD_PRELOAD environment variable\n",
					__FUNCTION__);
		}
		__dprintf("%s: preload library: %s\n", __FUNCTION__, envbuf);
	}

	if (getenv("ld_preload_envname")) {
		unsetenv(ld_preload_envname);
	}
}
#endif

#ifdef MCEXEC_RUST_HELPERS
int mcexec_get_thp_disable_prctl_bridge(void)
{
	return prctl(PR_GET_THP_DISABLE, 0, 0, 0, 0);
}

#define get_thp_disable() mcexec_get_thp_disable_body()
#else
static int get_thp_disable(void)
{
	int ret = 0;

	ret = prctl(PR_GET_THP_DISABLE, 0, 0, 0, 0);

	/* PR_GET_THP_DISABLE supported since Linux 3.15 */
	if (ret < 0) {
		/* if not supported, make THP enable */
		ret = 0;
	}

	return ret;
}
#endif

pthread_spinlock_t overlay_fd_lock;

#ifdef MCEXEC_RUST_HELPERS
int main(int argc, char **argv)
{
	return mcexec_main_body(argc, argv);
}
#else
int main(int argc, char **argv)
{
	int ret = 0;
	struct program_load_desc *desc;
	int envs_len;
	char *envs;
#ifndef MCEXEC_RUST_HELPERS
	char *p;
#endif
	int error;
#ifndef MCEXEC_RUST_HELPERS
	int i;
	unsigned long lcur;
	unsigned long lmax;
#endif
	int target_core = 0;
	int opt;
	char **shebang_argv = NULL;
#ifndef MCEXEC_RUST_HELPERS
	char *shebang_argv_flat = NULL;
#endif
	int num = 0;
	int persona;
#ifdef ADD_ENVS_OPTION
#ifndef MCEXEC_RUST_HELPERS
	char **local_env = NULL;
#endif
	struct env_list_entry *extra_env = NULL;
#endif /* ADD_ENVS_OPTION */

#ifdef USE_SYSCALL_MOD_CALL
	__glob_argc = argc;
	__glob_argv = argv;
#endif

#ifdef MCEXEC_RUST_HELPERS
	mcexec_init_page_altroot_body();
#else
	page_size = sysconf(_SC_PAGESIZE);
	page_mask = ~(page_size - 1);

	altroot = getenv("MCEXEC_ALT_ROOT");
	if (!altroot) {
		altroot = "/usr/linux-k1om-4.7/linux-k1om";
	}
#endif

	/* Disable READ_IMPLIES_EXEC */
	persona = personality(0xffffffff);
	if (persona & READ_IMPLIES_EXEC) {
		persona &= ~READ_IMPLIES_EXEC;
		persona = personality(persona);
	}

	/* Disable address space layout randomization */
	__dprintf("persona=%08x\n", persona);
	if ((persona & (PER_LINUX | ADDR_NO_RANDOMIZE)) == 0) {
		char path[PATH_MAX];

		CHKANDJUMP(getenv("MCEXEC_ADDR_NO_RANDOMIZE"), 1, "personality() and then execv() failed\n");

		persona = personality(persona | PER_LINUX | ADDR_NO_RANDOMIZE);
		CHKANDJUMPF(persona == -1, 1, "personality failed, persona=%08x, strerror=%s\n", persona, strerror(errno));

		error = setenv("MCEXEC_ADDR_NO_RANDOMIZE", "1", 1);
		CHKANDJUMP(error == -1, 1, "setenv failed\n");

		error = readlink("/proc/self/exe", path, sizeof(path));
		CHKANDJUMP(error == -1, 1, "readlink failed: %m\n");
		if (error >= sizeof(path)) {
			strcpy(path, "/proc/self/exe");
		} else {
			path[error] = '\0';
		}

		error = execv(path, argv);
		CHKANDJUMPF(error == -1, 1, "execv failed, error=%d,strerror=%s\n", error, strerror(errno));
	}
	if (getenv("MCEXEC_ADDR_NO_RANDOMIZE")) {
		error = unsetenv("MCEXEC_ADDR_NO_RANDOMIZE");
		CHKANDJUMP(error == -1, 1, "unsetenv failed");
	}

#ifdef MCEXEC_RUST_HELPERS
	if (mcexec_init_stack_limit_body(argv)) {
		return 1;
	}
#else
	/* Inherit ulimit settings to McKernel process */
	if (getrlimit(RLIMIT_STACK, &rlim_stack)) {
		fprintf(stderr, "getrlimit failed\n");
		return 1;
	}
    __dprintf("rlim_stack=%ld,%ld\n", rlim_stack.rlim_cur, rlim_stack.rlim_max);

	/* Shrink mcexec stack if it leaves too small room for McKernel process */
#define	MCEXEC_MAX_STACK_SIZE	(16 * 1024 * 1024)	/* 1 GiB */
	if (rlim_stack.rlim_cur > MCEXEC_MAX_STACK_SIZE) {
		/* need to call reduce_stack() before modifying the argv[] */
		(void)reduce_stack(&rlim_stack, argv);	/* no return, unless failure */
		fprintf(stderr, "Error: Failed to reduce stack.\n");
		return 1;
	}
#endif

	/* Parse options ("+" denotes stop at the first non-option) */
#ifdef MCEXEC_RUST_HELPERS
#define MCEXEC_APPLY_OPTION() \
	mcexec_apply_option_result(opt, optarg, &target_core, \
			&nr_processes, &nr_threads, &mpol_threshold, \
			&heap_extension, &straight_map_threshold, \
			&stack_premap, &stack_max, &uti_thread_rank, \
			&mcexec_flags)
#endif
#ifdef ADD_ENVS_OPTION
	while ((opt = getopt_long(argc, argv, "+c:n:t:M:h:e:s:m:u:S:f:",
				  mcexec_options, NULL)) != -1) {
#else /* ADD_ENVS_OPTION */
	while ((opt = getopt_long(argc, argv, "+c:n:t:M:h:s:m:u:S:f:",
				  mcexec_options, NULL)) != -1) {
#endif /* ADD_ENVS_OPTION */
		switch (opt) {
#ifndef MCEXEC_RUST_HELPERS
			char *tmp;
#endif

			case 'c':
#ifdef MCEXEC_RUST_HELPERS
				if (MCEXEC_APPLY_OPTION() < 0) {
					fprintf(stderr, "error: -c: invalid target CPU\n");
					exit(EXIT_FAILURE);
				}
#else
				target_core = strtol(optarg, &tmp, 0);
				if (*tmp != '\0') {
					fprintf(stderr, "error: -c: invalid target CPU\n");
					exit(EXIT_FAILURE);
				}
#endif
				break;

			case 'n':
#ifdef MCEXEC_RUST_HELPERS
				if (MCEXEC_APPLY_OPTION() < 0) {
					fprintf(stderr, "error: -n: invalid number of processes\n");
					exit(EXIT_FAILURE);
				}
#else
				nr_processes = strtol(optarg, &tmp, 0);
				if (*tmp != '\0' || nr_processes <= 0) {
					fprintf(stderr, "error: -n: invalid number of processes\n");
					exit(EXIT_FAILURE);
				}
#endif
				break;

			case 't':
#ifdef MCEXEC_RUST_HELPERS
				if (MCEXEC_APPLY_OPTION() < 0) {
					fprintf(stderr, "error: -t: invalid number of threads\n");
					exit(EXIT_FAILURE);
				}
#else
				nr_threads = strtol(optarg, &tmp, 0);
				if (*tmp != '\0' || nr_threads <= 0) {
					fprintf(stderr, "error: -t: invalid number of threads\n");
					exit(EXIT_FAILURE);
				}
#endif
				break;

			case 'M':
#ifdef MCEXEC_RUST_HELPERS
				MCEXEC_APPLY_OPTION();
#else
				mpol_threshold = atobytes(optarg);
#endif
				break;

			case 'm':
				mpol_bind_nodes = optarg;
				break;

			case 'h':
#ifdef MCEXEC_RUST_HELPERS
				MCEXEC_APPLY_OPTION();
#else
				heap_extension = atobytes(optarg);
#endif
				break;

			case 'S':
#ifdef MCEXEC_RUST_HELPERS
				MCEXEC_APPLY_OPTION();
#else
				straight_map_threshold = atobytes(optarg);
#endif
				break;

#ifdef ADD_ENVS_OPTION
			case 'e':
				add_env_list(&extra_env, optarg);
				break;
#endif /* ADD_ENVS_OPTION */
			
			case 's': {
#ifdef MCEXEC_RUST_HELPERS
				MCEXEC_APPLY_OPTION();
				errno = 0;
#else
				char *token, *dup, *line;

				dup = strdup(optarg);
				line = dup;
				token = strsep(&line, ",");
				if (token != NULL && *token != 0) {
					stack_premap = atobytes(token);
				}
				token = strsep(&line, ",");
				if (token != NULL && *token != 0) {
					stack_max = atobytes(token);
				}
				free(dup);
#endif
				__dprintf("stack_premap=%ld,stack_max=%ld\n",
					  stack_premap, stack_max);
				break;
			}

			case 'u':
#ifdef MCEXEC_RUST_HELPERS
				MCEXEC_APPLY_OPTION();
#else
				uti_thread_rank = atoi(optarg);
#endif
				break;

			case 'f':
#ifdef MCEXEC_RUST_HELPERS
				MCEXEC_APPLY_OPTION();
#else
				mcexec_flags = strtoul(optarg, NULL, 16);
#endif
				break;

			case 0:	/* long opt */
				break;

			default: /* '?' */
				print_usage(argv);
				exit(EXIT_FAILURE);
		}
	}
#ifdef MCEXEC_RUST_HELPERS
#undef MCEXEC_APPLY_OPTION
#endif

#ifdef MCEXEC_RUST_HELPERS
	{
		unsigned long planned_heap_extension = heap_extension;
		int planned_mcosid = num;
		int planned_optind = optind;

		if (mcexec_post_options_plan_result(optind, argc,
				optind < argc ? argv[optind] : NULL,
				heap_extension, page_size, num,
				&planned_heap_extension, &planned_mcosid,
				&planned_optind) < 0) {
			print_usage(argv);
			exit(EXIT_FAILURE);
		}

		heap_extension = planned_heap_extension;
		num = planned_mcosid;
		optind = planned_optind;
	}
#else
	if (heap_extension == -1) {
		heap_extension = sysconf(_SC_PAGESIZE);
	}

	if (optind >= argc) {
		print_usage(argv);
		exit(EXIT_FAILURE);
	}

	/* Determine OS device */
	if (isdigit(*argv[optind])) {
		num = atoi(argv[optind]);
		++optind;
	}

	/* No more arguments? */
	if (optind >= argc) {
		print_usage(argv);
		exit(EXIT_FAILURE);
	}
#endif

#ifdef MCEXEC_RUST_HELPERS
	if (mcexec_post_option_setup_body(num, enable_uti)) {
		exit(EXIT_FAILURE);
	}
#else
	mcosid = num;
	if (opendev() == -1)
		exit(EXIT_FAILURE);

#ifndef ENABLE_UTI
	if (enable_uti) {
		__eprintf("ERROR: uti is not available when not configured with --with-syscall_intercept=<path>\n");
		exit(EXIT_FAILURE);
	}
#endif

	pthread_spin_init(&overlay_fd_lock, 0);

	/* XXX: Fugaku: Fujitsu process placement fix */
	if (getenv("FLIB_AFFINITY_ON_PROCESS")) {
		char *cpu_s;
		int flib_size;
		char *flib_aff_orig, *flib_aff;
		int cpu, off = 0;

		flib_aff_orig = strdup(getenv("FLIB_AFFINITY_ON_PROCESS"));
		if (!flib_aff_orig) {
			fprintf(stderr, "error: dupping FLIB_AFFINITY_ON_PROCESS\n");
			exit(EXIT_FAILURE);
		}

		flib_size = strlen(flib_aff_orig) * 2;

		flib_aff = malloc(flib_size);
		if (!flib_aff) {
			fprintf(stderr, "error: allocating memory for "
					"FLIB_AFFINITY_ON_PROCESS\n");
			exit(EXIT_FAILURE);
		}
		memset(flib_aff, 0, flib_size);

		cpu_s = strtok(flib_aff_orig, ",");
		while (cpu_s) {
			int ret;

			/* "Shift" left by 12 CPUs */
			cpu = atoi(cpu_s) - 12;

			/* Prepend "," */
			if (off > 0) {
				ret = snprintf(flib_aff + off, flib_size - off, "%s", ",");
				if (ret < 0) {
					fprintf(stderr, "error: constructing "
							"FLIB_AFFINITY_ON_PROCESS\n");
					exit(EXIT_FAILURE);
				}

				off += ret;
			}

			ret = snprintf(flib_aff + off, flib_size - off, "%d", cpu);
			if (ret < 0) {
				fprintf(stderr, "error: constructing "
						"FLIB_AFFINITY_ON_PROCESS\n");
				exit(EXIT_FAILURE);
			}

			off += ret;
			cpu_s = strtok(NULL, ",");
		}

		__dprintf("FLIB_AFFINITY_ON_PROCESS: %s -> %s\n",
				getenv("FLIB_AFFINITY_ON_PROCESS"), flib_aff);
		setenv("FLIB_AFFINITY_ON_PROCESS", flib_aff, 1);
	}

	ld_preload_init();
#endif

#ifdef ADD_ENVS_OPTION
#else /* ADD_ENVS_OPTION */
#ifdef MCEXEC_RUST_HELPERS
	mcexec_collect_default_envs_body(&envs_len, &envs);
#else
	/* Collect environment variables */
	envs_len = flatten_strings(NULL, environ, &envs);
#endif
#endif /* ADD_ENVS_OPTION */

#ifdef MCEXEC_BIND_MOUNT
	error = isunshare();
	if (error == 0) {
		struct sys_unshare_desc unshare_desc;
		struct sys_mount_desc mount_desc;
		struct sys_umount_desc umount_desc;

		/* Unshare mount namespace */
		memset(&unshare_desc, '\0', sizeof unshare_desc);
		memset(&mount_desc, '\0', sizeof mount_desc);
		unshare_desc.unshare_flags = CLONE_NEWNS;
		if (ioctl(fd, MCEXEC_UP_SYS_UNSHARE,
			(unsigned long)&unshare_desc) != 0) {
			fprintf(stderr, "Error: Failed to unshare. (%s)\n",
				strerror(errno));
			return 1;
		}

		/* Privatize mount namespace */
		mount_desc.dev_name = NULL;
		mount_desc.dir_name = "/";
		mount_desc.type = NULL;
		mount_desc.flags = MS_PRIVATE | MS_REC;
		mount_desc.data = NULL;
		if (ioctl(fd, MCEXEC_UP_SYS_MOUNT,
			(unsigned long)&mount_desc) != 0) {
			fprintf(stderr, "Error: Failed to privatize mounts. (%s)\n",
				strerror(errno));
			return 1;
		}

		// bind_mount_recursive(<root>, <prefix>);
	} else if (error == -1) {
		return 1;
	}
#endif // MCEXEC_BIND_MOUNT

#ifdef MCEXEC_RUST_HELPERS
	if (mcexec_load_main_desc_body(argv[optind], &desc, &shebang_argv)) {
		return 1;
	}
#else
	/* fget executable as well */
	if ((ret = load_elf_desc_shebang(argv[optind], &desc,
					 &shebang_argv, 1 /* execvp */))) {
		fprintf(stderr, "%s: could not load program: %s\n",
			argv[optind], strerror(ret));
		return 1;
	}

	desc->mcexec_flags = 0;
#endif

#ifdef ADD_ENVS_OPTION
#ifdef MCEXEC_RUST_HELPERS
	mcexec_collect_main_envs_body(&extra_env, &envs_len, &envs);
#else
	/* Collect environment variables */
	for (i = 0; environ[i]; i++) {
		add_env_list(&extra_env, environ[i]);
	}
	local_env = create_local_environ(extra_env);
	envs_len = flatten_strings(NULL, local_env, &envs);
	destroy_local_environ(local_env);
	local_env = NULL;
	destroy_env_list(extra_env);
	extra_env = NULL;
#endif
#endif /* ADD_ENVS_OPTION */

#ifdef MCEXEC_RUST_HELPERS
	mcexec_prepare_main_desc_body(desc, argv + optind, shebang_argv,
			envs_len, envs, target_core, enable_vdso);
#else
	for(i = 0; i < sizeof(rlimits) / sizeof(int); i += 2)
		getrlimit(rlimits[i], &desc->rlimit[rlimits[i + 1]]);
	desc->envs_len = envs_len;
	desc->envs = envs;
	//print_flat(envs);

	if (shebang_argv)
		flatten_strings(NULL, shebang_argv, &shebang_argv_flat);

	desc->args_len = flatten_strings(shebang_argv_flat, argv + optind,
					 &desc->args);
	//print_flat(desc->args);
	free(shebang_argv);
	free(shebang_argv_flat);

	desc->cpu = target_core;
	desc->enable_vdso = enable_vdso;
#endif

#ifdef MCEXEC_RUST_HELPERS
	if (mcexec_apply_main_stack_body(desc, getenv(rlimit_stack_envname),
			stack_max, stack_premap, &rlim_stack.rlim_cur,
			&rlim_stack.rlim_max)) {
		return 1;
	}
#else
	/* Restore the stack size when mcexec stack was shrinked */
	p = getenv(rlimit_stack_envname);
	if (p) {
		char *saveptr;
		char *token;
		errno = 0;

		token = strtok_r(p, ",", &saveptr);
		if (!token) {
			fprintf(stderr, "Error: Failed to parse %s 1\n",
					rlimit_stack_envname);
			return 1;
		}

		lcur = atobytes(token);
		if (lcur == 0 || errno) {
			fprintf(stderr, "Error: Failed to parse %s 2\n",
					rlimit_stack_envname);
			return 1;
		}

		token = strtok_r(NULL, ",", &saveptr);
		if (!token) {
			fprintf(stderr, "Error: Failed to parse %s 4\n",
					rlimit_stack_envname);
			return 1;
		}

		lmax = atobytes(token);
		if (lmax == 0 || errno) {
			fprintf(stderr, "Error: Failed to parse %s 5\n",
					rlimit_stack_envname);
			return 1;
		}

		if (lcur > lmax) {
			lcur = lmax;
		}
		if (lmax > rlim_stack.rlim_max) {
			rlim_stack.rlim_max = lmax;
		}
		if (lcur > rlim_stack.rlim_cur) {
			rlim_stack.rlim_cur = lcur;
		}
	}

	/* Overwrite the max with <max> of "--stack-premap <premap>,<max>" */
	if (stack_max != -1) {
		rlim_stack.rlim_cur = stack_max;
		if (rlim_stack.rlim_max != -1 && rlim_stack.rlim_max < rlim_stack.rlim_cur) {
			rlim_stack.rlim_max = rlim_stack.rlim_cur;
		}
	}

	desc->rlimit[MCK_RLIMIT_STACK].rlim_cur = rlim_stack.rlim_cur;
	desc->rlimit[MCK_RLIMIT_STACK].rlim_max = rlim_stack.rlim_max;
	desc->stack_premap = stack_premap;
	__dprintf("desc->rlimit[MCK_RLIMIT_STACK]=%ld,%ld\n", desc->rlimit[MCK_RLIMIT_STACK].rlim_cur, desc->rlimit[MCK_RLIMIT_STACK].rlim_max);
#endif

#ifdef MCEXEC_RUST_HELPERS
	if (mcexec_setup_cpu_topology_body()) {
		return 1;
	}
#else
	ncpu = ioctl(fd, MCEXEC_UP_GET_CPU, 0);
	if (ncpu <= 0) {
		fprintf(stderr, "No CPU found.\n");
		return 1;
	}
	nnodes = ioctl(fd, MCEXEC_UP_GET_NODES, 0);
	if (nnodes <= 0) {
		fprintf(stderr, "No numa node found.\n");
		return 1;
	}
	cpu_set_size = CPU_ALLOC_SIZE(ncpu);
	numa_nodes = malloc(cpu_set_size * nnodes);
	if (!numa_nodes) {
		fprintf(stderr, "Error allocating nodes cpu sets\n");
		return 1;
	}
	for (i = 0; i < nnodes; i++) {
		cpu_set_t *node = numa_node_set(i);
		int j;
		struct stat sb;
		char buf[PATH_MAX];

		CPU_ZERO_S(cpu_set_size, node);
		for (j = 0; j < ncpu; j++) {
			snprintf(buf, PATH_MAX,
				 "/sys/class/mcos/mcos0/sys/devices/system/node/node%d/cpu%d",
				 i, j);
			if (stat(buf, &sb) == 0)
				CPU_SET_S(j, cpu_set_size, node);
		}
	}
#endif

#ifdef MCEXEC_RUST_HELPERS
	if (mcexec_plan_process_threads_result(&nr_processes, nr_threads,
			ncpu, &n_threads) < 0) {
		fprintf(stderr, "error: nr_processes can't exceed nr. of CPUs\n");
		return EINVAL;
	}
#else
	/* Fugaku: use FLIB_NUM_PROCESS_ON_NODE if -n is not specified */
	if (getenv("FLIB_NUM_PROCESS_ON_NODE") && nr_processes == 0) {
		nr_processes = atoi(getenv("FLIB_NUM_PROCESS_ON_NODE"));
		__dprintf("%s: using FLIB_NUM_PROCESS_ON_NODE: %d\n",
			__func__, nr_processes);
	}

	if (nr_processes > ncpu) {
		fprintf(stderr, "error: nr_processes can't exceed nr. of CPUs\n");
		return EINVAL;
	}

	if (nr_threads > 0) {
		n_threads = nr_threads;
	}
	else if (getenv("OMP_NUM_THREADS")) {
		/* Leave some headroom for helper threads.. */
		n_threads = atoi(getenv("OMP_NUM_THREADS")) + 4;
	}
	else {
		/*
		 * When running with partitioned execution, do not allow
		 * more threads then the corresponding number of CPUs.
		 */
		if (nr_processes > 0 && nr_processes < ncpu) {
			n_threads = (ncpu / nr_processes) + 4;

			if (n_threads == 0) {
				n_threads = 2;
			}
		}
		else if (nr_processes == ncpu) {
			n_threads = 1;
		}
		else {
			n_threads = ncpu;
		}
	}
#endif

	/* 
	 * XXX: keep thread_data ncpu sized despite that there are only
	 * n_threads worker threads in the pool so that signaling code
	 * keeps working.
	 *
	 * TODO: fix signaling code to be independent of TIDs.
	 * TODO: implement dynaic thread pool resizing.
	 */
#if 0
	thread_data = (struct thread_data_s *)malloc(sizeof(struct thread_data_s) * (ncpu + 1));
	if (!thread_data) {
		fprintf(stderr, "error: allocating thread pool data\n");
		return 1;
	}
	memset(thread_data, '\0', sizeof(struct thread_data_s) * (ncpu + 1));
#endif

#if 0	
	fdm = open("/dev/fmem", O_RDWR);
	if (fdm < 0) {
		fprintf(stderr, "Error: Failed to open /dev/fmem.\n");
		return 1;
	}

	if ((r = ioctl(fd, MCEXEC_UP_PREPARE_DMA, 
	               (unsigned long)&dma_buf_pa)) < 0) {
		perror("prepare_dma");
		close(fd);
		return 1;
	}

	dma_buf = mmap(NULL, PIN_SIZE, PROT_READ | PROT_WRITE,
	               MAP_SHARED, fdm, dma_buf_pa);
	__dprintf("DMA Buffer: %lx, %p\n", dma_buf_pa, dma_buf);
#endif

#ifdef MCEXEC_RUST_HELPERS
	mcexec_setup_dma_ppd_body();
#else
	dma_buf = mmap(0, PIN_SIZE, PROT_READ | PROT_WRITE, 
	               (MAP_ANONYMOUS | MAP_PRIVATE), -1, 0);
	if (dma_buf == (void *)-1) {
		__dprintf("error: allocating DMA area\n");
		exit(1);
	}
	
	/* PIN buffer */
	if (mlock(dma_buf, (size_t)PIN_SIZE)) {
		__dprintf("ERROR: locking dma_buf\n");
		exit(1);
	}

	/* Register per-process structure in mcctrl */
	if (ioctl(fd, MCEXEC_UP_CREATE_PPD, NULL)) {
		perror("creating mcctrl per-process structure");
		close(fd);
		exit(1);
	}
#endif

#ifdef MCEXEC_RUST_HELPERS
	if (mcexec_apply_partitioned_cpu_body(desc, nr_processes, &target_core,
			no_bind_ikc_map)) {
		return 1;
	}
#else
	/* Partitioned execution, obtain CPU set */
	if (!target_core && nr_processes > 0) {
		struct get_cpu_set_arg cpu_set_arg;
		int mcexec_linux_numa = 0;
		int ikc_mapped = 0;
		int process_rank = -1;
		cpu_set_t mcexec_cpu_set;

		CPU_ZERO(&mcexec_cpu_set);

		cpu_set_arg.req_cpu_list = NULL;
		cpu_set_arg.req_cpu_list_len = 0;
		cpu_set_arg.cpu_set = (void *)&desc->cpu_set;
		cpu_set_arg.cpu_set_size = sizeof(desc->cpu_set);
		cpu_set_arg.nr_processes = nr_processes;
		cpu_set_arg.ppid = getppid();
		cpu_set_arg.target_core = &target_core;
		cpu_set_arg.process_rank = &process_rank;
		cpu_set_arg.mcexec_linux_numa = &mcexec_linux_numa;
		cpu_set_arg.mcexec_cpu_set = &mcexec_cpu_set;
		cpu_set_arg.mcexec_cpu_set_size = sizeof(mcexec_cpu_set);
		cpu_set_arg.ikc_mapped = &ikc_mapped;

		/* Fugaku specific: Fujitsu CPU binding */
		if (getenv("FLIB_AFFINITY_ON_PROCESS")) {
			cpu_set_arg.req_cpu_list =
				getenv("FLIB_AFFINITY_ON_PROCESS");
			cpu_set_arg.req_cpu_list_len =
				strlen(cpu_set_arg.req_cpu_list) + 1;
			__dprintf("%s: requesting CPUs: %s\n",
				__func__, cpu_set_arg.req_cpu_list);
		}

		if (ioctl(fd, MCEXEC_UP_GET_CPUSET, (void *)&cpu_set_arg) != 0) {
			perror("getting CPU set for partitioned execution");
			close(fd);
			return 1;
		}

		desc->cpu = target_core;
		desc->process_rank = process_rank;

		/* Fugaku specific: Fujitsu node-local rank */
		if (getenv("FLIB_RANK_ON_NODE")) {
			desc->process_rank = atoi(getenv("FLIB_RANK_ON_NODE"));
			__dprintf("%s: rank: %d, target CPU: %d\n",
				__func__, desc->process_rank, desc->cpu);
		}

		/* Bind to CPU cores where the LWK process' IKC target maps to */
		if (ikc_mapped && !no_bind_ikc_map) {
			/* This call may not succeed, but that is fine */
			if (sched_setaffinity(0, sizeof(mcexec_cpu_set),
						&mcexec_cpu_set) < 0) {
				__dprintf("WARNING: couldn't bind to mcexec_cpu_set\n");
			}
#ifdef DEBUG
			else {
				int i;
				for (i = 0; i < numa_num_possible_cpus(); ++i) {
					if (CPU_ISSET(i, &mcexec_cpu_set)) {
						__dprintf("PID %d bound to CPU %d\n",
							getpid(), i);
					}
				}
			}
#endif // DEBUG
		}
		else {
			/* This call may not succeed, but that is fine */
			if (numa_run_on_node(mcexec_linux_numa) < 0) {
				__dprintf("WARNING: couldn't bind to NUMA %d\n",
						mcexec_linux_numa);
			}
#ifdef DEBUG
			else {
				cpu_set_t cpuset;
				char affinity[BUFSIZ];

				CPU_ZERO(&cpuset);
				if ((sched_getaffinity(0, sizeof(cpu_set_t), &cpuset)) != 0) {
					perror("Error sched_getaffinity");
					exit(1);
				}

				affinity[0] = '\0';
				for (i = 0; i < 512; i++) {
					if (CPU_ISSET(i, &cpuset) == 1) {
						sprintf(affinity, "%s %d", affinity, i);
					}
				}
				__dprintf("PID: %d affinity: %s\n",
						getpid(), affinity);
			}
#endif // DEBUG			
		}
	}
#endif

#ifdef MCEXEC_RUST_HELPERS
	mcexec_apply_desc_runtime_body(desc, profile, nr_processes,
			mpol_no_heap, mpol_no_stack, mpol_no_bss,
			mpol_shm_premap, mpol_threshold, heap_extension,
			mpol_bind_nodes, MPOL_DEFAULT, MPOL_INTERLEAVE,
			MPOL_BIND, MPOL_PREFERRED, PLD_MPOL_MAX, enable_uti,
			uti_thread_rank, uti_use_last_cpu, straight_map,
			straight_map_threshold,
#ifdef ENABLE_TOFU
			enable_tofu,
#else
			0,
#endif
			mcexec_flags);
#else
	desc->profile = profile;
	desc->nr_processes = nr_processes;
	desc->mpol_flags = 0;
	if (mpol_no_heap) {
		desc->mpol_flags |= MPOL_NO_HEAP;
	}

	if (mpol_no_stack) {
		desc->mpol_flags |= MPOL_NO_STACK;
	}

	if (mpol_no_bss) {
		desc->mpol_flags |= MPOL_NO_BSS;
	}

	if (mpol_shm_premap) {
		desc->mpol_flags |= MPOL_SHM_PREMAP;
	}

	desc->mpol_threshold = mpol_threshold;
	desc->heap_extension = heap_extension;

	desc->mpol_bind_mask = 0;
	desc->mpol_mode = PLD_MPOL_MAX; /* not specified */
	if (mpol_bind_nodes) {
		struct bitmask *bind_mask;
		bind_mask = numa_parse_nodestring_all(mpol_bind_nodes);

		if (bind_mask) {
			int node;
			for (node = 0; node <= numa_max_possible_node(); ++node) {
				if (numa_bitmask_isbitset(bind_mask, node)) {
					desc->mpol_bind_mask |= (1UL << node);
				}
			}
		}
	}
	/* Fujitsu TCS specific: mempolicy */
	else if (getenv("OMPI_MCA_plm_ple_memory_allocation_policy")) {
		char *mpol =
			getenv("OMPI_MCA_plm_ple_memory_allocation_policy");

		__dprintf("OMPI_MCA_plm_ple_memory_allocation_policy: %s\n",
			  mpol);

		if (!strncmp(mpol, "localalloc", 10)) {
			/* MPOL_DEFAULT has the same effect as MPOL_LOCAL */
			desc->mpol_mode = MPOL_DEFAULT;
		}
		else if (!strncmp(mpol, "interleave_local", 16)) {
			desc->mpol_mode = MPOL_INTERLEAVE;
			numa_local(desc->cpu_set, desc->mpol_nodemask);
		}
		else if (!strncmp(mpol, "interleave_nonlocal", 19)) {
			desc->mpol_mode = MPOL_INTERLEAVE;
			numa_nonlocal(desc->cpu_set, desc->mpol_nodemask);
		}
		else if (!strncmp(mpol, "interleave_all", 14)) {
			desc->mpol_mode = MPOL_INTERLEAVE;
			numa_all(desc->mpol_nodemask);
		}
		else if (!strncmp(mpol, "bind_local", 10)) {
			desc->mpol_mode = MPOL_BIND;
			numa_local(desc->cpu_set, desc->mpol_nodemask);
		}
		else if (!strncmp(mpol, "bind_nonlocal", 13)) {
			desc->mpol_mode = MPOL_BIND;
			numa_nonlocal(desc->cpu_set, desc->mpol_nodemask);
		}
		else if (!strncmp(mpol, "bind_all", 8)) {
			desc->mpol_mode = MPOL_BIND;
			numa_all(desc->mpol_nodemask);
		}
		else if (!strncmp(mpol, "prefer_local", 12)) {
			desc->mpol_mode = MPOL_PREFERRED;
			numa_local(desc->cpu_set, desc->mpol_nodemask);
		}
		else if (!strncmp(mpol, "prefer_nonlocal", 15)) {
			desc->mpol_mode = MPOL_PREFERRED;
			numa_nonlocal(desc->cpu_set, desc->mpol_nodemask);
		}

		__dprintf("mpol_mode: %d, mpol_nodemask: %ld\n",
			  desc->mpol_mode, desc->mpol_nodemask[0]);
	}

	desc->enable_uti = enable_uti;
	desc->uti_thread_rank = uti_thread_rank;
	desc->uti_use_last_cpu = uti_use_last_cpu;
	desc->thp_disable = get_thp_disable();

	desc->straight_map = straight_map;
	desc->straight_map_threshold = straight_map_threshold;
#ifdef ENABLE_TOFU
	desc->enable_tofu = enable_tofu;
#endif

	/*
	 * Override mcexec_flags, if explicitly set.
	 * This must be right before prepare image.
	 */
	if (mcexec_flags) {
		desc->mcexec_flags = mcexec_flags;
	}
#endif

#ifdef MCEXEC_RUST_HELPERS
	ret = mcexec_finish_main_image_body(desc);
#else
	/* user_start and user_end are set by this call */
	if (ioctl(fd, MCEXEC_UP_PREPARE_IMAGE, (unsigned long)desc) != 0) {
		perror("prepare");
		close(fd);
		return 1;
	}

	print_desc(desc);
	if (transfer_image(fd, desc) < 0) {
		fprintf(stderr, "error: transferring image\n");
		return -1;
	}

	/* fput executable */
	if ((ret = ioctl(fd, MCEXEC_UP_CLOSE_EXEC)) != 0) {
		fprintf(stderr, "error: MCEXEC_UP_CLOSE_EXEC failed with %d\n",
			ret);
		return 1;
	}

	fflush(stdout);
	fflush(stderr);
	
#ifdef USE_SYSCALL_MOD_CALL
	/**
	 * TODO: need mutex for static structures
	 */
	if(mc_cmd_server_init()){
		fprintf(stderr, "Error: cmd server init failed\n");
		return 1;
	}

#ifdef CMD_DCFA
	if(ibmic_cmd_server_init()){
		fprintf(stderr, "Error: Failed to initialize ibmic_cmd_server.\n");
		return -1;
	}
#endif

#ifdef CMD_DCFAMPI
	if(dcfampi_cmd_server_init()){
		fprintf(stderr, "Error: Failed to initialize dcfampi_cmd_server.\n");
		return -1;
	}
#endif
	__dprintf("mccmd server initialized\n");
#endif

	init_sigaction();

	if ((error = init_worker_threads(fd)) != 0) {
		fprintf(stderr, "%s: Error: creating worker threads: %s\n",
			__func__, strerror(-error));
		close(fd);
		return 1;
	}

	if (ioctl(fd, MCEXEC_UP_START_IMAGE, (unsigned long)desc) != 0) {
		perror("exec");
		close(fd);
		return 1;
	}

#if 1 /* debug : thread killed by exit_group() are still joinable? */
	join_all_threads();
#endif
#endif
 fn_fail:
	return ret;
}
#endif


#ifndef MCEXEC_RUST_HELPERS
void do_syscall_return(int fd, int cpu,
		       long ret, int n, unsigned long src, unsigned long dest,
		       unsigned long sz)
{
	struct syscall_ret_desc desc;

	memset(&desc, '\0', sizeof desc);
	desc.cpu = cpu;
	desc.ret = ret;
	desc.src = src;
	desc.dest = dest;
	desc.size = sz;
	
	if (ioctl(fd, MCEXEC_UP_RET_SYSCALL, (unsigned long)&desc) != 0) {
		perror("ret");
	}
}

void do_syscall_load(int fd, int cpu, unsigned long dest, unsigned long src,
		     unsigned long sz)
{
	struct syscall_load_desc desc;

	memset(&desc, '\0', sizeof desc);
	desc.cpu = cpu;
	desc.src = src;
	desc.dest = dest;
	desc.size = sz;

	if (ioctl(fd, MCEXEC_UP_LOAD_SYSCALL, (unsigned long)&desc) != 0){
		perror("load");
	}
}
#endif

#ifdef MCEXEC_RUST_HELPERS
long mcexec_do_generic_syscall_raw_bridge(struct syscall_wait_desc *w)
{
	return syscall(w->sr.number, w->sr.args[0], w->sr.args[1], w->sr.args[2],
		       w->sr.args[3], w->sr.args[4], w->sr.args[5]);
}

void mcexec_do_generic_syscall_start_bridge(unsigned long number)
{
	__dprintf("do_generic_syscall(%ld)\n", number);
}

void mcexec_do_generic_syscall_done_bridge(unsigned long number, long ret)
{
	__dprintf("do_generic_syscall(%ld):%ld (%#lx)\n", number, ret, ret);
}

#define do_generic_syscall(w) mcexec_do_generic_syscall_body(w)

long mcexec_do_generic_syscall_bridge(struct syscall_wait_desc *w)
{
	return mcexec_do_generic_syscall_body(w);
}
#else
static long
do_generic_syscall(
		struct syscall_wait_desc *w)
{
	long	ret;

	__dprintf("do_generic_syscall(%ld)\n", w->sr.number);

	ret = syscall(w->sr.number, w->sr.args[0], w->sr.args[1], w->sr.args[2],
		 w->sr.args[3], w->sr.args[4], w->sr.args[5]);
	SET_ERR(ret);

	__dprintf("do_generic_syscall(%ld):%ld (%#lx)\n", w->sr.number, ret, ret);
	return ret;
}
#endif

#ifndef MCEXEC_RUST_HELPERS
static struct uti_desc *uti_desc;
#endif

#ifdef MCEXEC_RUST_HELPERS
#define kill_thread(tid, sig, my_thread) \
	mcexec_kill_thread_body((tid), (unsigned long)(sig), (my_thread))

void *mcexec_kill_thread_head_bridge(void)
{
	return thread_data;
}

int mcexec_kill_thread_pthread_kill_bridge(struct thread_data_s *tp, int sig)
{
	return pthread_kill(tp->thread_id, sig);
}

void mcexec_kill_thread_not_found_bridge(unsigned long tid, int sig)
{
	printf("%s: ERROR: Thread not found (tid=%ld,sig=%d)\n",
	       "kill_thread", tid, sig);
}

void mcexec_kill_thread_bridge(unsigned long tid, unsigned long sig,
		struct thread_data_s *my_thread)
{
	mcexec_kill_thread_body(tid, sig, my_thread);
}
#else
static void kill_thread(unsigned long tid, int sig,
	            struct thread_data_s *my_thread)
{
	struct thread_data_s *tp;

	if (sig == 0)
		sig = LOCALSIG;

	for (tp = thread_data; tp; tp = tp->next) {
		if (tp == my_thread)
			continue;
		if (tp->remote_tid == tid) {
			if (pthread_kill(tp->thread_id, sig) == ESRCH) {
				printf("%s: ERROR: Thread not found (tid=%ld,sig=%d)\n", __FUNCTION__, tid, sig);
			}
		}
	}
}
#endif

#ifdef MCEXEC_RUST_HELPERS
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

void mcexec_gettid_alloc_error_bridge(void)
{
	fprintf(stderr, "__NR_gettid(): error allocating TIDs\n");
}

void mcexec_gettid_transfer_error_bridge(void)
{
	fprintf(stderr, "__NR_gettid(): error transfering TIDs\n");
}

void mcexec_debug_mlock_log_bridge(unsigned long addr, unsigned long len)
{
	printf("linux mlock(%p, %ld)\n", (void *)addr, len);
	printf("str(%p)=%s", (void *)addr, (char *)addr);
}

long mcexec_debug_mlock_bridge(unsigned long addr, unsigned long len)
{
	return mlock((void *)addr, len);
}

void mcexec_swapout_unavailable_bridge(void)
{
	printf("mcexec has not been compiled with ENABLE_QLMPI\n");
}

void mcexec_linux_spawn_invalid_arg_bridge(void)
{
	fprintf(stderr, "linux_spawn(): ERROR: invalid argument \n");
}

void mcexec_linux_spawn_invalid_exec_path_bridge(void)
{
	fprintf(stderr, "linux_spawn(): ERROR: invalid exec_path \n");
}

void mcexec_linux_spawn_alloc_exec_path_failed_bridge(void)
{
	fprintf(stderr, "linux_spawn(): ERROR: failed to allocating exec_path\n");
}

void mcexec_linux_spawn_strncpy_failed_bridge(void)
{
	fprintf(stderr, "linux_spawn(): ERROR: failed to strncpy from user\n");
}

void mcexec_linux_spawn_alloc_argv_failed_bridge(int index)
{
	fprintf(stderr, "linux_spawn(): ERROR: failed to allocating argv[%d]\n",
			index);
}

void mcexec_linux_spawn_posix_spawn_failed_bridge(int rc)
{
	fprintf(stderr, "linux_spawn(): ERROR: posix_spawn returned %d\n", rc);
}

void mcexec_fork_sync_lock_bridge(void)
{
	pthread_mutex_lock(&fork_sync_mutex);
}

void mcexec_fork_sync_unlock_bridge(void)
{
	pthread_mutex_unlock(&fork_sync_mutex);
}

void mcexec_fork_sync_munmap_bridge(void *fs)
{
	munmap(fs, sizeof(struct fork_sync));
}

void mcexec_fork_sync_free_bridge(void *node)
{
	free(node);
}

void *mcexec_clone_alloc_fork_sync_bridge(void)
{
	struct fork_sync *fs;

	fs = mmap(NULL, sizeof(struct fork_sync), PROT_READ | PROT_WRITE,
			MAP_SHARED | MAP_ANONYMOUS, -1, 0);
	if (fs == (void *)-1)
		return NULL;

	memset(fs, '\0', sizeof(struct fork_sync));
	sem_init(&fs->sem, 1, 0);
	return fs;
}

void *mcexec_clone_alloc_container_bridge(void)
{
	struct fork_sync_container *fsc;

	fsc = malloc(sizeof(struct fork_sync_container));
	if (!fsc)
		return NULL;

	memset(fsc, '\0', sizeof(struct fork_sync_container));
	return fsc;
}

int mcexec_clone_fork_bridge(void)
{
	return fork();
}

void mcexec_clone_fork_failed_bridge(void)
{
	fprintf(stderr, "fork(): error forking child process\n");
}

long mcexec_clone_child_bridge(struct syscall_wait_desc *w, void *sync)
{
	struct fork_sync *fs = sync;
	struct fork_sync_container *fp;
	struct fork_sync_container *fb;
	struct rpgtable_desc rpt;
	int ret = 1;

	ischild = 1;
	close(fd);
	fd = opendev();
	if (fd < 0) {
		fs->status = -errno;
		fprintf(stderr, "ERROR: opening %s\n", dev);
		goto fork_child_sync_pipe;
	}

	rpt.start = w->sr.args[1];
	rpt.len = w->sr.args[2];
	rpt.rpgtable = w->sr.args[3];
	if (ioctl(fd, MCEXEC_UP_CREATE_PPD, &rpt)) {
		fs->status = -errno;
		fprintf(stderr, "ERROR: creating PPD %s\n", dev);
		goto fork_child_sync_pipe;
	}

	init_sigaction();
	thread_data = NULL;
	__dprintf("pid(%d): signals and syscall threads OK\n", getpid());

	if ((ret = ioctl(fd, MCEXEC_UP_GET_NUM_POOL_THREADS)) < 0) {
		fprintf(stderr, "Error: obtaining thread pool count\n");
	}

	if (ret == 1) {
		n_threads = 4;
	}

	if ((ret = init_worker_threads(fd)) != 0) {
		fprintf(stderr, "%s: Error: creating worker threads: %s\n",
			__func__, strerror(-ret));
		close(fd);
		exit(1);
	}

fork_child_sync_pipe:
	for (fp = fork_sync_top; fp;) {
		fb = fp->next;
		if (fp->fs && fp->fs != fs) {
			munmap(fp->fs, sizeof(struct fork_sync));
		}
		free(fp);
		fp = fb;
	}
	fork_sync_top = NULL;

	sem_post(&fs->sem);
	if (fs->status) {
		exit(1);
	}

	pthread_mutex_init(&fork_sync_mutex, NULL);

	while (getppid() != 1 && fs->success == 0) {
		sched_yield();
	}

	if (fs->success == 0) {
		exit(1);
	}

	sem_destroy(&fs->sem);
	munmap(fs, sizeof(struct fork_sync));
	join_all_threads();
	return ret;
}

int mcexec_clone_sem_trywait_bridge(void *fs)
{
	return sem_trywait(&((struct fork_sync *)fs)->sem);
}

int mcexec_clone_waitpid_nohang_bridge(int pid)
{
	int st;

	return waitpid(pid, &st, WNOHANG);
}

void mcexec_clone_sched_yield_bridge(void)
{
	sched_yield();
}

void mcexec_clone_child_after_fork_failed_bridge(void)
{
	fprintf(stderr, "fork(): error with child process after fork\n");
}

void mcexec_clone_sem_destroy_bridge(void *fs)
{
	sem_destroy(&((struct fork_sync *)fs)->sem);
}
#endif

#ifdef MCEXEC_RUST_HELPERS
static long util_thread(struct thread_data_s *my_thread,
		unsigned long rp_rctx, int remote_tid, unsigned long pattr,
		unsigned long uti_info, unsigned long _uti_desc)
{
	return mcexec_util_thread_body(my_thread, rp_rctx, remote_tid, pattr,
			uti_info, _uti_desc);
}

void mcexec_util_thread_missing_desc_bridge(void)
{
	printf("%s: ERROR: uti_desc not found. Add --enable-uti option to mcexec.\n",
	       "util_thread");
}

void mcexec_util_thread_desc_log_bridge(void *desc)
{
	__dprintf("%s: uti_desc=%p\n", "util_thread", desc);
}

void mcexec_util_thread_barrier_init_bridge(void)
{
	pthread_barrier_init(&uti_init_ready, NULL, 2);
}

int mcexec_util_thread_create_worker_bridge(struct thread_data_s **tp_out)
{
	return create_worker_thread(tp_out, &uti_init_ready);
}

void mcexec_util_thread_worker_error_bridge(int rc)
{
	printf("%s: Error: create_worker_thread failed (%d)\n",
	       "util_thread", rc);
}

void mcexec_util_thread_barrier_wait_bridge(void)
{
	pthread_barrier_wait(&uti_init_ready);
}

void mcexec_util_thread_worker_tid_log_bridge(int tid)
{
	__dprintf("%s: worker tid: %d\n", "util_thread", tid);
}

void mcexec_util_thread_intercept_warning_bridge(int rc)
{
	fprintf(stderr, "%s: WARNING: syscall_intercept returned %x\n",
		"util_thread", rc);
}

void mcexec_util_thread_get_ctx_error_bridge(int error)
{
	fprintf(stderr, "%s: Error: MCEXEC_UP_UTI_GET_CTX failed (%d)\n",
		"util_thread", error);
}

void mcexec_util_thread_param_large_bridge(void)
{
	fprintf(stderr, "%s: ERROR: param is too large\n", "util_thread");
}

void mcexec_util_thread_attr_error_bridge(int error)
{
	fprintf(stderr, "%s: error: MCEXEC_UP_UTI_ATTR: %s\n",
		"util_thread", strerror(error));
}

int mcexec_util_thread_switch_ctx_bridge(struct uti_switch_ctx_desc *desc,
		void *lctx, void *rctx)
{
	return switch_ctx(fd, MCEXEC_UP_UTI_SWITCH_CTX, desc, lctx, rctx);
}

void mcexec_util_thread_switch_failed_bridge(int rc)
{
	fprintf(stderr, "%s: ERROR switch_ctx failed (%d)\n",
		"util_thread", rc);
}

void mcexec_util_thread_switch_returned_bridge(int rc)
{
	fprintf(stderr, "%s: ERROR: Returned from switch_ctx (%d)\n",
		"util_thread", rc);
}
#else
static long util_thread(struct thread_data_s *my_thread,
		unsigned long rp_rctx, int remote_tid, unsigned long pattr,
		unsigned long uti_info, unsigned long _uti_desc)
{
	struct uti_get_ctx_desc get_ctx_desc;
	struct uti_switch_ctx_desc switch_ctx_desc;
	int rc = 0;

	struct thread_data_s *tp;

	uti_desc = (struct uti_desc *)_uti_desc;
	if (!uti_desc) {
		printf("%s: ERROR: uti_desc not found. Add --enable-uti option to mcexec.\n",
		       __func__);
		rc = -EINVAL;
		goto out;
	}
	__dprintf("%s: uti_desc=%p\n", __FUNCTION__, uti_desc);

	pthread_barrier_init(&uti_init_ready, NULL, 2);
	if ((rc = create_worker_thread(&tp, &uti_init_ready))) {
		printf("%s: Error: create_worker_thread failed (%d)\n", __FUNCTION__, rc);
		rc = -EINVAL;
		goto out;
	}
	pthread_barrier_wait(&uti_init_ready);
	__dprintf("%s: worker tid: %d\n", __FUNCTION__, tp->tid);


	/* Initialize uti related variables for syscall_intercept */
	uti_desc->fd = fd;

	rc = syscall(888);
	if (rc != -1) {
		fprintf(stderr, "%s: WARNING: syscall_intercept returned %x\n", __FUNCTION__, rc);
	}

	/* Get the remote context, record refill tid */
	get_ctx_desc.rp_rctx = rp_rctx;
	get_ctx_desc.rctx = uti_desc->rctx;
	get_ctx_desc.lctx = uti_desc->lctx;
	get_ctx_desc.uti_refill_tid = tp->tid;

	if ((rc = ioctl(fd, MCEXEC_UP_UTI_GET_CTX, &get_ctx_desc))) {
		fprintf(stderr, "%s: Error: MCEXEC_UP_UTI_GET_CTX failed (%d)\n", __FUNCTION__, errno);
		rc = -errno;
		goto out;
	}

	/* Initialize uti thread info */
	uti_desc->mck_tid = remote_tid;
	uti_desc->key = get_ctx_desc.key;
	uti_desc->pid = getpid();
	uti_desc->tid = gettid();
	uti_desc->uti_info = uti_info;
	
	/* Initialize list of syscall arguments for syscall_intercept */
	if (sizeof(struct syscall_struct) * 11 > page_size) {
		fprintf(stderr, "%s: ERROR: param is too large\n", __FUNCTION__);
		rc = -ENOMEM;
		goto out;
	}

	if (pattr) {
		struct uti_attr_desc desc;

		desc.phys_attr = pattr;
		desc.uti_cpu_set_str = getenv("UTI_CPU_SET");
		if (desc.uti_cpu_set_str) {
			desc.uti_cpu_set_len = strlen(desc.uti_cpu_set_str) + 1;
		}

		if ((rc = ioctl(fd, MCEXEC_UP_UTI_ATTR, &desc))) {
			fprintf(stderr, "%s: error: MCEXEC_UP_UTI_ATTR: %s\n",
				__func__, strerror(errno));
			rc = -errno;
			goto out;
		}
	}

	/* Start intercepting syscalls. Note that it dereferences pointers in uti_desc. */
	uti_desc->start_syscall_intercept = 1;

	/* Save remote and local FS and then contex-switch */
	switch_ctx_desc.rctx = uti_desc->rctx;
	switch_ctx_desc.lctx = uti_desc->lctx;

	if ((rc = switch_ctx(fd, MCEXEC_UP_UTI_SWITCH_CTX, &switch_ctx_desc,
			     uti_desc->lctx, uti_desc->rctx))
	    < 0) {
		fprintf(stderr, "%s: ERROR switch_ctx failed (%d)\n", __FUNCTION__, rc);
		goto out;
	}
	fprintf(stderr, "%s: ERROR: Returned from switch_ctx (%d)\n", __FUNCTION__, rc);
	rc = -EINVAL;

out:
	return rc;
}
#endif

#ifdef MCEXEC_RUST_HELPERS
long mcexec_sched_setaffinity_util_bridge(struct thread_data_s *my_thread,
		unsigned long rp_rctx, int remote_tid, unsigned long pattr,
		unsigned long uti_info, unsigned long uti_desc_arg)
{
	return util_thread(my_thread, rp_rctx, remote_tid, pattr, uti_info,
			uti_desc_arg);
}

void mcexec_sched_setaffinity_invalid_bridge(unsigned long pid_arg)
{
	__eprintf("__NR_sched_setaffinity: invalid argument (%lx)\n",
			pid_arg);
}

long mcexec_perf_event_open_bridge(void)
{
	return open("/dev/null", O_RDONLY);
}

long mcexec_clock_gettime_bridge(int clock_id, struct timespec *tv)
{
	long ret;

	ret = clock_gettime(clock_id, tv);
	SET_ERR(ret);
	return ret;
}

void mcexec_clock_gettime_log_bridge(long sec, long nsec)
{
	__dprintf("clock_gettime=%016ld,%09ld\n", sec, nsec);
}
#endif

#ifndef MCEXEC_RUST_HELPERS
long do_strncpy_from_user(int fd, void *dest, void *src, unsigned long n)
{
	struct strncpy_from_user_desc desc;
	int ret;

	memset(&desc, '\0', sizeof desc);
	desc.dest = dest;
	desc.src = src;
	desc.n = n;

	ret = ioctl(fd, MCEXEC_UP_STRNCPY_FROM_USER, (unsigned long)&desc);
	if (ret) {
		ret = -errno;
		perror("strncpy_from_user:ioctl");
		return ret;
	}

	return desc.result;
}
#endif

#ifndef MCEXEC_RUST_HELPERS
int close_cloexec_fds(int mcos_fd)
{
	int fd;
	int max_fd = sysconf(_SC_OPEN_MAX);
	
	for (fd = 0; fd < max_fd; ++fd) {
		int flags;

		if (fd == mcos_fd)
			continue;
		
		flags = fcntl(fd, F_GETFD, 0);
		if (flags & FD_CLOEXEC) {
			close(fd);
		}
	}

	/*
	 * NOTE: a much more elegant solution would be to iterate fds in proc,
	 * but opendir() seems to change some state in glibc which makes some
	 * of the execve() LTP tests fail. 
	 * TODO: investigate this later.
	 *
	DIR *d;
	struct dirent *de;
	struct dirent __de;

	if ((d = opendir("/proc/self/fd")) == NULL) {
		fprintf(stderr, "error: opening /proc/self/fd \n");
		return -1;
	}

	while (!readdir_r(d, &__de, &de) && de != NULL) {
		long l;
		char *e = NULL;
		int flags;
		
		if (de->d_name[0] == '.')
			continue;

		errno = 0;
		l = strtol(de->d_name, &e, 10);
		if (errno != 0 || !e || *e) {
			closedir(d);
			return -1;
		}

		fd = (int)l;

		if ((long)fd != l) {
			closedir(d);
			return -1;
		}

		if (fd == dirfd(d))
			continue;

		if (fd == mcos_fd)
			continue;
		
		fprintf(stderr, "checking: %d\n", fd);

		flags = fcntl(fd, F_GETFD, 0);
		if (flags & FD_CLOEXEC) {
			fprintf(stderr, "closing: %d\n", fd);
			close(fd);
		}
	}

	closedir(d);
	*/
	
	return 0;
}
#endif

struct overlay_fd {
	int fd; /* associated fd, points to mckernel side */
	int getdents_fd; /* non-seekable mckernel fd */
	int linux_fd; /* linux fd, -1 if not opened */
	struct list_head link;
	char linux_path[PATH_MAX]; /* linux path */
	char mck_path[PATH_MAX]; /* mckernel path */
	size_t pathlen;
	void *mck_dirents; /* cache of mckernel dirents to filter duplicates */
	size_t mck_dirents_size;
	void *linux_dirents; /* cache of filtered Linux dirents */
	size_t linux_dirents_size;
};
struct list_head overlay_fd_list = { &(overlay_fd_list), &(overlay_fd_list) };

#ifndef MCEXEC_RUST_HELPERS
static void overlay_list_add(struct list_head *new, struct list_head *head)
{
	head->next->prev = new;
	new->next = head->next;
	new->prev = head;
	head->next = new;
}

static void overlay_list_del(struct list_head *entry)
{
	entry->next->prev = entry->prev;
	entry->prev->next = entry->next;
	entry->next = LIST_POISON1;
	entry->prev = LIST_POISON2;
}
#else
#define overlay_list_add(new, head) mcexec_overlay_list_add_body((new), (head))
#define overlay_list_del(entry) mcexec_overlay_list_del_body(entry)
#endif

#ifndef MCEXEC_RUST_HELPERS
void overlay_addfd(int fd, const char *path)
{
	struct overlay_fd *ofd;
	int n;
	char mcos[32], *real_path;
	const char *prefix = "";

	if (strncmp(path, "/proc/", 6) == 0)
		prefix = "/proc";
	else if (strncmp(path, "/sys/", 5) != 0)
		return;

	n = snprintf(mcos, 32, "mcos%d", mcosid);
	real_path = strstr(path, mcos);
	if (!real_path)
		return;

	/* point to first character after mcos string */
	real_path += n;

	ofd = malloc(sizeof(*ofd));
	if (!ofd) {
		fprintf(stderr, "%s: out of memory\n", __func__);
		return;
	}

	ofd->fd = fd;
	ofd->getdents_fd = -1;
	ofd->linux_fd = -1;
	ofd->mck_dirents = NULL;
	ofd->mck_dirents_size = 0;
	ofd->linux_dirents = NULL;
	ofd->linux_dirents_size = 0;
	ofd->pathlen = snprintf(ofd->linux_path, PATH_MAX, "%s%s",
				prefix, real_path);
	strncpy(ofd->mck_path, path, PATH_MAX);

	pthread_spin_lock(&overlay_fd_lock);
	overlay_list_add(&ofd->link, &overlay_fd_list);
	pthread_spin_unlock(&overlay_fd_lock);
}
#else
void mcexec_overlay_addfd_path_too_long_bridge(void)
{
	fprintf(stderr, "%s: path too long\n", "overlay_addfd");
}

int mcexec_overlay_addfd_publish_bridge(int fd, const char *linux_path,
		const char *mck_path, size_t pathlen)
{
	struct overlay_fd *ofd;

	ofd = malloc(sizeof(*ofd));
	if (!ofd) {
		fprintf(stderr, "%s: out of memory\n", "overlay_addfd");
		return -ENOMEM;
	}

	ofd->fd = fd;
	ofd->getdents_fd = -1;
	ofd->linux_fd = -1;
	ofd->mck_dirents = NULL;
	ofd->mck_dirents_size = 0;
	ofd->linux_dirents = NULL;
	ofd->linux_dirents_size = 0;
	ofd->pathlen = pathlen;
	strncpy(ofd->linux_path, linux_path, PATH_MAX);
	strncpy(ofd->mck_path, mck_path, PATH_MAX);

	pthread_spin_lock(&overlay_fd_lock);
	overlay_list_add(&ofd->link, &overlay_fd_list);
	pthread_spin_unlock(&overlay_fd_lock);

	return 0;
}
#endif

#ifndef MCEXEC_RUST_HELPERS
void overlay_delfd(int fd)
{
	struct overlay_fd *ofd;

	pthread_spin_lock(&overlay_fd_lock);
	for (ofd = ((typeof(*ofd) *)((char *)((&overlay_fd_list)->next) - offsetof(typeof(*ofd), link))); &ofd->link != (&overlay_fd_list); ofd = ((typeof(*ofd) *)((char *)(ofd->link.next) - offsetof(typeof(*ofd), link)))) {
		if (ofd->fd == fd) {
			overlay_list_del(&ofd->link);
			if (ofd->getdents_fd != -1)
				close(ofd->getdents_fd);
			if (ofd->linux_fd != -1)
				close(ofd->linux_fd);
			free(ofd->mck_dirents);
			free(ofd->linux_dirents);
			free(ofd);
			break;
		}
	}
	pthread_spin_unlock(&overlay_fd_lock);
}
#else
void mcexec_overlay_delfd_bridge(int fd)
{
	struct overlay_fd *ofd;

	pthread_spin_lock(&overlay_fd_lock);
	for (ofd = ((typeof(*ofd) *)((char *)((&overlay_fd_list)->next) - offsetof(typeof(*ofd), link))); &ofd->link != (&overlay_fd_list); ofd = ((typeof(*ofd) *)((char *)(ofd->link.next) - offsetof(typeof(*ofd), link)))) {
		if (ofd->fd == fd) {
			overlay_list_del(&ofd->link);
			if (ofd->getdents_fd != -1)
				close(ofd->getdents_fd);
			if (ofd->linux_fd != -1)
				close(ofd->linux_fd);
			free(ofd->mck_dirents);
			free(ofd->linux_dirents);
			free(ofd);
			break;
		}
	}
	pthread_spin_unlock(&overlay_fd_lock);
}
#endif

/* List of blacklisted paths
 *
 * Since we abuse sscanf, there are a few constraints:
 *  - scanf cannot be used to differenciate strings with no pattern,
 *    so the last character has to be a pattern. If it is not a number,
 *    it is compared by hand.
 *  - always make previous patterns ignore patterns (%*..)
 *  - symlinks can be assumed to be resolved previously
 */

#ifndef MCEXEC_RUST_HELPERS
struct overlay_blacklist_entry {
	char *pattern;
	int cpuid;
	int nodeid;
	char lastchar;
} overlay_blacklists[] = {
	{ "/sys/devices/system/cpu/cpu%d", 0, -1, -1 },
	{ "/sys/devices/system/cpu/cpu%d/node%d", 0, 1, -1 },
	{ "/sys/bus/cpu/devices/cpu%d", 0, -1, -1 },
	{ "/sys/bus/cpu/drivers/processor/cpu%d", 0, -1, -1 },
	{ "/sys/devices/system/node/node%d", -1, 0, -1 },
	{ "/sys/devices/system/node/node%d/cpu%d", 1, 0, -1 },
	{ "/sys/devices/system/node/node%d/memor%c", -1, -1, 'y' },
	{ "/sys/bus/node/devices/node%d", -1, 0, -1 },
	{ "/sys/devices/system/node/has%c", -1, -1, '_' },
	{ "/sys/fs/cgrou%c", -1, -1, 'p' },
	{ "/sys/devices/pci%*[^/]/%*[^/]/local_cpu%c", -1, -1, 's' },
	{ 0 },
};

int overlay_blacklist(const char *path)
{
	int ids[3];
	struct overlay_blacklist_entry *entry;
	int rc;
	int pid = -1;
	int tid = -1;

#ifdef MCEXEC_RUST_HELPERS
	if (mcexec_parse_proc_task_ids_result(path, getpid(), &pid, &tid)) {
		char check_path[PATH_MAX];
		struct stat sb;

		rc = mcexec_proc_task_check_path_result(check_path,
				sizeof(check_path), mcosid, pid, tid);
		if (rc < 0)
			return -ENOENT;
		if (pid > 0 && tid > 0 && stat(check_path, &sb) < 0)
			return -ENOENT;
	}
#else
	/* handle /proc/N/task/tid/ files */
	if (sscanf(path, "/proc/self/task/%d/", &tid) == 1) {
		pid = getpid();
	}
	else {
		sscanf(path, "/proc/%d/task/%d/", &pid, &tid);
	}

	if (pid > 0 && tid > 0) {
		char check_path[PATH_MAX];
		struct stat sb;

		sprintf(check_path, "/proc/mcos%d/%d/task/%d",
			mcosid, pid, tid);
		if (stat(check_path, &sb) < 0)
			return -ENOENT;
	}
#endif

	if (strncmp(path, "/sys/", 5))
		return 0;

	for (entry = overlay_blacklists; entry->pattern; entry++) {
		memset(ids, 0, sizeof(ids));
		rc = sscanf(path, entry->pattern, ids, ids + 1, ids + 2);
		if (rc < (entry->cpuid != -1 ? 1 : 0) +
			 (entry->nodeid != -1 ? 1 : 0) +
			 (entry->lastchar != (char)-1 ? 1 : 0))
			continue;
		if (entry->lastchar != (char)-1 && ids[rc - 1] != entry->lastchar)
			continue;
		if (entry->cpuid == -1 && entry->nodeid == -1)
			return -ENOENT;
		if (entry->cpuid != -1 && ids[entry->cpuid] >= ncpu)
			return -ENOENT;
		if (entry->nodeid != -1 && ids[entry->nodeid] >= nnodes)
			return -ENOENT;
		if (entry->cpuid != -1 && entry->nodeid != -1 &&
		    !CPU_ISSET_S(ids[entry->cpuid], cpu_set_size,
				 numa_node_set(ids[entry->nodeid])))
			return -ENOENT;
	}

	return 0;
}
#else
int mcexec_overlay_mcosid_bridge(void)
{
	return mcosid;
}

int mcexec_overlay_stat_exists_bridge(const char *path)
{
	struct stat sb;

	return stat(path, &sb) < 0 ? -errno : 0;
}

int mcexec_overlay_cpu_in_node_bridge(int cpu, int node)
{
	if (node < 0 || node >= nnodes || cpu < 0 || cpu >= ncpu)
		return 0;

	return CPU_ISSET_S(cpu, cpu_set_size, numa_node_set(node));
}
#endif

#ifndef MCEXEC_RUST_HELPERS
static int is_proc_task_leaf_path(const char *path)
{
	int pid, tid, offset = 0;

	if (sscanf(path, "/proc/self/task/%d/%n", &tid, &offset) == 1 &&
	    path[offset] != '\0') {
		return 1;
	}

	offset = 0;
	if (sscanf(path, "/proc/%d/task/%d/%n", &pid, &tid, &offset) == 2 &&
	    path[offset] != '\0') {
		return 1;
	}

	return 0;
}
#endif

#ifndef MCEXEC_RUST_HELPERS
static int mapped_proc_task_parent_exists(const char *mapped)
{
	char parent[PATH_MAX];
	char *slash;
	struct stat sb;

	strncpy(parent, mapped, PATH_MAX);
	parent[PATH_MAX - 1] = '\0';

	slash = strrchr(parent, '/');
	if (!slash) {
		return 0;
	}
	*slash = '\0';

	return stat(parent, &sb) == 0;
}
#endif

#ifdef MCEXEC_RUST_HELPERS
int mcexec_overlay_enable_uti_bridge(void)
{
	return enable_uti;
}

int mcexec_overlay_find_libdir_bridge(char *out, size_t size)
{
	return find_libdir(out, size);
}

ssize_t mcexec_overlay_readlink_bridge(const char *path, char *out,
		size_t size)
{
	return readlink(path, out, size);
}

int mcexec_overlay_lstat_is_symlink_bridge(const char *path, int *is_symlink)
{
	struct stat sb;

	if (lstat(path, &sb) == -1)
		return -errno;

	*is_symlink = S_ISLNK(sb.st_mode);
	return 0;
}

int mcexec_overlay_stat_errno_bridge(const char *path)
{
	struct stat sb;

	return stat(path, &sb) == -1 ? errno : 0;
}

void mcexec_overlay_considering_bridge(int dirfd, const char *path)
{
	__dprintf("considering fd %d path %s\n", dirfd, path);
}

void mcexec_overlay_fd_path_truncated_bridge(int dirfd)
{
	fprintf(stderr, "%s: /proc/self/fd/%d path truncated\n",
		"overlay_path", dirfd);
}

void mcexec_overlay_readlink_fd_failed_bridge(int dirfd, int error)
{
	fprintf(stderr, "%s: readlink /proc/self/fd/%d failed: %d\n",
		"overlay_path", dirfd, error);
}

void mcexec_overlay_truncated_bridge(const char *path)
{
	fprintf(stderr, "%s: %s truncated\n", "overlay_path", path);
}

void mcexec_overlay_getcwd_failed_bridge(int error)
{
	fprintf(stderr, "%s: could not getcwd(): %d\n",
		"overlay_path", error);
}

void mcexec_overlay_glued_bridge(const char *path)
{
	__dprintf("glued to %s\n", path);
}

void mcexec_overlay_find_libdir_failed_bridge(void)
{
	fprintf(stderr, "error: failed to find library directory\n");
}

void mcexec_overlay_replaced_bridge(const char *path, const char *mapped)
{
	__dprintf("%s: %s replaced with %s\n", "overlay_path", path, mapped);
}

void mcexec_overlay_trying_bridge(const char *path, int error)
{
	__dprintf("trying %s: %d\n", path, error);
}

void mcexec_overlay_blacklisted_bridge(const char *path)
{
	__dprintf("blacklisted %s\n", path);
}
#else

/* Fixup paths that need to point to mckernel files
 * dirfd/in are openat/fstatat/faccessat arguments,
 * buf is a buffer we can dirty assumed to be PATH_MAX long
 * returns path to use *with dirfd* if it was provided.
 */
const char *
overlay_path(int dirfd, const char *in, char *buf, int *resolvelinks)
{
	const char *path = in;
	char *linkpath, *tmppath;
	char tmpbuf[PATH_MAX], tmpbuf2[PATH_MAX];

	struct stat sb;
	ssize_t n;
	int rc;

	if (resolvelinks) {
		*resolvelinks = 0;
	}

	__dprintf("considering fd %d path %s\n", dirfd, in);

	if (dirfd != AT_FDCWD && in[0] != '/') {
#ifdef MCEXEC_RUST_HELPERS
		rc = mcexec_proc_self_fd_path_result(buf, PATH_MAX, dirfd);
		if (rc < 0) {
			fprintf(stderr,
				"%s: /proc/self/fd/%d path truncated\n",
				__func__, dirfd);
			return in;
		}
#else
		snprintf(buf, PATH_MAX, "/proc/self/fd/%d", dirfd);
#endif

		n = readlink(buf, tmpbuf, PATH_MAX);
		if (n == PATH_MAX || n < 0) {
			if (n == PATH_MAX)
				errno = ENAMETOOLONG;
			fprintf(stderr,
				"%s: readlink /proc/self/fd/%d failed: %d\n",
				__func__, dirfd, errno);
			return in;
		}
		tmpbuf[n] = 0;

#ifdef MCEXEC_RUST_HELPERS
		n = mcexec_join_path_inplace_result(tmpbuf, PATH_MAX, in);
		if (n < 0) {
			fprintf(stderr, "%s: %s truncated\n",
				__func__, tmpbuf);
			return in;
		}
#else
		if (n > 0 && tmpbuf[n-1] == '/')
			n--;

		n += snprintf(tmpbuf + n, PATH_MAX - n, "/%s", in);
		if (n >= PATH_MAX) {
			fprintf(stderr, "%s: %s truncated\n",
				__func__, tmpbuf);
			return in;
		}
#endif

		path = tmpbuf;
	} else if (in[0] != '/') {
		path = getcwd(tmpbuf, PATH_MAX);
		if (path == NULL) {
			fprintf(stderr, "%s: could not getcwd(): %d\n",
				__func__, errno);
			return in;
		}

#ifdef MCEXEC_RUST_HELPERS
		n = mcexec_join_path_inplace_result(tmpbuf, PATH_MAX, in);
		if (n < 0) {
			fprintf(stderr, "%s: %s truncated\n",
				__func__, tmpbuf);
			return in;
		}
#else
		n = strlen(tmpbuf);
		if (n > 0 && tmpbuf[n-1] == '/')
			n--;

		n += snprintf(tmpbuf + n, PATH_MAX - n, "/%s", in);
		if (n >= PATH_MAX) {
			fprintf(stderr, "%s: %s truncated\n",
				__func__, tmpbuf);
			return in;
		}
#endif

		path = tmpbuf;
	}

	__dprintf("glued to %s\n", path);

#ifdef MCEXEC_RUST_HELPERS
	if (mcexec_path_is_dev_xpmem_result(path))
		return "/dev/null";
#else
	if (!strcmp(path, "/dev/xpmem"))
		return "/dev/null";
#endif


#ifdef MCEXEC_RUST_HELPERS
	if (enable_uti && mcexec_path_has_libuti_result(path)) {
		char libdir[PATH_MAX];

		if (find_libdir(libdir, sizeof(libdir)) < 0) {
			fprintf(stderr, "error: failed to find library directory\n");
			return in;
		}
		n = mcexec_overlay_uti_path_result(libdir, path, buf,
				PATH_MAX);
		if (n < 0) {
			fprintf(stderr, "%s: %s truncated\n",
				__func__, path);
			return in;
		}
		__dprintf("%s: %s replaced with %s\n",
			  __func__, path, buf);
		goto checkexist;
	}
#else
	if (enable_uti && strstr(path, "libuti.so")) {
		char libdir[PATH_MAX];
		char *basename;

		basename = strrchr(path, '/');
		if (basename == NULL) {
			basename = (char *)path;
		} else {
			basename++;
		}
		if (find_libdir(libdir, sizeof(libdir)) < 0) {
			fprintf(stderr, "error: failed to find library directory\n");
			return in;
		}
		n = snprintf(buf, PATH_MAX, "%s/mck/%s",
			     libdir, basename);
		__dprintf("%s: %s replaced with %s\n",
			  __func__, path, buf);
		goto checkexist;
	}
#endif


#ifdef MCEXEC_RUST_HELPERS
	rc = mcexec_overlay_proc_self_path_result(path, mcosid, getpid(),
			buf, PATH_MAX);
	if (rc > 0) {
		n = rc;
		goto checkexist;
	}
	if (rc < 0) {
		fprintf(stderr, "%s: %s truncated\n", __func__, path);
		return in;
	}

	rc = mcexec_overlay_proc_path_result(path, mcosid, buf, PATH_MAX);
	if (rc > 0) {
		n = rc;
		goto checkexist;
	}
	if (rc < 0) {
		fprintf(stderr, "%s: %s truncated\n", __func__, path);
		return in;
	}
#else
	if (!strncmp(path, "/proc/self", 10) &&
	    (path[10] == '/' || path[10] == '\0')) {
		n = snprintf(buf, PATH_MAX, "/proc/mcos%d/%d%s",
			     mcosid, getpid(), path + 10);
		goto checkexist;
	}

	if (!strncmp(path, "/proc", 5) &&
	    (path[5] == '/' || path[5] == '\0')) {
		n = snprintf(buf, PATH_MAX, "/proc/mcos%d%s",
			     mcosid, path + 5);
		goto checkexist;
	}
#endif

	if (!strncmp(path, "/sys", 4) &&
	    (path[4] == '/' || path[4] == '\0')) {
		goto checkexist_resolvelinks;
	}

	return in;

checkexist_resolvelinks:
	/* now, for the fun part: since /sys is full of symlinks, we need
	 * to check every single component of that path for links
	 * (in the real path!) and consider the final destination
	 */
	if (path != tmpbuf) {
		strcpy(tmpbuf, path);
		path = tmpbuf;
	}
	linkpath = tmpbuf;
	while ((linkpath = strchr(linkpath + 1, '/'))) {
		linkpath[0] = 0;
		rc = lstat(tmpbuf, &sb);

		/* Could not exist on linux - no more links */
		if (rc == -1) {
			linkpath[0] = '/';
			break;
		}

		if (S_ISLNK(sb.st_mode)) {
			n = readlink(tmpbuf, buf, PATH_MAX);
			if (n >= PATH_MAX || n < 0)
				return in;
			buf[n] = 0;

			if (buf[0] == '/') {
				/* cannot snprintf from same source and dest */
				n = snprintf(tmpbuf2, PATH_MAX, "%s/%s", buf,
					     linkpath + 1);
				if (n >= PATH_MAX)
					return in;
				strcpy(tmpbuf, tmpbuf2);
				linkpath = tmpbuf;
			} else {
				strcpy(tmpbuf2, linkpath + 1);

				/* remove link component from path */
				linkpath = strrchr(tmpbuf, '/');
				if (linkpath != tmpbuf)
					linkpath[0] = 0;
				else
					linkpath[1] = 0;

				/* go back as many / as there are ..
				 * otherwise kernel would need intermediate
				 * directories to exist on mckernel side */
				tmppath = buf;
				while (!strncmp(tmppath, "../", 3)) {
					linkpath = strrchr(tmpbuf, '/');
					if (!linkpath) // should never happen
						return in;
					if (linkpath != tmpbuf)
						linkpath[0] = 0;
					tmppath += 3;
				}
				n = linkpath - tmpbuf;
				n += snprintf(linkpath, PATH_MAX - n,
					      "/%s/%s", tmppath, tmpbuf2);
				if (n >= PATH_MAX)
					return in;
			}

			if (resolvelinks) {
				*resolvelinks = 1;
			}
		}
		linkpath[0] = '/';
		linkpath++;
	}

#ifdef MCEXEC_RUST_HELPERS
	{
		size_t mapped_offset = 0;

		rc = mcexec_overlay_sys_path_result(path, mcosid, buf,
				PATH_MAX, &mapped_offset);
		if (rc <= 0)
			return in;
		n = rc;
		path = buf + mapped_offset;
	}
#else
	n = snprintf(buf, PATH_MAX, "/sys/devices/virtual/mcos/mcos%d",
		     mcosid);
	tmppath = buf + n;
	n += snprintf(buf + n, PATH_MAX - n, "/sys/%s", path + 5);
	path = tmppath;
#endif

checkexist:
	if (n >= PATH_MAX) {
		fprintf(stderr, "%s: %s truncated\n", __func__, buf);
		return in;
	}

#ifdef MCEXEC_RUST_HELPERS
	{
		size_t normalized_len = (size_t)n;

		rc = mcexec_normalize_overlay_path_result(buf,
				&normalized_len);
		if (rc < 0)
			return in;
		n = normalized_len;
	}
#else
	while ((tmppath = strstr(buf, "//"))) {
		memmove(tmppath, tmppath + 1, PATH_MAX - (tmppath + 1 - buf));
		n--;
	}
	while (n > 0 && buf[n-1] == '/') {
		buf[n-1] = 0;
		n--;
	}
#endif

	rc = stat(buf, &sb);
	__dprintf("trying %s: %d\n", buf, rc == -1 ? errno : 0);
	if (rc == -1 && errno == ENOENT) {
		if (is_proc_task_leaf_path(path) &&
		    mapped_proc_task_parent_exists(buf)) {
			return buf;
		}
		if (overlay_blacklist(path)) {
			__dprintf("blacklisted %s\n", path);
			return "/nonexisting";
		}
		return in;
	}

	return buf;
}
#endif

struct linux_dirent {
	unsigned long  d_ino;     /* Inode number */
	unsigned long  d_off;     /* Offset to next linux_dirent */
	unsigned short d_reclen;  /* Length of this linux_dirent */
	char           d_name[];  /* Filename (null-terminated) */
				  /* length is actually (d_reclen - 2 -
				   * offsetof(struct linux_dirent, d_name)) */
/*	char           pad;       // Zero padding byte
 *	char           d_type;    // File type (since linux 2.6.4) at reclen-1
 */
};
struct linux_dirent64 {
	ino64_t        d_ino;    /* 64-bit inode number */
	off64_t        d_off;    /* 64-bit offset to next structure */
	unsigned short d_reclen; /* Size of this dirent */
	unsigned char  d_type;   /* File type */
	char           d_name[]; /* Filename (null-terminated) */
};

static inline unsigned short dirent_reclen(int sysnum, void *_dirp)
{

#ifdef MCEXEC_RUST_HELPERS
#ifdef	__NR_getdents
		if (sysnum == __NR_getdents) {
			return mcexec_dirent32_reclen_result(_dirp);
		}
#endif
		if (sysnum == __NR_getdents64) {
			return mcexec_dirent64_reclen_result(_dirp);
		}
#endif
#ifdef	__NR_getdents
		if (sysnum == __NR_getdents) {
			struct linux_dirent *dirp = _dirp;

			return dirp->d_reclen;
		}
#endif
		if (sysnum == __NR_getdents64) {
			struct linux_dirent64 *dirp = _dirp;

			return dirp->d_reclen;
		}
		fprintf(stderr, "%s: unexpected syscall number %d\n",
			__func__, sysnum);
		exit(-1);
}

static inline char *dirent_name(int sysnum, void *_dirp)
{

#ifdef MCEXEC_RUST_HELPERS
#ifdef	__NR_getdents
		if (sysnum == __NR_getdents) {
			return mcexec_dirent32_name_result(_dirp);
		}
#endif
		if (sysnum == __NR_getdents64) {
			return mcexec_dirent64_name_result(_dirp);
		}
#endif
#ifdef	__NR_getdents
		if (sysnum == __NR_getdents) {
			struct linux_dirent *dirp = _dirp;

			return dirp->d_name;
		}
#endif
		if (sysnum == __NR_getdents64) {
			struct linux_dirent64 *dirp = _dirp;

			return dirp->d_name;
		}
		fprintf(stderr, "%s: unexpected syscall number %d\n",
			__func__, sysnum);
		exit(-1);
}

static inline void *dirent_off(int sysnum, void *_dirp)
{

#ifdef MCEXEC_RUST_HELPERS
#ifdef	__NR_getdents
		if (sysnum == __NR_getdents) {
			return mcexec_dirent32_off_result(_dirp);
		}
#endif
		if (sysnum == __NR_getdents64) {
			return mcexec_dirent64_off_result(_dirp);
		}
#endif
#ifdef	__NR_getdents
		if (sysnum == __NR_getdents) {
			struct linux_dirent *dirp = _dirp;

			return &(dirp->d_off);
		}
#endif
		if (sysnum == __NR_getdents64) {
			struct linux_dirent64 *dirp = _dirp;

			return &(dirp->d_off);
		}
		fprintf(stderr, "%s: unexpected syscall number %d\n",
			__func__, sysnum);
		exit(-1);
}

#ifdef MCEXEC_RUST_HELPERS
#define dirent_is64(sysnum) mcexec_dirent_is64_body((sysnum), __NR_getdents64)

void *mcexec_overlay_getdents_find_bridge(int fd)
{
	struct overlay_fd *ofd_iter;

	pthread_spin_lock(&overlay_fd_lock);
	for (ofd_iter = ((typeof(*ofd_iter) *)((char *)((&overlay_fd_list)->next) - offsetof(typeof(*ofd_iter), link))); &ofd_iter->link != (&overlay_fd_list); ofd_iter = ((typeof(*ofd_iter) *)((char *)(ofd_iter->link.next) - offsetof(typeof(*ofd_iter), link)))) {
		if (ofd_iter->fd == fd) {
			__dprintf("found overlay cache entry (%s)\n",
					ofd_iter->linux_path);
			pthread_spin_unlock(&overlay_fd_lock);
			return ofd_iter;
		}
	}
	pthread_spin_unlock(&overlay_fd_lock);

	return NULL;
}

int mcexec_overlay_getdents_hide_orig_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;
	size_t len;

	if (!ofd || strncmp(ofd->linux_path, "/proc", 5))
		return 0;

	len = strlen(ofd->linux_path);
	return len >= 4 && !strncmp(ofd->linux_path + len - 4, "task", 4);
}

const char *mcexec_overlay_getdents_linux_path_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->linux_path;
}

size_t mcexec_overlay_getdents_pathlen_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->pathlen;
}

void *mcexec_overlay_getdents_mck_dirents_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->mck_dirents;
}

size_t mcexec_overlay_getdents_mck_size_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->mck_dirents_size;
}

void *mcexec_overlay_getdents_linux_dirents_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->linux_dirents;
}

size_t mcexec_overlay_getdents_linux_size_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->linux_dirents_size;
}

int mcexec_overlay_getdents_mck_fd_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	if (ofd->getdents_fd == -1) {
		ofd->getdents_fd = open(ofd->mck_path, O_RDONLY | O_DIRECTORY);
		if (ofd->getdents_fd < 0) {
			int error = errno;

			if (error != ENOENT) {
				fprintf(stderr, "%s: could not open %s: %d\n",
					"overlay_getdents", ofd->mck_path,
					error);
			}
			return -error;
		}
	}

	return ofd->getdents_fd;
}

int mcexec_overlay_getdents_linux_fd_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	if (ofd->linux_fd == -1) {
		ofd->linux_fd = open(ofd->linux_path, O_RDONLY | O_DIRECTORY);
		if (ofd->linux_fd < 0) {
			int error = errno;

			if (error != ENOENT) {
				fprintf(stderr, "%s: could not open %s: %d\n",
					"overlay_getdents", ofd->linux_path,
					error);
			}
			return -error;
		}
	}

	return ofd->linux_fd;
}

int mcexec_overlay_getdents_append_mck_bridge(void *opaque,
		const void *dirp, size_t len, int is64)
{
	struct overlay_fd *ofd = opaque;
	void *newbuf;
	int rc;

	newbuf = realloc(ofd->mck_dirents, ofd->mck_dirents_size + len);
	if (!newbuf) {
		fprintf(stderr, "%s: not enough memory (%zd)",
			"overlay_getdents", ofd->mck_dirents_size + len);
		return -ENOMEM;
	}
	ofd->mck_dirents = newbuf;
	memcpy(ofd->mck_dirents + ofd->mck_dirents_size, dirp, len);

	rc = mcexec_dirent_rewrite_offsets_result(ofd->mck_dirents,
			ofd->mck_dirents_size, ofd->mck_dirents_size + len,
			0, is64);
	if (rc < 0)
		return rc;

	ofd->mck_dirents_size += len;
	return 0;
}

int mcexec_overlay_getdents_append_linux_bridge(void *opaque,
		const void *dirp, size_t len, int is64, int old_ret)
{
	struct overlay_fd *ofd = opaque;
	void *newbuf;
	int rc;

	newbuf = realloc(ofd->linux_dirents, ofd->linux_dirents_size + len);
	if (!newbuf) {
		fprintf(stderr, "%s: not enough memory (%zd)",
			"overlay_getdents", ofd->linux_dirents_size + len);
		return old_ret;
	}
	ofd->linux_dirents = newbuf;
	memcpy(ofd->linux_dirents + ofd->linux_dirents_size, dirp, len);
	ofd->linux_dirents_size += len;

	rc = mcexec_dirent_rewrite_offsets_result(ofd->linux_dirents, 0,
			ofd->linux_dirents_size, ofd->mck_dirents_size,
			is64);
	if (rc < 0)
		return rc;

	return 0;
}

void mcexec_overlay_getdents_offset_bridge(long offset)
{
	__dprintf("offset: %ld\n", offset);
}

void mcexec_overlay_getdents_upper_bridge(int mck_ret, int ret,
		unsigned int count)
{
	__dprintf("getdents from upper: mck_ret: %d, ret: %d, count: %d\n",
		  mck_ret, ret, count);
}

void mcexec_overlay_getdents_lower_failed_bridge(int error)
{
	fprintf(stderr, "%s: linux getdents failed: %d\n",
		"overlay_getdents", error);
}

void mcexec_overlay_getdents_blacklisted_bridge(const char *path)
{
	__dprintf("blacklisted: %s\n", path);
}

void mcexec_overlay_getdents_dupe_bridge(const char *name)
{
	__dprintf("dupe: %s\n", name);
}

void mcexec_overlay_getdents_lower_bridge(int linux_ret, int ret,
		unsigned int count)
{
	__dprintf("getdents from lower: linux_ret: %d, ret: %d, count: %d\n",
		  linux_ret, ret, count);
}

void mcexec_overlay_getdents_offset_too_large_bridge(long offset,
		size_t mck_size, size_t linux_size)
{
	fprintf(stderr, "%s: offset (%ld) is too large (upper: %ld, lower: %ld)\n",
		"overlay_getdents", offset, mck_size, linux_size);
}

void mcexec_overlay_getdents_upper_small_bridge(void)
{
	__dprintf("upper: Result buffer is too small\n");
}

void mcexec_overlay_getdents_lower_small_bridge(void)
{
	__dprintf("lower: Result buffer is too small\n");
}

void mcexec_overlay_getdents_mck_size_log_bridge(size_t size, long offset,
		int len, unsigned int count)
{
	__dprintf("mck_dirents_size: %ld, offset: %ld, mck_len: %d, count: %d\n",
		  size, offset, len, count);
}

void mcexec_overlay_getdents_linux_size_log_bridge(size_t size, long offset,
		int len, unsigned int count)
{
	__dprintf("linux_dirents_size: %ld, offset: %ld, linux_len: %d, count: %d\n",
		  size, offset, len, count);
}
#else

int copy_dirents(void *_dirp, void *dirents, size_t dirents_size,
		 off_t offset, unsigned int *count, int sysnum)
{
	off_t max_len;
	int len;
	void *dirp_iter;
	unsigned short reclen;

	max_len = dirents_size - offset > *count ?
		*count : dirents_size - offset;
	__dprintf("max_len: %ld\n", max_len);
	for (len = 0; len < max_len;) {
		dirp_iter = dirents + offset + len;
		reclen = dirent_reclen(sysnum, dirp_iter);

		/* early exit on record boundary */
		if (len + reclen > max_len) {
			/* don't try to copy lower */
			*count = 0;
			__dprintf("early exit: len: %d, reclen: %d, max_len: %ld\n",
			       len, reclen, max_len);
			goto out;
		}

		memcpy(_dirp + len, dirp_iter, reclen);
		len += reclen;
	}
	*count -= len;
out:
	return len;
}
#endif

#ifndef MCEXEC_RUST_HELPERS
int overlay_getdents(int sysnum, int fd, void *_dirp, unsigned int count)
{
	void *dirp = NULL;
	void *linux_dirp_iter;
#ifndef MCEXEC_RUST_HELPERS
	void *mck_dirp_iter;
#endif
	int ret, ret_before_edit;
	int mck_ret = 0, pos;
	int linux_ret = 0;
#ifndef MCEXEC_RUST_HELPERS
	int mcpos;
#endif
	unsigned short reclen;
	struct overlay_fd *ofd = NULL, *ofd_iter;
	int hide_orig = 0;
	off_t offset;
	char ofd_path[PATH_MAX];
	int mck_len, linux_len;
#ifdef MCEXEC_RUST_HELPERS
	int helper_rc;
#endif

	pthread_spin_lock(&overlay_fd_lock);
	for (ofd_iter = ((typeof(*ofd_iter) *)((char *)((&overlay_fd_list)->next) - offsetof(typeof(*ofd_iter), link))); &ofd_iter->link != (&overlay_fd_list); ofd_iter = ((typeof(*ofd_iter) *)((char *)(ofd_iter->link.next) - offsetof(typeof(*ofd_iter), link)))) {
		if (ofd_iter->fd == fd) {
			ofd = ofd_iter;
			__dprintf("found overlay cache entry (%s)\n",
					ofd->linux_path);
			break;
		}
	}
	pthread_spin_unlock(&overlay_fd_lock);

	/* special case for /proc/N/task */
	if (ofd && !strncmp(ofd->linux_path, "/proc", 5) &&
	    !strncmp(ofd->linux_path + strlen(ofd->linux_path) - 4,
		     "task", 4)) {
		hide_orig = 1;
	}

	/* not a directory we overlay or hiding lower fs */
	if (ofd == NULL || hide_orig) {
		ret = syscall(sysnum, fd, _dirp, count);
		if (ret == -1) {
			ret = -errno;
			goto err;
		}
		goto out_mck_only;
	}

	dirp = malloc(count);
	if (!dirp) {
		fprintf(stderr, "%s: out of memory\n", __func__);
		ret = -ENOMEM;
		goto err;
	}

	offset = lseek(fd, 0, SEEK_CUR);
	if (offset == (off_t)-1) {
		ret = -errno;
		goto err;
	}
	__dprintf("offset: %ld\n", offset);

	if (ofd->getdents_fd == -1) {
		ofd->getdents_fd = open(ofd->mck_path, O_RDONLY | O_DIRECTORY);
		if (ofd->getdents_fd < 0) {
			ret = -errno;
			if (errno != ENOENT) {
				fprintf(stderr, "%s: could not open %s: %d\n",
					__func__, ofd->mck_path, errno);
			}
			goto err;
		}
	}

mck_again:
	/* Use "count" to simplify the handling of
	 * "Result buffer is too small" case
	 */
	ret = syscall(sysnum, ofd->getdents_fd, dirp, count);
	if (ret < 0) {
		ret = -errno;
		goto err;
	}
	mck_ret += ret;
	__dprintf("getdents from upper: mck_ret: %d, ret: %d, count: %d\n",
		  mck_ret, ret, count);

	/* cache mckernel dirents to our buffer, in case of split getdents */
	if (ret > 0) {
		void *newbuf = realloc(ofd->mck_dirents,
				       ofd->mck_dirents_size + ret);

		if (!newbuf) {
			ret = -ENOMEM;
			fprintf(stderr, "%s: not enough memory (%zd)",
				__func__, ofd->mck_dirents_size + ret);
			goto err;
		}
		ofd->mck_dirents = newbuf;
		memcpy(ofd->mck_dirents + ofd->mck_dirents_size, dirp, ret);

		/* Rewrite d_off to match the packed data layout.
		 * (EOF of fd) >= (EOF of upper + lower) is assumed.
		 * See generic_file_llseek_size().
		 */
#ifdef MCEXEC_RUST_HELPERS
		helper_rc = mcexec_dirent_rewrite_offsets_result(
				ofd->mck_dirents, ofd->mck_dirents_size,
				ofd->mck_dirents_size + ret, 0,
				dirent_is64(sysnum));
		if (helper_rc < 0) {
			ret = helper_rc;
			goto err;
		}
#else
		for (mcpos = ofd->mck_dirents_size;
		     mcpos < ofd->mck_dirents_size + ret;) {
			mck_dirp_iter = ofd->mck_dirents + mcpos;
			reclen = dirent_reclen(sysnum, mck_dirp_iter);
#ifdef DEBUG
			printf("<%s,%d,%ld> ",
			       dirent_name(sysnum, mck_dirp_iter),
			       dirent_reclen(sysnum, mck_dirp_iter),
			       *((unsigned long *)
				 dirent_off(sysnum, mck_dirp_iter)));
#endif
			*((unsigned long *)
			  dirent_off(sysnum, mck_dirp_iter)) = mcpos + reclen;

			mcpos += reclen;
		}
#endif
#ifdef DEBUG
		printf("\n");
#endif
		ofd->mck_dirents_size += ret;
	}

	/* Fill as many entries as possbile to avoid
	 * upper entries appear to be inserted in the
	 * following getdents
	 */
	if (ret > 0 && mck_ret < count) {
		goto mck_again;
	}

	if (ofd->linux_fd == -1) {
		ofd->linux_fd = open(ofd->linux_path, O_RDONLY | O_DIRECTORY);
		if (ofd->linux_fd < 0) {
			ret = -errno;
			if (errno != ENOENT) {
				fprintf(stderr, "%s: could not open %s: %d\n",
					__func__, ofd->linux_path, errno);
			}
			goto err;
		}
	}

	/* lower fs path for blacklist check */
	strncpy(ofd_path, ofd->linux_path, PATH_MAX - ofd->pathlen);

linux_again:
	/* greedy-fetch because the results would be blacklisted */
	ret = syscall(sysnum, ofd->linux_fd, dirp, count);
	if (ret < 0) {
		ret = -errno;
		fprintf(stderr, "%s: linux getdents failed: %d\n",
			__func__, errno);
		goto err;
	}
	ret_before_edit = ret;

	for (pos = 0; pos < ret;) {
		linux_dirp_iter = dirp + pos;
		reclen = dirent_reclen(sysnum, linux_dirp_iter);
		snprintf(ofd_path + ofd->pathlen, PATH_MAX - ofd->pathlen,
			 "/%s", dirent_name(sysnum, linux_dirp_iter));
		/* remove blacklist */
		if (overlay_blacklist(ofd_path)) {
			__dprintf("blacklisted: %s\n", ofd_path);
			memmove(dirp + pos,
				dirp + pos + reclen,
				ret - pos - reclen);
			ret -= reclen;
			continue;
		}
		/* remove duplicates */
#ifdef MCEXEC_RUST_HELPERS
		if (mcexec_dirent_buffer_contains_name_result(
				ofd->mck_dirents, ofd->mck_dirents_size,
				linux_dirp_iter, dirent_is64(sysnum))) {
			__dprintf("dupe: %s\n",
				  dirent_name(sysnum, linux_dirp_iter));
			memmove(dirp + pos,
				dirp + pos + reclen,
				ret - pos - reclen);
			ret -= reclen;
			continue;
		}
#else
		for (mcpos = 0; mcpos < ofd->mck_dirents_size;) {
			mck_dirp_iter = ofd->mck_dirents + mcpos;
			if (!strcmp(dirent_name(sysnum, mck_dirp_iter),
				    dirent_name(sysnum, linux_dirp_iter))) {
				__dprintf("dupe: %s\n",
					  dirent_name(sysnum, mck_dirp_iter));
				memmove(dirp + pos,
					dirp + pos + reclen,
					ret - pos - reclen);
				ret -= reclen;
				break;
			}
			mcpos += dirent_reclen(sysnum, mck_dirp_iter);
		}
		if (mcpos < ofd->mck_dirents_size)
			continue;
#endif

		pos += reclen;
	}
	linux_ret += ret;
	__dprintf("getdents from lower: linux_ret: %d, ret: %d, count: %d\n",
		  linux_ret, ret, count);

	/* cache Linux dirents to our buffer, in case of split getdents */
	if (ret > 0) {
		void *newbuf = realloc(ofd->linux_dirents,
				       ofd->linux_dirents_size + ret);

		if (!newbuf) {
			fprintf(stderr, "%s: not enough memory (%zd)",
				__func__, ofd->linux_dirents_size + ret);
			return ret;
		}
		ofd->linux_dirents = newbuf;
		memcpy(ofd->linux_dirents + ofd->linux_dirents_size,
		       dirp, ret);

		ofd->linux_dirents_size += ret;

		/* Rewrite d_off to match the packed data layout.
		 * Rewrite all because ofd->mck_dirents_size might
		 * have changed.
		 */
#ifdef MCEXEC_RUST_HELPERS
		helper_rc = mcexec_dirent_rewrite_offsets_result(
				ofd->linux_dirents, 0,
				ofd->linux_dirents_size,
				ofd->mck_dirents_size, dirent_is64(sysnum));
		if (helper_rc < 0) {
			ret = helper_rc;
			goto err;
		}
#else
		for (pos = 0; pos < ofd->linux_dirents_size;) {
			linux_dirp_iter = ofd->linux_dirents + pos;
			reclen = dirent_reclen(sysnum, linux_dirp_iter);
#ifdef DEBUG
			printf("<%s,%d,%ld> ",
			       dirent_name(sysnum, linux_dirp_iter),
			       dirent_reclen(sysnum, linux_dirp_iter),
			       *((unsigned long *)
				 dirent_off(sysnum, linux_dirp_iter)));
#endif
			*((unsigned long *)
			  dirent_off(sysnum, linux_dirp_iter)) =
				ofd->mck_dirents_size + pos + reclen;

			pos += reclen;
		}
#endif
#ifdef DEBUG
		printf("\n");
#endif
	}

	/* It's possible we filtered everything out, but there is more
	 * available. Keep trying!
	 */
	if (ret_before_edit > 0 && mck_ret + linux_ret < count) {
		goto linux_again;
	}

	/* concatenate cached upper and lower and lseek */

	/* TODO: this error should be detected by lseek */
	if (offset > ofd->mck_dirents_size + ofd->linux_dirents_size) {
		fprintf(stderr, "%s: offset (%ld) is too large (upper: %ld, lower: %ld)\n",
			__func__, offset, ofd->mck_dirents_size,
			ofd->linux_dirents_size);
		ret = -EINVAL;
		goto err;
	}

	mck_len = 0;
	linux_len = 0;
	if (count > 0 && offset < ofd->mck_dirents_size) {
		mck_len = copy_dirents(_dirp, ofd->mck_dirents,
				       ofd->mck_dirents_size, offset,
				       &count, sysnum);
		/* Result buffer is too small */
		if (mck_len == 0)  {
			__dprintf("upper: Result buffer is too small\n");
			ret = -EINVAL;
			goto err;
		}
		offset = 0;
	} else {
		offset -= ofd->mck_dirents_size;
	}
	__dprintf("mck_dirents_size: %ld, offset: %ld, mck_len: %d, count: %d\n",
		  ofd->mck_dirents_size, offset,
		  mck_len, count);
	if (count > 0 && offset < ofd->linux_dirents_size) {
		linux_len = copy_dirents(_dirp + mck_len, ofd->linux_dirents,
					 ofd->linux_dirents_size, offset,
					 &count, sysnum);
		/* Result buffer is too small */
		if (mck_len == 0 && linux_len == 0) {
			__dprintf("lower: Result buffer is too small\n");
			ret = -EINVAL;
			goto err;
		}

		__dprintf("linux_dirents_size: %ld, offset: %ld, linux_len: %d, count: %d\n",
			  ofd->linux_dirents_size, offset,
			  linux_len, count);
	}

	ret = mck_len + linux_len;
	lseek(fd, ret, SEEK_CUR);

out_mck_only:

err:
	free(dirp);

#ifdef DEBUG
	{
		void *dirp_iter;

		printf("ret: %d, {<d_name,d_reclen,d_off>}: ", ret);
		for (pos = 0; pos < ret;
		     pos += dirent_reclen(sysnum, dirp_iter)) {
			dirp_iter = _dirp + pos;
			printf("<%s,%d,%ld> ",
			       dirent_name(sysnum, dirp_iter),
			       dirent_reclen(sysnum, dirp_iter),
			       *((unsigned long *)dirent_off(sysnum, dirp_iter))
			       );
		}
		printf("\n");
	}
#endif

	return ret;
}
#endif

#ifdef MCEXEC_RUST_HELPERS
#define getpath_execveat mcexec_getpath_execveat_body
#else
/* for execveat */
static int getpath_execveat(int dirfd, const char *filename, int flags,
		char *pathbuf, size_t size)
{
	int rc, ret = 0;
	size_t len;

	if (filename[0] == '/' || dirfd == AT_FDCWD) {
		len = snprintf(pathbuf, size, "%s", filename);
	}
	else if (flags & AT_EMPTY_PATH && filename[0] == '\0') {
		len = snprintf(pathbuf, size, "/dev/fd/%d", dirfd);
	}
	else {
		len = snprintf(pathbuf, size, "/dev/fd/%d/%s", dirfd, filename);
	}

	if (len >= size) {
		ret = ENAMETOOLONG;
		goto out;
	}

	if (flags & AT_SYMLINK_NOFOLLOW) {
		if ((rc = readlink(filename, pathbuf, PATH_MAX)) != -1) {
			ret = ELOOP;
			goto out;
		}
	}

out:
	return ret;
}
#endif

#ifndef MCEXEC_RUST_HELPERS
int main_loop(struct thread_data_s *my_thread)
{
	struct syscall_wait_desc w;
	long ret;
#ifndef MCEXEC_RUST_HELPERS
	const char *fn;
	int sig;
	int term;
#endif
#ifndef MCEXEC_RUST_HELPERS
	struct timespec tv;
#endif
	char pathbuf[PATH_MAX];
	char tmpbuf[PATH_MAX];
	int cpu = my_thread->cpu;

	memset(&w, '\0', sizeof w);
	w.cpu = cpu;
	w.pid = getpid();

	while (((ret = ioctl(fd, MCEXEC_UP_WAIT_SYSCALL, (unsigned long)&w)) == 0) || (ret == -1 && errno == EINTR)) {

		if (ret) {
			continue;
		}

#ifdef MCEXEC_RUST_HELPERS
		if (act_main_loop_iteration(&w, fd, my_thread, pathbuf,
				tmpbuf, &ret, ischild))
			return ret;
#else
		/* Don't print when got a msg to stdout */
		if (!(w.sr.number == __NR_write && w.sr.args[0] == 1)) {
			__dprintf("[%d] got syscall: %ld\n", cpu, w.sr.number);
		}
		//pthread_mutex_lock(lock);

		my_thread->remote_tid = w.sr.rtid;
		my_thread->remote_cpu = w.cpu;

		switch (w.sr.number) {
		case __NR_openat:
#ifdef MCEXEC_RUST_HELPERS
			act_openat(&w, fd, cpu, pathbuf, tmpbuf);
#else
			/* check argument 1 dirfd */
			ret = do_strncpy_from_user(fd, pathbuf,
			                           (void *)w.sr.args[1],
			                           PATH_MAX);
			__dprintf("openat(dirfd == AT_FDCWD)\n");
			ret = MCEXEC_PATH_COPY_RET(ret);
			if (ret < 0) {
				do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
				break;
			}
			pathbuf[ret] = 0;
			__dprintf("openat: %d, %s,tid=%d\n", (int)w.sr.args[0],
				  pathbuf, my_thread->remote_tid);

			fn = overlay_path((int)w.sr.args[0],
					  pathbuf, tmpbuf, NULL);

			ret = openat(w.sr.args[0], fn, w.sr.args[2],
				     w.sr.args[3]);
			SET_ERR(ret);
			if (ret >= 0 && fn == tmpbuf)
				overlay_addfd(ret, fn);

			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_futex:
#ifdef MCEXEC_RUST_HELPERS
			act_futex_clock(&w, fd, cpu);
#else
			ret = clock_gettime(w.sr.args[1], &tv);
			SET_ERR(ret);
			__dprintf("clock_gettime=%016ld,%09ld\n",
					tv.tv_sec,
					tv.tv_nsec);
			do_syscall_return(fd, cpu, ret, 1, (unsigned long)&tv,
			                  w.sr.args[0], sizeof(struct timespec));
#endif
			break;

		case __NR_kill: // interrupt syscall
#ifdef MCEXEC_RUST_HELPERS
			act_kill(&w, fd, cpu, my_thread);
#else
			kill_thread(w.sr.args[1], w.sr.args[2], my_thread);
			do_syscall_return(fd, cpu, 0, 0, 0, 0, 0);
#endif
			break;
		case __NR_exit:
		case __NR_exit_group:
#ifdef MCEXEC_RUST_HELPERS
			act_exit(&w, cpu, ischild);
#else
			sig = 0;
			term = 0;
			
			/* Enforce the order in which mcexec is destroyed and then 
			   McKernel process is destroyed to prevent
			   migrated-to-Linux thread from accessing stale memory values.
			   It is done by not calling do_syscall_return(fd, cpu, 0, 0, 0, 0, 0);
			   here and making McKernel side wait until release_handler() is called. */

			__dprintf("__NR_exit/__NR_exit_group: %ld (cpu_id: %d)\n",
					w.sr.args[0], cpu);
#ifdef MCEXEC_RUST_HELPERS
			mcexec_exit_status_plan_result(w.sr.number, w.sr.args[0],
					__NR_exit_group, ischild, isatty(2),
					&sig, &term, &report_sig,
					&report_status);
			if (report_sig) {
				fprintf(stderr, "Terminate by signal %d\n", sig);
			}
			else if (report_status) {
				__dprintf("Exit status: %d\n", term);
			}
#else
			if(w.sr.number == __NR_exit_group){
				sig = w.sr.args[0] & 0x7f;
				term = (w.sr.args[0] & 0xff00) >> 8;
				if(isatty(2)){
					if(sig){
						if(!ischild) {
							fprintf(stderr, "Terminate by signal %d\n", sig);
						}
					}
					else if(term) {
						__dprintf("Exit status: %d\n", term);
					}
				}
				
			}
#endif

#ifdef USE_SYSCALL_MOD_CALL
#ifdef CMD_DCFA
			ibmic_cmd_server_exit();
#endif

#ifdef CMD_DCFAMPI
			dcfampi_cmd_server_exit();
#endif
			mc_cmd_server_exit();
			__dprintf("mccmd server exited\n");
#endif
			if(sig){
				signal(sig, SIG_DFL);
				kill(getpid(), sig);
				pause();
			}

			exit(term); /* Call release_handler() and proceed terminate() */
#endif

			//pthread_mutex_unlock(lock);
			return w.sr.args[0];

		case __NR_mmap:
		case __NR_munmap:
		case __NR_mprotect:
#ifdef MCEXEC_RUST_HELPERS
			act_reserved_memory_syscall(&w, fd, cpu);
#else
			/* reserved for internal use */
			do_syscall_return(fd, cpu, -ENOSYS, 0, 0, 0, 0);
#endif
			break;

#ifdef USE_SYSCALL_MOD_CALL
		case 303:{
			__dprintf("mcexec.c,mod_cal,mod=%ld,cmd=%ld\n", w.sr.args[0], w.sr.args[1]);
			mc_cmd_handle(fd, cpu, w.sr.args);
			break;
		}
#endif

		case __NR_gettid:{
#ifdef MCEXEC_RUST_HELPERS
			act_gettid(&w, fd, cpu);
#else
			int rc = 0;
			/*
			 * Number of TIDs and the remote physical address where TIDs are
			 * expected are passed in arg 4 and 5, respectively.
			 */
			if (w.sr.args[4] > 0) {
				struct remote_transfer trans;
#ifndef MCEXEC_RUST_HELPERS
				struct thread_data_s *tp;
				int i = 0;
#endif
				int *tids = malloc(sizeof(int) * w.sr.args[4]);
				if (!tids) {
					fprintf(stderr, "__NR_gettid(): error allocating TIDs\n");
					rc = -ENOMEM;
					goto gettid_out;
				}

#ifdef MCEXEC_RUST_HELPERS
				if (mcexec_collect_active_tids_result(thread_data,
						tids, w.sr.args[4]) < 0) {
					rc = -EINVAL;
					free(tids);
					goto gettid_out;
				}
#else
				for (tp = thread_data; tp && i < w.sr.args[4];
				     tp = tp->next) {
					if (tp->joined || tp->terminate)
						continue;
					tids[i++] = tp->tid;
				}

				for (; i < w.sr.args[4]; ++i) {
					tids[i] = 0;
				}
#endif

				trans.userp = (void*)tids;
				trans.rphys = w.sr.args[5];
				trans.size = sizeof(int) * w.sr.args[4];
				trans.direction = MCEXEC_UP_TRANSFER_TO_REMOTE;

				if (ioctl(fd, MCEXEC_UP_TRANSFER, &trans) != 0) {
					rc = -EFAULT;
					fprintf(stderr, "__NR_gettid(): error transfering TIDs\n");
				}

				free(tids);
			}
gettid_out:
			do_syscall_return(fd, cpu, rc, 0, 0, 0, 0);
#endif
			break;
		}

		case __NR_clone: {
#ifdef MCEXEC_RUST_HELPERS
			int flag = w.sr.args[0];

			if (flag == 1) {
				act_clone_complete(&w, fd, cpu);
			}
			else if (act_clone_start(&w, fd, cpu, &ret)) {
				return ret;
			}
#else
			struct fork_sync *fs;
			struct fork_sync_container *fsc = NULL;
			struct fork_sync_container *fp;
			struct fork_sync_container *fb;
			int flag = w.sr.args[0];
			int rc = -1;
			pid_t pid;

			if (flag == 1) {
#ifdef MCEXEC_RUST_HELPERS
				act_clone_complete(&w, fd, cpu);
#else
				pid = w.sr.args[1];
				rc = 0;
				pthread_mutex_lock(&fork_sync_mutex);
				for (fp = fork_sync_top, fb = NULL; fp; fb = fp, fp = fp->next)
					if (fp->pid == pid)
						break;
				if (fp) {
					fs = fp->fs;
					if (fb)
						fb->next = fp->next;
					else
						fork_sync_top = fp->next;
					fs->success = 1;
					munmap(fs, sizeof(struct fork_sync));
					free(fp);
				}
				pthread_mutex_unlock(&fork_sync_mutex);
				do_syscall_return(fd, cpu, rc, 0, 0, 0, 0);
#endif
				break;
			}

			fs = mmap(NULL, sizeof(struct fork_sync),
			          PROT_READ | PROT_WRITE,
			          MAP_SHARED | MAP_ANONYMOUS, -1, 0);
			if (fs == (void *)-1) {
				goto fork_err;
			}
			memset(fs, '\0', sizeof(struct fork_sync));
			sem_init(&fs->sem, 1, 0);

			fsc = malloc(sizeof(struct fork_sync_container));
			if (!fsc) {
				goto fork_err;
			}
			memset(fsc, '\0', sizeof(struct fork_sync_container));
			pthread_mutex_lock(&fork_sync_mutex);
			fsc->next = fork_sync_top;
			fork_sync_top = fsc;
			pthread_mutex_unlock(&fork_sync_mutex);
			fsc->fs = fs;

			fsc->pid = pid = fork();

			switch (pid) {
			    /* Error */
			    case -1:
				fprintf(stderr, "fork(): error forking child process\n");
				rc = -errno;
				break;

			    /* Child process */
			    case 0: {
				int ret = 1;
				struct rpgtable_desc rpt;

				ischild = 1;
				/* Reopen device fd */
				close(fd);
				fd = opendev();
				if (fd < 0) {
					fs->status = -errno;
					fprintf(stderr, "ERROR: opening %s\n", dev);
					
					goto fork_child_sync_pipe;
				}

				rpt.start = w.sr.args[1];
				rpt.len = w.sr.args[2];
				rpt.rpgtable = w.sr.args[3];
				if (ioctl(fd, MCEXEC_UP_CREATE_PPD, &rpt)) {
					fs->status = -errno;
					fprintf(stderr, "ERROR: creating PPD %s\n", dev);

					goto fork_child_sync_pipe;
				}

				/* Reinit signals and syscall threads */
				init_sigaction();
				/* Only the caller survives fork(); inherited workers are stale. */
				thread_data = NULL;

				__dprintf("pid(%d): signals and syscall threads OK\n", 
						getpid());

				/* Check if we need to limit number of threads in the pool */
				if ((ret = ioctl(fd, MCEXEC_UP_GET_NUM_POOL_THREADS)) < 0) {
					fprintf(stderr, "Error: obtaining thread pool count\n");
				}

				/* Limit number of threads */
				if (ret == 1) {
					n_threads = 4;
				}

				if ((ret = init_worker_threads(fd)) != 0) {
					fprintf(stderr, "%s: Error: creating worker threads: %s\n",
						__func__, strerror(-ret));
					close(fd);
					exit(1);
				}

fork_child_sync_pipe:
				/* clear fork_sync inherited from parent */
				for (fp = fork_sync_top; fp;) {
					fb = fp->next;
					if (fp->fs && fp->fs != fs) {
						munmap(fp->fs, sizeof(struct fork_sync));
					}
					free(fp);
					fp = fb;
				}
				fork_sync_top = NULL;

				sem_post(&fs->sem);
				if (fs->status) {
					exit(1);
				}

				pthread_mutex_init(&fork_sync_mutex, NULL);

				/* TODO: does the forked thread run in a pthread context? */
				while (getppid() != 1 &&
				       fs->success == 0) {
					sched_yield();
				}

				if (fs->success == 0) {
					exit(1);
				}

				sem_destroy(&fs->sem);
				munmap(fs, sizeof(struct fork_sync));
#if 1 /* debug : thread killed by exit_group() are still joinable? */
				join_all_threads();
#endif
				return ret;
			    }
				
			    /* Parent */
			    default:
				while ((rc = sem_trywait(&fs->sem)) == -1 && (errno == EAGAIN || errno == EINTR)) {
					int st;
					int wrc;

					wrc = waitpid(pid, &st, WNOHANG);
					if(wrc == pid) {
						fs->status = -ENOMEM;
						break;
					}
					sched_yield();
				}

				if (fs->status != 0) {
					fprintf(stderr, "fork(): error with child process after fork\n");
					rc = fs->status;
					break;
				}

				rc = pid;
				break;
			}

fork_err:
			if (fs) {
				sem_destroy(&fs->sem);
				if (rc < 0) {
					munmap(fs, sizeof(struct fork_sync));
					pthread_mutex_lock(&fork_sync_mutex);
#ifdef MCEXEC_RUST_HELPERS
					if (mcexec_fork_sync_remove_node_result(
							&fork_sync_top, fsc) > 0) {
						free(fsc);
					}
#else
					for (fp = fork_sync_top, fb = NULL; fp; fb = fp, fp = fp->next)
						if (fp == fsc)
							break;
					if (fp) {
						if (fb)
							fb->next = fsc->next;
						else
							fork_sync_top = fsc->next;
						free(fp);
					}
#endif
					pthread_mutex_unlock(&fork_sync_mutex);
				}
			}
			do_syscall_return(fd, cpu, rc, 0, 0, 0, 0);
#endif
			break;
		}

		case __NR_wait4: {
#ifdef MCEXEC_RUST_HELPERS
			act_wait4(&w, fd, cpu);
#else
			int ret;
			pid_t pid = w.sr.args[0];
			int options = w.sr.args[2];
			siginfo_t info;
			int opt;

			opt = WEXITED | (options & WNOWAIT);
			memset(&info, '\0', sizeof info);
			while ((ret = waitid(P_PID, pid, &info, opt)) == -1 &&
			       errno == EINTR);
			if (ret == 0) {
				ret = info.si_pid;
			}

			if (ret != pid) {
				fprintf(stderr, "ERROR: waiting for %lu rc=%d errno=%d\n", w.sr.args[0], ret, errno);
			}

			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
		}

		/* Actually, performing execveat() for McKernel */
		case __NR_execve: {
#ifdef MCEXEC_RUST_HELPERS
			if (act_execve(&w, fd, cpu, pathbuf, &ret))
				return ret;
#else

			/* Execve phase */
			switch (w.sr.args[0]) {
#ifndef MCEXEC_RUST_HELPERS
				struct program_load_desc *desc;
				struct remote_transfer trans;
				char *filename;
				char **shebang_argv;
				char *shebang_argv_flat;
				char *buffer;
				size_t size;
				int dirfd, flags;
#endif
				int ret;

				/* Load descriptor phase */
				case 1:
#ifdef MCEXEC_RUST_HELPERS
					act_execve_phase1(&w, fd, cpu, pathbuf);
#else
					shebang_argv = NULL;
					buffer = NULL;
					desc = NULL;
					dirfd = (int)w.sr.args[1];
					filename = (char *)w.sr.args[2];
					flags = (int)w.sr.args[4];
					
					ret = getpath_execveat(dirfd,
						filename, flags,
						pathbuf, PATH_MAX);
					if (ret) {
						goto return_execve1;
					}
					filename = pathbuf;

					/* fget executable as well */
					if ((ret = load_elf_desc_shebang(filename, &desc,
									 &shebang_argv, 0)) != 0) {
						goto return_execve1;
					}

					desc->enable_vdso = enable_vdso;
					__dprintf("execve(): load_elf_desc() for %s OK, num sections: %d\n",
						filename, desc->num_sections);

					desc->rlimit[MCK_RLIMIT_STACK].rlim_cur = rlim_stack.rlim_cur;
					desc->rlimit[MCK_RLIMIT_STACK].rlim_max = rlim_stack.rlim_max;
					desc->stack_premap = stack_premap;

					buffer = (char *)desc;
					size = sizeof(struct program_load_desc) +
					       sizeof(struct program_image_section) *
					       desc->num_sections;
					if (shebang_argv) {
						desc->args_len = flatten_strings(NULL, shebang_argv,
										 &shebang_argv_flat);
#ifdef MCEXEC_RUST_HELPERS
						ret = mcexec_execve1_transfer_buffer_result(
							desc, size, shebang_argv_flat,
							desc->args_len, &buffer, &size);
						if (ret) {
							fprintf(stderr,
								"execve(): could not alloc transfer buffer for file %s\n",
								filename);
							free(shebang_argv_flat);
							goto return_execve1;
						}
#else
						buffer = malloc(size + desc->args_len);
						if (!buffer) {
							fprintf(stderr,
								"execve(): could not alloc transfer buffer for file %s\n",
								filename);
							free(shebang_argv_flat);
							ret = ENOMEM;
							goto return_execve1;
						}
						memcpy(buffer, desc, size);
						memcpy(buffer + size, shebang_argv_flat,
						       desc->args_len);
#endif
						free(shebang_argv_flat);
#ifndef MCEXEC_RUST_HELPERS
						size += desc->args_len;
#endif
					}

					/* Copy descriptor to co-kernel side */
					trans.userp = buffer;
					trans.rphys = w.sr.args[3];
					trans.size = size;
					trans.direction = MCEXEC_UP_TRANSFER_TO_REMOTE;
					
					if (ioctl(fd, MCEXEC_UP_TRANSFER, &trans) != 0) {
						fprintf(stderr, 
							"execve(): error transfering ELF for file %s\n", 
							filename);
						ret = -errno;
						goto return_execve1;
					}
					
					__dprintf("execve(): load_elf_desc() for %s OK\n",
						  filename);

					ret = 0;
return_execve1:
					/* We can't be sure next phase will succeed */
					/* TODO: what shall we do with fp in desc?? */
					if (buffer != (char *)desc)
						free(buffer);
					free(desc);

					do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
					break;

				/* Copy program image phase */
				case 2:
#ifdef MCEXEC_RUST_HELPERS
					ret = act_execve_phase2(&w, fd, cpu);
					if (ret)
						return ret;
#else
					
					ret = -1;
					/* Alloc descriptor */
					desc = malloc(w.sr.args[2]);
					if (!desc) {
						fprintf(stderr, "execve(): error allocating desc\n");
						goto return_execve2;
					}
					memset(desc, '\0', w.sr.args[2]);

					/* Copy descriptor from co-kernel side */
					trans.userp = (void*)desc;
					trans.rphys = w.sr.args[1];
					trans.size = w.sr.args[2];
					trans.direction = MCEXEC_UP_TRANSFER_FROM_REMOTE;
					
					if (ioctl(fd, MCEXEC_UP_TRANSFER, &trans) != 0) {
						fprintf(stderr, 
							"execve(): error obtaining ELF descriptor\n");
						ret = EINVAL;
						goto return_execve2;
					}
					
					__dprintf("%s", "execve(): transfer ELF desc OK\n");

					if (transfer_image(fd, desc) != 0) {
						fprintf(stderr, "error: transferring image\n");
						return -1;
					}
					__dprintf("%s", "execve(): image transferred\n");

					/* fput executable */
					if ((ret = ioctl(fd, MCEXEC_UP_CLOSE_EXEC)) != 0) {
						fprintf(stderr, "error: MCEXEC_UP_CLOSE_EXEC failed with %d\n",
							ret);
						return 1;
					}

					if (close_cloexec_fds(fd) < 0) {
						ret = EINVAL;
						goto return_execve2;
					}

					ret = 0;
return_execve2:					
					do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
					break;

				default:
					fprintf(stderr, "execve(): ERROR: invalid execve phase\n");
					break;
			}
#endif

			break;
		}

		case __NR_signalfd4:
#ifdef MCEXEC_RUST_HELPERS
			act_signalfd4_syscall(&w, fd, cpu);
#else
			ret = act_signalfd4(&w);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_perf_event_open:
#ifdef MCEXEC_RUST_HELPERS
			act_perf_event_open(&w, fd, cpu);
#else
			ret = open("/dev/null", O_RDONLY);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_rt_sigaction:
#ifdef MCEXEC_RUST_HELPERS
			act_rt_sigaction(&w, fd, cpu);
#else
			act_sigaction(&w);
			do_syscall_return(fd, cpu, 0, 0, 0, 0, 0);
#endif
			break;

		case __NR_rt_sigprocmask:
#ifdef MCEXEC_RUST_HELPERS
			act_rt_sigprocmask(&w, fd, cpu);
#else
			act_sigprocmask(&w);
			do_syscall_return(fd, cpu, 0, 0, 0, 0, 0);
#endif
			break;

		case __NR_setfsuid:
#ifdef MCEXEC_RUST_HELPERS
			act_setfsuid(&w, fd, cpu);
#else
			if (MCEXEC_SETFSUID_NEEDS_CRED(w.sr.args[1])) {
				ioctl(fd, MCEXEC_UP_GET_CRED, w.sr.args[0]);
				ret = 0;
			}
			else{
				ret = setfsuid(w.sr.args[0]);
			}
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_setresuid:
#ifdef MCEXEC_RUST_HELPERS
			act_setresuid(&w, fd, cpu);
#else
			ret = setresuid(w.sr.args[0], w.sr.args[1], w.sr.args[2]);
			SET_ERR(ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_setreuid:
#ifdef MCEXEC_RUST_HELPERS
			act_setreuid(&w, fd, cpu);
#else
			ret = setreuid(w.sr.args[0], w.sr.args[1]);
			SET_ERR(ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_setuid:
#ifdef MCEXEC_RUST_HELPERS
			act_setuid(&w, fd, cpu);
#else
			ret = setuid(w.sr.args[0]);
			SET_ERR(ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_setresgid:
#ifdef MCEXEC_RUST_HELPERS
			act_setresgid(&w, fd, cpu);
#else
			ret = setresgid(w.sr.args[0], w.sr.args[1], w.sr.args[2]);
			SET_ERR(ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_setregid:
#ifdef MCEXEC_RUST_HELPERS
			act_setregid(&w, fd, cpu);
#else
			ret = setregid(w.sr.args[0], w.sr.args[1]);
			SET_ERR(ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_setgid:
#ifdef MCEXEC_RUST_HELPERS
			act_setgid(&w, fd, cpu);
#else
			ret = setgid(w.sr.args[0]);
			SET_ERR(ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_setfsgid:
#ifdef MCEXEC_RUST_HELPERS
			act_setfsgid(&w, fd, cpu);
#else
			ret = setfsgid(w.sr.args[0]);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_close:
#ifdef MCEXEC_RUST_HELPERS
			act_close(&w, fd, cpu);
#else
			ret = MCEXEC_CLOSE_PLAN(w.sr.args[0], fd);
			if (ret == 0)
				ret = do_generic_syscall(&w);
			overlay_delfd(w.sr.args[0]);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_readlinkat:
#ifdef MCEXEC_RUST_HELPERS
			act_readlinkat(&w, fd, cpu, pathbuf, tmpbuf);
#else
			/* check argument 1 dirfd */
			ret = do_strncpy_from_user(fd, pathbuf,
					(void *)w.sr.args[1], PATH_MAX);
			ret = MCEXEC_PATH_COPY_RET(ret);
			if (ret < 0) {
				do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
				break;
			}
			pathbuf[ret] = 0;
			__dprintf("readlinkat: %d, %s\n", (int)w.sr.args[0], pathbuf);

			fn = overlay_path((int)w.sr.args[0],
					  pathbuf, tmpbuf, NULL);

			ret = readlinkat(w.sr.args[0], fn, (char *)w.sr.args[2],
					 w.sr.args[3]);
			SET_ERR(ret);
			__dprintf("readlinkat: dirfd=%d, path=%s, buf=%s, ret=%ld\n",
				(int)w.sr.args[0], fn, (char *)w.sr.args[2], ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
#ifdef __NR_readlink
		case __NR_readlink:
#ifdef MCEXEC_RUST_HELPERS
			act_readlink(&w, fd, cpu, pathbuf, tmpbuf);
#else
			ret = do_strncpy_from_user(fd, pathbuf, (void *)w.sr.args[0], PATH_MAX);
			ret = MCEXEC_PATH_COPY_RET(ret);
			if (ret < 0) {
				do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
				break;
			}

			fn = overlay_path(AT_FDCWD, pathbuf, tmpbuf, NULL);

			ret = readlink(fn, (char *)w.sr.args[1], w.sr.args[2]);
			SET_ERR(ret);
			__dprintf("readlink: path=%s, buf=%s, ret=%ld\n", 
				fn, (char *)w.sr.args[1], ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
#endif	/* __NR_readlink */

		case __NR_newfstatat:
#ifdef MCEXEC_RUST_HELPERS
			act_newfstatat(&w, fd, cpu, pathbuf, tmpbuf);
#else
			ret = do_strncpy_from_user(fd, pathbuf, (void *)w.sr.args[1], PATH_MAX);
			ret = MCEXEC_PATH_COPY_RET(ret);
			if (ret < 0) {
				do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
				break;
			}
			pathbuf[ret] = 0;

			fn = overlay_path((int)w.sr.args[0],
					  pathbuf, tmpbuf, NULL);

			ret = fstatat((int)w.sr.args[0],
				      fn,
				      (struct stat *)w.sr.args[2],
				      (int)w.sr.args[3]);
			SET_ERR(ret);
			__dprintf("fstatat: dirfd=%d, pathname=%s, buf=%p, flags=%x, ret=%ld\n",
				  (int)w.sr.args[0], fn, (void *)w.sr.args[2],
				  (int)w.sr.args[3], ret);

			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
#ifdef __NR_stat
		case __NR_stat:
#ifdef MCEXEC_RUST_HELPERS
			act_stat(&w, fd, cpu, pathbuf, tmpbuf);
#else
			ret = do_strncpy_from_user(fd, pathbuf, (void *)w.sr.args[0], PATH_MAX);
			ret = MCEXEC_PATH_COPY_RET(ret);
			if (ret < 0) {
				do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
				break;
			}

			fn = overlay_path(AT_FDCWD, pathbuf, tmpbuf, NULL);

			ret = stat(fn, (struct stat *)w.sr.args[1]);
			SET_ERR(ret);
			__dprintf("stat: path=%s, ret=%ld\n", fn, ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
#endif /* __NR_stat */

		case __NR_faccessat: {
#ifdef MCEXEC_RUST_HELPERS
			act_faccessat(&w, fd, cpu, pathbuf, tmpbuf);
#else
			int resolvelinks = 0;

			ret = do_strncpy_from_user(fd, pathbuf,
					(void *)w.sr.args[1], PATH_MAX);
			ret = MCEXEC_PATH_COPY_RET(ret);
			if (ret < 0) {
				do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
				break;
			}
			pathbuf[ret] = 0;

			fn = overlay_path((int)w.sr.args[0],
					  pathbuf, tmpbuf, &resolvelinks);

			/* the syscall doesn't take flags argument, link
			 * resolution happened first so don't do it again
			 */
			ret = faccessat((int)w.sr.args[0], fn,
					(int)w.sr.args[2],
					resolvelinks == 0 ?
						0 : AT_SYMLINK_NOFOLLOW);
			SET_ERR(ret);
			__dprintf("faccessat: dirfd=%d, pathname=%s, mode=%d, ret=%ld\n",
				  (int)w.sr.args[0], fn, (int)w.sr.args[2],
				  ret);

			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
		}
#ifdef __NR_access
		case __NR_access:
#ifdef MCEXEC_RUST_HELPERS
			act_access(&w, fd, cpu, pathbuf, tmpbuf);
#else
			ret = do_strncpy_from_user(fd, pathbuf,
					(void *)w.sr.args[0], PATH_MAX);
			ret = MCEXEC_PATH_COPY_RET(ret);
			if (ret < 0) {
				do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
				break;
			}

			fn = overlay_path(AT_FDCWD, pathbuf, tmpbuf, NULL);

			ret = access(fn, (int)w.sr.args[1]);
			SET_ERR(ret);
			__dprintf("access: path=%s, ret=%ld\n", fn, ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
#endif /* __NR_access */
		case __NR_getxattr:
#ifdef MCEXEC_RUST_HELPERS
			act_getxattr(&w, fd, cpu, pathbuf, tmpbuf);
#else
			ret = do_strncpy_from_user(fd, pathbuf,
					(void *)w.sr.args[0], PATH_MAX);
			ret = MCEXEC_PATH_COPY_RET(ret);
			if (ret < 0) {
				do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
				break;
			}

			fn = overlay_path(AT_FDCWD, pathbuf, tmpbuf, NULL);

			ret = getxattr(fn, (char *)w.sr.args[1],
				       (void *)w.sr.args[2],
				       (size_t)w.sr.args[3]);
			SET_ERR(ret);
			__dprintf("getxattr: path=%s, name=%s, ret=%ld\n", fn,
				  (char *)w.sr.args[1], ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
		case __NR_lgetxattr:
#ifdef MCEXEC_RUST_HELPERS
			act_lgetxattr(&w, fd, cpu, pathbuf, tmpbuf);
#else
			ret = do_strncpy_from_user(fd, pathbuf,
					(void *)w.sr.args[0], PATH_MAX);
			ret = MCEXEC_PATH_COPY_RET(ret);
			if (ret < 0) {
				do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
				break;
			}

			fn = overlay_path(AT_FDCWD, pathbuf, tmpbuf, NULL);

			ret = lgetxattr(fn, (char *)w.sr.args[1],
					(void *)w.sr.args[2],
					(size_t)w.sr.args[3]);
			SET_ERR(ret);
			__dprintf("lgetxattr: path=%s, name=%s, ret=%ld\n", fn,
				  (char *)w.sr.args[1], ret);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
#ifdef	__NR_getdents
		case __NR_getdents:
#endif
		case __NR_getdents64:
#ifdef MCEXEC_RUST_HELPERS
			act_getdents(&w, fd, cpu);
#else
			ret = overlay_getdents(w.sr.number,
					(int)w.sr.args[0],
					(struct linux_dirent *)w.sr.args[1],
					(unsigned int)w.sr.args[2]);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		case __NR_sched_setaffinity:
#ifdef MCEXEC_RUST_HELPERS
			act_sched_setaffinity(&w, fd, cpu, my_thread);
#else
			ret = MCEXEC_SCHED_SETAFFINITY_ACTION(w.sr.args[0]);
			if (ret > 0) {
				ret = util_thread(my_thread, w.sr.args[1], w.sr.rtid,
						w.sr.args[2], w.sr.args[3],
						w.sr.args[4]);
			}
			else {
				__eprintf("__NR_sched_setaffinity: invalid argument (%lx)\n", w.sr.args[0]);
			}
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
		case 801: {// swapout
#ifdef ENABLE_QLMPI
			int rc;
			int spawned;
			int rank;
			int ql_fd = -1;
			int len;
			struct sockaddr_un unix_addr;
			char msg_buf[QL_BUF_MAX];
			char *ql_name;

			rc = PMI_Init(&spawned);
			if (rc != 0) {
				fprintf(stderr, "swapout(): ERROR: failed to init PMI\n");
				ret = -1;
				goto return_swapout;
			}
			rc = PMI_Get_rank(&rank);
			if (rc != 0) {
				fprintf(stderr, "swapout(): ERROR: failed to get Rank\n");
				ret = -1;
				goto return_swapout;
			}

			// swap synchronization 
			rc = PMI_Barrier();

			if (rank == 0) {
				// tell ql_server what calculation is done.
				ql_fd = socket(AF_UNIX, SOCK_STREAM, 0);
				if (ql_fd < 0) {
					fprintf(stderr, "swapout(): ERROR: failed to open socket\n");
					ret = -1;
					goto return_swapout;
				}

				unix_addr.sun_family = AF_UNIX;
				strcpy(unix_addr.sun_path, getenv("QL_SOCKET_FILE"));
				len = sizeof(unix_addr.sun_family) + strlen(unix_addr.sun_path) + 1;
				rc = connect(ql_fd, (struct sockaddr*)&unix_addr, len);
				if (rc < 0) {
					fprintf(stderr, "swapout(): ERROR: failed to connect ql_server\n");
					ret = -1;
					goto return_swapout;
				}

				ql_name = getenv(QL_NAME);
				sprintf(msg_buf, "%c %04x %s",
				        QL_EXEC_END, (unsigned int)strlen(ql_name), ql_name);
				rc = send(ql_fd, msg_buf, strlen(msg_buf) + 1, 0);
				if (rc < 0) {
					fprintf(stderr, "swapout(): ERROR: failed to send QL_EXEC_END\n");
					ret = -1;
					goto return_swapout;
				}
				
				// wait resume-req from ql_server.
#ifdef QL_DEBUG
				fprintf(stdout, "INFO: waiting resume-req ...\n");
#endif
				rc = recv(ql_fd, msg_buf, strlen(msg_buf) + 1, 0);

				if (rc < 0) {
					fprintf(stderr, "swapout(): ERROR: failed to recieve\n");
					ret = -1;
					goto return_swapout;
				}

				// parse message
				if (msg_buf[0] == QL_RET_RESUME) {
#ifdef QL_DEBUG
					fprintf(stdout, "INFO: recieved resume-req\n");
#endif
				}
				else {
					fprintf(stderr, "swapout(): ERROR: recieved unexpected requsest from ql_server\n");
					ret = -1;
					goto return_swapout;
				}

				// resume-req synchronization
				rc = PMI_Barrier();
			}
			else {
				// resume-req synchronization 
				rc = PMI_Barrier();
			}
			
			ret = 0;

return_swapout:
			if (ql_fd >= 0) {
				close(ql_fd);
			}

			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#else
#ifdef MCEXEC_RUST_HELPERS
			act_swapout_unavailable(&w, fd, cpu);
#else
			printf("mcexec has not been compiled with ENABLE_QLMPI\n");
			ret = -1;
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
#endif // ENABLE_QLMPI
			break;
		}
		case 802: /* debugging purpose */
#ifdef MCEXEC_RUST_HELPERS
			act_debug_mlock(&w, fd, cpu);
#else
			printf("linux mlock(%p, %ld)\n",
			       (void *)w.sr.args[0], w.sr.args[1]);
			printf("str(%p)=%s", (void*)w.sr.args[0], (char*)w.sr.args[0]);
			ret = mlock((void *)w.sr.args[0], w.sr.args[1]);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

#ifndef ARG_MAX
#define ARG_MAX 256
#endif
		case 811: { // linux_spawn
#ifdef MCEXEC_RUST_HELPERS
			act_linux_spawn(&w, fd, cpu);
#else
			int rc, i;
			pid_t pid;
			size_t slen;
			char *exec_path = NULL;
			char* argv[ARG_MAX];
			char** spawn_args = (char**)w.sr.args[1];

			if (!w.sr.args[0] || ! spawn_args) {
				fprintf(stderr, "linux_spawn(): ERROR: invalid argument \n");
				ret = -1;
				goto return_linux_spawn;
			}

			// copy exec_path
			slen = strlen((char*)w.sr.args[0]) + 1;
			if (slen <= 0 || slen >= PATH_MAX) {
				fprintf(stderr, "linux_spawn(): ERROR: invalid exec_path \n");
				ret = -1;
				goto return_linux_spawn;
			}
			exec_path = malloc(slen);
			if (!exec_path) {
				fprintf(stderr, "linux_spawn(): ERROR: failed to allocating exec_path\n");
				ret = -1;
				goto return_linux_spawn;
			}
			memset(exec_path, '\0', slen);

			rc = do_strncpy_from_user(fd, exec_path, (void *)w.sr.args[0], slen);
			if (rc < 0) {
				fprintf(stderr, "linux_spawn(): ERROR: failed to strncpy from user\n");
				ret = -1;
				goto return_linux_spawn;
			}

			// copy args to argv[]
			for (i = 0; spawn_args[i] != NULL; i++) {
				slen = strlen(spawn_args[i]) + 1;
				argv[i] = malloc(slen);
				if (!argv[i]) {
					fprintf(stderr, "linux_spawn(): ERROR: failed to allocating argv[%d]\n", i);
					ret = -1;
					goto return_linux_spawn;
				}
				memset(argv[i], '\0', slen);
				rc = do_strncpy_from_user(fd, argv[i], spawn_args[i], slen);
				if (rc < 0) {
					fprintf(stderr, "linux_spawn(): ERROR: failed to strncpy from user\n");
					ret = -1;
					goto return_linux_spawn;
				}
			}

			rc = posix_spawn(&pid, exec_path, NULL, NULL, argv, NULL);
			if (rc != 0) {
				fprintf(stderr, "linux_spawn(): ERROR: posix_spawn returned %d\n", rc);
				ret = -1;
				goto return_linux_spawn;
			}

			ret = 0;
return_linux_spawn:
			// free allocated memory
			if (exec_path) {
				free(exec_path);
			}
			for (i = 0; argv[i] != NULL; i++) {
				free(argv[i]);
			}

			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
		}

#ifdef __NR_open
		case __NR_open:
#ifdef MCEXEC_RUST_HELPERS
			act_open(&w, fd, cpu, pathbuf, tmpbuf);
#else
			ret = do_strncpy_from_user(fd, pathbuf,
					(void *)w.sr.args[0], PATH_MAX);
			ret = MCEXEC_PATH_COPY_RET(ret);
			if (ret < 0) {
				do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
				break;
			}
			__dprintf("open: %s\n", pathbuf);

			fn = overlay_path(AT_FDCWD, pathbuf, tmpbuf, NULL);

			ret = open(fn, w.sr.args[1], w.sr.args[2]);
			SET_ERR(ret);
			if (ret >= 0 && fn == tmpbuf)
				overlay_addfd(ret, fn);

			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;
#endif

		default:
#ifdef MCEXEC_RUST_HELPERS
			act_generic_syscall(&w, fd, cpu);
#else
			ret = do_generic_syscall(&w);
			do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
#endif
			break;

		}
#endif

		my_thread->remote_tid = -1;

		//pthread_mutex_unlock(lock);
	}
	__dprintf("timed out.\n");
	return 1;
}
#endif
