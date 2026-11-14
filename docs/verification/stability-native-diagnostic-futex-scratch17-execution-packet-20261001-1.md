# Native scratch17 direct-futex diagnostic rebuild and guest packet

Status: **NOT_RELEASED**.  This is a fresh source-only packet for the
post-`50b08432` current candidate.  It grants no build, module, image, guest,
application, production, shutdown, catalog, or language acceptance.  No
attempt may start until the compiled scratch17 artifact and a separate exact
privileged execution release are both bound at a fetched commit.

## Immutable source authority

The candidate target is commit `50b084322610a9326b1b7b528edd4cd73b635632`
with tree `d28aaf4fa3df195e7ea36c4fa51b9392bfcb5620`.  The target commit must
be verified from the fetched repository before preparation.  These are the
source bytes to bind; a later working-tree mutation invalidates this packet:

| source | SHA-256 |
|---|---|
| `host-kernel/native-rust/mcctrl_process.rs` | `148134730b5fed7f14770eb070529b5227bb6ab790b7199f8800968219dffc70` |
| `scripts/tests/fixtures/native-application-return-adapter.rs` | `d8b340c6305f1b4ce65f57b3b7e9e573f5b43f1a9e8b2760cb31176e0ce2158b` |
| `scripts/application-tests/native_diagnostic.py` | `2aa9b0257395624ced3ecb4d9e4d3e9373310a9266653b1d1f3cec9d2c8f9356` |
| `scripts/application-tests/native_diagnostic_guest_collector.c` | `82825cf128689ba8f8a74d9528c1acffb724a9356a2c6192c67c8abe4a74965e` |
| `scripts/tests/test_native_diagnostic_guest_collector.py` | `3128e4a4463877c94ed2a6d4ade8be113e507ce28762cd4d5bd42b2ca25b5d2f` |

The producer must retain `let traced = number == 231 || self.trace();`.
`exit_group` 231 is independently observable and does not consume the 64
ordinary delivery sample budget.  Copy and COPIED_SYSCALL failures publish no
delivery and no trace record.  The observer must retain complete delivery,
route, and return groups for ordinary samples and must require one terminal
231 delivery before retirement evidence.

## Fresh artifact and attempt identities

All paths below are intentionally new and must be absent before preparation:

```text
candidate source: /home/holden/mckernel-work/scratch/native-exact-candidate-ddb8-scratch17-futex-1
module set:       /home/holden/mckernel-work/scratch/native-exact-scratch17-futex-modules-20261001-1
image set:        /home/holden/mckernel-work/scratch/native-exact-scratch17-futex-image-20261001-1
guest parent:     /home/holden/mckernel-work/scratch/native-exact-scratch17-futex-guest-20261001-1
manifest:         /home/holden/mckernel-work/scratch/native-exact-scratch17-futex-guest-20261001-1/manifest.json
owner evidence:   /home/holden/mckernel-work/scratch/native-exact-scratch17-futex-guest-20261001-1.owner
```

The module, image, and manifest bindings are currently `UNBOUND`; no invented
hash or copied artifact is admissible.  Preparation must produce fresh hashes
for all three pinned modules, the matching image/overlay, collector, and
manifest.  The candidate must be derived from target `50b08432` and the
module/image sources must be byte-bound to that candidate.  Neither failed
futex packet, nonce, parent, overlay, module, image, guest directory, or
evidence path may be reused.

## Runtime contract

The sole payload command is:

```text
/bin/mcexec -t 1 0 /apps/app
```

Boot arguments are `/bin/native-boot hidos allow_oversubscribe`; payload cwd is
`/case/work`; environment is exactly `PATH=/usr/bin:/bin` and
`COKERNEL_PATH=/apps`.  The strict oracle requires:

```text
stdout = NATIVE_ULTRA_FUTEX PASS cases=16 threads=2 raw_clone=1\n
exit   = 37
```

Stdout and stderr are complete, EOF-terminated, untruncated, and have a
4,096-byte limit.  Typed stderr selects `native-ultra-futex-v1/current-source-v1`:
exactly 16 ordered CASE records followed by THREADS and CLONE.  Every case
identity, errno/result, timing/deadline, TID, clone, count, flag, stack and
framing assertion remains required.  The serial trace must contain complete
delivery/return/route correspondence for sampled ordinary calls, exactly one
terminal delivered syscall with `number=231`, then procfs deletion, retirement
`errno=0`, and process release `cleanup_errno=0`.  No raw wait or successful
stdout may substitute for terminal trace evidence.

## Isolation and one-shot release gates

Only the reviewed container owner may execute the packet, and only after a
separate reviewer publishes an execution release naming this packet's fetched
commit, exact source hashes, fresh artifact hashes, manifest hash, nonce, and
command.  The release must prove the compiled scratch17 artifact exists and
matches all bindings; until then the packet is fail-closed.

The owner must use one serialized heavy lease: CPUs 2-5, 12 GiB memory and
swap limit, 512 pids, no network, read-only inputs, dropped capabilities,
`no-new-privileges`, private writable attempt parent only.  The guest uses q35
TCG, four vCPUs, 8 GiB/two NUMA nodes, one McKernel CPU, 128 MiB service
memory, no NIC/display, `-S`, and a private QMP endpoint.  Host and scratch
capacity, lease/lock availability, process/container absence, fresh-path
absence, and artifact identities must be rechecked immediately before launch.

Any hash, identity, resource, timeout, truncation, oracle, terminal-trace,
cleanup, or postflight mismatch stops the packet without retry.  Preserve raw
stdout/stderr, serial/debugcon/kernel logs, QMP transcript, exact argv,
container inspect/OOM state, owner process identities, lease/lock state,
first/secondary failures, and authenticated absence postflight.

This packet's eventual result is diagnostic-only.  Even a passing one-shot
guest cannot promote formal application acceptance, general futex coverage,
production readiness, shutdown correctness, or OS completion.
