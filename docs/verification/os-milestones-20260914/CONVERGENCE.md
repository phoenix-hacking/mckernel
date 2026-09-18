# Convergent execution policy

Effective 2026-09-17. This is dispatcher workflow policy, not an acceptance
certificate, a new OS requirement, or a claim that the Python harness enforces it.

## Authority and scope

Read this policy through GOAL.md and START.md. README.md, the original stability
and production contracts, `final-push.txt`, and each selected case/gate retain
their scope, dependencies, expectations and acceptance authority. Do not change
scores, denominators, required repetitions, 168-hour soaks, Rust/assembly closure,
native modules, the pinned Rocky/Linux target, or external qualification to
improve throughput. Preserve existing Rust consumers and immutable evidence.

This policy supersedes older scheduling, retry, context-loading and checkpoint
habits only. It does not override execution-release, isolation, ownership,
credential, cleanup or independent-review requirements. A source-only packet
remains source-only until its appropriate execution profile is reviewed.
Continuous operation means sustained useful work, not unlimited repetition of a
failed design. A blocked subtask is not completion of the whole objective.

## The unit of work: one observable behavior

Choose the earliest unmet dependency that prevents useful native/guest execution.
Name the violated invariant, its production consumer, and the next executable
observation before dispatching. Prefer a coherent repair across the necessary
files over either a one-line drafting exercise or a repository-wide rewrite.

A work item should produce one of: a reproduced failure with a bounded repair;
a passing implementation plus relevant regression evidence; or a precise
external blocker with its recheck condition. A plan, renamed packet, additional
review, larger archive or new dashboard does not by itself satisfy that item.
Do not demand a formal production-gate increment for every legitimate small fix;
record bounded behavior and infrastructure results separately from OS acceptance.

Use this cycle:

1. Read the live handoff, original task contract and relevant retained findings.
   Freeze the consumed inputs, allowed edits, test commands and expected behavior.
2. Reproduce the current defect under the cheapest valid execution profile. For
   a genuinely new feature, establish an independent expected result first.
3. Repair the implementation and run its admission suite before requesting broad
   review. Retain the original failure; do not repair an oracle to match output.
4. Have an independent reviewer examine the invariant, exact diff, actual test
   results and remaining risks. Review the whole affected boundary, not just the
   newest lines or each finding in isolation.
5. Integrate and run the next required native/root/guest layer as soon as its
   actual prerequisites pass. Update acceptance only under the original contract.

Do not start a second design/history audit when a failing compile or positive
example already identifies the next concrete action.

## Apply the harness at the appropriate layer

The dispatcher owns compiler commands and all build/guest leases. Workers write
code and tests within their explicit allowlists; they do not acquire runtime
permission by creating a fixture or changing a packet status.

| Layer | Useful evidence | Required boundary |
| --- | --- | --- |
| A: static admission | Syntax, imports without side effects, schema and source-binding checks | Read-only or disposable-output commands explicitly reviewed by the dispatcher; no credential or live runtime access. |
| B: unprivileged executable microtest | A real C/Rust compile, actual helper execution, ordinary subprocess descriptor behavior, positive and negative controls | One reusable reviewed cheap-check profile, pinned tools, disposable outputs, bounded processes/time/storage, no root, modules, guest, hardware, network or production state. |
| C: actual production build | Full consumed source/body and ABI bindings, real object/module/image, integration and symbol checks | Existing build ownership, resource policy and independently reviewed build packet. |
| D: privileged infrastructure/runtime | Actual root collector, guest, ownership, cleanup and fault observations | Existing independent execution release, serialized runtime owner and original isolation/cleanup requirements. |
| E: integrated acceptance | Required paired Linux/McKernel cases, repetitions, pressure, soaks and release evidence | All original global and per-case prerequisites; independent acceptance on exact artifacts. |

Layer names describe evidence, not extra gates. Credit any result only to the
original contract whose requirements it actually meets. A model-only test,
compiled fixture or root infrastructure test is never silently relabeled as
production/application acceptance.

If no reusable layer-B profile exists, prepare and independently review ONE
bounded profile before using it. Specify exact command families, input/output
roots, toolchain identity, maximum duration, process/resource limits, prohibited
operations and cleanup. Reuse it for changed candidate bytes only within its
explicit change envelope, with fresh input hashes and fresh results. A change to
privilege, commands, dependencies, isolation, resource use or side effects needs
renewed review. Do not require a new orchestration design for each test vector.
Do not execute unknown imports, repository launchers or fixture preparation
scripts merely because their names sound harmless.

Cheap checks must fit within the established four-CPU/12-GiB ceilings and leave
headroom for other work. Measure host/scratch capacity before expensive work;
reuse the existing measured floors rather than inventing a new fixed floor.
Do not lower safety floors or run a root/guest action as an unprivileged test.
An unavailable compiler/profile is a recorded NOT_RUN dependency, not a pass.

## Executable admission, not keyword coverage

