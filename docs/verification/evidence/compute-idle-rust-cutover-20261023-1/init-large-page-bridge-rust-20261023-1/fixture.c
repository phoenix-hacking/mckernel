/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <arch-memory.h>
extern int printf(const char *, ...);
extern void abort(void);
_Static_assert(sizeof(void *)==8 && sizeof(unsigned long)==8 && sizeof(int)==4,"native x86_64 scalar ABI");
_Static_assert(sizeof(enum ihk_mc_pt_attribute)==8 && _Alignof(enum ihk_mc_pt_attribute)==8,"actual enum width/alignment");
_Static_assert(__builtin_types_compatible_p(enum ihk_mc_pt_attribute,unsigned long),"actual enum unsigned long compatibility");
_Static_assert((unsigned long)(enum ihk_mc_pt_attribute)~0UL==~0UL,"enum cast preserves all bits");
_Static_assert((unsigned long)PTATTR_NO_EXECUTE==(1UL<<63),"actual header bit63");
struct capture {void *pt;unsigned long virt,phys,attr;int calls;};
static struct capture got;
static int reply;
#ifdef CHAIN_PROVIDER
int x86_pt_set_page_bridge(void *pt,unsigned long virt,unsigned long phys,unsigned long attr) {
#else
int set_pt_large_page(struct page_table *pt,void *virt,unsigned long phys,enum ihk_mc_pt_attribute attr) {
#endif
 got.pt=pt;got.virt=(unsigned long)virt;got.phys=phys;got.attr=(unsigned long)attr;got.calls++;return reply;
}
#ifdef CHAIN_PROVIDER
extern int set_pt_large_page(struct page_table *,void *,unsigned long,enum ihk_mc_pt_attribute);
#endif
#define X86_MEMORY_PUBLIC_BRIDGE
#define x86_init_normal_set_large_bridge original_bridge
#include "original_bridge.c.inc"
#undef x86_init_normal_set_large_bridge
extern int x86_init_normal_set_large_bridge(void *,unsigned long,unsigned long,unsigned long);
static unsigned long checked;
static void one(int rust,unsigned long pt,unsigned long virt,unsigned long phys,unsigned long attr,int result) {
 got=(struct capture){0};reply=result;
 int ret=rust?x86_init_normal_set_large_bridge((void*)pt,virt,phys,attr):original_bridge((void*)pt,virt,phys,attr);
 unsigned long expected=attr;
#ifdef CHAIN_PROVIDER
 expected|=PTATTR_LARGEPAGE|PTATTR_ACTIVE;
#endif
 if(ret!=result || got.calls!=1 || got.pt!=(void*)pt || got.virt!=virt || got.phys!=phys || got.attr!=expected)abort();
 checked++;
}
int main(void) {
 unsigned long words[]={0,1,0xffffffffUL,0x100000000UL,0x7fffffffffffffffUL,0x8000000000000000UL,~0UL};
 unsigned long attrs[]={0,PTATTR_ACTIVE,PTATTR_WRITABLE,PTATTR_USER,PTATTR_DIRTY,PTATTR_LARGEPAGE,PTATTR_FILEOFF,PTATTR_NO_EXECUTE,PTATTR_UNCACHABLE,PTATTR_FOR_USER,PTATTR_WRITE_COMBINED,0xffffffffUL,0x100000000UL,0x800000000000ffffUL,~0UL};
 int replies[]={0,1,-1,-14,(-2147483647-1),2147483647};
 for(unsigned int a=0;a<7;a++)for(unsigned int b=0;b<7;b++)for(unsigned int c=0;c<7;c++)for(unsigned int e=0;e<15;e++)for(unsigned int f=0;f<6;f++){
  one(0,words[a],words[b],words[c],attrs[e],replies[f]);one(1,words[a],words[b],words[c],attrs[e],replies[f]);
 }
 printf("PASS original C vs actual Rust: %lu call/return observations; enum64/align8; full pointer/attr64/int32 boundaries; chain=%d\n",checked,
#ifdef CHAIN_PROVIDER
 1
#else
 0
#endif
 );return 0;
}
