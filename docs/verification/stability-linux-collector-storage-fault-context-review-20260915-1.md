# Linux collector storage-fault source context review 1

Date: 2026-09-15
Task: `M02-B-storage-fault-v1-context-review`
Reviewed commit: `ac28cafecfbfd5cfd933de3c5d0ec0b5004e1f89`
Disposition: `FAIL_SOURCE`

This is an independent read-only review of the uncommitted storage-fault-v1
source packet and its two retained failures. It releases no source, build, root
execution, application acceptance or production credit.

## Retained test failures

The generated-source marker assertion is a test defect: the selector is spelled
in the included `inject.h`, not necessarily in the generated translation unit.
The test must bind the exact header/include relation and exercise actual seam
selection. Reusing an attempt root currently raises `AssertionError`; a fresh
contract must choose a stable exception and prove rejection leaves the existing
tree unchanged. The oracle negative matrix mutates selector 0's raw wait from
zero to zero and accumulates later mutations. Every negative must instead start
from an independent valid witness and change the selected field to a distinct
invalid value.

Those corrections are not sufficient. `prepare.py::generate` inserts
`m02_storage_fault_new_sink_guard`, but no production operation calls it. The
real create, write, fsync and report operations remain unchanged. A replacement
packet must connect separately guarded, occurrence-specific seams, including
the exact seven-byte partial retention case, preserve errno, and prove
unselected calls are unchanged. Its checked patch must bind the complete
generated diff.

`oracle.py::validate` accepts self-authored status, wait, fsync, process and seam
claims. The positive unit fixture even uses arbitrary `b"original"` report
bytes. A valid oracle must cross-bind raw parent wait observations, selected ELF
bytes, seam occurrence and ordering, retained prefix bytes/hash, child identity,
reaping, EOF, cleanup and absence. Report-open ENOSPC must prove the original
report is absent; applicable later report failures must retain the actual complete
or partial bytes without fabricating JSON.

Preparation also ignores short writes, does not guarantee fd closure on error,
and does not fsync `prepare.json`, the attempt directory and its parent. No
independent precreated durable witness producer exists yet.

The existing collector cleans a child before reporting, while pre-child failures
jump directly to `finished`. Artifact fsync failure can retain raw wait 256 when
reporting completes. Report open or final sync failure makes `report()` false and
selects collector exit 125/raw wait 32000; an already serialized report can still
contain `COMPLETED`. The witness must preserve the first failure and secondary
report failure separately and must not infer cleanup for a pre-child path.

The attempt-2 archive and all five current source hashes match their retained
failure records; the only attempt-1-to-2 change is the test import path. Design
record SHA-256: `12e86dee17da3e2c6962c00862ee2ef92d750d11feb270a1d54b66c6e1df83af`.

A future correction requires a newly scoped producer/oracle packet and a fresh
independent source review before any separate build or root release.
