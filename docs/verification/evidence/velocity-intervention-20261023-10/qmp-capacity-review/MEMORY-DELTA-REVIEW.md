# QMP memory-model correction: narrow independent review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
**Accept this memory-only source correction for one fresh root-granted ordinary
regression run.** No tests, root operations or workloads were run by the reviewer.
The six QMP/runtime source hashes are unchanged from the accepted source design.

The first actual result remains preserved byte-for-byte, both at its original
root-actual-qmp-fixture-1 path and in pre-memory-correction-1:24 tests ran,
23 passed and the memory fixture failed on actual Python3.9 overhead542B versus
the512B assumption. The direct child joined, its group was absent, streams
closed and no timeout occurred. This failure is not replaced with a pass.

The corrected fixture hash is
`421063d4ded1c80acec0ee3e0ad39a156737ac83cde7d7a4a68525f61a18d237`.
It measures decoded-row overhead again, records the measurement and preserved
542B history before assertions, and uses640B per row with a separate256MiB
fixed interpreter/control allowance. It measures its own VmSize and requires
that to fit the fixed allowance. The same fixture derives the complete sums
from actual profile caps and requires them to fit the proposed2GiB address-space
and12GiB container admission. This is more than a relaxed per-row comparison.

The arithmetic closes:

| Component | MiB |
| --- | ---: |
| 1,052,672 hard-cap rows ×640B | 642.5 |
| Additional row metadata versus512B | 128.5 |
| Inner full data sum | 1654.5 |
| Inner plus256 fixed allowance | 1910.5 |
| Remaining under2048 | 137.5 |
| Outer full data sum | 1622.5 |
| Outer plus256 fixed allowance | 1878.5 |
| Remaining under2048 | 169.5 |
| Possible8GiB guest plus inner including fixed | 10102.5 |
| Remaining under12288 | 2185.5 |

The full inner sum includes row metadata,68MiB hex characters,272MiB encoded
copies,384MiB serial,256MiB trace and32MiB metadata planning. The outer sum
includes640MiB pending capture plus rows, hex and encoded copies. The failed-reap
case is explicitly charged because writer capture follows the teardown attempt,
not guaranteed positive reaping. Owner readback remains after absence/release.

Raw/encoded/row caps, polling, writer/reader deadlines, shared640MiB capture,
per-file384MiB limit and4224MiB logical growth are unchanged. The extra128.5MiB
is bounded RAM metadata within existing admission, not additional output storage.
No larger RAM reservation or weakened functional oracle is proposed.

The next run must use a fresh direct-job capture, bind the current corrected
markers/test hash and retain row-memory-model.json from the printed fixture
evidence directory. Actual measured overhead, VmSize and every resource
inequality must pass. This review does not award a second fixture result,
source-cohort runtime release, kernel/application acceptance or partial P12 time.
