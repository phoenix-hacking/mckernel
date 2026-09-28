# Compact dispatcher handoff

Reconciled for launcher preparation: 2026-09-27. Campaign remains STOPPED at
the user's request; a later normal launcher invocation authorizes continuation.
Runner/resource/recovery preparation is recorded in
`LAUNCH-PREPARATION-20260927.md`. No OS acceptance counter changes follow.

## First resume

Read GOAL.md, START.md and CONVERGENCE.md. Record the policy hash after checking
out the update. Reconcile actual HEAD, dirty/untracked inputs, latest CURRENT.md
entries and retained reviews, launcher-owned state, file leases and runtime
owners before choosing a command. Do not edit launcher-owned state by hand.
Fetch/inspect remote changes without resetting, cleaning or overwriting local
work. A running dispatcher must reload the changed instructions at a safe
checkpoint; a GitHub documentation commit does not restart it.

Preparation baseline: `47262eb3ffd0017011b2cbcdff97579c7677bcf0`, branch
`codex/local-native-staging-repair`. The M02 and M03 inputs still match their
retained failed-review hashes. Subsequent changes may supersede those findings;
confirm consumed bytes and do not replay repaired work.
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

## Preparation cursor; recheck live ownership on launch

- Source: baseline above plus the launcher-preparation checkpoint. Pre-existing
  local deletion of `scripts/__pycache__/rust-source-retirement-audit.cpython-36.pyc`
  was preserved. Launcher records current policy hashes on each invocation.
- Saved thread: `01a0a312-8c59-7c80-93de-0b64adde646b`; persisted phase stopped,
  goal paused, stop reason `signal_15`. State and watcher files are unchanged.
- Active OS families: none executing. M02 retains source failure 60; M03 retains
  source failure 2. Resume with consolidated expert repair, not a reset budget.
- Layer-B release is still required for those OS fixtures. The independent
  launcher tests and container isolation checks do not release OS execution.
- Existing scratch image restored at its original mount with nodev/nosuid;
  approximately 21 GiB free. Original 4-CPU/12-GiB/512-task controls restored.
- Aggressive host scheduling: up to eight children, all affinity CPUs for local
  commands, up to 24 GiB shared memory budget. One heavy build/guest owner;
  privileged container profiles retain their independently reviewed limits.
- Next work: M02 real descriptor/identity repair and independent M03 executable
  admission; M01 fresh source-only attempt follows its retained review 43 once
  restored input hashes are authenticated. See the preparation record for paths.
- Campaign launch is pending the user; no paid goal continuation or OS payload
  was started by preparation. Reconcile all runtime leases before heavy work.

Keep this cursor compact. Preserve original failures and chronological history
in CURRENT.md and the existing evidence/event mechanism; do not copy that entire
history into this file or treat these bootstrap fields as machine runtime state.
