# Native sysfs integration

Source parent: `96dde3b4461f604ca474809ba3649cbf444da005`.
Target: the pinned Linux `6.12.0-211.44.1.el10_2`, native Rust 1.92 and
revision-3 McKernel image from the completed vDSO service checkpoint.

Both native startup interfaces currently reach `SCD_MSG_SYSFS_REQ_SETUP`
(0x40). Its argument is at IKC packet byte 24. The captured setup request is
1,056 bytes, with buffer physical address at 8, buffer size at 16 and busy at
1,052. The shared data allocation is a separate 4 KiB page. Setup must publish
success only after its real host objects and required files exist. Full boot,
continuing runtime dispatch, applications and shutdown remain the objective.

## Reuse and missing ownership

| Existing body | Decision | Native boundary |
| --- | --- | --- |
| `kernel/rust/sysfs.rs::sysfs_init` and `object_helpers.rs::sysfs_init_body_result` | Retain the existing guest allocation, packet and wait path. | Validate the complete request and buffer against the exact OS generation and exclude queues before any host access or reply. |
| `executer/kernel/mcctrl/rust/mcctrl_helpers.rs::mcctrl_sysfs_req_setup_body_result` | Adapt mapping, setup and release-last completion order. | Its old map callbacks and `sysfsm_setup` depend on C-owned driver objects and unchecked legacy addresses. |
| `mcctrl_sysfs_req_common_body_result`, `mcctrl_sysfs_lookup_i_body_result`, `mcctrl_sysfs_work_main_body_result` | Reuse request ordering, lookup rules and message classification. | Replace raw node-pointer handles with owned native identities; keep dispatch in sleepable context and preserve remote response ordering. |
| `setup_sysfs_files`, `setup_local_snooping_files`, CPU/cache/NUMA topology bodies in the same Rust crate | Adapt their existing file names, values and topology translation. | Existing access bridges depend on legacy `mcctrl_usrdata`, saved topology and C tree mutation. Do not replace them with fabricated topology or an empty setup-complete directory. |
| `executer/kernel/mcctrl/sysfs.c::{sysfsm_setup,mkdir_i,create_i,symlink_i,unlink_i}` | Implement missing native ownership in Rust. | These primary Linux object, allocation and cleanup bodies have no reusable native Rust counterpart. Preserve existing fallback consumers and verify behavior against their actual paths. |
| `host-kernel/native-rust/os_runtime.rs::create_os` and the OS registry | Extend the existing device ownership boundary. | Sysfs must attach to the actual generation-owned `mcos` device, with explicit references and cleanup ordering; no parallel synthetic production device. |
| Pinned Linux `rust/kernel/device.rs`, `lib/kobject.c`, `fs/sysfs/{file,symlink}.c` | Reuse Linux device references, dynamic kobjects and existing sysfs primitives. | There is no safe Rust sysfs wrapper in this source. Linux's dynamic kobject type already provides `kobj_sysfs_ops`; Rust can own a stable `kobj_attribute` and its callback data without adding C code or a new Linux release body. |

## Ownership and validation sequence

First implement the missing directory, attribute and symlink owners. Attribute
data and names must remain stable while Linux can invoke callbacks. File removal
must drain active callbacks before freeing their Rust storage. Callback data
must support concurrent access; every supplied buffer and returned byte count
must stay within the sysfs page/count contract. Parent and symlink-target
references must outlive every registered dependent. Removal must never delete
a different owner's node after a failed duplicate creation or a name reuse.

Verify the exact generated Linux object/callback layout with an independent C
witness, build the actual Rust adapter in a disposable module and exercise
real sysfs reads, writes, duplicate failures, dependent teardown, concurrent
read/removal and module reload. This is the prerequisite object boundary,
not a completed SYSFS_REQ_SETUP exchange or an application test.

Next attach the owners to the existing OS device and add the native tree,
shared-buffer owner and complete setup-file/topology adaptation. Reuse the
existing Rust request/dispatch bodies with generation, extent, queue-alias,
path and handle checks. Verify request failures and publication ordering with
actual-body tests before repeating both actual McKernel startup interfaces.
Only a completed real setup may clear busy. Preserve unsupported next requests
and started owners until continuing host dispatch and shutdown are implemented.

Retain every first validation failure in `kernel.log` and evidence, use the
established isolated four-CPU/12-GiB containers and save coherent checkpoints
to GitHub. Declared staging/contracts/full-suite integration and independent
production acceptance remain required in addition to the prototype evidence.

## Object adapter implementation

