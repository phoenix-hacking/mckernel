/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#define ADD_ENVS_OPTION
#define DO_NOT_OVERWRITE 0
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <getopt.h>
#include <pthread.h>
#include <sys/types.h>
#include <sys/resource.h>
#include <sys/personality.h>
#include <sys/prctl.h>
#include <sys/ioctl.h>
#include <assert.h>
#define IHK_OS_GET_BUILDID 0x112a37
#define __dprintf(format,args...) do {if(debug){printf("%s: " format,__func__,##args);fflush(stdout);}} while(0)
#define __eprintf(format,args...) do {fprintf(stderr,"%s: " format,__func__,##args);fflush(stderr);} while(0)
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

extern char *altroot;
extern int debug;
extern int disable_sched_yield;
extern int enable_uti;
extern int enable_vdso;
extern char *exec_path;
extern unsigned long heap_extension;
extern int ischild;
extern unsigned long mcexec_flags;
extern int mcosid;
extern char *mpol_bind_nodes;
extern int mpol_no_bss;
extern int mpol_no_heap;
extern int mpol_no_stack;
extern int mpol_shm_premap;
extern unsigned long mpol_threshold;
extern int no_bind_ikc_map;
extern int nr_processes;
extern int nr_threads;
extern int profile;
extern struct rlimit rlim_stack;
extern long stack_max;
extern long stack_premap;
extern int straight_map;
extern unsigned long straight_map_threshold;
extern int uti_thread_rank;
extern int uti_use_last_cpu;
extern int fd;
extern unsigned long page_size,page_mask;
extern char dev[64];
extern pthread_spinlock_t overlay_fd_lock;

extern struct option mcexec_options[];
static const char rlimit_stack_envname[]="MCKERNEL_RLIMIT_STACK";
static const char ld_preload_envname[]="MCKERNEL_LD_PRELOAD";
unsigned long mcexec_main_page_size_bridge(void);
void mcexec_main_publish_page_altroot_bridge(unsigned long new_page_size,
		const char *new_altroot);
const char *mcexec_altroot_bridge(void);
void mcexec_load_desc_publish_exec_path_bridge(char *path);
int mcexec_main_load_stack_rlimit_bridge(unsigned long *cur,
		unsigned long *max);
int mcexec_reduce_stack_setenv_bridge(const char *newval);
int mcexec_reduce_stack_setrlimit_bridge(unsigned long cur, unsigned long max);
ssize_t mcexec_reduce_stack_readlink_bridge(char *path, size_t size);
ssize_t mcexec_find_libdir_readlink_bridge(char *path, size_t size);
int mcexec_reduce_stack_execv_bridge(const char *path, char **argv);
int mcexec_execve1_enable_vdso_bridge(void);
unsigned long mcexec_execve1_rlim_cur_bridge(void);
unsigned long mcexec_execve1_rlim_max_bridge(void);
long mcexec_execve1_stack_premap_bridge(void);
int mcexec_main_loop_is_child_bridge(void);
int mcexec_opendev_mcosid_bridge(void);
int mcexec_overlay_mcosid_bridge(void);
int mcexec_ld_preload_enable_uti_bridge(void);
int mcexec_overlay_enable_uti_bridge(void);
int mcexec_ld_preload_disable_sched_yield_bridge(void);
void mcexec_main_publish_args_bridge(int argc, char **argv);
void mcexec_main_state_ptrs_bridge(struct mcexec_main_state_ptrs *state);
int mcexec_main_personality_bridge(char **argv);
int mcexec_main_next_option_bridge(int argc, char **argv);
char *mcexec_main_optarg_bridge(void);
int mcexec_main_optind_bridge(void);
void mcexec_main_publish_mcosid_bridge(int new_mcosid);
int mcexec_main_uti_unavailable_bridge(int enable_uti_arg);
void mcexec_main_overlay_lock_init_bridge(void);
char *mcexec_opendev_dev_bridge(void);
size_t mcexec_opendev_dev_size_bridge(void);
int mcexec_opendev_open_bridge(const char *path);
void mcexec_opendev_publish_fd_bridge(int value);
int mcexec_opendev_query_buildid_bridge(int target_fd, char *query_result);
void mcexec_opendev_close_bridge(int target_fd);
void *mcexec_find_libdir_popen_bridge(const char *cmd);
ssize_t mcexec_find_libdir_getline_bridge(char **line, size_t *linelen,
		void *filep);
void mcexec_find_libdir_pclose_bridge(void *filep);
void mcexec_find_libdir_free_bridge(char *line);
char *mcexec_ld_preload_getenv_bridge(const char *name);
int mcexec_ld_preload_setenv_bridge(const char *value);
int mcexec_ld_preload_unsetenv_bridge(void);
int mcexec_ld_preload_enable_qlmpi_bridge(void);
int mcexec_get_thp_disable_prctl_bridge(void);

#ifdef ENABLE_TOFU
extern int enable_tofu;
#endif
#ifdef USE_SYSCALL_MOD_CALL
extern int __glob_argc;
extern char **__glob_argv;
#endif
