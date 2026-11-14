# Start the bounded application-test drafting queue

**The separate release manifest and verified GitHub checkpoint govern activation.**
Read `docs/verification/ultra-drafting-handoff-20260909.json`: it must have status
PASS, bind the exact queue/context/manifests, and have successful fetched-blob
verification. Otherwise finish the [handoff gates](../../docs/verification/ultra-handoff-gates-20260909.md).
The queue's review state alone does not activate drafting. This page does not
enable execution or change the user's model.

The catalog contains **273 logical cases across 97 packets**, including
**56 vector instruction/state cases**. Parameter combinations are subordinate
runs, not extra logical cases. Historical baseline runs and the vector kernel
opcode audit are not new application runs. These are test specifications;
draft completion does not mean the applications or capabilities have passed.

Root prepares the starting context with the implemented metadata validator:

```text
python3 -B /workspace/scripts/application-tests/validate.py
python3 -B /workspace/scripts/application-tests/validate.py --packet /workspace/scripts/application-tests/packets/packet-001.json --emit-context /work/application-packet-001-context-20260909-1.json
```

Run these only through the established container workflow. The output path is
a fresh example; context creation is exclusive and must never overwrite prior
evidence. Metadata `PASS` means planning metadata only. The emitter includes
the exact packet/catalog/queue hashes, selected cases and queue cursor. It
keeps `mode=draft-only`, `execution_enabled=false` and unresolved runtime
inputs; it does not bind manifests, release the queue, enforce an OS sandbox
or execute a test. Root supplies the reviewed input/capability artifacts and
binds the fresh reporting run ID separately. Generated capability contracts
are specifications, not evidence that those features work.

The release manifest supplies the retained starting context, reviewed input
and capability manifest paths/hashes, and the resolved fresh report root.
Use those exact artifacts; do not reconstruct runtime inputs or load the full
final evidence checkpoint into the executor. The initial retained context is
`docs/verification/evidence/ultra-packet-001-context-20260909.json`; packet007's
vector context is retained separately for its turn in the queue.

Once Root releases drafting, start with packet 001: `startup.argv-empty`,
`startup.environment` and `startup.stdout-stderr`. Supply only the
[README contract](README.md), that packet's emitted context, reviewed manifests
and directly needed source excerpts. Do not load the whole catalog, all
packets or historical kernel.log into the executor's context. Follow the
packet's exact read/write allowlists and permitted commands; at most three
logical cases are active. Draft-only authority covers its listed fixture and
frozen independent oracle files plus its explicit reporting exception. It
does not authorize a guest launch or production-source change.

Write the packet's immutable report under the root-bound fresh directory:
`/work/application-test-drafts-20260909/{fresh_queue_run_id}/packet-NNN/report.json`.
The braces denote a selector Root must resolve, not a literal path to use.
Report each case as `DRAFTED`, `DRAFTED_WITH_UNRESOLVED`, `BLOCKED` or `FAILED`;
never label a draft `PASS`. Include changed-file hashes, original failures,
unresolved oracles, blocked capabilities and questions for Max. Report
progress as packet index/97, produced files and the next reviewed packet.

After reporting, follow the hashed queue cursor to packet 002, then the next
listed packet through 097, without repeated permission requests. Root's
context preparation supplies each next canonical packet using the same
validator interface and a fresh context path. Replace completed case bodies
with their report hashes and a short dependency summary. Never invent a next
packet, expand scope or silently enable execution. After all reports, create
the queue's immutable summary as `DRAFT_QUEUE_COMPLETE` or
`DRAFT_QUEUE_COMPLETE_WITH_BLOCKERS`.

At the first unexpected failure, stop the affected batch and preserve the
exact action, output, original source/diff, environment and context hashes
before diagnosis. Append and fsync the original event to the queue's regular,
nonsymlink `failures.jsonl` using its specified append-only contract. Actual
validation/runtime failures also require the immediate kernel.log record.
Use fresh attempt/report paths. Continue independent queued drafting after
classification; record affected dependencies rather than inventing results.

Small fixture/oracle repairs must stay within the current draft's allowlist
and preserve the original failure and independent expected behavior. Later,
an execution-enabled reviewed packet may allow one diagnosed candidate fix:
15 minutes, two files, 80 changed lines. Preserve its patch and new evidence
for Max; never automatically accept changed kernel code. Unsafe memory,
PID/MM lifetime, ABI, scheduler/transport ownership, unclear semantics and
larger or unsuccessful repairs go to Max. Independent runtime cases resume
only in fresh guests after classification; damaged guests are retired.

Root saves coherent progress and about every 30 minutes during sustained work,
pushes it to GitHub and verifies fetched exact blobs. Preserve all failures
and active inputs; clean up only audited obsolete duplicates. Neither a
checkpoint, a drafted queue nor a missing vector feature is application
acceptance. Runtime stays blocked until its own reviewed gates and packet
version explicitly enable it.
