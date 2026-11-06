# McKernel: M14 → M15 → complete supported system

Updated: 2026-11-06T00:18Z. This is the sole active human-readable campaign log.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

## Current decision

**M14 is active under the explicit November 5 resume.** Dispatcher:
`gpt-6.1-sol`, reasoning `max`; one disjoint light child, one shared HOST compiler
job on CPU6 within the initial 2 GiB phase. The existing timer steers every
15 minutes. The 01:14–02:14Z November 6 target is an aim, not acceptance.
After genuine original-scope M14 acceptance and a published verified matching
proof checkpoint, continue M15 automatically. Final delivery retains Rocky/Linux.

M14 remains **4/6 accepted**; all three integration gates remain open.
Checkpoint **`f0124bca88207e48ea8d811fee357f3733d0179b`** is pushed and fetched/blob
verified. GitHub base `146dcd187` and exact recovered IHK `c032c975` are retained;
pre-existing dirty work is preserved. The original 39 focused checks are reused.

The current coherent batch adds two real Rust refresh entries, `do_setresuid` and
`do_setresgid`, with paired opt-in C exclusions and genuine current ABI/providers.
The real host ioctl/action now propagates snapshot errors; guest scratch/request
are initialized and failed/partial responses publish no credential fields.
Five producer/consumer checks pass, including actual libc EBADF. The ten-entry
F03 unit compiles with the retained SDK into **5,672 bytes**, object
`fc5f0385167262654aabedbceb6d1aa24e3ce143db80dc6eb39fea5f511a8725`.
Its two new entries each contain 173 bytes of code. Default activation, host/guest
cohort linkage and matching native credential behavior remain open.

The `munmap_body_result` writer transaction now requires lock, unlock and mutator
before acquisition. The previous source fails six cases; the correction passes
all twelve, preserving normal order, range validation and error propagation.
The earlier two credential preflight fixes pass all five affected regressions.
These are meaningful source regressions, not C retirement or image acceptance.

The five-entry F06 unit and five genuine native-signal providers compile and
partially link without the former duplicate providers. The **27,200-byte** partial
object is `f76b95e0fe3e58851ec7c9ce90da9dcd044c9235f35c44b59a9e40987be746f9`.
The actual F06 C translation unit also compiles under the explicitly admitted
HOST flags with **zero C text definitions** and zero `.text/.data/.bss` bytes;
object `590dc309d4179428f3e57f0c4a7831bca0a3d97176176c786f25d81c18fdd8c6`.
Proof is under `docs/verification/m14-f06-eligible-units-20261105-1/`.
This HOST mapping is explicit; SDK/default selection and native acceptance are
unproven. The F06 partial link still needs 22 genuine kernel providers.
The composed F03/F06 relocatable unit now links **15 unique original entries**;
its 32,288-byte object is
`1cb113db2d8a107549658321d89cfbd6b7490a7c3e7f96806864e134e045026e`,
under `docs/verification/m14-combined-eligible-unit-20261105-1/`.
The combined unit still needs 35 real providers and is not a full image.

**R3 process custody transition completed:** an independent review accepted the
source-bound pre-publication failure plus verified ended boot epoch. The bounded
owner validator passed, and Root appended
`docs/verification/m14-r3-reboot-process-memory-disposition-20261105.json`.
Only R3's 4 GiB process-memory charge is retired; historical direct wait and
install outcome remain UNKNOWN. The other **18 GiB** (original install 4 GiB,
V2 2 GiB, native 12 GiB), persistent/native/source holds, scratch21 and mutex27:4
remain. No native admission, old-packet replay or launcher-state change occurred.
HOST checks still conservatively budget against the original 22 GiB plus 2 GiB
and the 4 GiB memory floor; resource grants have not been expanded.

New checks use the existing read-only retained February 18 Rust 1.95 SDK.
The old default Rust 1.60 shim is excluded from this queue. Compilation/partial
linking is under a second with roughly 85–130 MiB peak RSS per command; exact
CPU/wall/RSS, commands and retained failures are in the machine receipts. No new
production image, matching native validation, C retirement or accepted-file delta
is claimed. The historical 30-minute velocity baseline is unchanged.

## Status and useful results

| Track | Accepted | Remaining |
| --- | --- | --- |
| M14 compute-kernel Rust/assembly | 4/6 file goals | Generic and x86 syscall files, final integrated image and matching validation |
| M15 project-owned integration runtime | 1/8 file goals | Seven file goals and final delivered-runtime integration; resume after genuine M14 acceptance and published proof |
| Practical functional baseline | 35/35 at its accepted scope | Preserve matching results; qualify changed final artifacts and deliver the complete system |

