# M01-B expert packet52 — complete retained-owner source correction

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. Author: delegated Astra source
design owner. Concrete defect: attempt48 fails all four blocking obligations
in review51. Next check is independent review of this complete contract, then
one fresh source-only implementation and authenticated handoff. That unlocks
consideration of the separately reviewed compiled microtest; it does not unlock
Phase II, compilation or execution now. Attempts45 and48 are the failed candidate
and bounded correction in the same family. This is the escalated coherent
boundary repair, not a reset of that history.

## Immutable inputs and scope

Packet29 and corrections31/34/36/39/42/45, expert packet48, correction49 and
review50 remain normative except where this packet explicitly replaces an
implementation detail. In particular preserve wake-none `Err(-71)`, the
fixture/observer distinction, the row03 `-125` lifetime, the unique actual
post-store hook, all source authority/inverse requirements, and every prior
failure. Review50 released only root48; it cannot release root52. Review51's
`FAIL_HANDOFF` is authoritative despite the candidate's `PASS_PHASE_I` label.

The exact input root is
`/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-48`.
All hashes below are SHA256, measured from retained bytes during this design.

| Input | Hash |
| --- | --- |
| expert packet48 | `d0528c1022f19d6ae555edee745630ac43966b8b5b4c5d64a7dee3b95d5c2000` |
| packet48 failure review | `e4a24896ffaa5835925b92db4ab8044594887ce033ae368b154dbb1149f69241` |
| correction49 | `e3bf9e30fd41c9c52edcdd6f1769b1db0f8d3dfcb680949813dfd3bae8af68b6` |
| packet review50 | `48c17cbdb44c8cef93dc05070e55a48084133c135a7d07ecc979637f0b3ab601` |
| handoff failure review51 | `2913908f491eeac00cbd15921e4d797820ba1d7bfb3bd55f7367ca2195b1c448` |
| root48 `phase-i-handoff.json` (12,566 bytes) | `0d4023533bd802a456680b04e9bd0ab404fd86771b8cbb57d4f0ed840515dcf0` |
| `evidence/stability-selected-retention-generic-row03-row12-phase-i-attempt-20260928-48.tar.gz` (1,011,877 bytes) | `6bb534ea6893e113e136a890660ccebe9f1b122d10f84546c2e1fbffb92d6cd8` |
| mode2 `adapter.rs` | `f771d2e5e9565091e0a6a18b3fa9f54ae1a770a118491d34774210c3ff7a1d99` |
| mode2 `runner.rs` | `cb804d5995a53f17adb82f85222c5e0f768363733dc94a1d9d146a61f4f326da` |
| mode2 `record.json` | `e65bacba31c884196e4a109e231e70db792c232acd39a2fedf70e9b0c6394b94` |
| mode3 `adapter.rs` | `fed48d0b270c0e67316649ae283dba59a39691941234cc9136428f5b4287ef25` |
| mode3 `runner.rs` | `5a534e522e005d121467234eacb4f01eac4c24b5a6f80266b49d4d7fc8e20bab` |
| mode3 `record.json` | `787fbcc50cfedc2705f6746f55943c4e372e08fd822350414020e185d30cc4bc` |
| both modes `source/application_syscall.rs` | `9121342e2f9ce24be258633c6dd2d4914a096f731b2c05e46d0efa7ffee8c449` |
| mode2 `source/smp_application_syscall.rs` | `660a3d9489fe72462c460f46ced0531de63a01450a6f575fba5f34f5cda33a8f` |
| mode3 `source/smp_application_syscall.rs` | `aba3a861e9fa37955b0174c68e406f976dea5c2f5246c5776dd83666caae8d16` |
| mode2 `source/stability_phase.rs` | `2545ed3b3562fdf7a1f8913a6010c8519872a027191a0aca412dc8d5a6ec981e` |
| mode3 `source/stability_phase.rs` | `53bfd951176dbb165c49690438f3a99fe44c79f99611ae239b666601cb8c79e4` |
| both modes `source/stability_observer.rs` | `fb0a795209d73262b0415e91b55a9c4e7f9ac357cf255460c16dc84233ad6a31` |
| both modes `source/application_rpc.rs` | `40c07fb646300fd8f1ffad5502d555cb228b3b7c8ba05d0da3776af4f790d915` |

