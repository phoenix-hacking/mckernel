# Unattended M14/M15 harness contracts

This is an implementation and adoption reference. `CAMPAIGN.md` remains the
sole human plan and handoff. The canonical acceptance ledger remains
`docs/verification/m14-m15-closure-progress.json`.

The harness must connect a remaining original check to a finite action, its
existing owner, the required evidence, and a decision when that action fails or
stops producing evidence. A model turn, heartbeat, new attempt identifier or
published status is not a closed acceptance check.

The production objective is the remaining original M14/M15 work. The controller
derives the remaining-work list from the canonical ledger and supplies concrete
open IDs when asking the Root to select its next action. Recorded dependencies
and execution profiles explain that work; they do not themselves grant readiness.
The Root must execute eligible engineering, qualify the actual result and continue
to the next original check. Repeated harness changes, inventory passes and status
updates cannot substitute for that sequence. M14 final acceptance precedes M15
final acceptance, while independent admitted preparation can proceed in parallel.

## Three independent responsibilities

| Responsibility | Implementation | Evidence of success |
| --- | --- | --- |
| Receive instructions and publish status through engine pauses or exits | `os_goal_mailbox_monitor.py`, mailbox user service | Current observer identity and lease, successful poll tied to that observer, verified publication of the actual status bytes |
| Own each future ordinary HOST operation through bounded completion and cleanup | `os_goal_operations.py` | Original operation journal, actual wait result, positive owned-family closure and closed captures; reservations remain held if custody is unknown |
| Keep the existing Root working toward original closure | `os_goal_progress.py`, `Campaign.poll_progress()` | A current original-check target, matching evidence, a durable review request delivered to the same Root, and a separately observed decision or closure |

These components do not issue account, source, native or resource authority.
Functional McKernel OS/apps and Rust/allowed assembly migration remain the scope;
security testing is excluded.

## Mailbox observation

The mailbox has its own systemd user service, lifetime lease, PID/birth identity,
instance identifier, watchdog and bounded stages. Polling and status publication
have separate outcomes. A failed status write cannot consume a queued instruction.
Restarting the observer preserves cursors, sources, pending messages and receipts.
The replacement observer performs an immediate current-instance poll, then
retains the existing normal cadence and failure backoff.

Use these commands from the adopted workstation checkout:

```sh
python3 -B scripts/os_goal_service.py start-mailbox
python3 -B scripts/os_goal_service.py status-mailbox
```

`MAILBOX_START_REQUESTED` means systemd submission, not readiness. Verify the
`monitor`, `mailbox` and `publication` readiness stages. Publication requires a
remote readback matching the current local status SHA-256. A stopped or paused
engine can still have healthy observation. A live manual engine is identified
only by its explicit watcher/worker lineage, never by absence of a guardian.

A positively identified old guardian that still polls retains ownership until
its normal transition. An unknown held guardian lease blocks a competing reader.
`stop-mailbox` affects only the observer. The observer neither starts a model nor
resumes a goal. New supervised launches require a current successful mailbox
poll when mailbox configuration is present; `--mailbox-monitor required` makes
that explicit. `--mailbox-monitor off` is an intentional opt-out, not an unattended
readiness claim.

The observer's code checkout and the campaign data checkout may be different
worktrees of the same repository. Before publication, the observer resolves the
saved controller's absolute `repo` and verifies its Git common directory matches
the shared runtime directory. That checkout supplies the current working-tree
ledger, checkout HEAD and closure-target evidence; the pinned observer checkout
continues to supply code and mailbox configuration. A missing or foreign saved
checkout produces an explicit publication error without stopping authenticated
instruction reception. Only a genuinely absent controller state uses the
observer checkout, labelled `OBSERVER_CHECKOUT_NO_CONTROLLER`. This binding
does not prove a live controller or grant source execution authority.

Status publication retains its existing ten-minute cadence and failure backoff
across observer replacement. A fresh successful mailbox poll can therefore
precede full publication readiness. The new-engine startup check requires the
monitor and mailbox stages; unattended monitoring requires the publication stage
as well. Inspect the reported next due times instead of clearing durable
cadence, pending intents or receipts.

New controller instruction receipts bind the exact text SHA-256, verified source
ID, Root thread/turn, worker/server identities, invocation and durable pre-RPC
attempt. A legacy receipt is historical acceptance only. Uncertain mutating
delivery stays unresolved and is never automatically replayed. Acceptance by the
controller remains distinct from completion of the requested work.

## Closure decisions

Closure control is enabled by `--stop-after-m14-m15`, or explicitly by
`--progress-control`. Defaults are a 20-minute progress checkpoint and a decision
after 40 minutes without a newly verified original closure, newly qualified
matching evidence, or a resolved matching blocker. Checkpoint and stall intervals
must be positive, finite and ordered.

