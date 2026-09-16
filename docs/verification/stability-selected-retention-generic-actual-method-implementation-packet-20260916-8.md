# M01-B generic actual-method prerequisite packet (attempt 8)

Status: **PREREQUISITE ONLY; NOT AN IMPLEMENTATION RELEASE.** This is the
generic `ResponseMemory` actual-method runner defined by hard reviews 6 and 7.
It neither substitutes for nor tests native `SyscallResponse`/`Memory` ownership.
Native `SyscallResponse`, `BootStorage`, OS-generation, extent/lease, and private
response-ledger acceptance remain blocked pending a separately selected and
independently reviewed production-owned backing architecture. No compiler, root,
native, guest, runtime, application, production-gate, or acceptance activity is
authorized here.

## Pins, inputs, and boundaries

The worker shall authenticate before staging:

| input | SHA-256 |
| --- | --- |
| source map `docs/verification/stability-selected-retention-actual-method-source-map-20260916-1.json` | `a09978ce5d6bd8f3cdb43bbeba25af7ba287b5d6143d72e039b781df8abd4131` |
| attempt-6 consolidation record | `0453a3908c846ea2ab20455e4d44a808cafb2b84452f3bb608ac4124dbabfc98` |
| attempt-7 native architecture review | `0b997e2c65f443bf28a99e7e9494eb0c224bbad77f1b3a26eaa74c4894e14f4e` |
| stager `scripts/tests/prepare_stability_selected_retention.py` | `c2b8b256bc4ee0997fed3c210f9d6aef1878a6dc507d3fd96fe66ea011b843b0` |
| source manifest `scripts/tests/fixtures/stability-selected-retention-v1/source-manifests.json` | `d9d439bff0a90bddcc3920f36b8fac81d6e1515fd83f035e18a34464cc8498d0` |
| original-send-gate template | `dac2855ca19e587c33f7bd5a36c30c9090a6ea846f6dca90081abf0543228267` |
| response-prepare template | `38f5202ca358fc89cf440e4633cf6d98aa5549d550740da3acadd1fd040d8421` |
| return-prepare template | `3ea01848a34cbefd202de4947d4598b10ad55b298b170a60158b43ded840ac7c` |
| cancel-guard template | `39c75e46564da98a5d06d709bf31e309b46ba6bf2166a381d6f2e5354cdeb3e6` |
| mailbox-retention template | `b47f7f78f1b6d385a99de811eec46e7888f76219838fbeee1aff463d32d0a69a` |
| phase-retention template | `cf67a5c2b944c312e6467208ef3c87519be284a896a46dc23d598f7d3fbf5089` |

Mode 2 source is the manifest-bound postpublish-notify authority record
`3bded4f7bfc206b4e64b03a58243d0e3a7783a5a493dd4095be5916a07e7ed48`.
Mode 3 source is `/home/holden/mckernel-work/scratch/stability-published-held-source-20260915-recoverable-backpressure-3/held/source`, bound by base/held records
`11de2af873b88fe6afb19749195294b10b41879b6f0e99e97b95065cf25de968` and
`a5cee2ec4397bd37f1abe75a313f6de6a96fbd8983cc49c6f1e9437681fe435d`.
Authenticate all 102 source members (51 per mode) against the manifest; preserve
mode-specific `smp_application_syscall.rs` and `stability_phase.rs` without
cross-mode substitution.

Fresh root: `/home/holden/mckernel-work/scratch/m01b-generic-actual-method-packet-20260916-8`.
Only its parent and exactly these newly-created directories are allowed:
`mode2`, `mode2/source`, `mode2/originals`, `mode2/inputs`, `mode2/diffs`, and
the corresponding five mode3 directories. Per mode the stager alone may create
exactly 161 files: `helper.py`, `record.json`; six named `inputs/` files
(`response-prepare.rs`, `return-prepare.rs`, `cancel-guard.rs`,
`mailbox-retention.append.rs`, `phase-retention.append.rs`,
`original-send-gate.rs`); and, for every one of the manifest's exact 51 names,
the three explicitly named paths `source/<name>`, `originals/<name>`, and
`diffs/<name>.diff`. This is an exhaustive file allowlist, not a directory/glob
write grant. The same exhaustive allowlist also includes, per mode, exactly
these evidence files: `stager-pre.json`, `adapter-pre.json`, `adapter.diff`,
`adapter-inverse.json`, `stager-inverse.json`, `source-audit.txt`,
`runner-audit.txt`, `result.json`, and `failure.txt`. The fresh root, both mode
roots, all eight named subdirectories, all 161 stager files, these nine evidence
files, and the adapter files below are the complete creation allowlist; no
other path may be created or modified. Stager output must say
`PREPARED_NOT_COMPILED_NOT_EXECUTED`.

