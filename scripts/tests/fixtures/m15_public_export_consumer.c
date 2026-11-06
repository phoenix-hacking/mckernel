/* Nonshipped remaining-public ABI consumer; genuine Root strict Rust library.
 * All selected error calls return before access/open/ioctl by actual source order.
 * The only successful API called is the pure loglevel setter; no device action. */
#define _GNU_SOURCE
#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <ihk/ihklib.h>
#include "linux/user/rust/whole70/abi/public_export_signatures_witness.c"

static void check_result(int actual, int expected)
{
    assert(actual == expected);
    assert(errno == EDOM);
}

int main(void)
{
    int (*volatile ref_ihk_reserve_cpu)(int, int*, int) = ihk_reserve_cpu;
    assert(ref_ihk_reserve_cpu != NULL);
    int (*volatile ref_ihk_reserve_cpu_str)(int, const char *, int) = ihk_reserve_cpu_str;
    assert(ref_ihk_reserve_cpu_str != NULL);
    int (*volatile ref_ihk_get_num_reserved_cpus)(int) = ihk_get_num_reserved_cpus;
    assert(ref_ihk_get_num_reserved_cpus != NULL);
    int (*volatile ref_ihk_query_cpu)(int, int*, int) = ihk_query_cpu;
    assert(ref_ihk_query_cpu != NULL);
    int (*volatile ref_ihk_release_cpu)(int, int*, int) = ihk_release_cpu;
    assert(ref_ihk_release_cpu != NULL);
    int (*volatile ref_ihk_reserve_mem_conf)(int, int, void *) = ihk_reserve_mem_conf;
    assert(ref_ihk_reserve_mem_conf != NULL);
    int (*volatile ref_ihk_reserve_mem_conf_str)(int, const char *, int) = ihk_reserve_mem_conf_str;
    assert(ref_ihk_reserve_mem_conf_str != NULL);
    int (*volatile ref_ihk_reserve_mem_str)(int, const char *, int) = ihk_reserve_mem_str;
    assert(ref_ihk_reserve_mem_str != NULL);
    int (*volatile ref_ihk_get_num_reserved_mem_chunks)(int) = ihk_get_num_reserved_mem_chunks;
    assert(ref_ihk_get_num_reserved_mem_chunks != NULL);
    int (*volatile ref_ihk_create_os)(int) = ihk_create_os;
    assert(ref_ihk_create_os != NULL);
    int (*volatile ref_ihk_get_num_os_instances)(int) = ihk_get_num_os_instances;
    assert(ref_ihk_get_num_os_instances != NULL);
    int (*volatile ref_ihk_get_os_instances)(int, int *, int) = ihk_get_os_instances;
    assert(ref_ihk_get_os_instances != NULL);
    int (*volatile ref_ihk_destroy_os)(int, int) = ihk_destroy_os;
    assert(ref_ihk_destroy_os != NULL);
    int (*volatile ref_ihk_os_assign_cpu)(int, int*, int) = ihk_os_assign_cpu;
    assert(ref_ihk_os_assign_cpu != NULL);
    int (*volatile ref_ihk_os_assign_cpu_str)(int, const char *, int) = ihk_os_assign_cpu_str;
    assert(ref_ihk_os_assign_cpu_str != NULL);
    int (*volatile ref_ihk_os_get_num_assigned_cpus)(int) = ihk_os_get_num_assigned_cpus;
    assert(ref_ihk_os_get_num_assigned_cpus != NULL);
    int (*volatile ref_ihk_os_query_cpu)(int, int*, int) = ihk_os_query_cpu;
    assert(ref_ihk_os_query_cpu != NULL);
    int (*volatile ref_ihk_os_release_cpu)(int, int*, int) = ihk_os_release_cpu;
    assert(ref_ihk_os_release_cpu != NULL);
    int (*volatile ref_ihk_os_set_ikc_map_str)(int, const char *, int) = ihk_os_set_ikc_map_str;
    assert(ref_ihk_os_set_ikc_map_str != NULL);
    int (*volatile ref_ihk_os_get_num_assigned_mem_chunks)(int) = ihk_os_get_num_assigned_mem_chunks;
    assert(ref_ihk_os_get_num_assigned_mem_chunks != NULL);
    int (*volatile ref_ihk_os_get_eventfd)(int, int) = ihk_os_get_eventfd;
    assert(ref_ihk_os_get_eventfd != NULL);
    int (*volatile ref_ihk_os_load)(int, char*) = ihk_os_load;
    assert(ref_ihk_os_load != NULL);
    int (*volatile ref_ihk_os_kargs)(int, char*) = ihk_os_kargs;
    assert(ref_ihk_os_kargs != NULL);
    int (*volatile ref_ihk_os_kargs_str)(int, const char *, int, const char *) = ihk_os_kargs_str;
    assert(ref_ihk_os_kargs_str != NULL);
    int (*volatile ref_ihk_create_os_str)(int, int *, const char *, int, const char *, const char *, char *) = ihk_create_os_str;
    assert(ref_ihk_create_os_str != NULL);
    int (*volatile ref_ihk_os_boot)(int) = ihk_os_boot;
    assert(ref_ihk_os_boot != NULL);
    int (*volatile ref_ihk_os_shutdown)(int) = ihk_os_shutdown;
    assert(ref_ihk_os_shutdown != NULL);
    int (*volatile ref_ihk_os_get_status)(int) = ihk_os_get_status;
    assert(ref_ihk_os_get_status != NULL);
    int (*volatile ref_ihk_os_get_kmsg_size)(int) = ihk_os_get_kmsg_size;
    assert(ref_ihk_os_get_kmsg_size != NULL);
    int (*volatile ref_ihk_os_kmsg)(int, char*, ssize_t) = ihk_os_kmsg;
    assert(ref_ihk_os_kmsg != NULL);
    int (*volatile ref_ihk_os_clear_kmsg)(int) = ihk_os_clear_kmsg;
    assert(ref_ihk_os_clear_kmsg != NULL);
    int (*volatile ref_ihk_os_get_num_numa_nodes)(int) = ihk_os_get_num_numa_nodes;
    assert(ref_ihk_os_get_num_numa_nodes != NULL);
    int (*volatile ref_ihk_os_query_free_mem)(int, unsigned long *, int) = ihk_os_query_free_mem;
    assert(ref_ihk_os_query_free_mem != NULL);
    int (*volatile ref_ihk_os_query_total_mem)(int, unsigned long *, int) = ihk_os_query_total_mem;
    assert(ref_ihk_os_query_total_mem != NULL);
    int (*volatile ref_ihk_os_get_num_pagesizes)(int) = ihk_os_get_num_pagesizes;
    assert(ref_ihk_os_get_num_pagesizes != NULL);
    int (*volatile ref_ihk_os_get_pagesizes)(int, long *, int) = ihk_os_get_pagesizes;
    assert(ref_ihk_os_get_pagesizes != NULL);
    int (*volatile ref_ihk_os_setperfevent)(int, ihk_perf_event_attr *, int) = ihk_os_setperfevent;
    assert(ref_ihk_os_setperfevent != NULL);
    int (*volatile ref_ihk_os_perfctl)(int, int) = ihk_os_perfctl;
    assert(ref_ihk_os_perfctl != NULL);
    int (*volatile ref_ihk_os_getperfevent)(int, unsigned long *, int) = ihk_os_getperfevent;
    assert(ref_ihk_os_getperfevent != NULL);
    int (*volatile ref_ihk_os_freeze)(unsigned long *, int) = ihk_os_freeze;
    assert(ref_ihk_os_freeze != NULL);
    int (*volatile ref_ihk_os_thaw)(unsigned long *, int) = ihk_os_thaw;
    assert(ref_ihk_os_thaw != NULL);
    int (*volatile ref_ihk_os_makedumpfile)(int, char *, int, int) = ihk_os_makedumpfile;
    assert(ref_ihk_os_makedumpfile != NULL);
    int (*volatile ref_ihk_set_loglevel)(enum IHKLIB_LOGLEVEL) = ihk_set_loglevel;
    assert(ref_ihk_set_loglevel != NULL);
    int *volatile public_state = &loglevel;
    assert(public_state != NULL);
    const char *names[] = {
        "ihk_reserve_cpu",
        "ihk_reserve_cpu_str",
        "ihk_get_num_reserved_cpus",
        "ihk_query_cpu",
        "ihk_release_cpu",
        "ihk_reserve_mem_conf",
        "ihk_reserve_mem_conf_str",
        "ihk_reserve_mem_str",
        "ihk_get_num_reserved_mem_chunks",
        "ihk_create_os",
        "ihk_get_num_os_instances",
        "ihk_get_os_instances",
        "ihk_destroy_os",
        "ihk_os_assign_cpu",
        "ihk_os_assign_cpu_str",
        "ihk_os_get_num_assigned_cpus",
        "ihk_os_query_cpu",
        "ihk_os_release_cpu",
        "ihk_os_set_ikc_map_str",
        "ihk_os_get_num_assigned_mem_chunks",
        "ihk_os_get_eventfd",
        "ihk_os_load",
        "ihk_os_kargs",
        "ihk_os_kargs_str",
        "ihk_create_os_str",
        "ihk_os_boot",
        "ihk_os_shutdown",
        "ihk_os_get_status",
        "ihk_os_get_kmsg_size",
        "ihk_os_kmsg",
        "ihk_os_clear_kmsg",
        "ihk_os_get_num_numa_nodes",
        "ihk_os_query_free_mem",
        "ihk_os_query_total_mem",
        "ihk_os_get_num_pagesizes",
        "ihk_os_get_pagesizes",
        "ihk_os_setperfevent",
        "ihk_os_perfctl",
        "ihk_os_getperfevent",
        "ihk_os_freeze",
        "ihk_os_thaw",
        "ihk_os_makedumpfile",
        "ihk_set_loglevel",
        "loglevel"
    };
    for (size_t i = 0; i < sizeof(names) / sizeof(names[0]); ++i) {
        Dl_info loaded;
        void *provider = dlsym(RTLD_DEFAULT, names[i]);
        assert(provider != NULL && dladdr(provider, &loaded) != 0);
        assert(strcmp(loaded.dli_fname, CONSUMER_LIBRARY) == 0);
    }
    int *loaded_state = dlsym(RTLD_DEFAULT, "loglevel");
    assert(loaded_state == public_state);
    const int original_level = *loaded_state;
    assert(original_level == IHKLIB_LOGLEVEL_ERR);
    *loaded_state = 0x2468;
    assert(loglevel == 0x2468);
    *loaded_state = original_level;

    unsigned errors = 0, setters = 0;
    const int indices[] = {INT_MIN, -1, INT_MAX};
    const int invalid_counts[] = {0, -1, 1025};
    const int keys[] = {0, 5, -1, 6};
    const int counts[] = {-1, 0, 1, INT_MAX};
    char environment[] = "IHK_CPUS=0";
    int (*environment_ops[])(int, const char *, int) = {
        ihk_reserve_cpu_str, ihk_reserve_mem_str, ihk_os_assign_cpu_str,
        ihk_os_set_ikc_map_str, ihk_reserve_mem_conf_str
    };
    for (size_t i = 0; i < sizeof(indices) / sizeof(indices[0]); ++i) {
        for (size_t f = 0; f < sizeof(environment_ops) / sizeof(environment_ops[0]); ++f) {
            errno = EDOM;
            check_result(environment_ops[f](indices[i], NULL, 1), -EINVAL);
            ++errors;
            for (size_t j = 0; j < sizeof(invalid_counts) / sizeof(invalid_counts[0]); ++j) {
                errno = EDOM;
                check_result(environment_ops[f](indices[i], environment, invalid_counts[j]), -EINVAL);
                ++errors;
            }
        }
        errno = EDOM;
        check_result(ihk_os_kargs_str(indices[i], NULL, 1, NULL), -EINVAL);
        ++errors;
        for (size_t j = 0; j < sizeof(invalid_counts) / sizeof(invalid_counts[0]); ++j) {
            errno = EDOM;
            check_result(ihk_os_kargs_str(indices[i], environment, invalid_counts[j], NULL), -EINVAL);
            ++errors;
        }
        for (size_t j = 0; j < sizeof(keys) / sizeof(keys[0]); ++j) {
            errno = EDOM;
            check_result(ihk_reserve_mem_conf(indices[i], keys[j], NULL), -EFAULT);
            ++errors;
        }
        for (size_t j = 0; j < sizeof(counts) / sizeof(counts[0]); ++j) {
            errno = EDOM;
            check_result(ihk_os_setperfevent(indices[i], NULL, counts[j]), -EFAULT);
            ++errors;
            errno = EDOM;
            check_result(ihk_os_query_free_mem(indices[i], NULL, counts[j]), -EFAULT);
            ++errors;
            errno = EDOM;
            check_result(ihk_os_query_total_mem(indices[i], NULL, counts[j]), -EFAULT);
            ++errors;
        }
    }
    const int empty_sets[] = {0, -1, INT_MIN};
    for (size_t i = 0; i < sizeof(empty_sets) / sizeof(empty_sets[0]); ++i) {
        errno = EDOM;
        check_result(ihk_os_freeze(NULL, empty_sets[i]), -EINVAL);
        ++errors;
        errno = EDOM;
        check_result(ihk_os_thaw(NULL, empty_sets[i]), -EINVAL);
        ++errors;
    }
    const unsigned int levels[] = {0u, 1u, 2u, (unsigned int)INT_MAX, UINT_MAX};
    for (size_t i = 0; i < sizeof(levels) / sizeof(levels[0]); ++i) {
        /* Qualify the original enum-to-int store using this selected C compiler.
         * Out-of-range conversion is implementation-defined, not universal. */
        int expected = (int)levels[i];
        errno = EDOM;
        check_result(ihk_set_loglevel((enum IHKLIB_LOGLEVEL)levels[i]), 0);
        assert(*loaded_state == expected && loglevel == expected);
        ++setters;
    }
    *loaded_state = original_level;
    assert(errors == 126 && setters == 5);
    printf("PASS remaining public ABI: 43 typed function imports, public writable loglevel and 44 exact providers; %u pre-access error calls and %u pure logging setters; no device/ioctl\n", errors, setters);
    return 0;
}
