# Linux collector storage-fault v2 source packet 1

Date: 2026-09-15
Task: `M02-B-storage-fault-v2-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

This packet freezes a new producer/oracle source correction after the rejected
storage-fault-v1 attempts. It authorizes neither a collector build nor root,
payload, guest, application or production execution. Source review must pass
before separate build and root-ownership release packets may be drafted.

## Immutable inputs and preserved failures

Bind the v2 design at SHA256
`e39f5ca1ea62251cb1a8a8d56c0d1a48702e35d66c6210d6f4cb76a129b183fa`,
the rejected-source context review at
`01863d1962438a3d9b6c93ce725e42bc1cdd6f71fae29fddde68827f82e29080`,
and `linux-sealed-v1/collector.c` at
`09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f`.

Preserve original failure records 1 and 2 at SHA256
`c1910a35ee3249a21080162578048f66d23a987a9cbfc15f28e5cd85ee3d6adf`
and `a13155586476421f9ed09d20ccb7c0ba8e77ccee86e45569824eda834eb50a99`;
their archives are
`c4a1980cc53c9ef9387a7bc8eb1de8af9b24ebfad928f4ca935190a1dffe46fd`
and `1f4ee927970dcddd2eb45bb11098357f35247b730dafee52c406ffd555a8e3c4`.
Attempt 1 lacks its original failing test stream. Attempt 2 retains all three
source failures. Neither attempt executed an injected collector, and neither may
be promoted or overwritten.

Consume only the retained dependency identities, not their acceptance scope:

- root-success record
  `668fa2e2e7ea0321d0d31ce9b15c343ba95385e47619c76f635b5732b7bf19b6`,
  archive `ad7c670311f6756cf64610e1d3e0dbdcdb026f86857c8461c3295cc34c17a721`;
- adverse-success record
  `ce70c46fe21d9cdc11b59320807f8c05f07a7b28021f2b5d48725a7a85cade36`,
  archive `84d49c9395090531e0ac4e9823cfb8e910dcffb38c5e11152108b893401138f0`.

The exact retained root `stdin-devnull` inputs are request 406 bytes/SHA256
`e81b38bbe6116bf1df2807fa968e12dccfd28fe8c3ad225c45f282b36cab6716`,
selected-inputs 76 bytes/SHA256
`6b8761a9d2094147f02b9fe2a4c709246905a04c5122d68f6b9951162e01317d`
and fixture 27,448 bytes/SHA256
`9ad70dd23d699e72ad805f59446aec371c4e80b955056b845af921b4ce51f725`.
They establish source provenance only. Any fresh pathname, attempt-ID, nonce or
request adaptation remains a separately reviewed runtime input derivation.

## Exact source allowlist

Allow changes only to these files under
`scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/`:

```text
packet.json
prepare.py
inject.h
collector.patch
oracle.py
witness_owner.py
tests.md
```

and `scripts/tests/test_collector_storage_fault_packet.py`. The missing
`witness_owner.py` may be created. Preserve all rejected v1 file identities in
the failure archives; do not edit `collector.c` itself. The new packet kind and
every source/result record must say v2 and keep `backend_enabled=false` and
`application_acceptance=false`.

## Exact seams and local adapters

The generated source includes `inject.h` exactly once under guard
`M02_STORAGE_FAULT_TEST_ONLY == 1` and accepts selector integers 0 through 6
only. Replace only these unique source anchors; bind the full generated diff:

| Site | Exact production anchor | Object/occurrence |
| --- | --- | --- |
| artifact create | `new_sink`: `openat(attempt_fd, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600)` | `events.jsonl`, create 1 |
| artifact write | `retain`: `write(s->fd, bytes + done, keep - done)` | `request.bin`, writes 1 and 2 |
| artifact sync | first loop entry in `report`: `fsync(all[i]->fd)` | `request.bin`, artifact-sync 1 |
| report create | `report`: inner `openat(attempt_fd, "report.json", ...)` before `high_fd` | `report.json`, create 1 |
| report flush | `report`: `fflush(f) == 0 && !ferror(f)` | `report.json`, flush 1; observe only |
| report sync | final `fsync(fd)` in the same short-circuit expression | `report.json`, report-sync 1 |

Do not hook `write_fd`, pathname opens, `make_attempt` parent sync, `fclose`, the
attempt-directory sync, or global syscall names. Use explicit local adapters
equivalent to:

```c
int sf_open(site_id, object_id, int dirfd, const char *, int flags, mode_t);
ssize_t sf_write(object_id, int fd, const void *, size_t);
int sf_sync(site_id, object_id, int fd);
int sf_flush(int report_fd, FILE *);
```

The generated replacements first test exact object identity and call these
adapters only for `events.jsonl` create, `request_artifact` writes/first artifact
sync, and `report.json` create/flush/sync. Every other object bypasses them and
calls the original operation directly. Object classification uses the actual
static sink address where one exists; create BEFORE binds the attempt-directory
fd and fstat plus the constant object identifier. Create AFTER binds the returned
unrelocated fd/fstat or null on failure. A separate one-way `BIND` record after
the existing `high_fd` call binds the retained fd/fstat and proves the same
device/inode as the successful create. Report create is split into the same
inner-open then unchanged `high_fd` sequence for this purpose.

Counters are separate per site/object and count every selected adapter entry,
including failures and EINTR. Unselected operations run exactly once with
unchanged arguments, return handling, short-circuit order and ownership.
Adapters never call `fail`, change collector counters/hash state, or fabricate
an underlying result. Preserve the underlying return and saved errno across
witness traffic; errno after success is non-authoritative.
Immediately after each selected adapter or observation returns, the generated
call site checks `sf_transport_failed()` exactly once and, if set, invokes
`fail("COLLECTOR_ERROR", "test-witness", EIO)` outside the adapter before it
evaluates the production return. Existing first-failure semantics still apply.

In addition to operation seams, permit only these collector-observation anchors:

- the `reap()` success path immediately after `p->raw_wait` and `p->reaped` are
  assigned, emitting one `REAP` record with retained PID/startticks/raw wait;
- the `pump()` zero-read path immediately after each exact stream sets EOF and
  closes its read fd, emitting one `EOF` record for stdout, stderr or setup;
- the `cleanup()` complete predicate, emitting one `CLEANUP_READY` record with
  the contemporaneous ECHILD result, leader state and all EOF states;
- immediately after `cleanup_finished` and final cleanup status are decided,
  emitting one `CLEANUP_FINAL` record with all three timestamps, deadline,
  completeness, group/owner counts and first failure.

These are one-way observation records with durable acknowledgements, not syscall
adapters or collector events. They neither replace `waitpid`, `read`, close,
`waitid`, cleanup state nor reporting. Selector 4's child wait, EOFs, ECHILD and
cleanup proof comes from these exact collector-originated records joined to the
outer parent's collector wait; the outer parent never claims to have observed an
internal child it did not reap.

## Seven exact selectors

The selected request write is larger than seven bytes. The real first write must
return exactly seven; otherwise the case is invalid rather than fabricated. The
retained seven bytes are hex `41435251303030`, SHA256
`793665677edfa8c879c38d37c8c5300c54ff78e980eae26a96913d7aab9d8d91`.

| Selector | Injected behavior | Phase | Collector raw wait | Original report contract |
| ---: | --- | --- | ---: | --- |
| 0 | none | post-fork | 0 | complete `COMPLETED`, `none/0` |
| 1 | events create 1: no open, `-1/ENOSPC` | pre-fork | 256 | complete `PREPARATION_ERROR`, `artifact-create/28` |
| 2 | request write 1: real seven bytes; write 2: no write, `-1/ENOSPC` | pre-fork | 256 | complete `COLLECTOR_ERROR`, `artifact-write/28` |
| 3 | request artifact-sync 1: no sync, `-1/EIO` | post-fork | 256 | complete `COLLECTOR_ERROR`, `artifact-fsync/5` |
| 4 | report create 1: no open, `-1/ENOSPC` | post-fork | 32000 | report absent; no report status |
| 5 | report-sync 1: no sync, `-1/EIO`, after real successful flush | post-fork | 32000 | complete readable bytes still `COMPLETED`, `none/0` |
| 6 | selector 2 write sequence, selector 3 sync failure, selector 5 report-sync failure | pre-fork | 32000 | complete `COLLECTOR_ERROR`, first `artifact-write/28`; both EIOs separately witnessed |

Pre-fork selectors 1, 2 and 6 require `linux_child:null`, no child wait, zero
cleanup timestamps, `cleanup_complete=false` and all EOF flags false. Post-fork
selectors 0, 3, 4 and 5 require child raw wait zero, the actual direct/adopted
wait records, three EOFs, ECHILD and cleanup within the unchanged 15-second
deadline. Selector 4 must prove those facts from parent evidence, never from its
absent report. Artifact sync precedes report creation. Secondary preparation or
report failures never replace `fail()`'s first-failure latch. Complete serialized
report bytes do not establish durable report success.

## Parent-owned durable witness protocol

`witness_owner.py` is the direct collector parent and subreaper. It creates a
private `AF_UNIX/SOCK_SEQPACKET|SOCK_CLOEXEC` pair before `fork`. In the direct
collector child it `dup2`s the endpoint to fixed descriptor 198, verifies
`FD_CLOEXEC` is clear only on 198, closes every other inherited endpoint and
execs the collector. The parent closes the child endpoint. Generated collector
code validates descriptor 198 as a socket and closes it in the fixture child
before that child execs. No filesystem socket pathname is used.

Before any selected collector operation, the collector emits `READY` containing
its PID/startticks and blocks for release. The owner independently reads the same
`/proc/<pid>/stat`, requires matching PID/startticks/PPID, durably records READY,
then replies `RELEASE <nonce>\n`. Missing or mismatched identity never releases
the collector. READY is sequence zero. The collector consumes exactly one RELEASE,
requires its nonce and terminal LF, rejects any ACK or extra queued packet, then
starts ordinary records at sequence one. This startup exchange is anchored
exactly once after argument validation and before `make_attempt`; its exact
generated diff is source-bound.

Each selected syscall adapter sends exactly two compact UTF-8 JSON packets,
`BEFORE` then `AFTER`. `BIND`, `REAP`, `EOF`, `CLEANUP_READY` and `CLEANUP_FINAL`
are single observation packets. Every packet is at most 4096 bytes and has schema
version 2, a 128-bit lowercase hex nonce, selector, strictly increasing sequence,
phase, monotonic-ns, site, object, occurrence, collector PID/startticks and the
source/generated/header/ELF SHA256 values.

BEFORE has `return:null`, `errno_authoritative:false`, `errno:null`. For create it
has `fd:null`, `target_stat:null`, and the attempt dirfd/stat. For write/sync/flush
it has the currently retained fd/fstat; only write also has requested bytes. AFTER has the
actual return, `errno_authoritative:true` and exact errno only for a negative
return, otherwise false/null. Successful create AFTER has the opened fd/fstat;
failed create retains fd/stat null. Write AFTER has requested and actual bytes;
sync/flush AFTER has exact return. Every successful create receives a monotonic
per-site/object acquisition ID. Its AFTER preserves the low fd/fstat even after
`high_fd` closes that descriptor. `BIND` references the same acquisition ID and
has old/new fd numbers plus the preserved/new fstats. A successful BIND retires
the low-fd acquisition and keeps the relocated acquisition live until production
close. Later numeric reuse of a retired descriptor is valid and starts a new
acquisition ID; collision with a still-live acquisition or incorrect relocation
identity invalidates the case. Observation-only fields not applicable to their
kind are absent, never invented null aliases.

Only exact target objects enter adapters. The expected upper bound is 23 packets:
READY, at most fourteen BEFORE/AFTER operation packets (events create, up to two
request writes, request sync, report create, flush and sync), at most two BINDs,
one REAP, three EOFs, CLEANUP_READY and CLEANUP_FINAL. Pre-fork cases omit child
observations. The hard bound is 32 packets; a 33rd invalidates the case. Missing,
duplicate, reordered, truncated, oversized or additional packets invalidate it.

After each non-READY packet, the parent appends the packet plus its own receipt monotonic
time to an exclusive `witness.jsonl` outside the collection directory, performs
a complete-write loop, fsyncs the file and its parent directory, and replies with
the exact ASCII packet `ACK <nonce> <sequence>\n`. The adapter waits at most two
seconds by monotonic deadline for the matching acknowledgement. READY is appended
and fsynced by the same durable path, but its sole acknowledgement is the one
RELEASE already specified; no ACK is sent or consumed. The owner applies
a ten-second pre-release/witness-I/O deadline; once the collector creates a
fixture child, its existing process and 15-second cleanup deadlines remain
authoritative. Disconnect, acknowledgement mismatch, overflow, timeout, witness
write/sync failure or owner identity loss invalidates the case. Generated code
latches a transport fault at the next explicit phase boundary, calls the
collector's existing `fail` once outside the adapters and enters its normal
cleanup path when a child exists.

The outer cleanup deadline is 22 seconds after transport invalidation. The owner
first closes its endpoint and allows 16 seconds for collector-owned cleanup and
exit. It uses only nonblocking `waitpid` on its exact unreaped direct collector.
If still live, it rereads PID/startticks/PPID and sends SIGTERM only on an exact
match, waits one second, revalidates, then sends SIGKILL only on an exact match
and waits/reaps for at most five more seconds. It signals no process group. Any
adopted child is recorded and signalled only after two matching `/proc` identity
reads with PPID equal to the owner; otherwise it is retained as an unresolved
cleanup failure. Missing or mismatched identity never authorizes a signal. All
waits, signals, identities and terminal unresolved owners are durably recorded
while preserving partial witness bytes and the first owner failure. A witness
Boolean is never acceptance evidence.

The parent independently retains its collector raw wait, stdout/stderr bytes,
adopted reaps, final tree identities and exact report/artifact bytes or absence.
It separately retains and labels collector-originated child waits, ECHILD, EOF
and cleanup packets; these never masquerade as parent observations. It fsyncs its
result and parent directory before publishing a completion record. The oracle
recomputes all hashes and joins nonce, selector,
source/generated/header/ELF identities, argv/environment, process identity,
operation/object/occurrence, request/actual bytes, return/errno, phase, sequence,
monotonic order, waits, reaps, EOFs, cleanup and filesystem results.

For the pinned 406-byte request, normal request retention is exactly one write;
any additional normal short write invalidates the case. The exact accepted packet
counts, including READY and BIND/collector observations, are selectors
`0:21, 1:10, 2:17, 3:21, 4:16, 5:21, 6:17`. Tests derive these independently from
the named schedules and require every count below 32; they do not merely trust a
reported total.

## Source checks and negative oracle matrix

Cheap source tests must prove exact original/header/generated/diff hashes; unique
include and hook sites; guard exactly one; selectors exactly 0–6; no forbidden
global wrapping; exact target-only branching and per-selector packet schedules
below the independently recomputed 32-packet limit; unchanged unselected calls;
complete-write/fd cleanup; stable
fresh-root rejection that leaves the old tree byte-identical; and durable Python
publication order. Every negative starts from its own freshly copied valid
fixture and changes exactly one field to a distinct invalid value.

The negative matrix covers selector/wait, missing/reordered/duplicate seams,
site/object/occurrence, PID/startticks/ELF/source/header/generated identity, nonce,
seven-byte prefix/hash, fabricated report or absence, report durability claims,
EOF/reap/ECHILD, cleanup deadline, first-failure replacement, omitted secondary
failure, journal truncation/extra/oversize and witness file/parent sync failure.
Require the exact stable exception class/message for each source and oracle
rejection. Mock all compiler, build, root, collector and payload execution and
assert zero calls and no output outside fresh temporary roots.

Run only the new storage-fault-v2 source class under pinned Python 3.9.12 and
3.8.10. The source evidence packet must bind all current/replacement file hashes,
both original failures, exact interpreter commands and outputs, and every false
gate. Passing source tests is not build, root ownership, collector behavior,
storage-fault, application or production acceptance.
