# Native memory reservation: reuse and next integration boundary

The CPU adapter now has exact build/link and two-node guest evidence. The next
native deliverable is memory reservation and query/release, followed by resource
assignment to the existing generation-checked OS registry. This document records
inspected sources and remaining design work; it is not a memory runtime result.

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
layouts and the pointed-to size width differ. The current shared Rust ABI has
no memory request struct; add its exact definition without changing existing
CPU or OS layouts. The legacy reserve granule is 4 MiB. Query with zero input
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

The current configuration has debugfs but **does not enable CONFIG_FAULT_INJECTION**.
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
placement checks; neither is implemented or accepted by this inspection.

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
