# Native application service integration

Source reviewed at `4aea3ac846d499b3ebeb98393bfdc457020025ee` on 2026-09-08.
At that initial review, the actual guest sysfs checkpoint proved one executing
McKernel CPU reached full readiness through both startup ABIs; applications
had not yet run. The current runtime checkpoint below supersedes that status.

## Current application baseline, 2026-09-09

**All application-baseline runtime gates and the readiness audit PASS.**
The current authority is
[`native-application-ultra-handoff-20260909.md`](native-application-ultra-handoff-20260909.md),
with the requirement-by-requirement
[`native-application-readiness-20260909.json`](native-application-readiness-20260909.json).
After the final GitHub commit is fetched and every selected blob verified,
mark the Max phase complete and stop for the user's Astra Ultra switch.

The same signal module 1 / signal image 2 now passes memory, file I/O,
threads/futexes and signals through the unchanged mcexec and dynamic-libc core.
Five accepted application guests provide 48 HELLO launches and five core runs,
including an independent signal replay. Every original route/result,
retirement, procfs/process and pager assertion remains intact.

Actual scheduled launcher/worker failure also passes: SIGKILL while a real
Linux worker is blocked in a delegated sixteen-byte read, bounded retirement
and release, 700 quiet Linux forks reusing both the old PID and worker TID
three times, then eight unchanged applications in the same OS. The complete
first runner pause/resume failure is retained alongside the passing attempt.

The final checkpoint retains all three new core replays, both full original
control-ABI regressions and the sequential batch. All original physical
counter assertions pass, along with 72 worker reaps, four inherited-TGID
retirements, boot and continuing services. The only regression adaptations
select the current inputs, use fresh output names and change the known
continuing-worker count from two to three; complete original/executed helpers
prove this. All 57 native and 37 guest compiler bindings match current sources.

The handoff records exact inputs, commands, results, failures and limitations.
This is readiness for broader testing, with one McKernel CPU and 128 MiB in
the isolated TCG guest. Production acceptance, multicore/MPI, long stress and
full Rust/assembly completion remain later work. The dated checkpoints below
are preserved history; they do not supersede this current acceptance status.

## Earlier application checkpoints

`native-application-core-checkpoint-20260909.json` retains fourteen complete
captures and all six original failures, including the earlier pathname-copy,
file-pager and dynamic-loader attempts. Memory guest 2 and files guest 1 each
run the unchanged dynamically linked libc application through the unchanged
`mcexec`. Both verify exact output, exit 37, scheduled retirement, registration
release and no remaining process nodes. Each also repeats eight HELLO launches
with exact write 25, exit 37 and complete cleanup; both metadata/string pointer
widths and the boot/continuing sysfs checks pass.

The memory mode verifies malloc/mmap data, read-only/read-write mprotect and
munmap/free. All fourteen host invalidations return and complete zero. Three
actual zeroing batches clear 503 chunks / 521 pages; later pending pages are
still OS-owned and are not represented as fully drained. The four shared libc
pager references release to zero. The file mode verifies 8,209 bytes through
create/write/stat/seek/read/EOF/pwrite/pread/fsync/close/reopen/unlink and expected
ENOENT after deletion. Its ten host invalidations and pager release also pass.
These are the first two complete ordinary libc core modes accepted in McKernel.

The first thread guest remains FAIL. The guest forwards unimplemented syscall
435 (`clone3`) to the generic Linux launcher path. Linux returns child PID 311
and the launcher terminates with SIGSEGV/exit 139; the guest never completes its
thread smoke. Cleanup ultimately retires the original PID and releases pager
references, but this does not establish the required abnormal-owner coverage.
Signals have not run because the batch stopped at that first failure. Preserve
the complete serial/debugcon and emergency physical memory/queue/register data.

The guest-local native clone3 adapter now passes 524 Linux-reference argument
vectors, the full clone adapter tests and both original marker selections.
The clone3 image checkpoint retains all four passing image configurations,
34 exact source bindings and the complete first compiler-path audit failure.
Actual native ELF slot 435 selects the Rust adapter, with legacy absence and
the existing clone handler preserved. Protection and zeroing binary checks
still pass. Clone3 image 2 is ready for the unchanged pthread application with
current host zeroing module 2; its runtime result remains pending.

The subsequent native clone3 guest now reaches the existing `settid` path.
Its unchanged launcher fails to transfer the TID array because the native
ioctl only authorizes prepared ELF sections; guest clone3 returns -14 and
the original pthread_create check fails. The TID checkpoint retains this
complete failure and the new host adapter: exact current worker/delivery,
request-sized physical buffer and shared payload claim through ordinary RET.
The 34 mailbox, three user-adapter and 52 payload/zeroing/module tests pass;
all three native modules and 57 compiler bindings verify. The next candidate
is TID module 1 with clone3 image 2. Its actual thread result is pending.
For two pthreads on one McKernel CPU, enable the existing allow_oversubscribe
boot option; the old hidos-only probe otherwise limits NR_TIDS to one. Keep
the original/adapted probe and all original application assertions.

The host zeroing checkpoint retains all 57 native compiler bindings, nine host
unit tests, three successful native modules, the exact Rust 1.92 objtool patch
and 77 configuration/license tests. All four guest image selections build.
The first new memory attempt was a retained harness failure: the old capture
validator expected two continuing workers after integration added the third.
Only that exact count changed in the executed reference; both original and
adapted references remain archived, along with all original assertions.

The earlier `native-application-start-checkpoint-20260908.json` remains the
sixteen-HELLO baseline over two independent guests and original control-ABI
regressions. Whole-OS production acceptance, full Rust/assembly completion,
multicore McKernel execution, MPI and broader application testing are later
obligations. The current baseline uses one McKernel CPU and 128 MiB inside the
isolated four-vCPU/two-NUMA Linux guest. Do not announce Ultra readiness yet.

## Application readiness and model handoff, 2026-09-08

The user has divided the remaining work into phases. The current active goal
uses Max to establish that the kernel is ready for aggressive application tests.
At that milestone, stop execution after preserving the evidence and verifying
the GitHub checkpoint. The user will switch to Astra Ultra for review and test
planning, then to Codex Spark to implement and run that plan. The older whole-OS
and Rust/assembly requirements below remain future acceptance work; they are
not all prerequisites for ending this narrower execution phase.

Readiness must be demonstrated by real application runs in the established
isolated Linux/McKernel guest environment. Require:

- The unchanged `mcexec` launches an ordinary ELF inside McKernel. Its expected
  output and exit status are observed through the actual launcher. The existing
  hello fixture's expected marker is `NATIVE_APPLICATION_HELLO`, with exit 37.
- Delegated syscalls reach the native WAIT/RET path, execute in the Linux worker
  and return the actual result to the correct guest request. A prepared image,
  successful module build or protocol fixture alone does not satisfy this.
- Normal exit and launcher/worker failure handling retire or safely retain
  their actual owners, without stale response writes or unsafe PID reuse.
  Procfs publication and scheduled-process cleanup must support these runs.
  Any unresolved blocker in these paths keeps the phase active.
- Back-to-back launches in one running OS instance and a fresh guest replay
  reproduce the result without a host/guest panic, unexplained timeout or
  accumulating application registrations. Record the exact repetition counts.
- Small memory, file-I/O, thread/futex and signal smoke checks establish the
  basic execution paths needed by broader application tests. Preserve the
  normal boot and continuing-service regressions for the changed native code.
  These are baseline checks; the later application suite still needs review.
- The handoff binds the tested sources, module/image hashes, exact commands,
  expected and observed outcomes, and all failures. List unsupported features
  and remaining risks explicitly. A known defect that prevents safe application
  testing must be fixed before completing this phase.

At the original phase-definition checkpoint, the real launcher still failed
at START and no application had executed in McKernel. The syscall protocol has eleven passing
tests, with nineteen earlier image/protocol tests also passing, and all three
native modules compile. The native mailbox, response-memory ownership, actual
user WAIT/RET adapters, procfs and scheduled cleanup still need connection.
The immediate implementation sequence remains the scheduled-service review
below. No readiness criterion becomes PASS because of this workflow change.

Astra's subsequent review should examine the implementation and retained
evidence, fix issues it finds, and produce a test plan with bounded cases. Each
case needs its purpose, prerequisites, commands, independent expected behavior,
timeout and cleanup rules, negative cases and required captures. Record the
supported configuration matrix and which results require deeper investigation.
Spark then implements and executes those cases in small verifiable changes.
Preserve failing evidence and investigate kernel defects without weakening an
expected result. Review the resulting tests and failures before any broader
acceptance claim. The user's later model switches remain separate actions.

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

The next actual launcher run passes build-ID and process registration but
PREPARE_IMAGE fails before publication. Both existing launcher producers,
`mcexec.c::flatten_strings` and
`mcexec_helpers.rs::mcexec_flatten_strings_result`, write the total used byte
length into the terminal offset slot. The native `application_image.rs`
validator incorrectly requires zero there. The unchanged guest consumes the
explicit count and string offsets; init-stack construction supplies the actual
argv/envp terminators. Preserve acceptance of the already verified zero-slot
vectors and also accept the exact-length producer encoding, while retaining
all count, offset, maximum-size and NUL-bounds checks. Other terminal values
remain invalid. Reproduce the failure using exact extracted C and Rust producer
bodies, including empty and prefix-combined vectors, before changing validation.
Then repeat the image/protocol suite, module build and real launcher attempt.

## Actual launcher reaches START, 2026-09-08

The unchanged Rust-selected launcher and ordinary static ELF have now been
attempted in the native guest. After the two verified adapter fixes, it passes
the build-ID check, registers its process and receives a real PREPARE ACK.
The guest records one prepared thread with ELF entry 0x40010c. The launcher
advances through image transfer, CLOSE_EXEC and worker initialization to
START_IMAGE, which remains unimplemented and returns EINVAL. The actual
application attempt therefore remains FAIL. Final close receives its distinct
cleanup ACK and exact TID-zero deletion and releases the unscheduled owner.
Only the explicitly separate Linux reference executes the ELF and exits 37.

Both actual launcher builds pass with their existing CMake selections, including
the Rust object/link path and unchanged C fallback. Both metadata interfaces
verify the same authoritative NUL-terminated build ID, eight bounded successful
writes, twenty invalid/readonly/partial-page copyout faults, running/unbooted
states and queries with mcctrl absent. Nineteen protocol/image tests pass:
the original seventeen remain, and two added tests check six exact original
C/Rust producer vectors and terminal-length bounds. The unchanged legacy C
producer uses the actual launcher Debug optimization selection; its earlier
optimized compiler diagnostic and the reproduced decoder failure are retained.

Application-service module 2 also passes the unchanged x86_64 image and i386
baseline regressions. All 47 image assertions and seven physical ready captures
pass, alongside the existing process, credentials, executable and topology
checks. This does not add compatibility image preparation or application
execution coverage.

The retained checkpoint is `native-application-launcher-checkpoint-20260908.json`:
fifteen complete captures, all seven original failures and 41 artifacts. It
binds 49 current native sources, twenty Linux probe inputs, fifteen protocol
inputs, seven launcher source inputs, 226 actual compiler dependencies,
eleven unchanged guest peer files and three exact formatter replays. Each
complete archive preserves all original paths, modes, symlinks and bytes.
The source checkouts separately record their mapped omission of committed
evidence archives; no source code was omitted. Preserve current module 2,
protocol 6 and launcher build 2 with existing image/kernel/setup dependencies.

