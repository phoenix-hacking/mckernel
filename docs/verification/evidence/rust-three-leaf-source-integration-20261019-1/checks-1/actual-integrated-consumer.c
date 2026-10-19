#ifndef IHK_DEBUG_H
#define IHK_DEBUG_H

#define __aligned(n) __attribute__((aligned(n)))

void panic(const char *);

/* when someone has a lot of time, add attribute __printf(1, 2) to kprintf */
int kprintf(const char *format, ...);
unsigned long kprintf_lock(void);
void kprintf_unlock(unsigned long irqflags);
int __kprintf(const char *format, ...);

struct ddebug {
	const char *file;
	const char *func;
	const char *fmt;
	unsigned int line:24;
	unsigned int flags:8;
} __aligned(8);

#define DDEBUG_NONE  0x0
#define DDEBUG_PRINT 0x1

#define DDEBUG_DEFAULT DDEBUG_NONE

#define dkprintf(fmt, args...)        \
do {                                  \
	static struct ddebug __aligned(8) \
	__attribute__((section("__verbose"))) ddebug = { \
		.file = __FILE__,        \
		.func = __func__,        \
		.line = __LINE__,        \
		.flags = DDEBUG_DEFAULT, \
	};                            \
	if (ddebug.flags)             \
		kprintf(fmt, ##args); \
} while (0)
#define ekprintf(fmt, args...) kprintf(fmt, ##args)

#define BUG_ON(condition) do {                         \
	if (condition) {                               \
		kprintf("PANIC: %s: %s(line:%d)\n",    \
			__FILE__, __func__, __LINE__); \
		panic("");                             \
	}                                              \
} while (0)

#endif

#include <stddef.h>
struct list_head {struct list_head *next,*prev;};
struct timespec {long tv_sec,tv_nsec;};
struct mcs_rwlock_lock {unsigned long flags[8];} __attribute__((aligned(64)));
struct mcs_rwlock_node_irqsave {unsigned long irqsave;} __attribute__((aligned(64)));
struct mcexec_tid {int tid,padding;struct thread *thread;};
struct thread_hash {struct list_head list[73];struct mcs_rwlock_lock lock[73];};
struct resource_set {unsigned char prefix[32];struct thread_hash *thread_hash;unsigned char tail[344];} __attribute__((aligned(64)));
struct cpu_local_var {unsigned char prefix[7912];struct resource_set *resource_set;unsigned char tail[208];} __attribute__((aligned(64)));
struct process {unsigned char prefix[64];struct mcs_rwlock_lock update_lock;unsigned char middle[128];struct mcexec_tid *tids;int nr_tids;unsigned char middle2[1028];struct timespec stime,utime;unsigned char tail[400];};
struct thread {struct list_head hash_list;int cpu_id,tid;unsigned char middle[4280];struct process *proc;unsigned char middle2[728];unsigned long system_tsc,user_tsc;unsigned char tail[512];} __attribute__((aligned(64)));
extern struct cpu_local_var *get_this_cpu_local_var(void);
extern int thread_hash(int);
extern int process_list_is_linked_result(const struct list_head*);
extern void process_list_detach_result(struct list_head*);
extern void mcs_rwlock_writer_lock(struct mcs_rwlock_lock*,struct mcs_rwlock_node_irqsave*);
extern void mcs_rwlock_writer_unlock(struct mcs_rwlock_lock*,struct mcs_rwlock_node_irqsave*);
extern void tsc_to_ts(unsigned long,struct timespec*);
extern void ts_add(struct timespec*,const struct timespec*);
typedef void (*process_tid_log_fn_t)(int,void*,int);
int process_release_tid_body_result(
	void *tids, int nr_tids, unsigned long tid_stride,
	unsigned long tid_thread_offset, void *thread, int thread_tid,
	process_tid_log_fn_t log_fn);
#ifndef MCKERNEL_RUST_PROCESS_HELPERS
static void process_release_tid_log_bridge(int tid, void *thread, int new_tid)
{
	(void)new_tid;
	dkprintf("%s: tid %d has been released by %p\n",
		"__release_tid", tid, thread);
}
#endif
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void __release_tid(struct process *proc, struct thread *thread);
#else
void __release_tid(struct process *proc, struct thread *thread) {
	process_release_tid_body_result(proc->tids, proc->nr_tids,
		sizeof(proc->tids[0]),
		__builtin_offsetof(struct mcexec_tid, thread),
		thread, thread->tid, process_release_tid_log_bridge);
}
#endif
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_destroy_thread_time_account_bridge(void *thread_arg);
#else
void process_destroy_thread_time_account_bridge(void *thread_arg)
{
	struct thread *thread = thread_arg;
	struct process *proc = thread->proc;
	struct mcs_rwlock_node_irqsave updatelock;
	struct timespec ats;

	mcs_rwlock_writer_lock(&proc->update_lock, &updatelock);
	tsc_to_ts(thread->system_tsc, &ats);
	ts_add(&thread->proc->stime, &ats);
	tsc_to_ts(thread->user_tsc, &ats);
	ts_add(&thread->proc->utime, &ats);
	mcs_rwlock_writer_unlock(&proc->update_lock, &updatelock);
}
#endif
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_destroy_thread_hash_detach_bridge(void *thread_arg);
#else
void process_destroy_thread_hash_detach_bridge(void *thread_arg)
{
	struct thread *thread = thread_arg;
	struct mcs_rwlock_node_irqsave lock;

	if (process_list_is_linked_result(&thread->hash_list)) {
		struct resource_set *resource_set = get_this_cpu_local_var()->resource_set;
		int hash = thread_hash(thread->tid);

		mcs_rwlock_writer_lock(&resource_set->thread_hash->lock[hash],
					&lock);
		process_list_detach_result(&thread->hash_list);
		mcs_rwlock_writer_unlock(&resource_set->thread_hash->lock[hash],
					&lock);
	}
}
#endifvoid process_destroy_thread_release_tid_bridge(void *proc_arg,
					       void *thread_arg)
{
	__release_tid(proc_arg, thread_arg);
}
void process_mcs_writer_lock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_lock((struct mcs_rwlock_lock *)lock_addr,
			       (struct mcs_rwlock_node_irqsave *)node);
}
void process_mcs_writer_unlock_bridge(unsigned long lock_addr, void *node)
{
	mcs_rwlock_writer_unlock((struct mcs_rwlock_lock *)lock_addr,
				 (struct mcs_rwlock_node_irqsave *)node);
}
