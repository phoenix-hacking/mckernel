/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE ONLY. Read-only original callback/provider parity on hosted PTE words.
 */
#include <process.h>
#include <arch-memory.h>
extern int printf(const char *,...);
extern void exit(int);
extern int process_pte_is_null_bridge(void *);
extern int process_pte_is_fileoff_bridge(void *,size_t);
#define pte_is_null original_pte_is_null
#include "fixture/pte_is_null.ACTUAL-ARCH-C.inc"
#define process_pte_is_null_bridge original_null_callback
#include "fixture/process_pte_is_null_bridge.ACTUAL-C.inc"
#undef process_pte_is_null_bridge
#undef pte_is_null
#define pte_is_fileoff original_pte_is_fileoff
#include "fixture/pte_is_fileoff.ACTUAL-ARCH-C.inc"
#define process_pte_is_fileoff_bridge original_fileoff_callback
#include "fixture/process_pte_is_fileoff_bridge.ACTUAL-C.inc"
#undef process_pte_is_fileoff_bridge
#undef pte_is_fileoff
static int comparisons;
static void need(int ok,int line) {
 if(!ok){printf("FAIL functional invalidate predicates line=%d count=%d\n",line,comparisons);exit(1);}
}
#define CHECK(x) need(!!(x),__LINE__)
int main(void) {
 const unsigned long words[]={0,1,0x800,0x80,0x880,~0UL,0x800000001234d800UL,0x40};
 const size_t sizes[]={0,4096,1UL<<21,1UL<<30,1UL<<39,12345};
 for(int w=0;w<8;w++) {
  struct {unsigned long before;pte_t pte;unsigned long after;} s={0x123456789abcdef0UL,words[w],0xfedcba9876543210UL};
  int a=original_null_callback(&s.pte),b=process_pte_is_null_bridge(&s.pte);
  CHECK(a==b&&b==(words[w]==0));comparisons++;
  for(int z=0;z<6;z++) {
   a=original_fileoff_callback(&s.pte,sizes[z]);b=process_pte_is_fileoff_bridge(&s.pte,sizes[z]);
   CHECK(a==b&&b==((words[w]&0x800UL)!=0));comparisons++;
   CHECK(s.pte==words[w]&&s.before==0x123456789abcdef0UL&&s.after==0xfedcba9876543210UL);
  }
 }
 CHECK(comparisons==56);
 printf("PASS functional invalidate predicates actual-original-C/Rust comparisons=%d\n",comparisons);
 return 0;
}
