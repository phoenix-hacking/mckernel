# Native Rust HPC system work log

The active user goal began at 2026-09-07 04:09:13 UTC: complete a standalone
HPC system with a Rocky/Linux 6.12 control kernel supporting Rust and booted
Rust McKernel co-kernels, reusing the existing implementation and testing the
full system. This is an ongoing goal, not a claim of completion.

The user additionally requires the complete McKernel kernel implementation to
be **Rust or assembly**, while reusing and integrating Rust across all existing
source groups. This is part of the active goal, not optional follow-up work.
The [language completion requirements](mckernel-rust-assembly-completion.md)
define the final artifact, implementation boundaries, and acceptance checks.

Progress checkpoints are due every four hours during active work; the first is
2026-09-07 08:09:13 UTC (01:09:13 America/Los_Angeles). Shorter updates describe
material findings. Prior source-preservation work was progress: it changed the
authoritative local instructions/trackers and verified the existing Rust bytes.

## Completion requirements

- Preserve the Linux control-kernel / HPC co-kernel architecture and assess
  existing Rust symbols before replacement, as recorded in `rust-reuse-plan.md`.
- Build the exact Rocky-derived Linux 6.12 CONFIG_RUST kernel and native Rust
  IHK, SMP, and mcctrl modules with their required ABI and ownership contracts.
- Reach booted McKernel through those native modules, including real CPU/memory
  assignment, image loading, interrupts, and bidirectional IKC communication.
- Execute unchanged user tools and supported HPC/process/syscall workloads,
  including multi-CPU, memory, I/O, signal, thread, and futex behavior.
- Prove resource restoration, failure rollback, shutdown, unload/reload,
  repeated lifecycle, stress, packaging, and the applicable production gates.
- Complete McKernel's implementation in Rust or assembly and verify the final
  executable/source/dependency closure. Retain and integrate the existing Rust;
  replace remaining C implementation bodies and exclude C fallbacks from the
  final production kernel. Assembly is allowed and accounted for separately.
- Keep tests within the four-CPU, 12 GiB container boundary; experimental kernel
  execution belongs in disposable guests. The user's instruction to continue
  through booted co-kernels and test extensively authorizes this goal's isolated
  guest validation sequence. Host kernel/module execution remains excluded.

## 2026-09-07 continuation evidence

Source baseline: `24a151fef5b9fcf303fdbb8cf9762340cd4100fd`.
Original native CI run `34072696813`, artifact `10001359801`, ZIP SHA-256
`adbf5105ed248d304c2f86f29a67f964670e26ca7688437641b75aa215400988`.

The original archive was acquired and checked before source repair. It contains
49 members, 23,877,009 uncompressed bytes, the compiled bzImage and three native
modules. Build records say complete/exit 0. The original workflow subsequently
failed link validation and did not run a native guest.

The link validator omitted `os_runtime.rs` and its CONFIG_COMPAT dependency.
The repaired validator preserves exact input/order checking and successfully
replays the original records without changing their bytes. All 25 focused tests
passed, including a regression using the real stager and an original compiler
record, source-graph checks, and missing/moved/extra dependency rejection.

Broader local checks exposed coarse-timestamp assumptions in evidence handling:
the acceptance snapshot could miss equal-size byte changes, and a private pipe
write could be mistaken for descriptor replacement. Bounded content rechecks
and the existing stable namespace identity address those failures; 40 and 22
targeted tests respectively passed. Runtime directory rechecks are also being
strengthened to detect namespace changes independently of timestamp precision.
Current verifier byte bindings are refreshed only for reviewed changes;
historical evidence bindings and all production gate statuses are retained.

The local clone's group-writable files were normalized to their Git-declared
0644/0755 modes so exact source-permission checks can run. File contents and
executable selections were preserved. Logs for each first failure and repair
are recorded in `kernel.log`; raw local logs and original artifacts are under
`mckernel-work/scratch/artifacts/native-24a151fe`.

Next: complete affected verification, assemble a disposable native guest using
the existing runtime workflow and the pinned Linux `gen_init_cpio` tool, then
exercise the compiled unbooted OS lifecycle. That test is a prerequisite for
resource/boot/IKC integration and will not count as a booted McKernel result.

## 2026-09-07 05:03 UTC validation scope checkpoint

