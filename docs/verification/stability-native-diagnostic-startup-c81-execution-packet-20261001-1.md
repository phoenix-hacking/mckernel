# Native c81 startup.argv-empty diagnostic execution packet 1

Status: **NOT_RELEASED**. This is a one-shot, diagnostic-only proposal. It is
not application, production, or release acceptance. No execution is permitted
until an independent reviewer binds this exact packet hash, the manifest and
all source/artifact hashes below, then approves a fresh live preflight.

## Coordinator-bound identity and exact command

The fresh nonce is `26e1561d2a993a8fc687324f3a84bfb4`. Its parent is
`/home/holden/mckernel-work/scratch/ndsc81-20261001-1`, its only permitted
attempt is `.../attempt-26e1561d2a993a8fc687324f3a84bfb4`, and its root-owned
evidence sibling is
`/home/holden/mckernel-work/scratch/ndsc81-20261001-1.owner-26e1561d2a993a8fc687324f3a84bfb4`.
All must be absent during review and preflight. The sole command, after
independent release, is:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndsc81-20261001-1 --nonce 26e1561d2a993a8fc687324f3a84bfb4 --owner-sha256 c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-startup-c81-20261001-1/manifest.json --manifest-sha256 7f7a7150142848e315676ed3fba09847e5f52c9f7b0491858ab65467268439fb
```

Use `SUDO_ASKPASS` only through `sudo -A`; never inspect or invoke its helper.
The coordinator must bind the nonce once, create the parent once as uid/gid
1000 mode 0700, and never retry after start, uncertainty, timeout, or failure.

## Prepared manifest, case and oracle

Prepared manifest:
`/home/holden/mckernel-work/scratch/native-diagnostic-startup-c81-20261001-1/manifest.json`
(5,470 bytes, mode 0600), SHA-256
`7f7a7150142848e315676ed3fba09847e5f52c9f7b0491858ab65467268439fb`.
It is schema 1, case `startup.argv-empty`, with cwd `/case/work`, environment
`COKERNEL_PATH=/apps;PATH=/usr/bin:/bin`, and exact launcher argv:

```text
/bin/mcexec -t 1 0 app A "" B
```

The empty argument is literal and must be preserved. Expected exit is `0`,
stderr is empty, stdout is exactly the 91-byte hex string
`7b2263617365223a22737461727475702e617267762d656d707479222c2261726763223a342c2261726776223a5b22617070222c2241222c22222c2242225d2c227465726d696e61746f725f69735f6e756c6c223a747275657d0a`.
Both stream limits are 1024 bytes.

## Immutable inputs

The strict loader must authenticate every path, mode, size and digest in the
manifest before launch. The c81 McKernel image is
`fa6685543160fcaa5000b535ec8bd6fc70230465109564c3fb2beecb95bf39ed`; base
initramfs is `ed55400792c0fcb25f861062158b059d8db5b4d18399a33407f4e33b42138466`;
scratch12 `bzImage` is
`c995dfd141a6c2fb64c293a7e5b37fc5954008d1dfceb3d778910aa76261985e`;
corrected `mcexec` is
`ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b`;
startup payload is
`ff227c83b2da598110768e13f5e042b437e049659706b56079cc73f7c818a836`;
native boot is
`4558995ea1ae70c8d5a115542e333ad695a54b4b8f450ea717df37fd1e631af3`;
loader is
`0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b`;
libc is
`b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4`.
The three modules are `b4dbf04c47c8b8175462982cfee6e833bd40a2b7d6cadd947d68d4612c97dc9f`,
`268d6d3b36fd33f9650c5b7b3ae5233e606d07c992e1e0c4be64493527f84bbb`, and
`d927bc4460d23c175660f0a23ad8d9dec79b9e5c144e4ae0c898091bcc98a019`.
The collector is `78426897fed245e0a8c81996a369896fb264acb9ceb5aab1e5990505d1db4ecb`.
The derived overlay is
`c2735cd31b59e280ad6b4276b4f432a7646a3b72a276e79375cdd1d789f95ab8`; its
representation is `6c9801770fbbfd1609ad92b5e29a603b7735768652b69b54f04c3999d8b0bbe8`.

## Runtime sources and pinned profile

Bind these reviewed sources exactly: owner
`c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7`, runner
`25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499`, diagnostic
`65a2b9ee037fdf21255a3500bbac408bd9a0916467375c252d04c6356ca50043`, backend
`cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614`, QMP
`5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741`,
and overlay `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d`.

Use only image `sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`,
manifest `/home/holden/mckernel-work/logs/image-native.json` SHA-256
`c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`, uid/gid
1000, CPUs 2-5, 12 GiB memory with no additional swap, pids 512, no network,
all capabilities dropped, no-new-privileges, read-only inputs and only the
private attempt parent writable. Guest QEMU is q35/TCG, 4 vCPUs, 8 GiB, two
NUMA nodes, no NIC/display, `-S`, private QMP, one McKernel CPU and 128 MiB.
Do not widen this profile or add swap.

## Release, oracle and retention gates

Before release, measure at least 16 GiB host and 12 GiB scratch free plus
headroom; acquire the serialized heavy-runtime/launcher lease and prove no
matching owner, QEMU, mcexec, Docker client or container is live. Any hash or
path mismatch, collision, unexpected process, truncation, timeout, failed
oracle, or cleanup uncertainty is an immediate stop with no retry.

Retain raw stdout/stderr/status, serial/debugcon/kernel log, full QMP and argv,
Docker identities/statuses, inspect/OOM state, owner/root-lock/cgroup identities,
first and secondary failures, and authenticated absence/lease-release proof.
Preserve the parent, attempt and root-owned evidence sibling with exact
identities and bytes. Cleanup must authenticate container absence, owner/QEMU/
Docker-client retirement and development-lock release; never delete or rewrite
diagnostic evidence or prior failures.

This one-shot observes startup argv propagation only. A pass is diagnostic
evidence, not application acceptance, production acceptance, or any memory,
files, threads, or signals claim. Status remains **NOT_RELEASED** until an
independent reviewer binds this packet hash, fresh coordinator identity,
command, manifest, and live preflight.
