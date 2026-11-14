# Typed owner and RET observations

`owner_observations.py` consumes one complete fresh-module kernel log. It is an
offline metadata parser and expectation comparator. It never starts a process
under test, maps guest memory, injects a fault, or grants application acceptance.
The Python tests use synthetic log records; their success does not validate the
native observer, transport, application, or guest.

The supported producer is version 1 of the ten Rust files under
`scripts/tests/fixtures/stability-owner-observer/`, plus
`scripts/tests/fixtures/stability-ret-observer.rs`. The observer source review
is `docs/verification/stability-owner-observer-review-20260913.md`. The RET
appendix was an unwired prototype at initial parser implementation. Its actual
hook locations, native compilation, measured frames and line lengths, and
guest behavior require their own source-bound evidence.

## Input and output

For structural observations only:

```sh
python3 scripts/application-tests/owner_observations.py \
  --log retained-serial.log --output new-owner-observations.json
```

For an explicit caller-frozen mode comparison:

```sh
python3 scripts/application-tests/owner_observations.py \
  --log retained-serial.log --contract frozen-mode.json \
  --phase-timing observed-phase-intervals.json \
  --output new-owner-comparison.json
```

Outputs are created exclusively: an existing result is never overwritten. A
rejected in-cap log is retained in the result as exact base64 bytes with its
SHA-256 and size. Successful output also keeps every typed record, original line
number and raw-line SHA-256. CLI input paths, sizes and hashes identify the
capture, contract and timing files. Capture files remain separate immutable
artifacts; the JSON is an additional copy, not permission to discard evidence.
An input too large to read safely is rejected before embedding its bytes; the
caller must preserve that original capture externally.

Input files must be regular, nonsymlink final path components. Opens are
nonblocking, so FIFOs cannot hang the parser. Reads reject size/identity changes.
Ancestor directory symlinks are part of the caller-selected filesystem path;
this is not a filesystem sandbox. The entire log is limited to 16 MiB, 65,536
lines, 2,048 bytes per line including newline, 4,096 marker records and six
snapshots. Contract and timing JSON files are each limited to 64 KiB. Reaching a
bound does not justify raising it during a run; review the producer/capture and
freeze a new version if needed. These parser caps do not establish the native
printk limit or prove the logger did not drop data.

Accepted line prefixes are raw printk text, optional `<priority>`, and optional
`[ decimal_seconds.fraction ]` dmesg timestamps, in that order. CRLF and LF are
accepted and retained exactly. Unrelated bounded log lines are preserved and
ignored. Any line containing `STABILITY_OWNER` or `STABILITY_RET` must parse
completely; arbitrary prefixes, unknown markers, NULs, non-ASCII marker bytes,
missing final newline and trailing fields are rejected. Timestamp prefixes are
preserved as raw evidence, not promoted to precise event timestamps.

## Fixed literal and inventory schemas

The parser uses an explicit type-directed grammar, never `eval`, `exec`, or a
general expression parser. Rust struct names, field names and field order must
match the frozen schema. Only canonical decimal integers, lowercase unprefixed
hexadecimal Runtime pointers, true/false, exact `Some(...)`/`None`, two-field
worker tuples, six-element argument arrays, and fixed phase strings are allowed.
Integer widths match x86_64 `usize`, u64/u32/i64/i32. Unknown fields, escapes,
numeric suffixes, negative zero, overflow, missing fields and different tuple or
array lengths are rejected. Nesting is bounded by the schema and a depth limit.

Every snapshot requires one BEGIN, Runtime, applications domain, pager domain,
seven ledger domains, counters and END. It requires each application row's
cleanup/image/schedule/retirement detail and mailbox, plus a distinct release
mailbox. Counts, completeness, caps, ordinals, occupied slot ordering and domain
keys must agree. Missing detail, unknown native claim ownership, duplicate
delivery/worker/ledger identities and an incomplete or failed counter END are
rejected. The original BlockedRead sample must contain the actual Delivered
nr=0, fd=0, length=16 call, original worker pair, 40-byte response claim, OS
generation, response allocation serial and ledger slot/span.

The entire capture must start at owner sequence 1 and use contiguous sequences
with unique phases. Nested or interleaved owner snapshots are rejected. This is
a full fresh-module capture requirement, not support for concatenated guests or
arbitrary mid-run excerpts. RET records may occur between owner records, but
the complete capture requires exactly one SELECTED, ENTER and LEAVE, in that
order. All three keys must match the original selected OS generation, PID,
worker handle, delivery serial and actual worker TID. Invalid selection,
duplicates, missing records or nonmonotonic/out-of-range ktime timestamps fail.

The parsed RET result retains `errno`, `accepted`, input `value`, routed `cpu`,
entry/leave nanoseconds and elapsed nanoseconds separately. Neither the errno
nor accepted word is replaced with the launcher exit code. The source placement
of ENTER/LEAVE around the actual backend invocation remains a separate review.
The selected worker inventory row must match the call/delivery worker handle,
TID and active delivery; an older completed serial is retained legitimately by
the native reserve path. RET's routed CPU must equal the selected request CPU.
The comparator bounds base64 before decoding, reparses the raw capture, rejects
type changes including boolean/integer aliases, and uses that new parse as its
authority.

