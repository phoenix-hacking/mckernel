/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/new-window-source-37-coherent-lifetime-worker-whole-rust-source-1/bounded-pregrant-correction-1/candidate/kernel/process.c"
_Static_assert((sizeof(struct thread)) == 5568UL, "Source38 genuine ABI word 0");
_Static_assert((__alignof__(struct thread)) == 64UL, "Source38 genuine ABI word 1");
_Static_assert((__builtin_offsetof(struct thread, tid)) == 20UL, "Source38 genuine ABI word 2");
_Static_assert((__builtin_offsetof(struct thread, hash_list)) == 0UL, "Source38 genuine ABI word 3");
_Static_assert((__builtin_offsetof(struct thread, refcount)) == 4628UL, "Source38 genuine ABI word 4");
_Static_assert((__builtin_offsetof(struct thread, proc)) == 4304UL, "Source38 genuine ABI word 5");
_Static_assert((__builtin_offsetof(struct thread, vm)) == 4200UL, "Source38 genuine ABI word 6");
_Static_assert((sizeof(((struct thread *)0)->refcount.counter)) == 4UL, "Source38 genuine ABI word 7");
_Static_assert((__builtin_offsetof(struct process, pid)) == 456UL, "Source38 genuine ABI word 8");
_Static_assert((sizeof(struct process)) == 1728UL, "Source38 genuine ABI word 9");
_Static_assert((__alignof__(struct process)) == 64UL, "Source38 genuine ABI word 10");
_Static_assert((sizeof(struct thread_hash)) == 5888UL, "Source38 genuine ABI word 11");
_Static_assert((__alignof__(struct thread_hash)) == 64UL, "Source38 genuine ABI word 12");
_Static_assert((__builtin_offsetof(struct thread_hash, list)) == 0UL, "Source38 genuine ABI word 13");
_Static_assert((__builtin_offsetof(struct thread_hash, lock)) == 1216UL, "Source38 genuine ABI word 14");
_Static_assert((sizeof(struct mcs_rwlock_lock)) == 64UL, "Source38 genuine ABI word 15");
_Static_assert((__alignof__(struct mcs_rwlock_lock)) == 64UL, "Source38 genuine ABI word 16");
_Static_assert((sizeof(struct mcs_rwlock_node_irqsave)) == 64UL, "Source38 genuine ABI word 17");
_Static_assert((__alignof__(struct mcs_rwlock_node_irqsave)) == 64UL, "Source38 genuine ABI word 18");
_Static_assert((__builtin_offsetof(struct cpu_local_var, resource_set)) == 7912UL, "Source38 genuine ABI word 19");
_Static_assert((sizeof(struct resource_set)) == 384UL, "Source38 genuine ABI word 20");
_Static_assert((__alignof__(struct resource_set)) == 64UL, "Source38 genuine ABI word 21");
_Static_assert((__builtin_offsetof(struct resource_set, thread_hash)) == 32UL, "Source38 genuine ABI word 22");
_Static_assert((sizeof(struct list_head)) == 16UL, "Source38 genuine ABI word 23");
_Static_assert((__alignof__(struct list_head)) == 8UL, "Source38 genuine ABI word 24");
_Static_assert((__builtin_offsetof(struct list_head, next)) == 0UL, "Source38 genuine ABI word 25");
_Static_assert((__builtin_offsetof(struct list_head, prev)) == 8UL, "Source38 genuine ABI word 26");
_Static_assert((sizeof(unsigned long)) == 8UL, "Source38 genuine ABI word 27");
_Static_assert((__alignof__(unsigned long)) == 8UL, "Source38 genuine ABI word 28");
_Static_assert((sizeof(int)) == 4UL, "Source38 genuine ABI word 29");
_Static_assert((__alignof__(int)) == 4UL, "Source38 genuine ABI word 30");
_Static_assert((HASH_SIZE) == 73UL, "Source38 genuine ABI word 31");
_Static_assert((sizeof(process_thread_action_fn_t)) == 8UL, "Source38 genuine ABI word 32");
_Static_assert((sizeof(process_mcs_rwlock_fn_t)) == 8UL, "Source38 genuine ABI word 33");
_Static_assert((sizeof(((struct thread_hash *)0)->list[0])) == 16UL, "Source38 genuine ABI word 34");
_Static_assert((sizeof(((struct thread_hash *)0)->lock[0])) == 64UL, "Source38 genuine ABI word 35");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_try_hold_thread_live_v2), int (*)(void *)), "positive-only C int hold ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_destroy_thread_hash_detach_candidate_v3), process_thread_action_fn_t), "genuine void final-detach callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&find_thread), struct thread *(*)(int,int)), "existing public pointer lookup ABI");
typedef void * (*source38_process_find_thread_live_body_result_v2_fn)(
    struct list_head *head, unsigned long hash_lock, void *lock_node,
    int pid, int tid, const struct process_find_thread_offsets *offsets,
    process_mcs_rwlock_fn_t lock, process_mcs_rwlock_fn_t unlock,
    process_thread_try_hold_fn_v2 try_hold);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_find_thread_live_body_result_v2), source38_process_find_thread_live_body_result_v2_fn), "exact full process_find_thread_live_body_result_v2 C ABI");
