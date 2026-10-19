#include <stddef.h>
struct list_head {struct list_head *next,*prev;};
struct mcs_rwlock_node_irqsave {unsigned long irqsave;} __attribute__((aligned(64)));
struct mcs_rwlock_lock {unsigned long v;} __attribute__((aligned(64)));
struct mckfd {struct mckfd *next;};
struct process {struct list_head hash_list;unsigned char pad16[152];void *main_thread;unsigned char pad176[80];void *tids;unsigned char pad264[8];struct process *parent;unsigned char pad280[8];struct list_head children_list;unsigned char pad304[16];struct mcs_rwlock_lock children_lock;struct list_head siblings_list;unsigned char pad400[16];int refcount;unsigned char pad420[36];int pid;unsigned char pad460[824];int mckfd_lock;struct mckfd *mckfd;} __attribute__((aligned(64)));
struct resource_set {unsigned char pad[320];struct process *pid1;};
struct cpu_local_var {unsigned char pad[7912];struct resource_set *resource_set;};
extern struct cpu_local_var *get_this_cpu_local_var(void);
extern void hugefileobj_cleanup(void);
extern void process_mcs_reader_lock_bridge(unsigned long,void*);
extern void process_mcs_reader_unlock_bridge(unsigned long,void*);
#define mcs_rwlock_reader_lock(lock,node) process_mcs_reader_lock_bridge((unsigned long)(lock),(node))
#define mcs_rwlock_reader_unlock(lock,node) process_mcs_reader_unlock_bridge((unsigned long)(lock),(node))
#define list_empty(head) ((head)->next == (head))
_Static_assert(offsetof(struct process,children_list)==288,"children_list");
_Static_assert(offsetof(struct process,children_lock)==320,"children_lock");
_Static_assert(offsetof(struct resource_set,pid1)==320,"pid1");
_Static_assert(offsetof(struct cpu_local_var,resource_set)==7912,"resource_set");
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
void process_release_profile_bridge(void *proc_arg);
void process_free_thread_pages_bridge(void *thread);
unsigned long process_spin_lock_bridge(unsigned long lock_addr);
void process_spin_unlock_bridge(unsigned long lock_addr, unsigned long flags);
void process_mckfd_free_bridge(struct mckfd *fdp);
void process_optional_free_bridge(void *ptr);
void process_release_hash_detach_bridge(void *resource_set_arg, void *proc_arg);
void process_release_sibling_detach_bridge(void *proc_arg);
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void *process_current_resource_set_bridge(void);
#else
void *process_current_resource_set_bridge(void)
{
	return get_this_cpu_local_var()->resource_set;
}
#endif
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
void process_release_final_cleanup_bridge(void *resource_set_arg);
#else
void process_release_final_cleanup_bridge(void *resource_set_arg)
{
	struct resource_set *rset = resource_set_arg;
	struct mcs_rwlock_node_irqsave lock;

	mcs_rwlock_reader_lock(&rset->pid1->children_lock, &lock);
	if (list_empty(&rset->pid1->children_list)) {
#ifdef ENABLE_TOFU
		extern void tof_utofu_finalize(void);

		tof_utofu_finalize();
#endif
		hugefileobj_cleanup();
	}
	mcs_rwlock_reader_unlock(&rset->pid1->children_lock, &lock);
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
