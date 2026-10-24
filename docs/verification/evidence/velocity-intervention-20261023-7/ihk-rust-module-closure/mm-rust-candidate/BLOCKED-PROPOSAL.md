# M15 MM-wrapper Rust successor: concrete, not yet implementable with justified semantics

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source preparation only. Current production C wrappers remain untouched. No
compiler, linker, module load, root, guest or workload was invoked.

The proposal is one local Rust module replacing the three wrappers, with exact
pinned Linux operations and small Rust inline-assembly mechanisms where needed.
There is no justified production implementation yet: the retained SDK provides
no callable mmap/VMA write wrappers or Rust static-key helper. Supplying code
that merely calls down_write/up_write or unconditionally calls tracing helpers
would conceal unresolved behavior, so no such candidate is included.

## Exact interface and source mechanism that must be settled

Use the retained `mckernel-exact-candidate-scratch-22-authority3-output` source,
config, generated bindings and export table, not another kernel. The pin has
X86_64/SMP/PER_VMA_LOCK/TRACING/TRACEPOINTS/MEMCG/JUMP_LABEL and
HAVE_JUMP_LABEL_HACK enabled; KCSAN, DEBUG_VM, DEBUG_LOCK_ALLOC and PREEMPT_RT
are disabled. These details are checked by `prepare_fixture.py`.

The production-local interface can remain typed Rust, with no new kernel export:

```rust
unsafe fn mmap_write_lock(mm: *mut kernel::bindings::mm_struct);
unsafe fn mmap_write_unlock(mm: *mut kernel::bindings::mm_struct);
unsafe fn vma_start_write(vma: *mut kernel::bindings::vm_area_struct);
```

It needs two mechanisms absent as ready-made helpers in this Rust API:

1. Three compile-time-symbol trace gates, one for each exported mmap tracepoint.
   Exact C `tracepoint_enabled` uses `static_key_false`, which on this pin is
   `arch_static_branch(key, false)`. The x86 header uses asm-goto, an initial
   jump that objtool changes to a NOP, and `__jump_table` entries with the
   HAVE_JUMP_LABEL_HACK key adjustment `+2`, alignment and special-data
   annotation. A function receiving an arbitrary runtime key pointer is not a
   substitute for the original immediate-symbol mechanism. The local Rust
   macro/inline-assembly equivalent must be accepted against this exact header
   and emitted object. `static_key.enabled` polling is not proved equivalent.
2. Raw aligned u32 accesses with Linux-compatible sequence-count write barriers
   and WRITE_ONCE behavior. Exact x86 `smp_wmb` reduces to a compiler memory
   barrier on this no-KCSAN configuration. Rust raw-field/volatile accesses and
   an explicit compiler memory-clobber barrier need a justified FFI/LKMM
   argument and emitted-code evidence; a Rust atomic/compiler_fence choice is
   not automatically equivalent. Never create an exclusive reference to the
   entire concurrently observed MM/VMA object.

`down_write`, `up_write`, all three `__mmap_lock_do_trace_*` functions and
tracepoint symbols already have bindings and Linux exports. No Linux source
change is shown necessary, but this is not proof of a working local solution.
The existing exported trace helpers themselves retain a second enabled check
under MEMCG. Preserve both gates, including transitions between their reads.

Exact body order must remain:

- Lock: outer start gate/helper; mmap rwsem down; wrapping u32 sequence increment;
  smp_wmb; outer acquire gate/helper with write=true, success=true.
- VMA start: snapshot its owning MM sequence under the caller's mmap write lock;
  return if equal to VMA sequence; otherwise VMA rwsem down; single aligned
  WRITE_ONCE of that sequence; VMA rwsem up.
- Unlock: outer released gate/helper; smp_wmb; wrapping u32 sequence increment
  releasing all VMA write epochs; mmap rwsem up.

The wrappers return `()` and have no errno path. Keep their original valid/live
pointer and lock preconditions; add no allocation, ownership transfer, new error
branch or unrelated policy. Existing CurrentMm and InheritedWrite ownership in
mcctrl_vm.rs must continue to hold MM lifetime and balanced unlock across errors.

## Real original-body fixture material prepared

`generated/original/` contains unchanged byte copies of the actual project C
wrapper and header. `generated/original_linux_mm_bodies.h` contains13 exact
function definitions extracted from the pinned Linux headers, including the
actual sequence-count increment and VMA idempotence branches. The preparation
record binds each extracted body and the original wrapper. This avoids a
hand-written C algorithm serving as its own reference.

`fixture_runtime.h` supplies test-only reduced object types and lower-primitive
callbacks. The generated Linux include headers let the original wrapper C
translation unit compile unchanged. This is an oracle fixture, never production
C. Callback implementations and the executable comparison driver are still to
be supplied together with the actual Rust successor. They must maintain one
ordered log, scripted independent outer/inner gates, per-object lock identity,
sequence observations at barriers, and WRITE_ONCE values. Compare original C
against the actual proposed Rust source; a Rust model is insufficient.

`FIXTURE-VECTORS.json` supplies22 explicit state/event vectors: empty, balanced
lock/unlock, first VMA write, idempotence, two VMAs, u32 wrap, all8 outer tracing
masks and7 additional inner-gate masks. It also specifies repeated epochs,
independent MM objects, per-gate transitions, exact trace arguments, and invalid
schedules rejected before FFI. Compare complete logs and final state to each
other and the stated independent expectations. Null/dangling-pointer executions
are excluded because the original API does not define them.

`layout_witness.c` and `layout_witness.rs` emit the same23-word layout vector for
real pinned MM, seqcount, VMA, VMA-lock, rwsem, tracepoint, static-key and
jump-entry types. Compile these with the actual saved SDK flags/kernel.rmeta;
compare emitted constants without running a kernel module. The mocked fixture
layout is intentionally separate and cannot establish real SDK ABI correctness.

## Next command, prerequisites and remaining unknowns

The exact next unprivileged compiler command is the original-C fixture leaf
compile in `NEXT-FIXTURE-COMMAND.json`. It is proposed, not executed or released.
It requires dispatcher approval of an ordinary compiler slot, frozen source
readback, resolved `/usr/bin/cc` identity and the stated bounded profile. This
first command only validates the real C reference's mocked include surface; it
cannot produce Rust-equivalence or module credit. The preparation script has
already run once; use a fresh output directory for any subsequent preparation.

There are **4 remaining unknowns**: (1) accepted Rust jump-label mechanism;
(2) accepted Rust/LKMM raw-access and barrier mechanism; (3) actual-successor
fixture comparison plus exact-SDK layouts/codegen/module link; (4) exercised
native inherited-map/invalidation/lifecycle behavior with the new module tuple.
The first two block a justified source implementation. The other two block
retirement credit. No fixture, layout witness or native result is claimed.

After source and ordinary-fixture acceptance, include the new Rust module once
in mcctrl, replace its three C extern calls with typed local Rust calls, remove
only mcctrl_vm_write_compat.o from the composite Kbuild, and update staging's
source closure coherently. Preserve mcctrl_rust.o naming and current cfg controls.
Compile all three modules through the existing pinned SDK and verify exact
imports/CRCs/link ownership. Then reuse M03/M05/M06/M08 and M09/M11 functional
cases for the changed paths with the matching image/modules. No Linux-C
relocation, alternate-platform header or fallback body earns this closure.
