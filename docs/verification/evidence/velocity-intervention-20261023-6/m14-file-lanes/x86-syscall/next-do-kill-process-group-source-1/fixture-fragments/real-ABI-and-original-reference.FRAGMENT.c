/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Future fixture source fragments only: no executable/driver/compiler grant.
 */
#include <process.h>
#include <cls.h>
#include <syscall.h>
#include <kmalloc.h>
#include <errno.h>
extern int arch_do_kill_process_group_result(struct thread *,int,int,siginfo_t *,int,struct process_hash *);
_Static_assert(sizeof(int)==4 && sizeof(unsigned long)==8 && sizeof(void *)==8,"realLP64");
_Static_assert(HASH_SIZE==73,"real73bucket process hash");
_Static_assert(sizeof(struct mcs_rwlock_node_irqsave)==64 && __alignof__(struct mcs_rwlock_node_irqsave)==64,"real synchronous lock node");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_do_kill_process_group_result),int (*)(struct thread *,int,int,siginfo_t *,int,struct process_hash *)),"selected group helper ABI");
unsigned long f06_group_actual_ABI[] = {sizeof(struct process_hash),__alignof__(struct process_hash),
 __builtin_offsetof(struct process_hash,list),__builtin_offsetof(struct process_hash,lock),
 sizeof(struct process),__builtin_offsetof(struct process,hash_list),__builtin_offsetof(struct process,pid),__builtin_offsetof(struct process,pgid),
 __builtin_offsetof(struct thread,proc),sizeof(siginfo_t),sizeof(struct mcs_rwlock_node_irqsave),HASH_SIZE};
/* Rename do_kill to an explicit controlled recursive-delivery endpoint only in
 * the original reference branch; real lock/allocator ABI retained. Define the
 * lock/allocator controls in the eventual single bounded fixture, not here. */
unsigned long f06_group_reference_FRAGMENT(struct thread *thread,int pid,int sig,siginfo_t *info,int ptracecont,struct process_hash *phash)
{
 int tid=-1,i;
#include "original-process-group-branch.ACTUAL.inc"
 __builtin_unreachable();
}
