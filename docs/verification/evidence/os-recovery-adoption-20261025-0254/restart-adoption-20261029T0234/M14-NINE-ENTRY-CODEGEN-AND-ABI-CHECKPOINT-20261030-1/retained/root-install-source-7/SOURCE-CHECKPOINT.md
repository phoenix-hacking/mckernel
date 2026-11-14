# Functional M14 outside-group leasekeeper source successor

SOURCE ONLY; UNREVIEWED; NOT RELEASED. No sudo, fork, signal, subreaper syscall,
root operation, test, installation, mount, SDK, native work or cleanup occurred.
Prior v6 and its failures remain; V2 unknown 2 GiB, native12, scratch21 and
mutex27:4 remain held. Native current-free and all original source/collector,
profile/effective-view and native gates remain unchanged.

The exact profile starts a root issuer after sudo/taskset/prlimit on CPU6. It is
outside the private timeout group and uses `PR_SET_CHILD_SUBREAPER` through a
source-bound libc `prctl` wrapper. It validates the immutable start intent, actual
controller/guardian/monitor checks, scoped host receipt and pinned runtime before
opening the single lease FD under the private operation root. It does not flock it.
The issuer records the start nonce and forks/execs one root GNU timeout using the
reviewed DeferredFork/ChildRecord pattern. Timeout's default private group runs the
waiting installer directly: issuer, timeout and installer are the three operation
processes; each inherits a 1 GiB address-space ceiling, within the aggregate 4 GiB
operation planning allowance. Root must actually measure all shared headroom and
ensure native4+operation3 jobs and the 22.5447 GiB total stay within limits.

All FDs are opened after sudo. Only explicit already-owned descriptors are made
inheritable for the timeout/installer fork/exec; there is no sudo -C assumption.
The waiting installer verifies the exact source bytes and sends actual PID, birth,
parent, process group and boot in READY. It does not flock or install until GO.
The issuer verifies the timeout executable and exact argv, timer and installer
identity/birth, private PGID, its own outside-group position and the six campaign
actors/outer owner outside that group. It pins the installer pidfd, rechecks actual
controls/caps, seals the one-shot release with actual keeper, timeout and installer
identities, and sends GO. The installer verifies that release, locks its inherited
lease FD and ACKs. Because the issuer retains the *same* open-file description
outside the timeout group, timeout's group signals do not themselves close the
keeper's lease descriptor. Actual OFD inheritance through the selected GNU timeout
binary and kernel/subreaper behavior still require independent review and admitted
proof; no physical lease is claimed here.

The issuer polls timer and installer pidfds separately. It records timer direct
wait, actual installer pidfd terminal and any positive adopted-installer direct wait
as distinct facts. Timer exit alone never implies descendant retirement. The source
unconditionally holds UNKNOWN, records no empty group or complete installation
proof, and does not implement conditional retirement; an actual Root owner must
retain and explicitly resolve/retire it. If the installer is D-state/unjoined, the
outside-group keeper retains its actual FD and process/resource custody while alive.
The timer cannot unblock a stuck keeper journal, but it still governs its own private
installer group. Uncatchable keeper death remains an external-owner UNKNOWN case.

Root must provide a root-immutable start intent and scoped HOST_INSTALL_RESOURCE_
CUSTODY_V1 with native current-free null/no-unlisted UNKNOWN, exact initial caller
identity/ancestry, actual host/resource receipts, nonce, source/code/private-root
and lease identities, root-owned tool/interpreter bytes, clock caps, timeout bounds,
waiting-literal SHA, tool hashes and a release template whose six process identity
fields are null until READY. Root must independently review the `prctl` wrapper,
actual path/FD identity, ACL, group/lineage, boot/clock/cap checks, kernel behavior,
stop/failure custody and any future conditional retirement. No current-free,
source-exclusion, private-group-empty, native or execution-release fact is created.

`/usr/bin/python3` 3.8.10 AST parsing passed 26 Python files and three embedded
loader programs. Tests are UNRUN. After separate source/profile review and Root
admission, a proposed fresh-interpreter synthetic check is:

```
cd /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-source-7
/usr/bin/python3 -B -m unittest -v test_install_v2 test_keeper_lifecycle
```

Mocks do not establish actual OFD inheritance, pidfd, root, timeout, child adoption,
source exclusion or operational release.