After staging, source edits are restricted to these six generated candidates
only: `mode{2,3}/source/application_syscall.rs`,
`mode{2,3}/source/smp_application_syscall.rs`, and
`mode{2,3}/source/stability_phase.rs`. The only additional individually named
files are `mode{2,3}/runner.rs`, `result-parser.py`,
`owned-memory-ledger.rs`, `allocator-shim.rs`, `manifest.json`, and
`mode3/clock-shim.rs`; no other creation or modification is allowed.

## Actual generic method runner

Preserve both existing consuming prepare methods and their exact signatures,
including `Result<Completion<M>, (Self, i32)>` selected-error restoration. Do
not replace `Response::prepare`, duplicate it, invent a `Call` constructor, or
change production control flow. All definitions **and every inserted call** are
module-local `#[cfg(test)]` and erased under `cfg(not(test))`.

The runner constructs only through the actual chain
`Mailbox::new -> open_worker -> admit -> reserve(handle) -> copied(handle, serial, true)`;
`admit` remains the only private `Call` construction. It then uses unchanged
`verification_read16`, real observer selection, `return_value`,
`verification_phase_completion`, and the unique production `publish` path.
The permitted gated shims are runner-facing only: an admitted-chain driver,
`test_cancel_pending`, a publish callback observer, and
`test_set_state(stage, commits, invalid)`. They do not expose generic `Worker`
or private production construction.

`TestResponseMemory` is generic-test backing, not native backing: a guarded,
8-byte aligned 56-byte allocation contains exactly a 40-byte response span with
8-byte guards. It has exclusive physical/claim identity, rejects aliases, and
stays allocated through final status store and consuming `release(self)`. Its
atomic ledger records construction/preparation baseline, send attempt/success,
address, status-store, release, finished Drop, unfinished Drop/quarantine, and
first-invalid. Release removes exactly once and defers deallocation; no callback,
ledger, parser, or Drop reads response bytes after release. Quarantine retains
unfinished backing for evidence. Hold comparisons begin after successful
construction/preparation, since those methods may call `address`.

Immediately before the real second `state.compare_exchange(2, 1, ...)`, the
gated one-shot hook receives only `&AtomicU64`, mutates that live atomic once to
force the mismatch, retains no reference, and leaves the existing prefix writes
observable. The status event is emitted after the final real status store and
never dereferences released memory. Both modes provide a positive runner-owned
atomic `ktime_get() -> i64`; mode 2 supplies it for the selected-send path,
and mode 3 additionally uses it for the exact two-second recovery deadline.

The negative-TID case is the sole exception to the admitted mailbox runner: the
test-only, module-local fixture constructs one exclusive `TestResponseMemory`,
then constructs exactly one `Response::from_memory(&request, memory)` directly
and extracts that one consuming `Response<M>` into
`verification_prepare_retained(-1, value)`.  It neither inserts that Response
in a `Call` nor retains a second response owner; the request, physical address,
claim, and backing identity must be the same source-proven direct-construction
values.  `Err((response, -22))` is moved to unfinished Drop/quarantine.  There
is **zero** `ResponseMemory::release`, its backing remains retained for the
failure record, and no invented Response release/extraction API is permitted.

## Exact row matrix and legal sequencing

Every row and every listed subcase is a fresh process.  Its mandatory prefix is:
fresh mailbox/backing/ledger/one-shot statics; `Mailbox::new`; `open_worker`;
real `admit`; `reserve(handle)`; `copied(handle, serial, true)`; real selection
and claim verification; install phase state **ARMED (1), commits 0, invalid 0**;
then call unchanged `return_value`.  Thus normal selected preparation is always
`return_value(...) == Ok(())`, and its real `stability_fault_accepted` changes
ARMED to ACCEPTED_PENDING (2), with `accepted_selected()` having result
`stage=2, invalid=0`.  Only after that successful preparation may the runner use
`test_set_state(stage, commits, invalid)` for the publication condition.  It
must record separately: preparation result; accepted transition/result; phase
query timing/result; `publish` result; cancellation result; first-invalid;
state/status words; callbacks; send/status/release/Drop/quarantine ledger
events.  A held-stage `Err(-11)` is from the publication send gate, never from
preparation.  Never cancel while a mutable mailbox borrow or owner lock is held.
Rows 21--24 are explicitly response-prepare negative fixtures: construct their
specified response state first, call the named prepare route, and record its
error/unfinished disposition; they do not claim the normal successful prefix.

