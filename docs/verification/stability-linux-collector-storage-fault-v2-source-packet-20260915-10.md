# Linux collector storage-fault-v2 source correction packet 10

Status: DRAFT FOR INDEPENDENT PACKET REVIEW ONLY

This additive replacement preserves rejected packets 6 through 9. Packet 9's
source/write scope, invocation binding, outer wait input and owner exit rule,
packet 8's exact error/result unions, packet 7's runtime layout, and packets 1
through 5 remain mandatory except for the supervisor fields/bounds superseded
below.

## Supervisor ownership and total bound

Before spawn, `supervise.py` sets and confirms itself as a child subreaper. The
owner also retains its own subreaper role. If the owner dies, the supervisor
therefore adopts the collector; after collector death it adopts payload
descendants. The supervisor records owner spawn at `started_ns`, waits/drains
nonblocking stdout/stderr until `owner_wait_deadline_ns = started_ns + 220s`, and
on timeout performs two matching birth/PPID observations before TERM, waits one
second, repeats two observations before KILL, and waits five seconds for direct
reap. It then repeatedly scans every direct child with two matching `/proc` reads,
signals only matched births, reaps all waitable adopted children, and requires
two consecutive empty scans plus actual ECHILD. All retirement is bounded by
`supervisor_cleanup_deadline_ns = cleanup_trigger_ns + 22s` with the same sticky
tagged unresolved union as packet 8. No later observation erases a mismatch.

Pipe reads are interleaved with wait, signal, scan and reap operations and capped
at one MiB each. After the terminal empty/ECHILD proof the supervisor closes its
read descriptors; a descendant cannot extend the cleanup deadline merely by
retaining a writer. Capture/result publication has six additional seconds, so
`supervisor_deadline_ns = started_ns + 248s` (220 owner + 22 cleanup + 6
publication). Every loop and immediately-preceding signal/write/fsync checks the
applicable absolute deadline. Failure to reap the owner or any adopted identity
by cleanup deadline yields `OWNER_ERROR`, sticky unresolved evidence, and
nonzero supervisor exit; it never emits COMPLETE.

`supervisor-result.json` adds exact `owner_wait_deadline_ns,cleanup_trigger_ns,
supervisor_cleanup_deadline_ns,supervisor_deadline_ns,supervisor_cleanup`.
All timestamps are positive exact integers with the arithmetic above.
`supervisor_cleanup` has exactly `complete,events,unresolved`; events use packet
4's exact identity/signal/wait/owned-scan/ECHILD schemas and unresolved uses
packet 8's exact tagged union. COMPLETE requires complete true, empty unresolved,
two terminal empty scans and ECHILD. The oracle checks `finished_ns <=
supervisor_deadline_ns`; the direct outer supervisor wait must still be zero.

## Exact owner identity and wait union

Packet 9's positive `owner_pid,owner_startticks` fields are replaced by exact
`owner_identity` and `owner_identity_observations` plus `owner_wait_observed`.
`owner_identity` has exactly `state,pid,ppid,startticks,spawn_error`:

- `SPAWN_FAILED`: pid/ppid/startticks null; spawn_error has exactly
  `type,message,errno`, where type/message use packet 8 normalization and errno
  is a positive exact integer or null.
- `UNOBSERVED`: positive pid, null ppid/startticks/spawn_error; zero, one or two
  observations never yielded an observed identity before direct wait.
- `MISMATCH`: positive pid, null summary ppid/startticks/spawn_error; two raw
  observations differed in birth or did not both have PPID equal supervisor.
- `MATCHED`: positive pid/ppid/startticks, null spawn_error; exactly two observed
  records agree on all three and ppid equals supervisor PID.

Each `owner_identity_observations` entry has exactly
`observation,pid,ppid,startticks,monotonic_ns`; observation is
`observed|missing|error`, pid/time are positive exact integers, and ppid/startticks
are positive only for observed, otherwise null. COMPLETE requires MATCHED and an
OWNER_RESULT whose `owner.pid/startticks` equal the summary. No unavailable or
mismatched startticks is invented.

`owner_wait_observed` is exact Boolean. Spawn failure requires it false and both
`owner_exit_code/owner_signal` null. Every spawned result requires the supervisor
to reap the owner: wait observed true and exactly one of nonnegative exact exit
code or positive exact signal is nonnull. COMPLETE requires exit code zero and
signal null. An unreaped spawned owner prevents COMPLETE but, when possible, the
supervisor still persists an OWNER_ERROR result before exiting nonzero. The owner
is a direct unreaped child, so its PID cannot be reused before waitpid; TERM/KILL
of that direct PID is permitted even when `/proc` identity was unavailable. The
direct outer supervisor wait is nonzero for every such failure.

## Required controls

Source tests independently cover spawn failure, exit before any identity read,
one observed then missing, two differing births, wrong PPID, matched normal exit,
owner timeout with an adopted collector and grandchild retaining a pipe writer,
and terminal adopted-tree cleanup. They assert exact objects, exact errors,
deadlines, bounded pipe bytes, no invented identity, and nonzero status for every
failure. Packet 9's initial-missing/later-matched wait-timeout controls remain.

No source/build/root/native/application/production gate is released by this
draft. Fresh independent review of its exact hash is mandatory.
