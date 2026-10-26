Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Actual implementation: run_build_only.py owns one fresh build-only Docker operation;
build_only_worker.py executes exactly the supplied Rust1.95, selectedprocessGCC14,
and rawld11 argv in order. PROFILE.SOURCE-ONLY.json preserves literal commands,
source6153/threepostimages/nineprefixobjects/configuration/toolchain/SDK aliases.
No old owner is invoked around its global gate. Input descriptors have null authority.

24 cheap pure tests PASS on CPU2/onejob/2GiB, including missing/stale resource holds,
RAM/PID/secondheavy refusal, readonlydescriptor launch refusal, exact profile/argv,
and failed Rust/process/link plus stale-replacement shortcircuit. No real compiler,
container, root action, global mutex operation or native workload ran.

Container limits stay CPU2-5/12GiB/no swap/pids512; readonlyroot, UID1000, all caps
dropped, no new privileges, no network/custom devices/hostPID/privileged mode. Only
new /work outputs are writable, plus the bounded /tmp tmpfs. All source, toolchain,
postimage, generated-header/SDK alias, configuration and retainedobject mounts are RO.
No automatic --rm/kill/cleanup; capture CID and require stopped/Pid0 terminal state.
Failure preserves the local claim/capture/container and never changes native custody.

Before the next command, root supplies the exact independent execution review,
live CPU/heavy reservation process/start/full-EOF flock and fresh aggregateRAM/PID/
HOST/scratch guards, exact UID1000-readable input exports and new one-use rootgrant.
The runner uses /usr/bin/docker as UID1000, with no sudo/rootless fallback. Actual
daemon permission is unqualified and may need a separately reviewed existing control
path; this implementation does not grant one. Actual source/toolchain read exports
must pass before running. Existing owner735/attempt5/native releases are unchanged.

Next concrete command (only with those real authorities):

    /home/holden/anaconda3/bin/python3 -I -B run_build_only.py --execute ACTUAL_NEW_BUILD_ONLY_ROOT_GRANT.json

ACTUAL-ADMISSION-SLOTS.SCHEMA-ONLY.json lists the required actual fields and pins.
It cannot authorize execution. The same code supports an explicitly reviewed
postcleanup one-heavy admission if coexistence cannot qualify promptly.

The three real commands emit exact argv, return status, times/RSS, new object/image
hashes and a producer contract marked build-only. Existing current-default ownership,
panic/logger/RELA/storage and rawld/link.d/ELF/native-symbol validators remain required
before any default acceptance; matching native proof and Source38 GNU_RETAIN stay
open. No compiler/native/file/C-retirement closure is claimed by this source result.
