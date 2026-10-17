# OS velocity supervision reviews

User requested 30-minute to one-hour reviews and continuous concrete steering
from the interactive chat. Read [VELOCITY.md](VELOCITY.md) for the method.
Preserve completed entries; append new observations and update only this cursor.
This file describes supervision, not OS acceptance or execution authority.

## Current review cursor

- Supervisor chat: `01a1479e-a9c2-7340-8d88-4313fab04738`; supervision goal active.
- Engineering campaign: `01a149eb-f950-7f13-95a2-59dfc2918d49`; sole runtime/Git owner.
- First baseline recorded: `2026-10-17T13:26:00Z`.
- Baseline interval: `2026-10-17T12:52:42Z` to `2026-10-17T13:24:54Z` (32m12s).
- Active target: user-rebased [PRACTICAL-GOAL.md](PRACTICAL-GOAL.md), scope
  `practical-kernel-apps-v1-20261017`; comprehensive qualification is deferred.
- Last full review: `2026-10-17T15:55:14Z` (interval 30m03s).
- Next full review target: `2026-10-17T16:25:00Z` (09:25 America/Los_Angeles).
- Next review latest target: `2026-10-17T16:55:00Z`; preserve healthy operations.
- Last included-usage observation: 18%; existing campaign stop remains 97%.
- Current intervention: advance ready C-thread admission using its permitted
  metadata-only joins; correct the reviewed shutdown effect-classification defect
  with actual runtime-consumer regressions; stage the tested strict-Running helper.
- Current invocation independently accepted diagnostic/app behaviors: 10 (signal,
  calloc, file-write/read, TLS, adapted mutex, alternate-signal, realloc-grow,
  adapted closed-read, useful dynamic-libc memory application, real Rust std app).
  Old formal scores and estimates remain historical, not the new goal's percentage.
- No new monitor script, OS timer, engineering dispatcher or workload was started.

## Baseline review — 2026-10-17 13:26 UTC

| Measure | Observed result |
| --- | --- |
| Signal guest launch attempts | 1 |
| Actual guest boots / payload executions | 0 observed / 0 observed |
| New guest passes / observed kernel failures | 0 / 0 |
| Infrastructure launch failures | 1: QEMU rejected the QMP socket pathname as exceeding its 108-byte limit |
| Newly integrated kernel repair with actual-body regression | 0 confirmed in this interval |
| Formal acceptance / new milestone-condition closure | No increase established |
| Execution infrastructure | Mount-order correction, failed-staging retention, fresh retirement observation and archival cleanup advanced; these remain separate from kernel behavior |
| Next-ready cases | Signal, calloc and file-write/read inputs have strict manifests; no new guest pass from these preparations |

The original native/image artifacts remain available. Cleanup independently
accepted at 13:19:27 UTC; final signal execution review completed at 13:21:03;
attempt files appeared around 13:22. No material avoidable admission queue is
demonstrated for that transition. The exact QEMU launch/exit timestamps were not
established by this narrow review. QEMU stderr is 370 bytes; serial/debugcon and
QEMU stdout are empty. The failure precedes boot and proves no signal defect.
Failed guest-owner retirement was not yet established at the observed snapshot.

Useful separate results: mount-order checks passed 10 tests; retirement/cleanup
source review reports 23 tests; failed-output staging retention passed 17 tests.
The lifecycle diagnostic tool passed 26 injected actual-main scenarios, which
prove tool behavior rather than native shutdown. Callee/kernel acceptance is
not inferred from fixtures. Preserve original per-case results and contracts.

At 13:25 the campaign's own defect triage found no genuinely ready bounded new
M03/M02/fork-activation patch: M03 lacks production lease/generation authority,
M02's relevant descriptor tests already pass, and fork activation lacks the
end-to-end caller/ACK contract. Do not repeat that audit or invent a tiny patch
to fill workers. Prepared payloads and the actual socket-path defect are ready
work; extra local compiler jobs also require available shared capacity.

