# Autonomous McKernel goal

## Active Rust cutover priority — user instruction 2026-10-18

Functional delivery and retiring live McKernel compute C into Rust plus reviewed
assembly are both active requirements. The earlier whole-image zero-C deferral
below must not postpone compute-kernel retirement. Original scope IDs, historical
tables and qualification evidence remain preserved; large exposure and external
certification stay deferred. Practical M09 integration estimates are not a
whole-kernel language-conversion score.

Do not add or expand compute-kernel C behavior. Preserve accepted live cpu.c and
process.c fixes and the working image while implementing Rust through real
consumed ABIs. C reference/fallback paths may remain during development; count a
cutover only with production default selection, linked-artifact ownership and
applicable native proof. Linux control-plane compatibility C remains allowed;
the three mcctrl_vm_write_compat.c MM API thunks are host glue. Report any further
concrete exception before integration. First ports are the live FPU copy path
and scheduler FPU admission; process/scheduling retirement continues afterward.


## Active user scope — practical kernel and applications, 2026-10-17

The user explicitly replaced excessive formal qualification with a solid kernel
and working application infrastructure. [PRACTICAL-GOAL.md](PRACTICAL-GOAL.md)
and [practical-milestones.json](practical-milestones.json) now define completion.
They supersede older all-gates/all-catalog/exposure/soak/external-release clauses,
including the preserved launcher objective string. Preserve that legacy identity
for compatible resume; do not change launcher state or restart to adopt scope.
Original qualification evidence and counters remain deferred, never relabeled PASS.

Preparation on 2026-09-27 leaves the campaign stopped. A later normal launcher
invocation is explicit authorization to resume; this preparation hold does not
stop that invocation. Full dedicated-computer, aggressive scheduling supersedes
older three-child/workstation scheduling numbers only; the objective, acceptance
and other policies remain.
Documentation does not change the launcher or a currently running session.

## Start or resume the existing campaign

```bash
python3 /home/holden/mckernel/scripts/run_os_goal.py
```

For a later launch, use LAUNCH.md for the command's controls and checks.
The launcher owns one separate persistent thread and resumes its exact ID. Keep
any older interactive campaign paused; do not create competing dispatchers on
the same checkout. Model changes do not replenish quota or prove continuation.

The user now requires `gpt-6.1-sol` for the dispatcher and every subagent, with
no older-model fallback. Use low for simple inventories, medium for coordination
and implementation, and high for complex repairs and independent safety reviews. Default
`--profile aggressive` allows up to eight children within measured host CPU/RAM
capacity; no recursive dispatch, and fresh self-contained worker packets.
`--profile balanced` restores three children/four build jobs/12 GiB. Explicit
`--max-agents N --build-jobs N --memory-gib N` remain subject to host capacity.
Aggressive uses all affinity CPUs (currently seven) and
`min(24 GiB, measured available RAM minus 4 GiB headroom)`; see CONVERGENCE.md.
This user-authorized model policy supersedes earlier Sol/Luna/Terra/Astra role
choices. Preserve reviewer independence and global configuration.

## Mandatory reading and precedence

Read GOAL.md, START.md, CONVERGENCE.md, then the compact HANDOFF.md. This order
overrides the older read-order text in the launcher's exact preserved OBJECTIVE;
do not rewrite that objective or create a new thread to adopt the policy.
On the first policy adoption, reconcile that handoff with actual local sources,
launcher state, active leases and the latest relevant CURRENT.md evidence.
Read README.md once for the complete objective; thereafter load the selected
task/gate/case and required contracts, not the entire history at every turn.
Reload changed workflow instructions on resume or a safe coherent checkpoint.
The launcher records policy hashes; record the adopted hashes after reading.
A remote documentation commit is not proof that a local running dispatcher has
loaded it.

CONVERGENCE.md supersedes older scheduling, retry, context-loading and checkpoint
habits, including completed model-switch stops. PRACTICAL-GOAL.md governs current
scope and completion. README.md, `final-push.txt` and original contracts preserve
the deferred qualification backlog; they govern any original acceptance claim.
Independent execution releases still govern actual privileged/build/guest work.
Never treat the planning indexes, a generated dashboard or a source-only packet
as runtime authority. Preserve all immutable originals and existing Rust consumers.

## Execution contract

Continue dependency-ready implementation and validation until the practical
kernel/application exit checks pass on the declared supported profile. This is
the user's explicit rebaseline, not permission to claim original qualification.
Huge fuzz/exposure quotas, 168-hour soaks and full external qualification no longer
block this goal. Keep actual correctness, meaningful regressions, native lifecycle
restoration, artifact identity and recoverable delivery as completion requirements.

For each behavior: freeze its invariant and expected result; obtain the cheapest
valid executable evidence; repair; independently review the affected boundary;
then integrate and run the next authorized layer. Admission and failure-family
limits in CONVERGENCE.md are mandatory. A passing model or infrastructure fixture
is useful scoped evidence, never automatic product/application acceptance.

Only the dispatcher owns compiler-command approval, the single heavy build/guest
lease, integration, acceptance updates and Git checkpoints. Share aggregate
CPU/RAM budgets across bounded cheap test processes. Automatic build environment
settings are not a cgroup; pinned guest/privileged profiles need independent
resource review before exceeding their historical four-CPU/12-GiB envelopes.
Keep existing isolation, process-identity and cleanup rules; reconcile owners
after any interruption. Default `--stall-seconds 0` preserves silent builds;
the worker heartbeat watchdog remains 180 seconds.
A launcher exit, worker report or accepted source packet does not prove cleanup.

Continue after coherent checkpoints without routine confirmation. After one
failed candidate and one bounded correction in the same failure family, escalate
the design/implementation; do not reset that history by renaming packets or
restarting. Fix project-owned blockers, or select independent ready work while a
real external prerequisite is unavailable. Continuous duration is not permission
to loop on unchanged deterministic failures or repeatedly restate a blocker.

Preserve exact failures, source/test/oracle identities, commands and results.
Update HANDOFF.md and the existing chronological evidence/events. Report practical
criterion closures first; promote historical formal counters only under their
original acceptance rules. Commit coherent code/tests,
harness changes and reporting separately, verify fetched blobs, and preserve WIP
at the existing cadence and before long runs or a controlled stop.

Respect a new explicit stop, selected time/budget limit and exhausted credits.
An explicit stop takes precedence over watchdog recovery. Unclassified paused/
blocked goals and generic server/turn errors stop; only classified recoverable
faults continue the saved thread with backoff as described in LAUNCH.md.
Do not infer consent, read/print credentials or repeat failed authentication/spawn
attempts. Keep the campaign recoverable where possible; checkpointing is not
whole-OS completion. The current watcher's automatic recovery is process-level:
Markdown does not add machine-enforced convergence or guarantee autonomous uptime.
