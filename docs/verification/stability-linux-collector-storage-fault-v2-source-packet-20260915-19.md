# Storage-fault-v2 sentinel chronology and later-birth correction packet 19

Status: `DRAFT_PENDING_INDEPENDENT_REVIEW`

Task: `M02-B-storage-fault-v2-source`

This narrow additive packet addresses the two findings in source review attempt
18. It changes only the representation of a late owner-start failure and the
identity proof joining an earlier null-birth direct timeout to a later
positive-birth direct reap. Packets 11, 13, 15, 17 and 18 remain mandatory;
their inherited requirements remain effective except for the precise
cleanup-event lower-bound exception below. The seven selector schedules,
closed event/unresolved schemas, first-failure preservation and all execution
gates remain unchanged.

## Exact rejected inputs and required contracts

The following are rejected review inputs, not accepted source:

- `scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/supervise.py`:
  `9725513afc2f9b44a5b2fd1fdf925a01d7ef9dcb792f7c9e4e73d414d25eb267`
- `scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/oracle.py`:
  `3de6a00eea3ec798538a4d1aa584f99fe5d67b4f5a2e405395e89f3d2f464f07`
- `scripts/tests/test_collector_storage_fault_packet.py`:
  `d4afcbf009a922b77a8813087d3793e4ae52ab538d1790967ec5b4ca0882734c`
- [Source review failure 14](stability-linux-collector-storage-fault-v2-source-review-failure-20260915-14.json),
  review attempt 18, status `FAIL_SOURCE`:
  `73344a0679005f740beac4ae51f0e38e3a1789eb09ae8a47a2d91b3d3cc10759`
- Its retained review-input archive
  `evidence/stability-linux-collector-storage-fault-v2-source-review-input-20260915-21.tar.gz`:
  `28b1d2c73cb353dd136a8b10ccda018b7739a8e65d4909ebc4cd4fd97418350e`.

Required packet hashes:

- [Packet 11](stability-linux-collector-storage-fault-v2-source-packet-20260915-11.md):
  `274a51378b0172b4728eae3557b1f1b7a1c65708887b7980bfec1b205bc06f1f`
- [Packet 13](stability-linux-collector-storage-fault-v2-source-packet-20260915-13.md):
  `db607e3b89d7cdf0fbca6e69fe8ea29daa07b9c9cd7b55daae2ba4b0b91eee0a`
- [Packet 15](stability-linux-collector-storage-fault-v2-source-packet-20260915-15.md):
  `bb3a662fe4d729da08ea9ff4eaddcba632585565bc92e4547ee4ef83b52ded1a`
- [Packet 17](stability-linux-collector-storage-fault-v2-source-packet-20260915-17.md):
  `39c7b15d712a49f8ea94c8ea2d68e48376bd0deee1dba22897a9b21ca7b353f7`
- [Packet 18](stability-linux-collector-storage-fault-v2-source-packet-20260915-18.md):
  `45dccc23f26a88ceb5462d5f5f7d54865bffe1858988eb55cbf4a9acc12d60d5`.

## Actual late owner-start trigger and retained earlier sentinel wait

After successful sentinel validation, the producer samples the clock before
owner creation. If that actual sample exceeds the fixed
`sentinel_wait_deadline_ns`, owner creation is forbidden. Preserve that sample
as a separate internal `trigger_ns` on the failure path and serialize its exact
value as the existing `cleanup_trigger_ns`. Do not substitute the earlier
sentinel wait timestamp or a later resample. This adds no result-schema field.

The failure retains the exact existing preflight object:
`stage="sentinel-wait", type="TimeoutError", message="owner start deadline",
errno=null`. The result remains `NOT_SPAWNED`, `sigchld_default=true`,
`sentinel_wait_passed=false`, with no owner PID, observations or wait status.
The false sentinel flag denotes failed overall preflight in this existing
branch; the retained sentinel raw wait supplies the successful earlier wait.
`started_ns == preflight_started_ns` remains mandatory: the rejected late sample
is a failure observation, not an owner-spawn timestamp.

The actual successful sentinel wait remains the first retained cleanup event,
unchanged. The producer must retain the wait for its same directly forked
sentinel PID, with the existing exact wait keys, `direct=true`,
`raw_wait_status=73 << 8` (18688), and `startticks=null`. It must not re-wait or
signal this already-reaped sentinel.

The oracle permits exactly this one pre-trigger cleanup event only when all
of the following hold:

- The result has the exact NOT_SPAWNED failure identity, stage, exception
  type/message/errno, flags and absent-owner fields just specified.
- Event zero is the sole direct wait, has the exact direct-wait shape, a
  positive exact integer PID, null startticks and exact non-Boolean integer raw
  status 18688. Any other direct sentinel evidence must agree with that PID;
  this exception introduces no second sentinel or substitute process identity.
- Its positive exact integer timestamp satisfies
  `preflight_started_ns <= wait.monotonic_ns <= sentinel_wait_deadline_ns
  < cleanup_trigger_ns`. These comparisons use the retained actual times.
- Every other cleanup event still satisfies packet 17's normal lower bound
  `cleanup_trigger_ns`, and every event retains its existing upper bound and
  chronological ordering. No identity, signal, scan, ECHILD, other wait or
  unresolved record receives this exception.

