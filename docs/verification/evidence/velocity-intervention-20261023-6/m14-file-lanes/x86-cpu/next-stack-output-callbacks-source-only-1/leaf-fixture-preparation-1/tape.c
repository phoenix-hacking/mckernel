/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Controlled full-signature endpoints only. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/next-exception-stop-batch-source-1/bounded-error-alias-correction-1/source/kernel/include/kmsg.h"
typedef __builtin_va_list VA;
extern int printf(const char*,...);
static int eq(const char*a,const char*b){while(*a&&*a==*b){++a;++b;}return *a==*b;}
extern void x86_stack_frame_log_bridge(unsigned long,unsigned long,unsigned long);
extern void x86_print_stack_bridge(void*,unsigned long);
static const unsigned long V[8]={0,1,0x7fffffffUL,0x80000000UL,0x100000000UL,0x8000000000000000UL,~0UL,0xffff880000000000UL};
struct tape {unsigned long a,b,c,first;void*p;unsigned log,stack,bad;};
static struct tape t;static int ret;
int kprintf(const char*f,...){VA a;t.log++;t.bad+=!eq(f,"IP: %016lx, SP: %016lx, FP: %016lx\n");__builtin_va_start(a,f);t.a=__builtin_va_arg(a,unsigned long);t.b=__builtin_va_arg(a,unsigned long);t.c=__builtin_va_arg(a,unsigned long);__builtin_va_end(a);return ret;}
void __print_stack(void*p,unsigned long v){t.stack++;t.p=p;t.first=v;}
#define x86_stack_frame_log_bridge original_log
#define x86_print_stack_bridge original_forward
#include "original_callbacks.inc"
#undef x86_stack_frame_log_bridge
#undef x86_print_stack_bridge
static int same(struct tape a,struct tape b){return a.a==b.a&&a.b==b.b&&a.c==b.c&&a.first==b.first&&a.p==b.p&&a.log==b.log&&a.stack==b.stack&&!a.bad&&!b.bad;}
int main(void){unsigned n=0,bad=0;int returns[5]={(-2147483647-1),-1,0,1,2147483647};
for(unsigned z=0;z<5;z++){ret=returns[z];for(unsigned a=0;a<8;a++)for(unsigned b=0;b<8;b++)for(unsigned c=0;c<8;c++){
t=(struct tape){0};original_log(V[a],V[b],V[c]);struct tape old=t;t=(struct tape){0};x86_stack_frame_log_bridge(V[a],V[b],V[c]);bad+=!same(old,t)||t.log!=1||t.stack!=0||t.a!=V[a]||t.b!=V[b]||t.c!=V[c];n++;}
for(unsigned p=0;p<8;p++)for(unsigned v=0;v<8;v++){t=(struct tape){0};original_forward((void*)V[p],V[v]);struct tape old=t;t=(struct tape){0};x86_print_stack_bridge((void*)V[p],V[v]);bad+=!same(old,t)||t.stack!=1||t.log!=0||t.p!=(void*)V[p]||t.first!=V[v];n++;}}
printf("M14 stack callbacks: pairs=%u failures=%u\n",n,bad);printf("NOTEXECUTED: actualFormatter kernelStack NMI NULLfreeze native\n");return bad?1:0;}
