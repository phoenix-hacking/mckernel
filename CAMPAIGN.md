# McKernel: M14 → M15 → complete supported system

Updated: 2026-10-31 UTC. This is the sole active human-readable campaign log.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

## Current decision

**PAUSED at a verified checkpoint.** The user requested a break and a simpler
workflow. Start no new engineering work or automatic resume. Preserve dirty
sources, accepted work, failed evidence and every actual owner/reservation.
Consolidation changes no acceptance, service hold or budget.

Dispatcher: **`gpt-6.1-sol`, reasoning `max`**. Ordinary workers may use medium;
complex workers/reviewers high; bounded extraction low. Confirm project-scoped
`danger-full-access` and approval `never` once per new/recovered thread.

Final delivery means a complete, reproducible McKernel system **using the existing
Rocky/Linux control plane**. Linux-independent boot is outside this goal.

## Status and useful results

| Track | Accepted | Remaining |
| --- | --- | --- |
| M14 compute-kernel Rust/assembly | 4/6 file goals | Generic and x86 syscall files, final integrated image and matching validation |
| M15 project-owned integration runtime | 1/8 file goals | Seven file goals and final delivered-runtime integration; paused until M14 acceptance |
| Practical functional baseline | 35/35 at its accepted scope | Preserve matching results; qualify changed final artifacts and deliver the complete system |

- Existing accepted files stay accepted at their original supported scope. Stale
  internal subrows do not reopen a closed file or create new qualification quotas.
- Image `1cd7e4e66bdbd7d34bcca2e7cb698da814df470ffd726270a612a2d92faf8c38`
  already compiled and linked a 19-function candidate batch. Generic object
  `0633c5248eb68a59c1920799ad1ef1040e27f8733b074fbeea1fc58289eb398c`
  establishes 23 remaining original C definitions. The five architecture names
  below are a historical cursor, not a fresh production-image count.
- A later HOST Rust crate compiled in 18.87 seconds, but includes held XPMEM
  source; compilation is not permission to select or execute that behavior.
- The corrected `syscall_signalfd_create_bridge` compiled separately from genuine
  Rust sources into object `a93caecb` (6,712 bytes, 98-byte function). Its real
  `ihk_mc_get_processor_id` and `do_syscall` providers, request lifetime, final
  link and native behavior remain open. Preserve the inherited ABI warning.
- The 27 focused source regressions passed. Keep them as coverage. They are not
  27 C retirements. Reuse passing tests/artifacts unless changed inputs, a failure
  or a concrete unresolved concern requires another check.
- Since the recent restart: no newly accepted default image, native qualification,
  C retirement or file closure. Do not turn source/typecheck counts into a
  completion percentage. Do not invent ABI/stub providers, relocate live C, or
  count compiler-elided code as an implemented replacement.

## Immediate blocker and next action

The build/install ownership channel failed before a usable lease. The operation
deadline expired. Its caller/control outcome remains UNKNOWN; no further stop,
repair, install or retry is authorized by this consolidation. Preserve both 4-GiB
failed-operation reservations, V2's UNKNOWN 2 GiB, native CPU2–5/12 GiB, scratch21
and permanent mutex27:4. Absence of a process/output is not ownership retirement.

At the checkpoint record exact live identities and final pause here. On a later
explicit resume, the first owner must reconcile those live controls through their
normal reviewed path. Never replay a consumed nonce or treat model shutdown as
native cleanup. Do not start another root-control framework or diagnostic solely
to obtain another source-only report.

Then use one compositor to integrate eligible existing Rust replacements, compile
only affected units with the existing SDK/unaffected objects, link the candidate,
and validate its real consumers. Keep the ordinary admitted HOST compiler queue
independent of unfinished privileged/native setup. A specific held input still
blocks its own command; do not route around or relabel that rejected work.

## M14 checklist — compute kernel

Every remaining cutover needs real Rust/allowed assembly implementation, supported
default selection, ABI/link ownership and applicable functional/native proof.
Prepare compatible replacements together; full native qualification follows the
coherent image. Keep the existing four accepted files closed.

| Goal | File | Status and covered work |
| --- | --- | --- |
| M14-F01 / 01-01…05 | `kernel/mem.c` | Accepted: allocator, heap, references, faults/page maintenance, counters/diagnostics |
| M14-F02 / 02-01…05 | `kernel/process.c` | Accepted: creation/unwind, VM ranges, PID/TID lifetime, scheduling, inheritance/publication |
| M14-F03 | `kernel/syscall.c` | Open; five work areas below |
| M14-F04 / 04-01…05 | `arch/x86_64/kernel/cpu.c` | Accepted: primitives, startup/interrupts, context/TLS, FPU/xstate, diagnostics |
| M14-F05 / 05-01…05 | `arch/x86_64/kernel/memory.c` | Accepted: mappings, PTEs, walkers, TLB, usercopy/process-VM supported scope |
| M14-F06 | `arch/x86_64/kernel/syscall.c` | Open; five work areas below |

