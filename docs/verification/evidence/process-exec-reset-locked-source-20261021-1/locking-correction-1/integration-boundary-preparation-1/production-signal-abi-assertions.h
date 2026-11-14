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
