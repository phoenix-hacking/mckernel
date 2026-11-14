/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <memobj.h>
#include <ihk/debug.h>
extern int sync_one_page(void *,page_table_t,pte_t *,void *,int);
typedef int (*actual_visit_step_t)(void *,page_table_t,pte_t *,void *,int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&sync_one_page),actual_visit_step_t),"exact original callback signature");
_Static_assert(sizeof(pte_t)==8 && sizeof(size_t)==8 && sizeof(uintptr_t)==8 && sizeof(int)==4,"supported x86_64 full signedness/width ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct memobj *)0)->flags),uint32_t),"memobj flags unsigned32");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct memobj_ops *)0)->flush_page),memobj_flush_page_func_t *),"actual memobj operation ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),int (*)(const char *,...)),"exact existing variadic logger ABI");
_Static_assert(sizeof(struct ddebug)==32 && __builtin_offsetof(struct ddebug,fmt)==16,"actual ddebug lifetime/layout ABI");
