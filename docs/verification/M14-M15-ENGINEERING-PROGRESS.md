# M14/M15 remaining original deliverables

One goal: a working OS, completed through the unchanged original M14/M15 checks.

**Campaign: RUNNING.** Explicit campaign state supplied by the frontdoor; an open row is not proof of active work.

**112/156 original checks accepted; 44 open.**
Tracker update: `2026-11-15T06:45:56.003819+00:00`. [Original criteria, statuses and full evidence](m14-m15-closure-progress.json) remain the source of truth.

Runtime state update: `2026-11-16T05:33:41.273585+00:00`. Only explicit original-ID assignments can label a row working; unrelated agent activity cannot.

**Every percentage below estimates engineering work remaining. Lower is better.** Ranges are judgments about implementation, integration, functional tests and cleanup still needed. They are not acceptance percentages or a countdown to a completion date. Unknown stays unknown; new failures can increase an estimate.

Estimates assessed: `2026-11-16T05:33:41.293415+00:00`. Shared prerequisites are considered once when assessing a milestone; parent ranges are not an arithmetic average of check counts. See [estimate evidence and reasoning](m14-m15-work-remaining-estimates.json).

| Milestone | Engineering estimate — work remaining | Accepted checks | Open checks | Acceptance |
| --- | ---: | ---: | ---: | --- |
| M14 | 25–50% remaining (low confidence) | 36/54 | 18 | open |
| M15 | 25–55% remaining (low confidence) | 76/102 | 26 | open |

Verified acceptance remains a separate accepted/open decision and exact count. Original criteria, weights and the 156-check denominator remain in the source JSON. The [earlier fixed snapshot](M14-M15-BASELINE-20261116T034323Z.md) used verified checklist percentages; compare these new estimates with the [engineering baseline](M14-M15-ENGINEERING-BASELINE.md), not by subtracting one metric from the other.

Source, test and runtime increments below show progress between acceptances. A completed increment can be useful even while the engineering range remains unchanged. Update estimates when the assessed work changes; keep the latest result and next operation current.

## M14 — 18 open checks

### Every original parent subgoal

| Subgoal / scope | Engineering estimate — work remaining | Acceptance | Open checks | Last completed increment / next operation |
| --- | --- | --- | ---: | --- |
| M14-F01 — Allocator, heap, references, faults/page maintenance, counters/diagnostics | 0% — accepted | accepted | 0 | Original scope accepted. **Next:** Preserve passing scope. |
| M14-F02 — Creation/unwind, VM ranges, PID/TID lifetime, scheduling, inheritance/publication | 0% — accepted | accepted | 0 | Original scope accepted. **Next:** Preserve passing scope. |
| M14-F03 — Generic compute syscalls | 35–65% remaining (low confidence) | open | 7 | Default generic source/link and focused supported slices passed; image built. **Next:** Finish eligible lifetime/ownership repairs and run required matching generic functional/cleanup cases. |
| M14-F04 — Primitives, startup/interrupts, context/TLS, FPU/xstate, diagnostics | 0% — accepted | accepted | 0 | Original scope accepted. **Next:** Preserve passing scope. |
| M14-F05 — Mappings, PTEs, walkers, TLB, usercopy/process-VM supported scope | 0% — accepted | accepted | 0 | Original scope accepted. **Next:** Preserve passing scope. |
| M14-F06 — x86_64 architecture compute syscalls | 30–60% remaining (low confidence) | open | 7 | Qualified image and process-VM repair retained; real own-child Rust consumer now compiled with matched passive provider facts. **Next:** Compile/run the ready process-VM consumer and required architecture cases on an admitted cohort. |
| M14-I01 — Account for all emitted supported compute code, including headers, macros/callbacks and… | 0% — accepted | accepted | 0 | Original scope accepted. **Next:** Preserve passing scope. |
| M14-I02 — Reproducible default source/config/toolchain and matched image/modules | 0% — accepted | accepted | 0 | Original scope accepted. **Next:** Preserve passing scope. |
| M14-I03 — Matching useful applications, process/memory/thread/signal behavior and native… | 35–65% remaining (low confidence) | open | 4 | Matched image/modules and affected account-consumer tests pass. Corrected source publication completed; original installer/keeper/sudo exited zero and its lease is closed. **Next:** Connect the completed published source to the existing native launcher, obtain actual matching one-owner native admission, then run the prepared TIME/application and cleanup cases. |

### Every open original check

