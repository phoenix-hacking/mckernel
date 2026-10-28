/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE ONLY; actual original C/public Rust with real CPUSet/CPUlocal layouts.
 * IRQ/spinlock callbacks controlled; actual host-safe CPU_ISSET and atomic64 run.
 */
#include <process.h>
#include <cls.h>
#include <affinity.h>
#include <ihk/debug.h>
#include <string.h>
extern int printf(const char *,...);
extern int vsnprintf(char *,unsigned long,const char *,__builtin_va_list);
extern unsigned long f06_clone_cpu_Rust_ABI_fact(unsigned long);
extern int obtain_clone_cpuid(cpu_set_t *,int);
extern int num_processors;
ihk_spinlock_t runq_reservation_lock;
static struct cpu_local_var cpus[8];
struct event{unsigned long kind,a,b;};
struct observation{struct event e[64];unsigned int used,getters,outer_locks,outer_unlocks,inner_locks,inner_unlocks;char text[4096];unsigned long text_used;int result;unsigned long len[8],reserved[8];int status[8];};
static struct observation obs,old,new;
static int outer_held,inner_held;
static unsigned long vector_no;
static int pattern,use_last,debug_flags;
#define CHECK(x) do{if(!(x)){printf("FAIL clone_cpu line=%d vector=%lu\n",__LINE__,vector_no);return 1;}}while(0)
static void require(int x){if(!x)__builtin_trap();}
static void event(unsigned long kind,unsigned long a,unsigned long b){require(obs.used<64);obs.e[obs.used++]=(struct event){kind,a,b};}
struct cpu_local_var *fixture_clone_cpu(int i)
{require(outer_held && i>=0 && i<8);obs.getters++;event(3,(unsigned long)i,0);return &cpus[i];}
struct cpu_local_var *get_cpu_local_var(int i){return fixture_clone_cpu(i);}
unsigned long fixture_clone_lock(ihk_spinlock_t *l)
{require(l==&runq_reservation_lock && !outer_held && !inner_held);outer_held=1;obs.outer_locks++;event(1,0,0);return 0xface1234UL;}
void fixture_clone_unlock(ihk_spinlock_t *l,unsigned long irq)
{require(l==&runq_reservation_lock && outer_held && !inner_held && irq==0xface1234UL);obs.outer_unlocks++;event(2,0,irq);outer_held=0;}
static int lock_index(ihk_spinlock_t *l){for(int i=0;i<8;i++)if(l==&cpus[i].runq_lock)return i;__builtin_trap();}
void fixture_clone_noirq_lock(ihk_spinlock_t *l)
{require(outer_held && !inner_held);int i=lock_index(l);inner_held=1;obs.inner_locks++;event(4,i,0);}
void fixture_clone_noirq_unlock(ihk_spinlock_t *l)
{require(outer_held && inner_held);int i=lock_index(l);obs.inner_unlocks++;event(5,i,0);inner_held=0;}
int kprintf(const char *fmt,...)
{
 require(outer_held && inner_held);__builtin_va_list ap;__builtin_va_start(ap,fmt);
 int n=vsnprintf(obs.text+obs.text_used,sizeof(obs.text)-obs.text_used,fmt,ap);__builtin_va_end(ap);
 require(n>=0 && (unsigned long)n<sizeof(obs.text)-obs.text_used);obs.text_used+=(unsigned long)n;return n;
}
#undef ihk_mc_spinlock_lock
#undef ihk_mc_spinlock_unlock
#undef ihk_mc_spinlock_lock_noirq
#undef ihk_mc_spinlock_unlock_noirq
#define ihk_mc_spinlock_lock fixture_clone_lock
#define ihk_mc_spinlock_unlock fixture_clone_unlock
#define ihk_mc_spinlock_lock_noirq fixture_clone_noirq_lock
#define ihk_mc_spinlock_unlock_noirq fixture_clone_noirq_unlock
/* Baseline retains original __FUNCTION__/__func__/FILE/LINE in separate C TU. */
extern int original_C_obtain_clone_cpuid(cpu_set_t *,int);
extern struct ddebug __start___verbose[],__stop___verbose[];
static void reset(void)
{
 __builtin_memset(&obs,0,sizeof obs);__builtin_memset(cpus,0,sizeof cpus);outer_held=0;inner_held=0;
 for(int i=0;i<8;i++){
  cpus[i].status=i%4;
  switch(pattern){
   case 0:cpus[i].runq_len=0;cpus[i].runq_reserved=0;break;
   case 1:cpus[i].runq_len=i;break;
   case 2:cpus[i].runq_len=8-i;break;
   case 3:cpus[i].runq_len=i<2?7:3;break; /* old tie survives lower minimum */
   case 4:cpus[i].runq_len=0xffffffffUL;cpus[i].runq_reserved=i;break;
   case 5:cpus[i].runq_len=0xfffffffeUL;cpus[i].runq_reserved=i;break;
   case 6:cpus[i].runq_len=~0UL;cpus[i].runq_reserved=i;break;
  }
 }
 for(struct ddebug *d=__start___verbose;d<__stop___verbose;d++)d->flags=debug_flags;
}
static void save(struct observation *o,int result)
{
 require(!outer_held && !inner_held);obs.result=result;
 for(int i=0;i<8;i++){obs.len[i]=cpus[i].runq_len;obs.reserved[i]=cpus[i].runq_reserved;obs.status[i]=cpus[i].status;}*o=obs;
}
static int compare(cpu_set_t *mask)
{
 reset();save(&old,original_C_obtain_clone_cpuid(mask,use_last));
 reset();save(&new,obtain_clone_cpuid(mask,use_last));
 CHECK(memcmp(&old,&new,sizeof old)==0);
 CHECK(old.outer_locks==1 && old.outer_unlocks==1 && old.inner_locks==old.inner_unlocks);
 /* No candidate may manufacture fallback-to-min when use_last has no tie. */
 if(num_processors==1 && CPU_ISSET(0,mask) && use_last)CHECK(old.result==-1);
 return 0;
}
int main(void)
{
 const unsigned long facts[]={sizeof(cpu_set_t),sizeof(struct cpu_local_var),__alignof__(struct cpu_local_var),sizeof(ihk_spinlock_t),__builtin_offsetof(struct cpu_local_var,runq_lock),__builtin_offsetof(struct cpu_local_var,runq_len),__builtin_offsetof(struct cpu_local_var,runq_reserved),__builtin_offsetof(struct cpu_local_var,status)};
 for(unsigned long i=0;i<8;i++)CHECK(facts[i]==f06_clone_cpu_Rust_ABI_fact(i));
 CHECK(__stop___verbose-__start___verbose==4);
 for(num_processors=0;num_processors<=8;num_processors++)for(unsigned int bits=0;bits<(1U<<num_processors);bits++)for(pattern=0;pattern<7;pattern++)for(int last=-1;last<=1;last++)for(int debug=0;debug<3;debug++){
  cpu_set_t mask;CPU_ZERO(&mask);for(int i=0;i<num_processors;i++)if(bits&(1U<<i))CPU_SET(i,&mask);
  use_last=last;debug_flags=debug==0?0:debug==1?1:128;
  if(compare(&mask))return 1;vector_no++;
 }
 printf("PASS actual_C_public_Rust_obtain_clone_cpuid vectors=%lu real_ABI8=1 original_stale_tie_and_unsigned_truncation=1 controlled_IRQ_spin=1 actual_atomic64=1\n",vector_no);
 return vector_no==32193?0:2;
}
