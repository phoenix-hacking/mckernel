# Acknowledged prepublication prefix: source-only draft

This proposes one extra host capture between input and RET completion for
**postpublish-notify (2) and recoverable-backpressure (3)**. It is not execution
authorization. Existing phase, controller, parser, runner and compiled artifacts
remain unchanged. Modes 1 and 4 continue using their exact automatic-release
overlay and controller. No public production ABI changes are proposed.

## The missing ordering

Today `verification_accepted_phase` calls `release_accepted` immediately after
the unlocked AcceptedReturn observation. The selected send can then run before
the host stops QEMU. Meanwhile the controller calls `observe_return` immediately
after writing the input; it cannot request a held physical snapshot while
waiting there. A metadata label does not establish a physical prefix.

The minimal new sequence is:

```text
PRE_INPUT capture -> verified continue -> ACK -> write sixteen a5 bytes
native RET ENTER -> prepare completion -> normal advance initializes timer
AcceptedReturn full snapshot -> HELD_READY (selected send still deferred)
controller sees held status and samples original worker in RETURN ioctl
ACCEPTED_RETURN request -> host pauses, validates and captures response/rings
host verifies continue -> durable capture manifest -> exact ACK
controller sends one RELEASE_ACCEPTED ioctl carrying that ACK's digest
native checks original owner/timer, releases -> real fault-mode processing
actual RET LEAVE -> existing terminal or recovery collection
```

There is no host wait under application, transport, pager or ledger locks.
The existing brief slots lock is used only to copy the selected completion's
identity/timer and, on release, validate that same completion and commit scalar
release state. It is dropped before logging, ioctl copyout, sleeps or host I/O.
The verification Permit is also dropped before returning to userspace.

## Native change, isolated to the new published-mode overlay

Create a separate `published-hold-v1` fixture/stager restricted to compiled
modes 2 and 3. Keep the existing owner observer and production method bodies.
Preserve the measured noninline boundaries; measure any resulting compiled
stack change before execution. The new phase controller has these stages:

| Stage | Meaning | Selected send |
| --- | --- | --- |
| 0 | Unselected | Existing unmatched path |
| 1 | Original blocked read armed | No accepted completion yet |
| 2 | Accepted, waiting for full snapshot | Observation EAGAIN |
| 4 | Full accepted snapshot ready, waiting for ACK | Host-hold EAGAIN |
| 3 | One-shot release committed | Original mode-2/3 fault wrapper |

`accepted_selected` remains scalar-only under the original return path's slots
lock. At end-pump, first match actual Runtime OS/generation, then obtain the
verification Permit as today. Extend the existing selected-completion status
copy with its actual `publication_since: Option<u64>`. Check the original
request, worker, Returning completion and exact response Claim under the same
slots lock; do not initialize or change the timer there.

If that timer is `None`, leave stage 2 and return without a snapshot. The next
ordinary `Remote::advance` may initialize it through the existing
`publication_expired` logic. This also covers RET committing after this pump's
advance. If native health fails or the completion disappears, invalidate the
verification attempt; never manufacture a timer. With `Some(timer)`, copy the
scalar, emit the full unlocked AcceptedReturn snapshot once, and recheck the
same selected healthy completion/timer before making stage 4 queryable.
The actual AcceptedReturn CALL row must contain the same `Some(timer)`.

Emit a small `STABILITY_HOLD_READY version=1` record tied to the exact selection,
nonce, accepted snapshot sequence 2, copied timer and native monotonic time.
Initialize its scalars and finish its log before publishing stage 4 with Release
ordering. Queries use Acquire ordering. Do not repeat the full snapshot while
waiting. The packet worker continues its normal pumps, including the original
expiry scan. The hold retains no new application or guest-memory owner.

Separate host-hold retry accounting from existing pre-snapshot barrier counts.
In the new wrapper, return a typed decision such as `Released`, `BeforeSnapshot`
or `AwaitingHostAck`. The last increments a bounded, saturating host-hold counter
and returns -11 **before** fault attempts, real-send counts, response memory,
publication or notifications. The old phase/fault barrier pair counts only
`BeforeSnapshot`; its accepted/final equality remains valid. Overflow latches
verification invalid and supplies no acceptance. It never silently releases.
Use the existing scalar accounting at ordinary releases; do not change mode 1/4
artifacts or reinterpret old counts.

## Private command and ACK binding

Use a separate verification command, proposed `0xc100f502`, version 2, fixed
256 bytes; reject compat and any mixed old/new version. This value is absent
from the inspected current scripts/native sources, but must be collision-checked
again when implementing the isolated stager. No production ABI declaration or
command allocation changes. Keep the original request identity at offsets
0–63 and output selection at 80–159. Existing operation numbers retain their
meanings in this new version; add:

