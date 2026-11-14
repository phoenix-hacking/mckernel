/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Hosted controlled providers only: no DR6, HLT, exception, IRQ or IRET execution.
 */
#include <ihk/context.h>
#include <registers.h>
#include <signal.h>
#include <process.h>
#include <syscall.h>
#include <ihk/debug.h>
#undef memset
extern void *memset(void *, int, unsigned long);
extern int printf(const char *, ...);
extern long host_read(int,void*,unsigned long) __asm__("read");
extern long host_write(int,const void*,unsigned long) __asm__("write");
extern int host_pipe(int[2]) __asm__("pipe");
extern int host_fork(void) __asm__("fork");
extern int host_close(int) __asm__("close");
extern int host_waitpid(int,int*,int) __asm__("waitpid");
extern void host_exit(int) __asm__("_exit") __attribute__((noreturn));

#ifdef DEBUG_PRINT_CPU
const unsigned int x86_int3_debug_print_enabled=1;
const unsigned int x86_debug_handler_debug_print_enabled=1;
#else
const unsigned int x86_int3_debug_print_enabled=0;
const unsigned int x86_debug_handler_debug_print_enabled=0;
#endif

enum { WORDS=64, GPE=1, INT3=2, DEBUG=3, STOP=4 };
struct Input { unsigned long error,cs,rip,rsp,flags,display_cs,exit_rsp,dr6;
               unsigned display_mutate,exit_mutate; int print_result; };
