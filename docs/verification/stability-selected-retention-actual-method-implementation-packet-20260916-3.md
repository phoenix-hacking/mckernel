# M01-B actual-method implementation packet (correction 3)

Status: worker-ready source packet; implementation is not released. This packet
addresses review attempt 3 (`FAIL_ALLOWLIST_PACKET`) and the blocker
`BLOCKED_BY_REVIEWED_WRITE_BOUNDARY`. It authorizes only a fresh, generated,
test-only adapter in the two exact mode trees below. It gives no compile,
runtime, guest, application, production-gate, or acceptance credit.

## Authenticated inputs and generation

Run the existing stager once per mode, with fresh, disjoint output paths. Do
not use the held tree, a repository fixture, or a released production tree as a
candidate. The pre-generation source is the 51-member flat tree
`/home/holden/mckernel-work/scratch/stability-published-held-source-20260915-recoverable-backpressure-3/held/source`
for mode 3 and
`/home/holden/mckernel-work/scratch/stability-selected-retention-authority-20260915-1/mode2`
for mode 2. The manifest binds every member's pre-generation size/hash; the
three changed members' hashes are:

```
application_syscall.rs       83c76e277f759e920a91f4fd3bb601268aee39082acbe3f4cd732ec3c58feb92
smp_application_syscall.rs   4f7611fca376aacddf80be2dacef0928f5e6c8506c692f0154680f93dfeaa5d4
stability_phase.rs           041b7e983132745e64aed003e745600f7e8573ed19a8ead57a4f4fecda888131
```

Mode 3 pre-generation hashes are:

```
application_syscall.rs       83c76e277f759e920a91f4fd3bb601268aee39082acbe3f4cd732ec3c58feb92
smp_application_syscall.rs   b18b2356189a42b9083e09b477bba4b81011a9c3c42aafb9564daebb0f813ee2
stability_phase.rs           d81bb72e67ae0db6a69c6dfed6c9db96c33ec33ffc9aeef015970b431884d4ea
```

The stager is `scripts/tests/prepare_stability_selected_retention.py`, SHA256
`c2b8b256bc4ee0997fed3c210f9d6aef1878a6dc507d3fd96fe66ea011b843b0`, and the source manifest is
`scripts/tests/fixtures/stability-selected-retention-v1/source-manifests.json`,
SHA256 `d9d439bff0a90bddcc3920f36b8fac81d6e1515fd83f035e18a34464cc8498d0`.
The computed stager value is
`c2b8b256bc4ee0997fed3c210f9d6aef1878a6dc507d3fd96fe66ea011b843b0`.
The mode-2 authority record is SHA256
`3bded4f7bfc206b4e64b03a58243d0e3a7783a5a493dd4095be5916a07e7ed48`; the
mode-3 base and held records are respectively
`11de2af873b88fe6afb19749195294b10b41879b6f0e99e97b95065cf25de968` and
`a5cee2ec4397bd37f1abe75a313f6de6a96fbd8983cc49c6f1e9437681fe435d`.

## Exact candidate outputs and expanded write allowlist

The worker may create only these named paths (plus files beneath neither
directory nor glob):

```
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode2/source/application_syscall.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode2/source/smp_application_syscall.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode2/source/stability_phase.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode2/runner.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode2/result-parser.py
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode2/owned-memory-ledger.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode2/allocator-shim.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode2/manifest.json
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode3/source/application_syscall.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode3/source/smp_application_syscall.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode3/source/stability_phase.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode3/runner.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode3/result-parser.py
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode3/owned-memory-ledger.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode3/allocator-shim.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode3/clock-shim.rs
/home/holden/mckernel-work/scratch/m01b-actual-method-packet-20260916-3/mode3/manifest.json
```

No other path, directory, glob, generated member, production source, or
fixture may be written. `std` allocation is confined to the host runner and
ledger. The adapter is module-local `#[cfg(test)]`; every helper, setter,
clock override, ledger hook, and test constructor must vanish under
`#[cfg(not(test))]`.

## Required production anchors and adapter boundary

In each generated candidate preserve the stager's exact three transformations
and add only the test adapter:

* `application_syscall.rs`: `Worker` at lines 160/`Worker::new` 166;
  `unsafe trait ResponseMemory` at 316 with
  `physical(&self)->u64`, `address(&mut self)->*mut u8`, consuming
  `unsafe release(self)`, and `verification_owner()->Option<Claim>`;
  `Response::from_memory` 385, `Response::prepare` 402, `Completion` 437,
  `Completion::publish` 446. Put the fault hook immediately before the
  second `state.compare_exchange(2, 1, ...)` in `verification_prepare_retained`;
  put the status ledger event immediately after the final status store in
  `Completion::publish`, without dereferencing released memory.
