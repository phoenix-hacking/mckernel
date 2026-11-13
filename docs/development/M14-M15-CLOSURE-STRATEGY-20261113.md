# M14/M15 Closure Strategy

**Prepared:** November 13, 2026, America/Boise.  
**Evidence baseline:** canonical commit 2c59943d64ef9d3d323cda5063f195b27856dec8; current campaign updated 09:34 UTC / 02:34 Boise.  
**Purpose:** turn retained implementation and qualification work into small, verified closures of the original M14 and M15 requirements.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is a dated strategy reference. [CAMPAIGN.md](../../CAMPAIGN.md) remains the sole active plan, current-status record and handoff. The [canonical ledger](../verification/m14-m15-closure-progress.json) remains the only completion ledger. Root reconciles this strategy with current evidence before adopting the next actions and skips any step already satisfied by matching current receipts; this document does not create a second live queue or alter acceptance criteria.

## 1. The decision

Prioritize completed original requirements through three coordinated kinds of work:

1. Restore the existing execution path by finishing the actual failed operation's lifecycle.
2. Consume the already compiled, staged and reviewed work in real functional runs.
3. Continue the remaining generic Rust implementation and provider ownership work in parallel, one bounded change at a time.

**Reuse is the default.** Before a rebuild, identify the actual changed input, affected target and reason the retained artifact cannot be used. A new Git commit, documentation update, elapsed time or different test selection is not by itself a rebuild reason. Reuse passing results at their demonstrated source/configuration/toolchain/provider/cohort scope. Revalidate only dependencies that actually changed.

A useful implementation increment can be smaller than a counted requirement. Report that increment honestly, then continue until the original requirement's complete condition is satisfied. Do not add new counted microtasks or relax a criterion to increase the percentage.

## 2. Starting position and why progress has been slow

At the pinned evidence baseline:

| Measure | Verified state |
| --- | --- |
| M14 checklist | 70.00%; 4/6 original file gates and 1/3 integration gates accepted |
| M15 checklist | 74.59%; 1/8 original file gates and 2/4 integration gates accepted |
| Counted evidence tasks | 105/156 verified; 51 open |
| Open tasks by milestone | 24 M14; 27 M15 |
| Open tasks by declared execution profile | 29 native, 9 ordinary HOST, 13 retained-evidence acceptance reviews |

These categories describe the existing ledger. They do not mean that 13 acceptance reviews are immediately ready, or that every HOST-labelled task can finish without native evidence. The ledger is older than the latest campaign header; it must not be used to infer current resource availability. [1]

The immediate bottleneck is failed publication family **30017/a2d**. It retains an exclusive 2 GiB charge and unresolved original process/wait, lease, descriptor and capture state. The new read-only diagnostic completed its own operation successfully, received independent qualification, and had its own 256 MiB charge retired. Those results are complete and reusable; they do not release the original failed family. The prepared UTI compile needs 2 GiB; two 2 GiB families plus controller/worker overhead cannot fit the current 4 GiB HOST budget. [2]

The second bottleneck is repeated disagreement between the prepared source and the source actually consumed by publication. The latest concrete correction changes three graph-size values from 15,713 to 15,724 bytes. That correction is reviewed at source scope. The saved runtime records do not yet prove which particular membership operands caused the failure. Recovery and a genuinely corrected operation are still required. [3]

The project also has substantial retained work: the c964/a2f compute-image cohort, f133 staging, matching module evidence, the UTI ABI/provider baseline, TLS/time artifacts, seven compiled and staged wrapper cases, and reviewed installed runtime components. Repeating their unchanged build or qualification steps would delay the missing runtime results. The existing stable-baseline guide documents retention; current CAMPAIGN controls which code publication is actually current. [2][4][5]

## 3. What counts as a chip

Use the following distinctions in every checkpoint:

