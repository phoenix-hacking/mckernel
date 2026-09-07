# Native CPU reservation adapter: reuse and API review

This is the next bounded implementation after the recorded native unbooted
lifecycle run. It does not establish CPU reservation or McKernel boot yet.

The OS target is 64-bit x86_64 throughout. The i386 control probe tests only
userspace ioctl compatibility; it is not a 32-bit kernel build.

The source baseline is `24a151fef5b9fcf303fdbb8cf9762340cd4100fd`. Linux source
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

`kernel/cpu.c` exports `remove_cpu(unsigned int)` and `add_cpu(unsigned int)`
under GPL. Their implementations acquire `device_hotplug_lock`, invoke device
offline/online, and release that lock. The comments explicitly direct other
subsystems to these functions. Reuse them instead of reproducing the legacy
kernel writes to `/sys/devices/system/cpu/cpuN/online`.

The functions may sleep. Their return value is zero for a performed transition,
positive for an already-satisfied device state, or negative errno. Do not
convert any nonnegative value blindly into a newly owned transition.

`cpus_read_lock`/`cpus_read_unlock` are exported and can bracket topology reads;
release that read lock before a hotplug call requiring the write side.
`nr_cpu_ids`, `__cpu_online_mask`, and `__cpu_present_mask` are exported, and the
generated bindings expose the masks and scalar limit. In
`arch/x86/kernel/apic/apic_common.c`, the exported
`default_cpu_present_to_apicid(int)` supplies the physical APIC ID or BAD_APICID.
The NUMA configuration exports `__cpu_to_node(int)` from `arch/x86/mm/numa.c`.
Use these ordinary Linux services through small reviewed Rust FFI boundaries.
No McKernel-owned C object or helper bridge is needed for this slice.

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

The trait does not provide Linux hotplug exclusion, CPU device lifetime, or a
module reference. Those are explicit requirements of the Linux adapter. The
method is not reachable from an ioctl yet, and these model tests cannot prove
physical CPU reservation. No production tracker credit follows from this step.
