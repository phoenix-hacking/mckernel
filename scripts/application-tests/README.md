# Application verification executor contract

This directory contains a **plan**, a 273-case catalog and 97 draft packets. It does
not yet contain an implemented runner, supervisor or new application payloads.
All new results remain unverified. Commands containing placeholders, or naming
an unimplemented program, must not be executed. The four historically accepted
core modes are recorded separately in `cases.json`; they do not count toward
the new catalog's logical-case total.

The executor can be Luna or Spark. Its job is broad, bounded test implementation.
Max handles narrow diagnosis and difficult kernel fixes. Model changes are the
user's choice. This contract never permits changing an assertion to obtain a
pass.

## What the active executor receives

Give the executor only this README, one reviewed packet, that packet's selected
case objects, a capability manifest, an exact input manifest, and the directly
needed existing sources/helpers. Do not supply the whole historical log or the
whole catalog. At most three logical cases are active. Expand parameter vectors
only for those cases; each vector is an execution, not an additional case.

`cases.json#ID` in a packet is a selector, not a filesystem path. The packet
loader must resolve it to exactly one case object and supply that subset with
the complete catalog's SHA-256. Missing/duplicate IDs, unrecognized schema,
unresolved placeholders and stale input hashes are errors before execution.

All 97 packets are `draft-only` and `execution_enabled=false`. After root
releases the reviewed queue, they authorize creating their listed fixture/oracle
files and reporting a diff.
They do not authorize a kernel change or guest launch. Root may supply a
reviewed sequential draft queue; proceed through that queue without repeated
user permission, with only one packet's bounded context active at a time.
Do not select unlisted packets or broaden their scope. A reviewer must issue
a new packet version before enabling execution.

The canonical [draft queue](draft-queue.json) assigns every one of the 273 cases
exactly once. Packets 001–007 preserve the initial 20-case sequence; 008–097
cover the remaining 253 cases, grouped by family and dependency order. No
packet has more than three cases. The queue remains pending root validation
and the verified handoff checkpoint until its release record says otherwise.

The [handoff gates](../../docs/verification/ultra-handoff-gates-20260909.md)
distinguish drafting readiness from runtime acceptance. The catalog's global
execution gates and each packet's `blocked_by` list constrain execution; they
do not require implementing the runner before drafting its fixtures. Root
announces draft readiness after the specified current-source checks, original
regressions, independent ordinary fixtures and verified GitHub checkpoint.

## Canonical schemas

Catalog version 2 retains schema version 1 and has `schema_version`, `catalog_version`,
`logical_case_count`, `baseline_regressions`, `global_execution_gates`,
`capabilities` and `cases`. Each case has a unique `id`, integer `version`,
`family`, `status` (`planned` or `blocked`), `execution_status`, `requires`,
`depends_on`, `mode`, `command_argv`, `payload_contract`, `oracle`, `limits`,
`parameters`, `evidence`, `cleanup`, `repeatability`, `implementation_status`
and `acceptance_status`. Every case contributes exactly one to the logical
count. Dependencies must resolve without cycles. Baseline records contribute
zero. A planned case may be drafted while its global execution gate is blocked.

The 56 vector cases carry an embedded `vector_contract` with transitive CPUID
feature masks, XCR0 requirements, target instructions and compilation rules.
The raw capability records come from both pinned Linux guest and McKernel.
Physical host flags never authorize an optional guest instruction. Missing
support is BLOCKED, and an instruction's absent parameter is not a passing
parameter. Follow the [vector plan](../../docs/verification/ultra-vector-test-plan-20260909.md)
for register observation, exact arithmetic, FP tolerances and disassembly.
The kernel opcode audit is static evidence and contributes no application run.

Capability manifests must contain `schema_version=1`, a source/module/image
input-manifest SHA-256, and a capability map. Each capability has
`state=verified|unsupported|blocked`, its exact contract, and evidence paths
with SHA-256. `unsupported` satisfies only a named negative capability test;
it never enables a successful-use test. Historical baseline support does not
verify a modified module/image. Required `blocked`/missing/stale capability
means BLOCKED, never PASS or a permissive skip.

Input manifests must contain `schema_version=1`, source commit and dirty-diff
identity, selected source/formatter/compiler bindings, all three native module
hashes, Linux kernel and McKernel image hashes, unchanged launcher hash, exact
payload/interpreter/DSO closure, compiler commands/dependencies, QEMU argv,
container identity/limits, guest topology, boot arguments and named immutable
input fixtures. Every path has size and SHA-256. File hashes, not dated path
names, determine identity. A changed source or candidate fix invalidates old
binary coverage until rebuilt, rebound and reviewed.

