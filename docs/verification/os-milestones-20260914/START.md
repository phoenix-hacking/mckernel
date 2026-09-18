# Dispatcher entry point

Workflow policy updated 2026-09-17. Use GOAL.md for the unchanged whole-OS
objective, CONVERGENCE.md for execution/review/retry policy, HANDOFF.md for compact
routing, and LAUNCH.md for the existing launcher controls. Do not reinitialize
an existing goal or start a second dispatcher just to adopt these instructions.

```bash
python3 /home/holden/mckernel/scripts/run_os_goal.py
```

A normal invocation starts/resumes account-metered work. This documentation
change does not invoke it. Keep older interactive campaigns paused while the
launcher owns the checkout. A running dispatcher reloads the new policy at a
safe checkpoint after reconciling local/remote changes without discarding WIP.

## Dispatcher startup packet

1. Read CONVERGENCE.md and HANDOFF.md. Reconcile actual HEAD, tracked/untracked
   inputs, the latest relevant CURRENT.md records, launcher-owned state and file/
   runtime leases. Bootstrap handoff fields are not runtime observations. Record
   the adopted policy hash. Do not edit launcher-owned state by hand.
2. Read README.md once, then use the existing planning helper to select the exact
   task/gate/case and original prerequisites. Do not repeat a repository-wide
   audit, replay already-valid work, or give every worker the entire catalog.
3. Select one critical-path behavior and, when genuinely independent, one other
   ready task. Give each worker an invariant, source bindings, write allowlist,
   frozen expectations, allowed command/profile, evidence location and cumulative
   failure-family history. Reserve the third slot for review when needed.
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
available; explicitly select each child model/effort. At most three spawned
agents and no recursive dispatch. Final review must be independent of authorship.

Only the dispatcher owns compiler commands, build/guest leases, integration,
acceptance updates and Git operations. Retain four-CPU/12-GiB ceilings, existing
isolation/timeouts, measured free-space floors and emergency headroom. Remeasure
capacity before heavy work. Clean only verified redundant data under the existing
retention/restoration procedure. Never release a runtime lease on an unverified
cleanup claim or launch another owner after uncertain process retirement.

## Authorization and continuous work

The user's existing authorization covers project-scoped implementation, fixture/
oracle repair, toolchains, clean checkouts, isolated native/root/guest runs,
reviewed execution packets and verified GitHub checkpoints without repeated
routine questions. Choose reasonable implementation defaults and record them.
Source paths in a task are not blanket write permission. Exact reviewed execution
scope and the original safety/acceptance requirements remain mandatory.

Use noninteractive commands and existing credentials only through authorized
launcher mechanisms. For authorized host operations, use sudo -A with the
inherited SUDO_ASKPASS helper; never read, print or directly expose the credential.
Do not fabricate a human signature/approval, publish outside authorized project
scope, or sign legal agreements. Missing credentials/hardware/authority are real
blockers; project-owned missing helpers or records should be repaired, not
repeatedly returned as questions. Privilege granted to an agent is not Linux root.

There is no default calendar deadline or campaign restart cap. Continue after
checkpoints until full acceptance, exhausted credits or an explicit stop/limit.
This does not permit unchanged deterministic retry loops. Follow CONVERGENCE.md's
failure-family limits, external-wait policy and healthy-long-run protections.
The Python watcher does not yet enforce all of those distinctions; do not claim
that editing Markdown changed its runtime behavior. Preserve actual leases and
failures across every restart. Neither a paused packet nor a dashboard completes
the OS objective.
