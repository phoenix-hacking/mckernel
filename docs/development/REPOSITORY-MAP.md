# Repository map

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Start with [README.rst](../../README.rst) for the system description and
[AGENTS.md](../../AGENTS.md) for current working constraints. The active functional
plan and acceptance state live in
[the milestone directory](../verification/os-milestones-20260914/README.md).
Use its CURRENT/START and M14/M15 records when choosing work; this map does not
replace their acceptance contracts. Rust conventions are in
[RUST-STYLE.md](RUST-STYLE.md).

## Source and interfaces

| Path | Responsibility |
| --- | --- |
| `kernel/`, `kernel/rust/` | Compute kernel, current C/Rust transition, Rust implementations and ABI declarations. |
| `arch/x86_64/`, `arch/arm64/` | Architecture interfaces, entry/low-level code and reviewed assembly. Current qualified target scope is determined by the active plan. |
| `host-kernel/native-rust/` | Project host runtime Rust: IHK/SMP/mcctrl models and native integration. |
| `host-kernel/kbuild/`, `host-kernel/rocky/` | Host build integration, pinned target/toolchain inputs and compatibility patches. |
| `host-kernel/contracts/`, `host-kernel/reference/` | Host-facing contracts and retained reference inputs; preserve exact bindings. |
| `ihk/` | Separate IHK Git submodule, with its own revision and source ownership. |
| `executer/kernel/`, `executer/user/` | Host module integration, launcher and custom user runtime; Rust lives in the existing `rust/` directories. |
| `lib/`, `tools/` | Custom library interfaces and utilities, including Rust tool ports. Live C here remains subject to M15 accounting. |
| `cmake/`, root `CMakeLists.txt` | Existing build graph and Rust/C selection. Source location alone does not establish which implementation executes. |

## Workflows and retained records

| Path | Responsibility |
| --- | --- |
| `scripts/` | Build, orchestration and verification entry points; keep frozen command and resource controls intact. |
| `scripts/tests/`, `scripts/application-tests/`, `kernel/rust/tests/`, `test/` | Existing functional checks, fixtures, workloads and independent equivalence inputs. |
| `docs/verification/os-milestones-20260914/` | Active goal, current handoff and M14/M15 cutover worklists. |
| `docs/verification/evidence/`, `evidence/` | Retained source-bound results, original failures and snapshots; not a source refactoring target. |
| `docs/spec/`, `doxygen/`, `docs/locales/` | System documentation and documentation tooling. |
| `/home/holden/mckernel-work/host-preparation/` | Private candidate preparation, outside the canonical checkout. |
| `/home/holden/mckernel-work/scratch/`, retained candidates and mounted workload paths | Owned work/output trees; disposition follows current ownership and retention records. |

The functional source boundaries above take inspiration from the small, visible
top-level separation of runtime, shared interfaces and build entry points in
[the reference Rust kernel repository](https://github.com/gamozolabs/chocolate_milk).
Its build system and target choices are not requirements for this project.

## Staged cleanup

1. Add this index, the Rust style document, explicit stable formatter config and explicit-file
   checker. Link them from README. Preserve all existing source and evidence paths.
   No format-all command or automatic CI tree-wide gate is part of adoption.
2. As each owned M14/M15 body changes, apply the style only to its reviewed source
   diff. Keep source-selection, ABI/build/native results and remaining C debt in
   the current worklists. Resolve actual compiler/functional failures first.
3. After active ports qualify and shared-file ownership is released, propose one
   cohesive leaf extraction at a time from `kernel/rust/syscall_policy.rs`,
   `process_helpers.rs`, `mem_helpers.rs` or `sched_helpers.rs`. Keep exported names,
   visibility, cfgs and module order. Update the explicit CMake source list and
   fixture include paths together, then obtain applicable equivalence/build/link
   and native proof before integrating. Do not split these shared files during
   concurrent migration simply to make them smaller.
4. Improve entry-point documentation in place. Any later directory move requires
   its own source-owner proposal listing build consumers, relative includes,
   script references and evidence pins. Keep historical records at original paths;
   add an index or successor record instead of moving archives or failed results.

This sequence preserves dirty work in progress and frozen snapshots. There is no
archive deletion, automatic directory migration or new Cargo workspace implied by
this map. The active build graph remains authoritative.
