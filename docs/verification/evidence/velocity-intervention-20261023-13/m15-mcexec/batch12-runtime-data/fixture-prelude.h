/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <getopt.h>
#include <pthread.h>
#include <semaphore.h>
#include <sys/types.h>
#include <sys/resource.h>
#include <sched.h>
#include <assert.h>
struct list_head {struct list_head *next,*prev;};
struct thread_data_s;
struct fork_sync_container;
extern struct thread_data_s *thread_data;
extern struct fork_sync_container *fork_sync_top;
extern int debug;
extern pthread_mutex_t lock,fork_sync_mutex;
extern pthread_barrier_t init_ready,uti_init_ready;
extern pthread_spinlock_t overlay_fd_lock;
extern struct list_head overlay_fd_list;
extern struct option mcexec_options[];
extern int mcosid;
extern int fd;
extern int ischild;
extern int enable_vdso;
extern int mpol_no_heap;
extern int mpol_no_stack;
extern int mpol_no_bss;
extern int mpol_shm_premap;
extern int no_bind_ikc_map;
extern int straight_map;
extern int profile;
extern int disable_sched_yield;
extern int uti_thread_rank;
extern int uti_use_last_cpu;
extern int enable_uti;
extern int nr_processes;
extern int nr_threads;
extern pid_t master_tid;
extern int ncpu;
extern int nnodes;
extern int n_threads;
extern unsigned long straight_map_threshold;
extern unsigned long mpol_threshold;
extern unsigned long heap_extension;
extern unsigned long mcexec_flags;
extern unsigned long page_size;
extern unsigned long page_mask;
extern long stack_premap;
extern long stack_max;
#ifdef ENABLE_TOFU
extern int enable_tofu;
#endif
extern char *exec_path;
extern char *altroot;
extern char *mpol_bind_nodes;
extern unsigned char *dma_buf;
extern void *numa_nodes;
extern size_t cpu_set_size;
extern char dev[64];
extern struct rlimit rlim_stack;
extern cpu_set_t mcexec_partition_cpu_set_storage;