struct Report { unsigned long tape[WORDS]; struct x86_user_context frame; };
static struct Report report;
static struct Input input;
static struct x86_user_context *active;
static unsigned kind,failed,dr6_calls,stop_calls,stop_limit;
static int report_fd;
static unsigned failures;
static void require(int ok){if(!ok)failures++;}
static int same(const char*a,const char*b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static void event(unsigned long k,unsigned long a,unsigned long b,unsigned long c){
 unsigned long n=report.tape[0];if(n>=14){failed=1;return;}
 unsigned long at=1+n*4;report.tape[at]=k;report.tape[at+1]=a;
 report.tape[at+2]=b;report.tape[at+3]=c;report.tape[0]=n+1;
}
int interrupt_from_user(void *frame){
 if(frame!=active)failed=1;
 int user=(active->gpr.rsp>>63)==0;event(1,user,active->gpr.rsp,0);return user;
}
void set_cputime(enum set_cputime_mode mode){event(2,mode,0,0);}
int kprintf(const char *fmt,...){
 const char*want=kind==GPE?"General protection fault (err: %lx, %lx:%lx)\n":
                 kind==INT3?"int3 exception (err: %lx, %lx:%lx)\n":
                            "debug exception (err: %lx, %lx:%lx)\n";
 if(!same(fmt,want))failed=1;
 __builtin_va_list ap;__builtin_va_start(ap,fmt);
 unsigned long e=__builtin_va_arg(ap,unsigned long),c=__builtin_va_arg(ap,unsigned long),r=__builtin_va_arg(ap,unsigned long);
 __builtin_va_end(ap);event(3,e,c,r);return input.print_result;
}
void arch_show_interrupt_context(const void *frame){
 if(frame!=active)failed=1;event(4,1,0,0);
 if(input.display_mutate)active->gpr.cs=input.display_cs;
}
unsigned long fixture_debug_register_read(int reg){
 if(kind!=DEBUG||reg!=6||dr6_calls++)failed=1;
 event(8,reg,input.dr6,active->gpr.rflags);return input.dr6;
}
static int expected_code(void){
 if(kind==INT3)return TRAP_BRKPT;
 if(input.dr6&DB6_BS)return TRAP_TRACE;
 return input.dr6&(DB6_B0|DB6_B1|DB6_B2|DB6_B3)?TRAP_HWBKPT:0;
}
void set_signal(int sig,void *frame,struct siginfo *info){
 if(frame!=active)failed=1;
 if(kind==GPE){if(sig!=SIGSEGV||info)failed=1;event(5,sig,info==0,0);return;}
 if(sig!=SIGTRAP||!info){failed=1;return;}
 int code=expected_code();const unsigned char *b=(const unsigned char*)&code;
 const unsigned char *got=(const unsigned char*)info;
 unsigned long off=__builtin_offsetof(struct siginfo,si_code);
 for(unsigned long i=0;i<sizeof(*info);i++){
  unsigned char want=(i>=off&&i<off+sizeof(code))?b[i-off]:0;
  if(got[i]!=want)failed=1;
 }
 if(kind==DEBUG && (dr6_calls!=1 || active->gpr.rflags!=(input.dr6&DB6_BS?input.flags&~(unsigned long)RFLAGS_TF:input.flags)))failed=1;
 event(5,sig,0,info->si_code);info->si_code=0x12345678;
}
void interrupt_exit(struct x86_user_context *frame){
 if(frame!=active)failed=1;event(6,1,0,0);
 if(input.exit_mutate)active->gpr.rsp=input.exit_rsp;
}
static void terminal_report(void){
 report.tape[WORDS-1]=failed;
 long bytes=host_write(report_fd,&report,sizeof(report));
 host_exit(bytes==(long)sizeof(report)&&!failed?0:97);
}
__attribute__((noreturn)) void panic(const char *message){
 unsigned code=same(message,"gpe_handler")?1:same(message,"GPF")?2:0;
 if(kind!=GPE||!code)failed=1;event(7,code,0,0);terminal_report();
 __builtin_unreachable();
}
void cpu_halt(void){
 if(kind!=STOP||!stop_limit)host_exit(96);
 stop_calls++;
 if(stop_calls==stop_limit){report.tape[0]=stop_calls;terminal_report();}
}

#define gpe_handler original_gpe_handler
#include "original-gpe.inc"
#undef gpe_handler
#define int3_handler original_int3_handler
#include "original-int3.inc"
#undef int3_handler
#include "original-debug-controlled.inc"
#define arch_cpu_stop original_arch_cpu_stop
#include "original-stop.inc"
#undef arch_cpu_stop
extern void gpe_handler(struct x86_user_context*),int3_handler(struct x86_user_context*);
extern void actual_debug_controlled(struct x86_user_context*),arch_cpu_stop(void);
extern const unsigned long M14_C_GPE_ABI[11],M14_RUST_GPE_ABI[11];
extern const unsigned long M14_C_INT3_ABI[13],M14_RUST_INT3_ABI[13];
extern const unsigned long M14_C_DEBUG_ABI[10],M14_RUST_DEBUG_ABI[10];

static void setup(unsigned mode,const struct Input *in){
 kind=mode;input=*in;failed=dr6_calls=stop_calls=0;
 unsigned char*p=(unsigned char*)&report;
 for(unsigned long i=0;i<sizeof(report);i++)p[i]=0;
 p=(unsigned char*)&report.frame;
 for(unsigned long i=0;i<sizeof(report.frame);i++)p[i]=(unsigned char)(i*37+19);
 active=&report.frame;active->gpr.error=in->error;active->gpr.cs=in->cs;
 active->gpr.rip=in->rip;active->gpr.rsp=in->rsp;active->gpr.rflags=in->flags;
}
static struct Report run(void(*fn)(struct x86_user_context*),unsigned mode,const struct Input *in){
 setup(mode,in);fn(active);report.tape[WORDS-1]=failed;active=0;return report;
}
static struct Report child_run(void(*framefn)(struct x86_user_context*),void(*stopfn)(void),unsigned mode,const struct Input *in,unsigned limit){
 struct Report result;unsigned char*z=(unsigned char*)&result;
 for(unsigned long i=0;i<sizeof(result);i++)z[i]=0;
 int fds[2];if(host_pipe(fds)!=0){failures++;return result;}
 int pid=host_fork();
 if(pid==0){host_close(fds[0]);setup(mode,in);report_fd=fds[1];stop_limit=limit;
  if(mode==STOP)stopfn();else framefn(active);host_exit(98);}
 host_close(fds[1]);if(pid<0){host_close(fds[0]);failures++;return result;}
 unsigned long have=0;
 while(have<sizeof(result)){long n=host_read(fds[0],z+have,sizeof(result)-have);if(n<=0)break;have+=(unsigned long)n;}
 unsigned char extra;long tail=host_read(fds[0],&extra,1);host_close(fds[0]);
 int status=-1;int waited=host_waitpid(pid,&status,0);
 require(have==sizeof(result)&&tail==0&&waited==pid&&status==0);return result;
}
static struct Report expected(unsigned mode,const struct Input *in,unsigned limit){
 setup(mode,in);struct Report want=report;
 unsigned long *t=want.tape;unsigned n=0;
#define E(k,a,b,c) do{unsigned at=1+n*4;t[at]=(k);t[at+1]=(a);t[at+2]=(b);t[at+3]=(c);n++;}while(0)
 if(mode==STOP){t[0]=limit;return want;}
 unsigned long user=(in->rsp>>63)==0;
 E(1,user,in->rsp,0);E(2,user?CPUTIME_MODE_U2K:CPUTIME_MODE_K2K_IN,0,0);
 if(mode==GPE||x86_int3_debug_print_enabled){
  E(3,in->error,in->cs,in->rip);E(4,1,0,0);
  if(in->display_mutate)want.frame.gpr.cs=in->display_cs;
 }
 if(mode==GPE&&(want.frame.gpr.cs&3)==0){E(7,1,0,0);}
 else{
  int code=mode==INT3?TRAP_BRKPT:mode==DEBUG?(in->dr6&DB6_BS?TRAP_TRACE:in->dr6&15?TRAP_HWBKPT:0):0;
  if(mode==DEBUG){E(8,6,in->dr6,in->flags);if(in->dr6&DB6_BS)want.frame.gpr.rflags&=~(unsigned long)RFLAGS_TF;}
  E(5,mode==GPE?SIGSEGV:SIGTRAP,mode==GPE,code);E(6,1,0,0);
  if(in->exit_mutate)want.frame.gpr.rsp=in->exit_rsp;
  unsigned long again=(want.frame.gpr.rsp>>63)==0;
  E(1,again,want.frame.gpr.rsp,0);E(2,again?CPUTIME_MODE_K2U:CPUTIME_MODE_K2K_OUT,0,0);
  if(mode==GPE){E(7,2,0,0);}
 }
#undef E
 t[0]=n;return want;
}
static void compare(const struct Report *a,const struct Report *b,const struct Report *want){
 const unsigned char*x=(const unsigned char*)a,*y=(const unsigned char*)b,*z=(const unsigned char*)want;
 for(unsigned long i=0;i<sizeof(*a);i++)if(x[i]!=y[i]||x[i]!=z[i]){failures++;return;}
}
static unsigned long cases(unsigned mode){
 unsigned long pairs=0,values[3]={0,1,~0UL},rsps[4]={0,1,1UL<<63,~0UL};
 int returns[3]={0,0x7fffffff,(-0x7fffffff-1)};
 unsigned long states[14]={0,DB6_BD,DB6_BT,1UL<<63,DB6_B0,DB6_B1,DB6_B2,DB6_B3,15,DB6_BS,DB6_BS|DB6_B0,~0UL,DB6_BS,DB6_BS};
 unsigned outer=mode==DEBUG?14:3,cs_count=mode==DEBUG?1:4,rsp_count=mode==GPE?2:4;
 for(unsigned v=0;v<outer;v++)for(unsigned c=0;c<cs_count;c++)for(unsigned r=0;r<rsp_count;r++)
 for(unsigned display=0;display<2;display++)for(unsigned exit=0;exit<2;exit++)for(unsigned ret=0;ret<3;ret++){
  struct Input in={.error=mode==DEBUG?values[v%3]:values[v],.cs=c,.rip=~values[v%3],.rsp=mode==GPE?rsps[r*2]:rsps[r],
    .flags=mode==DEBUG&&v==12?0:mode==DEBUG&&v==13?0x8000000000000100UL:~0UL,
    .display_cs=(c&3)?0:3,.exit_rsp=~(mode==GPE?rsps[r*2]:rsps[r]),.dr6=states[v%14],
    .display_mutate=display,.exit_mutate=exit,.print_result=returns[ret]};
  struct Report a,b,w=expected(mode,&in,0);
  if(mode==GPE){a=child_run(original_gpe_handler,0,mode,&in,0);b=child_run(gpe_handler,0,mode,&in,0);}
  else if(mode==INT3){a=run(original_int3_handler,mode,&in);b=run(int3_handler,mode,&in);}
  else{a=run(original_debug_controlled,mode,&in);b=run(actual_debug_controlled,mode,&in);}
  compare(&a,&b,&w);pairs++;
 }
 return pairs;
}
int main(void){
 unsigned ABI=0;
 for(unsigned i=0;i<11;i++){require(M14_C_GPE_ABI[i]==M14_RUST_GPE_ABI[i]);ABI++;}
 for(unsigned i=0;i<13;i++){require(M14_C_INT3_ABI[i]==M14_RUST_INT3_ABI[i]);ABI++;}
 for(unsigned i=0;i<10;i++){require(M14_C_DEBUG_ABI[i]==M14_RUST_DEBUG_ABI[i]);ABI++;}
 unsigned long g=cases(GPE),i=cases(INT3),d=cases(DEBUG),stop=0;
 unsigned limits[5]={1,2,3,17,257};struct Input input={0};
 for(unsigned n=0;n<5;n++){struct Report w=expected(STOP,&input,limits[n]);
  struct Report a=child_run(0,original_arch_cpu_stop,STOP,&input,limits[n]);
  struct Report b=child_run(0,arch_cpu_stop,STOP,&input,limits[n]);compare(&a,&b,&w);stop++;}
 printf("M14 CPU exception/stop batch: gate=%u GPE=%lu INT3=%lu DEBUG=%lu STOP=%lu ABI=%u failures=%u\n",x86_int3_debug_print_enabled,g,i,d,stop,ABI,failures);
 printf("NOTEXECUTED: rawDR6 HLT exception IRQ IRET NULLfreeze native\n");
 return failures?1:0;
}
