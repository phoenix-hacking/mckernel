# M01-B remediation packet 25: genuine generic row03/row12 source stage

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This is an escalated replacement
for rejected packets 21 and 23. It authorizes one fresh packet-11-shaped
source-stage root only; it authorizes no compilation, execution, runtime,
guest, native, production-gate, application, or whole-OS acceptance credit.

## Authenticated inputs and scope

Before staging, hash and require exact equality for these direct authorities:

| input | SHA-256 |
|---|---|
| checkpoint | `fa32eddbb0f87732b8b5864e041cdce89584039e` |
| packet 11 | `0307c1ce54cb297caf3fc98a6f83b70d715a424114806bdf33e62c92744028cb` |
| review 17 | `aabe8774af2d86e46fc24f0f3c80a2218954b2cd1077839dbba63a161a491bb0` |
| failure 18 record | `346dcc884122f7e6a1ebf4032f014d91cfb008f1a37167038b3b6cfcf0997659` |
| failure 18 archive | `7637f909c7b53c3dd4171e4bee696fbe5d086a35ce5fb838da156d8cf988e3e4` |
| remediation review 20 | `94e76d353f7c223d50d8c49b67d881bc99f47e89b503d7e64e60ae3071ed013d` |
| rejected packet 21 | `8fe519aec93d6c45b784d9ee45d7ffafc149944693948b11805b8d4c6f0d5c8d` |
| failure review 22 | `1d0f1ce85366be2572e36f8edcb01128ee26d4e91c8203ca951d842173b95886` |
| rejected packet 23 | `d034fc887703a67ba9d3fb30e6b42d5d9449746492a319f567e294451907162c` |
| failure review 24 | `f5809a4dfae6bddbabdff227957f3af0133c05252193193b4f28ccf2d7b2be20` |

Also authenticate packet 11's design-matrix and design-input failures, rejected
packet 8, actual-method source map, packet-10 review 15, implementation failure
16 and its complete archive; the source-map stager, manifest, five named
templates, original-send-gate, and exact mode records; and all 51 source members
per mode. Use their exact packet-11 paths and hashes without substitution.
Attempts 16 and 18, their roots and their archives are immutable evidence and
must not be reused, modified, cleaned, or removed.

No rows 01-02, 04-11, or 13-27; no negative, identity/cancel, clock/notify, or
native-backing scope is authorized. The only semantic cases are fresh-process
row 03 and row 12, each independently staged in both modes.

## Exact fixture-owned backing ledger

`TestResponseMemory` is a `cfg(test)` fixture only. It exclusively owns an
8-byte-aligned guarded allocation of exactly 56 bytes: an exact 40-byte response
span between two 8-byte guards. Its physical address and exclusive claim identity
are recorded after construction/preparation as the per-row baseline; aliases are
rejected. It owns `Option<Box<AlignedBacking>>`, `Arc<Ledger>`, and a released
flag. `Ledger` owns `Mutex<State>`; `State` owns actual
`Vec<Box<AlignedBacking>>` deferred and quarantine queues, with capacity
preallocated before admission.

`release(mut self)` records exactly one release, marks released, transfers its
sole Box into the ledger-owned deferred vector under the mutex, releases the
mutex, and returns the production method's exact result. Its later `Drop` records
exactly one finished Drop and never touches response bytes. An unreleased `Drop`
transfers the sole Box into the ledger-owned quarantine vector and records exactly
one unfinished Drop and one quarantine event. Explicit drains move Boxes out
under the lock, drop them outside the lock, then record exactly one deallocation
per Box. No adapter, parser, callback, Drop, event recorder, or drain may read
backing bytes after final status publication or release.

The released event sequence is exactly construction, preparation baseline,
status store, release, deferred insertion, finished Drop, then explicit
deallocation. The held-teardown sequence is exactly construction, preparation
baseline, unfinished Drop, quarantine insertion, then explicit deallocation.
Snapshots occur before drains. These are fixture semantics, not production
quarantine or deallocation claims.

## Exact request, ownership and real method chain

Each fresh 128-byte request has little-endian i32 message `[8]=4`, cpu `[24]=0`,
pid `[32]=70`, requester `[48]=70`, target `[52]=0`; and little-endian u64 valid
`[56]=1`, number `[64]=0`, args `[72]=0`, `[80]=0x2000`, `[88]=16`, and response
`[120]=0x1000`. Decode it with the real `Request::decode`. The fixture's
`verification_owner()` returns exactly `Claim { os: 1, generation: 1, response:
Tag { index: 0, serial: Some(1), physical: 0x1000, end: 0x1028 }, payload: None }`;
the default `None` is forbidden.

Every case uses a fresh mailbox, backing, ledger and one-shot state. Invoke the
unchanged real chain `Mailbox::<TestResponseMemory>::new -> open_worker(71) ->
admit(request, move |_| Ok(memory)) -> reserve(handle) -> copied(handle, serial,
true)`. Obtain the real selection through `verification_read16(Some(70), 42)`,
install it with the real observer, set phase `ARMED (1), commits 0, invalid 0`,
and call real `return_value(handle, serial, 0, 16, |_| Ok(()))`. Require actual
accepted stage 2 before recording the baseline. Then invoke real
`verification_phase_completion(key)` and unique production `publish` paths.

