# Scratch18 baseline.core.memory diagnostic execution packet 1

Status: **NOT_RELEASED**. One-shot diagnostic proposal only; no formal
application, production, or OS acceptance.

Fresh nonce `236e282ab19f24ce60cbd9ce357fea1d`; parent
`/home/holden/mckernel-work/scratch/ndms18-20261001-1`; only attempt
`attempt-236e282ab19f24ce60cbd9ce357fea1d`; root evidence sibling
`/home/holden/mckernel-work/scratch/ndms18-20261001-1.owner-236e282ab19f24ce60cbd9ce357fea1d`.
All must be absent during independent review. After release, create the parent
once as uid/gid 1000 mode 0700 and invoke exactly once:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndms18-20261001-1 --nonce 236e282ab19f24ce60cbd9ce357fea1d --owner-sha256 e530a2dba473d8da6a8cb21db570eb121d16cff28be1e298fdb21f22d4ee9b60 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-scratch18-memory-runtime-20261001-1/manifest.json --manifest-sha256 1bdb2471c5c09d25d6b544892ed2a06377e2b345da8d819fafb18977406a593a
```

The strict manifest is 5,445 bytes, mode 0600, inode `1831:6685867`.
Case `baseline.core.memory` runs exact argv
`/bin/mcexec -t 1 0 app memory`, cwd `/case/work`, frozen PATH/COKERNEL_PATH,
and requires exit 37, empty stderr and stdout `NATIVE_CORE PASS memory\n`
(hex `4e41544956455f434f52452050415353206d656d6f72790a`).

It binds scratch18 image SHA `fa668554...39ed` and module SHAs
`db003ffd...2519`, `268d6d3b...4bbb`, `4cf6196f...23f`; the full exact
hashes and canonical paths are in the manifest. Base initramfs SHA is
`1497e9e188ac818fef5f4cba8f7ae7b62b32705468ab51dad9a51169db89b53d`;
derived memory initramfs SHA is
`13a6de8d244c21289fd40ff7aad104f2af2acf5ab6b6dfaf46c06055a41e2880`;
overlay record SHA is
`590a66185e934bd24bcb52ea7f066f25e896d59824824495a7a71b8e6f585976`.
Payload SHA is `558d1607...fda9a`, collector SHA `247433d6...0556`, corrected
mcexec SHA `ee1f660b...073b`, and retained bzImage SHA `c995dfd1...985e`.

Keep the already reviewed runtime profile unchanged: pinned container image,
CPUs 2-5/four CPUs, 12 GiB/no swap, 512 PIDs, no network, all capabilities
dropped, no-new-privileges and only the attempt parent writable; q35/TCG,
four vCPUs, 8 GiB, two NUMA nodes, no NIC/display, one McKernel CPU/128 MiB.
Independent release must authenticate every manifest file and source hash,
verify the exact container image/config, remeasure the 16/12-GiB host/scratch
floors, and prove the heavy lane, development lock, owner/QEMU/mcexec/client
and container namespaces are free. Any drift, collision or uncertainty stops
without retry. Preserve all streams, serial/debugcon, QMP, kernel/runtime logs,
Docker/OOM/cgroup/lock identities, retirement and cleanup evidence.