Owner means the tracker-recorded responsible role, not a currently running worker. Passing prerequisite/partial evidence does not satisfy the open row.

| Original ID / short name | Recorded state / update | Parent | Engineering estimate — work remaining | Recorded owner | Last completed increment / next missing proof |
| --- | --- | --- | --- | --- | --- |
| `M14-03-01-FUNCTIONAL` — dispatch/offload request abi, initialization, lifetime and exactly-once completion | open / `unknown` | `M14-03-01` | 20–45% remaining (low confidence) | Root integration/compositor; applicable original hold and native/source authorities retain release… | Scoped prerequisite `M14-03-01-DEFAULT`: [ROOT-DEFAULT-COMPLETIONS.json](m14-default-ownership-20261114/ROOT-DEFAULT-COMPLETIONS.json). **Next:** The matched guest/host agree on request layouts and initialized arguments; every admitted request has exactly one terminal completion, and buffers/providers remain live through their final borrow. Required universal dispatch and UTI/drain… |
| `M14-03-02-FUNCTIONAL` — fork/exec/wait/exit/ptrace and final host/process cleanup; held exec work remains excluded | open / `unknown` | `M14-03-02` | 25–55% remaining (low confidence) | Root integration/compositor; applicable original hold and native/source authorities retain release… | Scoped prerequisite `M14-03-02-DEFAULT`: [ROOT-DEFAULT-COMPLETIONS.json](m14-default-ownership-20261114/ROOT-DEFAULT-COMPLETIONS.json). **Next:** The matching image preserves required fork/exec/wait/exit results, initialized child state, ptrace stop/wakeup ordering and exactly-once host/process/reference cleanup on defined success and error paths. Held exec/ACK/TID behavior… |
| `M14-03-03-FUNCTIONAL` — mmap/munmap/mprotect/brk/remap, numa/process-vm and substantive callbacks | open / `unknown` | `M14-03-03` | 40–75% remaining (low confidence) | Root integration/compositor; applicable original hold and native/source authorities retain release… | Scoped prerequisite `M14-03-03-DEFAULT`: [REVIEW.json](m14-current-image-20261111/mprotect-signal-1/qualified-1/whole03-03/qualification-82c82622/REVIEW.json). **Next:** The selected mmap/munmap/mprotect/brk/remap and NUMA/process-VM implementations preserve required range/error results, real writer lock/unlock/mutator ordering, mappings and callback/reference lifetimes. The XPMEM… |
| `M14-03-04-FUNCTIONAL` — signal masks/actions/altstack, futex/robust cleanup, time/wait/wake and restart | open / `unknown` | `M14-03-04` | 25–55% remaining (low confidence) | Root integration/compositor; applicable original hold and native/source authorities retain release… | Scoped prerequisite `M14-03-04-DEFAULT`: [REVIEW.json](m14-current-image-20261111/wait-termination-1/qualified-1/whole04/REVIEW.json). **Next:** Matching-image signal masks/actions and altstack updates preserve requests and aliases; futex/robust cleanup, waits, wakes, interruption/restart and time behavior meet their existing defined contracts with no lost completion, stale… |
| `M14-03-05-FUNCTIONAL` — credentials/limits/scheduling, shm/perf/file wrappers, validation and forwarding | open / `unknown` | `M14-03-05` | 25–50% remaining (low confidence) | Root integration/compositor; applicable original hold and native/source authorities retain release… | Scoped prerequisite `M14-03-05-DEFAULT`: [REVIEW.json](m14-current-image-20261111/perf-supported-default-1/whole-review/REVIEW.json). **Next:** Credential refresh failures publish no partial fields and bind the real error-aware host getter; required limits/scheduling/SHM/file forwarding preserves existing results and ownership. Perf lookup/group/read/copy/close/free uses an… |
| `M14-06-01-FUNCTIONAL` — architecture wrappers, tls/arch_prctl and clone/mmap/shm abi translation | open / `unknown` | `M14-06-01` | 20–45% remaining (low confidence) | Root integration/compositor; applicable original hold and native/source authorities retain release… | Scoped prerequisite `M14-06-01-DEFAULT`: [REVIEW.json](m14-current-image-20261111/joint-providers-1/fork-default-whole-review-p03-max-1/REVIEW.json). **Next:** The supported x86_64 TLS/arch_prctl and clone/mmap/SHM wrappers agree with the selected real ABI and preserve values, results and required context behavior in the matching image. |
| `M14-06-02-FUNCTIONAL` — signal/rt_sigreturn frames, alternate stack, context and xstate restoration | open / `unknown` | `M14-06-02` | 30–60% remaining (low confidence) | Root integration/compositor; applicable original hold and native/source authorities retain release… | Scoped prerequisite `M14-06-02-DEFAULT`: [REVIEW.json](m14-f06-default-leaves-20261111/REVIEW.json). **Next:** Signal/rt_sigreturn paths restore the selected signal frame, alternate stack, register context and configured xstate with the required normal/error behavior and genuine providers on the matching image. |
| `M14-06-03-FUNCTIONAL` — ptrace registers/debug state and correct stop/wakeup/event ordering | open / `unknown` | `M14-06-03` | 25–50% remaining (low confidence) | Root integration/compositor; applicable original hold and native/source authorities retain release… | Scoped prerequisite `M14-06-03-DEFAULT`: [REVIEW.json](m14-current-image-20261111/joint-providers-1/f06-ptrace-default-whole-review-p04tests-max-1/REVIEW.json). **Next:** Both supported regsets and directions retain whole-eight-byte length validation, configured xstate/copy results, and required register/debug-state plus stop/wakeup/event ordering on the matching image; unavailable HOST ptrace control is… |
| `M14-06-04-FUNCTIONAL` — vdso/process mappings and time-page/tsc publication | open / `unknown` | `M14-06-04` | 20–45% remaining (low confidence) | Root integration/compositor; applicable original hold and native/source authorities retain release… | Scoped prerequisite `M14-06-04-DEFAULT`: [REVIEW.json](m14-current-image-20261111/time-bridge-1/time-bridge-image-review-p03-max-1/qualification-1/REVIEW.json). **Next:** The selected vDSO/process mappings and time-page/TSC publication have genuine provider ownership and preserve required mapping/publication/time behavior on the matching image. |
| `M14-06-05-FUNCTIONAL` — cross-process memory/move-pages, target references and numa callback lifetime | working / open / `2026-11-16T05:31:17.506088+00:00` | `M14-06-05` | 25–55% remaining (low confidence) | m14_generic: new typed oracle; Root: matching stage/native execution | Own-child Rust consumer compiled:4349416B/252ba835, matched ELF/provider facts and all original wait/capture/container closure qualified; only new1.5GiB family retired. — [RESULT.json](m14-06-05-own-process-consumer-20261116/RESULT.json). **Next:** Validate only new strict stdout oracle, then stage exact compiled consumer with retained matching providers and run actual admitted process-VM/move-pages cases plus full reference/callback restoration. |
| `M14-F03-ACCEPT` — Accept original M14-F03 scope | open / `unknown` | `M14-F03` | 35–65% remaining (low confidence) | Saved Root integration/review owner | Scoped prerequisite `M14-F03-DEFAULT`: [ROOT-NEXT-THREE-COMPLETIONS.json](m14-default-ownership-20261114/ROOT-NEXT-THREE-COMPLETIONS.json). **Next:** Close `M14-F03-FUNCTIONAL`, `M14-03-01`, `M14-03-02`, `M14-03-03`, `M14-03-04`, `M14-03-05`; then Root explicitly accepts the matching scope. |
| `M14-F03-FUNCTIONAL` — generic dispatch/process/MM/signal/credential/file syscall behavior and lifetime | open / `unknown` | `M14-F03` | 35–65% remaining (low confidence) | Root sole compositor; original service/hold authority alone may release held scope | Scoped prerequisite `M14-F03-DEFAULT`: [ROOT-NEXT-THREE-COMPLETIONS.json](m14-default-ownership-20261114/ROOT-NEXT-THREE-COMPLETIONS.json). **Next:** Qualify generic dispatch/process/MM/signal/credential/file syscall behavior and lifetime on the matching admissible coherent image; exact matching proof has no unresolved required owner, ABI/provider obligation, unexplained failure or… |
| `M14-F06-ACCEPT` — Accept original M14-F06 scope | open / `unknown` | `M14-F06` | 30–60% remaining (low confidence) | Saved Root integration/review owner | Scoped prerequisite `M14-F06-DEFAULT`: [REVIEW.json](m14-current-image-20261111/f06-whole-default-1/f06-whole-default-review-sourceacq-max-1/REVIEW.json). **Next:** Close `M14-F06-FUNCTIONAL`, `M14-06-01`, `M14-06-02`, `M14-06-03`, `M14-06-04`, `M14-06-05`; then Root explicitly accepts the matching scope. |
| `M14-F06-FUNCTIONAL` — architecture ABI, signal/context/xstate, ptrace, mappings/time and cross-process-memory… | open / `unknown` | `M14-F06` | 30–60% remaining (low confidence) | Root sole compositor; original source/service and native admission authorities retain their holds | Scoped prerequisite `M14-F06-DEFAULT`: [REVIEW.json](m14-current-image-20261111/f06-whole-default-1/f06-whole-default-review-sourceacq-max-1/REVIEW.json). **Next:** Qualify architecture ABI, signal/context/xstate, ptrace, mappings/time and cross-process-memory behavior on the matching admissible coherent image; exact matching proof has no unresolved required owner, ABI/provider obligation,… |
| `M14-I03-ACCEPT` — Accept original M14-I03 scope | open / `unknown` | `M14-I03` | 35–65% remaining (low confidence) | Saved Root integration/review owner | No passing scope recorded for this check. **Next:** Close `M14-I03-E1`, `M14-I03-E2`, `M14-I03-E3`; then Root explicitly accepts the matching scope. |
| `M14-I03-E1` — Obtain exact one-owner native/source-view/current-free admission for the coherent matched… | working / open / `2026-11-16T05:33:41.293415+00:00` | `M14-I03` | 25–55% remaining (low confidence) | Root: native integration/execution; TimeSource: existing-frontdoor source/launcher connection | Four affected consumer methods and the corrected comparison regression pass. Source publication499 completed with original installer/keeper/sudo exit0 and publication… — [RESULT.json](m14-i03-final-account-consumer-20261116/RESULT.json), [ARTIFACTS.json](m14-m15-build-reuse-20261115/ARTIFACTS.json), [QUALIFICATION.json](/home/holden/mckernel-work/m14-i03-final-account-consumer-repair-20261116-1/root-working-inputs-2/ROOT-ACTUAL-PUBLICATION-499-SUCCESS-1/independent-actual-publication-and-family-qualification-1/QUALIFICATION.json). **Next:** Reuse the completed publication499 and unchanged image/modules/stage. Finish TimeSource source-cut/loader connection, obtain actual matching one-owner native admission, then run prepared TIME and owned restoration. No failed nonce replay… |
| `M14-I03-E2` — Run matching useful applications and required process/memory/thread/signal behavior on that… | open / `unknown` | `M14-I03` | 40–70% remaining (low confidence) | Root integration owner; original hold/SDK/source/native authorities for each actual release | No passing scope recorded for this check. **Next:** Run matching useful applications and required process/memory/thread/signal behavior on that cohort; exact matching proof has no unresolved required owner, ABI/provider obligation, unexplained failure or unreviewed project-C… |
| `M14-I03-E3` — Prove native lifecycle and resource restoration with exact live/retained owners and outcomes;… | open / `unknown` | `M14-I03` | 40–70% remaining (low confidence) | Root integration owner; original hold/SDK/source/native authorities for each actual release | No passing scope recorded for this check. **Next:** Prove native lifecycle and resource restoration with exact live/retained owners and outcomes; preserve all historical UNKNOWNs and then accept M14 only when original file/integration requirements pass; exact matching proof has no… |

