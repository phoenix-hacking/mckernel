/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE FRAGMENT ONLY. */
#include <ihk/context.h>
#include <registers.h>
#include <signal.h>
#include <process.h>
#include <syscall.h>
extern void debug_handler(struct x86_user_context*);
extern const unsigned int x86_debug_handler_debug_print_enabled;
typedef void(*DebugEntry)(struct x86_user_context*);
_Static_assert(__builtin_types_compatible_p(__typeof__(&debug_handler),DebugEntry),"actual assembly target ABI");
_Static_assert(sizeof(enum set_cputime_mode)==4&&__builtin_types_compatible_p(enum set_cputime_mode,unsigned int),"supported enum transport; stop on mismatch");
_Static_assert(CPUTIME_MODE_K2U==0&&CPUTIME_MODE_U2K==1&&CPUTIME_MODE_K2K_IN==2&&CPUTIME_MODE_K2K_OUT==3,"actual enum values");
_Static_assert(SIGTRAP==5&&TRAP_TRACE==2&&TRAP_HWBKPT==4,"actual trap codes");
_Static_assert(DB6_B0==1&&DB6_B1==2&&DB6_B2==4&&DB6_B3==8&&DB6_BS==(1UL<<14),"actual DR6 predicates");
_Static_assert(RFLAGS_TF==(1UL<<8)&&sizeof(unsigned long)==8,"saved flag mask and word ABI");
_Static_assert(sizeof(unsigned int)==4&&__alignof__(unsigned int)==4,"readonly Cconfig ABI");
_Static_assert(sizeof(struct siginfo)==128&&__builtin_offsetof(struct siginfo,si_code)==8,"actual signal storage");
const unsigned long M14_C_DEBUG_ABI[10]={
 sizeof(struct x86_user_context),sizeof(struct siginfo),__alignof__(struct siginfo),
 __builtin_offsetof(struct siginfo,si_code),__builtin_offsetof(struct siginfo,_sifields),
 __builtin_offsetof(struct x86_user_context,gpr.rflags),
 sizeof(enum set_cputime_mode),DB6_BS,DB6_B0|DB6_B1|DB6_B2|DB6_B3,RFLAGS_TF};
