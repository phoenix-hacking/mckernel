/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Original byte-extracted C tail and exact private Rust body. Scheduler, IPI,
 * recursive signal delivery and reference-release are controlled endpoints.
 * Headers supply actual structs/constants. No native scheduling is claimed.
 */
#include <types.h>
#include <affinity.h>
#include <process.h>
#include <ihk/debug.h>
#include <string.h>
extern int printf(const char *, ...);
extern size_t fixture_wakeup_abi(size_t);
extern int arch_do_kill_wakeup_result(struct thread *,struct thread *,struct process *,
        int,int,unsigned long,int,int);
extern struct ddebug __start___verbose[], __stop___verbose[];
_Static_assert(sizeof(long)==8 && sizeof(int)==4,"LP64");
_Static_assert(sizeof(siginfo_t)==128,"real siginfo bytes");
_Static_assert(__builtin_types_compatible_p(__typeof__(&release_thread),void (*)(struct thread *)),"release endpoint ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&sched_wakeup_thread),int (*)(struct thread *,int)),"wakeup endpoint ABI");
enum { WAKE=1, NOTIFY, VECTOR, IPI, DEBUG, RELEASE };
struct event {int kind,a,b,status,pid,p0,p1,flags0,flags1,cpu;};
struct outcome {struct event events[12];int count,error,releases,notify_count,rc,status,
        proc_id,p0,p1,flags0,flags1,cpu;unsigned char info[128];};
static struct thread caller,target,main0,main1;
static struct process proc0,proc1,parent0,parent1;
static struct outcome observed;
static int initial_wake,mutation,released,expected_pid;
static void clear_bytes(void *p,size_t n){unsigned char *s=p;while(n--)*s++=0;}
static int same_bytes(const void *p,const void *q,size_t n){const unsigned char *a=p,*b=q;while(n--)if(*a++!=*b++)return 0;return 1;}
static void capture(int kind,int a,int b){
 struct event *e;
 if(released || observed.count>=12){observed.error=1;return;}
 e=&observed.events[observed.count++];e->kind=kind;e->a=a;e->b=b;
 e->status=target.status;e->pid=target.proc->pid;e->p0=proc0.status;e->p1=proc1.status;
 e->flags0=main0.signal_flags;e->flags1=main1.signal_flags;e->cpu=target.cpu_id;
}
int sched_wakeup_thread(struct thread *t,int states){
 if(t!=&target)observed.error=1;
 capture(WAKE,states,0);
 if(states==PS_STOPPED){
  if(mutation==1 && initial_wake==0)target.proc=&proc1;
  return initial_wake;
 }
 return -31;
}
unsigned long do_kill(struct thread *t,int pid,int tid,int sig,siginfo_t *info,int pc){
 siginfo_t expected;
 capture(NOTIFY,pid,sig);++observed.notify_count;
 clear_bytes(&expected,sizeof(expected));expected.si_signo=SIGCHLD;expected.si_code=CLD_CONTINUED;
 expected._sifields._sigchld.si_pid=target.proc->pid;
 expected._sifields._sigchld.si_status=0x0000ffff;
 if(t!=&target || tid!=-1 || pc!=0 || sig!=SIGCHLD || pid!=expected_pid
    || !same_bytes(info,&expected,128) || target.proc->status!=PS_RUNNING
    || target.proc->main_thread->signal_flags!=SIGNAL_STOP_CONTINUED)observed.error=1;
 {size_t i;for(i=0;i<128;i++)observed.info[i]=((unsigned char*)info)[i];}
 if(mutation==2){target.proc=&proc1;target.status=PS_TRACED;target.cpu_id=7;proc1.status=PS_STOPPED;}
 return (unsigned long)-999; /* must not overwrite enqueue rc */
}
int ihk_mc_get_vector(enum ihk_mc_gv_type type){capture(VECTOR,(int)type,0);if(type!=IHK_GV_IKC)observed.error=1;return 209;}
int ihk_mc_interrupt_cpu(int cpu,int vector){
 capture(IPI,cpu,vector);
 if(cpu!=target.cpu_id || vector!=209)observed.error=1;
 /* Changes target status after the candidate must have taken its snapshot. */
 if(mutation==2)target.status=PS_RUNNING;
 return -77;
}
int kprintf(const char *fmt,...){
 __builtin_va_list ap;int pid,cpu;
 __builtin_va_start(ap,fmt);pid=__builtin_va_arg(ap,int);cpu=__builtin_va_arg(ap,int);__builtin_va_end(ap);
 capture(DEBUG,pid,cpu);
 if(!same_bytes(fmt,"do_kill,ipi,pid=%d,cpu_id=%d\n",sizeof("do_kill,ipi,pid=%d,cpu_id=%d\n")) || pid!=proc0.pid || cpu!=target.cpu_id)observed.error=1;
 return 0;
}
void release_thread(struct thread *t){
 if(t!=&target)observed.error=1;
 capture(RELEASE,0,0);++observed.releases;released=1;
}
static unsigned long original_wakeup(struct thread *thread,struct thread *tthread,
        struct process *tproc,int sig,int ptracecont,unsigned long mask,int doint,int rc){
#include "original-wakeup.ACTUAL.inc"
}
static void setup(int status,int block,int mut,int wake,int debug){
 struct ddebug *d;
 clear_bytes(&observed,sizeof(observed));clear_bytes(&caller,sizeof(caller));clear_bytes(&target,sizeof(target));
 clear_bytes(&proc0,sizeof(proc0));clear_bytes(&proc1,sizeof(proc1));clear_bytes(&main0,sizeof(main0));clear_bytes(&main1,sizeof(main1));
 clear_bytes(&parent0,sizeof(parent0));clear_bytes(&parent1,sizeof(parent1));
 proc0.pid=101;proc1.pid=202;parent0.pid=301;parent1.pid=302;
 proc0.parent=&parent0;proc1.parent=&parent1;proc0.main_thread=&main0;proc1.main_thread=&main1;
 proc0.status=PS_STOPPED;proc1.status=PS_TRACED;main0.signal_flags=81;main1.signal_flags=82;
 target.proc=&proc0;target.status=status;target.cpu_id=4;target.sigmask.__val[0]=block?~0UL:0;
 initial_wake=wake;mutation=mut;released=0;expected_pid=mut==1 && wake==0?302:301;
 for(d=__start___verbose;d<__stop___verbose;d++)d->flags=debug;
}
static int run(int rust,int caller_mode,int sig,int pc,int di,int block,int status,int wake,int mut,int rc,int debug,struct outcome *out){
 struct thread *source;unsigned long ret;
 setup(status,block,mut,wake,debug);source=caller_mode==0?NULL:caller_mode==1?&target:&caller;
 ret=rust?(unsigned long)arch_do_kill_wakeup_result(source,&target,&proc0,sig,pc,1UL<<(sig-1),di,rc):
    original_wakeup(source,&target,&proc0,sig,pc,1UL<<(sig-1),di,rc);
 observed.rc=(int)ret;observed.status=target.status;observed.proc_id=target.proc==&proc0?0:1;
 observed.p0=proc0.status;observed.p1=proc1.status;observed.flags0=main0.signal_flags;observed.flags1=main1.signal_flags;observed.cpu=target.cpu_id;
 if(ret!=(unsigned long)rc || observed.releases!=1 || observed.count<1
    || observed.events[observed.count-1].kind!=RELEASE)observed.error=1;
 if(observed.notify_count!=((sig==SIGCONT || pc==1) && wake==0))observed.error=1;
 /* Independent counts include status saved before an IPI mutates target.status. */
 {int stop=(sig==SIGCONT || pc==1),continued=stop && wake==0;
  int ordinary=di && !block && !continued;
  int want_wakes=stop+(ordinary && status!=PS_RUNNING);
  int want_ipi=caller_mode!=1 && (continued || ordinary);
  int nw=0,ni=0,nd=0,i;
  for(i=0;i<observed.count;i++){
   nw+=observed.events[i].kind==WAKE;ni+=observed.events[i].kind==IPI;
   nd+=observed.events[i].kind==DEBUG;
  }
  if(nw!=want_wakes || ni!=want_ipi || nd!=(debug && ordinary && caller_mode!=1))observed.error=1;
  if(continued && target.proc->status!=PS_RUNNING)observed.error=1;
 }
 /* Independent ordering/mask assertions in addition to the byte-extracted oracle. */
 {int i,seen_vector=0;for(i=0;i<observed.count;i++){
  struct event *e=&observed.events[i];
  if(e->kind==VECTOR)seen_vector=1;
  if(e->kind==IPI){if(!seen_vector)observed.error=1;seen_vector=0;}
  if(e->kind==WAKE){
   int stop_wake=i==0 && (sig==SIGCONT || pc==1);
   int expected=stop_wake?PS_STOPPED:(sig==SIGKILL?(PS_TRACED|PS_STOPPED|PS_INTERRUPTIBLE):PS_INTERRUPTIBLE);
   if(e->a!=expected)observed.error=1;
  }
  if(e->kind==NOTIFY && (i==0 || observed.events[0].kind!=WAKE || observed.events[0].a!=PS_STOPPED))observed.error=1;
 }}
 *out=observed;return observed.error;
}
int main(void){
 static struct outcome a,b;unsigned long cases=0;
 const int sigs[]={12,SIGCONT,SIGKILL},statuses[]={PS_RUNNING,PS_STOPPED,PS_TRACED,PS_INTERRUPTIBLE},wakes[]={0,1,-11};
 size_t values[]={sizeof(struct thread),_Alignof(struct thread),sizeof(struct process),_Alignof(struct process),sizeof(siginfo_t),_Alignof(siginfo_t),
 sizeof(((siginfo_t*)0)->_sifields._sigchld),offsetof(siginfo_t,_sifields),offsetof(siginfo_t,si_code),offsetof(siginfo_t,_sifields._sigchld.si_status)-offsetof(siginfo_t,_sifields),
 offsetof(struct thread,proc),offsetof(struct thread,cpu_id),offsetof(struct thread,status),offsetof(struct thread,signal_flags),offsetof(struct thread,sigmask),
 offsetof(struct process,status),offsetof(struct process,main_thread),offsetof(struct process,parent),offsetof(struct process,pid),sizeof(struct ddebug),_Alignof(struct ddebug),
 SIGKILL,SIGCHLD,SIGCONT,PS_RUNNING,PS_INTERRUPTIBLE,PS_STOPPED,PS_TRACED,SIGNAL_STOP_CONTINUED,CLD_CONTINUED};
 int c,s,p,d,k,t,w,m,r,g;size_t i;
 for(i=0;i<sizeof(values)/sizeof(values[0]);i++)if(values[i]!=fixture_wakeup_abi(i)){printf("FAIL ABI %lu\n",(unsigned long)i);return 1;}
 for(c=0;c<3;c++)for(s=0;s<3;s++)for(p=0;p<2;p++)for(d=0;d<2;d++)for(k=0;k<2;k++)for(t=0;t<4;t++)for(w=0;w<3;w++)for(m=0;m<3;m++)for(r=0;r<2;r++)for(g=0;g<2;g++){
  int e0=run(0,c,sigs[s],p,d,k,statuses[t],wakes[w],m,r?-12:0,g,&a);
  int e1=run(1,c,sigs[s],p,d,k,statuses[t],wakes[w],m,r?-12:0,g,&b);
  if(e0 || e1 || !same_bytes(&a,&b,sizeof(a))){printf("FAIL wakeup case=%lu c%d s%d p%d d%d k%d t%d w%d m%d r%d g%d\n",cases,c,s,p,d,k,t,w,m,r,g);return 1;}++cases;
 }
 printf("PASS actual_C_Rust_wakeup cases=%lu ABI=30 ordered_callbacks=1 siginfo_bytes=128 release_once=1\n",cases);return 0;
}
