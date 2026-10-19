# Tactical plan for faster verified OS progress

Persistent handoff rule: after a whole command/result chain joins, send the
review task with `followup_task` unconditionally. It delivers to an active agent
and wakes a completed one. `send_message` alone can leave completed reviewers
idle. Include exact closed output/report paths and the narrow next review; do
not replay completed work. Check actual active state if the handoff goes quiet.

## Current priorities — review 83, 2026-10-19T23:35:00.735334Z

Distinct native behaviors increased 25 -> 26. Dispatcher deduplication confirms
one new composition: typed AVX payload -> strict stop -> public release -> second
boot. Earlier public-cycle records used a 40-byte signal payload; earlier AVX
records did not assert the whole sequence. This credits one composed case, not
individual stages, vectors or launches. Practical checks remain 11/35; selected
Rust paths remain 17 production/14 native. Whole milestones and engineering bands
are held. No overall OS or whole-Rust percentage is inferred.

Actual public-cycle diagnostic c32f227b and separate physical 9b50f20c accept
one guest/one payload/one post-release boot, with exact 380-byte output and empty
stderr. Closed owner took 62.1847 seconds, outer capture 62.2340 seconds. All30
clients/QEMU/container/lease retired. First observed joined result23:18:30.576,
semantic acceptance23:20:45.934. Second stop, full final restoration, ten cycles,
100 launches, 60-minute mixed workload and non-null FP ownership remain open.
Do not call this a complete native restoration cycle.

A real handoff stall was found: completed stage reviewer was sent notifications
without a new task. Root activated it explicitly. The persistent top-of-file rule
now requires followup_task unconditionally at every closed-result handoff; active
agents receive the task, completed agents wake. Root adopted it. Lifecycle physical
and semantic reviewers were activated promptly at whole join. Use this simple
workflow fix rather than a new monitoring framework or replaying passed stages.

Pin-change SDK request dfe115e7 is independently materialized/accepted fcf9d1f5:
60-file/1,214,162-byte closure, only smp_application.rs changes from the accepted
host pair, 75 copies and a two-command0.115-second chain. All groups absent.
The96-row publication is fetched and the exact build release review has passed.
Fresh heavy admission/compiler/artifact/native proof remain pending. The private
control fixture failures are disjoint from this production-source build boundary.
Current accepted image/module profiles stay frozen while source progresses.

The205 compatibility preparation encountered and fixed two concrete executor
boundaries. Five ownership tests pass, including a leader exiting while a group
member survives, receipt/stat failures and asynchronous stop. Initial stage chain
then refused before outputs because a pinned input was incorrectly subjected to
the single-link capture rule (actual review20986949). Corrected input reading
checks exact saved metadata/hash; captures keep single-link constraints. All7
affected checks passed, review12ae81df. Existing five ownership cases were reused.

Fresh three-command chain passed in50.36seconds under its combined90-second
budget, all children joined/groups absent. Actual stage reviewe4c5475a confirms
matched SDK modules, preserved archive metadata, exact accepted205 image and
unchanged387/254-byte application oracles/startupCPU checks. Native execution is
still separately gated. Author is binding existing N3 owner/runner; latest physical
predecessor, final snapshot and machine hashes remain late. Reuse already-built
ff4fca45/fa398247; do not switch the frozen FP case or rebuild the compute image.

Private provider control parking code is written and source-reviewed in the held
backend context. It uses a stage-0 pending-owner claim, exact callback/payload
validation and a fresh response owner, freezes ordinary publication, and refuses
already parked delivery before legacy RETURN. Restore uncertainty retains original
claim/response rather than relying on a possibly failing Drop identity check.
It writes no receipt and grants no MM revocation/terminal ACK or runtime authority.

First test compile had8diagnostics before tests; source/fixture classification
led to fixture-only corrections: real ACK helper, actualu32counter, read-only test
accessors and observed Arc counts. Corrected source compiles. First test then
aborted because concurrent LINK reused worker201 still held by the parked control.
Earlier assertions are not a test pass. Reviewer is checking a separate real
worker/response for LINK. Preserve both failed runs; change only the fixture if
confirmed. Positive provider, full crate/default/native proof remain incomplete;
weakNULL/CREATE_PPD-95 and release holds are unchanged.

Next tactics: admit the ready pin SDK compiler when its exact source/publication/
release and one-heavy controls pass, while ordinary205/N3/source work continues.
Run the accepted205 matched case when its own static bindings and fresh final
guard are ready, using actual latest physical predecessor separately from module
authority. Use a free existing lifecycle author to prepare second stop/final public
release with established CPU/memory inventory witnesses after the accepted second
boot. Keep original one-iteration proof intact; this must be a fresh explicit
variant, not an accounting upgrade. Prepare repeatability/delivery consumers from
a declared tested tuple. Complete the next real provider response-owner transition,
with distinct concurrent worker identities, before expanding the source scope.
Source-only SDK changes do not require a compute-image rebuild. Reuse passed
proofs; checkpoint coherent source/results once. Optional frameworks remain parked.

Usage84%,13percentage points to97%included stop. Host/scratch44.65/13.643GiB.
No sustained CPU/RAM bottleneck is shown. Preserve oneheavy4CPU/12GiB/noSwap/
512tasks, disjoint admittedCPU6/7ordinary work, aggregate reserves and disk/growth
floors, source/ownership/runtime controls, mutex27:4, Scratch21, failures and WIP.
Next review: 2026-10-20T00:05:00.735334Z.

## Previous priorities — review 82, 2026-10-19T23:03:36.655962Z

Live cursor, 23:20 UTC: first public-cycle diagnostic accepted c32f227b,
physical 9b50f20c. Exact typed AVX payload -> strict stop -> public release ->
second boot all passed in one guest on the matched tuple. This is one bounded
iteration; second stop, full final restoration and repetition quotas remain open.
SDK parent-pin source request dfe115e7/materialization fcf9d1f5 are accepted after
a 0.115-second two-command chain; compiler/publication/release remain separate.
Current Rust pin is pushed in 766805fa; launcher guard is applied, and a private
park-only control response transition is being reviewed. Path counters remain held;
c32f declares one new logical case, pending dispatcher behavior deduplication.
The stage-review handoff stall was corrected; all whole-join result review tasks
now use followup_task unconditionally (persistent rule above).

No additional practical or compute-path closure this interval: 11/35 checks,
25 distinct native behaviors, 17 selected production Rust paths and 14 with
applicable native proof. All whole milestones remain open. Engineering bands
are held, including the saved low-confidence M10 80–90% assessment. A module
load or source primitive does not automatically add a logical case or Rust port.

The matched SDK set completed a real guest run. Independent semantic review
88121b15 accepts all three current modules loaded with FP1e7, exact 380-byte AVX
output, exit 0, empty stderr/procfs and bounded raw/status/control transfer of
49,883/219/63 bytes. Physical a03e987a accepts owner/QEMU/container/lease retirement.
Closed owner duration is 38.3278 seconds; readbacks/decoder also joined zero.
First observed whole join 22:35:59.282, confirmed by actual load/guest evidence,
is 19.03 minutes after artifact acceptance 22:16:57.443: the 30-minute feedback
target was met for this tuple. This is a single measured handoff, not sustained
2x/3x engineering throughput. Formal application/new-case credit, negative-MM
ownership, full ring history and non-null FP proof remain open.

The exact supported recipe and module manifest are saved under the host-pair
native directory. Checkpoint 5252ab57 is pushed/fetched with those accepted
reports and captures. Diagnostic FP1e7 remains its own bounded profile; delivery
and broader application profiles are not inferred from this one AVX run.

Concrete Rust delivery: the historical parent-pin repair passed a focused body
check (08f5c012) but did not apply to production; that failure and held branch are
preserved. Production has no ChildFork/ingress backend. Author then prepared a
minimal current Entry/Remote pin primitive with cleanup retention, rather than
importing an incomplete backend. Exact one-file smp_application.rs patch aac4a248
is independently accepted 83134e83. Three actual-body checks cover identity,
OS generation, overflow, reserved close, reply/final cleanup and 500-iteration
retention; all six removal paths honor the pin and unpinned behavior is preserved.
Patch is integrated and pushed/fetched in 766805fa. No new caller or CREATE_PPD
activation. Full SDK/default-module/native proof of this changed source is pending;
this is useful source implementation, not completion of positive process creation.

Next provider work remains a delivered post-positive control request, retained
response owner and valid terminal release/ACK. Worker also found selectors 2/3
would enter ordinary Linux-fork allocation. A private launcher guard now routes
those controls to explicit unavailable RET, with ordinary clone body unchanged;
source/reply-producer review is active. It creates no fork-sync owner and grants
no revoke/ACK authority. Such refusal is prerequisite negative behavior, not a
substitute for a working positive provider. Keep current-source and held-backend
bases explicit; new compute work remains Rust/reviewed assembly, Linux control
plane compatibility changes retain their existing boundary.

Lifecycle preparation advances independently. Existing public-release -> strict5
reboot adapter passed two positives/four refusals. Composed typed-AVX collector
compiled and passed typed admission 1 positive/11 refusals plus supervised sequence
1 positive/4 refusals. Exact ordinary review 644f69ba released stage/preflight;
actual two-command preparation completed in 9.90 seconds. Genuine stage and typed
parent (101-byte QMP, 18-source closure) are under independent review; snapshot
adapter draft f6fa5ded separates latest native a03 retirement from SDK69 history.
No actual lifecycle cycle or full restoration acceptance yet. Existing logger's
120-second alarm/one launch cannot establish the 60-minute mixed run unchanged.

A spare lane prepares final-profile convergence with already accepted 205 image
ff4fca45/fa398247 and its corrected two-CPU N3 case. Selected ABI comparison finds
no mismatch in 12 header/descriptor rows, six public ABI files, 28 layouts and
accepted import/export evidence. Proposal changes only the module SHA tuple;
startup CPU checks and both application oracles stay fixed. Review is preparing
one whole-chain ordinary envelope for two compression stages and host growth.
Nothing staged/run yet; current FP1e7 cycle retains priority. No new kernel build
is required simply to reuse this already accepted 205 artifact.

Next tactics: finish the first actual lifecycle cycle, with result/retirement
reviewer ready before the last snapshot. Prepare the 205 matched-set case in
parallel and use exact compatibility evidence, without switching frozen FP cases.
Deliver the next concrete provider request/response ownership transition against
the proper source context. Compile coherent host-module changes with the existing
SDK route; a host-only pin change does not by itself require another compute-image
build. Reuse accepted source/engine/ABI evidence, test changed production boundaries
once, and checkpoint coherent code/results. Park optional frameworks. The existing
practical repeatability budget remains 2 boots/10 native cycles/100 actual launches/
60-minute mixed workload on a declared profile, with real resource observations.

Usage 83%, 14 percentage points to the 97% included-usage stop. Host/scratch about
44.79/13.648 GiB; no sustained CPU/RAM bottleneck is demonstrated. Keep one heavy
operation, 4 CPUs/12 GiB/no swap/512 tasks, disjoint admitted CPU6/7 ordinary work,
aggregate reserves and disk/growth floors, source/ownership/runtime controls,
permanent mutex 27:4, Scratch21, all failures and dirty work. Next review: 2026-10-19T23:33:36.655962Z.

## Previous priorities — review 81, 2026-10-19T22:32:32.352241Z

Live cursor, 22:38 UTC: independent review 88121b15 accepts the exact three
matched SDK modules loaded with FP1e7, unchanged typed AVX output (380 bytes,
exit 0), and bounded raw/status/control transfers (49,883/219/63 bytes).
Physical a03e987a independently accepts retirement. This is native diagnostic
and module-load acceptance only: application, negative-MM, full ring history
and non-null FP ownership credit remain open. Artifact-to-first-observed joined
native result is 19.03 minutes (22:16:57.443 to 22:35:59.282), now confirmed by
actual load/guest evidence. The 30-minute feedback target was met for this set.
Deferred review-81 steering was delivered after the timed sequence closed.
Checkpoint 0af5d3b1 preserves the Rust process reference. Provider review957f7a37
identifies premature parent-slot pin release before LINK/ACK; the first Rust
repair transfers durable ownership into ChildFork. Post-positive revoke remains
a separate missing transaction; weak prepare/CREATE_PPD/runtime holds remain.

Practical checks increased 9 -> 11/35: independent 0d600890 supports the
literal P-M06-02 and P-M07-02 using existing accepted thread/futex/error and
supported-profile FPU/vector records. Dispatcher reconciled them at 22:05.
This is recognition of existing engineering, not two new native cases.
Counts remain 25 native behaviors, 17 selected production Rust paths and 14
with applicable native proof. All whole milestones remain open; engineering
bands are held, including saved low-confidence M10 80–90%. No overall OS score.

Checkpoint ae8f1b12 is pushed/fetched, including the check reconciliation and
96-row matching SDK publication. Actual request 2ba04a12 uses the accepted
60-source closure and 75 materialization rows, retaining mailbox33e7 and current
kmsg6b736 together. Source/materialization1536cd16 and final releaseb2914e65 bind
canonical50908672 and physical predecessor080d5bfc. Root used fresh admission.
Actual closed SDK owner duration is21.2544 seconds (root rounded21.30), exit0.
Physical69b2fc61 accepts15clients/42emptygroupchecks/container/three records
retired. Artifactb9ea18d0 accepts all3module/default-consumer/source bindings;
ABI5d31c1f0 joins that exact set to FP1e7. No native loading or negative-MM proof.

Matched native preparation ran19.41seconds onCPU7. Stage3b801a5a verifies eight
outputs, all three actual SDK modules and metadata preservation; only SMP bytes
changed against the previous archive. Existing IHK/mcctrl and image bytes remain.
Fresh parent/100-byteQMP path and typed-runtime preparation are accepted. The
snapshot adapter binds the actual latest SDK retirement and complete three-module
schema, keeping staged-copy descriptors distinct from original artifact identities.
A fixture omitted a modules directory, then a different terminal fixture caught
the wrong exception class; originals remain preserved. Only affected fixture
entries changed, no production predicate relaxation. Corrected terminal fixture
passed in0.0643seconds. Existing source/engine/ABI checks were reused.

