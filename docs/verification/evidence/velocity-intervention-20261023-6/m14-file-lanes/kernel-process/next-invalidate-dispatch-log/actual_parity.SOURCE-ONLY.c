/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE ONLY: original C bodies against actual Rust callbacks and typed Rust
 * memobj dispatcher. This exercises the callbacks; it does not claim execution
 * of the complete invalidate owner or any native PTE/TLB effect.
 */
#include <process.h>
#include <memobj.h>
#include <ihk/debug.h>
#include <string.h>
#undef memset
extern int printf(const char *,...);
extern void exit(int);
extern void fixture_layout(unsigned long *);
extern int process_memobj_invalidate_page_bridge(struct memobj *,uintptr_t,size_t);
extern void process_invalidate_one_page_log_bridge(void *,void *,void *,unsigned long,void *,int,int);
#define process_memobj_invalidate_page_bridge original_dispatch
#include "fixture/original_dispatch.ACTUAL-C.inc"
#undef process_memobj_invalidate_page_bridge
#define process_invalidate_one_page_log_bridge original_error_log
#include "fixture/original_error_log.ACTUAL-C.inc"
#undef process_invalidate_one_page_log_bridge

struct event { int kind,error;unsigned long phys,size; };
struct result { int error,count;unsigned flags;int ops_null;struct event events[2]; };
static struct result tape;
static struct memobj object;
static struct memobj_ops operations;
static unsigned long phys_value,size_value,pte_value;
static int provider_error,mutation,comparisons,log_return;
static void *arg_value,*pt_value,*ptep_value,*pgaddr_value;
static int shift_value,expected_log_error;
static void need(int ok,int line) {
 if (!ok) { printf("FAIL functional invalidate callbacks line=%d comparison=%d\n",line,comparisons);exit(1); }
}
#define CHECK(x) need(!!(x),__LINE__)
static int invalidate(struct memobj *obj,uintptr_t phys,size_t pgsize) {
 CHECK(obj==&object&&phys==phys_value&&pgsize==size_value);
 CHECK(tape.count==0);
 tape.events[tape.count++]=(struct event){1,provider_error,phys,pgsize};
 if (mutation) { object.ops=0;object.flags=0xdeadbeefU;object.size=~0UL;object.path=0; }
 return provider_error;
}
int kprintf(const char *format,...) {
 static const char expected[]="invalidate_one_page(%p,%p,%p %#lx,%p,%d):invalidate failed. %d\n";
 CHECK(!strcmp(format,expected));
 __builtin_va_list ap;__builtin_va_start(ap,format);
 CHECK(__builtin_va_arg(ap,void *)==arg_value);
 CHECK(__builtin_va_arg(ap,void *)==pt_value);
 CHECK(__builtin_va_arg(ap,void *)==ptep_value);
 CHECK(__builtin_va_arg(ap,unsigned long)==pte_value);
 CHECK(__builtin_va_arg(ap,void *)==pgaddr_value);
 CHECK(__builtin_va_arg(ap,int)==shift_value);
 CHECK(__builtin_va_arg(ap,int)==expected_log_error);
 __builtin_va_end(ap);
 CHECK(tape.count<2);
 tape.events[tape.count++]=(struct event){2,expected_log_error,pte_value,0};
 return log_return;
}
static struct result run(int rust,int present) {
 tape=(struct result){0};
 operations=(struct memobj_ops){.invalidate_page=present?invalidate:0};
 object=(struct memobj){.ops=&operations,.flags=0x89abcdefU,.size=4096};
 int error=rust?process_memobj_invalidate_page_bridge(&object,phys_value,size_value):
                original_dispatch(&object,phys_value,size_value);
 CHECK(error==(present?provider_error:0));
 /* This is the existing owner's error gate; full actual owner source is retained
  * separately. It is not an independent execution of its PTE/lock algorithm. */
 if (error) {
  expected_log_error=error;
  if(rust) process_invalidate_one_page_log_bridge(arg_value,pt_value,ptep_value,pte_value,pgaddr_value,shift_value,error);
  else original_error_log(arg_value,pt_value,ptep_value,pte_value,pgaddr_value,shift_value,error);
 }
 CHECK(tape.count==present+(error!=0));
 if (present) CHECK(tape.events[0].kind==1&&tape.events[0].error==provider_error);
 if (error) CHECK(tape.events[tape.count-1].kind==2&&tape.events[tape.count-1].error==error);
 tape.error=error;tape.flags=object.flags;tape.ops_null=(object.ops==0);
 CHECK(tape.flags==((present&&mutation)?0xdeadbeefU:0x89abcdefU));
 CHECK(tape.ops_null==(present&&mutation));
 return tape;
}
static void equal(struct result a,struct result b) {
 CHECK(a.error==b.error&&a.count==b.count&&a.flags==b.flags&&a.ops_null==b.ops_null);
 for(int n=0;n<a.count;n++)
  CHECK(a.events[n].kind==b.events[n].kind&&a.events[n].error==b.events[n].error&&
        a.events[n].phys==b.events[n].phys&&a.events[n].size==b.events[n].size);
 comparisons++;
}
int main(void) {
 unsigned long layout[5];fixture_layout(layout);
 CHECK(layout[0]==sizeof(struct memobj)&&layout[1]==__alignof__(struct memobj));
 CHECK(layout[2]==__builtin_offsetof(struct memobj,ops));
 CHECK(layout[3]==sizeof(struct memobj_ops)&&layout[4]==__builtin_offsetof(struct memobj_ops,invalidate_page));
 const unsigned long physical[]={0,0x12345000UL,0x8000000012345000UL,~0UL};
 const unsigned long sizes[]={0,4096,1UL<<30,~0UL};
 const int errors[]={0,-5,7,(-2147483647-1),2147483647};
 arg_value=(void *)0x12345000UL;pt_value=(void *)0x8123456789abcdefUL;
 ptep_value=(void *)0x99887000UL;pgaddr_value=(void *)0xfedcba9876543210UL;
 pte_value=0xfedcba9876543210UL;shift_value=-2147483647-1;log_return=-77;
 for(int present=0;present<2;present++)for(int e=0;e<5;e++)
  for(int p=0;p<4;p++)for(int s=0;s<4;s++)for(mutation=0;mutation<2;mutation++) {
   provider_error=errors[e];phys_value=physical[p];size_value=sizes[s];
   equal(run(0,present),run(1,present));
  }
 /* Error callback accepts arbitrary opaque/null pointers and full signed ints;
  * no pointee is read or retained and kprintf result never becomes a result. */
 for(int nil=0;nil<2;nil++)for(int e=0;e<5;e++)for(int ret=0;ret<2;ret++) {
  arg_value=nil?0:(void *)0x12345000UL;pt_value=nil?0:(void *)0x8123456789abcdefUL;
  ptep_value=nil?0:(void *)0x99887000UL;pgaddr_value=nil?0:(void *)0xfedcba9876543210UL;
  expected_log_error=errors[e];shift_value=errors[(e+1)%5];log_return=ret?2147483647:(-2147483647-1);
  tape=(struct result){0};
  original_error_log(arg_value,pt_value,ptep_value,pte_value,pgaddr_value,shift_value,expected_log_error);
  struct result a=tape;tape=(struct result){0};
  process_invalidate_one_page_log_bridge(arg_value,pt_value,ptep_value,pte_value,pgaddr_value,shift_value,expected_log_error);
  equal(a,tape);
 }
 CHECK(comparisons==340);
 printf("PASS functional invalidate dispatch/log actual-original-C/Rust comparisons=%d\n",comparisons);
 return 0;
}
