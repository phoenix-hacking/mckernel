# Linux collector storage-fault v2 packet design 1

Date: 2026-09-15
Task: `M02-B-storage-fault-v2-packet-design`
Disposition: `DESIGN_ONLY`

This packet design follows the source failure/context review. It does not release
implementation, build, root execution, application acceptance or production credit.

The source allowlist is the seven files `packet.json`, `prepare.py`, `inject.h`,
`collector.patch`, `oracle.py`, `witness_owner.py`, and `tests.md` beneath the
existing `linux-sealed-v1/storage-fault-v1/` directory, plus
`scripts/tests/test_collector_storage_fault_packet.py`. A new packet must pin the
accepted collector hash, use a guard exactly equal to one and selectors 0 through
6, and replace only reviewed operation call sites rather than global syscall names.

Using the pinned `stdin-devnull` fixture, expected collector raw waits and original
reports are: control 0/complete `COMPLETED`; first `events.jsonl` create ENOSPC
256/complete `PREPARATION_ERROR`; request artifact seven-byte write then ENOSPC
256/complete `COLLECTOR_ERROR`; first request-artifact report fsync EIO 256/complete
`COLLECTOR_ERROR`; report open ENOSPC 32000/report absent; report-fd fsync EIO after
successful flush 32000/complete report still saying `COMPLETED`; and the combined
write ENOSPC, artifact fsync EIO, report fsync EIO case 32000/complete report whose
original failure remains the write error. Pre-fork selectors require no child,
zero cleanup timestamps and `cleanup_complete=false`; post-fork selectors require
the actual child wait, three EOFs and bounded cleanup.

Counters are per named operation/object and bind retained descriptor identity.
Unselected calls remain unchanged. Seven-byte cases retain exactly the first seven
request bytes and independently computed hash. Each attempted failure is recorded
without changing the collector's first-failure latch; secondary failures remain
additive.

`witness_owner.py` directly owns and waits for the collector, captures PID/startticks
before release, and is the subreaper. It durably creates a witness outside the
collection directory. A bounded private socket carries sequenced BEFORE/AFTER
records with parent durability acknowledgements; the fixture child closes its
endpoint. Disconnect, overflow, timeout or witness storage failure invalidates the
case and invokes bounded identity-safe cleanup while retaining partial evidence.

The journal binds nonce, selector, source/generated/header/ELF hashes, argv,
environment, process identity, operation/object/occurrence, requested/actual bytes,
return/errno, phase, sequence and monotonic time. The parent independently records
raw waits, adopted reaps, ECHILD and final filesystem identities and bytes/absence.
The oracle recomputes hashes and checks identity, order and cleanup; it never accepts
witness booleans as proof.

Independent negatives mutate one valid fixture at a time for selector/wait,
missing/reordered/duplicate seams, identity/ELF/nonce, prefix corruption, fabricated
report or absence, EOF/reap/ECHILD, deadline, first-failure replacement, missing
secondary failure, journal truncation and fsync failure. Cheap tests cover exact
source/diff/header binding, hook sites, fresh-root immutability, complete writes,
fd cleanup and durable Python publication ordering. Independent source review must
precede separate build and root-ownership packets.