| Open work area | Required result |
| --- | --- |
| M14-03-01 | Dispatch/offload request ABI, initialization, lifetime and exactly-once completion |
| M14-03-02 | Fork/exec/wait/exit/ptrace and final host/process cleanup; held exec work remains excluded |
| M14-03-03 | mmap/munmap/mprotect/brk/remap, NUMA/process-VM and substantive callbacks |
| M14-03-04 | Signal masks/actions/altstack, futex/robust cleanup, time/wait/wake and restart |
| M14-03-05 | Credentials/limits/scheduling, SHM/perf/file wrappers, validation and forwarding |
| M14-06-01 | Architecture wrappers, TLS/arch_prctl and clone/mmap/shm ABI translation |
| M14-06-02 | Signal/rt_sigreturn frames, alternate stack, context and xstate restoration |
| M14-06-03 | Ptrace registers/debug state and correct stop/wakeup/event ordering |
| M14-06-04 | vDSO/process mappings and time-page/TSC publication |
| M14-06-05 | Cross-process memory/move-pages, target references and NUMA callback lifetime |

Retained generic function cursor (23, not a list of unimplemented-from-scratch
ports): `ptrace_detach_do_kill_bridge`, `ptrace_detach_kfree_bridge`,
`ptrace_wakeup_sig`, `ptrace_wakeup_log_bridge`, `wait_host_wait4_bridge`,
`syscall_do_syscall3_bridge`, `do_execveat`, `do_mmap`, `do_syscall`,
`terminate_mcexec`, `terminate`, `terminate_host`, `interrupt_syscall`,
`syscall_execveat_bridge`, `do_fork`, `do_setresuid`, `do_setresgid`,
`syscall_forward_rt_sigprocmask_bridge`, `syscall_forward_sigaction_update_bridge`,
`sys_perf_event_open`, `syscall_policy_do_syscall2_bridge`,
`syscall_policy_do_syscall3_bridge`, `util_thread`.

Historical architecture cursor (5, current selection must be re-established):
`arch_rt_sigreturn_xrstor_bridge`, `arch_native_signal_bad_frame_bridge`,
`arch_rt_sigreturn_context_bridge`, `do_signal`, `arch_ptrace_regset_log_bridge`.

- [ ] M14-I01: account for all emitted supported compute code, including headers,
  macros/callbacks and unknown owners; zero live project compute-C implementations.
- [ ] M14-I02: reproducible default source/config/toolchain and matched image/modules.
- [ ] M14-I03: matching useful applications, process/memory/thread/signal behavior
  and native lifecycle/resource restoration on that image. Then accept M14.

## M15 checklist — starts only after M14 acceptance

Reuse existing Rust IHK, SMP, mcctrl, tools and accepted SDK/library artifacts.
For each open row finish remaining bodies, select the real Rust default and ABI,
prove linked/deployed ownership, then qualify the matching consumers/lifecycle.
Use disjoint source owners and batches of at least 30 original C functions where
available; finish a smaller final remainder without padding or delay.

| Goal | Target | Required result |
| --- | --- | --- |
| M15-F01 / 01-01…03 | `host-kernel/native-rust/mcctrl_vm_write_compat.c` | Accepted original three-wrapper Rust MM lock/unlock/VMA-write scope; preserve proof |
| M15-F02 / 02-01…03 | `executer/user/mcexec.c` | Remaining executor C bodies, real default/ABI, linked and functional process behavior |
| M15-F03 / 03-01…02 | `executer/user/mcinspect_bfd_shim.c` | Both BFD upper-bound/canonicalize adapters and real tool/library link |
| M15-F04 / 04-01…02 | `executer/user/eclair_bfd_shim.c` | Both BFD upper-bound/canonicalize adapters and real tool/library link |
| M15-F05 / 05-01…03 | `ihk/linux/user/ihklib.c` | Library bodies/default ABI plus deployed/native qualification; reuse real 70-function/six-data Rust link |
| M15-F06 / 06-01…03 | `ihk/linux/user/ihkconfig.c` | Complete existing partial Rust CLI, real default/library link and native behavior |
| M15-F07 / 07-01…03 | `ihk/linux/user/ihkosctl.c` | Control CLI bodies, real default/library link and native behavior |
| M15-F08 / 08-01…03 | `ihk/linux/user/ihkmond.c` | Monitor/event/thread/kmsg ownership, real default and functional behavior |