**Adjustment for the next interval:** delegate the narrow endpoint/path-length
correction and independent regression review while the dispatcher reconciles
the failed owner. Check complete encoded UNIX socket paths, including generated
suffixes, before consuming another guest release. Use a fresh output/attempt and
appropriate new release after correction. Reuse current942 and the ready next
payloads; do not rebuild Linux or repeat historical preparation for this defect.
Instruction `20261017T132606563155Z-8691d9cd5d05439982efde1d086a58e9` was queued
through the existing launcher. Confirm delivery in its receipt, not by replaying.

Sources read: launcher state and selected current console/lane messages;
HANDOFF/CURRENT checkpoint374; evidence records
`scratch22-image-mount-order-correction-20261017-1.json`,
`scratch22-image-reconciliation-source-review-20261017-1.json`,
`scratch22-authority3-image-cleanup-result-review-20261017-1.json`,
`native-lifecycle-probe-actual-main-pass-20261017-1.json`,
`memory-calloc-zero-current942-staging-20261017-1.json` and
`file-write-read-current942-staging-20261017-1.json` under `../evidence/`.
No speed multiplier can be calculated from a zero guest-pass baseline; compare
raw outcomes, time to first payload result and avoided repeated failures first.

## Review 1 — 2026-10-17 13:55:47 UTC

Interval: `13:24:54` to `13:55:47` UTC, 30m53s. The previous baseline was 32m12s;
these short windows and a zero guest-pass baseline do not establish a 2x/3x ratio.

| Measure | Previous baseline | This interval |
| --- | --- | --- |
| Launch attempts | 1, failed before boot | 4: signal, calloc, file, TLS |
| Independently accepted actual McKernel diagnostics | 0 | 3, each with accepted retirement |
| Accepted kernel failure | 0 | 0; TLS is a protocol/evidence failure under reconciliation |
| New integrated kernel implementation repair | 0 confirmed | 0 confirmed |
| New execution-infrastructure repair | Mount/stager/retirement work | QMP endpoint admission, integrated and independently reviewed, 76 tests PASS |
| Formal application/production/language acceptance | 0/273, 6/130, 0/7 | Unchanged |
| Included weekly usage reported by existing launcher | 12% | 13%; stop remains 97% |

**Verified runtime gains:**

- `signal.mask-restore`: independently accepted at 13:39:37 UTC. Exact 40-byte
  stdout `handled=1 observed_blocked=1 restored=1\n`, empty stderr, exit0.
  Covers the original selected two-bit oracle, not arbitrary whole-mask behavior.
- `memory.calloc-zero`: independently accepted by 13:43:58. All six frozen size
  lines match; actual McKernel scheduling, streams, process/procfs release and
  host/container retirement joined. One diagnostic, not six accepted cases.
- `file.write-read`: independently accepted at 13:48:31. All six sizes, including
  1 MiB, pass write/seek/read/compare/fstat/EOF. Reopen and checked close/unlink
  are not covered. Complete owner retirement independently accepted.

The accepted decisions are additive result-review records under `../evidence/`:
`signal-mask-restore-current942-result-review-20261017-2.json`,
`memory-calloc-zero-current942-result-review-20261017-1.json` and
`file-write-read-current942-result-review-20261017-1.json`. Keep raw results'
pending-review fields and original failures unchanged. The correction, plan and
initial review protocol were pushed/fetch-verified at `6ea3b964`; subsequent
guest releases advanced through `ba88a7e9`, `09205941` and `2b68c7ad`.

**Handoffs:** acceptance to next command-file start proxy was 2m19s, 1m58s and
2m03s for signal→calloc→file→TLS. All are below the five-minute scheduling
target. They include required reviews, source/HEAD and live admission; the
observations do not establish how much of each interval is avoidable. Successful
owner invocations took about 33-34 seconds. No unchanged kernel/image rebuild
was needed for these diagnostics.

**Failures and corrections:** the QMP fix preserved the original 132-byte path
failure and rejects endpoints above 107 encoded bytes before side effects. Its
first integrated test exposed a TMPDIR-dependent fixture and an outer shell
status masking the test failure; both are preserved. Final tests use the actual
constructor/source binding and real subprocess status: seven new plus 69 existing
tests PASS, with independent source/execution review. The fresh endpoint is 92 bytes.

