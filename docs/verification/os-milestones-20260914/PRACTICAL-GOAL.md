# Practical kernel and application goal

Current assignment scope (2026-10-21 UTC): functional McKernel OS/apps and
Rust/assembly migration only; no security testing. Apply the current assignment
scope in [AGENTS.md](../../../AGENTS.md) to every worker brief. Keep functional
correctness and resource/ownership checks. This note does not resume the stopped
campaign or clear its service-policy hold.

## Complete custom runtime language goal — user instruction 2026-10-24 UTC

The user now requires all project-owned production runtime, including Linux
modules, executors, custom libraries and user tools, to use Rust/reviewed assembly.
[M14](RUST-CUTOVER-M14.md) tracks compute-kernel conversion; separate
[M15](RUST-CUTOVER-M15.md) tracks remaining custom integration runtime. The native
IHK/SMP/mcctrl implementations already use Rust; current selected C MM wrappers
and user-space bodies are explicit remaining debt. Existing functional acceptance
and the35-check denominator do not imply either language milestone is complete.
Rocky/Linux, legitimate third-party dependencies, generated metadata and inactive
references remain separately classified. Keep working behavior while qualifying
Rust successors; do not remove current C or broaden native execution implicitly.

## Active Rust cutover priority — user instruction 2026-10-18

Functional delivery and retiring live McKernel compute C into Rust plus reviewed
assembly are both active requirements. The earlier whole-image zero-C deferral
below must not postpone compute-kernel retirement. Original scope IDs, historical
tables and qualification evidence remain preserved; large exposure and external
certification stay deferred. Practical M09 integration estimates are not a
whole-kernel language-conversion score.

Do not add or expand compute-kernel C behavior. Preserve accepted live cpu.c and
process.c fixes and the working image while implementing Rust through real
consumed ABIs. C reference/fallback paths may remain during development; count a
cutover only with production default selection, linked-artifact ownership and
applicable native proof. Linux control-plane compatibility C remains allowed;
the three mcctrl_vm_write_compat.c MM API thunks are host glue. Report any further
concrete exception before integration. First ports are the live FPU copy path
and scheduler FPU admission; process/scheduling retirement continues afterward.

Separate milestone, explicit user instruction on 2026-10-23: track the entire
co-booted LWK Rust/reviewed-assembly cutover in [M14](RUST-CUTOVER-M14.md), with
[file-by-file subgoals](rust-cutover-m14.json). Linux remains its permitted
control-plane dependency. M09/P-M09-02 retain their practical preservation and
changed-boundary validation scope; the35-check functional count is unchanged.
Practical35/35 and M14 completion are separate results. Both objectives remain
active in parallel;35/35 does not imply all-Rust completion, and M14 is not a new
prerequisite for the next functional test. The earlier same-day expansion of
P-M09-02 is superseded, with its wording retained as history in the worklist.


Effective 2026-10-17, scope `practical-kernel-apps-v1-20261017`.

The user explicitly revised the goal: a solid kernel and working application
infrastructure, with excessive formal exposure and certification requirements
removed from the current completion path. This supersedes older instructions
to finish every original M00–M13 contract, all 130 production gates, seven
language gates and the entire 273-case catalog before this goal can finish.
The old contracts, evidence, failures and scores remain preserved as a deferred
qualification backlog. Deferred does not mean passed.

## Deliverable and supported profile

Deliver a repeatably buildable, bootable McKernel kernel/image and its matching
native IHK/SMP/mcctrl modules, with useful C and Rust applications working on one
explicitly declared local x86_64 profile. Keep the existing Rocky/Linux 6.12
control kernel, Rust implementations and reviewed assembly. This deliverable
uses McKernel's Linux control plane; it does not claim a Linux-free bare-metal
system or qualification on untested hardware.

Bind the final source/config/toolchain and artifact set. Declare actual guest
CPU/RAM, enabled features, supported app/linking modes and unsupported operations.
Retain the current reviewed isolation/resource profile unless its change is
separately reviewed: one heavy build or guest, four-CPU/12-GiB/no-swap/512-task
validation envelope, measured aggregate headroom and existing disk floors.
Advertise only CPU counts and features actually exercised; loading the SMP
module alone proves neither SMP execution nor concurrent worker behavior.

## Practical definition of done

1. A pinned build recipe produces a matched runnable image/module set. Complete
   one clean rebuild/replay before final delivery, reusing unchanged Linux
   dependencies where the recipe permits. Source identities and output provenance
   must be correct; no claim that unbuilt source repairs were tested.
2. Boot and run actual applications through the normal runner with complete
   stdout/stderr, exit status, timeout/failure detection and kernel diagnostics.
   Include a useful libc-based C application, a Rust standard-library application,
   basic file/stream utilities, and representative memory, file, thread/futex,
   signal, process creation/exec/wait and mapping/protection behavior.
   Include genuine overlapping-worker contention rather than crediting sequential
   TID reuse as concurrency. Do not replace these with model-only tests.
3. The actual native boot -> workload -> stop -> destroy/release -> boot cycle
   restores assigned CPU/memory ownership. No stale process, mapping, callback,
   descriptor or owner may be reused. A failed stop must retain ownership and
   block unsafe reuse. The current Ready/Running and post-effect EBUSY defects
   remain real blockers; disposing of a VM does not prove native restoration.
