/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <syscall.h>
_Static_assert(sizeof(struct sig_pending)==160,"actual pending extent");
_Static_assert(__builtin_offsetof(struct sig_pending,list)==0,"pending list owner");
_Static_assert(__builtin_offsetof(struct sig_pending,sigmask)==16,"pending mask");
_Static_assert(__builtin_offsetof(struct sig_pending,info)==24,"pending full info");
_Static_assert(__builtin_offsetof(struct sig_pending,ptracecont)==152,"ptrace coalescing key");
_Static_assert(__builtin_offsetof(struct sig_pending,interrupted)==156,"zeroed interruption state");
_Static_assert(sizeof(siginfo_t)==128,"byte-exact info");
unsigned long f06_pending_actual_ABI[]={sizeof(struct thread),__builtin_offsetof(struct thread,sigevent),sizeof(struct list_head),sizeof(struct sig_pending),__alignof__(struct sig_pending)};
