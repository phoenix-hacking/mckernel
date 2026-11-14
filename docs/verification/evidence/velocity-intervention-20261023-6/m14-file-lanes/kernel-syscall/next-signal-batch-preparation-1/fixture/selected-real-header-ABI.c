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