`host-kernel/native-rust/sysfs_objects.rs` now owns directory registration,
stable attribute storage and symlinks. It uses Linux's existing `kobj_sysfs_ops`
with the generated `kobj_attribute` layout. Direct `kobject_init_and_add`
preserves add failures such as EEXIST; the convenience
`kobject_create_and_add` loses those error codes. A Rust release callback
reclaims only the boxed kobject allocation after Linux's final reference.
Failed directory adds also release through that callback. Every file/link
holds explicit object references, and failed duplicate creation never owns
or removes the original name. `sysfs_remove_file_ns` drains callbacks before
the attribute name and synchronized Rust operations can drop.

The current consumer is `scripts/tests/fixtures/mckernel_sysfs_objects_verify.rs`,
which includes the exact production source. Module attempts 1/3 pass formatting,
21 independent C/Rust layout values, actual module compilation and ELF/no-SIMD
checks. Attempt 2 also builds the module but fails the userspace fixture's
static libc link; its full inputs/logs are retained. Attempt 3 uses the existing
dynamic libc/loader, with their bytes and dependency report retained for the
disposable guest. Runtime checks and actual OS-device/service integration remain
pending at this implementation checkpoint.

Review of the pinned `fs/sysfs/dir.c::sysfs_remove_dir` identifies a further
caller obligation: object references alone do not serialize `kobj->sd`
removal against file/name operations. The adapter therefore shares one owned
Linux reference through Rust `Arc<DirectoryState>` and a pinned Rust mutex.
Direct registration/removal holds that mutex; directory removal marks the
state inactive before draining, and remaining file/link owners skip name
removal after that point. Symlink targets use Linux's existing separate target
lock, avoiding a second Rust namespace lock for reciprocal/same-directory
links. Callback code must not remove itself/ancestors or require its removal
lock. The real callback-drain fixture is repeated against this revision.

## Verified object checkpoint, 2026-09-07 local date

Final module 5 passes compilation, formatting, the 21-value independent C/Rust
layout witness and ELF/no-SIMD checks. Final guest 5 uses the unchanged pinned
Linux kernel, four TCG vCPUs and two NUMA nodes inside the established container.
Across two module lifetimes it passes 1,024 concurrent reads and writes and
32 races between actual directory/file destructors using 64 joined Linux
kernel threads. Failed duplicate directory/file/link creation preserves the
original nodes. Invalid names are rejected, and deleting an old parent before
its descendants does not remove a replacement subtree with the same names.

The user probe verifies exact file modes, symlink resolution, initial and
maximum-u64 values, malformed/overflowing writes and callback count overflow.
Each module removal observes an active slow callback and blocks until it exits;
then all Value callback payloads retire and the namespace disappears. An
already-open removed file rejects seek with ENODEV, exactly as the pinned
`fs/kernfs/file.c::kernfs_fop_llseek` requires. The final observed drain times
are 1,138 and 1,078 ms; these are fixture observations, not performance claims.

Four first failures remain preserved: the user fixture's missing static libc,
an incorrect BusyBox assumption in the new initramfs helper, loss of executable
permission on its copied dynamic loader, and an incorrect expectation that seek
would succeed after file removal. The first two guest attempts never execute
the object module. Guest 3 reaches real callback retirement before its fixture
assertion fails. Guests 4/5 pass; guest 5 adds the concurrent destructor races.
Linux intentionally emits duplicate-name diagnostic stacks during the negative
tests. The evidence validator requires every such stack to occur inside the
explicit duplicate-test spans and rejects unexpected diagnostics outside them.

`native-sysfs-objects-checkpoint-20260907.json` binds 27 retained artifacts,
the exact final production/test compiler inputs and the previous kernel/vDSO
evidence. All input/output hashes and gzip streams verify. This proves the
object boundary through its disposable module consumer. Allocation-pressure
fault injection and a complete OS lifecycle are not covered. Actual OS-device
binding, native tree/path/handle behavior, topology/setup files, owned shared
buffers and SYSFS_REQ_SETUP completion remain the next integration work.

## OS-device attachment implementation

The additive `ihk_os_with_kobject_v1` export borrows the actual `device_create`
result under a short, exact-generation registry lease. Acquisition rechecks the
generation against concurrent destruction/reuse. It deliberately does not take
the OS operation mutex: the boot backend already holds that mutex. Callback
code/context are synchronous kernel borrows; no private Rust layout crosses the
ABI, and callback status must be zero or a valid negative Linux errno.

