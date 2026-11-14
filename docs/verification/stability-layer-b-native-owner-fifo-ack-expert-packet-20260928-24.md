# Layer-B FIFO identity barrier: expert packet 24

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This complete execution contract
replaces the operational text of rejected packet21/correction22; those originals
and their failures remain immutable. This is an escalated design after one
candidate and one bounded correction failed the same family, not a fresh retry
budget. Only an independent `PASS_FIFO_EXECUTION_PACKET` bound to this file's
exact SHA256 releases one fresh root12 compile-only attempt. Preparation of this
document has executed no FIFO, service, compiler, link, owner, test or guest.

Owner: dispatcher, with a reconciled runtime lease. Concrete defect: fast main
completion can erase the cgroup property before identity capture. The next
executable check is the one object-only compile below, held behind a FIFO until
its original owner identity has been durably recorded. Success unlocks review of
the relocatable object and a separately reviewed linking/owner packet. It does
not unlock M02/M03 execution, applications, privileged work or acceptance.

## Immutable bindings

All paths in this table are relative to `docs/verification/`. Authenticate every
record before creating root12; preserve each record and its own bound lineage.

| Record | SHA256 |
| --- | --- |
| `stability-layer-b-native-owner-object-bootstrap-packet-20260928-10.md` | `b65c345bc8b15e6043bf0ae728d23e0cba895dcfbf3ad383160011094900acbd` |
| `stability-layer-b-native-owner-object-bootstrap-packet-correction-20260928-11.md` | `c5966dd64e8d38857433f2c9bbdd0b4a41793e40535f9d32a20a35af03519604` |
| `stability-layer-b-native-owner-direct-object-packet-20260928-15.md` | `73ed242336988f5f66bb65db7fc81f85e742ff197552047f74b7ec9b3ac4f100` |
| `stability-layer-b-native-owner-fast-completion-correction-packet-20260928-18.md` | `f30561ea725dfd5afb3ecfef43c24d46b3f98c0e4b8c2dbd95dbc894e2df3375` |
| `stability-layer-b-native-owner-fast-completion-correction-20260928-19.md` | `0623f94b2da690f79a7cbb00dc3d013f897305c6d21954c50e33e9c03e2f19a8` |
| `stability-layer-b-native-owner-fast-completion-packet-review-20260928-20.json` | `0261ed3606e2d2250b68018ef676c6ce8953ff09a464803d7af95c9db460aa0d` |
| `stability-layer-b-native-owner-fifo-ack-packet-20260928-21.md` | `4d2931e733c88a7d81de543d5b8b574bfc88a82051524107cad96ecc0136d9d1` |
| `stability-layer-b-native-owner-fifo-ack-packet-correction-20260928-22.md` | `30b90e7572d6911ac5f4343bd17716b274ed5890a9a691b95f83fd293b81050e` |
| `stability-layer-b-native-owner-fifo-strategy-review-20260928-23.md` | `2874e3c12f5f367c2e168ad01cbb7b3dedccfc9a23aafb6f12a176928123136a` |
| `stability-continuation-shutdown-checkpoint-20260928-6.json` | `322d00b463023930292df91dba0079730cc1d5f03375e1b0f21263538b424a64` |

Record23 is the immutable strategy authority: `PASS_FIFO_STRATEGY`, reviewer
`/root/layer_b_fifo_strategy`, turn `01a0e771-eb1d-77c2-ba7d-6723810d9587`.
Checkpoint6 authenticates its historical status only; its historical pause is
not a pause of the current invocation. A growing console is not a strategy
digest. The closed review logs under
`.git/os-autopilot/runs/20260928T095536Z-095509d1/agents/` preserve the rejected
packet findings:

| Review log | SHA256 |
| --- | --- |
| `2c4c51288244f4892b2e13aaa47dd399cff2c318de958f0f8634a0749162c0fd.log` | `c4bc819b847f2879220a289623b350cfb885ea3a8f36575f15f6f2ca5d65519d` |
| `84251a878cf735e69d09811d70c24b28dab4ddff0e4d40973353b6a9c97b76c8.log` | `eb1076a52ca4ee5f048e048236ca9c039426c3eeb7907fe831769999f755d112` |

Their consolidated findings are FIFO content-hashing/open interference;
inherited sleep/test commands; the false guarantee that writer failure prevents
gcc; missing durable identity/fresh query and full deadline admission; conflated
pre/post-ack states; and missing exact command/strategy/tool bindings. Each is
addressed below. Archive these closed logs with the dispatcher evidence before
execution so their local launcher paths are not the sole retained copies.