The cleanup deadline is exactly the actual `cleanup_trigger_ns + 22 seconds`.
The fixed five-second sentinel deadline and the existing
`preflight_started_ns + 33 seconds` overall deadline remain unchanged.
Packet 18's truthful publication-finish handling still applies. An elapsed
overall bound cannot be repaired by inventing or backdating timestamps.
Wrong-status sentinel failures and other exception types/messages retain their
ordinary trigger-bounded event rules; they do not acquire this exception.

## Exact later-birth proof for a sticky direct timeout

A `wait-timeout` with `stage="direct"` remains immutable. Its birth is the
latest independently established birth strictly before that timeout, or null
only if none existed. Its governing deadline remains exactly
`min(original_direct_wait_deadline_ns, supervisor_cleanup_deadline_ns)`;
the original deadline is the sentinel deadline for failed preflight and the
owner deadline for the real owner. No later observation rewrites the timeout.

For both a failed-preflight sentinel and a real owner, a null-birth direct
timeout may join a later positive-birth direct wait only if the retained cleanup
events contain an independently valid pair with all of these properties:

- The two records are adjacent in the event array and have the exact identity
  schema, `kind="identity"`, `observation="observed"`, `matched=true`, and
  identical positive exact integer PID, PPID and startticks.
- PID equals both the timeout PID and the direct-wait PID; PPID equals the
  independently recorded `supervisor_pid`; startticks equals the positive
  direct-wait birth.
- Phases are exactly `term-identity-1` followed by `term-identity-2`, or
  `kill-identity-1` followed by `kill-identity-2`. A suffix resemblance, mixed
  stages or an adopted-child scan phase is not direct-child birth authority.
- Both observations occur strictly after the timeout and strictly before the
  direct wait: `timeout.time < first.time <= second.time < wait.time`.
- The pair precedes any matching reap or ECHILD that would end the relevant
  authority. Existing mismatch, signal-authority, event-order and latest-birth
  checks remain mandatory; this pair cannot revive retired authority or
  override a later contradictory identity observation.

The oracle must independently establish this birth at the direct wait's own
timestamp. Null timeout birth is never a wildcard. A pair at or after the wait,
a pair before the timeout, the positive wait value alone, or an initial summary
alone cannot prove this null-to-positive transition. If no such pair exists,
the positive-birth wait fails the join. A valid null-birth timeout followed by a
null-birth direct wait remains subject to the existing same-PID and chronology
checks; it supplies no positive identity evidence.

Preserve exactly-one direct timeout when an applicable direct child remains
unreaped, and at most one sticky prior direct timeout after its actual reap.
TERM and KILL stage timeouts remain separate records with their existing
signal-relative budgets. No-sentinel branches retain zero direct timeouts.
Initial owner classification remains immutable. These rules provide no new
signal authority and change no adopted-child signaling contract.

## Required focused source controls

1. Exercise a successful sentinel reap followed by an actual late owner-start
   clock observation. Prove owner spawn is not called; the failure's trigger
   equals the late sample; the original sentinel wait is unchanged at event
   zero; cleanup uses trigger plus 22 seconds; and the producer/oracle round
   trip retains OWNER_ERROR and status 125 within the unchanged overall bound.
2. Independently reject a wrong exception type, message, stage or errno; wrong
   flags/owner fields; nonterminal or non-18688 raw wait; non-null sentinel
   birth; a producer wait PID differing from its retained fork-owned sentinel
   or an oracle PID inconsistent with other retained direct evidence;
   duplicate/reordered wait; wait before
   preflight or after its fixed deadline; trigger at/before that deadline;
   backdated trigger; altered cleanup arithmetic; and any second pre-trigger
   event or pre-trigger unresolved record. Preserve ordinary wrong-status
   sentinel-failure controls.
3. For sentinel and real-owner paths separately, retain a null direct timeout,
   then an exact positive pair, then a positive direct reap. The unchanged
   timeout plus the independently proven later birth must validate as sticky
   OWNER_ERROR evidence without initial-summary promotion.
4. For each path independently reject a missing pair, one observation only,
   wrong PID, wrong supervisor parent, mismatched birth, missing/error or
   unmatched observation, invalid/mixed/adopted phases, nonadjacent pair,
   pair before/at the timeout, pair at/after the reap, pair after ECHILD,
   intervening retirement, and a positive reap supplied with no birth proof.
   Keep positive-birth timeout equality and null-to-null controls, exact direct
   timeout cardinality, and independently joined TERM/KILL stage timeouts.
5. Preserve every prior failure and run the complete source-only suite under
   Python 3.9.12 and 3.8.10 after the separately reviewed implementation.
   Tests must retain real timestamps and exact objects; fixture arithmetic
   must be corrected rather than weakening the oracle.

## Preservation and non-release

All original packets, rejected sources, captures, reports and failure archives
remain unchanged. This document is a proposed representation/chronology
correction only. Independent review must bind its exact hash before source
implementation under this packet. Fresh exact-byte full-source review remains
mandatory afterward. Packet review or source-test success grants no
compilation, root use, native/guest execution, application acceptance,
production credit or conditional compiler-packet release.