Before substantive review, the selected candidate must pass syntax/compile,
at least one valid positive example, the original failure reproducer, and a
negative control relevant to the claimed invariant. Where a layer-B run has not
been released, perform static checks and obtain that bounded release first;
do not claim executable readiness while execution is prohibited.

Required practices:

- A named vector constructs actual input state and invokes the tested code.
  Case names and expected return codes alone are an inventory, not test cases.
  Assert observed return values, side effects, ownership and unchanged-on-error
  state. Count executed cases separately from declared cases and configurations.
- Grep, AST inspection and hash checks establish structure or provenance only.
  Never use their success as evidence that a semantic branch executed.
- Prefer the full selected production helper with every consumed dependency
  bound. A reduced model is useful for design, but must have an explicit mapping
  to a real consumer and an actual-body/integration test still due. Do not build
  another stand-alone model to avoid fixing that consumer.
- Keep reference/oracle expectations independent of candidate output. Use parent
  failure/candidate success when available. A compile-fail control must fail for
  its intended reason, not a missing import, broken syntax or missing tool.
- Preserve all applicable original tests. Change an incorrect fixture only with
  an independent semantic justification, additive expected-result version and
  retained original failure; never silently refresh golden outputs.
- Test OS semantics through real unprivileged subprocesses where feasible:
  descriptor aliasing, closed standard streams, source-equals-destination dup,
  descriptor inheritance and child termination cannot be established by fake
  dictionaries alone. Release privileged follow-up separately.

A checker failing on harmless local variable spelling is a checker defect, not
an implementation invariant. A positive case that cannot be constructed is an
admission failure. Resolve these before growing an adversarial matrix.

## Bound repair loops by failure family

Keep one compact record in HANDOFF.md and the existing append-only event stream.
Do not build a new ledger framework to implement this policy.

A failure family is the task/subsystem plus violated invariant and affected
production boundary. Its identity excludes packet names, timestamps, reviewer
names and commit hashes. An attempt additionally binds source/test/oracle hashes,
command, toolchain/environment, outcome and retained evidence. A source change
creates a new attempt; it does not erase that family's repair history.

One initial failed candidate and one bounded correction are the ordinary limit.
After the second failure, stop sending the same problem through cheap workers.
Escalate to a capable design/ownership expert with the complete current invariant
matrix, original failure, smallest reproducer and exact affected files. The
escalation must produce a coherent repair and executable checks, or a finite
missing-authority/dependency list. Another prose-only redesign is not closure.
Use the already selected Terra escalation or Astra/high ownership review where
appropriate; keep the final reviewer independent of the implementation author.

If the expert's candidate fails for the same family, the dispatcher must decide
between a larger coherent boundary repair, a strictly equivalent simpler design,
or a concrete blocked dependency. Record that decision before more work. Do not
reset the limit by renaming a packet or merely allocating a new reviewer. New
safety findings remain blockers and receive tests; limits never permit accepting
an unsafe candidate. They change the repair strategy, not the acceptance bar.

Never rerun an identical deterministic failure without a relevant source, test
or environment change. Record the delta being tested. Replaying a flaky or
transient failure is allowed only under a bounded, explicit hypothesis; every
failed run remains retained. Reviewers should consolidate known findings into
one invariant matrix instead of issuing one new administrative packet per item.

After two completed dispatch cycles with no new executable result, resolved
invariant, or necessary dependency, perform a short convergence check: identify
which hypothesis changed and select a different concrete repair or ready task.
Do not count review/heartbeat activity as technical progress. This is not a
wall-clock deadline and must not interrupt healthy long builds or required soaks.

## Review risk, not paperwork volume

Use independent expert review for unsafe ownership, concurrency, ABI, privileged
execution, cleanup and final acceptance. Syntax fixes, formatting, documentation
and routine tests within a reviewed envelope do not each require a fresh broad
architecture audit. The dispatcher remains responsible for checking them.

A reviewer returns: the tested behavior and exact artifact; blocking findings
with a reproducer or source-based invariant argument; nonblocking maintenance
notes; the scope released; and what remains unexecuted. Separate harness defects
from product defects. Separate demonstrable violations from new design wishes.
Source reasoning can block unsafe execution even when a reproducer is not safe.

Every additional proof obligation must map to an existing requirement or a
concrete defect in its declared trust boundary. Do not recursively authenticate
already-trusted observers or invent a new production requirement just to reject
another packet. When a genuine gap is discovered, consolidate it into the
relevant contract/implementation review without altering immutable originals.
Useful positive, rejection and recovery cases matter more than mutation counts.

Prefer one frozen schema and shared mechanical parsing where appropriate, while
preserving independent behavioral oracles required by the original contract.
Duplicating the same unchecked assumption in three validators is not independent
proof. Check the producer-to-observer joins explicitly, including identity,
sequence, lifetime and legitimate post-retirement reuse.

## Scheduling and model use

Keep Sol/medium as dispatcher. Use Luna/low for bounded read-only inventory,
Luna/medium for well-specified repairs/tests, the existing Terra escalation for
bounded hard repairs, and Astra/high for ownership/unsafe/ABI/release review.
At most three children total, no recursive dispatch, fresh self-contained packets.
Do not keep all slots busy when no independently useful work is ready.

