/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <sys/ioctl.h>
#include <pthread.h>
#include <semaphore.h>
#include <sched.h>
#include <assert.h>
#include <setjmp.h>
struct fork_sync {int status;volatile int success;sem_t sem;};
struct fork_sync_container {pid_t pid;struct fork_sync_container *next;struct fork_sync *fs;};
struct syscall_request {int rtid,ttid;unsigned long valid,number,args[6];};
struct syscall_wait_desc {unsigned long cpu;struct syscall_request sr;int pid;};
struct rpgtable_desc {uintptr_t rpgtable,start,len;};
extern int fd,ischild,debug,n_threads;
extern char dev[32];
extern void *thread_data;
extern struct fork_sync_container *fork_sync_top;
extern pthread_mutex_t fork_sync_mutex;
#define MCEXEC_UP_CREATE_PPD 0x30a0290e
#define MCEXEC_UP_GET_NUM_POOL_THREADS 0x30a02926
#define __dprintf(format,args...) do { if(debug) {printf("%s: " format,__func__,##args);fflush(stdout);} } while(0)
int mcexec_opendev_body(void);
#define opendev mcexec_opendev_body
void init_sigaction(void);
int init_worker_threads(int);
void mcexec_join_all_threads_body(void);
#define join_all_threads mcexec_join_all_threads_body
void *mcexec_clone_alloc_fork_sync_bridge(void);
void *mcexec_clone_alloc_container_bridge(void);
long mcexec_clone_child_bridge(struct syscall_wait_desc *,void *);
int mcexec_clone_sem_trywait_bridge(void *);
void mcexec_clone_sem_destroy_bridge(void *);
void mcexec_fork_sync_lock_bridge(void);
void mcexec_fork_sync_unlock_bridge(void);
void mcexec_fork_sync_munmap_bridge(void *);
void mcexec_fork_sync_free_bridge(void *);
int mcexec_clone_fork_bridge(void);
int mcexec_clone_waitpid_nohang_bridge(int);
void mcexec_clone_sched_yield_bridge(void);
