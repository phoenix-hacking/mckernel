/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Compile-only complete selected TU+real ABI+allocated C caller witness; never execute. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/passed-exceptions-wakeup-production-successor-1/candidate/arch/x86_64/kernel/cpu.c"
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/next-exception-stop-batch-source-1/bounded-error-alias-correction-1/real-header-ABI.c"
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/next-x86-wakeup-source-only-1/current-canonical-successor-1/leaf-fixture-preparation-1/FUTURE-C-TYPE-ABI.c.inc"
extern void gpe_handler(struct x86_user_context*);
extern void int3_handler(struct x86_user_context*);
extern void debug_handler(struct x86_user_context*);
extern void arch_cpu_stop(void);
#define ATTR(name) __attribute__((__used__,__noinline__,__externally_visible__,__section__(name)))
ATTR(".text.m14_f04_gpe") void m14_f04_call_gpe(struct x86_user_context*r){gpe_handler(r);}
ATTR(".text.m14_f04_int3") void m14_f04_call_int3(struct x86_user_context*r){int3_handler(r);}
ATTR(".text.m14_f04_debug") void m14_f04_call_debug(struct x86_user_context*r){debug_handler(r);}
ATTR(".text.m14_f04_stop") void m14_f04_call_stop(void){arch_cpu_stop();}
#undef ATTR
typedef void(*M14F04Trap)(struct x86_user_context*);
typedef void(*M14F04Stop)(void);
__attribute__((used,section(".rodata.m14_f04_traps"))) const M14F04Trap M14_F04_TRAP_TARGETS[3]={gpe_handler,int3_handler,debug_handler};
__attribute__((used,section(".rodata.m14_f04_stop"))) const M14F04Stop M14_F04_STOP_TARGET=arch_cpu_stop;
