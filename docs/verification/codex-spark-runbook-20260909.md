# Run the released McKernel drafting goal

This is the operating guide for the [Spark goal](codex-spark-goal-20260909.md).
It also applies if the user chooses Luna. The Ultra handoff notification has
already happened; when the user starts this goal on the chosen executor,
begin drafting instead of stopping again for the historical Ultra handoff.
Preparing the goal does not start it or switch models.

## Start with a small context

Use `/home/holden/mckernel`, branch `codex/local-native-staging-repair`.
Read this guide and the [executor contract](../../scripts/application-tests/README.md)
once. Read the current top-level AGENTS instructions; older dated history is
background, not another campaign to restart. Then load the release, the two
small reviewed manifests, and only the active packet context below.

| File, relative to the repository | When and why |
| --- | --- |
| `docs/verification/codex-spark-goal-20260909.md` | The goal and exact completion criteria. |
| `scripts/application-tests/README.md` | Shared fixture/oracle/report contract and limits. |
| `docs/verification/ultra-drafting-handoff-20260909.json` | Startup authority, hashes, selected context and resolved report root. |
| `docs/verification/ultra-draft-inputs-20260909.json` | Exact retained input pair; explicitly incomplete for new runtime tests. |
| `docs/verification/ultra-draft-capabilities-20260909.json` | Broad execution blockers; baseline facts are separate. |
| `docs/verification/evidence/ultra-packet-001-context-20260909.json` | Starting packet: three startup cases, exact writable files and report contract. |
| `scripts/application-tests/handoff-start.md` | Established handoff mechanics, if needed. |
| `scripts/application-tests/validate.py` | Invoke to check metadata and emit one next context; do not edit it. |
| `scripts/application-tests/draft-queue.json` | Machine-read the ordered cursor only; do not print all packet rows. |
| `scripts/application-tests/cases.json` | Machine input to the emitter; never print the full catalog into context. |
| `docs/verification/ultra-vector-test-plan-20260909.md` | Read when a vector packet becomes active. |
| `docs/verification/evidence/ultra-packet-007-context-20260909.json` | Retained vector context, only when packet 007 becomes active. |
| `docs/verification/ultra-handoff-gates-20260909.md` | Relevant excerpts for unresolved capability questions or Max escalation. |
| `docs/verification/ultra-application-test-plan-20260909.md` | Overview for the coordinator/Max, not required in every packet. |
| `docs/verification/ultra-final-checkpoint-20260909.json` | Large evidence manifest: machine-check references; do not load it wholesale. |
| `docs/verification/evidence/ultra-handoff-github-verification-20260909-1.json` | Retained proof that release commit `7b32298119df13a83240e082c275c34d184f7ccc` passed exact fetched-byte verification. Read only status, commit and verification fields. |

Before drafting, verify the release's `status=PASS`, `release=released-for-drafting`,
`mode=draft-only`, both execution flags false, and counts 273/97/56. Verify every
relative identity row for its queue, catalog, contexts and reviewed manifests
against actual file size/SHA-256. Machine-check the retained GitHub proof for
status PASS, that accepted commit and `drafting_release_verified=true`.
The current branch may be a later descendant containing these goal documents
or drafted fixtures; it must preserve the release-bound files unchanged.
A missing or mismatched input is a specific startup failure, not permission to
rebuild the kernel or invent replacement metadata. Preserve it and report it.

## Paths and bounded coordination

The executor performs both narrow fixture drafting and the small amount of
coordination needed to advance the released queue. These coordination actions
are covered by the user's existing instructions to continue, log and checkpoint:

- Read the bootstrap files above, file identities and minimal report/cursor
  metadata. Use the existing validator to emit only the next queued context.
- Read/create/edit only the active packet's listed fixture, input and oracle
  files. Reading those same files to review or resume their edits is included.
- Create packet reports and failure artifacts in the bound reporting root;
  append failure events, and append an exact validation-failure entry to
  `kernel.log` without loading its history.
- Perform source-control status/diff/hash checks, commits, pushes and fetched
  verification. Preserve reports in the repository evidence location below.

These coordination actions do not expand application-test or production-code
scope. Do not edit this goal, the released packets/catalog/validator/manifests,
old evidence or kernel sources to make work easier. Do not create a new runner,
supervisor, new packet, new capability, shell-based test interface or guest.
At most one packet is active, including when helpers or subagents are used.

