/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual Rust spinlock/page providers; controlled external IRQ/hash/log/allocator
 * endpoints. No privileged instruction, real physical page or native claim.
 */
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
struct list_head { struct list_head *next,*prev; };
typedef struct {int counter;} ihk_atomic_t;
typedef struct {long counter64;} ihk_atomic64_t;
struct page {
	struct list_head	list;
	struct list_head	hash;
	uint8_t			mode;
	uint64_t		phys;
	ihk_atomic_t		count;
	ihk_atomic64_t	mapped;
	off_t			offset;
	int pgshift;	/* Using by shmobj */
};
struct page_table { unsigned long entries[512]; };
typedef struct {unsigned head_tail;} ihk_spinlock_t;
typedef unsigned long ihk_mc_ap_flag;
enum ihk_mc_pt_attribute {ATTR_ZERO=0,ATTR_FULL=ULONG_MAX};
static struct page_table table_a,table_b,*init_pt;
static ihk_spinlock_t init_pt_lock;
static unsigned long ATTR_MASK,expected_flags;
static int held,irq_off,kernel_case,body_result;
static unsigned events[4],event_count;
static void *captured[2];static unsigned long args[4];
static unsigned long KERNEL_BASE=0xffff000000000000UL;
static int x86_pt_kernel_lock_needed_result(unsigned long v){return v>=KERNEL_BASE;}
extern unsigned long __ihk_mc_spinlock_lock(ihk_spinlock_t*);
extern void __ihk_mc_spinlock_unlock(ihk_spinlock_t*,unsigned long);
#define ihk_mc_spinlock_lock __ihk_mc_spinlock_lock
#define ihk_mc_spinlock_unlock __ihk_mc_spinlock_unlock
unsigned long cpu_disable_interrupt_save(void){assert(!irq_off && !held);irq_off=1;return expected_flags;}
void cpu_restore_interrupt(unsigned long flags){assert(irq_off && !held && flags==expected_flags);irq_off=0;}
void preempt_disable(void){assert(irq_off && !held && kernel_case);held=1;events[event_count++]=1;init_pt=&table_b;}
void preempt_enable(void){assert(irq_off && held);events[event_count++]=3;held=0;}
void cpu_pause(void){assert(0);}
void *x86_init_page_table_lock_bridge(void){assert(kernel_case);return &init_pt_lock;}
void *x86_page_table_init_pt_bridge(void){assert(held==kernel_case);return init_pt;}
unsigned long x86_attr_mask_bridge(void){assert(held==kernel_case);return ATTR_MASK;}
unsigned long x86_pt_virt_to_phys_bridge(void*p){(void)p;assert(0);return 0;}
void *x86_pt_phys_to_virt_bridge(unsigned long p){(void)p;assert(0);return 0;}
void x86_pt_set_page_log_bridge(unsigned long p){(void)p;assert(0);}
extern void *x86_pt_alloc_pages_bridge(int,int);
int x86_pt_set_page_body_result(void*pt,void*ip,unsigned long v,unsigned long p,unsigned long a,unsigned long mask,
 void*(*alloc)(int,int),unsigned long(*vp)(void*),void*(*pv)(unsigned long),void(*log)(unsigned long)){
 assert(held==kernel_case && irq_off==kernel_case);events[event_count++]=2;
 assert(alloc==x86_pt_alloc_pages_bridge && vp==x86_pt_virt_to_phys_bridge && pv==x86_pt_phys_to_virt_bridge && log==x86_pt_set_page_log_bridge);
 captured[0]=pt;captured[1]=ip;args[0]=v;args[1]=p;args[2]=a;args[3]=mask;return body_result;
}
static struct page_table memory[2] __attribute__((aligned(4096)));
static unsigned alloc_calls;static int alloc_mode,seen_flag;
const char x86_pt_alloc_pages_file[] = __FILE__;
const int x86_pt_alloc_pages_line = 750;
const int x86_pt_alloc_pages_p2align = PAGE_P2ALIGN;
const int x86_pt_alloc_pages_is_user = IHK_MC_PG_KERNEL;

