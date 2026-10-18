# OS velocity supervision reviews

User requested 30-minute to one-hour reviews and continuous concrete steering
from the interactive chat. Read [VELOCITY.md](VELOCITY.md) for the method.
Preserve completed entries; append new observations and update only this cursor.
This file describes supervision, not OS acceptance or execution authority.

## Current review cursor

- Supervisor chat: `01a1479e-a9c2-7340-8d88-4313fab04738`; user requested resumed
  steering on2026-10-18. The earlier supervision-goal block at19:41UTC remains
  historical; this inspection does not change goal-tool state or create a timer.
- Engineering campaign: `01a149eb-f950-7f13-95a2-59dfc2918d49`; sole runtime/Git owner.
- Campaign explicitly resumed by the user at`2026-10-18T01:31:35Z`; running with
  an active goal at03:05:43UTC. Worker760063/start8454148 and server760065/start8454153
  are live. Run directory:`.git/os-autopilot/runs/20261018T013135Z-08003bf4`.
  The old19:33UTC stop and its evidence remain in the
  [stop handoff](SUPERVISOR-STOP-20261017T193320Z.md). No automatic policy retry added.
- First baseline recorded: `2026-10-17T13:26:00Z`.
- Baseline interval: `2026-10-17T12:52:42Z` to `2026-10-17T13:24:54Z` (32m12s).
- Active target: user-rebased [PRACTICAL-GOAL.md](PRACTICAL-GOAL.md), scope
  `practical-kernel-apps-v1-20261017`; comprehensive qualification is deferred.
- Last full review: `2026-10-18T03:05:43Z`, review15, interval29m39s.
- User explicitly requested the interactive30-minute supervision loop again.
  Next full review target:`2026-10-18T03:35:00Z`, latest04:05UTC. Continue the
  loop in this chat; no independent OS timer or second dispatcher is installed.
  Exclude the19:33UTC-to01:31UTC stopped interval from velocity.
- Last launcher-reported included usage:4% in the new weekly primary window;
  previous stopped window33% is historical. Existing campaign stop remains97%.
- Current intervention: review15 steering queued as
  `20261018T030752832411Z-8c3ea880a9614859ba3b371595d15f22`. Recovery and the
  user-authorized reserve change are independently accepted. Host54.500GiB,
  scratch14.905GiB at cutoff. Take the first fully admitted build/runtime without
  serializing it behind the separate image-schema correction. Actual-consumer
  checks, short output paths and failure-family classification reduce handoff waste.
- Current invocation independently accepted app/diagnostic behaviors: 15 (signal,
  calloc, file-write/read, TLS, adapted mutex, alternate-signal, realloc-grow,
  adapted closed-read, useful dynamic-libc memory application, real Rust std app,
  useful dynamic-libc threads application, forced pthread contention app,
  actual memory-protection fault/recovery app, bounded vector-preservation app,
  AVX/YMM preservation across the exercised syscall/futex/signal boundaries).
- Separate native3f7b observations: independently accepted quiescent native
  shutdown5->0->0/close0 and public destroy/device-memory release; complete
  one public stop/destroy/release/reboot cycle is now accepted with d99 modules.
- CPU-repair candidate d99edf2f has native second-reservation and reboot evidence;
  practical public-cycle progress1/10. The second-boot workload now passes;
  its acceptance grants no additional final-profile repetition quota credit.
  Complete restoration and remaining repetitions remain open.
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

## Review 6 — 2026-10-17 16:24:58 UTC

Interval: `15:55:14` to `16:24:58` UTC, 29m44s. Same live worker498255/start3900845
and server498257/start3900851; running, no stop. Usage20%, existing97% stop.
HEAD64fac038; source integration checkpoint942d1218. Supervisor owns no runtime/Git.

| Actual operation | Launch UTC | Outer duration | Result |
| --- | --- | --- | --- |
| Original dynamic-libc C threads | 15:56:06.254 | 36.899s | Independent actual-app/retirement PASS15:57:29; total11 |
| Strict5 lifecycle with compiled176 modules | 16:03:22.420 | 34.694s | ActualRunning5 and payload PASS; shutdown reconcile-16/after8; retired |
| Forced pthread contention | 16:08:56.161 | 34.744s | Independent actual-app/retirement PASS16:11:15; total12 |
| Matched shutdown-module build1 | 16:18:10.570 | 5.883s | Full compilation FAIL E0308; independently retired16:21:37 |

**Delivered:** +2 distinct accepted app behaviors, total12 (preceding interval+1
in30m03s), plus the first direct nativeRunning5 observation. C threads prove
overlapping worker lifetimes with barrier/TLS/counter2000/joins and exact25-byte
stdout/exit37. The contention app proves held-mutexEBUSY andETIMEDOUT, then
handoff/join/TLS, exact48-byte stdout/exit0. Both have empty stderr and complete
application/client/owner/container/guest retirement. CPU parallelism, actual
futex sleeping and sustained contention are not inferred.

Strict5 helper observed5/expected5/raw0; the payload ran with exact40 bytes and
exit0. Native probe then observed5 -> shutdown-16 ->8, close0. Actual stage logs:
irq_close0, reset_reonline0, first failed stage reconcile-16. This is concrete
localization of the existing shutdown failure, not a second distinct defect or a
successful native cycle. The generic registration error is failure-masked
procfs_empty, not direct proof of remaining registrations. All25 host clients,
owner/container/QEMU retired. Earlier archive timestamp/precision failures remain
preserved; the additive exact-integer metadata correction passed separately.

Reviewed provider/callback integration reached checkpoint942d1218 after35Rust,
10Python,5compile rejection and2runtime mutation controls. Its full-package build
then exposed BootEpoch::allocate returning AllocError instead of kernel Error;
no three-module output set exists. Independent retirement verified14clients plus
observer, exact container removal and all3ownership-record releases; old seven
records were authenticated, not removed. The sole-tail Ok(Arc::new(...)?) repair
passes3actual-body tests, including ENOMEM/no epoch reuse and exhaustion; old
code reproducesE0308. Independent PASS_SOURCE16:23:25. No corrected build had
run at cutoff; fresh source checkpoint, exact package and release remain next.

Parallel useful source work: dormant fork consumer/prepared-backend joint suite
passes22 extracted-body cases; cancellation publication was repaired. Concrete
module bridge, host alias/TLB revocation and final guest destructorACK are now
implementation lanes. Production non-nullCREATE_PPD stays-95 until those real
boundaries pass. Fork/exec/wait app has independent Linux-reference review.
Memory-protection app independently passes source/Linux review: actual readonly
write fault with exact address/SEGV_ACCERR, restored permissions/mask and cleanup,
61-byte oracle plus6handler rejection controls; no native guest yet.

