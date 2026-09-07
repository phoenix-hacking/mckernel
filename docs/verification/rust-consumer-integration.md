# Rust consumer integration and remaining connections

The completion target is a Rust/assembly McKernel connected to the Rocky/Linux
6.12 control kernel. Every retained Rust implementation needs a known consumer
or an explicit pending integration task. Source presence, crate inclusion,
symbol linkage, and runtime acceptance are different levels of evidence.

The existing [preservation baseline](rust-reuse-baseline-24a151fe.json) remains
immutable. The current file-level inventory is recorded separately; modified
and added sources must remain visible rather than rewriting that baseline.

The [2026-09-07 inventory](rust-consumers-20260907.json) accounts for 130 files:
121 unchanged from the baseline, eight modified, one added, and none removed.
It checks all 64 core files against the crate and CMake dependencies, and the
14 native files against the staging/module graph. Its configuration identity
records the selected Rust, QLMPI and UTI flags. These are source/build checks.

## Current build boundaries

| Source | Current consumer | Remaining integration |
| --- | --- | --- |
| `kernel/rust/*.rs` | One McKernel crate rooted at `lib.rs`, selected by the compatibility image build | Retire remaining C implementation and boot through the native Linux 6.12 modules. Conditional module bodies still follow the selected configuration. |
| Native IHK/SMP/mcctrl roots and staged support modules | Native Kbuild module graph | Complete memory/resource assignment, boot and IKC/workload paths. Compiling a policy module does not establish live use of every capability. |
| `host-kernel/native-rust/ihk_mapping.rs` | Existing mapping checker and fixtures | Connect the retained model to native mapping and generation-checked OS ownership. It is currently absent from staging. |
| `executer/kernel/mcctrl/rust/mcctrl_helpers.rs` | Existing compatibility mcctrl module | Adapt useful Rust bodies to native Linux services and replace their project C bridges. Native `mcctrl.rs` does not import this file today. |
| Six common Rust execution/tool sources and `mcstat.rs` | Default compatibility user-tool targets | Validate these consumers against the native host implementation. |
| Four QLMPI and two UTI Rust sources | Optional build branches | The current compatibility configuration disables both features; preserve the branches and validate them when enabled. |
| `tools/mcstat/rust/runtest.rs` | Explicit `mcstat_runtest` target, excluded from the default build | Invoke this target explicitly when checking monitoring behavior. |
| `tools/mcstat/rust/mcstat_helpers.rs` | Historical equivalence-harness consumer | Compare and consolidate duplicated policy with active `mcstat.rs`; no complete equivalence or retirement is claimed yet. |
| Crash-extension Rust | Separate `mckernel.mk` extension build | Validate with the required crash headers. CMake copying the source is not a successful extension build. |
| `scripts/tests/**/*.rs` | Verification fixtures | Keep separate from production implementation and its language measurement. |

The two IKC endpoints run in different kernels. Preserve their common protocol
while respecting each side's memory, locking, and lifetime rules. Combining
them into one crate is not itself an integration requirement.

## Concrete build repair

`kernel/rust/hash.rs` was already included by `mod hash;` and compiled into the
Rust object, but CMake omitted it from `RUST_KERNEL_SRCS`. A change to this file
could therefore leave the object stale during an incremental build. Adding its
existing path to the dependency list preserves the implementation and ensures
the normal Rust build rule sees changes. This repair is not additional Rust
language ownership or native boot progress.

The isolated four-CPU compatibility check reproduced the missing rebuild with
the original rule, verified the corrected generated dependency, then rebuilt
the actual object and image after touching `hash.rs`. Both retained identical
SHA-256 bytes. The [verification record](rust-consumer-verification-20260907.json)
binds the recipes, before/after generated rules, configuration and logs.
The build still reports 17 existing warnings in other Rust ABI declarations;
no new guest boot or complete ABI closure is claimed.

## Required closure

Before declaring unification complete, resolve every pending production row,
retain a verified consumer or replacement for each useful legacy body, check
the shared ABIs and protocols, and pass native boot/workload/shutdown tests.
Optional features and comparison fixtures remain explicitly accounted for.
The final image and supporting kernel behavior must also pass the separate
[Rust/assembly acceptance checks](mckernel-rust-assembly-completion.md).
