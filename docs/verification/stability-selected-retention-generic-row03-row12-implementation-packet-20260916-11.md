# M01-B generic ledger rerun packet 11: rows 03 and 12

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**.  This is a narrow prerequisite
for actual admitted preparation, held completion row 03, and wake-`None`
consuming-release row 12 in two exact, separately staged generic mode trees.
It is not an implementation release, production claim, runtime/application
acceptance, or native-backing decision.

## Authenticated inputs and scope

Before staging, hash and require exact equality for these records:

| input | SHA-256 |
|---|---|
| design matrix failure 12 | `6cd2e5f52b163a536b32e6473ed3f9eccfe179ff89ceba776f9dfc6a60d9e0ab` |
| design input failure 13 | `8f3f44a61f0392b10f79258842a120bfefeb4aa8b5828868eb53a19de665e8d8` |
| rejected packet 8 | `8071bd38119ecc11e58e5e68c5b41ae5bee89a760d461350509442ec7af5744c` |
| actual-method source map | `a09978ce5d6bd8f3cdb43bbeba25af7ba287b5d6143d72e039b781df8abd4131` |
| packet 10 PASS review 15 | `e7d38285b99ad21329ad497516547d9ace150172f38905d2c4d77c29503461d9` |
| implementation failure 16 | `b9e0c07b8daea4a773908f40761c2fe83e6ae755860c2170bd9978299cf69e4b` |
| complete failure-16 archive | `43004cea9973639ae59bb4df8af431ebb9d25bf58afac0ff2b0faeb32a475f0c` |

Also authenticate the source-map stager
`scripts/tests/prepare_stability_selected_retention.py` (`c2b8b256bc4ee0997fed3c210f9d6aef1878a6dc507d3fd96fe66ea011b843b0`),
manifest `scripts/tests/fixtures/stability-selected-retention-v1/source-manifests.json`
(`d9d439bff0a90bddcc3920f36b8fac81d6e1515fd83f035e18a34464cc8498d0`), its
five named templates (response-prepare, return-prepare, cancel-guard,
mailbox-retention.append, phase-retention.append), the separately retained
`original-send-gate.rs` input
(`dac2855ca19e587c33f7bd5a36c30c9090a6ea846f6dca90081abf0543228267`),
and the exact mode records:
mode 2 `3bded4f7bfc206b4e64b03a58243d0e3a7783a5a493dd4095be5916a07e7ed48`;
mode 3 held `a5cee2ec4397bd37f1abe75a313f6de6a96fbd8983cc49c6f1e9437681fe435d`.
All 51 members per mode are manifest-bound; retain mode-specific
`smp_application_syscall.rs` and `stability_phase.rs` without substitution.

No rows 01-02, 04-11, or 13-27; no negative, identity/cancel, clock/notify,
or native-backing scope is authorized.  The only semantic cases are fresh
process row 03 and row 12, each run independently in both modes.

## Exact fixture-owned backing ledger

`TestResponseMemory` is a `cfg(test)` fixture only.  It exclusively owns an
8-byte-aligned guarded allocation of exactly 56 bytes: an exact 40-byte
response span between two 8-byte guards.  Its physical address and exclusive
claim identity are recorded after construction/preparation as the per-row
baseline; aliases are rejected.  The fixture owns `Option<Box<AlignedBacking>>`
and `Arc<Ledger>` plus a `released` flag.  `release(mut self)` records exactly
one release, marks released, takes the `Box` into a ledger-owned deferred
vector, and returns the production method's exact result.  Its later `Drop`
records exactly one finished Drop and never touches response bytes.

An unreleased `Drop` takes the `Box` into a ledger-owned quarantine vector,
then records exactly one unfinished Drop and one quarantine event.  Ledger
vectors retain raw backing until explicit drain, after all semantic snapshots;
`drain_deferred`/`drain_quarantine` records exactly one deallocation per Box and
never reads response bytes.  These are fixture semantics, not production
quarantine or deallocation claims.  No adapter, parser, callback, or Drop may
read bytes after release.  Event order is deterministic.  The released path is
construction, preparation baseline, status store, release, deferred insertion,
finished Drop, then explicit deallocation; a send event is absent in row 12.
The held teardown path is construction, preparation baseline, unfinished Drop,
quarantine insertion, then explicit deallocation.  Moving the Box before the
corresponding ledger event is an implementation detail and cannot expose or
read its bytes.

## Actual chain and row contracts