Preserve the exact production signatures `return_value(...) -> Result<()>`,
`verification_prepare_retained(...) -> Result<Completion<M>, (Self, i32)>`,
`verification_phase_completion(...) -> Result<CompletionStatus, i32>`, and
`publish(...) -> Result<bool, i32>`. All helpers, insertions, hooks and drivers
are module-local `#[cfg(test)]`; a child of `smp_application_syscall` may inspect
private fields without exposing or inventing `Call`. Worker remains nongeneric.
Each `runner.rs` is a standalone std host-test crate loading the exact staged
`application_rpc`, `application_syscall`, `smp_application_syscall`,
`stability_observer`, and `stability_phase` modules, plus only minimal
runner-local fallible Vec/log/clock compatibility.

Add only a `cfg(test)` metadata hook immediately after the real response-status
store and before consuming release. It records the actual stored status and
must not fabricate a Status event from release.

## Exact row contracts

Both rows begin with wake state `None`. Their snapshots and deltas use the exact
post-prepare accepted-stage-2 baseline.

Row 03: set stage 2, commits 0, invalid 0. `publish` returns `Err(-11)` from the
held gate. Before mailbox teardown, invalid remains zero, call/owner remain held,
and send/status/release/finished-drop/unfinished-drop/quarantine/deferred/
deallocate and address deltas are all zero. Mailbox teardown records exactly
unfinished-drop=1 and quarantine=1 while backing remains live. Explicit
quarantine drain records deallocate=1.

Row 12: before mutation, the real phase query returns `Err(-71)` without latching
invalid. Set stage 3, commits 1, invalid 0. `publish` returns `Ok(true)`; address,
status, release, deferred and finished-drop each advance exactly once; send,
unfinished-drop, quarantine and deallocate remain zero. The call is absent and
the post-publication query is `Ok(CompletionStatus { present: false,
publication_since: None })`. Mailbox teardown adds no delta. Explicit deferred
drain records deallocate=1.

Each row/mode runs in a fresh process only under later separately reviewed
execution authority because observer and token state are one-shot. This packet
does not authorize that execution.

## Exact creation and write allowlist

Use only absent root
`/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-remediation-packet-20260916-25`.
Its only created paths follow packet 11 exactly: mode2 and mode3, each with
`source/`, `originals/`, `inputs/`, and `diffs/`; per mode `helper.py`,
`record.json`; the six exact named inputs `response-prepare.rs`,
`return-prepare.rs`, `cancel-guard.rs`, `mailbox-retention.append.rs`,
`phase-retention.append.rs`, `original-send-gate.rs`; and, for each exact 51-name
manifest, `source/<name>`, `originals/<name>`, `diffs/<name>.diff`. Per mode also
create `adapter.rs`, `runner.rs`, and exactly these nine evidence files:
`stager-pre.json`, `adapter-pre.json`, `adapter.diff`, `adapter-inverse.json`,
`stager-inverse.json`, `source-audit.txt`, `runner-audit.txt`, `result.json`,
`failure.txt`. Global outputs are only `result-parser.py` and `manifest.json`.
The exact total is 346 regular files. No other path may be created.

Candidate production edits are restricted to generated
`application_syscall.rs`, `smp_application_syscall.rs`, and
`stability_phase.rs`, only inside `cfg(test)`. No repository production source,
released packet, catalog, oracle, native source, acceptance metadata, or prior
root may be edited.

## Noncircular manifest, evidence and erasure

`manifest.json` enumerates all 346 paths. For the other 345 finalized files it
embeds path, file kind, mode, size, SHA-256, authenticated inputs, generated
edits and status. Its own entry is explicitly `externally_bound`, contains no
embedded self-size or self-hash, and is not treated as a self-hash oracle. The
dispatcher binds the final raw manifest byte SHA-256 in separate review/archive
evidence without adding any worker output path.

`adapter.diff` contains genuine adapter-to-staged unified diffs.
`adapter-inverse.json` proves exact staged bytes restore to stager output.
`stager-inverse.json` proves stager output restores every authenticated original
member and template. Audits prove unique anchors, exact signatures, physical and
claim identity, real call sites, exact event order, post-store hook placement,
`cfg(not(test))` byte restoration, complete path/file hashes, and no parser
substring or self-hash oracle. `result-parser.py` performs strict structural JSON
validation; syntax-check it only by reading bytes with `python3 -B` and
`ast.parse`, never importing or executing it.

Every Python command uses explicit `-B`; `py_compile` and bytecode-emitting APIs
are forbidden. Audit for `__pycache__`, `.pyc`, and `.pyo` after every Python
step and hard-stop immediately if one appears.

## Checks and hard stops

Allowed source-stage checks are exact input/source/member/template hashes,
manifest membership and external self-binding, genuine diff/inverse restoration,
exhaustive allowlist, source anchors and unique hooks, exact method/result
signatures, physical/claim identity, real calls, ledger ownership and event order,
cfg erasure, strict parser structure, and `git diff --check` on generated patches.

Hard-stop, preserve `failure.txt`, and do not retry on pin/member/anchor drift,
existing root, unexpected path or bytecode, fake method call, invented result,
missing real ownership transfer, alias/claim ambiguity, lock re-entry or
lock-held drop, post-release read, fabricated status, signature/control-flow
change, non-erased helper, failed inverse/restoration, manifest mismatch, or
unexpected row result. Do not compile, execute code, use network/root/native/
guest resources, or claim acceptance.

Status remains **DRAFT_PENDING_INDEPENDENT_REVIEW**. Implementation release,
compilation, runtime execution, native backing, production-gate credit,
application acceptance and whole-OS acceptance are all false.
