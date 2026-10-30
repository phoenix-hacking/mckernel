# Functional McKernel source-only child and pidfd handoff successor

Status: UNREVIEWED; NOT RELEASED. This preserves all predecessors and is not a
claim of live supervisor, source-view, current-free, native or application proof.
`SOURCE-MANIFEST.json` binds the private Python sources. Only
`test_callback_handoff.py` is selected for this successor; the other copied tests
are inherited historical source and are not compatible successor test evidence.

`DeferredFork.fork_and_pin(record, child_callback)` enters the child-only
try/finally while configured stops remain masked, restores handlers and mask there,
and invokes all child exec setup before unconditional `_exit(127)` on an error or
unexpected return. Owner, validator and watchdog use this callback; parent PID,
pidfd and birth stay in the pre-reserved child record. Trusted runtime excludes
arbitrary asynchronous thread injection and uncatchable process death; actual
external supervisor/watchdog ownership is still required.

Validator adapter pidfd acquisition uses the same main-thread configured-stop
deferral. The caller preallocates an operation-owned pidfd record; the guard stores
and publishes the held descriptor before restoring handlers, and a pending stop or
restoration error marks the record UNKNOWN without closing the descriptor. A failed
publication also leaves UNKNOWN retained. The validator pauses in its UNKNOWN path;
the operation supervisor must retain process and lease and determine its disposition.

The supervisor inline loader now lists `pidfd_custody` before `deferred_fork` and
`adapter`. A proposed validator inline loader pins the exact root-owned immutable
runtime, module bytes, protocol, original parser and contract, local graph contract,
and separately reviewed profile via a root-owned immutable manifest; it loads in
explicit dependency order and uses the exact argv reconstructed by the supervisor.
The loader requires a locally installed `custody_protocol_v2.py`, graph contract
and selected profile, each pinned before execution. Root-owned immutable files,
trusted ancestry, actual manifest and correct runtime must be supplied by a reviewed
bootstrap; none has been installed or established here. The profile and adapter
selection hashes are deliberately None. Actual-operation gates, collector, launch,
effective-view and release remain disabled. Lifecycle after successful validator
return needs independent review before any gate is selected.

Syntax checks only: `/usr/bin/python3` 3.8.10 `ast.parse` passed all 16 Python
files and the three embedded loader programs. No tests, imports, real fork,
signals, pidfd syscalls, root operations, mount, or workloads were run.

Proposed next test after independent source/profile review and Root's explicit
admission (no real fork, signal, pidfd or root operation):

```
cd /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/child-callback-expert-1
/usr/bin/python3 -B -m unittest -v test_callback_handoff
```

Tests synthesize restoration failure, pending-handler raise, child callback raise
and return, and pending-stop/restoration failures during descriptor handoff. The
external graph module source imported by the test must be bound to the reviewed
`../adapter-readiness-expert-1/graph_observations.py` before admission. No result
from these unit tests authorizes bootstrap or a physical workload.
