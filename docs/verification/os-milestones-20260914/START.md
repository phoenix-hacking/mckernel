# Dispatcher entry point

Preparation on 2026-09-27 leaves the campaign stopped. A later normal launcher
invocation is explicit authorization to resume; this preparation hold does not
stop that invocation. Dedicated-computer scheduling supersedes older
three-child/workstation scheduling numbers only.
Use GOAL.md for the unchanged whole-OS objective, CONVERGENCE.md for execution/
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

## Dispatcher startup packet

1. Read GOAL.md, START.md, CONVERGENCE.md and HANDOFF.md in that order, overriding
   the preserved launcher's older OBJECTIVE read-order without rewriting it.
   Reconcile actual HEAD, tracked/untracked inputs, the latest relevant
   CURRENT.md records, launcher-owned state and file/runtime leases. Bootstrap
   handoff fields are not runtime observations. Record adoption against
   launcher-recorded policy hashes. Do not edit launcher-owned
   state by hand.
2. Read README.md once, then use the existing planning helper to select the exact
   task/gate/case and original prerequisites. Do not repeat a repository-wide
   audit, replay already-valid work, or give every worker the entire catalog.
3. Prioritize the critical path and saturate independently useful, ready work
   within the measured cap: suggested four implementation/test lanes, two audit/
   oracle lanes and two independent review slots, only when useful and disjoint.
   Do not manufacture tasks to fill slots. Give each worker an invariant,
   source bindings, write allowlist, frozen expectations, allowed command/profile,
   evidence location and cumulative failure-family history. Assign disjoint file
   ownership and independent reviews.
4. Execute cheap admission under a reusable reviewed profile before broad review:
   syntax/compile, a real positive, the defect reproducer and a relevant negative.
   Static keyword checks and named vectors alone establish no semantic behavior.
   No source-only packet self-authorizes compilation, root work or a guest.
5. Integrate a coherent repair and obtain the appropriate independent boundary/
   execution review. Launch the next native/root/guest layer as soon as its actual
   prerequisites pass; do not wait for unrelated whole-OS capabilities.
6. After one failed candidate plus one bounded correction for the same invariant,
   escalate with the complete current findings and minimal reproducer. Do not
   reset attempts through packet renaming, new reviewers or launcher recovery.
7. Preserve original failures, append chronological evidence and keep HANDOFF.md
   compact. Report executed behavior separately from formal gate/case acceptance.
   Checkpoint coherent changes about every 30 minutes and before long runs/end;
   label rejected/unexecuted WIP, verify remote blobs, and never force-push.

## Models, ownership and resources

Keep Sol/medium coordination. Use Luna/low for bounded read-only inventories,
Luna/medium for specified implementation/tests, Terra/medium or high for a bounded
repair escalation, and Astra/high for ownership, unsafe code, ABI, execution
release and final evidence. Use os_auditor/os_worker/os_reviewer roles where
available; explicitly select each child model/effort without model upgrades.
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
tests share aggregate CPU/RAM budgets with all concurrent work. Build environment
settings are injected through `shell_environment_policy.set.KEY` and verified
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
