# Native Linux 6.12 IRQ-work boundary

Adapt `kernel/rust/smp_ikc.rs::LinuxIrqWork` and
`ihk_mc_interrupt_host` in place. Retain the existing packet, channel and
`llist_add_batch` bodies, boot-parameter prefix, public symbols and the legacy
layout. The selected `kernel/rust/lib.rs` module and `RUST_KERNEL_SRCS` already
include this implementation. Add an explicit CMake host IRQ ABI selector;
the native choice requires the x86_64 Rust kernel and is used by the new native
McKernel image build. Keep existing legacy and C fallback selections intact.

The Linux 6.12 work header places its list node at offset 0, 32-bit atomic flags
at offset 8, callback at offset 16 and wait pointer at offset 24. Preserve the
guest's 64-byte allocation stride while matching that header and initializing
all native bytes before publication. Native initialization needs a publication
guard; invalid CPU, callback or queue inputs must fail before allocation, and
claim-to-enqueue execution must exclude nested interrupts on the same guest CPU.
The IRQ guard also encloses initialization, preventing a nested sender from
waiting on its own interrupted initializer. The existing NOWAIT allocator
already saves/restores IRQ state around its allocation body. This entry point
is excluded from NMI context; boot inputs and processor count remain immutable
after trusted boot setup.
Keep the legacy execution path unchanged. This is an ABI/lifetime adaptation,
not a second IKC protocol implementation.

Verify both layouts and the complete producer with the exact Linux headers and
existing Rust list implementation. A disposable native Linux verification
module will submit the guest-produced work items through Linux's exported
`irq_work_queue` and check real callbacks, flags and repeated reuse. Its test
transport does not establish cross-kernel APIC delivery or ownership of Linux's
private `raised_list`; those need the subsequent native IRQ adapter. Preserve
the test's mocked boot context and transport as explicit scope limitations.

Build and retain a real McKernel image with the native ABI selected. Then
continue the owned trampoline, boot-parameter and native IRQ/IKC adapters.
The existing CPU/memory/page-table owners remain authoritative. No CPU may
start using dummy queue or callback addresses, and no boot/runtime or production
credit follows from an ABI fixture alone.

The first bounded checks pass both complete producer selections: allocation
failure/retry, 1,027 completions per ABI, invalid native inputs, saved IRQ state,
busy-slot reuse and native error propagation. Two concurrent native senders
complete 8,192 callbacks with one published allocation. The exact Linux header
witness confirms the 32-byte native header and every listed offset. The native
verification module builds and passes an isolated four-vCPU/two-NUMA guest:
1,024 actual Linux callbacks across two load/unload cycles with both guest slots
reused and Linux PENDING/BUSY bits cleared. The two intermediate fixture Kbuild
failures remain in kernel.log and retained captures. The native-selected
McKernel image build and real cross-kernel transport are next.
