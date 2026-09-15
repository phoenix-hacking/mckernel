# Resume cursor

State: autonomous execution active. M00-A preservation is complete at pushed
commit `6c0f9f81339ed3ad90a8d207cdd995184fcc625f`; all 15 source-indexed
preexisting artifacts were fetched from GitHub and independently matched by size
and SHA256. Evidence is `docs/verification/os-m00-preservation-checkpoint-20260915.json`.
The retained patch has two source-index-bound trailing-space lines; preserve its
bytes. Generated `__pycache__` files remain untracked and outside checkpoints.

Active run directory:
`/home/holden/mckernel-work/scratch/os-goal-20260915T031816Z-78abb831`.
Launcher-owned state remains under
`.git/os-autopilot/runs/20260915T031816Z-78abb831`; do not edit it.
Coordinator is Sol/medium. Use Luna/low audits, Luna/medium specified fixtures
and bounded Astra/high ownership/release review. No child may recurse. The
dispatcher exclusively owns the currently free build/guest lease. Measured free
space is 39 GiB host and 23 GiB scratch; recheck before heavy work.

Active work:

1. M01-B source provenance now passes independent Astra/high review. Both modes
   bind all 51 Rust inputs, the mode-3 pre/post-rustfmt authority is retained,
   seven focused tests pass, and all rejected attempts are preserved. This is
   only a provenance subgate: the actual native state/cancellation matrix,
   selected candidate build, stack review and guests remain blocked/open. The
   first proposed native-method harness was rejected because it included method
   snippets only as strings and ran substring checks; its exact files and
   independent P1 review are retained as explicit failure evidence.
2. M02-A now passes exact-current independent Astra/high source review after six
   preserved correction findings. Twelve focused tests cover durable unique
   journals, bounded retry state, fallible diagnostics, actual inherited-flock
   recovery and the production PASS predicate. This releases only the source
   packet; the root/Docker 25-case run has not yet executed.
3. M00-B is complete locally: `docs/verification/os-live-ledger-20260915.json`
   contains every exact gate/case/packet ID and required reconciliation record;
   its SHA256 is `2b34c315a710620aa4f3c9eaaa76012f2c42dd2b374e8099b073a0229976a2e5`.
4. M00-D coordination is complete locally. The dispatcher alone owns one heavy
   build/guest lease; no exact heavy process or development-lock holder was
   present. The corrected resource record measured 58G host and 23G scratch
   available, explicitly scopes no-swap to isolated runs, and passed a bounded
   independent audit. Remeasure immediately before each heavy acquisition.

M03-A source audit defines the next implementation boundary: a pinned private
Rust pending-free batch must detach the exact per-CPU chain while preserving
order, page metadata and boundary links; invalid input must leave the list
untouched. Its first candidate was independently rejected for invalid Pin
construction, broken empty-list transfer, premature production integration and
grep-only tests; its exact failure archive and additive review record are
retained. Attempts 2 through 5 restored the production finish path but were also rejected:
empty detach did not release the source, mixed destination states passed, its
unsafe contract was incomplete, then the purported production tests were not
executed and contained independent borrow/count defects. Later extracted-helper
tests still used unbound ABI dependencies and overstated later-invalid/C-reference
coverage. All exact candidates are retained; the current dirty
candidate remains rejected and must not be staged as an implementation.

