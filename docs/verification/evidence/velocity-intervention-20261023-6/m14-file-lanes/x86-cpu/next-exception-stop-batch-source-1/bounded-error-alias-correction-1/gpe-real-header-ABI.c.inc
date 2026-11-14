/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE FRAGMENT ONLY; no command/cohort. */
#include <ihk/context.h>
#include <signal.h>
#include <process.h>
#include <syscall.h>
#include <ihk/debug.h>
extern void gpe_handler(struct x86_user_context*);
extern int interrupt_from_user(void*);
extern void interrupt_exit(struct x86_user_context*);
typedef void(*GpeEntry)(struct x86_user_context*);
typedef void(*CputimeFn)(enum set_cputime_mode);
typedef void(*SignalFn)(int,void*,struct siginfo*);
_Static_assert(__builtin_types_compatible_p(__typeof__(&gpe_handler),GpeEntry),"actual assembly target C declaration");
_Static_assert(__builtin_types_compatible_p(__typeof__(&set_cputime),CputimeFn),"existing timing provider declaration");
_Static_assert(__builtin_types_compatible_p(__typeof__(&set_signal),SignalFn),"existing signal provider declaration");
_Static_assert(CPUTIME_MODE_K2U==0&&CPUTIME_MODE_U2K==1&&CPUTIME_MODE_K2K_IN==2&&CPUTIME_MODE_K2K_OUT==3,"actual enum values");
_Static_assert(SIGSEGV==11,"actual signal constant");
_Static_assert(sizeof(enum set_cputime_mode)==4&&__alignof__(enum set_cputime_mode)==4,"actual32-bit enum transport");
_Static_assert(__builtin_types_compatible_p(enum set_cputime_mode,unsigned int),"supported GCC enum transport must match Rust CUInt; stop if different");
_Static_assert(sizeof(int)==4&&sizeof(unsigned long)==8&&sizeof(void*)==8,"supported actual primitive ABI");
const unsigned long M14_C_GPE_ABI[11]={
 sizeof(struct x86_user_context),__alignof__(struct x86_user_context),
 __builtin_offsetof(struct x86_user_context,gpr.error),
 __builtin_offsetof(struct x86_user_context,gpr.cs),
 __builtin_offsetof(struct x86_user_context,gpr.rip),
 __builtin_offsetof(struct x86_user_context,gpr.rsp),
 sizeof(enum set_cputime_mode),CPUTIME_MODE_K2U,CPUTIME_MODE_U2K,
 CPUTIME_MODE_K2K_IN,CPUTIME_MODE_K2K_OUT};
/* C panic's header says void; actual selected provider abort.rs::panic -> !.
 * The future fixture must implement terminal panic with _exit, not return or
 * longjmp/unwind through Rust. No assertion invents a C noreturn annotation. */
