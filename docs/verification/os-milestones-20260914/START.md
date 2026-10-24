Current delivery target and included-first/explicit-credit handoff limits: [October24 run window](RUN-WINDOW-20261024.md). Active resident billing controls remain authoritative.

# Dispatcher entry point

Current assignment scope (2026-10-21 UTC): functional McKernel OS/apps and
Rust/assembly migration only; no security testing. Apply the current assignment
scope in [AGENTS.md](../../../AGENTS.md) to every worker brief. Keep functional
correctness and resource/ownership checks. This note does not resume the stopped
campaign or clear its service-policy hold.

Current user scope (2026-10-17): [PRACTICAL-GOAL.md](PRACTICAL-GOAL.md) and
[practical-milestones.json](practical-milestones.json) replace comprehensive
qualification as the active completion target. Read them after GOAL.md. Preserve
the old roadmap as deferred scope; do not recreate long-exposure prerequisites.

Latest user instruction, 2026-10-23: keep the35 functional checks separate from
the full Rust cutover. Read [M14](RUST-CUTOVER-M14.md) and only the selected file
subgoals from [rust-cutover-m14.json](rust-cutover-m14.json) for cutover work.
M14 remains active alongside functional closure; it does not postpone the next
native test. Report both tracks separately and reuse matching evidence.

Latest language boundary, 2026-10-24 UTC: read [M15](RUST-CUTOVER-M15.md) and
[rust-cutover-m15.json](rust-cutover-m15.json) for project-owned runtime outside
M14, including Linux modules, executors, libraries and tools. Credit already
implemented Rust drivers and matching evidence, enumerate residual selected C,
and preserve working C until qualified Rust replacements are integrated. This
adds a separate active language milestone, without changing the35 functional
checks or resource/workload authority.

Preparation on 2026-09-27 leaves the campaign stopped. A later normal launcher
invocation is explicit authorization to resume; this preparation hold does not
stop that invocation. Dedicated-computer scheduling supersedes older
three-child/workstation scheduling numbers only.
Use GOAL.md for the current practical objective, CONVERGENCE.md for execution/
review/retry policy, HANDOFF.md for compact routing, and LAUNCH.md for launcher
controls. Do not reinitialize an existing goal or start a second dispatcher just
to adopt these instructions.

```bash
python3 /home/holden/mckernel/scripts/run_os_goal.py
```

A normal invocation starts/resumes account-metered work. This documentation
change does not invoke it. Keep older interactive campaigns paused while the
launcher owns the checkout. A running dispatcher reloads the new policy at a
safe checkpoint after reconciling local/remote changes without discarding WIP.

## Active agent dispatch rule — 2026-10-22

New work for a completed or idle agent MUST use `followup_task` to start a new
turn. Use `send_message` only to steer an already running agent. Confirm the new
turn/status once, then wait for its result without busy-polling. Sending a message
to a completed agent and waiting for it is not productive work. Apply this rule
before reporting a review or implementation lane as active.

## Dispatcher startup packet

1. Read GOAL.md, START.md, CONVERGENCE.md and HANDOFF.md in that order, overriding
   the preserved launcher's older OBJECTIVE read-order without rewriting it.
   Reconcile actual HEAD, tracked/untracked inputs, the latest relevant
   CURRENT.md records, launcher-owned state and file/runtime leases. Bootstrap
   handoff fields are not runtime observations. Record adoption against
   launcher-recorded policy hashes. Do not edit launcher-owned
   state by hand.
2. Select the next practical exit check from practical-milestones.json. Read
   README.md once as the preserved qualification roadmap; use its existing helper
   for a particular original task/gate/case only when relevant to current work.
   Do not reinstate the whole old backlog as a dependency. Do not repeat a repository-wide
   audit, replay already-valid work, or give every worker the entire catalog.
