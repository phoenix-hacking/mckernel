# Native startup page tables

The source-bound prototype now allocates, fills, retains and retires the x86
startup page tables in the real native Linux SMP module. See
[`native-startup-tables-checkpoint-20260907.json`](native-startup-tables-checkpoint-20260907.json)
for exact compiler inputs, artifacts, the first failed guest and the corrected
passing guest. This is preparation for native McKernel boot; no CPU wakeup,
trampoline, boot-parameter or IKC acceptance is claimed.

## Reuse and lifetime

Retain `smp_memory.rs::PageOwner`, the canonical `MemoryMap`, exact `OsToken`,
`smp_image.rs::BootLayout` and the existing ELF writer. The new allocation-free
`smp_startup.rs::PageTablePlan` adapts the frozen x86 SMP startup mapping ABI:
256 GiB identity and straight maps share a subtree, and four 2 MiB leaves map
the checked 8 MiB kernel window. Existing McKernel Rust consumers and the
legacy assembly/C fallback source remain unchanged.

One original Linux order-9 compound allocation contains 260 useful table pages.
DMA32 keeps the initial CR3 address below 4 GiB, even when the image occupies
another NUMA node above 4 GiB. The allocation uses ZERO, COMP, NORETRY and
NOWARN without THISNODE. The table plan rejects misalignment, overflow and
overlap with assigned bootstrap RAM. Each mutable reference and physical
readback stays within that single retained Linux allocation.

`LoadedImage` is now noncopy and owns its `StartupTables`. Allocation and fill
finish before the first image write. Replacement invalidates the prior image
before reading a new file; memory reassignment/release and unbooted destruction
also drop the original table owner. The existing IHK lease, provider-module
reference, per-OS operation mutex and CPU-then-memory locks remain authoritative.
Later CPU wakeup must retain these allocations across every uncertain outcome;
the current unbooted cleanup rules cannot be used after a CPU might run.

## Failure and verification

The first native guest found a real allocator API error: passing NUMA_NO_NODE
to `__alloc_pages_noprof` dereferenced an invalid node. The exact Linux
`mm/mempolicy.c::alloc_pages_noprof` is exported and resolves the current node
and policy before calling the lower-level allocator. The corrected adapter
uses that API for startup allocations and preserves concrete-node THISNODE
allocation for existing resource reservations. Both the original failure and
the successful rebuild are retained; no C shim or exported Linux patch was
needed for this repair.

The corrected four-vCPU/two-NUMA guest passes native and compat ABIs over two
module cycles. All 56 physical image readbacks match the ELF model. All 56
physical table readbacks match an independent hierarchical x86 encoder,
including high-memory image placement. Sixty-four forced order-9 allocation
failures recover, and 32 repeated load/invalidate cycles check table-owner
cleanup. Existing CPU, memory, OS resource and unload regressions also pass.
The pure fixture walks every identity/straight-map leaf and checks kernel
edges, holes, noncanonical addresses, root bounds and atomic storage rejection.

The declared graph now adds this source and its module edge. The unsafe/FFI
queue preserves all prior IDs: RS011-SMP-0044 records the changed allocator
call, and RS011-SMP-0073/0074 record the new table fill and readback blocks.
Its 156 sites across 19 sources still require independent review and formal
compiler capture. The subsequent declared-stage build and guest pass, followed
by the full repository suite: 2,242 passed and 71 skipped. See
`native-startup-exact-stage-checkpoint-20260907.json` and
`native-startup-final-validation-20260907.json`. Production gates and scores
remain unchanged.