TLS launched at 13:50:34; its outer owner command exited 1 after 34.423s. Initially
only `docker command failed: start` was available, so no inner outcome was
classified. By 13:53 the dispatcher had captured the inner result and owner
archive: the evaluator reports `stream accounting`, with ND_FUTEX declaring 4096
against the manifest's 1024. This supersedes any inference that Docker's outer
error proves failure to boot. Do not assign a TLS kernel failure or pass from
that error, change original captures, or admit another runtime before required
retirement/evidence reconciliation. Source: existing TLS dispatch captures and
13:53:39 dispatcher report; final independent disposition remains pending here.

**Useful parallel implementation:** lifecycle collector and parser progressed
while guests ran; staged artifacts have 60 members including the bound probe.
Actual producer→serializer→parser testing found the pinned ioctl ABI has
Running=5 and Booted=3, contrary to the earlier parser's Running=3. The original
bytes/failure are retained; correction explicitly rejects 3, and 13 focused tests
pass including real retained probe output through the unchanged C serializer.
This is offline tool integration, with no native shutdown/restoration credit.
Mutex preparation reused valid compile/reference output but found attr=NULL
versus the catalog's 262144-byte stack requirement; its admission remains held.

**One adjustment for the next interval:** before freezing a new collector mode,
run one cheap actual producer/serializer→actual consumer positive and relevant
boundary negative. Apply it now to TLS stream-limit agreement, while completing
the lifecycle enum correction's independent review. Keep original oracles and
allowed bounds; don't make a failed real capture pass by rewriting it. Resolve
the mutex stack contract explicitly and prepare a fresh permitted variant only
after its decision. Use the freed runtime lane for the next genuinely ready
case; no blind retry, unchanged image rebuild or speculative M03 audit.

Supervision instruction `20261017T135326429784Z-2c936ba144b246be9cdf83a98dcafe2f`
was accepted by the server at 13:53:26 UTC. Dispatcher plus source/test and review
lanes remain active. Next review is 14:25 UTC. Independent judgment retains
M02 50-70%, M04 30-50%, M08 55-75%; results strengthen runtime evidence within
these broad low-confidence bands. Other milestone estimates remain as previously
reported. No whole-OS score or formal milestone closure is inferred.

## Review 2 — 2026-10-17 14:25:21 UTC

Interval: `13:55:47` to `14:25:21` UTC, 29m34s. Campaign active; worker and
app-server PIDs/start identities match saved state. Next review: 14:55 UTC.

| Measure | Review 1 interval | This interval |
| --- | --- | --- |
| New independently accepted McKernel diagnostics | 3 | 1: corrected TLS2; invocation total 4 |
| New runtime attempts | 4 | 2: TLS2 and lifecycle; mutex not launched by cutoff |
| Native lifecycle failure | None established | Ready4, then shutdown -EBUSY and Shutdown8 |
| Reviewed production-source change | None confirmed | Running publication plus shutdown-stage logs; committed, not built/runtime-validated |
| Formal application/production/language acceptance | 0/273, 6/130, 0/7 | Unchanged; points remain 350/10000 |
| Included weekly usage | 13% | 14%; existing 97% stop unchanged |

TLS2 independently passed at 14:04:48: exact original 55-byte 2/4/8-worker
oracle, empty stderr, exit0, all 15 main/worker procfs publication/deletion pairs
and full owner/container retirement. Only the manifest limits changed to the
actual ND_FUTEX producer's 4096-byte limits. Four regressions bind the real
collector contract; the original 1024 mismatch is rejected. TLS1 remains FAIL.
This adds basic TLS/worker evidence, not comprehensive TLS or formal-case credit.
Clarification to Review 1's conservative pending disposition: TLS1's independent
retirement/harness-failure decision was already reported at 13:55:10; it grants
no runtime pass and is retained in its additive failure-review record.

Lifecycle launched 14:07:07.879 and its owner exited1 after 33.968 seconds.
Independent retirement accepted 14:09:29. Exact raw readback establishes
Ready(4) -> shutdown -16 -> Shutdown(8) -> close0. Signal payload output/exit0
passed. The collector maps helper failure onto its procfs result field, so
"guest registrations remain" does not independently prove leaked registrations.
Native Running/shutdown failed; the first busy teardown stage is still unknown.
The failure archive and original 399-byte probe are retained unchanged.

