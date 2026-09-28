# Native current-signal diagnostic execution packet 4

Status: draft for independent execution release; no execution has been performed.
This one-shot packet is bound to pushed and fetched-blob-verified commit
`778102e6f6ad594889e856969ac1d1f5e7d251de`. It does not inherit any prior
packet's release and must not be retried after an uncertain or failed attempt.

## Exact owner, attempt and command

Owner source `scripts/application-tests/native_diagnostic_container_owner.py`
has SHA-256 `9edd23ab1d579f4c96b4d1d080a989bc5acf6797170f841b16bd42865a9bba87`.
The never-used parent is
`/home/holden/mckernel-work/scratch/ndcs-20260928-4`; it must be absent during
review, then created once as uid/gid 1000 and mode 0700 only after release.
The nonce is `e8e0bd60422a94a18680321317786bee`.

The only released outer command may be:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndcs-20260928-4 --nonce e8e0bd60422a94a18680321317786bee --owner-sha256 9edd23ab1d579f4c96b4d1d080a989bc5acf6797170f841b16bd42865a9bba87
```

The inner attempt path is
`/home/holden/mckernel-work/scratch/ndcs-20260928-4/attempt-e8e0bd60422a94a18680321317786bee`;
the root-owned outer evidence sibling is
`/home/holden/mckernel-work/scratch/ndcs-20260928-4.owner-e8e0bd60422a94a18680321317786bee`.
The exact QMP path is
`/home/holden/mckernel-work/scratch/ndcs-20260928-4/attempt-e8e0bd60422a94a18680321317786bee/qmp.sock`;
it is 100 bytes in the C locale, below Linux's 107-byte usable pathname limit.
Recheck all three paths immediately before setup. The packet-3 parent, all old
parents, and all old nonces must not be reused.

## Immutable source and artifact closure

The strict manifest is
`/home/holden/mckernel-work/scratch/native-diagnostic-manifest-20260928-3/manifest.json`,
SHA-256 `ab2905811ae10eda6ba6d4ca7d023b0cc50fdaa7520968e45c2b41c733a1ecc6`,
4473 bytes, mode 0600. It was read through the actual owner `bound_manifest()`
and independently reviewed. It binds paths, modes, sizes and digests; no input
may be substituted or regenerated.

| Runtime source | SHA-256 |
|---|---|
| `native_diagnostic_container_owner.py` | `9edd23ab1d579f4c96b4d1d080a989bc5acf6797170f841b16bd42865a9bba87` |
| `native_diagnostic_runner.py` | `25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499` |
| `native_diagnostic.py` | `a8017956af1424736a88be15ce7a38db5fe0e0f1f33e1eea006a6b38b4f7f392` |
| `native_diagnostic_backend.py` | `41bf970ac1f2a7969651eca8d8138c4104b6d3951985d9bf4117a099d6e8a034` |
| `qmp_capture.py` | `5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741` |
| `native_diagnostic_overlay.py` | `a2d811c1c051644c1b91b4691a0224b96cfaf9572134e3f67800dd01ffc6ac47` |

| Manifest role | SHA-256 | Size | Mode |
|---|---|---:|---:|
| Linux `bzImage` | `b6cbd689108f499d37ba8d3768f2cdd6cb0f3422d93a4e091af93680686e94eb` | 16130048 | 0644 |
| base `initramfs` / `root_base` | `c7957431335818d1cf448bb0ae24efb5193bbfa226885787ff5311bea45b4265` | 11803083 | 0644 |
| guest loader | `0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b` | 930600 | 0755 |
| guest libc | `b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4` | 2339896 | 0755 |
| corrected `mcexec` | `ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b` | 453352 | 0755 |
| McKernel image | `5f370ee96463a0a606e2b06d0e76e26bd77055f44396e5cb0a4326bf996763a4` | 8016600 | 0644 |
| `native-boot` | `4558995ea1ae70c8d5a115542e333ad695a54b4b8f450ea717df37fd1e631af3` | 30984 | 0755 |
| application payload | `ff227c83b2da598110768e13f5e042b437e049659706b56079cc73f7c818a836` | 20528 | 0755 |
| `ihk.ko` | `2443a0b50b2aa1ad8f003558cd30bb0628ae35544925ca67e998a7cbc01545df` | 1357704 | 0644 |
| `ihk-smp-x86_64.ko` | `5bdcd1b4e285f3f8e23d0cb75e2e62db66161120623887543546f93b5987be90` | 10942760 | 0644 |
| `mcctrl.ko` | `332d7560e02f64844a4d01b837c2d64e65d0f792f3d186bdb8e3e19553efce46` | 1916160 | 0644 |
| static PID1 collector | `78426897fed245e0a8c81996a369896fb264acb9ceb5aab1e5990505d1db4ecb` | 1021256 | 0700 |
| derived initramfs | `19c3447625ff80c1bd9922a7e68cb0f54f7875b37546e0e0ec483cfd617fef3f` | 12395825 | 0600 |
| overlay manifest | `af324719e9f1cf985ced4b6621fb863479e56d5f04829944b79f1ccdbfb7139b` | 14875 | 0600 |

The derived archive preserves the complete decompressed signal base as its exact
prefix and appends canonical `apps`, `case`, `case/work`, `init`, `apps/app` and
`bin/mcexec` records. Independent replay proves the only final-map change from
the prior runtime image is the launcher. The stale launcher digest
`b786e9c98ecc3d429c5ce4d683f1ef4ebca7b3ea132b8435ed6026fc9e984639`
must not appear in the final map.

Container image is
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`.
Its record is `/home/holden/mckernel-work/logs/image-native.json`, SHA-256
`c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
QEMU is `/usr/libexec/qemu-kvm`, SHA-256
`5c1985041a27c64829d9ca18dd54c6ede039eafdef00c3abcd70479b03aca7d0`.
Its stdout must be exactly:

```text
QEMU emulator version 10.1.0 (qemu-kvm-10.1.0-16.el10_2.5)
Copyright (c) 2003-2025 Fabrice Bellard and the QEMU Project developers
```

Return status must be zero and stderr empty. Any drift is a preflight failure.

## Profile and generated guest command

The reviewed container remains UID/GID 1000:1000, CPUs 2-5, 12 GiB memory,
no additional swap, 512 tasks, no network, all capabilities dropped,
`no-new-privileges`, and read-only inputs/root where defined. Exact cgroup v1
values are CPU period 100000/quota 400000, memory limit and memsw limit
12884901888, hierarchy 1, and pids.max 512. Do not widen them.

Guest profile remains q35/TCG, four vCPUs, 8 GiB, two NUMA nodes, no NIC,
no display, `-S`, private QMP and one McKernel CPU/128 MiB. The exact generated
QEMU argv is:

```text
/usr/libexec/qemu-kvm -machine q35 -accel tcg,thread=multi -cpu max,la57=off -smp 4,sockets=2,cores=2,threads=1 -m 8192 -object memory-backend-ram,size=4G,id=ram-node0 -object memory-backend-ram,size=4G,id=ram-node1 -numa node,nodeid=0,cpus=0-1,memdev=ram-node0 -numa node,nodeid=1,cpus=2-3,memdev=ram-node1 -nic none -display none -no-reboot -no-shutdown -S -monitor none -qmp unix:/home/holden/mckernel-work/scratch/ndcs-20260928-4/attempt-e8e0bd60422a94a18680321317786bee/qmp.sock,server=on,wait=off -serial file:/home/holden/mckernel-work/scratch/ndcs-20260928-4/attempt-e8e0bd60422a94a18680321317786bee/serial.log -debugcon file:/home/holden/mckernel-work/scratch/ndcs-20260928-4/attempt-e8e0bd60422a94a18680321317786bee/debugcon.log -global isa-debugcon.iobase=0xe9 -kernel /home/holden/mckernel-work/scratch/native-application-signals-module-20260909-1/bzImage -initrd /home/holden/mckernel-work/scratch/native-diagnostic-overlay-20260928-4/initramfs.cpio.gz -append console=ttyS0,115200n8\ rdinit=/init\ nokaslr\ panic=-1\ memmap=4K%0x80000-1
```

Escaped spaces render the single literal `-append` argument. The owner/runner
reconstruct and compare argv before launch. Require one exact positive QEMU
PID/PGID/SID/starttime tuple with PID=PGID=SID. `owner.json` must retain the
outer owner starttime, root-lock identity and cgroup profile. Container state,
each Docker client identity/status and the inner QEMU identity/status remain in
their separately named records described below. Inner deadline is 300 seconds;
attached container startup deadline is 360 seconds.

## Frozen observation and cleanup

The payload is case `startup.argv-empty` with argv
`/bin/mcexec -t 1 0 app A "" B`, cwd `/case/work`, `COKERNEL_PATH=/apps` and
`PATH=/usr/bin:/bin`. Expected exit is 0. Exact stdout is 91 bytes:

```text
7b2263617365223a22737461727475702e617267762d656d707479222c2261726763223a342c2261726776223a5b22617070222c2241222c22222c2242225d2c227465726d696e61746f725f69735f6e756c6c223a747275657d0a
```

Expected stderr is empty. Both streams have 1024-byte bounds and must reach EOF
without truncation. Preserve raw application bytes/status, serial, debugcon,
kernel log, exact QMP transcript, QEMU argv/stdout/stderr/status, Docker inspect
and OOM status, owner/container/client/QEMU identities, cleanup and final absence.
On success and failure, retain each numbered Docker client command record with
its exact command, PID/PGID/SID/starttime, reaped state and return status.
Retain admitted QEMU argv and QEMU PID/PGID/SID/starttime/returncode after
cleanup; if QEMU evidence cannot be acquired before transfer, retain the
acquisition-failure record with the observed PID, every identity field actually
captured (explicitly null when unavailable), exact reap status and original
failure.
Delayed retirement records use `command-retirements-NNN.json` and retain every
identity/status transition.

An issued Docker create stays unresolved until an exact successful response or
authenticated exact name/label/container observation. Empty sampling, timeout
or interruption never proves absence. Unresolved creation or client retirement
retains the owner and development lock indefinitely; do not kill or retry it.
Publish absence only after exact local-client retirement, resolved creation,
authenticated container retirement and final empty lookup. The inner operations
retain their reviewed finite deadlines. The outer post-absence/post-lock-release
evidence flush is synchronous write/fsync with no wall deadline; a storage stall
there is not a live QEMU/container lease, but its owner PID must be preserved.

## Failure history and release gate

Packet 1 failed before QEMU because its version observer accepted shortened
text. Packet 2 ran one real diagnostic: exact stdout, exit, retirement and
teardown passed, but stale mcexec wrote 58 bytes to stderr. Packet 3 was
rejected before execution because its outer Docker command-child identities and
QEMU argv/status/identity records were not serialized with the required
one-shot evidence. The marker observer false positives were separately
repaired, the frozen empty-stderr oracle was not changed, and the launcher
fix/image rebinding are reviewed in
`docs/verification/stability-native-diagnostic-mcexec-overlay-success-20260928-1.json`.
The independent source-bound process-evidence success is
`docs/verification/stability-native-diagnostic-process-evidence-source-success-20260928-1.json`
(SHA-256 `4c3f0282e7967d2e82d047683d122e9797ed41d99d093843893b98d34abfd7f7`).
The rejected packet 3 is
`docs/verification/stability-native-diagnostic-current-signal-execution-packet-20260928-3.md`
(SHA-256 `01be20700088ed85cb346ef2143b87e7b6e0bd7bfa0f00683a2622bb7f7ecec9`),
and its failure record is
`docs/verification/stability-native-diagnostic-current-signal-execution-review-failure-20260928-3.json`
(SHA-256 `0c27ac2c7d539d02363ca7f7a83c37a8c3b8ce9660ab2a0413160e8d551ab9e6`).
They remain immutable. All original attempts remain immutable.

Before any root, Docker, QEMU or guest operation, an independent reviewer must
issue a release naming this packet's exact SHA-256, command, parent, nonce,
commit, source/artifact bindings, resource profile, deadlines and uncertainty
rules. A source or artifact review is not that release. The fresh parent,
inner attempt and evidence sibling are currently absent and must remain absent
until release. Even a passing diagnostic is protocol evidence only: it grants
no formal application, M04, production or whole-OS acceptance credit.
