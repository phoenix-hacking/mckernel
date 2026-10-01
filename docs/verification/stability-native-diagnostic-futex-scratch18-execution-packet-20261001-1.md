# Native scratch18 direct-futex diagnostic execution packet

Status: **NOT_RELEASED**. This is a source-only, future, diagnostic packet.
It grants no build, image, guest, application, production, shutdown, catalog,
language, or formal-acceptance authority. It is **UNBOUND** until an
independent privileged reviewer substitutes the actual scratch18 target,
artifact and manifest hashes, a fresh nonce, owner command, capacity/process
census, and a signed one-shot release for this exact packet.

## Immutable source oracle

The source candidate is commit `50b084322610a9326b1b7b528edd4cd73b635632`
with tree `d28aaf4fa3df195e7ea36c4fa51b9392bfcb5620`. Verify both from the
fetched repository before preparation. A changed working tree invalidates this
packet. These are exact source-oracle bindings, not runtime artifact hashes:

| source | SHA-256 |
|---|---|
| `host-kernel/native-rust/mcctrl_process.rs` | `148134730b5fed7f14770eb070529b5227bb6ab790b7199f8800968219dffc70` |
| `scripts/tests/fixtures/native-application-return-adapter.rs` | `d8b340c6305f1b4ce65f57b3b7e9e573f5b43f1a9e8b2760cb31176e0ce2158b` |
| `scripts/application-tests/native_diagnostic.py` | `2aa9b0257395624ced3ecb4d9e4d3e9373310a9266653b1d1f3cec9d2c8f9356` |
| `scripts/application-tests/native_diagnostic_guest_collector.c` | `82825cf128689ba8f8a74d9528c1acffb724a9356a2c6192c67c8abe4a74965e` |
| `scripts/tests/test_native_diagnostic_guest_collector.py` | `3128e4a4463877c94ed2a6d4ade8be113e507ce28762cd4d5bd42b2ca25b5d2f` |

The producer must retain `let traced = number == 231 || self.trace();`.
The terminal `exit_group` 231 is independently observable and is not part of
the ordinary delivery sample budget. Copy and COPIED_SYSCALL failures publish
no delivery or trace. The oracle retains complete delivery, route and return
groups and requires one terminal 231 delivery before retirement.

## Fresh UNBOUND identities

All paths and the nonce below are new scratch18 identities and must be absent
before preflight. They are placeholders until the release binds their exact
hashes; no copied or invented artifact is valid.

```text
nonce:          7e3c1f9a6b4d2e80f5a1c7d9b3e6f042
candidate:      /home/holden/mckernel-work/scratch/native-exact-candidate-scratch18-futex-20261001-1
modules:        /home/holden/mckernel-work/scratch/native-exact-scratch18-futex-modules-20261001-1
image:          /home/holden/mckernel-work/scratch/native-exact-scratch18-futex-image-20261001-1
guest:          /home/holden/mckernel-work/scratch/native-exact-scratch18-futex-guest-20261001-1
manifest:       /home/holden/mckernel-work/scratch/native-exact-scratch18-futex-guest-20261001-1/manifest.json
owner evidence: /home/holden/mckernel-work/scratch/native-exact-scratch18-futex-evidence-20261001-1.owner
evidence:       /home/holden/mckernel-work/scratch/native-exact-scratch18-futex-evidence-20261001-1
release:        /home/holden/mckernel-work/scratch/native-exact-scratch18-futex-release-20261001-1.json
serial log:     /home/holden/mckernel-work/scratch/native-exact-scratch18-futex-evidence-20261001-1/serial.log
qmp transcript: /home/holden/mckernel-work/scratch/native-exact-scratch18-futex-evidence-20261001-1/qmp.jsonl
```

The module, image, collector, manifest, overlay and evidence hashes are
`UNBOUND`. The release must bind every selected module/image/overlay/collector,
their source commit, manifest, nonce, owner command and exact packet hash.
No prior runtime path, nonce, image, module, guest, manifest, owner evidence,
or evidence directory may be reused.

## Exact payload and 16-case oracle

The sole payload command is `/bin/mcexec -t 1 0 /apps/app`; boot arguments are
`/bin/native-boot hidos allow_oversubscribe`, cwd is `/case/work`, and the only
environment is `PATH=/usr/bin:/bin` and `COKERNEL_PATH=/apps`. Required output:

```text
stdout = NATIVE_ULTRA_FUTEX PASS cases=16 threads=2 raw_clone=1\n
exit   = 37
```

Stdout and stderr are complete, EOF-terminated, and each is at most 4096
bytes. Typed stderr is exactly `native-ultra-futex-v1/current-source-v1`:
16 ordered CASE records, then THREADS, then CLONE, with no missing, duplicate,
reordered, or extra records. The exact source-bound case order is:
`wait_mismatch`, `wait_relative_zero`, `wait_relative_10ms`,
`wait_bitset_expired`, `wait_bitset_future`, `wait_null_word`,
`wait_unaligned_word`, `timeout_protected`, `timeout_cross_page`,
`timeout_negative_seconds`, `timeout_negative_nanoseconds`,
`timeout_large_nanoseconds`, `wait_bitset_zero`, `wake_empty`,
`wake_unmapped_private`, `wait_relative_runnable`. Every case identity, result/errno, timing and
deadline, TID, clone, count, flag, stack and framing assertion remains exact.
All 16 source-bound CASE lines are required.

The serial trace must contain delivered ordinary calls with complete
delivery/route/return correspondence, exactly one terminal delivered syscall
with `number=231`, then procfs deletion, retirement `errno=0`, and process release `cleanup_errno=0`. The terminal delivery must have no RET. Every sampled ordinary delivery must have its matching return and any required route record; no terminal delivery may have a RET. Raw
wait, successful stdout, or a partial trace cannot satisfy the oracle.

## Release, isolation, and stop rules

No launch is permitted before an independent privileged reviewer publishes a
one-shot release naming this packet's fetched commit/tree, all five source
hashes, fresh scratch18 artifact/module/image/manifest/evidence hashes, nonce,
owner command, capacity/process census, and release signature. The owner must
recheck host and scratch free capacity (at least 16 GiB and 12 GiB plus
headroom), the serialized heavy lane, lock availability, absence of all fresh
paths, and absence of prior owner/container/QEMU/mcexec/client processes.

The owner uses one serialized lease: CPUs 2-5, 12 GiB memory, 512 pids, no network,
read-only inputs, dropped capabilities, `no-new-privileges`, and only
the private attempt parent writable. The guest uses q35 TCG, four vCPUs,
8 GiB/two NUMA nodes, one McKernel CPU, 128 MiB service memory, no NIC/display,
`-S`, and a private QMP endpoint. Any identity, hash, capacity, timeout,
truncation, oracle, terminal-trace, cleanup, or postflight mismatch stops the
packet without retry. Preserve raw streams, serial/debugcon/kernel logs,
QMP/argv, owner/container status, process/lock census, and authenticated
postflight absence.

This remains diagnostic-only: even a passing one-shot guest cannot promote
formal application acceptance, general futex coverage, production readiness,
shutdown correctness, or OS completion.