The reviewed native runtime/FP-0006 changes passed 227 focused tests, followed
by a deterministic file-change-watch regression that also checks descriptor
cleanup. Native compiler replay was enabled with the packaged Rust 1.92.0.
The broad suite reached 1652 tests on one run; later discovery stopped at an
existing transient namespace race in `rocky_kernel_closure_offline.py`.
Its source and test remain unchanged from `24a151fe`. The failing scenario
renames and restores a private staged snapshot before hashing; coarse
filesystem timestamps can hide the namespace change. This remains an open
repository defect. Full-suite success and production readiness are not claimed.

The broad validation lane remains stopped at that recorded failure. Separate
native artifact validation continues with the affected suites and preservation
checks. The local guest uses the acquired, digest-verified original native ZIP,
the pinned source RPM, and the existing initramfs recipe; it does not invoke
`stage_verify_and_extract_snapshot` or consume that offline snapshot format.
The unresolved snapshot defect must be repaired and the broad suite completed
before the overall goal can be considered complete.

Full tests requiring repository writes now use the disposable copy
`/work/native-validation-24a151fe`, with group/world writes removed. The original
`/workspace` mount remains read-only. Four CPUs, 12 GiB, no network/devices,
unprivileged container execution, and guest-only experimental kernels remain
in force. Additional mutation checks use held bytes, a pinned symlink inode,
and Linux file-change events; the event watch supplements content checks and
does not claim immutability against arbitrary writable mmap.

Compatibility reference artifacts for the same source revision were also
acquired and digest-checked: build artifact `10001234965` from run `34072696554`
(SHA-256 `7f30e645ed657906f4d7668a19a9f061944b5526354b32bdf66a86810a160707`),
and boot artifact `10001350094`
(`8d7ddf61178c377549c7af52d4b5c15d7b2085d2cbfb76b98d3934236322530b`).
These preserve the existing Rust-heavy McKernel/user-tool reference for reuse;
archive acquisition is not a new compatibility or native runtime result.

At 05:05 UTC, all 458 tests covering the changed verifier/test families passed
in 49.788 seconds (`native-lane-final.log`). The source checkpoint also passed:
Git whitespace, Python/shell syntax, the exact original compiler fixture,
all 129 Rust files, the recorded build/equivalence inputs, and submodule pins.
The tracker still reports 350/10000 (3.50%), with 130 gate records unchanged.
Guest assembly began after these checks; no new guest result is claimed here.

## First native guest lifecycle result — 05:09 UTC

The local four-vCPU, 8192 MiB QEMU TCG guest booted
`6.12.0-211.44.1.el10_2.mckernel1.x86_64`, loaded the original three native Rust
modules, completed the existing initramfs protocol, and powered down. QEMU
returned 0 (05:09:35–05:09:44 UTC). The existing strict serial validator accepted
the capture. The run exercised x86_64/i386 control calls, 12 unbooted OS creates
and destroys, busy-destroy rejection, module pins with device files closed,
node removal/minor reuse, overlapping opens, and module unload/reload cleanup.

The machine retained host CPUs 0–7 online, and `/proc/modules` contained no IHK
or mcctrl modules after the run. The local initramfs adds the packaged coreutils
interpreter needed by this image's stat/uname wrappers and uses Linux's own
`gen_init_cpio` to emit device records without privileged host/container mknod.

The [local execution and serial review](native-unbooted-24a151fe-local.json)
binds the original artifact, input hashes, container image, QEMU arguments,
initramfs, and [retained serial output](evidence/native-unbooted-24a151fe-20260907.serial.txt.gz).
It is local technical evidence, not an exact GitHub runtime envelope or a
production gate promotion. McKernel image boot, CPU/memory assignment, live IKC,
HPC workloads through native mcctrl, and the remaining broad-suite defect are
still open. All pre-existing Rust implementation files remain unchanged.

## Local kernel build and CPU executor — 2026-09-07, 05:36–06:00 UTC

The local build completed Linux 6.12 bzImage and all three native Rust modules
using the pinned Rocky sources, resolved configuration, and existing patch and
staging recipe. A second four-vCPU TCG guest booted these locally built outputs,
passed the strict unbooted lifecycle serial review, and powered off cleanly.
The [local build/run record](native-local-build-24a151fe.json) includes the input
and initramfs hashes and points to the retained compressed serial output. These
outputs precede the following CPU executor change; they do not demonstrate it.

The existing Rust CPU transaction now has a tested host-effect sequencer. It
uses the same ownership table, journal, rollback, and quarantine mechanisms.
All 29 original Rust tests remain, and nine additional tests passed, including
both hotplug directions, failures before/after effects, inverse failures,
identity changes, and interruption. The [additive reuse check](native-cpu-additive-reuse.json)
confirms 127 original Rust files are byte-identical; the two extended files
retain every original byte and body. No new unsafe/FFI site was introduced.

