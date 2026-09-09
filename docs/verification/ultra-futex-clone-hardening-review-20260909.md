# Native futex timeout and clone TID hardening review

## Review recorded before implementation, 2026-09-09

This bounded Ultra repair addresses G04/G05 in
`ultra-guest-review-20260909.md`. No validation results are claimed here.
The baseline is signal module 1 / signal image 2, with native behavior from
`3453edd571152132b19d23b26dad32f4204612e6`. Legacy/fallback semantics remain
selected separately. Root owns shared `kernel/rust/lib.rs` and
`kernel/CMakeLists.txt` integration; this task must not overwrite them.

### Selected sources and reuse decisions

* Retain `kernel/rust/syscall_policy.rs::do_futex_body_result` and all its
  existing C fallback/legacy tests unchanged. Add a separately selected native
  entry in `kernel/rust/native_futex.rs`, gated in C by the proposed semantic
  `MCKERNEL_NATIVE_FUTEX` macro and in Rust by
  `native_linux_irq_work_v6_12`. Root adds the module/dependency/macro together.
  Native parent/child TID stores use the separate
  `MCKERNEL_NATIVE_CLONE_TID` selection.
* Reuse `syscall_copy_from_user_bridge` and the existing Rust x86 user-copy
  implementation. Copy one complete timespec to kernel storage; never read
  through the raw user timeout pointer. Validate signed sec/nsec before any
  arithmetic. Preserve the pinned Linux precedence: timeout copy and timespec
  validation precede command/clock rejection, then futex word setup.
* Reuse `native_vdso::clock` for precise available CLOCK_MONOTONIC/REALTIME
  samples, and the exact existing private nr202 clock bridge as fallback.
  Never silently substitute a coarse timestamp for an exact absolute deadline.
  Zero the entire C syscall request before assigning its physical destination
  and clock ID. The C bridge keeps its stack timespec alive through synchronous
  `do_syscall`; mcexec's existing clock operation returns at most 16 bytes.
  Host review confirms `application_syscall::authorize_return_copy` requires
  nr202/length16/destination==arg0, `sysfs_memory::application_copy` checks the
  OS span and holds the shared ledger during synchronous copying, and response
  publication follows that copy. No lifetime beyond that publication is
  invented. Error propagation and real timed application behavior still need
  runtime validation.
* Reuse existing futex queue/value/wake machinery. Deadline zero must never
  select its `timeout==0` untimed representation. Native conversion is signed,
  normalized and saturated to the positive timer range; a present immediate
  deadline uses the minimum positive timer quantum while the futex setup still
  runs first (preserving EAGAIN/EINVAL precedence). This gives a bounded
  immediate-expiry path, not permission to treat zero as infinite.
* Review the selected lower-level timer in
  `kernel/rust/sched_helpers.rs::timer_schedule_timeout_body_result`: its
  runnable-thread branch schedules and restarts measurement without charging
  elapsed time. Add native-only elapsed countdown using the original timer
  lock/scheduler/zeroing bridges. Preserve all original nonnative helper
  contracts and keep a native focused fixture for this control flow.
* `kernel/rust/futex.rs::get_futex_value_locked` currently performs an unchecked
  volatile user load under the hash-bucket spinlock. Ordinary checked copying
  cannot simply replace it there because page fault/allocator/scheduler work
  cannot run under that lock. Existing x86 futex asm emits `__ex_table`, but no
  exception-table consumer was located in the selected guest sources. A new
  nofault-load design must be coordinated with root before editing this path;
  table emission alone is not instruction-fault containment evidence.
* Replace only the native `CLONE_CHILD_SETTID` direct physical store in
  `kernel/syscall.c::do_fork` with existing
  `write_process_vm(new->vm, child_tidptr, &new->tid, sizeof(new->tid))`.
  `kernel/rust/x86_memory_helpers.rs::x86_write_process_vm_public_result`
  validates the complete user span and faults it with
  `PF_POPULATE|PF_WRITE|PF_USER`, using the **child's explicit VM**, then copies
  per virtual page. This retains permission/COW/page translation handling.
  Do not use current-parent `copy_to_user` for a separate child VM, and do not
  use `PF_PATCH` to bypass read-only protection. The child/thread reference is
  held and not yet runnable at this point. Private-child VM is unpublished;
  shared VM follows the existing user-copy concurrency contract, whose wider
  unmap-race acceptance remains separate.