| Result | Report it as | When it earns original checklist credit |
| --- | --- | --- |
| Reviewed source change | Implementation or repair completed at source scope | Only if the original task itself is completely satisfied by that evidence |
| New object with a proven caller/provider link | Changed compile/use obligation completed | Not automatically full default-image ownership or functional acceptance |
| Successful publication and readback | Execution prerequisite completed | Only within an original task's stated condition; no native behavior inference |
| Passing functional scenario and cleanup | A named runtime obligation completed | When all remaining obligations of its original task are covered on the matching cohort |
| Complete original task or gate | Original ID closed with matching evidence | Root records explicit acceptance in the existing ledger |

For example, the UTI initializer moves twelve field writes into Rust. It is meaningful code progress, but does not finish universal dispatch, the rest of util_thread, complete provider ownership, ACK/lifetime behavior or the final image. Similarly, a passing TLS case does not alone close the full TLS/clone/mmap/SHM requirement. [1][6]

## 4. Immediate work queue

The numbers below are execution priorities, not new ledger tasks. Keep existing frozen author/reviewer identities and healthy turns.

| Priority | Concrete next result | Owner / dependency | Exit condition |
| --- | --- | --- | --- |
| 0A | Decide the remaining original M15-I02 acceptance condition | An available independent original-gate reviewer; Root records the decision | Either a supported full-gate acceptance recommendation or the exact original clause and missing observation. Reuse the four verified children; no rebuild |
| Completed — reuse | New diagnostic qualification and scoped retirement | Existing independent review and Root receipt | Its own 256 MiB charge is already retired. Reuse saved bytes and results; original 30017 remains separate |
| 1 | Resolve the original failed 30017 family | NativeCurrent author, NativeBinding reviewer, Root executor | Actual supported disposition, original owning waits, SUDO/process/FD/capture/lease closure, independent qualification and original 2 GiB retirement |
| 2 | Complete one minimum corrected publication | Same critical-path pair and Root | Reviewed three-value correction and necessary dependent bindings, real completed publication, physical NEW30 qualification, both CORE/provider bindings |
| 3 | Run the already designated first native case | Root sole native executor | Actual signal.alternate-repeat result on c964/a2f/f133, with its required lifecycle/restoration |
| 4 | Complete the first fully coverable M14 functional row | Existing case owner plus independent result review | Whole original M14-06-04-FUNCTIONAL or M14-06-01-FUNCTIONAL condition demonstrated, not just one prerequisite |
| Parallel preparation / next admissible HOST slot | Compile and prove use of the changed UTI pair | Proc; distinct review; actual fit after exclusive-family release | Changed production C and Rust objects plus focused unique helper definition/reference/provider-use evidence |
| Parallel preparation / next admissible HOST slot | Finish F08 changed-data correction/review, then execute enabled-worker startup/shutdown | TimeSource author, FunctionalDelta reviewer, Root admission | Genuine size bindings and dependent literals pass review; actual run proves both worker identities, normal stop/joins and complete owned cleanup; no event credit |
| Next matched native window | Consume installed diagnostic and device obligations | Assigned M15 owner, one legitimate native operator | Actual original F03/F04/F05/F06/F07/F08/I04 evidence at each scenario's supported scope |

Publication retains priority when it is ready and properly admitted because it unlocks many native rows. A temporarily unavailable publication input should not prevent an independently admitted HOST result after the failed family's exclusivity is genuinely resolved. A ready HOST task must not be held merely for an unrelated native application's success.

### 4.1 Why M15-I02 gets a bounded review now

All four immediate technical children of **M15-I02** are already verified: source/kernel/Kbuild/toolchain bindings; module ownership; ABI/import/modpost qualification; matching delivered artifacts. Only **M15-I02-ACCEPT** remains open.

However, the saved matching-artifact review explicitly leaves the parent gate's original native-validation language unassessed. Four green children therefore justify an immediate acceptance review, not automatic acceptance. The reviewer must inspect the retained original row/snapshot and decide the actual requirement. If observed loadability is required, consume applicable module/kernel/boot/cleanup observations from the already planned first native operation; do not invent another module probe. If a different genuine condition is missing, name it exactly and assign its supplying owner. [1][7][8]

