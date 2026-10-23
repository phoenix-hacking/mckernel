/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual C headers and actual Rust ABI types; all primitive callbacks mocked.
 * schedule consumes the stack publication before return. No target instructions. */
#include <process.h>
#include <sched_helpers.h>
#include <cls.h>
#include <cpulocal.h>
#include "c-request-and-offsets.h"
extern void fixture_fail(unsigned);
#define CHECK(x) do { if(!(x))fixture_fail(__LINE__); } while(0)
static struct cpu_local_var target, current;
static struct thread thread, current_thread;
static int target_id,current_id,mode,return_value,use_bridge;
static unsigned int initial_flags;
struct observation { int events[24],count,get_target,get_current,get_id,provider,init,prepare,finish,schedule,interrupt,vector,log,result;unsigned int flags;int status; };
static struct observation seen;
static struct migrate_request *request;
static waitq_entry_t *entry;
static int migq_locked,runq_locked;
static void zero(void *p,unsigned long n) { unsigned char *b=p;while(n--)*b++=0; }
static void event(int n) { CHECK(seen.count<24);seen.events[seen.count++]=n; }
struct cpu_local_var *get_cpu_local_var(int id) { CHECK(id==target_id);seen.get_target++;event(1);return &target; }
unsigned long process_sched_cpu_local_bridge(int id) { return (unsigned long)get_cpu_local_var(id); }
struct cpu_local_var *get_this_cpu_local_var(void) { seen.get_current++;event(2);return &current; }
int ihk_mc_get_processor_id(void) { seen.get_id++;event(3);return current_id; }
int locked_wake_function(waitq_entry_t *e,unsigned m,int f,void *k) { (void)e;(void)m;(void)f;(void)k;fixture_fail(__LINE__);return 0; }
unsigned long process_spin_lock_bridge(unsigned long p) {
 CHECK(p==(unsigned long)&target.migq_lock&&!migq_locked&&!runq_locked);
 CHECK(request->thread==(mode==2?0:&thread));migq_locked=1;event(5);return ~0UL-9;
}
void process_spin_unlock_bridge(unsigned long p,unsigned long state) {
 CHECK(p==(unsigned long)&target.migq_lock&&migq_locked&&!runq_locked&&state==~0UL-9);
 CHECK(seen.log==1);migq_locked=0;event(12);
}
void process_sched_noirq_lock_bridge(unsigned long p) {
 CHECK(p==(unsigned long)&target.runq_lock&&migq_locked&&!runq_locked);
 CHECK(target.migq.next==&request->list&&target.migq.prev==&request->list);
 CHECK(request->list.next==&target.migq&&request->list.prev==&target.migq);
 runq_locked=1;event(8);
}
void process_sched_noirq_unlock_bridge(unsigned long p) {
 CHECK(p==(unsigned long)&target.runq_lock&&migq_locked&&runq_locked);
 CHECK(target.flags==(initial_flags|CPU_FLAG_NEED_RESCHED|CPU_FLAG_NEED_MIGRATE));
 CHECK(target.status==CPU_STATUS_RUNNING);runq_locked=0;event(9);
}
void process_sched_waitq_init_bridge(unsigned long p) {
 CHECK(p==(unsigned long)&request->wq&&migq_locked&&!runq_locked);
 request->wq.lock.head_tail=0;
 request->wq.waitq.next=request->wq.waitq.prev=&request->wq.waitq;
 seen.init++;event(6);
}
void process_sched_waitq_prepare_bridge(unsigned long p,unsigned long e,int status) {
 CHECK(p==(unsigned long)&request->wq&&e==(unsigned long)entry&&status==PS_UNINTERRUPTIBLE&&migq_locked&&!runq_locked);
 CHECK(entry->link.next==&entry->link&&entry->link.prev==&entry->link);
 CHECK(entry->private==&current_thread&&!entry->flags&&entry->func==locked_wake_function);
 struct list_head *h=&request->wq.waitq;
 h->next=h->prev=&entry->link;entry->link.next=entry->link.prev=h;
 current_thread.status=status;seen.prepare++;event(7);
}
int process_sched_vector_bridge(int key) { CHECK(key==IHK_GV_IKC&&migq_locked&&!runq_locked);seen.vector++;event(10);return -2147483647; }
void process_sched_interrupt_bridge(int id,int vector) {
 CHECK(id==thread.cpu_id&&vector==-2147483647&&migq_locked&&!runq_locked);
 CHECK(target.migq.next==&request->list);seen.interrupt++;event(11);
}
void process_sched_migrate_log_bridge(unsigned long t,int tid,int id) {
 CHECK(t==(unsigned long)&thread&&tid==thread.tid&&id==target_id&&migq_locked&&!runq_locked);
 CHECK(seen.interrupt==(target_id!=current_id));seen.log++;event(13);
}
void process_sched_schedule_bridge(void) {
 CHECK(!migq_locked&&!runq_locked&&seen.log==1&&seen.prepare==1);
 CHECK(target.migq.next==&request->list&&request->thread==&thread);
 CHECK(request->wq.waitq.next==&entry->link&&current_thread.status==PS_UNINTERRUPTIBLE);
 /* Functional schedule/target-completion model: dequeue publication and wake.
  * This does not claim a production migration or actual scheduler execution. */
 target.migq.next=target.migq.prev=&target.migq;
 request->list.next=request->list.prev=&request->list;
 current_thread.status=PS_RUNNING;seen.schedule++;event(14);
}
void process_sched_waitq_finish_bridge(unsigned long p,unsigned long e) {
 CHECK(p==(unsigned long)&request->wq&&e==(unsigned long)entry&&!migq_locked&&!runq_locked&&seen.schedule==1);
 CHECK(target.migq.next==&target.migq&&target.migq.prev==&target.migq);
 CHECK(current_thread.status==PS_RUNNING&&request->wq.waitq.next==&entry->link);
 request->wq.waitq.next=request->wq.waitq.prev=&request->wq.waitq;
 entry->link.next=entry->link.prev=&entry->link;seen.finish++;event(15);
}
extern int leaf_sched_request_migrate_body_result(int,unsigned long,unsigned long,unsigned long,unsigned long,int,int,unsigned int,unsigned int,int,int,const struct sched_migrate_offsets *,sched_migrate_spin_lock_fn_t,sched_migrate_spin_unlock_fn_t,sched_migrate_noirq_lock_fn_t,sched_migrate_noirq_unlock_fn_t,sched_migrate_waitq_init_fn_t,sched_migrate_waitq_prepare_fn_t,sched_migrate_waitq_finish_fn_t,sched_migrate_vector_fn_t,sched_migrate_interrupt_fn_t,sched_migrate_void_fn_t,sched_migrate_log_fn_t);
int sched_request_migrate_body_result(int id,unsigned long cpu,unsigned long req,unsigned long ent,unsigned long t,int this_id,int status,unsigned int resched,unsigned int migrate,int running,int key,const struct sched_migrate_offsets *o,sched_migrate_spin_lock_fn_t lock,sched_migrate_spin_unlock_fn_t unlock,sched_migrate_noirq_lock_fn_t noirq_lock,sched_migrate_noirq_unlock_fn_t noirq_unlock,sched_migrate_waitq_init_fn_t init,sched_migrate_waitq_prepare_fn_t prepare,sched_migrate_waitq_finish_fn_t finish,sched_migrate_vector_fn_t vector,sched_migrate_interrupt_fn_t interrupt,sched_migrate_void_fn_t schedule,sched_migrate_log_fn_t log) {
 CHECK(id==target_id&&cpu==(unsigned long)&target&&req&&ent&&req%__alignof__(struct migrate_request)==0&&ent%__alignof__(waitq_entry_t)==0);
 CHECK(t==(mode==2?0:(unsigned long)&thread)&&this_id==current_id&&status==PS_UNINTERRUPTIBLE&&resched==CPU_FLAG_NEED_RESCHED&&migrate==CPU_FLAG_NEED_MIGRATE&&running==CPU_STATUS_RUNNING&&key==IHK_GV_IKC);
 const unsigned long *a=(const unsigned long *)o,*b=(const unsigned long *)&process_sched_migrate_offsets;
 for(unsigned i=0;i<sizeof(*o)/sizeof(*a);i++)CHECK(a[i]==b[i]);
 CHECK(lock&&unlock&&noirq_lock&&noirq_unlock);
 CHECK(init==process_sched_waitq_init_bridge&&prepare==process_sched_waitq_prepare_bridge&&finish==process_sched_waitq_finish_bridge&&vector==process_sched_vector_bridge&&interrupt==process_sched_interrupt_bridge&&schedule==process_sched_schedule_bridge&&log==process_sched_migrate_log_bridge);
 request=(struct migrate_request *)req;entry=(waitq_entry_t *)ent;
 CHECK(entry->link.next==&entry->link&&entry->link.prev==&entry->link&&entry->private==&current_thread&&!entry->flags&&entry->func==locked_wake_function);
 seen.provider++;event(4);
 seen.result=mode?leaf_sched_request_migrate_body_result(id,cpu,req,ent,t,this_id,status,resched,migrate,running,key,o,lock,unlock,noirq_lock,noirq_unlock,init,prepare,finish,vector,interrupt,schedule,log):return_value;
 return seen.result;
}
#include "original.c"
#include "actual-consumer.c"
extern const unsigned long LEAF_REQUEST_LAYOUT[12],LEAF_ENTRY_LAYOUT[6];
static void check_layout(void) {
 const unsigned long *a=(const unsigned long *)&process_sched_migrate_offsets;
 for(unsigned i=0;i<10;i++)CHECK(a[i]==LEAF_REQUEST_LAYOUT[i]);
 CHECK(LEAF_REQUEST_LAYOUT[10]==sizeof(struct migrate_request)&&LEAF_REQUEST_LAYOUT[11]==__alignof__(struct migrate_request));
 const unsigned long e[]={sizeof(waitq_entry_t),__alignof__(waitq_entry_t),__builtin_offsetof(waitq_entry_t,link),__builtin_offsetof(waitq_entry_t,private),__builtin_offsetof(waitq_entry_t,flags),__builtin_offsetof(waitq_entry_t,func)};
 for(unsigned i=0;i<6;i++)CHECK(e[i]==LEAF_ENTRY_LAYOUT[i]);
}
static void init(void) {
 zero(&target,sizeof(target));zero(&current,sizeof(current));zero(&thread,sizeof(thread));zero(&current_thread,sizeof(current_thread));zero(&seen,sizeof(seen));
 target.flags=initial_flags;target.status=-2147483647;current.current=&current_thread;current_thread.status=PS_RUNNING;
 target.migq.next=target.migq.prev=&target.migq;migq_locked=runq_locked=0;
}
static struct observation run(int rust,int tid,int cpuid) {
 init();thread.tid=tid;thread.cpu_id=cpuid;
 if(rust) { if(use_bridge)sched_request_migrate_bridge(target_id,mode==2?0:(unsigned long)&thread);else sched_request_migrate(target_id,mode==2?0:&thread); }else original_sched_request_migrate(target_id,mode==2?0:&thread);
 CHECK(seen.get_target==1&&seen.get_current==1&&seen.get_id==1&&seen.provider==1&&!migq_locked&&!runq_locked);
 CHECK(target.migq.next==&target.migq&&target.migq.prev==&target.migq);
 if(mode==1)CHECK(seen.init==1&&seen.prepare==1&&seen.finish==1&&seen.schedule==1&&seen.result==1&&seen.interrupt==(target_id!=current_id)&&seen.vector==seen.interrupt);
 else CHECK(!seen.init&&!seen.prepare&&!seen.finish&&!seen.schedule&&!seen.interrupt&&!seen.vector&&!seen.log&&seen.result==(mode==2?-22:return_value));
 seen.flags=target.flags;seen.status=target.status;return seen;
}
unsigned long leaf_fixture_run(void) {
 const int boundary[]={0,1,-1,(-2147483647-1),2147483647};const unsigned int flags[]={0,1,2,3,~0U};unsigned long n=0;
 check_layout();
 for(int a=0;a<5;a++)for(int b=0;b<5;b++)for(int t=0;t<5;t++)for(int c=0;c<5;c++)for(int f=0;f<5;f++)for(int m=0;m<12;m++) {
  target_id=boundary[a];current_id=boundary[b];initial_flags=flags[f];mode=m==0?1:(m==1?2:0);use_bridge=m&1;return_value=boundary[(m-2+10)%5];
  struct observation original=run(0,boundary[t],boundary[c]),rust=run(1,boundary[t],boundary[c]);
  const unsigned char *x=(const unsigned char *)&original,*y=(const unsigned char *)&rust;
  for(unsigned long i=0;i<sizeof(original);i++)CHECK(x[i]==y[i]);n++;
 }
 return n;
}
