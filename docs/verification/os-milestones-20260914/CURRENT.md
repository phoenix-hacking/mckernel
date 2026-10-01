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

The M02-C loader-map audit finds no authoritative executed loader/DSO or
transient-map producer. Current image code validates caller-supplied section
descriptors, and synthetic procfs maps do not bind mapping lifetime or ownership.
The proposed begin/row/end record in
`stability-native-collector-loader-source-audit-20260915-1.md` remains structural
only: stable thread generation, executed hooks, complete transient events,
stream/no-loss attribution and ownership/clock qualification still block freeze.

The separate M02-C stream review confirms unchanged `mcexec` shares stdout/stderr
endpoints between launcher and delegated payload writes, while the supervisor
retains bytes but not writer identity or write boundaries. Marker filtering and
PTY substitution are unsound. The out-of-band exact partition proposal and
negative matrix in `stability-native-collector-stream-source-review-20260915-1.md`
remain structural only; no inspected producer supplies origin, endpoint-lifetime,
committed-fragment ordering and loss guarantees.

M03 candidate-15 updates only the isolated build owner and its cheap tests to bind
the committed candidate-14 hashes, 37 ordered rows and panic field. Eight tests
pass under each Python interpreter and independent review returns
`PASS_BUILD_PACKET`. The retained cheap streams lack full invocation/interpreter
metadata, which limits them to source-packet support. A fresh dispatcher-owned
Rocky Rust 1.92 focused build is released only after this exact checkpoint is
pushed and fetched; no runtime or production credit exists yet.

Dispatcher-owned candidate-14 focused build attempt 2 passes 37/37 computed Rust
and C rows, 20 production extraction bindings, 51 artifacts, the intended
partial-release mutant and five negative trait probes under the pinned Rocky
compiler. Both independent reviews accept only
`PASS_PENDING_FREE_BATCH_FOCUSED_EQUIVALENCE_ONLY`. Source integration remains
closed because the safety text forbids enqueue for the entire detached lifetime
while the implementation and source-reuse row permit a subsequent independently
owned capture on the reset head. The exact 288-member archive is
`stability-pending-free-batch-build-owner-success-20260915-2`.

The separate bounded-inventory audit finds that current cycle validation still
has no trusted node-count bound and dereferences ring links before independent
descriptor/range ownership proof. Aggregate allocator bounds cannot substitute.
`stability-pending-free-batch-inventory-source-audit-20260915-1.md` records the
needed captured capacity/count and negative matrix. No such ABI is wired today;
integration, invalidation, guest/application and production credit remain closed.

M03 candidate-16 corrects only the contradictory detach safety comment. Exact
archive comparison and independent reviews return `PASS_CONTRACT` and
`PASS_SOURCE_DELTA`: executable/test bytes and the normalized executable hash are
unchanged. The text now preserves exclusive transfer and retained-descriptor
ownership, pinning and callback non-reentrancy while permitting a later
independently owned capture after the source head is reset. The exact corrected
source is archived in `stability-pending-free-batch-contract-checkpoint-20260915-16`;
it is not committed as production source and integration remains closed on the
inventory, durable ownership, invalidation and qualification blockers.

M02-B now has a reviewed `PASS_DESIGN_ONLY` stopped-collector/external-rescuer
packet specification in `stability-linux-collector-stopped-rescue-design-20260915-1.md`.
It requires a real parent-observed SIGSTOP, fork-owned identity-safe leader and
adopted-child termination, raw stop/exit waits, ECHILD, bounded continuation and
complete cleanup evidence. No packet or execution is released yet. The separate
watchdog/fsync audit identifies an existing private-disarm timeout recovery path
but no deterministic post-reap/report-fsync seam; both need separately reviewed
instrumented cases. The accepted adverse run covers neither.

M03 candidate-17 changes only the focused build owner's exact production-source
pin to the reviewed comment-corrected SHA and adds an old-pin rejection. Eight
tests pass in both Python lanes; independent reviews return `PASS_BUILD_PACKET`
and `PASS_SOURCE_EVIDENCE`. The cheap command records lack complete interpreter,
environment and timestamp identity, so they support the source packet only. A
fresh dispatcher-owned container build is released after this fetched checkpoint;
source integration and all runtime/production credit remain closed.

The dispatcher-owned candidate-16 exact-source build attempt 3 passes the same 37
Rust/C rows byte-for-byte against corrected source SHA
`647825d8c51a9f584d1229a2389fbb81105e4bbf94bfcf95a12d172c5dde112b`.
All 20 bindings, 51 artifacts, five trait controls, mutant and isolated cleanup
checks pass independent audit/review. Its 288-member archive is
`stability-pending-free-batch-build-owner-success-20260915-3`. The accepted
disposition remains a private unused prerequisite only: trusted pre-dereference
inventory/range proof, durable owner-loss recovery/transaction identity,
invalidation/backing policy and full module/guest qualification still block source
integration and all runtime/production credit.

Two follow-up M03 reviews now make the remaining ownership boundary concrete.
`stability-pending-free-durable-owner-review-20260915-1.md` requires a surviving
OS registry, OS/VM incarnation plus nonreused serial, durable inventory/progress,
owned backing references and interruption-safe bounded recovery before capture.
`stability-pending-free-invalidation-policy-audit-20260915-1.md` requires retaining
`PM_PENDING_FREE` and backing until successful clear/TLB acknowledgement, with
bounded retry or terminal quarantine on failure. Current void callbacks and
stack-local inventories cannot supply either contract. An audit-response hash
transcription is corrected additively in the retained policy record.

M02-B stopped-rescue-v1 source attempt 1 passes four cheap mock tests but is
rejected by independent semantic/ownership review. It stops the fixture before
setup/exec rather than the collector at the designed boundary; its rescuer logic
is uncalled and lacks parent/adoption ownership; build/run wiring omits the new C
sources and calls a nonexistent API; and its oracle accepts handwritten summaries
without raw evidence. The exact source/check archive is retained as
`stability-linux-collector-stopped-rescue-source-checkpoint-20260915-1` with the
failure record. No build or root execution is released.

Stopped-rescue source attempt 2 made no file change: both proposed patches failed
their context verification atomically, then the dispatcher timeboxed the task.
Only an unretained Python syntax check was reported; no new evidence directory
exists. The exact working packet therefore remains identical to rejected attempt
1. Under the two-attempt stop rule this correction is escalated for a newly
scoped source/context review rather than another immediate implementation retry.

The escalated stopped-rescue context review retains `FAIL_SOURCE` and supplies an
exact dependency-ordered correction map in
`stability-linux-collector-stopped-rescue-context-review-20260915-2.md`. It
clarifies that the rescuer owns/waits only for the collector, while the stopped
collector owns and later reaps both fixture processes; it also identifies the
stateful non-idempotent setup validator and exact hook/run/oracle wiring. No third
immediate source retry, build or execution is released.

The M03 integration sequencing review returns `PASS_DESIGN_ONLY` for a four-file
private bounded-inventory fixture. Its independently supplied arena/count can test
address resolution before dereference, finite work and full range/membership
rejection without granting detach/free authority. Registry and typed release
authorization remain later prerequisites. The exact allowlist and negatives are
in `stability-pending-free-integration-plan-review-20260915-1.md`.

M03 private inventory fixture attempt 1 is rejected. Its 14 Rust/C rows are only
names and expected constants, its parser compares names/substrings rather than
computed behavior, the model accepts malformed rings without sentinel/cardinality
proof, range identity/geometry is missing, and Copy inventories retain no arena
lifetime or non-releasing validated authority. The exact four files are archived
as `stability-pending-free-inventory-source-checkpoint-20260915-1`; there are no
retained command streams. No compilation or acceptance follows.

M03 private inventory attempt 2 partially adds exclusive arena lifetimes, separate
descriptor/extent identity and a non-releasing result, but independent review
still rejects it. Sentinel rules reject valid rings while allowing detached cycles;
constructors remain metadata/zero-count placeholders; the C preprocessor and
source parser are invalid; trusted extent ownership is absent; and overflow codes
contradict vectors. No test was run before the dispatcher timebox. The exact source
is archived as `stability-pending-free-inventory-source-checkpoint-20260915-2`.
Under the two-attempt stop rule no immediate implementation retry is released.

Three remaining M02-B gaps now have bounded read-only records. Storage fault design
permits only separately guarded simulated I/O seams with an external fsynced
witness, preserving raw 256 versus report-path raw 32000 and immutable original
failures. Overflow audit distinguishes the already covered 65,537-byte stream case
from an unreleased >512-owner containment case. Loader-closure design requires
parent-owned exec/syscall tracing and descriptor/mapping identities across dynamic
load/unload plus a true static fixture. See the three new
`stability-linux-collector-{storage-fault,overflow,loader-closure}-design-20260915-1.md`
records. None releases source, build, root execution or acceptance.

Storage-fault-v1 source attempt 1 stops at its first focused test: the test computes
`scripts/scripts/tests/...` and raises `FileNotFoundError` before exercising the
packet or oracle. Python syntax was reported passing, but the original test streams
were not retained. The exact source tree is archived as
`stability-linux-collector-storage-fault-source-failure-20260915-1`; no semantic
review, build or execution follows until a fresh path-only correction and retained
test run.

Storage-fault-v1 source attempt 2 applies only that path correction and retains the
complete focused unittest streams, but all three tests fail. Generated bytes lack
the asserted case marker; reused attempt-root handling raises `AssertionError`
rather than the asserted `FileExistsError`; and the oracle negative matrix includes
a raw-wait mutation that can equal the selected case's expected value and therefore
be accepted. The exact source and streams are archived as
`stability-linux-collector-storage-fault-source-failure-20260915-2`. Under the
two-attempt stop rule no immediate third source attempt, build or root execution is
released; the lane returns to independently scoped source/context review.

Independent storage-fault context review retains `FAIL_SOURCE`. Two assertions are
test defects and one is an undefined exception contract, but the deeper packet is
also disconnected: its injected helper is uncalled, preparation is not durably
published, and the oracle trusts handwritten witness fields without raw wait,
process, cleanup, prefix or report-byte cross-binding. Report-open absence and
secondary report failures also need distinct evidence. The exact correction scope
is retained in `stability-linux-collector-storage-fault-context-review-20260915-1.md`;
no new source packet is released.

M03 durable-registry review finds `SOURCE_FEASIBILITY_ONLY`. The published OS
runtime can own a private transaction table, and existing application RPC slots
offer useful bounded/quarantine patterns. Production wiring remains blocked because
`Mirror::clear` cannot target a departed launcher's MM, clear errors are discarded,
the current zeroing head exchange cannot reconstruct interrupted work, and existing
raw page ownership cannot reject address reuse. A private non-releasing registry
model is now specifiable; exact identity and negative requirements are in
`stability-pending-free-durable-registry-feasibility-review-20260915-1.md`.

M02-C lifecycle review returns `FAIL_DESIGN_FREEZE`. Authoritative publication must
separate allocation/birth/abort, thread terminal, process terminal and actual
refcount-zero retirement. `do_exit` bypasses group `terminate`, early fork and main
preparation can fail after identity allocation, and finalized zombies or retained
main-thread storage outlive terminal status. Nonreused guest incarnation and exec
identity are still missing. The bounded producer-only next scope is recorded in
`stability-native-collector-lifecycle-publication-review-20260915-1.md`; ABI freeze,
native collection, application acceptance and production credit remain closed.

Three design-only packets now bound the next independent source work. Storage-fault
v2 specifies seven connected selectors, an external durable witness owner, raw wait
and report presence semantics, additive secondary failures and cross-bound oracle
negatives in `stability-linux-collector-storage-fault-v2-packet-design-20260915-1.md`.
The pending-free private registry model defines safe non-releasing owned mock state,
epochs, exclusive recovery leases, quarantine/archive and independent Rust/C full
snapshot checks in `stability-pending-free-private-registry-model-design-20260915-1.md`.
The native lifecycle model separates allocation, birth, abort, thread/process
terminal and actual retirement with sticky observation loss in
`stability-native-collector-lifecycle-model-design-20260915-1.md`. These records
release no source, build, root/native execution, ABI freeze or acceptance credit.

Native lifecycle model source attempt 1 is rejected before checks or compilation.
Its operation rows do not consistently join allocation to later typed identities
and one row violates the declared arity. Process/thread state is conflated, full
identity fields are ignored, numeric IDs narrow unchecked, and an unowned integer
can stand in for destruction authority while reference resurrection and retirement
without process terminal remain possible. Literal expectations omit the complete
event/ownership state and the harness ignores `S`/`E` fields. Exact bytes are
retained in `stability-native-collector-lifecycle-model-source-failure-20260915-1`.
One bounded correction may address these source-review findings; no build, native
execution, ABI freeze or acceptance is released.

The bounded lifecycle attempt-2 correction map is now source-ready but not
implemented. It replaces the ambiguous line protocol with exact eight-field JSON
operations and full typed keys, separates process/thread registries and obligations,
and defines retained one-shot unpublished destruction authority. It also requires
complete literal step/event/control expectations, strict output parsing and the
full failure/mutant vector set. See
`stability-native-collector-lifecycle-model-correction-map-20260915-1.md`. Attempt 1
remains rejected; no source check or build is released until exact attempt-2 bytes
receive independent review.

The independent attempt-2 corpus draft now freezes result codes, full row/event and
control layouts, main-storage acquisition, branch-4 and inherited-status semantics,
successful-operation event emission, EOF behavior, fault seeds, capacity/schema
negatives and four exact mutant bindings. Its acyclic literal-pool rules and full
coverage inventory are retained in
`stability-native-collector-lifecycle-corpus-draft-20260915-1.md`. The working
allowlist currently contains only a new README/harness/test shell over the rejected
attempt-1 model and data bytes; it is deliberately `SOURCE_WIP_NOT_REVIEWABLE`.
Materialized independent literals and replacement Rust/C models remain required
before attempt-2 source review or any check/compilation.

The first attempt-2 corpus slice now has independent
`PASS_BASELINE_LITERAL_SLICE_ONLY` review. Its exact 16 operations and full literal
process/thread/event/control expectations match the draft for immediate exit,
last-thread process terminal and ordinary complete retirement. The pool expander's
nested type checks, acyclic recursion and conservative pre-allocation node/byte
budgets pass source inspection, and `corpus_complete=false` prevents directory
creation or compilation. Exact five-file bytes are retained in
`stability-native-collector-lifecycle-baseline-literal-slice-20260915-1`. The other
required vectors and both replacement models are still missing; whole-corpus and
source acceptance remain closed.

The next attempt-2 slice receives independent `PASS_ABORT_LITERAL_SLICE_ONLY`.
Preparation abort (unassigned TID/stage 1), assigned-TID abort (TID 200/stage 2)
and late-clone abort (TID 200/stage 3) contribute 34 exact steps. Each preserves
unpublished authority until it is consumed with the sole reference at retirement
begin, retains identity/stage snapshots, retires the thread before releasing VM and
main storage, and emits no fabricated birth or terminal event. The exact cumulative
five-file slice is archived as
`stability-native-collector-lifecycle-abort-literal-slice-20260915-1`. Corpus
completion, replacement models, source checks and build remain closed.

Five attempt-2 semantic negatives now receive independent
`PASS_SEMANTIC_NEGATIVE_LITERAL_SLICE_ONLY`: birth after runnable, duplicate
terminal, runnable without birth, reference resurrection after retirement begins,
and active TID aliasing. Each failure emits no event, leaves the preceding full
state unchanged and latches incomplete; the later capture-end event uses the exact
retained attempt sequence. Active alias rejection creates no secondary thread row.
The cumulative five-file bytes are archived as
`stability-native-collector-lifecycle-semantic-negative-literal-slice-20260915-1`.
The entire corpus and models remain incomplete and unexecuted.

Six ownership-blocker vectors now receive independent
`PASS_OWNERSHIP_LITERAL_SLICE_ONLY`: retained thread/process references,
irreversibly revoked unpublished authority, zombie before and after parent reap,
main-thread storage retention and VM retention. Exact REF/BUSY failures preserve
state and sticky incompleteness; post-failure zombie recovery retains distinct
event sequence and operation IDs. A first review caught and the bounded correction
fixed those three event IDs plus the early-retirement mutant target. Cumulative
bytes are archived as
`stability-native-collector-lifecycle-ownership-literal-slice-20260915-1`. Whole
corpus/model source, compilation and acceptance remain closed.

Six capture-control vectors now receive independent
`PASS_CAPTURE_CONTROL_LITERAL_SLICE_ONLY`: teardown failure, launcher loss, missing
capture end, zero-capacity event retention, saturated lost-counter overflow and an
unfinished reservation. Zero capacity preserves all 16 lifecycle transitions while
retaining no events and counting every loss; all fault paths remain irreversibly
incomplete. One review correction binds the silent-loss mutant to the materialized
`buffer-full` case. The cumulative bytes are archived as
`stability-native-collector-lifecycle-capture-control-literal-slice-20260915-1`.
Whole corpus/model source, compilation and native/acceptance gates remain closed.

Seven terminal-integrity and source-identity negatives now receive independent
`PASS_IDENTITY_STATUS_LITERAL_SLICE_ONLY`: a wrong raw terminal status, five
separately forged capture/OS-generation/application/process/exec identity fields,
and process/thread domain confusion. Every rejected operation emits no event,
preserves the exact preceding process/thread rows and latches incompleteness; the
following capture end retains distinct operation and event sequence identities.
The first review found one required-name bookkeeping omission, corrected only by
adding the already materialized birth-after-runnable label. Cumulative five-file
bytes are archived as
`stability-native-collector-lifecycle-identity-status-literal-slice-20260915-1`.
The corpus remains incomplete; replacement models, source checks, compilation,
native execution, ABI freeze, application acceptance and production credit remain
closed.

Six multithread vectors now receive independent
`PASS_MULTITHREAD_LITERAL_SLICE_ONLY`: thread-only exit, rejected last-thread
process terminal with a live sibling, live-sibling retirement/VM blockers, two
independent competing group-terminal winner orders with explicit inherited branch
3 thread status, and non-main TID reuse only after the old full identity retires.
No group operation synthesizes a sibling terminal event; the old retired row and
snapshot remain alongside the distinct replacement identity. Cumulative five-file
bytes are archived as
`stability-native-collector-lifecycle-multithread-literal-slice-20260915-1`.
This still releases no whole-corpus/source/model/build/native/ABI/application or
production acceptance.

Independent capacity review returns `CAPACITY_SPEC_GAPS_ONLY`. The contract does
not yet freeze application admission/identity, global retained occupancy, second
application domain constraints or capacity-result precedence. The 129-operation
case is a raw document rejection rather than a semantic result, and the separate
attempt-counter saturation case is still missing. Exact required corrections are
retained in
`stability-native-collector-lifecycle-capacity-contract-gap-review-20260915-1.md`;
no capacity literals are released.

Independent malformed-input review returns `RAW_INVALID_SPEC_GAPS_ONLY`. The raw
entry schema, hash-bound oversized-byte artifact, pool argument policy and separate
coverage accounting are unfrozen, while the current harness never consumes its
empty `raw_invalid` object. Required mutation families and the exit-2/empty-stream/
zero-model-invocation contract are retained in
`stability-native-collector-lifecycle-raw-invalid-contract-gap-review-20260915-1.md`.
No raw-invalid source or execution is accepted.

The distinct attempt-counter saturation vector now receives independent
`PASS_ATTEMPT_OVERFLOW_LITERAL_SLICE_ONLY`. `ATTEMPTS_MAX` with capacity 256 and
one capture-end operation retains no event and saturates both attempts/lost with
overflow, end and incompleteness; the separate zero-capacity `LOST_MAX` vector is
unchanged. Cumulative five-file bytes are archived as
`stability-native-collector-lifecycle-attempt-overflow-literal-slice-20260915-1`.
This brings the materialized ordinary-vector count to 35 without completing the
corpus or releasing source execution.

The additive lifecycle corpus contract now receives scoped independent capacity
and raw-invalid review PASS. Three bounded review corrections require exact
thread-to-parent key projection, a single bounded read whose verified bytes are
the decoded bytes, and fixture-directory containment without symlink traversal.
The accepted text freezes application admission, globally retained occupancy,
capacity precedence, 129-operation document rejection, raw-case representation,
separate coverage and pool arity in
`stability-native-collector-lifecycle-corpus-contract-addendum-20260915-1.md`.
Capacity/raw literals are not yet materialized; whole-corpus/model/source and all
runtime or acceptance gates remain closed.

Three retained-capacity vectors now receive independent
`PASS_CAPACITY_LITERAL_SLICE_ONLY`. Separate traces admit exactly two applications,
four process rows and eight thread rows, then reject the next fresh identity with
`LIMIT` before any event or state mutation. Exact parent projection, sorted rows,
sticky incompleteness and post-failure capture-end sequence identities pass literal
inspection. Cumulative five-file bytes are archived as
`stability-native-collector-lifecycle-capacity-literal-slice-20260915-1`, bringing
the materialized ordinary-vector count to 38. The operation-count/raw matrix and
replacement models remain outstanding.

The bounded raw-invalid mechanism packet receives independent
`PASS_RAW_INVALID_SOURCE_PACKET_ONLY`. It freezes a four-path allowlist, isolated
stdin decoder, pre-build validation order, exact child status/stream contract,
nine first mechanism cases, single-open external artifact handling and separate
raw coverage in
`stability-native-collector-lifecycle-raw-invalid-source-packet-20260915-1.md`.
The current harness still lacks this behavior and the oversized artifact has no
final bound hash, so this is a source-ready packet only; no check, build or runtime
credit follows.

Raw-invalid mechanism source attempt 1 is preserved as rejected before execution.
Its build path could bypass payload checks, parent identity crossed the schema/model
boundary, artifact permissions and error typing were unsafe, pool validation was
unbounded/incomplete and cleanup/tripwire tests were insufficient. Exact four-file
bytes are archived as
`stability-native-collector-lifecycle-raw-invalid-source-failure-20260915-1`.

Bounded attempt 2 receives independent
`PASS_RAW_INVALID_SOURCE_MECHANISM_REVIEW_ONLY`, `PASS_POOL_ARITY_SOURCE_ONLY` and
`PASS_BOUND_RAW_INVALID_EVIDENCE_ONLY`. It adds a dedicated typed decoder, validates
all pools with bounded insertion-independent dependency depth, confines and reads
the oversized artifact once, checks all nine raw cases before any build action and
owns child timeout/output retirement. Self-bound Python 3.9.12 and 3.8.10 logs each
pass the six raw tests and two applicable source-envelope tests (8/8). The original
broad nine-test run is retained: its sole failure is the deliberately unreplaced,
previously rejected attempt-1 Rust model lacking `ProcessRow`; every raw test passed.
The nine-member checkpoint archive is
`stability-native-collector-lifecycle-raw-invalid-source-checkpoint-20260915-2`.
The full malformed/width/authority matrix, replacement models, whole-corpus review,
compilation and every runtime/acceptance gate remain closed.

The next raw work is split by an independent normalized inventory. Decoder input,
ordinary semantic precedence, positive legal boundaries, expected-output oracle
corruption and artifact/cleanup tests remain separate obligations; exact freeze
conditions are recorded in
`stability-native-collector-lifecycle-raw-matrix-inventory-draft-20260915-1.md`.
The first dependency-ready source packet receives independent
`PASS_RAW_AUTHORITY_WIDTH_PACKET_ONLY`. It pins exact base operations and mutations
for 19 authority-forging and shared PID/TID width/type cases, for 28 cumulative raw
cases, along with positive legal boundaries and the common u64 slot rule. The
matrix remains explicitly incomplete and `RAW_FULL_MATRIX_FROZEN` remains false.
No source edit, check, compilation, model run, runtime or acceptance credit follows.

The authority/width source slice now receives independent
`PASS_RAW_AUTHORITY_WIDTH_SOURCE_ONLY` and
`PASS_RAW_AUTHORITY_WIDTH_EVIDENCE_ONLY`. Exactly 19 new inline documents bring the
raw inventory to 28; exact compact-byte tests distinguish integer, integral-float
and boolean mutations and retain the original nine records unchanged. Python
3.9.12 and 3.8.10 each pass all seven bounded decoder tests. The first secondary
path lookup exited 127 before starting a test and is retained as a stale-path
preflight failure, followed by the passing `/usr/bin/python3.8` run. Eleven exact
members are bound by
`stability-native-collector-lifecycle-raw-authority-width-source-checkpoint-20260915-1.tar.gz`.
`RAW_FULL_MATRIX_FROZEN` remains false; no compiler, model, native, application or
production gate has run or receives credit.

Three independent raw-matrix design lanes returned bounded document/vector, pool
and key/domain slices. The dependency-closed 30-case document/vector slice receives
independent `PASS_RAW_DOCUMENT_VECTOR_PACKET_ONLY` and is retained in
`stability-native-collector-lifecycle-raw-document-vector-source-packet-20260915-1.md`.
It would bring the raw inventory to 58 while preserving the accepted 28 and the
false full-matrix gate. Pool accounting and key/domain packets remain separate;
no new source edit or check has begun.

The document/vector slice now receives independent
`PASS_RAW_DOCUMENT_VECTOR_SOURCE_ONLY` and
`PASS_RAW_DOCUMENT_VECTOR_EVIDENCE_ONLY`. Thirty exact negative documents bring
the raw inventory to 58; exact `raw-base` positives and a lexical SHA-256 guard
preserve the accepted first 28 record texts, including newline bytes. Python
3.9.12 and 3.8.10 each pass all eight focused decoder tests. The original stale
28-count test failure and three review corrections are retained in the 12-member
`stability-native-collector-lifecycle-raw-document-vector-source-checkpoint-20260915-1.tar.gz`.
The full matrix flag remains false; compilation, models, native execution and all
acceptance counters remain untouched.

After subtracting the accepted 58 cases, independent review rebases the next
key/domain slice to remove duplicate operation-ID mechanisms. After correcting an
operation-reference wording ambiguity, the resulting 30 exact negatives receive
independent `PASS_RAW_KEY_DOMAIN_PACKET_ONLY` and are retained in
`stability-native-collector-lifecycle-raw-key-domain-source-packet-20260915-1.md`.
The separate gap inventory keeps full per-component key, pool/budget, remaining
envelope, positive, semantic and oracle obligations open. No source edit or check
has begun.

The key/domain source slice now receives independent
`PASS_RAW_KEY_DOMAIN_SOURCE_ONLY` and `PASS_RAW_KEY_DOMAIN_EVIDENCE_ONLY`.
Thirty exact cases bring the raw inventory to 88, with the accepted first 58
record texts SHA-bound and relationship-consistent legal key controls. Python
3.9.12 and 3.8.10 each pass all nine focused decoder tests. A review caught an
anti-conflation test mutating `model_only` instead of the boolean key slot; the
structured correction and original finding are retained in the 11-member
`stability-native-collector-lifecycle-raw-key-domain-source-checkpoint-20260915-1.tar.gz`.
Full per-component key coverage, pools/budgets and remaining raw/oracle work stay
open; the matrix flag is false and no compiler, model, native or acceptance gate ran.

The independently rebased pool slice retains 22 negative records and eight legal
controls atop the accepted 88 cases, for 110 cumulative raw cases if materialized.
Its dependency-depth, syntax-depth and expansion-budget arithmetic is independently
confirmed and receives independent `PASS_RAW_POOL_PACKET_ONLY` in
`stability-native-collector-lifecycle-raw-pool-source-packet-20260915-1.md`.
Two controls are already covered and six are new; node/output budgets and broader
pool/key/raw closure remain deferred. No pool source edit or check has started.

The pool source slice now receives independent `PASS_RAW_POOL_SOURCE_ONLY` and
`PASS_RAW_POOL_EVIDENCE_ONLY`. Twenty-two exact negatives bring the raw inventory
to 110; dependency chains in both orders, unused syntax depth and the paired
175,020/175,021-byte expansion traversal boundary are checked without claiming
node or serialized-output coverage. Python 3.9.12 and 3.8.10 each pass all ten
focused decoder tests. The exact source, streams and arithmetic audit are retained
in the 11-member
`stability-native-collector-lifecycle-raw-pool-source-checkpoint-20260915-1.tar.gz`.
The full raw matrix, replacement models, compilation, native execution and all
acceptance gates remain closed.

Post-110 audits split the next work into a three-case envelope completion slice,
a separate 19-case operation/argument slice and an independently draftable model
foundation. Full model transitions remain blocked on explicit decision tables.
The selected envelope slice also pins legal whitespace and the exact 1-MiB input
boundary in
`stability-native-collector-lifecycle-raw-envelope-source-packet-20260915-1.md`.
It receives independent `PASS_RAW_ENVELOPE_PACKET_ONLY`; no source edit or new
check has started.

The envelope slice now receives independent `PASS_RAW_ENVELOPE_SOURCE_ONLY` and
`PASS_RAW_ENVELOPE_EVIDENCE_ONLY`. Three exact container-site negatives bring the
raw inventory to 113; whitespace, unresolved-mutant decoder isolation and exactly
1,048,576 input bytes are accepted. Python 3.9.12 and 3.8.10 each pass all eleven
focused decoder tests. Ten hash-bound members are retained in
`stability-native-collector-lifecycle-raw-envelope-source-checkpoint-20260915-1.tar.gz`.
The operation/argument slice and full raw/oracle matrix remain open; compilation,
models, native execution and acceptance remain closed.

The separate operation/argument slice is now frozen as a source-only packet in
`stability-native-collector-lifecycle-raw-operation-argument-source-packet-20260915-1.md`.
Its 19 independent mutations cover eight operation/terminal numeric boundaries
and eleven opcode-specific unused argument positions, for 132 cumulative raw cases
if materialized. The exact first-113 lexical prefix and decoder-positive boundary
controls are bound, and independent review returns
`PASS_RAW_OPERATION_ARGUMENT_PACKET_ONLY`. No source edit or new check has started;
the full raw/oracle matrix, compilation, models, native execution and acceptance
remain closed.

The operation/argument source slice now receives independent
`PASS_RAW_OPERATION_ARGUMENT_SOURCE_ONLY` and
`PASS_RAW_OPERATION_ARGUMENT_EVIDENCE_ONLY`. Its first review failure for missing
integer-versus-boolean/float anti-conflation assertions is preserved; the bounded
test correction then passes. Nineteen exact negatives bring the raw inventory to
132, with the first 113 lexical records unchanged. Python 3.9.12 and 3.8.10 each
pass all twelve focused decoder tests. The exact source, oversized artifact,
packet, reviews, commands and streams are retained in the 10-member
`stability-native-collector-lifecycle-raw-operation-argument-source-checkpoint-20260915-1.tar.gz`.
The full raw/oracle matrix remains open; compilation, models, native execution and
all acceptance gates remain closed.

Post-132 review selects an independent one-case expansion-node boundary as the
next raw source packet. A separate five-case artifact I/O cleanup packet is ready
after it, while paired model transitions remain blocked on six explicit decision
tables. The selected node packet is documented in
`stability-native-collector-lifecycle-raw-expanded-node-source-packet-20260915-1.md`;
after correcting and preserving two packet-wording findings, independent review
returns `PASS_RAW_EXPANDED_NODE_PACKET_ONLY`. No new source edit or check has
started.

The expansion-node slice now receives independent
`PASS_RAW_EXPANDED_NODE_SOURCE_ONLY` and
`PASS_RAW_EXPANDED_NODE_EVIDENCE_ONLY`. Its exact 262,144-node positive and
262,145th-node rejection bring the inventory to 133 while preserving the first
132 lexical records. Python 3.9.12 and 3.8.10 each pass all thirteen focused
decoder tests. Ten hash-bound members are retained in
`stability-native-collector-lifecycle-raw-expanded-node-source-checkpoint-20260915-1.tar.gz`.
The full raw/oracle matrix remains open; compilation, models, native execution
and all acceptance gates remain closed.

The next independent source packet targets five exceptional artifact I/O cleanup
paths plus one positive descriptor-lifetime control without adding raw cases. It
is frozen provisionally in
`stability-native-collector-lifecycle-artifact-io-cleanup-source-packet-20260915-1.md`;
it receives independent `PASS_ARTIFACT_IO_CLEANUP_PACKET_ONLY`. No source edit or
check has started.

The artifact cleanup slice now receives independent
`PASS_ARTIFACT_IO_CLEANUP_SOURCE_ONLY` and
`PASS_ARTIFACT_IO_CLEANUP_EVIDENCE_ONLY`. Its first source review failure for an
exact `OSError` class assertion is preserved and corrected. Five injected EIO
paths and the positive control pass all six focused tests under Python 3.9.12 and
3.8.10. Per-acquisition descriptor tracking, exact EBADF closure, immutable
artifact bytes and non-artifact execution guards are retained in the 10-member
`stability-native-collector-lifecycle-artifact-io-cleanup-source-checkpoint-20260915-1.tar.gz`.
Raw inventory remains 133; the raw/oracle matrix, compilation, models, native
execution and all acceptance gates remain incomplete, with every execution and
acceptance gate closed.

Post-checkpoint audits select strict output-oracle comparison as the next source
slice, ahead of the separate one-case expansion-depth boundary. The 13-case packet
in `stability-native-collector-lifecycle-output-oracle-source-packet-20260915-1.md`
requires each implementation to match an independent literal even when both agree
on a corruption and requires both one-sided comparison directions. After preserving
the missing-direction packet review failure, independent review returns
`PASS_OUTPUT_ORACLE_PACKET_ONLY`. Six model operation families still lack complete
decision tables. No new source edit or check has started.

The output-oracle source slice now receives independent
`PASS_OUTPUT_ORACLE_SOURCE_ONLY` and `PASS_OUTPUT_ORACLE_EVIDENCE_ONLY`. Its two
helper-site assertion failures and an evidence-manifest row-count failure are
preserved before bounded corrections. Python 3.9.12 and 3.8.10 each pass all
three focused tests: both one-sided comparisons, agreed corruption, 13 exact
corruptions, and the baseline with and without terminal LF. The canonical
one-row literal is independently bound as 192 compact bytes. The corrected
10-member archive and the byte-exact failed archive are retained. Raw inventory
remains 133; the raw/oracle matrix, compilation, models, native execution and
all acceptance gates remain incomplete and closed.

The next one-case raw slice is frozen in
`stability-native-collector-lifecycle-raw-expanded-depth-source-packet-20260915-1.md`.
It isolates supplied-argument expansion depth: an exact depth-32 positive and
depth-33 rejection, while preserving the first 133 lexical records. Independent
review returns `PASS_RAW_EXPANDED_DEPTH_PACKET_ONLY`; if materialized, the raw
inventory becomes 134. No source edit or new check has started, and every model,
native, application and production gate remains closed.

The expanded-depth source slice now receives independent
`PASS_RAW_EXPANDED_DEPTH_SOURCE_ONLY` and
`PASS_RAW_EXPANDED_DEPTH_EVIDENCE_ONLY`. The exact depth-32 positive and
depth-33 rejection bring the raw inventory to 134 while preserving the first
133 lexical records. Python 3.9.12 and 3.8.10 each pass all fourteen focused raw
decoder tests. The misplaced-vector source, wrong-selector errors, seven stale
inventory assertions and missing exact exception-class assertions are retained
as original failures in the 13-member archive. The full raw/oracle matrix remains
open; compilation, models, native execution and all acceptance gates remain
closed.

Post-134 audits leave all six lifecycle decision families blocked on incomplete
source-bound policy tables and select aggregate unused-pool preflight accounting
as the next raw slice. The exact adjacent-character boundary is frozen in
`stability-native-collector-lifecycle-raw-preflight-aggregate-byte-source-packet-20260915-1.md`;
independent review returns `PASS_RAW_PREFLIGHT_AGGREGATE_BYTE_PACKET_ONLY`. If
materialized it adds one raw case for 135 total. No source edit or check has
started, and all model, native, application and production gates remain closed.

The aggregate unused-pool preflight-byte slice now receives independent
`PASS_RAW_PREFLIGHT_AGGREGATE_BYTE_SOURCE_ONLY` and
`PASS_RAW_PREFLIGHT_AGGREGATE_BYTE_EVIDENCE_ONLY`. Its exact adjacent-character
boundary adds one rejection for 135 raw cases while preserving the first 134
lexical records. Python 3.9.12 and 3.8.10 each pass all fifteen focused decoder
tests. The 488,540-byte fixture, exact budget instances and all source/log hashes
are retained in the 10-member archive. The full raw/oracle matrix remains open;
compilation, models, native execution and all acceptance gates remain closed.

The next independent source packet covers `run()`'s post-capture output envelope:
nonzero status, nonempty stderr and the exact 1-MiB stdout boundary, plus two
positive controls. It is frozen in
`stability-native-collector-lifecycle-output-envelope-source-packet-20260915-1.md`;
independent review returns `PASS_OUTPUT_ENVELOPE_PACKET_ONLY`. This remains
mock-only validation and does not prove live collection bounds. Raw inventory
stays 135; no source edit or new check has started and every execution and
acceptance gate remains closed.

The output-envelope source slice now receives independent
`PASS_OUTPUT_ENVELOPE_SOURCE_ONLY` and `PASS_OUTPUT_ENVELOPE_EVIDENCE_ONLY`.
Three pre-parse rejections and two positive controls pass all five tests under
Python 3.9.12 and 3.8.10. The first evidence archive's missing command provenance
is preserved at its exact hash; corrected logs bind commands, versions, exits and
streams in the replacement 10-member archive. This proves mock-only post-capture
validation, not live collection bounds. Raw inventory stays 135, and compilation,
models, native execution and all acceptance gates remain closed.

Post-135 audits select aggregate unused-pool preflight node exhaustion as the
next raw slice. Its exact adjacent-zero boundary is frozen in
`stability-native-collector-lifecycle-raw-preflight-aggregate-node-source-packet-20260915-1.md`;
independent review returns `PASS_RAW_PREFLIGHT_AGGREGATE_NODE_PACKET_ONLY`. If
materialized, it raises raw inventory to 136 while leaving about 35 KiB fixture
headroom. No source edit or new check has started, and all execution and
acceptance gates remain closed.

The aggregate unused-pool preflight-node slice now receives independent
`PASS_RAW_PREFLIGHT_AGGREGATE_NODE_SOURCE_ONLY` and
`PASS_RAW_PREFLIGHT_AGGREGATE_NODE_EVIDENCE_ONLY`. Its adjacent-zero boundary
adds one rejection for 136 raw cases while preserving the first 135 lexical
records. After preserving the missing exact-size assertion, Python 3.9.12 and
3.8.10 each pass all sixteen focused decoder tests. The exact 1,013,510-byte
fixture remains below its unchanged 1-MiB cap and is retained with all hashes in
the 10-member archive. The raw/oracle matrix and every execution and acceptance
gate remain incomplete and closed.

A parallel source-bound TID-assignment audit now receives independent
`PASS_TID_ASSIGNMENT_EVIDENCE_DRAFT_ONLY`. Nine exact native source files, three
literal-review records and the retained START protocol archive distinguish slot
reservation/release and unchecked assignment from model identity semantics.
Same/different reassignment, phase/domain permission, alias classification,
reference/authority interaction and CLOSED precedence remain unspecified, so the
`TID_ASSIGN` decision family is not frozen and no transition source is released.

The next independent output-schema packet isolates exact Boolean typing in the
process and thread registries. It is frozen in
`stability-native-collector-lifecycle-output-registry-boolean-source-packet-20260915-1.md`;
independent review returns `PASS_OUTPUT_REGISTRY_BOOLEAN_PACKET_ONLY` for four
integer-for-Boolean rejections and two schema-only positive scenarios. Raw count
stays 136; no source edit or check has started and all execution and acceptance
gates remain closed.

The output-registry Boolean source slice now receives independent
`PASS_OUTPUT_REGISTRY_BOOLEAN_SOURCE_ONLY` and
`PASS_OUTPUT_REGISTRY_BOOLEAN_EVIDENCE_ONLY`. Four integer-for-Boolean
rejections and two positive schema scenarios pass all five focused tests under
Python 3.9.12 and 3.8.10. The initial missing exact compact-byte expectations are
preserved as a review failure; the corrected source independently binds each
unique literal-token mutation before collector invocation. The exact ten-member
archive retains both command-prefixed logs and all source, interpreter and
literal hashes. This is post-capture mocked-output evidence only. Raw inventory
stays 136, and compilation, models, native execution and every acceptance gate
remain closed.

The next independently reviewed output-schema packet covers the three Boolean
fields in the control array. It is frozen in
`stability-native-collector-lifecycle-output-control-boolean-source-packet-20260915-1.md`;
review returns `PASS_OUTPUT_CONTROL_BOOLEAN_PACKET_ONLY` for three exact
integer-for-Boolean rejections and two schema-only positive scenarios. Raw
inventory remains 136. No source edit or execution has started, and every
compiler, model, native, application and production gate remains closed.

The output control-Boolean source slice now receives independent
`PASS_OUTPUT_CONTROL_BOOLEAN_SOURCE_ONLY` and
`PASS_OUTPUT_CONTROL_BOOLEAN_EVIDENCE_ONLY`. Three exact integer-for-Boolean
rejections and two schema-only positive scenarios pass all four focused tests
under Python 3.9.12 and 3.8.10. The ten-member archive binds independently
handwritten compact literals, exact mutation bytes, validator ordering, pinned
interpreters and command-prefixed logs. This remains post-capture mocked-output
validation. Raw inventory stays 136, and all compilation, model, native,
application and production gates remain closed.

The next reviewed raw-decoder packet isolates the capture component of a full
key at the `u64` upper-bound adjacency. It is frozen in
`stability-native-collector-lifecycle-raw-key-capture-u64-source-packet-20260915-1.md`;
review returns `PASS_RAW_KEY_CAPTURE_U64_PACKET_ONLY`. If materialized, its one
position-specific record raises raw inventory from 136 to 137 while preserving
the first 136 lexical records. No source edit or execution has started, and all
compiler, model, native, application and production gates remain closed.

The raw capture-key `u64` adjacency now receives independent
`PASS_RAW_KEY_CAPTURE_U64_SOURCE_ONLY` and
`PASS_RAW_KEY_CAPTURE_U64_EVIDENCE_ONLY`. Its one exact upper-bound rejection
raises raw inventory to 137 while preserving the first 136 lexical records.
After correcting harness inventory and exact-size assertions, Python 3.9.12 and
3.8.10 each pass all 17 focused raw-decoder tests. The initial failing terminal
stream and exact failing source hash were not retained; the hash-bound
summary-only record discloses that evidence limitation and cannot support a
full original-failure-preservation claim. The corrected ten-member archive binds
all source, input, interpreter and command-log hashes. The raw matrix remains
open, and every compiler, model, native, application and production gate remains
closed.

The additive capture-closure policy now receives independent
`PASS_CAPTURE_CLOSED_POLICY_DECISION_ONLY`. It makes the first end irrevocable,
places every later schema-valid operation behind `CLOSED` before semantic checks,
and freezes zero-event/preserved-state/sticky-incomplete effects. Six independent
exact input/full-output witnesses remain mandatory before a source packet can be
released. No literal, fixture or model has been materialized; TID semantics and
the other lifecycle decision families remain unresolved, and all execution and
acceptance gates remain closed.

The six capture-closure literals now have an independently reviewed source
packet with `PASS_CAPTURE_CLOSED_LITERALS_PACKET_ONLY`. It freezes five exact
complete-state suffixes, one incomplete-state repeat end, all full registry and
control rows, 88 expanded steps, ordinary inventory 38 to 44, and two in-process
schema-first controls. The first packet review failure is preserved before the
artifact, vector-envelope and malformed-control corrections. Both rejected
MODEL1 sources remain excluded and unexecuted. No fixture or test source has yet
been materialized, raw inventory stays 137, and every compiler, model, native,
application and production gate remains closed.

The capture-closure source slice now also receives independent
`PASS_CAPTURE_CLOSED_LITERALS_SOURCE_ONLY` and
`PASS_CAPTURE_CLOSED_LITERALS_EVIDENCE_ONLY`. After preserving one source-review
failure, the four focused methods require exact duplicate-free inventories, real
wire validation, independent compact byte literals and zero execution calls.
Python 3.9.12 and 3.8.10 each pass 4/4. The exact ten-member archive retains six
witnesses and 88 expanded steps; ordinary inventory is 44 and the unchanged
first 137 raw records reproduce their lexical hash. The incompatible MODEL1
sources remain excluded and unexecuted, so this is literal/schema source evidence
only. The lifecycle decision families, full matrices and every execution and
acceptance gate remain incomplete and closed.

The next independently reviewed output-schema packet isolates exact typing of
the top-level output row identifier. It binds one positive R1 literal and exact
Boolean-`true` and integral-float-`1.0` mutations; review returns
`PASS_OUTPUT_ROW_ID_TYPE_PACKET_ONLY`. Both negatives must reject at the exact
integer helper before any registry, key or oracle validation. No source edit or
new check has started. Ordinary inventory remains 44, raw inventory remains 137,
and every compiler, model, native, application and production gate stays closed.

The output row-ID type slice now also receives independent
`PASS_OUTPUT_ROW_ID_TYPE_SOURCE_ONLY` and
`PASS_OUTPUT_ROW_ID_TYPE_EVIDENCE_ONLY`. Python 3.9.12 and 3.8.10 each pass all
three focused methods: exact integer `1` accepts, while Boolean `true` and
integral float `1.0` reject at the exact integer helper before registry or oracle
work. The ten-member archive binds all source, literal, interpreter and command
log hashes. This remains mocked post-capture schema evidence only. Ordinary 44,
raw 137 and its lexical hash are unchanged; the full matrices and all execution
and acceptance gates remain incomplete and closed.

Priority returns to the earlier M02-B collector fault gap. The corrected
storage-fault-v2 producer/oracle packet now receives independent
`PASS_STORAGE_FAULT_V2_SOURCE_PACKET_ONLY`. It freezes seven exact selectors,
target-only collector seams, parent-durable witness ownership, collector-origin
reap/EOF/cleanup observations, per-acquisition descriptor identity and bounded
identity-safe cleanup. Two packet-review failures are preserved before the
observation, record-budget, BEFORE/AFTER, READY/RELEASE and descriptor-reuse
corrections. Both rejected v1 source failures and their archives remain intact.
No v2 source, build or root execution has started, and this grants no collector,
application or production acceptance.

Storage-fault-v2 source attempts 1 and 2 exposed and preserve two focused-test
failures: the extra-packet negative was diagnosed first as receipt ordering, and
the report-sync negative edited a non-sync observation. After narrow corrections,
both pinned interpreters passed 6/6, but independent Astra/high review returns
`FAIL_SOURCE`. It found an off-by-one live ACK, incompatible generic packet
schemas, missing durable owner/output/filesystem evidence, incomplete adopted-
child cleanup, incorrect deadline/packet-limit behavior, insufficient independent
oracle joins and synthetic fixtures that concealed those faults. The complete
review failure is archive SHA256
`f09c32e1cd7a3ca693371fa3a1c898983ac0abafe393f0c387a6bf5e1fd9db01`.
Correction WIP now binds ACKs to their emitted sequence, uses an absolute C ACK
deadline across EINTR, accepts packet 32 while rejecting packet 33, and fixes the
two semantic negatives; both interpreters again pass 6/6. Its source-only archive
SHA256 is `4f1aaad972b137071a5722b4528415f68f34d12052eefdc8cf9890c15d98f689`.
Strict per-kind schemas, durable owner artifacts, adopted-child cleanup,
phase-relative owner deadlines and exact independent oracle fixtures remain open.
Source review, build, root, native, application and production gates remain closed.

An exact storage-fault-v2 packet correction now receives independent
`PASS_PACKET_ONLY` at SHA256
`0feaad14f408acf806fb391195e519a16de60cc41ffdb24cd9721ea432b90089`.
Two preserved packet-review failures first exposed missing create/cleanup values,
request size transitions, an inexact owner schema, and inability to represent
unavailable identities or verify cleanup timing. The accepted correction freezes
all seven real schedules/phases, strict kind schemas, imported request acquisition
zero, sanitized complete eight-entry collector environment, byte-identical durable
owner publication, tagged unavailable/unreaped states and trigger-relative 22-
second cleanup with 16/1/5 stage bounds. This releases a new source correction
only. The current untracked implementation still has the earlier source-review
blockers and is not accepted; compiler, build, root, native, application and
production gates remain closed.

A final retained-input correction now receives independent
`PASS_INPUT_PACKET_ONLY` at SHA256
`e6eacb0c70e1175a78076c695c38c5d8a7293d58f10176c112e0072df7dcee93`.
Its preserved first review failure found that reviewed ELF bytes were not bound
to the actually executed path. The correction requires four canonical pinned-fd
stable input reads, exact byte/hash records and canonical `argv[0] == --elf`
before fork; the oracle repeats every join. This closes only source authority.
The in-progress untracked producer/owner/oracle correction is not independently
accepted, and every compiler, build, root, native, application and production
gate stays closed.

The outer cleanup evidence union now receives independent
`PASS_CLEANUP_PACKET_ONLY` at SHA256
`521e5075a576ade72603e4867cc0b831ada163449ab5b60ca3adb1e755a90a44`.
It adds repeated double-identity owned scans and terminal empty/ECHILD evidence,
so killing or reaping an adopted parent cannot conceal a newly reparented child.
Source attempts 3 and 4 preserve two newly exposed test failures plus the first
partial implementation review. The current correction fixes the ACK binding,
C serializer arity, nonblocking absolute transport, original-path symlink/FIFO
checks, repeated descendant scans, bounded signal checks, early descriptor unwind
and strict per-kind/schedule validation before ACK. Seven focused methods pass
under both pinned interpreters, but the oracle and synthetic positive fixtures
still require replacement and the current partial source needs fresh review.
No compiler, build, root, native, application or production gate is released.

The stable owner-identity addition now receives independent
`PASS_OWNER_PACKET_ONLY` at packet SHA256
`4624b42a5f6fd63dacc8bcb881c7f8a31f38c5addffc4e74ff9ad3714f43caa5`.
It requires two matching `/proc/self/stat` observations before socket creation
or fork and joins that owner birth to the collector PPID. Strict-oracle work
then preserved source failures 5 through 7: replacement of the old placeholder
positives, a selector-4 phase-scope error, and a selector-4 absent-report setup
capture error. Both pinned interpreters subsequently pass all eight focused
methods with exact report keys, nested process/setup/source/sink structures,
production-shaped events, report/witness joins and exact-class/message semantic
negatives. Fresh full independent review nevertheless returns `FAIL_SOURCE`:
pre-ACK field/phase validation, request-sync identity, buffered pre-flush size,
phase deadlines, sticky cleanup mismatch, first-error-preserving unwind and the
shared owner/oracle layout remain incomplete. Corrections have started, but no
source acceptance, compiler, build, root, native, application or production gate
is released.

The broader storage-fault-v2 correction authority is now closed by additive
packet 11 at SHA256
`274a51378b0172b4728eae3557b1f1b7a1c65708887b7980bfec1b205bc06f1f`
with independent `PASS_CORRECTION_PACKET_ONLY`. Rejected packets 6 through 10
remain preserved with their exact reviews. The accepted union freezes strict
pre-ACK state and acquisition joins, observable 180/60-second collection bounds,
trigger-relative cleanup, buffered report-prefix handling, immutable ordered
error/result publication, three retained runtime inputs, an independently waited
supervisor, subreaper adoption cleanup, a 248-second total bound, and exact
non-overlapping owner identity/wait states. This releases source correction only.
The source is not accepted; fresh full review remains mandatory before any
compiler, root, native, application or production execution.

Window-end WIP checkpoint 4 preserves the authorized source correction at
archive SHA256
`056734884bc514d306071158501b9f69b660c88da4febf18a3e9191093d9f053`.
Python 3.9.12 and 3.8.10 each pass 10/10 focused methods. Implemented bytes add
exact pre-ACK types/phases, request/report identity joins, buffered pre-flush
handling, production-shaped report/event validation, observable owner deadlines,
fresh-root retained runtime inputs, and partial ordered owner-error/sticky-cleanup
handling. The next task is independent review of unreviewed packet 12 SHA256
`d7adc51450fd91420e9944cbbb8bc488758e275174452609accccf8deb735f70`,
which resolves nullable birth evidence for a safely signaled unreaped direct
owner. Then finish exception precedence, implement/test the source-bound
supervisor and supervisor/error oracle unions, and request fresh full source
review. No build or guest process is live. The only retained live identities are
launcher 776516, launcher worker 776518 and Codex app-server 776520, all started
2026-09-14 21:32:56 PDT. All three child agents are joined/completed. Source,
compiler, root, native, application and production gates remain closed.

Timestamp correction: packet-review records `20260915-11` through `-14` contain
mistaken future 16:27-16:51 UTC sequence labels. Host UTC was re-observed as
16:23:59 at this checkpoint. Their immutable message/hash order remains the
authority; those four `recorded_utc` values do not represent host wall time.

The final work-window checkpoint preserves source failure attempt 8 at archive
SHA256 `b623017859e7242f2d8640e0158e10800b00e7a7a394a6d3ded91c27c47a4c0b`.
After repairing the synthetic positive chronology, its older negative mutation
fell outside the cleanup interval and produced `owner cleanup event time` rather
than the intended order rejection. The exact Python 3.9.12 failure stream and
all source bytes remain immutable in the archive; the untracked failing test is
intentionally retained without a window-end correction or rerun.

Packet 12 receives independent `FAIL_DIRECT_OWNER_EVENT_PACKET_ONLY` at SHA256
`d7adc51450fd91420e9944cbbb8bc488758e275174452609accccf8deb735f70`.
Its replacement packet 13 receives independent
`PASS_DIRECT_OWNER_EVENT_PACKET_ONLY` at SHA256
`db607e3b89d7cdf0fbca6e69fe8ea29daa07b9c9cd7b55daae2ba4b0b91eee0a`.
That pass freezes only the exclusive-wait/no-auto-reap rule, monotonic direct
owner authority, later-observed matching births and nullable adopted historical
waits. It is not source or runtime acceptance.

Fresh full review of owner SHA256
`56c934dfdc7909c3568682bab58c8b42664e07110a3e353c81967145bdc87c30`,
oracle SHA256 `7e4f7308265c5bd535dfc703f6069023ef818b21c40b818a59a029717c960d41`
and test SHA256 `39802553c9433c3dff2b183c02507a25f1ba3aa8ccbbb83e01a78bd759b28643`
remains `FAIL_SOURCE`. P0 blockers are false zero exit, loss of first-exception
precedence and cleanup bypass immediately after fork. P1 blockers cover cleanup
stickiness/schema, receipt-bound deadlines, fresh-root/setup unwind, terminal
serialization/publication and incomplete pre-ACK semantic gates. The coverage
audit additionally requires exact error partition/publication tests, deadline
joins, durable runtime layout, cleanup tagged unions and supervisor status,
identity and wait controls.

Next window, in order: correct only the retained chronology negative timestamp
inside the cleanup interval and rerun Python 3.9.12 plus 3.8.10; implement the
first-exception ledger, unconditional post-fork cleanup and exit-125 contract;
complete deadline, cleanup and durable-publication validators/tests; then
implement and test the packet-bound supervisor with status-before-evidence-read.
Request a fresh full independent source review only after those controls pass.
Do not compile, use root, launch a guest or claim an application/production gate.

At the final observation, the active campaign identities are launcher 1492539,
launcher worker 1492541 and Codex app-server 1492543, started 2026-09-15
11:38:17-18 PDT. The previously recorded 776516/776518/776520 identities are no
longer present. No build, compiler, guest, QEMU, mcexec or IHK process is live.
All three child reviewers are joined/completed, and future launcher continuations
are user-paused. The OS goal remains incomplete and is not resumed or marked
complete by this checkpoint.

Window-end checkpoint 6 preserves the next exact source state at WIP archive
SHA256 `9afef9611bed413a4dd23bf4621239e6f776b4cee8154dcb7407cbc988318f9b`.
Python 3.9.12 and 3.8.10 each pass 29/29 source-only tests, and all four edited
Python files compile. These checks do not accept the source. The new supervisor
file is intentionally partial: it contains bounded helper code but its main
path returns 125 after input validation, so it is neither runnable nor accepted.

Original source-test failure attempt 9 is preserved at archive SHA256
`f466ea005966f1265c31efe322ecc2afa7779c193bb51624ae6dc3e33c3859c2`.
Packet 14 receives independent `FAIL_SUPERVISOR_GAP_PACKET_ONLY` at SHA256
`d8c39438d70e46f065668be9ed58fc13274a502837ca29b4ffeda9ca390413f7`.
Its replacement packet 15 receives independent
`PASS_SUPERVISOR_GAP_PACKET_ONLY` at SHA256
`bb3a662fe4d729da08ea9ff4eaddcba632585565bc92e4547ee4ef83b52ded1a`.
That packet pass releases only the exact supervisor-gap source contract; it is
not source, compiler, runtime, application or production acceptance.

The latest full owner/oracle review is `FAIL_OWNER_ORACLE_SOURCE` for its exact
older hashes. Five of its six findings were corrected in later bytes, but those
later bytes are unreviewed; real mocked `bounded_cleanup` transition coverage
remains open. Next tasks are to add that coverage, complete the packet-15
supervisor orchestration and failure cleanup, bind it in prepare/packet inputs,
require its exact result in oracle fixtures, and obtain fresh full independent
source review. No compilation, root use or guest execution is authorized before
that review passes.

At 2026-09-15T19:16:11Z the only retained campaign identities are launcher
1492539, launcher worker 1492541 and Codex app-server 1492543, started
2026-09-15 11:38:17-18 PDT. No build, compiler, guest, QEMU, mcexec, IHK, Cargo,
Rust, GCC or Clang process is live. All three child agents are joined/completed,
new dispatch is stopped and future launcher continuations remain user-paused.
The whole-OS goal remains incomplete and is not resumed or marked complete.

Window-end checkpoint 7 preserves source failure attempts 10 and 11 at archive
SHA256s `1ff7b0341d4f3ee7ab9aa1ed18ff6661d7d5035666559029ca8602b8ef456acf`
and `10fd9881d5f6f5bb24d8361e8aaaa9e80f46a0d5b26f4963f16ca225ec273ab8`.
It preserves the exact current WIP, including both checkpoint-rerun failures,
at archive SHA256
`e899c6b1ac0c954deb62484dd309f8f4cd728be9e730f92c0e7f037ac6036214`.
After correcting only the cleanup mock interface, Python 3.9.12 and 3.8.10
each pass 38/38 source-only tests and all edited Python files compile.

Fresh independent review attempt 8 is `FAIL_SOURCE` for its exact reviewed
snapshot. P0 blockers are stale sentinel identity/ECHILD signal authority and
post-fork failure paths that can abandon retirement. P1 blockers are incomplete
oracle cleanup/owner-wait joins and loss/non-draining of bounded pipe prefixes.
The current supervisor SHA256
`34a61c142b2d74b20f0b1460181f1892836fcf1e283ff681c5398011c0a115f2`
contains a later deadline patch and is unreviewed; it does not supersede the
failure. Source, compiler, root, native, application and production gates stay
closed.

Next window, in order: repair immediate-pair sentinel identity and terminate
authority on ECHILD; make every post-fork exception retain bounded cleanup and
evidence; make oracle require the complete cleanup state machine and direct
owner wait/signal joins; retain pipe prefixes and drain during cleanup; add real
`run_supervisor`/`spawn_owner`, packet-15 matrix, partial-spawn,
descendant-writer, cleanup-exception and durable rollback controls. Rerun both
Python versions and request a fresh full review only after the exact bytes are
stable. Do not compile native code, use root, launch a guest or claim acceptance
before that review passes.

At 2026-09-15T19:42:41Z the only retained campaign identities remain launcher
1492539, launcher worker 1492541 and Codex app-server 1492543, started
2026-09-15 11:38:17-18 PDT. No build, compiler, guest, QEMU, mcexec, IHK, Cargo,
Rust, GCC or Clang process is live. All three child agents are joined/completed,
new dispatch is stopped and future launcher continuations remain user-paused.
The whole-OS goal remains incomplete and is not resumed or marked complete.

The new continuous launcher resumed the campaign and preserves attempts 12
through 16 plus independent source review attempt 9. Review 9 is `FAIL_SOURCE`
for exact supervisor/owner/oracle/test hashes `ec666454/a73edf9f/9f66a85f/
7986129e`: ECHILD authority crossed layers incorrectly, cleanup exceptions could
discard retirement evidence, owner cleanup and oracle joins were incomplete,
pipe overflow lost its prefix, and prepare could leak descriptors. Its exact
input archive SHA256 is
`74cd28d9f662af70622c9280878612258bf8efe1dcd2bf2cfa20926e9e7b7e10`.

The current unreviewed correction is preserved in
`stability-linux-collector-storage-fault-v2-source-wip-20260915-10` at archive
SHA256 `e9a177df2391724cf3f3c13fcb6d0eb096020873bf593f151def2c77e0e033cd`.
Python 3.9.12 and 3.8.10 each pass 49/49 source-only tests and both compile the
four Python sources. New controls cover retained overflow prefixes, partial and
parent-close spawn ownership, packet-15 positive preflight stages/deadlines,
actual final rollback, direct/adopted wait-signal joins, terminal ECHILD, exact
adopted-reap equality and prepare descriptor unwind. These bytes are not source
accepted. The supervisor's last-resort unexpected cleanup exception path still
needs stateful retirement preservation without future timestamps or closed-union
schema drift; packet-15 invalid flag/time and unreaped-sentinel controls remain
incomplete. Do not compile the collector or use root before fresh full source
review passes.

Next tasks, in order: (1) replace the supervisor's outer placeholder fallback
with caller-owned mutable cleanup state and actual bounded continuation; (2) add
invalid packet-15 combinations plus cleanup-exception/descendant-writer controls
and rerun both interpreters; (3) obtain fresh exact-byte independent source review,
then checkpoint a released build packet only if it passes. The planning index is
locally repaired for the concurrent one-line README shift and passes all 14
milestones, 68 tasks, 130 gates, seven language gates and 273 cases; its edited
index remains unstaged with the concurrent launcher documentation.

At 2026-09-15T23:28:25Z the live campaign identities are launcher 1676703,
launcher worker 1676707 and Codex app-server 1676709, started 2026-09-15
15:51:14 PDT. No build, compiler, guest, QEMU, mcexec, IHK, Cargo, Rust, GCC or
Clang process is live. All bounded child agents are joined/completed. Host free
space is 68 GiB and scratch free space is 23 GiB. Counters remain 0/273 accepted
application cases, 2/4 narrow fault modes, 6/130 production gates, 350/10,000
points and 0/7 language gates; this checkpoint is not OS completion.

Window-end checkpoint 11 preserves the post-checkpoint bounded worker results
at archive SHA256
`c2c42633654f73036f2adc9d9031181eb8abfd560563b81a2ec79dc4261bc6a4`.
The supervisor now has a caller-owned mutable cleanup session and bounded
recovery continuation; the oracle adds packet-15 NOT_SPAWNED preflight record
validation. These exact bytes are WIP, not source accepted. Python 3.9.12 and
3.8.10 each report 47/49: the owner-identity and deadline negative mutations
are rejected first as `supervisor complete state`, rather than their required
specific errors. Both interpreters compile the two changed files. The original
failure is retained in
`stability-linux-collector-storage-fault-v2-window-end-20260915-11.json`.

Next tasks, in order: (1) correct oracle validation ordering while retaining
all exact completion, identity and deadline joins; (2) add packet-15 invalid
stage/flag/arithmetic/sentinel-retirement controls and supervisor exception-
injection coverage for retained event/wait prefixes, generic direct reaps,
ECHILD authority and actual-deadline timestamps; (3) rerun both pinned
interpreters and request a fresh independent exact-byte full source review.
Do not compile the collector, use root, launch a guest or claim a gate before
that review passes.

At 2026-09-15T23:33:17Z the active campaign identities are launcher 1676703,
launcher worker 1676707 and Codex app-server 1676709, started 2026-09-15
15:51:14 PDT. No build, compiler, guest, QEMU, mcexec, IHK, Cargo, Rust, GCC or
Clang process is live. All three bounded child agents are joined/completed and
new dispatch is stopped. Host free space is 68 GiB and scratch free space is
23 GiB. The launcher has paused future goal continuations. The counters remain
0/273 accepted application cases, 2/4 narrow fault modes, 6/130 production
gates, 350/10,000 points and 0/7 language gates. The whole-OS goal remains
incomplete and is neither resumed nor marked complete by this checkpoint.

Window-end checkpoint 12 preserves independent source review attempts 10 and 11
and their exact input archives. Both remain `FAIL_SOURCE`; no later bytes have
independent acceptance. The exact current WIP is archived at SHA256
`94c2c22c4f2dd4060e5935f444fee5926e5b16d98089895700db2521407b1c0c`.
It includes a bounded local raw-wait decoder needed by the new oracle join.
Python 3.9.12 and 3.8.10 both compile all four edited fixture sources, then each
passes 60/63 source-only tests. The three retained failures are exact validation-
order disagreements: owner observations precede owner identity, complete cleanup
precedes cleanup incomplete, and owner wait precedes direct wait. This is
`FAIL_SOURCE_WIP`, not source acceptance.

Next tasks, in order: (1) correct only those three oracle validation-order
failures without weakening identity, cleanup or wait joins; (2) add the missing
matched-unreaped OWNER_ERROR, owner exit/signal, sentinel signal/error, nullable
and positive birth, negative-descriptor and raw-wait-join controls; (3) rerun the
exact suite under both pinned interpreters; (4) request a fresh independent
exact-byte full source review only after stable PASS results. Do not compile,
use root, launch a guest or claim any gate before `PASS_SOURCE`.

At 2026-09-16T00:20:13Z the retained live campaign identities are launcher
1676703, launcher worker 1676707 and Codex app-server 1676709, all started
2026-09-15 15:51:14 PDT. No new task was dispatched; all three child agents are
joined/completed. Host free space is 64 GiB and scratch free space is 23 GiB.
The launcher has paused future goal continuations. Counters remain 0/273 accepted
application cases, 2/4 narrow fault modes, 6/130 production gates, 350/10,000
points and 0/7 language gates. The whole-OS goal remains incomplete and is
neither resumed nor marked complete by this checkpoint.

Continuous checkpoint 13 preserves source review envelope attempts 12 through
14. Attempt 12 is `FAIL_REVIEW_ENVELOPE` because it retained PASS hashes but
omitted packet texts 11/13/15. Corrected archive 13 receives `FAIL_SOURCE` for
six reproduced identity, sentinel-parent, chronology, later-birth, post-fork
observation and descriptor gaps. Packet 16 is independently rejected for an
impossible early timeout, unfixed stage budgets and selector-4 report conflation.
Replacement packet 17 SHA256
`39c7b15d712a49f8ea94c8ea2d68e48376bd0deee1dba22897a9b21ca7b353f7`
receives `PASS_CORRECTION_PACKET_ONLY` and releases only its source corrections.

The exact packet-17 implementation in review archive SHA256
`4394820878dc3bc9792ed3ee2c3e684861e1051254845775cd0c6c6ff06eac1d`
compiles and passes 75/75 source-only tests under Python 3.9.12 and 3.8.10,
but fresh independent full review remains `FAIL_SOURCE`. Five reproduced gaps
remain: TERM/KILL timeouts can suppress the mandatory direct timeout; COMPLETE
can accept a real-owner wait after 220 seconds; wrong-parent pairs and wrong-
birth timeouts can claim authority; signal errors can bypass retirement/adopted
pair checks; and owner adopted waits do not use the terminal raw-wait decoder.
These bytes are WIP evidence only. Source, compiler, root, native, application
and production gates remain closed.

Next tasks, in order: (1) restrict producer timeout suppression to an existing
direct timeout and require a timely real-owner wait for COMPLETE; (2) validate
later birth and every direct/adopted signal-error against chronological parent,
phase, unreaped and retirement authority; (3) decode every owner cleanup wait,
add exact counterexample round trips, rerun both pinned interpreters and request
a fresh full source review. Do not compile the collector or use root before
`PASS_SOURCE`.

At 2026-09-16T00:55:47Z the live campaign identities remain launcher 1676703,
launcher worker 1676707 and Codex app-server 1676709, all started 2026-09-15
15:51:14 PDT. Host free space is 64 GiB and scratch free space is 23 GiB. All
three bounded child agents are completed. Counters remain 0/273 application
cases, 2/4 narrow fault modes, 6/130 production gates, 350/10,000 points and
0/7 language gates. This checkpoint is not whole-OS completion.

Window-end checkpoint 13 preserves the exact post-review-9 correction bytes at
archive SHA256
`450b8bbe1dd03e6ca168c5a0bb7d25ec71406499c087a6b986ffdc8bc4f078b4`.
The producer now limits final-timeout suppression to a direct timeout and gates
COMPLETE on the fixed real-owner wait deadline. The oracle independently
establishes later births from exact supervisor-parent observation pairs, joins
direct and adopted signal errors to chronological unreaped authority and later
retirement, joins timeout identities, and decodes every owner cleanup wait.
These are unreviewed WIP corrections, not `PASS_SOURCE`.

Python 3.9.12 and 3.8.10 each compile the edited supervisor and oracle and pass
the existing 75/75 source-only tests. No collector compilation, root operation,
native run or guest run occurred. The raw storage-fault fixture remains
untracked; its exact bytes are retained only by the checkpoint archive pending
independent acceptance.

Next tasks, in order: (1) add exact producer/oracle counterexamples for the five
source-review-9 findings, including TERM/KILL plus direct timeout, late owner
wait, wrong-parent and wrong-birth authority, signal errors after/no authority,
and invalid adopted raw waits through the owner validator; (2) rerun the entire
suite under both pinned interpreters; (3) freeze a new exact-byte review archive
and obtain an independent full-source review. Do not compile the collector, use
root, run native code or launch a guest before `PASS_SOURCE`.

At 2026-09-16T01:02:56Z the preserved campaign identities are launcher 1676703,
launcher worker 1676707 and Codex app-server 1676709, all started 2026-09-15
15:51:14 PDT. No build, compiler, guest, QEMU, mcexec, IHK, Cargo, Rust, GCC or
Clang process is live. All three bounded child agents are completed and joined;
new dispatch is stopped. Host free space is 64 GiB and scratch free space is
23 GiB. The launcher has paused future goal continuations. Counters remain
0/273 application cases, 2/4 narrow fault modes, 6/130 production gates,
350/10,000 points and 0/7 language gates. The whole-OS goal remains incomplete
and is neither resumed nor marked complete by this checkpoint.

Window-end checkpoint 14 preserves the exact source-test failure archive at
SHA256 `e9236858a64b8ad610b835b39651f4a02374a4ae17387fb435e2301f3996dbb3`
and review-input archives 15 through 17. Archive 15 is disqualified by its
retained envelope failure because it replaced an immutable historical record;
the historical record was restored byte-for-byte and the new failure received
a distinct identity. Archive 16 receives `FAIL_SOURCE` for four exact findings.
Packet 18 SHA256
`45dccc23f26a88ceb5462d5f5f7d54865bffe1858988eb55cbf4a9acc12d60d5`
receives `PASS_CORRECTION_PACKET_ONLY` and releases only its bounded source
corrections.

Review archive 17 SHA256
`73ebe9fcb85c1de6e1d2dcedd227ee11dd6309e361f8fb7e822efb3c26c6ce8d`
has a passing independent envelope and two 86/86 interpreter runs, but fresh
full independent review remains `FAIL_SOURCE`. The four archive-16 findings are
corrected. Two blockers remain: initial post-fork identity observation exceptions
can bypass cleanup, pipe retirement and publication, and a second exception can
discard the first observation; the oracle also accepts duplicate direct
`wait-timeout` records. These exact bytes are evidence only. Source, compiler,
root, native, application and production gates remain closed.

Next tasks, in order: (1) add failing first- and second-observation exception
controls and a full-record duplicate-direct-timeout negative; (2) retain initial
observations incrementally inside the protected post-fork path so every failure
continues through bounded cleanup, pipe retirement and publication; (3) enforce
exactly one direct timeout when applicable without conflating TERM/KILL stage
timeouts; (4) rerun both pinned interpreters, freeze a new exact-byte archive and
obtain fresh full independent source review. Only after `PASS_SOURCE`, draft and
independently review the conditional UID1000 compiler-only packet for selectors
0 through 6; no existing build owner is reusable unchanged. Do not compile, use
root, run native code or launch a guest before the source and build-packet gates.

At 2026-09-16T01:33:47Z the retained campaign identities are launcher 1676703,
launcher worker 1676707 and Codex app-server 1676709, started 2026-09-15
15:51:14 PDT. No build, compiler, guest, QEMU, mcexec, IHK, Cargo, Rust, GCC or
Clang process is live. All three bounded child agents are completed and joined;
new dispatch is stopped. Host free space is 64 GiB and scratch free space is
23 GiB. The launcher has paused future goal continuations. Counters remain
0/273 application cases, 2/4 narrow fault modes, 6/130 production gates,
350/10,000 points and 0/7 language gates. The whole-OS goal remains incomplete
and is neither resumed nor marked complete by this checkpoint.

Continuous checkpoint 15 preserves source-test failure archives 18 through 22,
review-input archives 18 through 21 and independent source review failures 12
through 14. Every review envelope passes. The correction sequence raises both
pinned interpreter suites from 86 to 92 passing source-only tests and preserves
each intermediate regression. It adds protected incremental post-fork identity
observations, exact direct-timeout cardinality, failed-preflight timeout branch
rules, fixed sentinel wait and owner-start boundaries, strict timeout-before-reap
chronology and event-time-specific null-to-positive birth handling.

The latest exact review archive SHA256 is
`28b1d2c73cb353dd136a8b10ccda018b7739a8e65d4909ebc4cd4fd97418350e`.
Its 48-member envelope and both 92/92 logs pass, but independent full review
remains `FAIL_SOURCE`. Two representation blockers remain. First, the oracle
still accepts a null-birth sentinel timeout followed by a positive-birth reap
without an independently established identity pair. Second, late owner-start
failure evidence backdates `cleanup_trigger_ns` to the earlier sentinel reap;
truthful representation requires separate reap and actual failure timestamps,
while packet 17 currently forbids any cleanup event before the trigger. The
current raw fixture and tests remain untracked/rejected and must not be staged as
accepted source.

Next tasks, in order: (1) draft additive packet 19 to represent an earlier retained
direct reap separately from the actual late owner-start failure trigger, with a
narrow event-time exception and exact trigger-relative cleanup bound; (2) obtain
independent packet review; (3) add missing/wrong/post-wait identity-pair controls
for sentinel null-to-positive birth and a separated-timestamps full-path control;
(4) implement only the reviewed correction, rerun both interpreters and obtain a
fresh full exact-byte source review. Do not draft or run the conditional UID1000
compiler packet, use root, run native code or launch a guest before `PASS_SOURCE`.

At 2026-09-16T02:09:59Z the retained campaign identities remain launcher 1676703,
launcher worker 1676707 and Codex app-server 1676709, started 2026-09-15
15:51:14 PDT. No build, compiler, guest, QEMU, mcexec, IHK, Cargo, Rust, GCC or
Clang process is live. All three bounded child agents are completed and joined.
Host free space is 63 GiB and scratch free space is 23 GiB. Counters remain
0/273 application cases, 2/4 narrow fault modes, 6/130 production gates,
350/10,000 points and 0/7 language gates. This checkpoint is progress evidence,
not whole-OS completion.

Window-end checkpoint 15 adds correction packet 19 at SHA256
`4566c87f2c6a660a34d384393d3e2d429f8d7997555defe160a0903737189d8c` and
its independent review record at SHA256
`d6f8e7e1696973387f6934cce3ea2de5e4f53abf571bf647e8b2fe76a5a88248`.
The review status is `PASS_CORRECTION_PACKET_ONLY`; it releases only a bounded
source correction. Packet 19 requires the actual late owner-start sample to be
the cleanup trigger while retaining the earlier successful sentinel wait as the
sole narrowly permitted pre-trigger event. It also requires an exact adjacent
positive identity pair, with supervisor parent, matching PID/birth and permitted
TERM/KILL phase, before any null-timeout-to-positive-reap join. It forbids null
wildcards, post-wait or pre-timeout authority, wrong parent/birth/phase and
revived authority. No source, compiler, root, native, application or production
acceptance follows.

Next tasks, in order: (1) add packet-19 focused controls for separated trigger
timestamps and missing, wrong and post-wait identity pairs; (2) preserve the
expected failures against the current rejected source; (3) implement only the
reviewed `PreflightFailure` trigger, narrow earlier-sentinel-event exception and
event-time identity-pair proof; (4) rerun the complete suite under both pinned
interpreters; (5) freeze a fresh exact-byte source archive and obtain independent
full source review. Only after `PASS_SOURCE` may a separately reviewed UID1000
compiler-only packet be drafted. Do not compile, use root, run native code or
launch a guest before those gates.

At 2026-09-16T02:17:26Z new dispatch is stopped and all three child agents are
completed and joined. The retained live identities are launcher 1676703, launcher
worker 1676707 and Codex app-server 1676709, all started 2026-09-15 15:51:14 PDT.
No build, compiler, guest, QEMU, mcexec, IHK, Cargo, Rust, GCC, Clang or container
build process is live. Host free space is 63 GiB and scratch free space is 23 GiB.
The launcher has paused future goal continuations. Counters remain 0/273 accepted
application cases, 2/4 narrow fault modes, 6/130 production gates, 350/10,000
points and 0/7 language gates. The whole-OS objective remains incomplete and is
neither resumed nor marked complete by this checkpoint.

Continuous checkpoint 16 preserves packet-19 source-test failure archives 23
through 26 and full review-input archives 22 through 24. Review attempt 19
verified archive SHA256
`e2f24efd31ff7e1e6ee48624344f42d677cb9000291d91f8d7a6fa0f5237063f`
but returned `FAIL_SOURCE`: exact late-start records could omit/substitute the
sentinel wait or backdate the trigger, contradictory direct identity did not
revoke authority, a null adopted sentinel reap allowed PID revival, and
SPAWN_FAILED admitted an arbitrary direct timeout. Nine full-record controls
reproduced those findings before the bounded correction.

Review attempt 20 verified archive SHA256
`ead3fabe0d48e4c02e43789cf603bfd4df9ea8ef965906c9e35ca530d0b48132`
and also returned `FAIL_SOURCE`. It found that invalidated positive history was
conflated with never-established null history; sentinel retirement revoked only
waits rather than signal/signal-error authority; and incomplete sentinel cleanup
could bind a signal and timeout to different PIDs. Seven additional full-record
controls reproduce those exact cases in failure archive 26.

The current unaccepted correction separates historical birth from live
authority, makes sentinel PID retirement sticky across every direct authority
path, and requires all sentinel direct evidence to use one PID. Python 3.9.12
and 3.8.10 both compile the four sources and pass 100/100 source-only tests. The
fresh 61-member review archive SHA256 is
`1e74749856876abf5f337d30451581a7c8245327af074a6d768250a3780530d5`;
independent full review is active. These raw fixture/test bytes remain rejected
and untracked until `PASS_SOURCE`. No compiler, root, native, guest, application
or production credit follows.

Next tasks, in order: (1) finish the independent exact-byte review of archive
24; (2) if and only if it returns `PASS_SOURCE`, checkpoint the exact source and
draft a separately reviewed conditional UID1000 compiler-only packet for
selectors 0 through 6; otherwise preserve every finding and correct only the
reviewed source contract; (3) do not compile or use root until both gates pass.

At 2026-09-16T02:56:20Z the live campaign identities remain launcher 1676703,
launcher worker 1676707 and Codex app-server 1676709, all started 2026-09-15
15:51:14 PDT. No build, compiler, guest, QEMU, mcexec, IHK, Cargo, Rust, GCC,
Clang or container build process is live. Host free space is 63 GiB and scratch
free space is 22 GiB. Counters remain 0/273 accepted application cases, 2/4
narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7 language
gates. The whole-OS objective remains incomplete.

Window-end checkpoint 17 records independent source review attempt 21 as
`FAIL_SOURCE`. The reviewer verified the 4,295,234-byte, 61-member archive 24 at
SHA256 `1e74749856876abf5f337d30451581a7c8245327af074a6d768250a3780530d5`,
including 39 nested archive occurrences and 304 manifest bindings. Two
independently reproduced equal-timestamp gaps remain. A contradictory identity
event immediately before a same-timestamp positive-birth reap is ignored on both
sentinel and owner paths. An adopted retirement immediately before a
same-timestamp direct signal error is likewise ignored, allowing the error and a
later timeout after retirement. The exact reproduction hashes and bounded review
scope are retained in
`stability-linux-collector-storage-fault-v2-source-review-failure-20260915-17.json`.
The reviewer did not finish a complete reread before the checkpoint stop, so no
unaffected path is accepted by implication. The raw fixture/test bytes remain
untracked and rejected; no compiler packet, build, root action, native run, guest
run, application acceptance or production credit follows.

Next tasks, in order: (1) add and preserve full-record controls for the two
equal-timestamp failures; (2) process preceding same-timestamp events by array
position for authority invalidation while keeping positive proof strictly
earlier in time; (3) make every prior sentinel retirement revoke later direct
signal, signal-error and timeout authority; (4) rerun the complete suite under
both pinned interpreters, freeze a new archive and obtain a fresh complete
independent source review. Do not draft the conditional UID1000 compiler packet
or compile anything before `PASS_SOURCE`. M03 candidate 12 remains accepted only
as focused equivalence and is not integration-ready; its next action is a newly
reviewed correction/source packet.

At 2026-09-16T03:07:10Z new dispatch is stopped and both bounded child agents are
completed and joined. The retained live campaign identities are launcher
1676703, recovered worker 1855986 and Codex app-server 1855988; the launcher
started 2026-09-15 15:51:14 PDT and the recovered worker/server started
2026-09-15 20:01:15 PDT. No build, compiler, guest, QEMU, mcexec, IHK, Cargo,
Rust, GCC, Clang or container build process is live. Host free space is 63 GiB
and scratch free space is 22 GiB. The launcher has paused future goal
continuations. Counters remain 0/273 accepted application cases, 2/4 narrow
fault modes, 6/130 production gates, 350/10,000 points and 0/7 language gates.
The whole-OS objective remains incomplete and is neither resumed nor marked
complete by this checkpoint.

Continuous checkpoint 18 preserves storage source-test failure archives 27
through 29, review-input archives 25 through 27 and independent review failures
22 and 23. Review 22 fully verified archive 25 but returned `FAIL_SOURCE`:
direct timeout validation discarded prior PID retirement, adopted signal-error
expiration ignored an equal-time reap, and the archive had used Python 3.8.19
instead of required 3.8.10. Exact full-record canonical JSON hashes
`1d63a6ccf565392a6f7af5bee7680c7d43beab7a0f51b7fd3a52ce5905223671`
and `d68126e2674521cf4a11ed795486d7e7d20884a293d3d7aba1c7de69db008064`
reproduce both gaps. The first correction incorrectly conflated ECHILD with an
actual reap and regressed three legitimate timeout paths; its exact source is
retained. The bounded replacement distinguishes actual waits from ECHILD and
passes both exact full-record controls plus a later-wait/ECHILD positive.

Review 23 verified archive 26 and the required 3.9.12/3.8.10 107-test logs but
also returned `FAIL_SOURCE`. A direct sentinel reap did not update the shared
retired identity/PID sets, allowing later adopted signal, signal-error and a
second wait for the same lifetime. Exact canonical record
`7b3291baf911560a9dd2143189015debe63def4809e7391fb258dd9bea4dff22`
reproduces the positive-birth path. Additional full-record controls reproduce
null-to-positive, equal-time and adopted-error revival at hashes
`2f53e2859233b461cb8cd4af424cafd8862ecb96cfa23c275c99704fd07e6aac`,
`da837c8ca0fa27cf793b56feaa3cd48df620ae1d5628dd0c3125298ec633acd6`
and `f32bf14caf226ccda0733cd10ef1d655334085c60f2f05e6bfe7fb3bb3660bc9`.
All four accept under the rejected archive-26 oracle and reject after direct
waits update both exact and PID retirement state; timestamp-aware adopted-error
validation still accepts a valid later wait/ECHILD join.

The current raw fixture/test bytes remain untracked and unaccepted. Python
3.9.12 and `/usr/bin/python3.8` 3.8.10 each pass 110/110, and both pycompile all
four fixture sources. Fresh 28-member review archive 27 is 36,017,380 bytes at
SHA256 `85316fd95101c33448090d4fc2e3ce51fbf8a4b22fc0dd5075d5387e0c6f1ffb`;
independent full source review 24 is active. No compiler packet, compilation,
root/native/guest execution, application acceptance or production credit is
released unless that exact review returns `PASS_SOURCE`.

Independent M03 review leaves candidate 12 accepted only for focused
equivalence. Candidate-13/14 cannot receive a correction-packet pass because
production has no trusted begin-time descriptor inventory/cardinality/range
authority. The required private model needs immutable sentinel identity, exact
capacity/count, descriptor membership/generation and physical range/alignment
validation, with complete-batch preservation on every mismatch. Production
integration requires a real producer-maintained registry/count/range API; the
current raw-cast and physical lookup cannot supply it. No M03 execution or credit
is released.

Next tasks, in order: (1) finish exact review 24 of archive 27; (2) only on
`PASS_SOURCE`, checkpoint the exact raw storage source/test bytes and draft a
separately reviewed conditional UID1000 compiler-only packet for selectors 0
through 6; otherwise preserve the new finding and continue the bounded source
correction; (3) specify and independently review the missing M03 production
inventory API before another pending-free candidate. Do not compile or use root
before the corresponding release gates.

At 2026-09-16T03:56:48Z the live identities are launcher 1676703, recovered
worker 1875246 and Codex app-server 1875248. No build, compiler, container,
guest, QEMU, mcexec or IHK process is live. Host free space is 60 GiB and
scratch free space is 22 GiB. Counters remain 0/273 accepted application cases,
2/4 narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7
language gates. The whole-OS objective remains active and incomplete.

Window-end checkpoint 19 records independent source review attempt 24 as
`FAIL_SOURCE`. The reviewer verified the 36,017,380-byte, 28-member archive 27
at SHA256
`85316fd95101c33448090d4fc2e3ce51fbf8a4b22fc0dd5075d5387e0c6f1ffb`,
read all four current Python sources, the complete 110-test file, packet 19 and
the embedded failure descriptions, and independently exercised the six named
canonical negative controls plus the later adopted-error positive. The
negative controls reject and the positive accepts, but a new concrete source
gap remains.

The direct-birth state detects a contradictory birth and then overwrites the
established birth when a later matched identity pair appears. Exact sentinel
and owner records can therefore change birth 30 to birth 31 before their direct
reap and still validate, although the producer pins `last_birth` and cannot
emit that transition. The incorrectly accepted canonical JSON hashes are
`6fe02b2682cbe15f6c4ee97497129cd7a22454cd038cd7b25d1237ab85587242`
for the sentinel and
`b62b0b069a4dfef6f36df22d1e1918e3479e14a923d763ef840b345ad4e6042e`
for the owner. Review 24's exact envelope, source bindings, finding and limits
are preserved in
`stability-linux-collector-storage-fault-v2-source-review-failure-20260915-20.json`.
Eight historical archive references were unavailable inside the envelope, and
the reviewer stopped further inspection for this checkpoint, so the review is
not exhaustive acceptance.

The raw storage fixture/test bytes remain untracked and rejected. No accepted
source checkpoint, compiler packet, compilation, root/native/guest execution,
application acceptance or production credit is released. Next tasks, in order:
(1) add and preserve exact full-record sentinel and owner controls for changed-
birth waits, signals and signal errors, retaining legitimate null-to-positive
establishment; (2) keep an established direct-child birth immutable and reject
any later identity pair that contradicts it; (3) rerun both pinned interpreter
suites and pycompile; (4) freeze a new exact archive and obtain fresh complete
independent source review; (5) only after `PASS_SOURCE`, checkpoint the exact
source and draft a separately reviewed conditional UID1000 compiler-only packet
for selectors 0 through 6. M03 still requires a separately reviewed production
inventory API before another pending-free candidate.

At 2026-09-16T04:02:54Z new dispatch is stopped. Source reviewer 24 and reviewer
23 are completed and joined; the bounded direct-retirement worker is closed in
interrupted state with its retained edits represented by archive 27. The live
campaign identities remain launcher 1676703, recovered worker 1875246 and Codex
app-server 1875248. No project build, compiler, container build, guest, QEMU,
mcexec or IHK process is live. The host's pre-existing Docker daemon/proxies are
not project build work. Host free space is 59 GiB and scratch free space is
22 GiB. The launcher has paused future goal continuations. Counters remain
0/273 accepted application cases, 2/4 narrow fault modes, 6/130 production
gates, 350/10,000 points and 0/7 language gates. The whole-OS objective remains
incomplete and is neither resumed nor marked complete by this checkpoint.

Continuous checkpoint 20 resumes under launcher run
`.git/os-autopilot/runs/20260916T040529Z-c5b585aa`. Source correction attempt 25
made established direct-child birth immutable and added old-accept/new-reject
controls for sentinel and owner wait, signal and signal-error authority. The
first controls were themselves invalid under archive 27 and are preserved as
failure archive 30 at SHA256
`8a756749a091c72a716ea16e9926a7f21d5a900089bfe494422212ab7f111864`;
its invalid self-manifest entry is corrected additively without changing the
archive. The replacement exactly reproduces the original review-24 canonical
hashes `6fe02b2682cbe15f6c4ee97497129cd7a22454cd038cd7b25d1237ab85587242`
and `b62b0b069a4dfef6f36df22d1e1918e3479e14a923d763ef840b345ad4e6042e`.

Independent review 25 nevertheless returns `FAIL_SOURCE` for two additional
strict-schema gaps in archive 28 SHA256
`fe55a4e5ab948f41994d376ad570e73fd814670c6e4be9924784f7d174297b83`:
boolean `actual_bytes=False` compared equal to integer zero, and SPAWN_FAILED
accepted malformed normalized-error value types. Their exact selector and
full-record hashes are retained in
`stability-linux-collector-storage-fault-v2-source-review-failure-20260915-21.json`.
The first focused correction then stopped on a test-only module-binding
NameError; failure archive 31 SHA256 is
`90f985d3491b16fd29300a7619eb735d7a19e64441b2dad5fed7f8704c2a90f1`.

The corrected archive 29 is 36,475,232 bytes with 33 safe unique members at
SHA256 `7c57014f865797edd2c3abcafc0d96760fce4391d0e5d1064c7b31f7f682e0ee`.
Python 3.9.12 and 3.8.10 each pass 113/113, both pycompile the four fixture
sources, and the envelope now binds raw interpreter versions, paths, metadata
and executable hashes. Review 26 still returns `FAIL_SOURCE`: a valid
SPAWN_FAILED record accepts numerically equal floating
`owner_wait_deadline_ns=220000000100.0`, canonical hash
`58782272d47280a9075e57022c761c8f3653d3fd28c0c9b6f9ea9ed399bc8ec6`.
It also flags an unclosed report-schema concern where `wait.exit_code=False`
may compare equal to zero. The current raw storage fixture/test bytes remain
untracked and rejected; no compiler packet, compilation, root/native/guest
execution, application acceptance or production credit is released.

M03 now has an independently accepted proposal-only inventory source contract
at `stability-pending-free-inventory-source-contract-20260915-1.md`, SHA256
`00141eb8f17d21ad3ad9b20829a333e6558e8859f70347d72bd3e9b893ae8be8`.
It requires producer-owned identity/generation/count/range authority, pinned
arena lifetime, a real lock/lease, validate-before-dereference, typed clear/TLB
release and separate durable quarantine metadata. The registry, lock and
acknowledgement producers remain unresolved; candidate 12 remains focused-
equivalence-only and no M03 integration or gate credit is released.

Next tasks, in order: (1) add exact-integer owner-wait-deadline controls for
SPAWN_FAILED, preserving integer positives and float/boolean negatives; (2)
construct the complete report-process `wait.exit_code=False` reproduction and
audit adjacent top-level scalar/boolean fields against the producer schema; (3)
rerun both pinned suites, freeze a fresh archive and obtain complete independent
source review; (4) only after `PASS_SOURCE`, checkpoint the exact raw storage
source/test bytes and draft a separately reviewed UID1000 compiler-only packet;
(5) resolve and independently review the concrete M03 registry, lock, generation
and clear/TLB authority sources before any production edit.

At 2026-09-16T04:45:52Z all three bounded child agents are completed and joined.
The live campaign identities are launcher 1676703, recovered worker 1899017 and
Codex app-server 1899019. No project build, compiler, container build, guest,
QEMU, mcexec or IHK process is live. Host free space is 56 GiB and scratch free
space is 22 GiB. Counters remain 0/273 accepted application cases, 2/4 narrow
fault modes, 6/130 production gates, 350/10,000 points and 0/7 language gates.
The whole-OS objective remains active and incomplete.

Checkpoint 20 evidence was pushed and fetched-blob verified at commit
`775718dd5482bb44b4e327dbc54d95c6bc01c859`. Local HEAD,
`origin/codex/local-native-staging-repair` and `git ls-remote` matched; the
CURRENT, archive-29, review-26 failure, M03 contract and M03 contract-review
blobs matched the fetched remote objects exactly. This verified checkpoint does
not change any acceptance counter or release the rejected raw storage source.

Window-close checkpoint 21 stops new dispatch at 2026-09-16T04:56:46Z. The
bounded review-26 correction is implemented only in the still-untracked raw
storage fixture and test: terminal identity records now require a positive
exact-integer `owner_wait_deadline_ns`, and complete report wait fields must
exactly match the result decoded from the exact integer `raw_wait_status`.
Focused review-24/25/26 controls pass 5/5. The full suite passes 115/115 under
both Python 3.9.12 and Python 3.8.10; both interpreters also pycompile the four
fixture sources. The exact current oracle and test hashes are respectively
`f1979a4432a853ffe270c3748a18bbb0323a39da663ce1910ceb10486433c003`
and `a1cd82a391be67f2569bcea4ccfd2416ae3872bf1e0392ff4754888486fb8182`.
Original raw outputs and interpreter identities are preserved in
`stability-linux-collector-storage-fault-v2-window-validation-20260915-1.tar.gz`,
584 bytes, SHA256
`247be40a9b843e7eb1fdd7a7f230a75f29a68c7fb865a78e1c72be36b7f4c39f`.
This is validation-only evidence, not `PASS_SOURCE`; the raw source remains
untracked and rejected.

All three bounded children are completed and joined. The only live campaign
identities are launcher 1676703 (started Tue Sep 15 15:51:14 2026), recovered
worker 1899017 (started Tue Sep 15 21:05:29 2026), and Codex app-server 1899019
(started Tue Sep 15 21:05:29 2026). No project build, compiler, container build,
guest, QEMU, mcexec or IHK process is live. Host free space is 55 GiB and scratch
free space is 22 GiB. The launcher has paused future goal continuations.

Next tasks, in order: (1) freeze exact source-review archive 30 from the current
raw fixture/test, validation logs and prior review-26 evidence; (2) obtain fresh
independent review 27, including decode parity, the review-24/25/26 differential
hashes and another strict-type audit; (3) only after `PASS_SOURCE`, checkpoint
the exact raw source and draft a separate conditional UID1000 compiler-only
packet for independent review; (4) continue M03 only after its concrete registry,
lock, generation and clear/TLB authorities are independently reviewed. Counters
remain 0/273 accepted application cases, 2/4 narrow fault modes, 6/130 production
gates, 350/10,000 points and 0/7 language gates. The whole-OS objective remains
incomplete and is neither resumed nor marked complete by this window checkpoint.

The window-close evidence checkpoint was pushed and fetched-blob verified at
commit `181598d0ed1bf9148c0458f221b055cd528c15c1`. Local HEAD,
`origin/codex/local-native-staging-repair` and `git ls-remote` matched. The
CURRENT, validation record and evidence-archive blobs matched the fetched remote
objects exactly; the archive retained SHA256
`247be40a9b843e7eb1fdd7a7f230a75f29a68c7fb865a78e1c72be36b7f4c39f`.

Window-close checkpoint 22 stops new dispatch at 2026-09-16T05:28:56Z.
Independent source review 28 returns `FAIL_SOURCE` for archive 31, SHA256
`b8fb02bdff5f3d7a311316582850b0085bef903112142de0fb1c902b4a64b141`,
36,917,455 bytes and 32 safe unique members. All 89 prior malformed cases now
reject, selectors 0 through 6 and the optional-sample positive accept, and all
65,536 raw wait values match the supervisor decoder. Remaining findings are a
NUL or overlong proc-exe sample, invented pre-fork lifecycle/ownership state, a
zero preparation clock and a contradictory pinned-group child-kill flag. The
exact findings and canonical hashes are retained in
`stability-linux-collector-storage-fault-v2-source-review-failure-20260915-24.json`.

Bounded correction attempt 28 changed only the still-untracked oracle and test.
Its review-24-through-28 focused controls pass 7/7 and `git diff --check` passes.
The current oracle SHA256 is
`dc7dd7d2a33b694e607fa3e70c7767649f9da353c48f5af21d3bdbb4241d0874`;
the test SHA256 is
`42a159c2e4fd08c7b005d9eac4775753ad5b06de4797e5d7c87f5123a2bf1ad2`.
The window ended before attempt-28 dual full-suite and pycompile runs, so no
fresh source acceptance is claimed. The raw fixture/test remain untracked and
rejected, and no compiler packet or execution is released.

The M03 production-authority review returns `FAIL_AUTHORITY_PACKET`. Clear
failure currently releases XPMEM ownership, TLB completion lacks a generation
and late-interrupt lifetime permit, existing locking is only partial exclusion,
descriptor/VM generation and quarantine authorities are absent, and the dirty
inventory model is not executable equivalence evidence. The exact source-bound
audit and independent review are retained in
`stability-pending-free-inventory-production-authority-audit-20260915-1.json`
and `stability-pending-free-inventory-production-authority-review-20260915-1.json`.
No M03 integration or credit is released.

All three bounded children are completed and joined. Live campaign identities
are launcher 1676703, recovered worker 1899017 and Codex app-server 1899019.
No project build, container build, guest, QEMU, mcexec or IHK process is live;
unrelated Verilator compiler activity remains outside this project. Host free
space is 55 GiB and scratch free space is 22 GiB. The launcher has paused future
goal continuations.

Next tasks, in order: (1) rerun attempt-28 full suites and pycompile under both
pinned interpreters; (2) freeze a new exact source-review archive and obtain a
fresh complete independent review; (3) only after `PASS_SOURCE`, checkpoint the
raw source and draft the separate conditional UID1000 compiler-only packet; (4)
for M03, specify and independently review the lifecycle/clear-authority packet
covering descriptor and VM generations, retained partial-clear ownership,
late-TLB lifetime, lock order and quarantine handoff before any production edit.
Counters remain 0/273 accepted application cases, 2/4 narrow fault modes,
6/130 production gates, 350/10,000 points and 0/7 language gates. The whole-OS
objective remains incomplete and is neither resumed nor marked complete.

Continuous checkpoint 23 resumes under the existing launcher invocation.
Planning-index revalidation still passes with 14 milestones, 68 tasks, 130
production gates, seven language gates, 273 logical cases and 97 packets;
`execution_authorized` remains false and grants no runtime release.

Independent storage source review 29 returns `FAIL_SOURCE` for archive 32,
SHA256 `9638a45a70ead1d310ba1653ef6ad7868b0cdf65ae7aa47b6d181be74b18114c`,
37,033,713 bytes and 30 safe unique members. Eight impossible producer states
still validated: pre-fork executable/stdin state, wrong memfd flags, non-root
post-fork collector credentials and impossible request-sink error states. The
review also found that the review-28 test named five canonical hashes without
actually comparing or faithfully reproducing them. Exact findings and four new
canonical report hashes are retained in
`stability-linux-collector-storage-fault-v2-source-review-failure-20260915-25.json`.

Correction attempt 29A then ran all 118 Python 3.9 tests and failed one retained
review-27 canonical assertion because its test fixture incorrectly changed the
producer's always-3 source flags. The exact log is preserved in
`stability-linux-collector-storage-fault-v2-source-test-failure-20260915-33.tar.gz`,
SHA256 `735a635034eaac4aea0372f4fe58a2b654359a42dfb2ce5a88bee8263101bdb2`.
The worker replaced the still-untracked failure bytes before the dispatcher
copied them; their reported hashes are retained, but the archive explicitly
records that the unavailable bytes are not reconstructable evidence.

Correction 29C now binds the producer's exact source/sink state and all five
review-28 canonical mutations. The current oracle SHA256 is
`a0f09c2a21a868e9f566dbb5c87f52aa0a17c4e0b244953926d1c278fffbd598`;
the test SHA256 is
`aefdc5c6df70b3558f18dc56d9d986d2d43f220e00174fa5a42dcad292cbdd64`.
Dispatcher reproduction passes 118/118 under Python 3.9.12 and Python 3.8.10;
both interpreters pycompile all four fixture sources. Review-input archive 33
is 37,155,456 bytes with 30 safe unique members at SHA256
`e2ae06d94cd0e532691221462a931112f7d6fb1a5b7fd8f0cd51622101b0495e`.
Fresh independent source review 30 is active. The raw fixture/test remain
untracked and unaccepted until a terminal `PASS_SOURCE`; compiler-packet
drafting and all execution remain closed.

M03 lifecycle/clear source-map attempt 3 returns `FAIL_SOURCE_MAP`: current
source provides no generation allocator, descriptor pin, owned late-TLB address
snapshot or global quarantine handoff, and clear failure currently drops XPMEM
ownership. Its exact source-bound result is retained in
`stability-pending-free-lifecycle-clear-source-map-failure-20260915-1.json`.
M01 actual-method audit likewise returns `FAIL_SOURCE_MAP`: the untracked
16-row scaffold is still strings/counters rather than actual Rust type/module
linkage and lacks the aligned backing, drop ledger, worker/mailbox construction
and distinct cancellation executions. Neither lane receives implementation or
gate credit.

At 2026-09-16T06:01:57Z live campaign identities remain launcher 1676703,
recovered worker 1899017 and Codex app-server 1899019. No project build,
container build, guest, QEMU, mcexec or IHK process is live. Host free space is
55 GiB and scratch free space is 22 GiB. Next tasks: (1) finish exact source
review 30; (2) on `PASS_SOURCE`, checkpoint the exact raw source and prepare a
separately reviewed conditional UID1000 compiler-only packet, otherwise retain
the new finding and correct it; (3) specify new M03 generation/pin/TLB/quarantine
mechanisms and the M01 actual-source runner ABI before either implementation.
Counters remain unchanged and the whole-OS objective remains active.

Continuous checkpoint 24 preserves source-review attempts 30 through 32.
Review 30 rejected archive 33 because selector-specific source/devnull state,
successful request creation/relocation and archive31 acceptance controls were
still incomplete. Correction 30 added those joins and passed 119/119 under both
pinned interpreters. Review 31 then rejected archive 34, SHA256
`558fbca30a988b290122a816c38638f790fd2be1a6e124c2dcf9da398eeb3e15`,
because non-request reached sinks could still claim failed creation or fd
relocation while retaining later successful evidence. Its exact findings are
`stability-linux-collector-storage-fault-v2-source-review-failure-20260915-27.json`.

Correction 31 now requires exact successful new-sink state across all reached
artifact positions and passes 120/120 under Python 3.9.12 and 3.8.10 plus both
pycompile runs. Review-input archive 35 is 37,391,676 bytes with 29 safe unique
members at SHA256
`701d73ce1a7ff67c538dbdd5522569fbea1fe9f6124e8c8d88b872e5fb41006a`.
Independent review 32 still returns `FAIL_SOURCE`: selector 2/6 exempted every
sink from I/O consistency rather than request.bin alone, accepting impossible
truncated/error/overflowing events counters. Exact hashes are retained in
`stability-linux-collector-storage-fault-v2-source-review-failure-20260915-28.json`.
Bounded correction 32 is active on the same two untracked files. No source,
compiler packet or execution release follows yet.

The live identities remain launcher 1676703, recovered worker 1899017 and
Codex app-server 1899019. No project heavy build or guest is live. Host free
space is 54 GiB and scratch free space is 22 GiB. Next tasks remain: finish
correction/review of the exact source, checkpoint it only after `PASS_SOURCE`,
then independently review the conditional UID1000 compiler-only packet. M03 and
M01 retain their source-map blockers. Acceptance counters remain unchanged.

Window-close checkpoint 25 stops new dispatch at 2026-09-16T06:39:48Z.
Correction 32 is bounded and locally complete on the same two still-untracked
storage-fault files. It restricts the selector-2/6 I/O-failure exception to the
request sink, requires healthy reached event sinks, bounds retained counters to
the producer's uint64 domain and enforces their ordering relationships. The
review-28-through-32 controls pass, the complete suite passes 121/121 under both
Python 3.9.12 and Python 3.8.10, both pycompile runs pass, and `git diff --check`
passes. The exact oracle SHA256 is
`0c4d98319b562b72801b6f8ac5979ccfe301f5d25bf808680c216ea363c26afd`;
the exact test SHA256 is
`dbff9e543a31e2a0ebcd5a60b8be4b79d75fc2d6b1185088f67761499611cce1`.

The corrected bytes, dual-interpreter identities and raw logs, both empty
pycompile streams, archive 35 and review-32's failure record are frozen without
source promotion in the 29-member, 19-file review-input archive
`stability-linux-collector-storage-fault-v2-source-review-input-20260915-36.tar.gz`,
37,511,064 bytes, SHA256
`d1adca4b4904667efe66e8253a42c2d16a46336b34b676b0efa03ba65de011b8`.
Its manifest bindings and safe unique member paths were rechecked. No review-33
agent was dispatched before the window ended, so this is explicitly unreviewed
source-review input, not `PASS_SOURCE`; the raw fixture/test remain untracked and
unaccepted. No compiler packet, compilation, root/native/guest execution,
application acceptance or production credit is released.

All three bounded child agents are completed and joined. The live campaign
identities are launcher 1676703 (started Tue Sep 15 15:51:14 2026), recovered
worker 1899017 (started Tue Sep 15 21:05:29 2026) and Codex app-server 1899019
(started Tue Sep 15 21:05:29 2026). No project build, container build, guest,
QEMU, mcexec or IHK process is live. Unrelated Verilator compiler activity remains
outside this project and was left untouched. Host free space is 54 GiB and scratch
free space is 22 GiB. The launcher has paused future goal continuations.

Next tasks, in order: (1) obtain fresh complete independent review 33 of exact
archive 36, replaying reviews 24 through 32 and auditing adjacent producer/schema
joins; (2) only after terminal `PASS_SOURCE`, checkpoint the exact raw fixture and
test bytes; (3) draft and independently review a separate conditional UID1000
compiler-only packet before any compile; (4) retain M03 and M01 at their current
source-map blockers until concrete generation/pin/TLB/quarantine authority and
actual-method runner ABI packets are independently reviewed. Counters remain
0/273 accepted application cases, 2/4 narrow fault modes, 6/130 production gates,
350/10,000 points and 0/7 language gates. The whole-OS objective remains
incomplete and is neither resumed nor marked complete by this checkpoint.

The bounded closeout evidence was pushed and fetched-blob verified at commit
`0d46c61545e84111977a320c17adfffa10461eb1`. Local HEAD,
`origin/codex/local-native-staging-repair`, `git ls-remote` and fetched HEAD
matched. The CURRENT blob and archive-36 blob matched the fetched remote objects
exactly; archive 36 retained SHA256
`d1adca4b4904667efe66e8253a42c2d16a46336b34b676b0efa03ba65de011b8`.

Continuous checkpoint 26 resumes the launcher-owned goal and preserves review 33.
Archive 36 passed the complete review-24-through-32 regression replay, but fresh
independent source review returned `FAIL_SOURCE`: the oracle accepted empty or
raw/report-inconsistent setup evidence, an overflowing setup word, substituted
selected-input bytes and a child-created PID disconnected from the later
setup/report/reap identity. Five canonical report hashes and the exact reproducer
are retained in
`stability-linux-collector-storage-fault-v2-source-review-failure-20260915-29.json`,
SHA256 `affcd750bf77d7ab091c1ffb6e925213f5b7343e15b9c8b926ed44550b6764c8`.

Bounded correction 33 changes only the still-untracked storage oracle and test.
It binds exactly one 384-byte successful setup packet and all 48 little-endian
uint64 words to the report, binds selected-input artifact bytes to the retained
input, applies event-specific types and joins the one child-created identity to
setup/report/reap evidence. Dispatcher-owned Python 3.9.12 and 3.8.10 runs each
pass 122/122, and both pycompile lanes pass. Exact oracle SHA256 is
`008fea042f2b7b08e5e92d53d3b25bb690ba1aa1b303c89654de79224e67e018`;
test SHA256 is
`84bf5fbe57b94f01a9cdb9c0ed2d5f0e5aff1f11dbe6e2971eed54afb4a5510f`.
Review-input archive 37 has 29 safe unique members, 19 files and size 37,633,412
bytes at SHA256
`8864684d5698e30bd0620af915e039b0598b047b1266ad21c1ec46078d637b15`.
Independent source review 34 is active; source checkpointing and every compiler or
execution release remain closed until a terminal `PASS_SOURCE`.

Two parallel source-map lanes now pass their corrected map-only reviews. The M03
map at `stability-pending-free-authority-source-map-20260916-1.json`, SHA256
`92a35015344c007bdbc0117d889a6bb4683c6c10b2ef97fc9a42878e4674693a`,
binds the current enqueue/finish, XPMEM clear, TLB body/handler and VM-final-release
seams while retaining the missing OS/VM generation, descriptor pin, typed late
acknowledgement and quarantine-owner blockers. The dirty `mem_helpers.rs` remains
untouched. The M01 actual-method map at
`stability-selected-retention-actual-method-source-map-20260916-1.json`, SHA256
`a09978ce5d6bd8f3cdb43bbeba25af7ba287b5d6143d72e039b781df8abd4131`,
requires adapters only in exact stager-produced mode-2/mode-3 candidate outputs,
post-preparation ledger deltas and the mode-3 two-second recovery transition. The
original strings/counters scaffold remains rejected. The preserved first review
is `stability-source-maps-review-20260916-1.json`, SHA256
`7fd7c9aa6d5569433de3be37a6da73d999e04f8acbfb726663791ad5ba0dd731`.
Neither map releases implementation, compilation, runtime or gate credit.

Live campaign identities remain launcher 1676703, recovered worker 1899017 and
Codex app-server 1899019. No project build, container build, guest, QEMU, mcexec
or IHK process is live. Host free space is 54 GiB and scratch free space is 22
GiB. Next tasks: (1) complete exact source review 34; (2) on `PASS_SOURCE`,
checkpoint the raw source and prepare the separately reviewed UID1000 compiler-
only packet, otherwise retain/correct the finding; (3) turn one corrected source
map at a time into an independently reviewed implementation packet without
touching the dirty pending-free candidate. Counters remain 0/273 accepted
application cases, 2/4 narrow fault modes, 6/130 production gates, 350/10,000
points and 0/7 language gates. The whole-OS objective remains active and
incomplete.

Window-close checkpoint 27 stops all new dispatch at 2026-09-16T07:18:10Z.
Independent review 34 rejects archive 37 with `FAIL_SOURCE`: the positive
fixture argv did not match the request-decoded argv, setup words 21 through 26
did not bind stdout/stderr FIFO identity, lifecycle events admitted disconnected
or fabricated child identities, and selector 4 could bypass reached-artifact and
lifecycle validation by omitting its report. The exact finding is retained in
`stability-linux-collector-storage-fault-v2-source-review-failure-20260915-30.json`,
SHA256 `a555152c3e672db19b9603700641849e801edb513a8d31f900893dd3e768b043`.

Bounded correction 34 changes only the two still-untracked storage-fault files.
It adds request-decoded argv/environment byte binding, FIFO setup-word binding,
strict selector event identity and ordering, selector-4 report-absence joins and
the corrected positive argv. Dispatcher-owned Python 3.9.12 and Python 3.8.10
runs each pass 122/122; both pycompile lanes pass. Their raw final logs remain at
`/home/holden/mckernel-work/scratch/storage-fault-v2-attempt34-validation-hcJTAK`.
The worker reported two earlier correction cycles with four and then two legacy
canonical-hash failures; those interim raw streams were not retained and receive
no evidence claim. Exact final oracle SHA256 is
`71aa92b9740ce2b9b3745f711be81e53547ce5f4a15842c1609bc4550c45e27f`;
test SHA256 is
`507eb98f214794f36d03c7052b7f184b072edca54dbd763eaae6c001682f6032`.
No archive 38 or review 35 was started before closeout, so the corrected source
remains unreviewed and unaccepted. No compiler packet or execution is released.

The first M01 actual-method implementation packet is also rejected. Its exact
three-file state is preserved in
`evidence/stability-selected-retention-actual-method-source-failure-20260916-1.tar.gz`,
SHA256 `4fee427b35ca4f84fb4e7dd966274b9203502b49cf9893a8b7629df4fd8b5c16`,
with the independent finding in
`stability-selected-retention-actual-method-source-failure-20260916-1.json`,
SHA256 `9cbd070645e6571f8337de08c83ca6de51493e5ab8f3f791135f00a0a2c853bf`.
It used incorrect production trait/method signatures, invented private helpers,
did not compile or execute the declared rows, and relied on substring and
self-hash checks. Correction attempt 2 made no source change: truthful owned
backing, `Claim` identity, private `Call` admission and allocator-compatible
ledger hooks require a separately reviewed expansion into the generated
candidate modules. The exact blocker is retained in
`stability-selected-retention-actual-method-source-blocker-20260916-2.json`,
SHA256 `cc10877c18b02f6bf9ee070da4bb9df56f2cd3d9db3738ca3121239d35a81734`.
The rejected three raw files remain untracked and receive no implementation,
compilation, runtime or gate credit.

All bounded child agents are completed and joined. Exact live campaign identities
are launcher 1676703, recovered worker 1899017 and Codex app-server 1899019; no
project build, container build, guest, QEMU, mcexec or IHK process is live.
Unrelated Verilator activity remains outside this project and was left untouched.
Host free space is 54 GiB and scratch free space is 22 GiB. The launcher has
paused future goal continuations.

Next tasks, in order: (1) freeze correction 34, its exact final logs, archive 37
and review-34 failure as source-review archive 38; (2) obtain a fresh complete
review 35 replaying reviews 24 through 34 and adjacent schema/producer joins;
(3) only after terminal `PASS_SOURCE`, checkpoint the raw storage source and
prepare a separately reviewed conditional UID1000 compiler-only packet; (4)
independently review exact generated-candidate cfg(test) patch points and a
narrow expanded M01 allowlist before any further implementation attempt; (5)
retain M03 at its map-only blocker pending reviewed generation/pin/TLB/quarantine
authority. Counters remain 0/273 accepted application cases, 2/4 narrow fault
modes, 6/130 production gates, 350/10,000 points and 0/7 language gates. The
whole-OS objective remains incomplete and is neither resumed nor marked complete
by this window checkpoint.

Window-close checkpoint 28 stops all new dispatch after the launcher pause on
2026-09-16. The last remotely verified checkpoint before closeout is
`941ea224098f41c11f8b1adcb88925b21e5e3ae1`; local HEAD, its upstream tracking
reference, `git ls-remote` and a fetched remote archive matched. Review-input
archive 39 is retained at SHA256
`d0e8009235dce4bf61d59d28b538747af500891f42fec8cd584ebd9adea6f9bf`.

Independent storage source review 36 rejects archive 39 with `FAIL_SOURCE`.
Selectors 0/3/5 still depended on synthetic FIFO identities, selector 4 could
bypass full successful setup semantics and accept a lifecycle birth disconnected
from SETUP/REAP, and the owner could ACK a SETUP packet whose `setup_words` was
null. The exact record is
`stability-linux-collector-storage-fault-v2-source-review-failure-20260916-32.json`,
SHA256 `5ddb4fc83a98bcac9d1baca408b9ac863b801d8ebaf60ecba64fc02c7b9ca51f`.
It retains all canonical mutation hashes and gives no compiler, runtime,
application or production-gate credit.

Bounded correction attempt 36 completed before closeout and changed only the
still-untracked storage-fault fixture and its test. It adds collector-held stdin
identity to authenticated SETUP, validates all SETUP types/ranges/stat records
before ACK, validates the full successful 48-word setup contract before the
report-present branch, removes the remaining FIFO constants and joins the
complete leader PID/birth identity through child/group/SETUP/REAP evidence.
Four focused tests, both Python 3.8 and 3.9 pycompile lanes and
`git diff --check` pass. No full suite or fresh independent source review was
started after the close request. Exact final hashes are collector patch
`e58c48dea6455cf0172dd5295db149cb29b5996b03dda3631513da86e68fb7b2`,
inject header `0711a9f5bdd60326ed919a8b39d9ac081044dd054431f049aeb8c32e8803b962`,
owner `be1e3878ad6e7818d42f062ef66496b6af98f71277fcf62c55009a293ff2f94c`,
oracle `cfdbd7336241ce271d95fe3f82fce88f306a88ea5076e9df865dd03300c5a5d9`,
prepare helper `2c85d284548a8a9f426943c6c61019bbae8e13b4eabe3e662bc068b94037ab74`
and test `d1e5134a46c9edc3bae1903218b2827f3bff75e132f88fb1c26dde7c2ca8a9f7`.
Packet and tests-document hashes remain `b4acc91e6c92677f41eeaed31646cbbe4b556feee4b05a2920f78a195e60abdb`
and `eb0ad1868c021ce3091caa7095e427a3fd6a2b832dde51378842d9794deb4eb8`.
The raw source stays untracked and unaccepted.

M03 remains blocked before implementation. Architecture review 5, source audit
6, prerequisite review 7 and source audit 8 are retained at SHA256
`1c17cc25a1d63c29e49498579d9127a8f8dc3c69a9afdffe2734f4d82dce53b0`,
`69312e4be759730187babdd6ceea6ff4c23d5c51396f7855da82ab80b5b4b5e6`,
`f7c5eeb997b7da467e3941e0e3c3a70dc993ee1a1da77538b21c87a04d5ae392`
and `383d3c301abf23bc1fe5221e29f06fae10f2f83b2d78cab9f586ba44a626f76e`.
Descriptor capture must precede hash removal; XPMEM drops ownership upstream;
the proposed paths contain an ABBA lock inversion; IRQ acknowledgements lack
authentication; and the required OS/VM generation, pin and teardown authority
module does not exist. The dirty `mem_helpers.rs` and all candidate files remain
untouched. M01 remains at rejected packet attempt 5 and needs dispatcher-level
design consolidation rather than another cheap correction.

All bounded child agents are completed and joined. Exact live campaign identities
at closeout remain launcher 1676703, recovered worker 1899017 and Codex app-server
1899019. No project build, container build, guest, QEMU, mcexec or IHK process is
live; unrelated host activity was left untouched. Host free space is 53 GiB and
scratch free space is 22 GiB. The launcher controls the pause; this checkpoint
does not resume it.

Next tasks, in order: (1) independently run the complete Python 3.9 and 3.8
storage suites for correction 36 while retaining both logs and any original
failure; (2) on success, freeze archive 40 with archive 39, review-36 failure,
exact corrected sources and validation logs, then obtain fresh complete source
review 37; (3) only after terminal `PASS_SOURCE`, checkpoint the raw source and
prepare the separately reviewed conditional UID1000 compiler-only packet;
(4) consolidate M01's method/row/lifetime design before another packet review;
(5) leave M03 blocked until its missing generation/pin/ack/quarantine authority
is specified and independently reviewed. Counters remain 0/273 accepted
application cases, 2/4 narrow fault modes, 6/130 production gates, 350/10,000
points and 0/7 language gates. The whole-OS objective remains incomplete and is
not marked complete.

Continuous checkpoint 29 resumes the paused launcher-owned goal and completes
dispatcher validation of storage correction 36. The exact complete unittest
selector contains 123 methods. `/home/holden/anaconda3/bin/python3.9` 3.9.12 and
`/usr/bin/python3.8` 3.8.10 each pass 123/123; both pycompile the four fixture
Python sources, and `git diff --check` passes. Raw logs and interpreter-byte
identities remain at
`/home/holden/mckernel-work/scratch/storage-fault-v2-attempt36-validation-Cd6WD0`.
An independent read-only audit confirmed the selector/count and the exact current
packet, tests-document and test hashes; it also confirmed that no post-correction
full-suite evidence existed before this run.

Fresh source-review archive 40 is 38,007,901 bytes with 32 unique safe members
and 22 files at SHA256
`5f43d6af69298a84c980b04aa65f66a18c7e621043767a12f69039ed444e0a30`.
It binds archive 39, review-36 failure record 32, the exact correction-36 source,
both complete raw test logs, interpreter identities, status files, both empty
pycompile streams and the empty diff-check stream. This is source-review input
only: the raw fixture and test remain untracked and unaccepted, and no compiler,
root, native, application or production gate is released before fresh independent
review 37 returns terminal `PASS_SOURCE`.

Next tasks: (1) checkpoint and fetched-blob verify archive 40; (2) obtain a fresh
complete Astra/high review 37 that replays reviews 24 through 36 and audits the
full producer/owner/oracle schema; (3) on `PASS_SOURCE`, checkpoint the exact raw
source and prepare the separately reviewed conditional UID1000 compiler-only
packet, otherwise retain the exact finding and bounded correction; (4) continue
independent M01 design consolidation while leaving M03 behind its missing
generation/pin/ack/quarantine authority. Counters remain 0/273 application cases,
2/4 narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7 language
gates. The whole-OS objective remains active and incomplete.

Window-close checkpoint 30 stops new dispatch after the user paused future goal
continuations on 2026-09-16. Independent storage source review 37 rejects archive
40 with `FAIL_SOURCE`: one hard-coded FIFO-identity oracle remained, selector 4
accepted a zero executable seal, and pre-ACK owner/oracle integer domains were
not fully bounded. The exact finding is
`stability-linux-collector-storage-fault-v2-source-review-failure-20260916-33.json`,
SHA256 `bc7b38d29f482cf1857af6d6bea506935968aa89ffb09f587a807b4cfff2a62b`.
No compiler, root, native, application or production-gate credit is granted.

Bounded correction 37 changes only the still-untracked storage fixture and its
test. It derives the remaining FIFO identities from authenticated setup data,
requires a nonzero complete executable seal, and bounds the owner/oracle pre-ACK
integer domains. The dispatcher strengthened the regression so it proves the
archive-40 behavior against the corrected behavior and binds the canonical setup
and packet mutations. The final Python 3.9 and 3.8 lanes each pass 124/124, both
pycompile lanes pass, their outputs are identical, and `git diff --check` passes.
The complete validation directory is
`/home/holden/mckernel-work/scratch/storage-fault-v2-attempt37-validation-3uzTam`.
Final hashes are owner
`fc863e02ea8a312796b5c0cac7cc9253bc390920cc36dd38b3833b0f3a889912`,
oracle `84c8d23fbdf740e89d437bc0ad81fff3bcdcc1ff4ea2900c258e1c0ee61e6134`
and test `62c4fa16a14814a8d744a77664abe78de4d721759143a1934f3aa4c4c58c0596`;
the collector, inject-header, prepare, packet and tests-document hashes remain
`e58c48dea6455cf0172dd5295db149cb29b5996b03dda3631513da86e68fb7b2`,
`0711a9f5bdd60326ed919a8b39d9ac081044dd054431f049aeb8c32e8803b962`,
`2c85d284548a8a9f426943c6c61019bbae8e13b4eabe3e662bc068b94037ab74`,
`b4acc91e6c92677f41eeaed31646cbbe4b556feee4b05a2920f78a195e60abdb`
and `eb0ad1868c021ce3091caa7095e427a3fd6a2b832dde51378842d9794deb4eb8`.

Fresh source-review archive 41 is 38,136,275 bytes with 36 safe members and 26
files at SHA256
`b96f2107b6a2857b3995b65e626c9d8b5a47d0a9d5fd8f697489baab6779a5e0`.
It binds archive 40, failure record 33, the exact final source, both final 124-test
logs, the earlier correction logs, identities, statuses, pycompile outputs,
diff-check output, commands and source hashes. It is review input only. No fresh
review 38 was dispatched before closeout, so the raw source remains untracked and
unaccepted and no conditional compiler packet is released.

M01 remains blocked before implementation. Design consolidation 6 returns
`FAIL_DESIGN` at SHA256
`0453a3908c846ea2ab20455e4d44a808cafb2b84452f3bb608ac4124dbabfc98`:
the generic actual-method sequence is viable but native ownership remains absent.
Native backing architecture review 7 returns `FAIL_ARCHITECTURE` at SHA256
`0b997e2c65f443bf28a99e7e9494eb0c224bbad77f1b3a26eaa74c4894e14f4e`:
`Memory::new` metadata and copied `Claim` data are not backing leases, and a
reviewed native owner graph or test-owned ledger model is still required. The
generic-only implementation packet 8 is retained at SHA256
`624a7182330e941ee03cd7b9fdc07554b8033710ffe29e88d00033e4917afe5b`,
but independent review 9 returns `FAIL_PACKET` at SHA256
`10bbc15b9bf9aa68e5145d6722bdba22d242c6d91fc467448504abd9e4dfc4e2`.
It requires one authoritative evidence allowlist, corrected return types, a legal
direct negative-TID route, a complete rows 01-27 result matrix, and explicit
mode-2 notify and clock wiring. No M01 implementation is released.

All bounded child agents are completed and joined. Exact live campaign identities
at closeout are launcher 1676703, recovered worker 1899017 and Codex app-server
1899019. No project build, container build, guest, QEMU, mcexec or IHK process is
live. Host free space is 52 GiB and scratch free space is 22 GiB. The launcher
controls the pause; this checkpoint neither resumes nor completes the goal.

Next tasks, after a future launcher continuation, are: (1) obtain a fresh complete
Astra/high source review 38 of exact archive 41, replaying all historical controls
and adjacent producer/owner/oracle domains; (2) only on terminal `PASS_SOURCE`,
checkpoint the raw storage source and prepare the separately reviewed conditional
UID1000 compiler-only packet, otherwise retain the finding and use one bounded
correction; (3) make one bounded correction to generic packet 8 from review 9 and
obtain a fresh independent packet review; (4) keep native M01 and M03 blocked
until their missing ownership/generation/pin/ack/quarantine authorities are
specified and independently accepted. Counters remain 0/273 application cases,
2/4 narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7 language
gates. The whole-OS objective remains incomplete and is not marked complete.

Continuous checkpoint 31 resumes the launcher-owned objective from fetched
checkpoint `aa5fa4e21d014e6f1fc5a67c7578d85070c8414e`. Independent storage source
review 38 authenticates archive 41 and returns `FAIL_SOURCE`: post-fork SETUP
could substitute executable-backing size zero or permissions 0600 while both the
pre-ACK owner and full oracle accepted it for selectors 0, 3, 4 and 5. The exact
selector-4 compact packet hashes are
`59f63e520e309b23bc4f3ebce008cd31c84bedd9835fd07498dcef51389591a1`
and `f0854a4c4883ecb46218b9bddd6f01234673766456e3755a117aaa627596cbb0`.
The additive failure record is
`stability-linux-collector-storage-fault-v2-source-review-failure-20260916-34.json`,
SHA256 `c658c81e76ca9d439b32b22290c1c87989d9e01f977b651519ef1985473630dc`.

Bounded correction 38 changes only the still-untracked owner, oracle and test.
Before ACK it now requires the successful regular executable backing to have
exact permission bits 0500 and the authenticated runtime executable size. The
oracle enforces the same contract before report-presence branching and joins
device, inode, mode and size through SETUP, sealed backing and observed post-exec
backing when a report exists. A new independently rebound archive-41 regression
proves both old accepts and current rejects for both mutations across all four
post-fork selectors and computes the two canonical hashes. The dispatcher-owned
Python 3.9.12 and Python 3.8.10 lanes each pass 125/125; both pycompile lanes and
`git diff --check` pass. Exact final hashes are owner
`ddf0e8427a58feb82c830502eafe453eb26953d926c21238ba95345378a608d4`,
oracle `8769f9bee3f58bade679018b970242180a3862ce9a9ee3af15ccb9410cbd1d93`
and test `f0695c2ae43a9494afb5a507c5c82fc673d6c42d5a660104f77fc915a27c15ad`.
Raw validation is retained at
`/home/holden/mckernel-work/scratch/storage-fault-v2-attempt38-validation-SHftRS`.

Fresh source-review archive 42 is 38,261,570 bytes with 35 safe unique members,
25 files and 24 verified manifest bindings at SHA256
`c6e56b1332ec8b457cd3c031a0f1833e72d5edf6ce0d9b17d5417545603181e1`.
It binds archive 41, review-38 failure record 34, exact current source and all
dispatcher validation identities, commands, statuses and streams. This remains
review input only. The raw fixture/test are untracked and unaccepted; compiler,
root, native, guest, application and production execution remain closed pending
a fresh terminal `PASS_SOURCE`.

M01 generic packet corrections 10 and 11 both fail fresh Astra/high review.
Review 10 is retained at SHA256
`c102ca7832148b3ca7e5d8937f68b17181a00fda7a22264dfa28b66b225f6f6c`.
The Terra escalation closes preparation ordering, held publication, exact mode-2
notify, negative-TID ownership and fresh recovery history, but review 11 still
rejects exact packet SHA256
`8071bd38119ecc11e58e5e68c5b41ae5bee89a760d461350509442ec7af5744c`.
Row 20A, rows 25/26B, changed-key row 17 and direct rows 22-24 retain wrong or
conflated state-machine results, and the matrix still leaves exact latch, wake,
hook and terminal-ledger values implicit. Review 11 is retained at SHA256
`64e413b8e0916bba4b48c16587fca9e0c1425b8c6d279c3916d4a4c5c29fe733`.
Under the bounded retry rule, another cheap packet edit is stopped; M01 returns
to dispatcher-level exact state-machine consolidation. No implementation is
released and native backing ownership remains independently blocked.

Next tasks: (1) checkpoint and fetched-blob verify archive 42 and the exact
failure records; (2) obtain a fresh complete Astra/high source review 39 of
archive 42, replaying every retained control and adjacent executable-backing
schema join; (3) only on terminal `PASS_SOURCE`, checkpoint the exact raw source
and prepare the separately reviewed conditional UID1000 compiler-only packet;
(4) separately consolidate M01's exact per-operation state matrix before a new
packet version; (5) retain M03 behind its generation/pin/TLB/quarantine ownership
blocker. Counters remain 0/273 application cases, 2/4 narrow fault modes, 6/130
production gates, 350/10,000 points and 0/7 language gates. The whole-OS
objective remains active and incomplete.

Continuous checkpoint 32 preserves independent storage source review 39 and its
bounded correction. Review 39 authenticates archive 42 but returns `FAIL_SOURCE`:
the actual owner launch passed the instrumented collector ELF size to SETUP
validation even though SETUP describes the separately authenticated payload
fixture. With collector size 24 and valid payload backing size 27,448, all four
post-fork selectors fail before ACK; changing only the backing size to 24 wrongly
passes the pre-ACK schedule. The exact finding is
`stability-linux-collector-storage-fault-v2-source-review-failure-20260916-35.json`,
SHA256 `e2f0170f8d2ddfaab916c0812a990cc59f2b66f02c939563a8d4946b3c05f44d`.
Selector-4 complete-fixture SETUP hashes are
`30cab2013a195b0291ddc845c1aeecc84b3c1f03b446e06ccdd00c67ef658d95`
for valid size 27,448 and
`92d4f5d03902cfe5f0dbd372d7d6263b493b2498257c5107daf3e24cd2a03ebf`
for invalid collector size 24.

Correction 39 changes only the still-untracked owner and test. The actual launch
now supplies `runtime_inputs["fixture"]["size"]` to pre-ACK validation. A new
real-launch-path control exercises selectors 0, 3, 4 and 5 with the deliberately
different collector and payload sizes: valid 27,448 reaches normal EOF and size
24 rejects before ACK; archive 42 retains the old behavior. Dispatcher-owned
Python 3.9.12 and 3.8.10 each pass 126/126, both pycompile lanes pass and
`git diff --check` passes. Exact final owner SHA256 is
`fc0e5ee9451aa2e9b23a6a7aab4460706453d9eea46a9b96e0f9802369230a2b`;
test SHA256 is
`c80bf1e10c0c487e4fec2157dd9be800533b581114e6e4af4a21faa2b431ac21`.
Raw logs remain at
`/home/holden/mckernel-work/scratch/storage-fault-v2-attempt39-validation-6k7COf`.

Fresh source-review archive 43 is 38,388,429 bytes with 35 safe unique members,
25 files and 24 verified manifest bindings at SHA256
`5251a83bb4d2b2446c39156a7de1cbb6197e20c79e9cf23777b80f851a38da28`.
It binds archive 42, failure record 35, exact current source and all dispatcher
validation inputs and outputs. This is review input only; raw storage source stays
untracked and unaccepted and no compiler or runtime gate is released.

M01 state-machine consolidation 12 returns `FAIL_DESIGN_MATRIX` and is retained
in `stability-selected-retention-generic-actual-method-design-matrix-failure-20260916-12.json`,
SHA256 `6cd2e5f52b163a536b32e6473ed3f9eccfe179ff89ceba776f9dfc6a60d9e0ab`.
It source-derives the disputed row-17, row-20A, row-25/26B, held-latch,
mode-3 recovery and direct-versus-mailbox results, but correctly refuses to invent
the remaining fixture values and TestResponseMemory teardown ledger. The smallest
safe next packet is generic backing/ledger plus only actual admitted preparation,
row 03 hold and row 12 wake-None release; negative preparation, identity/cancel
and transport/clock work remain separate later packets. No M01 implementation is
released.

Next tasks: (1) checkpoint and fetched-blob verify archive 43 and the two new
failure records; (2) obtain fresh complete Astra/high source review 40 of exact
archive 43; (3) only on terminal `PASS_SOURCE`, checkpoint the raw storage source
and begin a separately reviewed conditional UID1000 compiler-only packet; (4)
freeze explicit M01 backing/ledger teardown choices for the narrow row03/row12
packet; (5) keep M03 closed behind its missing generation/pin/TLB/quarantine
authority. Counters remain 0/273 application cases, 2/4 narrow fault modes,
6/130 production gates, 350/10,000 points and 0/7 language gates. The whole-OS
objective remains active and incomplete.

Work-window closeout 33 records the user-requested pause after fetched checkpoint
`87d96366c8264a81ee77ebcec61e3fa2fae9ba74`. No new task was dispatched after
the pause request. All three bounded child lanes are complete and joined: M01
state-matrix review 12 returned `FAIL_DESIGN_MATRIX`, storage correction 32 is
superseded by the retained later correction, and storage correction 39 passes
both 126-test Python lanes plus pycompile and diff checks. No child operation is
live. Original failures, review archives, raw validation directories and the
still-untracked storage source remain preserved; source acceptance is not
inferred.

Exact live campaign identities at closeout remain launcher PID 1676703,
recovered worker PID 1899017 and Codex app-server PID 1899019. No project build,
container build, guest, QEMU, mcexec or IHK process is live. The dispatcher event
ledger is valid JSONL through 584 records, including the fetched checkpoint event.
Host free space is 50 GiB and scratch free space is 22 GiB. The launcher owns the
pause and future continuation; this closeout neither resumes the goal nor marks
it complete.

Next tasks after an explicit future continuation are: (1) obtain fresh complete
Astra/high source review 40 of exact archive 43, authenticating and replaying all
reviews 24-39 and the distinct collector/payload-size launch path; (2) only on a
terminal `PASS_SOURCE`, preserve its pass record, stage the exact raw storage
source, checkpoint it and prepare a separately reviewed conditional UID1000
compiler-only packet; otherwise retain the new failure and make only one bounded
correction; (3) freeze explicit M01 generic backing/ledger teardown choices and
prepare only the narrow actual-admission, row03-hold and row12-release packet;
(4) keep the negative/key-cancel/clock M01 work separate and M03 closed behind
its generation, descriptor-pin, authenticated-TLB-ack and quarantine-ownership
blockers. Counters remain 0/273 application cases, 2/4 narrow fault modes,
6/130 production gates, 350/10,000 points and 0/7 language gates. Whole-OS
acceptance remains incomplete.

Continuous checkpoint 34 resumes the launcher-owned objective after fetched
checkpoint `13445bf54d0f35b256c88b50cdde5415e69269bb`. Independent storage source
review 40 authenticates archive 43 but returns `FAIL_SOURCE`: for selectors 0,
3 and 5 the complete oracle accepted report executable `source_before` and
`source_after` sizes zero while the authenticated payload and retained executable
remain 27,448 bytes. The additive failure record is
`stability-linux-collector-storage-fault-v2-source-review-failure-20260916-36.json`,
SHA256 `7fb9aaab0597330a4952188247ea6582b7fa1fbd9757ab5933cbed1eaf5ed2ae`.
Correction 40 joins both source sizes to both the authenticated runtime fixture
size and independently retained byte count. Dispatcher Python 3.9 and 3.8 each
pass 127/127, dual pycompile and diff check pass. Archive 44 is 38,514,524 bytes,
35 safe unique members, 25 files and 24 verified bindings at SHA256
`5ddf13abf15505cc8ebbf71abfac7175603293b2dac46ee01aa3ddf952486153`.

Independent review 41 authenticates archive 44 and correction 40, then returns
`FAIL_SOURCE`: the oracle still accepted non-executable report source modes even
though `seal_source` rejects them. Failure record 37 is SHA256
`4495ae0738b08cd45b54639528dcc64bb78c2ff1dd3d2cdfaeef6166fee031ca`.
Correction 41 now applies the producer's exact regular-file, any-execute-bit and
no-setuid/setgid predicate only to executable report sources; generic stdin
validation remains non-executable. The initial worker log-path failure and first
mis-scoped focused-test failure remain preserved. The corrected focused test and
clean dispatcher Python 3.9/3.8 lanes each pass 128/128; both pycompile lanes and
the full diff check pass. Exact final oracle SHA256 is
`f14211e3f7bf1fc42367c58f0617de66d93ff130dd238eb953ce6fc705cd5a11`
and test SHA256 is
`a70a1ff3d639dffed070ee578e8ab35e0aa02c055cb3ad9beda8db5897786d74`.
Archive 45 is 38,640,721 bytes with 35 safe unique members, 25 files and 24
verified bindings at SHA256
`ced17e4703ca50a1797ac5531d95653f0f4ad408215d0d0da4d63e2cb0ee57fb`.
Raw storage source remains untracked and unaccepted pending complete review 42;
no compiler or runtime gate is released.

M01 design-input review 13 freezes the remaining ambiguity: production source
proves row03 and row12 publication outcomes but not a Drop/quarantine/deallocation
ledger. Packet 9 then fails independent review 14 on one mistyped input hash and
an allowlist total of 344 rather than 346; both are preserved. Additive packet 10,
SHA256 `7e934ff07a79eb89c533114552c43b50379f3a6028f25b501cc13a38ac344c57`,
corrects only those findings and receives independent `PASS_PACKET` review 15.
Its fixture-owned Box/Arc transfer, deferred/quarantine snapshots, explicit
post-snapshot drains and row03/row12 source traces are accepted for bounded
source staging only. The review record SHA256 is
`e7d38285b99ad21329ad497516547d9ace150172f38905d2c4d77c29503461d9`;
an additive timestamp correction preserves that consumed byte identity because
its embedded time was entered ahead of the host clock.

M01 implementation 16 authenticates and stages all 102 source members and the
expected 346 files, but hard-stops when a Python syntax check creates unlisted
`__pycache__/result-parser.cpython-39.pyc`, making 347 files. Nothing is deleted
or retried. The complete 359-member/347-file failure archive is 1,001,844 bytes
at SHA256 `43004cea9973639ae59bb4df8af431ebb9d25bf58afac0ff2b0faeb32a475f0c`;
the additive failure record binds the manifest, parser, bytecode, per-mode result
and identical failure hashes. No compilation, execution or M01 credit follows.

Crash recovery retained launcher PID 1676703 and replaced the worker/app-server
pair with recovered worker PID 2172732 and app-server PID 2172734. The heavy
lease is free; no project container build, guest, QEMU, mcexec or IHK process is
live. Host free space is 48 GiB and scratch free space is 22 GiB. Next tasks are:
(1) checkpoint and fetched-blob verify archives 44/45 and all M01/M02 additive
records; (2) obtain complete source review 42 of exact archive 45; (3) only on
terminal `PASS_SOURCE`, checkpoint the exact raw storage source and prepare the
separately reviewed conditional UID1000 compiler-only packet; (4) independently
review one additive M01 rerun packet that disables Python bytecode writes and
uses a fresh root; (5) keep M03 behind its generation/pin/authenticated-ack/
quarantine ownership blockers. Counters remain 0/273 application cases, 2/4
narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7 language
gates. Whole-OS acceptance remains incomplete.

Work-window closeout 35 records the user-requested pause after checkpoint
`0fffdc1d71b7b1de6601f05d51fef63d1f0d5beb`. No task was dispatched after the
pause request. All three bounded child lanes are complete and joined; no child
operation, project build, container build, guest, QEMU, mcexec or IHK process is
live. The launcher PID is 1676703, recovered worker PID 2172732 and app-server
PID 2172734. The heavy lease is free. Host free space is 46 GiB and scratch free
space is 22 GiB. The launcher owns the pause and future continuation; this
closeout does not resume or complete the OS goal.

Storage review 42 rejected archive 45 because signed-negative report stat fields
were accepted outside producer ranges. Failure record 38 is SHA256
`9488b12ca9cfd21a18d607b0b407b624c6e7f60eb782b9b47811a66963bd1fd8`.
Correction 42 adds the producer-aligned unsigned/signed/nanosecond ranges;
dispatcher Python 3.9 and 3.8 each passed 129/129 with both pycompile lanes and
the diff check. Archive 46 is 38,768,062 bytes, 35 safe unique members, 25 files
and 24 bindings at SHA256
`15ac775cf137503ae69c10220db13467f9fb3c49a5df650d6514573e5ce94187`.
Review 43 then returned `FAIL_SOURCE`: the authentic post-fork stdout is exactly
`DEVNULL\n`, while report-present records could rebind arbitrary output and the
synthetic selector-4 positive expected empty output. Failure record 39 is SHA256
`a9abaa2d3f0c9b9c13503f85a10aebf72aa9bf0f465e68d63a0bfa636ba9be96`.

Correction 43 binds exact authenticated stdout/stderr content and its focused
test passes, but the first full Python 3.9 lane stops at 130 tests with 13
failures and four errors. Those are the preserved cascade from changed canonical
fixture hashes and historical empty-output selector-4 oracles; Python 3.8 was not
run. The exact source, tests, logs and bytecode capture are archived in
`stability-linux-collector-storage-fault-v2-correction-validation-failure-20260916-43.tar.gz`,
405,325 bytes at SHA256
`eddfcfe96959c53e2d39d9f3b2228ee94d94eb36a4e6c15d074e3d58d09948d9`.
Raw storage source remains untracked and unaccepted. No archive 47, compiler
packet, compilation, root run, native run or gate credit is released.

M01 packet 11 prevents bytecode creation and receives `PASS_RERUN_PACKET` review
17, but implementation 18 is a semantic evidence failure. Its adapter drops the
Box instead of retaining real deferred/quarantine ownership, its runner only
names the required methods in string literals, and its asserted diff/inverse
records are not real bindings. The complete immutable failure archive is
1,001,218 bytes, 357 members and 346 files at SHA256
`7637f909c7b53c3dd4171e4bee696fbe5d086a35ce5fb838da156d8cf988e3e4`;
the failure record SHA256 is
`346dcc884122f7e6a1ebf4032f014d91cfb008f1a37167038b3b6cfcf0997659`.
Independent escalation 20 returns `PASS_REMEDIATION_DESIGN` only: a future
standalone host-test crate must invoke the real mailbox chain, use actual
mutex-owned Box queues, expose only a cfg(test) post-store metadata hook, drain
outside the lock, and run each row/mode in a fresh process. It releases no
implementation, compilation, runtime result or acceptance credit.

Next tasks after an explicit future continuation are: (1) correct only the
storage validation cascade by cloning historical empty-output fixtures and
rebinding every exact hash changed solely by the authenticated positive output,
preserving every intermediate failure; (2) rerun complete Python 3.9/3.8,
pycompile and diff lanes, then freeze archive 47 for a new independent source
review; (3) only after terminal `PASS_SOURCE`, checkpoint the exact raw storage
source and prepare the separately reviewed conditional UID1000 compiler-only
packet; (4) convert M01 remediation review 20 into a new bounded packet before
any further implementation, compilation or execution; (5) keep M03 closed
behind its generation, descriptor-pin, authenticated-TLB-ack and quarantine
ownership blockers. Counters remain 0/273 application cases, 2/4 narrow fault
modes, 6/130 production gates, 350/10,000 points and 0/7 language gates. The
whole-OS objective remains active, paused by the launcher, and incomplete.

Continuous checkpoint 36 resumes the launcher-owned objective after fetched
checkpoint `fa32eddbb0f87732b8b5864e041cdce89584039e`. Storage correction 44
separates historical selector-4 empty-output fixtures from the authentic
`DEVNULL\n` positive and updates only the canonical hashes changed by that
output. Independent dispatcher Python 3.9 and 3.8 lanes each pass 130/130;
both pycompile lanes and the diff check pass. Archive 47 is 39,301,852 bytes,
37 safe unique members, 27 files and 26 verified bindings at SHA256
`0f1c14cb106d0ec4e055c3fd18b46710111941fa22b7c6cfaf2a5ba6077c88ee`.

Complete source review 45 authenticates archive 47 and its 24-level lineage but
returns `FAIL_SOURCE`: `Path.exists()` treated dangling `report.json` and
`events.jsonl` symlinks as absent for selectors 4 and 1, contradicting the
producer's `O_NOFOLLOW` semantics. Failure record 45 is SHA256
`d700b33a157a26ebc992e7203acca086a9b8c31c28ff3bc4c5893893acb78d76`.
Bounded correction 46 adds one shared `lstat`-based genuine-ENOENT predicate,
routes all four applicable absence checks through it and adds symlink,
genuine-absence and lookup-error controls. Worker Python 3.9 and 3.8 each pass
131/131, both pycompile lanes and the diff check; exact oracle SHA256 is
`c61ff1740cd41b17416103ef5c312a855c73261b4118c2a6b1fe5e04e11f7d9d`
and test SHA256 is
`1c46cad58634f430162398e1a9594613d4432071daa48d14fca3ebc72c51898a`.
Dispatcher replay, archive 48 and independent review remain pending. Raw source
is still untracked and unaccepted; no compiler/root/native/runtime gate is open.

M01 remediation packet 21 fails review 22 on a malformed checkpoint ID and a
circular manifest self-hash requirement. Its bounded correction packet 23 fixes
those two items but improperly condenses away exact event-order, inverse,
identity and cfg-erasure requirements, so review 24 also returns `FAIL_PACKET`.
Both failures are preserved. Escalated packet 25 restores all nonconflicting
packet-21 requirements, applies only the reviewed pin/self-binding changes and
adds exact request, Claim and method-chain values. Independent review 26 returns
`PASS_PACKET`, SHA256
`e1e371cf469897d1bfa2f34c765c49ed571063d2e46f91c029a31423005d59e6`,
releasing exactly one fresh 346-file source-staging attempt. It releases no
compilation, execution, native-backing or acceptance credit.

Next tasks are: (1) independently replay correction 46, freeze archive 48 and
obtain a fresh complete source review; (2) only on terminal `PASS_SOURCE`,
checkpoint the exact raw storage source and draft the separately reviewed
conditional UID1000 compiler-only packet; (3) execute one source-stage-only M01
attempt under packet 25, preserve its exact evidence and obtain independent
review before compilation; (4) keep M03 closed behind its generation,
descriptor-pin, authenticated-TLB-ack and quarantine-ownership blockers.
Counters remain 0/273 application cases, 2/4 narrow fault modes, 6/130
production gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance
remains incomplete.

Continuous checkpoint 37 follows fetched checkpoint
`bc8940f17bf52623338813a7f32622f2bf39c053`. Dispatcher replay of storage
correction 46 passes Python 3.9 and 3.8 at 131/131, both pycompile lanes and
the diff check. Archive 48 is 39,429,878 bytes with 35 safe unique members,
25 files and 24 verified bindings at SHA256
`9b5221804efc5713fb11b58b97e0ebd7c991a261dcdf00c54eee7f02f87a12ca`.
Source review 47 accepts the nonfollowing absence correction but returns
`FAIL_SOURCE`: the create validators did not join directory type/fd/device/inode
across BEFORE/AFTER and both create sites. Failure record 47 is SHA256
`cde1f200b4f3800fe2b8d0c3a458139e1dc4f1794d1dceb37e4507505aba4ecb`.

Correction 48 aligns offline and pre-ACK validators, and dispatcher Python 3.9
and 3.8 each pass 132/132 plus both pycompile lanes and the diff check. Archive
49 is 39,559,661 bytes, 35 safe unique members, 25 files and 24 bindings at
SHA256 `ee042f98bc832d77b00d166c500bd59b510d158c8c8e5a38d117dd325fe80805`.
Review 49 returns a distinct `FAIL_SOURCE`: the join was still per create site,
so report-create could replace the live attempt-directory authority and the
directory fd was not reserved against regular-file descriptor/BIND aliases.
Failure record 49 is SHA256
`88a568224aadc132eb1c7150486cc80f5eab57d6b933c49ddbde88c60038ff1b`.
Correction 50 is active and must bind one persistent directory authority across
both sites and its full source-defined lifetime while excluding size. Raw source
remains untracked and unaccepted; compiler, root and native execution remain
closed.

M01 source-stage attempt 27 authenticates packet 25/review 26, creates exactly
346 allowed files with no bytecode and stages all 102 source members, but hard
stops before compilation. Its manifest is a four-field stub that enumerates no
paths; adapter diffs/inverses and result observations are not genuine. The full
357-member failure archive is 990,614 bytes at SHA256
`3b61378e8fdb9ad1894669ceb136c553ed683a7b1b6a2b273be3df335086f86d`.
Hard review 28 confirms limited genuine queue ownership progress but finds
string-only runners, wrong trait qualification, missing Claim/address/drain
behavior, fabricated status and stub evidence/parser artifacts. Its record is
SHA256 `8300a63954d2f7aab4f6afb3cba31beb00dbd9c2890ef5dd09a4817b0864540c`.
No retry is released; the feasible packet now needs a directed Rust
implementation owner and separate evidence owner before any compilation.

Next tasks are: (1) finish and independently replay storage correction 50,
freeze its next archive and obtain complete source review; (2) only after
terminal `PASS_SOURCE`, checkpoint the raw source and prepare the separately
reviewed conditional UID1000 compiler-only packet; (3) perform directed M01
source implementation from review 28 rather than another template retry, then
obtain independent evidence review; (4) keep M03 closed behind generation,
descriptor-pin, authenticated-TLB-ack and quarantine-ownership blockers.
Counters remain 0/273 application cases, 2/4 narrow fault modes, 6/130
production gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance
remains incomplete.

Work-window closeout 38 follows fetched checkpoint
`ae184ee592c2f83a4b92ba419b532e6c68462277`. No task was dispatched after the
user's pause request. All three bounded child lanes are complete and joined;
no project build, container build, guest, QEMU, mcexec or IHK process is live.
The launcher PID is 1676703, recovered worker PID 2238392 and app-server PID
2238394. The heavy lease is free. Host free space is 43 GiB and scratch free
space is 21 GiB. The launcher owns the pause and future continuation; this
closeout neither resumes nor completes the OS goal.

Storage correction 50 passed dispatcher Python 3.9 and 3.8 at 132/132 plus
both pycompile lanes and the diff check. Its immutable archive 51 is 39,690,015
bytes, 35 safe unique members, 25 files and 24 verified bindings at SHA256
`f5de5ac40efdbafe780500aeb81aa0e5b2dbd6b63e850ee0bf835b8d5074d456`.
Independent review 51 returns `FAIL_SOURCE`: all validators accept EOF records
that falsely close the still-live attempt-directory, events or request
descriptor. The exact review record SHA256 is
`23cf40bec561751b27d5f70645da9cafc1cbbdb35fff179cfc8fb6f3812c0046`.
Correction 52 adds the intended live-capability checks, but hard-stops on the
focused Python 3.9 import because the new regression lambda has mismatched
bracket/parenthesis syntax at test line 4352. No full suite, Python 3.8 lane,
archive or source acceptance follows. The exact in-place candidate hashes and
failure are preserved in the additive correction-52 failure record; raw source
remains untracked and unaccepted.

M01 directed implementation packet 29 is SHA256
`7fa429e0d3e4a960d514296b7cd9fcae71a3e82285efd7513420b9837043e753`.
Independent review 30 returns `FAIL_PACKET`, record SHA256
`18c99d3f3b57340addde3fc2880a4b7ba1e47d3920817b2948bcee8e738c41d2`:
an early Phase I failure has no authorized evidence owner because Phase I may
not create `failure.txt` and Phase II begins only after successful handoff. The
success-path Rust/evidence design is otherwise feasible. No Phase I or II
implementation, compilation, execution or credit is released.

Next tasks after an explicit future continuation are: (1) correct only the
correction-52 test syntax, run its focused case and complete Python 3.9/3.8,
pycompile and diff lanes, then freeze a fresh immutable review archive and
obtain independent source review; (2) only on terminal `PASS_SOURCE`, checkpoint
the exact raw storage source and prepare the separately reviewed conditional
UID1000 compiler-only packet; (3) issue an additive M01 packet correction that
authorizes narrowly scoped Phase I early-failure capture while keeping 346 files
as the success-only handoff count, then independently review it before any
implementation; (4) keep M03 closed behind generation, descriptor-pin,
authenticated-TLB-ack and quarantine-ownership blockers. Counters remain 0/273
application cases, 2/4 narrow fault modes, 6/130 production gates, 350/10,000
points and 0/7 language gates. Whole-OS acceptance remains incomplete.

Continuous checkpoint 39 resumes after fetched checkpoint
`353dbeb56a5ca7590516d6d9662fe36b73cde68d`. Storage review 55 first confirms
the complete 36-case EOF alias correction, then returns `FAIL_SOURCE` because
BIND did not join both old/new sizes to the empty successful-create snapshot.
Correction 56 adds that join and passes both Python versions at 134/134, but
review 57 finds three additional producer-model gaps: exact `high_fd`
transition/domain rules were absent, fixed witness socket fd 198 was not
reserved, and regular-file identities could alias the live attempt-directory
device/inode. The exact review-57 record SHA256 is
`0abed1c3f09eab131c2e3cfc717f782be1ff806f84763eb95c9e7238f0f8b529`.

Correction 58 implements all three invariants and the complete negative matrix.
Its first full dual-Python run rejects the intended contradictions but changes
three retained diagnostic precedences; the exact source/log failure archive is
99,201 bytes at SHA256
`4be555440fa79fc90e6850699918af739d56341aed2a21e7027718b3e6297e95`.
Correction 59 restores type/range diagnostic precedence without weakening the
new rules. The focused high-fd/fd198/inode, BIND-size and EOF matrices pass;
Python 3.9 and 3.8 each pass 135/135, both pycompile lanes and the diff check.
Immutable archive 60 is 40,237,424 bytes with 39 safe unique members, 29 files
and 28 bindings at SHA256
`342686df29a5a7c8fe91a34905dac92a794db0b09656a6aa189c23b0605dc47e`.
Complete independent review 60 is active. Raw source remains untracked and no
compiler, root, native or runtime lane is released.

M01 packet corrections 31/34/36 receive source-staging release after resolving
early-failure ownership, exact real APIs, canonical handoff identity and final
manifest self-binding. Phase I attempt 33 nevertheless fails independent review:
its mailbox/request/trait calls are incompatible, status evidence is fabricated,
scenarios are incomplete and its claimed handoff hashes have no retained bytes.
The preserved 326-file archive is SHA256
`02a538557b4b080df4468d6871e5263ac685fcc337f358c16ccee15e0dc823fa`.
Attempt 38 then correctly hard-stops when mode3 attempts to re-export the mode2
adapter; its 325-file archive SHA256 is
`18653b8eed7614d42e7d72803845fd77f12472762caa3d4569ab7a0a388bef72`.
Correction 39 independently passes review 40 and forbids all cross-mode backing.
Attempt 41 independently stages both modes but correctly hard-stops because its
post-store hook calls nonexistent `stability_observer::status_store`; its exact
327-file archive SHA256 is
`3281d44021b6af2adfe22ee4cf9f72bd4731e688d7b49acf74a88a28d5ee419f`.
No handoff, Phase II, compilation, execution or credit follows any attempt.

Launcher PID 1676703, recovered worker PID 2238392 and app-server PID 2238394
remain live. The heavy lease is free; no project build, container build, guest,
QEMU, mcexec or IHK process is live. Host free space is 43 GiB and scratch free
space is 21 GiB. Next tasks are: (1) finish independent storage review 60 and,
only on terminal `PASS_SOURCE`, checkpoint exact raw source then draft the
separately reviewed conditional UID1000 compiler-only packet; otherwise preserve
the new finding and make one bounded source correction; (2) define and review
the exact test-only observer metadata recorder for M01 before another fresh
source-stage attempt; (3) keep M03 closed behind generation, descriptor-pin,
authenticated-TLB-ack and quarantine-ownership blockers. Counters remain 0/273
application cases, 2/4 narrow fault modes, 6/130 production gates, 350/10,000
points and 0/7 language gates. Whole-OS acceptance remains incomplete.

Work-window closeout 40 follows fetched checkpoint
`a192c3fee872f0838da6665b7a14fcea1cbc4a2a`. No task was dispatched after the
user's pause request. The two already-complete M01 child lanes were joined, and
the active storage reviewer was stopped only after reporting its terminal
source-bound result. No project build, container build, guest, QEMU, mcexec or
IHK process is live. Launcher PID 1676703, recovered worker PID 2238392 and
app-server PID 2238394 remain live for the launcher's paused state. The heavy
lease is free. Host free space is 42 GiB and scratch free space is 21 GiB. The
launcher owns future continuation; this closeout neither resumes nor completes
the OS goal.

Storage review 60 returns `FAIL_SOURCE`. It confirms that all 292 accumulated
packet negatives reject in both packet validators and the complete memory-backed
oracle and that 24 retained baseline/size/reuse positives pass, but finds three
new blockers. Actual child descriptor remapping in `witness_owner.launch` and
`supervise.spawn_owner` is alias-unsafe for fd 198 and initially closed standard
descriptors, and was covered only with fake descriptor APIs. Twelve fabricated
positive acquisition-ID sequences and sixteen aliases between distinct live
event/request/report inode identities also pass all three validators. The exact
additive review record SHA256 is
`7e0dcdefbe396ddd4cde41d8448ab9f4505a02597d7fe26a92a6d130f90765e7`.
Raw storage source remains untracked and unaccepted; compiler, root, native and
runtime lanes remain closed.

M01 correction 42 replaces attempt 41's nonexistent forwarding call with an
exact test-only default method on the real `ResponseMemory` trait, a call
immediately after the real Release store, and mode-local test overrides that
record only metadata. Its SHA256 is
`2532c398642863e9427f4d6b391f6ce247756eab69791bca678bdc2613448e16`.
Independent review 43 returns `PASS_PACKET` at SHA256
`a173b29370b77886b067693282bfc4b1a09f5c0dce626bd8d131c066d18655d8`,
releasing one future fresh source-only attempt under the complete inherited
packet. The closeout request arrived before that attempt was dispatched. No
implementation, compilation, execution or acceptance credit follows.

Next tasks after an explicit future launcher continuation are: (1) make one
bounded storage correction covering alias-safe real descriptor remapping, exact
producer acquisition sequencing and cross-role live inode ownership, then run
the focused and complete dual-Python validation and obtain fresh independent
source review; (2) only on terminal `PASS_SOURCE`, checkpoint the exact raw
storage source before drafting the separately reviewed conditional UID1000
compiler-only packet; (3) execute the one released fresh M01 source-stage
attempt under packet 29 plus corrections 31/34/36/39/42 and review 43, then
obtain independent complete handoff review before Phase II; (4) keep M03 closed
behind generation, descriptor-pin, authenticated-TLB-ack and
quarantine-ownership blockers. Counters remain 0/273 application cases, 2/4
narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7 language
gates. Whole-OS acceptance remains incomplete.

Shutdown closeout 41 follows fetched checkpoint
`b5fb9995402a840aa6be9efe2418968cd0edf4e2`. The launcher received SIGTERM
through its documented graceful-stop path after its watcher had restarted two
workers following terminal `blocked` results. The launcher-owned state now says
the goal is `paused`. Launcher PID 1676703, recovered worker PID 2293235 and
app-server PID 2293237 remain live only while this final bounded dispatcher turn
returns; the watcher must not restart them afterward. No child agent, project
build, container build, guest, QEMU, mcexec or IHK process is active, and no new
task was dispatched after the original work-window stop request. The heavy
lease remains free. This shutdown neither completes the OS goal nor authorizes
further work; a subsequent launcher invocation is the resume authority.

The next authorized continuation starts from the unchanged tasks in closeout
40: correct the three source-review-60 storage blockers and independently review
the complete source; checkpoint only a terminal `PASS_SOURCE` before drafting
the separately reviewed conditional compiler packet; execute the already
reviewed M01 source-only attempt and independently review its handoff before
Phase II; and keep M03 closed behind its listed ownership and acknowledgement
blockers. Counters remain 0/273 application cases, 2/4 narrow fault modes,
6/130 production gates, 350/10,000 points and 0/7 language gates. Whole-OS
acceptance remains incomplete.

Preparation checkpoint, 2026-09-27: the user requested aggressive dedicated-host
scheduling and separate subagent windows, then explicitly selected preparation
and testing only. The campaign remains stopped/paused; its launcher-owned state
and watcher bytes are unchanged. See HANDOFF.md and
LAUNCH-PREPARATION-20260927.md for the compact resume route and exact evidence.
The launcher now supports up to eight child agents, measured aggregate host
budgets, per-agent desktop viewers, and classified recovery that honors stops.
All 98 focused tests passed, including the installed CLI protocol schemas;
configuration, sudo, two container isolation probes and an actual synthetic
two-window desktop test passed. Existing scratch and transient controls were
restored; no campaign, OS fixture, kernel build or guest was started. Official
acceptance counters above are unchanged. The next normal launcher invocation
is the user's explicit resume action.

Stable-core engineering tracker, 2026-09-28: the user explicitly requested
comprehensive, granular progress toward a stable kernel core, separately from
slow-moving production qualification. Root STABLE-CORE.md is generated from
stable-core.json with 121 bounded substeps across 16 areas. Every item carries
a stable ID, scoped result, next check, dependencies and evidence; owner roles
and original task mappings are inherited from its area. Historical passing
behavior, implemented/partial work, known blockers and unmeasured coverage stay
distinct. Unknown coverage does not imply absent Rust code. The first proposed
claim is explicitly one McKernel CPU on the declared profile; host concurrency,
alias safety and all advertised capabilities remain required. Broader multicore,
language, application and production obligations are explicitly preserved.

The existing progress updater renders both reports. START/HANDOFF/CONVERGENCE
route future checkpoint reporting through the relevant rows without adding a
new execution or review loop. The pure reporting helper and dashboard integration
pass 46 unit tests; schema/reference/task/dependency checks, deterministic report
comparison and git diff --check pass. No kernel source, fixture, build, guest,
module, launcher or production acceptance input was changed or executed. Saved
state/watcher and original gate-map/tasks/final-push hashes remain unchanged;
the campaign remains stopped/paused. These tests validate reporting only, not
kernel stability. SC1 remains NOT YET DEMONSTRATED.

Independent coverage review corrected overbroad zero-after-reuse and integer-
register baseline implications, current Rust-consumer claims and fixture/core
classification. It added explicit integer-register and M01-D physical-guard/
live-polling checks, clarified the result-plumbing versus durable-ownership
sequence, and tightened application/pressure/load dependencies. Proposed core
repeat targets remain planning inputs for a separately reviewed run packet,
not new runtime results or changes to original qualification requirements.

Shutdown checkpoint, 2026-09-28: the resumed launcher received its explicit
shutdown request before Layer-B review or any compiler/runtime work. All listed
child agents are terminal. Launcher PID 3033800, worker PID 3033802 and app-server
PID 3033804, all started at 2026-09-28 00:21:07 -0700, remain the active launcher
process identities while this bounded closeout returns. No project build, guest,
QEMU, mcexec or IHK process is active; the heavy lease is free. The launcher run
directory is `.git/os-autopilot/runs/20260928T072108Z-7569fb1b`. Host/scratch
free space measured 44/21 GiB. Future continuations are paused by the launcher.

M01 attempt 44 stopped at `FAIL_PHASE_I` because its supplied mode-2 source path
was absent. The exact 11,962-byte, 15-member failure archive is
`docs/verification/evidence/stability-selected-retention-generic-row03-row12-phase-i-failure-20260928-44.tar.gz`
at SHA256 `de032f2e45e8defefdbdeafe04d469bdd9f544fd51fb00696a7c8b5d4d47b697`;
the raw failure SHA256 is
`f3cdf239225b053ac42d058a4abb0357216708fc5a019d3f7000aae1ed04181b`.
Independent restoration review returned `FAIL_RESTORE`: the suggested eight-file
copy included two mode-3 hashes and could not meet the exact 51-member mode-2
source contract. Preserve attempts 41 and 44. Next issue an additive independently
reviewed path correction naming the existing complete mode-2 authority tree,
reauthenticate all 51 members, and only then use a fresh attempt root.

M02 has a static-only unreviewed candidate for alias-safe real descriptor
remapping, inherited-descriptor closure, exact successful acquisition sequencing,
and live cross-role device/inode ownership, with focused regressions. M03 has a
static-only unreviewed independent C/Rust pending-free inventory candidate with
23 explicit selectors. Python AST parsing and `git diff --check` pass. No real
descriptor test, compiler, candidate binary, kernel, native or guest execution
was run. Exact hashes, evidence and next commands are bound by
`docs/verification/stability-source-candidates-shutdown-checkpoint-20260928-1.json`.

Next continuation tasks are: (1) draft an exact bounded Layer-B profile binding
the current M02 and M03 hashes, focused descriptor selectors, compiler argv and
all 23 pending-free selectors; (2) obtain independent `PASS_LAYER_B` before any
such execution; (3) on a pass, execute in a fresh disposable root and preserve
the first failure or complete output, then obtain independent source reviews;
(4) prepare and independently review the M01 complete-mode-2 path correction
before any fresh attempt. The source candidates are WIP only. Counters remain
0/273 application cases, 2/4 narrow fault modes, 6/130 production gates,
350/10,000 points and 0/7 language gates. Whole-OS acceptance remains incomplete,
and this shutdown neither completes nor resumes the goal.

Continuation shutdown checkpoint 2, 2026-09-28: correction45 fixes attempt44's
mode-2 source path by binding the existing exact 51-member authority rather than
constructing an eight-file substitute. Independent review46 returns `PASS_PACKET`.
The released source-only attempt45 then produces an exactly authenticated
327-regular-file Phase-I handoff: 51 source members per mode, canonical handoff
SHA256 `db97372717f50f7dd8b6eec67755b3b20fa58736da7d442e4393f27bb1eb3b0b`,
all 56 inherited pins and both authorities matching, and no bytecode, links or
cross-mode indirection. The exact 1,011,369-byte archive has 338 members and
SHA256 `e32fa7d1bacbbab76473612fcbcf28dad0052b90d4b283045d216ada19368b70`.

Independent review47 returns `FAIL_HANDOFF`, so Phase II remains closed. Both
modes have an incompatible fallible-Vec runner shim; row03 drains before mailbox
destruction transfers the backing; both rows omit required phase/owner/delta/
teardown assertions; geometry/address/send instrumentation is incomplete; and
row12 directly writes state rather than exercising the real phase transitions.
Correction42's unique metadata-only post-store hook is correct, but does not cure
those defects. Preserve attempt45 unchanged. Next prepare an independently
reviewed expert design packet covering all five findings before any fresh source
attempt; do not compile or enter Phase II.

The first reusable Layer-B profile and its bounded correction both failed source
review. An escalated expert candidate binds the retained archive/members,
persistent M03 evidence and session cleanup, but independent review 3 still
returns `FAIL_LAYER_B`: interruption can land between spawn and owned identity;
signalling uses stale numeric PIDs/PGIDs; repeated TERM can reenter and truncate
M03 lifecycle evidence; and a reap-timeout fallback waits without a bound. No
unprivileged test or compiler was released or run. This failure family now needs
a different process-ownership strategy: defer signals across spawn, use
identity-safe ownership/signalling, append immutable lifecycle records and
return explicit unresolved ownership after bounded reap. Obtain fresh independent
review before any command.

M02 nevertheless has static-only candidates for alias-safe fd remapping,
sequential acquisition IDs and cross-role live inode ownership. A read-only
audit now enumerates the complete 137-test dependency closure: ten direct inputs,
the retained root archive, seven historical source-review archives with exact
dynamically compiled members, and three failure records. M03 has persistent
per-command evidence support, real C/Rust constructors and the restored
misaligned-descriptor `-22` check. These are unexecuted WIP, not `PASS_SOURCE`.
After `PASS_LAYER_B`, run one exact focused M02/M03 admission, preserve its first
failure, then add the full-suite dependency manifest to a reviewed profile.

The stop request arrived before any executable Layer-B work. All child agents
are terminal. Launcher PID 3033800, worker PID 3033802 and app-server PID 3033804,
started at 2026-09-28 00:21:07 -0700, remain the active launcher identities while
this bounded closeout returns. No project build, guest, QEMU, mcexec, IHK,
compiler or heavy owner is active; host/scratch free space is 44/21 GiB. Exact
results and next tasks are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-2.json`.
Unrelated concurrent launcher-file edits and the pre-existing user-owned bytecode
deletion remain unstaged. Counters remain 0/273 application cases, 2/4 narrow
fault modes, 6/130 production gates, 350/10,000 points and 0/7 language gates.
Whole-OS acceptance remains incomplete; future continuations are paused until a
subsequent launcher invocation.

Continuation shutdown checkpoint 4, 2026-09-28: the changed Layer-B strategy
passed independent review as `PASS_DIRECT_OBJECT_PACKET`. Its exact packet SHA256
is `73ed242336988f5f66bb65db7fc81f85e742ff197552047f74b7ec9b3ac4f100`.
The dispatcher created the canonical mode-0700 root10 and completed only its
non-following include inventory and preflight. The shutdown request arrived
before unit-name allocation or the sole compiler submission. No transient unit,
cgroup identity, compiler, link, owner execution or payload exists. The exact
preflight-only root is retained in
`docs/verification/evidence/stability-layer-b-native-owner-bootstrap-preflight-20260928-10.tar.gz`,
SHA256 `719fee24d51a10fbe665ba855d610985ca08ac2c88a6d3033bb2e3cf5f3b1b64`,
size 1,654,349 bytes and nine archive members. Preserve the live scratch root.
Next continuation may resume at packet15's single compile-only submission only
after rechecking inputs, free space and the absence of a unit/cgroup; linking and
owner execution remain separately gated.

M01 packet57 independently returns `PASS_RECOVERY_PACKET`. It confirms the
attempt54 duplicated-VERSION diagnosis was false and releases one future
source-only root56 attempt after immediate reauthentication. Additive correction:
root54 did contain partial `runner.rs` scaffolding in both modes, so packet57's
“before candidate work” means after partial scaffolding but before a complete
candidate/handoff. Preserve root54 and its complete archive. Phase II and
compilation remain closed.

M03 independent review returns `FAIL_VALIDATED_INVENTORY_SOURCE` with two
remaining evidence gaps: exact null-descriptor/immediate-free list preservation,
and fieldwise lease/token/descriptor-array nonmutation during repeated rejection.
The product helper remains frozen at SHA256
`423547dbfa8a39070c8dd6c8ce5b56d67cfd082ba091e12431359ffde46cf985`;
production callers remain unwired. Next correct only those fixtures and obtain a
fresh independent source review. M02's full 137-test dependency closure is now
recorded at SHA256
`6e4ec66cd0a4e8ad74bd067338342f6bce7a1a6cc9bf02946f8819f2b2bdc03b`,
but no execution is released by that static manifest.

All eight child agents are terminal. Launcher PID 3052017, worker PID 3052019
and app-server PID 3052021 remain the active launcher identities while this
bounded closeout returns; the run directory is
`.git/os-autopilot/runs/20260928T080459Z-d717ac31`. No compiler, systemd compile
unit, guest, QEMU, mcexec or IHK process is active. Host/scratch free space is
44/21 GiB. Exact evidence and next tasks are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-4.json`.
Unrelated concurrent launcher-file edits, bytecode deletion and untracked
bytecode remain unstaged. Counters remain 0/273 application cases, 2/4 narrow
fault modes, 6/130 production gates, 350/10,000 points and 0/7 language gates.
Whole-OS acceptance remains incomplete; this checkpoint pauses rather than
completes or resumes the goal.

Continuation shutdown checkpoint 5, 2026-09-28: policy hashes remain the exact
adopted GOAL/START/CONVERGENCE/HANDOFF values. This continuation produced three
technical results and preserved every first failure without acceptance promotion.

Layer-B attempt10 submitted the one reviewed object-only command. GCC exited
successfully in 199,901 microseconds, but systemd 245 had already pruned the
terminal `ControlGroup`; the attempt is immutable `FAIL_IDENTITY`. Its generated
`.i/.s/.o/.d` remain uninspected and uncredited. Original cleanup retention
failed independent review because raw timing/search evidence was incomplete;
an additive exact present-state reconciliation independently established current
quiescence and released only the heavy lease. The retained archive is
`docs/verification/evidence/stability-layer-b-native-owner-bootstrap-failure-20260928-10.tar.gz`,
SHA256 `036e05c62f7993fc5787be794f74d38d40c79d97f391e48ac1c59cbede153eff`.

Packet18 plus correction19 then independently passed the fast-completion
execution review. Fresh root11 rebuilt 29,552 include entries with zero inventory
errors and captured exact start-pre unit/invocation/cgroup identity. The explicit
shutdown arrived while the 20-second barrier was active; by the next observation
the 60-second dispatcher deadline had elapsed. Because the marker was never
published, `/usr/bin/test` exited 1 and gcc never started. This is
`FAIL_BARRIER_TIMEOUT`, not a compiler failure. The 16.64-second cleanup ended
`not-found/inactive/dead` with both prebound cgroup paths absent; no artifact or
payload process exists. Preserve root11 and its 18-member archive
`docs/verification/evidence/stability-layer-b-native-owner-bootstrap-failure-20260928-11.tar.gz`,
SHA256 `07228da2a5b6827b0c260f080217ea358b7c8c45848505990f30b466fa080d26`.
Do not retry either root. Next change lifecycle strategy to a retained-owner
acknowledgement barrier that is not dependent on conversation/tool latency,
obtain independent review, and use a fresh root before any link or owner run.

M03 now has independent `PASS_VALIDATED_INVENTORY_SOURCE` on frozen product
SHA256 `423547dbfa8a39070c8dd6c8ce5b56d67cfd082ba091e12431359ffde46cf985`,
harness SHA256 `f53b0ddf9e9d05a9cfe6e24eb09758759f9dba3c759bf8312b9e368f3bc91032`,
Rust vectors SHA256
`3c8a5a0ba8305b061ada285c310998508c8fb7adb361d21bff7446d1e9b33a0a`
and C vectors SHA256
`5a2714a7855e958a4b61bdbe64a8aab12763335d6b063d786f58705a16da7a6f`.
This is source readiness only: production callers remain unwired and no compiler,
fixture or runtime command ran. After Layer-B owner execution passes, prepare and
independently review the exact M03 compile/test packet, then run actual helper and
C fallback controls before production integration.

M01 root56 contains a complete candidate and passed both 51-member reconstruction,
cfg erasure, authority, membership, archive and observer checks. Its final command
incorrectly applied repository-mode `git diff --check` to an external scratch
path and exited 128. Root56 remains `FAIL_PHASE_I_VALIDATION_COMMAND` with no
handoff, but independent source review found all ten candidate files coherent
against packet52/review53. Preserve its 338-member archive
`docs/verification/evidence/stability-selected-retention-generic-row03-row12-phase-i-failure-20260928-56.tar.gz`,
SHA256 `8eabf2eb29512ce628da616ffe587bfa5d75775be2e783e55418f67e91d3a59a`.
Next issue an additive independently reviewed fresh-root packet binding these
candidate hashes and a scratch-compatible whitespace validator, repeat static
authentication, create the canonical handoff and independently review it before
Phase II.

All child agents are terminal. Launcher PID 3052017, worker PID 3052019 and
app-server PID 3052021 remain the live launcher identities while this shutdown
returns; the run directory remains
`.git/os-autopilot/runs/20260928T080459Z-d717ac31`. No project compiler, transient
Layer-B unit/cgroup, guest, QEMU, mcexec or IHK process remains. Host/scratch free
space is 44/21 GiB. Unrelated launcher-file edits, bytecode deletion and
untracked bytecode remain unstaged. Counters remain 0/273 application cases,
2/4 narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7
language gates. Whole-OS acceptance remains incomplete; this checkpoint pauses
rather than completes or resumes the goal.

Continuation shutdown checkpoint 8, 2026-09-28: all bounded operations from
this invocation are terminal and no new work was dispatched after the stop
request. Root12 and root58 remain preserved as failed evidence attempts, with
independent additive reviews correcting the claims their original records do
not prove. The standalone Linux diagnostic collector remains source-approved
at SHA256 `c9932ce4883b1c23c4fc5df0cdb6b4cbe855c140d38787b6abf960f1d75ee409`;
all 18 focused process tests pass, but no diagnostic execution packet or guest
application has been released.

Next tasks, in order, are: (1) draft and independently review a fresh root13
Layer-B packet whose observer derives the actual `name=systemd` hierarchy from
mountinfo and `/proc/self/cgroup`, retains the original mapping and verifies cat
membership; (2) draft and independently review a fresh M01 trusted-driver packet
that directly retains validator argv, return code, streams, authentication,
installation identities and all five controls; (3) prepare and independently
review the startup.argv-empty Linux diagnostic packet using the retained payload
archive; and (4) bind M03 production VM epoch, descriptor generation/lifetime,
locking, invalidation acknowledgement and durable quarantine ownership before
any integration attempt. No root13, fresh M01 root, Linux diagnostic payload,
compiler, Layer-B service, guest or acceptance run may begin without its stated
review release.

Real guest applications executed in this work window: **0**. Launcher PID
3098066, worker PID 3098071 and app-server PID 3098074 remain the preserved
active process identities for run
`.git/os-autopilot/runs/20260928T095536Z-095509d1`. No project compiler,
transient Layer-B unit/cgroup, guest, QEMU, mcexec or IHK process is active.
Host/scratch free space is 44/21 GiB. Unrelated launcher/LAUNCH/START edits and
bytecode artifacts remain unstaged. Counters remain 0/273 applications, 2/4
narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7 language
gates. Whole-OS acceptance remains incomplete; this checkpoint does not mark it
complete or resume the launcher-paused continuation.

Continuation checkpoint 7, 2026-09-28: this resumed window produced executable
behavior and three independently reviewed technical outcomes without promoting
any formal acceptance counter.

Layer-B expert FIFO packet24, SHA256
`ebc8778cda8d667c40b26362e4540e68a7217b0e7110526d31b7d2bf1c7a13a5`,
passed `PASS_FIFO_EXECUTION_PACKET`. The dispatcher retained the exact strategy,
review release and rejected-review logs, then ran the sole fresh root12 attempt.
Systemd invocation `a9ba8caace454337b6ef600c695fa75b` held cat PID 3112143
in `activating/start-pre` with MainPID 0 and an unstarted main command. The
observer incorrectly joined ControlGroup below `/sys/fs/cgroup` instead of the
actual `name=systemd` hierarchy at `/sys/fs/cgroup/systemd`; 1,204 pre-ack
queries therefore lacked membership and the attempt failed closed at its
90-second acknowledgement deadline. No writer record, GCC stream or compiler
artifact exists. Stop succeeded and a later reset left the unit
`not-found/inactive/dead`. Independent present reconciliation proves the correct
original group and `/proc/3112143` absent and releases the heavy lease, while
rejecting overstatements in the original failure record. Preserve root12 and
archive SHA256 `82574a70f22300c92fc01b1a5caaab39c3540b85e780d4b6974d8007fa312056`.
Next issue and independently review one fresh root13 correction binding the
actual observer and an unambiguous mountinfo plus `name=systemd` mapper; do not
repeat root12 or start linking/owner work.

M01 expert packet62, SHA256
`63bf79fc38cabf0787030f1e770fd178edd599e5e1371bdbc3a6f9feee6261be`,
passed independent packet review and released one source-only root58 attempt.
Both stagers prepared 163 files per mode and all ten candidate hashes match
root56, but retained execution evidence failed its own contract: no literal
validator argv/return-code capture proves exit 0, the failure text has an
embedded newline and seven lines, authentication/install/control evidence is
incomplete, and two extra stream files violate the diagnostic allowlist. No
handoff, Phase II or compiler artifact exists. Preserve root58/diagnostics62 and
archive SHA256 `88b7d69c828ecf2ed399ed609c2b91563877068c7e11f5b380158f2f53ec487a`.
Next use a separately reviewed fresh-root trusted driver that directly retains
argv/status/streams, five controls, authentication and exact membership.

The new standalone Linux diagnostic collector now passes independent
`PASS_SOURCE` at source SHA256
`c9932ce4883b1c23c4fc5df0cdb6b4cbe855c140d38787b6abf960f1d75ee409`
and test SHA256
`ac76db0114d12d737e5e60f4929ce029bb7a889532502801105d18abef52c39c`.
All 18 process tests pass, including actual exit 7, SIGTERM, timeout, truncation,
stdin and empty argv; 42 adversarial report mutations reject. The collector is
controlled-filesystem Linux diagnostic infrastructure only: it does not pin
pathname execution, prove build/interpreter/DSO closure, enable `run.py`, run a
guest or earn M02/M04 credit. Next prepare and independently review a packet that
restores the retained `startup.argv-empty` payload from Git blob `c9d87b...`,
binds its provenance/oracle/ownership and executes one fresh Linux diagnostic.

M03 audit confirms the frozen source prototype prevalidates the full descriptor
inventory and snapshots callback arguments before any allocator call, preventing
valid-prefix release on a later invalid node. Production still uses incremental
raw-list release in `kernel/mem.c`, and XPMEM shares that begin/finish mechanism.
Integration remains blocked on explicit VM epoch, descriptor-generation/lifetime,
lock/IRQ/reentry, clear/TLB acknowledgement and durable quarantine ownership;
Layer-B execution cannot substitute for those bindings.

Real guest applications executed in this work window: **0**. The exact blocking
dependency remains a reviewed current-candidate guest backend/input manifest;
the newly accepted Linux collector is only its paired-control prerequisite.
Launcher PID 3098066, worker PID 3098071 and app-server PID 3098074 remain live.
No compiler, Layer-B unit/cgroup, guest, QEMU, mcexec or IHK process is active;
host/scratch free space remains 44/21 GiB. Unrelated launcher/LAUNCH/START edits
and bytecode artifacts remain unstaged. Counters remain 0/273 applications, 2/4
narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7 language
gates. Whole-OS acceptance remains incomplete and the goal stays active.

Continuation shutdown checkpoint 3, 2026-09-28: the replacement Layer-B
strategy is now a native single-threaded pidfd/subreaper owner rather than the
rejected Python PGID family. Exact source SHA256
`2c157335e88b2088c56fc40fd6c0d966dc653ea68b4726e51feb1d4b4e62eafc`
and source-model SHA256
`427f6133497ce0706fce39d9e52051542821bc6deab29d27322733c927efd63d`
pass 17 static tests and independent `PASS_SOURCE`. This covers interpreted
seccomp branches, spawn gating, pidfd-only direct signalling, durable terminal
status before reap, direct/adopted deduplication and retained unresolved
supervision. It is source evidence only.

The separately reviewed compile-only bootstrap remains closed. Packet 8 failed
six findings; additive correction 9 fixed the environment, working directory,
macro conflict, static ELF inspection and kill syntax, but independent review 9
still returns `FAIL_BOOTSTRAP_PACKET`: both exact GCC commands omit `-v`, normal
retained units lack immediate stop, timeout cleanup lacks its own bounded budget
and SIGKILL fallback, and the dependency manifest conflates persistent inputs
with deleted GCC temporaries. No compiler, systemd transient unit, owner or
payload was run. This bootstrap family has used its bounded correction; change
strategy and independently review a new packet before compilation.

M01 expert attempt48 produced an exact 327-regular-file source handoff and the
1,011,877-byte archive
`docs/verification/evidence/stability-selected-retention-generic-row03-row12-phase-i-attempt-20260928-48.tar.gz`
at SHA256
`6bb534ea6893e113e136a890660ccebe9f1b122d10f84546c2e1fbffb92d6cd8`.
Independent review51 returns `FAIL_HANDOFF`: generic derived Default prevents
the required `mem::take`, observer counters are fabricated, deallocation is
recorded before Box destruction, and the assertion matrix remains incomplete.
Preserve root48 and its archive. Escalated packet52, SHA256
`846605e3c35c48e65ff892ae65ec67182eee1c5e38a43f3d5e83e651aa968568`,
passes independent `PASS_PACKET` and releases exactly one future source-only
attempt at absent root52 after reauthentication. Shutdown arrived before that
attempt; Phase II, compilation and runtime remain closed.

The M03 production mapping records a critical mismatch between the finite
23-selector model and production: current finish can release earlier valid
nodes before a later invalid node returns EINVAL. The next production step is a
reviewed prevalidation boundary that freezes the actual ABI list into exclusive
retained ownership before any allocator callback, followed separately by the
generation/quarantine/VA-exclusion/invalidation transaction owner. No production
behavior is accepted from this mapping.

The stop request arrived before any newly released source attempt or executable
work. All child agents are terminal. Launcher PID 3052017, worker PID 3052019
and app-server PID 3052021, started at 2026-09-28 01:04:58 -0700, remain the
active launcher identities while this closeout returns. No project build,
guest, QEMU, mcexec, IHK, compiler or heavy owner is active; host/scratch free
space is 44/21 GiB. The active launcher run directory is
`.git/os-autopilot/runs/20260928T080459Z-d717ac31`. Next tasks are: (1) change and independently review the
Layer-B bootstrap strategy before any compilation; (2) reauthenticate and run
the single packet52 source-only root52 attempt, then independently review its
handoff; (3) design/review M03 production prevalidation before integration.
Exact results are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-3.json`.
Unrelated concurrent launcher-file edits and the pre-existing user-owned
bytecode deletion remain unstaged. Counters remain 0/273 application cases,
2/4 narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7
language gates. Whole-OS acceptance remains incomplete; future continuations
are paused until a subsequent launcher invocation.

Continuation shutdown checkpoint 6, 2026-09-28: all newly dispatched bounded
lanes reached terminal state before shutdown. The FIFO acknowledgement strategy
passed strategy review, and its exact draft packet is
`docs/verification/stability-layer-b-native-owner-fifo-ack-packet-20260928-21.md`,
SHA256 `4d2931e733c88a7d81de543d5b8b574bfc88a82051524107cad96ecc0136d9d1`.
It remains `DRAFT_PENDING_INDEPENDENT_REVIEW`; no FIFO, systemd unit, compiler,
object, link or owner execution was started. Next independently review those
exact bytes, then only on PASS remeasure capacity and run one fresh root12
compile-only attempt under its acknowledgement and cleanup contract.

M01 validator-recovery packet60, SHA256
`4dc69511c0725e9045b6cee38035622118edec363d5fc39a42065638b8a9d126`,
returns `FAIL_VALIDATOR_RECOVERY_PACKET`. Its six blocking families are the
incorrect root56 JSON digest binding, opening the `--` argv separator, ineffective
trailing-whitespace controls, the impossible 327-file pre-handoff count,
incomplete immutable review hashes, and underspecified candidate installation /
per-mode isolation. Root58 was not created. Next make one bounded additive
correction covering all six findings and independently review it; Phase II,
compilation and runtime remain closed.

The exact application fast-path audit confirms packet-001's reviewed
`startup.argv-empty` source and oracle, but `run.py` has no execution backend,
the packet retains only a manifest placeholder, and no compiled payload or
current-candidate module/image binding exists. The historical QEMU helper is not
a packet backend. Next prepare and independently review the smallest concrete
backend/input-manifest packet with a fresh payload and current candidate bindings.
No application was executed and this diagnostic finding is not M04 acceptance.

Launcher PID 3098066, worker PID 3098071 and app-server PID 3098074, started at
2026-09-28 02:55:35 -0700, remain the live launcher identities while this
shutdown returns. The run directory is
`.git/os-autopilot/runs/20260928T095536Z-095509d1`. All child agents are terminal;
no project compiler, transient Layer-B unit/cgroup, guest, QEMU, mcexec or IHK
process is active. Host/scratch free space is 44/21 GiB. Exact results and next
tasks are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-6.json`.
Unrelated concurrent launcher-file edits, the LAUNCH/START overlays, bytecode
deletion and untracked bytecode remain unstaged. Counters remain 0/273 application
cases, 2/4 narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7
language gates. Whole-OS acceptance remains incomplete; this checkpoint pauses
rather than completes or resumes the goal.

Continuation shutdown checkpoint 9, 2026-09-28: checkpoint 8 above is the
authoritative result of this invocation. All bounded operations and child agents
are terminal, and no new task was dispatched after shutdown. The next executable
work remains the separately reviewed root13 cgroup-mapping correction, fresh M01
trusted-driver correction, startup.argv-empty Linux diagnostic packet, and M03
production-authority binding described in checkpoint 8. Preserve launcher PID
3098066, worker PID 3098071, app-server PID 3098074 and run directory
`.git/os-autopilot/runs/20260928T095536Z-095509d1` as the active process
identities. No project compiler, Layer-B service/cgroup, guest, QEMU, mcexec or
IHK process is active. Real guest applications executed in this window: **0**.
Whole-OS acceptance remains incomplete; the launcher-paused continuation is not
resumed or marked complete by this checkpoint.

Continuation shutdown checkpoint 10, 2026-09-28: this authorized continuation
adopted the exact policy hashes GOAL `76c4f5d...`, START `30a90c7...`,
CONVERGENCE `d211e7d...` and HANDOFF `265cd99...`, reconciled live state at
checkpoint `b9442601`, then stopped new dispatch immediately on the launcher
signal. All bounded children are terminal. No compiler, systemd unit, guest,
QEMU, mcexec or IHK runtime was started.

Two source candidates produced executable unit-test evidence but failed
independent review. The root13 cgroup observer at SHA256
`0b8f7a8dbf0966859c30423528679ab0d4baadac7c3653c4944d51eed2e02ea0`
passes six supplied tests, yet retained root12 mountinfo proves that it rejects
unrelated nsfs roots, incorrectly requires the observer inside the target unit,
maps non-root mount coordinates incorrectly, normalizes cgroup pathname bytes
and misses covering mounts. The M01 trusted driver at SHA256
`3ac88932f9fcdb1dcf01be8e1e3d3d9969cad984ff002b8a4d8306ee508b3a89`
passes four supplied tests, yet seven adversarial probes show fabricated control
results, unauthenticated arbitrary exit-zero success, legitimate-directory
rejection, root/output symlink races, lost first-failure evidence and multiline
failure-field injection. Neither source grants execution release; preserve both
failed byte sets and additive reviews 27/64.

M03 production review returns `FAIL_DESIGN_READY`: the valid-prefix partial
release is real, but safe integration first needs a capture owner and generation,
descriptor leases, allocator-extent authority, explicit VM/CPU context and
defined IRQ/nesting/reentry/migration behavior. The frozen helper needs an
adapter, not direct wiring. Full failed-invalidation acceptance still needs VM
epoch/lifetime, retained range/backing owners, VA exclusion, authenticated
clear/TLB/alias acknowledgement and durable quarantine.

The application-pilot audit recovered live retained identities for all three
modules, Linux bzImage/initramfs, McKernel image, mcexec and the compiled
startup.argv-empty payload; exact hashes are in
`stability-application-pilot-artifact-audit-20260928-1.json`. `run.py` remains
metadata-only and no reviewed guest backend/release exists. A draft Linux-only
diagnostic packet now binds the correct archive Git blob
`c9d87b95901c1581057a5ee86b1e5ab6196d3edc`, but remains unreleased because the
retained interpreter/libc closure differs from the current host and independent
review is still required.

Next tasks are: (1) make and independently review the one bounded root13 observer
correction before any packet or unit; (2) make and independently review the one
bounded M01 trusted-driver correction before any fresh root; (3) resolve a
controlled matching Linux DSO closure and review the diagnostic packet; (4)
freeze the M03 production authority contract before implementation; and (5)
prepare/review the exact guest backend/input manifest before implementing its
native terminal observer. Real guest applications executed in this window:
**0**. Launcher PID 3098066, worker PID 3098071 and app-server PID 3098074 remain
the preserved process identities for
`.git/os-autopilot/runs/20260928T095536Z-095509d1`. Host/scratch free space is
44/21 GiB and the heavy lease is released. Counters remain 0/273 applications,
2/4 narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7
language gates. Whole-OS acceptance remains incomplete; this checkpoint does not
resume or complete the launcher-paused goal.

Continuation shutdown checkpoint 11, 2026-09-28: the fast diagnostic
continuation produced one accepted parser repair and one source-reviewed kernel
error-propagation change, but no compile, root unit or guest was released. The
root13 cgroup observer at source SHA256 `2f187550...` and test SHA256
`ce6ebd78...` passes 26 tests plus independent adversarial review. Its exact
packet 28, SHA256 `7db94664...`, remains unreviewed and cannot run.

The native/Rust `do_munmap` path now returns the exact `clear_host_pte` failure
after a successful remove, with the whitebox copy updated. Independent source
review returns `PASS_SOURCE_READY_FOR_BUILD`; no build packet covers these exact
bytes yet. Draft packet 1, SHA256 `b0a44156...`, is still blocked on a reviewed
focused host-clear selector. This change does not solve durable page ownership,
quarantine, VM epochs or invalidation acknowledgement and is not M03 acceptance.
The pinned Linux startup.argv-empty diagnostic packet, SHA256 `ca308127...`, is
also draft-only pending independent review and same-image closure preflight.

Both escalated repairs were stopped at safe boundaries. M01 left an unreviewed
partial manifest-bound driver at SHA256 `9c64dc7...`; its old four-test file is
not synchronized (two pass, two error), so it has no execution release. The
native diagnostic expert was interrupted during replacement; the prior exact
independently failed candidate was restored from its retained agent log at
SHA256 `fc17200b...`, and its eight isolated tests pass. Its known missing real
guest transport, deadline, reap and durable failure-publication requirements
remain open. No QEMU or guest was started.

All child agents are terminal. Launcher PID 3125264, worker PID 3125267 and
app-server PID 3125269, started at 2026-09-28 03:47:42 -0700, remain the
preserved process identities for
`.git/os-autopilot/runs/20260928T104742Z-d8634f08`; that run has no `state.json`.
No project compiler, transient Layer-B unit/cgroup, guest, QEMU, mcexec or IHK
runtime is active. Host/scratch free space is 44/21 GiB and the heavy lease is
free. Real guest applications executed in this window: **0**.

Next tasks are: (1) independently review packet 28 and only on PASS run one
fresh root13 attempt; (2) finish and independently review the interrupted M01
driver/tests; (3) review and preflight the Linux diagnostic packet; (4) resolve
the VM packet's focused-selector blocker, review it, then compile/equivalence
test the propagation change; (5) repair and review the actual native guest
diagnostic transport before QEMU; and (6) continue the separate M03 durable
ownership/quarantine design. Exact results are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-11.json`.
Counters remain 0/273 applications, 2/4 narrow fault modes, 6/130 production
gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance remains
incomplete; this checkpoint neither resumes nor completes the paused goal.

Checkpoint publication note: the whitebox mirror is preserved in the nested
repository on local branch `codex/vm-clear-error-propagation-20260928` at commit
`21a0d1e`. Its HTTPS remote rejected noninteractive authentication, so that
nested commit is not pushed and the outer submodule pointer is intentionally
unstaged. The outer checkpoint excludes that pointer rather than publishing an
unfetchable nested object; the exact source SHA256 remains recorded above.

Continuation shutdown checkpoint 12, 2026-09-28: the pinned-container actual-
body test and independent review accept one narrowly scoped production repair.
The current Rust pending-free finish path now validates the complete ring before
any unlink or allocator callback. All 37 Rust/C snapshots and 15 trait-negative
controls pass; a preflight-removal mutant reproduces valid-prefix release. This
does not supply VM/token/extent authority, IRQ/reentry/migration exclusion, the
C fallback repair, guest runtime evidence or full M03 acceptance.

All other lanes are preserved without promotion. The SC-VM-01 harness failed its
bounded-correction review on fixture completeness, callback oracles, executable
mutants, packet bindings and durable evidence. The M01 driver failed source
review because cleanup can mask first failures and leak a Journal descriptor.
The native diagnostic failed review on teardown ordering, route completeness,
QMP cleanup isolation and unbounded failure journaling. The M02 real descriptor
candidate passes five fork/dup/exec and identity tests but still needs independent
review. The root13 collector and Linux diagnostic owner experts were interrupted
at source-edit boundaries on shutdown; their exact partial bytes are WIP and do
not release root, systemd, Docker, compiler or guest execution.

All children are terminal or interrupted. Launcher PID 3125264, worker PID
3125267 and app-server PID 3125269, started at 2026-09-28 03:47:42 -0700, remain
the preserved process identities for
`.git/os-autopilot/runs/20260928T104742Z-d8634f08`. No project compiler, guest,
QEMU, mcexec, native-boot or IHK runtime is active; host/scratch free space is
43/21 GiB and the heavy lease is free. Real guest applications executed in this
window: **0**.

Next tasks are: (1) independently review M02; (2) finish and review the root13
collector and Linux diagnostic owner corrections; (3) repair and review M01's
cleanup boundaries; (4) replace and review the SC-VM-01 harness before compile;
(5) repair the native diagnostic lifecycle; and (6) execute the matching C
pending-free preflight before continuing durable ownership design. Exact hashes,
review blockers and evidence are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-12.json`.
Counters remain 0/273 applications, 2/4 narrow fault modes, 6/130 production
gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance remains
incomplete; this checkpoint pauses rather than resumes or completes the goal.

Continuation shutdown checkpoint 15, 2026-09-28: the Python 3.9-safe backend
and joined runner/lifecycle are preserved at their exact source identities. The
final combined six-module suite passes 164 tests after a test-only correction
made the ambient `qmp_capture` oracle restore its exact prior state for both
initially absent and preloaded cases. Independent review returns
`PASS_RUNNER_SOURCE_READY_FOR_PACKET`; publication remains bounded best effort
and this is source/host-protocol readiness, not execution authority. The
pre-correction combined failure and earlier hostile-formatting failures remain
preserved as original evidence.

The current-signal overlay source passes 36 tests and independent source review.
Retained attempt 3 derives initramfs SHA256 `40d4924c...`; strict independent
replay accepts 61 final members and the exact current ihk-smp `5bdcd1b4...`,
McKernel image `5f370ee9...`, collector and payload bytes. Manifest 2 is retained
at SHA256 `c7072eea...`. Failed attempt 2 remains intact with its old-base
identity rejection. Attempt 3 has no saved command script, so its byte result is
accepted only for manifest integration. The only usable QEMU is container-local
QEMU 10.1.0, SHA256 `5c198504...`, in pinned image `46d47ba9...`; direct host
execution remains forbidden.

All child agents are terminal or interrupted. Launcher PID 3125264, recovered
worker PID 3170135 and app-server PID 3170137 remain alive for
`.git/os-autopilot/runs/20260928T120120Z-056cff0a`. No project compiler, guest,
QEMU, mcexec, native-boot or IHK runtime is active. Host/scratch free space is
43/21 GiB, memory available is 28.8 GiB and the heavy lease is free. Real guest
applications and current-candidate kernel builds in this window are **0** and
**0**; one current diagnostic initramfs was derived.

Next tasks are: (1) revalidate manifest 2 against the final checkpointed source;
(2) prepare a container-only execution packet binding every source/artifact,
QEMU, resource, deadline, evidence and cleanup identity; (3) obtain independent
execution review; (4) only after that release, run one current-signal diagnostic
guest and preserve application bytes, exit, kernel log, serial, QMP, container
status and teardown; and (5) repair any observer/evidence defect locally before
another privileged attempt. Exact identities and original failures are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-15.json`.
Counters remain 0/273 applications, 2/4 narrow fault modes, 6/130 production
gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance remains
incomplete; this checkpoint pauses rather than resumes or completes the goal.

Continuation shutdown checkpoint 14, 2026-09-28: four diagnostic prerequisites
are accepted at their bounded scopes. The independently reviewed PID1 collector
source passes 15 tests and its host-static artifact is an x86-64 ET_EXEC with no
interpreter or dynamic section. The authenticated overlay derives exact
initramfs SHA256 `f2e9f8ad...`; strict replay validates 62 final members and the
exact collector/application bytes. The retained host closure preflight exits 0
with the exact 91-byte oracle and a quiescent process group. These are source,
byte-artifact and host-diagnostic results only; no McKernel guest ran.

The joined native diagnostic candidate is preserved but rejected for execution.
Its 43 tests and strict 62-member derived-image join pass, but independent review
found two concrete error-path blockers: backend `BaseException.add_note` calls
are unavailable on the actual Python 3.9.12 host and can replace the first error
or skip descriptor cleanup; authenticated staging `OSError` failures can escape
without a terminal record or first-failure journal. No execution packet was
prepared and no QEMU process was started.

All child agents are terminal. Launcher PID 3125264 remains alive; worker PID
3125267 and app-server PID 3125269 are preserved identities but were no longer
present at the final process check. Their run directory is
`.git/os-autopilot/runs/20260928T104742Z-d8634f08`. No project compiler, guest,
QEMU, mcexec, native-boot or IHK runtime is active. Host/scratch free space is
43/21 GiB, memory available is 28.9 GiB and the heavy lease is free. Real guest
applications and current-candidate builds in this window: **0** and **1**; the
one build is the collector artifact, not a kernel image.

Next tasks are: (1) implement and independently review the Python 3.9-compatible
backend cleanup-error recorder; (2) journal and fail closed on staging I/O
errors, then independently re-review integration; (3) after both pass, prepare
and independently review an exact execution packet; (4) only after release, run
one startup.argv-empty diagnostic guest and retain application bytes, exit,
kernel log, QMP/serial and teardown; and (5) continue deferred M03 durable
ownership work without promoting diagnostic evidence. Exact hashes, evidence
and blockers are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-14.json`.
Counters remain 0/273 applications, 2/4 narrow fault modes, 6/130 production
gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance remains
incomplete; this checkpoint pauses rather than resumes or completes the goal.

Continuation shutdown checkpoint 13, 2026-09-28: three bounded results are now
accepted at their stated scopes. The C pending-free result and public fallback
prevalidate the complete ring before mutation; 48 candidate rows pass and two
guard-removal mutants reproduce valid-prefix release in the reviewed pinned
container. Independent review returns `PASS_SCOPED_C_PENDING_PREFLIGHT_EXECUTION`.
The M02 descriptor component returns `PASS_SOURCE_READY_FOR_LAYER_B_REVIEW`
after five focused tests exercise 48 real fork/exec permutations. The native
diagnostic lifecycle returns `PASS_PROTOCOL_SOURCE_BLOCKED_RUNTIME`; 23 tests
cover teardown-before-final-capture, complete route joins and bounded evidence
publication. None of these results is a guest, ABI, concurrency, VM ownership,
privileged Layer-B or production acceptance result.

The native application fast path remains blocked before compilation. The final
collector correction is preserved at source SHA256 `59eaaf71...` and test SHA256
`3dc4eaea...`; four source tests pass, but its worker reports incomplete checked
pipe/error channels, fair drain, process-group teardown and atomic serial-frame
publication, so it is unreviewed and unreleased. The replacement append-only
initramfs overlay was interrupted at SHA256 `170857d8...` / `ea6104b3...` and is
also unreviewed. The older full-tree stager remains rejected for path races,
weak identity/closure binding, nondeterministic metadata, absent real newc replay
and incomplete durability. No retained root was modified and no derived image,
collector binary, QEMU process or McKernel guest was started.

Root13 packet 28 remains source-ready, but its executor is rejected and must not
run. The combined pending-free owner is likewise rejected because its command,
diagnostic, mutant and exact-C evidence contracts do not match the harness. M01,
SC-VM-01 and the Linux diagnostic owner retain their prior deterministic failure
families; subsequent work must change strategy rather than replay unchanged
candidates. All child agents are terminal or interrupted. Launcher PID 3125264,
worker PID 3125267 and app-server PID 3125269, started at 2026-09-28 03:47:42
-0700, remain the preserved identities for
`.git/os-autopilot/runs/20260928T104742Z-d8634f08`. No project compiler, guest,
QEMU, mcexec, native-boot, IHK runtime, root unit or transient container is
active. Host/scratch free space is 43/21 GiB, memory available is 28 GiB and the
heavy lease is free. Real guest applications and current-candidate builds in
this window: **0** and **0**.

Next tasks are: (1) finish and independently review the append-only overlay;
(2) finish and independently review the collector lifecycle; (3) only after both
releases, compile the collector in the pinned container and derive an exact
authenticated initramfs; (4) implement/review the concrete process/QMP backend
and serial collector before one startup.argv-empty diagnostic guest; (5) keep
the rejected root13, M01, SC-VM-01, Linux-owner and combined-owner executors
stopped until their failure families receive changed strategies; and (6)
continue M03 VM/token/extent authority and durable-quarantine work. Exact hashes,
scope limits and blockers are recorded in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-13.json`.
Counters remain 0/273 applications, 2/4 narrow fault modes, 6/130 production
gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance remains
incomplete; this checkpoint pauses rather than resumes or completes the goal.

Latest continuation cursor: shutdown checkpoint 15 supersedes checkpoints 13
and 14 for the native diagnostic lane. Its exact source/artifact identities,
preserved failures, live launcher process identities and next tasks are recorded
above and in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-15.json`.
No execution packet was released and no guest ran. Resume by revalidating the
retained current-signal manifest against the checkpointed source, then prepare
and independently review the exact container-only execution packet. Whole-OS
acceptance remains incomplete and the launcher pause remains in force.

Continuation checkpoint 16, 2026-09-28: the current C and Rust pending-free
finish paths now reject unaligned and pairwise-overlapping physical extents
before any unlink, mode change or allocator callback. The ABI and existing Rust
consumers are unchanged. The host combined suite passes 37 paired rows,
production controls, 15 trait negatives, the original partial-release mutant
and four effective geometry mutants. A first independent review correctly found
that the older standalone C recovery fixture itself contained overlapping
extents; the corrected fixture preserves that failure, uses three adjacent valid
extents, and adds explicit second/last overlap rejection and recovery.

The exact corrected standalone C harness then passed in pinned container
`528455e4...`: 58 candidate rows and two guard-removal mutant rows, exit 0,
OOM false, followed by verified container removal and absence. Result SHA256 is
`addbc60b...`. Independent review returns
`PASS_SOURCE_READY_FOR_NEXT_BUILD_PHYSICAL_EXTENT_PREFLIGHT_ONLY`. This proves a
scoped geometry safety improvement under live, stable, exclusively owned
descriptors. It does not prove pointer lifetime, concurrency/reentry safety,
generation/epoch authority, invalidation acknowledgement, retained backing,
quarantine, a kernel build, guest behavior, M03 closure or production acceptance.

Next for this lane is a current-candidate build followed by explicit owner/token
and descriptor-generation propagation through syscall and both XPMEM paths,
preallocated frozen inventory, invalidation acknowledgement and durable
quarantine. Exact source, commands, container identity, evidence hashes and
limitations are in
`docs/verification/stability-pending-free-extent-admission-success-20260928-1.json`.
The independent current-signal diagnostic lane remains active in parallel; no
real guest application has run in this continuation. Official counters remain
0/273 applications, 2/4 narrow fault modes, 6/130 production gates, 350/10,000
points and 0/7 language gates. Whole-OS acceptance remains incomplete.

Continuation shutdown checkpoint 17, 2026-09-28: manifest 2 received a final
exact artifact/source reconciliation PASS. Its 17 references, current signal
module and image, collector, payload, derived initramfs `40d4924c...` and exact
91-byte application oracle match; this is still integration evidence only and
no guest ran. The independently reviewed pending-free physical-extent admission
was committed and remotely verified at `d6f5cf06`; its scoped pinned C execution
is the sole new executable production-body result in this continuation.

The new outer container owner remains deliberately blocked and is preserved as
a failing WIP candidate. Independent review rejected predecessor `83e1fd99...`
because a fatal signal could escape during `Popen` acquisition and a delayed
Docker create could publish after point-in-time absence. Candidate `c0a4b14a...`
now owns spawn pipes/PID under blocked cancellation, tracks reap, and applies a
repeated two-second exact-absence window; its delayed-create regression passes.
The exact host suite nevertheless runs 55 tests with 52 passes and three errors:
Anaconda Python 3.9 rejects `posix_spawn(setsid=True)`. Syntax compilation passes.
This candidate has no source PASS and no execution authority. The raw failure is
retained under `/home/holden/mckernel-work/scratch/native-diagnostic-container-owner-source-20260928-1`.

All child agents are terminal. Launcher PID 3125264, recovered worker PID
3170135 and app-server PID 3170137 remain alive for
`.git/os-autopilot/runs/20260928T120120Z-056cff0a`. No project compiler, guest,
QEMU, mcexec, native-boot or IHK runtime is active. Host/scratch free space is
43/21 GiB, available memory is 30,064,536 KiB and the heavy lease is free. A
read-only unprivileged Docker inventory query was denied, so shutdown did not
infer the two long-lived containerd shim identities were project containers.

Next tasks are: (1) replace unsupported `setsid=True` with a reviewed supported
process-group mechanism such as `setpgroup=0`, rerun all 55 cheap tests and get
independent source review; (2) bind the exact corrected owner and all committed
diagnostic inputs into an execution packet; (3) obtain independent execution
release; (4) only then run one current-signal diagnostic guest and preserve
application bytes, exit, kernel log, QMP/serial, Docker state and teardown; and
(5) after preserving that signal, build the current pending-free candidate and
continue explicit owner/token/generation, invalidation-acknowledgement and
durable-quarantine work. Exact identities and limitations are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-17.json`.
Official counters remain 0/273 applications, 2/4 narrow fault modes, 6/130
production gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance
remains incomplete; this checkpoint pauses rather than resumes or completes it.

Latest continuation cursor: shutdown checkpoint 17 supersedes checkpoint 15 for
the current-signal diagnostic lane and includes checkpoint 16's scoped M03
result. Resume from the supported process-group correction above. No execution
packet is released and no guest has run. Whole-OS acceptance remains incomplete
and the launcher pause remains in force.

Continuation checkpoint 18, 2026-09-28: the exact outer container owner is now
source-ready for an execution packet. The host-supported `setpgroup=0` path
creates a child-led process group while parent cancellation is blocked; exact
reap state prevents stale-PGID signaling. A persistent child ledger retains any
unreaped Docker client, and an issued create stays unresolved through any finite
empty lookup sequence until its exact successful response or authenticated
name/label/container observation. Cleanup no longer publishes tentative absence.

The coordinator independently reproduced 62/62 tests under host Python 3.9;
raw stderr SHA256 is `77addb5c...`. Independent ownership review returns
`PASS_SOURCE_READY_FOR_EXACT_EXECUTION_PACKET` for owner `91a9c035...` and tests
`ada330f0...`. The preserved history includes the Popen acquisition/stale-PGID
failure, unsupported `setsid=True` failure, finite quiet-window/premature-absence
failure and one corrected mock-interface expectation. An unresolved daemon create
intentionally retains the owner and development lock indefinitely. This is
source/local-process evidence only: no root, Docker, QEMU or McKernel command ran.

Next bind the exact owner and current-signal source/artifact identities into one
execution packet and obtain a separate independent execution release. Only then
create a fresh attempt and run one diagnostic guest. Exact evidence and limits
are in
`docs/verification/stability-native-diagnostic-container-owner-source-success-20260928-1.json`.
Official counters remain unchanged; whole-OS acceptance remains incomplete.

Continuation checkpoint 19, 2026-09-28: the first exact one-shot packet was
rejected before execution. Its QMP pathname was 128 bytes, beyond Linux's 107
usable pathname bytes. It also required process/cgroup identities that the then
current runtime did not persist and incorrectly described the outer post-cleanup
write/fsync as bounded. No root, Docker, QEMU or guest command ran; rejected
packet SHA256 `82e52a97...` and all findings are preserved.

The evidence gap is now implemented. Before ownership transfer the backend
captures positive QEMU PID, PGID, session and robust `/proc` starttime and keeps
those primitives through exact reap; evaluation rejects missing or mismatched
identity. The outer owner queues its own identity, root-lock device/inode/mode/
owner identity and exact cgroup profile without disk I/O while ownership is
live. The owner binds the changed diagnostic/backend bytes. After one preserved
observer-command typo, the corrected six-module suite passes 211/211 tests.
Independent review returns `PASS_IDENTITY_SOURCE_READY_FOR_PACKET_CORRECTION`
for diagnostic `0ab36565...`, backend `ffdde018...` and owner `4ed6f849...`.

Next use a shorter fresh parent, prove `qmp.sock` is at most 107 bytes, update
the packet's exact source identities and explicitly state that only inner
capture/publication is bounded while the safe post-retirement outer flush can
block. Then obtain a fresh independent execution release. Evidence is in
`docs/verification/stability-native-diagnostic-identity-source-success-20260928-1.json`
and the rejected review record. Official counters remain unchanged; no real
guest application or current kernel build has run in this continuation.

Continuation checkpoint 20, 2026-09-28: the corrected current-signal packet
now has `PASS_EXACT_ONE_SHOT_EXECUTION_RELEASE`. It is bound to pushed commit
`c059d839...`, packet SHA256 `fec6266a...`, short fresh parent
`/home/holden/mckernel-work/scratch/ndcs-20260928-1` and nonce
`6ea6a57520d94590b709b46dc011167c`. The exact QMP pathname is 100 bytes, both
parent and evidence paths are absent, and the review rejoined all six runtime
sources, manifest/artifact/image/QEMU identities, the 91-byte oracle, resource
profile, deadlines, process evidence and fail-closed cleanup.

This releases exactly one root-outer, UID1000-container diagnostic under CPUs
2-5, 12 GiB/no additional swap, 512 tasks and no network. An unresolved create
or client retains the owner and development lock indefinitely; it must not be
killed or retried. The outer post-retirement evidence flush is intentionally
unbounded and is not a live container/QEMU lease. Next remeasure capacity and
leases, create the exact parent once, run only the released command, monitor its
live process/session, and preserve all results. No execution or acceptance
claim follows from this release itself.

Continuation shutdown checkpoint 21, 2026-09-28: the one released diagnostic
attempt ran once and failed cleanly inside the container before QEMU launch.
Container `16e3d5e4...` exited 1 without OOM after 247 ms; the inner traceback is
`OwnerError: inside QEMU version drift`. The owner then authenticated and removed
that exact container, three final exact lookups were empty, the development
lease was released, and no QEMU, mcexec, guest or diagnostic owner remains.
The original root-owned evidence directory and every command record are retained
under `/home/holden/mckernel-work/scratch/ndcs-20260928-1.owner-6ea6a57520d94590b709b46dc011167c`.

This is an observer failure, not an OS result. Owner `4ed6f849...` compares the
first version line to shortened text `QEMU emulator version 10.1.0`, while the
repository's retained exact record for pinned QEMU `5c198504...` is
`QEMU emulator version 10.1.0 (qemu-kvm-10.1.0-16.el10_2.5)`. The positive unit
mock copied the shortened constant and therefore did not model the actual pinned
binary. No application bytes, kernel log or guest exit exist because the backend
was never entered. Exact hashes, timings, cleanup receipts and limits are in
`docs/verification/stability-native-diagnostic-current-signal-attempt-failure-20260928-1.json`.
The complete live-process/resource/next-task shutdown cursor is
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-21.json`.

All eight child agents are terminal. Launcher PID 3125264, recovered worker PID
3170135 and app-server PID 3170137, started at 2026-09-28 03:47:42 and 05:01:20
-0700, remain alive for `.git/os-autopilot/runs/20260928T120120Z-056cff0a`.
At the shutdown observation, host/scratch free space is 45,754,019,840 and
22,277,754,880 bytes, available memory is 30,000,996 KiB, and the heavy lease is
free. Real guest applications and current-candidate builds added by this attempt
are **0** and **0**.

Next tasks are: (1) bind the observer to the exact retained full QEMU version
output and add cheap local positive/suffix/extra-output regressions; (2) rerun
the unprivileged owner/combined suites and obtain independent source review;
(3) commit that correction, then use a fresh parent and nonce in a newly bound
packet and obtain a fresh independent one-shot release; (4) only after a new
resource/lease reconciliation, run one corrected diagnostic and preserve its
application bytes, exit, kernel log, QMP/serial, process identities and teardown;
and (5) continue the pending-free owner/token/generation, invalidation-ack and
durable-quarantine lane after the diagnostic signal. The failed parent/nonce
must never be reused, and the deterministic observer failure must not be replayed
unchanged. Official counters remain 0/273 applications, 2/4 narrow fault modes,
6/130 production gates, 350/10,000 points and 0/7 language gates. Whole-OS
acceptance remains incomplete; this checkpoint pauses rather than resumes or
completes the goal.

Continuation checkpoint 22, 2026-09-28: the first runtime attempt's observer
failure is corrected in pushed commit `79a1424f...`. The inner owner now binds
both the existing exact QEMU binary digest and the complete retained stdout,
including the Rocky `10.1.0-16.el10_2.5` suffix and copyright line; return status
must be zero and stderr empty. The positive fixture independently spells those
bytes. Missing/altered suffix, extra output, missing/altered copyright and
nonempty-stderr negatives all reject before runner exec.

The coordinator's fresh unprivileged six-module suite passes 211/211 in 12.539
seconds; raw stderr SHA256 is `725d0bc0...`. The first independent review found
two singleton-tuple negatives and a self-consistent positive fixture, so that
candidate was not accepted. After the bounded correction, independent review
returns `PASS_SOURCE_READY_FOR_FRESH_PACKET` for owner `35cd4596...` and tests
`f15fdef9...`. Fetched remote commit and both source blobs match locally.

This is source/fixture evidence only. No Docker, root, QEMU, guest, build or
application command ran, and official counters remain unchanged. Next prepare
a fresh packet bound to commit `79a1424f...`, a never-used short parent and a
fresh nonce; obtain a separate independent one-shot release before executing.
Exact commands, hashes, review history and limits are in
`docs/verification/stability-native-diagnostic-qemu-version-source-success-20260928-1.json`.

Continuation checkpoint 23, 2026-09-28: fresh current-signal packet 2 has
independent `PASS_EXACT_ONE_SHOT_EXECUTION_RELEASE`. Packet SHA256 is
`3917e333...`, bound to pushed commit `5f583b2c...`, corrected owner
`35cd4596...`, parent `/home/holden/mckernel-work/scratch/ndcs-20260928-2` and
nonce `d5c0db79dea44675abeb1c43c7187add`. Its QMP path is exactly 100 bytes.
The reviewer rejoined all six committed sources, strict manifest and artifact
inventory, pinned image/QEMU/full-version bytes, exact QEMU argv, 91-byte oracle,
process evidence, resource limits, deadlines and fail-closed cleanup. Parent,
inner attempt and sibling evidence were absent; packet-1 reuse is prohibited.

This releases exactly one diagnostic attempt and grants no application, M04,
production or whole-OS acceptance. Immediately recheck capacity, lease, source
and path freshness, create the exact parent once as uid/gid 1000 mode 0700, then
run only the released command. Preserve all output and do not retry if creation,
client retirement or owner cleanup becomes uncertain. Exact authority is in
`docs/verification/stability-native-diagnostic-current-signal-execution-release-20260928-2.json`.

Continuation checkpoint 24, 2026-09-28: the one released packet-2 attempt
crossed the previous preflight blocker and ran a real McKernel startup
application. QEMU PID/PGID/SID 3238385 booted the exact current-signal image;
guest PID 256 was scheduled, wrote the exact 91-byte stdout, exited with raw
wait status 0, reached stream EOF without truncation, removed procfs state,
completed cleanup/retirement/release with final errno 0, and powered down.
This is one real diagnostic guest application in this work window, but it is
not a formally accepted catalog case.

The diagnostic reported `kernel failure marker`, but exact replay identifies
only seven observer false positives: four expected `panic=-1` command-line
echoes, two lowercase `report a bug` PCI notices and successful `error=0`.
There is no actual panic/oops/BUG/warning/lockup in the kernel/debug streams.
After that observer defect, the real application mismatch remains: mcexec wrote
58 bytes (`objdump /proc/self/exe: 2` plus `warning: did not set LD_PRELOAD`)
to the captured application stderr, while the frozen oracle remains empty.
That output must be fixed at its source, not filtered or accepted.

QEMU was exactly reaped, container `812be46d...` exited 1 without OOM and was
authenticated/removed, three final exact lookups were empty, and the development
lease is free. The failed evaluator did not publish its internally retained QEMU
starttime; the live PID/group/session observation is preserved with that explicit
limitation. Original 136,695-byte serial, QMP transcript, inner failure and all
outer Docker records remain in their untouched attempt/evidence directories.
Exact hashes and results are in
`docs/verification/stability-native-diagnostic-current-signal-attempt-failure-20260928-2.json`.

Next: correct the marker observer locally while proving the 58-byte stream still
fails the empty oracle; implement and test the Rust/C mcexec no-preload path so
it does not run objdump or warn when no preload feature/value is requested;
then rebuild and rebind mcexec, overlay, initramfs and manifest before a fresh
independently released attempt. Do not reuse packet 2, its parent or nonce.
Official counters remain 0/273 accepted applications, 2/4 narrow fault modes,
6/130 production gates, 350/10,000 points and 0/7 language gates.

Continuation shutdown checkpoint 25, 2026-09-28: no new work was dispatched
after the shutdown request. All eight child agents are terminal, the heavy lease
is free, and no QEMU, mcexec, diagnostic owner or project compiler remains.
Launcher PID 3125264, recovered worker PID 3170135 and app-server PID 3170137
remain alive for `.git/os-autopilot/runs/20260928T120120Z-056cff0a`; launcher-owned
state was not edited. Host/scratch free space was 45,725,659,136 and
22,276,898,816 bytes, with 29,871,928 KiB available memory.

The bounded marker-observer correction is pushed at `41914a86...`. Its fresh
six-module suite passes 214/214, actual attempt-2 replay now reaches the real
`wrong payload bytes` result, and independent review returns
`PASS_SOURCE_READY_FOR_MCEXEC_REPAIR`. The frozen empty-stderr oracle remains
unchanged. This is observer evidence only and moves no acceptance counter.

A source-only mcexec candidate is preserved in three files. It captures all C
and Rust preload sources before executable lookup, returns without objdump or a
warning only when none is requested, and adds exact no-source, existing-source,
UTI, sched-yield and QLMPI test vectors. `git diff --check` and shell syntax pass.
The full equivalence suite, compilation, independent ABI review, artifact and
initramfs rebuild, and any new guest run were deliberately not started during
shutdown. Candidate hashes are `31030130...` (C), `b77d5443...` (Rust) and
`f39649ee...` (test harness).

Next: (1) run the complete equivalence suite with raw logs and allow at most one
bounded correction for this failure family; (2) obtain independent C/Rust/FFI
review; (3) build and hash-bind corrected mcexec under the reviewed pinned
profile; (4) rebuild/rebind overlay, initramfs, manifest and diagnostic source
identities; (5) create a new parent, nonce, packet and independent release; and
(6) only after fresh resource/lease checks, run one new diagnostic. Do not reuse
either prior parent/nonce, the stale mcexec artifact `b786e9c9...`, or weaken the
empty-stderr oracle. Exact shutdown identities, hashes, preserved attempt-2
paths and limits are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-25.json`.
Official counters remain 0/273 applications, 2/4 narrow fault modes, 6/130
production gates, 350/10,000 points and 0/7 language gates. One real diagnostic
guest application ran in this window; current-candidate builds remain zero.
Whole-OS acceptance remains incomplete, and this checkpoint does not resume or
complete the goal.

Continuation shutdown checkpoint 26, 2026-09-28: no new work was dispatched
after the shutdown request. All eight children are terminal, the heavy lease is
free, and no QEMU, mcexec, diagnostic owner or project compiler remains.
Launcher PID 3125264, recovered worker PID 3170135 and app-server PID 3170137
remain alive for `.git/os-autopilot/runs/20260928T120120Z-056cff0a`; launcher-owned
state was not edited. Host/scratch free space is 36,542,033,920 and
21,972,135,936 bytes, with 29,793,836 KiB available memory.

The source candidate and compiler-forwarding prerequisite are pushed at
`a1914e59...`. Four complete broad-equivalence attempts are retained with their
distinct failures. The focused pending-free test passed, but the broad suite
remains unaccepted: the native compiler is incompatible with the kernel Rust
surface and the current inventory lacks three inputs which that suite compiles
unconditionally. No module was skipped and no oracle was weakened. The exact
focused mcexec harness passes with digest `773c9d116a5f0f88`, and independent
C/Rust/FFI review returns `PASS_SOURCE_READY_FOR_BUILD`.

One exact current mcexec build now passes in the pinned compatibility profile.
The Rust artifact is `ee1f660b...02d073b` (453,352 bytes) and the C fallback is
`67dd5fef...0722241` (220,816 bytes). Independent inspection verified all 14
artifact hashes, normalized CMake profiles, compile/link rules, helper object,
ELF dependencies, symbols and both fastpath disassemblies, returning
`PASS_ARTIFACT_READY_FOR_DIAGNOSTIC_STAGING`. Its explicit limits remain: no
runtime, application, full-equivalence or production acceptance follows.

The diagnostic stager is bound to the new Rust artifact and has an explicit
regression against stale `b786e9c9...984639`; the coordinator reproduced all
5 tests plus py_compile and scoped diff checks. The fresh initramfs and manifest
were deliberately not started during shutdown. Next: (1) recover the exact
retained staging/overlay sequence; (2) create a fresh root/initramfs without
mutating historical inputs; (3) regenerate the strict manifest and update all
owner source bindings; (4) run the complete unprivileged combined suite and
obtain independent review; (5) checkpoint the fully rebound diagnostic and
obtain a fresh packet/release; and (6) only after a new resource/lease check,
run one new diagnostic. Separately repair the broad suite's missing IHK Rust
prerequisite rather than treating the focused pass as complete equivalence.

Exact paths, hashes, limitations, active identities and non-reuse rules are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-26.json`.
Official counters remain 0/273 applications, 2/4 narrow fault modes, 6/130
production gates, 350/10,000 points and 0/7 language gates. This work window
contains one real diagnostic guest and one current mcexec candidate build.
Whole-OS acceptance remains incomplete; this checkpoint does not resume or
complete the goal.

Continuation checkpoint 27, 2026-09-28: the current-signal diagnostic image is
now fully rebound to the reviewed mcexec no-source fastpath without modifying
the authenticated base. The actual runtime lineage uses the strict concatenated
overlay, not the older full-tree stager. Overlay and manifest changes pass 93
focused tests and the fresh six-module closure passes 216/216 in 13.78 seconds.
Independent source review returns `PASS_SOURCE_READY_FOR_FRESH_OVERLAY`.

Fresh overlay attempt 4 preserves the complete 38,191,104-byte decompressed
signal base as its exact prefix and appends six canonical members. Independent
replay proves the only final-map difference from attempt 3 is `bin/mcexec`, from
stale `b786e9c9...984639` to current `ee1f660b...02d073b`; collector, payload,
Linux kernel, McKernel image and all modules remain byte-identical. The derived
initramfs is `19c34476...17fef3f`, 12,395,825 bytes. Raw stderr is empty and the
artifact review returns `PASS_OVERLAY_ARTIFACT_READY_FOR_STRICT_MANIFEST`.

Strict manifest 3 is `ab290581...a1ecc6` and joins the new overlay source,
derived image, launcher path/hash/identity and unchanged empty-stderr oracle.
The owner now binds that exact manifest and diagnostic source; a read-only call
through its actual `bound_manifest()` succeeds. Independent closure review
returns `PASS_SOURCE_AND_MANIFEST_READY_FOR_CHECKPOINT`. Old manifests, packets,
releases, parents and nonces remain immutable and grant no authority to run the
new image.

The complete broad equivalence suite remains unaccepted for a separate retained
prerequisite: three IHK Rust helper inputs referenced unconditionally by the
harness are absent from pinned upstream history and all searched retained
worktrees. Historical logs prove prior fixture behavior but do not recover exact
source bytes. Do not skip those modules or treat the focused mcexec harness as
full equivalence; reconstruct them only against current C bodies and independent
fixture contracts with fresh review.

Next: (1) commit and fetched-blob verify this source/artifact-binding checkpoint;
(2) create a never-used short parent and nonce in packet 3 bound to the new
commit, owner, manifest and derived image; (3) obtain a separate independent
one-shot execution release; and (4) after fresh capacity, lock, container and
process checks, execute once and preserve application bytes, raw exit, kernel
logs, QMP/process identities and teardown. Exact evidence and limits are in
`docs/verification/stability-native-diagnostic-mcexec-overlay-success-20260928-1.json`.
Official counters remain 0/273 applications, 2/4 narrow fault modes, 6/130
production gates, 350/10,000 points and 0/7 language gates. This work window
still contains one real diagnostic guest and one current mcexec build. No new
runtime or acceptance credit follows from source/image preparation. Whole-OS
acceptance remains incomplete.

Continuation shutdown checkpoint 28, 2026-09-28: new dispatch stopped at the
shutdown request and all eight child lanes are terminal. The heavy lease is
free; no project QEMU, diagnostic owner, mcexec compiler or heavy build remains.
Launcher PID 3125264, recovered worker PID 3170135 and app-server PID 3170137
remain alive with their original process groups and sessions for
`.git/os-autopilot/runs/20260928T120120Z-056cff0a`; launcher-owned state was not
edited. Host/scratch free space is 36,488,355,840 and 21,959,589,888 bytes,
with 29,706,652 KiB available memory.

Packet 3 is immutably rejected as `FAIL_EXACT_ONE_SHOT_EXECUTION_RELEASE`. It
and its parent/nonce must never execute or be reused. The exact packet and
failure record are retained with hashes `01be2070...7ecec9` and
`0c27ac2c...1ab9e6`. No root, Docker, QEMU or guest operation followed the
review failure.

The two bounded repair lanes now preserve outer Docker-client identities and
inner QEMU argv, process identity and exact post-reap return code on success and
failure. Coordinator integration joins the QEMU record to the observation and
refreshes the diagnostic/backend source pins. The first combined run correctly
failed four stale synthetic owner fixtures; after the bounded fixture update,
all 156 diagnostic/backend/owner tests pass in 11.416 seconds, with py_compile
and scoped diff checks also passing. This is source/test evidence only: the
integrated boundary still requires independent review and gains no runtime or
acceptance credit.

Next: (1) independently review the integrated client/QEMU ownership and evidence
joins; (2) permit at most one bounded correction for this failure family;
(3) rerun the full six-module unprivileged suite and actual `bound_manifest()`;
(4) checkpoint and fetched-blob verify the final source hashes; (5) create
packet 4 with a fresh short parent and nonce; and (6) only after a distinct
one-shot release plus fresh capacity/lease checks, execute one diagnostic.
Separately reconstruct and review the three missing IHK Rust helper prerequisites
before claiming broad equivalence. Exact identities, hashes, tests and limits
are in
`docs/verification/stability-continuation-shutdown-checkpoint-20260928-28.json`.
Official counters remain 0/273 applications, 2/4 narrow fault modes, 6/130
production gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance
remains incomplete; this checkpoint neither resumes nor completes the goal.

Continuation checkpoint 29, 2026-09-28: packet 3 remains immutably rejected and
unexecuted, but its complete process-evidence failure family is now repaired at
source level. The first correction passed 231 six-module tests yet independent
review reproduced five acquisition/capture/finalization/retirement/argv gaps.
The escalated coherent repair closed those gaps; its first re-review then found
two additional failures: a QEMU-evidence `BaseException` could be demoted behind
later host capture, and a delayed-reap pair could be consumed before successful
queueing. The one bounded correction now preserves exact first-failure identity
and makes delayed reap publication transactional through peek/ack and retry.

The coordinator's fresh final six-module run passes 234/234 in 16.522 seconds,
with py_compile, scoped diff checks and actual `bound_manifest()` for strict
manifest `ab290581...a1ecc6` all passing. Independent re-review returns
`PASS_SOURCE_READY_FOR_PACKET4`. Exact source/test hashes, both preserved review
failures and raw scratch evidence are recorded in
`docs/verification/stability-native-diagnostic-process-evidence-source-success-20260928-1.json`.
This is source readiness only; packet 3, its parent and nonce remain unusable,
and no Docker, QEMU, guest or application ran in this continuation.

The unchanged M02 descriptor/identity component also received fresh executable
and independent confirmation: real closed-stdio/source-equals-destination/
fd-198 remaps preserve exact exec descriptors; successful-create IDs are bound
to the producer counter; live identities cannot alias while 17 legitimate
post-retirement reuse cases pass. The reviewer returns
`PASS_SOURCE_READY_FOR_LAYER_B`, matching the retained exact source manifest.
Layer-B/root13 remains closed because its current executor strategy is rejected;
no unchanged packet was replayed.

The broad equivalence blocker is now precisely scoped. The three absent IHK
Rust inputs have no recoverable history and are substantial core, SMP and
ihklib modules, not shims. Relevant production C is identical across the pinned
gitlink and observed IHK HEAD. Their authorities, symbol counts, differential
vectors and two C quirks that must not be silently repaired are retained in
`docs/verification/stability-ihk-missing-rust-helper-reconstruction-audit-20260928-1.json`.
No broad-equivalence or production-integration claim follows.

Next: (1) commit/push and fetched-blob verify this exact source checkpoint;
(2) create packet 4 with a fresh short parent and nonce bound to that commit,
manifest, derived image and owner hash; (3) obtain a separate one-shot execution
release; and (4) after fresh capacity/lease checks execute once and preserve
application bytes, raw exit, kernel log, QMP/process/container identities and
teardown. In parallel, change the rejected Layer-B strategy before M02 runtime
and assign the three IHK modules as separate implementation lanes. Official
counters remain 0/273 applications, 2/4 narrow fault modes, 6/130 production
gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance remains
incomplete.

Continuation checkpoint 30, 2026-09-28: packet 4, SHA256
`1c6701f6...93ec6`, was independently rejected before execution. Its exact
source, manifest, artifacts, command, profile, oracle, fresh-path state and
cleanup rules passed review, but both acquisition paths discarded PGID/SID
already observed when a later starttime read failed. The packet, parent
`ndcs-20260928-4` and nonce `e8e0bd60...86bee` are permanently nonreusable; the
additive failure record preserves the reproduction and otherwise-verified
closure. No root, Docker, QEMU or guest operation occurred.

The one bounded correction now retains PID, PGID, SID and starttime immediately
after each individual successful read for both inner QEMU and outer Docker
clients. A later read/validation failure records every observed primitive and
null only for unobserved fields; no post-retirement identity sampling occurs.
Complete identity remains mandatory for transfer/signaling, so partial evidence
does not broaden authority. The final six-module run passes 236/236 in 16.626
seconds; py_compile, scoped diff checks and strict `bound_manifest()` pass.
Independent review returns
`PASS_PARTIAL_IDENTITY_SOURCE_READY_FOR_CHECKPOINT`. Exact hashes and raw
evidence are in
`docs/verification/stability-native-diagnostic-partial-identity-source-success-20260928-1.json`.

Next: commit/push and fetched-blob verify these exact bytes, then create packet
5 with a fresh parent and nonce, obtain a new exact one-shot release, remeasure
capacity and reconcile the lease immediately before at most one diagnostic.
Packet 4 grants no authority. Official counters remain 0/273 applications, 2/4
narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7 language
gates. Whole-OS acceptance remains incomplete.

Continuation checkpoint 31, 2026-09-28: source checkpoint
`b020d8476117a309e8b22fe40f08ad9dd17aa8e9` is pushed and fetched-commit
verified. Fresh packet 5 uses parent `ndcs-20260928-5`, nonce
`7f531aa8...a01c3` and exact packet SHA256 `e0745c3c...2c57b`; all proposed
paths remain absent. A fresh independent review returns
`PASS_EXACT_ONE_SHOT_EXECUTION_RELEASE` for exactly one invocation of the
packet's sudo-A owner command after coordinator capacity, process, container,
lock and path preflight. The release binds the strict manifest/artifact closure,
progressive identity records, exact resource profile, 91-byte stdout/empty
stderr oracle, deadlines and cleanup uncertainty rules. Packet 3 and 4 remain
rejected and nonreusable.

Next: commit/push and fetched-blob verify packet 5 plus its additive release,
then remeasure capacity, authenticate that no prior diagnostic owner/container
or QEMU holds the lease, create the parent once as uid/gid 1000 mode 0700, and
run only the released command. Preserve raw stdout/stderr/status, application
bytes, serial/debugcon/kernel logs, QMP, all process/container identities and
final absence before interpreting the result. A diagnostic pass remains outside
formal M04/application/production acceptance. Whole-OS acceptance remains
incomplete.

Shutdown checkpoint 32, 2026-09-28: the launcher requested termination of
this invocation before packet 5 execution. No new task was dispatched, all
eight child agents are terminal, and no diagnostic owner, Docker client, QEMU,
guest or heavy build was started. The released parent, inner attempt and
evidence sibling remain absent; packet 5's single execution authorization is
therefore unconsumed. Preserve the exact active process identities observed at
2026-09-28T09:35:55-07:00: launcher PID 3125264 (PPID 771805, start
2026-09-28 03:47:42 PDT), recovered worker PID 3170135 (PPID 3125264, start
05:01:20 PDT), and app-server PID 3170137 (PPID 3170135, start 05:01:20 PDT).
The launcher owns their shutdown and future continuation state; this checkpoint
does not stop, replace or resume them.

Next invocation: first reconcile those process identities, launcher state and
the heavy-runtime lease. Verify checkpoint 32 and the packet/release blobs from
the fetched remote commit, then remeasure host/scratch/memory capacity and
repeat the released fresh path/container/lock checks. If and only if every
packet-5 precondition still holds, create its parent once as uid/gid 1000 mode
0700 and consume at most the one exact released sudo-A command. Do not reuse
packet 3 or 4, do not restart an uncertain attempt, and retain all outer/inner
process identities plus application bytes, status, logs and teardown evidence.
Official counters remain 0/273 applications, 2/4 narrow fault modes, 6/130
production gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance
remains incomplete.

Shutdown checkpoint 33, 2026-09-28: checkpoint 32, packet 5 and its release
record were committed as `429b926c09c71fe7531b671a411cf9e5f2816418`,
pushed to `origin/codex/local-native-staging-repair`, fetched back, and matched
the exact commit. Fetched blob IDs match locally for CURRENT
`39f73b7a05bd8754158594d850bb7befacaef337`, PROGRESS
`31f5f361f9fd78c4fa3a23ed6e37287744508165`, packet 5
`6351f074e8ff7b5277b0221925cfdd99a8ae93df`, and its release
`25e0d9031cd168a7b7af737e6d1e9a5d2ae38f68`. No runtime attempt was made and
the one-shot release remains unconsumed. Resume with checkpoint 32's exact
identity/lease/capacity preflight and next action; do not treat this shutdown
record as OS completion or formal acceptance.

Continuation checkpoint 34, 2026-09-28: the single released packet-5 command
was consumed exactly once. One real diagnostic McKernel guest application ran:
`startup.argv-empty` produced the exact 91-byte stdout, empty stderr, raw wait
status zero, EOF without truncation, empty procfs and normal application/process
retirement. QMP observed guest shutdown; QEMU PID/PGID/SID 10 and starttime
82339040 were exactly reaped with status -9. Container exit was zero, OOM was
false, every Docker client was reaped, authenticated removal/final absence
passed, and the development lock is free. No diagnostic owner, QEMU or matching
container remains. Raw inner and root-owned outer evidence, exact hashes and
identities are preserved in
`docs/verification/stability-native-diagnostic-current-signal-attempt-failure-20260928-3.json`.

The inner protocol passed, but the immutable outer result remains FAIL at
`QEMU evidence/result join`: the outer owner required QEMU status zero even
though the reviewed `-no-shutdown` cleanup intentionally sends TERM then KILL
before reap. Independent review verified the application bytes, QMP ordering,
capture copies, identities and teardown and authorized one bounded source
correction. The owner now accepts only exact integer statuses 0, -SIGTERM and
-SIGKILL, preserving the actual status; boolean, null, string, positive failure
and unrelated signals reject. The final six-module suite passes 244/244 in
16.507 seconds; py_compile, scoped diff checks, actual `bound_manifest()` and
independent read-only replay of packet-5 evidence pass. Exact source and test
hashes are retained in
`docs/verification/stability-native-diagnostic-qemu-status-source-success-20260928-1.json`.
Checkpoint `846ebe49c15bf885cb8982890759bb46746e9591` is pushed, fetched and exact
blob verified.

Next: prepare packet 6 against `846ebe49` with a fresh parent and nonce, preserve
packet 5 as consumed/nonreusable, and obtain a new independent exact one-shot
release. After fresh capacity, process, container, lock and path reconciliation,
run at most that one command and require both inner and outer protocol success.
This continuation has one real diagnostic guest app and zero current-candidate
builds; the latest executable result completed at 2026-09-28T16:40:00Z. Official
counters remain 0/273 applications, 2/4 narrow fault modes, 6/130 production
gates, 350/10,000 points and 0/7 language gates. Whole-OS acceptance remains
incomplete.

Continuation checkpoint 35, 2026-09-28: packet 6 is bound to pushed/fetched
source checkpoint `846ebe49c15bf885cb8982890759bb46746e9591`, fresh parent
`ndcs-20260928-6`, nonce `0f54526b...83a9e2`, corrected owner SHA256
`038fe292...173f1` and exact packet SHA256 `6cc79499...99de3`. Its generated
42-argument QEMU plan matches the packet and the private QMP path is 100 bytes.
The parent, inner attempt and root-owned evidence sibling remain absent.
Independent review returns `PASS_EXACT_ONE_SHOT_EXECUTION_RELEASE` for exactly
one invocation of the packet's sudo-A command after fresh coordinator capacity,
process, container, development-lock and path checks. Packet 5 is consumed and
nonreusable; packets 3 and 4 remain rejected and nonreusable.

Next: commit/push and fetched-blob verify packet 6 plus this release, then
remeasure capacity and reconcile every runtime owner immediately before setup.
If all preconditions still hold, create the parent once as uid/gid 1000 mode
0700 and execute only the released command. Preserve exact application bytes,
status, serial/debugcon/kernel logs, QMP, every process/container identity and
final teardown. No formal acceptance follows from release or a diagnostic pass.

Continuation checkpoint 36, 2026-09-28: packet 6 consumed its single release
and passes both inner and outer protocols. One real diagnostic McKernel
`startup.argv-empty` application again produced the exact 91-byte stdout, empty
stderr, raw wait status zero, complete EOF, empty procfs and normal retirement.
QMP has 1,348 records and 672 matched successful request/reply pairs through
guest shutdown and host quit. QEMU PID/PGID/SID 11, starttime 82440018 and
status -9 match the admitted command and reviewed cleanup policy. All 30 Docker
clients have exact identity/reap records; the container exited zero without OOM,
removal and three final empty lookups passed, the development lock is free, and
no matching owner, QEMU or container remains.

Independent review returns `PASS_DIAGNOSTIC_PROTOCOL_EVIDENCE` after checking
the exact source/artifact closure, archive and oracle replay, application bytes,
QMP ordering, capture bindings, process/container identities and teardown. Raw
inner/outer paths, tuple hashsets and key file hashes are retained in
`docs/verification/stability-native-diagnostic-current-signal-success-20260928-1.json`.
Packet 6 is consumed/nonreusable. This continuation now has two real diagnostic
guest applications (packet 5 exposed the outer join defect; packet 6 passed)
and zero current-candidate builds. The latest executable result completed at
2026-09-28T16:56:49Z.

Next: adapt the now-passing owner/runner boundary to the unchanged dynamically
linked `native-application-core` memory mode. Authenticate its retained binary,
loader/libc and current signal module/image tuple; generate a fresh manifest and
overlay under the unprivileged reviewed profile; then obtain a new exact release
for memory before proceeding to files, threads and shutdown. Official counters
remain 0/273 applications, 2/4 narrow fault modes, 6/130 production gates,
350/10,000 points and 0/7 language gates. Whole-OS acceptance remains incomplete.

Shutdown checkpoint 37, 2026-09-28: the launcher requested termination of
this invocation after continuation checkpoint 36. No new task was dispatched,
all eight existing child lanes are terminal, and no build, guest, container or
runtime operation was started after the request. At 2026-09-28T17:03:22Z the
only live campaign processes were launcher PID/PGID/SID 3125264, `/proc`
starttime 80228730; recovered worker PID/PGID/SID 3170135, starttime 80670556;
and app-server PID/PGID/SID 3170137, starttime 80670562. Their parent chain was
771805 -> 3125264 -> 3170135. The launcher owns their shutdown and paused
continuation state; this checkpoint does not stop, replace or resume them.
There was no live diagnostic owner, `native_diagnostic.py`, QEMU or Docker
client. Preserve the packet-6 inner root
`/home/holden/mckernel-work/scratch/ndcs-20260928-6`, outer root
`/home/holden/mckernel-work/scratch/ndcs-20260928-6.owner-0f54526bcbdfd2433bbc5ac7d783a9e2`
and readable review copy
`/home/holden/mckernel-work/scratch/native-diagnostic-packet6-outer-review-copy-20260928-1`.

Next invocation: first reconcile the three process identities above, launcher
state, repository HEAD and the heavy-runtime lease. Preserve packet 5 and 6 as
consumed and nonreusable. Then implement two disjoint unprivileged preparation
changes: make `native_diagnostic_overlay.py` require and authenticate an
explicit payload SHA256, and make `native_diagnostic_container_owner.py`
require and propagate an explicit canonical manifest path and SHA256 through
the outer/inside boundary. Add strict positive and fail-closed tests and run
the complete six-suite diagnostic regression before checkpointing. After
independent source review, authenticate the retained
`native-application-core` binary SHA256
`558d1607e4648321c9537215084e759496937d9591c319a21443f443193fda9a`
and its loader/libc plus the exact current signal module/image tuple. Generate
a fresh memory-mode overlay and manifest for `native-application-core memory`,
expected stdout `NATIVE_CORE PASS memory\n`, empty stderr and exit 37. A fresh
one-shot execution packet and independent release are required before any
runtime attempt; proceed to files, threads and shutdown only after preserving
memory bytes, status, logs, identities and teardown. This shutdown checkpoint
does not change the two diagnostic-app/zero-current-candidate-build count,
official acceptance counters, or whole-OS incomplete status.

Continuation checkpoint 38, 2026-09-28: memory-diagnostic source preparation
is independently accepted for checkpointing after one bounded correction. The
overlay now requires an explicit payload SHA256 and checks the bytes before
creating output; the owner now requires and propagates an explicit canonical
manifest path/hash through the inspected container command. Outer and inside
admission reject missing, malformed, wrong, noncanonical, symlinked,
outside-scratch and drifted identities. The first independent review found
that a manifest below the writable attempt parent could change before the
runner reopened it. The corrected owner rejects that subtree before container
creation and again before inside exec. Final review returns
`PASS_SOURCE_READY_FOR_CHECKPOINT`; 260 diagnostic tests pass in 17.462
seconds, with py_compile and scoped diff checks passing. Exact hashes and both
review decisions are retained in
`docs/verification/stability-native-diagnostic-memory-preparation-source-success-20260928-1.json`.

The retained core archive SHA256 is `7e2d88ab...ce8cc`. A fresh unprivileged
copy of its unchanged 39,488-byte payload has SHA256 `558d1607...da9a`; its
interpreter is `/lib64/ld-linux-x86-64.so.2` and its sole needed DSO is
`libc.so.6`. The extracted loader and libc compare byte-for-byte with the
current signal base root. The exact memory oracle is 24-byte stdout
`NATIVE_CORE PASS memory\n`, empty stderr and exit 37. No overlay, manifest,
root, container, QEMU or guest execution is accepted by this checkpoint.

Next: commit/push and fetched-blob verify these reviewed source bytes and
evidence. Then generate a fresh overlay and strict memory manifest against the
exact current signal module/image tuple, replay every artifact/final-map join,
and obtain independent artifact plus one-shot execution review before any
runtime. Packet 5 and 6 remain consumed/nonreusable. This continuation still
has two real diagnostic guest applications and zero current-candidate builds;
official counters and whole-OS incomplete status are unchanged.

Shutdown checkpoint 39, 2026-09-28: the requested work-window shutdown stopped
new dispatch before any collector build, overlay, manifest, root, container,
QEMU or guest operation. All eight child lanes are terminal. The bounded source
work already in progress is independently accepted for checkpointing. Strict
manifest startup argv now requires the exact `/bin/mcexec -t 1 0 app` prefix
and bounds exact UTF-8 arguments, while the collector selects memory, files,
threads or signals only through mutually exclusive presence flags that map to
source-fixed literals. Every legacy value-bearing selector rejects. After two
source corrections and one preserved test-observer failure, the final integrated
suite passes 280 tests in 22.381 seconds; py_compile and scoped diff checks pass.
Exact hashes, corrections and raw capture identities are retained in
`docs/verification/stability-native-diagnostic-memory-profile-source-success-20260928-1.json`.

At 2026-09-28T10:27:13-07:00 the only live campaign processes were launcher
PID/PGID/SID 3125264 with `/proc` starttime 80228730, recovered worker
PID/PGID/SID 3170135 with starttime 80670556, and app-server PID/PGID/SID
3170137 with starttime 80670562. Their parent chain remains
771805 -> 3125264 -> 3170135. The launcher owns their shutdown and paused
continuation state. No diagnostic owner, QEMU or matching Docker client was
live; unprivileged Docker enumeration was unavailable and no privileged check
was started during shutdown.

Next invocation: reconcile these exact process identities, launcher state,
repository HEAD and the heavy-runtime lease. Preserve packets 5 and 6 as
consumed/nonreusable. Build a fresh static collector with `ND_CORE_MEMORY=1`
under `/home/holden/mckernel-work/scratch/native-diagnostic-memory-collector-build-20260928-1`,
authenticate its compiler inputs, bytes and ELF properties, then generate a
fresh overlay and strict memory manifest using the already authenticated core
payload, loader/libc and exact current signal tuple. Require independent
artifact/manifest review and a separate exact one-shot release before runtime.
The continuation count remains two real diagnostic guest applications and zero
current-candidate builds; official acceptance counters and whole-OS incomplete
status are unchanged.

Continuation checkpoint 40, 2026-09-28: the source-fixed memory collector built
successfully as a static x86-64 ET_EXEC with SHA256 `247433d6...0556`, no
interpreter/dynamic section and a non-executable stack. Independent audit returns
`PASS_ARTIFACT_READY_FOR_OVERLAY`. The first overlay command used a transcribed
base-CPIO digest and failed before output; its root remains preserved. The one
bounded correction used fresh attempt 2 and the actual authenticated digest
`fefbfbe3...0de57`. Strict replay preserves the complete 38,191,104-byte base
prefix and joins 61 final members. The derived initramfs is `3fff2b94...e662`.

The strict `baseline.core.memory` manifest is SHA256 `10bbde5a...0660d` and
binds `/bin/mcexec -t 1 0 app memory`, exact 24-byte stdout
`NATIVE_CORE PASS memory\n`, empty stderr and exit 37. Independent review
returns `PASS_ARTIFACT_MANIFEST_READY_FOR_PACKET`, including all 37 final
userspace ELF provider joins and the exact signal module/image/runtime tuple.
Fresh packet 1 has SHA256 `057872d9...cece`, parent `ndcm-20260928-1`, nonce
`5759bc5f...f3c8a`, and a 100-byte QMP pathname. A separate independent review
returns `PASS_EXACT_ONE_SHOT_EXECUTION_RELEASE` for only its exact sudo-A command,
conditional on pushed/fetched packet/release blobs and fresh live preflight.
No root, container, QEMU or guest operation has occurred yet.

Next: commit, push and fetched-blob verify the artifact evidence, packet and
release. Then remeasure the 16/12-GiB disk and packet memory floors, reconcile
launcher identities and the single heavy lease, authenticate the real
development lock, Docker/container absence, every source/artifact and the three
fresh paths. If all remain exact, create the parent once as uid/gid 1000 mode
0700 and consume at most the single released command. Preserve application
bytes/status, serial/debugcon/kernel/QMP, every process/container identity and
final teardown. Packet 5/6 remain consumed and memory overlay attempt 1 remains
historical. No diagnostic result promotes formal counters; the continuation
still has two real guest applications and zero current-candidate kernel builds.

Continuation checkpoint 41, 2026-09-28: the one released memory command was
consumed exactly once and passes both inner and outer protocols. The real
`native-application-core memory` guest produced exact 24-byte stdout
`NATIVE_CORE PASS memory\n`, empty stderr, raw wait status 9472/exit 37,
complete EOF and empty procfs. Scheduling, sampled syscall delivery/return/route,
terminal exit-group, retirement, four-reference pager release, procfs deletion
and process release all join. QMP has 1,393 records: all 695 requests have
successful replies, guest shutdown precedes shutdown-status confirmation and
host quit. QEMU PID/PGID/SID 10, starttime 82726129 and return -9 match the
reviewed cleanup path.

All six inner/outer captures match. All 30 Docker clients have distinct exact
identities and completed reaps. Container
`e4c295f0...69418` exited zero without OOM; authenticated removal preceded
three empty lookups, and the development lock is free. Independent review
returns `PASS_DIAGNOSTIC_PROTOCOL_EVIDENCE`. The release record's hand-entered
`recorded_at` incorrectly says 10:51; it remains immutable. Additive correction
in `docs/verification/stability-native-diagnostic-memory-success-20260928-1.json`
binds authoritative Git/fetch at 17:42:45-53Z, successful live preflight at
17:43:40Z and container start at 17:43:55Z. No ordering gap exists.

Next: commit/push/fetch-verify the reviewed memory result, then reuse the same
unprivileged preparation profile to build `ND_CORE_FILES=1`, establish the exact
host files oracle, derive a fresh overlay and strict manifest, and obtain a new
artifact/packet/release review before one files diagnostic. Memory packet 1 is
consumed and nonreusable. This invocation has one real diagnostic guest app and
zero current-candidate kernel builds; the latest executable result completed at
2026-09-28T17:44:31Z. Official counters remain 0/273 applications, 2/4 narrow
fault modes, 6/130 production gates, 350/10,000 points and 0/7 language gates.
Whole-OS acceptance remains incomplete.

Shutdown checkpoint 42, 2026-09-28: the launcher stop request ended new task
dispatch before the prepared files diagnostic could become an execution packet.
No files parent, owner, container, QEMU or guest was created. The bounded
artifact review was stopped and closed; it verified the strict manifest,
artifact hashes/modes, the 61-member raw-CPIO prefix and canonical overlay
replay, final map, static collector profile, raw oracle streams, both preserved
pre-entry oracle failures, pure QEMU argv, absent execution paths and the
100-byte QMP pathname. It did not complete the 37-ELF dependency/version audit
because its host Python lacks `os.memfd_create`, and it did not inspect the
supplied oracle protocol record before shutdown. It therefore correctly did
not issue `PASS_ARTIFACT_MANIFEST_READY_FOR_PACKET`.

The prepared files collector remains at
`/home/holden/mckernel-work/scratch/native-diagnostic-files-collector-build-20260928-1/init`,
SHA256 `44bdb28f...1ab6`. The derived initramfs is
`/home/holden/mckernel-work/scratch/native-diagnostic-files-overlay-20260928-1/initramfs.cpio.gz`,
SHA256 `100e9989...aa15`; its overlay manifest is `60db93f4...aea89`.
The strict files manifest is
`/home/holden/mckernel-work/scratch/native-diagnostic-files-manifest-20260928-1/manifest.json`,
SHA256 `1987e592...4186`, and binds exact stdout
`NATIVE_CORE PASS files\n`, empty stderr and exit 37. Oracle attempt 1 preserves
the host-libc version mismatch (`stderr` SHA256 `273c21a1...0578`); attempt 2
preserves the non-executable extracted-loader failure (`9b5bf98a...5746`).
Corrected attempt 3 has exact 23-byte stdout SHA256 `e3a3b692...0bee`, empty
stderr and exit 37, with no residual `/tmp/native-core-*.dat`; its exact command,
status and cleanup are retained in launcher protocol lines 127829-127830 under
item `exec-69e213df-a867-4ee1-97da-ce6dd5f25fe3`.

At 2026-09-28T10:56:17-07:00 the live campaign identities remained launcher
PID/PGID/SID 3125264/starttime 80228730, recovered worker
PID/PGID/SID 3170135/starttime 80670556, and app-server
PID/PGID/SID 3170137/starttime 80670562. No diagnostic owner or QEMU was live;
the proposed `/scratch/ndcf-20260928-1` parent and owner-evidence sibling remain
absent. The launcher-owned state still reported `phase=running`; this shutdown
record does not edit that state or resume/complete the goal.

Next invocation: reconcile the exact campaign process identities, launcher
state, repository HEAD and heavy-runtime lease. Resume the incomplete files
artifact review with a compatible sealed ELF-audit mechanism, inspect the
retained oracle protocol record, and require a fresh independent
`PASS_ARTIFACT_MANIFEST_READY_FOR_PACKET`. Only then create and independently
review a files execution packet/release; do not reuse the proposed nonce or
claim that the partial review released execution. Memory packet 1 remains
consumed and nonreusable. The invocation still has one real diagnostic guest
application and zero current-candidate kernel builds; formal counters and the
whole-OS incomplete status are unchanged.

Continuation checkpoint 43, 2026-09-28: files artifact review resumed from the
shutdown boundary and completed its sealed audit using a compatible
`memfd_create` path. All 37 userspace ELFs join across 52 dependencies, 11
interpreters and 270 required-version/provider definitions. The review then
found that oracle attempt 3's `set -u` command could mask a failed residual-file
test with its unconditional final output and exit zero. That attempt remains
preserved as rejected observer evidence. Fresh unprivileged attempt 4 is the one
bounded correction: under `set -e` it proves empty pre/post residual inventories,
exit 37, exact 23-byte `NATIVE_CORE PASS files\n` stdout and empty stderr.
Independent review returns `PASS_ARTIFACT_MANIFEST_READY_FOR_PACKET`.

Fresh files packet 1 uses parent `ndcf-20260928-2` and nonce
`30cd836a7be0fd61d4b43fc1042e6afc`; the checkpoint-42 proposed nonce and all
`ndcf-20260928-1` paths are explicitly forbidden and remain unused. The strict
manifest is `1987e592...4186`, derived initramfs `100e9989...aa15`, collector
`44bdb28f...1ab6`, packet `fd9b87fa...6648` and preparation evidence
`f0206739...ec6`. Independent review returns
`PASS_EXACT_ONE_SHOT_EXECUTION_RELEASE` for only the release record's exact
sudo-A command, conditional on pushed/fetched blob verification and fresh live
capacity, identity, lease, lock, source/artifact, container and path checks.
No root, container, QEMU or McKernel files application execution has occurred.

Next: commit, push and fetched-blob verify the preparation evidence, exact
packet and release. Reconcile the same launcher/worker/server identities and
single heavy lease, remeasure at least 16/12 GiB disk plus packet RAM headroom,
authenticate the development lock, all runtime bytes and fresh/forbidden paths,
and prove live owner/QEMU/Docker/container absence. If every released precondition
holds, create the parent once as uid/gid 1000 mode 0700 and consume the command
once with no retry. Preserve exact application bytes/status, kernel/serial/QMP,
all process/container identities and teardown for independent evidence review.
This invocation still has one real diagnostic guest application and zero
current-candidate kernel builds; formal counters and whole-OS status are
unchanged.

Continuation checkpoint 44, 2026-09-28: the one released files command was
consumed exactly once and passes independent runtime review. The real
`native-application-core files` guest produced exact 23-byte stdout
`NATIVE_CORE PASS files\n`, empty stderr, raw wait 9472/exit 37, complete EOF
and empty procfs. Thirty-two sampled syscall deliveries, 31 returns and 17
routes include create/read/write/seek/stat/close, successful unlink and the
subsequent ENOENT. Cleanup ACK succeeds; retirement retries from -11 to zero;
pager handle 20 releases four references to zero; procfs deletion and process
release with `cleanup_errno=0` complete.

All 696 QMP requests have unique successful replies and no error. Guest shutdown
precedes confirmed shutdown status and host quit; QEMU PID/PGID/SID 10,
starttime 82863808, is reaped with -9 under the reviewed cleanup path. All six
captures join. All 30 Docker clients have distinct identities and exact reaps.
Container `2dbf935f...c0887` exits zero without OOM, authenticated removal
precedes three empty final lookups, three post-review lookups remain empty and
the development lock is free. Independent review returns
`PASS_DIAGNOSTIC_PROTOCOL_EVIDENCE`. The evaluator's unconditional
`mckernel_application_executed=false` and required `application_acceptance=false`
fields remain preserved; the additive review establishes only one observed
diagnostic guest execution, never formal catalog acceptance.

Next: commit/push/fetched-blob verify
`docs/verification/stability-native-diagnostic-files-success-20260928-1.json`,
then bind the freshly prepared source-fixed threads collector and exact host
oracle through independent artifact review, a fresh overlay/strict manifest and
separate one-shot release. Files packet 1 is consumed and nonreusable. This
invocation now has two real diagnostic guest applications and zero
current-candidate kernel builds. Official counters remain 0/273 applications,
2/4 narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7
language gates; whole-OS acceptance remains incomplete.

Continuation checkpoint 45, 2026-09-28: shutdown was requested before any
threads execution review or privileged/runtime operation. The source-fixed
static threads collector is preserved at
`/home/holden/mckernel-work/scratch/native-diagnostic-threads-collector-build-20260928-1/init`,
mode 0700, size 1,021,296 and SHA256 `9dd9388b...9b10`. Its exact host oracle
passes with 25-byte stdout `NATIVE_CORE PASS threads\n`, empty stderr, exit 37
and empty pre/post residual inventories; the earlier hard-coded-hash oracle
failure remains preserved. The derived initramfs is `e16c593d...eec`, its
overlay manifest is `d97f1201...66e7`, the canonical overlay digest is
`5991339e...8a17`, and the strict manifest is `0a473e55...5ca9`.

Independent artifact review returns `PASS_ARTIFACT_MANIFEST_READY_FOR_PACKET`:
the archive preserves the exact base prefix and 61 final members, while all 37
userspace ELFs join across 52 dependencies, 11 interpreters and 270 required
version/provider definitions. Preparation evidence and a proposed packet are
now retained as
`docs/verification/stability-native-diagnostic-threads-artifact-success-20260928-1.json`
and
`docs/verification/stability-native-diagnostic-threads-execution-packet-20260928-1.md`,
SHA256 `51e94029...cb4` and `75b62e2e...d932`. The proposed parent
`ndct-20260928-1`, nonce `9561a169a33ebd6ecbd9ae567abbe869`, inner attempt
and owner-evidence sibling remain absent. These documents are preparation only:
there is no independent execution-release decision, release record, root
command, container, QEMU or McKernel threads application attempt.

At the shutdown boundary the campaign processes remain launcher PID/PGID/SID
3125264/starttime 80228730, recovered worker PID/PGID/SID 3170135/starttime
80670556, and app-server PID/PGID/SID 3170137/starttime 80670562. The
launcher-owned state reports `phase=running`; this checkpoint does not edit that
state and does not resume, pause through goal tooling, or complete the OS goal.
No diagnostic owner or QEMU process is live. Child agents are closed: all are
completed except the superseded threads artifact audit, which is interrupted;
the fresh threads overlay/manifest review completed with the PASS above.

Next invocation: reconcile HEAD, the three exact campaign identities,
launcher state and the single heavy-runtime lease. Validate the proposed packet
against the exact 42-element generated QEMU argv and 100-byte QMP pathname,
expanding the packet if needed, then obtain a fresh independent execution review.
Only after a PASS should a hash-bound release record be created, checkpointed,
pushed and fetched-blob verified. Repeat every live resource, identity, lock,
container, source/artifact and fresh-path precondition immediately before any
one-shot command. Preserve the absent parent/owner paths until that release.
The two real diagnostic guest applications and zero current-candidate builds
from this invocation remain unchanged. Formal counters remain 0/273, 2/4,
6/130, 350/10,000 and 0/7; no application or whole-OS acceptance is claimed.

Continuation checkpoint 46, 2026-09-28: the proposed threads packet was
expanded before review to freeze its exact generated 42-element QEMU argv rather
than relying on a files-packet comparison. A local reconstruction matches all
42 arguments and the 100-byte QMP pathname. The corrected packet SHA256 is
`1e39b581...fc46`; preparation evidence remains `51e94029...cb4`.

Fresh independent review returns `PASS_EXACT_ONE_SHOT_EXECUTION_RELEASE` for
only the packet's 15-element outer command, parent `ndct-20260928-1`, nonce
`9561a169a33ebd6ecbd9ae567abbe869`, strict manifest `0a473e55...5ca9`
and source commit `a2df0eb7...edd74`. The release record is
`docs/verification/stability-native-diagnostic-threads-execution-release-20260928-1.json`,
SHA256 `891d2291...94b3`. Review rejoined the immutable artifacts and exact
oracle, process/container/QEMU ownership, child reaping, authenticated cleanup,
lock retention and 300/360-second deadlines. It performed no root, Docker, QEMU,
guest or application operation. Parent, inner and evidence paths remain absent.

A parallel read-only audit confirms that the collector has no distinct shutdown
selector. The threads diagnostic covers application `exit_group`, process
retirement, procfs emptiness and subsequent guest `/poweroff`; it must not also
be counted as independent whole-OS/QEMU shutdown behavior. After threads runtime
evidence, define a separate shutdown invariant rather than relabeling this run.

Next: commit, push and fetched-blob verify the exact packet, artifact record,
release, tracker and this cursor. Then recheck live launcher/worker/server
identities, exclusive heavy lease, host/scratch/RAM floors, development lock,
all source/artifact bytes, process/container absence and all fresh paths. If and
only if every released precondition holds, create the exact parent once as
uid/gid 1000 mode 0700 and invoke the released command exactly once without
retry. Preserve every partial outcome and obtain independent raw runtime review.
This invocation still has two real diagnostic guest applications and zero
current-candidate builds; formal counters and whole-OS status remain unchanged.

Continuation checkpoint 47, 2026-09-28: the released threads command was
consumed exactly once and independent review returns
`PASS_DIAGNOSTIC_PROTOCOL_EVIDENCE`. The real McKernel application produced
exact 25-byte stdout `NATIVE_CORE PASS threads\n`, empty stderr, raw wait
9472/exit 37, complete untruncated EOFs and empty procfs. The bound pthread
fixture completed two workers, barrier synchronization, mutex-protected counter
2000, TLS isolation and joins. McKernel published TIDs 256/258/257, transferred
512 TID bytes and later deleted all three procfs entries.

Twenty-eight sampled syscall deliveries join with 27 returns and 13 correct CPU
routes; the sole unreturned delivery is `exit_group`. The capture does not
separately trace clone3 or futex syscall entries/counts, so no such narrower
trace claim is made. Cleanup ACK is zero, retirement retries from -11 to zero,
pager handle 20 releases four references to zero and process release reports
`cleanup_errno=0`.

All 696 QMP requests receive unique successful replies with no error across
1,396 records. Event order is RESUME, guest SHUTDOWN, STOP and host-QMP-quit
SHUTDOWN. QEMU PID/PGID/SID 10, starttime 83068581, is reaped with -9 under the
reviewed controlled cleanup path; this is not natural-exit or independent OS
shutdown acceptance. All 30 Docker clients have exact identities/reaps;
container `5d16ec94...21f7` exits zero without OOM, authenticated removal and
three empty lookups pass, the current lookup is empty and the original
development lock is free. All copied captures join their originals.

The retained inner result is `671c837d...65230`, outer result
`a9cbc7a4...62e82`, serial `5d4f1a57...d0438`, QMP transcript
`4ec0fe34...9ef7` and capture bindings `8b0229e9...2342`. The additive success
record is
`docs/verification/stability-native-diagnostic-threads-success-20260928-1.json`.
Conservative `mckernel_application_executed=false` and
`application_acceptance=false` fields remain unchanged; the independent review
establishes only observed diagnostic behavior.

A bounded shutdown-path audit finds the smallest existing real native observer
in `scripts/rocky-rust-validation.sh`: boot through `mcreboot.sh`, run a workload,
then `mcstop+release.sh` and `verify_boot_cleanup`. Its stop body is
`scripts/mcstop+release-smp.sh.in`, which destroys the OS, releases CPU/memory,
unloads modules and stops `ihkmond`. It lacks a current reviewed packet and exact
before/after CPU-mask, IRQ, ID, mapping and policy snapshots, so it does not yet
prove complete drain/restoration/recreate. Model-only lifecycle tests, application
exit, Linux-guest poweroff and QEMU kill remain explicitly insufficient.

Next: checkpoint/push/fetched-blob verify this threads result. Then bind a fresh
native stop/release observer and reviewed Rocky boot-workload-stop packet with
before/after resource snapshots and a recreate workload. Keep the remaining
CPU/callback/mapping ownership gaps explicit. This invocation now has three real
diagnostic guest applications and zero current-candidate builds. Formal counters
remain 0/273 applications, 2/4 narrow fault modes, 6/130 production gates,
350/10,000 points and 0/7 language gates; whole-OS acceptance remains incomplete.

Continuation checkpoint 48, 2026-09-28: the launcher requested shutdown, so no
new work was dispatched and all child agents were joined or interrupted. The
only active child was stopped during its bounded, unprivileged signals-artifact
preparation. It completed only the static collector compile: the preserved
binary is
`/home/holden/mckernel-work/scratch/native-diagnostic-signals-collector-build-20260928-1/init`,
mode 0700, size 1,021,968 and SHA256 `e1c7b50e...cdea`. Its exact input record is
`f43b483a...ac63`, compiler command record `cf1b3838...1c9`, and successful
compiler result `01ec2574...eb72`; compiler stdout/stderr are empty. The source
is `e78760ae...ad4a` at HEAD `8607850b...34c4`, selected with
`-DND_CORE_SIGNALS=1`. No host oracle, overlay, derived initramfs, strict
manifest, artifact review, execution packet, root command, container, QEMU or
McKernel signals application was run. The newly created oracle, overlay and
manifest directories are empty and preserved. Pre-existing empty `ndcs` parent
and owner-evidence directories remain untouched; their existence means those
names are forbidden for any future fresh attempt.

The shutdown audit is now bounded more precisely. The existing Rocky lifecycle
can exercise one real `mcreboot.sh` boot, workload and `mcstop+release.sh` stop,
and already observes CPU-online state, swappiness, IRQ affinity, processes,
modules and devices. It does not perform a second recreate cycle, and it lacks
the current exact mapping/procfs policy contract. Its outer wrapper also stages
the whole source tree, which is unsuitable for the evidence-heavy working tree
without a lean exact source binding. There is no current reviewed execution
release for this Rocky/QEMU profile. Preserve the audited script identities:
Rocky validator `69c64c51...31bd`, wrapper `b1b05d09...7931`, guest wrapper
`83f73e40...53dfe`, stop/release body `1de92368...0eb8`, and runtime observer
`ee98e653...7a5a5`.

At the checkpoint boundary the campaign identities remain launcher
PID/PGID/SID 3125264/starttime 80228730, recovered worker PID/PGID/SID
3170135/starttime 80670556, and app-server PID/PGID/SID 3170137/starttime
80670562. No diagnostic owner, QEMU or mcexec process is live. Available bytes
are 27,160,174,592 on the host filesystem and 21,905,379,328 on scratch, with
29,763,592,192 bytes of MemAvailable. The launcher-owned state remains
untouched. During post-push verification its `state.json` disappeared while
the same three processes and starttimes remained live; the run directory still
retains `console.log`, `dispatcher.txt`, `protocol.jsonl` and
`server.stderr.log`. This checkpoint neither completes nor resumes the OS goal.

Next invocation: first reconcile this exact HEAD, the three campaign identities,
launcher state, dirty submodule/source ownership and the single heavy lease.
For signals, inspect the preserved compile records, run the exact host oracle
(`mcexec -t 1 0 ... signals`, exit 37, exact `NATIVE_CORE PASS signals\n`,
empty stderr), then produce and independently review a fresh overlay and strict
manifest; never reuse either pre-existing `ndcs` path. For shutdown, bind a lean
exact source tree and define the missing before/after procfs, mapping and reserved
resource contract before preparing a separately reviewed Rocky execution packet.
Run one current-candidate boot/workload/stop diagnostic first, retain its
one-cycle limitation, then add and review the recreate cycle. This invocation
still has three real diagnostic guest applications and zero current-candidate
kernel builds; formal counters remain 0/273, 2/4, 6/130, 350/10,000 and 0/7.

Continuation checkpoint 49, 2026-09-28: signals diagnostic preparation and its
separate execution review now pass, but no privileged/runtime command has yet
run. The static signals collector is `e1c7b50e...cdea`; the corrected Linux
payload oracle exits 37 with exact 25-byte `NATIVE_CORE PASS signals\n` stdout,
empty stderr, exact reap and empty residual inventories. The derived initramfs
is `9065d03b...e7ef91`; the strict manifest is `99482694...5c2d4` and
`bound_manifest` passes. Independent artifact review replays the exact base
prefix and all 61 members with complete userspace ELF closure. The original
invented-literal observer failure is preserved without weakening the oracle.

Independent execution review returns `PASS_EXACT_ONE_SHOT_EXECUTION_RELEASE`
for packet `86528f64...5663`, parent `ndcs-20260928-7`, nonce
`c113ad500484ce6fc89659eee237c8ce` and only the release record's exact
15-element sudo-A command. The generated QEMU argv has 42 exact elements and a
100-byte QMP pathname. Earlier `ndcs` parents 1, 2, 5 and 6 remain forbidden.
The release retains the pinned four-CPU/12-GiB/no-swap/no-network/512-task
container, 300/360-second deadlines, QEMU/image gate, all process/container
identity and cleanup joins, and uncertainty lock retention. Source checkpoint
`f8941f1b...be0b` matches the live origin ref and all six runtime source blobs.
The packet, preparation and release still require this checkpoint's push and
fetched-blob verification before one fresh preflight and execution.

The shutdown lane also advances without claiming runtime behavior. New pure
`native_shutdown_observer.py` at `c86c8190...c94a6` plus tests
`2612f442...15c77` passes seven tests and independent hostile review after one
bounded correction. The rejected first candidate accepted IRQ-affinity drift
and self-supplied expectations. The corrected schema binds independent process,
procfs content-digest, device/sysfs, module/refcount/holder, reserve, CPU,
IRQ-affinity and policy expectations across seven ordered lifecycle phases;
affinity, procfs, starttime and numeric-node mutations all reject. It remains a
source-only validator pending Rocky integration.

A standalone lean Rocky source stage is preserved at
`/home/holden/mckernel-work/scratch/rocky-lean-source-20260928-2`: outer
`f8941f1b...be0b`, clean campaign-authored nested IHK `21a0d1e...5f8c`, all
other exact recursive submodules, 8,420 files and 277,737,472 allocated bytes.
Its canonical tar digest is `0804ffc6...ae4`; root Git is read-only so the
validator takes its initialized-submodule branch and cannot reset the intentional
IHK plus-status. Independent review returns `PASS_WITH_EXACT_LIMITATION`: the
partial object store has 3,135 missing promisor objects, so any packet must
forbid historical/tree/blob traversal and lazy fetch. The reviewed validator,
build and source-retirement path consume present worktree/build files and only
the frozen safe Git operations. Two failed clone strategies are preserved in
launcher output; neither left a partial directory.

Next: commit, push and fetched-blob verify the signals preparation, packet,
release, observer source/tests, lean-source records, tracker and this cursor.
Then remeasure at least 16/12 GiB disk plus RAM headroom; reconcile the three
campaign processes and exclusive heavy lease; prove owner/QEMU/mcexec/container
absence; authenticate the development lock and every released byte; verify all
three signals paths remain absent; create the parent once as uid/gid 1000 mode
0700 and consume the exact released command once with no retry. Preserve raw
bytes/status/logs/identities/teardown for independent evidence review. In
parallel after that bounded runtime, integrate the reviewed seven-phase observer
into a Rocky packet; no Rocky build or shutdown run is yet released. This
invocation has zero new real guest applications and zero current-candidate
builds so far. Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and 0/7;
whole-OS acceptance remains incomplete.

Continuation checkpoint 50, 2026-09-28: the launcher requested shutdown after
the exact released signals diagnostic completed, so no further task was
dispatched. The sole active child finished its bounded independent raw-evidence
join and returned `PASS_DIAGNOSTIC_PROTOCOL_EVIDENCE`; all children are now
closed. The consumed attempt is `ndcs-20260928-7`, nonce
`c113ad500484ce6fc89659eee237c8ce`. Its inner result is `d9941db3...d59d`,
outer result `6202a1ee...ecd0`, capture binding `cf3cb00d...035e`, serial
`84765e33...ad3e`, QMP transcript `44339b2f...d2cf4` and debugcon
`bd87db77...6685`.

The hash-bound `baseline.core.signals` fixture exits 37 with exact 25-byte
`NATIVE_CORE PASS signals\n` stdout, empty stderr, both EOFs and empty procfs.
Its own assertions establish blocked/pending SIGUSR1 delivery, mask operations
and two alternate-stack handler invocations with successful returns. Exact
review replays 23 deliveries, 22 returns and 11 routes; terminal `exit_group`
has no return. PID/TID 255 is published and deleted, worker 256 retires, the
initial retirement `-11` is followed by success, pager handle 20 releases four
references to zero and process release reports cleanup errno zero. This is not
a complete signal-event trace or general signal qualification.

All 673 QMP requests have matching successful replies. Guest shutdown precedes
stopped status and acknowledged quit; QEMU identity 10/10/10 starttime 83268932
is exactly reaped with controlled return -9. Thirty Docker client records are
exactly reaped; the reviewed profile passes, the container exits zero without
OOM, authenticated removal succeeds and three final lookups are empty. No
owner, QEMU or mcexec remains, and the development lock is free. Module-signature
taint, negative pathname/rseq results and the transient retirement retry remain
visible. The additive success record is
`docs/verification/stability-native-diagnostic-signals-success-20260928-1.json`.
Its conservative `mckernel_application_executed=false` and
`application_acceptance=false` fields remain correct: this is one real
diagnostic guest application, not formal application, M04, production or OS
acceptance.

At shutdown the campaign identities remain launcher PID/PGID/SID
3125264/starttime 80228730, recovered worker PID/PGID/SID 3170135/starttime
80670556, and app-server PID/PGID/SID 3170137/starttime 80670562. Available
bytes are 27,073,064,960 on the host filesystem and 21,613,768,704 on scratch,
with 29,733,634,048 bytes of MemAvailable. Raw inner/outer evidence and the
lean Rocky source stage remain preserved. This invocation now has four real
diagnostic guest applications (memory, files, threads and signals) and zero
current-candidate builds. Formal counters remain 0/273 applications, 2/4
narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7 language
gates. This checkpoint neither completes nor resumes the OS goal.

Next invocation: reconcile this exact pushed HEAD, campaign identities, dirty
submodule/source ownership and exclusive heavy lease. Then bind the reviewed
seven-phase shutdown observer to the 278-MiB lean Rocky stage and exact
`mcstop+release-smp.sh.in` lifecycle in a fresh, separately reviewed packet.
Freeze the stage's 3,135-missing-object promisor limitation: forbid historical,
tree or blob traversal and lazy fetch; preserve nested campaign-authored IHK
`21a0d1e...5f8c`. The next executable check is one current-candidate
boot/workload/stop diagnostic with exact before/after process, procfs, device,
module/refcount/holder, reserve, CPU, IRQ-affinity and policy snapshots. Preserve
the one-cycle limitation; independently inventory CPU/callback/internal-mapping
owners before proposing recreate-cycle or formal lifecycle credit.

Continuation checkpoint 51, 2026-09-28: the launcher requested shutdown, so
new dispatch stopped and every child agent was joined. Source inspection showed
that the retained Rocky validator is a legacy IRQ-profile path and cannot prove
the current native Linux-6.12 lifecycle. More importantly, the native backend
has no shutdown callback: a booted `IHK_OS_SHUTDOWN` currently returns `EBUSY`,
started `BootStorage` is intentionally retained, and no guest-CPU stop,
IRQ/callback drain or safe service/sysfs/procfs cancellation protocol exists.
No privileged command, container, QEMU, mcexec or shutdown fixture was run.

Bounded source work is preserved in
`docs/verification/stability-native-shutdown-source-wip-20260928-1.json`.
The exact shutdown fixture and strengthened source test compile and pass; the
seven-phase observer now distinguishes clean, live, provider-only and fully
unloaded device/module states and requires `provider_absent` after unload.
Together their 12 focused tests, Python compilation, Rust formatting and diff
checks pass. A candidate allocation-free registry `ShutdownGuard` is also
preserved with exact-generation CAS, pre-effect rollback, irreversible
retention and NotBooted commit. It is WIP only: independent review and the
configured Rust-1.92 fixture are pending, while the frozen registry digest
correctly rejects the changed source and was not rewritten.

At the checkpoint boundary the campaign identities remain launcher
PID/PGID/SID 3125264/starttime 80228730, recovered worker PID/PGID/SID
3170135/starttime 80670556, and app-server PID/PGID/SID 3170137/starttime
80670562. No diagnostic owner, QEMU or mcexec process is live. Available bytes
are 27,034,759,168 on the host filesystem and 21,613,768,704 on scratch, with
29,563,035,648 bytes of MemAvailable. Unrelated launcher-policy changes,
pycache state and the dirty nested IHK checkout remain unstaged and preserved.
This invocation still has four real diagnostic guest applications and zero
current-candidate builds. Formal counters remain 0/273 applications, 2/4
narrow fault modes, 6/130 production gates, 350/10,000 points and 0/7 language
gates. This checkpoint neither completes nor resumes the OS goal.

Next invocation: reconcile this pushed checkpoint and the three exact campaign
process identities. Independently review the registry shutdown transaction,
especially retry-from-Shutdown, reference preservation and concurrent/stale
generation behavior; run its focused fixture under the configured Rust 1.92
toolchain before any contract update. Then add a versioned native shutdown ABI
and admission/in-flight gate, followed by explicit guest CPU stop
acknowledgement, IRQ/callback drain, worker join and safe resource retirement.
Do not execute the shutdown fixture until that backend path is implemented,
built and separately released; its current deterministic result is `EBUSY`.

Continuation checkpoint 52, 2026-09-28: the first native registry shutdown
candidate failed under the retained exact Rust 1.92 toolchain, proving the
earlier host-rustc limitation was not a blocker. Irreversible guard drop had
published phase zero instead of Live/Shutdown; independent review also found
that lease close during the transaction lost a decrement and successful commit
could recycle a slot with outstanding leases. The original candidate and exact
failure are retained in checkpoint 51 and
`docs/verification/stability-native-shutdown-registry-source-success-20260928-1.json`.

After the single bounded implementation correction and an expert-requested
actual-lease regression, the registry transaction passes all 15 compiled Rust
tests and all 11 Python contract tests with exact rustc 1.92.0. Reversible drop
restores the prior status with current references; irreversible drop retains a
retryable Live/Shutdown state; commit publishes Live/NotBooted with the same
generation/current references; destruction and reuse remain busy until the
last real lease closes. Independent review returns PASS for this source scope.
The deterministic foundation contract is updated to the exact source hash but
remains TODO/no-credit. No kernel build, module, root command or guest ran.

The next active bounded implementation is an additive v5 host shutdown dispatch
that preserves v1-v4 ABIs and rolls back on a missing/failing no-effect callback.
It deliberately does not wire the SMP backend or claim guest stop. After its
compile/review, implement the separate application/service admission drain,
acknowledged stop of every guest CPU, IRQ/callback synchronization, worker join
and safe boot-resource retirement. The corrected seven-phase observer and
fixture are independently source-ready but remain prohibited from runtime until
that backend path is built and separately released. Formal counters remain
0/273 applications, 2/4 narrow fault modes, 6/130 production gates, 350/10,000
points and 0/7 language gates; the four prior diagnostic apps and zero
current-candidate builds remain unchanged.

Continuation checkpoint 53, 2026-09-28: the launcher requested shutdown, so
no new work was dispatched and all eight child lanes were joined. The bounded
native v5 shutdown-dispatch candidate is preserved at exact source SHA-256
`5b79ca8cb303cbb8df590daf1d2a9d31381b1f95978672dd1d7611b908d17144`.
It adds an allocation-free per-OS admission gate, resident application/service
owners, registry rollback on pre-effect callback failure and an additive v5
shutdown callback without changing v1-v4. It deliberately does not wire the
SMP backend or claim that guest CPUs or resources stop.

Exact Rust 1.92 execution passes the Python wrapper and all 61 compiled Rust
tests; rustfmt and `git diff --check` pass. The retained application regression
proves that a live ApplicationConnection makes shutdown return `EBUSY`, its
provider close runs before shutdown, and shutdown can then succeed. Independent
review remains BLOCK, however: after the review found that fallible connection
allocation could invoke a reentrant provider Close while the operation mutex
was held, the source now explicitly releases that mutex first, but shutdown
arrived before the requested forced-allocation-failure/reentrant-topology test
and a final independent rereview. Deterministic FileService resident-admission
coverage is also pending. The exact WIP record is
`docs/verification/stability-native-shutdown-admission-wip-20260928-1.json`.
No production/lifecycle gate, build, privileged command, container or guest is
accepted by this checkpoint.

At the checkpoint boundary the campaign identities remain launcher
PID/PGID/SID 3125264/starttime 80228730, recovered worker PID/PGID/SID
3170135/starttime 80670556, and app-server PID/PGID/SID 3170137/starttime
80670562. No diagnostic owner, QEMU or mcexec process is live. Available bytes
are 26,989,322,240 on the host filesystem and 21,613,768,704 on scratch, with
29,444,976,640 bytes of MemAvailable. Unrelated launcher-policy changes,
pycache state and the dirty nested IHK checkout remain unstaged and preserved.
Formal counters remain 0/273 applications, 2/4 narrow fault modes, 6/130
production gates, 350/10,000 points and 0/7 language gates; four real
diagnostic applications and zero current-candidate builds remain unchanged.
This checkpoint neither completes nor resumes the OS goal.

Next invocation: reconcile this exact pushed checkpoint and the three campaign
process identities. First add the forced ApplicationConnection allocation-
failure regression whose provider Close reenters `topology_query`, plus a
deterministic FileService resident-admission regression; rerun exact Rust 1.92
and obtain independent PASS review of the final source/fixture hashes. Then
implement the mapped generation-bound guest stop request/ACK protocol before
wiring the v5 callback: every assigned CPU must release-publish its exact
request sequence/generation ACK before quiescence, and timeout retains all
resources. Do not execute the shutdown fixture until stop/ACK, IRQ/callback
drain, worker join and safe retirement are implemented, built and separately
released.

Continuation checkpoint 54, 2026-09-28: the final bounded v5 host
shutdown/admission candidate passes exact Rust 1.92 execution with 62 compiled
Rust tests. Source SHA-256 is
`5b79ca8cb303cbb8df590daf1d2a9d31381b1f95978672dd1d7611b908d17144`,
fixture SHA-256 is
`3c380a7695ab5a5c48c9b74a3f5aee9b228ead6c51783b7b74256d00f15579b0`,
and driver SHA-256 is
`ad592a7dbc2629039ce02fcd9c3e6c77db18df1bcf7f3eb4714e4857f60d57d5`.
Rust formatting and diff checks pass. Independent review returns PASS for this
source/Layer-B boundary.

The allocation-failure regression forces the fallible ApplicationConnection
allocation after provider Open, observes `-ENOMEM` and null output, then proves
provider Close runs exactly once and reenters production `topology_query` with
result 73 and ordered completion. This closes the prior mutex-lifetime review
block. A second new regression registers the real FileService callbacks,
attaches one via `MCEXEC_UP_PREPARE_IMAGE`, proves shutdown returns `EBUSY`
without invoking its provider while the service lives, observes exactly one
service Close on file release, and then completes shutdown. Together with the
registry transaction, this establishes scoped host admission, rollback and
callback-owner behavior; it does not establish a native stop.

The per-CPU stop/ACK review found that the 56-byte master queue is CPU0-only and
that a regular-channel ACK cannot yet authorize resource reuse. A CPU would
still execute guest code/stack/page tables, STOP cannot park inside the packet
handler before packet release/interrupted-context rundown, and guest-allocated
Linux IRQ-work may remain queued or executing after ACK, including failed IPI
after publication. Exact blockers and the provisional non-reserved encoding are
preserved in
`docs/verification/stability-native-shutdown-stop-ack-design-review-20260928-1.json`.
Implement independently retained parking or an independently proven host reset,
plus per-generation Linux IRQ-work inventory/unpublish/drain, before freezing
the ABI or wiring v5. Timeout must retain every owner.

The stable-core tracker now marks SC-LIFE-02 partial for production-body
Layer-B admission only; SC-LIFE-03/04 and every production/lifecycle gate remain
unaccepted. No kernel/module build, privileged command, container or guest ran.
Campaign identities remain launcher 3125264/starttime 80228730, recovered
worker 3170135/starttime 80670556 and app-server 3170137/starttime 80670562;
no QEMU, mcexec or diagnostic owner is live. Host free space is 26,965,172,224
bytes, scratch free space 21,613,768,704 bytes and MemAvailable 29,322,436,608
bytes. Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and 0/7; four real
diagnostic apps and zero current-candidate builds remain unchanged.

Next: decide whether the existing x86 INIT assert/deassert reset can become the
independently confirmed CPU-reclamation transition when all guest storage stays
retained through later successful Linux `device_online`. Then implement that
reset/confirmation primitive and the Linux IRQ-work publication inventory/drain
as separate source/test boundaries. Only after both pass should the per-CPU
regular-channel STOP/ACK contract be frozen and the v5 SMP callback integrated.

Continuation checkpoint 55, 2026-09-28: the launcher requested invocation
shutdown. No new work was dispatched; all eight bounded child lanes had already
completed and are joined. The independent x86 reclamation review returns
PASS_DESIGN for an explicitly supported native AP profile only. It accepts the
existing Linux `send_init_sequence(apicid)` as an attempted reset, without SIPI,
followed by successful synchronous Linux `device_online` from the retained
known-offline identity and an exact device/APIC plus `cpu_online` recheck as the
CPU-reclamation proof. Any failed or uncertain reset/re-online retains every
owner and a per-CPU progress ledger; it never restores a guest-running state.
The exact source-bound review is
`docs/verification/stability-native-shutdown-x86-reclaim-design-review-20260928-1.json`.
No implementation, build, privileged command, module, guest or lifecycle gate
is accepted by this design result.

The separate Linux IRQ-work/callback blocker remains: guest-allocated work may
still be queued or executing after a STOP ACK, including publication followed
by failed IPI. Therefore the regular-channel STOP/ACK ABI remains provisional
and unreserved, v5 remains unwired, and the shutdown observer remains prohibited
from runtime. Next invocation: reconcile this pushed checkpoint, then add and
test a minimal export of Linux `send_init_sequence(apicid)` and a distinct
native shutdown reset/re-online journal that retains all owners and never uses
ordinary hotplug rollback. Separately audit and implement exact per-generation
IRQ-work inventory, unpublish and callback drain. Freeze STOP/ACK only after
both source/test boundaries pass independent review.

At shutdown the preserved campaign identities are launcher PID/PGID/SID
3125264/starttime 80228730, recovered worker 3170135/starttime 80670556 and
app-server 3170137/starttime 80670562. No diagnostic owner, QEMU or mcexec is
live. Host free space is 26,960,207,872 bytes, scratch free space
21,613,768,704 bytes and MemAvailable 29,334,384,640 bytes. Unrelated dirty
launcher/policy files, deleted/untracked pycache and the dirty nested IHK
checkout remain unstaged and preserved. Formal counters remain 0/273, 2/4,
6/130, 350/10,000 and 0/7; four real diagnostic apps and zero current-candidate
builds remain unchanged. This checkpoint neither completes nor resumes the OS
goal; the launcher pause is temporary until a later invocation.

Continuation checkpoint 56, 2026-09-28: the resumed launcher produced one
bounded source implementation and two exact next-boundary decisions before a
new shutdown request. The new patch
`host-kernel/kbuild/patches/0010-x86-export-secondary-reset-sequence.patch`
declares and GPL-exports the existing pinned-Linux x86
`send_init_sequence(apicid)` while retaining its void return and byte-identical
body. The first candidate failed because its second unified-diff hunk was
malformed; that exact SHA/result is retained. One bounded hunk-range correction
then passes the exact pinned-source temporary-tree application/body test and
diff check. Patch SHA-256 is
`14b2796e7ea92243808f36da663e5572f07da561570f0e7a5918d7b52fd771e3`;
test SHA-256 is
`4a32e8218a0b9048db3508c67cbee8e7522f279dd5482e0c5a1966750c0e2734`.
This is source-only: no configured kernel build, module link/load, reset,
re-online or guest ran.

The IRQ-work audit and coordinator source check confirm pinned Linux exports
`irq_work_sync(struct irq_work *)`. The next implementation is now exact: a
private per-generation LIVE/STOPPING route registry retains every per-CPU work
node and callback owner; publishers hold sender leases through enqueue and IPI
attempt; retirement blocks new leases, waits for zero publishers, synchronizes
every retained node, then unpublishes callback/master state and permits
generation reuse. Removal from the private lockless `raised_list` is forbidden.
The source-bound decision is
`docs/verification/stability-native-shutdown-irq-drain-design-review-20260928-1.json`.

The existing IRQ-work producer test passes under exact Rust 1.92. The broader
native lifecycle checker is stale against accepted additive provider ABI source
and failed before its intended negative assertions. One bounded correction was
interrupted by shutdown and remains explicitly unstaged: its 60-test rerun still
has 100 failed subcases and four errors, next stopping at the current
`compatibility_build_id` helper boundary. Its exact file/diff hashes and failure
are retained in
`docs/verification/stability-native-lifecycle-checker-wip-20260928-1.json`.
Do not accept or broadly relax that oracle; continue this same correction family
and require all intended fail-closed assertions plus independent review.

All four new child lanes are joined and no new work was dispatched after the
shutdown request. Next invocation: first reconcile the unstaged lifecycle-
checker WIP. Then implement the distinct native per-CPU reset/re-online journal
and a production-body semantic fixture; separately implement the generation-
scoped IRQ-work sender/drain registry. Neither may wire v5 or release guest
storage until independent ownership review passes.

Campaign identities remain launcher PID/PGID/SID 3125264/starttime 80228730,
recovered worker 3170135/starttime 80670556 and app-server
3170137/starttime 80670562. No QEMU, mcexec, diagnostic owner or heavy lease is
live. Host free space is 26,942,808,064 bytes, scratch free space
21,613,768,704 bytes and MemAvailable 29,276,864,512 bytes. Formal counters
remain 0/273, 2/4, 6/130, 350/10,000 and 0/7; four real diagnostic apps and zero
current-candidate builds remain unchanged. This checkpoint neither completes
nor resumes the OS goal.

Continuation checkpoint 57, 2026-09-28: the launcher requested invocation
shutdown. No new work was dispatched after that request. All ten visible child
lanes are completed/retired or interrupted/retired, and no delegated command,
heavy build, QEMU, mcexec or diagnostic owner remains live.

The replacement x86 reset boundary now keeps the raw Linux
`send_init_sequence` helper static and byte-identical. It exports only a narrow
`native_reset_secondary_cpu_via_init(apicid)` wrapper whose reviewed body is
`preempt_disable`, one INIT attempt, and `preempt_enable`; it sends no SIPI.
Three exact candidate failures are preserved (post-0006 offset mismatch,
malformed hunk counts and literal backslash-t content). The corrected patch and
one-test pinned-source contract pass. The paired native reset/re-online journal
passes six exact Rust 1.92 fixture tests after repairing the first independent
review's Send/Sync, durable-barrier, errno/status, partial-recording, diagnostic
and coverage findings. Its repaired exact hashes still require independent
rereview, and neither boundary has had a configured kernel/module build or
privileged execution. Exact files, hashes, commands and failures are recorded in
`docs/verification/stability-native-shutdown-reset-journal-wip-20260928-1.json`.

An authenticated exact-build supplement now binds the immutable source lock and
ordered 0006, 0007, 0008, 0009 and replacement 0010-v2 closure, stages with
fuzz zero, checks pre/post images, and emits/verifies a final supplemental lock.
Its first positive verify-lock run failed because the verifier compared every
intermediate writer instead of the final authenticated writer of a path. The
bounded correction passes both tests in 308.604 seconds; negative cases remain
enabled. Workflow integration still needs its exact assertion under a compatible
Python interpreter and independent authority review. The source-only record is
`docs/verification/stability-native-shutdown-reset-build-supplement-wip-20260928-1.json`.

Independent IRQ-work review remains BLOCK for reclamation. The fixed boot header
cannot be extended in place; a native-revision-gated descriptor must follow the
variable tables and publish the retained physical slot range, exact geometry,
generation and release-ready state. Sender leases must span enqueue and IPI
result. Because a failed IPI leaves its node linked and BUSY and
`irq_work_sync()` only waits, recovery must retry the exact IRQ_WORK_VECTOR to
the retained target; an offline target quarantines the generation. The exact
design result and smallest two-source/two-target fixture are in
`docs/verification/stability-native-shutdown-irq-slot-design-review-20260928-1.json`.
No STOP/ACK ABI or v5 wiring is authorized yet.

The lifecycle checker WIP remains fail-closed and unstaged for acceptance. Its
v4 provider and split BUILDID focused tests pass, but the full suite currently
stops on an exact import-order expectation (`IHK_DEVICE_REGISTRY, SharePolicy`
versus the live `SharePolicy, IHK_DEVICE_REGISTRY`), and its contract carries a
transient pre-repair `smp_cpu.rs` hash. Resume by correcting only that exact
source ordering expectation, updating the contract to the final journal hash,
and requiring the complete 60-test suite and independent review; do not relax
the oracle.

At shutdown the preserved live process identities are launcher wrapper
PID/PGID/SID 3399308/starttime 83682487, worker PID/PGID/SID
3399313/starttime 83682494, and app-server PID/PGID/SID 3399317/starttime
83682500. Host free space is 26,891,231,232 bytes, scratch free space
21,613,768,704 bytes and MemAvailable 30,957,010,944 bytes. Preserve the
unrelated launcher/policy edits, dirty nested IHK checkout and deleted/untracked
pycache state.

Next invocation: reconcile the pushed tree and these process identities. First
finish the lifecycle checker exact-order/hash correction and run its full suite.
Then independently rereview the repaired journal and build supplement, run the
remaining compatible-interpreter workflow assertion, and perform the reviewed
configured build before any privileged reset. In a separate implementation
boundary, add the generation descriptor/sender gate/failed-vector retry fixture.
Do not freeze STOP/ACK, wire v5, free guest storage or run shutdown until CPU
reclamation and IRQ/callback drain both pass independent review. Formal counters
remain 0/273, 2/4, 6/130, 350/10,000 and 0/7; four diagnostic guest apps and
zero current-candidate builds remain unchanged. This checkpoint neither
completes nor resumes the OS goal.

Continuation checkpoint 58, 2026-09-28: the launcher requested invocation
shutdown at 14:33 PDT. No new work was dispatched after that request. Every
visible child lane is completed or interrupted and retired; no delegated
command, heavy build, QEMU, mcexec or diagnostic owner is live.

Three bounded source checkpoints were already pushed and fetched at the start
of shutdown. Commit `1957dd80d6c890e919536a588c82a4fc9d4800ce`
hardens the native shutdown CPU retention journal and passed its exact Rust
1.92 caller/Send fixture plus independent review. Commit
`06aca7eacf465ea07e133bdb35a4a67db15efcc2` publishes the ABI-4 retained IRQ
work descriptor and sender gate; its Layer-B producer/alias suite and
independent bounded review pass, while STOP, drain, retry/quarantine and
runtime acceptance remain open. Commit
`c8263eb38e01cc3aa229d4045dafa1f0a2623ae8` binds the secondary-reset patch
closure into the exact-build supplement; its 48-test source/workflow suite and
independent source review pass. None of these results is a configured build,
module load, privileged reset or guest acceptance.

The current-source lifecycle/staging correction remains an explicitly
unaccepted WIP. Its stage manifest, lifecycle contract/checker, staging oracle,
host audit and focused tests are saved in this checkpoint. The current host
audit advances past the earlier provider, APIC and mcctrl boundaries and now
fails closed at `unreviewed Rust escape hatch in
host-kernel/native-rust/smp_memory.rs: extern`; exit status is 1. Do not accept
or broadly relax this oracle. Exact WIP SHA-256 values are:

```
136f597b8702732da160831244ffe64d5db10483badb4e53abb92299889e1f84  host-kernel/kbuild/stage-manifest.json
8244c9a397b8967231d93374361f557947baada400ef7401387f974c8f08f9a6  host-kernel/native-rust/ihk-smp-lifecycle-contract-v1.json
ad9e6395206c124e3a2049536ec88f4bf8929011090ea794d7c8063b8bb4a70c  scripts/ihk_smp_native_lifecycle_check.py
e94185f080ae1ad63e17eb3fd9e7f0a3e500f459820dcb0e94e517cee9d0a341  scripts/native_rust_host_audit.py
6dfd8384846b4b5e5fa164074b7dabe551f2860d1d9346a1514faa02d3c88baf  scripts/tests/test_native_rust_host_audit.py
511964896d6ada0fe4cb006a4411b9e241667de3f53cbdb002ce48ca5b1f2000  scripts/rocky_rust_staging.py
1e5857bf42e7614e6fbd72c016a39e4b35c2de48a0e60cd04b17bafbab0b8ca8  scripts/tests/test_rocky_rust_staging.py
```

The journal evidence wording is also corrected from byte equality to the exact
property tested, field equality with padding excluded; its saved SHA-256 is
`be291eb67e4d25d9f35b31dde0ad202de73380ceb08aab1a566ac9aa45383136`.
All eight campaign files pass `git diff --check`.

Preserved live launcher identities are wrapper PID/PGID/SID 3399308,
starttime 83682487; worker PID/PGID/SID 3399313, starttime 83682494; and
app-server PID/PGID/SID 3399317, starttime 83682500. At capture, host free
space is 26,805,334,016 bytes, scratch free space 21,613,768,704 bytes and
MemAvailable 30,794,465,280 bytes. Preserve the unrelated launcher/policy
edits, dirty nested IHK checkout, and deleted/untracked pycache state.

Next invocation: reconcile this pushed WIP and the process identities. Resume
the same host-audit family at the exact `smp_memory.rs` extern boundary, adding
only exact reviewed block/prefix coverage and mutation negatives. Then require
the complete host-audit, Rocky staging and 60-test lifecycle suites under the
pinned tools, followed by independent review. If those pass, remeasure capacity
and run the separately reviewed configured exact build before any privileged
reset or shutdown runtime. Continue later with failed-vector retry/offline
quarantine, callback drain, STOP/v5 integration and CPU reclamation; never free
or reuse guest storage first. Formal counters remain 0/273, 2/4, 6/130,
350/10,000 and 0/7; four diagnostic guest apps and zero current-candidate builds
remain unchanged. This checkpoint neither completes nor resumes the OS goal.

Continuation checkpoint 59, 2026-09-28: exact current-source closure is now
complete for its explicitly noncrediting source/Layer-B scope. Commit
`029b41fad7f4a30ae347c9ca282d1b8d58d46ce9` is pushed, fetched and identical at
local HEAD, FETCH_HEAD and the remote branch. The corrected integrated command
passes 196 tests in 49.128 seconds (18 host audit, 61 Rocky staging, 60 ihk-smp
lifecycle, 56 mcctrl lifecycle and one OS-runtime ownership test) with
ResourceWarning promoted to an error. The exact-build/workflow subset passes 48
tests in 24.411 seconds under Python 3.12.

The initial independent review's three blocking oracle gaps are repaired.
Memory imports are now classified at outer depth zero, every reviewed escape
order is literal rather than candidate-derived, and staging binds the complete
`LoadedImage::started` and `Drop` bodies. Independent rereview repeated the
disabled/nested import, fresh-process reordered export, duplicate/unconditional
destruction and false-started-state mutations; all reject. Its additive decision
is `stability-native-current-source-closure-independent-review-20260928-1.json`.
The full evidence inventory and original failures remain in
`stability-native-current-source-closure-success-20260928-1.json` (SHA-256
`a2fb2925cf290d5c0a49601eab15753e35706f56767fcc9a62695e9e5ad9620c`).

This does not clear the four build-output blockers or grant a configured build,
module load, reset/shutdown, guest or application result. A separate independent
review evaluated exactly one canonical workflow dispatch against commit
`029b41fa` and returned BLOCK; no heavy lease has started. Preserved launcher identities remain
wrapper 3399308/starttime 83682487, worker 3399313/starttime 83682494 and
app-server 3399317/starttime 83682500. No QEMU, mcexec or diagnostic owner was
live at reconciliation. Host free space was 26,758,045,696 bytes, scratch free
space 21,613,768,704 bytes and MemAvailable 30,678,401,024 bytes.

Next executable step: repair only the specified execution-boundary defect and
seek fresh independent rereview. On PASS, execute only the exact pushed SHA,
preserve the run identity/logs/artifact and first deterministic failure, and do
one bounded correction for that failure family before escalation.
After a successful configured build, bind its exact kernel/modules to the
smallest real McKernel startup application; do not promote diagnostic results to
formal acceptance. Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and
0/7; four diagnostic guest apps and zero current-candidate builds remain
unchanged.

Independent configured-build execution review returned BLOCK for the proposed
canonical GitHub workflow dispatch, so it was not started. The job does not
enforce or read back CPUs 2-5, 12 GiB/no swap, 512 tasks or no-network; dnf and
source acquisition require network in the same job; success also schedules the
FP-0006 and RK-006 downstream jobs; and no exclusive owner, disk-floor admission
or terminal retirement receipt binds the lease. The bounded correction is an
explicit two-boundary owner: authenticate immutable preparation inputs, then run
only one offline constrained build with complete partial-failure retention.

The first preparation, runtime-owner and offline-driver candidates remained
unsafe after one bounded correction: preparation tests errored and trusted
claims, the owner could mishandle a live timeout, and the driver could PASS
without kernel/module artifacts. Following the convergence rule, the family was
escalated instead of iterating weakened drafts. The expert replacement preserves
the exact workflow bodies and passes 32 focused tests in 0.433 seconds, all six
`py_compile` checks and `git diff --check`. Stateful tests cover actual-limit and
mount mutation, exclusive lease/retirement, timeout and uncertain-create paths,
RPM/tool/OS drift, exact workflow-body extraction, phase failures and missing or
mutated artifacts. A real subprocess preserves partial output and exit 37.

This source-only infrastructure result is recorded in
`stability-native-exact-build-boundary-source-success-20260928-1.json`; the
original execution BLOCK is retained in
`stability-native-exact-build-execution-review-block-20260928-1.json`. The local
Rocky base resolves to image ID `sha256:0b5329d8...9012796`; the cached SRPM,
archive and baseline config rehash to their exact recorded identities. No
container or build has run. Next: push this source checkpoint, create a clean
self-contained candidate checkout and manifest, and obtain fresh independent
review of the networked preparation capabilities/cleanup. Preparation and the
offline heavy build require separate releases.

The first full-manifest attempt then failed safely on three unrelated gitlinks
that are tracked directories rather than regular files. No manifest was emitted
and no container ran. The bounded correction binds every top-level gitlink by
its exact Git object ID, recursively binds the consumed ihk checkout, and leaves
unconsumed submodules unmaterialized. All 12 offline-driver tests and syntax/
diff checks pass after the correction. The first asset extraction command also
found host `rpm2cpio` unavailable; the already retained debrand asset was instead
hardlinked and rehashed (`080bbc72...6b144`) for later in-container comparison
against the pinned SRPM.

The corrected clean candidate and manifest now pass real input verification.
`/home/holden/mckernel-exact-candidate-c140d23f` is clean at commit `c140d23f`
with ihk `3114d9e`; the 1,134,361-byte manifest binds 8,897 regular/symlink
entries, four exact gitlinks, four source assets and driver SHA-256
`5bf7dca3...bf01f`. Its SHA-256 is `05fdf00c...9f35`, with a deterministic
compressed committed copy SHA-256 `6803a253...c6f18`. Evidence is
`stability-native-exact-build-inputs-success-20260928-1.json`. A fresh
independent reviewer is evaluating only the networked, source-free tool-image
preparation command; no Docker container or heavy build has started.

That independent preparation review returned BLOCK on one failure-evidence gap.
`Docker.call` buffered `docker exec` output, so SIGTERM during dnf could leave the
lease while losing already-emitted transaction bytes; container logs cannot
recover exec output. The original decision is retained in
`stability-native-exact-image-preparation-review-block-20260928-1.json`. One
bounded correction is active: file-backed streaming from the first byte and
signal-driven bounded retirement/receipt, with real SIGTERM/SIGINT regressions.
No preparation command has run.

The bounded correction passes 43 focused tests in 5.269 seconds. Real CLI
subprocess tests cover SIGTERM, SIGINT and SIGKILL for both owner paths: emitted
stdout/stderr bytes are file-backed before the signal, orderly signals produce
atomic failure receipts and bounded cleanup, uncertain retirement retains the
lease, and SIGKILL still leaves first bytes recoverable. The raw log is
`evidence/stability-native-exact-boundary-corrected-tests-20260928-1.log.gz`
(SHA-256 `acfa09a2...bd73f`). This correction still requires fresh independent
execution rereview before preparation.

After the signal correction was pushed at `d0947e0c9688106ba853e5846afc63bc94deec03`,
the clean candidate and complete input manifest were regenerated rather than
reusing the earlier hardlinked checkout. The candidate is clean with ihk
`3114d9e`; 8,899 files and four gitlinks pass real `verify_inputs`. The live
manifest SHA-256 is `6b727167...590c8`, and its committed compressed copy is
`evidence/stability-native-exact-input-manifest-d0947e0c-20260928-1.json.gz`
(SHA-256 `545df87d...9f0f7`). The superseded c140 manifest is retained as original
pre-correction evidence. Next: independent rereview of the exact d0947e0c
preparation boundary; no container has run.

Continuation checkpoint 60, 2026-09-28: independent rereview now PASSes only
the exact d0947e0c source-free image-preparation boundary. The reviewer verified
the clean candidate and ihk identities, exact source/test hashes, the 43-test
raw log and the corrected first-byte output, orderly signal, bounded retirement
and lease-retention controls. The additive decision is
`stability-native-exact-image-preparation-review-success-20260928-1.json`; the
original c140 BLOCK and all correction evidence remain unchanged.

The launcher requested a checkpoint immediately after the review completed, so
the released preparation command was deliberately not started. No exact-build
output, evidence or lease target exists; no preparation container, heavy build,
QEMU or mcexec owner is active. The clean candidate remains
`d0947e0c9688106ba853e5846afc63bc94deec03` with ihk
`3114d9e7101ad52030eb3effa849a5c108972a1f`. Preserved launcher processes are
wrapper PID 3399308 (starttime 83682487), worker PID 3399313 (starttime
83682494) and app-server PID 3399317 (starttime 83682500). All child review and
implementation lanes are complete; none owns a live operation.

Next executable task after a subsequent launcher continuation: perform a fresh
preflight of the exact clean candidate and manifest, absent output/evidence/lease
targets, pinned Rocky digest and local image ID, conflicting owners, and the
16-GiB host / 12-GiB scratch / 16-GiB MemAvailable floors. If all checks pass,
run exactly the released preparation command recorded in the PASS decision and
retain every command capture, status, inspection, receipt and owner identity.
After successful terminal retirement and receipt validation, checkpoint the
prepared image and obtain a separate independent execution release for the
offline heavy build. Do not infer build, module, guest, application or OS
acceptance from the preparation release. Formal counters remain 0/273, 2/4,
6/130, 350/10,000 and 0/7; four diagnostic guest apps and zero
current-candidate builds remain unchanged.

Continuation checkpoint 61, 2026-09-28: the independently released exact
source-free image preparation executed once and PASSed. The command exited zero,
installed and observed the exact Rocky 10.2 package/tool closure, retired and
removed container `mckernel-tools-164c861b277a47b4be3d221a196b2065`, and removed
its lease. The immutable prepared image is
`sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d`.
The image receipt SHA-256 is `18225919...8172`; all 59 receipt-bound evidence
files rehash, all 18 Docker command records exited zero, and the reviewed stop
of the sleep entrypoint is terminal exit 143, running false and OOMKilled false.
The complete 79-entry preparation capture is retained at
`evidence/stability-native-exact-image-preparation-d0947e0c-20260928-1.tar.gz`
(SHA-256 `3094e94c...59d9`, 47,704 bytes). The additive result is
`stability-native-exact-image-preparation-success-20260928-1.json`.

Three lifecycle-checker edits initially propagated into the hardlinked d094
candidate while preparation was running. The preparation had no source mounts,
so those bytes never entered its image. The links were broken, exact d094 bytes
were restored, the candidate returned to zero status entries, and complete
8,899-file `verify_inputs` PASSed again. The first post-run inventory helper and
terminal assertion were also corrected without repeating privileged execution:
the former used the wrong working directory, while the latter incorrectly
expected the intentional sleep-container stop to exit zero rather than 143.
Both original observer errors are retained in the preparation result.

A suspected duplicate Docker start was likewise an observation error: two
overlapping `sed` ranges printed the same line 330 twice. Direct source
inspection proves exactly one start immediately followed by one wait. A new
regression freezes that lifecycle; all 21 owner tests pass in 2.740 seconds.
The compressed raw log is
`evidence/stability-native-exact-owner-single-start-tests-20260928-1.log.gz`
(SHA-256 `19f6e428...d049`). No configured kernel build has started.

Fresh build admission found a real host boundary blocker before request
creation: uid 1000 is not in the Docker group and direct access to
`/var/run/docker.sock` is denied, while the reviewed owner rejects uid 0. An
independent privilege review BLOCKed a simple `sudo -A docker` prefix because
SIGKILL is not reliably relayed to an elevated Docker descendant. One bounded
correction is active: retain the unprivileged owner and container UID, elevate
only an immutable absolute Docker client command, pass only the inherited
SUDO_ASKPASS field without logging it, use catchable TERM plus bounded client
retirement, retain the lease on every uncertain elevated descendant, and bind
the actual daemon endpoint. No offline-build execution release exists yet.

The first elevated-client correction passed 35 tests but independent rereview
returned BLOCK: a sudo wrapper killed during ordinary wait could exit negative
without descendant classification, then a surviving root Docker client could
start the container after cleanup had released its lease. The additive BLOCK is
`stability-native-exact-owner-sudo-review-block-20260928-1.json`. Expert
escalation first reproduced the defect with three tests and seven failures, then
made negative sudo-wrapper classification cover ordinary completion,
already-exited and post-TERM paths. Client uncertainty is sticky across later
container cleanup and prevents both `retired=true` and lease removal. The
original extracted log is
`evidence/stability-native-exact-owner-negative-exit-original-failure-20260928-1.log.gz`
(SHA-256 `5264b23e...c03`).

The corrected owner/preparation suites pass 39 tests in 5.535 seconds; the raw
log is `evidence/stability-native-exact-owner-negative-exit-tests-20260928-1.log.gz`
(SHA-256 `7c2e2c55...8229`). Owner SHA-256 is `63ed1c4a...5602` and test
SHA-256 is `831c84a6...1afd`. Final independent rereview PASSes the source
boundary and declares one exact offline build eligible only after a clean
pushed/fetched checkpoint plus exact request, identity, fresh-path, exclusive
owner and resource preflight. The decision is
`stability-native-exact-owner-sudo-review-success-20260928-1.json`. No sudo,
Docker or build was used for this correction or review.

In the disjoint lifecycle lane, the initial import-order oracle correction
exposed further stale contiguous snapshot/commit expectations. The unchanged
production detach retains its Unpublishing guard, checks both reference counts,
executes the retained callback before commit, commits Vacant, then clears the
callback identity. The 76-test failure is preserved at
`evidence/stability-native-ihk-lifecycle-oracle-correction-failure-20260928-1.log.gz`
(SHA-256 `b20ebb6f...43c`). Independent expert review authorizes only a bounded
checker/test formatting correction; whole-suite acceptance remains BLOCKED on
separately reviewed contract/source identity closure. No Rust production edit
or runtime credit follows.

Lifecycle phase 1 now passes five dispatcher-replayed focused tests with the
pinned Rust 1.92 compiler path. The two checkers use function-local,
rustfmt-insensitive active-code matching for snapshot/drain/exit/commit/callback
clear ordering, and the negative tests reject wrong receivers/handles, weakened
guards, inversions and comment/string decoys. Evidence is
`stability-native-ihk-lifecycle-oracle-phase1-wip-20260928-1.json` and
`evidence/stability-native-ihk-lifecycle-oracle-phase1-tests-20260928-1.log.gz`
(SHA-256 `029685e3...2118`). The full suites remain intentionally fail-closed
on the separately reviewed stale contract/source identity closure.

Next executable path: commit, push and verify the reviewed owner bytes and
preparation checkpoint; then create the exact fresh request, revalidate all
identities/resource floors/owners and run one offline build under the conditional
release. Preserve the prepared image and receipt. After a successful build,
bind exact bzImage/modules/image,
regenerate the startup packet, obtain a separate one-shot runtime release, and
run only the smallest `startup.argv-empty` diagnostic while capturing exact
bytes, exit, kernel logs and teardown. Formal counters remain 0/273, 2/4,
6/130, 350/10,000 and 0/7; four diagnostic guest apps and zero
current-candidate builds remain unchanged.

Continuation checkpoint 62, 2026-09-28: the conditionally released exact
offline build was invoked exactly once and failed safely before compilation.
The offline driver's first identity command found that `/src/.git` points to the
host linked-worktree metadata at
`/home/holden/mckernel/.git/worktrees/mckernel-exact-candidate-d0947e0c`, which
was not mounted in the source-free container. `git rev-parse HEAD` therefore
failed in phase `identity`; the driver executed zero build commands, emitted no
outputs or partial outputs, and returned exit 1. This is the first failure in
the offline-container linked-worktree-metadata family. The released request
does not authorize an unchanged retry.

The original evidence root remains
`/home/holden/mckernel-exact-build-evidence-d0947e0c-1`. Its deterministic
committed archive is
`evidence/stability-native-exact-build-identity-failure-d0947e0c-20260928-1.tar.gz`
(SHA-256 `da36c9ec...698c0`, 8,324 bytes), and the additive result is
`stability-native-exact-build-identity-failure-20260928-1.json`. The owner was
PID 3488858/starttime 84850867 with nonce
`c75243e3228b4afd9fe62543e98492fb`; it has exited. Failed container
`mckernel-exact-272a777b73aa4a5185f607bfa8fad490`, ID
`110dfe01e3fb5dea16c30911f3589dc49137dcaaff905a66dd4c0a6f731799b0`,
is deliberately retained exited with code 1, PID 0, running false and
OOMKilled false. The owner proved retirement and removed the lease. The clean
candidate still has zero status entries, and the output root remains empty.

Shutdown checkpoint state: no heavy build, guest or child-agent operation is
active. All child lanes are complete. Preserve launcher wrapper PID 3399308
(starttime 83682487), worker PID 3399313 (starttime 83682494) and app-server
PID 3399317 (starttime 83682500); the launcher owns their pause/continuation.
Do not remove the failed container or original evidence during the next
continuation.

Next executable task: apply the one allowed bounded correction for this failure
family by making the clean candidate's Git identity self-contained inside
`/src`, or by binding the exact required Git metadata read-only without exposing
unreviewed host state. Add a cheap local regression that reproduces the linked
worktree `.git` indirection and proves identity plus complete manifest checking
inside the reviewed mount layout. Then create fresh attempt-2 output, evidence,
lease and request paths, remeasure capacity and identities, and obtain a new
independent one-shot execution release. Do not retry attempt 1 unchanged.
Lifecycle full-suite closure remains separately blocked on semantic review of
the stale provider/source contract. Formal counters remain 0/273, 2/4,
6/130, 350/10,000 and 0/7; four diagnostic guest apps and zero successful
current-candidate builds remain unchanged.

Continuation checkpoint 63, 2026-09-28: shutdown joined all child lanes and
preserves a source-only bounded correction plus its independent BLOCK. The new
standalone-metadata helper transactionally replaces linked main/IHK Git
metadata, the owner rejects external Git indirection before lease acquisition,
and the existing six-mount boundary is unchanged. The first local regression
failed because reduced metadata omitted a tracked symlink blob; that original
failure is retained at
`evidence/stability-native-exact-standalone-metadata-correction-failure-20260928-1.log.gz`
(SHA-256 `7a0f4775...bf2f0`). The one bounded correction installs the exact indexed
symlink blobs. A combined 51-test run then PASSed the metadata helper, owner,
image-preparation and three focused lifecycle checks; its retained log is
`evidence/stability-native-exact-standalone-metadata-tests-20260928-1.log.gz`
(SHA-256 `e0c567eb...e34e`). No Docker, build or guest ran.

Independent review nevertheless BLOCKs both actual candidate conversion and
attempt-2 eligibility. The unchanged exact workflow runs
`scripts/x86_64_shared_abi.py --check`, which requires `git show` access to
historical main commit `f2eb735212e6ab0494e638497e80d9ae78b2848e` and four
regular blobs: `CMakeLists.txt`, `kernel/include/syscall.h`,
`executer/include/uprotocol.h`, and `executer/kernel/mcctrl/mcctrl.h`. The
reviewed reduced metadata contains the current commit/tree/index and symlink
blobs but not that historical closure. Its relocation regression therefore
does not cover every real workflow consumer. The complete additive record is
`stability-native-exact-standalone-metadata-wip-20260928-1.json`. Preserve the
failed attempt-1 container and archive unchanged; the actual d094 candidate was
not converted.

The disjoint lifecycle lane adds an explicit positive regression for the
unchanged `{SharePolicy, IHK_DEVICE_REGISTRY}` import and multiline detach
ordering. Five focused tests pass. No Rust production source changed, and the
complete lifecycle suites remain fail-closed on separately stale source and
contract identities; this earns no runtime or gate credit.

Shutdown process identities remain launcher wrapper PID 3399308/starttime
83682487, worker PID 3399313/starttime 83682494 and app-server PID
3399317/starttime 83682500. No child agent, heavy build, guest, QEMU or mcexec
operation is active. Host free space is about 24 GiB, scratch free space about
21 GiB and MemAvailable about 28.3 GiB; the configured floors still pass, but
must be remeasured before heavy work.

Next executable task after a subsequent launcher continuation: escalate the
second correction to an expert, inventory every Git consumer actually invoked
by the exact offline workflow, and extend the self-contained metadata contract
with the exact hash-checked historical main commit/tree/blob closure. Add a
real regression proving those historical reads while original object stores
are unavailable, then obtain independent review. Only a PASS may authorize
conversion of the actual candidate and a fresh attempt-2 request with new
backup, evidence, output and lease paths. Do not repeat the current correction
unchanged. Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and 0/7; four
diagnostic guest apps and zero successful current-candidate builds remain
unchanged.

Continuation checkpoint 64, 2026-09-28: expert escalation closed the source
design defect in the standalone Git metadata candidate. A read-only inventory
bound every Git consumer actually executed by the offline adaptation. The main
metadata now retains current identity/tree/index and symlink blobs plus the
exact historical commit `f2eb735212e6ab0494e638497e80d9ae78b2848e`, seven
necessary trees and four size/SHA-1/SHA-256-bound blobs consumed by
`x86_64_shared_abi.py`. The complete local IHK object/ref closure remains, and
the pinned `3114d9e...` commit is explicitly validated. Online provenance fetch
logic is not executed by the offline adaptation.

The dispatcher replay passes 52 tests in 7.170 seconds, including hidden
original stores, real historical `git show`, missing/wrong object rejection,
current clean identity and IHK history. `py_compile` and diff checks pass. The
raw log SHA-256 is `e37ede83...c9facf`; its deterministic compressed evidence
is `evidence/stability-native-exact-standalone-metadata-expert-tests-20260928-1.log.gz`
(SHA-256 `2f90e443...72899`). Helper SHA-256 is `b68a8b5d...7a10a` and test
SHA-256 is `ef9d32cf...4a01e`.

Independent review PASSes actual candidate conversion and eligibility to seek
a separate attempt-2 release only after conversion verification. It caught one
command-level issue before execution: the initially proposed scratch backup was
on a different filesystem, so `os.replace` would return `EXDEV`. The released
same-device roots are candidate
`/home/holden/mckernel-exact-candidate-d0947e0c`, backup
`/home/holden/mckernel-exact-metadata-backup-d0947e0c-1`, and evidence
`/home/holden/mckernel-exact-metadata-evidence-d0947e0c-1`; both destinations
are fresh and all relevant parents report device 66306. The exact source record
is `stability-native-exact-standalone-metadata-source-success-20260928-1.json`.

No conversion or build has run at this checkpoint. Next execute the released
conversion exactly once, preserve its backup and receipt, then verify installed-
only historical/main/IHK consumers, full manifest, owner admission, identities
and clean status. Only after a verified conversion and fetched checkpoint may a
fresh attempt-2 request receive independent execution review. Formal counters
remain 0/273, 2/4, 6/130, 350/10,000 and 0/7; four diagnostic guest apps and
zero successful current-candidate builds remain unchanged.

Continuation checkpoint 65, 2026-09-28: shutdown joined every child lane and
retired the only active test container. The released standalone Git metadata
conversion ran exactly once and PASSed transactionally with no rollback. Its
same-device backup, receipt and original main/IHK metadata remain at the paths
recorded in `stability-native-exact-metadata-conversion-success-20260928-1.json`.
Installed-only current and historical Git consumers, owner admission and the
8,899-file manifest passed. Independent post-conversion review accepts only the
metadata relocation and BLOCKS an attempt-2 build: d094 has deterministic stale
ioctl-registry, device-import-order and mapping source-contract bindings.

The lifecycle/runtime and mapping source corrections now pass independent final
semantic review. The corrected runtime contract distinguishes prepare failure,
effectful start failure, shutdown ownership/rollback and closed-gate reboot
semantics. The mapping contract binds exact consumers, checked boundaries,
trusted physical producers and failure propagation. The initial exact Rust
diagnostic failed only because its `/tmp` was non-executable; that original
failure is retained. The one bounded harness correction put TMPDIR on the
existing evidence filesystem without widening the reviewed profile. Attempt 2
then PASSed with Rust 1.92: the exact mapping fixture verified and 78 scoped
Python tests completed with zero failures and one intentional unconfigured
Rocky-source skip. Container `mckernel-rust-contracts-20260928-2` is absent.
Complete hashes and retained logs are in
`stability-native-lifecycle-mapping-contract-checkpoint-20260928-1.json`.

No build or guest ran. The old d094 candidate is explicitly quarantined: later
main-worktree edits propagated through shared hardlinks into six mapping/staging
paths. Preserve that dirty observation, the conversion backup/evidence and both
small restore roots; do not build or silently reuse d094. Host available space
is 25,120,907,264 bytes, scratch available is 21,611,433,984 bytes and
MemAvailable is 29,492,152 kB. Shutdown process identities are launcher wrapper
PID 3399308/starttime 83682487, worker PID 3399313/starttime 83682494 and
app-server PID 3399317/starttime 83682500. No child agent, test container, heavy
build, guest, QEMU or mcexec remains active.

Next executable task after a subsequent launcher continuation: start from the
new fetched checkpoint, create a fresh non-hardlinked clean candidate and full
manifest, install standalone metadata with fresh backup/evidence roots, and run
the complete offline source phase in the pinned image. Preserve any failure and
obtain an independent one-shot execution release before the first corrected
heavy build. If that build passes, bind its exact kernel/modules to the smallest
real startup application before proceeding through memory, file, thread and
shutdown diagnostics. Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and
0/7; four diagnostic guest apps and zero successful current-candidate builds
remain unchanged. The OS goal is paused for launcher shutdown, not complete.

Continuation checkpoint 66, 2026-09-28: the resumed launcher adopted GOAL
`76c4f5d...c0bcc3`, START `1698d342...6216c`, CONVERGENCE
`f6938bd2...3e86a` and live HANDOFF `b9d076bb...99359`, then reconciled no
active heavy lease or McKernel container. The intentionally retained failed
container `110dfe01...799b0` remains exited. The previous turn was progress, not
a wait: fetched checkpoint `2fec3948...e59a4` contained the accepted lifecycle
and mapping source closure.

The first fresh `--no-hardlinks` host clone was stopped at coordinator PIDs
3529337/3529767 when checkout reduced host free space to 8,379,637,760 bytes,
below the mandatory 16-GiB floor. The exact incomplete path contained no unique
work and was removed after HEAD verification; host free recovered to about
25.1 GB. Reflinks are unsupported. Independent resource review confirmed a
normal host clone remains inadmissible because the exact tracked checkout is
about 9.03 GB, dominated by retained evidence. The protected d094 candidate,
metadata backup/evidence, restore roots and failed container were untouched.

The missing exact-manifest generator is now implemented together with a hardened
offline consumer. Several retained candidates failed before final closure: the
initial/bounded versions omitted schema or attacks; an expert version allowed
`core.symlinks=false`, assume-unchanged bytes and racing-output substitution;
the larger correction initially normalized CR/CRLF bytes in NUL-delimited Git
paths. The accepted bytes keep path plumbing raw, bind HEAD tree/index mode,
OID and path, verify actual type/executable/blob identity independently, bind
main/IHK/gitlinks/assets/driver, and publish without replacement. Independent
real-Git review reproduced the prior attacks and now PASSes all of them.

The owner now measures declared host and scratch filesystems separately from
source/output, records bounded allocation, fails closed on traversal/type
uncertainty, and rejects tmpfs-candidate allocation plus the pinned 12-GiB
container above the aggregate 24-GiB ceiling before lease/Docker. Its first two
candidates mislabelled measurements and then omitted the aggregate/error checks;
the expert correction independently PASSes. The consolidated source run passes
80 tests with no failures; exact hashes and retained log are in
`stability-native-exact-manifest-owner-source-success-20260928-1.json`. No
Docker, build or guest ran, and this earns no acceptance credit.

Next executable task: after fetched verification of this checkpoint, obtain a
fresh independent command-level release for an exact non-hardlinked candidate
in `/dev/shm`, using a temporary shared clone only until the already reviewed
standalone metadata transaction removes all external Git indirection. Measure
tmpfs allocation, MemAvailable, host/scratch floors, backup/evidence bytes and
zero source inode overlap; generate and independently verify the canonical
manifest. Then run the complete offline source phase in the pinned image. Only
a source-phase PASS may proceed to a separate one-shot heavy-build release.
Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and 0/7; four diagnostic
guest apps and zero successful current-candidate builds remain unchanged.

Shutdown checkpoint 67, 2026-09-28: the authoritative launcher stop prevented
new dispatch and joined every child lane. The last bounded source correction
adds mandatory `memory_allocation_roots` owner admission: source and retained
backup roots must be absolute, existing, nonsymlink, canonical and disjoint;
each is measured fail-closed, and every tmpfs allocation is summed with the
pinned 12-GiB container reservation before lease or Docker activity. The exact
owner/test bytes pass 48 focused tests, `py_compile` and `git diff --check`.
Evidence is
`stability-native-exact-owner-allocation-roots-wip-20260928-1.json`.

These exact bytes have not received independent review, so the prior command-
level candidate packet remains BLOCKED. No candidate preparation, lease,
Docker operation, build or guest ran. The next continuation must independently
review owner SHA-256 `32e0c28d...e0d5f` and test SHA-256
`d4db50d2...8c3a9`; then submit a corrected command packet with durable scratch
evidence/log paths and an explicit staging/emergency tmpfs headroom bound. Only
a PASS may create a fresh candidate at the newly fetched checkpoint. Do not
reuse the earlier `78e7178c` candidate names or repeat the blocked packet.

Host available space is 25,067,454,464 bytes, scratch available is
21,611,433,984 bytes, `/dev/shm` available is 16,597,475,328 bytes and
MemAvailable is 29,074,920 kB. Retain failed container
`110dfe01...799b0` (`mckernel-exact-272a777b73aa4a5185f607bfa8fad490`),
exited with status 1. Launcher identities remain wrapper PID 3399308/starttime
83682487, worker PID 3399313/starttime 83682494 and app-server PID
3399317/starttime 83682500. No child agent, heavy build, guest, QEMU or mcexec
operation remains active. Formal counters remain 0/273, 2/4, 6/130,
350/10,000 and 0/7; four diagnostic guest apps and zero successful
current-candidate builds remain unchanged. The launcher pause is temporary;
the OS goal is not complete and was not resumed during shutdown.

Continuation checkpoint 68, 2026-09-28: the owner-allocation failure family is
closed at source level after expert escalation and three independently retained
fail-open findings. The initial sibling-backup correction omitted nested mount
allocations and ramfs; the first expert candidate mishandled stacked mounts and
root replacement; the second used Unicode whitespace parsing and failed to
revalidate an earlier root after scanning a later root. None was retried
unchanged.

The accepted owner parses mountinfo as raw bytes, binds canonical root
inode/device/type to full mount identity and major:minor, rejects stacked or
descendant mounts, counts tmpfs/ramfs, permits only reviewed ext4/xfs ordinary
storage, and revalidates every binding before `validate()` returns. The exact
owner SHA-256 is `9cb8565e...65ea2`; tests are `6bdf439f...0797f`.
The dispatcher passes 111 combined owner/metadata/manifest/offline/image tests.
Independent review passes 59 tests and every retained bypass. Complete scope,
failure history and constraints are in
`stability-native-exact-owner-allocation-final-source-success-20260928-1.json`.

Candidate preparation is conditionally released only after this checkpoint is
pushed and fetched. Use fresh commit-derived names, candidate plus backup on
`/dev/shm`, durable scratch evidence/log/manifest paths, and at least 4 GiB free
staging/emergency headroom before checkout, before conversion and afterward.
Hold exclusive source-object/mount ownership, record exact process identities,
verify clean detached main/IHK trees and distinct tmpfs inodes, require the
standalone conversion and installed-only consumers to PASS, generate and
separately verify the canonical manifest, then run `BuildOwner.validate()` only
with both candidate and backup allocation roots. No Docker/build/guest is yet
released. Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and 0/7; four
diagnostic guest apps and zero successful current-candidate builds remain
unchanged.

Continuation checkpoint 69, 2026-09-28: fresh candidate preparation for fetched
checkpoint `80b8c492...b7d0a` PASSes under the independently released packet.
The main and pinned IHK shared clones were detached, fully materialized on
`/dev/shm`, and converted to standalone metadata. All 8,896 regular tracked
files reside on tmpfs with no source inode identity. The transactional receipt,
same-device backup and durable evidence are retained; staging is absent.

Installed-only current/historical/IHK consumers pass, including the exact four
historical ABI blobs and the 163-constant/28-layout shared-ABI check. The actual
Git object/ref/config source closure is byte-metadata-identical before and after
conversion. Canonical manifest `a95019f3...3826a` was generated and separately
accepted by `verify_inputs`. Validate-only owner admission records candidate
9,065,619,456 bytes plus backup 1,327,104 bytes and the fixed 12-GiB container
reservation: 21,951,848,448 bytes total under 25,769,803,776. No lease or Docker
operation occurred. `/dev/shm` retains 7,530,528,768 bytes free, above the 4-GiB
emergency floor; host/scratch/MemAvailable floors pass.

Original observer and invocation failures remain retained: two malformed
placement observers, an overbroad launcher-log fingerprint plus one malformed
replacement, and a manifest invocation that created one untracked Python-3.8
bytecode file before correctly rejecting the dirty candidate. The exact file
identity was captured, only that disposable generated file was removed, and the
one bounded `-B` correction passed without weakening the manifest. Complete
paths, hashes and the compressed raw log are in
`stability-native-exact-candidate-preparation-success-20260928-1.json`.

Command provenance review corrected the earlier cursor: the offline driver's
five phases include the exact kernel/module compilation and artifact validation,
so there is no separately released Docker "source phase." Next obtain an
independent one-shot heavy-build release for the exact prepared request and
image receipt. Preserve any failure; no build or guest is released by this
checkpoint. Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and 0/7;
four diagnostic guest apps and zero successful current-candidate builds remain
unchanged.

Shutdown checkpoint 70, 2026-09-28: the independently released exact one-shot
build ran once and failed cleanly in phase 0 before compilation. The preserved
diagnostic is `native Rust build-surface audit failed: stage manifest must name
exactly the build authorities and locked supplemental inputs`. Owner PID
3570990/starttime 85681355, nonce `a1484c...2271`, and Docker wait PIDs
3571094/3571097 have retired; the lease is absent and the output root is empty.
The terminal non-OOM container is retained as
`mckernel-exact-917e1468d2664989aa026baf667b2b7b` (ID
`c6917efd...f9f0772`, exit 1), alongside the earlier retained failed container.
The complete receipts, command captures, terminal inspection and phase log are
archived in
`evidence/stability-native-exact-build-phase0-failure-80b8c492-20260928-1.tar.gz`;
the additive record is
`stability-native-exact-build-phase0-failure-20260928-1.json`.

This is a new deterministic source-contract failure family. Do not rerun the
unchanged request. On the next authorized continuation, first reproduce the
stage-manifest authority mismatch locally without Docker and capture the exact
expected and observed authority sets. Apply at most one bounded correction,
run focused local regressions, and obtain independent source review. A passing
correction requires a new pushed/fetched checkpoint and fresh candidate,
manifest, request, output, evidence and lease names before any new execution
review. Preserve the failed 80b candidate, metadata backup, durable evidence
and both terminal containers.

All child lanes are complete and no heavy build, guest, QEMU or mcexec process
remains active. Launcher wrapper PID 3399308/starttime 83682487 and worker PID
3399313/starttime 83682494 remain the shutdown identities. The launcher pause
is temporary; the OS goal is not complete and was not resumed during shutdown.
Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and 0/7; four diagnostic
guest apps and zero successful current-candidate builds remain unchanged.

Continuation checkpoint 71, 2026-09-28: the first phase-0 failure family is
closed at source level. The failed candidate's manifest correctly contained 21
locked inputs, but `native_rust_build_surface_audit.py` still expected 18 and
omitted `os_service.rs`, `abi/os_service.rs` and `abi/application.rs`. The one
bounded correction adds exactly those existing staging/lifecycle authorities.
Twenty-two focused tests, the direct repository audit, `py_compile` and
`git diff --check` PASS. Independent review accepts exact audit SHA-256
`bddd9a10...be9dc` and test SHA-256 `1a2726e9...d537e` for this failure family
only. Evidence is
`stability-native-build-surface-audit-correction-20260928-1.json` and its
compressed log.

Read-only recursive closure inspection found the next deterministic source
blocker before another build: the stager copies only the 21 manifest inputs and
three crate roots, while those roots unconditionally require 31 additional
compile inputs (29 Rust files and two `include_str!` assembly files). The
generated compatibility build-ID is not missing. Next implement a hash-bound
recursive module/include closure oracle, then correct the manifest/stager exact
list with omission, redirection, order and digest negatives and independent
review. Do not prepare a candidate or seek another heavy-build release until
that source closure passes at a pushed/fetched checkpoint. The failed 80b
candidate/request and both terminal containers remain preserved and must not be
reused. Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and 0/7; four
diagnostic guest apps and zero successful current-candidate builds remain.

Continuation checkpoint 72, 2026-09-28: candidate admission now rejects exact
filesystem-mode drift before a lease or Docker operation. The preserved 80b
candidate was inode-independent but inherited launcher umask `0077`: 7,342 Git
`100644` files became `0600` and 258 Git `100755` files became `0700`. This
caused the RK-006 preimage closure to differ (`d2da4c4...d575b3f` expected,
`a27144f2...395fe9d7` observed). The strict RK-006 oracle was not weakened.

The generator, offline verifier and owner now require exact `0644`/`0755`
materialization for every main and pinned-IHK regular file. Independent review
first caught umask-sensitive test fixtures and missing pre-lease validation,
then caught a missing/null/list inventory bypass. The final owner calls the
same bound verifier unconditionally before lease acquisition or Docker
construction. Ninety-eight combined tests PASS under umask `0077`; independent
real-Git probes reject all four main/IHK permission drifts with zero lease or
Docker activity. Exact hashes and the retained log are in
`stability-native-exact-candidate-mode-admission-20260928-1.json`.

The failed 80b candidate remains preserved and is not reusable. A future
candidate must be created under umask `0022` or have every tracked permission
normalized exactly from its Git index, then pass both generator and owner
admission. The separate 57-file Rust staging closure and unsafe-ledger inventory
remain in progress; no build/guest ran and counters remain unchanged.

Shutdown checkpoint 73, 2026-09-28: no new task was dispatched. The bounded
recursive-staging correction finished before shutdown. The manifest/stager now
bind 57 reached inputs (three roots, 52 Rust support files and two embedded
assembly files). The worker corrected all four concrete independent-review
findings: attribute-embedded dependencies, quoted-brace token handling,
separate reached/parsed state and explicit paths below inline modules. The four
exact regressions, three direct source checks, `py_compile` and `diff --check`
PASS on the recorded bytes. The full 114-test suite and independent rereview
remain pending, so this is WIP rather than source acceptance.

The unsafe-ledger parser WIP preserves the historical overlapping
`extern_function`/`ffi_export` identities while recognizing unique adjacent
Rust `# Safety` docs; seven focused tests pass. Its next real blocker is
`host-kernel/native-rust/os_runtime.rs:648`, and the full durable ledger digest
and source hashes are not reconciled. Do not update only the top-level digest
or claim RS-011 acceptance. Exact hashes and limitations are in
`stability-native-recursive-stage-and-unsafe-ledger-shutdown-wip-20260928-1.json`.

Next continuation: first run the complete 114-test recursive-stage suite and
obtain independent rereview of the committed correction. If accepted, close
that failure family additively. Then use an expert-reviewed bounded pass to add
genuine missing safety documentation and reconcile the full unsafe ledger plus
every affected manifest/stager hash. Only after all phase-0 source checks pass
may a fresh, correctly-moded commit-derived candidate be prepared. Never reuse
the failed 80b request; preserve its candidate, backup, evidence and terminal
containers.

No heavy build, guest, QEMU or mcexec process is active. Launcher wrapper PID
3399308/starttime 83682487 and worker PID 3399313/starttime 83682494 remain the
active shutdown identities. The launcher pause is temporary; the OS goal is not
complete and was not resumed. Formal counters remain 0/273, 2/4, 6/130,
350/10,000 and 0/7; four diagnostic guest apps and zero successful
current-candidate builds remain unchanged.

Continuation checkpoint 74, 2026-09-28: the failed 80b candidate remained
untouched while its deletion prerequisite was durably captured. Independent
review verified zero mismatches across 7,649 main blobs, 1,296 pinned-IHK blobs
and all 8,945 canonical-manifest entries. A 4,363,203-byte retention capsule
records both installed `.git` trees, both metadata backups, two unique bytecode
files, canonical manifest, request, metadata receipt and both observers. Its
372,489-byte inventory binds 924 entries; all 925 archive members verify. See
`stability-native-exact-failed-candidate-retention-capsule-20260928-1.json`.

Continuation checkpoint 75, 2026-09-28: the independently released cleanup of
the two failed-80b tmpfs roots PASSes. Two observer attempts remain preserved:
the first used a Python-3.9-incompatible string method, and the next matched host
path strings and could miss namespace bind aliases. The corrected observer binds
all 10,400 candidate and 87 backup inode identities, scans cwd/root/exe/fd and
mapped-file identities, and compares mount roots by device/filesystem coordinate.
Its exact pre-delete snapshot covered 274 processes and 19 mount namespaces with
zero permission denials and zero target references.

Only `/dev/shm/mckernel-exact-candidate-80b8c492-1` (device/inode 26/3088) and
`/dev/shm/mckernel-exact-metadata-backup-80b8c492-1` (26/13660) were removed.
Both are absent. The operation recovered 9,066,999,808 tmpfs bytes, leaving
16,597,475,328 bytes available; host and scratch retain 24,841,457,664 and
21,609,967,616 bytes. The fetched capsule and inventory hashes remain unchanged.
Both exact terminal failed containers remain exited, PID 0, exit 1 and non-OOM.

Complete observer sources, snapshots and the cleanup result are retained in
`evidence/stability-native-exact-failed-candidate-cleanup-80b8c492-20260928-1.tar.gz`;
the additive record is
`stability-native-exact-failed-candidate-cleanup-20260928-1.json`. Restoration is
from the exact main/IHK commits, recorded modes/symlinks and fetched capsule.
This cleanup enables a fresh candidate but grants no build, guest or acceptance
credit. Next finish and review the active recursive-stage/unsafe-ledger source
closure before preparing that fresh candidate.

Shutdown checkpoint 76, 2026-09-28: no new task was dispatched after the
launcher stop request, all child lanes joined, and no heavy build, guest, QEMU
or mcexec operation remains active. The bounded source integration is preserved
as WIP. Twenty-two Rust files now carry site-specific safety documentation with
an unchanged non-comment token stream. The reconciled unsafe/FFI inventory has
55 inputs and 637 sites, preserves all 156 historical mappings, and assigns 481
new pending IDs. Its inventory/check, 22 focused tests, lifecycle/mapping/runtime
source checks, `py_compile` and `diff-check` PASS. Closure digest is
`c1ae16ed...47c6`; canonical ledger digest is `e46ffbd8...1d55`.

The earlier recursive-staging bytes passed all 114 tests, but that run preceded
the final ledger/manifest reseal. Final integrated staging remains fail-closed
on one preserved deterministic mismatch: `native_rust_host_audit.py` has a
stale v5 exact escape-prefix expectation after the comment-only source changes.
Its 15 errors and four downstream assertion failures are one root family. No
shutdown correction was attempted and no passing integrated suite is claimed.
Exact hashes, checks, limitation and process/resource state are in
`stability-native-source-closure-shutdown-wip-20260928-1.json`.

Next continuation: make one bounded correction only to the host audit's exact
expected v5 escape blocks without weakening the oracle. Run the complete
114-test recursive suite, all 22 unsafe-ledger tests, direct inventory/check and
staging `--check`, then obtain independent review of the exact integrated bytes.
Only after a pushed/fetched source-clean checkpoint may a fresh correctly-moded
candidate be prepared; never reuse the deleted failed-80b request. Launcher
wrapper PID 3399308/starttime 83682487 and worker PID 3399313/starttime
83682494 remain the preserved shutdown identities. Both terminal failed
containers and the recoverable 80b capsule remain retained. Formal counters,
four diagnostic guest apps and zero successful current-candidate builds remain
unchanged. The launcher pause is temporary and the OS goal is not complete.

Continuation checkpoint 77, 2026-09-28: the phase-0 recursive staging and
unsafe/FFI source failure family is independently accepted on the exact current
bytes. The host audit now binds the complete create-v5 and topology-query Safety
prefixes without weakening exact count/order/top-level/remaining-escape checks.
Its fixture authority reseal preserves production hard locks while all intended
negative oracles execute again. The IHK lifecycle contract's sole update binds
the already-reviewed OS-runtime contract digest without changing readiness or
credit.

The authoritative fail-fast matrix embeds HEAD, exact file hashes, every
command, per-command return code and `MATRIX_RC=0`. It passes 119 recursive
staging/build-surface/host-audit tests, 22 unsafe-ledger tests and 55 IHK
lifecycle tests (196 total), plus all 16 direct checks. The ledger remains 55
inputs/637 sites; all 22 Rust files retain the exact non-comment token stream
from base `1129961b...61f`; closure is `c1ae16ed...47c6`. The optional mapping
fixture remains skipped because no configured Rust 1.92 was available.

Original harness and evidence-writer failures remain retained: unsupported
inventory output syntax, 39 fixture early-failure subcases, one stale lifecycle
contract digest, a non-fail-fast composite, and one passing but provenance-weak
log. The corrected matrix is
`native-rust-source-closure-final-20260928-2.log`, SHA-256
`944e572c...857`; the six-log archive is
`evidence/stability-native-rust-source-closure-20260928-1.tar.gz`, SHA-256
`6e9700a2...b1bb`. Exact results and limitations are in
`stability-native-rust-source-closure-checkpoint-20260928-1.json`.

This is source closure only. Rocky still reports four readiness blockers;
RS-011 remains NOT_READY, compiler-expanded capture/review is missing and
credit is forbidden. No build, module load, guest or application ran. After
this checkpoint is pushed and fetched, obtain a new command-level preparation
release and create one fresh correctly-moded commit-derived candidate under
new SHA-derived names with `umask 0022`. Never reuse the deleted failed-80b
request or paths. Formal counters, four diagnostic guest apps and zero
successful current-candidate builds remain unchanged.

Continuation checkpoint 111, 2026-09-29: corrected retention preparation
attempt 2 PASSes its single released ordinary-user invocation at commit
`38b08c31...20a3e`. Owner PID 3786420/starttime 88524458, planner
3786435/88524474, archive 3786482/88526551 and postflight planner
3786857/88527431 all exit zero and retire with their groups. Claim and lease
are absent after receipt publication. No Docker, root, build or guest ran.

Inventory `ce0c47f5...e1d10` has 10,595 exact entries: 917 capsule-required,
9,678 reconstructible and 49 safe links. Capsule `94fe0c36...712c8` is
11,591,680 bytes with 923 exact USTAR members. The second planner produces the
same inventory bytes; receipt `1d244143...e949e` binds all worker identities,
capacity samples and hashes. Raw archive `e91de69b...845df` retains all 12
scratch members.

Independent review reconstructs every archive header/payload/order/ancestor,
matches all live descendants, and verifies all 9,011 omitted regular/link blobs
from canonical main/IHK stores (7,715 + 1,296). The capsule is intentionally
not standalone: restoration requires main `67589154...fe794` in the root object
store and IHK `3114d9e7...72a1f` in `.git/modules/ihk`. No restoration ran.

Reviewer diagnostic PID 3788795 was stopped after a buffered Git-blob check
briefly reached about 17 GiB RSS, above the profile; exit 143 changed no
evidence. Bounded streaming verification then PASSed. Record
`stability-native-exact-retention-preparation-success-20260929-2.json` preserves
the result. Artifact commit `3c36091c...cf4bb` is pushed and fetched; HEAD,
upstream, FETCH_HEAD and the remote branch agree, and the four fetched evidence
blobs reproduce their recorded hashes. Next separately review a privileged
retirement packet binding both stores, exact roots, fresh
quarantine, two closure rounds and full Docker/process/mount evidence. No space
recovery, build, guest, application or formal credit is claimed.

Shutdown checkpoint 112, 2026-09-29: the launcher stop request ended new
dispatch after checkpoint 111. Every child lane is complete and joined; no
heavy owner, retention worker, build or guest remains active. Preserve launcher
wrapper PID 3399308/starttime 83682487, worker 3399313/83682494 and app-server
3399317/83682500. Preserve terminal containers `decd7cf9...c6b9` (exit 1) and
`8943e497...bc10` (exit 0), both consumed roots at device/inodes 26/25166 and
26/35798, and attempt evidence roots at scratch inodes 2907338 and 2907339.

Post-run free bytes are host 24,329,093,120, scratch 21,560,459,264, tmpfs
7,516,635,136 and available memory 20,822,495,232. The next invocation must
first reconcile these identities and verified fetched checkpoint. It may then create
and independently review the separate privileged ordinary-retirement release
described above; no root rename, deletion or cleanup is authorized by this
checkpoint. After reviewed retirement and capacity recovery, independently
review fresh candidate preparation `704f6654-1` before any heavy build. The OS
remains incomplete, current-candidate builds remain zero, real accepted apps
remain zero of 273, and this launcher pause is temporary.

Continuation checkpoint 113, 2026-09-29: retirement integration review found
that the previously reviewed helper renamed and chmodded the consumed roots but
left them owned by uid/gid 1000, violating the v7 observer's root-owned
quarantine assumption. The historical observer also accepted only the old
`68cf089a` root names. No retirement command ran.

Expert-corrected helper `2ba70074...8964e`, test `e7630fa2...20981`, current
observer `3562b1d3...53666` and test `b5f48e7b...922e4` receive independent
`PASS_SOURCE_BOUNDARY`. The helper now journals the exact released, target and
observed post-transition identities around descriptor-bound fchown/fchmod. The
observer binds device/inode/uid/gid/type/mode for every tree member and catches
root or child ownership mutation while preserving device/inode reference
matching and all v7 closure/mount checks. Python 3.8 and 3.9 each pass the same
50 dispatcher-run tests; the independent six-suite run reports 76 passes on
each. Both observer self-tests, pycompile and diff checks pass.

Record `stability-native-exact-retirement-owner-observer-source-success-20260929-1.json`
preserves the original findings and exact scope. This is source-only: the helper
remains callback-bound and no live 1000:1000 to root:root transition, census,
Docker check or deletion ran. The first packet `c27ee0e5...6324` and bounded
correction `2bd085ef...61e` were rejected; expert packet `22f19e81...80eb` was
also BLOCKed on incompatible root schemas, unbounded Git I/O, fail-open procfs
errors, incomplete interrupted-child retirement and absence of a held exclusion
through deletion. One larger coherent correction is in progress. Do not execute
or finalize it before a fresh independent source and execution review. Counts
remain zero current-candidate builds and zero accepted applications.

Shutdown checkpoint 78, 2026-09-28: no new work was dispatched after the stop
request, every child lane is complete, and no candidate preparation, Docker,
build, module, guest or application command was started. The launcher wrapper
PID 3399308/starttime 83682487, worker PID 3399313/starttime 83682494 and Codex
app-server PID 3399317/starttime 83682500 remain the active process identities.
No qemu, mcexec, native exact build, Rocky build or Docker-build command was
observed. Host, scratch and tmpfs have 24,751,034,368, 21,609,820,160 and
16,597,475,328 bytes available; MemAvailable is 29,889,921,024 bytes.

The rejected generic candidate-preparation wrapper is retained only as original
failure/review evidence in
`evidence/stability-native-exact-candidate-wrapper-rejected-20260928-1.tar.gz`
(SHA-256 `1fea2ea3...879b`). The wrapper sources themselves remain removed and
must not be revived or executed. A replacement immutable preparation-only
packet is preserved at
`evidence/native-exact-candidate-preparation-68cf089a-1.sh` (SHA-256
`7cd0555c...eed9`, 13,520 bytes). It passes `bash -n` only. It is unreviewed,
unreleased and unexecuted; syntax success grants no preparation, build or
runtime credit. The exact state and next actions are in
`stability-native-exact-candidate-preparation-shutdown-wip-20260928-1.json`.

Next continuation: independently review that exact one-shot packet before any
execution. In particular, check observer return-code handling, use of the bare
source Git directory for `cat-file`, metadata-staging scope, and the external
process/container preflight boundary. Make at most one bounded correction for a
concrete defect, then capture complete process, lease, container and capacity
preflight under a separately released privileged observation where required.
Only after review PASS and clean preflight may preparation run. A successful
preparation still requires its own checkpoint and separate heavy-build review
before Docker or the owner CLI. Never reuse the failed 80b names. Formal
counters, four diagnostic guest apps and zero successful current-candidate
builds remain unchanged. The OS goal is incomplete and the launcher pause is
temporary.

Continuation checkpoint 79, 2026-09-28: the fresh exact candidate preparation
now PASSes independently, but heavy build execution is BLOCKed on a newly
source-traced owner-lifecycle defect. The corrected immutable preparation packet
is `15f40733...7461`. It replaced the stale-HEAD dependency, fail-open closure
capture, Python-3.8 import exposure, partial umask, unjoined logger, weak mount
placement and global residue check without reviving the rejected generic
wrapper. Its independently released one-shot execution returned inner and outer
RC 0 with both log fsyncs passing.

Candidate `68cf089a` plus pinned IHK `3114d9e7` are clean under fresh tmpfs
paths. All 8,913 tracked regular files have distinct tmpfs identities; both
source Git closures remained stable. Metadata relocation, shared ABI,
`verify_inputs` and `BuildOwner.validate()` PASS. The request is
`25f820e2...576c`; measured aggregate allocation is 21,957,709,824 bytes below
the 25,769,803,776-byte ceiling. The build output/evidence roots are empty, the
lease is absent and no preparation process survives. The first preflight is
retained as an observer-only failure because procps 3.3.16 rejects `--ww`; its
host-compatible `ww` correction and the complete postflight return all zero.
Two unrelated long-running Kasper containers coexist; both failed McKernel
containers remain exited and retained.

The complete 48-member preparation archive is
`evidence/stability-native-exact-candidate-preparation-68cf089a-20260929-1.tar.gz`
(SHA-256 `78e2b5c4...4264`). Exact paths, hashes, measurements and the launcher-owned
outer-RC event are in
`stability-native-exact-candidate-preparation-checkpoint-20260929-1.json`.

Independent heavy-build review found that the exact candidate owner removes a
provisionally successful terminal container before final allocation-binding
revalidation, inventory capture, latched-signal handling and durable receipt
publication. A cleanup-time TERM or late allocation failure can therefore turn
the result into FAIL after destroying required failure evidence. No build was
released or run. Next correct this owner boundary with explicit cleanup-time
interruption and late-revalidation regressions, independently review it, commit
and prepare a new source-bound candidate before seeking another heavy release.
Do not mutate or build candidate `68cf089a-1`; preserve it and its backup until
the replacement is accepted. This continuation has zero new guest applications
and zero successful current-candidate builds. Formal counters remain 0/273,
2/4, 6/130, 350/10,000 and 0/7; the OS goal remains incomplete.

Continuation checkpoint 80, 2026-09-28: the terminal-container evidence defect
that blocked the fresh heavy build is corrected and independently PASSes at the
source/test-contract layer. `BuildOwner.run` no longer removes any container.
After a create attempt, reconciliation and cleanup are always separate reviewed
operations. Receipt truth is now tri-state: no-attempt is false, uncertain
existence/retirement is null, and retained is true only after an owned terminal
observation plus proven client retirement. A later client uncertainty preserves
the snapshot as historical, marks it non-current and retains the lease.

Owner `a8c4c9fc...9155` and tests `c96d25c0...0857` pass all 65 focused tests.
The five compatible exact-build suites pass 118 tests across metadata relocation,
owner lifecycle, image preparation, manifest generation and offline build. The
attempted sixth workflow import retains its pre-test failure: launcher Python
3.9 cannot evaluate an existing Python-3.10 union annotation in
`native_rust_runtime_evidence.py`. No oracle was weakened and no Docker/build
command ran. Exact results and independent review are in
`stability-native-exact-owner-terminal-retention-source-success-20260929-1.json`.

Next commit and fetched-blob verify these exact bytes, then release cleanup of
the now-superseded prepared `68cf089a-1` candidate only after proving no process,
mount or descriptor references it. Preserve its preparation archive and never
mutate/build it. Reclaiming that tmpfs allocation is required before a new
commit-derived candidate can fit while retaining the 4-GiB emergency reserve.
After cleanup, generate one new SHA-bound preparation packet, prepare/validate
the replacement, and seek a fresh heavy-build release. This source correction
changes no formal counter; there are still zero new guest applications and zero
successful current-candidate builds in this continuation.

Continuation checkpoint 81, 2026-09-28: the superseded prepared candidate's
small unique state is preserved before any cleanup. The 4,283,649-byte capsule
contains 920 unique supported members: both installed Git directories, the
complete metadata backup, metadata receipt, exact manifest and request. Capsule
SHA-256 is `eed1879b...80c6`; its additive record is
`stability-native-exact-prepared-candidate-retention-20260929-1.json`.

Both tmpfs roots remain present and unchanged. Deletion is held until this
capsule is pushed/fetched, a root-complete inode/filesystem-coordinate observer
reports zero permission denials and zero process/fd/map/mount references, fresh
lease/container preflight is clean, and an exact two-root deletion packet passes
independent review. Restoration uses main `68cf089a`, IHK `3114d9e7`, Git index
modes and the capsule; historical replay still needs a new execution release.
This preservation changes no build, guest or acceptance count.

Shutdown checkpoint 82, 2026-09-28: dispatch stopped on the launcher stop
request and all child lanes are complete. No cleanup, Docker, build, module,
guest or application command was started after the request. The launcher
wrapper PID 3399308/starttime 83682487, worker PID 3399313/starttime 83682494
and Codex app-server PID 3399317/starttime 83682500 remain the active process
identities. No qemu, mcexec, native-exact build, Rocky build or Docker-build
process was observed. Host, scratch and tmpfs have 24,694,710,272,
21,608,222,720 and 7,524,667,392 bytes available; MemAvailable is
21,187,031,040 bytes. The prepared candidate and backup remain present.

The first cleanup design remains rejected as unsafe; its independent review is
preserved in the agent result and must not be treated as an execution release.
The escalated source-only repair produced observer
`evidence/native-exact-candidate-live-reference-observer-68cf089a-1.py`
(SHA-256 `a1ce4fc6...615e`) and deleter
`evidence/native-exact-candidate-delete-68cf089a-1.py` (SHA-256
`74b5ec11...20b4`). They received only `py_compile`, pure synthetic assertions
and diff checking. Neither helper was executed. The deleter deliberately fails
closed because `WORKTREE_INVENTORY_SHA` is unset; a fresh post-seal observer
receipt and external lease/Docker no-bind preflight are also absent. Therefore
no deletion sequence is released, and the preserved candidate roots must not be
mutated or removed.

Next continuation: inspect and test these exact helper bytes, then define and
generate the required immutable complete inventory for both candidate roots.
It must account for every name, type, mode, byte payload and symlink target,
including ignored/untracked build entries and the complete IHK tree, while
preserving the capsule-bound Git metadata and backup. Independently review the
inventory schema, generated object and final helper hash before replacing the
UNSET pin. Only after that review PASS may a fresh per-thread/process/mount
observer, external lease/container no-bind preflight and the exact one-shot
root cleanup be considered. Preserve every partial journal and prohibit an
automatic retry. After a successful cleanup checkpoint, create a new
commit-derived candidate under new SHA-derived names and seek a fresh heavy
build release. Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and 0/7;
there are four diagnostic guest apps, zero successful current-candidate builds
and zero new guest apps in this continuation. The OS goal remains incomplete,
and this launcher pause is temporary.

Continuation checkpoint 83, 2026-09-28: the superseded-candidate cleanup
prerequisite now has independently accepted source readiness, but root deletion
is still not released. Three successively rejected designs remain preserved.
The final strategy is an exclusive cleanup lease, root-owned atomic quarantine,
helper-controlled per-thread/mount observation, and one sealed descriptor-only
verification/deletion pass with durable per-entry recovery records. Exact
observer `4a15271d...8e05` and inventory-pinned/release-unset deleter
`3803cf64...1eb0` pass their pure self-tests and independent source review.

The untouched live roots produced a fresh observational inventory in 7.9
seconds and an independent replay in 8.2 seconds. It contains 10,549 unique
rows: 10,462 candidate entries (925 directories, 9,488 files and 49 symlinks)
and 87 backup entries (39 directories and 48 files). Exact inventory SHA-256 is
`743c0564...82c0`; its deterministic committed archive is
`evidence/stability-native-exact-complete-inventory-68cf089a-20260929-1.tar.gz`
(SHA-256 `6be734da...b044`). This is preservation and cleanup infrastructure only;
it is not an atomic snapshot, deletion result, build or OS behavior.

Next construct and independently review one exact preflight/root execution
packet. It must bind the final helper, observer, inventory, release record,
boot/time, source-clean result, exact root identities and a fresh root Docker
no-bind observation. Only the released packet may fill the remaining release
pin and execute once. On failure retain the cleanup lease, journal, raw observer
streams and every surviving original/quarantine identity; never retry
automatically. After a successful cleanup checkpoint, prepare a fresh
commit-derived candidate and seek the heavy-build release. Formal counters and
the four diagnostic applications/zero successful current-candidate builds are
unchanged.

Shutdown checkpoint 84, 2026-09-28: dispatch stopped on the launcher stop
request and every child lane is joined in completed state. No cleanup, sudo,
Docker, build, module, guest or application command was run. The launcher
wrapper PID 3399308/starttime 83682487, worker PID 3399313/starttime 83682494
and Codex app-server PID 3399317/starttime 83682500 remain the active process
identities. The prepared candidate root remains dev 26/inode 14117/mode 0755/
uid 1000/gid 1000 and the metadata-backup root remains dev 26/inode 24701/
mode 0755/uid 1000/gid 1000. Host, scratch and tmpfs have 24,670,347,264,
21,606,010,880 and 7,524,667,392 bytes available; MemAvailable is
21,169,287,168 bytes.

The bounded execution-packet lane produced only a fail-closed draft:
`evidence/native-exact-candidate-cleanup-execution-68cf089a-1.sh` SHA-256
`39fbd9c2...be46` and release basis
`evidence/native-exact-candidate-cleanup-release-basis-68cf089a-1.json`
SHA-256 `d50f9840...b844`. `bash -n` and JSON parsing pass, but the packet stops
unconditionally before creating a release/preflight or invoking the helper;
its final helper/release pins remain unset. It also retains a broken indirect
fixed-input hash loop, lacks candidate/IHK clean and commit admission, enforces
too little tmpfs reserve, and the draft basis contains an impossible mutual
final-helper/release-record hash cycle. This exact draft is preservation of an
unfinished design, not independent review or root-execution authority.

Next continuation: correct the draft without executing it. Replace the hash
loop with direct checks; enforce 16-GiB host, 12-GiB scratch and 4-GiB tmpfs
floors; validate candidate `68cf089a` and IHK `3114d9e7` with hardened clean
Git checks; remove the circular final-helper/release hashes from the basis;
write and fsync the exact O_EXCL release and v2 preflight; add the single
sanitized `sudo -A` invocation and durable result capture. Then obtain an
independent exact-draft review, promote only the reviewed basis, mechanically
pin its hash in the deleter and packet, obtain a final execution review, and
commit/push/fetch those exact bytes before one fresh preflight. No automatic
retry is permitted. Formal counters remain 0/273, 2/4, 6/130, 350/10,000 and
0/7; four diagnostic applications and zero successful current-candidate
builds remain. The OS goal is incomplete and this launcher pause is temporary.

Continuation checkpoint 85, 2026-09-28: the cleanup release design now PASSes
independent source-template review without root execution. The reviewed helper
`0324772c...9c80` hashes and parses the same release bytes, rejects duplicate
keys and scalar type aliases, validates the exact v3 release/v2 preflight, and
normalizes only its release pin plus the packet's two final pins. Reviewed
packet `c9303cfb...562c` fixes the retention-record path, direct input hashes,
zero-container capture, ordinary QEMU matching, 16/12/4-GiB capacity floors,
hardened candidate/IHK cleanliness, BOOTTIME-bounded admission, raw O_EXCL
release/preflight writes, self-normalization before sudo, a TERM exception path
and one sanitized helper attempt. Draft basis `a6983f74...f593a` contains no
final/self hash cycle and remains fail-closed with DRAFT status, an unset source
checkpoint and unset final pins.

Ten pure regressions PASS, including an executable temporary final-join model:
the helper accepts exactly the normalized template/basis/helper/packet closure
and rejects duplicate JSON keys and integer-for-boolean substitution. See
`stability-native-exact-cleanup-template-readiness-20260929-1.json`. No cleanup,
sudo, Docker, build, module, guest or application ran; both tmpfs roots remain
untouched. Next commit/push/fetch this exact template. Then make only the four
review-authorized substitutions, rerun the checks, obtain an independent exact
mechanical-diff/execution review, commit/push/fetch final bytes and remeasure
the fresh preflight before the single root attempt. Counters remain unchanged.

Continuation checkpoint 86, 2026-09-28: template checkpoint
`5c7f598bcde4660000296500468fb0abcf7a2602` is pushed and fetched. The only
execution-artifact changes after it are independently verified as mechanical:
basis source/status, helper release pin and packet helper/release pins. Final
helper is `5500e77e...c753`, packet `d3d4c064...5729`, basis
`704c8409...7323`, and ten-test suite `aebc02ec...d9f7`; all local checks PASS.
Independent review conditionally releases exactly one non-root invocation of
the packet after these exact final bytes are committed, pushed and fetched.
See `stability-native-exact-cleanup-execution-release-20260929-1.json`.

The released command is `/usr/bin/bash` on the exact packet from the repository
root. Its gates must freshly prove branch/source bindings, candidate/IHK clean
commits, exact roots and inputs, 16/12/4-GiB capacity, no owner process and no
running-container bind before creating the v2 preflight and making one sanitized
`sudo -A` helper attempt. Timeout is 300 seconds with 10-second kill grace. Do
not invoke the helper directly, bypass a gate, retry, roll back or delete any
failure evidence/quarantine. Cleanup success is still unproven and earns no OS
acceptance credit.

Continuation checkpoint 87, 2026-09-28: the one released cleanup packet ran
exactly once and failed closed in 6.0 seconds. All non-root admission checks
passed. The helper acquired and retained the root lease, validated the full
inventory, sealed both roots root:root mode 0700 and atomically renamed them to
their exact quarantine names. It closed its target descriptors, then stopped
before any `delete-entry` phase because the post-seal observer returned FAIL.
Original paths are absent; quarantine dev/inode identities 26/14117 and
26/24701 remain intact. No retry or rollback occurred.

The original failure is preserved in
`stability-native-exact-cleanup-failure-20260929-1.json`: journal
`6bf12958...ebe`, observer result `8eb6762e...c06`, observer progress
`e9e65262...4d68` and lease `69ced239...47e3`. Five complete rounds each saw
815 tasks, zero permission denials, 815 systematic `map_files` churn records and
48 `missing-or-ambiguous-canonical-dev-shm` records. There were no deletion
phases. Source inspection shows the observer classifies every vanished/absent
`map_files` probe on a still-live task as churn and requires every isolated
mount namespace to expose exactly one host-canonical `/dev/shm`; these are
observer semantics defects, not cleanup success evidence.

Next fix that observer with synthetic positive and negative regressions. Then
independently review a quarantine-resume protocol that binds the retained lease,
journal prefix, exact quarantine identities, inventory and a fresh corrected
zero-reference observation. It must use a new recovery packet/evidence identity,
never rerun the failed packet, never roll back the quarantine and release the
old lease only after verified terminal deletion success. No build can start
while this retained lease/root state remains. Counters and application/build
counts remain unchanged.

Shutdown checkpoint 88, 2026-09-28: dispatch is stopped and every child lane is
joined in completed state. No recovery, sudo, Docker, build, module, guest or
application command ran after the stop request. Launcher wrapper PID
3399308/starttime 83682487, worker PID 3399313/starttime 83682494 and app-server
PID 3399317/starttime 83682500 remain live. Preserve the old root lease
`native-exact-build-lease-68cf089a-1.json` SHA-256 `69ced239...47e3`, the old
journal `6bf12958...ebe`, and both root:root 0700 quarantines at dev/inode
26/14117 and 26/24701. The originals remain absent. Do not rerun the old cleanup,
roll back either quarantine, or remove the old lease.

The corrected observer `e6f46761...e4d` and its ten synthetic regressions
`22043101...eb78` have independent source-review PASS. A distinct recovery
helper `ad0db6b...f3b`, packet `c59ed2d4...1473` and DRAFT basis
`fec0e99d...9a6` are preserved but are non-executable and have no independent
recovery review or release. Their nine-test regression suite currently FAILs
closed: two fixture metadata/descriptor identity mismatches and one expected
error-string mismatch; helper self-test, Python compilation, shell syntax, JSON
parsing and `git diff --check` pass. No recovery evidence was promoted.

Next continuation must first correct those three local regression failures
without touching protected state, rerun the pure checks, and independently
review the exact helper/packet/basis against the retained failure. Only after a
pushed/fetched template checkpoint may it mechanically bind final hashes and
seek a separate execution review. A released recovery must use its new O_EXCL
claim/journal, two clean corrected-observer rounds, descriptor-bound deletion
and old-lease removal only after all four protected paths are absent. Formal
counters remain 0/273, 2/4, 6/130, 350/10,000 and 0/7; four diagnostic apps and
zero successful current-candidate builds remain. The OS goal is incomplete and
the launcher pause is temporary.

Continuation checkpoint 89, 2026-09-28: the distinct quarantine-recovery
template now PASSes independent source review and remains impossible to execute.
Exact helper `d55fedef...188e`, packet `0298aea1...728`, DRAFT basis
`f26ee96c...6bd` and ten-test suite `84f8982d...318` pass the focused suite,
helper self-test, Python compilation, shell syntax, JSON parsing and diff checks.
The correction makes the inventory consume one root authority, journals each
validated deletion intent only after descriptor/content checks, descriptor-binds
the old lease through its final unlink, rechecks quarantine metadata before root
removal, and durably writes the packet capacity record. The original observer
failure, raw archive, old lease and quarantines remain unchanged.

This is Layer-A/temporary-filesystem evidence only. No recovery, sudo, Docker,
build, guest or application ran; this work window has zero new real guest apps,
and there are still zero successful current-candidate builds. See
`stability-native-exact-quarantine-recovery-template-readiness-20260929-1.json`.
Next commit/push/fetch these exact template bytes. Then change only the basis
source checkpoint/status, helper release pin and packet helper/release pins;
rerun all checks, obtain an independent exact mechanical-diff/execution review,
commit/push/fetch final bytes, and only then perform one fresh non-root packet
attempt. Never rerun or roll back the original cleanup. Formal counters remain
0/273, 2/4, 6/130, 350/10,000 and 0/7.

Continuation checkpoint 90, 2026-09-28: final recovery bytes now have an
independent CONDITIONAL PASS for exactly one non-root packet invocation after
commit/push/fetched-blob verification and fresh live preflight. Final helper is
`dcb72838...9735`, packet `ab2283d6...abac`, release basis
`bef067a4...7983`, and state-aware ten-test suite `aef2cce5...cb08`. Normalizing
the three release pins reproduces the exact pushed template at `13aef461...3c6b`;
the basis/helper/packet dependency is acyclic. See
`stability-native-exact-quarantine-recovery-execution-release-20260929-1.json`.

Do not execute until these final bytes and this release record are committed,
pushed and fetched byte-identically. Then revalidate the old lease/historical
evidence, absent originals, exact quarantine identities, absent old helper PID,
absent recovery outputs, capacity floors, processes and Docker bindings. If all
packet gates pass, invoke only `/usr/bin/bash` with the exact packet path once.
Never invoke the helper directly, retry, roll back, remove a claim, or reuse an
output. A failure may leave partial deletion and must be preserved for separate
review. This releases cleanup only and moves no OS acceptance counter.

Continuation checkpoint 91, 2026-09-28: the single released recovery packet ran
once and failed closed in 6.2 seconds before deletion. The new permanent claim
and three-record journal are retained; phases are `recovery-claimed`,
`inventory-reconstructed`, and `terminal-failure`. Both exact quarantines and
old lease retain their prior device/inode/mode/owner identities, both originals
remain absent, and there are zero `delete-entry`, `delete-complete` or lease
removal phases. No retry or rollback occurred.

The corrected observer completed five rounds with zero target references, zero
permission denials and zero tree transients, but could not obtain two consecutive
globally identical task sets. Rounds 1 and 4 were clean at 818 identities; round
2 ended with 206 new root service threads, round 3 reconciled 154 exiting
threads, and round 5 ended with two new identities. The churn is produced by
root PID/TGID 2545 `clearpass-agentcontroller-service`. Exact failure evidence is
in `stability-native-exact-quarantine-recovery-failure-20260929-1.json`; its
31-member raw archive `stability-native-exact-quarantine-recovery-failure-raw-20260929-1.tar.gz`
is `0a3e13ec...78b5` and 30 regular members match live originals byte-for-byte.

This is the second execution failure in the same cleanup/observer convergence
family, so another cheap correction or unchanged packet is prohibited. Expert
strategy change is active: define a bounded identity-closure scan that treats
exited tasks as unable to retain references but fully scans every newly appeared
or reused identity still live at the accepted cut, preserving all reference,
denial, incomplete-proof and mount/alias failures. It must use a new immutable
observer and new recovery identity bound to both retained failures and both
permanent claims. Independent ownership/source review and a distinct execution
release remain required. No build can start while the old lease/quarantines
remain. No real guest app or current-candidate build ran; counters stay unchanged.

Continuation checkpoint 92, 2026-09-28: expert strategy change produces a new
immutable v2 observer `71fc9f54...3bfa` with test suite `09206112...5a19`.
Sixteen tests, self-test, Python compilation and diff checks PASS; independent
review accepts it only as a source dependency for a new DRAFT recovery. The
production scanner now distinguishes safe exits from reuse, persists an inode
hit even when diagnostic `readlink` disappears, binds opened child identities,
and revalidates each exact root and complete member-inode set after every round.
References, denials, incomplete proofs, reuse, unscanned returned-census members
and any tree drift remain sticky failures.

The scoped contract is bounded repeated-census closure, not an atomic global
snapshot. It requires sealed root-owned 0700 quarantines and independent packet/
operational exclusion of privileged or adversarial mutation and reference
acquisition/transfer during observation. See
`stability-native-exact-live-reference-observer-v2-source-success-20260929-1.json`.
No live observer or cleanup ran. Next commit/push/fetch these exact bytes, then
create a distinct fail-closed recovery template that binds both failure records,
both raw archives, both permanent claims/journals, unchanged old lease and roots,
the v2 observer, and an explicit operational-assumption preflight. Independent
source and execution reviews remain mandatory; no retry of either old packet.

Shutdown checkpoint 93, 2026-09-28: the launcher stop request halted new
dispatch before the recovery-v2 expert produced any workspace file. The lane
was interrupted at a safe boundary and all other child lanes were already
complete. No observer, recovery, sudo, Docker, build, module, guest or
application command ran after the stop request. Repository HEAD and its tracked
remote remain byte-identical at `4add99009253bf8341cfacdec9dc077a3a52bf7e`.
Launcher wrapper PID 3399308/starttime 83682487, worker PID
3399313/starttime 83682494 and app-server PID 3399317/starttime 83682500 remain
live and are intentionally not disturbed during this temporary launcher pause.

Preserve both failure records and raw archives, both permanent recovery claims
and journals, the unchanged old lease `69ced239...47e3`, and both root:root 0700
quarantines at device/inode 26/14117 and 26/24701. Both original paths remain
absent. Do not retry either old cleanup/recovery packet, remove a claim or
lease, roll back a quarantine, or start a build while this state remains.

Next continuation must reconcile this exact pushed checkpoint and the three
launcher identities, then create the still-missing recovery-v2 DRAFT as a new
identity. It must bind both historical failure records/archives/claims/journals,
the unchanged lease and quarantine identities, and reviewed observer v2
`71fc9f54...3bfa`; enforce the explicit sealed-root/no-privileged-mutation
operational assumption; and remain non-executable pending independent source
review. Only after a pushed/fetched template, mechanical finalization and a
separate execution review may a new packet run once. Formal counters remain
0/273, 2/4, 6/130, 350/10,000 and 0/7; there are four historical diagnostic
apps and zero successful current-candidate builds. The OS goal is incomplete,
and this launcher pause is temporary.

Continuation checkpoint 94, 2026-09-28: the expert cleanup strategy now has an
independently PASSed recovery-v2 source template after the first draft and its
single bounded correction were both rejected. The required strategy change was
a larger coherent four-file boundary replacement, not another renamed retry.
Exact DRAFT helper `fb229489...f8d8c`, packet `5bafd304...6d1d7`, basis
`f2a19915...11ff` and 26-test suite `5d25dc07...6b195` pass the complete pure/
temporary-filesystem suite, helper self-test, Python compilation, shell syntax,
JSON parsing and diff checks. Independent review accepts only the non-executable
source-template scope; see
`stability-native-exact-quarantine-recovery2-template-readiness-20260929-1.json`.

The template binds both retained failures and archives, both claims/journals,
the unchanged lease and quarantine identities, exact inventory and reviewed v2
observer. It uses the acyclic template checkpoint -> final basis -> final helper
-> final packet chain, requires a separately fetched execution-release record,
preserves unrelated dirty work, reserves fresh outputs, retains substantive
process/Docker/preflight evidence, and validates exact v7 membership plus two
final closure-clean rounds. Deletion and lease release are descriptor-bound and
failure evidence reports actual survivors. The operational exclusion of
privileged/adversarial mutation and reference acquisition/transfer must hold
through observation and deletion; this is not an atomic census claim.

No live observer, cleanup, sudo, Docker, build, guest or application ran in this
checkpoint. Next commit/push/fetch these exact template bytes. Then mechanically
finalize only the reviewed source checkpoint/status/basis and helper/packet pins,
rerun all pure checks, obtain independent exact-diff/execution review, and
commit/push/fetch before any one-shot packet invocation. Neither older packet
may be retried. Formal counters and the four diagnostic apps/zero successful
current-candidate builds remain unchanged.

Continuation checkpoint 95, 2026-09-29: recovery-v2 final bytes now have an
independent CONDITIONAL PASS for exactly one non-root cleanup packet after this
final state and its execution-release record are committed, pushed and fetched
byte-identically. Mechanical finalization changed only the four reviewed basis
fields and three reviewed pins. Final basis is `4c50f12c...f8b5a`, helper
`5ac3601b...2f641`, packet `cc20d877...27d46`, and the unchanged 26-test suite
is `5d25dc07...6b195`. Reversing those substitutions reproduces the exact
template blobs at `bdbf16ea07f35767d3e8d72f5523545c034f6889`; the dependency
remains acyclic. Execution release
`stability-native-exact-quarantine-recovery2-execution-release-20260929-1.json`
is `7dc1b2b1...adc0d` and grants cleanup only, never runtime or OS acceptance.

Do not execute until the exact final artifacts plus release record are pushed
and fetched, then fresh packet admission confirms source, boot/time, capacity,
processes, Docker mounts, retained history/current identities and absent `-2`
outputs. The operational exclusion of privileged/adversarial mutation and
reference acquisition/transfer must remain true through observation and
deletion. If all gates pass, invoke only `/bin/bash` with the exact packet path
once as non-root. Direct helper execution, retry, rollback, claim removal or
output reuse is prohibited. Preserve any failure for separate review. Formal
counters, real guest application count and current-candidate build count remain
unchanged.

Continuation checkpoint 100, 2026-09-29: the single released recovery-3 packet
ran once and PASSed cleanup in 31 seconds. The v7 observer completed two clean
closure rounds across 1,636 task scans with zero target references, zero
permission denials, zero tree transients and zero persistent revalidation
failures; four exited identities were safely reconciled. The descriptor-bound
journal contains 10,555 records: 10,547 delete entries, two root removals, one
old-lease removal and terminal success. Both exact quarantine roots, both
original paths and the old root lease are absent. Recovery-3 claim and journal
remain preserved; no retry or rollback occurred.

Success record
`stability-native-exact-quarantine-recovery3-success-20260929-1.json` is
`b9870848...c92ae`. Its 23-member raw archive
`stability-native-exact-quarantine-recovery3-success-raw-20260929-1.tar.gz` is
`8a08748c...7388f`; all 22 regular members match the live originals
byte-for-byte. Preflight measured 24,560,197,632 host-free,
21,588,443,136 scratch-free, 7,524,667,392 tmpfs-free and 21,056,061,440
MemAvailable bytes. Post-cleanup tmpfs free is 16,597,475,328 bytes. This is
cleanup infrastructure only: `runtime_acceptance=false`, and all formal
counters plus the four diagnostic apps/zero successful current-candidate builds
remain unchanged.

The heavy/build lease is now clear. Next commit/push/fetch this exact success
record and archive, then prepare a wholly fresh commit-derived candidate,
standalone metadata backup, manifest, request, output/evidence roots and lease
identity under the already reviewed preparation/owner constraints. Revalidate
the current source closure, correct modes, aggregate candidate+backup+12-GiB
container accounting and at least 4-GiB tmpfs reserve. Candidate preparation
does not itself release the offline heavy build; obtain independent one-shot
review for the fresh request before Docker execution. Preserve the consumed
recovery-3 outputs and every earlier failure/archive.

Continuation checkpoint 101, 2026-09-29: a wholly fresh preparation-only
packet for fetched source checkpoint `675891545c881b8d625256ade56fe66ac69fe794`
now has independent CONDITIONAL PASS. Packet `34249db...5a33` differs from the
historical reviewed packet only in the full source commit, corrected terminal-
container owner hash `a8c4c9fc...9155`, and all nine fresh `67589154-1`
mutable identities. Its pure test `3815ef4d...e0b9` normalizes the bytes exactly
to the prior packet and passes five cases plus shell syntax, temporary-output
compilation and diff checks. The initial import-style unittest command is
retained as exit 1 (`scripts` was not importable under `-I`); the direct isolated
test command then exposed and corrected two test-only assumptions before PASS.

Read-only source identity review proves that kernel, host-kernel, workflow,
offline driver, manifest producer, all six workflow patches and external assets
are byte-identical to candidate `68cf089a`; only the build-control owner changed.
The outer Git commit and index still pin IHK `3114d9e7`. The live clean nested
checkout at local-only `21a0d1e` differs only in a whitebox test mirror and is
explicitly excluded: the packet clones the bare store and checks out the pinned
gitlink. Deterministic artifact equality remains an expectation until rebuilt,
and the new full manifest/request hashes must not reuse the old attempt.

Execution release
`stability-native-exact-candidate-preparation-67589154-execution-release-20260929-1.json`
is `3342e097...dfaa`. It conditionally authorizes one non-root packet only after
commit/push/fetched verification and fresh complete preflight. It separately
releases exactly one read-only `sudo -A docker --host
unix:///var/run/docker.sock ps --all --no-trunc` capture; no other privileged
operation is authorized. All nine destinations were absent at review. The
packet creates no Docker client, lease, build or guest and ends at
`BuildOwner.validate()`. `runtime_acceptance=false` and `build_acceptance=false`.
Next push/fetch these exact three files, capture fresh O_EXCL process/locks/all-
lease/Docker/capacity/target evidence, and run the packet once only if every
gate is clean. Preserve all outputs on failure; no retry or automatic cleanup.

Continuation checkpoint 96, 2026-09-29: the single released recovery-v2 packet
ran once and failed closed in 0.25 seconds during root source admission, before
claim or journal creation and before Docker, observer or deletion. The sanitized
root helper's `git -c safe.directory=... -C ... rev-parse HEAD` returned 128:
command-scope `safe.directory` did not satisfy Git's protected-configuration
ownership check for the user-owned repository. A separate read-only diagnostic
reproduced that exact error and showed that explicit `--git-dir` plus
`--work-tree` resolves discovery without changing repository state. No retry or
rollback occurred.

Both quarantines retain device/inode/mode/owner 26/14117/root:root0700 and
26/24701/root:root0700; both originals remain absent. The old lease remains
dev/inode 1831/31447 root:root0600 with SHA `69ced239...47e3`; the prior claim
and journal remain `f2d59c24...41f3` and `d9a17002...50d4`. New recovery-v2
claim and journal paths are absent, and there are zero deletion phases. Failure
record `stability-native-exact-quarantine-recovery2-failure-20260929-1.json` is
`fbdffcf7...3e3b`; its nine-member raw archive is `93fde8f0...e424`, with all
eight regular members verified byte-for-byte against live originals.

The released `-2` packet and every `-2` output are permanently consumed. Do not
retry, truncate or reuse them. This is a distinct execution-admission defect,
not an observer result. Make one bounded correction under a fresh `-3` identity:
preserve the reviewed state machine, replace only root Git discovery with exact
explicit git-dir/work-tree access, add a regression/source binding and fresh
outputs, then obtain independent source/mechanical/execution review before one
new attempt. No build can start while the unchanged old lease/quarantines remain.
Counters and application/build counts remain unchanged.

Continuation checkpoint 97, 2026-09-29: the one bounded correction for the
sanitized-root Git admission defect now PASSes independent DRAFT source review
under a fresh recovery-3 identity. Exact helper `b68ff713...72d7e`, packet
`d4353972...e1547`, basis `e887a35c...68ebe` and 30-test suite
`aec12790...8ad07` pass all prior 26 regressions plus consumed-recovery2 history,
fresh-output and exact Git-argv tests. Self-test, Python compilation, shell
syntax, JSON parsing and diff checks also pass. See
`stability-native-exact-quarantine-recovery3-template-readiness-20260929-1.json`.

Every Git query now uses explicit `/home/holden/mckernel/.git` and work-tree
arguments, with no `-C` discovery or `safe.directory` reliance. All recovery-3
outputs are fresh; consumed recovery-2 bytes, failure record/archive, absent
claim/journal and retained preflight/release/evidence are immutable admission
inputs. The reviewed observer/deletion/lease/failure state machine is otherwise
unchanged. No live or privileged operation ran. Next commit/push/fetch this
template, mechanically finalize its acyclic pins, obtain an independent exact
execution review, then push/fetch before at most one new packet attempt. Never
reuse `-2`; counters and app/build counts remain unchanged.

Shutdown checkpoint 98, 2026-09-29: the launcher stop request arrived after
the independently reviewed recovery-3 DRAFT template was committed, pushed and
fetched byte-identically at `7aa1c02763d517fa2267f2d3ce67e097ddfc7734`.
No recovery-3 finalization, execution-release record, sudo, Docker, observer,
cleanup, build, module, guest or application operation ran after the stop
request. All child lanes are joined. Launcher wrapper PID 3399308/starttime
83682487, worker PID 3399313/starttime 83682494 and app-server PID
3399317/starttime 83682500 remain live and were not disturbed.

Preserve the original root:root 0700 quarantines at device/inode 26/14117 and
26/24701, the absent original candidate and metadata-backup paths, and the old
root:root 0600 lease at device/inode 1831/31447 with SHA `69ced239...47e3`.
Recovery-3 claim and journal outputs remain absent. Preserve every recovery-1
and recovery-2 claim, journal, preflight, release, failure record and raw
archive; never retry, truncate or reuse the consumed `-2` packet or outputs.
Available capacity at shutdown was 24,566,345,728 bytes on the repository
filesystem, 21,588,471,808 bytes on scratch, and 21,060,419,584 bytes of host
memory. No heavy QEMU, mcexec or recovery-3 process was live.

The next authorized continuation must first reconcile this fetched checkpoint,
the three launcher identities and the protected live objects. Then mechanically
finalize recovery-3 exactly as specified by its reviewed basis: replace only
the four basis fields and the three helper/packet pins, rerun the complete 30
pure tests plus self-test, temporary-output Python compilation, shell syntax,
JSON and diff checks, and obtain an independent exact mechanical/execution
review. Create a separate execution-release record, commit/push/fetch and verify
all final blobs before at most one non-root packet invocation. Do not execute
the DRAFT or infer cleanup/runtime acceptance from source review. Formal
counters remain 0/273 applications, 2/4 fault modes, 6/130 production gates,
350/10,000 points and 0/7 language gates; there are four historical diagnostic
apps and zero successful current-candidate builds. The OS goal remains
incomplete, and this launcher pause is temporary.

Continuation checkpoint 99, 2026-09-29: recovery-3 final bytes now have an
independent CONDITIONAL PASS for exactly one non-root cleanup packet after this
final state and its execution-release record are committed, pushed and fetched
byte-identically. Mechanical finalization changed only the four reviewed basis
fields and three reviewed helper/packet pins. Final basis is
`46a9e891...47270`, helper `74460f72...9842f`, packet
`bf26d3b3...7e56`, and the unchanged 30-test suite is
`aec12790...8ad07`. Reversing those substitutions reproduces the exact template
blobs at `7aa1c02763d517fa2267f2d3ce67e097ddfc7734`; the dependency
remains acyclic. All 30 tests, helper self-test, temporary-output Python
compilation, shell syntax, JSON validation and diff checks PASS.

Execution release
`stability-native-exact-quarantine-recovery3-execution-release-20260929-1.json`
is `1a683afc...2154a` and grants cleanup only, never runtime or OS acceptance.
Do not execute until the exact final artifacts plus release record are pushed
and fetched, then fresh packet admission confirms source, boot/time, capacity,
processes, Docker mounts, retained history/current identities and absent `-3`
outputs. The operational exclusion of privileged/adversarial mutation and
reference acquisition/transfer must remain true throughout observation and
deletion. If all gates pass, invoke only `/bin/bash` with the exact packet path
once as non-root. Direct helper execution, retry, rollback, claim removal or
output reuse is prohibited. Preserve any failure for separate review. Formal
counters, real guest application count and current-candidate build count remain
unchanged.

Shutdown checkpoint 102, 2026-09-29: the released preparation packet ran
exactly once and PASSed without creating a Docker client, build lease, build or
guest. Fresh preflight found all nine targets absent, zero active conflicts,
zero build leases, zero running McKernel Docker owners and zero fresh Docker
bindings. The resulting clean candidate is
`/dev/shm/mckernel-exact-candidate-67589154-1` at device/inode 26/25166 mode
0755, with standalone metadata backup device/inode 26/35798 mode 0755. It pins
main source `675891545c881b8d625256ade56fe66ac69fe794` and IHK
`3114d9e7101ad52030eb3effa849a5c108972a1f`.

Manifest `c5204af6...6ef9` and request `a2c37952...aa7c` pass exact input
verification and owner validation only. Main/IHK closure observations contain
2,260/17 entries with hashes `6ce41301...8313` and `1538fd99...7f78`.
Output and evidence roots are empty, the lease is absent, no preparation
process survives, and inner/outer logs closed with RC 0 and final fsync PASS.
The aggregate candidate + backup + prospective 12-GiB container requirement is
21,965,742,080 bytes, below the 24-GiB budget; postflight retains
24,512,708,608 host-free, 21,581,594,624 scratch-free, 7,516,635,136 tmpfs-free
and 20,995,428,352 MemAvailable bytes.

Checkpoint record
`stability-native-exact-candidate-preparation-67589154-checkpoint-20260929-1.json`
is `05972423...dae8`. Its 75-member archive
`stability-native-exact-candidate-preparation-67589154-20260929-1.tar.gz` is
`53003c8e...a084`; all 72 regular members match live originals. This is
preparation infrastructure only: `runtime_acceptance=false`, no native build or
guest ran, formal counters remain unchanged, and successful current-candidate
builds remain zero.

The launcher shutdown request arrived before heavy-build review or execution.
All child lanes are joined. Wrapper PID 3399308/starttime 83682487, worker PID
3399313/starttime 83682494 and app-server PID 3399317/starttime 83682500 remain
live and were not disturbed. Preserve the candidate, metadata backup, manifest,
request, empty output/evidence roots, all preparation logs and receipts, and
every earlier failure/archive. On a subsequent authorized continuation, first
reconcile these identities and fresh capacity/process/Docker/lease state, then
obtain independent one-shot heavy-build execution review for exact request
`a2c37952...aa7c`. Only after a fetched release may the non-root owner command
run once. No build retry, guest, module or acceptance operation is released by
this checkpoint. The OS goal remains incomplete and the launcher pause is
temporary.

Continuation checkpoint 103, 2026-09-29: exact fresh request
`a2c37952...aa7c` now has independent CONDITIONAL PASS for one offline native
build after this release is committed, pushed and fetched byte-identically and
fresh fail-closed preflight passes. Release record
`stability-native-exact-build-67589154-execution-release-20260929-1.json` is
`d657a75e...8869`. It binds candidate `67589154...fe794`, pinned IHK
`3114d9e7`, manifest `c5204af6...6ef9`, owner `a8c4c9fc...9155`, driver
`1e522a60...962b`, immutable source-free image
`sha256:0f8ad280...775d` and image receipt `18225919...8172`.

Run at most once as the ordinary user with exact `/usr/bin/python3 -E -s -B`
owner command after fresh complete process/lock/lease/identity/capacity/source
checks and separately released absolute `/usr/bin/sudo -A` read-only Docker
`ps --all` plus exact returned-ID `inspect` observations. The reviewed profile
is CPUs 2-5, 12 GiB/no swap, 512 PIDs, no network, read-only root, dropped
capabilities, no-new-privileges, unprivileged container user, 256-MiB `/tmp`,
`-j2` and 19,800-second timeout. All concurrent work must remain within seven
jobs/24 GiB with four-GiB headroom and one heavy owner. Permission denial,
incomplete inventory, changed input, unresolved owner/mount conflict, a failed
floor, or a nonempty target blocks execution.

The pre-review `/usr/bin/python3` regression exposed one test-only Python 3.8
mock-signature error before Docker/lease creation. The bounded correction
`b187b587...9ae5` accepts and forwards the full `os.walk` signature while
preserving the denial oracle; both Python 3.8 and 3.9 pass all 65 owner tests.
Evidence record `stability-native-exact-owner-py38-fixture-success-20260929-1.json`
is `2ac8de95...032a`, pushed/fetched at
`4a25e8b683fd1ba4b723e1cbfe2cf4f84cb8c4c2`. Independent review confirms this
test-only fix does not require candidate regeneration.

This release grants no existing build success, cleanup, module, guest, runtime,
application or counter credit. Preserve every partial output, receipt, log,
container terminal state, process identity, lease/signal observation and prior
failure. A successful build must receive independent artifact/evidence review
before a separate current-candidate `startup.argv-empty` diagnostic release.
That fixture expects exit 0, empty stderr and exact JSON stdout, and remains
diagnostic rather than formal M04 acceptance.

Continuation checkpoint 104, 2026-09-29: the single released `67589154-1`
build attempt ran once and FAILed closed in phase 0 after 37 seconds, before
compilation. The owner retired normally, the two Docker wait processes retired,
the lease was released after proven retirement, and terminal container
`decd7cf92467e1214cc955d15a00b847587ada37016f206e9a82019cbb72c6b9`
remains retained, exited 1, non-OOM, under the exact reviewed profile. Output is
empty. Never retry, clean or reuse this request, namespace or container.

Preflight attempt 1 is permanently `FAIL_OBSERVER_ONLY`: this host rejected the
known-incompatible trailing `--ww`, leaving an empty process census. It made no
mutation. Fresh attempt 2 changed only that observer to trailing `ww` and PASSed
all hashes, identities, empty targets, locks, leases, process/resource floors,
11 exact Docker inspections and mount/owner exclusions. Receipts are
`3c4af543...142d5` and `e76fd4e0...14749`.

The new failure is exact:
`ihk-native-queue-check: FAIL: Rust source must define fn snapshot exactly once`.
Earlier phase-0 contracts passed through the IHK lifecycle check; compilation
did not start. Read-only diagnosis finds valid forwarding and implementation
methods named `snapshot` (and the same structure for `try_enqueue`), while the
checker incorrectly applies uniqueness across the entire Rust file. The defect
is the checker scope, not the production queue. One bounded correction may
scope extraction to the exact `impl SharedQueue<'mapping>` block while retaining
all body invariants and adding an allowed-wrapper positive plus duplicate-in-
target-impl rejection. A fresh candidate is mandatory after review.

Failure record `stability-native-exact-build-67589154-failure-20260929-1.json`
is `2402d856...03e6`. Its 193-member raw archive
`stability-native-exact-build-67589154-failure-raw-20260929-1.tar.gz` is
`a6e2fff0...b46d`; all 180 regular members match live originals. Preserve the
candidate, backup, both preflights, outer capture, request/manifest, complete
owner/build evidence and terminal container. Successful current-candidate build
count remains zero; no module, guest, diagnostic app or formal counter changed.

Continuation checkpoint 105, 2026-09-29: expert escalation closes the queue-
checker prerequisite without changing production Rust, ABI or fixture bytes.
Checker `c9b4d012...aa96` now selects exactly one
`impl SharedQueue<'mapping>` so valid `SharedProducer` forwarders do not collide,
while missing/duplicate impls and duplicate target methods fail closed. Contract
`b64022b8...f9fd` binds current source `3163d9cc...e9c5`, the exact ordered
three internal tests and seven configured tests. Test contract
`fca20469...6e11` covers missing/extra inventory, wrong totals, forwarders,
target uniqueness and all prior safety/order/hash/compiler/credit mutations.
Python 3.8 and 3.9 each pass 31 tests; the direct host check reports source-
contract verified and honestly skips its unavailable exact compiler.

Independent review then conditionally released one light, current-source Rocky
Rust fixture under 2 CPUs, 2 GiB/no swap, 128 PIDs, no network, read-only root,
unprivileged UID/GID 1000, dropped capabilities and no-new-privileges. Release
`stability-native-queue-fixture-execution-release-20260929-1.json` is
`8affa38e...0062`. Fresh preflight `e88d4197...93df` verified all six input
hashes, the immutable image, fresh private roots, no lease/heavy conflict,
absent container name, resource floors and the untouched failed heavy container.

The one released container PASSed. Rocky rustc is exact 1.92.0; all seven named
tests pass with zero failure/ignored/measured/filtered results. Inputs remain
unchanged, executable `queue-tests` is `ceb5db9f...f43d`, and retained container
`8943e49772f840ba5da6571c2e2c6fde60b61157f21f873d832669157ef9bc10`
is exited 0, PID zero and non-OOM. Result receipt is `2eb835a2...3616`.
Independent final evidence review PASSes all 43 receipt files and every archive
member.

Success record `stability-native-queue-contract-reseal-success-20260929-1.json`
is `849d4bee...d036`. Its 61-member archive
`stability-native-queue-fixture-success-raw-20260929-1.tar.gz` is
`bb26afcc...90d6`; all 59 regular members match live originals. This proves the
current-source bounded queue fixture only, not a kernel/module build,
`SharedProducer` runtime path, guest interoperability, application acceptance or
IHK-008 credit. Successful current-candidate builds remain zero and formal
counters are unchanged. Next push/fetch these exact bytes, then prepare a wholly
fresh commit-derived candidate/request/output/evidence/lease namespace and seek
a separate heavy-build review. Never reuse `67589154-1` or clean either retained
container through this decision.

Continuation checkpoint 106, 2026-09-29: the launcher requested a shutdown
checkpoint before any new execution. Every child lane is joined and no heavy,
guest, cleanup or candidate-preparation operation is active. Wrapper PID
3399308/starttime 83682487, worker PID 3399313/starttime 83682494 and app-server
PID 3399317/starttime 83682500 remain live and undisturbed. Retained failed
container `decd7cf9...c6b9` remains exited 1/PID 0/non-OOM/no-restart; retained
queue-fixture container `8943e497...bc10` remains exited 0/PID 0/non-OOM/no-
restart. Preserve both exactly and never restart or reuse them.

Fresh source-commit `704f6654...63561` preparation WIP is retained but was not
executed or released. Packet `native-exact-candidate-preparation-704f6654-1.sh`
is `7502c748...b3a0a` and its five-test contract
`test_native_exact_candidate_preparation_704f6654.py` is `ba67804f...d8c`;
bash syntax, temporary-output Python 3.8 compilation, JSON/diff/source-contract
normalization and all five tests pass. It names nine fresh targets and preserves
the unchanged owner, IHK pin and request contracts. This is preparation WIP
only, not a build, runtime result or acceptance result.

Independent read-only cleanup review BLOCKS deletion of consumed candidate
`/dev/shm/mckernel-exact-candidate-67589154-1` and metadata backup
`/dev/shm/mckernel-exact-metadata-backup-67589154-1`. The existing preparation
archive lacks complete installed Git metadata and backup coverage, while the
failed terminal container still records candidate/driver bindings. No fresh
privileged live-reference census or reviewed exact terminal-container exception
exists. Host/scratch/tmpfs free bytes at shutdown are 24,444,002,304 /
21,565,747,200 / 7,516,635,136. Do not improvise cleanup.

On the next authorized launcher continuation, first reconcile all identities,
leases, locks, mounts, Docker state and resource floors. Then prepare a complete
candidate/backup inventory and restoration capsule, plus one ordinary-retirement
packet using descriptor-relative no-follow checks, durable journal, two clean
closure rounds and an exact exception only for the unchanged terminal container.
Regression-test changed/running/restarting/paused/unknown container rejection
and obtain independent execution release before deleting anything. Only after
safe space recovery may the fresh `704f6654-1` preparation receive independent
review and one-shot execution, followed by a separate heavy-build release.
Record `stability-shutdown-checkpoint-20260929-106.json` preserves this cursor.
The OS remains incomplete; formal counters and successful current-candidate
build count remain unchanged at zero. The launcher pause is temporary.

Continuation checkpoint 107, 2026-09-29: the blocked cleanup family now has a
source-complete restoration/retirement toolchain after preserving two rejected
designs and the expert-integration failures. Exact final hashes are capsule
planner `ac3bb035...d0b26`, deterministic archive builder
`6a28184e...ac06e`, callback-bound retirement template
`744beace...21b5d`, and tests `ae6f129a...43c9a`,
`fa9d727d...8355e`, `3605a65b...2fce`. Both system Python 3.8 and Anaconda
Python 3.9 pass the same 40 tests; pycompile and diff checks pass.

Independent integrated review PASSes only these frozen source/pure-fixture
bytes. It reran 40/40 on Python 3.8 and verified direct planner -> archive ->
retirement behavior with the actual v7 observer top-level shape. The final
boundary proves exact main/IHK Git+gitlink and safe tracked-symlink handling,
descriptor-rooted/no-follow inventory, metadata and backup coverage,
deterministic normalized archive bytes, byte-snapshot verification, exact
original+quarantine Docker intersection rejection, the sole exact retained
terminal exception, durable quarantine/deletion journaling and post-journal
name revalidation. Arbitrary hashes, unrelated/partial capsules, nested roots,
metadata symlinks, FIFO/hardlink substitutions, stale observations, malformed
closure evidence and a replaced post-journal file all reject; the replacement
survives.

Record `stability-native-exact-retention-source-checkpoint-20260929-1.json`
preserves the rejected source hashes and concrete findings instead of erasing
the failure family. No live candidate or backup was read by the final reviewer,
no capsule was created, no root was renamed/deleted, and no Docker/build/guest
operation ran. Current-candidate builds remain zero, real guest applications
this checkpoint remain zero, and formal counters are unchanged.

Next checkpoint these exact bytes and fetch-verify them. Then create a new
one-shot preparation packet that binds candidate `67589154-1`, backup identity,
exact commits, fresh manifest/archive/evidence names and the final six source
hashes. Obtain a separate independent execution review for live manifest and
archive generation only. That read-only/source-preservation execution must
verify the live 49-link set, full restoration coverage, archive members and
postflight identities. It grants no retirement: a separate later root/Docker
execution release remains required before any rename or deletion.

Continuation shutdown checkpoint 108, 2026-09-29: the launcher requested a
stop while the first bounded correction of the live-retention preparation
packet was in progress. New dispatch stopped and the sole running child was
interrupted and joined. No packet, capsule, archive, retirement, cleanup,
Docker, build, module or guest command ran. The planned inventory, archive and
scratch evidence root are all absent. Formal counters remain unchanged,
successful current-candidate builds remain zero and no real guest application
ran in this checkpoint.

The interrupted packet is preserved as source-only WIP at
`native-exact-candidate-retention-preparation-67589154-1.py`, hash
`ab1471e8...4742`; its unchanged test is `63abe211...27defa`. Both compile, but
the four-test suite reports three passes and one failure because its stale
no-runtime token assertion rejects the packet's process-census string `qemu`.
The packet also has no independent review or release and must not be executed.
Resume its bounded correction by auditing the acyclic release binding, exact
Git admission, process-group failure cleanup, durable writes, manifest/member
coverage and postflight checks, then broaden and pass pure synthetic tests.

Preserve launcher wrapper 3399308/starttime 83682487, worker
3399313/83682494 and app-server 3399317/83682500. Preserve terminal containers
`decd7cf9...c6b9` (exited 1/PID 0/non-OOM/no restart) and
`8943e497...bc10` (exited 0/PID 0/non-OOM/no restart). Candidate and backup
remain unchanged at device/inode 26/25166 and 26/35798, uid/gid 1000/1000,
mode 0755. Measured free bytes are host 24,389,771,264, scratch
21,565,747,200, tmpfs 7,516,635,136 and available memory 20,874,715,136.

On the next authorized invocation, reconcile all identities and resources,
finish and independently review the source-only preparation packet, then
checkpoint/fetch-verify it and obtain a separate acyclic one-shot release for
manifest/archive preparation only. Independently review the resulting capsule
before designing a separate privileged retirement release. Only after reviewed
space recovery may fresh preparation `704f6654-1` advance toward a separately
released heavy build. Record
`stability-shutdown-checkpoint-20260929-108.json` is the live cursor. The OS is
incomplete and this launcher pause is temporary.

Continuation checkpoint 109, 2026-09-29: the launcher continuation reconciled
checkpoint 108 and resumed the blocked retention-preparation family. Live
launcher identities, candidate/backup inodes and commits, absent outputs and
both retained terminal containers remain unchanged. No heavy build, guest,
capsule, cleanup or retirement ran. Adopted policy hashes are GOAL
`76c4f5d1...bcc3`, START `1698d342...216c`, CONVERGENCE
`f6938bd2...86a` and current HANDOFF `a1cf9115...d24`.

The cheap correction `36a145f2...ec9` passed seven tests but independent review
BLOCKed it on seven release, archive, capacity, Git, process, snapshot and lease
defects. Per the failure-family limit, a Terra expert replaced the boundary.
Its first reviewed candidate `3727a43b...b175c` was BLOCKed on fresh-scratch
ordering, incomplete finalization-delta binding and an unprotected child-launch
signal interval. The dispatcher selected one larger coherent boundary repair;
every rejected hash and finding remains preserved.

Final placeholder packet `c57ed38d...8f1c` and test `57152321...dfa8` receive
independent source/test-design PASS. Python 3.8 and 3.9 each pass 14 behavioral
tests; pycompile and diff checks pass. Coverage includes an acyclic temporary
Git template/release chain, exact changed paths and fetched blobs, supporting-
test tampering, current sample hooks/worktree administration, top-level shared-
metadata rejection, bounded control-plane fingerprinting, fresh scratch claims,
real SIGTERM injection, timeout descendant retirement, snapshot substitution,
nested IHK archive ancestor closure, capacity deltas and second-planner mutation
rejection. Direct current-repository metadata admission passes in 0.020 seconds
without reading the 9.9-GiB Git object payload.

Record `stability-native-exact-retention-preparation-template-review-20260929-1.json`
contains the failure lineage and review scope. This is template source evidence
only. Next commit/push/fetch the exact placeholder template, create an
independently reviewed release JSON bound to that immutable commit, replace only
the packet release-hash declaration, and commit exactly packet plus new release
JSON. Only after fresh fetched preflight may the ordinary-user packet run once.
No execution, cleanup, application or formal gate credit is granted; current-
candidate builds and real guest applications remain zero.

Continuation checkpoint 110, 2026-09-29: the first released preparation packet
at commit `148e3101...e89fa` failed immediately with exit 2 before claim, lease,
planner, archive or root traversal. It observed PID 3780193 from `/proc`, then
treated the PID's normal disappearance before identity read as
`unreadable process identity`. PID 3780193 was absent at immediate postflight;
inventory and archive remain absent. Empty scratch attempt 1 is preserved at
device/inode 1831/2907338, uid/gid 1000/1000, mode 0700. Record
`stability-native-exact-retention-preparation-failure-20260929-1.json` preserves
the exact command, exit and side effects. No unchanged retry occurred.

The bounded census correction initially exposed two further source-review
defects: string `/proc` names did not reach `proc_identity`, and empty cmdlines
were not proven kernel threads or zombies. Final placeholder packet
`abe54826...b21b` plus tests `40dd25d3...8e93` receive independent source/test-
design PASS. `proc_identity` now parses integer PID, state, flags and starttime;
missing PIDs skip only after confirmed absence, protected executable links use
readable cmdline fallback, double-inaccessible identities reject, and empty
identities require state Z or `PF_KTHREAD`. Exact compiler/guest basenames and
`qemu-system-` prefixes still conflict. Both Python versions pass 18 tests,
including real string-PID parsing and live-userspace empty-identity rejection;
direct live census PASSes with no conflicts.

The retained input candidate and backup remain attempt 1 with their exact
identities. Only release, inventory, archive, scratch, claim and lease move to
fresh attempt 2; the attempt-1 competing build lease remains bound to the
consumed candidate. This is unexecuted placeholder source only. Commit/push/
fetch it with the attempt-1 failure record, then create and independently review
an attempt-2 release before any invocation. Formal counters, real guest apps and
successful current-candidate builds remain unchanged.

Shutdown checkpoint 114, 2026-09-29: the launcher stop request ended new
dispatch. The one active expert correction completed and is joined; every child
lane is now closed. Corrected retirement packet `59b3bedf...dc483` and test
`8c57021a...d5c8` pass 15 tests on each of Python 3.8 and 3.9, pycompile and
scoped diff checks. This is unreviewed source WIP only. It has not received the
required fresh independent source or execution review, immutable fetched
template checkpoint or acyclic release. No retirement packet, sudo mutation,
candidate traversal, Docker mutation, rename, deletion, build, module, guest or
application ran.

Preserve launcher identities 3399308/83682487, 3399313/83682494 and
3399317/83682500; candidate and backup identities 26/25166 and 26/35798;
evidence-root identities 1831/2907338 and 1831/2907339; and terminal containers
`decd7cf9...c6b9` (exit 1) and `8943e497...bc10` (exit 0). Measured free bytes
are host 24,276,938,752, scratch 21,560,459,264, tmpfs 7,516,635,136 and memory
20,682,653,696. Record
`stability-shutdown-checkpoint-20260929-114.json` is the exact live cursor.

Next invocation must reconcile those identities, then obtain fresh independent
source review of the exact packet/test against all five retained blockers. If
and only if that passes, checkpoint and fetch-verify the immutable template,
mechanically create the acyclic release, and obtain separate execution review
before any one-shot sudo invocation. After independently accepted retirement
and measured capacity recovery, independently review preparation `704f6654-1`
before any heavy build. Formal counters remain unchanged, current-candidate
builds remain zero, accepted applications remain 0/273, the OS is incomplete,
and this launcher pause is temporary.

Shutdown checkpoint 117, 2026-09-29: the launcher stop request again ended new
dispatch. All child lanes are closed and no bounded operation remains active.
The retirement helper/packet correction is preserved at exact hashes helper
`7860b315...226b`, helper test `846ef1ad...f225`, packet
`c98d3035...a51eb` and packet test `6522ab03...e649`. Python 3.8 and 3.9 each
passed the combined 48 tests; pycompile and scoped diff checks passed. This is
unreviewed source WIP only. The latest independent BLOCK applied to superseded
hashes `de53fbd5`/`edbe08b1`/`85d5fd30`/`bcddd30a`, so it neither rejects nor
approves these exact files. All earlier rejected hashes and their output-
namespace, exclusion, subprocess-lifecycle, bounded-I/O, helper-bridge and
durable-terminal-status findings remain preserved in checkpoint 117.

No retirement packet, candidate traversal, sudo mutation, Docker mutation,
rename, deletion, build, module, guest or application ran. Preserve launcher
identities 3399308/83682487, 3399313/83682494 and 3399317/83682500; candidate
and backup identities 26/25166 and 26/35798; evidence roots 1831/2907338 and
1831/2907339; and terminal containers `decd7cf9...c6b9` (exit 1) and
`8943e497...bc10` (exit 0). Both exact source commits remain available in
their object stores. No current candidate claim, build lease or heavy process
is active. Measured free bytes are host 24,228,782,080, scratch 21,560,459,264,
tmpfs 7,516,635,136 and memory 20,484,620,288.

The next invocation must first reconcile those identities, then obtain fresh
independent source review of all four exact hashes. The review must cover an
actual nonempty descriptor-relative helper bridge, leader-first descendant and
pidfd error/retry behavior, immutable-lease creation failure cleanup, bounded
reads, sticky-parent output safety and terminal publication/finalization. Only
after PASS may the template be committed/fetch-verified, an acyclic release be
mechanically constructed, and a separate execution review authorize a one-shot
sudo run. After accepted retirement and capacity recovery, review preparation
`704f6654-1`, run one heavy current-candidate build, then use the smallest real
memory application diagnostic before broader smokes. Record
`stability-shutdown-checkpoint-20260929-117.json` is the live cursor. Formal
counters remain unchanged, current-candidate builds remain zero, applications
remain 0/273, the OS is incomplete, and the launcher pause is temporary.

Continuation checkpoint 126, 2026-09-29: the retirement integration source
boundary now independently PASSes after preserving the complete rejected-hash
lineage from reviews 118 through 124. Exact reviewed hashes are packet
`f1cb3db7...c363`, packet test `41ad8074...c4b6`, helper
`2218e7fe...010` and helper test `c350fc3e...95c1`. The unchanged observer and
archive remain `3562b1d3...3666` and `6a28184e...06e`. Python 3.8 and 3.9 each
pass all 106 packet/helper/observer/archive tests sequentially; pycompile and
scoped diff checks pass.

Verified source behavior includes an unreaped leader/pidfd session anchor, raw
child/stream ownership before decoration, pre-spawn pidfd support checks,
identity-bracketed transient recovery, no replacement-session signalling,
bounded non-abortable retirement, identity-safe anchor close, descriptor-bound
outputs, and explicit helper/packet primary-plus-cleanup failure trees. A
permanent child-pidfd failure remains deliberately fail closed: only the proved
unreaped direct child may be signalled, surviving descendants are recorded,
retirement cannot PASS and the immutable exclusion tombstone blocks later work.
The one-shot terminal writer has the independently accepted limitation that its
read-only descriptor closes best effort after durable publication and otherwise
dies with the process; it cannot alter the published bytes.

Records
`stability-native-exact-retirement-integration-review-failures-20260929-1.json`
and `stability-native-exact-retirement-integration-source-success-20260929-1.json`
preserve the complete findings and accepted scope. This remains a DRAFT source
template. No candidate traversal, live Git streaming, immutable ioctl, sudo
retirement, Docker mutation, build, module, guest or application ran. Adopted
policy hashes remain GOAL `76c4f5d1...bcc3`, START `1698d342...216c`,
CONVERGENCE `f6938bd2...86a`; the launcher-recorded HANDOFF predecessor is
`f061d26f...8f2`, while the reconciled live HANDOFF before this append was
`61b477b7...821b`.

Next commit/push/fetch-verify these exact DRAFT bytes. Then construct an acyclic
release mechanically from the fetched template commit, changing only the packet
release sentinel and adding the release JSON. Independent exact mechanical and
execution review plus fresh live prerequisite/immutable-filesystem support
checks are mandatory before at most one sudo invocation. Accepted applications
remain 0/273, current-candidate builds remain zero and formal counters do not
move from source-template work.

Shutdown checkpoint 128, 2026-09-29: the launcher stop request ended new
dispatch. All child lanes are joined and closed, and no bounded operation
remains active. Source-template commit `325e7c2e...689a2` is already pushed,
fetched and exact: packet `f1cb3db7...c363`, packet test
`41ad8074...c4b6`, helper `2218e7fe...010`, helper test
`c350fc3e...95c1`, and source-success record `b892d3c3...36d8` match their
fetched blobs. The DRAFT sentinel remains and no release JSON exists.

Release-schema audit 127 completed without traversing either candidate root or
creating a release. It fixes the required 25-field schema, immutable template
binding and exact two-path finalization delta. Preserve boot
`c733d83b...9afd`; launcher identities 3399308/83682487,
3399313/83682494 and 3399317/83682500; candidate/backup identities 26/25166
and 26/35798; preparation evidence identities 1831/2907338 and 1831/2907339;
and both terminal containers. Both source commits remain present. No claim,
heavy lease, build or guest is active. Measured free bytes are host
24,170,889,216, scratch 21,560,459,264, tmpfs 7,516,635,136 and memory
20,251,942,912.

On the next authorized invocation, first reconcile these identities. Then
mechanically generate the acyclic release from fetched template `325e7c2e`,
including fresh complete live-root inventories and full terminal Docker
records. Change only the packet sentinel plus the new release JSON, verify and
push/fetch that exact delta, and obtain separate independent mechanical and
execution review plus fresh immutable-filesystem support checks before at most
one sudo retirement invocation. After accepted retirement and measured space
recovery, independently review preparation `704f6654-1`, run one serialized
current-candidate build, and start the smallest real memory application
diagnostic. Record
`stability-shutdown-checkpoint-20260929-128.json` is the live cursor. Formal
counters remain unchanged, current-candidate builds remain zero, applications
remain 0/273, the OS is incomplete, and this launcher pause is temporary.

Continuation checkpoint 132, 2026-09-29: the first mechanically generated
retirement release candidate failed precommit integrated validation before any
retirement or privileged mutation. Its fresh inventory covered all 10,595
members, but Docker returned the same six complete mount objects for terminal
container `decd7cf9...c6b9` in a different list order. Three further identical
13-container censuses retained stable IDs but three different terminal-row and
mount-list hashes. Raw failed release candidate `26bf80ff...e8a8d` remains at
scratch device/inode 1831/2907341; record
`stability-native-exact-retirement-release-generation-failure-20260929-1.json`
preserves the command result, identity, hashes and absence of side effects. The
DRAFT sentinel was restored and no unchanged release retry occurred.

The one bounded correction independently PASSes at exact hashes packet
`7e3581fb...0daf`, packet test `1e878802...e4f1`, helper
`704a3f5f...f54b` and helper test `c2a65c45...3d68`. Packet and sealed helper
canonicalize only the `Mounts` array ordering using each full mount object;
they retain multiplicity, every field, exact Config/HostConfig/State, full
census reconciliation and protected-path rejection. Python 3.8 and 3.9 each
pass 108 tests, all 720 retained six-mount permutations pass, negative mutation
controls reject, and three fresh live canonical comparisons pass across all 13
containers. Independent review 131 PASSes source-template scope only.

Record
`stability-native-exact-retirement-docker-order-source-success-20260929-1.json`
preserves the correction and its limitation that only hashes, not raw bytes, of
the three follow-up inspect responses were retained. Next commit/push/fetch
these exact DRAFT bytes as a new immutable template. Then regenerate an acyclic
release bound to that commit, changing exactly the packet sentinel and adding
the release JSON; obtain separate exact mechanical/execution review before any
one-shot sudo run. Current-candidate builds remain zero, real applications this
window remain zero, applications remain 0/273, and formal counters do not move.

Continuation checkpoint 134, 2026-09-29: release candidate 2
`5a28247b...bb34` passed schema, both full root/archive checks and three fresh
13-container Docker censuses, then failed its precommit exact-byte finalization.
The fetched template contained the complete sentinel twice: once in the release
declaration and once as the literal inside `final_bytes`, so the intended
exact-one guard deterministically rejected it. The raw 2,369,338-byte candidate
is retained at scratch device/inode 1831/2907354 and record
`stability-native-exact-retirement-release-generation-failure-20260929-2.json`
preserves the result. The DRAFT declaration is restored. No release commit,
retirement, privileged mutation, Docker mutation, build or guest occurred.

The one bounded sentinel correction independently PASSes packet
`aaf4ac87...de87` and test `7a563aac...d346`. It constructs the same search
bytes from pieces so only the declaration contains the complete token; the
exact-one guard and exact replacement remain intact. The prior fetched source
reproduces the two-token failure, while the corrected actual packet has one
token and finalizes only line 17. Missing and duplicated tokens reject. Both
Python versions again pass 108 tests; compilation and diff checks pass. Record
`stability-native-exact-retirement-sentinel-source-success-20260929-1.json`
preserves independent review 133.

Next commit/push/fetch these exact DRAFT bytes as the new immutable template,
then regenerate the acyclic release against that commit. The release commit may
change exactly the packet sentinel and add its release JSON; it still requires
separate exact mechanical/execution review and fresh support checks before any
one-shot sudo invocation. Builds remain zero, real applications this window
remain zero, applications remain 0/273 and formal counters remain unchanged.

Continuation checkpoint 138, 2026-09-29: fetched two-path release commit
`aa763d01...9d02` was mechanically correct but failed its first unprivileged
full admission before root euid or runtime mutation. The canonical Git child
could not map the retained 7,890,604,289-byte pack under its 512-MiB virtual
limit and exited 128 before the first object. The one bounded 12-GiB correction
then reached record 5,634 and exposed 49 symlinks whose content hash must derive
from their target bytes; it also measured 7,900,852 KiB RSS and compounded the
primary with a five-second EOF-wait cleanup timeout. Records
`stability-native-exact-retirement-release-admission-failure-20260929-1.json`
and `...-admission-correction-failure-20260929-1.json` preserve both failures.
The invalid release remains immutable in Git history and is deleted from the
new DRAFT worktree; no privileged retirement occurred.

Expert escalation 135 replaced that family coherently. Canonical readers alone
use 32-MiB packed windows, 128-MiB packed mapping limit, 32-MiB delta cache and
a 2-GiB address-space cap. Before spawn, the packet validates all retained
record shapes and routes exactly 7,715 main plus 1,296 IHK objects. It derives
symlink content digests from target bytes, uses a separate 128-MiB blob bound,
and streams content SHA256 plus both Git SHA1/SHA256 object identities. Reader
failure closes stdin boundedly, performs anchored retirement with output pipes
retained through census, and preserves complete identity-based failure trees.

Independent review 137 first BLOCKed packet `70e3637c...68ad` because unrelated
composite close errors could hide a natural-exit primary; record
`stability-native-exact-retirement-canonical-reader-review-failure-20260929-1.json`
preserves the reproducer. Final packet `6f2be938...ebc2` and test
`e26918a6...5cf1` PASS independent re-review. Python 3.8 and 3.9 each pass 116
tests. Exact final-source full runs each verify all 9,011 objects and
9,050,119,070 bytes in 33.846/34.381 seconds with 259,632/259,540 KiB peak RSS,
zero swap, and four recorded readers exiting 0, retired, pidfd released and
empty final census. Record
`stability-native-exact-retirement-canonical-reader-source-success-20260929-1.json`
preserves identities and measurements.

Next commit/push/fetch this DRAFT source and failure lineage as the new immutable
template. Then regenerate the release against it, verify the exact two-path
delta and complete full fetched admission, followed by separate execution
review before one-shot sudo. Current-candidate builds and real guest apps this
window remain zero; applications remain 0/273 and formal counters are unchanged.

Shutdown checkpoint 139, 2026-09-29: the launcher stop request ended all new
dispatch before privileged retirement. Every child lane is terminal and no
bounded operation, heavy lease, build or guest remains active. The mechanically
generated release is preserved, not executed: release JSON
`0f60c2f2...a8d0` (2,369,338 bytes) and finalized packet
`a05ea9ad...07c` are bound to fetched DRAFT template commit
`33eab956...9b88`. The packet compiles and its exact scoped diff check passes.
Full fetched-commit admission and independent execution review remain pending.

Preserve boot `c733d83b...9afd`; launcher identities 3399308/83682487,
3399313/83682494 and 3399317/83682500; candidate/backup identities 26/25166
and 26/35798; and terminal containers `decd7cf9...c6b9` and
`8943e497...c10`. The operational lease, output and both quarantine paths are
absent. Available bytes are host 24,128,962,560, scratch 21,555,707,904,
tmpfs 7,516,635,136 and memory 20,155,097,088. The shutdown-time Docker
recheck lacked socket permission; the release retains the earlier complete
canonical census, but the next invocation must reconcile it freshly.

Next verify this checkpoint's fetched bytes and run full unprivileged
`validate_release` against its fetched commit. Obtain a fresh independent exact
mechanical/execution review, then reconcile identities, Docker, resource floors
and immutable-filesystem support. Only after PASS may one `sudo -A` retirement
run occur. After accepted retirement, review preparation `704f6654-1`, run one
serialized current-candidate build, then the smallest real memory application
diagnostic. Record `stability-shutdown-checkpoint-20260929-139.json` is the live
cursor. Formal counters remain unchanged, builds remain zero, applications
remain 0/273, the OS is incomplete, and this launcher pause is temporary.

Continuation checkpoint 140, 2026-09-29: full unprivileged admission of fetched
commit `66611e18...cd92` failed before canonical object streaming because the
shutdown checkpoint and the finalized release shared one commit. Relative to
template `33eab956...9b88`, five paths changed, while the independently reviewed
release correctly permits only the packet and release JSON. The exact failure
was `nonmechanical changed path` after 0.23 seconds and 54,940 KiB max RSS;
record `stability-native-exact-retirement-release-admission-failure-20260929-2.json`
preserves it. No root traversal, privileged action, runtime mutation, build,
guest or application occurred.

The bounded correction does not weaken the oracle or rewrite Git history. This
commit becomes a fresh DRAFT template by retaining checkpoint 139 and its
documentation, restoring `RELEASE_HASH_REQUIRED`, and deleting the rejected
release from the live tree. After fetched verification, generate a new release
bound to this exact template and commit only the packet sentinel plus release
JSON. Then run full fetched admission across all 9,011 objects and obtain fresh
independent exact mechanical/execution review before any `sudo -A` retirement.
Current-candidate builds remain zero, real guest applications this window remain
zero, applications remain 0/273 and formal counters remain unchanged.

Continuation checkpoint 143, 2026-09-29: exact fetched release
`431df62c...2f35c` passed full admission across 9,011 objects and
9,050,119,070 bytes in 35.15 seconds at 259,508 KiB max RSS and zero swap.
Independent execution review 141 PASSed the design after fresh root traversal,
stable 13-container privileged Docker reconciliation and an exact scratch-device
immutable-flag probe. The reviewed `sudo -A` command ran once: wrapper
3871615/89921496 and packet 3871619/89921507 exited 0 with empty stdout/stderr.

Independent runtime review 143 PASSes retirement of candidate `67589154-1` and
its metadata backup. The 21,202-record journal pairs every deletion for 10,509
candidate and 86 backup members, removes both roots, and ends terminal PASS.
Two observer rounds were clean, the complete Docker census stayed stable, all
packet/observer/reader processes retired, and originals plus quarantines are
absent. Live packet status `aaab70bd...ae97`, evidence `3004ef56...e24`, journal
`0f87b33a...c1a` and claim `25357a94...44be` are archived completely at
`evidence/stability-native-exact-retirement-runtime-67589154-20260929-1.tar.gz`
SHA256 `840c1e95...c0d`. Preserve the immutable consumed-attempt tombstone at
scratch device/inode 1831/31470, SHA256 `ac3d1895...f34`; it is not an active
build owner and does not conflict with the distinct `704f6654-1` lease.

Next obtain independent source/execution review of preparation packet
`native-exact-candidate-preparation-704f6654-1.sh` SHA256 `7502c748...3a0a`,
then reconcile its nine absent targets and run it once if released. Review its
result before one serialized heavy current-candidate build, then run the
smallest real memory application diagnostic. Current-candidate builds remain
zero and real guest applications this window remain zero; applications remain
0/273 and formal counters remain unchanged.

Continuation checkpoint 145, 2026-09-29: independently reviewed preparation
packet `7502c748...3a0a` ran once under its 600-second supervisor and exited 0.
Outer evidence retained `TOPOLOGY_PASS` and `LOG_FINAL_FSYNC=PASS`; the durable
log `dade9c20...f643` ends terminal/preparation RC 0 with no live children.
Independent review 145 PASSes preparation evidence: candidate
`704f6654...63561` and IHK `3114d9e7...72a1f` are exact at dev/inode 26/36767,
backup 26/47413, both 0755 and uid/gid 1000. Installed metadata, closure, index,
ABI and manifest verification pass.

Manifest `b8d89bf8...e3b1`, request `891c24c0...a2f` and receipt
`05055889...e6e8` are preserved with the metadata backup in archive
`evidence/stability-native-exact-preparation-704f6654-20260929-1.tar.gz`
SHA256 `e9ae5ac4...f306`. Independent `BuildOwner.validate()` passes with
21,970,231,296 bytes required under the 24-GiB aggregate ceiling; output and
evidence roots are empty and the new lease is absent. Preserve the 9.08-GiB
candidate and backup unchanged.

Next obtain a fresh independent one-shot heavy-build release for exact command
`/usr/bin/python3 -E -s -B /dev/shm/mckernel-exact-candidate-704f6654-1/scripts/native_rust_exact_build_container_owner.py /home/holden/mckernel-work/scratch/native-exact-build-request-704f6654-1.json`.
Bind current roots, request, owner/driver, image, empty destinations, resources,
all leases and Docker state. Only after PASS run one serialized build, review its
retained terminal container/evidence, then start the smallest real memory app
diagnostic. Builds remain zero; real guest apps this window remain zero;
applications remain 0/273 and formal counters are unchanged.

Continuation checkpoint 147, 2026-09-29: the independently released exact
`704f6654-1` heavy build ran once and failed after 19.99 seconds in phase 0.
Every earlier source contract passed, including the prior queue-parser repair;
the first failing command was the exact Rust queue checker. Rustc returned 0
with empty stderr, then the checker reported `rustc did not create an executable
queue fixture` for its temporary output. This is a new output-location family,
not a retry of the `67589154-1` parser failure. No compilation phase or artifact
output began.

Owner 3881008/90041045 and all Docker clients retired; the exact lease is absent.
Terminal container `68881c05...927a6` is retained, exited 1, PID 0, non-OOM and
restart disabled. Owner receipt `f49164f5...5914`, build receipt
`63f155fb...1286`, driver log `c61ca4ed...6b46`, container log
`449c39bc...ad3c` and terminal inspect `eeb4f261...134c` are archived at
`evidence/stability-native-exact-build-704f6654-failure-20260929-1.tar.gz`
SHA256 `e09ca937...8417`. Preserve candidate, backup, container and evidence.

Do not rerun the unchanged request. The one bounded correction is to add exact
post-compile diagnostics and select a verified writable executable fixture
location, then run an isolated exact Rust compile/seven-test regression under
the reviewed light profile. Only after source review and a wholly fresh
commit-derived candidate/request may another heavy build be considered.
Successful current-candidate builds remain zero, real guest apps this window
remain zero, applications remain 0/273 and formal counters are unchanged.

Shutdown checkpoint 148, 2026-09-29: new dispatch stopped immediately on the
launcher shutdown request. All child lanes are terminal, no bounded operation
is running, the heavy lease is absent, and no build or guest remains active.
Preserve boot `c733d83b...9afd` and launcher identities 3399308/83682487,
3399313/83682494 and 3399317/83682500. The failed owner 3881008/90041045 and
its Docker clients are retired.

The original phase-0 evidence stays authoritative and unchanged. Candidate
`704f6654-1` remains at device/inode 26/36767, its metadata backup at 26/47413,
and terminal container `68881c05...927a6` remains exited 1, PID 0, non-OOM,
restart disabled. The artifact output root is empty; the evidence root retains
the driver, per-command results, container records and receipt. Available bytes
at shutdown were host 23,679,508,480, scratch 21,554,311,168 and tmpfs
7,502,585,856, with 19,563,268 KiB MemAvailable. No cleanup or retry occurred.

On the next authorized invocation, first reconcile these identities and retained
roots. Then reproduce whether the reviewed container temporary filesystem is
non-executable, apply one bounded queue-checker correction with exact
post-compile diagnostics and a verified executable fixture location, and run
the isolated exact Rust compile/seven-test regression under the reviewed light
profile. Obtain independent source review, then prepare a wholly fresh
commit-derived candidate/request before considering another serialized heavy
build. Never rerun the unchanged `704f6654-1` request. Record
`stability-shutdown-checkpoint-20260929-148.json` is the live cursor. Formal
counters do not move, successful current-candidate builds remain zero, real
guest applications this window remain zero, applications remain 0/273, and the
OS remains incomplete; the launcher pause is temporary.

Continuation checkpoint 149, 2026-09-29: the `704f6654-1` phase-0 failure is
now reproduced and corrected without rerunning its consumed heavy request. The
pinned container mounts `/tmp` `noexec`: exact Rust 1.92 creates a regular 0755
fixture there, but `access(X_OK)` is false and execution returns 126. The same
unchanged fixture on the writable evidence-style bind mount executes all seven
tests. Corrected cause-probe container `bfd1b859...cbe2` exits 0. The first
probe `e24b84b4...f331e` is retained as an observer failure: it omitted the
image's `/usr/bin/sleep` entrypoint override and performed no fixture action.

Checker `84634d62...a46c` now uses the offline driver's existing
`RUNNER_TEMP=/evidence/build` after fail-closed absolute-directory validation,
preserves the safe tempfile default when unset, and distinguishes missing,
non-regular and non-executable compiler output. Tests `83032bf2...41c8` pass
34 cases under the default Python 3.9.12 and `/usr/bin/python3.8`; compilation
and diff checks pass. Independent review PASSes this bounded source correction
with no blocking finding. Production Rust, contract, fixture and seven-test
oracle are unchanged.

Corrected checker container `d778b8fa...bc44` uses the reviewed unprivileged
2-CPU/2-GiB/no-network profile, exact Rust 1.92 and executable bind-backed
`RUNNER_TEMP`; it verifies the source contract, executes all seven tests, cleans
its temporary directory and exits 0, non-OOM, restart disabled. Archive
`evidence/stability-native-queue-fixture-exec-location-success-20260929-1.tar.gz`
SHA256 `9002fe60...3d6c` preserves all three terminal inspections/logs, exact
source/contract/driver bindings and the passing binary. This is light fixture
evidence only: no current-candidate build, module, guest, application or gate
credit follows.

Next commit/push/fetch these exact bytes. Then use the prior preparation packet
only as a template to bind the fetched correction into a wholly fresh candidate,
metadata backup, manifest, request, output, evidence and lease namespace. Obtain
fresh preparation review before one preparation run, review its result, and seek
a new one-shot heavy-build release only after capacity passes. Never reuse or
rerun `704f6654-1`. Formal counters remain unchanged, successful current-candidate
builds remain zero and real guest applications this work window remain zero.

Continuation checkpoint 150, 2026-09-29: fresh candidate preparation cannot
start while consumed `704f6654-1` occupies 9,083,990,016 allocated tmpfs bytes.
No ad-hoc deletion is permitted. The accepted retirement flow first requires a
small exact inventory/restoration capsule; the existing preparation and failure
archives do not contain the candidate checkout and cannot substitute for it.

Non-destructive retention-preparation DRAFT `3c684c86...e8b86` and tests
`a5496af2...c59c4` differ from the accepted 675 packet only in exact main
commit, candidate/backup identities, fresh output names, competing lease name
and the unreleased sentinel. Eighteen packet tests pass; the packet plus capsule
and archive support suites pass 46 tests on both Python 3.8 and default Python
3.9.12. Independent review PASSes its source/execution design with no blocking
finding, but releases no execution. It remains `RELEASE_HASH_REQUIRED`.

The later retirement DRAFT `3fd47e37...1bb37` and tests
`bfeffba9...43b6d` pass 79 tests and bind the exact consumed build failure, but
they deliberately retain inventory, capsule, success and release sentinels.
They fail closed before privileged action and cannot be finalized until the
retention outputs exist and receive independent result review. Candidate and
backup 26/36767 and 26/47413 remain untouched; no traversal, capsule, archive,
retirement, Docker mutation, build or guest occurred.

Next commit/push/fetch this exact DRAFT template, mechanically generate a
retention-preparation release that changes exactly its sentinel and adds one
release JSON, and obtain separate exact mechanical/execution review. After one
ordinary-user run, independently inspect inventory, capsule, child retirement,
claim/lease cleanup and reconstructible Git objects before finalizing any
retirement release. Record
`stability-native-exact-retention-704f-template-success-20260929-1.json`
preserves this scope. Formal counters remain unchanged, successful builds remain
zero and no real guest application has run in this work window.

Continuation checkpoint 151, 2026-09-29: fetched release `abc5d67a...44efc`
authorized one ordinary-user retention-preparation run. An outer supervisor
preflight first rejected an incorrectly expanded abbreviated packet hash before
creating any path or invoking the packet; the corrected full hash then ran once.
Supervisor 3893796/90191735, packet 3893798/90191735 and planner/archive/
postflight workers 3893811/90191746, 3894238/90193774 and 3894258/90194657
all exited 0 and are absent with no group/session survivors.

Independent result review PASSes 10,609 live entries, byte-identical original
and postflight inventories `4067c653...61b8e1`, exact 924-member USTAR capsule
`b6c85e40...ecec1`, 49 reconstructible links and canonical streaming of 7,728
main plus 1,296 IHK objects totaling 9,054,576,822 bytes. Candidate/backup
identities remain 26/36767 and 26/47413; claims, leases and partial files are
absent. Fresh postflight Docker evidence preserves all 17 IDs and the four
terminal containers referencing the candidate. Raw evidence archive
`stability-native-exact-retention-preparation-success-raw-704f6654-20260929-1.tar.gz`
has SHA256 `b06ce4f4...2cd72`. This capsule depends on the canonical Git stores;
no extraction replay or retirement follows from it.

Full retirement-template review then BLOCKed rejected packet
`19f598b3...d5f6d`: it retained prior-candidate Docker IDs and declared but did
not read the preserved 704f build-failure artifacts. The additive correction
keeps generic helper `704a3f5f...df54b` unchanged. New 704f helper
`46311908...c517` validates exact full Config/HostConfig/State/Mounts for the
four terminal candidate users and rejects every unknown protected-tree mount.
Packet admission now checks the failure record, archive and shutdown checkpoint
hashes before euid, output or tombstone activity. Corrected packet
`51d7c6d0...ee215` and tests `2e6e4e58...83f75` bind the accepted retention
artifacts and exact 7,728/1,296 routing. Python 3.8 and 3.9 each pass 121 tests;
independent rereview PASSes source only. `RELEASE_HASH_REQUIRED` remains.

Next commit/push/fetch this exact DRAFT template and retained evidence, then
mechanically generate a retirement release changing only the packet sentinel
plus one release JSON. Obtain separate exact execution review and fresh complete
root/member/object, Docker, observer, lease, namespace, immutable-filesystem and
resource preflight before any one-shot `sudo -A` invocation. No retirement,
new build, guest, application or formal counter advance has occurred; real guest
applications this work window remain zero.

Shutdown checkpoint 152, 2026-09-29: new dispatch stopped on the launcher
shutdown request. Every child lane is terminal and no bounded operation, heavy
build, guest or lease remains active. Preserve launcher wrapper 3399308/83682487,
worker 3399313/83682494 and app-server 3399317/83682500. The completed
retention-preparation process identities remain supervisor 3893796/90191735,
packet 3893798/90191735, planner 3893811/90191746, archive
3894238/90193774 and postflight 3894258/90194657; all exited 0 and are absent.

Candidate `704f6654-1` and its metadata backup remain untouched at device/inode
26/36767 and 26/47413. Terminal build container `68881c05...927a6` remains
exited 1, PID 0, non-OOM with restart disabled. Host, scratch and tmpfs available
bytes at shutdown are 23,548,321,792, 21,533,806,592 and 7,502,585,856;
MemAvailable is 19,383,656 KiB. The retirement packet still contains
`RELEASE_HASH_REQUIRED`, so no privileged retirement is authorized.

The next authorized invocation must first reconcile those identities and exact
retained hashes. Then fetch-verify this checkpoint, generate only the mechanical
two-path retirement release, obtain separate execution review, and repeat the
complete live preflight before considering its one-shot `sudo -A` execution.
Only accepted retirement may unlock a wholly fresh commit-derived candidate.
Never rerun the consumed `704f6654-1` build request. Formal counters remain
unchanged, successful current-candidate builds remain zero, real guest apps this
window remain zero, and the OS remains incomplete; this launcher pause is
temporary.

Continuation checkpoint 153, 2026-09-29: finalized v1 retirement release
`1dfd498b...ab01a1` was pushed/fetched at `342de408...18f5` and independently
passed its exact two-path mechanical binding, all 10,609 live identity/content
checks, fresh privileged 17-container/four-terminal census, boot/launcher/path
checks and immutable-filesystem capability inspection. It was correctly BLOCKed
before execution: after read-only verification, `SC_AVPHYS_PAGES` reported only
3,232,337,920 bytes against the unchanged 4-GiB floor. No output, tombstone,
quarantine, deletion or retirement packet execution occurred.

A coordinator read-only admission reproduction began with 11,151,843,328 strict
free bytes, streamed the exact 7,728 main plus 1,296 IHK objects in 38.215 seconds,
and ended with 3,269,971,968 strict free bytes while Linux MemAvailable remained
19,827,306,496. This proves an observer-ordering defect: reclaimable canonical
pack cache was counted as unavailable by the old SC_AVPHYS metric. V1 remains
immutable, blocked and unexecuted.

Additive v2 DRAFT `84015a3f...43e3b` replaces only that observation with a
fail-closed parser for Linux's unique nonzero bounded `MemAvailable` decimal kB
field, retaining the numeric 4-GiB floor and every retirement/ownership check.
Its first parser candidate rejected Linux's aligned spaces; the bounded
correction accepts only ASCII spaces/tabs. Independent review then BLOCKed an
unsafe fresh `-2` build lease; the correction restores the consumed owner's exact
`native-exact-build-lease-704f6654-1.json` shared exclusion while keeping v2
quarantine/evidence names fresh. Corrected tests `de7a3448...7ac1` pass 110 cases
under Python 3.8 and 3.9; live MemAvailable is 19,778,138,112 bytes and independent
rereview PASSes source only. `RELEASE_HASH_REQUIRED` remains.

Next checkpoint/push/fetch this v2 DRAFT and failure lineage, then mechanically
generate a v2 release changing only its sentinel plus one release JSON. Obtain
fresh independent execution review and repeat every live preflight before at
most one `sudo -A` run. No retirement, build, guest, application or formal
counter advance has occurred; real guest apps this work window remain zero.

Shutdown checkpoint 154, 2026-09-29: the released v2 packet ran once and failed
closed after atomically quarantining the exact candidate and metadata roots but
before deletion. Packet 3912447/90493097 is terminal and absent. The sealed
historical observer rejected the new quarantine names; its journal records
terminal failure and no deletion phase. Preserve candidate quarantine
26/36767, metadata quarantine 26/47413, root-owned evidence 26/47525, and the
immutable consumed-build tombstone 1831/31474. Never retry or roll back this
consumed packet. Failure record
`stability-native-exact-retirement-704f6654-failure-20260929-1.json` and raw
archive `stability-native-exact-retirement-704f6654-failure-20260929-1.tar.gz`
retain the original evidence; the archive intentionally excludes the 9-GiB
quarantine contents.

Observer adaptation `6feda9c9...10a42` and its six tests pass under Python 3.8
and 3.9; independent review accepts only its exact four-path-literal change.
The first continuation DRAFT `fe7a22fa...d40a` plus wrapper/basis/tests remains
BLOCKED despite nine passing tests per runtime. Independent review identifies
seven required corrections: authenticate and invoke a finalized acyclic
release; inherit and retire the observer callback FD/process group; validate
the observer's real six-field set schema; reconcile all 17 containers and four
terminal exceptions; restore fail-closed PID/starttime/boot/conflict gates;
rehash and rebind descriptors/names immediately at unlink; and durably publish
all success/failure/survivor evidence under partial-write, fsync, close and
interruption faults. No execution release exists.

All child lanes are terminal. Preserve launcher wrapper 3399308/83682487,
worker 3399313/83682494 and app-server 3399317/83682500. Shutdown capacity is
host 23,420,751,872, scratch 21,529,010,176 and tmpfs 7,502,475,264 available
bytes, with 19,231,856 KiB MemAvailable. On the next authorized invocation,
first reconcile these identities and retained roots, then make one expert
correction covering the seven review findings and rerun source/unit review.
Do not execute, retry, rename, delete or roll back any retirement state until a
fresh independently reviewed release and complete live preflight exist. Record
`stability-shutdown-checkpoint-20260929-154.json` is the live cursor. Formal
counters remain unchanged, successful current-candidate builds remain zero,
real guest apps this window remain zero, applications remain 0/273, and the OS
remains incomplete; the launcher pause is temporary.

Continuation checkpoint 155, 2026-09-29: the consumed v2 failure remains
unchanged, but its fresh quarantine continuation now passes independent source
review after a required strategy change. Two Terra correction cycles exposed
cyclic self-hashes, an impossible finalized invocation, mismatched observer and
Docker schemas, incomplete descendant retirement and lossy failure cleanup.
Rather than rename or retry that design, a fresh Astra owner replaced it with
an acyclic fetched-commit authority. Packet and wrapper each have one exact
DRAFT boolean; the non-authorizing basis receives only literal JSON-value
source hashes; a future external release binds the template ancestor, exact
four-path diff, derived final blobs and live runtime authority without carrying
or injecting its own hash.

Exact DRAFT packet `0f3c4400...418b`, wrapper `7b41bb6f...e4ef`, basis
`241feb5c...ac1f` and tests `1f409919...3ae4` pass 26 cases under Python 3.8
and default Python 3.9.12. The tests mechanically finalize the real templates,
execute finalized main with runtime mutation mocked, and reject substituted
artifacts, ancestry/diff/schema/path errors. They also cover actual six-field
observer output, inherited sealed FDs, bounded pidfd/session retirement,
17-container/four-exception validation, boot/PID/lease conflicts, no-follow
hash/target/name deletion, mutable tmpfs directory size, combined primary and
cleanup faults, terminal-write signals and a continuous TERM/INT storm. Syntax,
compilation and diff checks pass.

Independent rereview PASSes these exact source hashes. Termination uses two
fixed saturating latch slots and finite blocked snapshots; terminal persistence
has at most eight attempts and fails closed with signals blocked if arrivals do
not settle. No release was created and no sudo, Docker, build, guest, protected
root traversal or deletion occurred. Preserve quarantines 26/36767 and
26/47413, historical evidence 26/47525 and immutable tombstone 1831/31474.
Next commit/push/fetch this DRAFT source checkpoint, then mechanically derive
only packet, wrapper, basis and a new external execution release from the
fetched template. Obtain independent exact mechanical/execution review and a
fresh complete live preflight before one one-shot sudo run. Record
`stability-native-exact-quarantine-continuation-source-success-704f6654-20260929-1.json`
is source evidence only. Formal counters, successful current-candidate builds
and real guest applications remain zero; applications remain 0/273.

Continuation checkpoint 156, 2026-09-29: read-only release preflight found the
expected 17 Docker containers and the exact four exited protected-mount users,
but it also exposed a credential-retention risk before release generation. Full
`docker inspect` objects contain arbitrary `Config.Env` values and therefore
must not be committed or written into evidence. The first ordinary-user Docker
command correctly failed permission-denied without changing state; the repeated
read-only census used `sudo -A`. No environment values were printed or stored,
and the accidentally created empty `/tmp` output was verified size zero and
unlinked.

Packet `a1539505...3edf` now hashes each complete canonical inspect object only
in memory. The future external release stores exactly 17 ID-to-SHA256 bindings
and four safe protected-mount exceptions. Only Mounts array order is normalized;
all other fields and array order remain exact, so any secret-value mutation
changes the digest. Before/after evidence persists only ID, record digest,
selected terminal state, restart policy and protected mounts; Config, Env,
labels, state error text and arbitrary inspect data cannot enter the evidence.

Tests `f9c38fbb...70e9` pass 28 cases under Python 3.8 and 3.9, including secret
mutation/redaction, mount-order normalization and the 17/four/state/restart/
unknown-mount gates. Independent review PASSes the exact packet, unchanged
wrapper `7b41bb6f...e4ef`, basis `241feb5c...ac1f` and test hashes. This remains
source-only; no release, Docker mutation, protected-root access, deletion,
build or guest occurred. Next push/fetch this DRAFT privacy correction, then
mechanically finalize exactly packet, wrapper and basis while adding the safe
external release as the fourth changed path. Obtain independent mechanical and
execution review before sudo continuation. Record
`stability-native-exact-quarantine-continuation-docker-privacy-success-704f6654-20260929-1.json`
preserves this correction. Formal counters and real guest applications remain
unchanged.

Shutdown checkpoint 157, 2026-09-29: the launcher requested an immediate
checkpoint before finalization or execution. No new task was dispatched; all
child lanes are terminal. Wrapper 3399308/83682487, worker 3399313/83682494 and
app-server 3399317/83682500 remain live, while consumed packet
3912447/90493097 remains absent. Candidate quarantine 26/36767, metadata
quarantine 26/47413, historical evidence 26/47525 and immutable tombstone
1831/31474 remain unchanged; deletion, retry and rollback remain forbidden.

Fetched/upstream source checkpoint `f89cc5b8640fbae4119f851571c9254d38579f55`
retains the independently source-reviewed privacy correction. No external
execution release exists and no finalization, protected-root traversal, Docker
mutation, deletion, build or guest occurred. On the next authorized invocation,
reconcile the identities and retained roots first; inspect the exact runtime and
Docker release schemas; then derive the exact four-path finalization (packet,
wrapper, basis and safe external release) from fetched `f89cc5b8`. Commit that
mechanical finalization alone, obtain independent mechanical and execution
review, and repeat the complete live preflight before considering one one-shot
sudo continuation. Record `stability-shutdown-checkpoint-20260929-157.json` is
the live cursor. Formal counters, successful current-candidate builds and real
guest applications remain zero; applications remain 0/273 and the OS remains
incomplete. The launcher pause is temporary.

Continuation checkpoint 158, 2026-09-29: resumption found and repaired a
deterministic launch blocker before generating an execution release. A harmless
sudo ancestry probe proved the wrapper's direct `/usr/bin/sudo` parent retains
the canonical packet pathname in argv, so the accepted conflict scanner would
reject its own launch. The first bounded correction `6a29b462...00882` passed
29 tests but independent review BLOCKed it: the census exempted a bare parent
PID after validation, allowing reproduced reparent/PID reuse, compared volatile
status counters, and accepted extra trailing NUL argv fields.

Per convergence policy, an Astra expert replaced that candidate with exact DRAFT
packet `ae2f6d07...a1e9` and tests `fadd0322...18b6`. Direct sudo authority now
retains parent and child PID/starttime/PPID tokens, exact executable, exact
NUL-terminated argv and parsed root Uid/Gid. Both the sudo and released launcher
identities are revalidated when an exemption is applied and again before census
success; bare PID allowances reject and the complete forbidden set is unchanged.
Thirty-five tests pass under Python 3.8 and 3.9, including all four prior
post-admission/post-skip reuse windows, disappearance, reparent, credential/
argv/executable churn, malformed inputs and harmless volatile status changes.
Compilation and diff checks pass. Independent review PASSes source only.

No external release, protected-root operation, Docker mutation, deletion, build
or guest occurred. The packet and wrapper remain inert. Record
`stability-native-exact-quarantine-continuation-sudo-parent-success-704f6654-20260929-1.json`
preserves the failure lineage. Next commit/push/fetch this source correction and
use that fetched commit as the template ancestor for the exact four-path
finalization. Then obtain independent mechanical/execution review and repeat
the full live preflight before any one-shot sudo continuation. Formal counters,
current-candidate builds and real guest applications remain zero; applications
remain 0/273.

Continuation checkpoint 159, 2026-09-29: fetched four-path release
`fc529820...ae607` independently PASSed mechanical/execution review, but the
coordinator's immediately preceding external read-only preflight correctly
stopped before wrapper invocation, claim or deletion. `validate_raw_history`
reported `raw archive membership`: the pinned raw archive's directory TarInfo
name is `.mckernel-retirement-evidence-704f6654-2` without a trailing slash,
while the source expected the slash form. All eleven actual members, the pinned
archive SHA and retained roots remained unchanged. This also corrects the prior
review's overly broad live-preflight statement; it had not executed this exact
validator.

The local packet, wrapper and basis were immediately restored to inert DRAFT
before tests. Bounded packet `682a3791...dcc8` and tests `a8df1959...76c2`
accept the exact TarInfo directory name while preserving the pinned SHA, exact
eleven-member set/type, duplicate rejection, live name/byte equality and exact
tombstone bytes. The actual retained history now passes read-only validation;
37 tests pass under Python 3.8 and 3.9 with positive no-slash and missing/extra/
wrong-type/duplicate negatives. Independent review PASSes source only and
confirms the failed fetched release rejects against the changed DRAFT bytes.

No wrapper execution, claim, journal, output, Docker mutation, root deletion,
build or guest occurred. Release `fc529820` remains immutable in Git history and
must never run. Record
`stability-native-exact-quarantine-continuation-archive-member-source-success-704f6654-20260929-1.json`
preserves this failure and correction. Next commit/push/fetch the DRAFT, use the
new fetched commit as template authority, regenerate the exact four paths,
obtain fresh independent execution review and repeat the complete external
preflight before one one-shot wrapper invocation. Formal counters, builds and
real guest applications remain zero; applications remain 0/273.

Continuation checkpoint 160, 2026-09-29: corrected fetched release
`ef8dffa1...9986` passed fresh independent and coordinator preflight, then ran
exactly once. The durable journal records 21,226 ordered deletion entries and
`terminal-success` with null failure. All 10,523 candidate and 86 metadata
members, both quarantine roots and both original names are absent. Observer
3952221/91172574 exited 0 and retired without survivors; Docker before/after
safe summaries are byte-identical. Claim 1831/31475, journal 1831/31476 and
output 1831/2907441 remain root-owned, historical evidence 26/47525 and immutable
tombstone 1831/31474 remain unchanged. Archive
`stability-native-exact-quarantine-continuation-success-704f6654-20260929-1.tar.gz`
SHA `16cafe64...af2` preserves all ten live artifacts. Physical cleanup reclaimed
tmpfs to 16,587,804,672 available bytes.

Independent postflight nevertheless BLOCKs complete retirement proof. Observer
v7 scanned `/proc/<pid>/task/<tid>/map_files`; that directory is absent on this
host, while process-level `/proc/<pid>/map_files` is populated. Both rounds
therefore report zero mapping entries and 1,636 accepted directory absences. An
mmap-only reference after descriptor close could have been missed. The packet is
consumed and must never rerun; the trees stay deleted and the physical result is
not retroactively promoted. Wrapper/packet PID attribution was also not retained;
only observer identity is exact.

Record `stability-native-exact-quarantine-continuation-runtime-blocked-704f6654-20260929-1.json`
separates physical success from deficient reference proof. Next create an
additive corrected observer using process-level `map_files`, fail closed on
uninspected live address spaces, add an mmap-only regression, independently
review it, and run a fresh current-state deleted-inode audit over every retained
inventory identity before authorizing a wholly fresh candidate build. Formal
counters, successful current-candidate builds and real guest applications remain
zero; applications remain 0/273.

Continuation checkpoint 161, 2026-09-29: additive observer v3 repairs the
mapping-coverage defect without changing historical v2. Exact v3
`14789e10...7139` and tests `9e145133...3956` scan process-level
`/proc/<tgid>/map_files`, fail closed when a live address space cannot be
inspected, revalidate individual disappearance, require bounded hexadecimal
VMA ranges with `start < end`, and retain referenced device/inode. The first
candidate was independently BLOCKed for accepting equal/reversed ranges and a
vacuous mmap test; its bounded correction routes a real descriptor-closed libc
mapping through production `scan_identity` and rejects all prior range probes.
Eight tests and self-test pass on Python 3.8/3.9; independent rereview PASSes
source only.

This cannot retroactively accept checkpoint 160. A separate current-state
deleted-inode audit remains required against the sealed 10,611-identity set.
Its first candidate and bounded correction were both independently BLOCKed for
mount alias, identity reconciliation and map-entry error false PASSes, so that
lane is now under expert redesign. Record
`stability-native-exact-live-reference-observer-map-files-source-success-704f6654-20260929-1.json`
preserves v3 source evidence. No new root audit, build or guest has run; formal
counters, builds and applications remain unchanged.

Shutdown checkpoint 162, 2026-09-29: the expert deleted-inode audit source is
now independently PASS_SOURCE at helper `997c8b80...2406` and tests
`cbe06f64...9ab8`. Twenty-two tests pass under both Python 3.8 and 3.9. The
review replayed the prior identity-reconciliation, PID/TID reuse, stale-anchor,
empty-census, map-entry, mount-alias, malformed/changing namespace, short/zero
write, fsync and self-FD failure families. The actual retained archive and
inventory remain pinned to 10,611 distinct identities with canonical identity
set SHA `3ee0942c...a1e8` and root counts 10,524 plus 87.

This is source-only evidence. No privileged audit, build, Docker operation or
guest ran, and the consumed retirement proof is still BLOCKED. The unprivileged
descriptor-free mmap probe found its exact mapping but target stat returned
EPERM, so successful real device/inode observation remains an explicit root-run
requirement. All child lanes are terminal. Launcher wrapper 3399308/83682487,
worker 3399313/83682494 and app-server 3399317/83682500 remain live; historical
evidence 26/47525 and immutable tombstone 1831/31474 remain preserved. Record
`stability-native-exact-deleted-inode-audit-source-success-704f6654-20260929-1.json`
is the shutdown cursor.

The next launcher continuation must first verify this fetched checkpoint and
the three live identities, then create an exact fresh root read-only execution
release and obtain independent execution review. Only then run exactly three
audit rounds against the sealed baseline. Never rerun either consumed packet;
never promote sampled current-state evidence to retrospective retirement proof.
Formal counters remain 6/130 and 350/10000, successful current-candidate builds
and real guest applications remain zero, applications remain 0/273, and the OS
is incomplete. The launcher pause is temporary.

Continuation checkpoint 163, 2026-09-29: proposed root audit release attempt 1
at fetched `dcc3f8f8...ab6e` was independently BLOCKed before sudo. Stable host
PF_KTHREAD tasks, including PID 2/starttime 13, legitimately lack process
resources, so helper `997c8b80...2406` could not satisfy its promised clean
census. The proposal `cd3aa38f...2e74` was never executed and must never run.

The first bounded surface correction was independently BLOCKed because negative
flags granted PF_KTHREAD absence and missing mount namespaces skipped present
mountinfo aliases. Per convergence policy, an Astra expert redesigned the typed
surface handling. Its first candidate was also BLOCKed on out-of-range LP64 stat
fields and greater-than-64-bit VMA ranges; the bounded expert correction now
independently PASSes helper `47e741e7...6d88` and tests `0e217fbb...9e3`.
Forty-four tests pass on Python 3.8/3.9 and 59 additional complete-census probes
pass. Valid self/PID2 rows parse; malformed special rows, permission errors,
reuse, class/census churn, mount aliases and invalid VMA ranges fail closed,
while every existing special-process surface remains inspected.

Record
`stability-native-exact-deleted-inode-audit-proc-surface-source-success-704f6654-20260929-1.json`
preserves the full failure family. No privileged audit, build, Docker operation
or guest ran. Next commit/push/fetch this source, then generate a fresh attempt-2
basis/release bound to that fetched commit and obtain fresh independent execution
review. Never execute attempt 1 and never treat a later sampled PASS as
retrospective retirement acceptance. Formal counters, builds and applications
remain unchanged.

Continuation checkpoint 164, 2026-09-29: fetched attempt-2 release
`149d458e...1e84` independently PASSed execution review and ran exactly once.
It exited 1 after 2.149 seconds with empty streams and durable root-owned result
1831/31477 SHA `f5c1e35e...ee8`. All three rounds scanned 271 processes,
47 tasks and 33,881 mapping entries with zero mapping denials and zero retained
target references, but each failed closed on 267 mountinfo parser errors; the
cascade cleared identities and produced three missing anchors, one unstable
census and one process-census-churn failure. Archive `e0e206b3...e171` retains
the exact result/release/basis/source-review. It lacks a separate outer-status
receipt, so the coordinator capture is the authority for exit 1/empty streams.

The immediate cause was absolute-only parsing of canonical nsfs roots such as
`mnt:[id]`. A further live root diagnostic found ordinary chrooted PID 868/398
has root `/etc/avahi`, an empty filtered mountinfo and namespace
`mnt:[4026531841]`, while PID 1, PID 2 and the launcher share that namespace with
root `/` and a complete view. Equal namespace tokens plus an empty chroot view
cannot prove alias absence because Linux filters mounts outside the task root.
After the ordinary correction was BLOCKed on this coverage gap, an Astra expert
implemented namespace-level completeness. Exact helper `641c39a3...d7ab2` and
tests `af9ab213...6904` independently PASS source: 56 tests pass on Python
3.8/3.9, and every observed namespace now requires a revalidated root-`/`,
nonempty parsed representative; filtered views defer only within that exact
namespace.

Record
`stability-native-exact-deleted-inode-audit-runtime-failure-704f6654-20260929-2.json`
preserves the result and correction. Attempt 2 is consumed and must never retry.
No current-state reference-absence, build, guest, application or production
acceptance exists. Next commit/push/fetch this correction, then create a fresh
attempt-3 basis/output/release and obtain independent execution review.

Shutdown checkpoint 165, 2026-09-29: the corrected attempt-3 read-only root
audit is prepared and independently `PASS_EXECUTION_RELEASE` at fetched commit
`ce0a39ee73c55e410c79ed57f989fbc9a4f32f6f`. Basis
`be181ad8...9c75`, release `4760b966...cb98`, helper `641c39a3...7ab2` and
tests `af9ab213...6904` remain byte-exact. The release authorizes one invocation
of its recorded `sudo -A` argv only after its complete immediate preflight,
including privileged verification of the immutable tombstone flag and bytes,
and requires a separate durable exit/stdout/stderr receipt plus independent
runtime review before any candidate preparation.

The shutdown arrived before that preflight or invocation. No sudo command,
root audit, build, Docker operation or guest ran in this shutdown window. Fresh
output
`/home/holden/mckernel-work/scratch/native-exact-candidate-deleted-inode-audit-704f6654-3.json`
is absent, so attempt 3 is authorized but unconsumed. Attempts 1 and 2 remain
permanently non-runnable. All child agents are terminal. Launcher wrapper
3399308/83682487, worker 3399313/83682494 and app-server 3399317/83682500 still
match their preserved process identities; historical evidence 26/47525 and
immutable tombstone 1831/31474 remain the retained-state anchors.

The next launcher continuation must verify this fetched shutdown checkpoint,
reconcile those live identities, keep dispatch quiescent, and perform the full
released attempt-3 preflight. If every condition still matches, invoke the
exact released command once, preserve the result and a distinct outer-status
receipt without retry, then obtain independent runtime review. Only a reviewed
PASS may unlock wholly fresh candidate preparation; it cannot retroactively
accept the consumed retirement. Formal counters remain 6/130 and 350/10000,
successful current-candidate builds and real guest applications remain zero,
applications remain 0/273, and the OS remains incomplete. The launcher pause
is temporary.

Continuation checkpoint 166, 2026-09-29: the attempt-3 deleted-inode audit
passed its complete immediate preflight and ran exactly once with the released
argv. It exited 0 after 8.673624604 seconds with empty stdout and stderr. The
exclusive root-owned result is 1831/31478, mode 0600, size 1,128 and SHA
`ed82eba0...7903`. All three rounds report 271 processes, 816 tasks and stable
identities, 33,882 map-file entries, and zero references, failures, denials or
reconciled exits. The sealed target remains exactly 10,611 identities with
canonical digest `3ee0942c...a1e8` and root counts 10,524 plus 87.

Fresh independent review returned `PASS_RUNTIME_REVIEW`. It recomputed the
target from the archived observer, inspected namespace completeness and every
round, matched the exact release/basis/helper/toolchain bindings and receipt,
and rechecked the live boot, three launcher identities, scratch parent,
historical evidence 26/47525, immutable tombstone 1831/31474 and absent tree
names. Receipt `1401bb83...fb6` and archive `842f5d3f...b8be` preserve the outer
status and the release, basis, receipt and raw result. Attempt 3 is consumed and
must never run again.

This is sampled current-state absence only. It does not retroactively repair the
consumed retirement proof and grants no build, guest, production-gate or
application acceptance. It unlocks fresh candidate preparation. After this
record is committed, pushed and fetch-verified, derive an entirely new nonce
and path family from the fetched main commit plus IHK
`3114d9e7101ad52030eb3effa849a5c108972a1f`, using the existing preparation
profile only as a template. Never use the dirty nested IHK checkout directly or
reuse `67589154-1`/`704f6654-1` artifacts. Obtain independent preparation review
before its one-shot execution, then seek a distinct build release. Formal
counters remain 6/130 and 350/10000; current-candidate builds and real guest
applications remain zero, applications remain 0/273, and the OS is incomplete.

Continuation checkpoint 167, 2026-09-29: fetched preparation packet
`7e3c4897...a0010` and release `45c61dac...f0d1` passed independent execution
review and ran exactly once. It exited 0 with the exact topology line and outer
`LOG_FINAL_FSYNC=PASS`, empty stderr, and no surviving timeout, packet,
process-group, session or descendant identities. Candidate
`/dev/shm/mckernel-exact-candidate-f5d8d914-1` is 26/47678, uid/gid 1000,
mode 0755, and pins fetched main `f5d8d914...430b` plus IHK `3114d9e7...72a1f`.
Metadata backup is 26/58429 with the same ownership and mode.

Independent postflight returned `PASS_PREPARATION_EVIDENCE`. All 9,129 tracked
inputs, four gitlinks and four assets pass; 9,080 regular files are distinct
tmpfs objects. Clean indices, installed metadata, historical blobs, main/IHK
closures, shared ABI, manifest verification and owner validate-only all pass.
Manifest `b37c4f7c...a6d8`, request `9f1b1653...5fd8`, receipt
`6d076fd8...3a7a` and log `b09c18b3...6599` are retained. Output/evidence roots
are empty, the fresh lease and staging residue are absent, and unrelated running
containers mount no target. Candidate plus backup consumes 9,141,473,280 bytes;
the planned aggregate is 22,026,375,168 under 24 GiB. Archive
`69976447...a5ae` matches all 96 live members.

This accepts preparation evidence only. After this checkpoint is pushed and
fetch-verified, derive and independently review a fresh one-shot heavy-build
release for exact owner command `/usr/bin/python3 -E -s -B
/dev/shm/mckernel-exact-candidate-f5d8d914-1/scripts/native_rust_exact_build_container_owner.py
/home/holden/mckernel-work/scratch/native-exact-build-request-f5d8d914-1.json`.
Use the pinned CPUs 2-5, 12-GiB, 512-task, no-swap/no-network profile and `-j2`;
remeasure capacity and leases first. The candidate contains the reviewed queue
executable-root repair for the consumed 704f phase-0 failure. No build, guest or
application has run yet; formal counters remain 6/130 and 350/10000,
applications remain 0/273, and the OS is incomplete.

Shutdown checkpoint 168, 2026-09-29: the prepared `f5d8d914-1` candidate did
not enter a heavy build. Heavy release v1 was independently BLOCKed before
execution by an incorrect GOAL policy hash and an overstated historical output
claim. Additive v2 corrected those defects, passed candidate binding and census,
then was independently BLOCKed because its queue-only executable-root repair did
not cover later Python `tempfile.TemporaryDirectory()` fixtures while `/tmp` is
noexec. Neither release consumed the owner, build or lease; both are permanently
non-runnable. The exact owner command remains historical evidence only.

The escalated central correction at fetched commit
`57133e95944b3a808c3f38b912d4446ffc298eb1` binds `RUNNER_TEMP`, `TMPDIR`,
`TMP` and `TEMP` to the validated evidence build root for every phase-entry
shell. Exact driver `afc035bb...c629` and tests `1371bc9f...11ba` independently
PASS source; all 19 tests pass on Python 3.8/current. Path validation is not
descriptor-pinned, requires trusted stable ancestors, and does not itself prove
mount executability. Nested workflow `env -i` commands still intentionally
clear these variables. This grants no build or runtime acceptance.

Fresh light container `mckernel-offline-temp-57133e95-1`, identity
`1e92f6fb...828c4`, ran under the reviewed unprivileged profile with `/tmp`
noexec and `/evidence` executable. It exited 1 without OOM or restart after the
mount/compiler probes, all 19 offline-driver tests, the exact queue fixture and
the OS registry, device registry, ioctl and SMP-resource checks passed. It then
preserved two terminal failures: the standalone SMP loader fixture omitted the
new production `super::user_string` dependency, and the Rust-1.92 allocator
test asked rustc to create `/src/rmeta*` under the read-only source bind. Archive
`stability-native-offline-exec-temp-root-light-failure-57133e95-20260929-1.tar.gz`
SHA `f6c0c49a...d0b1` retains eight raw members; record
`stability-native-offline-exec-temp-root-light-failure-57133e95-20260929-1.json`
separates passed diagnostics from the failure and makes no acceptance claim.

Bounded candidate corrections are preserved at fixture `1296dc6f...81d6`, SMP
test `3be601ce...87c6` and compatibility test `755bbc1d...dc0`. The loader
fixture compiles and runs 40 tests with Rust 1.85.1 and its three Python tests
pass; the compatibility module passes 12 host tests with its exact Rust-1.92
test skipped. The host default Rust 1.60 failures only demonstrate that the
old compiler cannot parse current production Rust; they are not authoritative
regressions. Shutdown arrived before independent correction review or a fresh
pinned-Rust-1.92 container retry, so these edits remain candidate fixes.

All child lanes are terminal and no build or guest is active. The exited light
container is intentionally retained. Candidate 26/47678 and metadata backup
26/58429 remain intact, but are now obsolete for a corrected build and must be
retired only through reviewed retention/retirement machinery. Launcher wrapper
3399308/83682487, worker 3399313/83682494 and app-server 3399317/83682500 remain
live. At shutdown, host, scratch and tmpfs had about 22, 21 and 7 GiB available;
memory available was about 17 GiB. No current-candidate build or real guest app
ran; formal counters remain 6/130 and 350/10000, applications remain 0/273, and
the OS is incomplete.

The next invocation must first verify this fetched checkpoint and reconcile the
three launcher identities and retained container. Then independently review the
three candidate corrections and run a freshly named light container under the
same isolation profile: execute the two failed tests first, then the remaining
page-allocator, page-owner and mapping checks, preserving all results. Only a
passing chain may unlock safe retirement of `f5d8d914-1`, preparation of a
wholly fresh candidate from the corrected fetched commit, and a new heavy-build
request/release. Never patch the existing candidate in place or execute the
blocked v1/v2 releases. The launcher pause is temporary and the goal must not be
marked complete or resumed during shutdown.

Continuation checkpoint 169, 2026-09-29: independent source review PASSed all
three bounded fixture/test corrections at fetched commit `66ced088...fe17`.
Fresh container `mckernel-offline-temp-66ced088-2`, identity
`3c169e5c...5366`, used the same reviewed unprivileged profile: CPUs 2-3,
2 GiB/no swap, 128 tasks, no network, read-only root/source, all capabilities
dropped, no-new-privileges, uid/gid 1000, `/tmp` noexec and executable ext4
`/evidence`. Exact image `0f8ad280...775d` remains retained. It exited 0 after
30.56 seconds with no OOM or restart.

Pinned Rust 1.92 ran four focused tests without skips, including the production
`user_string` loader dependency and exact warning-clean allocator symbol probe.
All 19 offline-driver tests and the queue fixture passed. The consolidated
Python chain ran 85 tests: 84 passed and only the unchanged external Rocky source
audit skipped. Compiled registry/ioctl/resource fixtures passed, followed by the
page allocator, page owner and mapping checks. Final marker
`EXACT_PHASE0_TEMP_ROOT_PASS` is present and the evidence build root is empty.
Raw stdout `8a046650...7b10`, stderr `641ff4a5...755`, inspect
`8d4bb3bc...6baa` and exit receipt `9a271f2a...86aa` are retained in 13-member
archive `stability-native-offline-exec-temp-root-light-success-66ced088-20260929-2.tar.gz`
SHA `1c3ec354...81f6`.

The first independent postflight correctly BLOCKed three copied member hashes
in checkpoint 168's failure JSON. The original record and archive remain exact
and unchanged. Additive correction
`stability-native-offline-exec-temp-root-light-failure-record-correction-57133e95-20260929-1.json`
SHA `80b31e0a...dcfa` binds the original wrong values to direct archive-member
hashes. Bounded rereview returned `PASS_LIGHT_VALIDATION`; no oracle was
weakened. This accepts isolated phase-0 infrastructure only, not a full build,
kernel runtime, application, production gate or language gate.

Candidate `f5d8d914-1` at 26/47678 and metadata backup 26/58429 are now proven
obsolete for the corrected build but remain intact. Their combined ~9.14-GiB
tmpfs allocation must be retired only through fresh, reviewed retention and
one-shot retirement packets; direct deletion and reuse of any blocked v1/v2 or
historical 675/704 packet are forbidden. Next prepare and independently review
a fresh two-root retention capsule, run it once, review reconstructibility, then
separately release retirement. Only verified retirement unlocks a wholly fresh
candidate from the fetched corrected commit and a new heavy-build release.
Formal counters remain 6/130 and 350/10000, real guest applications this window
remain zero, and application acceptance remains 0/273.

Continuation checkpoint 170, 2026-09-29: fresh retention-preparation template
`native-exact-candidate-retention-preparation-9e5ab03d-1.py` SHA
`91bacf83...f60ab` and immutable tests SHA `2be61b93...aa53` now independently
`PASS_SOURCE`. The template binds candidate 26/47678, backup 26/58429, allocated
bytes 9,140,117,504 plus 1,355,776, exact candidate main `f5d8d914...430b`, IHK
`3114d9e7...72a1f`, current support hashes and an entirely fresh `9e5ab03d-1`
inventory/archive/scratch/claim/lease family. `RELEASE_HASH_REQUIRED` still
blocks execution.

Initial review preserved two test defects: the immutable suite would fail after
the release literal changed, and its compile check could write beside the packet.
The bounded correction fixed compilation but still normalized only the
placeholder. Per convergence policy, expert escalation normalized the loaded
current literal and added an already-populated-packet regression. Independent
rereview passes the same 20 tests against both placeholder and populated packet
forms; explicit temporary `cfile` compilation and scoped diff checks pass.

No retention or retirement has run. This checkpoint establishes the immutable
template ancestor only. After push/fetch verification, construct a release JSON
binding this exact prior commit, packet/test/support hashes and exact execute
inputs. The subsequent release commit may change exactly two paths: add that
release JSON and replace only the packet release-hash literal. Then obtain fresh
independent execution review and remeasure identities, allocations, capacity,
processes, leases and Docker mounts before a single ordinary-user run. Formal
counters and application acceptance remain unchanged.

Continuation checkpoint 171, 2026-09-29: fetched release commit
`610b7bb4...d32f` changed exactly the retention packet literal plus one release
JSON. Independent execution review PASSed exact roots, allocations, revisions,
fresh paths, processes, leases, capacity and a sanitized 19-container census.
The two candidate mounts and one repository-ancestor mount are terminal,
PID-zero, read-only and `restart=no`. The exact ordinary-user command ran once,
exited 0 in 51.644925029 seconds and emitted empty outer streams.

Inventory `841dedac...34f89` contains 10,714 entries and is byte-identical to
postflight. Restoration archive `624da324...a6a4` passes the production verifier
for all 924 exact ordered members: 918 capsule-required entries plus their
ancestor closure. Independent review rederived 9,796 reconstructible entries
from exact main/IHK Git trees and confirmed retained blob availability. Receipt
`e054ef28...5a84` records PASS. Planner 4028910/92235567, archiver
4028943/92237651, postflight planner 4028967/92238545 and packet
4028897/92235556 are absent with no child process-group survivors. Claims and
leases are absent; roots 26/47678 and 26/58429 remain clean, unchanged and exact.
Raw archive `stability-native-exact-retention-preparation-success-raw-9e5ab03d-20260929-1.tar.gz`
SHA `7bd51f30...83cf` preserves 23 members.

Independent postflight returns `PASS_RETENTION_PREPARATION`. This proves
reconstruction inputs in the declared scope, not an executed restore, original
inode/layout/timestamps/ACL/xattr fidelity, retirement or deletion. After this
checkpoint is pushed and fetch-verified, design a wholly fresh two-root
retirement packet bound to inventory `841dedac...34f89`, restoration archive
`624da324...a6a4`, candidate 26/47678 and backup 26/58429. It requires separate
source and execution review, canonical reconstruction admission and fresh
process/mount/reference checks before one invocation. Builds and real guest
applications remain zero; formal counters and 0/273 application acceptance do
not change.

Shutdown checkpoint 172, 2026-09-29: the launcher requested an immediate
checkpoint while the fresh two-root retirement packet was undergoing its first
bounded source correction. No retirement, deletion, restore, build or guest ran.
The sole active worker stopped and all child lanes are terminal. Launcher wrapper
3399308/83682487, worker 3399313/83682494 and app-server 3399317/83682500 remain
live; no retirement/helper/observer/deleted-inode-audit process is active.

The initial independent source review BLOCKed the retirement draft on wrong
candidate revision/counts, contradictory Docker sets, incomplete mount-namespace
proof, missing special-process classification, tests that could not survive
sealing, and absence of a post-delete inode census. The bounded correction is
preserved but remains unverified and non-runnable. Its attempted cheap suite ran
112 tests with one failure and six errors; its compile invocation was malformed
and is not evidence. Current exact file hashes are packet
`f25b695c...726ed`, packet test `3370660d...dfa2`, helper
`7aa052bc...e18`, helper test `ed7bd0e0...1441`, observer
`34a4e4bc...54a3`, and observer test `66b08586...3707`.

The correction has separated support and candidate revisions, bound the exact
inventory counts and three terminal container identities, and integrated the
sealed deleted-inode audit. It still has a `docker_callback` indentation defect
that raises `NameError: ids`, helper fixtures omit newly required audit sources,
inventory tests retain old schema/counts, and one signal-cleanup assertion fails.
These are source defects, not an execution result; `RELEASE_HASH_REQUIRED` and
independent source/execution review remain mandatory.

At shutdown, host, scratch and tmpfs have 23,012,728,832, 21,515,587,584 and
7,445,069,824 bytes available; `MemAvailable` is 18,075,304 KiB. Candidate
26/47678 and backup 26/58429 remain protected by the accepted retention inputs.
Next invocation must verify this fetched checkpoint and launcher identities,
then escalate this same failure family to an expert correction per convergence
policy rather than applying another ordinary bounded tweak. Rereview all six
original findings, deleted-inode integration and immutable release-transition
tests before any template commit. Only a source PASS may unlock the separate
template/release/push/fetch/execution-review sequence. Formal counters remain
6/130 and 350/10000, current-candidate builds and real guest applications remain
zero, application acceptance remains 0/273, and the OS is incomplete. The
launcher pause is temporary; do not mark the goal complete or resume it during
shutdown.

Continuation checkpoint 173, 2026-09-29: the new launcher generation is wrapper
4041681/92434707, worker 4041684/92434713 and app-server 4041686/92434719; the
three checkpoint-172 identities are absent. Policy hashes remain GOAL
`76c4f5d1...bcc3`, START `1698d342...16c`, and CONVERGENCE
`f6938bd2...e86a`. The planning index still validates exactly 130 production
gates, seven language gates, 273 logical cases and 97 packets.

The retirement failure family consumed its required expert escalation. Fresh
reconciliation corrected the stale historical post-delete target: retention
inventory `841dedac...34f89` contains 10,714 non-root entries, split 10,628 and
86, while the protected trees contain 10,716 distinct identities including the
two roots, split 10,629 and 87. Candidate 26/47678 remains allocated
9,140,117,504 bytes and backup 26/58429 remains allocated 1,355,776 bytes. No
retirement process or active build lease exists.

Expert repair across the exact six WIP files now separates support and candidate
revisions, validates 7,833 main and 1,296 IHK reconstructible objects plus 918
capsule entries, uses one exact three-container contract, imports the sealed
corrected audit for typed special-process and complete namespace coverage, makes
release-transition tests immutable, and gates terminal PASS on a durable
three-round post-delete census of the exact 10,716 identities. It explicitly
rejects historical 10,611. Python 3.9 passes 183 tests; Python 3.8 passes the
127 retirement and 56 audit tests. Explicit temporary compilation and scoped
diff checks pass.

Independent Astra review returns `PASS_SOURCE` on packet `efef4b6e...4ee7`,
packet test `3399b957...7959`, helper `f589ba43...378a`, helper test
`5774766d...515e`, observer `e8800a59...5374d`, and observer test
`b4eaac82...1321`. It independently passes all 183 tests under a two-CPU/4-GiB
cap. The observer's `field_counts['ns/mnt']` diagnostic remains zero even for
successful namespace scans; authorization uses explicit namespace coverage, so
that counter must not be interpreted quantitatively. Record
`stability-native-exact-retirement-source-success-b4208879-20260929-1.json`
preserves the history and decision.

This is source/template eligibility only. `RELEASE_HASH_REQUIRED` still prevents
execution. After this checkpoint is pushed and fetch-verified, construct a
mechanical two-path finalization: add one exact release JSON and replace only the
packet release-hash literal. Obtain independent execution review and repeat
current process/root/lease/capacity/Docker reconciliation immediately before one
invocation. No build or real guest application ran; counters remain 6/130,
350/10000 and 0/273 applications, and the OS remains incomplete.

Shutdown checkpoint 174, 2026-09-29: the launcher stop arrived after the
immutable source template `5b8f64827bacf2f5f49c94d33c4b41e4bfc12f65` was
pushed and fetch-verified and while the bounded mechanical release generation
was active. No new dispatch followed the stop. Both children are terminal, and
no retirement/helper/observer/deleted-audit process, build or guest is active.

Generation produced an exact but deliberately unreviewed draft release JSON,
`stability-native-exact-candidate-retirement-1c00d2b8-1.release.json`, SHA
`f7b48994f7678b1a71fd399940980818ce5e9a2c40a7f7e7d3c429c2d1006efa`,
2,415,286 bytes. It binds the 10,714 inventory members, protected roots
26/47678 and 26/58429, the exact three terminal Docker records, boot
`c733d83b-a5ae-4f91-9ce6-9f8ccf119afd`, and launcher wrapper
4041681/92434707, worker 4041684/92434713 and app-server 4041686/92434719.
All three identities remain live at checkpoint time. The candidate, backup,
quarantines, evidence directory and build lease remain respectively intact or
absent as required.

The packet release literal was restored to `RELEASE_HASH_REQUIRED` before this
shutdown checkpoint, so the draft cannot pass admission. Its populated-form
cheap regression ran 127 tests in 5.821 seconds before restoration and passed;
JSON parsing, exact SHA and scoped diff checks passed. This is not independent
execution review and not a release. Since this shutdown documentation changes
the fetched ancestry, the next invocation must treat the draft only as generation
input: verify this fetched checkpoint and live identities, update the release's
template/finalization commit and any changed live facts, recompute its hash, and
then commit exactly the release JSON plus packet literal. Only after push/fetch
may an independent Astra execution reviewer decide whether one `sudo -A`
invocation is released.

At checkpoint, host, scratch and tmpfs have 105,518,501,888, 21,515,587,584 and
7,445,069,824 bytes available; `MemAvailable` is 21,058,896 KiB. No real guest
application ran, formal counters remain 6/130 and 350/10000, application
acceptance remains 0/273, and the OS is incomplete. The launcher pause is
temporary; do not mark the goal complete or resume it during shutdown.
Continuation checkpoint 175, 2026-09-29: exact candidate retirement is accepted.
The one released `sudo -A` invocation from fetched commit
`5386f60cf88ddacf2170aee0ba8433f76c591d37` exited 0 in about 79.5 seconds.
Independent postflight returns `PASS_RETIREMENT`: all 21,440 journal rows,
10,714 member deletion pairs, two root deletion pairs, two clean observer
rounds over 820/821 task identities and 19 mount namespaces, and three clean
post-delete rounds over all 10,716 target identities reconcile. Candidate
`f5d8d914-1`, its backup and both quarantine roots are absent with zero surviving
references. The immutable root-owned tombstone SHA is `30477fdc...29e5` and
permanently forbids attempt-name reuse.

Raw archive `stability-native-exact-candidate-retirement-success-raw-1c00d2b8-20260929-1.tar.gz`
SHA `75946dc0...3829` durably retains the 25 evidence files and tombstone. Additive
decision record `stability-native-exact-candidate-retirement-success-5386f60c-20260929-1.json`
preserves hashes, exact command, results, limitations and review. Correcting an
earlier unit label, the coordinator-only before/after tmpfs measurements imply
9,133,658,112 bytes = 8.506 GiB reclaimed; only the after value is independently
rechecked. This does not affect the inode/reference proof.

Fresh differently named candidate preparation is now unlocked under its own
source and execution admission. Bind the current fetched main commit and pinned
IHK `3114...` with only the reviewed `clear_host_pte` overlay; never consume the
dirty nested IHK checkout directly. Reconcile current preparation support hashes,
use a fresh nonce/path, independently review it, then prepare and build the
smallest candidate in the pinned 4-CPU/12-GiB/no-network profile with `-j<=4`.
After a successful artifact build, run a fresh diagnostic startup guest, then
memory, files, threads/futexes and signals in fresh guests, and a separate
shutdown lifecycle check. Preserve exact stdout/stderr, exit status, kernel log
and teardown. Diagnostics remain separate from formal application acceptance.
Formal counters remain 6/130 and 350/10000; current-candidate builds and real
guest applications remain zero and the OS remains incomplete.
Continuation checkpoint 176, 2026-09-29: fresh exact candidate preparation
`76ae20b5-1` is accepted. The one released ordinary-user invocation exited 0
in 69.587 seconds, with the original outer `LOG_FINAL_FSYNC=PASS` retained in
launcher protocol event `exec-9b44e6b9-bbb4-40c4-a723-e36c12ddcbe0`.
Independent postflight returns `PASS_PREPARATION`. Candidate 26/58679 binds
main `76ae20b5...f671`, pinned IHK `3114d9e7...72a1f`, and exactly one mode-0644
whitebox overlay with diff `cbaaec7b...49e7` and result `7abb77fd...bf77`.
Metadata receipt, manifest and build request pass; output/evidence roots are
empty, the attempt lease is absent, and no owner/container/guest survives.

The support repair also has independent `PASS_SOURCE`. Its initial review
correctly BLOCKed mode drift in the overlay exception; the bounded correction
restored exact permissions, no-follow open and opened-file identity checks.
Forty-eight combined focused tests pass, including production manifest/offline
round-trip and 0600/0755 rejection. An existing reviewed Rust 1.92 light profile
also passes all seven IKC queue fixture tests. Raw preparation archive
`stability-native-exact-candidate-preparation-success-raw-76ae20b5-20260929-1.tar.gz`
SHA `d6262063...e703` retains 92 log/manifest/request/metadata members; additive
decision record `stability-native-exact-candidate-preparation-success-76ae20b5-20260929-1.json`
preserves exact identities and review history.

Heavy execution is not released. Candidate plus the pinned 12-GiB container is
22,055,116,800 bytes = 20.540428 GiB, exceeding this launcher's 16.2158-GiB
aggregate cap. The owner's historical 24-GiB admission is obsolete for this
invocation. Independent resource review selects exact copy to a fresh scratch
candidate, complete equality/provenance verification, and separately reviewed
retirement of both tmpfs roots. Only after retirement may the unchanged
4-CPU/12-GiB/no-swap/no-network profile build with `-j<=4`. A smaller container
is not selected because no successful current exact-build peak supports it.
Formal counters remain 6/130 and 350/10000; current-candidate builds and real
guest applications remain zero, application acceptance remains 0/273, and the
OS remains incomplete.

Continuation checkpoint 177, 2026-09-29: disk-backed candidate preparation is
accepted after preserving two failed validation attempts. The original copy
was byte-exact at copy time, but post-copy Git commands refreshed two index
files. The reviewed correction durably sealed their original bytes and restored
them, then correctly failed when its unchanged equality oracle discovered a
later one-bit divergence in one tmpfs gzip member. The divergent tmpfs byte is
`0xbb` at zero-based offset 37,352,801; the authenticated disk/pinned-Git byte
is `0x3b`. Tmpfs SHA `192f8fe1...b1c2` fails gzip CRC; disk/pinned Git SHA
`dbe24f5b...b5100` passes. No hardware cause is claimed.

Fresh fetched validation commit `080e31a708618d67510dd819d385c306673ec7c0`
then ran once and exited 0 in 33.301 seconds with outer
`LOG_FINAL_FSYNC=PASS`. Independent postflight returns `PASS_VALIDATION`:
candidate `1831:4194306`, backup `1831:4204970`, all 10,751 entries and 9,736
regular-file hashes match the authenticated copy-time inventory; exact PRE and
POST both hash `842f4522...26ae`. No-lock BuildOwner validation passes, build
output/evidence remain empty, the lease is absent and no child survives.
The 40,004,941-byte corrupt source is sealed on scratch with SHA
`192f8fe1...b1c2`; its one-byte delta from the pinned Git member makes it exactly
reconstructible. Raw archive `stability-native-exact-candidate-disk-validation-success-raw-76ae20b5-20260929-1.tar.gz`
SHA `ea1cdf88...ea35` retains 27 smaller records. The additive failure and
success JSON records preserve the full identities, hashes, outer events and
limitations.

The tmpfs candidate and backup remain present and are forbidden as build/copy
authority. Next create and independently review a fresh retirement packet for
both identities 26/58679 and 26/69465, preserving the corrupt seal and using the
current retirement helper. After `PASS_RETIREMENT`, execute the disk request
through the independently source-approved launcher-budget wrapper
`native_rust_exact_disk_build_wrapper.py` SHA `587bb769...d487`, under the
unchanged 4-CPU/12-GiB/no-swap/no-network profile and `-j<=4`. A successful
artifact build then unlocks fresh diagnostic startup, memory, files,
threads/futexes, signals and shutdown runs. Diagnostics remain non-accepting;
formal counters stay 6/130, 350/10000 and 0/273 applications.

Continuation checkpoint 178, 2026-09-29: the disk build admission wrapper is
source-approved and fetched at commit `21fb56e340995def52a37d9cefda266bd048c5f4`.
Independent adversarial review first reproduced pre-authentication candidate
code execution and malformed zero-memory accounting, then found one
owner-versus-offline-driver binding regression in the bounded correction.  The
expert-directed final correction passes all 12 focused tests.  Wrapper SHA is
`ca838820d1e21d522023e09890fd963a4d931e03ab99d39bb70c2a9c0b5b4bbd`;
test SHA is `7e091b0547797fa861f1c77373a6ed3d802a55d3479fd8e3292cd935d66b2513`.
It now executes only descriptor-authenticated source bytes, rejects link and
path escapes, validates the complete disk-only resource formula, and binds the
actual offline driver.  The old disk-validation request lacks the two new
owner/provenance hash fields and is intentionally not executable; create a
fresh externally bound request after tmpfs retirement.

Two draft retention-preparation packets were rejected without execution.  The
first lacked shared exclusion and stable postflight binding; its one bounded
correction retained a contradictory release preflight, path-reopen races and
detached-child cleanup gaps.  Both failures remain in the working tree as
unreleased templates.  Expert escalation selected the accepted `9e5ab03d`
Python supervisor as the new base, with additional common exclusion, sealed
helper-byte execution, complete tmpfs and disk pre/post inventories and a
success receipt published last.  That fresh packet is now the only retirement
prerequisite lane.  The tmpfs roots remain present and forbidden as build
authority; the accepted disk roots and corrupt seal remain intact.  Live
launcher identities are wrapper/launcher `4055285`/`4055286` (launcher
starttime `92631630`), worker `4055294/92631636`, and server
`4055298/92631642`; no build or guest was active at reconciliation.

The diagnostic protocol remains non-accepting but ready for new artifacts: 156
focused evaluator/backend/runner/stager/overlay tests pass.  Historical guest
manifests bind the old image/modules and will not be reused.  A current-source
`mckernel.img` still needs a separately reviewed four-CPU image build; the
current exact host build produces only `bzImage` and three host modules.
Next execute the expert-reviewed retention preparation, bind its real
inventory/capsule into the retirement packet, retire the two tmpfs roots, then
run the fresh disk build and current image build serially under the one heavy
lease before startup, memory, files, threads/futexes, signals and shutdown
diagnostics.  Formal counters remain 6/130, 350/10000 and 0/273 applications.

Continuation checkpoint 179, 2026-09-29: exact tmpfs retention preparation is
accepted and retained at fetched commit
`3bbf61aa122671901738e0504ebf9882518c269f`.  The first released packet stopped
before mutation on its overbroad Git worktree-config check.  Its corrected,
newly released successor ran once as UID 1000 on CPU 6 and independently passes
postflight.  Inventory SHA `585fc0f5...504fd` covers 10,749 entries, including
922 capsule-required entries.  Archive SHA `fd26f227...e3d7` is 52,039,680
bytes with exactly 937 verified members.  Receipt SHA `cfd7b5d5...565b`
records release `0dad43e9...c167`, identical complete tmpfs pre/post inventory
SHA `375e025c...f30d`, accepted disk inventory `842f4522...d526ae`, zero
helper errors/signals and released exclusions.

Fresh independent scans reproduce both complete inventories.  Tmpfs identities
`26:58679` and `26:69465`, disk identities `1831:4194306` and `1831:4204970`,
and corruption seal `1831:4849667` remain exact.  The retained corrupt member
is capsule-required with SHA `192f8fe1...b1c2`.  Wrapper/owner PIDs
`4142687/4142688` and every recorded descendant/session/group are absent; all
five operational exclusions and the retirement tombstone are absent.  The raw
18-member execution archive SHA is `2374d9ea...ebcf`; additive success record
SHA is `3b42a154...0ac4`.

Retention preparation does not delete anything and earns no application or OS
credit.  The retirement template now binds these real artifacts, receipt,
counts and common-exclusion contract and is under independent source review.
Only after its separately fetched root release passes may the two tmpfs roots
be retired.  The disk build wrapper and image driver have additional source
corrections in progress; no heavy build or guest has run.  Formal counters
remain 6/130, 350/10000 and 0/273 applications.

Continuation checkpoint 180, 2026-09-30: the exact tmpfs retirement performed
the intended deletion but failed closed in its post-delete observer.  The sole
released root invocation from fetched commit
`99fd0558dfce14c8f53c3fb2c0253129ccb25c60` removed both authenticated roots;
the originals and both quarantine paths are absent, no retirement process
survives, and tmpfs free space increased to 16,567,324,672 bytes.  The complete
21,510-row journal ends with `terminal-prepared`, a PASS helper result and all
four source/quarantine paths absent.  This is not accepted retirement because
the packet terminal status is FAIL: `closure-1 callback failed`.

The original root-owned 25-entry failure directory remains unchanged at
`/dev/shm/.mckernel-retirement-evidence-76ae20b5-1`, identity `26:69508`.
`packet.failure` SHA is
`e1e629b6f43a9661fcfe255b7b0607be365acb0812b028de6f99075837c36ec1`.
An independently verified no-atime archive at
`/home/holden/mckernel-work/scratch/native-exact-candidate-retirement-76ae20b5-1-failed-evidence-20260930-1.tar`
has SHA `9ecab3772c9b8a6e3a4b0257bce3136734e0bac0becf4b79157b35bb78ce9abe`,
size 10,874,880, and an exact 25-entry comparable inventory SHA
`74758565a5c6e4fc18381e23eeba61f7d279a986f4a9014465e30cbc4c0c4b77`.
All five root-owned immutable exclusions remain intact; never clear or reuse
them.

The preserved first post-delete scan contains no target references, denials,
incomplete observations or identity replacements.  Its 819 entry-churn rows
all identify the observer's incorrect assumption that every task has its own
`/proc/PID/task/TID/map_files`; the actual host exposes process-level
`/proc/PID/map_files`.  The bounded correction now scans that fallback while
binding and revalidating both leader and TID identities, never treating absence
as an empty mapping set.  Twenty-seven tests and the self-test pass, independent
source review passes, and fetched commit
`6e5de06ac8dddf4a7e20bf5ccc8fb8ab84335450` preserves the correction and the
original failed evidence.

Next, finish and independently review a postflight-only root packet that binds
the old baseline/FAIL/archive, the corrected observer, protected disk roots and
all immutable tombstones.  It must perform three complete fresh scans into a
new evidence namespace without retrying deletion or altering old evidence.
Only a passing postflight may unlock a newly named build exclusion/request;
the current wrapper's old exclusion path is permanently occupied.  Then build
the disk-backed host candidate in the single 4-CPU/12-GiB lease, build the
current McKernel image serially, and run startup, memory, files,
threads/futexes, signals and shutdown diagnostics.  Formal counters remain
6/130, 350/10000 and 0/273 applications; no current-candidate build or real
diagnostic app has run, and the OS remains incomplete.

Continuation checkpoint 181, 2026-09-30: exact candidate retirement closure
now independently passes.  The first postflight attempt preserved a completely
clean 823-identity round, then failed because an unchanged-global-census rule
treated one exact process exit as unsafe.  Its four-entry archive SHA is
`15309d25...05fd1`.  The corrected V2 oracle reconciles exact exited
identities, requires every final live identity to have a successful scan, and
rejects PID/TID reuse across or during scans.  Thirty-six focused tests and
independent source review pass.

The released observation-only retry from fetched commit
`a9889b0e3ef45bf1782f3165e33d219904973ebd` passes all three rounds over
10,751 retained target inode identities.  Census sizes are 823/823,
823/823/823 and 823/822; the latter rounds each reconcile one exact exit.
Every reference, denial, incomplete scan, replacement, entry-churn,
unscanned-final and nonconvergence count is zero.  Terminal status SHA is
`22a73d2...eb5c`; round SHAs are `17a0052f...8177`,
`c434f972...6d72d` and `14b01c87...7e5f`.  Independent postflight and archive
review pass.  The five immutable retirement tombstones and both original
failed evidence sets remain unchanged; this success does not remove them.

The fresh disk build path is now source-reviewed.  Wrapper SHA
`edc6e02...a5fc2` accepts only the new exclusion ending `76ae20b5-2.json` and
rejects the old tombstone.  Request SHA `23b0d911...caad` binds the exact disk
candidate/backup, 9,161 source bindings, four assets, owner/provenance bytes,
overlay, 4-CPU/12-GiB/no-swap/no-network/512-task profile and exact 16.2158-GiB
aggregate.  Fresh output/evidence directories are empty identities
`1831:5242881` and `1831:5373953`; independent execution review passes.
Next execute that one serialized host build.  Preserve its terminal container
and fresh common exclusion for separately reviewed cleanup, then build the
current McKernel image serially and run startup, memory, files,
threads/futexes, signals and shutdown diagnostics.  Formal counters remain
6/130, 350/10000 and 0/273 applications; no current-candidate build or real
diagnostic app has yet run, and the OS remains incomplete.

Continuation checkpoint 182, 2026-09-30: the first real disk-backed exact host
build attempt reached the pinned, offline four-CPU container but failed before
compilation in the source-only contract phase.  The exact command and request
are retained in `native-exact-build-disk-build-2-failure-20260930.json`.
Container `cc79cd696...cbd7` / full name
`mckernel-exact-7d4e3858320e4797ab6d22ed89195e9c` exited 1 with PID 0 and remains
owned by nonce `b3fcbace...19a1` for separately reviewed cleanup.  No kernel or
module artifact was produced.  Owner receipt SHA is `302961af...bf8c6`, driver
receipt SHA is `de23fa1a...bd17c`, driver-log SHA is `694ea916...08833`, and
the preserved 204,800-byte failure archive SHA is `845bff31...ce3a7`.

The observed deterministic error is `exact build workflow prebuild scope
differs`.  The current workflow is SHA `e9cfb14d...91831`, size 95,063 and Git
blob `4f8da595...2446`; its retained contract still names the older SHA
`16fb3010...81e9`.  The two changed step bodies have independently reproduced
source hashes, but the complete transitive workflow identities and checker
self-digest must pass their existing full contract before a new build.  The
first cleanup-packet drafts were rejected for Docker, release, and replacement
race defects and were not executed.  Preserve the terminal container, common
exclusion identity `1831:31517`, request, evidence and archive until a corrected
packet receives independent execution release.

Next finish and independently review the full source-bound identity correction,
release and execute exact failed-build cleanup, then create a fresh scratch
candidate from the fetched repaired commit.  Run one serialized host build;
only after it produces exact `bzImage` and module artifacts may the current
McKernel image build and diagnostic startup, memory, files, threads/futexes,
signals and shutdown apps proceed.  Formal counters remain 6/130, 350/10000
and 0/273; this prebuild failure is diagnostic evidence, not acceptance.

Continuation checkpoint 183, 2026-09-30: the complete workflow-identity repair
and transitive contract bindings independently pass and are fetched from
commit `97fb67a7932af8928e8f1340fdae6403795f256b`.  The native full contract,
all eight source-derived workflow step hashes and mutation controls, normalized
self-digest, and focused FP-0006/RS-006 consumers pass.  This fixes the exact
prebuild failure family without weakening its oracle; it does not prove a
build.  The next wrapper namespace is independently accepted and fetched at
`5aff8eef75f1d1788eb5c9d37135b789609dd57e`.  It permits only the fresh
`native-exact-candidate-operational-exclusion-97fb67a7-3.json` path and rejects
the retained `-2` failure exclusion and historical names.

The failed container and `-2` exclusion remain preserved.  Repeated cleanup
packet drafts were rejected for fetched-release, Docker-absence, pathname-race
and durable-publication defects and were never executed.  The strategy has
changed: the stopped container consumes no heavy lease, so the next attempt
uses the reviewed fresh `-3` namespace rather than risking deletion of original
failure evidence.

A full 419-line scratch preparation packet is now independently source-accepted.
Packet SHA is `c27f1c65...d4359e`, placement observer SHA is
`e4cc1cbb...ca032`, and tests SHA is `8df54fe3...93dc8`.  All 80 bounded tests
pass.  It binds source `5aff8eef...d57e`, IHK `3114d9e7...972a1f`, all four
exact Git links, clean metadata conversion before the reviewed overlay,
candidate-local manifests and owner validation, full request/profile inputs,
disk-backed zero-memory accounting, pre/post resource floors, and durable
partial/terminal evidence.  Actual preparation has not run yet.

Next commit/fetch this exact preparation template, execute it once with its
fetched release commit after live resource/process reconciliation, and
independently verify the resulting candidate/request.  Then run one serialized
four-CPU exact host build.  Image-owner work remains rejected source WIP and
will not run until its remaining authentication, tmpfs, evidence-confinement
and under-exclusion measurement defects are repaired.  Formal counters remain
6/130, 350/10000 and 0/273; no current-candidate artifact or diagnostic app has
yet passed.

Continuation checkpoint 184, 2026-09-30: the reviewed scratch preparation ran
once from fetched commit `9f4072a3d57531d015291a6590215476eeafef6f` and
passes both its own validation and independent postflight audit.  Candidate
`/home/holden/mckernel-work/scratch/mckernel-exact-candidate-5aff8eef-scratch-1`
is disk-backed with identity `1831:6553601`, source commit
`5aff8eef75f1d1788eb5c9d37135b789609dd57e`, IHK
`3114d9e7101ad52030eb3effa849a5c108972a1f`, all four exact Git links and
reviewed overlay SHA `cbaaec7b...f49e7`.  Its validated allocation is
9,236,361,216 bytes with zero memory-backed bytes.  Preparation log SHA is
`5b9ff681...1d639`, terminal SHA is `da988a39...b31c9`, metadata receipt SHA
is `ae62b53d...4dec7`, input manifest SHA is `29144b4d...a9998`, and request
SHA is `be455b54...9fe6e`.  Output and evidence roots were empty before the
build; the fresh lease and `-3` exclusion were absent.  This preparation earns
no build, runtime, application or acceptance credit.

The independently released exact host command then ran once in the pinned
offline four-CPU/12-GiB/no-swap/512-task container and failed before
compilation after 669 source tests with four failures and one error.  Terminal
container `b5a32f491e35d06aec1e0dca3f2ad29f4d4a96e46d4ce60c9e59478adce08f51`
(`mckernel-exact-5eb6988440f3492299214641b485eeb6`) exited 1 with PID 0 and
remains retained under owner nonce `7550ac9037a04edda56859767dc73fd6`.
The immutable `-3` exclusion is identity `1831:31523`, SHA
`20d1dfab...ad8db`; driver log SHA is `4a015d00...851d`, owner receipt SHA is
`9d1c05c7...f66b`, and driver receipt SHA is `ae207b88...7f08`.  No artifact
was produced.  The 1,576,960-byte, 47-member failure archive SHA is
`daf0bfb4...8eff`; independent archive review confirms it retains every
failure and the exact terminal identity.
The additive failure record is
`docs/verification/evidence/native-exact-build-5aff8eef-scratch-1-failure-20260930.json`,
SHA `b86732e5...c488`.

Continuation checkpoint 185, 2026-09-30: the bounded correction fixes all five
observed source-contract defects without weakening their oracles.  The
build-ID fixture now supplies the exact current compatibility query, v3 boot,
application callback and v4 create signatures; its focused test compiles and
runs all eight Rust checks, and independent source review passes.  The Kbuild
closure now binds the real stager set and all actual IHK, SMP and mcctrl crate
edges, including restricted `smp_procfs.rs`, both assembly inputs in retained
compiler order, `X86_5LEVEL`, and the three vDSO configuration inputs.  All 29
focused tests pass.  Independent parsing accepts the retained raw records with
13, 44 and 9 project dependencies respectively and rejects the previously
incorrect assembly order.  These are source-contract results only.

The direct and transitive semantic-authority, contract and normalized
self-digest rebinding now independently passes 159 affected tests: 90 core,
four native-runtime, 22 FP-0006 integration, 40 isolated acceptance-closure
and three targeted RS-006 tests.  No stale active binding to the reviewed
changed files remains.  The fresh wrapper independently passes 18 tests and
permits only
`native-exact-candidate-operational-exclusion-closurefix-4.json`, rejecting
the retired, `-2` and `-3` paths before owner invocation.  Seven unrelated
full RS-006 consumer mismatches are confirmed pre-existing and remain separate;
no RS-006 or acceptance credit is claimed.

Next commit/push/fetch the corrected source and additive failure record, then
prepare a fresh `scratch-2` candidate with the new `-4` exclusion.  Only one
separately reviewed exact host build may run.  Preserve both stopped
failure containers, all old exclusions and both failure archives.  A successful
host artifact is still required before repairing/releasing the image owner and
running startup, memory, files, threads/futexes, signals and shutdown diagnostic
applications.  Formal counters remain 6/130, 350/10000 and 0/273; diagnostic
results remain separate from formal acceptance.

Continuation checkpoint 186, 2026-09-30: the complete source-contract repair,
transitive bindings, fresh wrapper namespace, additive second-build failure
record and tracker are pushed and fetched at
`6323598141241dc7f734f42bac78c939bf5ae292`.  HEAD and origin match.  This is
the frozen source candidate for the next build; it does not claim an artifact
or runtime result.

The fresh `scratch-2` preparation packet now independently passes source
review.  Packet SHA is `5cf9ef17...53dbd` and test SHA is
`84633af8...0b0d`; both current and prior preparation suites pass, 68 tests
total, and both packets pass shell syntax checks.  It binds candidate
`63235981...e292`, the exact current helper and wrapper bytes, pinned IHK and
overlay/assets, eleven absent fresh `63235981-scratch-2` targets, and only
`native-exact-candidate-operational-exclusion-closurefix-4.json`.  Candidate
commit and later fetched packet release remain separate to avoid a binding
fixed point.  This is preparation source approval only.

Next push/fetch the packet release, reconcile live processes, stopped
containers, leases and resource floors, then execute this one preparation as
the unprivileged launcher user.  Independently audit the generated candidate,
request and empty output/evidence roots before seeking a new single-build
execution decision.  Preserve both prior terminal containers, all old
exclusions and failure archives.  Formal counters remain 6/130, 350/10000 and
0/273 applications.

Continuation checkpoint 187, 2026-09-30: the exact reviewed `scratch-2`
preparation ran once from fetched packet release
`42cd5b069fd201d1904c93743f71072edcc52514` and independently passes
postflight.  Terminal SHA is `94eb7673...6201`, log SHA is
`7e3102a7...1bc9`, PID/starttime `98932/94725417` and every descendant are
absent, and the log ends `PASS_PREPARATION_VALIDATE_ONLY` with no live child.
Candidate `63235981...e292` is identity `1831:6160385`; its IHK commit,
overlay and all four gitlinks match.  Backup identity is `1831:6684673`.
Manifest SHA is `5b158428...752f` and request SHA is
`6fefac25...e58e`.

The output and evidence roots are empty mode-0700 identities
`1831:6815745` and `1831:6291459`.  The new build lease and `closurefix-4`
exclusion remain absent.  Independent owner validation passes with
9,236,455,424 total allocated bytes, zero memory-backed/tmpfs allocation and a
12-GiB aggregate requirement under the 16.2158-GiB launcher ceiling.  Fresh
measurements before build review show 38,061,215,744 host bytes,
44,420,222,976 scratch bytes and 30,823,661,568 available-memory bytes; no
build, owner, guest or mcexec process is active.  An authorized unfiltered
Docker census confirms every McKernel container is stopped and only unrelated
Kasper services run.

Next obtain the independent decision for exactly one four-CPU pinned host build
using this request, checkpoint this preparation result, and execute only that
released command.  Preserve terminal containers and exclusions on every
result.  No compile artifact or diagnostic application exists yet; formal
counters remain unchanged.

Continuation checkpoint 188, 2026-09-30: the independently released
`scratch-2` host build ran once in the pinned four-CPU/12-GiB/no-swap/no-network
profile and failed before compilation after 671 source tests with one failure
and three errors.  All five defects from the prior attempt now pass.  The new
failure family is confined to detached runtime-evidence reconstruction: it
still compared against the old Rust-only compiler-source set after the closure
authority added the real assembly inputs.  The substitution negative then saw
the earlier closure error instead of its intended output-difference error.

Terminal container
`340d3232f39b292f4d5412729c971b31b0ca38b2828c5ac2e647caefeb6cac25`
(`mckernel-exact-dad0bfb903544364bf7df6bb949afafe`) exited 1 with PID 0
and remains retained under owner nonce `04bdb4e5057c44b88990dcae0ab6e423`.
The `closurefix-4` exclusion is identity `1831:31529`, SHA
`80128636...1dbb`; owner receipt SHA is `dc01a4de...7b9e`, driver receipt
SHA is `a252779d...25bb`, and driver log SHA is `06ad8bdb...cedb`.  No build
output exists.  The complete 1,576,960-byte, 48-member failure archive SHA is
`55b18988...05d2c`; independent streamed review verifies every source,
preparation, request, exclusion and terminal identity.  Additive record
`docs/verification/evidence/native-exact-build-63235981-scratch-2-failure-20260930.json`
has SHA `ed6dfd80...d9be`.

The bounded correction now independently passes 80 affected tests.  Detached
reconstruction consumes and returns the exact ordered full compiler-source
authority, including both assembly inputs; its regression asserts exact
membership rather than only `.rs` suffixes.  All four original failures pass,
four additional assembly substitutions are rejected, descriptor-bound replay
and the negative substitution oracle remain intact, and the FP-0006/RS-006
transitive identity fixed point and both normalized self-digests pass.  The
runtime checker SHA is `87198dcb...c063`; acceptance closure contract SHA is
`9e949e81...43aa`.

Next commit/push/fetch this correction and failure record, advance the wrapper
to a fresh `-5` namespace, and prepare a new disk candidate from that frozen
repair commit.  Do not retry the deterministic `scratch-2` request.  No
artifact, boot or diagnostic app has passed, and formal counters remain 6/130,
350/10000 and 0/273 applications.

Continuation checkpoint 189, 2026-09-30: the detached runtime-source closure
repair and exact second-build failure record are pushed and fetched at
`defab4d281a0f00f9647ae5787ee0fbefc14053e`.  The independently reviewed
wrapper successor is fetched at
`740851854b53036d4834dfb86a5fc7fb0f3954e6`; it permits only fresh
`runtimeclosure-5` and rejects every retired path through `closurefix-4` before
owner invocation.  Nineteen focused tests pass.  This fetched commit is the
frozen candidate for the next build.

The `scratch-3` preparation packet independently passes source review.  Packet
SHA is `af09e74e...93a0f`, test SHA is `b9c6fdb7...1a54c`, both current and
prior suites pass 68 tests total, and both packets pass shell syntax.  It binds
candidate `74085185...54e6`, eleven absent fresh paths, exact helpers,
IHK/overlay/assets and only `runtimeclosure-5`; the future fetched packet
release remains separate from the candidate commit.

Next push/fetch this preparation release, reconcile processes, leases,
containers and capacity, then execute the one unprivileged preparation and
independently audit its generated request.  Only after that may a separately
reviewed single host build run.  No current candidate artifact or diagnostic
app has passed; formal counters remain unchanged.

Continuation checkpoint 190, 2026-09-30: the exact reviewed `scratch-3`
preparation ran once from fetched release
`328c757f9f795ab8736bad1dc4e799f57732993c` and independently passes
postflight.  Terminal SHA is `9620f091...9472`, log SHA is
`f7eb4c60...da5b`, and PID/starttime `120655/94864502` plus all descendants
are absent.  Candidate `74085185...54e6` is identity `1831:3932163`; backup
is `1831:5111810`; exact IHK, overlay and four gitlinks match.  Manifest SHA
is `2e54c946...b77f` and request SHA is `c0fe30d7...6156`.

Output identity `1831:5636110` and evidence identity `1831:4456450` are
mode 0700 and empty.  The fresh lease and `runtimeclosure-5` exclusion are
absent.  Owner validation passes with 9,236,512,768 allocated bytes, zero
memory-backed/tmpfs allocation, the retained 2-5 CPU/12-GiB/no-network/512-task
profile and 16.2158-GiB aggregate ceiling.

Next checkpoint this preparation result, obtain an independent decision for
the one exact host-build command, and execute no other heavy work.  Preserve
the three prior stopped failure containers, exclusions and archives.  No
artifact, boot or diagnostic application has yet passed.

Continuation checkpoint 191, 2026-09-30: the independently released
`scratch-3` build ran exactly once.  All 671 source tests and phase 1 passed;
phase 2 then failed before compilation because Rocky's `merge_config.sh`
created `./.tmp.config.*` in the deliberately read-only `/src` working
directory.  This is a new harness temporary-file-placement failure family,
not a McKernel compile result.  There are zero final artifacts and no boot or
application result.

Terminal container
`80e172a592939e2c30ca87a5bc3b9356467876f8ca1716b4ccf718320593eb22`
(`mckernel-exact-d60382667e3d4c1f89a61850e5a1ba59`) exited 1 with PID 0
and remains retained under owner nonce `7662672170dd49eb8a0fb007ff33f007`.
The `runtimeclosure-5` exclusion is identity `1831:31535`, SHA
`0b2cf4f2...e9fccb`; owner receipt SHA is `d4c1bc42...b7e6`, driver receipt
SHA is `265f8d16...9885`, and driver log SHA is `52be2009...cf1`.  The
receipt-bound partial output is approximately 1.8 GiB.  The complete
87,541,760-byte, 52-member failure archive SHA is `4fb88caa...b4ee` and
independently passes archive review.  Additive failure record
`docs/verification/evidence/native-exact-build-74085185-scratch-3-failure-20260930.json`
has SHA `e8670961...f8a0`.

The one bounded correction for this family now independently passes source
review and 20 focused tests.  It anchors exactly one unchanged merge-config
command group, runs only that group from the writable build directory, then
returns automatically to the original workspace cwd for the following solver.
Anchor drift, duplicate anchors and any broader cwd adaptation fail closed;
the source mount remains read-only.  Driver SHA is `1993f3dd...a388` and test
SHA is `d8ddcb51...a5b2`.

Next commit/push/fetch this harness correction and failure record, advance the
wrapper to a fresh exclusion namespace, and prepare a new disk candidate from
that frozen repair commit.  Never rerun the deterministic `scratch-3` request.
Preserve all four stopped failure containers, prior exclusions and archives.
No current-candidate artifact or diagnostic application has passed; formal
counters remain 6/130, 350/10000 and 0/273 applications.

Continuation checkpoint 192, 2026-09-30: the independently reviewed wrapper
successor now permits only the fresh absolute `offlinecwd-6` exclusion and
rejects all five historical paths through `runtimeclosure-5` before loading or
invoking the owner.  Nineteen focused tests pass.  Wrapper SHA is
`3a42e268...b5e1f` and test SHA is `92125ae8...8a1`.

Read-only capacity reconciliation measures 36,814,290,944 host bytes,
33,144,688,640 scratch bytes and 30,642,696,192 available-memory bytes.  A
fresh approximately 9.3-GB disk candidate retains more than the 16-GiB host and
12-GiB scratch floors.  No build, guest, QEMU, mcexec, make or cargo process is
active; the launcher identities remain live.  Docker and lease metadata need
the already authorized dispatcher/root census before execution because the
unprivileged audit could not read them.  All four stopped build-failure
container identities remain protected.

Next freeze and push this wrapper commit, create a separately reviewed
`scratch-4` preparation packet bound to it and the corrected offline driver,
then run preparation and obtain a fresh exact-build release.  No artifact,
boot or diagnostic application result exists yet.

The `scratch-4` preparation packet now independently passes source review.
Packet SHA is `63507d09...31c`, test SHA is `1b13b811...2f0e`, both current
and prior preparation suites pass 68 tests total, and both packets pass shell
syntax checks.  It binds frozen candidate `e1c5e4e2...b74df`, the corrected
offline driver, reviewed wrapper, pinned IHK/overlay/assets, eleven absent
fresh targets and only `offlinecwd-6`.  Preparation calls validation rather
than the owner's run path, cannot acquire a lease or invoke Docker, and retains
partial evidence on failure.  The later fetched packet release remains a
separate required binding.

Next push/fetch this packet release, recheck the fresh targets and resources,
then obtain independent authorization for exactly one unprivileged preparation
run.  No current candidate artifact, boot or diagnostic application has
passed.

Continuation checkpoint 193, 2026-09-30: the exact reviewed `scratch-4`
preparation ran once from fetched packet release
`b9eb98fbf1e6e6819c77dd330fd165ca61108fa4` and independently passes
postflight.  Terminal SHA is `b9d29597...c4906`, log SHA is
`f92646eb...ad90`, and PID/starttime `156365/95002515` plus descendants are
absent.  Candidate `e1c5e4e2...b74df` is identity `1831:4587522`; backup is
`1831:6684674`; pinned IHK, overlay, gitlinks and assets match.  Manifest SHA
is `217454a7...e2d` and request SHA is `afc33966...ed9`.

Output identity `1831:6815746` and evidence identity `1831:7077891` are empty
mode-0700 directories.  The fresh build lease and `offlinecwd-6` exclusion
remain absent.  Owner accounting passes with 9,236,525,056 allocated bytes and
zero memory-backed allocation.  Postflight scratch free is 23,906,914,304
bytes and available memory is 30,636,957,696 bytes, preserving the reviewed
floors.  The authorized Docker census found every McKernel container stopped
and only two unrelated Kasper services live.

Next checkpoint this preparation result, obtain an independent decision for
exactly one build-wrapper invocation using the generated request, and execute
no other heavy work.  Preserve all four current stopped failure containers,
all historical exclusions and archives.  No artifact, boot or diagnostic app
has passed.

Continuation checkpoint 194, 2026-09-30: the independently released
`scratch-4` build ran exactly once.  All 671 source tests, phase 1 and the full
54-case Kconfig matrix passed.  The host kernel linked through final `vmlinux`,
System.map, relocations and post-link tests.  The first current-source compile
defect then appeared while building `ihk_smp_x86_64`: Rust E0107 at
`smp_memory.rs:1007` and `:1050`, where two references omitted the const
generic required by `MemoryMap`.  This is a real module compile failure, not a
harness failure.  There are zero accepted final artifacts and no boot or app
result.

Terminal container
`f93945ad8b4e8439c607a17ac37541de9eaa36fa9ab2f416ed7972edfac972dd`
(`mckernel-exact-d55b9d6762a243b884dfbbd675d5934d`) exited 1 with PID 0
and remains retained under owner nonce `7960e9b4c3384ccd80773ec7a8264358`.
The `offlinecwd-6` exclusion is identity `1831:31541`, SHA
`0ea742e4...75bb`; top receipt SHA is `5899087a...97f8`, build receipt SHA is
`2f0498d8...2ac6`, and driver log SHA is `9b98ae21...7829`.  The receipt-bound
partial output is 4.8 GiB and evidence is 429 MiB.  The independently verified
portable archive is 873,400,320 bytes with 286,248 members and SHA
`217c5618...d58e`; it omits exactly 55 unsafe absolute container-only
symlinks and contains no links or special files.  The original
`1561de5a...611a` archive remains retained unchanged but is rejected as
portable evidence.  Additive failure record
`docs/verification/evidence/native-exact-build-e1c5e4e2-scratch-4-failure-20260930.json`
has corrected SHA `ba821459...9988`.

The one bounded source correction for this family independently passes review:
both `PreparedBoot` helpers now take `MemoryMap<MAX_EXTENTS>`, matching the
production `MemoryContext` field, caller and adjacent helpers.  The exact
two-line diff changes no bodies, ABI, ownership or timeout behavior.  Nine
resource source-contract tests pass; source SHA is `1809dfde...334f`.  The
local host lacks Rust 1.92, so the next exact container build remains the real
compiler check.

The future McKernel image owner also independently passes source hardening at
commit `531f9c3af6a5982d01d323bfd0a7c9ad62b99d02`: 17 focused tests and 14
adversarial probes verify authenticated bootstrap, exact tmpfs/profile,
complete confined inventories, no-follow path handling, under-lease resource
refresh and early-log retention.  This is not image-build or boot authority.

Next independently verify the failure archive, checkpoint this correction,
then recover scratch capacity through a separately reviewed retention cleanup
before advancing to a fresh exclusion/candidate.  Current scratch free space
is 17,455,497,216 bytes, insufficient for another approximately 9.3-GB
candidate while retaining the 12-GiB floor.  Preserve all five current stopped
failure containers and original evidence identities.  Formal counters remain
6/130, 350/10000 and 0/273 applications.

Continuation checkpoint 195, 2026-09-30: the independently reviewed wrapper
successor permits only fresh `memorymap-7` and rejects every historical
exclusion through `offlinecwd-6` before owner loading.  Nineteen focused tests
pass; wrapper SHA is `13a6117f...5550` and test SHA is
`65ade476...60fc`.  This wrapper commit will be the frozen source candidate
after push/fetch.

Capacity remains the immediate prerequisite.  Read-only retention audit found
the minimum safe recovery candidate: only the superseded, fully archived
scratch-1 candidate/output/evidence roots, totaling approximately 9.235 GB.
The first cleanup packet was rejected before execution for broken embedded
Python, incomplete content/restoration binding, stale release binding,
insufficient concurrency/path checks and non-durable failure recording.  No
path was removed.  One corrected packet and behavioral tests are in progress.

Next push/fetch the wrapper checkpoint, complete independent cleanup source and
execution review, recover the exact scratch-1 allocation, then prepare a fresh
candidate from this correction.  Do not reuse scratch-4 or `offlinecwd-6`.

Continuation checkpoint 196, 2026-09-30: scratch capacity was recovered by
relocating the complete superseded scratch-1 candidate before retiring its
scratch copy.  Two complete `rsync -acHAXni --delete` comparisons were empty;
their four stdout/stderr captures each have the empty-file SHA
`e3b0c442...2b855`.  The retained candidate is identity `66306:47475936` at
`/home/holden/mckernel-work/retained-exact-candidates/mckernel-exact-candidate-5aff8eef-scratch-1`,
with Git HEAD `5aff8eef...d57e` and IHK HEAD `3114d9e7...2a1f`.  The original
and atomically renamed retiring paths are absent after a final privileged
process, mount and container-reference census, literal no-follow deletion and
scratch-parent fsync.

The permanent `memorymap-7` exclusion and deletion-start record remain.  The
operational terminal SHA is `56846c46...b673`; independent postflight passes
and also confirms stopped historical container `b5a32f491e35...` remains
retained.  Scratch free space rose from 16,582,082,560 to 25,816,915,968 bytes,
recovering exactly 9,234,833,408 bytes.  The additive checkpoint is
`docs/verification/evidence/native-exact-candidate-relocation-scratch1-terminal-20260930.json`.
This is storage evidence only: it creates no artifact, boot, app or acceptance
result.

Continuation checkpoint 197, 2026-09-30: the source/build boundary is ready
for a fresh frozen candidate.  The disk-build wrapper now permits only
`memorymap-relocated-8` and independently rejects every historical exclusion
through `memorymap-7`; 19 tests pass, wrapper SHA is
`31deba72...cf9`, and test SHA is `f10905f4...dd9e`.  The future image owner
uses the same fresh namespace and explicitly retains the consumed namespace
set.  Its focused 18-test suite passes; this is source readiness, not image
execution authority.

The two-line `MemoryMap<MAX_EXTENTS>` correction is now bound into both the
stage manifest and Rocky staging table.  A dedicated signature regression was
added, and the combined host-audit, image-owner and disk-wrapper run passes all
60 tests.  The exact container compiler remains the required check.

The first scratch-5 preparation draft was rejected before execution because it
discarded manifest/metadata/closure production, pinned the prior wrapper and
contained a literal-tab defect.  It was replaced once from the complete
accepted scratch-4 workflow.  The corrected template independently passes 35
tests and source review, with packet SHA `2ff88daa...c81c` and test SHA
`3ded01e2...d6e0`; unresolved candidate/release/wrapper bindings fail closed.

Next push and fetched-blob verify this checkpoint, bind the scratch-5 template
to that exact candidate/release and wrapper SHA, then perform the separately
reviewed unprivileged preparation.  Recheck the one-heavy-lease census and
16-GiB host/12-GiB scratch floors before the next exact four-job build.  If it
compiles, prepare a distinct reviewed image request before the startup,
memory, files, threads/futexes, signals and controlled-shutdown diagnostics.
No current-candidate artifact or diagnostic application has passed; formal
counters remain 6/130, 350/10000 and 0/273 applications.

Continuation checkpoint 198, 2026-09-30: fetched checkpoint
`61bfbb6cc059f5382b0b19361ff96bf51409620c` and its critical blobs match
origin exactly.  A targeted trim returned 31,214,907,392 unused scratch bytes
to the sparse backing file, increasing host free space from 25,586,978,816 to
54,104,264,704 bytes before preparation.  This resolved the projected host
floor failure without deleting additional evidence.

The independently released scratch-5 preparation then ran exactly once and
passes postflight.  Terminal SHA is `7644f647...8006`, log SHA is
`f74877fc...241`, and PID/starttime `327206/95549247` is absent with no live
children recorded.  Candidate `61bfbb6c...620c` is identity `1831:5505025`;
backup is `1831:6684675`; candidate Git, IHK, overlay, gitlinks, wrapper,
owner, provenance, image and asset bindings match.  Manifest SHA is
`0030a7c0...e43` and request SHA is `a3eb1e6e...c5070`.

Output identity `1831:5111813` and evidence identity `1831:6684676` are empty
mode-0700 directories.  The fresh lease and `memorymap-relocated-8` exclusion
remain absent.  Owner validation records 9,236,836,352 total allocated bytes,
zero memory-backed allocation, postflight host free 44,842,901,504 bytes,
scratch free 16,578,813,952 bytes and available memory 30,169,989,120 bytes.
The additive record is
`docs/verification/evidence/native-exact-candidate-preparation-61bfbb6c-scratch5-success-20260930.json`.

Continuation checkpoint 199, 2026-09-30: the pre-build capacity gate found
only 3,693,912,064 scratch bytes above the 12-GiB reserve, less than the prior
failed build's measured 5,577,920,512-byte output/evidence footprint.  No build
was started.  The complete superseded scratch-2 candidate was independently
found relocation-eligible and copied to host storage.  Two recorded checksum
comparisons plus a third live comparison were empty.  Atomic no-replace
publication retained it at identity `66306:47582206`, Git
`63235981...e292`, IHK `3114d9e7...2a1f`; source inode `1831:6160385` was
then atomically retired and literally deleted after a fresh process, mount and
running-container census.

All scratch-2 output, evidence, archive, request, preparation, metadata and
stopped container `340d3232f39b...` remain.  Operational terminal SHA is
`d31458a9...2532`.  Relocation recovered 9,234,927,616 scratch bytes and the
targeted trim returned 11,704,426,496 bytes to the host backing file.  Current
host/scratch free measurements are 44,756,668,416/25,813,733,376 bytes, leaving
12,928,831,488 scratch bytes above reserve.  The additive record is
`docs/verification/evidence/native-exact-candidate-relocation-scratch2-terminal-20260930.json`.

Next require an exact one-shot build execution decision using request SHA
`a3eb1e6e...c5070`.  If it passes, invoke only the reviewed wrapper command,
retain its exclusion/container/process identities and checkpoint its first
compiler result.  No current-candidate artifact, boot or diagnostic application
has passed.

Continuation checkpoint 200, 2026-09-30: the independently released scratch-5
build ran exactly once and stopped in 28 seconds during phase 0, before any
compilation.  The fail-closed IHK-007 mapping contract still bound the prior
109,016-byte `smp_memory.rs`; the reviewed const-generic correction made the
file 109,042 bytes with SHA `1809dfde...334f`.  Exact failure text is
`mapping consumer source size differs: actual=109042, expected=109016`.
There are zero compiled artifacts, no image, and no runtime result.

Terminal container `f64d0a94e8cc1ab5550be5a3f026e3aabc98f3c101fc6a2f5003d3a3d30a172d`
(`mckernel-exact-d3bc830f8349442382a6197bbe1be32e`) exited 1 with PID 0
and remains retained under owner nonce `3e2b534d6b0e4d7993446e495a197df4`.
The `memorymap-relocated-8` exclusion is identity `1831:57554`, SHA
`03b43991...bb8`; owner receipt SHA is `3dc0c127...254`, build receipt SHA is
`5706ea81...d83`, and driver log SHA is `d8646cbe...dbe`.  Output contains no
build files and evidence allocation is 217,088 bytes.  Additive failure record
`docs/verification/evidence/native-exact-build-61bfbb6c-scratch5-failure-20260930.json`
preserves these identities.

The one bounded correction for this failure family changes only the
`smp_memory.rs` source size/SHA row in
`host-kernel/native-rust/ihk-mapping-foundation-contract-v1.json`.  No mapping
consumer, arithmetic, ownership, limit, marker or oracle changes.  All 23
focused mapping tests pass and independent source review passes; corrected
contract SHA is `cb5d9694...89ef`.  A related optional host/workflow suite did
not start under local Python 3.9 because an existing annotation requires a
newer interpreter; this is not counted as a pass or a new kernel failure.

Next advance both build and image owners to a fresh exclusion namespace,
freeze and push the correction, then prepare a fresh candidate.  Never rerun
the deterministic scratch-5 request or reuse `memorymap-relocated-8`.  Preserve
its candidate, evidence, exclusion and stopped container until durable
retention is independently verified.  No diagnostic app has run.

Continuation checkpoint 201, 2026-09-30: the consumed scratch-5 candidate is
now durably retained at host identity `66306:47622717`.  Before source
retirement, a 1,433,600-byte portable failure archive with 49 safe members was
created at SHA `e84ec295...74b3`; it retains the request, manifest,
preparation, exclusion and complete output/evidence.  Two full checksum
comparisons were empty, and independent relocation postflight passes.  Source
inode `1831:5505025` is absent after atomic retirement and literal deletion;
all failure evidence and stopped container `f64d0a94...` remain.  Relocation
recovered 9,235,308,544 scratch bytes and trim returned 15,352,991,744 bytes.

Fetched correction/release `43e9dbbddd384d4197f981ada7f7a6ecced75555`
then produced a fresh validated candidate exactly once.  Terminal SHA is
`5dd5ca4f...9cea`, log SHA is `34f5d96a...ec8e`, candidate identity is
`1831:6422529`, and backup identity is `1831:6291500`.  Manifest/request SHAs
are `09c1eaa3...ef38` and `6f6dd8f9...1409`.  Output/evidence identities
`1831:6291501`/`1831:6291502` are empty mode-0700; the lease and fresh
`mappingbinding-9` exclusion are absent.  Post-preparation host/scratch/memory
availability is 35,261,022,208/25,809,145,856/30,179,463,168 bytes.

Next independently verify preparation postflight, push/fetch this checkpoint,
and obtain release for exactly one generated build request.  Preserve the
prior phase-0 failure unchanged.  No compiled current-candidate artifact,
image, boot, guest app or shutdown result exists yet.

Continuation checkpoint 202, 2026-09-30: the corrected mapping-contract build
ran once and passed the prior IHK-007 binding.  It then failed in phase 0 at
the next fail-closed source binding: `ihk-smp-native-lifecycle-check: SMP
compiled dependency digest differs: host-kernel/native-rust/smp_memory.rs`.
It stopped before compilation with zero artifacts and no runtime result.
Container `a06adba2c333...` exited 1/PID 0 and remains retained; owner/build/log
SHAs are `254f9d27...fb09`, `b5d19b52...c8e8` and `0f00ca5a...fb9d`.
The consumed `mappingbinding-9` exclusion is identity `1831:57567`, SHA
`54494d76...cf5a`.  A 1,433,600-byte, 49-member portable failure archive has
SHA `8956c1cd...b5cf`.

The bounded lifecycle correction updates only the `smp_memory.rs` dependency
SHA in the lifecycle contract/checker.  Eighty-nine lifecycle/link-closure
tests pass; independent review confirms no lifecycle, ownership, resource or
oracle change.  To avoid another serial source-binding failure, a complete
old-digest sweep also regenerated the unsafe/FFI ledger mechanically: 55
inputs and 637 site IDs/annotations/policy remain unchanged, 63 repeated file
hashes and 41 byte spans moved with the 26-byte source delta, 45 tests pass,
and RS-011 remains `NOT_READY`.  The combined focused source run passes 182
tests.  No acceptance credit is awarded.

The consumed candidate is checksum-preserved at host identity
`66306:47725821`; source inode `1831:6422529` is absent after atomic retirement
and literal deletion.  Relocation recovered 9,235,443,712 scratch bytes and
trim returned 19,715,186,688 bytes.  All request/preparation/failure evidence,
exclusion and the stopped container remain retained.  Current build wrapper
advances to fresh `lifecyclebinding-10` and rejects all history through
`mappingbinding-9`; its 19 tests pass.

Next push/fetch this complete source-binding correction, update the reviewed
preparation template to `lifecyclebinding-10`, and prepare a fresh candidate.
Do not reuse either failed scratch-5 request.  The next exact build remains the
first compiler check; no diagnostic app has run.

Continuation checkpoint 203, 2026-09-30: fetched complete binding-sweep commit
`dce800af8c19d014ef509e102ca4f4b1c473e2ab` produced a fresh candidate and
request exactly once.  Independent postflight passes.  Terminal/log SHAs are
`2788c195...dcd9`/`d0dac54f...c0e4`; PID `370707` and descendants are absent.
Candidate/backup identities are `1831:5242884`/`1831:5373996`; exact Git, IHK,
overlay and generated closure bindings match.  Manifest/request SHAs are
`0b80c8ad...74ce`/`d0cdd1e8...b039`.

Output/evidence identities `1831:5373997`/`1831:5373998` are empty mode-0700,
and the fresh lease plus `lifecyclebinding-10` exclusion are absent.  Current
host/scratch/memory availability is
25,802,477,568/25,804,738,560/30,159,790,080 bytes.  This leaves about 8.62 GB
of host headroom above reserve and 12.92 GB of scratch headroom, both exceeding
the measured 5.58-GB prior partial build footprint.

Next push/fetch this preparation checkpoint, reconcile the single heavy lease
and obtain exact execution release for request SHA `d0cdd1e8...b039`.  Run no
other heavy operation.  A successful run must compile past Rust E0107 before
any image or diagnostic boot is attempted.

Continuation checkpoint 204, 2026-09-30: the exact `dce800af` candidate passed
all earlier phase-0 source bindings, completed the Kconfig matrix and built the
Linux kernel, then failed during native-module objtool validation after 31m47s.
Container `6efd149e8b8c...` exited 1/PID 0, was not OOM-killed and remains
retained.  Objtool reported exactly two Rust fall-through diagnostics at
`Memory::publish_zero` and `Vec<Tagged>::swap_remove`; no module/image/guest
result is accepted.  Receipt/driver/build-log SHAs are
`b36a9d8f...8e0a`/`425dc05f...2808`/`e8c8af7a...8eb3`.  The 4.81-GB output,
444-MB evidence root, source candidate and consumed `lifecyclebinding-10`
exclusion identity `1831:57580` remain unchanged; the build lease is absent.

The bounded correction activates the already reviewed Rust-1.92 patch 0025
immediately after patch 0024 in the exact build workflow.  Patch 0025 is
specific to `Vec::swap_remove::assert_failed`, documents these two native
zeroing call sites, and preserves all objtool checks and unknown-callee
controls.  No Rust implementation or oracle changed.  The workflow prefix,
staging step and active runtime/FP-0006/RS-006 consumer hashes were rebound
exactly.  The focused workflow/patch suite has 132 passes and one configured
Rust-1.92 skip; its only failure is an unrelated synthetic GitHub fetch of an
unadvertised random object.  A separate interrupted FP-0006 checkout fixture
left a disposable 9.22-GB `/tmp` tree; removing only that tree restored
host/scratch availability to 18.97/20.22 GB without deleting build evidence.

Next durably archive the original failure roots and relocate the consumed
candidate, advance build/image/preparation owners to a fresh exclusion
namespace, and prepare one new candidate from the pushed correction.  Obtain
fresh independent execution release before the next exact build.  It must pass
the two retained objtool diagnostics before image preparation or diagnostic
startup/memory/files/threads/signals/teardown execution.  Diagnostic results
remain separate from formal acceptance.

Continuation checkpoint 205, 2026-09-30: the original `dce800af` objtool
failure is now portable and the corrected retry candidate is prepared.  The
335,902,720-byte failure archive has SHA `f8522be9...5952`; the complete
4.81-GB output, 444-MB evidence, receipt/log hashes, consumed
`lifecyclebinding-10` identity `1831:57580`, and stopped container
`6efd149e8b8c...` remain unchanged.

The first relocation attempt failed safely before rename or deletion because
its cross-filesystem inventory compared filesystem-specific directory
`st_size`.  Source and temporary copy both retained 10,725 entries and an
independent checksum rsync was empty.  That failure is preserved in
`native-exact-candidate-relocation-dce800af-copy-verification-failure-20260930.json`.
The bounded resume normalized directory size only, retained regular hashes and
sizes, symlink targets and hardlink topology, then passed complete independent
source and execution review.  Resume terminal SHA is `b66a36b2...d8f52`;
the candidate is now host identity `66306:47736554`, and the original scratch
source is absent.  A targeted trim returned 12,436,381,696 bytes.

Two separately reviewed exact duplicate-evidence cleanups removed only
single-link files byte-identical to pinned Git blobs from retained source
checkouts.  The first removed 2,422 files/9,100,673,024 allocated bytes from
the `63235981` checkout; the second removed 2,437 files/9,100,873,728 bytes
from relocated `dce800af`.  Both terminal plans and per-file Git restoration
maps are committed as compressed evidence.  Neither cleanup touched build
output/evidence, failure archives, stopped containers, differing files,
directories or links.

Fetched correction `8b5056f836ecd3e6916625696750c4dfadbaaf9f`
was prepared once as scratch-6.  Preparation terminal/log SHAs are
`dd243ae0...9b95`/`08e4004f...d76b`; candidate identity is `1831:5111816`,
manifest/request SHAs are `c1ad79ea...d719`/`f234ca2c...00d4`, and empty
output/evidence identities are `1831:6553623`/`1831:6553638`.  The lease and
fresh `objtoolbinding-11` exclusion remain absent.  Independent build-source
review confirms patch 0025 follows 0024 with `--fuzz=0`, both build commands
remain fixed at `-j2`, and the reviewed container profile remains CPUs 2-5,
12 GiB with no additional swap, network none and 512 PIDs.

Post-cleanup host/scratch free space is 27,232,235,520/19,873,378,304 bytes,
above the 16/12-GiB floors and the prior 5.25-GB partial-build footprint.
Next obtain the refreshed one-heavy-lease execution decision and run exactly
the scratch-6 wrapper request.  It must first pass both retained objtool
diagnostics; if compilation completes, prepare a separately reviewed image
request, then boot and run real startup, memory, files, threads/futexes,
signals and controlled-shutdown diagnostic apps.  Current-candidate build
attempts in this loop: one failed `dce800af` build and zero completed images.
Real diagnostic guest applications in this loop: zero.  Formal counters remain
6/130, 350/10000 and 0/273 applications; no cleanup, preparation or diagnostic
result is acceptance credit.

Continuation checkpoint 206, 2026-09-30: the independently released scratch-6
build ran exactly once and stopped after 45 seconds in phase 0, before any
compilation.  The exact runtime-evidence contract carried the correct
95,328-byte workflow SHA-256 (`030822f4...8629`) but a stale Git blob identity;
the checker rejected it with `runtime repository workflow identities differ`.
No compiler artifact, image, boot or application result exists.  Container
`92b2f3fed037...` exited 1/PID 0, was not OOM-killed and remains retained.
Output is empty; evidence allocation is 229,376 bytes.  Owner/build/driver-log
SHAs are `fba8703b...4107`, `ffa7765a...889` and `6023ceed...df5`; consumed
`objtoolbinding-11` is identity `1831:57597`.  Additive failure record
`native-exact-build-8b5056f8-scratch6-runtime-workflow-failure-20260930.json`
preserves the exact terminal state.

The bounded correction changes only that workflow Git blob to
`7d922ef0efc6629837b9fdb090d596bd63d90d69` and cascades the two exact contract
digests.  The workflow semantic validator passes and independent source review
passes.  A broader optional RS-006 follow-up still reports seven pre-existing
inventory mismatches and receives no credit; it is not in this phase-0 build
path.  Build/image owners now use fresh `runtimeblob-12`, explicitly retiring
`objtoolbinding-11`; 38 focused tests pass.  The pushed retry source is
`c658175ae1831e2caef6ecf59730a272f1324645`.

Scratch-6 remains identity `1831:5111816` and consumes 9,235,599,360 allocated
bytes.  Current host/scratch free space is approximately 27.0/19.9 GB; copying
a fresh candidate now would violate the 12-GiB scratch reserve.  Next create a
portable archive of the exact scratch-6 failure, relocate the source to host
under separately reviewed no-replace/capacity/process/container gates, trim
scratch, and run the reviewed scratch-7 preparation bound to `c658175a` and
`runtimeblob-12`.  Then obtain one fresh execution release and run the exact
build.  It must pass the retained phase-0 and objtool failures before image or
real startup/memory/files/threads/signals/shutdown diagnostics.  Current-
candidate builds in this loop: two failed, zero completed.  Real diagnostic
guest applications: zero; all diagnostic results remain separate from formal
acceptance.

Continuation checkpoint 207, 2026-09-30: scratch-6 failure retention and the
fresh `runtimeblob-12` candidate are now complete.  A separately reviewed exact
cleanup removed 2,433 single-link files byte-identical to pinned Git blobs from
the retained `43e9dbbd` source checkout, recovering 9,100,791,808 allocated
bytes.  Its immutable audit and complete Git restoration maps are committed;
the checkout now uses 142,946,304 bytes.  No differing source, build output,
failure evidence, archive or container was removed.

The scratch-6 phase-0 failure is portable in a 1,413,120-byte, 47-member archive
with SHA `73532685...e01f`; source is excluded.  The first relocation preflight
failed before copy because absent fixed `/run` lease paths were passed to the
privileged tombstone reader.  Its zero-byte log/lock identities and additive
failure record remain.  The bounded retry accepts only seven well-formed
terminal tombstones whose PID/starttime owners are absent or reused, while
preserving every lease file.  It copied and fully verified 9,231,400,960 source
bytes, atomically published host identity `66306:47727926`, then retired source
identity `1831:5111816`.  Output/evidence/request/manifest/archive, stopped
container and both relocation attempts remain.  Targeted scratch trim returned
13,304,832,000 bytes; post-trim host/scratch availability was approximately
35.7/29.1 GB.

The first scratch-7 preparation cloned exact pushed candidate `c658175a` but
failed closed before metadata conversion: its post-clone gate incorrectly
budgeted a second 9.2-GB checkout.  Original terminal/log SHAs are
`a9bf9967...f87b`/`47344ca5...982f`, and the full untouched clone remained at
identity `1831:6684719`.  A fresh reviewed resume binds that original failure,
the complete source closure and its own fetched packet, uses unique retry paths,
and budgets only incremental metadata/emergency space.  Thirty-nine focused
tests and independent source/execution reviews pass.

Resume preparation now passes with manifest SHA `e63cd03b...70a3`, request SHA
`7a0a654c...d826`, terminal/log SHAs `99e4f0bf...6ac4`/`6a0582b7...03c3`,
empty output/evidence identities `1831:5111838`/`1831:5111853`, and absent lease
and `runtimeblob-12` exclusion.  The request retains CPUs 2-5, 12 GiB, no
additional swap, no network, 512 PIDs and fixed build limits.  Current
host/scratch/memory availability is approximately 26.3/19.9/29.6 GB.

Next obtain one fresh heavy-build execution release for request
`7a0a654c...d826` and run only its exact wrapper.  It must pass the corrected
runtime-workflow phase-0 binding and both retained objtool diagnostics before an
image request is prepared.  Then regenerate source-bound startup/memory/files/
threads/signals/shutdown diagnostic packets.  Current-candidate builds in this
loop: two failed and zero completed.  Real diagnostic guest applications: zero;
no retention or preparation result is acceptance credit.

Continuation checkpoint 208, 2026-09-30: the exact `c658175a` build executed
once and failed closed in phase 0 before compilation because the isolated
runtime checker normalized SHA-256 no longer matched its refreshed embedded
self identity.  Container `4a0ffec...c7df2` exited 1 without OOM; the original
request, manifest, empty output/evidence roots, owner/build receipts, driver
log, operational exclusion, and failure record remain.  The portable 48-member
failure archive is 1,402,880 bytes at scratch identity `1831:57617`, SHA
`ee326adc...6cef`; it excludes the source tree.

The bounded correction refreshed only the eight-file runtime-checker digest
cascade.  The normalized digest is `36346f23...1b3`; the full checker SHA is
`84f2eb8a...ce17f`.  Three focused controls, the runtime contract validator,
38 namespace tests, and independent source review pass.  The candidate
operational namespace advanced from `runtimeblob-12` to `selfdigest-13`; this
is source/light-regression evidence, not a successful build.

The large failed candidate is retained without consuming the scratch build
floor.  The first relocation packet bound the wrong archive, the second failed
while routing its preserved failure record, and the verification-only retry
then exposed an unbound `FAILURE` variable.  All three failures and their
zero-byte lock/log identities are preserved.  The final `resume3` fixture
executes the real 25-argument `main()` to record-routing boundary, catches the
missing binding, and passes 11 tests plus independent source and execution
review at fetched commit `8fcc4d47`.

The reviewed live resume hashed all 10,746 source and temporary entries,
checked metadata/hardlinks and an empty checksum-mode rsync delta, atomically
promoted temporary identity `66306:47753167`, rechecked both trees, and only
then deleted source identity `1831:6684719`.  The destination is
`/home/holden/mckernel-work/retained-exact-candidates/mckernel-exact-candidate-c658175a-scratch-7`;
both the scratch source and temporary pathname are absent.  Terminal/log SHA
is `36a8c132...51d6`.  Targeted scratch trim returned 13,027,381,248 bytes;
post-trim host/scratch availability is 34,776,424,448/29,093,855,232 bytes.
The additive result is
`docs/verification/evidence/native-exact-candidate-relocation-c658175a-resume3-result-20260930.json`.

Next prepare one fresh exact candidate from the corrected pushed head using
the `selfdigest-13` wrapper/image-owner namespace and a new scratch/output
namespace.  Bind the post-clone capacity gate only to metadata plus emergency
headroom, then obtain a fresh heavy-build release and run one exact build.  It
must clear the retained phase-0 self-digest and objtool failure families before
image preparation and real startup/memory/files/threads/signals/shutdown
diagnostic applications.  Current-candidate builds in this loop: three failed,
zero completed.  Real diagnostic guest applications: zero; diagnostics remain
separate from formal acceptance.

Continuation checkpoint 209, 2026-09-30: fresh `selfdigest-13` candidate
preparation passes for exact source `f021bdee206944fc9c68a3f1f2e0f6683a849435`.
The reviewed scratch-8 packet protects both the host sparse-backing filesystem
and scratch at reserve + metadata + emergency after clone and after preparation,
without double-counting checkout bytes.  Its 40 focused tests and independent
source/execution reviews pass at fetched release `5829a9e2`.

The candidate is
`/home/holden/mckernel-work/scratch/mckernel-exact-candidate-f021bdee-scratch-8`,
identity `1831:5242921`, with 9,237,291,008 allocated bytes.  Manifest SHA is
`595382ec...40af`; request SHA is `afa27486...37e9`.  Terminal/log SHAs are
`0b6c1112...69bc`/`0d431898...c854`, with preparation PID 719558, starttime
97695444, return 0.  Output/evidence identities `1831:6684756` and
`1831:6684763` are empty; the build lease and `selfdigest-13` exclusion remain
absent.  The request preserves CPUs 2-5, 12 GiB, no extra swap, no network,
512 PIDs, and the four-job ceiling.  Post-preparation host/scratch/memory
availability was 25,351,069,696/19,853,746,176/29,325,033,472 bytes.

Independent heavy-build readiness is PASS_EXECUTION: exact candidate/IHK,
wrapper, owner, runtime checker/contract, image receipt, manifest/request,
empty roots, leases, process census, and unfiltered Docker state match.  Run
only `scripts/native_rust_exact_disk_build_wrapper.py` from the prepared
candidate with the exact scratch-8 request.  This is the single active heavy
lease.  It must clear the preserved self-digest and objtool families before
image preparation; no preparation result is build or runtime acceptance.

Continuation checkpoint 210, 2026-09-30: scratch-8 cleared the prior phase-0
self-digest and objtool families and completed the real Linux/kernel-module
compile.  `bzImage` is 16,130,048 bytes, SHA `12e6b40b...4c6`; Rust-linked
`ihk.ko`, `ihk-smp-x86_64.ko`, and `mcctrl.ko` have SHAs
`b4dbf04c...dc9f`, `268d6d3b...4bbb`, and `d927bc44...019`.  Build phase is
`complete` with exit 0.  This is a compiled diagnostic artifact set, not a
completed exact build or bootable McKernel image.

The post-compile lifecycle oracle then failed on 11 intentional
`MCKERNEL_IHK_V1` GPL exports absent from its frozen nine-symbol allowlist.
Independent source and ELF review binds all 20 exact definitions and 60 GPL
metadata relocations.  Container `b34323f6...c001` is retained, exited 1,
OOM false; owner/build/inspect receipt SHAs are `f1f58d48...f3c`,
`49d1a830...ae5`, and `5e7dbe6f...1df`.  The original driver log SHA is
`1aefe4c0...29ef`, and the source/output/evidence/exclusion remain.  Evidence
is `docs/verification/evidence/native-exact-build-f021bdee-scratch8-export-allowlist-failure-20260930.json`.

The bounded correction extends both lifecycle and downstream runtime evidence
contracts to the exact source-confirmed 20-symbol set while retaining rejection
of missing, unknown, unexported `ihk_os_*`, non-GPL, and namespace-drift cases.
Its digest/closure cascade is under final independent source review; do not
prepare a new candidate until that review passes and the exact corrected files
are pushed.

Capacity recovery removed only 2,452 single-link files byte-identical to exact
c658 Git blobs from retained identity `66306:47753167`.  The complete 1,597,062-
byte restoration plan SHA is `300fa3d2...0aee`; 9,101,340,672 allocated bytes
were recovered and the checkout fell from 9,244,356,608 to 143,015,936 bytes.
Its commit/identity are unchanged; all planned targets are absent and all
non-target state remains.  Two cleanup-harness failures occurred before any
deletion: unrelated lsof FUSE warnings were misrouted as references, then a
fresh dynamic census was compared byte-for-byte with the stored census.  Both
original messages, zero-deletion checks, bounded corrections, 20 regressions,
and the passing result are retained in
`docs/verification/evidence/native-exact-retained-candidate-c658175a-evidence-cleanup-result-20260930.json`.

Host/scratch availability is now approximately 27.42/14.20 GB.  Next reclaim
only Git-identical evidence copies inside the stopped f021 source, preserving
its source delta, build output/evidence, receipts, exclusion and exited
container.  Then prepare a fresh corrected candidate, rerun the single exact
build, and proceed to image/startup diagnostics only after a complete build
receipt.  Current-candidate builds in this loop: four failed, zero completed;
one produced a complete compile/artifact set before oracle failure.  Real
diagnostic guest applications: zero.

Continuation checkpoint 211, 2026-09-30: the exact-20 export correction is
pushed.  It passes 57 lifecycle tests, 169 pinned-Python-3.12 runtime tests,
runtime/closure contract validation, and replay against preserved `ihk.ko` SHA
`b4dbf04c...dc9f`.  The strict missing/unknown/unexported `ihk_os_*`, non-GPL,
and namespace controls remain.  Current lifecycle/runtime checker SHAs are
`8773eb0d...67ec` and `d86b2177...ec8d`; runtime contract SHA is
`bf94a508...767e`.  FP capture, RS006 and FP closure digest cascades are
`cbf580e8...e8d0`, `14c4b671...27f`, and `2c7fbe7e...6657`.

Broader preexisting gates remain explicit: the FP full-repository fixture
exceeded its bounded 512-MiB tmpfs, its direct validator rejects an existing
hardlinked witness, closure tests retain 17 nlink-guard failures, and RS006
retains seven HEAD inventory mismatches plus hardlink/fixture compilation
failures.  These are not waived and are not attributed to the bounded export
correction.

The stopped f021 source now retains only non-duplicate state.  A reviewed
2,479-target plan removed 9,102,540,800 allocated bytes identical to exact
`f021bdee` Git blobs.  Candidate identity `1831:5242921` and HEAD are unchanged;
allocation fell from 9,237,291,008 to 134,750,208 bytes.  Build output/evidence,
request, manifest, preparation records, metadata, `selfdigest-13` exclusion,
and stopped container `b34323f6...c001` remain.  The complete restoration plan
SHA is `cb35c05d...52cb`.

Two delegated-cleanup failures occurred before deletion: the first retained
host mount expectation rejected scratch device `1831`; the second adapter used
a zero-argument audit signature while the proven apply path supplied three
pinned arguments.  Both original errors, full-present target checks, bounded
corrections and eight apply-integration regressions are recorded in
`docs/verification/evidence/native-exact-retained-candidate-f021bdee-scratch8-evidence-cleanup-result-20260930.json`.
The corrected apply passed, then targeted trim returned 13,968,592,896 bytes.

Host/scratch availability is approximately 37.04/23.30 GB.  The exact fresh-
clone floor remains about 0.43 GB higher on scratch.  Next archive and retire
only the stopped build's expanded evidence root, preserving exact contents and
all compiled outputs, then prepare a new source-bound candidate from the pushed
exact-20 correction and rerun one build.  Current-candidate builds remain four
failed and zero completed; one has a complete compiled artifact set but failed
the now-corrected post-compile oracle.  Real diagnostic guest applications:
zero.

Continuation checkpoint 212, 2026-09-30: the stopped f021 expanded build-
evidence tree is durably archived and retired.  The archive SHA is
`ac7d2026...13d0`; its full map SHA is `23e418e1...fc2f9` and binds 286,318
members: 285,811 regular files, 452 directories and 55 symlinks.  Audit-only
execution verified every member before the separately released destructive
run.  The canonical retirement result is identity `66306:47475584`, SHA
`bd37b8cf...852f`, status `RETIRE_PASS`; source identity `1831:6684763` is
absent.  Candidate, compiled output, request, original build failure and exited
container `b34323f6...c001` remain protected.  Targeted trim returned
3,785,367,552 bytes.  Post-trim host/scratch availability is
36,719,865,856/23,786,360,832 bytes, preserving the unchanged reserve floors.

Two original audit-only failures remain additive evidence.  The first rejected
an unsupported Docker `inspect --no-trunc` flag before archive verification;
the second exposed that archived regular-file rows include `allocated_bytes`
while the live comparison initially omitted the field.  Neither attempt
deleted a member or published a result.  The bounded corrections pass 22
fault/integration tests, including nested retirement, partial-failure
`RETIRE_PREPARED`, root/result replacement, short writes, exact stopped-
container state and per-type archive schema controls.  Full evidence is
`docs/verification/evidence/native-exact-f021bdee-evidence-retirement-result-20260930.json`.

The downstream runtime oracle now binds the actual preserved consumer graph:
SMP imports eight exact provider symbols, including create-v4 and
with-kobject-v1; mcctrl imports the anchor plus six service/application
symbols.  The complete digest cascade passes 170 pinned-Python-3.12 tests and
real-ELF replay for ihk/SMP/mcctrl.  Existing FP/closure hardlink rejection and
seven RS006 inventory mismatches remain non-waived.  Because this correction
postdates frozen candidate `4197febb`, scratch-9 is retained as an unexecuted
historical packet and must not be run.  Next issue a fresh scratch-10
preparation packet bound to pushed runtime-corrected HEAD, remeasure the narrow
scratch margin, prepare the candidate, and run the single exact build.  Current-
candidate builds remain four failed and zero completed; real diagnostic guest
applications remain zero.

Continuation checkpoint 213, 2026-09-30: fresh scratch-10 preparation passes
for runtime-corrected candidate `e8bece7fd55a862599facb6c5e81e7597a4a5c0d`.
The independently reviewed packet preserves the four-CPU/12-GiB/no-network
profile and `exportset-14` namespace; 41 focused tests pass.  Candidate identity
is `1831:5111900`; manifest/request SHAs are `61500ea9...24ec` and
`2f02bce2...8f9c`.  Terminal/log SHAs are `e9440d52...8c50` and
`b91c1d9a...30e4`, with preparation PID 954964, starttime 98609654 and return
0.  Output/evidence identities `1831:4457328`/`1831:4457329` are empty; build
lease and exclusion are absent.  Full bindings are in
`docs/verification/evidence/native-exact-candidate-preparation-scratch10-result-20260930.json`.

Post-preparation host/scratch/memory availability is
27,357,286,400/14,546,067,456/29,309,054,976 bytes.  Although the immediate
12-GiB reserve still passes, the prior exact build produced about 5 GiB of
output; starting it now would cross the reserve.  Do not run the heavy build
until at least that measured requirement plus emergency headroom is recovered.
Next apply a separately reviewed Git-identical cleanup to one older retained
candidate, preserving its deltas/output/failure records, remeasure capacity,
then obtain a fresh heavy-build release for request `2f02bce2...8f9c`.
Current-candidate builds remain four failed and zero completed; real diagnostic
guest applications remain zero.

Continuation checkpoint 214, 2026-09-30: the older retained `74085185`
candidate supplied the measured build headroom without losing original
evidence.  A reviewed immutable plan identified 2,424 nlink-1 files under its
candidate evidence tree that were byte-identical to pinned Git blobs, with
zero differing files and 9,100,578,816 allocated bytes.  Apply re-audited the
entire plan, removed exactly those targets, and returned 0.  Plan identity is
`66306:47496551`, SHA `fbfa4cc7...461b0`; all targets are absent.  Candidate
identity `1831:3932163` and HEAD `74085185...f3954e6` are unchanged, and its
allocation is now 134,406,144 bytes.  Build output/evidence, metadata, request,
manifest, preparation records, original failure record/archive, operational
exclusion and stopped container all remain; the build lease remains absent.

The first live audit failed before plan publication or deletion because three
protected 0644 records were incorrectly frozen as 0600.  Its additive failure
record and the bounded 22-test correction are preserved.  Targeted trim
returned 11,894,759,424 bytes.  Host/scratch/memory availability is now
36,231,135,232/23,646,646,272/29,310,828,544 bytes.  Full result:
`docs/verification/evidence/native-exact-retained-candidate-74085185-source-evidence-cleanup-result-20260930.json`.

Next obtain a fresh heavy-build execution release for prepared scratch-10
request `2f02bce2...8f9c` and run exactly one build under CPUs 2-5, 12 GiB,
no swap expansion, 512 PIDs and no network.  It must clear the preserved
post-compile exact-export failure and the newly corrected runtime consumer
graph before image preparation.  Current-candidate builds remain four failed
and zero completed; real diagnostic guest applications remain zero.

Continuation checkpoint 215, 2026-09-30: scratch-10 compiled all three native
modules, then failed its offline postcheck.  The exact retained module SHAs are
`b4dbf04c...dc9f`, `268d6d3b...4bbb` and `d927bc44...019f`; container
`8c56b137...401a` exited 1 without OOM.  The unchanged configured OS-registry
fixture attempted to execute `/tmp/ihk-os-registry-rust-*/registry-tests` and
received EACCES: phase 4 had reconstructed `kbuild_environment` with `env -i`
but dropped the driver's reviewed `RUNNER_TEMP`, `TMPDIR`, `TMP` and `TEMP`.
This is an offline harness failure, not build or Rust-registry acceptance.
Scratch-10 output, evidence, 89-MiB receipt and exited container remain intact.

The bounded correction is in the phase-4 offline adapter.  It requires one
exact environment anchor, carries all four temporary variables across the
isolation boundary, and leaves `/tmp` noexec and the fixture/oracle unchanged.
The offline suite passes 21/21.  A fresh light container with read-only source,
no network, one CPU, 1 GiB, noexec `/tmp` and executable evidence storage passes
the configured Python suite 11/11 and its Rust fixture 15/15.  Two probe-only
failures (the image sleep entrypoint and Git safe-directory ownership) are
preserved with the successful output.  Full evidence is
`docs/verification/evidence/native-exact-build-scratch10-temp-environment-failure-20260930.json`.

Next commit/push this correction, prepare a fresh candidate and request bound
to that commit, independently review it, and run exactly one new heavy build.
Do not reuse scratch-10 or its attempt names.  Current-candidate builds are now
five failed and zero completed; real diagnostic guest applications remain zero.

Continuation checkpoint 216, 2026-09-30: scratch-10 storage maintenance
recovered the source-clone headroom while retaining the failed build.  The
sealed audit plan SHA is `f169bed7...0b35`; it selected 2,491 nlink-1 regular
files under the candidate evidence subtree, all byte-identical to pinned Git
blobs, with zero differing files and 9,102,626,816 allocated bytes.  Apply
re-audited the plan and removed all 2,491 targets.  Candidate identity
`1831:5111900` remains and now occupies 134,848,512 bytes.

Scratch-10's 5.17-GB compiled output, 486-MB full build evidence, exportset-14,
failure record, nested IHK delta and container `8c56b137...401a` remain.  The
container is still exited with status 1, PID 0 and OOM false.  The first audit
failed before plan publication or deletion because Docker's list formatter
reported a short ID; its 39-byte failure is preserved, and the bounded fix adds
independent exact terminal-state inspection.  Fourteen focused tests pass.
Targeted trim reported 15,358,861,312 bytes, leaving host/scratch free space
38,553,763,840/27,096,387,584 bytes.  Full result:
`docs/verification/evidence/native-exact-retained-candidate-e8bece7f-source-evidence-cleanup-result-20260930.json`.

The build and image owners now reserve fresh operational exclusion namespace
exportset-15; 38 focused owner tests pass.  Scratch-11 preparation is bound to
candidate `acd4197b6e1f53715f75cad6e2e7677d8ab24bc0` and packet SHA
`662c8d19...f648`, with 41 tests passing.  Next re-review it against the new
capacity and fetched release, execute preparation only, checkpoint its exact
manifest/request identities, and then obtain a fresh heavy-build release.
Current-candidate builds remain five failed and zero completed; real diagnostic
guest applications remain zero.

Continuation checkpoint 219, 2026-09-30: scratch-11 again completed kernel and
all three native module builds, then failed one later lifecycle oracle.  Module
SHAs remain `b4dbf04c...dc9f`, `268d6d3b...4bbb` and `d927bc44...019f`.
Retained container `d1972570...d954` exited 1 without OOM; driver log SHA is
`83d488a7...7333`.  The prior temp-root failure is cleared: configured registry
fixtures execute and pass.  The new failure is exact and additive: the module
contains reviewed read-only parameter `native_boot_prepare_only`, while the
built-artifact checker compared raw metadata only against the six frozen legacy
parameters.

The bounded checker correction adds the reviewed diagnostic parameter only to
current native artifact `parm`, `parmtype` and rendered-metadata expectations.
The legacy contract remains exactly six parameters, and unknown extras remain
fail-closed.  Sixty focused tests pass, including a new unexpected-parameter
negative.  Full retained failure and artifact identities are in
`docs/verification/evidence/native-exact-build-scratch11-additive-parameter-failure-20260930.json`.

Next commit/push the correction, recover only reviewed Git-identical source
evidence while preserving scratch-11 output/evidence/container, prepare a fresh
source-bound candidate/request, and run one new exact build.  Current-candidate
builds are now six failed and zero completed; real diagnostic guest applications
remain zero.

Continuation checkpoint 218, 2026-09-30: the first scratch-11 heavy-build
review correctly blocked before execution because the measured prior output
would leave scratch 195,735,552 bytes below the hard 12-GiB reserve and
1,269,477,376 bytes below the retained emergency margin.  Request, manifest,
empty outputs, absent lease/exportset-15 and profile all matched; no build ran.

The older e1c5 candidate supplied the missing headroom.  Its independently
reviewed sealed plan SHA is `e965f077...f06d`: 2,426 nlink-1 files were exact
Git blobs, zero files differed, and targets occupied 9,100,566,528 bytes.
Apply re-audited the plan and removed all targets.  Candidate identity
`1831:4587522` remains and now occupies 134,430,720 bytes.  Both original
failure archives, build output/evidence, metadata, request/manifest,
preparation records, offlinecwd-6 exclusion, nested IHK delta and stopped
container `f93945ad...ddf` remain.  The container still reports exited, status
1, PID 0 and OOM false.  Twenty focused tests pass.

Targeted trim reported 9,600,372,736 bytes.  Host/scratch availability is now
38,233,141,248/26,956,496,896 bytes, providing more than the measured build
output plus hard reserve and emergency margin.  Full result:
`docs/verification/evidence/native-exact-retained-candidate-e1c5e4e2-source-evidence-cleanup-result-20260930.json`.
Next repeat independent heavy review for unchanged scratch-11 request
`002b13dc...9db0`, then run one exact build if live ownership/capacity pass.
Current-candidate builds remain five failed and zero completed; real diagnostic
guest applications remain zero.

Continuation checkpoint 217, 2026-09-30: scratch-11 preparation passes for
candidate `acd4197b6e1f53715f75cad6e2e7677d8ab24bc0`, which carries the
postcheck executable-temp correction and fresh exportset-15 namespace.  The
independently reviewed packet SHA is `662c8d19...f648`; 41 focused tests pass.
Candidate identity is `1831:4063240`.  Manifest/request SHAs are
`241a53dd...1587` and `002b13dc...9db0`; output/evidence identities
`1831:3933547`/`1831:3933548` are empty.  The build lease and exportset-15 are
absent.  Preparation PID 1134304/starttime 99197642 returned 0; terminal/log
SHAs are `d83d6f1b...fbfe` and `06070640...35a`.

Post-preparation host/scratch/memory availability is
29,277,093,888/17,855,930,368/29,295,230,976 bytes.  This clears the 16/12-GiB
reserve and leaves about 5.85 GB beyond the scratch reserve, slightly above the
last build's 5.17-GB output.  Next obtain a fresh independent heavy-build
review for request `002b13dc...9db0`, remeasure immediately, and run exactly one
build under CPUs 2-5, 12 GiB, no swap expansion, 512 PIDs and no network.  Full
preparation result is
`docs/verification/evidence/native-exact-candidate-preparation-scratch11-result-20260930.json`.
Current-candidate builds remain five failed and zero completed; real diagnostic
guest applications remain zero.

Continuation checkpoint 220, 2026-09-30: scratch-11's Git-identical candidate
evidence was retired after independent review without removing its failed build.
Sealed plan SHA `d071cf3f...78b2` selected 2,499 nlink-1 exact Git blobs, zero
differences, totaling 9,102,712,832 allocated bytes.  Apply re-audited and
removed every target.  Candidate identity `1831:4063240` remains and occupies
134,922,240 bytes.  Full build output/evidence, metadata, request/manifest,
preparation records, exportset-15, failure record, nested IHK delta and stopped
container `d1972570...d954` remain.  Twenty-eight focused cleanup tests pass.

Targeted trim reported 13,299,142,656 bytes.  Host/scratch free space is now
41,035,231,232/30,406,483,968 bytes.  Full result:
`docs/verification/evidence/native-exact-retained-candidate-acd4197b-source-evidence-cleanup-result-20260930.json`.
Next prepare scratch-12 from the pushed lifecycle-oracle correction, bind a
fresh exclusion namespace, checkpoint it, then run one reviewed exact build.
Current-candidate builds remain six failed and zero completed; real diagnostic
guest applications remain zero.

Continuation checkpoint 221, 2026-09-30: scratch-12 preparation passes for
candidate `4e99a82c9b87a7cf3d6002b75ec380fef37af7a1`, carrying both current
postcheck corrections and exportset-16.  Independently reviewed packet SHA is
`f78ecf5e...490a`; 41 tests pass.  Candidate identity is `1831:3693246`.
Manifest/request SHAs are `4bc0a306...73fa` and `a2eb9345...b1b6`;
output/evidence identities `1831:6555351`/`1831:6555352` are empty, and lease
and exportset-16 are absent.  PID 1304702/starttime 99709551 returned 0.

Post-preparation host/scratch/memory availability is
31,713,222,656/21,165,916,160/29,285,572,608 bytes, above the measured prior
output plus hard reserve.  Full result is
`docs/verification/evidence/native-exact-candidate-preparation-scratch12-result-20260930.json`.
Next obtain fresh heavy-build review and run exactly one scratch-12 build under
the pinned profile.  Current-candidate builds remain six failed and zero
completed; real diagnostic guest applications remain zero.

Continuation checkpoint 222, 2026-09-30: scratch-12 is the first completed
current-candidate exact build in this repair loop.  Candidate
`4e99a82c9b87a7cf3d6002b75ec380fef37af7a1` built the host `bzImage` and all
three native Rust modules; the driver receipt is `PASS`/`complete`, and the
owner returned 0.  Retained container `4d15b349...e4f86` exited 0 with PID 0
and OOM false after running under CPUs 2-5, 12 GiB memory with no swap
expansion, 512 PIDs and no network.  The exact output/evidence roots remain at
identities `1831:6555351`/`1831:6555352` and occupy
5,166,792,704/502,849,536 bytes.  The lease is absent after retirement;
exportset-16 is retained at identity `1831:72288`.

Artifact SHAs are `c995dfd1...985e` (`bzImage`), `b4dbf04c...dc9f`
(`ihk.ko`), `268d6d3b...4bbb` (`ihk-smp-x86_64.ko`) and
`d927bc44...019f` (`mcctrl.ko`).  Owner/driver/terminal receipt SHAs are
`ceb5ee60...572b`, `9f0c9021...deae` and `96eb113a...6e6`.  Post-build
host/scratch/memory availability is
24,836,329,472/15,496,278,016/29,141,811,200 bytes.  Full compact evidence is
`docs/verification/evidence/native-exact-build-scratch12-pass-20260930.json`.
This is build-only evidence: no McKernel image, boot or guest application has
yet run.  Current-candidate builds are six failed and one completed; real
diagnostic guest applications remain zero.

The attempted scratch9 image-admission repair remains rejected and untracked.
After one bounded correction, independent adversarial review still reproduced
invented receipt fields, incomplete provenance/inventory binding, alias and
receipt-link bypasses, and a reservation written before validation with no
actual owner consumer.  Do not use or commit packet SHA `fcecd6a0...6056` or
test SHA `23a940df...1553`; this failure family now requires a fresh expert
design against the actual build/image owner and driver schemas.

Next preserve this successful build, design and independently review a fresh
actual-schema image-preparation owner, then build/authenticate the smallest
current `mckernel.img`.  After a separate one-shot root/guest release, run the
real startup/HELLO diagnostic and capture exact stdout, exit 37, kernel/QMP
logs, process retirement and teardown.  Continue with memory, file,
thread/futex, signal and shutdown diagnostics in fresh attempts.  None of
these diagnostic runs may be promoted to formal application acceptance.

Continuation checkpoint 223, 2026-09-30: shutdown preserves the first image
mapping/source correction as rejected WIP.  Independent integration review
found seven real contract defects despite the earlier isolated green tests:
the owner/driver binding schemas disagreed, real `/out` symlink translation
failed, host and container tool namespaces leaked into each other, receipt and
tool-version contracts disagreed, the old tool schema remained in two owner
paths, RPM epoch/CMake pin evidence was invalid, and the authenticated driver
hash was stale.  One bounded coherent correction was allowed to proceed, then
was stopped at the requested shutdown boundary without Docker, image, root,
guest, or application execution.

The exact shutdown regression ran 58 focused tests and failed with three
errors: both owner integrated fixtures report `PATH tool differs from bound
tool: ld`, and the offline positive v2 fixture reports `complete toolchain
inventory differs`.  `git diff --check` passes.  The six source/test files are
checkpointed as WIP so their exact bytes and failures survive; they are not an
execution release.  Full evidence is
`docs/verification/evidence/native-exact-image-mapping-shutdown-wip-20260930.json`.

The successful scratch-12 build remains intact at output/evidence identities
`1831:6555351`/`1831:6555352`; exportset-16 remains `1831:72288`, and retained
container `4d15b349...e4f86` remains exited 0, OOM false, PID 0.  No heavy
build, QEMU guest, or mcexec process is live.  Launcher wrapper/launcher/worker/
server PIDs are 1442141/1442142/1442145/1442149, all originating at
2026-09-30 10:46:42 -0700.  Host/scratch free space is
24,678,674,432/15,496,278,016 bytes; MemAvailable is 30,157,432 KiB.

Next resume this same failure family rather than dispatching a new one: repair
the `ld` PATH fixture and complete-inventory mismatch, rerun all 58 focused
tests, and obtain independent integration re-review against the real scratch12
`/out` link and nightly mapping.  Only after a pushed PASS_SOURCE checkpoint,
prepare and independently release a refreshed source-free tool image with the
repository-supported CMake 3.31.8 package.  Then build the smallest current
`mckernel.img` and seek a separate root/guest release for strict
`baseline.core.memory`, followed by files, threads/futexes, signals and
shutdown.  Current-candidate builds remain six failed and one completed; real
current diagnostic guest applications remain zero.  No acceptance bar moves,
and the launcher pause does not complete the OS goal.

Continuation checkpoint 224, 2026-09-30: the escalated image-mapping correction
now passes its bounded source gate.  All 58 preparation/owner/offline focused
tests pass in 17.746 seconds; `py_compile`, `git diff --check`, and the owner's
authenticated driver-hash equality also pass.  The corrected driver SHA is
`3867f6cc...5fcf`.  Independent Astra review returns `PASS_SOURCE` after
checking the real scratch12 absolute link and all previously blocking
boundaries.

The repair keeps owner and driver on identical `/out` and `/nightly` namespace
mappings, mounts each validated host root at its explicit container destination,
and records consistent `target`/`resolved`/`container_target` link metadata.
Host source admission now uses a separately hash-bound host Git; it no longer
pretends an image `/usr` binary is the host binary.  Image tool descriptors bind
their lookup spelling and canonical target separately, including strict leaf-
symlink, hash and PATH-selection checks.  Actual negatives cover boolean
`runtime_network`, target mismatch, PATH shadow, host-schema leakage and stale
helper bytes.  Full source identities and review scope are retained in
`docs/verification/evidence/native-exact-image-mapping-source-pass-20260930.json`.

This is source-only evidence.  No Docker preparation, network operation,
McKernel image build, root action, guest or application ran, and no acceptance
counter changes.  The historical source-free image remains unusable because it
lacks CMake and several required tool observations.  Next fetched-blob verify
this checkpoint, then obtain an independent execution release for one fresh
source-free Rocky tool image.  Its actual receipt must establish CMake
`3.31.8-1.el10`, complete package/tool observations and the offline runtime
profile before a deterministic current-image request is prepared.  The strict
first diagnostic oracle remains `baseline.core.memory`: stdout exactly
`NATIVE_CORE PASS memory\n`, stderr empty, exit 37/raw wait 9472.  Current-
candidate builds remain six failed and one completed; real current diagnostic
guest applications remain zero.

Continuation checkpoint 225, 2026-09-30: the exact refreshed tool-image
command has an independently reviewed `PASS_EXECUTION` release after one
rejected packet and one bounded harness correction.  The first review correctly
found that the root-owned Docker socket lacked the reviewed `sudo -A` client
and that `runtime_network=none` was merely declared.  The correction now uses
the privileged Docker transport only from the host owner, retires/commits/
removes the bridge-connected preparation container, then reuses the same
durably leased name and nonce for a fresh offline verification container.

The offline container is network-none, read-only, host uid/gid, cap-drop ALL,
no mounts, private IPC, 4 CPUs pinned to 2-5, 12 GiB without swap expansion,
and 512 PIDs.  It repeats the complete package/tool/RPM probe and must match the
networked observation byte-for-structure before the receipt can record
`runtime_network=none`.  Failure retains the phase-specific evidence and
container; uncertain retirement retains a lease naming the actual survivor.
The combined preparation and owner suite passes 81 tests, including an explicit
offline-unretirable identity regression; `py_compile` and diff-check pass.
Reviewed production/test/harness SHAs are `3af27f6d...dca8`,
`3073e43f...e96a`, and `7aee2f1f...5a61`.  Exact release evidence is
`docs/verification/evidence/native-exact-tool-image-execution-release-20260930.json`.

No Docker mutation or package installation has yet occurred under this release.
The one allowed command uses fresh host output/evidence paths and scratch lease
`native-exact-image-preparation-lease-f0a97d42-1.json`.  Immediately before
execution remeasure the 16/12-GiB host/scratch floors and confirm no live heavy
owner.  Then run it exactly once, retain actual CMake/tool observations, image
ID, both terminal inspections and lease retirement.  Current-candidate builds
remain six failed and one completed; real current diagnostic guest applications
remain zero.  This release grants no image-build, guest or acceptance credit.

Continuation checkpoint 226, 2026-09-30: tool-image attempt1 ran once under
the reviewed release and failed after successful pinned DNF installation and
cleanup.  The package transaction installed CMake `3.31.8-1.el10` and returned
zero.  The subsequent probe called canonical `/usr/bin/lld --version`; the
generic multicall driver returned 1 and instructed callers to use `ld.lld`.
No image was committed and the offline probe did not start.  Receipt SHA is
`eb295e7f...c8392`; failed stderr SHA is `7be3897d...633`; full compact evidence
is `docs/verification/evidence/native-exact-tool-image-attempt1-failure-20260930.json`.

The exact failed container `5b11e19e...97f6` is preserved exited 143, OOM false,
PID 0 with matching owner nonce.  Its lease is absent after proven retirement;
output/evidence identities `66306:45493667`/`66306:45494833` remain.  The one
bounded correction preserves canonical target bytes for RPM owner, NEVRA and
SHA checks but executes the PATH lookup spelling for version output, retaining
argv0-sensitive `ld.lld` behavior.  Eighty-two combined tests, `py_compile` and
diff-check pass.  Independent review grants `PASS_EXECUTION_CORRECTION` to
fresh attempt2 paths only, bound to source/test SHAs `bbe0ee6c...c0b2` and
`4f5befcf...c0db`.

Next push and fetched-blob verify the correction, remeasure resources and run
fresh attempt2 exactly once.  Do not reuse attempt1 paths or remove its failed
container/evidence.  Current-candidate builds remain six failed and one
completed; current tool-image attempts are one failed and zero completed; real
current diagnostic guest applications remain zero.  No acceptance bar moves.

Continuation checkpoint 227, 2026-09-30: shutdown preserves source-free
tool-image attempt2 as a distinct observer-validation failure.  The complete
networked probe now exits zero, proving the prior `ld.lld` argv0 correction;
it observes CMake `3.31.8-1.el10`, `ld.lld` 21.1.8 at lookup path
`/usr/bin/ld.lld` with canonical target `/usr/bin/lld`, and 474 unique RPM
inventory lines.  Validation rejects exactly the legitimate pseudo-package
line `gpg-pubkey-0:6fedfc85-682ae1a9.(none)`, so no image was committed and
the offline probe did not start.  Receipt/tool-observation/terminal-inspect
SHAs are `3153b2a4...9cf`, `cb669ce8...80a4` and `0cb148ba...d2b3`.

The exact failed container `f4068777...10c4` is retained as
`mckernel-tools-8d0cabb2913c4327b657f56cb174e76e`, exited 143, OOM false,
PID 0; its lease is absent after proven retirement.  Output/evidence identities
`66306:45495128`/`66306:45495129` remain.  The bounded correction accepts
`(none)` only as a terminal inventory architecture token and leaves strict
requested-package/tool NEVRA parsing unchanged.  All 84 combined preparation
and owner tests, `py_compile`, and diff-check pass.  Source/test SHAs are
`3a43e305...ba7` and `c2fdbaad...809`.  Full original-evidence binding is in
`docs/verification/evidence/native-exact-tool-image-attempt2-failure-20260930.json`.

No child agent, heavy build, QEMU guest, mcexec, or image-preparation process
remains live.  The launcher wrapper/launcher/worker/server identities remain
1442141/1442142/1442145/1442149, all started 2026-09-30 10:46:42 -0700.
Host/scratch free bytes are 21,650,976,768/15,496,278,016 and MemAvailable is
29,709,432 KiB.  Both failed tool-image containers and all raw evidence remain
retained; attempt3 was not started.

Next obtain an independent execution review of this correction, remeasure the
16/12-GiB floors and emergency headroom, confirm fresh attempt3 paths and no
live heavy owner, then run exactly one attempt3 at the paths recorded above.
If it passes, authenticate the source-free image and prepare the actual-schema
current `mckernel.img` request; only after a separate root/guest release run
strict `baseline.core.memory`, then files, threads/futexes, signals and
shutdown.  Current-candidate builds remain six failed and one completed;
tool-image attempts are two failed and zero completed; real current diagnostic
guest applications remain zero.  No acceptance bar moves, and this launcher
pause does not complete the OS goal.

Continuation checkpoint 228, 2026-09-30: source-free tool-image attempt3
passes its independently reviewed execution and result gates.  The exact
receipt SHA is `1ea38c33...af08`; immutable Linux/amd64 image
`sha256:5315d34307c6658907d3e74997b8e0b0637d237a26c070fe5dc5b03ee7667080`
is retained at 1,665,096,208 bytes.  All 92 receipt inventory entries and 28
captured Docker commands verify.  Networked and fresh offline observations are
byte-identical at SHA `cb669ce8...80a4`, including 474 unique RPM lines,
CMake `3.31.8-1.el10`, LLD 21.1.8 with the correct `ld.lld` lookup spelling,
and exact Rust 1.92.0.  RPM payload verification exits zero with empty streams.

Both phases ran on CPUs 2-5 with 12 GiB/no swap expansion and 512 PIDs, no
host mounts and private IPC.  The sequential offline phase additionally proves
network-none, read-only root, uid/gid 1000:1000 and all capabilities dropped.
Both terminal inspections show exited 143, PID 0, OOM false after bounded
retirement.  The shared container name is currently absent and the lease is
absent.  Owner PID/starttime was 1548639/100458522; output/evidence identities
are `66306:45495353`/`66306:45495354`.  Exact result evidence is
`docs/verification/evidence/native-exact-tool-image-attempt3-success-20260930.json`.

Post-run host/scratch free bytes are 20,115,988,480/15,496,278,016 and
MemAvailable is 29,544,128 KiB.  The retained scratch12 build artifacts still
match their checkpoint hashes, and its `/out` source symlink remains present;
one cheap audit incorrectly resolved that container-relative link against the
host and is not a blocker.  The earlier two failed tool-image containers and
their original evidence remain preserved.

Next create the v2 toolchain manifest and actual-schema current `mckernel.img`
request from this exact receipt/image plus the retained scratch12 build and a
fresh exportset-17.  Obtain independent execution review, then run one image
build.  Once its artifact is authenticated, create a fresh strict memory
manifest and root/guest release; the frozen oracle remains stdout exactly
`NATIVE_CORE PASS memory\n`, stderr empty, exit 37/raw wait 9472.  Tool-image
attempts are two failed and one completed; current-candidate builds remain six
failed and one completed; real current diagnostic guest applications remain
zero.  This tool-image result earns no production, application or OS acceptance.

Continuation checkpoint 229, 2026-09-30: launcher shutdown preserves the
bounded v2 image-request admission/publication repair as reviewed-but-not-yet-
released source WIP.  The first independent source review BLOCKed preparer SHA
`25d06613...0a00` and owner SHA `82807b38...150e` because the final toolchain
was written before full validation, destination confinement was incomplete,
the receipt lock comparison was optional, and publication failure tests were
missing.  The bounded correction now authenticates the actual PASS/retired
tool-image receipt and exact lock digest, validates a privately staged
toolchain before atomic publication/fsync, validates the final binding and
publishes the request last.  It also includes both destinations in protected-
root disjointness checks.

Corrected owner/preparer/test SHAs are `74eb5f72...c3d`,
`cad37c90...7ef`, `ee2713ec...09dc` and `22f07c4a...506`.  All 26 focused
tests pass with `py_compile` and diff-check.  This corrected source has not
received the required independent re-review.  Exact WIP evidence is
`docs/verification/evidence/native-exact-image-request-preparation-wip-20260930.json`.
No exportset-17 toolchain, request or lease was created; all three named fresh
paths remain absent.  No Docker/root/image build, QEMU, mcexec or diagnostic
application ran.

All eight child lanes are closed.  No heavy process is active.  The preserved
launcher wrapper/launcher/worker/server identities are
1442141/1442142/1442145/1442149, started 2026-09-30 10:46:42 -0700.  The
scratch12 backup/output identities remain `1831:6555350`/`1831:6555351` and
tool-image attempt3 evidence remains `66306:45495354`.  Host/scratch free
bytes are 20,073,394,176/15,496,278,016 and MemAvailable is 29,495,596 KiB.

Next independently re-review the exact corrected source hashes.  Only after a
PASS_SOURCE result, create fresh exportset-17, review its actual generated
manifest/request and obtain an independent execution release before one
serialized current `mckernel.img` build.  After authenticating that artifact,
prepare a fresh root/guest packet for strict `baseline.core.memory`, then
files, threads/futexes, signals and shutdown.  Current-candidate builds remain
six failed and one completed; tool-image attempts remain two failed and one
completed; real current diagnostic guest applications remain zero.  No
acceptance bar moves, the OS goal remains incomplete, and this launcher pause
is not permanent.

Continuation checkpoint 230, 2026-09-30: the second independent source review
BLOCKed checkpoint229's first bounded publication correction.  It found a
TOCTOU overwrite at final toolchain publication, partial-final request exposure
on interrupted direct writes, a receipt-derived rather than independently
selected lock expectation, missing full preparation integration coverage, and
overstated resource-profile authentication wording.  Because this was the
second failure in the same family, the work escalated to the bounded expert
lane `/root/image_publication_expert_repair_234` rather than another cheap
retry.

The expert repair privately stages and fsyncs both JSON documents, uses atomic
same-filesystem hard links for no-replace publication, independently requires
and compares the expected toolchain-lock SHA, and retains request-last
semantics.  New tests cover competing publishers, incumbent preservation,
short private writes, independent-lock mismatch and a complete successful
`prepare()` to real `ImageOwner.validate()` path.  Coordinator reproduction
passes all 52 combined tests plus `py_compile` and diff-check.  Final preparer
and test SHAs are `0de9550b...9ba8` and `36d08f58...a600`; unchanged owner and
test SHAs remain `74eb5f72...c3d` and `ee2713ec...09dc`.

Independent re-review now returns `PASS_SOURCE` for those four exact hashes.
The accepted scope is precise: owner admission hash-binds and preserves the
exact independently reviewed producer evidence; it does not semantically
reauthenticate that evidence's resource-profile contents.  This is source-only
admission, not an execution release.  Fresh exportset-17 toolchain/request/
lease paths remain absent and no Docker, build or guest ran.

Next compute the actual scratch12 backup/build and nightly inventories while
creating fresh work/evidence parents, publish the exportset-17 manifest and
request once, and independently review that exact packet.  Then obtain a fresh
image-owner execution release before one serialized current `mckernel.img`
build.  After artifact authentication, rebind the strict memory diagnostic's
image/final-map identity and obtain its fresh root/guest release.  The frozen
oracle remains stdout `NATIVE_CORE PASS memory\n`, empty stderr and exit
37/raw wait 9472.  Real current diagnostic guest applications remain zero and
no acceptance bar moves.

Continuation checkpoint 232, 2026-09-30: the one released exportset-17 image
attempt failed safely before compilation.  The driver receipt is
`b445816d...e55c1`, status FAIL, phase `identity`, exact error
`cc version differs`, with zero commands and empty build stdout/stderr.  Owner
receipt `0fc0386d...b5b56` preserves PID/starttime `1609818/100692872`,
container `282dff5e...d36dde`, owner nonce `44a459e5...1f125` and terminal
state exited1/PID0/OOMfalse.  Retirement is proven, the lease is absent, the
failed container is retained, and consumed exportset-17 exclusion
`6a4c544e...e68c1` remains preserved.

The exact cause is argv0-sensitive tool identity.  V2 admission authenticated
lookup `/usr/bin/cc` and canonical target `/usr/bin/gcc`, but replaced the
execution spelling with the target.  Runtime `gcc --version` therefore differed
from the producer's receipt-bound `cc --version` even though executable bytes
matched.  No build command ran and no product defect is inferred from this
observer failure.  Exact failure evidence is
`docs/verification/evidence/native-exact-mckernel-image-exportset17-failure-20260930.json`.

The one bounded correction retains the authenticated lookup spelling for
execution/version while continuing to hash and PATH-check its canonical target.
Literal container `/usr` paths stay literal; only fixture `/out` and `/nightly`
paths translate.  An argv0-sensitive symlink regression now returns `cc fake 1`
through the lookup and `cc-target fake 1` through the target, so the original
bug cannot pass.  Exportset-18 becomes active and exportset-17 is retired.
All 81 combined tests, the focused regression, `py_compile` and diff-check pass.
Corrected driver/owner/test SHAs are `c7d8956f...04fa`,
`08e336b3...be33`, `0d3c2350...ade7` and `bd8b2e7f...817a`.
Independent review returns `PASS_SOURCE_CORRECTION`.

Next commit/push/fetch-verify these exact source bytes, create fresh exportset-18
packet/work/evidence roots while preserving every exportset-17 artifact, obtain
new packet and execution review, and run at most one corrected image attempt.
Real current diagnostic guest applications remain zero and no acceptance bar
moves.

Continuation checkpoint 233, 2026-09-30: fresh exportset-18 is prepared and
released for the one bounded image-tool correction attempt.  Its 80,765,577-
byte toolchain remains byte-identical at SHA `471ed7e3...9d72`, while the fresh
43,891,119-byte request is `ee41103c...643a` and binds corrected driver
`c7d8956f...04fa`, owner `08e336b3...be33`, the active exportset-18 exclusion
and entirely fresh roots.  Toolchain/request identities are
`1831:1712448`/`1831:1712450`; fresh empty mode0700 work/owner-evidence roots
are `1831:1712445`/`1831:1712446`.

Actual read-only owner validation passes again over 140,053 `/out`, 35,973
nightly, 18,924 kernel and 86 backup entries.  Independent results are
`PASS_SOURCE_CORRECTION`, `PASS_PACKET`, capacity `GO` and
`PASS_EXECUTION_CORRECTION` for exactly the command in
`docs/verification/evidence/native-exact-mckernel-image-exportset18-release-20260930.json`.
Review confirms the correction retains `/usr/bin/cc` for version, `CC` and
CMake compiler arguments while canonical `/usr/bin/gcc` remains hash- and
PATH-authenticated.  Exportset-17 remains immutable and retired.

Host/scratch free bytes are 19,717,570,560/15,246,770,176 and MemAvailable is
30,018,060KiB.  The fresh output/evidence/attempt/lease/exclusion targets are
absent and no heavy owner is live.  Next remeasure immediately and run the one
released corrected attempt with the unchanged isolation profile.  Preserve any
new failure without retry.  Real current diagnostic guest applications remain
zero and no acceptance bar moves.

Continuation checkpoint 231, 2026-09-30: actual exportset-17 preparation now
passes against the retained scratch12 build and the source-free attempt3 tool
image.  The atomically published toolchain manifest is 80,765,577 bytes at
SHA `471ed7e3...9d72` and identity `1831:1712398`; the request is 43,891,119
bytes at SHA `36abddef...488` and identity `1831:1712400`.  Both are mode0600.
The packet binds 140,053 `/out` closure entries, 35,973 nightly entries, 18,924
kernel entries and 86 backup entries to candidate `4e99a82c...af7a1`, IHK
`3114d9e7...2a1f`, image `sha256:5315d343...7080`, receipt
`1ea38c33...af08` and lock `fd3d7a13...e6c802`.

Independent packet audit returns `PASS_PACKET` after a real read-only
`ImageOwner.validate()`.  Independent execution review returns
`PASS_EXECUTION` for exactly one serialized command recorded in
`docs/verification/evidence/native-exact-mckernel-image-exportset17-release-20260930.json`.
It independently checks all 92 tool-image evidence files and the exact v2
mount/resource boundary: CPUs2-5, four jobs, 12GiB/no swap expansion, 512 PIDs,
network none, private IPC, caller uid/gid, read-only root, cap-drop ALL,
no-new-privileges, `/work` as the sole writable bind and bounded `/tmp` tmpfs.

Fresh output/evidence/attempt/lease/common-exclusion targets remain absent;
work and owner-evidence roots are empty mode0700 at identities
`1831:1704202`/`1831:1704601`.  Host/scratch free bytes are
19,862,888,448/15,371,608,064 and MemAvailable is 30,057,872KiB.  No heavy
owner, QEMU or mcexec is live.

Next remeasure the same floors immediately before start, run the one released
image-owner command, preserve its complete receipt/logs/container retirement,
and do not retry automatically on failure.  If it passes, independently review
the exact `mckernel.img`, then bind it into a fresh strict memory diagnostic
packet/release.  Real current diagnostic guest applications remain zero and no
acceptance bar moves.

Continuation checkpoint 234, 2026-09-30: the one released exportset-18
bounded correction attempt terminated safely and is preserved as a configure
failure.  Identity checks now pass and CMake starts, proving the exportset-17
`cc` lookup-spelling correction.  Its kernel-module probe then uses GCC 14.3.1
against the retained host kernel tree built by Clang 21.1.8; GCC rejects
`-mretpoline-external-thunk`.  Configuration subsequently reports `error:
couldn't find libnuma`.  Exactly one CMake command ran and no `mckernel.img`
was produced.

Driver receipt `dd5c53b9...8272` records status FAIL, phase `configure`; owner
receipt `79297720...558c` preserves owner PID/starttime
`1634914/100793649`, container `a6e3772f...cb0ae` and nonce
`db5dfd5b...a42ed`.  Terminal state is exited1/PID0/OOMfalse, retirement is
proven, the lease is absent, and both the container and complete scratch
evidence remain retained.  Consumed exportset-18 exclusion
`d8c94e1b...3216` is preserved.  Exact hashes and paths are recorded in
`docs/verification/evidence/native-exact-mckernel-image-exportset18-failure-20260930.json`.

This is the bounded corrected attempt for the current-image build-contract
family.  Do not repeat it unchanged.  Next obtain expert source/toolchain review
of the Clang-built kernel compiler contract and sealed `libnuma` availability,
then implement one reviewed correction with cheap regression coverage before a
fresh packet and heavy attempt.  The strict memory diagnostic remains frozen
at stdout `NATIVE_CORE PASS memory\n`, empty stderr and exit 37/raw wait 9472,
but cannot be rebound until a current `mckernel.img` exists.  Real current
diagnostic guest applications remain zero; this diagnostic build failure moves
no acceptance bar.

Shutdown checkpoint: no image owner, QEMU or mcexec process remains.  The
launcher wrapper/launcher/worker/server identities are respectively
`1442141/1442142/1442145/1442149`, all started 2026-09-30 10:46:42 PDT and
left untouched for the launcher-controlled pause.  All child agents are
completed.  Host/scratch free bytes are 19,711,766,528/15,243,829,248 and
MemAvailable is 30,018,120 KiB.

Continuation shutdown checkpoint 235, 2026-09-30: expert inventory and
toolchain-contract work identifies exportset-18's configure failure precisely.
The retained host kernel is a Clang/LLD 21 build (`LLVM=1` and
`CONFIG_CC_IS_CLANG=y`); invoking its external-module probe with GCC caused the
`-mretpoline-external-thunk` rejection.  The source-free image also lacked the
required numactl development closure and its export manifest omitted the Clang
identity.  This is a build-contract defect, not a kernel flag to suppress.

The bounded source repair now seals Clang, LLD and exact libnuma/libbfd/
libiberty/libudev roles, passes the matching compiler/linker into Kbuild, and
requires an independently decoded ELF64 little-endian x86-64 `REL` probe with
a unique initialized `.data` `MAP_KERNEL_START`.  It compares that value with
the generated linker script, `flags.make` and `compile_commands`, rejects all
conflicting/malformed/empty/undefined definitions, and rejects probe stderr.
Coordinator reproduction passes `py_compile`, all 105 focused tests and
`git diff --check`.  Exact source/test hashes and the review history are in
`docs/verification/evidence/native-exact-mckernel-image-configure-repair-source-20260930.json`.

This is source-only progress.  The earlier final source review blocked on the
macro-override, ELF type and stderr gaps; the bounded correction and negative
tests close those reported cases, but shutdown prohibited dispatching a fresh
independent final review.  No Docker preparation, build or guest ran.  The
top-level CMake nested-make status defect also remains a deliberate follow-up
for a future source candidate because changing it now would invalidate the
retained exact candidate and require a complete host-kernel rebuild.

Next independently review the eight exact final hashes in that evidence file.
Only after `PASS_SOURCE`, prepare a fresh source-free image-tool image and
packet with the corrected package closure, obtain fresh packet/execution
review, and run one serialized configure/build attempt.  Authenticate the
resulting smallest current `mckernel.img` before the frozen memory diagnostic,
then files, threads/futexes, signals and shutdown.  Preserve exportsets 17 and
18 and all original failures; do not repeat either unchanged.  Current-
candidate builds remain six failed and one completed, and real current
diagnostic guest applications remain zero.

Shutdown state: all eight child agents are completed.  No image owner, QEMU or
mcexec is live.  Launcher wrapper/launcher/worker/server identities remain
`1442141/1442142/1442145/1442149`, each started 2026-09-30 10:46:42 PDT and
left untouched for the launcher-controlled pause.  Host/scratch free bytes are
19,196,985,344/15,243,829,248 and MemAvailable is 29,881,408 KiB.  The OS goal
remains incomplete and is not resumed or completed by this checkpoint.

Continuation checkpoint 236, 2026-09-30: the current-image configure repair is
now independently `PASS_SOURCE_FINAL`.  Expert correction closes every reported
protected-macro bypass: function-like and malformed spellings, complementary
rows, missing definitions, dual representation inconsistencies, empty/malformed
rows and absent native-kernel consumers all reject.  The complete four-suite
coordinator run passes 108 tests.  Final driver SHA is `417175f7...de3dc`;
owner `7de99b72...0c6637` pins it, advances the sole active namespace to
exportset-22 and rejects retired exportsets 18 through 21.  Owner/request tests
pass 53/53 and both the driver and namespace bindings have independent source
PASS decisions.  This remains source evidence, not runtime acceptance.

The first fresh tool-image run, attempt4, failed safely during networked package
installation: Rocky's minimal base already contains `coreutils-single`, and the
requested full `coreutils` conflicted.  Its exact DNF streams/status and receipt
are retained in
`docs/verification/evidence/native-exact-tool-image-attempt4-failure-20260930.json`.
Container `506c390e...79d5` is exited/PID0/OOMfalse and retained; its lease is
absent.  The one bounded correction authenticates `coreutils-single` as the
package and `/usr/bin/dd` owner; 21 tests and independent source/execution review
PASS.

Released attempt5 then passes.  Image `sha256:58da6415...4346`, receipt
`329811a1...445ce`, 46 packages, 22 tools, four exact library/header groups and
479 RPM inventory entries are independently verified.  Online and offline
observations are byte-identical at `f3b88a58...9cbc0`; both containers retired,
were removed, and the lease is absent.  Exact result evidence is
`docs/verification/evidence/native-exact-tool-image-attempt5-success-20260930.json`.
This accepts only the source-free tool image.

Data-only exportsets 19, 20 and 21 each failed closed before final publication,
respectively on the stale driver pin, the 16-GiB host floor, and the stale active
exclusion namespace.  Their fresh inputs/empty roots are retained and their
names retired.  Exportset-22 now prepares successfully: toolchain
`6f653072...a26d` (80,770,489 bytes), request `7a9c1c52...4c60`
(43,891,119 bytes), work identity `1831:1720079` and owner-evidence identity
`1831:1720080`; both roots are empty mode0700 and lease/exclusion are absent.
The complete binding is
`docs/verification/evidence/native-exact-mckernel-image-exportset22-preparation-20260930.json`.

To restore the immutable host floor without deleting evidence, three
unreferenced temporary repository/test copies (35,449,874 bytes) were moved from
`/tmp` to scratch preservation root
`/home/holden/mckernel-work/scratch/host-temp-preserved-20260930-1`.  One
unreferenced generated export18 summary and three local test logs were removed;
all are reproducible and no retained failure, image, container, receipt or input
was removed.  Current pre-review host/scratch free bytes are
17,310,855,168/15,078,977,536 and MemAvailable is 30,145,724 KiB.

Next obtain exact `PASS_PACKET` and `PASS_EXECUTION_EXPORTSET22`, checkpoint and
fetch-verify these source bytes, remeasure the narrow capacity margin, then run
at most one serialized build.  On an authenticated `mckernel.img`, rebind the
strict memory diagnostic (stdout `NATIVE_CORE PASS memory\n`, empty stderr,
exit37/raw9472), followed by files, threads/futexes, signals and shutdown.  Real
current diagnostic guest applications remain zero; no production/application
acceptance counter moves.

Independent packet rereview now returns `PASS_PACKET`: the sole initial concern
was resolved by the owner contract itself—the active exclusion must be absent so
`run()` can acquire it atomically with `O_CREAT|O_EXCL`; preexistence is the
rejection case.  Independent execution review returns
`PASS_EXECUTION_EXPORTSET22` for exactly one invocation of
`python3 -I -B scripts/native_rust_exact_mckernel_image_container_owner.py`
with request `7a9c1c52...4c60`.  It verifies the single heavy lease, exclusion,
read-only input mounts, CPUs2-5/four CPUs, 12GiB/equal swap, 512 PIDs, no
network, private IPC, caller uid/gid, cap-drop ALL, no-new-privileges,
read-only root, sole writable `/work`, bounded `/tmp`, timeout, capture and
terminal retirement paths.  No reviewer ran Docker or a build.

This exact source/packet checkpoint must be committed, pushed and fetched before
the released invocation.  Immediately before it, recheck the 16-GiB host and
12-GiB scratch floors: the last independent host observation was only
128,393,216 bytes above its floor.  Any admission failure is preserved and not
bypassed.  No guest may overlap the build.

Shutdown checkpoint 241, 2026-09-30: the fetched exportset-22 checkpoint was
executed exactly once under its independent release.  Admission passed at
17,304,039,424 host bytes, 15,078,907,904 scratch bytes and 30,615,584,768
available-memory bytes.  The reviewed four-CPU/12-GiB/no-network container ran
for about one minute and failed safely in its single CMake configure command.
The repaired Clang/LLD external-module probe and the libnuma probe now pass.
Configure instead found that the candidate records its required nested
libdwarf gitlink but does not materialize its source, so `libdwarf.h.in` and
`config.h.in.cmake` are absent.  This is new failure evidence and exportset-22
must not be repeated unchanged.

The complete record is
`docs/verification/evidence/native-exact-mckernel-image-exportset22-failure-20260930.json`.
Owner receipt `6f35ae64...c0255`, driver receipt `36a7cf06...ad9`, stderr
`fa96d87c...a91f` and provenance `4f3b206e...d5ab` remain in their original
scratch roots.  Container `4dc6377e...2707` / name
`mckernel-image-d6f5a553c80b41c48f52ec26afb90439` is retained exited, PID0,
exit1 and not OOM-killed; the heavy lease is absent and the exportset-22 common
exclusion remains present.  No image artifact or guest was produced.

Three bounded investigations agree on the defect.  The source gitlink is exact
commit `ab9230b2b8aa66a3d1d52e4be11fca17a3b63753`; the current checkout has its
clean complete 412-file object closure, while scratch candidate 12 has an empty
nested directory.  The two required templates hash to `727cd79f...527c` and
`58ffc3c9...c68`.  Top-level CMake requires DWARF for `mcinspect`; do not disable
that production surface or vendor-copy unauthenticated bytes.  The expert
confirmed that merely populating the directory under the present manifest
would leave consumed bytes unauthenticated, then was interrupted for shutdown.

Next design an additive exact-gitlink dependency closure which binds the clean
local libdwarf commit and every consumed byte while preserving the retained
host-kernel output.  Obtain independent source and execution review, advance to
a fresh owner/exclusion namespace, checkpoint, then run one corrected build.
After an authenticated smallest `mckernel.img`, run the frozen real memory
diagnostic, then files, threads/futexes, signals and shutdown, labeling these
diagnostic rather than acceptance results.  Current-candidate builds gain no
success and real current diagnostic guest applications remain zero.

Shutdown state: all child agents are completed or closed; no QEMU or mcexec is
live.  The retained failed container above is the only active process identity
requiring later cleanup reconciliation.  Launcher wrapper/launcher/worker/
server identities remain `1442141/1442142/1442145/1442149`, all started
2026-09-30 10:46:42 PDT and left untouched.  Host/scratch free bytes are
17,285,165,056/15,074,672,640 and MemAvailable is 29,990,784 KiB.  The OS goal
remains incomplete and is not resumed or completed by this shutdown.

Continuation checkpoint 244, 2026-09-30: exportset-22's missing bundled
libdwarf source is repaired at the image-input boundary without mutating
scratch candidate 12 or rebuilding its authenticated host kernel/modules.  A
fresh no-network helper creates a non-shared local checkout of exact gitlink
`ab9230b2b8aa66a3d1d52e4be11fca17a3b63753` / tree
`dcc29777813bf8625dce8bfb239c225d5535d668`.  Its supplemental manifest binds
the unchanged candidate/IHK/base manifest, all 412 tracked file paths, Git
modes, raw unfiltered blob identities, SHA-256 bytes and all 21 self-contained
Git metadata files.  Owner and offline driver validate that closure before and
after work, including failure paths, and mount the separate root read-only at
the exact nested `/src` gitlink path.  System libdwarf-devel was rejected as an
unnecessary dependency-profile change.

The initial implementation review blocked checkout stderr handling, inherited
Git controls, abbreviated identities, external metadata/object stores,
incomplete index/tree checks, filtered hash-object behavior and missing failure
revalidation.  All are closed.  The complete five-suite run passes 100 tests
in 36.157 seconds; its log hashes to `743bdab0...d5e8`.  The adversarial suite
includes the former `core.autocrlf` plus skip-worktree raw-byte bypass.
Independent rereview returns `PASS_SOURCE_CORRECTION`; namespace rereview
returns `PASS_SOURCE_NAMESPACE`.  Exact hashes and the additive correction to
the earlier transcribed template hash are retained in
`docs/verification/evidence/native-exact-mckernel-image-libdwarf-source-20260930.json`.

Exportset-23 is prepared and independently `PASS_PACKET_EXPORTSET23` plus
`PASS_EXECUTION_EXPORTSET23` for one serialized owner invocation.  Request
`6a62fd97...b1305` binds unchanged toolchain `6f653072...a26d`, supplemental
manifest `de08d8c...5309`, current owner `a30ec8cc...8095`, current driver
`fa3ea29e...2bd8`, and the attempt5 tool image.  Independent audit verifies
all 132,191 retained host-output entries with zero mismatches.  Work and owner
evidence roots remain empty mode0700, and lease/exclusion are absent.  Exact
packet identities and profile are recorded in
`docs/verification/evidence/native-exact-mckernel-image-exportset23-preparation-20260930.json`.

Six disposable helper regression roots totaling 243 MiB were removed after
their expected failures/successes; targeted scratch trim returned their sparse
blocks and additional old free blocks to the host.  No retained evidence was
removed.  Current host/scratch free bytes are
17,562,431,488/14,907,523,072 and MemAvailable is 29,755,780 KiB.  Next commit,
push and fetch-verify these exact bytes, remeasure capacity, and invoke the
exportset-23 owner exactly once.  On an authenticated `mckernel.img`, prepare
fresh current-image diagnostic packets in serial startup, memory, files,
threads/futexes, signals and separately reviewed shutdown order.  Old frozen
diagnostic packets bind a different image and must not be reused.  No build or
guest acceptance counter moves at this source/packet checkpoint.

Continuation checkpoint 249, 2026-09-30: exportset-23 executed exactly once
and closed the bundled-libdwarf configure blocker, but the subsequent Rust
kernel compilation failed.  CMake configure exited 0 and produced the exact
`MODULES_END` probe.  `mckernel.img -j4` exited 2 under the packet's
authenticated but obsolete `rustc 1.60.0-nightly`; its 3,898 diagnostics are
dominated by unsupported current-language surfaces (`offset_of!`, let-else,
raw-address syntax and C-string literals), rather than a demonstrated lifetime
defect.  Owner container `4f2b721b...e8fb3`, name
`mckernel-image-15024d3e89c64409b2146ecc9d969645`, nonce
`385793b1...54fab`, is retained exited/PID0/exit1/OOMfalse.  Its lease is absent
and exportset-23's consumed exclusion remains.  Original receipt, stderr and
provenance hashes are bound in
`docs/verification/evidence/native-exact-mckernel-image-exportset23-failure-20260930.json`.
No linked current image or guest resulted, and exportset-23 must not be repeated.

The single bounded correction binds exact historical production compiler
`rustc 1.95.0-nightly (c04308580 2026-02-18)`, commit
`c043085801b7a884054add21a94882216df5971c`, LLVM 22.1.0 and matching rust-src.
The retained no-symlink closure contains 2,465 files; rustc hashes to
`70ebcbba...54e09`.  Owner/preparer now reject every other compiler identity
for v1/v2, require request/manifest equality, and revalidate the complete
mounted closure after admission and on terminal paths.  Combined owner/request
tests pass 58/58 with log `08879d0e...895f4`; independent rereview returns
`PASS_SOURCE_TOOLCHAIN`.  A one-CPU, 600-second-bounded compile of the exact
current candidate Rust crate with the generated no-redzone/no-vectorization/
SSE-AVX-disabled command exits 0 in 17.3 seconds, empty stdout, 37 retained
warnings, and object `8ecb2043...ba004` (12,589,664 bytes).  This is compile
compatibility evidence only, not a linked-image or runtime result.

Fresh exportset-24 is prepared.  Inputs `a52770e8...e0915`, toolchain
`de4bcafc...1cf83` and request `cdfbbf6b...c54c` bind the exact compiler,
unchanged 132,191-entry retained host output, exact libdwarf closure, current
owner `e03793c9...6bb6`, driver `fa3ea29e...62bd8` and attempt5 tool image.
Work/owner roots are empty mode0700 at `1831:1721231` and `1831:1721232`;
lease, exclusion and driver children are absent as required before atomic
acquisition.  Independent decisions are `PASS_PACKET_EXPORTSET24` and
`PASS_EXECUTION_EXPORTSET24` for exactly one serialized invocation after this
checkpoint is pushed and fetched.  Exact preparation evidence is
`docs/verification/evidence/native-exact-mckernel-image-rust195-exportset24-preparation-20260930.json`.

Toolchain preparation temporarily crossed the 16-GiB host floor.  A wrong-date
Rust closure plus duplicate exact closure (1,338,163,200 bytes) was recorded and
removed while retaining the exact required closure; scratch trim discarded
1,751,281,664 bytes.  System journal vacuum removed 1,632 MiB of archived
segments while preserving 2.3 GiB current/recent journal data; those removed
journals are not recoverable.  Post-preparation host/scratch free bytes are
17,931,227,136/14,100,279,296 and MemAvailable is 30,375,432,192 bytes, above
the enforced 16/12/16-GiB floors.  The exact closure/removal record is
`docs/verification/evidence/native-exact-rust-nightly-closure-preparation-20260930.json`.

Next commit, push and fetch-verify this exact source/packet checkpoint, then
remeasure capacity and invoke exportset-24 exactly once.  On a linked image,
authenticate artifact/symbol/no-SIMD evidence and prepare fresh independently
reviewed diagnostic packets in startup, memory, files, threads/futexes, signals
and shutdown order.  Diagnostic outputs remain separate from acceptance.  The
current cursor has eight failed and one completed current-candidate build
records, zero linked smallest-current `mckernel.img` artifacts, one exact
current-crate compile, and zero real current-image diagnostic guest apps.
Launcher wrapper/launcher/worker/server remain
`1442141/1442142/1442145/1442149`, all started 2026-09-30 10:46:42 PDT; no
QEMU, mcexec or image owner is live.

Continuation checkpoint 250, 2026-09-30: exportset-24 ran exactly once after
its fetched checkpoint.  The exact Rust 1.95 correction worked: configure
passed, the current Rust crate and all C/assembly objects compiled, and the
build reached the final image link.  The raw `/usr/bin/ld` command then
rejected CMake 3.31.8's compiler-driver spelling
`-Wl,--dependency-file=CMakeFiles/mckernel.img.dir/link.d`; build exit is 2.
The actual Rust object is 12,587,464 bytes and hashes to `c32ff593...23e2`,
but no `mckernel.img` was linked and no guest ran.  The original receipts,
logs, command and partial-object hashes are retained in
`docs/verification/evidence/native-exact-mckernel-image-exportset24-failure-20260930.json`.
Container `053b5528...d24f`, name
`mckernel-image-69d5302ef1b74816aec831cf959404ee`, nonce
`09c96c3b...5b751`, is retained exited/PID0/exit1/OOMfalse; its lease is
absent and exportset-24's exclusion is consumed.  Do not retry it unchanged.

Independent final-link review confirms `kernel/CMakeLists.txt` deliberately
uses raw `ld` while CMake's GNU compiler module wrapped the injected linker
depfile option for a compiler driver.  The next bounded correction is
directory-local empty `CMAKE_C_LINKER_WRAPPER_FLAG` and
`CMAKE_C_LINKER_WRAPPER_FLAG_SEP`, preserving dependency generation.  Before
exportset-25, reproduce the old rejected command, prove the corrected raw
`--dependency-file` spelling creates a depfile and relinks on linker-script
change, prove compiler-driven sibling targets retain wrapping, and compare
Rust/fallback object sets plus entry/script/map/no-CRT options.  An interrupted
worker's incomplete alternate depfile-disabling edit and placeholder were
discarded; source remains at the fetched `3acdc449` checkpoint.

Shutdown handoff: all child agents are completed or closed and no new task was
dispatched after the stop request.  No QEMU, mcexec, image owner or heavy build
is live.  Launcher wrapper/launcher/worker/server identities remain
`1442141/1442142/1442145/1442149`, started 2026-09-30 10:46:42 PDT; the active
agent-log follower PID `1970570`, started 2026-09-30 15:07:57 PDT, exited while
the interrupted child lane closed and is no longer live.  Current
host/scratch free bytes are 17,674,272,768/14,079,119,360 and MemAvailable is
30,176,075,776 bytes.  The cursor now has nine failed and one completed
current-candidate build records, zero linked smallest-current images, one exact
current-crate compile and zero real current-image diagnostic guest apps.  The
OS goal remains incomplete and is neither resumed nor completed by shutdown.

Continuation checkpoint 251, 2026-09-30: shutdown resumed from the prior
exportset-24 failure checkpoint only long enough to join the two already active
bounded source lanes, preserve their bytes, and checkpoint them.  No new task
was dispatched after the stop request.  Every child is now completed.  No
QEMU, mcexec, image owner or heavy build is live, and the heavy lease is
absent.  The retained exportset-24 failure container remains exited/PID0/exit1/
OOMfalse with exact ID `053b5528...d24f` and name
`mckernel-image-69d5302ef1b74816aec831cf959404ee`.

The bounded final-link correction sets the C linker-wrapper flag and separator
empty only in `kernel/`, allowing the existing raw-ld rule to receive CMake's
bare dependency option while compiler-driven sibling targets retain wrapping.
Its exact source/test hashes are `0fb85281...f616e35` and
`969f6e05...02651`; independent review is PASS.  Retained host CMake 3.25.1
and exact-image CMake 3.31.8 regressions each pass 1/1.  The hardened
exportset-25 driver `d236409d...c9974` now binds the final raw-link inputs and
revalidates them after image inspection.  Owner `67923ab7...a7047a` pins it,
advances to exportset-25 and retires exportset-24.  The combined owner/offline
suite passes 61/61, but the correction landed after the last independent BLOCK
review: a fresh independent review remains mandatory before execution.

The candidate-12 storage helper was narrowed to a read-only audit-plan
generator after the prior apply-capable design was blocked.  Exact helper/test
hashes are `f4a49c1e...9cbf15` and `ef73db77...c1a450`; 11/11 focused tests,
Python compilation and diff checks pass.  It has no apply, deletion, Docker
mutation, build or guest path, and it has not been run against the candidate.
A fresh independent review is still required before its read-only inventory.
No candidate file was removed.  One bounded system-journal vacuum preceding
shutdown removed approximately 408 MiB of archived journal segments and left
about 1.9 GiB of journal data; those archived segments are not recoverable.

Exact source, checks, failure identity, resource readings, review state and
next tasks are recorded in
`docs/verification/evidence/native-exact-exportset25-link-contract-shutdown-20260930.json`.
At shutdown, host/scratch free bytes are
17,564,483,584/14,079,066,112 and MemAvailable is 29,857,984,512 bytes.
Launcher wrapper/launcher/worker/server identities remain
`1442141/1442142/1442145/1442149`, all started 2026-09-30 10:46:42 PDT.
The cursor remains nine failed plus one completed current-candidate build
records, zero linked smallest-current images, one exact current-crate compile,
and zero real current-image diagnostic guest apps.

Next continuation must first independently rereview both corrected source
packets.  After a fetched checkpoint and PASS, run only the read-only candidate
inventory to a fresh external plan path.  Review that actual plan, then create
and separately review a new plan-bound deletion program before removing any
duplicate evidence.  Remeasure the 16/12/16-GiB floors, prepare a fresh
scratch-13/exportset-25 packet, and run one serialized smallest-current image
build.  Only after artifact validation, prepare fresh startup, memory, files,
threads/futexes, signals and separately reviewed shutdown diagnostic packets.
Diagnostic output remains distinct from application or production acceptance.
The OS goal remains incomplete and is neither resumed nor completed during
this shutdown.

Continuation checkpoint 252, 2026-09-30: the stop request arrived after the
bounded cleanup correction completed.  No new work was dispatched.  All child
agents are completed, no QEMU, mcexec, image owner or heavy build is live, and
no candidate file was removed.  Launcher wrapper/launcher/worker/server remain
`1442141/1442142/1442145/1442149`, all started 2026-09-30 10:46:42 PDT.  The
two retained containers remain terminal: exportset-24 is
`053b5528...d24f`, exited/PID0/exit1/OOMfalse; the retained completed host
build is `4d15b349...e4f86`, exited/PID0/exit0/OOMfalse.

Independent final-link review now passes the exact exportset-25 source packet.
The offline driver/owner hashes are `91aa047f...7f4cc` and
`a6d6ffaa...f7f0`; their tests are `3c2891f6...1653` and
`17481bea...a0aef`.  The retained combined suite is 66/66 PASS.  This is
source integration and packet preparation only; exportset-25 has no execution
release and did not run.  Independent diagnostic review also passes the new
post-link checker `c22255b2...2731` and tests `cb154873...c0c9`; its retained
full suite is 181/181 PASS.  Actual current-image invocation and its separate
ownership check remain mandatory.

The candidate-12 read-only audit plan passes and identifies 2,507 exact
committed duplicate files occupying 9,102,798,848 allocated bytes, with no
protected overlap.  The plan-bound cleanup correction now hashes to
`61b83992...4c7e`, its tests hash to `6ddb4aa0...1224`, and its worker suite
passes 51/51.  Because shutdown arrived before independent rereview, that
corrected source is explicitly pending review.  It has no execution release;
the plan remains unapplied and files removed remain zero.

The exact retained Rocky bzImage/module tuple independently passes same-byte
diagnostic reuse review, and retained mcexec `ee1f660b...073b` contains the
matching IHK build ID `3114d9e`.  A fresh manifest and independently released
guest packet remain required.  Host/scratch free bytes at shutdown are
31,104,782,336/17,105,330,176 and MemAvailable is 29,261,602,816 bytes.  The
cursor remains nine failed plus one completed current-candidate build records,
zero linked smallest-current images, one exact current-crate compile and zero
real current-image diagnostic guest apps.  Full identities and next actions
are retained in
`docs/verification/evidence/native-exact-export25-postlink-cleanup-shutdown-20260930.json`.

Next continuation must first independently rereview the cleanup correction.
Only after a separately committed, reviewed and fetched execution release may
it run once.  Then trim scratch, prepare fresh scratch-13/exportset-25 inputs,
run one serialized image build, validate the actual linked artifact, and bind
the retained runtime tuple into fresh startup, memory, files, threads/futexes,
signals and shutdown diagnostic packets.  Diagnostic output remains distinct
from acceptance.  The OS goal remains incomplete and is neither resumed nor
completed during this shutdown.

Continuation checkpoint 253, 2026-09-30: the candidate-12 plan-bound cleanup
source now independently passes final source integration review.  Tool/test
hashes are `43afae37...fff9` and `3a683af7...c36a`; all 59 focused tests pass.
Eight new end-to-end disposable cases prove truthful staged, partial-delete,
complete-delete, quarantine/root descriptor-unwind, post-return and
pre-initialization states.  The exact read-only validation command also passes
against plan `eaba225b...f957`.  Earlier exact subtree, second-census, two
terminal-container and rename-reconciliation corrections remain intact.

This is source evidence only.  The cleanup still has no execution release, has
not run, and removed zero candidate files.  Exact review evidence is
`docs/verification/evidence/native-exact-candidate12-planbound-cleanup-source-review-20260930.json`.
Next checkpoint this source, fetch-verify it, author and independently review a
separate one-shot release, then remeasure capacity before executing exactly
once.  The OS goal remains incomplete; no diagnostic, application or
production acceptance changes here.

Continuation checkpoint 254, 2026-09-30: exact cleanup release 1 hashes to
`2dd558b7...e09` and independently passes precommit execution-release review.
It binds fetched source `fd4de5b1...1069`, tool `43afae37...fff9`/blob
`f0ff65c7...e3ef9`, plan `eaba225b...f957`, all 2,507 targets, four fresh
outputs, both absent leases, dispatcher exclusivity and both exact terminal
containers.  Fresh read-only Docker observation matches all sixteen retained
mount tuples and terminal states.  Cleanup still has not run; the release only
authorizes one invocation after its exact descendant commit is pushed, fetched
and commit-bound.

Fresh scratch-13 preparation source also independently passes.  Packet/test
hashes are `3694e530...328d` and `750ba961...d45e`; 43/43 tests pass.  It
authenticates and preserves consumed exportset-16 evidence, explicitly marks
the generated host-build request non-executable, and requires fresh
exportset-25 absence.  Candidate preparation, Docker and build did not run.
Exact combined review evidence is
`docs/verification/evidence/native-exact-candidate12-cleanup-release-and-scratch13-preparation-review-20260930.json`.

Next push/fetch this exact release, obtain final commit-bound confirmation and
execute cleanup once.  On a PASS receipt, verify restoration metadata, trim
scratch, remeasure the 16/12/16-GiB floors, then separately release and run the
scratch-13 preparation packet.  No acceptance bar changes at this source-only
checkpoint; the OS goal remains incomplete.

Continuation checkpoint 255, 2026-09-30: candidate-12 cleanup attempt 1 ran
once from fetched release `e6390a03...6c78` and failed closed during preflight
with `container-intersection`.  No target was staged or deleted: the receipt
records all 2,507 states `original`, no delete intent, no quarantine and zero
removed files.  The immutable receipt/journal/status hashes are
`c0480b1d...825d`/`39a9b195...3f23e`/`6d01b09e...9fee`.

The census found 41 stopped/retained containers and exactly six candidate-root
intersections.  Release 1 bound exportset-24 plus the retained host build but
omitted stopped exportsets 17, 18, 22 and 23.  Their exact owner receipts,
terminal states, owner nonces and mount tuples are retained.  Because this is a
repeat of the container-allowlist failure family, expert escalation requires a
single explicit six-ID inventory, proof-kind generalization, owner-nonce and
restart-count checks, and exact intersection-set equality.  Attempt 1 must not
be retried unchanged.  Exact failure evidence is
`docs/verification/evidence/native-exact-candidate12-planbound-cleanup-attempt1-failure-20260930.json`.

Next independently review the coherent six-container correction, checkpoint
it, then author a fresh release with new output paths.  Cleanup remains
incomplete; scratch-13 preparation and the current image build remain pending.
No diagnostic or acceptance result changes.

Continuation checkpoint 256, 2026-09-30: the expert-escalated six-container
cleanup correction independently passes source integration review.  Exact
tool/test hashes are `dcb2a0d6...b712` and `f543d60e...600a`; 69/69 tests pass.
A fresh read-only live census passes with 41 total containers and exactly six
candidate intersections.  The tool now binds all five image owner receipts and
the host Docker inspection by explicit proof kind, including exact ID, name,
owner nonce, restart count, complete terminal state and complete unordered
mount rows.  Unknown, missing or drifting intersections fail at initial,
post-staging and final censuses.

All earlier subtree, Git identity, protected-path, second-admission,
no-replace staging, rollback and truthful unwind protections remain.  Attempt
1 journal `39a9b195...3f23e` is unchanged.  Exact source-review evidence is
`docs/verification/evidence/native-exact-candidate12-six-container-cleanup-source-review-20260930.json`.
This is not an execution release; the corrected cleanup has not run.  Next
checkpoint/fetch this source and author a new release with fresh attempt-2
outputs.  The OS goal and current image/runtime work remain incomplete.

Continuation checkpoint 257, 2026-09-30: cleanup release 2 independently
passes precommit execution review.  Exact release SHA is
`b2a601c0...3eec`; it binds fetched source `93cc9559...d130`, corrected tool
`dcb2a0d6...b712`/blob `32f08267...602c`, plan `eaba225b...f957`, the
explicit six-container inventory and entirely fresh attempt-2 outputs.  The
complete sanitized read-only census `49ef2f4d...e8be` contains all 41 container
records and independently yields exactly six candidate intersections with
zero unknown intersections.  All six proof files, 50 mount tuples, nonces,
restart counts and complete terminal states match.

Attempt 1 evidence remains byte-identical and proves it stopped before staging.
Host/scratch free bytes are 31,006,511,104/17,102,430,208 and MemAvailable is
28,896,288 KiB, above floors.  Release 2 remains unexecuted until these exact
bytes are committed, pushed, fetched and finally commit-bound.  Next perform
that verification and invoke it once; do not reuse release 1.  No OS acceptance
or diagnostic result changes.

Continuation checkpoint 258, 2026-09-30: cleanup attempt 2 ran once from the
fetched release and failed closed at `staged-admission` with
`open-references-or-incomplete-census`.  All 2,507 plan files remain intact in
candidate-local quarantine `.planbound-cleanup-20260930-2`; the original
evidence directory contains zero files and no deletion was attempted.  The
journal/receipt/status hashes are `4749ea4d...d02`/`83d22b06...3c52`/
`b22762e6...9484a`.  Attempt 2 must not be retried or moved during shutdown.

The failure is in the observer, not the protected bytes: `lsof -w +D` returned
one while emitting only the cleanup process's exact root and quarantine
directory descriptors and empty stderr.  Without `-w`, lsof reports unrelated
inaccessible FUSE mounts.  Expert review requires a separate exact rename-back
recovery release, followed by a filesystem-scoped `lsof +f --` correction with
a pinned scratch witness, strict full-NUL parsing, canonical-path plus
device/inode classification, no-follow validation of outside-root records and
hard rejection of deleted, unknown, relative, escaped or aliased paths.  The
existing mount-device/no-alias and six-container checks remain mandatory.

Shutdown next tasks are therefore: independently implement and review the
exact 2,507-file rename-back packet; execute it only from a fresh fetched
release; then implement/test/review the observer correction and issue a new
cleanup release.  After cleanup succeeds, trim and remeasure capacity, release
scratch-13 preparation, build the smallest current image, and begin the
separately labelled diagnostic startup/memory/files/threads-futex/signals/
shutdown loop.  Exact failure evidence is
`docs/verification/evidence/native-exact-candidate12-planbound-cleanup-attempt2-failure-20260930.json`.

At shutdown, the preserved launcher identities are PIDs 1442141/1442142/
1442145/1442149 (wrapper/launcher/worker/app-server), all started 2026-09-30
10:46:42 PDT.  There is no build, QEMU, mcexec or guest process.  All child
lanes are quiesced.  The OS goal remains incomplete and is paused by the
launcher; it is neither resumed nor marked complete here.

Continuation checkpoint 259, 2026-09-30: the candidate-12 filesystem-wide
observer correction now independently passes source integration after the
required expert escalation.  Exact cleanup tool/test hashes are
`09f6d7a1...e1b28` and `a8abeb1f...f4073`; all 74 tests pass with no skips,
including a real unprivileged lsof 4.93.2 capture and 24 independent framing,
witness, PID/FD, access/type, alias and mount adversarial cases.  The exact
six-container, lease, release and transaction protections remain in place.
This is source evidence only: no privileged census or cleanup ran.

Three standalone rename-back recovery designs remain rejected.  Their supplied
5/7/11-test suites passed, but independent probes reproduced uncommitted or
self-referential release authority, intermediate-symlink destination escape,
incomplete namespace and metadata checks, missing operational exclusion,
output-parent substitution, truncated-evidence false PASS, signal/reconciliation
loss and—on the expert candidate—an immediate live `receipt-full-namespace`
refusal because the immutable attempt-2 receipt never contained invented
snapshot fields.  The final rejected source/test hashes are
`83b1e671...b6bd4`/`40f8c2d0...03d2f`; they are preserved but must never be
released or executed.  Exact failure history is in
`native-exact-candidate12-renameback-recovery-source-failures-20260930.json`.

The repair strategy changes now: extend the already reviewed cleanup
transaction with a dedicated staged-recovery mode, reusing its authenticated
plan and fetched-release contract, shared mutex, real live census, component
no-follow directory descriptors, `RENAME_NOREPLACE`, durable journal/publication
and per-row rollback reconciliation.  It must consume the exact immutable
attempt-2 journal/receipt/status and validate the current 2,507-entry staged
shape rather than require new fields in historical evidence.  Independently
review and checkpoint that source before authoring a fresh recovery release.

Two cheap readiness regressions also pass: 215 exportset-25 owner/postlink/
linked-text tests and 135 diagnostic owner/runner/backend/stager/shutdown tests.
They are infrastructure-only.  This continuation has executed zero real guest
applications and produced zero current-candidate builds; the exact blocker is
the staged candidate-12 recovery.  Live state remains 2,507 quarantined files,
zero originals and zero deletions with attempt hashes unchanged.  After safe
recovery: run the corrected cleanup once from a fresh release, trim/remeasure,
release scratch-13 preparation and the serialized current-image build, then run
the separately labelled startup/memory/files/threads-futex/signals/shutdown
diagnostic loop.  No formal acceptance counter changes.

Continuation checkpoint 260, 2026-09-30: shutdown stopped new dispatch and
completed only the already active bounded integrated-recovery correction.  The
exact tool/test hashes are `0afa98cd...ae83` and `7dc098d9...a341`; all 163
focused disposable tests pass, `py_compile` passes and `git diff --check`
passes.  The correction pins the complete destination hierarchy with retained
directory descriptors, uses those descriptors for rename/final verification/
reconciliation, adds a read-only `--validate-recovery` path and exact test
artifact release bindings, and demotes publication or terminal-signal failures
instead of reporting PASS.  Exact source-only WIP evidence is
`docs/verification/evidence/native-exact-candidate12-integrated-recovery-correction-wip-20260930.json`.

This is not an independent review or execution release.  No live recovery,
privileged census, Docker operation, build or guest ran.  The exact attempt-2
state remains 2,507 quarantined files, zero originals and zero deletions; its
journal/receipt/status hashes remain `4749ea4d...d02`/`83d22b06...3c52`/
`b22762e6...9484a`.  The preserved launcher identities remain PIDs
1442141/1442142/1442145/1442149 (wrapper/launcher/worker/app-server), started
2026-09-30 10:46:42 PDT.  There is no QEMU, mcexec, build or guest process.

Next continuation must first obtain a fresh independent source review against
the exact committed correction.  If it passes, author, checkpoint, push/fetch
verify and independently review a separate one-shot staged-recovery release;
run read-only recovery validation before any mutation, then execute at most
once.  After exact restoration, issue a fresh corrected-cleanup release, trim
and remeasure capacity, release scratch-13 preparation, build the smallest
current image, and run separately labelled startup/memory/files/threads-futex/
signals/shutdown diagnostics.  Diagnostic results remain distinct from formal
acceptance.  The OS goal is incomplete and remains launcher-paused during this
shutdown; it is neither resumed nor marked complete.

Continuation checkpoint 261, 2026-09-30: the escalated integrated staged-
recovery boundary independently passes source integration.  Exact tool/test
hashes are `a7a5766c...d0c2e` and `86a6b7dc...14e84`; all 182 disposable tests
pass under one CPU and 1.5 GiB, including actual SIGINT/SIGTERM in twelve
isolated CLI executions.  The accepted scope covers complete retained-FD lsof
declaration, destination/output namespace pinning, row reconciliation, held-
inode invalidation after permission/ownership drift, and one committed outcome
through output cleanup, mutex close, CLI delivery, stream flush and low-level
exit.  Exact evidence is
`docs/verification/evidence/native-exact-candidate12-integrated-recovery-source-success-20260930.json`.

Three earlier integrated candidates remain retained BLOCKs.  Their concrete
findings were publication false PASS and destination substitution; undeclared
destination FDs, output-parent replacement and late-signal divergence; then
terminal protection ending before cleanup/delivery and mutable metadata
preventing held-inode invalidation.  The accepted larger-boundary repair does
not convert those failures into passes.  Persistent I/O failure, SIGKILL, power
loss or malicious concurrent mutation still requires external reconciliation.

This is source-only evidence.  The exact live state remains 2,507 quarantined
files, zero originals and zero deletions, with attempt-2 journal/receipt/status
hashes `4749ea4d...d02`/`83d22b06...3c52`/`b22762e6...9484a`.  No privileged
census, Docker operation, build or guest ran.  Next fetch-verify this source
checkpoint, mechanically author the exact staged manifest and fresh one-shot
recovery release in a separate commit, independently review that execution
authority, run `--validate-recovery`, and only then execute once.  Successful
restoration unlocks a fresh corrected-cleanup release, scratch trim/capacity
measurement, rebound scratch-13 preparation, the serialized smallest-current
image build and separately labelled diagnostic applications.  No formal
acceptance counter changes here.

Continuation checkpoint 262, 2026-09-30: exact staged-recovery release
`4383b9c1...ca203` at fetched commit `8b6c1c11...e441` passed independent
execution review, then its single read-only validation and single recovery
invocation both passed.  The validation printed `RECOVERY_VALIDATION_PASS` and
the execution printed `RECOVERY_PASS`, both with exit zero.  No delete path was
entered.

Independent evidence review accepts all 5,019 journal records and all 2,507
restored files (9,096,966,061 bytes; 9,102,798,848 allocated bytes) against the
exact plan, including content, inode, mode, link, size, mtime and allocation.
The exact 100-directory evidence shape is restored.  The original quarantine
inode remains mode 0700 and empty; both leases are absent.  Journal/receipt/
status hashes are `d0765466...713a`/`92b51fe4...849f`/`5b3ebb13...e57f`.
Both initial and final censuses contain 115 complete lsof records, 41 stable
containers and exactly six authenticated terminal candidate intersections.
Exact evidence is
`docs/verification/evidence/native-exact-candidate12-staged-recovery-success-20260930.json`.

This accepts rename-back recovery only.  It is not cleanup/deletion, a build,
a guest or OS acceptance.  Next author a fresh cleanup release binding the
accepted observer/current source and entirely fresh attempt-3 outputs; obtain
independent execution review and run it once.  On accepted cleanup, trim and
remeasure capacity, rebind/release scratch-13 preparation and exportset-25,
build the smallest current image and run separately labelled diagnostic
startup/memory/files/threads-futex/signals/shutdown applications.

Continuation checkpoint 263, 2026-09-30: fresh cleanup release
`455b092e...b256` at fetched commit `3385747b...eff8` passed independent
execution review and its single authorized attempt returned `STORAGE_PASS` with
exit zero.  Independent evidence review accepts all 10,038 journal records:
complete staging, renewed census, irreversible admission, 2,507 paired deletion
intents/completions, final census and completion.  The receipt contains exactly
2,507 `deleted` states and no uncertain state.

All targets are absent; quarantines 2 and 3 exist and are empty.  Three raw
censuses retain stable 41-container inventories with exactly six authenticated
terminal intersections, both leases absent and all 17 protected entries valid.
All 2,507 restoration paths and Git blobs (9,096,966,061 bytes) remain verified
at `4e99a82c...7a1`; there is no separate capsule.  Journal/receipt/status hashes
are `78fd1fd6...2353`/`3c136b0d...2092`/`b73bdb91...763d`.  Exact evidence is
`docs/verification/evidence/native-exact-candidate12-planbound-cleanup-success-20260930.json`.

Scratch free space rose from about 17.1 GB to 26.19 GB before trim; host free is
30.83 GB and MemAvailable is 28,479,932 KiB.  This accepts cleanup only.  Next
checkpoint/fetch this evidence, run targeted scratch `fstrim`, remeasure floors,
then rebind and release scratch-13 preparation against the fetched descendant.
After preparation, independently release exactly one serialized exportset-25
build, validate its real linked artifact, and begin the separately labelled
diagnostic application loop.  No formal acceptance counter changes here.

Continuation checkpoint 264, 2026-09-30: after the fetched cleanup-evidence
checkpoint, targeted scratch `fstrim` reported 11,979,268,096 bytes trimmed.
The sparse backing allocation fell from 97,652,879,360 to 88,548,909,056 bytes,
a 9,103,970,304-byte host recovery.  Host/scratch free bytes are now
39,930,843,136/26,192,269,312 and MemAvailable is 28,473,880 KiB, above the
16/12/16-GiB floors.

Scratch-13 preparation is now rebound acyclically to fetched cleanup commit
`6fed3a10...2053`.  Exact packet/test hashes are `5aa30499...5589` and
`57b65381...95db`; all 43 tests, `bash -n` and diff checks pass.  Independent
source review confirms only the candidate sentinel and its two assertions
changed; all tool/contract/overlay bindings, resource gates and the consumed
exportset-16 identity remain exact, while all ten `6fed3a10-scratch-13` targets
plus exportset-25 are absent.  Exact evidence is
`docs/verification/evidence/native-exact-candidate12-trim-and-scratch13-rebind-source-20260930.json`.

This is preparation-source evidence only.  Next fetch-verify the rebind commit,
obtain command-level execution review and complete live process/lease/Docker/
capacity preflight, then run the packet once with candidate `6fed3a10...2053`
and the fetched descendant as its release commit.  Preparation creates no
Docker container, lease, compilation or guest.  A separate reviewed one-shot
exportset-25 build remains required afterward; no formal acceptance changes.

Continuation checkpoint 265, 2026-09-30: the single released scratch-13
preparation invocation completed with exit zero and final dispatcher stdout
`LOG_FINAL_FSYNC=PASS`.  Independent evidence review returns
`PASS_PREPARATION_EVIDENCE`.  The exact candidate/release are
`6fed3a10...2053`/`b55e3c37...12a2`; candidate and metadata-backup identities
are device 1831, inodes 3169097/1722598, with 9,240,506,368/1,556,480 allocated
bytes.  The candidate preserves pinned IHK `3114d9e...72a1f`, passes the
retained-file input, standalone Git-metadata and placement checks, and uses
ext4 with zero memory-backed allocation.

The raw log/terminal/input-manifest/nonreleased-request hashes are
`03e6fc48...a03`/`beee2e47...c3ec`/`fbfde0a1...3161`/
`765af952...688`.  The terminal binds preparation PID 2236619, starttime
102856668 and return code zero; that PID and all children are absent.  Output
and evidence directories are empty, while the request lease and exportset-25
exclusion are absent.  The request explicitly remains
`preparation_only=true`, `execution_released=false`, `executable=false` and
`release_required=true`.  Exact evidence is
`docs/verification/evidence/native-exact-candidate-preparation-scratch13-success-20260930.json`.

Launcher shutdown then stopped new dispatch and joined every child lane.
Preserved launcher process identities are PIDs 1442141/1442142/1442145/
1442149 (wrapper/launcher/worker/app-server), all started 2026-09-30 10:46:42
PDT.  No QEMU, mcexec, kernel build or guest is active.  Current host/scratch
free bytes are 30,651,338,752/16,948,912,128 and MemAvailable is 28,347,768
KiB; the independently checked required floors are 18,790,481,920/
14,495,514,624 bytes.  The raw log intentionally ends with
`LOG_FINAL_FSYNC=PENDING`; successful fsync precedes publication of the
hash-bound terminal, and the dispatcher retained its final PASS stdout.

The next invocation must not reuse the nonexecutable host request.  First
prepare an acyclic exportset-25 image input/toolchain/request binding for this
candidate and the current image owner/postlink/linked-text sources, then obtain
independent one-shot heavy-build release.  Recheck capacity, persistent
process identities, all leases and the full Docker census immediately before
the single serialized build.  If its real linked artifact passes, proceed to
separately labelled startup, memory, files, threads/futexes, signals and
shutdown diagnostic applications.  This window produced zero current image
builds and zero real guest applications; diagnostic and formal acceptance
counters remain unchanged.  The OS goal is incomplete and launcher-paused for
shutdown; it is neither resumed nor marked complete.

Continuation checkpoint 266, 2026-09-30: the resumed invocation found that the
old source-free tool-image receipt was candidate-bound to `4e99a82c`; it could
not authorize a `6fed3a10` request unchanged.  A proposed receipt-only rebind
was independently rejected: it required same-candidate and invented schema
fields, emitted an unconsumed request without an offline probe/final PASS path,
and had incomplete evidence and publication protections.  Its exact rejected
source/test hashes are `691130fa...dafc`/`ec9b7c0f...7009`; all seven synthetic
tests passed but do not cure those findings.  Failure evidence is
`docs/verification/evidence/native-exact-tool-image-rebind-source-failure-20260930.json`.

The strategy changed to the already reviewed source-free producer.  Fresh
attempt-6 proposal `e7327ee8...967f5` at fetched commit `94d4ef77...331c`
received independent `PASS_EXECUTION_ATTEMPT6`.  Privileged preflight found all
historical lease owner PIDs absent, all three attempt paths fresh, no live
heavy/QEMU/mcexec owner, 41 retained containers with only two unrelated Kasper
services running, and host/scratch/MemAvailable readings above the reviewed
floors.  The exact command ran once and exited zero.

Independent result review returns `PASS_RESULT_ATTEMPT6`.  Read-only receipt
`a030708f...2f08` binds candidate `6fed3a10...2053`, immutable amd64 image
`sha256:5688f9c8...cb98` (1,726,886,736 bytes), the exact toolchain lock, 46
packages, 22 executables, four library/header groups and 479 RPM identities.
All 92 receipt members and 28 successful command captures verify.  Online and
offline observations are byte-identical at `f3b88a58...9cbc`; both sequential
owned containers retired as exited/PID0/exit143/OOM-false and were removed.
The lease and all owner/client PIDs are absent.

Actual scratch device 1831 remained at 16,948,912,128 free bytes; host free is
28,919,656,448 and MemAvailable is 28,074,128 KiB after the run.  The producer
receipt's `scratch_free` field measures its host output filesystem, so the
separate actual-scratch measurements remain the capacity evidence.  One local
regression invocation with an artificial per-user `--nproc=96` limit produced
19 fork EAGAIN harness errors; removing only that artificial limit in the
bounded correction yielded all 86 tests PASS under one CPU/1.5 GiB.

Independent review also accepts reuse of the retained scratch-12 host output
as exportset-25's read-only `/out`: all 140,053 closure rows, 132,191 regular
files and 4,799,270,420 bytes match both live contents and the original PASS
owner inventory, with unchanged host/IHK inputs.  Only the McKernel-local
linker-wrapper source changed.  This avoids a redundant host build but grants
no new host-build acceptance.  Exact combined evidence is
`docs/verification/evidence/native-exact-tool-image-6fed3a10-attempt6-success-20260930.json`.

The next executable dependency is the fresh current-candidate libdwarf
gitlink binding.  Its first packet and bounded correction are both retained
BLOCKs for lifecycle/durability/inventory defects; an expert escalation is
active and must pass independent source review before one unprivileged
preparation.  Then prepare and review exportset-25 against the fresh tool image,
scoped retained `/out`, exact nightly and current source, run one serialized
image build, and validate the linked artifact before any diagnostic guest.
This continuation still has zero linked current images and zero real guest
applications; no formal acceptance counter changes.

Continuation checkpoint 267, 2026-09-30: the expert-repaired exportset-25
libdwarf packet at fetched commit `1db10b23...7ff` passed independent source
review.  Its packet/test hashes are `3e006c7c...dc65`/
`eef59779...e080`; 12 actual-packet methods covering 23 vectors passed under
one CPU and 1.5 GiB.  The single unprivileged production invocation then
returned zero with the required stdout commit witness and `LOG_FINAL_FSYNC=PASS`.

Independent result review returns `PASS_GITLINK_PREPARATION_RESULT`.  The new
manifest is `fcdc013f...9046`, the terminal is `e48b985c...dd3`, and the final
log is `645a8863...bb6`.  The clean libdwarf checkout binds commit/tree
`ab9230...3753`/`dcc297...668`, all 412 tracked files and 21 Git metadata
files.  Owner/child/helper PIDs 2258539/2258540/2258541 are absent; all four
exclusive claims remain as evidence.  Exact committed evidence is
`docs/verification/evidence/native-exact-export25-gitlink-preparation-success-20260930.json`.

Shutdown stopped new dispatch and joined every child lane.  Preserved launcher
process identities remain PIDs 1442141/1442142/1442145/1442149
(wrapper/launcher/worker/app-server), started 2026-09-30 10:46:42 PDT.  No
QEMU, mcexec, McKernel image owner/offline driver or compiler build is active.
Host/scratch free bytes are 28,857,323,520/16,906,440,704 and MemAvailable is
28,065,060 KiB.  No heavy build was started during shutdown.

The exportset-25 request wrapper's first version was independently blocked and
its one bounded correction is preserved unreleased at packet/test hashes
`4445af94...8203`/`e81ce26e...9616`.  The correction has only three superficial
tests and still lacks complete claims, signal/descendant retirement, exact
full dependency hashes, checked complete writes, durable log/terminal outcome,
and semantic post-result validation.  Per convergence, do not execute or send
it back through another cheap correction.  The next invocation must obtain an
independent final review of this correction, retain the expected BLOCK, then
escalate an expert repair using the accepted gitlink supervisor pattern.  After
that repaired data-only request packet passes review and runs once, checkpoint
and fetch-verify its exact request, obtain a separate one-shot heavy-build
release, and invoke the image owner unprivileged with the positional request.
The owner must retain the pinned four-CPU/12-GiB/no-network profile and the
read-only scratch-12 `/out`; preserve owner/driver evidence and terminal Docker
metadata.  Validate any real artifact with separate postlink and linked-text
ownership reports before the separately labelled memory-first diagnostic app
loop (then files, threads/futexes, signals and shutdown).  Current counts remain
zero linked current images and zero real current-candidate guest applications.
The OS goal is incomplete and launcher-paused; it is neither resumed nor marked
complete.

Continuation checkpoint 268, 2026-09-30: the launcher continuation resumed the
active objective and adopted the unchanged policy hashes GOAL
`76c4f5d1...c0bcc3`, START `1698d342...6216c`, CONVERGENCE
`f6938bd2...3e86a` and HANDOFF `bdc94610...0af8c5`.  Live reconciliation found
the same wrapper/launcher/worker/app-server PIDs 1442141/1442142/1442145/
1442149 and no QEMU, mcexec, image owner/offline driver, compiler build or heavy
lease occupant.  Scratch free space was 16,906,440,704 bytes and MemAvailable
about 27.9 million KiB.  A complete privileged Docker census remains a required
immediate pre-execution gate.

Independent final review confirmed the unreleased bounded correction at
packet/test hashes `4445af94...8203`/`e81ce26e...9616` was BLOCKed: it fails
deterministically after partial mutation, authenticates executable dependencies
with only 28-bit prefixes, and has no claim, terminal outcome, bounded child
retirement or semantic publication validation.  Per convergence, an Astra
expert redesigned the same two-file boundary.  Its first candidate
`8c3d5686...9be0`/`841340c4...2c2` passed 19 tests but independent review found
two additional blockers: valid Python bytecode caches could execute
unauthenticated code, and discarded initial build/nightly inventories allowed
both child and validator to accept a changed tree.  Both original findings are
preserved; no production target was touched.

The narrow expert correction now independently returns
`PASS_EXPORT25_PACKET_SOURCE` for exact packet/test hashes
`fbae0ebb...cbb4`/`963f8cad...7aca`.  Twenty-one methods and 103 counted vectors
pass on Python 3.8/3.9; the independent run passed in 17.908 seconds on CPU 0
with a 1.5-GiB address-space limit.  The preparer closure executes only
authenticated bundled source bytes through a closed importer; poisoned valid
cache controls and deterministic build/nightly mid-flight mutations reject.
The retained supervisor also supplies full-hash preflight, exclusive persistent
claim, durable log, bounded session/subreaper/pidfd retirement, explicit three-
state publication classification, independent exact-document validation,
durable no-replace terminal and matching stdout witness.  It remains data-only:
no Docker, build, heavy lease or owner `.run()` path is reachable.  Exact source
evidence is
`docs/verification/evidence/native-exact-export25-image-preparation-source-success-20260930.json`.

Next checkpoint and fetch-verify these exact bytes, then obtain an independent
command-level execution release for one ordinary-user invocation of the packet.
Reconcile all target absence, claims, leases, processes, capacity and the full
privileged Docker census immediately before running it.  Accept preparation
only from zero wrapper exit plus the stdout witness matching the durable
terminal/log; independently review the resulting toolchain/request and partial-
publication state.  Only after a fetched accepted request may a separate
one-shot heavy-build release invoke the image owner.  Validate any linked image
with separate postlink and linked-text reports, then rebind the memory diagnostic
to the exact image/module/mcexec tuple and run `/bin/mcexec -t 1 0 app memory`
with exact stdout `NATIVE_CORE_PASS memory\n`, empty stderr and exit 37.  The
diagnostic remains distinct from application acceptance.  Current counts remain
zero linked current images and zero real current-candidate guest applications;
the OS goal remains active and incomplete.

Continuation checkpoint 269, 2026-09-30: fetched source commit
`5b7b4d87...8564` received independent conditional execution release for one
ordinary-user data-only invocation.  Fresh admission verified all targets
absent, exact input/helper/image hashes, no conflicting process, devices
66306/1831, 28,812,750,848/16,906,440,704 host/scratch free bytes,
27,916,440 KiB MemAvailable, and a complete privileged Docker census with only
the two unrelated Kasper services running.  The first process observer matched
its own shell and stopped before completing admission; the corrected observer
excluded only its verified ancestor chain.  Neither observer created a target
or consumed the released packet.

The exact released command then ran once and failed immediately with exit 1,
empty stdout and `SUPERVISOR_ERROR=RuntimeError('receipt evidence name')`.
Every preparation target remains absent; no claim, directory, lease, exclusion,
Docker operation or build exists.  The consumed packet/release must never be
retried.  Diagnosis proves its read-only receipt validator incorrectly required
basenames while the immutable receipt validly binds nested command-capture names
such as `command-041639d913a34bfb854521039c919db3/status.json`.

The one bounded production correction admits only normalized nonempty relative
nested paths below the receipt root and continues to reject absolute, traversal,
dot, non-normal and symlink-escape paths with exact size/hash checks.  Its first
test candidate was independently BLOCKed only because a fixed `/tmp` escape
directory made the symlink regression nonrepeatable.  Expert escalation changed
that fixture to a unique temporary directory with registered cleanup; no stale
directory deletion was required.  Independent rereview now returns
`PASS_EXPORT25_RECEIPT_PATH_CORRECTION` for packet/test hashes
`a8f4fcb8...893f`/`a9e75195...5024`.  Both expert and reviewer passed the full
23-test suite twice; production packet behavior outside this path validator is
unchanged.  Exact additive evidence is
`docs/verification/evidence/native-exact-export25-image-preparation-attempt1-failure-and-correction-20260930.json`.

Next checkpoint and fetch-verify the corrected bytes, obtain a fresh independent
execution review, and use the same complete live admission with a new one-shot
authority.  On preparation PASS, independently validate the stdout witness,
terminal/log, exact request/toolchain documents and postflight before seeking a
separate heavy-build release.  Current linked-image and current-candidate real
guest-app counts remain zero; no formal counter changes and the whole OS goal
remains active.

Continuation checkpoint 270, 2026-09-30: corrected fetched commit
`4ae69af9...0e50` received fresh independent
`PASS_EXECUTION_EXPORT25_PREPARATION_ATTEMPT2`.  Complete live admission again
verified exact helpers and inputs, all targets absent, no conflicting process,
devices 66306/1831, 28,794,834,944/16,906,440,704 free bytes,
27,897,464 KiB MemAvailable, the immutable image identity and the complete
41-container census with only two unrelated Kasper services running.

The single ordinary-user attempt then completed after about three minutes with
wrapper exit zero and one stdout commit witness.  Independent review returns
`PASS_EXPORT25_PREPARATION_RESULT`: terminal/log hashes are
`8a72acac...e072`/`867ddf41...1b86`, publication is `request-published`, child
return is zero, semantic validation PASS and all descendants retired.  Published
inputs/toolchain/request hashes are `af41bb15...97ee`/
`de4bcafc...1cf83`/`9923b51f...461d`.  Terminal and pending names share inode
90678/link-count two.

Independent reconstruction verifies 140,053 retained `/out` entries, 3,035
nightly entries, 86 backup entries and all 92 tool-image evidence files.  A
mutation-denying replay of authenticated `ImageOwner.validate()` passes.
Owner/child/helper PIDs 2281698/2281701/2281739 are absent; work/evidence roots
are empty and lease/exclusion/attempt/new build output remain absent.  Postflight
host/scratch free bytes are 28,680,130,560/16,797,904,896 and available memory
is 27,958,583,296 bytes.  Exact evidence is
`docs/verification/evidence/native-exact-export25-image-preparation-attempt2-success-20260930.json`.

This accepts preparation only.  Next checkpoint/fetch these bytes, obtain a
separate independent one-shot heavy-build release for the exact request
`9923b51f...461d`, then repeat complete process/lease/Docker/capacity admission
immediately before invoking the image owner unprivileged.  Preserve every owner,
driver, Docker and terminal artifact.  A successful build still requires
independent artifact review plus separate postlink and linked-text reports before
the memory diagnostic can be rebound.  Current linked-image and real current-
candidate guest-app counts remain zero and no formal counter changes.

Continuation checkpoint 271, 2026-09-30: fetched commit
`85d254de...bfbd` received independent `PASS_EXECUTION_EXPORT25_HEAVY_BUILD`
for exactly one ordinary-user owner invocation.  Immediate admission verified
the exact request `9923b51f...461d`, owner `a6d6ffaa...7f0`, protected inputs,
empty work/evidence roots, absent attempt/output/lease/exclusion targets, no
competing build or guest, 28,661,276,672/16,797,904,896 host/scratch free
bytes, 27,858,200 KiB MemAvailable, and the complete 41-container census with
only the two unrelated Kasper services running.

The exact released command ran once and failed immediately with exit 1 and no
stdout.  Its import-time authenticated loader raised `RuntimeError: host owner
is not a regular source file`.  The consumed command named the owner script
relatively; Python therefore supplied a relative `__file__`, while
`_load_reviewed_host_owner()` deliberately requires an absolute regular source
path before reading the host owner.  This is a new deterministic
relative-entrypoint-authenticated-import failure family.  It occurred before
request parsing, claim/lease creation, Docker or build execution.  Do not retry
the consumed release.

Shutdown postflight found no matching owner, driver, mcexec or QEMU process;
the work and owner-evidence roots remain empty; output, evidence, attempt,
lease and common-exclusion targets remain absent.  The Docker census is still
41 total/two running with no exportset-25 or 6fed3a10 container.  Host/scratch
free bytes are 28,658,655,232/16,797,904,896 and MemAvailable is 27,858,896
KiB.  Original failure and postflight evidence is
`docs/verification/evidence/native-exact-export25-heavy-build-attempt1-failure-20260930.json`.

The launcher process identities preserved at shutdown are wrapper 1442141,
launcher 1442142, worker 1442145 and app-server 1442149, all started
2026-09-30 10:46:42 PDT.  All eight child lanes are completed.  The launcher
requested a checkpoint pause; the goal is not complete and is not resumed in
this window.

Next continuation: first add a cheap disposable regression that binds the
relative-entrypoint failure and proves the absolute entry point reaches the
same authenticated source loader without invoking `.run()`.  Independently
review the smallest command-only or source correction, checkpoint/fetch it,
then obtain a fresh one-shot heavy-build release using an exact absolute owner
path and repeat the full live admission.  On build PASS, independently validate
the artifacts, postlink and linked-text reports before rebinding and running
the diagnostic-only memory smoke.  Current counts remain zero linked current
images and zero real current-candidate guest applications; no formal acceptance
counter changes.
