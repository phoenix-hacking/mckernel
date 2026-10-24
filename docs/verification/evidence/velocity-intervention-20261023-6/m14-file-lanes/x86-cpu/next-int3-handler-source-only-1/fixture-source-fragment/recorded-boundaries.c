/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE FRAGMENT ONLY. No main/driver/argv or second executable cohort.
 * Future harness pairs originalC/actualRust using identical immutable debug
 * gate variants and real headers. No INT3/IRET/STI/signal/scheduler execution.
 */
#include <ihk/context.h>
#include <signal.h>
#include <process.h>
#include <syscall.h>
#ifdef DEBUG_PRINT_CPU
const unsigned int x86_int3_debug_print_enabled=1;
#else
const unsigned int x86_int3_debug_print_enabled=0;
#endif
struct M14Int3Case{
 unsigned long error,cs,rip,rsp,display_cs,exit_rsp;
 unsigned rewrite_display_cs,rewrite_exit_rsp;
 int ignored_kprintf_return;
};
enum{M14_INT3_TAPE_WORDS=40};
static unsigned long tape[M14_INT3_TAPE_WORDS];
static struct x86_user_context*active;
static struct M14Int3Case inputs;
static unsigned failed;
static int same(const char*a,const char*b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static void event(unsigned long kind,unsigned long a,unsigned long b,unsigned long c){
 unsigned long n=tape[0];if(n>=9){failed=1;return;}
 unsigned long at=1+n*4;tape[at]=kind;tape[at+1]=a;tape[at+2]=b;tape[at+3]=c;tape[0]=n+1;
}
int interrupt_from_user(void*regs){
 if(regs!=active)failed=1;int user=(active->gpr.rsp>>63)==0;
 event(1,user,active->gpr.rsp,0);return user;
}
void set_cputime(enum set_cputime_mode mode){event(2,mode,0,0);}
int kprintf(const char*fmt,...){
 if(!same(fmt,"int3 exception (err: %lx, %lx:%lx)\n"))failed=1;
 __builtin_va_list ap;__builtin_va_start(ap,fmt);
 unsigned long error=__builtin_va_arg(ap,unsigned long),cs=__builtin_va_arg(ap,unsigned long),rip=__builtin_va_arg(ap,unsigned long);
 __builtin_va_end(ap);event(3,error,cs,rip);return inputs.ignored_kprintf_return;
}
void arch_show_interrupt_context(const void*regs){
 if(regs!=active)failed=1;event(4,1,0,0);
 if(inputs.rewrite_display_cs)active->gpr.cs=inputs.display_cs;
}
void set_signal(int sig,void*regs,struct siginfo*info){
 if(sig!=SIGTRAP||regs!=active||!info){failed=1;return;}
 /* Both producer bodies initialize every byte before this callback. Read only
  * this initialized signal object, never raw context padding or saved frames.
  * Build independent expected si_code bytes from the actual C int type. */
 const unsigned char*got=(const unsigned char*)info;
 int brkpt=TRAP_BRKPT;const unsigned char*code=(const unsigned char*)&brkpt;
 unsigned long off=__builtin_offsetof(struct siginfo,si_code);
 for(unsigned long i=0;i<sizeof(*info);i++){
  unsigned char want=(i>=off&&i<off+sizeof(brkpt))?code[i-off]:0;
  if(got[i]!=want)failed=1;
 }
 event(5,sig,regs==active,info->si_code);
 /* Allowed mutation inside the exclusive callback; no pointer escapes. */
 info->si_code=0x12345678;
}
void interrupt_exit(struct x86_user_context*regs){
 if(regs!=active)failed=1;event(6,1,0,0);
 if(inputs.rewrite_exit_rsp)active->gpr.rsp=inputs.exit_rsp;
}
void m14_int3_recorded_run(void(*entry)(struct x86_user_context*),const struct M14Int3Case*input,unsigned long out[M14_INT3_TAPE_WORDS]){
 struct x86_user_context regs;unsigned char*p=(unsigned char*)&regs;
 for(unsigned long i=0;i<sizeof(regs);i++)p[i]=0;
 for(unsigned i=0;i<M14_INT3_TAPE_WORDS;i++)tape[i]=0;
 failed=0;inputs=*input;regs.gpr.error=input->error;regs.gpr.cs=input->cs;regs.gpr.rip=input->rip;regs.gpr.rsp=input->rsp;
 active=&regs;entry(active);active=0;
 tape[M14_INT3_TAPE_WORDS-1]=failed;
 for(unsigned i=0;i<M14_INT3_TAPE_WORDS;i++)out[i]=tape[i];
}
int m14_int3_expected_tape(const unsigned long got[M14_INT3_TAPE_WORDS],const struct M14Int3Case*in){
 unsigned long want[M14_INT3_TAPE_WORDS];for(unsigned i=0;i<M14_INT3_TAPE_WORDS;i++)want[i]=0;
 unsigned n=0;
#define E(k,a,b,c) do{unsigned at=1+n*4;want[at]=(k);want[at+1]=(a);want[at+2]=(b);want[at+3]=(c);n++;}while(0)
 unsigned long user=(in->rsp>>63)==0;
 E(1,user,in->rsp,0);E(2,user?CPUTIME_MODE_U2K:CPUTIME_MODE_K2K_IN,0,0);
 if(x86_int3_debug_print_enabled){E(3,in->error,in->cs,in->rip);E(4,1,0,0);}
 E(5,SIGTRAP,1,TRAP_BRKPT);E(6,1,0,0);
 unsigned long after=in->rewrite_exit_rsp?in->exit_rsp:in->rsp,again=(after>>63)==0;
 E(1,again,after,0);E(2,again?CPUTIME_MODE_K2U:CPUTIME_MODE_K2K_OUT,0,0);
#undef E
 want[0]=n;for(unsigned i=0;i<M14_INT3_TAPE_WORDS;i++)if(got[i]!=want[i])return 1;
 return 0;
}
