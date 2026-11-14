# Native lifecycle raw aggregate preflight-node source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-preflight-aggregate-node-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to output-envelope checkpoint commit
`b3efccd94395b9fb61f150f4bf8b4f2d45843918` and checkpoint JSON SHA256
`0dfa2185a52db068b32662517a6ad1c4a94773f34823bdc8d0f99081f894e13f`.
Preserve its recorded source hashes and all 135 raw records. Allow only an
appended `vectors.json::raw_invalid` record, matching harness inventory and
focused source tests. Preserve ordinary/expected literals, decoder logic,
models, mutants, artifacts and all artifact/oracle/output-envelope checks. Keep
both corpus flags and `RAW_FULL_MATRIX_FROZEN` false.

Use the established compact `pool-base` envelope below, in exact member order
with no trailing newline, substituting fully materialized JSON arrays for U and V:

```text
{"schema_version":2,"model_only":true,"corpus_complete":false,"pools":{"U":U,"V":V},"vectors":[{"name":"pool-base","coverage":["pool-base"],"event_capacity":256,"seed":"NONE","operations":[[1,"CAPTURE_END",null,null,0,0,0,0]]}],"raw_invalid":[],"mutants":{}}
```

U contains exactly 131,071 integer zeros. Positive V also contains exactly
131,071 zeros; negative V contains 131,072. Materialize every zero. Neither pool
is referenced, and the sole mutation appends one zero to V.

Add exactly one raw negative:

| Name | Compact input bytes | First `ValidationError` |
| --- | ---: | --- |
| `raw-pool-preflight-aggregate-node-over` | 524,544 | `expanded literal budget` |

Its coverage is
`['pool-validation','raw-pool-preflight-aggregate-node-over']`, with the standard
harness exit 2, empty-stream and zero-model-call expectation. Cumulative raw
inventory becomes 136.

The test-only `positive-pool-preflight-aggregate-node-fit` is exactly 524,542
compact bytes and decodes with exit zero and empty streams. For N zeros, each pool
body consumes N+1 nodes and 2N+1 charged bytes. U and positive V each consume
131,072 nodes and 262,143 bytes. Their aggregate leaves
`(nodes, bytes) == (0, 1572866)`. Negative V consumes 131,073 nodes and 262,145
bytes, so the attempted aggregate leaves `(-1, 1572864)`.

The negative first fails on V's final zero at depth one during `scan_arity(V)` in
the initial `analyze_pools()` pass, with exact `ValidationError` type and message.
No syntax budget exists and operation expansion has not begun. Each pool body
fits alone; byte and depth budgets remain below their limits. Positive
`analyze_pools()` returns `{"U":0,"V":0}`, and both its independent arity and
syntax budget instances end at `(0,1572866)`.

Tests independently construct and compact-compare the retained negative, assert
exact lengths/content and the one-zero mutation. Wrap the real budget constructor:
the negative decode creates exactly one instance ending `(-1,1572864)`; a
separate positive `analyze_pools()` call creates exactly two, each ending
`(0,1572866)`. Require the positive child outcome, exact one-name addition,
136-name union, coverage, expectations, uniqueness, nested-empty raw arrays and
ordinary disjointness. The exact first 135 lexical records have SHA256
`06f71693885dd79faf7edd1c8b5e33e5170bab3ecb6ed93716b603f8e64aee1d`.
Preserve that span and all prior prefix/CRLF guards. The build tripwire observes
136 raw children with no compiler, build or model calls and no output directory.

The current fixture is 488,540 bytes. This inline addition must remain below the
unchanged 1-MiB cap; assert and retain its exact resulting size. Do not externalize
the record or enlarge limits without a separate reviewed contract. This does not
duplicate traversal-node or aggregate-byte coverage and does not independently
exercise syntax-pass overflow. Remaining scalar/key positions, pool variants,
masked/name-budget dispositions and final reconciliation still block the full
matrix. No compiler, model, native, ABI, application or production release
follows.