Final data32ae1dea, eight-step capture indexc53ffec8 and mapping revieweb253e82
are frozen. Only genuine final snapshot and temporal hashes remain late. At this
review the dispatcher is approaching the snapshot/guard/immediate-launch sequence;
steering is deferred until the timed window closes. No native result yet.
Matched SDK artifact accepted22:16:57.443189UTC; current feedback delay15.6minutes,
target30. Keep this clock separate from older127.6-minute205build handoff and
98.2-minute first IHK corrected diagnostic chain. No sustained multiplier claim.

Concrete new code: static Rust process/exec/wait fixture with exact235-byte oracle.
Linux reference passes with two distinct children, exits37/42, successful self-exec,
missing-execENOENT, pipeEOF, one positive reap and subsequentECHILD per child,
no owned children. Independent8f43d9d0 binds ownership, artifact and toolchain.
This is reference-only; no P-M06-01/native credit or guest authorization.

Its actual native blocker is retained CREATE_PPD/provider/alias/final-ACK work.
The source lane found the caller still reaches a weakNULL prepare function;
retained carrier handles first/LINK and negative-first cancellation but not the
complete positive path. More specific gap: revoke helper rewrites only an
unpublished first return, not after positive return or sealedLINK. That path needs
a delivered control request and retained response owner. Existing author is
inactive; current workers coordinate private retained-candidate work and concrete
Rust transition/body checks. Do not wire an abort-only or incomplete provider
into the default fork path, invent native credit, or expand compute C.

Next tactics: finish timed matched-set runtime and immediately followup the
relevant reviewer after wholejoin. Use genuine raw bytes, unchanged typed AVX
and physical results; no automatic non-nullFP/full-history/negative-MM inference.
Source workers should deliver the first concrete missing positive-provider
transition and focused failure/success check using retained machinery, rather
than another equivalent reference fixture or broad audit. Preserve runtime hold
until full provider/ACK ownership conditions are met. Prepare final-profile
repeatability and delivery consumers while their matched prerequisite settles;
existing practical M12 budget is2boots/10cycles/100launches/60-minute mixed run.

Usage81%,16percentage points to97%stop. Host/scratch44.93/13.664GiB. No sustained
CPU/RAM bottleneck is shown. Oneheavy4CPU/12GiB/noSwap/512tasks, disjoint ordinary
CPU6/7 profiles, aggregate reserves and disk/growth floors remain. Preserve source/
ownership/runtime controls, permanent mutex27:4, Scratch21, failures and WIP.
Next review: 2026-10-19T23:02:32.352Z.

## Previous priorities — review 80, 2026-10-19T22:02:12.515950Z

Live cursor, 22:05 UTC: dispatcher reconciled accepted existing-evidence
P-M06-02 and P-M07-02 under decision 0d600890: 11/35 checks complete, 24 open.
No new runtime case, production/native Rust path or engineering-band increase.
Matched SDK proposal and compatible all-three-module FP1e7 consumer are being
prepared in parallel; old modules remain separate until actual artifact/ABI proof.

No count increase this interval: 9/35 practical checks, 25 distinct native
behaviors, 17 selected production Rust paths and 14 with applicable native proof.
All whole milestones remain open. Engineering bands are held, with M10's saved
80–90% low-confidence reassessment retained. No overall OS or Rust-conversion
percentage is inferred.

Concrete delivery: compiled kmsg source was integrated, pushed and fetched in
257ba169, with all 35 changed files verified. It preserves the earlier Rust
failed-invalidation ownership fix. The two fixes have separately accepted full
SDK/IHK compiler evidence; a single matched module set is now being prepared.
Old modules remain distinct and are not mixed by assumption.

First native logging attempt failed. Three closed failure readers joined;
independent physical dcb627e8 and classification 9ffe7afc preserve the actual
cause: collector saved 133 control bytes against the 128-byte exporter and
existing 63-byte decoder contract. Export fault aliased procfs_empty=false;
no real registration leak was established. Real guest boot, payload exit 0 and
49,795-byte ioctl return are diagnostic evidence only; the attempt stays FAIL.

Affected production save/export/decode check passed one positive and three
refusals, including original bad receipt. Fixture compile failure is preserved.
Corrected collector compile/stage/typed-metadata chain completed in 19.20 seconds.
Stage c71b7042 preserves all 69 raw spans, 60 final entries and unchanged metadata,
boot helper, module and image, changing only init. Snapshot predecessor adapter
d1a218dd accepts genuine native retirement and refuses historical SDK schema.
Existing freshness, resource, identity and live mutex checks are unchanged.

Pre-clock capture mapping 3c5fa906 froze all eight steps. Genuine last snapshot,
assembly, final guard and immediate owner ran in one root control flow. Closed
owner status records 37.2069 seconds, exit 0; three readers and decoder also
joined 0 with groups absent. Physical 080d5bfc accepts all 30 Docker clients,
QEMU/container/lease retirement and preserved permanent mutex identity. Typed
AVX/transport diagnostic review 404527bd accepts exact 380-byte output, exit 0,
empty stderr/procfs, and complete returned snapshot transfer: 49,670 raw bytes,
219 status bytes, 63 control bytes. It explicitly grants no formal application,
new logical case, complete history or non-null FP ownership acceptance.

Measured collector diagnosis-to-first-observed successful whole chain is 15.1
minutes (21:44:29.057 to 21:59:37.781 UTC); first container failure to corrected
container success is 25.4 minutes. This is one concrete repair loop, not sustained
2x/3x throughput. IHK artifact-to-first classified failed diagnostic was 83.1
minutes; artifact-to-first observed corrected chain was 98.2 minutes, missing the
30-minute target. Completed 205 build-to-first-observed native remains 127.6
minutes. Preserve the five-hour observation gap in all wall-time comparisons.

Next tactics: finish one matched SDK source set containing both reviewed fixes,
reuse the accepted 60-file closure and pipe-jobserver recipe, and prepare its
exact native consumer/result handling concurrently. Compiler and guests remain
serialized; ordinary source and case preparation may overlap within profiles.
Existing reviewer is checking P-M06-02/P-M07-02 literal conditions against accepted saved
evidence, without rerunning passed work or converting diagnostics into credit.
Use spare implementation capacity for the next concrete Rust process/thread or
recovery defect after identifying its failing behavior. Optional constructor and
self-retirement framework experiments remain parked.

Full ring history/non-null FP remains open under 2c11: a bounded pointer-only
snapshot does not prove absence of overwritten history or pointer reuse. Fix the
actual proof/implementation boundary if needed; preserve original requirements.
Use one focused production-path check per changed boundary, existing authority
and accepted engine checks elsewhere. Wake relevant completed reviewers with
followup_task promptly at whole join. Checkpoint new source/test/results once.

Usage 79%, 18 percentage points to 97% stop. Host/scratch 45.00/13.745 GiB; no
measured CPU/RAM bottleneck supports changing active limits. Keep one heavy
operation, 4 CPUs/12 GiB/no swap/512 tasks, aggregate reserve and disk/growth
floors, current ownership/source/runtime controls, permanent mutex, Scratch21,
all failures and dirty work. Next review: 2026-10-19T22:32:12.515Z.

## Previous priorities — review 79, 2026-10-19T21:32:10.547622Z

Live cursor, 21:44 UTC: independent classification 9ffe7afc confirms real
Linux/McKernel boot, payload exit 0 with 380 bytes, and successful ioctl returning
49,795 raw bytes. Overall attempt remains FAIL. Actual collector saved a 133-byte
control receipt against a 128-byte exporter and existing 63-byte decoder contract.
This export fault aliases procfs_empty=false; an actual registration leak is
unproven. Correct the receipt producer, retain caps/oracles, and check the actual
save/export/decode path. Three failure readers joined and independent physical
dcb627e8 accepts retirement. No old attempt replay. Source checkpoint 257ba169
pushed/fetched 35 changed files, including already-compiled kmsg source.

IHK artifact-to-first-observed closed diagnostic feedback: 83.1 minutes, based
on 20:21:25.936 artifact acceptance and 21:44:29.057 classification observation.
This closes the feedback clock only: application/FP/history acceptance remains
open and the original failed run is preserved. Saved M10 reassessment now records
80–90% engineering judgment; other bands remain held.

At review time FP was in its timed last-snapshot/assembly/check/launch window.
Steering was deferred until the window closed. The eight callable steps include
three readbacks and host decoding. Current failed-owner status is recorded above;
await closed-failure classification and independent physical review.

Interval gain is full SDK/module validation of the committed Rust ownership fix:
artifact c514083d, physical 950b862a. All three modules compiled, default-consumer/
source/SDK bindings accepted, owner21.55seconds,15clients/42emptygroupchecks,
container/three records retired. Module loading, mixing with current kmsg IHK
and native failed-invalidation ownership remain unaccepted. Reuse exact frozen
FP IHK c396 authority separately from the latest SDK retirement predecessor.

Corrected Linux serial transport compiled and passed CRLF/error-export checks.
Generic120-byte parser versus authentic380-byte typed AVX mismatch was corrected
by reusing the accepted typed CPUID/XCR0 parser and unchanged oracle. Fresh stage
passed18.35seconds and is accepted6d421750: only init changed from78ce5004;
module/boot/metadata/payload/full-source authority unchanged. Host raw retention
must follow actual frames/status/control receipts, bounded export and decoding.

Actual decorated snapshot adapter passed1positive/2refusals; typed-runtime/SDK
correctione71d9f20 and projection8004f701 keep IHK75 as module authority andSDK950
as latest predecessor. Realized owner/runner and101-byteQMP bindings passed.
Pre-clock review binds stage, typed consumer, reports and final guard. Eight-step
callable capture indexccbcb0b2 is frozen; only last genuine snapshot/hashes late.

No new count closure:9/35practicalchecks,25nativebehaviors,17productionRustpaths,
14selectednativeRustpaths;all14wholemilestonesopen. M10 recommended80–90% low
confidence is now saved in the single-milestone reassessment; other bands held.
At review time IHK feedback was pending 70.7 minutes; it is closed as failed
diagnostic feedback above. Completed205 kernel
build-to-first-observed-native remains127.6minutes. No speed multiplier claimed.

A separate lane prepared the exact repository patch for already-built kmsg:
baseline65107→compiled6b736, all14selectedbaseline files match. No shared change
yet; current runtime consumes frozen artifacts/reports, so integration can be
reviewed independently. Preserve the committed mailbox repair and all dirty work.

Ring2c11adb6 still cannot establish complete allocation/release history because
CAP-1 can conceal overwritten prefix/reuse. Native run's diagnostic collection,
unchanged AVX and retirement are separate; no proxy non-nullFP/wholeRust credit.
Review actual data promptly after wholejoin, record timestamp/proof, diagnose the
first real failure and change only affected source/data. Optional frameworks parked.

Usage78%;19points to97%stop;host/scratch45.15/13.77GiB. Oneheavy4CPU/12GiB/
noSwap/512tasks, aggregate reserve, disk/growth floors, ownership/source/runtime
controls, permanent mutex, Scratch21 and every failure remain. One-second sample
showed27.15GiB available/lowCPU/zeroPSI; no sustained resource shortage proved.
Next review:2026-10-19T22:02:10.547Z. Steering deferred until timed launch completes.

## Previous priorities — review 78, 2026-10-19T21:02:05.897177Z

Live cursor, 21:20 UTC: SDK build completed 21.55 seconds, receipt PASS; independent
physical retirement accepted (15 clients joined, 42 empty recorded group checks,
container/three records removed with matching archives). Three-module artifact
review remains. The runtime slot is free; FP binds this latest physical proof
separately from unchanged IHK c396 source authority. Typed runtime metadata check
passed, actual owner/runner and 101-byte QMP bindings included. Corrected collector
stage passed 18.35 seconds and is accepted 6d421750: only init changed. Snapshot
and final exact native guard remain. Short host sample showed 27.15 GiB available,
low CPU and zero memory/I/O pressure. One second cannot characterize sustained
compiler utilization or justify more resources.

Live cursor, 21:12 UTC: SDK source materialization accepted 64251613, actual
request186de2e1; accepted pipe-jobserver recipe retained. Publication proof has
96 rows; reviewer and owner-data author are binding exact canonical payload and
launch/admission captures. Heavy compilation remains unrun. Snapshot adapter's
actual decorated caller passed one positive/two refusals with effects stubbed.
Logging transport compiled and its CRLF/error-export checks passed. Full fixture
then found generic120-byte versus typed380-byte AVX-consumer mismatch; rebind
the previously accepted typed CPUID/XCR0 parser/oracle. No guest or new credit.
Preserve prior archive and fixture failures; corrected collector needs fresh stage.

Interval delivery: reviewed Rust failed-invalidation repair, portable tests and
preserved failures pushed/fetched in 36a475ef. Six actual-source cases and the
changed existing test pass. Negative MM clear retains its reservation/response;
full SDK/module/native error-path proof and automatic retry remain unproved.
No extra practical/native-path closure: 9/35 checks, 25 native behaviors,
17 production Rust paths, 14 selected native Rust paths; all whole milestones open.

FP1e7 upstream and logging stages passed in 18.10/18.40 seconds. Logging acceptance
78ce5004 verifies seven outputs, 60 entries and exactly three changed members.
Reuse those artifacts as the preserved baseline. Native preflight then found
guest-local ring files were never exported to the host. Implement bounded serial
transport/host decoding for raw bytes, status and receipts, separate from payload
stdout. Any changed collector stage needs its own reviewed variant; preserve
78ce5004. The other native blocker is the case snapshot adapter; reuse pinned
collection functions and exercise the actual caller with effects stubbed.

Native boundary 465893ab conditionally accepts existing engine, parent and 101-byte
QMP path. The next diagnostic run checks log collection, unchanged AVX and retirement.
Evaluator 2c11adb6 cannot prove complete FP allocation/release history: CAP-1
occupancy may hide overwritten prefix and pointer reuse. Keep full-history,
same-boot and non-null FP ownership credit open; no synthetic native acceptance.

