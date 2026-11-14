# Scratch 110 → 142 GiB maintenance candidate

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Status: CORRECTED SOURCE CANDIDATE 2, NOT ROOT RELEASED, NOT EXECUTED. Owner is
scratch_growth_prepare; dispatcher owns integration, release, host execution and
retirement. Only this new maintenance-source directory was written. No workloads,
root command, image/loop/filesystem mutation, credential access, reserve change,
cleanup, detach, unmount or ownership unlink was performed.

## Exact operation and current source observations

The separately retained USER-AUTHORIZED-GROWTH-PROPOSAL.json at
/home/holden/mckernel-work/host-preparation/scratch-growth-20261023-1/ supplies user
authorization for necessary growth. It is not the independent operation release.
Prior 128 MiB preparation explicitly reports not executed; current backing and
loop still have 118111600640 bytes. Dispatcher must retain that disposition in
the final release, never replay the older one-shot proposal.

Ordinary metadata during preparation still observes canonical backing
/home/holden/mckernel-work/scratch.ext4, regular root:root0600,
dev66306/inode47468427, size118111600640, allocated102264397824 bytes;
exact mounted ext4 UUID2a5768c8-718d-4914-bdc0-6b32c5a92a52 at
/home/holden/mckernel-work/scratch, rw,nosuid,nodev,relatime. Observed loop36
7:36 is only a discovery result. Runtime ext4 errors_count and warning_count
read zero. Permanent /run/lock/mckernel-development.lock is dev27/inode4.
These ordinary reads are not fresh execution admission or full health proof.

New target is152471339008 bytes, +34359738368 bytes, at4096 bytes/block:
28835840→37224448 blocks, 880→1136 groups of32768. No shrink or feature
conversion is allowed. The three ordered mutation argv, within the already
privileged reviewed CPU7 route, are exactly:

```text
/usr/bin/truncate --size=152471339008 -- /home/holden/mckernel-work/scratch.ext4
/usr/sbin/losetup --set-capacity <fresh exact source of mounted scratch>
/usr/sbin/resize2fs <same revalidated source> 37224448
```

Source revalidates original backing inode/owner/mode/size, mount UUID/options,
loop BACK-INO/BACK-MAJ:MIN against that exact backing inode/device,
mount-directory st_dev against resolved block-device st_rdev,
loop backing/offset/sizelimit/autoclear/RO, device identity,512-byte sectors,
complete dumpe2fs header geometry/reserves/health and runtime ext4 error counts
between every primitive. Expected geometry states are:

| Point | Backing bytes | Loop bytes | Filesystem blocks |
| --- | ---: | ---: | ---: |
| Before |118111600640|118111600640|28835840|
| After truncate |152471339008|118111600640|28835840|
| After loop update |152471339008|152471339008|28835840|
| After resize |152471339008|152471339008|37224448|

## Release inputs that still must be produced

The script deliberately has no default execution or embedded release. Its exact
future argv is `/usr/bin/python3 <absolute grow_scratch.py> --release
<canonical independently reviewed release.json> --release-sha256 <exact SHA256>`.
The dispatcher must bind this to its existing supported CPU7 root capture route;
the exact existing route and fresh attempt namespace are not fabricated here.
Use sudo -A only at that existing boundary, preserving inherited SUDO_ASKPASS;
the inner script is root already and never calls sudo or reads credentials.

Release status PASS_EXECUTION_RELEASE, execution_count1, scope exact above,
author, source_sha256 and external independent_review pointer {path,sha256}
must bind an independent reviewer with implementation_ownership=false and
reviewed_release_payload_sha256 over canonical sorted compact JSON excluding
independent_review. Bind this profile/test result in the reviewer record too.
No independent reviewer or release is claimed by this source owner.

Other release fields:

* `capture_directory`: new empty canonical external HOST directory beneath
  /home/holden/mckernel-work/host-preparation, never scratch.
* `historical_128m_attempt_disposition`: NOT_EXECUTED_RESOLVED, only after the
  dispatcher's exact historical-receipt reconciliation.
* `filesystem_qualification`: external {path,sha256}, status
  PASS_NATIVE_EXT4_GROWTH_110_TO_142, exact UUID, expected_reserved_blocks288358,
  kernel_vendor_binding_verified=true, resize2fs_vendor_binding_verified=true.
  Actual package/source binding evidence must support these predicates. The
  script also requires fresh exact kernel_release, kernel_version_signature,
  resize2fs_sha256 and dumpe2fs_sha256 matching the installed running environment.
  `geometry` must exactly equal the source GEOMETRY dictionary: approved complete
  features (including resize_inode),4096-byte blocks,32768 blocks/group,
  descriptor size64/blocks14→18, reserved GDT1018→1014,8192 inodes/group,
  inode size256/blocks512, inode count7208960→9306112. Every required header
  value must be present and correct at every stage; no missing-field equality
  can pass. This binding still requires fresh qualified evidence.
