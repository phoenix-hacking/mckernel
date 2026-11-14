# Scratch18 baseline.core.files diagnostic execution packet 1

Status: **NOT_RELEASED**. One-shot diagnostic proposal only; no formal
application, production, or OS acceptance.

Fresh nonce `d427db8a1c1d5e0a50f8b9b1705ab9fb`; parent
`/home/holden/mckernel-work/scratch/ndfs18-20261001-1`; only attempt
`attempt-d427db8a1c1d5e0a50f8b9b1705ab9fb`; root evidence sibling
`/home/holden/mckernel-work/scratch/ndfs18-20261001-1.owner-d427db8a1c1d5e0a50f8b9b1705ab9fb`.
All must be absent during independent review. After release, create the parent
once as uid/gid 1000 mode 0700 and invoke exactly once:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndfs18-20261001-1 --nonce d427db8a1c1d5e0a50f8b9b1705ab9fb --owner-sha256 e530a2dba473d8da6a8cb21db570eb121d16cff28be1e298fdb21f22d4ee9b60 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-scratch18-files-runtime-20261001-1/manifest.json --manifest-sha256 b35af7d80625b41a2b74aae84b451fcd1dd2ef02b917cf0307e5b1d5153cf9a9
```

The strict manifest is 5,438 bytes, mode 0600, inode `1831:6685972`.
Case `baseline.core.files` runs exact argv `/bin/mcexec -t 1 0 app files`,
cwd `/case/work`, frozen PATH/COKERNEL_PATH, and requires exit 37, empty stderr
and stdout `NATIVE_CORE PASS files\n` (hex
`4e41544956455f434f524520504153532066696c65730a`).

It binds scratch18 image SHA `fa668554...39ed` and exact module SHAs
`db003ffd...2519`, `268d6d3b...4bbb`, `4cf6196f...23f` through the full
manifest paths/hashes. Base initramfs SHA is `1497e9e1...9b53d`; derived files
initramfs SHA is `bd92bf0d241f0e5a15d9a03be105347d062eb212d225445e6ef9eeaf8605bb3e`;
overlay record SHA is `10255d3b26a76275d1f541e8669d7af1e415549b8f8961ad6e604ba6e1ae3626`.
Payload SHA is `558d1607...fda9a`, files collector SHA `44bdb28f...1ab6`,
corrected mcexec SHA `ee1f660b...073b`, retained bzImage SHA `c995dfd1...985e`.

Keep the reviewed profile unchanged: pinned container image; CPUs 2-5/four
CPUs, 12 GiB/no swap, 512 PIDs, no network, dropped capabilities,
no-new-privileges and one private writable attempt parent; q35/TCG, four
vCPUs, 8 GiB, two NUMA nodes, no NIC/display, one McKernel CPU/128 MiB.
Independent release must authenticate every file/source and the full derived
replay, remeasure the 16/12-GiB host/scratch floors, and prove the sole heavy
lane, development lock, process and container namespaces free. Any drift,
collision or uncertainty stops without retry. Preserve stdout/stderr/status,
serial/debugcon/kernel log, QMP, Docker/OOM/cgroup/lock, retirement and cleanup.
