# Native c81 memory diagnostic execution packet 1

Status: **NOT_RELEASED**. This packet is a bounded proposal only. It cannot be
executed until (1) the separately retained exportset26 container is cleaned up
under its own reviewed release and (2) an independent execution reviewer binds
this exact packet SHA-256, source hashes, manifest and command. It is neither
application nor production acceptance.

Before such a release, this corrected packet and its exact referenced runtime
source checkpoint must be committed, pushed and fetched-byte verified. Only
then may an independent reviewer compare the exact packet/source bytes and
release the command. Immediately before setup and execution, a fresh live
preflight must reauthenticate those same bytes and every listed artifact.

## One-shot namespace and proposed command

The fresh nonce is `501c0c8cb323e0459d3f504d8b1d1c20`. Its parent is the
currently absent, short namespace
`/home/holden/mckernel-work/scratch/ndmc81-20261001-1`; it must stay absent
until an independent release creates it once as uid/gid 1000, mode 0700. The
only permitted inner name would be
`/home/holden/mckernel-work/scratch/ndmc81-20261001-1/attempt-501c0c8cb323e0459d3f504d8b1d1c20`.
The corresponding root-owned sibling would be
`/home/holden/mckernel-work/scratch/ndmc81-20261001-1.owner-501c0c8cb323e0459d3f504d8b1d1c20`.

If and only if released, the sole outer command is:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndmc81-20261001-1 --nonce 501c0c8cb323e0459d3f504d8b1d1c20 --owner-sha256 c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-memory-c81-manifest-20261001-1/manifest.json --manifest-sha256 ccc2150208b86f898f9d01a3a6f760d763cd2b661bb1585ad10f53cff26a6b30
```

Use `SUDO_ASKPASS` only through `sudo -A`; never read or invoke its helper.
After any start, uncertainty or failure, no retry is allowed.

## Static closure and strict manifest

Candidate `c81aeaca5cedd893981a058444fa11a03a49a744` has static c81 evidence:

| Evidence | Path | SHA-256 |
|---|---|---|
| Export26 build result | `docs/verification/evidence/native-exact-export26-heavy-build-success-20261001.json` | `9207ab9cfa88dd74592f9a0a7184065ca5a108c3f3760013ee2cbdbc6f1e4a31` |
| Postlink report, attempt 2 | `/home/holden/mckernel-work/scratch/native-exact-export26-postlink-validation-20261001-2/current-image-postlink-c81aeaca-exportset26-attempt2.json` | `a22efb04bdf122778e5a122b7ceec8abe887e30870e03bb0b3231531fb869445` |
| Linked-text ownership report | `/home/holden/mckernel-work/scratch/native-exact-export26-postlink-validation-20261001-1/mckernel-linked-text-ownership-c81aeaca-exportset26.json` | `23f83418101aea86c5400b34f2bf96c54b28e2b3936bb0309da88ff7d6f06a21` |
| Postlink/diagnostic preparation checkpoint | `docs/verification/evidence/native-exact-export26-postlink-diagnostic-preparation-checkpoint-20261001.json` | `91ff3b2cacec68da8a4eb399e72b18e2401d8163a2c842606070e7860a1596cc` |

The strict loader-validated manifest is
`/home/holden/mckernel-work/scratch/native-diagnostic-memory-c81-manifest-20261001-1/manifest.json`,
SHA-256 `ccc2150208b86f898f9d01a3a6f760d763cd2b661bb1585ad10f53cff26a6b30`,
size 4,709, mode 0600. Its immutable inputs are:

| Role | SHA-256 | Size | Mode |
|---|---|---:|---:|
| scratch12 Linux `bzImage` | `c995dfd141a6c2fb64c293a7e5b37fc5954008d1dfceb3d778910aa76261985e` | 16130048 | 0644 |
| base initramfs | `ed55400792c0fcb25f861062158b059d8db5b4d18399a33407f4e33b42138466` | 12303864 | 0600 |
| c81 McKernel image | `fa6685543160fcaa5000b535ec8bd6fc70230465109564c3fb2beecb95bf39ed` | 7908256 | 0755 |
| corrected mcexec | `ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b` | 453352 | 0755 |
| native-application-core memory payload | `558d1607e4648321c9537215084e759496937d9591c319a21443f443193fda9a` | 39488 | 0755 |
| native boot | `4558995ea1ae70c8d5a115542e333ad695a54b4b8f450ea717df37fd1e631af3` | 30984 | 0755 |
| dynamic loader | `0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b` | 930600 | 0755 |
| libc | `b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4` | 2339896 | 0755 |
| scratch12 ihk.ko | `b4dbf04c47c8b8175462982cfee6e833bd40a2b7d6cadd947d68d4612c97dc9f` | 1425960 | 0644 |
| scratch12 ihk-smp-x86_64.ko | `268d6d3b36fd33f9650c5b7b3ae5233e606d07c992e1e0c4be64493527f84bbb` | 11075136 | 0644 |
| scratch12 mcctrl.ko | `d927bc4460d23c175660f0a23ad8d9dec79b9e5c144e4ae0c898091bcc98a019` | 1914824 | 0644 |
| memory collector | `247433d68fa712f0f456366baead6040848832284b5ff14d89fced108b200556` | 1021296 | 0700 |
| attempt3 derived overlay | `e2684f7641f2ea6a8f69632371a34fbed3960e4af2cc5badd90ceca93c22eb8b` | 12891594 | 0600 |
| attempt3 overlay representation | `6821cce5d6c4fbb2b3def336d571edf214a79ce18b82c41ed5971780405c88db` | 13792 | 0600 |

The attempt3 derived overlay is
`/home/holden/mckernel-work/scratch/native-diagnostic-memory-c81-overlay-20261001-3`.
Its loader-format representation is
`/home/holden/mckernel-work/scratch/native-diagnostic-memory-c81-overlay-result-20261001-3.json`.
It binds the startup-stage base, the unchanged memory payload, collector and
corrected mcexec; the strict loader authenticates source identities and final-map
members before any launch.

## Runtime-source and reviewed profile closure

| Runtime source | SHA-256 |
|---|---|
| `scripts/application-tests/native_diagnostic_container_owner.py` | `c6a6423712fc117ebba9eb56b1e1af1aca718a1a9f1ec9d4ccfc15c2b33ac4b7` |
| `scripts/application-tests/native_diagnostic_runner.py` | `25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499` |
| `scripts/application-tests/native_diagnostic.py` | `65a2b9ee037fdf21255a3500bbac408bd9a0916467375c252d04c6356ca50043` |
| `scripts/application-tests/native_diagnostic_backend.py` | `cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614` |
| `scripts/application-tests/qmp_capture.py` | `5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741` |
| `scripts/application-tests/native_diagnostic_overlay.py` | `46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d` |

The PASS_CONTRACT_AUDIT profile remains unchanged: pinned image
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`
with record `/home/holden/mckernel-work/logs/image-native.json` SHA-256
`c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`;
uid/gid 1000, CPUs 2-5, four CPUs, 12 GiB memory and memory+swap, pids 512,
no network, all capabilities dropped, no-new-privileges, read-only inputs and
only the private attempt parent writable. Guest QEMU remains q35/TCG, four
vCPUs, 8 GiB, two NUMA nodes, no NIC/display, `-S`, private QMP, one McKernel
CPU and 128 MiB. Inner/outer deadlines are 300/360 seconds. Do not widen it.

