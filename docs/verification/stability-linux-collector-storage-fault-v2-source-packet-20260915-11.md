# Linux collector storage-fault-v2 source correction packet 11

Status: DRAFT FOR INDEPENDENT PACKET REVIEW ONLY

This narrow additive replacement preserves rejected packets 6 through 10 and
changes only packet 10's owner identity/wait clauses. Every other packet 10
requirement and all earlier accepted authority remain unchanged.

## Non-overlapping identity precedence

The supervisor takes at most two initial observations and classifies in this
strict order:

1. `SPAWN_FAILED` iff process creation raised; there is no PID or observation.
2. `MATCHED` iff exactly two `observed` records have identical positive
   pid/ppid/startticks and ppid equals supervisor PID.
3. `MISMATCH` iff at least one observed record has wrong PPID, or at least two
   observed records conflict in PID, PPID, or startticks.
4. `UNOBSERVED` for every remaining spawned case: zero observed records, or one
   otherwise-valid observed record paired with `missing` or `error`.

The raw zero-to-two observation list is always retained. MATCHED alone populates
positive summary ppid/startticks. MISMATCH and UNOBSERVED retain positive spawned
PID but summary ppid/startticks null; they never invent a birth. This explicitly
covers missing+missing, error+error, missing+error, valid-observed+missing, and
valid-observed+error without overlap.

## Exact owner wait alternatives

- SPAWN_FAILED: `owner_wait_observed=false` and exit code/signal both null.
- Any spawned and reaped owner: `owner_wait_observed=true` and exactly one of a
  nonnegative exact exit code or positive exact signal is nonnull.
- Any spawned but unreaped owner at the supervisor cleanup deadline:
  `owner_wait_observed=false`, exit code/signal both null, status OWNER_ERROR,
  cleanup complete false, and a mandatory exact `wait-timeout` unresolved record
  for the spawned PID. Its startticks is the MATCHED birth or the last independently
  matching observed birth if one was ever established, otherwise null.

COMPLETE still requires MATCHED, observed normal wait exit zero/no signal, exact
OWNER_RESULT PID/birth equality, complete supervisor cleanup, empty unresolved,
and the packet-9 outer raw wait zero. An unreaped record is evidence of bounded
failure, never acceptance.

Source tests retain all packet-10 controls and add exact spawned/unreaped result
and all partial-observation classification combinations. No source, build, root,
native, application, or production gate is released without fresh review.