`sysfs_os.rs` creates the legacy `/sys` child through that borrow and stores its
owner in `PreparedBoot`. Linux's successful child add takes the parent kobject
reference. Unstarted image/boot retirement removes the child before the backend
release returns and IHK unregisters its device; started storage retains it.
A permanent additional OsLease would prevent the destruction guard from ever
calling backend cleanup, so the child owns the Linux reference and backend
lifetime instead. This extends the existing ownership graph without creating a
second device or changing the old create/backend ABIs.

The root is prepared before CPU startup so allocation errors remain recoverable.
It contains no setup marker and acknowledges no guest request. Native tree,
topology/setup files, owned shared buffers and request dispatch remain required.
Module attempt 2 builds all three native modules and the borrowing fixture;
all three independent Linux device-layout values match, and module disassembly
passes the no-SIMD check. Attempt 1's fixture modpost failure remains retained:
the helper incorrectly supplied a per-directory Module.symvers path; the actual
in-tree build publishes these exports in the build-root manifest. Live
OS-device retirement and borrowing checks are pending at this build checkpoint.

## Verified OS-device checkpoint, 2026-09-07 local date

Both preparation interfaces across two module lifetimes pass 404 namespace
checks, including repeated root creation/removal, failed-operation preservation,
argument/image/CPU changes, OS destruction and minor reuse. The original 32
boot allocation failures, four independent physical captures and full unstarted
resource restoration also pass. Both actual-start interfaces retain the root
after incomplete BOOT and rejected destruction, passing four further namespace
checks. No run exposes a `setup_complete` marker.

The actual IHK export passes 60 borrowing checks across four fixture lifetimes
on started mcos0 generation 1, including absent callbacks/OS instances, invalid
slots/versions, mismatched generations, the exact Linux device name and errno
boundaries. Only 20 valid invocations reach the callback. These are Linux-side
boundary tests, not McKernel application tests. The device's size/alignment and
kobject offset match the independent C witness: 760, 8 and 0 bytes.

The native SMP prototype now consumes the production directory owner directly.
Both actual starts preserve the preceding vDSO exchange and independently
captured architectural status 2. SYSFS_REQ_SETUP remains pending with busy=1;
the next implementation is the native tree, topology/setup files, shared-buffer
ownership and real request completion, followed by continuing host service.

`native-sysfs-os-checkpoint-20260907.json` binds 19 retained artifacts. The
initial fixture modpost failure and retention source-binding failure remain
preserved. The latter found formatter changes in older inputs; the corrected
retention binds original repository bytes to the exact compiler bytes by
replaying the same pinned rustfmt command and retaining both versions. All
capture hashes and complete gzip streams pass. The failed retention's already
completed archives are preserved byte-for-byte in this final artifact set.

Borrowing has not yet been raced against OS destruction in the new fixture;
minor reuse is covered separately by preparation. The original allocation
failures do not inject every new sysfs allocation point. Full ready status,
application launch/tests, native shutdown, declared production integration,
full Rust/assembly ownership and independent acceptance remain open.

## Native tree reuse and boundary

Adapt the existing Rust `mcctrl_sysfs_lookup_i_body_result` directory/type/name
walk and the remaining C `lookup`, `dig`, `sysfsm_{create,mkdir,symlink,unlink}`,
`remove` and `cleanup_ancestor` ownership bodies. Preserve repeated-separator
lookup, automatic intermediate directories, duplicate errors, directory-only
symlink targets, no symlink traversal by the request lookup, recursive unlink
and the KEEP_ANCESTOR flag. As in the existing body, a later create failure may
leave successfully created intermediate directories; they remain owned.

Validate the whole bounded path before namespace mutation, rejecting NUL,
dot/dotdot and oversized components. Reject removal of the logical root or its
protected sys child before touching descendants. Replace guest-visible node
addresses with nonzero, positive-long identities from a nonwrapping module-wide
sequence; every operation validates membership in its own tree. No handle is
ever converted into a Linux or Rust pointer. Different trees and removed nodes
cannot alias live handles through slot or filename reuse.

The tree owns heterogeneous file operations through stable boxed callback
objects and the verified Directory/File/Link owners. Mutable tree access
serializes metadata changes; callbacks must not reacquire the tree/removal lock.
Use iterative leaf-first deletion and reverse-publication cleanup so teardown
does not allocate or recurse on a kernel stack. Store the tree in PreparedBoot's
existing OS-device lifetime. Verify actual Linux paths, data, links, errors and
retirement, including stale/cross-tree handles, before request completion.

