# Native collector lifecycle producer model design 1

Date: 2026-09-15
Task: `M02-C-lifecycle-producer-model-design`
Disposition: `MODEL_DESIGN_ONLY`

The new-file allowlist is `README.md`, `model.rs`, `reference.c`, `vectors.json`,
`expected.json`, and `harness.py` under
`scripts/tests/fixtures/native-lifecycle-model-v1/`, plus
`scripts/tests/test_native_lifecycle_model.py`. No production imports, extracted
snippets, ABI exports, hooks, launcher changes or evaluator integration are allowed.

The bounded model supports two applications, four processes, eight threads, 128
operations and 256 event attempts per vector. It separates object identity,
lifecycle, reference count and retained storage. Operations are ALLOC, BIRTH after
fallible preparation and before RUNNABLE, ABORT for unpublished failures,
THREAD_TERMINAL, PROCESS_TERMINAL, RETIRE_BEGIN at refcount zero or consumed
exclusive unscheduled-destruction authority, THREAD_RETIRE, PROCESS_RETIRE and
CAPTURE_END. Process retirement additionally requires released main-thread storage;
zombie/parent-wait and VM ownership are explicit blockers.

Every event contains model version, attempt sequence, kind, typed subject and parent
keys, optional numeric PID/TID attributes, operation/source branch, clock, logical
time and typed payload. Subject identity joins capture incarnation, OS slot and
generation, application/process/thread instance and exec instance. Checked nonzero
u64 identities never wrap; numeric IDs are attributes. Terminal payload preserves
raw status, original status/signal inputs and branch without claiming a guest wait.

Serialized operations atomically commit state and event attempts. Birth precedes
runnable; terminal precedes retirement; group terminal never fabricates sibling
events. A registry surviving launcher departure owns identity, retirement snapshots
and capture control. Event exhaustion latches irreversible incompleteness and exact
loss counters without preventing cleanup transitions. Complete capture requires
contiguous attempts, zero loss, no reservation, explicit end and all scoped objects
retired. Logical time is model evidence only.

Strict vectors cover preparation/clone abort, immediate exit, TID reuse,
thread-only and last-thread exit, competing group exit, inherited group status,
duplicate terminal, retained references, zombie wait, unscheduled destruction,
main-storage retention, launcher loss, teardown failure, buffer/control exhaustion,
missing birth/end, forged identity and overflow. Bounded interleavings do not claim
real race testing.

Independent Rust ownership transitions and C tables consume identical literal
operations and must each match reviewed `expected.json` before cross-comparison.
Mutants allowing birth after runnable, early retirement, silent loss and TID aliasing
must fail. Cheap pre-build checks are diff/hash and Python AST parsing only. A later
dispatcher packet must bind toolchains and retain bounded build/run evidence.
This design freezes no ABI and grants no native collection, application or
production credit.