IHK c396958b artifact/physical/ABI/full-catalog joins remain accepted.
Artifact-to-native feedback is pending 40.7 minutes, beyond 30-minute target.
Keep its timing separate from the completed205 build-to-first-observed-native
handoff (127.6 minutes). Current delay is source/transport/schema work, with no
demonstrated CPU/RAM shortage or sustained throughput multiplier.

Fresh SDK module validation for the Rust fix has a source-bound owner/capsule
proposal: retained 60-source basis, only reviewed mailbox33e7 changed. Carry the
already accepted GNU Make4.4.1 pipe-jobserver flag/proof into a separate proposal;
keep strict special-file inventory. Review/materialize actual request and admit
one heavy compiler operation when free while ordinary transport work continues.
Do not replay spent requests or change frozen FP artifacts.

Self-retirement/constructor experiments stay parked. Finish concrete fixes and
the diagnostic run, preparing result/retirement handling in parallel. M10's
recommended engineering band remains80–90% (low confidence), pending canonical
reconciliation; other bands held. Save current comparison snapshot privately.
Usage76%;21 points to97%stop. Host/scratch45.21/13.84GiB. Preserve one heavy,
4CPU/12GiB/noSwap/512tasks, aggregate reserve, disk/growth floors, source/ownership/
runtime checks, permanent mutex, Scratch21 and all failures. Next review: 2026-10-19T21:32:05.897Z.

## Previous priorities — review 77, 2026-10-19T20:31:56.191864Z

Live cursor, 20:57 UTC: Rust ownership fix and portable tests pushed/fetched
36a475ef. Six actual-source cases plus the corrected existing test pass; full
module/native and automatic retry remain unproved. Fresh SDK-module owner/request
preparation reuses the retained 60-source basis with only mailbox33e7 changed.
Current frozen FP inputs remain untouched. Logging stage passed 18.40 seconds,
independently accepted 78ce5004: seven outputs, 60 entries, exactly native-boot,
init and ihk.ko changed; metadata/payload oracle/authority preserved. Native packet
is for diagnostic log collection, unchanged AVX and retirement. Ring evaluator
2c11adb6 is insufficient: CAP-1 occupancy can conceal overwritten prefix/history.
Full history, same-boot association and non-null FP ownership credit remain open.
Prepare native packet and SDK source validation in parallel; heavy runs serialize.

Live cursor, 20:45 UTC: first real upstream derivation refused before creating
an output directory. Both producer/stager joins confused output_sha256 (compressed
archive) with overlay_sha256 (uncompressed appended suffix). Reviewer/owner are
correcting both against saved actual metadata; preserve the refusal. No guest ran.
The one-file failed-invalidation Rust repair is independently accepted 06ded67a
for source integration after six focused cases. Failed MM clear retains claim/
reservation and blocks premature publication/reuse. Full module/native proof and
automatic WAIT-loop retry remain unproved; frozen logging inputs are disjoint.

Live cursor, 20:39 UTC: private FP1e7 derivation proposal v2 is ready; actual
identity plus tiny transformations passed 3 positives/8 refusals in 0.114 seconds,
CPU7 released. Real archive, genuine stage manifests and non-null FP ring-event
evaluation remain pending ordinary review/release; no guest yet. The unchanged
Rust mailbox reproduced the ownership bug: failed clear -14 became an ordinary
response, publication succeeded and the response claim was released. The private
repair targets only this transition, retaining the exact reservation; preserve
successful completion and valid-retry behavior. No fix acceptance is claimed yet.

Interval gains: practical checks 8 → 9/35 (25.7%); selected native Rust paths
11 → 14. Production paths remain 17 and distinct native behaviors 25. All 14
whole milestones remain open. M10's independently recommended engineering band
is 80–90% (low confidence), from 70–85%; canonical estimate reconciliation is
pending, other bands held. Do not derive engineering percentages from check counts.

Current205 N3 is accepted: application f55c5600, physical 5f83f3ca. One guest,
two completed apps, exact 387/254-byte outputs/exits 0, 1.353 seconds of overlap,
all CPUs match including child startup CPU1. This validates the affinity repair;
new logical cases zero. Whole invocation 44.239 seconds. Native path review
a9721a27 adds TID release, time accounting and hash detachment; no UTI/non-null FP,
clear-FP or hardware credit. P-M10-02 is complete 0fb93aa7; no duplicate rebuild.

Build-to-first-observed closed native feedback is 127.6 minutes, versus target 30;
the timer is closed with accepted invocation proofs. Preserve the distinction
between actual execution completion, first observed result and later acceptance.
The dashboard now records gains in native Rust paths as well as practical checks.

IHK module c396958b is accepted c0ad09a6, physical 75a15c7d; 1,475,952 bytes,
13 compiler inputs, 21 exports, 36 resolved kernel imports; conditional pairing
with retained SMP/mcctrl accepted. Owner 5.741 seconds, all 15 clients/container/
three records retired. Full original-authority join 6c53b908 reuses records with
no source-tree rescan. Module artifact acceptance was 20:21:25.936213 UTC; native
ioctl feedback remains pending 10.5 minutes after that acceptance.

Critical next work: produce genuine native/overlay manifests for the FP1e7 image
required by the existing logging contract. Existing AVX stage identifies e85;
derive the actual image member with the accepted metadata-preserving transform.
No substitution of image205. Reuse retained helper/stager/authority records.
Freeze and review only the affected ordinary boundary, generate the archive once,
then bind genuine stage/module authority and fresh native admission. Prepare the
existing native result/retirement handling while staging completes.

A separate actor is reproducing and repairing the failed-invalidation ownership
path using the existing Rust harness, with error/close/cancellation, worker/serial
identity and success cases. Keep that code private/disjoint until reviewed.
It is concrete implementation work; avoid another optional framework experiment.

Image self-retirement experiment is PARKED before its 20:41 cap: one saved positive
and four phase refusals passed. The capture consumer requires joined owner/guard
and retained container; same-owner retirement conflicts. No production delta,
deployment or measured saving. Earlier constructor experiments remain parked.

Usage 75%;22 percentage points to 97% stop. Host/scratch 45.28/13.90 GiB. Current
one heavy operation, 4 CPUs/12 GiB/no swap/512 tasks, aggregate reserve, disk/growth floors,
ownership/source/runtime controls, permanent mutex, Scratch21 and all failures
remain. More CPU/RAM requires a measured useful bottleneck; none is established
for the current source/schema handoffs. Next review: 2026-10-19T21:01:56.191Z.

## Previous priorities — review 76, 2026-10-19T20:01:40.608988Z

Live cursor, 20:27 UTC: image self-retirement experiment PARKED before its cap.
Actual-source probe passed one saved positive/four phase refusals. Postbuild
requires joined owner/guard and a retained container, so same-owner retirement
cannot be reused without changing that contract. No production patch, deployment
or demonstrated saving. Keep it parked. IHK full authority-record join passed;
FP logging still needs genuine native/overlay manifests for image 1e7. Historical
AVX stage identifies e85; derive the image member using the accepted transform.
Do not substitute image205 or replay the completed N3 test.

Live cursor, 20:23 UTC: IHK artifact accepted c0ad09a6, physical accepted
75a15c7d. Module c396958b is 1,475,952 bytes; 13 compiler inputs, 21 exports,
36 resolved kernel imports; conditional retained SMP/mcctrl ABI pairing accepted.
Owner took 5.741 seconds and self-retired all 15 clients, container and three
records. Artifact review timestamp: 20:21:25.936213 UTC. Staging/load/native ioctl
remain unaccepted; non-null FP logging preparation runs separately. No repeated
full kernel build is needed. Future image self-retirement experiment is private,
20:41:05 UTC cap, no deployment or demonstrated speed benefit yet.

Live cursor, 20:12 UTC: independent path-delta review a9721a27 confirms applicable
native Rust paths 11 → 14: TID release, time accounting and thread-hash detachment.
Production paths remain 17, distinct native behaviors 25, practical checks 9/35.
UTI replacement, non-null FP release, clear-FP and hardware obligations stay open.
These counts cover selected paths and do not measure whole-kernel Rust conversion.

Live cursor, 20:11 UTC: bounded independent M10 engineering reassessment recommends
80–90% (low confidence), from 70–85%, following the fresh build and matching
two-CPU native replay. Remaining: final supported delivery profile, usable pinned
recipe and matched image/module manifest with valid dependency reuse. Reuse the
accepted build/replay when consumed identities match; do not repeat it for scoring.
This is a proposed engineering-band update, not whole M10 closure or a conversion
of 2/2 checks to a percentage. Canonical reconciliation is queued; other bands held.
Campaign native review supports three existing Rust paths (TID release, time
accounting, hash detachment); recorded total confirmation pending. No UTI or
unobserved FPU-release credit. IHK's 13 ordinary metadata checks passed and exact
command is ready; root still owns release installation/live admission/compiler.

Live cursor, 20:09 UTC: actual N3 application PASS f55c5600 and physical PASS
5f83f3ca. One guest, two completed apps, exact 387/254-byte outputs and exits 0,
1.353-second overlap; all delivery/return CPUs match, including child startup
CPU1. Clone-affinity repair is validated; new logical cases zero. Whole invocation
44.239 seconds. P-M10-02 independently supported 0fb93aa7 and canonical ledger
now 9/35 (25.7%); all whole milestones remain open. Native/Rust counts are held
pending the existing per-path reviewer. First observed closed native feedback
20:05:01 UTC ends build-to-feedback at 127.6 minutes; this is distinct from later
application acceptance. Existing IHK kmsg build admission is being prepared in
parallel under root ownership. Do not replay the successful N3 iteration.

Live cursor, 20:04 UTC: all six typed steps and existing index-1 caller argv are
independently bound (b3fa3102). Actual physical/config binding, fresh snapshot,
assembly and final guard passed. Root invoked the exact native dispatcher
immediately; the whole command is active. Guest/application result and physical
retirement remain unconfirmed. Review the closed execution and all three
readbacks; repeat no preparation and keep the original startup-CPU assertion.

Independent physical acceptance 0f832641 is complete: current build container,
ownership records, lease and quarantine absent; groups empty; permanent mutex
available. Nine journal records, two ownership archives and all 74 retained-file
FD rows are verified. All 37 pairs and both failed observer attempts are retained.
Cleanup/postjoin passed in 6.854/0.966 seconds. Repeat no completed terminal stage.

N3 is the critical path: bind genuine physical data and configuration through the
existing accepted caller, finish the actual per-step command data and capture
directories, then take the final snapshot, assemble, review and launch immediately.
The caller's index 1 verifies report bytes and captures a command; it does not
install a release. The final checker still controls execution. Snapshot reserve
format (384 MiB) and required live margin (640 MiB above floors) stay distinct.
Native packet, ordinary acceptance 09532853, image and archive remain unchanged.
There has been no new guest or native feedback from this image.

Build-to-native delay is 124.3 minutes against the 30-minute target.
This interval closed physical retirement, with no additional milestone check,
native behavior or Rust-path acceptance: 8/35 checks, 25 native behaviors,
17 production Rust paths, 11 applicable native Rust paths. All 14 milestones and
engineering estimate bands are held. Source/config/toolchain recording P-M10-01
is saved in pushed/fetched checkpoint 16c00687; correction sources in 62a218fd.

Use the [metrics dashboard](VELOCITY-METRICS.md) for wall rates and observation
coverage. After real native feedback, record its timestamp/proof and stop this
pending timer. The collector now supports completed handoffs; read-only positive,
pending and three invalid-input checks passed without writing synthetic history.

Do not reopen accepted build/inspection/archive/consumer work. Before the snapshot,
settle every non-temporal CLI argument and capture parent against the actual
caller; no invented six-step interface. Prepare native-result handling from the
existing runner contract in parallel. After accepted feedback, reconcile the
literal clean rebuild/replay and recoverable-next-command checks against actual
current evidence; do not demand a duplicate build merely because old notes cite
admission-only evidence. Whole matched-profile delivery remains separate.

Current blockers are command/schema/handoff work; additional CPU/RAM benefit is
unproved. Preserve the one-heavy 4 CPU/12 GiB/no-swap/512-task profile, aggregate
reserve, disk/growth floors, source/ownership/runtime checks, permanent mutex,
Scratch21 and all failures. Optional framework experiments stay parked. Concrete
disjoint Rust work may advance only without delaying this native feedback.
Usage 74%; 23 percentage points remain to the 97% stop. Host/scratch approximately
45.39/13.91 GiB. Next review: 2026-10-19T20:31:40.608Z.

## Previous priorities — review 75, 2026-10-19T19:31:26.584457Z

Live cursor, 20:00 UTC: independent physical acceptance 0f832641 is complete.
Current build CID, ownership records, lease and quarantine are absent; process
groups empty, permanent mutex available. Nine journal records, two ownership
archives and all 74 FD rows verified; all 37 pairs and failed attempts preserved.
N3 now proceeds through pre-clock physical/config binding, final snapshot,
exact machine decision and immediate launch using its accepted caller interface.
No remaining physical gate or native acceptance is claimed here.

Live cursor, 19:54 UTC: raw-five archive independently matched all five files,
624,640 bytes. Cleanup/postjoin now completed in 6.854/0.966 seconds, children
joined and groups absent; exact current build CID is reported absent. Independent
physical acceptance is pending. Preserve the earlier pre-child capture-directory
refusal. N3 author/reviewer are active with command data and final-delta checks
prepared; take the last snapshot only after genuine physical acceptance. The
recorded snapshot reserve and stricter live free-space requirement stay separate.

Live cursor, 19:41 UTC: corrected source publication 62a218fd is pushed/fetched.
Actual observer, summary and original-five FD metadata stages passed in
2.781/0.174/0.173 seconds; all direct children joined, groups absent and captures
closed. Whole saved-path fixture reached cleanup-draft construction with eleven
compiler sources, three separate terminal imports, 74 FD rows and eight clients.
Raw-five export and its actual review, then separately released cleanup/postjoin
and physical acceptance, remain. Reuse these successful captures; N3 packet ready.

Practical checks are now 8/35 (22.9%), up one literal provenance check from
7/35 (20.0%). P-M10-01 is reconciled in the working canonical ledger using
accepted reports fa398247/f7352de9. This is source/config/toolchain recording,
not new native behavior or full M10 closure. All 14 whole milestones remain open;
25 native behaviors, 17 production Rust paths and 11 native Rust paths are held.
The next campaign checkpoint must preserve/push the canonical update.