Next connect the actual START request to its retained prepared owner and supply
syscall wait/return, native procfs and scheduled-process lifecycle services.
Continue all remaining signal, running-VM, fork/exec/exit, compatibility,
fault/race, multi-CPU/OS, shutdown, declared integration/current full suite,
full Rust/assembly and independent acceptance requirements. No formal gate or
whole-OS completion percentage changes at this checkpoint.

## Scheduled application service review, 2026-09-08

Reviewed parent: `50bd446cd27c3dfeb1de4e0a22c7847091423769`. The real launcher
has reached START, but no application has executed. Implement the dependent
syscall service first, then procfs publication and scheduled cleanup before
enabling START. Keep all existing consumers, fallback selections and application
acceptance requirements. This ordering is an implementation sequence, not a
reduction of the application milestone.

Retain the original guest `kernel/rust/syscall_policy.rs` bodies
`syscall_send_prepare_result`, `syscall_request_copy_result`,
`syscall_request_publish_result`, `syscall_packet_traditional_prepare_result`,
`syscall_offload_prepare_result` and `send_syscall`. The configured guest Rust
crate still consumes them through its existing CMake selection. Retain both
unchanged `executer/user` launcher selections. Adapt the host-side
`mcexec_wait_syscall` in `executer/kernel/mcctrl/control.c` and
`mcctrl_control_ret_syscall_body_result` in
`executer/kernel/mcctrl/rust/mcctrl_helpers.rs`: their legacy per-thread hashes,
wait queues, project mapping callbacks and packet allocations cannot be imported
as native Linux owners. Use the existing native Registration and its exact
OS-generation application connection, with a bounded syscall mailbox belonging
to each existing SMP application entry. Do not introduce another PID registry.

The exact pinned Linux 6.12 Rust `sync/condvar.rs` supplies interruptible waits
that release and reacquire a Mutex guard, including a pending-signal result.
Reuse it with Rust Arc/Mutex ownership and UserSlice for copies. Reuse the
current referenced PID wrapper for host worker identity as well as TGID identity;
numeric TID reuse must not take another worker's delivered request. Reserve a
delivery before copyout, commit it only on success, and requeue it on failed
copyout. An interrupted idle waiter must not consume a request. No OS operation,
publication or transport mutex may span an interruptible wait or user copy.

The existing guest request has 72 bytes and is embedded at packet offset 48.
Its response address is at 120; `send_syscall` fills CPU and PID but does not
fill osnum. Bind the OS generation to the receiving continuing owner instead
of requiring a nonexistent wire-generation field. Preserve the original x86_64
wait/return descriptor geometry and independently check it against actual C and
Rust declarations. Compatibility image execution remains separately pending.
Do not infer a syscall result from its number: the unchanged launcher must
execute each delegated userspace operation and return its actual result.

Adapt `executer/kernel/mcctrl/syscall.c::__return_syscall` and
`__notify_syscall_requester`. The common response prefix is 40 bytes; the guest
has an additional Tofu pointer that ordinary host completion must leave intact.
Write result and servicing TID, atomically change requester state from spinning
(0) or descheduled (2) to waking (1), send the actual 0x14 wake packet when
descheduled, and publish response status last. A full outgoing queue must retain
the wake and original response ownership for retry. Never acknowledge completion
before a required wake is published. Reject a second responder rather than
repeating writes to a potentially retired guest stack. Retain exclusive response
spans in the existing guest-memory ledger; reject aliases with queues, metadata,
sysfs snooping and other pending responses. Remove the span only at terminal
publication, after which no host code may touch that response address.

Procfs requires its own real VFS adapter. The pinned kernel has no Rust procfs
wrapper; `include/linux/proc_fs.h` defines proc_ops without a module-owner field,
and `fs/proc/inode.c::proc_entry_rundown` drains callbacks and forcibly invokes
each successful open's release exactly once. Any adapter must retain its module,
callback data, exact-generation guest memory and request buffers through this
rundown, without Runtime/tree/registration reference cycles. Preserve the
existing node tables in `executer/kernel/mcctrl/procfs.c` and guest request/read/
release formats in `kernel/include/syscall.h`. Guest procfs ANSWER precedes final
unmapping, so the existing same-CPU handler barrier requirement also applies to
host request-buffer retirement. `procfs_thread_ctl_result` waits on CREATE;
`mcctrl_procfs_work_main_body_result` publishes entries before that completion.
DELETE is advisory and must never write its expired stack response address.

START must consume only the retained checked prepared thread and its selected
CPU/MM, preserving `mcctrl_control_start_image_body_result` and
`host_schedule_process_request_result` sequencing. Once scheduling is published,
cleanup must use scheduled-process ownership, not the unscheduled thread-pointer
termination path. Keep START unavailable until syscall, procfs and that ownership
transition are connected. Verify the protocol against extracted unchanged guest
Rust producers and existing C declarations, then compile native adapters and run
isolated waiter/copy/lifetime checks before the next real application attempt.
No source retirement, application execution or production acceptance follows
from these prerequisites alone.

## Syscall protocol prerequisite verified, 2026-09-08

The first scheduled-service prerequisite now passes eleven tests using 25
unchanged extracted C/Rust declarations and bodies. The actual original C and
Rust request producers agree byte-for-byte on six vectors, including a targeted
worker. Twelve successful response vectors agree with the original host C
completion; the exact guest Rust wake handler consumes the new wake packet.
The common 40-byte response prefix is checked independently from the guest's
48-byte object, and completion preserves the extra pointer and surrounding
bytes. The decoder preserves the actual wait-copy extent and leaves its unused
trailing PID field alone. Worker and delivery tokens reuse the original
never-reused allocation source; 4,096 concurrent delivery/RPC tokens stay unique.

State tests cover copyout rollback, wrong workers, numeric TID reuse, duplicate
returns, CPU mismatches and targeted requests. The actual completion body passes
256 races with a concurrently descheduling simulated peer. In 1,024 simulated
queue-full failures it retains the original wake and result with status zero,
then publishes status only after send succeeds. This intentionally improves
the original C failure path, which publishes status even if its wake send fails;
successful-path byte equivalence is recorded separately. Repeated completion
does not access a response after simulated peer reuse. These are protocol and
atomic-memory tests, not live IKC capacity, actual user-copy or native worker
lifecycle tests.

The unchanged nineteen image/protocol tests pass again. All three native
modules compile with the new protocol selected, but the native continuing
service does not consume it yet. The new module has not been run in QEMU.
Compared with the last actual guest module, 47 source inputs are unchanged,
two change for shared token allocation and protocol compile selection, and
one is added. Both original launcher and guest implementation remain intact.

`native-application-syscall-checkpoint-20260908.json` retains all four complete
captures in fourteen artifacts, with fifty native source bindings, twelve
syscall test inputs, fifteen existing image/protocol inputs, four unchanged
actual guest source bindings, seven pinned Linux review files and three exact
formatter replays. The first successful capture preserves its generated
unused-import warning; the second removes that import and enforces Rust
warnings. No failed assertion or original evidence was removed.

Next implement the native mailbox in the existing application registration.
Capacity rejection must retain an incoming packet for retry rather than pop
and lose it; outgoing wake retry must keep its exclusive response claim.
Connect referenced Linux worker/MM identity and transactional user copyout,
then real procfs publication/read/release and scheduled process ownership.
The raw response capability is only a protocol view: its constructor requires
the native adapter to retain the exact mapping/module/pages and exclude aliases
through final publication or quarantine. Never treat dropping a view as guest
retirement. Keep native START unavailable until its dependent owners exist.
The latest actual launcher remains FAIL at START_IMAGE, and no application
instruction has executed in McKernel. The full acceptance goal stays active.

## Native syscall ownership refinement, 2026-09-08

Reviewed parent: `b8f990ef395a86e0b5206c41c91c1219da5fab0f`. Retain the exact
guest/launcher consumers and extracted reference bodies identified above.
Adapt the verified `application_syscall.rs::{Response,Completion}` to own a
memory capability and a copied Request so a native mailbox can retain completion
across queue retries without self-referential Rust storage. Preserve the existing
borrowed test adapter and the result/state/wake/status ordering. The owned
capability must keep its exclusive ledger tag on unfinished destruction; only
terminal status publication permits removal, with no later guest-memory access.
Errors quarantine the existing application entry instead of freeing its thread.

Extend `sysfs_memory.rs::Ledger` to exclude live application response spans from
all existing queue, metadata, snooping and prepared-image accesses. Reuse its
checked exact-generation extents, original started resource lifetime and tagged
claim allocation. Use bounded storage and reject aliases before reading shared
response fields. Do not reuse the sysfs Claim destructor, which acknowledges its
own protocol and would fabricate a syscall completion.

Add the mailbox to each existing `smp_application.rs::Entry`; no additional PID
registry is needed. Reuse Delivery and never-reused Worker/Token identities.
Reserve copyout before exposing a request, requeue on copy failure, and keep
Returning until the independent continuing worker publishes the actual wake
and final response. Receive capacity exhaustion retains one packet per channel
in the existing `OwnedControlChannel`, and retries it before popping another.
Only scheduled entries may accept application requests; worker waits can begin
after preparation, before START, as the unchanged launcher requires.

The pinned Linux `sync/condvar.rs` supplies interruptible waits releasing their
Mutex guard. Current `mcctrl_process.rs::ProcessId` and `mcctrl_vm.rs::Mirror`
supply referenced PID and originating-MM ownership to adapt for Linux workers.
The kernel-only application connection carries opaque worker/delivery handles;
existing user WAIT/RET descriptors retain their original layout. No transport,
OS operation or publication lock spans a user copy or interruptible sleep.
The continuing pump's existing nesting is transport, application, then memory;
master channel admission takes transport then memory. Preserve this direction
and release transport before waiting or notifying Linux waiters. Original C
kernel cancellation calls use servicing TID zero, which must be covered by an
additional original-C completion vector if enabled in the common protocol.

The existing launcher's only nonzero RET copy is `act_futex_clock` (and its C
fallback case): offloaded syscall 202, destination in request argument zero,
and a 16-byte timespec. Preserve that actual producer by binding the return
copy to those request fields before the checked guest-memory write. Zero-length
returns retain the general syscall path. User-supplied return addresses alone
must not authorize writes to unrelated guest allocations. An interrupted RET
keeps its accepted result owned by the pump; a kernel-only accepted flag lets
mcctrl clear its private delivery handle while the next WAIT waits for actual
publication. The user descriptor receives no new field.

The first live waiter/image guest passes, but two added source regressions expose
queue ordering and fairness defects in the initial mailbox. Preserve that failed
capture. Adapt the existing mailbox's selection rather than creating another
queue: keep original `mcexec_wait_syscall` targeted priority and pending-list
arrival order, using the already allocated monotonic delivery token across slot
reuse. Rotate completion selection even on full-queue failure. The continuing
pump must carry both the selected application's existing token and CPU through
publication, so one active application or CPU cannot monopolize the scan.


