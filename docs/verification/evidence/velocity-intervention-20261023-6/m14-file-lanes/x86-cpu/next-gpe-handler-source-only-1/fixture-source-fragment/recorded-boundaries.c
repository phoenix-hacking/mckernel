/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE FRAGMENT ONLY. No main/driver/argv/fixture queue.
 * Future host fixture starts one ordinary child per side/case, supplies this
 * terminal entry, reads initialized scalar words, and waits for exact exit0.
 * No native panic, IRQ, signal delivery, schedule, or exception instruction.
 */
#include <ihk/context.h>
#include <signal.h>
#include <process.h>
#include <syscall.h>
#include <ihk/debug.h>
extern long fixture_host_write(int,const void*,unsigned long) __asm__("write");
extern void fixture_host_exit(int) __asm__("_exit") __attribute__((noreturn));
struct M14GpeCase {
 unsigned long error,cs,rip,rsp,display_cs,exit_rsp;
 unsigned rewrite_display_cs,rewrite_exit_rsp;
 int ignored_kprintf_return;
};
enum { M14_GPE_TAPE_WORDS=48 };
static unsigned long record[M14_GPE_TAPE_WORDS];
static struct x86_user_context*active;
static struct M14GpeCase inputs;
static int report_fd;
static unsigned failed;
static int same(const char*a,const char*b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static void event(unsigned long kind,unsigned long a,unsigned long b,unsigned long c){
 unsigned long n=record[0];if(n>=11){failed=1;return;}
 unsigned long at=1+n*4;record[at]=kind;record[at+1]=a;record[at+2]=b;record[at+3]=c;record[0]=n+1;
}
int interrupt_from_user(void*regs){
 if(regs!=active)failed=1;
 int user=(active->gpr.rsp>>63)==0;event(1,user,active->gpr.rsp,0);return user;
}
void set_cputime(enum set_cputime_mode mode){event(2,(unsigned long)mode,0,0);}
int kprintf(const char*fmt,...){
 if(!same(fmt,"General protection fault (err: %lx, %lx:%lx)\n"))failed=1;
 __builtin_va_list ap;__builtin_va_start(ap,fmt);
 unsigned long err=__builtin_va_arg(ap,unsigned long),cs=__builtin_va_arg(ap,unsigned long),rip=__builtin_va_arg(ap,unsigned long);
 __builtin_va_end(ap);event(3,err,cs,rip);return inputs.ignored_kprintf_return;
}
void arch_show_interrupt_context(const void*regs){
 if(regs!=active)failed=1;event(4,1,0,0);
 if(inputs.rewrite_display_cs)active->gpr.cs=inputs.display_cs;
}
void set_signal(int sig,void*regs,struct siginfo*info){
 if(regs!=active||info!=0||sig!=SIGSEGV)failed=1;event(5,sig,regs==active,info==0);
}
void interrupt_exit(struct x86_user_context*regs){
 if(regs!=active)failed=1;event(6,1,0,0);
 if(inputs.rewrite_exit_rsp)active->gpr.rsp=inputs.exit_rsp;
}
__attribute__((noreturn)) void panic(const char*message){
 unsigned long code=same(message,"gpe_handler")?1:same(message,"GPF")?2:0;
 if(!code)failed=1;event(7,code,0,0);record[M14_GPE_TAPE_WORDS-1]=failed;
 long bytes=fixture_host_write(report_fd,record,sizeof(record));
 fixture_host_exit(bytes==(long)sizeof(record)&&!failed?0:97);
}
void m14_gpe_recorded_child(void(*entry)(struct x86_user_context*),int fd,const struct M14GpeCase*input){
 struct x86_user_context regs;unsigned char*p=(unsigned char*)&regs;
 for(unsigned long i=0;i<sizeof(regs);i++)p[i]=0;
 for(unsigned i=0;i<M14_GPE_TAPE_WORDS;i++)record[i]=0;
 failed=0;report_fd=fd;inputs=*input;
 regs.gpr.error=input->error;regs.gpr.cs=input->cs;regs.gpr.rip=input->rip;regs.gpr.rsp=input->rsp;
 active=&regs;entry(active);
 /* Both genuine selected paths terminate at the existing panic provider. */
 fixture_host_exit(98);
}
int m14_gpe_expected_tape(const unsigned long actual[M14_GPE_TAPE_WORDS],const struct M14GpeCase*in){
 unsigned long want[M14_GPE_TAPE_WORDS];for(unsigned i=0;i<M14_GPE_TAPE_WORDS;i++)want[i]=0;
 unsigned n=0;
#define E(k,a,b,c) do{unsigned at=1+n*4;want[at]=(k);want[at+1]=(a);want[at+2]=(b);want[at+3]=(c);n++;}while(0)
 unsigned long user=(in->rsp>>63)==0;
 E(1,user,in->rsp,0);E(2,user?CPUTIME_MODE_U2K:CPUTIME_MODE_K2K_IN,0,0);
 E(3,in->error,in->cs,in->rip);E(4,1,0,0);
 unsigned long after_cs=in->rewrite_display_cs?in->display_cs:in->cs;
 if((after_cs&3)==0){E(7,1,0,0);}
 else{
  E(5,SIGSEGV,1,1);E(6,1,0,0);
  unsigned long rsp=in->rewrite_exit_rsp?in->exit_rsp:in->rsp,again=(rsp>>63)==0;
  E(1,again,rsp,0);E(2,again?CPUTIME_MODE_K2U:CPUTIME_MODE_K2K_OUT,0,0);E(7,2,0,0);
 }
#undef E
 want[0]=n;for(unsigned i=0;i<M14_GPE_TAPE_WORDS;i++)if(actual[i]!=want[i])return 1;
 return 0;
}
