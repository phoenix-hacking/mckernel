# Layer-B native-owner object bootstrap packet 10

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This is the strategy change after
the candidate packet8 and bounded correction9 both failed review. It compiles
only one exact translation unit to a retained ELF relocatable object. It does
not link or execute the owner and does not release any compiler command until
an independent reviewer returns `PASS_OBJECT_BOOTSTRAP_PACKET` for these exact
bytes.

## Bound inputs and scope

The exact source is
`/home/holden/mckernel/scripts/tests/layer_b_native_owner_v1.c`, SHA256
`2c157335e88b2088c56fc40fd6c0d966dc653ea68b4726e51feb1d4b4e62eafc`.
The exact source-model test is
`/home/holden/mckernel/scripts/tests/test_layer_b_native_owner_source.py`,
SHA256 `427f6133497ce0706fce39d9e52051542821bc6deab29d27322733c927efd63d`.
Independent source review7, SHA256
`103a5e041f1851d893c5b5d8fcee05c7f813fb92bd2e81e1a94e46e370cd5d87`,
permits preparation of a separately reviewed bootstrap compile only.

Preserve packet8/correction9 and both failures. Their SHA256 values are:

- packet8: `3f8f363fe5e7086b027e7814ce98c7b715f3978981ff1e71b2234f0108bf0ec9`
- failure8: `157570389bc932efc440d2f380e2aeb9c91e44aaf3e52a53941c586b5035e5de`
- correction9: `923f1e45d9b5e9d3242c891b16c21af6e094ff7a78a677b08fbb37aee1434fb4`
- failure9: `f3e195ad50bc629a5ec1ba61248f33f3a4dfb64739694b78f730d8ca5d7cce1a`

The packet10 strategy review is
`docs/verification/stability-layer-b-native-owner-object-bootstrap-strategy-review-20260928-10.json`.
The fresh output root is exactly
`/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-10`.
The dispatcher must verify that it and the unique unit name are absent before
exclusive mode-0700 creation. Roots8/9 are absent because those packets never
released execution; do not describe them as compile attempts. No repository
file is writable by this packet.

## Exact object-only command

Let `R` be the exact root above, `S` the exact source, `B` the literal basename
`R/layer_b_native_owner_v1`, and `U` the literal unit name
`layer-b-native-owner-bootstrap-20260928-10-<nonce>.service`. The nonce is
generated once from a cryptographic source, recorded before submission and
must match `[A-Za-z0-9-]+`. These symbols document literal substitution; no
shell or environment-variable expansion is permitted.

Create only `R`, `R/home`, `R/tmp` and `R/logs`, all mode 0700, owned by the
current UID, with no symlink component. Submit exactly once with this argv:

```text
/usr/bin/timeout --signal=TERM --kill-after=1s 10s /usr/bin/systemd-run --user --unit=U --service-type=exec --working-directory=R --property=RemainAfterExit=yes --property=Restart=no --property=KillMode=control-group --property=RuntimeMaxSec=60s --property=TimeoutStartSec=10s --property=TimeoutStopSec=5s --property=SendSIGKILL=yes --property=UMask=0077 --property=StandardInput=null --property=StandardOutput=file:R/logs/unit.stdout --property=StandardError=file:R/logs/unit.stderr -- /usr/bin/env -i LC_ALL=C LANG=C HOME=R/home TMPDIR=R/tmp PATH=/usr/bin:/bin /usr/bin/prlimit --core=0:0 --cpu=55:55 --nofile=256:256 --fsize=67108864:67108864 --as=536870912:536870912 -- /usr/bin/gcc -v -std=c11 -O2 -Wall -Wextra -Werror -fno-pie -pthread -nostdinc -isystem /usr/lib/gcc/x86_64-linux-gnu/9/include -isystem /usr/include/x86_64-linux-gnu -isystem /usr/include -save-temps=obj -MD -MF B.d -MT B.o -c S -o B.o
```

