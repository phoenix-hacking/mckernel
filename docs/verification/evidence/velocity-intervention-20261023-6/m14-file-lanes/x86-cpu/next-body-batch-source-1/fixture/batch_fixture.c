/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * No privileged instruction or NMI raw-body function is invoked by main.
 * Stack coverage is actual low-address/no-walk paths only.
 */
#include <ihk/context.h>
extern int printf(const char*,...);
extern int vsnprintf(char*,unsigned long,const char*,__builtin_va_list);
extern void original_print_stack(void*,unsigned long),__print_stack(void*,unsigned long);
extern void original_interrupt_exit(struct x86_user_context*),interrupt_exit(struct x86_user_context*);
extern int actual_interrupt_classifier(void*);
extern int m14_nmi_pure_body_fixture(unsigned long*);
extern const unsigned long M14_C_NMI_HEADER_ABI[12],M14_RUST_NMI_HEADER_ABI[12];
extern const unsigned long M14_C_BATCH_WORD_ABI[7],M14_RUST_BATCH_WORD_ABI[7];
static unsigned failures;
static void require(int ok){if(!ok)failures++;}
static unsigned long patterns[136];
static unsigned make_patterns(void){
 unsigned n=0;unsigned long prefix[8]={0,1,~0UL,1UL<<63,(1UL<<63)-1,0x200,0x202,0x246};
 for(unsigned i=0;i<8;i++)patterns[n++]=prefix[i];
 for(unsigned b=0;b<64;b++){patterns[n++]=1UL<<b;patterns[n++]=~(1UL<<b);}return n;
}
static unsigned length(const char*s){unsigned n=0;while(s[n])n++;return n;}
static void copy(char*d,const char*s){do{*d++=*s;}while(*s++);}
static int equal(const char*a,const char*b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
struct StackCall{unsigned event;unsigned long capacity,offset,value;int returned;};
struct StackTape{struct StackCall calls[4];unsigned count;char line[1100];};
static struct StackTape tape;
static char*stackbase;
static int print_return;
int fixture_stack_snprintf(char*dst,unsigned long cap,const char*fmt,...){
 __builtin_va_list ap;__builtin_va_start(ap,fmt);
 require(tape.count<3);
 struct StackCall*c=&tape.calls[tape.count++];
 c->event=1;c->capacity=cap;c->value=0;
 if(tape.count==1){stackbase=dst;require(equal(fmt,"addr2line -e smp-x86/kernel/mckernel.img -fpia"));}
 else{
  require(equal(fmt," %#16lx"));__builtin_va_list peek;__builtin_va_copy(peek,ap);
  c->value=__builtin_va_arg(peek,unsigned long);__builtin_va_end(peek);
 }
 c->offset=(unsigned long)(dst-stackbase);
 int ret=vsnprintf(dst,cap,fmt,ap);__builtin_va_end(ap);c->returned=ret;
 require(ret>=0&&(unsigned long)ret<cap);return ret;
}
int fixture_stack_print(const char*fmt,...){
 __builtin_va_list ap;__builtin_va_start(ap,fmt);require(equal(fmt,"%s\n"));
 const char*line=__builtin_va_arg(ap,const char*);require(line==stackbase);
 require(length(line)<sizeof(tape.line));copy(tape.line,line);__builtin_va_end(ap);
 require(tape.count<4);struct StackCall*c=&tape.calls[tape.count++];
 c->event=2;c->capacity=0;c->offset=0;c->value=0;c->returned=print_return;return print_return;
}
static struct StackTape run_stack(void(*fn)(void*,unsigned long),void*rbp,unsigned long first){
 tape=(struct StackTape){0};stackbase=0;fn(rbp,first);
 require(tape.count==(first?3U:2U));require(tape.calls[0].capacity==1016&&tape.calls[0].offset==0);
 if(first){require(tape.calls[1].value==first);require(tape.calls[1].offset==(unsigned long)tape.calls[0].returned);
  require(tape.calls[1].capacity==1016-(unsigned long)tape.calls[0].returned);}
 return tape;
}
static unsigned long stack_fixture(unsigned n){
 int returns[5]={0,1,-1,0x7fffffff,(-0x7fffffff-1)};unsigned long pairs=0;
 unsigned long ordinary_frame[2]={0,0xfeedfacecafebeefUL};
 for(unsigned i=0;i<n;i++)for(unsigned r=0;r<5;r++)for(unsigned p=0;p<2;p++){
  void*frame=p?(void*)ordinary_frame:0;require((unsigned long)frame<=0xffff880000000000UL);
  print_return=returns[r];struct StackTape a=run_stack(original_print_stack,frame,patterns[i]);
  struct StackTape b=run_stack(__print_stack,frame,patterns[i]);
  require(a.count==b.count&&equal(a.line,b.line));
  for(unsigned j=0;j<a.count;j++){
   require(a.calls[j].event==b.calls[j].event&&a.calls[j].capacity==b.calls[j].capacity);
   require(a.calls[j].offset==b.calls[j].offset&&a.calls[j].value==b.calls[j].value&&a.calls[j].returned==b.calls[j].returned);
  }pairs++;
 }return pairs;
}
struct ExitCall{unsigned event;unsigned long arg,rax;int number;};
struct ExitTape{struct ExitCall calls[5];unsigned count;};
static struct ExitTape et;
static struct x86_user_context *active;
static int forced_classifier;
static unsigned mutate;
static void step(unsigned event){
 require(et.count<5);et.calls[et.count++]=(struct ExitCall){event,0,active->gpr.rax,0};
}
int interrupt_from_user(void*regs){require(regs==active);step(1);return forced_classifier;}
void cpu_enable_interrupt(void){require(et.count==1);step(2);}
void check_sig_pending(void){
 require(et.count==2);step(3);if(mutate)active->gpr.rax^=0xdeadbeef01234567UL;
}
void check_need_resched(void){
 require(et.count==3);step(4);if(mutate)active->gpr.rax+=0x1020304050607080UL;
}
void check_signal(unsigned long rc,void*regs,int num){
 require(et.count==4&&rc==0&&regs==active&&num==-1);step(5);
 et.calls[4].arg=rc;et.calls[4].number=num;
}
static struct ExitTape run_exit(void(*fn)(struct x86_user_context*),struct x86_user_context*regs){
 active=regs;et=(struct ExitTape){0};fn(regs);require(et.count==(forced_classifier?5U:1U));
 for(unsigned i=0;i<et.count;i++)require(et.calls[i].event==i+1);
 active=0;return et;
}
static void init_context(struct x86_user_context*r,unsigned seed){
 unsigned char*p=(unsigned char*)r;for(unsigned long i=0;i<sizeof(*r);i++)p[i]=(unsigned char)(i*37+seed*53);
}
static unsigned long exit_fixture(void){
 const int states[7]={0,1,-1,2,-2,0x7fffffff,(-0x7fffffff-1)};unsigned long pairs=0;
 for(unsigned s=0;s<7;s++)for(unsigned seed=0;seed<8;seed++)for(unsigned m=0;m<2;m++){
  struct x86_user_context a,b;init_context(&a,seed);init_context(&b,seed);forced_classifier=states[s];mutate=m;
  struct ExitTape x=run_exit(original_interrupt_exit,&a),y=run_exit(interrupt_exit,&b);
  require(x.count==y.count);for(unsigned i=0;i<x.count;i++)require(x.calls[i].event==y.calls[i].event&&x.calls[i].rax==y.calls[i].rax&&x.calls[i].arg==y.calls[i].arg&&x.calls[i].number==y.calls[i].number);
  const unsigned char*p=(const unsigned char*)&a,*q=(const unsigned char*)&b;
  for(unsigned long i=0;i<sizeof(a);i++)require(p[i]==q[i]);pairs++;
 }return pairs;
}
int main(void){
 unsigned n=make_patterns();require(n==136);
 for(unsigned i=0;i<12;i++)require(M14_C_NMI_HEADER_ABI[i]==M14_RUST_NMI_HEADER_ABI[i]);
 for(unsigned i=0;i<7;i++)require(M14_C_BATCH_WORD_ABI[i]==M14_RUST_BATCH_WORD_ABI[i]);
 unsigned long np=0;require(m14_nmi_pure_body_fixture(&np)==0);
 unsigned long sp=stack_fixture(n),ep=exit_fixture();
 for(unsigned i=0;i<n;i++){struct x86_user_context c;init_context(&c,i);c.gpr.rsp=patterns[i];
  require(actual_interrupt_classifier(&c)==((patterns[i]>>63)?0:1));}
 require(np==6528&&sp==1360&&ep==112);
 printf("M14 next-body batch: pureNMI=%lu stackNoWalk=%lu interruptExit=%lu classifier=%u ABI=19 failures=%u\n",np,sp,ep,n,failures);
 printf("NOTEXECUTED: rawNMIflags IRQenable kernelStackTraversal NMIcallerNULL native\n");
 return failures?1:0;
}
