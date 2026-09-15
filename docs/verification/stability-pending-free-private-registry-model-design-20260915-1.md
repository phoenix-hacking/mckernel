# Pending-free private registry model design 1

Date: 2026-09-15
Task: `M03-pending-free-private-registry-model-design`
Disposition: `MODEL_DESIGN_ONLY`

The exact new-file allowlist is `pending_free_registry_model_v1.rs`,
`pending_free_registry_driver_v1.rs`, `pending_free_registry_vectors_v1.json`,
`pending_free_registry_reference_v1.c`,
`pending_free_registry_compile_fail_v1.rs`, and
`pending_free_registry_harness_v1.py` under `kernel/rust/tests/`. Creation must
fail if any exists. Existing dirty/untracked candidates and production/build files
are not writable.

The safe standalone Rust model forbids unsafe code. `ModelWorld` independently owns
mock OS, VM and backing objects. A fixed-capacity `Registry` owns transaction slots
and a retained archive. Transactions own non-Copy/non-Clone mock references and an
immutable metadata-only `MockInventory`; handles carry identity only. There are no
registry back-references.

Identity includes nonzero u64 world epoch, OS generation, VM incarnation,
transaction and recovery-lease serials, descriptor and arena generations; a checked
u32 OS slot below 64; checked u64 geometry; and bounded u32 capacities/budgets.
Every increment/range is checked and exhaustion never wraps or resets.

The state machine is `Reserved -> Registered -> Retained -> Recovering -> Retained
| Quarantined | Archived`. Registration atomically attaches inventory and owned
references. Owner departure never removes a row. One exclusive nonreused lease
drives bounded recovery; interruption revokes it while retaining committed progress.
Unknown or exhausted work is enumerable quarantine. Archive atomically moves all
ownership to a retained archive and leaves a stale-handle tombstone; it never
releases backing. Only an empty Reserved row may be cancelled. OS destruction is
refused while any obligation or lease exists; restart receives a fresh epoch.

Vectors cover capacity, registration failure, identity/range overflow and reuse,
foreign epochs, duplicate inventory, owner departure at each transition, recovery
competition/interruption/stale commits, late completion, budget exhaustion,
archive rollback, teardown refusal and unchanged unrelated rows. Removal, MM clear,
acknowledgement and publication are distinct mock observations and never create
release authority.

The harness sends canonical traces to an actual Rust model and independently
implemented C state table, comparing every full snapshot to reviewed literal
expectations and then each other. Compile-fail probes with positive controls cover
cloning/moving retained ownership, private authority construction and thread sharing.
Mutants for stale leases, wrapping, premature deletion and teardown must fail. There
are no callbacks, raw pointers, physical memory, production imports, detach/free
methods or release permits; backing bytes and pending modes remain unchanged.

Future dispatcher-owned checks require absolute pinned compiler paths, a fresh
external output directory, bounded time/output and fully retained source/compiler
hashes, invocation/environment, streams and status. Source review precedes them.
No integration, invalidation, recovery-runtime or production credit follows.
