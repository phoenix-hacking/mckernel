# Linux collector storage-fault-v2 source correction packet 15

Status: DRAFT FOR INDEPENDENT PACKET REVIEW ONLY

This replaces rejected packet 14, retains its accepted direct-owner signal-error
union unchanged, and closes only the NOT_SPAWNED preflight branch. Packets 1
through 11 and 13 otherwise remain mandatory.

## Retained supervisor signal-error union

For `supervisor_cleanup.unresolved` only, `signal-error` has exactly
`kind,stage,pid,startticks,signal,errno,monotonic_ns,direct`. Direct is an exact
Boolean. Stage is `term|kill`; signal is respectively SIGTERM or SIGKILL; PID,
errno and time are positive exact integers. A direct-owner startticks value is
the latest matching positive birth established before the attempt, or null only
when none was ever established. An adopted signal error has direct false and the
positive birth from two immediately preceding matching observations. Signal
errors are sticky. Packet 8's owner-local union is unchanged.

## Exact preflight clock and flags

The supervisor result additionally contains positive exact
`preflight_started_ns,sentinel_wait_deadline_ns` with the latter exactly the
former plus 5 seconds. The first is sampled before SIGCHLD disposition work.
Successful owner-spawn branches retain packet 10's `started_ns` at owner spawn
and its 220/22/248-second arithmetic; preflight_started_ns is no later than
started_ns and the sentinel wait completes no later than its deadline.

For NOT_SPAWNED only, `started_ns == preflight_started_ns`,
`owner_wait_deadline_ns` is null, cleanup trigger is the actual preflight failure
observation, `supervisor_cleanup_deadline_ns == cleanup_trigger_ns + 22s`, and
`supervisor_deadline_ns == preflight_started_ns + 33s` (5 preflight + 22 cleanup
+ 6 durable publication). Finished is no later than the supervisor deadline.
This branch never invents an owner-spawn time.

The exact flag/stage combinations are:

- `sigchld-default`: sigchld_default false, sentinel_wait_passed false;
- `sentinel-fork` or `sentinel-wait`: sigchld_default true,
  sentinel_wait_passed false;
- successful preflight: both flags true and preflight_failure null.

Any other combination is rejected.

## NOT_SPAWNED identity and sentinel retirement

Packet 14's `preflight_failure` object and NOT_SPAWNED state remain. NOT_SPAWNED
has null owner pid/ppid/startticks/spawn_error, exact empty
`owner_identity_observations`, owner_wait_observed false, null owner exit/signal,
status OWNER_ERROR and nonzero outer supervisor wait. SPAWN_FAILED remains only
for a later owner-fork exception after successful preflight.

For `sigchld-default` and `sentinel-fork`, no sentinel exists. Supervisor cleanup
contains exact complete true, empty unresolved, two empty owned scans and actual
ECHILD before publication. For `sentinel-wait`, the successfully forked sentinel
is a direct child but is not assumed reaped. The supervisor first retains every
actual wait result. If still unreaped, TERM or KILL requires two immediately
preceding matching positive PID/PPID/startticks observations; null-birth direct
signaling is forbidden for this failed-preflight sentinel. It then requires the
exact direct wait, two empty scans and actual ECHILD within the trigger-relative
22-second deadline. Missing/mismatched identity, signal failure, timeout or an
unreaped sentinel remains sticky unresolved, cleanup incomplete and nonzero; the
supervisor never fabricates safe retirement.

Source controls independently mutate every flag/stage pair, preflight/start and
5/22/33-second arithmetic, nullable owner deadline, empty owner observation/wait
fields, no-sentinel terminal cleanup, and matched/unmatched/unreaped sentinel
cleanup. Packet 14's direct null/positive owner and positive adopted signal-error
controls remain mandatory.

No source, build, root, native, application or production gate is released until
fresh independent review of this exact packet hash.
