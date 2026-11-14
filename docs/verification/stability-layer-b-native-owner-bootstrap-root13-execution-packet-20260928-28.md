# Layer-B native-owner bootstrap: root13 execution packet

Status: **READY_FOR_REVIEW**.  This is the one fresh
root13, compile-only attempt unlocked by `PASS_SOURCE`.  It does not authorize
recursion, runtime, linking, owner execution, guests, compiler/systemd tests,
or application acceptance.  No command is executed by preparation of this
packet.  Base worktree: `c5d95e1cda88d6300ebf9d05bdcde69baf681887`.

## Release gate, bindings, and history

Execution requires an independent review whose exact release is recorded
against this file's final SHA256.  The source-review authority is
`PASS_SOURCE`; it binds the exact observer and supplied tests below.  Preserve
and authenticate these before creating the fresh root:

| item | SHA256 |
|---|---|
| `scripts/tests/layer_b_systemd_cgroup_observer.py` | `2f18755073ef3c33b4df9178f708187d344a50b03240b0fb7ce51a1d2c87e5bc` |
| `scripts/tests/test_layer_b_systemd_cgroup_observer.py` | `ce6ebd78da99c45e5caccc5c87cf6423ee1738ae884c5dd9c5bf3745a8c371c9` |
| packet24 `stability-layer-b-native-owner-fifo-ack-expert-packet-20260928-24.md` | `ebc8778cda8d667c40b26362e4540e68a7217b0e7110526d31b7d2bf1c7a13a5` |
| packet24 review25 | `PASS_FIFO_EXECUTION_PACKET` |
| root12 failure record | `stability-layer-b-native-owner-bootstrap-failure-20260928-12.json` |
| root12 failure review26 | `stability-layer-b-native-owner-bootstrap-failure-review-20260928-26.json` |
| source review27 | `stability-layer-b-systemd-cgroup-observer-source-review-failure-20260928-27.json` |
| bounded collector | `scripts/tests/layer_b_systemd_cgroup_collector.py` (`f96768d899b784ac3370be98644816c34c797b2623a87eb87d61329a3517c480`) |
| bounded collector tests | `scripts/tests/test_layer_b_systemd_cgroup_collector.py` (`13b28e23845be813efd57a5e4bdafacb48f8ffdc79cad220c976a243a10cd5be`) |
| root12 archive | `82574a70f22300c92fc01b1a5caaab39c3540b85e780d4b6974d8007fa312056` |
| current policy START | `1698d342...` |
| current policy CONVERGENCE | `f6938bd2...` |

Root12, packet24, review25, record27, correction/source-review history, all
failure evidence and the root12 archive remain immutable.  Root12's defect was
incorrectly joining `/sys/fs/cgroup` instead of the actual `name=systemd`
hierarchy at `/sys/fs/cgroup/systemd`; review26 also requires original-path
reconciliation and preserved parent identities.  Review27's five findings are
closed only by the exact observer bound above: opaque non-cgroup roots are
accepted, an external sibling observer is allowed, mount-root offsets are
applied exactly, cgroup bytes are preserved, and covering/stacked mounts fail.

## Fresh identities and scope

Use only these fresh identities; never reuse root12 names or artifacts:

* root `R=/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-root13-20260928-28`;
* unit `U=layer-b-native-owner-bootstrap-root13-20260928-28-<fresh-UUID>.service`;
* output prefix `R/layer_b_native_owner_v1`; FIFO `R/logs/identity.fifo`;
* token `R/logs/identity.token`; logs and evidence only below `R/logs`.

Generate the UUID once from `/proc/sys/kernel/random/uuid`, retain its exact
bytes before submission, and reject any existing root, unit, output, FIFO or
token.  Create only mode-0700 `R`, `R/home`, `R/tmp`, and `R/logs`, owned by
the current UID, with canonical non-symlink ancestry.  No repository file is
writable.  Record UID/GID, affinity/limits, leases, host/scratch capacity and
retain at least 16 GiB host and 12 GiB scratch free (or the larger active
capture requirement).  No link, owner, guest, runtime, or systemd operation
beyond the explicit allowlist below is in scope.

## Exact packet24 execution contract, with root13 substitutions

All packet24 tool hashes, include-root inventory rules, environment, resource
limits, FIFO/token rules, compiler command, systemd properties, deadlines,
single-writer barrier, ET_REL-only inspections, evidence and cleanup rules are
copied verbatim by reference, with every packet24 root and unit substituted by
the exact fresh `R` and `U` above.  The following is the literal submission
argv authority (JSON array; no shell, response file, wrapper, second source,
linker, CRT, target library, plugin, make/configure, mount, root/sudo,
container, network, owner or guest command):