Useful parallel source work: native boot had no Running publication after its
full-ready handshake. An explicit v6 ABI2 opt-in now publishes Running; older
versions and failure states retain their behavior. Independent source review
passed 70 runtime tests, 10 shutdown tests and four rejected semantic mutations.
HEAD at cutoff is `1769263c` (Running source change and next mutex diagnostic).
No new module build or native repair verification has occurred. Separately,
sysfs cancellation passed four actual-body tests, but remains unwired and
pending independent ownership review. It has no production peer-stop proof
constructor. Service joins/callback drains and generation/resource ownership
remain real integration work; do not remove the terminal retention guard.

**Throughput and handoffs:** TLS2 acceptance -> lifecycle launch was 2m19.879s,
again below five minutes. After lifecycle retirement, no subsequent guest
launched by cutoff, a 15m52s observed gap. Adapted mutex source/staging already
passed; execution review completed 14:19:09 with fresh-admission conditions.
The gap includes necessary failure reconciliation, review and checkpoint work;
its avoidable portion is not measured. Diagnostic throughput is lower than the
previous window (one pass versus three). Source repair progressed, but this
window does not demonstrate doubled/tripled engineering velocity.

**Removed/targeted repeated delays:**

- Future execution packets now include bounded exact nonce-bound attempt tar
  readback after positive retirement, avoiding a second predictable triage
  review. Mutex's accepted packet includes three scoped readbacks.
- Alternate-repeat metadata correction reused compile/reference/overlay and
  passed all nine fields for 59 members, preserving 40 authentic nonzero base
  timestamps; actual serializer/evaluator positive and two negatives passed.
  It remains prepared, not a runtime pass.
- Multiple lanes rediscovered the same Python3.8 annotation failure. Future
  packets should use the already passing `/home/holden/anaconda3/bin/python3`
  and approved environment. Preserve failures, avoid global environment edits.
- Module packaging copied 60 files (~1.17MiB), then failed an assumed
  `rust/libkernel.rlib` prerequisite. Correction must follow actual retained
  compiler dependencies and reuse the staged source package. Do not rebuild
  Linux/image or copy the full tree to satisfy an invented support filename.
  The exact external-module invocation remains unproven and unreleased.

**Adjustment:** give the coordinator a ready reviewed next-case packet while
specialists handle lifecycle source/ownership repair. Launch the next eligible
current942 diagnostic after its ordinary live admission and release, then keep
the alternate-repeat review ready. Use a separate frozen next-module candidate;
no failed lifecycle replay or shared baseline mutation. This overlaps useful
work rather than increasing simultaneous heavy owners or speculative audits.

Steering receipts `20261017T141124027564Z-d079af5c43474f93a90b4f567165101a`
and `20261017T141438942839Z-b6747a2b79ae44a9b3a87eecffb3c4a5` were
accepted by the existing server. Interpreter steering was queued as
`20261017T141924826117Z-45d27c644957434aa6b3d297ada7dd1f`.

Sources: existing state/console and additive records under `../evidence/`:
`thread-tls-isolation-current942-result-review-20261017-2.json`,
`thread-tls-isolation-manifest-correction-20261017-1.json`,
`native-lifecycle-current942-failure-review-20261017-1.json`,
`native-running-publication-source-20261017-1.json`,
`native-sysfs-remote-shutdown-source-20261017-2.json`, and
`native-running-external-modules-preparation-20261017-1.json`.
No shared artifact was rehashed for this supervision review. Broad M00-M13
estimate bands and formal statuses remain unchanged; scoped evidence improves.

## Review 3 — 2026-10-17 14:55:37 UTC

Interval: `14:25:21` to `14:55:37` UTC, 30m16s. Campaign/process identities
verified live; next review 15:25 UTC. User explicitly changed completion scope
during this interval; preserve that change across continuation and future launches.

