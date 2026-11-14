/* Functional McKernel OS/apps and Rust migration only; no security testing.
 * Nonshipped public-header witness for the actual whole70 rusage export/layout.
 * No private header, runtime provider, device access or library API runs here. */
#include <stddef.h>
#include <ihk/ihklib.h>

_Static_assert(sizeof(unsigned long) == 8 && sizeof(int) == 4, "rusage LP64 scalars");
_Static_assert(IHK_MAX_NUM_PGSIZES == 8 && IHK_MAX_NUM_NUMA_NODES == 1024 &&
               IHK_MAX_NUM_CPUS == 1024, "rusage public array extents");
_Static_assert(sizeof(struct ihk_os_rusage) == 16568, "rusage public size");
_Static_assert(_Alignof(struct ihk_os_rusage) == 8, "rusage public alignment");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_os_getrusage),
    int (*)(int, struct ihk_os_rusage *, size_t)), "rusage public function type");
#define RUSAGE_FIELD(field, type, offset) \
    _Static_assert(__builtin_types_compatible_p( \
        __typeof__(((struct ihk_os_rusage *)0)->field), type), #field " type"); \
    _Static_assert(offsetof(struct ihk_os_rusage, field) == offset, #field " offset")
RUSAGE_FIELD(memory_stat_rss, unsigned long[8], 0);
RUSAGE_FIELD(memory_stat_mapped_file, unsigned long[8], 64);
RUSAGE_FIELD(memory_max_usage, unsigned long, 128);
RUSAGE_FIELD(memory_kmem_usage, unsigned long, 136);
RUSAGE_FIELD(memory_kmem_max_usage, unsigned long, 144);
RUSAGE_FIELD(memory_numa_stat, unsigned long[1024], 152);
RUSAGE_FIELD(cpuacct_stat_system, unsigned long, 8344);
RUSAGE_FIELD(cpuacct_stat_user, unsigned long, 8352);
RUSAGE_FIELD(cpuacct_usage, unsigned long, 8360);
RUSAGE_FIELD(cpuacct_usage_percpu, unsigned long[1024], 8368);
RUSAGE_FIELD(num_threads, int, 16560);
RUSAGE_FIELD(max_num_threads, int, 16564);
#undef RUSAGE_FIELD
