/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <arch-memory.h>
extern uintptr_t process_pte_get_phys_bridge(void *);
extern int process_pgsize_to_tbllv_bridge(size_t);
extern size_t process_tbllv_to_contpgsize_bridge(int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pte_get_phys_bridge),uintptr_t (*)(void *)),"original unsigned physical-address callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pgsize_to_tbllv_bridge),int (*)(size_t)),"original page-size to signed level callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_tbllv_to_contpgsize_bridge),size_t (*)(int)),"original signed level to contiguous-size callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pte_get_phys),uintptr_t (*)(pte_t *)),"real architecture physical extractor signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pgsize_to_tbllv),int (*)(size_t)),"real architecture size converter signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&tbllv_to_contpgsize),size_t (*)(int)),"real architecture contiguous-size converter signature");
_Static_assert(sizeof(uintptr_t)==8&&sizeof(pte_t)==8&&sizeof(size_t)==8&&sizeof(int)==4,"supported LP64 unsigned/signed widths");
