/* Functional McKernel OS/apps and Rust migration only; no security testing.
 * Nonshipped private/source-only contract metadata. No production providers.
 * Source-only declarations/data below are extracted from actual original C. */
#include <stddef.h>
#include <linux/version.h>
#include <linux/sched.h>
#include <ihk/ihklib_private.h>
#include "source_export_actual_contracts.inc"
#define PRIVATE_FUNCTION(function, type) \
    _Static_assert(__builtin_types_compatible_p(__typeof__(&function), type), #function " private/source declaration")
PRIVATE_FUNCTION(ihklib_device_open, int (*)(int));
PRIVATE_FUNCTION(ihklib_os_open, int (*)(int));
PRIVATE_FUNCTION(ihklib_os_query_mem_sysfs, int (*)(int, char *, ssize_t, const char *));
PRIVATE_FUNCTION(cpu_str2count, int (*)(char *));
PRIVATE_FUNCTION(cpu_str2req, int (*)(char *, int, struct ihk_cpu_req *));
PRIVATE_FUNCTION(cpu_req2str, char *(*)(struct ihk_cpu_req *));
PRIVATE_FUNCTION(mem_str2count, int (*)(char *));
PRIVATE_FUNCTION(mem_str2req, int (*)(char *, struct ihk_mem_req *));
PRIVATE_FUNCTION(mem_req2str, char *(*)(struct ihk_mem_req *));
PRIVATE_FUNCTION(ikc_str2count, int (*)(char *));
PRIVATE_FUNCTION(ikc_str2req, int (*)(char *, int, struct ihk_ikc_req *));
PRIVATE_FUNCTION(ikc_req2str, char *(*)(struct ihk_ikc_req *));
PRIVATE_FUNCTION(_ihk_reserve_cpu_str, int (*)(int, char *, char *));
PRIVATE_FUNCTION(_ihk_reserve_mem_str, int (*)(int, char *, char *));
PRIVATE_FUNCTION(_ihk_os_assign_cpu_str, int (*)(int, char *, char *));
PRIVATE_FUNCTION(_ihk_os_set_ikc_map_str, int (*)(int, char *, char *));
PRIVATE_FUNCTION(parse_env, int (*)(const char *, int, char ***, char ***));
PRIVATE_FUNCTION(dump_reserve_mem_conf, void (*)(void));
#undef PRIVATE_FUNCTION
#define PRIVATE_DATA(symbol, type) \
    _Static_assert(__builtin_types_compatible_p(__typeof__(symbol), type), #symbol " private/source data type")
PRIVATE_DATA(reserve_mem_conf, struct ihklib_reserve_mem_conf);
PRIVATE_DATA(ihklib_os_query_mem_type_str, const char *[2]);
PRIVATE_DATA(__argc, int);
PRIVATE_DATA(__argv, char **);
PRIVATE_DATA(namespace_files, struct namespace_file[8]);
#undef PRIVATE_DATA
_Static_assert(sizeof(reserve_mem_conf) == 24, "private policy data width");
_Static_assert(sizeof(ihklib_os_query_mem_type_str) == 16, "private query strings width");
_Static_assert(sizeof(__argc) == 4 && sizeof(__argv) == 8, "source process data widths");
_Static_assert(sizeof(namespace_files) == 192, "source namespace array width");
#define PRIVATE_FIELD(structure, field, type, offset) \
    _Static_assert(__builtin_types_compatible_p(__typeof__(((struct structure *)0)->field), type), #structure "." #field " type"); \
    _Static_assert(offsetof(struct structure, field) == offset, #structure "." #field " offset")
_Static_assert(sizeof(struct ihk_cpu_req) == 16 && _Alignof(struct ihk_cpu_req) == 8, "ihk_cpu_req size/alignment");
PRIVATE_FIELD(ihk_cpu_req, cpus, int *, 0);
PRIVATE_FIELD(ihk_cpu_req, num_cpus, int, 8);
_Static_assert(sizeof(struct ihk_mem_req) == 32 && _Alignof(struct ihk_mem_req) == 8, "ihk_mem_req size/alignment");
PRIVATE_FIELD(ihk_mem_req, sizes, size_t *, 0);
PRIVATE_FIELD(ihk_mem_req, numa_ids, int *, 8);
PRIVATE_FIELD(ihk_mem_req, num_chunks, int, 16);
PRIVATE_FIELD(ihk_mem_req, min_chunk_size, int, 20);
PRIVATE_FIELD(ihk_mem_req, max_size_ratio_all, int, 24);
PRIVATE_FIELD(ihk_mem_req, timeout, int, 28);
_Static_assert(sizeof(struct ihk_ikc_req) == 24 && _Alignof(struct ihk_ikc_req) == 8, "ihk_ikc_req size/alignment");
PRIVATE_FIELD(ihk_ikc_req, src_cpus, int *, 0);
PRIVATE_FIELD(ihk_ikc_req, dst_cpus, int *, 8);
PRIVATE_FIELD(ihk_ikc_req, num_cpus, int, 16);
_Static_assert(sizeof(struct ihklib_reserve_mem_conf) == 24 && _Alignof(struct ihklib_reserve_mem_conf) == 4, "ihklib_reserve_mem_conf size/alignment");
PRIVATE_FIELD(ihklib_reserve_mem_conf, balanced_enable, int, 0);
PRIVATE_FIELD(ihklib_reserve_mem_conf, balanced_best_effort, int, 4);
PRIVATE_FIELD(ihklib_reserve_mem_conf, balanced_variance_limit, int, 8);
PRIVATE_FIELD(ihklib_reserve_mem_conf, min_chunk_size, int, 12);
PRIVATE_FIELD(ihklib_reserve_mem_conf, max_size_ratio_all, int, 16);
PRIVATE_FIELD(ihklib_reserve_mem_conf, timeout, int, 20);
_Static_assert(sizeof(struct namespace_file) == 24 && _Alignof(struct namespace_file) == 8, "namespace_file size/alignment");
PRIVATE_FIELD(namespace_file, nstype, int, 0);
PRIVATE_FIELD(namespace_file, name, const char *, 8);
PRIVATE_FIELD(namespace_file, fd, int, 16);
#undef PRIVATE_FIELD
