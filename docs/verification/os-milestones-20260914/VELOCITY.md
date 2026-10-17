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

## Reduce coordination and review latency

- Use fresh, self-contained worker packets: invariant, selected current inputs,
  owned paths, existing command/profile, resource share, expected observation,
  retained failure-family count and stop condition. Do not copy the dispatcher
  conversation or historical inventories. Use `fork_turns="none"` when the
  available delegation tool supports it, supplying all required packet context.
- Keep GPT-6.1 for every role. Use medium effort for ordinary implementation and
  coordination, high for difficult lifetime/ABI/concurrency repairs and concrete
  independent boundary reviews, and low for bounded extraction. Escalate the
  difficult task only. Do not switch models or spend extra reasoning on repeated
  status extraction.
- Give a reviewer the tested candidate, exact changed boundary, relevant
  retained findings, original invariant and one requested decision. Collect
  related findings together. Reuse unchanged source review only within its
  stated envelope; privileged execution still needs its independent decision.
- Start review as soon as the relevant candidate and admission results are
  ready. Other workers continue independent tests. A routine note or unrequested
  inventory must not occupy the exclusive execution path.
- Read the concise current SESSION-HANDOFF and relevant current task entries;
  follow links for necessary original authority. Preserve detailed history and
  original AGENTS.md. Do not repeatedly load every historical handoff into each
  packet or start an instruction-rewrite project before the next guest.
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
