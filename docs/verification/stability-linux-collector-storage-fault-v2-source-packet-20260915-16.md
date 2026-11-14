# Linux collector storage-fault-v2 source correction packet 16

Status: DRAFT FOR INDEPENDENT PACKET REVIEW ONLY

This additive packet preserves packets 1 through 11, 13 and 15. It closes only
the six independently reproduced gaps in source-review attempt 12/13. It does
not release compilation, root execution, application acceptance or production
credit.

## Independent supervisor identity authority

The supervisor result adds one positive exact integer `supervisor_pid`. It is
the value returned by the supervisor's single `os.getpid()` observation before
preflight and is immutable for the result. Every MATCHED summary PPID, every
initial observed owner PPID, every later direct-owner matching observation and
every adopted/sentinel parent observation is compared with this field.

The oracle independently recomputes packet 11's classification from the spawned
PID, `supervisor_pid` and the retained initial observations; it never trusts the
summary state. There are zero through two observations only. Their times are
strictly nondecreasing, no earlier than `started_ns`, and no later than
`cleanup_trigger_ns`. MATCHED, MISMATCH and UNOBSERVED are accepted only when the
recomputed state and all summary fields exactly equal the producer result.
NOT_SPAWNED and SPAWN_FAILED retain their existing empty observation rules.

Supervisor cleanup receives `supervisor_pid` directly instead of deriving it
from nullable owner-summary PPID. A sentinel/direct signal or signal-error pair
has the exact `term-identity-{1,2}` or `kill-identity-{1,2}` phases implied by
its signal, identical positive PID, `supervisor_pid` PPID and startticks, and
immediately precedes the attempt. Adopted pairs retain the corresponding exact
owned-scan phase and the same parent/PID/birth equality. Missing/error pairs
remain permitted only for packet 13's never-observed real-owner nullable-birth
case and never authorize the failed-preflight sentinel or an adopted child.

## Truthful cleanup chronology

All cleanup events occur from `cleanup_trigger_ns` through the earlier of the
actual `finished_ns` and the cleanup deadline. Every unresolved observation
time occurs from the trigger through `finished_ns`; no record may be from the
future. `finished_ns` remains bounded by the overall supervisor deadline.

An unresolved `deadline` record has `monotonic_ns >= deadline_ns`. Its
`deadline_ns` equals the supervisor cleanup deadline for `term-pre-signal`,
`kill-pre-signal` and `owned-scan`. An unresolved direct `wait-timeout` uses the
exact owner/sentinel wait deadline; TERM/KILL wait timeouts use a positive stage
deadline no later than the cleanup deadline, after the preceding matching signal
attempt, and no later than their timeout observation. Every timeout PID/birth
joins the direct or adopted identity applicable at that point.

Cleanup COMPLETE requires `finished_ns <= supervisor_cleanup_deadline_ns`, no
unresolved record, the exact direct wait where required, two terminal empty
scans and ECHILD. OWNER_ERROR may truthfully finish after the cleanup deadline
only with a matching deadline/timeout unresolved record and still no later than
the overall supervisor deadline. It must not be rejected merely for observing
the real expiration one or more nanoseconds after the cleanup deadline.

## Later direct-owner birth

Initial MATCHED/UNOBSERVED/MISMATCH classification remains immutable. Cleanup
tracks the latest positive direct-owner birth established by a valid matching
pair. A later direct signal, signal error or wait joins that latest birth; null
is accepted only while no matching pair has ever been established. Terminal
cleanup compares the direct wait with this latest event birth, not the nullable
initial summary. This implements packet 13 without retroactively promoting the
summary classification.

## All post-fork observations and raw waits

Selectors 0, 3, 4 and 5 all require exactly one REAP with a terminal wait status
decoded independently as exit zero/no signal, exactly three EOF observations
with distinct nonnegative descriptors, exactly one CLEANUP_FINAL, and
`cleanup_deadline_ns == cleanup_start_ns + 15 seconds`. The report child wait,
witness REAP and actual-reap event raw values are byte-for-byte equal and each
is decoded independently rather than inferred from the report's asserted wait
object. Pre-fork selectors retain no fabricated post-fork observations.

Every raw wait accepted by the supervisor or collector oracle is an exact
non-Boolean integer in the Linux 16-bit wait-status range and represents a
terminal exited or signaled state; stopped, continued, negative and oversized
values are rejected.

## Independent descriptor bounds

The offline oracle matches the owner ledger. Every present `dirfd`, `fd`,
`old_fd`, `new_fd` and EOF `closed_fd` is an exact non-Boolean nonnegative
integer. Fields that are contractually absent remain null. BIND can relocate to
a retired number but cannot use a negative number or collide with a live
descriptor; old/new descriptor and acquisition ownership remain joined before
the ledger changes.

## Required source controls

Tests retain all prior controls and add, at minimum:

- the identical observed+missing list cannot validate as both MISMATCH and
  UNOBSERVED, conflicting observations classify only as MISMATCH, and a third
  initial observation is rejected;
- sentinel/direct signal and signal-error pairs with differing PPIDs, births,
  PIDs or phases are rejected, including pairs not joined to `supervisor_pid`;
- a future timeout after `finished_ns` is rejected while truthful
  deadline-plus-one OWNER_ERROR evidence within the overall deadline accepts;
- initially UNOBSERVED followed by a valid later matching birth, direct signal
  and wait validates without summary promotion;
- each post-fork selector independently rejects nonzero/nonterminal REAP,
  duplicate EOF and altered 15-second cleanup arithmetic;
- negative and Boolean descriptors are rejected at every schema position, and
  raw wait/result mismatches or nonterminal encodings are rejected.

No source edit or execution is authorized by this draft until an independent
review binds and accepts its exact hash. Fresh full source review remains
mandatory after implementation.