The bound handoff supplies all 51 exact source-member sizes/hashes per mode;
the bound archive supplies every remaining root48 byte. Static archive reading
confirmed 338 members, 327 regular files, every file byte equal to root48, and
both 51-member handoff arrays equal to their staged sources. This is provenance
only, not evidence that the candidate works. Retain the 71 inherited authority
pins authenticated in review51; before a future stage reauthenticate the actual
mode authorities, source map, stager, manifests, templates and prior records.
No retained root/archive/packet byte is writable.

Adopted campaign policy hashes: GOAL
`76c4f5d12e3f233c8dc4f8f1a77dd1f2eae9df2ff8fb9f4000ef5a2e94c0bcc3`, START
`6e4b28be2bc6d101da8538d1bb640ef98bccacea011487e750b1ed4ccff61c3a`, CONVERGENCE
`d211e7dcda735dc98c4557e6aead941d07fb595ffc6c2fdb0bd03317f8dc1eab`, HANDOFF
`265cd9997588f84d69f4fa9da00b9df9b7153bf9e94366b478639941e680a415`.

## Future root, owners and exact write boundary

The selected future root, observed absent during design, is
`/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-52`.
Recheck canonicality, absence and disjointness immediately before creation.
The current author may write only this packet. No stager invocation, root52
creation or source edit is released until a fresh independent `PASS_PACKET`
and dispatcher source-owner assignment bind this exact packet and all inputs.

After that release only, one source owner uses these two existing commands:

```text
python3 -B scripts/tests/prepare_stability_selected_retention.py --source /home/holden/mckernel-work/scratch/stability-selected-retention-authority-20260915-1/mode2 --output /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-52/mode2 --mode postpublish-notify
python3 -B scripts/tests/prepare_stability_selected_retention.py --source /home/holden/mckernel-work/scratch/stability-published-held-source-20260915-recoverable-backpressure-3/held/source --output /home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-52/mode3 --mode recoverable-backpressure
```

The creation allowlist is exactly packet29 Phase I as corrected by31/34/36:
per mode, directories `source/`, `originals/`, `inputs/`, `diffs/`; `helper.py`,
`record.json`; the six inherited named inputs; and each manifest's 51
`source/<name>`, `originals/<name>`, `diffs/<name>.diff`; plus `adapter.rs`,
`runner.rs`. Add only root `phase-i-handoff.json` on success, or instead the
six-field `phase-i-failure.txt` on failure. Success is 327 regular single-link
files, no symlinks/bytecode/extra paths. The compact sorted-key handoff schema,
mode order, canonical root and 51-member arrays remain exactly corrections34/36.
No Phase-II file may exist. Modes are independently staged/authored; never
copy, include, link or read candidate bytes from the sibling mode.

After staging, content edits are allowed only in these five files per mode:
`adapter.rs`, `runner.rs`, `source/application_syscall.rs`,
`source/smp_application_syscall.rs`, `source/stability_phase.rs`.
All candidate additions are `cfg(test)` and erase exactly to authenticated
stager output under `cfg(not(test))`; the production method signatures,
branches, request/wake bytes and actual observer module are immutable. Preserve
the mode-specific stager records/diffs as original-stage evidence. Do not edit
the stager, templates, authorities, production checkout, release metadata or
launcher. Independent evidence/review ownership remains separate.

## Repair 1: generic fallible compatibility

Remove only `Default` from the wrapper's derive list and implement explicitly:

```rust
impl<T> Default for Vec<T> {
    fn default() -> Self { Self(std::vec::Vec::new()) }
}
```

There must be no `T: Default` bound, no workaround derive on `AlignedBacking`,
and no replacement of kernel callers with std calls. Retain the exact APIs
`with_capacity(usize, ()) -> Result<Self, ()>` and
`push(&mut self, T, ()) -> Result<(), ()>`, actual `try_reserve_exact` /
`try_reserve` error propagation, `Deref`/`DerefMut`, and owned/shared/mutable
iteration. Preserve both mailbox two-argument allocation forms and every
existing `map_err(|_| -12)?`. `mem::take` of either Box queue must consequently
be source-feasible without adding a trait bound to the element.

