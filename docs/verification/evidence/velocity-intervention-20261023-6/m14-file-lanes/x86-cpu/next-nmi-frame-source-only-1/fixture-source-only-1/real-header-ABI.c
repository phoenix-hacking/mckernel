/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <ihk/context.h>
extern void mod_nmi_ctx(void *, void(*)()); /* exact kernel/freeze.c declaration */
typedef void(*M14NmiRewriteFn)(void *,void(*)());
_Static_assert(__builtin_types_compatible_p(__typeof__(&mod_nmi_ctx),M14NmiRewriteFn),"actual caller function ABI");
_Static_assert(sizeof(unsigned long)==8&&__alignof__(unsigned long)==8&&sizeof(void*)==8,"actual64-bit word ABI");
_Static_assert(sizeof(void(*)())==8&&RFLAGS_IF==(1UL<<9),"actual function-pointer and IF ABI");
_Static_assert(sizeof(struct x86_basic_regs)==21*sizeof(unsigned long),"real basic-regs21 words");
_Static_assert(sizeof(ihk_mc_user_context_t)==28*sizeof(unsigned long),"real context is28 not27 words");
_Static_assert(__builtin_offsetof(ihk_mc_user_context_t,gpr)==7*sizeof(unsigned long),"real context regs base");
const unsigned long M14_C_NMI_HEADER_ABI[12]={
 sizeof(unsigned long),__alignof__(unsigned long),sizeof(void*),sizeof(void(*)()),
 sizeof(struct x86_basic_regs),__builtin_offsetof(struct x86_basic_regs,rip),
 __builtin_offsetof(struct x86_basic_regs,cs),__builtin_offsetof(struct x86_basic_regs,rflags),
 __builtin_offsetof(struct x86_basic_regs,rsp),__builtin_offsetof(struct x86_basic_regs,ss),
 sizeof(ihk_mc_user_context_t),__builtin_offsetof(ihk_mc_user_context_t,gpr)};
