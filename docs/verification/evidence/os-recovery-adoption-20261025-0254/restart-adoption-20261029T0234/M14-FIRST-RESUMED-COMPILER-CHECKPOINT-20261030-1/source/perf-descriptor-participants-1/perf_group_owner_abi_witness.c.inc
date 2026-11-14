/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * PRIVATE WITNESS ONLY. Include after actual selected process/mc_perf_event
 * headers in a separately reviewed opt-in witness translation unit. This adds
 * no C runtime behavior and does not select the Rust ownership candidate.
 */
#if defined(ENABLE_PERF) && defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL) && defined(MCKERNEL_F03_PERF_OWNER_ABI_WITNESS)
_Static_assert(sizeof(unsigned long) == sizeof(void *), "x86 witness width");
const unsigned long f03_perf_group_owner_c_layout_v2[33] = {
    sizeof(struct mckfd), _Alignof(struct mckfd),
    __builtin_offsetof(struct mckfd, fd), __builtin_offsetof(struct mckfd, data),
    __builtin_offsetof(struct mckfd, opt), __builtin_offsetof(struct mckfd, read_cb),
    __builtin_offsetof(struct mckfd, ioctl_cb), __builtin_offsetof(struct mckfd, mmap_cb),
    __builtin_offsetof(struct mckfd, close_cb), __builtin_offsetof(struct mckfd, fcntl_cb),
    sizeof(struct mc_perf_event), _Alignof(struct mc_perf_event),
    __builtin_offsetof(struct mc_perf_event, group_leader),
    __builtin_offsetof(struct mc_perf_event, sibling_list),
    __builtin_offsetof(struct mc_perf_event, group_entry),
    __builtin_offsetof(struct mc_perf_event, nr_siblings),
    __builtin_offsetof(struct mc_perf_event, counter_id),
    __builtin_offsetof(struct mc_perf_event, pmc_status),
    sizeof(ihk_spinlock_t), _Alignof(ihk_spinlock_t),
    sizeof(struct list_head), _Alignof(struct list_head),
    __builtin_offsetof(struct list_head, next), __builtin_offsetof(struct list_head, prev),
    sizeof(struct process), _Alignof(struct process),
    __builtin_offsetof(struct process, mckfd_lock), __builtin_offsetof(struct process, mckfd),
    __builtin_offsetof(struct mckfd, next), __builtin_offsetof(struct mckfd, dup_cb),
    __builtin_offsetof(ihk_spinlock_t, head_tail),
    sizeof(((ihk_spinlock_t *)0)->head_tail), _Alignof(__typeof__(((ihk_spinlock_t *)0)->head_tail)),
};
#define F03_CALLBACK_CHECK(field, ret) _Static_assert(__builtin_types_compatible_p( \
    __typeof__(((struct mckfd *)0)->field), ret (*)(struct mckfd *, ihk_mc_user_context_t *)), #field " ABI")
F03_CALLBACK_CHECK(read_cb, long);
F03_CALLBACK_CHECK(ioctl_cb, int);
F03_CALLBACK_CHECK(mmap_cb, long);
F03_CALLBACK_CHECK(close_cb, int);
F03_CALLBACK_CHECK(fcntl_cb, int);
F03_CALLBACK_CHECK(dup_cb, int);
#undef F03_CALLBACK_CHECK
_Static_assert(__builtin_types_compatible_p(__typeof__(&__ihk_mc_spinlock_lock),
    unsigned long (*)(ihk_spinlock_t *)), "spinlock lock ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&__ihk_mc_spinlock_unlock),
    void (*)(ihk_spinlock_t *, unsigned long)), "spinlock unlock ABI");
#endif
