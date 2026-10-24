/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual kernel C structures and original body text; callbacks model effects only.
 * No IRQ/MSR/scheduler/guest effects. The partially initialized C forwarding
 * provider remains exact; the fixture observes only its three initialized args.
 */
#include <types.h>
#include <process.h>
#include <cls.h>
#include <ihk/monitor.h>
#include <ihk/lock.h>
#include <errno.h>
#include <string.h>
#include <process_helpers.h>
#ifndef offsetof
#define offsetof(t,m) __builtin_offsetof(t,m)
#endif
extern int printf(const char *,...);
extern void abort(void);
extern unsigned long syscall_pending_mask_bridge(void *);
extern long syscall_sigsuspend_bridge(void *,void *);
extern int do_sigaction(int,struct k_sigaction *,struct k_sigaction *);
extern int syscall_do_sigaction_bridge(int,void *,void *);
extern size_t fixture_rust_layout(size_t *);
static unsigned long case_id;static int which;
#define CHECK(x) do{if(!(x)){printf("FAIL case=%lu implementation=%d line=%d predicate=%s\n",case_id,which,__LINE__,#x);abort();}}while(0)
static void bytes_clear(void *p,size_t n){unsigned char *d=p;for(size_t i=0;i<n;i++)d[i]=0;}
static void bytes_copy(void *d0,const void *s0,size_t n){unsigned char*d=d0;const unsigned char*s=s0;for(size_t i=0;i<n;i++)d[i]=s[i];}
/* Hosted-only provider for the known kernelstring.h macro ABI, never product code. */
void *__inline_memset(void *p,unsigned long c,size_t n){unsigned char*d=p;for(size_t i=0;i<n;i++)d[i]=(unsigned char)c;return p;}
void *__inline_memcpy(void *d,const void*s,size_t n){bytes_copy(d,s,n);return d;}
struct event {int kind,id;unsigned long a,b;};
static struct thread th;
static struct sig_common common;
static struct cpu_local_var cpu;
static struct ihk_os_cpu_monitor fixture_cpu_monitor;
static struct sig_pending nodes[8];
static struct k_sigaction input_act,output_act;
static struct event events[128];static size_t nevents;
static void *held_lock,*held_node;static int irq_disabled,runq_held,wait_mode,placement,consumed,injected;
static unsigned long saved_mask,wait_mask,forward_return;static int forward_sig;
static void log_event(int k,int id,unsigned long a,unsigned long b){CHECK(nevents<128);events[nevents++]=(struct event){k,id,a,b};}
static int lock_id(void*p){if(p==&common.lock)return 1;if(p==&th.sigpendinglock)return 2;if(p==&cpu.runq_lock)return 3;CHECK(0);return 0;}
struct cpu_local_var *get_this_cpu_local_var(void){log_event(1,0,0,0);return &cpu;}
void fixture_writer_lock(void *p,void*n){CHECK(!held_lock);CHECK(((unsigned long)n&63)==0);held_lock=p;held_node=n;((struct mcs_rwlock_node_irqsave*)n)->irqsave=0x1234;log_event(2,lock_id(p),th.sigmask.__val[0],th.sigevent);}
void fixture_writer_unlock(void*p,void*n){CHECK(held_lock==p&&held_node==n);CHECK(((struct mcs_rwlock_node_irqsave*)n)->irqsave==0x1234);log_event(3,lock_id(p),th.sigmask.__val[0],th.sigevent);held_lock=held_node=0;}
unsigned long fixture_disable_irq(void){CHECK(!irq_disabled&&!runq_held);irq_disabled=1;log_event(4,0,th.status,th.sigevent);return 0x2468;}
void fixture_restore_irq(unsigned long value){CHECK(irq_disabled&&!runq_held&&value==0x2468);irq_disabled=0;log_event(7,0,cpu.flags,0);}
void fixture_runq_lock(void*p){CHECK(p==&cpu.runq_lock&&irq_disabled&&!runq_held);runq_held=1;log_event(5,3,cpu.flags,0);}
void fixture_runq_unlock(void*p){CHECK(p==&cpu.runq_lock&&irq_disabled&&runq_held);runq_held=0;log_event(6,3,cpu.flags,0);}
static void append(struct list_head*h,struct sig_pending*n){n->list.prev=h->prev;n->list.next=h;h->prev->next=&n->list;h->prev=&n->list;}
static void wake_after_wait(int schedule_path){
 CHECK(!held_lock&&!runq_held&&!irq_disabled&&!injected);
 CHECK(th.status==PS_INTERRUPTIBLE&&th.sigevent==0&&th.sigmask.__val[0]==wait_mask);
 CHECK(fixture_cpu_monitor.status==IHK_OS_MONITOR_KERNEL_HEAVY);
 CHECK(schedule_path==(wait_mode==2));CHECK(!(cpu.flags&CPU_FLAG_NEED_RESCHED));
 log_event(8,schedule_path,th.status,th.sigmask.__val[0]);
 if(placement!=1)append(&common.sigpending,&nodes[2]);
 if(placement!=0)append(&th.sigpending,&nodes[3]);
 th.sigevent=1;injected=1;
}
void fixture_schedule(void){wake_after_wait(1);}
void fixture_pause(void){wake_after_wait(0);}
int do_signal(unsigned long rc,void*regs,struct thread*t,struct sig_pending*p,int n){
 CHECK(rc==(unsigned long)-EINTR&&!regs&&t==&th&&n==-1);
 CHECK(!held_lock&&!runq_held&&!irq_disabled&&th.sigmask.__val[0]==saved_mask);
 CHECK(th.status==PS_RUNNING&&th.sigevent==0&&fixture_cpu_monitor.status==IHK_OS_MONITOR_KERNEL_HEAVY);
 int id=p==&nodes[2]?2:p==&nodes[3]?3:-1;CHECK(id==(placement==1?3:2));CHECK(consumed==-1);
 CHECK(p->list.next==(void*)0x00100129&&p->list.prev==(void*)0x00200229);
 consumed=id;log_event(9,id,rc,n);
 /* Model consumption/free: every byte becomes poison before the body returns. */
 for(size_t i=0;i<sizeof(*p);i++)((unsigned char*)p)[i]=0xdd;
 return -777;
}
static long fixture_forwarding(int nr,ihk_mc_user_context_t*ctx){
 CHECK(nr==13&&!held_lock&&!runq_held&&!irq_disabled);
 unsigned long sig=ihk_mc_syscall_arg0(ctx),handler=ihk_mc_syscall_arg1(ctx),flags=ihk_mc_syscall_arg2(ctx);
 CHECK((int)sig==forward_sig);log_event(10,(int)sig,handler,flags);return (long)forward_return;
}
#undef mcs_rwlock_writer_lock
#undef mcs_rwlock_writer_unlock
#define mcs_rwlock_writer_lock fixture_writer_lock
#define mcs_rwlock_writer_unlock fixture_writer_unlock
#define cpu_disable_interrupt_save fixture_disable_irq
#define cpu_restore_interrupt fixture_restore_irq
#undef ihk_mc_spinlock_lock_noirq
#undef ihk_mc_spinlock_unlock_noirq
#define ihk_mc_spinlock_lock_noirq fixture_runq_lock
#define ihk_mc_spinlock_unlock_noirq fixture_runq_unlock
#define schedule fixture_schedule
#define cpu_pause fixture_pause
#define syscall_generic_forwarding fixture_forwarding
#define SYSCALL_POLICY_HELPER_SCOPE static
typedef void (*syscall_sigcommon_lock_fn_t)(void*,void*);
typedef long (*syscall_sigaction_forward_fn_t)(int,const void*);
/* Original C scalar helpers remain independent of the Rust versions. */
#define valid_signal original_valid_signal
#define sigaction_validate original_sigaction_validate
#define sigsuspend_prepare_mask original_sigsuspend_prepare_mask
#define sigsuspend_pending_matches original_sigsuspend_pending_matches
#include "valid_signal.EXACT-ORIGINAL-C.inc"
#include "sigaction_validate.EXACT-ORIGINAL-C.inc"
#include "sigsuspend_prepare_mask.EXACT-ORIGINAL-C.inc"
#include "sigsuspend_pending_matches.EXACT-ORIGINAL-C.inc"
#define do_sigaction_body_result original_do_sigaction_body_result
#include "do_sigaction_body_result.EXACT-ORIGINAL-C.inc"
#define syscall_pending_mask_bridge original_pending_mask_bridge
#include "pending_mask.EXACT-ORIGINAL-C.inc"
#undef syscall_pending_mask_bridge
#define syscall_sigsuspend_bridge original_sigsuspend_bridge
#include "sigsuspend.EXACT-ORIGINAL-C.inc"
#undef syscall_sigsuspend_bridge
#define syscall_forward_sigaction_update_bridge original_forward_provider
#define do_sigaction original_do_sigaction
#include "do_sigaction.EXACT-ORIGINAL-C.inc"
#undef do_sigaction
#undef syscall_forward_sigaction_update_bridge
/* Host-only linkage adapter; both sides consume the exact original provider. */
long syscall_forward_sigaction_update_bridge(int s,const void*a){return original_forward_provider(s,a);}
static int original_do_sigaction_bridge(int s,void*a,void*o){return original_do_sigaction(s,a,o);}
#undef sigaction_validate
#undef sigsuspend_prepare_mask
#undef sigsuspend_pending_matches

