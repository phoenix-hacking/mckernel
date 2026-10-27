/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Current C/Rust consumer argument checks. Allocator effects only record arguments.
 */
#include <process.h>
#include <kmalloc.h>
#include <ihk/mm.h>
extern int printf(const char *, ...);
extern void abort(void);
#define CHECK(t) do { if (!(t)) { printf("FAIL line13 line=%d: %s\n", __LINE__, #t); abort(); } } while (0)
static int same(const char *a, const char *b) { while (*a && *a == *b) { ++a; ++b; } return *a == *b; }
#include "exact_metadata.ACTUAL-C.inc"

/* Retained Source10 creator effect-record shape and allocation boundary. */
struct event { int kind; unsigned long value[8]; const char *file; const char *format; const char *name; };
static struct event actual, expected;
static void *alloc_result;
void *fixture_alloc(int n,int a,ihk_mc_ap_flag f,int node,int k,uintptr_t v,char *file,int line) {
 CHECK(actual.kind==0); actual.kind=1; actual.value[0]=(unsigned long)n;actual.value[1]=(unsigned long)a;
 actual.value[2]=f;actual.value[3]=(unsigned long)node;actual.value[4]=(unsigned long)k;
 actual.value[5]=v;actual.value[6]=(unsigned long)line;actual.file=file;return alloc_result;
}
void *_ihk_mc_alloc_aligned_pages_node(int n,int a,ihk_mc_ap_flag f,int node,int k,uintptr_t v,char *file,int line) {
 return fixture_alloc(n,a,f,node,k,v,file,line);
}
/* Same external tracked-free effect as the retained Source10 thread fixture. */
void fixture_free(void *ptr,int pages,int kind,char *file,int line) {
 CHECK(actual.kind==0); actual.kind=3; actual.value[0]=(unsigned long)ptr;
 actual.value[1]=(unsigned long)pages;actual.value[2]=(unsigned long)kind;
 actual.value[3]=(unsigned long)line;actual.file=file;
}
void _ihk_mc_free_pages(void *ptr,int pages,int kind,char *file,int line) {
 fixture_free(ptr,pages,kind,file,line);
}
/* Retained Source5 tracked-allocation boundary; only observable arguments differ. */
void *fixture_tracked_alloc(int size,unsigned long flags,char *file,int line) {
 CHECK(actual.kind==0);actual.kind=4;actual.value[0]=(unsigned long)size;
 actual.value[1]=flags;actual.value[2]=(unsigned long)line;actual.file=file;return alloc_result;
}
void fixture_tracked_free(void *ptr,char *file,int line) {
 CHECK(actual.kind==0);actual.kind=5;actual.value[0]=(unsigned long)ptr;
 actual.value[1]=(unsigned long)line;actual.file=file;
}
void *kmalloc_tracked(int size,unsigned long flags,char *file,int line) {
 return fixture_tracked_alloc(size,flags,file,line);
}
void kfree_tracked(void *ptr,char *file,int line) { fixture_tracked_free(ptr,file,line); }
/* Retained creator logger boundary. Anonymous cases deliberately allocate once
 * successfully, so no anonymous error formatting or retry behavior is claimed. */
int kprintf(const char *format,...) {
 CHECK(actual.kind==0);actual.kind=2;actual.format=format;
 __builtin_va_list args;__builtin_va_start(args,format);actual.name=__builtin_va_arg(args,const char *);
 if (same(format,"%s: pid: %d, CPU: %d\n")) {
  actual.value[0]=(unsigned long)__builtin_va_arg(args,int);actual.value[1]=(unsigned long)__builtin_va_arg(args,int);
 } else CHECK(same(format,"%s: invalid CPU requested in initial cpu_set\n"));
 __builtin_va_end(args);return 0;
}
/* Existing current x86 geometry owner consumes the same readonly address cell. */
static int use_1gb_page=1;
const int *const x86_clear_l3_use_1gb_page=&use_1gb_page;

#include "five_original_references.C.inc"

extern void *rust_create(int,unsigned long) __asm__("process_create_thread_alloc_pages_bridge");
extern struct vm_range *rust_split(unsigned long,unsigned long) __asm__("process_split_range_alloc_bridge");
extern void rust_thread_free(void *) __asm__("process_free_thread_pages_bridge");
extern void fixture_invoke_free_range_pages(void *,unsigned long);
extern int process_page_fault_anon_allocate_body_result(struct process_vm *,struct vm_range *,
        unsigned long,unsigned long,unsigned long **,void **,size_t *,int *,void **,int *);
extern const unsigned long LINE13_RUST_ABI[13];
static const unsigned long C_ABI[13]={sizeof(int),__alignof__(int),sizeof(unsigned long),sizeof(void *),
 sizeof(struct vm_range),__alignof__(struct vm_range),__builtin_offsetof(struct vm_range,flag),
 __builtin_offsetof(struct vm_range,pgshift),sizeof(struct process_vm),PAGE_SIZE,PAGE_P2ALIGN,IHK_MC_PG_KERNEL,IHK_MC_PG_USER};
