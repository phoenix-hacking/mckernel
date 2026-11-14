/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Existing25750assertion oracle using genuine current structures and Rust storage. */
#include <process.h>
#include <cpulocal.h>
#include <cls.h>
#include <timer.h>
#include <sched_helpers.h>
#include <string.h>
extern int printf(const char *,...);
extern void exit(int);
#ifndef INT_MIN
#define INT_MIN (-2147483647-1)
#endif
#ifndef INT_MAX
#define INT_MAX 2147483647
#endif
#define list list_head
extern const struct timer_runtime_offsets process_timer_runtime_offsets;
#define PROCESS_SCHED_PUBLIC_BRIDGE
PROCESS_SCHED_PUBLIC_BRIDGE const struct timer_runtime_offsets reference_process_timer_runtime_offsets = {
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_sched_list_offset = __builtin_offsetof(struct thread, sched_list),
	.thread_spin_sleep_lock_offset =
		__builtin_offsetof(struct thread, spin_sleep_lock),
	.thread_spin_sleep_offset = __builtin_offsetof(struct thread, spin_sleep),
	.thread_itimer_enabled_offset =
		__builtin_offsetof(struct thread, itimer_enabled),
	.cpu_runq_lock_offset = __builtin_offsetof(struct cpu_local_var, runq_lock),
	.cpu_runq_offset = __builtin_offsetof(struct cpu_local_var, runq),
	.cpu_runq_len_offset = __builtin_offsetof(struct cpu_local_var, runq_len),
	.cpu_current_offset = __builtin_offsetof(struct cpu_local_var, current),
	.cpu_timer_enabled_offset =
		__builtin_offsetof(struct cpu_local_var, timer_enabled),
	.cpu_backlog_list_offset =
		__builtin_offsetof(struct cpu_local_var, backlog_list),
	.timer_timeout_offset = __builtin_offsetof(struct timer, timeout),
	.timer_waitq_offset = __builtin_offsetof(struct timer, processes),
	.timer_list_offset = __builtin_offsetof(struct timer, list),
	.timer_thread_offset = __builtin_offsetof(struct timer, thread),
};
int time_sharing;
static struct cpu_local_var cpu;
static struct thread threads[4];
static struct list backlog;
static struct cpu_local_var *current_cpu;
static int mode, return_value, mutate_sharing;
struct observation { unsigned long cpu, offsets, lock, unlock, enable, disable;
 int sharing, locked, result, getter_calls, provider_calls, events[8], event_count, final_timer;
 unsigned long lock_addr, irqstate; };