Packets contain `schema_version=1`, stable `packet_id`, monotonically increasing
`version`, one to three `case_ids`, `mode`, `execution_enabled`, input selectors,
read/write allowlists, permitted command argv arrays, explicit resource limits,
blocking gates, candidate-fix policy and completion checks. The validator must
reject writes outside the allowlist, shell fragments in metadata, unknown case
IDs, absent oracles, unreviewed capabilities or increased resource bounds.

The draft queue has `schema_version=1`, `queue_version`, `queue_id`, a review
state, catalog version/count and ordered `packets` objects containing
`packet_id`, `path` and `case_ids`. The loader verifies each object against its
packet, unique complete catalog coverage and dependency order. It supplies the
active executor only a cursor with the queue hash, index, total and next ID,
plus that packet's bounded context. Completed case bodies are replaced by
immutable report references and a minimal unresolved-dependency summary.

Each packet's `reporting` object grants one explicit scratch exception under
`/work/application-test-drafts-20260909/{fresh_queue_run_id}`: its immutable
`packet-NNN/report.json`, original failure artifacts inside its named failure
directory, and append-only shared `failures.jsonl`. This does not expand the
repository write allowlist. Root binds a fresh queue run ID before drafting;
never overwrite a prior report. A revised run links the previous evidence.

On an unexpected drafting error, preserve the original output, source/diff,
command or tool action, environment and context hashes before diagnosis.
Append one complete JSON event using `O_APPEND|O_CREAT|O_NOFOLLOW` on a regular
file and fsync it; never truncate or rewrite prior events. Record the precise
question and smallest reproducer for Max where semantics are unclear. The
established immediate kernel.log rule also applies to actual validation/runtime
failures. A draft packet does not authorize a production candidate patch.

Every packet report names case draft statuses, changed-file hashes, unresolved
oracles, blocked execution capabilities, original failure reference and Max
escalation. Status is `DRAFTED`, `DRAFTED_WITH_UNRESOLVED`, `BLOCKED` or `FAILED`;
`PASS` is forbidden. Report progress after every packet: index/97, cases and
their draft statuses, produced files, unresolved expectations and the next
already-reviewed packet. Continue independent queued drafts after preserving
and classifying a failure; mark affected dependencies rather than fabricating
their expectations. Do not switch models or ask for permission at each packet.

After all 97 packet reports exist, exclusively create `queue-summary.json`
under the same scratch root, with all report hashes and exact drafted,
unresolved, blocked and failed counts. Its status is `DRAFT_QUEUE_COMPLETE` or
`DRAFT_QUEUE_COMPLETE_WITH_BLOCKERS`. That records drafting coverage only;
runtime readiness and application acceptance remain separate.

Each draft must create a versioned `oracles/ID.json` that freezes constants,
input-file hashes, raw byte expectations and named relational predicates before
its first run. Permitted predicate forms are exact integer/byte/string equality,
bounded integer/range, set equality, ordered sequence, monotonic sequence,
explicit digest of independently generated data, raw wait-status classification,
and named resource-lifetime invariants. No executable expressions or arbitrary
normalization code in metadata. A pinned-reference-specific diagnostic must be
frozen with its binary/version before the McKernel comparison. An unexpected
result cannot be adopted as the expectation retrospectively.

## Planned build and execution interface

The metadata validator exists. The execution command describes the required
interface for the future repository runner and is not implemented yet:

```text
python3 -B /workspace/scripts/application-tests/validate.py --packet /workspace/scripts/application-tests/packets/packet-001.json
python3 -B /workspace/scripts/application-tests/run.py --inputs /work/verified-inputs.json --case memory.calloc-zero --attempt /work/application-tests-memory-calloc-zero-ATTEMPT --profile baseline-root-1cpu --mode differential-guest
```

Run the second command only inside the established native container after all
gates pass. Its attempt directory must be created exclusively and must not
already exist. The runner reads argv arrays directly; it must not use a shell
to interpret the case metadata. Pinned `gcc` builds ordinary payloads with
`-std=c11 -O2 -Wall -Wextra -Werror -fno-pie -no-pie -pthread -MD`, plus a
case-reviewed feature macro when necessary. Retain the exact command, emitted
ELF/disassembly, dependency list and DSOs. Extended-loader cases explicitly
override ELF/link selection. Exact-production-fixture cases compile the actual
selected production bodies and retained independent references in the native
container; they are not application executions.

