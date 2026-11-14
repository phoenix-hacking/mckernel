# Native sysfs integration

## Verified actual guest sysfs checkpoint, 2026-09-08

All four image profiles build, with the fixture absent from the three normal
profiles and present only when explicitly enabled. Four invalid-configuration
checks pass. Both startup ABIs execute the opt-in fixture in an actual McKernel
image: each completes 52 metadata requests with nine exact expected errors,
nine special reads, 260 independent value reads, 256 stores and eight checked
data release callbacks. The rejected duplicate never receives a release. Both
4,095-byte ordinary/bitmap reads and a 4,096-byte ordinary store pass; malformed
return counts become EOVERFLOW, absent remote stores retain EIO, explicit callback
errors propagate and mapped snooping stores retain ENOSPC. Both temporary
subtrees and all eight samples retire while the established roots remain.

The opt-in phases complete 542 and 544 callback exchanges; the difference is
status polling. Both normal-image regressions also reach full readiness. All
four runs return BOOT=0/Ready=4, retain eight physical status-3 captures and add
520 post-ready callbacks with all 256 online-store payloads independently checked.
This is actual guest sysfs traffic; McKernel applications have not run.

`native-guest-sysfs-checkpoint-20260908.json` retains nine captures and 22
artifacts, including the first formatter, image-harness and guest-controller
failures. Thirty-two current native source bindings, 68 guest compiler-source
bindings and 18 Linux probe bindings verify. Image archives retain every entry
except exact copies of evidence already committed to Git; the manifest records
each omitted blob, SHA-256, mode and restoration path. The original passing
revision-3 image remains byte-identical. Preserve the new image family 2 and
snooping module 3 as active inputs alongside established dependencies.

The value workers finish before their subtree is removed. Forced removal while
a guest value read is active, remaining metadata/worker/queue fault injection,
multiple McKernel CPUs/OSes, native application services, applications, shutdown,
current full-suite integration and the complete language/production acceptance
scope remain open. No production gate is promoted.

## Actual guest metadata and special-format verification decision, 2026-09-08

Add an opt-in `ENABLE_NATIVE_SYSFS_VERIFY` image profile, default OFF, requiring
the x86_64 Rust kernel and linux-6.12 IRQ ABI. Its fixture compiles into the
actual McKernel image and calls the existing Rust public sysfs request functions
and callback dispatcher. Reuse `setup_remote_snooping_samples` for all eight
legacy formats. Source review finds one transcription error there: the Rust
string sample passes the address of its pointer, whereas kernel/init.c passes
the string bytes themselves. Restore that original instance contract and test
the actual resulting string through Linux sysfs.

Use a compile-time fixture module under scripts/tests/fixtures, with no new
production host protocol, diagnostic IHK identities or C implementation body.
Publish temporary directories, directory links, four independent writable
remote values, ordinary absent/error callbacks, full-capacity show/store and
oversized return-count cases, plus a 14,560-bit snooping mask. Exercise all five
metadata operations, duplicate publication, missing paths, stale handles,
protected roots and ancestor removal through actual IKC requests. Check that
a rejected duplicate never receives a guest release callback.

A Linux userspace helper starts before BOOT and polls for the fixture control
file while BOOT is waiting for physical readiness. Guest callbacks only update
atomic phase/value counters; they must never issue blocking metadata requests
from the IRQ handler. The normal guest boot thread waits with interrupts enabled,
removes the value subtree after the Linux read/write workers finish, checks each
actual remote release exactly once, and publishes a second phase. After Linux
checks those results, the guest retires its control namespace and eight samples
before returning to normal done_init/status-3 startup. Keep the pre-existing
test roots and CPU topology intact. A timeout or missing handshake is failure.

Expected values come independently from Linux integer/bitmap formatting and
known payload construction. Require complete 4,095-byte reads, 4,096-byte stores,
original errno behavior, isolated concurrent values and exact guest callback
counters. Retain real metadata results, guest kmsg and both QMP snapshots; account
for every metadata/reply packet without assuming a fixed number of status polls.
Repeat both startup ioctl ABIs and the ordinary post-ready callback regression.
Build the normal C, legacy Rust and native Rust profiles as regressions, verifying
that the fixture is absent there, and retain the original passing image unchanged.

Use the pinned compat container for guest image builds and the pinned native
container for Linux probe compilation and QEMU, one invocation at a time under
the established limits. Preserve the first failing command, error and complete
attempt before changing expectations or implementation. All current worker/queue
allocation faults, multi-CPU/multi-OS operation, native application services,
shutdown and the full Rust/assembly/integration/acceptance scope remain required.