static void init_list(struct list_head*h){h->next=h->prev=h;}
static void reset(void){
 bytes_clear(&th,sizeof(th));bytes_clear(&common,sizeof(common));bytes_clear(&cpu,sizeof(cpu));bytes_clear(&fixture_cpu_monitor,sizeof(fixture_cpu_monitor));bytes_clear(nodes,sizeof(nodes));bytes_clear(events,sizeof(events));bytes_clear(&input_act,sizeof(input_act));bytes_clear(&output_act,sizeof(output_act));
 th.sigcommon=&common;cpu.current=&th;cpu.monitor=&fixture_cpu_monitor;init_list(&common.sigpending);init_list(&th.sigpending);
 nevents=0;held_lock=held_node=0;irq_disabled=runq_held=injected=0;consumed=-1;forward_return=0;forward_sig=0;
}
struct snapshot {long result;struct thread t;struct sig_common c;struct cpu_local_var v;struct ihk_os_cpu_monitor m;struct sig_pending p[8];struct k_sigaction in,out;struct event e[128];size_t n;int consumed,irq,runq,injected;};
static struct snapshot a,b;
static void save(struct snapshot*s,long result){bytes_clear(s,sizeof(*s));s->result=result;bytes_copy(&s->t,&th,sizeof(th));bytes_copy(&s->c,&common,sizeof(common));bytes_copy(&s->v,&cpu,sizeof(cpu));bytes_copy(&s->m,&fixture_cpu_monitor,sizeof(fixture_cpu_monitor));bytes_copy(s->p,nodes,sizeof(nodes));bytes_copy(&s->in,&input_act,sizeof(input_act));bytes_copy(&s->out,&output_act,sizeof(output_act));bytes_copy(s->e,events,sizeof(events));s->n=nevents;s->consumed=consumed;s->irq=irq_disabled;s->runq=runq_held;s->injected=injected;CHECK(!held_lock&&!irq_disabled&&!runq_held);}
static void equivalent(void){if(memcmp(&a,&b,sizeof(a))){printf("MISMATCH case=%lu C_rc=%ld Rust_rc=%ld C_events=%lu Rust_events=%lu C_consumed=%d Rust_consumed=%d\n",case_id,a.result,b.result,a.n,b.n,a.consumed,b.consumed);for(size_t i=0;i<a.n||i<b.n;i++)printf("event%lu C=%d,%d,%lx,%lx Rust=%d,%d,%lx,%lx\n",i,a.e[i].kind,a.e[i].id,a.e[i].a,a.e[i].b,b.e[i].kind,b.e[i].id,b.e[i].a,b.e[i].b);for(size_t i=0;i<sizeof(a);i++)if(((unsigned char*)&a)[i]!=((unsigned char*)&b)[i]){printf("first_differing_snapshot_byte=%lu C=%u Rust=%u\n",i,((unsigned char*)&a)[i],((unsigned char*)&b)[i]);break;}abort();}}
static const unsigned long patterns[8]={0,1,1UL<<8,1UL<<18,1UL<<63,~0UL,0x5555555555555555UL,0xaaaaaaaaaaaaaaaaUL};
static void abi_check(void){
 size_t r[64],c[]={sizeof(struct thread),_Alignof(struct thread),offsetof(struct thread,status),offsetof(struct thread,sigcommon),offsetof(struct thread,sigmask),offsetof(struct thread,sigpending),offsetof(struct thread,sigpendinglock),offsetof(struct thread,sigevent),sizeof(struct sig_common),_Alignof(struct sig_common),offsetof(struct sig_common,lock),offsetof(struct sig_common,action),offsetof(struct sig_common,sigpending),sizeof(struct sig_pending),_Alignof(struct sig_pending),offsetof(struct sig_pending,list),offsetof(struct sig_pending,sigmask),offsetof(struct sig_pending,info),sizeof(struct cpu_local_var),_Alignof(struct cpu_local_var),offsetof(struct cpu_local_var,runq_lock),offsetof(struct cpu_local_var,current),offsetof(struct cpu_local_var,flags),offsetof(struct cpu_local_var,monitor),sizeof(struct ihk_os_cpu_monitor),offsetof(struct ihk_os_cpu_monitor,status),sizeof(struct k_sigaction),_Alignof(struct k_sigaction),offsetof(struct k_sigaction,sa),sizeof(struct mcs_rwlock_node_irqsave),_Alignof(struct mcs_rwlock_node_irqsave),sizeof(sigset_t),sizeof(mcs_rwlock_lock_t),_Alignof(mcs_rwlock_lock_t)};
 CHECK(fixture_rust_layout(r)==sizeof(c)/sizeof(c[0]));for(size_t i=0;i<sizeof(c)/sizeof(c[0]);i++)if(c[i]!=r[i]){printf("ABI_MISMATCH index=%lu C=%lu Rust=%lu\n",i,c[i],r[i]);abort();}
}
static void pending_cases(void){for(int cn=0;cn<4;cn++)for(int tn=0;tn<4;tn++)for(int seed=0;seed<8;seed++){
 case_id++;for(which=0;which<2;which++){reset();unsigned long want=0;
 for(int i=0;i<cn;i++){nodes[i].sigmask.__val[0]=patterns[(seed+i)%8];append(&common.sigpending,&nodes[i]);want|=nodes[i].sigmask.__val[0];}
 for(int i=0;i<tn;i++){nodes[4+i].sigmask.__val[0]=patterns[(seed+i+3)%8];append(&th.sigpending,&nodes[4+i]);want|=nodes[4+i].sigmask.__val[0];}
 long result=which?syscall_pending_mask_bridge(&th):original_pending_mask_bridge(&th);CHECK((unsigned long)result==want);CHECK(nevents==4);CHECK(events[0].kind==2&&events[0].id==1&&events[1].kind==3&&events[1].id==1&&events[2].kind==2&&events[2].id==2&&events[3].kind==3&&events[3].id==2);CHECK(consumed==-1);
 save(which?&b:&a,result);
 }equivalent();
}}
static void suspend_cases(void){for(int seed=0;seed<8;seed++)for(int where=0;where<3;where++)for(int mode=0;mode<3;mode++)for(int alias=0;alias<2;alias++){
 case_id++;for(which=0;which<2;which++){reset();placement=where;wait_mode=mode;unsigned long raw=patterns[seed];wait_mask=raw&~((1UL<<8)|(1UL<<18));saved_mask=alias?raw:(0x123456789abcdef0UL^(unsigned long)seed);th.sigmask.__val[0]=saved_mask;cpu.flags=0x20|(mode==2?CPU_FLAG_NEED_RESCHED:0);
 if(wait_mask){nodes[0].sigmask.__val[0]=wait_mask;nodes[1].sigmask.__val[0]=wait_mask;append(&common.sigpending,&nodes[0]);append(&th.sigpending,&nodes[1]);}
 unsigned long freebits=~wait_mask;unsigned long allowed=freebits&-freebits;CHECK(allowed);nodes[2].sigmask.__val[0]=allowed;nodes[3].sigmask.__val[0]=allowed;
 if(!mode){if(where!=1)append(&common.sigpending,&nodes[2]);if(where!=0)append(&th.sigpending,&nodes[3]);}
 sigset_t set;bytes_clear(&set,sizeof(set));set.__val[0]=raw;void*sp=alias?(void*)&th.sigmask:(void*)&set;
 long result=which?syscall_sigsuspend_bridge(&th,sp):original_sigsuspend_bridge(&th,sp);
 CHECK(result==-EINTR&&consumed==(where==1?3:2));CHECK(th.sigmask.__val[0]==saved_mask&&th.status==PS_RUNNING&&th.sigevent==0);CHECK(injected==(mode!=0));CHECK(cpu.flags==0x20);CHECK(events[nevents-1].kind==9);
 save(which?&b:&a,result);
 }equivalent();
}}
static void action_cases(void){for(int sig=-1;sig<=66;sig++)for(int pointers=0;pointers<5;pointers++)for(int pattern=0;pattern<4;pattern++)for(int neg=0;neg<2;neg++)for(int bridge=0;bridge<2;bridge++){
 case_id++;for(which=0;which<2;which++){reset();forward_sig=sig;forward_return=neg?(unsigned long)-99:0;
 for(size_t i=0;i<sizeof(common.action);i++)((unsigned char*)common.action)[i]=(unsigned char)(i*3+pattern*17);
 for(size_t i=0;i<sizeof(input_act);i++){((unsigned char*)&input_act)[i]=pattern==0?0:pattern==1?0xff:pattern==2?0xa5:(unsigned char)(i*7+5);((unsigned char*)&output_act)[i]=0x6d;}
 struct k_sigaction*act=(pointers==1||pointers==3||pointers==4)?&input_act:0;
 struct k_sigaction*old=(pointers==2||pointers==3)?&output_act:pointers==4?&input_act:0;
 int result=which?(bridge?syscall_do_sigaction_bridge(sig,act,old):do_sigaction(sig,act,old)):(bridge?original_do_sigaction_bridge(sig,act,old):original_do_sigaction(sig,act,old));
 int invalid=sig<1||sig>64||(act&&(sig==9||sig==19));CHECK(result==(invalid?-EINVAL:0));CHECK(nevents==(invalid?1:act?4:3));CHECK(events[0].kind==1);if(!invalid){CHECK(events[1].kind==2&&events[2].kind==3);if(act)CHECK(events[3].kind==10);}
 save(which?&b:&a,result);
 }equivalent();
}}
int main(void){abi_check();pending_cases();suspend_cases();action_cases();CHECK(case_id==5712);printf("PASS_F03_ACTUAL_C_RUST_SIGNAL_BATCH pending=128 sigsuspend=144 sigaction=5440 total=5712 real_layout_fields=34 consumed_node_poison=144 host_forward_error_ignored=1488 controlled_callbacks_only=1\n");return 0;}
