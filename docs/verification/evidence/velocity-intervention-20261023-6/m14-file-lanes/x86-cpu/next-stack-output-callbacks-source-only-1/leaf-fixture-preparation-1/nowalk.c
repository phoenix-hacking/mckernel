/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Actual existing C/Rust provider, NoWalk only. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/next-exception-stop-batch-source-1/bounded-error-alias-correction-1/source/arch/x86_64/kernel/include/ihk/types.h"
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/next-exception-stop-batch-source-1/bounded-error-alias-correction-1/source/kernel/include/kmsg.h"
typedef __builtin_va_list VA;
extern int printf(const char*,...);
static int eq(const char*a,const char*b){while(*a&&*a==*b){++a;++b;}return *a==*b;}
extern void x86_stack_frame_log_bridge(unsigned long,unsigned long,unsigned long);
extern void x86_print_stack_bridge(void*,unsigned long);
static const unsigned long V[8]={0,1,0x7fffffffUL,0x80000000UL,0x100000000UL,0x8000000000000000UL,~0UL,0xffff880000000000UL};

struct ptape {unsigned calls,prints,bad;unsigned long cap[2],first;char output[4];};static struct ptape t;static int length;
int kprintf(const char*f,...){(void)f;t.bad++;return 0;}
int snprintf(char*p,size_t cap,const char*f,...){unsigned i=t.calls++;if(i>=2){t.bad++;return 0;}t.cap[i]=(unsigned long)cap;
if(i==0)t.bad+=!eq(f,"addr2line -e smp-x86/kernel/mckernel.img -fpia");else{VA a;t.bad+=!eq(f," %#16lx");__builtin_va_start(a,f);t.first=__builtin_va_arg(a,unsigned long);__builtin_va_end(a);}p[0]='x';p[1]=0;return length;}
int __kprintf(const char*f,...){VA a;t.prints++;t.bad+=!eq(f,"%s\n");__builtin_va_start(a,f);char*p=__builtin_va_arg(a,char*);t.output[0]=p[0];t.output[1]=p[1];__builtin_va_end(a);return -2147483647;}
struct stack {struct stack*rbp;unsigned long eip;};
#define STACK_BUF_LEN (1024-sizeof("[  0]: "))
#define __print_stack original_provider
#include "ORIGINAL-C-STACK-PROVIDER.inc"
#define x86_stack_frame_log_bridge unused_original_log
#define x86_print_stack_bridge original_forward
#include "original_callbacks.inc"
#undef __print_stack
#undef x86_stack_frame_log_bridge
#undef x86_print_stack_bridge
static int same(struct ptape a,struct ptape b){return a.calls==b.calls&&a.prints==b.prints&&a.cap[0]==b.cap[0]&&a.cap[1]==b.cap[1]&&a.first==b.first&&a.output[0]==b.output[0]&&a.output[1]==b.output[1]&&!a.bad&&!b.bad;}
int main(void){unsigned n=0,bad=0;const unsigned long ptr[4]={0,1,0x1000UL,0xffff880000000000UL};const int lens[3]={1,7,41};
for(unsigned p=0;p<4;p++)for(unsigned f=0;f<8;f++)for(unsigned l=0;l<3;l++){length=lens[l];t=(struct ptape){0};original_forward((void*)ptr[p],V[f]);struct ptape old=t;t=(struct ptape){0};x86_print_stack_bridge((void*)ptr[p],V[f]);bad+=!same(old,t)||t.calls!=(V[f]?2:1)||t.prints!=1||t.cap[0]!=1017UL||(V[f]&&(t.cap[1]!=1017UL-(unsigned long)length||t.first!=V[f]));n++;}
printf("M14 actual stack provider NoWalk: pairs=%u failures=%u\n",n,bad);printf("NOTEXECUTED: kernelStackWalk IRQ NMI NULLfreeze native\n");return bad?1:0;}
