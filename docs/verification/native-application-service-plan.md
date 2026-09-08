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
