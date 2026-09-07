# Native CPU reservation adapter: reuse and API review

The Rust Linux CPU adapter now builds against the pinned Linux 6.12 kernel
and passes a disposable four-vCPU guest capture. Native x86_64 and compat i386
control programs reserve and return CPUs, exercise Linux failure injection,
and prove rollback, outside-online veto, closed-file module pinning, concurrent
operations, and two clean unload/reload cycles. McKernel boot remains pending.
The first capture used a prototype stage. The subsequent authoritative stage,
three-module Kbuild and compiler link closure pass; those rebuilt modules also
pass a four-vCPU guest with two NUMA nodes. No production gate is promoted.

The OS target is 64-bit x86_64 throughout. The i386 control probe tests only
userspace ioctl compatibility; it is not a 32-bit kernel build.

The preserved inventory baseline is `24a151fef5b9fcf303fdbb8cf9762340cd4100fd`;
the CPU adapter is added on local checkpoint `b8d5170d`. Linux source
comes from the pinned Rocky archive in `host-kernel/rocky/source-lock.json`;
the existing compatibility patches and native staging workflow are reused.

## Existing implementation to retain

- `host-kernel/native-rust/smp_resource.rs`: reuse `CpuTable`, `CpuSlot`,
  `CpuChange`, `prepare_reserve`, `prepare_return_to_host`,
  `begin_external_effects`, `commit`, and `compensated_rollback`. Keep its
  external-effect journal and quarantine behavior. Do not duplicate the state
  machine. Its OS token constructor remains unavailable to production code
  until the separate generation-checked IHK lease bridge is implemented.
- `host-kernel/native-rust/abi/x86_64.rs`: reuse the existing ioctl numbers and
  `IhkCpuRequest` layout. Add explicit compat request decoding at the adapter
  boundary; a 32-bit pointer-bearing request is not the native 16-byte layout.
- `ihk_smp_x86_64.rs`: retain module parameters, provider/open leases,
  `/dev/mcd0` registration, BUILDID, and unbooted create/destroy dispatch.
- `ihk/linux/driver/smp/smp-driver.c`: preserve the pinned behavioral reference
  for request validation, duplicate collapse, ascending query order, exact
  query count, and user-copy errors. This IHK revision has no Rust sources.
- `executer/kernel/mcctrl/rust/mcctrl_helpers.rs`: retain its existing CPU/IKC
  helpers and consumers. They do not implement host CPU reservation and still
  depend on C bridge state; importing the entire helper crate would not supply
  this missing Linux adapter.

## Inspected Linux 6.12 APIs

`kernel/cpu.c` exports `remove_cpu` and `add_cpu`, but each acquires the
Linux device hotplug lock independently. The existing transaction journal needs
that exclusion across the entire batch, including observations and rollback.
Calling those wrappers while holding the lock would deadlock. The new support
patch `0003-driver-core-export-device-hotplug-transactions.patch` therefore
exports four existing Linux functions: `lock_device_hotplug`,
`unlock_device_hotplug`, `device_offline`, and `device_online`. It adds four GPL
exports and no new C function body. The adapter uses those existing Linux
services through a task-bound Rust guard.

These functions may sleep. A positive already-satisfied transition is rejected,
not treated as a newly owned CPU. `cpus_read_lock`/`cpus_read_unlock` bracket
mask and topology observations and end before each CPU writer operation.
Retained `get_device` references preserve allocations, while canonical CPU
device identity is checked before a transition and on subsequent owned queries.

The selected NUMA configuration does **not** export `__cpu_to_node`; that export
requires `CONFIG_DEBUG_PER_CPU_MAPS`. The adapter instead reads Linux's embedded
`struct cpu.node_id` under the device/topology guards. Linux `register_cpu` and
`change_cpu_under_node` maintain that field. The generated bindings expose its
layout. The exported x86 `default_cpu_present_to_apicid` supplies the APIC ID.

A CPUHP prepare callback rejects external attempts to online a reserved CPU.
It reads only bounded atomics, never the policy mutex. A scoped current-task
permission allows the adapter's own transitions and Linux's internal rollback.
The module keeps a separate reference for outstanding resources, including
quarantine, so closing all control files cannot permit unsafe module unload.

## Ownership and behavior requirements

- Initialize large policy/journal/request arrays in static module storage or
  directly in owned heap storage; never place the 512-entry workspaces on the
  kernel stack. Use one pinned Linux Rust mutex for sleepable serialization.
  Publish access before the control device and retire it after deregistration.