M02-B root attempt 1 is retained as FAIL: SHA passed, but the first `literal`
collector case produced setup stage 1/EPERM and the remaining 24 cases did not
run. Cleanup, exact absence and the watchdog passed. The immutable raw packet
has magic decimal 827081537 (`0x314c4341`); an additive correction preserves the
earlier summary's mistyped decimal. Same-profile probes isolate the blocker to
Docker seccomp rejecting `close_range`. The production collector now has a
bounded ENOSYS/EPERM finite-descriptor fallback, and its exact included-C matrix
passes. The pinned rebuild helper binds all 14 original and retained inputs.
Independent review nevertheless withholds the build because the established
outer container wrapper can release its flock without verified Docker absence.
A first dedicated build-owner candidate was independently rejected because its
bounded cleanup could release the inherited flock with a live container, its
watchdog/config/isolation evidence was incomplete, and its root-owned `/work`
mount was unusable by UID 1000. Three follow-up candidates remained unsafe,
structurally incompatible with the reviewed watchdog ABI, or deterministically
unable to validate their own Docker configuration/build record. Their exact
states and findings are retained. Candidates 6 and 7 then exposed and corrected
container/host namespace, Docker allowlist, record membership, daemon-null and
numeric deadline defects. Candidate 8 passes independent Luna evidence audit and
Astra/high `PASS_BUILD_PACKET` review at exact owner SHA256
`06268712e4c070112e0d8aabdf68d7fba1413a2a1ccfebdd5ccbaf6737b583ee` and test
SHA256 `273c1ce062d83376ef43fce45a7e30dd55651aa299e91f8428ebac172c891af6`.
Both Python versions pass 8/8 focused tests; 23 additional clock/type mutations
are rejected. The exact packet was pushed and fetched-blob verified at
`2b2d8831da417a3654489eb7bf338d7c59f1fe26`. Bounded build attempt 1 completed
the 14 inputs, 16 outputs, 20 commands, SHA9 and builder-negative run, but the
owner rejected it because the new `<sys/resource.h>` fallback adds three exact
headers to the old 176-dependency expectation. The full original owner/build
trees are retained in archive SHA256
`b81e64cd1ae35152f9649f645151f158d4b6b34a3c37b9ce9b9b6d6b357e4a0d`.
Container absence, watchdog disarm/reap and lock release passed. The narrow
179-count correction passes both 8/8 test runs, the corrected verifier passes
against the preserved raw record, and Astra/high returned `PASS_RERUN_PACKET`.
Fresh attempt 2 then passes the complete build-owner gate. Its 612-member archive
SHA256 is `1aa076149e2ffc83019f43d11b79c9f679ec5ca24345c13525e45528292319a6`;
independent review returns `PASS_REBUILT_COLLECTOR_INPUT`, with rebuilt collector
SHA256 `e0e8e30e89b003ba51092f571d622e007ca2d9067561bfc06a2854cb8d29cc9d`.
This is build-input acceptance only. The root orchestrator was rebound to the
exact new record/path and
passes 14/14 focused tests under Python 3 and 3.8 plus independent Astra/high
`PASS_ROOT_PACKET_SOURCE` review at source SHA256
`b794fc74a668f9f41caceb99e299381652fe02caa002c06d8b43c287b75599a3`.
Its checkpoint was fetched-blob verified before execution. The stopped-container
interval before CID-bound watchdog
readiness remains an explicit non-execution limitation. No heavy process or
McKernel guest is live.

Root-positive attempt 2 now passes all 25 exact Linux infrastructure cases. Its
991-member archive SHA256 is
`ad7c670311f6756cf64610e1d3e0dbdcdb026f86857c8461c3295cc34c17a721`;
independent Luna and Astra reviews return `PASS_ROOT_EVIDENCE` and
`PASS_ROOT_COLLECTOR_INPUT`. All 58 supervisor collections, 989 inventory
entries, build/input bindings, exact process outcomes and cleanup/absence gates
verify. The retained `observed-profile.json` FAIL is the conservative pre-test
snapshot; the post-SHA9/post-25-case `root-result.json` is PASS. This remains
Linux infrastructure input only. M02-B still requires its adverse storage,
late-signal/setup, rescue, overflow and loader-closure cases; M02-C through M02-F
and all McKernel/application/transport acceptance remain open.

Counters remain: 0/273 application cases accepted (three compiled), 2/4 narrow
fault modes accepted, 6/130 production gates and 350/10,000 points, 0/7 language
gates complete (three IN_PROGRESS). Current production remains exact baseline
module2026091301/image3 with its eight original suites; no broader acceptance is
claimed. External hardware/exposure work remains later and unavailable locally.

M03-A/B pending-free candidate 6 stopped at its first focused execution failure:
the expanded Rust callback vectors exceeded the fixture's four-entry event ledger.
The exact five candidate sources plus generated Rust source/binary are preserved in
`stability-pending-free-batch-candidate-runtime-failure-20260915-6`; no negative
trait, C-oracle, runtime, invalidation, backing-reuse or production credit follows.
Candidate 5 and its independent review failure remain unchanged. A fresh reviewed
correction is required before another focused execution.

Independent M02-B review now permits a new additive adverse-v1 implementation
packet for missing setup, 383-byte partial setup and deterministic interruption
at the completed-wait boundary. It requires separately named, hash-bound generated
test collectors and a new root profile; the released collector and 25-case profile
remain unchanged. No adverse execution has started. Independent M02-C review did
not freeze the native collector ABI: terminal encoding, thread birth identity,
complete loader observation, unchanged-mcexec stream attribution and qualified
no-loss/clock/owner producers remain unresolved. No native collector implementation
or credit follows from the retained design draft.

The follow-up M02-C source audit found that retained host `ProcessId` object
identity already protects Linux PID reuse, but McKernel threads have no birth
generation and no native producer exports authoritative guest terminal status.
The existing 64-record trace budget is diagnostic rather than lossless. A future
freeze therefore needs separately reviewed guest birth and terminal/retirement
publication; numeric TID, launcher wait and fixture status encoding are invalid
substitutes.

