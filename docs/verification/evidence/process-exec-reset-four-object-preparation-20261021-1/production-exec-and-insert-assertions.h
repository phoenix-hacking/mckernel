/* Assertions only; actual TU already includes its production headers. */
_Static_assert(sizeof(unsigned long)==8,"LP64");
_Static_assert(sizeof(struct rb_node)==24,"rb node ABI");
_Static_assert(sizeof(struct vm_range_numa_policy)==80,"NUMA policy ABI");
_Static_assert(__builtin_offsetof(struct vm_range_numa_policy,policy_rb_node)==0,"policy node offset");
_Static_assert(__builtin_offsetof(struct vm_range_numa_policy,start)==24,"policy start offset");
_Static_assert(__builtin_offsetof(struct vm_range_numa_policy,numa_mask)==40,"policy mask offset");
_Static_assert(__builtin_offsetof(struct process_vm,vm_range_numa_policy_tree)==248,"policy root offset");
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
typedef int (*insert_signature_t)(struct process_vm *,struct vm_range_numa_policy *,
 void (*)(struct rb_node *,struct rb_node *,struct rb_node **),
 void (*)(struct rb_node *,struct rb_root *),
 void (*)(struct process_vm *,struct vm_range_numa_policy *,struct vm_range_numa_policy *));
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_vm_policy_insert_body_result),insert_signature_t),"Rust insertion callback ABI");
#endif

/* Compile-only production header/ABI proof; no implementation or fake layout. */
#include <process.h>
_Static_assert(_NSIG == 64 && SS_DISABLE == 2, "exec signal constants");
_Static_assert(__builtin_offsetof(struct thread, sigcommon) == 4824, "Thread.sigcommon");
_Static_assert(__builtin_offsetof(struct thread, sigstack) == 4840, "Thread.sigstack");
_Static_assert(sizeof(((struct thread *)0)->sigstack) == 24, "SigStack.size");
_Static_assert(__builtin_offsetof(struct thread, sigstack.ss_sp) - __builtin_offsetof(struct thread, sigstack) == 0, "SigStack.sp");
_Static_assert(__builtin_offsetof(struct thread, sigstack.ss_flags) - __builtin_offsetof(struct thread, sigstack) == 8, "SigStack.flags");
_Static_assert(__builtin_offsetof(struct thread, sigstack.ss_size) - __builtin_offsetof(struct thread, sigstack) == 16, "SigStack.sizefield");
_Static_assert(sizeof(struct sig_common) == 2176, "SigCommon.size");
_Static_assert(__alignof__(struct sig_common) == 64, "SigCommon.align");
_Static_assert(__builtin_offsetof(struct sig_common, lock) == 0, "SigCommon.lock");
_Static_assert(__builtin_offsetof(struct sig_common, use) == 64, "SigCommon.refcount");
_Static_assert(__builtin_offsetof(struct sig_common, action) == 72, "SigCommon.action");
_Static_assert(__builtin_offsetof(struct sig_common, sigpending) == 2120, "SigCommon.pending");
_Static_assert(sizeof(((struct sig_common *)0)->action[0]) == 32, "KSigAction.stride");
_Static_assert(__builtin_offsetof(struct k_sigaction, sa.sa_handler) == 0, "KSigAction.handler");
_Static_assert(sizeof(((struct sig_common *)0)->action[0].sa.sa_handler) == 8, "handler.word");
_Static_assert(sizeof(struct mcs_rwlock_node_irqsave) == 64, "MCS.node.size");
_Static_assert(__alignof__(struct mcs_rwlock_node_irqsave) == 64, "MCS.node.align");
_Static_assert(sizeof(((struct sig_common *)0)->lock) == 64, "MCS.lock.size");

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
_Static_assert(__builtin_types_compatible_p(__typeof__(&exec_reset_signal_state_current_v1),void (*)(struct thread *)),"Rust exec reset ABI");
#endif
