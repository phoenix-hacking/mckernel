# Read-only role FD budget exercise — source only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This is an unrun, non-authoritative source exercise. It uses the selected
child4 fixed loader and actual source-bound production functions under temporary
ordinary-user fixtures. It performs no fork, root call, pidfd operation, real
signal, installation mutation, mount or immutable ioctl. Synthetic fixture
creation writes only to a fresh local temporary directory, which is intentionally
retained. Its fixed nonce is only a local fixture name and is not an operation
nonce or admission.

Run one role per separately admitted unprivileged process, on CPU 6 with the
existing 128-FD light-test profile or, only when separately admitted, the
existing 256-FD operation-equivalent profile. The driver never changes either
limit. Supply an existing caller-owned private `FIXTURE_PARENT`; the driver
creates an exclusive child directory and records its path. Core command:

```
/usr/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-role-fd-budget-1/role_fd_budget.py --role ROLE --fixture-parent FIXTURE_PARENT
```

`ROLE` is `parent`, `keeper`, or `installer`. Root supplies the separately
reviewed CPU/timeout/resource wrapper and a distinct result capture for each.
The driver refuses UID 0, affinity other than CPU 6, and limits other than the
inherited 128/256 values. It outputs a JSON observation or a FAILED_UNKNOWN
record and exits nonzero on failure; no failed/ambiguous close is retried.

The parent scenario exercises two actual three-path `open_exact` walks plus
actual `install_proof`, which opens and hashes all 23 proof leaves. The keeper
scenario executes actual phase-zero `verify_source` for 23 source leaves, one
three-path walk and the same actual proof. The installer scenario invokes actual
`install()` with only root ownership, flags and control/receipt gates mocked;
it stops at the first attempted `O_CREAT` before journal or install mutation,
and confirms all 23 retained source inodes still read and hash correctly. The
source closure, direct child entry and parent3 manifest are hash bound. UID 0,
directory permission interpretation, immutable flags, time and host/control
proofs are fixture mocks; this is no authority for any real operation.

The observer wraps selected Python `os.open` and `os.close`, samples
`/proc/self/fd` after each, and reports its own transient directory descriptor
separately (+1). It reports preoccupied descriptors, loader delta, live exit,
observed peak, attempted ambiguous close and any open whose sampling failed.
Python imports, built-in file opens and C-library internal descriptor bursts
are not comprehensively intercepted. The harness precreates fixture content
before its observed baseline. A measured result is a **partial mocked role
exercise**, not a measured or conservative production peak. It excludes actual
socket/SCM_RIGHTS/pidfd/fork paths, phase-zero receipt creation and full parent
context verification, installer output writers/freeze and all failure branches.
The installer scenario also retains the test loader's leaf FDs even though the
real exec topology differs. Any 128-FD failure is preserved; no automatic retry
or cap widening follows. An actual 256-per-role operation budget and independent
review remain outstanding.
