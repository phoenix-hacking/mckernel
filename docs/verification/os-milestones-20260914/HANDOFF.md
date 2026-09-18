# Compact dispatcher handoff

Policy bootstrap: 2026-09-17. State: RECONCILIATION REQUIRED.
This is an instruction-update handoff, NOT a live runner observation, execution
release, completed task, or acceptance record. No OS or harness code was repaired
or executed by this documentation change.

## First resume

Read GOAL.md, START.md and CONVERGENCE.md. Record the policy hash after checking
out the update. Reconcile actual HEAD, dirty/untracked inputs, latest CURRENT.md
entries and retained reviews, launcher-owned state, file leases and runtime
owners before choosing a command. Do not edit launcher-owned state by hand.
Fetch/inspect remote changes without resetting, cleaning or overwriting local
work. A running dispatcher must reload the changed instructions at a safe
checkpoint; a GitHub documentation commit does not restart it.

Reviewed remote baseline: `499e8a70742f4b2e493a8a3dbbfb99b1d5bb3948`, branch
`codex/local-native-staging-repair`. Subsequent local/remote changes may supersede
the source findings below. Confirm consumed bytes; do not replay repaired work.
Official gate/case/point status remains in the original acceptance records.
Do not promote any counter for adopting this policy.

## Primary family: collector descriptor and identity integrity (M02)

Retained starting review:
`../stability-linux-collector-storage-fault-v2-source-review-failure-20260916-60.json`.
The source at the reviewed baseline still contains the descriptor remapping
sequence identified there. Relevant files are under
`scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/`:
`witness_owner.py`, `supervise.py`, `oracle.py`, and `collector.patch`.

Next deliverable: an alias-safe remap implementation tested with real ordinary
subprocess descriptor operations, plus the producer/observer identity fixes from
the same consolidated review. Preserve every source until all destinations are
installed; handle closed 0/1/2, source-equals-destination and fd 198 collisions.
Verify intended descriptors survive exec and unintended inherited descriptors do
not. Preserve stdout/stderr and cleanup semantics. Do not test a fake dictionary
and claim the actual descriptor behavior passed.

Bind positive acquisition IDs to the real producer sequence, including failed
creates and both successful create sites. Reject aliases of simultaneously live
resource identities while allowing source-defined post-retirement reuse. Retain
legitimate positive controls. Use layer B first after its bounded profile is
released, then the existing separately reviewed root/adverse qualification.
The old review count is NOT a fresh two-attempt budget: consolidate the retained
family history and escalate before another same-strategy repair loop.

## Independent family: pending-free executable admission (M03)

At the reviewed baseline, inspect
`kernel/rust/tests/pending_free_inventory_harness_v1.py`,
`pending_free_inventory_reference_v1.c`, `pending_free_inventory_vectors_v1.rs`
and `pending_free_inventory_v1.rs` in that same tests directory.

Next deliverable: a compilable independent C reference, actual descriptor-state
constructors and executable valid-single/valid-two plus invalid-state tests.
Correct the sentinel/data-ID distinction: rejecting the sentinel as a data item
must not reject valid first/last links to that sentinel. Fix the C preprocessor
layout and zero-count placeholder constructors. Replace variable-spelling checks
with appropriate structural checks; behavioral claims require execution.
Check overflow/error semantics against the original contract, not just matching
one implementation to the other.

This finite model is not the production pending-free boundary. Tie the repaired
examples to full selected helpers and ABI inputs in `kernel/rust/mem_helpers.rs`.
Preserve pinning, no implicit freeing, unchanged-on-error behavior and the
original source reset contract. Track actual production consumers and the
M03-C/D ownership, failed-invalidation, alias/TLB and reuse proof still due.
Do not substitute another model or widen the task into a whole-OS redesign.

## Next dependent outcome

After the applicable M01/M02/M03 and per-case prerequisites really pass, advance
the reviewed paired Linux/McKernel runner and first eligible M04 case. Do not
wait for unrelated advanced capabilities; do not bypass any actual dependency.
Keep accepted infrastructure, model/body tests and integrated OS acceptance
separate. Every release remains bound to the exact tested artifacts.

## Live fields for the dispatcher to replace after reconciliation

- Current source / dirty-input manifest / adopted policy hash: NOT RECONCILED.
- Active family / cumulative attempts / current strategy: NOT RECONCILED.
- Last executed command and result / retained evidence: NOT OBSERVED HERE.
- Reusable cheap-check profile and release / next exact command: NOT RECONCILED.
- File owners / heavy lease / cleanup evidence: NOT OBSERVED HERE.
- Blocker class and event permitting recheck: NOT RECONCILED.
- Next two dependency-ready tasks: select from the families above after review.

Keep this cursor compact. Preserve original failures and chronological history
in CURRENT.md and the existing evidence/event mechanism; do not copy that entire
history into this file or treat these bootstrap fields as machine runtime state.
