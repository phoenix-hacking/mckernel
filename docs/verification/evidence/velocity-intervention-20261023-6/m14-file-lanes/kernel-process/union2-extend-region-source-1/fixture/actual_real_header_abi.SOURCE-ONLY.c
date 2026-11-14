/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact real-header source ABI assertions; no hosted width-only stand-ins. */
#include <process.h>
#include <ihk/debug.h>
_Static_assert(__builtin_types_compatible_p(__typeof__(&extend_process_region),
 unsigned long (*)(struct process_vm *,unsigned long,unsigned long,unsigned long)),
 "actual public complete entry signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&lookup_process_memory_range),
 struct vm_range *(*)(struct process_vm *,uintptr_t,uintptr_t)),
 "actual lookup uses uintptr_t, nominally distinct from unsigned long here");
_Static_assert(__builtin_types_compatible_p(__typeof__(&add_process_memory_range),
 int (*)(struct process_vm *,unsigned long,unsigned long,unsigned long,unsigned long,
 struct memobj *,off_t,int,void *,struct vm_range **)),
 "actual range admission and ownership provider signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_alloc_aligned_pages_node),
 void *(*)(int,int,ihk_mc_ap_flag,int,int,uintptr_t,char *,int)),
 "actual tracked allocator nominal typedefs");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_free_pages),
 void (*)(void *,int,int,char *,int)),"actual tracked free signature");
_Static_assert(sizeof(uintptr_t)==8&&sizeof(unsigned long)==8&&sizeof(size_t)==8&&sizeof(int)==4,
 "supported target provider call ABI; nominal types remain exact above");
_Static_assert(sizeof(struct ddebug)==32&&__alignof__(struct ddebug)==8,
 "actual dynamic descriptor carrier");