Handoffs: C-thread decision ->strict5 launch5m53s; contention decision ->build
launch6m56s includes required source/capsule/execution review. Strict5 owner
readback ->contention launch3m24s starts before final independent review and is
not an accepted-retirement gap. Exact avoidable portions remain unknown. These
short mixed windows do not establish2x/3x velocity.

**Next adjustment:** prioritize the corrected matched-module build using retained
unchanged review/profile scope, new exact source pins and a fresh one-shot release;
do not wait for fork completion. Use a free heavy slot for the memory-fault app
while build preparation is pending when its separate release permits it; never
overlap heavy owners or ownership-sensitive preparation. Keep fork implementation moving
through actual bridge/revocation/destructor boundaries, not more dormant-only plans.
No new practical final-profile check closes here (14milestones open;32checks open,
1previous retirement check complete,2unassessed). Saved percentage baseline is
unchanged. Next full review16:55UTC, latest17:25.

Anchors under ../evidence/: native-core-threads-current942-result-review-20261017-1,
practical-pthread-contention-current942-result-review-20261017-1,
native-running-lifecycle-strict5-independent-execution-review-20261017-2,
native-shutdown-integration-source-20261017-2,
native-boot-epoch-allocate-error-source-20261017-1,
native-fork-consumer-joint-source-20261017-1 and
practical-memory-protection-source-linux-20261017-1 (all.json). Build diagnostic
and retirement remain in frozen nsd-c/nsd-o-23e0839d85fe47c4ab296fbe3f5a384c.
Steering160021956942,161453583905,161950017153 accepted by server; supervisor
started no workload/cleanup/launcher and performed no shared artifact rehash.

## Review 7 — 2026-10-17 16:55:03 UTC

Interval: `16:24:58` to `16:55:03` UTC, 30m05s. Campaign running, no stop; live
worker498255/start3900845 and server498257/start3900851. Usage21%, existing97%stop.
HEAD07c76eb7; corrected source3f7b265b. Supervisor owns no runtime/Git.

| Actual operation | Launch UTC | Outer duration | Independent result |
| --- | --- | --- | --- |
| Memory-protection app, current942 | 16:33:45.929 | 33.690s | PASS16:36:43; app total13 |
| Corrected matched shutdown build2 | 16:39:04.727 | 18.664s | PASS16:42:00; all3modules and retirement accepted |
| New-module strict native shutdown | 16:47:22.341 | 34.844s | PASS16:51:55; first successful quiescent native stop |

**Delivered:** +1 distinct app behavior, total13, plus an accepted matched build
and the first direct nativeRunning5 ->shutdown0 ->NotBooted0 ->close0. The478-byte
probe output, clean exit and both unchanged validators pass. Serial records
reconcile result0/effectcomplete. Signal payload40bytes/exit0 and all30client,
owner/container/guest retirement checks also pass. Prior5->EBUSY->8 failures stay
unchanged. This resolves that observed quiescent boundary; it is not a full native
cycle or independent physical-resource restoration proof. Probe explicitly reports
resource_restoration_verified=false. Complete destroy/release/reboot cycles0.

The protection app observes SIGSEGV/SEGV_ACCERR at the exact target address,
unchanged readonly data, restored RW access and restored mask. Its61-byte oracle,
empty stderr/exit0 and complete retirement pass. This is actual protection
behavior, not merely mprotect returning0; broader matrices remain unproved.

Build2 make/driver/owner pass with empty compiler stderr. All60source files stay
exact, and all3ELF/vermagic/compiler bindings pass. IHK and mcctrl rebuild
identically; the SMP artifact carries the shutdown repair. The one allocator
conversion correction is independently reviewed and regression-bound. Failed
build1 and its partial outputs remain retained. Original Linux/image dependencies
were reused under the reviewed profile; this is not final full-recipe replay.

Handoffs: protection decision ->build launch2m22s; build decision ->new guest
launch5m22s includes staging/review/release; lifecycle completion ->review start
2m46s. All13joined capture files were present before review; supervisor165035
directed prompt notification. Avoidable portions are not precisely isolated.
This mixed window does not establish a2x/3x multiplier.

Parallel source progress: fork consumer/private bridge/mirror revocation has39
actual-body cases and2compile controls, with actual C descriptor layout checks.
The private provider has22cases and a C ABI witness. Production CREATE_PPD stays
-95: actual caller/destructor wiring, backend-access drain, authenticated revoke,
queuedRET reconciliation and finalACK hold release remain open. Actual caller
fixture failures are under independent bounded correction; no native fork credit.

Resource-release probe source tests now use the compiled shutdown contract:
CPU1online, OSassignments empty, device reservation128MiB, then OSdestroy/memory
release. Nineteen injected-main scenarios and5parser negatives pass; static tool
compiled, not host-executed. Independent review/collector integration and native
execution remain pending; this subset alone does not prove reboot. Four original
outer summary files were overwritten; the limitation is reported, with inner
commands/streams/source snapshots/invalid build retained. No preservation claim
may hide that loss; subsequent attempts need fresh capture destinations.

**Next adjustment:** independently review/admit the resource boundary, then obtain
one complete boot/workload/stop/destroy/release/boot observation under a fresh
release; the strict-stop packet adds no destroy/reboot authority. Reconcile literal
P-M05-01 and P-M08-01 against the accepted current candidate at normal checkpoint;
both remain open in the observed worklist, as do all14milestones. Do not wait for
unrelated fork completion to record satisfied scoped checks. Keep other M05
resource/repetition requirements open. Use a free cheap lane for selected-profile
FPU/vector preservation across switching/syscalls/signals, while fork caller and
completion implementation continues; keep the two-case queue and oneheavy limits.

Saved percentage baseline stays immutable. No formal qualification is promoted.
Next review17:25UTC, latest17:55. Primary anchors under ../evidence/:
practical-memory-protection-current942-result-review-20261017-1.json,
native-shutdown-external-modules-result-review-20261017-2.json,
native-shutdown-lifecycle-execution-review-20261017-1.json,
native-fork-bridge-revoke-source-20261017-1.json,
native-resource-release-probe-source-20261017-1.json; actual lifecycle captures
under scratch/native-shutdown-lifecycle-dispatch-20261017-1. Steering163247 and
165035 accepted by server. Supervisor started no workload, cleanup or launcher.
The native result verdict is the independent signal_guest_execution_review
message completed16:51:55, joined to those raw captures; the execution-review
JSON is invocation authority, not the result-preservation record.

## Review 8 — 2026-10-17 17:27:01 UTC

Interval: `16:55:03` to `17:27:01` UTC, 31m58s. Same live worker498255/start3900845
and server498257/start3900851; campaign running, no stop. Usage23%, stop97%.
HEADeca77d43; compiled native candidate3f7b265b. Supervisor owns no runtime/Git.

