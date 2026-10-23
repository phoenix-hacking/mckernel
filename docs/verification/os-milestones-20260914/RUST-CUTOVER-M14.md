# M14: complete Rust and assembly McKernel LWK

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

M14 tracks full compute-kernel Rust cutover separately from the existing M00–M13 functional worklist. Practical progress remains **29/35** at this snapshot. M14 is **open** and active in parallel; it does not add to the35-check denominator or block the next functional test.

**Done means:** No live McKernel-owned compute-kernel C implementation remains on the supported default co-booted LWK path; the Rust/reviewed-assembly image works with the existing Linux supporting control plane and the practical application/lifecycle baseline.

Use [rust-cutover-m14.json](rust-cutover-m14.json) as the editable worklist. The [initial file inventory](rust-cutover-m14-inventory-20261023.json) is bound to image `10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2`. It identifies six runtime C translation units, not six entirely unported files. Existing Rust bodies and native results remain credited at their actual scope. Surviving C bytes/functions have not yet been measured; initial unassessed states are not a0% engineering estimate.

## File worklist

| File goal | Current C file | Functional subgoals | Closure |
| --- | --- | --- | --- |
| M14-F01 | `kernel/mem.c` | 5 | open; partial Rust already exists |
| M14-F02 | `kernel/process.c` | 5 | open; partial Rust already exists |
| M14-F03 | `kernel/syscall.c` | 5 | open; partial Rust already exists |
| M14-F04 | `arch/x86_64/kernel/cpu.c` | 5 | open; partial Rust already exists |
| M14-F05 | `arch/x86_64/kernel/memory.c` | 5 | open; partial Rust already exists |
| M14-F06 | `arch/x86_64/kernel/syscall.c` | 5 | open; partial Rust already exists |

## M14-F01: `kernel/mem.c`

Reuse: `kernel/rust/mem_helpers.rs`, `kernel/rust/page_alloc.rs`, `kernel/rust/page_helpers.rs`, `kernel/rust/refcount_helpers.rs`, `kernel/rust/object_helpers.rs`, `kernel/rust/abi.rs`.

- **M14-01-01** — Physical/NUMA allocator bootstrap, page bookkeeping and free-page lifecycle; reuse existing page allocator rather than duplicate it.
- **M14-01-02** — Kernel heap chunk allocation, cache allocation/free and free-list consolidation; close remaining C allocation/logging callback bodies.
- **M14-01-03** — Page and memobj reference ownership, map/unmap accounting and final release; carry explicit last-reference rules into Rust.
- **M14-01-04** — User-page lookup, fault-PTE lookup and VM page maintenance across split/shared/large-page cases.
- **M14-01-05** — Memory/rusage counters, memory-dump iteration and metadata publication; preserve exact functional counters and error ordering.

Existing progress: Rust mem_helpers exports rusage/stat routines, kmalloc cache public entrypoints and ___kmalloc/___kfree body helpers; macros retain C alternatives. Existing reference/page helper selectors prove partial dispatch structure, not deletion of every C body or callback.

Verification focus: Allocator alignment and exhaustion rollback; NUMA fallback; list/lock ordering and concurrent last put. Exact physical/free/rss counters and no double release; exercise mapping fault and shared-page lifetime. Source selection must be checked against actual production flags, symbols and linked object; do not count helper-only equivalence as retirement.

## M14-F02: `kernel/process.c`

Reuse: `kernel/rust/process_helpers.rs`, `kernel/rust/sched_helpers.rs`, `kernel/rust/affinity.rs`, `kernel/rust/waitq.rs`, `kernel/rust/list_helpers.rs`, `kernel/rust/abi.rs`.

- **M14-02-01** — Process/thread/address-space construction, clone ownership and unwind; reuse Rust creation and range orchestration bodies.
- **M14-02-02** — Process VM range insertion/split/join/removal and teardown; remove remaining substantive C bridges after parity.
- **M14-02-03** — Process/thread hash, PID/TID lookup/reuse and reference-counted final retirement.
- **M14-02-04** — Runqueue selection, wakeups, idle transitions, migration/affinity and post-switch release sequencing.
- **M14-02-05** — Signal-common/resource-set inheritance, process publication and cross-thread lifetime coordination.