The original private snapshot is not present at the inspected public paths. Root already has its retained source; retrieving that exact original clause is the bounded input to this review. It is not a request to write a new criterion. M14 must precede final M15 acceptance; individually supported M15 gate decisions can be reviewed earlier, as already accepted I01/I03 demonstrate.

### 4.2 Recover the current failure without restarting the investigation

Reuse the now-qualified capture and its completed scoped retirement. Use the already captured bytes for the minimum needed projection of the seven observation-error labels and relevant process/FD/socket/lock/lease/capture facts. The saved-only projection is prepared and with its existing independent reviewer. Do not repeat a live capture or broad inventory simply because its result is inconvenient to read.

Use the existing supported owning-context route for original disposition. A missing process, expired deadline, finished diagnostic or heartbeat is not a release receipt. Preserve the original failure and actual unknowns. Recovery completes only when the original family has its required positive disposition, final owning waits/captures and lease/resource qualification.

This is one critical-path task with an author and independent reviewer. Its scope should end at original retirement; it should not grow into a new retention, monitoring, scheduler or recovery framework. [2]

### 4.3 Correct publication once, then consume its result

Use the approved three scalar replacements and only necessary final source-reference/hash bindings. Fold their final consistency check into the existing review; do not add a new review layer or repeat unchanged qualification. Retain the genuine owner reference, helper resolution and final-byte argv/profile relationships already established.

After the real operation completes, obtain its actual closure and physical 30-file readback and bind both consuming namespaces to that actual generation. Then advance the existing first native case. An unchanged code generation should remain reusable across later requests that differ only in the admitted case manifest and source rows.

The seven wrapper cases already share reviewed provider modules. Their shared generation can be reused after it is genuinely published and matched; each run still gets its own actual request/admission, chosen manifest and restoration evidence. TLS/time may share a generation only where their actual final source bytes and reviews permit it. Do not delay the current minimal repair to build an unnecessarily broad combined generation. [3][5][9]

## 5. M14 closure sequence

Protect the already accepted F01, F02, F04, F05 and I02 evidence at its proven scope. F06's five DEFAULT regions are already verified; its principal remaining work is functional evidence and explicit acceptance. F03 and I01 retain substantial implementation/provider/default-selection work. [1]

### 5.1 First functional targets

After the mandatory first signal.alternate-repeat case, prefer the full original time row and wrapper row with the shortest remaining executable dependency. Default preference is **06-04**, then **06-01**. If the current matching functional generation already supports the wrapper batch while time needs another material source-generation change, execute the ready wrapper batch first. This is scheduling by actual reuse and readiness, not a change to the required first native case.

| Original task | Reuse now | Smallest remaining execution / full closure boundary |
| --- | --- | --- |
| M14-06-04-FUNCTIONAL | Passed time compiler/artifact work, completed TIME staging and guard controls | Bind and run the existing time payload; establish actual vDSO/process mappings, time-page/TSC publication and required mapping/time behavior with genuine providers and lifecycle |
| M14-06-01-FUNCTIONAL | Qualified TLS payload/collector/staging and all seven staged wrapper cases | Run the remaining supported TLS/arch_prctl, clone, mmap and SHM scenarios on the matching cohort; cover the entire original ABI/value/result/context requirement |
| M14-06-02-FUNCTIONAL | Existing first alternate-repeat case and eligible retained signal evidence | First repeat is a useful subset. Full closure still requires original signal-frame, alternate-stack, register-context and configured-xstate normal/error behavior |
| M14-06-03-FUNCTIONAL | Accepted default ownership/selection and matching existing proof | Finish both supported regsets/directions, validation/results, debug state and stop/wakeup/event ordering; an unavailable HOST control is not a pass |
| M14-06-05-FUNCTIONAL | Accepted default scope and reusable cross-process/NUMA source proof | Actual data/error results, target references and callback lifetime through completion and cleanup |

