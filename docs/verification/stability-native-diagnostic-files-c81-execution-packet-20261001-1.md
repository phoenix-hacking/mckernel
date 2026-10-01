# Native c81 files diagnostic execution packet 1

Status: **NOT_RELEASED**. This is a one-shot diagnostic proposal, not
application, production, or release acceptance. The earlier memory diagnostic
guest is retired; this packet must not reuse its namespace, attempt, overlay,
or evidence directory. No execution is authorized until an independent
reviewer binds this exact packet SHA-256, the manifest/source hashes below and
a fresh live preflight.

## Coordinator-bound one-shot identity and command

The fresh nonce is `b12fe7d1ca5d5dc8714810d657fe6c65`. Its parent is
`/home/holden/mckernel-work/scratch/ndfc81-20261001-1`, the only permitted inner
attempt is `.../attempt-b12fe7d1ca5d5dc8714810d657fe6c65`, and the root-owned
evidence sibling is
`/home/holden/mckernel-work/scratch/ndfc81-20261001-1.owner-b12fe7d1ca5d5dc8714810d657fe6c65`.

If and only if an independent review releases this exact committed/fetched
packet, the sole outer command is:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndfc81-20261001-1 --nonce b12fe7d1ca5d5dc8714810d657fe6c65 --owner-sha256 c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-files-c81-20261001-1/manifest.json --manifest-sha256 51541adecd6ffc2cbc182d267ffd976b4e39ba4e3e3f44580c0d73ce09ef7513
```

Use the inherited `SUDO_ASKPASS` only through `sudo -A`; never inspect or
invoke its helper.

All three paths must be absent at preflight. The coordinator must bind the
nonce once, create the parent once as uid/gid 1000 mode 0700, and never retry,
reuse, or substitute an identity after start, uncertainty, timeout, or
failure. The parent and owner sibling must be fresh and distinct from every
retained memory attempt.

## Prepared manifest and exact inputs

Prepared manifest:
`/home/holden/mckernel-work/scratch/native-diagnostic-files-c81-20261001-1/manifest.json`
(4,712 bytes, mode 0600), SHA-256
`51541adecd6ffc2cbc182d267ffd976b4e39ba4e3e3f44580c0d73ce09ef7513`.
Its case is `baseline.core.files`, schema 1, and its payload is exactly:

    argv=/bin/mcexec -t 1 0 app files
    cwd=/case/work
    env=COKERNEL_PATH=/apps;PATH=/usr/bin:/bin
    expected exit=37
    expected stderr hex=(empty)
    expected stdout hex=4e41544956455f434f524520504153532066696c65730a
    stdout/stderr limits=1024/1024 bytes

The strict loader must authenticate every manifest path, mode, size and hash
before launch. Exact artifact/input hashes are:

| Artifact/input | Size | Mode | SHA-256 |
|---|---:|---:|---|
| scratch12 Linux `bzImage` | 16130048 | 0644 | `c995dfd141a6c2fb64c293a7e5b37fc5954008d1dfceb3d778910aa76261985e` |
| base/root initramfs | 12303864 | 0600 | `ed55400792c0fcb25f861062158b059d8db5b4d18399a33407f4e33b42138466` |
| c81 McKernel image | 7908256 | 0755 | `fa6685543160fcaa5000b535ec8bd6fc70230465109564c3fb2beecb95bf39ed` |
| corrected `mcexec` | 453352 | 0755 | `ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b` |
| files payload | 39488 | 0755 | `558d1607e4648321c9537215084e759496937d9591c319a21443f443193fda9a` |
| native boot | 30984 | 0755 | `4558995ea1ae70c8d5a115542e333ad695a54b4b8f450ea717df37fd1e631af3` |
| dynamic loader | 930600 | 0755 | `0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b` |
| libc | 2339896 | 0755 | `b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4` |
| `ihk.ko` | 1425960 | 0644 | `b4dbf04c47c8b8175462982cfee6e833bd40a2b7d6cadd947d68d4612c97dc9f` |
| `ihk-smp-x86_64.ko` | 11075136 | 0644 | `268d6d3b36fd33f9650c5b7b3ae5233e606d07c992e1e0c4be64493527f84bbb` |
| `mcctrl.ko` | 1914824 | 0644 | `d927bc4460d23c175660f0a23ad8d9dec79b9e5c144e4ae0c898091bcc98a019` |
| files collector | 1021296 | 0700 | `44bdb28f6c57d28eee9959bb729a51e56fb67026fcae3d5d5f43159d0b651ab6` |
| derived files overlay | 12891590 | 0600 | `c470d9f6c3e974f59c71c251024556254e74d125a8905a2eabb9e5d58cd151a0` |
| overlay representation | 15067 | 0600 | `cb9342e7065d8507b2e11339309cb84cf326ebfa21a4571cc4f97438383bc6a6` |
| overlay source | 26579 | 0600 | `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d` |

The derived overlay is
`/home/holden/mckernel-work/scratch/native-diagnostic-files-c81-20261001-1/initramfs.cpio.gz`;
its representation is `.../overlay-result.json`. Runtime source hashes are
owner `c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7`,
runner `25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499`,
diagnostic `65a2b9ee037fdf21255a3500bbac408bd9a0916467375c252d04c6356ca50043`,
backend `cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614`,
QMP `5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741`,
and overlay `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d`.

## Pinned profile, isolation and lease rules

Use only the reviewed profile: container uid/gid 1000, CPUs 2-5 (4 CPUs),
12 GiB container memory with no additional swap, pids 512, no network, all capabilities
dropped, no-new-privileges, read-only inputs, and only the private attempt
parent writable. The pinned image is
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`;
authenticate `/home/holden/mckernel-work/logs/image-native.json` SHA-256
`c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
Guest QEMU is q35/TCG, 4 vCPUs, 8 GiB, 2 NUMA nodes, no NIC/display, `-S`,
private QMP, one McKernel CPU and 128 MiB. Do not widen either profile.

Before release, measure at least 16 GiB host and 12 GiB scratch free plus
headroom; reconcile and acquire the serialized heavy-runtime/launcher lease.
Prove no matching owner, QEMU, mcexec, Docker client or container is live.
On any unexpected process, lease conflict, hash mismatch, path collision,
truncation, timeout or failed oracle, stop immediately, retain all evidence,
and do not retry. Cleanup must be authenticated: preserve raw streams/status,
serial/debugcon/kernel log, full QMP and argv, Docker identities/statuses,
inspect/OOM state, owner/root-lock/cgroup identities, first and secondary
failures, then prove authenticated container absence, owner/QEMU/Docker-client
retirement and development-lock release. Preserve the parent, attempt and
root-owned evidence sibling with their exact identities and captured bytes;
never delete or rewrite diagnostic or prior failure evidence.

This diagnostic observes the files path only. A pass is diagnostic evidence,
not formal application acceptance, production acceptance, or a memory-path
claim. The packet remains **NOT_RELEASED** until independent review binds the
packet hash, coordinator-selected nonce/paths, command, and fresh preflight.
