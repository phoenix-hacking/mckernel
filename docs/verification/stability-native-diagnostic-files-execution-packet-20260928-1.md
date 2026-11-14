# Native files diagnostic execution packet 1

Status: draft for independent exact one-shot execution review. No command in
this packet is released until a separate review record names this packet's exact
SHA-256. This diagnostic cannot earn formal application or production credit.

## Immutable checkpoint and command

The source checkpoint is pushed and fetched-blob verified commit
`6ca65c063f3688790b4ecedae149ae291ba7222b` on
`codex/local-native-staging-repair`. Owner source
`scripts/application-tests/native_diagnostic_container_owner.py` has SHA-256
`c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7`.

The never-used parent is
`/home/holden/mckernel-work/scratch/ndcf-20260928-2`; it must remain absent
during review and be created once as uid/gid 1000 mode 0700 only after release.
The nonce is `30cd836a7be0fd61d4b43fc1042e6afc`. The inner attempt is
`/home/holden/mckernel-work/scratch/ndcf-20260928-2/attempt-30cd836a7be0fd61d4b43fc1042e6afc`.
The root-owned evidence sibling is
`/home/holden/mckernel-work/scratch/ndcf-20260928-2.owner-30cd836a7be0fd61d4b43fc1042e6afc`.
The checkpoint-42 proposed nonce `8808ac26689c76b89677cecedced2474` and
its `ndcf-20260928-1` paths are forbidden and remain unused.

The only proposed outer command is:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndcf-20260928-2 --nonce 30cd836a7be0fd61d4b43fc1042e6afc --owner-sha256 c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-files-manifest-20260928-1/manifest.json --manifest-sha256 1987e5921635cf6b364d0af83f50c61613a66ba4245cc1ddd078f27ca6574186
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
`/home/holden/mckernel-work/scratch/native-diagnostic-files-manifest-20260928-1/manifest.json`,
SHA-256 `1987e5921635cf6b364d0af83f50c61613a66ba4245cc1ddd078f27ca6574186`,
4,672 bytes, mode 0600. It binds the same exact current signal Linux kernel,
base initramfs, loader/libc, corrected mcexec, McKernel image, native boot,
payload and three modules listed in the memory packet. Files-specific staging is:

| Role | SHA-256 | Size | Mode |
|---|---|---:|---:|
| files collector | `44bdb28f6c57d28eee9959bb729a51e56fb67026fcae3d5d5f43159d0b651ab6` | 1021296 | 0700 |
| derived initramfs | `100e9989870491e279470fd87d2d6914b10f25392ebc4e175dcd380b11cfaa15` | 12405181 | 0600 |
| overlay manifest | `60db93f40e6dddfdca00b0309fd26f23396f8ce2175bb70f275acafb0feaea89` | 14880 | 0600 |

The decompressed base is 38,191,104 bytes with SHA-256
`fefbfbe32e2cfb05a200b0e8280f6ffa9be4698171194042fd69af85eea0de57`.
The canonical overlay SHA-256 is
`f0face7546044904a44825a83518f87f23042129bdab2ad1323e634afabb2906`.
Independent replay accepts all 61 final members and all 37 userspace ELF joins:
52 dependencies, 11 interpreters and 270 required-version/provider definitions.
Full preparation evidence is
`docs/verification/stability-native-diagnostic-files-artifact-success-20260928-1.json`.

## Pinned runtime profile and exact guest command

Container image is
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`.
Its retained record is `/home/holden/mckernel-work/logs/image-native.json`,
SHA-256 `c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
The reviewed uid/gid 1000:1000, CPUs 2-5, 12-GiB/no-swap, 512-task,
no-network, all-capabilities-dropped and read-only mount profile is unchanged.
Guest q35/TCG, four-vCPU, 8-GiB/two-NUMA-node, no-NIC/display, one-McKernel-CPU
and 128-MiB profile is unchanged. Inner deadline is 300 seconds and attached
container deadline is 360 seconds; do not widen the profile.

The exact 42-argument QEMU command is:

```text
/usr/libexec/qemu-kvm -machine q35 -accel tcg,thread=multi -cpu max,la57=off -smp 4,sockets=2,cores=2,threads=1 -m 8192 -object memory-backend-ram,size=4G,id=ram-node0 -object memory-backend-ram,size=4G,id=ram-node1 -numa node,nodeid=0,cpus=0-1,memdev=ram-node0 -numa node,nodeid=1,cpus=2-3,memdev=ram-node1 -nic none -display none -no-reboot -no-shutdown -S -monitor none -qmp unix:/home/holden/mckernel-work/scratch/ndcf-20260928-2/attempt-30cd836a7be0fd61d4b43fc1042e6afc/qmp.sock,server=on,wait=off -serial file:/home/holden/mckernel-work/scratch/ndcf-20260928-2/attempt-30cd836a7be0fd61d4b43fc1042e6afc/serial.log -debugcon file:/home/holden/mckernel-work/scratch/ndcf-20260928-2/attempt-30cd836a7be0fd61d4b43fc1042e6afc/debugcon.log -global isa-debugcon.iobase=0xe9 -kernel /home/holden/mckernel-work/scratch/native-application-signals-module-20260909-1/bzImage -initrd /home/holden/mckernel-work/scratch/native-diagnostic-files-overlay-20260928-1/initramfs.cpio.gz -append console=ttyS0,115200n8\ rdinit=/init\ nokaslr\ panic=-1\ memmap=4K%0x80000-1
```

The QMP pathname is exactly 100 bytes in the C locale and fits Linux's 107-byte
usable UNIX pathname limit. Owner and runner must reconstruct and compare the
list before launch.

## Frozen observation and oracle

Case `baseline.core.files` executes `/bin/mcexec -t 1 0 app files` in
`/case/work` with only `PATH=/usr/bin:/bin` and `COKERNEL_PATH=/apps`.
Required result is exit 37, empty stderr and exact 23-byte stdout:

```text
4e41544956455f434f524520504153532066696c65730a
```

Both streams have 1,024-byte bounds and must reach EOF without truncation.
Require exact scheduling, syscall delivery/return/route, exit-group, retirement,
procfs deletion, pager/process release and the absence of residual application
files. Retain raw bytes/status, serial, debugcon, kernel log, QMP, QEMU and every
Docker-client identity/status, container inspect/OOM state, locks, cleanup and
final absence.

## Fail-closed ownership and one-shot gate

The fail-closed QEMU/container identity, unresolved-create, child-reaping,
authenticated-removal and lock-retention contracts from the accepted memory
packet remain exact. Startup packets 5/6 and memory packet 1 are consumed and
nonreusable. Files oracle attempts 1-3 are preserved failures/invalid evidence;
attempt 4 is the bounded observer correction.

Immediately before setup, remeasure host/scratch/RAM floors (at least 16/12 GiB
free plus packet headroom), reconcile the launcher and heavy-runtime lease,
prove no diagnostic owner/QEMU/mcexec/Docker client or matching container is
live, check `/run/lock/mckernel-development.lock`, authenticate every source and
artifact, and confirm parent, attempt and evidence sibling are absent. Reconfirm
the forbidden checkpoint-42 nonce/paths remain unused. After a separate
independent review releases this packet's exact SHA-256 and command, create the
parent once and invoke only the released command once. A pass is diagnostic
behavior only, not formal M04/application/production acceptance.
