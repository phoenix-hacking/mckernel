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

## Preserved McKernel rebuild and shared ABI repair — 2026-09-07

Local checkpoint `496e2fc8` preserves the existing Rust implementation and the
verified native lifecycle/resource work. Its full compatibility image, modules,
and tool build passed in the bounded offline container. Compiler diagnostics
then exposed inconsistent external declarations across existing Rust modules.
The x86_64 page-attribute enum uses bit 63 for NX, but mapping and XPMEM paths
still declared parts of that interface as a 32-bit integer.

The [ABI repair](page-attribute-abi-repair.md) adapts those existing interfaces
without replacing their algorithms. The saved pre-fix object fails both new
real-object ABI probes, and the repaired object passes. Existing memory/init
and XPMEM C/Rust equivalence cases pass with the strengthened full-width case.
The corrected full compatibility build, existing linkage/no-SIMD/composition
checks, and 25 report tests also pass. The retained record binds the dirty
source changes separately from their parent commit. Other declaration warnings,
native CPU/memory assignment, McKernel boot, and workloads remain open.

## 2026-09-07 08:09:13 UTC four-hour checkpoint

The exact Linux 6.12 control kernel and three native Rust modules build. The
new CPU adapter passes real reserve/return operations in a four-vCPU TCG guest:
both native and compat control ABIs, failure injection at each CPU position,
reverse rollback, external-online veto, reservation lifetime after files close,
three concurrent control processes, and two clean unload/reload cycles. All four
guest CPUs are restored. This is the first native physical CPU reservation
result; it is separate from the earlier unbooted OS lifecycle captures.

The adapter reuses the unchanged 38-test `smp_resource.rs` policy and shared
ABI. The Linux patch only exports four existing device hotplug services. Large
workspaces reside in module storage; the prototype object's largest direct stack
allocation is 344 bytes, excluding saved registers and callees. See
[native CPU adapter review](native-cpu-adapter-review.md). Current integration
checks are updating the exact staging/FFI/lifetime fixture closure. The first
runtime capture used prototype staging, so final exact-stage replay remains.

The compatibility McKernel rebuild and existing memory/XPMEM equivalence tests
pass after the 64-bit page-attribute ABI repair committed as `b8d5170d`. The
latest linked image has 614,235 Rust executable bytes out of 783,895 total
(78.356795%). This is language ownership, not whole-system readiness. The earlier
broad suite ran 2,298 tests: 2,227 passed and 71 skipped. It predates the ABI and
CPU adapter changes and is not claimed as current-tree full-suite validation.

Remaining native integration: memory reservation and assignment, generation-
checked OS resource leases, image load/APIC start, bidirectional IKC, unchanged
user tools/workloads, and restoration/stress/production acceptance. Remaining
McKernel C bodies must also become Rust or assembly. Native McKernel has not
booted yet; no overall completion percentage or delivery date is established.
The formal native score remains 3.50% under its separate evidence authority.

Validation remains offline and unprivileged in the fixed four-CPU, 12 GiB
container, with experimental kernels only in disposable guests. No host kernel
module, host CPU hotplug or host reboot experiment is performed. The next formal
checkpoint is due at 2026-09-07 12:09:13 UTC (05:09:13 America/Los_Angeles).

## Verified native CPU checkpoint — 2026-09-07 09:03:54 UTC

The authoritative stage and all three native Rust modules pass the exact
Linux build/link checks. Their second guest capture passes the CPU reservation,
rollback, concurrent control, external-online veto, closed-file module pinning,
and unload/reload sequence with four vCPUs across two NUMA nodes. The earlier
prototype capture is retained separately with its original source identities.
The [checkpoint record](native-cpu-checkpoint-20260907.json) binds both runs,
serial logs, source archives, compiler records and the current test snapshot.

The final full repository run passed **2,299 tests in 334.363 seconds: 2,228
passed, 71 skipped, no failures**, in the fixed offline four-CPU native
container. This includes the unchanged 38-case resource policy fixture and the
expanded seven-case BUILDID/CPU dispatch fixture. Earlier first failures and
repairs are recorded in kernel.log; frozen historical authorities remain
unchanged. The separate license inventory group passed 260 tests with 28 skips.

The full-suite source record identifies its dirty inputs above parent
`b8d5170d00c30075ea726a17ea819aae80a4fe18`. Later documentation and the separate
hash.rs CMake dependency repair are outside that snapshot; the build repair
will be verified separately. No formal production gate is promoted. Memory
reservation/assignment, OS resource leases, McKernel boot, IKC and workloads
remain open, alongside the required remaining McKernel C retirement.