The first actual guest reaches all nine special reads and four completed value
workers before the controller fails its absent remote-store errno expectation.
The existing guest `sysfs_default_response_ssize_result` returns EIO, used by
`sysfss_req_store_body_result` when its callback is absent. This differs from
host-local snooping's absent-store ENOSPC. Keep both production dispatchers
unchanged and require those distinct original errors in the Linux controller.
The retained metadata log includes fields after Create/Symlink/Unlink variants;
count the leading variant while retaining and checking the complete raw trace.

## Verified exact-capacity output, 2026-09-08

Module attempt 3 and Linux guest attempt 3 pass the bitmap boundary correction.
Each legacy comparison now also tests an output slice ending exactly at the
last text byte and another one byte too short. Across both module lifetimes,
274 C format comparisons and 274 exact-capacity comparisons pass; all 274 short
outputs are rejected. A real 14,560-bit sysfs mask returns exactly 4,095 bytes,
matching independently constructed userspace hex groups. Both writes through
this writable-mode snooping file return the original ENOSPC. The 2,560 concurrent
scalar reads, 128 claim collisions, capacity/alias/reuse checks, two callback/
mapping drains and six joined workers also pass again.

Both actual startups pass with module 3, attempt 2 for each ABI: BOOT=0,
registry Ready=4, four physical status-3 captures and 260 real callbacks.
`native-sysfs-snoop-boundary-checkpoint-20260908.json` retains 16 artifacts,
44 current compiler bindings, three exact format replays and pinned Linux's
bitmap implementation. Its references preserve the earlier failed guest.
Use `native-sysfs-snoop-module-20260908-3` for new native checks. The diagnostic
mapping fixture does not grant IHK authority; direct guest special operations,
remaining metadata/failure paths, applications, shutdown and the full declared
language/integration/acceptance scope remain required. No gate is promoted.

## Snooping and mapping verification decision, 2026-09-08

Module attempt 2 and Linux guest attempt 2 now pass. Two module lifetimes
complete 272 unchanged-C format comparisons, 2,560 concurrent scalar reads,
128 claim-collision races and both callback/mapping drains; six workers join
and both namespaces retire. The 66-slot exhaustion/reuse and fixed/request/
snooping alias checks also pass. The original guest failure remains retained.
Both actual startup ABIs pass with the corrected modules: four physical ready
captures and another 260 real remote callbacks. See
native-sysfs-snoop-checkpoint-20260908.json for 19 artifacts, 44 source/compiler
bindings, three exact pinned-format replays and the failed first guest.
The diagnostic carriers do not grant IHK authority.

The follow-up above comes from pinned Linux source review: bitmap_print_to_buf copies at most
the requested count from a formatted string plus NUL. Complete text can end
exactly at the supplied output length, with its newline present and NUL omitted.
The initial Snoop wrongly required both bytes. The corrected adapter accepts
a final newline without NUL and still rejects missing-newline truncation;
the oracle-derived capacity checks and real full-size reads above verify it.

The first Linux fixture exposes a missing operation-specific store override:
the generic native AttributeOps default returns EIO, while the existing
mcctrl_sysfs_store_body_result returns ENOSPC for all eight snooping operations
with no store callback. Preserve that existing errno explicitly in Snoop;
retain the failed run and repeat the unchanged expectation.

Retain the existing eight operation IDs and Linux formatting. Numeric values
must come from one aligned native-width RAM load, matching the scalar access
in the existing remote snooping bodies; reject unaligned scalar mappings before
publication. Use relaxed 32/64-bit atomic loads on retained coherent RAM so a
concurrent native-width producer cannot create a mixed-byte value. This adds
no ordering claim between distinct guest fields. Strings retain the existing
bounded precision behavior: a descriptor-sized string without NUL is valid
when its bytes plus newline fit the output. Reject output overflow explicitly.

Exercise the unchanged Memory/Claim/Region and Snoop sources in a disposable
Linux fixture with module-owned RAM and diagnostic extent/identity carriers.
Extract the actual complete-extent checker without changing its body; these
carriers test the mapping algorithm and do not grant IHK authority or claim
another actual McKernel startup. Compare all eight formats with the existing
C bodies, including numeric boundaries, partial-word bitmaps and bounded
strings. Verify alias exclusion, duplicate claims, fixed queue reservations,
request-slot exhaustion, completion/reuse and retained file mappings. Concurrent
scalar producers and real Linux file reads must only observe complete values.
Keep direct continuing metadata/queue/task failure and actual guest coverage
open until separately exercised. All compilation and runtime use the pinned
native container and original resource limits; preserve the first failure.

