# Native lifecycle raw-invalid source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-invalid-source-packet`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

This bounded packet follows the accepted corpus-contract addendum. It does not
release edits or execution until independent review.

## Allowlist and entry points

The only writable source paths are `harness.py`, `vectors.json` and
`raw-invalid/oversized-document.json` under
`scripts/tests/fixtures/native-lifecycle-model-v1/`, plus
`scripts/tests/test_native_lifecycle_model.py`. Preserve ordinary vectors,
`expected.json`, mutants and both model sources.

Add mutually exclusive modes:

- `--decode-raw-document` consumes bounded stdin only and performs no corpus or
  expected-file discovery, compiler lookup, directory creation or subprocess/model
  call.
- `--check-raw-invalid` validates the containing corpus and runs raw cases without
  compiler/output arguments.
- existing build mode remains separate and corpus-completion gated.

Raw payloads are complete input-schema documents whose own `raw_invalid` is empty.
Decoder mode validates syntax, envelope, pools/arity, expanded operation schema and
count, but does not execute nested raw cases, campaign coverage, mutants or expected
output. Shared strict validators must be used.

Before compiler discovery or output creation: strictly decode carrier input and
expected documents; validate raw record shape/name/coverage/expectation; validate
ordinary operations and literal expected rows without models; obtain exact raw
bytes; and run isolated decoder children. Only full build mode then enforces whole-
corpus coverage/mutants and invokes compilers.

Validation rejection returns child exit 2 with empty streams. Valid structural
input returns 0 with empty streams. Deliberate validation failures are caught;
timeouts, crashes and unexpected exceptions never count as rejection. Each child
has a five-second limit and 64-KiB captured-stream limit and is terminated/reaped on
either bound. Source tests retain their own unittest streams.

## First nine mechanism cases

Each exact raw record uses the addendum's name/coverage/source/expected schema and
expects harness exit 2, empty stdout/stderr and zero model invocations:

1. `raw-duplicate-key`: duplicate `schema_version` member.
2. `raw-nonfinite`: `event_capacity` is `NaN`.
3. `raw-trailing-object`: append `{}` to an otherwise valid document.
4. `raw-embedded-nul`: insert a literal NUL byte.
5. `raw-129-operations`: 129 contiguous eight-field operations.
6. `raw-oversized-document`: otherwise valid JSON plus whitespace, exactly
   1,048,577 bytes, in the sole external artifact.
7. `raw-unknown-pool`: operations reference absent `MISSING`.
8. `raw-cyclic-pool`: referenced pool `A` references itself.
9. `raw-excess-pool-args`: a zero-arity valid operations pool is called with `[0]`.

The external artifact follows the accepted single-open, no-symlink, fixture-root
containment, pre-read cap, stable metadata, exact size/hash and same-retained-byte
decoder rules. Independently bind its final hash before release.

## Focused assertions

The source test adds a separate `RAW_REQUIRED` inventory for these nine names and
does not place them in ordinary expected mappings. Positive decoder controls cover
a valid document, exactly 128 operations, zero-arity omitted/empty arguments and
exact nonzero arity. Negatives verify exact child status/streams. Parent-side tests
reject metadata/hash/size/path/symlink failures and prove output/compiler/build/
model tripwires remain untouched, bytes are read once, recursive raw validation is
rejected and timeout cleanup reaps the child. Existing unrelated checks remain.

Forged-authority, numeric-width and the rest of the malformed-schema matrix remain
explicitly outstanding after this mechanism slice. Success is only a reviewed
source-mechanism prerequisite, never whole-corpus/model/native/ABI/application or
production acceptance.
