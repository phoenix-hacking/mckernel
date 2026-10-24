/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE FRAGMENT ONLY, no command/cohort. */
#include <ihk/context.h>
#include <signal.h>
#include <process.h>
#include <syscall.h>
extern void int3_handler(struct x86_user_context*);
extern const unsigned int x86_int3_debug_print_enabled;
typedef void(*Int3Entry)(struct x86_user_context*);
typedef void(*SignalFn)(int,void*,struct siginfo*);
_Static_assert(__builtin_types_compatible_p(__typeof__(&int3_handler),Int3Entry),"actual assembly target declaration");
_Static_assert(__builtin_types_compatible_p(__typeof__(&set_signal),SignalFn),"unchanged typed signal callback");
_Static_assert(SIGTRAP==5&&TRAP_BRKPT==1,"actual signal constants");
_Static_assert(CPUTIME_MODE_K2U==0&&CPUTIME_MODE_U2K==1&&CPUTIME_MODE_K2K_IN==2&&CPUTIME_MODE_K2K_OUT==3,"actual enum values");
_Static_assert(sizeof(enum set_cputime_mode)==4&&__builtin_types_compatible_p(enum set_cputime_mode,unsigned int),"supported enum transport; stop on mismatch");
_Static_assert(sizeof(unsigned int)==4&&__alignof__(unsigned int)==4,"immutable debug data ABI");
_Static_assert(sizeof(struct siginfo)==128&&__builtin_offsetof(struct siginfo,si_code)==8,"real signal storage");
const unsigned long M14_C_INT3_ABI[13]={
 sizeof(struct x86_user_context),__alignof__(struct x86_user_context),
 sizeof(struct siginfo),__alignof__(struct siginfo),
 __builtin_offsetof(struct siginfo,si_code),__builtin_offsetof(struct siginfo,_sifields),
 sizeof(enum set_cputime_mode),sizeof(unsigned int),
 __builtin_offsetof(struct x86_user_context,gpr.rsp),
 SIGTRAP,TRAP_BRKPT,CPUTIME_MODE_K2K_IN,CPUTIME_MODE_K2K_OUT};
/* Compile the same gate once undefined and once defined (including value0).
 * R4 datum must be0 only when undefined, and1 whenever defined. No Rustcfg
 * forwarding or production compiler/module expansion is assumed. */