## M15 — 26 open checks

### Every original parent subgoal

| Subgoal / scope | Engineering estimate — work remaining | Acceptance | Open checks | Last completed increment / next operation |
| --- | --- | --- | ---: | --- |
| M15-F01 — Accepted original MM compatibility wrappers | 0% — accepted | accepted | 0 | Original scope accepted. **Next:** Preserve passing scope. |
| M15-F02 — Rust executor qualification | 25–55% remaining (low confidence) | open | 3 | Selected/deployed executor and 78-word ABI qualified; existing non-ELF loader proof preserved. **Next:** Supply real matching GET_CREDV/device input and run the successful loader/application lifecycle. |
| M15-F03 — Rust mcinspect diagnostic qualification | 15–35% remaining (low confidence) | open | 2 | mcinspect source, host link, ABI and focused/default behavior passed. **Next:** Run the installed mcinspect consumer on the matching admitted runtime. |
| M15-F04 — Rust eclair diagnostic qualification | 15–35% remaining (low confidence) | open | 2 | eclair source, host link, ABI and focused/default behavior passed. **Next:** Run the installed eclair consumer on the matching admitted runtime. |
| M15-F05 — Rust IHK library qualification | 25–55% remaining (low confidence) | open | 3 | Changed IHK archive/DSO built; public providers and focused behavior qualified. **Next:** Run original balanced/zero/backend behavior and prove installed dependencies plus restoration. |
| M15-F06 — Rust ihkconfig CLI qualification | 20–45% remaining (low confidence) | open | 3 | ihkconfig source, installed artifact and focused behavior qualified. **Next:** Run required real-device ihkconfig commands and restoring lifecycle. |
| M15-F07 — Rust ihkosctl CLI qualification | 20–45% remaining (low confidence) | open | 3 | ihkosctl changed/installed artifact and focused behavior qualified. **Next:** Run required real-device ihkosctl commands and restoring lifecycle. |
| M15-F08 — Rust ihkmond supervisor qualification | 25–50% remaining (low confidence) | open | 3 | Changed monitor built; passive checks/private stage qualified. **Next:** Run the installed monitor against genuine events/service and verify error/stop restoration. |
| M15-I01 — Complete project-runtime ownership manifest | 0% — accepted | accepted | 0 | Original scope accepted. **Next:** Preserve passing scope. |
| M15-I02 — Three delivered Linux-loadable Rust/assembly modules | 0% — accepted | accepted | 0 | Original scope accepted. **Next:** Preserve passing scope. |
| M15-I03 — Reproducible Rust userspace and dependency closure | 0% — accepted | accepted | 0 | Original scope accepted. **Next:** Preserve passing scope. |
| M15-I04 — Matched application and restoring lifecycle qualification | 40–70% remaining (low confidence) | open | 7 | Matched artifacts and project ownership/dependency prerequisites qualified. **Next:** Reuse the matched native cohort for full applications, module/MM and restoration, after M14 acceptance. |

