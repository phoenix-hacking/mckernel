# M14/M15: recover native execution and close original checks

Prepared 2026-11-12. Evidence baseline: `3f639748089639086c9e09aff326af78e0b7aaeb` on `codex/local-native-staging-repair`.

This is a technical reference supplement to [CAMPAIGN.md][campaign]. CAMPAIGN remains the sole active plan and status authority; native workstation Root remains the sole compositor and operator. Scope: functional McKernel OS/apps and Rust/assembly migration only; no security testing.

## 1. Decision and immediate priorities

Earlier native applications really passed. The strongest retained comparisons are the October 23 ten-cycle M05 acceptance and the October 28 CURRENT115 process/exec/wait acceptance. Both include application and cleanup evidence. They establish a working historical execution model, but their old image/module/payload cohorts cannot establish acceptance for the changed November cohort.

The current attempt has a **proven error-reporting defect**: the supervisor can retain an exception in memory and pause without persisting its original cause or traceback. A later watchdog termination can then leave the parent reporting only a strict retirement refusal. That mechanism explains how the useful first failure can disappear; the published records do **not** prove which original predicate or event failed in session `81012`.

The fastest justified sequence is:

1. Finish the existing read-only, owning-context diagnosis of the current attempt and recover whatever original evidence was actually saved.
2. Prepare a small private correction to exception and wait-result reporting, with focused changed-path controls, in parallel with the current-attempt diagnosis and cleanup.
3. Qualify and complete only that failed attempt's necessary cleanup, retaining unresolved ownership until positively established.
4. Compose the reviewed correction and reuse the current matching image, modules, installation and passing proofs. Perform the next required native operation only after legitimate current ownership and fresh admission are established.
5. In parallel, finish the missing time/vDSO bindings, assess the two M15 diagnostic deployment requirements against retained consumer evidence, and advance the remaining actual C/provider replacements.

At the 16:15:24 UTC / 09:15:24 Boise telemetry snapshot, the controller was running with four active agent turns. Verified checklist progress remained **M14 70.00%, M15 74.59%, 105/156 original checks**. The published ledger remains the score authority. A recovery, a new diagnostic, or a passing preparation slice earns no original closure by itself. [Status][status] · [Original ledger][ledger]

## 2. What passed before and how to reuse it

### Historical acceptance comparison

| Evidence | Verified result | Useful reuse | Boundary |
|---|---|---|---|
| October 23, commit `0a0eb01ebf7fcf75f342aef7159b15538b5fd2fd` | Ten new cycles, twenty applications; exact 40-byte output per application, empty stderr, exit zero, EOF and empty procfs; application retirement before shutdown, strict stop/destroy/release, reboot and a second application; exact prepared resources returned. | Application oracle discipline; repeated lifecycle and cleanup ordering; whole-evidence acceptance structure. | Accepted historical `P-M05-03` and M05. The record explicitly grants no M14/P12 credit. |
| October 28, commit `858fd77eb237836c434192671b0576f763d85c66` | Original `P-M06-01-process-exec-wait-235B`; independent native and application acceptance; exact 235-byte stdout, empty stderr; original BEGIN/ACK/DELETE and distinct final retirement zero; direct helper joined, return code zero, streams closed. | Matching source/artifact/provider joins; normal entry and original-parent wait ownership; exact process/exec/wait oracle and retirement conditions. | The cited application record accepts this case. A separate record accepts F02's original supported-default file contract on exact CURRENT115. Neither establishes acceptance for changed inputs or completion of M14/M15. |

Sources: [October 23 formal acceptance][old-m05], [October 28 independent application acceptance][old-process], [October 28 normal helper join][old-join], [F02 original supported-default file closure][old-f02]. These were McKernel applications inside disposable QEMU guests, not evidence of a bare-metal workstation application run. Preserve the accepted F02 scope; do not reopen it merely because another component changed.

The historical commands were:

```text
# Historical M05 reference only
/bin/mcexec -t 1 0 app A "" B

# Historical CURRENT115 process reference only
/bin/mcexec -t 1 0 /apps/app
```