| Measure | Review 2 interval | This interval |
| --- | --- | --- |
| New independently accepted McKernel diagnostics | 1 | 3: adapted mutex, alternate-signal, realloc-grow |
| Invocation total accepted diagnostics | 4 | 7, each with accepted retirement |
| New runtime attempts | 2 | 3; adapted closed-read reviewed/released next, not launched at cutoff |
| New matched module build/native repair validation | 0 | 0; build admission remains blocked |
| Native shutdown/resource-restoration pass | 0 | 0; original Ready4 -> -16 -> Shutdown8 remains open |
| Included weekly usage | 14% | 16%; stop remains 97% |

**Actual gains:** adapted mutex launched14:25:28.302, owner0/33.582s,
independently accepted14:29:28. Frozen51-byte2/4/8 vectors pass; fourteen worker
cycles reuse TID258 and do not establish overlap/contention. Alternate-signal
launched14:39:36.912, owner0/33.643s, independently accepted14:46:02. Exact415
bytes and sixteen handler-address/alternate-stack hits pass; normal-stack
restoration is not proven. Realloc launched14:51:41.547, owner0/33.748s,
independently accepted14:53:59. Exact25-byte oracle shows the original32-byte
pattern survives growth to2048, not relocation or added-byte contents. All three
retain initial process-retirement EAGAIN followed by successful retirement and
release. Full guest/container/client/owner retirement accepted; no native OS
restoration credit follows from guest disposal.

**Scheduling:** mutex acceptance -> alternate launch10m08.912s; alternate
acceptance -> realloc launch5m39.547s. At14:36:23 the dispatcher explicitly
reported no known alternate runtime admission blocker and late assignment of
its already assembled proposal to review. Delegating packet assembly and
assigning the reviewer promptly removed that specific coordinator delay.
Remaining wall time includes real review, checkpoint/fetch and live admission;
do not call it all avoidable. Alternate owner result -> independent acceptance
was5m51.452s, including readback captured14:44:26. Throughput improved from one
to three accepted behaviors, but short different-workload windows do not prove
a sustained2x/3x multiplier. Have the next eligible case's reviewer assigned
while the current guest runs, rather than after its retirement.

**User-authorized rebaseline:** the user explicitly rejected excessive formal
milestones and huge fuzzing-hour requirements in favor of a solid kernel and
working application infrastructure. Actual old requirements include100000fuzz
VM-hours,30000bare-metal node-hours and168-hour Intel/AMD per-class soaks.
These and broad full-catalog/language/hardware/external certification are now
deferred from current completion, with all historical contracts/evidence/scores
preserved. They are not PASS and must not reappear as active finish prerequisites.

PRACTICAL-GOAL.md and practical-milestones.json define the new supported-profile
M00-M13 goal: useful libc C and Rust std applications, representative core and
concurrent/process behavior, actual native restoration, one clean pinned recipe
replay, focused regressions and runnable delivery. The bounded final session is
two fresh guests, ten complete native cycles,100app launches and60mixed-workload
minutes. Checks may overlap/reuse matching valid evidence. Known corruption,
unsafe ownership, failed shutdown and broken required apps remain real defects.
Rust consumers, isolation/resources, independent changed-boundary review and
usage/stop safeguards remain intact.

Active GOAL/START/CONVERGENCE/PARALLEL-RESUME/VELOCITY and handoff precedence were
updated; README's override was appended, preserving all68source-bound task lines.
JSON/unique IDs/diff checks passed. Independent documentation review found no
P1/P2 issue. Dispatcher explicitly adopted at14:47:27; practical-scope checkpoint
`958c6bbc` was pushed/fetch-verified. Existing progress renderer now shows practical
work first and original counters as historical/deferred. Reconciliation closes
only P-M02-03 for the six accepted runs available then: one completed,32open,
two unassessed checks across14open milestone areas. This is not a whole-OS
percentage, and unassessed is not0%engineering. Seventh run arrived later.

The earlier30–90+day full-roadmap planning guess is not a reliable ETA, especially
after confirming the enormous old exposure requirements. The practical scope is
different; forecast from actual lifecycle repairs and useful-app/exit-check
closure over the next24–48hours, not by rescaling old percentages or counting
new documents. No date was added as a contractual deadline.

