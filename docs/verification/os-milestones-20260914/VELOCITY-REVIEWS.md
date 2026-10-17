# OS velocity supervision reviews

User requested 30-minute to one-hour reviews and continuous concrete steering
from the interactive chat. Read [VELOCITY.md](VELOCITY.md) for the method.
Preserve completed entries; append new observations and update only this cursor.
This file describes supervision, not OS acceptance or execution authority.

## Current review cursor

- Supervisor chat: `01a1479e-a9c2-7340-8d88-4313fab04738`; supervision goal active.
- Engineering campaign: `01a149eb-f950-7f13-95a2-59dfc2918d49`; sole runtime/Git owner.
- First baseline recorded: `2026-10-17T13:26:00Z`.
- Baseline interval: `2026-10-17T12:52:42Z` to `2026-10-17T13:24:54Z` (32m12s).
- Last full review: `2026-10-17T13:55:47Z` (interval 30m53s after baseline end).
- Next full review target: `2026-10-17T14:25:00Z` (07:25 America/Los_Angeles).
- Next review latest target: `2026-10-17T14:55:00Z`; preserve healthy operations.
- Last included-usage observation: 13%; existing campaign stop remains 97%.
- Current intervention: reconcile the TLS protocol failure and align actual
  collector/manifest stream accounting before a fresh released attempt; validate
  lifecycle ABI records through the actual serializer/parser before runtime.
- Current invocation independently accepted diagnostic guests: 3 (signal,
  calloc, file-write/read). Formal acceptance and broad engineering ranges unchanged.
- No new monitor script, OS timer, engineering dispatcher or workload was started.

## Baseline review — 2026-10-17 13:26 UTC

| Measure | Observed result |
| --- | --- |
| Signal guest launch attempts | 1 |
| Actual guest boots / payload executions | 0 observed / 0 observed |
| New guest passes / observed kernel failures | 0 / 0 |
| Infrastructure launch failures | 1: QEMU rejected the QMP socket pathname as exceeding its 108-byte limit |
| Newly integrated kernel repair with actual-body regression | 0 confirmed in this interval |
| Formal acceptance / new milestone-condition closure | No increase established |
| Execution infrastructure | Mount-order correction, failed-staging retention, fresh retirement observation and archival cleanup advanced; these remain separate from kernel behavior |
| Next-ready cases | Signal, calloc and file-write/read inputs have strict manifests; no new guest pass from these preparations |

The original native/image artifacts remain available. Cleanup independently
accepted at 13:19:27 UTC; final signal execution review completed at 13:21:03;
attempt files appeared around 13:22. No material avoidable admission queue is
demonstrated for that transition. The exact QEMU launch/exit timestamps were not
established by this narrow review. QEMU stderr is 370 bytes; serial/debugcon and
QEMU stdout are empty. The failure precedes boot and proves no signal defect.
Failed guest-owner retirement was not yet established at the observed snapshot.

Useful separate results: mount-order checks passed 10 tests; retirement/cleanup
source review reports 23 tests; failed-output staging retention passed 17 tests.
The lifecycle diagnostic tool passed 26 injected actual-main scenarios, which
prove tool behavior rather than native shutdown. Callee/kernel acceptance is
not inferred from fixtures. Preserve original per-case results and contracts.

At 13:25 the campaign's own defect triage found no genuinely ready bounded new
M03/M02/fork-activation patch: M03 lacks production lease/generation authority,
M02's relevant descriptor tests already pass, and fork activation lacks the
end-to-end caller/ACK contract. Do not repeat that audit or invent a tiny patch
to fill workers. Prepared payloads and the actual socket-path defect are ready
work; extra local compiler jobs also require available shared capacity.

**Adjustment for the next interval:** delegate the narrow endpoint/path-length
correction and independent regression review while the dispatcher reconciles
the failed owner. Check complete encoded UNIX socket paths, including generated
suffixes, before consuming another guest release. Use a fresh output/attempt and
appropriate new release after correction. Reuse current942 and the ready next
payloads; do not rebuild Linux or repeat historical preparation for this defect.
Instruction `20261017T132606563155Z-8691d9cd5d05439982efde1d086a58e9` was queued
through the existing launcher. Confirm delivery in its receipt, not by replaying.

Sources read: launcher state and selected current console/lane messages;
HANDOFF/CURRENT checkpoint374; evidence records
`scratch22-image-mount-order-correction-20261017-1.json`,
`scratch22-image-reconciliation-source-review-20261017-1.json`,
`scratch22-authority3-image-cleanup-result-review-20261017-1.json`,
`native-lifecycle-probe-actual-main-pass-20261017-1.json`,
`memory-calloc-zero-current942-staging-20261017-1.json` and
`file-write-read-current942-staging-20261017-1.json` under `../evidence/`.
No speed multiplier can be calculated from a zero guest-pass baseline; compare
raw outcomes, time to first payload result and avoided repeated failures first.

## Review 1 — 2026-10-17 13:55:47 UTC

Interval: `13:24:54` to `13:55:47` UTC, 30m53s. The previous baseline was 32m12s;
these short windows and a zero guest-pass baseline do not establish a 2x/3x ratio.

