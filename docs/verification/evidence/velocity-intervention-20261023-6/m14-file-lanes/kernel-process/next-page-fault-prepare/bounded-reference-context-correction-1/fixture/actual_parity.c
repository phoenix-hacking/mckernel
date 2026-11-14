/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual original C preparation block vs actual Rust slice. Lock, lookup, TLB
 * and adjustment effects are controlled host observations, never kernel effects.
 */
#include <process.h>
#include <ihk/debug.h>
#include <string.h>
#undef memset
extern int printf(const char *,...);
extern void exit(int);
extern void fixture_layout(unsigned long *);
extern int process_page_fault_prepare_body_result(struct process_vm *,struct vm_range *,uintptr_t,uint64_t,pte_t **,void **,size_t *,int *,int *);
extern int fixture_actual_smaller_page_size(uint64_t,int,uint64_t *,int *);
struct ddebug process_page_fault_prepare_bounds_debug;
static struct process_vm vm;
static struct address_space address_spaces[2];
static struct vm_range range;
static pte_t live_pte;
static int scenario,debugging,held,active,comparisons,small_calls;
static uint64_t reason_value;
static const uintptr_t fault=0x40001000ULL;
struct event {int kind,value;};
struct result {int action,error,align,held,count,pte_nonnull;unsigned long base,size,pte;struct event events[16];};
static struct result tape;
static void need(int ok,int line) {
 if(!ok){printf("FAIL functional page-fault prepare line=%d comparisons=%d scenario=%d reason=%llx debug=%d\n",line,comparisons,scenario,(unsigned long long)reason_value,debugging);exit(1);}
}
#define CHECK(x) need(!!(x),__LINE__)
static void event(int kind,int value) {
 CHECK(active&&tape.count<16);tape.events[tape.count++]=(struct event){kind,value};
}
void __ihk_mc_spinlock_lock_noirq(ihk_spinlock_t *lock) {
 CHECK(lock==&vm.page_table_lock&&!held);held=1;event(1,0);
 if(scenario==8){vm.address_space=&address_spaces[1];range.pgshift=21;}
}
pte_t *ihk_mc_pt_lookup_pte(page_table_t pt,void *virt,int pgshift,void **base,size_t *size,int *align) {
 CHECK(held&&virt==(void *)fault);
 CHECK(pt==address_spaces[scenario==8].page_table);
 CHECK(pgshift==(scenario==8?21:12));event(2,0);
 if(scenario==5||scenario==10){*base=(void *)0x40000000ULL;*size=1ULL<<21;*align=9;}
 else if(scenario==6||scenario==11){*base=(void *)0x40000000ULL;*size=1ULL<<30;*align=18;}
 else {*base=(void *)fault;*size=4096;*align=0;}
 if(scenario==9){live_pte=0x1000;range.flag=0xfedcba9876543210UL;}
 return scenario>=1&&scenario<=4||scenario==9?&live_pte:0;
}
void flush_tlb_single(unsigned long addr) {
 CHECK(held&&addr==fault);event(4,0);live_pte=0x99887001ULL;
}
int arch_get_smaller_page_size(void *args,size_t old,size_t *size,int *align) {
 CHECK(held&&!args);event(5,0);small_calls++;
 uint64_t next=0;int result=fixture_actual_smaller_page_size(old,1,&next,align);*size=next;
 if(scenario==11){range.start=0x40000000ULL;range.end=0x40200000ULL;}
 return result;
}
void fixture_adjust_effect(void *pt,unsigned long addr,pte_t *pte,void **base,size_t *size) {
 CHECK(held&&pt==vm.address_space->page_table&&addr==fault);
 CHECK(!small_calls||!pte);event(6,0);
 if(scenario==8){*base=(void *)(fault+8);*size=2048;}
}
int kprintf(const char *format,...) {
 __builtin_va_list ap;__builtin_va_start(ap,format);
 if(!strcmp(format,"%s: pgaddr=%lx,range->start=%lx,range->end=%lx,pgaddr+pgsize=%lx\n")) {
  CHECK(!strcmp(__builtin_va_arg(ap,const char *),"page_fault_process_memory_range"));
  void *base=__builtin_va_arg(ap,void *);uintptr_t start=__builtin_va_arg(ap,uintptr_t),end=__builtin_va_arg(ap,uintptr_t);void *limit=__builtin_va_arg(ap,void *);
  CHECK(held&&start==range.start&&end==range.end);
  size_t size=scenario==5||scenario==10?1ULL<<21:scenario==6||scenario==11?1ULL<<30:4096;
  CHECK((uintptr_t)limit==(uintptr_t)base+size);event(3,0);
  if(scenario==10){range.start=fault;range.end=fault+4096;}
 } else {
  int expected=!strcmp(format,"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):PROT_NONE. %d\n")?-14:-12;
  CHECK(expected==-14||!strcmp(format,"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):arch_get_smaller_page_size(pte) failed. %d\n"));
  CHECK(__builtin_va_arg(ap,struct process_vm *)==&vm);
  CHECK(__builtin_va_arg(ap,uintptr_t)==range.start&&__builtin_va_arg(ap,uintptr_t)==range.end);
  CHECK(__builtin_va_arg(ap,unsigned long)==range.flag);
  CHECK(__builtin_va_arg(ap,uintptr_t)==fault&&__builtin_va_arg(ap,uint64_t)==reason_value);
  CHECK(__builtin_va_arg(ap,int)==expected);event(7,expected);
 }
 __builtin_va_end(ap);return -77;
}
#undef dkprintf
#define dkprintf(fmt,args...) do {if(process_page_fault_prepare_bounds_debug.flags)kprintf(fmt,##args);}while(0)
static int original(struct process_vm *vm,struct vm_range *range,uintptr_t fault_addr,uint64_t reason,
 pte_t **po,void **bo,size_t *so,int *ao,int *eo) {
 int error=*eo;pte_t *ptep;void *pgaddr;size_t pgsize;int p2align;
/* Restore the extracted block's original enclosing function identity.
 * The strict logger oracle below remains unchanged. */
#define __FUNCTION__ "page_fault_process_memory_range"
#include "original_page_fault_prepare.ACTUAL-C-BLOCK.inc"
#undef __FUNCTION__
 *po=ptep;*bo=pgaddr;*so=pgsize;*ao=p2align;*eo=error;return 0;
out:
 *po=ptep;*bo=pgaddr;*so=pgsize;*ao=p2align;*eo=error;return 1;
}
static void setup(void) {
 memset(&vm,0,sizeof(vm));memset(&range,0,sizeof(range));memset(&tape,0,sizeof(tape));
 memset(address_spaces,0,sizeof(address_spaces));
 address_spaces[0].page_table=(page_table_t)0x11110000UL;address_spaces[1].page_table=(page_table_t)0x22220000UL;
 vm.address_space=&address_spaces[0];range.start=fault;range.end=fault+4096;range.flag=0x123456789abcdef0UL;range.pgshift=12;
 if(scenario==7){range.start=fault+4096;range.end=fault+8192;}
 if(scenario==10){range.start=0x40000000ULL;range.end=0x40200000ULL;}
 live_pte=scenario==2?0x800:scenario==3||scenario==9?1:scenario==4?0x1000:0;
 process_page_fault_prepare_bounds_debug.flags=debugging;held=0;small_calls=0;
}
static struct result run(int rust) {
 setup();pte_t *p=0;void *base=0;size_t size=0;int align=99,error=0x1234567;active=1;
 int action=rust?process_page_fault_prepare_body_result(&vm,&range,fault,reason_value,&p,&base,&size,&align,&error):
                 original(&vm,&range,fault,reason_value,&p,&base,&size,&align,&error);
 CHECK(held==1);tape.action=action;tape.error=error;tape.align=align;tape.held=held;tape.pte_nonnull=p!=0;
 tape.base=(unsigned long)base;tape.size=size;tape.pte=live_pte;
 active=0;held=0;return tape;
}
static void push(struct result *r,int kind,int value) {
 CHECK(r->count<16);r->events[r->count++]=(struct event){kind,value};
}
static struct result oracle(void) {
 struct result r={0};r.held=1;r.error=0x1234567;r.base=fault;r.size=4096;r.align=0;
 r.pte=scenario==2?0x800:scenario==3?1:scenario==4||scenario==9?0x1000:0;
 r.pte_nonnull=scenario>=1&&scenario<=4||scenario==9;
 if(scenario==5||scenario==10){r.base=0x40000000ULL;r.size=1ULL<<21;r.align=9;}
 if(scenario==6||scenario==11){r.base=0x40000000ULL;r.size=1ULL<<30;r.align=18;}
 push(&r,1,0);push(&r,2,0);
 int prot=(reason_value&PF_PROT)!=0,patch=(reason_value&PF_PATCH)!=0;
 if(!prot&&!patch&&r.pte_nonnull&&r.pte&&!(r.pte&0x800)) {
  r.action=1;r.error=(r.pte&1)?0:-14;
  if(r.error)push(&r,7,-14);
  return r;
 }
 if(prot&&(!r.pte_nonnull||!(r.pte&1))) {
  push(&r,4,0);r.pte=0x99887001ULL;r.action=1;r.error=0;return r;
 }
 if(debugging)push(&r,3,0);
 int shrinks=scenario==5?1:scenario==6?2:scenario==7?1:scenario==10?(debugging?1:0):scenario==11?1:0;
 for(int i=0;i<shrinks;i++)push(&r,5,0);
 if(shrinks){r.pte_nonnull=0;r.error=0;}
 if(scenario==7){r.error=-12;r.size=0;r.align=-1;r.action=1;push(&r,7,-12);return r;}
 if(shrinks){r.size=scenario==11?1ULL<<21:4096;r.align=scenario==11?9:0;r.base=fault&~(r.size-1);}
 push(&r,6,0);
 if(scenario==8){r.base=fault+8;r.size=2048;}
 return r;
}
int main(void) {
 unsigned long actual[13],wanted[13]={sizeof(struct process_vm),__alignof__(struct process_vm),__builtin_offsetof(struct process_vm,address_space),__builtin_offsetof(struct process_vm,page_table_lock),
 sizeof(struct address_space),__builtin_offsetof(struct address_space,page_table),sizeof(struct vm_range),__builtin_offsetof(struct vm_range,start),__builtin_offsetof(struct vm_range,end),__builtin_offsetof(struct vm_range,flag),__builtin_offsetof(struct vm_range,pgshift),sizeof(ihk_spinlock_t),sizeof(struct ddebug)};
 fixture_layout(actual);CHECK(!memcmp(actual,wanted,sizeof(actual)));
 const uint64_t reasons[]={0,PF_PROT,PF_PATCH,PF_PROT|PF_PATCH|0x8000000000000000ULL};
 for(scenario=0;scenario<12;scenario++)for(int q=0;q<4;q++)for(int d=0;d<2;d++) {
  reason_value=reasons[q];debugging=d?255:0;
  struct result c=run(0),r=run(1),expected=oracle();
  CHECK(!memcmp(&c,&r,sizeof(c)));CHECK(!memcmp(&c,&expected,sizeof(c)));comparisons++;
 }
 CHECK(comparisons==96);
 printf("page_fault_prepare actual_original_C_Rust_comparisons=96 exact_lock_retention=1 controlled_host_effects=1\n");
 return 0;
}