* Match pinned Linux's ignored failed child-TID store: faulting child storage
  does not by itself make the parent's successful clone fail or tear down the
  child. Also retain the checked `setint_user` parent store but ignore its
  failure only in the native profile, matching Linux's parent put_user call.
  Legacy behavior remains unchanged. Existing CHILD_CLEARTID uses checked
  `setint_user` in the exiting/current child's VM, then wake and clears its
  kernel pointer; preserve that existing route. Do not implement fork/robust
  lists or broaden current host process-creation support as part of this repair.

### Exact pinned Linux dependencies

Local root: `/work/native-source/linux-6.12.0-211.44.1.el10_2`.

* `kernel/futex/syscalls.c`: `futex_cmd_has_timeout`, `futex_init_timeout`,
  `SYSCALL_DEFINE6(futex)`, and `do_futex` clock/op validation.
* `include/linux/time64.h`: `timespec64_valid`, timespec conversion bounds.
* `include/linux/ktime.h` and `kernel/time/hrtimer.c`: saturated ktime
  conversion/addition, distinguishing a null timeout from an expired one.
* `kernel/futex/waitwake.c`: value/bitset/queue/timeout error precedence.
* `kernel/sched/core.c::schedule_tail`: child `put_user` after child context
  switch, ignored failure. McKernel's explicit-child-VM store is earlier but
  before child user entry, satisfying visibility before the child returns.
* `kernel/fork.c::kernel_clone`: checked parent `put_user` result is ignored;
  `copy_process` selects `set_child_tid`; `mm_release` clears/wakes child TID.

Robust registration currently acknowledges a 24-byte list without tracking
its head. Robust owner-death behavior is an explicit capability blocker,
separate from ordinary pthread/mutex startup. No robust-mutex support claim
or new robust-list implementation is part of this change.

### Coordinated design additions before the lower-level edits

Root supplies `native_user_read_u32_checked(from, to) -> i64` with a whitelist
of its exact load PC in native #PF/#GP handling. Native futex loads validate
alignment and complete current-VM user range before that instruction; WAIT
and CMP_REQUEUE perform ordinary checked read/prefault **before** hash locks.
Private WAKE remains a range-only operation and does not demand-populate an
unmapped page. Concurrent unmap after prefault is a contained EFAULT under
the hash lock. No ordinary copying or VM fault handling is added under it.
The current native WAKE_OP path is explicitly EOPNOTSUPP until a reviewed
checked read-modify-write primitive exists; its old fault-uncontained asm is
not reachable through the selected native syscall wrapper. PI remains ENOSYS,
robust lists remain the separately documented blocker, and UTI is explicitly
EOPNOTSUPP in this native futex adapter because it needs its Linux-owned
user-copy/scheduler context. Legacy selection retains these old paths.

The native futex wait retry loop also needs one deadline for its entire wait,
not a restarted timeout after each spurious wake. It will charge elapsed TSC
ticks across retries, still running value/bitset validation before expiry.
The same native one-shot TSC clock convention supplies scheduler countdown.
Absolute REALTIME conversion samples the clock before waiting; this repair
does not establish adjustment tracking for subsequent Linux realtime clock
steps. No clock-setting test or such conformance claim is authorized by these
focused results alone.

Native `FUTEX_REQUEUE` must carry arg3 as val2; the old shared helper selected
arg3 only for CMP_REQUEUE/WAKE_OP. The native call site now preserves the
actual requeue count while retaining the legacy helper and its old selection.
Current command scope: WAIT/WAIT_BITSET, WAKE/WAKE_BITSET and
REQUEUE/CMP_REQUEUE use the retained native queue implementation;
WAKE_OP returns EOPNOTSUPP pending checked RMW; PI/unknown commands return
ENOSYS; disallowed CLOCK_REALTIME combinations return ENOSYS after the
required timeout snapshot/validation. These are source contracts awaiting
validation, not new broad futex acceptance.

