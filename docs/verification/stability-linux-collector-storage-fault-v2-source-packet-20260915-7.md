# Linux collector storage-fault-v2 source correction packet 7

Status: DRAFT FOR INDEPENDENT PACKET REVIEW ONLY

This additive replacement corrects rejected packet 6. It does not release
compilation or execution and does not weaken accepted packets 1 through 5.

## Exact pre-ACK state

Before durable witness publication and ACK, the owner validates exact JSON types
(Boolean is never integer), per-kind fields/nullability, selector, sequence,
phase, site/object/occurrence, result/errno, and stat/descriptor/acquisition/byte
semantics. State consists of optional exact tuples
`(fd,dev,ino,mode,acquisition_id,size)`. Create AFTER establishes an events or
report tuple; BIND must match its old tuple and replaces only fd/size with the
same dev/ino/mode/acquisition. Imported request acquisition zero is established
by request-write BEFORE and every request-write/request-sync must match its
fd/dev/ino/mode. Reviewed request sizes are exactly 0 to 406, or 0 to 7 followed
by requested 399 and retained size 7. A rejected packet receives no ACK.

## Independently derived absolute deadlines

- READY: owner start plus 10 seconds.
- Collection global ceiling: RELEASE receipt plus 180 seconds, derived as
  120-second preparation + 10-second process + 15-second collector cleanup +
  35 seconds for final storage/witness traffic.
- First valid post-fork packet: narrow to the earlier of the global ceiling or
  its receipt plus 60 seconds, derived as up to 10 process + 15 cleanup + 35
  final storage/witness seconds. Later packets never extend either ceiling.
- Each RELEASE/ACK send: its own two-second absolute nonblocking deadline.
- Owner-triggered retirement: the already reviewed trigger-relative 22 seconds,
  with 16/1/5 direct-wait/TERM/KILL stage ceilings.

## Buffered report and exact identity joins

Report-flush BEFORE must match report acquisition fd/dev/ino/mode/id and may have
any size from zero through the eventual retained report size. Flush AFTER and
both report-sync packets have that same tuple and the exact full size. Request-
sync likewise matches the imported request fd/dev/ino/mode/id and exact retained
size. No oracle accepts an identity change masked by an equal size.

## Exact error evidence

The fresh root contains `owner-errors.jsonl`. Every line has exactly:
`schema_version,kind,ordinal,primary,stage,type,message,monotonic_ns,packet_sequence,packet_sha256`.
Values are schema 2, kind `OWNER_ERROR`, zero-based strictly increasing integer
ordinal, exact Boolean primary, nonempty string stage/type/message, positive
integer time, and nullable packet sequence/hash. For a decoded rejected packet,
sequence is its claimed exact integer or null and SHA256 is over its canonical
sorted compact JSON bytes; receive/parse failures use both null. The first error
has `primary=true`; all later lines are secondary and false. Each line is fully
written, file-fsynced and root-directory-fsynced before cleanup continues.

OWNER_RESULT supersedes packet 2 only by adding exact keys `runtime_inputs` and
`secondary_failures`. `owner_failure` is null or the exact first OWNER_ERROR
object. `secondary_failures` is the ordered exact list known before the result is
serialized. OWNER_RESULT is serialized once and immutable. A later result-file,
terminal-witness, owner-error-journal, or directory-fsync failure never mutates
it: the owner appends an error line when that destination remains usable and
raises the first exception, chaining every later exception in occurrence order.
If root or initial journal creation fails, all acquired descriptors close and the
original exception is re-raised; no result or success is claimed. If OWNER_RESULT
cannot persist, no terminal witness is emitted. If terminal witness persistence
fails, the already durable result remains but oracle validation fails terminal
equality. Error-journal failure is itself chained even when it cannot self-record.

## Exact sticky cleanup schemas

`cleanup.unresolved` is ordered and permits only these exact tagged objects:

- identity: the existing exact identity observation schema;
- deadline: `kind,stage,monotonic_ns,deadline_ns`;
- signal-error: `kind,pid,startticks,signal,errno,monotonic_ns`;
- wait-timeout: `kind,pid,startticks,stage,monotonic_ns,deadline_ns`;
- owned: `kind,pid,ppid,startticks,phase,monotonic_ns`.

Every missing/failed second identity read, birth mismatch, deadline reached on an
immediate pre-signal recheck, failed signal, wait timeout, or nonempty scan adds
one of these records permanently. `cleanup.complete` is true only after a direct
collector wait, repeated empty double-identity scans, actual ECHILD, and an empty
unresolved list. Later empty observations never remove an entry.

## Exact shared fresh-root layout

The owner receives canonical source paths for `request`, `selected_inputs`, and
`fixture`. They must be regular, no-follow, stable across fstat, and exactly:
406/e81b38..., 76/6b8761..., and 27448/9ad70d... bytes/SHA256. The fixture source
path is exactly `/work/cases/stdin-devnull/inputs/fixture`, matching the immutable
request. After creating the canonical fresh attempt root and both journals, the
owner creates `retained-inputs` mode 0700 and, in request/selected/fixture order,
writes O_EXCL mode-0600 destinations `request.bin`, `selected-inputs.json`, and
`fixture`, fully writes and fsyncs each, rereads/hash-checks each, then fsyncs the
retained directory and root before fork. `runtime_inputs` has exactly those three
keys; each record has exactly `source_path,destination_path,size,sha256` and binds
both canonical paths plus the reviewed size/hash.

The invoked argv is exactly build input `inputs.elf.path`, the fixed mode string,
the retained request destination, retained selected destination, and an initially
absent canonical `collection` child of the same root. Thus `argv[0] ==
inputs.elf.path`; the collector ELF is never confused with the payload fixture.
The oracle derives collection/retained paths only from this OWNER_RESULT and
rejects any external or symlinked layout. Compilation inputs retain packet 3's
four exact records and remain distinct from the three runtime inputs.

No source/build/root/native/application/production gate is released without a
fresh independent PASS of this exact packet and then a fresh full source review.
