/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
/* Test-only, include after the selected original kernel syscall.c and its real
 * headers. Pair this object with the exact selected Rust object. This is no
 * production source, execution release, completed comparison, or host ACK. */
#include "../REQUEST-PACKET-ABI-WITNESS.c.inc"

#ifdef MCKERNEL_RUST_F03_DO_SYSCALL_SUPPORTED
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-do-syscall-supported-orchestration-source-1/REAL-HEADER-ABI-AND-ALLOCATED-CONSUMER.c.inc"
static int f03_check_do_syscall_abi_pair(void)
{
    unsigned int i;
    for (i = 0; i < 29; ++i)
        if (f03_do_syscall_C_ABI_v1[i] != f03_do_syscall_Rust_ABI_v1[i])
            return (int)i + 1;
    return 0;
}
#endif

#ifdef MCKERNEL_RUST_F03_UTIL_THREAD_WHOLE
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-util-thread-whole-owned-source-1/REAL-HEADER-ABI-WITNESS.c.inc"
extern const unsigned long f03_util_thread_Rust_ABI_v1[23];
static int f03_check_util_thread_abi_pair(void)
{
    unsigned int i;
    for (i = 0; i < 23; ++i)
        if (f03_util_thread_C_ABI_v1[i] != f03_util_thread_Rust_ABI_v1[i])
            return (int)i + 1;
    return 0;
}
#endif

#if defined(MCKERNEL_RUST_F03_DO_SYSCALL_SUPPORTED) && defined(MCKERNEL_RUST_F03_UTIL_THREAD_WHOLE)
/* Test harness calls this only after linking the exact Rust provider object.
 * 1..29 identifies the first do_syscall ABI difference; 101..123 identifies
 * the first util_thread difference. A missing selector cannot report success. */
int f03_queue_b_compare_real_abi_pairs(void)
{
    int mismatch = f03_check_do_syscall_abi_pair();
    if (mismatch)
        return mismatch;
    mismatch = f03_check_util_thread_abi_pair();
    if (mismatch)
        return 100 + mismatch;
    return 0;
}
#endif