Existing progress: Canonical idle() now calls sched_idle_runqueue_has_running_result under MCKERNEL_RUST_PROCESS_HELPERS at3914–3937; C loop fallback remains and lock/halt logic remains C. Idle helper is in kernel/rust/sched_helpers.rs:1949 (not process_helpers.rs). C verifies int/i32 status and list-next layout then passes production offsetof values. CURRENT retained source checkpoint6f367112 reports80 original C/Rust parity cases, alternate layout and selected/fallback link plus focused ABI review; production TU ABI/default link/new image/native remained pending in that record. Rust process_helpers exports process add-range orchestration, release/lookup/VM body helpers; accepted FP/post-switch C fixes remain functional requirements.

Verification focus: Idle lost-wakeup window, runq_lock/interrupt ordering and CPU status transitions must remain exact. Clone/exec/wait/exit repeated in one OS; cancellation/cleanup/PID reuse and allocation failure unwinds. No new native credit claimed for source-integrated idle helper; confirm current linked default path before retirement.

## M14-F03: `kernel/syscall.c`

Reuse: `kernel/rust/syscall_policy.rs`, `kernel/rust/process_helpers.rs`, `kernel/rust/futex.rs`, `kernel/rust/native_futex.rs`, `kernel/rust/rlimit_helpers.rs`, `kernel/rust/shmid_helpers.rs`, `kernel/rust/shmobj.rs`, `kernel/rust/timer.rs`, `kernel/rust/abi.rs`.

- **M14-03-01** — Syscall dispatch and Linux offload request/reply lifecycle, preserving context ABI and exactly-once completion.
- **M14-03-02** — Process-control syscalls: fork/exec/wait/exit, ptrace relationships and final reaping/host cleanup.
- **M14-03-03** — VM syscalls: mmap/munmap/mprotect/brk/remap, NUMA policies and process_vm orchestration; close subordinate C callbacks.
- **M14-03-04** — Signal/futex/time scheduling syscalls: signal masks/actions/altstack, robust-list cleanup, waits/wakes and interruption/restart.
- **M14-03-05** — Credentials/resource limits/scheduling policy and SysV SHM/perf/file wrapper paths; preserve validation and forwarding semantics.

Existing progress: Large syscall_policy module already exports validation and complete body-result helpers including wait, VM, signal and policy paths; C includes many substantive bridge callbacks and fallback blocks. do_wait, ptrace, munmap, mprotect and brk have explicit lock/list/usercopy/host callbacks; wrapper Rust ownership alone does not retire those callback implementations. ENABLE_TOFU changes selection for at least one syscall policy conditional; disabled optional features cannot receive production credit.

Verification focus: Clone child visibility, wait status/reaping, exec failure restoration and final host owner release. Usercopy failure/order, lock lifetime and partial VM side-effect unwind; ABI errno and restart behavior. Futex wake count/timeouts/cancellation, signal-frame interaction, same-session repetition and exact resource restoration. Separate supported feature configuration from dormant optional C branches; final milestone must state whether those are ported, retired or excluded.

## M14-F04: `arch/x86_64/kernel/cpu.c`

Reuse: `kernel/rust/x86_cpu_helpers.rs`, `kernel/rust/atomic_helpers.rs`, `kernel/rust/native_xstate.rs`, `kernel/rust/native_signal.rs`, `kernel/rust/x86_local.rs`, `kernel/rust/ap.rs`, `kernel/rust/x86_setup.rs`, `kernel/rust/abi.rs`.

