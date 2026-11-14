# Native memory reservation: reuse and next integration boundary

The CPU adapter now has exact build/link and two-node guest evidence. The next
native deliverable is memory reservation and query/release, followed by resource
assignment to the existing generation-checked OS registry. The prototype now has
the bounded runtime evidence below. Exact staging and production acceptance
remain separate, incomplete requirements.

## Preserve the existing Rust

- `host-kernel/native-rust/smp_resource.rs`: retain `MemoryMap`, `MemoryExtent`,
  `MemoryWorkspace`, `MemoryTransaction`, prepare/commit/compensated rollback,
  sorted extent merging and poison semantics. Its existing model and fixtures
  already cover insert, assign, release, release-all, capacity and rollback.
  Physical Linux allocations must stay paired with this map; a second map with
  independent ownership rules would defeat that investment.
- `host-kernel/native-rust/os_runtime.rs`: retain the working `KmsgPages` owner.
  Its zeroed 4 MiB allocation uses Linux `get_free_pages_noprof`, bounded
  NORETRY/NOWARN flags and exactly balanced `free_pages`. It has native guest
  lifecycle coverage. Its current placement API cannot select a NUMA node.
  Adapt that ownership approach for node-aware pages; only extract a common
  owner after the existing kmsg consumer can retain its ABI and tests.
- `host-kernel/native-rust/page_allocator.rs`: retain `BitmapPageAllocator` and
  its allocation/reservation leases. They manage already-owned physical ranges;
  they do not acquire Linux buddy-allocator pages. Integrate when suballocation
  of assigned physical ranges is required, instead of treating this bitmap as
  proof of Linux memory ownership.
- `page_owner_registry.rs`, `os_registry.rs`, and the current provider leases:
  preserve generation and lifetime rules. `OsToken` in the SMP model stays
  private until a real checked IHK lease bridge can mint it. A userspace integer
  must not authorize memory ownership or destruction of a newer OS generation.
- Existing `kernel/rust/mem_helpers.rs`, XPMEM and mcctrl Rust memory helpers
  remain their existing McKernel/control-path consumers. Their 64-bit page
  attribute ABI repair and compatibility equivalence evidence are preserved.
  Their C bridge callbacks do not implement native Linux page reservation.

## Exact interfaces inspected

The pinned IHK reference is `ihk/linux/driver/smp/smp-driver.c`, including
`validate_mem_req`, `smp_ihk_reserve_mem`, `smp_ihk_query_mem`, and release paths.
`ihk/linux/include/ihk/ihk_host_user.h` defines `struct ihk_mem_req`: pointer to
`size_t` sizes, pointer to integer NUMA IDs, chunk count, minimum chunk size,
maximum ratio for the all-memory request, and timeout. Native and compat
layouts and the pointed-to size width differ. Reinspection located the existing
canonical `abi/x86_64.rs::IhkMemoryRequest`, including all six fields and the
32-byte/8-byte-aligned layout assertion. Reuse it unchanged; the earlier draft's
claim that this struct was absent was incorrect. Add only the missing compat
decoder and adapter. The legacy reserve granule is 4 MiB. Query with zero input
chunks returns the current chunk count through the request field.

The actual generated Linux bindings expose `__alloc_pages_noprof` and
`__free_pages`; `mm/page_alloc.c` exports both. The generated `MAX_PAGE_ORDER`
is 10, enough for an individual 4 MiB allocation on this 4 KiB-page target.
The current Rust `kernel::page::Page` abstraction allocates order zero only and
has no node-selecting constructor. Therefore importing it alone cannot fulfill
this interface. `node_states` is exported by Linux and the kernel has NUMA,
SPARSEMEM_VMEMMAP and memory hotplug enabled. Exact page-to-physical-address
conversion, node-state exclusion and page lifetime need an explicit review
before implementing the adapter; do not assume an inline C macro is an export.

