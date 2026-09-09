# Ultra plan for broad application verification

The catalog now specifies **273 logical cases**, with parameter matrices kept
separate from that count. These are planned specifications, not implemented
tests or passing application results. Four unchanged historically accepted
core modes remain separate regression gates. The executor is Luna or Spark; the user chooses and controls model
switches. Max owns difficult, narrow diagnosis and repair.

The 273 specifications comprise 253 differential guest cases, 13 fault guest
cases, six static/exact-production boundary cases and one bounded
repeatability campaign. Protocol cases are not counted as real application
executions. The family totals are startup 10, memory 24, files 30, threads 17,
futexes 17, signals 18, time 10, processes 20, IPC 16, loaders 8, unchanged
applications 20, numerical work 5, failure phases 12, exhaustion 10 and vector
instruction/state cases 56. One vector case is a static opcode audit; the
remaining 55 require real guest execution. Eleven AVX-512 specifications
remain conditional on guest CPU and enabled xstate support.

Canonical artifacts:

- [`scripts/application-tests/README.md`](../../scripts/application-tests/README.md)
  defines schemas, isolation, independent oracles, evidence and repair limits.
- [`scripts/application-tests/cases.json`](../../scripts/application-tests/cases.json)
  gives each case its operation, independent assertions, capability dependencies,
  argv/mode, resource/time limits, parameters, cleanup and repetition contract.
- [`scripts/application-tests/packets/`](../../scripts/application-tests/packets/)
  contains 97 draft packets, each with one to three cases and exact writable
  files. They authorize drafting only. Runtime remains disabled.
- [`scripts/application-tests/draft-queue.json`](../../scripts/application-tests/draft-queue.json)
  orders every catalog case exactly once: the original packets 001–007 first,
  then 008–097 grouped by family and dependency order. Its release remains
  pending root validation and the verified drafting handoff checkpoint.
- [Host review](ultra-host-review-20260909.md) and
  [test inventory](ultra-test-inventory-20260909.md) provide review background.
  Supply only relevant excerpts with an active packet, not the complete history.

## Drafting handoff and execution gates

The [handoff gates](ultra-handoff-gates-20260909.md) are authoritative. The
requested next phase is bounded fixture/oracle drafting. Before that handoff,
finish focused signal/XSAVE/fault-dispatch/futex/clone checks, the native module
and all four image profiles, then replay all four unchanged core modes and
both control ABI regressions on one exact current module/image pair. Run the
new independent ordinary signal/futex fixtures, retain precise blocked-feature
reasons, validate the catalog and bounded starting context, and push/verify the
exact source/evidence/context blobs on GitHub. Root then announces the explicit
draft-only handoff. It does not require a completed new runner or runtime fault
injection before the faster model can draft tests.

Before releasing an **execution-enabled** packet, also:

1. Pass actual transport-failure guest verification: accepted RET with hard
   prepublication failure, notification failure after publication, recoverable
   full queue and permanent queue pressure. Require phase-specific memory/
   ownership evidence, bounded host waiter behavior and no stale publication.
   The 44 host protocol tests alone do not satisfy this execution gate.
   Injected EAGAIN is not physical ring saturation; retain both distinctions
   from the [runtime fault plan](ultra-transport-fault-runtime-plan-20260909.md).
2. Implement/review the repository runner, input/capability/result validators,
   pinned-guest Linux reference and dual-stream supervisor. Prove watchdog and
   QMP pause/resume behavior independently. The current catalog's commands name
   proposed interfaces; missing programs and placeholders cannot be executed.
3. Freeze an exact input manifest and capability manifest. A feature supported
   on the historical baseline is not automatically verified on modified inputs.
   Fork, extended loader, external signal, clock, IPC, accounting, exhaustion
   and multicore gates need their own explicit evidence or remain BLOCKED.
4. Review one small packet's frozen independent oracles and exact writable
   files. A release must explicitly identify that active packet, its mode
   and unresolved gates. Do not describe the entire 273-case list as runnable.

## Breadth and execution order

