# Native application service integration

Source reviewed at `4aea3ac846d499b3ebeb98393bfdc457020025ee` on 2026-09-08.
The actual guest sysfs checkpoint proves one executing McKernel CPU reaches
full readiness through both startup ABIs. Native applications have not run.
The remaining application work is production integration, not another boot
status milestone.

## Existing consumers and reuse decisions

| Source and symbols | Decision and native dependency |
| --- | --- |
| `executer/user/mcexec.c` and `executer/user/rust/mcexec_helpers.rs::{mcexec_setup_cpu_topology_body,mcexec_setup_dma_ppd_body,mcexec_main_prepare_image_body}` | Retain the existing launcher and configured Rust consumer. It requires GET_CPU/GET_NODES, executable and credential services, per-process data, image prepare/transfer/start, and syscall forwarding. Explicit `mcexec` invocation does not require automatic binary-format registration first. |
| `executer/kernel/mcctrl/rust/mcctrl_helpers.rs::{mcctrl_control_dispatch_body_result,mcctrl_control_get_cpu_body_result,mcctrl_control_get_nodes_body_result}` | Adapt the dispatch and count semantics. These selected compatibility-build bodies depend on C function tables, legacy `ihk_os_t`, `ihk_cpu_info`, and `mcctrl_usrdata`. Their pointer carriers cannot cross the native ownership boundary. Keep the compatibility consumers unchanged; use the existing native ABI constants and exact-generation boot owners instead. |
| `executer/kernel/mcctrl/rust/mcctrl_helpers.rs::{mcctrl_driver_ioctl_body_result,mcctrl_control_newprocess_body_result,mcctrl_control_start_image_body_result,mcctrl_control_ret_syscall_body_result}` | Retain now; adapt their process/image/IKC work next after the file and module lifetime connection is verified. No successful placeholder for these requests is acceptable. |
| `host-kernel/native-rust/abi/x86_64.rs` and `executer/include/uprotocol.h` | Reuse the already captured application ioctl numbers. Counts are scalar ioctl return values for both ABIs, not copied pointer payloads. |
| `host-kernel/native-rust/os_runtime.rs::{os_open,os_release,os_request,ProviderModule}` and `os_registry.rs::OsLease` | Extend the existing file ownership, module reference and generation checks. Do not create a second OS registry. Keep unbooted resource calls serialized; running application callbacks must not hold that operation mutex across waits. |
| `host-kernel/native-rust/smp_memory.rs::{LoadedImage,PreparedBoot}` and `smp_service.rs::Started` | Reuse the exact boot CPU list, the NUMA-node set used in the published boot parameters, and continuing-service health. Do not report Linux's available CPU/node counts as McKernel's assigned topology. |
| Pinned Linux `rust/kernel/{miscdevice.rs,types.rs,sync/lock/mutex.rs}`, `include/linux/module.h`, `kernel/module/main.c` | Reuse Rust allocation and pinned mutexes, and the existing bounded adapter to exported `try_module_get`/`module_put`. Linux's miscdevice abstraction owns one callback table through `.owner`; it does not implement a second module's service on an existing IHK character file. A project Rust adapter is required for that cross-module lifetime. |

## First production connection

Add one versioned, namespaced IHK registration for mcctrl's open/ioctl/close
callbacks. Registration itself must not pin mcctrl permanently. Lazy attachment
to an open OS file obtains a Linux module reference under the registration
mutex, then invokes callbacks outside that mutex. Unregistration and module
unload cannot race an unpinned callback. A successful attachment owns exactly
one opaque mcctrl context until final file release; release destroys that
context before dropping the mcctrl module reference and the OS lease.

The per-file mutex protects only initial publication. Application ioctls may
run concurrently on the same file and must not hold either this mutex or the
IHK OS operation mutex while executing. The callback contract requires its
context to support those concurrent borrows. Neither a user pointer nor a user
integer can become a callback, context, OS generation, or module pointer.

Route the existing application commands only for Ready/Running instances.
Implement GET_CPU and GET_NODES through mcctrl and a narrow IHK query of the
retained backend. Check the exact generation and current continuing-service
health. Return the positive CPU count and the boot NUMA-node count used by
the guest and sysfs. Keep all unimplemented launch/syscall requests rejected.
This is the first connection, not an application-execution claim.

