/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Nonshipped compile-only witness for the reused Rust layout; no C runtime provider. */
#include "rusage_public_abi_witness.c"
#include <stddef.h>
#include <ihk/ihklib_private.h>
_Static_assert(sizeof(unsigned long)==8 && sizeof(void*)==8,"LP64");
_Static_assert(IHK_MAX_NUM_PGSIZES==8,"existingRust page-count");
_Static_assert(IHK_MAX_NUM_NUMA_NODES==1024,"existingRust NUMA-count");
_Static_assert(IHK_MAX_NUM_CPUS==1024,"existingRust CPU-count");
_Static_assert(sizeof(struct ihk_os_rusage)==16568,"actualRust rusage layout");
_Static_assert(offsetof(struct ihk_os_rusage,num_threads)==16560,"actualRust threads");
_Static_assert(sizeof(struct mcctrl_ioctl_getrusage_desc)==16,"actualRust request");
_Static_assert(offsetof(struct mcctrl_ioctl_getrusage_desc,size_rusage)==8,"requestsize8");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_os_getrusage),
    int (*)(int,struct ihk_os_rusage*,size_t)),"publicgetrusage ABI");
