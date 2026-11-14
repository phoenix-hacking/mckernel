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

#ifdef MCKERNEL_RUST_F03_UTIL_THREAD_WHOLE
/* Compare each Rust-owned layout field to this translation unit's actual C
 * header. The 16 scalar values are copied by name, never by pointer punning. */
static int f03_check_util_layout_pair(void)
{
    const size_t actual[16] = {
        f03_util_thread_layout_v1.context_size, f03_util_thread_layout_v1.info_size,
        f03_util_thread_layout_v1.context, f03_util_thread_layout_v1.refill_tid,
        f03_util_thread_layout_v1.info_thread_va, f03_util_thread_layout_v1.info_response_pa,
        f03_util_thread_layout_v1.info_channel_pa, f03_util_thread_layout_v1.info_tid,
        f03_util_thread_layout_v1.info_cpu, f03_util_thread_layout_v1.info_status_pa,
        f03_util_thread_layout_v1.info_sleep_lock_pa, f03_util_thread_layout_v1.info_sleep_pa,
        f03_util_thread_layout_v1.info_vm_pa, f03_util_thread_layout_v1.info_futex_q_pa,
        f03_util_thread_layout_v1.info_idle_halt, f03_util_thread_layout_v1.info_futex_queue_pa,
    };
    const size_t expected[16] = {
        sizeof(struct uti_ctx), sizeof(struct uti_info),
        __builtin_offsetof(struct uti_ctx,ctx), __builtin_offsetof(struct uti_ctx,uti_refill_tid),
        __builtin_offsetof(struct uti_info,thread_va), __builtin_offsetof(struct uti_info,uti_futex_resp_pa),
        __builtin_offsetof(struct uti_info,ikc2linux_pa), __builtin_offsetof(struct uti_info,tid),
        __builtin_offsetof(struct uti_info,cpu), __builtin_offsetof(struct uti_info,status_pa),
        __builtin_offsetof(struct uti_info,spin_sleep_lock_pa), __builtin_offsetof(struct uti_info,spin_sleep_pa),
        __builtin_offsetof(struct uti_info,vm_pa), __builtin_offsetof(struct uti_info,futex_q_pa),
        __builtin_offsetof(struct uti_info,mc_idle_halt), __builtin_offsetof(struct uti_info,futex_queue_pa),
    };
    unsigned int i;
    for (i = 0; i < 16; ++i)
        if (actual[i] != expected[i])
            return (int)i + 1;
    return 0;
}
#endif

#if defined(MCKERNEL_RUST_F03_DO_SYSCALL_SUPPORTED) && defined(MCKERNEL_RUST_F03_UTIL_THREAD_WHOLE)
/* Test harness calls this only after linking the exact Rust provider object.
 * 1..29 identifies the first do_syscall ABI difference; 101..123 identifies
 * the first util_thread difference; 201..216 identifies a layout difference.
 * A missing selector cannot report success. */
int f03_queue_b_compare_real_abi_pairs(void)
{
    int mismatch = f03_check_do_syscall_abi_pair();
    if (mismatch)
        return mismatch;
    mismatch = f03_check_util_thread_abi_pair();
    if (mismatch)
        return 100 + mismatch;
    mismatch = f03_check_util_layout_pair();
    if (mismatch)
        return 200 + mismatch;
    return 0;
}
#endif
