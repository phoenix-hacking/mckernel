# Native lifecycle raw envelope source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-envelope-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to the accepted 110-case checkpoint JSON SHA256
`e1769b506a87ae8ac816e93073373d9a84dbf31e2f175846e49f9f6ba55c1b3c`.
Allow edits only to `vectors.json::raw_invalid`, the matching harness inventory
and focused source tests. Preserve decoder logic, all 110 records, ordinary and
expected literals, models, mutants and artifacts. Keep both corpus flags and
`RAW_FULL_MATRIX_FROZEN` false.

The exact 110-record lexical span is SHA256
`e66175e09519434778e8a91df2913cce7afc0c3eab7a0cdd49f8479069f2ccda`.
Read raw bytes before UTF-8 decoding and preserve it exactly.

Use this exact 245-byte compact base without a newline:

```json
{"schema_version":2,"model_only":true,"corpus_complete":false,"pools":{},"vectors":[{"name":"raw-base","coverage":["raw-base"],"event_capacity":256,"seed":"NONE","operations":[[1,"CAPTURE_END",null,null,0,0,0,0]]}],"raw_invalid":[],"mutants":{}}
```

Add exactly three independent mutations:

| Name | Sole mutation | First `ValidationError` |
| --- | --- | --- |
| `raw-raw-invalid-nonarray` | replace `raw_invalid:[]` with `{}` | `raw cases` |
| `raw-mutants-nonobject` | replace `mutants:{}` with `[]` | `mutants` |
| `raw-nested-raw-invalid` | replace `raw_invalid:[]` with `[null]` | `nested raw cases` |

The nested element is never interpreted or executed. Each record has coverage
`['malformed-schema',name]`, exact inline UTF-8 and the standard exit-2,
empty-stream, zero-model-call expectation. Cumulative raw count becomes 113.

Positive controls require exit 0 and empty streams for: the exact base; four-byte
prefix `20 09 0d 0a` plus base plus suffix `0d 0a 09 20` (253 bytes); base plus
exactly 1,048,331 ASCII spaces (1,048,576 bytes total); and base with
`mutants:{"unused":"unresolved"}`. The last validates only the decoder container;
build mode does not accept an unresolved mapping.

Tests independently compare all three compact payloads, assert named first errors,
the three-name slice and 113-name union, coverage, uniqueness and ordinary
disjointness. Preserve the 110-record hash and LF-to-CRLF rejection control. The
raw/build tripwire observes 113 children with no compiler/build/model call or
output directory. Construct the byte-limit positive in the test; do not create a
second artifact. Preserve recursion, timeout/output and artifact checks.

`raw-pool-map-array` already covers a nonobject pools container. Alternative
member/type mutations add site coverage only; empty vectors has no frozen rejection.
Defer operation/numeric/key positions, remaining budgets, semantic precedence,
output-oracle and artifact-fault matrices. No full-matrix, compiler, model, native,
ABI or acceptance release follows.
