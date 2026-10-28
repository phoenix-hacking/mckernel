Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private next117 composition is the two reviewed increments only: F03 perf_mmap
279df47b and F06 vdso_get_vdso_info fda8e9c7, based on Root-adopted116 ef82f328.
Accepted production remains CURRENT115. CURRENT116 build inputs are preserved;
this private source-ahead candidate is not a CURRENT116 hot edit or new runtime.

SELECTIVE-SEVEN-SOURCE-MAP.json supplies exact canonical adopted116 preimages,
private postimages and additive patches for Root. Seven changed paths: generic C,
arch C, shared Rust union, new f06 Rust child, CMake and the two existing origin
producer/profile files. The unchanged three paths from116 adoption remain exact.
No C implementation is expanded. The existing C do_mmap provider, C-owned VDSO88B
allocation/state bridge and new immutable C perf binding40B remain explicit debt.
The original selected C bodies remain under their opposite fallback selectors.

The shared Rust patches commute exactly in both orders. The existing complete
perf_mmap_body_result and six argument getters are reused. Generic VDSO setup
uses the new public legacy body; native setup retains the exact existing private
initializer and separate native_vdso protocol. The additional module is selected
only through the same supported x86/Linux6.12/non-UBSAN CMake branch and paired
f06_vdso_info_candidate/MCKERNEL_RUST_F06_VDSO_INFO. Perf remains on existing
enable_perf/ENABLE_PERF and Rust-helper gates. No profile is widened.

MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json reuses the reviewed116 recipe:
full Rust, selected generic C TU, selected arch C TU, exact eleven-input raw link.
Only one Rust cfg and one arch C define are added. All eight retained object refs
and their bytes remain unchanged; there is no SDK/compiler/archive replay or
broad rebuild. Root must source-adopt/bind/export/review/admit this candidate
separately before any command. A fresh origin output is required for this actual
source/profile; the existing origin algorithm changes only its one exact profile
hash. No origin producer was executed here and no historical output is relabelled.

RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json reuses all121 baseline directory
file references and adds one exact child file, replacing only syscall_policy.
The directory contains111 .rs files among122 total files (baseline110 .rs among121);
these counts describe a compiler source closure, not a language-migration score.
All three existing external relative module references remain retained. Root may
materialize the reference overlay normally; this lane copied no full subtree.

Desired C-function delta is exactly2 relative to116, pending actual compile/link:
remove selected C perf_mmap and vdso_get_vdso_info, add their Rust public owners.
Count no actual C retirement/default/native/file delta at source composition.
Required production ownership checks before acceptance:

- Generic selected TU has no defined perf_mmap; descriptor installation resolves
  to one Rust f03_perf_mmap_v1. Perf-disabled and helper-off fallbacks remain sane.
- New immutable C f03_perf_mmap_binding_v1 is honestly counted as a C data object,
  reprC40B with do_mmap pointer at32. Compile actual headers for MAP_ANONYMOUS,
  PROT_WRITE, data_head/capabilities offsets and bit2; verify the provider relocation
  still names original do_mmap. C do_mmap remains selected, unrelated C debt.
- Arch selected TU has no defined public vdso_get_vdso_info; Rust has exactly one
  unmangled public definition. Verify state bridge, packet preparation, IKC send,
  current CPU and pause imports/calls and complete real ABI (ArchVdso88B/align8,
  IkcScdPacket128B/align8, Ddebug32B/align8). HOST cfg(test) did not cover production
  wrappers/log code: full production crate/TU/link checks must cover them now.
- Two original C VDSO debug descriptors are replaced by exactly two Rust-owned
  __verbose records. Verify function/format strings, flags0, file/line provenance
  in /src/kernel/rust/f06_vdso_info.rs and actual linked registry count/consumers;
  both unconditional error strings stay active. New metadata is not silently
  equated to the original C-file line ownership.
- Preserve current complete syscall registry, inherited providers and direct or
  folded caller proofs. Verify exact final-image values and unique providers.
  Matching supported native/application/lifecycle proof remains a separate gate.

Pure source controls cover real union/inverse, hunk ordering, independent reviews,
unique exact patch preimages, duplicate application, missing header binding,
retained-object removal, extra command and origin-profile drift. Original test
mutation-path failure and source are preserved; its bounded correction changes
only the path filter so it actually exercises the canonical source input.

This package contains no account/window/clock/nonce/grant/controller changes,
compiler commands, Docker/root/guest actions or release. Root alone owns canonical
integration, current consumer evidence, resource/admission and independent review.
