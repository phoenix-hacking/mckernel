# Native memory diagnostic execution packet 1

Status: draft for independent exact one-shot execution review. No command in
this packet is released until a separate review record names this packet's exact
SHA-256. This diagnostic cannot earn formal application or production credit.

## Immutable checkpoint and command

The source checkpoint is pushed and fetched-blob verified commit
`d1552173a70f8ef195cac8475047a0579060c784` on
`codex/local-native-staging-repair`. Owner source
`scripts/application-tests/native_diagnostic_container_owner.py` has SHA-256
`c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7`.

The never-used parent is
`/home/holden/mckernel-work/scratch/ndcm-20260928-1`; it must remain absent
during review and be created once as uid/gid 1000 mode 0700 only after release.
The nonce is `5759bc5f9ea85de4ae41c380c30f3c8a`. The inner attempt is
`/home/holden/mckernel-work/scratch/ndcm-20260928-1/attempt-5759bc5f9ea85de4ae41c380c30f3c8a`.
The root-owned evidence sibling is
`/home/holden/mckernel-work/scratch/ndcm-20260928-1.owner-5759bc5f9ea85de4ae41c380c30f3c8a`.

The only proposed outer command is:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndcm-20260928-1 --nonce 5759bc5f9ea85de4ae41c380c30f3c8a --owner-sha256 c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-memory-manifest-20260928-1/manifest.json --manifest-sha256 10bbde5a2d9c0a85c415630c19db0345122bd2d13d162c0c549c52409be0660d
```

Use the inherited `SUDO_ASKPASS` only through `sudo -A`; never inspect or invoke
the helper directly. The command is one-shot and may not be retried after any
start, uncertainty or failure.

## Source and artifact closure

| Runtime source | SHA-256 |
|---|---|
| `native_diagnostic_container_owner.py` | `c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7` |
| `native_diagnostic_runner.py` | `25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499` |
| `native_diagnostic.py` | `65a2b9ee037fdf21255a3500bbac408bd9a0916467375c252d04c6356ca50043` |
| `native_diagnostic_backend.py` | `cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614` |
| `qmp_capture.py` | `5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741` |
| `native_diagnostic_overlay.py` | `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d` |

The strict manifest is
`/home/holden/mckernel-work/scratch/native-diagnostic-memory-manifest-20260928-1/manifest.json`,
SHA-256 `10bbde5a2d9c0a85c415630c19db0345122bd2d13d162c0c549c52409be0660d`,
5,289 bytes, mode 0600. It binds:

| Role | SHA-256 | Size | Mode |
|---|---|---:|---:|
| Linux `bzImage` | `b6cbd689108f499d37ba8d3768f2cdd6cb0f3422d93a4e091af93680686e94eb` | 16130048 | 0644 |
| base initramfs | `c7957431335818d1cf448bb0ae24efb5193bbfa226885787ff5311bea45b4265` | 11803083 | 0644 |
| loader | `0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b` | 930600 | 0755 |
| libc | `b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4` | 2339896 | 0755 |
| corrected mcexec | `ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b` | 453352 | 0755 |
| McKernel image | `5f370ee96463a0a606e2b06d0e76e26bd77055f44396e5cb0a4326bf996763a4` | 8016600 | 0644 |
| native-boot | `4558995ea1ae70c8d5a115542e333ad695a54b4b8f450ea717df37fd1e631af3` | 30984 | 0755 |
| native-application-core | `558d1607e4648321c9537215084e759496937d9591c319a21443f443193fda9a` | 39488 | 0755 |
| ihk.ko | `2443a0b50b2aa1ad8f003558cd30bb0628ae35544925ca67e998a7cbc01545df` | 1357704 | 0644 |
| ihk-smp-x86_64.ko | `5bdcd1b4e285f3f8e23d0cb75e2e62db66161120623887543546f93b5987be90` | 10942760 | 0644 |
| mcctrl.ko | `332d7560e02f64844a4d01b837c2d64e65d0f792f3d186bdb8e3e19553efce46` | 1916160 | 0644 |
| memory collector | `247433d68fa712f0f456366baead6040848832284b5ff14d89fced108b200556` | 1021296 | 0700 |
| derived initramfs | `3fff2b945f6dc5d0a4d1052c283c1613b3eadb138640f85ccfafa5d8106ee662` | 12405186 | 0600 |
| overlay manifest | `46083fc17c46fd16ef864b340f79551f18fe7baebb75e9344198a2214d4b07b2` | 14881 | 0600 |

The decompressed base is 38,191,104 bytes with SHA-256
`fefbfbe32e2cfb05a200b0e8280f6ffa9be4698171194042fd69af85eea0de57`.
The canonical overlay SHA-256 is
`67e9b39a5b010715bbf82e2d066007df9447f12182b29a4572b64013adbdbef9`.
Independent replay accepts all 61 final members and all 37 userspace ELF
dependency/provider joins. Full preparation evidence is
`docs/verification/stability-native-diagnostic-memory-artifact-success-20260928-1.json`.

## Pinned runtime profile and exact guest command

Container image is
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`.
Its retained record is `/home/holden/mckernel-work/logs/image-native.json`,
SHA-256 `c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
Container QEMU is `/usr/libexec/qemu-kvm`, SHA-256
`5c1985041a27c64829d9ca18dd54c6ede039eafdef00c3abcd70479b03aca7d0`,
with exact reviewed stdout and empty stderr:

```text
QEMU emulator version 10.1.0 (qemu-kvm-10.1.0-16.el10_2.5)
Copyright (c) 2003-2025 Fabrice Bellard and the QEMU Project developers
```

The container remains uid/gid 1000:1000, CPUs 2-5, four CPUs, 12 GiB memory
and memory+swap limit, pids 512, cgroup parent `/mckernel-dev`, no network, all
capabilities dropped, no-new-privileges, read-only image/repository/scratch
mounts except the private attempt parent, and bounded tmpfs. The guest remains
q35/TCG, four vCPUs, 8 GiB, two NUMA nodes, no NIC/display, `-S`, private QMP,
one McKernel CPU and 128 MiB. Inner deadline is 300 seconds; outer deadline is
360 seconds. Do not widen this profile.

The exact 42-argument QEMU command is:

```text
/usr/libexec/qemu-kvm -machine q35 -accel tcg,thread=multi -cpu max,la57=off -smp 4,sockets=2,cores=2,threads=1 -m 8192 -object memory-backend-ram,size=4G,id=ram-node0 -object memory-backend-ram,size=4G,id=ram-node1 -numa node,nodeid=0,cpus=0-1,memdev=ram-node0 -numa node,nodeid=1,cpus=2-3,memdev=ram-node1 -nic none -display none -no-reboot -no-shutdown -S -monitor none -qmp unix:/home/holden/mckernel-work/scratch/ndcm-20260928-1/attempt-5759bc5f9ea85de4ae41c380c30f3c8a/qmp.sock,server=on,wait=off -serial file:/home/holden/mckernel-work/scratch/ndcm-20260928-1/attempt-5759bc5f9ea85de4ae41c380c30f3c8a/serial.log -debugcon file:/home/holden/mckernel-work/scratch/ndcm-20260928-1/attempt-5759bc5f9ea85de4ae41c380c30f3c8a/debugcon.log -global isa-debugcon.iobase=0xe9 -kernel /home/holden/mckernel-work/scratch/native-application-signals-module-20260909-1/bzImage -initrd /home/holden/mckernel-work/scratch/native-diagnostic-memory-overlay-20260928-2/initramfs.cpio.gz -append console=ttyS0,115200n8\ rdinit=/init\ nokaslr\ panic=-1\ memmap=4K%0x80000-1
```

The QMP pathname is exactly 100 bytes in the C locale and fits Linux's 107-byte
usable UNIX pathname limit. Escaped spaces above represent one literal append
argument. Owner and runner must reconstruct and compare the list before launch.

## Frozen observation and oracle

Case `baseline.core.memory` executes
`/bin/mcexec -t 1 0 app memory` in `/case/work` with only
`PATH=/usr/bin:/bin` and `COKERNEL_PATH=/apps`. Required result is exit 37,
empty stderr and exact 24-byte stdout:

```text
4e41544956455f434f52452050415353206d656d6f72790a
```

Both streams have 1,024-byte bounds and must reach EOF without truncation.
Require exact scheduling, syscall delivery/return/route, exit-group, retirement,
procfs deletion and process-release joins already enforced by the runner. Retain
raw application bytes/status, serial, debugcon, kernel log, complete QMP, QEMU
argv/stdout/stderr/status/identity, every Docker-client identity/status, inspect
and OOM state, owner/root-lock/cgroup identities, cleanup and final absence.

## Fail-closed ownership and one-shot gate

Require one exact QEMU PID=PGID=SID plus starttime tuple. Preserve progressively
observed partial identity but never use it as signal/transfer authority. An
issued Docker create remains unresolved until an exact successful response or
authenticated exact name/label/container observation. Empty sampling never
proves absence. Unresolved creation, uncertain container retirement or unreaped
local Docker child retains the owner and development lock indefinitely. Publish
absence only after exact child retirement, resolved creation, authenticated
container removal and final empty lookup. Preserve the first failure plus every
secondary capture/evidence error. Packet 5 and packet 6 for startup are consumed
and nonreusable; memory overlay attempt 1 is a retained preparation failure.

Immediately before setup, remeasure host/scratch/RAM floors (at least 16/12 GiB
free plus packet headroom), reconcile the launcher and heavy-runtime lease,
prove no diagnostic owner/QEMU/mcexec/Docker client or matching container is
live, check `/run/lock/mckernel-development.lock`, authenticate every source and
artifact, and confirm parent, attempt and evidence sibling are absent. After a
separate independent review releases this packet's exact SHA-256 and command,
create the parent once and invoke only the released command once. A pass is
diagnostic behavior only, not formal M04/application/production acceptance.