## Native mailbox integration verified, 2026-09-08

The native mailbox and owned response adapter now compile into the actual SMP
module and connect to the original WAIT/RET ioctls. Each existing application
entry owns its bounded requests and Linux workers retain exact referenced PID
and originating-MM identities. Incoming capacity rejection keeps the packet
for retry; outgoing queue pressure retains the result, exclusive memory claim
and wake. Final response publication precedes host-only claim release, with no
later guest-memory access. Failed copies requeue; interrupted accepted returns
remain owned until the continuing pump completes them. Existing targeted
priority is preserved alongside arrival order across slot reuse. Completion
selection rotates across CPU queues and existing applications even after a
full-queue failure.

The final exact-source fixture passes 21 tests, preserving all earlier C/Rust
producer and completion assertions. Both original C stid-zero cancellation
vectors pass. Added FIFO and cross-CPU progress tests first reproduced the two
defects; their failed capture is retained alongside the passing correction.
The initial native compile failure is also retained: pinned VecExt must be
imported explicitly and its allocation failure has no error payload. The
allocation substitute now uses that same trait boundary.

The current module passes the real x86_64 idle-waiter/image guest and existing
i386 interface regression. All 396 waiter assertions pass, including 128
signal interruptions leaving all 11,264 user bytes untouched, 130 idle return
rejections and repeated use of one referenced worker. The original 47 image
assertions still pass, including independent physical content/page-table
checks and unscheduled cleanup. Across both guests there are seven physical
status-3 captures, 306 process assertions, 518 credential comparisons, 1,116
executable/file checks, 2,112 topology queries and 260 continuing sysfs callbacks.
Both guests shut down normally.

`native-application-mailbox-checkpoint-20260908.json` retains eleven complete
captures in 29 artifacts, with 51 native compiler bindings, 13 protocol source
bindings, 25 extracted C/Rust bodies, 17 guest fixtures, six exact module copies,
four unchanged actual guest source bindings, thirteen pinned Linux review
sources and three exact formatter replays. It includes every original failure.

These results do not cover live response claims, successful WAIT copyout or
RET completion from a scheduled application. START remains unavailable while
procfs and scheduled-process retirement are being connected. Worker pruning
currently runs on new worker acquisition; independent dead-worker retirement
is still required. No application has executed, and the Ultra readiness
milestone has not been reached. Next retain the original procfs producers,
node tables and read/release consumers while adapting them to pinned Linux VFS
ownership and the continuing transport, then connect scheduled lifetime and
START before the next unchanged-launcher attempt.

## Procfs VFS ownership adaptation, 2026-09-08

Reviewed parent: `e2ac85e18bcbea898d31f3899755a570a2372bf9`. Retain
`executer/kernel/mcctrl/rust/mcctrl_helpers.rs`'s procfs node, open/read/release
and seek bodies and their existing selection through `executer/kernel/mcctrl/procfs.c`.
Retain guest `kernel/rust/object_helpers.rs::{procfs_thread_ctl_result,
procfs_answer_result,procfs_finish_request_result}` and the existing configured
`kernel/procfs.c` consumer. The original host node tables and credential-based
file ownership remain the publication reference. No existing implementation
or fallback is retired by this step.

Adapt only the missing native VFS boundary first. Pinned Linux 6.12 exposes
`proc_mkdir_mode`, `proc_create_data`, `proc_set_user` and `proc_remove`, but its
Rust bindings lack proc_ops and safe procfs owners. Supply a narrow Rust ABI
view checked against a C object compiled with the exact kernel configuration,
including CONFIG_COMPAT. Reuse Linux's actual procfs implementation and Rust
Arc/Mutex/UserSlice APIs. The new owner must retain callback data until Linux's
`proc_entry_rundown` has finished both active operations and exactly one release
for each successful open. Release may happen during removal while userspace
still holds the fd; no later callback may dereference its retired session.

Use one short namespace lock shared by a root and its descendants. Track owned
names and ancestor liveness, so removing a parent before its descendants cannot
make later old-owner drops remove a replacement with the same name or touch a
freed proc_dir_entry. Reserve fallible name metadata and callback state before
Linux publication. Serialize each open session separately, preserving partial
I/O, independent pread positions, original SET/CUR seek behavior and copy-fault
position rollback. Backend callbacks must never acquire the namespace lock
that removal holds while draining them. No namespace or session lock should
become a Runtime/registration reference cycle.

First validate actual VFS callbacks, failed opens, duplicate names, ancestor
removal/name reuse, concurrent access and removal with active and retained open
files in a disposable guest. This owner alone does not acknowledge CREATE or
provide procfs content. Subsequent integration must supply the exact-generation
remote request/buffer owners, checked guest buffer lists and same-CPU retirement
barrier before releasing any host request page; DELETE never writes resp_pa.
START stays unavailable until those dependent services and scheduled cleanup
are connected.


## Procfs VFS owner verified, 2026-09-08

The new native `procfs_objects.rs` adapter passes its actual Linux guest tests.
Its C and Rust objects agree on all 27 proc_ops/inode/file/credential/configuration
values. The procfs implementation imports the pinned Linux APIs directly and
preserves stable callback payloads through actual `proc_entry_rundown`. Names
are reserved before publication, descendants retain ancestor identities, and
old-owner destruction cannot remove a replacement or touch a freed ancestor.
Backend session acquisition follows all fallible open allocation, ensuring each
successful backend open receives exactly one release. Bounded heap buffers avoid
large kernel stack allocations; user-copy failure preserves file position and
write input is copied before invoking the backend.

Two load/unload cycles in the disposable guest pass 1,024 concurrent writes and
1,024 reads, 32 namespace races with 64 joined workers, four user-copy faults,
two denied opens, overcount rejection, SET/CUR seeks, independent pread positions,
credential ownership and 16,384 bytes of partial reads. Both root-first removals
start with an active read and wait for it to finish (1,150 and 1,118 ms). Each
cycle records exactly 1,039 backend opens, releases and session drops, with zero
live payloads/active callbacks afterward. Duplicated held descriptors correctly
return EIO on read and EINVAL on seek after removal; closing them after module
unload does not call the released session again. The guest finishes both module
unloads and PASS before QMP quit, with QEMU exit zero.

`native-procfs-objects-checkpoint-20260908.json` retains both complete captures
and exact source, binary, layout, Linux and existing project references in eight
artifacts. No original assertion or failure was removed; this batch had no
failures. The VFS owner is tested in a separate module and is not yet connected
to McKernel procfs content or the production SMP module.

Next resolve the peer completion lifetime before connecting those requests.
The unchanged `kernel/procfs.c::_process_procfs_request` calls
`send_procfs_answer` before unmapping its host request/data, freeing its temporary
page and releasing process/thread/VM references. A maps/pagemap lock conflict
can defer the operation through backlog. Receipt of that ANSWER alone therefore
does not authorize native host request-buffer reuse. The prior image fixture's
later same-CPU cleanup ACK is an external barrier observation, not a native
procfs lifetime implementation. Verify backlog execution context before relying
on any queued barrier; consider explicit completion after peer cleanup, with
an identifiable native completion contract, while retaining all existing Rust
consumers and legacy fallback behavior. Preserve the original sources and test
the cleanup/reply order before new images are accepted. No application has
executed and the Ultra readiness milestone remains open.

## Selected Rust procfs completion review, 2026-09-08

Reviewed parent: `aad65b77e97b48bb04ff499ef8bda0d87cc35d0e`. Correction to the
preceding source-selection description: `kernel/rust/procfs.rs` is the actual
native guest implementation. `kernel/rust/lib.rs` selects it, and the x86 Rust
CMake branch removes `kernel/procfs.c` from MCKERNEL_SRCS. The current image's
build.make includes procfs.rs and its compile_commands has no procfs.c input.
All four reviewed selection/procfs/cls files match the retained image-2 sources.
The C file remains the legacy fallback/reference; preserve both selections.

Adapt the existing `procfs.rs::{goto_cleanup,process_procfs_request_inner,
lock_failed,do_procfs_backlog}` directly; no new replacement implementation or
cleanup abstraction is needed. The Rust goto_cleanup sends before unmapping,
like the C fallback. Its maps/pagemap/status deferred branches additionally
call the reply-producing cleanup even when backlog has retained the request.
Its backlog callback returns the processing errno instead of the C callback's
retry flag, potentially asking cls::do_backlog to retry an argument it just
freed. `kernel/rust/cls.rs::do_backlog` releases its queue spinlock before calling
that callback, so receipt of an unrelated same-CPU packet is not a sufficient
standalone proof of deferred-operation retirement.

First reproduce these paths using the complete existing Rust procfs and object
helper sources, the actual ABI, and controlled allocation/mapping/queue/lock
callbacks. Bind the retry expectations to the exact original C callback.
Then retain the existing request cleanup body but separate unmapping/reference
release from terminal reply, use no-reply cleanup while a request is deferred,
and return the actual retry flag. Terminal replies must follow all host-buffer
accesses. Preserve C fallback behavior except for the deliberate stronger
terminal cleanup ordering. The native receiver also needs an identifiable
completion contract before it can free its host request pages; legacy replies
must not silently authorize that retirement. Keep START unavailable until the
complete service and scheduled ownership are connected and tested.

## Native procfs terminal completion contract review, 2026-09-08

The full selected Rust lifetime fixture now passes five regressions, including
no reply during maps/pagemap/status deferral, terminal backlog error without
retry after packet free, and no release of an unacquired process reference on
a missing task. The original C and Rust retry helper returns -EAGAIN, which
cls interprets as nonzero; preserve that exact result. The C fallback also
needs the deliberate missing-task reference correction and terminal ordering.

The existing `kernel/rust/object_helpers.rs::procfs_answer_result` zeroes its
128-byte reply and publishes message 0x13, CPU, argument, errno, reply token
and PID. Its traditional resp_pa at offset 120 is unused for this message.
Both existing host consumers (`executer/kernel/mcctrl/ikc.c::mcctrl_wakeup_cb`
and `rust/mcctrl_helpers.rs::mcctrl_wakeup_cb_result`) read token/error for the
wake operation and do not use resp_pa. Reuse this producer and the existing
native `application_rpc::Exchange` lifecycle; do not introduce a replacement
RPC registry or an unrelated-packet retirement barrier.

For the existing native Linux 6.12 guest selection only, publish the eight
bytes `MCPR0001` in the unused response field after terminal cleanup. Keep
message numbers, packet layouts and the default legacy C/Rust response bytes
unchanged. Extend Exchange with procfs request/release constructors, including
root PID zero, while preserving the stricter positive PID requirement for
application registration. Procfs completion must match the never-reused token,
CPU, PID, request physical address and the explicit native retirement marker.
The queue owner supplies the exact OS generation; the existing answer producer
leaves osnum zero. Legacy/unmarked, stale, duplicate, premature and mismatched
replies must not authorize host-page release. Queue-full retries and abandoned
callers retain their request. This protocol is a prerequisite: production
request-page and peer-buffer owners still need integration and actual guests.

Verify the actual reply producer in both cfg selections against exact original
C packet/layout/body vectors, run the full lifetime cases in both selections,
and test native Exchange rejection and completion directly. Then rebuild all
four actual C fallback/legacy Rust/native Rust/sysfs verification image profiles
with their original selection checks and retain the exact source bindings.

