# Linux collector storage-fault v2 source packet 2

Date: 2026-09-15
Task: `M02-B-storage-fault-v2-source`
Disposition: `SOURCE_PACKET_CORRECTION_DRAFT_ONLY`

This additive correction supersedes only the ambiguous packet schema, ordered
schedule, imported request-acquisition and owner-publication clauses of source
packet 1 at SHA256
`c51fcdb93702bea514b0a70d49c7db75ef236502429e7c0292a5e0e47e9c065c`.
Every input, source allowlist, guard, selector behavior, fault result, cleanup
rule, timeout, preservation requirement and closed execution gate in packet 1
remains unchanged. This draft authorizes no source edit, compiler, build, root,
collector, payload, guest, application or production execution.

## Exact schedules and phases

`X` means adjacent BEFORE then AFTER. `O` is exactly one leader REAP, one EOF
for each of stdout/stderr/setup in any collector-observed permutation, then
CLEANUP_READY and CLEANUP_FINAL. All four REAP/EOF records precede
CLEANUP_READY, which precedes CLEANUP_FINAL. No extra adopted reap is accepted.
BIND follows the corresponding successful create/high-fd operation.

| Selector | Exact schedule after READY | Total packets |
| ---: | --- | ---: |
| 0 | events-create X, events BIND, request-write X, O, request-sync X, report-create X, report BIND, report-flush X, report-sync X | 21 |
| 1 | events-create-fail X, report-create X, report BIND, report-flush X, report-sync X | 10 |
| 2 | events-create X, events BIND, request-write-1 X, request-write-2-fail X, request-sync X, report-create X, report BIND, report-flush X, report-sync X | 17 |
| 3 | events-create X, events BIND, request-write X, O, request-sync-fail X, report-create X, report BIND, report-flush X, report-sync X | 21 |
| 4 | events-create X, events BIND, request-write X, O, request-sync X, report-create-fail X | 16 |
| 5 | events-create X, events BIND, request-write X, O, request-sync X, report-create X, report BIND, report-flush X, report-sync-fail X | 21 |
| 6 | events-create X, events BIND, request-write-1 X, request-write-2-fail X, request-sync-fail X, report-create X, report BIND, report-flush X, report-sync-fail X | 17 |

READY, events create/BIND and request writes are pre-fork. `O` is post-fork.
Request sync, report create/BIND/flush/sync are post-fork for selectors
0/3/4/5 and pre-fork for selectors 1/2/6. Selector 1 has no request sync because
the request fd was never created. Occurrence is one except request-write-2.
The successful ordinary request write returns exactly 406. Injected write 1
requests 406 and actually returns seven; write 2 requests 399 and returns
-1/ENOSPC without an underlying write.

## Exact packet schemas

Reject duplicate keys and require exact key-set equality and exact JSON scalar
types. Every packet has:

```text
schema_version, nonce, selector, sequence, kind, phase, monotonic_ns,
site, object, occurrence, collector_pid, collector_startticks,
source_sha256, generated_sha256, header_sha256, elf_sha256
```

READY uses `site=startup`, `object=collector`, occurrence zero and has no other
keys. Operation records add exactly:

- create BEFORE/AFTER: `dirfd,dir_stat,fd,target_stat,acquisition_id,return,errno_authoritative,errno`;
- write BEFORE: `fd,target_stat,acquisition_id,requested_bytes,return,errno_authoritative,errno`;
- write AFTER: the write-BEFORE keys plus `actual_bytes`;
- sync/flush BEFORE/AFTER: `fd,target_stat,acquisition_id,return,errno_authoritative,errno`;
- BIND: `acquisition_id,old_fd,old_stat,new_fd,new_stat`.

BEFORE has null return, false errno-authoritative and null errno. Create BEFORE
also has null fd/target-stat/acquisition ID. Failed create AFTER has return -1,
null fd/target-stat and null acquisition ID. Other AFTER records have the actual integer return;
negative returns have authoritative positive integer errno, while successful
returns have false/null. Write AFTER actual-bytes is the nonnegative return or
zero for a negative return. `dir_stat`, `target_stat`, `old_stat` and `new_stat`
have exactly integer keys `dev,ino,mode,size`; required live stats are never null.

Observation records add exactly:

- REAP: `pid,startticks,raw_wait_status` with site `reap`, object `leader`;
- EOF: `closed_fd` with site `pump` and object one of `stdout,stderr,setup`;
- CLEANUP_READY: `waitid_return,waitid_errno,leader_reaped,stdout_eof,stderr_eof,setup_eof` with site `cleanup`, object `owned-tree`;
- CLEANUP_FINAL: `cleanup_start_ns,cleanup_deadline_ns,cleanup_finished_ns,cleanup_complete,group_pinned,owned_count,owned_records_omitted,first_failure,first_failure_errno` with site `cleanup`, object `owned-tree`.

All observation occurrences are one except EOF occurrence is its stable stream
ordinal 1/2/3. Inapplicable operation keys are absent from observations.
CLEANUP_READY has waitid-return -1, waitid-errno integer ECHILD and all four
leader/EOF Booleans true.

## Acquisition rule

Successful instrumented create AFTER assigns the next positive acquisition ID.
BIND uses that same ID. Matching old/new device and inode is mandatory. If
`high_fd` returns the same number, the one handle remains live; otherwise BIND
retires the low handle and promotes the relocated one. Numeric reuse is allowed
only after retirement and starts a new positive ID.