Immediately after `return_value`, before the test state mutation, query
`verification_phase_completion(key)`: wake `None` yields `Err(-71)` (the real
completion has `(true,false)`), while wake `Some` yields
`Ok(CompletionStatus { present: true, publication_since: None })`.  After a
successful publish removes the call, the same query yields
`Ok(CompletionStatus { present: false, publication_since: None })`; it is not
the pre-publication wake-None error.

| ID | setup and exact expected result |
|---|---|
| M01-B-01 | After the mandatory successful ARMED preparation/query, set stage 0, commits 0, invalid 0; `publish` `Err(-11)`, first-invalid `-71`, retained, zero send/status/release. |
| M01-B-02 | After successful preparation/query, set stage 1, commits 0, invalid 0; `publish` `Err(-11)`, retained, zero send/status/release. |
| M01-B-03 | After successful preparation/query, set stage 2, commits 0, invalid 0; `publish` `Err(-11)`, invalid 0, retained. |
| M01-B-04 | After successful preparation/query, set stage 4, commits 0, invalid 0; `publish` `Err(-11)`, invalid 0, retained. |
| M01-B-05 | After successful preparation/query, set stage 5, commits 0, invalid 0; `publish` `Err(-11)`, invalid 0, retained. |
| M01-B-06 | After successful preparation/query, set stage 6, commits 0, invalid 0; `publish` `Err(-11)`, first-invalid `-71`, retained. |
| M01-B-07 | After successful preparation/query, set stage 255, commits 0, invalid 0; `publish` `Err(-11)`, first-invalid `-71`, retained. |
| M01-B-08 | After successful wake-None preparation and its pre-publication query `Err(-71)`, set stage 3, commits 0, invalid 0; `publish` `Err(-11)`, retained. |
| M01-B-09 | After successful wake-Some preparation and pre-publication query present/None, set stage 3, commits 0, invalid 0; `publish` `Err(-11)`, retained. |
| M01-B-10 | After successful wake-None preparation/query, set stage 3, commits 2, invalid 0; `publish` `Err(-11)`, retained. |
| M01-B-11 | After successful wake-Some preparation/query, set stage 3, commits 2, invalid 0; `publish` `Err(-11)`, retained. |
| M01-B-12 | After successful wake-None preparation/query, set stage 3, commits 1, invalid 0; `publish` `Ok(true)`, one status/release and zero send callbacks; post-removal phase query is absent. |
| M01-B-13 | Mode 2: after successful wake-Some preparation/query, set stage 3, commits 1, invalid 0; positive runner-owned `ktime_get`; `publish` `Ok(true)`, one real send/status/release and call removal. Then call exact `stability_fault_notify(os, generation, application, cpu, notify)` with matching selected fields: it returns `Err(-5)`, invokes `notify` zero times, and causes no rollback, second send, second release, or retained owner. |
| M01-B-14 | Mode 3 fresh process: perform the mandatory successful preparation/query, set stage 3, commits 1, invalid 0, and make the initial `publish` attempt at positive t. It returns `Err(-11)`, performs zero real sends/releases, and establishes `STABILITY_FAULT_SINCE=t`. |
| M01-B-15 | Mode 3 fresh process: first replay the complete row-14 initial attempt at positive t (including `STABILITY_FAULT_SINCE=t`), then retry the same retained completion at t+1,999,999,999 ns; `publish` remains `Err(-11)`, zero send/release. |
| M01-B-16 | Mode 3 fresh process: first replay the complete row-14 initial attempt at positive t (including `STABILITY_FAULT_SINCE=t`), then retry the same retained completion at t+2,000,000,000 ns; recovery `publish` `Ok(true)`, exactly one send/status/release and no second Drop/release. |
| M01-B-17 | Before accepted selection, change exactly one selected-key field in separate subcases—`pid`, `cpu`, `requester`, `delivery`, or `response`—while leaving os/generation/application/worker/ledger claim otherwise valid. `return_value` stays `Ok(())`, accepted state does not transition (stage remains 1); query/publish follow ordinary-unselected behavior, never fabricated selected mutation or release. |
| M01-B-18 | Fresh ordinary-unselected control with mismatched PID: observer selection `Ok(None)`; pre-RET `publish` `Ok(false)`; ordinary `return_value` `Ok(())`; its wake-None pre-publication phase query `Err(-71)`; ordinary `publish` `Ok(true)`, one status/release; post-removal query absent. |
| M01-B-19 | After mandatory selected ARMED preparation/query, set stage 2, commits 0, invalid 0 and cancel before publish; `test_cancel_pending` `Err(-71)`, first-invalid `-125`, quarantine/retained, zero release. |
| M01-B-20 | Fresh subcase A: after selected preparation/query set stage 3, commits 1, invalid 0, serialize cancel before publication; cancellation `Err(-71)`, first-invalid `-125`, quarantine/zero release. Fresh subcase B: same setup and mode-3 initial/recovery history where applicable, publish successfully, then retain the normal one-release conclusion. |
| M01-B-21 | The exclusive direct route above: `verification_prepare_retained(-1, value)` `Err((response, -22))`; returned Response enters unfinished Drop/quarantine, with zero release and retained backing. |
| M01-B-22 | Direct response-prepare negative: nonzero initial completed status; `verification_prepare_retained` `Err((response, -71))`, first-invalid `-71`; unfinished Drop/quarantine, retained, zero release. |
| M01-B-23 | Direct response-prepare negative: invalid wake/state; `verification_prepare_retained` `Err((response, -71))`, first-invalid `-71`; unfinished Drop/quarantine, retained, zero release. |
| M01-B-24 | Direct response-prepare negative: force the real second CAS failure; `verification_prepare_retained` `Err((response, -71))`, prefix writes preserved, first-invalid `-71`; unfinished Drop/quarantine, retained, zero release. |
| M01-B-25 | After admit/copy but before `return_value`, set phase stage 1, commits 0, invalid 0 and serialize cancel-before-RET; `return_value` `Err(-71)`, first-invalid `-125`, quarantine, zero release and no post-release read. |
| M01-B-26 | Separate fresh processes: (A) RET-before-precommit-cancel: successful selected preparation, then stage 2/commits 0/invalid 0, cancel `Err(-71)`; (B) cancel-before-RET: stage 1/commits 0/invalid 0, cancellation then `return_value` `Err(-71)`. Both quarantine, have zero release, no reentry, and at most one completion. |
| M01-B-27 | Fresh selected process: successful preparation/query, set stage 3, commits 1, invalid 0, then fully publish (`Ok(true)`; mode 3 first establishes `SINCE=t` and recovers only at t+2,000,000,000); one send/status/release and post-removal phase query absent. Then cancel; `test_cancel_pending` `Ok(())` because removal found no call, with no rollback, relatch, second release, or post-release read. |