* `smp_application_syscall.rs`: `Mailbox` 35, `Mailbox::new` 44,
  `open_worker(&mut self, tid: i32)->Result<u64>` 61, `admit` (124),
  `reserve` (212), `copied` (262), `return_value` (465), `publish` 563,
  `cancel_call` 660 and the unique send overlay at 980. The module-local test
  API may expose only `test_insert(Call)`, `test_cancel_pending()`, and
  `test_publish(cpu, FnOnce(...))`; it must construct through
  `Mailbox::new -> open_worker -> real admission/selection -> actual Call`
  containing `Response` or `Completion`. `Worker` remains nongeneric.
* `stability_phase.rs`: module-local test setter only, taking exactly
  `(stage: u64, commits: u64, invalid: i32)`. Do not substitute mode trees.

The adapter must call unchanged `admit`, `reserve(handle)`, `copied(handle,
serial, true)`, `verification_read16`, observer selection,
`verification_phase_completion`, and `return_value`; no invented production
constructor or broad integration is permitted.

## Memory, clock, and cancellation invariants

`TestResponseMemory::new(NonNull<u8>, u64, Arc<Ledger>)->Self` owns a guarded,
exclusive backing whose response span is exactly 40 bytes, starts at an
address divisible by 8, and remains valid through final status store and
consuming release. `physical()` equals the retained `Claim.response.physical`,
`end - physical == 40`, serial/index/os/generation are identical, and no alias
is admitted. The external ledger quarantines unfinished Drop; `release(self)`
removes its entry exactly once without reading response bytes. Ledger events
atomically record constructor baseline, send attempt/success, address calls,
status store, release, drop, quarantine, and invalid latch. Baseline counters
are taken after construction/preparation (both already call `address`);
hold assertions compare deltas from that baseline.

Mode 3's `clock-shim.rs` supplies runner-owned atomic `ktime_get()->i64`.
At selected wake publication, return `-11`, record one fault attempt and zero
real send callbacks; retain at 1,999,999,999 ns, then at exactly 2,000,000,000
ns recover, publish once, and release once. Precommit cancel returns `-71`,
latches first invalid `-125`, quarantines/retains ownership. Committed cancel
does not roll back the completion; it remains recoverable. Mode 2 wake Some
performs one matching notification failure `-5` and retains the call; wake
None is separate and follows its selected notification contract.

## Complete M01-B rows

Every row runs in a fresh process (observer and fault statics are one-shot),
with a fresh ledger/backing and baseline after preparation.

| ID | setup / expected result and events |
|---|---|
| M01-B-01 | stage 0: `-71`; no send/address/status/release/drop delta; owner retained. |
| M01-B-02 | stage 1: same no-op hold and retained owner. |
| M01-B-03 | stage 2: same no-op hold and retained owner. |
| M01-B-04 | stage 4: same no-op hold and retained owner. |
| M01-B-05 | stage 5: same no-op hold and retained owner. |
| M01-B-06 | stage 6: same no-op hold and retained owner. |
| M01-B-07 | invalid hold: `-71`; zero send/address/status/release/drop; owner retained. |
| M01-B-08 | stage 3, commits 0, wake None: hold identically; owner retained. |
| M01-B-09 | stage 3, commits 0, wake Some: identical hold; owner retained. |
| M01-B-10 | stage 3, commits 2, wake None: identical hold; owner retained. |
| M01-B-11 | stage 3, commits 2, wake Some: identical hold; owner retained. |
| M01-B-12 | stage 3, commits 1, wake None: unchanged no-send publication; one status store and one release, no send callback. |
| M01-B-13 | stage 3, commits 1, wake Some, mode 2: one notification attempt fails `-5`; no release; owner retained. |
| M01-B-14 | stage 3, commits 1, wake Some, mode 3 at t: one fault attempt, `-11`, zero real send; owner retained. |
| M01-B-15 | M01-B-14 at t+1,999,999,999: still held, no release. |
| M01-B-16 | M01-B-14 at t+2,000,000,000: one recovery send/publication, status store, one release; no second drop. |
| M01-B-17 | changed owner: unchanged production result; selection/claim mismatch is `-71`, no fabricated release. |
| M01-B-18 | selection false: unchanged non-selected behavior; no retention credit. |
| M01-B-19 | pre-release `cancel_pending`: real guard returns `-71`, first invalid `-125`, owner quarantined/retained. |
| M01-B-20 | post-commit cancellation: unchanged released path; completion remains recoverable, no relatch/rollback. |
| M01-B-21 | negative servicing TID: `-22`; no release; retained owner. |
| M01-B-22 | initial nonzero completed status: `-71`; no release; retained owner. |
| M01-B-23 | invalid wake/state: `-71`; no release; retained owner. |
| M01-B-24 | failed second compare-exchange after prefix writes: `-71`; prefix writes preserved, no release, owner retained. |
| M01-B-25 | pre-start cancellation with Response: real cancellation path and ownership quarantine; no byte read after release. |
| M01-B-26 | in-flight cancellation around Completion construction: deterministic guard result, no double completion/release. |
| M01-B-27 | post-publication cancellation: committed release remains final; no rollback or second release. |