M02-B adverse-v1 source attempt 1 stopped before executing any unit test because
its isolated `python -m unittest` invocation could not import the repository
`scripts` package. The exact new source packet is archived as
`stability-linux-collector-adverse-source-failure-20260915-1`; it has not been
compiled or executed and is under independent semantic review before any corrected
test run. The accepted adverse design record remains an input, not evidence.

M03-A/B candidate 7 printed its focused PASS marker, but independent review
rejects it. Its C side emits fixed rows without executing a model; production ABI
dependencies remain handwritten; the separate Rust fixture is not executed;
mandatory isolation/reuse/trait cases and safe callback/recovery are incomplete;
and the mutant does not exercise partial release. The exact claimed run and PASS
manifest remain archived as rejected evidence in
`stability-pending-free-batch-candidate-run-20260915-7`. Production source review
still finds complete validation before the first callback, but no focused
equivalence, invalidation, reuse, runtime or production credit follows.

M02-B adverse-v1 source attempt 2 corrected several semantic defects, then its
first focused unit-test run failed on a string/bytes hashing error, an inconsistent
hook-count assertion and a positive missing/partial oracle fixture that rejected
itself. The exact source is preserved as
`stability-linux-collector-adverse-source-failure-20260915-2` and is under fresh
independent review. It remains uncompiled and unexecuted outside Python tests.

M02-B adverse-v1 attempt 3 failed its focused test, then changed the candidate
without retaining the exact failing source or raw output. The post-failure tree is
preserved separately as `stability-linux-collector-adverse-source-postfailure-20260915-3`
and is explicitly untested; independent review is required before any new run.
M03-A/B candidate 8 stopped before compilation when its `IhkAtomic` extraction
anchor also matched `IhkAtomic64`. Its exact sources and `failure.json` are
preserved; no retry, focused equivalence or acceptance follows.

Read-only M02-B review confirms stopped-collector/external-rescue is not ready to
run: neither the accepted 25-case profile nor adverse setup packet contains an
identity-bound collector-stop stimulus. Existing supervisor and root watchdog
cleanup can be reused only after a separate reviewed stopper/rescuer packet; no
ordinary root rerun can substitute for this case.

M03-A/B candidate 9 expanded the unexecuted fixture/evidence design, but stopped
before compilation because its `kmalloc_track_hash` extraction end marker also
matched `kmalloc_track_hash_ptr`. Exact pre-run sources, environment, command
status and failure are retained in
`stability-pending-free-batch-candidate-runtime-failure-20260915-9`; the claimed
computed cases remain under independent static review and receive no credit.

M03-A/B candidate 10 applied the two candidate-9 corrections and passed source
extraction plus shell syntax, then stopped at Rust compilation. The host `+nightly`
is Rust 1.60.0-nightly from 2022 and lacks the modern APIs used by the exact-source
fixture, producing 46 diagnostics. The complete pre-run inputs, compiler identity,
commands, streams and failure are archived as
`stability-pending-free-batch-candidate-runtime-failure-20260915-10`; compiler-lane
review is pending and no retry or credit follows.

M02-B adverse-v1 attempt 4 passed 10 retained source/mock tests and diff check,
but independent review rejects its source/build packet. Under umask 077 its file
writer records modes it never applies, complete link/tool/input provenance is not
verified, and actual builds omit the generated diff. The exact passing unit-test
archive remains rejected evidence in
`stability-linux-collector-adverse-source-success-20260915-4`; no collector build,
root execution or acceptance follows.

M02-B adverse-v1 attempt 5 passes 12 retained Python 3.8 source/mock tests and
preserves the three attempt-4 corrections, but review finds a deterministic
producer/verifier mismatch: the pinned image resolves logical `/lib64` loaders to
canonical `/usr/lib64`, while verification demands the logical path as the file
identity. No build packet is released. M03 candidate-11's new Rocky Rust 1.92
owner likewise fails source review: it rejects the required negative mutant run,
accepts incomplete placeholder result inventories, and permits traversing or
symlink-followed artifact names. Its reported passing tests are not accepted
because an earlier fixture failure was corrected without retaining exact output.

M02-B adverse-v1 attempt 6 corrects the sole attempt-5 loader mismatch by binding
both logical `/lib64` and canonical `/usr/lib64` paths to the pinned image. Thirteen
retained Python 3.8 tests pass. The original no-index diff chain stopped normally
at its first content-difference status with empty diagnostics; additive per-file
checks retain status and empty streams for all three files. Independent Astra/high
review returns `PASS_BUILD_PACKET` for selectors 0-3 compilation only. The source
must be checkpointed before the dispatcher runs the isolated build; root execution
and all collector/application acceptance remain closed.

