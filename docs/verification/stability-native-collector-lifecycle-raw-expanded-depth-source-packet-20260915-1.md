# Native lifecycle raw expanded-depth source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-expanded-depth-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to output-oracle checkpoint commit
`102d1abc4ec5c6dbf41ca4a0f91cfd9037bb1f73` and checkpoint JSON SHA256
`c7ae5e27907d9346e4e03055d5b50821738e164405dcbd00c6eaa499e5391792`.
Its recorded source hashes and all 133 accepted raw records remain fixed. Allow
edits only to `vectors.json::raw_invalid`, the matching harness inventory and
focused source tests. Preserve ordinary and expected literals, decoder logic,
models, mutants, artifacts and the accepted output-oracle helper/tests. Keep
both corpus flags and `RAW_FULL_MATRIX_FROZEN` false.

Use this exact compact envelope and member order, substituting materialized
literal JSON for `L(N)` and `O`, with no trailing newline:

```text
{"schema_version":2,"model_only":true,"corpus_complete":false,"pools":{"D":{"arg":1}},"vectors":[{"name":"pool-base","coverage":["pool-base"],"event_capacity":256,"seed":"NONE","operations":{"pool":"D","args":[L(N),O]}}],"raw_invalid":[],"mutants":{}}
```

`L(N)` is exactly N opening brackets, the integer `0`, and N closing brackets.
`O` is the one-operation list
`[[1,"CAPTURE_END",null,null,0,0,0,0]]`, not a bare operation. `D` has the
single placeholder `{"arg":1}`, so it has arity two. Expansion traverses both
supplied arguments, then D selects and copies O. L therefore exercises only
supplied-argument traversal and is discarded.

Add exactly one raw negative:

| Name | N | Input bytes | First `ValidationError` |
| --- | ---: | ---: | --- |
| `raw-pool-expanded-depth-over` | 32 | 348 | `expansion depth` |

Its coverage is
`['pool-validation','raw-pool-expanded-depth-over']` and its expectation is the
standard harness exit 2, empty streams and zero model calls. The cumulative raw
inventory becomes 134.

The exact focused positive `positive-pool-expanded-depth-fit` uses N equal to 31
and is built only in the test. Its compact input is 346 bytes. It reaches depth
32, exits zero with empty streams, and expands exactly to O. Its expansion budget
consumes 54 nodes and 383 bytes, leaving 262,090 nodes and 2,096,769 bytes.

The negative reaches the depth guard while attempting its integer zero at depth
33. The guard rejects before charging that zero, after consuming 33 nodes and 66
bytes, leaving 262,111 nodes and 2,097,086 bytes. It fails before traversing O or
entering D's placeholder body. Pool preflight is independent and visits only D's
placeholder. This is expanded supplied-argument depth coverage, not pool syntax,
dependency-stack, node-budget or serialized-output-size coverage.

Tests independently construct exact compact bytes and compare the retained
negative, input sizes, exception class/message, positive child outcome, exact O
result and both remaining budget fields. Require the exact one-name slice and
134-name union, uniqueness, coverage, expectation, nested-empty raw arrays and
ordinary disjointness. The exact first 133 lexical records, from the first
opening brace through the 133rd closing brace including intervening separators
and whitespace, have SHA256
`7b84246f678c8239edd5fc504b63c2696dc64c0b5a71075cf3d71a493f0c9db8`.
Read bytes before UTF-8 decoding, preserve this prefix and all prior guards, and
retain the LF-to-CRLF rejection control. The build tripwire observes 134 raw
children with no compiler, build or model call and no output directory. Preserve
all artifact, timeout, output, cleanup and oracle checks.

Do not place L in the pool body, remove O's outer list or count the rejected
zero. Aggregate preflight budgets, remaining scalar/key positions, model
decision tables and the rest of the raw/oracle matrix remain deferred. No
full-matrix, compiler, model, native, ABI, application or production release
follows.