Current staging, SMP lifecycle, and FFI ledger bindings were updated for the
reviewed source/fixture additions, including computed source-closure digests.
Initial stale-binding/count failures are recorded in kernel.log. The Linux
locking, device lifetime, module pin, and ioctl adapter are still separate work;
the executor alone does not make physical CPU reservation reachable.

The open held-snapshot race was repaired using namespace/write events alongside
the existing held descriptors and digest replay. A subsequent private output
publication race received the same event protection across rename. All 52
closure/offline tests then passed. The complete repository suite still needs a
fresh run before its status can be changed. No final-push gate is promoted.

The incremental native module build and link-closure check passed with the new
executor source and current stage lock (`native-cpu-effects-build-evidence`).
The initial full-suite replay reached 1,911 tests before an old RK-007 positive
test attempted to apply its exact historical review to the newly changed
staging manifest. The verifier correctly rejected that unreviewed input. The
test now uses a sparse private checkout of the exact accepted 24a151fe revision;
it still loads the current checker and retains all mutation rejection checks.
The historical manifest and production verifier were not changed.

Original RK-007 artifact `9312566500`, run `32102757520`, was acquired and tested
against its frozen SHA-256
`72de35e144c18413980eb9f404aa6971c29826c86621fee18cc132ae6f23f346`.
All 110 tests passed in 13.443 seconds, enabling 69 previously skipped artifact
checks. The snapshot family now passes 54 tests, including watch cleanup on
copy/extraction errors and nested writes across the legitimate output rename.
The full suite is being replayed with these fixes and the exact artifact.

The existing compatibility image and its link map were extracted from build
artifact `10001234965` without execution. Their hashes match the source-24a151fe
[linked Rust report](compat-24a151fe-linked-rust.json): image
`68d7f6e7dbac77451e0fb97bcce1c0514b754e0a7d40f77ba6340f101baa230e`,
614,183 Rust-owned executable bytes / 783,847 total = 78.354960%. This is linked
code ownership, not native OS completion. The boot job's separately built image
has a different hash; its report is retained separately and is not attributed
to this build image. The reusable image/map and both original ZIP archives are
retained under `/work/artifacts/compat-24a151fe` in the bounded scratch volume.

## Verification closure — 2026-09-07, 06:40 UTC onward

The user's final McKernel language requirement is now explicitly Rust or
assembly, including linked runtime and support bodies. The separate
[language completion checklist](mckernel-rust-assembly-completion.md) requires
known executable provenance, verified C replacements, preserved Rust consumers,
and native boot/workload evidence. It adds no native host-module tracker points.

The second historical RK-007 fixture now materializes the same exact accepted
24a151fe repository inputs, using the current production checker. Original v2
artifact `9345473288` was acquired and verified against its frozen digest
`d0d63f49311f308b6e1f59e505cf0afc9bde95876ad8955b3ca49bd084a1c84e`.
Both original archives are retained with their required 0644 mode.

RS-006's existing post-close mutation regression exposed another timestamp-only
decision. Its snapshot now holds a Linux file-change watch through all input
and ancestor closes, alongside the original byte and descriptor replay. The
two existing close-race tests force equal timestamps, and a new clean-close
test checks descriptor cleanup. All 27 focused tests pass. The active RS-006
consumer inventory was refreshed only for five already-reviewed changed
current inputs; predecessor patches, historical reviews, and false-credit
claims remain unchanged.

The remaining suite segment passes all 291 tests in 25.429 seconds with both
historical artifacts, the exact Linux source replay subset, and Rust 1.92.
The final full run uses a fresh private checkout after two failed attempts to
overwrite immutable Git pack files and existing symlinks during preparation;
these preparation errors ran no tests and are recorded in kernel.log.

The final full repository suite passed: **2,298 tests, 71 skipped, no failures,
360.409 seconds**. Command: `python3 -m unittest discover -s scripts/tests -p
'test_*.py' -f`, under the four-CPU/12-GiB offline native runner, with both
original RK-007 artifact paths, `MCKERNEL_ROCKY_SOURCE_6_12` pointing to the
verified exact-source replay subset, and `MCKERNEL_RUSTC_1_92=/usr/bin/rustc`.
Source whitespace and generated final-push tracker checks also passed. This
does not convert the 71 skipped cases into passes or establish native CPU
reservation, McKernel boot, or HPC workload acceptance. The next build reuses
the existing compatibility Rust image/tool recipe, retaining image, map,
objects and compile commands for the Rust/assembly completion inventory.