The dispatcher has now run fresh adverse-v1 build attempt 1 from fetched commit
`2e3fe26cf138c4d2170912b82fb8b6419e573c6b`. Host owner, inner build and watchdog
all report their infrastructure-only PASS statuses; the raw build record contains
23 commands, 179 unique compiler dependencies, 24 outputs and all four selectors.
The complete 650-member archive SHA256 is
`eaf0665189b49d80359b44109d7f015e19700112cc1d07d68b2d1ccd405e8675`.
Independent evidence and ownership reviews are active; no root selector run or
acceptance is released yet.

M03 candidate-12's corrected Rocky Rust 1.92 build owner passes 8/8 retained
source tests under both Python interpreters and independent Astra/high source and
build-packet review. It binds 30 exact computed rows, 51 artifacts, five trait
negatives, the partial-release mutant, compiler bytes and the inherited isolated
watchdog/cleanup owner. This releases only a fresh dispatcher-owned focused
container build after a fetched-source checkpoint; no fixture execution or M03
credit exists yet.

The dispatcher-owned M03 candidate-12 focused build attempt 1 now passes its
exact 30-row Rust/C equivalence packet, five negative trait probes, partial-release
mutant and isolated Rocky Rust 1.92 ownership checks. Both independent reviews
accept only `PASS_PENDING_FREE_BATCH_FOCUSED_EQUIVALENCE_ONLY`. The fixture omits
conflicting/nested begin and its panic bridge, malformed active-source empty and
boundary links, and bounded incomplete-inventory behavior. The dirty candidate
may therefore be retained only as a private unused prerequisite; production
integration, guest execution, invalidation/concurrency/application acceptance and
all M03 production credit remain closed.

M02-B adverse-v1 root attempt 1 passes its exact instrumented Linux scope after
independent audit and semantic/ownership review. Control, missing setup, partial
setup and completed-wait interruption produce collector raw waits
`[0, 256, 256, 256]`, four child raw waits of zero, exact setup lengths
`[384, 0, 383, 384]`, verified container absence and watchdog disarm. A separate
accepted-supervisor observation reacquires the same development lock exclusively
and without waiting after completion. The immutable runtime and additive lock
archives are `stability-linux-collector-adverse-root-success-20260915-1` and
`stability-linux-collector-adverse-root-lock-observation-20260915-1`. This is one
four-selector Linux infrastructure run only: stopped-collector rescue,
watchdog-triggered recovery, post-reap/report-fsync interruption, general storage
faults, production-binary equivalence and every McKernel application/production
gate remain unaccepted.

M03 candidate-13 source attempt is rejected before build. It proposed seven new
conflict/panic/malformed-link rows, but semantic review finds pointer-to-integer C
link assignments, a handwritten panic dispatcher that bypasses the production
body helper, and two boundary cases that stop at the earlier inconsistent-empty
guard. The exact three-file source is preserved in
`stability-pending-free-batch-source-failure-20260915-13`; its owner-test pin-drift
output was not retained, which is recorded as an evidence limitation. A conflicting
cheap inspection reported PASS, but the precise semantic blockers control the
failure disposition. No build, runtime or credit follows.

The bounded M02-C birth/terminal source audit confirms there is no stable guest
thread generation or native terminal publication hook today. Numeric proxy TIDs
are reused; authoritative group/thread status writes precede a distinct later
finalize/release path. The current application ABI's delivery serial can be a
future carrier only after a retained loss-detecting event ledger exists; its
64-record trace is diagnostic. A proposed birth/terminal/retire record and exact
ordering are retained in
`stability-native-collector-birth-terminal-source-audit-20260915-1.md`, but loader
completeness, unchanged-`mcexec` stream attribution/no-loss and clock guarantees
still prevent ABI freeze. No producer edit or acceptance is authorized.

M03 candidate-14 corrects all three candidate-13 source blockers and receives
independent `PASS_SOURCE` and `PASS_SOURCE_EVIDENCE`. Its 37-row contract now
extracts the actual production body helper and callback aliases, uses normalized
C identities, and corrupts only `first.prev` or `last.next` on valid two-page
rings. Cheap source generation binds 20 regions/prefixes and 10,117 generated
bytes. The exact sources and streams are retained in
`stability-pending-free-batch-source-checkpoint-20260915-14`. Compilation,
execution, the real fatal panic/public-entry path, bounded incomplete inventory,
runtime and all production credit remain closed; a new reviewed build-owner pin
packet is required next.