- Validate the complete user request before any CPU effect: 0–512 entries,
  non-null array when nonempty, valid present/online IDs, duplicate collapse,
  and a retained Linux control CPU. The first isolated scope keeps CPU 0 online.
- Keep a Linux module reference for every outstanding reservation lifetime,
  including uncertain/quarantined effects. Closing the device cannot leave an
  unloadable module with owned offline CPUs. Release the pin only after verified
  restoration. Unbooted OS ownership remains independently pinned by IHK.
- Prepare policy, begin external effects, perform Linux transitions, verify
  physical state, then commit. On failure, compensate completed transitions in
  reverse order. Do not publish a rolled-back policy if hardware restoration is
  unknown; preserve quarantine and module lifetime.
- `GET_NUM_CPUS`/`QUERY_CPU` refer to available reserved CPUs. Query requires the
  exact count, returns ascending IDs, and copies the count field as the legacy
  request does. A fault must not expose uninitialized bytes or change ownership.
- CPU assignment to an OS, image boot/APIC reset, IKC, and memory remain separate
  integration work. Do not mint an OS token or advertise these operations here.
- The first guest has fixed CPU device topology. Concurrent physical CPU
  removal and external hotplug interference need explicit lifetime review and
  coverage before broad production claims; an initial validity check alone is
  not proof against later CPU-device disappearance.

## Required validation for the slice

Reuse the current policy tests. Add effect-sequence tests for failure at each
transition, reverse compensation, uncertain outcomes, and pin balance. Compile
the actual native crate against the pinned Linux tree and inspect its imports,
stack frames, staging and link closure. Retain unsupported-operation behavior.

In a disposable four-vCPU guest, keep CPU 0 for Linux, reserve/release the other
CPUs through native and compat ioctls, compare `/sys` online state and query
results, test malformed/faulting requests and concurrent opens, prove unload is
blocked while resources remain, then restore all CPUs and unload/reload. Only
after this foundation is covered should OS assignment and McKernel boot follow.

## First implementation: reuse of the transaction journal

The existing `smp_resource.rs` now adds `CpuTransaction::execute_hotplug` and a
small `HostCpuHotplug` boundary. This adapts the existing transaction directly:
the original table, journal entries, commit/rollback rules, OS token privacy,
memory model, and consumers remain in place. No second ownership state machine
or capacity-sized stack buffer is introduced. The new method performs complete
preflight, observes each transition and the final batch, reverses attempted
effects in reverse order, and retains the original quarantine rule if identity
or restoration cannot be verified. An errno after an effect is independently
observed; a successful errno without the physical state change is rejected.

Nine additional fixture tests cover both reserve and return directions, failure
at every CPU position, partial effects, inverse failures, incorrect success,
identity/NUMA mismatch, failed observations, sparse request order, and unwinding.
The existing 29 Rust tests are retained. This is an intentional, additive change
to one existing implementation file and its existing fixture, not a refresh of
the immutable 24a151fe reuse inventory.

The trait remains independent of Linux ownership. The new `smp_cpu.rs` supplies
its Linux hotplug exclusion, retained device lifetime, module reference and
native/compat ioctl adapter. `smp_resource.rs` is unchanged from the verified
38-test checkpoint; its existing transaction implementation executes the real
Linux effects. The canonical `abi/x86_64.rs` is also unchanged.

The first guest evidence is retained locally under
`/work/native-runtime-cpu-adapter-20260907`; `local-run.json` binds the actual
prototype sources, kernel, modules, fixture binaries and serial output. Both
ABIs pass reserve and return failure injection at each of three CPU positions,
three concurrent processes with eight cycles each, malformed/usercopy cases,
outside-online veto and closed-file resource pinning, repeated across two
module lifecycle cycles. All four CPUs are restored and all modules unloaded.
No BUG, WARNING, Oops or panic marker was detected.

This proves the fixed-topology CPU reservation slice. It does not prove physical
CPU eject, suspend, identity replacement recovery, memory allocation/assignment,
OS token handoff, APIC boot, IKC, or workloads. The second capture additionally
proves the same CPU operations with node 0 containing CPUs 0–1 and node 1
containing CPUs 2–3; it does not prove memory placement or boot on either node.
No production tracker credit follows automatically from this local capture.

## Retained exact-stage checkpoint

The [2026-09-07 checkpoint](native-cpu-checkpoint-20260907.json) retains both
runtime captures and distinguishes prototype staging from the verified exact
stage. Its source/compiler records bind the rebuilt modules and the two-node
guest. The final repository suite ran 2,299 tests in 334.363 seconds with 71
skips and no failures. Memory reservation/assignment, native McKernel boot,
workloads and production gate credit remain unproven by this CPU slice.
