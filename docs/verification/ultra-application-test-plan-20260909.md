# Ultra plan for broad application verification

The catalog now specifies **217 logical cases**, with parameter matrices kept
separate from that count. These are planned specifications, not implemented
tests or passing application results. Four unchanged historically accepted
core modes remain separate regression gates. The executor is Luna or Spark; the user chooses and controls model
switches. Max owns difficult, narrow diagnosis and repair.

The 217 specifications comprise 198 differential guest cases, 13 fault guest
cases, five exact-production protocol boundary cases and one bounded
repeatability campaign. Protocol cases are not counted as real application
executions. The family totals are startup 10, memory 24, files 30, threads 17,
futexes 17, signals 18, time 10, processes 20, IPC 16, loaders 8, unchanged
applications 20, numerical work 5, failure phases 12 and exhaustion 10.

Canonical artifacts:

- [`scripts/application-tests/README.md`](../../scripts/application-tests/README.md)
  defines schemas, isolation, independent oracles, evidence and repair limits.
- [`scripts/application-tests/cases.json`](../../scripts/application-tests/cases.json)
  gives each case its operation, independent assertions, capability dependencies,
  argv/mode, resource/time limits, parameters, cleanup and repetition contract.
- [`scripts/application-tests/packets/`](../../scripts/application-tests/packets/)
  contains six initial draft packets, each with one to three cases and exact
  writable files. They authorize drafting only. Runtime remains disabled.
- [Host review](ultra-host-review-20260909.md) and
  [test inventory](ultra-test-inventory-20260909.md) provide review background.
  Supply only relevant excerpts with an active packet, not the complete history.

## Gates before execution or model handoff

1. Complete review fixes and bind their exact selected source/compiler paths.
   Protocol tests do not revalidate old module/image binaries. Rebuild changed
   targets, retain original failures and replay all required current-pair
   baseline/control regressions without weakening assertions.
2. Pass actual transport-failure guest verification: accepted RET with hard
   prepublication failure, notification failure after publication, recoverable
   full queue and permanent queue pressure. Require phase-specific memory/
   ownership evidence, bounded host waiter behavior and no stale publication.
   The 44 host protocol tests alone do not satisfy this handoff gate.
3. Implement/review the repository runner, input/capability/result validators,
   pinned-guest Linux reference and dual-stream supervisor. Prove watchdog and
   QMP pause/resume behavior independently. The current catalog's commands name
   proposed interfaces; missing programs and placeholders cannot be executed.
4. Freeze an exact input manifest and capability manifest. A feature supported
   on the historical baseline is not automatically verified on modified inputs.
   Fork, extended loader, external signal, clock, IPC, accounting, exhaustion
   and multicore gates need their own explicit evidence or remain BLOCKED.
5. Review one small packet's frozen independent oracles and exact writable
   files. A model handoff must explicitly identify that active packet, its mode
   and unresolved gates. Do not describe the entire 217-case list as runnable.

## Breadth and execution order

| Wave | Coverage | Acceptance condition |
| --- | --- | --- |
| 0 | Four original core modes and original controls | Same changed-source-bound module/image pair; original outputs, routes and lifetime assertions retained. |
| 1 | Startup/argv/environment/streams; allocator and VM contracts; regular-file boundaries/errors | Fixed bytes/errno/relations plus same-binary pinned-Linux reference and real McKernel provenance. |
| 2 | Thread/TLS/mutex/barrier/condition-variable and futex contracts; signal/protection faults; time APIs | Individual capability prerequisites accepted; actual thread IDs, signal status and timeout semantics established. |
| 3 | Unchanged cat/wc/hash/copy/sort/head/tail/uniq; deterministic numerical work; gzip/xz/zstd | Exact pinned ELF/options/DSO closure; independent byte/hash/arithmetic/decode oracle; each executable directly launched. |
| 4 | Process fork/COW/exec/wait/pipes; IPC readiness; PIE/static/dlopen/C++/DSO TLS; shell pipeline | All child identities remain in McKernel; fork/loader/IPC support explicitly accepted first. |
| 5 | Every owner-loss phase, guarded user-copy, capacity/failure/zeroing and repeatability | Real fault hooks plus accounting; precise normal retirement versus stable quarantine; fresh fault guest every attempt. |
| Later | Two McKernel CPUs and routing, NUMA, MPI and long campaigns | Separate topology/resource/feature gates; never infer from four Linux vCPUs or one-CPU pthread success. |

The first six packets cover startup records, allocation, closed-fd errors,
basic futex negatives, repeated/nested alternate stacks and unchanged cat.
They are intentionally draft-only while execution infrastructure and runtime
gates are reviewed. New execution packets can select any dependency-satisfied
case, but remain limited to three active logical cases. Parameter vectors are
explicit subordinate runs, such as sizes 1/4095/4096/4097/65553/1048576 or
thread counts 2/4/8; do not multiply the feature count by those vectors.

Process capability deserves an explicit split: current non-null CREATE_PPD
rejects the ordinary fork adoption path. A reviewed negative rollback probe
can test that documented restriction; it cannot enable successful fork,
posix_spawn, shell pipeline or process-pool cases. Likewise documented
unsupported clone3/AUTODISARM cases verify rejection without claiming Linux
feature equivalence. Root-profile tests do not establish nonroot permission
behavior. Device/special-file, MPI, UTI and XPMEM work are outside this catalog's
initial executable subset.

## How broad work stays reviewable

An executor receives its active packet, selected case objects and exact
capability/input manifests. It writes ordinary fixtures and independent
oracles, inventories unchanged application binaries where requested, and
executes only the authorized modes. It returns per-case implementation and
acceptance status with complete evidence. It does not self-select the next
wave or infer permission to edit a native kernel from a test failure.

For a simple diagnosed defect, an execution packet may authorize one candidate
fix within 15 minutes, two files and 80 changed lines. Preserve the original
failure first. A candidate requires independent review and new source/binary
binding; it never upgrades old coverage. Unsafe/lifetime/ABI/scheduler/transport
problems, ambiguous semantics or larger changes go to Max. Max can investigate
one narrow issue while later independent fixture drafting continues within
reviewed packets. No oracle weakening, broad errno allowlists, hidden retries
or fabricated compatibility successes.

The suite summary must separate logical cases, parameter executions, Linux
reference runs, protocol/unit checks, real McKernel runs, required passes,
failures, blocked cases and not-run cases. It must name the exact accepted
input pair. Missing evidence is not a zero count. Sampled routes are labeled;
strong resource-growth claims require actual per-owner accounting.

After the short deterministic subset is accepted, repeat each case three times
in one OS and once in a fresh guest. Then run ten frozen cycles of the accepted
subset, partitioned into predefined guest batches respecting every case limit
and the 300-second guest bound. Fatal/transport/quarantine attempts always use
fresh guests. One-hour stress, shutdown/resource restoration, multicore/MPI,
production readiness and full Rust/assembly completion remain separate goals.

No new catalog case, new runner or real transport-injection guest is claimed
passing by this planning artifact. Readiness for the executor's model switch
must be declared by root after the above gates have actual retained evidence.
