/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact original L4 callback and walker call the existing real Rust root/phys/walk
 * bodies; only the retained private L3 C provider and boot state are controlled.
 * No provider mirror, no native table/free/flush acceptance. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <stdlib.h>
typedef unsigned long pte_t;
typedef void *(*phys_fn)(unsigned long);
typedef int (*child_fn)(void *,unsigned long,unsigned long,unsigned long,void *);
typedef int (*root_fn)(void *,pte_t *,uint64_t,uint64_t,uint64_t);
extern int x86_clear_range_root_body_result(void *,pte_t *,unsigned long,unsigned long,unsigned long,phys_fn,child_fn);
extern void *x86_clear_phys_to_virt_bridge(unsigned long);
extern int x86_clear_range_l4_body(void *,pte_t *,uint64_t,uint64_t,uint64_t);
extern int x86_clear_range_walk_l4_bridge(void *,unsigned long,unsigned long,unsigned long,void *);
extern int walk_pte_l4(void *,unsigned long,unsigned long,unsigned long,root_fn,void *);
struct event { uintptr_t pt,arg; unsigned long base,start,end; };
struct state { unsigned calls; int ret; pte_t *mutate; struct event events[512]; };
static struct state *active;
static int loaded;
/* Exact production provider type/BSS initialization from SMP setup.c;
 * arch_start fills this from boot_param->page_offset_base. Controlled bootdata
 * values below cover both ordinary bases and wrap-to-null boundaries. */
unsigned long linux_page_offset_base;
static const unsigned long offsets[]={0,0xffff888000000000UL,~0UL,0xfffffffffffff000UL};
int x86_addr_init_pt_loaded_bridge(void) { return loaded; }
static int x86_clear_range_walk_l3_bridge(void *pt,unsigned long base,unsigned long start,unsigned long end,void *arg)
{
 if(!active || active->calls>=512)abort();
 active->events[active->calls++]=(struct event){(uintptr_t)pt,(uintptr_t)arg,base,start,end};
 if(active->mutate)*active->mutate ^= 0x100000UL;
 return active->ret;
}
int (*const x86_clear_range_l3_callback)(void*,unsigned long,unsigned long,unsigned long,void*)=&x86_clear_range_walk_l3_bridge;
int (*const x86_clear_range_l4_callback)(void*,pte_t*,uint64_t,uint64_t,uint64_t)=&x86_clear_range_l4_body;
#include "../original-body.inc"
#include "../original-walker.inc"
static void require(int ok,const char *why){if(!ok){fprintf(stderr,"FAIL %s\n",why);exit(1);}}
int main(void)
{
 const unsigned long entries[]={0,1,0x1001UL,0xffffffffffffffffUL,0x10000000000000UL,0x8000000000000080UL,0x123456789abfffUL,0xfffUL};
 const unsigned long bases[]={0,1,0xffff000000000000UL,~0UL};
 const int returns[]={0,-2,-5,-12,INT_MIN,INT_MAX,7};
 unsigned direct=0,consumer=0,phys=0;
 const unsigned long physical[]={0,1,4095,4096,~0UL,~0UL-4095,1UL<<63,(1UL<<52)-4096};
 for(unsigned o=0;o<4;o++)for(loaded=0;loaded<2;loaded++)for(unsigned k=0;k<8;k++) {
  linux_page_offset_base=offsets[o];
  unsigned long expected=physical[k]+(loaded?offsets[o]:0xffff800000000000UL);
  require((uintptr_t)x86_clear_phys_to_virt_bridge(physical[k])==expected,"actual phys provider wrap/boundary/null");phys++;
 }

 for(unsigned o=0;o<4;o++)for(loaded=0;loaded<2;loaded++)for(unsigned e=0;e<8;e++)for(unsigned b=0;b<4;b++)for(unsigned q=0;q<7;q++)for(unsigned nullpte=0;nullpte<2;nullpte++)for(unsigned nullarg=0;nullarg<2;nullarg++) {
  linux_page_offset_base=offsets[o];
  pte_t a=entries[e],c=a;struct state sa={.ret=returns[q],.mutate=&a},sc={.ret=returns[q],.mutate=&c};
  void *arg=nullarg?NULL:(void*)(uintptr_t)0x12345UL;
  active=&sa;int ra=original_clear_range_l4(arg,nullpte?NULL:&a,bases[b],~0UL,17);
  active=&sc;int rc=x86_clear_range_l4_body(arg,nullpte?NULL:&c,bases[b],~0UL,17);
  require(ra==rc && sa.calls==sc.calls && a==c,"direct return/count/mutations");
  require(!memcmp(sa.events,sc.events,sizeof sa.events),"direct child exact arguments/order");
  if(nullpte)require(ra==-22 && !sa.calls,"null entry existing EINVAL");
  else if(!entries[e])require(ra==-2 && !sa.calls,"null PTE existing ENOENT");
  else if((uintptr_t)x86_clear_phys_to_virt_bridge(entries[e]&0x000ffffffffff000UL)==0)
   require(ra==-22 && !sa.calls,"actual phys conversion null suppresses child");
  else require(ra==returns[q] && sa.calls==1,"exact single child call and return");
  active=NULL;direct++;
 }
 for(unsigned o=0;o<4;o++)for(loaded=0;loaded<2;loaded++)for(unsigned q=0;q<7;q++)for(unsigned zero=0;zero<2;zero++) {
  linux_page_offset_base=offsets[o];
  pte_t a[512]={0},c[512]={0};for(unsigned i=0;i<4;i++)a[i]=c[i]=zero?0:(0x1001UL+i*0x1000UL);
  struct state sa={.ret=returns[q],.mutate=&a[0]},sc={.ret=returns[q],.mutate=&c[0]};
  active=&sa;int ra=original_walk_l4(a,0,0,4UL<<39,(void*)0x2345UL);
  active=&sc;int rc=x86_clear_range_walk_l4_bridge(c,0,0,4UL<<39,(void*)0x2345UL);
  require(ra==rc && sa.calls==sc.calls && !memcmp(a,c,sizeof a),"actual default walker return/callback mutations");
  require(!memcmp(sa.events,sc.events,sizeof sa.events),"actual default walker callback order/identity");
  if(zero)require(ra==-2 && !sa.calls,"default all-null PTE skips child");
  active=NULL;consumer++;
 }
 printf("PASS direct=%u default-walker=%u phys-provider=%u exact-original-C/Rust pairs; actual root+phys+walk bodies; typed retained L3 provider\n",direct,consumer,phys);
 return 0;
}