The scalar service ABI and its new Rust ownership adapter need a native Kbuild
consumer; the prototype builder must include all new files and retain the
original and compiler inputs. Declared staging, FFI review and downstream
evidence integration follow the source-bound runtime checkpoint and remain
separate acceptance obligations.

## Required verification and remaining application work

Build all three modules with the exact Linux 6.12/Rust environment. Verify real
IHK imports, module dependency and ELF constraints. In the isolated four-vCPU,
two-NUMA Linux guest, test pre-ready rejection, module absence and reload,
file-held unload veto, duplicate descriptors, concurrent requests, final-close
retirement and fresh attachment after reload. Obtain CPU/node expectations
independently from the real guest boot parameters and sysfs, and exercise both
startup/user ABIs. Repeat the existing normal-image boot and continuing sysfs
checks with the changed modules. Preserve every failed attempt.

Then implement native executable/credential ownership, process data and VM
mapping/pinning, existing image prepare/transfer/start packets and acknowledgments,
syscall waits/replies, signals and process close/exit. First application acceptance
requires an actual program launched by the unchanged `mcexec` to print and exit,
followed by memory/thread/I/O/signal/futex checks. Full shutdown must explicitly
stop and drain application work before freeing any started resource. An OS
lease alone is not that drain proof. Multi-CPU/multi-OS, remaining sysfs faults
and races, full Rust/assembly completion, full-suite and independent production
acceptance remain required by the original goal.

## First connection verified, 2026-09-08

The [source-bound checkpoint](native-mcctrl-service-checkpoint-20260908.json)
retains the three-module build and both real guest ABI runs. Each ABI passes
1,056 GET_CPU/GET_NODES queries, eight joined workers, four context open/close
pairs, five module loads and unloads, and eight file-held unload vetoes. Existing
open files recover after an absent service is loaded; duplicated descriptors
keep one context alive until the last close, while separately opened files own
separate contexts. The probe rejects premature, absent-service and unsupported
image requests and confirms the registry stays Ready. Physical boot parameters
and actual guest sysfs independently establish one McKernel CPU/node in the
four-CPU/two-NUMA Linux guest.

Both normal-image startup regressions also pass, retaining four physical status-3
captures, 132 ordinary reads, 128 stores and 260 post-ready callback exchanges.
The original online-store NYI semantics remain unchanged. No program has been
launched by native mcctrl, and full shutdown remains absent.

The first build used an inherited capture name; its complete new output is
preserved unchanged under a unique path with a relocation map. Fresh module
attempt 2 is the sole input to these two guest runs. The first retention attempt
stopped on an existing source/formatter mismatch. Three exact pinned formatter
replays now bind those unchanged sources to the compiler input, and the original
failed manifest/helper remain retained. Only verified duplicate archive copies
are omitted from that failed retention archive, with canonical restoration paths.

Next native requests in the unchanged loader include OPEN_EXEC/CLOSE_EXEC and
GET_CREDV. The latter's existing Rust body emits eight 32-bit credential values
through a checked user copy; OPEN_EXEC holds executable-file ownership through
launch. These need native Linux adapters before process-data, VM and image
packet integration. The retained file context is the ownership connection,
not proof of those unimplemented operations. Declared-stage/source-graph/FFI and
current full-suite integration remain separate unfinished work.

## Executable and credential adapter review, 2026-09-08

Reviewed source parent: `6f9e29abdcbbdb9fada38724b2ae8ecb242896cf`.
Retain the existing launcher and all compatibility helpers. Adapt
`mcctrl_control_getcredv_body_result` and its eight-value ordering to the pinned
kernel's current subjective credentials and `UserSliceWriter`. Read the calling
task on each request, before any user copy or sleep, rather than caching the
credentials of the task that opened the OS file. Preserve the existing raw
`kuid_t`/`kgid_t` values and the 32-byte payload on both ABIs. Physical-address
GET_CRED still requires the later checked shared-memory adapter.

`mcexec_open_exec` in `executer/kernel/mcctrl/control.c` remains C-owned; the
existing Rust `mcctrl_control_close_exec_body_result` delegates its file/list
effects to C bridges. Adapt their successful open/replace/close ownership and
preserve the legacy positive EINVAL result when CLOSE_EXEC finds no executable.
Extract the current `smp_loader.rs::read_user_string` byte loop into a shared
native `user_string.rs` adapter, keeping the image-loader wrapper, filename limit,
error behavior and all current consumers. The executable path uses a heap buffer
bounded by PATH_MAX, checks termination, and preserves EINVAL for a faulted path
copy. Reject an unterminated PATH_MAX path with ENAMETOOLONG instead of the old
unbounded kernel string access.

