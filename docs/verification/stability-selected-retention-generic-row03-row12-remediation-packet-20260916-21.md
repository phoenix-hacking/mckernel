# M01-B remediation packet 21 — genuine generic row03/row12 source stage

Status: **DRAFT_PENDING_IMPLEMENTATION_REVIEW**.  This packet authorizes one
fresh packet-11-shaped source-stage root only; it authorizes no compilation,
execution, runtime, guest, native, production-gate, application, or whole-OS
acceptance credit.

## Authenticated authority

Require exact hashes before creating the root (and preserve both failed roots
immutable): checkpoint `fa32eddb0f87732b8b5864e041cdce89584039e`;
packet 11 `0307c1ce54cb297caf3fc98a6f83b70d715a424114806bdf33e62c92744028cb`;
review 17 `aabe8774af2d86e46fc24f0f3c80a2218954b2cd1077839dbba63a161a491bb0`;
failure 18 record `346dcc884122f7e6a1ebf4032f014d91cfb008f1a37167038b3b6cfcf0997659`;
failure 18 archive `7637f909c7b53c3dd4171e4bee696fbe5d086a35ce5fb838da156d8cf988e3e4`;
and remediation review 20 `94e76d353f7c223d50d8c49b67d881bc99f47e89b503d7e64e60ae3071ed013d`.
Also reauthenticate packet-11's source-map, stager, 51-member-per-mode
manifest, five templates, original-send-gate, and mode-2/mode-3 authority
records and hashes.  The attempt-16/18 roots and archives are read-only
historical evidence and must not be reused, cleaned, or modified.

## Fresh root and exhaustive allowlist

Create only absent root
`/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-remediation-packet-20260916-21`.
Its exact 346 regular files are: two mode trees (`mode2`, `mode3`), each with
`source/`, `originals/`, `inputs/`, `diffs/`; per mode `helper.py`, `record.json`,
six named inputs, 51 `source/<name>`, 51 `originals/<name>`, 51 genuine
`diffs/<name>.diff`, `adapter.rs`, `runner.rs`, and nine evidence files
(`stager-pre.json`, `adapter-pre.json`, `adapter.diff`, `adapter-inverse.json`,
`stager-inverse.json`, `source-audit.txt`, `runner-audit.txt`, `result.json`,
`failure.txt`); plus global `result-parser.py` and `manifest.json`.
No other path may be created. Candidate production edits are restricted to
`application_syscall.rs`, `smp_application_syscall.rs`, and
`stability_phase.rs`, only in cfg(test) blocks, with adapters/runners/parser/
evidence as the named generated outputs.

## Required genuine implementation

Each `runner.rs` is a standalone std host-test crate loading the exact staged
modules (`application_rpc`, `application_syscall`, `smp_application_syscall`,
`stability_observer`, `stability_phase`) and only minimal runner-local
fallible Vec/log/clock compatibility.  A cfg(test) child of
`smp_application_syscall` must construct/decode the exact read request and
invoke real `Mailbox::new -> open_worker(tid) -> admit(request, claim) ->
reserve(handle) -> copied(handle, serial, true) -> verification_read16`, real
observer selection, phase arm, and `return_value`.  It must then invoke real
`verification_phase_completion` and `publish`, with exact signatures and
`Result<()>`, `Result<Completion<M>, (Self, i32)>`,
`Result<CompletionStatus, i32>`, and `Result<bool, i32>` preserved.  No method
names in strings, invented constructors, or fabricated outcomes count.

The fixture must own `Option<Box<AlignedBacking>>`, exact aligned 56-byte
guarded storage with a 40-byte span, physical identity, request bytes and
exclusive `Claim`.  `Ledger` owns `Mutex<State>`; `State` owns actual
`Vec<Box<AlignedBacking>>` deferred and quarantine queues.  Transfer the sole
Box into the appropriate queue; explicit drains move it out, drop it outside
the lock, then record exactly one deallocation.  Drops never read response
bytes.  Event ordering is genuine and deterministic.  Add a cfg(test)-only
metadata hook immediately after the real response-status store and before
release; it records status only and must not fabricate status from release.

Row 03, fresh process/mode: accepted stage-2 baseline, `publish == Err(-11)`;
all publication deltas zero, call/owner retained; pre-teardown snapshot has
no Drop/quarantine/deferred/deallocate, mailbox destruction gives unfinished
Drop=1/quarantine=1 with backing live, quarantine drain gives deallocate=1.
Row 12, fresh process/mode: accepted stage-2 baseline, phase wake-None query
then stage 3/commit 1, `publish == Ok(true)`; send=0 and address/status/
release/deferred/finished each advance once, call absent, post-query absent;
mailbox teardown adds nothing and deferred drain gives deallocate=1.  Every
row/mode is isolated to a fresh process under later separately authorized
execution; this packet only stages source.

## Evidence, inverses, erasure, and hard stops

`manifest.json` must enumerate every one of the 346 paths, mode, size, mode,
sha256, inputs, generated edits, and status.  `adapter.diff` must be genuine
adapter-to-staged unified diffs; `adapter-inverse.json` must prove staged bytes
restore to stager output; `stager-inverse.json` must prove stager output
restores every authenticated original member/template.  Audits must prove
unique anchors, exact signatures, physical/claim identity, real call sites,
post-store hook placement, cfg(not(test)) byte restoration, and no parser
substring/self-hash oracle.  `result-parser.py` must use strict structural
JSON validation; read/syntax-check it only with `python3 -B` plus `ast.parse`.
Audit for `__pycache__`, `.pyc`, `.pyo` after every Python command.

Allowed checks are hash/member/allowlist, genuine diff/inverse, anchor,
source/runner/erasure and strict parser audits, and `git diff --check` on
generated patches.  Hard-stop, preserve `failure.txt`, and do not retry on
any pin drift, existing root, unexpected path/bytecode, fake method call,
missing real ownership transfer, lock-held drop, post-release read, fabricated
status, signature/control-flow change, failed inverse, or unexpected result.
Both execution and acceptance remain false.