The seven prepared cases are memory.anonymous-zero, memory.mmap-zero-length, memory.munmap-unaligned, process.clone3-size-small, f06.clone-basic-own, f06.mmap-fixed-own and f06.shm-private-own. Do not recompile or restage their unchanged payloads or runners. Their necessary source-row subsets are not substitutes for the complete actual source view and native admission. Passing seven scenarios does not automatically close seven counted rows. [5][9]

### 5.2 Keep the generic implementation lane moving

The UTI pair is the next bounded implementation result, not the endpoint of the lane:

1. Compile the changed production C caller and genuine Rust crate object once.
2. Verify the C reference joins the unique Rust helper and real providers/storage. Reuse ABI35 and unchanged target/core/configuration evidence.
3. Select the next concrete remaining original implementation boundary in current dispatch/process source. Define its source/header/caller contract, implement the Rust/allowed-assembly replacement, and validate its changed compile/use/behavior obligations.
4. Maintain the supported final selection and unique project ownership mapping as replacements become real.
5. Produce the coherent final image and qualify affected runtime behavior before retiring the corresponding live C implementation.

The old qualified object contains neither the new helper nor the changed C call. It cannot prove the new pair. Conversely, rebuilding that old object without the new inputs would add no value. The twelve-field source change leaves request submission, ACK/refill/free/exit lifetime and other util_thread behavior outside its scope. [6][10]

Use the object's 114 undefined symbols as provider-accounting input. They are not 114 known missing implementations. Resolve each necessary reference against the actual selected definition, ABI, configuration, ownership and lifetime; reuse already established joins. The older 105-symbol ledger register belongs to another partial-link scope and must not be mixed into the newer count.

Current generic/syscall/process source/header/caller/build derivation is engineering work. It does not wait for an externally authored per-name inventory. Actual held exec/ACK/TID/XPMEM operations and the specifically excluded historical task still require their own supported disposition; do not replay or rename them. Keep eligible source/implementation work moving while an exact unavailable external input is escalated. [11]

### 5.3 Finish the remaining original M14 scope

| Original area | Required remaining result |
| --- | --- |
| 03-01 / 03-02 DEFAULT, whole F03 DEFAULT, I01-E2/E3 | Complete supported dispatch/process implementation and real selected providers; unique Rust/permitted-assembly ownership in the final coherent image; C retirement only after replacement and actual link/selection proof |
| 03-01 / 03-02 FUNCTIONAL | Actual request ABI/initialization/lifetime/exactly-once completion; required fork/exec/wait/exit/ptrace and final process/host cleanup under genuine scope |
| 03-03 FUNCTIONAL | mmap/munmap/mprotect/brk/remap, NUMA/process-VM behavior and substantive callbacks/lifetimes |
| 03-04 FUNCTIONAL | Signal actions/masks/altstack, futex/robust cleanup, time/wait/wake and restart |
| 03-05 FUNCTIONAL | Credentials/limits/scheduling, SHM/perf/file wrappers, validation/forwarding and required live-reference teardown |
| F03 / F06 ACCEPT and I01 ACCEPT | Explicit review of every applicable original child on its required cohort |
| I03-E1/E2/E3 and ACCEPT | Coherent image/modules, actual native/source/current-free admission, useful applications and process/memory/thread/signal behavior, full lifecycle/resource restoration |

Do not turn already accepted file gates into a recurring regression project. If a later image changes their actual dependency boundary, requalify that affected boundary and bind the result to the new cohort. Earlier evidence remains valid for its earlier proven scope.

## 6. M15 closure sequence

M15 F01, I01 and I03 are accepted. Preserve those results. The remaining file work is F02–F08; I02 needs the bounded parent review above and I04 needs matched applications and restoring lifecycle. [1]

