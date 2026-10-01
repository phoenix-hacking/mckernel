# Scratch18 startup.argv-empty diagnostic execution packet 1

Status: **NOT_RELEASED**. This is a one-shot diagnostic proposal only; it is
not application, production, or OS acceptance.

## Exact identity and command

The fresh nonce is `19972bcaaec2c3904d4102e50c0f2dd5`. The parent is
`/home/holden/mckernel-work/scratch/ndss18-20261001-1`, the sole attempt is
`attempt-19972bcaaec2c3904d4102e50c0f2dd5`, and the root evidence sibling is
`/home/holden/mckernel-work/scratch/ndss18-20261001-1.owner-19972bcaaec2c3904d4102e50c0f2dd5`.
All are absent at preparation. After an independent live release, run once:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndss18-20261001-1 --nonce 19972bcaaec2c3904d4102e50c0f2dd5 --owner-sha256 e530a2dba473d8da6a8cb21db570eb121d16cff28be1e298fdb21f22d4ee9b60 --manifest /home/holden/mckernel-work/scratch/native-diagnostic-scratch18-startup-runtime-20261001-1/manifest.json --manifest-sha256 c3a04371e9e67a861718a096dc3fd9f530ea7c66750a45caf71faa144f8f0c65
```

Use `sudo -A` only through the inherited askpass configuration. Create the
parent once as uid/gid 1000 mode 0700 only after release. Never retry this
nonce after start, uncertainty, timeout, or failure.

## Bound fixture and oracle

The strict schema-1 manifest is 5,586 bytes, mode 0600, inode
`1831:6685863`, SHA-256
`c3a04371e9e67a861718a096dc3fd9f530ea7c66750a45caf71faa144f8f0c65`.
Its case is `startup.argv-empty`, cwd `/case/work`, exact argv
`/bin/mcexec -t 1 0 app A "" B`, environment
`COKERNEL_PATH=/apps;PATH=/usr/bin:/bin`, expected exit 0, empty stderr, and
exact 91-byte stdout hex
`7b2263617365223a22737461727475702e617267762d656d707479222c2261726763223a342c2261726776223a5b22617070222c2241222c22222c2242225d2c227465726d696e61746f725f69735f6e756c6c223a747275657d0a`.

The newly linked scratch18 image is
`fa6685543160fcaa5000b535ec8bd6fc70230465109564c3fb2beecb95bf39ed`.
Scratch18 modules are, in load order,
`db003ffdbd2f939badac7753a1df08b9daf4a80544bf812e53ba1276fbd62519`,
`268d6d3b36fd33f9650c5b7b3ae5233e606d07c992e1e0c4be64493527f84bbb`,
and `4cf6196f9e93fb10b08bc4e5bf75022b0858779a6479910340941006748cd23f`.
The base initramfs is `1497e9e188ac818fef5f4cba8f7ae7b62b32705468ab51dad9a51169db89b53d`;
the derived startup initramfs is
`cddd79ea053558a4eefc7e79fa5cf4920917b3f0e40a5c7206259d5ef888b7d1`;
the authenticated overlay record is
`f92bc9e631e81ebce693680155f983864e34f217ba35925c43f10167b41a9b10`.
The retained scratch12 bzImage remains
`c995dfd141a6c2fb64c293a7e5b37fc5954008d1dfceb3d778910aa76261985e`.

Runtime source hashes are owner `e530a2d...e9b60`, runner
`25ea29f...499`, diagnostic `2aa9b02...9356`, backend `cd0759c...614`,
QMP `5bccd46...741`, and overlay `46d41bc...ba27d`; the exact full hashes are
bound in the owner and manifest. Use only container image
`sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`
and image record SHA-256
`c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.

## Profile and release boundary

Keep the reviewed profile unchanged: CPUs 2-5, four Docker CPUs, 12 GiB with
no swap, 512 PIDs, no network, dropped capabilities, no-new-privileges,
read-only inputs, one private writable attempt parent; q35/TCG guest with four
vCPUs, 8 GiB, two NUMA nodes, no NIC/display, one McKernel CPU and 128 MiB.

Independent release must reauthenticate the manifest and every referenced
regular file, confirm at least 16 GiB host and 12 GiB scratch free, acquire the
sole heavy-runtime/development lease, and prove no owner/QEMU/mcexec/client or
diagnostic container collision. Preserve stdout, stderr, status, serial,
debugcon, kernel log, QMP, argv, Docker/OOM/cgroup/lock identities and all
cleanup evidence. Any mismatch or uncertainty stops without retry. A pass is
one diagnostic startup result only.