### Latest combined M14/M15 debugging and HOST results

- M14-F03: C and Rust `sigaltstack_body_result` now snapshot the new request
  before writing the old stack back. The former order silently discarded an
  installation when input and output overlapped. Actual source fixtures pass
  **19 C and 19 Rust cases**, including identical/partially overlapping buffers,
  disable/query, invalid requests and copy errors; the same-buffer behavior also
  agrees with an ordinary Linux `sigaltstack` control.
- M14-F06: C and Rust GETREGSET/SETREGSET now reject lengths that are not whole
  eight-byte register elements before clamping, copying or invoking providers.
  **28 invalid-length cases per language** cover both supported regsets and both
  directions, alongside the existing configured-XSAVE and copy-error cases.
  The revised architecture source is pinned by the successor binding; frozen
  profile, predecessor, body/header and origin rejection checks remain intact.
  An owned-child Linux ptrace control was unavailable and was not retried; these
  results do not claim host ptrace runtime parity or a full kernel build.
- M15-F05: the C/Rust boot loops stop at the first RUNNING, error or other
  terminal status. Previously they continued all 50 polls and could overwrite
  success or the original error. BOOTING/BOOTED/READY retain their existing wait
  behavior. **34 behavior cases** cover transitions, timeout, descriptor zero,
  captured errno and cleanup; actual device boot was not executed.
- IHK successor `c032c975fdbe17be846bd61cc48cb541e7ab5830`, tree
  `fac3185fb76c9170452af25b8268fb3729699441`, is the current gitlink. Incremental
  bundle blob `7a9fdf2577b13778aad334dee990385eb6507b1e` and the committed manifest
  preserve the complete chain. A fresh three-stage replay from the exact public
  base reproduced that HEAD/tree with a clean checkout.
- The actual unchanged IHK userspace CMake recipes build **ihklib, ihkconfig,
  ihkosctl and ihkmond** with the strict whole70 qualifier and all 76 required
  roots. Generated rules select no project C runtime source. The initial scratch
  driver policy failure and one correction to the actual parent minimum 3.11 are
  preserved locally; production recipes, compiler pins and qualifiers are unchanged.
- Actual Rust ihkmond supervision passes four ordinary HOST startup/stop cases:
  idle, waiting kmsg worker, waiting hung-up monitor, and both workers. Real
  epoll/eventfd/signalfd, threads and libudev are used; each case returns `Ok(())`
  and restores the observed descriptor count from five to five. The consumer
  bypasses `daemon()` and issues no mcos event or device request; active native
  monitoring and installed-service behavior remain open.
- C/Rust mcinspect now finish the selected libdwarf compilation-unit stream on
  a successful lookup so the next independent query starts at its first unit.
  Before the fix, repeated real queries alternated success and failure. Both
  implementations pass eight queries across two real DWARF compilation units,
  including a missing type followed by a successful retry, against the exact
  bundled libdwarf and genuine libelf/BFD providers.
- Both Rust diagnostic tools used an obsolete section layout, reading BFD VMA
  at byte 40 rather than byte 48. Real eclair symbol lookup returned 1041 instead
  of 4202512. The corrected opaque prefix and typed witness bind every consumed
  symbol/section field's offset, width, alignment and C type. All four existing
  header/script/archive/compiler pins and build/profile guards remain unchanged.
  Actual full Rust tool objects and complete diagnostic PIE links succeed.
  Genuine BFD consumers now agree on data/function symbol addresses; eclair
  reads both BFD-written dump chunks and exact boundaries and rejects unmapped
  addresses. Tool mains, GDB and device paths are not invoked by these consumers.
- The final integrated run at source `1b82d6b` passes **64 top-level checks, zero
  skips, in 11.312 seconds**: 22 M14 checks and 42 M15 checks across 23 named modules.
  Real-provider diagnostic modules are rerunnable with
  `M15_DIAGNOSTIC_PROFILE`. The public summary and module list are in
  `docs/verification/m14-m15-focused-results-20261101.json`. Detailed machine
  records remain local: automatic publication review requires separate approval
  to export their workspace/toolchain locations and failed-run metadata. The
  published batch contains the source fixes, regressions and bounded summary.
  Independent changed-path review passed; no new file acceptance, C retirement,
  matched production image or native lifecycle qualification is asserted.

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

**Single blocker/owner: Root — current2 publication refused before installer
READY and retains live control custody.** The corrected three-actor contract
passed 19 focused control tests and reached all actual root/keeper/installer
roles. Its waiting loader then rejected the new installer hash: it still pins
`6fa1cca8…`, whereas the reviewed installer is `d87594a0…`. The installer was
observed zombie, the keeper reported EOFError with lease UNLOCKED, and the root
parent retained UNKNOWN after its configured timeout. No publication succeeded.