| Priority / original task | Concrete work | Reuse and acceptance boundary |
| --- | --- | --- |
| Now: M15-I02-ACCEPT | Decide original gate/native-validation language from retained criterion and four child receipts | No technical rebuild. If observed loadability is genuinely required, use the planned matching native receipts |
| Parallel source: M15-F02-complete-ABI-behavior | Join the remaining supported executor entry/provider/behavior obligations to actual existing evidence; implement or qualify only genuinely unmatched obligations | Original profile, selection, deployed/provider and existing ABI proof remain reusable; a descriptor-only proof is not full behavior |
| First admissible HOST slice: F08 worker lifecycle | Finish corrected no-event test review, then observe both enabled workers, normal stop/joins and full owned cleanup | Adds a missing installed runtime scenario; does not re-close already green fixture children or prove real events/kmsg/hung-up behavior |
| First matching diagnostic opportunity: M15-F03-deployed | Run installed mcinspect's real required consumer behavior on an admitted matching device/workload | Reuse its already complete default, ABI, provider and HOST link proof; then review F03 acceptance |
| Following genuine dump opportunity: M15-F04-deployed | Actual matching dump and GDB consumer behavior with positive continuation and cleanup | Reuse eclair's completed default/ABI/link work; then review F04 acceptance |
| Shared real device lifecycle: F05 original-behavior/deployed-native and F06/F07 device-behavior/native | Execute remaining supported library and command scenarios serially with exact actual OS/device identity and resources | Reuse installed tools, unknown-action corrections, interruption fixes and qualified seams; no fixture or help-output substitution |
| Genuine event lifecycle: F08 installed-service/native | Bind the real same-kernel IHK event/device owner; run the prepared CREATE/BOOT/REMOVE and kmsg subset, then the separately defined remaining original observations | AEA9/034b covers the one-kmsg-worker subset. Separately derive and admit required kind101/syslog/hung-up observations; no fabricated event or second device owner |
| Integration: M15-I04 children and ACCEPT | Join exact coherent image/modules/executor/libraries/tools, actual applications, module/MM lifecycle and restoration | Reuse genuine observations across applicable original obligations; final M15 acceptance follows M14 |

The no-event enabled-worker test is independent of successful native publication in its functional requirements. It still waits for actual HOST fit and closure of the current exclusive failed HOST scope. Its workers wait before IHK device access; this is why it is a useful separate runtime increment. [2]

The latest F08 source review found 25 consumed null-size arcs across 15 unique references that fail strict size equality before creation. TimeSource's next change is limited to genuine integer sizes and necessary request/pin/path literals, followed by FunctionalDelta's changed-data/final-argv review. Reuse the unchanged binary, providers, sampling/guard/custody/oracle bodies and passed readiness proof. This correction is not a reason to rebuild the image or re-run those unchanged proofs. Actual worker execution follows the successful operation review and its real admission. [2]

Real F08 event behavior requires actual same-running-kernel /dev/mcd0 and dynamic /dev/mcos0, a processed-event publisher/monitor association, the assigned native owner and lifetime/restoration evidence. The existing disabled-worker readiness result, an epoll registration, or two waiting workers does not satisfy this condition. AEA9/034b enables one kmsg worker and disables the hung-up worker; actual kind101 EPOLLIN delivery, syslog delivery/ordering and hung-up/status2 behavior remain separate unproved obligations. [12]

F05 also contains substantive remaining correctness work, including the actual supported balanced-reservation arithmetic/backend contract and defined zero-node/zero-compensation handling. Reuse already qualified ownership/error cases but do not treat them as proof of full success arithmetic. Derive the supported contract before executing any undefined path. Existing library/CLI definitions are useful input; current AGENTS clarification and later verified fixes supersede their old external-inventory or pre-correction language. [1][11]

### 6.1 Share legitimate native work

Where the reviewed operations allow it, use one admitted coherent lifecycle to produce several applicable observations:

- Exact module/kernel/image/tool identities and actual load/boot state.
- Real reservation/query, OS creation, assignments and required IKC state.
- Useful application and executor behavior.
- Installed diagnostic consumers and genuine daemon events on that same owned system.
- Required shutdown/release/destroy/unload and resource restoration.

Keep operations serial under one owner. Reusing a cohort does not reuse a consumed nonce, extend a finished operation, or modify an already frozen request. If an operation terminates its lifecycle or cannot admit another consumer, preserve that boundary and use the appropriate later operation. Share existing evidence when its identity and behavior match; do not create another owner merely to obtain a second report.