## Selected procfs lifetime prerequisite verified, 2026-09-08

`docs/verification/native-procfs-lifetime-checkpoint-20260908.json` retains
seven complete captures, including the three original failures. The actual
image selects `kernel/rust/procfs.rs` and removes C procfs from its Rust build;
retain/adapt that complete Rust body. Terminal replies now follow all mapping
and process/thread/VM reference retirement. Maps/pagemap/status deferral sends
no reply, the backlog callback returns the original C retry result, and missing
tasks do not release an unacquired process reference. Preserve both C fallback
and Rust selections, including the deliberate C cleanup/ref corrections.

Both guest cfg selections pass nine tests using the complete selected Rust
body and actual answer producer. Six exact C answer vectors preserve every
legacy response byte; native Linux 6.12 replies add MCPR0001 in the otherwise
unused final eight bytes. Native Exchange requires that marker and matching
token/CPU/PID/request address before completion. Root procfs permits PID zero;
application registrations still require positive PIDs. Nine C backlog vectors,
12,288 queue-full observations per profile, and the existing 19 image/protocol
and 21 mailbox regressions pass. Eighteen compiler bindings and original actual
image sources are retained. The native exchange tests do not supply real
request-page owners or integrate the procfs service.

Next rebuild all four guest image selections and three native modules, then
connect and guest-test the actual procfs service and scheduled cleanup before
START. The new image helper records exact Git blob restoration references
before omitting historical evidence from compile-only source copies. No new
image/module build or application execution is claimed by this checkpoint.
Host/scratch have about 136/38 GiB free. Preserve all failed/current captures
and current build/image inputs; continue periodic GitHub checkpoints. Explicitly
tell the user "We're ready to switch to Astra Ultra" only after the documented
application baseline passes, then stop for the user's model switch.

## Rebuilt procfs images and actual guests verified, 2026-09-08

`docs/verification/native-procfs-images-checkpoint-20260908.json` retains the
four rebuilt guest images, native module attempts 4 (original dead-code warning
failure) and 5 (PASS), final procfs lifetime fixture 6, and both real guests.
C fallback, legacy Rust, native Rust and sysfs verification image selection,
producer/configuration/ELF/linked-ownership checks pass. Source review and exact
compiler inputs prove procfs.rs is the selected Rust implementation. The native
Exchange::procfs constructor has one documented dead-code allowance while its
real service remains unconnected; request/release constants are local. All
other module warnings remain denied. Remove that allowance when connecting it.

Both guest ABIs reach physical McKernel status 3 and power off normally.
x86_64 retains 396 idle syscall-wait assertions and 47 image/memory assertions;
together the guests retain 306 process, 518 credential, 1,116 executable and
2,112 topology checks, plus 260 continuing sysfs callbacks. All original
assertions remain unchanged. Final procfs fixture source again passes nine
tests per cfg profile. Fifty-one native sources, eighteen fixture inputs,
seventeen guest probes, six module copies and both actual image copies are
bound to retained bytes. Three existing formatter differences are reproduced
with the pinned compiler's formatter. The complete image capture includes an
exact Git blob restoration map for 1,315 omitted historical evidence files
(4,156,777,159 bytes), avoiding their duplication in a compile-only checkout.

No live procfs request/release service or application instruction was exercised.
Next connect the verified VFS owner and terminal exchange to actual procfs nodes,
request-page/peer-buffer ownership, CREATE completion and advisory DELETE.
Then finish independent dead-worker reaping, scheduled cleanup and START, and
run the documented real application baseline before the Astra Ultra handoff.
The old broad-equivalence harness still lacks its recorded historical IHK
sources; do not claim that suite passed. Preserve current module attempt 5,
both procfs-image guests, procfs-image build 1 and fixture 6, plus all previous
active dependencies and original failure archives. Continue GitHub checkpoints
and audited storage maintenance; no formal gate or score is promoted.


## Live native procfs connection review, 2026-09-08

Reviewed parent: `04d80a3a0086cfe2b417a4e6f6840673a6727a35`. Previous turn
made verified progress: the lifetime fix, all four images and both actual guest
regressions are pushed. Continue with real procfs integration, not another
replacement guest implementation. Retain the full selected guest procfs.rs,
object_helpers.rs and original host node/open/read/release/seek bodies. Reuse
procfs_objects.rs and application_rpc::Exchange directly. The native service
will live alongside the existing continuing service and use its independent
packet/metadata workers; no second application PID registry is introduced.

Each existing prepared application entry will retain its procfs process owner.
Its CPU and raw kernel UID/GID come from the trusted prepared-image input:
mcctrl overwrites PID and all eight credential scalars before its kernel-only
PREPARE call. The old host credential lookup uses a borrowed task after RCU;
that legacy pointer cannot become a native owner. Snapshot uid/gid scalars from
the retained preparation and keep the existing referenced registration identity.
Root stat/mckernel and the original PID/TID node tables remain the interface.
Guest CREATE 0x44 waits for real publication; DELETE 0x45 is advisory and never
writes its expired resp_pa. Attach per-process VFS ownership to the existing
entry before scheduling. Drain/removal must run outside the application and
transport mutexes, and callbacks must never reacquire their namespace lock.

Use a bounded per-open remote table with original Linux BootPages for each
808-byte request and direct-I/O page. Reserving an open reserves its later
release capacity too. Queued/published requests outlive interrupted calls and
fd removal; the packet worker must retain and complete them independently.
Only the exact native MCPR0001 answer can permit request-page reuse. Snapshot
reads retain the guest's real linked buffer pages, validating complete page
ranges, header sizes, monotonic positions and repeated-page/alias rejection.
Extend the same Memory ledger that excludes queues, sysfs and syscall responses
for CREATE's four-byte completion and retained buffer pages. Release publication
must retire host read claims atomically under that ledger: queue-full leaves
claims intact, and successful publication permits no later host buffer access.
The request page itself remains held until the terminal release answer.

Keep Runtime/tree/file/registration ownership acyclic. File callback payloads
retain the independent remote service and a process-liveness identity, never
Runtime or the application registry. Started BootStorage already irreversibly
retains the exact guest RAM/module owners. Preserve that prerequisite through
all pending operations and quarantine uncertain retirement rather than freeing
published storage. Linux rundown may call release with fds still open; remote
release must not require the namespace or metadata worker to make progress.

Connect the actual SMP build and pump, then verify real procfs reads/releases,
partial I/O, copy faults, repeated opens, aliases and completion ownership in
the fixed guest environment. Follow with scheduled-process cleanup, independent
dead-worker reaping, START and the unchanged launcher baseline. These additions
are implementation work toward the existing readiness criteria; no procfs or
application acceptance follows from compiling an unused protocol constructor.

## Live root procfs service verified, 2026-09-08

The native SMP production crate now selects procfs_objects.rs and the live
smp_procfs.rs service. It reuses the original selected guest procfs body and
traditional Exchange, with MCPR0001 required for terminal retirement. Each open
reserves one of 64 slots and its Linux request/data owners; snapshot reads keep
checked guest buffer chains (at most 1,024 pages per open) until release. Shared
Memory claims exclude queue/sysfs/syscall/CREATE aliases. Successful release
publication retires read claims under that same ledger before guest reuse;
queue-full preserves them. Interrupted or closed callers cannot free pending
request pages. Unknown retirement quarantines storage. Metadata overflow fails
and retains started ownership without acknowledging CREATE or blocking later
answers needed by namespace rundown.

Each existing application Entry now retains its procfs identity, trusted UID/GID
and prepared CPU. PID/TID node publication, real CREATE completion and advisory
DELETE are compiled into the continuing service. Callback payloads retain the
independent remote owner, never the application registry or namespace. Process
close schedules namespace rundown on the metadata worker, while the packet
worker drains replies and release requests. START and scheduled cleanup remain
unavailable; these process paths are not yet runtime-proven.

Native module attempt 3 and x86_64 guest attempt 2 pass. The actual root files
return cpu0 and the guest version through 194 real snapshot requests and 194
terminal releases. The guest verifies 64-open capacity/exhaustion/recovery,
128 repeated opens, copy-fault position preservation, partial I/O, pread/seek,
and duplicate-fd shared position. All 388 answers have distinct exchange tokens,
zero errno and no quarantine; checked page counts fall from one to zero on each
release. Both physical boot captures, prepared-image/memory proof, unscheduled
cleanup evidence and the original idle-wait/process/credential/file/sysfs checks
pass. QEMU exits 0 after normal guest poweroff.

Original module failures 1-2 and guest failure 1 remain retained. The first guest
passed its Linux probes but its host verifier expected the old absolute packet
totals. The corrected verifier first proves all 388 added procfs exchanges, then
requires exact total counts (464,465) and the unchanged application remainder
(76,77); prepared-image remainder stays 74, later cleanup stays (2,3), and the
original physical TID-zero deletion proof remains present. No assertion is
removed or relaxed. Full evidence is indexed by
native-procfs-service-checkpoint-20260908.json; the earlier source/module WIP
checkpoint was pushed and independently verified as 379f6423.

This is live root procfs evidence, not full procfs or application acceptance.
Remaining coverage includes PID/TID CREATE/DELETE, direct mem/pagemap I/O,
interrupted live procfs operations and malformed/alias requests. Finish scheduled
cleanup and independent dead-worker reaping, connect START and test the unchanged
launcher, then prove those paths alongside the documented application smoke
baseline. No McKernel application instruction has executed. Preserve every
current/failed capture and continue periodic verified GitHub checkpoints.

## Independent worker and process reaping review, 2026-09-08

Reviewed parent: 0f6b8791ebf054e3f0485fb5a0b6ab3186178094. The previous
turn made verified progress: live root procfs is connected, guest-tested and
pushed. Continue toward real startup with actual Linux lifecycle ownership.

Retain/adapt mcctrl_process.rs::Registration::worker's existing referenced PID
pruning body and the single Process/Binding registry. Its current pruning runs
only during a new worker acquisition, so the final dead worker's response can
remain stranded. Use a joined mcctrl-owned kthread to scan bounded snapshots of
that same registry independently. Clone process/registration references under
short publication locks, then invoke existing WORKER_CLOSE outside the registry
lock. EBUSY retains the PID/MM and retries after the independent SMP packet pump
publishes cancellation. Preserve smp_application_syscall::Mailbox::close_worker,
cancel_call and publish sequencing and their actual response owners; no new
worker or application registry is needed.

Use the existing ProcessId get_pid_task/put_task_struct pair with PIDTYPE_PID
for workers and PIDTYPE_TGID for the process. A missing referenced TGID permits
removing its registration/executable from a process kept alive only by inherited
file bindings. Drop those owners outside all publication locks. MappingFile and
in-flight operations still retain Registration independently; never force its
cleanup while a Linux mirror VMA still owns guest PFNs. Registry destruction
must stop/join the reaper before releasing its table/module code. Task creation
and failed-publication rollback must release the never-entered callback exactly
once. Verify real worker departure without any new acquisition, slot reuse and
inherited-binding retirement in the isolated guest.

