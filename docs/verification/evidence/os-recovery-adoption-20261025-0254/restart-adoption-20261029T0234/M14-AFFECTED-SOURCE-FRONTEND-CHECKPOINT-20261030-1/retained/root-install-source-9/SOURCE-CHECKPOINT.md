# Functional M14 v9 install-only completion correction

SOURCE ONLY; UNREVIEWED; NOT RELEASED. No tests, sudo, fork, root action, physical
install, mount, SDK, native work or cleanup occurred. Frozen v8 and all earlier
failures remain unchanged. V2 unknown 2 GiB, native12, scratch21 and mutex27:4
remain held; native current-free and source/collector/profile/effective-view gates
remain unchanged.

The complete nonce-, role-identity- and source-bound result is written to an
exclusive private result file, fsynced, writer-closed, reopened and byte-verified;
its identity/hash are journaled durably, then the entire proof is written to the
actual Root stdout capture and the handoff is journaled before any optional lease
close. A short/failed output leaves UNKNOWN with the lease held. A successful
operation-only close is recorded separately; if publication fails after actual
close, the in-memory and journal UNKNOWN disposition says CLOSED_CONFIRMED or
CLOSURE_UNKNOWN, never claims the descriptor is still live or retries its number.
No native cleanup or release follows.

At GO the min(original BOOT/MONO/UTC caps) must contain the *full* 65-second
private timeout plus the positive admitted join/capture reserve. This deliberately
does not subtract the pre-fork interval. A separate check rejects GO when the
actual pre-fork upper-bound sample is already 60 seconds old.

`PROCESS-CREATION-MODEL.json` enumerates exactly three roles and two creation
sites: issuer's DeferredFork creates pinned GNU timeout; the reviewed timeout
creates the verified waiting installer. No other commands, forks or setsid are
allowed. It identifies source-bound executed modules, the trusted root-owned
Python/libc/kernel/GNU-timeout boundary, and copied package artifacts that are
never executed during installation. The `/proc` scan compares each sampled
PID/birth/parent/group twice and rejects missing parents and errors, but remains
explicitly `NONATOMIC_POINT_OBSERVATION`; it is not continuous containment proof.

**Actual missing fact:** no independent live root creation-custody holder has been
launched in this invocation, and this source does not bootstrap one. The existing
user-UID1000 controller is not such a holder. `verify_creation_custody` requires
a separately Root-issued immutable owner receipt attesting the exact reviewed
model/source pins and a live UID0 holder PID, birth, executable hash and expiry,
with `HELD_THROUGH_OPERATION` scope. Hashes and holder liveness do not themselves
prove an exclusion mechanism. Root must identify and independently review an
actual mechanism that grants and maintains this exclusive operation creation
custody. If it cannot, the exact custody fact is UNKNOWN and source fails closed
before GO; neither this model nor the process census becomes physical proof.

The same-process phase-zero loader must set `completion.SOURCE_PINS` from its own
held, hash-verified exact issuer and completion bytes before invoking
`verify_creation_custody(install, owner_fd, template, intent)`. The externally
Root-issued nested `creation_custody` schema and required template/intent fields
are in that function. Actual root owner, receipt bytes, UID1000 read, source
exclusion, native/current-free, controls, resources, clocks and one-shot admission
remain separate. Existing v8 eight synthetic tests passed only for their exact v8
source; that result does not clear v8 findings or verify this successor.

`/usr/bin/python3` 3.8.10 AST parsing passed 28 Python files and three embedded
loader programs. New tests are UNRUN. Following independent source/profile review
and Root admission, the proposed exact fresh-interpreter regression command is:

```
cd /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-source-9
/usr/bin/python3 -B -m unittest -v test_v9_corrections
```

These synthetic tests target full GO reserve, durable full-result publication and
short stdout, plus creation model/holder conditions. They do not prove a real
holder, continuous containment, pidfd/OFD, filesystem ownership or a root release.