Their bound environment used `/case/work`, `PATH=/usr/bin:/bin`, `COKERNEL_PATH=/apps`, a four-vCPU/8192-MiB guest with two NUMA nodes, a ten-second application bound and 1024-byte stream bounds. These values identify the old cases; they are not replacement settings for the current operation. [M05 binding][old-m05-binding] · [CURRENT115 stage/map acceptance][old-process-stage]

### Cohort separation

| Component | October 23 M05 | October 28 CURRENT115 |
|---|---|---|
| Image SHA256 | `10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2` | `de9fdd13b55a5a17158fa8247cc9351c1d9b1944a72c45bac9e4774473dca024` |
| Executor SHA256 | `dca0250159ce04a272a72dd1217213a4b6e0f21ec8c21da211eede250c451954` | `e5d18169ee50581274b374bba17fcefebe39e828885f367bfee182beaa3df756` |
| Payload SHA256 | `8be0b167d7267d4ef5aa122f62ebdbd95d6aa0be4f75384b9285d9983683c234` | `537cb22b2af1f7fca1202afaf45b017364823c185c2ec47474093e51647ba5b8` |

The current image is `a2f00a6105f20642db8ef95fe12ade0873120594531f325ef363a4bb59f0ff8a`, from source `c964be3917c8f4c5031108aa927c84894584b667`, with its current matching module/deployment cohort. The current intended first-repeat payload is `/bin/mcexec -t 1 0 /apps/signal.alternate-repeat`. It has different obligations from the old 40-byte signal case. Historical success is useful reference evidence; neither old payload substitutes for the current signal/context/xstate requirement. [Current cohort ownership][c4] · [Current request][request]

Reuse the earlier normal-entry, original-parent join and precise cleanup design where the actual contracts match. Reuse already qualified current inputs without replay. Change only the failing or invalidated portion. Do not transplant old binaries, restore an old harness wholesale, or mark an old scoped result as a new whole requirement.

The existing [M14 stable baseline guide][stable] already explains incremental builds and proof invalidation. Its November 10 build/link baseline is a useful foundation; it is not the current native acceptance record.

## 3. Current failure: what the source proves

The current packet records `UNKNOWN_NATIVE_CUSTODY` and the exception `exact current direct native supervisor join required`. The outer session is `81012`. At the pinned checkpoint, Root provider `1930708/b58283682`, sudo `1930695/b58283676`, and supervisor `1930710/b58283729` were the named identities. These are historical identity bindings to verify against the live owning context, never standalone PID instructions. The retained charge is 1.5 GiB / one HOST job, alongside native/source/runtime custody. [Failure record][failure] · [Exact published inputs][published]

The two published Root stdout rows establish materialization intent and a sealed request explicitly marked as not a native claim. They do not establish that the McKernel application ran. [Publisher stdout][publisher]

### Exact source path

| Source and pin | Decisive behavior |
|---|---|
| `supervisor_entry.py`, SHA256 `a47aba63261aa94492b95614b0a53b899ee20bc359c8de321bd2f07ec34eb2cd` | Lines 50–64 preallocate/retain `NativeAdmission`, catch constructor failure, retain it and pause. Lines 121–128 similarly retain later failures unless already released. Neither catch path emits the original exception/traceback. |
| `operation_watchdog.py`, SHA256 `debaf3c6ba43e09f632cf33505c7aabf72ba4dd18cf25b6a934b26ced3c5bb77` | After its pidfd/deadline logic, line 178 calls `os.waitpid(self.pid, 0)`, line 179 checks the returned PID, line 180 stores the raw status, and line 185 calls the retirement validator. |
| Current a2f `native_resource_admission.py`, SHA256 `1e7ced654a476c1e978c65e6f91b57088a8803917f9dc68ab69481dade8c1462` | Line 558 requires the current request type, a saved wait status and `os.WIFEXITED(wait_status)`. Failure retention stores the exception in process memory; journal rows omit its details. |
| `normal_native_once.py`, SHA256 `26f3c97014bdf8dc5a3337746c919b291f79be41d212e94771f9395cecff773e` | The parent diagnostic payload serializes the exception it caught but omits the watchdog's raw wait status and decoded termination outcome. |