Preserve source review7 (`103a5e041f1851d893c5b5d8fcee05c7f813fb92bd2e81e1a94e46e370cd5d87`),
packet8/failure8/correction9/failure9 bindings in packet10 and all controller
failure records in direct15. Retain attempt10 failure
`8c5437e98d4e98640560d6085927371846cb331fc7d7a2f69d94fe3ed5b95d99`,
failure review16 `5d29eec6a895ae7c0439693592efc5ae9ef7ab54a24b27d96d08e0d277da716c`,
cleanup recheck17 `150bed896bb8b4ebd7077cf221c6622f3d11a936c27b07f662913445ba473cc9`,
quiescence review17 `ae8cb248b006506908972143be9017d82d837fcb1ccb39cfdb2c740a81b30140`,
failure18 `a8f6564216ac1005a6ab7dcc2cfaa59563a287c95f77a578d7c691dc68aeef05`,
and attempt11 failure `47d8832f918cb98b35a71eea0e517e392474c3737d953b1939a6a8abf6c1455`.
No prior artifact is inspected or credited by this attempt.

Exact source `S` is
`/home/holden/mckernel/scripts/tests/layer_b_native_owner_v1.c`, SHA256
`2c157335e88b2088c56fc40fd6c0d966dc653ea68b4726e51feb1d4b4e62eafc`.
The source-model test is
`/home/holden/mckernel/scripts/tests/test_layer_b_native_owner_source.py`, SHA256
`427f6133497ce0706fce39d9e52051542821bc6deab29d27322733c927efd63d`;
this packet authenticates but does not run it.

## Preflight and fixed paths

The one root `R` is
`/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12`.
The output basename `B` is that root plus `/layer_b_native_owner_v1`.
The one unit `U` is
`layer-b-native-owner-bootstrap-20260928-12-5a3a3fe8-03a9-4dc6-86fc-9666747decc4.service`.
The nonce was generated once from `/proc/sys/kernel/random/uuid` during drafting;
record these exact bytes before submission. No regenerated nonce is allowed in
this attempt. Require root and unit absent; otherwise stop without reuse.

Before creation authenticate bindings, tools and include baseline; reconcile
current leases and prior cleanup, record UID/GID, current affinity/limits and
measured host/scratch capacity, preserving at least 16/12 GiB free respectively
and any greater capture/emergency requirement. Do not widen affinity or limits.
No repository file is writable by execution. Exclusively create only R, R/home,
R/tmp and R/logs as mode-0700 directories owned by the current UID, with verified
canonical ancestry and no symlink component. Required output paths B.i/B.s/B.o/B.d
must be absent. Root creation, inventories and token preparation occur before
submission and do not consume the submission-anchored deadline.

Create exactly one FIFO with this argv, bounded by timeout 2s/kill-after 1s:

```text
/usr/bin/mkfifo --mode=0600 /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/logs/identity.fifo
```

Record metadata-only `lstat`: exact path and ancestor identities, type FIFO,
mode 0600, owner, device/inode, link count, size and timestamps. Never open,
read, follow or hash the FIFO, including during final tree inventory. Hashing
serialized metadata is permitted and is never a FIFO-content hash. Never use
a generic content-hash walker on R. Do not replace/unlink FIFO during supervision.
Only the declared cat and the sole dd may open it; the controller never opens
it, including read-write or for a probe. Mode 0600 provides no isolation from
another process of the same UID; the execution trust boundary assumes no
unrelated same-UID interference. Any observed extra opener or identity change
is failure, not a claim that mode bits prevent it.

Exclusively create mode-0600 regular
`/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/logs/identity.token`
with exactly byte 0x41, fsync and close it. Require size 1 and SHA256
`559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd`.
Record its full identity. This is data; there is no marker-file authorization.

## Exact tools and input provenance

For each tool, record resolved path, complete symlink chain, type, mode, UID/GID,
device/inode, size and matching expected SHA256 before execution and after
cleanup. Reject a mismatch. GCC 9 and systemd 245 are the reviewed versions.

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
| `/usr/bin/cat` | `87e5bd81850e11eeec2d3bb696b626b2a7f45673241cbbd64769c83580432869` |
| `/usr/bin/dd` | `944e841180d21c3d60b079bd3e4a4b804d528cee289717c10390c7c0180825fa` |
| `/usr/bin/mkfifo` | `701473b4e6883abe695f287feefea5f877d26c0aca460960a1d5b1673f5ab878` |
| `/usr/bin/sync` | `7ecb2f99a697aa0d3c4eeeedde02a76d30139def1f85401b388a256a6079028f` |