The controller immediately asks the same active Root to choose a target when
none is selected, correct an invalid target, respond to a concrete ordinary
failure, and choose the next eligible check after a closure or an exact blocker
disposition. Actual dispatch waits for the existing hard-stop guards and preserves
a matching protected bounded operation. The finite remaining-work snapshot includes
every open original ID, parent, complete `done_when` condition, recorded execution
profile and dependencies. The review names a few concrete open candidates from both
milestones with admission explicitly `UNASSESSED`; the full list remains in the
canonical ledger. When all original checks are verified but acceptance is still open,
the next action is the original acceptance review. It cannot invent new checks.

The existing Root submits a plan through the checked CLI. This minimal example
is a plan with no claimed readiness or qualified evidence:

```json
{
  "schema_version": 1,
  "original_check": "M15-F02-complete-ABI-behavior",
  "owner": "existing executor owner",
  "next_action": "Identify and fix the next missing required executor behavior",
  "input_bindings": {},
  "evidence": [],
  "operation": null
}
```

```sh
python3 -B scripts/run_os_goal.py --set-closure-target /absolute/path/target.json
```

The CLI validates the original ID and immutable completion condition, then queues
the plan for the current controller invocation. The controller applies it; the
CLI does not edit `state.json`. A stale invocation is refused, and multiple queued
plans have deterministic supersession. Each request identity binds its durable
sequence and plan digest. Repeating the latest pending or currently applied plan
is idempotent; returning to plan A after independent plan B creates a new request,
preserves the earlier records and earns no semantic progress. A plan grants no
execution or acceptance.

Evidence references are repository-relative JSON files with exact SHA-256 values.
Each qualified-evidence, blocker or ordinary-failure adapter binds the original
`done_when` SHA-256 and the exact relevant input digests. A passing HOST process
does not produce a qualification or close a whole original condition. The source
and matching test/evidence must establish that original condition at its stated
scope. The frozen 156 counted IDs, parentage and completion conditions are checked
before both progress projection and the final M14/M15 completion checkpoint.

Missing engineering inputs are work to perform. The startup contract and each
closure advisory require deriving actual source/header/caller/ABI contracts,
fetching pinned dependencies and SDKs, installing required packages under actual
permissions and admission, and implementing real missing adapters/providers while
preserving the original supported behavior. This includes the future ordinary
HOST runner's actual admission/provider adapter; it is our code work when needed,
not a request for a user-authored inventory or permission to use a fake provider.
The owner then runs the affected verification and qualifies its actual scope.

A proposed blocked receipt must contain this exact additional `resolution`
object; values below describe fields to fill from the actual attempt:

```json
{
  "classification": "engineering",
  "attempted_action": "The exact attempted acquisition, installation or implementation action",
  "outcome": "Its actual recorded outcome",
  "missing_input": "The exact input still required",
  "supplying_owner": "The existing owner responsible for obtaining it",
  "evidence": {"path": "repository-relative-attempt.json", "sha256": "exact SHA-256 of that file"}
}
```

`classification` is `engineering`, `external` or `actual_hold`. The referenced
JSON either is the actual `mckernel-host-operation-v1` result with a matching
`spec.closure_target` and payload `PASS`/`FAIL`, or has schema
`mckernel-input-resolution-attempt-v1`, the same `original_check`,
`condition_sha256` and nonempty `input_bindings`, the same five descriptive
resolution fields above, and status `completed`, `failed` or
`refused_by_actual_hold`. An attempt record represents the real producer's
recorded action and outcome; creating a JSON claim does not perform that action.

An engineering classification produces `INPUT_RESOLUTION_REQUIRED` and a finite
get/install/derive/implement action. A missing, mismatched or unsubstantiated
attempt also remains resolution work. Only matching concrete evidence of an
absent external artifact/access/hardware or an actual hold can produce
`BLOCKED_BY_MATCHING_RECEIPT`, with its exact input and supplying owner. A
`resolved` disposition requires a matching completed resolution result; changing
the disposition text after a failed attempt earns no progress. Neither an attempt
nor a resolved input closes an original condition or clears an actual hold.

One unchanged cause produces one review request. The controller revalidates its
target, inputs, failure and operation protection before dispatch, so obsolete
instructions are cancelled. User instructions take priority. Actual stops, holds,
unknown delivery and non-active goals prevent steering. The pre-RPC intent is
durable before a request reaches the existing Root; uncertain acceptance is not
retried. A positive refusal before RPC can be retried without pretending it was
delivered.

An accepted review is not a completed repair. If the cause remains unresolved
for another stall interval, one bounded follow-up requests a concrete owner
action. Further unchanged retries stop, and the unresolved owner action and its
age remain visible. Qualified progress, a resolved cause or a matching protected
operation supersedes stale advice. No amount of generic activity resets the
semantic progress clock.

