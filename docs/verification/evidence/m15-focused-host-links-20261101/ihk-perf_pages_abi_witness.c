/* NONSHIPPED metadata witness; never link into production.
 * Functional OS/apps and Rust/assembly migration only; no security testing. */
#include <errno.h>
#include <limits.h>
#include <stddef.h>
#include <stdio.h>
#include <ihk/ihklib.h>
#include <ihk/ihk_host_user.h>
#if !defined(__x86_64__) || !defined(__linux__)
#error Current qualification covers Linux x86_64 LP64 only
#endif
_Static_assert(CHAR_BIT == 8 && sizeof(int) == 4 && sizeof(long) == 8 &&
    sizeof(void *) == 8 && sizeof(unsigned long) == 8, "selected scalar ABI");
#define SAME(type, expression) _Static_assert( \
    __builtin_types_compatible_p(type, __typeof__(expression)), #expression " ABI")
SAME(int (*)(int, ihk_perf_event_attr *, int), &ihk_os_setperfevent);
SAME(int (*)(int, int), &ihk_os_perfctl);
SAME(int (*)(int, unsigned long *, int), &ihk_os_getperfevent);
SAME(int (*)(int), &ihk_os_get_num_pagesizes);
SAME(int (*)(int, long *, int), &ihk_os_get_pagesizes);
#define INT(name, value) printf("pub const " #name ": core::ffi::c_int = %d;\n", (int)(value))
#define ULONG(name, value) printf("pub const " #name ": core::ffi::c_ulong = %lu;\n", (unsigned long)(value))
int main(void)
{
    int i;
    puts("// Generated from selected actual IHK headers; no runtime C dependency.");
    INT(EFAULT, EFAULT);
    INT(EINVAL, EINVAL);
    INT(PERF_ENABLE, PERF_EVENT_ENABLE);
    INT(PERF_DISABLE, PERF_EVENT_DISABLE);
    INT(PERF_DESTROY, PERF_EVENT_DESTROY);
    ULONG(PERF_NUM, IHK_OS_AUX_PERF_NUM);
    ULONG(PERF_SET, IHK_OS_AUX_PERF_SET);
    ULONG(PERF_GET, IHK_OS_AUX_PERF_GET);
    ULONG(PERF_ENABLE_REQUEST, IHK_OS_AUX_PERF_ENABLE);
    ULONG(PERF_DISABLE_REQUEST, IHK_OS_AUX_PERF_DISABLE);
    ULONG(PERF_DESTROY_REQUEST, IHK_OS_AUX_PERF_DESTROY);
    INT(IHK_MAX_NUM_PGSIZES, IHK_MAX_NUM_PGSIZES);
    printf("pub const PAGE_SIZES: [core::ffi::c_long; %d] = [", IHK_MAX_NUM_PGSIZES);
    for (i = 0; i < IHK_MAX_NUM_PGSIZES; ++i)
        printf("%s%ld", i ? ", " : "", rusage_pgtype_to_pgsize((enum ihk_os_pgsize)i));
    puts("];");
    printf("// Opaque attr actual size=%zu align=%zu; never copied/dereferenced by Rust.\n",
        sizeof(ihk_perf_event_attr), _Alignof(ihk_perf_event_attr));
    return 0;
}
