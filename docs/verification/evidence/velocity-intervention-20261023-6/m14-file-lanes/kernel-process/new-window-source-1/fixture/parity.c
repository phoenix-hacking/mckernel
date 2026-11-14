/* Functional OS parity fixture source only; no security testing.
 * Mock layouts check behavior only; actual-header/fullcrate ABI proof remains open.
 */
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define HASH_SIZE 73
struct list_head { struct list_head *next, *prev; };
struct mcs_rwlock_lock { int dummy; };
struct mcs_rwlock_node_irqsave { int dummy; };
struct ihk_atomic { int counter; };
struct process {
    struct list_head hash_list;
    struct process *ppid_parent;
    struct ihk_atomic refcount;
    int status, pid;
};
struct thread {
    struct list_head hash_list;
    struct process *proc;
    int cpu_id, tid, status, in_syscall_offload;
    struct ihk_atomic refcount;
    int ptrace;
};
struct process_hash {
    struct list_head list[HASH_SIZE];
    struct mcs_rwlock_lock lock[HASH_SIZE];
};
struct thread_hash {
    struct list_head list[HASH_SIZE];
    struct mcs_rwlock_lock lock[HASH_SIZE];
};
struct resource_set {
    struct process_hash *process_hash;
    struct thread_hash *thread_hash;
    struct process *pid1;
};
struct cpu_local_var { struct resource_set *resource_set; };

static struct process_hash processes;
static struct thread_hash threads;
static struct process init, first, second;
static struct thread worker1, worker2, worker3;
static struct resource_set resources = { &processes, &threads, &init };
static struct cpu_local_var cpu = { &resources };
static char output[16384];
static size_t output_len;
struct event { uintptr_t lock; int action; };
static struct event trace[2 * HASH_SIZE];
static size_t trace_len;
static struct mcs_rwlock_node_irqsave *active_node;
static struct mcs_rwlock_lock *active_lock;

struct cpu_local_var *get_this_cpu_local_var(void) { return &cpu; }

int kprintf(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    int n = vsnprintf(output + output_len, sizeof(output) - output_len, format, args);
    va_end(args);
    if (n < 0 || (size_t)n >= sizeof(output) - output_len) abort();
    output_len += (size_t)n;
    return n;
}

void fixture_reader_lock(struct mcs_rwlock_lock *lock,
                         struct mcs_rwlock_node_irqsave *node)
{
    if (active_lock || trace_len >= 2 * HASH_SIZE) abort();
    active_node = node;
    active_lock = lock;
    trace[trace_len++] = (struct event){ (uintptr_t)lock, 1 };
    node->dummy = 1234;
}

void fixture_reader_unlock(struct mcs_rwlock_lock *lock,
                           struct mcs_rwlock_node_irqsave *node)
{
    if (active_lock != lock || active_node != node || node->dummy != 1234 ||
        trace_len >= 2 * HASH_SIZE) abort();
    trace[trace_len++] = (struct event){ (uintptr_t)lock, 2 };
    active_node = NULL;
    active_lock = NULL;
}

#define __mcs_rwlock_reader_lock fixture_reader_lock
#define __mcs_rwlock_reader_unlock fixture_reader_unlock
#define debug_log reference_debug_log
#include "original_debug_log.ACTUAL-C.inc"
#undef debug_log
extern void debug_log(unsigned long arg);

static void list_init(struct list_head *head) { head->next = head->prev = head; }
static void list_add_tail(struct list_head *head, struct list_head *entry)
{
    entry->prev = head->prev;
    entry->next = head;
    head->prev->next = entry;
    head->prev = entry;
}

static void reset_capture(void)
{
    memset(output, 0, sizeof(output));
    memset(trace, 0, sizeof(trace));
    output_len = trace_len = 0;
    if (active_lock || active_node) abort();
}

