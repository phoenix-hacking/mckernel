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