Selected guest host_helpers.rs::host_cleanup_process_request_result deliberately
sends the ordinary ACK before terminate_host. Scheduled cleanup must pass a null
thread argument, since the prepared pointer can be freed after SCHEDULE. The
original process_release_thread_body_result sends advisory DELETE before VM and
process destruction; process_release_process_body_result detaches its PID hash
only on the final reference. Neither ACK nor DELETE alone proves scheduled
retirement. Preserve these existing Rust bodies and C fallback while reviewing
an explicit final-retirement contract; do not enable START based on the old
unscheduled cleanup flag. Also retain the unchanged mcexec exit path, which does
not return its exit syscall and relies on final Linux-owner release. Worker
cancellation must drain its actual response before guest cleanup is requested.

## Independent worker and process reaping verified, 2026-09-08

The exact checkpoint is `native-application-reaper-checkpoint-20260908.json`.
All three native modules compile with warnings enforced. Actual x86_64 guest
attempt 5 proves 72 Linux workers retire independently after interrupted WAIT
and thread exit: 72 distinct handles, 72 quiet windows without any new
application acquisition, and all 6,336 result bytes unchanged. Four reaped
TGIDs release their registrations with cleanup_errno=0 while the inherited
mcos file remains open, again before any new application acquisition.

The existing 194 root procfs snapshots and 194 terminal releases, 396 idle
WAIT assertions, physical boot/image/unscheduled-cleanup and process, executable,
credential, file, topology and continuing sysfs regressions pass. The guest
powers off normally and QEMU exits 0. Worker attempt 3 also passes. Original
attempts 1/2 failed strict evidence ordering because printk split serial
markers; attempt 4 failed compiler command construction before guest startup.
All three full original failures remain archived. The correction puts verifier
markers in /dev/kmsg and selects compiler output by the explicit -o argument;
no interval, identity or original regression assertion is removed.

Six full captures and sixteen artifacts retain exact helpers, modules, guest
roots, commands, probes, serial logs and physical evidence. All 53 native
compiler bindings, 13 current probe inputs, three module-to-guest copies and
three pinned formatter replays verify. There is no scheduled cleanup or live
syscall-delivery claim; no McKernel application has executed. Continue the
explicit scheduled-retirement contract and START, then all documented baseline
runs before announcing the Astra Ultra handoff.

## Scheduled retirement and START implementation review, 2026-09-08

Reviewed parent: 06976ff31b23cc2a3f885539cbf55feede724cd5, fetched from
GitHub and compared against 94 exact source/evidence blobs. Previous goal turn
made progress: independent Linux worker/TGID retirement is now guest-proven.

Retain the selected guest Rust host_helpers::host_cleanup_process_request_result
and its ordinary ACK-before-terminate ordering, process_helpers final-reference
PID-hash detachment, procfs advisory DELETE producers and all C fallback bodies.
Add a native-Linux-6.12-only read-only retirement query to the existing cleanup
handler: request CLEANUP/arg=0/resp_pa=MCRQ0001, response CLEANUP_REPLY with
MCRE0001 plus exact PID, OS, CPU and token. The bridge validates its current
resource set and process hash before using existing find_process/process_unlock;
missing configuration is an error, not proof of absence. A present PID gives
EAGAIN. No process reference or peer pointer escapes the lookup lock. Ordinary
legacy cleanup packet bytes and behavior remain unchanged.

Adapt the existing native Exchange and Entry owners, rather than introducing
another guest PID registry or Process ABI field. Only after the original
cleanup ACK may an independently pumped, uniquely tokened query be sent. A
matching zero answer is required alongside all recorded TID deletions and
retired syscall/procfs/mirror owners. PID hash absence occurs on the final
process reference; its remaining guest-only destruction does not borrow host
application pages after the other gates drain. DELETE alone and unrelated
same-CPU packets are not retirement proof. EAGAIN retries are rate bounded;
malformed, stale and unmarked answers cannot retire the Entry. Unknown or
incomplete state retains the bounded registration and excludes PID reuse.

Keep a bounded TID ledger on the existing ProcfsProcess, independently of
namespace nodes. Closing the namespace must preserve those identities until
DELETE. CREATE racing with close must still finish real publication and ACK,
then remove the closed namespace; callbacks refuse new opens. Duplicate
CREATE/DELETE must not alter the count twice. Close both syscall admission and
procfs before waiting for either to drain, so namespace rundown cannot prevent
worker cancellation. Validate event CPU against the actual OS topology; threads
may use a different CPU from the original prepare target.

Adapt the unchanged MCEXEC_UP_START_IMAGE path through mcctrl's existing
Registration operation serializer and referenced mirror MM. Copy the actual
user header and compare its identity/target to the retained prepare output;
only the retained guest thread pointer may enter SCHEDULE. Queue publication
and the transition to scheduled share the existing Entry mutex. Unpublished
schedule work may cancel into ordinary unscheduled cleanup; once published,
cleanup always uses arg=0 and the explicit scheduled retirement gates. Keep
mcexec unchanged. Verify exact wire/negative cases and source selection, compile
native modules and fallback/Rust/native images, preserve original regressions,
then attempt the actual hello/exit-37 launcher baseline. No application or
handoff claim is made by this design or compilation alone.

## Final-binding/reaper race review, 2026-09-08

Actual current i386 regression 1 fails immediate CREATE_PPD after final close
(PID 286, check 11, expected 0, actual EINVAL); the old registration's cleanup
ACK/release appears afterwards. The earlier x86_64 application is independently
PASS, but this regression blocks accepting the current baseline. Preserve the
original assertion and failure. Do not insert a retry or delay into the probe.

Review mcctrl_process::Binding::drop and the new joined reaper against the
existing Process/Registration owners. A reaper snapshot Arc<Process>, and its
temporary Arc<Registration> clone, can defer final registration destruction
past close even with no VMA or active ioctl. Adapt final Binding removal to
detach the process's executable and registration explicitly outside the global
table lock. Borrow the registration under its short process mutex while the
reaper invokes nonblocking WORKER_CLOSE, rather than cloning an observational
Arc. Thus final close waits for that observation before taking/dropping its
owner. The reaper still uses the same registry and referenced PID and still
retries EBUSY independently; its snapshot alone cannot delay registration
retirement. Real VMA/in-flight Arc owners must continue retaining Registration.
Reuse the same detach operation for a truly dead TGID. Never free guest pages
or bypass a real remaining owner just to satisfy immediate reopen. Compile and
rerun the failing original i386 regression, then current x86_64 and real
application runs with the corrected module.

## Native RET routing adaptation review, 2026-09-08

Repeated application attempt 1 delivers write on McKernel CPU 0, prints its
25 bytes, then the launcher reports RET EINVAL; dead-worker cancellation
subsequently returns -512 in the independent guest kmsg. This is a blocking
failure. The original capture remains FAIL, including its emergency physical
snapshot. The first module-3 application PASS is retained separately.

Selected existing Rust producers `executer/user/rust/mcexec_helpers.rs`:
`act_main_loop_iteration` passes `my_thread.cpu` into `act_main_loop_syscall`
and `do_syscall_return`. It stores the guest `w.cpu` separately in remote_cpu.
C fallback `executer/user/mcexec.c::main_loop` has the same semantics; thread
creation assigns increasing worker slots and creates n_threads + 1 workers.
Consequently even -t 1 can return from Linux worker slot 1 for guest CPU 0.
Both RET descriptor producers initialize all five fields.

Retain both launcher selections unchanged. Reuse the ownership contract of
`executer/kernel/mcctrl/rust/mcctrl_helpers.rs::mcctrl_control_ret_syscall_body_result`
(selected by MCCTRL_RUST_HELPERS outside CONFIG_MIC), and its control.c
fallback: look up the current task's retained packet and complete that packet;
neither uses ret_desc.cpu to choose or validate the guest request. The existing
C `syscall.c::__return_syscall` also derives response ownership from the packet.
Its Linux 4.x/C-bridge registry cannot be directly called by the Linux 6.12
native module; the existing referenced HostWorker/MM and private serial remain
the native equivalents.

Adapt native `mcctrl_process::Registration::{wait_syscall,return_syscall}` to
retain the trusted guest CPU alongside the delivered serial in HostWorker.
Store CPU before publishing the nonzero serial with Release, and load CPU only
after acquiring that serial. Only the referenced current Linux TID can issue
those synchronous ioctls; a reaper cannot reuse a live identity. Build the
internal RETURN message using this retained CPU, with the actual user result,
validated bounded copy and existing worker/serial. Keep the backend's wrong-CPU,
wrong-worker, stale serial and duplicate completion checks unchanged. Bound a
route diagnostic to the existing trace budget when launcher and guest CPU
differ, allowing the fresh unchanged-launcher run to prove this case directly.
Test the actual extracted adapter methods for distinct worker/guest values,
copy failures and acceptance/interrupt ownership before fresh module/runtime
checks. No guest code, wire ABI, old test assertion or launcher workaround is
needed for this adaptation.

## Native pathname-copy adaptation review, 2026-09-08

Retain the selected existing Rust `executer/user/rust/mcexec_helpers.rs::
do_strncpy_from_user` and its C fallback unchanged. File path dispatch uses
MCEXEC_UP_STRNCPY_FROM_USER (0x30a02908), with pointer/pointer/unsigned-long/long
fields in `executer/include/uprotocol.h::strncpy_from_user_desc`.

Adapt the selected Rust `executer/kernel/mcctrl/rust/mcctrl_helpers.rs::
mcctrl_control_strncpy_from_user_body_result`, called by control.c whenever
MCCTRL_RUST_HELPERS is selected. Its chunked copying body preserves source and
destination, stops at the first NUL, copies the terminator, returns count
excluding NUL (or n if none is found), and reports data-copy faults through
`desc.result` with ioctl return 0. Descriptor faults return EFAULT and buffer
allocation failure returns ENOMEM. The C fallback preserves those public
semantics; its unchecked pointer arithmetic is not copied into native Rust.

Reuse native `user_string::read_into`, already consumed by executable/image
path reads, and pinned Linux 6.12 `rust/kernel/uaccess.rs::UserSlice` readers and
writers. Reuse one initialized 4-KiB heap buffer and the existing Vec allocation
API. Retain bounded chunking with no arbitrary pathname-length cap; checked
address advancement prevents wrapping. No kernel/user copy or allocator bridge
is required. The old Rust function's C callback types and page allocator cannot
serve the native Linux crate directly, so adapt its sequencing in user_string.

As in the original body (which ignores os), this operation accesses only the
current Linux task's userspace, with no registration or guest-pointer shortcut.
Any mirror fault still uses the existing VMA's referenced MM/Registration
checks. Do not hold an application/registry lock across user copying. Decode
and preserve the original four fields for LP64 and i386; write only the result
field within the copied descriptor and return descriptor-copy faults normally.

Verify page boundaries, zero length, embedded NUL, multi-page strings, no
terminator within n, invalid source/destination/descriptor pointers, partial
copy faults and descriptor guards through both actual Linux ioctl ABIs. Then
run real application file operations through unchanged mcexec. Keep the prior
launch/cleanup baseline and all failure captures. This is missing integration
for the readiness smoke checks, not a new launcher or reduced test contract.

