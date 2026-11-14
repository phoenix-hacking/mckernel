# Native collector stream-attribution source review — 2026-09-15

Status: **SOURCE_FINDINGS_ONLY**. General byte attribution remains blocked with
unchanged `mcexec` and current capture interfaces. No ABI freeze or implementation
is authorized.

Payload and launcher share output endpoints. `mcexec_helpers.rs` (SHA256
`3718c537b3912f0a2b7714ad3f6d0e176d1a51fcf8f9fb449515c1f5f2a90ced`)
routes ordinary writes through the generic syscall path; `mcexec.c` (SHA256
`0264d8ad51e00fdaa6348c72db16063f61b4284fe3643b4dae00248727fc0c61`)
executes the requested Linux syscall with unchanged arguments. Payload fds 1/2
therefore name the launcher's descriptor table, where launcher diagnostics also
write. Writer PID/TID alone cannot identify delegated payload bytes.

`scripts/application-tests/supervisor.py` (SHA256
`8b8700175e6673c3a6b652d4a93bd18b56def83dfa3ac4ec821d4ae6c554e873`)
captures stdout/stderr completely per pipe but retains no writer identity, write
boundaries or cross-pipe ordering. Descendants may inherit endpoints; descriptor
duplication, closure and reuse make numeric fd attribution insufficient. Prefix
filtering or inserted markers are unsound because payloads can spoof them and
buffered/concurrent writes can interleave. PTY behavior is not equivalent.

Retained repeat-guest evidence proves only bounded aggregate stdout checks. The
guest-3 console mixes launcher warnings, native traces and HELLO; guest 4 redirects
aggregate stdout and verifies an exact 25-byte HELLO line. Neither supplies a
general writer partition or separately complete payload stderr. Guest-4 archive
SHA256 is
`7387df9ad4319ac2e2cd908bf6bd43901ab105284598f6eb814ecdd0fe3e6192`.

A future reviewed contract must preserve immutable raw streams and use out-of-band
partition rows with stream, checked byte range/hash, typed origin, application and
thread instance, endpoint lifetime, and authoritative raw producer-event links.
Sorted disjoint rows must cover every byte exactly once and reconstruct each raw
artifact. Payload fragments need actual successful-delivery and endpoint evidence;
short writes contribute only committed bytes. Launcher attribution also requires
positive writer evidence. Unknown origin, missing producer completeness, gaps,
overlaps or forged hashes must block acceptance. Per-stream ordering is distinct
from any separately qualified cross-stream clock.

Required negatives include marker spoofing, binary bytes, split/coalesced reads,
partial/EINTR writes, interleaving, fd duplication/reuse, inherited writers,
identity-generation mismatches, gaps/overlaps, truncation and fabricated ordering.
No inspected source-bound producer provides the needed origin/lifetime/ordering
and loss guarantees. No build, runtime or production credit follows.
