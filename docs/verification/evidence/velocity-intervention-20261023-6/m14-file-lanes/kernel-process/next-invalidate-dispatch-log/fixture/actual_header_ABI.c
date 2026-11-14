/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <memobj.h>
#include <ihk/debug.h>
extern int process_memobj_invalidate_page_bridge(struct memobj *,uintptr_t,size_t);
extern void process_invalidate_one_page_log_bridge(void *,void *,void *,unsigned long,void *,int,int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_memobj_invalidate_page_bridge),memobj_invalidate_page_func_t *),"exact typed dispatch callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_invalidate_one_page_log_bridge),void (*)(void *,void *,void *,unsigned long,void *,int,int)),"exact typed log callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct memobj_ops *)0)->invalidate_page),memobj_invalidate_page_func_t *),"actual memobj invalidate operation signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),int (*)(const char *,...)),"unchanged variadic logger ABI");
_Static_assert(sizeof(uintptr_t)==8&&sizeof(size_t)==8&&sizeof(unsigned long)==8&&sizeof(int)==4,"supported LP64 widths and signed CInt result");