Implementation WIP checkpoint during requested disk maintenance: the new
`sysfs_tree.rs` and its native-module, userspace and legacy-body comparison
fixtures are saved, including 60 shared path-operation cases. They have not
yet been compiled or executed. The next step is to extract the exact legacy
bodies into the fixture header, build the three native modules and tree fixture
in the pinned container, then run the disposable Linux guest and both existing
OS preparation/startup interfaces. This source checkpoint adds no runtime or
production acceptance claim; SYSFS_REQ_SETUP is still pending.

Tree build attempt 2 now passes in the pinned native container: all three
native modules, both boot layout witnesses, the OS-device borrowing fixture
and independent device layout, and the actual tree fixture compile. Module
disassembly checks find no SIMD/FPU register use. The helper extracts 15
unchanged legacy C bodies with byte offsets and individual hashes; their
userspace reference produces a 60-operation trace ending with only the two
protected nodes. Its Linux effects are stubbed only for this reference.
The separate native guest probe and exact dynamic libc/loader also build.
Attempt 1's missing fixture fmt! import is recorded and retained. Runtime
trace comparison, Linux namespace properties and both actual startup paths
remain pending at this build checkpoint.

## Verified tree checkpoint, 2026-09-07 local date

The disposable Linux guest passes two complete tree-module lifetimes. Each
matches all 60 legacy-body trace operations and verifies protected roots,
malformed paths without prefix mutation, stale and foreign identities, name
reuse, a 509-directory path and iterative teardown. Real sysfs modes, scalar
reads/writes and symlink resolution pass. Both module removals observe an active
callback, wait for it to finish (1,083 and 1,078 ms), then leave no namespace.

The native PreparedBoot owner also passes both user ABIs through two preparation
module lifetimes: 404 namespace checks, the original 32 allocation failures,
four independent physical captures and full unstarted resource restoration.
Both actual McKernel starts retain the tree root after incomplete boot, preserve
the completed vDSO exchange and pass another four namespace checks plus 60
OS-device borrowing checks. Architectural status remains 2 and SYSFS_REQ_SETUP
remains busy=1. These native trees still contain only the protected roots.

`native-sysfs-tree-checkpoint-20260907.json` retains 21 artifacts, including
the original fixture import failure, exact original/compiler sources, all
guest captures and the 15-body C extraction. All artifact hashes and full gzip
streams pass. Three older source files retain their explicit pinned rustfmt
replay bindings. New tree allocation-failure coverage, actual setup attributes,
shared-buffer ownership, continuing service, applications, shutdown and the
broader native integration/acceptance gates remain open.

## Topology capture boundary

The next setup adaptation retains the file names and ordering from the existing
Rust `setup_sysfs_files`, `setup_local_snooping_files`, CPU/cache setup and
`setup_node_files` bodies. Translate actual Linux CPU IDs and NUMA nodes into
the assigned McKernel ordering. Publish setup_complete only after every required
attribute and link succeeds; a missing topology or allocation error must not
be treated as successful setup.

The old collector in `ihk/linux/driver/smp/arch/x86_64/smp-arch-driver.c`
reads Linux sysfs at module initialization and saves topology before reservation.
Adapt that ownership boundary to Rust values. In the pinned Linux source,
`cacheinfo_cpu_pre_down` removes sysfs objects and can change shared CPU membership;
collecting after offline would lose siblings. Capture the initially supported
online CPU inventory under the existing device-hotplug and CPU read guards,
keep owned copies through reservation, and validate identity and current online
membership before admitting a reservation. Reject changed hardware/topology
instead of reusing stale data; existing owned CPUs retain their snapshot.

Reuse the already exported `cpu_info`, `cpu_core_map` and `cpu_sibling_map` and
their generated bindings. `get_cpu_cacheinfo` and its structures are already
bound but its existing Linux function lacks a module export. Add only the
missing GPL export, without a new C adapter body, then verify exact layouts
and captured values against independent Linux sysfs readings. Preserve cache
indices, scalar fields and real shared masks. The native snapshot must own all
data before releasing the hotplug guards; no Linux topology pointer may escape.

## Verified topology producer, 2026-09-07 local date

Patch 0009 exports the existing `get_cpu_cacheinfo` function. The pinned kernel
and existing native modules rebuild without changing the generated Rust bindings
or C topology declarations. `smp_topology.rs` copies the actual per-CPU scalar
fields, CPU masks and visible cache leaves into Rust-owned values while its
caller holds CPU hotplug exclusion. It reuses the established per-CPU linker
token calculation from the native raised-list integration. The copied values
hold no Linux topology pointers. Its current consumer is the disposable
`mckernel_topology_verify` fixture; CpuContext integration remains next.

