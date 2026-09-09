/* SPDX-License-Identifier: GPL-2.0-only */
/* Benign, bounded futex deadline and ordinary pthread application checks. */
#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <linux/futex.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

_Static_assert(sizeof(struct timespec) == 16, "x86_64 timespec ABI");
_Static_assert(sizeof(uint32_t) == 4, "futex word ABI");
_Static_assert(ATOMIC_INT_LOCK_FREE == 2, "raw clone callback needs lock-free int atomics");
#define STACK_BYTES (256U * 1024U)
#define MAX_ELAPSED_NS INT64_C(2000000000)
#define CHECK(value) do { if (!(value)) { \
    fprintf(stderr, "NATIVE_ULTRA_FUTEX FAIL line=%d errno=%d\n", __LINE__, errno); \
    exit(1); \
} } while (0)

static unsigned completed;
static char report_buffer[4096];
static uint32_t word;
static pthread_barrier_t start_barrier;
static _Atomic int stop_workers;
static _Atomic int worker_error;
static _Thread_local uintptr_t local_token;
struct worker_result { uint64_t count; long tid; uintptr_t token; };
static struct worker_result worker_results[2];
static _Atomic int raw_tid_cell = -1;
static _Atomic int raw_entry_tid;
static _Atomic int raw_entry_cell;
static _Atomic int raw_entered;

static int64_t now_ns(void)
{
    struct timespec value;
    CHECK(clock_gettime(CLOCK_MONOTONIC, &value) == 0);
    CHECK(value.tv_sec >= 0 && value.tv_sec < INT64_MAX / INT64_C(1000000000));
    CHECK(value.tv_nsec >= 0 && value.tv_nsec < 1000000000L);
    return (int64_t)value.tv_sec * INT64_C(1000000000) + value.tv_nsec;
}

static struct timespec from_ns(int64_t value)
{
    CHECK(value >= 0);
    return (struct timespec){ .tv_sec = value / INT64_C(1000000000),
                             .tv_nsec = value % INT64_C(1000000000) };
}

static void futex_case(const char *id, uint32_t *address, int operation,
                       uint32_t expected_word, const struct timespec *timeout,
                       uint32_t bitset, long expected_result, int expected_errno,
                       int64_t minimum_ns, int64_t absolute_deadline_ns)
{
    int64_t before = now_ns();
    errno = 0;
    long result = syscall(SYS_futex, address, operation, expected_word,
                          timeout, NULL, bitset);
    int error = errno;
    int64_t after = now_ns();
    int64_t elapsed = after - before;
    fprintf(stderr, "NATIVE_ULTRA_FUTEX_CASE id=%s result=%ld errno=%d elapsed_ns=%" PRId64
            " before_ns=%" PRId64 " after_ns=%" PRId64 " deadline_ns=%" PRId64 "\n",
            id, result, error, elapsed, before, after, absolute_deadline_ns);
    CHECK(result == expected_result && error == expected_errno);
    CHECK(elapsed >= minimum_ns && elapsed <= MAX_ELAPSED_NS);
    if (absolute_deadline_ns > 0)
        CHECK(after >= absolute_deadline_ns - INT64_C(1000000));
    ++completed;
}

static void barrier(void)
{
    int result = pthread_barrier_wait(&start_barrier);
    CHECK(result == 0 || result == PTHREAD_BARRIER_SERIAL_THREAD);
}

static void *worker(void *argument)
{
    uintptr_t index = (uintptr_t)argument;
    struct worker_result *result = &worker_results[index];
    CHECK(local_token == 0);
    local_token = index + 1;
    result->tid = syscall(SYS_gettid);
    CHECK(result->tid > 0);
    int64_t started = now_ns();
    barrier();
    uint64_t count = 0;
    while (!atomic_load_explicit(&stop_workers, memory_order_acquire)) {
        ++count;
        /* Yield without blocking: the thread remains runnable, exercising
         * the timeout's runqueue branch without assuming user preemption. */
        if ((count & UINT64_C(1048575)) == 0)
            CHECK(sched_yield() == 0);
        /* No allocation, unbounded counter, or clock/syscall per iteration. */
        if (count == UINT64_C(20000000) ||
            ((count & UINT64_C(1048575)) == 0 && now_ns() - started > MAX_ELAPSED_NS)) {
            atomic_store_explicit(&worker_error, 1, memory_order_release);
            atomic_store_explicit(&stop_workers, 1, memory_order_release);
            break;
        }
    }
    CHECK(local_token == index + 1);
    result->count = count;
    result->token = local_token;
    return (void *)local_token;
}

