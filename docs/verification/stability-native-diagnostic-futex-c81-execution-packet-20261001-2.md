# Native c81 direct-futex diagnostic execution packet 2

Status: **NOT_RELEASED**. This is the sole bounded correction after the
preserved packet-1 evaluator failure. It grants no application, production,
shutdown, catalog, release, or Rust/assembly acceptance and no runtime authority
until an independent reviewer binds this exact packet at a fetched commit and
repeats fresh live preflight.

## Fresh identity and sole command

Fresh nonce: `01d30ee0c82232c5efe4a3d810fe8af7`. Fresh parent:
`/home/holden/mckernel-work/scratch/ndfutexc81-20261001-2`; sole inner attempt:
`.../attempt-01d30ee0c82232c5efe4a3d810fe8af7`; root evidence sibling:
`/home/holden/mckernel-work/scratch/ndfutexc81-20261001-2.owner-01d30ee0c82232c5efe4a3d810fe8af7`.
Resolve each once. Never retry, reuse, rename, or substitute.

If and only if separately released, issue exactly:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndfutexc81-20261001-2 --nonce 01d30ee0c82232c5efe4a3d810fe8af7 --owner-sha256 e530a2dba473d8da6a8cb21db570eb121d16cff28be1e298fdb21f22d4ee9b60 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-futex-c81-20261001-4/manifest.json --manifest-sha256 5c0925bc4c5a59c6728187577d91599b7cdd395858feca69c719e5bf00d88dc9
```

Use inherited `SUDO_ASKPASS` only through `sudo -A`; never inspect/invoke it.
Create only the parent, once, uid/gid 1000 and mode 0700. All three selected
paths must be absent at preflight.

## Preserved failure and bounded correction

Packet 1 at fetched commit `0440661f6d80fb6723a44da08444947b161d858c`
ran once with nonce `1a9f699e18ae309d0cb9205564458ab0` and is immutable
FAIL. Its exact record is
`docs/verification/evidence/native-exact-c81-futex-diagnostic-failure-20261001.json`
at fetched commit `b77d815c22f9ca77c3cb0b4d6929502eb74b6288`. The
application emitted exact PASS stdout, exit 37 and complete typed stderr, but
the evaluator expected the historical record order. Never reuse packet 1,
nonce 1, its parent, or its evidence paths.

The correction does not change the payload, collector, candidate image,
expected values, bounds or profile. It adds a required typed-oracle
`record_order`. This manifest selects `current-source-v1`, which requires
exactly 16 ordered CASE lines, then THREADS, then CLONE. The other permitted
variant, `historical-split-v1`, exists only for authenticated historical replay
and requires 15 CASE, CLONE, final CASE, THREADS. Each rejects the other's
bytes. All case identity/result/errno, time/deadline, TID, clone, count and
stream completeness checks remain unchanged.

Corrected sources are evaluator
`2aa9b0257395624ced3ecb4d9e4d3e9373310a9266653b1d1f3cec9d2c8f9356`,
owner `e530a2dba473d8da6a8cb21db570eb121d16cff28be1e298fdb21f22d4ee9b60`,
runner `25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499`,
backend `cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614`
and QMP `5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741`.

## Exact corrected manifest and unchanged artifacts

Manifest:
`/home/holden/mckernel-work/scratch/native-diagnostic-futex-c81-20261001-4/manifest.json`,
6,125 bytes, mode 0600, SHA-256
`5c0925bc4c5a59c6728187577d91599b7cdd395858feca69c719e5bf00d88dc9`.
Contract:

    argv=/bin/mcexec -t 1 0 /apps/app
    cwd=/case/work
    env=COKERNEL_PATH=/apps;PATH=/usr/bin:/bin
    stdout=NATIVE_ULTRA_FUTEX PASS cases=16 threads=2 raw_clone=1\n
    stderr=native-ultra-futex-v1/current-source-v1, 18 lines
    stdout/stderr bounds=4096/4096 bytes
    exit=37

| Artifact/input | Size | Mode | SHA-256 |
|---|---:|---:|---|
| Linux `bzImage` | 16130048 | 0644 | `c995dfd141a6c2fb64c293a7e5b37fc5954008d1dfceb3d778910aa76261985e` |
| base initramfs | 12303864 | 0600 | `ed55400792c0fcb25f861062158b059d8db5b4d18399a33407f4e33b42138466` |
| c81 McKernel image | 7908256 | 0755 | `fa6685543160fcaa5000b535ec8bd6fc70230465109564c3fb2beecb95bf39ed` |
| `mcexec` | 453352 | 0755 | `ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b` |
| direct-futex payload | 45304 | 0755 | `9593e5f1f17736d8be4f720691df5da3b636e21bc82fbc5391baa894969b2ecc` |
| native boot | 30984 | 0755 | `4558995ea1ae70c8d5a115542e333ad695a54b4b8f450ea717df37fd1e631af3` |
| loader | 930600 | 0755 | `0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b` |
| libc | 2339896 | 0755 | `b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4` |
| `ihk.ko` | 1425960 | 0644 | `b4dbf04c47c8b8175462982cfee6e833bd40a2b7d6cadd947d68d4612c97dc9f` |
| `ihk-smp-x86_64.ko` | 11075136 | 0644 | `268d6d3b36fd33f9650c5b7b3ae5233e606d07c992e1e0c4be64493527f84bbb` |
| `mcctrl.ko` | 1914824 | 0644 | `d927bc4460d23c175660f0a23ad8d9dec79b9e5c144e4ae0c898091bcc98a019` |
| ND_FUTEX collector | 1021296 | 0700 | `3833fd03dbfeb0d2db6d03cc07399ec4b9a64fb6e2f892f5d7be2c0fafdb2e69` |
| derived overlay | 12894522 | 0600 | `08afffe000231b1ff4f1d87efd7c74e5e098473a7082c5d6e8298abe691d0efc` |
| overlay representation | 13783 | 0600 | `fd5feac712acce95361a7f2b33024be697bdb58334e7b70cb26570bbba0b0c97` |
| overlay source | 26579 | 0600 | `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d` |

The decompressed base CPIO remains 39,366,656 bytes at
`defbea55bebd9dc8c009e1317183bb08988d467911a41cb59c7e09dc59647b23`.
The corrected overlay is byte-identical to attempts 1-3 because only the
manifest oracle changed. Its retained stderr is empty. The preserved failed
guest stderr (2,610 bytes,
`64e45bd32c9605a28ea809ed5b0d1fc8205a77228ffde7f32bf11291c2132a2c`)
passes the corrected current-source parser in offline replay; that replay is
source validation only and does not reclassify packet 1.

## Pinned execution, evidence and stop rules

Use the already reviewed container image
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`
and record `c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
Container: uid/gid 1000, CPUs 2-5, 12 GiB, no added swap, pids 512, network
none, all capabilities dropped, no-new-privileges, inputs read-only and only
the private parent writable. Guest: q35/TCG, four vCPUs, 8 GiB/two NUMA nodes,
no NIC/display, `-S`, private QMP, one McKernel CPU and 128 MiB. Do not widen.

Before release require at least 16 GiB host and 12 GiB scratch free plus
headroom, the sole heavy lane free, packet-1 container/owner/QEMU/mcexec/client
retirement, development lock availability and the three fresh paths absent.
Any mismatch, timeout, truncation, identity, oracle or cleanup uncertainty stops
without another retry. Preserve full raw streams/status, serial/debugcon/kernel
log, QMP/argv, Docker inspect/OOM and command records, process/cgroup/lock
identities, first/secondary failures and authenticated postflight absence.

A pass is only bounded current-candidate direct-futex diagnostic evidence. It
does not establish formal application/catalog acceptance, general futex
completeness, shutdown correctness, production readiness or OS completion.