| Wave | Coverage | Acceptance condition |
| --- | --- | --- |
| 0 | Four original core modes and original controls | Same changed-source-bound module/image pair; original outputs, routes and lifetime assertions retained. |
| 1 | Startup/argv/environment/streams; allocator and VM contracts; regular-file boundaries/errors | Fixed bytes/errno/relations plus same-binary pinned-Linux reference and real McKernel provenance. |
| 2 | Thread/TLS/mutex/barrier/condition-variable and futex contracts; signal/protection faults; time APIs | Individual capability prerequisites accepted; actual thread IDs, signal status and timeout semantics established. |
| 3 | Unchanged cat/wc/hash/copy/sort/head/tail/uniq; deterministic numerical work; gzip/xz/zstd | Exact pinned ELF/options/DSO closure; independent byte/hash/arithmetic/decode oracle; each executable directly launched. |
| 3V | SSE through AVX/AVX2/FMA, guarded vector memory, crypto instructions, x87/MXCSR, live XMM/YMM state; conditional AVX-512 | Both-engine CPUID/XCR0 gates, exact opcode proof, independent scalar/math oracle, and actual transition/owner evidence; physical host flags never enable a guest feature. |
| 4 | Process fork/COW/exec/wait/pipes; IPC readiness; PIE/static/dlopen/C++/DSO TLS; shell pipeline | All child identities remain in McKernel; fork/loader/IPC support explicitly accepted first. |
| 5 | Every owner-loss phase, guarded user-copy, capacity/failure/zeroing and repeatability | Real fault hooks plus accounting; precise normal retirement versus stable quarantine; fresh fault guest every attempt. |
| Later | Two McKernel CPUs and routing, NUMA, MPI and long campaigns | Separate topology/resource/feature gates; never infer from four Linux vCPUs or one-CPU pthread success. |

The first seven packets cover startup records, allocation, closed-fd errors,
basic futex negatives, repeated/nested alternate stacks, unchanged cat, and
vector feature discovery plus live XMM/YMM preservation around raw syscalls.
They are intentionally draft-only while execution infrastructure and runtime
gates are reviewed. New execution packets can select any dependency-satisfied
case, but remain limited to three active logical cases. Parameter vectors are
explicit subordinate runs, such as sizes 1/4095/4096/4097/65553/1048576 or
thread counts 2/4/8; do not multiply the feature count by those vectors.

The remaining 90 packets complete the full breadth, rather than stopping after
the initial 20 cases. Dependency order applies both between packets and within
their ordered case lists. A declared runtime prerequisite can remain blocked
while its fixture/oracle is drafted; missing semantic expectations are recorded
explicitly and sent for Max review. The queue never turns feature absence into
test acceptance.

Process capability deserves an explicit split: current non-null CREATE_PPD
rejects the ordinary fork adoption path. A reviewed negative rollback probe
can test that documented restriction; it cannot enable successful fork,
posix_spawn, shell pipeline or process-pool cases. Likewise documented
unsupported clone3/AUTODISARM cases verify rejection without claiming Linux
feature equivalence. Root-profile tests do not establish nonroot permission
behavior. Device/special-file, MPI, UTI and XPMEM work are outside this catalog's
initial executable subset.

The [vector plan](ultra-vector-test-plan-20260909.md) freezes feature masks,
register observation rules and arithmetic semantics. AVX256 means 256-bit YMM
operations; AVX2 adds packed integer operations. The observed physical Intel
Core i7-1065G7 feature list includes AVX-512, but the historical TCG guest's
reported xstate mask `0x21f` lacks its register components. Optional AVX-512
execution stays BLOCKED until each current guest supplies the required CPU
bits and XCR0 `0xe6` components. Extended signal-frame ABI and first-entry
zero-state observation are separate gates. Existing native module no-SIMD
checks remain unchanged, and all decoded unexpected kernel vector/x87/MMX
instructions must fail the broader static audit.

## How broad work stays reviewable

An executor receives its active packet, selected case objects and exact
capability/input manifests. It writes ordinary fixtures and independent
oracles, inventories unchanged application binaries where requested, and
executes only the authorized modes. It returns per-case implementation and
acceptance status with complete evidence. Root can supply a reviewed sequential
draft queue; after completing a packet, the executor moves to the next listed
packet without repeated user permission, receiving only that packet's bounded
context. It must not invent another wave or infer permission to edit a native
kernel from a test failure. A queued draft packet never enables runtime.

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
passing by this planning artifact. Root declares the drafting handoff after its
specific retained gates pass. Execution gates remain visible and blocked until
their own evidence is accepted; draft readiness does not convert them to PASS.
