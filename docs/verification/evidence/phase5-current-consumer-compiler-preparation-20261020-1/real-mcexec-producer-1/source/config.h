/* config.h.in.  Generated from configure.ac by autoheader.  */

/* IHK build-id to confirm IHK and McKernel built at the same time are used */
#define BUILDID "3114d9e"

/* version number */
#define MCKERNEL_VERSION "1.8.0"

/* enable the required code for mcexec to be able to use bind mount
 * there is no config option as its use is discouraged */
// #define MCEXEC_BIND_MOUNT 1

/* whether memdump feature is enabled */
#define ENABLE_MEMDUMP 1

/* whether perf is enabled */
#define ENABLE_PERF 1

/* whether qlmpi is enabled */
/* #undef ENABLE_QLMPI */

/* whether rusage is enabled */
#define ENABLE_RUSAGE 1

/* whether UTI is enabled */
/* #undef ENABLE_UTI */

/* whether undefined behaviour sanitizer is enabled */
/* #undef ENABLE_UBSAN */

/* whether per-CPU allocator cache (ThunderX2 workaround) is enabled */
/* #undef ENABLE_PER_CPU_ALLOC_CACHE */

/* Path of bind-mount source directory */
#define ROOTFSDIR "/rootfs"

/* for non-RHEL kernels */
#ifndef RHEL_RELEASE_VERSION
#define RHEL_RELEASE_VERSION(a,b) (((a) << 8) + (b))
#endif
