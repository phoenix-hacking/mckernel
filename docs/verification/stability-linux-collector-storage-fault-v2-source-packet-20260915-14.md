# Linux collector storage-fault-v2 source correction packet 14

Status: DRAFT FOR INDEPENDENT PACKET REVIEW ONLY

This replaces no accepted behavior. It carries packets 1 through 11 and 13 and
changes only two supervisor failure-schema gaps discovered before implementation.

## Direct-owner signal-error birth

For `supervisor_cleanup.unresolved` only, `signal-error` has exactly
`kind,stage,pid,startticks,signal,errno,monotonic_ns,direct`. `direct` is an exact
Boolean. Stage is `term|kill`; signal is respectively SIGTERM or SIGKILL; PID,
errno and time are positive exact integers. For `direct:true`, startticks is the
latest matching positive birth established before the signal attempt, or null
only when no matching birth was ever established. For `direct:false`, the target
is adopted and startticks is always the positive birth from the two immediately
preceding matching observations. An ESRCH, EPERM or other signal failure is
always retained; it is never silently treated as successful retirement.

Packet 8's owner-local signal-error schema remains unchanged. Packet 13's normal
supervisor signal events retain their exact direct-child Boolean and the same
birth rule. The oracle rejects null adopted births and any null direct birth when
earlier matching observations exist.

## Supervisor preflight failure

`supervisor-result.json` adds exact `preflight_failure`, null after successful
preflight or an object with exactly `stage,type,message,errno`. Stage is one of
`sigchld-default|sentinel-fork|sentinel-wait`; type/message use packet 8's exact
normalization and errno is a positive exact integer or null. Packet 11's
`owner_identity.state` adds `NOT_SPAWNED`, which has null pid/ppid/startticks and
null spawn_error and is legal only when preflight_failure is nonnull. Conversely,
non-null preflight_failure requires NOT_SPAWNED, owner_wait_observed false, null
owner exit/signal, status OWNER_ERROR and nonzero outer supervisor wait.

The single-threaded supervisor sets SIGCHLD to SIG_DFL, confirms it, and performs
packet 13's exclusive sentinel fork/wait before attempting the owner fork. A
failure at any preflight stage creates no owner. When the canonical fresh attempt
root can be established, the supervisor durably publishes this exact OWNER_ERROR
result and its own bounded captures; persistence failure unlinks an unconfirmed
final and exits nonzero. `SPAWN_FAILED` remains reserved exactly for an exception
from the later owner process creation and retains packet 11's spawn_error object.
COMPLETE requires null preflight_failure, `sigchld_default:true`,
`sentinel_wait_passed:true`, MATCHED owner identity and every earlier completion
condition.

Source controls cover SIGCHLD confirmation failure, sentinel fork failure,
sentinel auto-reap/ECHILD, wrong sentinel PID/status, transition to owner
SPAWN_FAILED only after successful sentinel preflight, direct ESRCH with null and
positive births, direct EPERM with null birth, and adopted signal-error requiring
positive birth/direct false. No control launches the collector or payload.

No source, build, root, native, application or production gate is released until
fresh independent review of this exact packet hash.