static struct observation seen;
#define CHECK(x) do { if (!(x)) { printf("line=%d failed=%s\n",__LINE__,#x); exit(1); } } while(0)
static void event(int v) { CHECK(seen.event_count<8); seen.events[seen.event_count++]=v; }
struct cpu_local_var *get_this_cpu_local_var(void) {
 seen.getter_calls++; event(1); if(mutate_sharing) time_sharing=mutate_sharing; return current_cpu;
}
unsigned long process_timer_spin_lock_bridge(unsigned long addr) {
 CHECK(addr==(unsigned long)&cpu.runq_lock); seen.lock_addr=addr; event(3); return ~0UL-17;
}
void process_timer_spin_unlock_bridge(unsigned long addr, unsigned long irqstate) {
 CHECK(addr==(unsigned long)&cpu.runq_lock && irqstate==~0UL-17);
 seen.irqstate=irqstate; event(6);
}
void process_timer_lapic_enable_bridge(unsigned int clocks) { CHECK(clocks==1000000); event(4); }
void process_timer_lapic_disable_bridge(void) { event(5); }
typedef unsigned long (*lock_fn)(unsigned long);
typedef void (*unlock_fn)(unsigned long,unsigned long);
typedef void (*enable_fn)(unsigned int);
typedef void (*disable_fn)(void);
extern int leaf_timer_set_timer_body_result(unsigned long,int,int,const struct timer_runtime_offsets *,lock_fn,unlock_fn,enable_fn,disable_fn);
int timer_set_timer_body_result(unsigned long p,int sharing,int locked,
 const struct timer_runtime_offsets *off,lock_fn lock,unlock_fn unlock,enable_fn enable,disable_fn disable) {
 seen.provider_calls++; event(2); seen.cpu=p; seen.sharing=sharing; seen.locked=locked;
 seen.offsets=(unsigned long)off; seen.lock=(unsigned long)lock; seen.unlock=(unsigned long)unlock;
 seen.enable=(unsigned long)enable; seen.disable=(unsigned long)disable;
 CHECK(off==&process_timer_runtime_offsets && lock==process_timer_spin_lock_bridge &&
 unlock==process_timer_spin_unlock_bridge && enable==process_timer_lapic_enable_bridge && disable==process_timer_lapic_disable_bridge);
 seen.result=mode ? leaf_timer_set_timer_body_result(p,sharing,locked,off,lock,unlock,enable,disable):return_value;
 return seen.result;
}
#include "original.c"
extern void set_timer(int);
static void init(int sharing,int n,int status_bits,int spin,int timer,int itimer,int pending,int null_current,int null_cpu) {
 memset(&cpu,0,sizeof(cpu)); memset(threads,0,sizeof(threads)); memset(&seen,0,sizeof(seen));
 cpu.runq.next=cpu.runq.prev=&cpu.runq; cpu.backlog_list.next=cpu.backlog_list.prev=&cpu.backlog_list;
 for(int i=0;i<n;i++) { struct list *entry=&threads[i].sched_list;
  threads[i].status=(status_bits&(1<<i))?1:2; threads[i].spin_sleep=spin;
  entry->next=&cpu.runq; entry->prev=cpu.runq.prev; entry->prev->next=entry; cpu.runq.prev=entry; }
 cpu.current=null_current?NULL:&threads[3]; threads[3].itimer_enabled=itimer;
 cpu.timer_enabled=timer;
 if(pending) { cpu.backlog_list.next=cpu.backlog_list.prev=&backlog; backlog.next=backlog.prev=&cpu.backlog_list; }
 current_cpu=null_cpu?NULL:&cpu; time_sharing=sharing;
}
static void pair(int sharing,int locked,int n,int status_bits,int spin,int timer,int itimer,int pending,int null_current,int null_cpu) {
 init(sharing,n,status_bits,spin,timer,itimer,pending,null_current,null_cpu);
 original_set_timer(locked); seen.final_timer=cpu.timer_enabled; struct observation original=seen;
 init(sharing,n,status_bits,spin,timer,itimer,pending,null_current,null_cpu);
 set_timer(locked); seen.final_timer=cpu.timer_enabled;
 CHECK(memcmp(&original,&seen,sizeof(seen))==0);
 CHECK(seen.getter_calls==1 && seen.provider_calls==1 && seen.events[0]==1 && seen.events[1]==2);
 CHECK(seen.cpu==(unsigned long)current_cpu && seen.sharing==time_sharing && seen.locked==locked);
 if(mode) {
  int effective_sharing=mutate_sharing?mutate_sharing:sharing;
  if(!effective_sharing) CHECK(seen.result==0 && seen.event_count==2 && seen.final_timer==timer);
  else if(null_cpu) CHECK(seen.result==-22 && seen.event_count==2);
  else { int running=0; for(int i=0;i<n;i++) running+=((status_bits&(1<<i))!=0)||spin;
   int should_enable=running>1||(!null_current&&itimer)||pending;
   CHECK(seen.result==running && seen.final_timer==!!should_enable);
   CHECK((seen.lock_addr!=0)==(locked==0));
  }
 }
}
int main(void) {
 CHECK(sizeof(process_timer_runtime_offsets)==120 && __alignof__(process_timer_runtime_offsets)==8);
 CHECK(memcmp(&process_timer_runtime_offsets,&reference_process_timer_runtime_offsets,120)==0);
 const int values[]={0,1,-1,INT_MIN,INT_MAX}; unsigned long cases=0;
 mode=1;
 for(int s=0;s<5;s++) for(int l=0;l<5;l++) for(int n=0;n<4;n++)
 for(int bits=0;bits<8;bits++) for(int flags=0;flags<32;flags++) {
  pair(values[s],values[l],n,bits,flags&1,(flags>>1)&1,(flags>>2)&1,(flags>>3)&1,(flags>>4)&1,0); cases++;
 }
 for(int s=0;s<5;s++) for(int l=0;l<5;l++) { pair(values[s],values[l],0,0,0,1,0,0,1,1); cases++; }
 mode=0;
 for(int r=0;r<5;r++) for(int s=0;s<5;s++) for(int l=0;l<5;l++) {
  return_value=values[r]; mutate_sharing=values[(s+1)%5];
  pair(values[s],values[l],0,0,0,1,0,0,1,0); cases++;
 }
 printf("PASS original-C/actual-Rust wrapper pairs=%lu; real existing Rust timer semantics plus callback/descriptor/ordering and ignored-return checks\n",cases);
 return 0;
}
