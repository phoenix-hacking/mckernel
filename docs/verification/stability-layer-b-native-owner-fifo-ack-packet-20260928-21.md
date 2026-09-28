# Layer-B native-owner FIFO acknowledgement packet 21

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This packet is the fresh
FIFO-acknowledgement strategy selected after the PASS_FIFO_STRATEGY result.
It releases no execution by itself. It permits, after an independent PASS on
these exact bytes, one compile-only attempt in a fresh root12. It never releases
linking, owner execution, tests, M02/M03 work, guest/root work, or acceptance.

## Immutable inputs and failure history

The exact source is `/home/holden/mckernel/scripts/tests/layer_b_native_owner_v1.c`,
SHA256 `2c157335e88b2088c56fc40fd6c0d966dc653ea68b4726e51feb1d4b4e62eafc`.
The source-model test is
`/home/holden/mckernel/scripts/tests/test_layer_b_native_owner_source.py`,
SHA256 `427f6133497ce0706fce39d9e52051542821bc6deab29d27322733c927efd63d`.
The exact reviewed lineage is retained and must be hash-checked before any
preflight: packet10 `b65c345bc8b15e6043bf0ae728d23e0cba895dcfbf3ad383160011094900acbd`;
correction11 `c5966dd64e8d38857433f2c9bbdd0b4a41793e40535f9d32a20a35af03519604`;
direct15 `73ed242336988f5f66bb65db7fc81f85e742ff197552047f74b7ec9b3ac4f100`;
packet18 `f30561ea725dfd5afb3ecfef43c24d46b3f98c0e4b8c2dbd95dbc894e2df3375`;
correction19 `0623f94b2da690f79a7cbb00dc3d013f897305c6d21954c50e33e9c03e2f19a8`;
review20 `0261ed3606e2d2250b68018ef676c6ce8953ff09a464803d7af95c9db460aa0d`.
The preserved failure records are attempt10
`8c5437e98d4e98640560d6085927371846cb331fc7d7a2f69d94fe3ed5b95d99`,
attempt11 `47d8832f918cb98b35a71eea0e517e392474c3737d953b1939a6a8abf6c1455`,
and review failure18
`a8f6564216ac1005a6ab7dcc2cfaa59563a287c95f77a578d7c691dc68aeef05`.
Their failures remain immutable: prior identity observation/cleanup failures
are not compile attempts to be erased or retried.

The exact latest FIFO strategy result, status `PASS_FIFO_STRATEGY`, its path,
SHA256, and the independent review identity must be recorded in the dispatcher
manifest before release. If that result cannot be located or its hash/status
does not match, this packet is not executable. The fresh canonical root is
`/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-20260928-12`;
it and the literal unit
`layer-b-native-owner-bootstrap-20260928-12-<crypto-nonce>.service` must be
absent before exclusive mode-0700 creation. Generate one cryptographic nonce,
record it once, and never reuse it.

## Preflight and literal FIFO/token setup

Use only `lstat`-based, non-following inventories. Rebuild correction11's
complete baseline for exactly `/usr/lib/gcc/x86_64-linux-gnu/9/include`,
`/usr/include/x86_64-linux-gnu`, and `/usr/include`; retain every spelling,
symlink hop, excluded external-directory link, regular-file identity and hash.
Authenticate source, all packet inputs, root ancestry, UID/GID, capacities,
limits, and every selected tool. Do not create units, FIFOs, compiler outputs,
imports, tests, or scratch files before this check. The root, `home`, `tmp`,
`logs`, `fifo`, and `token` paths must have no symlink component.

After preflight create only the root subdirectories and the literal FIFO
`R/logs/ack.fifo` with mode 0600 using the pinned `/usr/bin/mkfifo`; hash and
record its `lstat` identity. Create a mode-0600 regular one-byte token source
`R/logs/ack.token` containing exactly byte `0x41` (`A`), fsync/close it, and
record SHA256 `559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd`.
The token is data, not authorization. No process other than the one declared
`ExecStartPre` reader and the single bounded writer may open either FIFO path;
reject any extra opener, reader, writer, descriptor, link, or pre-existing
entry. Pin `/usr/bin/mkfifo` and the exact resolved `/usr/bin/cat`, `/usr/bin/dd`
hashes in the manifest; any mismatch is preflight failure.

