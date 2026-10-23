# Exact read-only installed scratch qualification query

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

SOURCE PREPARATION ONLY. No root, Docker, guest, module, compiler or filesystem
operation was run by this owner. Candidate2 maintenance source remains unchanged
at3ec596265016e2f2e3b06d54761489c1dcc41c6fa9abc54f124cff71f1533070,
already SOURCE PASS in CANDIDATE2-MAINTENANCE-SOURCE-REVIEW.md. This new packet
does not request duplicate maintenance-source review or release its mutation.
Ownership: scratch_growth_prepare writes only this new readonly-qualification/.
Dispatcher owns the independent read-only execution release and actual invocation.

## Concrete next observation and frozen route

This is one fixed metadata query of the current110GiB scratch. It reuses ONLY
the approved candidate2 `snapshot` function, never its main, execute_steps,
Runner or ownership-acquisition body. Before and after snapshots run exact
findmnt, losetup --list and dumpe2fs -h commands. They check dynamic loop/source,
backing dev66306/inode47468427/110GiB, actual loop backing device/inode, mount
st_dev, UUID, flags, sectors, zero ext4 error/warning counters, full approved
features/geometry/reserve288358/GDT1018 and inode layout. Full headers/command
stdout/stderr remain in the single root-query report. Stable identity/geometry
must agree; volatile journal/free counters are retained without requiring equality.

The query also captures current running release/version_signature, selected
BOOT_IMAGE argument, loaded ext4 srcversion if present, package binary/source
versions, and stable canonical hashes of the installed resize2fs/dumpe2fs,
installed boot image and kernel config. It checks each selected file's MD5
against the exact installed package md5sums entry and retains SHA256 plus file
identity. It reads only selected ext4/64bit/x86 config fields into the report.
No module is loaded; the observed installed configuration is CONFIG_EXT4_FS=y.
HOST/scratch statvfs and TARGET minus ACTUAL backing allocation are captured
before/after, including margins over16GiB HOST/12GiB scratch. This OBSERVES
capacity; all-lane extras remain NULL and no admission is granted.

Installed package queries during preparation observed:

```text
e2fsprogs 1.45.5-2ubuntu1.2, source e2fsprogs 1.45.5-2ubuntu1.2
linux-image-5.15.0-139-generic 5.15.0-139.149~20.04.1,
  source linux-signed-hwe-5.15 5.15.0-139.149~20.04.1
linux-modules-5.15.0-139-generic 5.15.0-139.149~20.04.1,
  source linux-hwe-5.15 5.15.0-139.149~20.04.1
/proc/version_signature: Ubuntu 5.15.0-139.149~20.04.1-generic 5.15.178
```

These are ordinary observed metadata, not fresh root qualification. One ordinary
dpkg-query -S using /usr/sbin names returned no package-path match because package
manifests use sbin/resize2fs and sbin/dumpe2fs; both canonical files resolve under
/usr/sbin. The new query uses those exact manifest entries and hashes canonical
files rather than repeating that failed ownership lookup. The kernel config is
in linux-modules' manifest, the boot image in linux-image's. No installed ext4.ko
is assumed: ext4 is built in. No broad filesystem/source inventory is proposed.

Exact inner root argv (frozen in capture_query.py):

```text
/usr/bin/sudo -A /usr/bin/taskset -c 7 /usr/bin/prlimit --as=2147483648:2147483648 --cpu=30:30 --fsize=8388608:8388608 --core=0:0 --nofile=256:256 -- /home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel/docs/verification/evidence/scratch-growth-20261023-1/expert-device-parser-correction/readonly-qualification-attempt2/query_installed.py
```

The existing accepted helper is
/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py,
SHA256990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8.
capture_query.py imports that exact source, never its unrelated main, then calls
`owned_capture({'argv': ARGV}, CAPTURE, 35, lambda: None)`. It verifies the fixed
query source using the helper's stable single-link hashed reader. Fresh one-shot
CAPTURE is exactly
/home/holden/mckernel-work/host-preparation/scratch-growth-20261023-1/readonly-qualification-attempt-2.
It must not exist; an occupied/failed namespace stops, never overwrites/replays.

Proposed ordinary parent argv for dispatcher review/execution only:

```text
/usr/bin/taskset -c 7 /usr/bin/prlimit --as=536870912:536870912 --cpu=30:30 --fsize=8388608:8388608 --core=0:0 --nofile=256:256 -- /home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel/docs/verification/evidence/scratch-growth-20261023-1/expert-device-parser-correction/readonly-qualification-attempt2/capture_query.py
```

The parent stays UID1000 on CPU7; sudo -A inherits the already authorized
SUDO_ASKPASS boundary. No credential/helper body is accessed. Root query enforces
CPU7, AS2GiB, CPU30, FSIZE8MiB, NOFILE256, core0 exactly; Python -I -B prevents
user imports/bytecode writes. Query soft wall deadline28s; each fixed read-only
leaf command has at most3s. Total outer owned_capture wall35s. Per-command
stream<=256KiB, aggregate root JSON<=4MiB, accepted closed stdout<=8MiB and
stderr<=1MiB; external HOST reserve32MiB covers both streams and small receipts.
Full target sparse-gap budgets are observations and remain separate from this
small capture allowance. No swap/affinity/system-limit change is performed.

