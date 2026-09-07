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

The native boot note and parser now pass policy tests and all three refreshed
images pass the actual loader parser. Native image SHA is
`3eb7b36b3ef1ee069dbfdb163bff9f7a39bf828af3635417cd708a9a6f011be8`;
loaded-window FNV64 is `cfcc0211e5daf7dd`. The IHK v3 callback pair passes
51 ownership cases, including preparation cleanup and persistent started-state
owners for native/compat calls. See the separate backend/image checkpoint.
The SMP provider still uses v2 until its real preparation/start adapter is
ready. Patch 0006 proposes existing Linux INIT/SIPI and init_top_pgt exports;
its first apply/build and native SMP integration remain pending.

## SMP integration work in progress

The native provider now uses the tested v3 preparation/start ABI in source.
Preparation reuses the existing `ihk_trampoline` parameter under Linux's
parameter mutex, the canonical loaded generation, existing boot ABI structs,
original compound page owners and startup code. IRQ route slots retain their
generation and veto the Linux target's offline transition. An irreversible
started marker precedes INIT/SIPI; uncertain boot leaks retained storage rather
than freeing it. Deep resource paths also reject started-image mutation.

The read-only `native_boot_prepare_only=1` diagnostic holds a complete unstarted
preparation and returns EAGAIN; it never reports boot success. The new guest
probe will exercise allocation failures, cross-OS trampoline exclusion, repeated
preparation, CPU-change invalidation and destruction over both ABIs. A later
start run must capture actual guest progress and retain failed-boot owners.
Current start code deliberately reports incomplete boot while the real host IKC
service is still being connected. Guest status 2 is not full readiness.
Performance event maps remain unsupported/zero and the current boot profile
uses 2 MiB default huge pages; those capabilities require separate integration.

Patch 0006 is applied in the isolated prepared Linux tree, with the existing
INIT/SIPI body verified byte-identical. Its first complete Linux rebuild is
still running. The new SMP source and guest probes have not yet compiled or
executed. This WIP checkpoint precedes those checks and is not declared-stage
or production acceptance.

The pinned Linux export rebuild and all three prototype native modules now
compile. Independent C witnesses verify both complete boot layouts. The
preparation-only guest passes both ABIs across two module lifetimes, including
32 forced allocation failures, trampoline exclusion, CPU-change invalidation,
cleanup and four independent physical snapshots.

The first actual INIT/SIPI executes McKernel through architectural status 2;
both master queues are published and the captured AP resolves to
`kernel/rust/init.rs::post_init`, waiting for the host IKC acknowledgment.
The capture itself failed because it incorrectly expected the temporary startup
page to remain unchanged after execution. The existing `arch_start` switches to
its own stack; `mem_numa_init_body_result` publishes the remaining bootstrap
range and `page_alloc.rs::__ihk_numa_add_free_pages` clears it under
`zero_at_free`. Kmsg reports that free range, which includes the startup page.
Preserve the failed guest and diagnosis. Keep whole-byte assertions for
preparation; a started capture must inspect the AP's real image/CR3, retained
low-page header, queue contents and kmsg. The corrected replay is still pending.

Both corrected actual-start guests now pass, one through the native ioctl ABI
and one through compat. Their independently captured AP registers resolve to
`post_init`; each uses an owned guest page table, has status 2 and two valid
empty 56-byte master-packet queues. The retained low-page boot header matches
the canonical addresses. Started resource mutations, destruction and module
removal remain rejected after close. Full host IKC service, INIT_ACK and later
readiness are the next implementation; no native shutdown is claimed.

## Next host IKC adapter

Reuse `host-kernel/native-rust/ikc_queue.rs::SharedQueue` for the host receive
endpoint and its checked publication body for the initial master acknowledgment.
Preserve the existing queue and master policy consumers. The legacy guest
consumer advances its read counter before copying, so the initial acknowledgment
adapter must publish only once into an empty queue and never reuse that slot;
do not silently weaken `SharedQueue::attach`'s sole-consumer contract. Full
subsequent host send support needs an explicit compatible consumption protocol.
Retain `ikc_master.rs::ConnectOffer` for validating the first guest request;
listener/channel allocation and sysfs/mcctrl dispatch remain later effects.

Store the receive endpoint in stable heap storage retained by the started boot
owner. Publish its pointer with release/acquire ordering into the existing
per-OS, generation-bound IRQ route. The callback must drain a bounded number
of packets using the existing queue body, perform no allocation or sleepable
lock acquisition, and preserve the first request for process-context diagnosis.
Publish this owner before sending INIT_ACK. Uncertain starts retain it forever
until a separately proven sender-stop and Linux IRQ drain can be implemented.

