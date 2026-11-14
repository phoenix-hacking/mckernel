# Functional M14 bounded install-only completion successor

SOURCE ONLY; UNREVIEWED; NOT RELEASED. No test, sudo, fork, signal, subreaper
syscall, root operation, installation, mount, SDK, native work or cleanup ran.
v7, its review and all predecessors remain. The previous v8 review snapshot is
preserved in `prior-revision/`. V2 unknown 2 GiB, native12, scratch21 and
mutex27:4 remain held. Existing native/current-free/source/collector/profile/
effective-view gates are unchanged.

The outside-group issuer now has a real install-only completion path. It requires
an actual direct timer wait with zero exit, a separately observed installer pidfd
terminal, and a zero direct installer wait when that adopted wait is available.
An unavailable adopted wait is recorded as such; it is not inferred from timer
exit. It then performs a bounded, no-error `/proc` census against an admitted
proc/PID-namespace scope and rejects private-group members and issuer descendants.
It reads the nonce/release-bound terminal install journal; for each of 23 exact
closure artifacts it requires ordered creation, writer-close, immutable and held
records, then independently checks read-only inode, ownership, mode, membership,
size, hash and immutable flag. Both installer capture writers must be fsynced,
closed and independently reopened/hashed. A second no-error census precedes the
result `INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ`, with native release false,
native current-free null and no source/native acceptance claim.

The issuer retains the shared lease OFD if `retire_operation_only=false`. If true,
a separately Root-issued immutable owner receipt must explicitly authorize
`ROOT_INSTALL_OPERATION_RETIREMENT_V1` / `ROOT_CODE_INSTALL_ONLY`, the same nonce,
`APPROVED_IF_VERIFIED`, native release false and an actual independent-review hash.
Only after every completion criterion is positive does it close its own lease FD;
failed or uncertain close is UNKNOWN and never retried. This is local operation
custody only and is not native cleanup. If the result is held, the same keeper
remains alive after reporting; if result output is uncertain it retains UNKNOWN.

The start intent adds `proc_scope` with `proc_device`, `proc_inode`, `pidns_device`
and `pidns_inode`, plus `join_capture_reserve_ns` between 1 and 30 seconds. Root
must independently bind the actual host visibility scope. The existing release
template adds a Boolean `retire_operation_only`. The reserve fits within all
original BOOT/MONO/UTC limits and accounts for the actual elapsed timer runtime;
GO is refused after the timer's 60-second period. Scans, capture and verification
cannot extend those limits. I/O or D-state uncertainty leaves the outside-group
keeper owning the actual lease while alive; an external Root owner must retain
and resolve the process/resource hold.

Root must still supply an immutable start intent, exact scoped HOST_INSTALL_
RESOURCE_CUSTODY_V1, independent owner release, actual caller/boot/source/path/
lease/clock/runtime/tool/PGID/resource bindings and fresh one-shot admission.
The owner receipt is required in both modes; retirement mode needs the additional
explicit authority described above. UID1000 ACL/readability, actual source
exclusion, effective graph and native/current-free remain separate proof. No
actual facts or receipt are created by this source packet.

`/usr/bin/python3` 3.8.10 AST parsing passed 28 current Python files and 3 inline
programs. Tests are UNRUN. After independent review and Root admission, the
proposed fresh-interpreter synthetic check is:

```
cd /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-source-8
/usr/bin/python3 -B -m unittest -v test_install_v2 test_completion
```

These mocks do not establish actual pidfd/OFD, namespace census, writer closure,
installation, UID1000 access or Root operation acceptance.