static void pthread_cases(void)
{
    pthread_t threads[2];
    pthread_attr_t attributes;
    CHECK(pthread_attr_init(&attributes) == 0);
    CHECK(pthread_attr_setstacksize(&attributes, STACK_BYTES) == 0);
    CHECK(pthread_attr_setguardsize(&attributes, 4096) == 0);
    CHECK(pthread_barrier_init(&start_barrier, NULL, 3) == 0);
    int64_t before = now_ns();
    for (uintptr_t index = 0; index != 2; ++index)
        CHECK(pthread_create(&threads[index], &attributes, worker, (void *)index) == 0);
    barrier();
    struct timespec relative = { .tv_sec = 0, .tv_nsec = 10000000 };
    futex_case("wait_relative_runnable", &word, FUTEX_WAIT_PRIVATE, 0,
               &relative, 0, -1, ETIMEDOUT, INT64_C(9000000), 0);
    atomic_store_explicit(&stop_workers, 1, memory_order_release);
    for (uintptr_t index = 0; index != 2; ++index) {
        void *returned = NULL;
        CHECK(pthread_join(threads[index], &returned) == 0);
        CHECK(returned == (void *)(index + 1));
        CHECK(worker_results[index].token == index + 1 && worker_results[index].count > 0);
    }
    CHECK(!atomic_load_explicit(&worker_error, memory_order_acquire));
    CHECK(local_token == 0);
    long parent_tid = syscall(SYS_gettid);
    CHECK(parent_tid > 0 && worker_results[0].tid != parent_tid && worker_results[1].tid != parent_tid);
    CHECK(worker_results[0].tid != worker_results[1].tid);
    CHECK(pthread_barrier_destroy(&start_barrier) == 0);
    CHECK(pthread_attr_destroy(&attributes) == 0);
    int64_t elapsed = now_ns() - before;
    fprintf(stderr, "NATIVE_ULTRA_FUTEX_THREADS joined=2 parent_tid=%ld tid0=%ld tid1=%ld"
            " count0=%" PRIu64 " count1=%" PRIu64 " token0=1 token1=2 stack_bytes=%u elapsed_ns=%" PRId64 "\n",
            parent_tid, worker_results[0].tid, worker_results[1].tid,
            worker_results[0].count, worker_results[1].count, STACK_BYTES, elapsed);
    CHECK(elapsed >= 0 && elapsed <= INT64_C(6000000000));
}

/* No CLONE_SETTLS: this callback must not use libc, errno, TLS, allocation or
 * a stack protector. The build helper checks its exact ELF instructions. */
__attribute__((noinline, used))
static int raw_child_entry(void *unused)
{
    (void)unused;
    long tid = SYS_gettid;
    __asm__ volatile("syscall" : "+a"(tid) : : "rcx", "r11", "memory");
    int observed = atomic_load_explicit(&raw_tid_cell, memory_order_acquire);
    atomic_store_explicit(&raw_entry_tid, (int)tid, memory_order_relaxed);
    atomic_store_explicit(&raw_entry_cell, observed, memory_order_relaxed);
    atomic_store_explicit(&raw_entered, 1, memory_order_release);
    return 0; /* glibc clone's child stub issues thread-only SYS_exit. */
}