Use Linux's existing exported APIC static-call mask entry for the host-to-guest
notification, preserving the original assigned offline Linux CPU identity.
Include the existing x86 APIC header in Rust's generated binding closure so
preparation can reject logical-destination drivers explicitly. The pinned
physical-flat implementation iterates the supplied CPU mask and uses the retained
per-CPU hardware ID without filtering against Linux's online mask. No new C
function or copied APIC register driver is needed. Exact-header checks and a
fresh kernel/module build must precede the real bidirectional guest check.

Guest inspection also confirms the real control-channel setup is selected by
its existing `hidos` kernel argument before vDSO/sysfs requests. Connect the
unchanged SET_KARGS ioctl instead of inserting a synthetic default. Reuse the
loader's bounded UserSlice string reader; match the retained host's 1024-byte
read cap and SMP's 255-byte payload truncation. Store arguments with the IHK OS
generation independently of image replacement, retire unstarted preparation
on successful argument changes, and clear them on proven unbooted destruction.
The next guest must exercise invalid pointers, truncation and both ABIs before
using `hidos` for the real initial channel request.

The APIC binding rebuild, both exact header witnesses, all prototype modules,
seven queue tests and six master tests pass. The first new preparation guest
completed argument checks and eight cycles, then failed a cleanup probe that
requested one exact 128 MiB chunk on node 1. The existing release ABI matches
returned contiguous chunks; reservation may yield several chunks with that
total. Correct the fixture to query and assert the unchanged full 128 MiB per
node, verify exact 128 MiB rejection when node 1 is fragmented, and reuse its
existing `release_memory` helper for those actual chunks. Preserve the failure;
the retry must print the restored ranges and prove a zero pool plus CPU/module
restoration. No adapter release behavior or memory allowance is changed.

The corrected preparation guest now passes both ABIs and both module lifetimes.
Its independent queries show the full 128 MiB per node, including node-1 chunks
of 4, 108 and 16 MiB; exact 128 MiB rejection preserves the pool, then the
existing chunk release helper empties it. All four QMP captures verify the
255-byte truncated argument payload, boot layout and zero unstarted status.

Both native and compat actual-start guests now pass the first real exchange:
McKernel consumes INIT_ACK, logs `Master channel init acked.`, and sends the
port-501, 128-byte-packet CONNECT through Linux IRQ-work. Each Linux callback
consumes exactly one master packet. Independent QMP snapshots verify both queue
counter triples are (1,1,1), the acknowledgment and CONNECT wire bytes, guest
code execution and retained physical owners. The decoded request is a legitimate
one-way channel offer (`receive=0`, `send` owned by McKernel, magic 4905,
interrupt CPU -1); the null direction is not an invalid bidirectional mapping.

See `native-ikc-handshake-checkpoint-20260907.json` for retained source/build/
guest evidence and the initial preparation failure. The next adapter must
reuse the existing master listener/accept policy to establish this control
channel, connect subsequent regular channels and service vDSO/sysfs/mcctrl.
Full readiness requires status 3 and usable applications. Preserve the explicit
initial-publication restriction until the guest's consumption protocol supports
safe repeated slot reuse, then finish declared staging and current FFI/lifecycle/
license/verification bindings and a fresh complete suite. No production gate or
native shutdown evidence is promoted by the initial exchange.

## Repeated native queue exchange

Before listener acceptance, adapt the existing guest
`kernel/rust/ikc_queue.rs::{ihk_ikc_read_queue,ihk_ikc_read_queue_handler}`
under the established `native_linux_irq_work_v6_12` selection. These bodies
currently publish consumption before copying or invoking a borrowed-packet
handler. Retain the legacy selection and C fallback. The native selection will
claim the existing reserved header word at offset 60, hold the claim throughout
the read/handler, then release-publish consumption. A contending or reentrant
reader returns EBUSY instead of spinning in an interrupt. Shared native counter
reads must use aligned atomics. Header sizes, exported functions, packet formats
and existing caller ownership remain unchanged; callbacks cannot retain a slot
pointer after returning.

Reuse the host queue's existing private storage view and checked enqueue body
through a producer-only `SharedProducer` capability. Its unsafe attachment
contract requires the peer's copy-before-release consumption rule; it exposes
no dequeue operation. Preserve the stricter existing `SharedQueue::attach`
contract and the one-publication legacy adapter. Advertise this peer contract
as native boot note revision 2, emitted by the existing guest ABI consumer.
Keep revision 1 images loadable for historical comparisons, but reject their
native boot preparation before any startup effect. Reuse `ImagePlan` parsing
and fixtures for both supported revisions and unsupported-note rejection.