**Critical next work:** Running/log driver13injected tests pass; corrected
external-module owner23tests and independent source review pass. Review caught
a real descendant-retirement proof gap, fixed owner-locally with persistent
uncertainty/negative controls; shared live transport is unchanged. Draft build
admission still rejects seven preserved historical leases through a blanket glob.
Author is reusing their existing authenticated historical-retirement contract,
without deleting records or running cleanup. Resolve that exact source mismatch,
bind the final request/release, then perform the first actual matched module build.
No Linux/image rebuild or native repair pass has occurred. Keep new sysfs/worker
WIP out of this first Running/log candidate.

In parallel, realloc and adapted closed-read preparation/review are complete;
closed-read's next run covers EBADF and first/last buffer bytes only. Retained
dynamic-libc native-core memory/thread modes are being prepared. A real Rust std
application is being implemented and compiled with the pinned toolchain, rather
than stopping at a source-discovery note. Sysfs cancellation and exactly-once
worker-stop components still require integration/peer-stop proof and actual
native validation. One heavy owner remains the cap.

Steering receipts: practical scope
`20261017T144202597819Z-8d995cad319f40a99d4ee970c0a24488`, completed files
`20261017T144711682412Z-ccab5ebd78544f0fbc7a2f443f9ef4dc`, and compact report/
real app implementation
`20261017T145149287864Z-a89161b6732d43739b7c3386712b9647`.

Sources: existing state/console, three dispatch command/result records, additive
result reviews for mutex/alternate/realloc under `../evidence/`, practical goal/
worklist/reconciliation, existing PROGRESS.md, and external-owner reviewer findings
at14:48:42 and14:54:40. Supervision started no launcher/build/guest/cleanup and
rehashes no shared execution artifacts. Next adjustment: keep next-case assembly
and review ahead of the runtime slot while the module admission fix proceeds.

## Review 4 — 2026-10-17 15:25:11 UTC

Interval: `14:55:37` to `15:25:11` UTC, 29m34s. Campaign/worker/app-server
identities verified live. Practical goal remains active; next review15:55UTC.

| Measure | Review 3 interval | This interval |
| --- | --- | --- |
| New accepted actual McKernel diagnostic/app behaviors | 3 | 2: closed-read and useful dynamic-libc memory |
| Invocation total | 7 | 9, all with independent retirement acceptance |
| Actual matched native-module compile | 0 | 1 invocation: all three Rust modules compiled/linked, make0 |
| Accepted new artifact set | 0 | 1, through corrected artifact-only validation; original receipt remains FAIL |
| New-module Running/native shutdown/restoration proof | 0 | 0 at cutoff; lifecycle packet reviewed next |
| Included weekly usage | 16% | 17%; existing stop97% |

**Application gains:** adapted closed-read launched14:57:19.263, owner0/35.098s,
independent PASS by14:59:51. Covers EBADF and first/last buffer sentinels only.
Dynamic-libc core memory launched15:18:55.587, owner0/38.104s, independently
accepted15:22:01. Exact24-byte stdout, empty stderr and expected application
exit37 pass. Actual malloc,256KiB mmap/data checks, mprotect read/read-write
roundtrip, mapped write, munmap and free work. This is the first current942
useful dynamic-libc core app in this campaign. It does not prove forbidden-write
fault enforcement, broad VM stress or native OS restoration. Process-retirement
EAGAIN followed by success remains retained in both captures.

**Native build:** the matched-module owner launched15:11:10.484 and completed
15:11:28.512 (18.034s outer invocation, not isolated compiler timing). make0;
all three native Rust modules compiled/linked against retained Linux dependencies.
The driver rejected modules.order because its synthetic expectation used .ko
while pinned Linux6.12 emits .o. Original driver/owner outcome remains FAIL.
Independent owner-retirement acceptance15:13:54 joins14Dockerclients+observer,
exact container removal and three archived/released ownership records. Old
historical records remain untouched.

Corrected parser requires exactly three canonical candidate .o entries; foreign,
duplicate, missing, aliased and .ko entries reject. Fourteen focused tests and a
read-only replay pass actual ELF, vermagic, exports and compiler/source bindings.
Independent ACCEPTED_ARTIFACTS_ONLY at15:16:21 permits staging the existing matched
set. No rebuild or native runtime replay occurred. Honest provenance separates
1769263c module sources from942kernel/image compatibility inputs.

