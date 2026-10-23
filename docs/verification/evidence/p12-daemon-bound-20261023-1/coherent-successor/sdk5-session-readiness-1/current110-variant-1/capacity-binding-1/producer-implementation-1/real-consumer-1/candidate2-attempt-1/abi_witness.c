/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "pair_long_producer.h"
_Static_assert(sizeof(struct pair_long_app) == 48, "App ABI");
_Static_assert(sizeof(struct pair_long_pair) == 152, "Pair ABI");
_Static_assert(sizeof(struct pair_long_operations) == 48, "Operations ABI");
_Static_assert(sizeof(struct pair_long_summary) == 48, "Summary ABI");
_Static_assert(offsetof(struct pair_long_pair, report) == 120, "report ABI");
_Static_assert(offsetof(struct pair_long_pair, trace) == 136, "trace ABI");
_Static_assert(offsetof(struct pair_long_summary, completed) == 44, "completion ABI");
int32_t (*const actual_entry_abi)(void *, const struct pair_long_operations *, struct pair_long_summary *) = pair_run_long_session;
