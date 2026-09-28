# Native threads diagnostic execution packet 1

Status: draft for independent exact one-shot execution review. No command is
released until a separate record names this packet's exact SHA-256. This
diagnostic cannot earn formal application or production credit.

## Immutable checkpoint and command

The source checkpoint is pushed and fetched-blob verified commit
`a2df0eb7106b7194e899a6f87cd4c517ed0edd74` on
`codex/local-native-staging-repair`. Owner source
`scripts/application-tests/native_diagnostic_container_owner.py` has SHA-256
`c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7`.

The never-used parent is
`/home/holden/mckernel-work/scratch/ndct-20260928-1`; create it once as uid/gid
1000 mode 0700 only after release. Nonce
`9561a169a33ebd6ecbd9ae567abbe869` binds inner attempt
`/home/holden/mckernel-work/scratch/ndct-20260928-1/attempt-9561a169a33ebd6ecbd9ae567abbe869`
and root-owned evidence sibling
`/home/holden/mckernel-work/scratch/ndct-20260928-1.owner-9561a169a33ebd6ecbd9ae567abbe869`.

The only proposed outer command is:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndct-20260928-1 --nonce 9561a169a33ebd6ecbd9ae567abbe869 --owner-sha256 c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-threads-manifest-20260928-1/manifest.json --manifest-sha256 0a473e550fc7a399b4c969c51cba2894eb3c93f54df9fa0701f03badee835ca9
```

Use inherited `SUDO_ASKPASS` only through `sudo -A`; never inspect or invoke it.
The command is one-shot and may not be retried after any start, uncertainty or
failure.

## Source and artifact closure

Runtime source hashes remain exactly those in the accepted files packet:
owner `c6a64237...ac4b7`, runner `25ea29f9...d499`, diagnostic
`65a2b9ee...0043`, backend `cd0759c9...d614`, QMP capture
`5bccd46c...741` and overlay `46d41bc0...a27d`. The strict manifest is
`/home/holden/mckernel-work/scratch/native-diagnostic-threads-manifest-20260928-1/manifest.json`,
SHA-256 `0a473e550fc7a399b4c969c51cba2894eb3c93f54df9fa0701f03badee835ca9`,
4,686 bytes, mode 0600. It binds the same exact current signal Linux kernel,
base initramfs, loader/libc, corrected mcexec, McKernel image, native boot,
payload and modules as the accepted memory/files packets. Threads staging is:

| Role | SHA-256 | Size | Mode |
|---|---|---:|---:|
| threads collector | `9dd9388b34283779c8bb6c8d8c7779ef0e44e9480775a4a3244f50b3240e9b10` | 1021296 | 0700 |
| derived initramfs | `e16c593d37345e612fc8b5d1b8fcd92185077c347110e92f6cef266c385eeeec` | 12405183 | 0600 |
| overlay manifest | `d97f1201b6eb71e93245aeaa5bafa95427fa753fab4becc1ea73f331280d66e7` | 14882 | 0600 |

The decompressed base is 38,191,104 bytes, SHA-256
`fefbfbe32e2cfb05a200b0e8280f6ffa9be4698171194042fd69af85eea0de57`;
canonical overlay SHA-256 is
`5991339efa5fcd010fdf428413f1420a65c1bd99e8f27e7eea51c1dbd8058a17`.
Independent replay accepts 61 final members and all 37 userspace ELF joins: 52
dependencies, 11 interpreters and 270 version-provider definitions. Preparation
evidence is
`docs/verification/stability-native-diagnostic-threads-artifact-success-20260928-1.json`.

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

The generated QEMU argv has 42 elements and is identical to files packet 1
except for its fresh attempt paths and threads initramfs. Its QMP argument is:

```text
unix:/home/holden/mckernel-work/scratch/ndct-20260928-1/attempt-9561a169a33ebd6ecbd9ae567abbe869/qmp.sock,server=on,wait=off
```

The socket pathname is exactly 100 bytes. Kernel is the current signal
`bzImage`; initrd is
`/home/holden/mckernel-work/scratch/native-diagnostic-threads-overlay-20260928-1/initramfs.cpio.gz`;
append is the unchanged single argument
`console=ttyS0,115200n8 rdinit=/init nokaslr panic=-1 memmap=4K%0x80000-1`.
Owner and runner must generate and compare the entire argv before launch.

## Frozen observation and oracle

Case `baseline.core.threads` executes
`/bin/mcexec -t 1 0 app threads` in `/case/work`, with only
`PATH=/usr/bin:/bin` and `COKERNEL_PATH=/apps`. Required result is exit 37,
empty stderr and exact 25-byte stdout:

```text
4e41544956455f434f5245205041535320746872656164730a
```

Both streams have 1,024-byte bounds and must reach EOF without truncation.
Require scheduling, clone/thread/TID/futex behavior, syscall route/return,
exit-group, retirement, procfs deletion, pager/process release and teardown.
Retain raw bytes/status, serial/debugcon/kernel log, QMP, QEMU and all Docker
identities/statuses, inspect/OOM state, locks, cleanup and final absence.

## Fail-closed one-shot gate

The fail-closed QEMU/container identity, unresolved-create, child-reaping,
authenticated-removal and lock-retention contracts remain exact. Startup
packets 5/6, memory packet 1 and files packet 1 are consumed/nonreusable. The
threads oracle's original wrong expected-hash failure and correction remain
preserved.

Immediately before setup, remeasure host/scratch/RAM floors (at least 16/12 GiB
free plus packet headroom), reconcile launcher and exclusive heavy lease, prove
runtime process/container absence, authenticate the development lock, every
source/artifact and all three fresh paths. Only after a separate independent
review releases this packet's exact hash and command may the parent be created
and the command invoked once. A pass is diagnostic behavior only, not formal
M04/application/production acceptance.