Current build-to-native feedback delay is 94.0 minutes, target 30.
The accepted producer took 97.724 seconds (outer 259.023); artifact acceptance
took 45.17 minutes. No resource saturation or 2–3x speedup has been demonstrated.

N3 ordinary stage/consumer/parent is independently accepted 09532853. Frozen
non-temporal packet 11804f5a binds the genuine archive, owner, manifest, parent,
full argv and readbacks. Reuse it; do not re-stage or re-run successful consumers.
After physical retirement, activate its existing owner with followup_task if idle.
Keep the last fresh snapshot and exact final machine decision at the launch edge.

Both root observer failures are preserved and consumed. First: wrong callback
dictionary projection, before output/lock/Docker. Its actual validation path plus
13 refusals passed after correction. Second: during gathering, three terminal
imports polluted the fixed eleven compiler-source roles. Partial output and
three read-only captures are preserved; child groups are positively retired.
A complete 14-file readback passed 0.174 s. Run the complete affected observer path
against that genuine saved prefix, separate the two source maps, then review and
publish only changed sources for one fresh observer/summary/metadata release.
Raw-five, cleanup and postjoin require their genuine preceding outputs and their
own exact decisions. No weakened checks, synthetic success or replay of releases.

Prioritize current terminal/native work and concrete Rust implementation. Parked
constructor/framework experiments remain parked. One spare worker may advance an
existing disjoint Rust compute candidate with a small real check if it does not
borrow the current owners/reviewer, interfere with frozen 205 or delay native
feedback. Do not fill slots with duplicate reviews or new harness frameworks.

Usage 73%;24 percentage points remain to 97% stop. Host/scratch 45.36/13.91 GiB.
Keep one heavy operation, 4 CPUs/12 GiB/no swap/512 tasks, aggregate reserve, disk/growth floors,
ownership/source/runtime controls, Scratch21 and all failures. Change no active
limits; more resources require measured benefit. Next review: 2026-10-19T20:01:26.584Z.

## Previous priorities — review 74, 2026-10-19T19:01:00.299546Z

Live cursor, 19:23 UTC: a second root observer invocation failed during gathering:
three terminal gate imports were added to FULL_SOURCE_SHA256, which must retain
the request's exact eleven compiler sources. Keep terminal imports in the outer
closure. Preserve both consumed observer attempts; review actual effects and the
whole remaining consumer boundary before another privileged invocation. The
callback correction passed its actual validation path plus thirteen refusals,
but that alone did not cover this later map check. N3's ordinary stage/consumer/
parent is independently accepted 09532853; its non-temporal packet is frozen.

Live cursor, 19:15 UTC: corrected N3 remaining consumer passed owner/runner,
PROTOCOL_PASS, exact report, reaped fake process and empty native parent; actual
QMP path is 103 bytes. Independent actual-result review is active. The terminal
observer's first root invocation failed before output/lock/Docker capture: its
validator treated the callback proof block as the callback list. Direct join and
process-group absence are recorded. Preserve the consumed release and failure;
correct that projection against the accepted report, validate the real report
through the affected predicate, then obtain a fresh exact release. No guest ran.
Do not repeat the build, archive, inspections or successful ordinary stages.

The optional case-data constructor is PARKED after two pre-output fixture
failures; no deployment or speed benefit is established. Do not start another
optional optimization before current native feedback. A narrow independent
literal review supports P-M10-01 from accepted source/config/toolchain/provenance
records; canonical reconciliation is requested, so counters remain 7/35 for now.
P-M00-02 stays open pending a fresh exact repaired invocation. Usage is 73%.

Native feedback is pending 63.6 minutes after producer completion, missing
the 30-minute target. The full build and canonical artifact are accepted:
f7352de9 / fa398247; kernel 205410e4, request 8b7b34ed, image ff4fca45,
7,988,768 bytes. Build driver took 97.724 seconds, outer invocation 259.023 seconds.
Build-to-artifact acceptance took 45.17 minutes. Repeat no build or inspection.

N3 normalization and corrected staging PASSED; the genuine archive took 31.37
seconds to stage. Consumer refused a stale expected -initrd path referring to
the earlier failed stage. Correct only the actual consumer argv data and obtain
a remaining-only release; preserve and reuse the archive and normalization.
No guest has run. Kernel structural validation is fixed and passes the actual
image plus 15 malformed variants; collector/application checks stay unchanged.

Ordinary source generation passed after its 126-path check. Its publication
completion and observer constant-loading interface are under exact finite review.
Preserve both assembly refusals; reuse eight unchanged tracked imports and copy
only missing approved rows. Continue terminal observer/raw-five/cleanup/postjoin
preparation in parallel with the N3 consumer correction. Native launch requires
its own positive physical predecessor and fresh admission.

Preservation is accepted c88a63f7: 37 pairs, 74 descriptor records, 33 copies and
four reuses in 0.559 seconds. Transport 0418e0ed passed four copies and fifteen
inspections in 6.135 seconds. All four affinity machine paths are proven,
including the valid inline form. Do not reopen those proofs or replay tools.

Use the [five-minute velocity dashboard](VELOCITY-METRICS.md) to assess outcome
rates, handoff latency, quota and observation coverage. At least seven postbuild
harness failures/refusals explain avoidable rework; these are not kernel defects
or completed checks. Keep complete authoritative descriptors and explicit source,
work and stage namespaces. Derive actual argv from genuine stage data. Start a
cheap real-image structural check while artifact analysis continues when its
ordinary profile permits it; this grants no staging/guest authority.

The private case-data constructor must freeze a result by 19:07:38 UTC or park
with its concrete gap. It uses the existing format; no engine rewrite or automatic
deployment. Keep it off the critical path. On subsequent necessary changes,
prefer pinned callable engines with typed case data to per-case source generation.
Measure preparation/review time before claiming improvement. Explicitly start
ready completed owners with followup_task and verify activity; reuse existing
completed reviews. Avoid generic audits and duplicated unchanged-file checks.

Counters: 25 native behaviors, 17 production Rust paths, 11 applicable native
Rust paths, 7 of 35 practical checks. All 14 milestones remain open; engineering
bands are held. Usage 72%; stop at 97%, leaving 25 percentage points for the run.
Host/scratch about 45.38/13.91 GiB. Keep current one-heavy 4 CPU/12 GiB/no swap/
512 task limits, aggregate reserve, disk/growth floors, source/ownership/runtime
checks, Scratch21 and every failure. More CPU/RAM is authorized when measured
useful; change no active limits. Prior failed-case cleanup and approved scratch
reserve are complete; repeat neither. Next review: 2026-10-19T19:31:00.299546Z.

## Previous priorities — review 70, 2026-10-19T11:59:02Z

Live cursor update, 12:25 UTC: user explicitly approved scratch reserved blocks
576716→288358 on UUID2a5768c8-718d-4914-bdc0-6b32c5a92a52 via the reviewed
sudo -A /usr/sbin/tune2fs -r 288358 /dev/loop36 operation. Root will recheck live
identity and apply after failed-case physical release, before the next workload,
retaining12GiBfloor; measure actual gain. Restore command uses-r576716. No change
has been reported yet. RootNVMe reserve change is already complete; do not repeat.
Recovery route is a NEW fresh full request/workspace with the two include flags
corrected. No adoption code exists; failed whole guard170.56s makes new adoption
engineering slower than the compiler work saved. Original failed request/source/
objects remain immutable. Seven useful lanes include failure cleanup, fresh
request, terminal consumer correction and strict N3 review. Producer validation
and all physical/execution gates still apply.

Live cursor update, 12:15 UTC: the first205 production attempt failed after
nine successful commands. Its relocated full-syscall fixture omitted the quote
include path for an existing ../executer/include/uti.h header. This is a producer
include-path failure; no kernel ABI defect is established and no image passed.
Private correction adds -iquote /src/kernel to both affected commands. Request,
frozen source, original failure and partial build remain unchanged. Failed-build
classification/positive owner+eight-client retirement is accepted a55469e6;
stopped container and records remain held for failure-only physical release.
Preserve twelve finite logs/receipts and the partial tree. No compiler retry or
new heavy operation before independent correction/admission and physical release.
Review any reuse of unchanged successful phases explicitly; never reuse failed
affinity objects. The chronological review below remains historical.

The cached e0d3180a image passed its real FP-thread application and physical
retirement: fef728f6/8c8ec185. Exact254B stdout, empty stderr, exit0, two distinct
workers and both64-round FP checks; guarded whole invocation36.10s, owner plus
three readbacks0. QEMU,30 clients and31 host groups retired, container absent,
lease released. This is a new image proving an existing behavior, so accepted
totals remain25 behaviors/17 production paths/11 native paths/7 of35 checks.
All whole milestones remain OPEN; no unsupported language-retirement credit.

The previous cleanup failure is resolved. Ten corrected-source rows match
19b758bd;16 offline checks passed with44 other functions unchanged. Corrected
cleanup/postjoin0 in6.72/.90s, physical6d6ad764 accepted,42 metadata rows unchanged.
Do not replay cleanup or native preparation. Preserve both original failures.

First final native guard refused an expired snapshot before an owner or guest.
Review age49.23s plus25s command preparation led to launch age74.21s. The prepared
mechanical checker validates in~.04s and honestly rejects expiry; preconstructing
commands reduced second review age to17.72s and allowed the successful run.
Carry this method forward with the original60-second limit. Native feedback took
about89 minutes after a216-second build, still far beyond the30-minute target.
No2x/3x throughput claim is justified.

New205 compiler remains UNRUN. Its exact sources/fresh-output guard are published
8a27bd44; latest physical predecessor8c8ec185 is genuine and available. Finish
final heavy joins/admission promptly. A freed independent peer can perform the
final heavy decision while the existing reviewer freezes the postbuild contract.
Do not delay a fully released production iteration for unrelated drafting.

Before that image completes, settle the one37-role/15-capture interface directly
between binder, artifact reviewer, terminal and N3 authors. Include the real
affinity production caller, compiler/layout/source/ownership proof; use a targeted
callsite witness where needed, without reviving full syscall-DWARF qualification.
Namespace-corrected binder fixture passes1positive/16refusals, but actual205
artifacts remain absent. N3 keeps the original strict startupCPU oracle and
accepted boot helper. Terminal preparation derives command layout from the actual
reviewed producer and counts from37roles, avoiding the current inherited errors.

Refill one freed kernel implementation lane with one coherent Rust/reviewed-asm
batch from remaining live compute C, tied to supported thread/application paths
and a small real check. Keep its candidate private and disjoint from frozen205;
preserve existing correctness fixes, fallback and C ABI glue. The deliverable is
working candidate code and focused evidence, not another history or ledger audit.
No backlog of unrelated private ports or new compute-C implementation.

Usage66%; host/scratch about45.772/12.808GiB. Preserve one-heavy4CPU/12GiB/noSwap/
512tasks,16/12GiB floors plus growth, all evidence/exclusions and97%stop. Optional
reserve authority remains pending. Next full review:12:29:02UTC.

## Previous priorities — review 69, 2026-10-19T11:28:46Z

Live cursor update, 11:46 UTC: physical cleanup is complete and independently
accepted 6d6ad764. Corrected cleanup/postjoin passed 6.72/.90 seconds; exact CID
absent, records archived, 42 artifact rows unchanged. Do not replay cleanup.
The first final native guard refused an expired snapshot before any owner or
guest. A reviewed mechanical late-data check is being prepared before a second
fresh snapshot; keep the 60-second limit and all non-temporal inputs unchanged.
FP ordinary preparation and physical acceptance remain valid. New205 sources
are published, no compiler has run, and its postbuild/N3 source preparation
continues separately. The chronological review below remains historical.

Campaign remains active. Accepted counters are unchanged: 25 native behaviors,
17 production Rust paths, 11 applicable native paths and 7/35 practical checks.
The cached e0d3180a image has canonical artifact and retention acceptance, but
has not run natively. Its driver finished at 10:19:46 UTC; about 69 minutes have
elapsed without native feedback. No throughput multiplier is established.

Current critical blocker: cleanup refused at reviewed-container-profile after
its exact release. Postjoin was correctly skipped. Preserve that invocation and
release, keep physical ownership held, and independently determine effects and
the exact mismatch against captured container/create/owner evidence before any
correction. Activate a concrete implementation owner alongside the independent
reviewer. Do not weaken container identity/profile checks or replay observations.

Terminal publication 0039b202 is pushed/fetched: 105 roles/104 unique files.
Observer, summary and original-five metadata completed in 2.47/.13/.18 seconds;
raw-five export completed in .17 seconds and is independently accepted. These
completed captures remain valid. Any corrected executable must preserve original
sources/proofs and bind its changed execution sources separately and explicitly.

FP native ordinary stage/fixture/parent is accepted 4b571da9: 21.06 seconds,
all 60 archive members preserved, only the image changed, full owner-derived
socket path 103 bytes. The reuse-row schema failure and its bounded correction
are preserved. Final data has conditional acceptance 82af0bae; physical receipt,
latest predecessor, fresh snapshot and exact final machine decision remain.
Do not repeat the accepted preparation or start the snapshot clock early.

New205 source ordinary acceptance cc5fecb5 and corrected guard fixture (one
positive, 17 refusals) are accepted. Its 12 sources match fetched 8a27bd44;
no compiler or guest has run. The next postbuild draft already covers 15 captures
and 37 retention roles: 33 copies, four reuses, 74 FD rows. Review that changed
boundary now, reusing the corrected parser and existing engine evidence. Prepare
the repaired-source N3 variant in parallel with strict startup-CPU assertions and
the correct 37-role contract. Avoid the inherited type/cardinality/profile errors
before the next build, without fabricating future artifacts or executing a guest.

One heavy operation and all original resource/source/ownership controls remain.
Usage is 65%; host/scratch availability about 45.875/12.809 GiB. Keep 16/12 GiB
floors and 97% usage stop. Optional reserve authorization is pending; no mutation.
Next full review: 11:58:46 UTC.

## Previous priorities — review 68, 2026-10-19T10:58:03Z

