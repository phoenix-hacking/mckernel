/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <process_helpers.h>
#include <ihk/debug.h>
extern void vm_range_insert_log_bridge(int,struct process_vm *,struct vm_range *,struct vm_range *);
extern struct ddebug process_vm_range_insert_debug;
_Static_assert(sizeof(void *)==8 && sizeof(unsigned long)==8 && sizeof(int)==4 && (char)-1<0,"supported LP64 signed-char ABI");
_Static_assert(sizeof(struct ddebug)==32 && __alignof__(struct ddebug)==8,"actual Ddebug ABI proven by prior1101 fixture");
_Static_assert(__builtin_offsetof(struct ddebug,fmt)==2*sizeof(void *),"descriptor pointer fields");
_Static_assert(__builtin_types_compatible_p(__typeof__(&vm_range_insert_log_bridge),process_vm_range_insert_log_fn_t),"unchanged full callback signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),int (*)(const char *,...)),"existing exact variadic provider");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct vm_range *)0)->flag),unsigned long),"keep original UL flag varargs even for %x");
extern void vm_range_insert_dump_bridge(struct process_vm *);
extern const int process_dump_tree_enabled;
_Static_assert(__builtin_types_compatible_p(__typeof__(&vm_range_insert_dump_bridge),process_vm_range_insert_dump_fn_t),"exact existing dump callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(process_dump_tree_enabled),const int),"readonly original compile-time gate");
_Static_assert(sizeof(struct rb_node)==24 && __builtin_offsetof(struct rb_node,rb_left)==16 && __builtin_offsetof(struct rb_node,rb_right)==8,"real x86_64 rbnode ABI from accepted433 fixture");