void *_ihk_mc_alloc_aligned_pages_node(int n,int align,unsigned long flag,int node,int user,unsigned long virt,char*file,int line){
 assert(n==1 && align==x86_pt_alloc_pages_p2align && node==-1 && user==x86_pt_alloc_pages_is_user && virt==ULONG_MAX);
 assert(file==x86_pt_alloc_pages_file && line==x86_pt_alloc_pages_line);
 ++alloc_calls;seen_flag=(int)flag;return alloc_mode<0?NULL:&memory[alloc_mode];
}
extern void *x86_pt_alloc_zeroed_result(int,void*(*)(int,int));
extern void page_map(struct page*);
extern int page_unmap(struct page*);
static void *x86_split_alloc_new_pt_bridge(int,int) __asm__("original_C_split_alloc");
static void x86_split_page_map_bridge(void*) __asm__("original_C_split_map");
static int x86_split_page_unmap_bridge(void*) __asm__("original_C_split_unmap");
#include "EXACT-ORIGINAL-C-PROVIDERS.inc"
extern int rust_set(void*,unsigned long,unsigned long,unsigned long) __asm__("x86_pt_set_page_bridge");
extern void *rust_alloc(int,int) __asm__("x86_split_alloc_new_pt_bridge");
extern void rust_map(void*) __asm__("x86_split_page_map_bridge");
extern int rust_unmap(void*) __asm__("x86_split_page_unmap_bridge");
unsigned char page_hash_locks[16] __attribute__((aligned(4)));
const int page_unmap_hash_shift=12;
const unsigned long page_unmap_hash_mask=3;
const size_t page_unmap_lock_stride=4;
static unsigned hash_held,hash_locks,hash_unlocks,log_count;static unsigned log_events[3];static int log_returns[3];
unsigned long page_hash_lock_bridge(size_t addr){assert(!hash_held && addr==(size_t)page_hash_locks+4);hash_held=1;++hash_locks;return 0xa55aUL;}
void page_hash_unlock_bridge(size_t addr,unsigned long f){assert(hash_held && addr==(size_t)page_hash_locks+4 && f==0xa55aUL);hash_held=0;++hash_unlocks;}
void page_unmap_log_bridge(int event,struct page*page,int ret){assert(!hash_held && page && log_count<3);log_events[log_count]=event;log_returns[log_count++]=ret;}
static void reset_set(unsigned long v){held=irq_off=0;event_count=0;init_pt_lock.head_tail=0;init_pt=&table_a;kernel_case=v>=KERNEL_BASE;memset(events,0,sizeof(events));memset(captured,0,sizeof(captured));memset(args,0,sizeof(args));}
static void set_case(void*pt,unsigned long v,unsigned long p,unsigned long attr,int ret){
 body_result=ret;reset_set(v);unsigned allocations=alloc_calls;
 int a=__set_pt_page(pt,(void*)v,p,(enum ihk_mc_pt_attribute)attr);
 assert(!held && !irq_off && a==ret && event_count==(kernel_case?3U:1U));
 assert(captured[1]==(kernel_case?(void*)&table_b:(void*)&table_a));
 unsigned ev[4];void*ptrs[2];unsigned long av[4];unsigned n=event_count;
 memcpy(ev,events,sizeof(ev));memcpy(ptrs,captured,sizeof(ptrs));memcpy(av,args,sizeof(av));
 reset_set(v);int b=rust_set(pt,v,p,attr);
 assert(!held && !irq_off && b==a && n==event_count && !memcmp(ev,events,sizeof(ev)));
 assert(!memcmp(ptrs,captured,sizeof(ptrs)) && !memcmp(av,args,sizeof(av)) && alloc_calls==allocations);
}
static void alloc_case(int count,int flags,int mode){
 alloc_mode=mode;alloc_calls=0;seen_flag=0;memset(memory,0xa5,sizeof(memory));
 void*a=x86_split_alloc_new_pt_bridge(count,flags);unsigned n=alloc_calls;int f=seen_flag;
 unsigned char expected[sizeof(memory)];memcpy(expected,memory,sizeof(memory));
 alloc_calls=0;seen_flag=0;memset(memory,0xa5,sizeof(memory));void*b=rust_alloc(count,flags);
 assert(a==b && n==alloc_calls && f==seen_flag && !memcmp(expected,memory,sizeof(memory)));
 assert(n==(count==1?1U:0U));if(count==1){assert(f==flags);if(mode>=0)for(unsigned i=0;i<512;i++)assert(memory[mode].entries[i]==0);}else assert(a==NULL);
}
static struct page pg;
static void reset_page(int count){memset(&pg,0,sizeof(pg));pg.phys=4096;pg.count.counter=count;pg.hash.next=pg.hash.prev=&pg.hash;hash_held=hash_locks=hash_unlocks=log_count=0;memset(log_events,0,sizeof(log_events));memset(log_returns,0,sizeof(log_returns));}
static void page_case(int count){
 reset_page(count);x86_split_page_map_bridge(&pg);struct page wanted=pg;
 reset_page(count);rust_map(&pg);assert(!memcmp(&pg,&wanted,sizeof(pg)) && !hash_locks && !log_count);
 reset_page(count);int a=x86_split_page_unmap_bridge(&pg);wanted=pg;unsigned l=hash_locks,u=hash_unlocks,n=log_count,ev[3];int rets[3];memcpy(ev,log_events,sizeof(ev));memcpy(rets,log_returns,sizeof(rets));
 reset_page(count);int b=rust_unmap(&pg);
 assert(a==b && !memcmp(&pg,&wanted,sizeof(pg)) && !hash_held && hash_locks==l && hash_unlocks==u && n==log_count);
 assert(!memcmp(ev,log_events,sizeof(ev)) && !memcmp(rets,log_returns,sizeof(rets)) && l==1 && u==1 && n==2);
}
int main(void){
 _Static_assert(sizeof(struct page)==80 && _Alignof(struct page)==8 && offsetof(struct page,count)==48 && offsetof(struct page,hash)==16,"real page layout closure");
 _Static_assert(sizeof(ihk_spinlock_t)==4 && _Alignof(ihk_spinlock_t)==4,"real lock layout closure");
 const unsigned long values[]={0,1,0x123456789abcdef0UL,1UL<<63,ULONG_MAX};
 const unsigned long virt[]={0,0xffff000000000000UL-1,0xffff000000000000UL,ULONG_MAX};
 const int errors[]={0,-12,-16,INT_MIN,INT_MAX};void*pts[]={NULL,&table_a,&table_b};
 unsigned set_pairs=0,alloc_pairs=0,page_pairs=0;
 for(unsigned t=0;t<3;t++)for(unsigned v=0;v<4;v++)for(unsigned x=0;x<5;x++)for(unsigned e=0;e<5;e++){
  expected_flags=values[(x+1)%5];ATTR_MASK=values[(x+2)%5];set_case(pts[t],virt[v],values[x],values[4-x],errors[e]);++set_pairs;
 }
 const int counts[]={INT_MIN,-2,-1,0,1,2,3,512,INT_MAX};const int flags[]={INT_MIN,-1,0,1,2,7,INT_MAX};
 for(unsigned c=0;c<9;c++)for(unsigned f=0;f<7;f++)for(int m=-1;m<2;m++){alloc_case(counts[c],flags[f],m);++alloc_pairs;}
 const int pc[]={1,2,7,INT_MAX};for(unsigned i=0;i<4;i++){page_case(pc[i]);page_pairs+=2;}
 /* Exact unmap wrapper preserves genuine provider's NULL behavior without a new policy. */
 assert(x86_split_page_unmap_bridge(NULL)==rust_unmap(NULL));++page_pairs;
 assert(set_pairs==300 && alloc_pairs==189 && page_pairs==9);
 puts("PASS set/split:498 original-C/Rust pairs (300 set,189 alloc,9 page);actual Rust spinlock/page/zeroing providers;controlled external endpoints");return 0;
}
