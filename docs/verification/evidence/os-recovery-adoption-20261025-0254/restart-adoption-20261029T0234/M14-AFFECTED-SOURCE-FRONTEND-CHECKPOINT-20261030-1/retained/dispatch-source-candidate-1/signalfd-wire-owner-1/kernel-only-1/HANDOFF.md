Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

M14 ONLY. Private owner /root/dispatch_source. Same-thread full-access/approval-never
confirmation remains recorded; no redundant permission recovery occurred. Only
private packet files were written, preserving the compositor and all other writers.
No test, prior passing projection replay, compiler, workload, native/model/root
launch or subagent action occurred. One source preparer path typo stopped before
output; its original script/error record is retained and the path was corrected
once to the exact compositor-supplied dispatcher root.

Active delivery is one exact-function patch:
SIGNALFD-EXPLICIT-WIRE.M14-ONLY.PRIVATE-NOT-APPLIED.patch
SHA256 059e16fb78465115ea906f6113441124978fc6483e6e8da9eff66fad0be871ce.
It changes only the already-Rust compute syscall_signalfd_create_bridge. The bound
passed actual 172-source parent is m14-combined-frontend-candidate-2/work-1/src,
syscall_policy.rs SHA aa751edb617692c1da8ed2fe59c897bb2e20e6357f8a3431a16d27443becadeb,
lib.rs SHA 8180e97b158ab48c64378082aeb8ef6b0c15761ad77c38ac78ffe833c95e70ab.
Original function hash 51eb544714c24f2e1fffe42aec22fff553b24767db59f11d3f6f5ab924f0a1bd;
new function hash 992e54553c00b817f89a0e741f5997ac1946fee645814604513c78a585e3a0d6.
The patch contains the unique complete function preimage, so the compositor can
apply it to a compatible later append-only descendant after checking that exact
function, without discarding another owner's later modules. No stale whole-file
postimage is supplied. INPUTS.json names exact real source/ABI/C declaration files.

The original retained C callback clears its whole request, then sets number,
args0=0 and args1=flags. The existing selected Rust callback likewise zeroed the
whole MaybeUninit storage first. Thus this function already has a defined wire
intent: number=syscall_nr as CULong, args=[0, flags as CULong, 0, 0, 0, 0]. This
patch preserves that vector with seven explicit raw field writes in naturally
aligned MaybeUninit<SyscallRequest>. The CInt-to-CULong number/flags conversions,
current processor lookup order, existing do_syscall call and CLong result are
unchanged. There is no new blanket zero-fill, syscall-number guard, errno, host
operation or arity assumption. The actual caller remains sys_signalfd4 ->
signalfd4_body_result -> syscall_signalfd_create_bridge with SYS_SIGNALFD4=289;
the existing host mode0 consumes only scalar mode/flags. No guest pointer-bearing
argument, descriptor, buffer mapping or ownership pin is introduced.

Focused initialization/ABI invariants:
- The actual selected Rust ABI defines SyscallRequest size72/alignment8 with rtid0,
  ttid4, valid8, number16, args24; its exact scalar fields cover bytes0..72. There is
  no internal/trailing padding in that selected layout. No request layout/type or
  transport-size change is made; cross-language selected-object proof remains at
  its existing accepted/pending scope, not newly supplied by this source patch.
- The old caller storage initially zeroed rtid/ttid/valid too. Those values are not
  caller-owned protocol data: syscall_offload_prepare_result writes rtid/ttid and
  response req_thread_status/pde_data; syscall_send_prepare_result writes caller
  valid=0 before copy. The sender copies the complete request into its separate
  packet and release-publishes packet valid=1. The new caller leaves these three
  fields to the same helpers; it does not read or form a whole typed reference to
  them before those writes. The same initialized request bytes reach the genuine
  first copy on the supported helper path.
- Every number/arg field is assigned individually through addr_of_mut!; no
  assume_init, whole SyscallRequest reference, response/packet/UTI zeroing or
  uninitialized-byte comparison is added. Existing sender packet padding handling
  and 128-byte packet semantics are untouched.
- Request stack storage remains borrowed throughout the same synchronous call.
  Current thread/process/monitor/stack/channel and completion/storage lifetimes
  retain their original separate contracts. Scalar fields and this initializer
  do not close global do_syscall/host-drain/UTI descriptor lifetime predicates.

The earlier host act_signalfd4 draft is excluded from this active patch and
explicitly deferred in ../M14-ACTIVE-M15-DEFERRED.md. Do not integrate/compile it
until original M14 supported-scope acceptance permits M15. Process-wide UTI static
descriptor/previous-state/outstanding-borrower holds, global do_syscall, exec,
exec-tail, ACK and direct-TID held selections remain unchanged. No C, CMake,
profile, host or other function is modified by this patch. New retirement credit,
new candidate builds and guest applications are all zero.

Next affected frontend: Root/compositor bind this one function change into the
actual passed 172-source root or its compatible current codegen successor, retain
the complete existing cfg/environment/tool tuple and choose a fresh private Rust
frontend output. The actual crate entry is kernel/rust/lib.rs; no new cfg or
selector is required. Existing m14_private_frontend/m14_typecheck_body_refs can
remain only where already admitted by the source owner. Root owns argv, tools,
source-map/effective-view custody, current-free/resources and operation admission.
Source preparation succeeded; no compile result or default/link/native acceptance
is asserted. READINESS-ROWS.json records the exact original C boundary, current
Rust path/hash, genuine prototype, provider gap and executable next step.