| Operation | Input beyond byte 63 | Result |
| --- | --- | --- |
| 7 `ACCEPTED_STATUS` | All zero | EAGAIN until stage 4; then existing accepted sequence and held timer scalars, no new snapshot |
| 8 `RELEASE_ACCEPTED` | accepted sequence at 64, UART sequence at 72, raw 32-byte capture SHA256 at 80; bytes 112–255 zero | One release of this exact selected completion |

For these published profiles the accepted snapshot and UART capture are both
sequence 2. They are separate sequence spaces and must be compared to their
own recorded values. The request's normal strictly increasing ioctl sequence
continues independently. All other operations require zero request tail.
Release requires stage 4, exact selected OS/generation/PID/delivery/ledger
identity and nonce, accepted sequence 2, UART sequence 2, nonzero digest, no
prior release, no verification error, healthy actual Runtime/application, and
the same Returning completion/Claim and original timer.

The new output tail can carry timer seconds at 208, a strict timer-present bit
at 216, held-ready time at 224, host-hold retry count at 232, and this command's
native observation begin/end times at 240/248. Query and release therefore both
retain fresh observation intervals. Zero-before-availability is explicit for
the held/timer values; timer value zero is not
used as the absence sentinel. Each field is an unsigned 64-bit little-endian
word. Original output selection and consumed-sequence checks remain mandatory.
The complete raw request, reply and actual ioctl/probe outcome must be retained.

Immediately before scalar release, check native `now_ns < (timer+5)*1e9` with
checked arithmetic. Record a begin/end interval around the short validation
and stage transition; never claim a timestamp taken before/after the transition
is its exact instant. The selected send cannot pass the same slots lock until
the scalar commit completes. Log the release result and ACK digest outside that
lock; fault logging may interleave, so the new validator joins identity and
time intervals instead of requiring release-print-before-send-print ordering.
Post-release observations must show the same immutable copied timer.

The kernel cannot authenticate a host QMP operation from a digest. The required
external join is native release request/digest -> controller's exact received
ACK -> host's complete captured bytes and durable manifest -> verified QMP
continue. A successful private ioctl alone proves none of those external facts.

## Controller and host changes

Create new published-mode controller/client and host protocol components; do
not edit frozen v2 or `fault_control.py`. Use an explicit new protocol/profile
(proposed `STF2`) whose ordered normal phases are PRE_INPUT, ACCEPTED_RETURN,
POST_RET, and QUIET only for terminal mode 2. Reject mode 1/4, old frames and
unexpected phases. Preserve the existing strict nonce/sequence/TGID/TID/start-
ticks/manifest-digest checks, bounded UART framing and original emergency data.

After input, poll operation 7 while pumping the actual pipes and sampling the
original worker's ticks/syscall. This is before `observe_return`, not inside an
unbounded kernel wait. Retain each actual probe and bound attempts/artifact
count. A successful query must show the original key, stage 4, accepted sequence
2 and timer-present 1. The controller must independently observe the original
worker in the real RETURN ioctl while held and retain that sample; then it sends
ACCEPTED_RETURN. Later RET observation uses that recorded entry, preventing a
fast post-release return from escaping the sampling window.

The host requires exactly the two complete native snapshots plus the matching
HELD_READY record. Pause QEMU, refresh and validate this prefix, and verify the
original selected worker, owner, response Claim and timer. Capture the physical
40-byte original response and actual rings. Require status 0, wake 1, servicing
TID matching the selected original worker and result 16; preserve the opaque
first word and tail. Compare against BlockedRead allowing only the exact
prepare-written fields and prove no selected wake was published yet. Counts
remain address 1, payload 0/0, released false/release 0, fault attempts 0,
real sends 0, publications 0 and notification failures 0.

Always attempt/verify QMP continue after a stop or capture error. Only a complete
physical comparison and independently verified continue permit the exact ACK.
Persist raw bytes and the manifest before ACK. The controller retains that ACK
and passes its digest to operation 8. The host must latch release-possible
**before its first ACK send attempt**, and the controller must latch it before
submitting the release ioctl. A short write, error, timeout or failed local
return does not prove the peer received no complete ACK or that no native
release committed. From that latch onward, including every emergency/final
capture: **never reread the original response**. Post-RET/recovery evidence uses retained prefix bytes, rings, native
owner records and raw outcomes; no dangling physical response access is allowed.

A dispatched release is not retried. Only the existing narrowly proved
pre-dispatch busy-Permit EAGAIN with untouched output can retry under the same
original request sequence. Copyout failure after release is ambiguous and
fatal to verification; it is not a rollback. Duplicate/stale releases fail.
Lost ACK, invalid metadata, capture/resume failure or expired timer causes no
automatic release. Preserve evidence and allow ordinary production expiry and
bounded owned cleanup. No new lock is held during either process.