## Caller-frozen mode contract

The JSON contract has exactly these fields:

```json
{
  "schema_version": 1,
  "observer_version": 1,
  "mode": "hard-prepublication",
  "expected_counters": {},
  "ret": {
    "errno": -5,
    "accepted": 1,
    "value": 16,
    "maximum_elapsed_ns": 15000000000
  }
}
```

This example is incomplete and intentionally cannot authorize or pass a run.
The example RET values are synthetic test data, not a prescribed outcome for
any transport mode. The caller must freeze the reviewed mode's actual expected
backend result, accepted word and input value before collecting results.

Supported mode names are `hard-prepublication`, `postpublication-notify`,
`permanent-pressure`, and `recovery-before-deadline`. Terminal modes require
exactly BlockedRead, AcceptedReturn, Terminal and TerminalPlusFive snapshots.
Recovery requires BlockedRead, AcceptedReturn, Recovery and AfterEightHello.
Missing, extra or differently ordered phases fail.

`expected_counters` must contain exactly those four phase names. Each phase
must supply all seven fields: `address_calls`, `payload_calls`, `payload_bytes`,
`release_calls`, `released` (a boolean), `after_release_calls` and
`duplicate_release`. Every observed field must equal its frozen expectation.
The comparator independently enforces the source's selected-response epoch:

| Phase | Address calls | Release calls |
| --- | ---: | ---: |
| BlockedRead | 0 | 0 |
| AcceptedReturn | 1 | 0 |
| Hard prepublication/permanent pressure terminal and +5s | 1 | 0 |
| Postpublication notify terminal and +5s | 2 | 1 |
| Recovery and after eight HELLOs | 2 | 1 |

Payload calls/bytes are explicitly frozen by the caller; no default claims a
copy occurred. After-release accesses and duplicate releases must be zero.
Counts cannot decrease across phases, and the final two vectors must be equal.
The observer uses u64 atomic fetch-add counters without a wrap latch. This
parser rejects out-of-range values, the maximum counter boundary, decreases and
unexpected exact counts; logs alone cannot rule out an entire 2^64 wrap. These
are adapter entry-point counters, not hardware watchpoints or proof that every
possible memory access was instrumented.

RET comparison requires exact errno/accepted/value and a positive elapsed-time
limit of at most 15 seconds. This observes time inside the actual backend
bracket only when the separately reviewed hook wiring establishes that bracket.
Host task state, ioctl exit, launcher wait status and controller deadlines are
additional checks, not inferred from this interval.

## Independent domains and phase timing

Runtime, application inventory, application detail, each mailbox, pagers, each
ledger class and lifetime counters are independently sampled. Parsed records
preserve those boundaries. The parser does not require live cross-domain values
to form a fictitious atomic whole-OS snapshot. The original claim/worker checks
only assert the selected record's exact identity and operation.

Terminal/+5s comparison requires equality of all actual domain records and
rows, including Runtime counts, ledger allocation serials and individual tag
identities. It omits only log envelope/position, phase labels and the separately
compared lifetime counters. Comparing `last_serial` alone is insufficient:
ledger removal does not advance it. Recovery and after-eight inventories are
retained separately because subsequent applications may legitimately change
them; the old response counters must remain equal. Phase labels do not prove
either successful recovery or eight launches.

Owner markers have no `mono_ns` field. Therefore the comparator requires a
separate exact timing JSON with `schema_version: 1`,
`clock: "host_kernel_monotonic"`, and `phases`, mapping the same four phase
names to `{ "begin_ns": INTEGER, "end_ns": INTEGER }`. Intervals must be ordered,
nonoverlapping and in the nonnegative signed-64-bit kernel-time range; BlockedRead must end no
later than RET entry. TerminalPlusFive must begin at least 5,000,000,000 ns
after the Terminal interval ends. The caller must source-bind these intervals
to observed barriers in the same kernel clock. Merely writing a timing JSON
does not prove that provenance. The output explicitly records
`timing_provenance_verified: false`.

Structural success is `COMPLETE_OBSERVATIONS_ONLY`. A matching explicit
comparison is `OBSERVATIONS_MATCH_FROZEN_CONTRACT`. Neither is PASS. Both keep
`application_acceptance: false` and `production_gate_credit: false`.
Physical response/ring bytes, host task state, UART acknowledgement protocol,
actual phase barriers, guest/module/image/hook provenance, launcher wait status,
and same-OS follow-up applications remain separate required evidence. The
external orchestration layer must establish those facts before any runtime
gate or application acceptance decision.

In particular, stable inventories alone do not prove terminal quarantine or
the expected transport error. The comparator deliberately permits a caller's
explicit RET/payload expectations; it does not derive correct errno, accepted
word, payload or terminal flags from a mode name. A reviewed execution profile
must supply those semantic checks separately. The synthetic tests include
healthy Terminal inventory flags and a -5 RET errno even in recovery to show
that metadata comparison never claims actual fault recovery or acceptance.