## Validation plan (not executed)

Root serializes validation in the existing native/compat containers. The task
will supply a dedicated helper and fixtures; original attempts must be fully
captured and failure logged before retry. Required layers: exact selected
Rust helper unit tests; independent exact pinned-Linux time validation and
saturation vectors; unchanged legacy/fallback equivalence; C/Rust selection
and call-path checks; four image profiles; same-binary native Linux-reference
and real McKernel timeout/TID tests; original pthread/core/control regressions.

Required primitive cases include faulting/cross-page timeout pointers; negative
seconds, nsec -1/1e9; zero relative, past absolute, very large saturated values;
FUTEX_WAIT|CLOCK_REALTIME rejection after timeout validation; mismatched value
before expiry; valid wake; countdown while another thread remains runnable;
and writable/read-only/unmapped/cross-page child and parent TID spans with
canaries and continued successful child startup/join. Fault waits must use a
Linux-side outer watchdog. Full fork/COW runtime tests remain blocked by the
separate CREATE_PPD/process protocol milestone; exact target-VM copy fixtures
can verify child VM selection without claiming actual fork acceptance.

Prepared repository helper and exact commands (neither has run):

```text
/home/holden/mckernel-work/bin/mckernel-container native python3 -B /workspace/scripts/tests/run_ultra_futex_clone.py native 1
/home/holden/mckernel-work/bin/mckernel-container compat python3 -B /workspace/scripts/tests/run_ultra_futex_clone.py compat 1
```

Each uses a fresh `/work/ultra-futex-clone-protocol-20260909-PROFILE-ATTEMPT`
directory and retains complete selected original sources, exact extracted
bodies, Linux source/header identities, compiler commands/dependencies and
all output. The helper compares 240 exact pinned-Linux vectors, exercises the
new native timeout body, exact scheduler and futex retry bodies with a
controlled TSC, exact native C child/parent TID store blocks, and the existing
Rust complete-span VM copy over guarded discontiguous page providers. The
Rust fixture substitutes the physical page-fault provider, so its permission
and VM-routing checks do not establish real COW or concurrency. The actual
root-owned nofault instruction and ordinary application tests still require
the new image and isolated guest. The preserved
`kernel/rust/tests/run_equivalence.sh` is the full legacy-equivalence command,
to be run from an isolated writable source copy with its existing prerequisite
inputs; this helper does not replace it or alter its assertions.

## Native image 2 link failure: bounded division design before correction

Root retained `/work/mckernel-native-ultra-images-20260909-2` and logged the
native linker failure: `timer_ticks`' u128 `div_ceil` requires `__udivti3`, which
the freestanding kernel does not provide. The passing user-space protocol
fixture linked compiler runtime support and therefore did not expose this
image dependency. Fallback and legacy Rust were already built and audited.

Review found no existing selected kernel Rust u128 division or long-division
helper to reuse (`kernel/rust` search for `__udivti3`, division helpers and
u128 division). Retain the original multiply-by-1000, which already compiled,
and the original exact ceil/minimum-one/i64::MAX saturation contract. Replace
only the division with 63 bounded descending quotient-bit decisions. For
each bit 62 through 0, compare/subtract the u64 divisor shifted into u128.
Each shift fits in 126 bits; the numerator is below 2^74. The resulting
quotient is the exact floor when representable, or i64::MAX when larger;
one remaining nonzero remainder rounds up, then the original upper cap and
minimum-one apply. This needs no new compiler runtime, C provider or ABI.

Keep every existing protocol assertion. Extend the independent standard-Rust
u128 division oracle with all u64 powers of two and adjacent values, extreme
divisors and exact quotient/remainder boundaries; those test-only divisions
remain in the ordinary user-space fixture. Root must rerun the complete
protocol in fresh native/compat attempts and rebuild a fresh four-profile
image attempt. No new runtime or image acceptance follows from this design.