3. Prioritize the critical path and saturate independently useful, ready work
   within the measured cap: favor implementation, build and executable-test lanes;
   use audit/review slots only for a concrete blocking decision. Aim for four or
   more disjoint implementation/test lanes when they are genuinely ready.
   Do not manufacture tasks to fill slots. Give each worker an invariant,
   source bindings, write allowlist, frozen expectations, allowed command/profile,
   evidence location and cumulative failure-family history. Assign disjoint file
   ownership and independent reviews.
   Apply CONVERGENCE.md's implementation-progress priority: every lane names its
   owner, next executable check and downstream dependency; use review/audit slots
   only for specific decisions. At checkpoints report verified behavior, actual
   test evidence, blockers and next executable work. Keep the prepared launcher
   stable unless a reproduced defect blocks execution, correctness or visibility.
4. Execute cheap admission under a reusable reviewed profile before broad review:
   syntax/compile and the smallest real positive or defect reproducer first;
   add the relevant negative before claiming the repaired boundary is ready.
   Static keyword checks and named vectors alone establish no semantic behavior.
   Within a reviewed unprivileged profile, do not make a new packet/review for
   every edited candidate or vector. No source-only packet self-authorizes work
   outside its released profile, root work or a guest.
5. Integrate a coherent repair and obtain the appropriate independent boundary/
   execution review. Launch the next native/root/guest layer as soon as its actual
   prerequisites pass; do not wait for unrelated whole-OS capabilities.
6. After one failed candidate plus one bounded correction for the same invariant,
   escalate with the complete current findings and minimal reproducer. Do not
   reset attempts through packet renaming, new reviewers or launcher recovery.
   For an infrastructure-only failure, test and repair the observer/validator
   locally before requesting another one-shot execution release.
7. Preserve original failures, append chronological evidence and keep HANDOFF.md
   compact. Report executed behavior separately from formal gate/case acceptance.
   Checkpoint coherent changes about every 30 minutes and before long runs/end;
   label rejected/unexecuted WIP, verify remote blobs, and never force-push.

For the user's intermediate engineering milestone, use the root
[STABLE-CORE.md](../../../STABLE-CORE.md) and its `stable-core.json` worklist.
Read the declared profile and selected rows, not all historical evidence at
every turn. Report newly implemented/tested/integrated behavior and baseline
reuse separately from production acceptance. Update touched rows and their
source/evidence bindings at existing checkpoints; the normal progress updater
renders both reports. SC1 completion is a scoped notification, never practical-goal
completion or permission to omit a required execution/safety check.

## Fast path to an application-testable core

The user now explicitly prioritizes the fastest route to a functional, stable
kernel core. The next user-visible result is a reproducible **diagnostic**
application run on the current McKernel candidate, not completion of all M01–M04
acceptance gates. Do not optimize this phase for perfect formal coverage.
Identify the existing compiled startup argv/environment/stdout-stderr fixtures,
their exact guest runner and the shortest unmet prerequisite. Prepare the
current-candidate artifact and independent expected bytes while disjoint workers
repair kernel/Rust code, the Linux comparison path and relevant M01/M02/M03
blockers. Prefer code and running tests over another source-only packet. Once
the applicable reviewed execution release, source bindings, isolation and
runtime lease are valid, run the smallest positive
fixture and capture actual output bytes, exit status, kernel log and teardown.
Then iterate on memory, file, thread and shutdown smokes; retain concise
regression evidence at normal checkpoints. Expand only after the result is
understood. Do not label compilation, a host subprocess or a model as a
McKernel application execution. This pilot grants no
M04 acceptance credit and bypasses no root/guest isolation or cleanup rule.
Formal case acceptance still follows its original per-case contract.

At existing checkpoints, report the number of real guest applications executed
in the work window, the latest executable regression result, elapsed time since
the last such result, and the exact blocking dependency if the count is zero.
If two completed dispatch cycles produce no executable result, change the
technical strategy or move a lane to another dependency-ready behavior; do not
interrupt a healthy long-running operation or manufacture a result. The target
is faster observed kernel behavior, not a promised numerical speedup.

## Models, ownership and resources