Build a finite non-following lstat baseline of exactly
`/usr/lib/gcc/x86_64-linux-gnu/9/include`, `/usr/include/x86_64-linux-gnu`, and
`/usr/include`. Retain every spelling, canonical identity, complete component
resolution, mode/owner/device/inode/size/hash for regular files; retain literal
targets and resolution hops for symlinks. Deduplicate overlapping entries only
after retaining every spelling. Never recurse a symlink directory. Record
external directory links as EXCLUDED_EXTERNAL_DIRECTORY_LINK, and broken/loop
links without following them. Their existence alone is not failure; consuming
them is. Inventory/stat/hash errors fail preflight. Pin S separately with the
same complete identity; it is not part of the header baseline.

## Complete single-submission argv

The following JSON array is the literal argv authority, not a shell script.
It copies packet10's submission/main arguments with root12/unit substitutions,
changes only TimeoutStartSec to 120s, and adds `--no-block` and exactly one cat
ExecStartPre. The explicit `--no-block` supersedes packet10's blocking client:
without it the client would wait on the FIFO that this observer must release.
No packet18/19 sleep, test, marker, mv or publication sequence participates.

```json
[
  "/usr/bin/timeout", "--signal=TERM", "--kill-after=1s", "10s",
  "/usr/bin/systemd-run", "--user",
  "--unit=layer-b-native-owner-bootstrap-20260928-12-5a3a3fe8-03a9-4dc6-86fc-9666747decc4.service",
  "--service-type=exec",
  "--working-directory=/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12",
  "--property=RemainAfterExit=yes", "--property=Restart=no",
  "--property=KillMode=control-group", "--property=RuntimeMaxSec=60s",
  "--property=TimeoutStartSec=120s", "--property=TimeoutStopSec=5s",
  "--property=SendSIGKILL=yes", "--property=UMask=0077",
  "--property=StandardInput=null",
  "--property=StandardOutput=file:/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/logs/unit.stdout",
  "--property=StandardError=file:/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/logs/unit.stderr",
  "--no-block",
  "--property=ExecStartPre=/usr/bin/cat /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/logs/identity.fifo",
  "--", "/usr/bin/env", "-i", "LC_ALL=C", "LANG=C",
  "HOME=/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/home",
  "TMPDIR=/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/tmp",
  "PATH=/usr/bin:/bin", "/usr/bin/prlimit", "--core=0:0", "--cpu=55:55",
  "--nofile=256:256", "--fsize=67108864:67108864", "--as=536870912:536870912",
  "--", "/usr/bin/gcc", "-v", "-std=c11", "-O2", "-Wall", "-Wextra",
  "-Werror", "-fno-pie", "-pthread", "-nostdinc", "-isystem",
  "/usr/lib/gcc/x86_64-linux-gnu/9/include", "-isystem",
  "/usr/include/x86_64-linux-gnu", "-isystem", "/usr/include",
  "-save-temps=obj", "-MD", "-MF",
  "/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/layer_b_native_owner_v1.d",
  "-MT",
  "/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/layer_b_native_owner_v1.o",
  "-c", "/home/holden/mckernel/scripts/tests/layer_b_native_owner_v1.c", "-o",
  "/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/layer_b_native_owner_v1.o"
]
```

Retain this array and the actual executed array byte-for-byte. Pinned systemd-run
and the independently reviewed v245 property parser establish the one-property
argument boundary. Rendered `ExecStartPre`/`ExecStart` are corroboration only;
require exactly this cat without ignored failure and exactly this main command.
Do not claim a space-joined show response proves argv boundaries. No shell,
response file, plugin/specs, make/configure, controller import, second source,
linker/collect2/CRT, target library, container, mount, root/sudo, credential,
network or owner execution is allowed. `-pthread` is compile-only here.

## Submission-anchored timing and identity barrier

Use CLOCK_MONOTONIC throughout. State sequence is PRECHECK, SUBMIT_ONCE,
PRE_ACK, WRITER_INITIATED_POSSIBLE_COMPILER, POST_ACK, CLEANUP, EVIDENCE, terminal.
Immediately before the sole submission record t0, ack_deadline=t0+90s and
observation_deadline=t0+180s. Preflight does not start these clocks. Submission
has the exact 10s nominal timeout plus 1s client-kill allowance; nonzero,
timeout or ambiguity latches failure and enters cleanup of U without retry.

