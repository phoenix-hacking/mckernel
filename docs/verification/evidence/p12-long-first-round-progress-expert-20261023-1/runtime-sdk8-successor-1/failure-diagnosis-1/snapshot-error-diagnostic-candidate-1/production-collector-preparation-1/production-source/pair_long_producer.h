/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Declarations only; no C producer/allocator/ownership implementation added. */
#ifndef MCKERNEL_PAIR_LONG_PRODUCER_H
#define MCKERNEL_PAIR_LONG_PRODUCER_H
#include <stdint.h>
#include <stddef.h>
struct pair_long_bytes { const uint8_t *ptr; size_t len; };
struct pair_long_app {
    uint64_t pid, started_ns, reaped_ns, finished_ns;
    int32_t raw_wait_status, clean, stdout_eof, stderr_eof;
};
struct pair_long_pair {
    struct pair_long_app apps[2];
    uint64_t os, generation;
    int32_t strict_gate_result, ownership_complete;
    struct pair_long_bytes report, trace;
};
struct pair_long_operations {
    uint64_t (*now_ns)(void *);
    int32_t (*empty)(void *, uint32_t, uint64_t);
    int32_t (*run_pair)(void *, uint32_t, uint64_t, struct pair_long_pair *);
    ptrdiff_t (*retain_trace)(void *, const uint8_t *, size_t);
    ptrdiff_t (*read_trace)(void *, uint64_t, uint8_t *, size_t);
    ptrdiff_t (*write_serial)(void *, const uint8_t *, size_t);
};
struct pair_long_summary {
    uint64_t rounds, launches, work_ns, elapsed_ns, trace_bytes;
    int32_t ownership_complete, completed;
};
int32_t pair_run_long_session(void *, const struct pair_long_operations *, struct pair_long_summary *);
int32_t pair_complete_long_session(void *, const struct pair_long_operations *, struct pair_long_summary *, uint64_t, uint64_t);
#endif