Every case uses a fresh mailbox, backing, ledger, and one-shot state, then the
unchanged chain `Mailbox::new -> open_worker(tid) -> admit(request, claim) ->
reserve(handle) -> copied(handle, serial, true)`, real observer selection and
claim verification, and phase `ARMED (1), commits 0, invalid 0`.  Use the real
`return_value(...) -> Result<()>`; selected preparation's
`verification_prepare_retained(...) -> Result<Completion<M>, (Self, i32)>`.
Use real `verification_phase_completion(key) -> Result<CompletionStatus, i32>`
and unique production `publish(...) -> Result<bool, i32>`.  All test helpers,
insertions, hooks, and calls are module-local `#[cfg(test)]` and erased under
`cfg(not(test))`; Worker remains nongeneric and no private Call constructor is
invented.

Row 03: after successful admitted preparation and accepted-state observation,
set stage 2, commits 0, invalid 0.  `publish` returns `Err(-11)` from the
held gate.  Snapshot before mailbox teardown: publish Err(-11), invalid 0,
call/owner held, and deltas send/status/release/finished-drop/unfinished-drop/
quarantine/deferred/deallocate all zero (address compared from the
post-prepare baseline).  Explicit mailbox teardown then records exactly
unfinished-drop=1 and quarantine=1, backing remains live; explicit quarantine
drain records deallocate=1.

Row 12: after successful admitted preparation, call the phase query before
state mutation: wake `None` returns `Err(-71)` and does not latch invalid.
Set stage 3, commits 1, invalid 0.  `publish` returns `Ok(true)`, with zero
send, status=1, release=1, finished-drop=1, deferred=1, unfinished-drop=0,
quarantine=0, deallocate=0; call is absent and post-publication phase query
is `Ok(CompletionStatus { present: false, publication_since: None })`.
Mailbox teardown adds nothing.  Explicit deferred drain records deallocate=1.

The row-03 and row-12 snapshots are taken before any mailbox teardown or
ledger drain.  All deltas are from the exact post-prepare baseline.  Physical
identity, owner/claim identity, 40-byte span geometry, and no-post-release-read
assertions are mandatory.

## Exact creation/write allowlist

Use fresh root
`/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-packet-20260916-11`.
The only created paths are that root; `mode2` and `mode3`, each with
`source/`, `originals/`, `inputs/`, and `diffs/`.  Per mode the stager may
create exactly 161 files: `helper.py`, `record.json`; six exact `inputs/` files
(`response-prepare.rs`, `return-prepare.rs`, `cancel-guard.rs`,
`mailbox-retention.append.rs`, `phase-retention.append.rs`, and
`original-send-gate.rs`); and, for each of the manifest's exact 51 names,
`source/<name>`, `originals/<name>`, and `diffs/<name>.diff`.  The only other
created files are `mode2/adapter.rs`, `mode3/adapter.rs`, `mode2/runner.rs`,
`mode3/runner.rs`, global `result-parser.py`, global `manifest.json`, and per-mode
`stager-pre.json`, `adapter-pre.json`, `adapter.diff`, `adapter-inverse.json`,
`stager-inverse.json`, `source-audit.txt`, `runner-audit.txt`, `result.json`,
and `failure.txt`: exactly 346 files total.  No other path, repository production source, released
packet, catalog, oracle, native source, or acceptance metadata may be edited.
Adapters may modify only the necessary generated source files
`application_syscall.rs`, `smp_application_syscall.rs`, and
`stability_phase.rs`, and only inside `cfg(test)`.

## Rerun-only bytecode correction

Attempt 16 is immutable failure evidence.  Do not reuse, modify, or clean its
root.  Every Python invocation in this rerun must use explicit `-B`; no command
may use `py_compile` or any API that emits bytecode.  Validate parser syntax only
with an explicit `python3 -B -c` command that reads `result-parser.py` and calls
`ast.parse` without importing or executing the parser.  The stager, parser
audit, manifest audit, inverse audit, and every helper invocation use the same
no-bytecode rule.  Audit for `__pycache__`, `.pyc`, and `.pyo` after every Python
step and hard-stop immediately if any appears.  This correction changes no
semantic source, case, event, count, path allowlist, or acceptance boundary from
packet 10; the exact final total remains 346 files.

## Checks and hard stops

Precompile-only checks are exact input/source/member/template hashes, manifest
membership and inverse restoration, exhaustive allowlist, source anchors and
unique hooks, cfg-erasure, exact adapter/runner method/result signatures,
physical/claim and ledger assertions, parser structural audit, and
`git diff --check` on generated patches.  Do not compile, execute code, use
network/root/native/guest resources, or claim acceptance.  Stop and preserve
evidence on any pin/member/anchor drift, unexpected path, non-erased helper,
production signature/control-flow change, alias/claim ambiguity, lock
re-entry, post-release read, incorrect event order/count, failed inverse, or
unexpected row result; do not retry.  Independent review must approve this
packet before any implementation staging.

Status remains **DRAFT_PENDING_INDEPENDENT_REVIEW**; implementation release,
runtime execution, production-gate credit, and application/whole-OS acceptance
are all false.
