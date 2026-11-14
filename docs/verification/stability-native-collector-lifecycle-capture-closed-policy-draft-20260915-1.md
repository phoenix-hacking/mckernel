# Native lifecycle capture-closed policy draft 1

Date: 2026-09-15
Task: `M02-C-lifecycle-capture-closed-policy`
Disposition: `POLICY_DECISION_DRAFT_ONLY`

This additive normative decision resolves capture-closure behavior left open by
the corpus draft and contract addendum. It changes no historical record and
releases no source, fixture, model, compiler, native, application or production
acceptance. A separately reviewed source packet must supply independent exact
input and full-output literals before materialization.

## Normative decision

Whole-document schema validation remains first. It validates operation count,
contiguous identifiers, operation names and arities, argument scalar types and
ranges, key shapes/domains, and required/unused argument positions before any
transition runs. A failure there remains a harness exit 2 with empty streams and
zero model invocations; `CLOSED` never masks a schema error.

During transition execution, the first `CAPTURE_END` is irrevocable. It sets
`ended=true` even when the resulting capture is incomplete. It attempts the one
ordinary `CAPTURE_END` event under the existing event-capacity and counter rules,
then evaluates retained live rows, reservation state and sticky fault state. Its
operation status is `OK`; completeness is represented only by the control row's
`incomplete` Boolean. Event loss or attempt overflow can make that closure
incomplete but cannot reopen it.

After that first end, every later schema-valid operation returns `CLOSED`. This
includes a second `CAPTURE_END`, `LAUNCHER_LOSS`, `TEARDOWN_FAIL`, and every
registry/reference/retirement operation. The closure check occurs before capture,
slot, generation, application, process or exec identity matching; before active
TID, reference or authority checks; before retained capacity; and before
lifecycle-state checks. Thus a schema-valid wrong-key operation after end returns
`CLOSED`, not `KEY`, `IDENTITY`, `REF`, `LIMIT` or `STATE`.

A `CLOSED` result emits no event and attempts no event reservation. It preserves
all process and thread rows, reference counts, VM/main-storage flags, authority,
terminal tuples, retained-event rows, retained count, lost count, overflow flag,
reservation count and attempt count. It preserves `ended=true` and irreversibly
sets `incomplete=true`. Consequently, a second operation after an otherwise
complete first end changes only `incomplete` from false to true; after an already
incomplete first end, the entire control row is unchanged. Subsequent `CLOSED`
results remain idempotent except for their own output status rows.

There is no non-closing first-end outcome. A first end with live rows, a retained
reservation, event loss, counter overflow, launcher loss or teardown failure in
its prior history is an incomplete but permanently closed capture.

## Required literal witnesses before source release

The separately reviewed materialization packet must contain independent compact
input and full output literals for all six witnesses below. No expected output may
be imported from either model.

| Witness | Required operation suffix | Required second status | Required post-second delta |
| --- | --- | --- | --- |
| `end-after-complete-end` | complete state; `CAPTURE_END`; `CAPTURE_END` | `CLOSED` | only `incomplete: false→true` |
| `end-after-incomplete-end` | live or sticky-fault state; `CAPTURE_END`; `CAPTURE_END` | `CLOSED` | no state/control delta |
| `operation-after-end` | complete state; `CAPTURE_END`; schema-valid registry operation | `CLOSED` | only `incomplete: false→true` |
| `wrong-key-after-end` | complete state; `CAPTURE_END`; schema-valid wrong-capture operation | `CLOSED` | only `incomplete: false→true`; proves precedence over `KEY` |
| `launcher-loss-after-end` | complete state; `CAPTURE_END`; `LAUNCHER_LOSS` | `CLOSED` | only `incomplete: false→true`; no loss event |
| `teardown-fail-after-end` | complete state; `CAPTURE_END`; `TEARDOWN_FAIL` | `CLOSED` | only `incomplete: false→true`; no teardown event |

Each literal review must account for exact operation IDs, event attempts and
retention, sorted registries, all seven control fields, both model outputs and the
oracle. It must separately prove the first-end complete and incomplete cases,
the closure-before-semantic-precedence rule, zero second-event attempt, and sticky
incomplete behavior. Any different policy requires a new additive reviewed
decision rather than silently changing this record.

This policy freezes only post-closure precedence and effects. TID reassignment,
phase/domain permission, alias classification, reference/authority interaction
and the other five lifecycle decision families remain unresolved.
