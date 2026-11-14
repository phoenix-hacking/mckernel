# Idle scan compute-C cutover: selected-image gap and concrete successor

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Owner: scratch_growth_prepare. Supported-profile functional McKernel OS/apps plus
active compute-C retirement into Rust/reviewed assembly. This packet stages the
already source-reviewed idle scan onto the source actually used by image10972;
it does not claim a new source algorithm or production/native retirement.
Only this new evidence directory and the matching HOST preparation directory
were written. No canonical source, accepted image, active source/build, Docker,
root, guest, launcher, lock/lease, scratch or compiler profile was modified.

## Concrete defect and useful result

Image10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2
still executes the original C idle runqueue scan, despite current Git containing
the reviewed Rust port. Its source bundle predates the port. The finite join used
the actual accepted image source, recorded production compile row, provenance,
saved production Rust/final symbol inventories and the actual process.c.o symbol
imports. No historical archive or repository-wide source audit was needed.

The selected build's provenance repository_files AND materialized_repository_files
agree exactly with the original source-reviewed idle port's three preimages:

| Path | Actual image source preimage | Exact staged reviewed postimage |
| --- | --- | --- |
| kernel/process.c |a400590c51d4badeca9af7f75fa2aaca2c15a7182020380fed79bdf9d007ac33|910771e0908d3fc69fcad13e94a2f0da13a964ce0293911fa2dcd5180b6e9ca7|
| kernel/rust/sched_helpers.rs |a5b8ed0f048adcfa6908094f7b8b5d459b9b14aa0ed4b75e5250abe6f8387c57|8b5c15fe52c59964105561d560bca5c648464872a44ead44b672e180c44acbd1|
| kernel/include/sched_helpers.h |a11c196aef4398cb39694258889da2586ae9203df1c177afd7bd93418d184493|15e506c4a6e6bd359e704a29e89bff20ea65a14ea69f24171aeb43024847d474|

The actual selected process.c retains the unconditional original C loop. Both
saved final-image and production-Rust inventories lack
sched_idle_runqueue_has_running_result; actual `nm -u process.c.o` likewise
has no helper import. The production process.c compile command already enables
MCKERNEL_RUST_PROCESS_HELPERS, and actual CMakeCache has ENABLE_RUST_KERNEL=ON.
The missing source delta, rather than a disabled selection option, explains this
gap. The historical HANDOFF's production/default-link/native OPEN status remains
correct for this specific path; later image10972 did not silently close it.

Source/artifact authority:
/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/
INDEPENDENT-ACTUAL-MATCHED-IMAGE-ARTIFACT-REVIEW-1.json accepts that exact image
and named boundaries, expressly without broad language-retirement credit.
Its source root is source-materialization-1/materialized-source; actual
full-image-attempt-1/owner-work/evidence/provenance.json, artifacts/compile_commands.json,
symbols.txt and rust-object-symbols.txt supply the selected joins. The actual
object is owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o.
Accepted image bytes/hashes are reused from that authority, not rehashed here.

## Coherent staged successor

HOST packet:
/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/.
preimage/ and postimage/ contain exactly the three files above. The independently
accepted original delta is retained as source.patch; no additional compute C
functionality is introduced. The original C scan remains byte-identical in its
fallback branch. The selected branch calls the existing Rust body while C keeps
the original runq_lock coverage and CPU-status assignment. Existing process.c
FP/post-switch fixes and all other selected-image bytes remain unchanged.

SOURCE-OVERLAY-CONTRACT.json defines the complete source identity from the accepted
base materialization/provenance plus these exact three replacements. Unchanged
source-file authority is reused by reference; no second full source copy or
unbounded tree scan was performed. Derived candidate identity is
d1ce667053d904b9bcf0df94c43865993719479372c785d1174ee46f134307f1;
updated canonical materialized-file-map SHA256 is
5fbcf3fdf055a7af93c012b55943d09d206e5922e924cef250708941133ad709.
This is a source-fingerprint identity, not a fabricated Git commit or a completed
materialization/build claim. At observation HEAD5d41341d0c2c28ab92fe52cc974c742196289fbc,
the three canonical files already equal the reviewed postimages. They were read
for context and never overwritten. The missing work is coherent selected build
input activation and proof, not repeating the same canonical source patch.

## Actual ordinary check and original failure

Exact outer invocation for corrected attempt2 (functional OS only; no security
testing), with one job, inherited NPROC and Rust RUST_MIN_STACK2097152/codegen1:

```text
taskset -c 6 prlimit --as=2147483648 --cpu=60 --fsize=33554432 --core=0 timeout --kill-after=6s 90s python3 docs/verification/evidence/compute-idle-rust-cutover-20261023-1/prepare_and_check.py
```