The verified CPU checkpoint configuration has debugfs but **does not enable CONFIG_FAULT_INJECTION**.
CPU hotplug failure-state coverage does not imply buddy-allocation failure
injection is available. Any changed validation configuration needs its own bound
build evidence. Avoid inducing uncontrolled memory exhaustion as a substitute.

Further inspection of this exact build found that `get_online_mems` and
`put_online_mems` have generated bindings but no entries in `Module.symvers`.
They take/release the existing memory-hotplug read semaphore in
`mm/memory_hotplug.c`. A module cannot link them merely because bindings exist;
using that exclusion would require a separately reviewed export-only Linux
patch, exact rebuild, and validation. Do not inspect changing node masks without
a justified synchronization boundary.

`vmemmap_base` and `page_offset_base` are present in this build's export table.
The selected configuration has SPARSEMEM_VMEMMAP, dynamic memory layout, NUMA,
and five-level paging support. Generated bindings describe a 1,024-node mask,
`NODES_WIDTH=10`, and `NODES_MASK=1023`. Page-to-PFN conversion and node decoding
must follow the exact Linux definitions, with layout/shift assertions and live
placement checks. The subsequent prototype implements these checks and passes
the bounded guest capture below; exact staging and production acceptance remain open.

## Memory prototype in progress — 2026-09-07

The existing memory map now accepts sorted insertion/removal batches through
its original workspace, normalization, transaction and poison rules. A complete
candidate is checked before publication or Linux page release. Seven additive
cases cover ordering, overlap, ownership, capacity, split removal, compensation
and unchanged live state after a late error. The isolated Rust 1.92 fixture
passes all 45 cases, and its nine Python checks pass in 2.646 seconds; see
`/work/native-memory-policy-tests-20260907.log`. The old cases are retained.

`smp_memory.rs` adapts the existing `KmsgPages` owning-value approach to strict
NUMA allocation using ordinary Linux `__alloc_pages_noprof`/`__free_pages`.
It retains each original compound-page order and privately owns the entire
pending allocation batch before publishing through `MemoryMap`. It reuses
the canonical memory ABI and the CPU adapter's module pin. Full release and
partial release preflight every selected owner before returning pages.
This is new Linux adaptation around retained Rust policy. The initial policy
result was followed by the separately bound build and guest results below.

The prototype applies export-only patch `0004` for the existing Linux memory
hotplug read lock/unlock and node memory-statistics APIs. Its separate debug
configuration enables `FAULT_INJECTION`, `FAIL_PAGE_ALLOC`, and
`FAULT_INJECTION_DEBUG_FS`; the previous kernel, modules, stage, configuration,
and symbol table are preserved in `/work/native-memory-prototype-20260907`.
The fixed four-CPU/12-GiB native container completed that kernel build.

The new userspace-only guest fixture includes the unchanged CPU fixture and
adds native/compat memory validation. Planned runtime checks include strict
two-node placement, query and copy faults, an inaccessible second request
element with an unconsumed allocation-failure counter, closed-file module
pinning, every position of an eight-page-block allocation batch repeated three
times, free-memory recovery, lower-order fallback, bounded all-memory requests,
partial-release rounding, late release failures, and concurrent reserve/release.
The guest repeats both ABIs across two module load/unload cycles. These are
prepared tests at the initial policy checkpoint. Their subsequent results follow.

## Verified prototype capture — 2026-09-07

[The memory checkpoint](native-memory-checkpoint-20260907.json) retains 37
artifacts binding the compiled source, configuration, compiler records, probe
sources, exact run recipes and serial logs. All three modules build against the
fault-injection kernel. Linux 6.12's missing Rust `EOVERFLOW` constant is handled
through its public errno conversion API. Objtool patch `0024` recognizes the
two exact Rust 1.92 library panic symbols reached by sorting and `Vec::remove`.
The original tool rejects the unchanged object with five fallthrough errors;
the updated tool accepts it, and three unknown-callee mutations still reject
with four, one and five errors. All original objtool flags remain enabled.

