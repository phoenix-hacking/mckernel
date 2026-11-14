# Native current-signal diagnostic execution packet

Status: draft for independent execution release; no execution has been performed.
This packet is bound to committed HEAD `5f583b2cc857609dcd8706f756dc9bbe7f922ffe`.
It is a one-shot, root/Docker/QEMU diagnostic only. It must not be retried with
the same attempt after any failure.

## Immutable inputs and ownership

The owner source is
`scripts/application-tests/native_diagnostic_container_owner.py`, SHA-256
`35cd4596c353e916e0167807ed97ecb13fbbefe5c9f98a87706ad97aab37699d`, reviewed
by `docs/verification/stability-native-diagnostic-qemu-version-source-success-20260928-1.json`.
That review records a 211-test integrated pass and is source-readiness evidence, not execution
release. The exact fresh attempt parent is
`/home/holden/mckernel-work/scratch/ndcs-20260928-2`;
it must be absent before setup, then be created as uid/gid 1000, mode 0700.
Use nonce `d5c0db79dea44675abeb1c43c7187add`.

The exact outer command is:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndcs-20260928-2 --nonce d5c0db79dea44675abeb1c43c7187add --owner-sha256 35cd4596c353e916e0167807ed97ecb13fbbefe5c9f98a87706ad97aab37699d
```

The manifest is `/home/holden/mckernel-work/scratch/native-diagnostic-manifest-20260928-2/manifest.json`, SHA-256 `c7072eeaecdc44e450cc9511a994c13db66540465722443a312479c92e5e2d04`.
It binds every artifact by path, mode, size, and digest; do not substitute
artifacts or regenerate the manifest. The image is `sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`,
record `/home/holden/mckernel-work/logs/image-native.json`, SHA-256
`c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
QEMU must be `/usr/libexec/qemu-kvm`, SHA-256
`5c1985041a27c64829d9ca18dd54c6ede039eafdef00c3abcd70479b03aca7d0`,
version `QEMU emulator version 10.1.0 (qemu-kvm-10.1.0-16.el10_2.5)\nCopyright (c) 2003-2025 Fabrice Bellard and the QEMU Project developers\n`; stderr must be empty and stdout must match these bytes exactly. A missing or mismatching input is a
preflight failure, not permission to substitute.

The runtime source closure is exact:

| Source | SHA-256 |
|---|---|
| `native_diagnostic_container_owner.py` | `35cd4596c353e916e0167807ed97ecb13fbbefe5c9f98a87706ad97aab37699d` |
| `native_diagnostic_runner.py` | `25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499` |
| `native_diagnostic.py` | `0ab36565fe4b7019baa66398c4f5cb08801143322ea9e21c12916250278ef02d` |
| `native_diagnostic_backend.py` | `ffdde01883c77171d1512769e0c88f2539dda8f7da4bd22ae4e71f69f080a16b` |
| `qmp_capture.py` | `5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741` |
| `native_diagnostic_overlay.py` | `24c555db4b7490bde1aafdd8a0a6ac5da4cf1f024d44353347d0b9e66b8eba5d` |

The complete manifest inventory, including intentional aliases, is:

| Role | SHA-256 | Size | Mode |
|---|---|---:|---:|
| Linux `bzImage` | `b6cbd689108f499d37ba8d3768f2cdd6cb0f3422d93a4e091af93680686e94eb` | 16130048 | 0644 |
| base `initramfs` and `root_base` | `c7957431335818d1cf448bb0ae24efb5193bbfa226885787ff5311bea45b4265` | 11803083 | 0644 |
| guest loader | `0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b` | 930600 | 0755 |
| guest libc | `b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4` | 2339896 | 0755 |
| `mcexec` | `b786e9c98ecc3d429c5ce4d683f1ef4ebca7b3ea132b8435ed6026fc9e984639` | 453288 | 0755 |
| McKernel image | `5f370ee96463a0a606e2b06d0e76e26bd77055f44396e5cb0a4326bf996763a4` | 8016600 | 0644 |
| `native-boot` | `4558995ea1ae70c8d5a115542e333ad695a54b4b8f450ea717df37fd1e631af3` | 30984 | 0755 |
| application payload | `ff227c83b2da598110768e13f5e042b437e049659706b56079cc73f7c818a836` | 20528 | 0755 |
| `ihk.ko` | `2443a0b50b2aa1ad8f003558cd30bb0628ae35544925ca67e998a7cbc01545df` | 1357704 | 0644 |
| `ihk-smp-x86_64.ko` | `5bdcd1b4e285f3f8e23d0cb75e2e62db66161120623887543546f93b5987be90` | 10942760 | 0644 |
| `mcctrl.ko` | `332d7560e02f64844a4d01b837c2d64e65d0f792f3d186bdb8e3e19553efce46` | 1916160 | 0644 |
| static PID1 collector | `78426897fed245e0a8c81996a369896fb264acb9ceb5aab1e5990505d1db4ecb` | 1021256 | 0700 |
| derived current-signal initramfs | `40d4924c7c052aba24621f22183e2836f29ef0d207ca6575c4729838fb6d7ac3` | 12221271 | 0600 |
| overlay manifest | `6b727dcdbfe6641b2f8037ffce74a07dc5981043a1aff4dde168d0aebf70259f` | 14384 | 0600 |