static void reset(void) { actual=(struct event){0}; }
static void save(void) { expected=actual;reset(); }
static void compare(int kind,int line) {
 CHECK(actual.kind==kind && actual.kind==expected.kind);
 for(int i=0;i<8;++i) CHECK(actual.value[i]==expected.value[i]);
 CHECK(same(actual.file,expected.file) && same(actual.file,"/src/kernel/process.c"));
 CHECK(actual.value[kind==1?6:kind==4?2:3]==(unsigned long)line);
 reset();
}
int main(void) {
 for(int i=0;i<13;++i) CHECK(C_ABI[i]==LINE13_RUST_ABI[i]);
 CHECK(sizeof(process_create_thread_alloc_pages_source_line)==4);
 CHECK(sizeof(process_split_range_alloc_source_line)==4 && sizeof(process_free_range_pages_source_line)==4);
 CHECK(sizeof(process_free_thread_pages_source_line)==4 && sizeof(process_page_fault_anon_alloc_line)==4);
 const int pages[]={(-2147483647-1),-1,0,1,2,2147483647};
 const unsigned long flags[]={0,1,~0UL};
 const unsigned long sizes[]={0,1,2147483647UL,0x80000000UL,0xffffffffUL,0x100000001UL,~0UL};
 static char storage[2];int comparisons=0;
 for(int n=0;n<6;++n)for(int f=0;f<3;++f)for(int ok=0;ok<2;++ok) {
  alloc_result=ok?&storage[0]:NULL;reset();
  void *reference=reference_process_create_thread_alloc_pages_bridge(pages[n],flags[f]);
  CHECK(reference==alloc_result && actual.value[6]==788);save();
  CHECK(rust_create(pages[n],flags[f])==reference);compare(1,788);++comparisons;
 }
 for(int n=0;n<7;++n)for(int f=0;f<3;++f)for(int ok=0;ok<2;++ok) {
  alloc_result=ok?&storage[0]:NULL;reset();
  void *reference=reference_process_split_range_alloc_bridge(sizes[n],flags[f]);
  CHECK(reference==alloc_result && actual.value[0]==(unsigned long)(int)sizes[n]);save();
  CHECK(rust_split(sizes[n],flags[f])==reference);compare(4,1628);++comparisons;
 }
 void *pointers[]={NULL,&storage[0],&storage[1]};
 for(int i=0;i<3;++i) {
  reset();reference_process_free_thread_pages_bridge(pointers[i]);
  CHECK(actual.kind==3 && actual.value[1]==KERNEL_STACK_NR_PAGES && actual.value[3]==3501);save();
  rust_thread_free(pointers[i]);compare(3,3501);++comparisons;
  for(int n=0;n<7;++n) {
   reset();reference_process_free_range_pages_bridge(pointers[i],sizes[n]);
   CHECK(actual.value[1]==(unsigned long)(int)sizes[n]);save();
   fixture_invoke_free_range_pages(pointers[i],sizes[n]);compare(3,1873);++comparisons;
  }
 }
 /* Original anonymous allocator body, exact current VmRange and CInt conversion.
  * Successful controlled allocations isolate this changed provenance argument. */
 const unsigned long spans[]={0,1,PAGE_SIZE,0x200000UL,0x100000001000UL,~0UL};
 const int aligns[]={-1,0,2147483647};
 const unsigned long addresses[]={0,0x12345000UL,~0UL};
 struct vm_range range={0};
 for(int n=0;n<6;++n)for(int a=0;a<3;++a)for(int u=0;u<2;++u)for(int v=0;v<3;++v) {
  range.flag=u?VR_AP_USER:0;range.pgshift=0;range.start=0x1000;range.end=0x3000;
  unsigned long *ptep=(unsigned long *)0x1110;void *base=(void *)0x2220,*virt=NULL;
  size_t span=spans[n];int align=aligns[a],error=123;alloc_result=&storage[0];reset();
  CHECK(fixture_original_anon_allocate(NULL,&range,addresses[v],0x400,&ptep,&base,&span,&align,&virt,&error)==0);
  CHECK(virt==alloc_result && actual.value[6]==3058 && actual.value[0]==(unsigned long)(int)(spans[n]/PAGE_SIZE));save();
  CHECK(ptep==(unsigned long *)0x1110 && base==(void *)0x2220 && span==spans[n] && align==aligns[a] && error==123);
  virt=NULL;
  CHECK(process_page_fault_anon_allocate_body_result(NULL,&range,addresses[v],0x400,&ptep,&base,&span,&align,&virt,&error)==0);
  CHECK(virt==alloc_result && ptep==(unsigned long *)0x1110 && base==(void *)0x2220);
  CHECK(span==spans[n] && align==aligns[a] && error==123);compare(1,3058);++comparisons;
 }
 CHECK(comparisons==210);
 printf("PASS five current Rust consumers: 210 original-C argument comparisons, 13 genuine ABI rows; line/file/narrowing/null/flags exact\n");
 return 0;
}
