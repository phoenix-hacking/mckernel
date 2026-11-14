/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
/* Appended to actual selected arch TU ONLY for compile-only ABI qualification.
 * Do not link this witness build as production acceptance. No fake headers. */
extern void arch_rt_sigreturn_xrstor_bridge(void *);
extern long arch_native_signal_bad_frame_bridge(long);
extern void arch_rt_sigreturn_context_bridge(struct thread **, struct x86_user_context **, int *);
extern int do_signal(unsigned long, void *, struct thread *, struct sig_pending *, int);
extern void arch_ptrace_regset_log_bridge(int, long);
#define ARCH5_TYPE(fn, type) _Static_assert(__builtin_types_compatible_p(__typeof__(&(fn)), type), #fn " ABI")
ARCH5_TYPE(arch_rt_sigreturn_xrstor_bridge, void (*)(void *));
ARCH5_TYPE(arch_native_signal_bad_frame_bridge, long (*)(long));
ARCH5_TYPE(arch_rt_sigreturn_context_bridge, void (*)(struct thread **,struct x86_user_context **,int *));
ARCH5_TYPE(do_signal, int (*)(unsigned long,void *,struct thread *,struct sig_pending *,int));
ARCH5_TYPE(arch_ptrace_regset_log_bridge, void (*)(int,long));
_Static_assert(sizeof(long)==8 && sizeof(unsigned long)==8 && sizeof(int)==4,"LP64");
_Static_assert(__builtin_offsetof(struct x86_cpu_local_variables,tss.rsp0)==180,"actual GS180");
const unsigned long arch5_c_abi_geometry[] __attribute__((used,section(".arch5_abi_c"))) = {
    sizeof(int), /* 0 int.size */
    __alignof__(int), /* 1 int.align */
    sizeof(long), /* 2 long.size */
    __alignof__(long), /* 3 long.align */
    sizeof(unsigned long), /* 4 ulong.size */
    __alignof__(unsigned long), /* 5 ulong.align */
    sizeof(void *), /* 6 pointer.size */
    __alignof__(void *), /* 7 pointer.align */
    sizeof(siginfo_t), /* 8 siginfo.size */
    __alignof__(siginfo_t), /* 9 siginfo.align */
    sizeof(struct thread), /* 10 thread.size */
    __alignof__(struct thread), /* 11 thread.align */
    sizeof(struct sig_pending), /* 12 pending.size */
    __alignof__(struct sig_pending), /* 13 pending.align */
    sizeof(struct process), /* 14 process.size */
    __alignof__(struct process), /* 15 process.align */
    sizeof(struct sig_common), /* 16 sigcommon.size */
    __alignof__(struct sig_common), /* 17 sigcommon.align */
    sizeof(struct x86_user_context), /* 18 context.size */
    __alignof__(struct x86_user_context), /* 19 context.align */
    sizeof(struct xsave_struct), /* 20 xsave.size */
    __alignof__(struct xsave_struct), /* 21 xsave.align */
    sizeof(struct sigsp), /* 22 frame.size */
    __alignof__(struct sigsp), /* 23 frame.align */
    __builtin_offsetof(struct thread,tid), /* 24 thread.tid */
    __builtin_offsetof(struct thread,exit_status), /* 25 thread.exit_status */
    __builtin_offsetof(struct thread,status), /* 26 thread.status */
    __builtin_offsetof(struct thread,proc), /* 27 thread.proc */
    __builtin_offsetof(struct thread,report_proc), /* 28 thread.report_proc */
    __builtin_offsetof(struct thread,sigcommon), /* 29 thread.sigcommon */
    __builtin_offsetof(struct thread,sigmask), /* 30 thread.sigmask */
    __builtin_offsetof(struct thread,sigstack), /* 31 thread.sigstack */
    __builtin_offsetof(struct thread,ptrace), /* 32 thread.ptrace */
    __builtin_offsetof(struct thread,coredump_regs), /* 33 thread.coredump_regs */
    __builtin_offsetof(struct sig_pending,info), /* 34 pending.info */
    __builtin_offsetof(struct sig_pending,ptracecont), /* 35 pending.ptracecont */
    __builtin_offsetof(struct process,parent), /* 36 process.parent */
    __builtin_offsetof(struct process,main_thread), /* 37 process.main_thread */
    __builtin_offsetof(struct process,update_lock), /* 38 process.update_lock */
    __builtin_offsetof(struct process,pid), /* 39 process.pid */
    __builtin_offsetof(struct process,status), /* 40 process.status */
    __builtin_offsetof(struct process,group_exit_status), /* 41 process.group_exit_status */
    __builtin_offsetof(struct sig_common,lock), /* 42 sigcommon.lock */
    __builtin_offsetof(struct sig_common,action), /* 43 sigcommon.action */
    __builtin_offsetof(struct sigsp,info), /* 44 frame.info */
    __builtin_offsetof(struct sigsp,fpregs), /* 45 frame.fpregs */
    __builtin_offsetof(struct sigsp,sigstack), /* 46 frame.sigstack */
    __builtin_offsetof(siginfo_t,si_signo), /* 47 siginfo.si_signo */
    __builtin_offsetof(siginfo_t,si_code), /* 48 siginfo.si_code */
    __builtin_offsetof(siginfo_t,_sifields), /* 49 siginfo._sifields */
    __builtin_offsetof(siginfo_t,_sifields._sigchld.si_pid), /* 50 siginfo.child.si_pid */
    __builtin_offsetof(siginfo_t,_sifields._sigchld.si_status), /* 51 siginfo.child.si_status */
    __builtin_offsetof(siginfo_t,_sifields._sigchld.si_uid), /* 52 siginfo.child.si_uid */
    __builtin_offsetof(siginfo_t,_sifields._sigchld.si_utime), /* 53 siginfo.child.si_utime */
    __builtin_offsetof(siginfo_t,_sifields._sigchld.si_stime), /* 54 siginfo.child.si_stime */
    __builtin_offsetof(struct x86_cpu_local_variables,tss.rsp0), /* 55 GS.rsp0 */
    SIGCHLD, /* 56 SIGCHLD */
    CLD_TRAPPED, /* 57 CLD_TRAPPED */
    SIGTRAP, /* 58 SIGTRAP */
    SIGSEGV, /* 59 SIGSEGV */
    EFAULT, /* 60 EFAULT */
};
#undef ARCH5_TYPE