The exact Linux `fs/exec.c::open_exec` and `do_open_execat` check execution
permission, regular-file type and noexec mounts, but this pinned source no longer
acquires write exclusion. Its matching `do_close_execat` now only calls `fput`.
Use the exported `open_exec`/`fput` and `d_path`, with a narrowly reviewed Rust
adapter for the `include/linux/fs.h::{deny_write_access,allow_write_access}`
signed atomic inode counter. Each successful denial must have exactly one
increment before its owned file reference is released. Failures, replacement,
CLOSE_EXEC and final file cleanup must all balance that owner. Do not assume the
legacy Linux inline behavior still runs in the new kernel.

Executable ownership is per OS generation and Linux process, not per descriptor.
Use the exported `get_task_pid(current, PIDTYPE_TGID)`/`put_pid` ownership to
identify a thread group without namespace-number collisions or PID reuse. The
existing Rust Task API does not expose this stable thread-group PID owner.
New native process glue shares one mutex-protected executable owner across
separately opened OS files belonging to the same process. Each file retains an
explicit process binding; the final binding retires the process entry. Forked
callers sharing an OS descriptor attach separate process identities. Global
publication locks must not cross pathname/user-copy/VFS operations; per-process
replacement publishes only a completely opened, denied and resolved file.

The existing `procfs.c` and `mcctrl_procfs_exe_link_body_result` also publish the
guest process/exe/task hierarchy and other guest-backed proc files. Retain those
consumers. The owned canonical executable path is an input to their later native
procfs/process integration; do not credit `/proc/mcosN/...` publication or full
OPEN_EXEC parity before that integration. Per-process data, native guest VM,
launch packets and syscall forwarding still need their existing Rust adapters.

Verify caller-vs-opener credentials, distinct real/effective/saved/fs IDs, bad
and boundary-crossing user buffers, current IDs after changes, and both ABIs.
Verify real VFS permission/noexec/type/busy failures, bounded paths, replacement
rollback, shared descriptors vs separately opened files vs forked processes,
write exclusion through successful ownership and its release on close/final exit,
and concurrent replacements without leaked exclusions. Repeat the established
module lifetime/topology and normal-image boot/sysfs checks. First application
execution, declared-stage/FFI/full-suite integration and the full original goal
remain open throughout this adapter checkpoint.

The first executable runtime diagnostic identifies an incorrect empty-path
expectation in the fixture. In the pinned Linux source, `fs/namei.c::getname_kernel`
copies an empty NUL-terminated name without the empty-name rejection performed
for userspace path acquisition. `path_init` starts at the current directory;
`link_path_walk` keeps `LAST_ROOT`, and `may_open` returns EACCES for a directory
with MAY_EXEC. `fs/exec.c::open_exec` uses that exact route, also called by the
existing `mcexec_open_exec` implementation. Correct only this expected result
from ENOENT to EACCES; retain ENOENT for the missing file and every other error
and ownership assertion. Module attempt 2 and its production sources remain
unchanged. Preserve failed guests 1/2/3 and rerun with fresh names. Retain both
pinned Linux source files with the executable checkpoint so this correction is
reviewable independently of the observed native ioctl result.

## Executable and credential checkpoint verified, 2026-09-08

[The retained checkpoint](native-mcctrl-exec-checkpoint-20260908.json) binds the
unchanged production module attempt 2 to passing x86_64 guest attempt 4 and i386
attempt 1. Both ABIs pass 518 independent credential comparisons (including IDs
above 16 bits), six copy faults, 1,116 executable/file assertions and six exact
context retirements. Write denial remains balanced through failures, replacement,
separate and duplicate descriptors, forked process isolation and final file close.
Two phases of four forked workers per ABI cover credential changes and executable
replacement. The existing topology/module/file and normal-image boot/sysfs checks
also pass, with four physical status-3 captures and 260 continuing callbacks.