Build-selection refinement: user_string is shared with the SMP image loader,
which correctly rejects the unused mcctrl-only ioctl adapter under -D warnings.
Keep user_string::read_into unchanged and place the new current-caller copy
adapter in mcctrl_exec, reusing its initialized path_buffer allocation. This
retains both existing consumers and introduces no dead-code allowance.

## Native file-pager source review, 2026-09-08

Reviewed parent: 4b067ed93077e433fe6f4c9bdde31a786bf2b696. Original
`native-application-core-memory-guest-20260908-1` remains FAIL. PID 307 opens
libc as fd 6, reads 832 bytes, preads 784 bytes, completes fstat and a second
pread, then receives -38 on syscall 9. The independently captured McKernel
log identifies `fileobj_create(6)` / PAGER_REQ_CREATE. Its loader prints the
shared-object mapping failure, exits 127 and completes marked retirement.
The application does not reach its memory checks. Diagnostic evidence and
source identities are recorded in `native-application-pager-review-20260908.json`;
the complete original guest capture remains protected pending full archival.

Retain `kernel/rust/fileobj.rs::{fileobj_create,fileobj_do_pageio,fileobj_free}`
and its CREATE/READ/WRITE/RELEASE request producers. Kernel CMake selects
this Rust module through rust/lib.rs and removes fileobj.c in the Rust build;
the C fallback remains a reference and a supported build selection. Retain
`kernel/rust/abi.rs::PagerCreateResult`: size 4128, handle at 0, maxprot at 8,
flags at 12, size at 16, pgshift at 24 and the 4096-byte path at 28, with final
alignment padding. Keep the existing result and request ABI unchanged.

Retain the selected launcher `act_reserved_memory_syscall` unchanged. Its
ENOSYS is deliberate: the existing host handles reserved mmap/munmap/mprotect
requests before userspace dispatch. Adapt the existing Rust
`mcctrl_in_kernel_irq_syscall_body_result`,
`mcctrl_in_kernel_syscall_body_result` and
`mcctrl_pager_call{,_irq}_body_result` dispatch semantics. Compatibility CMake
links mcctrl_helpers.o under MCCTRL_RUST_HELPERS; these bodies call C callback
tables and legacy OS/packet pointers, so they cannot be directly linked into
the native ownership graph. `syscall.c::pager_req_*` supplies the actual Linux
file-I/O and registry bodies behind those callbacks; it is not already a
native Rust pager. Preserve all compatibility consumers.

The source contract requires more than acknowledging CREATE. The file pager
shares handles by retained inode, increments a server reference for each
CREATE, retains read/write Linux file references independently of fd close,
and releases the accumulated guest sref on final file-object destruction.
READ repeats short reads and zero-fills the final partial page; WRITE is
bounded by the existing file size. Permissions, noexec mounts, file type,
tmpfs/procfs/device handling and huge-page selection must remain explicit.
Guest `kernel/rust/pager.rs` implements swap/page-in/page-out and mlock-list
requests; it does not replace the Linux file-pager backend.

The pinned Linux 6.12 rust/kernel/lib.rs exposes no fs/file module or File
owner abstraction. Its generated bindings already expose ordinary Linux
fget/fput, kernel_read/kernel_write and vfs_getattr. Use those reviewed exports
behind a Rust file owner, retaining Linux's permission checks and positional
I/O. The existing native mcctrl_exec::Executable demonstrates balanced fput
and bounded d_path, but its execute-only opening and write denial cannot own
arbitrary mapped files. Do not use whole-image smp_loader loading for paging.

Native integration must retain the exact reserved Request, worker and serial
while handling CREATE/READ/WRITE in the calling Linux worker's sleepable
context; fd lookup needs that caller's file table. Keep file-I/O outside the
application state and memory-ledger locks. Reuse the existing OS generation,
started storage, mailbox completion/wake ordering and memory span validation.
Add a distinct internal pager operation and request-authorized data path;
keep the userspace RET copy contract restricted to its existing 16-byte futex
case. Never authorize arbitrary physical writes through the public RET ioctl.

RELEASE cannot depend on a surviving Linux launcher worker: the existing
in-kernel IRQ path handles it before userspace dispatch, including during
guest teardown. Its native equivalent must run through continuing service,
retain the response until completion, and validate handles and sref without
underflow or reuse. Per-OS sharing, cancellation during I/O, unpublished CREATE
rollback, late RELEASE and independently referenced files must have explicit
ownership before source changes are accepted. Close or PID deletion alone
cannot free shared pagers or permit stale writes.

Next implement that bounded integration and test exact ABI/dispatch, sharing,
close-after-mmap, partial/EOF I/O, invalid handles/spans, cancellation and
teardown. Then rebuild the native modules and rerun the unchanged dynamic
application in a fresh guest. Original failure evidence stays FAIL. Passing
Linux reference modes, a source review or a compile cannot promote the handoff.

Implementation ownership refinement: the native OS Remote will own the shared
file registry and a separately pumped RELEASE mailbox with a never-reused
internal token. Route RELEASE before numeric process lookup, because final VM
file-object destruction can occur after the original PID/TID retirement gates;
a shared file object may also release CREATE references from multiple processes.
This queue borrows no dead launcher or MM and uses the original response/wake
protocol. Active file I/O reserves the existing mailbox delivery, defers close
cancellation until I/O ends, and retains an exclusive payload tag on the same
SyscallResponse through publication. Chunk copies validate the retained tag
under the application's short lock; filesystem calls hold neither that lock
nor the shared memory ledger. CREATE commits its inode handle/reference only
when the authorized result copy succeeds and cancellation has not won. Public
RET and ordinary mailbox behavior remain unchanged. Add exact protocol tests
for deferred cancellation and service completion before native compilation.

## File-pager runtime findings and next service review, 2026-09-08

Native pager protocol 2 passes all 26 cases, module 1 passes all three native
builds/imports/no-SIMD checks, and the four file-mode masks match separately
compiled definitions from the pinned Linux fs.h. Guest 1 passes the prior
pathname and eight-HELLO setup, loads libc and reaches memory operations, but
remains FAIL on continuing-service EINVAL. Its emergency port-503 receive ring
retains the original 128-byte packet at byte 6080: message 4, CPU 0, PID 307,
requester/target 0, valid 1, syscall 279, node argument 0xfffffffffe910040 and
response physical address 0. This is a legitimate one-way allocator request.
Preserve Request::decode's strict requester/response checks for ordinary calls.

Retain the selected `kernel/rust/page_alloc.rs` producer
`__ihk_numa_zero_request_packet_fill`, worker increment and deferred-free list
publication. Its node pointer and intrusive list links are guest virtual
addresses; they are not Linux pointers. The selected old host Rust
`mcctrl_zero_mckernel_pages_{step,finish}_result` pops a free chunk, zeroes all
bytes after its 48-byte metadata, publishes the chunk to zeroed_list, subtracts
its pages from nr_to_zero_pages and finally decrements zeroing_workers. Legacy
Linux/C mappings supplied its pointer interpretation. Adapt the sequencing
with exact current-OS mapping and atomic list ownership, without calling the
old pointer body on unvalidated guest values. Bind the guest's exact node and
FreeChunk layouts, kernel-address translation and original publication order
before implementation. This work must be handled by continuing service with
no synthetic syscall response or requirement for a surviving application PID.

The same guest reaches ordinary munmap, whose selected Rust
`clear_host_pte_body_result` forwards syscall 11 before freeing/reusing pages.
The legacy host's in-kernel Rust dispatcher calls its PTE-clearing adapter;
the native path still sends it to the launcher's reserved-memory ENOSYS body.
The guest logs that error while its public munmap returns 0, so application
exit/output alone cannot establish safe invalidation. Reuse the existing
native `mcctrl_vm::Mirror::clear` with its referenced current MM, complete
range preflight and exact mirror-file check. Route the retained syscall's
range through a native kernel service and actual completion, keeping syscall
ownership alive through invalidation. Review mprotect synchronization as well;
do not weaken the VM callbacks or accept arbitrary userspace ranges.

Actual file RELEASE, zeroing completion, host invalidation and full libc/core
exit remain unverified. The original guest failure and its emergency physical
state stay protected, along with the original failed protocol attempt. Full
capture archives are still pending at this WIP. Next fix the newly reached
services, rerun the unchanged app in a fresh guest, then preserve original
regressions and finish all remaining handoff requirements.

## Retained host invalidation and zero-list ownership review, 2026-09-09

Continue from clean `24a7a41cc146bffa9be60944c9178ae148305c99`. The intervening
status turn also reviewed the selected guest address conversion and list
consumers. Preserve `clear_host_pte_body_result` and its selected C bridge:
the retained syscall 11 carries an address and length, with the guest's pending
free sequence delaying reuse until the offload returns. Adapt the legacy
`mcctrl_clear_pte_range_body_result` integration by reusing native
`mcctrl_vm::Mirror::clear` unchanged. Its current-MM check, two-pass exact VMA
preflight and Linux `zap_vma_ptes` already supply the required side effect.
No generic Linux VMA mutation or userspace-supplied service handle is needed.

Add kernel-only begin/finish commands around that existing operation. Begin
uses the exact reserved worker and delivery in `smp_application_syscall`,
validates syscall 11 and checked page geometry, then reuses `begin_kernel`.
The calling mcctrl worker retains its original PID, Mirror and Registration
while clearing the returned range, outside application/transport locks.
Finish reuses `finish_kernel` and the original response/wake publication;
cancellation must retain response ownership until the MM operation has ended.
Both commands reject another syscall kind, stale delivery or wrong worker.
Only the actual clear result is completed; a failed begin rolls the untouched
WAIT reservation back, and interruption after completion acceptance does not
re-execute the clear. Existing public RET and WAIT user layouts stay unchanged.

The protection review also finds that selected
`syscall_policy::set_host_vma_body_result` currently returns zero without host
invalidation. The C bridge returns through it before the historical mprotect
offload. Keeping a host VMA writable was deliberate for the legacy fabric
path, but stale writable host PTEs must still be invalidated after guest
protection changes. This remains required native guest integration and cannot
be accepted merely because the memory smoke returns success. Keep the actual
Mirror callbacks' protection checks intact.

For the native Linux-6.12 guest selection, adapt that existing Rust no-op to
call `clear_host_pte_body_result` with the current Thread/ProcessVm, the exact
`is_memory_range_lock_taken` offset, and the existing
`syscall_policy_do_syscall3_bridge`. This reuses nr 11 and propagates its actual
result without adding a C body or Linux mprotect request. Preserve the legacy
Rust/C no-op selection. Native permission-change detection must cover read,
write and execute bits, including read-to-none; invalidate after partial guest
range changes even if a later range fails, preserving the first error. Compare
the unchanged legacy behavior with its exact C body, and test the native
forwarded arguments, lock flag restoration, errors and partial-range case.

For zeroing, `page_alloc::IhkMcNumaNode` is 256 bytes/aligned 64; worker count,
pending-page count, zeroed head and pending head are at 40, 44, 48 and 56.
FreeChunk is 48 bytes, with its list link at 40. The selected address converter
maps the kernel window through the retained BootLayout physical base, and
post-initialization free chunks through the supplied Linux direct-map base.
Both translations must still validate the complete span against the same OS.
The guest also consumes pending zero chunks in its low-memory allocation path.
The pinned Linux `include/linux/llist.h` explicitly requires serialization
when any consumer uses del_first alongside another consumer; replacing only
the host pop with del_all does not remove that ABA risk. Resolve ownership
across both selected consumers before wiring the zeroing side effect. Do not
cast guest pointers to Linux objects, suppress the packet or relax the ordinary
response-bearing decoder. Original captures stay protected and failed.