Live cursor update, 11:18 UTC: canonical artifact 530a21e6 and retention
a0d67aa3 are accepted. Terminal publication 0039b202 is pushed/fetched with all
105 role rows matching; exact observer release, observations/export/cleanup and
physical acceptance remain next. Native ordinary correction, stage/fixture/parent
are accepted 4b571da9; final native data is being prepared without a live snapshot.
No guest has launched. The separate new205 four-stage ordinary run is accepted
cc5fecb5, and the corrected guard fixture passes one positive plus 17 refusals.
Its corrected 12-file publication is frozen but not yet launch-authorized.
Do not relaunch any of those completed ordinary sequences. The immutable review
68 below is preserved separately in VELOCITY-REVIEWS.md; later results above
supersede its pending action cursor. Counters still await scoped reconciliation.

Counts remain 25 accepted native behaviors, 17 selected production Rust paths,
11 applicable native paths and 7/35 practical checks. All whole milestones remain
open. This interval advanced the image handoff, not accepted runtime coverage.

The cached 03a image is e0d3180a (7,968,952 bytes). All four copies and 15
inspection commands completed. Finite preservation is independently accepted
(a0d67aa3): 21 pairs, 42 FD/hash rows, zero mismatches. The first inspection
release failed before effects because its hash included a null field omitted by
the producer; the corrected data-only release ran without changing the producer.

The saved-capture facts consumer needed coherent corrections for disassembler
names, compiler inlining, the existing nm API and relocatable descriptor fields.
Its complete positive and all 11 relevant refusals passed on saved genuine bytes;
the executed facts are accepted. Original failures remain preserved. Canonical
artifact joins, terminal observations/physical release and native feedback remain
pending. The driver finished at 10:19:46 UTC: the 30-minute build-to-native target
was missed, with about 38 minutes elapsed. Do not claim a throughput multiplier.

Finish canonical joins and the prepared finite terminal chain directly. Keep the
native consumer ready for genuine report values. Retain these saved captures as
regression inputs for the corrected parser; reuse its accepted interpretation in
the next source image instead of rediscovering these assumptions after a build.
Do not replay the passed compilation, copies or inspection commands.

The separate 205410e4 callbacks-plus-affinity packet has seven frozen overlays,
28 authority references and 6,948 entries. A source-copy binding gap and stale
metadata were corrected. Two metadata commands passed in 2.4599 seconds, with
CPU6 released. The four-stage ordinary release is 58cae8a7; activate its specific
owner promptly through followup_task after fresh CPU6 admission. Materialization,
new compiler outputs, linked-image acceptance and strict N3 CPU proof are pending.
Keep the current cached source separate; old objects cannot validate the repair.

One heavy operation, source/ownership controls, original CPU/RAM/task limits,
16/12 GiB floors and 97% usage stop remain. Usage is 63%; host/scratch availability
about 45.92/12.809 GiB. Optional reserve permission is still pending; no change.
Next full review: 11:28:03 UTC.

## Previous priorities — review 67, 2026-10-19T10:27:41Z

Condvar is independently accepted on McKernel (22f64306) with physical
retirement df2186e5: exact 75-byte result, empty stderr, exit 0 and all 30 Docker
clients/QEMU/container retired. Accepted native behaviors are now 25; selected
production/native Rust paths remain 17/11 and practical checks 7/35.

The clone-affinity repair passed independent source review and 14 focused checks,
including 256 mask pairs, high/tail/error cases, child-mask installation, lock
ordering, actual C consumers and Linux inheritance. It is integrated and pushed
in 205410e4. Preparation/fixture failures are preserved. Full production crate,
link and strict native startup-CPU verification remain pending; N3 stays failed.

The separate cached 03a remaining-image operation completed with exit 0 in
216 seconds. It adopted nine validated phases without replay and ran one MAKE.
All 491 seed entries committed, all eight clients retired, and all 17 fresh
evidence files plus 12 output/copy descriptors matched. Image: 7,968,952 bytes.
Build/client retirement is accepted. The stopped container and ownership records
are held for actual 15-capture inspection, canonical artifact acceptance,
21-role retention and physical cleanup. No new production/native credit yet.

Finish the exact inspection command set now; reuse the accepted engines and
seven path checks. Report and native-consumer authors should settle the fixed
role cardinality and phase-adoption fields before capture completion. Keep one
owner/reviewer following the entire finite inspection/preservation/release
chain. Do not repeat compiler steps or create per-field review loops.

Prepare the next coherent source image from 205410e4 separately, combining the
four callbacks and affinity fix. It needs a new source identity and fresh outputs
for changed dependencies; never claim the cached 03a build validates the fix or
silently carry old Rust/C objects across the changed graph. Reuse unchanged
toolchain/engine contracts and carry the strict N3 CPU oracle through to runtime.
Keep this source preparation parallel to current inspection, under actual CPU
and storage admission. No second heavy operation while the current one is held.

No whole milestone closed. Usage is 62%; host/scratch availability is about
46.35/12.809 GiB. Keep original floors, one-heavy controls, the 97% stop and all
evidence/exclusions. Optional reserve authorization remains pending; no setting
changed. Next full review: 10:57:41 UTC.

## Previous priorities — review 66, 2026-10-19T09:55:31Z

The failed build is physically released (864478cf): container absent, groups
empty, mutex free, 496 inventory rows and 22 retained-log FD rows preserved.
All host build/evidence trees remain intact. Its producer still failed before
image make; no image acceptance or compiler replay is implied by that release.

N3 ran both real Rust apps on the intended parent CPU assignments, with exact
387/254-byte outputs, exit 0 and 1.697 seconds of overlap. Physical retirement
passed (ba80041b). The retirement parser confused supported EAGAIN retry attempts
with completions; its scoped correction passed four positives and 13 refusals.
Full N3 acceptance remains refused: one FP child startup syscall executed on
CPU0 while its creating thread was pinned to CPU1. Keep that CPU assertion.

A private Rust clone-affinity lane has identified the inconsistency: placement
uses the process eligibility mask, while the child mask comes from its creator.
The candidate snapshots the caller mask within process eligibility, uses it for
selection, and installs it before publication. It shares the affinity writer's
reservation lock and releases it before selection/migration callbacks. Focused
mask, locking, failure-exit and real C-call-site checks remain required. Preserve
the frozen remaining-image source; do not seed changed code with old proofs.

Condvar remains an independent one-CPU case. Its ordinary results, corrected
provenance, interface and static envelope are accepted. N3 physical predecessor
and final command data are bound without a source change; the final checker is
ready. Root takes the fresh snapshot last, obtains the exact machine decision
and executes. Do not delay the valid frozen record with optional refinements.
Continue parser/affinity review alongside actual test feedback.

Remaining-image request 9f04f3a3 and retained compiler artifacts are accepted;
seeding and image make remain unperformed. Give that operation a separate exact
release and genuine admission when selected. No unchanged compiler or parity
replay is authorized merely by a ready proposal. Actual Rust-caller and final
linked-consumer proof remain mandatory.

Totals stay 24 native behaviors, 17 production Rust paths, 11 native paths and
7/35 practical checks. No whole-milestone uplift this interval. Usage is 60%;
host/scratch availability about 46.46/12.810 GiB. Preserve the 97% stop, original
floors, one-heavy sequencing, all failures and scratch21 exclusions. The optional
reserve question is pending without mutation authority. Next review: 10:25:31 UTC.

## Previous priorities — review 65, 2026-10-19T09:25:00Z

The failed build still holds the heavy slot through its stopped container and
common/shared records. Client/owner/guard retirement is accepted. Eleven retained
logs (22 FD rows) are verified, and the failure observer and summary passed.
The metadata child first refused an inherited 2 GiB limit where exactly 1 GiB
was required. Its failure is preserved; only metadata/export were corrected and
completed. Actual readback review and the separate cleanup release are next.

Prioritize that finite physical-release path, then N3's prepared two-CPU test.
Use the exact approved argv and per-stage resource fields directly through the
existing executor; avoid transcribing flags, phase order or common default
limits. This is a small execution-data correction, not another framework or
another broad review. Reuse the successful observer/summary and all unchanged
source decisions. No effects occur before the genuine current release.

The remaining-image request 9f04f3a3 passed the real owner validator; retained
compiler artifacts and their symbol matrix are independently accepted for reuse.
Fresh work/evidence roots are empty. The bounded seed and remaining-image packet
is frozen; no seeding, compiler replay or image make has run. Preserve the failed
tree in place and bind future effects to the accepted source/profile and fresh
physical predecessor. Keep the failure-only authority distinct from image PASS.

Condvar's corrected provenance and all three ordinary stage/fixture/parent
results are accepted. Its native wrapper has conditional source/profile approval;
genuine predecessor, any remaining interface result, fresh snapshot and exact
execution release stay late. N3's actual consumers and non-temporal runtime
freeze are accepted. Continue useful ordinary preparation alongside recovery.

There were no new native behaviors or check closures in this interval. Totals
remain 24/17/11 and 7/35 practical checks; all 14 whole milestones remain open.
Host/scratch availability is about 46.45/12.811 GiB; included usage is 59%.
Keep the 97% stop, unchanged floors, one-heavy controls, all failures and scratch21
exclusions. The optional filesystem-reserve question remains pending with no
mutation authority. Next full review: 09:55:00 UTC.

## Previous priorities — review 64, 2026-10-19T08:53:31Z

The four-callback operation at 19adeb42 failed a producer assertion before
image compilation. Eight compiler steps passed, including both full Rust crates
and both GCC14 process compilations with 109 ABI assertions. Selected C properly
has zero definitions and zero unresolved references for release_process; the
selected Rust crates define it and all four callbacks. The private correction
passed saved-capture regression with the three real symbol tables and six
mutation refusals. Kernel source and later linked-consumer checks are unchanged.

Owner, guard and eight Docker clients have independent positive retirement
acceptance (def58a4f). The stopped container and common/shared records remain
held. Prepare and review the bounded failed-producer retention/physical-release
route using actual terminal facts. Preserve all host source, partial compiler
outputs and failure evidence. Do not demand a successful image report from an
operation that never built an image. No cleanup, remaining-build continuation
or spent-release replay is authorized by this cursor.

N3 two-CPU staging and actual ordinary consumers are accepted. Its exact
non-temporal runtime packet is frozen (39f6f27b); only the genuine predecessor,
fresh snapshot and final release remain late. Condvar Linux timeout and corrected
binary provenance are accepted; stage/fixture/parent completed with three joins
and exit 0 in 12.41 seconds, awaiting independent result review. Continue those
ordinary lanes while failure recovery is prepared; give the next heavy slot to
the first genuinely admitted useful operation after physical release.

For the corrected build, reuse valid outputs where the existing contract permits;
otherwise choose a bounded fresh-workspace correction with the same configured
container paths. Do not invent a resume framework to avoid a short compile, or
replay unchanged semantic/source reviews. Actual Rust-caller and linked-consumer
proof stays required. Keep the ready 15-observation/finite-21 success preparation
for the next real image; the current failure needs its own honest scope.

The 0eca FP-thread workload and physical retirement are accepted. Recorded totals
are 24 distinct native behaviors, 17 selected production Rust paths (up four),
11 native Rust paths and 7/35 practical checks. No additional path/whole-milestone
credit is implied. Preserve all exclusions, actual floors, one-heavy controls and
97% included-usage stop. Usage is 58%; host/scratch availability is about
46.46/12.811 GiB. The optional reserve question is still pending without mutation
authority. Next full review: 09:23:31 UTC.

## Previous priorities — review 63, 2026-10-19T08:21:01Z

Two real guest invocations now exist. The short-parent two-CPU guest reached
McKernel running status and two logical CPUs, but its bootstrap/control query
failed before either app started. Its physical retirement is independently
accepted. The new 0eca one-CPU FP-thread case then completed: owner exit 0 in
35.89 seconds and three readbacks exit 0. Follow-up at 08:27 UTC: the exact
254-byte oracle, two real 64-round threads and physical retirement are accepted
(application dbb53e09, physical e43e8ff9). This credits that workload, not UTI
refill, __replaceTID or non-null FP release. The earlier 113-byte QMP failure was
an owner invocation only; preserve it separately from these real guests.

Finish the new-image retirement decision promptly. Where evidence permits,
issue physical acceptance before deeper path-credit/ledger work, then continue
semantic review against immutable captures while another ready operation runs.
Application failure does not prevent physical acceptance, as the two-CPU case
already demonstrated; genuine ownership uncertainty still blocks reuse.
Both final QMP paths are 101 bytes. The two-CPU control correction compiled and
passed six ordinary commands plus 16 affected discovery checks. Staging and its
new native release remain pending. A new Rust Condvar timeout/mutex-ownership
case is source-only and targets an uncovered P-M06-02 behavior. Preserve the
already accepted 387-byte batch rather than creating another duplicate variant.

The two process resource/cleanup callbacks and configuration-aware TOFU assertion
are shipped in 03a91997, with all 186 fetched files verified. Source review,
126 parity scenarios and two affected compiles passed. Production C-layout,
full-image and native proof for these callbacks remain open. Preserve WIP and
frozen current-image inputs.

The four-callback compiler request is prepared. Codegen/binder and all four
ordinary materialization/request/consumer stages are independently accepted
(1b94b6ad; actual request e9497da4). The actual callback argument map is
8/9/10/17, distinct from capture indices. Heavy source publication, exact
execution review and admission remain pending. The plan covers 109 ABI assertions
and 15 post-build observations, reusing existing full Rust objects. Post-build
adapters are being prepared before compilation finishes. Keep corrected section
and finite-21 machinery; derive counts from bound data. Avoid a new framework.

Recorded totals are 24 native behaviors, 17 production Rust paths (up four from
13, confirmed against artifact review 40ea08b7), 11 native Rust paths and 7 of
35 practical checks. There is no distinct-native-behavior/check uplift yet;
all 14 whole milestones and earlier engineering bands are held. The optional
scratch reserve question is pending with no mutation authority. Usage is 57%;
the 97% stop and existing floors remain. Next full review: 08:51:01 UTC.

## Previous priorities — review 61, 2026-10-19T07:20:02Z

