/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Real structures and byteexact original C bodies. External CPU/IRQ/signal/timer
 * effects controlled; real selected Rust arithmetic. No actual IRQ or timers. */
#include <types.h>
#include <process.h>
#include <cls.h>
#include <syscall.h>
#include <time.h>
#include <rusage.h>
#include <ihk/monitor.h>
#include <string.h>
#ifndef offsetof
#define offsetof(t,m) __builtin_offsetof(t,m)
#endif
extern int printf(const char*,...);
extern void abort(void);
extern size_t fixture_rust_layout(size_t*);
static unsigned long case_id;static int which;
#define CHECK(x) do{if(!(x)){printf("FAIL case=%lu implementation=%d line=%d predicate=%s\n",case_id,which,__LINE__,#x);abort();}}while(0)
static void bytes_clear(void*p,size_t n){unsigned char*d=p;for(size_t i=0;i<n;i++)d[i]=0;}
static void bytes_copy(void*d0,const void*s0,size_t n){unsigned char*d=d0;const unsigned char*s=s0;for(size_t i=0;i<n;i++)d[i]=s[i];}
/* Known hosted-only kernel string macro ABI providers; not compute product code. */
void *__inline_memset(void*p,unsigned long value,size_t n){unsigned char*d=p;for(size_t i=0;i<n;i++)d[i]=(unsigned char)value;return p;}
void *__inline_memcpy(void*d,const void*s,size_t n){bytes_copy(d,s,n);return d;}
struct cpu_local_var *clv;
int gettime_local_support;
struct tod_data_s tod_data;
static struct thread fixture_thread;
static struct process fixture_process;
static struct cpu_local_var fixture_cpu;
static struct ihk_os_cpu_monitor fixture_monitor;
static struct rusage_percpu fixture_usage;
static unsigned long next_tsc,irq_token;
static int irq_disabled,mutation,signal_count,disable_count,restore_count,timer_count;
static long kill_return;
struct event {unsigned long kind;unsigned long args[23];};
static struct event events[32];static size_t nevents;
static void record(int kind){
 CHECK(nevents<32);struct event*e=&events[nevents++];e->kind=kind;
 e->args[0]=irq_disabled;e->args[1]=fixture_thread.base_tsc;e->args[2]=fixture_thread.user_tsc;e->args[3]=fixture_thread.system_tsc;
 e->args[4]=fixture_thread.times_update;e->args[5]=fixture_thread.in_kernel;e->args[6]=fixture_thread.itimer_enabled;
 e->args[7]=fixture_thread.itimer_virtual_value.tv_sec;e->args[8]=fixture_thread.itimer_virtual_value.tv_nsec;
 e->args[9]=fixture_thread.itimer_prof_value.tv_sec;e->args[10]=fixture_thread.itimer_prof_value.tv_nsec;
 e->args[11]=fixture_thread.itimer_virtual.it_value.tv_sec;e->args[12]=fixture_thread.itimer_virtual.it_value.tv_usec;
 e->args[13]=fixture_thread.itimer_prof.it_value.tv_sec;e->args[14]=fixture_thread.itimer_prof.it_value.tv_usec;
 e->args[15]=fixture_monitor.status;e->args[16]=fixture_monitor.counter;e->args[17]=fixture_usage.user_tsc;e->args[18]=fixture_usage.system_tsc;
 e->args[19]=(unsigned long)fixture_cpu.current;e->args[20]=next_tsc;e->args[21]=mutation;e->args[22]=signal_count;
}
struct cpu_local_var *get_this_cpu_local_var(void){record(1);return &fixture_cpu;}
unsigned long fixture_disable_irq(void){CHECK(!irq_disabled);record(2);irq_disabled=1;disable_count++;return irq_token;}
void fixture_restore_irq(unsigned long flags){CHECK(irq_disabled&&flags==irq_token);record(7);irq_disabled=0;restore_count++;}
unsigned long fixture_rdtsc(void){CHECK(irq_disabled);record(3);return next_tsc;}
void fixture_set_timer(int runq_locked){CHECK(irq_disabled&&runq_locked==0&&!fixture_thread.itimer_enabled);CHECK(fixture_thread.itimer_virtual.it_value.tv_sec==0&&fixture_thread.itimer_virtual.it_value.tv_usec==0&&fixture_thread.itimer_prof.it_value.tv_sec==0&&fixture_thread.itimer_prof.it_value.tv_usec==0);record(6);timer_count++;}
long fixture_do_kill(void*thread,int pid,int tid,int sig,const void*info,int ptracecont){
 CHECK(thread==&fixture_thread&&pid==fixture_process.pid&&tid==fixture_thread.tid&&!info&&!ptracecont&&irq_disabled);
 CHECK(sig==SIGVTALRM||sig==SIGPROF);record(sig==SIGVTALRM?4:5);signal_count++;
 if(sig==SIGVTALRM&&mutation==1){fixture_thread.itimer_prof.it_value.tv_sec=0;fixture_thread.itimer_prof.it_value.tv_usec=0;}
 if(sig==SIGVTALRM&&mutation==2){fixture_thread.itimer_prof.it_value.tv_sec=0;fixture_thread.itimer_prof.it_value.tv_usec=1;fixture_thread.itimer_prof_value.tv_sec=2;fixture_thread.itimer_prof_value.tv_nsec=0;}
 return kill_return;
}
#undef cpu_disable_interrupt_save
#undef cpu_restore_interrupt
#undef rdtsc
#undef do_kill
#undef set_timer
#define cpu_disable_interrupt_save fixture_disable_irq
#define cpu_restore_interrupt fixture_restore_irq
#define rdtsc fixture_rdtsc
#define do_kill fixture_do_kill
#define set_timer fixture_set_timer
#define reset_cputime original_reset_cputime
#define set_cputime original_set_cputime
#include "cputime.ORIGINAL-C.inc"
#undef set_cputime
#undef reset_cputime
#undef set_timer
#undef do_kill
#undef rdtsc
#undef cpu_restore_interrupt
#undef cpu_disable_interrupt_save
/* Actual Rust exports retain the public original ABI. */
extern void reset_cputime(void);
extern void set_cputime(enum set_cputime_mode mode);
static void init(void){
 bytes_clear(&fixture_thread,sizeof(fixture_thread));bytes_clear(&fixture_process,sizeof(fixture_process));bytes_clear(&fixture_cpu,sizeof(fixture_cpu));bytes_clear(&fixture_monitor,sizeof(fixture_monitor));bytes_clear(&fixture_usage,sizeof(fixture_usage));bytes_clear(&tod_data,sizeof(tod_data));bytes_clear(events,sizeof(events));
 clv=&fixture_cpu;fixture_cpu.current=&fixture_thread;fixture_cpu.monitor=&fixture_monitor;fixture_cpu.rusage=&fixture_usage;fixture_thread.proc=&fixture_process;
 fixture_process.pid=4321;fixture_thread.tid=8765;fixture_thread.status=0x1357;fixture_monitor.status=99;fixture_monitor.status_bak=0x2468;fixture_monitor.ocounter=0xdeadbeef;
 fixture_monitor.counter=~0UL;fixture_thread.times_update=17;fixture_thread.in_kernel=23;fixture_thread.base_tsc=10;fixture_thread.user_tsc=~0UL-3;fixture_thread.system_tsc=~0UL-7;fixture_usage.user_tsc=~0UL-11;fixture_usage.system_tsc=~0UL-15;
 gettime_local_support=1;tod_data.clocks_per_sec=1000000000UL;next_tsc=10;irq_token=0x24681357;irq_disabled=mutation=signal_count=disable_count=restore_count=timer_count=0;kill_return=0;nevents=0;
}
/* Compare initialized scalar projections and ordered effects, never structure padding. */
struct snapshot {unsigned long state[35];struct event events[32];unsigned long n,signals,disables,restores,timers,irq;};
static struct snapshot reference,candidate;
static void save(struct snapshot*s){bytes_clear(s,sizeof(*s));unsigned long state[]={(unsigned long)clv,(unsigned long)fixture_cpu.current,(unsigned long)fixture_cpu.monitor,(unsigned long)fixture_cpu.rusage,fixture_cpu.idle.base_tsc,fixture_thread.base_tsc,fixture_thread.user_tsc,fixture_thread.system_tsc,fixture_thread.times_update,fixture_thread.in_kernel,fixture_thread.itimer_enabled,fixture_thread.itimer_virtual.it_value.tv_sec,fixture_thread.itimer_virtual.it_value.tv_usec,fixture_thread.itimer_virtual.it_interval.tv_sec,fixture_thread.itimer_virtual.it_interval.tv_usec,fixture_thread.itimer_prof.it_value.tv_sec,fixture_thread.itimer_prof.it_value.tv_usec,fixture_thread.itimer_prof.it_interval.tv_sec,fixture_thread.itimer_prof.it_interval.tv_usec,fixture_thread.itimer_virtual_value.tv_sec,fixture_thread.itimer_virtual_value.tv_nsec,fixture_thread.itimer_prof_value.tv_sec,fixture_thread.itimer_prof_value.tv_nsec,(unsigned long)fixture_thread.proc,fixture_thread.tid,fixture_thread.status,fixture_process.pid,fixture_monitor.status,fixture_monitor.status_bak,fixture_monitor.counter,fixture_monitor.ocounter,fixture_usage.user_tsc,fixture_usage.system_tsc,gettime_local_support,tod_data.clocks_per_sec};bytes_copy(s->state,state,sizeof(state));bytes_copy(s->events,events,sizeof(events));s->n=nevents;s->signals=signal_count;s->disables=disable_count;s->restores=restore_count;s->timers=timer_count;s->irq=irq_disabled;CHECK(!irq_disabled&&disable_count==restore_count);}
static void equivalent(void){if(memcmp(&reference,&candidate,sizeof(reference))){printf("MISMATCH case=%lu C_events=%lu Rust_events=%lu C_signals=%lu Rust_signals=%lu\n",case_id,reference.n,candidate.n,reference.signals,candidate.signals);for(size_t i=0;i<35;i++)if(reference.state[i]!=candidate.state[i])printf("state%lu C=%lu Rust=%lu\n",i,reference.state[i],candidate.state[i]);for(size_t i=0;i<reference.n||i<candidate.n;i++)printf("event%lu C_kind=%lu Rust_kind=%lu\n",i,reference.events[i].kind,candidate.events[i].kind);abort();}}
static void abi_check(void){size_t actual[64],expected[]={sizeof(struct thread),_Alignof(struct thread),offsetof(struct thread,base_tsc),offsetof(struct thread,user_tsc),offsetof(struct thread,system_tsc),offsetof(struct thread,times_update),offsetof(struct thread,in_kernel),offsetof(struct thread,itimer_enabled),offsetof(struct thread,itimer_virtual),offsetof(struct thread,itimer_prof),offsetof(struct thread,itimer_virtual_value),offsetof(struct thread,itimer_prof_value),offsetof(struct thread,proc),offsetof(struct thread,tid),sizeof(struct cpu_local_var),_Alignof(struct cpu_local_var),offsetof(struct cpu_local_var,current),offsetof(struct cpu_local_var,idle),offsetof(struct cpu_local_var,monitor),offsetof(struct cpu_local_var,rusage),sizeof(struct ihk_os_cpu_monitor),_Alignof(struct ihk_os_cpu_monitor),offsetof(struct ihk_os_cpu_monitor,status),offsetof(struct ihk_os_cpu_monitor,status_bak),offsetof(struct ihk_os_cpu_monitor,counter),offsetof(struct ihk_os_cpu_monitor,ocounter),sizeof(struct rusage_percpu),_Alignof(struct rusage_percpu),offsetof(struct rusage_percpu,user_tsc),offsetof(struct rusage_percpu,system_tsc),sizeof(struct process),_Alignof(struct process),offsetof(struct process,pid),sizeof(struct itimerval),_Alignof(struct itimerval),offsetof(struct itimerval,it_interval),offsetof(struct itimerval,it_value),sizeof(struct timespec),_Alignof(struct timespec),offsetof(struct timespec,tv_sec),offsetof(struct timespec,tv_nsec),sizeof(struct timeval),_Alignof(struct timeval),offsetof(struct timeval,tv_sec),offsetof(struct timeval,tv_usec),sizeof(struct tod_data_s),_Alignof(struct tod_data_s),offsetof(struct tod_data_s,clocks_per_sec)};CHECK(fixture_rust_layout(actual)==sizeof(expected)/sizeof(expected[0]));for(size_t i=0;i<sizeof(expected)/sizeof(expected[0]);i++)if(actual[i]!=expected[i]){printf("ABI_MISMATCH index=%lu C=%lu Rust=%lu\n",i,expected[i],actual[i]);abort();}}
static void timer_pattern(int pattern){
 fixture_thread.itimer_enabled=pattern!=0;
 fixture_thread.itimer_virtual_value.tv_sec=1;fixture_thread.itimer_prof_value.tv_sec=1;
 if(pattern>=2){fixture_thread.itimer_virtual.it_value.tv_sec=1;fixture_thread.itimer_virtual.it_value.tv_usec=pattern==2?1:0;}
 if(pattern==4||pattern==8){fixture_thread.itimer_virtual_value.tv_nsec=1000;}
 if(pattern==5){fixture_thread.itimer_virtual.it_value.tv_sec=0;fixture_thread.itimer_prof.it_value.tv_usec=1;}
 if(pattern==6||pattern==8){fixture_thread.itimer_virtual.it_value.tv_usec=1;fixture_thread.itimer_prof.it_value.tv_usec=1;fixture_thread.itimer_virtual_value.tv_sec=2;fixture_thread.itimer_prof_value.tv_sec=2;}
 if(pattern==6){fixture_thread.itimer_virtual.it_interval.tv_usec=11;fixture_thread.itimer_prof.it_interval.tv_usec=13;}
 if(pattern==7){fixture_thread.itimer_virtual.it_value.tv_sec=0;fixture_thread.itimer_virtual.it_value.tv_usec=1;fixture_thread.itimer_prof.it_value.tv_sec=3;}
 if(pattern==9){fixture_thread.itimer_virtual.it_value.tv_sec=0;fixture_thread.itimer_virtual.it_value.tv_usec=1;fixture_thread.itimer_virtual_value.tv_sec=0;fixture_thread.itimer_virtual_value.tv_nsec=999;}
}
int main(void){
 abi_check();unsigned long resets=0,sets=0;
 for(int owner=0;owner<4;owner++)for(int base=0;base<3;base++){
  case_id++;for(which=0;which<2;which++){init();fixture_thread.base_tsc=base==0?0:base==1?10:~0UL;fixture_cpu.idle.base_tsc=77;if(owner==0)clv=0;if(owner==1)fixture_cpu.current=0;if(owner==2)fixture_cpu.current=&fixture_cpu.idle;
   if(which)reset_cputime();else original_reset_cputime();CHECK(nevents==(owner==0?0:1));CHECK(!disable_count&&!signal_count&&!timer_count);if(owner==3)CHECK(fixture_thread.base_tsc==0);else CHECK(fixture_thread.base_tsc==(base==0?0:base==1?10:~0UL));if(owner==2)CHECK(fixture_cpu.idle.base_tsc==0);save(which?&candidate:&reference);
  }equivalent();resets++;
 }
 const int modes[]={0,1,2,3,-1,2147483647};const unsigned long bases[]={0,10,~0UL-25};const unsigned long clocks[]={0,10,1000000010};
 for(int owner=0;owner<3;owner++){case_id++;for(which=0;which<2;which++){init();if(owner==0)clv=0;if(owner==1)fixture_cpu.current=0;if(owner==2)fixture_cpu.current=&fixture_cpu.idle;if(which)set_cputime(CPUTIME_MODE_U2K);else original_set_cputime(CPUTIME_MODE_U2K);CHECK(nevents==(owner==0?0:1)&&!disable_count&&!signal_count&&!timer_count&&fixture_monitor.counter==~0UL&&fixture_monitor.status==99);save(which?&candidate:&reference);}equivalent();sets++;}
 for(int mode=0;mode<6;mode++)for(int local=0;local<2;local++)for(int base=0;base<3;base++)for(int clock=0;clock<3;clock++)for(int pattern=0;pattern<10;pattern++)for(int mutate=0;mutate<3;mutate++){
  case_id++;for(which=0;which<2;which++){init();gettime_local_support=local;fixture_thread.base_tsc=bases[base];next_tsc=clocks[clock];mutation=mutate;kill_return=mutate==0?0:mutate==1?-777:123;timer_pattern(pattern);
   if(which)set_cputime((enum set_cputime_mode)modes[mode]);else original_set_cputime((enum set_cputime_mode)modes[mode]);
   CHECK(fixture_monitor.status==(mode==0?IHK_OS_MONITOR_USER:mode==1?IHK_OS_MONITOR_KERNEL:99));CHECK(fixture_monitor.counter==(mode==1?0:~0UL));CHECK(fixture_thread.times_update==1);
   if(!local){CHECK(disable_count==0&&restore_count==0&&signal_count==0&&timer_count==0&&fixture_thread.base_tsc==bases[base]&&fixture_thread.in_kernel==23);}
   else{CHECK(disable_count==1&&restore_count==1&&fixture_thread.base_tsc==next_tsc&&fixture_thread.in_kernel==modes[mode]);}
   if(local&&base==0&&pattern==3)CHECK(signal_count==0); /* equal deadline does not expire */
   CHECK(fixture_thread.status==0x1357&&fixture_process.pid==4321&&fixture_monitor.status_bak==0x2468&&fixture_monitor.ocounter==0xdeadbeef);
   save(which?&candidate:&reference);
  }equivalent();sets++;
 }
 CHECK(resets==12&&sets==3243);printf("PASS_F03_ACTUAL_C_RUST_CPUTIME reset=%lu set=%lu total=%lu real_layout_fields=48 controlled_OS_effects_only=1\n",resets,sets,resets+sets);return 0;
}