## Verified continuing service, 2026-09-08

Both actual startup ABIs now complete full one-CPU McKernel boot: BOOT=0,
registry Ready=4 and physical status 3. Each completes four creates, one lookup
and two symlinks, followed by 66 reads and 64 writes through the real guest
callbacks. Independent QMP captures before and after the calls show drained
queues; both CPU symlinks resolve to their intended targets. McKernel kmsg
contains its booted message and every alternating store payload. The existing
store_fake_cpu_info is NYI and does not change online; acknowledged bytes are
verified without claiming value mutation or CPU hotplug.

`native-sysfs-service-checkpoint-20260908.json` preserves eight captures and
all three failures in 24 artifacts, with 42 current source/compiler bindings.
The pinned three-module build and no-SIMD checks pass. Preparation retains
404 namespace checks, 32 original allocation failures, four physical captures
and full unstarted restoration through both ABIs and two module lifetimes.
The accepted real starts use helper v3, x86_64 attempt 3 and i386 attempt 1.
Keep `native-sysfs-service-module-20260908-2` as a current input.

Next directly exercise mkdir/unlink/remote release, eight special snooping
formats and claim handling in the actual continuing guest service. The Linux
fixture above covers bounded formats and claim collisions; actual queue pressure
and worker allocation failures still need direct coverage. Multiple active
McKernel CPUs/OSes, application execution, native
shutdown and complete resource restoration, current full-suite integration,
full Rust/assembly and independent production acceptance remain open.
The historical design/checkpoint sections below retain their original scope;
their earlier status-2 boot boundary is superseded by this checkpoint.

## Continuing request and callback adaptation, 2026-09-07

Runtime implementation decision, 2026-09-08: use two owned per-OS kthreads,
adapting the joined Linux peer-thread owner already verified by the remote
callback fixture. One pumps packets; one consumes a preallocated 64-entry
metadata queue. A dedicated metadata worker avoids coupling one OS's remote
release wait to another OS or the global workqueue. Both tasks are allocated
stopped before transferring the published tree and are activated only after
the BOOT caller releases CPU/device/topology/memory guards. Retain both task
owners in started storage before activation. Unstarted task cleanup must also
reclaim a callback context when kthread_stop prevents its first entry.

Share the existing whole-extent address checker between the live MemoryMap
and an immutable vector of exact-generation extents. A separate mapping ledger
excludes queues, shared data, vDSO, active metadata and retained snooping
regions. It has 66 request slots: 64 queued, one executing and one admission
slot so queue pressure can still receive a checked ENOMEM completion. Remove
the request claim under the ledger lock before the final busy release-store;
the peer may reuse the allocation immediately after observing that store.

The actual setup checkpoint now reaches CREATE for
`/sys/devices/system/cpu/num_processors`. Continue with the complete metadata
protocol (create, mkdir, symlink, lookup and unlink), ordinary remote callbacks,
special snooping files and a retained packet service. Do not replace remote
callbacks with fixed values or acknowledge files before their operations exist.

Adapt `mcctrl_sysfs_req_common_body_result` and the unchanged `sysfs_msg.h`
layouts into bounded native snapshots and error/handle-before-busy completion.
The caller must validate the whole exact-generation mapping, reject queue/data
aliases and retain an exclusive request claim before decoding. Client ops and
instance are opaque guest tokens; only McKernel may invoke them. Guest-visible
directory handles remain checked native tree identities.

Adapt `mcctrl_sysfs_remote_common_body_result`,
`mcctrl_sysfs_remote_release_body_result`, `mcctrl_sysfs_resp_body_result`
and `sysfss_packet_handler_body_result` into one shared-data exchange per OS.
Use a fresh positive request token for every exchange; the guest already echoes
arg1 without dereferencing it. Match token and response kind before completing,
bound every returned byte count, and preserve an outstanding exchange when a
Linux waiter is interrupted. Queue-full before publication can retry; an error
after publication cannot authorize buffer reuse. Release must also finish
before the guest can retire its instance after unlink.

Linux file removal drains active callbacks while the metadata/tree lock is
held. Its response processing must therefore run independently of that lock.
The intended continuing owner has a dedicated packet pump and separate bounded
metadata work, using the pinned Linux Rust workqueue and condition-variable
APIs. Ingress must reject duplicate/overlapping outstanding metadata mappings;
queue pressure must receive a checked error completion without blocking the
response pump. Packet processing owns channel publication and outgoing sends.
Callback operations own only the shared exchange and never reacquire the tree
or resource locks. Special snooping operations retain checked OS-owned regions
and use bounded volatile reads, not guest-derived Linux references.

