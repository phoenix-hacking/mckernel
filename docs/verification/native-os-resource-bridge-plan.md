# Native OS resource assignment: reuse and lifetime boundary

This is an implementation plan after the exact native memory checkpoint, not
an implemented feature or an acceptance result. The full goal still requires
native McKernel boot, workloads, Rust/assembly-only McKernel implementation and
production verification. Keep verification in the fixed four-CPU isolated runner.

## Existing bodies to preserve

- `os_registry.rs::OsRegistry`, `OsHandle`, `OsLease` and `DestroyGuard` already
  implement 64-slot generation checking, reference exclusion and rollback. An
  open OS file owns a lease; destruction requires no open references. Keep the
  existing generation bounds and never accept a userspace integer as a token.
- `os_runtime.rs::OsObject` already retains its provider registry lease, the SMP
  module reference, and owned kmsg pages. Its `OS_OBJECTS` publication is inside
  the existing reserve/commit protocol. A new backend belongs to that object.
- `smp_resource.rs::CpuTable` already prepares assignment/release and preserves
  assignment rank; `MemoryMap` already prepares assignment, release and release-
  all with bounded workspaces and compensation/poison rules. Adapt these bodies.
- `smp_cpu.rs` already owns offline Linux CPU devices, blocks external online
  operations and retains the module while resources remain. `smp_memory.rs`
  already owns exact Linux compound-page allocations, and its coverage verifier
  explicitly allows free and OS-owned map segments without a second owner map.
- `abi/x86_64.rs` already declares OS CPU/memory assign/release/query commands,
  CPU count, IKC mapping commands and the canonical request layouts. Preserve
  command values and both native and compat widths.
- The older Rust McKernel, mcctrl and user-tool implementations keep their
  existing consumers. This bridge does not replace their allocation, process,
  mapping or communication algorithms.

## Concrete integration approach

Add a versioned, scalar-argument C-ABI callback table supplied by the native SMP
module while creating an OS. A new create entry point can accept that table;
retain the existing v1 unbooted entry point for its existing consumers. Copy the
validated table into the OS object before device publication. The existing
`ProviderModule` owner keeps every callback resident for the object's lifetime.
This avoids a cyclic IHK/SMP module dependency or a separately published global
table that could race with OS creation. The table's pointer comes from trusted
module code, never from an ioctl argument.

Route native and compat OS callbacks through the existing `OsLease`, obtaining
the matching object while that exact generation remains live. Serialize state-
changing operations with a sleepable per-object lock; the same lock must cover
future image loading/boot transitions. Native user addresses retain all 64 bits;
compat addresses are zero-extended once before request parsing. Status-only
commands retain their existing dispatcher and scalar return ABI.

Only that checked lease callback or an exclusive destruction guard may enter
the SMP token constructor. Keep `OsToken` fields private and retain the existing
test-only constructor. A production constructor needs an explicit unsafe
contract describing the versioned IHK lease proof and its lifetime; bounds
checks alone cannot prove that an OS generation exists.

Reuse the existing CPU and memory controllers. A callback borrows their contexts
only for the duration protected by the OS object's module owner. Preserve CPU
then memory lock ordering for coupled teardown, and do not allow a controller
guard or borrowed context to escape the callback. Ordinary resource operations
must not acquire an OS lock from inside a controller lock.

Prepare CPU and memory cleanup completely before either is committed during
OS destruction. Return resources to the reserved pool, retaining Linux owners
and reservation pins, before publishing the slot as vacant. A preparation
failure leaves the existing OS and its resources intact. The later booted path
must additionally stop/reset CPUs and retire mappings before this logical
cleanup; unbooted assignment cannot substitute for that requirement.

## Request details that need explicit adaptation

The device CPU parser sorts and deduplicates reservation input. OS assignment
must preserve the caller's order because that determines McKernel logical CPU
rank. Reuse the header decoder and existing rank-aware policy, not the device
reservation ordering behavior. Query must preserve the pinned IHK count and
ordering semantics. Exercise duplicates and cross-OS ownership explicitly.

The memory request layout is shared, but reserve-only allocation hints must not
silently become new OS assignment/query requirements. Compare each command's
validation with the pinned IHK source. Assignment must select existing free
ranges on the requested node rather than allocate another Linux pool. Preserve
compound-page ownership: no Linux free may occur while any assigned subrange
still uses that allocation. The legacy assignment code handles compound-page
boundaries when splitting chunks; inspect and test that behavior before choosing
an exact rounding or split policy. Existing free/owned coverage checks remain.

A whole multi-range request needs a bounded candidate before publication. Extend
the existing batch memory transaction machinery for assignment/release as needed;
sequentially committing individual chunks would expose partial assignment when
a later request is invalid. OS-specific queries filter by the complete token,
while device queries continue to report the free reserved pool.

## Evidence needed for the next functional checkpoint

Use the existing policy fixtures for order, generation, capacity, atomic late
errors and poison/compensation behavior. Add real guest cases for both ABIs:
two OS instances with disjoint resources, cross-OS release rejection, ordered
CPU queries, memory queries, count/address faults, late-invalid batch rollback,
concurrent opens/operations and destroy-vs-open exclusion. Destroy and recreate
the same minor and prove the new generation cannot inherit or release the old
ownership. Close files while resources remain, then destroy/unload in order and
verify CPUs, memory and modules are restored. Keep the earlier reservation and
failure-injection guest cases as regressions.

After assignment, continue into the preserved image loader, AP startup, IKC and
unchanged user tools. No boot or language-completion credit follows from this
plan or from an unbooted assignment test.
