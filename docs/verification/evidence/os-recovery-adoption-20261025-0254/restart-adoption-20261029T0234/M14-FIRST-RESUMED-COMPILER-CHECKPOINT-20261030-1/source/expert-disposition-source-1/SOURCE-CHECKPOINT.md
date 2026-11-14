# Functional M14 operation-owned disposition successor

Status: SOURCE ONLY; UNREVIEWED; NOT RELEASED. Previous candidates and evidence
are preserved. `SOURCE-MANIFEST.json` binds exact files; `SOURCE-DELTA.patch`
compares the close-state predecessor. Two intermediate source snapshots are
preserved in `../expert-disposition-pre-output-limit-1` and
`../expert-disposition-output-bound-1` with their original manifests.

The operation's RLock is outermost for UNKNOWN and local-close admission through
publication; the nested order is operation, session, pidfd record, duplicate
socket record. Configured-stop delivery is deferred through acquisition and close;
a reentrant stop may latch UNKNOWN but cannot restore a closed/unknown record to
live. Closing this local session never retires root, native, mount or process
ownership. The operation pre-registers a duplicate-socket record before os.dup;
the duplicate is recorded and the actual socket object adopted while configured
stops are masked. Partial adoption or close becomes CLOSURE_UNKNOWN with no
usable fd, a historical identity, and do-not-use-or-retry disposition. Both
records and any socket object remain operation-owned on uncertainty.

The inline caller receives the typed bytes-only collection result and operation
from `validator_entry.run`. On confirmed local disposition it requests one
canonical newline-terminated JSON record on the existing captured stdout, with
`record_type=source_collection_result_data_v1`, `authority=null`, the inherited
operation nonce, payload length, SHA-256 and base64. This is diagnostic DATA only.
The NEW format limit `MAX_RESULT_OUTPUT_BYTES=2097152` limits both raw payload
and complete serialized record. Oversize is rejected with actual lengths; no
truncation occurs. Encoding, short-write or flush failure retains operation,
session and plan as UNKNOWN; the external owner remains responsible. The exact
stdout stream/process/source binding, blocking behavior and terminal handling
need independent review and actual admission. This output is not acceptance.

The existing `_collect`, source-binding, effective-view and profile refusal gates
remain unchanged, and no real collector result or output is claimed. Root must
separately establish actual source exclusion, graph/pre-shadow/effective view,
nonce and current intent, caller join/current-free, resource/clock constraints,
native ownership, source/profile installation and one-shot admission. Trusted
runtime excludes arbitrary injected asynchronous thread exceptions and
uncatchable process death; real parent/watchdog ownership remains required.

`/usr/bin/python3` 3.8.10 AST parsing passed 18 Python files and three embedded
loader programs. No tests, fork, signals, pidfd syscalls, root operations, mount,
stdout result emission or workloads ran. After independent review and Root
admission, proposed synthetic tests use separate interpreter processes:

```
cd /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/expert-disposition-source-1
/usr/bin/python3 -B -m unittest -v test_actual_close test_validator_consumer
/usr/bin/python3 -B -m unittest -v test_callback_handoff
```

These tests are source only and do not provide a physical execution release.
