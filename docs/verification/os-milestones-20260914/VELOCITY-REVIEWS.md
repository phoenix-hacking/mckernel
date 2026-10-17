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
- Next full review target: `2026-10-17T13:55:00Z` (06:55 America/Los_Angeles).
- Next review latest target: `2026-10-17T14:25:00Z`; preserve healthy operations.
- Last included-usage observation: 12%; existing campaign stop remains 97%.
- Current intervention: repair the pre-boot QMP socket pathname failure, retain
  the original attempt, establish required retirement and prepare a fresh release.
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
