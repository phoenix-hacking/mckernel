/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <kmalloc.h>

_Static_assert(__builtin_types_compatible_p(__typeof__(&kmalloc_tracked),
               void *(*)(int, unsigned long, char *, int)), "actual tracked allocator ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kfree_tracked),
               void (*)(void *, char *, int)), "actual tracked free ABI");
_Static_assert(sizeof(int)==4 && sizeof(unsigned long)==8 && sizeof(char *)==8,
               "actual CInt, CULong and metadata pointer widths");
_Static_assert(IHK_MC_AP_NOWAIT==2, "existing NOWAIT constant");

#include "exact_metadata.ACTUAL-C.inc"
_Static_assert(__builtin_types_compatible_p(__typeof__(process_tracked_allocator_source_file),
               const char *const), "exact readonly source pointer type");
_Static_assert(sizeof(process_alloc_bridge_source_line)==4 &&
               sizeof(process_add_range_alloc_bridge_source_line)==4 &&
               sizeof(process_mckfd_free_bridge_source_line)==4 &&
               sizeof(process_policy_free_bridge_source_line)==4 &&
               sizeof(process_optional_free_bridge_source_line)==4 &&
               sizeof(process_free_vm_bridge_source_line)==4 &&
               sizeof(process_range_kfree_bridge_source_line)==4 &&
               sizeof(process_add_range_free_bridge_source_line)==4,
               "all eight source-line metadata values use actual int width");