- **M14-04-01** — CPU register/interrupt/atomic primitives with reviewed assembly boundaries and exact memory ordering.
- **M14-04-02** — CPU/AP startup, GDT/IDT/TSS and syscall entry initialization, LAPIC/IPI/timer and clock setup orchestration.
- **M14-04-03** — Context switching, TLS installation, runqueue lock handoff and post-switch process retirement.
- **M14-04-04** — FPU/XSAVE ownership: allocate/save/copy/restore/clear/release, signal handoff and fault recovery.
- **M14-04-05** — CPU-local diagnostics/context access and register/performance state housekeeping.

Existing progress: Rust-selected save/copy/restore/clear FP wrappers call rust_x86_* routines; Rust x86_cpu_helpers also exports primitives, AP boot helpers and debug-register/FP release functions. arch_switch_context remains an actual C body; preserve accepted FP/post-switch fixes and exact selected save/restore conditions. C declarations under MCKERNEL_RUST_X86_CPU_HELPERS often delegate public implementations to Rust; distinguish these from remaining bridge bodies.

Verification focus: XSAVE masks/sizes/alignment and SSE/default-image initialization; FP state across threads/signals and child copies. Reviewed assembly preserves calling conventions, stack/register state and context return value; CPU-local offsets verified against actual headers. Interrupt enable/disable and runqueue lock restoration; AP boot/timer/IPI requires matching native coverage when authorized.

## M14-F05: `arch/x86_64/kernel/memory.c`

Reuse: `kernel/rust/x86_memory_helpers.rs`, `kernel/rust/pte_helpers.rs`, `kernel/rust/native_fault.rs`, `kernel/rust/native_vdso.rs`, `kernel/rust/page_helpers.rs`, `kernel/rust/abi.rs`.

- **M14-05-01** — Early allocation and boot page-table construction, normal/fixed/Linux/vsyscall mapping regions and page-table destruction.
- **M14-05-02** — PTE encode/decode, level/page-size selection, large-page split/merge and mapping attributes.
- **M14-05-03** — Page-table walkers, lookup/map/unmap/replace and fault-PTE translation, including partial failure ownership.
- **M14-05-04** — TLB invalidation/load-page-table and CPU synchronization with reviewed architecture instructions.
- **M14-05-05** — Usercopy and process-VM verify/read/write/patch entrypoints, bounded mapping lifetimes and fault fixups.

Existing progress: Rust x86_memory_helpers exports early_alloc_pages, init_page_table, set_pte, public usercopy/process-VM entrypoints and many body-result functions. C uses separate PUBLIC and USER_COPY_PUBLIC selectors; pte_helpers owns many primitive operations when selected. Remaining C bridge functions cannot be presumed assembly-only.

Verification focus: 4KiB/large/1GiB tables and boundary crossings; ownership of allocated page-table levels on failure. TLB visibility and memory ordering; usercopy partial transfer/fault recovery and source/destination bounds. Kernel/user mapping ABI and actual boot table layout; prove symbols/default flags in the artifact before native mapping regression credit.

## M14-F06: `arch/x86_64/kernel/syscall.c`

Reuse: `kernel/rust/syscall_policy.rs`, `kernel/rust/native_signal.rs`, `kernel/rust/native_xstate.rs`, `kernel/rust/native_fault.rs`, `kernel/rust/native_vdso.rs`, `kernel/rust/x86_cpu_helpers.rs`, `kernel/rust/x86_memory_helpers.rs`, `kernel/rust/x86_vsyscall.rs`, `kernel/rust/abi.rs`.

- **M14-06-01** — Architecture syscall wrappers and arch_prctl/TLS/clone/mmap/shm argument/context translation.
- **M14-06-02** — Signal delivery and rt_sigreturn context/frame/alternate-stack/xstate construction and restoration.
- **M14-06-03** — Ptrace general/FP/xstate/debug registers and syscall-event reporting with correct stop/wakeup ordering.
- **M14-06-04** — vDSO setup, process mappings and time-page/TSC conversion publication.
- **M14-06-05** — Cross-process memory read/write and move-pages orchestration, target lifetime and NUMA callback ownership.