static void raw_clone_case(void)
{
    const size_t allocation = STACK_BYTES + 2 * 4096;
    unsigned char *stack = mmap(NULL, allocation, PROT_NONE,
                                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    CHECK(stack != MAP_FAILED);
    CHECK(mprotect(stack + 4096, STACK_BYTES, PROT_READ | PROT_WRITE) == 0);
    const int flags = CLONE_VM | CLONE_FS | CLONE_FILES | CLONE_SIGHAND |
        CLONE_THREAD | CLONE_SYSVSEM | CLONE_CHILD_SETTID | CLONE_CHILD_CLEARTID;
    CHECK(atomic_load_explicit(&raw_tid_cell, memory_order_acquire) == -1);
    int64_t before = now_ns();
    int tid = clone(raw_child_entry, stack + 4096 + STACK_BYTES, flags, NULL,
                    NULL, NULL, (int *)&raw_tid_cell);
    CHECK(tid > 0);
    unsigned waits = 0;
    for (;;) {
        int value = atomic_load_explicit(&raw_tid_cell, memory_order_acquire);
        if (value == 0)
            break;
        CHECK(now_ns() - before <= MAX_ELAPSED_NS && waits < 256);
        struct timespec timeout = { 0, 10000000 };
        errno = 0;
        /* clear_child_tid uses a shared wake, so this wait is not PRIVATE. */
        long result = syscall(SYS_futex, &raw_tid_cell, FUTEX_WAIT, value,
                              &timeout, NULL, 0);
        int error = errno;
        CHECK((result == 0 && error == 0) ||
              (result == -1 && (error == EAGAIN || error == ETIMEDOUT)));
        ++waits;
    }
    int entered = atomic_load_explicit(&raw_entered, memory_order_acquire);
    int entry_tid = atomic_load_explicit(&raw_entry_tid, memory_order_relaxed);
    int stored_tid = atomic_load_explicit(&raw_entry_cell, memory_order_relaxed);
    int64_t elapsed = now_ns() - before;
    long parent = syscall(SYS_gettid);
    fprintf(stderr, "NATIVE_ULTRA_FUTEX_CLONE parent_tid=%ld child_tid=%d entry_tid=%d stored_tid=%d"
            " cleared_tid=0 entered=%d wait_calls=%u elapsed_ns=%" PRId64 " flags=%x stack_bytes=%u\n",
            parent, tid, entry_tid, stored_tid, entered, waits, elapsed, flags, STACK_BYTES);
    CHECK(parent > 0 && parent != tid && entered == 1 && entry_tid == tid && stored_tid == tid);
    CHECK(elapsed >= 0 && elapsed <= MAX_ELAPSED_NS);
    CHECK(munmap(stack, allocation) == 0);
}

int main(void)
{
    /* Buffer bounded diagnostics so they do not consume the guest trace
     * before the independently checked application transitions. exit() also
     * flushes this buffer on a CHECK failure. */
    CHECK(setvbuf(stderr, report_buffer, _IOFBF, sizeof report_buffer) == 0);
    CHECK(sysconf(_SC_PAGESIZE) == 4096);
    /* Fixture-owned mappings/stacks stay below 1 MiB; no large heap or files.
     * This is not an assertion about loader mappings or total virtual size. */
    unsigned char *pages = mmap(NULL, 8192, PROT_READ | PROT_WRITE,
                                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    CHECK(pages != MAP_FAILED);
    CHECK(mprotect(pages + 4096, 4096, PROT_NONE) == 0);
    struct timespec zero = { 0, 0 }, relative = { 0, 10000000 };
    struct timespec bad_seconds = { -1, 0 }, bad_negative_ns = { 0, -1 };
    struct timespec bad_large_ns = { 0, 1000000000 };
    struct timespec expired = { 0, 0 };
    int64_t first_seconds = 0;
    memcpy(pages + 4096 - sizeof(first_seconds), &first_seconds, sizeof(first_seconds));

    futex_case("wait_mismatch", &word, FUTEX_WAIT_PRIVATE, 1, &zero, 0, -1, EAGAIN, 0, 0);
    futex_case("wait_relative_zero", &word, FUTEX_WAIT_PRIVATE, 0, &zero, 0, -1, ETIMEDOUT, 0, 0);
    futex_case("wait_relative_10ms", &word, FUTEX_WAIT_PRIVATE, 0, &relative, 0, -1, ETIMEDOUT, INT64_C(9000000), 0);
    futex_case("wait_bitset_expired", &word, FUTEX_WAIT_BITSET_PRIVATE, 0, &expired,
               FUTEX_BITSET_MATCH_ANY, -1, ETIMEDOUT, 0, 0);
    int64_t deadline = now_ns() + INT64_C(10000000);
    struct timespec future = from_ns(deadline);
    futex_case("wait_bitset_future", &word, FUTEX_WAIT_BITSET_PRIVATE, 0, &future,
               FUTEX_BITSET_MATCH_ANY, -1, ETIMEDOUT, 0, deadline);
    futex_case("wait_null_word", NULL, FUTEX_WAIT_PRIVATE, 0, &zero, 0, -1, EFAULT, 0, 0);
    futex_case("wait_unaligned_word", (uint32_t *)(pages + 1), FUTEX_WAIT_PRIVATE, 0,
               &zero, 0, -1, EINVAL, 0, 0);
    futex_case("timeout_protected", &word, FUTEX_WAIT_PRIVATE, 0,
               (const struct timespec *)(pages + 4096), 0, -1, EFAULT, 0, 0);
    futex_case("timeout_cross_page", &word, FUTEX_WAIT_PRIVATE, 0,
               (const struct timespec *)(pages + 4096 - 8), 0, -1, EFAULT, 0, 0);
    futex_case("timeout_negative_seconds", &word, FUTEX_WAIT_PRIVATE, 0,
               &bad_seconds, 0, -1, EINVAL, 0, 0);
    futex_case("timeout_negative_nanoseconds", &word, FUTEX_WAIT_PRIVATE, 0,
               &bad_negative_ns, 0, -1, EINVAL, 0, 0);
    futex_case("timeout_large_nanoseconds", &word, FUTEX_WAIT_PRIVATE, 0,
               &bad_large_ns, 0, -1, EINVAL, 0, 0);
    futex_case("wait_bitset_zero", &word, FUTEX_WAIT_BITSET_PRIVATE, 0,
               &zero, 0, -1, EINVAL, 0, 0);
    futex_case("wake_empty", &word, FUTEX_WAKE_PRIVATE, 1, NULL, 0, 0, 0, 0, 0);
    void *vacant = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    CHECK(vacant != MAP_FAILED);
    uintptr_t vacant_address = (uintptr_t)vacant;
    CHECK(munmap(vacant, 4096) == 0);
    futex_case("wake_unmapped_private", (uint32_t *)vacant_address,
               FUTEX_WAKE_PRIVATE, 1, NULL, 0, 0, 0, 0, 0);
    CHECK(munmap(pages, 8192) == 0);
    /* Observe this distinct clone route before the runnable-peer test. */
    raw_clone_case();
    pthread_cases();
    CHECK(completed == 16);
    CHECK(fputs("NATIVE_ULTRA_FUTEX PASS cases=16 threads=2 raw_clone=1\n", stdout) >= 0);
    CHECK(fflush(stdout) == 0 && fflush(stderr) == 0);
    return 37;
}
