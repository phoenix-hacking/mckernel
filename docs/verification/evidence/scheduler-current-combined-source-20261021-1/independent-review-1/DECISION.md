# Independent exact scheduler source-union review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: PASS FOR DISPATCHER SOURCE INTEGRATION of this exact two-file union,
provided the complete live preimages still match immediately before applying.
The current reviewed live preimages match. No additional edit or silent rebase
is admitted. This decision accepts the combined SOURCE boundary only; it does
not accept combined compilation, default linked ownership, native behavior or
compute-C retirement, and does not release a future compiler/root/guest run.

## Exact union established independently

- combined.patch: `ef51fce560db693cb812fa231346348bcd3b3417d9fccef857ae73556dd1e6ea`
- LITERAL-HUNK-UNION.json: `ba4836b14a52021f359c5fb87c80f8d713f3f301896eb1f9b167b17e09ddb697`
- FROZEN-MANIFEST.json: `b4e1ddf5964b9aacfcf7e22e4eb400f1d82eecaac647432e09952761604ee792`
- C preimage: `81404ef35d90cf965c1f46ba200d6d83106576373c0ddd84128c638dffe3b6fb`
- Rust preimage: `8c5f69629882e7bdcca88fdc7a7fe58d762cf9906e065a0da932f0dfb260628e`
- C postimage: `55e04a1e152d17c83d61280ea436012d8c073c78cb3c62bf9689c670b4021d34` /839266bytes
- Rust postimage: `a5b8ed0f048adcfa6908094f7b8b5d459b9b14aa0ed4b75e5250abe6f8387c57` /170508bytes

All frozen-manifest rows match. Independent static comparison confirms exactly
four hunk payloads, identical in order and content to mutation8d769da2 followed
by retained-reference3fbc5a0c. The only later-coordinate shift is the existing
38-line Rust insertion. Independently composing the complete parent source
contents in either order produces these exact full postimages. The entire C
postimage equals its already reviewed mutation parent. No extra body, signature,
layout, default, flag or fallback change exists.

## Combined caller, ABI and guard assessment

The existing enabled Rust syscall caller still supplies the real C
sched_apply_scheduler_bridge; it calls the same static setscheduler wrapper.
Under existing MCKERNEL_RUST_SCHED_POLICY_HELPERS, that wrapper passes the C
thread/param addresses, policy, sizeof(*param) and real priority/target offsets
to the new extern-C Rust body. Its seven argument types match the Rust
usize/CInt/SizeT ABI on supported x86_64. The same existing Rust validator
precedes exact byte copy and policy store. The external setscheduler caller
retains its single selected lookup reference through owner offload and through
this complete C-bridge/Rust-mutation call, then releases once on error or normal
apply return. No new provider, lock, callback or ownership hook is introduced.

The untouched CMake syscall.c definitions continue selecting both scheduler and
syscall policy helpers. No default-selection change is made by the union. The
new C extern/use is inside its matching scheduler guard; #else preserves the
original entire C mutation. Disabling the scheduler helper selector retains
the original C validator/mutation fallback. Its inherited caller lifetime
limitations are not retroactively repaired or accepted by this Rust caller fix.

Reuse the exact passed sixteen-case mutation acceptance5f9c6606 and seven-case
retained-reference acceptance23c21b59 bound in the union receipt. Their unchanged
function contents compose without a new source-level ownership or ABI conflict.
No vectors were rerun. These isolated fixture results do not become whole-crate,
combined-link or native evidence merely because the source union is accepted.

## Frozen inputs and next actual observation

The narrow ownership receipt was inspected and current stat/samefile checks
confirm all four current160/image6959 touched-file copies have their recorded
distinct inodes and are not live repository files. Both declared actual image
materializer origins are also distinct from live files. Integrating only the
two live source files therefore does not modify those frozen input copies;
current image work need not wait or be relabelled. No full6959-row inventory
was reopened for this disjoint source review.

A future fresh two-row successor materialization/compile must bind the new
complete source and preserve the other158 rows. The described unchanged
six-stage recipe plus scheduler-policy -U in its existing sixth C fallback
stage is a reasonable next observation proposal, not an execution grant here.
It still needs its own exact driver/request/profile review and actual compiler
feedback. Guarded whole Rust/C/fallback/ABI compilation, one final default
definition/consumer, matching image/module and native scheduler evidence remain
open. Numeric host-owner incarnation, target exit-state behavior, scheduler-field
concurrency/publication and compute-C retirement remain unproven.

Only static reads, hashes, literal source composition comparisons and narrow
inode checks were performed, plus this private report. No compiler, test,
candidate execution, lease, root/guest command, shared integration or Git edit
was performed by this reviewer.