* `stock_resize2fs_fallback_risk_explicitly_accepted`: true only if independent
  operation review accepts the known internal fallback limit below. Otherwise
  retain candidate and prepare a separately reviewed execution-method change.
* `host_extra_bytes`: integer>=1GiB covering ALL remaining all-lane metadata,
  capture, emergency and ongoing growth, not merely this script's capture.
  `scratch_extra_bytes`: integer>=0, all additional unchanged scratch budgets.
* `retirement`: external {path,sha256}, status PASS_POSITIVE_RETIREMENT, exact
  current boot_id and observed_epoch no more than60 seconds old under exclusive
  campaign control; scratch_writers/qemu_tasks/docker_tasks/live_leases all[];
  active_110gib_consumers_reconciled=true; protected_scratch21_unchanged=true.
  These fields require actual bound underlying positive retirement and identity
  observations, not a hand-written assertion. Final reviewer must inspect them.

The main script locks the existing permanent27:4 via nonblocking flock and uses
the EXISTING c252ee34 disk wrapper's `_acquire_lock` O_EXCL/fsync schema
mckernel.heavy-operation.v1 at scratch/mckernel-heavy-operation.lock, with kind
scratch-growth-maintenance. This is an explicit new operation kind for review;
all existing build/image/guest consumers refuse an occupied shared path. The
helper hash is pinned in source. It does not invoke a build. Shared record and
captured retained-owner identity are never released/unlinked by this script.
Separate normal dispatcher retirement/reconciliation must precede new work.

Existing exact current ownership paths to positively reconcile BEFORE acquiring
the new shared record (taken from current235 observer, not historical search):

```text
/home/holden/mckernel-work/scratch/native-running-external-modules.lease.json
/home/holden/mckernel-work/scratch/native-running-external-modules-operational-exclusion.json
/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json
/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock
/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/common-exclusion.json
/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/lease.json
/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/common-exclusion.json
/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/image-lease.json
```

Absence alone does not establish retirement. Preserve scratch21 container/records,
exclusions57687/57688, dirty inputs, original failures and permanentmutex27:4.
No unlink of those protected records or raw container removal is permitted.

## Exact active 110 GiB consumers

Current native235 observer, ending
p-m06-current68-native-stage-binding-20261022-1/fork-v3-matched-process-successor-1/
case-235/final-runtime-ready-1/root-live-admission-1/read_only_native235_admission.py,
SHA2563dd230d35c41011e84b13cecef9ab303586c02ada9b0259fa50487d16d79b05b,
line21 requires118111600640. This is an additional active pin beyond the latest
CURRENT.md claim of sole P12 pin. Preserve predecessor; either complete its
admissible workload before maintenance or prepare an independently reviewed142GiB
successor before reuse. Dispatcher was informed immediately; this lane did not
change that observer or its release.

P12 selected private source ending seven-check-closure-20261022-1/
p12-long-session-1/coupled-host-filebound-1/source/long_transport.py,
SHA2562964902b8b2465c40c4ee5c37fa161507426cc6695757cc46177dbea1b4b2075,
line214 pins110*2**30. Separate P12 owner handles its coherent successor. No
canonical source or historical release is rewritten by maintenance preparation.

## Resource, health and reserve qualification

HOST admission pessimistically charges TARGET minus ACTUAL allocated backing
bytes, not merely the32GiB logical increment. At the retained observation this
is50206941184 bytes (46.758GiB). HOST available must exceed that plus16GiB floor
plus all host_extra; sparse truncate is not physical reservation. Scratch must
retain12GiB plus scratch_extra before, between and after primitives. The
full-gap HOST admission is likewise repeated at all four snapshots. The apparent~32GiB gain is not
an application admission or a weakened unchanged SDK/guest resource oracle.

Proposed maintenance profile: one serialized CPU7 root operation, no overlap
with heavy/root/native/writers; parent memory<=512MiB, nofile64, core0, no changed
swap/affinity/system limits. Each command stdout/stderr max1MiB (RLIMIT_FSIZE),
metadata max1MiB, ordinary command20s, resize600s; external capture budget1GiB
minimum including surrounding existing route. Root caller limits must be reviewed
for this precise metadata operation; they are not inferred from ordinary tests.
No child CPU limit is invented beyond reviewed outer controls. Children inherit
the SAME permanent lock descriptor. On timeout they are neither killed nor
declared retired, and retain the lock until they exit. Shared token persists.