The four-leaf image has passed independent canonical artifact review, including
all four descriptor strings. The 21-pair retention operation is accepted: 17 new
copies and four verified reuses. The actual build finished at 06:05:52 UTC;
terminal physical release is now the dependency before the next native run.
Keep one author and reviewer responsible for the finite terminal chain through
publication, observer/raw-five readback and physical release. Group bounded
read-only calls and reuse unchanged accepted engines and results. Preserve the
original failed observation, DWARF gap, fresh identities and sole-heavy controls.

Prepare both native paths in parallel: the two-CPU application case on the
accepted FP image and the single-CPU continuation on the new 0eca image. Finish
their static fixes before the terminal release. Do not spend their live snapshot
windows resolving source or interface issues. The optional scratch reserve
proposal is nonblocking and must not delay the runtime path or change settings
without the exact authorization it requires.

The two additional process-release Rust callbacks are integrated and pushed in
44541ca9, with source review and focused parity/consumer checks accepted. Their
production image and native proof remain pending. Preserve the frozen four-leaf
build inputs; do not repeat that compiler run or require a compiler per leaf.
The practical Python progress display is shipped in f4a9e440.

Recorded counters remain 24 native behaviors, 13 production Rust paths, 11 native
Rust paths and 7 of 35 practical checks. Reconcile any newly earned production
count at the next natural checkpoint using accepted evidence. All 14 whole
milestones remain open; no percentage uplift is inferred from preparation.
New-image ordinary staging ran in parallel with terminal work, produced its
archives, and stopped on an inherited payload-path mismatch. The payload hash,
size and mode match. Preserve the failed manifest and review a new manifest-only
finalizer plus the remaining fixture/parent commands; do not recompress archives.
The terminal closure is pushed/fetched in d4a77223. Finish its batched observation
and physical release, then run the first genuinely admitted native packet.

There were no new native behaviors or closed practical checks in this interval.
Two source callbacks shipped, but that is not a demonstrated 2x guest-throughput
gain. Before the next compiler cycle, prepare the corrected section-aware
descriptor reader and exact consumer plan while the compiler runs. Reuse its
accepted inputs and collect only genuinely late observations after the build.
The next full review is due at 07:50:02 UTC. Continue evening supervision.

## Previous build status — review59, 2026-10-19T06:19:11Z

Four-leaf production build independently PASS:10phases,71Cassertions,selected+
fallback actualC TUs,bothfullRustcrates,guard/dispatcher0 and ownerclientretired.
Image0eca91b13bd62ab98441104930eda1a63f247fecd939996858b16f90b7480550
is7,962,040B. Do not rerun compiler. Run the ready14postbuild observations with
corrected completion/FD/hash consumer, then21-role retention and reviewed terminal
release. Actual linked-body/native acceptance remains pending; current ownership
records/container intentionally held. Keep soleheavy/mutex controls.

Prioritize ready real execution over new helper preparation. TwoCPUordinary3/25/6
accepted; originalFP1e7 native proposal/metadata ready, ownerfixture needs complete
synthetic inspect schema review. New0eca oneCPUAVX/thread continuation separately
prepared and gated on postbuild/retainedimage acceptance. Reuse fixed oracles and
completedarchives; original0700binary and every failedstage preserved.

Source/review lanes remain parallel; ACTUALCPU6source/cleanup andCPU7readbacks/app
jobs need finite whole-profile handoffs. Full4.1Mchar reviewer dump was caught:
print status/predicate/counts/<=5witnesses, keep rawrecords on disk. No whole-corpus
rereads after compaction. Counts24/13/11,7of35,all14milestonesopen unchanged.
Next fullreview06:49UTC; user explicitly wants continued evening supervision.

## Previous velocity priorities — review58, 2026-10-19T05:49:09Z

Select the first genuinely admitted useful execution. Four-leaf ordinary source/
request/toolchain/consumer chain is accepted; host-backed build requestbc98516d
has separate host16GiB/scratch12GiB floors and does not inherit the IHK target's
extra scratch need. Finish genuine growth/source/ownership/execution review and
get real compiler feedback when its sole-heavy slot is available. No overlapping
root cleanup or shared development-mutex work; no budget/floor reduction.

Cleanup55863886 deterministic mount ordering + bounded drift diagnostics has9
fixtures and focused reviewPASS; old source0c134 preserved. Publish/freeze genuine
new observation9/apply2 bindings and validated checker before the live clock.
Retained obs7/8 canonical comparison is useful regression evidence; failed live
apply difference was unrecorded. No deletion/capacity credit before actual result.

App source and5compile/ELF checks passed. Private base correction preserves all
records except declared bootstrap payload/sizeCRC and retains canonical overlay
rules. Measured compression exceeded20s;45s stage/60s outer is a time-only next
proposal, not replay authority. Execute just remaining admitted commands after
CPU7 handoff. ACTUAL CPU6 source/cleanup versusCPU7 readbacks/app ownership must
join between conflicting jobs; parallel source writing/review should not reserve
idle execution slots. Coherent whole-profile delegation avoids per-command waits.

Accepted native24/production13/nativeRust11 and7of35checks unchanged; all14whole
milestones open. Prior engineering bands held. Usage49%; next06:19UTC. Root owns
Git/releases; preserve this cursor with next checkpoint. No new compute C.

## Previous velocity priorities — review57, 2026-10-19T05:19:09Z

Keep three useful paths concurrent: root owns exact cleanup/live releases;
CPU6 owner executes the complete reviewed four-leaf source binding/materialization/
request-preparation chain; app owner implements and checks the end-to-end two-CPU
stager/collector/evaluator within one existing guest envelope. Delegate whole
approved ordinary profiles so root cleanup does not serialize unrelated writes.
Retain the accepted one-CPU behavior and fail clearly on absent CPU assignments.
No new McKernel compute C; preserve original source/oracles and failure evidence.

Latest real source35a497b2 is pushed/fetched; actual full production/native remains
one coherent four-leaf batch. Two Rust app references and collector compiled,
six real process fixtures accepted. Root Git diagnostic and full observation6
accepted. Observation7 expired during two reviewer-script errors; validate that
checker on retained real evidence before refreshing8. Source/fetched/static
proof is reusable; only fresh live identity/snapshot/release fields need refresh.
Do not start a freshness clock while still writing the checker or apply wrapper.
No deletion/build/guest yet. Actual accepted counters remain24/13/11 and7of35;
all14wholemilestones open. Prior engineering estimate bands held. Next05:49UTC.

## RESUMED — latest explicit user authorization, 2026-10-19T04:48:16.575393+00:00

The user requested evening-long functional OS development and supervision. The
previous stop below is historical and superseded for this invocation. Same saved
thread01a149eb-f950-7f13-95a2-59dfc2918d49 is running/goalactive in
20261019T044732Z-ea212224; watcher1347803,worker1347805,server1347807. Explicit
manual resume envelope accepted; real handoff/tool reads observed. Launcher fix
5c292417 is pushed/fetched (6files);66launcher+75parallel/recovery/CLI testsPASS
and independent narrow lifecycle reviewPASS. New user stops remain authoritative.

Implement → compile/test → debug → commit. Resume disjoint ready Rust source and
application work alongside the actual capacity/IHK critical path. Follow
[EVENING-RESUME-20261019.md](EVENING-RESUME-20261019.md) for per-CPU app concurrency
inside one existing guest envelope; CPU pinning alone does not isolate shared OS
state. Keep original resource/ownership controls and later stop/quota gates.
30-minute substantive review resumes; no measured2–3x speedup claimed. Baseline
24behaviors/13selectedproduction/11nativeRustpaths/7complete28openchecks.

## Historical stop — explicit user request, verified2026-10-19 01:48 UTC

Campaign goalpaused,phase stopped,active_turns empty;watcher1031359,worker1284993
andserver1284995 absent. No heavy workload or active child. Source85468476 is
pushed/fetched; final pause checkpoint646190dc preserves WIP, unfinished Git-owner
fix and exact CURRENT.md/HANDOFF.md. No archive deletion; scratch21/locks retained.
Monitoring and scheduled review are stopped. Resume only after a new explicit
user invocation; the delivery policy below applies to that later run.

## Delivery policy for a later resume — user instruction, 2026-10-19 01:15 UTC

Implement → compile/test → debug → commit coherent code. The user explicitly
rejects review-heavy progress without working implementation. Within an existing
reviewed ordinary profile, run the smallest real check immediately and fix the
observed failure. Do not create a new packet, reviewer turn or approval layer
for every helper, vector, syntax repair, retention edit or routine metadata
projection. Consolidate focused review at the coherent integration/new unsafe
ABI or ownership boundary. Keep root cleanup/guest execution releases, actual
resource controls and original failure evidence. Do not weaken an oracle.

Land tested code in the actual production source/consumer, preserving unrelated
WIP. At coherent checkpoints commit/push source with exact checks passed and
remaining production/native proof; a WIP checkpoint is not acceptance. Do not
collect an expanding queue of private drafts while waiting for whole-OS closure.
Release-TID and time-account batch f5faf9ed has source/ABI preparation PASS;
hash-detach130cbb2a passes60C/Rust cases and linkage after a preserved fixture
correction. Integrate compatible leaves together, reuse existing proof objects,
and pay full production/terminal/native overhead once for the coherent batch.
Fixed FP1e7 artifact remains the functional test baseline until a replacement
actually passes. Preserve accepted compute C correctness fixes; new compute
functionality remains Rust/reviewed assembly.

Immediate execution blocker: scratch ~335MB short of the IHK build's real
reserve. Exact120archive cleanup can recover1.225GiB. Two failed root observations
remain preserved; alias correction7d2825e5/33local cases and attempt3 profile
c9f7baa4 passed focused review. Finish its published-source/fresh-observation/
result/apply chain, then launch the already prepared IHK-only build once genuine
admission passes. Its35-file copy, fetched metadata and conditional static release
are ready. Logging stage authority/format corrections are source-reviewed; actual
IHK ABI, conditional module reuse and native evidence remain pending. Do not make
unrelated kernel-source integration depend on unchanged IHK consumed-source pins.

Keep disjoint implementation/debug lanes active while cleanup runs. After
ordinary capacity recovery reactivate unfinished idle owners, reusing completed
outcomes. Integrated child-capacity isolation12offlinePASS is loaded by workers
started after00:50; live benefit remains unmeasured, primary/unknown/policy/quota/
userpause stays authoritative. GPT6.1 and97%included-usage stop remain.

Measure code integrated, real compiler/runtime outcomes, defects fixed, accepted
functional behavior and blocked minutes. Latest counts24nativebehaviors/13selected
productionRustpaths/11applicablenativepaths/7of35checks; no2–3x speedup established.
Full manifests/captures stay on disk: print selected fields/counts/failed predicates
and a few witnesses. The01:07 e60bb9b3 manifest dump exceeded5million characters;
prevent repeated context cost without rehash, cache clearing or history reset.
Campaign owns Git/releases; supervisor monitors/steers and prepares private fixes.

## Read terminal results while an owner remains alive

The 2026-10-18 IHK attempt wrote a failed terminal receipt within seconds, while
its owner deliberately waited in quarantine to retain the development mutex.
A live owner or held lease alone does not establish that compilation continues.
When a terminal receipt/capture exists, inspect its selected status, exit and
retirement fields promptly; do not wait for the outer wrapper to return before
classifying an already recorded failure. Keep healthy silent operations intact.

Separate compiler failure from client retirement, evidence preservation and
ownership release. Move disjoint source fixes and cheap regressions forward
while preparing the existing finite recovery. Fresh identities, independent
execution review and positive physical retirement still govern release; never
unlink a held record or infer cleanup from an exited container. Measure actual
compile time separately from time blocked on quarantine/recovery. Keep manifests
on disk and print only affected fields, counts and bounded mismatch samples.

Latest user instruction, 2026-10-17: complete the practical kernel/application
goal in [PRACTICAL-GOAL.md](PRACTICAL-GOAL.md), replacing excessive formal
qualification as the active target. Use [practical-milestones.json](practical-milestones.json)
for current M00-M13 exit checks; old contracts and estimates remain historical.
Target twice the useful engineering
throughput, with three times as a stretch experiment. These are targets to test,
not promised speedups or permission to raise estimated percentages without work.
The practical scope explicitly defers large fuzz/exposure/soak quotas and broad
certification. Execution releases, correct behavioral expectations, failure
history, ownership/machine limits and the 97% included-usage stop still apply.

User clarification,2026-10-18: implement new McKernel compute-kernel behavior in
Rust or reviewed assembly. Keep Linux control-plane compatibility C within its
existing allowance; do not add compute-kernel C subsystems or expand C logic as
the migration strategy. Existing cpu.c/process.c correctness fixes remain
preserved and their tested linked paths are live, not verification-only fallback.
Report a concrete exception before integrating a future expansion of compute C.
Practical M09 integration estimates do not measure whole-kernel Rust conversion.
The user further reaffirmed that retiring live McKernel C into Rust is active
work alongside functional delivery; whole-image certification deferral does not
postpone that cutover. Implement the first bounded known live CPU/FPU path in
the existing Rust framework, then name process/scheduling retirement work. Track
C entrypoint, Rust replacement, actual default consumer, tested artifact and
retirement status in the existing cursor. An unused Rust port is not production
cutover. Keep the accepted baseline and reference C/evidence intact while the
replacement passes its affected build and runtime checks.

## What is slowing the current campaign

The current bottleneck is moving a prepared artifact through ownership recovery,
review, integration and actual guest execution. Increasing compiler jobs does
not address that dependency. At the inspected 13:17-13:18 UTC snapshot, the
dispatcher was active and the five specialist lanes had completed. Refill useful
work as results arrive instead of allowing every lane to converge on one handoff.

An idle specialist needs followup_task to start a new turn; send_message alone
only queues a message. At18:07UTC on2026-10-18, completed next-Rust and application
packets awaited review while only the dispatcher was active. Activate those
bounded independent new-change reviews alongside publication/final build binding.
Track completed packets awaiting handoff, and refill useful implementation,
application preparation and review work as each result arrives. Keep unrelated
review decisions out of a ready build's dependency chain.