**Pipeline timing:** final build execution review15:09:06 -> launch2m04.484s.
Build-retirement acceptance -> memory launch5m01.587s includes2m27s required
artifact correction/review; artifact acceptance -> launch2m34.587s. Do not count
all five minutes as avoidable. Memory owner result15:19:33.691 -> completion
packet available15:21:26 leaves a concrete coordinator/readback gap of roughly
1m52s. Future successful wrappers will run already-approved exact readbacks in
the same command continuation after positive owner/client retirement, then
notify the reviewer. Canonical paths, bounded fresh ordinary-UID captures and
uncertainty stop rules remain. Dispatcher acknowledged15:23:17.

**Useful parallel work:** a real Rust std app now has source/reference review,
static GNU compile/reference and59-member staging/execution review. Its unchanged
144-byte oracle covers Vec/file roundtrip, String/BTreeMap, joined barrier/mutex
workers and TLS. Static linking removes the missing-libdl dependency; the dynamic
variant remains preserved. No McKernel Rust app runtime credit yet. Retained
dynamic-libc threads mode is separately prepared/reviewed with exact exit37.
The next new-module lifecycle archive preserves60members and changes only the
three matched modules. Strict Running5 -> shutdown0 -> NotBooted0 and raw
independent lifecycle review remain required; expected EBUSY is never a pass.

Shutdown epoch source passed independent review15:24:01 after a production-lint
signature correction. The fixture now consumes actual Started/service body with
production flags; restoring omitted PeerStopped lifetime reproduces the rejection.
Retained evidence supports25Rustcases,9Pythonchecks and5compile controls.
This API remains UNWIRED. Serialized provider/module lease, application/callback
drain and final CPU/memory commit consuming the same live claim remain required
integration work within the practical goal, not deferred qualification.

Practical worklist still has only P-M02-03 closed and no whole M00-M13 area
complete; this does not mean only that fraction of the code is implemented.
Source/actual behavior improved while final-profile checks remain open. Earlier
full-scope estimates are not interchangeable with the new practical denominator.
At the user's ETA request, a7–21day continuous-work planning guess (~14day budget)
was given, explicitly low confidence/not a deadline; reassess after24–48hours of
real native lifecycle/process/VM and app closure rather than extrapolating tokens.

**Next adjustment:** preserve fast module-only iteration, stage/review the next
eligible runtime packet during artifact work, and inline already-approved passing
readbacks. New postcheck predicates should consume actual retained producer
output, and source tests should use production compiler flags/boundaries before
larger execution. Reuse already-accepted source/preparation; no fresh history
audit, unchanged Linux/image rebuild or generic monitoring framework.

Key checkpoints:2558578c reviewed module build;7ff2d5f0 accepted matched artifacts
and libc memory release. Sources: corresponding dispatch command/result records,
new-module attempt/artifact reviews, closed-read/core-memory result reviews and
native-shutdown-epoch-source-20261017-2.json under ../evidence/, plus selected
state/console events. Steering:150239861035 useful apps/build priority,
150635894646 epoch/refill, and152228560482 immediate reviewed readbacks. Supervisor
started no launcher/build/guest/cleanup and rehashed no shared execution artifacts.

At the user's percentage-uplift request after this review, saved a new practical-
scope subjective baseline in practical-engineering-estimate-20261017T152511Z.json.
No prior practical percentage baseline existed at14:47; do not invent retrospective
percentage-point gains or subtract the old comprehensive-scope ranges. Current
estimates are low-confidence engineering judgments; future same-scope deltas need
concrete evidence. M05 remains the main blocker. This changes no acceptance state.

## Review 5 — 2026-10-17 15:55:14 UTC

Interval: `15:25:11` to `15:55:14` UTC, 30m03s. Same campaign, live worker
498255/start3900845 and server498257/start3900851; phase running, no stop.
Included usage18%, existing97% stop. HEAD723d04f1; supervisor owns no runtime/Git.