A long operation needs matching original-input evidence and an originally
declared deadline of at most 24 hours. That protects legitimate bounded work
from a premature stall review. It does not establish fresh liveness indefinitely
or extend itself through new attempt names. `FRESH_DECLARED_HEALTH` means the
matching receipt's observation is at most 120 seconds old;
`DECLARED_BOUNDED_PROTECTION_ONLY` means the original declaration still protects
its finite operation but does not prove current process liveness. The first
deadline remains pinned to the original check and exact input bindings: changing
the operation name, attempt ID or deadline cannot renew it. A new operation must
provide its actual new matching input/admission bindings and durable receipt.
Expired, missing or mismatched proof
returns the operation to unknown status and a concrete review decision.

## Future ordinary HOST operations

`OperationRunner` is a callable execution API for future operations. It does not
take custody of old retained operations, retrofit native wrappers or release old
UNKNOWN reservations. Its CLI offers `validate`, `status` and `reconcile`; there
is deliberately no JSON flag that grants execution authority.

The existing owner integrates it with its reviewed, read-only admission provider:

```python
from os_goal_operations import OperationRunner

runner = OperationRunner(
    journal_dir,
    admission_provider=current_root_admission,
    repo=repo,
)
result = runner.run(exact_operation_spec)
```

`current_root_admission` above is an integration point, not a supplied global
grant. It must obtain the actual current account, source, permission and ownership
facts from their existing authorities, plus the fresh measured resource snapshot.
It receives the exact parsed specification, phase (`execute` or `cleanup`), active
charges and `deadline_mono_ns`, and returns a bound `FreshAdmission`. That return
value includes the exact operation ID, specification SHA-256 and phase, paired
UTC/monotonic observation clocks, and authoritative evidence references for all
four keys `account`, `source`, `permission` and `ownership`. Its resource snapshot
contains the complete **external** retained inventory; the runner adds every
unresolved journal charge itself, including the provisional operation reservation.
The provider may inspect the supplied active charges but must not duplicate them
in that external inventory. Boolean fields cannot substitute for this trusted
provider or its bound evidence. The unit-test
provider is fake and must never be used on the workstation. If the actual provider
cannot supply those facts, the operation remains unstarted or held; it does not
infer authority from status text or a source-only GO.

The versioned specification requires an exact canonical original ID, owner, ordered argv, executable and
input hashes, exact environment and ulimits, cwd, declared resources, execution
and cleanup timeouts, process-group ownership and expected exit codes. Validation
precedes payload effects. Environment and ulimit row order is semantically
irrelevant; duplicate or missing fields are rejected, while changed values or
ordered argv produce a different specification identity requiring fresh review
and admission. A closure target must match the canonical original condition, and
every claimed closure input digest must occur in the actual execution inputs.
Input hashes are checked again after admission. Both admission and resource
clocks are checked after the durable start/cleanup intent, immediately before
effects. Provider and capture-finalizer waits occur outside the short accounting
transaction lock; current journal charges are revalidated before execution.

The default Linux backend owns a new local supervisor and its child family. The
supervisor is a child subreaper: it joins the payload and adopted descendants,
including descendants that create another session, until `waitpid` positively
reports `ECHILD`. Only its private invocation-bound closure receipt, the original
supervisor wait, process-group absence and closed captures together establish
local family closure. Ordinary foreground timeouts can terminate and join within
the original cleanup budget. A killed supervisor or detached child beyond that
budget leaves missing proof and retained custody. Group signals require the
explicitly created original group and its exact still-unreaped leader identity.

This local proof does not close an external service, container or other owner to
which a command hands work. Such operations need a separately reviewed original
owner's custody and resource accounting; the default backend supplies no generic
external-resource closure. The admission provider must preserve those separate
charges and refuse unsupported handoffs.

The journal separates payload outcome, custody and resource reservation:

| Payload | Custody | Reservation | Meaning |
| --- | --- | --- | --- |
| `NOT_STARTED` | Positively closed | `RELEASED` | Admission failed before the payload; its own provisional validator charge is closed |
| `PASS` or `FAIL` | `CLOSED` | `RELEASED` | Actual payload result retained; original process family and captures positively closed |
| Any, including `PASS` | `HELD_UNKNOWN` | `HELD` | Some original ownership, worker, wait, stream or family outcome remains unresolved |

The original payload error survives secondary cleanup errors. Cleanup and lock
acquisition have a finite budget within the original reservation. A timed-out
admission/finalization worker remains durably charged; no new operation can pile
up additional workers behind it. A process restart may mark abandoned bookkeeping
held, but cannot replay, signal, expire or release it. `OperationJournalError`
retains the original result in `.record` if a final journal write itself fails,
with its reservation conservatively `HELD` and `release_committed=False`.