**Delivered:** two scoped practical checks now complete: P-M05-01 native
Ready/Running/shutdown and P-M08-01 matched three-module build/load. All14
milestones remain open; checklist3complete/30open/2unassessed. Accepted distinct
app/diagnostic behaviors stay13, with zero new passes this interval. Complete
stop/destroy/release/reboot cycles stay0. The immutable15:25 percentage baseline
is unchanged; these closures do not imply a measured whole-OS percentage.

One new resource guest ran17:16:33.397–17:17:08.341,34.945s, and failed at the
probe contract. Strict native stop again passed5/0/0/close0. CPU1 was online,
device CPU inventory empty and128MiB/node0 reserved memory visible, but the
post-stop OS CPU query returnedEBUSY. Successful shutdown deliberately closes
ordinary backend admission; status queries bypass that guard. The probe stopped
before the memory query, OSdestroy or device memory release. Independent review
classified RETIRED_FAILED_RESOURCE_QUERY_CONTRACT at17:19:46. All25clients,
owner/container/QEMU retired; no resource restoration, new kernel defect or new
app pass is credited. Preserved result/archive review passed17:21:45.

**Correction:** preserve kernel admission guards and the failed v1 attempt.
Reviewed v2 requires status0 and exact CPU/MEM query rejection(-1,errno16,
linux_result-16), explicitly reporting inventories unavailable. Unexpected
success or another error must stop before effects. Then test close/destroy,
refresh device reservation, release exact chunks once and require empty device
pools/CPUonline. At17:26 the compiled runtime's actual status/admission bodies
returned0,-16,-16 without invoking the ordinary backend; those results passed
the actual C main and strict v2 parser. Negative query outcomes stop early.
Static tool compiled/ELF checks passed without host execution. Independent
source/collector review, fresh proposal/release/live admission remain pending;
v1 must not be replayed. This resource-only scope still adds no reboot authority.

Parallel progress: the vector/FPU payload passed independent source/Linux
review, including signal-marker and corruption negatives. Its native stage
completed at17:26 with60members,54nonoverlay metadata joins, accepted general threads
collector with oversubscribe, actual serializer/evaluator and3negative controls.
Proposal ownership transferred; independent execution review started. No native
vector observation yet. The staged case can use the next fully admitted free
heavy slot while v2 correction proceeds. Reboot sequence tests remain modeled,
not native resource or full-cycle results.

Fork's private in-band caller passed independent source review after40C/Rust
scenarios and4detach cases. Completion implementation has32phase cases; actual
IHK-owned module-pin construction/cancel/accept hooks are still being added.
Codec review found its truncation fixture stopped at an adapter; fresh direct
decoder tests now pass with unchanged production codec, pending review closure.
Authenticated carrier, real backend/revocation/finalACK integration, full build
and runtime remain open. Production non-nullCREATE_PPD remains-95.

**Next adjustment:** finish the concrete v2 review, then obtain fresh resource
execution authority; execute the independently staged vector case as soon as its
own review/admission is complete. Keep the two-case queue and oneheavy limits.
After a real destroy/release pass, advance the separately reviewed reboot/full
cycle. Continue actual fork completion implementation in parallel. This window
has source and criterion progress but no new native behavior pass and does not
establish2x/3x velocity. Next review17:55UTC, latest18:25.

Primary anchors under ../evidence/: native-shutdown-lifecycle-result-review-
20261017-1.json; native-resource-release-failure-review-20261017-1.json;
native-resource-release-v2-source-20261017-1.json;
native-resource-release-collector-source-20261017-3.json;
native-vector-preservation-linux-reference-20261017-2.json;
native-vector-preservation-preparation-20261017-1.json. Practical check closures
are in practical-milestones.json. Steering170255,171123 and172002 was accepted
by the server and adopted. No supervisor workload, cleanup, launcher or shared
artifact rehash was performed.

## Review 9 — 2026-10-17 17:57:25 UTC

Interval: `17:27:01` to `17:57:25` UTC,30m24s. Same live worker498255/start3900845
and server498257/start3900851; running, no stop. Usage26%, stop97%.
HEAD413462da records the vector and public resource results. Current compiled
native candidate remains3f7b265b; supervisor owns no runtime/Git.

| Actual operation | Launch UTC | Outer duration | Independent decision |
| --- | --- | --- | --- |
| Vector preservation | 17:29:43.076 | 36.248s | PASS17:32:15; distinct app total14 |
| Public resource-release v2 | 17:33:50.558 | 34.594s | PASS17:36:23; one destroy/release diagnostic |

**Delivered:** +1 distinct app and the first accepted native public resource
release. Vector output is the exact77-byte four-line oracle, empty stderr/exit0;
tested XMM0–15, MXCSR and x87 state survives raw syscall, blocked futex and
delivered signal. Trace records worker257/futex return0. No AVX/XSAVE/multicore
credit follows. All30clients and owner/container/QEMU retire; lease and root lock are released.

Resource v2 observes strict5/shutdown0/query0/close0, both closed OS inventory
queries returning exactEBUSY/unavailable, successful OS0destroy, refreshed128MiB
device reservation, release0, empty final device CPU/memory inventories and
CPU1online. All four evaluations and complete30client/owner/container/QEMU
retirement pass. No assigned-OS empty inventory, physical/generation identity,
full lifetime restoration, reboot or whole-milestone acceptance is inferred.
Application total stays14; this is a separate resource diagnostic. Original v1
failure stays preserved. Both result archives pass exact13-file integer-metadata
retention review.

**Measured handoff:** accepted vector retirement17:32:15 ->resource launch
17:33:50.558 is95.558s. This is within the five-minute scheduling target and is
an improvement over previously observed gaps; these few mixed cases do not
establish2x/3x overall velocity. After resource acceptance, the next case required
new collector implementation and review, not merely an idle ready-guest slot.

The offline v2 reboot reference passed independent review17:36:32. The one-cycle
collector then passed six focused methods, actual supervised helper handoff and
eight rejection captures; a missing raw-file inventory was corrected additively
without rerun. Stage61members/55nonoverlay metadata joins passes. Execution review
passed conditionally17:55:03 for exactly one second boot after accepted workload,
stop/destroy/release, with fresh append-only kernel-log status5 and snapshots.
Final independent source/protocol/raw-inventory PASS arrived17:56:50: all136raw
files are bound, reviewed source unchanged. Live admission and final metadata
joins still precede invocation. Second OS/resources remain until guest shutdown;
no second native cleanup is authorized. No actual cycle at cutoff; count0.

