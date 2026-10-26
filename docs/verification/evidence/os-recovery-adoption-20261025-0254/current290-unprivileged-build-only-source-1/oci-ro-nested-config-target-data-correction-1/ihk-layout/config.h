/* config.h.in.  Generated from configure.ac by autoheader.  */

/* IHK build-id to confirm IHK and McKernel built at the same time are used */
#define BUILDID "3114d9e"

/* whether memdump feature is enabled */
#define ENABLE_MEMDUMP 1

/* whether perf is enabled */
#define ENABLE_PERF 1

/* whether rusage is enabled */
#define ENABLE_RUSAGE 1

/* for non-RHEL kernels */
#ifndef RHEL_RELEASE_VERSION
#define RHEL_RELEASE_VERSION(a,b) (((a) << 8) + (b))
#endif
