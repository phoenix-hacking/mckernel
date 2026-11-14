# Native lifecycle raw document/vector source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-document-vector-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

This packet is bound to the 28-case checkpoint source: harness
`0ec78538c319db7b1780dce0c7faa1ad58e0d4249462f60e8744c6864735779a`,
vectors `5d1f3e1ebd9a03a97e241e6ed3686f316caaa50c593a8af2690866fc9b4d43df`,
expected `86473f7b4027b9a06e064788d7ed41115b28705a62edc199879990310323a7f7`
and source test `d06d1f4761b6764467c5bc18104a6fe9f31b53fefc2348c8bccbc06fc71fb4cb`.

Allow edits only to `vectors.json::raw_invalid`, the matching name inventory in
`harness.py`, and focused tests in `test_native_lifecycle_model.py`. Preserve the
accepted 28 records byte-for-byte, all ordinary vectors, expected literals,
decoder semantics, models, mutants and oversized artifact. Keep both corpus flags
false and `RAW_FULL_MATRIX_FROZEN=false`.

## Exact base and records

Use this exact compact UTF-8 base without a trailing newline:

```json
{"schema_version":2,"model_only":true,"corpus_complete":false,"pools":{},"vectors":[{"name":"raw-base","coverage":["raw-base"],"event_capacity":256,"seed":"NONE","operations":[[1,"CAPTURE_END",null,null,0,0,0,0]]}],"raw_invalid":[],"mutants":{}}
```

Let `V` be its sole vector and `O` its sole operation. Each case independently
mutates a fresh base. Preserve member order, append added members last and retain
scalar spelling, especially `2.0`.

| Name | Sole mutation |
| --- | --- |
| `raw-json-truncated` | delete the final `}` byte |
| `raw-document-nonobject` | replace the whole root with `[]` |
| `raw-top-missing-field` | remove `model_only` |
| `raw-top-unknown-field` | append top member `"extra":0` |
| `raw-schema-version-wrong` | set `schema_version` to `3` |
| `raw-schema-version-boolean` | set it to `true` |
| `raw-schema-version-integral-float` | set it to `2.0` |
| `raw-model-only-false` | set `model_only` to `false` |
| `raw-model-only-integer` | set it to `1` |
| `raw-corpus-complete-nonboolean` | set `corpus_complete` to `0` |
| `raw-vectors-nonarray` | set `vectors` to `{}` |
| `raw-vector-nonobject` | set `vectors` to `[null]` |
| `raw-vector-missing-field` | remove `V.seed` |
| `raw-vector-name-empty` | set `V.name` to `""` |
| `raw-vector-name-nonstring` | set it to `0` |
| `raw-vector-name-duplicate` | append an exact copy of `V` |
| `raw-coverage-nonarray` | set `V.coverage` to `"raw-base"` |
| `raw-coverage-empty` | set it to `[]` |
| `raw-coverage-nonstring` | set it to `[0]` |
| `raw-coverage-empty-string` | set it to `[""]` |
| `raw-coverage-duplicate` | set it to `["raw-base","raw-base"]` |
| `raw-seed-unknown` | set `V.seed` to `"UNKNOWN"` |
| `raw-seed-nonstring` | set it to `0` |
| `raw-operations-nonarray` | set `V.operations` to `null` |
| `raw-operations-empty` | set it to `[]` |
| `raw-operation-nonarray` | set it to `[null]` |
| `raw-operation-short` | delete `O`'s last field |
| `raw-operation-nonstring-name` | set `O[1]` to `0` |
| `raw-id-zero` | set `O[0]` to `0` |
| `raw-id-gap` | set `O[0]` to `2` |

Each record uses coverage `['malformed-schema', name]`, exact inline UTF-8 and
`{"stage":"harness","exit_code":2,"stdout_hex":"","stderr_hex":"","model_invocations":0}`.
These 30 names bring the cumulative raw inventory from 28 to 58. Authority-slice
extra-field and unknown-operation cases already cover those structural mechanisms;
do not add renamed duplicates.

## Positive controls and checks

Require decoder exit 0 and empty streams for the exact base; base with
`corpus_complete:true`; two otherwise identical vectors named `raw-base` and
`raw-other`; coverage `['raw-base','second']`; the existing exact 128-operation
document; and contiguous operations
`[1,"LAUNCHER_LOSS",null,null,0,0,0,0]`, then
`[2,"CAPTURE_END",null,null,0,0,0,0]`.

Construct all 30 expected compact payload strings independently and compare exact
bytes, never parsed Python equality. Add explicit boolean/integer/integral-float
anti-conflation controls. Assert exact 30-name slice, 58 cumulative names, exact
coverage/expectations, unique names, empty nested raw lists, disjoint ordinary
mappings and byte-identical preservation of the first 28 records. The build
tripwire must observe exactly 58 raw children and no build, compiler, model or
output-directory action. Preserve recursive rejection, artifact and child
timeout/output retirement checks.

After independent packet review, run only the focused raw decoder class and raw
check mode under the existing Python 3.9.12 and `/usr/bin/python3.8` 3.8.10 lanes.
Bind commands, streams, interpreter and source hashes; stop on unexpected failure.

Deferred: alternative missing members and scalar variants; fractional/boolean/
integral-float/out-of-range operation IDs; remaining envelope containers; pool,
numeric/key, semantic, oracle and artifact matrices. This packet does not freeze
the full matrix or release compilation, models, native execution or acceptance.