The owner reconstructs the retained 42-argument QEMU form with the new attempt
paths, scratch12 `bzImage`, attempt3 overlay, fixed append argument
`console=ttyS0,115200n8 rdinit=/init nokaslr panic=-1 memmap=4K%0x80000-1`,
and a QMP socket below Linux's 107-byte usable pathname limit. It must compare
the complete argv before launch.

## Oracle, evidence and release gate

The only payload is `/bin/mcexec -t 1 0 app memory` in `/case/work`, with only
`PATH=/usr/bin:/bin` and `COKERNEL_PATH=/apps`. The oracle is exit 37, empty
stderr, and exact stdout hex:

```text
4e41544956455f434f52452050415353206d656d6f72790a
```

Both streams are bounded at 1,024 bytes, must reach EOF without truncation, and
the runner must prove scheduling, syscall delivery/return/route, exit-group,
retirement, procfs deletion and process-release joins. Preserve raw application
bytes/status, serial/debugcon/kernel log, complete QMP, QEMU argv/stdout/stderr/
status/identity, Docker-client identities and statuses, inspect/OOM state,
owner/root-lock/cgroup identities, first failure and every secondary evidence
failure, cleanup and final authenticated absence.

Before a release, remeasure host/scratch/RAM floors (at least 16/12 GiB free
plus packet headroom), reconcile launcher/heavy-runtime leases, prove no owner,
QEMU, mcexec, Docker client or matching container is live, authenticate all
listed files, and prove parent/attempt/evidence-sibling absence. Exportset26
cleanup and independent review are outstanding; therefore this document is
**NOT_RELEASED** and must not create the parent or invoke the command.
