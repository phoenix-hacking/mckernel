# Native Linux IRQ-work transport

Retain `kernel/rust/smp_ikc.rs::ihk_mc_interrupt_host`, its native Linux 6.12
layout and initialization guard, and `kernel/rust/llist.rs::llist_add_batch`.
The CMake native ABI selection and all legacy consumers remain unchanged.
The earlier module fixture used a local transport that removed the producer's
node from a mock queue and submitted it with Linux `irq_work_queue`. The next
check must publish directly into Linux's actual per-CPU raised queue and send
its real APIC IRQ-work vector to a different CPU.

The pinned Linux source keeps `raised_list` static and does not export the
existing `per_cpu_ptr_to_phys` routine. Add only explicit GPL symbol exports:
make that existing per-CPU declaration externally visible and export the
existing address-translation function without changing either implementation.
This supplies a revision-bound Linux FFI boundary without kallsyms discovery
or a project C helper. No McKernel policy moves into Linux core. The exact
header witness must bind the queue, physical-address and APIC-call signatures.

Adapt the existing `mckernel_irq_work_verify.rs` fixture behind a separate
remote-queue selection. The original fixture remains available. Use the
exported APIC mask-call trampoline, which is the same Linux implementation
selected by `__apic_send_IPI_mask`, and the exact `IRQ_WORK_VECTOR` value.
The target queue address comes from `raised_list + __per_cpu_offset[cpu]`;
physical addresses come from Linux's own per-CPU translator. Hold Linux's CPU
read exclusion throughout publication, completion and the final cross-CPU
drain, and pin the initiating task to its original CPU. The fixture owns its
poisoned work storage and callback code until all senders stop, `irq_work_sync`
completes, and a synchronous call on each target proves its preceding hard-IRQ
tail is finished. Never return an init error with reachable work or callbacks.

The direct producer sets BUSY without calling Linux's claim helper. Verify
that exact flag sequence separately from the earlier queue-helper fixture;
do not infer the direct path's flags from the helper's CSD-type bookkeeping.
Exercise every other CPU as a real destination, both work slots, repeated
initialization/reuse, and two module lifetimes. Preserve the unresolved earlier
default-idle timer/RCU stall and reject the same signatures in new captures.

This transport prerequisite still mocks the McKernel boot context and allocator;
it cannot prove an executing McKernel CPU or IKC handshake. Subsequent native
boot integration must retain the exact OS/module and guest-memory owners,
prevent target CPU removal during active communication, and stop/drain every
sender before retirement. The existing CPU/resource owners and IHK operation
mutex remain authoritative. Then connect owned boot parameters/trampoline,
native CPU wakeup, readiness, IKC and application execution.

The source-bound prototype now passes both modes on the newly rebuilt kernel.
The direct mode has no `irq_work_queue` import, executes 1,024 callbacks across
three different target CPUs and two module lifetimes, and drains each target.
The original local-queue mode also passes 1,024 callbacks and both unloads.
The only compiler failure was the fixture assertion's temporary shared borrow
of `nr_cpu_ids`; a protected scalar read fixes it with the lint still enabled.
Retain that failure with the successful captures.

Integrate patch 0005 into the current exact-build workflow and live additive
license-input inventory. Refresh only their current verifier/dependency byte
bindings. Preserve the historical source/config patch replay, predecessor
contracts, and false production-credit flags. A fresh current-stage check and
the focused downstream groups must precede the next boot implementation.

That integration now passes its focused groups and fresh declared build,
link closure, artifact checks and native-image guest. The full suite passes
2,315 tests (2,244 passed, 71 skipped) on clean source `772ae63d`.
See `native-irq-transport-final-validation-20260907.json`. These completed
prerequisites still do not establish native McKernel boot or IKC.