The strict manifest loader reauthenticates the exact paths as well as these
values. The initramfs/root-base and staging/base-initramfs rows are deliberate
aliases; the derived initramfs is a distinct authenticated output.

## Preflight and isolation

The outer process is root; the container workload is UID 1000. Verify the
parent identity and permissions, exact HEAD/source/manifest/record hashes,
artifact identities, QEMU identity, and that no prior attempt directory exists.
After release, create the exact absent parent once with
`/usr/bin/install -d -m 0700 -- /home/holden/mckernel-work/scratch/ndcs-20260928-2`
as uid/gid 1000, then revalidate its canonical ancestry, uid/gid and mode. The
inner attempt will be
`/home/holden/mckernel-work/scratch/ndcs-20260928-2/attempt-d5c0db79dea44675abeb1c43c7187add`;
the root-owned outer evidence sibling will be
`/home/holden/mckernel-work/scratch/ndcs-20260928-2.owner-d5c0db79dea44675abeb1c43c7187add`.
The resulting QMP pathname is exactly
`/home/holden/mckernel-work/scratch/ndcs-20260928-2/attempt-d5c0db79dea44675abeb1c43c7187add/qmp.sock`,
100 bytes under the C locale and therefore within Linux's 107-byte usable
pathname limit. Recompute and require that length before setup.
Measure capacity immediately before launch: retain at least 16 GiB host free,
12 GiB scratch free, and the measured RAM required by the profile. Acquire one
heavy development lease only. The reviewed Docker profile is CPUs 2-5 (four
CPUs), 12 GiB memory, no swap, pids limit 512, no network, read-only root/files
where applicable, all capabilities dropped, and `no-new-privileges`. Record
the effective cgroup values, including CPU period 100000/quota 400000,
memory limit 12884901888, hierarchy 1, and pids.max 512. Do not widen affinity,
limits, privileges, or network access.

The guest profile is 8 GiB, 4 vCPUs, 2 NUMA nodes, TCG, q35, no NIC and no
display, with `-S` and a private QMP endpoint. The retained result must contain
the exact positive QEMU PID/PGID/session/starttime tuple with PID=PGID=session;
outer `owner.json` must contain a non-null owner starttime, process identity,
root-lock identity and exact cgroup values. Also retain the exact QEMU argv,
container ID and QMP endpoint. Inner deadline is 300 s; outer startup deadline
is 360 s. Record every source-defined command, capture and cleanup bound.

The exact generated QEMU argv is:

```text
/usr/libexec/qemu-kvm -machine q35 -accel tcg,thread=multi -cpu max,la57=off -smp 4,sockets=2,cores=2,threads=1 -m 8192 -object memory-backend-ram,size=4G,id=ram-node0 -object memory-backend-ram,size=4G,id=ram-node1 -numa node,nodeid=0,cpus=0-1,memdev=ram-node0 -numa node,nodeid=1,cpus=2-3,memdev=ram-node1 -nic none -display none -no-reboot -no-shutdown -S -monitor none -qmp unix:/home/holden/mckernel-work/scratch/ndcs-20260928-2/attempt-d5c0db79dea44675abeb1c43c7187add/qmp.sock,server=on,wait=off -serial file:/home/holden/mckernel-work/scratch/ndcs-20260928-2/attempt-d5c0db79dea44675abeb1c43c7187add/serial.log -debugcon file:/home/holden/mckernel-work/scratch/ndcs-20260928-2/attempt-d5c0db79dea44675abeb1c43c7187add/debugcon.log -global isa-debugcon.iobase=0xe9 -kernel /home/holden/mckernel-work/scratch/native-application-signals-module-20260909-1/bzImage -initrd /home/holden/mckernel-work/scratch/native-diagnostic-overlay-20260928-3/initramfs.cpio.gz -append console=ttyS0,115200n8\ rdinit=/init\ nokaslr\ panic=-1\ memmap=4K%0x80000-1
```