Before **every** pre-ack operation, including submission, query, mapping reads,
evidence persistence, sync, metadata recheck and any polling wait, require
`now + full_operation_timeout_and_kill_envelope <= ack_deadline`.
Never start an operation with an unbounded envelope. Queries, mapping/metadata
snapshots and evidence persistence each have a 2s nominal/1s termination
envelope; evidence persistence must report successful fsync/close within it.
Stop processing on overrun even if a late result appears valid. Poll waits are
at most 100ms and must fit too. Post-ack operations use the same fit rule against
observation_deadline. Insufficient time fails closed and enters cleanup.
These bounds do not guarantee recovery from uninterruptible host I/O or stalls.

Every external control command uses a literal argv with the pinned timeout
prefix `/usr/bin/timeout --signal=TERM --kill-after=1s`; never a shell. Q is the
following query with U replaced by the exact unit string above before retention
and execution, nominal timeout 2s plus 1s kill allowance:

```text
/usr/bin/systemctl --user show U -p Id -p LoadState -p ActiveState -p SubState -p Result -p ExecMainCode -p ExecMainStatus -p InvocationID -p ControlGroup -p MainPID -p ControlPID -p ExecStartPre -p ExecStart -p ExecMainStartTimestamp -p ExecMainExitTimestamp -p ExecMainStartTimestampMonotonic -p ExecMainExitTimestampMonotonic
```

Before acknowledgement require loaded/activating/start-pre, Id=U, nonzero
InvocationID, nonempty ControlGroup, nonzero ControlPID, MainPID=0 and unstarted
main (zero monotonic start/exit timestamps and rendered main unstarted). Require
exactly one expected running cat pre-command, its exit not yet recorded, and
the exact rendered main. Recursively map the original ControlGroup through
`/proc/self/mountinfo` and `/proc/self/cgroup`, retaining both raw mappings,
hierarchy and accessible parent identities, descendant `cgroup.procs`, and the
ControlPID's membership in that mapped group. Record read-only process identity
to corroborate the expected cat; a numeric PID is never signal authority.
Retain unit/InvocationID/original ControlGroup, root/nonce/packet/review hashes,
FIFO/token metadata, query raw bytes, mappings and monotonic times in regular
evidence files under R/logs. Fsync and close them successfully. Run exactly:

```text
/usr/bin/timeout --signal=TERM --kill-after=1s 2s /usr/bin/sync -f /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/logs
```

The syncfs operation must succeed within its admitted 3s envelope. Then make
a fresh Q and mapping/membership/metadata check immediately before release;
require the same complete prebound tuple and pre-ack predicate, unchanged FIFO
and token, and no intervening productive operation. Persist the fresh response
as evidence. Immediately before launching dd require **`now + 3s <=
ack_deadline`**. If false, clean up without opening FIFO. Missing/ambiguous
identity, query failure, changed hierarchy, premature cat/main completion,
unbound empty group, timeout or discrepancy fails closed without a writer.

## Single writer and post-ack observation

Launch exactly once, as literal argv (paths already substituted):

```text
/usr/bin/timeout --signal=TERM --kill-after=1s 2s /usr/bin/dd if=/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/logs/identity.token of=/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/logs/identity.fifo bs=1 count=1 status=none
```

No iflag, extra writer/opener, echo/printf/tail, alternate cat, timeout widening,
regular-file replacement or repeated acknowledgement is permitted. Record raw
argv/streams/status and monotonic start/end. Writer initiation is the one-way
POSSIBLE_COMPILER boundary: cat may exit successfully on EOF even if no byte
arrives; it authenticates neither byte value nor length. Any writer failure,
timeout, ambiguous/disappeared result, unexpected transfer evidence or overrun
must assume gcc may have started, latch failure and enter cleanup. Never retry
to repair an acknowledgement. For success require writer exit 0, unchanged
one-byte token identity/hash, cat exit 0 and the independent main predicate.

Post-ack Q may observe the same identity in activating/start-pre while cat
finishes, activating/start during main startup, or active/running. These are
pending only after writer initiation. No post-ack state may retroactively prove
the pre-ack barrier. Each nonempty ControlGroup must equal the original mapping;
Id and InvocationID must stay fixed. Inspect no compiler artifacts while
observing. Record cat CLD_EXITED/status 0 separately from main status.

The exact packet10 terminal predicate is **active/exited, Result=success,
ExecMainCode=1/CLD_EXITED, ExecMainStatus=0 and a nonzero exit timestamp**
(including monotonic exit). Require cat success, writer success and stable
prebound identity as additional predicates. Capture this complete response and
enter cleanup immediately, without waiting for the observation deadline.
Terminal ControlGroup may be empty only with matching prebound Id/InvocationID
and subsequent reconciliation of the original path; an empty unbound identity
is FAIL_UNRESOLVED. Unexpected state, abnormal/pre-command exit, query timeout,
changed identity or observation deadline expiry latches failure and cleanup.

