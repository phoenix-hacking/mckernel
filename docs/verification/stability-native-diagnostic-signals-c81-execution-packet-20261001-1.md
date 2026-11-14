# Native c81 signals diagnostic execution packet 1

Status: **NOT_RELEASED**. One-shot diagnostic proposal only; no application,
production, release, shutdown, or Rust/assembly acceptance and no runtime
authority. Independent review must bind this exact packet SHA-256, manifest and
runtime-source hashes, coordinator identity, prior cleanup, and a fresh live
preflight before setup or launch.

## Coordinator identity and sole command

Fresh nonce: `12b580e25217daeb184cc3b6af080b0e`. Fresh parent:
`/home/holden/mckernel-work/scratch/ndsigc81-20261001-1`; sole inner attempt:
`.../attempt-12b580e25217daeb184cc3b6af080b0e`; distinct root-owned evidence sibling:
`/home/holden/mckernel-work/scratch/ndsigc81-20261001-1.owner-12b580e25217daeb184cc3b6af080b0e`.
Resolve each once. Never retry, reuse, rename, or substitute after start,
uncertainty, timeout, or failure.

If and only if independently released, the sole command is:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndsigc81-20261001-1 --nonce 12b580e25217daeb184cc3b6af080b0e --owner-sha256 c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-signals-c81-20261001-3/manifest.json --manifest-sha256 7638d9829c8e2fbc45829b7e3aae1e602e1c8bd42ee611796ee0e5037001c298
```

Use inherited `SUDO_ASKPASS` only through `sudo -A`; never inspect or invoke
it. All three selected paths must be absent at preflight. Create the parent
once as uid/gid 1000, mode 0700. This command is one-shot.

## Prepared manifest and exact contract

Manifest:
`/home/holden/mckernel-work/scratch/native-diagnostic-signals-c81-20261001-3/manifest.json`,
mode 0600, SHA-256
`7638d9829c8e2fbc45829b7e3aae1e602e1c8bd42ee611796ee0e5037001c298`.
Independent `PASS_SIGNALS_MANIFEST_C81` authenticates all 17 referenced
artifacts/modules/staging inputs, canonical 60-member replay, exact paths,
modes, sizes and hashes. The frozen application contract is:

    argv=/bin/mcexec -t 1 0 app signals
    cwd=/case/work
    env=COKERNEL_PATH=/apps;PATH=/usr/bin:/bin
    expected exit=37
    expected stderr hex=(empty)
    expected stdout hex=4e41544956455f434f52452050415353207369676e616c730a
    stdout/stderr limits=1024/1024 bytes

| Artifact/input | Size | Mode | SHA-256 |
|---|---:|---:|---|
| scratch12 Linux `bzImage` | 16130048 | 0644 | `c995dfd141a6c2fb64c293a7e5b37fc5954008d1dfceb3d778910aa76261985e` |
| base/root initramfs | 12303864 | 0600 | `ed55400792c0fcb25f861062158b059d8db5b4d18399a33407f4e33b42138466` |
| c81 McKernel image | 7908256 | 0755 | `fa6685543160fcaa5000b535ec8bd6fc70230465109564c3fb2beecb95bf39ed` |
| corrected `mcexec` | 453352 | 0755 | `ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b` |
| core payload | 39488 | 0755 | `558d1607e4648321c9537215084e759496937d9591c319a21443f443193fda9a` |
| native boot | 30984 | 0755 | `4558995ea1ae70c8d5a115542e333ad695a54b4b8f450ea717df37fd1e631af3` |
| dynamic loader | 930600 | 0755 | `0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b` |
| libc | 2339896 | 0755 | `b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4` |
| `ihk.ko` | 1425960 | 0644 | `b4dbf04c47c8b8175462982cfee6e833bd40a2b7d6cadd947d68d4612c97dc9f` |
| `ihk-smp-x86_64.ko` | 11075136 | 0644 | `268d6d3b36fd33f9650c5b7b3ae5233e606d07c992e1e0c4be64493527f84bbb` |
| `mcctrl.ko` | 1914824 | 0644 | `d927bc4460d23c175660f0a23ad8d9dec79b9e5c144e4ae0c898091bcc98a019` |
| signals collector | 1021968 | 0700 | `e1c7b50e3efe559c72ded2288da021ad6c15ace1825074e1ef0e60ae43a0cdea` |
| derived signals overlay | 12891736 | 0600 | `138b2bb557d3c4cbfaed8409f0cc22a629f1c00e2add7824e3ed61ae1b4ac55a` |
| overlay representation | 15069 | 0600 | `eec0964b94da39e26f7795d811a6d93aa86a23f1a186b6ee341ae0b87544a473` |
| overlay source | 26579 | 0600 | `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d` |

The base decompressed CPIO is 39,366,656 bytes at
`defbea55bebd9dc8c009e1317183bb08988d467911a41cb59c7e09dc59647b23`.
Overlay construction exited zero; its retained stderr is empty. The two earlier
preparation failures remain immutable: attempt 1 precreated the output, and
attempt 2 supplied the non-authoritative collector digest
`e1c7b50e58c3a82f7e22b879048425ed7be1874a67f80add89986b3ee197cdea`.
Attempt 3 uses the original independently reviewed artifact digest and is not a
reclassification of either failure.

Runtime source hashes are owner
`c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7`,
runner `25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499`,
diagnostic `65a2b9ee037fdf21255a3500bbac408bd9a0916467375c252d04c6356ca50043`,
backend `cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614`,
QMP `5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741`,
and overlay `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d`.

## Pinned profile, evidence and stop rules

Use only uid/gid 1000, CPUs 2-5 (four CPUs), 12 GiB memory with no additional
swap, pids 512, no network, all capabilities dropped, no-new-privileges,
read-only inputs and only the private parent writable. Pinned image:
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`;
image record SHA-256
`c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
Guest QEMU is q35/TCG, four vCPUs, 8 GiB, two NUMA nodes, no NIC/display,
`-S`, private QMP, one McKernel CPU and 128 MiB. Do not widen these profiles.

Before release, require at least 16 GiB host and 12 GiB scratch free plus
headroom; reserve the coordinator's sole heavy-runtime lane; prove the threads
owner/container/QEMU/mcexec and every Docker client retired; authenticate the
development lock and prove no diagnostic owner/container is live. Any hash,
path, process, lease, truncation, timeout, identity or oracle mismatch stops the
attempt without retry. Preserve raw streams/status, serial/debugcon/kernel log,
complete QMP/argv, Docker identities/statuses, inspect/OOM state, owner/root-lock/
cgroup identities, first/secondary failures, and authenticated cleanup/absence.
Never delete or rewrite evidence.

This observes the bounded signal fixture only: pending/masked SIGUSR1 and two
alternate-stack deliveries/returns plus syscall route/return, exit-group,
retirement, procfs deletion, pager/process release and teardown. The selected
source-consumer regression passed separately, but neither it nor this packet
qualifies general signals. Memory, files, startup and threads diagnostic packets
are consumed/non-reusable history. A pass is current-candidate diagnostic
evidence only. This packet remains **NOT_RELEASED** until exact-hash review and
fresh preflight pass.
