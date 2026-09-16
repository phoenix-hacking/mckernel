# M01-B directed implementation packet 29 — generic row03/row12

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This packet supersedes no
history and releases no implementation, compilation, execution, runtime,
guest, native, production-gate, application, or whole-OS acceptance. It is a
directed source implementation handoff after the hard failure of attempt 27;
root27 and its complete archive are immutable and must not be reused.

## Authenticated authority and exact scope

The dispatcher must authenticate fetched checkpoint
`ae184ee592c2f83a4b92ba419b532e6c68462277` before any staging. Direct packet
authorities are packet25
`576a13a5be0c2fec06c4a62fabd5d25f81f5a994ab54bcdf0dd3733b55906ebb`, passing
review26 `e1e371cf469897d1bfa2f34c765c49ed571063d2e46f91c029a31423005d59e6`,
failure27 record `be2db7b66c652ab8ee8bfac67baf7faa4205ea6ebafe9905931b863718077eed`,
failure27 archive `3b61378e8fdb9ad1894669ceb136c553ed683a7b1b6a2b273be3df335086f86d`,
and hard source review28
`8300a63954d2f7aab4f6afb3cba31beb00dbd9c2890ef5dd09a4817b0864540c`.
Authenticate every inherited pin required by packet25/packet11, including
the actual-method source map, source-manifest, stager, original-send-gate,
five templates, mode records, and all 51 source members per mode. The exact
map authorities remain: source map
`docs/verification/stability-selected-retention-actual-method-source-map-20260916-1.json`
SHA `a09978ce5d6bd8f3cdb43bbeba25af7ba287b5d6143d72e039b781df8abd4131`;
stager `scripts/tests/prepare_stability_selected_retention.py` SHA
`c2b8b256bc4ee0997fed3c210f9d6aef1878a6dc507d3fd96fe66ea011b843b0`;
manifest `scripts/tests/fixtures/stability-selected-retention-v1/source-manifests.json`
SHA `d9d439bff0a90bddcc3920f36b8fac81d6e1515fd83f035e18a34464cc8498d0`;
mode2 record `3bded4f7bfc206b4e64b03a58243d0e3a7783a5a493dd4095be5916a07e7ed48`;
mode3 base/held records
`11de2af873b88fe6afb19749195294b10b41879b6f0e99e97b95065cf25de968` /
`a5cee2ec4397bd37f1abe75a313f6de6a96fbd8983cc49c6f1e9437681fe435d`.
Mode-specific trees must never be substituted. Scope is only fresh-process
generic fixture rows 03 and 12 in modes 2 and 3.

The source envelope is the map's exact 51-name manifest in each mode, including
`application_syscall.rs` (authority SHA
`83c76e277f759e920a91f4fd3bb601268aee39082acbe3f4cd732ec3c58feb92`, anchors
Worker/ResponseMemory/Response::prepare/Completion::publish),
`smp_application_syscall.rs` (SHA
`b18b2356189a42b9083e09b477bba4b81011a9c3c42aafb9564daebb0f813ee2`, anchors
Mailbox::new/open_worker/publish/cancel_call), `smp_application.rs` (SHA
`78e9d817247ab73fa246563b0665afc3eb7ee2d8aa4df361449438fcf57d2a41`),
`stability_phase.rs` (SHA
`d81bb72e67ae0db6a69c6dfed6c9db96c33ec33ffc9aeef015970b431884d4ea`, release
counter/publication gate/release commit), `sysfs_memory.rs` (SHA
`a06db09b3e823636405888cd636e1a6fbf79ca7a0400bb0355899384638d629a`),
`smp_memory.rs` (SHA
`abdaa082804a79b25a749245febc954cf7dcdcbd599d9e56accd79a299c36fb6`), and
`smp_service.rs` (SHA
`96737eb497b3e84a71747b18d1d93133efd75b2a0d7c23e5d1c452869e82d197`). The
remaining manifest members and all six template hashes are inherited only by
exact path/hash from the authenticated packet25/map; a missing or substituted
member is a hard stop.

## Fresh root and two-phase ownership

Use only the absent root
`/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-directed-implementation-packet-20260916-29`.
Phase I is owned by the Rust implementation owner. It may create only
`mode2/` and `mode3/`, each with `source/`, `originals/`, `inputs/`, `diffs/`,
`helper.py`, `record.json`, six named inputs (`response-prepare.rs`,
`return-prepare.rs`, `cancel-guard.rs`, `mailbox-retention.append.rs`,
`phase-retention.append.rs`, `original-send-gate.rs`), the exact 51
manifest-named `source/<name>`, `originals/<name>`, `diffs/<name>.diff`, and
the candidate `adapter.rs` and `runner.rs`. It may create no evidence or
global files. Phase I must hand off a complete per-mode member manifest and
raw hash, plus the exact candidate paths and hash, to the evidence owner.

Phase II is owned by an independent evidence owner only after Phase I's
handoff. It may add only, per mode, `stager-pre.json`, `adapter-pre.json`,
`adapter.diff`, `adapter-inverse.json`, `stager-inverse.json`,
`source-audit.txt`, `runner-audit.txt`, `result.json`, `failure.txt`, and
global `result-parser.py`, `manifest.json`. The final allowlist is exactly
346 regular files: 172 per mode plus two global files. `manifest.json` must
enumerate and bind 345 finalized files (path, kind, mode, size, SHA-256,
inputs, edits, status); its own entry is `externally_bound`, with raw final
manifest SHA recorded only in separate dispatcher evidence. No self-hash
oracle is permitted.

