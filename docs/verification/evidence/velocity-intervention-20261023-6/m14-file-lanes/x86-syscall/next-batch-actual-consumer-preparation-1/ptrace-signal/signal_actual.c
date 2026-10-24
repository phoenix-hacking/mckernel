/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual selected C entry + exact C fallback against public Rust, real ABI.
 * TESTONLY IRQ/lock/MSR/wakeup/kill/schedule effects; no privileged mechanism.
 */
#include <process.h>
#include <cls.h>
#include <waitq.h>
#include <ihk/debug.h>
#include <string.h>
#include "original-C-offsets.ACTUAL.inc"
extern int printf(const char *,...);
extern int vsnprintf(char *,unsigned long,const char *,__builtin_va_list);
extern void ptrace_report_signal(struct thread *,int);
extern unsigned long fixture_signal_Rust_ABI(unsigned long);
extern int ptrace_report_signal_body_result(void *,int,void *,const struct ptrace_report_signal_offsets *,void *,
 void (*)(void *,void *),void (*)(void *,void *),void (*)(void *),void (*)(void *),
 long (*)(void *,int,int,int,const void *,int),void (*)(void),void (*)(int,int,int));
static struct thread target,current_thread;
static struct process target_proc,parent_proc,report_proc;
static struct cpu_local_var cpu;
static unsigned long debugregs[8];
static struct config {int traced,trace_syscall,main,signal,invalid,debug;unsigned long kill_result;} cfg;
struct effect {unsigned long kind,a,b,c,d;};
struct observation {
 struct effect events[20];unsigned long used,locks,unlocks,saves,wakes,kills,schedules,cpu_reads;
 char text[512];unsigned long text_used;
 struct siginfo kill_info;
 struct thread thread;
 struct process proc;
 unsigned long debugregs[8];
};
static struct observation obs,selected_result,rust_result,fallback_result;
static int held;
static void *active_node;
static unsigned long vector_number;
#define CHECK(x) do {if(!(x)){printf("FAIL signal line=%d vector=%lu\n",__LINE__,vector_number);return 1;}}while(0)
static void require(int good){if(!good)__builtin_trap();}
static void effect(unsigned long k,unsigned long a,unsigned long b,unsigned long c,unsigned long d)
{ require(obs.used<20);obs.events[obs.used++]=(struct effect){k,a,b,c,d}; }
int kprintf(const char *fmt,...)
{
 __builtin_va_list ap;__builtin_va_start(ap,fmt);
 int n=vsnprintf(obs.text+obs.text_used,sizeof(obs.text)-obs.text_used,fmt,ap);
 __builtin_va_end(ap);require(n>=0 && (unsigned long)n<sizeof(obs.text)-obs.text_used);
 obs.text_used+=(unsigned long)n;return n;
}
struct cpu_local_var *fixture_signal_cpu(void){obs.cpu_reads++;return &cpu;}
void fixture_signal_lock(void *l,void *n)
{
 require(l==&target_proc.update_lock && n && ((unsigned long)n%64)==0 && !held);
 active_node=n;held=1;obs.locks++;
 ((struct mcs_rwlock_node_irqsave *)n)->irqsave=0xabc123UL;
 effect(1,(unsigned long)l,64,0,0);
}
void fixture_signal_unlock(void *l,void *n)
{
 require(l==&target_proc.update_lock && held && n==active_node);
 require(((struct mcs_rwlock_node_irqsave *)n)->irqsave==0xabc123UL);
 held=0;obs.unlocks++;effect(2,(unsigned long)l,64,0,0);
}
void fixture_signal_save(void *p)
{
 require(held && p==debugregs);obs.saves++;
 for(int i=0;i<8;i++)debugregs[i]=0xf000UL+(unsigned long)i;
 effect(3,(unsigned long)p,0,0,0);
}
void fixture_signal_wake(void *q)
{
 require(q==(cfg.main?(void *)&parent_proc.waitpid_q:(void *)&report_proc.waitpid_q));
 require(held==!cfg.main);obs.wakes++;effect(4,(unsigned long)q,held,0,0);
}
unsigned long do_kill(struct thread *t,int pid,int tid,int sig,siginfo_t *info,int cont)
{
 require(!held && t==&current_thread && tid==-1 && sig==SIGCHLD && cont==0);
 require(pid==(cfg.main?parent_proc.pid:report_proc.pid));
 struct siginfo expected;memset(&expected,0,sizeof expected);expected.si_signo=SIGCHLD;
 expected.si_code=CLD_TRAPPED;expected._sifields._sigchld.si_pid=target.tid;
 expected._sifields._sigchld.si_status=target.exit_status;
 require(memcmp(info,&expected,sizeof expected)==0);
 obs.kills++;obs.kill_info=*info;
 effect(5,(unsigned long)t,(unsigned long)(long)pid,(unsigned long)(long)tid,(unsigned long)(long)sig);
 return cfg.kill_result;
}
void schedule(void)
{
 require(!held && obs.kills==1 && obs.wakes==1);obs.schedules++;effect(6,0,0,0,0);
 /* Synchronous wake/resume may change reported state. No reference is retained. */
 target.exit_status=123456;target.status=PS_RUNNING;target_proc.status=PS_RUNNING;
}
#define get_this_cpu_local_var fixture_signal_cpu
#undef mcs_rwlock_writer_lock
#undef mcs_rwlock_writer_unlock
#define mcs_rwlock_writer_lock(l,n) fixture_signal_lock((l),(n))
#define mcs_rwlock_writer_unlock(l,n) fixture_signal_unlock((l),(n))
#define save_debugreg fixture_signal_save
#define waitq_wakeup fixture_signal_wake
#include "original-adapters.ACTUAL.inc"
#define ptrace_report_signal original_selected_C_entry
#include "original-entry.ACTUAL.inc"
#undef ptrace_report_signal
/* Preserve fallback baseline separately: it lacks the selected helper null checks. */
#undef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
#define ptrace_report_signal original_fallback_C_entry
#include "original-entry.ACTUAL.inc"
#undef ptrace_report_signal
#define MCKERNEL_RUST_SYSCALL_POLICY_HELPERS 1
#undef get_this_cpu_local_var
extern struct ddebug __start___verbose[],__stop___verbose[];
static void reset(void)
{
 memset(&obs,0,sizeof obs);memset(&target,0,sizeof target);memset(&current_thread,0,sizeof current_thread);
 memset(&target_proc,0,sizeof target_proc);memset(&parent_proc,0,sizeof parent_proc);memset(&report_proc,0,sizeof report_proc);memset(&cpu,0,sizeof cpu);
 held=0;active_node=NULL;for(int i=0;i<8;i++)debugregs[i]=0x100UL+(unsigned long)i;
 target.proc=&target_proc;target.tid=77;target.status=PS_RUNNING;target.exit_status=-45;
 target.signal_flags=0x40|SIGNAL_STOP_STOPPED;
 target.ptrace=(cfg.traced?PT_TRACED:0)|(cfg.trace_syscall?PT_TRACE_SYSCALL:0)|0x40000000;
 target.ptrace_debugreg=debugregs;target.report_proc=&report_proc;
 target_proc.pid=88;target_proc.status=PS_RUNNING;target_proc.parent=&parent_proc;
 target_proc.main_thread=cfg.main?&target:&current_thread;
 parent_proc.pid=99;report_proc.pid=101;cpu.current=&current_thread;
 if(cfg.invalid==2)target.proc=NULL;
 if(cfg.invalid==3)cpu.current=NULL;
 if(cfg.invalid==4)target_proc.parent=NULL;
 if(cfg.invalid==5)target.report_proc=NULL;
 for(struct ddebug *d=__start___verbose;d<__stop___verbose;d++)d->flags=cfg.debug;
}
static void save(struct observation *out)
{
 require(!held);obs.thread=target;obs.proc=target_proc;
 memcpy(obs.debugregs,debugregs,sizeof debugregs);*out=obs;
}
static int compare(void)
{
 reset();original_selected_C_entry(cfg.invalid==1?NULL:&target,cfg.signal);save(&selected_result);
 reset();ptrace_report_signal(cfg.invalid==1?NULL:&target,cfg.signal);save(&rust_result);
 CHECK(memcmp(&selected_result,&rust_result,sizeof selected_result)==0);
 CHECK(selected_result.cpu_reads==1);
 CHECK(selected_result.locks==selected_result.unlocks && selected_result.locks<=1);
 CHECK(selected_result.saves<=1 && selected_result.wakes<=1 && selected_result.kills<=1 && selected_result.schedules<=1);
 if(cfg.invalid==0) {
  reset();original_fallback_C_entry(&target,cfg.signal);save(&fallback_result);
  CHECK(fallback_result.cpu_reads==(unsigned long)(cfg.traced?1:0));
  /* The selected wrapper captures current before the body; old fallback only
   * fetches current at do_kill. Keep this baseline difference explicit. */
  struct observation comparison=selected_result;comparison.cpu_reads=fallback_result.cpu_reads;
  CHECK(memcmp(&comparison,&fallback_result,sizeof comparison)==0);
 }
 return 0;
}
int main(void)
{
 unsigned long expected[]={sizeof(struct thread),__alignof__(struct thread),sizeof(struct process),__alignof__(struct process),sizeof(struct cpu_local_var),sizeof(struct siginfo),sizeof(struct mcs_rwlock_node_irqsave),__alignof__(struct mcs_rwlock_node_irqsave),
 __builtin_offsetof(struct thread,proc),__builtin_offsetof(struct thread,tid),__builtin_offsetof(struct thread,status),__builtin_offsetof(struct thread,exit_status),__builtin_offsetof(struct thread,signal_flags),__builtin_offsetof(struct thread,ptrace),__builtin_offsetof(struct thread,ptrace_debugreg),__builtin_offsetof(struct thread,report_proc),__builtin_offsetof(struct process,pid),__builtin_offsetof(struct process,parent),__builtin_offsetof(struct process,main_thread),__builtin_offsetof(struct process,status),__builtin_offsetof(struct process,update_lock),__builtin_offsetof(struct process,waitpid_q)};
 for(unsigned long i=0;i<sizeof expected/sizeof expected[0];i++)CHECK(expected[i]==fixture_signal_Rust_ABI(i));
 CHECK((unsigned long)(__stop___verbose-__start___verbose)==9);
 const int signals[]={0,SIGCHLD,SIGSTOP,SIGTSTP,SIGTTIN,SIGTTOU,-1,2147483647};
 for(int traced=0;traced<2;traced++)for(int syscall=0;syscall<2;syscall++)for(int main=0;main<2;main++)for(int sig=0;sig<8;sig++)for(int invalid=0;invalid<6;invalid++)for(int debug=0;debug<3;debug++)for(int rc=0;rc<3;rc++) {
  cfg=(struct config){traced,syscall,main,signals[sig],invalid,debug==0?0:debug==1?1:128,rc==0?0:rc==1?~0UL:0x8000000000000000UL};
  if(compare())return 1;vector_number++;
 }
 printf("PASS ptrace_report_signal selected_C_public_Rust=%lu fallback_baseline_valid_only=1 actual_ABI_fields22=1 controls_lock_MSR_wait_kill_schedule=1\n",vector_number);
 return 0;
}