M07 now records partial native coverage, replacing both unassessed checks with
open assessments. Current checklist3complete/32open; all14milestones open, no new
check closure this interval. The focused feature/state trace found an actual
source defect: save_fp_regs ENOMEM is ignored before restore/switch. The retained
production-body reproducer proves that control flow using mocked boundaries,
not hardware corruption. An isolated pre-runqueue fail-stop repair passed independent source review
17:57:22 after four compilations and42executions across Rust-helper and C fallback
branches, IRQ states and relevant no-switch/idle/exit paths. Both fixture failures
remain preserved. Hardware/XSAVE/allocation boundaries are mocked; panic halts
the calling CPU and can occur before a no-switch selection. Native validation,
recoverable ENOMEM and whole-guest shutdown are not proved. Frozen cycle
artifacts are unchanged.

Fork completion's two review findings are corrected and independently accepted
at17:52:20: separate durable full-key ACK cells survive pending-slot reuse, capacity
fails before effects, and final ACK survives parent mailbox retirement.41actual-
body tests pass; completed receipts are limited to64per generation until justified
authenticated retirement exists. Consumer60case source packet remains separate.
The actual retained carrier and child-referenced LINK are being implemented under
an agreed commit/cancel/seal/final-response ownership contract. Carrier tests are
not yet accepted; production non-nullCREATE_PPD stays-95. No native fork credit.

**Next adjustment:** consume the final cycle evidence closure, complete live
admission and use its one-shot release once; retain any failure and repair its
actual first failed boundary.
Keep FPU correction and carrier/LINK work independent and promote them through
affected builds/runtime only when reviewed. Reuse unchanged inputs, maintain the
two-case queue and oneheavy limits. Do not pre-run obsolete final repetitions.
Saved percentage baseline remains unchanged; no numerical uplift is invented.
Next review18:25UTC, latest18:55. Steering173320,173542,174049,174917 was accepted
and adopted;175629 requests the final bounded cycle join. No supervisor workload,
cleanup, launcher or shared artifact rehash was performed.

Anchors under ../evidence/: native-vector-preservation-result-review-20261017-1.json;
native-resource-release-v2-result-review-20261017-1.json;
native-resource-reboot-sequence-source-20261017-2.json;
native-resource-reboot-cycle-execution-proposal-20261017-1.json;
practical-m07-selected-profile-assessment-20261017-1.json;
practical-m07-active-state-mismatch-20261017-1.json;
native_fp_save_repair_20261017.json. Fork correction report remains
under scratch/fork-adoption-wip-20261017-1/docs/verification/evidence/
fork-provider-completion-correction-20261017-1/report.json.

## Review 10 — 2026-10-17 18:25:56 UTC

Interval: `17:57:25` to `18:25:56` UTC,28m31s. Same live worker498255/start3900845
and server498257/start3900851; running, no stop. Usage28%, stop97%.
HEADd99edf2f58ee44b1a7e9aa726cbb49eee7850248 is pushed/fetched/byte-verified by
the dispatcher. Supervisor owns no runtime/Git.

| Actual operation | Elapsed | Independent result |
| --- | --- | --- |
| First native same-guest cycle, launch17:57:51.178 | 36.447s | Retired failed second CPU reacquisition18:03:30 |
| CPU-repair matched three-module build | 18.15s | Artifact and retirement PASS18:23:57 |

**Delivered:** a concrete native failure localized, repaired and compiled. First
workload, strict shutdown and public resource release passed again. Second helper
CPU1reservation failed before memory reservation, OScreation or second boot;
75bytes/exit1/empty stderr, no fresh status5. Numeric guest errno was not captured.
The compiled shutdown dropped its CPU-device snapshot, while subsequent reserve
required it without reacquisition. Original-source fixtures reproduce-19; ENODEV
is source inference, not an observed guest errno. All25clients, owner/container/
QEMU retired; lease/root lock released. The failed capture remains preserved.

The repair retains module-owned CPU discovery references across successful
reconciliation while clearing OSassignment, journal, veto and resource pins.
Later reserve still checks device/topology/APIC/NUMA identity and online state;
actual controller Drop releases the references after callback removal. Six
actual-body tests pass; original source fails four. Independent source PASS
18:09:08; integration20cases plus compile/mutation controls PASS18:14:38 and the
original15case reclaim suite passes. Fixture changes preserve ownership and
retirement assertions. These tests use deterministic hardware adapters.

Build uses60files/1,205,770bytes, only smp_cpu.rs changed. All three ELF/compiler
bindings pass with exit0/empty compiler stderr. SMP hash82c9021f7491fa8bc6d178fe99e7d4b7b6f90838474a9c91b62ddb8edb3d13f8.
All14Docker clients, fixed observer, owner/container retire; three owned records
archived/released. Accepted artifacts now unblock module-dependent cycle staging.
The fresh short-path cycle2draft reuses unchanged image/helper/collector/oracles;
final module bindings, staging and separate execution release remain next.

**Actual totals:**14distinct app behaviors unchanged; no new app or successful
native cycle this interval. Complete cycles0; checklist3complete/32open; all14
milestones open. Source fixes and compilation are not native fix acceptance or
evidence of a2x/3x throughput gain. The first cycle exposed the CPU-reuse defect
and produced a source-reviewed, compiled repair.

Storage is a concrete preparation constraint. Final build record, not a fresh
measurement: host17,963,380,736B free against17,783,848,960B floor-plus576MiB
reserve, margin179,531,776B; scratch margin3,525,877,760B after its same reserve.
Earlier quoted251MB was an older reserve-adjusted margin, not headroom above
the general16GiB floor. Fresh admission passed the full reserve for this build.
Trim remains separate from a guest that independently passes its own admission.
No trim/deletion ran. Wrapper review found missing competing-fstrim publisher
classification; a narrow identity-aware correction is in progress. Estimated
reclaim2.51GB is optimistic, not guaranteed.

FPU thin preparation is ready for independent review:117MBrequired source,
exact omission/restoration records, full9,760file authority with only process.c
changed, five isolated admission/guard diffs. Estimated peak464MB/reserve512MiB.
No materialization or image build occurred. The reviewed fail-stop repair remains
isolated; original full-tree validation is unchanged. Fork storage and guest
backing prerequisites pass, including the copied operations-table lifetime fix;
provider52case suite passes. Actual pre-MM module-pinned capsule, phase writer,
resolver/LINK and finalRET/ACK joins are still being integrated. No native fork;
production non-nullCREATE_PPD remains-95.

**Next adjustment:** immediately bind the accepted modules and complete the fresh
cycle packet/review/admission; do not wait for unrelated FPU/fork work or routine
notes. Keep thin-source and targeted-trim reviews on independent cheap lanes;
any trim needs exact release, fresh identities and exclusive ownership. Source
checks continue within remaining resources while the single runtime lane works.
Preserve all failures, scratch21 and historical exclusions. Percentage baseline
remains immutable. Next review18:55UTC, latest19:25. Steering180528,180931,181231
and182329 reached the campaign; no supervisor workload, cleanup or launcher ran.

