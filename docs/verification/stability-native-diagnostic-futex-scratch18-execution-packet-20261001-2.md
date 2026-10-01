# Scratch18 diagnostic.native-ultra-futex execution packet 2

Status: **NOT_RELEASED**. This replaces packet 1's c81-derived archive mismatch;
packet 1 and runtime preparation 1 remain preserved as a source-only failure.
One-shot diagnostic scope only; no formal acceptance.

Fresh nonce `4e77144119439085593c17714867debd`; parent
`/home/holden/mckernel-work/scratch/ndfutexs18-20261001-2`; matching attempt and
root evidence sibling must be absent. Exact command after independent release:

```text
/usr/bin/sudo -A /home/holden/anaconda3/bin/python3 -B /home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py --attempt-parent /home/holden/mckernel-work/scratch/ndfutexs18-20261001-2 --nonce 4e77144119439085593c17714867debd --owner-sha256 a3efa2ef4f6deb2fc1938bd3723b90baf6b8d30c60faf079ada0e2cd0f69deec --manifest /home/holden/mckernel-work/scratch/native-diagnostic-scratch18-futex-runtime-20261001-2/manifest.json --manifest-sha256 f66d2cf3f7e19c23c843ab974e8e16296e955c65e41cb66f8164b11a9773ef5a
```

Manifest is 6,252 bytes, mode 0600 and passes the current strict loader. It
binds scratch18 image/modules, corrected mcexec, retained bzImage/libc closure,
payload `9593e5f1...2ecc` and collector `3833fd03...2e69`. Base initramfs is
`1497e9e1...9b53d`; derived initramfs is
`a2299f30a7b9616a558b0fb487ab1db30617af6332c18e0d813763c6f5483a82`;
overlay record is `4e5d99ff758cd178e41a841e2c05214d2e1127dd90e5c635b489bdc797666897`.

Run `/bin/mcexec -t 1 0 /apps/app`; require exit 37 and exact stdout
`NATIVE_ULTRA_FUTEX PASS cases=16 threads=2 raw_clone=1\n`. Typed stderr is
`native-ultra-futex-v1`, `current-source-v1`: all 16 ordered CASE records,
THREADS and CLONE with existing exact errno/timing/TID/flag assertions.

Keep the reviewed outer CPUs2-5/4CPU/12GiB/no-swap/512PID/no-network profile
and retained 4-vCPU/8-GiB/two-NUMA guest. Independent release must authenticate
all files and full replay, exact sources/container profile, capacity, sole heavy
lane, development lock and complete process/container absence. Stop on drift,
timeout, oracle or cleanup uncertainty; preserve all output, serial/QMP, clone/
futex trace, retirement and cleanup evidence.
