# Coherent idle consumer source prepared; pinned build remains unreleased

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The private successor is materialized at
`/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-consumer-1/materialized-source`.
It contains all 6,959 retained entries from the actual frozen10972 source
(6,910 private regular files and49 tracked symlinks), with exactly the three
root-integrated idle postimages. Copying verified each source's bytes against
the exact authority, preserved modes and IHK metadata, and recorded its entry
in the retained journal. The final names/type/mode closure passed. The active
image, original source, accepted build output and canonical sources were not
changed by this preparation. The previously accepted CPU/process correctness
fixes are retained through the selected complete source authority and exact
three-postimage derivation; this is not a rebase onto today's unrelated changes.

The new source manifest's **canonical** SHA256 is
`7dc3bbf0dca602a1085dab30d304b7a59f9c765acfdc36a0abf744c2dc1a5f31`.
Its derivative identity is
`ed2ca29c35463080d14532fcab07ef82cb8fdd6c1c1376e139fd7fc026afafb4`;
its materialization identity is
`631f17ef309c06ea634027785f75a7db21b1a4839d04711ae8775d932f8ea67e`.
These identities describe the derivative. The retained base Git commit alone
does not identify these new bytes.

The current-CPU bridge now has six actual ordinary host link/execution cases.
The check includes the real whole `abi.rs` and `cls.rs`, exact existing
`process_sched_cpu_local_bridge` body and exact new
`sched_idle_current_cpu_bridge` body. The production C CPU-local type agrees
with Rust in size and alignment. All six CPU indices select the same actual
array entry through each bridge and CPU-local lookup. The actual final host
binary has unique definitions for the two bridges and CPU-local providers.
The existing frozen image/Rust-object symbol inventories also uniquely define
the three existing underlying providers. Only the privileged CPU-ID boundary
was a safe test stub. The real `x86_local` MSR/GS implementation was not executed.
The check uses ordinary host GCC9/Rust1.92, discards unreferenced CLS allocation
functions and is **not** pinned production TU/full-crate or native proof.

| Selected body | Before frozen10972 | Prepared default consumer | Remaining proof |
|---|---|---|---|
| Exact-running runqueue scan | C scan in idle loop | Rust scan called by Rust iteration while existing lock is held | Pinned full Rust object, default image link and native path |
| Idle initialization and orchestration | C state/IRQ/migration/scan/halt loop | Rust begin/iteration/infinite loop; earlier108 actual original-body equivalence cases retained, not repeated | Pinned whole TU/default link/native; full M14-02-04 area remains open |
| Current-CPU bridge | Existing Rust CPU-ID/process/CLS providers | New Rust bridge uses those providers; six actual ordinary ABI/link cases pass | Real pinned full crate and MSR/GS runtime path |
| Entry and primitive dependencies | C idle entry and existing scheduler/lock/interrupt/halt/allocator primitives | Thin existing C idle producer of ABI offsets/constants/callbacks; primitive implementations still exist | No exemption or whole-area retirement credit |

`PINNED-PRODUCTION-CONSUMER-COMMANDS.json` freezes the actual GCC14 compile
row, header-metadata argv, fresh configure/full Rust/default image targets,
source mount, reviewed resource limits and precise symbol/relocation checks.
It requires the already accepted pinned build image
`sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5`
and a new output namespace. Nothing in it releases Docker, root or a build.

The next executable production observation is the saved GCC14 whole
`process.c` TU/header metadata inside the existing pinned profile, followed by
the real `mckernel_rust_obj` target and default `mckernel.img` target in that
same coherent successor. Before release, the dispatcher must bind the fresh
request/nonce/owner and adapt the existing provenance/image admission pins to
this exact manifest and three postimages. This packet includes a proposed
two-constant successor of the existing thin-source contract, with its exact
patch. It is source only and was not executed. Existing unmodified driver
process/scheduler and old manifest pins correctly refuse the new source;
they must not be bypassed. The exact finite owner-rebinding requirements are
listed in the commands JSON. Existing checks and accepted toolchain/SDK mounts
must remain bound. Fresh capacity includes HOST/scratch floors, full sparse
backing growth and planned new output/capture/emergency bytes.

The root-owned independent execution release, one shared heavy lease and
positive predecessor retirement remain prerequisites. The standalone whole-TU
object must be joined to the generated default CMake consumer and final image;
a successful standalone compile alone is insufficient. The unchanged real
Rust CPU-ID provider must be selected, with no teststub/equivalence config.
New native idle/wakeup/order evidence is separate. Full M14-02-04 remains open.

`ordinary-source-and-bridge-evidence.tar.gz` retains the complete materialization
manifest/journal, raw commands/streams/statuses and generated bridge sources,
objects and executable. All ordinary children joined. No compiler/test ran
after the CPU0 hold; finalization used source/metadata operations only.
`PREPARATION-RESULT.json` binds the exact sources and evidence. No throughput or
native retirement claim is made from this preparation.