The zeroing review must also cover `syscall_policy`'s offload-poll loop and
the timer bridge, which call `ihk_numa_zero_free_pages` outside the allocator's
MCS lock. Native host/guest pop ownership therefore cannot assume that lock
serializes all consumers. Any shared critical section must account for guest
interrupt reentry and avoid Linux blocking operations while the guest waits.
The original image's `memory_nodes` symbol is exactly
`0xfffffffffe910040`, matching the captured node argument. `kernel/mem.c`
owns its static BSS array of 512 nodes; `mem_helpers::MemNumaNode` explicitly
represents the four bytes of padding at offset 12 as `_pad0`. Review its
selected initializer and all field accesses before using any layout space for
coordination. Keep node/chunk bounds, atomic publication and worker/page counts
in the protocol checks, and require the selected guest and host to agree on any
new synchronization contract before handling the one-way request.

## Native zeroing batch integration review, 2026-09-09

Start from verified `f0181f89d9e63e4a16a5dfb90545dfd5cb8f1a52`; the previous
goal turn made implementation/verification progress on host invalidation and
guest protection, with all failures retained. For zeroing, use atomic batch
detachment on every native pending-list consumer. Reuse the sequencing of
`kernel/rust/llist.rs::llist_del_all` (atomic exchange with zero) and its batch
publication operation. This is the multiple-consumer combination explicitly
supported by the pinned Linux list contract. Native allocator, timer and
offload-poll calls all enter `__ihk_numa_zero_free_pages_node`; adapt its native
selection to detached batches, preserving first-sufficient-chunk selection and
returning unused chunks. Keep legacy Rust/C behavior and current exports.
Capture page counts before publishing zeroed chunks, because another consumer
may immediately reuse their metadata. No shared spinlock or node layout change
is needed. Add a native-only marker in the unused second one-way argument so
the host cannot consume an old guest's del_first list under the new contract.

Adapt `mcctrl_zero_mckernel_pages_{step,finish}_result` using bounded OS-owned
views: retain the actual boot layout for kernel-window node translation;
translate post-initialization free-chunk links through the supplied direct-map
base, then validate complete ranges against the same assigned OS extents.
Claim the node's four control fields and all detached chunk spans in the
existing continuing-service ledger before clearing or publishing any chunk.
Reject overlap, cycles, wrong physical headers and invalid sizes. Preserve each
48-byte header, publish zeroed chunks atomically, subtract their retained page
counts and finish exactly one worker request. On malformed work retain claims
and started owners, record the service failure and never synthesize a response.

Run zeroing on a third retained continuing-service worker so metadata and
packet/reply progress continue during a large batch. Use the established
bounded admission/backpressure and stopped-task activation/rollback paths.
This one-way service must precede ordinary syscall decoding and must not depend
on a still-registered PID or launcher. Test exact old/new producers, unchanged
ordinary decoding, guest first-fit behavior, concurrent batch ownership, node
and chunk geometry, guarded data zeroing and ledger/publication ownership before
module/image compilation and the unchanged libc application rerun.

Guest batch/protocol checkpoint: native pending consumers now use the existing
atomic `llist_del_all` and `llist_add_batch` operations. The node ABI is unchanged,
with compile-time bindings to the shared checked zeroing geometry. The original
one-way producer sets `MCZB0001` only for native nr 279; the ordinary syscall
decoder remains strict. Protocol attempt 4 passes three legacy and five native
tests, including all 30 exact C allocation/guard vectors, six producer vectors,
deterministic timer-style reentry/late arrivals and three concurrent consumers
with immediate allocator metadata reuse of 2,048 chunks. Original attempts 1–3
remain failed and fully retained: a legacy C signedness warning and two fixture
module/import issues. Native host integration and actual guest acceptance remain
pending. Keep the original core application and launcher unchanged.

All four guest image selections now build with this batch contract; exact
source/binary evidence is in the zeroing image checkpoint. The Rust selections
exclude the whole C allocator and supply all zeroing exports from the actual
Rust object. Native disassembly binds atomic exchange at node offset 56,
zeroed publication at 48, page subtraction at 44 and the nr-279 marker at
packet offset 80. The legacy image retains its old producer and consumer.
No new image has executed in a guest yet.

For the remaining host adapter, validate a chunk across the contiguous union
of the same OS's extents: existing `checked_guest_bytes` admits only one extent,
while guest free chunks can span adjacent owned extents. Keep the existing
other service mappings unchanged. The node control claim covers 24 bytes, but
chunk preflight must additionally reject overlap with the complete 256-byte
node, including a node that straddles a page boundary. Do not exclude the whole
8-MiB kernel mapping window from zeroing: unused pages beyond early allocation
can legitimately enter the free pool there. Retain exact boot geometry and
check assigned ownership, headers, cycles and active ledger spans before
clearing any detached chunk.

The host adapter is now integrated. `sysfs_zeroing.rs` retains the exact boot
layout, validates the complete same-owner extent union, claims node control
and every detached chunk before effects, preserves the 48-byte header, and
uses captured page counts after publication permits immediate allocator reuse.
A third retained worker handles bounded zeroing admission independently of
metadata and packet progress. Existing EAGAIN handling retains the complete
unaccepted packet; malformed accepted work retains its claims and owners.
Nine focused host tests pass, including 512 concurrent immediate chunk reuses,
1,024 queue-full retries, five allocation failure points and all seven ledger
claim classes. The original fixture accessor failure is preserved.

Native module attempt 1 compiled Rust but objtool did not recognize the exact
Rust 1.92 `Vec::swap_remove::assert_failed` noreturn symbol. The retained compiler
library source, alloc object and relocations prove this function returns `!`.
Patch 0025 adds only its exact mangled suffix to the existing Rust classifier.
The identical failing module object then passes the original objtool flags;
three unknown-callee mutations still reproduce both original errors. Module
attempt 2 builds all three modules with all original checks. All 77 targeted
configuration/license tests pass from a captured writable source tree; the
earlier read-only mutation-test failure remains preserved. Historical config
replay and patch 0024 are unchanged. These results establish compilation and
focused checks; actual zeroing, host invalidation and libc completion remain
unverified until the next guest run.

The full `native-application-zeroing-host-checkpoint-20260909.json` retains
nine complete validation captures and both original audit failures in 13
artifacts, with all 57 native compiler bindings. The corrected audit accounts
for expected CLI-error stdout inside one passing test and buffered stdout after
final unittest OK. Neither failure changes the original test or build results.
Guest runtime verification remains the next gate.

## Native clone3 capability boundary review, 2026-09-09

Before changing behavior, preserve thread guest 1 from `a841707d`. The actual
trace records guest syscall 435 returning Linux child PID 311, followed by
launcher SIGSEGV. `arch/x86_64/kernel/include/syscall_list.h` has no clone3
handler; `kernel/syscall.c::syscall` routes that missing entry through existing
Rust `syscall_generic_forwarding` / `syscall_generic_forwarding_body_result`.
The unchanged launcher special-cases syscall 56 for its existing cooperative
clone protocol, but sends 435 to `syscall(number, args...)` generically. It
cannot create a McKernel thread from that Linux execution context.

Retain the existing Rust `sys_clone` / `arch_clone_body_result` and `do_fork`
implementation and unchanged libc/application/launcher. For the native guest
selection only, return truthful ENOSYS for unsupported clone3 from the generic
forwarding body before writing the request or invoking its offload provider.
Keep its original null-request/provider checks, all other syscall forwarding,
legacy Rust selection and exact C fallback unchanged. Clone3 remains explicitly
unsupported; this is a capability boundary, not a clone3 implementation. Do not
change libc or force a successful thread result. Its normal compatibility path
must exercise the existing guest clone and pass the complete original pthread,
TLS, barrier, mutex and join checks in a fresh guest.

Verify exact C/legacy Rust equivalence for the original forwarding body,
native non-435 equivalence, and zero request mutation/provider calls for 435,
including hostile argument values and original invalid-input guards. Build all
four images and bind the selected native code before rerunning the thread mode.
If the existing clone path exposes another issue, retain it and investigate;
signal and handoff acceptance remain pending until their actual checks pass.

## Guest-local clone3 integration review, 2026-09-09

This implementation supersedes the preceding unexecuted blanket-ENOSYS plan.
Reuse the existing Rust `sys_clone`, `arch_clone_body_result` and their C
`do_fork` lifecycle provider to create the actual McKernel thread. Add a native
Rust `sys_clone3` handler in the selected x86_64 syscall table, controlled by
the same native build profile. Preserve C fallback/legacy tables and all
existing clone exports. The generic forwarding body remains unchanged.

Bind the new 88-byte argument decoder to pinned Linux 6.12 `include/uapi/linux/
sched.h`, `kernel/fork.c::{copy_clone_args_from_user,clone3_stack_valid,
clone3_args_valid}` and `include/linux/uaccess.h::copy_struct_from_user`.
Accept the 64-, 80- and 88-byte versions and zero-filled extensions up to one
page; preserve size, copy-fault, zero-tail, signal, flag and stack validation.
Use the existing checked `syscall_copy_from_user_bridge` into bounded private
storage, then compute the downward-growing child stack top and map flags,
parent/child TID pointers and TLS into a private copy of the original context.
Preserve the caller's complete context, PC/SP and actual clone result. Never
invoke a Linux clone3 syscall. Reject features without a McKernel owner
(pidfds, explicit set-TID, cgroups/namespaces, CLONE_IO and CLEAR_SIGHAND)
explicitly; do not silently accept or truncate their flags. Existing guest
clone restrictions remain enforced by the retained lifecycle provider.

The old clone ABI has a private pthread-marker convention when child stack
and parent-TID addresses are equal. A real clone3 must never be interpreted as
that marker: gate the existing C call-site's marker branch by the original
syscall number under the same native-only selection. Keep all other legacy
and lifecycle control flow intact. Verify the original/adapted selection and
valid alias case; do not introduce an artificial address restriction.

Test the full decoder against exact extracted pinned Linux C validators with
controlled copy/access providers, then the complete native adapter with the
existing Rust clone entry and lock/fork callbacks. Include all version/tail
boundaries, checked address arithmetic, rejected flags, copy faults, invalid
owners, context preservation, correct stack/TID/TLS/PC/SP mapping and actual
success/error propagation. Build all four image selections; require the native
syscall table's slot 435 to point at the Rust handler and legacy slots to stay
zero. Run the unchanged pthread/TLS/barrier/mutex/join application afterward,
with no observed generic host syscall 435, before signals or handoff acceptance.

The adapter/protocol checkpoint now passes 524 vectors against the exact pinned
Linux C validators, with explicit unsupported-feature errors, plus three full
Rust decoder/adapter tests and 144 exact C marker-selection cases per profile.
The actual Rust clone/lock/fork adapters preserve private context and actual
provider results. Original attempts 1 and 2 remain failed fixture captures
(missing exact lock-node type and generated C indentation respectively).
Image compilation and actual clone3 thread execution remain pending.