At the user's request, the current rough overall planning estimate is **35%**
for the complete Rust/assembly McKernel plus native Rocky/Linux 6.12 OS goal.
This is a subjective engineering estimate with substantial uncertainty, not
an earned evidence score or a remaining-time ratio. The measured Rust share
of the compatibility image remains 78.356795%; the formal native acceptance
score remains separately 3.50%.

## Native memory reservation prototype — 2026-09-07

The [memory checkpoint](native-memory-checkpoint-20260907.json) and
[adapter review](native-memory-adapter-review.md) record the next verified
runtime step after CPU reservation. The existing Rust map, ownership and
transaction code now preflight whole allocation/release batches; all 45 Rust
policy cases and nine Python checks pass. The Linux adapter reuses the canonical
ABI, CPU module pin and existing page-owner approach, adding exact-node Linux
allocation and native/compat memory ioctls.

The separate fault-injection kernel and all three native modules build. The
new objtool compatibility adjustment passes an unchanged-object positive check
and three unknown-callee rejection checks. Two disposable four-CPU/two-node
captures pass; the final one includes both ABIs, two module cycles, 96 injected
allocation failures, partial-release and concurrency checks, complete CPU/module
restoration, and existing unbooted OS lifecycle probes while memory is reserved.
The first serial-interleaved capture remains failed and retained. The checkpoint
preserves 37 artifacts; earlier compiler/checker failures are in `kernel.log`.

Next: integrate this source and the two Linux patches into the authoritative
staging/workflow and verification contracts, then rebuild and rerun that exact
stage. Subsequently connect resource assignment through the existing checked
OS leases, then image loading, AP startup, IKC and workloads. The prototype does
not yet establish those results, a fresh full repository suite, the required
Rust/assembly-only McKernel, or production gate acceptance. The formal tracker
and rough overall planning estimate remain unchanged.

## Rust consumer integration and incremental build repair — 2026-09-07

Local commit `9e7b1f63` saves the verified native CPU adapter and its evidence.
The subsequent [consumer record](rust-consumer-integration.md) accounts for all
130 Rust files against the original 129-file baseline: 121 unchanged, eight
modified, one added, none removed. The 64 core files share the McKernel crate;
14 files are selected by native module graphs. Remaining native mapping and
legacy mcctrl adaptation are explicit, as are optional, separate-tool and
comparison/test consumers. Complete unification is still an acceptance task.

The omitted `hash.rs` CMake dependency is repaired. Inside the four-CPU
compatibility container, the original rule missed its rebuild, the corrected
rule scheduled compilation, and a real incremental image rebuild passed. The
Rust object and image hashes remained identical to the preserved ABI-repair
artifacts. The existing 17 compiler warnings in other declarations remain;
this build-only repair adds no runtime or language percentage credit. See the
[source-bound verification](rust-consumer-verification-20260907.json).

Next major work remains native memory reservation/query/release using the
existing Rust map, allocation owners and OS lease model, followed by resource
assignment and McKernel boot. Preserve the common ABI and existing consumers
while retiring the remaining McKernel C implementation paths.

## Memory staging integration and standalone prototype estimate — 2026-09-07

The [integration checkpoint](native-memory-staging-integration-20260907.json)
retains seven test attempts, their source-input records and the final helper.
The focused policy/dispatch/lifecycle/staging/build/link group passes 182 Python
checks, including 45 Rust resource-policy cases and eight extracted ioctl cases.
The later unsafe/FFI group passes all 17 cases with the clarified shared CPU/memory
module-pin lifetime. Fourteen new memory boundaries join the review queue; all
106 existing site IDs are retained. Its 120 sites across 15 source inputs still
require compiler cross-validation and independent review for formal acceptance.
Intermediate failures were stale fixture expectations or an omitted test source;
their actual first errors remain in kernel.log and retained logs.

The manifest and build audits include smp_memory.rs. Link validation binds the
observed source order and places NUMA, SPARSEMEM_VMEMMAP, MEMORY_HOTPLUG and
DYNAMIC_MEMORY_LAYOUT fixdep records after their owning memory source; malformed,
missing, duplicate, reordered or misplaced entries remain rejected. Lifecycle
checks bind both ABIs and memory teardown before CPU/provider teardown. The native
workflow consumes the export-only memory patch 0004 and objtool patch 0024.

