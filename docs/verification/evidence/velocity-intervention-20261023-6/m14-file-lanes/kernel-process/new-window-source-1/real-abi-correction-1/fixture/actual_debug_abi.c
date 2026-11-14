/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <cpulocal.h>
#include <cls.h>
__attribute__((used,section(".process_debug_abi")))
const unsigned long PROCESS_DEBUG_C_ABI[] = {
    sizeof(struct mcs_rwlock_lock),
    __alignof__(struct mcs_rwlock_lock),
    sizeof(struct mcs_rwlock_node_irqsave),
    __alignof__(struct mcs_rwlock_node_irqsave),
    HASH_SIZE,
    __builtin_offsetof(struct cpu_local_var, resource_set),
    __builtin_offsetof(struct resource_set, process_hash),
    __builtin_offsetof(struct resource_set, thread_hash),
    __builtin_offsetof(struct resource_set, pid1),
    __builtin_offsetof(struct process_hash, list),
    __builtin_offsetof(struct process_hash, lock),
    __builtin_offsetof(struct thread_hash, list),
    __builtin_offsetof(struct thread_hash, lock),
    __builtin_offsetof(struct process, hash_list),
    __builtin_offsetof(struct process, ppid_parent),
    __builtin_offsetof(struct process, refcount),
    __builtin_offsetof(struct process, status),
    __builtin_offsetof(struct process, pid),
    __builtin_offsetof(struct thread, hash_list),
    __builtin_offsetof(struct thread, proc),
    __builtin_offsetof(struct thread, cpu_id),
    __builtin_offsetof(struct thread, tid),
    __builtin_offsetof(struct thread, status),
    __builtin_offsetof(struct thread, in_syscall_offload),
    __builtin_offsetof(struct thread, refcount),
    __builtin_offsetof(struct thread, ptrace),
    __builtin_offsetof(struct list_head, next),
    sizeof(((struct process *)0)->refcount),
    __builtin_offsetof(__typeof__(((struct process *)0)->refcount), counter),
};
_Static_assert(sizeof(unsigned long)==8,"supported u64 ABI words");
_Static_assert(sizeof(struct mcs_rwlock_node_irqsave)==64 && __alignof__(struct mcs_rwlock_node_irqsave)==64,"actual callback node geometry");
