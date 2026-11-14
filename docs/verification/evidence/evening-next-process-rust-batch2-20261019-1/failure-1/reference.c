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
#define process_current_resource_set_bridge c_process_current_resource_set_bridge
void *process_current_resource_set_bridge(void)
{
	return get_this_cpu_local_var()->resource_set;
}
#undef process_current_resource_set_bridge
#define process_release_final_cleanup_bridge c_process_release_final_cleanup_bridge
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
#undef process_release_final_cleanup_bridge