Anchors under ../evidence/: native-resource-reboot-cycle-failure-review-20261017-1.json;
native-cpu-reacquire-source-integration-20261017-1.json;
native-cpu-reacquire-external-modules-execution-proposal-20261017-1.json;
native-resource-reboot-cycle-execution-proposal-draft-20261017-2.json;
native_fp_save_thin_preparation_20261017.json;
native-targeted-trim-preparation-20261017-1.json. Actual build/owner receipts are
under scratch/nsd-c-a7d84db0d8b54b9b94347fd0aff57594/evidence/receipt.json and
scratch/nsd-o-a7d84db0d8b54b9b94347fd0aff57594/owner-receipt.json.

## Review 11 — 2026-10-17 18:54:56 UTC

Interval: `18:25:56` to `18:54:56` UTC,29m00s. Same live worker498255/start3900845
and server498257/start3900851; running, no stop. Usage30%, stop97%. Dispatcher
reports checkpoint230c9654 pushed/fetch-verified. Supervisor owns no runtime/Git.

| Actual operation | Duration | Independent result |
| --- | --- | --- |
| Cycle2, launch18:34:32.244/end18:35:31.190 | 58.947s | One public native cycle accepted18:39:53 |
| One targeted scratch trim | 0.650s | Trim/retirement accepted18:41:22; backing reduction1.004GiB |

**Delivered:** first accepted native boot/workload/stop/destroy/release/boot
sequence. Repaired SMP plus unchanged942image observes Running5, shutdown0,
NotBooted0, public destroy/release and fresh generation2Running5. CPU reacquisition
now has actual native evidence. Owner/client/container/QEMU retirement passes.
This gives public-cycle progress1/10, with no second native stop, physical-identity
or full mapping/callback/reference-restoration claim. App/diagnostic total14 stays
unchanged; no new distinct application this interval. All14milestones remain open;
checklist3complete/32open, including P-M05-02/03open.

The fourth consumer initially rejected the log priority. Matched Linux source
establishes LOG_USER PRI14 for the helper's userspace PRI6 write. A versioned,
exact-PRI14 correction passes all four consumers on the unchanged actual capture;
wrong-priority/freshness/status negatives still reject. Original source and failed
evaluation remain preserved. No new guest was needed for this framing correction.

**Handoff:** module acceptance18:23:57 ->stage ready18:32:42 ->execution review
18:33:46 ->launch18:34:32.244. Review-to-launch46.244s; artifact-to-launch10m35.244s.
Two preparation defects caused avoidable work: an unsupported97%host occupancy
gate and binder field names inconsistent with the accepted receipt. Required
staging/review also occupied the interval; exact avoidable time is unknown.
VELOCITY.md now distinguishes included-account usage from disk byte floors plus
growth reserve. Reuse the corrected binding path. No overall2x/3x claim follows.

Trim reduced actual backing allocation by1,078,071,296bytes, approximately1.004GiB.
Reported discard19,199,012,864bytes is a separate quantity. One execution, no
deletion/resize; filesystem/mount/UUID/backing identity, logical size and historical
leases unchanged. Client groups retired, PIDs absent, mutex27:4free. Post-record
margins after floors plus576MiBreserve: host1,016,901,632B/scratch3,335,053,312B.
These are retained measurements; the next admission must remeasure.

Parallel FPU progress: the exact schedule() merge into main passed independent
review18:53:58, preserving every outside byte and later VM/thread-release bridges.
No changed source warranted repeating42injected tests. The isolated thin build
remains unbuilt: first copy stopped on a tracked symlink after4,866files. Original
authority supports49links; corrected materialization binds exact kinds/link text/
contained regular targets. Three focused tests, document-tamper and filesystem
cases pass; frozen review/new copy still pending at cutoff. Failed tree retained.
This is source preparation, not image/native acceptance.

The new AVX payload passed independent source/Linux review18:51:25. ABI-correct
helper zeroes all16YMM registers, raw-wakes and verifies every lane; primary uses
distinct nonzero patterns. Positive and four intended rejection controls pass.
This repairs the accidental-survival gap. Native CPUID/XCR0, scheduling/state and
retirement still require its released matched-image case; actual libc dispatch
remains unobserved. Accepted SSE2 inputs and failed disassembly are preserved.

Fork's initial consumer82case join is independently accepted source-only. Review
also corrected a mutable payload borrow across READY unlock and unnecessary
exclusive scope references. Author reported starting the next joint check18:54:20,
using actual receipt writers, memory ledger and guest C receiver, with stale/
cancel/earlyLINK controls. No joint result or activation at cutoff; CREATE_PPD
remains-95.

**Next adjustment:** finish the bounded case that executes a real payload after
the second boot. Its generation partition must preserve global error checks,
identity and transient retirementEAGAIN before unique terminal success. Complete
the typed-link materialization review and separately released image build; prepare
the reviewed AVX case within the two-case queue. Use the next fully admitted
useful build/guest under oneheavy ownership while fork integration continues.
Final repetitions await the coherent supported candidate. Saved percentage
baseline stays immutable. Next review19:25UTC, latest19:55. Steering183110,
184222,184622 and185026 reached the campaign. No supervisor workload, cleanup
or launcher was executed.

Anchors under ../evidence/: native-resource-reboot-cycle-result-review-20261017-2.json;
native-resource-reboot-cycle-retention-20261017-2.json;
native-resource-reboot-consumer-correction-20261017-1.json;
native-targeted-trim-result-review-20261017-1.json;
native-fp-save-main-integration-20261017-1.json;
practical-m07-enabled-state-closure-20261017-2.json;
native-fork-initial-consumer-source-20261017-1.json. Original cycle2 dispatch is
scratch/native-resource-reboot-cycle-dispatch-20261017-2; trim nonce is
6d69acc2eccb458ba5fbc17a9f9b1b81, execution_count1.

## Review 12 — 2026-10-17 19:25:03 UTC

Interval: `18:54:56` to `19:25:03` UTC,30m07s. Same live worker498255/start3900845
and server498257/start3900851; running, no stop. Usage33%, stop97%. Checkpoint
2ea020a6 is pushed/verified, including the schedule repair. Supervisor starts no
workload or cleanup and owns no campaign Git integration.

| Measure | Change this interval |
| --- | --- |
| Accepted app/diagnostic behaviors | 14 ->14; no new guest result |
| Accepted public native cycles | 1 ->1; practical progress1/10 |
| New corrected FPU image | Configure/build success; artifact and retirement reviews accepted |
| Practical checklist | 3complete/32open; all14milestones remain open |

