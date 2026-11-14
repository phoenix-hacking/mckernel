/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <arch-memory.h>
extern int process_pte_is_null_bridge(void *);
extern int process_pte_is_fileoff_bridge(void *,size_t);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pte_is_null_bridge),int (*)(void *)),"original signed predicate callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pte_is_fileoff_bridge),int (*)(void *,size_t)),"original file-offset predicate callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pte_is_null),int (*)(pte_t *)),"actual C PTE predicate signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pte_is_fileoff),int (*)(pte_t *,size_t)),"actual C file-offset predicate signature");
_Static_assert(sizeof(pte_t)==8&&sizeof(size_t)==8&&sizeof(int)==4,"supported word and result widths");
