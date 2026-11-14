#include <stddef.h>
struct list_head {struct list_head *next,*prev;};
struct mcs_rwlock_node_irqsave {unsigned long irqsave;} __attribute__((aligned(64)));
struct mcs_rwlock_lock {unsigned long v;} __attribute__((aligned(64)));
struct mckfd {struct mckfd *next;};
struct process {struct list_head hash_list;unsigned char pad16[152];void *main_thread;unsigned char pad176[80];void *tids;unsigned char pad264[8];struct process *parent;unsigned char pad280[8];struct list_head children_list;unsigned char pad304[16];struct mcs_rwlock_lock children_lock;struct list_head siblings_list;unsigned char pad400[16];int refcount;unsigned char pad420[36];int pid;unsigned char pad460[824];int mckfd_lock;struct mckfd *mckfd;} __attribute__((aligned(64)));
struct resource_set {unsigned char pad[320];struct process *pid1;};
#ifdef ENABLE_TOFU
struct cpu_local_var {unsigned char pad[24368];struct resource_set *resource_set;};
#else
struct cpu_local_var {unsigned char pad[7912];struct resource_set *resource_set;};
#endif
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
#ifdef ENABLE_TOFU
_Static_assert(offsetof(struct cpu_local_var,resource_set)==24368,"resource_set");
#else
_Static_assert(offsetof(struct cpu_local_var,resource_set)==7912,"resource_set");
#endif
