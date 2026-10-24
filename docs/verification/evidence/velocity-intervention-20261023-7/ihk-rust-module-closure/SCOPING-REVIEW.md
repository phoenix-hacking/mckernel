# IHK native Rust module closure: bounded source review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only source/evidence review, 2026-10-24 UTC. No compiler, module load, root,
guest, workload, model call or canonical edit was performed. Shared dirty sources
and the six M14 implementers remain untouched.

## Finding

The three custom Linux drivers already have native Rust implementations. Current
`host-kernel/kbuild/Kbuild.in:6-10` selects `ihk.o`, the Rust
`ihk_smp_x86_64.o` composite, and `mcctrl_rust.o` plus
`mcctrl_vm_write_compat.o`. The only project C translation unit selected by this
Kbuild is `host-kernel/native-rust/mcctrl_vm_write_compat.c`. Its entire executable
content is three one-call functions:

| Project function | Linux operation |
| --- | --- |
| `mckernel_inherited_mmap_write_lock(mm)` | `mmap_write_lock(mm)` |
| `mckernel_inherited_mmap_write_unlock(mm)` | `mmap_write_unlock(mm)` |
| `mckernel_inherited_vma_start_write(vma)` | `vma_start_write(vma)` |

These are Linux ABI adapters, with no project validation, routing or ownership
policy. Their Rust callers in `mcctrl_vm.rs:198-206,244,272,411-439` retain project
MM/VMA orchestration, including RAII unlock, inheritance and invalidation. Thus
zero remaining substantial project C policy is visible in this selected link
list, but three project-authored C wrapper bodies remain. This is not a
whole-repository C inventory or whole-functionality completion claim.

The retained upstream `ihk/linux/` and `executer/kernel/mcctrl/` C/helper profiles
are separate compatibility implementations; presence on disk does not select
them into the native Kbuild. Linux itself, Linux headers/inline implementations,
and generated `.mod.c`/module metadata are distinct from these three project C
functions. Rust `extern "C"` declarations alone are not C implementations.

Root AGENTS explicitly permits these wrappers under the existing functional
scope. The native staging README/final-push zero-project-C criterion is stricter.
The user's new explicit M15 request makes this narrow residual language closure
a distinct objective; it does not justify rewriting existing Rust drivers.

## Existing artifact/native evidence and its boundary

The Oct19 actual-three-module artifact review reports successful real full-SDK
Rust compilation of all three crates, strict compiler dependency closures,
modpost and matching module identities for pinned Linux
`6.12.0-211.44.1.el10_2.mckernel1.x86_64`. It explicitly sets
`implementation_ownership=false`, `native_acceptance=false`, and
`module_load_acceptance=false`; it is not a current zero-C proof.

The associated usable-profile recipe joins separate artifact, ABI, semantic and
physical evidence for one exact tested configuration: one native lifecycle,
two overlapping applications with exit codes zero, both McKernel CPUs used,
and procfs empty after retirement. It grants no new Rust-path or C-retirement
credit and cannot be generalized to arbitrary current working-tree sources.

The current68 retained `accepted-Kbuild-MODULE-cfg/Kbuild` already selects the C
shim composite. Its SDK-v3 source-integration review is source acceptance only:
production compile/module and native acceptance remain false. Do not treat the
older Rust-only `mcctrl.o` command as proof of the later composite or claim a
new current-shim native result from these records.

## Exact pinned API assessment

Inspected the retained SDK source/build from the accepted Oct19 mount authority:
`scratch/mckernel-exact-candidate-scratch-22-authority3-output`, with source
`linux-6.12.0-211.44.1.el10_2`. Its Rust kernel has no MM/VMA module or ready-made
write-lock API. Generated `build/rust/bindings/bindings_generated.rs` contains
none of `mmap_write_lock`, `mmap_write_unlock`, `vma_start_write`, or
`vma_end_write_all` as callable functions.

`CONFIG_PER_VMA_LOCK=y` and `CONFIG_TRACING=y`. In the exact headers,
`mmap_write_lock` performs tracing, `down_write`, and sequence-count begin;
unlock performs tracing, sequence-count end/release of all VMA write locks,
and `up_write`. `vma_start_write` checks the current sequence, takes the VMA
rwsem and publishes the VMA lock sequence with `WRITE_ONCE`. Replacing these
with only `down_write`/`up_write` changes behavior.

The SDK bindings and Module.symvers do provide `down_write`, `up_write`, the
three `__mmap_lock_do_trace_*` functions and exported tracepoints. A small
project-local Rust transcription using those lower primitives may therefore be
possible without a Linux kernel change. This review has not established full
seqcount/barrier, tracepoint-enabled and configuration equivalence, so it does
not certify that route. There is no verified drop-in existing Rust API. The
first implementation task must settle those exact semantics against the pin;
retain the working C wrappers until then. Do not move them into Linux or
silently select another kernel to claim project Rust closure.

## Recommended M15 subgoals

1. **M15-01: bind the selected closure.** Freeze canonical Kbuild, staging inputs,
   exact SDK/config, all three roots/transitive sources and active module tuple.
   Enumerate these three wrappers and distinguish old native evidence from the
   current source generation. Reuse existing native Rust bodies.
2. **M15-02: replace mmap write lock/unlock.** Implement and independently review
   exact paired Linux semantics in a private Rust candidate, preserving the
   existing `InheritedWrite` lifetime. Settle tracing, sequence-count barriers,
   lock ownership and configuration requirements before integration.
3. **M15-03: replace VMA start-write.** Implement/review exact idempotence,
   VMA-rwsem/sequence publication and caller preconditions in Rust. Preserve
   inheritance/invalidation ordering; no compute-C or new project C body.
4. **M15-04: production integration and module proof.** Remove the C leaf from
   Kbuild/staging only after accepted replacements. Compile all three modules
   through the pinned SDK; retain exact compiler/link closure, module ABI/CRCs,
   imports and generated metadata classification proving no project C object.
   Couple the reviewed source/build changes; do not count source-only removal.
5. **M15-05: matching native functional proof.** Reuse M03 mapping/invalidation,
   M05 lifecycle/restoration, M06 fork/exec/wait/inherited-map paths and M08
   module/interface cases, plus M09/M11 changed-boundary integration, with the
   exact new module set and compatible image. Cover success/error cleanup and
   exercised wrapper successors, then ordinary unload/retirement. Existing
   Oct19 usable-profile behavior is reusable baseline evidence, not sufficient
   branch coverage for every wrapper. Keep whole-file/runtime credit open until
   matching native observations pass.

M15 should stay separate from M14's six compute C files and the35 functional
checks. It is three thin C-body retirements plus exact module/native closure,
not three new Rust driver ports and not a second broad functional campaign.
