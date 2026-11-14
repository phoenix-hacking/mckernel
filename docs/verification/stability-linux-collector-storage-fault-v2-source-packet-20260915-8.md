# Linux collector storage-fault-v2 source correction packet 8

Status: DRAFT FOR INDEPENDENT PACKET REVIEW ONLY

This additive replacement preserves rejected packets 6 and 7 and corrects the
three remaining packet-review gaps. All accepted packet 1 through 5 constraints
and packet 7's exact pre-ACK state, buffered-report identities, runtime inputs,
and layout remain mandatory.

## Observable phase deadlines

The owner records `release_send_start_ns` immediately before calling the bounded
successful RELEASE send. The global collection ceiling is exactly that timestamp
plus 180 seconds: 120 preparation + 10 process + 15 collector cleanup + a bounded
35-second final-storage/witness allowance. The allowance bounds qualification;
it is not a claim that arbitrary ordinary storage completes within 35 seconds.
The first valid post-fork packet receipt narrows the ceiling to the earlier of
global or receipt plus 60 seconds (10 + 15 + the same bounded 35 allowance).
READY remains owner start plus 10 seconds, each send has its own two-second
absolute deadline, later packets never extend a deadline, and owner-triggered
retirement separately retains trigger plus 22 seconds and its 16/1/5 stages.

OWNER_RESULT adds exact `deadlines` with keys `owner_start_ns,ready_deadline_ns,
release_send_start_ns,collection_deadline_ns,first_postfork_receipt_ns,
postfork_deadline_ns,cleanup_trigger_ns,cleanup_deadline_ns`. Every value is a
positive exact integer except the four release/post-fork values may be null when
that phase was never reached. The oracle recomputes all applicable arithmetic
and joins cleanup timestamps.

## Exact cleanup union

Every unresolved object has `kind` plus the exact keys below; no extras:

- identity: `kind,phase,observation,pid,ppid,startticks,matched,monotonic_ns`.
  Observation is `missing|error|observed`; unavailable ppid/startticks are null,
  otherwise positive exact integers; matched is exact Boolean. Phase is one of
  `term-identity-1|term-identity-2|kill-identity-1|kill-identity-2` or
  `owned-scan-N-1|owned-scan-N-2`, with decimal N from 0 through 2047.
- deadline: `kind,stage,monotonic_ns,deadline_ns`; stage is
  `direct-wait|term-pre-signal|kill-pre-signal|owned-scan` and both times are
  positive exact integers with observation at or beyond deadline.
- signal-error: `kind,stage,pid,startticks,signal,errno,monotonic_ns`; stage is
  `term|kill`, PID/startticks/errno are positive exact integers, signal is exactly
  SIGTERM or SIGKILL, and time is positive.
- wait-timeout: `kind,stage,pid,startticks,monotonic_ns,deadline_ns`; stage is
  `direct|term|kill`, PID and times are positive integers, and startticks is null
  only when initial identity was never observed, otherwise positive.
- owned: `kind,phase,pid,ppid,startticks,monotonic_ns`; phase is
  `owned-scan-N` for N 0 through 2047 and all numeric identity/time values are
  positive exact integers.

Entries are append-only. Any mismatch/failure described by packet 7 adds the
corresponding record. Complete cleanup requires the reviewed direct wait,
repeated empty scans, actual ECHILD, and `unresolved:[]`.

## Immutable error/result joins

`owner-errors.jsonl` retains packet 7's exact OWNER_ERROR keys. `stage` is one of
`receive|pre-ack|journal-packet|release|ack|cleanup|capture-fsync|artifact-read|
owner-result-write|journal-result|directory-fsync`; `type` is the exact exception
class name. `message` is `str(error)` when nonempty, otherwise exactly
`<empty-TypeName>`. Nullable packet sequence is an exact nonnegative integer when
available; nullable packet hash is exactly 64 lowercase hex characters when
available. Ordinals start at zero, times strictly increase, and exactly ordinal
zero has primary true.

OWNER_RESULT adds packet 7's `runtime_inputs,secondary_failures` plus positive
exact `result_serialized_ns`. `owner_failure` equals ordinal zero iff its time is
not later than serialization; `secondary_failures` exactly equal all later
OWNER_ERROR objects through that timestamp. Errors after serialization appear
only in the error journal. The oracle validates this exact partition, hashes,
ordering, stages and packet joins.

## Independent supervisor status

A new source-bound `supervise.py` is the parent of the owner process. It records
the owner's actual wait status and is the independent status consumed by the
oracle, so readable bytes never imply successful fsync. Its sole
`supervisor-result.json` object has exactly:
`schema_version,kind,status,owner_exit_code,owner_signal,started_ns,finished_ns,
attempt_root,owner_result_present,owner_result_sha256,witness_present,
witness_sha256,owner_errors_present,owner_errors_sha256`.
Schema is 1, kind is `STORAGE_FAULT_V2_SUPERVISOR`, status is `COMPLETE` only for
normal exit zero after the owner reports every required fsync success; otherwise
`OWNER_ERROR`. Exit code and signal are mutually exclusive nullable exact
nonnegative integers; times are positive and ordered; attempt root is canonical;
presence fields are exact Boolean and hashes are null iff absent, otherwise 64
lowercase hex. The supervisor writes/fsyncs the result and directory, unlinks an
unconfirmed final on any persistence error, and exits nonzero. The outer packet
runner must retain the supervisor's actual wait status; the oracle requires both
that status zero and a `COMPLETE` record before interpreting OWNER_RESULT.

Thus an owner-result, terminal-journal, owner-error-journal, or directory-fsync
failure yields nonzero owner status and independently retained `OWNER_ERROR`; if
that journal also fails, the supervisor still records the nonzero wait. A
supervisor persistence failure yields nonzero supervisor status and no confirmed
final. Preparation failure before journals exist follows the same nonzero owner
wait path. OWNER_RESULT remains serialize-once and terminal equality remains
required when present, but neither is treated as durability proof without the
supervisor result and retained supervisor wait.

## Runtime layout carried forward exactly

Packet 7's three source paths/destinations, copy/fsync/reread order, exact
`runtime_inputs` records, immutable `/work/.../fixture` source binding, initially
absent root-local collection, and exact argv remain unchanged. In particular,
`argv[0] == inputs.elf.path`; the ELF and 27,448-byte payload fixture are distinct.

No source, build, root, native, application, or production gate is released by
this draft. Its exact hash requires fresh independent packet review.
