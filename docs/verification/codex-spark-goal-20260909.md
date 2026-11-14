# Codex Spark goal: draft the complete McKernel application test suite

Use this goal after selecting Codex Spark. Luna may follow the same goal.
Preparing this document does not start the drafting campaign or change models.

## Goal to paste into Goal mode

Work in `/home/holden/mckernel` on `codex/local-native-staging-repair`.
Complete the released application-test drafting queue: **273 logical cases
across 97 packets, including 56 vector instruction/state cases**. Create the
specified test fixtures or pinned-application input specifications and their
independent oracle JSON files. Produce useful, specific tests that expose bugs.
This goal completes test drafting; it does not execute or accept the new suite.

First read `docs/verification/codex-spark-runbook-20260909.md` and follow its
startup checks and file-reading order. The Ultra release was accepted at
commit `7b32298119df13a83240e082c275c34d184f7ccc`; the runbook identifies its
retained GitHub verification proof. Preserve the released catalog, packets,
validator, contexts, input/capability manifests, kernel and launcher unchanged.

Start with packet 001 and continue automatically through packet 097. Use only
one packet and at most three logical cases at a time. Load selected case bodies
through the existing context emitter; do not load the whole catalog, other
packet bodies, historical kernel.log or complete evidence archives into context.
Replace completed case bodies with report hashes and a short dependency note.
Do not ask for permission between packets, routine edits or checkpoints.

For every active case, implement its exact operation, parameter vectors,
resource bounds, cleanup and expected output contract. Write a versioned
independent oracle with fixed bytes, values or named relational assertions.
Retain every required parameter; parameter executions do not add logical cases.
Do not finish with empty files, comment-only fixtures, unconditional success,
or tests that never exercise the specified behavior. Do not invent expected
results or resolve an uncertain errno by accepting multiple arbitrary values.

All packets are `draft-only` with execution disabled. Missing runtime support
does not prevent drafting a well-specified test. Record a drafting blocker only
when a concrete missing interface, input or semantic expectation actually
prevents that draft. Complete the independent work, record the exact missing
item and smallest question for Max, then continue the next independent packet.
Do not implement a runner or supervisor, compile/run payloads, launch guests,
modify production code, weaken an oracle or change the released plan to clear
a blocker. Those actions require a later reviewed execution scope.

For vector cases, preserve the reviewed per-engine CPUID/OSXSAVE/XCR0 gates,
independent scalar/math expectations and emitted-instruction requirements.
Cover SSE/XMM, AVX/AVX2/YMM and the specified optional extensions. AVX-512 stays
conditional on the actual guest feature and enabled-state checks. Host CPU
flags alone never authorize guest instructions; missing support is not PASS.

Preserve each original failure before diagnosis. Use the immutable per-packet
reports and append-only failure log defined by the packet and runbook. Small
fixture/oracle corrections must preserve independent expectations, stay inside
the active write allowlist, and respect one candidate, 15 minutes, two files
and 80 changed lines. Escalate unsafe, kernel/ABI/lifetime/scheduler/transport,
unclear or unsuccessful repairs to Max. No production repair is enabled here.

After every packet, report its index out of 97, exact case statuses, files
created, unresolved expectations, original failures and next packet. Checkpoint
the drafted files and immutable reports to GitHub after coherent packet groups,
about every 30 minutes, and before stopping. Verify the fetched commit and file
hashes. Preserve prior evidence and active inputs. Follow the runbook's bounded
coordination permissions for contexts, reporting, logging and Git checkpoints.

Finish only when all 97 immutable packet reports account for all 273 unique
case IDs exactly once, with meaningful drafts wherever the specification allows
them and precise evidence for every remaining blocker. Create the immutable
queue summary with separate `DRAFTED`, `DRAFTED_WITH_UNRESOLVED`, `BLOCKED` and
`FAILED` counts, report/file hashes and prioritized Max questions. Verify the
final GitHub checkpoint. State **"The Spark drafting queue is complete and
ready for Max review"**, identify any blockers, and stop. Do not claim that
drafted tests passed or that the OS is production-ready.

## Entry files

- [Execution runbook](codex-spark-runbook-20260909.md): startup, exact paths,
  permitted coordination, checks, crash recovery and completion.
- [Executor contract](../../scripts/application-tests/README.md): fixture,
  oracle, report, failure and resource requirements.
- [Starting context](evidence/ultra-packet-001-context-20260909.json): only
  `startup.argv-empty`, `startup.environment` and `startup.stdout-stderr`.

The runbook lists the remaining references and when to read them. Do not load
every linked document into the executor at startup.
