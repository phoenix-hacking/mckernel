# M14 pending-signal ownership: conditional design and status blocker

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source analysis only. This is a proposed protocol, not a reviewed implementation,
release, or evidence of a runtime race. No usercopy or provider was executed.

## Exact inputs and existing work

Selected candidate root: `/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/f06-debug-constants-align32-host-1/src`.
`kernel/rust/syscall_policy.rs`: SHA256 `11d9d9e14c6c4ee3d593083ce18137414a7780c23507a44fb0834937fa9618e4`;
`kernel/rust/process_helpers.rs`: `be562522271404c8e5f7cf07f7a7fff9caed6e7be125d4098c7cfb35d1134da1`;
`kernel/rust/sched_helpers.rs`: `c4e6153bef33ec018d2efc88c93854a4dc351f78c901ed3cb25f73524d7c0020`.

Existing draft, do not duplicate: `docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-REMAINING23-C-1/staged-pending-successor-1/experimental-on-1/postimage/kernel/rust/syscall_ptrace_setsiginfo_staged.rs`, SHA256 `722600a5f452c1cb4658f82a57ee3b10a398d26e9a0e001780125e20f0042f28`.
Its `pending_slot_protocol.rs`, SHA256 `5083e63d566afc541e290490074985271abf425377c2ddc005c49d447115a883`, has 64 pointer-keyed shared buckets; its own source-check record leaves all-participant and lock-order coverage open. Neither is an accepted combined-profile integration.

Participant matrix: `/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-pending-participant-matrix-1/MATRIX.md`, SHA256 `63cdc10ad1cf68b9b6b596e51f87e9469ed9544174d80af504f9880fa7998c74`.

## First missing invariant: status publication and revalidation

A thread reference from `find_thread` keeps the thread alive according to the existing reference contract; it does not exclusively own the pending nodes, freeze status, or prevent pointer reuse of a replaced node. `ptrace_io_status` at `syscall_policy.rs:16245` is a volatile raw read, not synchronization. The staged setter samples status before usercopy, then checks slot presence, not status or node identity, on publication or update. Conflict loops repeat usercopy, which can re-read changed user memory or fault a second time.

The actual selected candidate does not support the simple claim that `proc.update_lock` serializes every thread status writer. `ptrace_report_signal_body_result` (`syscall_policy.rs:22209`) and `ptrace_report_clone_body_result` (`:22435`) do write PS_TRACED under that lock. However `arch_do_signal_trap_stop_result` (`:30365`) writes thread PS_TRACED before taking it, and `arch_do_signal_stop_result` (`:30462`) writes thread PS_STOPPED outside it for the non-main `ptracecont == 2` branch. `sched_wakeup_thread_body_result` (`sched_helpers.rs:3149`, around :3240-3278) holds the CPU run-queue lock, releases process update lock, then sets thread PS_RUNNING. Taking the proposed pending bucket lock cannot synchronize with these writers unless they also participate. A second volatile read while holding that bucket therefore does not establish a status transition boundary.

Before implementation, identify every selected Rust and C/architecture fallback status writer and its lock/IRQ/preemption/lifetime context; define a common synchronization or generation publication protocol covering each writer and the setter's commit, including wakeup, stop, terminal and destruction transitions. Prove its lock ordering against run-queue, process update, sigcommon and process threads locks, with IRQ/preemption behavior and no reentrant deadlock. A status generation alone is insufficient if any writer fails to publish through the same protocol, or if generation lifetime/wrap/ABA is undefined. Existing evidence does not establish this invariant, so a correct revalidation or bounded retry outcome cannot yet be selected.

## Conditional all-participant design

If the above status authority and lock order are established, the common slot protocol must include all selected Rust and fallback C/architecture participants, not only setter and wakeup. The core operations are: (1) select the pending source and detach it in one protected operation, transferring exclusive ownership to the taker; (2) snapshot a receive payload while protected and perform `copy_to_user` after unlock; (3) replace/clear slots in signal-stop under the same protocol; and (4) detach all remaining nodes during teardown before their exactly-once free. Detached objects may be freed outside the slot lock only when no other borrowed node pointer escapes it. Establish that independently owned nodes cannot alias across slots and that the thread, sigcommon, and detached objects remain live throughout each operation. Existing signal-stop nesting includes sigcommon before slot, and destruction includes process threads lock before slot; reconcile every opposite edge and IRQ path before using that order. The 64-bucket draft has contention and collisions and requires this same global ordering proof.

For the setter, allocate a private node and copy the first payload into private scratch outside locks. A successful first copy can be committed exactly once under the status authority and slot ownership protocol, with explicit revalidation of the target's live stop state and appropriate slot identity/version. Perform the second distinct usercopy outside locks, and commit its result under the same protocol; if that second copy fails, preserve the already committed first update and return the existing failure. Do not repeat either usercopy on conflicts. Specify and verify what an actual status or slot conflict returns and whether the captured payload applies to an existing/replaced node; no existing authority establishes that policy yet. The slot identity must distinguish replacement/ABA, and the commit must not dereference an unowned stale node. This is a design condition, not a proposed silent change to a concurrent outcome.

Initialized-only publication is a deliberate first-failure behavior change: the old path publishes a new uninitialized sendsig before its first usercopy and can leave that slot after failure; the staged path does not publish it and frees the unpublished node after first-copy failure. Never claim parity for this case or manufacture zero data. First-success/second-failure must preserve the first committed update. Acceptance of this repair needs review of both the changed failed-first-copy state and the unresolved concurrent conflict result.

A bucket-only implementation has no new `Thread` ABI field, but also supplies no universal status epoch. Adding per-thread metadata would require coordinated C/Rust layout, initialization, clone, destruction and ABI assertions; current `Thread` has asserted size 5568. No such expansion is authorized by these source observations alone. Only after ownership, status and conflict semantics are fixed should a real candidate pair the Rust bodies and selectors with actual-body regression tests for success, each copy failure, slot replacement, take, destruction and both source-selection profiles. Tests cannot establish missing synchronization by mock results alone.

## Decision and next safe step

No private replacement code or test was added: its synchronization and observable conflict contract would be speculative. Next, trace a bounded complete status-writer and IRQ/lock-order closure for the selected profile and fallback, then independently review an all-writer status/slot protocol and failure semantics before modifying the staged body. Preserve all held attempts; no native, guest, Docker, privileged, controller or cleanup operation was run.