| Measure | Previous baseline | This interval |
| --- | --- | --- |
| Launch attempts | 1, failed before boot | 4: signal, calloc, file, TLS |
| Independently accepted actual McKernel diagnostics | 0 | 3, each with accepted retirement |
| Accepted kernel failure | 0 | 0; TLS is a protocol/evidence failure under reconciliation |
| New integrated kernel implementation repair | 0 confirmed | 0 confirmed |
| New execution-infrastructure repair | Mount/stager/retirement work | QMP endpoint admission, integrated and independently reviewed, 76 tests PASS |
| Formal application/production/language acceptance | 0/273, 6/130, 0/7 | Unchanged |
| Included weekly usage reported by existing launcher | 12% | 13%; stop remains 97% |

**Verified runtime gains:**

- `signal.mask-restore`: independently accepted at 13:39:37 UTC. Exact 40-byte
  stdout `handled=1 observed_blocked=1 restored=1\n`, empty stderr, exit0.
  Covers the original selected two-bit oracle, not arbitrary whole-mask behavior.
- `memory.calloc-zero`: independently accepted by 13:43:58. All six frozen size
  lines match; actual McKernel scheduling, streams, process/procfs release and
  host/container retirement joined. One diagnostic, not six accepted cases.
- `file.write-read`: independently accepted at 13:48:31. All six sizes, including
  1 MiB, pass write/seek/read/compare/fstat/EOF. Reopen and checked close/unlink
  are not covered. Complete owner retirement independently accepted.

The accepted decisions are additive result-review records under `../evidence/`:
`signal-mask-restore-current942-result-review-20261017-2.json`,
`memory-calloc-zero-current942-result-review-20261017-1.json` and
`file-write-read-current942-result-review-20261017-1.json`. Keep raw results'
pending-review fields and original failures unchanged. The correction, plan and
initial review protocol were pushed/fetch-verified at `6ea3b964`; subsequent
guest releases advanced through `ba88a7e9`, `09205941` and `2b68c7ad`.

**Handoffs:** acceptance to next command-file start proxy was 2m19s, 1m58s and
2m03s for signal→calloc→file→TLS. All are below the five-minute scheduling
target. They include required reviews, source/HEAD and live admission; the
observations do not establish how much of each interval is avoidable. Successful
owner invocations took about 33-34 seconds. No unchanged kernel/image rebuild
was needed for these diagnostics.

**Failures and corrections:** the QMP fix preserved the original 132-byte path
failure and rejects endpoints above 107 encoded bytes before side effects. Its
first integrated test exposed a TMPDIR-dependent fixture and an outer shell
status masking the test failure; both are preserved. Final tests use the actual
constructor/source binding and real subprocess status: seven new plus 69 existing
tests PASS, with independent source/execution review. The fresh endpoint is 92 bytes.

TLS launched at 13:50:34; its outer owner command exited 1 after 34.423s. Initially
only `docker command failed: start` was available, so no inner outcome was
classified. By 13:53 the dispatcher had captured the inner result and owner
archive: the evaluator reports `stream accounting`, with ND_FUTEX declaring 4096
against the manifest's 1024. This supersedes any inference that Docker's outer
error proves failure to boot. Do not assign a TLS kernel failure or pass from
that error, change original captures, or admit another runtime before required
retirement/evidence reconciliation. Source: existing TLS dispatch captures and
13:53:39 dispatcher report; final independent disposition remains pending here.

**Useful parallel implementation:** lifecycle collector and parser progressed
while guests ran; staged artifacts have 60 members including the bound probe.
Actual producer→serializer→parser testing found the pinned ioctl ABI has
Running=5 and Booted=3, contrary to the earlier parser's Running=3. The original
bytes/failure are retained; correction explicitly rejects 3, and 13 focused tests
pass including real retained probe output through the unchanged C serializer.
This is offline tool integration, with no native shutdown/restoration credit.
Mutex preparation reused valid compile/reference output but found attr=NULL
versus the catalog's 262144-byte stack requirement; its admission remains held.

**One adjustment for the next interval:** before freezing a new collector mode,
run one cheap actual producer/serializer→actual consumer positive and relevant
boundary negative. Apply it now to TLS stream-limit agreement, while completing
the lifecycle enum correction's independent review. Keep original oracles and
allowed bounds; don't make a failed real capture pass by rewriting it. Resolve
the mutex stack contract explicitly and prepare a fresh permitted variant only
after its decision. Use the freed runtime lane for the next genuinely ready
case; no blind retry, unchanged image rebuild or speculative M03 audit.

Supervision instruction `20261017T135326429784Z-2c936ba144b246be9cdf83a98dcafe2f`
was accepted by the server at 13:53:26 UTC. Dispatcher plus source/test and review
lanes remain active. Next review is 14:25 UTC. Independent judgment retains
M02 50-70%, M04 30-50%, M08 55-75%; results strengthen runtime evidence within
these broad low-confidence bands. Other milestone estimates remain as previously
reported. No whole-OS score or formal milestone closure is inferred.