Source review also corrected partial release to retain memory when the next
compound allocation would exceed the request. A 5-MiB trim of order-10 memory
releases 4 MiB; a following 1-MiB trim leaves the pool unchanged. Candidate
selection preserves the legacy smallest-chunk-first and alignment behavior.

The final four-vCPU/two-node guest passes both ABIs over two module cycles:
96 injected allocation failures, untouched preexisting reservations, bounded
free-memory recovery, lower-order fallback, a bounded all-memory request,
malformed requests and late copy faults, release preflight, partial trimming,
closed-file module pinning, and three-worker/eight-iteration concurrency. It
reruns the unchanged CPU probe and the existing assembly OS lifecycle probes.
Creating and destroying unbooted OS instances preserves the 32-MiB reservation
pool. All CPUs return online, all modules unload, QEMU exits zero, and the strict
capture reports no missing or error markers. The free-memory check has an
explicit 8-MiB per-node noise tolerance; it is not exhaustive leak proof.

The first guest capture remains failed because informational printk traffic
split one CPU success marker. The subsequent guest limits live console output
to errors and emits the complete kernel ring buffer at exit. Exact marker
counts and warning/panic rejection remain unchanged. Both successful captures
and the original failed stream are retained separately.

This is prototype runtime evidence. The authoritative staging manifest,
workflow, source/FFI inventories and their current verification bindings still
need integration and a fresh exact-stage build/capture. The current full
repository suite has not been rerun for this prototype. No OS memory assignment,
native McKernel boot, IKC workload, all-Rust/assembly image, or production gate
completion follows from these results.

The subsequent [artifact/module check](native-memory-module-checks-20260907.json)
verifies all 37 retained artifact identities and their uncompressed contents.
The new adapter passes Rust formatting, and tracked/new source whitespace
checks pass. Disassembly of all three preserved modules confirms ELF64 x86-64
and finds no SIMD or x87 instructions in their executable sections. The
[check recipe](evidence/native-memory-module-checks-20260907.py) is retained.

## Next implementation and acceptance

Validate and copy the complete request before effects, preserve the legacy
4 MiB granule and query behavior, and use bounded sleepable allocation without
OOM-killer escalation. Retain every Linux allocation through an owning Rust
value and keep the SMP module pinned while memory remains reserved. Large
extent/journal storage belongs off the kernel stack. Failed allocation, policy
capacity, copyout and release paths must preserve ownership or perform verified
rollback; OS-owned memory must never return to Linux before guest access ends.

First verify bounded reservations on both nodes in the existing four-vCPU,
8 GiB disposable guest, including native and compat requests, zero/malformed
requests, physical alignment and node placement, query/copyout behavior,
allocation failure cleanup, module pinning and complete restoration. Then bind
CPU/memory assignment to OS leases, image loading, APIC start and IKC. Native
McKernel boot and workloads remain separate required results.

## Declared source integration checkpoint

The [staging integration record](native-memory-staging-integration-20260907.json)
binds the passing 182-case focused group and later 17-case unsafe/FFI group.
The production manifest, source audits, lifecycle contract, extracted native/compat
ioctl fixture and exact fixdep graph now include the memory adapter. The shared
reservation pin's safety argument covers CPU and memory contexts. No algorithm or
ABI is replaced by this integration. All prior unsafe-site IDs remain; the 14 new
memory sites retain pending independent review and no gate credit.

The [fresh declared-stage debug build and guest](native-memory-exact-stage-checkpoint-20260907.json)
now pass separately from the retained prototype: kernel, three modules, exact link
closure and native/compat two-cycle runtime replay. The [final validation record](native-memory-final-validation-20260907.json)
adds passing runtime/workflow/license bindings and the 2,301-test repository suite
(2,230 passed, 71 skipped). The frozen configuration replay retains its original
patch list while separately pinning the later objtool-only addition. OS resource
assignment, McKernel startup, IKC and workloads remain subsequent functional
deliverables; see the [resource bridge plan](native-os-resource-bridge-plan.md).
