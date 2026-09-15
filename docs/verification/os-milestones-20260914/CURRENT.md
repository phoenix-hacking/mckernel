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
unable to validate their own Docker configuration/build record. All four exact
states and findings are retained. A
corrected durable owner with persistent recovery, watchdog identity and exact
name/label/ID cleanup is the next prerequisite; only then may the dispatcher
take the sole heavy lease. No heavy process or McKernel guest is live.

Counters remain: 0/273 application cases accepted (three compiled), 2/4 narrow
fault modes accepted, 6/130 production gates and 350/10,000 points, 0/7 language
gates complete (three IN_PROGRESS). Current production remains exact baseline
module2026091301/image3 with its eight original suites; no broader acceptance is
claimed. External hardware/exposure work remains later and unavailable locally.
