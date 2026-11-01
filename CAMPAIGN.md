# McKernel: M14 → M15 → complete supported system

Updated: 2026-11-01 UTC. This is the sole active human-readable campaign log.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

## Current decision

**Focused M15 source checks resumed by explicit user request after the M14
debugging checkpoint `0f0fd1a`.** This supersedes the prior M15 scheduling pause;
it changes no acceptance, actual source/service hold or native authorization.
The retained native pipeline remains blocked at the verified checkpoint below.
The user has now explicitly requested GitHub publication and continued M15 work.
Draft PR [#2](https://github.com/phoenix-hacking/mckernel/pull/2) contains the
published source checkpoints `ed2e30b` and `b66ba1c`. The user's earlier commits preserved the
exact Rust IHK source in tracked Git bundles; that source has now been recovered
and this branch adds the follow-up fixes and reproduction helper to the same PR.
The next source batch `b3ccdb3` fixes IHK query failures, argument ownership and
daemon help. Actual HOST builds now link the Rust IHK library, all three IHK
tools, eclair and mcinspect against the recovered providers. Exact BFD/compiler
pins are available; the explicitly supplemented HOST profile does not establish
the complete original native SDK. This checkout still cannot access R3 controls.
Preserve dirty sources, accepted work, failed evidence and every actual
owner/reservation. The source work changes no acceptance, service hold or budget.

Dispatcher: **`gpt-6.1-sol`, reasoning `max`**. Ordinary workers may use medium;
complex workers/reviewers high; bounded extraction low. Confirm project-scoped
`danger-full-access` and approval `never` once per new/recovered thread.

Final delivery means a complete, reproducible McKernel system **using the existing
Rocky/Linux control plane**. Linux-independent boot is outside this goal.

## Status and useful results

| Track | Accepted | Remaining |
| --- | --- | --- |
| M14 compute-kernel Rust/assembly | 4/6 file goals | Generic and x86 syscall files, final integrated image and matching validation |
| M15 project-owned integration runtime | 1/8 file goals | Seven file goals and final delivered-runtime integration; focused source/debugging checks active by user request |
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

Source checkpoint based on `5a5d7e77ab4ada91777f1ee06c5d7fbdb98f5b71`:

- Fixed the final architecture-syscall CMake assignment that erased earlier F06
  ownership guards; it now appends the base guards. This affects existing default
  selections as well as the new candidate.
- Initialized the traced default-SIGTRAP notification before either consumer in
  C and the existing unselected whole-Rust candidate, preserving notification,
  lock and wake order. The whole candidate now requires the initializer.
- Added five Rust forwarding adapters and two signal/ptrace diagnostic adapters,
  with paired source guards behind `ENABLE_RUST_M14_SYSCALL_ADAPTERS=OFF` by
  default. Whole-signal/context selection and held source remain unchanged.
- Isolated tests passed using pinned `rustc 1.95.0-nightly (c04308580 2026-02-18)`
  and CMake 3.28.3: `test_f03_forward_adapters.py`,
  `test_f06_signal_adapters.py`, and `test_m14_syscall_selection.py`. The last
  reproduces the former overwrite and verifies ON/OFF pairing and profile
  rejection. These are unit/configuration results, not a production kernel
  build, final-link or native acceptance. M14 remains 4/6; zero new retirements.
- The earlier Git push dry-run failed for missing credentials. The now-connected
  GitHub account provides an authenticated source-publication route. The
  prescribed `scripts/push_os_checkpoint.py` is absent from the tracked tree;
  publication through GitHub does not replace the original native controls.

The user explicitly requested a further debugging pass. Reproduced and corrected
these eligible-source defects in the same checkout:

- The preceding architecture edits broke configure-time F06 origin generation.
  A separately pinned successor-source binding now permits the actual revised
  bytes while preserving the frozen command profile, source/body/header checks
  and debug-line identities. All metadata inputs trigger CMake reconfiguration.
  The generated receipt remains source metadata with no build/runtime authority.
- Both C and Rust wait helpers now propagate copyout failures, avoid wait4 output
  copies after errors or WNOHANG/no-result, decode waitid exit/signal/core status,
  and zero waitid's no-result siginfo. Both C declarations and the Rust definition
  agree on the siginfo helper's long return. Invalid waitid IDs are rejected.
  A private selector distinguishes PGID 1 from all children; public wait4 rejects
  INT_MIN before the backend. Normal process/ptraced lists use the same matcher.
- Preserved complete ptrace event/SYSGOOD payloads when decoding stopped status,
  including a truncation error caught in the new tests by independent review.
  Successful ptraced process/thread candidates now retain their cause in a
  private local-status tag; waitid reports CLD_TRAPPED, while wait4 restores the
  public stop encoding before copyout. Both languages assert that supported
  signals cannot collide with the tag. Function signatures, stored exit state
  and reap/unlock order are unchanged; the enumerated status consumers are the
  two syscall result helpers. Independent review found no further blocker in
  these changed paths at source/unit scope.
- C and Rust xstate regset paths use the configured XSAVE extent instead of the
  fixed 1088-byte type, covering both smaller and larger allocated state.
- Both signal-forwarding bridges and the C sigaction fallback initialize their
  whole contexts before the forwarding path reads all argument slots.
- The combined focused run passed **20 top-level unittest checks, no skips**:
  `test_f03_forward_adapters`, `test_f06_signal_adapters`,
  `test_m14_syscall_selection`, `test_m14_build_origin`,
  `test_m14_f03_signal_context`, `test_m14_f03_wait_results`,
  `test_m14_f03_wait_c`, and `test_m14_f06_xstate_extent` under `scripts.tests`.
  The wait fixtures run 15 Rust and 13 C behavior cases; C also checks the changed
  ABI with incompatible-pointer errors and undefined-behavior instrumentation.
  Traced/ordinary process and thread stop cases cover WNOWAIT, error/no-result,
  preserved event payloads, callback order and absence of private wait4 output.
  Xstate fixtures exercise the actual C/Rust functions across configured extents
  and copy errors. These use observation doubles, not production providers.
  The pinned Rust compiler and CMake versions above were used; `git diff --check`
  passed. No full kernel crate, held input, install or native workload was run.
- The earlier exact-IHK source blocker is resolved through tracked Git bundles
  from the user's prior commits. Canonical upstream does not advertise the
  custom `a7ddca26b0dfb087569d652dce5f4262e1311b70` revision, but the committed
  cache-fix and adoption bundles reproduce it exactly. The M15 source recovery
  and the successor fixes are recorded below; no alternate source revision or
  guessed submodule URL was substituted.

These results improve source confidence only. M14 remains 4/6 accepted, with no
new C retirement, accepted image or native qualification.

The next native action remains reconciliation of the recorded R3 owner on that
host, followed by the existing changed-unit build/link/consumer qualification.

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

## M15 checklist — focused source/debugging checks resumed

The user's explicit M15 request authorizes this focused source work before M14
acceptance. Final M15 acceptance still needs the matching image/modules/tools
and evidence below; no M14 acceptance is implied.

Reuse existing Rust IHK, SMP, mcctrl, tools and accepted SDK/library artifacts.
For each open row finish remaining bodies, select the real Rust default and ABI,
prove linked/deployed ownership, then qualify the matching consumers/lifecycle.
Use disjoint source owners and batches of at least 30 original C functions where
available; finish a smaller final remainder without padding or delay.

| Goal | Target | Required result |
| --- | --- | --- |
| M15-F01 / 01-01…03 | `host-kernel/native-rust/mcctrl_vm_write_compat.c` | Accepted original three-wrapper Rust MM lock/unlock/VMA-write scope; preserve proof |
| M15-F02 / 02-01…03 | `executer/user/mcexec.c` | Remaining executor C bodies, real default/ABI, linked and functional process behavior |
| M15-F03 / 03-01…02 | `executer/user/mcinspect_bfd_shim.c` | Both Rust adapters pass real BFD consumption; complete HOST tool links; matched default/deployed qualification remains |
| M15-F04 / 04-01…02 | `executer/user/eclair_bfd_shim.c` | Both Rust adapters pass real BFD consumption; complete HOST tool links; matched default/deployed qualification remains |
| M15-F05 / 05-01…03 | `ihk/linux/user/ihklib.c` | Current Rust library links with all 70 function/six data roots and passes real parser consumption; complete ABI/deployed/native qualification remains |
| M15-F06 / 06-01…03 | `ihk/linux/user/ihkconfig.c` | Query error paths fixed; complete Rust CLI links and argument preflight passes; matched default/native behavior remains |
| M15-F07 / 07-01…03 | `ihk/linux/user/ihkosctl.c` | Query/release prerequisite errors fixed; complete Rust CLI links and argument preflight passes; matched default/native behavior remains |
| M15-F08 / 08-01…03 | `ihk/linux/user/ihkmond.c` | Help startup defect fixed; complete Rust daemon links and help exits correctly; monitor/event/thread/kmsg behavior remains |

Focused M15 checkpoint, based on `0f0fd1ad22bf9a59d23eec48c4482b20a775487a`:

- Corrected C/Rust executor library-directory discovery: EOF no longer reports
  success or stale errno, newline removal preserves unterminated output, output
  capacity includes its terminator, and failures preserve the output buffer.
  Exact first-field RPATH/RUNPATH matching fixes real RUNPATH executables.
  Thirty observed C/Rust cases and four calls against real host ELF/libc/objdump/
  awk providers passed. These extracted functions do not prove the full Rust
  executor's provider closure or execute held source.
- All four existing Rust BFD adapters passed 72 callback/ABI cases against the
  actual Rust module and retained C wrappers with explicitly synthetic BFD
  objects. No adapter body defect was found or new body/retirement claimed.
- User-tool recipes now use the existing independent runtime compiler binding,
  reject an invalid binding instead of silently retaining C, and depend on the
  selected compiler file. The option is declared before child configuration.
  Actual generated rules check seven ordinary tool/BFD object recipes, source
  ownership and target dependencies without compiling a held/full crate.
  Compute RUSTC, the separate mcexec compiler and optional-profile guards remain
  unchanged. Optional runtime bodies were neither changed nor executed.
- The BFD witness now receives directory definitions/options and active build
  configuration flags, restores the caller's probe configuration, and rejects
  unsupported debug-send, directory generator-expression and multi-config
  profiles. Its compiler is a configure input. Original header/library/compiler
  pins and typed ABI assertions remain intact; isolated compile observers test
  the actual probe command, not a substituted production library.
- The combined focused run passed **15 top-level checks, no skips** under
  `scripts.tests`: `test_m15_executor_libdir`, `test_m15_executor_libdir_real`,
  `test_m15_bfd_accessors`, `test_m15_user_tool_selection`,
  `test_m15_bfd_profile`. Pinned Rust and CMake versions are recorded above;
  GCC was 13.3.0. Independent changed-path reviews and `git diff --check` passed.
- The initial upstream lookup did not recover F05–F08's custom IHK source, and
  three guessed Rocky 8 SDK packages did not match the BFD pin. The subsequent
  committed-source recovery below supersedes those source-availability findings.

Publication follow-up, based on local source checkpoint `3bb8bb8`:

- Restored both saved patches and reproduced all three original local commit
  hashes, including `43202ba`, `0f0fd1a` and `3bb8bb8`; the remote base remains
  `5a5d7e77ab4ada91777f1ee06c5d7fbdb98f5b71`.
- Reproduced a further C/Rust libdir defect against real ELF providers: literal
  RPATH and RUNPATH `/fixture/lib dir` both returned the truncated successful
  value `/fixture/lib`. Strip the objdump tag prefix and preserve its complete
  remaining value. The two affected test modules pass without skips: 30 observed
  C/Rust cases and eight real ELF/libc/objdump/awk calls. This does not qualify
  whitespace in executable filenames or complete installation-prefix handling.
- Published these changes as `ed2e30b561cc329404c171acab462097caffe268` on
  `codex/m15-focused-checks-20261030`, targeting
  `codex/local-native-staging-repair` in draft PR #2. All 28 uploaded blob hashes
  matched the local Git objects. A Git fetch verified the published tree
  `41693ac0c101c0b19382ec89245342a0719b80fe` against the reviewed local tree.

IHK recovery and focused follow-up:

- The user's prior McKernel commits contain the exact custom Rust IHK history.
  `IHK-SOURCE-COMMITS-CACHE-FIX-v2.bundle` (blob `35d7d5b0`, added in `c58d68f`)
  bridges public IHK base `3114d9e` to `7629397`; `IHK-SOURCE-ADOPTION.bundle`
  (blob `ee86bed2`, added in `59f4dbc`) reaches the original gitlink `a7ddca2`.
  Both bundles remain in the current parent tree. The upstream development base
  alone has none of these Rust files; the exact recovered tree does.
- Fixed an inherited C/Rust CPU-list formatting bug: a standalone CPU 0 before
  a gap was lost, so `[0, 2]` became `"2"`. The retained C library formatter,
  shared Rust library formatter and Rust ihkconfig formatter now return `"0,2"`.
  Focused checks cover independent expected strings, all 255 nonempty subsets
  of CPUs 0–7, round trips and buffer growth.
- The IHK CLI build rules now require an existing nondirectory absolute Rust
  compiler binding and depend on that compiler file. The whole-library rule
  also tracks its selected Rust and C compiler files. A compiler-replacement
  observer reproduced stale CLI output before the fix and rebuilt both objects
  afterward. Actual CLI adapters also emitted ihkconfig/ihkosctl Rust objects
  under an explicit fixture configuration. Actual library/CLI links followed in
  the later HOST result below; no device operation was run.
- The first five IHK source changes are commit
  `5f43aea5f45359e9e605543fea6362952beac42f`, tree
  `6c52c505fec71e2cccd8f1dff458884403e412d3`. The incremental
  bundle `scripts/source-bundles/ihk-m15-focused-fixes.bundle` preserves those
  commit objects, and its adjacent patch makes the changes directly reviewable.
- `scripts/ihk_source_bundles.json` and `scripts/restore_ihk_source.py` bind the
  complete ordered chain to the committed parent manifest, bundle blob IDs,
  prerequisites, advertised tips and final gitlink. A real three-stage replay
  using local transport for the exact public base produced the exact successor
  HEAD/tree and a clean checkout. Independent review found no remaining concrete
  source-recovery defect after fixing sparse/index-hidden checkout handling and
  reading the default manifest from the frozen commit.
- For a fresh checkout with an absent or empty IHK directory, run
  `python3 -B scripts/restore_ihk_source.py`. The helper imports Git data only and
  refuses dirty, mismatched, sparse, hidden-index or unrelated destinations.
  It does not replay archived scripts or native controllers. An existing exact,
  complete clean checkout is a no-op; `--destination` can select a separate empty
  location. Canonical `.gitmodules` remains unchanged, so ordinary remote-only
  submodule initialization still cannot retrieve these custom commits.
- Recovered the exact pinned BFD header and linker-script bytes from committed
  selected-source artifacts. The selected package is binutils-devel 2.41-63.el10;
  its `libbfd.so` script names `/usr/lib64/libbfd.a`, `/usr/lib64/libsframe.a`,
  `-liberty`, `-lz` and `-ldl`. The committed `SOURCE-LIFETIME-FACTS.json` (blob
  `391a5331`) records the 18,504,828-byte libbfd.a SHA256
  `2324c3f9557b3387126123659badf4cccdbbd272104aec42a21c709c31bf6d4e`.
- Added that recorded libbfd.a pin while preserving the existing header, script
  and compiler pins. Both directly named archives now trigger configuration and
  mcinspect/eclair relinking. A clearly labeled temporary-file observer first
  reproduced the stale-input path, then verified automatic reconfiguration and
  pin rejection after archive replacement. Generated Makefile prerequisites
  include both archives. The actual unchanged witness and genuine selected BFD
  archive subsequently passed under the explicitly supplemented HOST profile below.
- The final combined focused run passed **36 top-level checks, no skips**, in
  6.441 seconds with the pinned Rust/CMake and GCC 13.3.0. Modules:
  `test_m15_executor_libdir`, `test_m15_executor_libdir_real`,
  `test_m15_bfd_accessors`, `test_m15_user_tool_selection`,
  `test_m15_bfd_profile`, `test_m15_ihklib_cpu_format`, `test_m15_ihk_cli`,
  `test_restore_ihk_source`, `test_m15_ihklib_kargs`,
  `test_m15_ihk_cli_query_errors`, and `test_m15_ihkmond_help` under `scripts.tests`.
  This includes the 72 synthetic
  BFD callback cases and eight real ELF/libc/objdump/awk calls described above.
  The unchanged M14 checkpoint retains its earlier 20 passing checks.
- The follow-up uses the existing PR branch, with exact remote/local tree
  verification required at publication. The commits retain `[skip ci]`: the
  unfiltered tracker uses ordinary remote-only submodule initialization and broad
  unrelated discovery, and is not wired to this source recovery helper. Existing
  workflow definitions and required merge checks remain intact. Skipped/pending
  CI is not a passing result or acceptance evidence.

Further M15 fixes and actual HOST userspace links:

- IHK successor `78f731e5eed1abc4faf69e347d48d473a0727935`, tree
  `84c11f941cba10318be3133839863ff382ea8786`, is now the parent gitlink.
  The updated incremental bundle and manifest preserve both focused commits;
  a fresh three-stage replay reproduced this exact clean HEAD/tree.
- C/Rust ihkconfig and ihkosctl stop after failed CPU/memory counts or payload
  queries. `release mem all` preserves prerequisite failures instead of issuing
  a release and masking the error. Twenty-four failing observations became
  **44 passing behavior cases**, retaining success order and cleanup.
- C/Rust `ihk_os_kargs` retain the duplicated allocation base separately from
  the `strsep` cursor, freeing it exactly once on success and error paths while
  preserving the caller's original ioctl pointer and captured error return.
  Eighteen failing subcases
  became **28 passing cases**. Strict source-bound Rust diagnostic qualification
  remains unchanged and passed during the real library build.
- C/Rust ihkmond help now returns before daemon startup and recognizes `-?`.
  The C basename also handles an argv0 without a slash. Sixteen failing help
  cases became **20 passing cases**. Independent changed-path review passed.
- Recovered the exact `libbfd.a` and `/usr/bin/cc` pins from official Rocky
  binutils-devel 2.41-63.el10 and GCC 14.3.1-4.4.el10 packages, with matching
  CPP/binutils/libgcc and real companion archives. All four production pins
  matched inside the disposable namespace. The unchanged CMake layout witness
  and actual Rust BFD accessor object built successfully; no guard was bypassed.
- The genuine BFD/ELF consumer compared all four Rust bridges with the selected
  BFD library: upper bounds, 34 symbols, names, values and flags agreed. Complete
  Rust eclair and mcinspect binaries linked without project C runtime objects.
  Mcinspect used exact bundled libdwarf commit `ab9230b` (tree `dcc2977`) and
  matching HOST libelf development/runtime files. The first dwarf configuration
  failure is preserved; exporting the already declared HOST C/C++ search flags
  to its nested configuration made the unchanged feature probes/build succeed.
- The actual whole70 producer and strict qualifier built the current Rust IHK
  archive. Its shared library link retains all **70 function and six data roots**;
  independent symbol review confirms their kinds, visibility and definitions.
  The real linked C ABI parser consumer passed **258 formatting cases and 257
  nonempty round trips**, including CPU zero, empty formatting and buffer growth.
  Parser declarations are in the real private header; this is not full public
  API signature/behavior qualification. The observer supplies no project provider.
- Complete Rust ihkconfig, ihkosctl and ihkmond linked to that real library.
  CLI no-argument checks returned their expected error/usage status; both daemon
  help forms exited successfully. Actual mcinspect help/missing-kernel/no-action
  preflights and eclair `-h` passed with their existing return contracts. These
  paths precede device/workload access; dump/Dwarf/monitor behavior remains open.
- Machine evidence is in
  `docs/verification/evidence/m15-focused-host-links-20261101/`: source/package/
  provider/artifact identities, exact commands, selected archive members,
  producer results, real consumers and preserved failed-attempt metadata.
  The profile explicitly supplements the exact pins with HOST glibc 2.39,
  headers/startup objects, zlib, udev and libelf; a host C++ compiler served only
  the libelf configuration probe. This is neither original complete-SDK identity
  nor matched native/deployed qualification. No held full kernel/executor source,
  module/service/install action or native owner was touched.

M15 remains **1/8 accepted**. These fixes and focused results create no additional
file acceptance, C retirement, matched production build or native qualification. The
original native/control holds remain as recorded above. Exact IHK source is now
available, and the selected BFD/archive/compiler bytes and actual HOST userspace
links are resolved. Remaining prerequisites are original supported-profile
transitive SDK qualification and native-owner reconciliation, then a matched
image/module/tool cohort, deployed ownership and application/resource-restoring
lifecycle qualification. Reuse these unchanged HOST artifacts/results.

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

## Retained checkpoint and break

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
