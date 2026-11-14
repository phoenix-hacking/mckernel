/* SPDX-License-Identifier: GPL-2.0 */
/* TEST ORACLE ONLY: controlled lower-primitive boundary, never module input. */
#ifndef M15_MM_FIXTURE_RUNTIME_H
#define M15_MM_FIXTURE_RUNTIME_H
#include <stdbool.h>
#include <stdint.h>
struct rw_semaphore { uint32_t fixture_id; uint32_t held; };
typedef struct { uint32_t sequence; } seqcount_t;
struct mm_struct { struct rw_semaphore mmap_lock; seqcount_t mm_lock_seq; };
struct vma_lock { struct rw_semaphore lock; };
struct vm_area_struct {
    struct mm_struct *vm_mm;
    uint32_t vm_lock_seq;
    struct vma_lock *vm_lock;
};
/* Each callback must append (operation, object identity, observed value) to
 * one ordered log. Gates have separate scripted outer/inner answers to expose
 * trace enable/disable transitions; helpers must retain the second gate. */
bool m15_fixture_outer_gate(unsigned event);
void m15_fixture_trace_start(struct mm_struct *, bool);
void m15_fixture_trace_acquire(struct mm_struct *, bool, bool);
void m15_fixture_trace_release(struct mm_struct *, bool);
void down_write(struct rw_semaphore *);
void up_write(struct rw_semaphore *);
void m15_fixture_smp_wmb(void);
void m15_fixture_write_once_u32(volatile uint32_t *, uint32_t);
void __mmap_lock_do_trace_start_locking(struct mm_struct *, bool);
void __mmap_lock_do_trace_acquire_returned(struct mm_struct *, bool, bool);
void __mmap_lock_do_trace_released(struct mm_struct *, bool);
/* Exact pin: these instrumentation/diagnostic facilities are disabled. */
#define kcsan_nestable_atomic_begin() ((void)0)
#define kcsan_nestable_atomic_end() ((void)0)
#define ASSERT_EXCLUSIVE_WRITER(value) ((void)0)
#define rwsem_assert_held_write(sem) ((void)(sem))
#define smp_wmb() m15_fixture_smp_wmb()
#define WRITE_ONCE(value, new_value) \
    m15_fixture_write_once_u32(&(value), (uint32_t)(new_value))
#define M15_EVENT_mmap_lock_start_locking 0u
#define M15_EVENT_mmap_lock_acquire_returned 1u
#define M15_EVENT_mmap_lock_released 2u
#define tracepoint_enabled(name) m15_fixture_outer_gate(M15_EVENT_##name)
#endif