This is an argv rendering: the escaped spaces after `-append` delimit one
literal kernel-command-line argument, not separate shell arguments. The owner
and runner reconstruct and compare the immutable argv before launch.

## Required one-shot protocol

Run only the owner CLI above. It validates and stages the manifest/overlay,
starts the reviewed container and runner, and captures serial, debugcon, QMP,
kernel console through `serial.log`, Docker inspect/status/OOM data, QEMU
stdout/stderr, exit status, and
teardown identities. The expected application payload is case
`startup.argv-empty` with `/bin/mcexec -t 1 0 app A "" B`, cwd `/case/work`,
`COKERNEL_PATH=/apps`, and `PATH=/usr/bin:/bin`.

The exact application stdout oracle is 91 bytes (hex):

```text
7b2263617365223a22737461727475702e617267762d656d707479222c2261726763223a342c2261726776223a5b22617070222c2241222c22222c2242225d2c227465726d696e61746f725f69735f6e756c6c223a747275657d0a
```

Expected application result is exit 0, exactly that stdout, empty stderr, and
no truncation (the per-stream bound is 1024 bytes). Preserve raw bytes, exit
status, serial/debugcon/QMP/kernel logs, Docker inspect status and OOM state,
and complete teardown evidence. Protocol-wrapper success is not OS success:
the result must state `mckernel_application_executed: false` and
`application_acceptance: false`, and receives no M04 or formal acceptance
credit even if the startup payload is observed.

## Fail-closed cleanup and uncertainty

An issued Docker create remains unresolved until its exact successful response
or an authenticated exact name/label/container observation. Empty lookups,
timeouts, interruption, or finite sampling never prove absence. An unresolved
create may intentionally keep the owner process and development lock alive
indefinitely. Monitor and preserve owner/container/client/QEMU process IDs,
logs, and lock identity; do not kill an uncertain owner or retry an unchanged
packet. Cleanup may publish absence only after exact local-client retirement,
resolved creation, authenticated container retirement, and a final empty
lookup. Evidence writers remain deferred until absence and lock release.
The inner lifecycle's capture/publication operations have their reviewed finite
bounds. The outer owner's final `_flush` uses synchronous write/fsync only after
verified absence and lock release and has no wall deadline; a storage stall may
leave that post-retirement owner process alive. Preserve its PID and evidence
directory and do not mistake that state for a live container/QEMU lease.
Preserve every failure and partial capture for later review.

## Failure history and release gate

The reviewed source also preserves the actual first fresh-attempt failure in
`docs/verification/stability-native-diagnostic-current-signal-attempt-failure-20260928-1.json`:
the exact container exited 1 before QEMU startup because the observer required
only the shortened version line while the pinned QEMU emitted its retained
full distribution-suffixed stdout. Cleanup authenticated container retirement,
final absence, and lease release; no QEMU or guest process ran. This packet
must use the new parent and nonce above; reusing packet 1, its parent, or its
nonce is prohibited.

The reviewed source preserves four predecessor failures: cancellation before
child process-group ownership could signal a reused group; Python 3.9 rejected
the `setsid=True` spawn candidate (52 pass/3 errors); finite two-second empty
sampling discharged an in-flight daemon create and swallowed local retirement
errors; and one ledger mock binding failed before correction. Fake backends and
local-process tests do not establish Docker, QEMU, guest, or McKernel behavior.
The first packet hash `82e52a97...` was rejected without execution for its
128-byte QMP path, missing retained process/cgroup identities and overstated
outer-writer bound; that review remains preserved separately.

Before launch, an independent reviewer must issue an execution release naming
this final packet SHA-256, exact command, nonce, parent, immutable inputs,
resource profile, deadlines, and cleanup/uncertainty rules. No root, Docker,
QEMU, or guest command is authorized without that release. After drafting,
compute and record this file's SHA-256 in the review/release record.

