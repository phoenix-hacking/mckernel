# Current110 production cutover operation is ready for focused review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

`EXACT-PRODUCTION-OPERATION.PROPOSED.json` freezes one existing pinned
4CPU/12GiB production image operation with fresh private output. It uses the
**current110GiB scratch profile**. Pending142GiB maintenance is separate and is
not a prerequisite. Root must supply the normal fresh identities, aggregate
capacity/full current sparse gap, physical predecessor and one-shot release
after focused independent source/data review. Yield to any eligible critical
235/227 operation. No compiler, build, root, Docker or guest ran in this task.

The exact outer command is the existing owner interface, with the new private
owner and root-created final request:

```text
/home/holden/anaconda3/bin/python3 -I -B /home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2/native_rust_exact_mckernel_image_container_owner.py /home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2/image-request.FINAL.json
```

The coherent source is under HOST `production-combined-2/source-materialization-attempt-2/materialized-source`.
The copy/hash and names/type/mode closure passed for the same6,959 entries,
6,910 private regular files and49 retained symlinks. It increments the accepted
idle+memory source by only the two latest canonical memory postimages. Relative
to frozen10972, the exact source delta remains five files:

| Source | Exact prepared SHA256 |
|---|---|
| `kernel/process.c` | `7203019d2ba8143f9240a03d11bc8c5cfcd495d89183aa7ab643c6159a6bd02d` |
| `kernel/rust/sched_helpers.rs` | `449df570965855f992a0fe024fca7cd6527b20622b4b8e3b33af04900b02e923` |
| `kernel/include/sched_helpers.h` | `9712a3df59eb0251f517ce01254e4576119868924b35f7da6fbee294bff966ae` |
| `arch/x86_64/kernel/memory.c` | `95bb6a4a916a802e98eb9f7eac98eef990d6f75a3e42b06f29ac0a73ef2a452b` |
| `kernel/rust/x86_memory_helpers.rs` | `689b9741821609a7c2e3aadb8cd46b0dbc57948090b38758f0b3eb120a5297fb` |

Manifest SHA256 is `9b86c84a92133678171b3e476560bcdfc99070f727b9c11c764de7092de8b88c`;
derivative `0de61193133a82b41772fc6ad1c0ccdcb07d5820d1a200f7259c9a7654e0d136`;
materialization `10d314578ce3225d450fbf5d3b39946d10d51f6c020d5a04f19eee7d4abba123`.
The retained base Git commit identifies provenance, not this derivative.
Accepted FP/post-switch/CPU/process fixes and all other known source bytes are
preserved. Canonical source, frozen10972 and its build output were not changed.

The existing production chain advances through three small reviewed-source
successors, with exact diffs retained here:

- Provenance `1be3a017e2ae47a0d1ecfcd4e1d22d7d8d569808e495d2b6d055c851d0582ae2`
  changes only exact thin-schema/manifest admission.
- Image driver `46b426530bbde4054d19af52fc815aece237e20b84031a2594c1575a0dbe5942`
  advances the old process/scheduler pins and authenticated provenance hash,
  pins the five exact source postimages and adds focused M14 observations.
  All existing FP, lifecycle, fork, affinity, ABI, toolchain and link gates remain.
- Outer owner `e95e41a3fe7d3abadf996b16414312cb943627773ce78bf50df2c9039009d4ce`
  binds the new driver/provenance path/hashes, uses a fresh common exclusion
  namespace and explicitly rejects the prior namespace. Resource/ownership/
  retirement controls and fixed host owner are unchanged.

The supplemental libdwarf manifest now binds the new base manifest hash;
its consumed Git commit/tree/content/toolchain authority is unchanged.
The fresh static request is
`image-request.STATIC-DATA.expert-compact1.json`,26,524,647bytes,
SHA256 `b4f18e1f97cb8c1657a1b803a84fcde3fe25124da93569c0df4f054fc3b78b33`.
`REQUEST-FIELD-DELTA.json` names every changed field. Full retained inventories,
toolchain and library inputs are reused. Typed-null live identities remain
unreleased; do not execute static data.

The smallest new compile within the existing operation is **one actual selected
GCC14 memory.c translation unit** using its generated command, including the
paired layout/flag witnesses. Preprocessing must exclude the old C action,
output adapter and physical-to-virtual adapter bodies. The existing actual
selected/fallback process TU and native/legacy full Rust gates are reused;
no new helper/vector suite or duplicate full Rust compile was added. The existing
`mckernel_rust_obj` and default `mckernel.img` targets then prove the actual
default process/memory imports/relocations, unique Rust/final exports, no final
undefineds, and object stability through receipt publication. New proof is
stored as `m14-combined-default-link.json`; native execution remains separate.

| Body displaced by the five source postimages | Explicit remaining boundary |
|---|---|
| Idle initialization/iteration/infinite orchestration and exact-running scan | C entry/descriptor producer and existing scheduler/lock/IRQ/halt/allocator primitives remain |
| Clear-range old-PTE snapshot/output/lookup/membership orchestration and output adapter | C page-table callers, private-layout declaration/witnesses, established page lookup/effect/allocator/hash/lock primitives remain |
| Selected C physical-to-virtual forwarding callback | New Rust callback reuses existing Rust `phys_to_virt`; other memory callbacks and broader area remain |

Earlier108 idle cases,129,888 memory vectors, six CPU-bridge cases and the latest
actual GCC9/Rust-module partial link remain their exact prior evidence; none
was rerun. They are not pinned full-crate/default-image/native acceptance.
No full M14 area, whole-file, zero-C, whole-kernel Rust percentage or practical35
closure is claimed.

The exact pinned nightly1.95 compiler is also retained on HOST, SHA70ebcbba,
with its same original sysroot. `EXACT-PINNED-HOST-RUST-CANDIDATE.CORRECTED.NOT-RELEASED.json`
contains a correctly split argv (no shell), explicit fresh HOST cwd/output,
unchanged compiler/sysroot/target/cfg/codegen flags and the exact mount remap.
The accepted baseline full Rust object is13,599,104bytes, below32MiB, matching
both actual stat and its receipt. However the production recipe has **no
explicit CGU1 flag**, so compatibility with the ordinary one-job/2GiB profile
is unproved. Do not add CGU1 or run it without a new compatible grant and CPU0
SDK-preparation whole join. The selected operation remains the existing pinned
container route.

Failure history is retained: initial8MiB source-manifest EFBIG, successful fresh
32MiB source-copy correction, then pretty static-request EFBIG at32MiB. Expert
prescribed compact serialization of the same object in a fresh filename,
without recopy/regeneration or limit changes. Its complete bytes were bounded
before exclusive creation, fsynced, reread/hashed and canonical-roundtrip checked.
Both truncated files/raw errors remain on HOST. The unexecuted host argv first
proposal retained a Make shell cwd prefix; its source-only correction validates
and extracts that exact prefix and rejects remaining shell operators/variables.
Neither metadata defect was an executed compiler or kernel failure.
