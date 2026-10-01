# Native scratch18 threads diagnostic execution packet 1

Status: **NOT_RELEASED**. One-shot diagnostic proposal only; no application,
production, release, or Rust/assembly acceptance and no runtime authority.
Independent review must bind this exact packet SHA-256, the manifest/source
hashes, coordinator identity, and a fresh live preflight before setup or launch.

## Coordinator identity and command

The fresh nonce is `8a5c4f6e0eab4e17b4c7f09e6a2d3scratch18`. Its parent is
`/home/holden/mckernel-work/scratch/ndt18-20261001-1`, its sole inner attempt
is `.../attempt-8a5c4f6e0eab4e17b4c7f09e6a2d3scratch18`, and the distinct root-owned
evidence sibling is
`/home/holden/mckernel-work/scratch/ndt18-20261001-1.owner-8a5c4f6e0eab4e17b4c7f09e6a2d3scratch18`.
Resolve each once; never retry, reuse, or substitute after start, uncertainty,
timeout, or failure.

If and only if independently released, the sole command is:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndt18-20261001-1 --nonce 8a5c4f6e0eab4e17b4c7f09e6a2d3scratch18 --owner-sha256 c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-scratch18-threads-runtime-20261001-1/manifest.json --manifest-sha256 23d0218399883c5f7990ca6b1faca3ea7735de4242875f2fbda4628a68794e44
```

Use inherited `SUDO_ASKPASS` only through `sudo -A`; never inspect or invoke
it. All selected paths must be absent at preflight. Create the parent once as
uid/gid 1000, mode 0700. This command is one-shot.

## Prepared manifest and exact contract

Manifest:
`/home/holden/mckernel-work/scratch/native-diagnostic-scratch18-threads-runtime-20261001-1/manifest.json`,
mode 0600, SHA-256
`23d0218399883c5f7990ca6b1faca3ea7735de4242875f2fbda4628a68794e44`.
`PASS_THREADS_MANIFEST_SCRATCH18` authenticates schema 1, case
`baseline.core.threads`, every path/mode/size/hash, and:

    argv=/bin/mcexec -t 1 0 app threads
    cwd=/case/work
    env=COKERNEL_PATH=/apps;PATH=/usr/bin:/bin
    expected exit=37
    expected stderr hex=(empty)
    expected stdout hex=4e41544956455f434f5245205041535320746872656164730a
    stdout/stderr limits=1024/1024 bytes

| Artifact/input | Size | Mode | SHA-256 |
|---|---:|---:|---|
| scratch12 Linux `bzImage` | 16130048 | 0644 | `c995dfd141a6c2fb64c293a7e5b37fc5954008d1dfceb3d778910aa76261985e` |
| base/root initramfs | 12303864 | 0600 | `ed55400792c0fcb25f861062158b059d8db5b4d18399a33407f4e33b42138466` |
| scratch18 McKernel image | 7908256 | 0755 | `fa6685543160fcaa5000b535ec8bd6fc70230465109564c3fb2beecb95bf39ed` |
| corrected `mcexec` | 453352 | 0755 | `ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b` |
| threads payload | 39488 | 0755 | `558d1607e4648321c9537215084e759496937d9591c319a21443f443193fda9a` |
| native boot | 30984 | 0755 | `4558995ea1ae70c8d5a115542e333ad695a54b4b8f450ea717df37fd1e631af3` |
| dynamic loader | 930600 | 0755 | `0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b` |
| libc | 2339896 | 0755 | `b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4` |
| `ihk.ko` | 1425960 | 0644 | `b4dbf04c47c8b8175462982cfee6e833bd40a2b7d6cadd947d68d4612c97dc9f` |
| `ihk-smp-x86_64.ko` | 11075136 | 0644 | `268d6d3b36fd33f9650c5b7b3ae5233e606d07c992e1e0c4be64493527f84bbb` |
| `mcctrl.ko` | 1914824 | 0644 | `d927bc4460d23c175660f0a23ad8d9dec79b9e5c144e4ae0c898091bcc98a019` |
| threads collector | 1021296 | 0700 | `9dd9388b34283779c8bb6c8d8c7779ef0e44e9480775a4a3244f50b3240e9b10` |
| derived threads overlay | 12891593 | 0600 | `20749f16b12ac9bffe8080fdb013831b26684456a4aba4383016220970fc33a6` |
| overlay representation | 15069 | 0600 | `620a02b7ae3b59389a487e53bf77811057334d14e929ad2b7dcace426a72d553` |
| overlay source | 26579 | 0600 | `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d` |

Derived overlay:
`/home/holden/mckernel-work/scratch/native-diagnostic-scratch18-threads-runtime-20261001-1/initramfs.cpio.gz`;
representation: `.../overlay-result.json`. The strict loader authenticates
every manifest path, mode, size and hash before launch. Runtime hashes are
owner `c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7`,
runner `25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499`,
diagnostic `65a2b9ee037fdf21255a3500bbac408bd9a0916467375c252d04c6356ca50043`,
backend `cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614`,
QMP `5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741`,
and overlay `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d`.

## Pinned profile, evidence and stop rules

Use only uid/gid 1000, CPUs 2-5 (4 CPUs), 12 GiB memory with no additional
swap, pids 512, no network, all capabilities dropped, no-new-privileges,
read-only inputs and only the private parent writable. Image:
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`;
authenticate `/home/holden/mckernel-work/logs/image-native.json` SHA-256
`c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
Guest QEMU is q35/TCG, 4 vCPUs, 8 GiB, 2 NUMA nodes, no NIC/display, `-S`,
private QMP, one McKernel CPU and 128 MiB. Do not widen these profiles.

Before release, measure at least 16 GiB host and 12 GiB scratch free plus
headroom; acquire the serialized heavy-runtime/launcher lease; prove no owner,
QEMU, mcexec, Docker client or matching container is live. Any unexpected
process, lease conflict, hash mismatch, path collision, truncation, timeout or
failed oracle stops work immediately with no retry. Preserve raw streams/status,
serial/debugcon/kernel log, complete QMP/argv, Docker identities/statuses,
inspect/OOM state, owner/root-lock/cgroup identities, first and secondary
failures, and authenticated cleanup/absence. Never delete or rewrite evidence.

This observes threads only. Require scheduling, clone/thread/TID/futex behavior,
syscall delivery/return/route, exit-group, retirement, procfs deletion,
pager/process release and teardown. The prior threads packet's wrong
expected-hash/oracle failure and corrected record remain preserved; they are not
reclassified. Startup, memory and files packets are consumed, non-reusable
history. A pass is diagnostic evidence only. This packet remains **NOT_RELEASED**
until exact-hash review and fresh preflight pass.