```json
["/usr/bin/timeout","--signal=TERM","--kill-after=1s","10s","/usr/bin/systemd-run","--user","--unit=U","--service-type=exec","--working-directory=R","--property=RemainAfterExit=yes","--property=Restart=no","--property=KillMode=control-group","--property=RuntimeMaxSec=60s","--property=TimeoutStartSec=120s","--property=TimeoutStopSec=5s","--property=SendSIGKILL=yes","--property=UMask=0077","--property=StandardInput=null","--property=StandardOutput=file:R/logs/unit.stdout","--property=StandardError=file:R/logs/unit.stderr","--no-block","--property=ExecStartPre=/usr/bin/cat R/logs/identity.fifo","--","/usr/bin/env","-i","LC_ALL=C","LANG=C","HOME=R/home","TMPDIR=R/tmp","PATH=/usr/bin:/bin","/usr/bin/prlimit","--core=0:0","--cpu=55:55","--nofile=256:256","--fsize=67108864:67108864","--as=536870912:536870912","--","/usr/bin/gcc","-v","-std=c11","-O2","-Wall","-Wextra","-Werror","-fno-pie","-pthread","-nostdinc","-isystem","/usr/lib/gcc/x86_64-linux-gnu/9/include","-isystem","/usr/include/x86_64-linux-gnu","-isystem","/usr/include","-save-temps=obj","-MD","-MF","R/layer_b_native_owner_v1.d","-MT","R/layer_b_native_owner_v1.o","-c","/home/holden/mckernel/scripts/tests/layer_b_native_owner_v1.c","-o","R/layer_b_native_owner_v1.o"]
```

`R` and `U` above are textual placeholders resolved once to the retained
absolute paths/UUID; the rendered array and executed array must be retained
byte-for-byte.  Packet24's exact tool pins include GCC 9, systemd 245.4,
`timeout`, `systemctl`, `journalctl`, `readelf`, `objdump`, `cat`, `dd`,
`mkfifo`, `sync`, `env`, `prlimit`, `as`, and `cc1`; reject any hash/path
mismatch.  Compile resources are exactly `--cpu=55:55`, `--nofile=256:256`,
`--fsize=67108864:67108864`, `--as=536870912:536870912`, core disabled, and
the sanitized environment above.  Header baseline is exactly the three
packet24 include roots, non-following and identity-complete.

Create the FIFO with exactly `/usr/bin/timeout --signal=TERM --kill-after=1s
2s /usr/bin/mkfifo --mode=0600 R/logs/identity.fifo`; metadata-only lstat is permitted, never
open/hash its contents.  Create a regular 0600 one-byte `0x41` token, fsync
and close it; require SHA256
`559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd`.

## Observer-integrated preflight and acknowledgement

The observer is an exact source component, not a test oracle replacement.  Run
its pure parser only under the separately released `PASS_SOURCE` scope.  Before
submission, read real `/proc/self/mountinfo` and `/proc/self/cgroup` as raw
bytes and retain hashes, complete records, mount IDs/parents/roots/mountpoints,
and the `name=systemd` controller row.  Resolve `U`'s nonempty
`ControlGroup` using `resolve_systemd_mapping`; require exactly one cgroup
mount with `name=systemd`, exact mount-root containment, no covering/stacked
mount, and a reachable mapped filesystem path.  The observer may be a sibling:
independently read the ControlPID cgroup and require
`verify_pid_membership` for the mapped original ControlGroup.  Retain raw and
decoded mapping, mount/device/inode, every accessible parent identity, and
the original ControlGroup path.  Numeric PIDs are observation data only, never
signal authority.

Use CLOCK_MONOTONIC.  Immediately before submission set `t0`, ack deadline
`t0+90s`, observation deadline `t0+180s`; each pre/post-ack operation has a
2s nominal plus 1s kill envelope and must fit its deadline, with polls <=100ms.
The exact packet24 `systemctl --user show` property list is required.  Require
loaded/activating/start-pre, Id=U, InvocationID, nonempty ControlGroup,
ControlPID membership, MainPID=0, unstarted main, one expected cat, unchanged
FIFO/token and exact rendered main.  Persist evidence with fsync/close and run
the exact packet24 `sync -f R/logs` command before a fresh mapping query.

Only if the complete pre-ack tuple remains valid and `now+3s<=ack_deadline`
may the sole writer run:

```text
/usr/bin/timeout --signal=TERM --kill-after=1s 2s /usr/bin/dd if=R/logs/identity.token of=R/logs/identity.fifo bs=1 count=1 status=none
```

Writer initiation is the irreversible possible-compiler boundary.  Any writer
error, timeout, ambiguity, changed mapping, premature cat/main completion or
deadline overrun fails closed; never retry.  Post-ack observation requires the
same unit/invocation and original mapping while recursively retaining
`cgroup.procs`, ControlPID membership, device/inode and parent identities.
Success additionally requires cat and writer status 0 and packet24's exact
terminal predicate: active/exited, Result=success, CLD_EXITED/0 and nonzero
exit timestamp.

