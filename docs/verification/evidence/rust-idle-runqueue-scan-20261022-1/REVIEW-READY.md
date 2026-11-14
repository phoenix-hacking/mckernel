# Idle runqueue read-only Rust scan — review packet

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Supported-profile kernel/application delivery plus active live compute-C retirement
into Rust/reviewed assembly. Source preparation is not linked/native acceptance.

Owner: /root/rust_idle_scan_port. Base HEAD: 81dd8caf8d31eb25504ef492186515898506541b.
Private complete postimages and their exact preimages are in source-map.json;
source.patch contains the only proposed shared production changes. The worker
changed no shared production file. The new regression script is shared for review.

## Contract and integration

The existing idle() holds runq_lock across the exact selected scan and CPU status
assignment; unlocking, idle/reserved gating, halt, interrupt state, allocator work,
FP prelude and post-switch code are unchanged. Rust traverses next links until the
sentinel and returns one only when a C int status is exactly the C PS_RUNNING
value. It neither inspects spin_sleep nor retains pointers or references, changes
state, allocates, invokes callbacks, changes IRQs or transfers ownership. C supplies
both offsetof values. Selected C compile-time assertions require thread.status to
be int and four bytes and list_head.next to be first. Original C scan remains
byte-for-byte in #else. Existing default MCKERNEL_RUST_PROCESS_HELPERS selection
already applies to process.c; no CMake change is proposed.

Unsafe preconditions: valid circular runqueue; each entry is a live thread's
sched_list; caller holds runq_lock and C offsets refer to these actual nodes.
No added null/corruption recovery is implied. Existing concurrent status writers
and exact-equality semantics are preserved. The volatile read uses the actual
kernel CInt alias i32. This is a supported LP64 profile only.

## Executed checks

Pinned rustc 1.92.0 and /usr/bin/gcc, ordinary CPU0 / 1 GiB AS / 20 CPU seconds /
30 wall seconds. Final exact command, environment and resource settings are in
test-attempt-2.command.json; stdout/stderr/status are retained adjacent. The test
retains every subprocess command and stream, objects, generated source, nm and
objdump results under test-attempt-2/. Initial attempt 1 also passed and remains
retained; attempt 2 added explicit production status-width assertion, exact CInt
source binding and corrected fixture spin_sleep placement/size. No failed
candidate or deterministic retry occurred in this lane.

PASS: 80 cases compare actual original C scan and actual Rust body via selected
consumer for empty/one/two/three node queues, all stopped, running first/middle/last,
multiple running, status bit combinations, signed high values and spin_sleep-only;
CPU_STATUS_IDLE and CPU_STATUS_RESERVED both preserve their initial value when no
exact running status exists. Thread bytes and both sentinel links remain unchanged.
An alternate C layout exercises supplied offsets and read-only behavior separately.
Both selected/fallback objects and executables compile/link/run; fallback has no
Rust symbol dependency, selected has the exact Rust dependency. Rust object has
zero undefined references and no FP/SIMD instruction registers. All process.c bytes
outside this insertion and guarded local declaration exactly match the preimage.

C fixtures supply offsetof/sizeof/type checks and the helper assumes no Rust
Thread layout. The primary fixture uses existing canonical status/list offsets
4184/4328 with C int width 4. This is NOT actual current whole-TU ABI verification:
there is no freshly designated standalone generated-config root for this lane.
No current image build directory, Docker, root operation, whole crate, image build,
new guest or native app was used. Production header declaration int status was
read directly from the actual thread definition; full production compile/link
will verify its static assertions later.

## Blocking review and next observation

Independent focused unsafe/ABI review must decide whether this read-only walk,
C producer widths/offsets, exact-equality behavior and lock placement are ready to
integrate. Root owns shared source integration and Git. If approved, apply only
the three source.patch hunks to current shared sources preserving concurrent work;
rerun the retained actual-body test against integrated sources, then existing
reviewed whole-source compiler recipe. Linked artifact and native idle behavior
proof are still required before any Rust-path retirement or acceptance claim.
Stop on genuine unsafe/ABI uncertainty or one candidate plus one bounded correction
failure in the same invariant family. No such failure occurred here. No reserved
576 MiB, scratch21, exclusions57687/57688, mutex27:4, launcher or ownership state
was mutated.