Attempt1 failed at the small actual-header consumer compile: its harness omitted
the production cls.h include which defines struct cpu_local_var/CPU status values.
Original script is prepare_and_check.failed1.py; RESULT.json and actual-check-1/
retain all commands, error8555B, stdout/status and failed source. ONE bounded
correction added that existing production include, reused verified exact staged
bytes and used fresh actual-check-2/ plus RESULT-2.json. Attempt2 exited0. No
profile widening,512MiB retry, compiler fallback or unchanged deterministic
failure replay occurred. This family has consumed its bounded correction; any
further same-family failure requires expert escalation.

The ordinary host GCC9.4.0 check compiles a SMALL consumer with actual accepted
process.h, cls.h, list headers and generated config.h. It preserves the selected
macro set/include ordering, rebasing paths and the GCC builtin include root for
the host. No substitute thread/CPU structs or guessed offsets are used. Emitted
actual ABI data:

| Production field/value | Host-header observation |
| --- | ---: |
| sizeof(thread) |5568|
| thread.status offset / width |4184 /4|
| thread.sched_list offset |4328|
| cpu.runq offset / cpu.status offset |7872 /7920|
| sizeof(unsigned long) / sizeof(void*) |8 /8|
| PS_RUNNING / CPU IDLE / RESERVED / RUNNING |1 /1 /3 /2|

The source-selected C consumer has exactly one undefined import, the new helper.
Pinned Rust1.92 compiles the EXACT existing body and list_next, codegen1,2MiB
Rust stack; that object has no undefined references. Host link has one helper
definition and --no-undefined succeeds. An ordinary executable using ACTUAL
production thread/CPU records exits0 for three cases: empty/idle; stopped with
spin_sleep-only/reserved; and exactly running/running. This extends the prior80
fixture cases with actual production-header ABI/link evidence; the80 cases were
not rerun. Rust's retained disabled-SSE2 target warning is preserved, with no
whole-crate ABI or warning-free claim.

Important scope: this probe compiles the extracted selected consumer with actual
headers, not the complete process.c TU or a preprocessed default-image selection.
The host compiler is GCC9, while the selected pinned container uses GCC14 and
nightly Rust1.95. It is meaningful actual-header diagnostic/link evidence only;
it does NOT close the pinned production TU, whole-crate, final image, native path
or retirement obligation. RESULT-2.json keeps those acceptance fields false.

## Actual C-body retirement table and next executable observation

| Current compute-C path | Rust body / staged selection | Actual displaced/default/native scope |
| --- | --- | --- |
| process.c idle locked PS_RUNNING scan |Existing sched_idle_runqueue_has_running_result; reviewed3-file delta staged; existing MCKERNEL_RUST_PROCESS_HELPERS default|Current10972 still C: zero displacement. Actual-header host consumer/Rust link PASS only. Pinned fullTU/default final image/native OPEN.|

No new whole-kernel Rust path count or native credit is claimed. A source patch
in current Git or a host executable does not retire the C body in the running OS.

NEXT-PINNED-PRODUCTION-COMMAND-COMPLETE.json carries the exact selected GCC14
process.c command with only its output redirected to a new dedicated
/work/idle-cutover-production/process.c.o, a preprocessor metadata command, and
the actual selected default build argv:

```text
/usr/bin/cmake --build /work/output/build --target mckernel_rust_obj -j4
/usr/bin/cmake --build /work/output/build --target mckernel.img -j4
```

These are preparation data only. The dispatcher must make a fresh coherent
source/output successor and keep the accepted10972 source/build/image immutable;
retain the supported profile/pinned image41778f1f..., Linux6.12 ABI/native fork
option, ENABLE_RUST_KERNEL=ON and exact process-helper define. The future root
operation needs its own independent execution release, positive retirement,
source/toolchain/generated-config bindings, fresh capacity, common/shared leases,
and4CPU/12GiB/no-swap/512task/no-network controls. Root must derive fresh version/
source identity metadata rather than mislabel the new source as the old build.
No second Docker/heavy operation is admitted by this packet.

At the next quiescent boundary AFTER the current SDK/native critical chain:
compile that actual whole process.c TU under the pinned profile to check the
real static assertions/producer ABI; build the whole Rust object/default image;
retain the caller helper relocation, unique Rust/final definition, zero final
undefineds and exact source selection. Then independently review and execute a
native idle/wakeup observation that proves this selected path runs alongside the
unchanged strict application oracle. A boot/app pass alone must not be promoted
to observed helper execution without its required native evidence. No native
instrumentation or guest was added/executed here. Stop on failed/uncertain proof,
preserve every failure; do not count a staged source/mock as cutover.

All raw ordinary artifacts, both source versions, objects/executable and complete
command streams are retained in the HOST packet and hash-listed in
RETAINED-ARTIFACTS.json. Small relevant raw observations are mirrored alongside
this report. Original idle source/unsafe-ABI review remains unchanged under
../rust-idle-runqueue-scan-20261022-1/. Scratch21, permanent27:4, existing ownership,
frozen image10972 and all other workers' dirty inputs are preserved.