All seven captures, including the four failures, are retained without exclusions.
The 19 artifacts also retain 43 native compiler bindings, 12 Linux probe bindings,
three exact pinned formatter replays and the six Linux review source files. No
new C production shim, guest-image change or launcher change was required.

This remains a host application-service checkpoint. Native procfs/exe publication,
PPD/VM/pinning, image launch, syscall forwarding and actual mcexec applications
are still required. Current process retirement follows final file bindings; the
inherited-descriptor test closes the child's executable explicitly, while the
automatic process-exit test gives the child its own file. Abrupt exit with a
shared descriptor held elsewhere and same-TGID thread races need the full
process-lifecycle adapter. Do not equate these tests with that pending coverage.
The accumulated declared staging/source-graph/FFI integration, current full suite
and all original runtime/language/independent acceptance requirements remain open.

## Native process registration and cleanup transport review, 2026-09-08

Reviewed parent: `e1a1d633869c7200dd85e371a397d916ee0e2fc1`. The next native
consumer is the unchanged launcher's `MCEXEC_UP_CREATE_PPD(NULL)` before
PREPARE_IMAGE. The existing `mcexec_create_per_process_data` body remains C-owned;
it creates per-process state, rejects duplicate registration, and uses the Rust
`mcctrl_control_newprocess_body_result` sequencing to attach final-file cleanup.
Its non-null `rpgtable_desc` branch also clears a Linux mirror mapping after
fork; that branch requires the later VM adapter and must remain explicitly
unsupported until implemented, with bad user copies still rejected.

Reuse the native `mcctrl_process.rs` OS-generation/referenced-TGID table and
existing file bindings. Add actual owned process registration with a retained
backend connection, duplicate exclusion and exactly-once final cleanup; do not
return success from an empty CREATE_PPD placeholder. No parallel PID registry or
legacy project C bridge is introduced. Extend this same registration with image,
VM, syscall and procfs state in subsequent work. Preserve the current explicit
limits on abrupt exit with an externally held inherited file.

`release_handler` currently sends SCD_MSG_CLEANUP_PROCESS and awaits
SCD_MSG_CLEANUP_PROCESS_RESP. Adapt `mcctrl_ikc_send_wait_array` ownership: queue
publication transfers the request to the continuing service, and a departing
waiter cannot free a published request or its later reply target. Reuse the
native sysfs RPC pattern for bounded pending requests and publication/reply
ordering. Traditional packets use the reply field at offset 16 as an opaque
non-reused scalar token, not the sysfs token field or a dereferenceable Linux
pointer. Match the exact reply message and CPU reference. The existing guest
Rust `host_cleanup_process_request_result` and `host_traditional_reply_result`
remain the peer; retain their cleanup/acknowledgement ordering and C fallback.

The SMP continuing owner already retains the exact guest memory and channels.
Extend its packet pump with the traditional cleanup exchange and independent
progress during caller waits. Add an explicit v4 OS backend callback family for
acquiring, invoking and releasing an application connection. Retain v1/v2/v3
exports. IHK opens the connection under its short OS operation guard, owns an
additional exact-generation lease, then invokes application work outside that
guard. Closing destroys the opaque backend context before releasing the lease.
Callbacks and opaque contexts are trusted kernel identities; no private Rust
layout or userspace value becomes a callback or connection. Do not hide a kernel
pointer operation behind a userspace-reachable private ioctl command.

Verify packet layout and reply semantics against the existing guest Rust/C
sources, including queue-full retry, wrong/stale replies and waiter departure.
In real guests, verify duplicate process registration, independent forked
registrations, file/module lifetime, exactly-once cleanup acknowledgements and
continued boot/sysfs service on both ABIs. The initial process registration owns
no prepared guest application. Actual image/VM preparation, image transfer/start,
syscall forwarding, procfs publication and application execution remain the next
required consumers of this connection, alongside all original acceptance work.

Implementation refinement: reserve one of 64 continuing cleanup descriptors when
opening a process connection, before publishing registration. Release therefore
requires no allocation; exhausted capacity returns EAGAIN before registration.
An unpublished connection cancels only its reservation. Queued/published requests
outlive a timed-out caller, and their numeric PID remains excluded until the
matching acknowledgement. Use the referenced Linux TGID's initial-namespace
number on the guest wire; retain the referenced PID object for local identity.
The initial request has no prepared thread or guest memory. An acknowledgement
precedes guest terminate_host, so it must not be promoted to proof of full task
termination or prepared-image retirement. Those owners and final termination
semantics remain part of the subsequent image/process lifecycle work.