For every row record return value, event sequence, owner identity, response
status/state words, send callback count, address delta, release/drop counts,
quarantine and first-invalid value. Expected matrix errors are `-22` bad tid,
`-71` invalid state/second CAS, mode-2 `-5`, mode-3 selected wake `-11`,
mode-3 precommit cancel `-71`, and first-invalid `-125`.

## Evidence, checks, and stop rules

`manifest.json` must bind every generated member's path, mode, size and SHA256,
all 51 pre-generation members, authority records, stager hash, adapter-only
diffs, and inverse-restoration hashes. `result-parser.py` must reject missing,
duplicate, reordered, extra, or unknown row IDs and unexpected events. Record
independent pre/post manifests, exact adapter-only diffs, and byte-identical
inverse restoration before any source-only check.

Allowed checks are SHA256/member-manifest comparison, anchor and duplicate or
missing-hook checks, `git diff --check` on generated patches, the retained
Python structural envelope suite, and independent source review of adapter and
runner. No compilation, runtime, root/sudo, network, guest, heavy build, or
acceptance check is allowed in this packet.

Hard stop and escalate immediately on any hash/member drift, non-unique anchor,
unexpected file, failed inverse restoration, production-code change outside
`cfg(test)`, alias/claim ambiguity, private-call API invention, a mismatched
mode tree, any unexpected check failure, or a second failed attempt. Preserve
the command, environment, exact failure output, and evidence path/hash; do not
retry beyond one bounded correction.

## Correction 4: executable boundary and complete stager schema

The packet hash before this correction was
`6727a0405534b3d95bc5fd8dc7fa8803c05c6cecedd0ea19f9d1a4f6d0288d08`.
For each mode, the stager creates exactly directories `source/`, `originals/`,
`inputs/`, `diffs/`, and files `helper.py`, `record.json`, 51
`source/<member>.rs`, 51 `originals/<member>.rs`, 51
`diffs/<member>.rs.diff`, plus six inputs: `response-prepare.rs`,
`return-prepare.rs`, `cancel-guard.rs`, `mailbox-retention.append.rs`,
`phase-retention.append.rs`, and `original-send-gate.rs`. This is 160 files
plus four directories per mode. `record.json` binds every identity and says
`PREPARED_NOT_COMPILED_NOT_EXECUTED`. The adapter allowlist adds, per mode,
the three candidate source files, `runner.rs`, `result-parser.py`,
`owned-memory-ledger.rs`, `allocator-shim.rs`, and `manifest.json`; mode 3
also adds `clock-shim.rs` (8 named files for mode 2, 9 for mode 3). No glob or
directory is write authority.

### Exact gated helpers and setup

In `application_syscall.rs`, add only under `#[cfg(test)]`:
`pub(crate) fn verification_prepare_retained(&mut self, servicing_tid: i32,
value: i64) -> Result<Completion<M>, i32>` (called only by the test-gated
`Response::prepare` replacement); `fn test_second_cas_hook()` immediately
before the second `compare_exchange(2, 1, ...)`; and
`fn test_record_status_store(physical: u64)` immediately after the final
status store, without reading memory. Negative-TID rows call
`verification_prepare_retained` directly. In `smp_application_syscall.rs`
add `pub(crate) fn test_insert_admitted(&mut self, request: Request, memory: M,
worker_tid: i32) -> Result<(u64,u64)>`, calling `Mailbox::new`,
`open_worker`, `admit`, then normal `reserve`/`copied`; it stages the actual
`Call` only after normal prepare. Add `pub(crate) fn test_cancel_pending(&mut
self) -> Result` and `pub(crate) fn test_publish_with(&mut self, cpu: i32,
send: impl FnOnce(&[u8; 128]) -> Result) -> Result<bool>`, forwarding to the
unchanged private methods. The sole publish call site is the existing closure
at line 584 calling `stability_fault_send(...)`. In `stability_phase.rs`, add
only `pub(crate) fn test_set_state(stage: u64, commits: u64, invalid: i32)`
under `cfg(test)`, storing the existing atomics. No `cfg(not(test))` code may
reference a test helper.