Existing progress: Rust syscall_policy contains architecture callback-driven helpers and native_signal/native_xstate supply signal preparation/validation; C retains copy, allocation, XRSTOR and context callbacks. do_signal, interrupt_from_user, do_kill, signal setting, process_vm and vDSO paths appear among canonical headings; inspect exact selectors per subgoal rather than labeling entire file C-only. x86_cpu_helpers also exports clear/save/restore debug-register routines formerly associated with this TU.

Verification focus: Signal ABI alignment/masks, nested altstack and invalid frames; XRSTOR fault recovery and accepted FP fixes. Ptrace stop/resume/register-set sizes and process/thread reference lifetime. vDSO page permissions/layout and time monotonicity; process_vm partial copy and target exit races.

## Proof recorded for every subgoal

1. **implementation** — Reuse or implement Rust owning the complete supported behavior, including substantive callbacks; retain reviewed assembly and remove live compute-C implementation dependency.
2. **focused checks** — Run the relevant actual-body regression and error/lifetime checks under the existing ordinary profile; reuse matching accepted evidence.
3. **production link** — Compile the real selected translation unit and Rust object, then prove default selection, ABI and ownership in the matched linked image. A C wrapper calling Rust is insufficient while substantive C remains.
4. **native validation** — Demonstrate applicable actual native functional behavior on matching artifacts; record exact supported scope and unresolved branches. Model-only results are insufficient.

Each file also has a residual-C closure record covering its remaining functions and included-header/macro implementations. Classify already Rust-selected code once and reuse matching proof; do not port it again. Retaining a C source file is allowed when it contributes no live owned compute implementation. Substantive C callbacks and forwarding wrappers are not automatically exempt.

## Final integration

| ID | Required result |
| --- | --- |
| M14-I01 | Account for the final supported compute image — Reconcile all emitted executable implementation with the final selected sources and link inputs. Zero live McKernel-owned compute-C implementations; resolve unknown owners and included-header/macro bodies. Check the ABI witness stubs are absent/inert at runtime rather than assuming every C input requires porting. If another active file is discovered, add it with provenance. |
| M14-I02 | Deliver a coherent reproducible Rust/assembly image — Record the real default build/config/toolchain and matching image/modules, with all file cutovers linked and unchanged required capabilities preserved. Reuse matching practical M10 evidence; do not require an all-Rust Linux/control plane or a C-free compiler toolchain. |
| M14-I03 | Validate useful applications and lifecycle on the final cutover image — Reuse matching qualified functional application/process/mapping/thread/signal/lifecycle evidence and run affected regressions after cutovers. The final supported image must retain the practical functional baseline. No new broad hardware, exposure quota or exhaustive unsupported-operation matrix. |

## Explicit exclusions and inventory limits

`kernel/rust/abi_checks.c` is tracked as an ABI witness, separately from the six runtime file goals. It contains layout assertions and five inert file-local XPMEM stubs; verify final runtime absence/inertness instead of assuming it is literally declaration-only. The inventory also enumerates46 Rust-selected-out legacy C files and7 disabled/optional/fallback files. They are not active conversion debt for this profile. Reviewed `context.S`, `interrupt.S` and `trampoline.S` remain allowed.

Linux host modules/control-plane compatibility C, user tools, tests, vendor/generated sources, unsupported architectures and disabled optional configurations are outside this milestone. No new feature or broad qualification requirement is introduced. If a later supported build admits another runtime C file or a missing owned header body, add its actual work rather than silently excluding it.

## Execution and reporting

Keep the current native functional repair moving. Start with the already source-integrated `process.c` idle-scan slice, then assign bounded independent areas to existing workers. Shared ABI edits have one owner; integration/build/guest admission remains with the campaign dispatcher. Do not change a frozen runtime image mid-attempt.

At normal checkpoints report practical check closures separately from M14 Rust implementation, focused tests, production-link proof, native proof and residual C. Reuse final matching application/lifecycle evidence across both milestones. Finishing35/35 permits the already authorized seeded Rust functional workloads while M14 continues; it does not imply full Rust conversion. No new workload, cleanup or filesystem mutation is released by this document.
