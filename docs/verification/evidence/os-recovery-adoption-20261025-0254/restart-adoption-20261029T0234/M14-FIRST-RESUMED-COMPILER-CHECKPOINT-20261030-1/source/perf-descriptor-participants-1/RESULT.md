# Perf descriptor participants — private source, NOT SELECTED

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This packet binds the independently source-reviewed candidate-3 owner core and
retained 5aa composite perf entry; its exact source digests are in MANIFEST.json.
Only the new Rust module and previously paired witness patch are proposed. No
canonical files, selectors, C runtime bodies or held domains were changed.

Implemented source adapters:

* `acquire_open_group` uses the actual candidate-3 process/registry/group locked
  lookup and returns a held root-or-member pin plus a preallocated record.
  `release_open_group` consumes the pin and keeps nonempty final batches or
  quarantine in a separately allocated retained record. Member descriptors are
  detected, but using one as group leader remains a held semantics decision.
* `prepare_standalone` allocates event/group sidecars through the retained selected
  tracked allocator bridge; commit/register/list publication share the process
  lock. Failed or aborted tokens and private allocations transfer to records.
  `publish_member_reserved` holds the same process lock across member link,
  registry registration and descriptor publication, and undoes its descriptor
  lease on registration failure. Fresh member/event creation remains a caller
  obligation and must precede the adapter.
* `clone_registered` snapshots the actual `Mckfd` only under its parent process
  lock, requires live generation-protected registration and null dup callback,
  mints a separate descriptor lease, releases the parent lock, and registers the
  child under its lock. Registration failure invokes lease unwind and retains
  descriptor, registration and the exact finalization/quarantine outcome.
* `detach_for_close` finds and unregisters only a registered perf descriptor
  under the same process lock before unlink, then runs typed detach after unlock
  and retains both descriptor and outcome. It does not invoke the current close
  callback, issue the host forward, free anything or return a syscall result.

Records use the selected tracked allocator before entering descriptor operations;
failed inputs, typed tokens, finalization batches and quarantine are retained in
an IRQ-lock-protected private append-only list after process locks are dropped.
This is a concrete owner but deliberately has no drain, finite bound, teardown or
recovery; selecting it would leak and can exhaust memory. No source result claims
production readiness. Any unused reservation must be explicitly cancelled; token
must-use annotations do not replace caller discipline. Actual allocator pairing,
alignment and all lock/IRQ/reentrancy requirements remain independently unproved.

The actual selected `syscall_close_body_result` first runs its tofu helper under
process lock, removes the descriptor, calls its close callback/free after unlock,
and returns the host forward result. The actual `f03_perf_close_v1` frees the event
and clears the closing current thread's PMU maps. The original fork path copies
from the source list while taking the child lock and can call dup callbacks under
that lock. These behaviors are not reproduced or replaced by this module: caller
selection, parent/child fork synchronization, rollback/teardown, counter owner,
monitor/scheduler/raw list readers and callback/host-close semantics are still
blocked. The selected source actually publishes opt NULL today; no registration
or private module is wired. No generic descriptor lifetime or mmap interface is
claimed. The member-FD path is explicitly held rather than claimed compatible.

The paired 33-field C/Rust ABI witness is reused unchanged from candidate-3;
it has not been compiled, compared or linked with this module. Regression source
exercises actual proposed participant bodies for member-FD distinction, leader
first, clone registration failure/unwind and retained close; callback substitution
is a deliberate synthetic fault and proves no observed race. The fixture is
uncompiled and unrun; future execution must be serial because the fixture shares the private registry and retained-record head. Next: independent unsafe/ABI review, then resolve record
reclamation and every production participant before selection. No compiler,
test, guest, native, container, mount, privilege, controller or cleanup ran.
