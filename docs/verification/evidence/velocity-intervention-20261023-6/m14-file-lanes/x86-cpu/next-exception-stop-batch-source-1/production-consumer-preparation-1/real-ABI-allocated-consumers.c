/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Real-header ABI and allocated compiler-consumer witness only; never executed.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/next-exception-stop-batch-source-1/bounded-error-alias-correction-1/real-header-ABI.c"
extern void gpe_handler(struct x86_user_context*);
extern void int3_handler(struct x86_user_context*);
extern void debug_handler(struct x86_user_context*);
extern void arch_cpu_stop(void);
#define ATTR(name) __attribute__((used,noinline,externally_visible,section(name)))
ATTR(".text.m14_f04_gpe") void m14_f04_call_gpe(struct x86_user_context*r){gpe_handler(r);}
ATTR(".text.m14_f04_int3") void m14_f04_call_int3(struct x86_user_context*r){int3_handler(r);}
ATTR(".text.m14_f04_debug") void m14_f04_call_debug(struct x86_user_context*r){debug_handler(r);}
ATTR(".text.m14_f04_stop") void m14_f04_call_stop(void){arch_cpu_stop();}
#undef ATTR
typedef void(*M14F04Trap)(struct x86_user_context*);
typedef void(*M14F04Stop)(void);
__attribute__((used,section(".rodata.m14_f04_traps"))) const M14F04Trap M14_F04_TRAP_TARGETS[3]={gpe_handler,int3_handler,debug_handler};
__attribute__((used,section(".rodata.m14_f04_stop"))) const M14F04Stop M14_F04_STOP_TARGET=arch_cpu_stop;