## Process registration and cleanup checkpoint, 2026-09-08

Native module attempt 1, protocol attempt 1, x86_64 guest attempt 3 and i386
guest attempt 1 pass. Both real guest interfaces complete 306 PPD assertions:
146 registrations, 148 duplicate rejections, six user-copy faults, four explicit
unsupported mirror-VM requests, two 64-slot exhaustion/reuse phases, 138 joined
fork workers and 142 exact process-file context retirements. All 146 cleanup
acknowledgements have matching unique tokens and errno zero. Independent queue
captures show exactly 146 corresponding request/reply exchanges; all six physical
captures remain status 3. Existing executable/credential, topology/file lifetime
and 260 continuing sysfs callback regressions pass again.

Eight protocol tests bind the actual native state to four exact C declarations
and seven extracted unchanged guest Rust bodies. They cover cleanup/ACK/terminate
ordering, errno handling, reservation, queue-full retries, wrong/stale replies,
caller departure, malformed matching results and 4,096 concurrent unique tokens.
These fault paths are state/body checks; actual guest timeout, queue-full fault
injection and removal races remain open. The real guest capacity test exercises
the Linux adapter's 64-descriptor admission and complete reuse.

See `native-mcctrl-process-checkpoint-20260908.json`: six complete captures,
both original harness failures, 18 artifacts, 46 native compiler bindings,
14 Linux probe bindings, seven protocol compiler bindings, four unchanged image
peer source bindings, three exact formatter replays and four pinned Linux review
sources. The failures are the fixture's nested main macro before boot and final
capture parsing of the repeated shutdown dmesg output. Both remain FAIL in their
original complete captures. The corrected capture uses the original console
segment and retains strict metadata sequencing and queue assertions.

Preserve `native-mcctrl-process-module-20260908-1` and
`native-application-protocol-20260908-1` alongside the established image/kernel,
executable/service, snooping, compiler and setup dependencies. Next extend the
owned connection through actual image/VM preparation, transfer/start and syscall
service for the unchanged launcher. Procfs, full exit and prepared-task retirement,
non-null CREATE_PPD parity, same-TGID thread races and the full original language,
staging/FFI/full-suite, shutdown, multi-CPU/OS and acceptance work remain required.
No native application has run, and no production acceptance gate is promoted.

## Native image preparation and mirror VM reuse review, 2026-09-08

Reviewed parent: `4093b9a027c84034291abf556dead948d92b1d39`. The next actual
consumer is the unchanged x86_64 launcher's PREPARE_IMAGE, followed by TRANSFER
and START_IMAGE. Preserve that path and the full application verification goal.
The first implementation must prepare a real guest thread and return its actual
section/page-table results; an empty successful ioctl is not implementation.
The narrower cleanup-only registration checkpoint remains historical evidence.

Reuse `executer/include/uprotocol.h` and `kernel/rust/abi.rs` as the image ABI
sources. A checked native byte view avoids copying private Rust layouts across
modules. Verify every used field against independently compiled existing C and
guest Rust declarations. Keep pointer-width conversion explicit; the earlier
i386 registration probes do not prove image/VM compatibility. Validate section
counts, checked address geometry, CPU selection, and flattened argument/env
counts, offsets and terminating strings before exposing input to the guest.
The unchanged guest maps the fixed descriptor plus all 16 section slots even
when fewer are used, so allocate and zero that complete physical capacity.

Adapt `mcexec_prepare_image` and the existing guest
`host_prepare_process_body_result`, `host_prepare_ranges_args_envs_result` and
traditional reply path. Extend the existing `application_rpc.rs` and
`smp_application.rs` connection, not a parallel PID registry. Each published
operation gets a fresh opaque token and exact message/CPU/argument matching.
Reuse the current bounded reservation and independent packet pump. Descriptor,
arguments and environment must be owned physically contiguous allocations;
reuse the existing `smp_memory.rs` PageOwner/BootPages allocator rather than
introduce another Linux allocator. The continuing owner keeps published buffers
past a departing waiter and consumes the actual prepare reply before releasing
them. A prepared thread pointer comes only from the checked peer result and is
carried by its final cleanup request. Preparation and cleanup use the same guest
CPU queue. The cleanup ACK precedes terminate_host; do not claim it proves final
prepared-task retirement. Late replies, failed prepares and termination ordering
need direct verification as well as state tests.

