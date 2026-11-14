# Native lifecycle raw capture-key u64 source packet 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-key-capture-u64-source`
Disposition: `SOURCE_PACKET_DRAFT_ONLY`

Bind this slice to output control-Boolean checkpoint commit
`9c81a0242e52bfe91772f696029f9eafd30f7908`. Preserve its current harness
SHA256 `a4a18e905d238f0763a67e533a1c5a278a9fab3735b2b32a26464a603aecdc54`,
vectors SHA256 `651e053dd507347d3853f3e27a2b6e501c518d7123347fa161908a301fa962d7`,
expected SHA256 `86473f7b4027b9a06e064788d7ed41115b28705a62edc199879990310323a7f7`
and test SHA256 `be7b680a170c4c9bc4fe49eb102d002e58e077ff6ccb896f34a029f1aa9547da`.
Allow only one appended `vectors.json::raw_invalid` record, matching harness
inventory, and focused source tests. Preserve decoder/model logic, ordinary and
expected literals, mutants, artifacts, output tests and all 136 existing raw
records. Keep both corpus flags and `RAW_FULL_MATRIX_FROZEN` false.

Use this exact compact positive document with no trailing newline:

```json
{"schema_version":2,"model_only":true,"corpus_complete":false,"pools":{},"vectors":[{"name":"raw-base","coverage":["raw-base"],"event_capacity":256,"seed":"NONE","operations":[[1,"P_ALLOC",[18446744073709551615,0,1,1,1,0,1],null,100,0,0,0],[2,"CAPTURE_END",null,null,0,0,0,0]]}],"raw_invalid":[],"mutants":{}}
```

It is exactly 309 bytes with SHA256
`d160bba3040ad430b156ae007cbb2dcbd1867b59564d1f9ac9d93470346838c4`.
The sole negative mutation changes capture-key component
`vectors[0].operations[0][2][0]` from integer `18446744073709551615` to
integer `18446744073709551616`. The negative is also 309 bytes, with SHA256
`f3e2178e2cb748c1c9523b0a97c3bd39d7127aaf2450a32d1a98110b1f518443`.
Both expanded operation arrays compact to exactly 101 bytes.

Append exactly one raw record named `raw-key-capture-u64-overflow`, coverage
`["full-key","raw-key-capture-u64-overflow"]`, the exact negative as
`source.inline_utf8`, and expectation
`{"stage":"harness","exit_code":2,"stdout_hex":"","stderr_hex":"","model_invocations":0}`.
This position-specific obligation complements the existing slot-component
overflow case; it does not claim a new validator mechanism. Raw inventory becomes
137.

Expansion of both documents succeeds before key validation. Each visits exactly
26 expansion nodes and charges 299 bytes, leaving budget
`(nodes,bytes) == (262118,2096853)`; maximum expansion depth is only three and
empty-pool preflight is unchanged. The negative first raises the exact harness
`ValidationError("integer")` at key component zero, before required-nonzero and
domain checks. The positive fully decodes with exit zero and empty streams. No
model execution occurs.

Add `test_capture_key_u64_boundary_payload` to
`NativeLifecycleRawDecoderTests`. Independently construct the positive and
negative, assert their exact compact bytes and hashes, and prove the sole
mutation by requiring the positive numeric token once and the negative token
zero times before replacement. Assert exact integer types, input and operation
array sizes, successful expansion/budgets for both, exact exception class and
message for the negative, and positive and negative child outcomes
`(0,b"",b"")` and `(2,b"",b"")`.

Reconcile exactly one new name from 136 to 137. Update the all-raw check and build
tripwire to observe 137 child calls with zero compiler, build or model calls and
no output directory. Preserve the exact first 136 lexical raw records with
SHA256 `f60081f55283820733933c6efba366385ddd3f557d76a6cd7353bd83845ac297`
and retain the prefix/CRLF guards. Require and retain the exact resulting fixture
size below the unchanged 1-MiB limit; do not externalize the small addition or
enlarge limits.

Run all 17 focused raw-decoder tests under pinned Python 3.9.12 and 3.8.10 and
require 17/17 each. The immutable archive has ten members: manifest, four source
files, oversized artifact, this packet and its review, and two command-prefixed
logs. Bind interpreter binaries, source/input hashes and sizes, first-136 hash,
raw 137 and every false gate. Preserve failures separately.

Remaining key-component/type positions and final raw-matrix reconciliation stay
deferred. No compiler, model, native, ABI, application or production release
follows.