### Every open original check

Owner means the tracker-recorded responsible role, not a currently running worker. Passing prerequisite/partial evidence does not satisfy the open row.

| Original ID / short name | Recorded state / update | Parent | Engineering estimate — work remaining | Recorded owner | Last completed increment / next missing proof |
| --- | --- | --- | --- | --- | --- |
| `M15-F02-ACCEPT` — Accept original M15-F02 scope | open / `unknown` | `M15-F02` | 25–55% remaining (low confidence) | Saved Root integration/review owner | Scoped prerequisite `M15-F02-deployed`: [RUNTIME-QUALIFICATION.json](m15-i01-deployed-20261112/RUNTIME-QUALIFICATION.json). **Next:** Close `M15-F02-complete-ABI-behavior`, `M15-F02-native`; then Root explicitly accepts the matching scope. |
| `M15-F02-complete-ABI-behavior` — Complete original executor behavior, ABI and provider ownership qualification | open / `unknown` | `M15-F02` | 25–50% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Tracker records actual nonELF loader Q0a7fe/Root0ef901; matched GET_CREDV success remains parked. Original 78-word ABI stays qualified — [m14-m15-closure-progress.json](m14-m15-closure-progress.json), [QUALIFICATION.json](m15-executor-abi-20261111/descriptor-cpuset-78word-1/independent-review/actual-result-1/QUALIFICATION.json). **Next:** Supply the real matched mcctrl/device GET_CREDV input, then qualify successful loader publication/cleanup; preserve every other unmatched original behavior obligation. |
| `M15-F02-native` — Matching application/offload/process and resource-restoring native behavior | open / `unknown` | `M15-F02` | 35–65% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Scoped prerequisite `M15-F02-deployed`: [RUNTIME-QUALIFICATION.json](m15-i01-deployed-20261112/RUNTIME-QUALIFICATION.json). **Next:** Reviewed original application/offload/process/lifecycle scenario inventory has matching admitted native results and observed cleanup/resource restoration; exact scenario/entrypoint bindings remain absent. |
| `M15-F03-ACCEPT` — Accept original M15-F03 scope | open / `unknown` | `M15-F03` | 15–35% remaining (low confidence) | Saved Root integration/review owner | Scoped prerequisite `M15-F03-original-default`: [REPORT.json](m15-diagnostic-original-default-20261110/mcinspect/zstd/output-1/REPORT.json). **Next:** Close `M15-F03-deployed`; then Root explicitly accepts the matching scope. |
| `M15-F03-deployed` — Delivered/installed ownership and matching runtime consumer qualification | open / `unknown` | `M15-F03` | 15–35% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Scoped prerequisite `M15-F03-original-default`: [REPORT.json](m15-diagnostic-original-default-20261110/mcinspect/zstd/output-1/REPORT.json). **Next:** Installed mcinspect artifact/providers match the admitted image/runtime, and every required source-derived runtime-consumer obligation has matching passing evidence. |
| `M15-F04-ACCEPT` — Accept original M15-F04 scope | open / `unknown` | `M15-F04` | 15–35% remaining (low confidence) | Saved Root integration/review owner | Scoped prerequisite `M15-F04-original-default`: [REPORT.json](m15-diagnostic-original-default-20261110/shared-provider/output/REPORT.json). **Next:** Close `M15-F04-deployed`; then Root explicitly accepts the matching scope. |
| `M15-F04-deployed` — Delivered/installed ownership and matching runtime consumer qualification | open / `unknown` | `M15-F04` | 15–35% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Scoped prerequisite `M15-F04-original-default`: [REPORT.json](m15-diagnostic-original-default-20261110/shared-provider/output/REPORT.json). **Next:** Installed eclair artifact/providers match the admitted image/runtime, and every required source-derived runtime-consumer obligation has matching passing evidence. |
| `M15-F05-ACCEPT` — Accept original M15-F05 scope | open / `unknown` | `M15-F05` | 25–55% remaining (low confidence) | Saved Root integration/review owner | Scoped prerequisite `M15-F05-changed-library`: [m15-retained-c-dump-owner-results-20261109.json](m15-retained-c-dump-owner-results-20261109.json). **Next:** Close `M15-F05-original-behavior`, `M15-F05-deployed-native`; then Root explicitly accepts the matching scope. |
| `M15-F05-deployed-native` — Matched installed ABI/library dependencies and resource-restoring native lifecycle | open / `unknown` | `M15-F05` | 25–50% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Scoped prerequisite `M15-F05-changed-library`: [m15-retained-c-dump-owner-results-20261109.json](m15-retained-c-dump-owner-results-20261109.json). **Next:** Actual installed library/public ABI/dependency identities match the admitted cohort and required original resource-restoring native scenarios pass; exact full scenario/operation bindings remain unestablished. |
| `M15-F05-original-behavior` — Complete original supported public behavior and backend/provider qualification | open / `unknown` | `M15-F05` | 30–55% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Changed library emission passed with actual archive/DSO and provider qualification — [ARTIFACTS.json](m14-m15-build-reuse-20261115/ARTIFACTS.json). **Next:** Qualify real balanced-success, zero-node/compensation and backend/restoration behavior on the matching changed library; retain the full original public-behavior obligation. |
| `M15-F06-ACCEPT` — Accept original M15-F06 scope | open / `unknown` | `M15-F06` | 20–45% remaining (low confidence) | Saved Root integration/review owner | Scoped prerequisite `M15-F06-installed`: [RUNTIME-QUALIFICATION.json](m15-i01-deployed-20261112/RUNTIME-QUALIFICATION.json). **Next:** Close `M15-F06-device-behavior`, `M15-F06-native`; then Root explicitly accepts the matching scope. |
| `M15-F06-device-behavior` — Complete required supported/default real-device command behavior | open / `unknown` | `M15-F06` | 20–45% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Scoped prerequisite `M15-F06-installed`: [RUNTIME-QUALIFICATION.json](m15-i01-deployed-20261112/RUNTIME-QUALIFICATION.json). **Next:** Derive the complete required supported/default ihkconfig real-device command behavior obligations from its selected source and public contracts, then qualify every required observation using exact admitted provider/operation bindings. |
| `M15-F06-native` — Applicable matching native/resource-restoring command lifecycle | open / `unknown` | `M15-F06` | 25–50% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Scoped prerequisite `M15-F06-installed`: [RUNTIME-QUALIFICATION.json](m15-i01-deployed-20261112/RUNTIME-QUALIFICATION.json). **Next:** Original required ihkconfig native command/error/resource-restoring lifecycle scenario inventory has matching passing admitted results and restored ownership. |
| `M15-F07-ACCEPT` — Accept original M15-F07 scope | open / `unknown` | `M15-F07` | 20–45% remaining (low confidence) | Saved Root integration/review owner | Scoped prerequisite `M15-F07-installed`: [RUNTIME-QUALIFICATION.json](m15-i01-deployed-20261112/RUNTIME-QUALIFICATION.json). **Next:** Close `M15-F07-device-behavior`, `M15-F07-native`; then Root explicitly accepts the matching scope. |
| `M15-F07-device-behavior` — Complete required supported/default real-device command behavior | open / `unknown` | `M15-F07` | 20–45% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Scoped prerequisite `M15-F07-installed`: [RUNTIME-QUALIFICATION.json](m15-i01-deployed-20261112/RUNTIME-QUALIFICATION.json). **Next:** Derive the complete required supported/default ihkosctl real-device command behavior obligations from its selected source and public contracts, then qualify every required observation using exact admitted provider/operation bindings. |
| `M15-F07-native` — Applicable matching native/resource-restoring command lifecycle | open / `unknown` | `M15-F07` | 25–50% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Scoped prerequisite `M15-F07-installed`: [RUNTIME-QUALIFICATION.json](m15-i01-deployed-20261112/RUNTIME-QUALIFICATION.json). **Next:** Original required ihkosctl native command/error/resource-restoring lifecycle scenario inventory has matching passing admitted results and restored ownership. |
| `M15-F08-ACCEPT` — Accept original M15-F08 scope | open / `unknown` | `M15-F08` | 25–50% remaining (low confidence) | Saved Root integration/review owner | Scoped prerequisite `M15-F08-active-monitor`: [m15-active-monitor-results-20261107.json](m15-active-monitor-results-20261107.json). **Next:** Close `M15-F08-installed-service`, `M15-F08-native`; then Root explicitly accepts the matching scope. |
| `M15-F08-installed-service` — Required installed daemon/service/udev and actual IHK event/kmsg/hung-up qualification | open / `unknown` | `M15-F08` | 25–50% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Changed monitor normal emission/passive checks/private stage qualified at its recorded durability limits — [QUALIFIED-INCREMENT.json](m15-f08-changed-monitor-build-20261114/QUALIFIED-INCREMENT.json). **Next:** Bind genuine installed IHK providers/events/service and qualify required active/hung-up/error/stop/restoration behavior on matching inputs. |
| `M15-F08-native` — Matched active native lifecycle and resource restoration | open / `unknown` | `M15-F08` | 30–55% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | Scoped prerequisite `M15-F08-active-monitor`: [m15-active-monitor-results-20261107.json](m15-active-monitor-results-20261107.json). **Next:** Original matching active-monitor startup/stop/error/native lifecycle inventory is satisfied with actual admitted devices/providers and measured resource restoration. |
| `M15-I04-ACCEPT` — Accept original M15-I04 scope | open / `unknown` | `M15-I04` | 40–70% remaining (low confidence) | Saved Root integration/review owner | No passing scope recorded for this check. **Next:** Close `M15-I04-native-admission`, `M15-I04-cohort`, `M15-I04-applications`, `M15-I04-module-MM`, `M15-I04-restoration`, `M15-I04-acceptance`; then Root explicitly accepts the matching scope. |
| `M15-I04-acceptance` — Original integration review after M14 acceptance | open / `unknown` | `M15-I04` | 40–70% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | No passing scope recorded for this check. **Next:** M14 is genuinely accepted first, original M15 F/I obligations have required closure evidence, and saved Root records original M15 integration acceptance. |
| `M15-I04-applications` — Required useful matching application behavior | open / `unknown` | `M15-I04` | 40–70% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | No passing scope recorded for this check. **Next:** Derive the original useful-application scenarios and required observations from existing supported system contracts, then satisfy each with matching admitted cohort results; no new application quota is invented. |
| `M15-I04-cohort` — Exact matched image/modules/executors/libraries/tools binding | open / `unknown` | `M15-I04` | 20–45% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | No passing scope recorded for this check. **Next:** Exact admitted compute image, three modules, executor, library and installed tool identities are recorded as one coherent supported cohort. |
| `M15-I04-module-MM` — Required matched load/unload and MM lifecycle behavior | open / `unknown` | `M15-I04` | 30–60% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | No passing scope recorded for this check. **Next:** Derive required load/unload and MM lifecycle obligations from actual supported module/consumer contracts, then satisfy every required behavior and ordering observation on the matching admitted cohort. |
| `M15-I04-native-admission` — Actual reviewed original native/source/current-free admission | open / `unknown` | `M15-I04` | 35–65% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | No passing scope recorded for this check. **Next:** Original native authority supplies actual reviewed one-shot operation/current-free/source-custody bindings and reconciles the original owner without retiring UNKNOWN charges by assumption. |
| `M15-I04-restoration` — Required actual native shutdown/error resource restoration | open / `unknown` | `M15-I04` | 40–70% remaining (low confidence) | Saved Root integration owner; original source/SDK/native authorities retain their admissions | No passing scope recorded for this check. **Next:** Derive required shutdown/error/restoring-lifecycle obligations from the actual supported sources and contracts, then demonstrate native before/after ownership restoration with all owned operations/waits reconciled. |