The current BOOT loop holds CPU/device/topology/memory locks. Transfer the
validated memory extents, owned service/channel state and retained CPU target
before releasing those guards; wait for readiness outside them. Started
BootStorage and existing module/resource pins must retain every allocation and
callback throughout errors. Return successful BOOT only after full status 3
and continuing service readiness. Native shutdown and the entire declared
Rust/assembly and production acceptance scope remain required afterward.

Validate the unchanged C layouts and actual protocol/state bodies first, then
the real Linux callback adapter with an independent peer and concurrent file
removal. Integrate the owned pump and run both actual McKernel startup ABIs;
fixture success alone does not prove guest sysfs or application completion.

## Verified remote callback boundary, 2026-09-07

The native metadata decoder and exchange state pass seven actual-body tests:
32 unchanged-C layout values, 2,560 concurrent metadata completions and 4,096
responses through nine extracted existing guest Rust bodies. The final protocol
capture preserves immutable originals and compiler bytes. Earlier fixture type
failure and original-source recorder limitation remain documented in
`native-sysfs-request-protocol-20260907.json`.

`sysfs_remote.rs` now compiles in all three native modules and in the disposable
Linux fixture. It uses the pinned Rust Mutex/CondVar, a caller flag that can be
released on interruption without releasing the pending exchange, bounded
volatile copies and a release gate armed only after successful file creation.
The fixture's separate peer keeps replies moving while Tree::unlink drains an
active file callback, and acknowledges release before that unlink finishes.

Two module lifetimes pass 512 concurrent write/read round trips, 1,068 completed
exchanges and 1,068 forced pre-publication queue-full retries. Each lifetime
interrupts a reader, proves the next reader still waits for the outstanding
peer write, and then receives its own fresh result. Each removes a file during
an active callback and verifies both callback and remote release completion.
All 18 published remote attributes release, failed duplicate creation never
releases its guest token, and both namespaces disappear. Four page-boundary
checks and eight malformed-count/errno checks also pass.

`native-sysfs-remote-checkpoint-20260907.json` retains 16 artifacts, 31 exact
source/compiler bindings and three references. Three older formatting changes
are bound by the exact pinned rustfmt replay. The allocator-error conversion,
fixture visibility and CondVar symbol assertion failures remain FAIL; module
attempt 4 and guest attempt 1 pass. Linux's notify_all is imported through its
Rust library rather than a direct __wake_up import.

This fixture uses a separately owned Linux page and diagnostic identity in
place of the setup mapping carrier. It proves no IHK generation or actual
McKernel extent ownership. Continuing dispatch, request claims/aliases, special
snooping, real CREATE and both actual-start regressions remain the next work.
Architectural boot status is still 2; full readiness, applications, shutdown,
declared production integration, complete Rust/assembly and independent
acceptance remain open.

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

## Actual setup exchange verified

`native-sysfs-setup-checkpoint-20260907.json` records the subsequent preparation
and both real startup interfaces. Preparation passes 404 namespace checks,
the original 32 forced boot-allocation failures, four independent physical
captures and full unstarted restoration across two module lifetimes. Both
actual starts complete vDSO and SYSFS_REQ_SETUP with the new topology-export
kernel and CpuContext owner. Each OS publishes 52 exact files, 19 directories
and four links, including the final setup_complete marker. Expected values
come from Linux topology read before reservation, with McKernel CPU/node ranks
translated independently. Both starts preserve generation borrowing and retain
their namespaces after incomplete BOOT and refused destruction.

QMP captures each real port-503 queue advancing to SYSFS_REQ_CREATE (0x30) for
`/sys/devices/system/cpu/num_processors`, mode 0444 and busy=1. Request/data
extents, every queue, vDSO exclusion and guest callback tokens are captured.
The previous setup request may already be freed after acknowledgement; the
verifier does not interpret reused bytes as its old setup layout. The next
request proves that the guest observed the setup response and continued.

Architectural status remains 2, and BOOT returns -110/Failed with started owners
retained. Full ready status 3, continuing remote sysfs file/path/callback service,
other native mcctrl services, application execution, shutdown and production
integration/acceptance remain open. The initial packaging helper failed because
it assumed a top-level outputs field absent from the established OS guest
record schema. That failure is retained separately; retry 2 checks the actual
input/per-capture hashes and archives all capture files. Both guest starts
passed on their first attempts. All 15 final archives/gzip artifacts verify.
