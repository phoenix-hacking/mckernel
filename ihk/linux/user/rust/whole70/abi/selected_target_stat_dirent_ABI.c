/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Nonshipped selected-target header ABI check; no device/library provider runs. */
#include <stdio.h>
#include <sys/stat.h>
#include <dirent.h>
#include <stddef.h>
#include <ihk/ihklib_private.h>
_Static_assert(sizeof(struct stat)==144 && _Alignof(struct stat)==8,"Rust stat storage144/8");
_Static_assert(__builtin_types_compatible_p(__typeof__(&stat),
    int(*)(const char*,struct stat*)),"selected public stat provider ABI");
_Static_assert(sizeof(struct dirent)==280 && offsetof(struct dirent,d_name)==19,
    "selected existing readdir provider layout280/name19");
_Static_assert(sizeof(((struct dirent*)0)->d_ino)==8 &&
    sizeof(((struct dirent*)0)->d_off)==8 && sizeof(((struct dirent*)0)->d_reclen)==2,
    "selected existing dirent scalar ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&readdir),
    struct dirent*(*)(DIR*)),"selected readdir symbol ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_os_get_status),int(*)(int)),"status");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_os_kmsg),int(*)(int,char*,ssize_t)),"kmsg");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihklib_os_query_mem_sysfs),
    int(*)(int,char*,ssize_t,const char*)),"sysfs");
