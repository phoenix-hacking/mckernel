# User-authorized follow-on: randomized McKernel correctness testing

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

On 2026-10-23 the user explicitly requested: finish all six remaining practical
checks, then start randomized OS fuzzing to find bugs. The latest clarification
makes seeded Rust workloads the FIRST implementation. Syzkaller support is a
required later integration task, not an initial dependency or compatibility spike.
The ordering is mandatory. At this instruction the ledger is29/35, with
P-M01-02/P-M05-03/P-M06-01/P-M08-02/P-M09-02/P-M12-01 still open. Keep all current
execution capacity focused on those closures. This follow-on is not an additional
prerequisite for35/35 and does not start any fuzzer or authorize a new execution
profile by itself. Preserve the prior no-security-testing scope; this request is
for functional crashes, hangs, incorrect results and resource/lifecycle regressions.

## Transition after all six are actually accepted

1. Save the genuine35/35 checkpoint with exact source/config/toolchain/image,
   module/launcher tuple, supported profile and known limitations. Keep milestone
   completion and randomized-test progress as separate records. At the existing
   checkpoint, persist this link in CURRENT/HANDOFF so a fresh session follows it.
2. After positive retirement of the final milestone workload, continue into this
   authorized follow-on rather than stopping solely because35/35 was achieved.
   Do not disable quota or policy holds. Included weekly usage only; no automatic
   credit spending; existing100% usage stop remains.
3. Begin reproducible seeded Rust workloads through the existing native runner
   and normal McKernel launcher. Start with the already accepted supported
   operations and their invariants; vary bounded sequences, sizes, alignments,
   process/thread schedules and seeds. Review/admit the small actual workload
   profile, then execute it. Preserve useful seeds and reduce failures into
   regression cases. New McKernel implementation/glue remains Rust/reviewed
   assembly; preserve allowed Linux control-plane/test-tool boundaries.
4. Add syzkaller support later as a distinct integration work item after initial
   seeded workloads are operating. Do not delay the Rust batches for syzkaller
   setup, coverage instrumentation or a port. When this later task is active,
   freeze an upstream revision and prove its executor reaches actual McKernel
   via the normal launch path, with compatible process/transport/crash handling.
   McKernel is absent from the upstream supported-OS list; Linux ABI similarity
   alone does not prove compatibility. Separate Linux-control-kernel coverage
   from McKernel Rust/assembly coverage; report guidance honestly if the pinned
   tool is used without target coverage. Keep the seeded regression corpus useful
   during and after this integration.

## Initial test scope and operation

Start from accepted selected-suite behaviors: process/exec/wait, cancellation,
threads/futexes, signals, memory mappings/protection, file/stream operations and
resource lifecycle. Generate varied bounded sequences, sizes, alignments and
concurrency schedules with independently specified expected invariants. Retain
supported-operation allowlists and explicitly observed unsupported behavior.
Do not count endless unsupported-syscall rejection as useful coverage. Limit
filesystem targets to each disposable test namespace and keep all privileged
resource lifecycle actions under the existing owner/controller.

Before execution obtain the existing required independent source/runtime review
and fresh measured admission for the actual fuzzer profile. Preserve one-heavy,
CPUs2-5/fourCPU/12GiB/no-swap/512tasks, CPU1 exclusion, ordinary slot grants,
filesystem floors, all active evidence and immutable failures. No testing on the
workstation's host kernel as a substitute for an isolated target. Parallelize
admitted guest workers only within the tested CPU/ownership profile and parallelize
host-side reproduction/minimization when independently admitted.

Use bounded batches with recorded seeds and complete generated programs, syscall
results, stdout/stderr, kernel diagnostics, exact artifact tuple, resource counters
and timeouts. Classify and deduplicate crashes, hangs and incorrect results;
reduce each failure to a small reproducible sequence, fix it and add a regression
before rerunning the affected boundary. Preserve the original failure and require
positive retirement before a fresh guest after a crash. An uncertain owner remains
retained. If a finding contradicts a previously accepted check, explicitly reopen
that check and revalidate it after the repair; do not silently preserve an invalid
completion claim. No arbitrary huge exposure quota is added.

At existing30-minute checkpoints report actual McKernel executions/sec, successful
and rejected operations, unique reproducible defects, fixed regressions, tested
seeds, actual coverage where available, and time lost to restart/admission. A long
run without observed failures is bounded evidence, not proof of a bug-free OS.

## Primary references checked 2026-10-23

- Supported OS list and tool overview: https://github.com/google/syzkaller/blob/master/README.md
- Linux setup and executor/VM environment: https://github.com/google/syzkaller/blob/master/docs/linux/setup.md
- Linux coverage model: https://github.com/google/syzkaller/blob/master/docs/linux/coverage.md

These references support the compatibility questions above; no McKernel
syzkaller port or coverage integration has been demonstrated in this preparation.
