# Autonomous McKernel goal

User-selected setup: Sol with medium reasoning as dispatcher, Luna workers,
and focused Astra/high reviews only when required. The launcher selects these
settings itself; changing this chat's model is unnecessary for a script run.

Run `python3 /home/holden/mckernel/scripts/run_os_goal.py`. See `LAUNCH.md`.
The launcher owns one separate persistent thread and resumes its exact ID; it
does not replace the older goal in this chat. Keep that older goal paused while
the launcher works. The following chat controls are an alternative to the script.

This thread already has an unfinished goal, observed as `usageLimited` during
planning. Preserve it. Once quota is available, send:

```text
Use docs/verification/os-milestones-20260914/GOAL.md as the execution instructions
for our existing McKernel goal. Read CURRENT.md and resume the next ready task.
I explicitly authorize automatic subagent dispatch following this plan.
```

Then use `/goal resume` or the client's resume control. Use `/goal` to inspect
status and `/goal pause` to stop continued dispatch. A normal instruction does
not itself guarantee the client has resumed a usage-limited goal. These controls
are documented in [Follow a goal](https://learn.chatgpt.com/use-cases/follow-goals).
Changing reasoning effort does not replenish quota.

In a new conversation without an unfinished goal, set:

```text
/goal Complete the McKernel OS functionality, stability, native production and
Rust/assembly acceptance objective defined in
docs/verification/os-milestones-20260914/README.md. Follow GOAL.md and CURRENT.md.
Automatically dispatch bounded cheap subagents, verify their results, and continue
through dependency-ready milestones. Finish only when all required acceptance
contracts pass; preserve a verified checkpoint and exact blockers when progress
requires unavailable quota, hardware, access or user decisions.
```

Execution instructions for the dispatcher:

1. Follow START.md's resource, evidence and dispatch rules. Read README once;
   resume the current cursor instead of repeating the repository-wide audit.
2. Own one durable whole-OS objective. Its 14 milestones and 68 tasks are work
   items, not 68 separately spawned goals. Current tool rules govern goal status.
3. Automatically choose ready independent tasks and spawn at most three children
   total: ordinarily two cheap workers and one reviewer as needed. Explicitly use
   Luna/low for bounded audits, Luna/medium for specified implementation, and
   Astra/high for hard ownership/unsafe/ABI/release review. Use fresh packets;
   workers cannot create goals, recursively dispatch or alter acceptance.
4. Follow each original case/gate contract. Completion means all 130 production
   gates, seven language gates and required application/configuration coverage
   accepted on exact artifacts, including full external qualification. Source,
   compilation, fixtures and local smokes alone do not meet that condition.
5. Continue after each coherent checkpoint without waiting for routine user
   confirmation. When one task blocks, preserve it and select unrelated ready
   work. Keep one build/guest owner under the original isolation and timeouts.
6. Review worker results, escalate after the bounded retry limit, and preserve
   original failures. Update CURRENT and append-only events with evidence hashes,
   source/binary identity, leases, counters and next three tasks. Commit/push and
   verify fetched blobs about every 30 minutes and before long runs/session end.
7. Treat a roughly 12-hour unattended session as a work window. Keep making
   useful progress while the client, machine and quota permit it. It is not a
   promise of uninterrupted execution or a deadline for the full OS contract;
   the required 168-hour soaks and larger exposures remain mandatory. The user
   can pause an interactive goal when returning. The launcher defaults to a
   12-hour window and reserves up to ten minutes within it for checkpointing.
   Obey its stop/checkpoint message, join workers and preserve process identities.
8. Before low quota or a controlled stop, save a short restart record and inspect
   active process identities. Do not loop on quota errors, infer permission from
   elapsed time, relax gates to continue, or mark the OS complete at a checkpoint.

For local CLI sessions keep the computer awake and the session/runtime available.
The launcher enables goals and supplies Sol/medium, cheap-worker defaults and
the three-child/no-recursion limits directly. It does not depend on project-local
configuration being trusted. No 12-hour campaign was started during preparation.
