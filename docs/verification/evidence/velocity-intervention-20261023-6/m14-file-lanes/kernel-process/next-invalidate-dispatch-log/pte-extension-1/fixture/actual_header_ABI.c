/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <arch-memory.h>
extern void process_pte_make_fileoff_bridge(long,size_t,void *);
extern void process_pte_xchg_bridge(void *,void *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pte_make_fileoff_bridge),void (*)(off_t,size_t,void *)),"original signed LP64 offset callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pte_xchg_bridge),void (*)(void *,void *)),"original two-borrowed-pointer exchange ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pte_make_fileoff),void (*)(off_t,enum ihk_mc_pt_attribute,size_t,pte_t *)),"real architecture encoder signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pte_xchg),void (*)(pte_t *,pte_t *)),"real architecture atomic exchange signature");
_Static_assert(sizeof(off_t)==8&&sizeof(long)==8&&sizeof(pte_t)==8&&sizeof(size_t)==8,"supported LP64 signedness/widths");
_Static_assert(__alignof__(pte_t)==__alignof__(unsigned long),"existing atomic PTE alignment");
