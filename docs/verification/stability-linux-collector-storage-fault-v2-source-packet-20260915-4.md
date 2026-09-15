# Linux collector storage-fault v2 source packet 4

Date: 2026-09-15
Task: `M02-B-storage-fault-v2-source`
Disposition: `SOURCE_PACKET_CLEANUP_EVIDENCE_DRAFT_ONLY`

This additive correction supersedes only the outer-owner cleanup event union in
packet 2 SHA256
`0feaad14f408acf806fb391195e519a16de60cc41ffdb24cd9721ea432b90089`.
Packets 1 through 3 otherwise remain effective. No execution is authorized.

Add two exact cleanup event variants:

- owned scan: `{kind="owned-scan",monotonic_ns:int,pids:[identity...]}` where
  each identity has exactly positive integer `pid,ppid,startticks`, PPID equals
  the owner and two consecutive `/proc/<pid>/stat` reads agree before inclusion;
- empty wait set: `{kind="echild",monotonic_ns:int,return=-1,errno=ECHILD}` from
  an actual nonblocking `waitpid(-1, WNOHANG)` after the terminal owned scan.

After the direct collector is reaped, the owner repeatedly reaps available
children, performs a fresh double-identity owned scan, safely signals verified
remaining children within the existing deadline, and repeats. Killing or reaping
one adopted process always triggers another scan because a descendant can be
reparented afterward. Cleanup `complete=true` requires, in order, a terminal
owned-scan with an empty `pids` array and the actual ECHILD event, with no later
owned identity, signal, wait or unresolved record. Deadline exhaustion,
nonempty terminal scan, waitpid returning zero, identity mismatch or any
unresolved process makes complete false. The oracle enforces this terminal
sequence and rejects fabricated, stale, omitted or reordered scan/ECHILD proof.