Sources: [Supervisor entry][supervisor] · [Watchdog][watchdog] · [Exact current resource source][resource] · [Current caller][caller]. The older complete-interface resource source has a different image constant; use the a2f source linked here when comparing this attempt.

The inner supervisor is the watchdog's own forked child. This path has an actual direct `waitpid`; it is not a missing-`Popen.wait()` defect. The still-open outer capture session is a separate ownership boundary.

**Inference, not an observed raw result:** reaching this retirement refusal after the verified wait and current typed request strongly suggests the supervisor did not terminate through normal exit. Signal termination is consistent with that path. The actual signal, deadline history and first exception are unpublished. A constructor or later retained exception followed by watchdog termination is a source-supported possible chain, not a proven reconstruction of this attempt.

Published preissue values also do not establish a simple resource or stale-image mismatch: available memory was 30,194,909,184 bytes; disk availability was 108,559,908,864 bytes; overhead plus the 1.5-GiB job was within the 4-GiB HOST pool; the current boot and a2f image bindings matched the named path. These observations precede admission and cannot prove every later predicate passed. There is no evidence-based reason to widen deadlines or change image pins blindly. [Measured projection][projection]

## 4. Native recovery work order

### A. Finish the existing current-attempt diagnosis

Owners: `native_current_binding` and independent `native_binding_review`; Root executes any admitted operation.

Use the already assigned finite read-only owning-context review to retrieve existing records from the exact current operation:

- `native-operation.json`, `registered-loader.json` and `source-manifest.json`, joined to the publisher's recorded hashes (`cf10e689…`, `ed2c9163…`, `d20e9333…`).
- Any actual `GRAPH-WATCHDOG-UNKNOWN-<nonce>.json`, `NATIVE-CLAIM-<nonce>.jsonl`, `NATIVE-SOURCE-FLAGS-<nonce>.jsonl`, caller/terminal diagnostics and command/guest failure records.
- Existing full stdout/stderr with their original capture identities and closure states.
- An original-owner raw supervisor wait result or original child exception/traceback **if actually persisted**.

Use the last valid journal events and actual captures to locate the first established failure boundary. Record absent evidence explicitly. A second wait cannot recover an already consumed wait status, and a proc snapshot does not expose a vanished Python exception. If the original cause remained only in a terminated child's memory, report it as unavailable.

Then derive only the exact failed scope's legitimate cleanup from current ownership and evidence. Retain the original handles, source/runtime flags, native lease and resource charges until positive cleanup is qualified. Never synthesize a success/terminal record from a missing process or absent file. This work does not require a new broad inventory or a replacement collector.

### B. Correct the proven reporting defect

Prepare a minimal private source delta against the exact pins above, with the existing independent reviewer:

1. In both supervisor catch paths, capture the original exception and traceback before reporting. Emit a bounded diagnostic through the existing private operation root and captured stderr, bound to phase, nonce/config identity and supervisor PID/birth. Constructor failure can leave `NativeAdmission` partially initialized: use the already-verified `request` and inherited `root_fd` for available identity/context, and tolerate missing admission attributes. Keep credentials and private capability values out of logs.
2. Keep reporting failures secondary. Preserve the original error, retained handles and existing ownership behavior if writing or formatting diagnostics fails. Reporting must stay finite and must not block the watchdog indefinitely.
3. Immediately after the original exact-child wait, persist returned PID, raw wait status and the decoded normal-exit or signal outcome. Include actual recorded deadline and signal-attempt events separately from inferred causes.
4. Invoke the unchanged strict retirement validator. A signalled wait remains a failed attempt with unresolved custody until its own cleanup is positively established.

This correction makes failures actionable; it does not claim to fix an unobserved admission or application bug. It does not change current live objects or authorize another native issuance.

Minimum useful verification:

| Changed path | Required result |
|---|---|
| Constructor exception | Original cause and traceback become visible before the retained pause; no false release. |
| Post-acquisition exception | Original cause remains visible while all uncertain ownership is retained. |
| Diagnostic write/format failure | Reporting error stays secondary; original error and handles survive. |
| Signalled supervisor wait | Actual raw status and signal are recorded; strict retirement still refuses clean completion. |
| Existing normal-return path | Reuse the qualified contract and check only that the reporting delta preserves its result. |

Do not rerun unchanged compiler, producer, physical-readback or ABI suites for this source-only correction. Do not weaken `WIFEXITED`, add a second reaper, relabel signal termination as success, or expand timeouts without a demonstrated timing cause.

### C. Resume the necessary native work

Once the original attempt is positively cleaned up, Root composes any approved minimal source correction, qualifies only changed bindings and takes fresh admission for the next original operation. Reuse the current coherent image/modules/deployment evidence where identities and contracts are unchanged. If a genuine image/provider change is required, invalidate and rebuild only its dependent proof scope.

Run the current required first-repeat operation once under its existing original contract, capture the application result and first failure directly, and qualify actual restoration. Then advance the prepared time operation. A single alternate-repeat success contributes only its actual coverage; whole `M14-06-02-FUNCTIONAL` still requires the complete original signal-frame, alternate-stack, context, xstate and required error behavior.

## 5. Parallel work aimed at original closure

Use the current six owners. Source derivation and retained-evidence assessment can proceed alongside native recovery; actual execution still shares the measured resource pool.

| Priority and original check | Existing owner | Next concrete deliverable | Completion boundary |
|---|---|---|---|
| P0: native recovery; enables signal and later native work | `native_current_binding` + `native_binding_review` | First established failure boundary, available original wait/cause evidence, exact failed-scope cleanup, minimal reporting delta and review. | Recovery is a prerequisite, not a new accepted original check. |
| P1: `M14-06-04-FUNCTIONAL` | `time_functional_source` | Complete only missing source/stage/manifest/caller/capture/cohort bindings; reuse payload `a98d…`, collector `dc0e…`, three passing oracles and qualified producer cleanup. | Matching selected vDSO/process mappings and time-page/TSC publication preserve all required behavior with genuine providers and actual cleanup. Preparation alone earns zero. |
| P1: `M15-F03-deployed` and `M15-F04-deployed` | `m15_installed_leaf_review` | Match `mcinspect::init_bfd_symbols` and `eclair::setup_symbols` to retained BFD, repeated-DWARF and offline-dump evidence, checking its exact current artifact/profile binding. Name only the actual unmatched runtime-consumer observation, if any. | Installed current artifacts/providers match the admitted runtime and every required source-derived consumer obligation has passing evidence. Loader/file-map evidence alone did not execute main. |
| P2: `M14-I01-E2`, `M14-I01-E3`, relevant supported-default work | `proc_vm_index_fix` | Reuse the qualified Rust/C ABI35 equality and source-ready clone-disabled work; finish genuine UTI DATA/provider ownership and eligible remaining implementation contracts. Root selects/builds the necessary coherent successor. | Every required live implementation has genuine Rust/permitted-assembly ownership; complete replacement and actual final selection/link proof precede C retirement. A tiny bridge or ABI slice does not close the whole condition. |
| P3: `ihk_create_os` within `M15-F05-original-behavior` | `functional_delta_review`; existing `proc_vm_index_fix` reviewer as capacity permits | Finish the prepared owned-FD cases returning 0/7/-5, promoted-int request and one close preserving the captured result. Reuse all qualified destroy cases. | Useful bounded behavior only. Whole F05 still includes the complete supported public/backend obligations and its genuine excluded or unproved domains. |

Sources: [Original conditions and weights][ledger] · [Time prerequisites][time] · [M15 delivery ownership][m15-ownership] · [Actual runtime qualification limits][m15-runtime] · [C4 ownership finding][c4] · [F05 exact scope and next slice][f05].