The typed-link copy succeeded with6,948entries:6,899private regular files and49
exact links; failed copy preserved. Request preparation completed19:07:07,
eligibility review19:12:40, execution review19:14:51. Guard launch was reported
19:15:57; total guard duration213.151351s includes preparation and retirement,
not just compilation. Artifact review accepted19:20:54; owner/eight-client
retirement accepted19:22:10. Image SHAa0f508540d03819d45da6de78a849ae1241fa988feb9e1a90d997b667ea1b7eb,
7,908,616bytes. Linked code checks FP-save failure and panics before scheduler
preparation/restore/switch. This is the declared942-plus-FPU derivative, not a
claim that all of current HEAD was built or that native AVX behavior passed.

The reviewer identified process.c.o outside the receipt inventory. Steering
192153 requested explicit retention; dispatcher confirmed it19:22:20 at the
reviewed hash/319,704bytes. Both copies are bound by the cleanup proposal. The
stopped container and authenticated ownership records remain retained. A nested-
path cleanup adapter passed14disposable filesystem cases; its source and exact
proposal are under independent review at cutoff. No terminal cleanup/common
release or next heavy admission has yet been observed.

Post-reboot collector source passed19:07:03. Staging then exposed an integration
gap: runner and owner still called the default full-stream evaluator. Four
focused methods exercise both actual host call sites through fresh private
instances; independent review accepted19:19:34. Proposal3 preserves all21runtime
bindings of conditionally reviewed proposal2, pending cleanup and fresh admission. It is
still the d99/942 case, separate from the new FPU image. No post-second-boot
workload result yet. AVX parser source also passed; native case adapter/release
and actual feature/state observations remain pending.

Fork's actual carrier/LINK deterministic interleavings passed independent source
review19:12:00:9selected cases, no native multicore/final-release claim. Early
Kbuild preparation uses the immutable accepted after snapshots and original WIP
base09f43875, not fork-modified61030. A bounded read reproduced Git128: the pack
could not mmap under256MiB. Per-command core.packedGitWindowSize=16m read all17
base blobs within unchanged limits; no Git mutation. Three-way merge preserves
d99 CPU/shutdown sources. Independent review caught omitted ABI1/2 startup-state
handling in three factories and omitted fork-payload shutdown accounting. Both
corrections passed8actual-body tests plus old-byte controls and review19:18:38.
The new63-file candidate/11-tool capsule passed7metadata checks and awaits source/
execution review; no full fork Kbuild yet. Revoke, checked guest destruction,
final ACK and final publication still need their real joined route; activation
remains closed. Parallel source work continues against separate inputs.

**Adjustment:** use the existing focused host check to exercise changed consumers
through both actual runner and owner replay before staging. Preserve wire bytes
and assert that negative-fixture mutations really change their intended target.
Keep the next two cases ready; once cleanup and live admission pass, dispatch the
next useful released operation before report-only work. No new repetition quota,
broad rehash or unchanged-corpus replay is added. Saved percentage baseline is
unchanged. Next review19:55UTC, latest20:25.

Anchors under ../evidence/: native_fp_save_thin_materialization_20261017_attempt2.json;
native-fp-save-thin-image-execution-review-20261017-1.json;
native-reboot-workload-host-source-20261017-1.json;
native-reboot-workload-execution-proposal-20261017-3.json;
native-fork-carrier-link-races-source-20261017-1.json;
native-fork-real-target-source-independent-review-20261017-1.json;
practical-m07-avx-native-proposal-draft-20261017-1.json. Build receipt is
scratch/native-fp-save-thin-preparation-20261017-1/symlink-correction-1/image-owner-work/evidence/receipt.json;
guard capture is scratch/native-fp-save-thin-image-guard-20261017-c42c0dd52667eed862cb8555416d9912/guard-result.json.
Correction report: scratch/native-fork-real-target-correction-20261017-1/report.json.

## Stop event — 2026-10-17 19:33:20 UTC

Service-side cyberPolicy failed native_shutdown_epoch_impl turn01a14b4b and the
launcher interrupted the remaining agents. State19:33:21 is stopped, non-retryable,
exit23, campaign goal paused, no active turns; both launcher processes are absent.
Usage33%, below97% boundary. The last footer misidentifies the failing worker
because later interrupted turns overwrite last_turn. Actual failed identities,
retained work and exact safe commands are saved in
[SUPERVISOR-STOP-20261017T193320Z.md](SUPERVISOR-STOP-20261017T193320Z.md).

Cleanup source correction passed16cases/review and was published. Its fresh
read-only observer was approved19:33:08 but did not run; output directory absent.
FPU stopped container/common/shared records remain intentionally retained.
Post-reboot guest, AVX guest and real fork Kbuild did not launch. Fork final
proposal paths were corrected, but its review was interrupted. AVX review found
strict-type equality and41stage-mtime defects; neither has final acceptance.
Source work is preserved, not resumed by the supervisor. No new M0 closure or
percentage change follows. The historical review entries and saved baseline remain.

## Explicit resume and steering — 2026-10-18 01:35 UTC

The user manually restarted the existing campaign and requested aggressive
parallel engineering again. Live state is running/active; the saved last_error
still contains the historical service refusal and is not a new refusal. The
supervisor started no launcher, build, guest or cleanup and changed no runtime state.

Instruction20261018T013447246345Z-624398be8e5842f589c7fd531ea4f1d8 was accepted by
the server at01:34:47.634UTC. It reiterates the practical kernel/application
target, GPT-6.1 medium/high, four to six useful independent lanes when ready,
prompt review/integration, two prepared cases, artifact reuse and no repeated
broad inventories/hashing or unchanged failure replay. The dispatcher retains
heavy execution and Git ownership, original resource/admission constraints and
the97% included-usage stop. Host free is about16.68GiB, scratch15.13GiB;
packet growth reserves remain necessary.

The resumed FPU read-only observer failed Docker census before cleanup. A
bounded version probe reproduced a Go virtual-address-space initialization
failure under the observer's inherited256MiB RLIMIT_AS; the default version
probe passed. The dispatcher opened a focused resource-repair lane and retained
independent review. This is an observer/tool compatibility issue, not evidence
of a new kernel failure. The AVX metadata worker's missing output ancestor was
reported and the dispatcher explicitly redirected its next step. Post-reboot
release assembly is complete as a draft; final cleanup/admission joins remain.
At01:35:48UTC the dispatcher plus three specialist workers were active. No new
native/guest pass has been accepted in this short resumed interval.

For today's velocity question, distinguish capability from rate. During the
first roughly two diagnostic hours, accepted behaviors rose0->9. Between the
15:25 baseline and the19:33 stop they rose9->14, alongside the first accepted
public native reboot cycle, CPU-reacquisition repair and corrected FPU image.
Those are substantial integration gains; later hourly diagnostic count did not
accelerate, and different tasks do not establish an overall2x/3x speedup. Matched
three-module rebuild invocations took about18seconds; the new image guard took
213.151seconds including preparation/retirement. Preserve these scopes rather
than treating them as a whole-OS completion forecast or benchmark ratio.