The request artifact's production create is deliberately outside the reviewed
hook allowlist. Its retained fd first enters the witness protocol as imported
acquisition ID zero. Every request write/sync record must bind the same fd and
exact fstat fd/dev/ino/mode identity; size is checked separately. Its size
transitions from 0 to 406 for the ordinary write and remains 406 at sync, or
from 0 to 7 after injected write 1, remains 7 after failed write 2 and remains 7
at sync for selectors 2/6. Return, actual-bytes and size deltas must agree.
ID zero is unique to `request.bin`, is already live at its
first record, never appears in BIND, and may not collide with any positive live
acquisition. No new packet is added, so all reviewed counts remain unchanged.

## Durable owner publication

Before fork, the owner exclusively creates stdout and stderr capture files in
the private witness root and redirects only the direct collector child to them.
After collector cleanup it fsyncs both captures, retains their size/SHA256, and
fsyncs the witness directory. It independently retains stable-read size/SHA256
or exact absence for request, report and events artifacts under the exact
collection root supplied in argv.

The collector receives no inherited environment. The owner constructs exactly
`LANG=C`, `LC_ALL=C`, `PATH=/usr/bin:/bin` and the five M02 nonce/source/generated/
header/ELF variables. This is the complete effective collector environment and
is retained exactly; no credential, askpass or unrelated parent variable enters
the child or evidence.

The owner result requires exact top-level keys and values:

```text
schema_version=2, kind=OWNER_RESULT, nonce:string32hex, selector:int0..6,
argv:[string...], environment:{string:string...},
collector:{pid:int>0,identity_observed:bool,ppid:int|null,startticks:int|null,
           reaped:bool,raw_wait_status:int|null},
packet_count:int, hashes:{source_sha256,generated_sha256,header_sha256,elf_sha256},
captures:{stdout,stderr}, artifacts:{events,request,report},
owner_failure:null|{type:string,message:string},
cleanup:{complete:bool,trigger_kind:string,trigger_ns:int,
         cleanup_start_ns:int,cleanup_deadline_ns:int,cleanup_finished_ns:int,
         events:[cleanup-event...],adopted_reaps:[wait-event...],
         unresolved:[identity-record...]},
backend_enabled=false, application_acceptance=false
```

Each capture has exact keys `path,present,size,sha256`; path is `stdout.bin` or
`stderr.bin`, present is true, size is a nonnegative integer and SHA256 is
lowercase hex. Each artifact has the same exact keys; path is the canonical
absolute `events.jsonl`, `request.bin` or `report.json` below the argv collection
root. Present artifacts have nonnegative size and lowercase SHA256; absent ones
have null size/SHA256. Absence must match the selector contract. The hash object
contains exactly four lowercase SHA256 values. Environment is exactly the eight
entries above (the five M02 names include nonce plus four hashes), and argv is
byte-for-byte the exec argv represented as JSON strings.

Cleanup events are exact tagged unions: identity record
`{kind=identity,phase:string,observation=observed|missing|error,pid:int,
ppid:int|null,startticks:int|null,matched:bool,monotonic_ns:int}`;
signal record `{kind=signal,pid:int,startticks:int,signal:int,monotonic_ns:int}`;
wait record `{kind=wait,pid:int,startticks:int|null,raw_wait_status:int,
direct:bool,monotonic_ns:int}`. Adopted
reaps contain only wait records with direct false. Unresolved entries contain
only the last identity record for that PID. Any unknown/missing/extra key rejects.
When collector identity-observed is true, PPID equals the owner and startticks is
positive; when false, both are null. Raw wait is an integer exactly when reaped
is true and null otherwise. Observed identity records have positive PPID/
startticks; missing/error records have both null and matched false. Signals are
permitted only after two consecutive observed matching identity records and use
their exact startticks. A wait may use null startticks only when no identity was
ever observed; it never fabricates identity.

Cleanup trigger-kind is exactly `normal-eof` or `owner-failure`. All monotonic
fields are positive integers. Cleanup start is at or after trigger, deadline is
exactly trigger plus 22,000,000,000 ns, and finish is at or after start and no
later than deadline for a complete result. The direct collector receives up to
16 seconds from cleanup start before the first SIGTERM. SIGKILL, if needed,
follows at least one second after SIGTERM; final wait/reap completes within the
remaining deadline, bounded by five seconds after SIGKILL. Event timestamps are
nondecreasing, fall within start/deadline, and independently prove those stages.
An unresolved collector or adopted child makes complete false and is represented
without invented wait or identity fields.

The result is serialized once. The owner complete-writes and fsyncs `owner-result.json`, fsyncs
the witness directory, appends the byte-identical parsed object as terminal
OWNER_RESULT to the already durable journal, fsyncs again, then closes it.
That terminal journal line has exactly keys `packet,receipt_monotonic_ns`, the
packet is structurally equal to the parsed owner-result object, and receipt time
is a positive integer greater than every earlier receipt. Publication failure
preserves partial evidence and makes the case invalid.

The oracle stable-reads and rehashes retained generated source, header, ELF,
stdout/stderr, request/report/events bytes. It joins the direct collector
identity, nonce, selector, exact schedule/phase, acquisition lifetime, receipt
order, waits, cleanup observations and original report semantics. Handwritten
summaries or hash strings without retained bytes cannot satisfy a positive.

Source tests must build each positive from the exact schedule above, not
`site-N` placeholders, and use exact exception class/message assertions. The
negative matrix must cover every required ownership, durability, acquisition,
identity, schedule, secondary-failure and retained-byte join from packet 1.
Passing source tests grants no runtime or production credit.