## Native running TID transfer integration review, 2026-09-09

Before host behavior edits, the clone3 image 2 / host zeroing module 2 guest
reaches the existing guest `do_fork` and `settid` path. The unchanged Rust
launcher `act_gettid` receives delegated nr 186, collects its actual active
thread IDs, and invokes the existing `MCEXEC_UP_TRANSFER` descriptor. That
ioctl currently authorizes only prepared ELF sections; the allocated guest
kernel TID array is outside them. The launcher reports the failed transfer,
returns -EFAULT, and the original pthread_create assertion fails at line 102.
The actual guest clone3 result is -14; no nr-435 Linux delegation occurs.
The complete original runtime capture remains FAIL and must be retained.

Reuse decisions and required integration:

- Preserve `kernel/syscall.c::{do_fork,settid,NR_TIDS}` and the selected native
  clone3 adapter. Preserve `executer/user/rust/mcexec_helpers.rs::{act_gettid,
  mcexec_collect_active_tids_result}`, its C counterpart and the public
  `remote_transfer` descriptor. The actual launcher supplies the TID bytes;
  do not fabricate IDs, remove a thread or replace pthread synchronization.
- Extend `mcctrl_process::Registration::transfer_image` using its existing
  referenced current Linux worker/MM, private delivery token and UserSlice
  copy. Add a kernel-only running-transfer command to the existing application
  connection. Prepared image transfers retain their original section checks.
  A delivered worker cannot fall back to unrestricted prepared-image copying.
- Reuse `application_syscall::Request` to authorize exactly nr 186's arg4
  element count, arg5 physical address, checked four-byte element size and
  to-guest direction. Preserve the existing public transfer size bound; do not
  silently truncate a requested TID array or broaden arbitrary RAM access.
- Extend `smp_application_syscall::Mailbox` under its existing application
  mutex: exact worker/delivery, Delivered state, no kernel-service takeover,
  cancellation, stale/reused token, duplicate successful transfer or completion
  may write. The full bounded kernel-buffer copy stays inside this ownership
  critical section; user access occurs before it. The original RET publishes
  the actual launcher result; a successful TID result requires its copy.
- Reuse `sysfs_memory::SyscallResponse` and its shared payload ledger. Factor
  the existing pager claim into one checked helper used by both pager and TID
  payloads. Retain the whole exact-OS payload claim through real response/wake
  publication, including close and full-queue retries. All seven existing
  claim classes and zeroing exclusions remain active. No guest access after
  final status or ownership release. Failed copies retain or release owners
  through the existing response lifecycle.
- Route the new kernel-only command through existing IHK/SMP application
  dispatch and registration, with no new C body, Linux FFI or registry.
  Validate argument/owner/state/duplicate/retry/cancellation cases against the
  full current mailbox, exact native user adapter and actual memory ledger,
  then build all three native modules with original warnings/objtool/no-SIMD
  checks. Guest sources are unchanged; reuse clone3 image 2 and rerun the
  unchanged pthread test in a fresh isolated guest. Stop at its first failure.

This work is an unfinished host connection, not a thread/futex PASS. Signals,
actual abnormal-owner coverage, final control regressions and replays remain
required before the Ultra handoff.


## Native syscall trace sampling review, 2026-09-09

The TID-module thread guest completes both guest clones (TIDs 310/309), all
original pthread checks, exact output/exit 37 and full normal cleanup. Its
final audit fails because Registration's per-PID trace budget counts each
line separately: 27 deliveries + 26 returns + 11 routes consume all 64 slots,
cutting off the final write result after its route. Preserve that original
FAIL; do not weaken route/result assertions. Before logging edits: reuse the
existing private HostWorker and exact delivery publication, sample once per
WAIT delivery, and retain that decision for its route and actual return.
Keep the 64-delivery bound (at most three lines each), existing identity/MM and
WAIT/RET effects, error propagation, C code and public ABI. Validate the exact
WAIT/RET adapter including its final budget slot, build native module 2 and
rerun the unchanged guest with all original assertions. Thread acceptance
remains pending the complete passing audit.


## Signal-stack failure triage, 2026-09-09

TID module 2 / clone3 image 2 passes the full unchanged threads guest audit.
The first signal guest fails line 142: the first blocked/pending SIGUSR1 is
unblocked, handled on the 64-KiB alternate stack and returns successfully;
the second SIGUSR1 handler is placed on the ordinary user stack. The exact
captured handler stack pointers are 0x60f648 and 0x547fffffec78. Keep the
original assertion requiring both deliveries on the alternate stack.

The selected architecture C signal-frame builder in
`arch/x86_64/kernel/syscall.c::do_signal` sets `SS_ONSTACK` on the live thread
before copying that stack into `ksigsp.sigstack`. The selected Rust
`syscall_policy::arch_rt_sigreturn_body_result` then restores the saved stack
bytes verbatim. That preserves the active-stack flag after return and explains
why the next delivery skips the alternate stack. Review the full producer,
Rust consumer, nested delivery and original Linux stack-state semantics before
editing; preserve the legacy/C equivalence selections and implement new native
behavior in Rust through the established boundary. Do not change the app.

The same capture contains `ret: Interrupted system call` during the host return
path. Its accepted-result/response ownership and ordinary launcher behavior
also need review; do not hide that output or weaken the guest error scan.
The first failure scan stopped before complete cleanup, so this signal attempt
has no abnormal-owner or cleanup acceptance credit. Final current-module
memory/file replays, both full control regressions and real abnormal-owner
coverage remain pending. The phase is still active, with three core modes
accepted and no Ultra readiness claim.


## Native signal frame and committed-return integration review, 2026-09-09

Before behavior edits, the selected producer remains architecture C
`arch/x86_64/kernel/syscall.c::do_signal`; native Rust owns
`syscall_policy::{sys_rt_sigreturn,arch_rt_sigreturn_body_result,
sys_sigaltstack,sigaltstack_body_result}`. Reuse `abi::SigStack`, the existing
`sigsp`/`RtSigreturnFrame` layout, checked user-copy bridges, XSAVE providers,
and the current signal-common lock and pending-signal lifecycle. Preserve
legacy Rust and C fallback selections and their original equivalence bodies.
No existing Rust producer implements this architecture stack-selection gap.
Add only the native Rust stack preparation/publication and alternate-stack
state handling behind the existing Linux-6.12 Rust cfg and an explicit matching
C selection; do not overload the clone3 selection macro.

Pinned Linux 6.12 references are `include/linux/sched/signal.h::{__on_sig_stack,
on_sig_stack,sas_ss_flags}`, `arch/x86/kernel/signal.c::get_sigframe`,
`include/linux/signal.h::unsafe_save_altstack`, and
`kernel/signal.c::{do_sigaltstack,restore_altstack}`. Linux determines active
stack state from the interrupted/restored SP; entering a handler must not save
an already-mutated active flag. Its downward stack interval excludes the base
and includes the top. Preserve the 128-byte x86 red zone for ordinary and nested
frames, check all frame/XSAVE/restorer arithmetic and user/alternate extents,
and reject overflow before user writes. Keep McKernel's existing frame ABI
and floating-point layout. Unsupported SS_AUTODISARM remains rejected.

Native preparation snapshots the interrupted stack without changing the live
thread. Publish live active state only after the existing XSAVE/frame copies
and a checked restorer copy succeed. Failed copies must leave that state
unchanged and release the signal lock before the retained termination path.
Native sigaltstack queries derive flags from the actual caller SP and reject
replacement while running on the alternate stack. Native sigreturn restores
stack configuration with the Linux nesting rule, uses its private copied frame
for restart/result fields, and releases its temporary XSAVE allocation after a
copy failure. Keep the old byte-restoration tests in the legacy selection;
exercise actual native bodies separately with copy faults and nested returns.

The actual host nr-14 RET was accepted while Linux delivered the signal, but
`Remote::return_syscall` allowed its completion wait to return EINTR. The
unchanged launcher treats a RET error as an error, whereas its WAIT loop
explicitly retries EINTR. Reuse the exact pinned Linux
`rust/kernel/sync/condvar.rs::CondVar::wait` for the already-committed return
publication interval. Validation/copy errors before acceptance remain errors;
ordinary WAIT remains interruptible. The existing continuing pump, retained
response/worker ownership, quarantine errors and notifications remain the
completion authority. A committed result cannot be retried or rebound; hold
the ioctl's referenced owner until its real publication or recorded failure.
No new FFI, fabricated result or early 'returned' log is needed. Preserve the
actual native user RET adapter and its acceptance/error tests.

Validate the native stack predicates against exact extracted pinned Linux C,
actual native preparation/publication/sigaltstack/return bodies including
nested delivery, red-zone/extent boundaries and copy failures, and the exact
host committed-return method with delayed/full-queue and error completion.
Build all four guest selections and all three host modules with original
checks; then run the unchanged signal application in a fresh guest. Preserve
the original failed attempt and all original output/route/cleanup assertions.
Final memory/files/control replays and abnormal-owner coverage still follow.

The native signal image checkpoint now passes all four image profiles and 37
exact guest compiler bindings. It retains the complete first indirect-call
audit failure and the corrected exact target/register/call audit. Prior
clone3, protection and zeroing binary checks still pass. All three signal
host modules also compile. Candidate: signal module 1 and signal image 2;
the unchanged signal application result remains pending.


## Actual abnormal-owner verification, 2026-09-09

Use the current signal module 1 / signal image 2, unchanged mcexec and original
core/HELLO assertions. Existing worker-reap and inherited-process fixtures prove
real Linux task departure only with applications=0; they do not satisfy the
scheduled application failure gate. Retain them as later control regressions.

Add a small ordinary dynamic-libc payload that writes a fixed readiness marker,
then reads sixteen bytes from stdin into a guarded buffer. Its Linux reference
must verify both the ordinary successful read and a real blocked read killed
by its parent. A separate Linux guest controller owns private stdin/stdout
pipes, forks and execs the unchanged mcexec, reads the exact marker, and locates
the exact live Linux task blocked in read(fd=0, length=16) through /proc. Only
then send SIGKILL to that unreaped child and verify its actual SIGKILL status.
The controller never writes input that could complete the read before death.

Require scheduled application and delivered-read evidence, successful normal
baseline first, bounded process/worker cleanup after actual launcher failure,
and no remaining application process nodes. In the isolated guest only, lower
pid_max after cleanup and fork/reap enough children to prove numerical reuse
of both the old launcher PID and blocked worker TID. No application ioctl may
hide cleanup during that quiet reuse window. Then run eight more unchanged
HELLO applications in the same McKernel OS instance, with original output,
exit, delivery/result, registration and retirement assertions for each.
Keep the entire pre-failure core suite and every unexpected-error scan. Audit
the intentional failure window separately and retain all original/executed
helpers and exact binaries. A cleanup failure stops the batch and is evidence
for investigation, not permission to weaken the acceptance criteria.

Reuse the existing native ProcessId, Registration/HostWorker reaper,
Remote/Mailbox cancellation and scheduled retirement implementations unchanged
for this first test. Any behavior fix needs its own selected Rust/Linux reuse
review and focused validation after the actual failure is retained. Final
current-pair core replays and both full control-ABI regressions remain pending.
