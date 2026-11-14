/* Functional McKernel OS/apps and Rust migration only; no security testing.
 * Nonshipped remaining public-export signature/scalar/data witness. */
#include <stddef.h>
#include <limits.h>
#include <ihk/ihklib.h>
_Static_assert(CHAR_BIT == 8 && CHAR_MIN == -128, "selected signed C char");
_Static_assert(sizeof(int) == 4 && sizeof(long) == 8 && sizeof(void *) == 8, "selected LP64 scalars");
_Static_assert(sizeof(size_t) == 8 && sizeof(ssize_t) == 8, "selected public lengths");
_Static_assert(__builtin_types_compatible_p(ssize_t, long), "Rust isize signedness");
_Static_assert(__builtin_types_compatible_p(size_t, unsigned long), "Rust usize unsignedness");
_Static_assert(sizeof(enum IHKLIB_LOGLEVEL) == 4 && _Alignof(enum IHKLIB_LOGLEVEL) == 4, "selected logging enum representation");
_Static_assert(__builtin_types_compatible_p(enum IHKLIB_LOGLEVEL, unsigned int), "selected logging enum compatible C type");
_Static_assert(IHKLIB_LOGLEVEL_EMERG == 0 && IHKLIB_LOGLEVEL_ERR == 1, "logging enumerators");
_Static_assert(sizeof(ihk_perf_event_attr) == 16 && _Alignof(ihk_perf_event_attr) == 8, "opaque perf attribute layout");
_Static_assert(offsetof(ihk_perf_event_attr, config) == 0 && __builtin_types_compatible_p(__typeof__(((ihk_perf_event_attr *)0)->config), unsigned long), "opaque perf config member");
_Static_assert(__builtin_types_compatible_p(__typeof__(&loglevel), int *) && sizeof(loglevel) == 4, "public writable logging data type");
#define PUBLIC_FUNCTION(function, type) \
    _Static_assert(__builtin_types_compatible_p(__typeof__(&function), type), #function " public declaration")
PUBLIC_FUNCTION(ihk_reserve_cpu, int (*)(int, int*, int));
PUBLIC_FUNCTION(ihk_reserve_cpu_str, int (*)(int, const char *, int));
PUBLIC_FUNCTION(ihk_get_num_reserved_cpus, int (*)(int));
PUBLIC_FUNCTION(ihk_query_cpu, int (*)(int, int*, int));
PUBLIC_FUNCTION(ihk_release_cpu, int (*)(int, int*, int));
PUBLIC_FUNCTION(ihk_reserve_mem_conf, int (*)(int, int, void *));
PUBLIC_FUNCTION(ihk_reserve_mem_conf_str, int (*)(int, const char *, int));
PUBLIC_FUNCTION(ihk_reserve_mem_str, int (*)(int, const char *, int));
PUBLIC_FUNCTION(ihk_get_num_reserved_mem_chunks, int (*)(int));
PUBLIC_FUNCTION(ihk_create_os, int (*)(int));
PUBLIC_FUNCTION(ihk_get_num_os_instances, int (*)(int));
PUBLIC_FUNCTION(ihk_get_os_instances, int (*)(int, int *, int));
PUBLIC_FUNCTION(ihk_destroy_os, int (*)(int, int));
PUBLIC_FUNCTION(ihk_os_assign_cpu, int (*)(int, int*, int));
PUBLIC_FUNCTION(ihk_os_assign_cpu_str, int (*)(int, const char *, int));
PUBLIC_FUNCTION(ihk_os_get_num_assigned_cpus, int (*)(int));
PUBLIC_FUNCTION(ihk_os_query_cpu, int (*)(int, int*, int));
PUBLIC_FUNCTION(ihk_os_release_cpu, int (*)(int, int*, int));
PUBLIC_FUNCTION(ihk_os_set_ikc_map_str, int (*)(int, const char *, int));
PUBLIC_FUNCTION(ihk_os_get_num_assigned_mem_chunks, int (*)(int));
PUBLIC_FUNCTION(ihk_os_get_eventfd, int (*)(int, int));
PUBLIC_FUNCTION(ihk_os_load, int (*)(int, char*));
PUBLIC_FUNCTION(ihk_os_kargs, int (*)(int, char*));
PUBLIC_FUNCTION(ihk_os_kargs_str, int (*)(int, const char *, int, const char *));
PUBLIC_FUNCTION(ihk_create_os_str, int (*)(int, int *, const char *, int, const char *, const char *, char *));
PUBLIC_FUNCTION(ihk_os_boot, int (*)(int));
PUBLIC_FUNCTION(ihk_os_shutdown, int (*)(int));
PUBLIC_FUNCTION(ihk_os_get_status, int (*)(int));
PUBLIC_FUNCTION(ihk_os_get_kmsg_size, int (*)(int));
PUBLIC_FUNCTION(ihk_os_kmsg, int (*)(int, char*, ssize_t));
PUBLIC_FUNCTION(ihk_os_clear_kmsg, int (*)(int));
PUBLIC_FUNCTION(ihk_os_get_num_numa_nodes, int (*)(int));
PUBLIC_FUNCTION(ihk_os_query_free_mem, int (*)(int, unsigned long *, int));
PUBLIC_FUNCTION(ihk_os_query_total_mem, int (*)(int, unsigned long *, int));
PUBLIC_FUNCTION(ihk_os_get_num_pagesizes, int (*)(int));
PUBLIC_FUNCTION(ihk_os_get_pagesizes, int (*)(int, long *, int));
PUBLIC_FUNCTION(ihk_os_setperfevent, int (*)(int, ihk_perf_event_attr *, int));
PUBLIC_FUNCTION(ihk_os_perfctl, int (*)(int, int));
PUBLIC_FUNCTION(ihk_os_getperfevent, int (*)(int, unsigned long *, int));
PUBLIC_FUNCTION(ihk_os_freeze, int (*)(unsigned long *, int));
PUBLIC_FUNCTION(ihk_os_thaw, int (*)(unsigned long *, int));
PUBLIC_FUNCTION(ihk_os_makedumpfile, int (*)(int, char *, int, int));
PUBLIC_FUNCTION(ihk_set_loglevel, int (*)(enum IHKLIB_LOGLEVEL));
#undef PUBLIC_FUNCTION