The dispatcher replaces `R`, `S`, `B` and `U` with those recorded literal
absolute strings before preserving the argv. There is no shell, response file,
make/configure, import, test, second translation unit, linker, collect2, CRT,
target libc/pthread library, container, mount, root, sudo, credential, network
operation or owner execution. `-pthread` affects preprocessing/compilation only.
Expected generated outputs are exactly `B.i`, `B.s`, `B.o` and `B.d`, plus
controller/evidence files under `R/logs`.

## Pinned tools and input provenance

Before submission record resolved path, symlink chain, type, mode, UID/GID,
size and SHA256 for every selected tool. Current observed hashes are:

| Tool | SHA256 |
| --- | --- |
| `/usr/bin/gcc` | `6cb2d84ccd9fd3485d4e47ba032e626be65692601c38fad46866a6b565f3100f` |
| `/usr/lib/gcc/x86_64-linux-gnu/9/cc1` | `c09275e2d3f811e23d255eac415bfedd9e68ba8b5cf4b261d2fce136b5e8fc99` |
| `/usr/bin/as` | `8d45684bbd6420e3e97907257c510f199bb6c5f9b02ea8ee0a590c1a8b662ead` |
| `/usr/bin/env` | `5f7c7882898e9e280e93579b459e22b339c4f38cfd54a05b46b81dfb60c557cc` |
| `/usr/bin/prlimit` | `06a57e4767f1bdfcc8c5a39b4b58decb9366447b007a8bdd9d6b12d1e6698d8c` |
| `/usr/bin/timeout` | `91db1e64064f0bf5ee99abda3a054cc6f05748dad2af5a145f890c9172d28d73` |
| `/usr/bin/systemd-run` | `15c14831822016fd68ab3e2f265223463c46b4cf7fcc4595a91f09c5bbd950eb` |
| `/usr/bin/systemctl` | `ec3c1aa59f5047dacfdd00a90504e02557032bf4016f0d28799d95792e9005b1` |
| `/usr/bin/journalctl` | `4688b902b33e0d5d211a64c98a71ecfc1334dce4f2f4b4af20e6f4e554ed851e` |
| `/usr/bin/readelf` | `41a813335a74480f145fba9400aa7fb5c0ec7ffcaa7af7f33e832dc75eb90ffb` |
| `/usr/bin/objdump` | `afd9c7433c96cb0f37df99cab98fc860bbbe2bed17f37df66254a8778adfc61d` |

The host facts are GCC 9 and systemd 245. Before start build a finite baseline
of every regular file and symlink under exactly these deduplicated include roots:

```text
/usr/lib/gcc/x86_64-linux-gnu/9/include
/usr/include/x86_64-linux-gnu
/usr/include
```

Record spelling, canonical path, complete symlink chain, type, mode, UID/GID,
size and SHA256. Header symlinks may resolve only within those roots. After
resolved compile success, parse `B.d` as Make dependency syntax, including line
continuations and escaped names. Require target exactly `B.o`, source exactly
`S`, and every canonicalized/deduplicated header prerequisite present and
unchanged in the baseline. Parse the raw `-v` stderr to require the pinned cc1
and assembler, exact controlled include search and `S -> B.i -> B.s -> B.o`;
reject collect2, ld, external plugins/specs or an unexpected persistent path.

`B.i`, `B.s`, `B.o` and `B.d` are generated artifacts, absent at preflight and
hashed only after completion. Inventory every surviving private `R/tmp` entry.
Disappearing GCC scratch paths are ephemeral intermediates and are recorded as
such without invented hashes. The dependency file is preprocessor prerequisite
evidence, not a claim of complete OS-level file-open tracing. Compiler process
runtime libraries are environment dependencies outside this object packet;
link-time target libraries are not consumed.

## Identity-safe lifecycle

Use `CLOCK_MONOTONIC`. The state machine is
`PRECHECK -> SUBMIT_ONCE -> OBSERVE -> CLEANUP -> EVIDENCE -> terminal`.
Set observation deadline `D` to 60 seconds after the timestamp immediately
before submission. The submission wrapper consumes at most 11 seconds including
its client SIGKILL allowance. A nonzero/timeout submission latches the first
failure, enters cleanup for the same `U`, and is never resubmitted.

Every controller command is a literal argv wrapped by
`/usr/bin/timeout --signal=TERM --kill-after=1s`. Query `Q` is:

