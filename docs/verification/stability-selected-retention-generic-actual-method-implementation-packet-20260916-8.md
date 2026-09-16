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
write grant. Stager output must say `PREPARED_NOT_COMPILED_NOT_EXECUTED`.

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
never dereferences released memory. Mode 3 uses only runner-owned atomic
`ktime_get() -> i64`; mode 2 has no substituted mode-3 clock.

## Exact row matrix and legal sequencing

Every row is a fresh process with fresh mailbox, backing, ledger, and one-shot
statics. Record arguments, result, selected identity, state/status words,
callback count, baseline deltas, ledger sequence, first-invalid, quarantine,
and release/Drop counts.

* Holds: stages 0, 1, 6, 255, and stage 3 with commits 0 or 2, for both wake
  values, return publish `-11` and latch invalid `-71`; stages 2, 4, 5 return
  `-11` with invalid zero. All retain backing with zero publication/release.
* M01-B-18 is the complete ordinary-unselected control: mismatched PID gives
  `Ok(None)`, pre-RET publish is `Ok(false)`, then ordinary `return_value` and
  wake-None publish are `Ok(true)` with exactly one status store/release.
* Mode 2 selected wake-Some performs the real notification failure `-5` only
  after publication/release; it never rolls back or claims retention. Mode 3
  selected wake-Some at `t` makes one fault attempt, `-11`, zero real sends and
  retains; at `t+1,999,999,999` it is still held; at exactly
  `t+2,000,000,000` it recovers once, stores status, and releases once.
* M01-B-20 first completes `return_value`; cancel-before-publication is a
  distinct serialized case (expected guard `-71`, first-invalid `-125`,
  quarantine/no release). Its positive publication conclusion uses a fresh
  completion and, for mode 3, completes the exact two-second recovery before
  recording post-RET conclusions. Never cancel while a mutable mailbox borrow
  or owner lock is held.
* M01-B-25 selects after admitted/copying, then performs serialized
  cancel-before-RET: `-71`, first-invalid `-125`, quarantine, zero release and
  no post-release read. M01-B-26 uses separate fresh serialized processes for
  RET-before-precommit-cancel and cancel-before-RET; it asserts at most one
  completion/release and no reentry. M01-B-27 fully publishes first (and mode-3
  fully recovers at two seconds), then cancellation has the unchanged
  post-publication result with no rollback, relatch, or second release.
* Negative TID is `-22`; nonzero initial completed status, invalid wake/state,
  changed selected claim, and forced second CAS are `-71`; the CAS row preserves
  prefix writes. Changed owner is a real mismatch, not fabricated physical
  mutation. All other original rows 01--27 retain their reviewed attempt-6
  method/result definitions; no row earns native ownership credit.

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
