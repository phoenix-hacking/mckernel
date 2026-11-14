# Layer-B profile 1 correction 2 — persistent bounded evidence

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This is the one bounded correction
to failed profile review 1, SHA256
`b6b094931602d362aeba2b762a2e2c1971115fe748b7564f1e4440644ed204b8`.
Authenticate its exact failure record at
`docs/verification/stability-layer-b-microtest-profile-review-failure-20260928-1.json`.
Unchanged prohibitions and no-acceptance scope from profile 1 remain normative;
the following clauses supersede its command, binding, evidence and limit clauses.

## Exact supervisor and initial command release

The sole initial entry point is
`scripts/tests/run_layer_b_microtests_v1.py`, SHA256
`66bb449a02be5dadecaf24289bbdafaf067befa561214b76ab494b06984b32d6`, invoked by the
dispatcher with Python 3.9.12 from repository root as:

```text
/home/holden/anaconda3/bin/python3 -B scripts/tests/run_layer_b_microtests_v1.py --output /home/holden/mckernel-work/scratch/stability-layer-b-microtest-20260928-2
```

The output root must be absent and its parent existing. The supervisor itself
creates mode-0700 `home`, `tmp`, `logs` and persistent `m03` content, verifies
every bound input before creating the root, uses the sanitized environment from
profile 1, and runs exactly three sequential commands in new sessions:

1. the two named M02 descriptor/acquisition tests under pinned Python 3.9;
2. the same two tests under `/usr/bin/python3` 3.8.10;
3. the M03 harness under Python 3.9 with
   `--execute --output <root>/m03`.

The complete 137-test M02 class is **not released by this correction**. It will
require an additive reviewed dependency manifest for the preparation calls,
retained root inputs, failure records and source-review archives whose Python
members it compiles/executes. The focused commands import the exact bounded
`prepare.py` module but never call `prepare.prepare`; that import is explicitly
allowed. Their complete repository dependency set is the current test file,
`collector.c`, and the storage fixture's `packet.json`, `prepare.py`, `inject.h`,
`collector.patch`, `oracle.py`, `witness_owner.py`, `supervise.py` and `tests.md`,
all pinned in the supervisor. The real child replacement environment may add
only `M02_SENTINEL` to `PATH` and `PYTHONDONTWRITEBYTECODE` as encoded in the
bound test. It may use `/dev/null`, pipes, Unix socketpairs and local fork/exec;
it may not access network or production state.

The M03 harness now requires a caller-supplied absent absolute output. It retains
the raw stdout, stderr, status, argv and timestamps for both compiler commands
and all 46 vector executions, retains both binaries and their SHA256, writes a
machine result only after all checks pass, and writes `failure.txt` without
deleting completed evidence on a later failure. Any compiler or vector stderr is
unexpected. Its Rust command is pinned directly to
`/home/holden/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu/bin/rustc`,
version 1.60.0-nightly (`777bb86bc`), SHA256
`cd99ee316fdd92e1c7a9d4442020c722460011e8559a614fb86bb20e5c042f74`;
it does not consult rustup settings or download/install a toolchain. The M03
bindings after the bounded alignment correction are harness SHA256
`85e79cbef3a97443b88017e57c1d1dc9c48d117fc86026a7cecf5789482e7e18`,
C SHA256 `2755ba19e0d7083895daf82f815aca84090a0231d46c119bab93248467490aa6`,
Rust SHA256 `26d1528f296979683850a846bb7a600a451a75a51db50f4d0900e9bdddc6b742`
and unchanged vector SHA256
`bf966b1226f4134609f565bb4e27d89ceff41a79fc842aeac7c8a05999668664`.
Both validators now preserve the independent `misaligned-extent -> -22` oracle
by checking each descriptor physical start against the page alignment.

## Concrete bounds and failure retention

For each child command the supervisor uses `start_new_session=True`, direct
stream files and inherited limits set before exec: core 0, CPU 55 seconds,
NOFILE 256, FSIZE 64 MiB per file and AS 512 MiB per process. Every 50 ms it
enumerates `/proc` by exact session ID, sums current RSS, counts processes and
walks the output tree. It terminates the whole exact process group with TERM,
waits at most five seconds, then KILLs and reaps on any wall time at 60 seconds,
more than eight processes, aggregate RSS over 512 MiB or output tree over
256 MiB. It records peaks, violation, return status and zero residual process/
RSS observation. The runner itself consumes one aggregate campaign job. The
512-MiB compiler ceiling is an admission candidate, not presumed adequate; an
actual resource failure is retained and any limit change needs new review.

M02 `TemporaryDirectory` fixture files are the sole transient-output exception:
their tested constructors are completely source/hash-bound, and ordinary
context cleanup may remove them. A failure still preserves the exact command,
inputs, raw streams, status, limits and supervisor failure record needed to
reconstruct the fixture; no retry occurs. M03 output is never transient and is
preserved in full. Dispatcher evidence additionally records pre/post Git status,
tool hashes/versions, runner hash, complete output type/mode/size/SHA256 manifest,
free space and no surviving session identity.

An initial pass proves only four focused M02 unittest executions and 46 finite
M03 vector executions. It does not establish the full M02 suite, `PASS_SOURCE`,
production pending-free behavior, root/native/guest behavior, application or
gate acceptance. A first compilation/test failure is valid retained admission
evidence and must not be weakened or silently retried.