The current four live project-C symbols are `do_execveat` (1659 bytes), `syscall_execveat_bridge` (12), `util_thread` (1260), and `syscall_util_indicate_clone_disabled_bridge` (34): 2965 bytes total. Derive ordinary source/header/caller/provider contracts as engineering work. Preserve the actual exec/ACK exclusion; do not inflate it into a prohibition on unrelated source work. E2/E3 cannot close from UTI alone. [C4 review][c4]

The private procVM index correction is real useful bug work, but its lower-effect regression does not close `M14-06-05-FUNCTIONAL`: selection into the matching image and required data/error, target-reference and NUMA-lifetime native proof remain. F08's failed readiness cleanup likewise does not establish enabled service behavior. Prioritize the lanes above rather than adding simultaneous service work to the time/F05 owners. [procVM contract][procvm] · [F08 diagnosis][f08]

For prioritization, the ledger's whole time functional leaf is worth about **0.55556 M14 percentage points**; each whole diagnostic deployment leaf about **1.04167 M15 points**; each whole E2/E3 about **2.77778 M14 points**. These are conditional weights, not projected gains or credit for partial work. M14 final acceptance still precedes final M15 acceptance.

## 6. Preserve the baseline and keep work moving

- Reuse unchanged passing source, ABI, provider, build, deployment and runtime evidence at its exact scope. Name the changed input that invalidates a proof before scheduling a rerun.
- Use current HOST CPUs 0,6,7, at most three aggregate light jobs and 4 GiB total including controller/worker overhead. The retained 1.5-GiB/one-job attempt consumes part of that allowance until qualified cleanup; at most two other job slots and only measured residual memory remain.
- Fresh admitted execution preserves the campaign's at-least-26-GiB host availability requirement and existing disk/reservation floors. Native remains one owner on CPUs 2–5 with the existing 12-GiB allocation.
- Use the existing six-owner roster and Sol/MAX assignments without recursive fanout. Source reading and review can run in parallel; shared native mutation and Root composition remain serialized.
- Keep the existing foreground steering cadence. Defer the proposed 25-GiB/seven-job phase and optional mailbox/capacity projects while original requirements have ready work.
- Preserve the exact excluded historical collector worker `01a1c48d-4d96-7cc3-b733-73a97973152f`, turn `01a1ce01-20cf-7e03-9442-f6d521fb8b02`; do not replay, rephrase, reassign or substitute that request.

These resource and ownership rules are the current campaign inputs, not new restrictions introduced by this guide. [Campaign][campaign] · [AGENTS.md][agents]

## 7. Mailbox reporting and proof of progress