| Purpose | Inside native container | Host filesystem |
| --- | --- | --- |
| Repository | `/workspace` (read-only) | `/home/holden/mckernel` |
| Scratch | `/work` | `/home/holden/mckernel-work/scratch` |
| Bound report root | `/work/application-test-drafts-20260909/ultra-handoff-1` | `/home/holden/mckernel-work/scratch/application-test-drafts-20260909/ultra-handoff-1` |

The report root already exists and was empty at handoff. Do not create it again
or delete it. Edit allowed repository files with the workspace editor on the
host; the container deliberately cannot write `/workspace`. Use the host alias
of scratch for report/file operations when working outside the container.
Keep canonical `/work` paths in reports and record the alias mapping once.
Never remount the repository writable or enlarge container limits.

Metadata and source checks use the existing wrapper, for example:

```bash
/home/holden/mckernel-work/bin/mckernel-container native python3 -B /workspace/scripts/application-tests/validate.py --packet /workspace/scripts/application-tests/packets/packet-001.json
/home/holden/mckernel-work/bin/mckernel-container native git -C /workspace diff --check
```

The native wrapper fixes CPUs 2–5, four CPUs, 12 GiB, no swap, 512 tasks,
uid/gid 1000 and no network. Git network operations use the host repository.
Use existing authorized authentication; never store credentials in a goal,
command argument, environment, fixture, report or Git artifact.

For packet 002, the coordinator may use this existing emitter command:

```bash
/home/holden/mckernel-work/bin/mckernel-container native python3 -B /workspace/scripts/application-tests/validate.py --packet /workspace/scripts/application-tests/packets/packet-002.json --emit-context /work/application-packet-002-context-20260909-1.json
```

For subsequent packets substitute only the exact ID from the verified cursor.
The output is exclusive. If it already exists, verify its packet/catalog/queue
hashes and use it if identical, or preserve it and use a fresh output suffix.
Never overwrite a context. Context-emission files are the coordinator's input
artifacts; they are separate from the packet's restricted reporting writes.
Metadata PASS does not mean a fixture compiled, ran or passed.

## Draft and report each packet

Check the active context's hashes, ID/version, next cursor, cases and limits.
Resolve its manifest placeholders to the two reviewed files listed above and
`fresh_queue_run_id` to `ultra-handoff-1`. Do not execute command placeholders.
Keep only the current case bodies, their contracts and short dependency notes.

Implement each permitted fixture/input file and its corresponding oracle.
`payload_contract.path` is relative to `scripts/application-tests`; the exact
repository destination is always the packet's `write_allowlist` entry. Never
create a repository-root `cases/` directory from that relative payload path.
Cover the complete specified parameter vectors, exact operations, negative
results, bounds and cleanup. Freeze independent expectations from the reviewed
specification; report any unknown constant or semantic rule explicitly. An
unimplemented runtime runner or blocked feature alone is not a drafting blocker.
Do not mark a draft complete by returning success without exercising the case.
Initial fixture creation is not limited to 80 lines; that bound applies to a
later candidate repair. Follow case resource limits regardless of source size.

When frozen fields conflict, preserve both fields and identify the precise
conflict in the allowed oracle and report. Draft the intended operation with a
clearly labeled proposed invocation/expectation, and use
`DRAFTED_WITH_UNRESOLVED` pending Max review; do not change frozen metadata or
silently choose an authoritative field. Known packet 001 examples:

- `startup.argv-empty`: the payload argv lists only its executable, while an
  assertion requires argc 4 with `app`, `A`, an empty argument and `B`.
- `startup.stdout-stderr`: the operation writes binary stderr, while the
  generic oracle stderr field is empty.

These are specific drafting questions, not reasons to skip the whole packet
or campaign. Preserve useful fixture work and propose exact corrected values
inside the writable oracle/report for independent review before execution.

Review the source against every assertion and run the two permitted checks.
No compiler, payload, reference application, vector instruction test or QEMU
run is enabled by this goal. Record build/runtime status as NOT_RUN, not PASS.
Likewise, do not demand completed runtime input manifests before drafting.

Create `packet-NNN/report.json` under the report root using its exact reporting
schema. Record case-specific statuses, implemented operations and vectors,
source/oracle paths and hashes, checks actually run, unresolved assertions,
execution blockers, first failure reference and smallest Max question. A
`DRAFTED` case has its complete specified source/input and oracle; unresolved
expectations require `DRAFTED_WITH_UNRESOLVED` or a justified `BLOCKED`/`FAILED`.
Never use PASS as a draft status or use one generic blocker for all 273 cases.
Each report's `cases` IDs must match its packet exactly; its parameter map must
account for every specified parameter/vector. Each BLOCKED/FAILED case names
the concrete missing item, independent work completed, and why that item
prevents further drafting. Empty changed-file lists require that case-specific
evidence; a missing runtime capability alone does not justify them.