Verify the actual guest Rust readers against the actual native host producer,
including several producers/readers, tiny queues, repeated slot reuse and a
paused borrowed-packet handler. Reuse the pinned complete C queue bodies and
header with the same sequential driver as legacy/native Rust, then build
fallback, legacy Rust and native
Rust images. Only after this contract is demonstrated may the boot adapter use
repeated sends and the existing `ikc_master` listener/accept policy. No new C
implementation or Linux API is required by this queue adaptation.

The source adaptation now passes the real queue peer fixture on native Rust
1.92: all three sequential C/legacy Rust/native Rust drivers transfer 13,312
packets with the same digest `5d3367a006a52b85`; four producers and four guest
readers transfer 16,384 unique complete packets through eight slots. A paused
borrowed-packet handler keeps all 1,024 attempted writes backpressured, rejects
reentrant consumption, and permits 256 subsequent slot reuses after completion.
Invalid geometry, overlap, corrupt counters and claim retirement are checked.
The first C comparison compile omitted PIC and failed at the PIE link step;
the failed source/logs remain in completion-tests attempt 1. Attempt 2 corrects
only that flag and passes the peer check plus the existing queue/master/image
policy fixtures. Refreshed revision-2 images, module integration and real guest
replays are still pending. The host boot sender remains initial-only for now.

Further listener inspection fixes the next allocation boundary precisely:
`kernel/rust/host_helpers.rs::host_init_ikc2mckernel_result` first requests port
501 (128-byte packets, 16 KiB queue, magic 0x1329, interrupt CPU -1), followed
by `host_init_ikc2linux_result` on port 503 (magic 0x1129 and the Linux CPU).
Retain `ikc_master::{ListenerRegistry,MasterRouter,AcceptPlan,AcceptSuccess}`
for validation/reply fields. The null receive address in CONNECT means the host
must allocate that queue: even the Send listener needs an owned receive queue.
The existing guest `ikc_master.rs::ihk_ikc_connect` unconditionally maps the
reply's receive address and writes its queue header before enabling the channel.
Returning a successful reply with receive address zero would fault the guest.
Reuse original compound page owners for that retained allocation; validate the
guest-provided 16 KiB send mapping and its source CPU against the exact OS's
assigned memory and ordered CPUs before accepting. Preserve both queue owners,
channel identity and generation before reply publication.

The current IRQ callback retains only the first request for diagnosis. Before
accepting and receiving subsequent requests, replace that diagnostic-only drain
with a bounded owned packet handoff to process-context service using the existing
queue primitive. An interrupt cannot allocate a channel or acquire the resource
mutex held by BOOT. Outbound process operations also need one producer claim so
same-CPU interrupt reentry cannot wait behind an interrupted reservation. The
regular 501/503 channel adapters must precede their mcctrl/vDSO/sysfs dispatch;
the initial acknowledgment alone does not enable those services.

The revision-2 image checkpoint now passes all three image builds, the actual
parser against all three new images and the retained revision-1 image, both
boot-layout witnesses and all three native prototype modules. The initial
independent note extraction used native binutils without an output filename and
rewrote its input ELF. Its final hash check correctly failed. The exact original
object files and compatibility linker reproduce the recorded image bytes;
restoration and the corrected extraction with a separate output both pass.
Preserve those distinct captures and the mutated image as failure evidence.

Both preparation ABIs over two module cycles now additionally prove revision-1
native images load but fail BOOT before preparation, leaving status/CPU owners
unchanged. All 32 forced allocations, four physical snapshots and complete
unstarted cleanup pass. Both actual-start ABIs execute the new native image,
receive INIT_ACK and publish CONNECT through real Linux IRQ-work; QMP confirms
both (1,1,1) counter triples and exact packet fields. Native image SHA is
`8c7703327cca094c7c55664bca3288aea8e300371959ad630608c9d3c92722ca`, entry
`0xfffffffffe845e10`, loaded-window FNV64 `c9af6a2dd84ebcc5`.
Its revision-bound linked Rust text is 614,629 / 784,327 bytes (78.363871%);
this is language attribution, not whole-OS readiness or production credit.
See `native-ikc-completion-checkpoint-20260907.json`. Listener acceptance and
subsequent service requests are still pending; no application execution or
full boot/status 3 is claimed by this prerequisite.