The [fresh declared-stage checkpoint](native-memory-exact-stage-checkpoint-20260907.json)
passes the kernel/module build and exact link closure under the existing offline
four-CPU/12-GiB runner. The build ran from 10:45:43 to 10:48:27 UTC and preserves
the earlier prototype and the same debug configuration. Its guest replay ran from
10:49:09 to 10:50:35 UTC: QEMU exit 0, no missing or error markers, both ABIs and
two module cycles pass. It includes the CPU regressions, 96 injected allocation
failures and existing unbooted OS probes with a reserved memory pool. All four
guest CPUs and all modules are restored. Fifteen retained artifacts bind the
exact build, staged source, compiler records, guest inputs and serial output.
Remaining runtime/workflow and current license authority bindings and a fresh
full repository suite remain pending. Historical source locks and acceptance
scores are unchanged.

For the user's standalone-but-not-fully-verified milestone, the rough planning
estimate is **40–50%**, with substantial uncertainty. The milestone means the
Rocky/Linux 6.12 control system starting the Rust/assembly McKernel on assigned
CPUs and memory and running a basic workload. It still requires resource assignment,
image loading/start, IKC/application integration and the remaining McKernel C
retirement. Native McKernel has not booted. This subjective estimate is separate
from the earlier **35%** complete-goal estimate and **3.50%** formal native evidence
score; none measures elapsed or remaining development time.

## Final native memory integration checkpoint — 2026-09-07 11:20:23 UTC

The [final validation record](native-memory-final-validation-20260907.json)
retains the current binding checks and both full-suite attempts. The final run
passed **2,301 tests in 333.823 seconds: 2,230 passed and 71 skipped**, in the
fixed offline four-CPU/12-GiB native runner. Its private checkout is based on
bf5db3c36e1842235a1b95778895d565866ba644 with the recorded working-tree overlay.
The exact source subset and original RK-007 artifacts were supplied; skipped
checks remain skipped. The earlier first failures remain in kernel.log.

Current workflow, runtime provenance, FP-0006 dependencies, the unsafe/FFI queue
and license inventory now bind the memory implementation. The historical v2
configuration replay keeps its original patch list and evidence identities. Its
current consumer recognizes only the separately pinned later objtool patch,
without applying it to that frozen replay or accepting unknown/modified files.
Targeted runtime/binding checks passed 398 tests; the configuration/review group
passed 163 tests with 10 skips before the successful full run.

The [updated Rust inventory](rust-consumers-memory-20260907.json) accounts for
131 sources: 121 unchanged from the preservation baseline, eight modified, two
added and none removed. All 64 core Rust files remain in their existing crate
with complete CMake dependencies; all 15 native inputs match the stage/module
graph. Legacy, optional and pending Rust consumers remain explicit. This adds
no McKernel language-percentage credit or complete-unification claim.

The already retained exact-stage debug kernel, three modules and two-node guest
pass with CPU/memory rollback, 96 injected allocation failures, concurrency,
both ABIs, two module cycles and clean restoration. The next implementation is
the [checked OS resource bridge](native-os-resource-bridge-plan.md): preserve
lease generations and assignment order, retain Linux page/device owners, and
complete coupled cleanup before reusing an OS slot. Then continue image loading,
AP startup, IKC, workloads and remaining McKernel C retirement. No native McKernel
boot or production acceptance gate is promoted by this checkpoint.

## Native OS resource assignment prototype — 2026-09-07 12:00:22 UTC

The [source-bound checkpoint](native-os-resource-checkpoint-20260907.json) retains
48 artifacts across policy tests, complete IHK adapter mocks, two module builds,
two guest captures, compiler/source records, the compiled modules and architecture
checks. The source parent is local memory commit `3d68165c`; current changes are
recorded as overlays. The prior exact memory stage and its compiled evidence are
preserved. No new Rust source replaces an existing consumer: this extends the
existing policy and Linux adapters in place.

The existing Rust `MemoryMap` gains atomic batch assignment/release. Six new
cases include 65,536 independent per-page model comparisons, plus late errors,
capacity, stale generations, coalescing and compensation. The policy/fixture
group passes 51 Rust cases and ten Python checks. Direct private-field token
construction, safe calls to the sole checked-lease constructor and aliased
workspaces remain rejected by the compiler. The first test compile failure was
a test-local retained transaction borrow; it was recorded before repair and the
failed source/log remain retained.

IHK's additive v2 creation ABI stores a validated scalar callback pair while its
existing provider module owner remains pinned. Per-OS sleepable locks serialize
resource calls; file leases supply exact generations and compat addresses are
zero-extended once. The exclusive destruction guard supplies its captured status,
so initial-state cleanup cannot race loading/boot. The complete Linux-adapter
mock fixture passes 47 cases. Together with the policy group, the later focused
run passes 11 Python checks; this is separate from the earlier full suite.

