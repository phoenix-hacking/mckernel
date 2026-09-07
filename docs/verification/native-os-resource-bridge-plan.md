# Native OS resource assignment: reuse and lifetime boundary

The source-bound prototype is implemented and passes the isolated native/compat
guest as of 2026-09-07 12:00:22 UTC. See
[`native-os-resource-checkpoint-20260907.json`](native-os-resource-checkpoint-20260907.json).
Current staging, lifecycle, unsafe/FFI and verification bindings remain pending;
this is not an exact-stage or production acceptance result. The full goal still requires
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

The versioned `ihk_os_create_unbooted_v2` takes two scalar-argument C-ABI callback
identities and a checked ABI version from the native SMP module. The v1 entry
point remains exported for existing consumers. Copy the validated callback pair
into the OS object before device publication. The existing
`ProviderModule` owner keeps every callback resident for the object's lifetime.
This avoids a cyclic IHK/SMP module dependency or a separately published global
table that could race with OS creation. Callback identities come from trusted
module code, never from an ioctl argument; no shared Rust object layout crosses
the module boundary.

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

## Implemented prototype and remaining integration

The current adapter reuses `CpuTable`, its assignment ranks and rollback journal,
`MemoryMap`, `MemoryWorkspace`, exact Linux `PageOwner`s, and both existing module
reservation pins. Six added memory tests include 65,536 cases compared with an
independent per-page ownership model. The policy/fixture group passes 51 Rust
tests and ten Python checks, including compile failures for direct token fields,
an unchecked lease-constructor call and workspace aliasing. The constructor is
the one explicit unsafe contract in the otherwise allocation/FFI-free policy;
its scalar bounds checks alone do not prove authority.

IHK retains a pinned sleepable mutex per OS. Its file lease supplies the exact
generation, and the backend receives native addresses or once-zero-extended
compat addresses. Status aliases keep the existing scalar dispatcher. Resource
calls require `NotBooted`. The destruction transaction checks the status captured
by its exclusive guard before any callback, node removal or owner destruction.
The complete adapter mock fixture now passes 47 cases, including provider
allocation failures, invalid callback pairs/versions, release failures, concurrent
operations, minor reuse and rejection of cleanup during loading.

CPU assignment preserves input order and rejects duplicates. Assigned CPUs retain
the existing Linux device reference, offline state, online veto and resource pin.
Memory assignment selects the legacy exact match or largest free NUMA extent,
then commits a fully preflighted batch. Fixed requests remain page aligned. The
canonical map can split compound allocations logically because Rust metadata
lives outside the managed pages; the original Linux allocation owner is never
split or freed. A device release cannot free a partly assigned allocation. This
is an intentional adaptation of the legacy intrusive free-chunk metadata, which
could not place a new chunk header in an arbitrary compound tail. OS release uses
the sizes/nodes returned by the canonical ownership query.

Coupled destruction takes CPU then memory locks. Both transactions finish their
fallible preflight before either commit. Both locks remain held through publication;
if memory preparation fails, CPU logical preparation is compensated without Linux
hotplug effects. An instance with no CPUs still returns its memory. Cleanup returns
resources to the reserved pool; explicit device release returns them to Linux.

The three modules compile against the pinned Linux 6.12 debug configuration.
ELF64/x86-64 and no-SIMD/x87 instruction checks pass. Two retained prototype guest
runs pass, with the expanded second run finishing at 12:00:22 UTC. Each uses four
vCPUs, two NUMA nodes and 8 GiB under the offline four-CPU/12-GiB runner. Both ABIs
pass twice: ordered CPU transfer and rollback, cross-instance ownership checks,
page-sized memory assignment, whole-batch rollback, ALL/empty memory requests,
query faults, concurrent instance creation/assignment/release, closed-file module
pinning and destruction/recreation without inherited resources. Previous CPU and
memory regressions, including 96 injected allocation failures, also pass; every
CPU and module is restored. These are unbooted OS instances.

Next integrate these exact source changes into the existing manifests, lifecycle
contracts, unsafe/FFI review queue and downstream identities without rewriting
historical evidence. Then rebuild the declared stage, replay the expanded guest
and run the repository suite. After that, connect image loading, AP startup, IKC
and applications. The preserved Rust/assembly-only McKernel completion requirement
and production acceptance remain open.

## Declared-stage follow-through

The current manifest/lifecycle/FFI integration, declared kernel/module
build and four-CPU/two-NUMA guest replay now pass. The final suite ran
2,305 tests in 354.989 seconds: 2,234 passed and 71 skipped; see
`native-os-resource-final-validation-20260907.json`. Historical witness
fixtures remain bound to their original bytes. Continue with
`native-image-boot-plan.md`; image boot, IKC, native mcctrl execution,
applications and final language/production acceptance remain pending.
