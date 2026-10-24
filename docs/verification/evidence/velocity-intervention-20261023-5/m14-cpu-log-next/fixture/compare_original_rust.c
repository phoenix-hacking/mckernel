/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <stdarg.h>
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
struct tape { unsigned calls,kind; unsigned long value; char format[96]; };
static struct tape *active;
static int printf_result;
static unsigned event_evaluations,value_evaluations;
static void need(int ok,const char *what){if(!ok){fprintf(stderr,"FAIL %s\n",what);exit(1);}}
int kprintf(const char *format,...){
 need(active!=NULL,"live synchronous tape");active->calls++;
 unsigned i=0;for(;format[i];i++){need(i+1<sizeof(active->format),"bounded format");active->format[i]=format[i];}
 active->format[i]=0;
 va_list ap;va_start(ap,format);unsigned conversions=0;
 for(i=0;format[i];i++)if(format[i]=='%'){
  conversions++;
  if(format[i+1]=='p'){active->kind=2;active->value=(unsigned long)(uintptr_t)va_arg(ap,void*);i++;}
  else {need(format[i+1]=='l'&&(format[i+2]=='x'||format[i+2]=='u'),"exact long conversion");active->kind=1;active->value=va_arg(ap,unsigned long);i+=2;}
 }
 va_end(ap);need(conversions==1,"one typed variadic argument");return printf_result;
}
#include "original-body.inc"
extern void x86_cpu_ulong_log_bridge(int,unsigned long);
static int event_arg(int e){event_evaluations++;return e;}
static unsigned long value_arg(unsigned long v){value_evaluations++;return v;}
static void run(void(*fn)(int,unsigned long),int e,unsigned long v,struct tape *t){
 active=t;event_evaluations=value_evaluations=0;fn(event_arg(e),value_arg(v));
 need(event_evaluations==1&&value_evaluations==1,"arguments evaluated exactly once");active=NULL;
}
static int same(const char*a,const char*b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
int main(void){
 _Static_assert(sizeof(int)==4&&sizeof(unsigned long)==8&&sizeof(void*)==8,"actual x86_64 variadic widths");
 unsigned long v[136]={0,1,~0UL,1UL<<63,(1UL<<63)-1,0xaaaaaaaaaaaaaaaaUL,0x5555555555555555UL,0x0123456789abcdefUL};
 unsigned n=8;for(unsigned b=0;b<64;b++){v[n++]=1UL<<b;v[n++]=~(1UL<<b);}need(n==136,"136 boundary long values");
 const int events[]={INT_MIN,-1,0,1,2,3,14,15,16,INT_MAX};
 const int returns[]={INT_MIN,-1,0,1,INT_MAX};unsigned pairs=0,printed=0,noops=0;
 for(unsigned e=0;e<sizeof(events)/sizeof(events[0]);e++)for(unsigned i=0;i<n;i++)for(unsigned r=0;r<sizeof(returns)/sizeof(returns[0]);r++){
  struct tape a={0},b={0};printf_result=returns[r];
  run(original_x86_cpu_ulong_log_bridge,events[e],v[i],&a);run(x86_cpu_ulong_log_bridge,events[e],v[i],&b);
  need(a.calls==b.calls&&a.kind==b.kind&&a.value==b.value&&same(a.format,b.format),"original C versus actual Rust complete variadic tape");
  if(events[e]==1||events[e]==2||events[e]==15){
   need(a.calls==1&&a.value==v[i],"one print with unchanged long bits");
   need(a.kind==(events[e]==15?2U:1U),"pointer case versus unsigned long case");
   if(events[e]==1)need(same(a.format,"Trampoline area: 0x%lx \n"),"trailing space and newline");
   if(events[e]==2)need(same(a.format,"# of cpus : %lu\n"),"decimal format exact");
   if(events[e]==15)need(same(a.format,"arch_save_panic_regs: in user-space: %p\n"),"pointer format exact");
   printed++;
  }else{need(a.calls==0,"unknown event no print");noops++;}
  pairs++;
 }
 need(pairs==6800&&printed==2040&&noops==4760,"finite planned coverage");
 printf("PASS original_C_actual_Rust_ulong_log_pairs=%u printed=%u unknown_noops=%u values=136 events=10 kprintf_returns=5 exact_formats=3\n",pairs,printed,noops);
 return 0;
}
