/* Header-only HOST diagnostic; no syscall or perf body is compiled. */
#include <types.h>
#include <kmsg.h>
#include <ihk/cpu.h>
#include <cpulocal.h>
#include <ihk/mm.h>
#include <ihk/ikc.h>
#include <errno.h>
#include <cls.h>
#include <syscall.h>
#include <page.h>
#include <amemcpy.h>
#include <uio.h>
#include <ihk/lock.h>
#include <ctype.h>
#include <waitq.h>
#include <rlimit.h>
#include <affinity.h>
#include <time.h>
#include <ihk/perfctr.h>
#include <mman.h>
#include <kmalloc.h>
#include <memobj.h>
#include <shm.h>
#include <prio.h>
#include <arch/cpu.h>
#include <limits.h>
#include <mc_perf_event.h>
#include <march.h>
#include <process.h>
#include <process_helpers.h>
#include <bitops.h>
#include <bitmap.h>
#include <xpmem.h>
#include <rusage_private.h>
#include <ihk/monitor.h>
#include <profile.h>
#include <ihk/debug.h>
#include <sched_helpers.h>
#include "../executer/include/uti.h"

/* Headers taken from kitten LWK */
#include <lwk/stddef.h>
#include <futex.h>

#if !defined(ENABLE_PERF) || !defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)
#error "HOST witness requires actual ENABLE_PERF and F03 perf entry selector"
#endif
_Static_assert(__builtin_offsetof(struct mckfd, sig_no) == 12, "mckfd sig_no slot ABI");
_Static_assert(sizeof(struct mckfd) == 80 && _Alignof(struct mckfd) == 8, "perf mckfd size ABI");
_Static_assert(__builtin_offsetof(struct mckfd, opt) == 24, "perf mckfd opt ABI");
_Static_assert(__builtin_offsetof(struct mckfd, dup_cb) == 72, "perf mckfd dup ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct mckfd *)0)->opt), void *), "perf mckfd opt type ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct mckfd *)0)->dup_cb), int (*)(struct mckfd *, ihk_mc_user_context_t *)), "perf mckfd dup type ABI");

/* Inspectable C layout facts; no production selector or runtime provider. */
__attribute__((used, visibility("hidden"))) const unsigned long m14_host_mckfd_c_layout[5] = {
    sizeof(struct mckfd), _Alignof(struct mckfd),
    __builtin_offsetof(struct mckfd, sig_no),
    __builtin_offsetof(struct mckfd, opt),
    __builtin_offsetof(struct mckfd, dup_cb)
};