## Smaller engineering increments

Checked boxes show the stated increment only. They are not equally weighted effort units and do not change original acceptance. Pending boxes name the concrete work still needed.

**`M14-06-05-FUNCTIONAL`: 25–55% remaining (low confidence).**

- [x] Prepare the real own-child process-VM/move-pages Rust consumer; source only. — [main.rs](/home/holden/mckernel-work/m14-06-05-own-process-consumer-20261116/main.rs)

- [x] Compile and qualify the actual userspace consumer and own lifecycle; runtime ABI remains separately unproved. — [RESULT.json](m14-06-05-own-process-consumer-20261116/RESULT.json)

- [ ] Run the original read/write/error/target-exit observations.

- [ ] Complete required concurrent target-reference and NUMA callback lifetime/restoration proof.

**`M14-I03-E1`: 25–55% remaining (low confidence).**

- [x] Produce and qualify the coherent image and paired modules. — [ARTIFACTS.json](m14-m15-build-reuse-20261115/ARTIFACTS.json)

- [x] Implement bounded account-consumer completion and refusal handling. — [RESULT.json](m14-i03-final-account-consumer-20261116/RESULT.json)

- [x] Correct the actual Python3.8 interpreter binding. — [RESULT.json](m14-i03-final-account-consumer-20261116/RESULT.json)