```text
/usr/bin/systemctl --user show U -p Id -p LoadState -p ActiveState -p SubState -p Result -p ExecMainCode -p ExecMainStatus -p InvocationID -p ControlGroup -p MainPID -p ExecMainStartTimestamp -p ExecMainExitTimestamp -p ExecMainStartTimestampMonotonic -p ExecMainExitTimestampMonotonic
```

Each query has a 2-second nominal timeout plus one-second client kill allowance;
sleep at most 100 ms between completed queries. Store every raw response and
require stable unit identity, InvocationID and ControlGroup. Pending states are
only activating or active/running. Normal completion is exactly active/exited,
Result=success, ExecMainCode=1/CLD_EXITED, ExecMainStatus=0 and a nonzero exit
timestamp. Capture that complete response, then enter cleanup immediately; do
not wait until `D`. Any query error/timeout, identity change, absent/ambiguous
unit, unexpected state, abnormal exit or `D` expiry latches failure and enters
cleanup. Artifact inspection is forbidden during observation.

Cleanup gets a new independent 30-second budget `C`. On normal completion issue
`systemctl --user stop U` immediately, with a 7-second nominal timeout and
one-second client kill allowance. On failure first take one best-effort bounded
query, then issue the same stop. If stop times out/nonzero, a post-stop query is
ambiguous/timed out, or the unit remains activating/running/deactivating or has
nonempty cgroup membership, issue this separate manager-side command even if
state cannot be read:

```text
/usr/bin/systemctl --user --signal=SIGKILL --kill-who=all kill U
```

The kill has a 2-second nominal timeout plus one-second client allowance. A
timed-out client signal never substitutes for the manager-side group kill.
Continue bounded queries/cgroup reconciliation only inside `C`. Map the original
ControlGroup through `/proc/self/mountinfo` and `/proc/self/cgroup` for the
actual named systemd/hybrid hierarchy, recursively reading descendant
`cgroup.procs`. Require loaded/inactive or, after a successful recorded stop,
unloaded/not-found; require the original cgroup empty or absent with an
accessible parent. `MainPID=0` alone is insufficient. Capture failure status
before `systemctl --user reset-failed U`; reset only a resolved failed unit and
take a bounded final query. Do not require both loaded inactivity and absence.

Unreachable manager, uncertain late submission, changed identity, residual or
uninspectable cgroup, or exhausted `C` is `FAIL_UNRESOLVED`. Retain the root and
identity, do not reset unresolved evidence, retry, signal a numeric PID or
start another unit. This cannot guarantee recovery from manager/host failure or
uninterruptible I/O.

## Static object evidence and terminal handling

Only after compile success and resolved cleanup, run these nonexecuting
inspections, each under a 5-second nominal timeout plus one-second client kill:

```text
/usr/bin/readelf -h -S -s R/layer_b_native_owner_v1.o
/usr/bin/objdump -f R/layer_b_native_owner_v1.o
```

Require ELF64, x86-64, `ET_REL`. Record raw stdout/stderr/status and tool hashes.
Never execute or link the object. Journal capture uses a separate 5-second plus
one-second budget after supervision cleanup:

```text
/usr/bin/journalctl --user -u U --no-pager -o short-monotonic
```

Capture exact expanded argv/environment, unit definition/properties, all
controller streams/statuses/timestamps, the pre-stop terminal response, source/
test/tool/header pre/post hashes, compiler streams, generated artifacts, private
tmp inventory, full output tree, repository status, capacity/limits and zero
residual observations. `failure.json` immutably identifies the earliest failure
and separately appends later cleanup/evidence errors. At the first productive
failure stop compile/inspection work, but finish bounded cleanup and evidence
retention. Preserve and archive the root without deleting it; never overwrite or
retry the unit/root.

A successful packet10 result proves only that the exact source compiles through
preprocess/cc1/assembler into a reviewed relocatable object under the recorded
owner. Linking, executable behavior, native fault/descriptor/signal/status tests,
M02/M03 admission, kernel/native/guest behavior and all application, production,
language and whole-OS acceptance remain unreleased.
