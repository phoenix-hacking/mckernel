# Scratch18 baseline.core.threads diagnostic execution packet 2

Status: **NOT_RELEASED**. This replaces packet 1's invalid nonce and broken
base/derived join. Packet 1 and runtime preparation 1 remain preserved as a
source-only failure. This packet is one-shot diagnostic authority only after
independent release; it is not formal application, production, or OS acceptance.

Fresh nonce `8a5c4f6e0eab4e17b4c7f09e6a2d3c81`; parent
`/home/holden/mckernel-work/scratch/ndt18-20261001-2`; root evidence sibling
uses the same parent plus `.owner-<nonce>`. All must be absent. Exact command:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndt18-20261001-2 --nonce 8a5c4f6e0eab4e17b4c7f09e6a2d3c81 --owner-sha256 a3efa2ef4f6deb2fc1938bd3723b90baf6b8d30c60faf079ada0e2cd0f69deec --manifest /home/holden/mckernel-work/scratch/native-diagnostic-scratch18-threads-runtime-20261001-2/manifest.json --manifest-sha256 b3e5ba0cb54c42595e1b0ce751cf5276fd55df7cde2b52ace304fb45e421f550
```

Manifest is 5,452 bytes, mode 0600. It binds scratch18 image `fa668554...39ed`,
modules `db003ffd...2519` / `268d6d3b...4bbb` / `4cf6196f...23f`, corrected
mcexec, retained bzImage and exact libc closure. Base initramfs is
`1497e9e1...9b53d`; fresh derived initramfs is
`e15497c00fd689a28e1677b74fcad421cb42bfda19790e7920144d2d066c285a`;
overlay record is `770bb8d9d423a8b037a380593d36e5657238fa6a63b3a7b3aae1b56513259c02`.
Current runtime source hashes include diagnostic `13406216...9261` and owner
`a3efa2ef...deec`; exact full hashes are bound by the owner.

Run `/bin/mcexec -t 1 0 app threads` in `/case/work` with frozen environment.
Require exit 37, empty stderr and exact stdout `NATIVE_CORE PASS threads\n`.
Keep the reviewed outer CPUs2-5/4CPU/12GiB/no-swap/512PID/no-network profile
and retained 4-vCPU/8-GiB/two-NUMA guest. Before release authenticate every
file and full 59-member replay, the pinned container image/config, capacity
floors, sole heavy lane, development lock and absence of owners/QEMU/mcexec/
clients/containers. Stop on any drift or uncertainty. Preserve all raw streams,
serial/debugcon/kernel/QMP, TID/futex/retirement and cleanup evidence.