## Evidence, restoration, checks, stops

Per mode, `manifest.json` names/hashes every 161 staged file, all candidate
files, authenticated inputs, pre/post member manifests, and these evidence
paths: `stager-pre.json`, `adapter-pre.json`, `adapter.diff`,
`adapter-inverse.json`, `stager-inverse.json`, `source-audit.txt`,
`runner-audit.txt`, `result.json`, and `failure.txt` (all under that mode root).
Stage one inverse restoration is adapter-to-staged byte identity for all three
candidates. Stage two is stager-to-authenticated-original byte identity for all
51 members, templates, and source input. Preserve both manifests, diffs,
commands, output, and SHA-256 values.

Allowed checks only: hash/member comparison, source anchor/unique-hook and
cfg-erasure audit, exhaustive allowlist audit, parser structural audit,
adapter/runner source review, and `git diff --check` on generated patches.
No compile, execution, network, root, native, guest, or acceptance check.
Hard-stop (preserve failure, do not retry) on any pin/member/anchor drift,
unexpected path, non-erased helper/call, changed production method/signature,
alias/claim ambiguity, illegal lock reentry, post-release read, failed inverse
stage, unexpected row result, or native-ownership assertion. Escalate the
preserved evidence; this packet authorizes no correction beyond these candidates.
