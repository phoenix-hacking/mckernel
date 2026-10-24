/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <cls.h>
#include <syscall.h>
#include <ihk/context.h>
_Static_assert(sizeof(long)==8 && sizeof(void *)==8 && sizeof(int)==4,"realLP64");
_Static_assert(__builtin_types_compatible_p(__typeof__(&set_signal),void (*)(int,void *,struct siginfo *)),"real public entry ABI");
unsigned long f06_set_signal_actual_ABI[]={sizeof(ihk_mc_user_context_t),
 __builtin_offsetof(ihk_mc_user_context_t,gpr.rsp),sizeof(siginfo_t),sizeof(struct thread),
 __builtin_offsetof(struct thread,proc),__builtin_offsetof(struct thread,tid),__builtin_offsetof(struct thread,sigmask),
 __builtin_offsetof(struct process,pid),__builtin_offsetof(struct cpu_local_var,current)};
