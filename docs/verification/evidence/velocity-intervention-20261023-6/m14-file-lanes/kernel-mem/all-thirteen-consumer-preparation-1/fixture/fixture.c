/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * All13 exact original C providers versus actual candidate Rust providers; both
 * feed the unchanged actual Rust array/handler bodies using real header layouts.
 * CPU/interrupt/timestamp/flush/pause ISA endpoints controlled; real Rust atomic/spinlock modules. Completion is ONLY the actual
 * Rust handler -> atomic_dec path; neither interrupt return nor mock ACK clears it.
 */
#include "actual_kernel_declarations.h"
extern int printf(const char *,...);
extern void abort(void);
#define require(c) do{if(!(c)){printf("FAIL line=%d\n",__LINE__);return __LINE__;}}while(0)
extern int mem_tlb_current_cpu_bridge(void);
extern int mem_tlb_get_vector_bridge(int);
extern void mem_tlb_interrupt_cpu_bridge(int,int);
extern int mem_tlb_flush_handler_body_result(int,struct tlb_flush_entry*,int,int,unsigned long(*)(void),void(*)(unsigned long),void(*)(unsigned long),void(*)(void),void(*)(unsigned long));
struct tlb_flush_entry tlb_flush_vector[IHK_TLB_FLUSH_IRQ_VECTOR_SIZE];
const int mem_remote_tlb_geometry[3]={IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,IHK_TLB_FLUSH_IRQ_VECTOR_START,CPU_SETSIZE};
static struct process_vm vm;
static struct address_space aspace;
static unsigned long *addresses;
static unsigned long invalid_addresses[3]={1,2,3};
struct event {unsigned long code,a,b,c,d;};
static struct event trace[256],saved[256];
static unsigned n;
static int consumer_mode,current_cpu,provider_return,delay_delivery,lock_depth,original_mode;
static int queue[CPU_SETSIZE],queued,done;
static int interrupts,handlers,decrements,pauses;
static void event(unsigned long code,unsigned long a,unsigned long b,unsigned long c,unsigned long d)
{if(n>=256)abort();trace[n++]=(struct event){code,a,b,c,d};}
int ihk_mc_get_processor_id(void){event(1,current_cpu,0,0,0);return current_cpu;}
int ihk_mc_get_vector(enum ihk_mc_gv_type type){int result=consumer_mode?type:provider_return;event(2,type,result,0,0);return result;}
static unsigned long irq_save(void){event(13,0,0,0,0);return 0x55;}
static void irq_restore(unsigned long flags){if(flags!=0x55)abort();event(14,flags,0,0,0);}
extern unsigned long mem_tlb_rdtsc_bridge(void);
extern void mem_tlb_noirq_lock_bridge(unsigned long);
extern void mem_tlb_noirq_unlock_bridge(unsigned long);
extern void mem_tlb_atomic_set_bridge(unsigned long,int);
extern void mem_tlb_atomic_inc_bridge(unsigned long);
extern void mem_tlb_atomic_dec_bridge(unsigned long);
extern int mem_tlb_atomic_read_bridge(unsigned long);
extern void mem_tlb_flush_single_bridge(unsigned long);
extern void mem_tlb_flush_all_bridge(void);
extern void mem_tlb_pause_bridge(void);
void preempt_disable(void){++lock_depth;event(5,lock_depth,0,0,0);}
void preempt_enable(void){event(6,lock_depth,0,0,0);--lock_depth;if(lock_depth<0)abort();}
void flush_tlb_single(unsigned long addr){event(10,addr,0,0,0);}
void flush_tlb(void){event(11,0,0,0,0);}
#include "original-all13-providers.inc"
static void deliver(int vector)
{
 int slot=vector-IHK_TLB_FLUSH_IRQ_VECTOR_START;
 if(slot<0||slot>=IHK_TLB_FLUSH_IRQ_VECTOR_SIZE)abort();
 int before=ihk_atomic_read(&tlb_flush_vector[slot].pending);++handlers;
 int ret=mem_tlb_flush_handler_body_result(vector,tlb_flush_vector,IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,IHK_TLB_FLUSH_IRQ_VECTOR_START,irq_save,irq_restore,
  original_mode?original_mem_tlb_flush_single_bridge:mem_tlb_flush_single_bridge,
  original_mode?original_mem_tlb_flush_all_bridge:mem_tlb_flush_all_bridge,
  original_mode?original_mem_tlb_atomic_dec_bridge:mem_tlb_atomic_dec_bridge);
 if(ret||before<=0||ihk_atomic_read(&tlb_flush_vector[slot].pending)!=before-1)abort();++decrements;
}
int ihk_mc_interrupt_cpu(int cpu,int vector)
{
 event(3,cpu,vector,provider_return,0);
 if(consumer_mode){++interrupts;if(delay_delivery){if(queued>=CPU_SETSIZE)abort();queue[queued++]=vector;}else deliver(vector);}
 return provider_return;
}
unsigned long rdtsc(void){event(4,17,0,0,0);return 17;}
void cpu_pause(void){++pauses;event(15,done,queued,0,0);if(done>=queued)abort();deliver(queue[done++]);}
#include "original-array-entry.inc"
static void reset(void)
{
 n=0;memset(trace,0,sizeof trace);memset(tlb_flush_vector,0,sizeof tlb_flush_vector);memset(&aspace.cpu_set_lock,0,sizeof aspace.cpu_set_lock);
 queued=done=interrupts=handlers=decrements=pauses=lock_depth=0;
}
static unsigned remote_count(const unsigned long *bits)
{unsigned count=0;for(int i=0;i<CPU_SETSIZE;i++)if((bits[i/64]>>(i%64))&1UL)count+=(current_cpu!=i);return count;}
extern const unsigned long F01_ACTUAL_LAYOUT[7];
int main(void)
{
 const unsigned long layout[7]={__builtin_offsetof(struct process_vm,address_space),__builtin_offsetof(struct address_space,cpu_set),__builtin_offsetof(struct address_space,cpu_set_lock),sizeof(struct tlb_flush_entry),__alignof__(struct tlb_flush_entry),__builtin_offsetof(struct tlb_flush_entry,pending),sizeof(int)};
 require(!memcmp(layout,F01_ACTUAL_LAYOUT,sizeof layout));
 const int values[]={(-2147483647-1),-1,0,1,63,64,1023,1024,2147483647};
 unsigned direct=0,protocol=0,invalid=0;
 consumer_mode=0;
 for(unsigned i=0;i<9;i++){
  current_cpu=values[i];reset();int a=original_mem_tlb_current_cpu_bridge();unsigned len=n;memcpy(saved,trace,sizeof trace);
  reset();int b=mem_tlb_current_cpu_bridge();require(a==values[i]&&a==b&&n==len&&n==1&&!memcmp(saved,trace,sizeof trace));direct++;
 }
 for(unsigned i=0;i<9;i++)for(unsigned j=0;j<9;j++){
  provider_return=values[j];reset();int a=original_mem_tlb_get_vector_bridge(values[i]);unsigned len=n;memcpy(saved,trace,sizeof trace);
  reset();int b=mem_tlb_get_vector_bridge(values[i]);require(a==values[j]&&a==b&&n==len&&n==1&&!memcmp(saved,trace,sizeof trace));direct++;
 }
 for(unsigned i=0;i<9;i++)for(unsigned j=0;j<9;j++)for(unsigned k=0;k<9;k++){
  provider_return=values[k];reset();original_mem_tlb_interrupt_cpu_bridge(values[i],values[j]);unsigned len=n;memcpy(saved,trace,sizeof trace);
  reset();mem_tlb_interrupt_cpu_bridge(values[i],values[j]);require(n==len&&n==1&&!memcmp(saved,trace,sizeof trace)&&!handlers&&!decrements);direct++;
 }
 unsigned atomics=0,locks=0,endpoints=0;
 for(unsigned i=0;i<9;i++){
  ihk_atomic_t a,b;
  original_mem_tlb_atomic_set_bridge((unsigned long)&a,values[i]);mem_tlb_atomic_set_bridge((unsigned long)&b,values[i]);
  require(original_mem_tlb_atomic_read_bridge((unsigned long)&a)==mem_tlb_atomic_read_bridge((unsigned long)&b));atomics++;
  original_mem_tlb_atomic_inc_bridge((unsigned long)&a);mem_tlb_atomic_inc_bridge((unsigned long)&b);
  require((unsigned)ihk_atomic_read(&a)==(unsigned)values[i]+1U&&(unsigned)ihk_atomic_read(&a)==(unsigned)ihk_atomic_read(&b));atomics++;
  original_mem_tlb_atomic_dec_bridge((unsigned long)&a);mem_tlb_atomic_dec_bridge((unsigned long)&b);
  require(ihk_atomic_read(&a)==values[i]&&ihk_atomic_read(&a)==ihk_atomic_read(&b));atomics++;
 }
 for(unsigned i=0;i<3;i++){
  ihk_spinlock_t a,b;unsigned short v=(unsigned short)(i==0?0:i==1?65534:65535);a.head_tail=b.head_tail=(unsigned)v|((unsigned)v<<16);
  reset();original_mem_tlb_noirq_lock_bridge((unsigned long)&a);require(lock_depth==1);original_mem_tlb_noirq_unlock_bridge((unsigned long)&a);require(!lock_depth);unsigned len=n;memcpy(saved,trace,sizeof trace);
  reset();mem_tlb_noirq_lock_bridge((unsigned long)&b);require(lock_depth==1);mem_tlb_noirq_unlock_bridge((unsigned long)&b);require(!lock_depth&&a.head_tail==b.head_tail&&a.tickets.head==(unsigned short)(v+2)&&a.tickets.head==a.tickets.tail&&len==n&&!memcmp(saved,trace,sizeof trace));locks++;
 }
 for(unsigned i=0;i<9;i++){
  reset();unsigned long a=original_mem_tlb_rdtsc_bridge();original_mem_tlb_flush_single_bridge((unsigned long)(long)values[i]);original_mem_tlb_flush_all_bridge();unsigned len=n;memcpy(saved,trace,sizeof trace);
  reset();unsigned long b=mem_tlb_rdtsc_bridge();mem_tlb_flush_single_bridge((unsigned long)(long)values[i]);mem_tlb_flush_all_bridge();require(a==b&&n==len&&!memcmp(saved,trace,sizeof trace));endpoints++;
 }
 const unsigned long firsts[]={0,1,4096,(IHK_TLB_FLUSH_IRQ_VECTOR_SIZE-1UL)<<12,~0UL};
 const int cpus[]={-1,0,1,63,64,1023,1024};
 for(unsigned mask=0;mask<8;mask++)for(unsigned cur=0;cur<7;cur++)for(unsigned addr=0;addr<5;addr++)for(int count=1;count<=3;count+=2)for(int delay=0;delay<2;delay++){
  unsigned long stack_addresses[3];addresses=stack_addresses;
  memset(&vm,0,sizeof vm);memset(&aspace,0,sizeof aspace);vm.address_space=&aspace;
  switch(mask){case 0:break;case 1:aspace.cpu_set.__bits[0]=1;break;case 2:aspace.cpu_set.__bits[0]=2;break;case 3:aspace.cpu_set.__bits[0]=3;break;case 4:aspace.cpu_set.__bits[0]=1UL<<63;break;case 5:aspace.cpu_set.__bits[1]=1;break;case 6:aspace.cpu_set.__bits[15]=1UL<<63;break;default:aspace.cpu_set.__bits[0]=3UL|(1UL<<63);aspace.cpu_set.__bits[1]=1;aspace.cpu_set.__bits[15]=1UL<<63;}
  addresses[0]=firsts[addr];addresses[1]=0x12345;addresses[2]=~0UL;consumer_mode=1;current_cpu=cpus[cur];provider_return=0;delay_delivery=delay;
  reset();original_mode=1;original_remote_flush_tlb_array_cpumask(&vm,addresses,count,-99);unsigned len=n;memcpy(saved,trace,sizeof trace);unsigned expected=remote_count(aspace.cpu_set.__bits);
  require(!lock_depth&&interrupts==(int)expected&&handlers==interrupts&&decrements==interrupts&&done==queued);
  for(int i=0;i<IHK_TLB_FLUSH_IRQ_VECTOR_SIZE;i++)require(tlb_flush_vector[i].pending.counter==0);
  reset();original_mode=0;remote_flush_tlb_array_cpumask(&vm,addresses,count,-99);
  require(n==len&&!memcmp(saved,trace,sizeof trace));require(!lock_depth&&interrupts==(int)expected&&handlers==interrupts&&decrements==interrupts&&done==queued);
  for(int i=0;i<IHK_TLB_FLUSH_IRQ_VECTOR_SIZE;i++)require(tlb_flush_vector[i].pending.counter==0);
  if(delay&&expected)require(pauses==(int)expected);protocol++;
 }
 addresses=invalid_addresses;
 for(int which=0;which<5;which++){
  memset(&vm,0,sizeof vm);vm.address_space=which==4?0:&aspace;consumer_mode=1;current_cpu=0;provider_return=0;reset();
  struct process_vm *p=which==0?0:&vm;unsigned long *a=which==1?0:addresses;int nr=which==2?0:which==3?-1:1;
  original_remote_flush_tlb_array_cpumask(p,a,nr,0);require(n==0&&!handlers&&!decrements);reset();original_mode=0;remote_flush_tlb_array_cpumask(p,a,nr,0);require(n==0&&!handlers&&!decrements);invalid++;
 }
 require(direct==819&&protocol==1120&&invalid==5);
 require(atomics==27&&locks==3&&endpoints==9);
 printf("PASS all13 direct=%u actual-array-handler=%u invalid=%u atomics=%u locks=%u endpoints=%u; actual atomic/spin providers; completion only real handler decrement\n",direct,protocol,invalid,atomics,locks,endpoints);return 0;
}
