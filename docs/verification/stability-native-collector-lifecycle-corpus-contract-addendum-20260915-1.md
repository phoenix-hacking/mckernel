# Native lifecycle corpus contract addendum 1

Date: 2026-09-15
Task: `M02-C-lifecycle-corpus-contract-addendum`
Disposition: `CORPUS_CONTRACT_CORRECTION_DRAFT`

This additive draft resolves gaps found after the attempt-2 corpus draft. It does
not modify historical records and releases no source, checks, compiler/model,
native/guest, ABI, application or production acceptance until independent review.

## Retained-capacity semantics

An application identity is the four-tuple `[capture,slot,os_generation,application]`
projected from a full key. A successful parentless `P_ALLOC` admits that identity.
All subjects in one vector must have the same capture, slot and OS generation;
multiple application identities may coexist. `P_ALLOC` requires a process-domain
key and null parent. `T_ALLOC` requires a thread-domain key and an existing exact
parent process: replacing only the thread component of the thread key with zero
must equal the complete parent key. A mismatch returns `KEY` before capacity or
lifecycle checks, emits no event, preserves rows/counts and latches incomplete.

Application, process and thread occupancy counts distinct identities retained in
their registries and never decreases when rows retire. Limits are global per
vector: two admitted applications, four process rows and eight thread rows.
Validation precedence is schema, full key/domain/parent, duplicate or active-TID
identity, then retained capacity, then lifecycle state. Exceeding any retained
capacity returns `LIMIT`, emits no event, performs no registry/reference/VM/main-
storage mutation and irreversibly latches incomplete at the preceding attempt and
retained counts.

Use three independent boundary vectors. The application vector admits two
parentless process keys in applications 1 and 2, then rejects application 3 while
process occupancy is three or less. The process vector admits four process keys in
application 1, then rejects its fifth. The thread vector admits exactly eight
distinct thread keys under one process, exactly one marked main, then rejects a
ninth fresh non-main key/TID. All successful rows remain literal and sorted.

The operation limit is whole-document validation: 1 through 128 contiguous
operations are legal; an empty or 129-operation document exits 2 with empty stdout
and stderr and zero model invocations. It never emits an operation-129 `LIMIT` or
state row.

## Raw-invalid representation

`raw_invalid` is an array of objects with exactly these fields:
`name`, `coverage`, `source`, and `expected`. Names are unique strings; coverage is
a nonempty unique string array. `expected` is exactly
`{"stage":"harness","exit_code":2,"stdout_hex":"","stderr_hex":"","model_invocations":0}`.
Raw cases count against a separate reviewed `RAW_REQUIRED` name/family inventory;
they do not appear in ordinary `vectors` or `expected.json` model-step mappings.

`source` is exactly one of:

- `{"inline_utf8":string}` for exact UTF-8 bytes; or
- `{"artifact":{"path":string,"sha256":64-lowercase-hex,"size":integer}}`.

Artifact paths are repository-relative, must remain inside
`scripts/tests/fixtures/native-lifecycle-model-v1/`, and must pass containment
checks with no symlink traversal. The harness opens the regular artifact once, checks its declared
size and the absolute 1,048,577-byte cap before a bounded read, then verifies the
actual length and SHA-256. Those same retained bytes, never bytes from a reopened
pathname, are passed to the decoder. Only the specifically reviewed oversized-
document case may exceed the ordinary 1,048,576-byte document limit; its exact size
is 1,048,577 bytes. Inline UTF-8 is used for every other raw case, including
embedded NUL, malformed, nonfinite and trailing-byte cases.

Raw decoding and validation run in a dedicated harness mode before output/build
directory creation or compiler discovery. Each case is evaluated in an isolated
child decoder, captures both streams, confirms exit 2, and records that neither
model was invoked. The enclosing source test may report its own unittest output;
the empty-stream rule applies to the decoder child.

Pool references may omit `args` only when the referenced pool has arity zero.
Otherwise `args` is mandatory. Pool arity is one plus the greatest placeholder
index anywhere in its body, or zero when there is no placeholder. The argument
array must have exactly that arity; missing or excess arguments reject the whole
document. Unknown fields, non-string names, non-array arguments, invalid
placeholders, cycles, depth above 32 and expanded budget excess also reject before
any model invocation.

## Counter boundary separation

`LOST_MAX` with zero event capacity and one capture-end operation is the lost-
counter overflow case. `ATTEMPTS_MAX` with capacity 256 and the same operation is
the separate attempt-counter overflow case. The latter retains no event and yields
control `[18446744073709551615,0,18446744073709551615,true,true,true,0]`.

Independent review must approve this addendum before capacity or raw-invalid
materialization. Whole-corpus and model-source review remain later gates.