| Measure | This interval |
| --- | --- |
| Actual guest attempts | 2: new-module lifecycle setup and real Rust std app |
| Newly accepted app behaviors | +1, total10; preceding interval +2 in29m34s |
| Real Rust std | Launched15:42:24.228, ended15:42:58.421;34.197s outer operation; independently accepted15:45:18 |
| Failed new-module lifecycle | Launched15:27:50.700, ended15:28:03.594;12.898s; setup failed before app/probe; retirement accepted15:35:05 |
| New native Running/shutdown/restoration acceptance | 0 |
| New practical milestone/check closure established | 0; actual C/Rust and overlap evidence added to still-open final-profile checks |
| Source implementation | Drain helpers independently PASS_SOURCE_PREREQUISITE,7 actual-body cases; provider integration33 Rust cases/5 compile controls, but independent review BLOCKED_SOURCE |
| Observer correction | StrictRunning5 helper/collector compiled;10 helper cases and4 independent retained-console cases pass,0 skips in final correction |

Rust uses the pinned GNU-static real standard library, not a host-only reference:
exact144-byte stdout, empty stderr, exit0,8193-byte Vec/checksum/file roundtrip,
EOF/removal, String/BTreeMap, two worker threads/barrier/mutex counter2000/TLS.
Native worker lifetimes overlap before either deletion. CPU parallelism,
sustained blocking contention, measured stack properties and native OS resource
restoration remain unproved. All30 clients, owner, container and guest retired.

The reviewed passing-owner readbacks now ran in the same command continuation,
finishing approximately0.06s after owner completion. This removes the prior
manual readback handoff for this pass, not the independent result decision.
Lifecycle retirement to Rust launch was7m19.228s, including binding/checkpoint
work; dispatcher explicitly reported no new admission blocker15:41:38 and
launched46s later. Exact avoidable seconds cannot be isolated. At this cutoff,
accepted Rust retirement to next C-thread launch is at least9m56s with no launch
observed. The earlier conditional review exists; final live admission is underway.

The failed lifecycle packet captured no queried numeric OS status or probe run.
Its legacy boot helper requiresReady4 while the new backend contract requires
Running5; this is a source mismatch hypothesis, not an observed kernel result.
The separate strict5 helper now logs observed/expected status through checked
kmsg and the collector retains raw boot-result fields. Actual-body tests accept5,
reject4 and reject logging failures. Earlier wrapper compile failure and skipped
tests remain preserved without credit. Fresh staging/release is still required.

Provider review found one concrete correctness blocker: after irreversible
native admission closure, application-busy or early IRQ failure can report
pre-effect, causing the outer runtime to restore Running with native gates
closed. Author is correcting the classification or rollback and adding actual
runtime decode/finish/admission regressions for app-busy,pager-busy,early IRQ.
The33 passing fixtures do not close this boundary. No second concrete blocker
was found in same-claim ownership, unlocked joins/removal or paired commit.

**Adjustment:** finish C-thread live admission and execute before noncritical
reporting; keep provider correction and fresh lifecycle staging parallel. The
selected C-thread reviewer explicitly confirmed no new push/fetch/commit gate
for its permitted metadata-only joins. CONVERGENCE/VELOCITY now clarify reuse of
verified consumed code/artifacts while preserving exact releases, resolved
conditional references, live identity/resource checks, HEAD freeze and oneheavy.
Packets explicitly requiring a final release checkpoint remain binding.

Actual results are useful but this window does not establish2x/3x velocity. The
saved15:25 practical percentage baseline stays immutable; no numerical uplift
or historical formal acceptance is inferred from test count or scope deferral.
Next review16:25UTC, latest16:55. Core anchors under ../evidence/:
`practical-rust-std-current942-result-review-20261017-1.json`,
`native-running-lifecycle-failure-review-20261017-1.json`,
`native-shutdown-drain-helpers-source-20261017-1.json`,
`native-shutdown-integration-source-20261017-1.json`; helper expert result under
scratch/native-boot-running-prerequisite-20261017-1/observability-expert-3/.
Steering154855681411 was accepted by server; no supervisor workload or shared
artifact rehash was performed.