## Repair 2: actual observer records and separate fixture counters

Replace the runner's discarded `format_args!` logging with a mode-local
test-only capture sink. The `kernel::pr_info!` macro forwards its actual
`format_args!` once to that sink, which renders and retains the supplied log
bytes in ordinary host memory. It must not manufacture a counter line or
rewrite fields. The sink's lock is independent of the fixture ledger; do not
hold either lock when invoking the observer, and do not log recursively.
No file/process/network IO is needed. No edit to `stability_observer.rs` is
permitted.

For each required snapshot call the existing `observer::begin` with the real
selected key, retain its returned sequence, and call `observer::end(sequence,
true)` after collecting the complete test-scope scalar metadata. Assert its
return is true. Read the exact new captured interval and require precisely
one `STABILITY_OWNER_COUNTERS` and one matching `STABILITY_OWNER_END`, with
version1, matching sequence, `selected_ledger_serial=Some(1)`,
`complete=true`, `counters_valid=true`, and `result=COMPLETE_SNAPSHOT`.
Parse the actual fields with strict key uniqueness, required-field and type
checks; absent/malformed/duplicate/stale lines fail. Snapshot sequence changes
are expected and are excluded from behavioral no-delta comparisons. A begin/end
record is a fixture observer sample, not a native full-domain snapshot claim.

Copy into a separate `ObserverCounters` value exactly the emitted
`address_calls`, `payload_calls`, `payload_bytes`, `release_calls`, `released`,
`after_release_calls`, and `duplicate_release`. Never increment these in the
fixture, subtract an assumed construction call, infer them from events, or
populate them with expectations. Calls to `observer::address(claim)` and
`observer::release(claim)` remain at the actual adapter operations only.
`observer::selected()` must equal the real selection at every sample.

Fixture snapshots separately contain actual address/status/send/release,
deferred-insertion, finished/unfinished-drop, quarantine-insertion and
deallocation totals; both current queue lengths; fixture live-owner and
released flags; actual prohibited-address/duplicate-release attempt counters;
immutable construction metadata; and the complete event vector. Increment
prohibited-attempt counters in the detecting branch before rejecting the
operation, never return or dereference a released span. An always-zero field
with no observing branch is not evidence. No row introduces an extra address
or release call just to sample these counters.

Construction's address call precedes selection, so fixture/observer address
totals are 1/0 there. Preparation changes them to 2/1. Row03 stays 2/1;
row12 publication changes them to 3/2. Payload calls/bytes and observer
after-release/duplicate counters stay zero throughout both rows. Row03's
observer release/released values stay 0/false; row12's change from 0/false to
1/true on actual release and remain so through destruction and drain.

Preserve packet48's 56-byte aligned allocation, offset8/length40 checked span,
physical `0x1000..0x1028`, exact Claim and alias rejection. Validate immutable
geometry before admission and immediately before `return_value`. After status
publication, snapshots may copy already captured scalar metadata but may not
query backing/span/address, inspect a response, read a byte through a pointer,
or call `address`. The unique correction42 hook records `StatusStore` only,
after the actual Release store and before the consuming release.

## Repair 3: destruction precedes deallocation evidence

Keep sole-Box transfers into the deferred/quarantine queues under the ledger
mutex, and retain the driver `Arc<Ledger>` through the final snapshot. A drain
must detach the entire queue using `mem::take` inside a lexical lock scope,
then leave that scope. For each detached Box use this order:

```rust
for backing in batch {
    drop(backing); // actual Box destruction, with no ledger guard held
    let mut state = ledger.state.lock().unwrap();
    state.deallocations += 1;
    // Append exactly one Deallocation event here.
}
```

