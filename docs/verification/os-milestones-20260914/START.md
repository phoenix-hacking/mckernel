# Dispatcher entry point

Run `python3 /home/holden/mckernel/scripts/run_os_goal.py` for the autonomous
campaign. The coordinator is Sol with medium reasoning, as requested by the
user. See `LAUNCH.md` for status, restart and work-window controls. For this
existing chat, select Sol/medium and use `GOAL.md`. Dispatcher instructions:

```text
Continue the full McKernel functionality, stability, Rust/assembly and native
production goal using docs/verification/os-milestones-20260914/README.md.
Use milestones, with no calendar deadline. First read
docs/verification/os-milestones-20260914/CURRENT.md, then follow its active-run
pointer if present; otherwise run the planning index check and begin M00-A.
Preserve existing untracked work and original evidence.

I explicitly authorize tiered subagent work. Use the user-selected dispatcher and
at most three spawned agents: ordinarily two cheap workers and an independent
reviewer when needed. Start narrow inventory tasks on gpt-5.6-luna/low, specified
fixture tasks on gpt-5.6-luna/medium, bounded escalations on gpt-5.6-terra/medium,
and ownership/unsafe/execution-release reviews on gpt-6-astra/high. Use the
os_auditor, os_worker and os_reviewer project roles where available. Explicitly
select the child model and effort; use a fresh self-contained context instead
of forking the full history. Workers must not spawn more agents.

Read the runbook once as dispatcher. Use dispatch.py to select one task and
its needed gates/cases. Give workers exact input bindings, paths/symbols,
invariants, write allowlists, allowed checks and a concise result contract.
The starting source paths in a task are not blanket write permission. Do not
send workers the whole catalog, progress files or historical log.

Only the dispatcher owns builds/guests, acceptance updates and Git checkpoints.
Keep heavy work serialized under the existing isolation/resource limits. Current
runtime contracts and independently reviewed execution packets determine release;
the planning index never enables execution. Reuse valid evidence where consumed
inputs still match. Complete required tests; avoid unrelated repeat testing.

Continue ready independent tasks without asking at each packet. After one failed
attempt and one bounded correction, escalate the affected task with its original
failure and minimal reproducer. Preserve a small CURRENT.md, append-only events,
exact evidence hashes, file/runtime leases and the next three tasks. Checkpoint
about every 30 minutes and before long runs/session end; verify remote blobs.
On quota exhaustion preserve the cursor and stop repeated spawn attempts.

The user explicitly authorized full permissions and requested no questions for
the standalone launcher. Do not ask for routine confirmation or clarification.
Choose reasonable defaults and record assumptions. Log missing facts, credentials
or hardware as task blockers and continue independent work. Use noninteractive
commands, including sudo -A with the launcher's inherited SUDO_ASKPASS helper;
never wait on password prompts or read/print the private credential. Include this policy
in worker packets. The launcher applies full filesystem/network access and never
approval policy to each new/resumed dispatcher; it does not grant Linux root.

Priority: published-response retention/fault modes; Linux/native collector and
paired backend; VM invalidation and physical ring pressure; first accepted cases;
native restoration; advanced capabilities and vectors/HPC; native/ABI and language
closure; exact packages; integration, hardware qualification and release.
Prepare independent later work when useful, but spend effort on the earliest
execution blocker. Never convert drafting/build/protocol results into runtime
acceptance. Report exact gate/case/exposure counters and the next blocker.
```

Single-command local launch (starts or resumes the launcher's own goal):

```bash
python3 /home/holden/mckernel/scripts/run_os_goal.py
```

This starts account-metered work when issued by the user; preparing/testing the
launcher did not start the OS campaign. It defaults to a 12-hour work window,
with up to ten minutes inside that window reserved for a checkpoint. Rerun the
same command to resume its saved thread. Keep this chat's older goal paused
while using the launcher; do not dispatch two campaigns on this checkout.