## 7. Six-owner working model

Root remains the sole canonical compositor, resource-admission operator, native executor and ledger acceptance recorder. Existing frozen reviewer assignments stay intact. Use this table for the next eligible work after those handoffs finish.

| Existing owner | Primary next responsibility | Stop / hand off when |
| --- | --- | --- |
| NativeCurrent | Current failed-family resolution, minimum corrected publication and actual native binding | The specific handoff is executable or the exact missing external input is named |
| NativeBinding | Independent review of the critical changed source/operation and actual outcome | The existing review is complete; avoid another whole-history review |
| Proc | UTI changed compile/use, then one remaining generic implementation/provider boundary | The increment has real source/object/use evidence and its next original obligation is clear |
| TimeSource | Ready time/F08 work and actual runtime preparation using saved artifacts | The exact next operation is ready; do not keep generating preparation variants |
| FunctionalDelta | Existing F08 review, then one disjoint unmet functional/provider obligation or result analysis | Its bounded source/review/output is complete |
| M15Leaf | Finish the current UTI operation review, then bounded I02 original-gate review and matching M15 result/acceptance review | The existing original task is accepted or its exact remaining clause is recorded; completed capture qualification is reused |

Keep at most one unfinished implementation obligation per source owner. Normally only the critical author/reviewer pair stays continuously on the shared control path; a third owner may finish an already assigned independent result review. Use remaining owners on genuine independent implementation or acceptance work. If no eligible task exists, let the owner wait rather than create another inventory.

More owners do not imply more executable jobs. Current HOST limits remain CPUs 0,6,7, at most three aggregate light jobs and 4 GiB total including all retained families and controller/worker/container overhead; require at least 26 GiB available and the existing disk floors. Native remains one separately admitted owner on CPUs 2–5 with 12 GiB. Native work can also have HOST provider/controller charges, which must be included. The optional 25 GiB/16-owner phase remains deferred. [11]

## 8. Rebuild and reuse rules

The user's explicit direction is to stop continually rebuilding and always use existing work where it remains applicable. Apply these rules before invoking build or publication commands.

| Change or situation | Required action |
| --- | --- |
| Documentation, status, ledger or review-only commit | Reuse binaries, image, modules and unchanged tests. No rebuild |
| Same test binary/runner; different admitted case selection or data | Reuse compiled artifacts and matching installed code; bind the actual new request and run only the missing case |
| Python/control-publication source change | Validate the changed source boundary and publish only the necessary changed code generation. Do not rebuild the compute image merely for this |
| UTI C/Rust implementation change | Compile the affected genuine C and Rust targets and prove their real reference/definition/provider use; reuse unchanged ABI/core/toolchain/configuration evidence |
| Changed object included in the compute image | Relink the affected candidate image and qualify the changed ownership/dependency/runtime boundaries |
| Compute change with unchanged Linux-module inputs | Reuse the three qualified KOs and their ABI/Kbuild evidence at the matching scope; do not rebuild unrelated modules |
| ABI, configuration, toolchain or provider change | Identify affected consumers and rebuild/requalify that dependency set; preserve unaffected results |
| Suspected stale/corrupt cache or reproducibility defect | Establish the concrete defect and rebuild the smallest invalid part. Use a clean rebuild only when the evidence or original criterion actually requires it |
| Old green test with no changed relevant input | Reuse its result; do not run it again to populate a tracker |

Use the saved configured build directory, dependency files, object/provider mappings and retained source/configuration/toolchain identities. No new cache manager or retention framework is needed. Record the changed input and affected target in the existing handoff; this is a routine engineering decision, not a new permission gate.

Keep the preserved c964/a2f/f133 cohort as a working baseline. Integrate compatible actual implementation increments into a separate candidate, then build and qualify that candidate at a meaningful boundary. Do not produce a new full image for every source-only helper, review correction or report.