## Original clock and feasibility

The authoritative deadline is `(publication_since_seconds + 5) * 1e9`, not
accepted time plus five seconds and not `FAULT_SELECTED.since_ns`. Its coarse
seconds origin can leave less than five seconds after acceptance. Waiting for
the ACK consumes that existing budget, including any time the guest clock
accounts for QMP pause/resume. Do not pause/reset/replace the timer.

Preserve input-plus-15-second RET and overall-90-second controller deadlines,
existing bounded cleanup, host transaction bounds and the independent QEMU
watchdog. Until the timer is observed, controller polls retain the original
input/overall deadline and normal native expiry continues independently. Once
known, guest controller polls/release use the minimum of those original bounds
and the original production deadline in the same guest Linux monotonic clock.
There is no fresh budget per retry. The host keeps its bounded capture/rescue
limits; a short successful transaction is required in practice, and a late one
cannot authorize release. Native release always rechecks its own clock after resume. Log actual
budget at held-ready, release and callback completion. Do not assume that the
current seven-second QMP upper bound fits this smaller window.

Mode 3 still holds backpressure for the original two seconds beginning at its
first **post-release fault attempt**, and must show the unique actual successful
send callback ending before the copied original five-second deadline. If capture
or release leaves insufficient time, the attempt fails; do not shorten the
two seconds or reset the timer. Mode 2 likewise must publish before expiry so
the intended notification failure is isolated. Host clock values are not
subtracted directly from guest/native timestamps without a justified mapping.

## Correct the newly observed sampling classification

Permanent guest 2's original controller recorded `running\n` at
35745933935 ns after a complete RETURN sample, then labeled RET left. Native
RET did not leave until approximately 40.004 seconds. Preserve that original
report and source; its polling time is not a true RET exit. The new controller
must not infer a different syscall from `!is_ioctl(RET)`.

Use explicit classifications. A complete, error-free nine-field nonnegative
syscall record matching ioctl RETURN is `IN_RET`. A complete valid different
syscall is `OTHER_SYSCALL`; only after entry was observed can it establish a
sampled departure. `running`, empty, partial, extra-token, malformed and negative
number forms are `UNKNOWN` in the minimal correction and never change entry/
departure state. The pinned proc implementation also emits a three-field
negative-number form; treating it as unknown is deliberately conservative.
Future support for that separate grammar needs its own reviewed vectors.

ENOENT/ESRCH on the syscall file alone is not an exit classification. Recheck
the original task identity; a confirmed disappearance may record worker gone,
while a surviving changed start time is an identity failure. Other read errors
fail collection. A waitable launcher by itself does not fabricate a syscall
sample or native errno. Native RET ENTER/LEAVE remain the independent return-
value and deadline authority.

The separate root-owned `owner-return-poll-v1` candidate is the intended source
of this correction and must be frozen/reviewed before composition here. Its
required regression inputs include actual permanent-guest-2 read, RETURN and
`running` bytes with their original event-line identities. Any derived
truncation/malformed/error/identity cases must be explicitly synthetic and unrun
until their own validation. This hold draft does not modify that candidate.
In particular the actual RETURN -> actual `running` sequence must remain
entered-but-unknown, with no departure timestamp. An actual pre-input read
reused as an isolated `OTHER_SYSCALL` input is labeled as such, never presented
as a later observation from that guest.

## Before implementing or executing

Required focused negative checks cover missing/late/duplicate ACK and release,
mixed mode/version/nonce/owner, timer None/changed/overflow/expired, query or
copyout failure, incomplete physical capture, failed continue, and the case
where publication precedes the release ioctl's userspace return. Verify no
response read after possible release; prove retry counters stay separate and
overflow cannot promote success. Preserve byte-identical mode 1/4 paths.
Test the raw sample classifications separately from the real fork/ioctl/ACK
state machine. All tests, native compilation and guest runs remain unperformed
by this draft.

Freeze the full new source graph, review it independently, compile and remeasure
the affected observer paths, then use a fresh reviewed execution packet. The
host-hold handshake must fit the existing combined export/member budget; the
mode-3 eight-HELLO collector remains its separate already-documented gap. This
draft closes no acceptance gate and changes no historical score.

Primary source anchors are bound in the companion JSON: phase accepted/release
and private command handling, selected completion/Remote status, controller
input/RET/capture paths, UART phase grammar, phase parser and production timer,
plus pinned Linux `fs/proc/base.c:676–700` and original guest-2 evidence.
