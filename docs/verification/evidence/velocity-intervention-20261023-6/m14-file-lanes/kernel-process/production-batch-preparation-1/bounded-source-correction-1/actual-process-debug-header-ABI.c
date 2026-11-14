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
#include <memobj.h>
#include <rusage_private.h>
struct actual_rfp_args { off_t off; uintptr_t start; struct memobj *memobj; };
extern int sync_one_page(void *,page_table_t,pte_t *,void *,int);
extern int remap_one_page(void *,page_table_t,pte_t *,void *,int);
extern void process_sync_range_log_bridge(struct process_vm *,struct vm_range *,unsigned long,unsigned long,int);
typedef int (*actual_visit_t)(void *,page_table_t,pte_t *,void *,int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&sync_one_page),actual_visit_t)&&__builtin_types_compatible_p(__typeof__(&remap_one_page),actual_visit_t),"exact original five-argument visitor ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sync_range_log_bridge),void (*)(struct process_vm *,struct vm_range *,unsigned long,unsigned long,int)),"exact range logger ABI");
_Static_assert(sizeof(struct actual_rfp_args)==24&&__alignof__(struct actual_rfp_args)==8&&__builtin_offsetof(struct actual_rfp_args,off)==0&&__builtin_offsetof(struct actual_rfp_args,start)==8&&__builtin_offsetof(struct actual_rfp_args,memobj)==16,"existing actual ProcessRemapArgs ABI");
_Static_assert(sizeof(struct page)==80&&__alignof__(struct page)==8,"actual existing Page provider ABI; remap accesses no Page fields");
_Static_assert(__builtin_types_compatible_p(__typeof__(&phys_to_page),struct page *(*)(uintptr_t)),"explicit existing C forwarding provider ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_free_pages),void (*)(void *,int,int,char *,int)),"exact tracked free signature/static file lifetime");
_Static_assert(__builtin_types_compatible_p(__typeof__(&rusage_memory_stat_sub),void (*)(struct memobj *,unsigned long,int)),"original RSS size_t to int conversion boundary");
_Static_assert(IHK_MC_PG_USER==1,"original user-page accounting mode");
extern const char *const process_remap_free_file;
extern const int process_remap_free_line;
_Static_assert(__builtin_types_compatible_p(__typeof__(process_remap_free_file),const char *const)&&__builtin_types_compatible_p(__typeof__(process_remap_free_line),const int),"static original tracked-free identity ABI");