The focused instruction was posted to [mailbox PR #3 at 16:14:21 UTC][dispatch]. GitHub readback verified the exact posted body. The [workstation receipt][receipt] confirms receipt at 16:15:19 UTC and queues instruction `source-8ae5dd188c4f6fdc1742e112521122ba3b4e54955af236121ac7cf1b45059692`. That receipt reports **WAITING for controller acceptance**; it does not establish execution or completion.

Use the existing mailbox signs and return one concise record per useful result:

```text
RECEIVED: command ID; owner assignments; current canonical commit
WORKING: original check ID; exact next action; reused evidence
BLOCKED: first concrete failing predicate; actual error; owner; next repair
RESULT: original check ID; evidence/commit; acceptance scope; old -> new score
CUSTODY: retained attempt/charge; qualified cleanup; remaining unknowns
```

If no original check closes, state that directly and name the specific prerequisite removed. If a whole original condition is already satisfied by matching retained evidence, Root should record it promptly without scheduling a green replay. If the evidence is insufficient, return the smallest genuinely missing observation or implementation and continue independent ready work.

The next useful native result is a real first cause or a fully qualified scoped recovery, followed by a matching application outcome and restoration. The next useful milestone result is an original check closed with its whole evidence, not a higher agent count or another preparation percentage.

## References

Evidence links above are pinned to the reviewed commits, except the explicitly live status view. The original acceptance records and exact current source govern their stated scopes.

[campaign]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/CAMPAIGN.md
[agents]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/AGENTS.md
[status]: https://github.com/phoenix-hacking/mckernel/blob/codex/mckernel-control-mailbox/status.txt
[ledger]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/m14-m15-closure-progress.json
[stable]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/development/M14-STABLE-BASELINE.md
[old-m05]: https://github.com/phoenix-hacking/mckernel/blob/0a0eb01ebf7fcf75f342aef7159b15538b5fd2fd/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2/m05-readiness-runtime-failure-2/next-batch-binding-preparation-1/coherent-ten-cycle-preparation-1/accepted-first-binding-1/derivation-bounded-correction-1/release-assembly-1/actual-post-batch-readonly2-1/INDEPENDENT-FORMAL-TEN-CYCLE-AND-LITERAL-M05-ACCEPTANCE.json
[old-m05-binding]: https://github.com/phoenix-hacking/mckernel/blob/0a0eb01ebf7fcf75f342aef7159b15538b5fd2fd/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2/m05-readiness-runtime-failure-2/coherent-successor-preparation-1/BINDING.json
[old-process]: https://github.com/phoenix-hacking/mckernel/blob/858fd77eb237836c434192671b0576f763d85c66/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/independent-actual-native-review-1/INDEPENDENT-ACTUAL-NATIVE-ACCEPTANCE.json
[old-join]: https://github.com/phoenix-hacking/mckernel/blob/858fd77eb237836c434192671b0576f763d85c66/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/normal-entry-preclock-source-2/root-adopted-matching115-process235-entry-2/ROOT-ONCE-ENTRY.JOINED.json
[old-f02]: https://github.com/phoenix-hacking/mckernel/blob/858fd77eb237836c434192671b0576f763d85c66/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/independent-actual-native-review-1/F02-ORIGINAL-FILE-CONTRACT-CLOSURE.json
[old-process-stage]: https://github.com/phoenix-hacking/mckernel/blob/858fd77eb237836c434192671b0576f763d85c66/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/independent-actual-stage-map-review-1/STAGE-AND-MAP-ACCEPTANCE.json
[request]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/native-first-repeat-custody-20261112/REQUEST.json
[failure]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/native-first-repeat-custody-20261112/ACTUAL-CUSTODY-FAILURE.json
[published]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/native-first-repeat-custody-20261112/PUBLISHED-EXACT-INPUTS.json
[publisher]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/native-first-repeat-custody-20261112/ACTUAL-ROOT-PUBLISHER-STDOUT.jsonl
[projection]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/native-first-repeat-custody-20261112/ACTUAL-MEASURED-PROJECTION.json
[supervisor]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/native-admission-debug-20261111/complete-interface-candidate-1/package/supervisor_entry.py
[watchdog]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/native-admission-debug-20261111/complete-interface-candidate-1/package/operation_watchdog.py
[resource]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/native-admission-debug-20261111/a2f-cohort-binding-1/source-candidate/package/native_resource_admission.py
[caller]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/native-first-repeat-custody-20261112/normal_native_once.py
[time]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/m14-time-functional-host-20261112/STATUS.json
[m15-ownership]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/m15-i01-deployed-20261112/WHOLE-REVIEW.json
[m15-runtime]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/m15-i01-deployed-20261112/RUNTIME-QUALIFICATION.json
[c4]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/m14-current-image-20261111/i01-ownership-manifest-e1-1/independent-review/REVIEW.json
[f05]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/m15-f05-public-destroy-observer-20261112/ACTUAL-THREE-CASE-QUALIFICATION.json
[procvm]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/proc-vm-remote-index-20261112/CONTRACT.json
[f08]: https://github.com/phoenix-hacking/mckernel/blob/3f639748089639086c9e09aff326af78e0b7aaeb/docs/verification/m15-f08-readiness-recovery-20261112/DIAGNOSIS.json
[dispatch]: https://github.com/phoenix-hacking/mckernel/pull/3#issuecomment-6829049471
[receipt]: https://github.com/phoenix-hacking/mckernel/pull/3#issuecomment-6829088084