Reuse `reserve_user_space` and `reserve_user_space_common`'s anon-inode-backed
mirror VMA. The existing Linux `anon_inode_getfile` implementation retains its
file-operations module; use a real native mmap/release/fault owner. VMAs retain
the application connection until their final file reference retires. Do not
create a reference cycle through mm_users. Preserve referenced MM identity for
cross-thread/fork/exec checks and keep publication locks out of waits and VFS
release. Check subtraction of the 512-GiB launcher gap and use
MAP_FIXED_NOREPLACE to avoid overwriting a raced mapping. The temporary
CAP_SYS_RAWIO override required for the existing zero-based reservation must be
reverted on every path; Linux's exported abort_creds balances prepare_creds
without introducing an ad-hoc credential refcount adapter. No extra McKernel C
bridge or private user-reachable ioctl is needed.

The actual RELEASE_USER_SPACE ioctl clears PTEs, while the legacy internal
release_user_space helper unmaps VMAs; preserve that distinction. The shared
anon inode must never be invalidated with an unscoped unmap_mapping_range.
Reuse the existing remote page-table translation and page-fault protocol for
mirror faults, with exact retained guest-memory bounds and per-process state.
User-supplied physical addresses must not authorize arbitrary guest RAM access.
Transfer must consume the prepared section ownership, and START must consume
the same prepared thread. Full syscall/signal/procfs/exit, mirror invalidation,
fork/exec lifetime, compatibility, real fault injection and application runs
remain required before acceptance, together with all earlier integration and
Rust/assembly requirements. Verify in the pinned containers and real guests,
retain first failures, and save coherent GitHub checkpoints periodically.

Image guest attempt 1 refinement: the exact Linux 6.12 anon_inodefs initializer
sets SB_I_NOEXEC (`fs/anon_inodes.c:89`), and `mm/mmap.c` returns EPERM for an
executable mapping on such a path. The legacy RWX mirror reservation therefore
cannot be copied unchanged onto this Linux ABI. Reserve the Linux mirror with
PROT_READ|PROT_WRITE: it serves host data access/transfer, while McKernel executes
the application under its own prepared page-table permissions. Preserve those
actual guest text/stack execute attributes and Linux's anon-inode mount policy.
The original failed guest capture remains evidence; retry with a fresh module
and guest. Full application execution still requires the same guest scheduling,
syscall and lifecycle work, with no reduction in the requested end state.

Image guest attempt 2 write-notify diagnosis: the preserved emergency capture
has Linux CPU 2 in asm_exc_page_fault (RIP 0xffffffff82001280, matching the
pinned System.map) with CR2 0x600080, exactly the probe's data store. The run
remains FAIL at its original 600-second timeout. Linux mm/mmap.c:81 and
mm/vma.c:1948 intentionally give a shared writable PFN mapping an initially
read-only vm_page_prot when pfn_mkwrite is installed. mm/memory.c:2494 calls
insert_pfn with mkwrite=false and returns VM_FAULT_NOPAGE; using that same fault
callback for pfn_mkwrite causes wp_pfn_shared (line 3614) to return without
finish_mkwrite_fault (line 3590), repeatedly retrying the unchanged read-only PTE.

Reuse the current exact-registration/MM guest LOOKUP permission check for both
callbacks, but give pfn_mkwrite its required success return of zero so Linux
locks, revalidates the original PTE and performs the write upgrade. Keep initial
PFN insertion in fault only. Guest text still requires an explicit successful
write-authorized LOOKUP; a rejected write returns SIGBUS. This introduces no
new C bridge, allocator, registry or private userspace ABI. The prepared image
and its page table are stable under the VMA-retained connection; full running
image invalidation and remote page faults remain required before START parity.

Extend the actual x86_64 guest probe with a joined raw-vfork child sharing the
originating MM: it must first write the original value to the second data page,
then publish a shared progress marker, and finally receive SIGBUS on a text
write. The parent checks both the progress marker and exact termination signal
and verifies all text bytes unchanged. This distinguishes write-permission
rejection from a blanket foreign-MM rejection. Disable core dumps for this
fixture and keep all child work inside the syscall assembly until exit/fault,
so vfork does not corrupt the suspended parent's stack. Preserve the original
failed helper/source/captures; use fresh module 7 and guest 3. Keep all baseline,
physical-memory, queue, capability and lifecycle assertions unchanged in strength.