Default work in progress: one critical-path implementation family and one
independent ready task; reserve the third slot for review when a candidate has
admission evidence. Assign disjoint file ownership. The dispatcher serializes
builds/guests and reconciles all active process/runtime leases before another
heavy operation. Neither worker completion nor launcher exit proves cleanup.

A worker packet needs only: task/invariant, consumed inputs, allowed files,
commands/profile, frozen expectations, current failure-family attempt count,
result/evidence location, and stop/escalation condition. Workers do not receive
the entire CURRENT history, all 273 cases or all historical checkpoint notes.
Do not delegate an ambiguous cross-kernel lifetime design to a cheap worker.

## Harness lifecycle is not engineering convergence

The existing `scripts/watch_os_goal.py` can restart paused/blocked goals and
counts agent events, not accepted engineering results. This Markdown update
DOES NOT implement a fingerprint circuit breaker or change Python defaults.
Until those mechanisms exist, the dispatcher enforces the policy after every
resume. Record a failure to enforce it as a harness defect, not OS progress.

| Condition | Dispatcher action | Harness behavior to implement/test if absent |
| --- | --- | --- |
| Transient transport/capacity fault | Preserve thread, budget and evidence; reconcile leases; retry with backoff | Bounded/backed-off recovery classified separately from engineering failures. |
| Deterministic compile/test failure | Run the failure-family repair/escalation process | Carry family/attempt state across restarts; no blind identical retry. |
| Missing space/tool/authority/fixture | Repair project-owned dependencies once; otherwise select ready work | Recheck an external blocker only when its condition may change; no repeated model calls just to restate it. |
| Healthy long build/guest/soak | Preserve its owner, deadline and progress evidence | Do not restart solely because agent chatter is silent; never synthesize chatter to defeat the watchdog. |
| Unknown process ownership or cleanup | Hold affected execution and reconcile through approved mechanisms | No second owner and no fabricated cleanup success. |
| Explicit stop, exhausted credits/budget, missing credentials | Checkpoint safely where possible; stop the affected work | No automatic consent, quota-spawn loop or authentication bypass. |

The campaign may remain open without repeatedly invoking inference. Unlimited
campaign duration does not authorize unlimited deterministic retries. Do not
claim these classifications are machine-enforced until the launcher tests prove
it. A reviewed harness repair, if necessary, is a separate infrastructure item;
it must not become a new generic orchestration platform project.

## Current state, evidence and Git hygiene

HANDOFF.md is the compact live routing record; CURRENT.md and original evidence
remain historical/chronological sources, not material to reread from the top on
every resume. Before using the initial handoff, reconcile it with the local
working tree, latest retained records, launcher state and active leases. Do not
trust a stale top paragraph or an exported dashboard as a live process check.
Only the dispatcher updates the handoff and official acceptance records.

Keep the handoff around 120 lines: current source identity and policy hash,
active task/family, failed attempts, last executed result, pending command,
release/profile state, leases, blockers and next two tasks. Link full history.
Append failure details to the existing evidence/event mechanism; do not overwrite
original results or copy every previous review into every new record.

Use source/input manifests and exact retained blobs for reproducibility. Avoid
repacking an entire unchanged dependency tree for each review when the original
contract permits exact referenced artifacts. Never delete or alter required
archives, failed attempts or active dependencies. Cleanup still requires the
existing verified retention/restoration and ownership checks. Do not create
new unverified storage or silently move evidence outside its authorized location.

Checkpoint coherent implementation plus its tests separately from harness
mechanics and reporting-only work. Titles must name the actual behavior changed.
Never bury kernel changes or executable fixtures in a dashboard commit. Save
necessary WIP at the existing cadence and before long runs/end; label unexecuted
or rejected WIP explicitly. A scheduled checkpoint with no change needs no
empty commit. Verify the remote commit and consumed blobs; do not force-push,
discard local work, publish credentials or overwrite immutable evidence.

README.md and its line-indexed tasks/maps are unchanged by this policy. Do not
regenerate them just to mark this instruction update as progress. M00-C's large
AGENTS.md consolidation remains a separate one-time preservation/review task:
archive exact original bytes, check all still-operative requirements, then make
a concise active entry. Do not hide requirements by lowering a document limit.

## Measure payoff without manufacturing progress

Record policy adoption time, active execution time versus external waiting,
new passing actual-body/native/integrated behaviors, accepted original gates,
repair attempts per family, recurrence, and usage only when reported. Separate
new implementation from newly documented or revalidated old work. Missing cost
or timing data stays unknown.

For a before/after comparison use equal, explicit observation windows, comparable
resource availability and the same acceptance definitions. Show source revisions
and acceptance timestamps. Commit count, lines added, review count, declared
vectors and dashboard percentages are not substitutes for delivered behavior.
A failed qualification can be useful defect discovery; repeated failure without
an improved executable candidate is a convergence problem, not automatic ROI.
