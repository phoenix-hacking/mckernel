# Native image loader staging integration — 2026-09-07

The recovered image loader is now declared in the native stage manifest,
Kbuild source closure, lifecycle contracts, and unsafe/FFI inventory. This is
a WIP integration checkpoint; the fresh declared-stage build, guest replay,
and full repository suite remain pending.

The stage includes the existing `ihk_mapping.rs` geometry and the new
`smp_image.rs` and `smp_loader.rs` consumers. Geometry reuse does not implement
the IHK-007 Linux user-mmap adapter. Its mapping gate credit remains forbidden.
The OS load callback retains its IHK lease, SMP module owner and operation
mutex, exposes Loading temporarily, and restores NotBooted after the backend
result. CPU startup is not implemented by loading an image.

The source ledger covers 154 sites across 18 sources. All previous site IDs
are retained; two existing callback bodies change and nine unsafe blocks are
added. Independent review and compiler expansion acceptance remain pending.
The standard exact-build workflow now runs image and OS adapter tests before
and after compilation, with the exact-compiler mapping fixture before staging.
Current workflow and license records follow these sources; historical evidence
is not rewritten as current acceptance.

Verification so far: 96 staging/link/source checks passed. The lifecycle and
mapping groups passed before a synthetic ledger fixture missed three new
support files. After fixing that fixture, the 30-check ownership/image/resource
continuation and the exact mapping fixture, OS contract and ledger checks
passed. The later mapping group passed with the workflow change. Downstream
workflow checks exposed two stale current identities; their corrections are
being verified. Every first failure is recorded in `kernel.log`.

The adjacent JSON checkpoint retains source snapshots, test logs and recipes.
The earlier successful loader guest remains separately recorded in
`native-image-loader-checkpoint-20260907.json`. McKernel boot, IKC, workloads,
Rust/assembly-only completion and production acceptance remain open.