Evidence reuse must remain exact. A different final image is not automatically covered by all prior runtime passes. Join unchanged components to their preserved evidence, identify affected source/ABI/provider/lifetime consumers and run the required matching final behavior. Reuse avoids repetition; it does not turn old cohort evidence into a new result by changing its label. [4][6][9][10]

## 9. Operating rules that prevent another preparation loop

1. **Ready means executable.** A ready handoff names one operation, its exact changed and reused inputs, executor, real prerequisites, expected result and cleanup observations. Once those requirements are satisfied and the grant fits, execute it.
2. **Review validity follows material inputs.** Keep an existing review until an actual reviewed input or dependency changes. Review that change, rather than the whole history.
3. **Diagnose the first actual failing boundary.** Preserve the original result, exact safe error and owned lifecycle state. A new attempt must contain a concrete correction or new necessary input.
4. **Stop the artifact cascade.** A source handoff should become execution or a named missing prerequisite. Do not repeatedly create an additional wrapper, catalogue or narrative packet without a concrete consumer requirement.
5. **Finish the failed family.** Original waits, descriptors, captures and lease/resource disposition remain tied to their actual operation. A later helper's successful cleanup cannot close them.
6. **Keep status requests from resetting work.** Report current evidence while keeping healthy assignments and the accepted next operation intact.
7. **Publish useful increments.** Commit the bounded source pair, actual validation result and relevant original IDs once coherent. Root preserves unrelated dirty edits.
8. **Update acceptance promptly.** When a full original condition is satisfied, the reviewer supplies the explicit decision and Root updates the ledger at the same coherent checkpoint. Do not leave a completed child or gate at zero merely because a larger milestone is unfinished.

An error report should include enough safe source/binding context to identify the failed predicate, its relevant expected/observed values where appropriate, the operation's real terminal or pending state, and the specific missing closure fact. Use the existing capture/reporting path. Do not interrupt the immediate closure queue to build a generalized observability framework.

## 10. Checkpoints, escalation and useful metrics

Use the existing 20-minute foreground checkpoint and 10-minute mailbox polling cadence. This strategy creates no new scheduled task.

At each checkpoint, record in the existing CAMPAIGN/mailbox flow:

- Original IDs closed and the exact matching result/review.
- Actual functional cases completed, including failures and cleanup.
- Necessary implementation increments completed and whether they are compiled, linked, selected or only source-ready.
- The next executable operation and its precise missing input, if any.
- Retained operation families and charged bytes/jobs, with the unresolved closure fact.
- Ready-to-execution waiting time and the reason for that wait.

If a ready task does not execute by the next checkpoint, Root either runs it under the available valid admission or names the exact missing prerequisite and supplying owner. If the same boundary remains unchanged across two checkpoints, focus on that one unresolved observation/artifact/access and the supported way to obtain it. Do not respond with another broad preparation assignment.

A checkpoint is a trigger for diagnosis and escalation. Elapsed time does not grant cleanup permission, prove a process absent, release a lease or reset accounting. Preserve actual service/auth/usage and ownership restrictions, the same finite credit run, all original unknowns and the excluded historical task. Continue genuinely eligible work when another task has an exact hold. [11]

Useful progress measures are completed functional scenarios, complete original checks, accepted gates, necessary emitted-and-used implementation increments, and reduced execution waiting time. Packet count, review count, hashes collected, agent utilization and unchanged green reruns are not completion metrics.

### Immediate operating targets

- **Next existing checkpoint:** finish or precisely bound the I02 original-gate decision; state the remaining 30017 closure fact and its supplying owner; finish the pending UTI operation review and F08 changed-data correction/review.
- **First restored execution slot:** complete the corrected publication or an independently admissible ready HOST result, according to actual priority and fit.
- **First restored native window:** obtain the designated first case and restoration result, then consume the next ready time/wrapper obligations.
- **Next acceptance review:** close a complete original row/gate when its evidence is sufficient, otherwise list only the exact remaining clauses.

These are sequencing targets, not promised elapsed-time completion. A reliable milestone ETA requires a functioning native execution path and measured throughput on the remaining original obligations.

