/* Functional McKernel OS/apps and Rust migration only; no security testing.
 * Nonshipped public descriptor/function witness; no API or device call. */
#include <stddef.h>
#include <ihk/ihklib.h>
_Static_assert(sizeof(unsigned long) == 8 && sizeof(int) == 4, "descriptor LP64 scalars");
_Static_assert(sizeof(struct ihk_mem_chunk) == 16, "memory descriptor size");
_Static_assert(_Alignof(struct ihk_mem_chunk) == 8, "memory descriptor alignment");
_Static_assert(sizeof(struct ihk_ikc_cpu_map) == 8, "IKC descriptor size");
_Static_assert(_Alignof(struct ihk_ikc_cpu_map) == 4, "IKC descriptor alignment");
#define DESCRIPTOR_FIELD(structure, field, type, offset) \
    _Static_assert(__builtin_types_compatible_p( \
        __typeof__(((struct structure *)0)->field), type), #structure "." #field " type"); \
    _Static_assert(offsetof(struct structure, field) == offset, #structure "." #field " offset")
DESCRIPTOR_FIELD(ihk_mem_chunk, size, unsigned long, 0);
DESCRIPTOR_FIELD(ihk_mem_chunk, numa_node_number, int, 8);
DESCRIPTOR_FIELD(ihk_ikc_cpu_map, src_cpu, int, 0);
DESCRIPTOR_FIELD(ihk_ikc_cpu_map, dst_cpu, int, 4);
#undef DESCRIPTOR_FIELD
#define DESCRIPTOR_FUNCTION(function, structure) \
    _Static_assert(__builtin_types_compatible_p(__typeof__(&function), \
        int (*)(int, struct structure *, int)), #function " public signature")
DESCRIPTOR_FUNCTION(ihk_reserve_mem, ihk_mem_chunk);
DESCRIPTOR_FUNCTION(ihk_query_mem, ihk_mem_chunk);
DESCRIPTOR_FUNCTION(ihk_release_mem, ihk_mem_chunk);
DESCRIPTOR_FUNCTION(ihk_os_assign_mem, ihk_mem_chunk);
DESCRIPTOR_FUNCTION(ihk_os_query_mem, ihk_mem_chunk);
DESCRIPTOR_FUNCTION(ihk_os_release_mem, ihk_mem_chunk);
DESCRIPTOR_FUNCTION(ihk_os_set_ikc_map, ihk_ikc_cpu_map);
DESCRIPTOR_FUNCTION(ihk_os_get_ikc_map, ihk_ikc_cpu_map);
#undef DESCRIPTOR_FUNCTION
