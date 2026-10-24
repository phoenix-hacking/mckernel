/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
extern unsigned long page_hash_lock_bridge(unsigned long);
extern void page_hash_unlock_bridge(unsigned long,unsigned long);
extern void page_hash_lock_init_bridge(unsigned long);
extern struct page *page_hash_alloc_bridge(unsigned long,int);
extern void page_init(void);
extern int page_hash_count_pages(void);
extern int page_hash_tables_init_body_result(unsigned long,unsigned long,int,unsigned long,unsigned long,void(*)(unsigned long),int(*)(struct list_head*));
extern int page_hash_count_all_result(unsigned long,unsigned long,int,unsigned long,unsigned long,unsigned long(*)(unsigned long),void(*)(unsigned long,unsigned long));
extern int page_hash_count_pages_body_result(unsigned long,unsigned long,int,unsigned long,unsigned long,unsigned long(*)(unsigned long),void(*)(unsigned long,unsigned long),int(*)(unsigned long,unsigned long,int,unsigned long,unsigned long,unsigned long(*)(unsigned long),void(*)(unsigned long,unsigned long)));
#include "actual-C-geometry-and-origin.inc"
#include "actual-original-three-untested-bodies.inc"
struct observation{int size;unsigned long flag;char *file;int line;unsigned calls;};
static struct observation observed;static void *allocation_result;
void *kmalloc_tracked(int size,ihk_mc_ap_flag flag,char *file,int line){observed=(struct observation){size,flag,file,line,observed.calls+1};return allocation_result;}
static unsigned phase,provider_error,cycles;
unsigned long cpu_disable_interrupt_save(void){if(phase)provider_error=1;phase=1;return 0x246;}
void preempt_disable(void){if(phase!=1)provider_error=1;phase=2;}
void preempt_enable(void){if(phase!=2)provider_error=1;phase=3;}
void cpu_restore_interrupt(unsigned long flags){if(phase!=3||flags!=0x246)provider_error=1;phase=0;cycles++;}
void cpu_pause(void){provider_error=1;}
static struct page allocated[2],nodes[6];
static unsigned char saved_heads[sizeof page_hash],saved_locks[sizeof page_hash_locks];
static int alloc_pair(unsigned long size,int flag,unsigned r){
 struct observation first;allocation_result=r?&allocated[r-1]:0;memset(&observed,0,sizeof observed);
 struct page *a=original_page_hash_alloc_bridge(size,flag);first=observed;memset(&observed,0,sizeof observed);
 struct page *b=page_hash_alloc_bridge(size,flag);
 return a!=allocation_result||b!=a||first.calls!=1||observed.calls!=1||first.size!=(int)size||observed.size!=first.size||first.flag!=(unsigned long)flag||observed.flag!=first.flag||strcmp(first.file,"/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/pagehash-alloc-init-count-batch-preparation-1/fixture/actual-original-three-untested-bodies.inc")||first.line!=3||observed.file!=page_hash_alloc_file||observed.line!=page_hash_alloc_line;
}
static int check_initialized(void){for(int i=0;i<PHYS_PAGE_HASH_SIZE;i++)if(page_hash[i].next!=&page_hash[i]||page_hash[i].prev!=&page_hash[i]||page_hash_locks[i].head_tail)return 1;return 0;}
static int init_pair(unsigned char dirty){memset(page_hash,dirty,sizeof page_hash);memset(page_hash_locks,dirty,sizeof page_hash_locks);original_page_init();if(check_initialized())return 1;memcpy(saved_heads,page_hash,sizeof page_hash);memcpy(saved_locks,page_hash_locks,sizeof page_hash_locks);memset(page_hash,dirty,sizeof page_hash);memset(page_hash_locks,dirty,sizeof page_hash_locks);page_init();return check_initialized()||memcmp(saved_heads,page_hash,sizeof page_hash)||memcmp(saved_locks,page_hash_locks,sizeof page_hash_locks);}
static void setup_count(unsigned n,unsigned mode){page_init();memset(nodes,0,sizeof nodes);for(unsigned i=0;i<n;i++){unsigned b=mode==0?0:mode==1?(i%3==0?0:i%3==1?PHYS_PAGE_HASH_SIZE/2:PHYS_PAGE_HASH_SIZE-1):PHYS_PAGE_HASH_SIZE-1;struct list_head *h=&page_hash[b],*x=&nodes[i].hash;x->next=h->next;x->prev=h;h->next->prev=x;h->next=x;}}
static int count_pair(unsigned n,unsigned mode){setup_count(n,mode);phase=provider_error=cycles=0;int a=original_page_hash_count_pages();if(a!=(int)n||phase||provider_error||cycles!=PHYS_PAGE_HASH_SIZE)return 1;memcpy(saved_heads,page_hash,sizeof page_hash);memcpy(saved_locks,page_hash_locks,sizeof page_hash_locks);setup_count(n,mode);phase=provider_error=cycles=0;int b=page_hash_count_pages();return a!=b||phase||provider_error||cycles!=PHYS_PAGE_HASH_SIZE||memcmp(saved_heads,page_hash,sizeof page_hash)||memcmp(saved_locks,page_hash_locks,sizeof page_hash_locks);}
int main(void){const unsigned long sizes[]={0,1,sizeof(struct page),2147483647UL,2147483648UL,4294967295UL,4294967296UL,~0UL};const int flags[]={(-2147483647-1),-1,0,IHK_MC_AP_CRITICAL,IHK_MC_AP_NOWAIT,2147483647};unsigned ac=0,ic=0,cc=0;for(unsigned i=0;i<8;i++)for(unsigned j=0;j<6;j++)for(unsigned r=0;r<3;r++){if(alloc_pair(sizes[i],flags[j],r))return 11;ac++;}for(unsigned d=0;d<2;d++){if(init_pair(d?0xa5:0xff))return 12;ic++;}for(unsigned n=0;n<=6;n++)for(unsigned m=0;m<3;m++){if(count_pair(n,m))return 13;cc++;}__builtin_printf("PASS actualOriginalC_Rust alloc=%u init=%u count=%u total=%u\n",ac,ic,cc,ac+ic+cc);return 0;}