## 11. Completion order and review decision

M14 finishes when F03, F06, I01 and I03 satisfy every applicable original condition, while the accepted F01/F02/F04/F05/I02 scopes remain properly bound to the required final cohort. Final M15 acceptance follows M14, after F02–F08, I02 and I04 meet their original conditions. M15 source work, matching qualifications and supported individual-gate decisions can advance in parallel.

The strategic test is whether the work consumes completed artifacts and produces actual missing evidence. First establish one properly retired failed family and a working native functional path. Then keep that path busy with the smallest complete original requirements while the remaining Rust/provider work advances alongside it.

## Sources

[1]: https://github.com/phoenix-hacking/mckernel/blob/52b587e6ff4932beb610b42ec8e90995a67e38f6/docs/verification/m14-m15-closure-progress.json
[2]: https://github.com/phoenix-hacking/mckernel/blob/2c59943d64ef9d3d323cda5063f195b27856dec8/CAMPAIGN.md
[3]: https://github.com/phoenix-hacking/mckernel/blob/52b587e6ff4932beb610b42ec8e90995a67e38f6/docs/verification/m14-graph-net-normal-caller-repair-20261113/three-size-scalars/SOURCE-REVIEW.json
[4]: https://github.com/phoenix-hacking/mckernel/blob/52b587e6ff4932beb610b42ec8e90995a67e38f6/docs/development/M14-STABLE-BASELINE.md
[5]: https://github.com/phoenix-hacking/mckernel/blob/52b587e6ff4932beb610b42ec8e90995a67e38f6/docs/verification/m14-f06-seven-stages-20261113/QUALIFIED-SEVEN-STAGE-IDENTITIES.DATA.json
[6]: https://github.com/phoenix-hacking/mckernel/blob/52b587e6ff4932beb610b42ec8e90995a67e38f6/docs/verification/m14-uti-private-object-20261113/paired-info-initializer/SOURCE-REVIEW.json
[7]: https://github.com/phoenix-hacking/mckernel/blob/52b587e6ff4932beb610b42ec8e90995a67e38f6/docs/verification/m15-i02-matched-artifacts-20261112/INDEPENDENT-REVIEW.json
[8]: https://github.com/phoenix-hacking/mckernel/blob/52b587e6ff4932beb610b42ec8e90995a67e38f6/docs/verification/m15-i02-matched-artifacts-20261112/MATCHED-THREE-MODULES.GO-CANDIDATE.json
[9]: https://github.com/phoenix-hacking/mckernel/blob/52b587e6ff4932beb610b42ec8e90995a67e38f6/docs/verification/m14-f06-seven-provider-guard-20261113/post-control-binding/REVIEW.json
[10]: https://github.com/phoenix-hacking/mckernel/blob/52b587e6ff4932beb610b42ec8e90995a67e38f6/docs/verification/m14-uti-private-object-20261113/paired-info-initializer/NECESSARY-CHANGED-PAIR-COMPILE-LINK-USE.NOT-A-GRANT.json
[11]: https://github.com/phoenix-hacking/mckernel/blob/52b587e6ff4932beb610b42ec8e90995a67e38f6/AGENTS.md
[12]: https://github.com/phoenix-hacking/mckernel/blob/52b587e6ff4932beb610b42ec8e90995a67e38f6/docs/verification/m15-f08-minimum-context-20261112/next-active-worker-source/PUBLICATION-AND-NEXT-RUNTIME-INPUT.HANDOFF.DATA.json

- [Canonical original ledger][1]
- [Current campaign at the evidence baseline][2]
- [Reviewed three-value publication correction][3]
- [Stable-baseline retention reference][4]
- [Qualified seven-case staging][5]
- [Reviewed paired UTI initializer][6]
- [I02 matching-artifact review][7] and [candidate][8]
- [Seven-case shared-provider binding review][9]
- [Necessary changed UTI compile/use checks][10]
- [Execution and reuse instructions][11]
- [F08 event contract and remaining actual inputs][12]