## Exact one-shot service and acknowledgement order

Use packet18/19's literal systemd-run argv, root12 substitutions, `--no-block`,
and the unchanged packet10 `env -i`/`prlimit`/gcc main command. Add exactly one
`ExecStartPre` element, and no other opener:

```text
--property=ExecStartPre=/usr/bin/cat R/logs/ack.fifo
```

It is one argv element. No shell, response file, command substitution, import,
second unit, second FIFO, or alternate cat invocation is allowed. Pin the full
argv and rendered `ExecStartPre`/`ExecStart` with systemd v245 parser/hash
evidence. `cat` must block on the FIFO until the writer supplies exactly one
byte, then exit 0; EOF, short/long data, nonzero status, premature return,
extra opener, or any other pre-command status is failure and must prevent gcc.

After the preflight identity query passes, run exactly one bounded writer:

```text
/usr/bin/timeout --signal=TERM --kill-after=1s 5s /usr/bin/dd if=R/logs/ack.token of=R/logs/ack.fifo bs=1 count=1 iflag=fullblock status=none
```

The writer may be initiated only after the observer has retained the valid
prebound unit tuple and the `cat` pre-command is demonstrably pending. A
possible compiler/writer initiation race is a `POSSIBLE_COMPILER` result, not
permission to retry; preserve all statuses and stop. Do not open the FIFO in
the controller, use `echo`, `printf`, `tail`, a shell, a second `dd`, or a
regular-file substitution. Record writer raw argv, streams, status and
monotonic times, then requery the same unit and require the exact prebound
identity, `cat` status 0, main status 0 and normal completion.

## Timing, observation, cleanup and evidence

Use `CLOCK_MONOTONIC`. The sole submission is bounded by
`/usr/bin/timeout --signal=TERM --kill-after=1s 10s`; `TimeoutStartSec=120s`.
Set the observation deadline immediately before submission to 180 seconds and
the acknowledgement/writer observation window to 90 seconds. No blocking
submission and no retry. Poll with the packet18 expanded `systemctl --user show`
query, retaining raw responses, `ExecStartPre`, `ExecStart`, InvocationID,
ControlPID, ControlGroup, mountinfo/cgroup mappings and recursive `cgroup.procs`.
The only pending state is the prebound activating/start-pre state. A missing,
changed, ambiguous, empty-unbound, timed-out or late identity fails closed.

On every outcome enter the independent 30-second cleanup. Stop the exact unit;
on timeout, ambiguity, residual activation/running/deactivating state, or
nonempty original cgroup issue the manager-side `systemctl --user
--signal=SIGKILL --kill-who=all kill U`. Reconcile the original path through
the recorded hierarchy and require it empty/absent with accessible parents.
Never signal a numeric PID, reset unresolved evidence, delete the root, or
start another unit. Capture statuses before any permitted reset-failed.

Retain raw command JSON/argv, all stdout/stderr, timestamps, FIFO/token
identities and hashes, cat/pre/main/writer statuses, exact unit definition,
compiler streams, source/header pre/post hashes, dependency parse, output tree,
private tmp inventory, journal, limits/capacity, and zero-residual proof.
An empty terminal cgroup condition is valid only with a stable prebound tuple
and successful cleanup; otherwise it is `FAIL_UNRESOLVED`.

Only on full success (cat=0, writer=0, main=0, exact identity, cleanup
resolved, all pre/post inputs unchanged) may `readelf -h -S -s` and `objdump -f`
inspect the output object. Require ET_REL x86-64 and perform dependency/object
static inspection only; never execute or link. The `.d` partition and exact
cc1/assembler chain remain packet15's rules. This packet produces no acceptance
credit and remains pending independent review.
