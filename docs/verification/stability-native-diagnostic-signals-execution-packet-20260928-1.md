# Native signals diagnostic execution packet 1

Status: draft for independent exact one-shot execution review. No command is
released until a separate record names this packet's exact SHA-256. This
diagnostic cannot earn formal application or production credit.

## Immutable checkpoint and command

The source checkpoint is pushed and fetched-blob verified commit
`f8941f1b5ad136c65b6a20424f10250253d2be0b` on
`codex/local-native-staging-repair`. Owner source
`scripts/application-tests/native_diagnostic_container_owner.py` has SHA-256
`c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7`.

Earlier `ndcs-20260928-1`, `-2`, `-5` and `-6` paths and their evidence siblings
exist and are forbidden. The never-used parent for this packet is
`/home/holden/mckernel-work/scratch/ndcs-20260928-7`; create it once as uid/gid
1000 mode 0700 only after release. Nonce
`c113ad500484ce6fc89659eee237c8ce` binds inner attempt
`/home/holden/mckernel-work/scratch/ndcs-20260928-7/attempt-c113ad500484ce6fc89659eee237c8ce`
and root-owned evidence sibling
`/home/holden/mckernel-work/scratch/ndcs-20260928-7.owner-c113ad500484ce6fc89659eee237c8ce`.

The only proposed outer command is:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndcs-20260928-7 --nonce c113ad500484ce6fc89659eee237c8ce --owner-sha256 c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-signals-manifest-20260928-1/manifest.json --manifest-sha256 99482694277898df70373f193d89362648f9c1975a4dfdbf18776c4a5b05c2d4
```

Use inherited `SUDO_ASKPASS` only through `sudo -A`; never inspect or invoke it.
The command is one-shot and may not be retried after any start, uncertainty or
failure.

## Source and artifact closure

Runtime source hashes are owner `c6a64237...ac4b7`, runner
`25ea29f9...d499`, diagnostic `65a2b9ee...0043`, backend
`cd0759c9...d614`, QMP capture `5bccd46c...741` and overlay
`46d41bc0...a27d`. The strict manifest is
`/home/holden/mckernel-work/scratch/native-diagnostic-signals-manifest-20260928-1/manifest.json`,
SHA-256 `99482694277898df70373f193d89362648f9c1975a4dfdbf18776c4a5b05c2d4`,
5,296 bytes, mode 0600. It binds the same exact current signal Linux kernel,
base initramfs, loader/libc, corrected mcexec, McKernel image, native boot,
payload and modules as the accepted memory/files/threads packets. Signals staging
is:

| Role | SHA-256 | Size | Mode |
|---|---|---:|---:|
| signals collector | `e1c7b50e3efe559c72ded2288da021ad6c15ace1825074e1ef0e60ae43a0cdea` | 1021968 | 0700 |
| derived initramfs | `9065d03bc3b1c89762743dd5d3d16d2b202c3fb19a287d56893b92473e07ef91` | 12405306 | 0600 |
| overlay manifest | `06feecc69507b43535a95dd2f981360ea841d69a19bcf8b83c3ad3db76372582` | 19292 | 0600 |

The decompressed base is 38,191,104 bytes, SHA-256
`fefbfbe32e2cfb05a200b0e8280f6ffa9be4698171194042fd69af85eea0de57`.
Independent replay accepts 61 final members and complete userspace ELF
interpreter, dependency and version-provider closure. Preparation evidence is
`docs/verification/stability-native-diagnostic-signals-artifact-success-20260928-1.json`.

## Pinned runtime and guest command

The container image remains
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`,
with retained image record SHA-256
`c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
Preserve uid/gid 1000:1000, CPUs 2-5, four CPUs, 12 GiB/no swap, 512 tasks,
no network, dropped capabilities, no-new-privileges and read-only mounts except
the private parent. Guest remains q35/TCG, four vCPUs, 8 GiB/two NUMA nodes,
no NIC/display, one McKernel CPU and 128 MiB. Deadlines remain 300 seconds inner
and 360 seconds attached container; do not widen them.

The exact generated 42-element QEMU argv is:

```text
/usr/libexec/qemu-kvm -machine q35 -accel tcg,thread=multi -cpu max,la57=off -smp 4,sockets=2,cores=2,threads=1 -m 8192 -object memory-backend-ram,size=4G,id=ram-node0 -object memory-backend-ram,size=4G,id=ram-node1 -numa node,nodeid=0,cpus=0-1,memdev=ram-node0 -numa node,nodeid=1,cpus=2-3,memdev=ram-node1 -nic none -display none -no-reboot -no-shutdown -S -monitor none -qmp unix:/home/holden/mckernel-work/scratch/ndcs-20260928-7/attempt-c113ad500484ce6fc89659eee237c8ce/qmp.sock,server=on,wait=off -serial file:/home/holden/mckernel-work/scratch/ndcs-20260928-7/attempt-c113ad500484ce6fc89659eee237c8ce/serial.log -debugcon file:/home/holden/mckernel-work/scratch/ndcs-20260928-7/attempt-c113ad500484ce6fc89659eee237c8ce/debugcon.log -global isa-debugcon.iobase=0xe9 -kernel /home/holden/mckernel-work/scratch/native-application-signals-module-20260909-1/bzImage -initrd /home/holden/mckernel-work/scratch/native-diagnostic-signals-overlay-20260928-1/initramfs.cpio.gz -append console=ttyS0,115200n8\ rdinit=/init\ nokaslr\ panic=-1\ memmap=4K%0x80000-1
```

The QMP socket pathname within its argument is exactly 100 bytes. The escaped
spaces above represent the single unchanged append argument
`console=ttyS0,115200n8 rdinit=/init nokaslr panic=-1 memmap=4K%0x80000-1`.
Owner and runner must reconstruct and compare the entire list before launch.

## Frozen observation and oracle

Case `baseline.core.signals` executes
`/bin/mcexec -t 1 0 app signals` in `/case/work`, with only
`PATH=/usr/bin:/bin` and `COKERNEL_PATH=/apps`. Required result is exit 37,
empty stderr and exact 25-byte stdout:

```text
4e41544956455f434f52452050415353207369676e616c730a
```

Both streams have 1,024-byte bounds and must reach EOF without truncation.
Require signal delivery, mask, alternate-stack/return behavior exposed by the
bound fixture, syscall route/return, exit-group, retirement, procfs deletion,
pager/process release and teardown. Retain raw bytes/status,
serial/debugcon/kernel log, QMP, QEMU and all Docker identities/statuses,
inspect/OOM state, locks, cleanup and final absence.

## Fail-closed one-shot gate

The fail-closed QEMU/container identity, unresolved-create, child-reaping,
authenticated-removal and lock-retention contracts remain exact. Startup
packets 5/6 and memory/files/threads packet 1 are consumed/nonreusable. All
earlier `ndcs` parents remain forbidden. The signals preparation's original
invented-literal assertion failure and corrected authority remain preserved.

Immediately before setup, remeasure host/scratch/RAM floors (at least 16/12 GiB
free plus packet headroom), reconcile launcher and exclusive heavy lease, prove
runtime process/container absence, authenticate the development lock, every
source/artifact and all three fresh paths. Only after a separate independent
review releases this packet's exact hash and command may the parent be created
and the command invoked once. A pass is diagnostic behavior only, not formal
M04/application/production acceptance.
