/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Original complete C/Rust bodies. These host allocation/range/translation
 * effect adapters do not execute backend/kernel ownership or native mapping. */
#include <process.h>
#include <memobj.h>
#include <page.h>
#include <syscall.h>
#include <memory.h>
#include <ihk/debug.h>
#include <string.h>
#undef memset
extern int printf(const char *,...);extern void exit(int);
extern void fixture_layout(unsigned long *);
extern int process_page_fault_cow_classify_body_result(struct vm_range *,uint64_t,struct page *);
static int fixture_gate(const char *);
#undef dkprintf
#define dkprintf(fmt,args...) do {if(fixture_gate(fmt))kprintf(fmt,##args);}while(0)
#include "original_lexical_reference.inc"
#undef dkprintf
#define extend_process_region fixture_selected_extend_process_region
#line 1 "held-current-COW-process.c"
#include "extend_region.ACTUAL-C-SELECTION.inc"
#undef extend_process_region
#line 1 "extend-cow-functional-fixture"
struct vector {unsigned long end,address,heap,wanted,len;int npages,shift,align;unsigned long align_size,mask;};
static const struct vector vectors[]={
 {0x10000000UL,0x10000001UL,0x0UL,0x10001000UL,0x1000UL,1,12,0,0x1000UL,0xfffffffffffff000UL},
 {0x10000000UL,0x10000000UL,0x1000UL,0x10001000UL,0x1000UL,1,12,0,0x1000UL,0xfffffffffffff000UL},
 {0x10000000UL,0x10000001UL,0x2000UL,0x10200000UL,0x200000UL,512,21,9,0x200000UL,0xffffffffffe00000UL},
 {0x10001000UL,0x10002000UL,0x2000UL,0x10200000UL,0x1ff000UL,511,21,9,0x200000UL,0xffffffffffe00000UL},
 {0x10000000UL,0xffffffffffffffffUL,0x0UL,0x0UL,0xfffffffff0000000UL,-65536,12,0,0x1000UL,0xfffffffffffff000UL},
 {0xfffffffffffff000UL,0xffffffffffffffffUL,0x1000UL,0x0UL,0x1000UL,1,12,0,0x1000UL,0xfffffffffffff000UL},
 {0xfffffffffffff000UL,0xfffffffffffff000UL,0x2000UL,0x200000UL,0x201000UL,513,21,9,0x200000UL,0xffffffffffe00000UL},
 {0x0UL,0x80000000000UL,0x0UL,0x80000000000UL,0x80000000000UL,-2147483648,12,0,0x1000UL,0xfffffffffffff000UL},
 {0x0UL,0x100000000000UL,0x0UL,0x100000000000UL,0x100000000000UL,0,12,0,0x1000UL,0xfffffffffffff000UL},
 {0x10000000UL,0x10000000UL,0x0UL,0x10000000UL,0x0UL,0,12,0,0x1000UL,0xfffffffffffff000UL},
};
struct event {int kind,x,y;unsigned long a,b,c,d;};
struct tape {unsigned long result,mpol;int count,allocated,transferred;struct event e[8];};
static struct tape tape;
static struct process_vm vm;static struct process proc;static struct vm_range range;
static struct memobj obj;static struct page page;
static const struct vector *v;
static int action,dbg,mpol,comparisons,extend_comparisons,cow_comparisons;
static void need(int ok,int line) {
 if(!ok){printf("FAIL functional extend/COW line=%d comparisons=%d action=%d vector=%ld debug=%d mpol=%d\n",line,comparisons,action,(long)(v?v-vectors:-1),dbg,mpol);exit(1);}
}
#define CHECK(x) need(!!(x),__LINE__)
static void event(int k,int x,int y,unsigned long a,unsigned long b,unsigned long c,unsigned long d) {
 CHECK(tape.count<8);tape.e[tape.count++]=(struct event){k,x,y,a,b,c,d};
}
static int gate(int which) {
 static const int gates[4][3]={{0,0,0},{1,1,1},{2,0,255},{0,255,0}};
 return gates[dbg][which];
}
static int fixture_gate(const char *fmt) {
 if(!strcmp(fmt,"%s: warning: vm_range for extension already exists\n"))return gate(0);
 if(!strcmp(fmt,"%s: warning: failed to allocate %d contiguous pages  (bytes: %lu, pgshift: %d), enabling demand paging\n"))return gate(1);
 CHECK(!strcmp(fmt,"%s: new_end_allocated: 0x%lx, align_size: %lu, align_mask: %lx\n"));
 return gate(2);
}
static int add_error(void){return action==4||action==5?-12:action==6||action==7?17:0;}
static int demanded(void){return action==1||action==5;}
static int allocation_fails(void){return action==3||action==6;}
struct vm_range *lookup_process_memory_range(struct process_vm *p,uintptr_t start,uintptr_t end) {
 CHECK(p==&vm&&start==v->end&&end==v->wanted);
 event(1,0,0,start,end,0,0);
 if(action==7)proc.mpol_flags^=MPOL_NO_HEAP;
 return action==0?&range:0;
}
void *_ihk_mc_alloc_aligned_pages_node(int n,int align,ihk_mc_ap_flag flag,int node,int user,uintptr_t addr,char *file,int line) {
 CHECK(n==v->npages&&align==v->align&&node==-1&&user==IHK_MC_PG_USER&&addr==v->end);
 CHECK(flag==(IHK_MC_AP_NOWAIT|(!(proc.mpol_flags&MPOL_NO_HEAP)?IHK_MC_AP_USER:0)));
 CHECK(!strcmp(file,"held-current-COW-process.c")&&line==3408);
 event(2,n,align,flag,addr,(unsigned long)node,user);
 tape.allocated=!allocation_fails();return allocation_fails()?0:(void *)0x80000000UL;
}
unsigned long virt_to_phys(void *p) {
 CHECK(p==(void *)0x80000000UL&&tape.allocated);
 event(3,0,0,(unsigned long)p,0,0,0);return 0x12345000UL;
}
int add_process_memory_range(struct process_vm *p,unsigned long start,unsigned long end,
 unsigned long phys,unsigned long flag,struct memobj *memobj,off_t offset,int shift,void *data,struct vm_range **rp) {
 CHECK(p==&vm&&start==v->end&&end==v->wanted&&!memobj&&!offset&&shift==v->shift&&!data&&!rp);
 CHECK(phys==(tape.allocated?0x12345000UL:0));
 CHECK(flag==(0x8000000000000000UL|((demanded()||allocation_fails())?VR_DEMAND_PAGING:0)));
 event(4,add_error(),shift,start,end,phys,flag);
 if(!add_error())tape.transferred=tape.allocated;
 return add_error();
}
void _ihk_mc_free_pages(void *p,int n,int user,char *file,int line) {
 CHECK(p==(tape.allocated?(void *)0x80000000UL:0)&&n==v->npages&&user==IHK_MC_PG_USER);
 CHECK(!strcmp(file,"held-current-COW-process.c")&&line==3423&&add_error());
 event(5,n,user,(unsigned long)p,0,0,0);tape.allocated=0;
}
int kprintf(const char *fmt,...) {
 __builtin_va_list ap;__builtin_va_start(ap,fmt);
 CHECK(!strcmp(__builtin_va_arg(ap,const char *),"extend_process_region"));
 if(!strcmp(fmt,"%s: warning: vm_range for extension already exists\n")) {
  CHECK(action==0&&gate(0));event(6,0,0,0,0,0,0);
 }else if(!strcmp(fmt,"%s: warning: failed to allocate %d contiguous pages  (bytes: %lu, pgshift: %d), enabling demand paging\n")) {
  int n=__builtin_va_arg(ap,int);size_t len=__builtin_va_arg(ap,size_t);
  unsigned long align=__builtin_va_arg(ap,unsigned long);
  CHECK(allocation_fails()&&gate(1)&&n==v->npages&&len==v->len&&align==(unsigned long)v->align);
  event(7,n,0,len,align,0,0);
 }else{
  CHECK(!strcmp(fmt,"%s: new_end_allocated: 0x%lx, align_size: %lu, align_mask: %lx\n")&&gate(2)&&!add_error());
  unsigned long end=__builtin_va_arg(ap,unsigned long);size_t size=__builtin_va_arg(ap,size_t);
  unsigned long mask=__builtin_va_arg(ap,unsigned long);
  CHECK(end==v->wanted&&size==v->align_size&&mask==v->mask);event(8,0,0,end,size,mask,0);
 }
 __builtin_va_end(ap);return -77;
}
static struct tape run_extend(int rust) {
 memset(&vm,0,sizeof(vm));memset(&proc,0,sizeof(proc));memset(&range,0,sizeof(range));memset(&tape,0,sizeof(tape));
 vm.proc=&proc;proc.heap_extension=v->heap;proc.mpol_flags=mpol?MPOL_NO_HEAP:0;
 process_extend_region_exists_debug.flags=gate(0);process_extend_region_alloc_debug.flags=gate(1);process_extend_region_success_debug.flags=gate(2);
 unsigned long flag=0x8000000000000000UL|(demanded()?VR_DEMAND_PAGING:0);
 tape.result=rust?fixture_selected_extend_process_region(&vm,v->end,v->address,flag):
  fixture_original_extend_process_region(&vm,v->end,v->address,flag);
 tape.mpol=proc.mpol_flags;
 CHECK(proc.heap_extension==v->heap&&vm.proc==&proc);
 return tape;
}
static void expected_push(struct tape *t,int k,int x,int y,unsigned long a,unsigned long b,unsigned long c,unsigned long d) {
 CHECK(t->count<8);t->e[t->count++]=(struct event){k,x,y,a,b,c,d};
}
static struct tape oracle_extend(void) {
 struct tape t={0};t.mpol=(mpol?MPOL_NO_HEAP:0)^(action==7?MPOL_NO_HEAP:0);
 expected_push(&t,1,0,0,v->end,v->wanted,0,0);
 if(action==0){
  t.result=v->end;if(gate(0))expected_push(&t,6,0,0,0,0,0,0);return t;
 }
 int allocated=!demanded()&&!allocation_fails();
 if(!demanded()){
  unsigned long f=IHK_MC_AP_NOWAIT|(!(t.mpol&MPOL_NO_HEAP)?IHK_MC_AP_USER:0);
  expected_push(&t,2,v->npages,v->align,f,v->end,(unsigned long)-1,IHK_MC_PG_USER);
  if(allocation_fails()&&gate(1))expected_push(&t,7,v->npages,0,v->len,v->align,0,0);
 }
 if(allocated)expected_push(&t,3,0,0,0x80000000UL,0,0,0);
 unsigned long f=0x8000000000000000UL|((demanded()||allocation_fails())?VR_DEMAND_PAGING:0);
 expected_push(&t,4,add_error(),v->shift,v->end,v->wanted,allocated?0x12345000UL:0,f);
 if(add_error()){
  expected_push(&t,5,v->npages,IHK_MC_PG_USER,allocated?0x80000000UL:0,0,0,0);
  t.result=v->end;return t;
 }
 t.allocated=t.transferred=allocated;t.result=v->wanted;
 if(gate(2))expected_push(&t,8,0,0,v->wanted,v->align_size,v->mask,0);
 return t;
}
static int original_cow(struct vm_range *range,uint64_t reason,struct page *page) {
 int private_range,patching_to_rdonly,devfile_or_hugetlbfs_or_premap,regfile_or_shm;
#include "original_classify.ACTUAL-C.inc"
  return 1;
 }
 return 0;
}
int main(void) {
 unsigned long actual[21],wanted[21]={
 sizeof(struct process_vm),__alignof__(struct process_vm),__builtin_offsetof(struct process_vm,proc),
 sizeof(struct process),__alignof__(struct process),__builtin_offsetof(struct process,mpol_flags),__builtin_offsetof(struct process,heap_extension),
 sizeof(proc.mpol_flags),sizeof(proc.heap_extension),sizeof(struct ddebug),__alignof__(struct ddebug),
 sizeof(struct vm_range),__builtin_offsetof(struct vm_range,flag),__builtin_offsetof(struct vm_range,memobj),
 sizeof(struct memobj),__builtin_offsetof(struct memobj,flags),
 sizeof(struct page),__alignof__(struct page),__builtin_offsetof(struct page,mode),__builtin_offsetof(struct page,count),sizeof(ihk_atomic_t)};
 fixture_layout(actual);CHECK(!memcmp(actual,wanted,sizeof(actual)));
 CHECK(!strcmp(process_extend_region_exists_debug.file,"held-current-COW-process.c")&&
 !strcmp(process_extend_region_alloc_debug.func,"extend_process_region")&&
 !strcmp(process_extend_region_success_debug.func,"extend_process_region"));
 CHECK(process_extend_region_exists_debug.line==3394&&process_extend_region_alloc_debug.line==3411&&process_extend_region_success_debug.line==3428);
 CHECK(!process_extend_region_exists_debug.fmt&&!process_extend_region_alloc_debug.fmt&&!process_extend_region_success_debug.fmt);
 for(unsigned q=0;q<sizeof(vectors)/sizeof(vectors[0]);q++)for(action=0;action<8;action++)for(dbg=0;dbg<4;dbg++)for(mpol=0;mpol<2;mpol++){
  v=&vectors[q];struct tape c=run_extend(0),r=run_extend(1),e=oracle_extend();
  CHECK(!memcmp(&c,&r,sizeof(c)));CHECK(!memcmp(&c,&e,sizeof(c)));comparisons++;extend_comparisons++;
 }
 unsigned long flags[]={0,VR_PRIVATE,VR_PROT_WRITE,VR_PRIVATE|VR_PROT_WRITE};
 uint64_t reasons[]={0,PF_PATCH,0x8000000000000000ULL,PF_PATCH|0x8000000000000000ULL};
 unsigned char modes[]={0,1,2,3,4,5,6,7,255};int counts[]={(-2147483647-1),-1,0,1,2,2147483647};
 for(int f=0;f<4;f++)for(int z=0;z<4;z++)for(int p=0;p<10;p++)for(int n=0;n<6;n++)for(int m=0;m<4;m++){
  memset(&range,0,sizeof(range));memset(&obj,0,sizeof(obj));memset(&page,0,sizeof(page));
  range.flag=flags[f]|0x8000000000000000UL;range.memobj=m?&obj:0;
  obj.flags=m==2?MF_ZEROOBJ:m==3?0xffffffffU:0;
  page.mode=p?modes[p-1]:255;page.count.counter=counts[n];
  struct page *pp=p?&page:0;struct vm_range before_range=range;struct memobj before_obj=obj;struct page before_page=page;
  int c=original_cow(&range,reasons[z],pp);
  int r=process_page_fault_cow_classify_body_result(&range,reasons[z],pp);
  int in_object=p&&page.mode>=PM_WILL_PAGEIO&&page.mode<=PM_MAPPED;
  int expected=((flags[f]&VR_PRIVATE)||((reasons[z]&PF_PATCH)&&!(flags[f]&VR_PROT_WRITE)))&&p&&(in_object||counts[n]>1);
  CHECK(c==r&&c==!!expected);
  CHECK(!memcmp(&range,&before_range,sizeof(range))&&!memcmp(&obj,&before_obj,sizeof(obj))&&!memcmp(&page,&before_page,sizeof(page)));
  comparisons++;cow_comparisons++;
 }
 CHECK(extend_comparisons==640&&cow_comparisons==3840&&comparisons==4480);
 printf("extend_region_and_cow actual_original_C_Rust_comparisons=4480 extend=640 cow=3840 controlled_host_effects=1\n");return 0;
}
