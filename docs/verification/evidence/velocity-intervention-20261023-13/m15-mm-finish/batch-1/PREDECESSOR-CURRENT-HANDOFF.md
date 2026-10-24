# M15 MM lane: actual source candidate and executable ordinary-fixture handoff

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source candidate only. No compiler, objtool, linker, fixture executable,
root, Docker, module or guest was invoked by this lane. The earlier
BLOCKED-PROPOSAL and original raw/reference sources remain preserved as history.

`mcctrl_mm_write_candidate.rs` now implements all three actual operations.
Explicit x86 assembly reads/writes the shared sequence words, so concurrent
Linux word access is not expressed as a racy Rust reference or Rust load/store.
It uses wrapping u32 arithmetic, one aligned mov for WRITE_ONCE, and an empty
side-effecting assembly memory clobber for the exact no-KCSAN x86 smp_wmb.
Additional compiler clobbers are stronger than the original unmarked accesses;
independent semantic and emitted-code acceptance remains required. The safe
caller context and error/lifetime handling remain with the existing Rust MM
owners. There are no allocations, new errors, reference transfers or C fallback.

`m15_mmap_trace_gates.S` implements three gate functions with the retained
HAVE_JUMP_LABEL_HACK initial jump, aligned16-byte relative __jump_table entries,
key symbol + tracepoint.key offset8 + HACK flag2, and special-data annotations.
Production uses the pinned Linux SYM_FUNC_START/END, ENDBR and RET macros.
The Rust body retains the outer enabled gate and exported Linux helper call;
the Linux helper retains its own inner enabled check. No polling replacement
or unconditional trace-helper call is used. Rust/C witnesses enforce offset8.
The object must pass the pinned objtool rewrite before it is a default-false
kernel gate. Unprocessed raw jumps are never proposed as loadable module code.

The actual-source ordinary consumer consists of fixture_root.rs,
fixture_bindings.rs and fixture_driver.c. It links the unchanged original C
wrapper with the13 previously byte-extracted original Linux inline bodies,
and links the same proposed Rust bodies under a test-only bindings/gate shim.
It compares every ordered callback event and final state, then checks the22
independent vectors. Shared-word assembly still executes in this fixture;
only the lower MM primitives, trace enable gates and barrier observation are
mocked. Repeated epochs and4 invalid schedules are included. It does not
qualify Linux concurrency, production bindings or actual kernel tracing.

The separate executable gate microprobe uses the same assembly jump/table
body with user-mode linkage. It validates actual ELF key relocation/symbol/
addend/alignment and special-data metadata, then invokes retained objtool's
--hacks=jump_label conversion. Separate consumers check raw jumps return true
and processed NOPs return false. It captures both objects and narrow assembly
readbacks. This tests the mechanism; production Linux linkage/RET/ENDBR,
actual module preprocessing and runtime text patching remain separate.

`run_candidate_fixture.py` is ready for one fresh ordinary campaign grant.
`ORDINARY-FIXTURE-PROFILE.json` binds the exact runner argv, tools and1CPU/1GiB
profile. It preserves the first failure and stops without retry. The runner
checks CANDIDATE-INPUTS before compiling anything. Source-only Python parsing,
JSON decoding and source-byte checks were performed; no executable result is
claimed. An incompatible retained objtool executable is a preserved tool-boundary
failure, not authorization for another environment or root/Docker work.

Four qualification unknowns remain: (1) independent acceptance of the
jump-label assembly mechanism; (2) independent acceptance of the raw-access /
LKMM barrier argument; (3) actual ordinary fixture and exact-SDK layout,
leaf codegen, object processing and three-module link/ABI results; (4) matching
native inherited-map/invalidation and lifecycle proof. Their implementation
absence is addressed by concrete source, but none receives passed proof here.

`sdk_leaf_probe.rs` emits three real-SDK ABI consumer functions without module
initialization or execution. layout_witness_v2.c adds exact key/sequence-alignment
preconditions to the preserved23-word C/Rust witnesses. Compile those only via
a separately reviewed derivative of the retained SDK commands and matching
kernel.rmeta. This ordinary fixture command is not a substitute for that stage.

After independent source/fixture acceptance, root integration should include
this Rust module once, replace the three mcctrl_vm.rs C extern calls with its
typed Rust functions, add the reviewed gate assembly object and remove only
mcctrl_vm_write_compat.o from the current composite Kbuild/staging closure.
Preserve mcctrl_rust.o and the existing cfg controls. Exact all-three-module
proof and reused M03/M05/M06/M08 plus M09/M11 changed-path native checks precede
C-retirement credit. No canonical file has been changed by this lane.
