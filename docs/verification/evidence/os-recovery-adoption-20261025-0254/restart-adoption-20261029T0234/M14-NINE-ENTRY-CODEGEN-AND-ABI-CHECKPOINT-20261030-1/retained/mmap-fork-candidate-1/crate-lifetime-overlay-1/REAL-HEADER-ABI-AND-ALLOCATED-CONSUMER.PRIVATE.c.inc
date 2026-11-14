/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
/* Include the exact private C proposal with its explicit profile selectors. */
_Static_assert(__builtin_types_compatible_p(__typeof__(&do_fork),
 unsigned long (*)(int, unsigned long, unsigned long, unsigned long,
                  unsigned long, unsigned long, unsigned long)), "whole fork public ABI");
_Static_assert(sizeof(((struct thread *)0)->pthread_routine) == PATH_MAX + 64,
 "real bounded diagnostic destination");
_Static_assert(sizeof(struct f03_tid_pool_origins) == sizeof(void *) * 3 + 24,
 "real origin transport with actual int padding");
_Static_assert(sizeof(struct owned_fork_caller_outcome) == 24,
 "real existing metadata-only constructor disposition");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct f03_fork_origins *)0)->ptrace_report),
 int (*)(struct thread *, struct thread *, int)), "genuine retained ptrace callback debt");
__typeof__(&do_fork) f03_whole_fork_entry_address_v1 = &do_fork;
const unsigned long f03_do_fork_C_ABI_v1[46] = {
 sizeof(struct thread),
 __alignof__(struct thread),
 __builtin_offsetof(struct thread, proc),
 __builtin_offsetof(struct thread, vm),
 __builtin_offsetof(struct thread, cpu_id),
 __builtin_offsetof(struct thread, uctx),
 __builtin_offsetof(struct thread, clone_pthread_start_routine),
 __builtin_offsetof(struct thread, mod_clone),
 __builtin_offsetof(struct thread, pthread_routine),
 __builtin_offsetof(struct thread, cpu_set),
 __builtin_offsetof(struct thread, tid),
 __builtin_offsetof(struct thread, refcount),
 sizeof(struct process),
 __alignof__(struct process),
 __builtin_offsetof(struct process, coredump_barrier_count),
 __builtin_offsetof(struct process, uti_thread_rank),
 __builtin_offsetof(struct process, clone_count),
 __builtin_offsetof(struct process, uti_use_last_cpu),
 __builtin_offsetof(struct process, cpu_set),
 __builtin_offsetof(struct process, ppid_parent),
 __builtin_offsetof(struct process, pid),
 __builtin_offsetof(struct process, threads_lock),
 __builtin_offsetof(struct process, nr_tids),
 __builtin_offsetof(struct process, tids),
 sizeof(struct mcexec_tid),
 __alignof__(struct mcexec_tid),
 __builtin_offsetof(struct mcexec_tid, tid),
 __builtin_offsetof(struct mcexec_tid, thread),
 sizeof(cpu_set_t),
 __alignof__(cpu_set_t),
 sizeof(struct owned_fork_caller_outcome),
 __alignof__(struct owned_fork_caller_outcome),
 __builtin_offsetof(struct owned_fork_caller_outcome, disposition),
 __builtin_offsetof(struct owned_fork_caller_outcome, error),
 __builtin_offsetof(struct owned_fork_caller_outcome, handle),
 __builtin_offsetof(struct process, update_lock),
 sizeof(((struct process *)0)->update_lock),
 __alignof__(((struct process *)0)->update_lock),
 sizeof(ihk_atomic_t),
 __alignof__(ihk_atomic_t),
 __builtin_offsetof(ihk_atomic_t, counter),
 __builtin_offsetof(struct thread, refcount) + __builtin_offsetof(ihk_atomic_t, counter),
 sizeof(((struct thread *)0)->refcount.counter),
 __alignof__(((struct thread *)0)->refcount.counter),
 sizeof(int),
 __alignof__(int),
};

_Static_assert(sizeof(ihk_atomic_t) == sizeof(int), "atomic storage width");
_Static_assert(__alignof__(ihk_atomic_t) == __alignof__(int), "atomic storage alignment");
_Static_assert(__builtin_offsetof(ihk_atomic_t, counter) == 0, "atomic counter is prefix");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread *)0)->refcount.counter), int), "counter is signed int");
