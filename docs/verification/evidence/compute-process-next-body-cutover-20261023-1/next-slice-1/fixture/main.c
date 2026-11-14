/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Explicit host state model; no target lock/IRQ/CPU instructions are executed. */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include "runqueue-offsets.h"
struct list { struct list *next,*prev; };
struct sig_common { struct list sigpending; };
struct process { int pid,status; unsigned long update_lock; int clone_count; };
struct thread { int cpu_id,tid,status; unsigned long spin_sleep_lock; int spin_sleep;
 struct list sched_list,sigpending; struct sig_common *sigcommon; struct process *proc; int mod_clone; };
struct cpu_local_var { unsigned long runq_lock,runq_irqstate; struct thread *current; int prevpid;
 struct list runq; unsigned long runq_len; int runq_reserved; unsigned int flags; int status,in_interrupt; unsigned long nr_ctx_switches; };
#define O(t,f) offsetof(struct t,f)
static const struct sched_runqueue_offsets process_sched_runqueue_offsets = {
 O(thread,cpu_id),O(thread,tid),O(thread,status),O(thread,spin_sleep_lock),O(thread,spin_sleep),O(thread,sched_list),
 O(thread,sigpending),O(thread,sigcommon),O(sig_common,sigpending),O(thread,proc),O(thread,mod_clone),O(process,pid),
 O(process,status),O(process,update_lock),O(process,clone_count),O(cpu_local_var,runq_lock),O(cpu_local_var,runq_irqstate),
 O(cpu_local_var,current),O(cpu_local_var,prevpid),O(cpu_local_var,runq),O(cpu_local_var,runq_len),O(cpu_local_var,runq_reserved),
 O(cpu_local_var,flags),O(cpu_local_var,status),O(cpu_local_var,in_interrupt),O(cpu_local_var,nr_ctx_switches)
};
int idle_halt;
static struct cpu_local_var cpu;
static struct thread thread;
static struct sig_common common;
static struct list pending_node;
static int cpu_id,has_signal,wake_after,late_resched,mode,return_value;
struct event { unsigned long code,a,b; int x,y; };
struct observation { int getters,cpuid,provider,result,schedule,pauses,zeroes,signal_calls,event_count;
 unsigned long thread_addr,cpu_addr; int id,halt; unsigned int need;
 unsigned char offsets[sizeof(struct sched_runqueue_offsets)]; struct event events[80];
 int final_spin; unsigned int final_flags; };