HOST affinity and per-process resource limits are applied to the launched child.
`RLIMIT_AS` is per-process, not a cgroup aggregate memory limit. Aggregate HOST
planning/admission still includes measured controller overhead, all retained
charges and the original campaign ceilings. A workload requiring an enforced
family-wide memory limit needs its reviewed containment in addition to this API;
do not describe the planning reservation as such an enforcement mechanism.

## Adoption and verification

Publishing this source does not change a running workstation process. The
existing Root adopts the reviewed commit through its normal source transition,
preserving the current Root, credit ledger, live owners and all actual holds.
Do not replace a healthy controller, mutate its live state or restart work merely
to load this change. The mailbox observer can be started independently after its
source is adopted; closure control is loaded at the supported controller transition.

When the current working tree has ongoing source changes, the existing Root can
start only the mailbox component from a clean detached worktree at the exact
reviewed commit. Use the original repository's normal `git worktree` operation,
verify the shared Git common directory and the exact observer HEAD, then run
`start-mailbox` and `status-mailbox` there. Do not run engine or guardian start,
replace the active checkout, or edit its saved state as part of observer
bootstrap. The saved controller checkout remains the publication source. The
`status-text` manual-preview command is not part of this isolated bootstrap.

Before treating the installation as unattended-ready, observe current-instance
polling and publication, submit a harmless exact instruction and verify its
controller receipt, apply a real finite target, and observe the next automatic
checkpoint/decision. The first new HOST use must have the real reviewed admission
provider and show a complete original operation journal. Retained operations and
genuine external blockers remain explicit owner work.

The dedicated `OS goal unattended reliability` workflow checks the exact PR head,
not a stale merge or default-branch checkout. It exercises fake service/RPC paths
and bounded harmless child processes, and fails on errors, zero loaded tests,
skips or expected-failure substitutions. It includes the current retained-owner,
transport, resource, mailbox and controller suites. Two older recovery modules
(`test_os_goal_recovery` and `test_os_goal_timeout_recovery`) already fail at the
unchanged source baseline (21 failures and one error across 32 tests) and are not
represented as passing by this gate. Their historical generic-restart expectations
do not replace current owner-retention tests.

The full-project `Final push completion tracker` remains a separate check of
the broader project. Its full unittest discovery now stops at the
first failure so a concrete traceback survives its job budget. CI restores both
the vendored IHK source and a separate pinned Git-history checkout in
`RUNNER_TEMP`, exports `MCKERNEL_IHK_HISTORY`, and explicitly retains that input
through the isolated contract launcher. Workflow regressions exercise the actual
shell argument boundaries, failed-restoration behavior and isolated environment.
These repairs do not declare the historical submodule-only authority consumers
compatible with the current vendored layout; any remaining failures must be
resolved without changing frozen source identities or skipping the full gate.

Automated tests establish these exercised contracts. Workstation adoption,
actual provider admission, service availability and an unattended production
observation remain separate evidence; neither a green check nor a PR guarantees
every future milestone will close.

## Sequential dispatcher and measured closure velocity

The sole Root dispatcher is pinned to GPT-6.1 Sol with **max** reasoning by default;
model preflight checks the actual app-server catalog. No workstation model choice
is proven by publishing a GitHub commit. The dispatcher gives each *eligible*
existing child owner a finite original-check assignment via the supported
`followup_task` route: exact original ID/unchanged completion contract, smallest
real code or input repair, focused test, evidence reference, and Root handoff.
Use disjoint owners in parallel within the current original milestone. Do not
replay a held or uncertain operation, interfere with healthy retained work, or
move new closure assignments to M15 before M14's original acceptance.
After M15, continue the already authorized full OS milestone goal in its
recorded sequence, unless an invocation explicitly requested a two-milestone
checkpoint. This does not change the saved goal identity.

The progress observer records **new** canonical binary original-check 0->100
transitions, never the initial baseline or partial evidence, in a rolling
1800-second window. It exposes a **target of 1-5 genuine closures per 30 minutes**
and issues one deduplicated guarded same-Root review if the measured window
falls below one closure. The target is aspirational, not a throughput guarantee,
resource grant, acceptance substitution, or reason to restart in-flight work.
The existing 20-minute checkpoint and 40-minute qualified-evidence stall defaults
are preserved; the independent velocity deficit can request a finite decision
at 30 minutes. The 156 original checks, holds, budgets, native custody, and
all original file/integration and milestone acceptances remain unchanged.

Future `--continuous` invocations now enable closure control WITHOUT implicitly
setting `--stop-after-m14-m15`: after accepted M14 and M15 they keep working on
the saved whole-OS original milestones in order. A *separately explicit*
`--stop-after-m14-m15` still checkpoints the larger goal exactly as requested;
for example the previously authorized overnight launcher uses that explicit flag.
Neither this source change nor a new default changes a live invocation's actual
startup arguments, process identity or saved Root.
