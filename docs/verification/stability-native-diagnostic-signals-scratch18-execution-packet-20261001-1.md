# Scratch18 signals diagnostic execution packet 1

Status: **NOT_RELEASED**. Diagnostic-only; no guest, Docker, sudo, or QEMU execution is authorized by this preparation task.

Fresh nonce: `fb2046b1ff643844f351e6e12c04b589`; parent:
`/home/holden/mckernel-work/scratch/ndsig18-20261001-1`. The eventual one-shot
command, only after independent release, is:

    /usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndsig18-20261001-1 --nonce fb2046b1ff643844f351e6e12c04b589 --owner-sha256 a3efa2ef4f6deb2fc1938bd3723b90baf6b8d30c60faf079ada0e2cd0f69deec --manifest /home/holden/mckernel-work/scratch/native-diagnostic-scratch18-signals-runtime-20261001-1/manifest.json --manifest-sha256 8a330f9c9fc4944f5190db972717aab718930c4ef3a55eb2401b4a91f0f7c43d

Manifest: `/home/holden/mckernel-work/scratch/native-diagnostic-scratch18-signals-runtime-20261001-1/manifest.json`, SHA-256 `8a330f9c9fc4944f5190db972717aab718930c4ef3a55eb2401b4a91f0f7c43d`.
It is schema 1, case `baseline.core.signals`, with real argv
`/bin/mcexec -t 1 0 app signals`, exit 37, exact stdout
`NATIVE_CORE PASS signals\n`, and empty stderr. The strict loader passes.

Derived initramfs:
`/home/holden/mckernel-work/scratch/native-diagnostic-scratch18-signals-runtime-20261001-1/initramfs.cpio.gz`, SHA-256
`7a270b5610e455c96703b2a36d81d5c3f112ffaf4a54c435e17e848066d4bcf1`, size
12872904 bytes. Overlay evidence `overlay-result.json` SHA-256
`380bd1cc8015af97ed1e2b055bbf3c1ee5657af1563a475bff7cc7f10d058ad6`.

The scratch18 image is `fa6685543160fcaa5000b535ec8bd6fc70230465109564c3fb2beecb95bf39ed`.
Modules are `db003ffdbd2f939badac7753a1df08b9daf4a80544bf812e53ba1276fbd62519`,
`268d6d3b36fd33f9650c5b7b3ae5233e606d07c992e1e0c4be64493527f84bbb`, and
`4cf6196f9e93fb10b08bc4e5bf75022b0858779a6479910340941006748cd23f`.
Corrected mcexec is `ee1f660b6c181bb2301bcde8b30c109659f74d52b30407fa6f273d27c02d073b`.

Before release independently re-authenticate every path, mode, size and
digest; prove fresh parent/attempt/owner evidence absence, heavy-runtime lease,
Docker/QEMU/mcexec absence, ownership, isolation, resource headroom and terminal
cleanup. Retain exact stdout/stderr, status, serial/kernel/QMP, process
identities and cleanup evidence. Use only the reviewed 4-vCPU/8-GiB guest and
4-CPU/12-GiB container profile; no concurrent heavy guests. Any mismatch,
collision, timeout, failed oracle or uncertain cleanup is terminal for this
one-shot. This is diagnostic evidence only and must not inflate acceptance.
