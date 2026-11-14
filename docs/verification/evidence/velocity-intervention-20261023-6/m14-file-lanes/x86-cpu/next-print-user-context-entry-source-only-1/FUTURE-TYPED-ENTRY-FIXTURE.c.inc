/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE FRAGMENT ONLY: actual C selected wrapper and actual unchanged Rust
 * core compare the same initialized real context and typed log callback tape.
 * No main/driver/argv/second execution queue.
 */
#include <ihk/context.h>
extern int x86_print_user_context_body_result(const void*,void(*)(int,unsigned long,unsigned long,unsigned long,unsigned long));
static unsigned tape_count,failed;
static unsigned long tape[3][5];
void x86_context_line_log_bridge(int event,unsigned long a,unsigned long b,unsigned long c,unsigned long d){
 if(tape_count>=3){failed=1;return;}
 unsigned long *row=tape[tape_count++];row[0]=(unsigned long)event;row[1]=a;row[2]=b;row[3]=c;row[4]=d;
}
#define ihk_mc_print_user_context original_print_user_context
#include "ORIGINAL-SELECTED-C-BODY.inc"
#undef ihk_mc_print_user_context
extern void ihk_mc_print_user_context(ihk_mc_user_context_t*);
typedef void(*PrintEntry)(ihk_mc_user_context_t*);
_Static_assert(__builtin_types_compatible_p(__typeof__(&original_print_user_context),PrintEntry),"actual selected C entry ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_print_user_context),PrintEntry),"new Rust export ABI");
_Static_assert(sizeof(unsigned long)==8 && sizeof(int)==4,"actual typed log fields");
static unsigned m14_print_user_context_run(PrintEntry entry,ihk_mc_user_context_t *ctx,unsigned long out[3][5]){
 tape_count=failed=0;
 for(unsigned i=0;i<3;i++)for(unsigned j=0;j<5;j++)tape[i][j]=0;
 entry(ctx);
 for(unsigned i=0;i<3;i++)for(unsigned j=0;j<5;j++)out[i][j]=tape[i][j];
 return failed?99:tape_count;
}
static int m14_print_user_context_expected(const unsigned long got[3][5],unsigned count,const ihk_mc_user_context_t *ctx){
 if(!ctx)return count!=0;
 if(count!=3)return 1;
 unsigned long want[3][5]={{20,ctx->gpr.cs,ctx->gpr.rip,0,0},
  {21,ctx->gpr.rax,ctx->gpr.rbx,ctx->gpr.rcx,ctx->gpr.rdx},
  {22,ctx->gpr.rsi,ctx->gpr.rdi,ctx->gpr.rsp,0}};
 for(unsigned i=0;i<3;i++)for(unsigned j=0;j<5;j++)if(got[i][j]!=want[i][j])return 1;
 return 0;
}
/* Future cases: all 64 single-bit/complement values and edge words in each
 * printed field; initialized real-context storage; NULL gets zero log events.
 * Original selected C wrapper and actual Rust entry must both equal this tape.
 * Logger formatting itself is already accepted context-code reuse, controlled
 * as this typed callback; no replay/native/valid-kernel-frame claim is made. */
