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

The image validation additionally compares the exact pinned IHK C producer
body with the legacy Rust producer using one fixture and checks identical
observable results. The broad historical harness needs three Rust crates
absent from pinned IHK 3114d9e; its failed replay remains recorded and is not
counted as a pass. The current C fallback exposed a missing `LIST_HEAD` static
initializer in `lib/include/list.h`. Restore that data declaration macro so
the retained IHK manycore wait-list declaration compiles; keep existing Rust
list execution bodies and consumers unchanged. No executable C body is added.

The subsequent fallback compiler also requires the old list-entry and safe
traversal macros in IHK's retained `ikc/master.c` and `queue.c`. Reuse the four
dependent macros from `10c68621^:lib/include/list.h` under
`!MCKERNEL_RUST_LIST_HELPERS`; the normal and native Rust image configurations
exclude them. This is explicitly optional fallback C execution support, not a
Rust retirement or language-completion claim. All existing Rust list bodies
remain selected in the Rust image.

The legacy IHK x86 setup also uses `CVAL`/`CVAL2` in static perf tables.
Select constant encodings only for that C fallback translation unit through
`MCKERNEL_IHK_STATIC_PERF_TABLES`. Preserve the normal header declarations,
Rust runtime symbols and existing C runtime fallback functions. The encoding
matches the retained Rust body and the original pre-conversion constants;
the native and legacy Rust setup tables remain unchanged.

The final fallback link requires the old IHK queue's generic `cmpxchg` name.
For that C translation unit alone, adapt it to the existing x86
`atomic_cmpxchg8` primitive, with a compile-time assertion that the offset is
64 bits and one evaluation of each argument. Preserve both the Rust and C
atomic implementations. This wrapper is absent from Rust image consumers.

Image attempt 9 passes all three complete builds, ELF64 x86 checks and linked
Rust attribution. The native-selected image is 7,947,616 bytes with SHA-256
`fb7f5140c8a877b2f927c222332bf589ad70120849285e50b46c352bfcd79ad1`.
Its Rust object contributes 614,450 of 784,119 executable bytes; the remaining
contributions still require the full Rust/assembly completion work. The exact
compiler is nightly 1.95.0 (`c04308580`, 2026-02-18). The native Rust flag is
present only in the native build command. Both unsupported ABI configuration
checks reject their inputs. All intermediate build failures and source overlays
are retained in `native-irq-images-checkpoint-20260907.json`. Next run the new
image through native loader/startup readback and the full repository suite.

Runtime follow-up retains an intermittent default-idle Linux timer/RCU stall
after the first 512 callbacks and drained module-drop marker. The later
poll-idle and original-idle passes do not resolve its cause. Keep this failure
open separately from successful ABI and image readbacks. Native image guest 3
passes all 56 image/table pairs and 64 forced startup-allocation failures.
The earlier cleanup failures are explained by free-page movement into Linux's
PCP caches: the diagnostic measures 4,096 KiB fewer buddy pages and 4,088 KiB
more free PCP pages. The test correction accounts for both sources of free
pages without increasing its 4 MiB allowance. Final assertion replay and the
full suite are pending; all captures are in the runtime WIP checkpoint.

The final cleanup assertion now passes guest 4, with all 56 image/table pairs,
64 forced startup-allocation failures and four cleanup measurements losing
only 8-12 KiB each. The full repository suite subsequently passes 2,315 tests
(2,244 passed, 71 skipped) on clean source `0d5cd7b0`; the initial formatting
failure remains retained. See `native-irq-final-validation-20260907.json`.
The intermittent IRQ guest stall and real cross-kernel transport remain open.

For the next adapter, the exact native `Module.symvers` exports
`irq_work_queue`, `irq_work_run` and `irq_work_sync`. Its `raised_list` is
private, and `irq_work_queue_on` has no exported module symbol. The x86 IRQ-work
vector is `0xf6`. Use these pinned boundaries when choosing the owned transport;
do not infer module access from a declaration alone. Retain OS/module owners
until the guest has stopped sending and every queued callback has drained.