After an operation's actual direct join and required readbacks complete, notify
its waiting result reviewer before unrelated preparation. Include exact completed
capture/status paths and real join/readback results. The parent checks completion,
status and resource ownership, then delegates the full byte/oracle/retirement
review promptly. If a join is unfinished, state that specific boundary. At19:02
and19:12UTC on2026-10-18, reviewers still awaited this notification after observed
command returns; both handoffs were closed by explicit steering. Track return-to-
notification latency separately from review time. Preserve the no-unfinished-
artifact-read rule, and avoid performing the complete independent review twice.

Delegate the next private candidate's discovery as well as implementation. At20:19-
20:22UTC on2026-10-18 the coordinator investigated the future CPU path centrally
while current terminal publication waited. Moving that work to a specialist kept
the ready image's release on the coordinator's critical path. A completed private
candidate and source review may wait without blocking the active image/native cycle.

Use each accepted producer's actual record shape and canonical encoding. The paired
terminal cycle needed a finite five-file FD metadata read because the summary only
contained hashes. Its first cleanup assembly also appended another role's newline
convention; the unchanged payload matched the reviewed hash without that newline.
Preserve these pre-effect failures. Prepare the full export metadata and numeric
caller caps before release; consume the exact review request's declared convention.
Do not change signed payload bytes or weaken a gate to repair a scaffold. Child
RLIMIT_FSIZE does not cap piped stdout captured in an uncapped parent; future private
check runners must use genuinely bounded captures where their profile requires it.

The four-hour18:04->22:04UTC comparison on2026-10-18 records2 additional accepted
behaviors and3 production/native Rust-path increments, but no new practical check
closures. After the current image's actual artifact review, use the existing
supported-candidate mechanism to hold one exact tested image/profile stable for
its remaining literal functional checks. Keep later Rust implementations private
while that bounded session proceeds; active migration continues. Reuse matching
valid evidence and identify concrete missing execution or code, without another
global accounting audit. Assess existing contract-permitted regression batching
with unchanged per-case oracles, failure stops and real retirement, rather than
introducing a framework or blocking ready work. Count actual launches/cases and
closed checks separately. Do not lower requirements or confuse a scoped functional
image checkpoint with whole-kernel Rust/assembly or overall OS completion.

For future checkpoints, assess compatible independently reviewed Rust leaf changes
for a shared production build/regression cycle where repository rules permit.
Keep the currently frozen attempt stable. Prepare affected postbuild and terminal
inputs during compilation, and run separately admitted cheap application staging
in its available CPU lane. Measure accepted functional outcomes per wall hour and
time waiting for handoffs separately from compiler runtime. Agent occupancy and
additional preparation alone do not establish a2x/3x throughput improvement.

Review41 on2026-10-18 measured a200.543s successful image build against roughly
32minutes in the subsequent inspection/publication/terminal phase. That phase
contains required work; record pure handoff waiting separately. Use the real
canonical producer's metadata and wait-record schema early. Preserve original
records when a declared compatibility receipt is needed, and derive fields from
actual successful waits. For the next candidate, assess source-reviewed save_debugreg
and an eligible privately implemented restore_debugreg as compatible leaf changes
for one future production/native cycle, with independent review and repository
rules. Current frozen attempts remain stable; this is a throughput experiment,
not automatic integration or additional native credit.

For new paired templates, bind linked-symbol requirements, selected source paths
and immediate accepted-baseline descriptions coherently from one pinned role map.
The19:28 advisory found stale paired symbols/baseline fields, and the19:44 final
template review found a selected guard/test list pointing to old files. Both were
corrected before their execution boundaries. Keep heavy-only corrections additive
when the ordinary packet is already frozen. Distinguish a source-copy blocker from
a pending final-release obligation; actual request/source/independent-result joins
must be enforced before build release. Reuse unchanged engine decisions and check
only the affected new bytes/data. Source-only advisory reports grant no workload
authority or milestone credit.

The native control kernel, three Rust modules and matching current942 image
already exist. The native baseline passed diagnostic artifact revalidation;
strict fresh-build reproducibility and runtime acceptance remain unproved.
Signal staging passed its strict manifest and 59 member joins. The next calloc
payload also has a prepared overlay and matching strict manifest. Signal stage
and overlay took about 7.08s and 8.68s; the calloc overlay took 8.21s. Reuse valid
outputs: another unchanged Linux/image build or staging replay adds no behavior.

These are startup observations, not a command to replay work. The latest live
result always takes precedence. Cleanup returned PASS_EXECUTED during inspection;
its required postflight must be joined before the next owner is admitted.

## Immediate execution sequence

1. Finish the current image-cleanup postflight and consume the reviewed result.
   Preserve the original quarantine and failed attempt. If this is already done,
   go directly to the next unmet step; do not repeat cleanup or the census.
2. Finalize the existing signal proposal using its prepared strict manifest and
   only the required fresh live ownership/resource facts. Obtain the existing
   independent execution decision, then run `signal.mask-restore` once in its
   released profile. Frozen expected stdout is
   `handled=1 observed_blocked=1 restored=1\n`, empty stderr, exit0. Capture actual
   guest output, status, kernel trace and required retirement. A manifest PASS
   does not count as this runtime result.
3. While that guest runs, have a different worker finish the already staged
   `memory.calloc-zero` execution inputs, and another bind the next eligible file
   read/write fixture and its independent Linux oracle. Keep the next two cases
   ready; final live admission and releases happen just before consumption.
4. After verified signal retirement, run the eligible calloc diagnostic and
   advance to the ready file fixture. Continue through memory, files, process,
   threads/futex, signals and lifecycle cases according to their dependencies.
   Do not wait for unrelated complete M01-M03 acceptance before a separately
   authorized diagnostic. Formal application acceptance keeps all original gates.
5. A failure stops the affected execution, preserves its bytes and produces a
   concrete repair hypothesis. Reproduce the smallest useful failure under its
   existing cheap profile, repair, then obtain the next appropriate execution
   layer. Use a fresh guest after every failure. Do not repeat an unchanged
   deterministic failure, rename an attempt to reset its history, or consume a
   one-shot release twice.

## Close milestone conditions in parallel

Use the practical worklist's exit checks. Original task rows remain useful
technical references, not a requirement to finish deferred qualification:

| Milestone group | Closure tactic |
| --- | --- |
| M00 | Consume the working launcher, preservation and resource controls. Repair reproduced dispatch blockers only; keep routine bookkeeping off the execution path. |
| M01-M03 | Assign concrete remaining response, collector and VM ownership defects to disjoint actual-body test lanes. Promote each passing boundary to its next eligible native/guest observation. |
| M04-M05 | Turn the current stack into actual applications and then lifecycle/restoration results. Ready payloads and independent oracles feed the single runtime lane continuously. |
| M06-M09 | Implement missing process/syscall/vector behavior and Rust/interface closure by affected surface. Integrate tested coherent changes into a next candidate; preserve the working baseline for unrelated diagnostics. |
| M10-M11 | Advance exact package recipes, reproduction and integration checks when their consumed candidate is ready. Prepare applicable offline inputs in parallel; do not repeatedly package an obsolete candidate. |
| M12-M13 | Run the practical bounded repeatability/mixed workload on the supported final profile, review unresolved correctness risks and deliver runnable artifacts/commands. Huge exposure quotas, external hardware matrices and production certification are deferred. |

The bounded practical mixed run still occupies its reviewed runtime resources.
Overlap cheap source work within the remaining budget; do not run a competing
heavy guest. Deferred hardware/exposure is not a current blocking dependency.

## Keep a small pipeline full

Use the existing task cursor and worker tools. No new dispatcher, tracker,
dashboard or scheduling framework is required. When independent ready work
exists, aim for four to six useful implementation/test workers within the
launcher's measured ceiling. Add a reviewer for a concrete ready decision;
release or reassign finished workers promptly. Fewer useful workers are better
than invented audits. Remote worker count does not multiply local CPU/RAM.

Assign a completed candidate's concrete review at the next dispatch opportunity;
refill its implementation slot with the next ready task in that same cycle.
For an actionable finding assigned to an idle author, use `followup_task` or the
equivalent task-activation operation and confirm a running turn before waiting.
`send_message` queues information without starting an idle worker. A queued
correction is not active implementation. Reviewers may activate the concrete
authorized follow-up directly within the agreed owned scope.
As an operational target, keep avoidable gaps between verified retirement and
the next fully ready guest below five minutes. This is a scheduling target,
not a deadline that overrides live admission or interrupts a healthy operation.
If that target is missed, name the missing dependency in the existing cursor
and put an available worker on its concrete correction.

| Lane | Next useful output | Work that can overlap |
| --- | --- | --- |
| Dispatcher / exclusive runtime | Next actual guest result, retirement, integration and final release | All disjoint cheap lanes within the remaining budget |
| Next payload and oracle | One eligible case with strict inputs, independent expected output and reviewed command | Current guest and disjoint kernel changes |
| Following payload and oracle | A second eligible case ready for the next runtime slot | Current guest and first payload lane |
| M01/M02 implementation | One selected response-ownership or collector descriptor/identity defect repaired with an actual-body reproducer | Payload work and current immutable runtime candidate |
| M03/M06 implementation | One selected pending-free, invalidation or process/VM lifetime defect repaired and tested | M01/M02 only with disjoint write sets and agreed interfaces |
| M05 or next eligible core behavior | Lifecycle probe/tool correction and actual-main checks, then native proof when released | Other cheap lanes; injected syscall results remain scoped |
| Independent reviewer, as needed | One explicit source/ABI/ownership/execution decision with consolidated findings | Unrelated ready work; reviewer does not edit the candidate |

Select actual open packets and current contracts before assigning these lanes;
the table is a menu, not authorization to rerun already passing tests. Relevant
existing checks include selected-retention actual methods, pending-free actual
C bodies, collector descriptor/identity checks and the lifecycle probe. The
retained lifecycle probe already has 26 passing injected actual-main scenarios;
consume that result and seek its next missing observation instead of rerunning
the same scenarios for activity. Do not count it as native shutdown restoration.

Each worker owns one coherent change through its next executable check. Keep at
most one completed candidate waiting for review per lane; help integrate it
before creating another draft. Interfaces shared by two lanes need a named
owner and agreed boundary before either edits. The dispatcher owns integration,
Git, heavy execution and acceptance updates. Ready results should be reviewed
and integrated at the next safe boundary, without waiting for a report-only
checkpoint or unrelated milestone closure.

Within an assigned private write scope and reusable cheap profile, repair routine
fixture/generator mistakes without another permission round. Missing imports,
escaped-text anchors, tool/source row shapes and total-input versus Rust-file
counts are ordinary implementation corrections when the authoritative contract
is unchanged. Preserve the original failing evidence, make the bounded correction
and run the affected check, then report the coherent result. A private scaffold
failure does not itself create a new global readiness gate. Unexpected workload
effects, uncertain live identities, changes outside the assigned scope and changes
to frozen privileged/source/artifact contracts still require the existing stop,
preservation and focused review. Never replay a one-shot workload under this rule.

Before publishing or handing off a changed packet, exercise its existing actual
consumer where the cheap profile permits: source replacement maps, consumed byte
counts, closure/schema bindings and runtime file availability belong in that
check. Reuse accepted unaffected evidence. Imported placeholders or a generator's
own success do not establish that the final preparation/runner/owner can consume
the packet. Consolidate these affected bindings into one reviewable handoff.

When deriving a new candidate from an accepted base, select the current base once
and derive dependent namespace and supplemental/gitlink scalar bindings from it.
Avoid copying predecessor identifiers into an otherwise current packet. Exercise
the existing metadata consumer before request preparation in the assigned cheap
profile; this is one affected check, not a new tracking framework. A metadata-only
correction should reuse a valid source materialization and its accepted evidence.

For an observer/cleanup pair, check the actual cleanup consumer's required source
closure against the proposed selected-file map before privileged dispatch. A
missing required source row belongs in the existing cheap validation, not the
first root invocation. Record a command refusal separately from independently
positive child/tree retirement; preserve the failed attempt and all original
gates. Any corrected execution/readback still needs its exact reviewed release.

Prepare affected C/Rust ABI fixtures with the actual production translation unit,
compiler and flags before the image build when possible. DWARF may omit natural
alignment even when size/offsets are present; a host compiler is not a substitute
for the pinned producer. Bind the smallest actual-source compile assertion to the
existing reviewed build/inspection phase, reuse its proof until relevant inputs
change, and keep ordinary retention/publication work parallel to that check.

Bind privileged readbacks to the actual downstream consumer's required original
bytes before release. A console summary or hash list is not a substitute for raw
files when that consumer needs them; exercise the complete bounded raw transport
and ordinary consumer together under the cheap fixture profile. Preserve stable
producer field names/types across successor artifact reviews, with new evidence
added separately, so an unchanged stager does not need a late schema adaptation.

A terminal packet is ready before build completion when its actual observer,
exporter and downstream consumer implementations exist and their affected cheap
fixtures pass. Leave only observed attempt identities and publication receipts
for late binding. Enumerate production and mock endpoint paths with the actual
test-output prefix before their first replay, keeping the existing UNIX limit.

Prepare the postbuild read-only inspection profile alongside the build proposal:
commands, tools, output bounds, copy destinations and actual consumer joins.
Leave artifact identities explicitly pending, then bind them once from the
completed receipt. Reuse the accepted 14-command profile for matching successors
and review only affected changes. Review36 observed a 201.34-second image run
and 4.95-second inspection run, with several minutes spent preparing the handoff.
Reduce that delay while preserving the required completed-owner, admission and
exact-release boundaries for actual inspection.

Check the actual metadata authorization path before dispatch, including a real
implementation author. Validate the derivative's actual transaction paths against
the fresh attempt and reject preserved predecessor mutation paths; keep historical
proof references intact. Test actual helper return shapes and post-spawn failures.
Identity or evidence-write errors must still account for and join the child.

Finish non-temporal final-payload joins and accepted predecessor references before
collecting time-limited admission. Then measure genuine fresh facts, perform the
permitted narrow delta/hash confirmation and invoke within the existing freshness
window. Preserve expired snapshots; do not relax the bound or repeat static review.