Image guest attempt 3 teardown diagnosis: the PFN correction passes the actual
same-MM data write, readonly-text SIGBUS and unchanged-text checks, plus all
12,288 independently captured image bytes and three guest page walks. Teardown
then emits message 0x45 (printed in hex), SCD_MSG_PROCFS_TID_DELETE. The emergency
port-503 receive ring at byte 11200 contains OS 0 / CPU 0 / PID 351 / TID 0. The
native dispatcher currently treats it as unserviced and sets ENOSYS, so the
subsequent cleanup barrier's registration fails. Keep the original overall FAIL.

Reuse kernel/rust/object_helpers.rs::procfs_thread_ctl_result and the existing
mcctrl_procfs_work_main_body_result / mcctrl_procfs_delete_tid_entry_body_result
contract: DELETE does not wait for or require a response-memory write, and an
absent thread entry is a successful absence. The event's resp_pa points into a
guest stack and must never be dereferenced on DELETE. Prepared threads have no
scheduled TID (zero); host scheduling assigns the PID as TID in
host_schedule_process_request_result. This image phase has never published a
thread directory and needs no synthetic procfs node or fabricated writeback.

Extend the existing Exchange/Remote cleanup owner to retain a prepared,
unscheduled registration past its cleanup ACK until its exact OS/CPU/PID and
TID-zero deletion event is consumed. Reject foreign, duplicate, premature and
nonzero-TID events; unprepared cleanup still needs only its existing ACK. A late
event can retire an abandoned waiter without permitting premature PID reuse.
Route only this implemented deletion case through the existing packet worker;
actual procfs CREATE, reads, scheduled-thread tracking and full process/exit
parity remain required before application acceptance. Do not claim that DELETE
is final destruction: the same-CPU subsequent request still provides the
existing barrier past the cleanup handler. The traditional DELETE contains no
per-operation token, so ordered exactly-once queue delivery and the retained
unscheduled owner are the applicable identity boundary; full running process
and duplicate/reuse fault injection remain required.

Verify state and packet construction with the exact guest procfs helper and C
message constant, including the unchanged zero done flag on DELETE. Extend the
actual capture to prove one additional incoming deletion packet (no outgoing
reply) and its exact OS/CPU/PID/TID fields. Keep every prior queue invariant and
baseline assertion, accounting explicitly for the protocol's asymmetric event.
Use fresh module 8, image protocol attempt 2 and image guest attempt 4; module 7
and the original failed guest 3 remain unchanged. No application has executed.

## Actual prepared-image and mirror-VM checkpoint, 2026-09-08

Native module 8, protocol attempt 3, actual x86_64 image guest 4 and the unchanged
i386 baseline regression pass. The prepared image receives a real guest thread,
page table and two sections. All 47 image assertions pass, including 12,288
transferred bytes, 16,384 readback bytes and 24,576 mirror comparison bytes.
The joined vfork child shares the originating MM, successfully writes data and
receives SIGBUS on a text write; all text bytes remain unchanged. Capability
restoration, transfer bounds and copy faults, exact-owner PTE clear/refault,
foreign-process rejection, module unload vetoes and final VMA/file release pass.
Independent physical capture matches all 12,288 image bytes and three page walks.

Prepared cleanup now retains its unscheduled owner through both the traditional
ACK and the matching advisory TID-zero deletion. The final queue contains the
exact deletion packet and one additional incoming event with no outgoing reply.
A later acknowledged request on the same guest CPU supplies the original
handler-completion barrier. This verifies neither a scheduled process nor all
allocator/fork/exit semantics. Full native procfs publication and read paths,
scheduled TID tracking and running-VM synchronization remain required.

Both ABI regressions repeat 306 PPD checks, 518 credential checks, 1,116 executable
checks, 2,112 topology queries and 260 continuing sysfs callbacks. Seven physical
ready captures pass. Seventeen protocol/image tests bind the traditional packet
and image geometry to original C/guest Rust declarations and eleven exact guest
Rust functions, including advisory deletion construction and completion ownership.
The i386 regression does not claim image preparation compatibility.