Use `gpt-6.1-sol` for coordination and every child; the user explicitly requires
this model throughout. Use low for simple read-only inventories, medium for
coordination/implementation, and high for complex repairs and independent
ownership/unsafe/ABI/execution-release/final-evidence review. Use
os_auditor/os_worker/os_reviewer roles where available. Do not fall back to older
models; admission must verify every required GPT-6.1 effort before resume.
Default `--profile aggressive` allows up to eight children, constrained by
measured host CPU/RAM; no recursive dispatch. Final review must be independent
of authorship. Project config sets eight; the launcher's measured effective cap
takes precedence and must be checked through CLI `config/read` before work.

Default `--agent-windows auto` opens each child's own `gnome-terminal` window when
a desktop is available; the main terminal stays with the coordinator. Per-thread
logs remain available; use `--agent-windows off` for headless operation (`on` is
also supported). `--check`/`--dry-run` report the backend without opening windows
or inference. Up to eight useful ready children may have windows; no busywork.

Aggressive uses all affinity CPUs (currently seven) and
`min(24 GiB, measured available RAM minus 4 GiB headroom)`.
`--profile balanced` restores three children/four build jobs/12 GiB;
`--max-agents N --build-jobs N --memory-gib N` override within host capacity.
Only the dispatcher owns compiler-command approval, integration, acceptance,
Git and the heavy lease: at most one heavy build or guest at once. Bounded cheap
tests share aggregate CPU/RAM budgets with all concurrent work.
Multiple light, isolated Docker checks may overlap only when their exact
unprivileged profiles have been reviewed, their output roots and owners are
disjoint, and measured aggregate CPU/RAM/storage headroom remains; two default
4-CPU/12-GiB containers are not automatically admissible under the seven-job/
24-GiB aggregate budget. They do not create another heavy build/guest lease.
Build environment settings are injected through
`shell_environment_policy.set.KEY` and verified
with `config/read`; they are not a cgroup. Pinned guest/privileged profiles need
independent resource review before exceeding historical four-CPU/12-GiB envelopes.
Retain isolation/timeouts, measured free-space floors and headroom; remeasure
before heavy work. Default `--stall-seconds 0` preserves silent builds; the worker
heartbeat watchdog remains 180 seconds. Clean only verified redundant data under
the existing retention/restoration procedure. Never release a runtime lease on
an unverified cleanup claim or launch another owner after uncertain retirement.

## Authorization and continuous work

For the later campaign, the user's existing authorization covers project-scoped
implementation, fixture/oracle repair, toolchains, clean checkouts, isolated
native/root/guest runs, reviewed execution packets and verified GitHub checkpoints
without repeated routine questions. Choose reasonable defaults and record them.
Source paths in a task are not blanket write permission. Exact reviewed execution
scope and the original safety/acceptance requirements remain mandatory.

Use noninteractive commands and existing credentials only through authorized
launcher mechanisms. For authorized host operations, use sudo -A with the
inherited SUDO_ASKPASS helper; never read, print or directly expose the credential.
Do not fabricate a human signature/approval, publish outside authorized project
scope, or sign legal agreements. Missing credentials/hardware/authority are real
blockers; project-owned missing helpers or records should be repaired, not
repeatedly returned as questions. Privilege granted to an agent is not Linux root.

There is no default calendar deadline; eligible recoveries have no default cap.
Explicit stops take precedence over watchdog recovery. Unclassified paused/
blocked goals and generic server/turn errors stop. Structured
`serverOverloaded`/`rateLimitExceeded`, positively retryable transport failures,
code 24 and eligible watchdog recovery continue the same thread with backoff.
Continue after checkpoints until full acceptance, exhausted credits or a stop/limit.
This does not permit unchanged deterministic retry loops. Follow CONVERGENCE.md's
failure-family limits, external-wait policy and healthy-long-run protections.
The Python watcher does not yet enforce all of those distinctions; do not claim
that editing Markdown changed its runtime behavior. Preserve actual leases and
failures across every restart. Neither a paused packet nor a dashboard completes
the OS objective.
