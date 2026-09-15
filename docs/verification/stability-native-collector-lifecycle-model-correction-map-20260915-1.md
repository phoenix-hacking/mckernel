# Native collector lifecycle model correction map 1

Date: 2026-09-15
Task: `M02-C-lifecycle-producer-model-correction-map`
Disposition: `CORRECTION_MAP_ONLY`

Attempt 2 may replace all seven source-packet files within the existing allowlist;
attempt 1 remains immutable in its retained failure archive. This record releases
no source checks, compilation, execution, ABI freeze or acceptance.

## Canonical operation schema

Strict JSON operations are `[id, op, key, parent, a, b, c, d]`, exactly eight
fields with contiguous IDs. A full key is `[capture, slot, os_generation,
application, process, thread, exec]`; process keys use thread zero. Parent is a
full key or null. Unknown operations, duplicate JSON keys, booleans as integers,
nonzero unused arguments and unexpected parents are rejected. Instance fields are
nonzero u64 except slot; PID/TID conversion accepts only 1 through `INT32_MAX`,
apart from explicitly unassigned TID zero.

Operations are `P_ALLOC`, `T_ALLOC`, `TID_ASSIGN`, `BIRTH`, `RUNNABLE`, `REF_ADD`,
`REF_DROP`, `RETIRE_BEGIN`, `RETIRE_DONE`, `ABORT`, `TERMINAL`, `ZOMBIE_SET`,
`PARENT_REAP`, `VM_RELEASE`, `MAIN_STORAGE_RELEASE`, `LAUNCHER_LOSS`,
`CAPTURE_END` and `TEARDOWN_FAIL`. Allocation carries PID or TID/main status;
abort carries failure stage; terminal carries raw u32, status u8, signal u8 and
branch. Other arguments are zero.

## Separate ownership

Process and thread registries have distinct full-key lookups. Each retains parent,
numeric attributes, phase, references, exclusive authority, terminal tuple and
retirement snapshot. Process rows additionally retain main-thread key, zombie, VM
and main-storage obligations. Retired identities remain present. The model bounds
two applications, four processes and eight threads; active TID exclusion is scoped
to the owning process.

Allocation starts with one reference and `ExclusiveUnpublished` authority. Adding
a reference irreversibly revokes that authority; birth consumes it. An aborted
object may enter exclusive destruction only while retaining the authority and
exactly one reference, consuming both atomically. Otherwise retirement requires
zero references. References cannot be acquired after retirement begins.

Phases are Allocated to Born to Runnable for threads, Allocated to Aborted, and
Born/Runnable to Terminal; only Terminal/Aborted proceeds through Retiring to
Retired. Process birth precedes thread birth. Thread birth needs assigned TID and a
live born process; group terminal blocks later births. Thread retirement requires
terminal/abort and satisfied reference/authority rules. Main-thread logical
retirement retains its storage.

Process retirement requires every child thread retired, zero process references,
released VM and main storage and no zombie. Main storage release follows main-thread
retirement; VM release follows process terminal/abort and all thread retirements;
parent reap clears only a real zombie. Duplicate retirement fails.

Terminal branches are ordinary-thread 1, first-group 2, inherited-group 3 and
last-thread 4. Branches 1/2/4 check the raw formula; branch 3 equals the retained
process tuple. Last-thread process terminal requires all siblings terminal or
retired. No sibling event is synthesized.

## Oracle and vectors

Each operation emits one strict JSON array `[id, result, events, process_rows,
thread_rows, control]`. Sorted rows include every retained field. Events include
schema, attempt sequence, operation, kind, full key and parent, numeric attributes,
terminal/reason payload, clock 1 and logical tick equal to operation ID. Control
includes attempts, retained, lost, overflow, ended, incomplete and outstanding
reservations. Missing, extra, malformed or trailing output fails.

`expected.json` may pool exact literal rows/events/control and have steps reference
the pools, but expansion performs literal substitution only—no transition
calculation. Each independently implemented Rust ownership model and C table model
must match expanded literals before cross-comparison.

Required vectors cover preparation/assigned-TID/late-clone abort, immediate and
thread-only/last-thread exit, TID reuse, competing group orders, inherited and
duplicate terminal, retained thread/process references, revoked/forged authority,
reference resurrection, zombie/reap, unscheduled destruction, main storage, live
sibling and VM blockers, launcher loss, teardown failure, buffer/counter/reservation
faults, missing birth/end, domain/generation mismatch, numeric widths, capacities
and malformed schema. Required rejected mutants are birth-after-runnable, early
retirement, silent loss and TID aliasing.

Event overflow must preserve cleanup state and latch exact irreversible loss.
Counter overflow, unfinished reservation and teardown failure force incomplete.
Capture end requires all subjects retired, no reservation and zero loss. Seeded
boundary/fault fixtures can never claim complete capture.
