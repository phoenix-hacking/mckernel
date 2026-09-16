# M01-B remediation packet 23 — genuine generic row03/row12 source stage

Status: **DRAFT_PENDING_IMPLEMENTATION_REVIEW**. This authorizes one fresh
packet-11-shaped source-stage root only; compilation, execution, runtime,
guest, native, production-gate, application, and whole-OS acceptance are
prohibited.

## Authenticated authority

Require exact hashes before creating the root: checkpoint
`fa32eddbb0f87732b8b5864e041cdce89584039e`; packet21
`8fe519aec93d6c45b784d9ee45d7ffafc149944693948b11805b8d4c6f0d5c8d`;
independent failure22 record `1d0f1ce85366be2572e36f8edcb01128ee26d4e91c8203ca951d842173b95886`;
packet11 `0307c1ce54cb297caf3fc98a6f83b70d715a424114806bdf33e62c92744028cb`;
review17 `aabe8774af2d86e46fc24f0f3c80a2218954b2cd1077839dbba63a161a491bb0`;
failure18 record `346dcc884122f7e6a1ebf4032f014d91cfb008f1a37167038b3b6cfcf0997659`;
failure18 archive `7637f909c7b53c3dd4171e4bee696fbe5d086a35ce5fb838da156d8cf988e3e4`;
and review20 `94e76d353f7c223d50d8c49b67d881bc99f47e89b503d7e64e60ae3071ed013d`.
Reauthenticate packet11's source-map, stager, 51-member-per-mode manifest,
five templates, original-send-gate, and both authority records. Failed roots
and archives remain immutable and are not reused or cleaned.

## Root and exhaustive allowlist

Create only absent root
`/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-remediation-packet-20260916-23`.
It contains exactly 346 regular files: mode2/mode3, each with source,
originals, inputs and diffs; per mode helper.py, record.json, six inputs, 51
source members, 51 originals, 51 genuine diffs, adapter.rs, runner.rs and
nine evidence files (`stager-pre.json`, `adapter-pre.json`, `adapter.diff`,
`adapter-inverse.json`, `stager-inverse.json`, `source-audit.txt`,
`runner-audit.txt`, `result.json`, `failure.txt`); and global result-parser.py
and manifest.json. No other path may be created. Candidate production edits
are only application_syscall.rs, smp_application_syscall.rs and
stability_phase.rs, only in cfg(test) blocks.

## Genuine implementation contract

Each runner is a standalone std host-test crate loading exact staged
application_rpc, application_syscall, smp_application_syscall,
stability_observer and stability_phase modules, plus minimal fallible
Vec/log/clock compatibility. A cfg(test) child of smp_application_syscall
must construct/decode the exact request and invoke real
`Mailbox::new -> open_worker(tid) -> admit(request, claim) -> reserve(handle) ->
copied(handle, serial, true) -> verification_read16`, observer selection,
phase arm, return_value, verification_phase_completion and publish. Preserve
exact `Result<()>`, `Result<Completion<M>, (Self, i32)>`,
`Result<CompletionStatus, i32>`, and `Result<bool, i32>` signatures. Strings
naming methods, invented constructors, and fabricated outcomes do not count.

The cfg(test) fixture owns Option<Box<AlignedBacking>>, exact aligned 56-byte
guarded storage with a 40-byte span, physical identity, request bytes and
exclusive Claim. Ledger owns Mutex<State>; State owns actual
Vec<Box<AlignedBacking>> deferred and quarantine queues. Transfer the sole Box
to a queue; explicit drains move it out, drop it outside the lock, then record
one deallocation. Drops never read response bytes. Add a cfg(test)-only
metadata hook immediately after the real response-status store and before
release; it records status and never fabricates status from release.

Row03 (fresh process/mode): accepted stage-2 baseline, publish Err(-11), all
publication deltas zero and call/owner retained; pre-teardown has no Drop,
quarantine, deferred or deallocate; mailbox destruction gives unfinished
Drop=1/quarantine=1 with backing live; quarantine drain gives deallocate=1.
Row12 (fresh process/mode): accepted stage-2 baseline, wake-None query, then
stage3/commit1, publish Ok(true); send=0 and address/status/release/deferred/
finished each advance once, call absent, post-query absent; teardown adds
nothing and deferred drain gives deallocate=1. Execution requires later,
separate authority; this packet only stages source.

## Evidence, inverses, erasure and stops

`manifest.json` must enumerate all 346 paths and embed path, type-or-kind,
mode, size and SHA bindings for the other 345 finalized files. Its own entry is
externally bound and has no embedded self-hash; dispatcher review/archive
evidence binds the raw final manifest SHA without creating a worker output
path. Adapter diffs must be genuine adapter-to-staged diffs; inverse records
must prove staged-to-stager and stager-to-authenticated-original byte identity.
Audits prove unique anchors, exact signatures, ownership, post-store hook,
real calls, cfg erasure, and strict structural result parsing. Read/syntax-check
Python only with `python3 -B` and `ast.parse`; audit for __pycache__, .pyc and
.pyo after every Python command.

Allowed checks are hashes/members/allowlist, genuine diffs/inverses, anchors,
source/runner/erasure, strict parser, and git diff --check. Hard-stop and
preserve failure.txt on pin drift, existing root, unexpected path/bytecode,
fake call, missing ownership transfer, lock-held drop, post-release read,
fabricated status, signature/control-flow change, failed inverse or unexpected
result; never retry. Acceptance remains false.