## Review 13 — 2026-10-18 02:05:24 UTC

First resumed review: user-run campaign01:31:35 to02:05:24UTC,33m49s. Exclude
the19:33-to01:31 stopped interval. Same live worker760063/start8454148 and
server760065/start8454153, goal active, no stop. Included usage1%, stop97%.
HEAD remains7c2b87de; dispatcher owns integration and the next coherent checkpoint.

| Measure | Accepted change this interval |
| --- | --- |
| Distinct native app/diagnostic behaviors | 14->15: actual AVX/YMM preservation |
| Public native lifecycle | Fresh generation2 boot ran signal workload; no extra final-profile quota credit |
| FPU terminal ownership | Exact stopped-container cleanup/common-record release accepted |
| Kernel source repair | XSAVE copy extent corrected, independently reviewed and integrated; new image/runtime pending |
| Process application | Real Linux fork/exec/wait oracle and cancellation correction pass; native CREATE_PPD gated |
| Practical checklist | Unchanged3complete/32open; all14milestones remain open |

The observer's inherited256MiB virtual-space cap prevented Docker startup.
Focused correction retains Python's cap, allows2GiB only for fixed Docker
children and preserves failed diagnostics. One output-parent review finding
was corrected. Observer/readback passed01:39:51; terminal cleanup took4.238s
and was independently accepted by01:48:48. Both ownership records were archived,
46selected files and503/4-entry inventories preserved, and root/cleanup mutexes
checked unheld. Scratch21 and unrelated retained records remain untouched.

Post-reboot execution followed01:50:13 announcement; independent result review
passed01:54:46. Exact40byte signal results passed on generation1 andgeneration2,
with public stop/destroy/release between them and verified teardown. This closes
the missing actual second-boot workload observation, not complete mapping/callback/
physical-reference restoration or final repeatability. AVX guest was running
01:58:59; independent raw acceptance02:01:29. Full YMM0-15 and selected x87/
control/TOP/MXCSR checks pass across exercised syscall, blocked-futex and signal
paths on one assigned McKernel CPU. XCR0=0x21f, required mask0x7. Each guest joins
30Docker-client identities, positive QEMU/container retirement and three bounded
readbacks. No full ISA/IFUNC/AVX512/multicore credit.

Parallel actual-body regression exposed copy_fp_regs copying1088bytes for a
2696byte XSAVE extent. Original fails the unchanged oracle; xsave_size copy
passes extent/canary/ENOMEM/reuse/absent-source controls and source review.
The accepted AVX imagea0f508 is unchanged and lacks this newer repair. Linux
process oracle and publication/wait cancellation tests pass; native process
creation is unproved. Frozen fork source/tool map now has PASS_SOURCE; its exact
execution decision is the next build prerequisite.

**Adjustment:** obtain frozen fork-build executable feedback without waiting
for reporting. Overlap new FPU image delta, process-driver review and a concrete
remaining application/mapping gap when ready. Read only needed fields from the
35.9MB request, avoiding another full pretty-print under256MiB. Reuse accepted
reviews and refill disjoint lanes; keep two upcoming cases ready. Host16.578GiB/
scratch15.093GiB requires full packet growth admission. No broad inventory,
unchanged replay or supervisor workload introduced. This interval is useful
progress, not a measured2x/3x overall speedup. Next review02:35UTC, latest03:05.

Canonical anchors under ../evidence/: native-fp-save-terminal-cleanup-result-review-20261018-1.json;
native-postreboot-workload-result-review-20261018-1.json;
native-m07-avx-actual-result-review-20261018-1.json;
native-fp-copy-extent-source-integration-20261018-1.json.

## Review 14 — 2026-10-18 02:36:04 UTC

Interval02:05:24->02:36:04UTC,30m40s. Same live worker760063/start8454148 and
server760065/start8454153; campaign active, no service stop. Included usage3%,
stop97%. HEAD24683024 follows4af0547a/3eb6100c integration and corrected fork
publication; exact fetched composite proof is retained.

| Measure | Change this interval |
| --- | --- |
| Accepted native app/diagnostic behaviors | 15->15; no new runtime pass |
| Practical checks | 3complete/32open, unchanged; no percentage uplift inferred |
| Actual fork module builds | Two compiler failures; first positively retired, second quarantined after resource-monitor exception |
| Compiler repair | First six errno sites pass source review and corrected actual build entry; two remaining issues localized |
| Useful file utility | Binary/empty-file, target-libc, error and nine source fault controls accepted; native stage held |
| Disk recovery | 6,483,968bytes trim +72,241,152bytes inactive caches =78,725,120bytes, about75.08MiB allocation reduction |
| Larger capacity action | User explicitly approved exact root-reserve change; not executed at cutoff |

First actual fork Kbuild failed with six unresolved EOVERFLOW references after
5.55s; its container/clients/records retired and were independently accepted.
Six-site errno(-75) correction across five sources preserves checked arithmetic,
with original negative and actual-width zero/max-1/max controls. Initial next-
packet preparation missed tool-row source_relative and then stale REPLACEMENTS/
consumed-byte metadata. Affected correction plus actual load_preparation and
closure consumer checks passed; corrected bytes were published/fetched and77
private copies totaling2,019,774bytes materialized. Next build announced02:28:10,
roughly22minutes after the first failure, including repair/review, publication,
capacity maintenance and final release. This is not isolated compiler time or
a measured avoidable-idle total.

The corrected build found mcctrl_vm's remaining EOVERFLOW and an unused three-
line sysfs_memory wrapper under strict warnings. Narrow advisory repair uses
existing errno conversion and deletes only the uncalled wrapper; warning flags
and closed fork activation remain. Postflight fell about300KiB below the full
floor-plus-reserve predicate. Resource monitoring raised during the wait-client
path, leaving retirement unproven and a live owner holding mutex27:4. Exact
stopped CIDa84d19b5 and three ownership records remain retained. No failure
latch/ledger is reset. Source repair, terminal recovery and a future consumed-
runner fix now have separate workers. New heavy work waits for reviewed positive
retirement/release; restored capacity alone does not prove it.

FPU successor validation is now container-self-contained and passes19controls;
materializer/request source review accepts the CPU-only delta. Its existing
outer release still requires floors+512MiB after preparation: initial headroom
803,520,512bytes, about192MBshort before cache recovery. File utility's unchanged
binary passes exact retained loader/libc and all12version requirements, binary/
empty copy and three errors. Nine instrumented whole-C-source fault cases pass.
Producer/verifier sees real changed input/output bytes; strict consumer38controls
then revealed missing supported CRLF framing. Fix remains pending authentic
overlay and actual runner/owner replay. These are host/source gains, not native
process-creation or file-utility acceptance.