- [x] Run the four affected controller-consumer integration methods: PASS, 0.627 seconds. — [RESULT.json](m14-i03-final-account-consumer-20261116/RESULT.json)

- [x] Complete the corrected source publication/install: original installer, keeper and sudo exit zero; own publication lease closed. No native authority inferred. — [QUALIFICATION.json](/home/holden/mckernel-work/m14-i03-final-account-consumer-repair-20261116-1/root-working-inputs-2/ROOT-ACTUAL-PUBLICATION-499-SUCCESS-1/independent-actual-publication-and-family-qualification-1/QUALIFICATION.json)

- [ ] Connect published source and its source-cut commitments to the existing same-Root native launcher.

- [ ] Obtain actual one-owner source/SDK/lease/current-free native admission.

**`M14-I03-E2`: 40–70% remaining (low confidence).**

- [ ] Run useful applications on the exact admitted image/module cohort.

- [ ] Demonstrate required process/thread and signal behavior.

- [ ] Demonstrate required memory/NUMA behavior and match each required observation.

**`M14-I03-E3`: 40–70% remaining (low confidence).**

- [ ] Observe matching native shutdown/error and terminal lifecycle.

- [ ] Prove CPU/RAM and descriptor/reference/callback restoration with positive own-family evidence.

- [ ] Join the required original functional results and explicitly accept the matching scope.

