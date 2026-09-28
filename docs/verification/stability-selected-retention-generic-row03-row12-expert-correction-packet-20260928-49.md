# M01-B packet48 correction49 — wake-none, address, teardown, and staging repair

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**.  This additive correction binds
expert packet48 SHA256
`d0528c1022f19d6ae555edee745630ac43966b8b5b4c5d64a7dee3b95d5c2000` and
its independent `FAIL_PACKET` findings.  Packet48, packet29, corrections
31/34/36/39/42/45, review46, failure47, attempt45 root, and archive45 remain
immutable and normative unless this document identifies an exact conflict.
This correction releases no source attempt, staging, compilation, execution,
Phase II, guest/native execution, production gate, application acceptance, or
whole-OS acceptance before an independent combined `PASS_PACKET` review.

## 1. Wake-none is not completion-query presence

Replace packet48's assertion that the initial post-`return_value`
`verification_phase_completion(selection)` result is `present=true`.  For the
exact packet29 wake-none request, that initial query must instead remain
exactly `Err(-71)`: the retained `Completion` has response state true and wake
state false, whereas the existing query accepts only `(true, true)`.  Assert
that error and immediately assert phase invalid remains exactly zero.  Do not
change the request's wake field, `Completion::verification_state`,
`verification_phase_completion`, delivery phase, or query preconditions to
make this query succeed.

The row must prove the retained completion/owner without using that failing
query as a presence oracle.  Its mode-local test may inspect only existing
immutable metadata through the mailbox's existing test-visible call/worker
state or one new module-local `#[cfg(test)]` metadata accessor.  The accessor
must return copied scalar metadata only: completion-present, response-present,
completion response/wake booleans, delivery phase, worker/delivery identity,
and `Option<Claim>`.  It must confirm the exact selected Claim and returning
delivery identity, response present before `return_value`, completion present
after it, `(response,wake)==(true,false)`, and no duplicate/alias owner.  It
must not read the response backing, call `address`, alter a wake, mutate a
call/worker/phase field, fabricate a `CompletionStatus`, or weaken the real
query.  The sole required absent completion-query outcome remains row12 after
successful publication.

## 2. Exact address accounting and event order

Packet48's address/event wording is replaced by this exact accounting.  The
fixture ledger records every actual `TestResponseMemory::address` invocation;
the observer record is a separate selected-claim counter.  In each fresh row:

1. `Response::from_memory` invokes `address` during `admit`, before
   `observer::select`: fixture total becomes one, while observer total remains
   zero because no selected Claim exists.
2. `verification_prepare_retained` invokes `address` during the real
   `return_value`: fixture total becomes two and observer total becomes one.
   The preparation baseline is recorded only **after** that second call, the
   real selected acceptance transition, the initial `Err(-71)` query, and its
   invalid-zero assertion.
3. Row03's gate returns `Err(-11)` before `Completion::publish`, so it adds no
   third address call: fixture/observer totals stay two/one through teardown
   and drain.
4. Row12's successful `Completion::publish` invokes `address` once before the
   actual status store: fixture/observer totals become three/two.  No later
   address call is permitted.

The exact row12 event ordering is `Construction, Address, Address,
PreparationBaseline, Address, StatusStore, Release, DeferredInsertion,
FinishedDrop, Deallocation`; row03 before close is `Construction, Address,
Address, PreparationBaseline`, and its teardown ordering is then
`UnfinishedDrop, QuarantineInsertion, Deallocation`.  A static/source checker
must distinguish fixture totals from observer totals and reject a baseline
placed before the second address call, any synthesized address event, or any
address/backing/pointer observation after the status store.  All geometry,
Claim, no-alias, post-release and duplicate-release assertions in packet48
remain required with these corrected totals.

## 3. Row03 invalid lifetime

Packet48's row03 pre-teardown phase assertions remain: after accepted stage 2,
after the held `publish Err(-11)`, and immediately before teardown, invalid is
exactly 0, stage is 2, and release commits are 0.  The row then calls the real
`close_worker(worker)` and requires its actual `Err(-71)` cancellation path.
The retained selected cancellation guard must latch phase invalid exactly
`-125`; assert that value immediately after `close_worker`, after mailbox
destruction, and after quarantine drain.  It must remain `-125`, never be
cleared/replaced, and no later phase operation may be used to manufacture a
different result.  Continue to require destruction before quarantine drain,
one unfinished drop, one quarantine insertion, one deallocation, zero release
and finished-drop, no live fixture owner after destruction, and unchanged
address/send/post-release/duplicate-release counters.

## 4. Narrow Phase-I staging authorization after review only

This section supersedes only packet48's blanket prohibition on invoking the
stager.  After a dispatcher has reauthenticated every inherited pin, bound the
canonical absent root48, and recorded an independent combined `PASS_PACKET`,
the Phase-I source owner may invoke **only** the existing authenticated
source-only stager, once per independent mode, using exactly:

```text
python3 -B scripts/tests/prepare_stability_selected_retention.py --source /home/holden/mckernel-work/scratch/stability-selected-retention-authority-20260915-1/mode2 --output /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-48/mode2 --mode postpublish-notify
python3 -B scripts/tests/prepare_stability_selected_retention.py --source /home/holden/mckernel-work/scratch/stability-published-held-source-20260915-recoverable-backpressure-3/held/source --output /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-48/mode3 --mode recoverable-backpressure
```

Both source trees, the stager, manifest, and exact source-member identities
must first match their inherited pins; source/output trees remain canonical,
disjoint, mode-owned, and absent before creation.  The inherited stager's
first-failure and no-bytecode rules apply.  This is only the necessary
source-copy/inverse-check preparation for Phase I.  It does **not** authorize
any other interpreter import, candidate test, compiler, binary, container,
guest, network, root/sudo action, Phase II evidence owner, or acceptance
claim.  After staging, only packet48's static file/hash, byte-reading parse,
structural/erasure/inverse, no-bytecode, and `git diff --check` checks remain
allowed.  First failure writes only correction31's `phase-i-failure.txt`,
preserves the root, and stops without retry or repair.

## Static review boundary

Independent review must reject any candidate that does not bind packet48 and
this correction; accepts wake-none by changing live semantics; treats the
initial query as present; conflates fixture and observer address totals;
omits the `-125` lifetime; drains before destruction; grants the stager before
dispatcher binding plus `PASS_PACKET`; or expands the named command envelope.
The review result is a packet decision only.  No evidence in this correction
counts as an implementation, executed test, or acceptance credit.