If an ordinary wrapper loses a child result, keep that status unknown. Independent
validation may establish reusable output artifacts where the applicable contract
permits it; bind their actual identity and current-writer evidence into a separately
reviewed remaining-only continuation. Do not invent exit0 or replay a consumed copy.
Keep unrelated ready work moving under its own admission and resource constraints.

On reassignment, reuse already-read policy and the latest compact CURRENT/HANDOFF
cursor. Open historical sections only to resolve a concrete dependency. Retain
complete captures in files and print selected findings, timing and paths; avoid
dumping the full historical handoff into each worker's context.

Before a healthy finite build/guest finishes, activate its existing result
reviewer and terminal author with the exact output paths and completion contract.
Ordinary review starts only after the documented completed-output/retirement
receipt, not mere file presence. This lets cheap affected review continue during
dispatcher context maintenance. Keep waits bounded, avoid polling unfinished
artifacts, and reserve all privileged observation, release and runtime actions
for their existing owner and exact decision.

Carry each accepted readback's exact transport-output contract into its result
fixture. Application stderr and transport stderr are separate observations: an
explicitly reviewed, exact socket-skipped tar warning must not become a late
blanket-empty-stderr assertion. Preserve unexpected stderr as a failure and do
not relax the application's frozen empty-stderr oracle.

Assign short nonce-based protocol/execution output roots up front. Preflight all
canonical generated UNIX endpoint paths before creating archives or attempt
fixtures; source-workspace paths need not be runtime-output paths. Preserve the
existing socket-path admission bound. For an operation with already-approved
bounded readbacks, include those exact readbacks in its reviewed continuation
after positive source-known child/owner retirement and join, then dispatch result
review promptly. Uncertain retirement stops that continuation. Existing
success-only releases still stop on nonzero exit. For a future failed-build
envelope, explicitly review bounded read-only diagnostic capture after positive
owner/client retirement and receipt/journal validation, independently of the
failed workload status. Preserve the failure and authorize no build replay,
new workload or automatic cleanup. This requires its own exact release; it
does not expand earlier root-read authority.

## Reuse artifacts and batch the work that is actually independent

| Change | Cheapest appropriate next action |
| --- | --- |
| Payload or expected-output change only | Reuse compatible current942 kernel/modules/image and staging base; produce the required fresh payload overlay/manifest and obtain its runtime release |
| Checker, collector or ownership helper correction | Run the small original reproducer and relevant negative; reuse compiled artifacts when the reviewed source/artifact contract permits it |
| Kernel/module behavior or ABI change | Actual-body regression, independent affected-boundary review, then the required affected build and guest; keep the known-good baseline available |
| Unchanged accepted input/result | Consume its retained binding and result; recheck only what changed, is uncertain, or is required at the next live consumption boundary |

Use existing `native_diagnostic_stager.py`, `native_diagnostic_overlay.py`,
`native_diagnostic_batch.py` and strict manifest loading where applicable.
Keep source changes for the next candidate separate from the immutable current
runtime stack. The first one-shot diagnostic matched-module reuse build and
artifact-only revalidation are recorded in
`native-running-external-modules-attempt-review-20261017-1.json` and
`native-running-external-modules-artifact-review-20261017-1.json` under
`docs/verification/evidence/`. Consume their exact scope; a later build still
needs its own applicable release. Never narrow a frozen full-tree/source
binding or skip required live admission checks to make reuse convenient.

Exercise a changed collector/oracle through the actual runner and owner replay
call sites in the existing focused host check, using retained complete captures.
Keep raw observations unchanged and preserve wire newline bytes in fixtures.
Assert each negative mutation has its intended unique target and changes bytes.
This catches composition and fixture mistakes before staging; reuse unchanged
compiled inputs and check results within their accepted scope.

For a changed metadata join, test the actual immutable input rows against the
actual producer/helper return shape. Do not invent fields in a fixture that the
real identity helper omits. Exercise changed review/payload bindings with focused
negative cases and check a published test's normal module import, not only its
private override. Consolidate these affected checks before the next handoff.

When repeated per-image packet authoring dominates build time, use an otherwise
idle cheap lane for a bounded next-case template/data-generation experiment.
Derive counts, selected object fields and reference hashes from frozen actual
rows; exercise the existing consumers with retained positives and changed-row
negatives. Keep the accepted engine and identity/ownership/release boundaries.
Render future drafts only, preserve scratch21 exclusions and active packets,
and obtain affected review before use. The prototype must never hold up a
currently ready operation or become a new scheduling framework.

For a build-only candidate, consider one newly reviewed conditional envelope
instead of separate preparation/release cycles for every compiler phase. The
current 66-file module proposal first compiles and audits the C object, then
continues to the complete three-module build only after its actual command,
header dependencies, thunk definitions and undefined imports pass the strict
matched-kernel checks. Bind both phases, their evidence and failure propagation
in the exact new packet; retain one owner/container and the existing admission,
limits and retirement controls. This is a preparation tactic, not authority to
expand an existing release. Preserve any explicit intervening review required
by the selected contract. Build success never grants runtime authority.

Prepare at most two upcoming guest cases while one runs. Batch shared setup and
review of unchanged boundaries. Same-OS application batching requires explicit
permission in the released case contract, fixed membership, independent oracles,
input resets and per-case outputs. Preserve every required repetition, separate
fault-mode release and fresh-guest rule. Initial positive diagnostics should
yield executable feedback promptly; their passing results do not replace formal
repetitions, soaks or qualification.

Keep one heavy build OR guest, including its ownership-sensitive preparation,
retirement and cleanup. Preserve each operation's released limits; the current
isolated validation profile remains four CPU/12 GiB/no swap/512 tasks. The
launcher's larger aggregate budget does not enlarge that profile. Divide
remaining measured CPU/RAM among cheap checks and use disjoint
outputs. Remote model work may overlap while local checks await capacity.
Preserve host/scratch free-space floors; the ready queue is deliberately bounded
so extra overlays do not consume the runway. Healthy silent builds/soaks retain
their owners; a reporting target never interrupts them.

For new, unbound cheap fixtures and preparation outputs, prefer the host volume
when its accepted profile permits and scratch runway is tighter. Keep actual
scratch/runtime paths required by their contracts. Do not move, relink or rename
already pinned evidence, weaken ordinary-file identities, or make another full
source/archive copy merely to fill a ready slot. Admit heavy work only with its
floor plus required growth reserve; this tactic grants no cleanup authority.

Check the actual owner's location rule before assigning each new storage role.
The native diagnostic owner requires its manifest under scratch even when a
staging archive or cheap author workspace can use host capacity. Exercise that
actual path predicate before staging. Correct a rejected placement with a new
reviewed manifest copy and exact rebinding; preserve original manifests and
archives rather than widening the owner contract or repeating passed runner work.

The97% stop measures included account usage. Disk admission uses the selected
packet's byte floors and growth reserve. Do not convert the account threshold
into a host-filesystem occupancy rule or add an unsupported admission gate.
If a selected profile explicitly has another disk rule, cite and preserve that
rule. Retain failed prechecks and correct only the demonstrated scope error.

## Reduce coordination and review latency

- Use fresh, self-contained worker packets: invariant, selected current inputs,
  owned paths, existing command/profile, resource share, expected observation,
  retained failure-family count and stop condition. Do not copy the dispatcher
  conversation or historical inventories. Use `fork_turns="none"` when the
  available delegation tool supports it, supplying all required packet context.
  After normal completion/checkpoint of a large worker conversation, use a fresh
  context for its next task instead of accumulating unrelated assignments until
  compaction. Carry selected current Markdown/evidence references and accepted
  unchanged decisions. Do not interrupt healthy work or service checks, roll
  back rejected requests, or automatically retry a service-policy denial.
- Keep GPT-6.1 for every role. Use medium effort for ordinary implementation and
  coordination, high for difficult lifetime/ABI/concurrency repairs and concrete
  independent boundary reviews, and low for bounded extraction. Escalate the
  difficult task only. Do not switch models or spend extra reasoning on repeated
  status extraction.
- Give a reviewer the tested candidate, exact changed boundary, relevant
  retained findings, original invariant and one requested decision. Collect
  related findings together. Reuse unchanged source review only within its
  stated envelope; privileged execution still needs its independent decision.
  Supply the machine-readable decision shape required by the actual consumer,
  including all selected source bindings. A descriptive profile-review label
  does not replace the consumer's canonical decision record. Exercise that
  record through the existing consumer before the final handoff.
- In affected ordinary-wrapper checks, use the declared outer and inner resource
  limits together. Verify inherited soft/hard limits, bounded drain behavior and
  capture reserve accounting with normal subprocesses before privileged use.
  Keep these checks scoped to changed behavior and reuse unaffected evidence.
- Start review as soon as the relevant candidate and admission results are
  ready. Other workers continue independent tests. A routine note or unrequested
  inventory must not occupy the exclusive execution path.
- Read the concise current SESSION-HANDOFF and relevant current task entries;
  follow links for necessary original authority. Preserve detailed history and
  original AGENTS.md. Do not repeatedly load every historical handoff into each
  packet or start an instruction-rewrite project before the next guest.
- Project selected scalar fields, counts and requested bindings from large
  request/toolchain/catalog records. Keep full documents and detailed reports
  in files; do not print entire manifests or collection members into model
  conversations. Read a particular complete member only when its content is
  needed for the current decision, retaining all original evidence.
- Before runtime, finalize metadata using the real consumed status values and
  source-expression forms, and check both pre/post observer entry points under
  the declared interpreter/version/isolation flags, not the author's ambient
  Python. Exercise configuration to the no-effect transaction boundary. Reuse
  frozen fixtures and real consumer argument checks; avoid discovering a missing
  post phase or unsupported REPO-plus-literal map only after an operation. Keep
  private pre-effect assembly errors separate from kernel/production failures;
  fix the bounded join without replaying the workload or building a new framework.
- Batch normal notes and Git saves at existing checkpoints. Keep code/input,
  exact command, actual result/error and retained failure. Authenticate unchanged
  shared content once per required phase/device/inode, preserving every path's
  identity/race checks and all mandatory consumption checks. Do not replay a
  completed corpus scan or preparation because a new worker joined.
- Reuse a verified code/artifact checkpoint for record-only diagnostic admission
  when the selected review permits it, as clarified in CONVERGENCE.md. Resolve
  all conditional references before execution; explicit final-release push/fetch
  or `--release-commit` requirements remain binding. When the next packet is fully
  admitted and its predecessor retired, launch before noncritical reporting.
- After the original failure plus one bounded correction in the same family,
  change the technical approach or escalate with the small reproducer. Do not
  spend multiple complete cycles on the same bookkeeping/observer mistake.

## Check whether velocity actually improved

### Recurring supervision requested by the user

On 2026-10-17 the user explicitly requested ongoing supervision from the
interactive chat, velocity reviews every 30 minutes to one hour, and concrete
steering of the existing campaign. The supervision goal is separate from the
single engineering dispatcher: it observes, records and sends current user
priorities through the launcher's instruction queue. It starts no build, guest,
cleanup, competing dispatcher or automatic retry of a stopped campaign.

Use [VELOCITY-REVIEWS.md](VELOCITY-REVIEWS.md) for the small durable review cursor
and chronological results. Target one review every 30 minutes. A review may land
within 60 minutes when useful observation is pending; report a healthy operation
as pending instead of interrupting it. Inspect lightweight current state between
reviews when a concrete event warrants intervention. Do not repeatedly read
large logs, full histories or unchanged artifact content just to monitor activity.

Each review reports UTC interval, actual guest attempts/boot/payload results,
new tested and integrated behavior, original milestone conditions closed,
current blocker, useful/blocked/finished lanes and one specific adjustment for
the next interval. Give counts and durations before rates. Keep infrastructure,
actual-body kernel tests and guest/formal acceptance separate. Record unknown
timing and coverage explicitly. Refresh only touched milestone estimates when
actual engineering evidence warrants it; do not manufacture a percentage gain.

Steer immediately on a concrete avoidable failure or missed handoff, without
waiting for the full review. Consolidate instructions so supervision does not
become another source of interruption. Refill only demonstrably ready work;
unready ownership contracts need a bounded design decision, not speculative
patches or reruns of passing tests. Preserve normal Git cadence and the single
runtime owner. The engineering dispatcher checkpoints these small Markdown
updates when safe; the supervising chat does not race its Git or pinned HEAD.

Continue while the user wants supervision and execution is available. Preserve
explicit stops, the included-usage reserve, authentication/policy stops and
genuine unresolved ownership. A Markdown instruction is not a clock or execution
service: the active supervisory goal provides this chat's ongoing loop. Do not
claim that a separate hosted schedule or operating-system timer was installed.

At existing checkpoints, use retained commands/events and the current task cursor
to report the following; add no monitoring project or per-edit ledger:

1. Distinct newly passing guest application behaviors per elapsed hour, with
   candidate and execution profile. Repeat runs of one behavior are reported
   as repeatability, not new behaviors.
2. Distinct repaired production behaviors with actual-body regressions and
   integration per elapsed hour. Keep this separate from guest results and
   infrastructure repairs; raw test-case count is not this measure.
3. Practical exit checks actually closed, with evidence. Keep original formal
   counters and earlier broad estimates explicitly historical; do not rescale
   them or promote deferred gates. Unassessed new checks are not 0% engineering.
4. The next runtime-slot readiness and elapsed waiting caused by missing inputs,
   integration or review. Separate that avoidable delay from actual execution,
   required admission, retirement and soaks. Note tokens consumed if the existing
   account data reports them; do not infer cost from cached tokens.

Compare two comparable two-hour windows with similar resources and available
work. The first window establishes a baseline if no valid earlier window exists.
Target 2x on the chosen behavior-throughput measure, with 3x a stretch; report raw
counts and durations alongside any ratio. A zero baseline, different workload or
only one new result cannot support a meaningful multiplier. Record time to first
new guest result and reduced waiting instead. The practical bounded validation
remains meaningful testing; deferred exposure/certification is not a finish gate.

If two existing dispatch cycles produce no new executable observation outside a
healthy long operation, identify the actual dependency and change the approach
or move a worker to ready implementation. Continue useful independent work;
record a precise missing external resource when that is the actual blocker.