- [ ] M15-I01: complete selected/linked/deployed project-runtime ownership manifest.
- [ ] M15-I02: all three delivered Linux-loadable modules use Rust/reviewed assembly;
  keep exact pinned kernel/Kbuild, ABI/import/modpost and generated-metadata checks.
- [ ] M15-I03: Rust executors/libraries/installed tools, public ABI and actual
  static/dynamic project dependency closure with reproducible sources/toolchain.
- [ ] M15-I04: matched modules/image/tools retain application, load/unload, MM and
  resource-restoring lifecycle behavior. Then accept M15.

Rocky/Linux-owned C and legitimate unchanged third-party/generated code remain
allowed. Project C is not exempt because it sits under a vendor/generated/kernel
path. Declare crash-extension/QLMPI/UTI and other optional targets honestly for
the delivered profile; disabling or relocating an owned runtime does not port it.

## Final complete-system checklist

- [ ] S01: declare the supported local x86_64/Rocky-Linux profile, actual features,
  CPU/RAM, toolchain, configs, artifacts and unsupported operations.
- [ ] S02: one reproducible matched image/module/tool build and clean final replay;
  reuse unchanged Linux dependencies and already valid exact-scope artifacts.
- [ ] S03: boot and run useful libc C, Rust standard-library, file/stream utilities,
  memory/mapping, overlapping threads/futexes, signals and fork/exec/wait workloads.
- Run ordinary seeded Rust correctness workloads after the accepted functional
  baseline; do not introduce security testing or syzkaller work.
- [ ] S04: native boot → work → stop → release → boot restores assigned resources;
  no stale mappings, callbacks, descriptors, owners or unexplained failures.
- [ ] S05: final matching regression coverage: two fresh boots, ten complete native
  cycles, at least 100 successful application launches and 60 cumulative mixed-work
  minutes on the same artifact cohort under the user's accepted cumulative-session
  rule. Reuse valid matching rounds; preserve the original uninterrupted contract
  and failures. Add only defect-specific functional/error/cancellation regressions.
- [ ] S06: exact build/run commands, supported/unsupported capabilities, known
  limitations and concise final results; one focused final functional/ownership
  review. Announce completion only after M14, M15 and these checks are accepted.

## Operating rules that remain binding

- Keep the same saved Root/ownership and historical credit ledger; never edit
  launcher-owned state by hand. A new model conversation is not native retirement.
- Included weekly usage only: last confirmed 96% used; stop at 100%, an earlier
  actual hold/unknown usage or inherited cutoff. Original reset upper bound is
  `2026-11-04T06:35:33Z`; it grants no new allowance. No prepaid/API fallback.
- Existing native one-heavy/four-CPU/12-GiB envelope, ordinary compiler grants,
  aggregate reservations and host/scratch floors stay in force. Model parallelism
  creates no workload grant. No overlapping owners, lock unlink, broad chmod/chown,
  scratch deletion/shrink or automatic UNKNOWN release.
- Preserve the held `generic_c` child `01a18a76-b017-76b3-9755-b812d0f923ed`
  and rejected turn `01a18a83-c803-7e63-9aa4-8c54e013c7e5`, execve/ACK/exec-tail,
  held TID/XPMEM behavior/selection, undefined ABI and every retained service/account/source hold.
  Do not retry equivalents through another thread/model or clear stop records.
- Use the existing sudo-A/askpass route only within real admission. Never read or
  log credentials or invoke the askpass helper directly. Full access is not root.
- Use `followup_task` for actual assignments to completed/idle workers; verify a
  new turn once. One compositor owns shared integration; other writers use private
  disjoint paths. Reviews answer a concrete changed-ABI/ownership/release question.
- Use reusable admitted ordinary compile/test profiles. Reuse accepted reviews at
  unchanged scope. One failed candidate plus one bounded correction per failure
  family precedes focused escalation; never loop unchanged failures.
- Push coherent fixes through `python3 -B scripts/push_os_checkpoint.py origin
  codex/local-native-staging-repair`, then verify fetched commit/blobs. Preserve
  dirty work. No dashboard, repeated inventory or new control framework unless
  a demonstrated defect blocks the next real engineering result.

## Single-log and legacy policy

Read and update this file for routine planning, status and handoff. Do not reopen
old narrative logs, old goals, handoffs or investigation diaries. Current source,
build definitions, artifacts and necessary live machine controls remain usable;
they are not additional narrative entrypoints. Never disable a real operational
identity/resource/hold check to avoid reading an old narrative.