static struct observation seen;
static int irq_disabled,noirq_locked,spin_locked;
static unsigned long held_spin;
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"line=%d failed=%s\n",__LINE__,#x); exit(1); } } while(0)
static void event(unsigned long code,unsigned long a,unsigned long b,int x,int y) {
 CHECK(seen.event_count<80); seen.events[seen.event_count++]=(struct event){code,a,b,x,y};
}
struct cpu_local_var *get_this_cpu_local_var(void) { seen.getters++; return &cpu; }
int ihk_mc_get_processor_id(void) { seen.cpuid++; return cpu_id; }
#define ihk_ikc_get_processor_id ihk_mc_get_processor_id
#define CPU_FLAG_NEED_RESCHED 1u
unsigned long process_sched_irq_save_bridge(void) { CHECK(!irq_disabled); irq_disabled=1; event(1,0,0,0,0); return ~0UL-31; }
void process_sched_irq_restore_bridge(unsigned long s) { CHECK(irq_disabled&&!noirq_locked&&s==~0UL-31);irq_disabled=0;event(4,s,0,0,0); }
unsigned long process_spin_lock_bridge(unsigned long p) { CHECK(!spin_locked);CHECK(p==(unsigned long)&thread.spin_sleep_lock||p==(unsigned long)&cpu.runq_lock);spin_locked=1;held_spin=p;event(5,p,0,0,0);return ~(p^0x12345678UL); }
void process_spin_unlock_bridge(unsigned long p,unsigned long s) { CHECK(spin_locked&&held_spin==p&&s==~(p^0x12345678UL));spin_locked=0;event(6,p,s,0,0); }
void process_sched_noirq_lock_bridge(unsigned long p) { CHECK(irq_disabled&&!noirq_locked&&p==(unsigned long)&cpu.runq_lock);noirq_locked=1;event(2,p,0,0,0); }
void process_sched_noirq_unlock_bridge(unsigned long p) { CHECK(irq_disabled&&noirq_locked&&p==(unsigned long)&cpu.runq_lock);noirq_locked=0;event(3,p,0,0,0); }
void process_sched_schedule_bridge(void) { CHECK(!irq_disabled&&!spin_locked&&!noirq_locked);seen.schedule++;event(7,0,0,0,0); }
void process_sched_zero_free_bridge(void) { CHECK(!irq_disabled&&!spin_locked&&!noirq_locked);seen.zeroes++;event(8,0,0,0,0); }
void process_sched_pause_bridge(void) { CHECK(seen.zeroes==seen.pauses+1);seen.pauses++;CHECK(seen.pauses<=3);event(9,0,0,0,0);if(seen.pauses==wake_after) { if(late_resched)cpu.flags|=1;else thread.spin_sleep=0; } }
int process_sched_has_signal_bridge(unsigned long p) { CHECK(p==(unsigned long)&thread);seen.signal_calls++;event(10,p,0,0,0);return has_signal; }
void process_sched_runq_log_bridge(int e,unsigned long a,unsigned long b,int x,int y) { CHECK(a==(unsigned long)&thread&&b==(unsigned long)&cpu&&x==thread.tid);event(20+e,a,b,x,y); }
typedef unsigned long (*irq_fn)(void);
typedef void (*restore_fn)(unsigned long);
typedef unsigned long (*lock_fn)(unsigned long);
typedef void (*unlock_fn)(unsigned long,unsigned long);
typedef void (*noirq_fn)(unsigned long);
typedef void (*void_fn)(void);
typedef int (*signal_fn)(unsigned long);
typedef void (*log_fn)(int,unsigned long,unsigned long,int,int);
extern int leaf_spin_sleep_or_schedule_body_result(unsigned long,unsigned long,int,int,unsigned int,const struct sched_runqueue_offsets *,irq_fn,restore_fn,lock_fn,unlock_fn,noirq_fn,noirq_fn,void_fn,void_fn,void_fn,signal_fn,log_fn);
int sched_spin_sleep_or_schedule_body_result(unsigned long t,unsigned long c,int id,int halt,unsigned int need,const struct sched_runqueue_offsets *off,irq_fn irq,restore_fn restore,lock_fn lock,unlock_fn unlock,noirq_fn nl,noirq_fn nu,void_fn schedule,void_fn zero,void_fn pause,signal_fn signal,log_fn log) {
 seen.provider++;seen.thread_addr=t;seen.cpu_addr=c;seen.id=id;seen.halt=halt;seen.need=need;
 CHECK(off&&memcmp(off,&process_sched_runqueue_offsets,sizeof(*off))==0);memcpy(seen.offsets,off,sizeof(*off));
 CHECK(irq==process_sched_irq_save_bridge&&restore==process_sched_irq_restore_bridge&&schedule==process_sched_schedule_bridge&&zero==process_sched_zero_free_bridge&&pause==process_sched_pause_bridge&&signal==process_sched_has_signal_bridge&&log==process_sched_runq_log_bridge);
 CHECK(lock&&unlock&&nl&&nu); /* actualRust reuses its already-established4typed adapters */
 seen.result=mode?leaf_spin_sleep_or_schedule_body_result(t,c,id,halt,need,off,irq,restore,lock,unlock,nl,nu,schedule,zero,pause,signal,log):return_value;
 return seen.result;
}
#include "original.c"
extern void spin_sleep_or_schedule(void);
extern void futex_wait_schedule_direct_bridge(void);
static unsigned long pair_index;
static void list_init(struct list *p) { p->next=p->prev=p; }
static void init(int halt,unsigned int flags,unsigned long len,int spin,int pending,int common_present,int null_thread) {
 memset(&seen,0,sizeof(seen));memset(&cpu,0,sizeof(cpu));memset(&thread,0,sizeof(thread));memset(&common,0,sizeof(common));
 irq_disabled=noirq_locked=spin_locked=0;held_spin=0;idle_halt=halt;cpu.current=null_thread?NULL:&thread;
 cpu.flags=flags;cpu.runq_len=len;thread.tid=INT_MIN+17;thread.spin_sleep=spin;
 list_init(&thread.sigpending);list_init(&common.sigpending);thread.sigcommon=common_present?&common:NULL;
 if(pending&1)thread.sigpending.next=&pending_node;
 if(pending&2)common.sigpending.next=&pending_node;
}
static void pair(int halt,unsigned int flags,unsigned long len,int spin,int pending,int common_present,int null_thread) {
 init(halt,flags,len,spin,pending,common_present,null_thread);original_spin_sleep_or_schedule();
 CHECK(!irq_disabled&&!noirq_locked&&!spin_locked);seen.final_spin=thread.spin_sleep;seen.final_flags=cpu.flags;struct observation original=seen;
 init(halt,flags,len,spin,pending,common_present,null_thread);
 if(pair_index++&1)futex_wait_schedule_direct_bridge();else spin_sleep_or_schedule();
 CHECK(!irq_disabled&&!noirq_locked&&!spin_locked);seen.final_spin=thread.spin_sleep;seen.final_flags=cpu.flags;
 CHECK(memcmp(&seen,&original,sizeof(seen))==0);CHECK(seen.getters==2&&seen.cpuid==1&&seen.provider==1);
 CHECK(seen.thread_addr==(unsigned long)cpu.current&&seen.cpu_addr==(unsigned long)&cpu&&seen.id==cpu_id&&seen.halt==halt&&seen.need==1);
 if(!mode) { CHECK(seen.result==return_value&&seen.event_count==0&&seen.final_spin==spin&&seen.final_flags==flags);return; }
 if(null_thread) { CHECK(seen.result==-22&&seen.event_count==0);return; }
 if(halt) { CHECK(seen.result==2&&seen.schedule==1&&seen.event_count==3&&seen.zeroes==0);return; }
 int resched=(flags&1)||len>1;int pending_signal=((pending&1)||((pending&2)&&common_present))&&has_signal;
 if(spin==0||pending_signal) { CHECK(seen.result==1&&seen.schedule==0&&seen.zeroes==0);CHECK(seen.final_flags==(resched?(flags|1):flags)); }
 else if(resched) { CHECK(seen.result==2&&seen.schedule==1&&seen.final_spin==0&&seen.final_flags==(flags&~1u)&&seen.zeroes==0); }
 else { CHECK(seen.zeroes==wake_after&&seen.pauses==wake_after&&seen.final_spin==0);CHECK(seen.result==(late_resched?2:1)&&seen.schedule==late_resched); }
}
int main(void) {
 const int boundary[]={0,1,-1,INT_MIN,INT_MAX};const unsigned int flags[]={0,1,2,UINT_MAX};unsigned long cases=0;
 mode=1;
 for(int h=0;h<5;h++)for(int id=0;id<5;id++)for(int f=0;f<4;f++)for(unsigned long len=0;len<3;len++)for(int sp=0;sp<3;sp++)for(int pending=0;pending<4;pending++)for(int sig=0;sig<3;sig++)for(int wake=1;wake<=3;wake++)for(int late=0;late<2;late++)for(int cp=0;cp<2;cp++) {
  cpu_id=boundary[id];has_signal=boundary[sig];wake_after=wake;late_resched=late;
  pair(boundary[h],flags[f],len,boundary[sp],pending,cp,0);cases++;
 }
 for(int h=0;h<5;h++)for(int id=0;id<5;id++) { cpu_id=boundary[id];pair(boundary[h],0,1,1,0,0,1);cases++; }
 mode=0;
 for(int r=0;r<5;r++)for(int h=0;h<5;h++)for(int id=0;id<5;id++) { return_value=boundary[r];cpu_id=boundary[id];pair(boundary[h],0,1,1,0,0,0);cases++; }
 printf("PASS original-selected-C/actual-Rust spin_sleep_or_schedule pairs=%lu; actual existing body/adapters/offset constructor; callback ordering/state and independent branch expectations\n",cases);
 return 0;
}
