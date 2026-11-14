#include <stddef.h>
struct list_head {struct list_head *next,*prev;};
struct mcs_rwlock_node_irqsave {unsigned long irqsave;} __attribute__((aligned(64)));
struct mcs_rwlock_lock {unsigned long v;} __attribute__((aligned(64)));
struct mckfd {struct mckfd *next;};
struct process {struct list_head hash_list;unsigned char pad16[152];void *main_thread;unsigned char pad176[80];void *tids;unsigned char pad264[8];struct process *parent;unsigned char pad280[40];struct mcs_rwlock_lock children_lock;struct list_head siblings_list;unsigned char pad400[16];int refcount;unsigned char pad420[36];int pid;unsigned char pad460[824];int mckfd_lock;struct mckfd *mckfd;} __attribute__((aligned(64)));
struct process_hash {struct list_head list[73];struct mcs_rwlock_lock lock[73];};
struct resource_set {unsigned char pad[24];struct process_hash *process_hash;};
extern int process_hash(int);
extern int process_list_is_linked_result(const struct list_head*);
extern void process_list_detach_result(struct list_head*);
extern void process_mcs_writer_lock_bridge(unsigned long,void*);
extern void process_mcs_writer_unlock_bridge(unsigned long,void*);
#define mcs_rwlock_writer_lock(lock,node) process_mcs_writer_lock_bridge((unsigned long)(lock),(node))
#define mcs_rwlock_writer_unlock(lock,node) process_mcs_writer_unlock_bridge((unsigned long)(lock),(node))
_Static_assert(offsetof(struct process,parent)==272,"parent");
_Static_assert(offsetof(struct process,children_lock)==320,"children lock");
_Static_assert(offsetof(struct process,siblings_list)==384,"siblings");
_Static_assert(offsetof(struct process,pid)==456,"pid");
_Static_assert(offsetof(struct process_hash,lock)==1216,"bucket lock");
typedef void (*process_mckfd_free_fn_t)(struct mckfd *fdp);
typedef int (*process_ref_dec_and_test_fn_t)(void *object,
					     unsigned long ref_offset);
typedef void *(*process_current_resource_set_fn_t)(void);
typedef void (*process_resource_process_action_fn_t)(void *resource_set,
						     void *process);
typedef void (*process_process_action_fn_t)(void *process);
typedef void (*process_resource_set_action_fn_t)(void *resource_set);
typedef void (*process_thread_action_fn_t)(void *thread);
typedef unsigned long (*process_spin_lock_fn_t)(unsigned long lock_addr);
typedef void (*process_spin_unlock_fn_t)(unsigned long lock_addr,
					 unsigned long irqstate);
typedef void (*process_free_fn_t)(void *ptr);
int process_release_process_body_result(
	void *proc, unsigned long refcount_offset, unsigned long tids_offset,
	unsigned long main_thread_offset, unsigned long mckfd_offset,
	unsigned long mckfd_lock_offset, unsigned long mckfd_next_offset,
	process_ref_dec_and_test_fn_t dec_fn,
	process_current_resource_set_fn_t current_resource_set_fn,
	process_resource_process_action_fn_t hash_detach_fn,
	process_process_action_fn_t sibling_detach_fn,
	process_process_action_fn_t profile_fn,
	process_thread_action_fn_t free_thread_pages_fn,
	process_spin_lock_fn_t lock_fn, process_spin_unlock_fn_t unlock_fn,
	process_mckfd_free_fn_t mckfd_free_fn, process_free_fn_t free_fn,
	process_resource_set_action_fn_t final_cleanup_fn);
void *process_current_resource_set_bridge(void);
void process_release_profile_bridge(void *proc_arg);
void process_free_thread_pages_bridge(void *thread);
unsigned long process_spin_lock_bridge(unsigned long lock_addr);
void process_spin_unlock_bridge(unsigned long lock_addr, unsigned long flags);
void process_mckfd_free_bridge(struct mckfd *fdp);
void process_optional_free_bridge(void *ptr);
void process_release_final_cleanup_bridge(void *resource_set_arg);
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_release_hash_detach_bridge(void *resource_set_arg,
					void *proc_arg);
#else
void process_release_hash_detach_bridge(void *resource_set_arg,
					void *proc_arg)
{
	struct resource_set *resource_set = resource_set_arg;
	struct process *proc = proc_arg;
	struct mcs_rwlock_node_irqsave lock;

	if (process_list_is_linked_result(&proc->hash_list)) {
		struct process_hash *phash = resource_set->process_hash;
		int hash = process_hash(proc->pid);

		mcs_rwlock_writer_lock(&phash->lock[hash], &lock);
		process_list_detach_result(&proc->hash_list);
		mcs_rwlock_writer_unlock(&phash->lock[hash], &lock);
	}
}
#endif
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_release_sibling_detach_bridge(void *proc_arg);
#else
void process_release_sibling_detach_bridge(void *proc_arg)
{
	struct process *proc = proc_arg;
	struct process *parent = proc->parent;
	struct mcs_rwlock_node_irqsave lock;

	mcs_rwlock_writer_lock(&parent->children_lock, &lock);
	process_list_detach_result(&proc->siblings_list);
	mcs_rwlock_writer_unlock(&parent->children_lock, &lock);
}
#endif
#ifndef MCKERNEL_RUST_PROCESS_HELPERS
void
release_process(struct process *proc)
{
	process_release_process_body_result(proc,
		__builtin_offsetof(struct process, refcount),
		__builtin_offsetof(struct process, tids),
		__builtin_offsetof(struct process, main_thread),
		__builtin_offsetof(struct process, mckfd),
		__builtin_offsetof(struct process, mckfd_lock),
		__builtin_offsetof(struct mckfd, next),
		NULL,
		process_current_resource_set_bridge,
		process_release_hash_detach_bridge,
		process_release_sibling_detach_bridge,
		process_release_profile_bridge,
		process_free_thread_pages_bridge,
		process_spin_lock_bridge,
		process_spin_unlock_bridge,
		process_mckfd_free_bridge,
		process_optional_free_bridge,
		process_release_final_cleanup_bridge);
}
#endif