Legacy repository: `/home/holden/mckernel-legacy-20261031.git`, branch
`legacy-handoff-20261031`, verified commit
`f191ad00202cce588c4f31a36737cf94b6bb181c`. It retains original history plus
82,631 readable log/evidence records and 348 symlinks from the reset snapshot. Bound operational originals remain at
their exact paths for immutable references; they are archival compatibility data,
not routine reading. Do not delete evidence, owner records or locks for tidiness.

Keep this log concise: update current status and checklist in place; Git preserves
history. Record only a real implementation/build/test/retirement delta, its exact
artifact/checkpoint identifier, one blocker/owner and one next action. Preserve raw
command output as machine evidence when required, without copying it into this log.

## Checkpoint and break

**PAUSED** at 2026-10-31T00:28:57+00:00. The dispatcher completed and fetched-verified
checkpoint `7edcb1459d6ba01299c4e161dd7721e9d4b8328f`; every child-agent turn completed.
The model worker/server/watchers are retired. Periodic engineering reminders are
stopped. No new build, native run, install, repair, cleanup or automatic resume.
Wait for the user's explicit resume after this consolidation and break.

Read-only liveness: `python3 -B scripts/run_os_goal.py --progress`. The old frozen
controllers are retired and must not be rerun against changed launcher hashes. A
later explicit resume needs a fresh controller bound to this file, Sol/max, the
same Root and tighter inherited limits, with actual permissions/heartbeat/leases.
Keep the stored legacy goal identity for ownership checks; its old reading list
is superseded by this file.

Saved Root: `01a18bc3-e072-7810-9426-75101b0856c0`. Historical credit ledger:
`.git/os-autopilot/credit-runs/7f4af94a83b14cc08f97401f5891d965.json` (unchanged).
Inherited boot `7bfc5687-6c04-4d15-84eb-b92ab9a55dcb`, BOOT cutoff
`1571567.6959065471`, MONO cutoff `1556229.568859425`; never widen them.

The expired R3 operation remains UNKNOWN with caller join pending and 4 GiB held.
Nonce `8c12bd228ca26f54732752129977b7310a74234a5d8812faaaa8658be5925bec` is consumed and must not be replayed.
Exact recorded controls and fresh post-model-stop metadata:

| PID | Expected birth | Current observation |
| --- | --- | --- |
| 3121863 | `120224717` | absent; ownership release NOT inferred |
| 3121864 | `120224735` | birth 120224735, state S, parent 1311 |
| 3121867 | `120224742` | birth 120224742, state S, parent 3121864 |
| 3121868 | `120224750` | absent; ownership release NOT inferred |

Current operation/artifact root (abbreviated `WORK` below):
`/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1`.

Reusable items, without reopening narrative history:

| Item under WORK | Exact identity / limit |
| --- | --- |
| `m14-eligible-signalfd-unit-1/work-1/out/signalfd.o` | SHA256 `a93caecbfd04b672a860e4a5de00e5ec8c280b5e35883b7498ae5ce82dc62678`; providers/lifetime/link/native still open |
| `m14-eligible-signalfd-unit-1/INTEGRATION.PRIVATE.patch` | SHA256 `e01cfe2d41d91ec8a0f89a5352e0a80efcf44498182e048d8a5a7209dd4772e0`; source candidate only |
| `root-install-r3-control-stop-1/FROZEN-SOURCE.json` | SHA256 `ee8ae6a493682c2fcc1c02f210eaf723077e2fc76a5744af89aa9ac15839eb86`; prepared and UNINVOKED, requires fresh manual authority/admission |
| `root-install-actual-caller-3` | Expired UNKNOWN R3 operation; do not rerun |

The original `dfd0a93f86905adc253dff7a4c83df722e498ba61d96c8fe524a6b7c3f2dacf0`
install also remains UNKNOWN with 4 GiB held despite known controls being joined.
Total retained planned reservations are 22 GiB. `/usr/bin`'s single-inode mode
repair to0755 was completed and verified; do not repeat it. Scratch21, mutex27:4,
V2's unknown parent birth and native current-free/source-exclusion/effective-view
holds remain unchanged.

**First action after explicit resume:** reconcile the recorded live R3 control
session and obtain a fresh scoped disposition/stop proof before any further build
or install. No old stop packet, release or nonce is revived by resuming a model.
Then return to the eligible source → changed-unit compile → link → native path.

Consolidation verification: 174 offline launcher/recovery/billing checks passed,
including one-log-only reads and pinned Sol/max defaults. Other runtime guards
were unchanged. This is workflow verification, with zero new M14/M15 acceptance.
