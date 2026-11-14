# M05 used-resource identity observation — private source result

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The finite source unit is complete. Production files were not changed. The private Rust postimages compile through the existing actual-body integration fixture; 21 tests pass. The new decoder consumes actual emitted log bytes, accepts one exact policy commit, rejects 21 invalid/retained/incomplete observations, and separately accepts a synthetic canonical free-extent coalescing variant. This is source feedback, not native execution or M05 completion.

## Concrete source trace

The exact selected manifest is `/home/holden/mckernel-work/scratch/m05-n-261021-4/manifest.json` (`b8a0626becf2a0826c743416fc11a2208e0830350414dc4aabb3802d31f4f85d`). It selects collector `f0435be1e7d4f132c0a013297fbd462627a75eddabf001258f769ff34b2149b4`; the genuine compiled source is the `main-callsite-and-fixture-braces-correction-1/native-second-stop-collector.two-generation.c` source bound by `actual-two-generation-check-1/ACTUAL-M05-TWO-GENERATION-BOOT-AND-STATIC-RESULT-1.json`, not its earlier ancestor.

That selected collector invokes `/bin/native-resource-release-probe` at source line 645, takes Linux host kernel snapshots with `klogctl(3,...)`, saves `/case/evidence/kernel.log` and publishes it to the console at lines 1016–1020. Its final log therefore already transports these proposed Rust observations. No changed collector or new ioctl ABI is required.

The current public probe `scripts/application-tests/native_resource_release_probe.c` lines 139–176 explicitly expects errno 16 for assigned CPU/MEM after shutdown and records unavailable/closed_admission. In `host-kernel/native-rust/os_runtime.rs`, the serialized successful shutdown commits closed admission; the ordinary backend path's `admission.enter()` at line 1487 returns EBUSY before the SMP query callbacks. The NotBooted status alone does not reopen this gate. The Rust CPU callback's query returns only logical CPU IDs; the memory query returns only size/NUMA. The old Linux C query bodies are not this Rust admission producer. Existing READ_KMSG bypass reads the guest ring, not arbitrary host resource storage.

## Candidate behavior

`postimages/smp_cpu.rs` adds a bounded observation helper and two calls around the real coupled commit in `reconcile_shutdown_boot`. The existing CPU policy/hotplug locks retain Linux CPU IDs, APIC IDs, NUMA identity, exact OS token and boot epoch. Before rows require Assigned/current owner; after rows report the actual CPU table Online/unowned state. Linux device reference dropping is not asserted.

`postimages/smp_memory.rs` adds a bounded helper and prepared/committed observations around the actual same-claim memory commit. Every emitted row contains an exact physical interval, NUMA and known owner disposition. At most 64 rows per block are emitted; larger inventories carry complete=0. Missing rows, missing commit, truncation, stale generation/epoch and incomplete observations cannot become zero use. This reports resource-map ownership returning to the RESERVED pool. Linux page owners remain separately retained and their eventual release is unproven.

`resource_observation.py` requires one exact ordered CPU-prepared/memory-prepared/memory-committed/CPU-committed sequence and an explicit expected `(slot,generation)` plus epoch. It compares exact CPU identities, pointwise physical coverage/NUMA/owner disposition (allowing canonical coalescing), and preserves every other generation. A full kernel.log containing multiple boot generations must first be split by a source-bound caller; do not infer an expected epoch from a row and call that independent proof. The current strict application/public-release oracles stay unchanged.

## Actual commands and evidence

The owner used the existing reviewed unprivileged CPU7/one-job/AS1GiB/CPU30s/wall35s/FSIZE64MiB/NOFILE256/CORE0 profile, via pinned `owned_capture_helpers.py` SHA 7834a85d. Host/scratch floors and scratch UUID were checked. No root, Docker, guest, SDK build or production ioctl was executed. The helper's required per-child process-group retirement inspection was used; no independent/exclusive machine census was launched.

- Generation: `/home/holden/anaconda3/bin/python3 -B generate_test.py`.
- Compile: `/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc --edition=2021 --test -Wrust_2018_idioms -Dwarnings actual-resource-body.rs -o actual-check-3/body`.
- Actual body: `actual-check-3/body --test-threads=1` — 21 passed, 0 failed; includes 5 new scenario vectors in one observation test (success, IRQ retention, memory-map preflight retention, stale epoch, bounded incomplete observation).
- Consumer: `/home/holden/anaconda3/bin/python3 -B test_decoder.py actual-check-3/logs` — actual log positive, coalescing positive, 21 negatives.

`actual-check-3/RESULT.json` points to the accepted compile/body/decoder joined receipts. All show returncode 0, direct child joined, closed streams and group absence, with no unexpected group members. Actual emitted logs and decoder output are under `actual-check-3/logs/`. The fixture uses the actual changed CPU reconciliation/memory commit/helpers and existing real shutdown claim, runtime gate, service and callback consumers. Its CPU/memory tables, Linux/hardware/lock/thread interfaces remain explicit deterministic adapters, not production kernel execution.

## Retained failure families

1. `actual-check-1/generate`: system Python3.8 cannot import an existing tuple-annotated fixture. Bounded correction selected the already available Python3.9 interpreter; generation passed.
2. `actual-check-2/compile`: the existing fixture lacked current Entry fork fields/exec_payloads storage; the new observation helper also needed an impl wrapper in the generated fixture. Bounded adapter-only correction compiled. Failed source and generator are retained.
3. `actual-check-3`: binary `body` collided with a proposed capture directory before body execution. Continued the accepted binary under fresh `body-run`; no repeat compilation.
4. `actual-check-3/decoder`: the test expected APIC65/66 NUMA0 while the actual existing fixture uses APIC33/34 NUMA1. Bounded correction adopted the fixture's genuine values and corrected its hardware-negative mutation; consumer passed at fresh `decoder-correction`.

No production candidate failure, assertion or oracle was hidden. No family has a pending unchanged retry.

## Next production boundary

Root should independently review the two additive Rust diffs, especially bounded printing under existing locks and generation/epoch caller binding; integrate/rebase only if SOURCE-PINS still match. Current source carries other unproven dirty SDK changes. The existing SDK66/current-module capacity stop remains fixed at 14159970304 bytes and is not bypassed here. A separately released module/native run is still required to prove these paths in the supported profile. That run can reuse the unchanged collector and must capture the full existing kernel.log and check complete records for each exact boot owner/epoch. No complete-cycle quota, physical host-page release, mapping/callback/reference/frame restoration or whole-kernel Rust retirement credit is claimed.
