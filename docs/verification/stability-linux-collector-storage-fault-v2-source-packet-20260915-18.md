# Storage-fault-v2 bounded cleanup closure correction packet 18

Status: `DRAFT_PENDING_INDEPENDENT_REVIEW`

Task: `M02-B-storage-fault-v2-source`

This additive packet corrects three source-level closure gaps reproduced after
packet 17. It changes neither the seven selector schedules nor any collector,
native, application or production acceptance contract. Packet texts 11, 13, 15
and 17 remain required inputs.

## Bound inputs

- `supervise.py` SHA256
  `3a8a643e7e55328ca9d410ccca9433124005ec988186715d306a239bde33015b`
- `oracle.py` SHA256
  `68754c224d13bd059997e2e07e1cddd2200436deaf74d4666403fecb8c270c77`
- failing test SHA256
  `124717e529186d644755692b236a23e1c4e67d3c639c012371c02fab5bde58b5`
- retained failure archive SHA256
  `e9236858a64b8ad610b835b39651f4a02374a4ae17387fb435e2301f3996dbb3`

## Released corrections if this packet passes

1. Reaching the maximum 2,047 identity scans before the fixed cleanup deadline
   must not return from cleanup. It transitions to a no-new-authority bounded
   wait/reap/pipe-progress phase until the required direct wait, two terminal
   empty scans and actual ECHILD are all established, or the actual fixed
   deadline is reached. Direct reap alone never ends continuation; adopted
   children remain outstanding, and ECHILD is irreversible. It emits no phase
   numbered above 2,047, does not signal from stale identity, and never
   fabricates a future timestamp. A direct child still unreaped at its governing
   deadline retains exactly one direct timeout.

2. `COMPLETE` is decided using the published supervisor `finished_ns`, not only
   cleanup's earlier local finish. If publication crosses the cleanup deadline,
   the producer retains the genuine wait/scans/ECHILD, changes
   `cleanup.complete` to false, and appends exactly one unresolved record
   `{kind:"deadline", stage:"publication-finish",
   monotonic_ns:<actual published finished_ns>,
   deadline_ns:<fixed cleanup deadline>}`. This forces `OWNER_ERROR`/125 without
   fabricating a child timeout. The oracle accepts that record only in supervisor
   cleanup, only when the timestamp is the exact published finish at or after
   the exact fixed cleanup deadline, and never with `complete=true`.

3. A failed adopted-child signal can close as bounded unresolved evidence when
   the child is not reaped before the actual cleanup deadline. The join requires:
   the immediately preceding exact positive identity pair under the supervisor;
   a matching earlier `owned` record with the same scan phase, PID, PPID and
   birth; no intervening or prior matching reap/ECHILD; and a later actual
   `deadline(stage=owned-scan)` at the fixed cleanup deadline. This is an
   identity-bound unresolved-expiration join, not retirement. It always forbids
   `complete=true`. A wait after the signal error remains the preferred normal
   join. An unrelated deadline, wrong birth/parent/phase, premature deadline or
   signal error after reap remains invalid.

## Required focused controls

- force scan index 2,046 with time still before deadline and prove bounded
  progress reaches actual deadline and emits the direct timeout;
- prove a direct reap with an outstanding adopted child does not terminate the
  scan-cap continuation, and ECHILD without the required direct wait remains
  incomplete through the actual deadline;
- preserve TERM and KILL stage timeouts plus the distinct final direct timeout;
- cross the cleanup deadline only in the final published-finish sample and prove
  the producer-to-oracle round trip returns 125 while retaining the real wait
  and exact `publication-finish` deadline; reject premature timestamps, future
  timestamps, wrong deadlines and `complete=true` with that record;
- accept one exact adopted signal-error/owned/deadline unresolved record;
- reject wrong birth, parent or phase, deadline before the fixed bound, missing
  owned record, unrelated deadline, and signal error after matching reap/ECHILD;
- rerun the complete source-only suite under Python 3.9.12 and 3.8.10.

## Non-release

Packet review, source tests and source review grant no compilation, root use,
native execution, guest execution, application acceptance or production credit.
Fresh exact-byte full-source review remains mandatory after implementation.