static int check(unsigned long arg, int populated)
{
    char expected_output[sizeof(output)];
    struct event expected_trace[2 * HASH_SIZE];
    reset_capture();
    reference_debug_log(arg);
    memcpy(expected_output, output, sizeof(output));
    memcpy(expected_trace, trace, sizeof(trace));
    size_t expected_len = trace_len;
    reset_capture();
    debug_log(arg);
    printf("CASE populated=%d arg=%lu\nREFERENCE_OUTPUT_BEGIN\n%sREFERENCE_OUTPUT_END\n"
           "RUST_OUTPUT_BEGIN\n%sRUST_OUTPUT_END\n", populated, arg, expected_output, output);
    printf("LOCK_COUNTS reference=%zu rust=%zu\n", expected_len, trace_len);
    for (size_t i = 0; i < expected_len; ++i) {
        printf("REFERENCE_LOCK %zu %p %d\n", i,
               (void *)expected_trace[i].lock, expected_trace[i].action);
    }
    for (size_t i = 0; i < trace_len; ++i) {
        printf("RUST_LOCK %zu %p %d\n", i, (void *)trace[i].lock, trace[i].action);
    }
    fflush(stdout);
    int trace_mismatch = trace_len != expected_len;
    for (size_t i = 0; i < trace_len && i < expected_len; ++i) {
        if (trace[i].lock != expected_trace[i].lock ||
            trace[i].action != expected_trace[i].action) trace_mismatch = 1;
    }
    if (strcmp(output, expected_output) || trace_mismatch) {
        fprintf(stderr, "FAIL arg=%lu populated=%d expected=%s actual=%s locks=%zu/%zu\n",
                arg, populated, expected_output, output, expected_len, trace_len);
        return 1;
    }
    size_t required = (arg == 1 || arg == 2) ? 2 * HASH_SIZE : 0;
    if (trace_len != required) return 2;
    if ((arg < 1 || arg > 4) && output_len) return 3;
    return 0;
}

int main(void)
{
    const unsigned long args[] = { 0, 1, 2, 3, 4, 5, ~0UL };
    for (int i = 0; i < HASH_SIZE; ++i) {
        list_init(&processes.list[i]);
        list_init(&threads.list[i]);
    }
    int cases = 0;
    for (int populated = 0; populated <= 1; ++populated) {
        if (populated) {
            init.pid = 1;
            init.ppid_parent = &init;
            first = (struct process){ .ppid_parent = &init,
                .refcount = { 3 }, .status = 2, .pid = 41 };
            second = (struct process){ .ppid_parent = &first,
                .refcount = { 4 }, .status = 7, .pid = 42 };
            worker1 = (struct thread){ .proc = &first, .cpu_id = 2, .tid = 101,
                .status = 3, .in_syscall_offload = 1,
                .refcount = { 5 }, .ptrace = (int)0x80000001U };
            worker2 = (struct thread){ .proc = &second, .cpu_id = 3, .tid = 102,
                .status = 4, .in_syscall_offload = 0,
                .refcount = { 6 }, .ptrace = 0x1234 };
            worker3 = (struct thread){ .proc = &init, .cpu_id = 4, .tid = 103,
                .status = 5, .in_syscall_offload = 2,
                .refcount = { 7 }, .ptrace = -1 };
            list_add_tail(&processes.list[0], &init.hash_list);
            list_add_tail(&processes.list[72], &first.hash_list);
            list_add_tail(&processes.list[72], &second.hash_list);
            list_add_tail(&threads.list[0], &worker1.hash_list);
            list_add_tail(&threads.list[72], &worker2.hash_list);
            list_add_tail(&threads.list[72], &worker3.hash_list);
        }
        for (size_t i = 0; i < sizeof(args) / sizeof(args[0]); ++i) {
            int error = check(args[i], populated);
            if (error) return error;
            ++cases;
        }
    }
    printf("PASS debug_log actual-C/Rust parity: %d cases, output and lock order\n", cases);
    return 0;
}
