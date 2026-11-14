# Native lifecycle raw aggregate preflight-byte source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-preflight-aggregate-byte-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to expanded-depth checkpoint commit
`062bb544d0d5f3676c0fdee19a07df59ebc3208d` and checkpoint JSON SHA256
`b83a76a76c74ebfafb1e1e845ac2fae871564748b957a57b0c376830e06a5246`.
Preserve its recorded source hashes and all 134 raw records. Allow edits only to
`vectors.json::raw_invalid`, the matching harness inventory and focused source
tests. Preserve ordinary/expected literals, decoder logic, models, mutants,
artifacts and all accepted artifact/output checks. Keep both corpus flags and
`RAW_FULL_MATRIX_FROZEN` false.

Use this exact compact envelope and member order, substituting fully materialized
JSON strings for U and V, with no trailing newline:

```text
{"schema_version":2,"model_only":true,"corpus_complete":false,"pools":{"U":U,"V":V},"vectors":[{"name":"pool-base","coverage":["pool-base"],"event_capacity":256,"seed":"NONE","operations":[[1,"CAPTURE_END",null,null,0,0,0,0]]}],"raw_invalid":[],"mutants":{}}
```

U is exactly 87,381 lowercase ASCII `u` characters. Positive V is exactly
87,381 lowercase ASCII `v` characters; negative V is exactly 87,382. Materialize
every character inside the JSON strings. The sole mutation appends one `v`.

Add exactly one raw negative:

| Name | Compact bytes | First `ValidationError` |
| --- | ---: | --- |
| `raw-pool-preflight-aggregate-byte-over` | 175,023 | `expanded literal budget` |

Its coverage is
`['pool-validation','raw-pool-preflight-aggregate-byte-over']` and its expectation
is the standard harness exit 2, empty streams and zero model calls. The cumulative
raw inventory becomes 135.

The exact test-only positive `positive-pool-preflight-aggregate-byte-fit` uses
the shorter V and is 175,022 compact bytes. It decodes with exit zero and empty
streams. Each string costs `12 * length + 2`: U and positive V each cost
1,048,574 bytes, leaving four bytes after their aggregate 2,097,148-byte charge.
Negative V costs 1,048,586 bytes, so the aggregate charge is 2,097,160 and the
budget reaches minus eight. Both variants visit exactly two nodes and leave
262,142 nodes.

The negative first fails `ExpansionBudget.take()` while `scan_arity(V)` executes
in the initial `analyze_pools()` pass. Require exact `ValidationError` type and
message. The syntax budget has not been constructed and operation expansion has
not begun. Each pool body fits alone, making this an aggregate preflight boundary.
The positive completes both independent preflight passes; each budget instance
ends at `(nodes, bytes) == (262142, 4)`, and `analyze_pools()` returns
`{"U":0,"V":0}`. This is the adjacent-character boundary, not an exact-zero-byte
boundary.

Tests independently construct and compact-compare the retained negative; assert
both input sizes and exact scalar/string spelling. Wrap the real
`ExpansionBudget` constructor for one in-process negative decode and retain all
instances: require exactly one instance ending `(262142,-8)`. In a separate
positive `analyze_pools()` call require exactly two instances, each ending
`(262142,4)`. Do not replace validation logic. Require the exact one-name slice,
135-name union, uniqueness, coverage, expectation, nested-empty raw arrays and
ordinary disjointness. The exact first 134 lexical records have SHA256
`bc3f41f0c386c36b9a3ebd69283c619b7b070c9053fe6df00a10a0234c26b2e5`.
Preserve that span byte-for-byte and retain the LF-to-CRLF rejection control.
The build tripwire observes 135 raw children without compiler, build or model
calls or an output directory. Preserve artifact, timeout, output, cleanup and
oracle protections. Record the exact resulting fixture size in evidence.

This does not cover syntax-pass overflow: the arity pass rejects first. Existing
traversal byte/node/depth cases do not cover aggregate unused-pool preflight.
Aggregate nodes, remaining scalar/key positions, pool variants and final
guard-to-case reconciliation remain open. Pool-name charging and masked
serialized-output limits require explicit dispositions. No full-matrix,
compiler, model, native, ABI, application or production release follows.
