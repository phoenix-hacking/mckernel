# Native collector lifecycle literal corpus draft 1

Date: 2026-09-15
Task: `M02-C-lifecycle-producer-model-corpus-draft`
Disposition: `CORPUS_DRAFT_ONLY`

This independent review draft expands the committed attempt-2 correction map. It
does not constitute materialized or reviewed JSON and releases no source checks,
compiler/model execution, ABI freeze, native collection or acceptance.

## Frozen conventions

Input operations are exact eight-field arrays `[id,op,key,parent,a,b,c,d]`.
Expected output for each operation is `[id,result,events,P_rows,T_rows,control]`.
Results are the literal strings `OK`, `SCHEMA`, `KEY`, `STATE`, `IDENTITY`, `REF`,
`BUSY`, `STATUS`, `LIMIT`, and `CLOSED`. Whole-document/schema rejection exits 2
with empty stdout/stderr and executes no transition. Semantic rejection emits no
event, leaves lifecycle rows unchanged and latches incomplete.

Process rows are `[key,parent,pid,phase,refs,authority,terminal,abort_reason,
main_key,zombie,vm_held,main_storage_held,snapshot]`. Thread rows are
`[key,parent_process,pid,tid,is_main,phase,refs,authority,terminal,abort_reason,
snapshot]`. Authority is `E` or `N`; terminal is null or
`[raw,status,signal,branch]`; snapshots retain `[key,terminal,abort_reason]`.

Events are `[1,attempt_seq,id,kind,key,parent,pid,tid,payload,1,id]`, where payload
is `[raw,status,signal,branch,reason]`. Every successful state-changing operation,
including reference and administrative operations, attempts exactly one event.
Failed operations attempt none. Process/thread-specific ALLOC, TERMINAL,
RETIRE_BEGIN and RETIRE_DONE event kinds are distinct. Control is
`[attempts,retained,lost,overflow,ended,incomplete,reservations]`.

Process allocation starts with no main-thread key and no main-storage obligation.
The unique main-thread allocation atomically binds both. Process-terminal branch 4
requires every owned thread terminal or retired. Inherited branch 3 copies raw,
status and signal from the retained process tuple while retaining branch value 3.

CAPTURE_END emits even when closure fails. LAUNCHER_LOSS and TEARDOWN_FAIL emit and
latch incomplete. EOF without CAPTURE_END changes only the last literal control to
ended false/incomplete true; models must buffer bounded rows rather than synthesize
an extra operation. Empty operations are a schema failure.

Fault seeds are `NONE`, `ATTEMPTS_MAX`, `LOST_MAX`, and `RESERVATION_ONE`.
Non-NONE starts incomplete. Attempt-counter overflow retains attempts at u64 max,
sets lost to u64 max and overflow, and retains no event. Lost-counter overflow at
capacity zero retains lost at u64 max and sets overflow. A retained reservation
prevents complete capture.

## Literal-pool rules

A pool reference has only `{"pool":name,"args":[literal-or-pool-reference...]}`.
Pool bodies may contain positional argument placeholders. Expansion performs
acyclic literal substitution and fixed concatenation only: no arithmetic,
conditionals, transition logic, prior-state access, defaults, ID renumbering,
model-output reads or input-to-expected imports. Depth is bounded to 32 and expanded
data to 2 MiB. Input and expected documents duplicate their own literal identities.

The canonical baseline uses process key `[1,0,1,1,1,0,1]`, main-thread key
`[1,0,1,1,1,1,1]`, secondary-thread key `[1,0,1,1,1,2,1]`, PID 100 and TIDs
200/201. It retains the exact 16-operation complete sequence from process/main
allocation through birth/runnable, thread and process status 37, reference drops,
thread retirement, VM/main-storage release, process retirement and capture end.
Each prefix has an independently specified full process/thread state, event and
control literal.

Separate complete literal sequences cover preparation abort with unassigned TID,
assigned-TID abort, late-clone abort, two competing group-terminal orderings,
inherited status, active-TID rejection, retired non-main TID reuse, multithread
thread-only exit and last-thread-with-live-sibling rejection. Ownership sequences
cover retained thread/process references, permanently revoked unpublished authority,
reference resurrection rejection, zombie before/after parent reap, main-storage,
VM and live-sibling blockers, launcher loss and teardown failure.

Loss/control sequences cover capacity-zero cleanup with exact growing loss counts,
attempt/lost u64 overflow, retained reservation and missing end. Capacity sequences
cover two applications, four processes, eight threads and 128 operations, with the
next literal allocation/operation rejected before transitions.

Identity negatives independently replace capture, OS generation, application,
process, exec or subject domain. Numeric/schema negatives include zero/too-wide/
negative/boolean PID, too-wide TID, zero/gapped/fractional operation ID, zero or
overflowed instance, short/long row, unused argument, unexpected parent, unknown
operation, invalid main flag, raw/signal overflow, duplicate/unknown top-level keys,
trailing object, boolean/oversized capacity, unknown seed, empty operations,
nonfinite number, missing thread parent, wrong subject kind and a document exceeding
1,048,576 bytes. Raw decoder cases retain their exact bytes separately and expect
exit 2 with empty streams.

Mutant bindings are exact: birth-after-runnable, retained-thread-reference for
early retirement, capacity-zero cleanup for silent loss, and active-TID alias.
Mutants must compile and run, then disagree with or be rejected by unchanged literal
expectations. A compiler failure, crash or missing binary is not a killed mutant.

## Remaining gate

The drafted aliases and templates must be materialized into exact `vectors.json`
and `expected.json` bytes. An independent review must verify expansion cycles,
arity, reference resolution, literal step/event/control completeness and coverage
counts before the remaining attempt-2 model source is reviewed. No expected row may
be recorded from either implementation.
