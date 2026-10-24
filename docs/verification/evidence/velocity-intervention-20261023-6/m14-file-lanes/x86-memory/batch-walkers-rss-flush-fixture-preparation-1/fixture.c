/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Original C providers vs actual Rust walkers/accounting/memobj dispatch.
 * Remaining page/CPU/flush/log providers are controlled trace endpoints. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <sys/types.h>
#include "actual-object-accounting-types.inc"
typedef unsigned long pte_t;
#define PTL1_SHIFT 12
#define PTL1_SIZE (1UL<<12)
#define PTL2_SHIFT 21
#define PTL2_SIZE (1UL<<21)
#define PTL3_SHIFT 30
#define PTL3_SIZE (1UL<<30)
#define PFL2_SIZE 0x80
#define PFL3_SIZE 0x80
#include "actual-clear-types.inc"
#include "actual-clear-args.inc"
extern void memory_stat_rss_sub(unsigned long,int);
extern void rusage_memory_stat_sub(struct memobj*,unsigned long,int);
extern int memobj_flush_page(struct memobj*,uintptr_t,size_t);
extern int clear_range_l1(void*,pte_t*,uint64_t,uint64_t,uint64_t);
extern int clear_range_l2(void*,pte_t*,uint64_t,uint64_t,uint64_t);
extern int clear_range_l3(void*,pte_t*,uint64_t,uint64_t,uint64_t);
extern int walk_pte_l1(void*,unsigned long,unsigned long,unsigned long,int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t),void*);
extern int walk_pte_l2(void*,unsigned long,unsigned long,unsigned long,int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t),void*);
extern int walk_pte_l3(void*,unsigned long,unsigned long,unsigned long,int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t),void*);
typedef int (*walker_t)(void*,unsigned long,unsigned long,unsigned long,void*);
extern int x86_clear_range_walk_l1_bridge(void*,unsigned long,unsigned long,unsigned long,void*);
extern int x86_clear_range_walk_l2_bridge(void*,unsigned long,unsigned long,unsigned long,void*);
extern int x86_clear_range_walk_l3_bridge(void*,unsigned long,unsigned long,unsigned long,void*);
extern void x86_clear_rss_sub_bridge(size_t,size_t);
extern void x86_clear_memobj_rss_sub_bridge(void*,size_t,size_t);
extern void x86_clear_memobj_flush_bridge(void*,unsigned long,size_t);
extern int x86_clear_old_action_bridge(void*,unsigned long,size_t,unsigned long*,void**,int*);
extern void *x86_clear_phys_to_virt_bridge(unsigned long);
extern void x86_clear_free_pages_user_bridge(void*,int);
extern int x86_clear_page_unmap_bridge(void*);
extern size_t fixture_geometry(int);
extern int fixture_rusage_enabled(void);
struct rusage_global rusage;
struct event { unsigned long code,a,b,c,d,e,rss,mapped; };
struct trace { unsigned n;struct event ev[1024]; };
static struct trace *active;
static pte_t *live_table;
static void *live_args,*live_obj;
static unsigned long norm(void *p) {
 if(p==live_args)return 0x111;
 if(p==live_obj)return 0x333;
 uintptr_t v=(uintptr_t)p,t=(uintptr_t)live_table;
 if(t && v>=t && v<t+512*sizeof(pte_t))return 0x1000+(v-t);
 return v;
}
static void event(unsigned long code,unsigned long a,unsigned long b,unsigned long c,unsigned long d,unsigned long e) {
 if(!active||active->n>=1024)abort();
 active->ev[active->n++]=(struct event){code,a,b,c,d,e,(unsigned long)rusage.memory_stat_rss[0],(unsigned long)rusage.memory_stat_mapped_file[0]};
}
static void require(int ok,const char*why){if(!ok){fprintf(stderr,"FAIL %s\n",why);exit(1);}}
int ihk_mc_get_processor_id(void){event(1,7,0,0,0,0);return 7;}
int x86_addr_init_pt_loaded_bridge(void){return 1;}
struct page *phys_to_page(unsigned long phys){event(2,phys,0,0,0,0);return NULL;}
unsigned long linux_page_offset_base=0xffff888000000000UL;
unsigned char page_hash_locks[8];
const int page_unmap_hash_shift=12;
const unsigned long page_unmap_hash_mask=0;
const size_t page_unmap_lock_stride=8;
unsigned long page_hash_lock_bridge(uintptr_t addr){event(3,addr,0,0,0,0);return 0;}
void page_hash_unlock_bridge(uintptr_t addr,unsigned long flags){event(4,addr,flags,0,0,0);}
void page_unmap_log_bridge(int code,void *page,int ret){event(5,code,norm(page),(unsigned)ret,0,0);}
void remote_flush_tlb_array_cpumask(void *vm,unsigned long *addr,int nr,int cpu){event(6,(uintptr_t)vm,(unsigned)nr,(unsigned)cpu,addr?addr[0]:0,0);}
const char x86_clear_free_pages_user_file[]=__FILE__;
const int x86_clear_free_pages_user_line=__LINE__;
const int x86_clear_free_pages_user_flag=1;
void _ihk_mc_free_pages(void *p,int n,int flag,char *file,int line){require(file==x86_clear_free_pages_user_file&&line==x86_clear_free_pages_user_line,"retained user-free provenance");event(7,(uintptr_t)p,(unsigned)n,(unsigned)flag,0,0);}
void x86_pt_free_pages_bridge(void *p,int n){event(8,(uintptr_t)p,(unsigned)n,0,0,0);}
static void x86_clear_range_log_bridge(int e,void *args,unsigned long *pte,unsigned long base,unsigned long start,unsigned long end,int err,int shift,unsigned long phys){event(9,(unsigned)e,norm(args),norm(pte),base,start);event(10,end,(unsigned)err,(unsigned)shift,phys,0);}
static void x86_clear_effect_log_bridge(int e,unsigned long base,unsigned long phys,size_t pg){event(11,(unsigned)e,base,phys,pg,0);}
static int use_1gb_page=1;
x86_clear_child_walk_fn_t const x86_clear_l2_child_walk=&x86_clear_range_walk_l1_bridge;
x86_clear_child_walk_fn_t const x86_clear_l3_child_walk=&x86_clear_range_walk_l2_bridge;
x86_clear_flush_memobj_fn_t const x86_clear_l3_memobj_flush=&x86_clear_memobj_flush_bridge;
x86_clear_rss_sub_fn_t const x86_clear_l3_rss_sub=&x86_clear_rss_sub_bridge;
x86_clear_memobj_rss_sub_fn_t const x86_clear_l3_memobj_rss_sub=&x86_clear_memobj_rss_sub_bridge;
x86_clear_range_log_fn_t const x86_clear_l3_range_log=&x86_clear_range_log_bridge;
x86_clear_effect_log_fn_t const x86_clear_l3_effect_log=&x86_clear_effect_log_bridge;
const int *const x86_clear_l3_use_1gb_page=&use_1gb_page;
#include "original-providers-and-callbacks.inc"
static unsigned walkers(void) {
 walker_t old[]={original_walk_l1,original_walk_l2,original_walk_l3};
 walker_t rust[]={x86_clear_range_walk_l1_bridge,x86_clear_range_walk_l2_bridge,x86_clear_range_walk_l3_bridge};
 const unsigned shifts[]={12,21,30};unsigned pairs=0;
 for(unsigned lev=0;lev<3;lev++)for(unsigned pat=0;pat<4;pat++)for(unsigned range=0;range<8;range++)for(unsigned nullpt=0;nullpt<2;nullpt++) {
  unsigned long span=1UL<<shifts[lev],a[512]={0},b[512]={0},aa[512]={0},bb[512]={0};
  a[0]=b[0]=(pat&1)?0x81:0;a[1]=b[1]=(pat&2)?0x81:0;
  unsigned long starts[]={0,1,span,span,span-1,2*span,0,2*span};
  unsigned long ends[]={2*span,span,2*span,span,span+1,span,0,2*span+1};
  struct clear_range_args ca={0,NULL,(void*)0x345,aa,0,512},cb=ca;cb.addr=bb;
  struct trace ta={0},tb={0};struct rusage_global before={0},after;
  rusage=before;active=&ta;live_table=a;live_args=&ca;int ra=old[lev](nullpt?NULL:a,0,starts[range],ends[range],&ca);after=rusage;
  rusage=before;active=&tb;live_table=b;live_args=&cb;int rb=rust[lev](nullpt?NULL:b,0,starts[range],ends[range],&cb);
  require(ra==rb&&!memcmp(a,b,sizeof a)&&ca.nr_addr==cb.nr_addr&&!memcmp(aa,bb,sizeof aa),"walker return/bounds/PTE/address effects");
  require(!memcmp(&ta,&tb,sizeof ta)&&!memcmp(&after,&rusage,sizeof rusage),"walker exact callback order/args/accounting");
  if(nullpt)require(ra==-2&&ta.n==0,"walker's unchanged null-table policy");
  active=NULL;live_table=NULL;live_args=NULL;pairs++;
 }
 return pairs;
}
static unsigned rss(void) {
 const unsigned long sizes[]={0,1,4096,~0UL,1UL<<63};
 const unsigned long pages[]={0,4096,1UL<<21,1UL<<30,(1UL<<32)|4096,(1UL<<32)|(1UL<<21),(1UL<<32)|(1UL<<30),~0UL,1UL<<63};
 const unsigned flags[]={0,0x40000,0x10000};unsigned pairs=0;
 for(unsigned s=0;s<5;s++)for(unsigned p=0;p<9;p++) {
  struct rusage_global before,after;memset(&before,0xa5,sizeof before);rusage=before;
  original_rss(sizes[s],pages[p]);after=rusage;rusage=before;x86_clear_rss_sub_bridge(sizes[s],pages[p]);
  require(!memcmp(&after,&rusage,sizeof rusage),"RSS actual atomic counter state/int narrowing");pairs++;
  for(unsigned f=0;f<3;f++) {
   struct memobj obj={0};obj.flags=flags[f];rusage=before;original_memobj_rss(&obj,sizes[s],pages[p]);after=rusage;rusage=before;x86_clear_memobj_rss_sub_bridge(&obj,sizes[s],pages[p]);
   require(!memcmp(&after,&rusage,sizeof rusage),"Memobj RSS actual SHM/mapped-file branches/int narrowing");pairs++;
  }
 }
 if(!TEST_RUSAGE_ENABLED){struct rusage_global before={0};rusage=before;original_memobj_rss(NULL,1,4096);x86_clear_memobj_rss_sub_bridge(NULL,1,4096);require(!memcmp(&before,&rusage,sizeof rusage),"disabled accounting does not dereference memobj");pairs++;}
 return pairs;
}
static int operation_ret;
static int flush_op(struct memobj *obj,uintptr_t phys,size_t pg){event(12,norm(obj),phys,pg,(unsigned)operation_ret,obj->flags);obj->flags^=0x1234;obj->size=phys^pg;return operation_ret;}
static unsigned flush(void) {
 const int returns[]={0,-5,7,INT_MIN};const unsigned long phys[]={0,4096,~0UL},pages[]={0,4096,1UL<<21,~0UL};unsigned pairs=0;
 for(unsigned present=0;present<2;present++)for(unsigned r=0;r<4;r++)for(unsigned ph=0;ph<3;ph++)for(unsigned pg=0;pg<4;pg++) {
  struct memobj_ops ops={0};ops.flush_page=present?flush_op:NULL;struct memobj a={0},b={0};a.ops=b.ops=&ops;a.flags=b.flags=0x40000;a.size=b.size=19;operation_ret=returns[r];
  struct trace ta={0},tb={0};active=&ta;live_obj=&a;original_memobj_flush(&a,phys[ph],pages[pg]);active=&tb;live_obj=&b;x86_clear_memobj_flush_bridge(&b,phys[ph],pages[pg]);
  require(!memcmp(&a,&b,sizeof a)&&!memcmp(&ta,&tb,sizeof ta),"memobj actual ops call/args/mutation/ignored errors");require(ta.n==present,"present/missing memobj op exact call count");active=NULL;live_obj=NULL;pairs++;
 }
 return pairs;
}
int main(void) {
 require(fixture_rusage_enabled()==TEST_RUSAGE_ENABLED,"exact real Rust rusage cfg");
 require(fixture_geometry(0)==sizeof(struct rusage_global)&&fixture_geometry(1)==_Alignof(struct rusage_global),"actual Rust/C full rusage geometry");
 require(fixture_geometry(2)==sizeof(struct memobj)&&fixture_geometry(3)==sizeof(struct memobj_ops),"actual Memobj/ops ABI geometry");
 unsigned w=walkers(),r=rss(),f=flush();
 require(w==192&&r==(TEST_RUSAGE_ENABLED?180:181)&&f==96,"fixed batch case counts");
 printf("PASS batch rusage=%d walkers=%u rss=%u flush=%u actual-C/Rust pairs; real accounting/ops; remaining providers controlled\n",TEST_RUSAGE_ENABLED,w,r,f);return 0;
}