The user's disk-cleanup instruction added bounded host maintenance to this
supervisor's scope. Targeted trim reclaimed6.18MiB, insufficient by itself.
Inactive pip HTTP cache reclaimed13.57MiB; closed application/Go caches last
used2023-2025 reclaimed55.32MiB. UID/type/link/date/no-open-handle checks preceded
removal. Installed packages, user profiles/mail, active Tracker/Conda/current
compiler/browser caches and every OS input/failure remain preserved. Old failed
source copies offer only124.7MBgross and lack complete archive/release proof;
none deleted. Host now16.620GiB, scratch15.062GiB, subject to fresh admission.

Independent reserve proposal review confirms249,919,744blocks at4096bytes,
old reserve12,495,987 ->2,499,198, retaining9.533684GiB and conditionally exposing
38.134724GiB. The user answered "Yes, apply the reviewed reserve change";
instruction023604 conveys explicit authorization of tune2fs -r2499198 on the
bound root device. Existing proposal files remain historical proposal-only
records. Exact execution review and positive prior-owner retirement are still
required;16/12GiB floors, packet reserves and97% usage stop remain. No setting
changed at cutoff. Accessibility change must not be reported as allocation reclaim.

**Adjustment:** finish exact recovery and the approved capacity operation, keep
compiler repair and future monitor/retirement correction parallel, and batch all
consumed source/tool-map/byte-count joins before actual consumer checks and
publication. Reuse earlier six-site evidence. Avoid more paper-only frameworks
or repeated corpus hashing. This interval exposed preparation/resource overhead;
it does not establish doubled/tripled throughput. Next review03:05UTC, latest03:35.

Anchors: ../evidence/native-fork-real-target-build-failure-review-20261018-1.json;
../evidence/native-fork-errno-rebuild-fetched-source-proof-20261018-1.json;
../evidence/native-targeted-trim-result-review-20261018-1.json;
../evidence/host-pip-cache-cleanup-20261018-1.json;
../evidence/host-stale-cache-cleanup-20261018-1.json;
[reserve proposal](HOST-RESERVE-PROPOSAL-20261018.md) and
../evidence/host-ext4-reserve-proposal-review-20261018-1.json.

## Review 15 — 2026-10-18 03:05:43 UTC

Interval02:36:04->03:05:43UTC,29m39s. Same live worker/server identities;
campaign active, no service stop. Included usage4%, stop97%. HEADd23c6ff9
preserves recovery/capacity results and the corrected native capsule.

| Measure | Change this interval |
| --- | --- |
| Accepted native app/diagnostic behaviors | 15->15; no new native pass |
| Practical checklist | 3complete/32open, unchanged |
| Quarantined owner | Positive terminal recovery and mutex release independently accepted |
| User-approved root reserve | Executed once and accepted; about38.13GiB newly accessible, zero allocation reclaimed |
| Live capacity at cutoff | Host54.500GiB/scratch14.905GiB; floors/reserves unchanged |
| Third module candidate | Two-file compiler repair and future retirement fix reviewed;75-blob fetched proof and77-copy materialization pass; exact execution decision pending |
| New FPU image | 6,899regular files+49symlinks copied,141,041,664bytes; request schema correction still pending |
| File utility | Actual runner/owner protocol accepted; static one-guest proposal accepted conditionally; final admission/release pending |

Recovery initially stopped before owner action because Docker reordered five
otherwise byte-equivalent complete mount rows. Independent comparison confirmed
every other field equal. Bounded correction fixes both profile and old/fresh
observation joins;31checks preserve duplicate/count/destination/field/type
rejections. New exact release led to accepted recovery: old PID783155 was
pidfd-bound and joined after controlled retirement, exact stopped container
removed,31clients retired, and all three records archived/released under a
12-event journal. Mutex27:4remains intact and unheld. All75other pinned inputs/
failure generations and the original uncleared transport latch are preserved.
Successful recovery returned02:54:41; independent result acceptance02:58:56.
That return-to-review handoff is an improvement target, not proof every second
was avoidable. No original failed build is relabeled PASS.

The user explicitly authorized the exact reserve change. Reviewed guard ran in
1.11007s and changed12,495,987->2,499,198reserved blocks. Device/UUID/boot/block
counts and scratch backing identity remained unchanged; seven clients joined0,
mutex released, no rollback. Nominal newly accessible40,946,847,744bytes;
observed availability gain40,946,618,368bytes differs by concurrent229,376bytes
of allocation. Allocation reclaimed0. Independent acceptance03:01:12. This
retains9.533684GiB emergency reserve plus the unchanged16GiB workflow floor;
scratch12GiB and all packet reserves remain. Prior caches/trim already counted
in review14 are not counted again.

Two-file compiler correction and future wait/resource-monitor proof fix passed
source review. The latter's ten focused producer/consumer cases preserve failed
command state and prior uncertainty while proving normal direct-child completion
when appropriate. Third63-file closure4d31002d/1,453,567bytes, transitive pins,
real preparation loader and stale-map/size negatives pass. Actual Kbuild still
needed. New FPU source copy passes, but request preparation reaches another
hardcoded schema predicate in its private image owner. A patch-generator anchor
assertion then failed before any change/test; this is a separate fixture failure,
not a second demonstrated failure of the production schema invariant.

File utility framing and authentic archive pass; earlier long QMP path was fixed
by assigning a short nonce root. Seven canonical endpoints82-92bytes preflight
before fixture creation. Actual runner/owner accept positive and reject typed,
duplicate and actual-corruption fixtures. Accepted archive is reused. Static
proposal uses98byte real QMP path, matching a0f/d99profile and three approved
bounded post-join readbacks; no guest run at cutoff.

**Adjustment:** move immediately to the first fully admitted useful build/guest,
keeping FPU schema repair separate. Consolidate changed bindings and actual
consumer checks before publication. CONVERGENCE now distinguishes failure
families by the actual invariant reached; unrelated private generator errors
do not consume a production repair attempt. Genuine repeated same-invariant
failures still escalate; no frozen contract or workload replay is waived.
VELOCITY now asks for endpoint preflight and reviewed exact readbacks in the
post-join continuation where already permitted. No new framework or broad rehash.
This interval restored capacity and closed recovery; it adds no native behavior
or measured2x/3x throughput claim. Next review03:35UTC, latest04:05.

User-requested engineering table is saved separately at
[03:02:55 comparison](practical-engineering-estimate-20261018T030255Z.md): only
M05+5pp/M07+10pp versus the previous table, based on the earlier accepted
second-boot/AVX evidence. No maintenance or unbuilt-source percentage credit.
Original baseline stays unchanged.

Anchors under ../evidence/: native-fork-quarantine-terminal-recovery-result-review-20261018-1.json;
host-ext4-reserve-result-review-20261018-1.json;
native-fork-third-candidate-fetched-source-proof-20261018-1.json.