4. Run a bounded final regression session on the declared final profile:
   two fresh guest boots, ten complete native lifecycle cycles, at least 100
   successful application launches spread across the selected suite, and one
   60-minute mixed application workload. These checks may overlap and reuse
   matching valid evidence. App vectors are not separate launches. Do not repeat
   unchanged passing work solely for new paperwork. Use an existing reviewed
   batch runner where possible; any new privileged batching needs its normal review.
5. Include targeted invalid-input/error, cancellation and recovery checks for
   exercised boundaries, especially repaired unsafe/lifetime paths. Retain raw
   failures. No unexplained panic, corruption, lost data, stranded owner or
   accumulating live-resource trend may remain in the supported profile.
   Record expected warnings and unsupported features explicitly.
6. Supply exact build/run commands, artifacts, supported/unsupported capabilities,
   known limitations and a concise result summary. Perform one focused final
   review of unresolved functional and ownership risks. Announce practical-goal
   completion only when these conditions have actual evidence.

This is a bounded engineering baseline, not a quantified reliability guarantee.
If a defect shows a check is insufficient, add its targeted regression; do not
expand every issue into a new universal qualification program.

## M00–M13, rebased to this goal

The machine-readable worklist is [practical-milestones.json](practical-milestones.json).
Its scope ID distinguishes these exit checks from the preserved original IDs.

| Area | Practical completion requirement | Deferred qualification |
| --- | --- | --- |
| M00 | Compact supported profile, recoverable source/artifact checkpoint and next runnable step | Complete historical-inventory and model-cost campaigns |
| M01 | Correct ownership and supported request/cancellation/error recovery, with relevant actual-body and guest evidence | Exhaustive synthetic permutations and saturation certification |
| M02 | Reliable Linux/McKernel runner, complete results, timeout/failure detection and verified retirement | Every collector matrix and historical record conversion |
| M03 | Working used map/protect/unmap paths, data/access checks and safe failure ownership | Broad NUMA/XPMEM/alias/topology matrices |
| M04 | Useful C/Rust apps, file/stream utilities and representative memory/file/thread/signal regressions | All 273 catalog cases and every parameter expansion |
| M05 | Repeated actual native stop/destroy/release/reboot with restored resources | Every crash/reset/unload permutation on multiple hardware classes |
| M06 | Process creation/exec/wait, thread/futex and syscall behavior required by the selected apps | Complete ptrace, credential, device and optional-network feature parity |
| M07 | State preservation for vector/FPU features actually used across threads/syscalls/signals | AVX-512 and broad MPI/OpenMP/QLMPI/UTI/HPC qualification |
| M08 | Matched native modules build/load and used ABI/lifetime paths work | Exhaustive export/interface/topology mapping |
| M09 | Preserve Rust consumers and validate changed Rust/C/assembly boundaries; complete compute-C retirement has its own active M14 | Broader host/tool/vendor conversion and all seven language certifications |
| M10 | One pinned clean build/replay yields runnable artifacts and a usable recipe | Full RPM/signing/Secure Boot/update/downgrade certification |
| M11 | Integrated regressions, targeted negatives and useful failure diagnostics | Every sanitizer/failure site and whole-host pressure certification |
| M12 | The bounded repeatability/60-minute mixed run above, with resource trends | 100,000 fuzz VM-hours, 30,000 node-hours, 168-hour per-class soaks, 100,000-cycle and billion-operation quotas |
| M13 | Runnable delivery, known limits and focused final correctness review | Signed production release and separate external certification boards |

Known memory/ownership defects cannot be waived as paperwork. Optional unsupported
features may remain disabled with clear safe errors; required app functionality
must be repaired rather than removed to obtain a pass. Optional security audits,
threat modeling and hardening remain outside this functional completion target.
Host isolation, ownership/resource checks and service safeguards remain operative.

## Scheduling, reporting and compatibility

Keep independent implementation/tests, next-case packet preparation and boundary
review moving in parallel. Reuse the working current942 stack for compatible
diagnostics while the next matched module candidate is built and validated.
Keep the next two eligible cases ready. Routine edits within a reusable cheap
test profile need no new ceremony; changed privileged/unsafe ownership boundaries
still need focused independent review and their reviewed execution release.

Primary reporting now uses this practical worklist: what works, actual failures,
next executable repair and practical exit checks closed. Reconcile existing
evidence once at the next normal checkpoint. An unassessed new check is not 0%
engineering completion. Do not rescale the old subjective estimates or relabel
old formal gates PASS. Original acceptance counters remain explicitly historical/
deferred and must not be the headline progress bar or active stopping condition.

The user-requested percentage comparison baseline is
[practical-engineering-estimate-20261017T152511Z.json](practical-engineering-estimate-20261017T152511Z.json),
as of 2026-10-17 15:25:11 UTC. Preserve its fourteen ranges unchanged. Save future
same-scope comparisons in new records with estimated percentage-point deltas and
concrete code/test/runtime evidence; do not substitute the old comprehensive-scope
table or treat activity, elapsed time or deferred requirements as engineering gains.

The launcher has a legacy exact objective string used for resume validation.
Do not mutate that constant, remote goal identity or live state to adopt these
instructions. The latest explicit user scope controls work; the preserved string
does not reinstate deferred qualification. At practical completion, report the
scoped result and arrange a normal recoverable stop/handoff without claiming the
legacy comprehensive qualification is complete. Any future objective migration
belongs to the launcher owner at a safe checkpoint.

Continue 30-minute velocity supervision, GPT-6.1 medium/high as appropriate,
measured useful parallelism, the 97% included-usage stop and explicit-stop rules.
Do not restart a policy-stopped campaign or bypass platform safeguards.
