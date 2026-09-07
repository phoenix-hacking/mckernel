# Native image loading, boot and first application checks

The OS resource adapter now has a declared-stage build and four-CPU/two-NUMA
guest replay in `native-os-resource-exact-stage-checkpoint-20260907.json`.
Native McKernel has not booted. This document identifies the next implementation
boundaries; it grants no boot, application, language-completion or production
acceptance credit.

The [source-bound image-loader checkpoint](native-image-loader-checkpoint-20260907.json)
now passes a four-vCPU/two-NUMA guest with both ABIs and two module cycles.
All 24 physical image readbacks match the independent ELF model, alongside
the existing CPU, memory and OS resource regressions. The retained native
build matches the current source bytes. Declared staging, lifecycle/FFI and
downstream verification integration now pass, followed by a fresh declared-stage
build and guest replay; see `native-image-exact-stage-checkpoint-20260907.json`.
The full repository suite now passes 2,312 tests (2,241 passed, 71 skipped);
see `native-image-final-validation-20260907.json`. AP startup comes next.
No native McKernel boot is claimed.

First application checks require a repeatable native boot, working IKC channels,
and the native mcctrl process-launch/syscall path. The first program should
exercise output and a successful exit through the existing `mcexec` interface.
Memory, threads, file access, signals and futex checks follow; HPC performance
measurements need those functional checks first. A delivery date is not yet
established. These tests stay in the existing isolated four-CPU environment.

## Reuse and ownership boundaries

Retain `kernel/rust/x86_setup.rs::SmpBootParam`, `arch_start`, `arch_ready`,
`done_init` and the existing CPU, NUMA, memory and IKC accessors as the guest
boot ABI consumers. Retain `kernel/rust/ap.rs::ap_start`/`ap_init` and
`kernel/rust/x86_cpu_helpers.rs::x86_boot_cpu_body_result` for guest AP startup.
That guest helper uses McKernel's own page tables, stacks and wakeup callbacks;
it is not a Linux-side CPU-start adapter. Preserve the existing x86 assembly
entry and trampoline implementation while adapting its host-side preparation.

Reuse the current native `CpuTable`, canonical `MemoryMap`, Linux allocation
owners and exact `OsToken`. IHK's `OsLease` and `DestroyGuard` remain the OS
identity authority. Loading and boot transitions must take the same per-OS
operation mutex as resource calls. An image, startup page table or trampoline
owner must remain tied to the exact generation and be retired before minor
reuse. Do not create a second CPU or memory ownership map.

The existing allocation-free `host-kernel/native-rust/ihk_mapping.rs` provides
checked geometry, address/range descriptors and cleanup obligations. Its physical
range and page geometry are now reused by the staged SMP image loader. The
IHK-007 Linux user-VMA mapping adapter remains absent; image geometry reuse
does not establish its mapping, pinning or cleanup behavior.

The pinned IHK reference at `3114d9e7101ad52030eb3effa849a5c108972a1f` has no Rust
source. `ihk/linux/driver/smp/smp-driver.c::smp_ihk_os_load_file` describes the
kernel ELF placement convention, and `smp_ihk_os_setup_startup` in the x86 host
driver describes startup mappings and stack/trampoline fields. Preserve their
ABI and intended successful behavior, with explicit checks for malformed ELF,
integer overflow, short reads, resource ownership and reserved startup regions.
The old loader can write before all segments are checked; its failure paths
must not become permission to boot a partly loaded image.

The inspected prepared Linux 6.12 Rust crate exposes `uaccess`, allocation and
synchronization support, but no Rust file-open/read abstraction. File ownership
therefore needs a bounded adapter to the exact exported Linux functions, after
checking their pinned prototypes and lifetime rules. Preserve the existing
load ioctl and its bounded filename semantics; user addresses cannot be treated
as kernel pointers or callback identities.

For communication, retain the guest's existing `kernel/rust/ikc_master.rs`,
`ikc_queue.rs`, `smp_ikc.rs` and `mikc.rs`, and extend the native queue/master
foundations with the required mapping, interrupt and lifetime adapters.
`executer/kernel/mcctrl/rust/mcctrl_helpers.rs` contains the existing host
process/IKC/ELF work, including `load_elf`; its Linux C bridges still need native
adaptation. Preserve the current user tools and their Rust helpers.

## Next observable milestones

The next source prototype prepares owned x86 startup page tables during image
loading. Retain `smp_memory.rs::PageOwner`, `MemoryMap`, `OsToken`, `BootLayout`
and the existing ELF writer; adapt the Linux allocation owner to permit a
bounded DMA32 allocation without forcing the image's NUMA node. Newly implement
only the allocation-free `smp_startup.rs::PageTablePlan`, adapting the identity,
straight-map and kernel-window geometry from the pinned
`smp-arch-driver.c::smp_ihk_os_setup_startup`. Existing guest Rust consumers and
legacy C/assembly fallback builds remain selected as before. Linux's exact
generated `__alloc_pages_noprof`, DMA32 flags, vmemmap and direct-map bindings
provide the backing allocation; no new C adapter is introduced.

The useful 260 table pages fit in one order-9 compound allocation. Its original
owner must remain attached to the exact loaded OS generation, with cleanup on
failed/replaced loads, resource changes and unbooted destruction. Independent
x86 page walking and actual guest readback must verify all mappings, including
images above 4 GiB, and forced order-9 allocation failures must recover without
publishing a loaded image. This preparation does not start a CPU. Trampoline,
boot parameters, IRQ/IKC ownership, CPU wakeup and bounded readiness are still
required for native McKernel boot; the prototype does not promote any gate.

| Milestone | Required evidence |
| --- | --- |
| Load the existing kernel image | Owned bootstrap extent, checked ELF segments and entry, bounded writes/zeroing, and cleanup after every load failure; no CPU starts yet. |
| Start native McKernel | Exact boot-parameter layout, owned startup mappings and stack, AP startup, bounded readiness wait, guest diagnostics and tested failure cleanup. |
| Connect IKC and native mcctrl | Master-channel handshake, bidirectional packet progress, interrupt ownership, process launch and syscall forwarding, with close/shutdown handling. |
| Run applications | Repeatable minimal program through `mcexec`, then memory/thread/I/O/signal/futex regressions and resource restoration before performance work. |

Use the preserved image as an incremental integration target, and keep its
remaining C implementation explicitly accounted for. Completion of the user's
OS goal still requires the entire McKernel implementation and linked support
code to be Rust or reviewed assembly, as specified in
`mckernel-rust-assembly-completion.md`. A successful early application check
does not by itself satisfy that final requirement.

The initial startup-table source checkpoint passes 14 focused Python checks
(including the independent page walker and preserved OS/resource fixtures)
in 29.205 seconds under the pinned four-CPU native runner. Raw output and
source identities are retained in `artifacts/native-startup-policy-20260907-1.*.gz`.
Native compilation and guest verification are next; declared staging and FFI
bindings still describe the preceding accepted image-loader checkpoint.
