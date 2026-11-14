/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <arch-memory.h>
extern int printf(const char *,...);
extern void exit(int);
extern uintptr_t process_pte_get_phys_bridge(void *);
extern int process_pgsize_to_tbllv_bridge(size_t);
extern size_t process_tbllv_to_contpgsize_bridge(int);
#define pte_get_phys original_pte_get_phys
#include "fixture/pte_get_phys.ACTUAL-ARCH-C.inc"
#define process_pte_get_phys_bridge original_phys_callback
#include "fixture/process_pte_get_phys_bridge.ACTUAL-C.inc"
#undef process_pte_get_phys_bridge
#undef pte_get_phys
#define pgsize_to_tbllv original_pgsize_to_tbllv
#include "fixture/pgsize_to_tbllv.ACTUAL-ARCH-C.inc"
#define process_pgsize_to_tbllv_bridge original_level_callback
#include "fixture/process_pgsize_to_tbllv_bridge.ACTUAL-C.inc"
#undef process_pgsize_to_tbllv_bridge
#undef pgsize_to_tbllv
#define tbllv_to_contpgsize original_tbllv_to_contpgsize
#include "fixture/tbllv_to_contpgsize.ACTUAL-ARCH-C.inc"
#define process_tbllv_to_contpgsize_bridge original_contiguous_callback
#include "fixture/process_tbllv_to_contpgsize_bridge.ACTUAL-C.inc"
#undef process_tbllv_to_contpgsize_bridge
#undef tbllv_to_contpgsize
static int comparisons;
static void need(int ok,int line) {
 if(!ok){printf("FAIL functional invalidate phys/size line=%d count=%d\n",line,comparisons);exit(1);}
}
#define CHECK(x) need(!!(x),__LINE__)
int main(void) {
 const unsigned long words[]={0,1,0x800,0xfff,~0UL,0x800000001234d800UL,0x000fffffffffffffUL,0x12345043UL};
 for(int w=0;w<8;w++) {
  struct {unsigned long before;pte_t pte;unsigned long after;} s={0x123456789abcdef0UL,words[w],0xfedcba9876543210UL};
  unsigned long a=original_phys_callback(&s.pte),b=process_pte_get_phys_bridge(&s.pte);
  CHECK(a==b&&b==(words[w]&0x000ffffffffff000UL));
  CHECK(s.pte==words[w]&&s.before==0x123456789abcdef0UL&&s.after==0xfedcba9876543210UL);comparisons++;
 }
 const size_t sizes[]={0,1,4095,4096,1UL<<21,1UL<<30,1UL<<39,~0UL};
 const int levels[]={0,0,0,1,2,3,4,0};
 for(int s=0;s<8;s++) {
  int a=original_level_callback(sizes[s]),b=process_pgsize_to_tbllv_bridge(sizes[s]);
  CHECK(a==b&&b==levels[s]);comparisons++;
 }
 const int input_levels[]={(-2147483647-1),-5,-1,0,1,2,3,4,5,2147483647};
 for(int l=0;l<10;l++) {
  size_t a=original_contiguous_callback(input_levels[l]),b=process_tbllv_to_contpgsize_bridge(input_levels[l]);
  CHECK(a==b&&b==0);comparisons++;
 }
 CHECK(comparisons==26);
 printf("PASS functional invalidate phys/size actual-original-C/Rust comparisons=%d\n",comparisons);
 return 0;
}
