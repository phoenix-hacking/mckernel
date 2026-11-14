/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <stdarg.h>
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
typedef void(*Log)(int,unsigned long,unsigned long,unsigned long,unsigned long);
struct event{unsigned provider,depth,nargs;unsigned long args[4];char format[96];};
struct trace{unsigned n;struct event events[16];};
static struct trace *active;static unsigned depth,eval[5];static int return_value,mode;static unsigned long lock_flags;
static void need(int b,const char*s){if(!b){fprintf(stderr,"FAIL %s\n",s);exit(1);}}
static struct event* next(unsigned p){need(active&&active->n<16,"bounded synchronous tape");struct event*e=&active->events[active->n++];e->provider=p;e->depth=depth;return e;}
static int record(unsigned p,const char*fmt,va_list ap){
 struct event*e=next(p);unsigned i=0;for(;fmt[i];i++){need(i+1<96,"bounded exact format");e->format[i]=fmt[i];}e->format[i]=0;
 for(i=0;fmt[i];i++)if(fmt[i]=='%'){i++;while(fmt[i]>='0'&&fmt[i]<='9')i++;need(fmt[i]=='l'&&fmt[i+1]=='x',"exact unsigned-long conversion");need(e->nargs<4,"at most four arguments");e->args[e->nargs++]=va_arg(ap,unsigned long);i++;}
 if(mode==1)need(p==1&&depth==1,"interrupt context uses unlocked print within outer lock");
 if(mode==0)need(p==2&&depth==0,"user context uses ordinary print without outer lock");
 return return_value;
}
int __kprintf(const char*f,...){va_list ap;va_start(ap,f);int r=record(1,f,ap);va_end(ap);return r;}
int kprintf(const char*f,...){va_list ap;va_start(ap,f);int r=record(2,f,ap);va_end(ap);return r;}
#include "original-body.inc"
extern void x86_context_line_log_bridge(int,unsigned long,unsigned long,unsigned long,unsigned long);
extern int fixture_run_context(int,const unsigned long*,Log,unsigned long(*)(void),void(*)(unsigned long));
static unsigned long lock_spy(void){need(depth==0,"outer lock enters once");next(3);depth++;return lock_flags;}
static void unlock_spy(unsigned long f){need(depth==1&&f==lock_flags,"outer unlock exact saved flags");struct event*e=next(4);e->nargs=1;e->args[0]=f;depth--;}
static int evarg(int e){eval[0]++;return e;}
static unsigned long arg(unsigned i,unsigned long v){eval[i]++;return v;}
static int same(const char*a,const char*b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static void compare(struct trace*a,struct trace*b){
 need(a->n==b->n,"exact call count");for(unsigned i=0;i<a->n;i++){struct event*x=&a->events[i],*y=&b->events[i];need(x->provider==y->provider&&x->depth==y->depth&&x->nargs==y->nargs&&same(x->format,y->format),"exact provider/order/depth/format/vararg count");for(unsigned j=0;j<x->nargs;j++)need(x->args[j]==y->args[j],"full-width ordered vararg bits");}
}
static void direct(Log fn,int e,unsigned long*a,struct trace*t){
 active=t;depth=0;mode=-1;for(unsigned i=0;i<5;i++)eval[i]=0;
 fn(evarg(e),arg(1,a[0]),arg(2,a[1]),arg(3,a[2]),arg(4,a[3]));
 for(unsigned i=0;i<5;i++){need(eval[i]==1,"five caller arguments evaluate once");}
 need(depth==0,"logger does not change lock depth");active=NULL;
}
static void context(Log fn,int which,unsigned long*a,struct trace*t){
 active=t;depth=0;mode=which;int r=fixture_run_context(which,a,fn,lock_spy,unlock_spy);need(r==0&&depth==0,"actual context body completes and unlocks");
 if(which==0)need(t->n==3,"three user context prints");
 else {need(t->n==13&&t->events[0].provider==3&&t->events[12].provider==4,"one outer span brackets eleven prints");}
 active=NULL;
}
int main(void){
 _Static_assert(sizeof(int)==4&&sizeof(unsigned long)==8&&sizeof(void*)==8,"real x86_64 widths");
 unsigned long values[136]={0,1,~0UL,1UL<<63,(1UL<<63)-1,0xaaaaaaaaaaaaaaaaUL,0x5555555555555555UL,0x0123456789abcdefUL};unsigned n=8;
 for(unsigned b=0;b<64;b++){values[n++]=1UL<<b;values[n++]=~(1UL<<b);}need(n==136,"136 long boundaries");
 const int events[]={INT_MIN,-1,0,1,2,3,4,5,6,7,19,20,21,22,23,INT_MAX};
 const int returns[]={INT_MIN,-1,0,1,INT_MAX};unsigned directpairs=0,contextpairs=0;
 for(unsigned i=0;i<n;i++)for(unsigned r=0;r<5;r++){
  unsigned long args[21];for(unsigned j=0;j<21;j++)args[j]=values[(i+j)%n];return_value=returns[r];lock_flags=values[i];
  for(unsigned e=0;e<16;e++){
   struct trace a={0},b={0};direct(original_context_log,events[e],args,&a);direct(x86_context_line_log_bridge,events[e],args,&b);compare(&a,&b);
   unsigned expected=(events[e]>=2&&events[e]<=6)?2:((events[e]==1||events[e]==20||events[e]==21||events[e]==22)?1:0);need(a.n==expected,"all nine defined events and unknown no-op");directpairs++;
  }
  for(int which=0;which<2;which++){struct trace a={0},b={0};context(original_context_log,which,args,&a);context(x86_context_line_log_bridge,which,args,&b);compare(&a,&b);contextpairs++;}
 }
 need(directpairs==10880&&contextpairs==1360,"exact finite pair coverage");
 printf("PASS actual_C_Rust_context_logger_direct_pairs=%u actual_Rust_caller_lock_span_pairs=%u total=12240 exact_events=9 provider_channels=2 return_values=5\n",directpairs,contextpairs);return 0;
}