Publish each report once. The coordinator may exclusively create a fresh
`.report-<nonce>.tmp` in that packet's directory, write and fsync complete JSON,
and validate its required fields before publishing. Use an atomic operation
that fails if `report.json` already exists, such as a same-filesystem hard link
from the owned staging file; fsync the directory, then remove only that staging
file. A normal overwriting rename is not permitted. Apply the same procedure
with a fresh `.summary-<nonce>.tmp` for the final queue summary. Interrupted
staging files are preserved/reviewed and never counted as completed reports.
Do not replace or edit a committed report.
If an interrupted write leaves a malformed report, preserve its exact bytes
and failure event; that packet needs a reviewed recovery before completion.
Do not overwrite the report, invent a new run ID or silently count it complete.

At the first unexpected failure, preserve command/tool action, environment,
original stdout/stderr and source/diff/context hashes in the named failure
directory. Append one JSON event to `failures.jsonl` with
`O_APPEND|O_CREAT|O_NOFOLLOW`, verify it is a regular file, and fsync. Do not
truncate the log or issue hidden retries. Actual validation failures also
require the immediate append to `kernel.log`. One small diagnosed correction
may touch only the active allowed files, within 15 minutes/two files/80 changed
lines, with original failure and before/after evidence retained. Oracle
weakening and production repairs remain prohibited. Continue independent
queued drafts after classification; carry unresolved dependencies to Max.

After the immutable report, provide the user a short packet progress update
and advance automatically to the next listed context. Do not ask permission
again. Release completed case bodies from context before loading new ones.

## Resume and checkpoint

On resumption, inspect report IDs/statuses/hashes programmatically, without
loading all previous case bodies. Verify completed report source/oracle hashes.
Resume the first unfinished packet in queue order, preserving partial files
and failure evidence. Do not rerun completed packets, reset existing work,
silently repair old report mismatches, or claim a malformed report completed.
Finish other independent packets while identifying any recovery needed by Max.
Skip valid published reports even when their status is BLOCKED or FAILED;
carry their precise dependency notes forward. If scratch evidence is missing,
restore it exclusively from its verified committed byte-identical mirror,
preserving the same bound run ID and hashes. A mismatch is a recorded recovery
problem, not permission to replace either version or invent a new run ID.

After coherent packet groups and about every 30 minutes, checkpoint the allowed
draft files and byte-identical immutable reports/failure artifacts. Preserve
them under the coordinator evidence directory:
`docs/verification/evidence/application-drafts-20260909/ultra-handoff-1/`.
Mirror packet report/failure paths without overwriting prior artifacts. Copy
the growing failure log under a new numbered snapshot name at each checkpoint;
never overwrite a previously committed snapshot. Retain each emitted context
with its packet's evidence so later contexts survive a crash or scratch loss.
These evidence copies are the explicit coordination exception, not additional
test implementation or production write access. Keep every file below 95 MiB;
split any larger archive with a hashed ordered reconstruction manifest.

Commit only the intended drafts/evidence/log append, push the current branch
without rewriting history, fetch that exact branch and verify the fetched
commit equals the pushed commit. Compare the checkpoint's changed source and
report/artifact blobs with their recorded hashes. Keep verification output in
a fresh scratch report; do not require a report to contain its own Git hash.
Do not run the old whole-tree release generator after adding fixtures: its
original planning snapshot is historical evidence, not the live draft catalog.
Clean up only verified obsolete duplicates; preserve all failures and active
dependencies, including the mounted scratch backing file.

## Finish with a concrete Max handoff

After all 97 valid immutable reports exist, verify exact unique coverage of the
273 queue IDs and every referenced file hash. Create `queue-summary.json` once
under the report root, with report/context/source/oracle hashes, four separate
case-status counts summing to 273, exact parameter coverage, remaining blockers
and prioritized Max questions. Include each original failure and candidate
patch reference; distinguish source review/metadata checks from NOT_RUN build
and runtime evidence. Missing files, malformed reports and unresolved hash
mismatches prevent claiming completion.

Use `DRAFT_QUEUE_COMPLETE` only when all drafts are complete; otherwise use
`DRAFT_QUEUE_COMPLETE_WITH_BLOCKERS` with the exact unresolved cases and reasons.
Archive and verify the final GitHub checkpoint, announce the goal's exact
completion phrase, and stop for Max review. Do not automatically begin tests,
change models or broaden the next phase.