**`M15-F05-original-behavior`: 30–55% remaining (low confidence).**

- [x] Build and qualify the changed archive/DSO and public providers. — [ARTIFACTS.json](m14-m15-build-reuse-20261115/ARTIFACTS.json)

- [ ] Run real balanced full-success and arithmetic behavior.

- [ ] Run required zero-node/zero-compensation and backend behavior.

- [ ] Demonstrate original ownership and resource restoration across required cases.

**`M15-F08-installed-service`: 25–50% remaining (low confidence).**

- [x] Build the changed monitor and qualify passive/private-stage behavior. — [QUALIFIED-INCREMENT.json](m15-f08-changed-monitor-build-20261114/QUALIFIED-INCREMENT.json)

- [ ] Bind the genuine installed service and IHK event/kmsg/hung-up providers.

- [ ] Run required active/error/stop behavior and prove cleanup/restoration.

## Stop and resume

```sh
python3 -B scripts/m14_m15.py stop
```

This stops new campaign/child dispatch and requests active work to stop through the existing bounded shutdown. It preserves the saved goal, evidence, finite credit ledger and unresolved owners. A stop request or STOPPED label is not proof of Docker/native/workload cleanup or OS completion.

Only an explicit later user start/resume restarts campaign dispatch. M14 final acceptance precedes M15 final acceptance. After both, checkpoint and stop the campaign; do not mark the larger working-OS goal complete without its remaining original requirements.

Regenerate/print **every open row** with `python3 -B scripts/m14_m15.py status` (or `python3 -B scripts/m14_m15_progress.py status`). Each assignment must name an original ID, the concrete missing proof/next functional increment, and its expected result. Record a completed engineering step only with its actual evidence; original acceptance changes only through the canonical tracker.
