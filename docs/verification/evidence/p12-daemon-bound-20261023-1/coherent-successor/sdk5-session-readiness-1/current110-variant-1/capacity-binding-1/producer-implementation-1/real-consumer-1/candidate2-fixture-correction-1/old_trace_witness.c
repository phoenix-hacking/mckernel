/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual unchanged retained legacy gate, for old/new body regression only. */
#define ND_PAIR_LAUNCH_EXPANSION
#define main preserved_legacy_collector_main
#include "/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/candidate/pair_collector.c"
#undef main
int old_trace_witness(const char *log,int pid,int cpu) {
    pair_seen_token_count=0;return pair_round_trace(log,pid,cpu);
}
