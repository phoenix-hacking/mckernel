/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE ONLY. Actual original C callbacks/providers vs actual Rust callbacks/
 * providers on aligned hosted PTE words. No TLB or kernel instruction is invoked.
 * The original atomic provider's ordinary xchg operates only on these local words.
 */
#include <process.h>
#include <arch-memory.h>
#include <ihk/atomic.h>
extern int printf(const char *,...);
extern void exit(int);
extern void process_pte_make_fileoff_bridge(long,size_t,void *);
extern void process_pte_xchg_bridge(void *,void *);
#define pte_make_fileoff fixture_original_encoder
#include "fixture/pte_make_fileoff.ACTUAL-ARCH-C.inc"
#define process_pte_make_fileoff_bridge original_make_fileoff_callback
#include "fixture/process_pte_make_fileoff_bridge.ACTUAL-C.inc"
#undef process_pte_make_fileoff_bridge
#undef pte_make_fileoff
#define pte_xchg fixture_original_exchange
#include "fixture/pte_xchg.ACTUAL-ARCH-C.inc"
#define process_pte_xchg_bridge original_exchange_callback
#include "fixture/process_pte_xchg_bridge.ACTUAL-C.inc"
#undef process_pte_xchg_bridge
#undef pte_xchg

static int comparisons;
static void need(int ok,int line) {
 if (!ok) { printf("FAIL functional invalidate PTE callbacks line=%d comparisons=%d\n",line,comparisons);exit(1); }
}
#define CHECK(x) need(!!(x),__LINE__)
struct slot { unsigned long before;pte_t value;unsigned long after; };
static struct slot slot(unsigned long value) {
 return (struct slot){0x123456789abcdef0UL,value,0xfedcba9876543210UL};
}
static void guards(struct slot s) {
 CHECK(s.before==0x123456789abcdef0UL&&s.after==0xfedcba9876543210UL);
}
static unsigned long encoded(long off,size_t pgsize) {
 /* Independent bit oracle for ptattr0, including unrecognised-size fallback. */
 return ((unsigned long)off&~4095UL)|0x800UL|
        ((pgsize==(1UL<<21)||pgsize==(1UL<<30))?0x80UL:0);
}
int main(void) {
 _Static_assert(sizeof(pte_t)==8&&__alignof__(pte_t)==8,"real aligned x86_64 PTE");
 _Static_assert(PAGE_SIZE==4096&&PAGE_MASK==~4095UL,"actual supported base page geometry");
 const long offsets[]={0,1,-1,-4096,0x7fffffffffffffffL,(-0x7fffffffffffffffL-1)};
 const size_t sizes[]={0,4096,1UL<<21,1UL<<30,1UL<<39,12345};
 const unsigned long old[]={0,1,~0UL,0x8000000012345000UL,0x000fffffffffffffUL,0x12345043UL};
 for(int o=0;o<6;o++)for(int s=0;s<6;s++) {
  struct slot a=slot(~0UL),b=slot(~0UL);
  original_make_fileoff_callback(offsets[o],sizes[s],&a.value);
  process_pte_make_fileoff_bridge(offsets[o],sizes[s],&b.value);
  CHECK(a.value==b.value&&b.value==encoded(offsets[o],sizes[s]));guards(a);guards(b);comparisons++;
  for(int v=0;v<6;v++) {
   /* The actual owner encodes stack-local apte before exchanging the live word.
    * Observe both the publication and captured old PTE before any next effect. */
   a=slot(old[v]);b=slot(old[v]);struct slot av=slot(~0UL),bv=slot(~0UL);
   original_make_fileoff_callback(offsets[o],sizes[s],&av.value);
   process_pte_make_fileoff_bridge(offsets[o],sizes[s],&bv.value);
   original_exchange_callback(&a.value,&av.value);
   process_pte_xchg_bridge(&b.value,&bv.value);
   CHECK(a.value==b.value&&a.value==encoded(offsets[o],sizes[s]));
   CHECK(av.value==bv.value&&bv.value==old[v]);guards(a);guards(b);guards(av);guards(bv);comparisons++;
  }
 }
 for(int aidx=0;aidx<6;aidx++)for(int bidx=0;bidx<6;bidx++) {
  struct slot a=slot(old[aidx]),b=slot(old[aidx]),av=slot(old[bidx]),bv=slot(old[bidx]);
  original_exchange_callback(&a.value,&av.value);
  process_pte_xchg_bridge(&b.value,&bv.value);
  CHECK(a.value==b.value&&b.value==old[bidx]&&av.value==bv.value&&bv.value==old[aidx]);
  guards(a);guards(b);guards(av);guards(bv);comparisons++;
 }
 for(int v=0;v<6;v++) {
  struct slot a=slot(old[v]),b=slot(old[v]);
  original_exchange_callback(&a.value,&a.value);
  process_pte_xchg_bridge(&b.value,&b.value);
  CHECK(a.value==b.value&&b.value==old[v]);guards(a);guards(b);comparisons++;
 }
 CHECK(comparisons==294);
 printf("PASS functional invalidate PTE callbacks actual-original-C/Rust comparisons=%d\n",comparisons);
 return 0;
}
