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