## Independent cleanup and static-only evidence

Every submitted outcome gets a new independent 30s cleanup deadline C. Every
cleanup operation must fit its full timeout/kill envelope before C. Normal
completion immediately issues `/usr/bin/systemctl --user stop U`, nominal 7s
plus 1s kill allowance. Failure first takes one best-effort Q (2s+1s), then the
same stop. Preserve first failure before all subsequent cleanup errors. Stop
timeout/nonzero, ambiguous/timed-out post-stop query, residual activating/
running/deactivating state or nonempty original cgroup requires the separate
manager-side command, even if state cannot be read:

```text
/usr/bin/systemctl --user --signal=SIGKILL --kill-who=all kill U
```

Kill has nominal 2s plus 1s client allowance. Reserve sufficient cleanup budget
for this fallback; a client timeout signal never replaces manager-side kill.
Continue bounded Q and recursive original-path cgroup reconciliation within C.
Require loaded/inactive, or after a successful recorded stop unloaded/not-found;
require the original group recursively empty or absent beneath the same
accessible, identity-matching parent hierarchy. Do not require both inactivity
and absence. MainPID=0 alone never proves cleanup. Capture failed status before
`/usr/bin/systemctl --user reset-failed U` (2s+1s); reset only a resolved failed
unit, then final Q. Never reset unresolved evidence or treat reset as cleanup.

Unreachable manager, uncertain late submission, identity change, residual or
uninspectable cgroup, or exhausted C is FAIL_UNRESOLVED. Retain root and owner
identity; no numeric-PID signal, second unit/submission/writer, retry, deletion
or reuse is allowed. Preserve all failures and original roots. Manager/host
failure or uninterruptible I/O can exceed these bounds and stays unresolved.

Only after successful compilation **and resolved cleanup**, authenticate
source/test/tool pre/post identities, and parse B.d as exactly one Make rule
with target B.o. Implement LF/backslash-newline and escaped space/backslash/hash/
dollar handling; reject malformed escapes, extra rules/targets or incompatible
duplicates. Retain original spellings and component chains when canonicalizing.
Require exactly one source occurrence equal to S and its pinned pre/post
identity. Every other prerequisite must be a baseline header beneath an approved
root, with entire unchanged component chain and final regular file inside those
roots. Reject excluded external links, broken/cyclic/changed/missing entries,
third classes and any prerequisite under R. Outputs are never exempted inputs.

Parse R/logs/unit.stderr (not the client stderr) for the exact pinned cc1 and
assembler, controlled include search and S -> B.i -> B.s -> B.o. Reject ld,
collect2, unexpected commands, external plugins/specs or persistent paths.
Hash generated B.i/B.s/B.o/B.d and inventory surviving R/tmp entries. Record
disappearing GCC scratch paths as ephemeral without invented hashes. The .d/-v
evidence is prerequisite/driver evidence, not a full file-open trace or runtime
library audit. Compiler process libraries are environment dependencies; target
link libraries are not consumed.

Run only these nonexecuting object inspections, each nominal 5s plus 1s kill:

```text
/usr/bin/readelf -h -S -s /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/layer_b_native_owner_v1.o
/usr/bin/objdump -f /home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12/layer_b_native_owner_v1.o
```

Require ELF64 x86-64 ET_REL. Never link or execute it. After supervision cleanup
capture `/usr/bin/journalctl --user -u U --no-pager -o short-monotonic` under a
separate 5s+1s bound on success or failure. Retain actual expanded command arrays,
environment/unit properties, all control streams/statuses/times, pre-stop
terminal response, prebound identity and mappings, FIFO metadata-only records,
token and artifact hashes, compiler streams, dependency parse, private tmp and
full type-aware output inventory, repository status, capacities/limits and
zero-residual evidence. Never content-hash the FIFO during retention.

`failure.json` immutably identifies the earliest failure; later cleanup/evidence
errors are separate append-only records. At first productive failure stop
compile/inspection work, finish bounded cleanup and preserve/archive the root
without deleting it. Success proves one exact preprocess/cc1/assembler path to
a relocatable object under the recorded owner. It proves no owner runtime,
native/kernel/guest behavior, M02/M03 admission, application case, production,
language or whole-OS acceptance. Independent final review remains required.
