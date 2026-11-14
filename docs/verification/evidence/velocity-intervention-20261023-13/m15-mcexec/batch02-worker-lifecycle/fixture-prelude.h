/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <assert.h>
struct thread_data_s {
 struct thread_data_s *next; pthread_t thread_id;
 int cpu,ret,tid,terminate,remote_tid,remote_cpu,joined,detached;
 pthread_mutex_t *lock; pthread_barrier_t *init_ready;
};
extern struct thread_data_s *thread_data;
extern pthread_mutex_t lock;
extern pthread_barrier_t init_ready,uti_init_ready;
extern int n_threads;
static int max_cpuid;
void *mcexec_main_loop_thread_func_body(void *);
int mcexec_create_worker_thread_body(struct thread_data_s **,void *);
int init_worker_threads(int);
void mcexec_join_all_threads_body(void);
void *mcexec_join_all_threads_head_bridge(void);
int mcexec_kill_thread_pthread_kill_bridge(struct thread_data_s *,int);
void mcexec_init_worker_threads_reset_cpuid_bridge(void);
void mcexec_util_thread_barrier_init_bridge(void);
int mcexec_util_thread_create_worker_bridge(struct thread_data_s **);
void mcexec_util_thread_barrier_wait_bridge(void);
int mcexec_main_loop_thread_barrier_wait_bridge(void *);
#define main_loop_thread_func mcexec_main_loop_thread_func_body
#define create_worker_thread mcexec_create_worker_thread_body
