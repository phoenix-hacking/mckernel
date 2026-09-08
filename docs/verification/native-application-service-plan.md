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