The CPU adapter preserves assignment rank, rejects whole invalid batches, and
keeps assigned CPUs offline under the existing Linux device owner and online
veto. Memory assignment selects existing free NUMA ranges, retains exact Linux
compound-page owners, and publishes only a complete candidate. Out-of-line Rust
metadata permits logical page-sized splits without splitting or freeing Linux
compound allocations. Release uses canonical queried sizes/nodes. CPU then memory
locks remain held through both cleanup commits; preparation errors retain the OS
and its ownership. The [implementation notes](native-os-resource-bridge-plan.md)
record these reuse decisions and their remaining boundaries.

The combined prototype modules build against the unchanged Linux 6.12 fault-
injection debug configuration. The IHK and SMP module SHA-256 values are
`399dcb3777d334ef61fbb3d79d71c5e37f4a9c3b1d06338ee9ddb1b323d1af45`
and `5b3b56c082048a40a956b69aff098ac4c488675abfc0c47171ad175a2ed85e47`.
mcctrl and the Linux kernel image are unchanged from the exact memory checkpoint.
All three remain ELF64/x86-64 and have no SIMD/x87 instructions in the disassembly
check (4,727 IHK, 16,739 SMP and 221 mcctrl instructions).

The first guest run finishes at 11:57:37 UTC; the expanded second at 12:00:22 UTC.
Both exit 0 with no missing or error markers. Each uses four vCPUs, two NUMA nodes
and 8 GiB under the fixed offline four-CPU/12-GiB runner. Native and compat each
pass twice: ordered CPU transfers, successful release/reassignment, cross-instance
ownership rejection, page-sized NUMA assignment, all-or-nothing late errors,
ALL/empty memory requests, query faults, concurrent create/assign/release/destroy,
closed-file module pinning and minor reuse without inherited resources. Both
captures retain all old CPU/memory regressions, including 96 injected allocation
failures, and restore every CPU and unload every module.

This is a working source-bound assignment prototype, not an exact-stage or
production acceptance claim. Current manifest, lifecycle, unsafe/FFI and downstream
verification bindings remain pending. Next finish those bindings, rebuild/replay
the declared stage and run the full suite, then connect image loading, AP startup,
IKC and basic workloads. Native McKernel has not booted; remaining McKernel C
retirement and production acceptance remain required. No formal score changes.

## Declared OS resource checkpoint — 2026-09-07T12:50:02.823874+00:00

The [final local validation](native-os-resource-final-validation-20260907.json)
retains the integration failures, focused passes and final source snapshot.
The full suite ran 2,305 tests in 354.989 seconds: 2,234 passed and 71 skipped. The
[declared build and guest](native-os-resource-exact-stage-checkpoint-20260907.json)
pass with the existing debug configuration: four CPUs, two NUMA nodes,
both ABIs and two module cycles. CPU/memory assignment, ownership rejection,
atomic rollback, reuse and cleanup pass alongside prior reservation and
allocation-failure regressions. ELF64 and no-SIMD/x87 checks also pass.

The manifest, IHK/SMP lifecycle contracts, exact callback boundaries and
145-site unsafe/FFI inventory now include the versioned OS resource bridge.
All prior durable site IDs remain. The new scalar callback aliases and
separate export/function safety arguments are in the rebuilt source.
Independent review and production acceptance remain pending.

Historical FP-0006 status/negative witnesses retain their original checker,
contract and producer bytes. An 8,527-byte pinned archive retains the four
old registry/dispatcher source and contract files, verified against commit
`3d68165c0d5c6ce173577a2d6ab5efe18c498052`. Their tests use explicit
private source namespaces. The current capture-integration record binds
that test harness and archive, while its historical witness still rejects
the newer live implementation. These schema/fixture tests are not a
successful current-code production capture workflow.

The [updated inventory](rust-consumers-os-resource-20260907.json) accounts
for 131 Rust files: 116 unchanged, 13 modified and two added relative to
the immutable baseline; none removed. All 64 McKernel files and 15 staged
native files have identified consumers. Optional tools and the native
mapping foundation keep their explicit pending dispositions.

Application checks begin after image loading, native AP startup, IKC and
the native mcctrl launch/syscall path work together. The
[implementation plan](native-image-boot-plan.md) identifies the existing
Rust to retain and the missing adapters. Native McKernel has not booted;
no delivery date or new completion percentage is established. The final
McKernel must still be entirely Rust or reviewed assembly.