The query takes the existing permanent27:4 nonblocking flock without replacing
or writing it, and passes that descriptor to leaf metadata commands. The parent
must not already hold a separately opened conflicting flock. This read-only
query creates no shared-heavy ownership record, releases/unlinks no record,
and does not grant subsequent growth. Run between conflicting root/writer
operations under fresh dispatcher coordination. Do not delay the currently
affected SDK materialization/build for this off-critical-path preparation.

## Capture acceptance and stop behavior

The exact helper already owns process-group termination/direct wait/census/closed
stream hashing. For this READ-ONLY query only, normal helper bounded timeout
retirement applies; this is not the mutation runner's preserve-inflight-effects
contract. Query leaf commands stay in the outer owned process group; they are
ordinary read-only utility processes. subprocess.run timeout kills/joins only
its direct read-only leaf, then the query stops; no automatic retry. The outer
helper preserves abnormal descendant/retirement/capture outcomes under its
accepted rules. No source change to that helper is proposed.

Accept only returncode0, direct_child_joined/group_absent/closed_streams=true,
timed_out=false and error/retirement_error bothNULL, followed by stable stream
hashes and exact report status
PASS_READONLY_INSTALLED_METADATA_NOT_VENDOR_SOURCE_QUALIFICATION. Capture receipt
and hashes are retained even if report parsing fails. Any missing/changed source,
identity, geometry, capacity metadata, nonzero/error/timeout/overflow/uncertainty,
new service/auth/policy stop or failed close means preserve and STOP. No effects,
retry, policy bypass, second namespace, workload or automatic source modification.
Root query source has never been executed in this lane.

## Vendor-source and stock fallback decision for the operation reviewer

Read-only package identity and exact installed-file hashes do NOT by themselves
prove the installed distribution's ext4 function bodies equal upstream. The
query deliberately emits vendor_source_qualification=false and
stock_resize2fs_fallback_risk_explicitly_accepted=NULL. Its output is not the
PASS_NATIVE_EXT4_GROWTH_110_TO_142 receipt consumed by maintenance. That later
receipt must bind the exact observed vendor source/version and selected bodies
to the approved GEOMETRY, with actual evidence behind both vendor-verification
predicates. No such receipt is invented here. The running release/signature and
installed boot-image/package match are ordinary provenance, not a direct hash of
the live in-memory kernel. Retain that practical limit accurately.

Existing selected primary predictions are retained in
SCRATCH-GROWTH-INDEPENDENT-REVIEW.md and the accepted candidate2 profile:

* [Linux5.15.178 ext4 resize.c](https://raw.githubusercontent.com/gregkh/linux/v5.15.178/fs/ext4/resize.c):
  native EXT4_IOC_RESIZE_FS, integer floor(288358*100/28835840)=0, predicted
  reserve288358; descriptor/GDT14→18/1018→1014, no feature conversion.
* [e2fsprogs1.45.5 online.c](https://raw.githubusercontent.com/tytso/e2fsprogs/v1.45.5/resize/online.c):
  native success returns; ENOTTY/EINVAL can fall through into legacy group-add.
  Legacy327 reserves/group ×256 groups adds83712, for372070. Output detection
  includes actual `Old resize interface requested.` and `Performing an on-line
  resize` strings. Detection after invocation cannot prevent legacy writes.

Concrete decision requested from the independent operation reviewer: after exact
vendor-source qualification and fresh retirement/admission, either accept this
known stock fallback exposure explicitly in the canonical release payload, OR
hold mutation for a separately reviewed native-only ioctl method. Recommended
focused route is the already source-accepted stock invocation if the reviewer
finds the bounded failure/retention disposition acceptable: fallback/unexpected
reserve is a FAILED operation, larger/partial state and ownership are retained,
no tune2fs/reserve reduction/shrink/detach/repair/replay or workload follows.
An ioctl error does not prove no partial native writes. A native-only helper
eliminates internal fallback but introduces a new execution method/ABI source
review; none is implemented or released by this read-only packet. The source
owner does not set the risk-acceptance field on the reviewer's behalf.

Current235 failed-attempt physical acceptance and coherent future235/P12
142GiB successors remain dispatcher-owned prerequisites. No active110GiB
consumer may execute during maintenance. Retain source/evidence predecessors,
Scratch21/exclusions57687/57688, permanent27:4 and all dirty work. Actual mutation
remains unreleased and belongs later between fully retired operations.

## Preparation checks only

New source has been AST-parsed under CPU0/512MiB/20CPU/25wall ordinary limits;
no source main was executed. Candidate2's already accepted27 fixtures and source
review are reused. No duplicate storage/main fixture suite or privileged query
was run. Frozen source/argv bindings accompany this profile. Next executable
observation is the independently reviewed fixed read-only query above, not growth.
