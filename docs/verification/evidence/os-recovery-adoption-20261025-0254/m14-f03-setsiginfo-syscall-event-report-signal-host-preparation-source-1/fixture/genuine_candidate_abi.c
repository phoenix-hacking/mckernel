/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f03-setsiginfo-syscall-event-report-signal-host-preparation-source-1/candidate/kernel/syscall.c"
_Static_assert(sizeof(siginfo_t)==128,"genuine SigInfo128");
_Static_assert(sizeof(struct sig_pending)==160,"genuine SigPending160");
_Static_assert(__builtin_offsetof(struct sig_pending,info)==24,"genuine pendinginfo24");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ptrace_setsiginfo),long (*)(int,siginfo_t *)),"setsiginfo exactlong/int/pointer ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ptrace_syscall_event),void (*)(struct thread *)),"public event void/thread ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ptrace_report_signal_bridge),void (*)(void *,int)),"signal callback void/opaque/int ABI");
const unsigned long f03_ptrace_C_ABI[9]={sizeof(siginfo_t),__alignof__(siginfo_t),sizeof(struct sig_pending),__alignof__(struct sig_pending),__builtin_offsetof(struct sig_pending,info),__builtin_offsetof(struct thread,ptrace),sizeof(int),sizeof(long),IHK_MC_AP_NOWAIT};
