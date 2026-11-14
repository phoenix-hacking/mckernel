# Pending-free integration sequencing review — 2026-09-15

Status: **PASS_DESIGN_ONLY**. A private bounded-inventory fixture may proceed;
production integration remains blocked.

Stage 1 is an unused private inventory model: fixed-capacity `InventoryBuilder`,
identity/generation/range `DescriptorRecord`, `FrozenInventory`,
`ValidatedInventory`, `InventoryError`, and a stable exclusively borrowed
`DescriptorArena`. Capacity is reserved before removal; count comes only from
successful producer insertion and freezes under exclusive ownership. Resolve every
address to an independently supplied identity before reading its descriptor;
recognize only the supplied sentinel. Validate exact cardinality, uniqueness,
reciprocal links, pending mode, positive checked page extents, alignment,
membership and nonoverlap with bounded work/storage. Failure changes no descriptor
and invokes no release callback. `ValidatedInventory` grants no detach/free right.

Stage 2 requires the surviving OS registry and nonreused OS/VM/serial transaction
identity described in the durable-owner review. Stage 3 records removal, host-MM
clear, TLB completion, alias drainage and publication separately; only their
reviewed conjunction mints a transaction-bound release permit. Retry retains the
batch; terminal/unknown failure quarantines it. Stage 4 jointly reviews producer
arena lifetime, registry, lock ordering, handoff, teardown and acknowledgement
before any production caller wiring.

The next source-packet write allowlist is only:

- `kernel/rust/tests/pending_free_inventory_v1.rs`
- `kernel/rust/tests/pending_free_inventory_vectors_v1.rs`
- `kernel/rust/tests/pending_free_inventory_reference_v1.c`
- `kernel/rust/tests/pending_free_inventory_harness_v1.py`

Required private negatives cover zero/exact/exceeded capacity, count mismatch and
overflow, duplicate/foreign descriptors, null/dangling/one-sided links, malformed
sentinel and foreign cycle, wrong mode, invalid/overflow page count, misaligned or
foreign/overlapping extents, stale generation and concurrent mutation attempts.
Instrument reads to prove rejection before invalid-address access and byte-identical
descriptors/zero callbacks on failure.

No production integration without a trusted arena/count producer, surviving
registry, typed release authorization and separately reviewed execution packet.
Private candidate SHA256 remains
`647825d8c51a9f584d1229a2389fbb81105e4bbf94bfcf95a12d172c5dde112b`.
No runtime or production credit follows.
