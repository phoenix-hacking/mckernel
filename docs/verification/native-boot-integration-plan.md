# Native McKernel boot integration

The preceding checkpoints prove the native-selected image, image/startup-table
owners, direct Linux IRQ transport and an exclusive low-memory region. Connect
these existing bodies to the native OS boot operation. The end state remains
real McKernel readiness, IKC and application execution followed by complete
Rust/assembly ownership and independent production acceptance.

## Reuse and new integration

- Extract `Reservation` and `LowRegion` from the passing trampoline-region
  fixture into the native SMP source and make that fixture consume the same
  implementation. Retain its E820 coverage, exclusive claim and ordered unmap/
  release behavior. Generalize only the bounded writer/readback access needed
  to prepare the retained assembly; no physical address comes from an OS user
  pointer or substitutes for an owner.
- Adapt the pinned IHK `smp-x86_64-trampoline.S` and
  `smp-x86_64-startup.S` into reviewed native assembly inputs. Preserve instruction
  bodies and ABI offsets, replacing only preprocessing constants, local label
  scope and section/symbol names required by Rust assembly inclusion. Compare
  their complete emitted bytes against the original assembly before use.
- Retain `smp_image.rs::BootLayout`, `smp_startup.rs::PageTablePlan`,
  `smp_memory.rs::PageOwner` and the exact `LoadedImage` owner. The startup entry,
  stack and image physical addresses come from that checked layout. Keep all
  new boot storage with the exact loaded generation; resource changes or
  replacement loads may retire it only before any CPU-start effect.
- Adapt the existing `kernel/rust/x86_setup.rs::SmpBootParam` ABI declaration
  and the pinned C boot-parameter construction to the native allocator and
  topology. Preserve the guest Rust consumers. Exact witnesses must verify
  performance-enabled and disabled header sizes, every used offset and the
  CPU/NUMA/memory/distance tails. Fill from the canonical resource maps and
  real Linux clock, page-table, kmsg and IRQ identities.
- Extend the IHK backend with an additive versioned boot callback pair.
  Preserve the existing v1/v2 entry points. Preparation receives trusted
  physical kmsg scalars from IHK's existing allocation and performs no CPU
  start. IHK then publishes Booting under its existing per-OS operation mutex
  before invoking the start callback. A failed or uncertain start retains
  the OS/module, CPU, memory, page-table, trampoline and communication owners;
  returning to NotBooted requires a separately proven stop and drain.
- Reuse the pinned Linux INIT/SIPI implementation through an explicit GPL
  export, without changing its function body or introducing a project C helper.
  Exclude device/CPU hotplug while checking and starting the exact assigned
  offline CPU. Use the existing exported APIC and per-CPU services for the
  already-verified IRQ transport. Linux IRQ destination CPUs need a permanent
  offline veto for the active communication lifetime, in addition to startup
  read-side exclusion.

## Runtime obligations

Preserve CPU-to-memory lock order. IRQ callbacks cannot take either sleepable
resource mutex. Their dispatch identity and storage must remain generation-bound
until all guest senders have stopped and Linux has drained every destination.
Use actual callback identities and queue addresses, never dummy boot fields.
The retained guest's architectural status 2 precedes post-init host/IKC work;
it is not full readiness. Status 3, usable IKC and the existing user interface
must be checked separately. Preserve kmsg and the existing early debug-port
markers so an interrupted boot has an observable failure point.

First verify complete preparation and failure cleanup, then execute the actual
image in the same four-CPU/two-NUMA disposable guest. Bound every wait and retain
uncertain resources instead of unloading live code or releasing reachable
memory. A disposable VM teardown can contain an incomplete start but is not
successful native shutdown or resource-restoration evidence. Continue to the
full boot/IKC/application path; these intermediate checks do not redefine the
goal or change production-credit flags.

## Work checkpoint before validation

Extracted the tested low-memory owner into `smp_trampoline.rs`, retaining its
fixture consumer. Added immutable native assembly inputs and `smp_boot_code.rs`
using the pinned IHK instruction bodies. The source is a WIP: the first exact
assembly comparison, extracted-owner build and repeated guests remain to run.
The native OS boot callback and CPU startup are still being implemented; these
files do not change the current declared stage or claim executable boot.

The extraction now passes: both full native assembly bodies match the original
IHK bytes in the Rust object and final module, and all three low-memory guest
modes pass with the shared native owner. The explicit-hole guest additionally
reads back the whole copied trampoline on all 128 leases. The initial final-ELF
section extraction failure and corrected retry are preserved in
`native-boot-code-checkpoint-20260907.json`. No assembly execution is claimed.

Further reuse inspection found the complete existing native
`abi/x86_64.rs::IhkSmpBootParam` and its CPU/NUMA/chunk/dump types. Retain these
verified layouts directly instead of duplicating guest Rust types. The optional
performance tail begins at the existing `hardware_event_map` field. Before boot,
require an explicit native ELF note containing the host IRQ ABI and exact guest
header size. Emit it from the existing guest Rust crate and preserve all legacy
image consumers; images lacking the note remain loadable but cannot enter the
native boot operation. Add checked note parsing to the existing `ImagePlan`.
