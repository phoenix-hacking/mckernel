#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-signal-batch-preparation-1/candidate/syscall.c"
/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
_Static_assert(sizeof(struct thread)==5568 && _Alignof(struct thread)==64,"actual Thread extent");
_Static_assert(sizeof(struct sig_common)==2176 && _Alignof(struct sig_common)==64,"actual SigCommon extent");
_Static_assert(sizeof(struct sig_pending)==160,"actual SigPending extent");
_Static_assert(sizeof(struct mcs_rwlock_node_irqsave)==64 && _Alignof(struct mcs_rwlock_node_irqsave)==64,"actual IRQ node");
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_pending_mask_bridge),unsigned long(*)(void*)),"pending ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_sigsuspend_bridge),long(*)(void*,void*)),"suspend ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&do_sigaction),int(*)(int,struct k_sigaction*,struct k_sigaction*)),"sigaction ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_do_sigaction_bridge),int(*)(int,void*,void*)),"public callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_forward_sigaction_update_bridge),long(*)(int,const void*)),"unchanged C forward debt ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&do_signal),int(*)(unsigned long,void*,struct thread*,struct sig_pending*,int)),"ownership handoff ABI");

/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <types.h>
#include <ihk/context.h>
#include <signal.h>
_Static_assert(sizeof(unsigned long)==8,"selected LP64 ulong");
_Static_assert(sizeof(ihk_mc_user_context_t)==224 && _Alignof(ihk_mc_user_context_t)==8,"context extent/alignment");
_Static_assert(__builtin_offsetof(ihk_mc_user_context_t,gpr)==56,"actual gpr offset");
_Static_assert(__builtin_offsetof(ihk_mc_user_context_t,gpr.rdi)==168 && __builtin_offsetof(ihk_mc_user_context_t,gpr.rsi)==160 && __builtin_offsetof(ihk_mc_user_context_t,gpr.rdx)==152,"actual selected argument offsets");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_syscall_arg0),unsigned long(*)(const ihk_mc_user_context_t*)),"const arg0 getter ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_syscall_set_arg0),void(*)(ihk_mc_user_context_t*,unsigned long)),"mutable arg0 setter ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_syscall_arg1),unsigned long(*)(const ihk_mc_user_context_t*)),"const arg1 getter ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_syscall_set_arg1),void(*)(ihk_mc_user_context_t*,unsigned long)),"mutable arg1 setter ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_syscall_arg2),unsigned long(*)(const ihk_mc_user_context_t*)),"const arg2 getter ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_syscall_set_arg2),void(*)(ihk_mc_user_context_t*,unsigned long)),"mutable arg2 setter ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&__sigmask),unsigned long(*)(unsigned long)),"signal-mask ABI");