Consumed current2 nonce:
`b3f11a200351e7b1a252e6e609597ff65c8a92a4fbc88f68e63034b481cfb6f3`.
The original caller/session84730 owns sudo58390; root58393, keeper58394 and
installer58395 have exact recorded births. Their last point observations and
source/request/cap bindings are in
`docs/verification/m14-publication-current2-inflight-failure-20261106.json`.
Root and the active `protocol_review` child are preparing only the minimal
current-operation pidfd stop and original caller join. The expired install cap
is not extended. No PID-number signal, old R3 packet, cleanup or nonce replay.

The first attempt's six-actor failure was reviewed as occurring before keeper
creation; its sudo child was positively joined and captures closed. Root recorded
only that attempt's process-charge closure in
`docs/verification/m14-publication-failure-before-keeper-20261106.json`.
All historical UNKNOWN waits/install outcomes and the other 18 GiB remain held.

The independent provider lane verified that the retained `c205` core's signal
source and ABI exactly match the F06 inputs and supply 33 of the partial unit's
35 missing providers. Its private composition omits duplicate native providers.
The old core's getter ignores host errors, so the two new credential entries
must remain unselected when that core is reused. The proposed selector patch is
unapplied; no new policy hold or acceptance is created. A complete image also
needs genuine unaffected objects and eligible `do_syscall`/`terminate` providers.

The independent VM lane delivered the three-line C `do_fork` constructor-failure
CPU-credit correction and an actual-branch regression. They remain untested
while publication owns the shared queue; the private Rust candidate stays
unwired. Later enqueue/TID/exec/XPMEM paths are unchanged.

M14 acceptance delta remains **0 files, 0 production images, 0 native-qualified
cohorts and 0 C retirements**. The 15-entry relocatable link and F06 HOST zero-C
text proof are retained. Native work has been blocked since at least 22:23Z;
exact queue latency and failure-to-validated-fix timing remain unknown. The
avoidable gap was caller/loader integration left outside the synthetic fixtures.
Scheduling change: test the actual waiting loader's source hash before any next
publication admission; source bodies continue independently of this control lane.

**Next deliverable:** reviewed stop-only source/profile, bounded current-role
termination observations and original caller join; then one bounded installer
pin correction with a real pre-READY loader regression. Only after custody and
fresh admission permit it may publication or compilation proceed. A coherent
image and matching applications/native restoration remain mandatory for M14.

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
| M15-F03 / 03-01…02 | `executer/user/mcinspect_bfd_shim.c` | Rust adapters and corrected full tool pass real BFD symbols/repeated DWARF queries; complete HOST link; matched default/deployed qualification remains |
| M15-F04 / 04-01…02 | `executer/user/eclair_bfd_shim.c` | Rust adapters and corrected full tool pass real BFD symbols/offline dump reads; complete HOST link; matched default/deployed qualification remains |
| M15-F05 / 05-01…03 | `ihk/linux/user/ihklib.c` | Actual CMake target links all 70 function/six data roots; parser and boot-result checks pass; complete ABI/deployed/native qualification remains |
| M15-F06 / 06-01…03 | `ihk/linux/user/ihkconfig.c` | Query error paths fixed; complete Rust CLI links and argument preflight passes; matched default/native behavior remains |
| M15-F07 / 07-01…03 | `ihk/linux/user/ihkosctl.c` | Query/release prerequisite errors fixed; complete Rust CLI links and argument preflight passes; matched default/native behavior remains |
| M15-F08 / 08-01…03 | `ihk/linux/user/ihkmond.c` | Actual Rust CMake target links; help and four idle/waiting-worker stop cases pass; active device/event/kmsg and native qualification remain |

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

- At the preceding HOST checkpoint, IHK successor
  `78f731e5eed1abc4faf69e347d48d473a0727935`, tree
  `84c11f941cba10318be3133839863ff382ea8786`, was the parent gitlink.
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
  paths precede device/workload access. The latest combined results above add
  bounded real dump/DWARF and supervisor checks; native behavior remains open.
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
- Included weekly usage only. This explicit 2026-11-05 resume must obtain a
  fresh account/usage observation before any model turn; stop at 100% or an
  earlier actual hold/unknown usage. No prepaid/API fallback. The previous 96%
  observation and `2026-11-04T06:35:33Z` cutoff remain historical constraints of
  the old operation; this resume does not revive any expired execution packet,
  widen its deadlines, reset its ledger or clear a service/source hold.
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

## Historical checkpoint and break

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