See native-mcctrl-image-checkpoint-20260908.json: sixteen complete captures,
all seven original failures, 41 artifacts, 49 native compiler bindings, sixteen
Linux probe bindings, twelve protocol bindings, eleven unchanged guest peer
bindings, three exact formatter replays and sixteen pinned Linux reference files.
The noexec, repeated-write-fault and unserviced-deletion failures remain FAIL in
their original archives; the three build failures and duplicate C-declaration
fixture failure are also preserved. No existing assertion was removed to pass.

Preserve the accepted module/protocol and original build/image/setup dependencies.
Next implement START and the complete native procfs/syscall/signal/process services
needed by the actual ELF launcher, then run real applications. Continue running-VM
invalidation/pinning and remote faults, mprotect/mremap, compatibility, full
fork/exec/exit and real race/fault injection, alongside the accumulated declared
staging/source-graph/lifecycle/FFI/current-full-suite integration, full Rust/assembly,
shutdown, multi-CPU/OS, remaining sysfs faults and independent acceptance. This
checkpoint makes no application-execution or production-gate completion claim.

## Actual launcher integration review, 2026-09-08

Reviewed parent: `37fbf7962eaf1ffe6181e7564d5870c34a65ab2c`, verified on origin.
Retain `executer/user/CMakeLists.txt`, `mcexec.c` and
`rust/mcexec_helpers.rs` without production changes. The configured Rust consumer
`mcexec_finish_main_image_body` prepares and transfers the ELF, closes the
executable, initializes signal handlers and worker threads, and only then calls
START_IMAGE. `act_main_loop_body` concurrently enters WAIT_SYSCALL before START.
The C fallback preserves the same path. A START-only adapter is insufficient.

Rebuild both actual launcher selections with the pinned compatibility compiler
in fresh directories; bind their source, generated build commands, Rust object,
ELF/link outputs and runtime libraries. Use a sparse source checkout omitting
only committed `docs/verification/evidence` archives, with their Git object
inventory retained, to avoid duplicating large existing captures. Keep all
source code and submodule pins. Existing kernel/module/image captures remain
unchanged. The small freestanding ELF fixture exercises getpid, write and
exit_group through ordinary application syscalls. Its Linux reference result
must remain explicitly separate from later McKernel application acceptance.

For the native path, adapt the existing
`mcctrl_control_start_image_body_result` and scheduling serializer to the
retained Registration/Preparation rather than trusting user-provided remote
thread pointers. Preserve exact-generation CPU, MM and image ownership.
`kernel/rust/host_helpers.rs::host_schedule_process_request_result` assigns the
PID as TID and queues the prepared thread. The exact guest
`object_helpers.rs::procfs_thread_ctl_result` spins until CREATE completes;
the Linux-side `mcctrl_procfs_work_main_body_result` first publishes actual
thread entries and then writes its completion flag. DELETE never writes that
stack address. Native procfs publication/read ownership, syscall wait/return,
signals and scheduled-process cleanup must accompany real application startup.
Do not acknowledge unimplemented services or claim an application ran merely
because its image or launcher compiled.

The first actual launcher run (guest attempt 2) reaches both validated boot
captures and passes the Linux ELF reference, then fails in the unchanged
`mcexec_opendev_body` at IHK_OS_GET_BUILDID. The existing native
`ihk_smp_x86_64.rs::control_device_ioctl` already returns the authoritative
stager's exact NUL-terminated `ihk-compat-build-id.bin` through Linux Rust
UserSlice. Reuse that body for the OS-device request. Adapt the original pinned
IHK `smp_ihk_os_get_buildid` semantics: the same consumer-sized bytes and EFAULT
on failed copyout. No C bridge, new export or mcctrl service is needed.

Keep the existing OS file's exact-generation lease, backend module pin and
operation serializer. Permit only this immutable metadata query through the
current unbooted-state restriction; resource mutation remains restricted as
before. The backend validates the same lease token before copyout. Verify
native and compat pointers, exact trailing NUL and buffer guards, inaccessible,
readonly and partial-page copyout, both unbooted and running instances, and
operation with mcctrl absent. Then retry the same unmodified actual launcher.
Preserve the first run's build-ID failure and both harness failures unchanged.