`allocator-shim.rs` host `std` allocates a guarded 48-byte region; only the
candidate `ResponseMemory` implementation calls `address`, `physical`, and
consuming `release`. The ledger owns deallocation: capability Drop never
deallocates backing; unfinished Drop quarantines the claim; release marks once
and queues backing for post-publication deallocation. Status is observed via
an atomic copied ledger event after publication, never released memory. Mode 2
uses its shim as the monotonic clock provider; mode 3 uses the runner-owned
atomic `ktime_get()->i64` clock shim.

### Row execution corrections

Rows M01-B-01..-11 and -17..-19 are explicit hold calls asserting publish
result `-11`, zero real sends, no status/release/drop, and first-invalid `0`
except actual invalid-state/owner cases (`-71`). Inputs are stages
`0,1,2,4,5,6,invalid`, then `(3,0,None)`, `(3,0,Some)`, `(3,2,None)`,
`(3,2,Some)`; changed-owner and false-selection rows run separately in each
mode. `verification_phase_completion` requires wake `Some`; wake `None` uses
ordinary release. Rows -15/-16 recreate the initial selected-wake attempt in a
fresh process before advancing time: -15 at exactly `t+1,999,999,999` remains
`-11`; -16 at `t+2,000,000,000` publishes/releases once. Mode 2 wake `Some`
consumes, status-stores, releases, then matching-notify fails `-5`; it does
not retain or rollback. Wake `None` has no published-fault attempt and
releases normally.

Changed-owner assertions split by method: `verification_phase_completion`
rejects the copied identity with `-71`; retention-gate/fault-send selection
bypass separately exercises ordinary release with a valid physical/backing
claim and never mutates physical identity. Rows -20, -25, -26, -27 execute
`test_insert_admitted`, selection, `return_value`, then cancellation before
commit, around completion construction, or after `test_publish_with` commit.
Expect precommit `-71`, first-invalid `-125`, quarantine and retention;
deterministic single completion/release around construction; and unchanged
post-publication no-rollback. Row -25 records distinct pre- and
post-preparation baselines.

The previously terse rows have these exact invocations (run once in mode 2 and
once in mode 3 unless marked mode-specific). M01-B-18 uses a valid request
`target=worker_tid`, `number=0`, `arguments[0]=0`, `arguments[2]=16`, and a
valid 40-byte claim, then calls `test_insert_admitted(request, memory,
worker_tid)`, `verification_read16(Some(other_pid), application)`, and
`test_publish_with(cpu, |_| Ok(()))`; return is `Ok(false)` from selection,
publish is `-11`, first-invalid is 0, and all ownership counters remain held.
M01-B-20 uses the same arguments, calls `return_value(handle, serial, cpu as
i64, value, |_| Ok(()))`
to obtain `Completion`, calls `test_set_state(3,1,0)`, then
`test_publish_with(cpu, |_| Ok(()))` (one status store/release), followed by
`test_cancel_pending()`; cancellation is the unchanged post-commit result,
with no second release or invalid latch. M01-B-25 calls
`test_insert_admitted(request, memory, worker_tid)`, captures the
pre-preparation ledger baseline, invokes `test_cancel_pending()` while the
call still owns `Response`, and expects `-71`, first-invalid `-125`,
quarantine, zero release, and retained backing; it then captures the distinct
post-preparation baseline only for comparison and must not retry publication.
M01-B-26 calls `test_insert_admitted`, starts `return_value(handle, serial,
cpu as i64, value, |_| Ok(()))` while the mailbox
lock is held, invokes `test_cancel_pending` at the construction boundary, and
expects one deterministic guard result, one completion at most, and no double
release/drop. M01-B-27 calls `test_insert_admitted`, `return_value(handle,
serial, cpu as i64, value, |_| Ok(()))`,
`test_set_state(3,1,0)`, `test_publish_with(cpu, |_| Ok(()))`, then
`test_cancel_pending`; expected events are status-store, release, ordinary
completion, then unchanged cancellation with no rollback, relatch, or second
release. Every invocation records args, return, callback count, ledger events,
and owner identity.

`manifest.json` pins all five templates and `original-send-gate.rs` using the
source-map hashes, plus pre/post manifests and `manifest.adapter.diff` under
the fresh packet root. Check adapter-to-staged byte restoration, then
stager-to-authenticated inverse restoration of all 51 originals. Preserve
both evidence manifests and hashes. No compile/runtime/acceptance credit.