Healthy mounted needs_recovery can occur without corruption. Require clean
superblock state, zero recorded/runtime errors and warning_count, same features
and inode/block geometry, no aborted journal/read-only transition. Full before/
after headers and runtime health plus kernel/resize2fs vendor identities must be
retained. Descriptor groups increase880→1136, descriptor blocks14→18 at64-byte
descriptors/4096-byte blocks; reserved GDT behavior must be qualified by the
selected implementation, rather than requiring unchanged1018 blindly.

Historical source review predicts normal native EXT4_IOC_RESIZE_FS on5.15 uses
integer floor(288358*100/28835840)=0, adding zero reserves, leaving288358.
That is a conditional prediction, NOT fresh installed-vendor implementation
proof. Historical stock resize2fs1.45.5 can internally try its legacy path after
ENOTTY/EINVAL; legacy per-group calculation differs:327 reserves/group times256
added groups =83712 added, for372070 total versus native288358. Candidate1's
approximate372244 was incorrect and remains preserved in candidate1/. Postchecks cannot prevent such an internal
fallback attempt. Fresh exact implementation qualification remains mandatory.
The new script requires unchanged reserve288358 at each check and fails on any
fallback/error indication, including actual1.45.5 messages `Old resize interface
requested.` and `Performing an on-line resize`. Never run tune2fs, lower reserves
or repair a mismatch. A native-only EXT4_IOC_RESIZE_FS helper would eliminate
stock internal fallback, but adds new source/ABI and execution-method review.
This one bounded correction keeps the existing three primitives and makes the
stock-risk decision explicit. No alternate helper is proposed as released.

Every command retains exact argv, stdout, stderr, PID/starttime, exit/timeout.
Any error, overflow, capture loss, unsupported health/geometry, identity change,
failed postcheck, service/auth/policy stop or uncertain completion means STOP;
no successor, workload, replay or automatic retry. Retain larger file/capacity/
partial metadata and ownership. No shrink-back, detach, unmount, fsck, cleanup or
automatic recovery. Dispatcher must positively retire commands under existing
controls and independently review recovery. Root-process termination does not
prove in-flight filesystem work has retired.

## Actual ordinary verification

Candidate1 and its14-test PASS sources/raw/profile/receipt are preserved under
candidate1/. Independent ACTUAL-MAINTENANCE-SOURCE-REVIEW.md returned HOLD for
specific identity/geometry/fallback/test gaps. This candidate2 is the ONE bounded
correction of that source family; a further source failure requires expert
escalation rather than another correction loop. No privileged attempt occurred.

CPU0 bounded light-job grant permits this single<=512MiB job alongside the
separate P12 light lane (max two). Exact corrected-candidate command (functional
OS only; no security testing):

```text
taskset -c 0 prlimit --as=536870912 --cpu=20 --nofile=64 --core=0 timeout 25s python3 -m unittest discover -s docs/verification/evidence/scratch-growth-20261023-1/maintenance-source -p test_grow_scratch.py -v
```

27 tests PASS, exit0,0.640s reported test runtime. Raw candidate2-tests1.stdout/
stderr retained in this directory. State-machine/mocked tests cover exact three-command
order, geometry after every step, each failed primitive/check stopping successors,
all four full-growth capacity checks, actual legacy-message output, loop/feature changes,
duplicate header/JSON rejection, mandatory extra budget, nonzero capture failure
and timeout bookkeeping. NEW fixture tests execute the actual snapshot and main
bodies through all four stages, valid independently bound test receipts, real
temporary-file permanent-style flock and existing helper's real O_EXCL/fsync
shared-record protocol. Storage metadata/mutation commands and root identity
are synthetic; only ordinary tiny temporary files are changed. Expected failures
cover loop backing inode/device and mounted-device mismatch, every missing
required header field, missing resize_inode/extra unsupported feature, wrong
reserved-GDT stages, invalid geometry qualification, wrong permanent-lock identity,
stale/nonretired receipts, retained shared owner after snapshot failure, and
occupied shared record never replaced. A separate actual ordinary child proves
the inherited temporary-file flock survives the parent's descriptor close after
timeout, and becomes available only after positive waitpid retirement. Its
ResourceWarning while intentionally live is retained; PID3462800 was positively
waitpid-reaped by the test, with no kill or orphan. This establishes ordinary
FD lifetime, not the future privileged outer route's behavior.

No real root, storage, loop, Docker or guest operation ran. This is source
correctness evidence only, no OS behavior or Rust-retirement acceptance.
Candidate2 first tests passed; prior128MiB proposal has zero execution attempts.

Next executable observation: independent focused review of this source/profile,
including precise installed reserve/fallback qualification and current positive
retirement inputs; if accepted, dispatcher binds one fresh exact root operation
release. No privileged observation or effect is authorized by this document.