All 45 independently compiled C/Rust layout values match. The fixture builds
with the expected Linux imports and no SIMD/FPU register use. In a four-vCPU,
two-NUMA TCG guest, two module lifetimes perform 376 scalar/mask checks and
32 cache-leaf checks against independent Linux sysfs and procfs readings. All
24 reads of owned snapshots stay byte-identical before CPU1 offline, while it
is offline and after it returns online. Linux removes CPU1's cache namespace
and changes CPU0's core-sibling mask from 3 to 1; the stored snapshots retain
the original topology. Both fixture namespaces retire completely on unload.

The pinned x86 `remove_siblinginfo` also clears an offline CPU's core_id, so
boot-time topology must use the retained pre-offline values. Cache masks need
more care: this QEMU model reports different valid L3 cache IDs for CPUs sharing
a mask. Linux's level/type/ID predicate leaves those cache masks unchanged on
offline. The final capture verifies that exact behavior and the changing core
mask separately. Do not reconstruct cache sharing from IDs or require every
raw Linux cache mask to lose an offline CPU bit. Reservation validation should
compare online membership and scalar identity against the saved snapshot.

`native-topology-checkpoint-20260907.json` retains the new kernel, producer,
fixture and three guest attempts. Guest 1 lacked a utility in its minimal root;
the corrected init uses existing Bash file reads. Guest 2 reached the guest
success marker but failed the original cache-mask assumption; a separate hash
function shadowing error prevented its final record write. The original pending
record and explicitly recovered FAIL record are both retained. Guest 3 passes
the corrected checks. Native CPU-context ownership, every new allocation failure,
the actual setup attributes and shared-buffer request completion remain open.
This new kernel has topology-fixture coverage; both actual McKernel startup
interfaces must be repeated after integrating the producer into the SMP owner.

## CPU reservation and setup service adaptation

Keep each initialization-time snapshot in the existing CpuDevice owner through
an Arc. After the existing policy preflight, compare a fresh online capture to
that snapshot under the CPU read guard before reservation has any hotplug effect.
Compare hardware/cache scalars and membership restricted to currently online
CPUs; retain Linux's observed cache masks. Drop the read guard before offline.
BootTopology lends these owned snapshots in the exact assigned CPU rank order.

Adapt the existing Rust setup sequence into the owned tree: test nodes, global
CPU lists, CPU/cache topology, node lists/distances and reciprocal links, then
setup_complete last. Use the same sorted node ranks and positive Linux distance
values already written to boot parameters. Translate saved Linux masks through
the assigned CPU list. Reuse Linux bitmap formatting with an explicitly bounded
buffer. Immutable callback payloads never borrow mutable guest memory.

Validate the whole 1,056-byte setup request and separate 4-KiB data page against
the retained exact OS generation, all active queues and one another. Keep only
an owned validated data descriptor after setup; use volatile wire accesses.
Adapt the existing setup body's error-before-release-before-busy-clear order.
On publication failure, retire every newly created tree entry before replying;
never leave setup_complete after a failed setup. Continue draining the real
channel after success so the next guest dependency is observed. Full ready,
continuing host services, applications and shutdown remain required.

## Setup build and Linux fixture checkpoint

`native-sysfs-setup-build-checkpoint-20260907.json` retains the integrated
three-module build, protocol tests, exact extent/reply-body fixture and real
Linux setup fixture. The wire layout matches all six values from the unchanged
legacy C header; 4,096 concurrent exchanges preserve release-last completion.
The actual ownership/reply bodies reject stale generations, incomplete extents,
all queue/vDSO/request/data aliases and malformed buffers before publication.
Their setup callback is an effect recorder, separate from real Linux coverage.

The Linux fixture uses assigned CPU ranks [3, 1] across two NUMA nodes. Its
97 files, 27 directories and seven links match independently read Linux values
and the legacy setup names. Across two module lifetimes, 582 complete text
reads stay identical before CPU offline, during offline and after restoration.
Four CPU offline/online cycles complete. A forced invalid-cache error occurs
after partial publication and removes every created entry while preserving
protected roots. Duplicate setup preserves the completed tree; all namespaces
retire on unload. Forty-four topology comparisons cover changed scalar fields,
cache identity/shape and online/offline membership. Not every allocation failure
has been injected. Actual McKernel setup completion still requires both startup
interfaces with this integrated CPU owner and new kernel.
