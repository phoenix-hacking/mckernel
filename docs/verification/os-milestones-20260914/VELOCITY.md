# Tactical plan for faster verified OS progress

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
