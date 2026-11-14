/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact original C L1 body/selected walker vs actual candidate Rust L1 entry,
 * real Rust leaf/effect/oldaction/phys/walk/page-unmap bodies. Existing external
 * lower C providers are typed controlled trace endpoints, not mirrored helpers. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
typedef unsigned long pte_t;
#define PTL1_SHIFT 12
#define PTL1_SIZE (1UL<<12)
#include "actual-types-and-level-declaration.inc"
struct memobj { void *ops;unsigned flags,status;unsigned long size;int refcnt,pad;void **pages;int nr_pages,pad2;char *path; };
struct clear_range_args { int free_physical;struct memobj *memobj;void *vm;unsigned long *addr;int nr_addr,max_nr_addr; };
_Static_assert(sizeof(struct clear_range_args)==40 && offsetof(struct clear_range_args,nr_addr)==32,"actual clear args ABI");
_Static_assert(offsetof(struct memobj,flags)==8,"actual Memobj flags ABI");
struct page { _Alignas(8) unsigned char bytes[80]; };
extern int clear_range_l1(void *,pte_t *,uint64_t,uint64_t,uint64_t);
extern int walk_pte_l1(void*,unsigned long,unsigned long,unsigned long,int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t),void*);
extern int x86_clear_old_action_bridge(void*,unsigned long,size_t,unsigned long*,void**,int*);
extern void *x86_clear_phys_to_virt_bridge(unsigned long);
extern void x86_clear_free_pages_user_bridge(void*,int);
extern int x86_clear_page_unmap_bridge(void*);
unsigned long linux_page_offset_base=0xffff888000000000UL;
const char x86_clear_free_pages_user_file[]=__FILE__;
const int x86_clear_free_pages_user_line=__LINE__;
const int x86_clear_free_pages_user_flag=1;
struct event { unsigned long code,a,b,c,d,e,f,g,h; };
struct trace { unsigned n;struct event ev[128]; };
static struct trace *active;
static struct clear_range_args *live_args;
static pte_t *live_entry;
static int child_ret,page_variant,unmap_ret,cpu;
static struct page page;
static struct memobj memobj;
static unsigned long coverage;
static void reset_page(void);
static unsigned long norm(void *p){if(p==(void*)live_args)return 0x111; if(p==(void*)live_entry)return 0x222;return (uintptr_t)p;}
static void event(unsigned long code,unsigned long a,unsigned long b,unsigned long c,unsigned long d,unsigned long e,unsigned long f,unsigned long g,unsigned long h)
{ if(!active||active->n>=128)abort();coverage|=1UL<<code;active->ev[active->n++]=(struct event){code,a,b,c,d,e,f,g,h}; }
int ihk_mc_get_processor_id(void){event(1,cpu,0,0,0,0,0,0,0);return cpu;}
int x86_addr_init_pt_loaded_bridge(void){return 1;}
struct page *phys_to_page(unsigned long phys){event(3,phys,page_variant,0,0,0,0,0,0);if(page_variant)reset_page();return page_variant?&page:NULL;}
/* Actual Rust page_unmap is linked, with controlled external lock/log endpoints. */
unsigned char page_hash_locks[8];
const int page_unmap_hash_shift=12;
const unsigned long page_unmap_hash_mask=0;
const size_t page_unmap_lock_stride=8;
unsigned long page_hash_lock_bridge(uintptr_t addr){event(13,addr,0,0,0,0,0,0,0);return 0x321;}
void page_hash_unlock_bridge(uintptr_t addr,unsigned long flags){event(14,addr,flags,0,0,0,0,0,0);}
void page_unmap_log_bridge(int code,struct page *p,int ret){event(5,code,(uintptr_t)p,ret,0,0,0,0,0);}
struct link {struct link *next,*prev;};
static struct link head;
static void reset_page(void){
 memset(&page,0,sizeof page);page.bytes[32]=page_variant==2?7:0;
 struct link *hash=(struct link*)(page.bytes+16);head.next=head.prev=hash;hash->next=hash->prev=&head;
 *(unsigned long*)(page.bytes+40)=0x1000;*(int*)(page.bytes+48)=unmap_ret?1:2;
}
void remote_flush_tlb_array_cpumask(void *vm,unsigned long *addr,int nr,int id)
{event(2,(uintptr_t)vm,nr,id,addr?addr[0]:0,live_entry?*live_entry:0,0,0,0);}
void _ihk_mc_free_pages(void *ptr,int nr,int flag,char *file,int line)
{if(file!=x86_clear_free_pages_user_file||line!=x86_clear_free_pages_user_line||flag!=1)abort();event(6,(uintptr_t)ptr,nr,flag,line,0,0,0,0);}
void x86_pt_free_pages_bridge(void *ptr,int nr){event(12,(uintptr_t)ptr,nr,live_entry?*live_entry:0,0,0,0,0,0);}
static void x86_clear_memobj_flush_bridge(void *m,unsigned long phys,size_t size){event(4,(uintptr_t)m,phys,size,0,0,0,0,0);}
static void x86_clear_rss_sub_bridge(size_t size,size_t pg){event(7,size,pg,0,0,0,0,0,0);}
static void x86_clear_memobj_rss_sub_bridge(void*m,size_t size,size_t pg){event(8,(uintptr_t)m,size,pg,0,0,0,0,0);}
static void x86_clear_effect_log_bridge(int code,unsigned long base,unsigned long phys,size_t pg){event(10,code,base,phys,pg,0,0,0,0);}
static void x86_clear_range_log_bridge(int code,void*args,unsigned long *pte,unsigned long base,unsigned long start,unsigned long end,int err,int shift,unsigned long phys)
{event(9,code,norm(args),norm(pte),base,start,end,((unsigned long)(unsigned)err<<32)|(unsigned)shift,phys);}
static int x86_clear_range_walk_l1_bridge(void *pt,unsigned long base,unsigned long start,unsigned long end,void *args)
{event(11,(uintptr_t)pt,base,start,end,norm(args),child_ret,0,0);return child_ret;}
x86_clear_child_walk_fn_t const x86_clear_l2_child_walk=&x86_clear_range_walk_l1_bridge;
x86_clear_flush_memobj_fn_t const x86_clear_l3_memobj_flush=&x86_clear_memobj_flush_bridge;
x86_clear_rss_sub_fn_t const x86_clear_l3_rss_sub=&x86_clear_rss_sub_bridge;
x86_clear_memobj_rss_sub_fn_t const x86_clear_l3_memobj_rss_sub=&x86_clear_memobj_rss_sub_bridge;
x86_clear_range_log_fn_t const x86_clear_l3_range_log=&x86_clear_range_log_bridge;
x86_clear_effect_log_fn_t const x86_clear_l3_effect_log=&x86_clear_effect_log_bridge;
#include "original-body.inc"
#include "original-walker.inc"
#include "selected-walker.inc"
static void require(int ok,const char *why){if(!ok){fprintf(stderr,"FAIL %s\n",why);exit(1);}}
static unsigned count(struct trace*t,unsigned code){unsigned n=0;for(unsigned i=0;i<t->n;i++)n+=t->ev[i].code==code;return n;}
int main(void)
{
 const unsigned long entries[]={0,0x1001,0x81,0x400000c1,0x881,0x400000c1,0x8000000000000080UL,~0UL};
 const int nrvalues[]={-1,0,2};
 unsigned direct=0,consumer=0;
 for(unsigned e=0;e<8;e++)for(unsigned range=0;range<4;range++)for(unsigned nr=0;nr<3;nr++)for(unsigned fre=0;fre<2;fre++)for(unsigned nullpte=0;nullpte<2;nullpte++) {
  unsigned long a=entries[e],b=a,aa[2]={31,37},bb[2]={31,37};
  memobj.flags=e%3==1?0x10000:0;page_variant=e%3;unmap_ret=fre;reset_page();cpu=nr==0?-1:nr==1?0:63;
  struct clear_range_args ca={fre,e%2?&memobj:NULL,(void*)0x345,aa,nrvalues[nr],2},cb=ca;cb.addr=bb;
  unsigned long base=0,start=range==1?1:0,end=range==2?PTL1_SIZE-1:range==3?0:PTL1_SIZE;
  struct trace ta={0},tb={0};active=&ta;live_args=&ca;live_entry=&a;int ra=original_clear_range_l1(&ca,nullpte?NULL:&a,base,start,end);
  struct page page_after=page;reset_page();active=&tb;live_args=&cb;live_entry=&b;int rb=clear_range_l1(&cb,nullpte?NULL:&b,base,start,end);
  require(!memcmp(&page_after,&page,sizeof page),"real page_unmap atomic count/list effects");
  require(ra==rb && a==b && ca.nr_addr==cb.nr_addr && !memcmp(aa,bb,sizeof aa),"direct return/PTE/address counter effects");
  require(!memcmp(&ta,&tb,sizeof ta),"direct exact callback order/args/log/free/flush effects");
  require(count(&ta,1)==1,"CPU provider exactly once even helper early errors");
  if(nullpte)require(ra==-22 && ta.n==1,"original null-ptep policy after args/CPU evaluation");
  else if(!entries[e])require(ra==-2 && ta.n==1,"zero entry skip");
  active=NULL;direct++;
 }
 for(unsigned e=0;e<8;e++)for(unsigned nr=0;nr<3;nr++)for(unsigned fre=0;fre<2;fre++) {
  unsigned long a[512]={0},b[512]={0},aa[2]={31,37},bb[2]={31,37};a[0]=b[0]=entries[e];a[1]=b[1]=entries[(e+1)%8];
  memobj.flags=0;page_variant=e%3;unmap_ret=fre;reset_page();cpu=7;
  struct clear_range_args ca={fre,e%2?&memobj:NULL,(void*)0x345,aa,nrvalues[nr],2},cb=ca;cb.addr=bb;
  struct trace ta={0},tb={0};active=&ta;live_args=&ca;live_entry=a;int ra=original_walk_l1(a,0,0,2*PTL1_SIZE,&ca);
  struct page page_after=page;reset_page();active=&tb;live_args=&cb;live_entry=b;int rb=selected_walk_l1(b,0,0,2*PTL1_SIZE,&cb);
  require(!memcmp(&page_after,&page,sizeof page),"PUBLIC real page_unmap count/list effects");
  require(ra==rb&&!memcmp(a,b,sizeof a)&&ca.nr_addr==cb.nr_addr&&!memcmp(aa,bb,sizeof aa),"actual PUBLIC walker return/PTE/address effects");
  /* Range-log ptep may be another table entry: normalize identical table offsets. */
  for(unsigned i=0;i<ta.n;i++)if(ta.ev[i].code==9&&ta.ev[i].c==(uintptr_t)(a+1))ta.ev[i].c=0x223;
  for(unsigned i=0;i<tb.n;i++)if(tb.ev[i].code==9&&tb.ev[i].c==(uintptr_t)(b+1))tb.ev[i].c=0x223;
  require(!memcmp(&ta,&tb,sizeof ta),"actual PUBLIC consumer callback ordering and provider identity");active=NULL;consumer++;
 }
 require((coverage&0x65fe)==0x65fe,"all11leaf provider/effect trace categories observed");
 require(!(coverage&((1UL<<9)|(1UL<<11)|(1UL<<12))),"leaf has no range log/child walk/child PTfree");
 printf("PASS direct=%u PUBLIC-walker=%u original-C/Rust L1 pairs; actual leaf/effects/oldaction/phys/walk bodies; retained lower-provider traces\n",direct,consumer);return 0;
}