The guest supervisor first runs the exact payload directly on pinned Linux,
resets all case inputs, then runs those same bytes through
`/bin/mcexec -t 1 0 PAYLOAD ARGS...`. Match argv, environment, cwd, uid/gid/groups,
umask, inherited fd streams and all input bytes. Capture those values for both
engines. A container reference runs on the container host kernel and cannot
replace the pinned guest Linux reference. Root-profile permission tests must
not assert nonroot EACCES semantics. Do not impose an unverified small
`RLIMIT_AS` on mcexec's large mirror mapping.

The supervisor drains stdout/stderr concurrently, records raw `waitpid` status
and separates payload diagnostics from launcher diagnostics. Normal fixtures
emit a bounded canonical JSON record and exit zero; baseline cases retain exact
output and exit 37. Fatal tests require real `WIFSIGNALED` and the named signal;
an exit code `128+signal` is insufficient. Read errno immediately; pthread
functions return their own error numbers. Every case additionally requires its
independent fixed oracle, not merely equality to another execution.

Real McKernel provenance requires scheduled OS/generation/PID/TIDs and a matched
actual delegated request/return. Prove every application child separately;
Linux supervisor children are not guest application children. Route sampling
after 64 deliveries is labeled `first_64_deliveries`; never claim complete
runtime tracing from sampled printk. Strong stress/lifetime acceptance needs
verified resource accounting and explicit loss/overflow information.

## Bounds, failures and repair authority

Per-case bounds are in the catalog. The default is ten seconds of payload time,
15 seconds of cleanup, 300 seconds per QEMU guest, 120 seconds per preparation
subprocess, 8 MiB live payload allocation, one guest CPU/128 MiB, four Linux
vCPUs/8 GiB, and four container CPUs/12 GiB/no swap/512 tasks. Tests requiring
more threads use explicit 256 KiB stacks. No host kernel/module tests, host
reboot, network downloads, broad process-name kills or resource expansion.

An independent Linux-supervisor deadline and outer host QEMU deadline must
both exist; a frozen guest clock cannot disable the latter. On timeout capture
the exact owned VM before terminating it. QMP capture records stop/continue
states and explicitly resumes even an unvalidated capture. A failed resume
is a failure with emergency capture, never an implicit successful continuation.

On the first unexpected failure: stop the affected batch, immediately record
exact command/environment/error in `kernel.log`, preserve the complete original
attempt, then diagnose. No hidden retry. Every rerun uses a new attempt ID.
Expected negative cases pass only their frozen exact negative contract and
required lack of partial side effects. A missing capability is BLOCKED.

An execution-enabled packet may permit **one** candidate fix for a simple,
diagnosed defect: at most 15 minutes, two files and 80 changed lines, within
an explicitly reviewed write allowlist. The preserved first failure remains
FAIL. A candidate is never accepted automatically; submit its diff, rationale,
new evidence and changed-input identities. Native unsafe code, memory/PID/MM
lifetime, ABI/wire formats, scheduler/transport ownership, unclear errno or
concurrency semantics, larger edits or an unsuccessful candidate go to Max.
Do not continue drafting competing kernel repairs or broaden the allowlist.
Oracle weakening, baseline changes and relabeling old failures are prohibited.

## Evidence and completion

Every result has `schema_version`, case/version, packet/version, attempt ID,
source and input-manifest identities, exact commands/profile, both kernel
versions, raw output/wait artifacts, individual expected/observed comparisons,
provenance, trace coverage, cleanup/accounting, deadlines and complete artifact
SHA-256. Status is `PASS|FAIL|BLOCKED|NOT_RUN`; missing evidence never defaults
to an empty passing array. Unit, Linux-reference and real application results
are separate dimensions.

Normal cleanup requires matching process/procfs/worker owners gone, retirement
and release successful, observed pager handles balanced, and accounting at the
declared quiet baseline within 15 seconds. Quarantine tests require stable,
explicit retained ownership and no later access/republication; they must not
demand unsafe release. Run every fault attempt in a fresh guest and discard
that guest after terminal quarantine. Quiet numerical PID reuse never replaces
identity/claim verification.

After first acceptance of a short case: three same-OS repeats and one fresh
guest repeat using identical inputs. Later ten-cycle campaigns have frozen
membership and bounded guest batches; never inflate a guest timeout to conceal
a stalled case. Preserve all raw logs, original/executed helpers, queue/RAM/
register captures and failures. Root checkpoints coherent work and roughly
every 30 minutes, verifies GitHub fetched blobs, then permits only audited
cleanup of obsolete duplicates. No old baseline artifact or failed attempt is
expendable merely because a newer case passes.