## Cleanup, evidence, and independent review

Every outcome gets a new independent 30s cleanup deadline.  On a productive
failure, first preserve the first-failure record and raw evidence, perform one
best-effort bounded query, then immediately issue packet24's bounded
`systemctl --user stop U`; do not continue compile/inspection work.  On
success, issue that bounded stop immediately.  On stop timeout/nonzero,
residual state, residual membership, or ambiguity use the manager-side
`systemctl --user --signal=SIGKILL --kill-who=all kill U` fallback, then perform
bounded stop/reconciliation queries.  Capture stop/KILL statuses before
reset-failed; reset only a resolved failed unit and retain final query.  After
supervision cleanup (for either success or failure), capture the bounded
packet24 `journalctl --user -u U` result and journal status as a separate
operation.  Never signal a numeric PID, delete/reuse a root, or retry a
submission/writer.  Unresolved manager, uninspectable cgroup, residual
process, or exhausted deadline is `FAIL_UNRESOLVED`.

On the first productive failure stop compile/inspection work immediately,
retain the first-failure record before cleanup errors, archive/log all raw
membership and control-file evidence, and preserve the root.  Only after
successful compile and resolved cleanup may the packet24 dependency parser,
compiler-stream audit, hashes, and `readelf`/`objdump` ET_REL checks run;
journal capture follows supervision cleanup on every outcome, including
compile failure.  Retain the actual argv/environment/properties, mappings,
device/inode/parents, FIFO metadata without content hashing, token/artifact
hashes, statuses/times, capacities/limits and zero-residual evidence.  An
independent execution review must verify this exact document and final hash
before any execution; preparation itself performs no execution.

## Bounded correction: recursive observation and failure ordering

The collector is pure and consumes only the immutable `Mapping` returned by
`resolve_systemd_mapping`; it performs no reads, writes, systemd calls, or
normalization of supplied pathname bytes. Every recursively observed directory
and control-file path must be under the selected mount and have no descendant
or individual-file covering mount. Opaque mappings and changed mount
ID/root/mountpoint/parent topology fail closed. The original mapping and raw
path bytes remain in evidence after terminal `ControlGroup=` becomes empty.
Pre-command ControlPID membership is live membership; terminal `ControlPID=0`
and an empty group are accepted only with that retained original mapping. A
replaced/nonempty mapping is rejected.

Only the user-manager `systemd-run` submission above, exact
`systemctl --user show` queries, bounded `systemctl --user stop`, manager-side
`systemctl --user --signal=SIGKILL --kill-who=all kill` fallback, bounded
queries, and `reset-failed` after resolved cleanup are permitted. On a first
productive failure, persist the first-failure evidence (not a delayed journal),
perform one best-effort query, then issue bounded stop; do not continue
compile/inspection work. On success issue bounded stop immediately. After
supervision cleanup, capture the packet24-bounded journal on both compile
success and compile failure. Recursive cleanup deadlines and
`FAIL_UNRESOLVED` remain unchanged. This correction is ready for independent
review only and authorizes no execution.

### Collector contract (root13 immutable baseline)

`accept_observation()` receives the exact `Mapping`, complete immutable
`Entry` tuples for the target subtree, and complete immutable `Entry` tuples
for every filesystem parent through the selected mountpoint. Each directory
listing must account for every child (including `cgroup.procs`), each regular
control file is identity-checked, and every `cgroup.procs` read is retained as
raw bytes and parsed into positive numeric PIDs. The accepted result retains
the selected controller record, its complete mount-parent chain, target and
parent device/inode identities, raw paths, and the pre-command PID tuple.

`collect_recursive_observation()` revalidates the same target/parent records
and mount chain. With `require_retired=False` it is only a live
pre/post-ack observation and requires the original nonempty
`ControlGroup`; it reports current recursive membership. With
`require_retired=True` it accepts either the same original tree (which must
have no members) or a complete nearest-parent listing proving target absence;
an empty/sibling-only walk, changed parent topology/root/controller, ancestor
overmount, descendant/file overmount, identity replacement, or nonempty
replacement `ControlGroup` fails closed. The terminal result always retains
the original mapping and accepted identities, even when `ControlGroup=` is
empty.

The only permitted manager operations are the literal packet24
`systemd-run --user` submission, exact bounded `systemctl --user show`
queries, bounded `systemctl --user stop`, manager-side
`systemctl --user --signal=SIGKILL --kill-who=all kill` fallback, bounded
follow-up queries, and `reset-failed` only after resolved cleanup. On either
compile success or compile failure, retain the complete success/failure
status; after supervision cleanup, capture the corresponding
`journalctl --user -u U` result (with query-before-stop evidence already
retained on a productive failure). Cleanup errors never replace the first-failure record; unresolved
manager or cgroup state remains `FAIL_UNRESOLVED`.
