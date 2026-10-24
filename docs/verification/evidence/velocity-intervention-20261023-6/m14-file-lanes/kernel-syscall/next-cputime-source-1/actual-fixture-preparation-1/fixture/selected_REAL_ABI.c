/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE ONLY; future syntax-only command must retain actual selected TU flags/headers.
 */
#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
#error selected Rust policy required
#endif
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-cputime-source-1/actual-fixture-preparation-1/candidate/syscall.c"
_Static_assert(sizeof(enum set_cputime_mode)==4, "mode ABI bits");
_Static_assert(CPUTIME_MODE_K2U==0 && CPUTIME_MODE_U2K==1 &&
 CPUTIME_MODE_K2K_IN==2 && CPUTIME_MODE_K2K_OUT==3, "mode constants");
_Static_assert(IHK_OS_MONITOR_USER==2 && IHK_OS_MONITOR_KERNEL==3, "monitor constants");
_Static_assert(SIGVTALRM==26 && SIGPROF==27, "signal constants");
_Static_assert(__builtin_types_compatible_p(__typeof__(&reset_cputime),void(*)(void)), "reset ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&set_cputime),void(*)(enum set_cputime_mode)), "set ABI");
_Static_assert(sizeof(((struct thread*)0)->base_tsc)==8 &&
 sizeof(((struct thread*)0)->system_tsc)==8 && sizeof(((struct thread*)0)->user_tsc)==8,
 "unsigned accounting widths");
_Static_assert(sizeof(((struct cpu_local_var*)0)->monitor->counter)==8, "monitor wrap width");