Every Python read uses explicit `python3 -B`; parse `result-parser.py` only
with byte-reading `ast.parse`, never import or execute it. Audit for
`__pycache__`, `.pyc`, and `.pyo` after every Python operation. Any unexpected
path, bytecode, pre-existing root, or failed hash is an immediate hard stop.

## Required implementation (Rust owner)

Replace both adapter/runners coherently. `runner.rs` is a standalone `std`
host-test crate loading the exact staged `application_rpc`,
`application_syscall`, `smp_application_syscall`, `stability_observer`, and
`stability_phase` modules, with only minimal fallible Vec/log/clock
compatibility. Remove its source include from `smp_application_syscall`; put
scenarios inline under `#[cfg(test)]` there, without recursive inclusion.
Correct trait qualification and fixture visibility; never invent `Call` or
production constructors. All additions and calls are module-local `cfg(test)`
and erase byte-for-byte under `cfg(not(test))`. Production signatures remain
exactly `return_value(...) -> Result<()>`,
`verification_prepare_retained(...) -> Result<Completion<M>, (Self, i32)>`,
`verification_phase_completion(...) -> Result<CompletionStatus, i32>`, and
`publish(...) -> Result<bool, i32>`.

Use the exact packet25 request bytes and real chain:
`Mailbox::<TestResponseMemory>::new -> open_worker(71) -> admit(request,
move |_| Ok(memory)) -> reserve(handle) -> copied(handle, serial, true)`;
the 128-byte request has little-endian i32 `[8]=4`, `[24]=0`, `[32]=70`,
`[48]=70`, `[52]=0`, and little-endian u64 `[56]=1`, `[64]=0`, `[72]=0`,
`[80]=0x2000`, `[88]=16`, `[120]=0x1000` (all other bytes zero).
select via `verification_read16(Some(70), 42)`, install the real observer,
set `ARMED (1), commits 0, invalid 0`, call real `return_value`, require
accepted stage 2, then call `verification_phase_completion` and unique
production `publish`. `verification_owner()` must return the exact Claim
`{os:1,generation:1,response:{index:0,serial:Some(1),physical:0x1000,end:0x1028},payload:None}`.

`TestResponseMemory` owns exactly a guarded 56-byte, 8-byte-aligned
allocation (40-byte response span), `Option<Box<AlignedBacking>>`, and a
retained `Arc<Ledger>`. `Ledger` owns `Mutex<State>`; State preallocates real
`Vec<Box<AlignedBacking>>` deferred and quarantine queues and event storage.
Release transfers its sole Box under the mutex, releases the mutex, and
returns the real result. Unreleased Drop transfers to quarantine. Drains move
a batch out under lock, unlock, drop outside lock, then record one deallocation
per Box. Retain the driver Arc through snapshots and drains. Add a test-only
metadata hook immediately after the real response-status store and before
consuming release; it records the actual store, never fabricates status.
No adapter, callback, event recorder, Drop, drain, snapshot, or parser reads
backing bytes after final status publication/release.

Row03 must be stage2/commit0/invalid0, `publish Err(-11)`, retained owner,
zero send/status/release/drop deltas before teardown; teardown gives exactly
unfinished-drop=1 and quarantine=1, then drain gives deallocate=1. Row12 must
first observe wake-None `Err(-71)` without latching invalid, then stage3/
commit1/invalid0, `publish Ok(true)`, one address/status/release/deferred/
finished-drop delta, no send/unfinished/quarantine/deallocate delta, absent
post-publication completion, and deferred drain deallocate=1. Both modes use
fresh process state. Snapshots precede drains and event order is exact:
construction, preparation baseline, status store, release, deferred insertion,
finished Drop, deallocation; held teardown is construction, preparation
baseline, unfinished Drop, quarantine insertion, deallocation.

## Independent evidence and hard stops

Evidence owner must inspect finalized source, not trust declarations. Produce
genuine adapter-to-staged unified diffs; exact adapter and stager inverses;
complete 345-file hashes; source anchors, unique post-store hook, real method
calls, Claim/physical identity, ownership transfer, lock-free drops, exact
events/snapshots, and `cfg(not(test))` erasure. `result-parser.py` must enforce
a strict schema separating `expectations` (unexecuted) from `observations`
(none are execution evidence), exact modes/rows/counts/events, and explicit
scope flags; prose or substring assertions are invalid. Run only hash,
membership, inverse, structural, erasure, parser-AST, bytecode-audit, and
`git diff --check` checks. Do not compile, execute, use network/root/native/
guest resources, or claim acceptance.

Hard-stop and preserve `failure.txt` on any drift, fake call/result, missing
real queue/Arc ownership, alias or Claim ambiguity, lock re-entry or lock-held
drop, post-publication read, fabricated status, signature/control-flow change,
non-erased helper, failed inverse, manifest mismatch, unexpected row result,
unexpected file, or bytecode. Escalate after the first unexpected failure;
retry is prohibited without a new independently reviewed packet.

Implementation release, compilation, runtime execution, guest execution,
native backing, production-gate credit, application acceptance, and whole-OS
acceptance remain false. Ready-for-review means only that the two-phase source
and evidence handoff is complete.
