# Native c81 direct-futex diagnostic execution packet 1

Status: **NOT_RELEASED**. One-shot diagnostic proposal only. It grants no
application, production, shutdown, release, catalog, or Rust/assembly
acceptance and no runtime authority until independent review binds this exact
packet at a fetched commit and repeats the live preflight.

## Coordinator identity and sole command

Fresh nonce: `1a9f699e18ae309d0cb9205564458ab0`. Fresh parent:
`/home/holden/mckernel-work/scratch/ndfutexc81-20261001-1`; sole inner attempt:
`.../attempt-1a9f699e18ae309d0cb9205564458ab0`; distinct root-owned evidence sibling:
`/home/holden/mckernel-work/scratch/ndfutexc81-20261001-1.owner-1a9f699e18ae309d0cb9205564458ab0`.
Resolve each once. Never retry, reuse, rename, or substitute after start,
uncertainty, timeout, or failure.

If and only if independently released, the sole command is:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndfutexc81-20261001-1 --nonce 1a9f699e18ae309d0cb9205564458ab0 --owner-sha256 5d6fffe0bcc73929772c55dff3a57c3c7aace8fa74eea5745fcd1720c869b20e --manifest /home/holden/mckernel-work/scratch/native-diagnostic-futex-c81-20261001-3/manifest.json --manifest-sha256 ce4be0043b42e1fac46862811dc78d15a1e89740c20a609d32f60db6ba5ef28d
```

Use inherited `SUDO_ASKPASS` only through `sudo -A`; never inspect or invoke
it. All three selected paths must be absent at preflight. Create the parent
once as uid/gid 1000, mode 0700. This command is one-shot.

## Prepared manifest and exact contract

Corrected manifest:
`/home/holden/mckernel-work/scratch/native-diagnostic-futex-c81-20261001-3/manifest.json`,
mode 0600, 6,080 bytes, SHA-256
`ce4be0043b42e1fac46862811dc78d15a1e89740c20a609d32f60db6ba5ef28d`.
Its frozen application contract is:

    argv=/bin/mcexec -t 1 0 /apps/app
    cwd=/case/work
    env=COKERNEL_PATH=/apps;PATH=/usr/bin:/bin
    expected exit=37
    expected stdout=NATIVE_ULTRA_FUTEX PASS cases=16 threads=2 raw_clone=1\n
    expected stderr=typed native-ultra-futex-v1, 18 complete lines
    stdout/stderr limits=4096/4096 bytes

The typed oracle requires the exact ordered 16 case IDs and their result/errno
contracts, one clone record, one two-thread record, timing/deadline relations,
bounded counts and complete raw bytes. It does not freeze dynamic timestamps,
TIDs or worker counts. The evaluator and collector source checkpoint is fetched
commit `cca634afbbf8961f5cd89f5d8b7efa1f5fa99859`; the path/join correction is
part of the commit containing this packet and must be fetched before release.

| Artifact/input | Size | Mode | SHA-256 |
|---|---:|---:|---|
| scratch12 Linux `bzImage` | 16130048 | 0644 | `c995dfd141a6c2fb64c293a7e5b37fc5954008d1dfceb3d778910aa76261985e` |
| base/root initramfs | 12303864 | 0600 | `ed55400792c0fcb25f861062158b059d8db5b4d18399a33407f4e33b42138466` |
| c81 McKernel image | 7908256 | 0755 | `fa6685543160fcaa5000b535ec8bd6fc70230465109564c3fb2beecb95bf39ed` |
| corrected `mcexec` | 453352 | 0755 | `ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b` |
| direct-futex payload | 45304 | 0755 | `9593e5f1f17736d8be4f720691df5da3b636e21bc82fbc5391baa894969b2ecc` |
| native boot | 30984 | 0755 | `4558995ea1ae70c8d5a115542e333ad695a54b4b8f450ea717df37fd1e631af3` |
| dynamic loader | 930600 | 0755 | `0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b` |
| libc | 2339896 | 0755 | `b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4` |
| `ihk.ko` | 1425960 | 0644 | `b4dbf04c47c8b8175462982cfee6e833bd40a2b7d6cadd947d68d4612c97dc9f` |
| `ihk-smp-x86_64.ko` | 11075136 | 0644 | `268d6d3b36fd33f9650c5b7b3ae5233e606d07c992e1e0c4be64493527f84bbb` |
| `mcctrl.ko` | 1914824 | 0644 | `d927bc4460d23c175660f0a23ad8d9dec79b9e5c144e4ae0c898091bcc98a019` |
| futex collector | 1021296 | 0700 | `3833fd03dbfeb0d2db6d03cc07399ec4b9a64fb6e2f892f5d7be2c0fafdb2e69` |
| derived futex overlay | 12894522 | 0600 | `08afffe000231b1ff4f1d87efd7c74e5e098473a7082c5d6e8298abe691d0efc` |
| overlay representation | 13783 | 0600 | `5e252f5b4c8912ffeafddb7015e6aa356da365ec3ab416619b5eb8b7e62a3335` |
| overlay source | 26579 | 0600 | `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d` |

The base decompressed CPIO is 39,366,656 bytes at
`defbea55bebd9dc8c009e1317183bb08988d467911a41cb59c7e09dc59647b23`.
Overlay construction exited zero, used one pinned CPU and about 225 MiB peak
RSS; its retained stderr is empty. Attempt 1 produced the same deterministic
image but returned its JSON only to the launcher console. Attempt 2 preserved
manifest `51a7f75c...61a1` and was independently blocked because it described
`app` while the exact collector executes and reports `/apps/app`. Attempt 3 is
the bounded correction and does not reclassify either earlier record.

Runtime sources are owner
`5d6fffe0bcc73929772c55dff3a57c3c7aace8fa74eea5745fcd1720c869b20e`,
runner `25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499`,
diagnostic `bda3191b20e1c2a8bdfab44c116536569b91e05835ae3bf1bcc97fa67ba45375`,
backend `cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614`,
QMP `5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741`,
and overlay `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d`.

## Pinned profile, evidence and stop rules

Use only uid/gid 1000, CPUs 2-5, 12 GiB memory with no additional swap, pids
512, no network, all capabilities dropped, no-new-privileges, read-only inputs
and only the private parent writable. Pinned image:
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`;
image record SHA-256
`c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
Guest QEMU is q35/TCG, four vCPUs, 8 GiB, two NUMA nodes, no NIC/display,
`-S`, private QMP, one McKernel CPU and 128 MiB. Do not widen these profiles.

Before release, require at least 16 GiB host and 12 GiB scratch free plus
headroom; reserve the coordinator's sole heavy-runtime lane; prove all prior
owners/containers/QEMU/mcexec and every Docker client retired; authenticate the
development lock and prove no diagnostic owner/container is live. Any hash,
path, process, lease, truncation, timeout, identity or oracle mismatch stops the
attempt without retry. Preserve raw streams/status, serial/debugcon/kernel log,
complete QMP/argv, Docker identities/statuses, inspect/OOM state, owner/root-lock/
cgroup identities, first/secondary failures, and authenticated cleanup/absence.
Never delete or rewrite evidence.

A pass is current-candidate direct-futex diagnostic evidence only. It is not
formal application/catalog acceptance and does not establish production
shutdown or general futex completeness. This packet remains **NOT_RELEASED**
until exact fetched-hash review and fresh preflight pass.
