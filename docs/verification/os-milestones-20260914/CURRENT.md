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