The lexical loop tail is not a substitute for the explicit `drop(backing)`:
attempt48 logged the event first. Alternatively record the detached count,
explicitly drop the entire batch outside the lock, then append exactly that
many events under a new guard. Never forget/leak/retain a Box while claiming
deallocation. Drops/drains inspect no backing bytes. Keep insertion totals
distinct from queue lengths so post-drain emptiness is observable.

## Repair 4: complete real-state assertion matrix

Use the unchanged packet29 request and real admitted chain. No fabricated
Request/Selection/Completion/worker/phase state is allowed. Preserve the narrow
pristine-arm CAS and its checks; no later direct scalar store/reset is allowed.
Each row/mode still requires its own fresh process under future execution
authority, since token, observer and phase state have no reset contract.

Use existing `Mailbox::verification_mailbox` with fresh `Rows<Call,CALLS>` and
`Rows<Worker,WORKERS>` for copied metadata. Require both `complete()` values,
exact row counts and unique delivery/worker matches; no truncated or duplicate
row can prove presence. This existing method reports both `call.response` and
completion ownership before and after preparation, so no pre-return call to
attempt48's completion-only accessor is needed. Remove that redundant test
accessor or retain it only as an additional post-return check. Never alter the
real phase query's `(true,true)` condition to accommodate wake-none.

Immediately before return, assert one call, one matching worker, response=true,
completion=false, completion_response=false, completion_wake=false, exact
Claim, worker `(handle,71)`, serial/delivery match, phase `delivered`, and
unchanged original request identity. Selection equality covers os/generation,
application42, PID70, CPU0, requester70, worker/delivery, ledger index0/serial1,
response/end and payload=None through the Claim. Assert no second live owner.

Call pristine arm, verify geometry, then actual
`return_value(worker,serial,0,16,|_| Ok(()))`, requiring `Ok(())`. Before
recording `PreparationBaseline`, assert stage2, accepted_sequence0, invalid0,
release_commits0 and timer=None. Resample real mailbox metadata: response=false,
completion=true, completion_response=true, completion_wake=false, same Claim,
same worker/delivery/request, phase `returning`, `publication_since=None`.
Assert the actual phase query is `Err(-71)` and invalid remains0. Only then
record the baseline; assert fixture/observer addresses 2/1, live fixture owner,
all other fixture totals/queue lengths zero, observer release0/released=false,
and events exactly `[Construction, Address, Address, PreparationBaseline]`.
Retain a copied baseline owner/delivery/publication record for comparisons.

Both publish closures must keep and check the supplied packet parameter,
record a real `Send` only if invoked, and return the original success result.
Require length128 and exact wake bytes: an otherwise-zero array with LE i32
`0x14` at `[8,12)` and requester70 at `[24,28)`, as defined by the unchanged
`Request::wake`. Do not replace the closure parameter with `_`, fabricate a
send event, or invoke the callback from the test. Both rows require zero
invocations, so these packet assertions are retained checks, not claimed
executed wake-send coverage.

Row03 sequence:

1. Actual `publish(0, callback)` is exactly `Err(-11)`. Repeat all retained
   completion/response/Claim/worker/delivery/publication comparisons to baseline.
   Require stage2/accepted0/commits0/invalid0, fixture live owner, 2/1 address
   totals, and zero deltas for every other fixture and observer counter/flag,
   queue and event. Repeat these assertions immediately before close.
2. Actual `close_worker(worker)` is exactly `Err(-71)`; mailbox quarantine is
   true, invalid is exactly -125. Before destroying the mailbox, the retained
   completion and its Claim/delivery/worker remain equal to baseline, with no
   fixture drop/release/queue/event delta. Stage2/accepted0/commits0 remain.
   Do not demand whole mailbox equality: quarantine and the real publish cursor
   are allowed to change. The cancellation guard must not release the owner.
3. `drop(mailbox)` precedes any drain. Snapshot scalar ledger/phase/observer
   data only: fixture live-owner=false, released=false, unfinished-drop1,
   quarantine-insertion1, quarantine-length1, deallocation0. All other totals
   remain at baseline, deferred-length0, observer 1/0/false address/release/
   released, and stage2/accepted0/commits0/invalid-125. The metadata Claim remains
   equal to the captured original; do not query a destroyed mailbox.
4. Drain quarantine, then require both queues empty, deallocation1,
   unfinished-drop1/quarantine-insertion1, no live fixture owner, and every
   other fixture total/flag, observer counter, Claim and phase value unchanged
   from step3. Exact final events are baseline followed by
   `[UnfinishedDrop, QuarantineInsertion, Deallocation]`.

Row12 sequence:

1. From the complete common baseline take the real permit, choose
   `timer=now_ns()/1_000_000_000+8`, then assert successful `begin_emitting(timer)`,
   stage4; `commit_held(2,timer)`, stage5/accepted2; `claim_release()`;
   `commit_release(timer)`, stage3/accepted2/commits1/invalid0. Assert
   `before_selected_send()` is Released, not an invented enum value. Timer
   remains the exact chosen timer. No phase writes occur outside real methods.
2. Actual `publish(0, callback)` is exactly `Ok(true)`. Assert actual absent
   query with `present=false, publication_since=None`, no matching call in
   complete mailbox metadata, and no retained response/completion owner.
   Fixture totals are address3/status1/send0/release1/deferred-insertion1/
   finished-drop1/unfinished-drop0/quarantine-insertion0/deallocation0;
   deferred-length1/quarantine-length0, live-owner=false/released=true.
   Observer totals are address2/release1/released=true, payload0/bytes0/
   after-release0/duplicate0. Fixture prohibited-attempt counters remain0.
   Stage3/accepted2/commits1/invalid0 and timer are unchanged. Events are exactly
   baseline followed by `[Address, StatusStore, Release, DeferredInsertion,
   FinishedDrop]`.
3. Explicitly destroy the mailbox before draining deferred storage. Snapshot
   again and assert equality of every fixture total, flag, queue length,
   metadata value and event and every observer counter and phase value from
   step2. This is the required mailbox-destruction no-delta check.
4. Drain deferred. Assert both queues empty and exactly deallocation1; all
   insertion/drop/status/send/address/release totals and flags, metadata Claim,
   observer counters, stage/accepted/commit/invalid/timer values remain as in
   step3. Exact final events equal step2's vector plus `[Deallocation]`.

Full tuple/struct comparisons are acceptable if every named field participates
and the one permitted deallocation/queue delta is explicitly constructed from
the prior actual snapshot. Assertions only on `.last()` or a small subset of
counters are insufficient. Never compare snapshots by reading freed storage.

## Static checks, first failure and unreleased execution

The design/implementation checks are read-only source/hash/file inspections,
archive byte comparisons, structural checks, in-memory inverse/erasure checks,
byte-reading `ast.parse` where needed, no-bytecode audits and `git diff --check`.
Every Python inspection uses `-B` and imports no repository/candidate module.
Only after independent packet release are the two source-only stager commands
above excepted. No candidate/helper execution, compiler, test runner, binary,
container, guest, root/sudo or network command is authorized by this packet.

Before handoff reject any inherited pin/member/path/link drift; non-erased
source change; Vec element-Default bound; altered fallible caller; synthesized
observer counter; missing strict live end/log capture; post-store pointer/span
read; misplaced hook; lock-held or premature deallocation event; incomplete
mailbox metadata; premature baseline; omitted phase/owner/commit invariant;
wrong wake/query; discarded packet check; row03 drain before destruction;
missing row12 destruction no-delta; nonempty final queues; or incomplete final
counter/event comparison. Check both modes independently against this matrix,
not against each other's candidate output. These checks establish source
structure only; do not label them executable regressions.

At the first failure, stop the affected attempt, create only correction31's
`phase-i-failure.txt` with its six exact LF-terminated fields, preserve the
partial root and return to the dispatcher for archival. No in-place repair,
retry, cleanup or Phase-II start follows. The dispatcher continues independent
ready work. On static success bind all candidate bytes in the unchanged handoff
schema and obtain an independent handoff review before considering any next
layer. Compile feasibility, log parsing under real Rust execution, actual
drop/ownership behavior and production/native/guest acceptance remain unproved.
